# UART Loader阶段①：ROM驻留与PING

日期：2026-10-07，Asia/Shanghai。

## 后续实板结果：复位前后各100次PING PASS

用户上板后以COM11执行100次PING，粘贴输出PING1–100均ACK。
读取本机sim/uart_loader/board/ping100.json，逐帧核对100个请求与协议编码一致，
应答SEQ连续1–100、Header/Payload CRC正确、status=ACK，往返9.760–10.563ms。
首轮原始JSON（含逐帧tx_hex/rx_hex）固定归档为sim/uart_loader/board/ping100_first.json，
SHA256=1595057243e7ed1413fe4e7a047f186575d4dee5c74f78f3e457ee49dc0c9282。
粘贴附件初次已读，随后附件路径不可用；未复制该文本，原始字节证据以归档JSON为准。

当前两个IDF的INIT_FILE分别指向loader_rom.dat与loader_ram.dat，两DAT哈希与下方验收身份一致。
用户安装pyserial3.5；串口枚举确认COM11为CH340，COM5为蓝牙。此前打开端口报错发生在PC侧，
不作为本轮FPGA协议失败。未采集位流文件身份，未独立操作串口或生成/下载位流。

用户随后确认复位后100次通过。独立读取ping100_after_reset.json，100个请求编码与SEQ1–100、
响应Header/Payload CRC、ACK状态再次全部PASS，往返9.758–10.665ms。
复位操作本身依据用户确认，未独立观察按钮。固定归档ping100_after_reset_verified.json，
SHA256=f49444d2bbebc409c54faa8023ffac5115bb989f88c015afcdbd6245eb6804d0。
机器汇总见sim/uart_loader/board/ping_stage1_board_result.json。

阶段①实板PASS：首轮与复位后共200次有效PING。下一步唯一动作变为阶段②固定小数据接收测试，
先核CPU轮询FIFO收到的字节，再逐层接DDR写入与读回；本轮没有继续编码或修改验收DAT。
未覆盖断电重上电、高速UART、LOAD/VERIFY/RUN，未采集下载位流哈希。此前记录为历史快照：

## 本轮授权与实现

依据用户“根据相关文件，执行”，执行上一轮唯一下一步：独立最小ROM常驻候选，先核RAM常量、
BSS、片内栈和重复复位，再PING/ACK。没有扩展到LOAD、VERIFY、RUN、DDR CRC读回、Hello或上板。

新增`tests/uart_loader`的C/头文件、startup、linker、构建和Harvard ELF审查/镜像提取；
新增`sim/uart_loader`的真实CPU TB、独立同步BRAM模型与分层runner；
新增`tools/uart_loader`的Python二进制协议与仅PING CLI，及各README。
AGENTS只补长期入口约定，保留已有CoreMark/用户工程改动。

代码驻留指令ROM0x00000000；数据常量驻留RAM0x00000100；BSS0x00001000；接收缓冲0x00002000；
初始sp0x00003FF0向下，栈底0x00003000；旧manifest末16字节保留。
ROM/RAM同址但不同总线，使用分区ASSERT、独立PHDR和`--no-check-sections`明确允许Harvard重叠，
逐section提取两份4096字DAT；不能将重叠ELF合成单BIN用于部署。

构建使用GCC15.2.0，C/libgcc严格RV32I/ILP32、-Os、no-relax；startup局部`.option arch,+zicsr`
只允许当前CPU实际已有的CSR指令。关闭mie/MIE，设置ROM fatal trap入口，清BSS再main。
禁止非零可变.data，避免误以为KEY0会重载RAM初始化。main实际读取RAM常量，计算标准CRC向量；
UART禁RX IRQ、清错、轮询FIFO。没有FENCE.I、DMA、Cache或新RTL。

PING为36-byte RVLD请求，60-byte响应，Header与payloadCRC均为CRC-32/ISO-HDLC。
有效PINGACK对应SEQ；重复最近PINGACK但计数不增加；更小序号拒绝。capabilities=3只表示CRC和
ROM驻留，状态/accepted_bytes/DDR_crc全0，不声明下载或执行能力。LOAD/VERIFY/RUN明确COMMAND_ERROR。
100ms收帧超时/坏帧连续空闲恢复已写入，但全部异常/边界包验收属于后续阶段⑧，不宣称已覆盖。

## 复现入口

```powershell
Set-Location D:/riscv/RISCV
& ./tests/uart_loader/build.ps1
# runner仅读已有同一候选，不重建或转换DAT
& C:/python/python.exe sim/uart_loader/run.py
```

默认依次执行residency→ping，前一级FAIL即停止；默认PING_COUNT=100。
`--residency-only`仅前置，`--ping-count 2..200`是诊断选项，不替代100次标准。
本轮默认sandbox执行启动失败（helper_unknown_error），经许可在可启动的环境执行构建/ModelSim；
这不是工程RTL FAIL。

## 最终结果：ROM驻留前置与阶段①仿真PASS

构建PASS：ROM.text=1876 bytes（0x00000000–0x00000753），RAM.rodata=32 bytes
（0x00000100–0x0000011F），BSS=76 bytes（0x1000–0x104B），RX buffer=256 bytes，
诊断16 bytes。469条最终机器码通过CPU指令白名单。ELF32小端EXEC、入口0、rv32i2p1、
16-byte stack alignment，无M/C/F/非法FENCE.I；没有未解析符号。size汇总bss=348包含76状态+256缓冲+16诊断。

