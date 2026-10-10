# UART Loader：CPU写DDR、读回、固定数据比较

日期：2026-10-08。前置：PING与固定接收均实板复位前后各100次PASS，证据在
sim/uart_loader/board/ping_stage1_board_result.json、rx_fixed_stage2_board_result.json。
本步只覆盖原计划④⑤⑥。仿真验收PASS，实板两轮各100次ACK也已独立核验PASS，结果见文末。

## 范围和实际地址

新增受控CMD0x11 DDR_TEST，固定64字节，不是任意文件LOAD。CPU从ROM继续执行，
16次对齐32-bit SW → 普通fence rw,rw → 16次LW → 将真实读回值保存RAM并比较。
正确才ACK64；比较失败NACK DDR_ERROR=0x800B，不更新成功计数/SEQ。
最近已成功的同SEQ同CMD重发复用ACK，不重复访问DDR；失败后的同SEQ允许重写。
不实现LOAD/VERIFY/RUN、不跳转、不DDR取指、没有DDR CRC或DMA。

|区域|地址|依据/用途|
|---|---|---|
|指令ROM|0x00000000–0x00003FFF|soc_top指令译码、linker.ld；Loader从0启动|
|数据RAM|0x00000000–0x00003FFF|独立数据总线；与ROM同地址、不同存储|
|常量|0x00000100–0x0000012F|本次ELF .rodata=48字节|
|BSS|0x00001000–0x00001067|本次ELF 104字节；每次启动清零|
|接收缓冲|0x00002000–0x000020FF|linker.ld；header+payload+CRC在前100字节|
|DDR读回缓冲|0x00002080–0x000020BF|同256字节缓冲内独立64字节|
|Loader栈|0x00003000–0x00003FEF|sp=0x00003FF0，向下增长；末16字节保留|
|UART寄存器|0x10001000–0x1000100F|uart_mmio，115200/8N1、16字节RX FIFO|
|DDR CPU窗口|0x40000000–0x5FFFFFFF|soc_top与两路互连，ENABLE_DDR=1|
|本诊断唯一DDR区域|0x40000000–0x4000003F|真实窗口起点64字节；其他地址一律拒绝|

桥一次一事务、数据优先，用户拍128-bit。CPU字地址[3:2]选择32-bit槽位，strobe=0xF
扩为对应16-bit槽位掩码；用户地址按16-bit字计，local字节地址右移1后低3位清零。
因此16次SW/LW访问四个16-byte拍，对应用户地址0、8、16、24各四次。
它没有标准AXI4的WVALID/B/RREADY，不改用标准AXI模型。桥没有超时监测；
硬件DDR完全不返回时CPU会等待，PC会超时，不能宣称CPU必能返回TIMEOUT。

## 协议

沿用RVLD 32字节Header：MAGIC RVLD、VERSION=1、CMD、flags(u16)、
SEQ/ADDRESS/LENGTH/TOTAL/IMAGE_CRC(u32)及前28字节CRC32；小端。
DDR_TEST要求ADDRESS=0x40000000、LENGTH=64、flags/TOTAL/IMAGE_CRC=0。
尾部DATA64与DATA CRC32。固定数据前16字节为
00 FF 55 AA 52 56 4C 44 0A 0D 80 7F FE 01 02 00，后48字节为(i*37+11)&255，i=16..63。
固定DATA CRC32=23C3E508。先验证Header、地址/长度、完整payload、包CRC、固定向量和SEQ，
再允许DDR写；CRC是UART包校验，DDR正确性本步使用逐字节比较。

应答沿用60字节CMD0x80，payload6个u32：status、request_cmd、accepted_bytes、
actual_ddr_crc、capabilities、max_chunk。DDR ACK accepted=64、NACK=0，DDRCRC仍0，
capabilities仍3、max_chunk=256、名义maximum_bin=61440（不是当前下载能力）。
PING/RX_TEST保持原格式。LOAD2、VERIFY3、RUN4仍COMMAND_ERROR=0x8007。
保留CRC_ERROR8001、ADDRESS_ERROR8002、LENGTH_ERROR8003、SEQ_ERROR8009、
固定向量错误800A；新增DDR_ERROR800B。坏包先排空、100ms连续空闲后NACK，防FIFO溢出。

