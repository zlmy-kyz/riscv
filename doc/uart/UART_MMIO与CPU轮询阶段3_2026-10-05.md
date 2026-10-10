# UART MMIO 与 CPU 轮询：阶段 3

日期：2026-10-05。工程：`D:/riscv/RISCV`。阶段 3 的 RTL/MMIO/CPU 仿真及要求的两条完整 DDR 回归均通过。

## 1. 阅读依据、时钟与数据访问结构

实现前阅读并核对：

- `AGENTS.md`、`RISCV.pds`、`.gitignore`、阶段 1/2 UART 验证记录及对应 RTL/TB/Tcl。
- `myriscv/mycpu_sync.v`、`l_alu.v`：数据请求、SB/SH/SW 的 lane/strobe、load 扩展、请求接受/响应完成、misaligned 与 access fault。
- `myriscv/soc_top.v`、`data_bus_interconnect.v`、`inst_bus_interconnect.v`：实际实例、地址窗、请求和返回选择。
- `myriscv/data_bram_adapter.v`、`inst_bram_adapter.v`、`simple_mmio.v`、`dual_sram_to_pango_ddr_bridge.v`：BRAM 时序、旧 MMIO 行为、DDR 仲裁/掩码/完成握手。
- `myriscv/soc_ddr3_top.v`、`board_top.v`、`reset_button_debounce.v`、`ipcore/ddr3/ddr3.idf` 及 PLL/PHY 时钟配置：参考时钟 125 MHz、DDR 用户 `core_clk=93.75 MHz`，DDR ready/lock 两拍同步释放 SoC reset。
- `doc/SoC结构说明_2026-10-04.md`、板级启动/LED/MMIO 记录、主 ROM/RAM IP 初始化入口、`MyCpu_test/board_selftest/` 地址约定。
- 两条 DDR Tcl、DDR RV32I/CPU 并发访问 runner、已有总线 TB、MMIO/access-fault 脚本及 PDS 行为仿真编译入口。

```text
mycpu_sync 的数据 SRAM-like 请求
    ↓ req_valid/write/size/addr/wdata/wstrb
data_bus_interconnect（单 outstanding；接受时锁存响应目标）
    ├─ RAM  → data_bram_adapter → data_ram
    ├─ MMIO → simple_mmio（原有寄存器）
    ├─ UART → uart_mmio → uart_tx → TX
    │                   RX → uart_rx → uart_rx_fifo → RX_DATA
    └─ DDR  → dual_sram_to_pango_ddr_bridge → DDR IP 用户口
    ↑ req_ready；随后 rsp_valid/rdata/error → CPU MEM/WB
```

指令路径仍为 `mycpu_sync → inst_bus_interconnect → ROM 或共享 DDR 桥`。UART 仅接数据互连，沿用现有请求/响应协议。没有重构仲裁或 CPU 流水线。

CPU 本身拦截不对齐 load/store；slave `rsp_error` 使用既有 load/store access-fault 路径。UART +0x10/+0x14 进入互连原 unmapped target，握手后返回 error，不发明新异常机制。

底层 UART 三个 RTL 完全未改，保留 814 clk/bit：`93,750,000/814 = 115,171.990172 baud`，相对 115200 为 `-0.0243141%`；115200 8N1、idle high、LSB first。

## 2. 地址空间与冲突检查

| 区域 | 默认 CPU 字节地址 | 说明 |
|---|---|---|
| 指令 ROM | 0x00000000–0x00003FFF | 16 KiB，仅指令总线 |
| 数据 RAM | 0x00000000–0x00003FFF | 16 KiB，仅数据总线，与 ROM 分总线 |
| 原 simple_mmio | 0x10000000–0x10000FFF | SCRATCH/ID/CYCLE/STATUS/TEST_STATUS；LED 使用自检状态 |
| 新 UART | 0x10001000–0x1000100F | 精确 16 字节、4 个寄存器 |
| DDR | 0x40000000–0x5FFFFFFF | 512 MiB，ENABLE_DDR=1 才有效 |

