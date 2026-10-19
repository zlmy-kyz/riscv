# 任务032收尾 结果：两条原语提示口径与仅key续测（`ds_data_bus_response_turnover_ip_count_key_20261014_a`）

**状态：`DATA_BUS_RESPONSE_TURNOVER_KEY_ONLY_WITH_REUSED_CONTROL_PASS`。**

- 三条原生 job 全部正常：`vlib` / `vlog` / `key vsim` 均 exit/native 0、未超时、`cleanup=None`；38 模块、`Errors: 0, Warnings: 0`、正常 `$finish`、console 与 transcript 归一后逐字相同；`IPSpecCheck` **恰好 2 条** 且值均为 `04030130`。
- **只跑了 key**；control 未重跑，直接复用 `TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING` 收据。
- 结果：unit **33 拍/51 接续/1 取消/68 场景**；SoC **617 拍、MEM 等待 415 拍、18 次接受接续、82 EV、49 请求、5 AW=W、40 AR=R**、`fence_wait=8`。
- 差值（从原日志计算，非预填）：unit **64→33 省 31 拍**；SoC 总周期 **619→617 省 2 拍**；MEM 等待 **443→415 省 28 拍**。
- 输入/Git：166 工程 + 626 保护逐项 SHA 全等，`git_before == git_after`。**PDS/时序/串口/实板全部 NOT_RUN。**

原始目录：`sim/data_bus_turnover/build/ds_data_bus_response_turnover_ip_count_key_20261014_a/`

## 1. 限定代码改动（本任务授权范围内）

唯一语义改动是那一处厂家提示条数，字节级 diff 只有 1 行：

```diff
--- frozen（grs_resume 运行副本）
+++ active（sim/data_bus_turnover/check_evidence.py）
@@ -144,7 +144,7 @@
     assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', log)
-    assert re.findall(r'IPSpecCheck: (\d+)', log) == ['04030130'] * 4
+    assert re.findall(r'IPSpecCheck: (\d+)', log) == ['04030130'] * 2
```

- 依据：本轮 TB 只有 **1 个 `soc_top`**（1 组 icache/dcache），两个生成 Cache 各打印一次 `04030130`；031 另有手工桥才有 4 条。
- 未忽略提示、未改为下界、未设允许区间；**未为凑 4 条另加 DUT/TB 实例**。
- 运行前以字节级断言证明：把 `['04030130'] * 2` 还原为 `['04030130'] * 4` 后，活动 checker 与冻结副本**完全相同**（`current.replace(active, frozen) == frozen`，且 `* 4` 已不存在、`* 2` 恰 1 处）。checker SHA：旧 `a5675177afeb7b8c94acff66d4854a91f23e8e9dc6d1d7eb138016cb4c08c80f` → 新 `0bdf70c42b06e9c89e5a0e450632583a4f8c0f0044587d761bbfc3aba4c68242`。

新增实现文件（均已写入最终清单并随输入副本封存）：

| 文件 | 作用 |
| --- | --- |
| `sim/data_bus_turnover/run_ip_count_key_resume.py` | 新主入口：核输入→新目录→vlib/vlog→**仅 key**→严格核 key 并与 control 收据比较→Git 前后/结果 |
| `sim/data_bus_turnover/seal_ip_count_key_resume.py` | 封存脚本：由 `inputs_grs_resume.json` 生成新清单，并做 `--check` 自查 |

原 `run.py` / `review.py` / `run_grs_resume.py` / `review_grs_resume.py` / `prepare_program.py` / `seal_inputs.py` / TB / include / 模型 / 参考 / 判据 / 超时**一律未改**；新入口复用原 `run.py` 的 native `command`、Git snapshot、`snapshot`、`compile_command`、`job_command` 与独立 checker，**未调用原 `main`**（因此不会再跑 control）。

## 2. 新身份、输入保护与 include 闭合

