# 任务040 补正02 报告（fix02）

日期：2026-10-18。承接 `review_20261018_02`，**未修改 RTL / PDS / IP / 成功 BIN**，未开串口、未上板、未推送。
旧 `fix01b`、`run1/run2`、`report.md`、`report_fix01.md` 全部保持不动。

## 1. 偏差根因与修法

审查指出：封存 TB 里模型块写 `cycle`、观察器在另一个 posedge 块读它，`#1` 读到的是**已被下一进程更新后的全局值**；
fast 日志中 phase0 打印 cyc10、phase1 却打印 cyc11，紧接下一物理沿 phase0 才是 cyc11；`oldpend_pc` 也读到了新请求 PC。
"单一 posedge 块"的说法与实际不符。

**修法：彻底不用可变 cycle 作为沿号。** 所有事件改由 `$time` 打时间戳（时钟 10 ns，posedge 在 5/15/25…），
存储模型也用绝对时间调度响应；没有任何进程通过读取另一个进程维护的计数来决定接受/消费时刻。
相位分离保留：phase0 拍快照（含 OLD pending/buffer/响应 request_id 冻结），phase1 在 `#1` 后核实际装入。
新增 `t3 < t4` 的严格有序断言。

## 2. 五沿表（绝对时间 ns；间隔 = 物理沿数）

| 运行 | t0 | t1 | t2 | t3 | t4 | t1−t0 | t2−t1 | t3−t2 | t4−t3 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fast | 85 | 95 | 95 | 105 | 115 | 1 | 0 | **1** | **1** |
| slowwrong | 85 | 95 | 155 | 165 | 175 | 1 | **6** | **1** | **1** |
| oldmem_d1 | 105 | 115 | 115 | 125 | 135 | 1 | 0 | **1** | **1** |
| oldmem_d8 | 105 | 185 | 185 | 195 | 205 | **8** | 0 | **1** | **1** |
| nottaken | 95 | — | — | — | — | — | — | — | — |
| serial（年轻 CSR） | 105 | 185 | 185 | 205 | 215 | 8 | 0 | **2** | **1** |

**与审查的离线推导逐项吻合**（审查给的是旧编号，间隔应相同）：

| 运行 | 审查推导间隔 | 本轮实测间隔 |
|---|---|---|
| fast | 1 / 0 / 1 / 1 | **1 / 0 / 1 / 1** |
| slowwrong | 1 / 6 / 1 / 1 | **1 / 6 / 1 / 1** |
| oldmem_d1 | 1 / 0 / 1 / 1 | **1 / 0 / 1 / 1** |
| oldmem_d8 | 8 / 0 / 1 / 1 | **8 / 0 / 1 / 1** |
| serial | 8 / 0 / 2 / 1 | **8 / 0 / 2 / 1** |

即：**目标接受→装入 IF/ID 为 1 沿、装入→ID 发射为 1 沿**，上一版"2 拍 / 0 拍"的判断作废。
`serial` 比 `oldmem_d8` 多 1 沿（3−2=2），对应审查指出的"响应在 DRAIN 取消期间进 buffer 再 pop"，
本轮由绝对时间戳实际见证，不再是猜测；`ROI` 里 `ctrl_hold=2` 与之对应。

## 3. 真实延迟见证

```
SLOWWIT id=3 addr=00000008 acc=75 rsp=155 consume=155 edges_acc_to_consume=8
```

同一笔慢请求：接受于 t=75 ns、155 ns 被消费，**正好 8 沿**，符合"N=8 在 E+8 消费"。
（上一版此处打印 0 是因为消费沿用了被新请求覆盖的 `i_rsp_id_q`，已改为沿前冻结的 `cons_id`。）

## 4. 参考与守恒

- `ref.py` 改为**架构小解释器**：从 lst 解码 `addi/add/sub/xor/or/and/lw/sw/beq/bne/blt/bge/jal/csrw`，
  只按架构状态推进，不读任何 DUT 信号，输出每条 `pc/inst/rd/we/value/next_pc`。
- runner 对 **6 个运行全部**逐条比对上述字段（`ref=OK`），不再出现"mode4 跳过参考却记 ref_match=true"。
- 六个运行都核 `x31 == 0` 与 `mscratch == 0`（CSR 变体不再只凭 PC 前缀排除副作用）。
- I 侧：`acc == rspgen == consume`、`inflight=0`（399/392/399/385/399/384）；D 侧：`acc == rspgen == consume`、
  `stores` 与程序一致、`dmem[0]=1`。
- `nottaken` 有自己的 ROI（edges=6）与自己的参考，不再等 taken 的 t0 才开始。

## 5. 命令、封存与判停

- 封存 `sealed_fix02d/`：17 个文件 + `manifest.json`（含 TB、reference、runner、4 个程序、`asm.py`、
  CPU 039、5 个 RTL 依赖、`csr_defs.vh`、`mul_behavioral.v`）。**编译、汇编、参考、运行全部只从副本读取**。
- `build/fix02d/commands.json` 记录每条真实命令的 `argv/cwd/exit/stdout/stderr`（iverilog、ref、vvp 全过程）。
- 判停：编译 4 / 汇编 5 / 参考 6 / 任一组非 PASS 或参考不符 7；检查**所有** `RESULT:` 行而非只看第一条。
  本次 `ALL PASS`（0）。
- 编译告警如实保留 2 条（`simple_mmio.v:223 @* sensitive to 13 words 'count'`，属 RTL，不是本轮改动）。

## 6. 结论与边界

- ① ID 发射→EX 重定向 **1 沿**（结构下限）；
- ② 错路占槽：redirect 时慢请求在途，`t2−t1` 由 0 变 **6**，慢请求自身 `acc→consume = 8 沿`；
- ③ 更老 MEM：`t1−t0` 由 1 变 **8**，`t2−t1` 仍 0，MEM 分类 0→14；
- ④ OTHER 在短 ROI 内仅 4~5 沿，主体是正常推进；不复用 400 沿自旋统计。

未覆盖（保持）：真实 I 缓存/DDR miss 分布、真实 P/V 占比、IRQ 与排空并发、JALR 间接目标。
本组仍只属 040 测量，不据此改 RTL 或宣称性能收益。
