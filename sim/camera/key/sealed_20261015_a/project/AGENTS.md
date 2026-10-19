# RISCV 工程长期约定

本文件只放跨阶段仍适用的工程入口和约束。当前进度、最近 PASS/FAIL 和阶段验证细节记录在 `doc/`，不在本文件堆叠。

## 工程入口

- 2026-10-15当前工作转为单目OV5640→DDR→CPU单帧校验，CPU性能优化暂停。用户确认DOUBLE-DVP载板/J10/CAM1-J4/本地24MHz XVCLK。相机首版RTL与Camera MMIO/CRC已接入，尚待本版PDS时序及功能验证；入口见`doc/CODEX_HANDOFF.md`顶部及`doc/camera/OV5640单目_DDR_CPU通路复用清单与Astra交接_2026-10-15.md`。当前MINI板级为x32/256bit、原生4字节地址单位，旧x16/128bit描述不适用于本板；新增相机DMA后帧区有明确缓存隔离。032成功基线和历史证据保留，本版不得继承032 PASS。用户负责PDS，时序通过后Sol准备关键测试，DeepSeek仅执行；本对话负责RTL/时序修复。

- 根目录：`D:/riscv/RISCV`；PDS 工程：`RISCV.pds`。
- `myriscv/`：CPU 与 SoC RTL。`mycpu_sync.v` 是五级流水 CPU，具有分离的指令/数据类 SRAM 请求-响应接口；`soc_top.v` 连接两路互连、片内 ROM/RAM、`simple_mmio`、`uart_mmio` 和可选 DDR 桥；`soc_ddr3_top.v` 例化 `soc_top` 与 Pango `ddr3` IP。
- `myriscv/inst_bus_interconnect.v`、`data_bus_interconnect.v` 负责译码；`inst_bram_adapter.v`、`data_bram_adapter.v` 接片内 IP；`dual_sram_to_pango_ddr_bridge.v` 把两路类 SRAM 接口仲裁/转换到 Pango DDR 用户口。该用户口是 AXI-like，不能直接当标准 AXI4。
- `source/`：SoC、总线和 DDR 联仿 TB；`ipcore/`：PDS 生成的 ROM、RAM、DDR3 IP 与厂家例程；`MyCpu_test/dat/`：指令测试的 ROM 镜像，部分测试另有同名 RAM 镜像；`difftest/`：轨迹/异常等定向验证；`doc/`：设计与复现记录，分类入口见 `doc/README.md`。
- `coremark-main/`：用户提供的CoreMark源包，保留算法源码与随包清单；独立裸机端口为`tests/coremark_baremetal/`，仿真入口为`sim/coremark/run.py`。当前状态以`doc/CODEX_HANDOFF.md`和`doc/coremark/CoreMark裸机构建与短迭代CRC_2026-10-07.md`为入口，源码核对见`doc/coremark/CoreMark源码核对与移植交接_2026-10-07.md`。短迭代CRC通过不能作为正式跑分或实板PASS。
- 测试软件目录沿用development/与独立实验目录：tests/development为当前开发工作区；tests/fpga_uart_pc_output_30保存实板成功基准main.dat；tests/pc_uart_fpga_uart_pc保存Echo阶段实验。各实验根目录放main.c、对应功能.c/.h、启动/链接、build.ps1与转换器，build/放ELF/BIN/DAT；不使用tests/common或src分层。归档状态以各README为准，仿真PASS不能等同实板PASS。仿真环境、TB、模型、临时产物和日志留在sim/。上板使用Full Boot验收过的同一DAT，验收后不另生成DAT直接部署。
- UART Loader独立实验在`tests/uart_loader/`，分层真实CPU仿真入口为`sim/uart_loader/run.py`，PC工具在`tools/uart_loader/`。片内指令ROM与数据RAM同址但分挂总线，Loader代码与常量必须分别构建ROM/RAM镜像，不能直接从当前数据RAM执行或合并成一个BIN。当前实现阶段与验收范围以`doc/CODEX_HANDOFF.md`和各README为准；候选不得自动替换主IP或成功Echo/CoreMark镜像。

## SoC 层次与模块职责

