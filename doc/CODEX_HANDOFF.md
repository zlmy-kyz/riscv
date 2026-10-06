# RISCV SoC 开发交接

更新日期：2026-10-07（Asia/Shanghai）。工程根目录：`D:/riscv/RISCV`。

## GitHub同步准备与发布前复验（2026-10-07）

用户要求更新相关文件到GitHub。发布范围包括tests独立实验、成功镜像、C/Echo仿真
环境、UART引脚/RAM初始化配置及相关文档/实板截图；无关PDS运行状态和临时产物保留本地。
本次没有重编译或转换DAT，直接重跑ModelSim四层4/4 PASS，每层97字节，
Errors0/Warnings0；Echo构建DAT及根归档哈希保持不变。
验收ELF/BIN/DIS/DAT与结果/镜像凭据纳入发布，DAT以.gitattributes保留原字节。
实板结论仍来自此前用户确认，本次没有新增下载/实板测试。
范围、命令和核对记录见doc/UART_Echo_GitHub发布核对_2026-10-07.md。

## 最新反馈：Echo实板功能验收PASS，成功镜像已归档（2026-10-07）

用户已确认Echo位流下载、FPGA双向连线及拆除USB-TTL自身回环；在补充复位/重复
发送建议后进一步反馈“成功”，提交新截图，增加小写a和字母/数字/符号混合文本
对应回显，TX/RX累计均36字节。按用户操作反馈记录复位后重复通信成功，
Echo实板功能验收PASS；截图本身没有KEY0动作轨迹，复位结论来源于用户反馈。
不据此声称长时间无间隙压力、二进制、错误寄存器/注入或IRQ实板PASS。

原build/main.dat直接复制归档为tests/pc_uart_fpga_uart_pc/main.dat，
与输出30成功归档同样保留固定根DAT；本次没有重新构建/转换镜像。
根DAT与原build/main.dat逐字节一致，SHA-256均为
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20。
verified_image.json记录来源/验收范围，build.ps1不会覆盖根基准；
Full Boot和当前RAM IP仍使用原build/main.dat，没有改生产代码/IP/PDS或下载。
截图、两次用户确认及限制见doc/UART_Echo实板基本回显确认_2026-10-07.md。

下一阶段为PC→UART→DDR装载器：先规划装载器、目标程序和栈的互不覆盖地址区间，
做长度/目标地址检查、校验、ACK、超时与读回校验，再做跳转执行。尚未开始该阶段代码。
下方“复位待补齐/仅基本回显”的描述为前一轮快照，已由本条更新。

## 最新实板进展：Echo基本回显样本PASS（2026-10-07）

用户提交UartAssist截图，随后明确确认已下载Echo位流、USB-TTL连接FPGA并拆除
适配器自身回环。nb两次、小写a、hello 123（带空格）及符号/大小写混合文本都有
对应回显；第二张累计TX/RX均26字节。串口为115200/8N1/无流控。
当前可记录PC→FPGA→PC **实板基本回显样本PASS**，不是适配器自身短接回环。
完整记录及保存截图见doc/UART_Echo实板基本回显确认_2026-10-07.md。

本机当前data_ram的IDF/wrapper/IP TB三处INIT_FILE已引用
tests/pc_uart_fpga_uart_pc/build/main.dat；本地DAT哈希仍为
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20，与四层验收一致。
本次仅更新文档并保存截图，没有修改软件/RTL/TB/IP/PDS/镜像或运行构建/下载/仿真。
未保存本次下载位流哈希或原始串口捕获，不能独立核定其所有部署产物对应关系。

KEY0复位后重复、连续多组/长串、实板二进制/错误寄存器/IRQ尚未报告；
截图hello 123带空格，不能改写为已实测无空格hello123。建议补齐复位后A、hello123和
连续多组验收，再固定成功镜像/位流，进入PC→UART→DDR分块装载（尚未实现）。
下方“仅仿真/尚未上板”和“主RAM仍指向输出30”均为各步骤历史快照，已由本条更新。

## 最新目录修正：恢复development与成功归档，Echo迁移（2026-10-06）

用户要求恢复原tests结构，新增pc_uart_fpga_uart_pc放Echo内容；本条替代下方上一阶段
tests/common、src分层和uart_output_30/uart_echo测试目录约定。sim/uart_echo保持不动。

- tests/development：原输出30工作副本、README、uart_printf.c/.h、启动/链接/build.ps1
  和全部已有build产物原样恢复；不是将Echo自动覆盖到development。
- tests/fpga_uart_pc_output_30：原成功归档整目录恢复，根main.dat原字节不变；
  主RAM IP三处INIT_FILE恢复指向此根main.dat，生成初始化字未改。
- tests/pc_uart_fpga_uart_pc：迁入原Echo全部产物，源码放根main.c，功能代码配套
  uart_echo.c/.h，独立startup.S/linker.ld/build.ps1/bin_to_dat.py；不依赖common。
  最终Echo DAT改为tests/pc_uart_fpga_uart_pc/build/main.dat。
- 此前公共代码和输出30的重复新布局移至各build/previous_layout保护保存，不清理用户文件。

原成功输出30DAT仍为e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5；
Echo DAT仍为2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20。
Echo仅修改include/header guard和构建引用，独立脚本在sim build隔离重建核对BIN/DAT
与移动前逐字节一致，没有覆盖最终DAT。新路径ModelSim四层4/4 PASS，
每层97字节；CPU MMIO响应/退休LBU/写TX/引脚解码均一致。
输出30从恢复的归档路径重跑CPU UART验收PASS，Errors0/Warnings0。
Icarus新路径四层也4/4 PASS，保护/布局/.c/.h配对检查PASS，详见本次目录恢复记录；
不重复运行未改动的DDR PHY/RTL回归。
没有修改生产RTL/TB、PDS/FDC、RAM初始化字或下载；Echo仍仅仿真PASS、实板待验证。

