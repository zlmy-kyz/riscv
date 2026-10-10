# CPU 中断验收与 UART RX IRQ

验证日期：2026-10-05。范围：现有 CPU 中断验收，最小 UART RX 电平 IRQ 扩展及 SoC 接线，RTL＋仿真。没有执行 PDS Synthesis、Place & Route、bitstream；没有更换板级启动镜像或增加物理引脚约束。

## 1. 阅读与原有机制

先检查 git status/diff、`AGENTS.md` 和 `doc/SoC结构说明_2026-10-04.md`，保留已有工作树改动；阅读以下文件：

- `myriscv/mycpu_sync.v`：IRQ 仲裁、FLOW_RUN/IRQ_DRAIN/IRQ_CHECK、WB trap/CSR/MRET、arch_next_pc、访存握手、等待、退休及冲刷。
- `myriscv/csr_file.v`、`csr_defs.vh`：mstatus/mie/mip/mtvec/mepc/mcause/mtval、Direct mtvec、WARL 掩码及 trap/MRET。
- `myriscv/soc_top.v`、`soc_ddr3_top.v`、`board_top.v`：现有三个 IRQ 输入、UART 层次、时钟和复位；DDR IP IDF/生成时钟配置核对沿用 125 MHz 参考与 93.75 MHz core_clk。
- `myriscv/inst_bus_interconnect.v`、`data_bus_interconnect.v`、两个 BRAM adapter、`dual_sram_to_pango_ddr_bridge.v`、`simple_mmio.v`：一笔未完成请求的目标锁存、延迟响应、错误响应及 Pango AXI-like 端口（无 WVALID/B/RREADY）。
- `myriscv/uart_mmio.v`、`uart_tx.v`、`uart_rx.v`、`uart_rx_fifo.v`：寄存器、握手时副作用、异步 RX 同步、16 字节队列、旧错误 W1C。
- `difftest/tb/tb_irq_step11.v`、`difftest/prog/irq_step11.S`、CSR/trap 专项汇编工具、`difftest/run*.ps1`、`source/tb_soc_uart_cpu.v`、`tb_uart_mmio.v`、DDR fast TB、UART/DDR Tcl 和 Python runner：沿用已有仿真工具与风格。

CPU 已有 Machine Mode 中断，不需要新建中断控制器：

1. mip 直接反映同步电平：MEIP[11]、MSIP[3]、MTIP[7]；mie 的使能掩码为 0x888，mstatus.MIE 是全局使能。软件读 mip 不受这些使能屏蔽。
2. 资格为 `mstatus.MIE && |(mip & mie)`，优先级 external(11) → software(3) → timer(7)。进入 IRQ_DRAIN 后停止新 ID 发射，让已发射 EX/MEM/WB 和已接受数据事务完成。
3. pipeline_empty 且 IRQ 仍有效才提交中断。mepc 取退休后的 arch_next_pc，mcause 为 0x8000000B/03/07，mtval=0；同步异常优先，mepc 是故障指令 PC，mcause 不置中断位。
4. trap 将旧 MIE 复制到 MPIE 并清 MIE，Direct mtvec 重定向；MRET 由 mepc 返回、MPIE 恢复 MIE、MPIE 置 1，再检查仍有效的 IRQ。撤销的 IRQ 在排空结束不再进入 ISR。

原来的缺口是 UART 无 IRQ 使能或输出、板级三个外部源为 0，以及缺少当前共享 DDR/延迟 MMIO 总线的中断验收。旧 step11 TB 还使用 CPU 内嵌存储的历史层次，不能直接证明当前 SoC；本轮读取其覆盖意图后用新的真实 `soc_top` TB 验收，没有声称旧 TB 在当前接口上运行通过。

## 2. 修改与连接

功能 RTL 仅修改：

- `myriscv/uart_mmio.v`：一个复位为 0 的 rx_irq_enable 寄存器、CONTROL 命令和 STATUS 诊断位、新输出 uart_irq。
- `myriscv/soc_top.v`：接收 uart_irq；`cpu_irq_external = irq_external | uart_irq`；送 `u_cpu.irq_external`。原 generic external 输入保留，板级该输入为 0，没有覆盖其他外设。

测试新增 `source/tb_soc_irq.v`、`sim/uart_irq/run_irq.py`、`soc_fixture.vh`、`irq_checks.vh`、`uart_stimulus.vh`、`uart_irq.S`。`source/tb_uart_mmio.v` 保留全部旧检查，连接新增 IRQ 输出并补充命令/掩码/复位测试。更新 `AGENTS.md`、`README.md`、结构说明、本文及 `.gitignore` 的文档/仿真 build 规则；回归刷新既有日志。

