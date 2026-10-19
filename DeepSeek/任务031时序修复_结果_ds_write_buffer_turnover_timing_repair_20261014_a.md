# 任务031时序修复 结果：x32响应寄存器使能关键仿真（`ds_write_buffer_turnover_timing_repair_20261014_a`）

**状态：`TASK031_TIMING_REPAIR_KEY_PASS`。一次执行完成，未重试、未改任何文件。**

- 三条命令（`--check-inputs`、`vlib`、`vlog`、`key vsim`）全部正常：exit/native 0、未超时、`Errors: 0, Warnings: 0`、正常 `$finish`、console 与 transcript 归一后逐字相同。
- key：**889 项检查全 PASS / 430 EV 严格比对通过 / 短程序 44 拍、6 store、5 机会、5 接受**；受控模型相对已核 control 省 **5 拍**。
- 独立 BUS 复核（AW/W/data/strobe 守恒、DRM 字节更新、转发与冲突、143 条真实 CPU 请求、IRQ/FENCE/MMIO 排空）全部通过。
- **PDS 时序 `NOT_RUN`**：本仿真不能证明 −1.002 ns WNS/149 端点已修复，需用户重新实现后的新 PDS 报告。

原始目录：`sim/write_buffer_turnover/build/ds_write_buffer_turnover_timing_repair_20261014_a/`
`result.json`：`status=TASK031_TIMING_REPAIR_KEY_PASS`、`inputs_unchanged=true`、`git_unchanged=true`、`control_reused=true`、`controlled_cycles_saved=5`、`serial_opened=false`、`PDS_started=false`、`board=NOT_RUN`、`timing=NOT_RUN`。

## 1. 真实命令与元数据（runner 原生直写，未倒填）

| # | 命令 | exit | native | elapsed(s) | 上限(s) | timed_out |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `python -B sim/write_buffer_turnover/simulation_timing_repair.py --check-inputs` | 0 | — | — | — | — |
| 2 | `vlib <run>/work` | 0 | 0 | 0.1561 | 60 | false |
| 3 | `vlog -sv +incdir… -work <run>/work <3 厂家源><33 工程源> <TB>` | 0 | 0 | 0.4503 | 60 | false |
| 4 | `vsim -batch -lib <run>/work tb_write_buffer_turnover_completion -gPOSTED=1 -gTURNOVER=1 …` | 0 | 0 | 2.7341 | 180 | false |

第 1 条输出：`RESULT: PASS timing repair frozen inputs; HDL NOT_RUN; ISA=0`。
第 4 条输出：`RESULT: PASS Task031 timing repair key889 EV430; PDS timing NOT_RUN`。
编译：`-- Compiling module` 共 **36** 个，`Errors: 0, Warnings: 0`；每个 job 4 条 `IPSpecCheck: 04030130` 原文保持。

## 2. 身份与封存（执行前）

| 项 | 值 |
| --- | --- |
| 清单 `simulation_timing_repair_inputs.json` SHA256 | `c552686a8f4b96d6b71df53055b17519ae5b7784c0266884432fa84662036aff` ✔ |
| 新 tag 目录 | 执行前不存在 ✔ |
| `pds_shell` 并发 | 0 ✔ |
| 桥 `myriscv/dual_sram_to_pango_ddr_bridge.v` | `97273a85137600e596b38a3e061cf2841bf24bc397bf9412688cd580fa164c20`（新）✔，副本与工作树一致 |
| CPU `myriscv/mycpu_sync.v` | `b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3`（未变）✔ |
| 输入集合 | 211 工程 + 3 厂家 + 3 工具；214 份副本落盘；两个 `*_init_param.v` include 闭合 ✔ |
| 历史证据 | 旧清单、旧失败目录、独立 IRQ 闭合门及其余 `build/` 目录全部保留 ✔ |

## 3. 检查与覆盖（key）

八组 CHECK 全 PASS，检查数与冻结清单一致：

