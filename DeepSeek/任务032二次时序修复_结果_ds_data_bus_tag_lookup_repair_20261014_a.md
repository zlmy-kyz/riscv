# 任务032二次时序修复 结果：I标签并行查询关键仿真（`ds_data_bus_tag_lookup_repair_20261014_a`）

**状态：`STOPPED_FIRST_FAILURE`。首败即停、保留现场、未重试、未改任何既有文件。**

**关键事实：本次两条实质验证都已通过，STOP 完全由我新写的执行/检查管线代码缺陷造成，与 RTL、TB 激励、独立参考和原 key 判据无关。**

- **原 SoC key：PASS，且与已复核 key 逐字段完全相同** —— `UNIT cycles=33 turns=51 cancelled=1`、`SOC cycles=617 events=82 turns=18 mem_wait=415 ...`、五组 CHECK 全过、恰好 2 条 `04030130`、`Errors: 0, Warnings: 0`、正常 `$finish`；`result.json` 已写入 `completed.key` 且 `deltas.key_identical_to_reviewed=true`（**617 周期 / 415 MEM 等待 / 18 接续保持一致**）。
- **新标签查询组：仿真功能 PASS** —— `RESULT: PASS tag_lookup det=1472 rnd=512 mismatches=0 hits=64 misses=1920`，2 条 `04030130`、`Errors: 0, Warnings: 0`、2045 ns 正常 `$finish`。
- **失败点在我新增的 `run_tag_lookup_repair.check_lookup()`**：把 `lookup.log`（TB 自己写的轨迹文件）当成 stdout 去和 `lookup.transcript` 比对；该 job 的 stdout 实际是 `tag_lookup.log`，两者归一后**本来就相同**（均 33 行，`stdout==transcript: True`）。
- 因此断言在独立检查器 `check_tag_lookup.py` **尚未运行**之前就抛出；**新标签查询轨迹未获得我的独立 Python 复核**（只有 TB 自检 0 mismatch），这一点按实记录，不宣称已独立核验。

原始目录：`sim/data_bus_turnover/build/ds_data_bus_tag_lookup_repair_20261014_a/`

## 1. 四条原生命令的真实元数据（全部正常）

| job | exit | native | elapsed(s) | 上限 | timed_out | cleanup |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `vlib` | 0 | 0 | 0.0999 | 60 | false | none |
| `vlog`（34 源） | 0 | 0 | 0.4083 | 60 | false | none |
| `key`（原 SoC，TURNOVER=1） | 0 | 0 | 1.9233 | 180 | false | none |
| `tag_lookup`（新 TB） | 0 | 0 | 1.3750 | 60 | false | none |

编译：**39 模块**（原 38 + 新顶层 `tb_inst_tag_lookup`）、`Errors: 0, Warnings: 0`。完整 argv/cwd/exit/native/elapsed/timeout/pid 由 runner 原生直写保存在 `*.command.json`。

## 2. 原 SoC key 的完整通过证据（不加拍要求满足）

```
CHECK: response_owner_matrix PASS cases=24 / old_error_blocks 5 / posted_write_order 5
       / delayed_reset 2 / consecutive_requests 32 cycles=33
UNIT: pairs=24 errors=5 order=5 burst=32 cycles=33 turns=51 cancelled=1
SOC: cycles=617 events=82 turns=18 mem_wait=415 fault=1 error_rsp=1 mmio=5 uart=1 ram=1 fence=1 fence_wait=8 aw=5 w=5
RESULT: PASS data_bus_turnover key_group TURNOVER=1
Errors: 0, Warnings: 0        （IPSpecCheck: 恰好 2 × 04030130）
```

`result.json` 记录 `completed.key`、`reused_key_checked`（完整 `checked_key`）、
`deltas={unit_cycles_saved:31, soc_cycles_saved:2, soc_mem_wait_saved:28, key_identical_to_reviewed:true}`，
`check_key()` 的"整段 `checked_key` 相等"断言**已通过**——即 617/415/18 与已复核 key 完全一致，不是"仍快于 control"。

## 3. 失败点与根因（均为本轮我新增代码的缺陷）

**(a) 读错文件对（直接触发）。** `check_lookup()` 写的是一律比对 `out/'lookup.log'`：

```python
log = base.common.read(out / 'lookup.log')
transcript = base.common.read(out / 'lookup.transcript')
assert log.strip() == transcript.strip(), 'lookup console/transcript differ'
```

但 `base.common.command(..., out / 'tag_lookup', 60)` 把 stdout 写到 `tag_lookup.log`，
`+LOOKUP_LOG=<out>/lookup.log` 是我给 TB 轨迹起的名。实测：`tag_lookup.log`（33 行）与 `lookup.transcript`（33 行）**归一后完全相同**（`stdout==transcript: True`），
而 `lookup.log` 是 2497 行的 OBS/TBL 轨迹，自然不可能与 transcript 相等。
→ 最小修复：console 读 `tag_lookup.log`，轨迹读 `lookup.log`。

**(b) `scenario` 未初始化。** TB 里 `integer fd, i, r, b, k, idx, scenario;` 是四态变量且无初值，
`scenario = scenario + 1` 永远是 `x`，因此轨迹首列全部打印成 `x`（实测首行 `OBS x 0 0 0 00000 000000 1 1 1`）。
→ 最小修复：`integer scenario = 0;`（`det_obs/rnd_obs/mismatches/hits/misses` 已有初值，未受影响）。

