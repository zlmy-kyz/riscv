# 任务030 结果：CPU普通分支目标取指同拍接续关键验证（tag `ds_cpu_branch_turnover_20261014_a`）

**状态：首次失败停止 `STOPPED_FIRST_FAILURE`。未重试、未清理、未换 tag、未改 RTL/TB/模型/判据/清单/成功镜像。PDS/串口/上板/Git 提交均未执行。**

失败点：第二条单次命令在 **第 4 个命令（key job）** 处因 TB 覆盖率总闸 `fail("coverage totals")` 触发 `$fatal` 而终止；
第 5、6 个命令（`isa_auipc`、`isa_sb`）**未派发**，`git_after.json` 未生成。
control 与之相反的**例外**：control（ENABLE=0）单独 PASS，key 的九个 CHECK 也都逐组 PASS，只有 key 收尾的覆盖计数总闸 FAIL。

原始目录：`sim/cpu_branch_turnover/build/ds_cpu_branch_turnover_20261014_a/`
结果文件：`result.json` = `STOPPED_FIRST_FAILURE`
（本文只记录事实；`review.py` 属 Codex 审查入口，按要求未执行。）

## 0. 执行前环境阻塞（非本轮功能失败，已由用户解除）

第一次派发第二条命令时，`out.mkdir()` 立即失败：

```
PermissionError: [WinError 5] 拒绝访问。:
D:\riscv\RISCV\sim\cpu_branch_turnover\build\ds_cpu_branch_turnover_20261014_a
```