原 MMIO 掩码是 `ffff_f000`，因此不覆盖 `0x10001000`。RAM、ROM、DDR 都不覆盖 UART 窗口。当前未实现独立 timer/GPIO/CLINT/PLIC 窗口；CPU CSR/trap 不构成另一个数据 MMIO 窗口。启动程序及 DDR 装载/跳转目标不在新 UART 窗口。采用建议基址无冲突。

互连增加 `ENABLE_UART`（独立互连默认 0）和 `UART_BASE`；`soc_top` 打开 UART。地址选择保持 one-hot，返回路径按接受时的目标锁存，不随等待期间 master 地址变化。`UART_BASE` 须按 16 字节对齐，项目使用上述默认值。

## 3. 寄存器及接口

| 地址 | 名称 | R/W | 位定义 | 副作用 |
|---|---|---|---|---|
| 0x10001000 | TX_DATA | W | [7:0] 待发字节 | 低 lane 有效且 TX_READY 时开始一帧；busy 时丢弃新字节并返回总线 error；读返回 error |
| 0x10001004 | RX_DATA | R | [7:0] FIFO 队首，[31:8]=0 | 接受低字节地址的合法读取时锁存队首并 pop 一次；empty 返回 0、不 pop；写返回 error |
| 0x10001008 | STATUS | R | 0 TX_READY；1 TX_BUSY；2 RX_NOT_EMPTY；3 RX_FULL；4 FRAME_ERROR；5 RX_OVERFLOW；[31:6]=0 | 无副作用；写返回 error |
| 0x1000100C | CONTROL | W1C / R=0 | 0 clear frame；1 clear overflow | 写 1 清相应 sticky；其余位忽略，不影响收发/FIFO |

遵守 CPU 的移位后 `req_wdata` 和 `req_wstrb`：对低字节的 SB/SH/SW 均有效；只写上 lane 或零 mask 不启动 TX/不清错误。RX_DATA 上 lane 读取不消费字节，返回 word 的上位为零，由 CPU 做 lane 选择。`req_size=3` 或半字/字不对齐请求返回 error。

`uart_mmio` 接口：`clk/resetn`；输入 `req_valid/req_write/req_size[1:0]/req_addr[31:0]/req_wdata[31:0]/req_wstrb[3:0]`；输出 `req_ready/rsp_valid/rsp_rdata[31:0]/rsp_error`；输入 `uart_rx`、输出 `uart_tx`。地址是互连减去 UART_BASE 后的局部字节地址。参数 `CLK_HZ=93750000`、`BAUD=115200`、`RSP_DELAY_CYCLES=0`。响应延迟参数用于验证 pending 等待，不增加新的 bus 协议。

## 4. 握手与收发流程

`req_fire = req_valid && req_ready` 是唯一 side-effect 条件。接受边沿锁存读数据/error、执行 TX send/FIFO pop/W1C，随后 `pending` 阻止新的握手。默认下一周期给出一次 `rsp_valid`，响应被现有 CPU/互连接收后清 pending。响应接口与原工程一致，无 `rsp_ready`。

RX 读是在接受边沿同时锁存旧队首并 pop；之后响应来自锁存数据，FIFO 后续变化不改变本次返回值。请求在 pending 期间持续不会再次 pop 或发送。

协议含义是每个 valid/ready 握手代表一个请求：master 完成握手后应撤销原请求。若 master 故意把 valid 保持到下一次 ready 又握手，该边沿代表第二个请求，不是 slave 应去重的第一笔。TB 用响应延迟 6 拍、握手后保持请求 5 个时钟，明确保证仅一次握手/一次响应/一次 pop。

TX 软件先轮询 STATUS[0]，再 store TX_DATA；busy 误写产生既有 store access fault，当前帧不被破坏。RX 软件先轮询 STATUS[2]，再 load RX_DATA。FIFO 固定沿用已有深度 16，不增加 TX FIFO。

错误寄存器每拍更新：`sticky_next = event || (sticky && !clear)`。底层 frame_error/overflow 单周期事件锁存到 STATUS，软件错过脉冲也能观察。新事件优先于同边沿 W1C；CONTROL=0/1/2/3 分别不清/清 frame/清 overflow/全清。

