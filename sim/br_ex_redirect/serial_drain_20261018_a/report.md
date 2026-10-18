# 任务038 定位报告：EX 重定向冲刷串行排空导致永久停滞

日期：2026-10-18。只做最小定位，**未修改任何设计 RTL / PDS / IP / 成功镜像**，未开串口、未跑 PDS、未做 Git 提交推送。

## 1. 结论

**EXPECTED_BUG_REPRODUCED（两种形态）**。

EX 级分支重定向把 ID 里唯一能发射的串行指令（CSR/FENCE/WFI）冲刷掉之后，
`flow_state` 仍停在 `FLOW_SERIAL_DRAIN`，而该状态的唯一出口 `serial_issue`
要求 ID 里还有 `serial_candidate`，于是永远不成立 → 前端被 `frontend_hold` 永久钉住。

对照：同一微程序在冻结的旧 ID 版 CPU 上全部正常完成，控制组在两个版本上都正常。
所以程序、激励与模型有效，缺陷由 EX 重定向引入。

## 2. 复现结果

### 冻结 EX CPU（`ef6bfec…06cc87e6`）

| 模式 | 场景 | 结果 | drain | redirect | 停滞 | 目标 |
|---|---|---|---:|---:|---:|---|
| 1 | A：分支紧邻 CSR（ddelay=1） | **EXPECTED_BUG_REPRODUCED** | cyc 13 | cyc 12 | **cyc 13** | dmem[0]=0 未达 |
| 2 | B：load 等待中排空（ddelay=10） | **EXPECTED_BUG_REPRODUCED** | cyc 15 | cyc 24 | **cyc 25** | dmem[0]=0 未达 |
| 3 | 对照：分支紧邻普通 ALU | PASS | — | cyc 12 | — | dmem[0]=1 |
| 4 | 对照：CSR 在正确路径 | PASS | cyc 12 | cyc 32 | — | dmem[0]=1 |

### 冻结旧 ID CPU（`b1114fa…0f4a41d3`，对照）

| 模式 | 结果 | 说明 |
|---|---|---|
| 1 | **NO_REPRODUCTION**，dmem[0]=1 | 从未进入 `FLOW_SERIAL_DRAIN`（drain=-1）：分支在 ID 就重定向，CSR 根本没进 ID |
| 2 | **NO_REPRODUCTION**，dmem[0]=1 | 同上 |
| 3 | PASS | 对照 |
| 4 | PASS，drain=cyc 12 | 正确路径的 CSR 正常完成一次排空，机制本身有效 |

## 3. 第一分歧轨迹（原始见证）

### 形态 A：同一拍既启动排空又被冲刷（ddelay=1，m1）

```
cyc=12 pc=00000010 ifid=1/00000008/34009073 idex=1/00000004/0/00000008
       fire=0 adv=1 rdir=1 tgt=00000010 fs=0 sc=1 si=0 pe=0 hold=1
       ↑ ID 里是 CSR(34009073)，serial_candidate=1；同时 EX 分支重定向
cyc=13 pc=00000010 ifid=0/ffffffff/00000013 idex=0/…  fire=0 adv=0 rdir=0
       fs=1 sc=0 si=0 pe=0 hold=1
       ↑ ID 被冲刷，候选消失，但 flow_state 已锁在 SERIAL_DRAIN
cyc=14..16  fs=1 sc=0 si=0 hold=1（永久）
```

`FLOW_RUN → FLOW_SERIAL_DRAIN` 的转移用 cyc=12 的 `serial_candidate`，
而同一拍的 `branch_redirect` 又通过 `kill_if_id` 清掉了 IF/ID。两件事同时成立，状态机与数据源互相矛盾。

### 形态 B：排空先建立，9 拍后才跳转（ddelay=10，m2）

```
cyc=14 ifid=1/00000010/34009073  sc=1 fs=0 pe=0 hold=1 adv=0   ← CSR 进 ID，分支在 EX 等 load
cyc=15 ifid=1/00000010/34009073  sc=1 fs=1 pe=0 hold=1 adv=0   ← 进入 SERIAL_DRAIN，但 pipeline 非空
cyc=16..23  同上（等 load 响应，serial_issue=0 因为 pipeline_empty=0）
cyc=24 ifid=1/00000010/34009073  sc=1 fs=1 pe=0 hold=1 adv=1 rdir=1
         ↑ load 响应到，分支 advance 并重定向
cyc=25 ifid=0/ffffffff/00000013  sc=0 fs=1 si=0 hold=1          ← 候选被冲掉，永久停滞
```

