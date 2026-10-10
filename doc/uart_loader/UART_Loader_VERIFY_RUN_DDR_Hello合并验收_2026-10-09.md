# UART Loader VERIFY / RUN / DDR / Hello 合并验收

2026-10-09最新：用户完成一次合并实板验收，157/157响应和唯一RUN后的精确Hello均通过；独立核验及170项成功归档完成，第②关完成。详见[实板验收](UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md)。下方保留开发、构建和待上板时的历史记录；门控的NOT_TESTED不改写。

日期：2026-10-09。精简计划第②关已完成开发和集中仿真，门控为 `COMBINED_SIM_PASS`；实板仍 `NOT_TESTED`。本记录后续补充隔离位流构建与实际部署结果，不改写冻结门控的生成时状态。

## 目的与隔离范围

按用户要求，将正式 VERIFY、RUN、DDR 取指和 Hello 合为一个开发与验收阶段。Loader 和 Hello 各构建一次，随后所有仿真使用同一 ELF/DAT/BIN；没有重新编译软件来部署。候选为 `tests/uart_loader/candidates/verify_run_hello/`，应用为 `tests/uart_loader/program_hello/`，PC 工具为 `tools/uart_loader/candidates/verify_run_hello/`，私有仿真为 `sim/uart_loader/verify_run_hello/`。共用 CPU、总线、DDR 桥与 UART RTL 均未修改。

阶段⑩两轮实板成功档案继续保留，原主 PDS/IP/位流没有被本次候选覆盖。主工程仍选择阶段⑩ Loader；新 PDS 副本、两块初始化 IP 和候选位流均留在 `sim/uart_loader/build/verify_run_hello/pds_candidate/`。主项目配置与板上实际运行镜像是两个事实，须以本次实际下载记录确认板上状态。

用户最新要求将上板相关操作交回用户：供电、JTAG下载、KEY0复位及COM11串口测试均由用户操作；Codex提供已构建候选、操作步骤，并在收到日志后离线核验归档，不再操作下载器或串口。不得在旧阶段⑩位流上运行新验收工具。

## 实现与关键检查

LOAD 保留 Header→READY→DATA/CRC→实际 DDR 写→ACK。CMD3 VERIFY 与 CMD4 RUN 均只允许入口 `0x40000000`、完整镜像长度 4–61440 字节、合法新 SEQ、flags=0/version=1 和已完整 END 的镜像身份，控制帧 UART payload 为空且仍带 4-byte CRC。任何 NACK、新 BEGIN 或诊断写均撤销 VERIFIED。

VERIFY 对实际 DDR 全文件重新读回 CRC32，全部匹配才设置 VERIFIED。RUN 要求 VERIFIED 并再次读取 DDR CRC32，覆盖验证后内存损坏；失败不跳转。诊断 CMD14 CRC 不授予 VERIFIED。RUN 不重试，等待整条 ACK 的 UART 发送完成且空闲，再禁用 IRQ、执行 CPU 支持的 `fence rw,rw`，跳转入口。该 CPU 没有 Cache 且不支持 FENCE.I，没有引入该指令。

Loader 文本 6256 字节，RAM 常量 112 字节、BSS 188 字节、RX 缓冲 840 字节，ISA 审查为 1564 条合法指令，均在既有 Harvard 16 KiB 边界内。新 manifest 的布局审查继承 `ROM_RESIDENT_LOAD_STAGE10` 标签，能力以本轮源码和 `COMBINED_SIM_PASS` 门控为准；未改写已冻结 manifest。

Hello BIN 为 367 字节，两块 256+111 字节，CRC32 `5E142E06`，SHA256 `a9209268576a07fb8cb4cc55920cb20494682aefd6a22f620d3000f9338ab79d`。非空 data 64 字节，BSS 96 字节；BSS 不在 BIN 中。启动代码设置 gp=`0x4000092C`、sp=`0x40010000`，在 main 前清零 24 个 BSS word，main 检查 data/BSS 后输出唯一的 13-byte `Hello World\r\n`。末尾 3-byte 标记、BIN 外边界和保留栈区均检查。

同一对 Loader DAT/ELF 身份：

- `loader.elf`：`ac8127d7e67702d31d2e6bf10c171de1dc631c3d7307fb3387b5e8fb4ff40c6a`
- `loader_rom.dat`：`53a2d9912e85b6b5c90768fb0422be6cde8d5bdab37ef07b7eabfb065b76cea1`
- `loader_ram.dat`：`986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975`

## 集中仿真与离线核验

