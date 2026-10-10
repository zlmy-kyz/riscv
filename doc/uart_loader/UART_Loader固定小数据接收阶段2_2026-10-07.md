# UART Loader阶段②/③：固定小数据与CPU轮询FIFO接收

执行日期：2026-10-07，归档更新：2026-10-08，Asia/Shanghai。

## 后续实板结果：复位前后各100次固定接收PASS

用户提供COM11运行rx-test的完整RX_TEST1–100 ACK输出。读取本机rx_fixed100.json，
逐帧核对100个请求编码/固定向量、SEQ、响应Header/Payload CRC、status=ACK和accepted_bytes=64，
全部PASS。有效payload累计6400 bytes、请求10000 bytes、应答6000 bytes，往返15.411–16.064ms。
payload_crc=23C3E508是本固定RAM接收向量/包校验，不是DDR CRC。
固定原始证据归档sim/uart_loader/board/rx_fixed100_first_verified.json，
SHA256=6bc43e1bb6acceeb78387556e55ee8216a76c62cba9bfe003dd8de0d334be38c；
汇总rx_fixed100_first_result.json。原JSON含全部请求/响应hex，未覆盖阶段①任何证据。

用户当前两个IDF的INIT_FILE已指向build/rx_fixed对应DAT，ROM/RAM哈希与下方最终候选一致。
未独立生成/下载位流或打开串口，未采集实际下载位流身份；实板结果依据用户输出与原始日志。
用户按此前要求提供复位后第二轮100次ACK输出；独立读取rx_fixed100_after_reset.json，
请求固定向量编码、SEQ1–100、响应Header/Payload CRC、status=ACK和accepted_bytes=64全部PASS。
往返15.450–15.909ms。固定归档sim/uart_loader/board/rx_fixed100_after_reset_verified.json，
SHA256=2665249a3e5884550d3591570658afda2f424f24acccbc5ace909e8f6aa57f37。
复位操作依据用户提交的所要求第二轮结果，未独立观察按钮或PHY训练。

两轮合计200 ACK、固定payload12800 bytes、请求20000 bytes、应答12000 bytes。
机器汇总rx_fixed_stage2_board_result.json为board_result=PASS；原首轮记录保持历史身份不覆盖。
阶段②/③固定RAM接收/CPU轮询FIFO实板PASS。未覆盖断电重上电、高速UART或实板负例，
未实现DDR写入、DDR读回CRC、LOAD/VERIFY/RUN，不能标记程序下载PASS。
下一步唯一动作：受控固定数据CPU写DDR、CPU读回并逐字节比较。本轮只归档，不继续实现。
以下为此前实现与仿真记录。

## 授权与前置

用户确认阶段①复位后100次PING通过，并要求“执行下一步”。本轮只实现固定64-byte接收、
CPU轮询FIFO存入片内RAM并逐字节比较，不进入DDR写入/读回、LOAD/VERIFY/RUN或完整程序下载。
阶段①两轮原始串口JSON各100 ACK且请求/SEQ/Header/Payload CRC核对通过，runner核其PASS与归档哈希。

阶段①当前IP仍指向tests/uart_loader/build/loader_rom.dat与loader_ram.dat。
修改源码前保存tests/uart_loader/verified/ping_stage1完整源码与build快照，
sim/uart_loader/build/ping_stage1_sources保存TB/runner，tools/uart_loader/verified/ping_stage1保存PC源码。
原build/根镜像不覆盖；新构建默认输出tests/uart_loader/build/rx_fixed，脚本拒绝覆盖原build/根。
本轮不自动改IP或主工程，不生成/下载位流，不打开串口，不重新运行数小时PHY回归。

## 协议与软件变化

新增受控诊断CMD0x10 RX_TEST，沿用RVLD32-byte Header、60-byte Response、ISO-HDLC CRC与小端字段。
Header FLAGS/ADDRESS/TOTAL_LENGTH/IMAGE_CRC32必须0，LENGTH必须64。不是v1对外任意内存操作。
64-byte向量：前16字节00 FF 55 AA 52 56 4C 44 0A 0D 80 7F FE 01 02 00；
索引i=16..63按(i*37+11)&255。CRC32=23C3E508，包总长100 bytes。

