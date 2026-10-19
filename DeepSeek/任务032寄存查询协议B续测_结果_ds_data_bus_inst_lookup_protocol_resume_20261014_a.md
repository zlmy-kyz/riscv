# 任务032寄存查询协议B续测 结果：`ds_data_bus_inst_lookup_protocol_resume_20261014_a`

**状态：`STOPPED_FIRST_FAILURE`。首败（编译阶段）即停、现场完整保留、未重试、未改任何既有文件。**

**失败点是纯机械的系统 Verilog 保留字冲突，不是协议/判据/RTL 问题：新 TB 用 `edge` 作 task 形参名，ModelSim 在语法分析阶段即报错，vlog 未通过，B-only vsim 从未启动。**

| job | exit | native | elapsed | 上限 | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 0 | 0 | 0.0934 s | 60 s | 正常 |
| **vlog** | **2** | **2** | 0.3810 s | 60 s | **`Errors: 6, Warnings: 0`** —— 6 处 `edge` 语法错误 |
| B-only vsim | **未派发** | — | — | 180 s | — |
| 独立 Python 检查器 | **未运行** | — | — | — | B 组未产生任何轨迹 |

原始目录：`sim/data_bus_turnover/build/ds_data_bus_inst_lookup_protocol_resume_20261014_a/`

## 1. 第一失败点（编译）

```
** Error: (vlog-13069) .../tb_inst_lookup_protocol_resume.sv(416): near "edge": syntax error,
   unexpected edge, expecting IDENTIFIER or TYPE_IDENTIFIER or NETTYPE_IDENTIFIER.
** Error: (vlog-13057) .../tb_inst_lookup_protocol_resume.sv(430): Expecting numeric digits.
** Error: (vlog-13069) .../tb_inst_lookup_protocol_resume.sv(434): near "edge": syntax error ...
** Error: (vlog-13057) .../tb_inst_lookup_protocol_resume.sv(445): Expecting numeric digits.
** Error: (vlog-13069) .../tb_inst_lookup_protocol_resume.sv(449): near "edge": syntax error ...
** Error: (vlog-13057) .../tb_inst_lookup_protocol_resume.sv(456): Expecting numeric digits.
Errors: 6, Warnings: 0
```

`edge` 是 SystemVerilog 保留字，`note_accept` / `note_response` / `note_cancel` 三个 task 把它用作形参名：

| 行 | 内容 |
| --- | --- |
| 416 | `task automatic note_accept(input integer tok, input integer edge);` |
| 434 | `task automatic note_response(input integer tgt, input integer edge);` |
| 449 | `task automatic note_cancel(input integer edge);` |
| 427 / 430 / 445 / 456 | 三处 task 体内对该形参的引用（`tok_acc_edge[tok] = edge;`、`$fdisplay(..., edge, ...)`） |

我另外扫描了该文件里其他高危保留字作标识符的用法（`time/event/bit/type/sample/cover/type/class/new/void/ref/const/static/...`），**只发现 `edge` 一处**。即：修复只需把这一个标识符改名。

## 2. 本次已按方案落实的部分（不受失败影响，均已生效）

- **B-only 口径**：入口只派发 3 个 job（`vlib / compile / inst_lookup_protocol_resume`），未派发 key/A/control/旧版/history/ISA/PHY ✔（`--plan-only` 与 `jobs` 字段已核）。
- **失败也保留 after 状态**（方案第 39 行要求）：新的 `finally` 路径本次**实际生效**——`git_after.json` 已保存、`result.json` 记录 `git_after_captured_in_finally=true`、`git_before == git_after`、`git_unchanged=true`，错误上下文 `AssertionError: ...\compile` 一并落盘。此前几轮"旧缺失 git_after 不补造"的缺口在本轮不再出现。
- **交接文档身份迁移生效**：新清单不再冻结活的 `doc/CODEX_HANDOFF.md`（实测活文档现为 `43f87622…`，原历史身份 `55be65f6…`），改为绑定逐字相同的保存副本并在 `historical_identity_relocations` 记录映射；`require_inputs()` 断言活文档不在保护集合内。
- **零设计改动**：相对上一轮清单 180 工程输入**零变化**（含有缺陷的旧 TB/checker 作为冻结身份），`changed_design_files_this_round=[]`；桥保持 `f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0`。
- **编译顶层唯一替换**：新 B-only 顶层 `tb_inst_lookup_protocol_resume.sv` 替换旧协议顶层，仍 **39 模块**；include 闭包 5 条不变。
- 独立检查器（`check_inst_lookup_protocol_resume.py`）已实现并在 Python 侧对合成边沿轨迹做过正/负例验证，`plan_summary()` 给出**执行前**预计数 `{scenarios:17, tokens:43, accepts:43, responses:40, cancels:3, resets:3, planned_cancel_ids:[37,39,41]}`（未沿用旧 29/26，未按实测回填），已封入清单。

## 3. 未执行 / 未取得（不补造）

- **B-only 协议仿真从未运行**：无 `edge.log`/`plan.log`、无 `protocol.log`/`protocol.transcript`，因此无任何事务守恒、边沿快照、8 lane、AR 背压、复位取消数据。
- 独立 Python 检查器未在真实轨迹上运行；不宣称协议组有通过或失败的功能结论。
- 按 B-only 设计**未重跑** key/A/control/旧桥/历史 031/030/ISA/CoreMark/PHY；未运行旧 runner/旧 tag。
- 未修改 RTL/TB/清单/旧结果/旧门；未生成或改写任何 Codex 门。
- **PDS 时序/位流/串口/KEY0/实板全部 NOT_RUN**；"用户反馈时序通过"仍只是用户反馈，未经独立复核。

## 4. 身份与保护（执行前后均已核对）

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_inst_lookup_protocol_resume.json`，SHA **`9c478eaa351d1d0a1dbd601b817bb69cccf2f60513a52981938569fe785ee1db`** |
| 运行副本 | `inputs.json` SHA = 清单 SHA（一致） |
| 工程输入 / 保护证据 | **184 / 1827**（逐项 SHA256 全等，0 处不符） |
| 新实现（均已随副本封存） | `tb_inst_lookup_protocol_resume.sv`（`6d52cc39…`）、`check_inst_lookup_protocol_resume.py`（`20e62ae3…`）、`run_inst_lookup_protocol_resume.py`、`seal_inst_lookup_protocol_resume.py` |
| 绑定 | 部分复核收据 `2a482844…`（`checked_key` 617/415/18、`checked_A` 1472/512/256/256/0）及其 203 项 `prior_files_sha256` 逐项保持同一身份；control 收据 `61c2dc2d…`；已核 key 门 `cd6a9fb6…`；C 门 `8ffa90fc…`（仅对应旧桥） |
| Git | `git_before` 与 `git_after` **相等** ✔（本轮 finally 已补齐 after 保存） |

## 5. 建议的最小修复（待授权，我未自行实施）

把该 TB 中作为标识符的 `edge` 改名（例如 `edge_id`）：3 处 task 形参声明（416/434/449）+ 4 处体内引用（427/430/445/456），**不改变任何逻辑、激励、判据、时序或覆盖**。因方案明确"首FAIL 保留返回、不自动修后续 test 重跑"，我不自行改动；一旦授权，按工程约定绑定**新清单 + 新运行目录**（本 STOP 目录、清单与报告原样保留、不复用、不倒写）后再执行一次。

由于首次 HDL 运行已在编译阶段被保留字挡住，vlog 之后是否还有其它 elaboration/时序问题仍未可知——这也是本报告如实交回的残余风险。