| 检查组 | 响应数 | 结果 | 用时 | 汇总路径（工程根相对） |
| --- | ---: | --- | --- | --- |
| positive | 11 | PASS | 6.59 s | `sim/uart_loader/build/verify_run_hello/v3/positive/results.json` |
| negative | 157 | PASS | 67.65 s | `sim/uart_loader/build/verify_run_hello/v3/negative/results.json` |
| native | 9 | PASS | 206.55 s | `sim/uart_loader/build/verify_run_hello/v3/native/results.json` |
| UART_verified_invalidation | 25 | PASS | 11.49 s | `sim/uart_loader/build/verify_run_hello/uart_event_v2/negative/results.json` |
| control_timeout_CRC | 34 | PASS | 15.4 s | `sim/uart_loader/build/verify_run_hello/control_v1/negative/results.json` |

各组真实 CPU/SoC/DDR 桥执行同一固件，三次 ROM 启动检查，Errors=0，无 FAIL。DDR 初始为 A5 污染数据，应用从 UART LOAD 写入，不预装。逐笔核对 SRAM/DDR 请求、写字节与退休，RUN ACK 全部解码且 UART 空闲之前不能出现应用 DDR 取指；之后核对实际退休指令与 BIN、入口、gp/sp、data/BSS 和精确 Hello。

原速 native 使用 93.75 MHz / 115200 UART 引脚，无 force；RX 619 / TX 553 字节，367-byte LOAD、734-byte VERIFY/RUN 实际读回、11139 条 DDR 应用指令退休。加速正向/负向与超时组通过真实 FIFO/MMIO 字节注入并缩放 TB 计时，不能把该模式当成线速验收。

157 响应矩阵覆盖空镜像、未 VERIFY 的 RUN、非法/不对齐/ROM/MMIO/栈区/越界入口、子范围、长度/身份、flags/version/SEQ、缺失 END、整镜像 CRC 错误、VERIFY 前实际内存损坏及 VERIFY 后 RUN 前再次读回发现损坏、重复控制、新 BEGIN 失效和错误后恢复。25 响应 UART 组通过私有 TB 注入 frame_error/overflow 事件验证 sticky error 和 VERIFIED 撤销，属于 `MMIO_EVENT_MODEL_NOT_PHYSICAL_UART`，不宣称本候选完成实际 BREAK/FIFO 洪泛验收。原阶段⑧线级异常实板与阶段⑩原速故障仿真证据各自保持原范围；阶段⑩两轮实板只验收正常 LOAD。34 响应组覆盖 VERIFY/RUN 截断超时、坏控制 CRC、失效后禁止 RUN 以及重新下载恢复。

PC 工具 14 项离线核验 PASS，来源 `OFFLINE_FIXTURE_NOT_BOARD`。`board_plan.json` 仅计划：157 响应、最终唯一 RUN，不打开串口。实板计划将仿真中两项物理内存损坏替换为明确身份拒绝，不伪造板上损坏覆盖。

冻结门控保存 76 项输入、71 项证据、76 个源副本：`sim/uart_loader/build/verify_run_hello/deployment_gate.json`。阶段⑩原 79 项输入/110 项证据以及当前主 PDS/IP/位流的 10 个成功配置文件与其副本均匹配。Markdown 不在冻结功能输入内，更新文档不会影响门控。

## 失败记录和修复范围

全部失败日志保留。v1 positive 的 SP 监视器误把 AUIPC 中间值当最终 sp；v2 negative 的错误整镜像 CRC 用例身份与保存值不一致，先触发 8008，已修正期望输入以实际走 CRC 8001；v2 native 的 TB 在应用正常发送 UART 时仍要求 TX 空闲，已改为仅首个 DDR 取指检查；uart_event_v1 最终事务守恒未计终端循环的一个在途取指，已修复私有 TB。固件与 DAT/BIN 无改动，v3 / uart_event_v2 / control_v1 为最终冻结结果，旧结果只作历史。

首次隔离 PDS 构建完成 Compile/Synthesize，但 Device Map 因缺少主工程静态 DebugCore FIC 输入而失败（Flow-0037）；`cli_build.log` 保留。已复制该 FIC，仅将 designInputFile 路径改到隔离候选，收据为 `pds_candidate/fic_relocation.json`。恢复 PDS 流程会重新运行综合，但没有重建软件或改变成功镜像；`cli_resume.log` 记录当前构建。最终选中 seed4，已完成位流、时序、生成初始化及实现网表的完整审计，结果见下节。

JTAG 初次探测能识别 USB Cable II，但扫描不到 FPGA（JtagServer-0306），已请求现场通电并接好 JTAG。尚未下载候选或打开 COM11；位流完成前已再次扫描，仍无 FPGA；COM11 枚举为 USB-SERIAL CH340，仅枚举，未打开。不能据此记录实板 PASS。

## 隔离位流构建完成，等待现场连接

20:11:03 完成 Generate Bitstream，审计收据为 `sim/uart_loader/build/verify_run_hello/pds_build_result.json`，状态 `COMBINED_ISOLATED_PDS_BUILD_PASS`。候选位流：`sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit`，3791112 字节，SHA256 `31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0`。

