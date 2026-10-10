# UART 程序下载 Loader：当前工程调查与第一版方案

2026-10-09计划调整：用户要求精简，剩余原阶段⑩至⑮按[三个验收关口](UART_Loader剩余阶段精简计划_2026-10-09.md)推进：真实程序下载、校验并运行Hello、同位流换程序与CoreMark。本文原编号和检查项保留为详细设计/证据索引；实际开发及上板批次以精简计划为准，历史状态以最新交接为准。

日期：2026-10-07（Asia/Shanghai）。根目录：`D:/riscv/RISCV`。

本轮仅调查、核对已有证据和规划。新增本文；没有修改 RTL、C、链接脚本、IP、DAT、位流或既有日志，没有构建软件、重跑仿真、操作串口或上板。方案内地址分为“当前事实”和“建议分区”，建议分区尚未实现、尚未验收。

已阅读根 `AGENTS.md`、`doc/CODEX_HANDOFF.md`，核对 CPU/SoC/互连/BRAM adapter/UART/DDR bridge、板级顶层、IP 配置、ROM 搬运源与实际 DAT、Echo 和 CoreMark 启动/链接/构建/ELF/MAP，以及 DDR、Echo、裸机 C、CoreMark 测试入口和选定原始凭据。交接文件按最新条目覆盖历史快照，不能把旧“尚未运行 C/CoreMark/Echo”沿用为当前状态。

## 1. 结论与本轮边界

当前具备 UART 实板 Echo 与复位后重复通信、CPU 经 DDR 控制器写/读/取指的物理模型验证、从 ROM 搬入 DDR 执行裸机 C 的验证。CoreMark 两组 60 次也已有用户提供的实板 CRC/时长验收凭据，但其部署仍通过 RAM 初始化镜像。

缺少的是常驻 UART Loader、可靠二进制下载协议、DDR 全镜像 CRC32 校验、受控 RUN、PC 工具及这条新链路的测试；不是缺少基础 DDR 写/读/取指功能。

**关键结构限制：当前片内数据 RAM 不接指令总线，不能直接从它执行 Loader。第一版推荐 UART Loader 的 `.text` 常驻片内指令 ROM，常量、状态、缓冲和 Loader 栈放片内数据 RAM；下载程序仍在 DDR。** 这是用户“优先片内 RAM/BRAM 执行”目标在当前硬件上的可行实现。若要求从可写片内 RAM 执行，则需要改指令译码/BRAM 端口，另立硬件步骤；本版不需要它。

未来首次部署 UART Loader，需要一次生成 Loader ROM/RAM 初始化并重建、下载位流。Loader 固定后，更换普通裸机程序才可走 `C → ELF → BIN → UART → VERIFY → RUN`，不再更换程序暂存 RAM IP。改变 Loader、UART 固定波特率或硬件功能仍可能需要新位流。

## 2. 真实 CPU 地址空间

以下为当前板级默认参数链，不采用独立 TB 的覆盖值。依据：`myriscv/board_top.v`、`soc_ddr3_top.v`、`soc_top.v`、两个 bus interconnect、两个 BRAM adapter 及三块 IP IDF/wrapper。

| 对象 | CPU 字节地址，含首尾 | 容量/权限 | 依据与注意事项 |
| --- | --- | --- | --- |
| CPU 复位 PC | `0x00000000` | 首条指令 | board_top 默认 RESET_PC 经 DDR 顶层传至 CPU；mycpu_sync 复位设置 PC |
| 指令 ROM | `0x00000000–0x00003FFF` | 16 KiB，仅取指 | INST_ROM_BASE=RESET_PC；ROM mask=`0xFFFFC000`；IP 4096×32 bit |
| 数据 RAM | `0x00000000–0x00003FFF` | 16 KiB，数据读写 | DATA_RAM_BASE=RESET_PC；RAM mask 同上；独立于同地址 ROM |
| simple_mmio | `0x10000000–0x10000FFF` | 4 KiB 译码窗口 | 实际仅已定义寄存器可合法访问，不能把整个窗口当 RAM |
| UART | `0x10001000–0x1000100F` | 16 字节，数据 MMIO | 精确比较地址 `[31:4]`；soc_top 启用 UART |
| DDR3 | `0x40000000–0x5FFFFFFF` | 512 MiB，指令/数据共享 | DDR mask=`0xE0000000`；板级 ENABLE_DDR=1 |
| 其他区域 | 除上述映射外 | 未映射 | 经现有互连返回 access fault；不允许下载访问 |

独立 interconnect 的默认 ROM/RAM 基址为 `0x80000000`，但 soc_top 已覆盖；物理 DDR 定向 TB 也覆盖 RESET_PC 为 `0x80000000`。这些测试地址不改变板级地址。

DDR IP 当前 x16，row=15、column=10、bank=3、控制器地址宽 28；配置容量 `2^(15+10+3) × 2 bytes = 512 MiB`，与 CPU 译码窗口相符。这只确认配置与映射，不表示全部 512 MiB 地址均已做实板无别名/长期稳定性测试。第一版只使用已有软件验证的低 64 KiB 区域。

simple_mmio 寄存器：`0x10000000 SCRATCH`、`0x10000004 ID`、`0x10000008 CYCLE`、`0x1000000C STATUS`、`0x10000010 TEST_STATUS`。CYCLE 为 32 位 core_clk 计数，93.75 MHz 下约 45.81 秒回绕；短超时用无符号差值，不依赖未核实的 rdcycle。

## 3. 当前启动程序、镜像、段与栈

### 3.1 启动链与真正使用的文件

板级层次为 `board_top → soc_ddr3_top → soc_top → mycpu_sync`，PDS 设计顶层是 board_top，行为仿真顶层另为 tb_board_top_selftest。125 MHz 参考时钟经 DDR IP 得到配置 93.75 MHz core_clk。`ddr_init_done && pll_lock` 两拍同步后才释放 SoC 复位；训练未完成时 CPU 不能运行 UART Loader 或响应 PING。