- 当前板级层次为 `board_top → soc_ddr3_top → soc_top → mycpu_sync`；`RISCV.pds` 当前设计顶层为 `board_top`。设计顶层与仿真顶层分别核对，旧 `topcpu_instrom` 或 TB 的存在不能作为当前工程入口依据。
- `board_top.v` 负责板级引脚、`GTP_INBUFDS` 差分参考时钟缓冲、`GTP_CLKBUFG` 消抖时钟及 `reset_button_debounce`。KEY0 按下立即复位，释放稳定 20 ms 后解除；消抖使用参考时钟，不能改用复位期间可能停下的 DDR `core_clk`。
- `soc_ddr3_top.v` 例化 `soc_top u_soc`、`ddr3 u_ddr3` 和同文件内的 `soc_ddr3_leds u_leds`，并向 `soc_top` 设置 `ENABLE_DDR=1`。DDR `ddr_init_done && pll_lock` 经 `core_clk` 两拍同步后释放 `soc_resetn`。当前参考为 125 MHz，DDR IP 输出 `core_clk=93.75 MHz`；CPU、互连、片内存储、MMIO 和桥均在该域，LED 计时参数须与实际时钟一致。
- 指令路径：`mycpu_sync → inst_bus_interconnect → inst_bram_adapter → inst_rom`，或经译码进入共享 DDR 桥；数据路径：`mycpu_sync → data_bus_interconnect → data_bram_adapter → data_ram`，或进入 `simple_mmio` / `uart_mmio` / 共享 DDR 桥。片内 ROM 仅接指令总线，片内 RAM/MMIO/UART 仅接数据总线；DDR 内容由两条总线共同访问。
- `soc_top` 例化 `uart_mmio u_uart_mmio`，内部为 `uart_tx u_tx`、`uart_rx u_rx`、`uart_rx_fifo u_fifo`（16 字节）。UART 使用 93.75 MHz、115200 8N1、814 clk/bit、idle high、LSB first；`UART_CLK_HZ` 必须与实际输入时钟一致。TX/RX 通过 `soc_ddr3_top` 直连至 `board_top.uart_tx/uart_rx`；物理引脚约束必须另核官方原理图/Pin Map，逻辑接通不能据此认定 USB-TTL 实板通信可用。非 UART TB 把新增 RX 接 idle high。当前板级软件镜像和实板进度见 doc/CODEX_HANDOFF.md；DebugCore 准备与镜像停止条件见 `doc/uart/UART顶层接入与DebugCore准备_2026-10-05.md`。
- `mycpu_sync` 的 IF/ID/EX/MEM/WB 流水寄存器及控制逻辑直接写在核内，子模块为 `regfile`、`alu`、`br_alu`、`l_alu`、`csr_file`。分支判定在 ID，访存请求在 EX 发射，MEM 等待响应，WB 写回及提交 CSR/异常事件；前递、load-use、等待和冲刷不可绕过。
- `dual_sram_to_pango_ddr_bridge` 当前一次处理一笔单拍 DDR 事务，两路同时请求时数据优先。`ddr3` IP 内主要子模块为控制器 `ips2l_mcdq_wrapper_v1_2b` 和 PHY `ddr3_ddrphy_top`；厂家 UART/BIST 例程及仿真物理模型不属于当前板级 SoC 路径。
- CPU 保留 external/software/timer 三路 IRQ；`board_top` 的三个外部输入仍接 0，`soc_top` 将原 external 输入与 `uart_mmio.uart_irq` 做 OR 后送 CPU。UART RX IRQ 为同 core_clk 域电平 `rx_irq_enable && !fifo_empty`，复位默认禁用；软件读空 FIFO 后自动撤销。软件轮询仍可用，当前无 TX IRQ、Cache、DMA、CLINT、PLIC 或 RK3568 通信接口。RTL/仿真接通不能等同于已有实板中断验证。
- 当前模块实例表、连接图及启动说明见 `doc/SoC结构说明_2026-10-04.md`（文件名保留首次建立日期，核对日期见文内）；UART 开发与验证记录见 `doc/uart/UART_MMIO与CPU轮询阶段3_2026-10-05.md`。后续修改仍须以实际 RTL/PDS/IP 配置核对。

