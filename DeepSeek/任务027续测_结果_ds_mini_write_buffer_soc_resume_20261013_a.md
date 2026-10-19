# 任务027续测 结果：SoC 自检 RUN 补齐与精确陷阱复核 PASS（tag ds_mini_write_buffer_soc_resume_20261013_a）

**结论：`WRITE_BUFFER_SOC_REPAIR_AND_TWO_ISA_PASS`。四个 job 全部通过**：`old_program` 精确复现原故障、`soc` 修复后 414 项全过、两项 ISA 抽测（`isa_or`/`isa_lhu`）完成。原 027 的 `control`(8) 与前六组(426) 证据**直接复用**，本 tag 新增 414 项，当前关键检查合计 **840**。

> **重要口径**：`old_program` 的 PASS 是**诊断预测完全命中**（原程序仍为 FAIL，`original_functional_status=FAIL`），**不是**原程序功能通过；修复只落在**测试程序**（补写 TEST_STATUS=1 的 RUN），RTL/判据/清单未改。

## 1. 入口与身份

固定 tag `ds_mini_write_buffer_soc_resume_20261013_a` 启动前**不存在**；无 `pds_shell` 实现进程、无既有 `vsim/vsimk` 会话；未改权限/RPC/超时/源码/判据/清单。

```powershell
python -B sim/mini_board_migration/run_write_buffer_soc_resume.py --check-inputs
# 退出 0：INPUTS_MATCH_SOC_RESUME_HDL_NOT_RUN old-program exact diagnosis + SoC414 + ISA or/lhu; prior 426/control8 reused
python -B sim/mini_board_migration/run_write_buffer_soc_resume.py --tag ds_mini_write_buffer_soc_resume_20261013_a
# 退出 0：RESULT: PASS write-buffer SoC repair + precise old-program diagnosis + two pending ISA; board NOT_RUN
```

| 项目 | 实测 SHA256 | 与任务书 |
| --- | --- | --- |
| `myriscv/dual_sram_to_pango_ddr_bridge.v` | `b64f756d49a88f9001e12f45a4e9385bbbf245010777a35a430205b913ed251b` | 一致（027 失败时身份） |
| `myriscv/mycpu_sync.v` | `3faf81a6383d0f69bbb3d8c24083ffb3b5066830ddf3f2951c2b5f278f8055fb` | 一致 |
| `myriscv/data_bus_interconnect.v` | `e8582e27f88f0e5e2bf820e4f7088495f16cad3f4cd7a70a7ee4944d9c85524e` | 一致 |
| `myriscv/soc_top.v` | `3fdbe2f5a08a6759f2667d158b44d34d3158d1971ee52b11cbacfa33eb2a9716` | 一致 |
| 续测清单 `write_buffer_soc_resume_inputs.json` | `98aa2479a5fe08c3dfcf37d7af94a78752760f35fd596d6280272a6f96e001ea` | 一致 |

## 2. 命令矩阵（一次 vlib/vlog + 四次独立 vsim -batch）

| 命令 | 上限 | 用时 | exit | native | timed_out |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 60 s | 0.09 s | 0 | 0 | false |
| vlog | 60 s | 0.39 s | 0 | 0 | false |
| old_program | 180 s | 2.15 s | 0 | 0 | false |
| soc | 180 s | 2.07 s | 0 | 0 | false |
| isa_or | 180 s | 1.57 s | 0 | 0 | false |
| isa_lhu | 180 s | 1.55 s | 0 | 0 | false |

编译 **37 个唯一模块**、`Errors: 0, Warnings: 0`，顶层 `tb_write_buffer_soc_resume` 与 ISA 顶层；使用新库，未加载旧失败库。四个 job 的 console 均非空、**与 transcript 换行归一后全文相同**，`Errors: 0, Warnings: 0`，无 `FAIL`/`Fatal`/`RPC_Init`/`RUNNER TIMEOUT`。

## 3. `old_program`：原故障精确复现（诊断命中）

```text
# DIAG_TRAP pc=4000007c inst=00b52823 cause=7 tval=10000010 cpu_events=412 AW=67 W=67 selftest=0 busy=0 flow=0
# CHECK: original_missing_RUN_store_fault PASS pc=4000007c cause=7 tval=10000010
# RESULT: PASS write_buffer_old_program_diagnosis events=412 original_functional_status=FAIL
# ** Note: $finish : .../tb_write_buffer_soc_resume.sv(445)   Time: 33395 ns
# Errors: 0, Warnings: 0
```

预测的每一项都逐字命中：**trap PC `4000007c`、指令 `00b52823`、cause `7`、tval `10000010`**，陷阱前 **412** 事件，`AW=W=67`、`selftest=0`、`busy=0`、`flow=0`。即：原程序缺少 `TEST_STATUS` 的 RUN(1) 写入，`simple_mmio` 只允许 IDLE→RUN→PASS，于是 IDLE 直接写 PASS 被拒并使 store 错误映射为 **cause 7（store/AMO access fault）**、`tval=10000010`（MMIO 地址）——原 51575 ns 的“unexpected synchronous CPU trap”由此**得到精确复现与解释**。该 job 保留 **4 条 `04030130`** 原文。

