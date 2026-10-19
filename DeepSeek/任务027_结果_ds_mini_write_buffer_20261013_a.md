# 任务027 结果：首次失败停止 —— key 套件 `real_soc_fence_irq_stop` 组报同步陷阱（tag ds_mini_write_buffer_20261013_a）

**结论：`STOPPED_FIRST_FAILURE`。四次 vsim 只执行到第 2 个（`key`），第 3、4 个（`isa_or`/`isa_lhu`）未执行。**
`control`（关闭功能的最小控制）**PASS**；`key` 的前六组**全 PASS（426 项）**，第 7 组 `real_soc_fence_irq_stop`（413 项）在 TB 的 SoC 观察点以 **`RESULT: FAIL unexpected synchronous CPU trap`** 中止——这是**日志确证的功能 FAIL**，不是工具/环境终止，也不是超时。按任务约定首次失败保留停止：未重试、未换 tag、未清理、未补造 `git_after` 或后续日志，未改 RTL/TB/生成器/模型/判据/清单/超时/权限。

## 1. 输入与前置

| 主设计文件 | 实测 SHA256 | 与任务书 |
| --- | --- | --- |
| `myriscv/dual_sram_to_pango_ddr_bridge.v` | `b64f756d49a88f9001e12f45a4e9385bbbf245010777a35a430205b913ed251b` | 一致 |
| `myriscv/mycpu_sync.v` | `3faf81a6383d0f69bbb3d8c24083ffb3b5066830ddf3f2951c2b5f278f8055fb` | 一致 |
| `myriscv/data_bus_interconnect.v` | `e8582e27f88f0e5e2bf820e4f7088495f16cad3f4cd7a70a7ee4944d9c85524e` | 一致 |
| `myriscv/soc_top.v` | `3fdbe2f5a08a6759f2667d158b44d34d3158d1971ee52b11cbacfa33eb2a9716` | 一致 |

清单 `sim/mini_board_migration/write_buffer_inputs.json` SHA256 `ea0ba519d8342c215303ce7b1af7f1da0b67f0293190dbcadd8d7b7c482a49c0`，与任务书一致。固定 tag `ds_mini_write_buffer_20261013_a` 启动前**不存在**；无 `pds_shell` 实现进程、无既有 `vsim/vsimk` 会话。

```powershell
python -B sim/mini_board_migration/run_write_buffer.py --check-inputs
# 退出 0：INPUTS_MATCH_WRITE_BUFFER_HDL_NOT_RUN key=839 control=8 ISA=or,lhu
python -B sim/mini_board_migration/run_write_buffer.py --tag ds_mini_write_buffer_20261013_a
# RUN_EXIT=1  →  AssertionError: ...\build\ds_mini_write_buffer_20261013_a\key
```

## 2. 命令执行矩阵

| 命令 | 上限 | 用时 | exit_code | native_exit_after_wait | timed_out | 结果 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| vlib | 60 s | 0.09 s | 0 | 0 | false | 通过 |
| vlog | 60 s | 0.33 s | 0 | 0 | false | **37 个模块，`Errors: 0, Warnings: 0`** |
| control（vsim） | 180 s | 1.54 s | 0 | 0 | false | **PASS** |
| key（vsim） | 180 s | 2.35 s | 0 | 0 | false | **功能 FAIL**（见 §3） |
| isa_or（vsim） | 180 s | — | — | — | — | **未执行** |
| isa_lhu（vsim） | 180 s | — | — | — | — | **未执行** |

先做一次 vlib/vlog、随后四次独立 `vsim -batch`，与任务书要求一致；`key` 的 `exit_code=0`、无超时，失败是 TB 断言而非工具错误。

## 3. 失败原始证据（`key.log`）

前六组逐字通过：

```text
# CHECK: posted_ack_instruction_overlap PASS checks=8
# CHECK: masked_store_readback PASS checks=385
# CHECK: full_entry_miss_ordering PASS checks=5
# CHECK: instruction_invalidation PASS checks=10
# CHECK: reset_initialization_pause PASS checks=8
# CHECK: non_ddr_order_gate PASS checks=10
# ** Fatal: RESULT: FAIL unexpected synchronous CPU trap
#    Time: 51575 ns  Scope: tb_write_buffer_x32.real_soc_observe File: D:/riscv/RISCV/sim/mini_board_migration/write_buffer_cases.svh Line: 215
# ** Note: $finish    : D:/riscv/RISCV/sim/mini_board_migration/write_buffer_cases.svh(215)
#    Time: 51575 ns  Iteration: 1  Instance: /tb_write_buffer_x32
# Errors: 1, Warnings: 0
```

