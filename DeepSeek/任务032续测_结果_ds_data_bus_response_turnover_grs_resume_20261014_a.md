# 任务032续测 结果：GRS顶层实例补齐（`ds_data_bus_response_turnover_grs_resume_20261014_a`）

**状态：`STOPPED_FIRST_FAILURE`（首次失败即停止，未重试、未换 tag、未改任何文件）。**

- 第 1 条静态入口：**PASS**（exit 0）。
- 第 2 条正式运行：**GRS 修复生效**——`vlib`/`vlog`/`control vsim` 全部正常，**设计成功载入并跑完**（`$finish`、`Errors: 0, Warnings: 0`、`control` exit/native **0**），上一轮的 20 条 `GRS_INST` 未解析错误完全消失。
- 失败发生在 runner 内的**证据复核**：`check_evidence.review_job:147` 要求每个 job 恰好 **4 条** `IPSpecCheck: 04030130`，而 control 日志只有 **2 条**（值都是 `04030130`）。
- 因该断言排在最前，**key job 未派发**；核对 CHECK/UNIT/SOC/EV/BUS 的后续断言**未执行**；`git_after.json` 未生成。

原始目录：`sim/data_bus_turnover/build/ds_data_bus_response_turnover_grs_resume_20261014_a/`
`result.json`：`status=STOPPED_FIRST_FAILURE`、`HDL_started=true`、`completed={}`、`board=NOT_RUN`、`timing=NOT_RUN`、`PDS_started=false`、`serial_opened=false`。

## 1. 命令与真实元数据（runner 原生直写，未倒填）

| # | 命令 | exit | native | elapsed(s) | 上限(s) | timed_out |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `python -B sim/data_bus_turnover/run_grs_resume.py --check-inputs` | 0 | — | — | — | — |
| 2 | `vlib <run>/work` | 0 | 0 | 0.1246 | 60 | false |
| 3 | `vlog -sv +incdir… -work <run>/work <3 厂家源><35 模块源>` | 0 | 0 | 0.3733 | 60 | false |
| 4 | `vsim -batch -lib <run>/work tb_data_bus_turnover -gTURNOVER=0 …`（control） | **0** | **0** | 3.5552 | 180 | false |
| 5 | `vsim … -gTURNOVER=1 …`（key） | **未派发** | — | — | 180 | — |

第 1 条输出：`RESULT: PASS Task032 inputs; reference82/requests49; HDL NOT_RUN; ISA=0`。
编译：**38 模块**、`Errors: 0, Warnings: 0`；`control` 日志 `# Errors: 0, Warnings: 0`、`$finish`、console 与 transcript 归一后逐字相同。

## 2. control job 的原始输出（日志原文，未经 runner 复核）

```
CHECK: response_owner_matrix   PASS cases=24
CHECK: old_error_blocks        PASS cases=5
CHECK: posted_write_order      PASS cases=5
CHECK: delayed_reset           PASS cases=2
CHECK: consecutive_requests    PASS cases=32 cycles=64
UNIT: pairs=24 errors=5 order=5 burst=32 cycles=64 turns=0 cancelled=1
SOC: cycles=619 events=82 turns=0 mem_wait=443 fault=1 error_rsp=1 mmio=5 uart=1 ram=1 fence=1 fence_wait=8 aw=5 w=5
RESULT: PASS data_bus_turnover key_group TURNOVER=0
```

- 与冻结口径可对照的原始数字：control **64 拍、turns=0、cancelled=1**（`UNIT:` 行）；`SOC` 的 `events=82 / fault=1 / error_rsp=1 / mmio=5 / uart=1 / ram=1 / fence=1 / aw=5 / w=5`、`fence_wait=8 > 0`；五组 CHECK 名称与用例数齐全。
- 原始轨迹非空：`control.unit.log` 200 行、`control.events.log` 82 行、`control.bus.log` 198 行。
- **上述只读自日志观察不等于 runner 复核通过**：复核在 `check_evidence.py:147` 即中断，后面的 CHECK 顺序、UNIT 拍数、SOC 字段、82 EV 逐事件对参考、unit/bus 轨迹与 49 CPU 请求等断言**均未执行**。

## 3. 失败点：`IPSpecCheck` 条数口径与本次 TB 形状不符（只读定位）

