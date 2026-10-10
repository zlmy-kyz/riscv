# UART Loader阶段⑨随机二进制与DDR读回CRC

日期：2026-10-09（Asia/Shanghai）。阶段⑨隔离random_stage9候选已两轮各1000镜像实板PASS；用户完成IP/PDS、位流下载、复位及COM11操作，Codex仅离线核验归档。原阶段⑦/⑧成功镜像和配置档案保留，当前主IP由用户切换到阶段⑨同一对DAT。

## 最新结果：阶段⑨随机二进制两轮实板PASS（2026-10-09）

用户完成COM11首轮及after_reset轮；Codex直接读取工程内原始JSON，独立逐帧核验请求、60-byte响应的全部字段/CRC、固定seed输入、镜像/PC工具/部署门控身份及完整数量。每轮1000镜像、17946响应、3700127有效文件字节，1000个整镜像DDR CRC ACK及999个尾哨兵CRC ACK全部通过，零CRC/UART错误、零重试。合计2000镜像、35892响应、7400254有效文件字节；两轮分别549.845/550.179秒，约6729.41/6725.32 B/s，SEQ均1–17946。

板级汇总 `sim/uart_loader/board/random_stage9_board_result.json` 为STAGE9_TWO_ROUND_DIAGNOSTIC_BOARD_PASS / PASS_RANDOM_DIAGNOSTIC_ONLY。两份固定原始日志副本及PDS/IP/当前sbit共10文件配置副本已新增保存；1186项冻结输入及副本、103项仿真证据、阶段⑦37项原始/副本和阶段⑧成功配置档案均未变。部署前286项保护文件中277项未变、9项变化均为用户本次PDS/ROM/RAM/位流部署文件；未覆盖旧成功档案。详见[两轮实板验收](UART_Loader随机二进制两轮实板验收_2026-10-09.md)。

当前两主IP INIT_FILE已由用户指向 `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat` 和同目录 `loader_ram.dat`。Loader从ROM驻留，RAM存放常量/状态/缓冲/栈；CMD13/14仅低60KiB诊断写/真实DDR CRC，不执行随机数据。满61440-byte文件没有实板栈探针，栈保护另有仿真证据；after_reset重新接受SEQ1已核实，KEY0和已下载位流文件身份未独立观察。部署门控的历史NOT_TESTED保持生成时状态，当前实板结论看新增板级汇总。

下一开发步骤为阶段⑩：新独立Hello ELF/BIN/manifest（含非空data/bss），正式LOAD完整END，每块ACK，最终LOADED_UNVERIFIED，持续在ROM、不得输出Hello或自动执行。VERIFY和RUN按后续阶段验收，当前均未实现；本轮只离线核验归档，未开始阶段⑩。成功DAT不重建，后续继续使用隔离候选；上板、复位和串口由用户操作。

## 本阶段范围

这是受限诊断收发压力验收，新增CMD13随机分块写和CMD14范围读回CRC；正式LOAD2、VERIFY3、RUN4仍拒绝。所有代码继续从ROM取指，没有随机字节执行、镜像加载完成状态、应用入口切换或自动跳转。不要将本阶段数据诊断当作正式program.bin下载执行。

DDR诊断窗口为 `[0x40000000,0x4000F000)`，最大61440字节；`0x4000F000–0x4000FFFF` 应用栈区不可写。当前ROM已为常驻Loader，不使用旧自检在DDR0x1000/0x2000的scratch；本阶段仅在该候选数据窗口操作。每次随机文件从0x40000000开始，可以覆盖原固定64字节测试内容；阶段⑦成功镜像本身不改。

| 字段 | CMD0x13随机写 | CMD0x14范围CRC |
| --- | --- | --- |
| ADDRESS | 低60KiB内块首地址，允许非对齐 | 低60KiB内读回首地址，允许非对齐 |
| LENGTH | 1..256，真实DATA长度 | 1..61440，DDR范围长度，UART DATA为空 |
| TOTAL / FLAGS | 必须0 | 必须0 |
| IMAGE_CRC | 必须0 | PC期望范围CRC |
| 实际操作 | 全包CRC及序号检查后，SB前缀/尾部、SW中部，fence，再真实DDR读回CRC | 仅真实DDR读取，分256字节scratch累计CRC，不重写DDR |
| ACK accepted_bytes | 本块LENGTH；实际CRC须匹配payload | 范围LENGTH；实际CRC须匹配PC期望 |
| 失配 | DDR_ERROR800B并返回实际CRC | CRC_ERROR8001并返回实际CRC |

范围判断先验证ADDRESS、长度上限，再用 `length <= end-address`，不使用容易溢出的address+length。非法Header/长度/地址/FLAGS/版本/数据CRC或序号不产生DDR事务。接收缓冲292字节、最近请求292字节、读回scratch256字节分离；最高DATA256字节加Header32和尾CRC4不越界。最近成功新命令请求保留完整字节；同SEQ不同Header/长度/地址/内容均8009，严格匹配的WRITE重发不重写、但再次实际读回CRC。CRC重发也重新读取。失败不推进成功序号，物理损坏后可重新写入并验证。没有正式分块连续镜像会话状态。

