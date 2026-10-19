# 任务028 结果：D 缓存命中读与写缓冲重叠关键仿真 PASS（tag ds_mini_data_read_overlap_20261013_a）

**结论：`DATA_READ_OVERLAP_KEY_PASS`。`control`（关闭重叠）8 项与 `key` 六组 **1597** 项全部通过。**
唯一结果
`RESULT: PASS data_read_overlap_x32 tests=1597 cpu_events=480 IRQ=1 early_acks=267 I_OVERLAP=383 FENCE_WAIT=44 IRQ_WAIT=44 STOP_WAIT=44 fills=2 updates=65 D_OVERLAP=578 SOC_D_OVERLAP=64`
——五个等待/重叠覆盖数均为正，`SOC_D_OVERLAP=64>0`，且 **`D_OVERLAP − SOC_D_OVERLAP = 578 − 64 = 514`** 与任务书要求的手工提前接受 D 读数一致（不是只看 PASS 字样）。仅主桥改动；**CPU 未改、ISA=0**。**不代表全 SoC/全 ISA/PHY/时序/实板 PASS**。

## 1. 入口与身份

固定 tag `ds_mini_data_read_overlap_20261013_a` 启动前**不存在**；无 `pds_shell` 实现进程、无既有 `vsim/vsimk` 会话；未改 RPC/权限/判据/清单/超时。

```powershell
python -B sim/mini_board_migration/run_data_read_overlap.py --check-inputs
# 退出 0：INPUTS_MATCH_DATA_READ_OVERLAP_HDL_NOT_RUN key=1597 control=8 ISA=0 CPU480
python -B sim/mini_board_migration/run_data_read_overlap.py --tag ds_mini_data_read_overlap_20261013_a
# 退出 0：RESULT: PASS D-read overlap key + minimal disabled control; board NOT_RUN
```

| 项目 | 实测 SHA256 | 与任务书 |
| --- | --- | --- |
| `myriscv/dual_sram_to_pango_ddr_bridge.v` | `3e1e6f98ebbf1e66531fa63a9443b72a70af781b08560c020ae6de7a6a876794` | 一致（改前 `b64f756d…ed251b`） |
| `myriscv/mycpu_sync.v` | `3faf81a6383d0f69bbb3d8c24083ffb3b5066830ddf3f2951c2b5f278f8055fb` | 未改（与 027 相同） |
| 清单 `data_read_overlap_inputs.json` | `4cbe8ece3147d93addff9b12ec0066634549f4a2c0874a9d2cdd86843a0bfd47` | 一致 |

## 2. 命令矩阵

| 命令 | 上限 | 用时 | exit | native | timed_out |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 60 s | 0.09 s | 0 | 0 | false |
| vlog | 60 s | 0.38 s | 0 | 0 | false |
| control | 180 s | 1.67 s | 0 | 0 | false |
| key | 180 s | 3.95 s | 0 | 0 | false |

编译 **36 个唯一模块**、`Errors: 0, Warnings: 0`（真实 I/D DRM、mul、ROM/RAM 源、实际 CPU/SoC/总线/UART/MMIO/计数器与 `GTP_GRS`/`GTP_DRM36K_E1`/`GTP_APM_E2`），单顶层 `tb_data_read_overlap_x32`，控制参数 `READ_OVERLAP=0/1`。两 job 均 `Errors: 0, Warnings: 0`、正常 `$finish`、无 `FAIL`/`Fatal`/`RPC_Init`/超时，**console 与 transcript 换行归一后全文一致**。

## 3. control（关闭重叠）证据

```text
# CHECK: disabled_read_overlap_control PASS checks=8
# RESULT: PASS data_read_overlap_control tests=8
# Errors: 0, Warnings: 0
```

即关闭新重叠时，busy 期间**其他行命中仍等待 W**，与原路径一致；同样保留 **4 条 `04030130`**。

## 4. key 六组 CHECK（逐字）

```text
# CHECK: qualification_priority_turnover PASS checks=8
# CHECK: all_rows_words_mask_overlap PASS checks=704
# CHECK: same_line_all_byte_masks_order PASS checks=385
# CHECK: alias_miss_and_full_store_order PASS checks=11
# CHECK: reset_and_init_qualification_clear PASS checks=9
# CHECK: real_soc_read_overlap_fence_irq_stop PASS checks=480
# RESULT: PASS data_read_overlap_x32 tests=1597 cpu_events=480 IRQ=1 early_acks=267 I_OVERLAP=383 FENCE_WAIT=44 IRQ_WAIT=44 STOP_WAIT=44 fills=2 updates=65 D_OVERLAP=578 SOC_D_OVERLAP=64
# ** Note: $finish : .../tb_data_read_overlap_x32.sv(636)   Time: 93690 ns
# Errors: 0, Warnings: 0
```

