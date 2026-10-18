# 任务040 补正报告（fix01）

日期：2026-10-18。针对 Sol 审查 `PARTIAL_MECHANISM_SUPPORTED_NOT_ACCEPTED_REPAIR_REQUIRED` 的补正。
**未修改设计 RTL / PDS / IP / 成功 BIN**，未开串口、未上板、未提交推送。原 `run1/run2` 与 `report.md` 保持不动。

## 1. 已修正项（逐条对应审查意见）

| 审查意见 | 本轮处理 | 证据 |
|---|---|---|
| t3 采到沿前值，实际装入早一沿 | 相位分离：phase0 沿前快照采 t0/t1/t2/t4，phase1 在 `#1`（NBA 后）判定"本沿是否装入 IF/ID" | `EV,...,ph=1,LOAD_IFID` 行 |
| 两个 `always @(posedge)` 争用 cycle，出现跳拍（cyc=9 丢失、cyc=6/8 重复） | 合并为**单一** posedge 块，`cycle` 只有一个所有者 | 轨迹 cyc 连续无重复 |
| SLOWDELAY=8 实际 9 沿 | 延迟语义改为"接受后第 N 沿被消费"（`i_cnt <= N-1`） | `SLOWWIT id=3 addr=8 acc=8 rsp=16 consume=16 diff=8` |
| D 延迟同样偏移 | 同一修正 | `DAUDIT` acc=rsp=consume |
| 结束未排空、inflight≠0 | 400 拍后 `stop_accept=1`，再等 40 拍排空 | 所有运行 `inflight=0` |
| "零警告"与 compile.log 不符 | 如实报告 | 2 条 `simple_mmio.v:223 @* sensitive to all 13 words in array 'count'`（属 RTL，非本轮修改） |
| "非采样沿释放 reset" 与代码不符 | 改为真正在 `negedge` 释放 | `repeat(3)@(negedge clk); @(negedge clk); resetn=1` |
| 无独立架构参考 | 新增 `ref.py`：从 lst 解码 B/J 立即数生成正确路径退休 PC 序列，逐条比对 | 6 个运行 `ref_match=true` |
| 错路只写标志会漏检污染 | 增加 `x31` 初值检查（错路 `addi x31` 不得生效） | 全部 `X31CHECK ... 00000000` |
| 输入未封存、runner 不判停 | 新建 `sealed_fix01b/`（17 文件 + manifest），**编译/汇编/参考只从副本读取**；任一 FAIL/INCOMPLETE/参考不符即非 0 退出并停止 | `sealed tree: ...\) 17 files`，`ALL PASS` 时才返回 0 |

补充：`slow_delay` 由**接受地址**选择（`+SLOWADDR`），模型不读 DUT 的 taken/redirect。

## 2. 六组运行结果（build/fix01b/）

| 运行 | t0 | t1 | t2 | t3 | t4 | t1−t0 | t2−t1 | t3−t2 | t4−t3 | 错路在途@t1 | 判定 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| fast | 8 | 9 | 9 | 11 | 11 | **1** | **0** | 2 | 0 | 0 | PASS |
| slowwrong | 8 | 9 | 15 | 17 | 17 | 1 | **6** | 2 | 0 | **1** | PASS |
| oldmem_d1 | 10 | 11 | 11 | 13 | 13 | 1 | 0 | 2 | 0 | 0 | PASS |
| oldmem_d8 | 10 | 18 | 18 | 20 | 20 | **8** | 0 | 2 | 0 | 0 | PASS |
| nottaken | — | — | — | — | — | — | — | — | — | — | PASS（无重定向，retire=137） |
| serial（年轻 CSR） | 10 | 18 | 18 | 21 | 21 | 8 | 0 | **3** | 0 | 0 | PASS |

所有运行：`IAUDIT acc == rspgen == consume`、`inflight=0`、`DAUDIT` 一致、`x31=0`、`ref_match=true`。

### 真实延迟见证

```
SLOWWIT id=3 addr=00000008 acc=8 rsp=16 consume=16 consumed_minus_accepted=8
```

同一笔慢请求：接受于 cycle 8，响应在 16 有效并被消费，**差正好 8 沿**，符合任务要求的
"N=8 在 E+8 消费"，不再有原先的 9 沿偏移。

