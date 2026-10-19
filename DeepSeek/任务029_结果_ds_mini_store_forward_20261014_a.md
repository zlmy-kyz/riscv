# 任务029 结果：写缓冲字节转发与同行命中读关键仿真 PASS（tag ds_mini_store_forward_20261014_a）

**结论：`STORE_FORWARD_KEY_PASS`。`control`（关闭转发）8 项与 `key` 八组 **2238** 项全部通过。**

唯一结果
`RESULT: PASS store_forward_x32 tests=2238 cpu_events=489 IRQ=1 early_acks=308 I_OVERLAP=515 FENCE_WAIT=44 IRQ_WAIT=44 STOP_WAIT=44 fills=2 updates=69 D_OVERLAP=1318 SOC_D_OVERLAP=130 SAME_LINE=1314 WORD_FORWARD=347 SOC_SAME_LINE=130 SOC_WORD_FORWARD=130 COLLISION_BLOCKS=16 RSP_W_OVERLAP=16`

——五个等待/重叠覆盖数均为正，`SOC_SAME_LINE`/`SOC_WORD_FORWARD` 均为正，且 **`SAME_LINE − SOC_SAME_LINE = 1314 − 130 = 1184`**、**`WORD_FORWARD − SOC_WORD_FORWARD = 347 − 130 = 217`**，与任务书要求的手工同行读 1184 / 同字转发读 217 一致（不是只看 PASS 字样）；`COLLISION_BLOCKS=16 ≥ 16`、`RSP_W_OVERLAP=16 ≥ 16`。仅主桥改动；**CPU 未改、ISA=0**。**不代表全 SoC/全 ISA/PHY/时序/实板 PASS**。

## 1. 入口与身份

固定 tag `ds_mini_store_forward_20261014_a` 启动前**不存在**（`build/` 下无该目录）；无 `pds_shell` 实现进程、无既有 `vsim/vsimk` 会话；未改 RTL/TB/模型/判据/清单/超时/权限/RPC；执行后无残留 `vsim/vsimk/pds_shell` 进程。

```powershell
python -B sim/mini_board_migration/run_store_forward.py --check-inputs
# 退出 0：INPUTS_MATCH_STORE_FORWARD_HDL_NOT_RUN key=2238 control=8 ISA=0 CPU489
python -B sim/mini_board_migration/run_store_forward.py --tag ds_mini_store_forward_20261014_a
# 退出 0：RESULT: PASS store-forward key + minimal disabled control; board NOT_RUN
```

| 项目 | 实测 SHA256 | 与任务书 |
| --- | --- | --- |
| `myriscv/dual_sram_to_pango_ddr_bridge.v` | `355145f2fca4c08cac12525f7ab16a2faae7466953baf49fc021c7bce413d7aa` | 一致（改前 `3e1e6f98…876794`） |
| `myriscv/mycpu_sync.v` | `3faf81a6383d0f69bbb3d8c24083ffb3b5066830ddf3f2951c2b5f278f8055fb` | 未改（与 027/028 相同） |
| 清单 `store_forward_inputs.json` | `468881648582eabe4db783ea17fd3d7085401436d1f44767492be5d395c94494` | 一致（268 工程文件 + 10 外部 + 11 副本 + 36 模块） |
| `tb_store_forward_x32.sv` | `9a46e76dc3dbdb18c07b0f224630ec04f32156ccaf7cda2680ac9f15ddfb0e4a` | 与 `generate_store_forward_tb.build_tb()` 逐字节一致 |

SoC 指令镜像 `build/store_forward_preparation_20261013_a/soc_program.hex` SHA256 `d873e0f318e26a5c7723ffa5ba5311c52a9c3494c22ca21f3b9de56c3fdd9291`，为 029 固定输入副本之一。

## 2. 命令矩阵

