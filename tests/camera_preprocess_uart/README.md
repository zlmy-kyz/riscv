# 预处理96RGB888 两组实板固定程序（Camera ABI2 + PP + PP01 串口导图）

2026-10-15。目录 `tests/camera_preprocess_uart/`。本文件是**程序与离线审计**记录：
本目录**未打开串口、未跑 PDS、未生成 `board_release.json`、无任何实板/PASS 结论**。
方案与判据见 `DeepSeek/预处理96RGB888_逐字节参考与串口导图测试_2026-10-15.md` §6/§7，
寄存器合同见 `doc/camera/OV5640预处理96RGB888与DDR接口_2026-10-15.md` 与
`doc/camera/OV5640双缓冲所有权与CPU并发读取_2026-10-15.md`。
串口字面合同对齐已存在的对端 PC 工具 `tools/camera_preprocess_uart/protocol.py`
（比对时 SHA256 `d6cc91160efb353cfa1b856a2fbfacc34a09b6549def89bb582b3beb197d0909`）。

## 1. 固定身份与审计数字

| 项 | 值 |
|---|---|
| 构建标签 | `pp_uart_20261015_a`（对端工具默认清单路径就是该目录） |
| BIN | `build/pp_uart_20261015_a/program.bin`，**18952 字节** |
| BIN SHA256 | `ba081126d0acc68c246d36e0e355a9e250a1a36418e94547227bcd4e86c0ca98` |
| Loader CRC32 | `be9e0c92` |
| ELF / DAT | `program.elf` / `program.dat`（DAT 由 BIN 4 字节补齐后按 32bit 小端十六进制逐行写出，已做读回比对） |
| 段 | `.text` 15572 @40000000、`.rodata` 3376、`.data` 4、`.bss` 2276（NOLOAD） |
| 入口/复位 | 0x40000000，`sp` 由启动代码 `la sp,__stack_top` 设置（sp_auipc pc=0x40000010 → 0x40010000） |
| 栈 | 独立 4KiB `4000F000–40010000`；单函数最大静态帧 176 字节（`main`）；**静态最大栈深 352 字节**（`_start→main→cam_claim→fail→dec→__umoddi3`，.su 与反汇编逐函数一致，51 条调用边，无环） |
| 指令 | RV32I 合法指令 3893 条（审计逐字校验；反汇编中 F/D/M 扩展指令 0 条） |
| Loader | 复用既有 Loader 计划/VERIFY/唯一 RUN；`run.py --plan-only` 对该清单给出 153 条 Loader 应答、RUN=1、`serial_opened=false`；**不改 ROM/RAM 初始化**（本目录只产出 DDR 镜像 BIN/DAT） |

可复现命令（唯一入口，不打开串口、不启动 PDS）：

```powershell
python tests/camera_preprocess_uart/build.py            # 默认 --tag pp_uart_20261015_a
python tools/camera_preprocess_uart/run.py --plan-only  # 只读身份/Loader 计划检查
```

`build/<tag>/` 内保存：`program.elf/bin/dat`、`compile/objcopy/readelf/disassembly/symbols/size`
的完整日志与 `*.command.json`（argv+cwd+returncode）、`*.su` 与 `stack_usage.log`、
`stack_depth.json`、`native_check.json`、`native/` 主机交叉检查日志与样例、`manifest.json`
（含全部源码/工具 SHA256）。已存在的 tag 目录一律拒绝覆盖。

两次准备失败目录原样保留：`build/prep_fail_20261015_a/`、`build/prep_fail_20261015_a_r2/`
（各自 `FAILURE_NOTE.txt` 说明失败点；都是测试侧脚本缺陷，修复后换新构建名，未倒填）。

## 2. 范围与适用边界

- **首版只有两组**成对采图：第 1 组取源 A（0x41000000），第 2 组取源 B（0x41200000），
  两次共用同一输出窗口 0x42000000，覆盖输出地址复用与 DDR 不复用旧数据。
- 不沿用 ABI1 程序；不做 100 帧循环、不接 CNN/INT8 量化、不做双目/缩放。
- 只有一份输出张量：第 2 组 START 会覆盖第 1 组输出，程序保证第 1 组导出与核对全部结束后
  才进入第 2 组。
- 本程序不执行 ABORT、不执行 CLEAR、不重拍、不重试、不重同步、不清错。
- 适用边界：**未上板**（无实板证据）、**未接 CNN**、未做实板 Full Boot/PHY 验收；
  这里只有离线构建与静态/主机审计。

## 3. 每组流程（两组相同，目标缓冲不同）

