# 任务021批处理续测 结果：I64/D32 真实 DRM 单次验收 PASS（tag ds_mini_idrm64_batch_20261013_a）

**结论：`MINI_INST_DRM64_BATCH_RESUME_KEY_TEST_PASS`，`functional_status=PASS`，2449/2449 项检查全部通过。**
这是 I64/D32（I=2KiB、D=1KiB）候选的**首次完整功能验证**：真实厂家 I/D 生成 IP + Pango 原语、真实单顶层、原八组 2449 项判据全部通过，且**全程无 RPC 故障**。ISA=0；未跑 ISA/Hello/CoreMark/PHY/CPU 程序/历史套件；未执行 PDS、串口、上板、Git 提交或推送。**新 I64 的时序、资源、面积与实际 DDR 收益均未测量。**

## 1. 输入身份

| 项目 | 值 |
| --- | --- |
| 主桥（I64=2KiB / D32=1KiB / 93.75MHz） | `myriscv/dual_sram_to_pango_ddr_bridge.v` SHA256 `a0c4e2f6eef67f31333e5e350c5cf84b50025a4141e0fb03a6ce51540c96601b` |
| 本批处理清单 | `sim/mini_board_migration/inst_drm64_batch_inputs.json` SHA256 `98cee935fd5f77a3d905dc14af930bf296738264e52088019e3ae63991d7b1ec`（233 项 + 5 模拟器文件 + 2 参考/配置文件） |
| 原 021 清单（未刷新） | `inst_drm64_inputs.json` SHA256 `9e74eb569e075bb9b64e7ebc852b2bcc2baf9d9e7f3dbc42cf6c23d08cd2d68c` |
| 诊断 / CLI 清单（未刷新） | `inst_drm64_resume_inputs.json` `d1b0b468…df6d`；`inst_drm64_cli_inputs.json` `b0640ab8…682c8` |
| Git HEAD（执行前后一致） | `7af48d2185bc01a62be528c70b83c42689394c31` |

只读检查（执行前，退出 0，逐字匹配预期）：

```text
INPUTS_MATCH_NOT_SIMULATED 233 original=179 vendor=2 tools=5 refs=2 checks=2449 ISA=0 vsim_limit=180s entry=BATCH_SINGLE_TOP
```

固定 tag `ds_mini_idrm64_batch_20261013_a` 在启动前确认**不存在**（未换 tag、未清目录）；`pds_shell` 计数 0（未与用户 PDS 并行）。开始时间 2026-10-13 09:52:42。

## 2. 执行模式与三条命令

本入口按任务书只把工具模式从 `-c` 换成手册支持的 `-batch`、日志选项从 `-l` 换成 `-logfile`；**未改系统/套接字/文件权限、未强制 IPv4、未使用未验证的环境变量或厂家 Tcl**（`result.json` 记录 `host_settings_changed=false`）。

| 步骤 | 上限 | 用时 | 退出码 | 超时 | 说明 |
| --- | ---: | ---: | ---: | --- | --- |
| vlib | 60 s | 0.28 s | 0 | 否 | 新 work 库 |
| vlog | 60 s | 0.29 s | 0 | 否 | 原 **8 模块**（真实 `GTP_GRS`/`GTP_DRM36K_E1` + I/D 四生成源 + 当前主桥 + 原 TB），单顶层 `tb_inst_drm64_x32`，`Errors: 0, Warnings: 0` |
| vsim | 180 s | **1.76 s** | **0** | 否 | 见下 |

vsim 实际 argv（`command.json`）：

```text
vsim.exe -batch -lib <tag>\work tb_inst_drm64_x32 -logfile <tag>\transcript -do "run -all; quit -f"
```

未同时使用 `-c`；不在 `-do` 内调用 `vsim`；不编译/加载第二观察顶层；未重跑工具启动或环回探针。执行后 **0** 个残留仿真进程。

## 3. 验收逐条核对

1. **三命令退出 0**、无超时（1.76 s ≪ 180 s）。
2. **Errors/Warnings**：`compile.log` 末行与 `simulation.log` 末行均为 `Errors: 0, Warnings: 0`。
3. **正常加载与运行**：`simulation.log` 依次给出 8 条 `# Loading`（`sv_std.std`、`tb_inst_drm64_x32`、`GTP_GRS`、`dual_sram_to_pango_ddr_bridge`、`icache`、`ipm2l_sdpram_v1_10_icache`、`dcache`、`ipm2l_sdpram_v1_10_dcache`、`GTP_DRM36K_E1`）、`# run -all` 回显。
4. **两条厂家非致命提示（原文，恰好两条，I/D 各一条）**：

   ```text
   # IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
   # IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
   ```

   `IPSpecCheck` 行数 = 2，ID 均为 04030130；未改厂家源、未屏蔽日志。
5. **八组 CHECK 顺序与计数**（`simulation.log` 第 29–36 行，8 条全部 PASS）：

   | CHECK组 | 项数 | 日志 |
   | --- | ---: | --- |
   | sixtyfour_rows_slots_1024_split_2048_conflict | 645 | PASS |
   | upper_I63_full_tag_partial_zero_write_I_D_invalidation | 147 | PASS |
   | independent_D32_locked_upper_I63_fill_data_priority | 207 | PASS |
   | same_cycle_bad_ID_last_idle_preserve_upper_I63_victim | 139 | PASS |
   | readiness_reset_clear_I64_D32_cancel_pending_IF | 480 | PASS |
   | synchronous_read_accepted_address_all_rows_words_hit_reset | 515 | PASS |
   | D32_all_words_synchronous_accepted_address_1024_conflict_hit_reset | 294 | PASS |
   | D31_bad_ID_last_same_cycle_fill_cancel_and_I_D_source_switch | 22 | PASS |
   | 合计 | **2449** | 与唯一 `tests=2449` 相符 |

   判据与原 021 完全一致（未放宽/重写）；2449 为完成检查计数，不等于事务数。
