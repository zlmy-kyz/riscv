# UART Loader VERIFY / RUN / DDR / Hello 实板验收

> GitHub 发布说明（2026-10-10）：下文标为“仅本地”的历史档案/参考材料保留在开发机，未随本次源码发布；原验收结论和哈希不变。当前开发入口见 doc/CODEX_HANDOFF.md。

日期：2026-10-09。用户完成隔离候选下载与 COM11 验收，Codex 直接读取工程内原始日志并独立核验，精简计划第②关完成：`PASS_VERIFY_RUN_DDR_HELLO`。现在已具备从 PC 经 UART 下载程序到 DDR3、正式校验并运行的已验收基本链路。

## 实测结果

| 项目 | 结果 |
| --- | --- |
| 原始来源 | ACTUAL_SERIAL，COM11，115200 8N1 |
| 全矩阵 | 157/157，83 ACK、49 LOAD READY、25 预期 NACK |
| 正式 VERIFY | 4 次 ACK，367-byte 文件实际 DDR CRC32 均 `5E142E06`，授予 VERIFIED |
| 最终 RUN | SEQ106，唯一成功 RUN，367-byte 实际 DDR CRC32 `5E142E06` |
| 应用输出 | 精确 13-byte `Hello World\r\n`，十六进制 `48656c6c6f20576f726c640d0a` |
| 总用时 | 4.301259 秒 |
| 收发 | 请求12952字节，协议响应9420字节，应用13字节 |
| 错误统计 | 响应CRC错误0、额外RX字节0、重试0；25个预期NACK均匹配 |

独立核验请求矩阵、全部60-byte响应字段与两处CRC、READY/DATA顺序、镜像状态、错误后重新下载恢复、唯一RUN和精确Hello。另将日志中的 ELF/DAT/BIN/CRC/门控/位流哈希与当前冻结输入、PDS审计和固定副本逐项核对，全部一致。内部DDR指令退休、ACK发送完成时的跳转约束、gp/sp/BSS写入顺序已有集中仿真证据；实板没有采集退休轨迹，实际成功执行由Hello应用自身data/BSS检查及严格UART结果确认。

## 证据和成功镜像

- 原始日志：verify_run_hello_first.json（仅本地：`../../sim/uart_loader/board/verify_run_hello_first.json`），SHA256 `91d799481c325df34c738bb8bb7ba7f61fc514c393ef883a631c6925abcdcd84`。
- 独立汇总：verify_run_hello_board_result.json（仅本地：`../../sim/uart_loader/board/verify_run_hello_board_result.json`），`COMBINED_ACTUAL_BOARD_VERIFIED`。
- 固定原始副本：verify_run_hello_board_result_raw_verified.json（仅本地：`../../sim/uart_loader/board/verify_run_hello_board_result_raw_verified.json`），与原始日志同哈希。
- 成功归档收据：verify_run_hello_submission_result.json（仅本地：`../../sim/uart_loader/board/verify_run_hello_submission_result.json`），`COMBINED_ACTUAL_BOARD_ARCHIVE_PASS`。
- 完整成功快照：`sim/uart_loader/board/verify_run_hello_success/`，170文件，包括76项输入、71项仿真/离线证据、18项PDS/IP/网表/时序/位流，以及门控、实板日志和汇总；逐文件哈希见收据。

Loader ELF SHA256 `ac8127d7e67702d31d2e6bf10c171de1dc631c3d7307fb3387b5e8fb4ff40c6a`；ROM DAT `53a2d9912e85b6b5c90768fb0422be6cde8d5bdab37ef07b7eabfb065b76cea1`；RAM DAT `986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975`。应用 BIN SHA256 `a9209268576a07fb8cb4cc55920cb20494682aefd6a22f620d3000f9338ab79d`，367字节。候选与快照不得重建或修改；下一开发在独立应用/工具目录进行，同一成功Loader位流继续使用。

实板工具记录用户选用的位流路径 `D:/riscv/RISCV/sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit`，SHA256 `31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0`，与已审计、归档的候选位流一致。用户报告下载成功，协议与新固件相符；Codex未独立观察JTAG下载、KEY0或读取板上配置，因此不宣称独立读回确认整个FPGA配置。初次JTAG扫描未发现FPGA属于准备阶段历史，当前不再阻碍本轮实板完成。

## 覆盖边界和保护核对

本轮157响应保留非法地址/对齐/长度/版本/命令/SEQ/身份、未END/未VERIFY、控制CRC/整镜像CRC、重复控制、新BEGIN撤销VERIFIED和恢复检查。两项仿真物理DDR损坏用例在实板明确替换为身份拒绝，本轮没有物理损坏注入；没有重复实际BREAK/FIFO洪泛或控制截断超时验收。相关集中仿真及阶段⑧实际UART异常证据保留各自范围。

新冻结输入76项、证据71项、源副本76项均匹配；阶段⑩79项输入、110项证据和79项源副本均匹配；阶段⑦37项原始/归档及⑧/⑨/⑩各10项成功配置快照匹配。主PDS/IP/位流的阶段⑩10项当前文件与旧归档一致。本轮只离线核验、复制归档、更新文档，未打开COM11或下载/修改RTL、重建DAT/BIN。

原 `COMBINED_SIM_PASS` 门控及PDS构建收据内 NOT_TESTED 保留其生成时状态；当前板级结论看新独立汇总和归档收据。历史FAIL日志均保留，不改写为PASS。

## 复现和后续

独立核验入口为 `sim/uart_loader/verify_run_hello/check_board.py`；重新核验时用新的output路径，保护已有成功汇总及固定副本。所有上板、复位、供电和串口操作由用户负责，Codex开发、仿真、提供步骤和离线核验。

第①关与第②关均已完成。下一关为第③关：保持本次成功Loader位流不变，至少10轮复位下载/校验/运行、第二份不同BIN，随后CoreMark短迭代算法CRC和正式运行。第③关本轮尚未开发或测试，不要求重复本关构建与两轮上板。程序大小仍限低60KiB下载窗口，栈保留在DDR窗口上方4KiB。

开发、集中仿真、位流构建详情见[合并验收记录](UART_Loader_VERIFY_RUN_DDR_Hello合并验收_2026-10-09.md)。
