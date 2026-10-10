# UART 顶层接入与 DebugCore 实板调试准备

日期：2026-10-05。目的：贯通现有 UART 的板级逻辑端口，准备观察真实 CPU/MMIO 发送链路。本轮没有执行任何 PDS Compile/Synthesis、Device Map、Place & Route、Generate Bitstream、IP Generate 或实板下载；没有新增 DebugCore/FIC，也没有添加 UART 物理引脚约束。

**顶层接线完成；主启动镜像未改，当前板上 DDR 自检程序仍不会发送 H。** 单字符测试停在候选软件说明，不能把此准备记录当作已部署 UART 输出或 DebugCore 实测 PASS。

## 1. 核对依据及范围

阅读 `AGENTS.md`、`README.md`、结构说明、`board_top.v`、`soc_ddr3_top.v`、`soc_top.v`、`data_bus_interconnect.v`、`uart_mmio.v`、`uart_tx.v`、`uart_rx.v`、`uart_rx_fifo.v`；核对 `RISCV.pds` 当前顶层与源文件、实际约束入口、DDR IDF/PHY 时钟生成、ROM/RAM IDF、`MyCpu_test/build_ddr_stage.py`、`build_ddr_selftest.py`、`prepare_board_selftest_ip.py`、板级 manifest 与现有 TB/Tcl。

DebugCore 操作依据本机官方 [Fabric Inserter V1.0 手册](C:/pango/PDS_2022.2-SP6.4/doc/Fabric_Inserter_User_Guide.pdf) PDF 第 24、26、31、35–36 页，以及 [Fabric Debugger V1.1 手册](C:/pango/PDS_2022.2-SP6.4/doc/Fabric_Debugger_User_Guide.pdf) PDF 第 26、31、36–37、71 页；检查了采样设置与 All Data 截图。当前安装版本为 PDS 2022.2-SP6.4，实际可选节点及控件仍须在本机 GUI 中确认。

进入本轮前 `RISCV.pds`、`impl.tcl`、`multiseed_summary.csv` 已有未提交的 PDS Compile 状态更新；本轮不覆盖、不清理、不提交这些更新。DDR IP 的参考为 125 MHz，PHY 中 `PPLL_IDIV=1`、`PPLL_FDIV=12`、`PPLL_ODIVPHY=2`，GPLL 的反馈/输出分频为 6/8；`ddrphy_sysclk → core_clk` 为 93.75 MHz。`board_top.CORE_CLK_HZ=93750000`；集成层保留的 100 MHz LED 参数默认值由 board_top 覆写，不是板级实际时钟。

## 2. 修改文件及直连

- `myriscv/board_top.v`：新增 `output wire uart_tx`、`input wire uart_rx`，接至 `soc_ddr3_top u_soc` 同名端口。
- `myriscv/soc_ddr3_top.v`：新增同名端口，将 `soc_top u_soc` 的 RX 接高/TX 空接改为直接传递。
- `source/tb_soc_ddr3_top.v`、`source/tb_soc_ddr3_pds_ip.v` 及 `sim/{board_main_selftest,board_main_selftest_candidate,board_key_boot_validation,board_top_validation}/tb_board_top_selftest.v`：仅将新增 RX 明确接 1，TX 空接，保留原测试功能。
- `source/tb_reset_button_debounce.v`：仅同步测试 stand-in 的两个端口，并将 board TB 的 RX 接高/TX 空接；stand-in 不是功能 UART 或综合源。
- `AGENTS.md`、`README.md`、`doc/SoC结构说明_2026-10-04.md` 和本记录：同步当前端口边界与调试说明；`.gitignore` 为本记录添加单项例外。阶段 3 PNG/SVG 保留为接线前的历史快照，当前说明已明确区分。
- 两条完整 DDR 回归日志随实际复跑更新；编译库、临时脚本/日志和 PDF 渲染保留本地或清理，不作为功能输入。

完整 TX 路径：

```text
board_top.u_soc.u_soc.u_cpu
  → soc_top 数据请求 → u_data_bus_interconnect
  → u_uart_mmio.req_* → u_uart_mmio.tx_send
  → u_uart_mmio.u_tx.tx_valid / tx_data
  → u_uart_mmio.u_tx.tx
  → u_uart_mmio.uart_tx → soc_top.uart_tx
  → soc_ddr3_top.uart_tx → board_top.uart_tx
```

完整 RX 路径：

```text
board_top.uart_rx → soc_ddr3_top.uart_rx → soc_top.uart_rx
  → board_top.u_soc.u_soc.u_uart_mmio.uart_rx
  → u_uart_mmio.u_rx.rx → 同步/接收 → u_fifo → RX_DATA
```

