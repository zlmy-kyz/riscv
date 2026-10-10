# RISCV SoC 开发交接

## GitHub 协作入口：摄像头与 CNN（2026-10-10）

主设计直接维护在 `myriscv/`，摄像头/CNN 同学先读 [开发交接](project/摄像头与CNN开发交接_2026-10-10.md)。当前没有摄像头、CNN 或 DMA RTL；其中新外设地址和接入步骤是建议，尚未实现。共享 DDR 用户口是 Pango AXI-like，不能按标准 AXI4 直接挂新主机；DDR 仲裁、跨时钟与完成可见性须单独验证。

本次整理发布当前 RTL/PDS/IP 配置、Loader 必要初始化镜像、软件与仿真入口、固定测量 BIN 和精选结果。完整本地冻结档案、位流、编译工具链及大部分运行日志不上传；历史文档里的档案路径不代表新克隆已包含对应文件。新克隆运行板级下载前必须由用户生成并审查当前主工程位流、建立对应的新门控，不能沿用历史成功位流身份。2B 主 RTL 仿真已通过，当前主设计计数器实板仍 **NOT_TESTED**；本次发布不运行 PDS，也没有新增 RTL 功能。发布范围和复现入口见 [发布记录](project/GitHub协作发布_2026-10-10.md)。

## 最新整理：2B 重复设计与缓存已清理（2026-10-10）

按用户要求删除已迁入主设计的myriscv/candidates/perf_2b、未使用独立PDS工程pds_user_20261010_a、早期软件a/b、重复计数模板、旧生成/审查脚本、旧独立重建步骤及相关仿真缓存。主设计、最终测量BIN c、成功位流/快照、日志/统计与必要实现报告保留。run.py/regress.py已直接读取myriscv，清理后MMIO oracle和下载读出离线mock PASS；冻结246副本/339证据校验保留。详见[清理记录](cpu/CPU计数器2B冗余文件清理_2026-10-10.md)。当前入口为根目录RISCV.pds，PDS由用户执行；下方独立工程/目录保留等是清理前历史。

## 最新入口：2B 计数器直接并入 myriscv 主 RTL（2026-10-10）

用户要求直接修改myriscv已有.v，不再新增设计候选文件夹。已将已验证2B的CPU只读观察、SoC连线和MMIO计数器逐字节并入 `myriscv/mycpu_sync.v`、`soc_top.v`、`simple_mmio.v`。根目录RISCV.pds已经使用这些路径，无需切换工程；IP/初始化/成功BIN/位流不改，本轮不运行PDS。今后主设计直接修改，历史candidate目录保留证据。

主路径回归入口 `sim/cpu_performance_2b/main_rtl.py`，直接编译主RTL，日志为build/main_*_20261010_a。六组回归均完成：MMIO窗口/计数、两条完整DDR物理定向、40个RV32I支持用例+6并发背压、32CPU+2UART IRQ、三条MMIO/UART/access-fault、两组短CoreMark CRC与13项计数。FENCE.I/ma_data原有缺口用迁入前快照独立复现；短CoreMark不是正式跑分。汇总main_integration_20261010_a.json为PERF2B_MAIN_RTL_INTEGRATION_REGRESSION_PASS，两组13项统计与上一候选相同。结果与未覆盖范围见[主RTL集成记录](cpu/CPU性能计数器2B并入主RTL_2026-10-10.md)。用户现在应打开根目录RISCV.pds完整重建，包含实现网表导出；完成后Codex审查新位流并绑定新门控。原门控因主RTL哈希改变将拒绝部署，这是正确行为；旧246项冻结副本/339项证据及成功档案保留。下方“主RTL未改/使用pds_user独立工程”为历史状态，当前计数器实板仍NOT_TESTED。

## 最新准备：用户重建 2B 候选工程（2026-10-10）

当时用户表示自行生成比特流，曾准备 `sim/cpu_performance_2b/build/pds_user_20261010_a/combined.pds`，顶层board_top，状态PERF2B_USER_PDS_INPUT_PREPARATION_PASS；未运行PDS。随后按用户要求将RTL并入主文件，该独立工程及重复步骤已清理，最新入口见[主RTL集成](cpu/CPU性能计数器2B并入主RTL_2026-10-10.md)。用户完成后Codex核对新产物并绑定新的门控/工具，不能沿用旧位流哈希。

## 最新分工：PDS 实现交给用户（2026-10-10）

用户明确要求后续 PDS 编译、综合、布局布线相关步骤交由用户执行。Codex 负责代码与仿真、准备候选工程/步骤，并审查用户生成的时序、资源、初始化、源文件身份和位流；默认不再启动 PDS 实现或生成比特流。此长期约定已写入 AGENTS.md。已生成的 2B 候选与证据保留，不因本次分工调整重新构建；下面记录为既有结果，实板仍 NOT_TESTED。本次只更新分工文档，没有运行 PDS 或修改 RTL。

## 最新结果：CPU 性能计数器 2B MMIO 隔离候选（2026-10-10）

用户授权下一步并选择独立测量 BIN 通过 UART 打印。计数器用 MMIO 实现，候选为 `myriscv/candidates/perf_2b/` 的 CPU/SoC/MMIO 三文件：只读事件输出、13项64-bit冻结计数、ARM/CANCEL/手动起停及PC过滤，旧总线握手和寄存器保持原语义。观察增加一级寄存以通过时序，`[S,T)` 口径与2A observer逐项一致。尚无Cache/M/Burst/BTB或提速结论。

最终MMIO定向、两组短CoreMark CRC/UART读出、两条DDR物理定向、RV32I/并发背压、CPU/UART IRQ、MMIO/access-fault回归通过。完整Pango IP/PHY/物理DDR九微基准1199退休核验通过，首硬件窗口13项与observer相等，九窗口cycles/instret/DDR命令与2A direct基线相等。FENCE.I/ma_data原RTL同失败的已知缺口保留；60次只完成下载/校验/启动仿真，不算完整CRC或实板PASS。

隔离PDS最终 `sim/cpu_performance_2b/build/pds_20261010_b` 四个种子满足现有93.75MHz约束，best seed5 setup +0.526ns；LUT6910/FF7070/DRM8，主工程5714/6052/8。候选位流SHA256 `dc5121b8857a08c053698def358cc07f3be083252cb0b7274f27e6277b5dbb46`。启动脚本两条探测诊断保留，成功加载后七阶段全部完成且无E:，详情见报告；首个直接组合草案时序失败，保留且禁止部署。

新 `sim/cpu_performance_2b/build/deployment_gate.json` 为PERF2B_PRE_BOARD_AUDIT_PASS，246项输入/副本、339项证据冻结，8192初始化字及实现网表8个存储实例核验；52项主RTL/PDS/IP/原成功BIN/位流/CoreMark算法保护输入不变。六份离线计划564响应、6次RUN通过，Codex未打开串口。新测量BIN在 `tests/cpu_performance_2b/build/measure_20261010_c`，后续优化固定同一批BIN；原成功BIN保留。

**实板仍NOT_TESTED。** 用户下载候选位流，再按[六应用操作步骤](../tools/uart_loader/candidates/perf_2b/README.md)执行Hello/CRC32/两组短CRC/两组正式60次；每轮KEY0等待DDR后回车，正式模式绑定同候选短测量BIN的实板CRC日志。工具等待PERF2B_DONE后独立核验协议与统计。完成实板基线后再独立开发16-byte I读缓冲，不与本轮计数器同时优化。完整设计、复现、证据和限制见[2B计数器记录](cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)。下方2A“无硬件计数器/等待确认”为历史状态。

## 最新结果：CPU 性能测量 2A 首批物理基线（2026-10-10）

用户确认执行阶段1方案后，新增 `tests/cpu_performance/` 和 `sim/cpu_performance/`，主 RTL/PDS/IP/成功 BIN/位流不变。仿真observer的窗口、互斥分类、退休/MRET、请求响应守恒、turnover、64-bit carry及32-bit CYCLE wrap通过，三类故意错误被拒绝。九组微基准在当前Pango IP/PHY/物理DDR模型完整PASS，1199条DDR退休逐条解释器核验，Errors:0、无物理ERROR。52项关键保护输入前后SHA256一致。

CPU copy-loader物理基线中，顺序ALU cycles3694/instret129/CPI28.636，IF等待96.51%，129笔DDR读命令，IF响应中位数26周期；顺序64-word load cycles5692、MEM分类63.55%。这些是指定小微基准的物理模型结果，不是实板CoreMark瓶颈份额。现有两组短CoreMark原BIN完整功能CRC通过，动态退休中软件乘法占52.116%/54.998%；用户口模型时间不作真实DDR性能证据，不能直接推算60次CPI或提速。

仿真专用128-bit Pango入口完成358拍物理写入/回读后释放CPU的第二路径也九窗口PASS，1199条退休及各窗口DDR命令数与CPU copy-loader一致，Errors:0/无物理ERROR。短窗口可因背景等待相位出现211-cycle差异，不算硬件提速；默认入口用此方式，生产UART Loader和位流不变。

结果、原始CSV/日志、复现及未覆盖范围见 [2A测量记录](cpu/CPU_DDR性能测量2A与首批物理基线_2026-10-10.md)，入口见 [仿真说明](../sim/cpu_performance/README.md)。本轮没有硬件计数器、cache/M/BTB或新位流；下一步待确认2B板级计数读出及独立16-byte I读缓冲候选。下方“CPU性能分析尚未实施”等描述为历史状态；最新主位流六轮实板和正式60次基线仍保留。

## 最新软件能力：通用新 C 程序入口（2026-10-10）

