# 任务032二次时序修复 最终结果：I标签并行查询（`ds_data_bus_tag_lookup_repair_c_20261014_a`）

**状态：`TASK032_PARALLEL_INST_TAG_LOOKUP_REPAIR_KEY_AND_LOOKUP_PASS`。一次执行完成，未重试、未改任何冻结判据。**

- 四条原生 job（`vlib` / `vlog` / 原 SoC `key` / 新 `tag_lookup`）全部 exit/native 0、未超时、`cleanup=None`；**39 模块**、`Errors: 0, Warnings: 0`。
- **原 SoC key 与已复核 key 逐字段完全相同**：unit **33 拍 / 51 接续 / 1 取消**、SoC **617 周期 / 415 MEM 等待 / 18 接续**、82 EV、49 请求/49 响应、5 AW=W、40 AR=R、MMIO 6/RAM 2/UART 1、FENCE 1/等待 8、精确 load fault；runner 用整段 `checked_key` 相等断言（`key_identical_to_reviewed=true`）——**不加拍要求满足**。
- **新 I 标签并行查询组：TB 自检与独立 Python 复核双重通过**：`det=1472 rnd=512 rows=64 high_bits=21 tables=512 hits=64 misses=1920 mismatches=0`。
- 相对复用 control 的差值：unit **−31**、SoC 总周期 **−2**、MEM 等待 **−28**。
- **PDS 时序、位流、串口、KEY0、实板全部 NOT_RUN**；本仿真不证明 WNS/TNS 是否修复。

原始目录：`sim/data_bus_turnover/build/ds_data_bus_tag_lookup_repair_c_20261014_a/`

## 1. 三次尝试的收敛链（前两次现场全部保留）

| 尝试 | tag | 结束 | 原因（均在我新增的测试/执行代码内，不在 RTL/激励/参考/判据） | 结果报告 |
| --- | --- | --- | --- | --- |
| A | `ds_data_bus_tag_lookup_repair_20261014_a` | STOP | `check_lookup` 把 TB 轨迹文件当 stdout 比对；TB `scenario` 未初始化打印 `x`。**key 已实测 617/415/18，lookup 仿真已 PASS** | [任务032二次时序修复_结果_…_repair_20261014_a.md](任务032二次时序修复_结果_ds_data_bus_tag_lookup_repair_20261014_a.md) |
| B | `…_repair_b_20261014_a` | STOP | 独立检查器 `check_tag_lookup.py` 在同一行内持久化 valid 期望，未复位；**key 与 lookup 仿真均已 PASS** | [任务032二次时序修复B_结果_…_repair_b_20261014_a.md](任务032二次时序修复B_结果_ds_data_bus_tag_lookup_repair_b_20261014_a.md) |
| **C** | `…_repair_c_20261014_a` | **PASS** | — | 本文件 |

B 的检查器缺陷在消费 C 之前，已用 **B 已落盘的真实轨迹离线复算**（`RESULT: PASS tag_lookup det=1472 rnd=512 rows=64 high_bits=21 tables=512 hits=64 misses=1920 mismatches=0`）并对 `check_lookup()` 整条断言链做了只读彩排，全部通过后才封存 C。

## 2. 本轮实现文件与最终身份