**证据价值**：B 证明"只在 `FLOW_RUN → FLOW_SERIAL_DRAIN` 入口加 `!branch_redirect` 门控"是不够的。
这里排空比重定向早 9 个周期建立，入口门控完全看不到后面那次 redirect，必须给
`FLOW_SERIAL_DRAIN` 本身加"候选已消失则退出"的判据。

## 4. 静态机制

`myriscv/mycpu_sync.v`（冻结 EX 版）：

```verilog
assign serial_candidate = if_id_valid && (serial_csr || serial_system || serial_fence);
assign serial_issue     = (flow_state == FLOW_SERIAL_DRAIN) && pipeline_empty && serial_candidate;
...
FLOW_RUN:          else if (fetch_valid && serial_candidate) flow_state <= FLOW_SERIAL_DRAIN;
FLOW_SERIAL_DRAIN: if (serial_issue)                        flow_state <= FLOW_SERIAL_RUN;
...
assign kill_if_id = redirect_valid || serial_issue;
assign frontend_hold = (flow_state != FLOW_RUN) || load_use || data_pipeline_stall || serial_candidate || …
```

- `FLOW_SERIAL_DRAIN` 只有 `serial_issue` 一个出口，而 `serial_issue` 的唯一数据源是 `if_id_valid` 的串行项；
- redirect 用 `kill_if_id` 清掉这个唯一的串行项；
- 之后 `serial_candidate=0 → serial_issue=0`，状态永不出清；`frontend_hold=1` 又禁止前端再装指令，
  连"重新取到一条新的串行项"都不可能 → 死锁闭环。

旧 ID 版为什么没事：分支在 ID 判定并当拍重定向，ID 里那条就是分支本身，不可能是 CSR；
"分支在 EX、年轻 CSR 在 ID"这个重叠窗口在旧结构里不存在。

## 5. 与实板失败的一致性

- 实板日志：123 条 RVLD 全 PASS、VERIFY 与唯一 RUN 成功、应用 RX=0、40 s 超时
  （`sim/cpu_ex_redirect/board/ex_redirect_reviewed_300_01/performance_300.json`、
  `sim/cpu_ex_redirect/board/new_bit_0615_300_01/performance_300.json`）。
- 本定位的形态 A 正是"分支后紧跟 CSR"，而固定 P300 在 `program.bin` 偏移 0x120 为
  `104080e7`（JALR 到 trap_dispatch），紧随 0x124 为 `34151073`（CSRW MEPC,a0）。
- 因此时间线与现象吻合：应用启动早期在 BSP 路径上遇到"JALR/分支紧邻 CSR"，
  一旦命中即停摆在 `FLOW_SERIAL_DRAIN`，第一条 UART 输出之前就再也不会前进。
- **边界**：这仍是"最小复现 + 机制一致"，不是已用实板轨迹直接证实的根因；C 场景（真实 BIN 片段）未做。

## 6. 修复方向（本任务未实施，供 Sol/Astra 决策）

两类形态需要不同的处理，缺一不可：

1. **入口侧（治形态 A）**：`FLOW_RUN → FLOW_SERIAL_DRAIN` 的转移条件加上 `!redirect_valid`，
   避免"同一拍既启动排空又冲刷候选"。
2. **出口侧（治形态 B，且是必需的）**：在 `FLOW_SERIAL_DRAIN` 里增加
   "候选已消失（`!serial_candidate`）且排空尚未真正开始（`!pipeline_empty` 或
   `id_ex_serial` 未在飞）→ 撤销回 `FLOW_RUN`"。
   必须区分"排空由被冲刷项启动"和"串行项已发射进 EX（`FLOW_SERIAL_RUN`）"：
   后者不能撤销，否则会破坏串行语义。

## 7. 输入与复现命令

| 输入 | SHA256 |
|---|---|
| 冻结 EX CPU `candidate_cpu_from_HEAD.v.txt` | `ef6bfec7853f6b0e93f976c7038ad25cdb4f6e04b14251331fdbf79906cc87e6` |
| 旧 ID CPU `observed/myriscv/mycpu_sync.v` | `b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3` |

