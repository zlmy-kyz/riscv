# UART Loader阶段⑧主机可注入异常两轮实板验收

日期：2026-10-08（Asia/Shanghai）。用户操作COM11和板卡，Codex离线核验与归档。阶段⑦成功位流对应ELF/DAT沿用；本轮不修改生产C/RTL/IP/PDS，不重建镜像或重新仿真。

## 结论与范围

PC工具r2两轮108/108 PASS，独立struct/zlib核对原始请求矩阵及响应全部字段/Header CRC/DATA CRC、预期状态、序号、DDR实际CRC、时序和日志额外RX检查记录；216条终端PASS逐行对应JSON名称/状态/毫秒显示，两条最终RESULT: PASS，无FAIL。

| 轮次 | 帧数 | ACK | 预期NACK | CRC ACK | 请求/响应字节 | 开始/结束SEQ |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| first_pc_r2 | 108 | 73 | 35 | 37 | 5839/6480 | 1/73 |
| after_reset_pc_r2 | 108 | 73 | 35 | 37 | 5839/6480 | 1/73 |
| 合计 | 216 | 146 | 70 | 74 | 11678/12960 | 各轮重新开始 |

35个负例涵盖坏Header/DATA CRC、非法地址/长度/版本/flags/命令/序号/状态/预期DDR CRC、截断Header/body/tail及坏Header中嵌合法包。每项错误后的合法PING和只读DDR CRC恢复均通过，CRC ACK的实际DDR CRC均0x23C3E508。范围为同一0x40000000起64字节；每轮仅seed一次固定写/读比较，不表示随机BIN、完整DDR区域或正式下载执行已验收。错误PC CRC的NACK返回真实CRC且同SEQ正确CRC重试ACK。

每轮预期NACK统计：8001×5、8002×6、8003×7、8004×4、8006×2、8007×6、8008×1、8009×3、800A×1。预期NACK是用例PASS条件。

| 真正截断负例NACK8004 | 首轮ms | after_reset轮ms |
| --- | ---: | ---: |
| magic | 207.188 | 207.400 |
| header | 208.807 | 208.766 |
| body | 211.278 | 211.781 |
| data_crc | 215.709 | 215.603 |

均满足195ms检查下限。恢复ACK首轮9.936–10.826ms，第二轮9.938–11.145ms；原第95帧truncated_magic_recover_ping不再误套截断包下限。

当前机器汇总sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json：status=STAGE8_HOST_INJECTABLE_TWO_ROUND_BOARD_PASS，board_result=PASS_HOST_INJECTABLE_ONLY。UART帧错与FIFO溢出实板仍NOT_TESTED，仅有专项真实UART仿真证据；stage8_full_board_result=NOT_COMPLETE。接收超时已验收，不代表DDR总线永久停顿有watchdog。板级CRC证据只证明固定区读回一致，非法请求无DDR写/跳转的内部事务证据来自已归档仿真。

两轮按要求提交first/after_reset日志并均接受新SEQ1；未独立观察KEY0，未采集板上已下载位流文件身份。LOAD/VERIFY/RUN仍未实现，本轮未启动⑨；后续仍使用隔离候选并明确覆盖范围。

## 固定证据

目录sim/uart_loader/board/：

| 证据 | SHA256 |
| --- | --- |
| ack_nack_stage8_first_pc_r2_result_verified.json | fc6362f0ce093cf1a8a0cbfca78628cbc8ce7ef70b3b57d9eb764de6ec1134c8 |
| ack_nack_stage8_after_reset_pc_r2_result_verified.json | 2fba8cc8e2174c9e5c2029251a1823cac695762f54afb96fbb45e635a0368d10 |
| ack_nack_stage8_pc_r2_board_result_console_verified.txt | 06dc60e250c736c1cc0af88b47690f032360a4bf50c0fafa1be3bd6833bc8811 |

单轮核验结果为同名去掉_verified的_result.json。综合汇总保留每轮来源/hash、输入工具hash、超时测量、计数、复位/位流证据边界和来源凭据；其_sources目录保留离线核验/归档脚本快照。

原ack_nack_stage8_first.json及首轮误报归档、旧ack_nack_stage8_board_result.json的INCOMPLETE_RETEST_REQUIRED_PC_TIMING_FIX全部保留，不改写为PASS。历史仿真结果也保持原字节；当前结论使用新的r2板级汇总。

## 镜像与输入保护

ELF/ROM/RAM三份成功文件在原build/ddr_crc、verified/ddr_crc_stage7/build及candidates/ack_nack_stage8/build逐份核对，均与日志身份一致：

- ELF：49744ef735f2c14461594969004641f318f62991589aadf2209f9e15cf6de178。
- ROM DAT：21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a。
- RAM DAT：59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a。

主IP两IDF的INIT_FILE仍指向tests/uart_loader/build/ddr_crc对应DAT。阶段⑦37项source/archive、阶段⑧27项source/candidate、PC原/r2的11项source/archive哈希均匹配；完整仿真成功结果的221项保护文件和25项输入文件匹配。成功仿真results.json SHA256仍b8ec6becb8817ec37302081abda0b84c8a225ae072037c9056c086e432e959db。

本轮新增离线archive_board_r2.py，核对终端216行、两轮身份/SEQ/计数及既有输入凭据后独占创建汇总和终端副本；没有串口调用。只更新文档/README当前入口，不改成功快照。

## 离线复现

从D:/riscv/RISCV运行以下命令，--output必须使用未存在的新名字，避免覆盖证据；原始COM11日志不再重跑。

```powershell
& C:/python/python.exe sim/uart_loader/stage8/check_board_r2.py sim/uart_loader/board/ack_nack_stage8_first_pc_r2_result_verified.json --output sim/uart_loader/board/ack_nack_stage8_first_pc_r2_recheck.json
& C:/python/python.exe sim/uart_loader/stage8/check_board_r2.py sim/uart_loader/board/ack_nack_stage8_after_reset_pc_r2_result_verified.json --output sim/uart_loader/board/ack_nack_stage8_after_reset_pc_r2_recheck.json
& C:/python/python.exe sim/uart_loader/stage8/archive_board_r2.py --console sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result_console_verified.txt --output sim/uart_loader/board/ack_nack_stage8_pc_r2_board_recheck.json
```

实测三个核验步骤退出0，全部PASS。综合归档脚本首次调试曾因终端变量赋值被选入命令行、相对输出路径不能求工程相对名而停止；均发生在写汇总/证据之前，修正后完整核验通过，不影响用户串口日志或板级结果。
