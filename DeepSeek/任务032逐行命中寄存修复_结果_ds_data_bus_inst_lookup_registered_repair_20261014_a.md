# 任务032逐行命中寄存修复 结果：`ds_data_bus_inst_lookup_registered_repair_20261014_a`

**状态：`STOPPED_FIRST_FAILURE`。首败即停、现场完整保留、未重试、未改任何既有文件。**

**关键事实：本次任务的时序修复核心（A 组：接受边沿寄存逐行命中）与不加拍要求都已通过；失败在 B 组（实际握手/DRM/填充协议组）TB 自身的守恒门。**

| 项 | 结果 |
| --- | --- |
| vlib / vlog | exit/native 0；**39 模块**、`Errors: 0, Warnings: 0`；编译列表已按方案把旧组合 lookup TB 换成新顶层 `tb_inst_lookup_registered` |
| **原 SoC key** | **PASS**，与已核 key **逐字段完全相同**：unit **33 拍/51 接续/1 取消**、SoC **617 周期 / 415 MEM 等待 / 18 接续**、82 EV、`key_identical_to_reviewed=true`（`deltas` 31/2/28） |
| **A 组（标签采样）** | **全项通过**：`ASUM det=1472 rnd=512 hits=320 misses=1664 rows=64 cont=320 mismatches=0` |
| **B 组（真实协议）** | **FAIL**：`BSUM accepts=70 responses=60 cancels=8 events=188 outstanding=2` → 70 ≠ 60+8，且 outstanding=2；TB 在 `tb_inst_lookup_registered.sv:724` 主动 `$fatal(1,"RESULT: FAIL inst_lookup group B conservation")` |
| 新组 vsim | exit/native 0（未超时），但 stdout 含 `RESULT: FAIL`，故 runner 在 `command()` 的失败文本断言处停止 |
| 独立 Python 检查器 | **未运行**（TB 先 fatal，未写出 `RESULT: PASS` 行）；本次不宣称新协议组经独立核验 |
| Git | `git_before.json` 已保存；`git_after.json` **未生成**，按约定不补造 |

原始目录：`sim/data_bus_turnover/build/ds_data_bus_inst_lookup_registered_repair_20261014_a/`

## 1. A 组通过的完整统计（本版修复的核心）

```
ASUM det=1472 rnd=512 hits=320 misses=1664 rows=64 cont=320 mismatches=0
```
- 轨迹记录：`A` 1984 条 = 1472 确定性 + 512 随机；`ATBL` 512 张（随机准备表）；`ACONT` 320 条接续证明。
- 确定性 1472 = 64 行 ×（匹配 hit 1 + 所选行 valid0 miss 1 + 恢复 valid 后 21 个高 tag 位逐 bit 翻转 miss 21）；随机 512 = 64 行 × 8、种子 20261014、**256 hit / 256 miss**；合计 hit 320 / miss 1664。
- 每条观察都含一次**真实 I 请求接受**，并在观察拍把 live 地址换成已缓存诱饵地址后取样：**每个观察都恰好出现"响应"或"AR"之一**（TB 对"两者都无"或"两者同时"都会 fatal，本次未触发），且 `outcome_cycle == accept_edge`（接受沿后第一拍）→ **接受边沿寄存的逐行命中无额外查询空拍**得到动态证明。
- 320 次 `ACONT`：接受后下一沿确实接受了诱饵事务并拿到响应（快照归属证明）。

## 2. 第一失败点与现场（B 组）

TB 末尾的守恒门（`tb_inst_lookup_registered.sv:721-724`）：

```systemverilog
$fdisplay(b_fd, "BSUM accepts=%0d responses=%0d cancels=%0d events=%0d outstanding=%0d", ...);
if (b_out != 0 || b_acc != b_rsp + b_can)
    $fatal(1, "RESULT: FAIL inst_lookup group B conservation");
```

实测 `BSUM accepts=70 responses=60 cancels=8 events=188 outstanding=2`，即 **70 ≠ 60+8**、且结束时仍有 **2 笔被接受请求既无响应也无取消**。
`registered.log`：`# ** Fatal: RESULT: FAIL inst_lookup group B conservation`，`# Errors: 1, Warnings: 0`，Time 82330 ns（B 组已跑到末尾，未提前中断）。

**逐场景（由 `bus.log` 原始记录重算；kind 为字符串）**：

| 场景 | 激励条数 | 接受 | 响应 | 取消 | 备注 |
| ---: | ---: | ---: | ---: | ---: | --- |
| 1-2 | 4/2 | 4/2 | 4/2 | 0 | 平衡 |
| 3 | 3 | 6 | 6 | 0 | 平衡，但**接受数 > 激励数** |
| 4 | 3 | 6 | 6 | 0 | 同上 |
| 5 | 3 | 4 | 4 | 0 | 平衡 |
| 6 | 4 | 4 | 4 | 0 | 平衡 |
| **7** | 4 | 4 | 3 | 0 | **少 1 个响应** |
| 8-12 | 4/6/4/8/0 | 3/5/2/8/0 | 3/5/2/8/0 | 0 | 平衡 |
| **13** | 1 | **8** | 4 | 1 | 单条激励被接受 8 次 |
| **14** | 1 | **6** | 3 | 1 | 同上 |
| **15** | 2 | 4 | 1 | 1 | 同上 |
| **16** | 6 | 4 | **5** | 0 | **响应多于接受** |