实际板级层次：

```text
board_top.uart_rx
  → board_top.u_soc.uart_rx                         (soc_ddr3_top)
  → board_top.u_soc.u_soc.uart_rx                   (soc_top)
  → board_top.u_soc.u_soc.u_uart_mmio.u_rx
  → u_uart_mmio.u_fifo                             (真实 RX byte 入 FIFO)
  → u_uart_mmio.uart_irq = rx_irq_enable && !fifo_empty
  → soc_top.uart_irq
  → soc_top.cpu_irq_external = irq_external | uart_irq
  → board_top.u_soc.u_soc.u_cpu.irq_external
  → u_cpu.u_csr_file.irq_pending[11] (mip.MEIP) → trap → ISR RX_DATA pop
  → FIFO 读空 / uart_irq 撤销 → MRET → 原程序
```

UART IRQ 在 core_clk 同域，不需要另加 CDC；异步串口输入仍由已验证的 uart_rx 两拍同步。没有使用 rx_valid 单周期脉冲作为 IRQ。board_top/soc_ddr3_top 不需要增加 IRQ 引脚。

CPU、CSR、uart_tx、uart_rx、uart_rx_fifo 的 SHA256 与本轮开始时一致；未修改共享互连、DDR 桥/IP/PHY、93.75 MHz 时钟、boot flow、主 ROM/RAM 初始化。工作树中已存在的 RISCV.pds、impl.tcl、multiseed_summary.csv 改动保留。中间核对三者哈希未变；最终整理期间检测到任务之外的更新：RISCV.pds/impl.tcl 最后写入为 16:02:39，约束文件 16:02:23 新增 UART TX=AA20、RX=AA21，另有同刻约束备份。本任务的工具没有调用 PDS 或写入这些文件，保留外部更新；AA20/AA21 未在本轮核验官方原理图，不能据此声称物理 UART 接线正确或实板验证通过。

## 3. MMIO 软件接口

原 16 字节地址窗与四个寄存器不变，默认基址 0x10001000：

| 寄存器 | 新位 | 语义 |
| --- | --- | --- |
| CONTROL +0xC | bit8 RX_IRQ_ENABLE_SET | 写 1 使能；需要 wstrb[1]，SB 到 +0xD 的移位数据、低 SH 或 SW 均可 |
| CONTROL +0xC | bit9 RX_IRQ_ENABLE_CLEAR | 写 1 禁用；需要 wstrb[1]；同时 set/clear 时禁用优先 |
| STATUS +0x8 | bit6 RX_IRQ_ENABLE | 当前使能寄存器 |
| STATUS +0x8 | bit7 RX_IRQ_PENDING | 使能后的实际 IRQ 电平；原 bit2 仍表示原始 FIFO 非空 |

CONTROL 仍读 0，写 0 或旧 bit0/1 W1C 不改变 IRQ 使能；STATUS bit0–5 不变、bit31:8 为 0。所有命令仅在合法请求的接受边沿执行；禁用不清 FIFO，轮询仍可读出数据；复位清使能/FIFO/IRQ。

```c
*(volatile unsigned int *)0x1000100C = 0x100; /* RX IRQ enable */
*(volatile unsigned int *)0x1000100C = 0x200; /* RX IRQ disable */
/* ISR: while STATUS bit2 != 0, read RX_DATA at 0x10001004. */
```

CPU 还须设置四字节对齐的 mtvec（本测试 0x400）、mie.MEIE=bit11、mstatus.MIE=bit3。测试 ISR 专用 x20–x28 寄存器是明确的仿真程序约定，不是通用 C ABI ISR 示例；没有嵌套或软件优先级机制。主板级镜像没有替换或使能 UART IRQ。

## 4. CPU 专项验收

先在原 CPU/UART RTL 上运行全部 16 项 PASS，才修改 UART IRQ；接入后重新运行。下面每项又分别在 ROM 取指和 DDR 取指配置运行，共 **32/32 PASS**。