这两处都只影响我新增的轨迹/比对管线；**TB 的激励、准备表不变量、期望计算、DUT 观测均正确**（TB 自检 1472+512 全过、0 mismatch、hit/miss 均覆盖）。

## 4. 新标签查询组的实测统计（TB 自检，未经独立 Python 复核）

```
LOOKUP-SUMMARY det=1472 rnd=512 mismatches=0 hits=64 misses=1920 rows=64 high_bits=21 seed=20261014
```
- 轨迹：`OBS` 1984 行（1472 确定性 + 512 随机）、`TBL` 512 行、SUMMARY 1 行，共 2497 行；
- 确定性覆盖 = 64 行 × (1 命中 + 1 所选 valid0 + 21 高位翻转) = 1472，符合方案下限 64×23；
- 随机 = 64 行 × 8 = 512，种子 20261014；
- 命中 64（每行一次匹配命中）、未命中 1920，hit/miss 均覆盖；
- TB 内已逐条断言：桥始终 `IDLE`、无 DDR 活动、`inst_line_index` 译码正确、`observed === expected`。

**未完成**：`check_tag_lookup.py`（独立重算每条期望、复核低 6 位不变量、64 行/21 位覆盖、种子重放、零 mismatch）**尚未执行**，因此该轨迹暂不视为已独立核验。

## 5. 身份、输入与保护（执行前后均已核对）

| 项 | 值 |
| --- | --- |
| 新清单 | `sim/data_bus_turnover/inputs_tag_lookup_repair.json`，SHA **`50408ce477e58edeb8624a8e8fbf5845b009960da48332be22463df90773fdb1`** |
| 运行副本 | `inputs.json` 副本 SHA 与 `result.json` 记录的 manifest SHA **一致**（均为 `50408ce4…3fdb1`） |
| 桥 | `1df26c25…0406` → **`1170cfd21a9dc01fe526256a778309f0f657b0445ff53707ddfdc877a7280406`**（与方案一致） |
| 工程输入 | **172**（原 168 中只有桥变化 + 本轮 4 个实现文件：`tb_inst_tag_lookup.sv`/`check_tag_lookup.py`/`run_tag_lookup_repair.py`/`seal_tag_lookup_repair.py`） |
| 保护证据 | **1018**（原 821 ∪ 旧 5e5 清单 ∪ 前次运行目录除 `work` 全部文件 ∪ 前次结果报告 ∪ 本次准备目录 11 文件） |
| 逐项核对 | 172 工程 + 3 厂家 + 3 工具 + 1018 保护 **全部 SHA256 相等（0 处不符）**；175 份输入副本落盘；5 条 include 闭合、两 `*_init_param.v` 就位、两个 TB 顶层均含 `GTP_GRS GRS_INST`；`reference.json` 独立重算相等 |
| 编译源 | 原 33 + 新 TB = 34；`include_dependencies`/`vendor`/`tool`/`timeouts` 与上一轮逐字相同 |
| 绑定 | control 收据 `61c2dc2d…91ba13`；已复核 key 门 `cd6a9fb6…f7eaaf`（`checked_key` 即 `expected_key`）；前次修复复核 `4de7282d…e4e319`（`TASK032_FIRST_SELECTOR_REPAIR_RAW_FUNCTIONAL_REVIEW_PASS_TIMING_FAIL`） |
| Git | `git_before.json` 已保存；`git_after.json` **未生成**（失败于其写入之前），按约定不补造 |

## 6. 未执行 / 未覆盖

- `check_tag_lookup.py` 独立复核**未运行**；新轨迹未获独立核验。
- `git_after` 未采集、`inputs_unchanged`/`git_unchanged` 未复核（runner 在写 `result.json` 终值前抛出，`finally` 已落盘 STOP 记录）。
- 未重跑 control、历史 031/030、ISA、CoreMark/PHY；未运行 `review.py`/`review_grs_resume.py`/旧 runner/旧 tag。
- **未修改任何设计 RTL/TB（原）/include/模型/参考/DAT/checker/成功镜像/PDS/约束/判据/超时**；未生成 Codex 门。
- **PDS 时序、位流、串口、KEY0、实板全部 NOT_RUN**：本次不证明 WNS −0.218 ns/TNS −0.431 ns/2 端点是否修复。
- 方案已声明：AR 接受同拍 R 返回相位未由冻结模型动态模拟；标签查询组不模拟 DDR 返回相位/x16 行为。

## 7. 建议的处置（待 Codex/用户裁定，我不自行改判据或换 tag）

失败仅是我的两处管线缺陷，且失败目录/清单按约定保持原身份。按工程约定"失败目录/冻结清单保持原身份，修复后绑定新清单和新运行目录"，建议：

1. 我修正 `run_tag_lookup_repair.py` 的 console 路径与 `tb_inst_tag_lookup.sv` 的 `scenario` 初值（各一行级改动，**不动激励、期望、判据、超时、源清单结构**）；
2. 重新封存为**新清单 + 新运行目录 + 新 tag**（旧 `50408ce4…` 清单与本 STOP 目录原样保留、不复用、不倒写）；
3. 在一个新目录重跑同样的四个 job 一次（key 仍须 617/415/18，lookup 仍须 1472/512/64/21），并让 `check_tag_lookup.py` 独立复核这次轨迹。

在获得明确授权（沿用固定 tag 的替代方案，或 Codex 新收据）之前，我不自行重跑，也不把本次 TB 自检当作独立核验。