只是端口及接线，没有改变四个 UART 模块、CPU、互连、DDR 桥、DDR IP/PHY、时钟/复位或启动镜像。输入 RX 仍由已验证的 `uart_rx` 两拍同步。未接外部 UART 的实板 RX 不再内部常量接高，不能把仿真 TB 的 idle-high tie 当成实板电平保证；内部 TX 测试无需等待 RX 状态。

## 3. DebugCore 候选信号

以下为已核对的 **RTL 层次和别名**。没有运行新综合，因此不能保证综合后原名仍可直接选择。Inserter 可能使用 `/` 分隔、移除顶层名前缀、扁平化层次或合并别名；按实例/信号原名搜索并从来源寄存器/逻辑确认。

简写 `U = board_top.u_soc.u_soc.u_uart_mmio`：

| 目标 | 真实 RTL 路径 | 等价/备用搜索及含义 |
|---|---|---|
| tx_valid | `U.u_tx.tx_valid` | `U.tx_send`；被 MMIO 接受且 ready 的发送脉冲 |
| tx_ready | `U.u_tx.tx_ready` | `U.tx_ready`；复位释放且 TX 为 IDLE |
| tx_busy | `U.u_tx.tx_busy` | `U.tx_busy`；状态非 IDLE |
| tx_data[7:0] | `U.u_tx.tx_data[7:0]` | `U.req_wdata[7:0]`、`soc_top.uart_req_wdata[7:0]`；仅握手边沿有发送意义 |
| uart_tx | `U.u_tx.tx` | `U.uart_tx`；优先真实发送寄存器 Q/输出缓冲前的内部发送节点 |
| 已锁存字符 | `U.u_tx.data_latched[7:0]` | busy 期间保持本字符，握手后的采样应为 0x48 |
| MMIO 请求有效/接受 | `U.req_valid`、`U.req_ready`、`U.req_fire` | `soc_top.uart_req_valid/uart_req_ready`；不能仅看 write 判断已接受 |
| MMIO write | `U.req_write` | `soc_top.uart_req_write`；与有效及 ready 一起解释 |
| MMIO 相对地址 | `U.req_addr[31:0]` | `soc_top.uart_req_addr`；TX 写是 0，STATUS 读是 8 |
| CPU 完整地址 | `board_top.u_soc.u_soc.data_req_addr[31:0]` | `u_data_bus_interconnect.m_req_addr`；TX=0x10001000，STATUS=0x10001008 |
| MMIO wdata / strobe | `U.req_wdata[31:0]`、`U.req_wstrb[3:0]` | `soc_top.uart_req_wdata/uart_req_wstrb`；SB H 的 low byte=0x48，strobe=0001 |
| Clock / reset | `board_top.core_clk`、`board_top.soc_resetn` | `board_top.u_soc.core_clk/soc_resetn`；内部同域，93.75 MHz |

最小 Data 捕获为 valid/ready/busy 各 1 位、data 8 位、串行 TX 1 位，共 12 位。有余量加 `data_latched[7:0]`（20 位），再考虑 MMIO 请求。`tx_data` 是当前总线输入，不是发送期间稳定的字节，不能用发送中途的 tx_data 判定正在发哪个字符。

`tx_send/tx_valid` 可能与使能组合逻辑合并；ready/busy 可能互补合并；MMIO 高地址位可能常量优化；`tx_data` 可能只有 wdata 别名。输出 TX 的别名也可能合并，官方 Inserter 手册第 26 页对用户端口相连的网线另有选择限制，因此不能承诺 `board_top.uart_tx` 可探测。先寻找同一发送寄存器 Q 或缓冲前内部节点；若仍不允许连接，应停止并报告实际网表限制，不能用重算的假 TX 代替。

可辅助搜索 `U.u_tx.state`、`bit_count`、`bit_index`、`data_latched`；state 可能重编码，不能按 RTL 的 00/01/10/11 推断综合位编码。本轮没有加 keep/mark-debug 属性、复制寄存器、debug 输出或生成软件波形来替代功能逻辑。

## 4. Trigger、深度与 H 预期

首选同一接受周期触发：`tx_valid=1 && tx_ready=1 && tx_data[7:0]=8'h48`。若 valid 已被合并，使用等价 `tx_send=1`（其定义已包含 ready）；仍应同时捕获数据。只抓串行线时可用 TX 下降沿，但 H 内部也有下降沿，宜在首次 IDLE→busy 边界触发以避免从数据段开始。

