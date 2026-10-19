# 任务032寄存查询协议B续测D 结果：`ds_data_bus_inst_lookup_protocol_resume_d_20261014_a`

**状态：`STOPPED_FIRST_FAILURE`（仅因 runner 引用参考返回字典中不存在的键）。首败即停、现场完整保留、未重试。**

**实质结论：本版 B-only 协议组在本轮通过了两道独立检查。** 失败发生在两道检查都已通过之后的一行多余断言。

| job | exit | native | elapsed | 上限 | 结果 |
| --- | ---: | ---: | ---: | ---: | --- |
| vlib | 0 | 0 | — | 60 s | 正常 |
| vlog | 0 | 0 | — | 60 s | **39 模块、`Errors: 0, Warnings: 0`** |
| B-only vsim | 0 | 0 | — | 180 s | 未超时；console/transcript 归一相同、`$finish`、2×`04030130`、无 FAIL/Fatal |
| 独立 Python 参考 | **通过** | — | — | — | 见下（含对**本次自身轨迹**的离线重放） |
| runner 后置断言 | **失败** | — | — | — | `KeyError: 'outstanding'` |

## 1. TB 自检（协议仿真）

```
RESULT: PASS inst_lookup_protocol_resume scenarios=17 tokens=43 accepts=43 responses=40
       cancels=3 resets=3 ar=19 r=18 aw=5 w=5 edges=189 mismatches=0
Errors: 0, Warnings: 0
```
与执行前封存计划完全一致：`{scenarios:17, tokens:43, accepts:43, responses:40, cancels:3, resets:3, planned_cancel_ids:[37,39,41]}` → `accepts = responses + cancels`、outstanding 0、3 笔计划取消全中。

## 2. 独立参考（对本次运行自身轨迹的离线重放）

```
REPLAY PASS scenarios=17 tokens=43 accepts=43 responses=40 cancels=3 resets=3
            ar=19 r=18 aw=5 w=5 edges=188 mismatches=0
            lanes=8 ready_blocked=6 busy_blocked=14 competition=3 idle_silent=17
            hit_after_miss=8 miss_after_hit=8 hit_after_hit=9 refetch_changed=1
```
即方案要求的覆盖计数全部非零：**8 个 lane 逐 word 命中**、**AR 背压阻塞 6 拍（≥3）**、**写排空阻塞 14 拍**、**I/D 竞争 3 次**、**idle 静默 17**、**同行写后重取新值 1 次**、三相位复位取消各 1 笔、hit→miss / miss→hit / hit→hit 序列均有覆盖。

## 3. 唯一失败点（runner 侧，非 DUT/参考）

`run_inst_lookup_protocol_resume_b.py` 的 `check_protocol` 末尾：

```python
assert result['outstanding'] == 0, result       # KeyError: 'outstanding'
```

独立参考的 `review()` 并不返回 `outstanding` 键；它自身已在内部断言了守恒（`accepts == responses + cancels`、结束时 `read_owner`/`write_owner` 均已释放）。该行是我 runner 里的多余断言，**与 DUT、TB、参考、判据无关**；且它此前已通过 `accepts == responses + cancels` 与 `mismatches == 0` 两项断言。

## 4. 本次运行前的离线收敛（同一授权下的静态检查，未运行 HDL）

| # | 侧 | 缺陷 | 验证 |
| --- | --- | --- | --- |
| 1 | 参考 | `line_base` 用裸 CPU 地址算行基址 | 重放越过 edge 6 |
| 2 | TB | 同沿先提交写字节再生成 R 数据（方案要求先取边沿前内存） | 与方案对齐；本激励下无同沿 W 提交与 R 握手，**行为中性** |
| 3 | 参考 | W 完成只认同沿 `w_r && aw_hs`，漏掉"AW 已接受"（RTL 无 WVALID） | 重放越过 edge 125 |
| 4 | 参考 | 复位只撤 token，`valid` 未清 | 重放越过 edge 154 → **全 188 边沿重放 PASS** |

## 5. 身份、保护与 Git

| 项 | 值 |
| --- | --- |
| 清单 | `inputs_inst_lookup_protocol_resume_d.json`，SHA `cdc0e15d52507c427863bc0b51eb9c9d4370607f1f1e3ebe190bed3ad22a7721` |
| 工程/保护 | 190 / 2231（逐项 SHA256 全等） |
| 桥 | `f14b16cb…`（未变） |
| Git | `git_before == git_after` ✔，`finally` 已保存 after 与错误上下文 |
| 未执行 | 未派发 key/A/control/旧版/history/ISA/PHY；未改 RTL/旧清单/旧结果/旧门；**PDS/位流/串口/KEY0/实板 NOT_RUN**；未生成 Codex 门 |

## 6. 处置

按同一授权删除该行多余断言并绑定新清单 `_e` 再执行一次三 job，以产出可自洽的 PASS 记录；本目录、清单与轨迹按约定保留、不复用、不倒写。