CRC仍为CRC32/ISO-HDLC、兼容zlib；16项nibble表放在独立RAM常量镜像中，支持分块累计。固件.text4020字节、.rodata112字节、.bss148字节，.rx_buffer840字节；栈0x3000–0x3FEF、初始SP0x3FF0。ROM/RAM分别生成，不能合成单一DAT。

| 文件 | SHA256 |
| --- | --- |
| build/loader.elf | de08ec6f89132ff469dfd3369e8b5f6d389d0608074534c0f63e82596b008061 |
| build/loader_rom.dat | d5c887dec64d167d7f1532db126df31f1b5d0cf4b051a56d175d19fd56d002d6 |
| build/loader_ram.dat | 986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975 |

首次编译成功后，旧审查器的recovery LBU函数扫描范围包含新增CRC update函数，错误报两处LBU；仅修复隔离审查器的函数边界，对同一ELF再次提取DAT通过，没有重编译ELF或改主审查器。首次仿真入口导入旧shell helper所需decode_response兼容导出、故障兼容脚本sha名称绑定也已补齐；这些是运行入口问题，没有改写任何失败为PASS或替换旧阶段输入。新负例与旧命令干净执行通过。

## 分层验证

1. `sim/uart_loader/stage9/run.py --suite negative --tag v1`：62响应PASS，四次脏BSS复位启动；真实DDR字节9翻转后连续CRC失配，重写恢复；重复WRITE无写事务；地址、长度、尾字节、重试内容、超时和保护区检查通过。RX/pop/LBU2473、TX3720，DDR请求/退休123、AW/W16、AR107，写52字节/读359字节，最低SP0x3F00，Errors/Warnings0，21.09秒。
2. `--suite legacy --tag v1`：原108项主机矩阵PASS，三次ROM启动；写64字节/读2496字节，AW/W16、AR624，RX/pop/LBU5839、TX6480，最低SP0x3F20，Errors/Warnings0，37.01秒。
3. `--suite bulk --tag v1`：纯字节运输模型，在真实MMIO/FIFO边界送收字节；真实CPU、两路互连、共享DDR桥和带背压用户口模型全部保留。覆盖14边界长度、100组1..1024随机文件，共114镜像/148171字节/980响应。114镜像/980响应全部PASS，写148510字节/读297020字节，DDR请求/正常退休112503、AW/W37501、AR75002。RX/pop/LBU183790、TX58800，最低SP0x3F00，Errors/Warnings0，951.78秒。61440字节、所有尾字节、哨兵及整个应用栈保护均通过。模型主动逐字节握手并绕过TX串行等待，不证明115200持续服务能力。
4. `--suite native --tag v1`：原93.75MHz/115200、真实RX/TX引脚、TIME_SCALE1，无UART force；10种1..257边界文件、41响应全部PASS，三次脏BSS启动，写856字节/读1712字节、AW/W247、AR494，RX/pop/LBU2332、引脚TX解码2460，FIFO峰值1、最低SP0x3F00，39236967周期/15218161退休，Errors/Warnings0，694.87秒。
5. `sim/uart_loader/stage9/faults/run.py --suite native --tag v1`：对本新固件复验阶段⑧原速9响应BREAK/洪泛及恢复，三次驻留启动及原速9响应全部PASS，真实帧错1、溢出/丢弃各43、两次W1C、FIFO峰值16，恢复PING/DDR CRC通过；无CPU/UART/FIFO force。驻留2.04秒、线级450.77秒，Errors/Warnings0；正常响应兼容阶段⑧诊断ABI。

6. `run_write_fault.py`：独立7响应追加检查，真实物理DDR在写完成后/第一次读前翻转字节9；新WRITE正确NACK800B且不推进序号，同SEQ合法PING可通过。恢复写成功后再次损坏，严格相同的重复WRITE连续两次NACK800B，没有重写修复，后续新SEQ重写和CRC恢复PASS。写51字节/读102字节，45个请求/退休、AW/W15、AR30，Errors/Warnings0，3.69秒；原五组通过输入不改。

每个新TB复位只毒化BSS/可变缓冲/栈，不重新装RAM DAT，DDR物理内容保留。检查正常退休、实际DDR LBU/LW数值及读响应、SB/SW数据/字节使能、Pango128位lane、接受/响应/退休守恒、原始RX/TX与独立zlib oracle、ROM驻留、所有不可写RAM边界、DDR最高4KiB栈哨兵，以及每个完整镜像的全部64KiB物理内容。该模型不含DDR PHY训练。

## 实板输入与工具

确定性seed=`0x20261009`。输入已生成至 `sim/uart_loader/build/random_stage9/corpus/board/`，manifest逐文件绑定BIN/SHA256/CRC；1000镜像共3700127个有效payload字节，包含14种边界长度 `1/2/3/4/15/16/17/255/256/257/1023/16368/16369/61440`、100组1..61440随机长度、886组1..1024随机长度，数据包含00/FF/RVLD/CRLF等二进制字节。正常17946次停等请求，0预期NACK、0自动重试。