```
turnover_accept_eligibility 10 | front_slot_priority 7 | consecutive_turnover 6 |
lane_strobe_dcache_ownership 407 | forward_read_boundaries 12 | reset_init_cancel 7 |
non_ddr_order_gate 10 | real_soc_turnover_fence_irq 430        → 合计 889
SHORT: cycles=44 stores=6 opportunities=5 accepted=5 late=0 aw=16 w=16
RESULT: PASS write_buffer_turnover_x32 tests=889 cpu_events=430 IRQ=1 OPPORTUNITIES=82
        ACCEPTED=81 LATE=1 MLATE=0 EARLY=197 I_OVERLAP=454 OVERLAP=164 GATE=1
        FENCE_WAIT=49 IRQ_WAIT=26 STOP_WAIT=26 UART=1 RAM=2 SOC_TURNOVER=69
        fills=12 updates=203 cancelled=1
```

该 RESULT 字段与清单 `key_result_fields` **逐字段一致**（由 runner 断言通过）。control 复用已核 49 拍（`control_reused=true`），受控差值 `controlled_cycles_saved=5`，与 5 次接续机会一致。

## 4. 原始轨迹与守恒（独立 BUS 复核，3348 行）

- EV：`key.events.log` **430 行**，与冻结独立参考**逐事件严格相等**（含 IRQ 排空契约 `mepc=40000060`）。
- BUS 计数：`RESET 3 / INIT 3 / DREQ 573 / DRSP 573 / stores 232`，`AW 231 = W 231`，`cancelled 1`，`stores = W + cancelled` ✔；`IREQ 520 / IRSP 519`（末次取指留在 PASS 之后，符合约定）。
- 真实 CPU：`CPU_REQ 143 / CPU_RSP 143`（64 load + 79 store，其中 73 DDR store），与参考 143 请求**逐条地址/write/size/data/strobe 比对通过**。
- D 缓存：`cache_fills 12 / cache_store_updates 203` ✔；`CACHE 215`；`SERIAL 5`。
- 接续：`OP 82`（含 SoC 69 次机会），总接受 81、`LATE 1`——唯一未接受发生在 **cycle 3784、mode 1（SoC）、state 1、old_addr 2081→new_addr 2050**，与冻结契约「late 必须 mode=1 且 state 不在 (0,5)」一致；SoC 实际接受 68，**`SOC_TURNOVER=69` 是机会数而非 69 次成功接续**。
- 排空：`WAIT` 合计 101，判据要求 `IRQ 26 / FENCE 49 / STOP 26` ✔；`SIDE_MMIO 4 / SIDE_UART 1 / SIDE_RAM 1` 均 >0 ✔。
- 短程序 6 笔完整写入（完整地址/data/strobe，含最后一笔）：
  `(0x800,0x000000a1,0xf) (0x804,0x000000a2,0xf) (0x808,0x000000a3,0xf) (0x80c,0x000000a4,0xf) (0x810,0x00005000,0x3) (0x814,0x00006000,0xc)` ✔ 与冻结期望相等。
- 短组 5 次机会全部 `accepted=1`，其余模式一致。

## 5. 输入与 Git 前后

- 214 份输入副本全部落盘，清单三类输入（211/3/3）逐项 SHA256 一致；`simulation_timing_repair_inputs.json` 副本 SHA = 冻结清单 SHA。
- `git_before.json` 与 `git_after.json` **完全相等**；运行后当前 `git status --porcelain -uall` 与 `git_before.json` 逐行相同、HEAD 未变（本任务产物位于被忽略的 `build/` 下）。
- runner 结论字段：`inputs_unchanged=true`、`git_unchanged=true`。

## 6. 未覆盖范围与边界

- **PDS 时序/资源、位流、串口、KEY0、实板均未执行**（`timing=NOT_RUN`、`board=NOT_RUN`）。本轮的 −1.002 ns WNS、−60.104 ns TNS、149 个失败端点是否修复，只能由用户重新实现后的新 PDS 报告证明，**不能沿用旧位流或旧门认定新版本 PASS**。
- 只跑了原 key 组一次；未重跑旧对照、ISA、CoreMark、PHY，未运行旧 runner / `review_timing_repair.py` / PDS / 串口 / Git 提交推送。
- 未修改任何 RTL/TB/include/模型/参考/脚本/清单/判据/超时；未生成任何 Codex PASS 门。
- 本仿真只证明**功能与时序修复前的行为等价性**（889 检查、430 EV、守恒与接续计数全部保持），不构成任何性能收益结论。

## 7. 交回 Codex

证据齐备，可直接用 `review_timing_repair.py` 只读核原证据（该审查入口按约定不交 DeepSeek 执行）；通过后才开放本修复版本的上板入口。当前功能门与实板结论均保持关闭/未测。