当前指令 ROM IDF/wrapper 引用 `MyCpu_test/board_selftest/boot_rom.dat`。实际前 24 个字是 CPU 搬运代码：从数据 RAM `0x3FF0` 读取清单，LW/SW 将 RAM payload 复制到 DDR `0x40000000`，可复制第二数据区，最后 JALR 到 `0x40000000`。没有 UART 下载、CRC、ACK 或等待 RUN；这个旧 loader 会自动跳转，也没有设置 C 栈。构建源为 `MyCpu_test/build_ddr_stage.py::boot_program()`，board_selftest 构建使用 `build_ddr_selftest.py`；该通用函数旧默认 base 不能替代实际 DAT 的 `0x40000000`。

数据 RAM 最后 16 字节 `0x3FF0–0x3FFF` 为 `[code_words, data_source_offset, data_words, reserved]`。平坦 C BIN 转换器把整个 BIN（含 rodata/data）当首个连续 payload，第二区长度为 0；当前旧流程 BIN 最多 **16,368 bytes**，不是 16,384 bytes。

**当前 data_ram IDF、wrapper 和 IP TB 三处均引用 `tests/coremark_baremetal/build/validation_60/main.dat`。** Echo README 中“当前 RAM IP 仍为 Echo”是其验收时状态，不能据此更改现工程配置。生成初始化内容、PDS 产物和当前 FPGA 已下载位流仍是不同事实；本轮没有采集板上位流身份。

Echo 成功归档在 `tests/pc_uart_fpga_uart_pc/main.dat`，构建副本在其 `build/main.dat`；本轮只读重算两者 SHA-256 均为 `2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20`。保持这些成功文件原样。

### 3.2 已构建程序的实际布局

Echo 与 CoreMark linker 均声明 DDR ORIGIN=`0x40000000`、LENGTH=64K；`.text → .rodata → .data → .bss` 顺序增长，`.data` LMA=VMA，`.bss` NOLOAD 且按字对齐。`.text.startup` 放最前面，ELF entry 是 `_start`，不是 main。

| 段/符号 | Echo 已有 main.map/ELF | 当前 validation_60 main.map/ELF |
| --- | --- | --- |
| entry/_start | `0x40000000` | `0x40000000` |
| `.text` | `[0x40000000,0x400000F0)`，240 bytes | `[0x40000000,0x40002B40)`，11072 bytes |
| `.rodata` | 无内容 | `[0x40002B40,0x40003398)`，2136 bytes |
| `.data` | 空，边界 `0x400000F0` | `[0x40003398,0x400033AC)`，20 bytes |
| `.bss` | `[0x400000F0,0x400000F8)`，8 bytes | `[0x400033AC,0x40003B88)`，2012 bytes |
| BIN | 240 bytes | 13228 bytes；不包含 BSS/栈 |
| `__stack_bottom` | `0x4000F000` | `0x4000F000` |
| 初始 sp/`__stack_top` | `0x40010000` | `0x40010000` |
| Heap | 无 allocator/明确 heap 分区 | 静态 2000-byte 工作缓冲，未用动态 heap |

表中段为左闭右开，其他地址空间表为含首尾。栈范围含首尾是 `0x4000F000–0x4000FFFF`，4 KiB，向低地址增长，ABI 要求 sp 16 字节对齐。初始 sp 在范围上边界之后，首次分配栈帧再进入栈区；不是在 `0x40010000` 写第一字。CoreMark 原 Full Boot 实测最低 sp=`0x4000FA40`，使用1472 bytes；这是当前程序的证据，不是未来任何程序的栈保证。

startup 设置自己的 gp/sp、清 BSS，然后调用 main；main 返回后死循环。旧 ROM 搬运程序不用栈。当前启动文件未配置通用 C trap handler；Loader 需要单独准备异常停机/诊断路径及关闭 IRQ，不能直接把现有专用 IRQ 测试 ISR 当 C 上下文处理器。

## 4. UART 与 DDR 访问约束

### 4.1 UART 软件接口

| 绝对地址 | 寄存器 | 第一版使用方式 |
| --- | --- | --- |
| `0x10001000` | TX_DATA，写 | 先检查 STATUS bit0，再 volatile uint8/SB lane0 写一个字节 |
| `0x10001004` | RX_DATA，读 | 先检查 STATUS bit2，再 volatile uint8/LBU 读一个字节，pop 一次 |
| `0x10001008` | STATUS，读 | bit0 ready、1 busy、2 RX非空、3 FIFO满、4 frame error、5 overflow、6 RX IRQ enable、7 UART IRQ |
| `0x1000100C` | CONTROL，命令写 | bit0/1 W1C 清错误；bit9 禁 IRQ（lane1），如初始写 `(1<<9)|3`；bit8 使能 IRQ，本版不用 |

`uart_rx_fifo` 默认 16 bytes，FWFT，FIFO count 没有软件寄存器。满时继续接收会丢新字节并置 sticky overflow；不能把 empty 返回的 0 与合法二进制 `0x00` 混淆。非法方向/非对齐/窗口外访问不能使用。副作用只在请求接受时发生，响应等待期间不会重复 pop。

现有 Echo 的 `uart_getchar()` 没有超时，main 遇 UART error 后永久停机；只复用其寄存器语义，Loader 接口必须另加超时、错误传播和恢复状态。轮询 RX 应快速排空，不在接收每个字节时同步回显或输出调试文字；协议流与应用 UART 文本分开按状态解析。

### 4.2 DDR bridge/controller

CPU 字节地址先减 DDR_BASE。CPU 支持 SB/LB/LBU（任意字节）、SH/LH/LHU（2 字节对齐）、SW/LW（4 字节对齐）；取指地址需4字节对齐。非对齐半字/字走 CPU 异常，没有自动拆分跨字访问。

