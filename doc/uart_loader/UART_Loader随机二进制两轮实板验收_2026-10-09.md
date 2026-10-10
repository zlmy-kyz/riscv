# UART Loader阶段⑨随机二进制两轮实板验收

日期：2026-10-09（Asia/Shanghai）。用户报告成功，工程中已有首轮及after_reset两份完整JSON；无需粘贴每轮1000条进度输出。Codex只读取日志、离线核验、保存新增档案和更新交接，未打开COM11或修改C/RTL/工具、重建DAT、生成/下载位流。

## 实测结论

阶段⑨完整约定随机/边界数据诊断压力验收通过，身份绑定隔离 `random_stage9`。每轮1000镜像达到原方案“1000镜像或累计16MiB”的1000镜像条件；不声称达到16MiB。seed=0x20261009，14边界长度（含61440）、100组全窗口随机长度、886组小随机长度，包含00/FF/MAGIC/CRLF。

| 指标 | 首轮 | after_reset轮 |
| --- | ---: | ---: |
| 完整镜像数 | 1000 | 1000 |
| ACK响应数/SEQ范围 | 17946 / 1–17946 | 17946 / 1–17946 |
| 整镜像实际DDR CRC ACK | 1000 | 1000 |
| 尾部3-byte哨兵CRC ACK | 999 | 999 |
| 有效文件payload字节 | 3700127 | 3700127 |
| 额外哨兵写入字节 | 2997 | 2997 |
| UART请求/响应字节 | 4349180 / 1076760 | 4349180 / 1076760 |
| CRC错误/UART错误/重试 | 0 / 0 / 0 | 0 / 0 / 0 |
| 总耗时（秒） | 549.845 | 550.179 |
| 有效payload速率（B/s） | 6729.41 | 6725.32 |

两轮合计2000镜像、35892响应、7400254有效文件字节。每个文件在同一低60KiB窗口重复写入，不能解释为覆盖了7400254个不同DDR地址或整个512MiB DDR。所有代码仍从ROM取指；CMD13分块诊断写后真实DDR读回CRC，CMD14整文件实际DDR范围CRC均与PC oracle一致。正式LOAD2/VERIFY3/RUN4没有实现，不执行随机数据或Hello。

## 原始证据与独立核验

两轮live日志 `sim/uart_loader/board/random_stage9_first.json`、`random_stage9_after_reset.json`；固定副本 `random_stage9_board_result_first_verified.json` 和 `random_stage9_board_result_after_reset_verified.json`，副本与原始字节完全一致：

- 首轮SHA256：`29f428e4fe052788f913f15f4030549c40154b6b3f3c655e5c2dbf01d76ce7ed`。
- after_reset SHA256：`2b8f78fd41cf43dab52f99db994c9ccdfb6b5f2850c4584743a65664b1f49334`。
- 板级汇总 `sim/uart_loader/board/random_stage9_board_result.json`：STAGE9_TWO_ROUND_DIAGNOSTIC_BOARD_PASS / PASS_RANDOM_DIAGNOSTIC_ONLY。
- 归档收据 `sim/uart_loader/board/random_stage9_submission_result.json`：STAGE9_ACTUAL_BOARD_ARCHIVE_PASS。

独立struct/zlib核验所有请求与固定BIN生成的规范帧逐字节一致；Header、DATA与响应CRC、完整响应字段、SEQ、状态、实际DDR CRC、完整1000个image_end、时序、额外RX为空、完整写入计数、0重试/0错误均符合要求。候选ELF/DAT、PC工具、corpus与部署门控身份全部相同；fixture/plan不能算板级证据。本轮未采集终端文本，结论来自两份完整原始JSON。

复现（均只离线读取；已有归档拒绝覆盖，重新核验须使用新output名称）：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe sim/uart_loader/stage9/finalize_board.py --first sim/uart_loader/board/random_stage9_first.json --after-reset sim/uart_loader/board/random_stage9_after_reset.json --output sim/uart_loader/board/random_stage9_board_result.json
& C:/python/python.exe sim/uart_loader/build/archive_stage9_board_2026-10-09.py
```

## 成功镜像与配置保存

| 文件 | SHA256 |
| --- | --- |
| loader.elf | de08ec6f89132ff469dfd3369e8b5f6d389d0608074534c0f63e82596b008061 |
| loader_rom.dat | d5c887dec64d167d7f1532db126df31f1b5d0cf4b051a56d175d19fd56d002d6 |
| loader_ram.dat | 986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975 |
| 当前磁盘board_top.sbit副本 | 07172fb480379d910ad3feee66362abbede81eae38bcf1d3e945288b261a8438 |

当前两IP的实际IDF INIT_FILE均核对为 `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat`、`loader_ram.dat`。`sim/uart_loader/board/random_stage9_deployed_workspace/`保存PDS、两IP的IDF/RTL/TB/初始化参数及当前sbit，共10文件；逐项路径、字节数、哈希在归档收据。当前sbit为磁盘配置档案，日志没有绑定实际下载位流文件，不能把副本哈希写成独立确认板上位流身份。

1186项冻结源码/输入及1186项副本、103项仿真证据均未变；阶段⑦37项原始/副本、阶段⑧已成功10文件配置档案均未变。部署前保护清单286项中277项未变，9项变化全部是用户本次PDS/ROM/RAM生成文件/当前位流，具体列表见收据；旧成功配置完整保留。历史仿真部署门控NOT_TESTED不改写，最新板级结论独立记录。

## 覆盖边界与下一阶段

每轮999个文件有尾部哨兵；61440-byte文件恰好到窗口末端，工具输出WINDOW_END_NO_BOARD_PROBE，不探测后4KiB应用栈。应用栈物理保护另有阶段⑨仿真全窗口检查，不能写成实板探针结果。after_reset轮从SEQ1再次成功，但未独立观察KEY0动作。仅验证115200 8N1，未验高速UART、DMA、全DDR容量或程序执行。

下一步阶段⑩为新独立真实Hello ELF/BIN/manifest（非空data/bss）与正式LOAD完整END，每块ACK后进入LOADED_UNVERIFIED，DDR可读、仍在ROM且不输出Hello。VERIFY与RUN按后续阶段进行。本轮阶段⑩未开始；成功镜像不重建，继续隔离候选，上板、复位和串口由用户完成。
