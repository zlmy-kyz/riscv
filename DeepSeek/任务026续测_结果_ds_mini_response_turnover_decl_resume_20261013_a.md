# 任务026续测 结果：TB 声明顺序修复后单次验证 PASS（tag ds_mini_response_turnover_decl_resume_20261013_a）

**结论：`RESPONSE_TURNOVER_KEY_TEST_PASS`，`functional_status=PASS`，七组 1832 项检查全部通过。**
修复后的 TB 编译 **20 个设计模块 `Errors: 0, Warnings: 0`**，仿真正常 `$finish`；唯一结果
`RESULT: PASS response_turnover_x32 tests=1832 cpu_events=392 turnovers=1744 I_TURN=1002 D_TURN=742 CPU_TURN=522 fills=71 updates=97`（`fills=71`/`updates=97` 与静态预期完全一致，各接续计数均为正数）。**CPH/桥 RTL 未改、判据未放宽**；本轮**不代表 SoC/MMIO/Loader/PHY/全 ISA/板级 PASS**。

## 1. 入口与身份

新固定 tag `ds_mini_response_turnover_decl_resume_20261013_a` 启动前确认**不存在**；无 `pds_shell` 实现进程、无既有 `vsim/vsimk` 会话；未改权限/RPC/IPv6/工具配置，无启动预检。**原失败 tag `ds_mini_response_turnover_20261013_a` 未被复用、未清理、未覆盖。**

```powershell
python -B sim/mini_board_migration/resume_response_turnover.py --check-inputs
# 退出 0：INPUTS_MATCH_RESPONSE_TURNOVER_HDL_NOT_RUN tests=1832 cpu_events=392 groups=7
python -B sim/mini_board_migration/resume_response_turnover.py --tag ds_mini_response_turnover_decl_resume_20261013_a
# 退出 0：RESULT: PASS response turnover key suite; board performance NOT_RUN
```

| 项目 | 值 |
| --- | --- |
| 桥（未改） | `myriscv/dual_sram_to_pango_ddr_bridge.v` SHA256 `f47ca39df5b17968e653afabd80ab62564d23cd227a71290c5673c96703ba224` |
| CPU（未改） | `myriscv/mycpu_sync.v` SHA256 `43e451038cc14b3402ff159629d18783fbd8d1364e7c05197fadbb1e8e5d6cfe` |
| 续测清单 | `sim/mini_board_migration/response_turnover_decl_resume_inputs.json` SHA256 `9bfa2e520077d5f5f3c7e3ae8bd1f0c2845315d0820361e37bc620a2c003e218` |
| 修复后 TB | `sim/mini_board_migration/tb_response_turnover_x32.sv` SHA256 `bc99d609756e911c08d8d4468fb8c65be414d2cc43c30fb10cd2787abc35a30f`（失败版为 `fc524cf4…601b5`） |
| Git HEAD（前后一致） | `7af48d2185bc01a62be528c70b83c42689394c31` |

## 2. 三条命令、退出码与时长

| 命令 | 上限 | 用时 | exit_code | native_exit_after_wait | timed_out |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 60 s | 0.10 s | 0 | 0 | false |
| vlog | 60 s | 0.27 s | 0 | 0 | false |
| vsim | 180 s | **2.82 s** | 0 | 0 | false |

- 编译 **20 个设计模块**、`Errors: 0, Warnings: 0`：`GTP_GRS, GTP_DRM36K_E1, GTP_APM_E2, ipm2l_sdpram_v1_10_icache, ipm2l_sdpram_v1_10_dcache, icache, dcache, alu, br_alu, l_alu, regfile, csr_file, mycpu_sync, mul, ipm2l_mult_v1_3_mul, ipm2l_apm_data_pipeline, ipm2l_apm_distributed_sdpram, ipm2l_apm_distributed_shiftregister, dual_sram_to_pango_ddr_bridge, tb_response_turnover_x32`（真实 CPU/I·D·mul IP + 三厂家原语 + 桥 + 单顶层 TB）。
- vsim 使用 `-batch`、单顶层 `tb_response_turnover_x32`、同一 `CPU_IMAGE`/`+incdir`、原生直写、`run -all; quit -f`；外层异步 session 未提前终止。

## 3. 七组 CHECK 与唯一 RESULT（逐字）

