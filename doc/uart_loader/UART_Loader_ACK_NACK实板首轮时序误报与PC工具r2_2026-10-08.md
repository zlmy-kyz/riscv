# UART Loader阶段⑧实板首轮时序误报与PC工具r2

日期：2026-10-08（Asia/Shanghai）。用户负责实板，Codex仅离线分析、修改PC检查与提供复测命令。本轮不打开COM11，不改C/RTL/IP或成功DAT，不重跑硬件仿真，因为修改只涉及PC计时分类。

## 最新结果：阶段⑧主机可注入异常两轮实板PASS（2026-10-08）

用户用PC工具r2在COM11提交首轮与after_reset轮；独立struct/zlib逐帧核验两份原始日志、请求矩阵、响应全部字段/CRC、时序、额外RX检查记录与终端输出，每轮108/108 PASS：73ACK、35个预期NACK、37个DDR CRC ACK。合计216帧、146ACK、70个预期NACK、74个CRC ACK，实际DDR CRC均23C3E508；错误后的合法PING/CRC恢复全部通过。两轮均接受新SEQ1并完成至SEQ73；未独立观察KEY0，未采集板上位流文件身份。

现行板级汇总为sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json，board_result=PASS_HOST_INJECTABLE_ONLY；UART帧错/FIFO溢出实板仍NOT_TESTED，阶段⑧完整实板范围NOT_COMPLETE。旧ack_nack_stage8_board_result.json及原首轮误报FAIL保留为历史证据，不覆盖；旧仿真报告内NOT_TESTED也保留生成时状态。详见[两轮验收记录](UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。

成功ELF/ROM/RAM、阶段⑦37项快照、阶段⑧27项候选、PC原/r2的11项输入档案及全矩阵221项保护文件/25项仿真输入哈希均匹配。未重建DAT、修改C/RTL/IP/PDS或重新仿真；Codex仅离线核验/归档，所有上板操作继续由用户负责。本轮未启动⑨随机BIN或正式LOAD/VERIFY/RUN；后续须保留上述实板覆盖边界并使用隔离候选。

## 历史首轮实测和原因

首轮在94/108 PASS后停止，第95条truncated_magic_recover_ping实际为合法SEQ64 ACK：10.289ms、60-byte Header/DATA CRC和所有字段正确。第94条truncated_magic NACK8004为207.309ms，符合接收100ms加恢复100ms。误报是acceptance.py用名称前缀truncated_选择所有用例，包括恢复PING/CRC，错误要求正常ACK>=195ms。check_board.py独立核验器也有同样前缀判断。旧离线fixture按同样前缀给恢复ACK人为201ms延迟，未暴露误判。

独立struct/zlib核对实际95个请求与原矩阵、全部响应字段/CRC及94条终端PASS行时间匹配；95条原始响应为64个ACK/31个预期NACK，但第95条未执行额外RX检查，不能升级成95个完整验收PASS。记录94个原工具PASS、首轮未完成，第二轮未提交。

## 保留证据

- 原live日志ack_nack_stage8_first.json不变，status仍FAIL。
- 固定副本sim/uart_loader/board/ack_nack_stage8_first_pc_timing_failure_archived.json；终端副本ack_nack_stage8_first_pc_timing_failure_console.txt。
- board门控ack_nack_stage8_board_result.json：INCOMPLETE_RETEST_REQUIRED_PC_TIMING_FIX，未标PASS。
- 分析、12项时序回归、8项通用PC检查与原/r2输入档案：sim/uart_loader/build/ack_nack_stage8_pc_r2/。
- 修正版tools/uart_loader/candidates/ack_nack_stage8_r2/；cases/protocol与旧版逐字节相同，仍读取相同已验收ELF/DAT。

## 修改和回归

acceptance.py只对negative且预期status==8004的真正超时负例检查>=195ms。恢复PING/CRC仍严格检查原始响应全部字段/SEQ/CRC，正常快速ACK可通过；不改变5s等待上限和失败即停。check_board_r2.py做同样最小修正，旧工具与旧独立检查器保留。

12项专项回归包括旧95帧错误复现、修正版108帧且恢复ACK约9ms/最多7-byte短读取PASS、4类早到超时NACK仍拒绝，以及独立核验器快速ACK接受/早NACK拒绝。8项通用PC回归再PASS；--plan-only生成108帧/35负例计划且未打开串口。成功镜像/原保护文件/原仿真输入哈希最终核对不变。

```powershell
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/stage8/check_pc_timing_r2.py
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/stage8/check_pc_tool_r2.py
```

离线fixture不是实板证据，不能把修正后的离线108帧PASS写成用户完成实板108帧。

## 用户复测

不用重新编译DAT或下载新位流。沿用当前阶段⑦成功位流，关闭串口助手；每轮KEY0复位并等DDR初始化。旧首轮已经推进到SEQ64，不能直接从SEQ1重发而不复位。使用全新日志名，原失败日志保留。

```powershell
$stage8Tool = 'D:/riscv/RISCV/tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py'
$stage8Logs = 'D:/riscv/RISCV/sim/uart_loader/board'
# KEY0复位，等待DDR初始化后：
& C:/python/python.exe $stage8Tool --port COM11 --log "$stage8Logs/ack_nack_stage8_first_pc_r2.json"
# 再KEY0复位，等待DDR初始化后：
& C:/python/python.exe $stage8Tool --port COM11 --log "$stage8Logs/ack_nack_stage8_after_reset_pc_r2.json"
```

每轮108/108 PASS，73ACK/35个预期NACK/37个CRC ACK，出现其他FAIL即停止并保留日志。收到实际两轮后用check_board_r2.py逐帧核验与归档；原check_board.py会误判快速恢复，不能用于r2门控。

## 未覆盖

本轮仅收到首轮前95个原始响应，尚未完成后续截断Header/body/CRC和嵌入报文组及完整两轮实板。UART帧错/溢出仍仅仿真，实板未测试。仍不推进随机BIN、正式LOAD/VERIFY/RUN或DDR执行。