`check_evidence.py:147`

```python
assert re.findall(r'IPSpecCheck: (\d+)', log) == ['04030130'] * 4
```

- control 日志实测：**2 条** `IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error …`（值本身完全正确）。
- 本次 TB（`sim/data_bus_turnover/tb_data_bus_turnover.sv`）只例化：`GTP_GRS GRS_INST`、`data_turnover_unit`、**一个 `soc_top`**、`mini_ddr_model_x32`；**没有第二个桥/互连实例**。
- 作为对照，任务 031 的 TB 同时例化了 `soc_top` **和**一个手工 `dual_sram_to_pango_ddr_bridge`，因此同一判据在 031 各 job 上正好得到 **4 条**同类提示。
- 即：**`×4` 的条数期望沿用了 031 的 TB 形状（两个桥实例），与本轮 032 单 `soc_top` 的 TB 形状不一致**。两个 `*_init_param.v`、`GRS_INST`、编译参数、模块数（38）与判据其余部分都已闭合。

按约定我不判定这是判据需改还是 TB 需补实例，只交付事实与差异位置，由 Codex 裁定；本次未修改任何文件。

## 4. 身份与输入（执行前核对 + 运行后只读复核）

| 项 | 值 |
| --- | --- |
| 新清单 `sim/data_bus_turnover/inputs_grs_resume.json` SHA256 | `fa8bf3ae379103f3450dc18c9a037f5711f3fbc12228e418b4719049ae5b6eee` ✔ |
| 新 tag 目录 | 执行前不存在 ✔ |
| `pds_shell` 并发 | 0 ✔ |
| `myriscv/data_bus_interconnect.v` | `b0afffb5c45f8a635b90482cc15bd94f17ce2c748fd6f1bdad9db0b098131f24`（本轮新改动，未变）✔ |
| CPU `myriscv/mycpu_sync.v` | `b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3` ✔ |
| 桥 `myriscv/dual_sram_to_pango_ddr_bridge.v` | `97273a85137600e596b38a3e061cf2841bf24bc397bf9412688cd580fa164c20` ✔ |
| TB 顶层 GRS | `tb_data_bus_turnover.sv:3` 为 `GTP_GRS GRS_INST (.GRS_N(1'b1));` ✔，运行副本同样含该行 |
| 输入集合 | 164 工程 + 3 厂家 + 3 工具，逐项存在且 SHA256 一致（0 处不符）；167 份副本落盘；`inputs.json` 副本 SHA = 新清单 SHA |
| 旧失败身份 | 旧目录 `build/ds_data_bus_response_turnover_20261014_a/`（181 文件）与旧清单 `427844a5…f2c370` **原样保留**，未清理/未复用/未倒写 PASS ✔ |

`git_before.json` 已保存；`git_after.json` **未生成**（失败于其写入之前），按约定不补造。

## 5. 未执行 / 未覆盖范围

- **`key` job 未运行**：无 key 的 51 次 unit 接续 / 33 拍 / 31 拍收益、无 key 的 SoC 82 EV 与 49 请求、无 key 的 `turns>0`、无 key 与 control 的周期/MEM 等待对比证据。
- control 的 runner 复核**只走到第 147 行**；UNIT/EV/BUS 的独立核对与 49 请求逐条比对未执行（原始日志已完整保留，可供 Codex 复算）。
- 未执行 PDS/串口/KEY0/上板/Git 提交推送；未运行旧 `run.py`/旧 tag、`prepare_program.py`、`seal_inputs.py`、`review_grs_resume.py`/`review.py`；
  未修改任何 RTL/TB/include/模型/参考/脚本/清单/判据/超时；未生成任何 Codex PASS 门。

## 6. 交回 Codex 的核对要点（本次未实施）

1. 确认 `IPSpecCheck` 条数口径：本轮 TB 只有 1 个 `soc_top`（1 组 icache/dcache），实测 **2 条** 且值均为 `04030130`；031 的 4 条来自「SoC + 手工桥」两个实例。
2. 修复（若确为口径问题）只需按新 TB 形状调整该条数期望，或为该 TB 补足实例；任一改动后需**新授权 + 新运行目录**重跑。
3. 本次目录按约定保留、不清理、不复用；旧 031/032 目录与两份清单身份均未变动。
