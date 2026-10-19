# 任务031续测 结果：ROM/RAM初始化参数封存补齐（`ds_write_buffer_turnover_init_resume_20261014_a`）

**状态：`STOPPED_FIRST_FAILURE`（首次失败即停止，未重试、未换 tag、未改任何文件）。**

- 第 1 条静态入口：**PASS**（exit 0）。
- 第 2 条正式运行：**vlib / vlog / control / key 四个命令全部正常跑完**（exit/native 0、无超时、`Errors: 0, Warnings: 0`、正常 finish、console==transcript），
  上一轮的 258 个 include 错误已消失（两个 `*_init_param.v` 已进入副本并被正确解析）。
- 失败发生在 runner 内的**证据复核**步骤：`check_completion_evidence.review_job` 对 **key 的独立 EV 逐事件参考比对** 断言失败——DUT 430 条事件与冻结参考 430 条**在其 IRQ 位置的 4 行（索引 23–26）上顺序不同**。
- 因该断言在独立 BUS 复核之前，**key 的独立 BUS 复核未执行**；`git_after.json` 未生成。

原始目录：`sim/write_buffer_turnover/build/ds_write_buffer_turnover_init_resume_20261014_a/`
`result.json`：`status=STOPPED_FIRST_FAILURE`、`HDL_started=true`、`completed={control:…}`、`board=NOT_RUN`、`serial_opened=false`、`PDS_started=false`、`error="AssertionError: "`。

## 1. 两条命令与真实元数据

| # | 命令 | 结果 |
| --- | --- | --- |
| 1 | `python -B …/simulation_completion_init_resume.py --check-inputs` | exit 0，`RESULT: PASS completion inputs; observation-only equivalence; reference EV430; HDL NOT_RUN; ISA=0` |
| 2 | `python -B …/simulation_completion_init_resume.py --tag ds_write_buffer_turnover_init_resume_20261014_a` | exit 1（`AssertionError`，见 §3） |

runner 原生直写保存的真实元数据（未倒填）：

| 命令 | exit_code | native_exit_after_wait | elapsed(s) | 上限(s) | timed_out |
| --- | ---: | ---: | ---: | ---: | --- |
| `vlib <run>/work` | 0 | 0 | 0.0972 | 60 | false |
| `vlog -sv +incdir… -work <run>/work <3 厂家源><36 模块源>` | 0 | 0 | 0.4083 | 60 | false |
| `vsim -batch tb_write_buffer_turnover_completion -gPOSTED=1 -gTURNOVER=0 …`（control） | 0 | 0 | 2.2802 | 180 | false |
| `vsim -batch … -gTURNOVER=1 …`（key） | 0 | 0 | 2.6698 | 180 | false |