6. **唯一结果行与正常结束**：`simulation.log` 第 37 行为唯一 `# RESULT: PASS inst_drm64_x32 tests=2449`（RESULT 行数 = 1）；第 38–39 行 `$finish : .../tb_inst_drm64_x32.sv(483)`、`Time: 133570 ns`；第 41 行 `Errors: 0, Warnings: 0`。无 FAIL/FATAL/Error/超时。
7. **无 RPC 故障**：`simulation.log` 与 `transcript` 中 `RPC_Init` 匹配数均为 **0**（`result.json.evidence.rpc_error_seen=false`），与三次失败形成对照。
8. **显式 batch transcript**：`transcript` 2864 字节、**非空**，41 行，与 `simulation.log` 内容一致（同一条原生输出流，未重复计数），同样含两条 04030130、八组 CHECK、`RESULT: PASS … tests=2449`、`$finish`、`Errors: 0, Warnings: 0`，无错误。
9. **result.json**：`status=MINI_INST_DRM64_BATCH_RESUME_KEY_TEST_PASS`、`functional_status=PASS`、`checks=2449`、`inputs_unchanged=true`、`git_snapshots_identical=true`、`isa_cases=[]`、`ip_spec_diagnostics=["04030130","04030130"]`、`pds_started=false`、`serial_opened=false`、`formal_board=NOT_TESTED`、`entry_contract` 与批处理契约一致。
10. **八份冻结副本**与当前工作副本逐一相同：`dual_sram_to_pango_ddr_bridge.v`、`tb_inst_drm64_x32.sv`、`resume_inst_drm64_batch.py`、`inst_drm64_batch_inputs.json`、`icache.v`、`dcache.v`、`ipm2l_sdpram_v1_10_icache.v`、`ipm2l_sdpram_v1_10_dcache.v`。
11. **git 快照**：`git_before.json` 与 `git_after.json` 内容哈希相同；233+5+2 与 179+2 输入在执行前后均保持。

## 4. 原始产物路径

`sim/mini_board_migration/build/ds_mini_idrm64_batch_20261013_a/`：`result.json`、`vlib.log`、`compile.log`、`simulation.log` 及三份 `command.json`、`transcript`、`git_before.json`、`git_after.json`、`work/`，以及上述八份冻结副本。

## 5. 与前三次失败的关系（如实记录，不越界）

- 三次失败（`ds_mini_idrm64_20261013_013143` 60 s、`..._diag_..._021854` 180 s、`..._cli_..._a` 180 s）都缺失功能证据并与 `RPC_Init … ::1 … couldn't open socket: invalid argument` 相关。本次改用文档支持的 `-batch` 模式后**未再出现该错误并正常结束**，说明 `-batch` 路径规避了原先的 RPC 初始化。
- 但这**不等于**宿主的 IPv6 环回限制已修复，也**不等于**已证明三次失败同因：原始 60 秒日志中并无 RPC 文本，只能作为假设；本报告不写“三次均已证同故障”，也不推断所有其他 ModelSim 调用必然失败。宿主/会话侧的具体策略原因仍未确定。
- 本次结论**仅覆盖**本 tag 的这一次 `-batch` 执行、这批受保护输入与本机 ModelSim 环境。

## 6. 未覆盖范围

- 无 ISA 抽测/全量、无 CPU 程序/Loader、无 Hello/短 CoreMark、无 DDR PHY、无历史套件；**x16 兼容数组分支本轮未仿真**（仅静态保留）。
- DDR 侧仍是**功能用户口模型**（无 Pango 控制器/PHY），不能作性能结论。
- 新 I64/D32 双 DRM 的**时序、资源（FF/LUT/DRM）、面积、功耗与实际 DDR 收益均未测量**；桥级 PASS 不等于完整 SoC 或实板 PASS；当前根位流 `d60f9ce2…` 仍属 I32/D32，不能当作 I64。
- 未执行 PDS 实现、未开串口、未上板、未提交或推送 Git；本候选的 I64 PDS 与实板均待执行。

## 7. 交回 Codex

按约定停在关键仿真。Codex 核验原始证据后连续衔接用户新 PDS：核来源（桥 `a0c4e2f6` 与两 IP IDF/生成源身份）、层次（两个 DRM 实例、x32 I/D 数据 FF 阵列消失、I valid64/tag64、D valid32/tag32、I 完整 2KiB 地址参与使用）、最终 seed/多角 setup/hold 汇总与 FF/LUT/DRM、Loader ROM/RAM INIT、原 120 次 BIN/ELF/manifest 与新位流 SHA。PDS 通过并下载后，由用户在 COM9 跑原 120 次 P/V 各 1 轮，新日志目录 `sim/mini_board_migration/board/coremark_i64_d32_01`，对照成功 I32/D32 `coremark_idrm_d32_01`（cycles 398389378 / 412352500，4.249486699 / 4.398426667 秒），原 BIN 不重建，不足 10 秒仅作同 BIN 比较。I64 功能已通过前，不开始 M/D64、写缓冲、提频等其他改动。
