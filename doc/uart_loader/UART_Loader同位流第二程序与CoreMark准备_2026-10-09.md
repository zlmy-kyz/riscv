# 同位流第二程序与 CoreMark 下载准备

2026-10-09 更新：用户五步测试已完成，第二程序、两组短迭代CRC及两组60次正式运行全部实板PASS，独立核验/279项归档完成。详见[实板验收](UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。下方“待实板/NOT_TESTED”保留为准备时记录。

日期：2026-10-09。用户本次选择两步：换第二个 C 程序，以及 CoreMark 先验算法 CRC 再正式运行。开发和集中仿真已完成，**本次 UART 下载实板验收仍待用户执行**。额外至少10轮复位不在本次任务范围内，不据此把整个精简计划第③关标记为完成。

## 已完成及保留范围

沿用 VERIFY/RUN/DDR/Hello 已实板 PASS 的同一 Loader ROM/RAM DAT 和 FPGA 位流，仅通过 UART 更换 DDR 中的应用 BIN。没有重建 Loader、IP 或位流，没有操作 COM11、JTAG、供电或 KEY0。主 PDS/IP 仍保留阶段⑩配置；请沿用此前已经输出 Hello 成功的板上候选位流，不能把主工程旧位流当作本次 Loader。

成功位流为 `D:/riscv/RISCV/sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit`，SHA256 `31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0`。原成功170项快照、原门控76项输入和71项证据以及18项候选PDS产物/副本核对一致。阶段⑦至⑩档案保留。下载和复位的现场动作未由 Codex 独立观察，工具绑定的是已核验文件身份和实际串口协议证据。

新增隔离目录：

- `D:/riscv/RISCV/tests/uart_loader/program_second/`：新程序 main.c、startup.S、linker.ld、build.py；build 下为 ELF/BIN/manifest 和汇编检查记录。
- `D:/riscv/RISCV/tests/uart_loader/coremark_uart/`：原裸机端口源码副本及四套已验收 ELF/BIN 的逐字节副本；origin.json 绑定原构建和完整算法证据。
- `D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/`：通用 manifest 下载工具、协议计划、严格应用输出检查和用户五步脚本。
- `D:/riscv/RISCV/sim/uart_loader/applications_stage3/`：真实CPU私有TB、完整应用入口、60次专用启动入口、PC离线检查和实板独立检查。

第二个程序构建一次：`C:/python/python.exe D:/riscv/RISCV/tests/uart_loader/program_second/build.py`。当前成功 ELF 已存在，构建器拒绝覆盖，**本次验收直接使用已经通过仿真的同一 BIN，不重建后直接下载**。RV32I/ILP32、GCC15.2.0、-Os、无LTO、裸机链接0x40000000，乘法由 libgcc 的 RV32I 软件实现。

新 C 程序检查32个 data 初值和32个 BSS 零值，再计算1至32平方和，精确输出 `SECOND_PROGRAM_PASS sum=11440\r\n`。文件587字节，CRC32 `280DE354`；包含三字节非对齐文件尾，低60KiB应用窗口及顶部4KiB栈保持不变。BIN SHA256 `d93bce4969897fc5c242177e014afdb944dd944cd37a57ebee0b2085ea1a88d8`。

## 集中验证结果

最终门控 `D:/riscv/RISCV/sim/uart_loader/build/applications_stage3/deployment_gate.json` 为 **SAME_LOADER_APPLICATIONS_SIM_PASS**，冻结196项输入、74项证据和196项源副本，35项PC离线检查PASS。实板字段为NOT_TESTED。

| 最终仿真 | 范围 | 响应 | 结果位置 |
| --- | --- | --- | --- |
| second 原速 | 实际115200引脚收发，真实Loader/CPU/DDR，data/BSS和31字节输出 | 9 | v3/second_native/results.json |
| performance_1 | UART下载、VERIFY、RUN、完整算法及全部CRC/精确输出 | 107 | v3/performance_1_fast/results.json |
| validation_1 | 同上，另一组种子 | 107 | v3/validation_1_fast/results.json |
| performance_60 | UART下载、VERIFY、RUN、DDR退休、gp/sp、BSS、main及4124条应用退休 | 107 | v4/performance_60_fast/results.json |
| validation_60 | 同上 | 107 | v4/validation_60_fast/results.json |

表中路径均位于 `D:/riscv/RISCV/sim/uart_loader/build/applications_stage3/`。五组均Errors:0、Warnings:0、无FAIL，输入和保护文件哈希未变。全部应用由Loader通过UART写入DDR，无应用DDR预装；VERIFY和RUN分别整镜像重读CRC，RUN ACK发完才取首条应用指令。每条数据事务响应和退休、DDR指令退休、写字节位置、应用栈和整块物理DDR均有自动检查。

第二程序原速实际RX803、TX571字节；TX包含540字节协议及31字节应用输出，两个方向独立串行解码。CoreMark专用快速传输仅加速UART字节输入/输出，保留真实CPU、MMIO/FIFO、DDR桥和用户口延迟；计时器scale=1。不是DDR PHY训练模型或新的物理模型回归。

两组1次输出CRC分别为：

| 配置 | seedcrc | crclist | crcmatrix | crcstate | crcfinal(1次) | crcfinal(60次) |
| --- | --- | --- | --- | --- | --- | --- |
| performance | e9f5 | e714 | 1fd7 | 8e3a | e714 | a14c |
| validation | 18f2 | e3c1 | 0747 | 8d84 | e3c1 | 6770 |

新UART完整短迭代仿真计时ticks为8563099和9053158。1次执行不足10秒，CoreMark原程序会打印时间不足的ERROR及Errors detected；本轮工具只在**唯一错误是时间不足、算法全部CRC正确、输出完全匹配**时给CRC_FUNCTIONAL_PASS，不能据此认定正式跑分。

四个CoreMark BIN直接复制原已验收构建，不重编译。大小performance_1/validation_1/performance_60/validation_60分别13216/13224/13220/13228字节。原完整1次/60次Full Boot算法证据为 `D:/riscv/RISCV/sim/coremark/build/results.json` 和 `results_60.json`；60次原模型约90分钟/组，完整算法已通过，本轮只重测变化的UART装载/启动路径。原预置RAM复制启动的实板60次PASS是历史证据，不能替代本次UART下载实板验收。

保留失败：首次PC样例读取Windows文件CRLF，修正为文本规范化后28项通过，不改变应用输出检查。v3/performance_60_fast在主循环执行期间结束，200周期后仍有已接受DDR事务未退休，触发事务守恒检查。新增独立partial TB仅增加结束前等待已接受访问退休/响应，v4两组通过；已通过完整CRC和原速串口的TB保持不变，不改CPU/桥/Loader，也未绕过事务检查。旧失败结果和日志原位保留。

## 用户实板操作：一次启动五步脚本

1. 保持此前 Hello 成功的 Loader 位流。关闭串口助手；板供电正常，COM11空闲。板若断电后丢失配置，由用户重新下载**同一已成功位流文件**，不重新生成位流。
2. 在PowerShell执行下面命令。脚本依次运行second、performance_1、validation_1、performance_60、validation_60；每次提示时按KEY0，释放并等DDR初始化完成，再按回车。

```powershell
& 'D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1'
```

脚本使用C:/python/python.exe、COM11、115200 8N1；每个BIN都是PING→分块LOAD→完整VERIFY→唯一RUN→应用输出。Loader本身一直保留在片内ROM；应用返回后驻留DDR，下一程序必须KEY0复位再从SEQ1开始。

成功标记依次为SECOND_APPLICATION_PASS、两次COREMARK_CRC_FUNCTIONAL_PASS、两次COREMARK_FORMAL_BOARD_PASS，最后总验收RESULT:PASS。60次运行必须先通过对应模式的实际1次CRC日志；正式检查要求60次、全部算法CRC、Correct operation validated、无ERROR、ticks不少于937500000(10秒)，以及主机40秒截止，避免32位cycle计数单周期45.81秒回绕误判。计时为93.75MHz，不使用仿真耗时当板级性能。

所有原始日志保存在 `D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_first/`：five app名.json及board_result.json。总验收脚本核验实际串口来源、每帧双CRC及全部字段、完整输出、应用manifest与同一成功位流身份，并绑定两个正式运行的对应短迭代实板证据。协议CRC32与CoreMark算法CRC16分别检查。

失败立即停止，不自动重试、不清除异常RX、不重复RUN、不覆盖旧日志。若日志已存在，可由用户选择新目录：

```powershell
& 'D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1' -LogDirectory 'D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_second'
```

执行后交回日志目录或结果，由Codex离线核验和归档。当前不记录实板PASS或新分数。

## 仿真复现入口

仿真输出tag不得复用已有目录，不触碰冻结成功BIN：

```powershell
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/applications_stage3/run.py --application second --native --tag future01
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/applications_stage3/run.py --application performance_1 --tag future01
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/applications_stage3/run.py --application validation_1 --tag future01
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/applications_stage3/run_partial.py --application performance_60 --tag future01
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/applications_stage3/run_partial.py --application validation_60 --tag future01
```

门控已经冻结，不为重复运行改写历史证据。若应用或工具输入变化，现门控拒绝下载，须使用新隔离候选验证。当前没有改共享RTL，因此本轮未重复既有CPU/DDR物理回归。未覆盖本次实际UART CoreMark计时、额外10轮复位、掉电恢复动作及板上物理故障注入。
