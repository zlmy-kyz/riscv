# RISCV 工程长期约定

本文件只放跨阶段仍适用的工程入口和约束。当前进度、最近 PASS/FAIL 和阶段验证细节记录在 `doc/`，不在本文件堆叠。

## 工程入口

- 根目录：`D:/riscv/RISCV`；PDS 工程：`RISCV.pds`。
- `myriscv/`：CPU 与 SoC RTL。`mycpu_sync.v` 是五级流水 CPU，具有分离的指令/数据类 SRAM 请求-响应接口；`soc_top.v` 连接两路互连、片内 ROM/RAM、`simple_mmio`、`uart_mmio` 和可选 DDR 桥；`soc_ddr3_top.v` 例化 `soc_top` 与 Pango `ddr3` IP。
- `myriscv/inst_bus_interconnect.v`、`data_bus_interconnect.v` 负责译码；`inst_bram_adapter.v`、`data_bram_adapter.v` 接片内 IP；`dual_sram_to_pango_ddr_bridge.v` 把两路类 SRAM 接口仲裁/转换到 Pango DDR 用户口。该用户口是 AXI-like，不能直接当标准 AXI4。
- `source/`：SoC、总线和 DDR 联仿 TB；`ipcore/`：PDS 生成的 ROM、RAM、DDR3 IP 与厂家例程；`MyCpu_test/dat/`：指令测试的 ROM 镜像，部分测试另有同名 RAM 镜像；`difftest/`：轨迹/异常等定向验证；`doc/`：设计与复现记录。
- 测试软件目录沿用development/与独立实验目录：tests/development为当前开发工作区；tests/fpga_uart_pc_output_30保存实板成功基准main.dat；tests/pc_uart_fpga_uart_pc保存Echo阶段实验。各实验根目录放main.c、对应功能.c/.h、启动/链接、build.ps1与转换器，build/放ELF/BIN/DAT；不使用tests/common或src分层。归档状态以各README为准，仿真PASS不能等同实板PASS。仿真环境、TB、模型、临时产物和日志留在sim/。上板使用Full Boot验收过的同一DAT，验收后不另生成DAT直接部署。

## SoC 层次与模块职责

- 当前板级层次为 `board_top → soc_ddr3_top → soc_top → mycpu_sync`；`RISCV.pds` 当前设计顶层为 `board_top`。设计顶层与仿真顶层分别核对，旧 `topcpu_instrom` 或 TB 的存在不能作为当前工程入口依据。
- `board_top.v` 负责板级引脚、`GTP_INBUFDS` 差分参考时钟缓冲、`GTP_CLKBUFG` 消抖时钟及 `reset_button_debounce`。KEY0 按下立即复位，释放稳定 20 ms 后解除；消抖使用参考时钟，不能改用复位期间可能停下的 DDR `core_clk`。
- `soc_ddr3_top.v` 例化 `soc_top u_soc`、`ddr3 u_ddr3` 和同文件内的 `soc_ddr3_leds u_leds`，并向 `soc_top` 设置 `ENABLE_DDR=1`。DDR `ddr_init_done && pll_lock` 经 `core_clk` 两拍同步后释放 `soc_resetn`。当前参考为 125 MHz，DDR IP 输出 `core_clk=93.75 MHz`；CPU、互连、片内存储、MMIO 和桥均在该域，LED 计时参数须与实际时钟一致。
- 指令路径：`mycpu_sync → inst_bus_interconnect → inst_bram_adapter → inst_rom`，或经译码进入共享 DDR 桥；数据路径：`mycpu_sync → data_bus_interconnect → data_bram_adapter → data_ram`，或进入 `simple_mmio` / `uart_mmio` / 共享 DDR 桥。片内 ROM 仅接指令总线，片内 RAM/MMIO/UART 仅接数据总线；DDR 内容由两条总线共同访问。
- `soc_top` 例化 `uart_mmio u_uart_mmio`，内部为 `uart_tx u_tx`、`uart_rx u_rx`、`uart_rx_fifo u_fifo`（16 字节）。UART 使用 93.75 MHz、115200 8N1、814 clk/bit、idle high、LSB first；`UART_CLK_HZ` 必须与实际输入时钟一致。TX/RX 通过 `soc_ddr3_top` 直连至 `board_top.uart_tx/uart_rx`；物理引脚约束必须另核官方原理图/Pin Map，逻辑接通不能据此认定 USB-TTL 实板通信可用。非 UART TB 把新增 RX 接 idle high。当前板级软件镜像和实板进度见 doc/CODEX_HANDOFF.md；DebugCore 准备与镜像停止条件见 `doc/UART顶层接入与DebugCore准备_2026-10-05.md`。
- `mycpu_sync` 的 IF/ID/EX/MEM/WB 流水寄存器及控制逻辑直接写在核内，子模块为 `regfile`、`alu`、`br_alu`、`l_alu`、`csr_file`。分支判定在 ID，访存请求在 EX 发射，MEM 等待响应，WB 写回及提交 CSR/异常事件；前递、load-use、等待和冲刷不可绕过。
- `dual_sram_to_pango_ddr_bridge` 当前一次处理一笔单拍 DDR 事务，两路同时请求时数据优先。`ddr3` IP 内主要子模块为控制器 `ips2l_mcdq_wrapper_v1_2b` 和 PHY `ddr3_ddrphy_top`；厂家 UART/BIST 例程及仿真物理模型不属于当前板级 SoC 路径。
- CPU 保留 external/software/timer 三路 IRQ；`board_top` 的三个外部输入仍接 0，`soc_top` 将原 external 输入与 `uart_mmio.uart_irq` 做 OR 后送 CPU。UART RX IRQ 为同 core_clk 域电平 `rx_irq_enable && !fifo_empty`，复位默认禁用；软件读空 FIFO 后自动撤销。软件轮询仍可用，当前无 TX IRQ、Cache、DMA、CLINT、PLIC 或 RK3568 通信接口。RTL/仿真接通不能等同于已有实板中断验证。
- 当前模块实例表、连接图及启动说明见 `doc/SoC结构说明_2026-10-04.md`（文件名保留首次建立日期，核对日期见文内）；UART 开发与验证记录见 `doc/UART_MMIO与CPU轮询阶段3_2026-10-05.md`。后续修改仍须以实际 RTL/PDS/IP 配置核对。