从工程根目录：

```powershell
& ./tests/pc_uart_fpga_uart_pc/build.ps1
# 验收后不再重建另一个DAT直接上板
& C:/python/python.exe sim/uart_echo/run.py
```

README、仿真runner、旧C runner、AGENTS和主RAM IP引用同步恢复。
完整说明见doc/tests恢复旧结构与Echo实验迁移_2026-10-06.md。

## 上一阶段快照（其中测试目录/构建命令已由上条替代）

## UART Echo 分层仿真完成，实板待验证（2026-10-06）

用户要求在输出30已实板成功的基础上实现PC → FPGA → PC字节Echo。
当前软件/目录已完成，ModelSim和Icarus四层各4/4仿真PASS；Echo尚未上板，
不得记录Echo实板PASS。原输出30实板证据仍仅为用户此前“成功输出30”的反馈。

目录约定已替代旧development规则：

- tests/common：复用启动、链接、UART字节/精简printf、build.py、BIN→DAT转换。
- tests/uart_output_30/src/main.c及build/main.dat：输出30成功基准；原DAT直接保存，
  SHA-256仍为e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5。
  原development/旧归档及全部已有产物完整移至其build/legacy_development、legacy_archive，
  没有清理/丢弃用户工作。build.py重建只比较候选，不覆盖已验证DAT。
- tests/uart_echo/src/main.c及build/{main.elf,main.bin,main.dis,main.dat}：真实CPU轮询
  STATUS、LBU读RX_DATA、SB写TX_DATA；无提示文字、换行变换或IRQ，不是RTL pin回环。
- sim/uart_echo：唯一Echo分层仿真区；run.py、tb/tb_uart_echo.v、tb/echo_bram.v，
  build/uart_module、uart_mmio、cpu_echo、full_boot保存各层编译/仿真/临时产物。

最终Echo上板DAT（仿真直接读取此绝对路径，runner不编译/转换）：
`D:/riscv/RISCV/tests/uart_echo/build/main.dat`。
BIN为240字节/60字，DDR入口0x40000000、main=0x4000003c，初始SP=0x40010000；
BSS含echo_error/echo_count共8字节。DAT SHA-256为：

```text
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20
```

| 层 | ModelSim | Icarus | 验收 |
| --- | --- | --- | --- |
| UART RX/TX module | PASS | PASS | 输入/RX/FIFO字节/TX写值/TXD解码均97，最终空闲 |
| UART MMIO | PASS | PASS | 同上，97次RX读响应相等，响应延迟7拍，副作用仅一次 |
| CPU Echo | PASS | PASS | 真实CPU从DDR启动，97次退休LBU值/97次TX写值/97次解码一致 |
| Full Boot | PASS | PASS | 原ROM loader从RAM最终DAT搬60字到毒化DDR后执行，与CPU层同样字节闭环 |

刺激为A、hello123、九组连续hello123和00/11/…/FF二进制，共97字节。
115200/8N1/无流控，RXD按真实8.680556us位周期驱动，TXD独立start检测/中心采样/
LSB-first/stop检查/字节比较，末尾等待20个位时间检查重复输出。
无丢字节、重复、乱序、frame/overflow、CPU同步异常/IRQ、总线错误或超时；FIFO峰值1。
CPU软件echo_count=97、echo_error=0；Full Boot逐字检查loader地址/数据/strobe、
DDR payload、startup SP、BSS毒化后由startup清零及main退休。
ModelSim四层编译/运行Errors0、Warnings0。完整证据在
sim/uart_echo/build/{modelsim,iverilog}_results.json及每层对应.log；镜像凭据为
build/{modelsim,iverilog}_validated_image.json，仿真前后main.dat哈希不变。

复现（工程根目录）：

```powershell
# 仅在修改程序时先构建；构建后必须重新验收，验收后不再生成另一个DAT。
& C:/python/python.exe tests/common/build.py uart_echo
# 一条命令依次重跑所有四层，上一层PASS后才进入下一层。
& C:/python/python.exe sim/uart_echo/run.py
& C:/python/python.exe sim/uart_echo/run.py --simulator iverilog
```

本次没有修改任何myriscv生产RTL、RAM生成初始化字、ROM/DDR初始化、PDS/FDC或位流。
主RAM IP三处INIT_FILE仅从旧已移动路径更新为tests/uart_output_30/build/main.dat，
仍为输出30基准，没有推广Echo、运行PDS或下载。保护核对在
sim/uart_echo/build/layout_before.json、layout_verification.json。
输出30原C五项ModelSim回归因路径迁移重跑5/5 PASS。
完整DDR IP＋物理模型两条回归本轮按序均退出0、RESULT: PASS、无FAIL，
Errors0/Warnings357（store/load/fetch 81.584us，lanes/masks/boundary/DDR-code 90.704us）。
记录见doc/UART_Echo分层仿真与目录统一_2026-10-06.md和原DDR日志；这些原DDR测试
不使用Echo软件。Echo Full Boot采用同步BRAM及带背压/延迟DDR用户口模型，
不含DDR PHY训练、板级复位/电气或USB-TTL实板验证。

下一步由用户将上述同一个已验收main.dat用于RAM IP、重新生成IP、PDS实现/时序/
位流下载，完成实板接收回显。USB-TTL TXD→FPGA RXD，RXD←FPGA TXD，GND共地；
PC 115200/8N1/无流控，关闭本地回显和自动换行；发送hello123应收到hello123。
Echo无限运行且不写TEST_STATUS，原5秒LED watchdog可能超时，LED不是Echo验收依据。
用户确认前保持“仿真PASS、实板待验证”；后续UART分块装载/通用C ISR仍未实现。

## 下方历史快照（旧路径/目录规则已由上述最新接续替代）