1. 前置：两块 FREE、无采集在飞、流已停、无错误（`BUFFER_STATE & 0x2ef == 0`，STATUS busy/stream 为 0）。
2. `STREAM_START`(CTRL=8)，回读确认 STATUS bit5/bit6 置位。
3. 轮询目标块进入 READY；`SELECT=目标` → 读 `FRAME_SEQ/FRAME_BYTES/PIXELS/BEATS/FRAME_BASE`
   （校验 1843200 / 921600 / 57600 / 0x41000000 或 0x41200000）→ 写 `EXPECTED_SEQ` →
   `CLAIM`(CTRL=0x20) → 复核该块为 CPU。**不假设两组 SEQ 连续**，只核对被选块的 token。
4. `STREAM_STOP`(CTRL=0x10)，等待 STOP 排空（`BUFFER_STATE` bit6 busy 与 STATUS bit1 同时为 0）。
5. 启动 PP：写 `SOURCE_BUF=目标`、`EXPECTED_SEQ=seq`、`CTRL=1`；随后核**源锁与状态**：
   PP STATUS busy=1、PP `SOURCE_BUF` 仍为目标、Camera 该块仍为 CPU(=3)、Camera 无错误。
6. 等待 DONE/ERROR（软件 5s 上限）；核 `RESULT_BUF/RESULT_SEQ/OUTPUT_BASE=42000000/
   OUTPUT_BYTES=27648/OUTPUT_SIZE=00600060/READ_BEATS=9216/WRITE_BEATS=864/
   PRODUCED_BYTES=27648/ERROR_CODE=0`。
7. CPU 独立整数参考：从**仍持有的同一源**按坐标公式取 9216 个 RGB565，逐像素位复制展开，
   与输出 27648 字节**逐字节比较**并算 expected CRC；另做一次输出全量复读 CRC。
8. CPU 源全帧 CRC 与 Camera 冻结 `FRAME_CRC32` 核对。
9. 打印冻结的 `PP_GROUP=...` 摘要行（其中 `CRC_PP=CRC_CPU=CRC_REREAD`，三者已核对相等）。
10. 收到 `D` 后：`PPX_BEGIN` → 源流（kind1 DATA×1800 + kind2 END）→ RGB888 流
    （kind3 DATA×27 + kind4 END）→ `PPX_DONE`；每个完整包等待一个 `K`。
    源 END 的 data_crc 为整帧 CRC，RGB888 END 的 data_crc 为 27648 字节 CRC（=PP 硬件 CRC）。
11. 导出与 ACK 结束后：`RELEASE` 释放源（正确 token）→ 排空**非选定/STOP 尾帧**
    （逐块 `SELECT`→读 SEQ→`CLAIM`→记账 DISCARD→`RELEASE`）→ 复核 Camera 空闲/全 FREE、
    PP 有效输出身份不变 → 核发布/丢弃账本闭合（`GLOBAL_SEQ == 本轮 CLAIM 总数`）。
12. 两组结束后收到 `Q`：再做全局账本与 Camera 终态检查，打印 `PPX_SESSION_DONE GROUPS=2 CPU_CHECK=PASS`，
    写 `TEST_STATUS=2` 并停机（`PPX_SESSION_DONE` 之后不再输出任何字节）。

## 4. 寄存器合同（程序实际使用/核对）

Camera ABI2（0x10002000，ID 必须 0x43414d02）：`0x04 CTRL`（只写 8/0x10/0x20/0x40 单命令）、
`0x08 STATUS`、`0x0c FRAME_BASE`、`0x10 FRAME_BYTES`、`0x14 FRAME_SEQ`、`0x18 PIXELS`、
`0x1c ERROR_CODE`、`0x20 SENSOR_ID`（核 0x5640）、`0x24 WRITTEN_BEATS`、`0x28 FRAME_CRC32`、
`0x2c SELECT`、`0x30 BUFFER_STATE`、`0x34 GLOBAL_SEQ`、`0x38 EXPECTED_SEQ`。
写 `SELECT/EXPECTED_SEQ` 只在 `DUAL_MODE=1` 时进行（否则会触发 access fault）；
`CLAIM` 先核该块 READY 且 `EXPECTED_SEQ==FRAME_SEQ`，`RELEASE` 先核该块 CPU 且 token 匹配，
避免任何非法命令副作用。

