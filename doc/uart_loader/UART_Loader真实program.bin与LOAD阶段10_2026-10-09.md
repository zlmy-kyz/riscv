# UART Loader阶段⑩真实program.bin与正式LOAD

2026-10-09最新：阶段⑩两轮各8响应实板已独立核验PASS，DDR CRC32 B2E24920，最终LOADED_UNVERIFIED；[板级汇总与成功归档](UART_Loader真实程序LOAD两轮实板验收_2026-10-09.md)。下文NOT_TESTED及未执行描述保留为候选冻结时的历史状态。下一步按精简计划第②关合并开发VERIFY/RUN/DDR执行/Hello。

日期：2026-10-09（Asia/Shanghai）。阶段⑨随机数据诊断两轮各1000镜像实板PASS后，用户授权下一步。新增隔离固件 `tests/uart_loader/candidates/load_stage10/`、新PC工具 `tools/uart_loader/candidates/load_stage10/`、真实应用 `tests/uart_loader/program_stage10/` 和专用仿真 `sim/uart_loader/stage10/`。Codex没有打开COM11、修改主IP/PDS/RTL、生成或下载位流。当前主IP仍由用户指向阶段⑨random_stage9成功DAT。

当前结果：编译、Harvard镜像/1354条RV32I审查、真实应用ELF/BIN审查、七组真实CPU/DDR/UART仿真及19项PC/独立核验器离线检查全部PASS。部署门控 `sim/uart_loader/build/load_stage10/deployment_gate.json` 为STAGE10_SIM_PASS / board_result=NOT_TESTED，已冻结79项输入及副本、110项证据。阶段⑩实板尚未验收，下一步仅由用户部署同一对DAT并进行两轮下载验收。

## LOAD行为及边界

正式CMD2 LOAD新增两次应答：PC仅发送32-byte Header，Loader校验Header后响应READY1；PC确认READY再发DATA与4-byte DATA_CRC；Loader完整接收、检查块CRC/UART状态后，CPU写DDR并fence，再响应最终ACK0。Header被拒绝时没有READY、不得发送DATA；READY不表示已写入。PC收到最终ACK之前不发送下一块Header。

首块必须BEGIN bit0、地址0x40000000、total1..61440；块长1..256，后续地址严格连续、total/image_crc不变、不能再BEGIN，除非有意用新BEGIN从头替换会话。非末块长度4的倍数，起点4字节对齐；末块END bit1必须恰好收齐total，允许1–3尾字节用SB精确写入。使用减法范围检查，不写后4KiB应用栈，不支持任意MMIO/片内RAM写入。

有效BEGIN撤销旧状态；完整END最终ACK后仅LOADED_UNVERIFIED。LOAD不计算整镜像DDR CRC，不执行程序。PING返回已接收累计字节数、活动image_crc、bit16已收齐；bit17 VERIFIED和bit2 RUN能力始终0。READY accepted_bytes=0，最终LOAD ACK accepted_bytes=本块长度；所有响应包含请求地址和当前image_crc。

最近LOAD块的同SEQ重发先严格比完整Header，重走READY并接收DATA，严格比较完整请求字节，成功仅重发ACK，不写DDR、不增加累计长度。错误Header/CRC/地址/长度/版本/SEQ/状态、截断包、UART帧错/溢出和未完成会话等待5秒都会撤销下载会话与重发缓存；已写入物理DDR可保留，但不允许执行，必须新BEGIN重来。接收字节间100ms超时及坏帧恢复连续空闲100ms保留原约定；未完成会话的5秒等待覆盖MMIO计数回绕差值。完成后的状态保留至新BEGIN、错误、诊断写或复位；只读诊断不会授予VERIFIED。

保留旧受限诊断CMD10–14；诊断写会撤销镜像状态。正式VERIFY3/RUN4仍拒绝8007，本阶段没有跳转代码。独立反例特意给完整LOAD错误的整镜像image_crc、但合法块CRC：可收齐并ACK，但仍未VERIFIED；CMD14按正确CRC做诊断读回后也不置VERIFIED。

## 真实应用与Harvard Loader身份

真实 `program.bin` 为383字节、两块256+127，最后有3-byte尾部；链接entry=_start=0x40000000。`.text`252、`.rodata`61、`.data`64、尾部3字节；`.bss`96字节位于0x40000180–0x400001DF，不在BIN中。BIN从0x40000000至0x4000017E，0x4000017F为对齐间隙。ELF LOAD段LMA=VMA，BSS/程序均在低60KiB；应用保留0x4000F000–0x4000FFFF栈，启动代码自己设置gp/sp并清BSS，再main。