Pango 用户口每拍128bit/16 bytes；命令地址单位16bit半字：`ctrl_addr=(local_byte_addr>>1)&~7`，`lane=local_addr[3:2]`。CPU 已移位的32bit数据和4-bit strobe 再由桥移至所选槽，展开成16-bit byte enables。**CPU 侧不要求所有访问16字节对齐**；16字节对齐约束属于桥生成的整拍命令。Loader 主循环按小端整理4字节后 SW，最后1–3字节以 SB 写，不越界补写或覆盖邻居。

桥单 outstanding、AWLEN/ARLEN=0，两路同时请求数据优先；没有 burst、公平仲裁、DMA、Cache。写数据在 AW 前稳定，首次 WREADY 接受后向 CPU 回应；读没有 RREADY。没有标准 B/BRESP/RRESP，bridge rsp_error 固定0，也没有事务 watchdog。因此不能用“无总线error”代替数据校验；控制器若永不回应，CPU 会卡在事务中，软件 UART 超时无法救回，只能外部复位或以后增加硬件恢复机制。

CPU `mycpu_sync.v` 明确实现 FENCE 串行排空，**FENCE.I 未实现**。当前无 I/D Cache，已有“写入新代码再 JALR”的验证；本版 RUN 前可用普通 `fence rw,rw` 并通过跳转冲刷取指，不能插入 fence.i。未来加 Cache 后必须重新设计代码可见性。RV32I 回归 supported40/40，全量40/42，fence_i/ma_data 为 known_gap，不能声称完整扩展 ISA 支持。

## 5. 现有验证证据与缺口

| 能力 | 已有证据/范围 | 本轮判断 |
| --- | --- | --- |
| CPU→DDR写、DDR→CPU读、DDR取指 | `ipcore/ddr3/sim/modelsim/soc_ddr3_sim.log`：2026-10-06 22:19:47开始；CPU SW/LW读回42，再写入指令并执行，81.584us PASS；Errors0/Warnings357 | 三项基础功能已有真实 CPU＋真实IP＋物理模型可靠定向证据 |
| 槽位、掩码、跨拍、DDR代码再访存 | 同目录 `soc_ddr3_regress_sim.log`：2026-10-06 22:22:39开始；14项load与连续DDR执行，90.704us PASS；Errors0/Warnings357 | 四槽/邻拍/字节半字/代码路径已验证，不等于全容量压力 |
| 原ROM→DDR→C→UART Echo | `sim/uart_echo/build/modelsim_results.json` 和 full_boot/modelsim.log；四层4/4，每层97字节；Full Boot搬60字、DDR取指、BSS清零，Errors0 | 用户口模型含背压/延迟，不含PHY训练；本轮DAT哈希仍匹配凭据 |
| UART实板Echo和复位重复 | `tests/pc_uart_fpga_uart_pc/README.md`、verified_image.json、`doc/uart/UART_Echo实板基本回显确认_2026-10-07.md`及本轮用户确认 | 功能验收已有；无大随机二进制/长时压力结论 |
| 非空.data/.bss | `sim/baremetal_c/build/led_pass/modelsim.log`：mode1 copied83/BSS8 PASS/Errors0；CoreMark MAP和Full Boot毒化BSS检查 | C初始化已有证据，但新Loader reset初始化仍要测试 |
| CoreMark DDR实板运行 | `sim/coremark/board/results_iter60_user_20261007.json`：两组BOARD_CRC_AND_DURATION_PASS；模型 results_60.json 分别保留 | 进一步支持DDR软件执行；不是UART下载CoreMark PASS |

物理 DDR 测试的 ROM 是独立仿真模型，RESET_PC 覆盖为0x80000000；从CPU握手与退休检查实际数据及指令结果，不是仅检查桥内部值，也不是通过TB预灌DDR代码。本轮另将当前21个myriscv源文件SHA-256与`sim/coremark/build/results_60.json`的protected_sha256逐一比较，全部一致，确认该验收时的生产RTL未被替换。当前源码路径无新增差异不意味着当前PDS位流/整个系统已重测；这些日志按原日期与范围引用。

**本轮不必先新增DDR基础写/读/取指定向测试。** 若后续改共享RTL或发现证据对应输入变动，则重新运行两个脚本；其中任何一个FAIL应先定位基础路径，停止UART下载后续阶段。

仍缺的前置验证：ROM常驻C代码＋RAM常量/状态/栈布局、KEY0复位后RAM状态重置、接收整块时的FIFO服务间隔；新下载路径的长二进制/尾字节/边界/异常包/重试/超时、DDRCRC32、LOAD不自动跳转、RUN验证状态与入口限制、应用栈切换及重复下载执行。高波特率与全512MiB也未有这类验收。

## 6. 第一版推荐布局（待确认，均在真实映射内）

### 6.1 Loader 独立于 DDR 的常驻布局

| 总线/区域 | 建议含首尾地址 | 用途/限制 |
| --- | --- | --- |
| 指令ROM | `0x00000000–0x00003FFF` | Loader startup、trap、`.text`；entry=0；最大16KiB，链接断言检查容量 |
| 数据RAM | `0x00000000–0x000000FF` | 保留诊断/边界哨兵，不供UART LOAD写入 |
| 数据RAM | `0x00000100–0x00000FFF` | Loader `.rodata`/只读表，固定IP预置；最多3840 bytes |
| 数据RAM | `0x00001000–0x00001FFF` | Loader `.bss`、状态、计数器；可变状态启动显式初始化 |
| 数据RAM | `0x00002000–0x000020FF` | 256-byte块接收缓冲，4字节对齐 |
| 数据RAM | `0x00002100–0x00002FFF` | 小报文、工作空间/预留，不自动用作heap |
| 数据RAM | `0x00003000–0x00003FEF` | Loader向下栈，4080 bytes；初始sp=`0x00003FF0`，16字节对齐 |
| 数据RAM | `0x00003FF0–0x00003FFF` | 保留旧manifest地址，UART Loader不读取；禁止新LOAD写入 |