## 改动与复现

- tests/uart_loader/ddr_test.c/.h：对齐写读及readback比较；uart_loader.c/.h：受控命令/诊断。
- tests/uart_loader/build.ps1、image_to_dat.py：独立build/ddr_fixed，审查真实SW/LW退休PC与ISA。
- tools/uart_loader/protocol.py、loader.py：ddr-test；仅固定测试数据，无任意文件或RUN入口。
- sim/uart_loader/run.py、tb/tb_uart_loader.v、tb/loader_ddr_model.v：17帧独立预期、真实CPU、
  DDR背压/即时与延迟返回、物理字节损坏、CPU/Pango事务检查和串口逐字节比较。
- 三处README与CODEX_HANDOFF记录状态；myriscv共享RTL、生产IP/PDS不修改。

修改前阶段②源码/build保存tests/uart_loader/verified/rx_fixed_stage2，TB/runner保存
sim/uart_loader/build/rx_fixed_stage2_sources，PC保存tools/uart_loader/verified/rx_fixed_stage2。
保留build/根阶段①及build/rx_fixed的ELF/DAT、实板证据；候选不得自动替换IP。

```powershell
cd D:/riscv/RISCV
& ./tests/uart_loader/build.ps1
& C:/python/python.exe sim/uart_loader/run.py --stage ddr-fixed
```

RV32I/ILP32、-Os、no-relax、freestanding，startup局部允许已实现CSR。
代码2624字节、常量48、BSS104、656条指令审查；无M/C/FENCE.I。ELF/DAT身份：

- ELF：56b67bb403daf1a15cfdfda1c6ac960792959bee6539328ddcdd06280f5ff0cf
- ROM：a24df3ee6ed1ca07b40bbb258fbfa9160ad2070be099d8e8bb2f795b3a04cae7
- RAM：59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a

## 分层PASS/FAIL与产物

|顺序|测试输入/方法|PASS|FAIL|保存|
|---|---|---|---|---|
|前置门控|核阶段②实板两轮及hash；3次复位、毒化BSS|证据PASS、启动清零、栈/常量正确、无DDR/UART|证据不符、启动/ISA/越界异常|residency日志、manifest、results|
|④CPU写DDR|正确100字节DDR_TEST帧|16笔对齐SW退休；真实DDR四拍等于UART64字节；槽位/掩码/用户地址正确|漏写、错值、错地址、错误strobe、包未收完就写|ddr_trace.csv、modelsim.log、原始RX|
|⑤DDR读回|写PASS后16次LW|16个CPU退休值逐笔等于真实DDR，RAM readback逐字节一致|写未PASS先读、少读、读错值/地址|LW退休记录、总计数|
|⑥固定比较|正常/重复/损坏/重试/复位|正常ACK64；重复不二次写读；损坏DDR字节26产生800B；同SEQ重写恢复ACK|损坏仍ACK、成功计数/SEQ错误、复位状态残留|应答bin、decoded JSON、case/ddr_state|
|拒绝路径|地址+1、坏CRC、错误向量、65字节、RUN|对应NACK且DDR请求0，FIFO无错误|非法包访问DDR、溢出/总线错误/陷阱|原始TX/RX、cases、日志|
|实板|COM11，复位前后各100次ddr-test|两轮各100ACK，CRC/SEQ/accepted64核对通过|任一NACK/超时/字段错误|两轮JSON、复位说明、DAT/位流身份|

仿真17帧分12+5两次启动：4PING、2RAM RX、4唯一成功DDR+1重复、1DDR损坏比较NACK、
4非法DDR包NACK及1RUN NACK；五次DDR尝试共80 SW/80 LW。每次都通过真实UART引脚
→FIFO→MMIO→CPU LBU→内存，禁止直接预填结果。DDR内存A5初始化且跨SoC复位保留，
首次写后才得到固定向量；全部其他64KiB模型地址维持A5。真实窗口512MiB不全覆盖。
运行门控还要求退出0、Errors0、一个RESULT PASS、无FAIL、原始UART TX/RX等于独立基准，
生产RTL/IP/旧镜像和本候选DAT在运行前后hash不变。停止/失败不新增成功receipt。
该模型不含PHY训练、物理引脚/信号完整性、PDS生成BRAM，仿真PASS不等于实板PASS。