新增 `tests/c_app/`，提供 `run_app.py --source ... --expect ...`：编译 RV32I ELF/BIN、审查地址/大小/ISA、真实 CPU 完整下载执行仿真、独立应用门控，再由用户确认 KEY0/DDR 就绪后自动 COM11 LOAD/VERIFY/RUN 与输出验证。`--prepare` 不开串口，`--deploy` 复用已准备结果，`--verify-log` 离线复核日志；多 C 文件及精确输出文件可用。原 Loader/BSP/主 IP/位流/旧门控及成功镜像保持不变。

示例与另一份多文件/软件除法程序通过完整仿真；协议、输出及编译/ISA/布局错误检查通过。新入口实板仍 NOT_TESTED，上板/KEY0/串口由用户执行；下方“通用入口未实现”是历史状态。操作见 [c_app README](../tests/c_app/README.md)，目的、命令、证据和限制见 [实现记录](software/通用C程序自动构建下载验证_2026-10-10.md)。CPU 性能分析尚未实施，无 RTL 优化或提速结论。

## 最新结果：用户重建主工程位流六轮实板 PASS（2026-10-10）

新位流 `generate_bitstream/board_top.sbit`（SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf）已由用户上板，六份原始JSON独立核验540/540响应（279ACK/261READY）、6次唯一成功RUN、零CRC错误/重试/额外RX。Hello/CRC32及两组短CoreMark CRC正确，新位流两组正式60次无ERROR且CRC正确，17.750024053/18.752304203秒。主IP当前verify_run_hello Loader DAT，旧“load_stage10配置”仅历史。

`sim/bsp_workflow/rebuilt_20261010/board/independent_result.json` 为REBUILT_SIX_APPLICATION_ACTUAL_BOARD_VERIFIED，submission_result.json为REBUILT_SIX_APPLICATION_ACTUAL_BOARD_ARCHIVE_PASS，549项成功快照在first_success/。415项冻结输入/副本、原116项证据及旧518项十轮快照匹配。新门控NOT_TESTED保留生成时历史，最新看实板报告。新工具绑定此次主工程位流，原BSP工具仍绑定旧隔离位流；不要混用正式CRC日志或覆盖成功文件。

本轮重建复验已完成，不再等待用户测试。Codex未操作板子或串口，CPU/Loader/BSP未改；新旧CoreMark时间基本一致，没有性能优化结论。下一任务继续CPU瓶颈统计及性能优化。见[新位流实板验收](board/主工程新位流六轮实板验收_2026-10-10.md)，下方准备记录仅历史。

## 最新准备：主工程新位流可进行六轮实板复验（2026-10-10）

用户新位流SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf已完成初始化/综合/时序离线审查：原CPU/Loader/BSP仿真输入与证据不变，主IP生成初始化及本次综合网表8个存储实例与成功版本匹配，93.75MHz现有约束通过。generate_netlist导出仍为10月3日旧文件，已排除；未宣称本次完整实现仿真网表初始化核验。新门控REBUILT_LOADER_PRE_BOARD_AUDIT_PASS冻结415项输入/副本，8项PC离线检查PASS，实板NOT_TESTED。

用户先下载 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`，关闭串口助手，再执行 `& C:/python/python.exe D:/riscv/RISCV/tools/uart_loader/candidates/rebuilt_20261010/run_board.py`。六轮Hello/CRC32/两组短CoreMark/两组正式CoreMark，各提示KEY0等待DDR后回车；日志在sim/bsp_workflow/rebuilt_20261010/board/first。新工具绑定新位流，不套用旧位流CRC日志或门控；原工具、十轮成功档案均保留，Codex未操作板子。完成后独立核验实际日志，再归档新位流。详见[复验准备](board/主工程新位流实板复验准备_2026-10-10.md)。CPU性能优化方向保持，尚未改CPU RTL。

## 最新配置观察：用户重新生成主工程位流（2026-10-10 14:34）

新文件 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`，3791112字节，SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf；生成日志记录完成。当前两主IP INIT_FILE已由用户切到verify_run_hello/build同一对loader_rom.dat/loader_ram.dat，下方“主IP仍为load_stage10”保留重建前历史。原十轮成功隔离位流未覆盖，SHA仍31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0。新位流尚未完成独立初始化/网表/时序审查或实板验收，现有PC工具仍绑定原成功版本。见[新位流定位记录](board/主工程新位流定位记录_2026-10-10.md)。本轮只定位与核对配置，未修改RTL或操作板子。

## 当前任务：转入 CPU 性能优化（2026-10-10）

用户要求更新文档，下一项工作为CPU性能优化。本轮仅整理交接，不改RTL、不实现通用软件入口、不重新构建或上板。统一BSP及十轮实板任务已经完成，成功镜像与518项快照保留；下方历史待验描述不再是当前任务。

优化起点见[CPU性能优化约定](CPU性能优化起点与验收约定_2026-10-10.md)：固定93.75MHz及本次两份成功CoreMark BIN（performance_60 17.749998571秒、validation_60 18.752320843秒），先统计CoreMark计时区间的退休、CPI、取指/数据等待、分支和流水线停顿，再依据证据选择优化点。目前尚无瓶颈分解或优化RTL。CPU变更须新隔离PDS/位流、回归和新门控，不能让旧哈希门控认可修改后的硬件；主IP仍为load_stage10，优化候选明确采用成功verify_run_hello Loader DAT/IP。

软件能力边界：build.py/run.py只接入已验收的Hello、CRC32和CoreMark；任意新main.c的一键构建/下载/验证尚未实现，讨论过的run_app.py仅为示例。新程序需注册构建与预期输出，--tag只隔离构建不自动接入。此工具扩展暂留后续，不阻塞现有CoreMark性能分析。全部实板操作继续由用户负责。

## 最新结果：统一 BSP 与十轮复位下载实板 PASS（2026-10-10）

用户完成同一Hello成功Loader位流的十轮KEY0/COM11验收，Codex直接独立核验十份原始JSON：834/834响应（432ACK/402READY）、10次唯一成功RUN，零CRC错误、零重试/额外RX；每轮SEQ1 PING空状态、完整LOAD/VERIFY/RUN及程序输出通过。Hello和独立CRC32各两轮、CoreMark短迭代四轮及正式60次两轮均通过同一BSP构建/审查/下载流程；新BSP正式performance/validation分别17.749998571/18.752320843秒，所有算法CRC正确且无ERROR。

`sim/bsp_workflow/board/first_independent_result.json` 为UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_VERIFIED；`first_submission_result.json` 为UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_ARCHIVE_PASS，518项完整成功快照在 `first_success/`。380项冻结输入/116项证据/380项源副本、旧Hello170项及18项PDS源/副本、旧应用279项快照均匹配。历史门控NOT_TESTED保留生成时状态，当前结论看新增报告。

统一BSP、统一软件流程及十轮连续复位下载任务已完成；精简第③关剩余十轮已补齐。未改CPU/DDR桥/ROM Loader、未重建成功软件或位流；Codex未打开串口或操作板子。KEY0/JTAG由用户确认，日志独立证明十轮Loader空状态重新启动；UART IRQ仍只仿真PASS。详见[十轮实板验收](software/统一BSP与十轮复位下载实板验收_2026-10-10.md)。后续使用已验收软件和成功位流；新程序单独隔离构建验证，不重复本次开发与上板。

## 最新准备：统一 BSP 与十轮复位下载（2026-10-10）

用户已将统一软件流程及至少10轮KEY0复位验收纳入当前任务。隔离目录 `tests/bsp_workflow/` 已完成 startup/linker、UART轻量printf、cycle延时、trap/IRQ和CRC32驱动，以及统一 build.py/run.py。Hello、CRC32和两种CoreMark配置通过同一构建、镜像审查、LOAD/VERIFY/RUN和严格结果核验流程；未修改CPU、DDR桥、ROM Loader或成功位流。

八组真实CPU仿真及54项PC离线检查PASS；Hello原速115200真实引脚仿真通过，另含完整短迭代CoreMark CRC、UART RX IRQ/ECALL上下文和cycle回绕。新60次BIN仅完成装载/校验/启动仿真，完整正式算法与时长待本轮实板，不能沿用旧不同BIN的PASS。门控 `sim/bsp_workflow/build/deployment_gate.json` 为UNIFIED_BSP_SIM_PASS，冻结380项输入/116项证据/380项源副本；六个可部署manifest，IRQ仅仿真。最终 `pre_board_audit.json` 核验冻结文件、六份离线计划及旧170/279项成功快照PASS。

**本轮十轮实板仍NOT_TESTED。** 用户保持此前Hello成功Loader位流（SHA256 31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0），关闭串口助手，在PowerShell执行 `& C:/python/python.exe D:/riscv/RISCV/tests/bsp_workflow/run.py --acceptance`。每轮按KEY0、释放并等DDR初始化完成后回车；脚本连续安排Hello/CRC32/短CoreMark/正式CoreMark共10轮，正式模式绑定本批第7/8轮CRC日志。结果保存 `sim/bsp_workflow/board/first/`，用户完成后Codex直接独立核验及归档，再更新实板PASS。Codex未打开COM11或操作板子；旧成功镜像与失败记录保留。详见[准备与步骤](software/统一BSP与十轮复位下载验收准备_2026-10-10.md)。下方历史“额外10轮不在本次范围”仅指2026-10-09任务。

## 最新结果：同位流第二程序与 CoreMark 实板 PASS（2026-10-09）

用户完成五次COM11下载，Codex独立核验五份原始JSON：第二程序精确输出SECOND_PROGRAM_PASS sum=11440；CoreMark两组1次算法CRC正确，两组60次正式运行CRC正确且无ERROR，分别17.756533472秒和18.758810933秒。437/437响应（226ACK/211READY）、5次唯一成功RUN，零响应CRC错误、零重试/额外RX。均沿用此前Hello成功的同一Loader位流文件身份，无Loader/IP/位流重建。