```powershell
Set-Location D:\riscv\RISCV
$ex = "sim/cpu_ex_redirect/board_review_20261018_a/observed/candidate_cpu_from_HEAD.v.txt"
$id = "sim/cpu_ex_redirect/board_review_20261018_a/observed/myriscv/mycpu_sync.v"

python -X utf8 sim/br_ex_redirect/serial_drain_20261018_a/run.py --tag ex_d1  --cpu $ex --ddelay 1
python -X utf8 sim/br_ex_redirect/serial_drain_20261018_a/run.py --tag ex_d10 --cpu $ex --ddelay 10
python -X utf8 sim/br_ex_redirect/serial_drain_20261018_a/run.py --tag id_d1  --cpu $id --ddelay 1
```

编译命令：`iverilog -g2012 -Wall -Wno-timescale -I myriscv -o build/<tag>/tb.vvp
tb_serial_drain.v <cpu> regfile.v alu.v l_alu.v br_alu.v csr_file.v mul_behavioral.v`
（零 warning；每次运行的完整输入 SHA 记录在 `build/<tag>/result.json`）。

### 模型延迟合同

- 指令侧：**1 拍命中**。E 接受地址并组合读，E+1 `rsp_valid` 与数据同时有效，
  E+1 允许同沿再接受下一笔；无零拍响应。任务明确否决的两拍模型未使用。
- 数据侧：`+DDELAY=n`，n=1 为 1 拍命中，n>1 为 n 拍计数器模型（用于构造 B 形态的先排空后跳转）。
- 超时：2000 拍，用于判定停滞；超时前完整轨迹保留在 `build/<tag>/m*/run.log`。

## 8. 覆盖与缺项

已覆盖：A 形态（同拍）、B 形态（排空早于重定向 9 拍）、两个对照（ALU 顺序项、正确路径 CSR）、
EX 与 ID 两版同刺激对照、逐沿完整轨迹。

未覆盖：C（真实 P300 启动片段 `0x40000120/124` 的字节级复现）、FENCE/WFI 变体、
IRQ 与排空并发、真实 DDR 多主机仲裁。**不把本报告写成实板根因已证实**，
也不据此宣称任何功能或性能验收。

## 9. 修复与复验（同日，用户确认后实施）

### 改动（`myriscv/mycpu_sync.v`，flow_state 状态机）

```verilog
FLOW_RUN: if (irq_candidate)
              flow_state <= FLOW_IRQ_DRAIN;
          // 同拍已有重定向时不得启动串行排空
          else if (fetch_valid && serial_candidate && !redirect_valid)
              flow_state <= FLOW_SERIAL_DRAIN;
FLOW_SERIAL_DRAIN: if (serial_issue)
                       flow_state <= FLOW_SERIAL_RUN;
                   // 候选被更年轻的重定向冲掉 → 撤销回 RUN
                   else if (!serial_candidate)
                       flow_state <= FLOW_RUN;
```

- 入口加 `!redirect_valid`：治形态 A（同拍转向）。
- 出口加 `!serial_candidate → FLOW_RUN`：治形态 B（排空已建立后才重定向）。
  串行项一旦真正发射就转入 `FLOW_SERIAL_RUN`，不会走到这条撤销分支，串行语义不受影响。

### 判据修正

初版 `stuck` 判据是"任意一拍 `fs==DRAIN && !sc`"，修复后撤销的那一拍也会命中，
造成假阳性（`dmem0=1` 却报复现）。已改为**连续 8 拍**才判永久停滞；
冻结版在两种判据下结论一致（`fs` 会一直保持到 2000 拍超时）。

### 复验结果

| RTL | ddelay | A | B | 对照 ALU | 对照 CSR |
|---|---:|---|---|---|---|
| 冻结 EX `ef6bfec…` | 1 | 复现(stuck 13) | 复现(stuck 15) | PASS | PASS |
| 冻结 EX `ef6bfec…` | 10 | 复现(stuck 13) | 复现(stuck 25，drain 15 / redirect 24) | PASS | PASS |
| **修复版** | 1 | **NO_REPRODUCTION** dmem0=1 | **NO_REPRODUCTION** dmem0=1 | PASS | PASS |
| **修复版** | 10 | **NO_REPRODUCTION** dmem0=1 | **NO_REPRODUCTION** dmem0=1 | PASS | PASS |

### 副作用检查

`sim/br_ex_redirect/run.py --tag postfix_20261018_a`：六项定向用例 PASS、错位 jalr 仍正确 trap、
**bench cycles = 11021（与修复前完全一致）**，说明本次修复不引入任何周期开销。