应用代码预留输出HELLO_LOADER_DATA_BSS_PASS/FAIL并检查非空data/bss，但阶段⑩必须没有应用输出。当前只验下载，不把C源码、ELF合法或DDR CRC通过记作应用执行PASS；后续RUN/DDR取指/Hello验收仍分别进行。首次应用汇编因新工具链要求Zicsr标志未编译成功，日志保留compile_failed_initial.log；改用当前CPU支持的机器CSR指令编码，随后生成此唯一成功ELF/BIN，没有重建成功BIN。

Loader继续ROM常驻，独立RAM存常量/状态/缓冲/栈。`.text`5416、`.rodata`112、`.bss`176字节，三个独立缓冲292+292+256=840字节。初始SP0x3FF0，最低实测SP0x3F00。ROM/RAM分开生成，不能把它们合并，也不能把program.bin写进片内数据RAM当作可执行代码。

| 文件 | SHA256 |
| --- | --- |
| Loader ELF | 83954b42e85e6c4475b989e546bc1eee3dd9e9731e33742bcfa315067278b36b |
| Loader ROM DAT | bf91790345b66cf29246b42d909f1c32e8bd978a712ab756c20ae18eaa5609ae |
| Loader RAM DAT | 986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975 |
| program.bin | ccc434866bcf384488e53d972f0fcb4cd6be9a977ce0e4d26c8bb349c3c3dc69 |
| 部署门控 | b5bb8ccff3b009366603b9b01b93f139829373be120a8001318167acb2146ed3 |

program.bin CRC32=`B2E24920`。完整ELF/MAP/DIS/BIN/sections/manifest在program_stage10/build。冻结输入副本在load_stage10/validated_sources；源文件/DAT/BIN不能修改或重建后未经重验直接部署。

## 仿真证据

| 套件 | 响应/检查数 | READY数 | 预期NACK数 | 耗时秒 | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| positive | 49 | 17 | 0 | 25.80 | STAGE10_POSITIVE_SIM_PASS |
| negative | 71 | 12 | 24 | 57.69 | STAGE10_NEGATIVE_SIM_PASS |
| native | 8 | 2 | 0 | 227.67 | STAGE10_NATIVE_SIM_PASS |
| extended | 50 | 12 | 11 | 20.60 | STAGE10_NEGATIVE_SIM_PASS |
| window | 483 | 240 | 0 | 345.51 | STAGE10_POSITIVE_SIM_PASS |
| unverified | 6 | 1 | 0 | 3.43 | STAGE10_POSITIVE_SIM_PASS |
| uart_faults | 14 | 4 | 2 | 604.01 | STAGE10_NATIVE_SIM_PASS |
| pc | 19 | — | — | 0.00 | STAGE10_PC_OFFLINE_PASS |

positive49响应：真实程序、首/末块、严格重复末块无写、PING报告完整未校验、CMD14实际DDR CRC、复位清状态且保留DDR、长度1/2/3/4/255/256/257/1023。negative71响应：非法Header/地址/对齐/长度/total/FLAGS、BEGIN/END、CRC/截断、连续地址/镜像身份变更、重复BEGIN严格字节比较、5秒会话超时、错误恢复及正式VERIFY/RUN拒绝。extended50响应追加同SEQ Header字段变更、SEQ0、旧块重试、部分Header超时、新BEGIN替换和接收中RUN拒绝。

window483响应：240块正式LOAD收齐61440字节，完整实际DDR CRC一致，应用栈4KiB未变，写/读各61440字节。unverified6响应：错误整镜像CRC也只收齐，不产生VERIFIED，诊断读回不授权执行。native8响应：实际93.75MHz/115200 RX/TX引脚、TIME_SCALE1、无CPU/UART/FIFO force，599输入/480输出字节，两块写383、读383，全部响应独立线级解码一致。

uart_faults14响应：LOAD READY后物理BREAK产生帧错、违规在READY发送期间96-byte洪泛填满真实FIFO产生溢出；两类都NACK8005、记录真实原因0x10/0x20、清状态且不写失败块，后续PING与新BEGIN下载真实程序、DDR CRC及未执行检查通过。真实事件frame=1、overflow=43、dropped=43、W1C=2、accepted=788，FIFO峰值16；原速TIME_SCALE1，没有CPU/UART/FIFO force。