| 命令 | 上限 | 用时 | exit | native | timed_out |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 60 s | 0.34 s | 0 | 0 | false |
| vlog(compile) | 60 s | 0.94 s | 0 | 0 | false |
| control（`FORWARD_ENABLE=0`） | 180 s | 2.54 s | 0 | 0 | false |
| key（`FORWARD_ENABLE=1`） | 180 s | 6.72 s | 0 | 0 | false |

编译 **36 个唯一模块**、单顶层 `tb_store_forward_x32`、`Errors: 0, Warnings: 0`。加载的真实模块：`dual_sram_to_pango_ddr_bridge`、`soc_top`、`mycpu_sync`（`regfile`/`alu`/`mul`+`ipm2l_mult_v1_3_mul`/`l_alu`/`csr_file`/`br_alu`）、`inst_bus_interconnect`/`inst_bram_adapter`/`inst_rom`+厂家 `ipm2l_rom_v1_8_inst_rom`/`ipm2l_spram_v1_8_inst_rom`、`data_bus_interconnect`/`data_bram_adapter`/`data_ram`+厂家 `ipm2l_spram_v1_8_data_ram`、`simple_mmio`、`uart_mmio`(`uart_tx`/`uart_rx`/`uart_rx_fifo`)、`icache`/`ipm2l_sdpram_v1_10_icache`、`dcache`/`ipm2l_sdpram_v1_10_dcache`、`ipm2l_apm_data_pipeline`/`ipm2l_apm_distributed_shiftregister`/`ipm2l_apm_distributed_sdpram`、`GTP_APM_E2`、`GTP_DRM36K_E1`、`cpu_perf_counters`、`GTP_GRS`。

两 job 均 `Errors: 0, Warnings: 0`、正常 `$finish`（control 于 690 ns、key 于 114920 ns），无 `FAIL`/`Fatal`/`RPC_Init`/`RUNNER TIMEOUT`，**console 与 transcript 换行归一后全文一致**（control 5949 字符、key 6575 字符，逐字节相等）；两 job 各 **4 条厂家 `04030130`** 原样保留。

## 3. control（关闭转发）证据

```text
# CHECK: disabled_store_forward_control PASS checks=8
# RESULT: PASS store_forward_control tests=8
# ** Note: $finish ... tb_store_forward_x32.sv(608)   Time: 690 ns
# Errors: 0, Warnings: 0
```

即 `DATA_STORE_FORWARD_ENABLE=0` 时回到 028 语义：**同行读仍等 W 完成**，其他行命中读仍可重叠；`same_reads`/`word_forwards` 计数器保持 0，TB 以 `if(same_reads || word_forwards) $fatal(...)` 断言**无同行/同字转发事件**。控制 job 无真实 SoC，`control.events.log` 为 **0 字节（空）**，任务书允许。

## 4. key 八组 CHECK（逐字）

```text
# CHECK: forward_response_owner_clear PASS checks=8
# CHECK: all_write_read_words_byte_masks PASS checks=1280
# CHECK: all_line_indices_forward PASS checks=320
# CHECK: unaligned_byte_half_packets PASS checks=24
# CHECK: miss_alias_and_store_order PASS checks=12
# CHECK: W_accept_and_response_boundaries PASS checks=96
# CHECK: reset_init_forward_metadata_clear PASS checks=9
# CHECK: real_soc_store_forward_typed_loads PASS checks=489
# RESULT: PASS store_forward_x32 tests=2238 cpu_events=489 IRQ=1 early_acks=308 I_OVERLAP=515 FENCE_WAIT=44 IRQ_WAIT=44 STOP_WAIT=44 fills=2 updates=69 D_OVERLAP=1318 SOC_D_OVERLAP=130 SAME_LINE=1314 WORD_FORWARD=347 SOC_SAME_LINE=130 SOC_WORD_FORWARD=130 COLLISION_BLOCKS=16 RSP_W_OVERLAP=16
# ** Note: $finish ... tb_store_forward_x32.sv(710)   Time: 114920 ns
# Errors: 0, Warnings: 0
```

