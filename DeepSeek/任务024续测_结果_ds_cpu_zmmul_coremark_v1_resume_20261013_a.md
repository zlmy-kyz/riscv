# 任务024续测 结果：只补 V1、复用 P1 —— PASS（tag ds_cpu_zmmul_coremark_v1_resume_20261013_a）

**结论：`PASS`，`functional_status=P1_REUSED_V1_NEW_P_V_SHORT_CRC_PASS`。**
本次只执行 `validation_1` **一次**，复用原 024 编译库与 P1 原始功能证据；**未重跑 P1**、未重跑 vlib/vlog、未跑 023/ISA/旧版/120 或 300 全仿真、未重建软件、未碰 PDS/串口/板子/Git。V1 vsim 实际耗时 **1321.17 s（22:01）**，上限 3600 s，`exit_code=0`、`native_exit_after_wait=0`、`timed_out=false`。

## 1. 唯一入口与实际命令

```powershell
python -B sim/cpu_zmmul/resume_coremark_v1.py --check-inputs
# 退出 0：INPUTS_MATCH_V1_ONLY_NOT_SIMULATED; reused compile/P1; timeout=3600s; 300 software ready
python -B sim/cpu_zmmul/resume_coremark_v1.py --start --tag ds_cpu_zmmul_coremark_v1_resume_20261013_a
# 退出 0：STARTED V1 worker pid=44368; use --status; do not start again
```

- 启动前：固定 tag 目录**不存在**（未换 tag/未清理）；无 `pds_shell` 实现进程（仅剩空闲的 PDS GUI，pid 33648，起始 2026-10-11）；无既有 `vsim/vsimk` 会话。
- `--start` 按设计**立即返回**并派生子进程（`worker_launch.json`：pid 44368、`stdout_native_to_file=true`、`parent_returns_without_wait=true`、`simulation_timeout_seconds=3600`；`worker_entered.json` 同 pid）。查询用 `--status`，间隔约 45 s，未忙轮询、未在 60 秒后杀后台、未重启。

V1 实际 vsim 命令（`validation_1/simulation.command.json`，cwd=`validation_1`）：

```text
vsim.exe -batch -lib <新tag>\work tb_coremark_zmmul
  +ROM=D:\riscv\RISCV\tests\uart_loader\candidates\verify_run_hello\build\loader_rom.dat
  +DAT=D:\riscv\RISCV\sim\cpu_zmmul\fixtures\coremark_validation_1.dat +DONE=40000080
  +OUT=<新tag>\validation_1 +MAX_CYCLES=60000000
  +HOT_PC_FILE=D:\riscv\RISCV\sim\cpu_zmmul\fixtures\coremark_validation_mul_pcs.hex
  -logfile <新tag>\validation_1\transcript -do "run -all; quit -f"
```

| 项目 | 值 |
| --- | --- |
| exit_code / native_exit_after_wait | 0 / 0 |
| seconds | **1321.17 s**（ModelSim `Elapsed time: 0:22:01`） |
| timeout_seconds / timed_out | 3600 / **false** |
| cleanup | null（未发生超时清理） |

## 2. V1 原始证据

`validation_1/simulation.log` 关键尾部（`transcript` 换行归一后与之相同，5621 / 5562 字节）：

```text
# run -all
# IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
# IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
# RESULT: PASS coremark_zmmul_direct cycles=11085406 retired=4275052 AR=72198 AW=21363 UART=1121 MUL=9618 MATRIX_MUL=9396
# ** Note: $finish    : D:/riscv/RISCV/sim/cpu_zmmul/tb_coremark_zmmul.v(104)
#    Time: 118237044234 ps  Iteration: 0  Instance: /tb_coremark_zmmul
# End time: 15:17:51 on Oct 13,2026, Elapsed time: 0:22:01
# Errors: 0, Warnings: 0
```

计数：唯一 `RESULT: PASS coremark_zmmul_direct` = 1；`RESULT: FAIL`/`** Error|Fatal`/`RPC_Init`/`RUNNER TIMEOUT` = **0**；`04030130` = **2**；`Errors: 0, Warnings: 0` = 1；`$finish` = 1。`worker.log` 全文：`RESULT: PASS V1-only continuation; P1 reused; Zmmul300 ready for user board`。

## 3. UART 实解与 CRC（`validation_1/uart.txt`，1121 字节 = TB 报告 UART=1121）

```text
2K validation run parameters for coremark.
CoreMark Size    : 666
Total ticks      : 1842118
Total time (secs): 0
ERROR! Must execute for at least 10 secs for a valid result!
Iterations       : 1
Compiler version : GCC15.2.0
Compiler flags   : -Os -march=rv32i_zmmul -mabi=ilp32; no LTO
Memory location  : DDR code/data; static 2000-byte buffer
seedcrc          : 0x18f2
[0]crclist       : 0xe3c1
[0]crcmatrix     : 0x0747
[0]crcstate      : 0x8d84
[0]crcfinal      : 0xe3c1
Errors detected
PORT_DONE ticks=1842118 iterations=1 hz=93750000
PERF2B version=1 state=3 start=87238 stop=1929356
PERF2B cycles=00000000001C1BC6
... （13 项冻结计数，截断显示）
PERF2B_DONE
```

- **五项 CRC 逐字符合要求**：`18f2 / e3c1 / 0747 / 8d84 / e3c1`；flags `rv32i_zmmul`；`iterations=1`；`hz=93750000`；`state=3`；`PERF2B_DONE` 存在。
- 算法自身的 `ERROR! Must execute for at least 10 secs…` 与 `Errors detected` 是**短 CRC 时长提示**（`formal_benchmark=false`、`duration_requirement_met=false`），按任务口径**不算算法失败、也不作性能证据**。
- **计数守恒（我独立核对）**：`stop-start = 1929356-87238 = 1842118` = `ticks` = `cycles`；七分类 `382038+923086+128817+0+0+0+408177 = 1842118` = `cycles`；`ddr_transactions 83602 = AR 66429 + AW 17173`；`MUL=9618>0`、`MATRIX_MUL=9396>0`。