| 项 | 值 |
| --- | --- |
| 新清单 | `sim/data_bus_turnover/inputs_ip_count_key_resume.json` |
| 新清单 SHA256 | **`22959513e1113e097ffafd2c245ce57ee10d054cab8deca8fccd27dd2501334f`** |
| 工程输入 | **166**（= 原 164 + 新增 2 个实现文件；只有 `check_evidence.py` 一处 SHA 更新） |
| 保护证据 | **626**（原 fa8 的 437 ∪ control 收据 `prior_files_sha256` 188 ∪ `control_review.json`），与 437 的交集为空 |
| 厂家/工具 | 3 + 3，身份与 fa8 清单逐项相同 |
| compile_sources / expected_modules / include_dependencies / timeouts | 与 fa8 清单**逐字相同**（33 源 / 38 模块 / 5 条 include / 4 项超时） |
| 强制保持身份 | TB `cb1adf6f…`、互连 `b0afffb5…`、CPU `b1114fa3…`、桥 `97273a85…`，另含 unit_cases.svh / program.dat / reference.json / reference.trace / prepare_program.py |
| control 绑定 | 收据 SHA `61c2dc2dbb6386465fd9dc6e9a8bcb21cf42bda11ae69c465a2dbd2cda91ba13`；`source_run = sim/data_bus_turnover/build/ds_data_bus_response_turnover_grs_resume_20261014_a`；`source_manifest_sha256 = fa8bf3ae…5b6eee`；`checked` 内容整段绑定（`unit_cycles=64`、`cycles=619`、`mem_wait=443`、`turns=0`、`fence_wait=8`、`unit.turns=0`、`URESET=1`） |
| 运行副本 | `inputs.json` 副本 SHA = 冻结清单 SHA；169 份文件落盘；`require_inputs()` 在运行首尾各核一次且相等 |

自查命令（均在 native 启动前通过）：

```powershell
python -B sim/data_bus_turnover/seal_ip_count_key_resume.py --check
python -B sim/data_bus_turnover/run_ip_count_key_resume.py --check-inputs
python -B sim/data_bus_turnover/run_ip_count_key_resume.py --plan-only
```

输出：`SEAL CHECK PASS project=166 protected=626 control_review=61c2dc2dbb638646`；
`RESULT: PASS Task032 ip-count key-resume inputs; checker edit=1 line; control reused 64/619/443; HDL NOT_RUN; ISA=0`；
`--plan-only` 的 jobs 恰为 `["vlib","compile","key"]`（**无 control**）。
自查还包含：旧 164 工程中与本清单不同的集合 **== {check_evidence.py}**；新增集合 == 声明的实现文件；compile/include/expected_modules/timeouts/vendor/tool 与 fa8 逐字相同；运行副本 5 条 include 闭合、两个 `*_init_param.v` 就位、TB 顶层含 `GTP_GRS GRS_INST`；Python AST 全过；`reference.json` 由 `program.dat` 独立重算仍相等。

## 3. 三条原生命令的真实元数据

| job | argv（关键部分） | exit | native | elapsed(s) | 上限 | timed_out | cleanup |
| --- | --- | ---: | ---: | ---: | ---: | --- | --- |
| vlib | `vlib <run>/work` | 0 | 0 | 0.0861 | 60 | false | none |
| vlog | `vlog -sv +incdir… -work <run>/work <3 厂家源><35 模块源>` | 0 | 0 | 0.3702 | 60 | false | none |
| key | `vsim -batch -lib <run>/work tb_data_bus_turnover -gTURNOVER=1 +DAT=… +UNIT_LOG=… +EV_LOG=… +BUS_LOG=… -logfile … -do "run -all; quit -f"` | 0 | 0 | 1.8657 | 180 | false | none |

完整 argv/cwd/exit/native/elapsed/timeout 由 runner 原生直写保存在对应 `*.command.json`；stdout 与 `-logfile` transcript 双份保留。

## 4. key 全部 CHECK / 覆盖 / 守恒

```
CHECK: response_owner_matrix PASS cases=24      （68 场景之一）
CHECK: old_error_blocks      PASS cases=5
CHECK: posted_write_order    PASS cases=5
CHECK: delayed_reset         PASS cases=2
CHECK: consecutive_requests  PASS cases=32 cycles=33
UNIT: pairs=24 errors=5 order=5 burst=32 cycles=33 turns=51 cancelled=1
SOC: cycles=617 events=82 turns=18 mem_wait=415 fault=1 error_rsp=1 mmio=5 uart=1 ram=1 fence=1 fence_wait=8 aw=5 w=5
RESULT: PASS data_bus_turnover key_group TURNOVER=1
Errors: 0, Warnings: 0     （IPSpecCheck: 恰好 2 × 04030130）
```

独立 checker（`check_evidence.review_job` + `unit_trace` + `soc_trace`）对原始轨迹的严格核对全部通过：