`soc_top` 暴露串口给仿真。当前 `soc_ddr3_top` 将内部 RX 固定 1、TX 不接外部端口；`board_top`、J8、引脚约束未改。UART reset 来自原 SoC reset，未改变时钟或整体复位结构。

## 5. 文件改动与共享范围

### 本轮新增实现/验证文件

- `myriscv/uart_mmio.v`：MMIO、一次响应、FIFO pop、sticky/W1C；新增外设逻辑。
- `source/tb_uart_mmio.v`：真实数据互连、原 MMIO、UART，与受控 RAM/DDR responder；总线级自动检查。
- `source/tb_soc_uart_cpu.v`：真实 `soc_top/mycpu_sync` 执行最小轮询程序，串口输入/输出独立检查。
- `sim/uart_mmio/run_uart_mmio.tcl`、`run_soc_uart_cpu.tcl`、`run_bus_regression.tcl`：沿用 ModelSim，独立 work/log。
- `sim/uart_mmio/uart_poll.S`：仅仿真程序；复用 `difftest/golden/rvtool.py` 汇编，生成 `cpu_image/{rom.hex,ram.hex,prog.lst}`。
- `sim/uart_mmio/uart_synth/uart_synth.pds`、`uart_synth.fdc`：只包含 4 个 UART 源文件的独立 PDS 工程，93.75 MHz 模块时钟约束，无引脚分配、无 DDR IP。
- 本记录及 `doc/uart/UART阶段3_Git检查_2026-10-05.txt`：阶段实现时的本地开发记录；后续发布选入本文，Git 检查快照仍仅保留本地。

### 本轮修改已有文件

| 文件 | 修改原因 | 共享 SoC 逻辑？ |
|---|---|---|
| `myriscv/data_bus_interconnect.v` | 增加 UART 精确译码/转发/返回目标；原目标编号不变，target 位宽 2→3 | 是 |
| `myriscv/soc_top.v` | 例化 UART MMIO、连接数据互连、暴露仿真串口 | 是 |
| `myriscv/soc_ddr3_top.v` | 仅将 u_soc 新 RX 端口接 idle、TX 留内部 | 是，接线而已 |
| `RISCV.pds` | 注册 4 个 UART 源文件；保留进入任务前已有生成时间注释 | 工程源文件列表 |
| `source/tb_data_bus_interconnect.v`、`tb_ddr_bus_path.v` | 接上新增而禁用的 UART slave 返回端，保持旧测试逻辑 | 否，旧 TB 兼容 |
| `source/tb_soc_top.v`、`tb_soc_ddr3_rv32i_fast.v` | 新 RX 接 1、TX 未用 | 否，旧 TB 兼容 |
| `ipcore/ddr3/sim/modelsim/soc_ddr3_sim.tcl`、`soc_ddr3_regress_sim.tcl`、`soc_ddr3_rv32i_sim.tcl` | 编译列表增加 UART 依赖 | 否，仿真入口 |
| `MyCpu_test/run_ddr_rv32i_fast.py`、`run_cpu_ddr_overlap_fast.py` | 编译列表增加 UART 依赖 | 否，仿真入口 |
| `sim/pds_ddr_selftest_compile.tcl`、`pds_ddr_ip_compile.tcl`、`pds_ddr_reset_compile.tcl` | 保持现有完整 IP/PDS 仿真入口可编译 | 否，仿真入口 |
| `sim/board_main_selftest/compile.tcl`、`board_main_selftest_candidate/compile.tcl`、`board_key_boot_validation/compile.tcl`、`board_top_validation/compile.tcl` | 同上，仅依赖列表 | 否，仿真入口 |
| `difftest/run_mmio.ps1`、`run_access_fault.ps1`、`run_inst_access_fault.ps1`、`run.ps1` | 本地忽略文件，增加 UART 编译依赖；保留 Windows PowerShell 5 UTF-8 BOM | 否，仿真入口 |
| `difftest/tb/tb_mmio_test.v`、`tb_access_fault_test.v`、`tb_inst_access_fault_test.v`、`tb_difftest.v` | 本地忽略文件，新 RX 接 1、TX 未用 | 否，旧 TB 兼容 |