这些地址是软件建议，不是新硬件译码。全部片内RAM均不在PC可下载区域。ROM `.text` 和RAM的数据VMA同属低地址但不同存储器；链接时定义独立region/PHDR并按section分别生成 `loader_rom.dat`、`loader_ram.dat`，不能把整个重叠地址ELF直接objcopy成单BIN。

**C从ROM取指时，普通load同地址读到的是数据RAM。** 因此字符串、CRC表、编译器switch跳表等 `.rodata/.srodata` 必须映射到上述数据RAM区，不能照搬DDR linker把常量放到ROM代码后。第一版尽量只用BSS可变状态和显式赋值，避免非零可变 `.data`；若必须使用，需要保留不可修改的初始化模板并在每次复位恢复，不能假设IP初始化每次KEY0都会重新装入。只读表由固定RAM镜像预置且Loader/目标程序不得改它。检查程序对RAM的写范围和栈水位；没有MPU来硬件隔离错误应用。

### 6.2 下载程序与应用栈

| 区域 | 建议含首尾地址 | 规则 |
| --- | --- | --- |
| DDR程序区 | `0x40000000–0x4000EFFF` | `.text/.rodata/.data/.bss`；第一版无heap，低地址向上布局 |
| DDR应用栈 | `0x4000F000–0x4000FFFF` | 4KiB向下栈，初始sp=`0x40010000`；下载禁止写入 |
| 其余DDR | `0x40010000–0x5FFFFFFF` | 第一版协议拒绝写入；未来扩大需另验证/改布局 |

LOAD首块地址固定 `0x40000000`，后续块必须连续，不允许任意写MMIO/片内RAM/任意DDR。entry第一版固定 `_start=0x40000000`，RUN仍带地址并严格校验，不支持在BIN中任意main地址执行。总BIN名义最大60KiB=**61,440 bytes**；实际要求 `ALIGN_UP(file_end,4) <= __bss_start <= __bss_end <= 0x4000F000`，因此非空BSS会降低实际文件上限。程序区不留额外动态heap；以后如需要，显式设 `[ALIGN_UP(__bss_end,16),heap_end)` 并保留stack guard，不能让allocator自由增长至栈。

老DDR自检的 `0x40001000` 诊断区/`0x40002000` scratch 不再作为新Loader工作区；当前CoreMark本来就覆盖这些地址。只有新ROM明确替代旧自检启动且不再使用这些诊断数据时，才能执行本布局；不得并行保留会写这些地址的旧自检任务。Loader诊断放片内RAM。

范围检查使用减法：先确认 `base<=address<limit`，再确认 `length<=limit-address`；不要只检查 `address+length`，以免32位溢出。非末块长度为4的倍数，块起点4字节对齐；末块允许1–3尾字节，尾部SB精确写入，CRC只覆盖原BIN长度。RUN要求至少4个有效镜像字节、entry+4不越已校验镜像；强制entry=base和4字节对齐。

目标应用 `_start` 自己设gp/sp、清BSS再main。Loader保持自身RAM栈到最后跳转；不要用C函数调用随意跨sp切换，不支持返回Loader。一次RUN后重新下载需KEY0复位，重新训练/初始化Loader后PING。无复位热返回、多程序驻留、多段ELF装载和重定位不在v1范围。

## 7. UART 下载协议 v1（建议规格，未实现）

### 7.1 帧格式

8N1、115200、二进制透明传输、无硬件流控；不能用文本行/换行作分隔。所有多字节整数字段小端，序号不回绕；复位后PC重新PING并开启新下载。

每帧：`32-byte Header → LENGTH bytes DATA → 4-byte DATA_CRC32`。零长度DATA也带CRC32=0。MAGIC原始字节为ASCII `RVLD`（52 56 4C 44），不靠主机整数表示猜端序。

| Header偏移 | 字节数 | 字段 | 语义 |
| --- | --- | --- | --- |
| 0 | 4 | MAGIC | `RVLD` |
| 4 | 1 | VERSION | 1 |
| 5 | 1 | CMD | 1 PING、2 LOAD、3 VERIFY、4 RUN；0x80 RESPONSE |
| 6 | 2 | FLAGS | LOAD bit0 BEGIN、bit1 END；其余必须0；其他请求为0 |
| 8 | 4 | SEQ | 请求序号，响应原样回送；只允许一笔等待中的命令 |
| 12 | 4 | ADDRESS | LOAD块地址、VERIFY镜像基址、RUN入口；PING为0 |
| 16 | 4 | LENGTH | 本帧DATA字节数；LOAD为1..256，PING/VERIFY/RUN为0 |
| 20 | 4 | TOTAL_LENGTH | LOAD/VERIFY/RUN的完整原BIN长度；PING为0 |
| 24 | 4 | IMAGE_CRC32 | PC对完整原BIN的CRC32，所有同一下载命令保持一致；PING为0 |
| 28 | 4 | HEADER_CRC32 | 对Header前28字节计算CRC32，保护地址/长度/命令 |

CRC使用CRC-32/ISO-HDLC（反射实现poly=`0xEDB88320`，初始=`0xFFFFFFFF`，final xor=`0xFFFFFFFF`，refin/refout=true）；与Python `zlib.crc32(data)&0xffffffff`一致。向量 `123456789 → 0xCBF43926`，空数据→0。不是CoreMark算法报告的16-bit CRC。HEADER_CRC、块DATA_CRC和完整IMAGE_CRC是三个不同范围；不把UART收到的CRC当作DDR已正确的证据。

### 7.2 LOAD：两次应答的分块停等

每块严格执行：PC发送Header → Loader验证Header并返回READY → PC发送DATA和DATA_CRC → Loader轮询完整接收入256-byte RAM缓冲 → CRC/错误检查 → CPU按字写DDR → 返回最终ACK。PC收到最终ACK前不发送下一块Header；Loader写DDR、计算整块CRC、发送应答时PC不发送新数据。