| case | 场景 | 结果与关键检查 |
| --- | --- | --- |
| 0 | 普通 external IRQ | PASS，cause=11、1 ISR/1 MRET，续执行一次 |
| 1 | 全局 MIE 屏蔽再使能 | PASS，屏蔽时 mip 仍读 0x800，使能后进入 ISR |
| 2 | mie 局部屏蔽再使能 | PASS，mip 不被局部 mask 隐藏 |
| 3 | DDR store 等待中 IRQ | PASS，37 个 overlap 时钟，目标请求/退休/物理写各 1 |
| 4 | DDR load 等待中 IRQ | PASS，50 个 overlap 时钟，目标请求/退休/读各 1，值 0x12345678 |
| 5 | store 响应边界 IRQ | PASS，请求/退休/实际写各 1 |
| 6 | load 响应边界 IRQ | PASS，请求/退休/读各 1 |
| 7 | UART STATUS MMIO 延迟中 IRQ | PASS，10000 个 overlap 时钟，单次请求/退休，读值 1 |
| 8 | MMIO 响应边界 IRQ | PASS，单次请求/退休 |
| 9 | misaligned load 异常与 IRQ | PASS，cause4、mtval=0x40000001、故障不发数据请求/不退休；先异常后中断，两次 MRET |
| 10 | 只读 MMIO store access fault 与 IRQ | PASS，cause7、mtval=0x10000004；先异常后 IRQ，故障仅请求一次、不退休 |
| 11 | 等待时 IRQ 撤销 | PASS，排空期间看见 IRQ，撤销后 0 ISR；store 完成一次 |
| 12 | 持续电平 IRQ | PASS，2 次 ISR/2 MRET；原程序目标/续执行均一次 |
| 13 | software IRQ | PASS，cause3 |
| 14 | timer IRQ | PASS，cause7（中断位为 1） |
| 15 | 三路同时 pending | PASS，external → software → timer，3 ISR/3 MRET |

`soc_fixture.vh` 例化实际 CPU/互连/BRAM adapter/MMIO/DDR 桥。测试用 Pango 用户口模型产生 AWREADY/ARREADY/WREADY 背压和延迟 RVALID；store 只在模型 WREADY 时写一次。MMIO 使用已有 UART_RSP_DELAY_CYCLES=10000，不改 simple_mmio。DDR 取指配置从 0x40001000 执行前台程序，ISR 留在 ROM 0x400，数据仍在 DDR 0x40000000；只是独立 TB 预载模型，未改板级装载过程。

`irq_checks.vh` 从退休指令独立解码顺序 PC、branch、JAL/JALR，维护寄存器影子值，不用 DUT 的 arch_next_pc/mem_wb_next_pc 来生成期望 PC；逐次比较退休 PC、trap mepc/mcause/mtval、MIE/MPIE、Direct mtvec、MRET 返回。指令运算的全面检查由原差分/RV32I 回归补充。IRQ 边界断言已接受数据请求全部响应，EX/MEM/WB 排空，禁止同边沿新数据请求/ID 发射。已接受的投机取指可以迟到，由 CPU 原有冲刷丢弃；DDR 取指的退休 PC 检查覆盖其效果。

每个目标访存同时统计 CPU 接受次数、响应总数、退休次数和 DDR 真实模型读写次数。故障指令不得写 GPR/正常退休；中断取消和持续电平分别计数，最终程序结果及 RAM/DDR 数据也比较。

## 5. mepc/mcause/MRET 证据

每次 trap/MRET 自动输出详细日志，不依赖目测波形。ROM/DDR 两种真实 UART 程序的四次中断日志分别记录：

| 次序 | ROM 前台 mepc | DDR 前台 mepc | mcause | MRET |
| --- | --- | --- | --- | --- |
| 单字节 H | 0x00000084 | 0x40001084 | 0x8000000B | 返回相同 mepc，MIE=1/MPIE=1 |
| 队列 Hello | 0x0000009C | 0x4000109C | 0x8000000B | 同上 |
| DDR store 等待 | 0x000000B4 | 0x400010B8 | 0x8000000B | 同上，store 不重放 |
| MMIO load 等待 | 0x000000D0 | 0x400010CC | 0x8000000B | 同上，load 不重放 |

后两项的 ROM/DDR 取指延迟不同，IRQ 排空前已退休的年轻指令边界也不同；期望 mepc 依据独立退休模型计算，不能机械地给 ROM 结果加 DDR 基址。

调试测试自身时修正了两类假设：MMIO 测试主机原协议要求 held valid 在响应前解除，因此新命令的保持长度改为允许范围；STATUS 保留位断言改为 bit31:8。另一个固定“中断一定返回目标 store+4”的新增断言不适合所有退休边界，已删除，保留独立退休模型：DDR case5 的 store 0x40001038 和后续串行 CSR 0x4000103C 都已退休，中断正确 mepc=0x40001040、MRET 返回 0x40001040，物理写/请求/退休各 1。没有为这些测试假设修改 CPU；生成了该 case 的 VCD 作为辅助证据（build 下、未发布）。

