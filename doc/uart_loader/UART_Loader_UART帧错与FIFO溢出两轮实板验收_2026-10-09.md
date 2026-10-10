# UART Loader阶段⑧UART帧错与FIFO溢出两轮实板验收

日期：2026-10-09（Asia/Shanghai）。结论：隔离诊断候选 `uart_fault_stage8_diag` 的阶段⑧完整约定矩阵，两轮实板均PASS。用户操作COM11、上板与复位；Codex仅离线核验和归档，没有打开串口、修改RTL/C/PC工具或重建DAT。

## 验收目的与结果

阶段⑧原主机可注入异常已两轮PASS，剩余真实UART帧错和FIFO溢出没有板级原因证据。本候选只增加清错前真实STATUS[4:5]快照，在8005响应capabilities高位中上报0x10/0x20；不修改底层UART/FIFO和错误恢复算法。候选开发、仿真、DAT身份、注入方式和首次部署命令见[注入准备记录](UART_Loader_UART帧错与FIFO溢出实板注入准备_2026-10-09.md)。

用户提交两轮终端输出，以及工程内 `uart_fault_stage8_diag_first.json`、`uart_fault_stage8_diag_after_reset.json`。独立核验器逐帧使用struct/zlib检查原始请求、60字节响应、Header/DATA CRC、所有响应字段、序号、工具身份、候选ELF/DAT、部署门控、实际时序、额外RX检查和故障原因。另将234条终端PASS输出逐条与日志比对，编号、名称、ACK/NACK、原因位和三位小数耗时均一致，无FAIL/Traceback，两份原始日志哈希不同。

| 项目 | 首轮 | 第二轮 |
| --- | --- | --- |
| 完整矩阵 | 117/117 PASS | 117/117 PASS |
| ACK / 预期NACK | 80 / 37 | 80 / 37 |
| DDR CRC ACK | 40，实际CRC均23C3E508 | 40，实际CRC均23C3E508 |
| 成功SEQ范围 | 1–80 | 1–80 |
| BREAK API及实际持有 | Set/Clear均成功，20.906ms | Set/Clear均成功，20.938ms |
| 帧错响应 | NACK8005，真实原因0x10 | NACK8005，真实原因0x10 |
| 从BREAK发起至帧错响应 | 107.497ms | 107.565ms |
| 洪泛触发PING | ACK PASS | ACK PASS |
| FIFO溢出响应 | NACK8005，真实原因0x20 | NACK8005，真实原因0x20 |
| 从洪泛发起至溢出响应 | 119.312ms | 118.884ms |
| 两类故障后的PING/DDR CRC | 全部PASS | 全部PASS |

合计234响应：160 ACK、74个预期NACK，其中80个实际DDR CRC ACK。每轮包含原108项主机矩阵及9项线级故障/恢复响应。实板没有记录FIFO峰值、溢出事件次数或丢弃字节数；仿真的43次溢出/43字节丢弃不能算作实板测量。

## 镜像与部署身份

| 候选文件 | SHA256 |
| --- | --- |
| loader.elf | b70f19595329b11d3e6c09c3b1021699ff24f5e068cac0d7b700aff2d164aa86 |
| loader_rom.dat | 391eb696d4cca6803e2469ec5d02a156b38e9fb9849c3cd4754b62853d8533a3 |
| loader_ram.dat | 59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a |

日志绑定的同一对DAT及PC输入均与部署门控一致。66项仿真输入、58项仿真证据的哈希全部仍匹配；阶段⑦37个原始/归档文件均未变。开发阶段冻结的源码/ELF/DAT位于 `sim/uart_loader/build/uart_fault_stage8_diag/validated_sources/`，旧成功镜像及阶段⑧r2和原FAIL证据继续保留，不覆盖历史报告内NOT_TESTED状态。

当前两块主IP的IDF已经由用户指向：

- `tests/uart_loader/candidates/uart_fault_stage8_diag/build/loader_rom.dat`
- `tests/uart_loader/candidates/uart_fault_stage8_diag/build/loader_ram.dat`

