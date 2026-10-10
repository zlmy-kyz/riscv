# UART Loader DDR读回CRC32：阶段⑦

日期2026-10-08。前置：固定64-byte CPU写DDR→读回→比较实板两轮各100次ACK，
机器凭据sim/uart_loader/board/ddr_fixed_stage3_board_result.json为PASS且两归档hash正确。
本步只新增只读CRC诊断，不实现任意BIN下载、正式VERIFY3、RUN4、DDR取指或DMA。
构建/审查、三次ROM启动及完整21帧联仿PASS；后续实板两轮各100次CRC32 PASS也已独立核验。

## 真实地址与行为

沿用soc_top两路译码真实DDR窗口0x40000000–0x5FFFFFFF，唯一允许校验区域
0x40000000–0x4000003F（64字节）。新CMD0x12 DDR_CRC_TEST先检查包、地址、长度、SEQ，
然后16次volatile 32-bit LW，按小端拆成64字节保存数据RAM的0x2080–0x20BF，
用已有loader_crc32计算实际读回CRC。CRC源是这16笔DDR读取；不是RX buffer或固定常量。
CPU仍执行指令ROM0..0x3FFF，常量/data分挂数据RAM；栈sp0x3FF0向下、底0x3000。
新候选.text2920/rodata48/BSS128字节，BSS为0x1000–0x107F；缓冲仍0x2000–0x20FF。
桥用户口128-bit、16-bit字地址、单事务，与既有DDR阶段相同；不改RTL/IP/PDS。

CRC32使用CRC-32/ISO-HDLC（反射多项式EDB88320，初值FFFFFFFF，末尾取反），
标准向量123456789=CBF43926，空数据0，固定64字节向量23C3E508。
PC CRC相等才ACK64；不等NACK CRC_ERROR8001，响应携带实际DDR CRC，失败不推进成功SEQ。
未写过的DDR也按实际内容计算，不假定复位清空或预置数据；SoC复位不重新初始化模型DDR。
重复同SEQ同CMD同expected CRC仍重新读DDR并计算，不重复计唯一成功次数。
同SEQ更换expected CRC拒绝8009且不读DDR；失败后原SEQ可在修复DDR/预期值后重试。
只有CRC计算完成的请求返回实际CRC；非法包/PING/RX_TEST/DDR_TEST响应该字段0，避免旧值泄漏。
现有DDR_TEST0x11仍仅写入固定64-byte、读回比较，响应DDRCRC0且保持原协议。

## 协议与PC命令

Header仍32字节、小端：RVLD、VERSION1、CMD0x12、flags0、SEQ、ADDRESS40000000、
LENGTH64、TOTAL0、IMAGE_CRC（PC提供的期望CRC）、前28字节Header CRC。
CMD0x12的LENGTH表示DDR校验范围，不是UART DATA长度；DATA为空，尾部DATA CRC0，
所以校验请求36字节，无程序回传。响应60字节、CMD0x80、LENGTH24，payload六个u32：
status、request_cmd、accepted_bytes、actual_ddr_crc、capabilities3、max_chunk256。
ACK accepted64，NACK accepted0；基址40000000，名义maximum61440仍不表示支持下载。
包CRC错误与DDR CRC不等都用8001，区分依据是否实际访问DDR及响应actual CRC。
保留地址8002、长度8003、TIMEOUT8004、UART_ERROR8005、命令8007、SEQ8009等拒绝路径。
桥本身没有watchdog；DDR完全停滞时CPU等响应，PC超时，不宣称必能返回TIMEOUT。

PC工具新增ddr-crc-test，每个测试按以下顺序停等：

1. DDR_TEST（SEQ2n-1）发送固定64字节，等写/读/比较ACK。
2. DDR_CRC_TEST（SEQ2n）只发PC CRC，等CRC结果并核对ACK实际CRC。

--count100为100次CRC测试，包含100次写比较和100次只读CRC，共200个响应。
日志200条，test_number1..100，每组operation=DDR_WRITE_COMPARE/DDR_CRC；PC/DDR CRC、
原始tx/rx hex、状态、SEQ、往返耗时保存。任何NACK/超时/包CRC/字段或ACK DDR CRC不符即停止，
无自动重试或RUN；新命令从SEQ1开始，每轮必须先KEY0复位并等待DDR初始化。
CRC_ERROR实际不等输出PC/DDR CRC以便判断；PC拒绝包CRC有效但DDR CRC错误的伪ACK。

## 改动与镜像

阶段③代码、build、TB/runner和PC工具先保存到各verified/ddr_fixed_stage3与
sim/uart_loader/build/ddr_fixed_stage3_sources。旧build/ddr_fixed不改、不覆盖；
build.ps1默认独立build/ddr_crc且禁止输出到三份实板成功目录。
生产IP继续保留用户部署的ddr_fixed路径，仿真不自动切换。