CPU验证Header后，先检查长度再读DATA/tail到0x2020–0x2063；校验64-byte尾CRC，再逐字节
匹配固定向量。成功ACK的ADDRESS=0、accepted_bytes=64（仅本诊断帧）、actual_ddr_crc=0、
capabilities=3，不声明活动镜像、DDR CRC或RUN。PING格式和能力保持原值。
三个BSS诊断量记录唯一匹配帧数、累计匹配字节数、最近成功RAM向量CRC；失败不更改它们。
成功序号递增；最近相同RX_TEST重复ACK但不再计数；同序号换命令拒绝8009。
坏CRC8001、非法长度8003、合法CRC但向量不匹配800A、未开放RUN8007；坏帧先持续轮询排空RX，
等待100ms连续空闲，再发送NACK，避免拒绝Header时仍在发送的payload撑满FIFO。
仍拒绝LOAD/VERIFY/RUN；不会跳DDR，也不会把整个payload回传比较。

地址分区沿用阶段①：ROM0–3FFF，RAM常量100起、BSS1000起、256-byte缓冲2000起；
栈3000–3FEF，初始sp3FF0向下，保留末16字节。新代码不能使用当前数据RAM取指。
构建仍RV32I/ILP32/-Os/no-relax，局部CSR已实现范围，ISA逐指令审查；无新RTL、DMA或Cache。

## 测试方法、输入与判据

从根目录执行tests/uart_loader/build.ps1，再执行python sim/uart_loader/run.py --stage rx-fixed。
读取已有同一DAT，阶段①门禁→ROM驻留前置→固定接收，每层失败即停。

| 层 | 输入与方法 | 预期/PASS | FAIL |
| --- | --- | --- | --- |
| 驻留 | 3次SoC复位，BSS毒化，RAM不重载 | 每次完整清BSS、常量/CRC标准向量/栈/哨兵正确，无UART/DDR | 未清零、boot error、栈/边界损坏、trap |
| 正常接收 | 64-byte固定二进制，帧内连续115200/8N1字节；两次启动各2唯一帧 | ACK64、CPU RAM内容逐字节等于输入，诊断CRC23C3E508 | 任意字节/计数/CRC不一致 |
| 重复与SEQ | 重复最近RX_TEST，再用同SEQ换PING | 前者ACK不重复计数，后者8009；后续正确帧可继续 | 重复执行、换命令错误ACK、SEQ状态改变 |
| CRC/数据 | 尾CRC损坏；另发有效CRC但数据第20字节错误 | 分别8001/800A，成功计数/CRC不变，空闲恢复后可收正确帧 | 错误数据ACK、恢复失败 |
| 长度 | Header/尾CRC合法、DATA65字节 | 8003，缓冲上界哨兵不变，尾数据只由恢复流程丢弃 | 越界写/意外执行/错误ACK |
| 未开放命令 | RUN | 8007、没有DDR请求或跳转 | RUN执行或DDR请求 |
| 复位 | 第二启动重新SEQ1 | 所有新诊断量清零，PING及两帧数据再次通过 | 状态残留/第二轮失败 |

14帧含4个正常PING、4个唯一RX_TEST、1个重复RX_TEST、5个NACK；
原始RX共1017 bytes，TX共840 bytes。逐拍比较UART RX→FIFO pop→MMIO返回→实际CPU LBU退休值，
核RAM存储；TX接受值与引脚独立解码均对Python/zlib基准。FIFO16字节，MMIO响应延迟7拍。
任何UART错误、总线error、trap/IRQ、ROM取指越界、RAM分区/栈哨兵损坏或DDR请求均立即FAIL。
TB将DDR启用且init_done=1，但接口无ready/返回；禁止用用户口未握手掩盖意外请求。
通过还须进程退出0、唯一RESULT: PASS、无FAIL、编译/运行Errors0，完整原始捕获匹配与哈希保护通过。

## 最终结果：固定小数据接收与CPU轮询FIFO仿真PASS

