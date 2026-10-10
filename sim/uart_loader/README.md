# UART Loader ROM驻留与DDR CRC32分层仿真

2026-10-09最新：VERIFY/RUN/DDR/Hello合并实板157/157响应PASS，DDR CRC32 5E142E06，唯一RUN后精确Hello；零CRC错误/重试/额外RX，独立核验和170项成功快照归档完成。第②关完成，下一步第③关同位流复位/第二BIN/CoreMark。成功Loader、应用和位流不重建；用户负责实板操作。见[实板验收](../../doc/uart_loader/UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md)。

下方保留集中仿真及准备阶段历史。

2026-10-09最新：VERIFY/RUN/DDR执行/Hello已合并开发，五组集中仿真和14项PC离线检查PASS，冻结门控COMBINED_SIM_PASS；隔离位流与时序/初始化审计PASS，JTAG仍未发现FPGA，实板待验。新候选verify_run_hello及其PDS/IP均隔离，原成功镜像保留。见[合并验收](../../doc/uart_loader/UART_Loader_VERIFY_RUN_DDR_Hello合并验收_2026-10-09.md)。本轮用户自行完成下载、供电/JTAG、复位和串口测试，Codex提供步骤并核验日志。

下方保留此前阶段⑩及更早记录，历史“尚未实现/用户操作”对应其记录时间。

2026-10-09最新：阶段⑩真实program.bin正式LOAD两轮各8响应实板PASS，DDR读回CRC32 B2E24920，零错误/重试；独立原始日志核验和成功配置归档完成。状态仍为LOADED_UNVERIFIED，正式VERIFY/RUN/执行尚未实现。精简计划第①关完成，下一步新隔离候选合并开发第②关VERIFY/RUN/DDR执行/Hello。保留当前load_stage10成功DAT/BIN及所有旧档案，上板/复位/串口由用户负责。见[实板验收](../../doc/uart_loader/UART_Loader真实程序LOAD两轮实板验收_2026-10-09.md)。

阶段⑨两轮各1000镜像实板PASS，固定证据和成功镜像继续保留。

## 历史准备与验收记录

下方“当前/下一步”按记录时点保留，最新状态以上述阶段⑩实板结论为准。

2026-10-09最新：阶段⑧完整约定异常矩阵已在隔离uart_fault_stage8_diag两轮实板PASS，每轮117项（80ACK/37预期NACK/40实际DDR CRC ACK）；帧错返回真实状态0x10，FIFO溢出返回0x20，随后PING/DDR CRC恢复全部通过。原始帧与终端输出已独立核验，汇总为sim/uart_loader/board/uart_fault_stage8_diag_board_result.json。当前IP由用户指向诊断候选DAT，阶段⑦成功镜像及旧证据保留；⑨尚未启动，正式LOAD/VERIFY/RUN未实现。详见[两轮实板验收](../../doc/uart_loader/UART_Loader_UART帧错与FIFO溢出两轮实板验收_2026-10-09.md)。下方保留此前准备/验收记录。

2026-10-09当前继续阶段⑧UART帧错/FIFO溢出实板验收：隔离uart_fault_stage8_diag诊断候选的原速线级9响应、108帧host回归及PC/核验器离线检查全部PASS，部署门控已冻结66项输入副本；新实板仍NOT_TESTED。该候选上报真实STATUS0x10/0x20，原成功C/RTL/IP/DAT不改。下一步由用户生成下载诊断位流，KEY0后运行专用acceptance.py --mode all两轮。详见[候选身份、DAT及操作说明](../../doc/uart_loader/UART_Loader_UART帧错与FIFO溢出实板注入准备_2026-10-09.md)。