**原失败结论不变**：这是诊断匹配，不是功能 PASS；原 `ds_mini_write_buffer_20261013_a` 的 `STOPPED_FIRST_FAILURE` 与原始日志未被改写。

## 4. `soc`：补写 RUN 后的正确路径

```text
# CHECK: real_soc_fence_irq_stop PASS checks=414
# RESULT: PASS write_buffer_soc_resume tests=414 cpu_events=414 IRQ=1 early_acks=67 I_OVERLAP=318 FENCE_WAIT=44 IRQ_WAIT=44 STOP_WAIT=44 fills=1 updates=65
# ** Note: $finish : .../tb_write_buffer_soc_resume.sv(515)   Time: 33620 ns
# Errors: 0, Warnings: 0
```

- 414 项与 414 个架构事件全部通过，**0 同步陷阱**；`IRQ=1`（精确中断）；
- **五个覆盖计数均为正**：`early_acks=67`、`I_OVERLAP=318`、`FENCE_WAIT=44`、`IRQ_WAIT=44`、`STOP_WAIT=44`；
- `fills=1`、`updates=65`，与任务书预测的 `fills=1 updates=65` 逐项相符；`RUN`/`PASS` 各写一次、自检 2、handler 寄存器 1、PERF DONE 3、冻结 `AW=67` 等由 TB 判据覆盖，FENCE/IRQ/MMIO/字节缓存/前后端守恒判据保持。
- 同样保留 **4 条 `04030130`** 原文。

## 5. 两项 ISA 抽测（原 027 未完成）

| 用例 | 冻结事件 | 实测事件 | 5 条 trap | tohost | muls |
| --- | ---: | ---: | --- | ---: | ---: |
| isa_or | 530 | **530** | 4×cause2（tval=指令编码，目标 800000e8/f8/118/130）+ 1×结束 ECALL cause11/tval0/→80000004 | 1 | 0 |
| isa_lhu | 320 | **320** | 同上（结束 ECALL 于 pc=80000478） | 1 | 0 |

逐事件架构字段与冻结成功事件一致（`architectural_events_identical=true`）；`CHECK/RESULT` 形如 `tohost=00000001 traps=5 probes=4 muls=0`。这两个 job 的 `IPSpecCheck` 为 0，符合任务书只要求两个 SoC job 各四条 04030130 的口径（ISA TB 不例化 DRM 桥）。

## 6. 事件 trace、输入/副本/Git 与旧证据保持

- **events.log 均非空且含 EV/BUS**：`old_program` 1234 行（EV 413 / BUS 821）、`soc` 1257 行（EV 419 / BUS 838）、`isa_or` 530 行（EV 530）、`isa_lhu` 320 行（EV 320）；诊断 trap 字段在 console 与 trace 中可查。
- **13 份执行副本**与当前工作副本逐份 SHA256 比对**零不匹配**；`git_before.json` 与 `git_after.json` 内容哈希相同。
- **旧失败目录 35 个文件完整保持**：`key.log`/`key.transcript` 仍在，`git_after.json` 与 `isa_or.log` **仍然缺失**（未补造、未改写）。
- `result.json`：`status=WRITE_BUFFER_SOC_REPAIR_AND_TWO_ISA_PASS`、`reused_control=8`、`reused_key_checks=426`、`aggregate_current_key_checks=840`、`inputs_unchanged=true`、`git_unchanged=true`、`board_status=NOT_RUN`、`PDS_started=false`、`serial_opened=false`。
- 执行后无残留 `vsim/vsimk/python` 进程。

## 7. 未覆盖范围

- 本 tag **未重跑** `control` 与前六组；426 与 8 是**复用原 027 原始证据**，因此不能声称原 839 项在本 tag 全部重跑 PASS；本 tag 新增的是 414 项 SoC 组 + 两项 ISA。
- x16 兼容路径本轮**仅静态**；未跑物理 PHY 训练联仿、CoreMark、Hello、历史 026 或全 ISA。
- 桥级/SoC 模型 PASS **不能替代 PHY、时序、资源或实际性能**；板级 `NOT_RUN`。
- 未执行 PDS、串口、上板、Git 提交推送，未执行 Codex 的只读复核脚本。

## 8. 交回 Codex

原始产物：`sim/mini_board_migration/build/ds_mini_write_buffer_soc_resume_20261013_a/`（六份 `command.json`、`vlib.log`、`compile.log`、四个 job 的 `console`/`transcript`/`events.log`、`inputs.json`、`inputs/`(13)、`git_before/after.json`、`result.json`）。

Codex 只读复核（`review_write_buffer_soc_resume.py`）通过后，功能门才开放 `run_write_buffer_soc_resume_measurements.ps1`；由用户自行 PDS 生成/下载，随后直接给 COM9 同冻结 P300/V300 各一次（新目录 `coremark_i64_d64_zmmul_wbuf_300_01`，对照成功 `turnover_300_01` P 283353216 / V 282589565 cycles）。功能完整核验通过前不进入上板。