刷新现有 `soc_ddr3_sim.log`、`soc_ddr3_regress_sim.log`、阶段 1/2 日志及各回归生成日志。未改 CPU、BRAM/DDR bridge、DDR3/PHY/IP 配置、board_top、启动镜像、装载流程、中断或引脚约束。

## 6. 自动验证与结果

MMIO TB 用真实串口引脚激励 RX，按独立标称 `1e9/115200 ns` 位周期解码 TX 的起始、LSB-first 8 数据位、停止位，比较预期字符。超时或任何不一致输出具体 `RESULT: FAIL` 并 `$fatal`，Tcl 也检查完成标志并返回非零。

| 检查 | 结果 |
|---|---|
| 地址无冲突；one-hot 选择；16 字节边界；+10/+14 unmapped | PASS |
| STATUS reset=1；TX_READY/TX_BUSY；保留位=0 | PASS |
| TX 写 H、软件轮询 Hello、SB/SH/SW、上 lane/零 mask | PASS |
| busy 写 X 返回 error，不破坏/重复现有字符 | PASS |
| 从 TX 线解码 9 帧：H、Hello、55/AA/80，无丢失/重复 | PASS |
| RX 引脚波形 Hello→RX→FIFO→MMIO，按序读回 | PASS |
| A/B/C 持续请求只 pop A；随后独立读 B/C | PASS |
| upper-lane RX read 无 pop；反复 empty read=0 无 pop/X | PASS |
| STATUS 连续读不 pop、不发 TX、不清错误 | PASS |
| RX_FULL、overflow sticky、满 FIFO 保留原 16 字节 | PASS |
| frame_error sticky、不入错误字节；W1C 0/1/2/3/mask | PASS |
| 两种错误同边沿 event/W1C：event 优先 | PASS |
| R/W 权限、不对齐非法请求、原 RAM/MMIO/DDR/unmapped | PASS |

总线级最终 `TX=9 requests=8230 responses=8230 pops=24`，`Errors: 0, Warnings: 0`。

真实 CPU 软件程序执行 68 条静态指令，动态轮询 TX_READY 后分别用 SB/SH/SW 发送 Hello；TB 在 RX 引脚注入 Hello，CPU 轮询 RX_NOT_EMPTY 后用 LBU/LB/LHU/LH/LW 读并比较，最后通过原 TEST_STATUS 报 PASS。TB 独立解码 TX Hello，并核对 5 次 TX store、5 次 RX load、2014 次 STATUS poll、FIFO empty、无意外总线 error。`RESULT: PASS soc_uart_cpu`，`Errors: 0, Warnings: 0`。程序只在独立仿真 ROM 运行，未替换板级启动镜像。

## 7. 实际命令和回归证据

以下为 PowerShell 命令。UART Tcl 要在对应目录执行；DDR 两条须依次执行，厂家 file list 使用相对路径。

```powershell
Set-Location D:/riscv/RISCV/sim/uart_mmio
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_mmio.tcl'
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_bus_regression.tcl'

Set-Location D:/riscv/RISCV
python difftest/golden/rvtool.py asm sim/uart_mmio/uart_poll.S sim/uart_mmio/cpu_image
Set-Location sim/uart_mmio
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_soc_uart_cpu.tcl'

Set-Location D:/riscv/RISCV/sim/uart_tx
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_tx.tcl'
Set-Location D:/riscv/RISCV/sim/uart_rx
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_rx.tcl'

Set-Location D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do soc_ddr3_sim.tcl; quit -f'
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'

Set-Location D:/riscv/RISCV
powershell -NoProfile -File difftest/run_mmio.ps1
powershell -NoProfile -File difftest/run_access_fault.ps1
powershell -NoProfile -File difftest/run_inst_access_fault.ps1
python MyCpu_test/run_ddr_rv32i_fast.py
python MyCpu_test/run_cpu_ddr_overlap_fast.py
python MyCpu_test/run_cpu_ddr_overlap_fast.py --backpressure
```