第一块必须BEGIN，ADDRESS=base，TOTAL_LENGTH在1..61440；非首块不能BEGIN且地址必须等于base+已接受字节数。同一镜像的total/image_crc不能变；非末块payload长必须4的倍数。只有累计长度等于total时才允许END，END必须存在；首末同块FLAGS=3。只保留一个活动镜像，不能稀疏/乱序/跨保护区写。

Header通过前不接受DATA；Header错误不执行DDR写。完整块CRC/UART错误检查通过前不写该块。有效BEGIN立即撤销旧verified状态；每个新块写前verified必须已清除。中途错误、TIMEOUT、丢包或复位使整次下载无效，要求新BEGIN从头开始；之前已经写入DDR的块可保留物理字节但永不允许RUN。最终LOAD ACK只表示收齐并写入，状态为LOADED_UNVERIFIED，**不自动执行，也不代表整镜像DDR CRC通过**。

支持最近已完成LOAD块的同SEQ重试：必须重新走READY/收块过程，匹配完整Header、DATA内容/CRC后仅重发缓存ACK，不再次写、不增加计数；同SEQ不同内容NACK。重复块识别优先于BEGIN重置与连续地址检查，避免首块ACK丢失重发时错误开启新下载。不能把仅32-bit CRC作为严格相同内容证明，保留最近256-byte缓冲与Header直到下一合法块；重收缓冲与保留缓冲必须分开，重收可用RAM预留工作区。SEQ小于已完成且不等于最近块/序号重复用途不符时拒绝；新合法SEQ递增。未ACK的活动块重试先经过超时/重同步，失败下载重新BEGIN。

### 7.3 PING、VERIFY、RUN

PING：只返回版本/能力、允许的base、最大BIN/块长、活动状态/已接受字节数。PING不写DDR、不跳转；不能凭PING ACK宣布下载能力已PASS。

VERIFY：仅在完整END已接受时，ADDRESS/total/image_crc必须与当前活动镜像完全一致。Loader从DDR按原BIN长度读取，重新计算CRC32，比较PC值并把actual DDR CRC放响应；不把整个程序回传PC。任何差异为CRC_ERROR且verified=false；只校验子范围不能授权RUN。成功置VERIFIED。VERIFY期间PC不发送其他帧。

RUN：必须VERIFIED；ADDRESS=0x40000000、4字节对齐、至少4有效字节，长度和CRC身份与已验证镜像一致，否则NACK。为防止校验后内存变化，RUN前再从DDR按同一范围算CRC；失败不跳转。禁止UART RX IRQ和CPU MIE/mie，完成普通FENCE排空，发送RUN ACK并等TX_BUSY清零，再通过汇编JALR进入应用 `_start`。全过程不得在ACK后还执行会污染应用输出的日志；应用设自己的gp/sp/BSS。

RUN ACK只表示跳转条件满足、即将执行；实际程序执行成功必须看应用输出/仿真退休PC。ACK丢失时PC不能自动重发RUN，因为CPU可能已经执行应用；报告“执行状态未知，需检查输出或复位”。协议阶段结束后工具转为应用UART捕获，避免flush输入吞掉首个Hello字节。

### 7.4 RESPONSE 与状态

响应也使用上述Header及尾CRC，CMD=0x80、FLAGS=0、SEQ对应请求；ADDRESS回显请求（PING返回base）、LENGTH=24、TOTAL_LENGTH返回最大BIN容量61440、IMAGE_CRC32返回活动镜像期望CRC（没有活动镜像为0）。DATA为6个u32：`status, request_cmd, accepted_bytes, actual_ddr_crc, capabilities_and_state, max_chunk`。max_chunk=256；capabilities bit0=CRC32、bit1=ROM常驻、bit2=显式RUN；状态bit16=image_complete（已收齐，在LOADED_UNVERIFIED与VERIFIED时都为1）、bit17=VERIFIED，其余0。actual_ddr_crc仅VERIFY或RUN校验结果有效；其他为0。PC必须验证完整响应CRC、SEQ/CMD/状态后才推进。

| status | 名称 | 规则 |
| --- | --- | --- |
| 0 | ACK | 该命令对应操作完成；RUN另需应用结果 |
| 1 | READY | 只用于LOAD Header通过后；不是最终ACK |
| 0x8001 | CRC_ERROR | Header/DATA/DDR CRC错误；错误类型可由所处阶段判断 |
| 0x8002 | ADDRESS_ERROR | 窗口、起点、对齐、连续性或入口错误 |
| 0x8003 | LENGTH_ERROR | 0/超长/越界/total或END不一致 |
| 0x8004 | TIMEOUT | Header/DATA接收或活动会话超时，撤销下载有效性 |
| 0x8005 | UART_ERROR | frame/overflow；记录状态后撤销，清错/排空/恢复 |
| 0x8006 | VERSION_ERROR | 不支持版本 |
| 0x8007 | COMMAND_ERROR | 未知命令/保留FLAGS非0 |
| 0x8008 | STATE_ERROR | 未LOAD完整/未VERIFY/身份不符 |
| 0x8009 | SEQUENCE_ERROR | 不合法序号/重复内容不同 |

高位1均为NACK，工具显示`NACK <具体名称>`并非零退出。MAGIC不匹配时滑动寻找同步字，不执行操作；Header CRC坏时SEQ不可相信，可返回诊断NACK但PC不能作为正常响应接受，最终由PC超时恢复。收到坏帧后不在任意payload中直接执行新命令：丢弃至串口连续空闲100ms，再开始寻找完整新Header。PC失败后停止发送、等待至少200ms并重新PING/BEGIN。接收Header/DATA的字节间超时建议100ms；活动会话等待下一命令建议5秒；PC响应超时5秒，RUN/VERIFY可给10秒。CPU用MMIO无符号计数差，本版所有单项超时均小于回绕周期。参数须经TB和实际USB串口调度验证。

若DDR桥硬件事务永久无响应，上述软件TIMEOUT无法执行；不能承诺它能对所有硬件故障NACK。UART错误复位前保存诊断，错误分支不得继续CRC通过或跳转。