2026-10-08最新：阶段⑧主机可注入ACK/NACK异常实板两轮PASS；每轮108帧、73ACK/35个预期NACK、37个DDR CRC ACK，独立原始帧核验及终端对照通过。现行PC工具为tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py；当前汇总sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json为PASS_HOST_INJECTABLE_ONLY。UART帧错/FIFO溢出实板仍NOT_TESTED，完整实板范围NOT_COMPLETE；⑨本轮未启动。成功ELF/DAT/C/RTL/IP不改，原第95帧PC误报FAIL保留。见[两轮验收记录](../../doc/uart_loader/UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。所有上板/复位/串口操作继续由用户负责。

以下为阶段⑧实板提交前的仿真与准备记录；最新板级结果以顶部为准，旧工具仅保留复现历史误报。

2026-10-08新增：阶段⑧ACK/NACK专项仿真PASS，实板待验。完整114帧/37负例修复检查器后从头重跑PASS，另有原速超时与UART故障各8帧PASS；生产C/RTL/IP及成功DAT不改。见[阶段⑧记录](../../doc/uart_loader/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。独立仿真入口sim/uart_loader/stage8/run_repaired.py；成功机器门控sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json。PC实板专项工具tools/uart_loader/candidates/ack_nack_stage8/acceptance.py为108帧/35负例。先恢复已有阶段⑦成功位流、KEY0复位并等DDR初始化，串口助手保持关闭；本轮未打开COM11。下方阶段⑦成功记录和旧入口继续保留，不能用旧runner冒充阶段⑧验收。

当前阶段⑦正常路径实板已PASS，换对话读 [交接入口](../../doc/uart_loader/UART_Loader换对话交接_2026-10-08.md)。runner/TB/模型和验收结果副本已保存build/ddr_crc_stage7_sources，archive_receipt.json核验37个跨软件/PC/仿真副本。本次未重跑仿真；后续新阶段保留已有镜像/证据，候选及新日志使用隔离目录。results.json内board_result=NOT_TESTED是当时状态，后续实板结论以board/ddr_crc_stage7_board_result.json为准。

默认--stage ddr-crc，读取tests/uart_loader/build/ddr_crc已有ELF/DAT。先核固定DDR阶段
两轮实板PASS/证据hash，再3次ROM启动→21帧/两次启动。CRC命令只读16次LW，无SW；
每笔LW退休值、readback RAM与物理DDR一致，再独立核CPU/TB/Python CRC。
用例包括未写A5内存、正常/重复CRC、物理字节26损坏后两次NACK、写修复、错误PC CRC、
同SEQ正确重试/更换预期拒绝、坏空DATA CRC、非法地址/长度/RUN、复位保留DDR后直接CRC。
兼容旧PING/RX_TEST/DDR_TEST；不含正式VERIFY、程序下载、RUN或DDR取指。

```powershell
& C:/python/python.exe sim/uart_loader/run.py --stage ddr-crc
```

产物build/ddr_crc/{residency,ddr_crc}与父目录results/validated_image；新层有crc_state.hex、
ddr_trace.csv（区分CRC_LW_RETIRE）、原始1012-byte RX/1260-byte TX及独立预期。
合计48 SW/192 LW，其中144 LW属于9次只读CRC；5个CRC ACK含重复、4个CRC失配NACK。
本候选三次ROM启动及21帧CRC联仿PASS，Errors0/Warnings0、镜像/保护/输入hash不变。
保护旧实板镜像和证据/IP/RTL，前级FAIL即停，不自动构建或部署。模型不含PHY。
后续实板两轮各100次CRC32 PASS见board/ddr_crc_stage7_board_result.json，已独立核验归档；
不能把仿真负例结果当作实板异常路径PASS。
阶段③runner/TB快照build/ddr_fixed_stage3_sources，软件/PC对应verified/ddr_fixed_stage3。

## 固定DDR写读比较与更早阶段历史

默认--stage ddr-fixed，读取tests/uart_loader/build/ddr_fixed已有ELF/DAT，核阶段②/③
两轮实板PASS证据哈希后先三次ROM启动，再两次启动/17帧。生产CPU/UART/互连/DDR桥
全部使用当前RTL，DDR为独立Pango用户口延迟/背压模型，没有PHY训练。
内存初始化A5，不预装固定向量；检查16次SW确实写入后才允许16次LW，
检查128-bit槽位/strobe、半字命令地址、CPU退休值和读回RAM实际值。
一次物理DDR字节损坏须NACK800B，同SEQ重新写入应恢复ACK；重复包不再次访问DDR。
非法地址、坏CRC、错向量、65字节和RUN均NACK且不访问DDR，复位后正常接收/比较。
任何DDR取指都FAIL。五次写读尝试合计80 SW/80 LW；17帧UART逐字节匹配独立Python基准。

```powershell
& C:/python/python.exe sim/uart_loader/run.py --stage ddr-fixed
```

产物build/ddr_fixed/{residency,ddr_fixed}，总results.json/validated_image.json在父目录；
ddr_fixed/ddr_trace.csv保存CPU请求、Pango命令与LW退休值。前一级FAIL即停，保护旧镜像/IP/RTL。
不表示实板PASS、DDR CRC、任意文件下载、RUN或Hello World完成。
阶段②runner/TB快照在build/rx_fixed_stage2_sources，软件/PC快照在各verified/rx_fixed_stage2。

## 阶段②及阶段①历史

当前默认--stage rx-fixed，读取tests/uart_loader/build/rx_fixed已有ELF/DAT，先核阶段①
两轮实板PASS凭据及哈希，再3次驻留复位→14帧固定接收测试。含4个唯一固定帧、1重复、
4正常PING及5个NACK（序号换命令/坏CRC/错误向量/65-byte超长/RUN），分两次启动。
比较实际RAM payload与原始1017-byte RX、840-byte TX及UART/FIFO/MMIO/CPU LBU路径，
核接收缓冲哨兵、计数、RAM诊断CRC和复位清零。任何DDR请求立即FAIL，不含PHY训练。
产物在build/rx_fixed/{residency,rx_fixed}/，总results/validated_image在父目录。
新候选通过只表示片内固定接收仿真PASS，不是实板、DDR写入或程序下载。

```powershell
& C:/python/python.exe sim/uart_loader/run.py --stage rx-fixed
```

--stage ping可重查原build/根阶段①镜像，输出build/ping_recheck，原证据不覆盖。
原TB/runner快照在build/ping_stage1_sources；软件和PC快照分别在对应verified/ping_stage1。
下方为阶段①历史方法，--ping-count只影响ping模式；当前模式保留同样CPU/总线/错误检查与哈希保护。

从根目录先构建一次 `tests/uart_loader/build.ps1`，再运行：

```powershell
& C:/python/python.exe sim/uart_loader/run.py --stage ping
```

runner仅读已有ELF/ROM DAT/RAM DAT，不构建或转换，先做Harvard布局、逐条ISA和镜像哈希审查。
ModelSim入口固定本机 `D:/modelsim/win64pe`；生产CPU/互连/UART/DDR桥均直接编译当前RTL。
独立同步BRAM模型从两个DAT初始化一次，复位不重装RAM；SoC UART响应延迟7拍。
DDR启用且init_done=1，但用户口没有ready/返回；任何DDR请求立即FAIL，不能用未握手隐藏错误。
不含DDR PHY、真实KEY0消抖/训练、PDS生成BRAM和实板电气。

两层按序执行，前一级失败即停：

1. `build/residency`：连续3次SoC复位，BSS每次预先毒化；逐笔检查startup清零顺序/数据/strobe，
   main入口前全BSS为0；强制RAM常量读和CRC标准向量；最终sp初始化正确，后续sp16-byte对齐且
   位于Loader栈。检查低RAM、诊断边界、栈底64byte和旧manifest保留区哨兵。无UART/DDR动作。
2. `build/ping`：默认100个独立递增PING，分两次启动各50个；第一轮另重复最近PING并分别发送
   LOAD、VERIFY、RUN，要求3个COMMAND_ERROR且不改变有效PING计数。复位重新从SEQ1开始。
   每帧36-byte请求、60-byte响应，帧内UART不插间隔，115200/8N1真实引脚激励。
   Python/zlib生成独立应答基准，比较UART RX、FIFO pop、MMIO响应、两处RX LBU退休值、TX MMIO
   接受字节与TXD独立中心采样解码。无frame/overflow/trap/IRQ/总线error、栈/常量越界或DDR请求。

允许 `--residency-only` 只执行前置层；`--ping-count N`（2..200）用于诊断，正式①标准为默认100，
不能把较少次数结果冒充100次。停止或失败不产生新的validated_image成功凭据。

通过同时要求：对应RESULT: PASS、无RESULT: FAIL、进程退出0、编译/运行Errors0、原始TX/RX
捕获逐字节等于基准、响应CRC/SEQ/命令正确。生产RTL/IP/PDS/FDC及Echo/CoreMark归档受SHA256保护；
自己的DAT在仿真前后也必须不变。

产物：每层compile/modelsim日志、独立work/run.tcl、UART原始bin；PING另有requests/responses
bin/hex、cases/decoded_responses JSON。总结果results.json记录输入/保护哈希、图像身份、结果与墙钟；
validated_image.json绑定成功同镜像。debug/保留检查器开发阶段失败记录。仿真库/波形不作为源码。

本入口通过只表示ROM驻留前置与阶段①仿真PASS，不是DDR下载、CRC读回、RUN、Hello或实板PING PASS。
