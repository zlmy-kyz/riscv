# CoreMark 跑分操作

更新日期：2026-10-10。适用于已经完成六轮实板验收的主工程 Loader 位流，CPU 主频为 93.75 MHz，串口为 COM11、115200 8N1。

当前可以直接下载已成功的 `performance_60` 程序进行正式跑分。程序通过 UART 写入 DDR 后执行；不需要重新编译 C、生成 DAT 或生成 FPGA 位流。上板、供电、KEY0 和串口测试由用户操作。

## 1. 准备板子

1. 确保板子运行 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`。如果已经运行该位流，不需要重新上板；如果断电后 FPGA 配置丢失，先重新下载该位流。
2. 关闭串口助手及其他占用 COM11 的程序。
3. 按下并释放 KEY0，等 DDR 初始化完成，再执行下面的命令。单应用命令不会提示等待按键，需要执行前自行复位。

本说明对应的位流 SHA256：

```text
7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf
```

当前工具绑定这个位流及其冻结输入。若硬件、位流或被冻结的软件发生变化，需要建立新的候选和门控，不能跳过哈希检查。旧隔离位流使用另一套入口，不与本文的工具或 CRC 日志混用。

## 2. 直接进行正式跑分

在 PowerShell 执行，当前目录不限：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tools/uart_loader/candidates/rebuilt_20261010/run_board.py `
  --application performance_60 `
  --log D:/riscv/RISCV/sim/bsp_workflow/rebuilt_20261010/board/score_01.json `
  --crc-log D:/riscv/RISCV/sim/bsp_workflow/rebuilt_20261010/board/first/round_03_performance_1.json
```

`--crc-log` 引用本位流已经通过的 performance 单迭代算法 CRC 实板日志，无需重复六轮验收。工具自动完成 `LOAD → DDR CRC32 VERIFY → RUN → 检查 CoreMark 输出 → 保存 JSON`；下载时间另计，正式计算约 18 秒。

成功时应看到：

```text
Correct operation validated. See README.md for run and reporting rules.
RESULT: PASS COREMARK_FORMAL_BOARD_PASS same Loader bitstream
```

这是当前工程工具的正式运行验收结果，不表示已完成外部成绩提交或认证。正式验收要求算法 CRC 正确、计时至少 10 秒且没有 ERROR；`performance_1` 只检查算法 CRC，不作正式成绩。

## 3. 读取精确分数

轻量打印函数仅输出整数，所以串口可能显示 `Iterations/Sec : 3` 和 `Total time (secs): 17`。精确值保存在 JSON 的 `application.parsed` 中：

```powershell
$scoreLog = Get-Content -LiteralPath D:/riscv/RISCV/sim/bsp_workflow/rebuilt_20261010/board/score_01.json -Raw | ConvertFrom-Json
$scoreLog.board_result
$scoreLog.application.parsed | Select-Object mode, iterations, ticks, seconds, iterations_per_second, formal_benchmark
```

通过条件为 `board_result = COREMARK_FORMAL_BOARD_PASS`，且 `formal_benchmark = True`。`iterations_per_second` 是精确分数，单位为 iterations/s：

```text
运行秒数 = ticks / 93750000
分数 = iterations / 运行秒数
```

当前主工程位流的既有成功基准如下；这是已完成验收的结果，不是执行上述新命令后必然相同的数字：

| 项目 | performance_60 基准 |
| --- | --- |
| CPU 主频 | 93.75 MHz |
| 编译配置 | GCC 15.2.0，-Os，RV32I / ILP32，无 LTO |
| 迭代次数 | 60 |
| ticks | 1664064755 |
| 计时 | 17.750024053 秒 |
| 分数 | 3.380277109 iterations/s |
| final CRC | a14c |

原始基准日志：`D:/riscv/RISCV/sim/bsp_workflow/rebuilt_20261010/board/first/round_05_performance_60.json`。不要用工具下载总耗时或手动秒表代替 CoreMark 内部计时。

## 4. 再跑一轮或重新检查短 CRC

每次运行前重新按 KEY0 并等待 DDR 初始化完成。第二次正式跑分沿用第 2 节命令，把 `--log` 改为 `score_02.json`，之后继续使用未存在的新文件名。工具拒绝覆盖已有日志，原来的 `first/` 和成功快照保留。

如果需要本次重新进行短 CRC 检查，先复位，再执行：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tools/uart_loader/candidates/rebuilt_20261010/run_board.py `
  --application performance_1 `
  --log D:/riscv/RISCV/sim/bsp_workflow/rebuilt_20261010/board/score_crc_01.json
```

短 CRC 通过标志为 `RESULT: PASS COREMARK_CRC_FUNCTIONAL_PASS`。单迭代输出允许出现“必须运行至少 10 秒”的 ERROR 和 `Errors detected`，因此以工具检查所有预期算法 CRC 后给出的功能 PASS 为准；不能将它记作正式跑分 PASS。

短 CRC 通过后，再次 KEY0 复位、等待 DDR 初始化，将第 2 节的 `--crc-log` 改为刚生成的 `score_crc_01.json`，并使用新的正式输出日志名。

## 5. 常见情况与文件位置

| 情况 | 处理 |
| --- | --- |
| COM11 被占用 | 关闭串口助手和其他串口进程后重测 |
| 提示日志已存在 | 换一个新的 `--log` 文件名，保留原日志 |
| 超时或启动收到意外字节 | 保留失败日志，核对位流和接线；重新 KEY0 后用新日志名测试 |
| CRC 前置日志被拒绝 | 使用同一模式、同一位流及门控的实际单迭代成功日志；不能用 validation 日志替代 performance 日志 |
| 冻结输入或位流哈希不一致 | 停止使用该门控，核对变更，另建候选验收 |
| 正式运行不足 10 秒或算法 CRC 错误 | 不计作有效成绩；性能优化后若 60 次不足 10 秒，需要另行构建更多迭代的新程序并验收 |

关键文件均位于 `D:/riscv/RISCV/`：

| 路径 | 用途 |
| --- | --- |
| coremark-main/ | 保留原始 CoreMark 算法源码 |
| tests/bsp_workflow/core_portme.c、core_portme.h、ee_printf.c | 当前 BSP 的 CoreMark 计时、配置和输出端口 |
| tests/bsp_workflow/build/performance_60/program.bin、manifest.json | 已成功的正式程序与镜像清单，工具自动选择 |
| tests/uart_loader/candidates/verify_run_hello/build/loader_rom.dat、loader_ram.dat | 当前位流使用的常驻 Loader ROM/RAM 镜像 |
| tools/uart_loader/candidates/rebuilt_20261010/run_board.py | 本位流的 PC 下载与测试入口，内部固定 COM11 |
| sim/bsp_workflow/rebuilt_20261010/deployment_gate.json | 位流、应用及工具输入身份检查 |
| sim/bsp_workflow/rebuilt_20261010/board/ | 新跑分日志及既有成功证据 |

进一步查看：[tests 总说明](README.md)、[主工程新位流实板验收](../doc/board/主工程新位流六轮实板验收_2026-10-10.md)、[CPU 性能优化约定](../doc/CPU性能优化起点与验收约定_2026-10-10.md)。