## 8. 编译与PC工具

本轮只读工具查询确认：工程 `xpack-riscv-none-elf-gcc-15.2.0-1/bin` 的GCC 15.2.0、objcopy 2.45；`-march=rv32i -mabi=ilp32 -print-libgcc-file-name` 选择rv32i/ilp32/libgcc.a。Echo ELF为ELF32小端、RISC-V EXEC、rv32i2p1、16-byte stack alignment、entry=0x40000000。Python `C:/python/python.exe` 为3.13.0，当前该解释器**未安装pyserial**；本轮未安装。

目标程序保留 `-march=rv32i -mabi=ilp32`，禁M/C/A/F/D/V，使用freestanding、nostdlib/nostartfiles、no-relax、msmall-data-limit=0与匹配libgcc；Hello可-O2，Loader优先-Os。不能把-rv32im换来减小软件乘除。最终反汇编仍要逐条审查CPU指令白名单，避免fence.i/rdcycle或扩展库指令；ISA字符串本身不能证明最终机器码合法。

建议新应用构建输出 `program.elf/.map/.dis/.readelf.txt/.bin/program.json`，保持 `.text=0x40000000`、LMA=VMA，NOLOAD BSS与顶部栈。program.json由ELF生成，记录entry/load_base/file_bytes、段范围、BSS边界、stack、ISA/ABI、SHA256和CRC32。BIN没有入口/地址/BSS信息，PC不能从BIN字节推断这些值；默认要求同名manifest并与BIN哈希匹配。v1只支持这个固定ABI的连续平坦映像，不做ELF重定位。PC和构建审查负责BSS/栈布局，Loader只能基于协议验证文件窗口与固定入口。

构建步骤是 `gcc → readelf/objdump/nm审查 → objcopy -O binary → ELF/BIN一致性及布局检查 → program.json`。BIN包含loadable的text/rodata/data及必要空洞，不包含BSS/栈；CRC覆盖完整原BIN，包含实际空洞字节。下载程序构建不再调用旧BIN→RAM DAT转换器。Loader自身ROM/RAM DAT是首次固定部署产物，单独生成。

拟用Python+pyserial PC命令（命令尚未实现，COMx待实际指定）：

```text
loader --port COMx ping
loader --port COMx load program.bin
loader --port COMx verify
loader --port COMx run --entry 0x40000000
loader --port COMx program.bin            # PING → LOAD → VERIFY，然后停下
loader --port COMx program.bin --run      # 用户显式要求才发送RUN并捕获应用输出
```

独立verify/run命令需读取同一program.json/本地会话记录，必须再次PING核对活动镜像状态，不能靠上次工具进程的本地“成功”猜板上状态。自动快捷流程只有带显式--run才执行；LOAD成功绝不自动跳转。

工具显示端口/波特率、file size、load base、ELF entry、有效payload发送与ACK接受字节数（重发字节另计）、单次下载耗时/整体耗时、实际KiB/s（bytes/1024/s）、PC CRC/DDR CRC、READY/ACK/NACK、最终VERIFY状态、RUN已接受与应用结果/执行未知。Hello阶段要求精确捕获`Hello World\r\n`，不能只显示RUN ACK即“执行成功”。错误重试有界，正常随机压力验收要求零重试；注错测试可按规定恢复。运行记录保存原始TX/RX二进制、时间戳/SEQ/status JSON、BIN/manifest/hash、DDR CRC、UART应用日志与Loader/位流身份。pyserial依赖安装属于实际工具实现时动作。

## 9. 严格分阶段实施与PASS/FAIL

所有阶段依次开门，前一级FAIL即停止。每一级先通过其适用的独立模型/真实CPU仿真，再实板确认；已存在的旧能力PASS是前置证据，不能代替新Loader同镜像验收。仿真通用条件：正确对应输入镜像、有RESULT: PASS、无RESULT: FAIL、进程退出0、ModelSim编译/运行Errors0；厂商原语warning对比基线，不要求0。每级记录日期、命令、输入哈希、源码/镜像身份、PASS/FAIL和未覆盖范围。

