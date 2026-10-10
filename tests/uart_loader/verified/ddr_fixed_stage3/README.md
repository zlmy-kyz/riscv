# ROM常驻UART Loader：固定数据DDR写读比较候选

2026-10-08：阶段②/③已完成实板复位前后各100次ACK。当前候选新增CMD0x11 DDR_TEST，
固定64字节写入0x40000000–0x4000003F，16次SW后16次LW读回逐字节比较；通过才ACK64。
不支持任意BIN、LOAD/VERIFY/RUN或DDR取指。当前构建默认build/ddr_fixed，禁止覆盖
已验收build/根与build/rx_fixed镜像；阶段②源码/build快照在verified/rx_fixed_stage2。
仿真开发时保留阶段②IP引用，仿真不自动部署；后续用户已切换至ddr_fixed，见下方实板结果。

```powershell
& ./tests/uart_loader/build.ps1
& C:/python/python.exe sim/uart_loader/run.py --stage ddr-fixed
```

仿真通过后同时部署build/ddr_fixed/loader_rom.dat与loader_ram.dat；必须使用验收过的同一DAT。
本候选三次ROM启动、17帧/两次启动联仿PASS（80 SW/80 LW、损坏NACK、复位恢复）；
实板首轮和更新的after_reset轮各100 ACK独立核验PASS。最初第二次尝试8009为序号错误，
未计入成功，来源记录保留；当前用户两IP已指向ddr_fixed，详细证据见CODEX_HANDOFF。
详细阶段门控、失败注入与上板方法见doc/uart_loader/UART_Loader固定数据DDR写读比较阶段4至6_2026-10-08.md。
以下保留阶段②和阶段①历史记录；旧构建默认目录描述仅对应当时。

## 阶段②固定接收历史

阶段①已完成实板复位前后各100次PING。当前新增受控诊断CMD0x10 RX_TEST：
CPU轮询FIFO，将64-byte固定向量存入片内RAM，校CRC并逐字节比较后ACK；不写DDR或执行。
新构建默认输出build/rx_fixed/，禁止覆盖build/根的实板PING镜像，生产IP仍引用原build/根。
修改前的源码/build在verified/ping_stage1/。完整实现、判据和状态见
doc/uart_loader/UART_Loader固定小数据接收阶段2_2026-10-07.md与doc/CODEX_HANDOFF.md。

```powershell
& ./tests/uart_loader/build.ps1
& C:/python/python.exe sim/uart_loader/run.py --stage rx-fixed
```

候选通过后，必须同时用build/rx_fixed/loader_rom.dat与loader_ram.dat重新生成IP和位流。
这一步不自动执行；旧PING位流会拒绝rx-test。上板使用同一验收DAT，不重新构建。

下方为阶段①结构与历史说明，分区/ISA约束继续适用；原镜像保留原样。

本目录是独立软件实验。实现ROM常驻启动、片内RAM常量/BSS/栈、轮询UART和二进制PING/ACK。
LOAD、VERIFY、RUN均返回COMMAND_ERROR，未实现DDR下载或执行；仿真结论及精确镜像身份见
`sim/uart_loader/build/results.json`。没有切换主ROM/RAM IP，没有PDS实现或实板验收。

## 地址与构建

- 代码 `.text`：指令ROM `0x00000000` 起，16KiB范围。
- 常量 `.rodata`：数据RAM `0x00000100` 起，限于 `0x00000FFF`。
- BSS：数据RAM `0x00001000` 起，限于 `0x00001FFF`。
- 256-byte接收缓冲：数据RAM `0x00002000` 起。
- 栈：`0x00003000–0x00003FEF`，sp=`0x00003FF0`，向下增长；末16字节保留。
- 诊断4字：数据RAM `0x20/24/28/2C`，分别为常量XOR、CRC检查向量、空数据CRC、boot error。

指令ROM与数据RAM同VMA、不同总线。链接刻意使用 `--no-check-sections` 允许Harvard重叠，
各分区仍有链接ASSERT和ELF检查。`image_to_dat.py`独立提取 `.text` 与 `.rodata`，
不把整个ELF转换成一个BIN。两份DAT均为4096×32-bit HEX，小端每字。
可变非零 `.data` 被禁止；BSS每次复位清零，RAM模型不会在复位时重新加载DAT。

```powershell
Set-Location D:/riscv/RISCV
# 当前构建默认生成阶段②，重查原阶段①镜像使用：
& C:/python/python.exe sim/uart_loader/run.py --stage ping
```

构建输出仅在本目录build：loader.elf/map/dis/readelf、symbols、stack usage、ROM/RAM DAT及manifest。
使用 `-march=rv32i -mabi=ilp32 -Os`、no-relax、freestanding和匹配libgcc。
GCC15将CSR归入Zicsr，startup仅在汇编局部用 `.option arch,+zicsr` 允许CPU已有的CSR指令，
不改变C/libgcc的RV32I参数；最终每条机器码另行审查。没有FENCE.I或M/C/F等指令。

startup设置gp/sp，关闭CPU中断、设置ROM fatal trap入口、清BSS后main。
main实际通过数据总线读取常量，检查CRC32 `123456789=CBF43926` 和空串0，
设置BSS探针、禁UART RX IRQ并清错误，再进入PING轮询。boot error非零时停机，不发ACK。

## PING行为

沿用 `doc/uart_loader/UART程序下载Loader调查与方案_2026-10-07.md` 的32-byte RVLD Header，
PING为CMD1、flags/address/length/total/image_crc均0，尾部空DATA CRC=0。
Header CRC为前28字节CRC-32/ISO-HDLC。响应60字节，CMD=0x80，payload为6个u32：
`status, request_cmd, accepted_bytes, actual_ddr_crc, capabilities, max_chunk`。

有效PING返回ACK、对应SEQ、base=0x40000000、名义容量61440、max_chunk=256；
accepted/DDRCRC/state为0，capabilities=3仅表示CRC与ROM驻留。容量信息是未来布局，
不能据此认为当前支持LOAD或RUN。递增SEQ计数一次；同一最近PING序号重复ACK但不再计数；
更小SEQ拒绝。更换PC进程从SEQ1开始前需要复位，或沿用已有下一SEQ。

协议错误有明确NACK；收帧有100ms字节间超时，坏帧后等待100ms连续空闲恢复。
最小阶段未完成所有负例验收，不能沿用为阶段⑧全协议PASS。LOAD/VERIFY/RUN不会写DDR或跳转。
主板DDR训练完成前CPU仍处于复位，无法PING；本sim测试从SoC释放复位开始，不含PHY训练。

## 实板边界

本阶段仅软件候选/真实CPU仿真；候选DAT不可直接代替当前CoreMark RAM payload DAT，
也不能继续使用旧24字ROM搬运程序。未来部署需同时选固定loader_rom.dat与loader_ram.dat，
核对生成内容、Full Boot凭据和位流身份。未经这一部署步骤，现FPGA不会因新增本目录自动响应PING。
验收后不重新构建另一套DAT直接部署。成功Echo/CoreMark镜像继续保留原样。