候选镜像SHA-256：

| 文件 | SHA-256 |
| --- | --- |
| loader.elf | 41fb5524c4c8e229b6975505bac1fd0bab2834402e4106d83e6d3db7dc43d788 |
| loader_rom.dat | 6898daf5217fcef9c851989f8abe5f6cdca2b59dcb157a3f010373f3dce49fbb |
| loader_ram.dat | 5c6373da7f8c9afb3d4edffbb2343ce1b259df9beedfe2a319b86639b30bbfe8 |

residency实测PASS：3次SoC复位，每次19笔BSS清零，main前全0；boot时至少13笔RAM常量读；
常量XOR929A5E56、CRC123456789=CBF43926、空CRC0；初始sp3FF0，最低sp3F60，使用144/4080 bytes。
低RAM/诊断边界/栈底64 bytes/旧manifest哨兵未改，UART RX IRQ与CPU MIE保持关闭。
没有UART发送或DDR请求，2727条退休、4028个运行周期。编译/运行Errors0/Warnings0。
原始证据：`sim/uart_loader/build/residency/modelsim.log`。

PING完整验收PASS：100个有效PING、1个重复PING、3个不支持命令（LOAD/VERIFY/RUN），
分两次启动各50个有效PING；重复请求不重复计数，三个未开放命令均返回COMMAND_ERROR=0x8007。
复位后重新从SEQ1通信。3744字节RX、FIFO pop、MMIO响应、CPU两处RX LBU退休完全一致；
6240字节TX接受值与引脚独立解码完全一致，全部原始捕获逐字节匹配Python/zlib基准，CRC/SEQ正确。
FIFO峰值4/16字节，最低sp3F60，栈使用144/4080 bytes；无UART错误、CPU trap/IRQ、
总线error、越界写或DDR请求。41402158条退休、109850838个运行周期。
编译/运行Errors0/Warnings0，进程退出0；PING仿真墙钟1863.29秒（约31分钟）。

最终`sim/uart_loader/build/results.json`记录status=PING_STAGE_PASS、
protected_unchanged=true、image_unchanged=true、board_result=NOT_TESTED。
同一候选身份绑定`sim/uart_loader/build/validated_image.json`；本轮验收后未重新构建DAT。
原始证据在ping/modelsim.log、compile.log、uart_rx.bin、uart_tx.bin及decoded_responses.json。
这是阶段①仿真PASS；不是阶段②固定数据下载、实板PING或最终Loader验收。

## 检查器修正记录

首次构建遇GCC15 RV32I汇编默认不接受CSR助记符，已用局部Zicsr汇编选项明确CPU已有能力，
保持C/libgcc ISA不变。首次仿真SP检查误把`la sp`的AUIPC中间值当最终SP，
修正为标记后的ADDI写回检查；只有两步初始化完成才检查栈范围/对齐。
该失败日志保留在`sim/uart_loader/build/debug/residency_sp_checker_failure.log`。

另一轮TB等待函数内RAM状态没有完成唤醒，已停止该仿真，改为逐时钟读取并加40000周期启动上限；
随后3次复位通过。停止记录保留在debug/residency_wait_function_interrupted.log。
未通过放宽CPU/内存期望制造PASS，未修改生产CPU/总线/UART RTL。

## 产物、保护与未覆盖范围

候选ELF/MAP/DIS/符号/stack usage/DAT/manifest在tests/uart_loader/build；TB/模型/runner、
编译运行日志、输入bin/hex、原始UART捕获、JSON、独立库在sim/uart_loader/build。
runner记录全部验收输入SHA-256，并保护当前生产RTL、PDS/FDC、ROM/RAM/DDR IP与初始化内容、
旧boot镜像、成功Echo/输出30/CoreMark基准；验收前后候选DAT也须一致。

本轮没有操作主IP、PDS生成或下载、串口、电气或实板；当前data_ram仍为CoreMark validation_60。
本测试DDR启用，但所有DDR请求立刻FAIL；无DDR用户口模型预灌内容，更不含PHY训练。
SoC复位不等同真实KEY0消抖/DDR再训练验收。完整DDR物理模型历史PASS继续按原范围保留，
未改共享RTL故本阶段不重复数小时回归。

PC CLI帮助已检查，pyserial未安装，未打开COM口。它从SEQ1开始，实板使用前需复位Loader；
实板依赖安装与候选Loader部署不属于本轮已完成动作。新文件/部分文档与构建产物按现有规则可能被忽略，
没有改.gitignore、提交或推送。

## 推荐下一步唯一动作

用本次已验收的loader_rom.dat与loader_ram.dat进行一次最小Loader实板部署与PING验收。
部署需明确同时切换ROM代码与RAM常量，重新生成两块IP/位流并记录身份；
先完成训练后PING、100次ACK、KEY0复位后重新PING并保存原始串口记录。
本轮没有执行这些生产配置/上板动作；实板PING未PASS前不推进固定数据下载或完整LOAD/RUN。