所有套件保留真实CPU/分离互连/MMIO/FIFO/共享DDR桥、带背压Pango用户口模型；检查完整接收前无DDR写、逐块字节地址/值/strobe、请求响应退休守恒、真实DDR读退休值、状态RAM、ROM取指、IRQ禁用、脏BSS复位、全64KiB物理内容及保护区。所有有效最终报告均Errors0/无FAIL。fast套件用真实MMIO/FIFO边界字节运输和虚拟时间，不能证明实际UART吞吐；native/faults是实际原速引脚。

故障TB首次faults_v1因不存在的frame_error_event信号加载失败，faults_v2因用延迟一拍overflow事件判断当前FIFO入队导致oracle顺序误报；faults_v3在错误恢复后仍用原始RX总数判断完整退休，未扣除丢弃字节，误报DDR过早。三个FAIL及当时TB副本保留。仅修复独立TB，使用实际frame_error及fifo_full/fifo_pop决定入队，并将退休接受字节数加已丢弃字节数与原始帧边界比较；faults_v4从头14响应通过。同一成功C/ELF/DAT未重建，原正常/负例/native/window PASS输入保持不变。

19项PC离线检查包含碎片读完整握手、错误READY/SEQ/CRC/accepted/VERIFIED位/image_crc、额外Hello、短写/59字节响应/Startup RX/NACK、无自动重试，以及独立struct/zlib核验器拒绝伪造DDR CRC/少帧/执行/重试元数据。fixture明确OFFLINE_FIXTURE_NOT_BOARD，不能算实板证据。现有主PDS/IP、阶段⑦/⑧/⑨镜像和板级档案未改；历史失败/历史NOT_TESTED不改写。

## 用户上板步骤

1. 保留阶段⑨成功位流；已保存的工作区配置副本为sim/uart_loader/board/random_stage9_deployed_workspace。用户临时把两主IP的INIT_FILE分别指向下列同一对候选DAT，然后生成两IP、综合/实现/生成并下载位流。不要运行build.ps1或program_stage10/build.py重建成功产物。

```text
D:/riscv/RISCV/tests/uart_loader/candidates/load_stage10/build/loader_rom.dat
D:/riscv/RISCV/tests/uart_loader/candidates/load_stage10/build/loader_ram.dat
```

2. 关闭串口助手、KEY0复位并等DDR初始化完成，在任意PowerShell目录运行：

```powershell
$stage10Tool = 'D:/riscv/RISCV/tools/uart_loader/candidates/load_stage10/acceptance.py'
$stage10Logs = 'D:/riscv/RISCV/sim/uart_loader/board'
& C:/python/python.exe $stage10Tool --port COM11 --log "$stage10Logs/load_stage10_first.json"
```

3. 再KEY0复位并等DDR初始化，执行第二轮，使用新日志：

```powershell
& C:/python/python.exe $stage10Tool --port COM11 --log "$stage10Logs/load_stage10_after_reset.json"
```

工具固定使用已审查program.bin，先核验STAGE10_SIM_PASS和全部冻结输入才打开串口；每轮8条PASS（3 PING、2 READY、2最终LOAD ACK、1受限诊断CRC），最终必须RESULT: PASS stage10 real program LOAD; LOADED_UNVERIFIED; diagnostic DDR CRC matches; no Hello/RUN。无自动重试/flush，不得出现Hello，任意FAIL停止并保留日志。可选--bitstream用户实际文件仅记录文件身份，不独立证明已下载。

无需粘贴长输出，告诉Codex完成即可离线读取上述两份JSON。Codex用独立check_board.py核验并新增固定原始副本（不占用串口）：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe sim/uart_loader/stage10/check_board.py --first sim/uart_loader/board/load_stage10_first.json --after-reset sim/uart_loader/board/load_stage10_after_reset.json --output sim/uart_loader/board/load_stage10_board_result.json
```

该板级命令当前未执行，因为尚无用户提交的阶段⑩实际日志。按用户要求，后续已合并为[三个验收关口](UART_Loader剩余阶段精简计划_2026-10-09.md)：本阶段为第①关；两轮实板通过后，第②关一起开发并验收正式VERIFY、RUN、DDR执行与基本Hello；第③关验收同位流反复下载、第二BIN及CoreMark。原⑪至⑮编号保留为检查项索引。完整DDR PHY、全512MiB、高速UART、永久DDR事务停顿watchdog和实际程序执行未由本阶段覆盖。
