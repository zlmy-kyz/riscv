# UART Loader阶段⑧UART帧错与FIFO溢出实板注入准备

2026-10-09更新：用户已完成诊断候选两轮实板验收，每轮117/117 PASS；帧错真实状态0x10、溢出0x20及后续PING/DDR CRC恢复全部通过。已独立核验原始日志并归档，见[两轮实板验收](UART_Loader_UART帧错与FIFO溢出两轮实板验收_2026-10-09.md)。当前IP已由用户切换到该候选，成功基线保留。以下为部署前准备记录，其中NOT_TESTED和待验步骤是当时状态，无需因该旧状态重新上板。

日期：2026-10-09（Asia/Shanghai）。目标是补充阶段⑧剩余两类真实UART故障的实板证据；用户负责PDS/IP生成、位流下载、供电、KEY0复位和COM11运行，Codex只开发、仿真及离线核验。当前板级状态仍NOT_TESTED，不因本轮仿真或PC fixture通过而改写实板PASS。

## 原因与隔离候选

原阶段⑦成功固件对FRAME_ERROR/RX_OVERFLOW都返回NACK8005；只看到8005无法区分两项。新增tests/uart_loader/candidates/uart_fault_stage8_diag，从阶段⑦verified源码复制，仅增加诊断：uart_read_byte在真实STATUS错误返回前把STATUS & 0x30保存为loader_uart_error_status，respond在8005时把两位镜像到RESPONSE capabilities bit24/25；其他响应字节不变。原MMIO地址、W1C清错、FIFO容量、波特率和C错误恢复算法不变；没有软件置假flag或测试专用停止CPU命令。

| 原始STATUS | 诊断响应capabilities | 要求 |
| --- | --- | --- |
| 0x10 FRAME_ERROR | 0x01000003 | 只帧错，不能混合overflow |
| 0x20 RX_OVERFLOW | 0x02000003 | 只溢出，不能混合frame_error |
| 正常/其余NACK | 0x00000003 | 沿用原响应，无LOAD/RUN能力 |

诊断ABI仅用于此候选；旧阶段⑦镜像和原工具不替换。CAP高位不是正式下载协议状态。必须使用同目录诊断PC工具，其日志绑定新ELF/DAT，不能用旧r2工具记录新候选的身份。

| 候选文件 | SHA256 |
| --- | --- |
| build/loader.elf | b70f19595329b11d3e6c09c3b1021699ff24f5e068cac0d7b700aff2d164aa86 |
| build/loader_rom.dat | 391eb696d4cca6803e2469ec5d02a156b38e9fb9849c3cd4754b62853d8533a3 |
| build/loader_ram.dat | 59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a |

代码2960字节/常量48字节/BSS132字节，740条RV32I审查通过；新增快照变量位于RAM0x1080。候选RAM DAT与原成功RAM逐字节相同；启动代码仍须清新增BSS。构建脚本限制输出在候选目录，拒绝覆盖已有ELF；验收后不能重建再直接部署。生产C/RTL/IP/PDS、成功build/ddr_crc及原实板日志不改。

## 真实线级注入

只读PnP查询COM11为USB-SERIAL CH340，VID_1A86/PID_7523；未打开串口，型号不等于驱动支持BREAK的证据。

