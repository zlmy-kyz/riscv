# 任务032寄存查询协议B续测B 结果：`ds_data_bus_inst_lookup_protocol_resume_b_20261014_a`

**状态：`STOPPED_FIRST_FAILURE`。首败即停、现场完整保留、未重试、未改判据。**

本次是保留字修复后的 B-only 重跑（首次尝试见[任务032寄存查询协议B续测_结果_ds_data_bus_inst_lookup_protocol_resume_20261014_a.md](任务032寄存查询协议B续测_结果_ds_data_bus_inst_lookup_protocol_resume_20261014_a.md)，因 vlog 保留字 `edge` 失败）。

**重大进展：本轮三条 job 全部原生通过，B-only 协议仿真首次真正跑完并由 TB 报 PASS；失败只发生在随后运行的独立 Python 参考对 DUT 地址约定的换算上。**

| job | exit | native | elapsed | 上限 | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 0 | 0 | 0.0633 s | 60 s | 正常 |
| vlog | 0 | 0 | 0.3810 s | 60 s | **39 模块，`Errors: 0, Warnings: 0`**（保留字修复生效） |
| B-only vsim | **0** | **0** | 1.5508 s | 180 s | 未超时；console/transcript 归一相同、正常 `$finish`、2×`04030130`、无 FAIL/Fatal |
| 独立 Python 参考 | **失败** | — | — | — | `AssertionError: edge 6 AR address 00000000, owner 40000000` |

## 1. B-only 协议仿真的实测结果（TB 自检通过）

```
RESULT: PASS inst_lookup_protocol_resume scenarios=17 tokens=43 accepts=43 responses=40
       cancels=3 resets=3 ar=19 r=18 aw=5 w=5 edges=189 mismatches=0
Errors: 0, Warnings: 0     （IPSpecCheck: 恰好 2 × 04030130）
```
- **与执行前封存的刺激计划完全一致**：`plan_summary()` = `{scenarios:17, tokens:43, accepts:43, responses:40, cancels:3, resets:3, planned_cancel_ids:[37,39,41]}` → `accepts = responses + cancels`（43 = 40 + 3）、outstanding 0、**3 笔计划取消**全部命中。
- 轨迹：`edge.log` 339 行、`plan.log` 43 条 `PLAN` —— 即方案要求的逐边沿快照与执行前 token 表均已落盘。
- 四项修订的落地结构均已生效：每 token 独立 id/owner、仅 negedge 驱动、接受后下一下降沿撤销、三处复位相位、唯一边沿监视快照、场景间完全排空。

## 2. 第一失败点：独立参考的地址换算（非 DUT/TB 缺陷）

`check_inst_lookup_protocol_resume.py`：

```python
def line_base(addr):
    return (addr >> 5) << 3          # 行 103-104
...
assert e['ar_addr'] == line_base(tok['addr']), ...   # 行 298（另有 277/318/323 同样用法）
```

**`line_base` 被传入了裸 CPU 地址**（token 的 `addr` = `0x40000000`），于是算出 `(0x40000000>>5)<<3 = 0x10000000`；而桥实际驱动的 `axi_araddr = 0x00000000`。

桥的行为与工程既有约定**完全一致**：DDR 用户地址 = `(CPU地址 − 0x40000000) >> 2`（16 位字单位），行基址再按 32 字节对齐。三处独立佐证：
1. 本轮 edge 6 的 owner 是 `0x40000000` → 用户行基址 = `0`，与 DUT 一致；
2. 既有已通过的 032 各轮里，CPU `0x40000500` 对应 `AW 0x140`（= `0x500>>2`）；冻结参考 `check_evidence.soc_trace` 用的正是 `local >> 5 << 3`（`local = addr − 0x40000000`）；
3. 同一检查器的 `line_index`/`lane_of` 用掩码取低位（`(addr>>5)&63`、`(addr>>2)&7`），对高位不敏感因此不受影响——**只有不做掩码的 `line_base` 受影响**。

因此这是**我新增的独立参考里的地址空间换算错误**（4 处调用同一函数：AR 地址、AW 地址、W 归属、以及缓存初值比对），不是 DUT、TB、激励、判据或封存问题。检查器在第 6 个边沿即停止，后续 180+ 边沿的场景未被该参考核验。

## 3. 身份、保护与 Git

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_b.json`，SHA **`f2294a96e58bf422548b9753f4a359aa9b2e5f8d2b84e6e00c1b2045299935f3`** |
| 运行副本 | `inputs.json` SHA = 清单 SHA（一致） |
| 工程输入 / 保护证据 | **186 / 2024**（逐项 SHA256 全等，0 处不符） |
| 相对上一轮清单 | **只有 `tb_inst_lookup_protocol_resume.sv`**（保留字改名 `edge`→`edge_id`，无逻辑变化）+ 本轮 runner/sealer；其余全部逐字未变，桥仍 `f14b16cb…` |
| 绑定 | 部分复核收据 `2a482844…`（`checked_key` 617/415/18、`checked_A` 1472/512/256/256/0）；`historical_identity_relocations` 仍绑定保存副本 `55be65f6…`，活交接文档不被冻结 |
| Git | `git_before` 与 `git_after` **相等** ✔，`git_after_captured_in_finally=true`（方案第 39 行要求生效） |
| 前次 STOP 现场 | 清单/目录（除 work）/报告原样保留，未清理、未复用、未倒写 |

## 4. 未执行 / 未覆盖（不补造）

- 独立参考**未完成**核验：只走到 edge 6，其余边沿/场景（8 lane 命中、AR 背压、I/D 竞争、posted 写排空、三种复位相位、同行写后重取等）**未获独立核验**，本次不宣称协议组通过。
- 按 B-only 设计未重跑 key/A/control/旧桥/历史 031/030/ISA/CoreMark/PHY；未运行旧 runner/旧 tag。
- 未修改 RTL/旧 TB/清单/旧结果/旧门；未生成或改写任何 Codex 门。
- **PDS 时序/位流/串口/KEY0/实板全部 NOT_RUN**；"用户反馈时序通过"仍只是用户反馈，未经独立复核。
- 未覆盖（方案已声明）：x16 与关闭 I buffer、D/R 重叠许可、store-forwarding、真实 DDR/PHY 返回相位。

## 5. 建议的最小修复（待授权，我未自行实施）

把独立参考的 CPU→用户地址换算补上（1 处函数，4 个调用点自动受益）：

```python
DDR_BASE = 0x40000000
def line_base(addr):
    return (((addr - DDR_BASE) & 0x1FFFFFFF) >> 5) << 3
```

`line_index`/`lane_of` 无需改动。因方案明确"首FAIL 保留返回、不自动修后续 test 重跑"，我不自行改动；一旦授权，按工程约定绑定**新清单 + 新运行目录**（本 STOP 目录/清单/报告原样保留、不复用、不倒写）后再执行一次三 job。

## 6. 残余风险（如实交回）

修好地址换算后，独立参考将在 edge 6 之后**首次**核对 180+ 边沿与其余场景；`beat_from`/缓存初值比对、AW/W 归属、复位取消、idle 静默等断言是否还有同类口径问题，仍属未验证领域——下一次运行可能仍在参考侧首个不一致处停止（属保守失败，不会假 PASS）。
