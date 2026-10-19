# 任务030续测 结果：LOAD激励修正与两项ISA补跑（tag `ds_cpu_branch_loaduse_resume_20261014_a`）

**状态：`STOPPED_FIRST_FAILURE`（首次非预期失败停止）。未重试、未清理、未换 tag、未补造缺失产物。
冻结输入/TB/oracle/阈值/原030现场与三诊断均保持。PDS/串口/上板/Git 提交未执行。**

- **key 首次正式 PASS**（激励修正生效）：九组 455 架构事件、12 项覆盖全部达标，`LOAD=3`。
- **`isa_auipc` 功能 PASS**（五条 trap 与冻结参考逐字段一致，tohost=1），但日志带 **2 条 vsim 端口警告**，
  被 `check_job` 的 `Errors: 0, Warnings: 0` 判据拦下，`run.py:40` 断言失败。
- **`isa_sb` 未派发**，`git_after.json` 未生成。

原始目录：`sim/cpu_branch_turnover/build/ds_cpu_branch_loaduse_resume_20261014_a/`
`result.json` = `STOPPED_FIRST_FAILURE`，`error` = `AssertionError: `
（`review_resume_loaduse.py` 属 Codex 审查入口，按要求未执行。）

## 0. 执行前核对

| 项 | 结果 |
| --- | --- |
| `loaduse_resume_inputs.json` SHA256 | `7cb5c88efd5564c271b981aae9a865b8433869496a43d10c39d48f84c2902ccd` ✔ |
| 原 `inputs.json` SHA256 | `e26f0bac…81dd08` ✔ 未刷新 |
| CPU `myriscv/mycpu_sync.v` | `b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3` ✔ 与 030 相同 |
| 新 tag 目录 | 执行前不存在 ✔ |
| `pds_shell` 并发 | 0 ✔（`pds.exe` PID 57664 为 0:37 起常开的图形界面、累计 CPU 77 s，非批处理实现） |
| `--check-inputs` | `INPUTS_MATCH_LOADUSE_RESUME_HDL_NOT_RUN key455/LOAD>0 ISA=auipc,sb control94 reused; RTL/TB/oracle unchanged`，exit 0 ✔ |

清单内旧/新 spec 逐字段比对由 runner 静态断言：九行中**只有第 5 行 `load_branch_jalr` 的 profile `1→0`**，
实际档位表 `[0,1,2,1,0,0,1,1,1]`；复用的原 control 证据被重新核过（94 事件 / 194 cycles / DROP_ERR=8）。

## 1. 命令 argv / exit / native / 时间 / 上限

| # | 命令 | 状态 | exit | native | 秒 | 上限 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 0 | `resume_loaduse.py --check-inputs` | 通过 | 0 | — | — | — |
| 1 | `vlib <out>/work` | 通过 | 0 | 0 | 0.089 | 60 s |
| 2 | `vlog -sv -work <out>/work +incdir+myriscv <vendor×2> <14 源>` | 通过 | 0 | 0 | 0.183 | 60 s |
| 3 | `vsim -batch tb_branch_turnover -gENABLE=1 +SPECS=…/key_specs_profile0.txt +CASES=9` | **PASS** | 0 | 0 | 1.683 | 180 s |
| 4 | `vsim -batch tb_cpu_rv32i_sample +NAME=isa_auipc +ROM=…/auipc_rom.dat +TRAPS=…/auipc.traps` | **判据拦下** | 0 | 0 | 1.393 | 180 s |
| 5 | `vsim -batch tb_cpu_rv32i_sample +NAME=isa_sb …` | **未派发** | — | — | — | 180 s |

全部无超时。编译 16 唯一模块、`Errors: 0, Warnings: 0`（与 030 同集合，无缓存 DRM/PHY，未出现 04030130）。

## 2. key（ENABLE=1）——正式 PASS，覆盖闸全达标

```
CHECK: flow_fast          PASS events=94 cycles=148
CHECK: flow_delayed       PASS events=94 cycles=524
CHECK: flow_backpressure  PASS events=94 cycles=194
CHECK: reset_pending      PASS events=94 cycles=524
CHECK: load_branch_jalr   PASS events=10 cycles=64
CHECK: misaligned_branch  PASS events=14 cycles=68
CHECK: target_access_fault PASS events=16 cycles=106
CHECK: older_load_fault   PASS events=17 cycles=128
CHECK: irq_load_drain     PASS events=22 cycles=146
RESULT: PASS branch_turnover enable=1 cases=9 events=455 FAST=56 EMPTY=5 RSP=51 LATE=96 READY=47
        BUFFER=5 DROP_ERR=35 LOAD=3 TRAP=3 IRQ=1 RESET=1
Errors: 0, Warnings: 0   $finish tb_branch_turnover.sv(182)
```

- 455 架构事件逐字段与独立 oracle 一致（`check_job` 内含该逐事件比对，已通过）；`RESULT: PASS` 唯一。
- 12 项覆盖全部为正（**LOAD 由 030 的 0 变为 3**），TRAP=3 / IRQ=1 / RESET=1，未放宽任何条件。
- `key flow_fast cycles=148` 严格小于复用 control 的 `194`（同模型发射空档减少；**非实际 DDR 收益或正式成绩**）。
- `load_branch_jalr` cycles 由 030 的 82 变为 64，为激励换档的直接结果，如实记录。

复用的 control 身份（取自原 030 目录、本轮重新核验）：`enable=0 cases=1 events=94 FAST=0 DROP_ERR=8`、flow_fast cycles 194。
本轮未重跑 control，未重跑已成功的 030 control job。

## 3. isa_auipc——功能 PASS，但被 Warnings 判据拦下