采样时钟选真实 `core_clk`，上升沿，93.75 MHz，每拍存一个样本；Hardware Sample Rate 仅用于时间显示，也设 93.75 MHz。采用 Block RAM、单窗口、Sample Depth 至少 8192，关闭 Storage Qualification、捕获 All Data。不按 tx_valid 或 busy 过滤存储，否则相邻样本不再等于相邻 core_clk。

触发点建议设在 sample 0～32，例如 16，不能设为窗口中点 4096。8192 个样本仅比 8140 个发送周期多 52 拍；较多前触发样本会截掉停止位末端/ready 回升。若当前界面默认单窗口未开放 Position，使用触发点在首样本的设置；需要更长前触发历史则手动选 16384。握手触发采样可能先看到 idle high，下一拍看到 start/busy；给网表采样流水延迟留余量。

| 位段 | TX | 相对 start 起点的周期区间（右端不包含） |
|---|---|---|
| START | 0 | 0～814 |
| D0 | 0 | 814～1628 |
| D1 | 0 | 1628～2442 |
| D2 | 0 | 2442～3256 |
| D3 | 1 | 3256～4070 |
| D4 | 0 | 4070～4884 |
| D5 | 0 | 4884～5698 |
| D6 | 1 | 5698～6512 |
| D7 | 0 | 6512～7326 |
| STOP | 1 | 7326～8140 |

每 bit 为 814 拍、8.682667 µs，一字符 8140 拍、86.826667 µs。实际波特率 115171.990，误差 -0.024314%。START 与 D0/D1/D2 连成 3256 拍低电平，是 H 的正常结果；不能把长低脉冲误判成单 bit 时长错误。发送期间 busy=1/ready=0，完整 stop 后回 idle high/busy=0/ready=1。

单字符只发一次很容易在打开 Debugger 前已经结束：可以先在 Inserter 配置 PowerOn Init 触发并读取对应上电数据；读取前不要执行 Run/Stop/Trigger Immediate 使它失效。普通 Run 后按 KEY0 的方法需先确认 DebugCore 的 reset 连接不会同时取消已设置的采集、core_clk 会恢复且调试核能正常等待；本轮没有实板确认这种复位采集行为，不承诺 Run 后按键必然能抓到。

## 5. CPU 发 0x48 与启动镜像停止点

以下是候选 DDR 程序片段，仅作为后续镜像接入说明；尚未写入现有启动程序、RAM 镜像或 IP。占用 x5/x6/x7，不调用中断，不依赖 RX。应在独立候选 DDR 自检成功路径、最终 PASS/tohost 上报及停留循环之前加入，保留原自检与装载逻辑：

```asm
    lui  x5, 0x10001        # UART_BASE = 0x10001000
uart_h_wait_ready:
    lw   x6, 8(x5)          # STATUS
    andi x6, x6, 1          # TX_READY bit0
    beq  x6, x0, uart_h_wait_ready
    addi x7, x0, 0x48
    sb   x7, 0(x5)          # one TX_DATA request, low lane
uart_h_wait_complete:
    lw   x6, 8(x5)
    andi x6, x6, 1
    beq  x6, x0, uart_h_wait_complete
    # fall through to the existing PASS/tohost reporting and done loop
```

当前实际 `inst_rom.idf` 的 INIT_FILE 是 `MyCpu_test/board_selftest/boot_rom.dat`，`data_ram.idf` 是 `MyCpu_test/board_selftest/ddr_selftest.dat`。`build_ddr_stage.py:boot_program` 从 RAM 0x3FF0 读取复制字数，将 RAM 源装载到 DDR 0x40000000 后跳转；manifest 当前为 245 字。`build_ddr_selftest.py` 成功后上报 PASS/tohost 并 `jump("done")`，没有 UART 访问。

因此只改顶层不会让 CPU 自动发 H。真正部署必须改变当前自检 payload，并同步 RAM 末四字的 loader manifest、重新生成/核对 RAM IP 初始化；不能仅编辑 dat 就假设生成 RTL 初始内容已变化，也不能拿阶段 3 的直接 ROM Hello 仿真镜像替换板级 boot ROM。`prepare_board_selftest_ip.py` 连默认运行也会先重建 board_selftest 镜像，`--promote` 还会覆盖主 IP，本轮都未运行。