| 组 | 项数 | 验证内容 | 结果 |
| --- | ---: | --- | --- |
| forward_response_owner_clear | 8 | 转发 D 旧响应与 I 新请求同拍交接，其他行读无 mask 污染 | PASS |
| all_write_read_words_byte_masks | 1280 | 8 写槽 × 16 mask × 8 读槽，AW 前/W 前阻塞交替，zero/partial/full 及邻字 | PASS |
| all_line_indices_forward | 320 | 64 行索引，写字/邻字提前读及实际 DDR 读回 | PASS |
| unaligned_byte_half_packets | 24 | 4 字节偏移及 2 合法半字位置的移位 data/strobe，raw32 返回 | PASS |
| miss_alias_and_store_order | 12 | 写 miss 无缓存基础不转发；同索引不同完整 tag 防误转发；新 store 满条等待 | PASS |
| W_accept_and_response_boundaries | 96 | 16 mask × 两个 W 边界，强制 `w_wait=0` 后测碰撞门与旧响应消费 | PASS |
| reset_init_forward_metadata_clear | 9 | 接受后未消费的转发响应 reset 取消；init 清 tag/资格后不得拿旧基础值转发 | PASS |
| real_soc_store_forward_typed_loads | 489 | 实际 CPU 逐退休，同字 RAW 循环及 SB/SH 后的有符号/无符号 load | PASS |
| 合计 | **2238** | 与 `tests=2238` 相符 | |

覆盖计数核对（逐项验算）：`early_acks=308`、`I_OVERLAP=515`、`FENCE_WAIT=44`、`IRQ_WAIT=44`、`STOP_WAIT=44` 均 > 0；`SOC_SAME_LINE=130>0`、`SOC_WORD_FORWARD=130>0`；**`SAME_LINE−SOC_SAME_LINE=1184`**、**`WORD_FORWARD−SOC_WORD_FORWARD=217`**；`COLLISION_BLOCKS=16`、`RSP_W_OVERLAP=16`。`fills=2`、`updates=69` 为 **SoC 组增量**（不含手工测试），按要求口径记录，不当作总数；同字事件计数包含 zero mask 用例，**不等同转发字节数**。

TB 在 `checkpoint("reset_init_forward_metadata_clear")` 之后以 `$fatal` 精确断言手工覆盖率与守恒：`same_reads==1184`、`word_forwards==217`、`collision_blocks==16`、`response_w_overlap==16`、`pushes==completions+cancelled`、`cancelled==1`（入条 = 完成 + reset 取消 1）。

## 5. 真实 SoC / typed load / 独立记分板

- **CPU 组守恒**：`pushes−base_pushes=71`、`completions−base_completions=71`、`cancelled−base_cancelled=0`（71 入条 = 71 W 完成 / 0 取消）；`d_overlap−base_d_overlap>0`、`same_reads−base_same>0`、`word_forwards−base_word>0`；`aw_count==w_count==71`。
- **程序与事件**：`cpu_events==489`、`IRQ=1`，程序共 48 条静态指令，`loop@72`、`PASS@176`、`done@180`、`handler@256`（`.org 0x100`）。MMIO 语义按命令字核对：PERF START/STOP 各 1 次（STOP 要求 `w_count==71`）、`TEST_STATUS RUN`/`PASS` 各 1 次，PERF 冻结后 `state==3` 且 `count[12]==71`（冻结 AW 记为该测试程序的 71）。
- **typed load**：golden 逐退休解释器对**每条** `normal_retire`/`mret_commit`/`irq_take` 逐寄存器比对（含 LB/LBU/LH/LHU 的 8/16 位符号/零扩展），全部 489 事件一致。程序 `sb x6(=0x80),1(x1)` 后：**LB=−128（0xFFFFFF80）、LBU=128、LH=−128、LHU=65408**；最终存回 `final word64=64`、`sum=2080`、`mem[66]=1/1`。全程 `DIAG_TRAP=0`，**无同步 trap**。
- **独立记分板**：`architectural_word()` 用**已接受 store 的地址/data/mask**在自有参考内存上覆盖，读值期望**只取自该架构模型**，不取 DUT 转发字段；cache 写边沿仍以实际后端 W 与 `oracle_valid/oracle_tag` 核对（`cache_we` 与期望边沿不符即 `$fatal`）。凡同行 D 接受与后端 W **同边沿**（`backend_write && pending_tag==bda[31:5]`）直接 `$fatal`。