## 4. P1 复用与旧编排证据边界

- 原 tag `ds_cpu_zmmul_coremark_crc_20261013_a` **未被修改**：其 `result.json` 仍为 `RUNNING`、`completed` 为空、**无 `git_after.json`**、**P1 `simulation.command.json` 不存在**；本次未补造旧 command/git、未改旧 result。
- P1 原始证据仍在并被复核：`performance_1/` 的 `simulation.log`、`transcript`、`uart.txt` 均在，P1 结果行
  `RESULT: PASS coremark_zmmul_direct cycles=11087686 retired=4278641 AR=71615 AW=21438 UART=1122 MUL=9618 MATRIX_MUL=9396`，CRC `crcfinal=e714`（performance）。
- `original_observation.json` 如实记录：**原 P1 原生退出/完整编排状态 UNKNOWN，未重建**；已知旧工作树差异 `ipcore/mul/.settings`（旧 `git_before` 之后新增）已纳入本次基线。
- 因此新软件功能结论 = **P1 原始功能证据复用 + V1 本次验证**；**不能**标称旧 runner 整套原生执行 PASS。

## 5. 输入、库副本与 Git 守恒

- 新清单 `sim/cpu_zmmul/coremark_v1_resume_inputs.json` SHA256 `119e0853d69fa4aac1a55bbf36c226c9b53a59393a5053796d9b8362f2e1632a`，与 Codex 收据 `build/preparation_20261013_a/v1_300_static_review.json` 中记录的 `manifest_sha256` **一致**（该收据状态 `V1_ONLY_CONTINUATION_AND_ZMMUL300_STATIC_PREPARATION_PASS_HDL_NOT_RUN`）；原清单仍 `ca07e018…47605` 未被刷新。
- 编译库整体从旧 tag 复制到新 tag 的 `work/`，runner 对 `original_artifact_sha256` 内每个旧文件逐份 SHA 核对；我另抽样核对 `_lib1_0.qpg` 新旧哈希相同。
- `new_inputs/` 归档 **67 份**新增续测/300 软件/工具文件；`git_before.json` 与 `git_after.json` 内容哈希相同，HEAD `7af48d2185bc01a62be528c70b83c42689394c31`；执行后无残留 `vsim/vsimk/python` 进程。

## 6. 新功能门与 300 软件身份

`software_gate.json`（SHA256 `cb94c1e36eac70b4ce1af4856b95f7f21000982faf69e39b2fea5aef48447eca`）：

- `status = ZMMUL_P_V_SHORT_CRC_GATE_PASS_300_READY_FOR_USER_BOARD`，`formal_benchmark=false`，`board_300=NOT_RUN`，`serial_opened=false`，`PDS_started=false`；
- 位流身份 `bitstream_sha256 = 64445ecf1e72d11eef96c0e488053d77e0ef74f978d22b040861803831ac8ee4`（与工作树 `generate_bitstream/board_top.sbit` 实测一致，即用户已下载的 I64/D64+Zmmul 位流）；
- 300 软件 BIN：P300 `677ee766fd0fc34d1558d778a343743a1cd9287ecdbbc182cb4681af3374517d`（15204 byte）、V300 `461c635c46c86c8e719ced403b045bca468ded7299870bf2f87f8547ce11719b`（15212 byte），与任务书一致。
- **300 迭代软件只做了构建与离线静态验证，未跑 HDL、未上板**；本轮 DeepSeek 未执行 Codex 的 `review_coremark_v1.py`、未开串口。

## 7. 未覆盖范围与边界

- 仅 `validation_1` 一次；未重跑 P1、未跑 120/300 全仿真、未跑 023/ISA/旧版/Hello/PHY/工具预检。
- **不满足正式 CoreMark 成绩条件**（1 次迭代、约 0.0196 s < 10 s）：本轮只是**短 CRC 功能证据**，不能作为性能成绩，也不能与实板秒数直接比较。
- 不代表 SoC/DDR PHY/时序/资源/实板性能 PASS；未执行 PDS 实现、未开串口/上板、未提交或推送 Git。
- 旧编排的 P1 原生退出仍为 UNKNOWN；旧 tag 的缺失文件保持缺失，未补造。

## 8. 交接给用户/Codex

1. Codex 按计划运行只读 `review_coremark_v1.py` 核原始证据并生成 `codex_review.json`；**DeepSeek 不执行该审查**。
2. 新 300 板级工具要求“续测功能门 + Codex 收据”均存在且身份匹配，否则不应开跑。
3. 用户侧仍用**已下载的同一位流**、COM9，每模式 KEY0 → 等 DDR 就绪 → Enter，仅 P300/V300 各一次，123 响应 + 唯一 RUN，新日志目录 `sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul`；比较用 cycles/iteration 与 iterations/second 并披露迭代数差与初始化摊销，低于 10 秒仅作比较，不擅自增迭代或重跑。

原始产物路径：`sim/cpu_zmmul/build/ds_cpu_zmmul_coremark_v1_resume_20261013_a/`（`result.json`、`worker_launch/entered.json`、`worker.log`、`validation_1/{simulation.log,transcript,uart.txt,simulation.command.json,crc_review.json}`、`original_observation.json`、`software_gate.json`、`inputs.json`、`new_inputs/`、`git_before/after.json`、`work/`）。