| 文件 | 说明 |
| --- | --- |
| `sim/data_bus_turnover/tb_inst_tag_lookup.sv` | 新增最小组合查表定向 TB（真实桥 x32、`INST_LINE_BUFFER_ENABLE=1`、无 CPU/无程序/无 DDR 事务、桥恒 IDLE） |
| `sim/data_bus_turnover/check_tag_lookup.py` | 独立 Python 复核（逐条重算期望、种子重放、覆盖统计） |
| `sim/data_bus_turnover/run_tag_lookup_repair_c.py` | 本轮入口：核输入→新目录→vlib/vlog→key→tag_lookup→双检查→Git/结果 |
| `sim/data_bus_turnover/seal_tag_lookup_repair_c.py` | 本轮封存与只读自查 |

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_tag_lookup_repair_c.json` |
| 清单 SHA256 | **`b41b38a146d906833f23fbc46bc9babdf5a501a8cd5379910c53ce6a9182b600`** |
| 工程输入 | **176**（B 的 174，仅 `check_tag_lookup.py` 一处修正 + C 的 runner/sealer） |
| 保护证据 | **1408**（B 的 1212 ∪ B 清单 ∪ B 报告 ∪ B 运行目录除 `work` 的全部文件） |
| 相对 B 变化 | **只有 `sim/data_bus_turnover/check_tag_lookup.py`**（逐项核对，其余全部逐字未变） |
| 编译源 / 模块 | 34 源 / **39 模块**（原 38 + 新顶层 `tb_inst_tag_lookup`） |
| 桥身份 | `1df26c25…0406` → **`1170cfd21a9dc01fe526256a778309f0f657b0445ff53707ddfdc877a7280406`**（与方案一致） |
| 未变 | checker `0bdf70c4…`、TB `cb1adf6f…`、CPU `b1114fa3…`、互连 `b0afffb5…`、unit/include/模型/参考/DAT/超时/判据 |
| 绑定 | control 收据 `61c2dc2d…91ba13`；已复核 key 门 `cd6a9fb6…f7eaaf`（`checked_key` 即 `expected_key`）；前次修复复核 `4de7282d…e4e319` |
| 逐项核对 | 176 工程 + 3 厂家 + 3 工具 + 1408 保护 **全部 SHA256 相等（0 处不符）**；179 份输入副本；5 条 include 闭合、两 `*_init_param.v` 就位、两 TB 顶层均含 `GTP_GRS GRS_INST`；`reference.json` 独立重算相等 |

自查命令（native 启动前全部通过）：

```powershell
python -B sim/data_bus_turnover/seal_tag_lookup_repair_c.py --check
python -B sim/data_bus_turnover/run_tag_lookup_repair_c.py --check-inputs
python -B sim/data_bus_turnover/run_tag_lookup_repair_c.py --plan-only
```
输出：`SEAL CHECK PASS project=176 protected=1408 modules=39 changed=['sim/data_bus_turnover/check_tag_lookup.py'] tables=512 bridge=1170cfd21a9dc01f`；jobs 恰为 `["vlib","compile","key","tag_lookup"]`。

## 3. 四条原生命令的真实元数据

| job | exit | native | elapsed(s) | 上限 | timed_out | cleanup |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `vlib` | 0 | 0 | 0.0553 | 60 | false | none |
| `vlog`（34 源） | 0 | 0 | 0.3584 | 60 | false | none |
| `key`（原 SoC，TURNOVER=1） | 0 | 0 | 1.6079 | 180 | false | none |
| `tag_lookup`（新 TB） | 0 | 0 | 1.3171 | 60 | false | none |

完整 argv/cwd/exit/native/elapsed/timeout/pid 由 runner 原生直写保存在 `*.command.json`；stdout 与 `-transcript` 双份保留。

## 4. 原 SoC key：全部功能与不加拍

```
CHECK: response_owner_matrix PASS cases=24 / old_error_blocks 5 / posted_write_order 5
       / delayed_reset 2 / consecutive_requests 32 cycles=33        （68 场景）