构建PASS：修复后ROM.text2236 bytes（0–8BB），RAM.rodata48 bytes（100–12F），BSS92 bytes（1000–105B），
559条机器码审查通过，非零可变.data为0，ELF入口0。接收缓冲256、诊断16 bytes，size bss364包含这两项。
前置驻留实测3次复位PASS，23字BSS清零，最低sp3F40（176/4080 bytes），2775退休/4100周期，
Errors0/Warnings0，DDR请求0。

修复后完整固定接收实测PASS：14帧、两次启动、4个唯一接收+1个重复、4正常PING与5个NACK，
全部计数、状态、RAM payload与诊断CRC正确；错误帧恢复后正确帧可继续，复位后状态清零。
RX/FIFO pop/MMIO返回/CPU LBU退休各1017字节，TX接受/引脚解码各840字节，
完整原始捕获匹配Python/zlib基准；FIFO峰值1/16，最低sp3F40、176/4080 bytes。
19361664条退休、52771383个运行周期，DDR请求0，编译/运行Errors0/Warnings0、进程退出0。
固定接收墙钟876.17秒（约14.6分钟），前置驻留2.07秒。
results.json为FIXED_RX_STAGE_PASS，protected_unchanged与image_unchanged均true；
validated_image.json绑定上述最终同一候选。验收结束后未重建DAT。
实板board_result仍NOT_TESTED；本轮完成阶段②/③的片内接收仿真，不等于DDR写入或程序下载。

候选SHA256：

| 文件 | SHA256 |
| --- | --- |
| loader.elf | dadccdaac42a208b6398bb13bea0f944fa6efa2962c84f7c29927cee16d9eff3 |
| loader_rom.dat | c6adca13f459d35c81dc356ab4850f6491e38b239829840190c940c816cece68 |
| loader_ram.dat | 59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a |

ELF/MAP/DIS/readelf/symbol/stack usage/DAT/manifest在tests/uart_loader/build/rx_fixed。
仿真输入bin/hex、cases/state、compile/modelsim日志、原始RX/TX和decoded JSON在
sim/uart_loader/build/rx_fixed/rx_fixed；驻留日志在同级residency，总results/validated_image在父目录。
runner保护原生产RTL/IP/PDS/FDC、Echo/CoreMark、阶段①镜像与实板证据，并核新候选验收前后一致。

## 失败与修复记录

首轮候选（原.text2204 bytes/551条指令）在65-byte长度拒绝用例失败：
UART event error，cycle25966181、仿真时间276955622525ps，此前有效/重复/SEQ/CRC/错误向量用例均按预期。
时序分析：Header长度拒绝后先进入阻塞TX发送60-byte NACK，此时PC仍连续发送65-byte DATA与尾CRC，
RX没有被CPU服务，16-byte FIFO不能容纳剩余69字节。此前PING未开放命令只有4-byte尾CRC，没有触发这个问题。

修复将坏帧排空/100ms连续空闲恢复放到NACK发送前；TX自身超时则另做恢复。保持真实计时和所有错误检查。
没有改UART FIFO深度、波特率、生产RTL、TB期望或缩短测试来绕过失败；完整分层重新验收修复后候选。
失败时的C源码、ELF/DAT/manifest、输入/原始捕获、日志/results固定保存在
sim/uart_loader/build/debug/rx_fixed_fifo_before_drain。原候选不作为成功部署镜像。

PC codec独立检查PASS：固定向量长度/CRC、ACK64、拒绝损坏响应CRC/SEQ/CMD，
并重新解析原阶段①两轮归档，保持兼容。CLI help包含ping/rx-test；本轮未打开串口。

## 实板下一步与限制

全套仿真PASS后，用户用同一新ROM/RAM DAT分别生成两块IP，再生成并下载位流；当前PING旧位流
不会响应rx-test。关闭串口助手，KEY0复位并等待DDR初始化，再执行：

```powershell
C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/rx_fixed100.json rx-test
```

100次RX_TEST ACK并退出0后，再KEY0复位，换日志rx_fixed100_after_reset.json重复。
两轮均PASS才能推进DDR写入/读回阶段。新位流PING回归也须独立复位后另存日志。
本候选尚未实板验收，未覆盖随机压力测试、PHY重新训练验证、DDR CRC、DDR取指或程序下载；
原DDR基础验证继续保留原证据范围。本轮只完成受控接收候选与其分层验收。
