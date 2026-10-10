# UART Loader 真实程序 LOAD 两轮实板验收

日期：2026-10-09。用户完成阶段⑩上板并报告成功；Codex读取工程内首轮与after_reset原始JSON，逐帧独立离线核验，两轮通过。未打开COM11、重建DAT/BIN、生成或下载位流。

## 结果与范围

板级汇总为 `STAGE10_TWO_ROUND_BOARD_PASS / PASS_LOAD_ONLY_UNVERIFIED`，精简计划第①关完成。每轮8响应：3个PING、2个READY、2个LOAD最终ACK、1个诊断DDR CRC ACK；两輪合计16响应，CRC/UART错误及自动重试均为0。

383-byte真实program.bin以256+127字节下载，含非空data/bss布局，DDR读回CRC32均为`B2E24920`，与实际文件一致；两轮重复覆盖同一383-byte程序区，不能算766个不同地址。最终状态仅`LOADED_UNVERIFIED`，无Hello或额外串口输出，正式VERIFY、RUN及应用执行尚未实现。本次通过证明真实程序下载和读回，不授予VERIFIED。

| 轮次 | 响应 | 用时 | UART TX / RX字节 | 原始日志SHA256 |
| --- | --- | --- | --- | --- |
| first | 8 | 0.396331 s | 599 / 480 | `2841ea792ee09b8130d2069bdf015c45e13ac1b31ce2a15237888a103e1e9144` |
| after_reset | 8 | 0.387259 s | 599 / 480 | `41c4b91cc7d1e8837bf4c0f5e08314f662a9dc62e12ee8dc21c186c38e4f2c69` |

## 独立核验与复现

核验响应60-byte全部字段及两个CRC、SEQ、READY/ACK顺序、真实DDR CRC、应用BIN/manifest身份、Loader ELF/DAT身份、PC工具与部署门控哈希、两轮日志互不相同、无错误/重试/额外RX。响应不带VERIFIED或RUN能力位。没有用离线fixture替代实板证据。

以下命令只读原始日志并新增输出，不操作串口；输出已存在时停止，复核需使用新的输出路径，不覆盖成功档案。

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe sim/uart_loader/stage10/check_board.py --first sim/uart_loader/board/load_stage10_first.json --after-reset sim/uart_loader/board/load_stage10_after_reset.json --output sim/uart_loader/board/load_stage10_board_result.json
& C:/python/python.exe sim/uart_loader/build/archive_stage10_board_2026-10-09.py
```

- 原始副本：`sim/uart_loader/board/load_stage10_board_result_first_verified.json`、`load_stage10_board_result_after_reset_verified.json`。
- 板级汇总：`sim/uart_loader/board/load_stage10_board_result.json`。
- 归档收据：`sim/uart_loader/board/load_stage10_submission_result.json`，状态`STAGE10_ACTUAL_BOARD_ARCHIVE_PASS`。
- 当前PDS、两IP的IDF/生成RTL/初始化参数、sbit共10文件已复制至`sim/uart_loader/board/load_stage10_deployed_workspace/`；逐文件SHA256见收据。该工作区位流副本不是独立观测的板上位流身份。
- 79项冻结输入、110项仿真证据、79项源副本全部相同；阶段⑦37项原始/副本、阶段⑧及⑨各10项部署档案相同。439项先前保护文件中417项相同，22项PDS/IP/位流产物变化属于用户部署工作区；未覆盖旧档案或修改历史门控。

主IP INIT_FILE为`tests/uart_loader/candidates/load_stage10/build/loader_rom.dat`及同目录`loader_ram.dat`。冻结成功输入与构建副本保留在`sim/uart_loader/build/load_stage10/validated_sources/`，后续开发使用新隔离候选，不能修改或重建本次成功镜像。

| 成功镜像 | SHA256 |
| --- | --- |
| `loader.elf` | `83954b42e85e6c4475b989e546bc1eee3dd9e9731e33742bcfa315067278b36b` |
| `loader_rom.dat` | `bf91790345b66cf29246b42d909f1c32e8bd978a712ab756c20ae18eaa5609ae` |
| `loader_ram.dat` | `986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975` |
| `program.bin` | `ccc434866bcf384488e53d972f0fcb4cd6be9a977ce0e4d26c8bb349c3c3dc69` |

归档首尝试遇到旧PDS自动备份日志`generate_bitstream/logbackup/run_2026-10-06-23-34-15.log`已不存在，尚未生成成功收据；调整归档脚本为显式记录缺失后重跑通过。初次错误记录保留于`sim/uart_loader/build/load_stage10/archive_first_attempt_2026-10-09.txt`，收据的`deployment_files_missing_since_gate`保留该差异，未删除文件。

## 下一步

按[三个关口计划](UART_Loader剩余阶段精简计划_2026-10-09.md)进入第②关：在新隔离候选合并开发正式VERIFY、RUN、真实UART下载后的DDR指令退休与Hello。先仿真及离线工具验收，再由用户上板。保留全镜像DDR CRC、RUN前重验、非法请求不跳转、ACK发完才跳转、应用gp/sp及data/bss检查，不再拆成四次用户阶段。

KEY0按钮及实际下载的位流身份未独立观察；after_reset轮从SEQ1开始且初始状态清空通过。UART帧错/FIFO溢出等专项证据仍看各阶段独立验收；本次正常两轮不扩大这些覆盖，也未覆盖完整512MiB、永久DDR事务停顿或应用执行。