## 地址及硬件边界

- `soc_top` 默认 `RESET_PC=0`，`INST_ROM_BASE=DATA_RAM_BASE=RESET_PC`；两块存储器分挂指令、数据总线，各 16 KiB，可以在两条分离总线上同基址。TB 可覆盖复位地址，不能误认为 RTL 默认值也改变了。
- MMIO：`0x1000_0000` 起 4 KiB，当前 `simple_mmio` 寄存器偏移为 `0x0 SCRATCH`、`0x4 ID`、`0x8 CYCLE`、`0xC STATUS`、`0x10 TEST_STATUS`。自检状态 0/1/2/3 表示 IDLE/RUN/PASS/FAIL，PASS/FAIL 锁存至复位；LED 上报和超时约定见 `doc/board/LED状态指示与MMIO自检上报_2026-10-02.md`。
- 性能计数器 2B 已并入 `myriscv/{mycpu_sync,soc_top,simple_mmio}.v`，`soc_top` 默认 `PERF_ENABLE=1`；原 MMIO 窗口内 `0x100–0x118` 为控制/状态，`0x140–0x1A4` 为13项64-bit冻结计数。统计口径见 `doc/cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md`，最新主RTL集成/回归及用户PDS重建状态见 `doc/CODEX_HANDOFF.md`。现有成功位流不会因源码改变而获得计数器，需用户重新实现并下载。
- UART：默认 `UART_BASE=0x1000_1000`，精确覆盖 `0x1000_1000–0x1000_100F`，基址须 16 字节对齐；偏移 `0x0 TX_DATA`（W）、`0x4 RX_DATA`（R）、`0x8 STATUS`（R）、`0xC CONTROL`（命令写，读 0）。STATUS bit0–5 为 TX_READY/TX_BUSY/RX_NOT_EMPTY/RX_FULL/FRAME_ERROR/RX_OVERFLOW；bit6 为 RX_IRQ_ENABLE，bit7 为使能后的 UART IRQ 电平。CONTROL bit0/1 清两种 sticky error，同周期新事件优先；bit8 写 1 使能 RX IRQ，bit9 写 1 禁用（同时写 1 时禁用优先），需要 write strobe lane1。写 0/原低字节 W1C 不改变 IRQ 使能。`soc_top` 启用 UART，独立 `data_bus_interconnect` 的 `ENABLE_UART` 默认 0；不要扩大译码窗口或改动原 MMIO/DDR 地址。
- UART 副作用仅在 `req_valid && req_ready` 接受边沿执行；RX_DATA 低字节地址读取锁存队首并 pop 一次，empty 返回 0 且不 pop，等待响应期间不能重复操作。低 lane TX_DATA 写仅在 TX_READY 时发送，busy 写丢弃新字节并返回既有总线 error；SB/SH/SW 须遵守移位数据和 write strobe，上 lane 访问不消费 RX、不启动 TX、不清错误，只有 CONTROL lane1 的 bit8/9 执行 IRQ 命令。软件应先轮询 STATUS，非法偏移/访问遵循既有 access-fault 机制。
- DDR CPU 窗口：`0x4000_0000` 起 512 MiB，只有 `ENABLE_DDR=1` 才启用；Pango IP 用户数据拍 128 位，桥在其中选择 32 位槽位并扩展写字节使能。DDR 用户地址按 16 位字计，不是 CPU 字节地址。
- 普通 `soc_top` 默认 `ENABLE_DDR=0`；DDR 集成版是 `soc_ddr3_top`。不要仅凭 IP 文件存在就认定当前 PDS 顶层已接入 DDR。
- 板级启动行为取决于实际 ROM/RAM 初始化镜像，不能固定理解为复制后跳转。旧自检/Echo/CoreMark 流程由 CPU 执行 `MyCpu_test/board_selftest/` 的 ROM 装载程序，将预置 RAM 程序复制到 DDR 后跳转；UART Loader 实验则从 ROM 常驻执行，数据 RAM 存放常量、状态、缓冲和栈，下载/校验/跳转能力以当前阶段验收为准。没有独立 DMA 装载器。具体 `INIT_FILE` 以两块 IP 的 IDF 和生成初始化内容为准，最新选择及成功镜像身份见 `doc/CODEX_HANDOFF.md`。更换镜像或 DDR 基址时，核对 ROM/RAM 分离布局、装载目标、链接地址、诊断/自检区及入口一致性；必须部署验收过的同一对 DAT，不能重建后未经重验直接上板。