本轮另保存当前PDS、两个IP的IDF/生成Verilog/TB/初始化参数，以及工作区 `generate_bitstream/board_top.sbit`，共10个文件，位于 `sim/uart_loader/board/uart_fault_stage8_diag_deployed_workspace/`；逐文件哈希在submission_result中。当前工作区sbit哈希是 `baee4c72ceb93449c3f6cfd4a8c48b7c3f3575146cdb1e5671ee9b85c6adeaf8`。这是当前磁盘产物快照，日志没有绑定下载位流文件，不能据此独立证明板上运行的位流文件身份。原部署前15个文件快照仍在 `sim/uart_loader/build/uart_fault_stage8_diag/retained_before_deploy/`。

## 固定证据与复现

板级汇总：`sim/uart_loader/board/uart_fault_stage8_diag_board_result.json`，状态 `STAGE8_DIAGNOSTIC_TWO_ROUND_BOARD_PASS`，`stage8_full_board_diagnostic_candidate=PASS`、`board_result=PASS_DIAGNOSTIC_CANDIDATE_ONLY`。

| 固定原始证据（均在sim/uart_loader/board） | SHA256 |
| --- | --- |
| uart_fault_stage8_diag_board_result_first_verified.json | da44da5afc7c07b1af430ccdf4440e1fa06857afc127de9fb7ab2e7e99996ce7 |
| uart_fault_stage8_diag_board_result_after_reset_verified.json | 6ac52af5f3644f96673ec01aef021db6df160449a16fad51fb5ade537d4d5bb8 |
| uart_fault_stage8_diag_console_verified.txt | 2d1b1719947af33d0f1450a9375026a42c73a570df9bac8358c37496164349d0 |

终端对照、37项旧基线核验、66项输入/58项仿真证据核验、现行IDF路径及10个部署工作区副本哈希见 `uart_fault_stage8_diag_submission_result.json`。归档脚本 `sim/uart_loader/build/check_uart_fault_stage8_submission_2026-10-09.py` 不操作串口且拒绝覆盖现有档案，已执行一次。

可用下列只读命令复验已固定的两轮证据，不重新打开串口，也不创建新文件：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe -c "import sys;from pathlib import Path;sys.path.insert(0,'sim/uart_loader/stage8_uart_fault');from check_board import verify;print(verify(Path('sim/uart_loader/board/uart_fault_stage8_diag_board_result_first_verified.json')));print(verify(Path('sim/uart_loader/board/uart_fault_stage8_diag_board_result_after_reset_verified.json')))"
```

实际汇总归档命令如下，已执行且输出文件存在，不应重复覆盖：

```powershell
& C:/python/python.exe sim/uart_loader/stage8_uart_fault/finalize_board.py --first sim/uart_loader/board/uart_fault_stage8_diag_first.json --after-reset sim/uart_loader/board/uart_fault_stage8_diag_after_reset.json --output sim/uart_loader/board/uart_fault_stage8_diag_board_result.json
```

## 覆盖边界与下一步

阶段⑧约定的ACK/NACK、UART接收超时、两种sticky错误和错误后恢复实板矩阵已补齐，PASS绑定本诊断候选。原阶段⑦二进制仍保留其阶段⑦及原r2主机异常验收范围，不能把本候选的原因诊断结果改写成原二进制已通过同一专项。两轮重新从SEQ1成功，结合用户按要求提交after_reset轮，作为复位后再验依据；Codex没有独立观察KEY0按钮。

DDR范围仍仅 `0x40000000–0x4000003F` 固定64字节。尚无任意BIN、正式LOAD/VERIFY/RUN或UART下载后DDR取指；DDR永久总线停顿也没有桥watchdog。本轮只核验和归档，没有开始阶段⑨。下一开发步骤是阶段⑨隔离随机二进制收发、DDR写入及实际读回CRC压力验收；下载执行仍须后续单独实现和验证。用户继续负责所有上板及串口操作。
