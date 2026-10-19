# 任务032二次时序修复B 结果：I标签并行查询重跑（`ds_data_bus_tag_lookup_repair_b_20261014_a`）

**状态：`STOPPED_FIRST_FAILURE`。首败即停、现场保留、未重试、未改任何既有冻结文件。**

本次是方案[任务032二次时序修复](任务032二次时序修复_I标签并行查询关键仿真.md)授权下的**第一次重跑**（首次尝试见[任务032二次时序修复_结果_ds_data_bus_tag_lookup_repair_20261014_a.md](任务032二次时序修复_结果_ds_data_bus_tag_lookup_repair_20261014_a.md)）。
授权范围：修首次尝试中我新增管线代码的两处缺陷（lookup console 读错文件、轨迹 `scenario` 未初始化），绑定新清单+新目录重跑一次。

## 已通过的实质内容

| 项 | 结果 |
| --- | --- |
| vlib / vlog（34 源） | exit/native 0，未超时；**39 模块**、`Errors: 0, Warnings: 0` |
| 原 SoC key | exit/native 0；`UNIT cycles=33 turns=51 cancelled=1`、`SOC cycles=617 events=82 turns=18 mem_wait=415 ...`、五组 CHECK 全过、2×`04030130`、`Errors: 0, Warnings: 0`；`check_key()` 整段 `checked_key` 相等断言**已通过**（**617/415/18 保持**） |
| 新标签查询 vsim | exit/native 0；`RESULT: PASS tag_lookup det=1472 rnd=512 mismatches=0 hits=64 misses=1920`、2×`04030130`、`Errors: 0, Warnings: 0`、正常 `$finish`；**console==transcript 断言已通过**（首次尝试的缺陷(a) 已修复） |
| 轨迹 `scenario` 初值 | 已修复（缺陷(b)），轨迹首列已为 0..1983 连续编号 |

## 失败点：我的独立检查器状态模型错误

`check_tag_lookup.py:118`：

```python
assert selected_valid == expected_valid[r], (selected_valid, expected_valid[r])
AssertionError: (1, 0)
```

检查器在**同一行内持久化** `expected_valid[r]`：处理 `kind==1`（所选行 valid=0）时置 0 后未复位，
而 TB 在进入 21 个高位翻转场景前已恢复 `tab_valid[r]=1`。因此对 `kind==2` 记录，TB 记录的 `valid=1` 与检查器残留的期望 0 不符。
**TB 行为正确**（翻转场景确实 valid=1、期望 miss），错的是我的检查器记账方式，不是 DUT、TB 激励、参考或判据。

## 修复与离线复算（只读，未产生新运行）

- 修正为**逐条按场景推导所选行的准备态**（不再跨记录持久化）：`kind 0 → (BASE, valid1)`、`kind 1 → (BASE, valid0)`、`kind 2(bit b) → (BASE^(1<<b), valid1)`。
- 用**本次已落盘的真实轨迹**离线复算修正后的检查器：

```
RESULT: PASS tag_lookup det=1472 rnd=512 rows=64 high_bits=21 tables=512 hits=64 misses=1920 mismatches=0
```

- 同时对 `check_lookup()` 的整条断言链做了只读彩排（console/transcript 归一相等、无 FAIL/Fatal、恰好 2×`04030130`、`det=1472 rnd=512 rows=64 high_bits=21 tables=512 seed=20261014`、`hits>0 and misses>0`、`mismatches=0`）→ 全部通过。
- 另发现并修正封存口径一处：随机 `TBL` 记录为**每条随机观察一行**（64 行 × 8 = 512），此前预期的 `tables=64` 有误，应为 **512**。

## 身份与保护

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_tag_lookup_repair_b.json`，SHA **`9c8b684e6d30af122ebe2871a0f23ac38698bce004d176fdece75b7553c8c4be`** |
| 工程输入 / 保护证据 | 174 / 1212（逐项 SHA256 全等）；运行副本 `inputs.json` SHA = 清单 SHA |
| 相对 STOP-A 清单 | **只有 `tb_inst_tag_lookup.sv` 一处变化**（172→174：另加 B 的 runner/sealer） |
| 桥 | `1170cfd21a9dc01fe526256a778309f0f657b0445ff53707ddfdc877a7280406`（未变） |
| 未变 | checker、原 TB、unit/include/模型/参考/DAT/编译源/模块数(39)/超时/判据 |
| STOP-A 现场 | 清单、运行目录（除 `work`）、报告全部原样保留，未清理、未倒写 |
| Git | `git_before.json` 已保存；`git_after.json` **未生成**（失败于其写入之前），不补造 |

## 未执行 / 未覆盖

- 未重跑 control/历史 031/030/ISA/CoreMark/PHY；未运行旧 runner/旧 tag；未生成 Codex 门。
- 未修改设计 RTL / PDS / IP / 成功镜像 / 判据 / 超时。
- **PDS 时序、位流、串口、KEY0、实板全部 NOT_RUN**：不证明 WNS −0.218 ns/TNS −0.431 ns/2 端点是否修复。
- 方案已声明：AR 接受同拍 R 返回相位未由冻结模型动态模拟；标签查询组不模拟 DDR 返回相位与 x16 行为。

## 处置

检查器修正已用本目录真实轨迹离线复算通过，故按同一授权以**新清单+新目录（C）**重跑同样四个 job 一次，产出可自洽 PASS 的记录；本目录按约定保留、不复用、不倒写。