## 6. 真实 UART 引脚闭环

`uart_stimulus.vh` 按独立的 `1e9/115200` ns 位周期、非时钟对齐相位在 RX 引脚产生 8N1，不直接注入 FIFO、不强制 CPU/MMIO 请求。`uart_irq.S` 由真实 CPU 执行：

1. RX IRQ 默认 disabled；CPU 中断使能但收到 D，不进 ISR，主程序轮询读取。
2. CONTROL 使能、FIFO 空，执行延时，不允许额外 IRQ。
3. 收 H，进入 ISR，读 RX_DATA、清空队列、撤销 IRQ、MRET 返回。
4. UART 保持使能，暂屏蔽 CPU MIE，在 DDR load 的 70000-cycle 延迟中连续收 Hello，FIFO 达到 5；load 完成后开启 MIE，ISR 顺序读出五字节，最后一笔 pop 撤销 IRQ。
5. MIE 开启时，DDR store 等待 WREADY 的 14000-cycle 延迟中收到 0xA5；中断只在 store 已响应/退休后进入，物理写和退休均一次。
6. MIE 开启时，10000-cycle 的 UART STATUS MMIO load 等待中收到 0xB6；原 load 完成并退休一次，再进入 ISR。
7. CONTROL 禁用，收到 Z，主程序仍能轮询读出，不新增 ISR。

自动核对每个 FIFO pop 的字节及最终软件缓冲：`44 48 48 65 6C 6C 6F A5 B6 5A`；引脚输入 10、pop 10、ISR 收 8、轮询收 2、ISR/MRET 各 4、FIFO 峰值 5、无 frame/overflow error。每个启用状态下的 ISR pop 都要求实际 IRQ 为高，最后一次 pop 在 MMIO 响应前即撤销 IRQ。

ROM 和 DDR 取指两次均 PASS，输出：

```text
RESULT: PASS UART RX IRQ: pin_bytes=10 pops=10 ISR=4 MRET=4 FIFO_peak=5
DDR_store_IRQ_wait=6246 MMIO_load_IRQ_wait=2249 DDR_W=1 DDR_R=1 req=50 rsp=50
```

## 7. 实际执行命令

以下从根目录运行，工具路径沿用本机 Icarus/ModelSim，Python 实际使用 `C:/python/python.exe`：

```powershell
& C:/python/python.exe sim/uart_irq/run_irq.py --stage cpu
& C:/python/python.exe sim/uart_irq/run_irq.py --stage cpu --ddr-code
& C:/python/python.exe sim/uart_irq/run_irq.py --stage uart
& C:/python/python.exe sim/uart_irq/run_irq.py --stage uart --ddr-code
& C:/python/python.exe sim/uart_irq/run_irq.py --stage cpu --ddr-code --case 5 --wave
powershell -NoProfile -File difftest/run.ps1 -Prog prog0_alu
powershell -NoProfile -File difftest/run.ps1 -Prog prog1_mem
powershell -NoProfile -File difftest/run.ps1 -Prog prog2_hazard_precision
powershell -NoProfile -File difftest/run_mmio.ps1
powershell -NoProfile -File difftest/run_access_fault.ps1
powershell -NoProfile -File difftest/run_inst_access_fault.ps1
& C:/python/python.exe MyCpu_test/run_ddr_rv32i_fast.py
& C:/python/python.exe MyCpu_test/run_cpu_ddr_overlap_fast.py
& C:/python/python.exe MyCpu_test/run_cpu_ddr_overlap_fast.py --backpressure
& C:/python/python.exe difftest/golden/rvtool.py asm sim/uart_mmio/uart_poll.S sim/uart_mmio/cpu_image
```

每条 ModelSim 命令先进入对应目录：

```powershell
Set-Location D:/riscv/RISCV/sim/uart_tx
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_tx.tcl; quit -f'
Set-Location D:/riscv/RISCV/sim/uart_rx
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_rx.tcl; quit -f'
Set-Location D:/riscv/RISCV/sim/uart_mmio
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_mmio.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_soc_uart_cpu.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_bus_regression.tcl; quit -f'
Set-Location D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_sim.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'
```