UNIT: pairs=24 errors=5 order=5 burst=32 cycles=33 turns=51 cancelled=1
SOC: cycles=617 events=82 turns=18 mem_wait=415 fault=1 error_rsp=1 mmio=5 uart=1 ram=1 fence=1 fence_wait=8 aw=5 w=5
RESULT: PASS data_bus_turnover key_group TURNOVER=1
Errors: 0, Warnings: 0        （IPSpecCheck: 恰好 2 × 04030130；console==transcript）
```

| 指标 | 复用 control | 已复核 key | **本次（新桥）** |
| --- | ---: | ---: | ---: |
| unit cycles / turns | 64 / 0 | 33 / 51 | **33 / 51** |
| SoC cycles | 619 | 617 | **617** |
| SoC MEM 等待 | 443 | 415 | **415** |
| SoC turns | 0 | 18 | **18** |
| EV / 请求 / AW=W / AR=R / MMIO / UART / RAM / FENCE / fence_wait | 82/49/5/40/6/1/2/1/8 | 同左 | **同左** |

轨迹非空：`key.unit.log` 200 行、`key.events.log` 82 行、`key.bus.log` 216 行；EV 82 行与冻结参考逐事件（逐 PC/inst/we/rd/data/cause/tval/next）相等；DDR 每拍返回 beat 与最终字节内容、5 AW-W、排空与响应归属由 `soc_trace` 独立重算通过；精确 PC 40000094 / cause5 / tval 20000000→40000300 与年轻 `40000808` store 抑制均保持。

## 5. 新 I 标签并行查询组（覆盖与统计）

TB 构造（不跑第二个 CPU/程序，只例化真实桥 x32；`data_req_valid=inst_req_valid=0`、DDR 握手/返回静止、reset 正常释放、桥恒 IDLE）：

- 仅做**测试准备分层 deposit** `inst_line_tag`/`inst_line_valid`（无 force、不写 hit/state/ready 或任何 DUT 输出），且对每行强制真实填充不变量 `tag = (upper_tag << 6) | row`；
- 每次设置后等待组合稳定，并断言桥 `IDLE`、无 DDR 活动、请求 index 译码正确；
- 期望由 TB 自身准备数组计算；DUT 输出只被比较，不参与期望生成。

| 组 | 规模 | 内容 |
| --- | ---: | --- |
| 确定性 | **64 行 × 23 = 1472** | 每行：匹配命中 1 + 所选行 valid0 必 miss 1 + 21 个高位标签 bit 逐个翻转必 miss 21（其余 63 行同高 tag 且 valid=1，index 不同，不得干扰） |
| 随机 | **64 行 × 8 = 512** | 固定种子 **20261014**，well-formed 表（64 行高 tag + 64 位 valid），每行偶/奇交替构造命中/必 miss |
| 高位图样 | — | `0x000000` / `0x1FFFFF` 全 1 / `0x055555` 交错（按行号轮换） |
| 轨迹 | 2497 行 | `OBS` 1984（1472+512）+ `TBL` 512 + `LOOKUP-SUMMARY` 1 |

TB 自检：`RESULT: PASS tag_lookup det=1472 rnd=512 mismatches=0 hits=64 misses=1920`（2×`04030130`、`Errors: 0, Warnings: 0`、2045 ns 正常 `$finish`、console==transcript）。

独立 Python 复核（`check_tag_lookup.py`，**不读 DUT 输出构造期望**）：

```
RESULT: PASS tag_lookup det=1472 rnd=512 rows=64 high_bits=21 tables=512 hits=64 misses=1920 mismatches=0
```
逐项完成：每条记录结构校验；**低 6 位填充不变量**（`sel_tag[5:0] == index`）全 1984 条；确定性 64 行全覆盖、每行 21 个高位 bit 全覆盖、每行含所选 valid0 场景；随机组用**同一整数发生器**由种子重放 512 张表并与 TB 打印的 `TBL` 逐字段相等，再逐条重算期望；hit 与 miss 均 >0；`mismatches=0`；SUMMARY 与重算计数一致。

## 6. 输入、保护与 Git

- 清单 176 工程 / 1408 保护**逐项 SHA256 全等（0 处不符）**；运行副本 `inputs.json` SHA = 冻结清单 SHA；179 份输入文件落盘。
- `git_before.json` 与 `git_after.json` **完全相等**（runner 内断言通过）；运行后再只读复核：当前 `git status --porcelain -uall` 与 `git_before.json` **逐行相同**，`HEAD` 未变。
- 全部旧现场原样保留、未清理/未复用/未倒写 PASS：`ds_data_bus_response_turnover_20261014_a`、`…_grs_resume_…`、`…_ip_count_key_…`、`ds_data_bus_turnover_timing_repair_…`、**`ds_data_bus_tag_lookup_repair_20261014_a`（A STOP）**、**`…_repair_b_20261014_a`（B STOP）**、四个 preparation 目录及三份旧清单（`427844a5…`/`fa8bf3ae…`/`22959513…`/`5e5c0c30…`/`50408ce4…`/`9c8b684e…`）；旧缺失的 `git_after.json` 继续保持缺失。

## 7. 未覆盖范围与边界

- **新标签查询组不模拟 DDR 返回相位**，也不覆盖 x16 行为；真实 tag 填充/失效/冲突与响应仍由原 SoC key 覆盖。
- **AR 接受同拍 R 返回的来源选择相位**未被冻结用户口模型动态模拟，仅由 Codex 状态逻辑审查覆盖——不宣称覆盖全部 DDR 返回相位。
- **PDS 时序/资源、位流、串口、KEY0、实板全部 NOT_RUN**：本次只证明功能与周期等价（不加拍）；WNS −0.218 ns/TNS −0.431 ns/2 端点是否修复**必须由用户重新实现后的新 PDS 报告判定**，不能沿用旧门或旧位流。组合比较器可能增加 LUT，面积/时序效果同样只能由新实现确认。
- 未重跑 control、历史 031/030、ISA、CoreMark/PHY；未运行 `review.py`/`review_grs_resume.py`/旧 runner/旧 tag；未生成 `codex_review.json` 或任何 Codex PASS 门；未做 Git 提交推送。
- 未修改设计 RTL（本轮桥由 Codex 改，我只读取核对）/PDS/IP/成功镜像/冻结判据/超时/原 checker。

## 8. 交回 Codex

新清单/176+1408 输入副本/四条原生命令/原 UNIT-EV-BUS/新 lookup 完整轨迹与独立复核结果/Git/result 全部落盘，可只读核验。当前总功能门未开放，033 不启动；实板日志目录待 Codex 复核通过后单独准备。冻结 P300/V300、031 成功基线 `P 2.251881472 s / V 2.248137195 s` 与 BIN 保持。