- **unit**：`UREQ 100 = URSP 99 + URESET 1`、`URESET=1`、`turns=51`、`cycles=33`；每笔 UREQ 的 target 译码、token、响应错误位与"响应同拍新请求"判定逐条核验。
- **SoC**：`CPU_REQ = CPU_RSP = 49`，逐字段与独立参考（`reference.json`）的 `write/size/addr/data/strobe` 比较；
  `AR 40 = R 40`（每拍 8×32bit 独立重算并逐拍比对）、`AW 5 = W 5`（AW 地址/data/strobe 展开与 W 拍逐字节相等）、`TURN 18` 与 `turns=18` 一致；
  `SIDE_MMIO=6 / SIDE_RAM=2 / SIDE_UART=1 / FENCE=1`；DDR 最终字 `0x800=0x33444444`、`0x804=0x80c=0x11223344`、`0x808=0xa5a5a5a5`；
  `fault=1 / error_rsp=1`（精确 load access fault 与年轻 store 抑制）；PASS 之后不得残留数据请求或写条。
- **EV**：`key.events.log` **82 行** 与冻结参考逐事件相等（81 正常 + 1 trap）。
- **轨迹非空**：`key.unit.log` 200 行、`key.events.log` 82 行、`key.bus.log` 216 行。

## 5. 复用 control 的对照与实际差值

| 指标 | 复用 control（收据 `checked`） | 本次 key | 差值 |
| --- | ---: | ---: | ---: |
| unit cycles | 64 | **33** | **−31** |
| unit turns | 0 | 51 | +51 |
| SoC cycles | 619 | **617** | **−2** |
| SoC MEM 等待 | 443 | **415** | **−28** |
| SoC turns | 0 | **18** | +18 |
| EV / 请求 / AW / W / MMIO / UART / RAM / FENCE / fence_wait | 82 / 49 / 5 / 5 / 6 / 1 / 2 / 1 / 8 | 同左 | 0 |

`result.json` 记录：`control_reused=true`、`reused_control_review_sha256=61c2dc2d…`、`control_source_run=…grs_resume_20261014_a`、`control_source_manifest_sha256=fa8bf3ae…`、`old_control_git_after=ABSENT_NOT_BACKFILLED`、`key_only=true`、`deltas={unit_cycles_saved:31, soc_cycles_saved:2, soc_mem_wait_saved:28}`。
runner 断言：key SoC `turns>0`、`cycles<619`、`mem_wait<443`、`fence_wait>0`，且 `619−617=2`、`443−415=28`、`64−33=31` 由脚本计算而非预填。

## 6. Git 与旧证据保持

- `git_before.json` 与 `git_after.json` **完全相等**（runner 内断言通过）；运行结束后再次只读核对：当前 `git status --porcelain -uall` 与 `git_before.json` **逐行相同**，HEAD 未变。
- 旧 `ds_data_bus_response_turnover_20261014_a`（elaboration STOP）与 `ds_data_bus_response_turnover_grs_resume_20261014_a`（IPSpecCheck STOP）目录、各自清单、STOP `result.json`、缺失的 `git_after.json` **全部原样保留**，未清理、未复用、未倒写 PASS；旧 fa8 清单 SHA 仍为 `fa8bf3ae…5b6eee`，原 427844a5 清单亦未改动。
- 新目录保存自己的 `git_before/after`，并注明 `old_control_git_after=ABSENT_NOT_BACKFILLED`。

## 7. 未覆盖范围与边界

- **PDS 实现、时序/资源、位流、串口、KEY0、实板全部未执行**（`board=NOT_RUN`、`timing=NOT_RUN`、`serial_opened=false`、`PDS_started=false`）；本仿真不能替代实际 DDR 性能验收。
- 未重跑 control、未跑历史 030/031/029/ISA/CoreMark/PHY；未运行 `review.py` / `review_grs_resume.py` / 旧 `run.py` / 旧 tag；未生成 `codex_review.json` 或任何 Codex PASS 门。
- 未修改设计 RTL / PDS / IP / 成功镜像 / 冻结判据 / 超时；未做 Git 提交推送。
- 本结果只证明**本修复版本的功能与受控收益**（key SoC 617 拍、MEM 等待 415 拍，相对复用 control 省 2/28 拍），**不代表实板收益**；031 基线 `P 2.251881472 s / V 2.248137195 s` 仍待同冻结 BIN 的实测对照。

## 8. 交回 Codex

证据齐备（新清单/副本/三条原生命令/UNIT/EV/BUS/Git/result 全部落盘），可用 `review_grs_resume.py` 或独立入口只读复核。当前总功能门仍未开放，033 不启动。