探测：`D:\riscv\RISCV` 可写，`sim\`、`sim\cpu_branch_turnover\`、`...\build\`、`DeepSeek\` 全部拒绝写入。
权限诊断/修复脚本结论 `REPAIR_REFUSED` / `nextAction=stop`，**未做任何修改**（`changes=[]`，无需回滚），报告
`D:\riscv\_acl-recovery\acl-report-ed357bf49ba745128899d22cbc5af453.jsonl`。
该次只是目录创建失败：**未创建 tag 目录、未编译、未跑 HDL，执行名额未消耗**。
用户把本会话切到「完全权限」后，写入探测（`sim\`、`...\build\`、`DeepSeek\`）全部 OK，才重新派发同一条命令一次。

## 1. 冻结身份核对（执行前后各一次，均一致）

| 项 | 值 |
| --- | --- |
| `sim/cpu_branch_turnover/inputs.json` SHA256 | `e26f0bacf56bdc8aad8ff4d091a55d2957567eff15ec0dccc280f363ae81dd08` ✔ |
| 当前 `myriscv/mycpu_sync.v` SHA256 | `b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3` ✔ 与任务新 CPU 一致 |
| `--check-inputs` | `INPUTS_MATCH_BRANCH_TURNOVER_HDL_NOT_RUN key=455 control=94 ISA=auipc,sb seed=2026101430`，exit 0 ✔ |
| PDS 进程 | 无 ✔（`pds_shell_count()==0` 通过） |
| tag 目录 | 执行前不存在 ✔ |
| 工程输入 196 / 外部输入 5 | 执行后逐项 SHA256 复核：0 处不一致 ✔ |
| 冻结副本 46 | `out/inputs/` 46 个副本全部写出，逐项 SHA256 与清单一致 ✔ |
| Git | HEAD `7af48d2185bc01a62be528c70b83c42689394c31` 未变；`git status --porcelain -uall` 与 `git_before.json` **逐行一致** ✔（`git_after.json` 因失败未生成，如实记录） |

## 2. 六命令 argv / exit / native / 时间 / 上限

| # | 命令 | 状态 | exit | native_after_wait | 秒 | 上限 |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| 0 | `python -B sim/cpu_branch_turnover/run.py --check-inputs` | 通过 | 0 | — | — | — |
| 1 | `vlib <out>/work` | 通过 | 0 | 0 | 0.145 | 60 s |
| 2 | `vlog -sv -work <out>/work +incdir+myriscv <vendor×2> <12 个源>` | 通过 | 0 | 0 | 0.271 | 60 s |
| 3 | `vsim -batch -lib <out>/work tb_branch_turnover -gENABLE=0 +SPECS=control_specs.txt +CASES=1 +EVENT_LOG=control.events.log` | **PASS** | 0 | 0 | 1.750 | 180 s |
| 4 | `vsim -batch -lib <out>/work tb_branch_turnover -gENABLE=1 +SPECS=key_specs.txt +CASES=9 +EVENT_LOG=key.events.log` | **FAIL** | 0 | 0 | 1.535 | 180 s |
| 5 | `vsim -batch … tb_cpu_rv32i_sample +NAME=isa_auipc …` | **未派发** | — | — | — | 180 s |
| 6 | `vsim -batch … tb_cpu_rv32i_sample +NAME=isa_sb …` | **未派发** | — | — | — | 180 s |

全部通过 `{job}.command.json` 记录的 argv 与 `{job}.log`（stdout 直写文件的原生日志实现，单工作库，未换加载方式/权限/RPC/超时）。
`vsim` 的 `exit_code`/`native_after_wait` 均为 0（`-do "run -all; quit -f"` 会把 `$fatal` 归零），失败由 `run.py` 对日志文本的断言捕获，与设计一致。

## 3. 编译（16 唯一模块全部编译，Errors 0 / Warnings 0）

`compile.log`：`GTP_GRS`、`GTP_APM_E2`、`alu`、`br_alu`、`l_alu`、`regfile`、`csr_file`、`mycpu_sync`、
`mul`、`ipm2l_mult_v1_3_mul`、`ipm2l_apm_data_pipeline`、`ipm2l_apm_distributed_sdpram`、`ipm2l_apm_distributed_shiftregister`、
`tb_cpu_rv32i_sample`、`inst_bus_interconnect`、`tb_branch_turnover` = **16**，与清单 `expected_modules` 集合一致；
`Errors: 0, Warnings: 0`，Top level 两个 TB 均在位。真实 `mul` 五源、真实 `inst_bus_interconnect`、厂家 `GTP_GRS/GTP_APM_E2` 均参与编译。
本轮 ROM/RAM 为独立模型，未加载缓存 DRM/DDR PHY，**未出现 04030130 提示**。

## 4. control（ENABLE=0，1 组）

```
CHECK: flow_fast PASS events=94 cycles=194
RESULT: PASS branch_turnover enable=0 cases=1 events=94 FAST=0 EMPTY=0 RSP=0 LATE=0 READY=0 BUFFER=0 DROP_ERR=8 LOAD=0 TRAP=0 IRQ=0 RESET=0
$finish  tb_branch_turnover.sv(182)   Errors: 0, Warnings: 0
```
- 94 架构事件、单组、独立参考逐退休通过；`FAST=0` 符合关闭功能预期（`DROP_ERR=8` 说明错路响应丢弃路径在关闭态同样成立）。
- console/transcript 换行归一全文一致；事件 trace `control.events.log` 94 行非空。

## 5. key（ENABLE=1，9 组）——九组 CHECK 全部 PASS，收尾覆盖总闸 FAIL

```
CHECK: flow_fast          PASS events=94 cycles=148
CHECK: flow_delayed       PASS events=94 cycles=524
CHECK: flow_backpressure  PASS events=94 cycles=194
CHECK: reset_pending      PASS events=94 cycles=524
CHECK: load_branch_jalr   PASS events=10 cycles=82
CHECK: misaligned_branch  PASS events=14 cycles=68
CHECK: target_access_fault PASS events=16 cycles=106
CHECK: older_load_fault   PASS events=17 cycles=128
CHECK: irq_load_drain     PASS events=22 cycles=146
RESULT: FAIL branch_turnover case=irq_load_drain event=22 pc=ffffffff inst=00000000 cause=2 tval=00000000 coverage totals
** Fatal: Assertion error.  Time: 19980 ns  Scope: tb_branch_turnover.fail  File: tb_branch_turnover.sv Line: 46
** Note: $finish  : tb_branch_turnover.sv(46)   Errors: 1, Warnings: 0
```

要点：
- 九组 CHECK 合计 **455** 事件（94/94/94/94/10/14/16/17/22），与冻结参考逐组一致，全部 PASS。
- 失败发生在第 177–178 行的**覆盖计数总闸**（`fail("coverage totals")`），不是任何逐事件/逐 PC/CSR/trace 检查：
  九组各自的逐退休、trace、请求槽位、目标地址、PC+4、CSR 精确状态检查都已在组内通过。
- `pc=ffffffff cause=2` 是 `fail()` 打印时当前 case 已 `resetn=0` 的 DUT 端口采样值，不是架构事件失配；报告中的 `event=22` 只是该 case 的事件数。
- **`FAIL` 报文里没有给出是哪一个覆盖计数不达标**：TB 只在最终 PASS 的 `$display` 里打印
  `FAST/EMPTY/RSP/LATE/READY/BUFFER/DROP_ERR/LOAD/TRAP/IRQ/RESET`，FAIL 路径只输出 `coverage totals`。
  因此**从本轮原始产物无法判定**具体是哪一项，日志/transcript/events 中均无该计数数值（未使用 `-wlf`，无波形可回读）。
- key 的 `flow_fast cycles=148` **严格小于** control 的 `194`（同模型同程序，少 46 拍），发射空档确有减少——但这是模型内周期，**不是实际 DDR 收益，也不是正式成绩**。

### 5.1 覆盖总闸的 12 个条件（`tb_branch_turnover.sv:177-178`，未改动）

`case_count==9` ✔（9 条 CHECK）、`total_events==455` ✔（各 CHECK events 求和）之外，还要求
`fast>0`、`response_fast>0`、`empty_fast>0`、`late_wait>0`、`ready_wait>0`、`buffer_flush>0`、
`discarded_errors>0`、`load_stalls>0`、`traps==3`、`irqs==1`、`resets==1` 全部成立。
`FAIL` 报文无法区分是其中哪一条（或多条）未达标。

### 5.2 可独立复核的强证据：455 事件与冻结 oracle 逐字段全等

`run.py` 的 trace 核对因 job 断言提前终止未执行；本次由只读脚本按 `run.py` 的同一比较规则
（`kind/pc/inst/rf_we` 全等；`rf_we` 为真时比 `rd/rf_wdata`；`kind∈{1,2}` 时比 `cause/tval`）对
`key.events.log`（**455 行，非空**）与九份冻结 `.trace` 逐行比对：

- 逐组事件数：`flow_fast 94 / flow_delayed 94 / flow_backpressure 94 / reset_pending 94 / load_branch_jalr 10 /
  misaligned_branch 14 / target_access_fault 16 / older_load_fault 17 / irq_load_drain 22`，与计划完全一致；
- **失配数 = 0**。

即：架构级行为（退休 PC/指令/写使能/寄存器结果/异常 cause-tval/IRQ 下一 PC）与独立解释器参考完全一致，
失败只落在 TB 的覆盖计数闸上。此为只读复核，不替代 `review.py`，也不构成 PASS 结论。

## 6. ISA 抽测（auipc、sb）——未执行

固定种子 `2026101430`（池 39 个、已排除 `fence_i`/`ma_data`）抽得的两项 `auipc`、`sb` 对应的第 5、6 个命令
**未派发**，`isa_auipc.log`/`isa_sb.log`/两个 `*.events.log` 均不存在，五条精确 trap 与 tohost 无从记录。
**本轮未取得任何 ISA 抽测证据，不得记为 ISA PASS 或全量 ISA PASS。**

## 7. 未覆盖范围 / 未完成项

- key 的覆盖计数总闸未通过，且失败项未在产物中标明；`RESULT: PASS branch_turnover` 未出现。
- `isa_auipc`、`isa_sb` 未运行；`git_after.json`、`inputs_unchanged`、`git_unchanged`、`scope` 等收尾字段未写入。
- 未运行 029/历史 MUL/旧 CPU/短 CoreMark/PHY 全套（按要求禁止复跑，本轮也不涉及）。
- 未执行 PDS 实现、时序/资源核对、比特流生成或下载；未开串口；**实板与性能收益均 NOT_RUN**。
- 未执行 `review.py`（Codex 审查入口）。

## 5.3 失败定位（用户单独授权后追加的只读诊断，不属原单次执行）

**结论：唯一未达标的覆盖项是 `LOAD`（`load_stalls`），根因是 `load_branch_jalr` 的取激励档位（profile=1）让该计数在本设计里不可达；不是 DUT 功能错误。**

诊断一（计数打印，tag 目录 `build/diag_counters_20261014_b/`，脚本 `sim/cpu_branch_turnover/diag_counters.py`）：
在不改冻结 TB 的前提下派生一份“只多打一行计数”的 TB，同 RTL/fixture/oracle 重跑 key：

| 计数 | FAST | EMPTY | RSP | LATE | READY | BUFFER | DROP_ERR | **LOAD** | TRAP | IRQ | RESET | CASES |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 九组累计 | 55 | 5 | 50 | 96 | 47 | 5 | 35 | **0** | 3 | 1 | 1 | 9 |

12 项条件里 **只有 `load_stalls>0` 不成立**，其余全部达标，故 `fail("coverage totals")` 被触发。

诊断二（逐拍探针，`build/diag_load_use_20261014_c/`，脚本 `diag_load_use.py`）：
`load_branch_jalr` 内 `lw x1,0(x10)`（`0x80000010`）的执行窗为

```
cy=12  pc=80000010 ixv=1 ixl=1 ixrd=1  ifidv=0 dps=0   ← load 在 EX，IF/ID 空（取指延迟，依赖项还没到 ID）
cy=13  pc=80000014 ixv=0 ixl=0         ifidv=1 dps=1   ← load 已进 EX/MEM，beq 才到 ID
cy=13..34 dps=1 fire=0                                  ← 等待由 MEM 级 data_pipeline_stall 承担
```

profile=1 的取指延迟使依赖指令 `beq` 在 `lw` **离开 EX 之后**才进入 ID，于是 ID 级 `load_use` 互锁从未成立，
等待全部由 MEM 级 `data_pipeline_stall` 吸收——架构事件完全正确（455/455 与 oracle 全等），但 TB 的
`load_stalls>0` 期望在该激励下**不可满足**。`load_use` 表达式（`mycpu_sync.v:655`）与改前 CPU
（`preparation_20261014_a/mycpu_sync_before.v:646`）逐字相同，本轮改动未触碰该互锁。

诊断三（可达性验证，`build/diag_load_profile_20261014_d/`，脚本 `diag_load_profile.py`）：
只把该用例 spec 的 profile 列 `1→0`（RTL/fixture/oracle 不变，架构参考与档位无关），同 tag 流程重跑：

```
RESULT: PASS branch_turnover enable=1 cases=9 events=455 FAST=56 EMPTY=5 RSP=51 LATE=96 READY=47
        BUFFER=5 DROP_ERR=35 LOAD=3 TRAP=3 IRQ=1 RESET=1