- 已通过的检查 = 8+385+5+10+8+10 = **426**；第 7 组 `real_soc_fence_irq_stop` 的 **413 项未完成**（其 `CHECK` 行未出现），合计 426+413 = 839 与计划一致。
- 触发点条件（`write_buffer_cases.svh` 第 215 行，原文）：`if(soc.u_cpu.sync_trap_event) $fatal(1,"RESULT: FAIL unexpected synchronous CPU trap");` —— 即真实 SoC 场景中 DUT 出现了一个**未被期望的同步陷阱事件**。
- `key.log` 中**没有任何非 `#` 行的附加诊断**，TB 未打印该陷阱的 cause/tval/PC，因此**现有产物无法判定具体是哪种异常、发生在哪个 PC**；这是需要 Codex 定位的部分，我不越界推断其原因（可能来自新排空逻辑与 SoC/CPU 的交互，也可能来自 SoC 程序或 TB 期望口径）。
- 该组按任务书覆盖 FENCE、精确 IRQ、MRET、PERF STOP 排空等 SoC 行为；`key.log` 里 **4 条 `04030130` 厂家提示原文保留**（独立桥 I/D + 真实 SoC 桥 I/D）。

## 4. control（关闭功能）PASS 证据

```text
# CHECK: disabled_legacy_contract PASS checks=8
# RESULT: PASS write_buffer_control tests=8
# Errors: 0, Warnings: 0
```

control 退出 0、1.54 s、无超时；同样保留 **4 条 `04030130`**。即“同新 RTL 关闭功能”的最小控制合同与关闭路径一致——本次失败局限于**启用路径的真实 SoC 场景**。

## 5. 未执行与守恒状态

- **`isa_or`、`isa_lhu` 未执行**：本 tag 内不存在其 `command.json`/`log`/`transcript`；两项 ISA 抽测（各 4 个 CSR 启动陷阱 + 1 个结束 ECALL、tohost=1、muls=0、与冻结事件对照）**完全未验证**。
- **`git_after.json` 缺失**（失败发生在 runner 收尾之前）——本报告**不声称**执行前后快照相等，未补造。
- 16 份执行快照齐全（`inputs/`），可用于复核失败时输入。
- `result.json`：`status=STOPPED_FIRST_FAILURE`、`completed={"control":{"tests":8}}`、`PDS_started=false`、`serial_opened=false`，`error` 指向本 tag 的 `key`。
- 执行后无残留 `vsim/vsimk/python` 进程。

## 6. 未覆盖范围

- `key` 第 7 组 413 项、`isa_or`/`isa_lhu` 两例、以及“完整通过后的输入复核/16 副本/Git 前后一致”判定均未完成。
- 未执行 Codex 的只读 `review_write_buffer.py`、未跑板级工具、未执行 PDS/串口/上板、未提交或推送 Git，未跑 PHY/CoreMark/历史 026/Hello/全 ISA。
- 该 tag 目录现已存在；按任务约定**不得**清理或复用，重跑需 Codex 修订授权与新 tag。
- 本轮结论**仅**为 x32 桥/SoC 功能仿真，不代表 PHY、时序、资源或实际性能。

## 7. 交回 Codex

1. 复核本报告与原始 `control/key` 的 `command.json`、`console`、`transcript`、`result.json`。
2. 定位 `key` 第 7 组 `real_soc_fence_irq_stop` 在 51575 ns 触发的“unexpected synchronous CPU trap”：建议增加该陷阱的 cause/tval/PC 可见性（现有 TB 未打印），再判断是 RTL 排空交互问题还是 SoC 程序/期望口径问题。
3. 因固定 tag 已存在且第 3、4 个 job 未跑，需给出新的授权与 tag 后由 DeepSeek 单次执行；**在收到修订授权前我不会重试、不改源码/TB/判据、不清理目录**。
4. 功能门未通过前不进入上板步骤（`coremark_i64_d64_zmmul_wbuf_300_01` 不启动）。