（事件种类计数：`I_ACC 55 / D_ACC 15 / I_RSP 45 / D_RSP 15 / AR 17 / AW 11 / W 11 / R 16 / RESET 3`；TB 自己的 `cancels=8` 与其打印的 3 条 `RESET` 也不一致，说明取消计数口径同样待核。）

**可复现的形态**：场景 13/14/15 中 TB 在复位边界后**持续保持 `inst_req_valid`**，而桥在被复位清空后每个空闲沿都合法接受一次，于是同一笔激励被反复接受（13：8 次），远超 TB 预设的"1 次接受"；场景 16 中 D 侧 posted 写在同一地址连续多拍被重复接受并重复发 AW/W，同时 `D_RSP` 比 `D_ACC` 多 1。这与 TB 作者的设计预期（**16 场景 / 29 接受 / 26 响应 / 3 取消**）差距很大，属**B 组激励时序与记账口径**与 DUT 实际行为不一致。

## 3. 判定与边界（不越权下结论）

- 失败发生在 **TB 自己的守恒断言**，而非桥输出错误、不是判据降低、也不是我的封存/入口问题；`compile` 39 模块零错零警告、A 组 1472+512 全过、key 完全一致，说明封存、include 闭包、GRS 实例、编译参数与桥本身在该 job 内均正常。
- **我不宣称 B 组失败证明 RTL 有缺陷，也不宣称 RTL 无缺陷**：现有证据只能说明"B 组 TB 的激励/记账模型与 DUT 实际协议行为不一致"，其根因（是 TB 的 holding-valid 约定/复位后重试写法，还是桥在复位后或重复接受下的真实行为）需要**带 HDL 迭代的定位**才能区分。方案明确禁止在正式流程中先试跑 HDL 或失败后自行重跑，因此交回 Codex 裁定。
- 未执行/未取得：独立 Python 检查器（`check_inst_lookup_registered.py`）**未运行**；`BSUM` 与 `bus.log` 的取消口径互校未完成；`git_after` 未采集。
- 未重跑 control、历史 031/030、ISA、CoreMark、PHY；未运行旧 runner/旧 tag；未修改 RTL/TB/清单/旧结果；未生成或改写任何 Codex 门。
- **PDS 时序/位流/串口/KEY0/实板全部 NOT_RUN**：本次不产生时序结论；方案记录的"用户反馈时序通过"仍只是用户反馈，未经独立复核。

## 4. 身份与保护（执行前后均已核对）

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_inst_lookup_registered_repair.json`，SHA **`b2f9a26eea2992c92b02da144c13a1f9361dc9e11f5ffb321abb9807173c26af`** |
| 运行副本 | `inputs.json` SHA = 清单 SHA（一致） |
| 桥 | `1170cfd2…` → **`f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0`**（与方案一致） |
| 工程输入 / 保护证据 | **180 / 1621**（逐项 SHA256 全等，0 处不符） |
| 相对 C 清单 | **只有桥**一处变化；新增 4 个实现文件；编译列表仅把旧组合 lookup TB 换成新顶层（仍 39 模块）；include 闭包 5 条不变 |
| 新实现（均已随副本封存） | `tb_inst_lookup_registered.sv`（`688c91f5…`）、`check_inst_lookup_registered.py`（`477e7649…`）、`run_inst_lookup_registered_repair.py`、`seal_inst_lookup_registered_repair.py` |
| 绑定 | control 收据 `61c2dc2d…`；已核 key 门 `cd6a9fb6…`；**C 门 `8ffa90fc…` 已显式标注只对应 1170 旧桥、不得作为本版功能门**；本次静态准备收据 `823be9af…`；031 基线目录与 `doc/CODEX_HANDOFF.md`（冻结镜像身份） |

## 5. 交回 Codex（建议）

1. 复核本目录原始证据（`key.log`/`key.*.log`、`lookup.log` + `ASUM`、`bus.log` + `BSUM`、三方 command.json、`result.json`）。
2. 就 B 组 TB 交回一份修订要求，我据此实现新清单 + 新目录后**再执行一次**（本目录按约定保留、不复用、不倒写）。需要明确的关键点：
   - 复位/取消后 `inst_req_valid` 的持有时机与"每笔激励只接受一次"的约定；
   - 同一周期内 `I_ACC`/`D_ACC` 与 `I_RSP`/`D_RSP` 的配对记账规则（场景 16 出现响应多于接受）；
   - 取消计数口径（`cancels=8` vs 打印 3 条 `RESET`）；
   - 若允许，给出"失败后可在临时目录做 HDL 定位"的授权边界，否则下一次仍将是首次运行即判定。
3. 当前总功能门未开放，033 不启动；实板日志目录与 COM9 入口待功能复核通过后另行准备。