历史目录规则（2026-10-06整理时）：`tests/development/` 曾是唯一当前测试程序开发区；
`tests/<其他目录>/` 是已完成验证的测试程序归档。tests只负责测试源码、启动/链接、
构建/转换和最终DAT，不负责RTL、testbench、DDR模型或仿真日志。
本次实板成功输出30归档在 `tests/fpga_uart_pc_output_30/`，其main.dat在重编译前
直接复制自成功镜像，SHA-256为
`e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5`。
复制前后完全一致，作为已验证基准固定保存；各build.ps1仅写各自build/，不会覆盖基准。
主RAM IP的INIT_FILE引用已改为归档main.dat，生成初始化字及生产RTL逻辑未变。
从development执行 `./build.ps1`，当前输出 `tests/development/build/main.dat`。
仿真仍在sim/baremetal_c；各目录README和
`doc/tests目录整理与成功镜像归档_2026-10-06.md`记录构建、迁移及验证。
以下历史段落中的路径已更新以便访问，但日期、当时程序大小/验证范围仍按原步骤理解。

后续进展（2026-10-06）：第 12.1 项已完成独立 C 装载/DDR 执行验收，ModelSim 与
Icarus 各 4/4 PASS，并验证非空 `.data/.bss`、LED PASS/FAIL/超时。
详见 `doc/裸机C_BIN到DAT与DDR_LED仿真验收_2026-10-06.md` 及
`sim/baremetal_c/README.md`。下文第 8/9/11/12 节保留交接时快照；其中 C
“尚无执行验证”的描述已由本补充更新。主板级镜像/IP/生产 RTL 仍未切换，未上板。

再后续（2026-10-06）：用户反馈USB-TTL已到货并通过Hello回环，且已手动将
data_ram初始化指向先前 `sim/baremetal_c/build/converted/main.dat`。
对应程序已归档，development中保留工作副本；提供精简printf输出 `30\r\n`，RAM基准为
`tests/fpga_uart_pc_output_30/main.dat`（680字节/170字），原ROM loader兼容。
ModelSim/Icarus各5/5 PASS，真实CPU/DDR执行且TX引脚自动解码30 CR LF通过。
本次没有修改用户当前主IP/PDS/FDC或下载，用户计划自己替换新DAT并上板。
详见 `doc/C裸机printf输出30与RAM镜像_2026-10-06.md`。

最新实板反馈（2026-10-06）：用户明确报告“成功输出30”，本次C镜像的
FPGA → USB-TTL → PC发送链路已获用户实板确认。没有独立位流哈希/串口捕获；
LED、重复复位、FPGA RX接收及UART IRQ实板结果尚未报告。本文下方的
“尚未到货/没有串口实测/尚未部署”等历史描述须结合本条更新阅读。

本文供新 Codex 对话直接接续开发，汇总本对话的结构分析、启动/通信方案和频率核对，并以交接时实际仓库核对后续已集成的 UART、IRQ 与裸机 C 构建。后续代码变动须重新核对，不能把历史 PASS 当成新代码 PASS。本次仅阅读代码、文档和已有日志并创建本文，没有重跑仿真/PDS、下载或修改功能代码。

## 1. 用户目标与开发边界

- 继续完善 FPGA 上的 RISC-V SoC，最终用于物体识别程序及模型计算；CoreMark 已交给别人负责，不要自行重新接管或联系对方。当前没有本对话可确认的 CoreMark 分数。
- 用户明确要求运行方案只能使用 FPGA，不能依赖 RK3568。早期讨论的 RK Linux、FSPI、PCIe 通信方案不作为当前实施方向。
- 用户 USB 转 TTL 已到货并通过 Hello 回环；2026-10-06 进一步反馈 FPGA 串口成功输出30。端子为 5V、3V3、TXD、RXD、GND；FPGA RX/IRQ 实板验证仍待开展。
- 当前优先把已有 UART 和真实 CPU 软件跑通、观察状态，再建立程序/数据装载方式。Cache、DMA、AI 加速器仍是后续规划。
- 遵守当前根目录 `AGENTS.md`。先检查 git status/diff，保留不相关改动，不 clean/reset，不凭文件名删除 IP、初始化内容或镜像。每个独立开发/验证步骤在 doc 记录命令、结果和未覆盖范围。
- 用户请求本次只生成交接文档；本文的后续建议不等于授权立即切换板级镜像、发布或提交其他文件。

## 2. 当前 Git 与工程状态

交接时分支 `master`，HEAD：`f42709275304d47b6159ae5d91bf7c8e671e4035`。

最近与功能相关提交：

| 提交 | 内容 |
| --- | --- |
| f427092 | Wire board UART ports and add verified RX interrupts：贯通板级 TX/RX、UART RX IRQ 及验收 |
| ee1e7f6 | Integrate polling UART MMIO and publish verified SoC diagrams：UART 阶段 1/2/3、数据互连、CPU 轮询、公开验证输入 |
| de3b16d | 仓库入口、构建和仿真工作流文档 |

创建本文前，`git status --short` 显示：

```text
 M RISCV.pds
 M constraint_check/temp_constraint_file.fdc
 M impl.tcl
 M multiseed_summary.csv
 D zongxian.md
?? constraint_check/constraint_backup/temp_constraint_file_2026_10_05_16_02_23.fdc
?? tests/
?? xpack-riscv-none-elf-gcc-15.2.0-1/
```

以上是接手前已有状态，不能归因于本次交接文档。不要恢复删除的 zongxian.md 或覆盖 PDS 会话改动。`impl.tcl` 是累计工具操作记录，含大量历史路径，不是从头重建入口。

`.gitignore` 忽略大部分 doc、旧 difftest、构建库/数据库/波形；本文当前也被 `/doc/*` 忽略，已实际保存但默认不会出现在普通 git status 中。用户没有要求本次提交/发布，也没有要求修改忽略规则。新对话在本机能直接读本文；若将来要克隆携带它，另行处理精确例外或明确添加文件。

## 3. 当前 SoC 结构与模块名称