## 本机仿真工具与可复现命令

- 用户2026-10-12进一步要求精简流程，覆盖2026-10-11每轮固定ISA抽测的约定：默认三步为“评估与单项RTL修改/审查 → DeepSeek关键仿真及Codex原始证据复核 → 用户PDS实现与实际DDR上板验收”。审查并入对应步骤，不单独安排多轮审查或重复测试；只评估、未改RTL时不运行仿真/PDS/上板。
- 性能优化默认只跑改动模块的一组关键定向仿真一次，复用已有成功基线，不例行重跑旧版对照、ISA、Hello、短CoreMark、九微基准或历史全套。TB/模型/判据发生变化且原基线不能直接复用时，才补一次相关旧版对照。CPU未修改时省去例行ISA抽测；CPU流水线/指令行为有改动时从支持且无已知缺口的用例中随机抽2个，记录种子和用例名，涉及具体指令/异常/中断再选该行为的最小定向用例。抽测PASS不写成全量ISA PASS。
- 用户2026-10-13进一步简化上板流程：DeepSeek任务由Codex复核原始证据通过后，直接给出上板/跑分命令、固定BIN、成功对照基线、新日志目录和KEY0步骤；不等待或例行核对PDS时序/资源/源文件/初始化/比特流，不以PDS审查收据或比特流哈希为上板工具前置门。PDS生成与新位流下载仍由用户完成；上板不成功或用户要求审查时，再按问题需要核对相关产物。收到实板日志后核验并分析性能，基于实测瓶颈继续推进下一轮单项性能提升；日志失败则先定位相关失败。未审查的PDS与未完成的实板不能记录PASS，历史成功证据保持。
- 实际DDR上固定BIN的CoreMark performance/validation各1轮，当前为同冻结Zmmul P300/V300。DDR握手或共享仲裁改变时补直接相关的最小集成测试，DDR IP/PHY/时钟改变时选择相关物理DDR测试，不默认两条物理脚本都跑。新失败仅补相关定位/复验，不扩成全量；无新改动/异常不要求重复测量。正式CoreMark成绩仍要求单次至少10秒，同BIN不足10秒仅记性能对比。仿真不能替代实际DDR性能验收。

- ModelSim：`D:/modelsim/win64pe/vsim.exe`（本机 DE-64 10.6c）；PDS：`C:/pango/PDS_2022.2-SP6.4`。DDR Tcl 使用的 Pango 仿真库路径是 `C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation`，换机器需核对脚本的 `LIB_DIR`。
- 完整 DDR3 IP＋物理模型联仿须先进入 `D:/riscv/RISCV/ipcore/ddr3/sim/modelsim`，因为厂家 `sim_file_list.f` 使用相对路径。在 ModelSim Transcript 执行：

  ```tcl
  cd D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
  do soc_ddr3_sim.tcl
  do soc_ddr3_regress_sim.tcl
  ```

