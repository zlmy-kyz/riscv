# 任务032旧I命中响应沿双请求 单场景补测 结果：`ds_data_bus_inst_lookup_triple_20261014_a`

**状态：`TASK032_TRIPLE_SUPPLEMENT_PASS_REUSED_KEY_A_B`。按 Sol 封存入口执行一次，未改任何代码/判据/清单，未重跑整组。**

- 三条 job 各一次、全部 exit/native **0**、未超时：`vlib` 0.1289 s（上限 60）、`vlog` 0.4097 s（60）、`triple` vsim 1.8061 s（180）。
- **39 模块、`Errors: 0, Warnings: 0`**、恰好 2×`04030130`、正常 `$finish`、console 与 transcript 归一全文相同、无 FAIL/Error/Fatal/RPC。
- 独立参考**通过**且命中本轮唯一关键场景；Git 前后一致、全部输入与保护身份不变。

## 1. 唯一关键场景实测（本轮目的）

独立参考要求**同一个 pre-NBA 快照**上 `i_rsp && i_v && d_v && d_r && !i_r`：

```
E 8 1 1 1 | i_v=1 i_r=0 i_addr=00000044 | d_v=1 d_r=1 d_wr=1 d_size=2 d_addr=00000044 d_wdata=01020304 d_wstrb=a
          | i_rsp=1 i_rdata=471cf1c6 | d_rsp=0 | ...
```

- **`triple_edges = [8]`** —— 旧 I 命中**响应被消费的同一边沿**上，I 与 D 同时 valid、`D_READY=1` 使 `I_READY=0`：**只接受 D 一次**。
- 该边沿上旧 I 数据 **`0x471cf1c6`** 先被核验（失效前缓存值），同行 store 由此使该 I 行失效。
- 未接受的 **token 2**（I 读 `0x44`）保持字段直到**后续被接受**（edge 9）并正常响应（edge 11，读 miss 发 AR/R），与本轮"有效输入必须被覆盖"的要求一致。

## 2. token / 边沿对照

| token | 计划（`plan.log` 第 2 列场景=1） | 接受边沿 | 响应边沿 |
| ---: | --- | ---: | ---: |
| 0 | I 读 `0x40`（真实 DDR 整行 fill） | 4 | 6 |
| 1 | I 读 `0x44` hit（保存旧数据 `0x471cf1c6`） | 7 | **8**（与 triple 同沿） |
| 3 | D store `0x44`，`data=0x01020304`，`strobe=0xa`（只接受 D 一次；posted ACK 独立于 W 提交） | **8** | 9 |
| 2 | I 读 `0x44`（被 D 阻塞，字段保持至被接受；同行失效后转 miss） | 9 | 11 |

`plan.log`：`PLAN 0 1 0 0 00000040 2 00000000 0 0` / `PLAN 1 1 0 0 00000044 2 00000000 0 0` / `PLAN 2 1 0 0 00000044 2 00000000 0 0` / `PLAN 3 1 1 1 00000044 2 01020304 a 0`（字段：id/scen/tgt/write/addr/size/wdata/wstrb/cancel）。

## 3. 守恒与数据

| 项 | 实测 | 要求 |
| --- | --- | --- |
| accepts / responses / cancels | **4 / 4 / 0** | 4 接受、4 响应、零取消、零 outstanding |
| AR / R | **2 / 2** | `AR=R2` |
| AW / W | **1 / 1** | `AW=W1` |
| 日志边沿 | `edges=13`（`SUM accepts=4 responses=4 aw=1 w=1 edges=13`） | — |
| **旧 word** | **`0x471cf1c6`**（1193079238） | 保存旧缓存数据 |
| **新 word** | **`0x011c03c6`**（18613190） | 旧≠新，且为 W 已提交后的新字节 |
| 部分字节写校验 | `strobe=0xa` 只覆盖 byte1/byte3：旧 `471cf1c6` → 新 `011c03c6`，**未使能 byte0=`c6`、byte2=`1c` 保持不变** | 未使能字节保持 |

参考对完整 256-bit payload 与 32-bit strobe 逐字节比对，且 W 数据/使能由**封存计划**推导后与实际 AW/W 比对（不直接抄 DUT）；无 force/deposit DUT 内部。

## 4. 原始元数据与身份

| 项 | 值 |
| --- | --- |
| 清单 | `sim/data_bus_turnover/inputs_inst_lookup_triple.json` |
| 清单 SHA256 | **`fdd0e64a8fb5654f31010e44a5e24c1bee23ad7959cb3c56ddb32e08f0d4b13d`**（执行前实测与任务文件一致；执行后未变） |
| `--check-inputs` | `Static inputs verified; HDL NOT_RUN; 199 project / 2869 protected; one 4-token case` |
| 桥 | `f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0`（未变） |
| 运行副本 | `inputs.json` 与清单同源；三命令原生 argv/cwd/pid/exit/native/elapsed/timeout/cleanup 均已保存 |
| 日志 | `triple.log`/`triple.transcript`（归一相同）、`edge.log`（13 边沿 + SUM）、`plan.log`（4 token）、`compile.log`（39 模块、0/0） |
| Git | `git_before == git_after`（字节相同）✔；`git_unchanged=true` |
| 执行前前置 | tag 目录不存在 ✔、`pds_shell` = 0 ✔ |

## 5. 复用项与未覆盖项

- **复用**（本轮未重跑）：completion 的 196 工程/2651 保护与 44 接受=41 响应+3 取消、真实 AR/R 同沿 2、双请求 2、AW=W6、8 lane/背压/排空/三复位/部分字节写；原 key `617 周期 / 415 MEM / 18 接续`；A 组 1472 确定性 + 512 随机（随机 256 hit / 256 miss）。
- **未覆盖**：本补测不含物理 DDR/PHY 与实板；x16 与关闭 I buffer、D 读写重叠许可、store-forwarding、真实 DDR 返回相位未动态覆盖。
- **PDS 时序/位流、串口、KEY0、实板全部 NOT_RUN**；RTL/桥/IP/BIN 未改；用户时序反馈 PASS 保持；未做 Git 提交推送；未生成或改写任何 Sol/Codex 验收门；033 不启动。
- 失败链与历史目录（A/B/C 未执行/D/E/completion）**原样保留**，未删除、未复用、未回填。

## 6. 交回 Sol

原始证据齐备：新清单与 199/2869 逐项身份、三命令原生元数据、`triple.log`/transcript、`edge.log`+`plan.log`、独立参考结果（`triple_edges=[8]`、`accepts=4/responses=4/ar=2/r=2/aw=1/w=1`、`old_word/new_word`）、Git 前后、`result.json`（`status=TASK032_TRIPLE_SUPPLEMENT_PASS_REUSED_KEY_A_B`）。等待 Sol 原始证据复核。
