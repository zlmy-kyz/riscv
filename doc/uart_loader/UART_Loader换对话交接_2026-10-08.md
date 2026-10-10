# UART Loader 换对话交接

## 最新软件扩展：新 C 程序通用入口（2026-10-10）

`tests/c_app/run_app.py --source ... --expect ...` 已独立实现构建、ELF/BIN/ISA 审查、真实 CPU 完整执行仿真及新应用门控，然后由用户确认 KEY0/DDR 就绪后进行 COM11 LOAD/VERIFY/RUN 和输出验证。支持多文件及 `--expect-file`，`--prepare` 不开串口，`--deploy` 复用准备结果。旧白名单/Loader/BSP/主位流保持不变；示例仿真/离线检查通过，新程序实板尚待用户。下面“尚未实现”保留历史。操作及边界见 [通用 C 说明](../../tests/c_app/README.md)和 [实现记录](../software/通用C程序自动构建下载验证_2026-10-10.md)。

## 最新可用硬件：主工程重建位流实板 PASS（2026-10-10）

用户新生成的 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`，SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf，六轮Hello/CRC32/CoreMark短CRC及正式60次全部实板PASS。540响应、6次唯一RUN、零CRC错误/重试/额外RX；两组正式17.750024053/18.752304203秒。549项成功快照在sim/bsp_workflow/rebuilt_20261010/board/first_success，独立报告及归档收据同目录上级；原十轮518项快照仍保留。详见[新位流实板验收](../board/主工程新位流六轮实板验收_2026-10-10.md)。

主IP当前已切verify_run_hello对应DAT，不再是load_stage10；新下载入口tools/uart_loader/candidates/rebuilt_20261010/run_board.py绑定本次新位流，原tests/bsp_workflow/run.py仍绑定旧隔离成功位流，不能混用前置CRC证据。新位流复验完成，下一任务仍CPU瓶颈分析；尚无优化RTL或性能提升结果。

## 当前交接：下一任务为 CPU 性能优化（2026-10-10）

Loader、统一BSP及十轮连续复位下载/VERIFY/RUN已实板PASS并完成归档，不重复这些开发阶段。用户现在准备优化CPU；先读[性能优化起点与验收约定](../CPU性能优化起点与验收约定_2026-10-10.md)，以新BSP成功CoreMark两组BIN/CRC/实测ticks为基准，先统计计时区间CPI及取指、数据、分支停顿。目前仅更新文档，没有性能统计或RTL优化。

新main.c自动编译/审查/下载/验证的通用run_app.py尚未实现；现有工具仅支持已接入应用与冻结门控，不能把--tag当作新程序注册功能。CPU变更需要隔离候选位流、完整正确性回归与新门控；保留成功位流、Loader DAT/IP和全部快照，不跳过旧哈希检查。上板/KEY0/COM11仍由用户操作，Codex负责开发/仿真/离线核验。

## 最新结果：统一 BSP 与十轮实板验收完成（2026-10-10）

同一成功Loader位流连续十轮KEY0/重新下载/VERIFY/RUN全部实板PASS。十份原始JSON独立核验834响应（432ACK/402READY）、10次唯一成功RUN及Hello/CRC32/CoreMark输出，零CRC错误/重试/额外RX。新BSP两组正式60次CRC正确、无ERROR，17.749998571/18.752320843秒；短迭代分别作为第9/10轮前置CRC证据。

本轮任务完成，不再等待十轮操作。独立报告 `sim/bsp_workflow/board/first_independent_result.json` 为UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_VERIFIED；归档收据 `first_submission_result.json` 为UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_ARCHIVE_PASS，518项成功快照在 `first_success/`。冻结380项输入/116项证据/380项副本及旧170/279项成功快照、18项PDS源/副本匹配；门控原NOT_TESTED是历史状态。成功软件/Loader/位流保留，无重新构建；全部物理操作由用户完成，Codex未打开COM11。UART IRQ仍仅仿真通过。详见[实板验收](../software/统一BSP与十轮复位下载实板验收_2026-10-10.md)，下方待实板入口保留历史，不重新执行已完成流程。

## 最新入口：统一 BSP 与十轮验收待实板（2026-10-10）

当前用户要求完成统一BSP和至少10轮复位下载；软件开发、七个隔离BIN构建与审查、八组真实CPU仿真和54项离线检查均完成。新目录 `tests/bsp_workflow/`、`tools/uart_loader/candidates/bsp_workflow/`、`sim/bsp_workflow/`；门控UNIFIED_BSP_SIM_PASS冻结380项输入/116项证据/380项副本，最终pre_board_audit.json PASS。CPU/DDR桥/Loader/成功位流未修改，旧170/279项成功快照匹配。

新60次CoreMark仿真仅覆盖UART装载/VERIFY/RUN/启动，完整算法与时长必须本轮实板验收；两组短迭代完整算法CRC、Hello原速UART、独立CRC32、ECALL/IRQ及cycle回绕仿真PASS。IRQ探针仅仿真，不在六个可部署应用白名单。本轮实板仍NOT_TESTED，不把旧不同BIN的实板结果或离线fixture计作10轮。

下一步由用户保持此前Hello成功Loader位流、关闭串口助手，执行 `& C:/python/python.exe D:/riscv/RISCV/tests/bsp_workflow/run.py --acceptance`，按每轮提示KEY0/等待DDR/回车。固定10轮独立日志在 `sim/bsp_workflow/board/first/`。完成后Codex执行check_ten.py核验真实原始日志并新增成功归档；不重新构建镜像、不打开串口、不代替用户按键。操作与边界见[统一BSP准备](../software/统一BSP与十轮复位下载验收准备_2026-10-10.md)。下方所有“当前/下一步”按记录日期解释。

## 最新结果：同位流第二程序与 CoreMark 实板 PASS（2026-10-09）

用户完成五次COM11下载，Codex独立核验五份原始JSON：第二程序精确输出SECOND_PROGRAM_PASS sum=11440；CoreMark两组1次算法CRC正确，两组60次正式运行CRC正确且无ERROR，分别17.756533472秒和18.758810933秒。437/437响应（226ACK/211READY）、5次唯一成功RUN，零响应CRC错误、零重试/额外RX。均沿用此前Hello成功的同一Loader位流文件身份，无Loader/IP/位流重建。

独立结果 `sim/uart_loader/board/applications_stage3_independent_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_PASS；归档收据 `applications_stage3_submission_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_ARCHIVE_PASS。279项完整成功快照在 `sim/uart_loader/board/applications_stage3_success/`；196项输入/74项证据/196项源副本、旧Hello170项成功快照及PDS副本均匹配。门控生成时NOT_TESTED保留历史，当前结果看新增板级报告。

本次用户指定“第二程序/CoreMark先CRC后正式”两步已完成。额外10轮复位不在本次任务范围，尚未执行，不将原更宽的第③关所有检查记为PASS。Codex未打开串口或操作板子；未独立观察JTAG/KEY0。详见[实板验收](UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。

## 历史准备：同位流第二程序与 CoreMark（2026-10-09）

用户本次选择换第二个C程序，以及CoreMark先验算法CRC再正式运行。隔离开发和集中仿真全部完成：587-byte第二程序原速115200引脚收发/输出PASS，两组CoreMark 1次完整算法CRC PASS，两组60次新UART装载/VERIFY/RUN/启动PASS；60次完整算法复用原逐字节相同BIN的既有Full Boot证据。本次UART实板仍NOT_TESTED，额外10轮复位不在此次任务范围内。

门控 `sim/uart_loader/build/applications_stage3/deployment_gate.json` 为SAME_LOADER_APPLICATIONS_SIM_PASS，冻结196项输入/74项证据/196项源副本，35项PC离线检查PASS。沿用此前Hello成功的同一Loader位流，无Loader/IP/PDS重建；成功170项快照及旧76项输入/71项证据核对一致。失败日志保留，不修改成功镜像。上板/KEY0/COM11由用户操作，Codex未打开串口或下载位流。

下一步用户执行 `D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1`，按提示五次KEY0：second、performance_1、validation_1、performance_60、validation_60。正式模式必须先提供对应短迭代实际CRC日志；结果在 `sim/uart_loader/board/applications_stage3_first/`。完成后离线核验/归档，再记录实板结果。详见[准备记录](UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。

## 最新结果：VERIFY / RUN / DDR / Hello 合并实板 PASS（2026-10-09）

用户完成隔离候选下载和COM11测试，Codex独立核验实际原始JSON：157/157响应（83ACK/49READY/25预期NACK）、4次正式VERIFY的367-byte DDR CRC32均5E142E06，最终SEQ106唯一成功RUN后精确收到13-byte `Hello World\r\n`，零响应CRC错误、零重试/额外RX，用时4.301259秒。精简计划第②关完成，已验收UART下载→正式VERIFY→RUN→DDR应用Hello链路。

汇总 `sim/uart_loader/board/verify_run_hello_board_result.json` 为COMBINED_ACTUAL_BOARD_VERIFIED；归档收据 `verify_run_hello_submission_result.json` 为COMBINED_ACTUAL_BOARD_ARCHIVE_PASS。170项完整成功快照保存在 `sim/uart_loader/board/verify_run_hello_success/`，冻结76项输入/71项证据/76源副本、阶段⑦至⑩成功档案及主PDS/IP/旧成功位流均匹配。原仿真门控内NOT_TESTED是历史生成状态，当前结论看新增板级汇总。详见[实板验收](UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md)。

主工程配置继续保留阶段⑩；用户报告本次下载隔离verify_run_hello位流，PC日志中的位流文件哈希与已审计快照一致。未独立观察下载/KEY0或读回FPGA配置；本轮没有物理DDR损坏或UART线级故障注入。上板、供电、复位和串口由用户负责，Codex只离线核验和归档。本轮不重建镜像、不重复仿真。下一步第③关同位流至少10轮复位、第二BIN和CoreMark；本轮尚未启动。

## 历史准备：VERIFY / RUN / DDR / Hello 合并仿真 PASS（2026-10-09）

精简计划第②关已在新隔离候选 `verify_run_hello` 完成，Loader 与 367-byte Hello 各构建一次。五组真实 CPU 仿真全部 PASS：正向11、错误矩阵157、原速 UART9、UART事件失效恢复25、控制截断/CRC34响应；14项 PC 离线检查 PASS。门控 `COMBINED_SIM_PASS` 冻结76项输入、71项证据和76项源副本，实板仍 NOT_TESTED。

正式 VERIFY 重读整个 DDR 文件 CRC，RUN 要求 VERIFIED 且再次重读，全部 ACK 发完才跳转。仿真已证明真实 DDR 指令退休、应用 gp/sp、非空 data/BSS 清零及精确 Hello。主 PDS/IP/成功位流保持阶段⑩配置，阶段⑦至⑩成功档案保留；新候选 PDS/IP/位流在 `sim/uart_loader/build/verify_run_hello/pds_candidate/`，不重建成功 DAT。

用户最新要求：上板、供电、JTAG下载、KEY0复位和COM11测试由用户操作；Codex提供步骤并离线核验日志，不再操作下载器或串口。隔离位流已生成并审计PASS，最终seed4满足93.75 MHz已有时序约束，8192个初始化字和8个实现网表存储实例均与冻结DAT一致；收据为 `sim/uart_loader/build/verify_run_hello/pds_build_result.json`。JTAG两次扫描仅识别USB Cable II、未发现FPGA，等待现场通电/接好JTAG；COM11仅枚举，尚未下载或打开串口，实板未完成。详情及后续入口见[合并验收记录](UART_Loader_VERIFY_RUN_DDR_Hello合并验收_2026-10-09.md)。后续继续现有候选和冻结镜像，不重新开始开发。

## 历史结果：阶段⑩真实程序LOAD两轮实板PASS（2026-10-09）

用户完成两轮COM11测试；Codex独立核验工程内原始日志，每轮8响应、383-byte真实BIN的DDR读回CRC32均B2E24920，零CRC/UART错误、零重试/额外RX。汇总STAGE10_TWO_ROUND_BOARD_PASS / PASS_LOAD_ONLY_UNVERIFIED，第①关完成。正式VERIFY/RUN和执行尚未实现。

两份固定原始日志和当前PDS/IP/sbit共10文件配置已归档；79项冻结输入、110项证据及79项源副本相同，阶段⑦/⑧/⑨成功档案保留。历史STAGE10_SIM_PASS门控内NOT_TESTED保持生成时状态，当前实板结论看新增汇总。详见[两轮实板验收](UART_Loader真实程序LOAD两轮实板验收_2026-10-09.md)。

当前主IP指向load_stage10成功DAT；下一开发步骤为精简计划第②关：新隔离候选一起实现正式VERIFY、RUN、DDR执行及Hello。上板/复位/供电/COM11全部由用户操作，Codex负责开发、仿真与离线核验。本次已完成板级核验归档，尚未开发第②关功能，不重建成功DAT/BIN。

## 精简计划制定时记录：剩余三个关口（2026-10-09）

用户要求精简阶段，后续按[剩余阶段精简计划](UART_Loader剩余阶段精简计划_2026-10-09.md)推进：①真实程序下载（原⑩，两轮实板PASS）；②正式VERIFY/RUN、DDR执行及基本Hello（原⑪至⑬及⑭基本验收）；③同位流至少10轮复位、第二BIN与CoreMark（原⑭重复/换程序及⑮）。第②关通过即可UART下载并运行DDR程序。原编号保留作证据索引，历史“下一步”按该合并计划解释。

第①关两轮实板日志已核验通过，下一步一起开发第②关隔离候选；不得把LOADED_UNVERIFIED/诊断CRC当作VERIFIED。Codex负责开发、仿真与离线核验，全部上板/复位/供电/COM11由用户操作。本次只改计划文档，不重建或修改成功镜像及阶段⑩冻结输入。

计划精简时的工作区观察（历史）：两主IP INIT_FILE已指向load_stage10同一对DAT，board_top.sbit修改时间2026-10-09 16:37:49；未观察实际下载，工程内阶段⑩两轮日志和汇总均不存在，实板仍待验。79项冻结输入、110项证据和79项源副本哈希匹配；先前439项保护文件中的22项PDS/IP/位流产物已有变化，本次未写这些文件。下文主IP仍为阶段⑨的描述对应候选冻结时的状态。

更新日期：2026-10-09，工程根目录 `D:/riscv/RISCV`。原阶段⑦交接轮仅更新入口/复制成功基线并核验哈希；当前阶段⑨两轮各1000镜像实板PASS，结果见下方。原成功C/工具/RTL和DAT保持不变；当前IP由用户切换到隔离诊断候选。Codex本轮仅核验归档，未重建DAT、生成或下载位流，也未打开串口。

## 历史准备：阶段⑩真实program.bin正式LOAD隔离候选（2026-10-09）

阶段⑨已两轮实板PASS，现开发新load_stage10候选和独立program_stage10应用。新增正式CMD2两次应答：Header→READY→DATA/CRC→CPU写DDR→最终ACK；BEGIN/END、连续地址、total/image_crc身份、重复块精确字节比较且无重写、错误失效及未完成会话5秒超时已实现。383-byte真实ELF/BIN含非空data/bss，两块256+127，最终仅LOADED_UNVERIFIED；VERIFY3/RUN4仍拒绝，持续ROM驻留，没有应用执行。

编译/Harvard/1354条ISA及真实ELF/BIN审查、七组真实CPU/DDR/UART仿真和19项PC离线检查全部PASS：positive49、negative71、extended50、最大61440字节window483、unverified6、原速native8、原速实际BREAK/overflow会话失效及恢复14响应。部署门控STAGE10_SIM_PASS已冻结79项输入和110项证据；阶段⑩实板NOT_TESTED。当前主IP仍为阶段⑨random_stage9成功DAT，PDS/RTL和阶段⑦/⑧/⑨成功档案未改，未打开COM11。

下一步由用户把两IP临时指向load_stage10/build同一对DAT，生成下载位流；KEY0后专用acceptance.py两轮各8响应，得到LOADED_UNVERIFIED/诊断DDR CRC匹配且无Hello，再离线核验两份日志。正式VERIFY在精简计划第②关验收，不能用CMD14诊断CRC授予VERIFIED。操作命令、哈希、复现证据与失败保留见[阶段⑩记录](UART_Loader真实program.bin与LOAD阶段10_2026-10-09.md)。

## 最新结果：阶段⑨随机二进制两轮实板PASS（2026-10-09）

用户完成COM11首轮及after_reset轮；Codex直接读取工程内原始JSON，独立逐帧核验请求、60-byte响应的全部字段/CRC、固定seed输入、镜像/PC工具/部署门控身份及完整数量。每轮1000镜像、17946响应、3700127有效文件字节，1000个整镜像DDR CRC ACK及999个尾哨兵CRC ACK全部通过，零CRC/UART错误、零重试。合计2000镜像、35892响应、7400254有效文件字节；两轮分别549.845/550.179秒，约6729.41/6725.32 B/s，SEQ均1–17946。

板级汇总 `sim/uart_loader/board/random_stage9_board_result.json` 为STAGE9_TWO_ROUND_DIAGNOSTIC_BOARD_PASS / PASS_RANDOM_DIAGNOSTIC_ONLY。两份固定原始日志副本及PDS/IP/当前sbit共10文件配置副本已新增保存；1186项冻结输入及副本、103项仿真证据、阶段⑦37项原始/副本和阶段⑧成功配置档案均未变。部署前286项保护文件中277项未变、9项变化均为用户本次PDS/ROM/RAM/位流部署文件；未覆盖旧成功档案。详见[两轮实板验收](UART_Loader随机二进制两轮实板验收_2026-10-09.md)。

当前两主IP INIT_FILE已由用户指向 `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat` 和同目录 `loader_ram.dat`。Loader从ROM驻留，RAM存放常量/状态/缓冲/栈；CMD13/14仅低60KiB诊断写/真实DDR CRC，不执行随机数据。满61440-byte文件没有实板栈探针，栈保护另有仿真证据；after_reset重新接受SEQ1已核实，KEY0和已下载位流文件身份未独立观察。部署门控的历史NOT_TESTED保持生成时状态，当前实板结论看新增板级汇总。

下一开发步骤为阶段⑩：新独立Hello ELF/BIN/manifest（含非空data/bss），正式LOAD完整END，每块ACK，最终LOADED_UNVERIFIED，持续在ROM、不得输出Hello或自动执行。VERIFY和RUN按后续阶段验收，当前均未实现；本轮只离线核验归档，未开始阶段⑩。成功DAT不重建，后续继续使用隔离候选；上板、复位和串口由用户操作。

## 历史准备：阶段⑨随机二进制/DDR读回CRC隔离候选（2026-10-09）

阶段⑧完整诊断矩阵已两轮实板PASS，用户授权下一步；新候选tests/uart_loader/candidates/random_stage9、新工具tools/uart_loader/candidates/random_stage9、新TB/脚本sim/uart_loader/stage9。新增受限CMD13分块写/CMD14范围CRC，低60KiB窗口，256-byte块，SB前缀/尾部与SW中部；严格同SEQ完整字节比较，重复写不重写且重读CRC；无正式LOAD/VERIFY/RUN或随机数据执行。

编译/Harvard布局/1005条ISA审查、62项负例及恢复、108项旧命令兼容、114镜像/148171字节bulk、原速41响应/10边界文件、原速BREAK/洪泛9响应、独立写后物理损坏7响应及17项PC/独立核验器离线检查全部PASS。部署门控STAGE9_SIM_PASS已冻结1186项输入和103项证据；阶段⑨实板仍NOT_TESTED，当前主IP仍为阶段⑧成功诊断候选。原成功镜像/C/RTL/IP/PDS不改，未打开COM11。

已生成1000实板镜像、3700127有效payload字节、17946停等请求计划（14边界+100组全窗口随机+886组小随机）；每轮至少1000镜像，正常0错误/0重试。现已完成全部仿真/冻结部署门控；下一步由用户用random_stage9/build同一对DAT生成下载诊断位流，KEY0后两轮各1000镜像实板验收，日志再离线核验。详细状态、范围及命令见[阶段⑨记录](UART_Loader随机二进制与DDR读回CRC阶段9_2026-10-09.md)。

## 历史结果：阶段⑧完整异常矩阵诊断候选两轮实板PASS（2026-10-09）

用户提交COM11首轮和after_reset轮，各117/117 PASS。独立struct/zlib核验两轮原始请求/响应、全部字段与CRC、错误恢复、时序和候选/工具/部署门控身份，另逐条对照234条终端PASS。每轮80ACK、37个预期NACK、40个实际DDR CRC ACK；合计234响应、160ACK/74NACK/80CRC ACK，实际DDR CRC均23C3E508。BREAK返回NACK8005且真实UART原因0x10，洪泛先PING ACK再NACK8005且原因0x20，两类故障后PING/DDR CRC全部恢复通过。两轮分别SEQ1–80，日志哈希不同；未独立观察KEY0。

阶段⑧约定的完整实板矩阵已补齐，结论绑定隔离uart_fault_stage8_diag。板级汇总sim/uart_loader/board/uart_fault_stage8_diag_board_result.json为STAGE8_DIAGNOSTIC_TWO_ROUND_BOARD_PASS、PASS_DIAGNOSTIC_CANDIDATE_ONLY；固定两轮JSON/终端及部署工作区10个文件副本已保存。66项输入/58项仿真证据及阶段⑦37项原始/副本哈希仍一致。原成功镜像、r2和原FAIL全部保留；没有改写原二进制验收范围或历史NOT_TESTED报告。

当前两IP已由用户指向tests/uart_loader/candidates/uart_fault_stage8_diag/build/loader_rom.dat与loader_ram.dat；本轮Codex只离线核验归档，未打开COM11、修改RTL/C/工具或重建DAT。磁盘当前sbit已保存副本，未独立核实已下载位流文件身份。详细证据/哈希/复验命令见[两轮实板验收](UART_Loader_UART帧错与FIFO溢出两轮实板验收_2026-10-09.md)。

下一开发步骤为阶段⑨隔离随机二进制/DDR实际读回CRC压力验收；本轮未启动。仍仅固定64-byte DDR诊断，不支持任意BIN或正式LOAD/VERIFY/RUN。上板、复位、串口继续由用户负责。

## 历史准备：阶段⑧UART帧错/溢出实板注入准备（2026-10-09）

用户要求补齐剩余两类实板故障，所有上板/复位/串口操作仍由用户负责。原成功镜像和主IP不改，新增隔离诊断候选tests/uart_loader/candidates/uart_fault_stage8_diag：清错前记录真实STATUS[4:5]，8005响应capabilities bit24/25镜像原因，分别要求0x10/0x20，避免仅凭共用8005推测两项通过。

原速纯引脚9响应和三次ROM启动PASS：BREAK产生1次真实帧错，PING ACK期间96-byte洪泛产生43次真实FIFO溢出、丢43字节，峰值16、两次W1C；不force CPU/UART/FIFO。105.348/116.719ms恢复，PING/DDR CRC通过。PC13项与独立核验器11项离线PASS，108帧候选host回归PASS；部署门控STAGE8_UART_DIAGNOSTIC_SIM_PASS，已冻结66项输入副本。新候选实板仍NOT_TESTED，现可交给用户上板验收。详见[注入准备与用户操作](UART_Loader_UART帧错与FIFO溢出实板注入准备_2026-10-09.md)。

候选host回归、部署门控和同一DAT身份已完成冻结；下一步由用户临时切换两IP/生成下载诊断位流，KEY0后运行诊断acceptance.py --mode all两轮（每轮117响应，原108+线级9）。原阶段⑦/阶段⑧r2成功和FAIL证据全部保留，诊断候选身份与旧二进制分开记录，尚不推进⑨或LOAD/VERIFY/RUN。

## 历史结果：阶段⑧主机可注入异常两轮实板PASS（2026-10-08）

用户用PC工具r2在COM11提交首轮与after_reset轮；独立struct/zlib逐帧核验两份原始日志、请求矩阵、响应全部字段/CRC、时序、额外RX检查记录与终端输出，每轮108/108 PASS：73ACK、35个预期NACK、37个DDR CRC ACK。合计216帧、146ACK、70个预期NACK、74个CRC ACK，实际DDR CRC均23C3E508；错误后的合法PING/CRC恢复全部通过。两轮均接受新SEQ1并完成至SEQ73；未独立观察KEY0，未采集板上位流文件身份。

现行板级汇总为sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json，board_result=PASS_HOST_INJECTABLE_ONLY；UART帧错/FIFO溢出实板仍NOT_TESTED，阶段⑧完整实板范围NOT_COMPLETE。旧ack_nack_stage8_board_result.json及原首轮误报FAIL保留为历史证据，不覆盖；旧仿真报告内NOT_TESTED也保留生成时状态。详见[两轮验收记录](UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。

成功ELF/ROM/RAM、阶段⑦37项快照、阶段⑧27项候选、PC原/r2的11项输入档案及全矩阵221项保护文件/25项仿真输入哈希均匹配。未重建DAT、修改C/RTL/IP/PDS或重新仿真；Codex仅离线核验/归档，所有上板操作继续由用户负责。本轮未启动⑨随机BIN或正式LOAD/VERIFY/RUN；后续须保留上述实板覆盖边界并使用隔离候选。

## 历史记录：首轮PC时序误报与r2复验准备（2026-10-08）

用户已运行首轮：终端94条PASS后停止，第95条truncated_magic_recover_ping记录FAIL。独立struct/zlib核对全部已收95个原始响应及请求矩阵，字段/CRC/预期状态全部一致；truncated_magic正确NACK8004为207.309ms，随后SEQ64合法PING ACK为10.289ms。错误来自PC工具：startswith('truncated_')把恢复PING/CRC也要求>=195ms；旧离线fixture同样给这些恢复ACK加延迟，掩盖了误判。原FAIL日志/终端和输入副本保留，不改写PASS；最后一帧没有完成额外RX检查，整轮仅记录94个完整工具PASS，第二轮尚未提交。

修正版在tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py，仅对negative且预期status8004的真正截断包施加195ms下限；独立核验器sim/uart_loader/stage8/check_board_r2.py同步修正。12项时序回归复现旧95帧失败、修正版108帧快速ACK通过，且4类早到超时NACK仍拒绝；另8项通用PC离线检查PASS。成功C/RTL/IP/DAT和原仿真输入不变，不需要新位流/重建DAT。Codex未打开COM11，实板操作仍由用户负责。

板级门控sim/uart_loader/board/ack_nack_stage8_board_result.json为INCOMPLETE_RETEST_REQUIRED_PC_TIMING_FIX，不是阶段⑧实板PASS。详见[PC时序误报及r2复验](UART_Loader_ACK_NACK实板首轮时序误报与PC工具r2_2026-10-08.md)。下一步用户KEY0复位并等DDR后，使用r2工具和新日志ack_nack_stage8_first_pc_r2.json；再复位后另跑ack_nack_stage8_after_reset_pc_r2.json。每轮108/108 PASS再离线核验。不得继续阶段⑨，UART帧错/溢出实板仍未覆盖。

## 历史记录：阶段⑧专项仿真与实板准备（2026-10-08）

用户分工（2026-10-08）：实板下载、供电、KEY0复位和COM11串口验收由用户自行操作；Codex提供脚本/命令，并在用户提交日志后进行离线核验与归档。本阶段不由Codex打开COM11。每轮预期108帧全部PASS（73ACK/35个预期NACK，37个CRC ACK）；预期NACK本身是通过条件，任何RESULT: FAIL/超时/字段或CRC异常均须保留日志后停止。UART帧错/溢出实板仍未覆盖。

阶段⑧专项仿真已PASS，实板仍待验：修复隔离检查器的丢字节计数后从头完整114帧/37负例PASS，另有native8帧原速超时和uart8帧故障恢复PASS；Errors/Warnings0。机器门控为sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json。详情、原FAIL保留、成功输入归档、候选目录及实板命令见[阶段⑧记录](UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。

成功ELF/DAT只是逐字节复制至tests/uart_loader/candidates/ack_nack_stage8，未重建；主IP仍引用原build/ddr_crc。PC工具tools/uart_loader/candidates/ack_nack_stage8/acceptance.py为108帧/35个主机可注入负例，每项后PING/DDR CRC恢复。用户说明板子已经断电，本轮未操作COM11；先恢复原成功位流、KEY0复位并等DDR初始化，再进行两轮实板测试，保留UART帧错/溢出实板未覆盖边界。不推进⑨或LOAD/VERIFY/RUN。下方原阶段⑦交接内容继续作为成功基线说明。

## 新对话先读

1. 根目录 `AGENTS.md`、`doc/CODEX_HANDOFF.md`，再读本文件。HANDOFF 顶部是最新状态，下方“已有结果”保留当时记录，旧“当前/下一步”不覆盖顶部结论。
2. `doc/uart_loader/UART程序下载Loader调查与方案_2026-10-07.md`：真实地址、ROM/RAM 分离限制、后续下载布局与协议方案。
3. `doc/uart_loader/UART_Loader_DDR读回CRC32阶段7_2026-10-08.md`：当前实现和阶段⑦验收。
4. `tests/uart_loader/README.md`、`sim/uart_loader/README.md`、`tools/uart_loader/README.md`，再查对应源码和实际 RTL/IP 配置。

## 当前完成范围

| 层级 | 最新结果 | 范围 |
| --- | --- | --- |
| PC ↔ FPGA UART Echo | 实板 PASS，复位后重复成功 | 基础收发；成功镜像保留在 Echo 实验 |
| ① PING/ACK | 实板两轮各 100 ACK | ROM 常驻 Loader |
| ②③ 固定数据接收/FIFO 轮询 | 实板两轮各 100 ACK | 64 字节收到片内 RAM |
| ④⑤⑥ CPU 写 DDR/读回/比较 | 实板两轮各 100 ACK | `0x40000000–0x4000003F` 固定 64 字节 |
| ⑦ DDR 实际读回 CRC32 | 实板两轮各 100 CRC32 PASS | 合计 400 ACK：200 写比较 + 200 CRC 校验 |
| ⑧ ACK/NACK 异常专项 | 隔离诊断候选完整矩阵实板两轮PASS | 每轮117响应/37预期NACK，含帧错0x10、溢出0x20和恢复；旧二进制范围单独保留 |
| ⑨ 随机二进制压力 | 隔离random_stage9两轮各1000镜像实板PASS | 35892响应/7400254有效文件字节，完整DDR CRC相等，零错误/零重试；仅低60KiB诊断，正式LOAD/VERIFY/RUN未实现 |
| ⑩ 真实program.bin下载 | 隔离候选七组仿真/PC离线PASS，实板NOT_TESTED | 两次应答正式LOAD，383-byte真实BIN含data/bss，LOADED_UNVERIFIED；下一步用户两轮实板，不执行 |

历史自检、Echo 和 CoreMark 走旧 ROM 复制预置 RAM 至 DDR 的启动流程，其 DDR 执行证据仍保留；不能作为 UART 下载执行链已经通过的证据。历史 CoreMark 实板 60 次 CRC PASS 与本 Loader 下载阶段分开记录。

## 当前启动与地址

板级 `board_top → soc_ddr3_top → soc_top → mycpu_sync`；DDR 初始化/锁定后释放 CPU，复位 PC 为 `0x00000000`。当前 ROM 常驻 UART Loader 等待报文，数据 RAM 存放常量、状态、接收缓冲和栈，不自动复制旧自检程序或跳转 DDR。

| 实际地址 | 当前用途 |
| --- | --- |
| 指令总线 `0x00000000–0x00003FFF` | 16 KiB ROM，Loader `.text` 从 0 开始，random_stage9候选4020字节 |
| 数据总线 `0x00000000–0x00003FFF` | 独立 16 KiB RAM，不能当作当前可执行 RAM |
| `0x20–0x2F` | 4 字诊断区 |
| `0x100–0x16F` | 当前 `.rodata` 112 字节，链接预留到 `0xFFF` |
| `0x1000–0x1093` | 当前 `.bss` 148 字节，链接预留到0x1FFF |
| `0x2000–0x2347` | RX请求292字节、最近成功请求292字节、CRC scratch256字节，共840字节 |
| `0x3000–0x3FEF` | Loader 栈，初始 SP `0x3FF0`，向下增长；末 16 字节保留 |
| `0x10000000–0x10000FFF` | 原 MMIO |
| `0x10001000–0x1000100F` | UART：TX/RX/STATUS/CONTROL 偏移 0/4/8/C |
| `0x40000000–0x5FFFFFFF` | RTL DDR CPU 字节窗口，512 MiB；本阶段诊断限定低60KiB `[0x40000000,0x4000F000)`；后4KiB应用栈不可写 |

CPU 编译参数 `-march=rv32i -mabi=ilp32`，不使用 M/C 或 FENCE.I。UART 当前 93.75 MHz、115200 8N1、814 clk/bit、16 字节 RX FIFO、CPU 轮询，IRQ 默认禁用。共享 DDR 桥一次单拍事务、数据优先，128 位用户拍选择 32 位槽位并扩展字节使能；用户地址按 16 位字计，不能直接按标准 AXI4 使用。当前CMD13支持SB前缀/尾部和对齐SW中部；CMD14对实际DDR范围分块累计CRC。旧CMD11/12的固定64-byte路径保留。

## 已验收文件身份与保存规则

当前两块主 IP 的 IDF `INIT_FILE` 分别指向：

- `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat`
- `tests/uart_loader/candidates/random_stage9/build/loader_ram.dat`

当前候选哈希见顶部两轮验收记录；下方保留阶段⑦成功基线身份。阶段⑦核验身份如下，验收后未重建：

| 文件 | SHA256 |
| --- | --- |
| `loader.elf` | `49744ef735f2c14461594969004641f318f62991589aadf2209f9e15cf6de178` |
| `loader_rom.dat` | `21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a` |
| `loader_ram.dat` | `59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a` |

阶段⑦快照已逐文件复制并验证，共 37 个文件：

- 软件源码/启动/链接/构建脚本及 ELF/DAT：`tests/uart_loader/verified/ddr_crc_stage7/`，产物在其 `build/`。
- PC 工具/协议/依赖：`tools/uart_loader/verified/ddr_crc_stage7/`。
- runner/TB/模型和验收结果副本：`sim/uart_loader/build/ddr_crc_stage7_sources/`。
- 复制清单及哈希：上述目录 `archive_receipt.json`，`status=STAGE7_ARCHIVE_PASS`。
- 归档复现脚本：`sim/uart_loader/build/archive_stage7_2026-10-08.py`，只允许新增或与已有档案逐字节相同，不覆盖不同内容。后续修改源码后不要再用它归档阶段⑦。

**不要直接执行无参数 `tests/uart_loader/build.ps1`：它仍默认写 `build/ddr_crc`，尚未将这份新实板成功目录加入脚本保护。** 本次不改构建脚本，保留其与仿真输入哈希一致。后续候选须显式用隔离 `-OutputDirectory`，先完成对应层级仿真，再使用同一对 DAT 上板；不要覆盖阶段⑦、Echo/CoreMark、旧阶段镜像或证据。

工作树已有大量未提交内容，先看 `git status/git diff`，不要 reset/clean，不要据名称删除 IP、镜像或日志。部分本地文档/产物被 gitignore 忽略；本次保存是本机文件交接，不代表已提交或推送。

## 协议和测试入口

当前诊断命令：PING、`0x10 RX_TEST`、`0x11 DDR_TEST`、`0x12 DDR_CRC_TEST`、`0x13 RANDOM_WRITE`、`0x14 RANGE_CRC`。新命令详细字段与范围见阶段⑨记录；CMD14请求DATA为空，LENGTH是DDR范围长度。正式 LOAD `0x02`、VERIFY `0x03`、RUN `0x04` 尚未实现，返回命令错误，禁止自动执行程序。

32 字节小端 Header 格式 `<4sBBH6I>`：MAGIC `RVLD`、VERSION 1、CMD、FLAGS 0、SEQ、ADDRESS、LENGTH、TOTAL、IMAGE_CRC、HEADER_CRC（前 28 字节 CRC）。后接 DATA 和 4 字节 DATA_CRC。CRC32 是反射式 `0xEDB88320`，初值/最终异或均 `0xFFFFFFFF`，兼容 Python zlib。

CMD11 固定地址 `0x40000000`、LENGTH 64、DATA 64 字节，CPU 写/读/比较后 ACK64。CMD12 同地址/LENGTH，但 DATA 为空、DATA_CRC=0、TOTAL=0、IMAGE_CRC 为 PC 预期：**请求只有 36 字节，LENGTH 表示 DDR 区域长度，不能用通用 `36+LENGTH` 解析它。** CPU 实际 16 次 LW 后对读回内容计算 CRC，不回传整个程序；匹配 ACK64，否则 `CRC_ERROR=0x8001` 并返回实际 DDR CRC。

CMD12 同 SEQ/同预期重复请求也重新读取 DDR；同 SEQ 换预期返回 `SEQUENCE_ERROR=0x8009`，失败不推进成功序号。其他状态：ADDRESS `0x8002`、LENGTH `0x8003`、TIMEOUT `0x8004`、UART `0x8005`、VERSION `0x8006`、COMMAND `0x8007`、STATE `0x8008`、DATA `0x800A`、DDR 比较失配 `0x800B`；ACK 状态 0，NACK 带具体错误码。

正常固定 CRC `0x23C3E508`。PC 的 `ddr-crc-test --count 100` 为 200 个停等请求/应答（写比较 SEQ 奇数、CRC SEQ 偶数），不是连续程序下载。每次 CLI 从 SEQ1 开始，须 KEY0 复位并等 DDR 初始化，关闭串口助手；复测使用新日志名，保留成功档案。

```powershell
cd D:/riscv/RISCV
# 可选复测；本次交接没有执行此串口命令：
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_crc100_recheck.json ddr-crc-test
```

本机 `C:/python/python.exe` 已安装 pyserial 3.5；先 cd 工程根目录，避免从用户目录运行相对路径。离线重验板级证据可执行 `C:/python/python.exe sim/uart_loader/build/check_ddr_crc_board_2026-10-08.py`，不占串口。

## 证据与限制

- 阶段⑨当前板级汇总：`sim/uart_loader/board/random_stage9_board_result.json`，两轮各1000镜像实板PASS；固定原始日志/配置副本、范围与哈希见[验收记录](UART_Loader随机二进制两轮实板验收_2026-10-09.md)。下列阶段⑦/⑧证据保留各自历史范围。

- 阶段⑧历史板级汇总：`sim/uart_loader/board/uart_fault_stage8_diag_board_result.json`，`PASS_DIAGNOSTIC_CANDIDATE_ONLY`，完整约定异常矩阵两轮PASS；固定归档与哈希见顶部验收记录。原r2汇总及首轮PC误报FAIL门控继续保留为历史。
- 阶段⑦板级门控：`sim/uart_loader/board/ddr_crc_stage7_board_result.json`，`board_result=PASS`；两轮固定归档 `ddr_crc100_first_verified.json`、`ddr_crc100_after_reset_verified.json` 和 `ddr_crc100_console_verified.txt`，每轮有独立 result.json。原 live 日志不可取代固定归档身份。
- 仿真：`sim/uart_loader/build/ddr_crc/results.json` 为 `DDR_CRC_STAGE_PASS`，`validated_image.json` 绑定 ELF/DAT；3 次 ROM 启动、21 帧/两次启动，48 SW/192 LW（CRC 144 LW），FIFO 峰值 1，Errors/Warnings 0，输入及镜像哈希一致。该旧仿真报告内 `board_result=NOT_TESTED` 是生成时状态，后续实板结论看独立板级门控，不修改历史报告。
- 仿真模型含用户口延迟/背压、物理内容损坏与重复重读检查，不含 DDR PHY 训练；正常板级 CRC 通过不代替异常专项或高速压力测试。
- 两轮总 12800 字节写 payload 是重复写同一 64 字节，并非已覆盖 12800 个不同 DDR 地址。未采集已下载位流文件/哈希；复位证据是用户按要求提交 after_reset 轮并 SEQ1 重启成功，未独立观察按钮。
- 现有桥没有 DDR 事务 watchdog。DDR 总线永久停顿时 CPU 无法返回 TIMEOUT，只能由 PC 等待超时；不能在下一阶段把这两种超时混为一项已支持行为。

## 历史阶段⑧结论与后续边界

完整约定异常矩阵已在隔离诊断候选两轮实板PASS，包含UART帧错/溢出及恢复，见顶部最新结果；⑨本轮未启动。下文保留原方案约束。原要求：对照现有 C/PC/TB 实现列出专项用例，在隔离目录开发最小所需测试，不直接扩展任意 BIN/RUN。覆盖 Header/DATA CRC 错误、非法地址/对齐/长度、版本/命令/序号、截断包接收超时、UART sticky 错误和错误后恢复；坏 Header 的恢复会先排空并等待 100ms 连续 idle，再发 NACK，工具须按实际时序设置超时。UART 帧错/溢出若主机串口无法可靠注入，明确保留仿真证据和实板未覆盖，不声称专项全通过。

每项保存：输入原始字节、预期状态、实际原始响应及字段/CRC、耗时、后续合法 PING/固定 DDR CRC 恢复结果、日志、候选 ELF/DAT 哈希、仿真命令与结果。仿真另检查非法请求无 DDR 写入/跳转，当前 RAM/栈及基线受保护。

PASS：错误码与约定一致、响应本身可校验、合法恢复成功、固定数据 CRC 仍一致、没有越界写/跳转；FAIL：误 ACK、错误码不符、丢响应/无法恢复、错误响应包 CRC、非预期修改 DDR 或进入执行。前级 FAIL 即停；完成专项并明确覆盖范围后才进入⑨随机二进制压力测试。高速波特率、DMA、Hello World/CoreMark 下载执行继续后置。

新对话可以直接发送：

> 工程在 D:\riscv\RISCV。先读 AGENTS.md、doc/CODEX_HANDOFF.md、doc/uart_loader/UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md 和换对话交接说明。精简第①关阶段⑩两轮实板PASS、第②关VERIFY/RUN/DDR/Hello合并实板157/157响应PASS，4次正式VERIFY及最终唯一RUN的367-byte DDR CRC32为5E142E06，精确Hello输出，零CRC错误/重试/额外RX。已独立核验实际原始日志并归档170项成功快照，新冻结输入/证据与旧成功档案保留。下一步第③关：同一成功Loader位流至少10轮复位、第二BIN及CoreMark；使用独立应用/工具候选，不重建或修改成功Loader DAT/BIN/位流，主PDS/IP继续保留阶段⑩配置。上板、供电、JTAG下载、复位和COM11全部由我操作，Codex负责开发、仿真、步骤和离线核验。