编译：`-- Compiling module` 共 **36** 个，与清单 `module_count=36` 一致，`Errors: 0, Warnings: 0`。运行副本 `inputs/project/ipcore/inst_rom/rtl/inst_rom_init_param.v` 与 `inputs/project/ipcore/data_ram/rtl/data_ram_init_param.v` **已存在**，上一轮的 `` `include `` 缺失问题已闭合。

> 更正：上一份报告表中 `vlib` elapsed 误记为 0.192 s，真实值 `vlib.command.json.seconds = 0.2483402`（本次运行 0.0972 s）。旧报告该字段不修改，只在此更正。

## 2. 已通过的部分（原始证据）

| 项 | 结果 |
| --- | --- |
| `control` job | `RESULT: PASS write_buffer_turnover_control tests=6 cycles=49 opportunities=5 late=5 AW=6 W=6`；8 组 CHECK 为空、无 EV 文件，符合 control 约定；console==transcript；`Errors: 0, Warnings: 0`；4 条 `IPSpecCheck: 04030130` 原文保持 |
| `control` 独立 BUS 复核 | **通过**（runner 已写入 `result.completed.control.bus`）：RESET1 / INIT1 / DREQ6 / stores6 / DRSP6 / AW6 / W6 / OP5，5 次机会全部 `mode=0 accepted=0`，短程序 6 笔完整写入 `(0x800,0xa1,15)(0x804,0xa2,15)(0x808,0xa3,15)(0x80c,0xa4,15)(0x810,0x5000,3)(0x814,0x6000,12)` |
| `key` job 内嵌判据 | 八组 CHECK 全 PASS：`turnover_accept_eligibility 10 / front_slot_priority 7 / consecutive_turnover 6 / lane_strobe_dcache_ownership 407 / forward_read_boundaries 12 / reset_init_cancel 7 / non_ddr_order_gate 10 / real_soc_turnover_fence_irq 430`（889 项） |
| `key` RESULT 字段 | `RESULT: PASS write_buffer_turnover_x32 tests=889 cpu_events=430 IRQ=1 OPPORTUNITIES=82 ACCEPTED=81 LATE=1 MLATE=0 EARLY=197 I_OVERLAP=454 OVERLAP=164 GATE=1 FENCE_WAIT=49 IRQ_WAIT=26 STOP_WAIT=26 UART=1 RAM=2 SOC_TURNOVER=69 fills=12 updates=203 cancelled=1`，**与冻结清单 `key_result_fields` 逐字段完全一致**（只读复核 = True） |
| `key` SHORT / 日志 | `SHORT: cycles=44 stores=6 opportunities=5 accepted=5 late=0 aw=16 w=16`；console==transcript；`Errors: 0, Warnings: 0`；4 条 `04030130` |
| 身份 | 副本 `myriscv/mycpu_sync.v` = `b1114fa3…`、`myriscv/dual_sram_to_pango_ddr_bridge.v` = `2dfa96ca…`，与工作树一致；`simulation_completion_inputs.json` 副本 SHA = 冻结清单 SHA；`git status --porcelain -uall` 与 `git_before.json` 逐行相同，HEAD 未变 |

## 3. 失败点：key 独立 EV 参考比对（只读差异分析）

断言：`check_completion_evidence.py:182`

```python
assert events == [event_line(event) for event in completion_reference.json['events']]
```

只读比对 `key.events.log` 与冻结参考渲染结果：

- **两边都是 430 条**，索引 0–22 完全相同，**不一致仅 4 行：索引 23、24、25、26**，索引 27 起再次完全相同。

| idx | DUT `key.events.log` | 冻结参考 |
| ---: | --- | --- |
| 22 | `EV 22 N 40000058 0050a023 0 0 00000000 00000000 00000000 4000005c` | 同左（循环内 DDR store，即 IRQ 触发笔） |
| 23 | `EV 23 N 4000005c 00520233 f 4 00000001 … 40000060`（`add x4,x4,x5` 先退休） | `EV 23 I 4000005c … 0000000b … 40000100`（**立即进 IRQ，mepc=4000005c**） |
| 24 | `EV 24 I 40000060 … 0000000b … 40000100`（**DUT 的 IRQ，mepc=40000060**） | `EV 24 N 40000100 001a0a13 …` |
| 25 | `EV 25 N 40000100 001a0a13 …` | `EV 25 M 40000104 30200073 … 4000005c` |
| 26 | `EV 26 M 40000104 30200073 … 40000060` | `EV 26 N 4000005c 00520233 … 40000060` |
| 27+ | 与参考逐行相同 | 同左 |

即：**事件集合、条数（430）、后续顺序都相同，只是 IRQ 的插入位置不同**——
DUT 在触发 store 之后仍让已流入的 `add x4,x4,x5`（0x4000005c）退休，然后才进入 IRQ（`mepc=0x40000060`）；
冻结参考约定为「触发 store 退休后立即进 IRQ」（`mepc=0x4000005c`），把那条 `add` 排到 MRET 之后。
二者各自自洽；差异来源于 **TB 在 store 接受边沿才拉起 `soc_irq`** 时 IRQ 被采样的时机，与参考模型注入 IRQ 的约定不同。
DUT 的 `IRQ_WAIT=26`、`IRQ=1`、`cpu_events=430` 与冻结 `key_result_fields` 完全一致。

**本次未由我判定这是 RTL 功能 FAIL 还是参考约定需修正**；按约定只交付事实与差异位置，由 Codex 复核裁定。

## 4. 未执行 / 未覆盖范围

- key 的**独立 BUS 复核未执行**（runner 在 EV 断言处停下）；`key.bus.log`（122829 B）已原始保存但未经 `review_bus` 校验。
- `git_after.json` 未生成（失败于其写入之前）；`result.json` 的 `inputs_unchanged` / `git_unchanged` 等收尾字段未写入。
- 未执行 PDS、未开串口、未做 KEY0/实板；未执行 `review_completion_init_resume.py` 等 Codex 审查入口；未运行旧 `run.py` / 旧 `simulation_runner.py` / `prepare*.py`。
- 未修改任何 RTL/TB/include/模型/参考/清单/判据/超时；未创建任何 Codex PASS 门。

## 5. 证据与保护

运行目录内已保存：`vlib.command.json`+`vlib.log`、`compile.command.json`+`compile.log`、`control.command.json`+`control.log`+`control.transcript`+`control.events.log`+`control.bus.log`、`key.command.json`+`key.log`+`key.transcript`+`key.events.log`+`key.bus.log`、`git_before.json`、`inputs/`（207 工程 + 3 厂家 + 3 工具副本）、`inputs.json`、`simulation_completion_inputs.json`、`result.json`。

- 旧失败目录 `build/ds_write_buffer_turnover_20261014_a/` 与旧清单 `simulation_completion_inputs.json`（SHA `513b578c…13c96`）**原样保留**，未清理、未复用、未倒写 PASS。
- 新清单 `simulation_completion_init_resume_inputs.json` SHA `a891161f231a0ac81784432d2054d0941f655a2de240e57f2717ade3f3309763` ✔；原 Codex inputs SHA `1b19dad3…403b692` ✔；执行前新 tag 不存在、`pds_shell` 计数 0 ✔。
- 报告名与目录名均按本续测入口使用；旧报告 `任务031_结果_ds_write_buffer_turnover_20261014_a.md` 保持原内容。