| 级 | 测试方法与输入 | 预期输出/PASS条件 | FAIL条件 | 保存产物 |
| --- | --- | --- | --- | --- |
| 0 Echo基线 | 阅读现有97-byte四层仿真和实板复位回显证据；新Loader部署前保留旧基准 | 已有Echo功能PASS，本轮确认归档哈希一致 | 证据/镜像不一致则先恢复可核对基准 | 旧DAT、凭据、截图原样保留；新部署另存位流hash |
| 前置 ROM驻留 | 独立新Loader linker/startup最小候选，只读RAM常量、清BSS、检查栈；两次复位并毒化状态 | PC始终从ROM执行；常量正确；BSS/状态每次恢复；RAM栈无越界 | 数据常量读成代码/旧状态残留/从数据RAM误取指/栈破坏 | ELF/MAP/分开ROM-RAM DAT、TB、日志、最低sp/guard |
| ① PING/ACK | PC/TB发合法PING；100次序号递增，复位再发 | 每次一个CRC合法对应SEQ的ACK；无DDR写/跳转 | 缺/重复ACK、乱码、error、超时、错误状态 | 请求/响应原始字节、uart.log、results.json |
| ② 固定小数据接收 | 发送20 bytes `00..13`，仅验证接收缓冲，不启用DDR写 | 缓冲与输入逐字节一致，00正常；仍在ROM | 长度/值/顺序错，额外DDR写/跳转 | stimulus.bin、缓冲转储/scoreboard、日志 |
| ③ CPU轮询FIFO | 同20-byte连帧，TB加MMIO响应延迟和异步相位 | 引脚RX、pop、退休LBU、缓冲一致；无frame/overflow | pop重复/漏、FIFO溢出、读空当0、异常 | UART/MMIO/退休计数、FIFO峰值/服务间隔、可选VCD |
| ④ CPU写DDR | 从已验收缓冲写20 bytes到base，检查SW及跨16-byte拍地址 | 接受写地址/数据/strobe完全符合，保护区哨兵不变 | 错地址/掩码/邻区改写、重复写或无写 | 写事务轨迹、保护区检查、DDR模型/日志 |
| ⑤ DDR读回 | CPU LW读5字，从DDR而非RAM缓冲取得结果 | 读退休值为03020100、07060504、0B0A0908、0F0E0D0C、13121110 | 读源错/值错/错误/超时 | CPU退休读值、读事务/日志 |
| ⑥ 固定数据比较 | CPU逐字比较上述5字，TB再注入一字错值 | 正常MATCH；注错MISMATCH并保留位置，未跳转 | 注错仍PASS/只靠TB直接读判成功/保护区坏 | 正常与注错独立日志、首错地址/期望/实际 |
| ⑦ CRC32 | C/PC对空串、123456789、20-byte数据；CPU从DDR读原长CRC，TB改一字节 | 向量一致；正常DDR CRC=PC CRC；改字节不一致 | CRC变体/端序/覆盖长度错，缓存CRC冒充读回 | crc_vectors.json、PC/CPU/DDR三值、注错凭据 |
| ⑧ ACK/NACK及恢复 | 错magic/version/cmd/flags/header CRC/data CRC/address/length/SEQ；中断帧、帧错、overflow、复位、最后ACK丢失重试 | 对应拒绝；未校验块无写；已有下载失效规则正确；同块重试不重复写；RUN前不取DDR | 坏包写入/伪ACK/越界/无法恢复/提前执行 | 每用例packet.bin、结果与写计数、UART error和trap日志 |
| ⑨ 随机二进制压力 | 固定seed；长度1/2/3/4/15/16/17/255/256/257/1023/16368/16369/61440；另100组随机长度/内容，含00/FF/MAGIC/CRLF；多块停等 | 所有完整DDR CRC与PC一致；尾字节/哨兵正确；正常0error/0retry；实板再循环1000镜像或累计≥16MiB | 任何CRC错/重试掩盖丢包/保护区破坏/停不下来 | seed、输入BIN/hash、CRC/耗时/重试/错误计数、TXRX捕获 |
| ⑩ 下载真实program.bin | 使用新独立Hello ELF/BIN/manifest，含非空data/bss；发送LOAD完整END | 每块ACK，LOADED_UNVERIFIED；DDR可读；持续在ROM，未输出Hello | ELF/link与base不一致、未完整也成功、LOAD自动运行 | ELF/MAP/DIS/BIN/manifest、加载事务、状态/无取指证明 |
| ⑪ VERIFY | 全范围合法VERIFY；错CRC、子范围、缺END、校验后注错再RUN | DDRCRC=PCCRC才VERIFIED；负例拒绝；RUN再次校验能发现改动 | 仅收串口CRC即成功/子区CRC授权完整RUN/改字节仍RUN | PC与DDR CRC、状态转移、注错日志 |
| ⑫ RUN | 未VERIFY/不对齐/ROM/MMIO/stack/非base/长度身份不符入口；再发合法RUN | 负例无跳转；合法仅一次ACK、TX发送完后跳至_start；禁止自动重发RUN | 坏入口执行、先跳再ACK、错误后仍执行 | RUN包、ACK、跳转前后状态/PC、UART波形 |
| ⑬ DDR取指 | TB不预灌DDR，代码只能从真实UART接收；跟踪接受取指与退休指令 | 首个DDR退休PC及指令匹配BIN，startup设置应用sp/gp且清BSS后main | 仅PC请求到DDR却无退休/旧预灌代码执行/异常/栈错 | payload对照、退休trace、SP/BSS/guard检查 |
| ⑭ Hello World | 实板新固定Loader位流；加载/VERIFY/RUN Hello，KEY0后重复至少10次，再换第二不同BIN | 精确输出Hello World CRLF；data/bss检查PASS；改程序只需重编BIN，位流hash不变 | 没输出/乱码/旧程序输出/需换IP才能换程序/复位后失败 | 同位流hash、两个BIN及manifest、10轮CRC/状态/原始UART |
| ⑮ CoreMark | Hello新链路PASS后，用已有RV32I端口BIN经UART下载，两组先短CRC再60次 | 下载CRC32与算法CRC分别正确；60次≥10s且32-bit计时不溢出；两组结果匹配已知凭据 | 下载CRC或任一算法CRC错/时间不足/溢出/仅LED作结论 | BIN/配置/hash、协议CRC、完整CoreMark UART/ticks、栈水位 |

②到⑥是受控开发/诊断里程碑，不是v1对外任意存储器命令，不扩正式协议。①前的ROM驻留验证是当前结构带来的必要前置；它失败就不能进入PING。阶段⑨可VERIFY数据但禁止RUN随机字节，阶段⑬才认可“UART下载代码真的执行”。最后程序检查非空data/bss失败时，单独Hello字符串不能判总体PASS。

新增Loader软件测试需覆盖候选启动而不是用旧24字搬运ROM；共享RTL未改时可以复用生产核/互连/桥/UART和独立用户口模型。正式首次推广前按影响重跑UART TX/RX/MMIO/CPU、access-fault以及两条完整DDR物理模型脚本；若要新ROM/RAM生成真实板级模型Full Boot，可在独立sim目录准备，不覆盖旧IP或成功镜像。

## 10. UART性能后续验证

当前TX/RX均用整数四舍五入 `BIT_CYCLES=(CLK_HZ+BAUD/2)/BAUD`；无软件baud寄存器，soc_top只传CLK_HZ，uart_mmio的BAUD目前默认115200。未来升速需把BAUD参数逐层传递/重新综合，或另行实现并验证可编程分频；不能只改PC串口波特率，不能把CORE_CLK_HZ参数当真实升频。