独立结果 `sim/uart_loader/board/applications_stage3_independent_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_PASS；归档收据 `applications_stage3_submission_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_ARCHIVE_PASS。279项完整成功快照在 `sim/uart_loader/board/applications_stage3_success/`；196项输入/74项证据/196项源副本、旧Hello170项成功快照及PDS副本均匹配。门控生成时NOT_TESTED保留历史，当前结果看新增板级报告。

本次用户指定“第二程序/CoreMark先CRC后正式”两步已完成。额外10轮复位不在本次任务范围，尚未执行，不将原更宽的第③关所有检查记为PASS。Codex未打开串口或操作板子；未独立观察JTAG/KEY0。详见[实板验收](uart_loader/UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。

## 历史准备：同位流第二程序与 CoreMark（2026-10-09）

用户本次选择换第二个C程序，以及CoreMark先验算法CRC再正式运行。隔离开发和集中仿真全部完成：587-byte第二程序原速115200引脚收发/输出PASS，两组CoreMark 1次完整算法CRC PASS，两组60次新UART装载/VERIFY/RUN/启动PASS；60次完整算法复用原逐字节相同BIN的既有Full Boot证据。本次UART实板仍NOT_TESTED，额外10轮复位不在此次任务范围内。

门控 `sim/uart_loader/build/applications_stage3/deployment_gate.json` 为SAME_LOADER_APPLICATIONS_SIM_PASS，冻结196项输入/74项证据/196项源副本，35项PC离线检查PASS。沿用此前Hello成功的同一Loader位流，无Loader/IP/PDS重建；成功170项快照及旧76项输入/71项证据核对一致。失败日志保留，不修改成功镜像。上板/KEY0/COM11由用户操作，Codex未打开串口或下载位流。

下一步用户执行 `D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1`，按提示五次KEY0：second、performance_1、validation_1、performance_60、validation_60。正式模式必须先提供对应短迭代实际CRC日志；结果在 `sim/uart_loader/board/applications_stage3_first/`。完成后离线核验/归档，再记录实板结果。详见[准备记录](uart_loader/UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。

## 最新结果：VERIFY / RUN / DDR / Hello 合并实板 PASS（2026-10-09）

用户完成隔离候选下载和COM11测试，Codex独立核验实际原始JSON：157/157响应（83ACK/49READY/25预期NACK）、4次正式VERIFY的367-byte DDR CRC32均5E142E06，最终SEQ106唯一成功RUN后精确收到13-byte `Hello World\r\n`，零响应CRC错误、零重试/额外RX，用时4.301259秒。精简计划第②关完成，已验收UART下载→正式VERIFY→RUN→DDR应用Hello链路。

汇总 `sim/uart_loader/board/verify_run_hello_board_result.json` 为COMBINED_ACTUAL_BOARD_VERIFIED；归档收据 `verify_run_hello_submission_result.json` 为COMBINED_ACTUAL_BOARD_ARCHIVE_PASS。170项完整成功快照保存在 `sim/uart_loader/board/verify_run_hello_success/`，冻结76项输入/71项证据/76源副本、阶段⑦至⑩成功档案及主PDS/IP/旧成功位流均匹配。原仿真门控内NOT_TESTED是历史生成状态，当前结论看新增板级汇总。详见[实板验收](uart_loader/UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md)。

主工程配置继续保留阶段⑩；用户报告本次下载隔离verify_run_hello位流，PC日志中的位流文件哈希与已审计快照一致。未独立观察下载/KEY0或读回FPGA配置；本轮没有物理DDR损坏或UART线级故障注入。上板、供电、复位和串口由用户负责，Codex只离线核验和归档。本轮不重建镜像、不重复仿真。下一步第③关同位流至少10轮复位、第二BIN和CoreMark；本轮尚未启动。

## 历史准备：VERIFY / RUN / DDR / Hello 合并仿真 PASS（2026-10-09）

精简计划第②关已在新隔离候选 `verify_run_hello` 完成，Loader 与 367-byte Hello 各构建一次。五组真实 CPU 仿真全部 PASS：正向11、错误矩阵157、原速 UART9、UART事件失效恢复25、控制截断/CRC34响应；14项 PC 离线检查 PASS。门控 `COMBINED_SIM_PASS` 冻结76项输入、71项证据和76项源副本，实板仍 NOT_TESTED。

正式 VERIFY 重读整个 DDR 文件 CRC，RUN 要求 VERIFIED 且再次重读，全部 ACK 发完才跳转。仿真已证明真实 DDR 指令退休、应用 gp/sp、非空 data/BSS 清零及精确 Hello。主 PDS/IP/成功位流保持阶段⑩配置，阶段⑦至⑩成功档案保留；新候选 PDS/IP/位流在 `sim/uart_loader/build/verify_run_hello/pds_candidate/`，不重建成功 DAT。

用户最新要求：上板、供电、JTAG下载、KEY0复位和COM11测试由用户操作；Codex提供步骤并离线核验日志，不再操作下载器或串口。隔离位流已生成并审计PASS，最终seed4满足93.75 MHz已有时序约束，8192个初始化字和8个实现网表存储实例均与冻结DAT一致；收据为 `sim/uart_loader/build/verify_run_hello/pds_build_result.json`。JTAG两次扫描仅识别USB Cable II、未发现FPGA，等待现场通电/接好JTAG；COM11仅枚举，尚未下载或打开串口，实板未完成。详情及后续入口见[合并验收记录](uart_loader/UART_Loader_VERIFY_RUN_DDR_Hello合并验收_2026-10-09.md)。后续继续现有候选和冻结镜像，不重新开始开发。

## 历史结果：阶段⑩真实程序LOAD两轮实板PASS（2026-10-09）

用户完成两轮COM11测试；Codex独立核验工程内原始日志，每轮8响应、383-byte真实BIN的DDR读回CRC32均B2E24920，零CRC/UART错误、零重试/额外RX。汇总STAGE10_TWO_ROUND_BOARD_PASS / PASS_LOAD_ONLY_UNVERIFIED，第①关完成。正式VERIFY/RUN和执行尚未实现。

两份固定原始日志和当前PDS/IP/sbit共10文件配置已归档；79项冻结输入、110项证据及79项源副本相同，阶段⑦/⑧/⑨成功档案保留。历史STAGE10_SIM_PASS门控内NOT_TESTED保持生成时状态，当前实板结论看新增汇总。详见[两轮实板验收](uart_loader/UART_Loader真实程序LOAD两轮实板验收_2026-10-09.md)。

当前主IP指向load_stage10成功DAT；下一开发步骤为精简计划第②关：新隔离候选一起实现正式VERIFY、RUN、DDR执行及Hello。上板/复位/供电/COM11全部由用户操作，Codex负责开发、仿真与离线核验。本次已完成板级核验归档，尚未开发第②关功能，不重建成功DAT/BIN。

更新日期：2026-10-09（Asia/Shanghai）。工程根目录：`D:/riscv/RISCV`。

## 精简计划制定时记录：三个关口（2026-10-09）

用户要求精简阶段，剩余原⑩至⑮合并为：①真实程序下载（原⑩，两轮实板PASS）；②校验并运行Hello（原⑪至⑬及⑭基本Hello）；③同位流换程序与CoreMark（原⑭至少10轮复位/第二BIN及⑮）。第②关通过即可UART下载并运行DDR程序。关键检查保留，按LOAD→VERIFY→RUN顺序验收，原编号仅作为检查项和历史证据索引。详细通过条件见[剩余阶段精简计划](uart_loader/UART_Loader剩余阶段精简计划_2026-10-09.md)。

第①关两轮实板验收已完成；下一步一起开发第②关隔离候选。上板、复位、供电和COM11全部由用户操作，Codex不打开串口。此次只调整文档，不改冻结代码或成功镜像；下方历史“下一阶段”按本文合并计划解释。

计划精简时的工作区观察（历史）：两主IP INIT_FILE已指向load_stage10同一对DAT，board_top.sbit修改时间2026-10-09 16:37:49；未观察实际下载，工程内阶段⑩两轮日志和汇总均不存在，实板仍待验。冻结输入79项/证据110项/源副本79项哈希匹配；先前439项保护文件中22项PDS/IP/位流产物已有变化，本次未写这些文件，详见精简计划记录。

## 换对话快速入口（2026-10-08）

先读 [UART Loader 换对话交接](uart_loader/UART_Loader换对话交接_2026-10-08.md)，包含地址、现行协议、成功镜像哈希、证据、构建注意事项和可复制的新对话指令。最新实板结论为阶段⑩真实程序LOAD两轮PASS；阶段⑨随机二进制/DDR CRC两轮各1000镜像PASS保留；阶段⑦、⑧成功证据均保留，见下方最新结果；历史小节里的“当前/下一步”仅对应其记录时间。

阶段⑨验收时主 IP 初始化为 `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat` 与同目录 `loader_ram.dat`；本次核对已指向 `load_stage10/build` 同一对 DAT。PC0 从 ROM 常驻 Loader 等待 UART，数据 RAM 是常量/状态/缓冲/栈，不走旧自检或 CoreMark 的预置 RAM 复制启动。主IP配置不能证明板上已运行对应镜像。

阶段⑦源码及完整构建已保存 `tests/uart_loader/verified/ddr_crc_stage7/`；PC工具保存 `tools/uart_loader/verified/ddr_crc_stage7/`；runner/TB/模型保存 `sim/uart_loader/build/ddr_crc_stage7_sources/`。该目录 `archive_receipt.json` 核对 37 个副本相同，全部仿真输入和成功 ELF/DAT 哈希一致，未重建镜像。

**不要运行无参数 build.ps1 覆盖 `build/ddr_crc`；它尚未保护这份新实板成功目录。** 后续使用隔离 `-OutputDirectory`。阶段⑧完整约定实板矩阵已在隔离诊断候选两轮验收，仍不能任意 BIN 下载或 RUN。阶段⑦归档交接时只更新入口和成功快照；本轮阶段⑧开发与仿真结果见下方最新进展，原阶段⑦工具/C/RTL/IP和成功镜像不改。

## 历史准备：阶段⑩真实program.bin正式LOAD隔离候选（2026-10-09）

阶段⑨已两轮实板PASS，现开发新load_stage10候选和独立program_stage10应用。新增正式CMD2两次应答：Header→READY→DATA/CRC→CPU写DDR→最终ACK；BEGIN/END、连续地址、total/image_crc身份、重复块精确字节比较且无重写、错误失效及未完成会话5秒超时已实现。383-byte真实ELF/BIN含非空data/bss，两块256+127，最终仅LOADED_UNVERIFIED；VERIFY3/RUN4仍拒绝，持续ROM驻留，没有应用执行。

编译/Harvard/1354条ISA及真实ELF/BIN审查、七组真实CPU/DDR/UART仿真和19项PC离线检查全部PASS：positive49、negative71、extended50、最大61440字节window483、unverified6、原速native8、原速实际BREAK/overflow会话失效及恢复14响应。部署门控STAGE10_SIM_PASS已冻结79项输入和110项证据；阶段⑩实板NOT_TESTED。当前主IP仍为阶段⑨random_stage9成功DAT，PDS/RTL和阶段⑦/⑧/⑨成功档案未改，未打开COM11。

下一步由用户把两IP临时指向load_stage10/build同一对DAT，生成下载位流；KEY0后专用acceptance.py两轮各8响应，得到LOADED_UNVERIFIED/诊断DDR CRC匹配且无Hello，再离线核验两份日志。正式VERIFY在精简计划第②关验收，不能用CMD14诊断CRC授予VERIFIED。操作命令、哈希、复现证据与失败保留见[阶段⑩记录](uart_loader/UART_Loader真实program.bin与LOAD阶段10_2026-10-09.md)。

## 最新结果：阶段⑨随机二进制两轮实板PASS（2026-10-09）

用户完成COM11首轮及after_reset轮；Codex直接读取工程内原始JSON，独立逐帧核验请求、60-byte响应的全部字段/CRC、固定seed输入、镜像/PC工具/部署门控身份及完整数量。每轮1000镜像、17946响应、3700127有效文件字节，1000个整镜像DDR CRC ACK及999个尾哨兵CRC ACK全部通过，零CRC/UART错误、零重试。合计2000镜像、35892响应、7400254有效文件字节；两轮分别549.845/550.179秒，约6729.41/6725.32 B/s，SEQ均1–17946。

板级汇总 `sim/uart_loader/board/random_stage9_board_result.json` 为STAGE9_TWO_ROUND_DIAGNOSTIC_BOARD_PASS / PASS_RANDOM_DIAGNOSTIC_ONLY。两份固定原始日志副本及PDS/IP/当前sbit共10文件配置副本已新增保存；1186项冻结输入及副本、103项仿真证据、阶段⑦37项原始/副本和阶段⑧成功配置档案均未变。部署前286项保护文件中277项未变、9项变化均为用户本次PDS/ROM/RAM/位流部署文件；未覆盖旧成功档案。详见[两轮实板验收](uart_loader/UART_Loader随机二进制两轮实板验收_2026-10-09.md)。

当前两主IP INIT_FILE已由用户指向 `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat` 和同目录 `loader_ram.dat`。Loader从ROM驻留，RAM存放常量/状态/缓冲/栈；CMD13/14仅低60KiB诊断写/真实DDR CRC，不执行随机数据。满61440-byte文件没有实板栈探针，栈保护另有仿真证据；after_reset重新接受SEQ1已核实，KEY0和已下载位流文件身份未独立观察。部署门控的历史NOT_TESTED保持生成时状态，当前实板结论看新增板级汇总。

下一开发步骤为阶段⑩：新独立Hello ELF/BIN/manifest（含非空data/bss），正式LOAD完整END，每块ACK，最终LOADED_UNVERIFIED，持续在ROM、不得输出Hello或自动执行。VERIFY和RUN按后续阶段验收，当前均未实现；本轮只离线核验归档，未开始阶段⑩。成功DAT不重建，后续继续使用隔离候选；上板、复位和串口由用户操作。

## 历史准备：阶段⑨随机二进制/DDR读回CRC隔离候选（2026-10-09）

阶段⑧完整诊断矩阵已两轮实板PASS，用户授权下一步；新候选tests/uart_loader/candidates/random_stage9、新工具tools/uart_loader/candidates/random_stage9、新TB/脚本sim/uart_loader/stage9。新增受限CMD13分块写/CMD14范围CRC，低60KiB窗口，256-byte块，SB前缀/尾部与SW中部；严格同SEQ完整字节比较，重复写不重写且重读CRC；无正式LOAD/VERIFY/RUN或随机数据执行。

编译/Harvard布局/1005条ISA审查、62项负例及恢复、108项旧命令兼容、114镜像/148171字节bulk、原速41响应/10边界文件、原速BREAK/洪泛9响应、独立写后物理损坏7响应及17项PC/独立核验器离线检查全部PASS。部署门控STAGE9_SIM_PASS已冻结1186项输入和103项证据；阶段⑨实板仍NOT_TESTED，当前主IP仍为阶段⑧成功诊断候选。原成功镜像/C/RTL/IP/PDS不改，未打开COM11。

已生成1000实板镜像、3700127有效payload字节、17946停等请求计划（14边界+100组全窗口随机+886组小随机）；每轮至少1000镜像，正常0错误/0重试。现已完成全部仿真/冻结部署门控；下一步由用户用random_stage9/build同一对DAT生成下载诊断位流，KEY0后两轮各1000镜像实板验收，日志再离线核验。详细状态、范围及命令见[阶段⑨记录](uart_loader/UART_Loader随机二进制与DDR读回CRC阶段9_2026-10-09.md)。

## 历史结果：阶段⑧完整异常矩阵诊断候选两轮实板PASS（2026-10-09）

用户提交COM11首轮和after_reset轮，各117/117 PASS。独立struct/zlib核验两轮原始请求/响应、全部字段与CRC、错误恢复、时序和候选/工具/部署门控身份，另逐条对照234条终端PASS。每轮80ACK、37个预期NACK、40个实际DDR CRC ACK；合计234响应、160ACK/74NACK/80CRC ACK，实际DDR CRC均23C3E508。BREAK返回NACK8005且真实UART原因0x10，洪泛先PING ACK再NACK8005且原因0x20，两类故障后PING/DDR CRC全部恢复通过。两轮分别SEQ1–80，日志哈希不同；未独立观察KEY0。

阶段⑧约定的完整实板矩阵已补齐，结论绑定隔离uart_fault_stage8_diag。板级汇总sim/uart_loader/board/uart_fault_stage8_diag_board_result.json为STAGE8_DIAGNOSTIC_TWO_ROUND_BOARD_PASS、PASS_DIAGNOSTIC_CANDIDATE_ONLY；固定两轮JSON/终端及部署工作区10个文件副本已保存。66项输入/58项仿真证据及阶段⑦37项原始/副本哈希仍一致。原成功镜像、r2和原FAIL全部保留；没有改写原二进制验收范围或历史NOT_TESTED报告。

当前两IP已由用户指向tests/uart_loader/candidates/uart_fault_stage8_diag/build/loader_rom.dat与loader_ram.dat；本轮Codex只离线核验归档，未打开COM11、修改RTL/C/工具或重建DAT。磁盘当前sbit已保存副本，未独立核实已下载位流文件身份。详细证据/哈希/复验命令见[两轮实板验收](uart_loader/UART_Loader_UART帧错与FIFO溢出两轮实板验收_2026-10-09.md)。

下一开发步骤为阶段⑨隔离随机二进制/DDR实际读回CRC压力验收；本轮未启动。仍仅固定64-byte DDR诊断，不支持任意BIN或正式LOAD/VERIFY/RUN。上板、复位、串口继续由用户负责。

## 历史准备：阶段⑧UART帧错/溢出实板注入准备（2026-10-09）

用户要求补齐剩余两类实板故障，所有上板/复位/串口操作仍由用户负责。原成功镜像和主IP不改，新增隔离诊断候选tests/uart_loader/candidates/uart_fault_stage8_diag：清错前记录真实STATUS[4:5]，8005响应capabilities bit24/25镜像原因，分别要求0x10/0x20，避免仅凭共用8005推测两项通过。

原速纯引脚9响应和三次ROM启动PASS：BREAK产生1次真实帧错，PING ACK期间96-byte洪泛产生43次真实FIFO溢出、丢43字节，峰值16、两次W1C；不force CPU/UART/FIFO。105.348/116.719ms恢复，PING/DDR CRC通过。PC13项与独立核验器11项离线PASS，108帧候选host回归PASS；部署门控STAGE8_UART_DIAGNOSTIC_SIM_PASS，已冻结66项输入副本。新候选实板仍NOT_TESTED，现可交给用户上板验收。详见[注入准备与用户操作](uart_loader/UART_Loader_UART帧错与FIFO溢出实板注入准备_2026-10-09.md)。

候选host回归、部署门控和同一DAT身份已完成冻结；下一步由用户临时切换两IP/生成下载诊断位流，KEY0后运行诊断acceptance.py --mode all两轮（每轮117响应，原108+线级9）。原阶段⑦/阶段⑧r2成功和FAIL证据全部保留，诊断候选身份与旧二进制分开记录，尚不推进⑨或LOAD/VERIFY/RUN。

## 历史结果：阶段⑧主机可注入异常两轮实板PASS（2026-10-08）

用户用PC工具r2在COM11提交首轮与after_reset轮；独立struct/zlib逐帧核验两份原始日志、请求矩阵、响应全部字段/CRC、时序、额外RX检查记录与终端输出，每轮108/108 PASS：73ACK、35个预期NACK、37个DDR CRC ACK。合计216帧、146ACK、70个预期NACK、74个CRC ACK，实际DDR CRC均23C3E508；错误后的合法PING/CRC恢复全部通过。两轮均接受新SEQ1并完成至SEQ73；未独立观察KEY0，未采集板上位流文件身份。

现行板级汇总为sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json，board_result=PASS_HOST_INJECTABLE_ONLY；UART帧错/FIFO溢出实板仍NOT_TESTED，阶段⑧完整实板范围NOT_COMPLETE。旧ack_nack_stage8_board_result.json及原首轮误报FAIL保留为历史证据，不覆盖；旧仿真报告内NOT_TESTED也保留生成时状态。详见[两轮验收记录](uart_loader/UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。

成功ELF/ROM/RAM、阶段⑦37项快照、阶段⑧27项候选、PC原/r2的11项输入档案及全矩阵221项保护文件/25项仿真输入哈希均匹配。未重建DAT、修改C/RTL/IP/PDS或重新仿真；Codex仅离线核验/归档，所有上板操作继续由用户负责。本轮未启动⑨随机BIN或正式LOAD/VERIFY/RUN；后续须保留上述实板覆盖边界并使用隔离候选。

## 历史记录：首轮PC时序误报与r2复验准备（2026-10-08）

用户已运行首轮：终端94条PASS后停止，第95条truncated_magic_recover_ping记录FAIL。独立struct/zlib核对全部已收95个原始响应及请求矩阵，字段/CRC/预期状态全部一致；truncated_magic正确NACK8004为207.309ms，随后SEQ64合法PING ACK为10.289ms。错误来自PC工具：startswith('truncated_')把恢复PING/CRC也要求>=195ms；旧离线fixture同样给这些恢复ACK加延迟，掩盖了误判。原FAIL日志/终端和输入副本保留，不改写PASS；最后一帧没有完成额外RX检查，整轮仅记录94个完整工具PASS，第二轮尚未提交。

修正版在tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py，仅对negative且预期status8004的真正截断包施加195ms下限；独立核验器sim/uart_loader/stage8/check_board_r2.py同步修正。12项时序回归复现旧95帧失败、修正版108帧快速ACK通过，且4类早到超时NACK仍拒绝；另8项通用PC离线检查PASS。成功C/RTL/IP/DAT和原仿真输入不变，不需要新位流/重建DAT。Codex未打开COM11，实板操作仍由用户负责。

板级门控sim/uart_loader/board/ack_nack_stage8_board_result.json为INCOMPLETE_RETEST_REQUIRED_PC_TIMING_FIX，不是阶段⑧实板PASS。详见[PC时序误报及r2复验](uart_loader/UART_Loader_ACK_NACK实板首轮时序误报与PC工具r2_2026-10-08.md)。下一步用户KEY0复位并等DDR后，使用r2工具和新日志ack_nack_stage8_first_pc_r2.json；再复位后另跑ack_nack_stage8_after_reset_pc_r2.json。每轮108/108 PASS再离线核验。不得继续阶段⑨，UART帧错/溢出实板仍未覆盖。

## 历史记录：阶段⑧专项仿真PASS与实板准备（2026-10-08）

用户分工（2026-10-08）：实板下载、供电、KEY0复位和COM11串口验收由用户自行操作；Codex提供脚本/命令，并在用户提交日志后进行离线核验与归档。本阶段不由Codex打开COM11。每轮预期108帧全部PASS（73ACK/35个预期NACK，37个CRC ACK）；预期NACK本身是通过条件，任何RESULT: FAIL/超时/字段或CRC异常均须保留日志后停止。UART帧错/溢出实板仍未覆盖。

阶段⑦成功源/ELF/DAT逐字节复制到tests/uart_loader/candidates/ack_nack_stage8，未重建镜像；PC专项工具在tools/uart_loader/candidates/ack_nack_stage8。主IP继续引用原build/ddr_crc，生产C/RTL/IP/PDS不改，阶段⑦37个原始/归档文件哈希全部一致。

完整114帧/37负例从头重跑PASS：77ACK/37NACK、39CRC ACK，16SW/656LW；RX6000/消费5999（真实FIFO溢出丢1）、TX/解码6840、FIFO峰值16，Errors/Warnings0、退出0，全部保护/镜像/输入哈希不变。全矩阵仅隔离TB的MMIO计时源TIME_SCALE64；另外native8帧原速PASS，坏Header113.941ms、截断body209.509ms；UART8帧独立重测PASS。首次长矩阵因检查器漏计丢字节而FAIL，原日志/输入保留；只修复隔离TB一行计数，已有全矩阵干净重跑，未改C/RTL。

机器门控sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json为STAGE8_ACK_NACK_SIM_PASS、board_result=NOT_TESTED；完整新日志在sim/uart_loader/build/ack_nack_stage8_repaired/full，最终输入副本在ack_nack_stage8/final_sources。PC工具8项及独立实板核验器5项离线检查PASS，不能当作实板证据。详见[阶段⑧记录](uart_loader/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。

用户说明阶段⑦验收后板子已断电且串口关闭；本轮未打开COM11或生成/下载位流。下一步唯一动作：恢复板子及已有阶段⑦成功位流，关闭串口助手、KEY0复位并等DDR初始化，运行候选acceptance.py的108帧/35个主机可注入负例，首轮与复位后第二轮各用新日志名。仿真已经通过，不需要重建DAT/更换IP。UART帧错/溢出实板无法用普通串口可靠注入的部分继续单独标明未覆盖，不能记作专项实板全PASS；尚不推进⑨随机BIN或LOAD/VERIFY/RUN。

## 当前结果：阶段⑦DDR读回CRC32实板PASS，两轮各100次CRC32 PASS

用户提交COM11的两轮完整输出：每轮100次固定64-byte DDR写/读/比较ACK，再100次只读CRC ACK。
独立struct/zlib逐帧核对ddr_crc100.json和ddr_crc100_after_reset.json，每份200条SEQ1–200：
CMD11奇数帧DATA64、CMD12偶数帧DATA空且LENGTH64/IMAGE_CRC=23C3E508；地址均40000000，
Header/DATA CRC、响应命令/status0/accepted64/字段、实际DDR CRC和日志元数据全部PASS。
写比较响应DDRCRC0，CRC响应PC=DDR=23C3E508；日志均含100组匹配测试编号，无NACK/超时。
两轮共400 ACK（200写比较+200CRC校验），27200请求字节/24000响应字节/12800写入payload字节；
始终重复操作同一64-byte区域，不表示随机数据、12800个不同DDR字节或大程序已验收。
复位证据为按要求提交的after_reset轮和重新从SEQ1成功，未独立观察KEY0。
首轮归档sim/uart_loader/board/ddr_crc100_first_verified.json，SHA256=
87b4dd7c284083a578a848a10fe8d07827f3a71c653a2cfce993910797a39c26；CRC RTT9.843–10.501ms。
第二轮归档ddr_crc100_after_reset_verified.json，SHA256=
2661f01148a5772d1750bc2d76d45ede2e1b3df08ef7ac428d2437b5fa62974b；CRC RTT9.847–10.182ms。
提交输出另保存ddr_crc100_console_verified.txt，200条CRC32 PASS/200写ACK/无FAIL，SHA256=
0b58b955f825523b98d85f3a08a4f300c08a600602ddbe2f7a2f34087bd3045f。
机器汇总sim/uart_loader/board/ddr_crc_stage7_board_result.json为board_result=PASS，
两单轮result.json和独立核验脚本build/check_ddr_crc_board_2026-10-08.py保存复现和范围。
当前两IP的IDF已由用户指向build/ddr_crc对应DAT，ELF/ROM/RAM及仿真全部输入hash仍匹配receipt。
本轮未操作串口、改RTL/C/PC工具、重建镜像或生成/下载位流；未采集已下载位流文件身份。
只有固定64-byte正常CRC实板路径通过；新阶段坏CRC/非法地址/长度/超时/UART错误等实板负例仍待验。
下一步唯一动作：阶段⑧ACK/NACK异常路径专项验收；通过后再进入⑨随机二进制压力测试。
仍不支持任意program.bin下载、正式VERIFY3或RUN4/DDR取指。本轮仅核验归档，不推进后续编码。

## 已有结果：阶段⑦DDR实际读回CRC32仿真PASS

前级固定DDR实板两轮PASS。新增CMD0x12只读0x40000000起64字节，LENGTH描述DDR范围、
UART DATA为空、IMAGE_CRC为PC期望。16次LW的实际内容保存RAM readback后CRC32，
相等ACK64，失配8001且返回actual_ddr_crc；重复校验重新读取，不从UART buffer计算CRC。
PC ddr-crc-test每次先旧DDR_TEST写比较，再CRC只读校验；--count100为100次CRC/200响应。
独立build/ddr_crc，代码2920/常量48/BSS128、730条ISA审查PASS；三次ROM启动PASS，
21帧/两次启动完整真实CPU联仿PASS，覆盖DDR物理损坏、错误PC CRC、未写/复位保留DDR和非法包。
9次CRC校验共144笔真实LW（5次CRC ACK含重复、4次CRC失配NACK），3次旧写比较48 SW/48 LW；
总48 SW/192 LW、Pango AW/W48和AR192。正常23C3E508，损坏AE4B18EA连续两次8001；
错误PC预期23C3E509返回真实DDR23C3E508并8001，同SEQ正确重试ACK；CRC不重写DDR。
非法包/SEQ更换预期/坏DATA CRC/地址/长度/RUN拒绝且不读DDR；复位后直接读取保留DDR也PASS。
RX/pop/MMIO/LBU各1012字节、TX/引脚解码各1260与独立Python/zlib基准匹配；
FIFO峰值1、最低sp3F40/动态栈176字节，20540978退休/56212153周期、Errors0/Warnings0、退出0。
驻留2.06秒、CRC层992.76秒；sim/uart_loader/build/ddr_crc/results.json为DDR_CRC_STAGE_PASS，
保护/候选hash不变、全部输入hash最终核验一致，validated_image.json绑定同一DAT，验收后未重建。
21个共享RTL与前阶段hash相同；未改RTL/IP/PDS或操作串口，无新阶段实板部署。
PC工具离线100次/200应答及每次最多7字节read测试PASS；拒绝包CRC有效但DDR CRC错误的伪ACK。
ROM SHA256=21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a，
RAM SHA256=59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a。
当时共享RTL/IP/PDS不改，生产IP保留用户ddr_fixed引用；原阶段源码/镜像/工具先归档ddr_fixed_stage3。
详见doc/uart_loader/UART_Loader_DDR读回CRC32阶段7_2026-10-08.md；仿真完成时实板待验，后续结果见上方。
下一步唯一动作：同时用build/ddr_crc的ROM/RAM两DAT生成IP/位流并上板，COM11每轮先KEY0复位、
等待DDR初始化，执行--count100 ddr-crc-test；每轮100条CRC32 PASS/200应答，分别保存
board/ddr_crc100.json与ddr_crc100_after_reset.json。前级ddr_fixed位流会拒绝新CMD0x12。

## 已有结果：阶段④⑤⑥固定数据DDR写读比较实板PASS，两轮各100次ACK

用户提交COM11首轮DDR_TEST1–100 ACK输出，随后第二次从SEQ1开始得到NACK8009。
8009是SEQUENCE_ERROR，区别于DDR失配800B；提示序号状态未重新初始化，复位未生效是推断。
核验期间用户更新了ddr_fixed100_after_reset.json，最新文件为SEQ1–100全部ACK。
独立使用struct/zlib逐帧核对两轮全部200帧：请求Header/地址0x40000000/64-byte固定payload、
SEQ1–100、Header和DATA CRC，以及响应Header/命令/status0/accepted64等全部PASS。
复位凭据是此前要求的after_reset日志及SEQ重新从1成功，未独立观察实体按钮；
不能把最初的8009当作复位后PASS，早先失败保留在提交附件来源记录中，原临时JSON已被重测覆盖。
首轮固定归档sim/uart_loader/board/ddr_fixed100_first_verified.json，SHA256=
4f753811e65ea711306a04938a14a33ead3473c9ff8b8d5424504f52166f59a8，RTT15.395–16.111ms。
第二轮归档ddr_fixed100_after_reset_verified.json，SHA256=
94876ca7bb2dd8a5ce2f29b0cbf026a324ecf22508eba8123456370506ef5a33，RTT15.390–16.070ms。
机器汇总sim/uart_loader/board/ddr_fixed_stage3_board_result.json为board_result=PASS；
共200 ACK、12800字节固定payload、20000字节请求、12000字节响应，重复操作同一64-byte DDR区域。
两块IDF已由用户切到build/ddr_fixed的对应DAT，ELF/ROM/RAM与仿真receipt哈希一致；
本轮只读核验并保存证据，没有操作串口、重建DAT、生成/下载位流，未采集下载位流身份。
此PASS只覆盖固定64-byte数据的DDR写读比较；尚无DDR读回CRC32、随机/大文件下载或RUN。
下一步唯一动作：阶段⑦从DDR实际读回计算CRC32，与PC固定数据CRC比较；本轮未继续编码。

## 已有结果：阶段④⑤⑥固定数据DDR写读比较仿真PASS

按用户指令推进CPU写DDR→读回→比较，只新增受控CMD0x11 DDR_TEST与PC ddr-test。
只允许真实DDR基址0x40000000起64字节；16次对齐SW、fence rw,rw、16次LW及实际读回比较，
匹配才ACK64，失配DDR_ERROR800B；不支持任意BIN/LOAD/VERIFY/RUN，不DDR取指。
独立候选tests/uart_loader/build/ddr_fixed，默认仿真--stage ddr-fixed；三次ROM启动PASS，
17帧/两次启动真实CPU/用户口DDR模型联仿PASS，含真实DDR字节损坏→NACK→同SEQ重写恢复。
80 SW/80 LW、Pango用户AW/W/AR各80；重复/非法包不写DDR，RX/pop/MMIO/LBU各1381，
TX/引脚解码各1020字节与Python基准完全一致。FIFO峰值1、最低sp3F40，栈176/4080字节。
24505631退休/66605160周期，Errors0/Warnings0、退出0；驻留3.49秒、DDR阶段1123.60秒。
sim/uart_loader/build/ddr_fixed/results.json为FIXED_DDR_STAGE_PASS，保护/镜像hash不变，
全部输入hash最终复核一致，validated_image.json绑定同一候选DAT，验收后未重建。
ROM SHA256=a24df3ee6ed1ca07b40bbb258fbfa9160ad2070be099d8e8bb2f795b3a04cae7，
RAM SHA256=59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a。
软件/TB/PC修改前阶段②快照已保存，仿真开发完成时各生产IP仍指向用户已验收rx_fixed，未改共享RTL。
当时无串口操作、IP生成/位流部署，实板待验；后续用户部署和实板结果见上方。详见
doc/uart_loader/UART_Loader固定数据DDR写读比较阶段4至6_2026-10-08.md。
下一步唯一动作：同时用build/ddr_fixed的loader_rom.dat与loader_ram.dat生成IP/位流并上板，
COM11复位前后各100次ddr-test，分别保存board/ddr_fixed100.json和ddr_fixed100_after_reset.json。
该64字节实板PASS前不进入DDR CRC、任意BIN下载或RUN。现有PHY/实板DDR历史证据不替代本诊断实板验收。

## 已有结果：阶段②/③固定接收实板PASS，复位前后各100次ACK

用户提供COM11的RX_TEST1–100全部ACK输出；本机rx_fixed100.json逐帧独立核对请求的
固定64-byte向量、SEQ1–100、响应Header/Payload CRC、status=ACK及accepted_bytes=64均PASS。
共6400 bytes有效payload、10000 bytes请求、6000 bytes响应，往返15.411–16.064ms。
首轮固定归档sim/uart_loader/board/rx_fixed100_first_verified.json，SHA256为
6bc43e1bb6acceeb78387556e55ee8216a76c62cba9bfe003dd8de0d334be38c，汇总rx_fixed100_first_result.json。
当前用户已将两个IDF引用切到build/rx_fixed下对应ROM/RAM DAT，两DAT与仿真验收哈希一致；
本轮只读核对并归档，没有生成/下载位流或操作串口。未采集下载位流文件身份。
用户按此前要求提供复位后第二轮RX_TEST1–100 ACK输出；独立解析rx_fixed100_after_reset.json，
100帧请求编码/SEQ/响应Header与Payload CRC/status/accepted_bytes全部PASS，往返15.450–15.909ms。
固定归档sim/uart_loader/board/rx_fixed100_after_reset_verified.json，SHA256为
2665249a3e5884550d3591570658afda2f424f24acccbc5ace909e8f6aa57f37。
复位操作依据用户提交的所要求第二轮结果，未独立观察按钮；两轮共200 ACK、12800 bytes固定payload。
机器汇总sim/uart_loader/board/rx_fixed_stage2_board_result.json为board_result=PASS。
阶段②/③片内固定接收实板PASS；仍未实现DDR写入/LOAD/VERIFY/RUN，不等于程序下载。
推荐下一步唯一动作：受控固定数据CPU→DDR写入、DDR→CPU读回并逐字节比较验证；本轮只归档，未继续编码。

## 已有结果：阶段②/③固定64-byte接收与CPU轮询FIFO仿真PASS

用户要求执行下一步，仅新增受控CMD0x10 RX_TEST与PC rx-test命令，CPU轮询UART FIFO，
存入片内RAM并校CRC/逐字节比较固定64-byte向量，正确才ACK；不写DDR，不实现LOAD/VERIFY/RUN。
新构建默认tests/uart_loader/build/rx_fixed；当时保留原build/根阶段①镜像与生产IP引用，后续用户部署见上方。
源码/build与TB/PC工具已先保存阶段①快照，说明见doc/uart_loader/UART_Loader固定小数据接收阶段2_2026-10-07.md。
首次65-byte超长用例暴露Header拒绝后阻塞TX导致FIFO不能继续接收；已改为先排空坏帧，
100ms连续空闲后再NACK，失败证据保存在sim/uart_loader/build/debug/rx_fixed_fifo_before_drain。
修复后构建ROM2236/常量48/BSS92 bytes、559条ISA审查PASS；新候选驻留3次复位PASS，最低sp3F40。
真实CPU14帧/两次启动全部PASS：4唯一接收+1重复、4正常PING与5个NACK；
RX/FIFO pop/MMIO/CPU LBU各1017 bytes、TX/引脚解码各840 bytes匹配Python/zlib基准与实际RAM。
FIFO峰值1/16、栈176/4080 bytes，19361664退休/52771383周期、DDR请求0、Errors0/Warnings0、退出0。
墙钟876.17秒；sim/uart_loader/build/rx_fixed/results.json为FIXED_RX_STAGE_PASS，
protected_unchanged/image_unchanged均true，validated_image.json绑定同一候选，验收后未重建DAT。
仿真完成时未改IP/PDS、未开串口，实板为NOT_TESTED；后续用户部署/首轮结果见上方当前条目。
两轮固定接收实板PASS后才进入DDR写入/读回。

## 已有结果：UART Loader阶段①PING实板PASS，复位前后各100次ACK

用户提供COM11首轮PING1–100全部ACK的输出；本机ping100.json独立解析核对100帧请求、
SEQ、响应Header/Payload CRC与ACK状态均PASS，往返9.760–10.563ms。
固定证据归档sim/uart_loader/board/ping100_first.json，SHA256为
1595057243e7ed1413fe4e7a047f186575d4dee5c74f78f3e457ee49dc0c9282。
当前ROM/RAM IDF分别已引用tests/uart_loader/build/loader_rom.dat与loader_ram.dat，
两份候选DAT仍匹配仿真验收哈希；这是用户进行的部署，本轮只读核对并归档，未生成或下载位流。
pyserial3.5已由用户安装，COM11为CH340；COM5为蓝牙，之前端口打开失败不属于Loader协议FAIL。
用户确认复位后100次通过；本机ping100_after_reset.json再次独立核对SEQ1–100、请求编码、
响应Header/Payload CRC及ACK状态全部PASS，往返9.758–10.665ms。复位操作依据用户确认记录。
固定归档sim/uart_loader/board/ping100_after_reset_verified.json，SHA256为
f49444d2bbebc409c54faa8023ffac5115bb989f88c015afcdbd6245eb6804d0。
两轮实板共200次有效PING通过，阶段①实板验收PASS；未采集下载位流路径/哈希，
未覆盖断电重上电或高速UART，仍不能声称DDR下载/执行已通过。
推荐下一步唯一动作：阶段②固定小数据接收测试，先核CPU轮询FIFO收到的字节，再逐层接DDR写入与读回。
LOAD/VERIFY/RUN仍未实现，本轮仅归档实板结果，未修改Loader/RTL或重建镜像。

## 已有结果：UART Loader ROM驻留与阶段①PING仿真PASS

用户确认上一轮方案并要求执行，当前仅建立独立ROM常驻最小Loader与PING/ACK，未进入LOAD/RUN。
入口tests/uart_loader/build.ps1、sim/uart_loader/run.py、tools/uart_loader/loader.py；
说明见doc/uart_loader/UART_Loader_ROM驻留与PING阶段1_2026-10-07.md及各README。
构建ROM1876/常量32/BSS76 bytes、469条RV32I机器码审查通过；3次SoC复位/BSS毒化清零/
RAM常量CRC/片内栈验证PASS，ModelSim Errors0/Warnings0、无UART/DDR请求。
默认100次有效PING、1次重复PING和LOAD/VERIFY/RUN三个拒绝应答均PASS，分两次启动且复位后SEQ1可用。
RX/FIFO pop/MMIO/CPU LBU各3744字节、TX/引脚解码各6240字节完全匹配独立Python/zlib基准；
FIFO峰值4/16、最低sp3F60、DDR请求0，编译/运行Errors0/Warnings0、进程退出0。
PING墙钟1863.29秒；results.json为PING_STAGE_PASS，protected_unchanged与image_unchanged均true，
validated_image.json绑定同一候选；LOAD/VERIFY/RUN尚未实现，不宣称DDR下载或执行PASS。
仿真完成时主IP/RAM INIT_FILE/位流未切换，仍为CoreMark validation_60；后续用户部署状态见上方当前结果。
仿真期间生产RTL/IP/PDS及成功Echo/CoreMark镜像受哈希保护；当时未上板或打开串口、pyserial未安装。
推荐下一步唯一动作：用同一已验收ROM/RAM DAT部署最小Loader并做实板PING/KEY0复位验收。
实板PING未PASS前不推进固定数据下载。下方为已有实板结果，不能当成新UART Loader实板PASS。

## 已有结果：两组实板60次CRC与运行时长验收通过

用户2026-10-07标注performance_60/main.dat、validation_60/main.dat并提供两组完整UART。
均Iterations=60、hz=93750000、有Correct operation validated，无ERROR/Errors detected，
Total ticks与PORT_DONE ticks一致；两组seed/list/matrix/state/final全部匹配对应DAT Full Boot凭据。
performance ticks=1664676818，时间17.7565527253秒，final=a14c；
validation ticks=1758636430，时间18.7587885867秒，final=6770。
按配置93.75MHz计时，两组均超过10秒，低于约45.81秒单次测量上限。
据用户UART证据记录两组实板验收PASS；performance按ticks计算约3.379034迭代/秒，
约0.036043迭代/秒/MHz。HAS_FLOAT=0使整数秒和整数除法打印Iterations/Sec=3，未改验收镜像。

原始文本/机器记录在sim/coremark/board/*iter60_user_20261007*；成功DAT直接复制原字节至
tests/coremark_baremetal/verified/{performance_60,validation_60}/main.dat，每组另存verified_image.json。
归档与现有构建DAT哈希均与Full Boot凭据一致；本轮未重建软件或修改算法/RTL/IP/存储深度。
当前主RAM IDF/wrapper/IP TB均引用build/validation_60/main.dat，保持32位数据/12位地址。
保留用户现有PDS/impl/IP生成及其他工作树改动，没有再次下载或运行数小时仿真。
完整结果、复现和证据范围见doc/coremark/CoreMark实板60次验收_2026-10-07.md。
尚未独立测量时钟、采集下载位流哈希或申请EEMBC认证；精确吞吐按配置频率计算。
后续重现用归档原DAT；如修改软件或RTL，重新验收后才能沿用新的结果。以下为此前阶段快照。

## 历史仿真结果：60次两组Full Boot CRC功能验收通过

用户要求执行60次步骤，沙箱外命令已成功。构建显式传ITERATIONS=60和CLOCKS_PER_SEC=93750000，
core_portme.c计时/PORT_DONE频率引用同一编译宏。-Os performance BIN=13220、validation=13228，
各2768条RV32I指令、入口/ABI/ELF-BIN-DAT清单均审查通过，未扩RAM/ROM深度。
输出在tests/coremark_baremetal/build/{performance_60,validation_60}/，保留所有单迭代成功DAT。
ModelSim第一次因小数秒格式启动失败，runner已改整数微秒并使用同一DAT重新启动。
两组完整执行60次，runner退出0，均CRC_FUNCTIONAL_PASS、RESULT: PASS，ModelSim Errors0/Warnings0。
performance seed/list/matrix/state/final=e9f5/e714/1fd7/8e3a/a14c，ticks=736356597；
validation=18f2/e3c1/0747/8d84/6770，ticks=778648235。栈实测均1472/4096字节。
仿真墙钟分别5540.29/5387.02秒（约92/90分钟），两组顺序执行共约3.04小时。
模型程序计时分别约7.85/8.31秒，原版不足10秒错误预期保留；这是功能验收，不是正式实板分数。
完成后重新核对两组ELF/BIN/DAT当前SHA-256，均与验收凭据一致；生产RTL/IP及原成功镜像受保护。
最终凭据目录为sim/coremark/build/{performance_60,validation_60}/，总结果results_60.json。
下一步用已验收performance_60/main.dat切换RAM IP INIT_FILE、重新生成IP和PDS实现后上板，
再用validation_60/main.dat验证。两组实板60次仍未测试，需ticks>=937500000且低于32位计时上限，
核各CRC及Correct operation validated提示，并保存完整UART。无需修改RAM/ROM深度。
最新结果及DAT哈希见doc/coremark/CoreMark_60次迭代构建与上板步骤_2026-10-07.md，以下准备/进行中描述为历史快照。

## 历史准备：60次候选构建与Full Boot入口（当时未执行）

用户问如何进行下一步，已增加tests/coremark_baremetal/build_60.ps1与run.py --iterations 60，
候选放build/{performance_60,validation_60}，保留单迭代成功DAT；TB周期上限按迭代扩展。
多迭代final CRC从对应DAT模型UART记录供实板比较，不能用单迭代final作为期望。
操作说明见doc/coremark/CoreMark_60次迭代构建与上板步骤_2026-10-07.md。
本机exec仍启动失败，本轮无法读取最新git或构建/运行，新入口未验证、60次镜像尚未生成。
用户本机执行build_60.ps1→run.py --iterations 60 --audit-only→run.py --iterations 60，
同一DAT Full Boot通过后才能切RAM INIT_FILE并PDS实现/下载。完整RTL仿真可能数小时/组。
没有修改IP/RTL/深度；尺寸超限时先向用户说明容量缺口和扩深度方案。

## 最新反馈：两组CoreMark单迭代UART CRC均正确（2026-10-07）

用户补充validation串口文本：seed/list/matrix/state/final为18f2/e3c1/0747/8d84/e3c1，
ITERATIONS=1，Total ticks和PORT_DONE ticks均29302693，与已知CRC全部一致。
原文保存于sim/coremark/board/validation_iter1_user_20261007.txt，证据来源为用户粘贴文本。
按93750000Hz换算约0.312562秒，整数秒0及唯一的时间不足ERROR/Errors detected正常。
结合此前performance文本，两组短迭代CRC功能检查均通过，仍不作为正式CoreMark跑分或完整实板PASS。

下一阶段可准备performance/validation各60次的独立候选；按单次线性估算分别17.755/18.754秒，
实际次数/耗时须以新运行ticks为准。先隔离构建、检查尺寸、验收同一DAT，再上板；
多迭代crcfinal不能沿用单迭代e714/e3c1，需独立参考或对应仿真结果。
正式运行需至少10秒、32位计时不溢出、两组CRC正确，并保存完整串口输出。
仍无独立时钟校准或正式分数。本轮终端与Node辅助进程启动失败，未读取最新git/IP状态、
未构建新镜像/跑仿真；仅通过文件补丁保存用户文本、更新相关记录，不修改RTL/IP/已有DAT。
此前16KiB短镜像已装入，当前无扩RAM/ROM深度的理由；新镜像若超限，先告知用户再考虑扩深度。
下方validation实板待验证为此前步骤快照，本条补充新的用户输出证据。

## 最新实板反馈：CoreMark performance单迭代CRC通过（2026-10-07）

用户在上板步骤之后提供完整串口输出，performance seed/list/matrix/state/final为
e9f5/e714/1fd7/8e3a/e714，ITERATIONS=1、ticks=27742465，两处ticks一致。
按用户文本记录performance实板短迭代CRC功能通过，原始文本保存
sim/coremark/board/performance_iter1_user_20261007.txt；详情见CoreMark裸机构建与短迭代CRC文档。
93750000Hz换算约0.29592秒，整数秒=0；唯一ERROR是不足10秒，Errors detected正常保留。
尚无正式分数，亦未独立校准实际时钟。下步先实板validation单迭代（已验收DAT），
核18f2/e3c1/0747/8d84和final=e3c1；performance60次可作后续候选，约17.755秒仅为线性估计，
新镜像须另构建/检查/验收，正式结果以实测ticks>=10秒且计时不溢出及CRC为准。

当前主RAM IDF/wrapper/IP TB已由用户侧切换到tests/coremark_baremetal/build/performance/main.dat，
其哈希仍为已验收52b8b8eafa58bc924c1497e1ff2ba49d071c81e4c0b2bb563a338ee4b04de075。
RAM仍12位地址/32位数据（16KiB），ROM loader未改。本轮保留PDS/impl/IP生成等新工作区变化，
仅记录用户文本与读配置，没有重编译/仿真/修改IP或下载；未确认位流哈希和validation实板结果。
用户要求修改RAM/ROM深度前先说明容量缺口、建议深度和原因，当前不需要扩深度。
下方主RAM仍为Echo、实板NOT_TESTED等内容为上一阶段快照，最新状态以本条为准。

## 最新接续：CoreMark裸机移植与短迭代CRC通过（2026-10-07）

用户明确授权继续移植，先做构建尺寸和短迭代CRC；本条替代下方“尚未移植/构建”的最新状态。
已建立tests/coremark_baremetal独立端口、构建/转换与sim/coremark真实CPU Full Boot验收，
保留coremark-main五个算法.c、coremark.h和清单原字节，没有修改CPU/互连/UART/DDR生产RTL。
详见doc/coremark/CoreMark裸机构建与短迭代CRC_2026-10-07.md；旧源码核对文档继续保留版本/MD5说明。

统一-O2的performance BIN=17108超过16368，转换拒绝；统一-Os后performance=13216、
validation=13224，两组ELF入口0x40000000，RV32I/ILP32，2766条最终指令审查，无未解析符号。
静态2000字节、单线程、volatile种子、整数MMIO计时93750000Hz，原版时间检查保留。
ModelSim ITERATIONS=1两组2/2 CRC_FUNCTIONAL_PASS：
performance seed/list/matrix/state=e9f5/e714/1fd7/8e3a，final=e714，ticks=12271801；
validation=18f2/e3c1/0747/8d84，final=e3c1，ticks=12974244。
两组都验证原ROM搬最终DAT、毒化BSS清零、UART TXD独立解码和计时接受周期差，
栈实测1472/4096字节，ModelSim编译/运行Errors0/Warnings0，无异常/总线错误。
短运行约0.13秒，原版ERROR时间不足及Errors detected预期存在；不是正式CoreMark分数。

复现：先./tests/coremark_baremetal/build.ps1 -Mode performance -Iterations 1，再-Mode validation，
然后C:/python/python.exe sim/coremark/run.py（仅读已有DAT，不自动重建；--audit-only仅尺寸/布局检查）。
已验收镜像在tests/coremark_baremetal/build/{performance,validation}/main.dat；日志/UART/哈希凭据在
sim/coremark/build/<mode>/，总结果results.json。验收后不要另生成DAT直接上板。
主RAM IP仍引用Echo，输出30/Echo成功DAT哈希不变，PDS/impl/既有日志和删除等改动保留。
无IP切换/PDS实现/下载/实板CoreMark，无PHY训练/长迭代或跨32位回绕测试；生产RTL及共用TB未改，
本次没有重跑完整DDR/全CPU/UART回归。下一步可先用同一短DAT上板校准计时并捕获UART，
再据实板速度确定10–30秒迭代，performance/validation各满足至少10秒且不超过32位计时上限后报告分数。
没有提交/推送或联系其他对话。

## 本次交接入口：CoreMark源码已提供并核对（2026-10-07）

用户提供D:/riscv/RISCV/coremark-main，要求阅读源码并更新相关文件，准备移交下一对话。
本次完成源码/平台静态核对和文档更新，未移植/构建/运行CoreMark，没有CoreMark PASS或分数。
优先读doc/coremark/CoreMark源码核对与移植交接_2026-10-07.md，里面给出缺口、配置、CRC、
装载/栈/计时限制和下一步实施顺序；2026-10-04准备文档保留为旧快照。

五个算法.c与随包MD5清单一致，coremark.h与清单不一致，但其Git blob
d0542004edffe6685e093892980b35d96db5ab04与本次官方GitHub文件相同；不改源码/清单。
barebones有计时/初始化/UART三个#error占位，默认主机配置不能直接上板。
本机GCC15.2.0已确认RV32I/ILP32 libgcc路径；仍须检查CoreMark最终镜像及完整运行库。
移植先用静态2000字节、单线程、volatile种子、整数计时/输出；计时MMIO=0x10000008，
93.75MHz，不能rdcycle，32位约45.81秒回绕。当前BIN装载上限16368字节，
64KiB DDR链接范围/4KiB栈也须按实际需求核对；不假定源码存在就能装入现有RAM。
先短Full Boot核对performance/validation CRC，再实板各至少10秒；整数秒截断时
保存iterations/ticks在PC算精确分数。main返回0或LED状态不能单独作为验收依据。

既有Echo实板功能PASS和成功DAT保持不变，当前RAM IP仍指向Echo build/main.dat。
PC→UART→DDR装载器未实现，视镜像尺寸/部署需要再安排，不是开始CoreMark移植的前置。
早期“CoreMark由他人负责”属于历史分工，本次已获源码核对/交接授权；下一对话按最新
用户请求确定开发范围。本轮没有接管完整移植或联系别人。
此前GitHub推送已完成，origin/master与本地HEAD均为f35609d890ddded06f1ac238f4fce95eb91625d5；
本次新增文档/源码尚未提交。源码目录为未跟踪用户文件，PDS/impl/DDR日志/摘要/删除等
原本地改动仍保留，先看git status/diff，勿git add -A或清理/重置。

## GitHub同步准备与发布前复验（2026-10-07）

用户要求更新相关文件到GitHub。发布范围包括tests独立实验、成功镜像、C/Echo仿真
环境、UART引脚/RAM初始化配置及相关文档/实板截图；无关PDS运行状态和临时产物保留本地。
本次没有重编译或转换DAT，直接重跑ModelSim四层4/4 PASS，每层97字节，
Errors0/Warnings0；Echo构建DAT及根归档哈希保持不变。
验收ELF/BIN/DIS/DAT与结果/镜像凭据纳入发布，DAT以.gitattributes保留原字节。
实板结论仍来自此前用户确认，本次没有新增下载/实板测试。
范围、命令和核对记录见doc/uart/UART_Echo_GitHub发布核对_2026-10-07.md。

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
截图、两次用户确认及限制见doc/uart/UART_Echo实板基本回显确认_2026-10-07.md。

下一阶段为PC→UART→DDR装载器：先规划装载器、目标程序和栈的互不覆盖地址区间，
做长度/目标地址检查、校验、ACK、超时与读回校验，再做跳转执行。尚未开始该阶段代码。
下方“复位待补齐/仅基本回显”的描述为前一轮快照，已由本条更新。

## 最新实板进展：Echo基本回显样本PASS（2026-10-07）

用户提交UartAssist截图，随后明确确认已下载Echo位流、USB-TTL连接FPGA并拆除
适配器自身回环。nb两次、小写a、hello 123（带空格）及符号/大小写混合文本都有
对应回显；第二张累计TX/RX均26字节。串口为115200/8N1/无流控。
当前可记录PC→FPGA→PC **实板基本回显样本PASS**，不是适配器自身短接回环。
完整记录及保存截图见doc/uart/UART_Echo实板基本回显确认_2026-10-07.md。

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
完整说明见doc/software/tests恢复旧结构与Echo实验迁移_2026-10-06.md。

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
记录见doc/uart/UART_Echo分层仿真与目录统一_2026-10-06.md和原DDR日志；这些原DDR测试
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
`doc/software/tests目录整理与成功镜像归档_2026-10-06.md`记录构建、迁移及验证。
以下历史段落中的路径已更新以便访问，但日期、当时程序大小/验证范围仍按原步骤理解。

后续进展（2026-10-06）：第 12.1 项已完成独立 C 装载/DDR 执行验收，ModelSim 与
Icarus 各 4/4 PASS，并验证非空 `.data/.bss`、LED PASS/FAIL/超时。
详见 `doc/software/裸机C_BIN到DAT与DDR_LED仿真验收_2026-10-06.md` 及
`sim/baremetal_c/README.md`。下文第 8/9/11/12 节保留交接时快照；其中 C
“尚无执行验证”的描述已由本补充更新。主板级镜像/IP/生产 RTL 仍未切换，未上板。

再后续（2026-10-06）：用户反馈USB-TTL已到货并通过Hello回环，且已手动将
data_ram初始化指向先前 `sim/baremetal_c/build/converted/main.dat`。
对应程序已归档，development中保留工作副本；提供精简printf输出 `30\r\n`，RAM基准为
`tests/fpga_uart_pc_output_30/main.dat`（680字节/170字），原ROM loader兼容。
ModelSim/Icarus各5/5 PASS，真实CPU/DDR执行且TX引脚自动解码30 CR LF通过。
本次没有修改用户当前主IP/PDS/FDC或下载，用户计划自己替换新DAT并上板。
详见 `doc/software/C裸机printf输出30与RAM镜像_2026-10-06.md`。

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
