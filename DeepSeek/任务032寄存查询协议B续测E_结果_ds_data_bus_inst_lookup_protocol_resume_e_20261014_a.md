# 任务032寄存查询协议B续测 最终结果：`ds_data_bus_inst_lookup_protocol_resume_e_20261014_a`

**状态：`TASK032_REGISTERED_LOOKUP_REUSED_KEY_A_PROTOCOL_B_PASS`。一次 B-only 执行完成，未重试、未改判据。**

- 三条 job（`vlib` / `vlog` / B-only `vsim`）全部 exit/native 0、未超时（0.0661 / 0.4067 / 1.3605 s，上限 60/60/180）、`cleanup=None`；**39 模块、`Errors: 0, Warnings: 0`**、正常 `$finish`、console 与 transcript 归一全文相同、恰好 2×`04030130`、无 FAIL/Error/Fatal/RPC。
- **本组不看 key/A 的新测量**（按方案复用已核证据）：key 33unit/617SoC/415MEM/18接续与 A 组 1472/512/256/256 来自部分复核收据 `2a482844…`，本次不重跑。
- **B 协议组为本次新实际测量，TB 自检与独立 Python 参考双重通过**，且与执行前封存的刺激计划逐项一致。

## 1. 实际命令与元数据

| job | argv 关键部分 | exit | native | elapsed(s) | 上限 | timed_out |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| vlib | `vlib <run>/work` | 0 | 0 | 0.0661 | 60 | false |
| vlog | `vlog -sv +incdir… -work <run>/work <3 厂家源><35 模块源>` | 0 | 0 | 0.4067 | 60 | false |
| protocol | `vsim -batch -lib <run>/work tb_inst_lookup_protocol_resume +EDGE_LOG=… +PLAN_LOG=… -logfile … -do "run -all; quit -f"` | 0 | 0 | 1.3605 | 180 | false |

完整 argv/cwd/pid/exit/native/elapsed/timeout/cleanup 保存在对应 `*.command.json`；stdout 与 transcript 双份保留。

## 2. 严格执行的 B-only 范围

`jobs` 固定为 `["vlib","compile","inst_lookup_protocol_resume"]`（清单内绑定并在 `require_inputs` 断言）：**未派发 key / A / control / 旧版 / history / ISA / PHY**。

## 3. TB 自检（协议仿真）

```
RESULT: PASS inst_lookup_protocol_resume scenarios=17 tokens=43 accepts=43 responses=40
       cancels=3 resets=3 ar=19 r=18 aw=5 w=5 edges=189 mismatches=0
Errors: 0, Warnings: 0        （IPSpecCheck: 恰好 2 × 04030130）
```

## 4. 独立参考（对本次运行自身边沿轨迹的 edge 级复核）

```
scenarios=17 tokens=43 accepts=43 responses=40 cancels=3 resets=3
ar=19 r=18 aw=5 w=5 edges=188 mismatches=0
lanes=8 ready_blocked=6 busy_blocked=14 competition=3 idle_silent=17
hit_after_miss=8 miss_after_hit=8 hit_after_hit=9 refetch_changed=1
```

覆盖逐项落地（均为**独立重算**，非 DUT 输出回填）：

| 方案要求 | 实测 |
| --- | --- |
| 接受 = 响应 + 取消、outstanding 0、每 token 终态唯一 | 43 = 40 + 3；3 笔计划取消即 `[37,39,41]`；`mismatches=0` |
| 8 个 lane 由真实 fill 逐 word 命中 | `lanes=8` |
| AR 背压 ≥3 周期 | `ready_blocked=6` |
| posted 写排空阻塞 AR | `busy_blocked=14` |
| I/D 同沿竞争（data 优先、仅一方接受、无重复响应） | `competition=3` |
| idle valid0 无伪响应/AR | `idle_silent=17` |
| hit→hit / hit→miss / miss→hit 序列 | 9 / 8 / 8 |
| 同行写后重新取指得到新值 | `refetch_changed=1` |
| 三相位复位取消 + 复位后新 token 正常完成 | `resets=3`、`cancels=3`（每场景各 1 笔） |
| 同沿 W/R 可见性 | 本激励内无"同沿写提交 + R 握手"，TB 已按方案"先取边沿前内存响应、再提交写字节"实现（行为中性） |