修改tests/uart_loader/uart_loader.c/.h、ddr_test.c/.h、build.ps1、image_to_dat.py，
tools/uart_loader/loader.py/protocol.py，sim/uart_loader/run.py/tb/tb_uart_loader.v；
DDR模型复用已有延迟/即时响应和物理字节损坏功能。文档/README/HANDOFF记录验收范围。
CPU、总线、UART、桥、DDR顶层均不改；无需因软件诊断变动重跑未受影响的完整PHY回归。
新镜像730条机器码通过RV32I/ILP32审查；startup局部CSR许可保持原样，无M/C/FENCE.I。

- ELF49744ef735f2c14461594969004641f318f62991589aadf2209f9e15cf6de178
- ROM21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a
- RAM59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a

```powershell
cd D:/riscv/RISCV
& ./tests/uart_loader/build.ps1
& C:/python/python.exe sim/uart_loader/run.py --stage ddr-crc
```

runner只读已有DAT/ELF；先核前级实板证据→三次ROM复位→21帧/两次启动。任何前级失败即停。
生产RTL/IP/PDS、旧镜像/前级实板证据与新候选前后hash保护；验收后不重新生成DAT。

## PASS/FAIL和产物

|阶段/输入|PASS|FAIL|产物|
|---|---|---|---|
|前置实板门控、ROM三次启动|前级PASS/证据hash正确，BSS毒化后全清零、栈/常量/CRC向量正确|证据不符、启动/ISA/边界异常|residency日志、image manifest/receipt|
|未写DDR（模型A5）先CRC|读16笔实际A5，CRC不等NACK，返回真实CRC|误ACK、CRC来自RX或假数据|CPU CRC诊断、LW退休与Pango AR轨迹|
|写PASS后CRC与重复校验|PC=DDR=23C3E508，ACK64；重复请求又读16次|未重新读、值不符仍ACK、计数错误|UART原始bin/decoded JSON、crc_state|
|改物理DDR字节26后两次CRC|均NACK8001，返回损坏CRC，CRC命令0次SW，不修复内存|错误ACK、CRC请求偷偷重写、读回失真|CRC_LW_RETIRE、DDR物理CRC与Python基准|
|DDR_TEST重写修复、错误PC CRC再正确重试|错误预期NACK但返回正确DDR CRC，同SEQ正确重试ACK|用PC提供值冒充实际DDR CRC、失败推进SEQ|case/expected_response、状态诊断|
|同SEQ换预期/坏包CRC/错地址/65字节/RUN|对应NACK且0 DDR请求，坏包空闲恢复无FIFO错误|非法包读写DDR、溢出/陷阱|原始TX/RX、日志|
|复位后直接CRC，再写/CRC/RX/PING|清零软件状态，重新读仍保留的真实DDR；兼容旧命令|复位残留CRC、RAM旧结果冒充读取|第二次启动计数/诊断|
|实板两轮各100 CRC测试|每轮100 CRC32 PASS；日志SEQ1..200、各100写ACK和CRC ACK，PC=DDR|任一CRC/SEQ/字段/NACK/超时|两轮JSON、DAT与位流身份、复位说明|

联仿合计21帧：3PING、1RAM RX、3写比较、9次CRC读取（5成功含重复/4失配），
另外5次拒绝（SEQ换预期/坏空DATA CRC/地址/长度/RUN）。共48 SW、192 LW，
其中CRC单独144 LW，Pango AW/W48、AR192。UART请求1012字节、响应1260字节与Python/zlib基准逐字节比。
TB逐笔核32-bit槽位/用户半字地址/strobe，LW退休值和RAM readback须等于模型实际内容；
TB再独立对物理DDR计算CRC，与Python物理内容CRC和CPU结果同时核对。
模型64KiB初值A5、DDR保留跨SoC复位，诊断仅64字节，其他内存不变；不含PHY训练或实板电气。
停止/FAIL不生成成功receipt；要求退出0、Errors0、一个RESULT PASS、无FAIL、各计数与hash正确。

## 本次真实CPU联仿结果

