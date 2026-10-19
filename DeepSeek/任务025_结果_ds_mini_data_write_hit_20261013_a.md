# 任务025 结果：D 缓存写命中更新关键仿真 PASS（tag ds_mini_data_write_hit_20261013_a）

**结论：`DATA_WRITE_HIT_KEY_TEST_PASS`，`functional_status=PASS`，七组 945 项检查全部通过。**
`RESULT: PASS data_write_hit_x32 tests=945 fills=80 updates=135`（fills/updates 均为正）。本轮只验证 **x32 桥的 D 写命中局部更新（byte enable）**；CPU 未改（ISA=0）、DDR 控制器/握手/共享仲裁/响应时刻未改。**不代表 SoC 执行、PHY、时序、资源或板级 PASS**。

## 1. 入口与身份

固定 tag `ds_mini_data_write_hit_20261013_a` 启动前确认**不存在**（未换 tag、未清理）；无 `pds_shell` 实现进程（仅剩空闲 PDS GUI）；原权限/RPC/IPv6/工具配置未动，无额外启动预检。

```powershell
python -B sim/mini_board_migration/run_data_write_hit.py --check-inputs
# 退出 0：INPUTS_MATCH_WRITE_HIT_NOT_SIMULATED checks=945 groups=7 real I/D DRM; CPU/DDR controller unchanged
python -B sim/mini_board_migration/run_data_write_hit.py --tag ds_mini_data_write_hit_20261013_a
# 退出 0：RESULT: PASS data_write_hit key group; board/timing NOT_RUN
```

| 项目 | 值 |
| --- | --- |
| 新桥（仅本轮改动） | `myriscv/dual_sram_to_pango_ddr_bridge.v` SHA256 `90385fdda4b5eb5018e988187827c3675558ae7ce19cf6b9e53a992c519f4b44` |
| 清单 | `sim/mini_board_migration/data_write_hit_inputs.json` SHA256 `7d88cd3ef7f31af185531cd0358498810336710029c1284ac310bb5d44b06133` |
| D 字节写 wrapper | `ipcore/dcache/dcache.v` SHA256 `bf62d32342a11ba6fad55f11c2413716a834c7028e9a1d8660a5f1a5477514a7`（IDF `60e668a1…efa51`） |
| CPU（未改，仅身份） | `myriscv/mycpu_sync.v` SHA256 `43e451038cc14b3402ff159629d18783fbd8d1364e7c05197fadbb1e8e5d6cfe` |
| Git HEAD（前后一致） | `7af48d2185bc01a62be528c70b83c42689394c31` |

## 2. 三条命令、退出码与时长

编译 **8 个设计模块**、唯一顶层 `tb_data_write_hit_x32`，`Errors: 0, Warnings: 0`：
`GTP_GRS, GTP_DRM36K_E1, ipm2l_sdpram_v1_10_icache, ipm2l_sdpram_v1_10_dcache, icache, dcache, dual_sram_to_pango_ddr_bridge, tb_data_write_hit_x32`（真实 I/D 四生成源 + 厂家两原语 + 主桥 + 新 TB，无行为替身）。

| 命令 | 上限 | 用时 | exit_code | native_exit_after_wait | timed_out |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 60 s | 0.15 s | 0 | 0 | false |
| vlog | 60 s | 0.26 s | 0 | 0 | false |
| vsim | 180 s | **1.61 s** | 0 | 0 | false |

vsim 实际 argv：`vsim.exe -batch -lib <tag>\work tb_data_write_hit_x32 -logfile <tag>\transcript -do "run -all; quit -f"`，工作目录为 tag 目录，stdout/stderr 原生直写文件；外层未提前终止规定 180 秒的 vsim（异步 session 跟进），`cleanup=null`。

## 3. 七组 CHECK 与唯一 RESULT（逐字）

```text
# CHECK: full_fill_byte_enable PASS
# CHECK: masked_hit_all_lanes PASS
# CHECK: no_allocate_tag_conflict PASS
# CHECK: write_completion_and_backpressure PASS
# CHECK: instruction_invalidation_and_zero_mask PASS
# CHECK: reset_before_aw_during_w_after_write PASS
# CHECK: initialization_loss PASS
# RESULT: PASS data_write_hit_x32 tests=945 fills=80 updates=135
```

