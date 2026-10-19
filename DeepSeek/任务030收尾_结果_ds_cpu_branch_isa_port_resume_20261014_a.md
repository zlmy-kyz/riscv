# 任务030收尾 结果：ISA空闲端口补连与双样本复验（tag `ds_cpu_branch_isa_port_resume_20261014_a`）

**状态：`BRANCH_TURNOVER_REUSED_KEY_PLUS_TWO_ISA_PASS`。四命令全部 exit/native 0、未超时、无 FAIL/Fatal/RPC/timeout，
两个 ISA job `Errors: 0, Warnings: 0`，原 vsim-3017/3722 端口警告消失。**

本轮只补 ISA TB 的 `.memory_order_busy(1'b0)`，**CPU 未再修改**，key455/control94 复用已复核证据、未重跑；
原 030 失败目录与续测目录/诊断全部保留。PDS/串口/上板/Git 提交未执行。

- 原始目录：`sim/cpu_branch_turnover/build/ds_cpu_branch_isa_port_resume_20261014_a/`
- `result.json` = `BRANCH_TURNOVER_REUSED_KEY_PLUS_TWO_ISA_PASS`
- 报告：本文件（按要求未执行 Codex 审查脚本，未改动阶段文档/清单/备用诊断）

## 0. 固定身份与执行前核对

| 项 | 值 |
| --- | --- |
| tag | `ds_cpu_branch_isa_port_resume_20261014_a`（执行前不存在 ✔） |
| 清单 `sim/cpu_branch_turnover/isa_port_resume_inputs.json` SHA256 | `3672e60af67a08a031e48c4fd5375f681ee2bac3ef1e83cc673458bca6f17a66` ✔ |
| 新 ISA TB `sim/cpu_zmmul/tb_cpu_rv32i_sample.sv` SHA256 | `4ee8ada865d4c80fc5bfb2637b827d247231021ffcd7bddb2bc216ce1de92bc3` ✔ |
| 旧 TB 副本 `build/isa_port_preparation_20261014_a/tb_cpu_rv32i_sample_before.sv` | 保留 ✔（SHA 前缀 `4cf1aa4f60de`，与旧清单绑定） |
| CPU `myriscv/mycpu_sync.v` | `b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3` ✔ 未变 |
| `pds_shell` 并发 | 0 ✔ |
| `--check-inputs` | `ISA_PORT_INPUTS_MATCH_HDL_NOT_RUN; only memory_order_busy tie0; key455/control94 reused; ISA auipc,sb`，exit 0 ✔ |

唯一 TB 差异由 runner 静态断言逐字核验：旧文件锚点行后**只插入一条** `        .memory_order_busy(1'b0),`，
除此之外新旧 TB 完全相同；旧清单 `e26f0bac…`、续测清单 `7cb5c88e…` 未刷新。

## 1. 四命令 argv / exit / native / 时间 / 上限

| # | 命令 | 状态 | exit | native | 秒 | 上限 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 0 | `resume_isa_port.py --check-inputs` | 通过 | 0 | — | — | — |
| 1 | `vlib <out>/work` | 通过 | 0 | 0 | 0.192 | 60 s |
| 2 | `vlog -sv -work <out>/work +incdir+myriscv <vendor×2> <11 源> <新 ISA TB>` | 通过 | 0 | 0 | 0.187 | 60 s |
| 3 | `vsim -batch -lib <out>/work tb_cpu_rv32i_sample +NAME=isa_auipc +ROM=…/auipc_rom.dat +STATUS=80001000 +TRAPS=…/auipc.traps +EVENT_LOG=…` | **PASS** | 0 | 0 | 1.728 | 180 s |
| 4 | `vsim -batch -lib <out>/work tb_cpu_rv32i_sample +NAME=isa_sb +ROM=…/sb_rom.dat +STATUS=80001000 +TRAPS=…/sb.traps +RAM=…/sb_ram.dat +EVENT_LOG=…` | **PASS** | 0 | 0 | 1.519 | 180 s |