每个文件先写末尾3-byte哨兵，再分块写文件、验证整文件真实DDR CRC，最后读回哨兵CRC。61440-byte文件到窗口末端，不写/探测受保护应用栈；该文件实板末端保护没有独立读探针，工具标记WINDOW_END_NO_BOARD_PROBE。仿真另检查整个应用栈4KiB未变，不能把该计数写成实板测量。

专用PC工具 `tools/uart_loader/candidates/random_stage9/acceptance.py`。plan-only已输出 `build/random_stage9/board_plan.json`，未打开串口。真实模式必须验证已生成的STAGE9_SIM_PASS部署门控和冻结输入才能打开COM11；日志拒绝覆盖，Startup RX/短写/缺响应/额外RX/包CRC/SEQ/DDR CRC或NACK立即停，失败和Ctrl-C保留日志。17项离线测试包含1000镜像完整fragmented-read、错误包/伪DDR ACK/SEQ/短写/额外RX等拒绝，以及独立struct/zlib核验器。`pc/`里的fixture明确标OFFLINE_FIXTURE_NOT_BOARD，不能算实板证据。

部署门控已生成：`sim/uart_loader/build/random_stage9/deployment_gate.json`，SHA256=`d678813c4d5cfaea0116b1cc446f67abc61a3c1728f60f64ac7b4ab732460be9`，状态STAGE9_SIM_PASS/board_result=NOT_TESTED。1186项输入副本（含1000个板级输入BIN、114个仿真输入BIN、代码、工具、TB、ELF/DAT等）已保存validated_sources，103项仿真/离线证据的哈希绑定，286项原保护文件未变。PC实际require_gate只读核验已PASS，不打开串口；CLI help及最终plan-only已执行，`board_plan_final.json`为现行工具身份，旧board_plan.json保留为早期准备输出。门控后不得修改冻结代码/工具/TB或重建DAT再直接上板。

## 历史部署与实板命令（已由用户完成，保留复现）

1. 当前阶段⑧成功C/ELF/DAT和板级证据继续保留；当前PDS/IP/sbit的10文件副本已在 `sim/uart_loader/board/uart_fault_stage8_diag_deployed_workspace/`，之前阶段⑦位流/配置还在 retained_before_deploy。磁盘副本身份不等于独立观察下载位流；用户保留自己确认成功的位流文件。Codex没有替换当前主IP或生成下载位流。
2. 用户临时将ROM/RAM INIT_FILE分别改为下列路径，生成两个IP，再重新综合/实现/生成/下载诊断位流；必须使用这一对DAT，不运行build.ps1重建：

```text
D:/riscv/RISCV/tests/uart_loader/candidates/random_stage9/build/loader_rom.dat
D:/riscv/RISCV/tests/uart_loader/candidates/random_stage9/build/loader_ram.dat
```

3. 关闭串口助手，KEY0复位并等DDR初始化完成。工具会验证冻结门控及输入哈希，拒绝有Startup RX的轮次，不自动flush。以下命令可在任意PowerShell目录执行：

```powershell
$stage9Tool = 'D:/riscv/RISCV/tools/uart_loader/candidates/random_stage9/acceptance.py'
$stage9Logs = 'D:/riscv/RISCV/sim/uart_loader/board'
& C:/python/python.exe $stage9Tool --port COM11 --log "$stage9Logs/random_stage9_first.json"
```

4. 再次KEY0复位并等DDR初始化，使用新日志执行第二轮：

```powershell
& C:/python/python.exe $stage9Tool --port COM11 --log "$stage9Logs/random_stage9_after_reset.json"
```

每轮1000条IMAGE进度，其中PC=DDR CRC相等，普通文件tail_guard=PASS，满61440文件WINDOW_END_NO_BOARD_PROBE；最后必须RESULT: PASS stage9 1000 random/boundary images，3700127 bytes，zero errors/retries。17946请求共4349180字节TX/1076760字节RX（有效文件payload3700127，额外哨兵写2997）；约9–15分钟每轮是115200串行量的估算，真实耗时/速率以日志为准。可追加 `--bitstream 用户实际位流路径`记录文件哈希，但该字段不能独立证明已下载。

任何FAIL/超时/额外响应/CRC或字段异常停止并保留日志，不能覆盖同名文件重试或跳过失败镜像。工具自动重试为0，Ctrl-C也保存未完成记录。用户提交两轮日志/终端输出后Codex离线核验并新增固定档案：

```powershell
cd D:/riscv/RISCV
& C:/python/python.exe sim/uart_loader/stage9/finalize_board.py --first sim/uart_loader/board/random_stage9_first.json --after-reset sim/uart_loader/board/random_stage9_after_reset.json --output sim/uart_loader/board/random_stage9_board_result.json
```

上述板级汇总已执行并PASS：2000镜像/35892响应/7400254有效文件字节。核验器拒绝fixture/plan、同一份复制日志、少镜像、错误CRC/字段、重试或候选身份不符；固定档案与当前配置见[实板验收记录](UART_Loader随机二进制两轮实板验收_2026-10-09.md)。现有输出拒绝覆盖，后续重验应使用新输出文件名。阶段⑩尚未开始。