新 runner 使用 `iverilog -g2012 -Ptb_soc_irq.EXEC_FROM_DDR=0/1 -I myriscv -I sim/uart_irq -s tb_soc_irq` 编译实际 SoC 源和旧行为存储模型，再用 vvp 的 CASE/TARGET/RESUME 等 plusargs 选择程序。依赖只需仓库公开的 rvtool.py 与两份模型，不依赖忽略的旧 difftest 程序。build 含 asm/listing/4096 字 ROM/RAM hex/编译和逐例日志，可重新生成；结果摘要/CSR 关键日志另汇总于 `sim/uart_irq/validation_20261005.log`。

## 8. 回归结果及边界

| 验证 | 本轮结果 | 日志 |
| --- | --- | --- |
| CPU IRQ ROM/DDR 取指 | 32/32 PASS | sim/uart_irq/build/*/sim.log，cpu*_results.json |
| 真实 UART RX IRQ | 2/2 PASS | 同目录 uart_rx_closed_loop* |
| UART TX | PASS，decoded12，814 clk/bit | sim/uart_tx/uart_tx.log |
| UART RX/FIFO/loopback | PASS，good75，frame1，overflow4（预期注错） | sim/uart_rx/uart_rx.log |
| UART MMIO 全部旧用例＋IRQ 扩展 | PASS，TX9、req/rsp8247、pop26；Errors0/Warnings0 | sim/uart_mmio/uart_mmio.log |
| 原真实 CPU UART polling | PASS，TX/RX Hello，poll2014；Errors0/Warnings0 | sim/uart_mmio/soc_uart_cpu.log |
| CPU ALU/memory/hazard 差分 | 3/3 PASS，寄存器/内存终值一致 | difftest/build/prog*/sim.log |
| 原 MMIO/data access-fault/inst access-fault | 3/3 PASS，153/445/193 cycles | difftest/build/*_e2e/sim.log |
| 原数据互连/DDR 桥 | PASS/PASS，旧未用端口 warning9/0 | sim/uart_mmio/tb_*bus*.log |
| DDR CPU 并发/背压 | 5/5 PASS，背压 ld_st PASS | sim/cpu_ddr_*_fast_*.log |
| DDR IP＋物理模型基线 | PASS，81.584 us，Errors0/Warnings357 | ipcore/ddr3/sim/modelsim/soc_ddr3_sim.log |
| DDR IP＋物理模型 regression | PASS，90.704 us，Errors0/Warnings357 | 同目录 soc_ddr3_regress_sim.log |
| DDR RV32I fast | supported 40/40 PASS；全量 40/42 | MyCpu_test/ddr_stage/fast_summary.csv |

`fence_i`、`ma_data` 仍输出既有 `tohost=00000539` known_gap，阶段 3 和早期 CPU 文档已记录；本轮未扩大范围修 CPU，不能报告全量 42/42 PASS。CPU/CSR 核心哈希未变。既有 Icarus -Wall 回归有继承 timescale 和禁用 DDR 未用输入 warning；厂家 DDR 原语和缩短初始化仿真有既有 warning。新 IRQ build 编译日志无 warning 输出；UART TX/RX/MMIO/CPU polling ModelSim 均 Errors0/Warnings0。

本次 UART IRQ 验收使用实际 SoC 与 DDR 用户口模型；完整 DDR 物理模型回归单独运行通过，没有把用户口模型说成 DDR PHY 中断联仿。没有进行综合、板级时序、下载或 USB-TTL 实测。当前主板级 DDR 自检保持原样，不会自动进入 UART ISR；IRQ 实板程序部署应另开步骤核对装载与链接地址。无 TX IRQ、嵌套、PLIC、DMA 或 bootloader。

## 9. Git 检查

在根目录实际执行 `git diff --check`、`git diff --stat`、`git status --short`，完整最终输出另保存在 `tmp/uart_irq_baseline/final_git_review.txt`（本地文件）。`git diff --stat` 只统计已跟踪文件，不含新增 TB、IRQ 仿真目录和本文；工作树还包含本轮开始前的顶层、PDS 输入和文档改动，不能把全部统计归因本轮。

最终 `git diff --check` exit_code=0；新增未跟踪源文件的行尾空白/结束换行另行扫描通过。全工作树已跟踪统计为 28 files changed, 260 insertions(+), 254 deletions(-)，包含已有改动与外部约束/PDS 会话更新；功能 RTL 本轮只有 soc_top（6+/2−）、uart_mmio（17+/4−），已有 tb_uart_mmio 为 38+/4−，新增文件单独列于第 2 节。

日志整理仅移除本次仿真输出行尾空白，保留全部结果和 warning 内容，确保 diff whitespace 检查通过。没有清理、reset 或覆盖无关文件；本轮没有 commit/push。