## 6. 事件 trace 与提示

- `key.events.log` 252062 字节、非空：**EV 494 行 / BUS 1129 行**，无其他格式行；同步陷阱按严格判据处理（本次无陷阱）。
- `control.events.log` 为 **0 字节（空）**——控制 job 未进入 SoC，任务书允许。
- 两 job 各 **4 条厂家 `04030130`**（手工桥与真实 SoC 桥各一对 I/D IP）原文完整保留，未改成零 warning 要求。

## 7. 输入、副本与 Git 守恒

- `result.json`：`status=STORE_FORWARD_KEY_PASS`、`manifest_sha256=468881648582…4494`、`completed={control:8, key:2238/489/IRQ1/early_acks308/I_OVERLAP515/FENCE_WAIT44/IRQ_WAIT44/STOP_WAIT44/fills2/updates69/D_OVERLAP1318/SOC_D_OVERLAP130/SAME_LINE1314/WORD_FORWARD347/SOC_SAME_LINE130/SOC_WORD_FORWARD130/COLLISION_BLOCKS16/RSP_W_OVERLAP16}`、`inputs_unchanged=true`、`git_unchanged=true`、`CPU_changed=false`、`PDS_started=false`、`serial_opened=false`、`board_status=NOT_RUN`。
- **268 份工程登记源 + 10 份外部输入**逐份 SHA256 与清单比对**零不匹配**；`require_inputs()` 在执行前后各比对一次并相等。
- **11 份执行副本**（桥 / 生成器 / 准备 / 审查 / runner / cases.svh / SoC.S / TB / soc_program.hex / 测量 py+ps1）与当前工作副本逐份一致。
- `git_before.json` 与 `git_after.json` 内容哈希相同（`dcd0ef2f…87c1`，各 1059796 字节）。
- 原成功/失败证据目录（含 027/028 结果目录、`store_forward_preparation_20261013_a/before` 与 `bridge.patch`）均**保持未动**。

## 8. 未覆盖范围

- x16 兼容路径本轮**仅静态**；未跑 PHY 训练联仿、CoreMark、历史 ISA/CPU 重跑或 028 全套复跑。
- 仅为 **x32 桥 + 真实 CPU/SoC 模型**的关键功能与最小真实集成：**不能替代 PHY、时序、资源或实际性能**；板级 `NOT_RUN`，新功能实际收益未测。
- 未执行 PDS、串口、上板、Git 提交推送；未执行 Codex 的 `review_store_forward.py`。

## 9. 交回 Codex

原始产物：`sim/mini_board_migration/build/ds_mini_store_forward_20261014_a/`（四份 `command.json`、`vlib.log`、`compile.log`、`control`/`key` 的 `console`/`transcript`/`events.log`、`inputs.json`、`inputs/`(11)、`git_before/after.json`、`result.json`）。

Codex 用 `review_store_forward.py` 核原始证据通过后，可直接给 PowerShell `run_store_forward_measurements.ps1` 的 COM9 命令：新日志 `coremark_i64_d64_zmmul_sfwd_300_01`，同冻结 Zmmul P300/V300 各一次，对照成功 `dread_300_01`（P 231832909 / V 231467889 cycles，2.472884 / 2.468991 秒）；BIN / 300 次 / CRC 5275-8803 保持，不例行核 PDS/位流。收到实板日志后再核协议/DDR VERIFY/五 CRC/计数与同 BIN，并分析新收益。