## 地址及硬件边界

- `soc_top` 默认 `RESET_PC=0`，`INST_ROM_BASE=DATA_RAM_BASE=RESET_PC`；两块存储器分挂指令、数据总线，各 16 KiB，可以在两条分离总线上同基址。TB 可覆盖复位地址，不能误认为 RTL 默认值也改变了。
- MMIO：`0x1000_0000` 起 4 KiB，当前 `simple_mmio` 寄存器偏移为 `0x0 SCRATCH`、`0x4 ID`、`0x8 CYCLE`、`0xC STATUS`、`0x10 TEST_STATUS`。自检状态 0/1/2/3 表示 IDLE/RUN/PASS/FAIL，PASS/FAIL 锁存至复位；LED 上报和超时约定见 `doc/LED状态指示与MMIO自检上报_2026-10-02.md`。
- UART：默认 `UART_BASE=0x1000_1000`，精确覆盖 `0x1000_1000–0x1000_100F`，基址须 16 字节对齐；偏移 `0x0 TX_DATA`（W）、`0x4 RX_DATA`（R）、`0x8 STATUS`（R）、`0xC CONTROL`（命令写，读 0）。STATUS bit0–5 为 TX_READY/TX_BUSY/RX_NOT_EMPTY/RX_FULL/FRAME_ERROR/RX_OVERFLOW；bit6 为 RX_IRQ_ENABLE，bit7 为使能后的 UART IRQ 电平。CONTROL bit0/1 清两种 sticky error，同周期新事件优先；bit8 写 1 使能 RX IRQ，bit9 写 1 禁用（同时写 1 时禁用优先），需要 write strobe lane1。写 0/原低字节 W1C 不改变 IRQ 使能。`soc_top` 启用 UART，独立 `data_bus_interconnect` 的 `ENABLE_UART` 默认 0；不要扩大译码窗口或改动原 MMIO/DDR 地址。
- UART 副作用仅在 `req_valid && req_ready` 接受边沿执行；RX_DATA 低字节地址读取锁存队首并 pop 一次，empty 返回 0 且不 pop，等待响应期间不能重复操作。低 lane TX_DATA 写仅在 TX_READY 时发送，busy 写丢弃新字节并返回既有总线 error；SB/SH/SW 须遵守移位数据和 write strobe，上 lane 访问不消费 RX、不启动 TX、不清错误，只有 CONTROL lane1 的 bit8/9 执行 IRQ 命令。软件应先轮询 STATUS，非法偏移/访问遵循既有 access-fault 机制。
- DDR CPU 窗口：`0x4000_0000` 起 512 MiB，只有 `ENABLE_DDR=1` 才启用；Pango IP 用户数据拍 128 位，桥在其中选择 32 位槽位并扩展写字节使能。DDR 用户地址按 16 位字计，不是 CPU 字节地址。
- 普通 `soc_top` 默认 `ENABLE_DDR=0`；DDR 集成版是 `soc_ddr3_top`。不要仅凭 IP 文件存在就认定当前 PDS 顶层已接入 DDR。
- 板级启动由 CPU 执行片内 ROM 的装载程序，将片内 RAM 中预置的程序复制到 DDR 后跳转执行；没有独立 DMA 装载器。ROM loader 入口在 `MyCpu_test/board_selftest/`，裸机 RAM 构建镜像位于各实验build/main.dat，实板成功归档另固定保存根main.dat，具体 `INIT_FILE` 以两块 IP 的 IDF 和生成初始化内容为准。更换镜像或 DDR 基址时，核对 ROM 装载目标、RAM 清单、程序链接地址、诊断/自检区及跳转入口的一致性，并重新生成相关存储 IP。