按用户的失败停止条件，镜像步骤已停止。后续需要单独批准/安排候选镜像工作：在独立目录生成加入上述 9 条指令的 payload，沿用同一 0x40000000 目标及原 boot ROM；核对长度不越过 0x40001000 诊断区、保留 TEST_STATUS 和 112 项 DDR 检查；核对 loader manifest（实际生成长度为准），生成独立 RAM IP，先用现有完整板级联仿自动验证装载、自检及串行 H，再决定替换主 RAM IP。当前主 ROM/RAM/IP 与启动文件均保持原样。

## 6. 本轮验证与未覆盖范围

验证只使用 ModelSim/Icarus，不执行 PDS。两条完整 DDR 定向已复跑：`soc_ddr3_sim.tcl` PASS，81584000 ps；`soc_ddr3_regress_sim.tcl` PASS，90704000 ps；两者 Errors: 0 / Warnings: 357，保持原厂家 warning 数量。

```powershell
Set-Location D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do soc_ddr3_sim.tcl; quit -f'
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'
```

板级检查复用 `sim/board_main_selftest/compile.tcl` 的真实 ROM/RAM、CPU、DDR IP/物理模型与现有 TB；临时 Tcl 仅运行 200 ns，逐层自动比较 board_top、soc_ddr3_top、soc_top、实际 TX 寄存器和 RX 输入均为 idle high。实测 `RESULT: PASS board UART elaboration, reset TX idle high and connected RX idle high (200ns only)`，退出码 0、Errors: 0 / Warnings: 353（厂家/原端口 warning），没有悬空 UART RX 输入。本检查未等待训练/启动或声称 CPU 已发 H。现有 Icarus `tb_board_key_reset` 同步测试 stand-in 端口后也 PASS，退出码 0。

实际命令（临时 Tcl 与日志只保留本地）：

```powershell
Set-Location D:/riscv/RISCV
& 'D:/modelsim/win64pe/vsim.exe' -c `
  -l D:/riscv/RISCV/tmp/uart_board_debug_20261005/board_boundary.log `
  -do 'do D:/riscv/RISCV/tmp/uart_board_debug_20261005/board_boundary.tcl'
& 'D:/iverilog/bin/iverilog.exe' -g2012 -Wall -DKEY_RESET_BOARD_STUB `
  -s tb_board_key_reset -o tmp/uart_board_debug_20261005/key_reset.vvp `
  myriscv/reset_button_debounce.v myriscv/board_top.v source/tb_reset_button_debounce.v
& 'D:/iverilog/bin/vvp.exe' tmp/uart_board_debug_20261005/key_reset.vvp
```

本轮不重跑完整长时板级自检，也不把短时端口检查称为新启动镜像 PASS。对保护范围的 51 份文件比较 SHA256，确认功能 UART/CPU/SoC/互连/桥、时钟复位、ROM/RAM IP及镜像、DDR 顶层/PHY/IDF、物理约束和原有三个 PDS 状态文件保持不变。`git diff --check` 用于检查本轮改动格式；未执行 stage/commit/push。

## 7. 用户下一步手动 PDS 操作

1. 在 PDS 打开现有 `RISCV.pds`，确认设计顶层 board_top、四个 UART 源已在列表中；源码接线是本轮改变，不依赖重新生成 DDR IP。
2. 手动 Compile/Synthesis，检查错误、latch、多驱动、时钟与 UART 是否保留；在有效综合网表上打开 Fabric Inserter，按第 3 节实例/信号搜实际节点并核对来源。本记录的 RTL 原名不是新综合网表存在证明。
3. 配置真实 core_clk、最小 Data Probe、触发输入、8192/单窗口/All Data/靠前触发点，保存与本次实现对应的 FIC。只有实际可选信号才加入；不要强行增加假 debug 功能 RTL。
4. 由用户手动执行 Device Map/插核、Place & Route、检查含核时序与资源，再决定 Generate Bitstream；本轮没有执行这些操作。若未约束 UART 端口被工具自动分配 I/O，不把自动位置当成板卡 UART pin。在生成/下载含新增 I/O 的位流前，先确认官方 Pin Map 或工具支持且已核实的仅内部调试处理方法；本记录没有提供安全的物理 UART pin。
5. 镜像候选尚未部署，当前自检只能用于检查原启动/训练；部署并验证单字符 H 的候选镜像后，使用与 FIC 对应的新位流，在 Debugger 通过 JTAG 抓取、按第 4 节时序检查，不把旧位流或仿真 Hello 当实板 H。
6. USB-TTL 到货且官方 pin/电平确认后再完成物理 TX/RX、交叉接线与共地验证。UART 电气、最终 I/O、DebugCore 插核后时序及实板波形均未在本轮覆盖。