```
** Warning: (vsim-3017) sim/cpu_zmmul/tb_cpu_rv32i_sample.sv(38): [TFMPC] - Too few port connections. Expected 30, found 29.
** Warning: (vsim-3722) sim/cpu_zmmul/tb_cpu_rv32i_sample.sv(38): [TFMPC] - Missing connection for port 'memory_order_busy'.
ISA_TRAP: isa_auipc index=0 pc=800000e4 inst=74445073 cause=2 tval=74445073 target=800000e8 rf_we=0
ISA_TRAP: isa_auipc index=1 pc=800000f4 inst=18005073 cause=2 tval=18005073 target=800000f8 rf_we=0
ISA_TRAP: isa_auipc index=2 pc=8000010c inst=3b029073 cause=2 tval=3b029073 target=80000118 rf_we=0
ISA_TRAP: isa_auipc index=3 pc=80000128 inst=30205073 cause=2 tval=30205073 target=80000130 rf_we=0
ISA_TRAP: isa_auipc index=4 pc=80000204 inst=00000073 cause=11 tval=00000000 target=80000004 rf_we=0
CHECK: isa_auipc PASS tohost=00000001 traps=5 probes=4 muls=0 events=100
RESULT: PASS rv32i_sample case=isa_auipc tohost=1 traps=5 probes=4 muls=0
$finish tb_cpu_rv32i_sample.sv(60)   Errors: 0, Warnings: 2
```

只读复核（`run.py` 的 ISA 比对因首断言未执行，本次按同一口径独立比对）：五条 `ISA_TRAP` 与冻结
`fixtures/auipc.traps` **逐字段全等**（index/pc/inst/cause/tval/target/rf_we 均匹配，五条 `rf_we=0`），
即四启动 CSR probe cause=2 + 最后 pass ECALL cause=11/tval=0→80000004；事件 trace 100 行、其中 5 条 kind=1，
与 `events=100`、`traps=5` 自洽。**不能用宽松 cause2 白名单**——本处是逐字段精确比对。

### 3.1 警告归因（只读查证）

- 该警告是**严格 ISA TB 的端口漏连**，不是 RTL 报错，也不影响 DUT 行为（上节功能证据）。
- `memory_order_busy` 在**当前 CPU 与冻结的改前 CPU 中都存在**（`mycpu_sync.v:17` / `mycpu_sync_before.v:15`），
  即**不是本轮分支目标取指改动的产物**。
- 快照溯源：该端口最早出现在写缓冲轮的 CPU `3faf81a6…`（2026-10-13 20:38）；
  而 `sim/cpu_zmmul/tb_cpu_rv32i_sample.sv` 最后修改于 2026-10-13 12:05，端口增补时**未同步更新该 TB**。
- 该 TB 上一次真实运行是 `ds_cpu_zmmul_isa_resume_20261013_a`（CPU `43e45103…`，早于该端口），当时
  `isa_lhu`/`isa_or` 均 `Warnings: 0`；写缓冲轮的两项 ISA 用的是另一个 TB `tb_write_buffer_isa`，不可比。
- 结论：这是**写缓冲轮遗留、本轮首次暴露**的 TB/端口不同步；`Errors/Warnings0` 判据本身正确，
  但当前冻结 TB 与当前 CPU 的端口集不匹配。

## 4. 冻结性与未完成项

| 项 | 结果 |
| --- | --- |
| 清单内 327 工程 + 5 外部输入 | 逐项 SHA256 复核 0 处不一致 ✔ |
| 执行副本 53 | 全部写出、SHA256 与清单一致 ✔ |
| 冻结 TB SHA `6949972a…` / 新 spec SHA | 与清单一致，未被改动 ✔ |
| 原 030 失败目录 67 文件 | 保留 ✔ |
| 三份诊断产物 | 保留（`build/diag_counters_*`、`diag_load_use_*`、`diag_load_profile_*`）✔ |
| Git | HEAD 与 `git status --porcelain -uall` 与 `git_before.json` 逐行一致 ✔；`git_after.json` 未生成（如实记录） |
| `isa_sb` | 未运行，无日志/trace/证据 |
| `isa_auipc` | 未通过 runner 判据（`completed` 中无该键），其功能证据为本次只读复核所得，**不得记为 ISA 抽测 PASS** |
| 未覆盖 | 未跑诊断/历史 CoreMark/MUL/PHY/全量ISA/PDS/串口/上板；未做时序资源核对 |

## 5. 结论与下一步（不给上板命令）

- 本轮**功能门仍未闭合**：CPU 侧 key 全部通过，但 ISA 两项未完成（一项被判据拦下、一项未跑），
  成功状态 `BRANCH_TURNOVER_LOADUSE_KEY_AND_TWO_ISA_PASS` **未达成**。
- 因此**不提供** `run_branch_loaduse_resume_measurements.ps1` 上板/跑分命令；实板收益仍待实测。
  对照基线仍为 sfwd_300_01 的 P226998804 / V226731331 cycles、2.421321 / 2.418468 秒。
- 剩下的唯一阻塞是 `sim/cpu_zmmul/tb_cpu_rv32i_sample.sv` 未连 `memory_order_busy`（29/30 端口）。
  可能的处置都需要**用户单独授权**（本轮已按首败停止封存现场，不改 TB/判据/清单）：
  1. 给该 TB 补 `.memory_order_busy(1'b0)`（与 `tb_branch_turnover` 同口径），新 tag 重跑两项 ISA；
  2. 或明确把该 2 条已知端口警告列入可接受集合（判据变更），原 tag 现场仍不重跑。
- 处置前的现状：`isa_sb` 无任何证据，`isa_auipc` 只有本次只读功能复核；**未取得本轮 ISA 抽测的正式 PASS**。
