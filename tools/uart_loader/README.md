# RVLD PC工具：DDR读回CRC32

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

换对话入口见 [阶段⑦交接](../../doc/uart_loader/UART_Loader换对话交接_2026-10-08.md)。当前PC工具/协议/依赖快照保存在verified/ddr_crc_stage7，阶段⑧主机可注入部分现已两轮实板验收。当前实板COM11、115200；C:/python/python.exe已安装pyserial3.5。复测另用新日志名，保留board下成功verified档案。

新增ddr-crc-test。每次先DDR_TEST写/读/比较固定64字节，成功后发只读DDR_CRC_TEST，
PC CRC=实际DDR CRC=23C3E508才CRC32 PASS。--count100包含200个停等请求/响应：
100次写比较和100次CRC。日志含operation/test_number/pc_crc/actual_ddr_crc及原始报文。
校验请求36字节：CMD0x12，LENGTH64描述DDR范围、IMAGE_CRC为PC CRC、DATA空；不回传完整数据。
旧DDR_TEST返回DDRCRC0保持兼容，LOAD/VERIFY3/RUN4仍未实现。

需要先将tests/uart_loader/build/ddr_crc下ROM/RAM两DAT同时部署。旧位流会拒绝CMD0x12。
关闭串口助手，KEY0复位并等待DDR初始化，每轮新命令从SEQ1开始：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_crc100.json ddr-crc-test
# 必须再KEY0复位、等待初始化；否则可能返回SEQ_ERROR8009：
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_crc100_after_reset.json ddr-crc-test
```

每轮100条DDR_CRC_TEST n: ACK ... CRC32 PASS，退出0；NACK/超时/包CRC/字段或ACK的DDR CRC不符即FAIL。
CRC_ERROR8001的NACK保存实际DDR CRC，输出PC/DDR CRC。仿真与实板状态以CODEX_HANDOFF为准。

2026-10-08实板两轮各100次CRC32 PASS已独立核验：共400ACK，PC/实际DDR CRC一致，
证据sim/uart_loader/board/ddr_crc_stage7_board_result.json。仅覆盖同一固定64-byte正常路径。
下一步是ACK/NACK异常路径专项验收，尚不能任意BIN下载或RUN。

## 固定DDR写读比较历史

新增ddr-test：仅发送预定64字节，CPU写0x40000000后读回比较，匹配才返回ACK64；
不发送任意program.bin，不执行程序，不计算DDR CRC（该阶段待后续）。
必须先将tests/uart_loader/build/ddr_fixed下的ROM/RAM两份DAT同时生成IP并部署位流；
旧阶段②位流会拒绝此命令。关闭串口助手，KEY0复位、等待DDR初始化后运行：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_fixed100.json ddr-test
# 再KEY0复位、等待初始化，另存第二轮：
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_fixed100_after_reset.json ddr-test
```

PASS：每轮100条DDR_TEST N: ACK; 64 bytes written/read/matched at 0x40000000，退出0。
FAIL：任一NACK（DDR_ERROR=0x800B）、超时、CRC/SEQ/响应字段异常。JSON保留原始请求/应答。
软件成功只覆盖该64字节固定模式；实板DDR诊断状态以CODEX_HANDOFF为准。

## 阶段②与阶段①历史

新增rx-test：固定发送64-byte向量，CRC=23C3E508；CPU存入片内RAM并逐字节比较，
正确才返回ACK64。没有DDR下载或RUN。仅适用于阶段②build/rx_fixed的ROM/RAM同时部署后。
pyserial3.5已由用户安装，COM11已确认CH340。关闭串口助手，每条独立命令前KEY0复位并等待初始化。

```powershell
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/rx_fixed100.json rx-test
# 再复位并等待初始化，另存第二轮：
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/rx_fixed100_after_reset.json rx-test
```

预期100条RX_TEST N: ACK; 64 bytes matched in RAM，退出0；JSON含原始tx/rx hex。
NACK/超时/CRC/SEQ不符即停止并非零退出，不自动重试。新位流PING也需复位后独立回归。
两轮固定接收均实板PASS后才推进DDR写入/读回；当前仿真进度以CODEX_HANDOFF为准。

以下为阶段①工具的历史说明；PING格式与命令继续兼容，原日志和镜像保留原样。

只提供PING；没有LOAD/VERIFY/RUN命令。protocol.py使用Python标准库CRC32编码36-byte PING，
严格检查60-byte应答的Header/Payload CRC、SEQ、命令、基址和PING-only能力。
协议编解码已用于 `sim/uart_loader/run.py` 与真实CPU C程序互操作。

当前 `C:/python/python.exe` 未安装pyserial，实板调用前需安装requirements；本阶段未安装依赖、
未打开任何串口，也未部署Loader位流。当前Echo或CoreMark位流不会响应这个协议。

```powershell
# 实板Loader部署并确认端口后执行，不要照搬COM编号。
& C:/python/python.exe -m pip install -r tools/uart_loader/requirements.txt
& C:/python/python.exe tools/uart_loader/loader.py --port COMx --count 100 --log sim/uart_loader/board/ping.json ping
```

CLI固定115200/8N1/无流控，停等，响应5秒超时，无自动重试或RUN。
每个新CLI从SEQ1开始，需先复位Loader，避免复用旧会话序号；重试场景和自动会话续接留后续实现。
输出ACK/SEQ、ROM驻留候选阶段、地址/容量/块长与往返时长。容量字段不是下载能力声明。