| 目标baud | 93.75MHz分频 | 算得实际baud | 分频误差约 | 16-byte FIFO填满时间（目标速率） |
| --- | --- | --- | --- | --- |
| 115200 | 814 | 115171.990 | -0.0243% | 1.389ms |
| 460800 | 203 | 461822.660 | +0.2219% | 347.2us |
| 921600 | 102 | 919117.647 | -0.2694% | 173.6us |
| 1Mbps | 94 | 997340.426 | -0.2660% | 160us |
| 2Mbps | 47 | 1994680.851 | -0.2660% | 80us |

只是算术估算，不是高速UART可用结论。115200/8N1裸数据名义上限11520B/s，实际按当前分频约11517B/s；256-byte块加32-byteHeader、4-byte数据CRC及两个60-byte应答，理论净payload比例256/412≈62.1%，约7.16kB/s，USB调度、两次停等、CPU/DDR时间还会降低。下载60KiB纯协议线速下限约8.6s，无停等额外延迟时；不能把这个值当实测速率。

Hello与115200二进制CRC压力PASS后，每一级依次做阶段⑨同样随机/边界/持续测试，实板≥1000镜像或≥16MiB、0CRC错/0UART error/正常0retry，再复位重复及Hello。保存适配器/驱动/位流参数、RX最坏服务间隔、FIFO峰值（仿真/探针）、下载耗时和实测速率。高速字符串Echo成功不足以开门。若失败回到最后通过的速率；先改软件轮询/块调度或评估FIFO容量，再单独考虑DMA，第一版不加DMA。

## 11. 预计文件清单（未来编码范围）

| 文件/目录 | 预计动作/职责 |
| --- | --- |
| `tests/uart_loader/README.md,main.c,uart_loader.c/.h,uart_io.c/.h,crc32.c/.h` | 新独立Loader实验，解析/状态/范围/超时/CRC/轮询；根放源码，不建common/src层 |
| `tests/uart_loader/startup.S,linker.ld,build.ps1,image_to_dat.py` | ROM取指＋RAM常量/状态/栈，分别输出固定ROM/RAM镜像；容量/ISA检查 |
| `tests/uart_loader/build/` | loader.elf/map/dis、loader_rom.dat/loader_ram.dat、构建manifest；只写自己的产物 |
| `tests/uart_download_hello/main.c,uart_printf.c/.h,startup.S,linker.ld,build.ps1,README.md` | 新独立应用，复用已验收UART寄存器语义，输出Hello并检查data/bss，生成program.bin/json |
| `tools/uart_loader/loader.py,protocol.py,requirements.txt,README.md` | PC串口CLI、编码/CRC、分块/序号/重试、显式RUN与日志；程序侧无新DAT需求 |
| `sim/uart_loader/run.py,tb/tb_uart_loader.v,tb/loader_bram.v,tb/pango_ddr_model.v` | 独立真实CPU验证；ROM/RAM新候选；引脚驱动/解码、DDR背压、注错、保护区与退休检查 |
| `sim/uart_loader/test_protocol.py,cases/,build/,board/` | 协议互操作/负例、固定seed输入、日志/VCD/JSON及实板捕获；不放tests软件目录 |
| `tests/coremark_baremetal/build.ps1`或独立UART构建脚本 | 到阶段⑮才提供BIN/manifest输出途径，保留旧DAT/verified基准；算法源码不改 |
| `ipcore/inst_rom/*,ipcore/data_ram/*` | 只有候选全链路验收、方案确认后首次部署才切固定Loader初始化；不扩大深度，不覆盖旧成功镜像 |
| `RISCV.pds` | 仅确有工程输入/主仿真入口调整时修改，设计顶层仍board_top |
| `myriscv/*` | 115200第一版原则上无功能改动；高波特率阶段才评估参数传递；CPU/共享桥/译码不因Loader重写 |
| `doc/CODEX_HANDOFF.md,AGENTS.md,README.md` | 实际阶段完成后再记录入口/实测状态，未来需要时精确修改 |

本轮只新增本文。Git原有PDS/IP/日志/源码/删除等改动均保留；本文被当前 `/doc/*` 忽略规则覆盖，可在本机查看，未改.gitignore、未提交/推送。实现时不要 `git add -A` 或清理旧产物。

## 12. 本轮复现查询、风险与唯一下一步

本轮只读查询包括git status/diff摘要、Get-Content/rg源码与日志、readelf/nm现有ELF、gcc/objcopy版本、匹配libgcc路径、Get-FileHash Echo两份DAT以及Python依赖查询。默认沙箱命令环境启动报helper_unknown_error，获准使用可启动的环境完成只读核对；没有将工具环境失败误记为工程测试FAIL。

已有DDR基础证据复现入口（本轮未执行）：

```powershell
Set-Location D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_sim.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'
```

两条须在同目录依次运行，检查对应PASS、无FAIL、Errors0；不能只看进程退出0。Echo `sim/uart_echo/run.py` 直接读已有DAT、不自动重建，CoreMark `sim/coremark/run.py` 有昂贵Full Boot，文档调查不需要重跑它们。

主要风险是：误把数据RAM当可取指RAM；ROM中的C常量经数据口读错；KEY0不重新装载可变RAM初始化；16-byte FIFO在CPU停顿时溢出；错误包/整数溢出写坏栈；BIN地址/entry/BSS身份缺失；VERIFY前或LOAD后误跳转；FENCE.I非法；DDR硬件永不应答时软件无法超时；当前配置/生成初始化/已下载位流对应性丢失。第一版以固定ROM、片内RAM工作区、低64KiB DDR、固定入口、分块停等、CRC与状态机限制降低这些风险。

**方案确认后的下一步唯一动作：建立独立 `tests/uart_loader`/`sim/uart_loader` 最小ROM常驻候选，先验证ROM取指、RAM常量/BSS/Loader栈及重复复位，再完成PING/ACK验收；不加入LOAD、CRC整镜像或RUN。** 此最小步骤不改主IP/当前位流，先仿真形成可审查产物，通过后才推进下一层。