无超时；`$(job).command.json` 记录了完整 argv/cwd/exit_code/native_exit_after_wait/seconds/timeout_seconds/timed_out。
两个 job 的 console 日志与 `-logfile` transcript 换行归一后**逐行一致**（均 True）。

## 2. 编译（14 唯一模块，Errors 0 / Warnings 0）

`compile.log` 实际编译：`GTP_GRS`、`GTP_APM_E2`、`alu`、`br_alu`、`l_alu`、`regfile`、`csr_file`、`mycpu_sync`、
`mul`、`ipm2l_mult_v1_3_mul`、`ipm2l_apm_data_pipeline`、`ipm2l_apm_distributed_sdpram`、`ipm2l_apm_distributed_shiftregister`、
`tb_cpu_rv32i_sample` = **14**，与清单 `expected_modules` 集合完全一致；`Errors: 0, Warnings: 0`。
真实 `mul` 五源与 CPU 五子模块参与编译；未编译 key TB / 总线测试，未加载缓存 DRM/PHY，**未出现 04030130 提示**。

## 3. isa_auipc（PASS，零警告）

```
ISA_TRAP: isa_auipc index=0 pc=800000e4 inst=74445073 cause=2 tval=74445073 target=800000e8 rf_we=0
ISA_TRAP: isa_auipc index=1 pc=800000f4 inst=18005073 cause=2 tval=18005073 target=800000f8 rf_we=0
ISA_TRAP: isa_auipc index=2 pc=8000010c inst=3b029073 cause=2 tval=3b029073 target=80000118 rf_we=0
ISA_TRAP: isa_auipc index=3 pc=80000128 inst=30205073 cause=2 tval=30205073 target=80000130 rf_we=0
ISA_TRAP: isa_auipc index=4 pc=80000204 inst=00000073 cause=11 tval=00000000 target=80000004 rf_we=0
CHECK: isa_auipc PASS tohost=00000001 traps=5 probes=4 muls=0 events=100
RESULT: PASS rv32i_sample case=isa_auipc tohost=1 traps=5 probes=4 muls=0
$finish tb_cpu_rv32i_sample.sv(61)   Errors: 0, Warnings: 0
```

- **无** `vsim-3017` / `vsim-3722`；端口补连后警告清零。
- 五条 trap 与冻结 `fixtures/auipc.traps` **逐字段全等**（index/pc/inst/cause/tval/target/rf_we，`rf_we` 全 0），
  即四启动 CSR probe cause=2 + 最后 pass ECALL cause=11/tval=0→80000004。**未使用宽松 cause2 白名单。**
- `EV` trace 100 行、其中 5 条 trap 事件，与 `events=100 traps=5` 自洽。

### 3.1 auipc 与旧警告运行的架构归一对照

按 runner 的同一归一规则（只取 kind/pc/inst/写使能与写寄存器 rd/data、trap 的 cause/tval/target，
忽略时间戳与非写寄存器字段），本次 `isa_auipc.events.log` 与旧续测目录的
`build/ds_cpu_branch_loaduse_resume_20261014_a/isa_auipc.events.log` 逐项比较：

- 旧 100 事件、新 100 事件，**架构序列完全相等**（独立复核 = True）。
- 即端口补连只消除了 TB 未连引发的时间戳/信号噪声，**不改任何架构行为**。
- 旧任务那次 `Warnings: 2` 的记录保持为当时的非 PASS，不追改为正式 PASS。

## 4. isa_sb（PASS，零警告）