PDS 主工程：`RISCV.pds`；器件 `PG2L100H`，`FBG484`，速度等级 `-6`。实际设计顶层 `board_top`，主行为仿真顶层 `tb_board_top_selftest`，两个入口要分别核对。

```text
board_top
  ├─ GTP_INBUFDS：125 MHz 差分参考时钟输入
  ├─ GTP_CLKBUFG + reset_button_debounce：参考域 KEY0 消抖
  └─ soc_ddr3_top u_soc
       ├─ ddr3 u_ddr3
       │    ├─ ips2l_mcdq_wrapper_v1_2b：DDR 控制器
       │    └─ ddr3_ddrphy_top：PHY/PLL/训练
       ├─ soc_ddr3_leds u_leds
       └─ soc_top u_soc
            ├─ mycpu_sync u_cpu
            │    ├─ regfile
            │    ├─ alu / br_alu / l_alu
            │    └─ csr_file u_csr_file
            ├─ inst_bus_interconnect
            │    ├─ inst_bram_adapter → inst_rom
            │    └─ 共享 DDR 桥指令端
            ├─ data_bus_interconnect
            │    ├─ data_bram_adapter → data_ram
            │    ├─ simple_mmio
            │    ├─ uart_mmio u_uart_mmio
            │    │    ├─ uart_tx u_tx
            │    │    ├─ uart_rx u_rx
            │    │    └─ uart_rx_fifo u_fifo（16 字节）
            │    └─ 共享 DDR 桥数据端
            └─ dual_sram_to_pango_ddr_bridge → ddr3 用户口
```

CPU 是核内直接实现 IF/ID/EX/MEM/WB 的五级流水。分支判定在 ID，EX 发访存请求、MEM 等待响应、WB 写回/退休并提交 CSR/异常。前递、load-use、等待、冲刷和中断排空均是现有行为，新增外设不得绕开。

指令和数据是分离的 SRAM-like 请求/响应接口。请求接受为 `req_valid && req_ready`；响应为 `rsp_valid/rsp_rdata/rsp_error`，当前无 rsp_ready。互连接受时锁存返回目标，单 outstanding，等待期间不能随 master 当前地址切换响应。

两个 BRAM adapter 适配片内 ROM/RAM IP 的同步时序，不是 DDR 模拟器；仿真 DDR 用户口模型与这两个 adapter 是不同对象。CPU 根据 PC 发字节地址，由指令互连译码决定 ROM 或 DDR，CPU 无需识别存储器种类。

DDR 桥处理一次一笔单拍事务，两路同时请求时数据优先；32 位 CPU 数据映射到 128 位用户拍的槽位和 byte enable。Pango 用户口是 AXI-like，不能套标准 AXI4；没有标准 WVALID/B/RREADY。用户地址按 16 位字计，CPU 地址按字节计，地址/掩码转换须沿用桥实现。

## 4. 时钟、复位和板级状态

- 参考时钟 125 MHz；生成 DDR IP 的系统 GPLL 为输入分频 1、反馈倍频 6、输出分频 8：`125 × 6 / 8 = 93.75 MHz`。
- `ddr3.v` 中 `core_clk = ddrphy_sysclk`；CPU、互连、ROM/RAM、MMIO、UART、桥和 LED 在此域。`CORE_CLK_HZ`/`UART_CLK_HZ` 是计时参数，改数字不会改变实际 PLL 时钟。
- `ddr_init_done && pll_lock` 在 core_clk 两拍同步后释放 soc_resetn。KEY0 按下立即复位，释放稳定 20 ms 后解除；消抖必须用参考时钟，不能用复位期间可能停下的 core_clk。
- `soc_top` 默认 ENABLE_DDR=0；`soc_ddr3_top` 显式启用 DDR。不要把独立 soc_top 仿真默认配置当成板级配置。
- LED：J16 心跳约 1 Hz，M17 表示 DDR ready/SoC 释放复位，K17 自检 IDLE 灭、RUN 慢闪、PASS 常亮、FAIL/超时快闪。5 秒超时是指示逻辑，不等于 CPU 自动复位。

频率核对有两个不同日期的结果：

| 报告 | core_clk 请求频率 | 同域时序估计最高频率 | Setup 余量 |
| --- | --- | --- | --- |
| 本对话 10-04 13:55:43 所读旧报告 | 93.75 MHz | 96.1571 MHz | 0.267 ns |
| 交接时当前 report_timing/board_top.rtr，10-05 22:46:27 | 93.75 MHz | 96.8462 MHz | 0.341 ns |

当前报告为 multi corner、显示 All Constraints Met，Slow/Fast 已分析 setup/hold 无违规；Fast 同域 hold 余量 0.102 ns。它是当前实现时序估计，不是 CPU 独立固定上限或实板升频结果。旧最慢路径由 data_ram 输出经数据互连、CPU 前递、分支比较及取指控制至 PC CE；更改 RTL/探针/布局后须重新确认路径，不能沿用旧瓶颈结论。

当前本地 `place_route/run.log` 记录 10-05 22:40:22 布局布线成功；`generate_bitstream/run.log` 记录 22:50:25 生成成功，存在 `generate_bitstream/board_top.sbit`（3791112 字节）。报告中含 DebugCore 时钟，PDS 输入有 `synthesize/board_top_syn.fic`。这些本地生成产物不在日常 Git 发布范围；尚无本对话可确认的该版本下载、Debugger 捕获或 USB-TTL 实测。UART/复位/DDR 等外部端口仍有未约束 warning，All Constraints Met 仅涵盖实际分析的约束路径。

## 5. 地址、启动和 DDR 内容来源

| 区域 | CPU 字节地址 | 边界 |
| --- | --- | --- |
| 指令 ROM | 0x00000000–0x00003FFF | 16 KiB，仅指令总线 |
| 数据 RAM | 0x00000000–0x00003FFF | 16 KiB，仅数据总线；与 ROM 同址但不同总线 |
| simple_mmio | 0x10000000–0x10000FFF | 4 KiB 原窗口 |
| UART | 0x10001000–0x1000100F | 精确 16 字节，基址 16 字节对齐 |
| DDR | 0x40000000–0x5FFFFFFF | 512 MiB CPU 窗口，需启用 DDR |