- 在 PowerShell 中也可从同一目录调用：`& 'D:\modelsim\win64pe\vsim.exe' -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'`；基线脚本同理。两个脚本各用独立库和日志。判断通过需同时检查相应 `RESULT: PASS`、无 `RESULT: FAIL`、ModelSim `Errors: 0`；厂家原语 warning 不必为零。
- PDS 默认行为仿真入口由 `RISCV.pds` 的仿真顶层及 `sim/behav/run_behav.bat`/`run_behav_*.tcl` 决定；它与上述独立 DDR 联仿不是同一个测试。运行 RV32I 镜像前，逐一核对 ROM/RAM 初始化文件和 TB 标注的测试名，不能只看写死的 PASS 文本。
- 改CPU、互连、桥、DDR顶层或共用TB后，按上面的精简约定挑选相关关键用例，不再强制两条DDR脚本及全套RV32I/异常回归。记录选中用例、脚本、日志、日期、结果及未覆盖范围；历史PASS不等于新代码PASS。
- UART 仿真入口：在 `sim/uart_tx` 执行 `do run_uart_tx.tcl`；在 `sim/uart_rx` 执行 `do run_uart_rx.tcl`；在 `sim/uart_mmio` 执行 `do run_uart_mmio.tcl` / `do run_soc_uart_cpu.tcl`。CPU测试先从根目录用 `python difftest/golden/rvtool.py asm sim/uart_mmio/uart_poll.S sim/uart_mmio/cpu_image` 生成独立仿真镜像。检查自动串行解码、结果比较、`RESULT: PASS`、无FAIL和`Errors: 0`，不能只看波形；按改动选TX、RX/FIFO或MMIO副作用关键用例，未改UART不重复其底层回归，共享互连改动只补相关译码/access-fault用例。
- 编译 `soc_top` 的脚本须包含 `uart_tx.v`、`uart_rx.v`、`uart_rx_fifo.v`、`uart_mmio.v`；未使用串口的 TB 将 RX 明确接 idle high，不能悬空。MMIO 或板级接线应沿用既有 UART 接口，避免无必要重写已验证的底层收发/FIFO。
- CPU IRQ/真实UART IRQ定向入口：根目录执行 `python sim/uart_irq/run_irq.py --stage cpu`或`--stage uart`；加`--ddr-code`覆盖DDR取指，ISR在片内ROM。生成镜像仅在`sim/uart_irq/build/`，不改板级boot flow；`--case N --wave`可保存单个CPU用例VCD。只有修改相关中断/连接/MMIO时才选择相应用例，不默认运行完整32+2 IRQ及其他全套回归。结构、精确退休检查和未覆盖范围见`doc/cpu/CPU中断验收与UART_RX_IRQ_2026-10-05.md`。
- UART Echo入口为根目录 `python sim/uart_echo/run.py`；首次开发或修改该流程时按module→MMIO→CPU Echo→Full Boot定位验证，未受影响时不重跑整个链。Full Boot直接读取`tests/pc_uart_fpga_uart_pc/build/main.dat`，不自动重建。该入口DDR是带背压/延迟用户口模型，不含PHY训练；物理DDR测试按本节精简约定选择。实板Echo在用户确认前只能记录待验证。

## 协作约束

- 用户2026-10-14最新直接指令覆盖以下历史分工：另一个对话的GPT-6 Astra负责RTL设计、修改与时序修复；本对话的GPT-6.1 Sol负责仿真/测试要求、方案、TB、模型、独立参考、测试程序、执行/封存脚本、文档及原始证据复核；DeepSeek只执行已封存代码并保存完整命令/日志/轨迹和报告。DeepSeek不自行修测试代码或降低判据，测试问题交回Sol，已证实RTL问题及最小复现证据交给Astra。用户负责PDS、下载、KEY0与串口实板。保留“RTL修改→用户时序检查→时序通过后关键仿真→Sol复核→用户上板”的顺序。每轮只做改动相关的一组关键测试，已有成功证据复用；缺项只补最小相关用例，主动检查数据、握手、优先、背压、复位等RTL缺陷，不用PASS文字替代实际触发。本条不自动启动或向另一个对话发消息。

- 用户2026-10-14最新调整后续顺序：Codex修改RTL并做静态审查后，先由用户PDS重新实现检查时序；有违例则交回Codex继续修改，时序通过后才交DeepSeek实现/执行本版相关仿真与测试。覆盖历史“先仿真、后PDS”的顺序；此时PDS生成不等于功能验收，不直接上板跑分。DeepSeek结果经Codex原证据复核通过后再由用户下载/KEY0/串口实板测量。未收到用户时序通过结果，不派发本版仿真、不重复历史测试。分工保持下一条：Codex写要求/方案/判据，DeepSeek写测试代码并执行，Codex审原证据；用户询问现状不自动改成“Codex写全部测试代码”。