| 组 | 项数 | 结果 |
| --- | ---: | --- |
| qualification_priority_turnover | 8 | PASS |
| all_rows_words_mask_overlap | 704 | PASS |
| same_line_all_byte_masks_order | 385 | PASS |
| alias_miss_and_full_store_order | 11 | PASS |
| reset_and_init_qualification_clear | 9 | PASS |
| real_soc_read_overlap_fence_irq_stop | 480 | PASS |
| 合计 | **1597** | 与 `tests=1597` 相符 |

覆盖计数核对（我逐项验算）：`early_acks=267`、`I_OVERLAP=383`、`FENCE_WAIT=44`、`IRQ_WAIT=44`、`STOP_WAIT=44` 均 > 0；`SOC_D_OVERLAP=64` > 0；**`D_OVERLAP−SOC_D_OVERLAP=514`** 与任务书要求一致。`fills=2`、`updates=65` 为 **SoC 组增量**（不含手工测试），按要求口径记录，不当作总数。key 同样保留 **4 条 `04030130`** 原文。

## 5. 事件 trace 与提示

- `key.events.log` 235082 字节、非空：**EV 485 行 / BUS 1036 行**；同步陷阱仍按严格判据处理（本次无陷阱，故无 FAIL）。
- `control.events.log` 为 **0 字节（空）**——如实记录：该 job 未产生事件流（runner 未把控制 job 的 trace 非空作为判据，控制 job 仍完整通过）；任务书“EV/BUS trace 非空”的要求针对 key/真实 SoC 轨迹，已满足。
- 两 job 各 **4 条厂家 `04030130`**（手工桥与真实 SoC 桥各一对 I/D IP）原文完整保留，未改成零 warning 要求。

## 6. 输入、副本与 Git 守恒

- `result.json`：`status=DATA_READ_OVERLAP_KEY_PASS`、`manifest_sha256=4cbe8ece…`、`completed={control:8, key:1597/480/IRQ1/early_acks267/I_OVERLAP383/FENCE_WAIT44/IRQ_WAIT44/STOP_WAIT44/soc_fills2/soc_updates65/D_OVERLAP578/SOC_D_OVERLAP64}`、`inputs_unchanged=true`、`git_unchanged=true`、`CPU_changed=false`、`PDS_started=false`、`serial_opened=false`、`board_status=NOT_RUN`。
- **11 份执行副本**与当前工作副本逐份 SHA256 比对**零不匹配**；`git_before.json` 与 `git_after.json` 内容哈希相同。
- 原 027 失败目录（35 文件）与 027 续测目录（44 文件）均**保持未动**；执行后无残留 `vsim/vsimk/python` 进程。

## 7. 未覆盖范围

- x16 兼容路径本轮**仅静态**；未跑 PHY 训练联仿、CoreMark、历史 ISA/CPU 重跑或旧版对照。
- 仅为 **x32 桥 + 真实 CPU/SoC 模型**的关键功能与最小真实集成：**不能替代 PHY、时序、资源或实际性能**；板级 `NOT_RUN`，实际收益未测。
- 未执行 PDS、串口、上板、Git 提交推送；未执行 Codex 的 `review_data_read_overlap.py`。

## 8. 交回 Codex

原始产物：`sim/mini_board_migration/build/ds_mini_data_read_overlap_20261013_a/`（四份 `command.json`、`vlib.log`、`compile.log`、`control`/`key` 的 `console`/`transcript`/`events.log`、`inputs.json`、`inputs/`(11)、`git_before/after.json`、`result.json`）。

Codex 用 `review_data_read_overlap.py` 核原始证据通过后，可直接给 PowerShell `run_data_read_overlap_measurements.ps1` 的 COM9 命令：新日志 `coremark_i64_d64_zmmul_dread_300_01`，同冻结 P300/V300 各一次，对照成功 `wbuf_300_01`（P 250107028 / V 249687374 cycles，2.667808 / 2.663332 秒）；BIN/300 次/CRC 5275-8803 保持，不例行核 PDS/位流。