## 本机仿真工具与可复现命令

- ModelSim：`D:/modelsim/win64pe/vsim.exe`（本机 DE-64 10.6c）；PDS：`C:/pango/PDS_2022.2-SP6.4`。DDR Tcl 使用的 Pango 仿真库路径是 `C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation`，换机器需核对脚本的 `LIB_DIR`。
- 完整 DDR3 IP＋物理模型联仿须先进入 `D:/riscv/RISCV/ipcore/ddr3/sim/modelsim`，因为厂家 `sim_file_list.f` 使用相对路径。在 ModelSim Transcript 执行：

  ```tcl
  cd D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
  do soc_ddr3_sim.tcl
  do soc_ddr3_regress_sim.tcl
  ```

- 在 PowerShell 中也可从同一目录调用：`& 'D:\modelsim\win64pe\vsim.exe' -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'`；基线脚本同理。两个脚本各用独立库和日志。判断通过需同时检查相应 `RESULT: PASS`、无 `RESULT: FAIL`、ModelSim `Errors: 0`；厂家原语 warning 不必为零。
- PDS 默认行为仿真入口由 `RISCV.pds` 的仿真顶层及 `sim/behav/run_behav.bat`/`run_behav_*.tcl` 决定；它与上述独立 DDR 联仿不是同一个测试。运行 RV32I 镜像前，逐一核对 ROM/RAM 初始化文件和 TB 标注的测试名，不能只看写死的 PASS 文本。
- 改 CPU、互连、桥、DDR 顶层或共用 TB 后，至少重新运行两条 DDR 定向脚本，并按影响范围运行当前 `soc_top` 的 RV32I/异常等回归。记录脚本、日志路径、日期与结果；历史 PASS 不等于新代码 PASS。
- UART 仿真入口：在 `sim/uart_tx` 执行 `do run_uart_tx.tcl`；在 `sim/uart_rx` 执行 `do run_uart_rx.tcl`；在 `sim/uart_mmio` 执行 `do run_uart_mmio.tcl` / `do run_soc_uart_cpu.tcl`。CPU 测试先从根目录用 `python difftest/golden/rvtool.py asm sim/uart_mmio/uart_poll.S sim/uart_mmio/cpu_image` 生成独立仿真镜像。检查自动串行解码、结果比较、`RESULT: PASS`、无 FAIL 和 `Errors: 0`，不能只看波形；修改底层 UART 后重跑 TX 与 RX/FIFO/loopback，修改共享互连后还须运行 DDR、原 MMIO 和 access-fault 回归。
- 编译 `soc_top` 的脚本须包含 `uart_tx.v`、`uart_rx.v`、`uart_rx_fifo.v`、`uart_mmio.v`；未使用串口的 TB 将 RX 明确接 idle high，不能悬空。MMIO 或板级接线应沿用既有 UART 接口，避免无必要重写已验证的底层收发/FIFO。
- CPU IRQ/真实 UART IRQ 定向入口：根目录执行 `python sim/uart_irq/run_irq.py --stage cpu`，再执行 `--stage uart`；各加 `--ddr-code` 覆盖 DDR 取指，ISR 在片内 ROM。生成镜像仅在 `sim/uart_irq/build/`，不改板级 boot flow；`--case N --wave` 可保存单个 CPU 用例 VCD。修改中断相关连接/MMIO 后须重跑这些验收及 UART、CPU、DDR、access-fault 回归。结构、精确退休检查和未覆盖范围见 `doc/CPU中断验收与UART_RX_IRQ_2026-10-05.md`。
- UART Echo 在根目录执行 `python sim/uart_echo/run.py`，严格按 module → MMIO → CPU Echo → Full Boot 逐层PASS后继续；Full Boot直接读取 `tests/pc_uart_fpga_uart_pc/build/main.dat`，不自动重建。该入口的DDR是带背压/延迟用户口模型，不含PHY训练；完整DDR物理模型回归仍按上面的两条脚本执行。实板 Echo 在用户确认前只能记录待验证。

## 协作约束

- 工作树可能含未提交 RTL、PDS 生成文件、镜像、测试和日志；先检查 `git status`/`git diff`，不要清理、重置、覆盖不相关文件。特别是 `ipcore/` 和 `MyCpu_test/dat/` 不要凭名称当作可丢弃产物。
- DDR 训练完成、联仿 PASS、PDS 顶层已切换、实板验证是四个不同事实。DDR3 易失，正式运行 DDR 程序还需要明确装载来源和启动顺序。
- 每完成一个独立开发/验证步骤，在 `doc/` 记录目的、改动、复现命令、实测效果和未覆盖范围。若在文档中画图，可把生成的图片放在 `doc/` 并嵌入 Markdown 图片链接；板级结构说明见 `doc/SoC结构说明_2026-10-04.md`，历史 CPU/DDR 结构图见 `doc/CPU现状_2026-09-27.md`。