| 实际测试 | 实测结果/日志 |
|---|---|
| 阶段 1 TX `run_uart_tx.tcl` | PASS；0 Errors / 0 Warnings；`sim/uart_tx/uart_tx.log` |
| 阶段 2 RX/FIFO/loopback `run_uart_rx.tcl` | PASS；0 / 0；`sim/uart_rx/uart_rx.log` |
| UART MMIO `run_uart_mmio.tcl` | PASS；0 / 0；`sim/uart_mmio/uart_mmio.log` |
| CPU UART `run_soc_uart_cpu.tcl` | PASS；0 / 0；`sim/uart_mmio/soc_uart_cpu.log` |
| 原 `tb_data_bus_interconnect` | PASS；0 / 9，原 TB 未用 DDR/test_status 端口 warning；`sim/uart_mmio/tb_data_bus_interconnect.log` |
| 原 `tb_ddr_bus_path` | PASS；0 / 0；`sim/uart_mmio/tb_ddr_bus_path.log` |
| `soc_ddr3_sim.tcl` 完整 IP+物理模型 | PASS DDR store/load/fetch，81584000 ps；0 / 357；原目录 `soc_ddr3_sim.log` |
| `soc_ddr3_regress_sim.tcl` 完整 IP+物理模型 | PASS lanes/masks/boundary/DDR-code，90704000 ps；0 / 357；原目录 `soc_ddr3_regress_sim.log` |
| `mmio_e2e` | PASS cycles=153，mmio_req=5，ram_req=1，scratch=1234aa78；`difftest/build/mmio_e2e/sim.log` |
| `access_fault_e2e` | PASS cycles=445，unmapped=2/errors=2/traps=2；对应 `difftest/build/access_fault_e2e/sim.log` |
| `inst_access_fault_e2e` | PASS cycles=193，unmapped_fetch=3/errors=3/traps=1；对应 `difftest/build/inst_access_fault_e2e/sim.log` |
| DDR RV32I fast | 40 个 supported 全 PASS；fence_i、ma_data 两个原 runner 的 known_gap 仍 FAIL；不是 42/42 PASS；`MyCpu_test/ddr_stage/fast_summary.csv` |
| CPU-origin DDR overlap | ld_st/lb/st_ld/sw/lw 5 个 PASS；`sim/uart_mmio/cpu_ddr_overlap_console.log` |
| CPU-origin DDR backpressure | ld_st PASS；`sim/uart_mmio/cpu_ddr_backpressure_console.log` |

两条完整 DDR 日志与 Git HEAD 比较：原先也是 357 warning，PASS 时间不变，本轮新增 UART 模块加载与运行时间记录；没有增加厂家 warning。Icarus 原回归还会输出旧 CPU 子模块 timescale 和禁用 DDR 未接端口 warning，执行退出码均为 0，没有新增 UART dangling input。

## 8. 综合检查与限制

实测命令：

```powershell
& 'C:/pango/PDS_2022.2-SP6.4/bin/pds_shell.exe' `
  -project 'D:/riscv/RISCV/sim/uart_mmio/uart_synth/uart_synth.pds' `
  -work_dir 'D:/riscv/RISCV/sim/uart_mmio/uart_synth' -run synthesize
```

独立 `uart_mmio` 顶层及现有三个 UART 子模块完成 PDS Compile/Synthesize，退出码 0，最终日志没有 `E:`，`Total Latches: 0`。检查未发现 multiple-driver 或 width-mismatch 诊断。

`sim/uart_mmio/uart_synth/run.log` 最终有 133 条 `W:`：14 条未分配端口 I/O 约束、83 条模块输入/输出未给 delay、25 条常量高位寄存器删除/悬空清理、9 条 constant probe loop、2 条 max-fanout 未满足。constant probe 同类诊断也出现在原 PDS 综合日志中；它位于综合器常量探测阶段，不能据此宣称板级实现/时序已经通过。保留完整日志，不隐藏 warning。