### 与上轮结论的差异（不得混用）

- 错路占槽由"7 拍"改为 **6 拍（t2−t1）**；同时以 `SLOWWIT` 的 8 沿作为延迟口径的独立见证。
  两者不等是因为 redirect 发生时慢请求已过 1 沿，剩余等待 7 沿、目标在下一可接受沿落地。
- **上轮"2 拍装入是结构下限、入 ID 零拍发射"作废**：本轮 t3−t2 仍为 2、t4−t3 仍为 0，
  与 Sol 审查给出的期望（装入 1 沿、装入→发射 1 沿）**不一致**，见第 4 节。

## 3. OTHER 与 ROI

观察窗从分支事件开始、到目标完成 store 退休结束（不再把之后的自旋算入）：

| 运行 | ROI 拍 | OTHER | MEM | IF | branch | ctrl_hold | OTHER∧retire | OTHER∧无retire | OTHER∧id_fire |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| fast | 7 | 5 | 0 | 0 | 2 | 0 | 3 | 2 | 3 |
| slowwrong | 13 | 4 | 0 | 1 | 8 | 0 | 1 | 3 | 2 |
| oldmem_d1 | 7 | 5 | 0 | 0 | 2 | 0 | 4 | 1 | 3 |
| oldmem_d8 | 21 | 5 | 14 | 0 | 2 | 0 | 4 | 1 | 3 |
| serial | 22 | 5 | 14 | 0 | 1 | 2 | 3 | 2 | 3 |

交叉统计可能重叠，不相加当互斥分解。ROI 内 OTHER 只占 4~5 拍，主体仍是正常推进；
`serial` 出现 `ctrl_hold=2`，对应年轻 CSR 变体里排空取消的两拍。

## 4. 仍未解决（不掩盖）

**t3/t4 的归属仍有 ±1 的不确定**：本轮 t3 用 phase1（NBA 后）判定"本沿装入"，
但实测 fast 为 t2=9 → t3=11（差 2）、t4=11（与 t3 同拍）；
而 Sol 审查据原始轨迹推算应为"接受→装入 1 沿、装入→发射 1 沿"（差 1/1）。

本轮没有把这两者调和。可能原因（未证实，不写成结论）：
- 目标响应在 cycle 10 消费时 `inst_if_id_accept` 不成立，响应先进 `inst_buffer`，
  cycle 11 才 pop 进 IF/ID，因此"接受→装入"天然是 2；
- 若如此，则 `t3` 应定义为 buffer pop 沿而非 valid 出现沿，t4 应在下一沿。

原始逐沿轨迹（含 `ph=0/ph=1`、pending/buffer owner PC）已保留在
`build/fix01b/<run>/run.log`，供 Sol 直接判定这一归属，本报告不擅自改判据。

## 5. 封存、命令与判停

- 封存树 `sealed_fix01b/`：17 个文件（TB、CPU 039、5 个 RTL 依赖 + `csr_defs.vh`、
  `mul_behavioral.v`、`asm.py`、4 个程序、`ref.py`、`run.py`）+ `manifest.json`（SHA256）。
  编译、汇编、参考**全部只从该树读取**；重复运行前会逐文件复验 SHA，被篡改即拒绝。
- 命令：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 sim/cpu_ex_redirect/id_ex_attribution_20261018_a/fix01_src/run.py --tag fix01b
```

- 退出码：编译失败 4、汇编失败 5、参考失败 6、任一组未通过 7、全部通过 0。
  本次 `ALL PASS`（0）。
- 原始日志：`build/fix01b/<run>/{program.lst,ref_pc.txt,ref_meta.json,run.log}`，
  编译日志 `build/fix01b/compile.log`，汇总 `build/fix01b/result.json`（含封存清单副本）。

## 6. 边界

CPU 身份未变（`5c26df02…d47745`），无需新 PDS；本组仍只属 040 测量。
未覆盖：真实 I 缓存/DDR miss 分布、真实 P/V 占比、IRQ 与排空并发、JALR 间接目标、
t3/t4 归属的最终裁定。不据本报告修改 RTL 或承诺性能收益。