轨迹：`edge.log`（188 边沿快照，33 字段/边沿）、`plan.log`（43 条执行前 token 表）。

## 5. 身份、输入与保护

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_e.json` |
| 清单 SHA256 | **`e7ca966c62d4ba59f4c5f8ae6fc24a4704c10b649c6fee5480cb018bbb746f74`** |
| 运行副本 | `inputs.json` SHA = 清单 SHA（一致） |
| 工程输入 / 保护证据 | **192 / 2439**（逐项 SHA256 全等，0 处不符） |
| 相对 `_d` | **只有 `run_inst_lookup_protocol_resume_b.py`** 一处（删除对不存在键的多余断言）；TB `e816f310…`、独立参考 `8505908f…`、桥 `f14b16cb…`、编制源/模块/include/超时/判据**逐字未变** |
| 相对原始设计 | 相对 C 清单仅桥 + 本轮实现文件；相对 `_b` 仅 TB、参考、runner 三类修复 |
| 编译顶层 | 新 B-only 顶层 `tb_inst_lookup_protocol_resume.sv`；**39 模块**；5 条 include 闭合、两 `*_init_param.v` 就位、顶层含 `GTP_GRS GRS_INST` |
| 绑定 | 部分复核收据 `2a482844…`（`checked_key` 617/415/18、`checked_A` 1472/512/256/256/0）及其 203 项 `prior_files_sha256`；control 收据 `61c2dc2d…`；已核 key 门 `cd6a9fb6…`；C 门 `8ffa90fc…`（仅对应旧桥，不作本版门）；**交接文档身份迁移**：活 `doc/CODEX_HANDOFF.md` 不被冻结，历史身份绑定保存副本 `55be65f6…` |
| 刺激计划 | 封存于清单：`{scenarios:17, tokens:43, accepts:43, responses:40, cancels:3, resets:3, planned_cancel_ids:[37,39,41]}`（执行前固定，非实测回填） |
| Git | `git_before == git_after` ✔（字节相同），`inputs_unchanged=true`、`git_unchanged=true` |

## 6. 收敛过程（全部经离线重放门后才有正式运行）

前序尝试的现场与清单原样保留、未倒写：reserved-word STOP（`_a`）、参考地址换算 STOP（`_b`）、`_c`（封存后未执行）、`_d`（runner 键名 STOP，其实质已通过——见[D 结果](任务032寄存查询协议B续测D_结果_ds_data_bus_inst_lookup_protocol_resume_d_20261014_a.md)）。运行前共修 4 处并逐次以"重放已落盘轨迹"推进：参考 `line_base` 地址空间 → TB 同沿 W/R 可见性 → 参考 W 完成判定（补"AW 已接受"）→ 参考复位清 valid，直至 **188 边沿全绿**；`_d`/`_e` 两轮均为修 runner 自身断言。

## 7. 未覆盖范围与边界

- **PDS 时序/资源、位流、串口、KEY0、实板全部 NOT_RUN**：本次只是仿真功能验证；**时序按用户反馈"通过"，未经独立复核 WNS/TNS**，不产生时序结论。
- 本组 DDR 模型不是物理 PHY；未动态覆盖 **x16 模式、关闭 I buffer、D 读/写重叠许可、store-forwarding、真实 DDR 返回相位**（方案已声明）。
- 未重跑 key/A/control/旧桥/历史 031/030/ISA/CoreMark/PHY；未修改 RTL/桥/IP/BIN/冻结判据；未做 Git 提交推送。
- 未生成或改写任何 Codex 验收门；整体功能门与上板入口须由 Codex 复核原始证据后给出。

## 8. 交回 Codex

原始证据齐备：新清单 + 192/2439 逐项副本核验、三条原生命令元数据、`edge.log`/`plan.log`、TB 自检与独立参考结果、Git 前后、`result.json`（`status=TASK032_REGISTERED_LOOKUP_REUSED_KEY_A_PROTOCOL_B_PASS`）。033 不启动；冻结 P300/V300、031 基线 `P 2.251881472 s / V 2.248137195 s` 与 BIN 保持。