- 用户2026-10-14再次调整后续分工：Codex负责性能优化方案、RTL/软件、仿真与测试的要求和方案（范围、场景、刺激、独立参考要求、验收判据、输入身份和证据要求）、任务/阶段文档及原始证据复核；DeepSeek按方案编写或修改TB、仿真模型、独立参考、测试程序、执行脚本及输入封存代码，执行仿真与测试，保存完整命令/日志/轨迹并整理结果。DeepSeek可在任务要求范围内实现测试代码，不能自行修改设计RTL/PDS/IP/成功镜像或降低验收判据；需要调整方案时先交回Codex明确要求。用户继续负责PDS实现、下载、KEY0和串口实板操作。覆盖此前“Codex编写全部测试代码、DeepSeek仅执行”的分工；已经封存的当前任务沿其有效入口执行，后续新增测试开发或修复按新分工处理。
- 封存后从运行副本编译时，输入集合必须包含被编译源递归引用的Verilog include依赖（含`.vh`、`.svh`及IP的`*_init_param.v`），并在正式执行前确认副本目录的include路径闭合及厂家原语必需的顶层实例（如`GTP_GRS GRS_INST`）；不能只按编译命令中的模块源清单复制文件。DeepSeek依Codex方案落实封存与检查，Codex复核输入身份及原始证据。失败目录/冻结清单保持原身份，修复后绑定新清单和新运行目录，不倒填缺失原证据。
- `DeepSeek/` 存放仿真/测试要求、方案与结果模板。Codex写清设计版本/已有输入身份、测试范围、验收口径、执行入口要求和产物路径；DeepSeek实现相应测试代码，登记全部最终输入哈希、封存副本并按任务执行，Codex复核原始证据后更新正式结论。任务文件不会自动调用DeepSeek，默认不授权其修改RTL/PDS/IP/成功镜像、偏离或放宽既定判据，或执行PDS、实板、Git提交推送；额外范围须任务明确指定且符合用户授权。TB、模型、编译产物和完整日志仍留在`sim/`，没有输入变化不重复跑整套历史PASS。
- 结果交接后连续推进，按用户2026-10-13最新约定：收到DeepSeek任务结果，在同一步完成原始证据复核、记录更新并直接给上板步骤和跑分命令，不逐步询问是否继续；用户交来“PDS已生成/已下载”不触发例行PDS/位流审查。收到实板日志后继续核日志、分析性能、更新结论并推进下一轮单项优化。PDS实现、下载与KEY0/串口仍由用户执行；等待外部结果不记作已完成，不追加无关测试，未拿到本轮实测结果前不另起优化。
- 设计 RTL 直接维护在 `myriscv/` 已有 `.v` 中，不为新任务新增设计候选文件夹；根目录 `RISCV.pds` 使用这些设计文件。已迁入主设计的重复候选可按用户要求清理，成功快照与必要验证证据保留，新增仿真产物仍放 `sim/`。此用户约定优先于历史隔离设计目录流程。
- PDS 硬件实现流程由用户执行：工程编译、综合、器件映射、布局布线、时序报告及比特流生成。Codex负责RTL/软件修改、仿真准备及DeepSeek结果审查、上板命令和性能分析；PDS产物审查仅在上板失败需定位或用户明确要求时进行。除非用户明确要求，不启动PDS实现或生成比特流。上板下载及KEY0/串口实板操作仍由用户执行。
- 工作树可能含未提交 RTL、PDS 生成文件、镜像、测试和日志；先检查 `git status`/`git diff`，不要清理、重置、覆盖不相关文件。特别是 `ipcore/` 和 `MyCpu_test/dat/` 不要凭名称当作可丢弃产物。
- DDR 训练完成、联仿 PASS、PDS 顶层已切换、实板验证是四个不同事实。DDR3 易失，正式运行 DDR 程序还需要明确装载来源和启动顺序。
- 每完成一个独立开发/验证步骤，在 `doc/` 记录目的、改动、复现命令、实测效果和未覆盖范围；优先更新本轮同一阶段记录与交接，不为重复审查另建阶段文档或重复归档相同输入，保留必要源码/位流/BIN身份和原始日志。若在文档中画图，可把生成的图片放在 `doc/` 并嵌入 Markdown 图片链接；板级结构说明见 `doc/SoC结构说明_2026-10-04.md`，历史 CPU/DDR 结构图见 `doc/cpu/CPU现状_2026-09-27.md`。