```text
# CHECK: instruction_hit_stream PASS checks=576
# CHECK: data_hit_stream PASS checks=576
# CHECK: alternating_response_owner PASS checks=128
# CHECK: write_hit_turnover_ordering PASS checks=128
# CHECK: read_miss_turnover PASS checks=24
# CHECK: reset_and_initialization PASS checks=8
# CHECK: real_cpu_ddr_loop PASS checks=392
# RESULT: PASS response_turnover_x32 tests=1832 cpu_events=392 turnovers=1744 I_TURN=1002 D_TURN=742 CPU_TURN=522 fills=71 updates=97
```

| 组 | 检查数 | 结果 |
| --- | ---: | --- |
| instruction_hit_stream | 576 | PASS |
| data_hit_stream | 576 | PASS |
| alternating_response_owner | 128 | PASS |
| write_hit_turnover_ordering | 128 | PASS |
| read_miss_turnover | 24 | PASS |
| reset_and_initialization | 8 | PASS |
| real_cpu_ddr_loop | 392 | PASS |
| 合计 | **1832** | 与 `tests=1832` 相符 |

顺序与数量与任务书完全一致；`turnovers=1744`、`I_TURN=1002`、`D_TURN=742`、`CPU_TURN=522` 全部为正，`fills=71`、`updates=97` 与静态预期逐项相符。

## 4. 日志、提示与结束状态

- `simulation.log`：`CHECK` 行 = 7、`RESULT:` 行 = **1**、`$finish` = 1、`Errors: 0, Warnings: 0` = 1；`RESULT: FAIL`/`** Error|Fatal`/`RPC_Init`/`RUNNER TIMEOUT` 匹配数 = **0**。
- **两条厂家 `04030130` 原文保留**（真实 I/D DRM 逻辑深度地址提示，各一条）：

  ```text
  # IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
  # IPSpecCheck: 04030130 ipm2l_flex_sdpram parameter setting error !!!: c_WR_ADDR_WIDTH must between 9-20 when DRM Resource is 36K
  ```

- 正常结束：`$finish : .../response_turnover_cases.svh(290)`，`Time: 46860 ns`；`End time: 18:45:30`，ModelSim `Elapsed time: 0:00:02`。
- `console` 4585 字节与 `transcript` 4533 字节**非空且换行归一后全文相同**。

## 5. 输入、副本与 Git 守恒

- `result.json`：`status=RESPONSE_TURNOVER_KEY_TEST_PASS`、`functional_status=PASS`、`tests=1832`、`cpu_events=392`、`turnovers/I_TURN/D_TURN/CPU_TURN=1744/1002/742/522`、`fills=71`、`updates=97`、`inputs_unchanged=true`、`git_unchanged=true`、`CPU_changed=false`、`PDS_started=false`、`serial_opened=false`。
- **21 份冻结副本**齐全，逐份 SHA256 与当前工作副本比对**零不匹配**。
- `git_before.json` 与 `git_after.json` 内容哈希相同（HEAD `7af48d2185bc01a62be528c70b83c42689394c31`）。
- **原失败目录 30 个文件全部保持**：其 `git_after.json` 与 `simulation.log` **仍然缺失**（未补造、未推断 Git 前后相等），原失败报告与清单未被改动。
- 执行后无残留 `vsim/vsimk/python` 进程。

## 6. 实际产物路径

`sim/mini_board_migration/build/ds_mini_response_turnover_decl_resume_20261013_a/`：`result.json`、`vlib.log`、`compile.log`、`simulation.log` 及三份 `command.json`、`transcript`、`git_before.json`、`git_after.json`、`inputs.json`、`inputs/`（21 份冻结副本）、`work/`。

## 7. 未覆盖范围

- 仅为 **x32 桥 + 真实 CPU/I·D·mul IP** 的关键功能与最小 CPU 集成验证：**不构成全 SoC、MMIO、Loader、DDR PHY、全 ISA、时序、资源或板级 PASS**。
- x16 兼容分支本轮**仅静态**，未仿真。
- 未运行 PDS、串口、上板、Git 提交推送、启动预检或任何历史测试；未执行 Codex 的审查脚本（按约定由 Codex 执行）。
- 板级性能 `NOT_RUN`；固定软件 BIN 未重建。

## 8. 交回 Codex

原始证据齐备（三 command.json exit/native 0、20 模块编译 0 错、1832 项、唯一 RESULT、两条 04030130、console/transcript 一致、21 副本、Git 前后相同）。Codex 独立核验后可直接给出 COM9 同 P300/V300 的命令：新日志目录 `sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01`，对照刚成功的 `coremark_i64_d64_zmmul_dwh_300_01`（P 395967938 / V 395398048 cycles）；原 BIN 不重建、不重跑旧基线，不足 10 秒只作性能比较。本轮不代为执行上板工具，也不例行审 PDS/位流。