本检查只有 UART 模块 93.75 MHz clock 约束，无 physical pin assignment；不是完整 board_top 综合、布局布线或实板 timing closure。没有重新生成 DDR IP。未验证板级引脚、USB-TTL、电气时序、中断或 CoreMark 输出，属于后续阶段。

## 9. Git 范围、已有修改和生成文件

进入本轮前 `RISCV.pds` 已有生成时间注释从 Oct 4 改为 Oct 5 00:40:48；本轮保留它，功能改动仅是 UART 源文件注册。阶段 1/2 的 3 个 UART RTL、2 个 TB、2 套 Tcl/log 原本就未跟踪，不能当作本轮新增功能。

底层 SHA256 与开始时相同：

```text
uart_tx.v      BC132B3A229FEA8894B52FE60BFED0F376A4097B0A3F074FAB48E02BFE15AB4F
uart_rx.v      D602552BFC6269C1ED87EF2C4F094BD4F7D600F3AC81DB1B860C485FA6A2BB4E
uart_rx_fifo.v E0377AEBB6B43B8C76BCAF1B5854D14BA9E1E5141FDA60BFEDC558EAC9728047
```

`git diff --check`、`git diff --stat`、`git status --short` 的最终原始输出保存到同目录 Git 检查记录。普通 diff stat 不包含未跟踪的新 uart_mmio/TB/Tcl/软件/PDS 检查文件，也不包含被忽略的 doc/difftest 改动。仿真日志和 cpu_image 为验证产物；ModelSim work/wave 与 PDS compile/synthesize 按已有 .gitignore 保留本地。没有执行 clean/reset/stage/commit，也没有覆盖不相关文件。

## 10. GitHub 发布范围

以上 Git 状态是阶段 3 实现结束时的历史快照。随后按用户要求公开 UART 阶段 1/2/3 源码、TB、Tcl、CPU 轮询汇编、工程/编译依赖更新、精选日志、结构文档与 PNG/SVG/绘图源；README 同步当前 UART 地址和板级边界。

`.gitignore` 仅为三份 UART 记录、结构图/绘图源及 `difftest/golden/rvtool.py`、`difftest/model/{inst_rom.v,data_ram.v}` 添加精确例外。新克隆可生成 CPU 仿真镜像并运行 UART CPU 测试；完整旧 difftest 脚本/TB、其编译/运行日志和本地 Git 状态快照不发布，本记录列出的旧 MMIO/access-fault 命令仍依赖本地完整 difftest 工程。

CPU 仿真 hex/listing、ModelSim 库/波形、重复 console、PDS 构建数据库/临时报告继续保留本地。独立 UART 综合只公开 PDS/FDC 输入和主要 `run.log` 作为证据；不公开重复 flow/console 或生成 impl 记录。没有修改 CPU、DDR IP/时钟、板级引脚或启动镜像。

发布前于 2026-10-05 从 Git index 用 `git checkout-index --prefix=<独立目录>/ -- <测试输入路径>` 导出 65 份已跟踪测试输入到 `tmp/uart_upload_verify_20261005_60338cee/`，目录不含原工作树的编译库、CPU 镜像或未公开 difftest 文件。以 `C:/python/python.exe` 执行上述 `rvtool.py asm` 命令重新生成 68 条指令的 UART 测试镜像，再按 README 的 ModelSim 命令运行 `run_uart_tx.tcl`、`run_uart_rx.tcl`、`run_uart_mmio.tcl`、`run_soc_uart_cpu.tcl` 和 `run_bus_regression.tcl`，退出码全部为 0。四项 UART 测试全部自动检查 PASS、0 Errors / 0 Warnings；两项原总线测试 PASS、0 Errors，原未用端口的 9 条 warning 仍存在。该验证确认本次公开文件包含 UART CPU 测试所需依赖。

发布整理仅去除精选日志的行尾空格，保留全部诊断和 PASS/FAIL 信息；`git diff --cached --check` 通过。独立副本和新生成的验证产物继续忽略，不纳入提交。