Errors: 0, Warnings: 0
```

九组 455 事件仍逐项与冻结 oracle 一致（每组 CHECK PASS），**覆盖总闸 12 项全部达标**。
即：该用例改用 profile 0 后，它真正测到了自己命名所指的“load-use 停顿”（LOAD=3），
而 profile=1 下这一项永远为 0（延迟取指本由 `flow_delayed`/`reset_pending` 覆盖）。

以上三份诊断产物只写入各自新建的 `build/diag_*` 目录，冻结 TB、`inputs.json`、fixture、oracle、RTL 均未改动。

## 8. 结论与下一步（不给上板命令）

本轮**功能门未通过**：key 在九组逐项 PASS 之后被 TB 覆盖率总闸拦下，ISA 两项未跑。
因此按任务约定**不提供 `run_branch_turnover_measurements.ps1` 上板/跑分命令**，新收益仍待实测；
对照基线保持 sfwd_300_01 的 P226998804 / V226731331 cycles、2.421320576 / 2.418467531 秒不变。

已定位：唯一缺口是 `load_branch_jalr` 的 profile=1 激励使 `LOAD` 计数不可达（见 §5.3），
属**测试激励/覆盖判据**问题，不是本轮 CPU 改动或既有流水功能的问题。
把它改成 profile=0 即可让九组 455 事件与 12 项覆盖全部达标（§5.3 诊断三已实证）。

但该改动落在**冻结激励/清单**上，超出“只做计数诊断”的授权范围，故本轮不改、不重跑：
- 冻结 TB、`fixtures/key_specs.txt`、`inputs.json`（SHA `e26f0bac…`）、oracle、RTL 均保持原样；
- 已用的 tag `ds_cpu_branch_turnover_20261014_a` 保留现场、不清理；
- 若要据此开正式功能门，需要用户对“改该用例 profile 并新 tag 重跑”的单独授权；
  ISA `auipc`/`sb` 两项也必须在同一次正式运行中补跑，才能记录本轮 ISA 抽测证据。