帧错：Windows SetCommBreak拉低TXD约20ms，ClearCommBreak释放。对FPGA115200/8N1接收器，持续低跨过停止位采样，触发真实FRAME_ERROR。PC检查两次API的BOOL结果和实际持有2..75ms；还必须收到8005、诊断位恰为0x10，API成功本身不算注入成功。BREAK接口依据[pySerial API](https://pyserial.readthedocs.io/en/stable/pyserial_api.html#serial.Serial.break_condition)和[Windows ClearCommBreak](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-clearcommbreak)。若驱动不支持或没有该原因响应，保存FAIL日志后停止，不自动切换波特率或伪造通过。

溢出：一次write发送完整合法PING36字节紧接96个0x55，均115200/8N1。CPU发送60字节ACK期间不pop RX，合法字节持续到来填满16-byte FIFO并触发真实overflow。工具先核对PING ACK，再等待第二个8005，诊断位须恰为0x20；两响应之间不能丢弃输入或做“额外RX”为空检查。该洪泛故意违反正常停等，仅是异常注入；没有合法LOAD/DDR写/随机RUN。若主机/USB分包形成的空隙使FIFO未溢出，本项FAIL，不能用8005推测原因或自动重试。

每个错误后正常PING及只读固定64-byte DDR CRC必须PASS。UART NACK时间从本次注入开始计算须>=95ms；不能对正常恢复ACK套用该下限，也不能把洪泛第二响应的单次read时间误当全部恢复时间。BREAK后返回WAIT_HIGH状态释放，清sticky并排空FIFO后正常操作。

## 当前仿真与离线结果

原速纯引脚9响应专项和三次ROM启动PASS：20ms BREAK触发1次frame_error；连续PING+96-byte洪泛产生43次overflow/丢弃43个新字节，峰值16，CPU两次真实W1C清错。RX412/pop/MMIO/LBU369，TX/引脚解码540，16SW/64LW，最低SP3F40，Errors0/Warnings0；原速恢复分别105.348ms及116.719ms，DDR CRC23C3E508。TB不force CPU、UART、FIFO或错误位，不预置故障flag；实际接受/丢弃字节与CPU退休队列独立核对。native日志：sim/uart_loader/build/uart_fault_stage8_diag/v1/native。

新诊断候选108帧原有异常矩阵完整PASS：73ACK/35预期NACK/37CRC ACK；RX/pop/MMIO/LBU均5839，TX/解码6480，FIFO峰值1，16SW/624LW，Errors0/Warnings0，退出0，耗时1979.84秒；各保护/输入/镜像hash不变。终端继承旧TB的pings=3仅为显示，逐帧RAM实际PING计数35。现在已冻结部署门控，可以交给用户上板验收。该host回归只把隔离TB的MMIO计时源TIME_SCALE64，CPU/UART/DDR时钟与实际波特率不变；真正故障专项TIME_SCALE1。原阶段⑧成功/失败日志均不改。PC13项离线回归、独立板级核验器11项离线回归PASS；fixture是纯PC模拟，不作为实板证据。

全部PASS后已由sim/uart_loader/stage8_uart_fault/finalize.py创建sim/uart_loader/build/uart_fault_stage8_diag/deployment_gate.json，状态STAGE8_UART_DIAGNOSTIC_SIM_PASS、board_result=NOT_TESTED，绑定候选ELF/DAT、原保护文件、全部仿真/工具输入及66项冻结副本；PC fixture实板升级拒绝检查也PASS。工具实际串口模式要求门控PASS且各输入hash匹配；plan-only不打开串口，也不授权上板。

## 用户上板操作（门控已PASS）

1. 当前工作区15项PDS/IP配置、ELF/DAT及两份位流输出已封存于sim/uart_loader/build/uart_fault_stage8_diag/retained_before_deploy，receipt.json逐字节校验PASS。主board_top.sbit SHA256=8475b606d3cd98e1584e9ff17c3eb7f0c8fe952baad3a05bc5c63d7a52a2e8e3；bak位流SHA256=3ca53bb9e29f08c6d8373ca2fd0d732fcdc3a5befda92b8a43aeaeb2f26fd656。仅能称当前工作区输出，未独立绑定实板成功位流。保留你实际已验收位流和两份DAT及日志，记录路径/哈希以便恢复。Codex不改主IP，下面的临时切换、生成和下载由用户操作。
2. 两块IP的INIT_FILE分别选择以下同一对已验收DAT，生成IP并重新综合/实现/生成位流，然后下载诊断候选。不要运行旧build.ps1或验收后重建DAT。

```text
D:/riscv/RISCV/tests/uart_loader/candidates/uart_fault_stage8_diag/build/loader_rom.dat
D:/riscv/RISCV/tests/uart_loader/candidates/uart_fault_stage8_diag/build/loader_ram.dat
```

3. 关闭串口助手，KEY0复位并等DDR初始化；从任意PowerShell目录运行绝对路径工具。每轮新日志拒绝覆盖。默认all模式117响应：原108帧+9个线级响应，合计80ACK/37预期NACK/40CRC ACK，115次write（洪泛write对应两个响应，BREAK不write字节）。

```powershell
$stage8FaultTool = 'D:/riscv/RISCV/tools/uart_loader/candidates/uart_fault_stage8_diag/acceptance.py'
$stage8FaultLogs = 'D:/riscv/RISCV/sim/uart_loader/board'
# 每轮必须KEY0复位并等待DDR初始化；两轮之间再复位。
& C:/python/python.exe $stage8FaultTool --port COM11 --mode all --log "$stage8FaultLogs/uart_fault_stage8_diag_first.json"
# 再KEY0复位，等DDR后执行：
& C:/python/python.exe $stage8FaultTool --port COM11 --mode all --log "$stage8FaultLogs/uart_fault_stage8_diag_after_reset.json"
```

如有位流文件可追加--bitstream实际路径，记录SHA256；该字段不能独立证明该文件已下载。--mode faults只有9响应，不能替代新候选全部主机矩阵的两轮实板验收。

关键输出为wire_break: NACK 0x8005 PASS raw_UART=0x10，wire_flood_trigger_ping: ACK PASS，wire_fifo_overflow: NACK 0x8005 PASS raw_UART=0x20，以及两次恢复PING/CRC PASS，最终RESULT: PASS。任何FAIL/超时/字段或CRC异常保留日志后停止并提交，不自动重试。

4. 用户提交两轮日志和终端输出，Codex用独立struct/zlib核验器check_board.py逐帧归档，再用finalize_board.py汇总两轮all模式234响应（160ACK/74预期NACK/80CRC ACK）。日志范围是新诊断候选；旧阶段⑦二进制仍保留其原验收范围。当前未独立观察KEY0，未采集已下载位流身份，也未完成任何新实板验收。

## 复现与未覆盖

隔离构建只执行过一次；当前已有ELF，以下是首次构建入口记录，不应重复覆盖：tests/uart_loader/candidates/uart_fault_stage8_diag/build.ps1。仿真入口支持--suite native/host与新的--tag，拒绝覆盖已有结果。

```powershell
& C:/python/python.exe sim/uart_loader/stage8_uart_fault/run.py --suite native --tag v1
& C:/python/python.exe sim/uart_loader/stage8_uart_fault/run.py --suite host --tag v1
```

用户日志离线核验入口（--output必须新文件名）：

```powershell
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/stage8_uart_fault/check_board.py D:/riscv/RISCV/sim/uart_loader/board/uart_fault_stage8_diag_first.json --output D:/riscv/RISCV/sim/uart_loader/board/uart_fault_stage8_diag_first_result.json
& C:/python/python.exe D:/riscv/RISCV/sim/uart_loader/stage8_uart_fault/check_board.py D:/riscv/RISCV/sim/uart_loader/board/uart_fault_stage8_diag_after_reset.json --output D:/riscv/RISCV/sim/uart_loader/board/uart_fault_stage8_diag_after_reset_result.json
```

不改变波特率，不扩正式LOAD/VERIFY/RUN，不启动⑨。该模型包含真实CPU/UART/互连/DDR桥及用户口背压，不含DDR PHY训练；新候选实板仍需用户按上述流程证明。诊断位能区分原因，但实板没有FIFO事件计数/峰值或丢弃字节数，不能把仿真的43次/43字节记成实板测量。主机正常matrix108对应的各异常与新诊断位在不同路径验收；未来正式下载能力仍须单独实现和验证。