预处理 MMIO（0x10003000，ID 必须 0x50525001）：`0x00 ID`、`0x04 CTRL`（只写 1 START，不写 2/4）、
`0x08 STATUS`、`0x0c SOURCE_BUF`、`0x10 EXPECTED_SEQ`、`0x14 RESULT_SEQ`、`0x18 OUTPUT_BASE`、
`0x1c OUTPUT_BYTES`、`0x20 OUTPUT_CRC32`、`0x24 ERROR_CODE`、`0x28 READ_BEATS`、
`0x2c WRITE_BEATS`、`0x30 PRODUCED_BYTES`、`0x34 CYCLES`、`0x38 OUTPUT_SIZE`、`0x3c RESULT_BUF`。
配置写只在 `!BUSY` 时进行。

输出窗口 0x42000000–0x4200ffff 无缓存/不可执行：程序只在 DONE 后读取 27648 个有效字节，
从不写输出窗口、不在 DONE 前读取、不读有效长度之外；源帧区只在 CPU 拥有期间读取。

## 5. 串口协议与字面合同

32 字节头，全部 uint32 小端：`magic[4]='PP01'`、`kind`、`source_seq`、`offset`、`payload_len`、
`total_len`、`data_crc`、`header_crc=CRC32(header[0:28])`（反射 IEEE/zlib，初值 ffffffff、
多项式 edb88320、末取反；与本目录 `pp01_wire.c` 同一份实现，已在主机上与 zlib 逐记录对齐）。
`kind`：1 源 DATA、2 源 END、3 RGB888 DATA、4 RGB888 END；`total_len` 源 1843200 / RGB888 27648；
DATA `payload_len=min(1024,total_len-offset)`；END `payload_len=0` 且 `offset=total_len`；
END 的 `data_crc` 为整条流 CRC，DATA 的 `data_crc` 为该 payload CRC。
每个完整有效包（含 END）与 PC 之间恰好一次 `K`；源与输出流不交错，顺序固定 源→输出。
ASCII 边界行只有 `PPX_BEGIN`（导出块前）与 `PPX_DONE`（导出块后），逐包不带任何 ASCII 行。

与 PC 工具的字面握手（字节精确）：

```
PP_APP=1 ID=50525001 HZ=93750000 TARGET=2 WIDTH=1280 HEIGHT=720 OUT=96x96\n
SENSOR_ID=00005640 CONFIG=OK\n
PP_READY\n
                          <-- PC 发 'G'
                          <-- PC 发 'C'
PP_GROUP=<g> BUF=<0|1> SEQ=<seq> SRC=<0|1> SRC_SEQ=<seq> LAYOUT=1280x720x2 SRC_CRC=<8h> SRC_BYTES=1843200 BASE=42000000 BYTES=27648 SIZE=00600060 READ=9216 WRITE=864 PRODUCED=27648 CRC_PP=<8h> CRC_CPU=<8h> CRC_REREAD=<8h> ERR=00000000\n
                          <-- PC 发 'D'
PPX_BEGIN\n
<32 字节头 + payload，每包后 PC 发 'K'>（kind1 ×1800, kind2, kind3 ×27, kind4）
PPX_DONE\n
（第 2 组重复 'C' → 摘要 → 'D' → PPX_BEGIN/数据/PPX_DONE）
                          <-- PC 发 'Q'
PPX_SESSION_DONE GROUPS=2 CPU_CHECK=PASS\n
```

`build.py` 会把 `protocol.py` 的上述冻结字面量与 `main.c` 中实际发出的字符串做静态比对
（含摘要行去掉占位符后的完整串、4 个单字节命令、PP01 magic 与 6 个头部字段顺序、
DATA/END 的 payload/offset 规则、每包恰好一次 ACK、源流先于输出流），不一致则构建失败。
正常通路下除上述行以外**不输出任何多余字节**（对端重放要求会话结束后 RX/TX 无剩余字节）。

`SRC_CRC` 语义：源整帧 1843200 字节的 CRC32，等于 Camera 冻结 `FRAME_CRC32`，也等于 CPU 侧
独立计算的整帧 CRC；它**不等于** 27648 字节输出的 CRC，本程序不把输出 CRC 写进该字段。

## 6. 固定超时（运行期不延长）

| 阶段 | 上限 |
|---|---|
| `CONFIG_DONE`（SCCB 配置） | 5s |
| Camera 目标帧 READY / STOP 排空 | 5s |
| PP 正常 DONE | 5s |
| CPU 校验（逐字节比较 + 输出复读 + 源整帧 CRC，各自循环内检查） | 20s |
| 每个完整包的 `K` ACK | 5s |
| 每个 UART 发送字节等待 TX_READY | 5s |
| 自动命令等待（`G`、第 1 组 `C`、`D`、`Q`） | 30s |
| 第 2 组 `C`（对端在用户改画面确认后才发，故窗口放宽） | 600s |
| PC 侧读一行（对端 `LINE_SECONDS`） | 30s |

