# 任务032协议B覆盖补齐 结果：`ds_data_bus_inst_lookup_protocol_completion_20261014_a`

**状态：`TASK032_PROTOCOL_COMPLETION_REUSED_KEY_A_PASS`。一次 B-only 执行完成，未重试、未改判据。**

三项缺口已按方案落实并被独立参考**实测**（非声明）确认；第 4 项（计划身份/写数据）由参考逐字段从计划推导核验。

## 1. 原生命令与结果

| job | exit | native | elapsed(s) | 上限 | timed_out |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 0 | 0 | 0.2886 | 60 | false |
| vlog | 0 | 0 | 0.5812 | 60 | false |
| completion B-only vsim | 0 | 0 | 1.8260 | 180 | false |

`jobs` 固定 `["vlib","compile","inst_lookup_protocol_completion"]`；**未派发** key/A/control/旧版/history/ISA/CoreMark/PHY。39 模块、`Errors: 0, Warnings: 0`、恰好 2×`04030130`、正常 `$finish`、console 与 transcript 归一全文相同。

TB 控制台：
```
EDGES counter=187 logged=186 first_logged=2
RESULT: PASS inst_lookup_protocol_completion scenarios=17 tokens=44 accepts=44 responses=41
       cancels=3 resets=3 ar=19 r=18 aw=6 w=6 ar_r_same=2 dual_present=2 edges=187 mismatches=0
```

## 2. 独立参考实测（逐项对应四项缺口）

| 缺口 | 要求 | **实测** |
| --- | --- | --- |
| ① AR/R 同拍 | 同一 posedge 上 `ar_v&&ar_r&&r_v&&resetn`，计数 ≥2，两个指定 token | **`ar_r_same=2`**，边沿明细 `[[16, token 2, scen 2], [121, token 31, scen 11]]` = 冷 I miss 与 posted 写排空后的 I miss，完全命中封存声明 `ar_r_same_tokens=[2,31]` |
| ② I/D 同时请求 | 存在 `i_v&&d_v&&resetn` 边沿且其中 `d_v&&d_r&&!i_r`，计数 ≥2 | **`dual_present=2`**（边沿 68/86，场景 7/9）、**`dual_d_wins=2`**（D 胜出且只接受一次，未接受的 I 保持到后续接受） |
| ③ 内存只在 W 完成提交 | AW 只锁存；`f_w = wready && (本沿 AW 接受 \|\| owner AW 已接受)` 才提交；AW/W 期间 addr/data/strobe 稳定；非零 lane 部分字节写 | 参考按**计划字段**推导 256-bit 数据与 32-bit 使能，先逐字段比对实际 AW/W 再更新内存；新增 `wstrb=0xa` 的 lane1 部分写（token 36）经整 32 字节 R 拍逐字节核验未使能字节保持；`aw=6, w=6` |
| ④ 计划身份与覆盖从原始记录重算 | 真正读取 `plan.log` 并逐字段核；SUM 计数从真实记录重算；edge counter 与日志行数分开 | 参考强制 `plan_path`（缺失即失败）并 `compare_plan` 逐字段比对成功；`plan_sha256=ac8536f9…` 与封存一致；`edges=187`、`log_lines=186`、`first_edge=2` 分开报告 |

守恒与覆盖（全部由参考独立重算）：`accepts 44 = responses 41 + cancels 3`；`resets=3` 与**初始上电 reset 单列** `power_on_resets=1`（`reset_edges=12` 为复位电平边沿数）；`lanes=8`、`ready_blocked=6`（AR 背压）、`busy_blocked=14`（写排空阻塞 AR）、`competition=4`、`idle_silent=17`、`hit_after_miss/miss_after_hit/hit_after_hit=8/8/9`、`refetch_changed=1`、`mismatches=0`。

## 3. 诚实列出的未触发项（不声称已验证）

- **`dual_with_i_rsp=0`**：在已封存计划下，"旧 I hit 响应沿同时 I_VALID 与 D_VALID"不可构成（该 I token 期望 hit，同沿 D store 获胜会使其失效变 miss；下一个 I token 属场景 13、accept 边 scen 必须为 13）。参考只统计不断言；场景 12 仍以"旧 I hit 响应消费同沿 + 同行失效 store"覆盖竞争，旧 I 数据先按失效前缓存核验。
- **`r_w_same_edge=0`**：本次无真实 W 与 R 同沿，参考打印 NOTE，**不声称已动态验证该相位**；代码顺序已保证"R 取该沿前内存、W 在该沿后提交"。
- token 42 的 AR 无 R 属计划内（复位取消）。
- 部分字节写地址采用检查器封存口径 `0x40000444`（非任务书示例的 `0x40000804`），同等属性（非零 lane、部分使能、未使能字节保持）已核。
- 未动态覆盖：x16 与关闭 I buffer、D 读/写重叠许可、store-forwarding、真实 DDR/PHY 返回相位。

## 4. 身份、输入与保护

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_inst_lookup_protocol_completion.json` |
| 清单 SHA256 | **`d9d215eaa72e84aeeda76fee4c777f2d6f2a0d0a58ed279b666a962434ca1cb7`** |
| 运行副本 | `inputs.json` SHA = 清单 SHA；工程输入 **196** / 保护证据 **2651**，逐项 SHA256 全等（0 处不符） |
| 相对 E | **只有 `compile_sources` 里旧 B-only 顶层换成 completion 顶层**、`expected_modules` 同名替换（仍 39）、新增 4 个实现文件；既有 192 项逐字未改（E 的 TB `e816f310…`/参考 `8505908f…`/runner 全部保留） |
| 新实现 | TB `0283b863…f92f`、参考 `b91683c6…079b`、runner `e0053e13…834a`、sealer `112c90b2…2df0`（sealer 自查脚本修掉"对 .sv 做 AST"一处后重封存） |
| 桥 / 工具 / include | 桥 `f14b16cb…` 未变；3 厂家 + 3 工具与 E 相同；5 条 include 闭合、两 `*_init_param.v` 与 GRS 就位 |
| 绑定 | 部分收据 `2a482844…` 的 `checked_key`（617/415/18）与 `checked_A`（1472/512/256/256/0）；E 清单 `e7ca966c…`；审查收据 `5bdabc0b…` 及其 210 项 `prior_files`；`coverage_contract` = `plan_summary()` + `ar_r_same_min=2`/`dual_present_min=2`/`same_edge_required`/`dual_present_required`/`w_commit_rule` |
| 交接迁移 | 活 `doc/CODEX_HANDOFF.md` 不冻结，历史身份绑定保存副本 |
| Git | `git_before == git_after`（字节相同）✔，`inputs_unchanged=true`、`git_unchanged=true` |

## 5. 边界

- **PDS 时序/位流/串口/KEY0/实板全部 NOT_RUN**；RTL/桥/IP/BIN 未改；时序按用户反馈"通过"、未经独立复核；**07 不启动**。
- 未运行旧 HDL（vlib/vlog/vsim 只在本次正式运行中执行一次）；未生成或改写任何 Codex 验收门。
- 冻结 P300/V300、031 基线 `P 2.251881472 s / V 2.248137195 s` 与 BIN 保持。

## 6. 交回 Codex

原始证据齐备：新清单 + 196/2651 逐项副本核验、三命令原生元数据、`edge.log`(186 行)/`plan.log`(44 token)、独立参考完整结果（含 `ar_r_same_edges`/`dual_present_edges`/逐 token 终态）、Git 前后、`result.json`（`status=TASK032_PROTOCOL_COMPLETION_REUSED_KEY_A_PASS`）。