## 本次实测结果

sim/uart_loader/build/ddr_fixed/results.json为FIXED_DDR_STAGE_PASS，退出0。
residency三次复位PASS，墙钟3.49秒；ddr_fixed两次启动/17帧PASS，墙钟1123.60秒。
80 SW/80 LW与用户AW/W/AR各80，四次唯一成功与一次损坏失败符合预期；重复包不增加事务。
物理DDR byte26损坏返回800B，重写恢复；非法地址/坏CRC/错向量/超长/RUN均对应NACK且无DDR请求。
RX引脚/FIFO pop/MMIO/CPU LBU各1381字节，TX MMIO/引脚解码各1020字节，逐字节匹配独立预期。
FIFO峰值1/16，最低sp=0x3F40、动态栈176/4080字节；DDR比较函数静态栈0字节。
24505631退休、66605160周期；编译/运行Errors0、Warnings0，无陷阱、UART错误或DDR取指。
ddr_trace.csv有320行真实请求/用户口/退休记录，原始TX/RX及decoded_responses均保存。
protected_unchanged/image_unchanged=true，所有input_sha256最终复核也一致；验收后未重建DAT。
共享RTL与前一阶段21个myriscv文件hash一致，本轮没有重跑完整PHY回归，没有主IP/PDS变更。
validated_image.json绑定该同一候选。仿真完成时receipt的board_result=NOT_TESTED，
该仿真记录本身不能认作实板DDR PASS；随后独立实板结果见下一节。

## 实板验收结果

用户提交首轮100 ACK，第二轮最初SEQ1返回8009（序号错误，非DDR比较800B）。
核验期间用户更新了after_reset日志，新文件两轮各100 ACK；原失败临时JSON已被重测覆盖，
提交附件仍保存该错误输出，源路径记录于board汇总。复位按所要求after_reset日志和
SEQ从1重启成功记录，未独立观察KEY0。没有把早先8009计为复位PASS。

独立struct/zlib核对两轮200帧全部请求编码、固定DATA、地址、SEQ及Header/DATA CRC，
所有响应status=0/accepted64/字段与CRC均PASS。两轮共12800字节固定payload，
20000请求字节、12000响应字节；不表示覆盖12800个不同DDR地址，仅反复同一64字节。
首轮RTT15.395–16.111ms，第二轮15.390–16.070ms。

- sim/uart_loader/board/ddr_fixed100_first_verified.json：
  4f753811e65ea711306a04938a14a33ead3473c9ff8b8d5424504f52166f59a8
- sim/uart_loader/board/ddr_fixed100_after_reset_verified.json：
  94876ca7bb2dd8a5ce2f29b0cbf026a324ecf22508eba8123456370506ef5a33
- ddr_fixed100_first_result.json、ddr_fixed100_after_reset_result.json与
  ddr_fixed_stage3_board_result.json：汇总board_result=PASS，保留最初SEQ_ERROR记录来源。

当前IP两份IDF已由用户指向ddr_fixed镜像；三份ELF/DAT均匹配validated_image的哈希。
本验收轮没有串口操作、IP/位流生成部署或重新构建DAT，下载位流文件身份未记录。
独立核验/归档脚本sim/uart_loader/build/check_ddr_board_2026-10-08.py只针对本次提交。
下一步唯一动作：阶段⑦DDR实际读回CRC32，与PC CRC比较；本轮未实现。

## 实板验收命令记录

候选仿真PASS后，同时用build/ddr_fixed/loader_rom.dat和loader_ram.dat生成IP/位流并上板；
验收后不重新构建DAT。关闭串口助手，KEY0复位并等待DDR初始化，执行：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_fixed100.json ddr-test
# KEY0复位、等待初始化，再执行：
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_fixed100_after_reset.json ddr-test
```

当时要求两轮实板PASS前不推进DDR CRC、随机二进制/下载或RUN；后续本次两轮结果见上方。