所有 deadline 使用 93.75MHz CYCLE 的**软件 64bit 扩展**（每次读取累加 32bit 差值），
整图导出跨 32bit 回绕时依然正确；导出循环按 1024 字节块至少采样一次，远小于回绕周期。

## 7. 失败策略

首败即停：打印一行 `PP_FAIL REASON=... GROUP/BUF/SEQ/CLAIMS/TARGET_CLAIMS/DISCARD_CLAIMS/
LAST_DISCARD/CAM_STATUS/CAM_ERR/CAM_BUFSTATE/CAM_GLOBAL_SEQ/PP_STATUS/PP_ERR/UART_STATUS/
ELAPSED_TICKS=...`，写 `TEST_STATUS=3`，停机。字节不匹配时先打印
`PP_MISMATCH X/Y/CHANNEL/EXPECTED/ACTUAL/SX/SY/SOURCE_BYTE`。CPU trap 打印
`PP_TRAP CAUSE/PC/TVAL` 后同样首败停机。程序不自动 ABORT/重拍/重试/重同步/清错；
`PP_FAIL` 打印过程中若 TX 再超时则丢弃该字节（`failing` 保护），不再递归。
DDR 读本身挂起时（源/输出区读不返回）不承诺还能打印诊断，原始超时门限仍然保留。

## 8. 发布/丢弃账本与“不能把 READY 当 FREE”

- 每组只把目标块作为 PP 输入；非选定帧与 STOP 尾帧必须走 `SELECT→读SEQ→EXPECTED_SEQ→
  CLAIM→（记账 DISCARD）→RELEASE`，每块一次，绝不直接当 FREE，也不留到下一组混用。
- 程序维护 RAM 账本：全部 CLAIM 的 (BUF,SEQ)（上限 16，重复或溢出即失败）、目标/丢弃分类计数。
  每组导出后与最终都要求 `GLOBAL_SEQ == CLAIM 总数`，且两块 FREE、无 busy、流已停；
  第 2 组还要求目标 CLAIM 恰好 2 次。`PPX_SESSION_DONE` 只在全部闭合检查通过后才打印。
- **线序约束（重要）**：对端 `protocol.py`/`session.py` 的冻结行序在通过路径上不允许任何
  额外 ASCII 行（`'C'` 后恰好 1 行摘要、`'D'` 后恰好 1 行 `PPX_BEGIN`、二进制块后恰好 1 行
  `PPX_DONE`、`'Q'` 后恰好 1 行会话行，且结束后 RX/TX 无剩余字节）。因此 DISCARD 记录不能
  作为独立日志行出现在正常通路；本实现把 DISCARD 语义放在“必须实际执行并校验的 CLAIM/
  RELEASE 动作 + RAM 账本 + 失败诊断 + 账本闭合前置条件”里，并在 README 与 manifest 中
  明示该取舍，等待 Sol 裁定是否需要独立的线上 DISCARD 行（若需要，必须同时改对端行序）。

## 9. CPU 独立参考（与输出数据无关）

- 采样坐标严格整数：`sx = 280 + ((2x+1)*15)/4`、`sy = ((2y+1)*15)/4`（整数除），
  源字节偏移 `2*(sy*1280+sx)`；第一点 (283,3)、最后一点 (996,716)。
- 像素读取：按 `offset & ~3` 取一个小端 32bit 字，用 `offset bit1` 选高/低 16bit
  （与 RTL `source_addr[4:1]` 选择一致，不依赖子字 DDR 访问）。
- 展开只用位复制：`R=(r5<<3)|(r5>>2)`、`G=(g6<<2)|(g6>>4)`、`B=(b5<<3)|(b5>>2)`；
  **无浮点、无四舍五入、无缩放库**（`-march=rv32i`，反汇编 0 条 F/D/M 指令）。
- expected 只来自源 + 公式：不用输出字节、不用 PP 计数器/选址、不做 CRC 反推。
- 逐字节比较 27648 字节；同时得到 expected CRC、输出全量读 CRC、输出复读 CRC，并与 PP
  硬件 CRC 四者相等才打印摘要；源整帧 CRC 另与 Camera 冻结 CRC 相等。

## 10. “实板坐标参考函数在 native 上以固定图案逐字节核 Python 公式”