最终 seed4；PG2L100H / FBG484 / -6，CPU 时钟 93.75 MHz。最终多角时序报告 `report_timing/board_top.rtr` 为 All Constraints Met，slow/fast setup 0.144/4.096 ns，hold 0.138/0.102 ns。该结论覆盖原项目已有约束；沿用的 reset/UART/LED/部分 DDR 端口未约束 warning 保留，不宣称所有物理 I/O 均有外部时序约束。候选未放宽时钟或更改这些约束。

独立解析 ROM 四个 8-bit 数据通道及 RAM 两组地址银行/两个 16-bit 数据通道，重建全部 8192 个 32-bit 初始化字，与冻结 DAT 逐字一致；再次核对实现后网表 8 个存储实例、每实例128个 INIT 参数全部一致。已保存18项 PDS/IP/FIC/网表/时序/日志/位流副本于 `validated_pds/`，其哈希见收据。76项新冻结输入/71项证据/源副本及阶段⑩输入、证据、10个当前成功配置文件均匹配；没有更新主 PDS/IP/位流，也没有重建软件。

两次只读 JTAG 扫描均能连接服务器和识别 USB Cable II，但均为 JtagServer-0306：No devices detected。最新原始日志 `sim/uart_loader/build/verify_run_hello/jtag_rescan/scan.log`。尚未 cfg_assign_file/cfg_program、复位或打开 COM11。当前必须先由现场通电并接好 JTAG，确认能扫描到目标 PG2L100H 后才下载候选。无需重新生成位流或重跑已通过的仿真。新下载后一次执行157响应链路，最后唯一 RUN 和13-byte Hello，另独立核验保存 ACTUAL_SERIAL 日志。

## 用户上板步骤（最新分工）

1. 给开发板通电，接好JTAG及原成功COM11串口连接，关闭占用COM11的串口助手。
2. 在PDS的配置下载窗口扫描链，确认目标PG2L100H；选择下列已生成的候选sbit，下载到FPGA。无需修改主IP INIT_FILE、重新生成IP或重新构建。主工程根目录旧sbit继续保留。

   `D:/riscv/RISCV/sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit`

3. 下载成功后按KEY0复位，释放并等DDR初始化完成。
4. 在PowerShell执行下面完整命令；路径都是绝对路径，可从任意当前目录运行。工具自行打开COM11并核对157个响应和唯一RUN后的13-byte Hello，不需要另开串口助手。

```powershell
$stageHelloBit = 'D:/riscv/RISCV/sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit'
$stageHelloTool = 'D:/riscv/RISCV/tools/uart_loader/candidates/verify_run_hello/acceptance.py'
$stageHelloLog = 'D:/riscv/RISCV/sim/uart_loader/board/verify_run_hello_first.json'
& C:/python/python.exe $stageHelloTool --port COM11 --bitstream $stageHelloBit --log $stageHelloLog
```

5. 最后一行应为 `RESULT: PASS combined LOAD -> VERIFY -> RUN -> Hello World`。部分NACK是预期错误测试，工具对应项显示PASS即可。用户返回最后几行或日志路径；Codex读取原始JSON并独立核验归档。一次验收即可，不要求本关额外第二轮。

若扫描不到FPGA或下载失败，停在下载步骤；若串口工具报错/FAIL，保留原日志与最后输出，交给Codex分析，不直接重跑覆盖。已有同名日志时会拒绝执行，后续复验另取新文件名。

## 实板一次验收入口

仅在候选位流构建/时序/同 DAT 身份审计通过、JTAG 确认为目标 FPGA 并完成新候选下载后执行。下载后的启动会等待 DDR 初始化；从 SEQ1 开始，串口助手须关闭。

```powershell
& C:/python/python.exe D:/riscv/RISCV/tools/uart_loader/candidates/verify_run_hello/acceptance.py --port COM11 --bitstream D:/riscv/RISCV/sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit --log D:/riscv/RISCV/sim/uart_loader/board/verify_run_hello_first.json
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/verify_run_hello/check_board.py --log D:/riscv/RISCV/sim/uart_loader/board/verify_run_hello_first.json --output D:/riscv/RISCV/sim/uart_loader/board/verify_run_hello_board_result.json
```

验收工具拒绝覆盖日志，开串口前检查冻结输入，READY 后才发 DATA，任何非预期响应、CRC、额外 RX 或错误 Hello 均保留日志停止，不自动重试/重复 RUN。最终需要 157 响应全部匹配、唯一 RUN 后精确 Hello，独立核验器仅接受 `ACTUAL_SERIAL` 来源，结果应为 `COMBINED_ACTUAL_BOARD_VERIFIED`。当前尚无该实板日志。

第②关实板通过后才进入第③关：同一成功 Loader 位流的至少 10 轮复位、第二份 BIN 与 CoreMark。当前仿真 DDR 是带背压的用户口模型，未包含 PHY 训练；实际 DDR 初始化和板级链路由此次实板验收确认。