simple_mmio 偏移：0 SCRATCH、4 ID、8 CYCLE、C STATUS、10 TEST_STATUS。TEST_STATUS 为 0/1/2/3=IDLE/RUN/PASS/FAIL，PASS/FAIL 锁存至复位。MMIO CYCLE 是 32 位周期计数，93.75 MHz 下约 45.81 秒回绕；当前不能假设已具备完整 mcycle/minstret 计时。

板级 boot flow 保持：DDR 训练完成 → CPU 从 ROM 地址 0 开始 → 从片内 RAM 清单得长度 → CPU load/store 复制 payload 到 DDR 0x40000000 → 跳转 DDR 执行。没有独立 DMA 装载器。

实际 IP INIT_FILE 已核对：

- inst_rom：`MyCpu_test/board_selftest/boot_rom.dat`。
- data_ram：`MyCpu_test/board_selftest/ddr_selftest.dat`。
- 清单为 `MyCpu_test/board_selftest/manifest.tsv`，不是 manifest.json；RAM 末 4 字保留 loader manifest（0x3FF0 起），当前 payload 245 字。镜像构建入口 `MyCpu_test/build_ddr_stage.py`、`build_ddr_selftest.py`。
- 当前 DDR 自检程序仍未访问 UART，不会自动发 H、Hello 或进入 UART ISR。阶段 3 Hello 程序仅是独立仿真镜像。
- 自检使用 DDR 0x40001000 诊断区、0x40002000 scratch；替换 payload 必须重新核对代码、数据、诊断、栈与清单边界。原 payload 长度不能占用诊断区。
- 编辑 DAT 不保证 IP 生成初始化已同步，必须核对 IDF 和实际生成初始化内容，必要时重新生成相关存储 IP。`prepare_board_selftest_ip.py` 默认也会重建镜像，`--promote` 会覆盖主 IP，不要误当只读检查运行。

关于大程序/模型：ROM 容量小则保留精简启动程序；DDR 易失，需要真实装载来源。现有 RAM staging 有约 16 KiB 的总容量限制，不能靠跳转 DDR 自动解决来源问题。将来可从 PC UART 分块接收，CPU 从 FIFO 搬到 DDR，或增加经核对的 FPGA Flash 装载器；这两种正式 loader 均未实现。模型权重、图像、计算缓冲可布局在 DDR，但当前没有既定的生产地址规划、模型导入程序、图像接口或内存管理器。

## 6. UART 已完成的功能与接口约定

已实现独立 TX、RX、16 字节 RX FIFO；MMIO 接入数据互连；真实 CPU 软件轮询；板级 TX/RX 逻辑直连；RX 电平 IRQ 接入 CPU。

- 115200、8N1、idle high、LSB first；93.75 MHz 下取 814 clk/bit，实际 115171.990 baud，误差约 -0.024314%。每帧 8140 拍。
- RX 两拍同步，验证假起始过滤、停止位错误/恢复、异步相位和 ±2% 波特率。错误帧不入 FIFO。
- FIFO 队首组合读（FWFT），empty 返回 0；满且无 pop 时拒绝新字节并报 overflow；满同时 pop/push 可保持深度并接受新字节。底层 error/overflow 是事件，MMIO 负责 sticky 锁存。

| 偏移 | 寄存器 | 当前语义 |
| --- | --- | --- |
| 0x0 | TX_DATA（W） | 低 lane 写入字节；ready 才发送；busy 误写返回既有总线 error，不破坏当前帧 |
| 0x4 | RX_DATA（R） | 合法低字节地址读在接受边沿锁存队首并 pop 一次；empty 返回 0 不 pop |
| 0x8 | STATUS（R） | bit0 TX_READY、1 TX_BUSY、2 RX_NOT_EMPTY、3 RX_FULL、4 FRAME_ERROR、5 RX_OVERFLOW、6 RX_IRQ_ENABLE、7 UART IRQ；31:8=0 |
| 0xC | CONTROL（命令写，读0） | bit0/1 W1C 清 frame/overflow；bit8 写1使能 RX IRQ，bit9 写1禁用，同写禁用优先 |

所有副作用仅在 req_valid && req_ready 执行；等待响应期间不能重复 pop/send/clear。SB/SH/SW 遵守 CPU 移位 wdata/strobe。TX 和 W1C 要 lane0；CONTROL IRQ 命令要 lane1。上 lane RX 访问不消费字节；无效方向/size/非对齐访问/窗口外遵循已有 access fault。新 error 事件与 W1C 同拍时事件优先。CONTROL 写0或只写旧 W1C 不改变 IRQ 使能。

IRQ：`uart_irq = rx_irq_enable && !fifo_empty`，复位禁用，与 generic irq_external 做 OR 送 CPU external。FIFO 读空即撤销；禁用不清 FIFO。board_top 的原三路外部 IRQ 输入仍接0。UART IRQ 在 core_clk 域，不需额外 CDC，不能用 rx_valid 脉冲代替电平。

CPU 原有 machine IRQ：mip MEIP/MSIP/MTIP，mie 掩码0x888，全局 mstatus.MIE；优先级 external→software→timer。排空已发射流水和已接受数据事务后以退休边界 arch_next_pc 入中断；同步异常优先；mepc/mcause/mtval、MIE/MPIE、Direct mtvec 和 MRET 已有机制。本阶段未修改 CPU/CSR。软件还需配置 mtvec、mie.MEIE 和 mstatus.MIE；UART 使能本身不等于 CPU 已开启中断。

## 7. 修改/新增文件交接索引

下面区分功能改动和测试/工程依赖；不是把整个仓库历史都归为本对话修改。