sim/uart_loader/build/ddr_crc/results.json为DDR_CRC_STAGE_PASS，退出0。
residency三次复位PASS、2.06秒；ddr_crc两次启动/21帧PASS、992.76秒。
9次CRC读取144 LW，其中5个CRC ACK含重复、4个CRC失配NACK；3次DDR_TEST48 SW/48 LW。
共48 SW/192 LW、用户AW/W48、AR192；ddr_trace.csv有480行，含CRC_LW_RETIRE144、
普通LW_RETIRE48、SW_REQ48、AW48和AR192。没有CRC命令写DDR或DDR取指。
正常CRC23C3E508，初始A5 CRC74465CC5、损坏CRC AE4B18EA均NACK8001；
损坏后再次只读仍同样NACK，重写修复后CRC恢复。PC故意提供23C3E509时仍返回真实23C3E508且NACK，
同SEQ正确预期重试ACK；重复正常校验重新读取而唯一成功计数不重复增加。
五个拒绝路径对应NACK且零DDR请求，复位保留DDR内容/BSS清零/重新读CRC/旧命令兼容均通过。
RX/FIFO pop/MMIO/CPU LBU各1012字节、TX/引脚解码各1260，原始捕获与独立Python基准完全一致。
FIFO峰值1/16、最低sp3F40，动态栈176/4080字节；两个DDR函数静态栈0。
20540978退休、56212153周期；编译/运行Errors0、Warnings0，没有UART/CPU/总线错误。
protected_unchanged/image_unchanged=true，全部input_sha256最终复核一致；
21个共享myriscv文件与前阶段hash一致。未改生产IP/PDS，未重跑未受影响的完整DDR PHY回归。
validated_image.json绑定上述同一候选，验收后未重建DAT；该receipt仍board_result=NOT_TESTED。
模型不含PHY训练/实板电气，不能以本联仿作为阶段⑦实板PASS。

## PC工具离线检查

sim/uart_loader/build/ddr_crc/pc_tool_check.py使用独立struct/zlib伪串口服务端，
不使用pyserial后端、不打开COM端口。执行真实loader.main，校验--count100生成SEQ1..200、
100个旧写比较请求和100个36-byte CRC请求，模拟每次最多7字节的分段read。
核日志200条、test_number/operation正确及100条CRC32 PASS；另提供包CRC有效、
ACK状态却含错误DDR CRC的应答，工具必须ValueError拒绝。离线结果PASS，
产物build/ddr_crc/pc_tool/{results.json,normal.json,normal_stdout.txt}，不表示硬件PASS。

## 实板验收结果

用户提交COM11两轮，各100条DDR_CRC_TEST CRC32 PASS及100条DDR_TEST写比较ACK，无FAIL/NACK。
独立核验每份JSON200条SEQ1–200，奇数CMD0x11固定DATA64、偶数CMD0x12只读空DATA，
Header/data CRC、地址/长度/PC期望、响应status/accepted/命令/实际DDR CRC以及operation/test_number全部PASS。
CRC响应实际DDR CRC=PC CRC=23C3E508，旧写比较响应该字段0。两轮总400 ACK、200个CRC结果。
复位按要求提交的after_reset轮及SEQ重启记录，未独立观察物理按钮，未采集下载位流身份。
当前两块IDF已由用户引用ddr_crc的DAT；ELF/DAT和仿真全部输入hash仍一致，验收后未重建。

|固定产物（sim/uart_loader/board）|SHA256|结果|
|---|---|---|
|ddr_crc100_first_verified.json|87b4dd7c284083a578a848a10fe8d07827f3a71c653a2cfce993910797a39c26|200ACK/100 CRC32 PASS|
|ddr_crc100_after_reset_verified.json|2661f01148a5772d1750bc2d76d45ede2e1b3df08ef7ac428d2437b5fa62974b|200ACK/100 CRC32 PASS|
|ddr_crc100_console_verified.txt|0b58b955f825523b98d85f3a08a4f300c08a600602ddbe2f7a2f34087bd3045f|两轮提交输出400ACK无失败|

机器结果ddr_crc100_first_result.json、ddr_crc100_after_reset_result.json、ddr_crc_stage7_board_result.json，
总board_result=PASS。复现核验脚本sim/uart_loader/build/check_ddr_crc_board_2026-10-08.py不打开串口，
用独立标准库struct/zlib解析原始报文；再次运行只允许相同证据，避免覆盖归档。
首轮写比较RTT15.411–16.041ms、CRC9.843–10.501ms；第二轮写15.396–16.005ms、CRC9.847–10.182ms。
总27200请求/24000响应字节、12800写payload字节，只反复同一64-byte区域，不是大文件或随机数据覆盖。
本轮只核验与归档、更新文档，没有RTL/C/工具修改、串口操作或位流生成/下载。
实板故障/非法包/超时/UART错误等负例尚未完成；仿真负例PASS不能替代实板异常路径验收。
下一步唯一动作：阶段⑧ACK/NACK异常路径专项验收，通过后才进入⑨随机二进制压力。
仍无任意BIN下载、正式VERIFY3、RUN4或下载程序DDR取指，本轮不开始编码后续功能。

## 实板验收命令记录

同时使用tests/uart_loader/build/ddr_crc下loader_rom.dat与loader_ram.dat生成IP/位流并上板。
用同一验收DAT，不重新构建；关闭串口助手。KEY0复位、等待DDR初始化后执行：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_crc100.json ddr-crc-test
# KEY0复位并等待初始化后，再执行：
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/ddr_crc100_after_reset.json ddr-crc-test
```

预期每轮100条CRC32 PASS，PC CRC=DDR CRC=0x23C3E508。新日志包含200个请求/应答。
当时要求实板两轮PASS前不继续随机二进制压力/任意BIN/VERIFY/RUN；后续两轮结果见上方。