```
ISA_TRAP: isa_sb index=0 pc=800000e4 inst=74445073 cause=2 tval=74445073 target=800000e8 rf_we=0
ISA_TRAP: isa_sb index=1 pc=800000f4 inst=18005073 cause=2 tval=18005073 target=800000f8 rf_we=0
ISA_TRAP: isa_sb index=2 pc=8000010c inst=3b029073 cause=2 tval=3b029073 target=80000118 rf_we=0
ISA_TRAP: isa_sb index=3 pc=80000128 inst=30205073 cause=2 tval=30205073 target=80000130 rf_we=0
ISA_TRAP: isa_sb index=4 pc=80000634 inst=00000073 cause=11 tval=00000000 target=80000004 rf_we=0
CHECK: isa_sb PASS tohost=00000001 traps=5 probes=4 muls=0 events=496
RESULT: PASS rv32i_sample case=isa_sb tohost=1 traps=5 probes=4 muls=0
$finish tb_cpu_rv32i_sample.sv(61)   Errors: 0, Warnings: 0
```

- 五条 trap 与冻结 `fixtures/sb.traps` **逐字段全等**；`EV` trace 496 行、5 条 trap 事件。
- 带 `+RAM=…/sb_ram.dat`（sb 需数据侧初值），`muls=0`、IRQ 未触发。
- 与 auipc 共用同一次编译与同一 `work` 库，未改动判据。

两个样本合计：**tohost 各 1、各恰好 5 条 trap（四 cause2 probe + ECALL cause11/tval0→80000004）、muls0、IRQ0**，
种子 `2026101430`、池内 `auipc`/`sb` 两项，与冻结 `.traps` 逐字段一致。
**这是两项抽测，不代表全量 ISA PASS。**

## 5. 复用证据与冻结性

| 项 | 结果 |
| --- | --- |
| 复用 key（前一续测正式 PASS） | `enable=1 cases=9 events=455 FAST=56 EMPTY=5 RSP=51 LATE=96 READY=47 BUFFER=5 DROP_ERR=35 LOAD=3 TRAP=3 IRQ=1 RESET=1`，cycles 148/524/194/524/64/68/106/128/146 ✔ |
| 复用 control | `enable=0 cases=1 events=94 FAST=0 DROP_ERR=8`，flow_fast cycles 194 ✔ |
| 同模型对照 | key `flow_fast 148 < control 194` ✔（发射空档减少；**非板级收益、非正式成绩**） |
| 清单输入 410 工程 + 5 外部 | 逐项 SHA256 复核 0 处不一致 ✔ |
| 执行副本 25 | 全部写出、SHA256 与清单一致 ✔ |
| Git | `git_before.json` 与 `git_after.json` **完全相等**；当前 HEAD 与 `git status --porcelain -uall` 与之一致 ✔ |
| 旧证据 | 原 030 失败目录（67 文件）、续测目录、三诊断目录均在，未清理未覆盖 ✔ |
| RTL | 本轮 `RTL_changed=false`，CPU 仍 `b1114fa3…` ✔ |

## 6. 未覆盖范围

- 本轮**未运行 key / control**（按入口复用已复核证据），也**未跑任何诊断、历史 MUL/CoreMark/PHY、全量 ISA**。
- 未执行 PDS 实现/时序/资源核对、未生成或下载比特流；未开串口；**实板与性能收益均 NOT_RUN**。
- 未执行 Codex 审查脚本（`review_isa_port_resume.py`）。
- 本轮闭合的是**指定功能门**（复用 key455 + 两项零警告 ISA），**不代表全 SoC / PHY / 时序资源 / 实板 PASS**。

## 7. 结论

本轮指定功能门已闭合：`BRANCH_TURNOVER_REUSED_KEY_PLUS_TWO_ISA_PASS`。
CPU 侧分支目标取指同拍接续的 455 架构事件与 12 项覆盖、以及 `auipc`/`sb` 两项 ISA 抽测均已通过且零警告；
旧 key/control 证据复用，RTL 未再修改，全部历史证据与 Git 状态保持。
上板/跑分命令等待 Codex 复核原始证据后按其流程给出；本报告不自行给出或执行 `run_branch_isa_port_measurements.ps1`。
对照基线仍为 sfwd_300_01 的 **P226998804 / V226731331 cycles、2.421321 / 2.418468 秒**，新收益待实测。
