# ROM常驻UART Loader：阶段⑦DDR读回CRC32实板PASS

2026-10-09最新：VERIFY/RUN/DDR/Hello合并实板157/157响应PASS，DDR CRC32 5E142E06，唯一RUN后精确Hello；零CRC错误/重试/额外RX，独立核验和170项成功快照归档完成。第②关完成，下一步第③关同位流复位/第二BIN/CoreMark。成功Loader、应用和位流不重建；用户负责实板操作。见[实板验收](../../doc/uart_loader/UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md)。

下方保留集中仿真及准备阶段历史。

2026-10-09最新：VERIFY/RUN/DDR执行/Hello已合并开发，五组集中仿真和14项PC离线检查PASS，冻结门控COMBINED_SIM_PASS；隔离位流与时序/初始化审计PASS，JTAG仍未发现FPGA，实板待验。新候选verify_run_hello及其PDS/IP均隔离，原成功镜像保留。见[合并验收](../../doc/uart_loader/UART_Loader_VERIFY_RUN_DDR_Hello合并验收_2026-10-09.md)。本轮用户自行完成下载、供电/JTAG、复位和串口测试，Codex提供步骤并核验日志。

下方保留此前阶段⑩及更早记录，历史“尚未实现/用户操作”对应其记录时间。

2026-10-09最新：阶段⑩真实program.bin正式LOAD两轮各8响应实板PASS，DDR读回CRC32 B2E24920，零错误/重试；独立原始日志核验和成功配置归档完成。状态仍为LOADED_UNVERIFIED，正式VERIFY/RUN/执行尚未实现。精简计划第①关完成，下一步新隔离候选合并开发第②关VERIFY/RUN/DDR执行/Hello。保留当前load_stage10成功DAT/BIN及所有旧档案，上板/复位/串口由用户负责。见[实板验收](../../doc/uart_loader/UART_Loader真实程序LOAD两轮实板验收_2026-10-09.md)。

阶段⑨两轮各1000镜像实板PASS，固定证据和成功镜像继续保留。

## 历史准备与验收记录

下方“当前/下一步”按记录时点保留，最新状态以上述阶段⑩实板结论为准。

2026-10-09最新：阶段⑧完整约定异常矩阵已在隔离uart_fault_stage8_diag两轮实板PASS，每轮117项（80ACK/37预期NACK/40实际DDR CRC ACK）；帧错返回真实状态0x10，FIFO溢出返回0x20，随后PING/DDR CRC恢复全部通过。原始帧与终端输出已独立核验，汇总为sim/uart_loader/board/uart_fault_stage8_diag_board_result.json。当前IP由用户指向诊断候选DAT，阶段⑦成功镜像及旧证据保留；⑨尚未启动，正式LOAD/VERIFY/RUN未实现。详见[两轮实板验收](../../doc/uart_loader/UART_Loader_UART帧错与FIFO溢出两轮实板验收_2026-10-09.md)。下方保留此前准备/验收记录。

2026-10-09当前继续阶段⑧UART帧错/FIFO溢出实板验收：隔离uart_fault_stage8_diag诊断候选的原速线级9响应、108帧host回归及PC/核验器离线检查全部PASS，部署门控已冻结66项输入副本；新实板仍NOT_TESTED。该候选上报真实STATUS0x10/0x20，原成功C/RTL/IP/DAT不改。下一步由用户生成下载诊断位流，KEY0后运行专用acceptance.py --mode all两轮。详见[候选身份、DAT及操作说明](../../doc/uart_loader/UART_Loader_UART帧错与FIFO溢出实板注入准备_2026-10-09.md)。

2026-10-08最新：阶段⑧主机可注入ACK/NACK异常实板两轮PASS；每轮108帧、73ACK/35个预期NACK、37个DDR CRC ACK，独立原始帧核验及终端对照通过。现行PC工具为tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py；当前汇总sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json为PASS_HOST_INJECTABLE_ONLY。UART帧错/FIFO溢出实板仍NOT_TESTED，完整实板范围NOT_COMPLETE；⑨本轮未启动。成功ELF/DAT/C/RTL/IP不改，原第95帧PC误报FAIL保留。见[两轮验收记录](../../doc/uart_loader/UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。所有上板/复位/串口操作继续由用户负责。

以下为阶段⑧实板提交前的仿真与准备记录；最新板级结果以顶部为准，旧工具仅保留复现历史误报。

2026-10-08新增：阶段⑧ACK/NACK专项仿真PASS，实板待验。完整114帧/37负例修复检查器后从头重跑PASS，另有原速超时与UART故障各8帧PASS；生产C/RTL/IP及成功DAT不改。见[阶段⑧记录](../../doc/uart_loader/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。独立仿真入口sim/uart_loader/stage8/run_repaired.py；成功机器门控sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json。PC实板专项工具tools/uart_loader/candidates/ack_nack_stage8/acceptance.py为108帧/35负例。先恢复已有阶段⑦成功位流、KEY0复位并等DDR初始化，串口助手保持关闭；本轮未打开COM11。下方阶段⑦成功记录和旧入口继续保留，不能用旧runner冒充阶段⑧验收。

换对话先读 [交接入口](../../doc/uart_loader/UART_Loader换对话交接_2026-10-08.md)。当前两IP引用build/ddr_crc，阶段⑦源码和完整构建已保存verified/ddr_crc_stage7；复制哈希见sim/uart_loader/build/ddr_crc_stage7_sources/archive_receipt.json。阶段⑧主机可注入部分现已两轮实板验收；完整实板范围仍保留UART帧错/溢出缺项。

**不要运行无参数build.ps1：默认输出build/ddr_crc，尚未保护这份新实板成功目录。** 后续候选须显式指定隔离-OutputDirectory；保留已验收同一DAT。本页下方旧阶段构建命令/默认目录仅为历史，不能按旧命令重建后直接上板。

2026-10-08：固定DDR写读比较阶段实板两轮各100次ACK已PASS。
新候选CMD0x12 DDR_CRC_TEST只读0x40000000起64字节，16次LW后计算实际读回CRC32，
与PC提供IMAGE_CRC比较并返回actual_ddr_crc。相等才ACK64，失配8001，重复校验重新读取。
构建默认build/ddr_crc，保护build/根、rx_fixed和ddr_fixed；阶段③快照verified/ddr_fixed_stage3。
旧DDR_TEST行为兼容；不支持任意program.bin、正式VERIFY/RUN或DDR取指。

```powershell
& C:/python/python.exe sim/uart_loader/run.py --stage ddr-crc
```

新镜像.text2920/常量48/BSS128、730条RV32I指令审查、三次ROM启动和21帧CRC联仿PASS；
CRC144笔真实LW，损坏/错误预期NACK、重复重读和复位恢复通过。
后续实板两轮各100 CRC32 PASS独立核验通过（总400 ACK）；当前两IP已由用户指向ddr_crc。
机器证据sim/uart_loader/board/ddr_crc_stage7_board_result.json，异常路径实板验收待后续阶段⑧。
上板同时部署build/ddr_crc的ROM/RAM两DAT，不重新构建已验收DAT。
详见doc/uart_loader/UART_Loader_DDR读回CRC32阶段7_2026-10-08.md和CODEX_HANDOFF。

## 固定DDR写读比较阶段历史

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