| 组 | 检查数 | 结果 |
| --- | ---: | --- |
| full_fill_byte_enable | 512 | PASS |
| masked_hit_all_lanes | 384 | PASS |
| no_allocate_tag_conflict | 8 | PASS |
| write_completion_and_backpressure | 16 | PASS |
| instruction_invalidation_and_zero_mask | 12 | PASS |
| reset_before_aw_during_w_after_write | 9 | PASS |
| initialization_loss | 4 | PASS |
| 合计 | **945** | 与 `tests=945` 相符 |

顺序与数量与任务书完全一致；`fills=80`、`updates=135` 均为正数。

## 4. 日志与结束状态

- `simulation.log`：`CHECK` 行 = 7、`RESULT:` 行 = **1**、`$finish` = 1、`Errors: 0, Warnings: 0` = 1；`RPC_Init`/`RUNNER TIMEOUT`/`RESULT: FAIL`/`** Error|Fatal` 匹配数 = **0**。
- **两条厂家非致命提示原文保留**（旧 IP 逻辑深度地址提示，I/D 各一条）：

  ```text
  # IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
  # IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
  ```

- 正常结束：`$finish : .../tb_data_write_hit_x32.sv(338)`，`Time: 47380 ns`；`End time: 16:32:10`，ModelSim `Elapsed time: 0:00:01`。
- `console`（2705 字节）与 `transcript`（2665 字节）**非空且换行归一后全文相同**（已核对）。

## 5. 冻结输入、副本与 Git 守恒

- `result.json`：`status=DATA_WRITE_HIT_KEY_TEST_PASS`、`expected_checks=945`、`tests=945`、`fills=80`、`updates=135`、`inputs_unchanged=true`、`git_unchanged=true`、`CPU_changed=false`、`PDS_started=false`、`serial_opened=false`、`board=NOT_RUN`、`scope="Real I/D DRM and x32 bridge only"`。
- **10 份新增冻结副本**逐份 SHA256 与当前工作副本相同：`dcache.idf`、`dcache.v`、`ipm2l_sdpram_v1_10_dcache.v`、`dual_sram_to_pango_ddr_bridge.v`、`prepare_data_write_hit.py`、`review_data_write_hit.py`、`run_data_write_hit.py`、`tb_data_write_hit_x32.sv`、`run_data_write_hit_measurement.py`、`run_data_write_hit_measurements.ps1`。
- `git_before.json` 与 `git_after.json` 内容哈希相同（HEAD `7af48d2185bc01a62be528c70b83c42689394c31`）；执行后无残留 `vsim/vsimk/python` 进程。
- 未修改 RTL 之外任何内容：本轮除 runner 写入本 tag 外未写文件；未改动旧 tag/旧报告/清单/成功镜像。

## 6. 实际产物路径

`sim/mini_board_migration/build/ds_mini_data_write_hit_20261013_a/`：`result.json`、`vlib.log`、`compile.log`、`simulation.log` 及三份 `command.json`、`transcript`、`git_before.json`、`git_after.json`、`inputs.json`、`inputs/`（10 份冻结副本）、`work/`。

## 7. 未覆盖范围

- 仅为 **x32 桥 + 真实 I/D DRM** 的关键功能仿真：**不构成 SoC 执行、DDR PHY、时序、资源或板级 PASS**；根位流 `64445ecf…8ee4` 仍是上轮 D 写失效版本，源码新逻辑不会自动改变已下载硬件。
- x16 兼容分支本轮**未仿真**（按任务仅静态保留），不宣称新 x16 功能 PASS。
- 未重跑 023/024/022/旧版/ISA/CoreMark/Hello/PHY/Loader，未跑新 300 全仿真或物理 DDR；未执行 PDS、未开串口/上板、未提交或推送 Git。
- 本轮未运行 Codex 的只读审查脚本（`review_data_write_hit.py` 按约定由 Codex 执行）。

## 8. 交回 Codex

Codex 按计划运行只读 `review_data_write_hit.py` 核原始证据后，衔接用户 PDS：核最终多角时序/资源、实际字节写端口映射、137 登记源与 Loader INIT、新位流 SHA（当前 `pds_review`/工具 gate 尚未生成，`board`/`timing` 均 NOT_RUN）。PDS 通过并下载新位流后，用户在 COM9 用冻结 P300/V300 各一次，日志目录 `sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01`，对照已有成功 `sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul`（P 511184720 / V 509875909 cycles）；不重建 BIN、不重复历史测量，不足 10 秒仍只作比较。