| 文件或目录 | 已完成内容 |
| --- | --- |
| myriscv/uart_tx.v、uart_rx.v、uart_rx_fifo.v | 新 UART 底层；后续 MMIO/IRQ 复用，未重写 |
| myriscv/uart_mmio.v | MMIO、pending 响应、sticky/W1C、FIFO pop；后续新增 IRQ enable/输出 |
| myriscv/data_bus_interconnect.v | 新 UART 精确译码/请求转发/锁存响应目标；target 位宽由2到3，旧目标保持 |
| myriscv/soc_top.v | 例化 UART、连接互连及串口，UART IRQ OR 接 CPU external |
| myriscv/soc_ddr3_top.v、board_top.v | TX/RX 顶层直连；其他时钟/复位/boot flow 保持 |
| source/tb_uart_tx.v、tb_uart_rx.v | 串口独立激励/解码、FIFO/环回测试 |
| source/tb_uart_mmio.v、tb_soc_uart_cpu.v | 总线副作用、地址/strobe/error、真实 CPU Hello 轮询 |
| source/tb_soc_irq.v、sim/uart_irq/* | 16 个 CPU IRQ 场景、真实 UART ISR 闭环及独立退休检查 |
| source/tb_data_bus_interconnect.v、tb_ddr_bus_path.v、tb_soc_top.v、tb_soc_ddr3_rv32i_fast.v | 新端口兼容，非 UART RX 接高 |
| source/tb_soc_ddr3_top.v、tb_soc_ddr3_pds_ip.v、tb_reset_button_debounce.v；sim/board_* 的板级 TB | 同步顶层端口，原功能保留 |
| sim/uart_tx/、uart_rx/、uart_mmio/ 的 Tcl 与日志 | ModelSim 独立运行入口和精选证据；uart_poll.S 是仿真软件 |
| sim/uart_mmio/uart_synth/ | UART 模块独立 PDS 综合输入/主要日志 |
| ipcore/ddr3/sim/modelsim/soc_ddr3_{sim,regress_sim,rv32i_sim}.tcl | 增加 UART 编译依赖；前两项日志随回归更新 |
| MyCpu_test/run_ddr_rv32i_fast.py、run_cpu_ddr_overlap_fast.py | 增加 UART 编译依赖 |
| sim/pds_ddr_{selftest,ip,reset}_compile.tcl、sim/board_*/compile.tcl | 当前共享 SoC 编译依赖更新 |
| 本地 difftest/run*.ps1 与 difftest/tb/* | UART 编译/idle RX 兼容；大部分仍被忽略，完整新克隆未必存在 |
| difftest/golden/rvtool.py、model/inst_rom.v、data_ram.v | 已公开的 UART/IRQ 仿真必要依赖 |
| tests/development/main.c、startup.S、linker.ld、build.ps1 | 当前未跟踪的裸机 C 构建，见下一节 |
| AGENTS.md、README.md、.gitignore、精选 doc/结构图与绘图源 | 同步工程入口、UART 接口、验证和发布依赖 |

本对话早期新增/维护了 SoC结构说明、CoreMark准备、总线评估、RK接口核对和 CPU工作频率核对记录；部分仅本地保存。后续仓库精选文档包含 UART 阶段1/2/3、顶层DebugCore准备、CPU中断验收和结构 PNG/SVG。结构图文件名是阶段3快照，最新 IRQ/板级连接以 RTL 和本文为准。

## 8. 裸机 C 构建现状（交接时新增的本地工作）

工程内已存在 `xpack-riscv-none-elf-gcc-15.2.0-1/bin`，不能继续使用早期“本机没有 RISC-V GCC”的结论。`tests/development/build.ps1` 通过本地路径构建，不依赖全局 PATH。

- `-march=rv32i -mabi=ilp32 -O2`，freestanding、nostdlib/nostartfiles、禁 relax，链接 -lgcc，未链接 libc。
- startup 设置 gp/sp、清 word 对齐 BSS、调用 main，返回则循环；未配置 CSR/中断/异常。
- linker：DDR 起点0x40000000、测试使用64 KiB，顶部4 KiB栈，初始sp=0x40010000；.data LMA=VMA，由 loader 放最终地址；BSS NOLOAD 由 startup 清零。这不是整个 SoC 的永久 DDR 分区。
- 当前 main 是 volatile a=10、b=20、c=a+b 后无限循环，无 UART/TEST_STATUS 上报。包含 stdio.h 不等于支持 printf。
- 已有构建记录和产物：ELF32 小端 RISC-V EXEC，入口0x40000000、rv32i2p1，text=100/data=0/bss=0，BIN100字节；静态反汇编无 M/C/F/A 指令。编译有 c 未读取、链接 RWX LOAD warning。
- 静态推导 main=0x4000003C、最终循环=0x40000060，a/b/c 在0x4000FFF4/FFF8/FFFC，预期10/20/30；尚无运行内存实测。当前 BSS/data 为空，不能宣称这两项初始化已运行验证。
- ELF/BIN 未转换为现有 DAT/清单或接入启动镜像。没有 C 执行仿真或实板 PASS。后续需要独立镜像转换和真实 CPU 验收，再考虑板级部署。

## 9. 已完成测试及实际结果

以下为已存日志/2026-10-05 验证记录，交接时查读而非本次重跑。最主要原始证据可直接读对应日志。

| 测试 | 已完成结果 | 证据路径 |
| --- | --- | --- |
| UART TX | PASS，解码12帧、814 clk/bit，Errors0/Warnings0 | sim/uart_tx/uart_tx.log |
| UART RX/FIFO/loopback | PASS，good75、预期注错frame1/overflow4，writes71/reads70，Errors0/Warnings0 | sim/uart_rx/uart_rx.log |
| UART MMIO + IRQ扩展 | PASS，TX9、req/rsp8247、pop26，Errors0/Warnings0 | sim/uart_mmio/uart_mmio.log |
| 真实 CPU polling Hello | PASS，SB/SH/SW TX、LBU/LB/LHU/LH/LW RX，poll2014，Errors0/Warnings0 | sim/uart_mmio/soc_uart_cpu.log |
| CPU IRQ专项，ROM与DDR取指 | 16场景×2=32/32 PASS；精确退休PC、trap CSR、MRET、访存不重放 | sim/uart_irq/validation_20261005.log；build下逐例sim.log/results.json |
| 真实引脚RX→FIFO→IRQ→ISR→MRET | ROM/DDR共2/2 PASS；pin10/pop10、ISR/MRET4、FIFO峰值5，DDR写一次 | 同上，uart_rx_closed_loop* |
| 原CPU ALU/memory/hazard差分 | 3/3 PASS，终值一致 | 本地 difftest/build/prog*/sim.log |
| 原MMIO/data fault/inst fault | 3/3 PASS，153/445/193 cycles | 本地 difftest/build/*_e2e/sim.log |
| 数据互连/DDR桥 | PASS/PASS，Errors0，原未用端口warning9/0 | sim/uart_mmio/tb_data_bus_interconnect.log、tb_ddr_bus_path.log |
| CPU DDR并发与背压 | 5/5 PASS，背压ld_st PASS | sim/cpu_ddr_*_fast_*.log；runner控制台记录 |
| 完整DDR IP+物理模型基线 | PASS store/load/fetch，81.584 us；Errors0/Warnings357 | ipcore/ddr3/sim/modelsim/soc_ddr3_sim.log |
| 完整DDR IP+物理模型定向 | PASS lanes/masks/boundary/DDR-code，90.704 us；Errors0/Warnings357 | 同目录soc_ddr3_regress_sim.log |
| DDR RV32I fast | supported40/40 PASS；全量40/42 | MyCpu_test/ddr_stage/fast_summary.csv |
| 板级UART端口200 ns检查 | PASS idle-high及逐层连接；未等待训练/启动，Errors0/Warnings353 | 本地tmp/uart_board_debug_20261005/board_boundary.log |
| KEY0 board stand-in测试 | PASS；不是DDR真实长时板级测试 | 同目录key_reset.vvp相关记录 |
| UART独立PDS综合 | Compile/Synthesize退出0、无E、latches0；133条既有/未约束等warning | sim/uart_mmio/uart_synth/run.log |
| 当前本地整板PnR/时序/bitstream | 已有成功日志，时序已分析路径满足；未实板确认 | place_route/run.log、report_timing/board_top.rtr、generate_bitstream/run.log |
| 裸机C编译/链接 | 构建退出0、ELF/BIN属性核对；未执行CPU | tests/development/build/* 与本地构建文档 |

IRQ用户口模型测试涵盖 DDR背压/延迟，不是 DDR PHY IRQ物理联仿；完整物理模型回归单独PASS。CPU验收包括mask、store/load/MMIO等待和响应边界、同步异常优先、IRQ撤销/持续、三路优先级，独立退休模型计算mepc，不能用DUT内部arch_next_pc作为期望值。

UART 发布前还从 Git index 导出65份输入到独立目录、重新生成仿真镜像，四项UART和两项总线测试PASS，确认公开文件依赖完整。完整旧difftest未发布；不能承诺仅新克隆即可运行所有本地旧回归。

## 10. 复现命令与工具

本机工具：ModelSim `D:/modelsim/win64pe/vsim.exe`；PDS `C:/pango/PDS_2022.2-SP6.4`；Icarus `D:/iverilog/bin/{iverilog.exe,vvp.exe}`；Python实际可用 `C:/python/python.exe`。

先从根目录检查状态/源码。下面按需运行，不能把列表理解为每次写说明文档都要重跑全部测试。

```powershell
Set-Location D:/riscv/RISCV
git status --short
git diff --stat
Get-Content AGENTS.md

# CPU polling独立镜像，不改板级IP
& C:/python/python.exe difftest/golden/rvtool.py asm sim/uart_mmio/uart_poll.S sim/uart_mmio/cpu_image

# IRQ专项与真实串口闭环；可加 --case 5 --wave 保存单例
& C:/python/python.exe sim/uart_irq/run_irq.py --stage cpu
& C:/python/python.exe sim/uart_irq/run_irq.py --stage cpu --ddr-code
& C:/python/python.exe sim/uart_irq/run_irq.py --stage uart
& C:/python/python.exe sim/uart_irq/run_irq.py --stage uart --ddr-code

Set-Location D:/riscv/RISCV/sim/uart_tx
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_tx.tcl; quit -f'
Set-Location D:/riscv/RISCV/sim/uart_rx
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_rx.tcl; quit -f'
Set-Location D:/riscv/RISCV/sim/uart_mmio
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_mmio.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_soc_uart_cpu.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_bus_regression.tcl; quit -f'

# 完整DDR两条须在此工作目录依次运行，相对file list不能换目录
Set-Location D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_sim.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'

Set-Location D:/riscv/RISCV
& C:/python/python.exe MyCpu_test/run_ddr_rv32i_fast.py
& C:/python/python.exe MyCpu_test/run_cpu_ddr_overlap_fast.py
& C:/python/python.exe MyCpu_test/run_cpu_ddr_overlap_fast.py --backpressure

# 本地完整旧difftest存在时才能运行以下命令
powershell -NoProfile -File difftest/run.ps1 -Prog prog0_alu
powershell -NoProfile -File difftest/run.ps1 -Prog prog1_mem
powershell -NoProfile -File difftest/run.ps1 -Prog prog2_hazard_precision
powershell -NoProfile -File difftest/run_mmio.ps1
powershell -NoProfile -File difftest/run_access_fault.ps1
powershell -NoProfile -File difftest/run_inst_access_fault.ps1

# 裸机C：仅生成产物，不部署
& ./tests/development/build.ps1
```

DDR Tcl `LIB_DIR` 为 `C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation`。通过标准：出现对应 RESULT: PASS、无 RESULT: FAIL、ModelSim Errors:0；厂家warning无需0，但应与基线比较。IRQ runner build在 `sim/uart_irq/build/`，依赖公开rvtool及行为ROM/RAM，可重新生成。

板级主仿真由 `RISCV.pds` 指定 `sim/board_main_selftest/compile.tcl` 与 `run.tcl`，不同于独立DDR两条脚本。在 ModelSim Transcript 从DDR modelsim目录依次 do 这两份绝对路径脚本。依赖 `D:/modelsim/pango_sim_libraries` 的匹配预编译库及 `sim/compile_ddr3_physical_model.tcl` 派生模型；库映射未准备时不能假设装好ModelSim即可运行。

整板构建用 PDS 打开 RISCV.pds，核对 board_top、三块IP、4个UART源及实际FDC后，按 Compile→Synthesize→Device Map→Place & Route→Report Timing→Generate Bitstream。不回放历史impl.tcl。首次克隆不带本地数据库，不凭PDS旧完成标识跳过构建。

改CPU/互连/桥/DDR顶层或共用TB至少跑完整DDR两条，并跑受影响RV32I/异常回归；改UART底层跑TX/RX/FIFO/环回；改MMIO/中断跑MMIO/CPU polling及四组IRQ，同时保证原MMIO/access-fault回归。所有编译soc_top的入口要包含四个UART RTL，非UART TB显式RX=1。

## 11. 已知问题与尚未覆盖事项

1. RV32I fast仍有 `fence_i` 和 `ma_data` 两个known_gap，日志FAIL且tohost=0x539；不能写42/42 PASS。具体原因需另读测试/RTL定位，本次未修CPU。
2. UART逻辑已通，实板软件仍是DDR自检，无串口发送/IRQ；启动镜像部署未完成。之前顶层准备步骤按当时用户失败停止条件停在候选H代码，不能把停止点当成已部署。
3. 当前FDC已有未提交 `uart_tx=AA20`、`uart_rx=AA21`、LVCMOS33/VCCIO3.3及PAP_IO_UNUSED TRUE。它们是外部PDS会话更新，不是已核准连线；不能自动改或宣称可用。
4. 手册FPGA扩展排针J8表中35/36对应AA21/AA20，但图标有RS485共享提示。需核实际原理图、收发器占用、Bank供电、方向和约束属性，尤其避免USB-TTL TX与板上输出相接。不能把ARM UART2 Type-C当成FPGA UART。
5. 对话另提过普通GPIO候选J8 pin3=AB21作RX、pin4=P14作TX，GND pin37；这是备选方案，未在当前FDC实施，不可与AA20/21方案混用。最终排针编号/板修订以官方图纸和实物确认。
6. USB-TTL基本连法为TXD→FPGA RX、RXD←FPGA TX、GND共地；板卡独立供电，通常不接模块5V/3V3。必须核实际TX逻辑电平，模块有3V3电源端不保证TX为3.3V。本对话未测量电平或上板。
7. 当前时序/bitstream已有新本地产物，但功能开发记录中的“未运行PDS”描述的是各步骤当时范围，不代表交接时目录里没有实现结果。现有产物对应性、探针配置和实板结果仍须接手确认。
8. 还无Cache、DMA、CLINT、PLIC、TX IRQ、通用C ISR上下文保存、嵌套中断、模型推理程序或AI加速硬件。IRQ测试ISR专用x20–x28仅为测试约定，不能直接当C ABI处理器。
9. 本地C只完成构建；BIN不是IP DAT。程序、BSS/栈/诊断区布局及装载必须显式设计；没有模型权重、图像或中间结果写入DDR的正式链路。
10. CoreMark尚需独立baremetal port、计时/输出和装载约定。不要用LED5秒超时判断至少10秒的性能运行，32位周期计数要处理回绕。这个任务由他人负责，本对话无分数验收。
11. 当前桥单笔单拍且数据优先，有吞吐/取指等待限制；尚无burst、多outstanding、公平仲裁和DMA一致性。这不妨碍当前基础load/store/fetch已验证，优化应按实际需求另立步骤。

## 12. 建议新对话从哪里继续

先读取本文及当前AGENTS、git状态，再针对用户新指令选择路径，避免从已完成UART TX/RX阶段重做：

1. 若先跑C：在独立sim目录将tests/development/build/main.bin转换为CPU/DDR模型镜像，核入口、loader内容和sp，使用真实SoC验证a/b/c终值及0x40000060退休循环；增加非空.data/.bss用例后再宣称C初始化通过。保持主IP/镜像不动，验收后再设计板级部署。
2. 若先调实板UART：核定物理脚/电平，确认当前FIC和捕获节点；在独立候选payload的DDR自检成功路径加入轮询发H，核代码不越0x40001000、清单长度、原自检与TEST_STATUS，先完整板级联仿自动解码H。之后按用户授权再推广主RAM/IP。
3. DebugCore最小观测选 `board_top.u_soc.u_soc.u_uart_mmio` 的tx_send/tx_ready/tx_busy/tx_data/data_latched和实际TX寄存器；RTL别名可能综合合并，按网表来源核对。core_clk采样，All Data，8192样本且触发靠窗口开头（0–32）或用16384样本；每帧8140拍。触发tx_valid&&tx_ready&&data=0x48，不能用busy过滤采样来计算位宽。新插探针后重跑时序。
4. 串口验收通过再建立PC→UART分块装载协议，第一版CPU搬FIFO到DDR：长度/目标地址/校验/ACK/流控/超时/范围检查明确，读回校验后跳转；这是新功能，尚未实现。随后再规划权重/图像/缓冲DDR区域和加速器接口。

完成每步时写清“RTL接通、仿真PASS、时序通过、镜像生成、下载成功、实板收发PASS”分别有哪些证据，不能互相替代。