`preprocess_ref.c`（坐标+像素选择+位复制展开）与 `pp01_wire.c`（PP01 头+CRC表）**同一份源码**
既进 RV32I 镜像，也被主机 `native_check.exe`（`native_check.c`，**不进入镜像**）编译。
`build.py` 在构建时强制跑：

1. `--vectors`：边界与低位复制向量（0000→000000、ffff→ffffff、2104→33/65/33、
   0841→8/8/8、f800/07e0/001f/0001/0010）、首点 (283,3)、末点 (996,716)、列步长 {7,8}。
2. `--ref`：5 个全尺寸固定图案（k=1 非对称、k=2 非对称、纯红 f800、纯绿 07e0、纯蓝 001f），
   每个图案逐像素核 `x,y,sx,sy,offset,pixel` 坐标表与 27648 字节展开，
   与 `build.py` 按文档 §2 独立实现的 Python 公式**逐字节比较**，任一不一致即构建失败。
3. `--wire`：固定 10 条记录覆盖 kind1–4、offset 0/512/1024/total-1024、seq 回绕值、
   1024/0 字节 payload；核固件 CRC == `zlib.crc32`、固件 32 字节头 == 对端
   `protocol.build_header(...)`、`header_crc == CRC32(header[0:28])`、字段偏移与 magic。

即：实板程序里那份坐标/展开代码，已经在 native 上以固定图案逐字节核对过 Python 公式；
这**不是**用硬件输出充当参考，也不是仿真宏替换。

## 11. 内存与启动约束

- 复用既有 Loader（`tools/uart_loader/candidates/bsp_workflow`）与既有启动/链接的只读副本
  （`startup.S`、`linker.ld` 复制到本目录后未改布局）；不改 ROM/RAM 初始化 DAT。
- 代码/数据/BSS 位于 0x40000000 起 60KiB 应用边界内（.bss 结束 < 0x4000F000）；栈独立 4KiB
  `4000F000–40010000`，链接脚本带越界断言；静态最大栈深 352 字节，不覆盖源帧区
  （0x41000000–0x413fffff）、输出窗口（0x42000000–0x4200ffff）或 Loader 诊断区。
- 不把整图或输出拷到低 64KiB：只用 1024 字节 payload 缓冲 + 32 字节包头 + 288 字节行缓冲
  （复用同一 1024 字节缓冲）+ 1KiB CRC 表（`pp01_wire.c`）+ 小账本（≤16 项）。

## 12. 待 Sol 澄清的歧义

1. **`SRC_CRC` 与对端重放判据冲突**：`session.py::replay` 把摘要的 `capture_crc` 与
   `cpu_expected/cpu_reread/pp_hardware/pc_expected/pc_actual` 放进同一个集合要求全部相等
   （`len(set(closed.values()))==1`）。源整帧 CRC 与 27648 字节输出 CRC 在真实图像下不可能相等
   （对端自己的合成 transcript 也是 `crc32(src)` ≠ `crc32(expected)`）。本固件按 §6/§7 语义
   把 `SRC_CRC` 写成**真实源整帧 CRC**，因此该 replay 断言会在实板会话结束时拒绝通过。
   建议对端改为 `capture_crc == crc32(source_raw)`（源文件独立可验），输出 CRC 集合只含
   输出相关的五项。若 Sol 裁定必须让 `SRC_CRC` 等于 PP 输出 CRC，则语义变成“重复输出 CRC”，
   需要明确改名/改文档，固件侧只是一行改动。
2. **DISCARD 日志的线上形式**：见第 8 节，冻结行序不容纳额外行。是否需要为丢弃账本增加一条
   线上行（会同时改动对端解析）请裁定。
3. **第 2 组命令窗口**：对端在 `confirm()` 用户改画面之后才发 `'C'`，窗口不可预知；本程序用
   固定 600s（与对端 `GROUP_SECONDS=600` 同阶）而不是 30s。若要求统一 30s，需要把“改画面”
   提前到第 1 组导出期间完成并写进对端提示。
4. **`PP_CYCLES`/`WAIT_CYCLES` 等只读计数**未进摘要行（行格式已冻结），只在失败诊断中体现；
   若 Sol 需要把 PP CYCLES 纳入证据，需扩冻结摘要或另加离线读取通道。
5. **对端工具仍在演进**：`tools/camera_preprocess_uart/` 与本次比对时的文件 SHA 已记入
   manifest 的 `wire_contract_tools_sha256`；对端改名/改行序会使本目录的静态合同比对失败，
   此时应按新身份重跑 `build.py`（新 tag），不能改本目录的冻结产物。
