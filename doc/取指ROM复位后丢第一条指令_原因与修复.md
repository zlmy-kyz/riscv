# 取指 ROM 复位后丢失第 0 条指令 —— 原因与修复

> 对象:`source/tb_topcpu.v`、`myriscv/topcpu.v`、`ipcore/inst_rom/`
> 现象:复位在 95 ns 释放,100 ns 处 `debug_pc/debug_inst` 期望 `(00000000, 00A00093)`,实测 `(00000000, 00000000)`;此后逐拍一一对应
> 日期:2026-09-12

---

## 1. 结论速览

| # | 结论 |
| :-- | :-- |
| 1 | **不是 IP 坏了**,但确实和 IP 的复位行为有关 —— 是"接法 + IP 复位时序"不匹配。 |
| 2 | 根因:ROM 的**地址端口接的是 `next_pc`**,而复位期间 `pc = 0` → `next_pc = 4` → ROM 地址端口在整个复位期间就是 **word 1**。 |
| 3 | ROM 内部地址寄存器 **不带复位**(`GTP_DRM36K_E1.v` 第 711–725 行只在 `posedge CLKA` 赋值),所以它在复位期间照常锁存,复位结束时已经指向 **word 1**。→ **word 0 从头到尾没被寻址过。** |
| 4 | ROM 输出在 `rst` 撤销后还会被强制为 `RSTA_VAL`(=0)**一个时钟**(内部把 `rst` 打了一拍 → `rsta_int`)。所以 100 ns 那拍 `rd_data = 0`,锁进 IF/ID 就是 `(0, 0)`。 |
| 5 | 从下一个沿起 `ada_reg == pc/4` 恒成立,配对自洽 —— 这解释了"之后都一一对应"。 |
| 6 | 修复 = **让 CPU 侧复位比 ROM 侧复位晚一拍释放**(PC 保持不动多一拍)。实测:100 ns 仍是 1 个气泡,110 ns 正确给出 `(0, 00A00093)`,之后全部正确。 |
| 6b | 另一条路:**换成方案一-B(`addr = PC`、指令不寄存)**。真 IP 实测 **0 气泡、不需要任何额外逻辑/FF**,而且首条指令早一拍进 ID。代价是 ROM 同步读延迟落进 ID 关键路径。详见 6.1。 |
| 7 | ⚠️ **仅加"复位期间 next_pc = pc"的门控是不够的**(已做对照实验,见第 6 节)。 |
| 8 | ⚠️ 气泡**不能靠"全零"表示**:`0x00000000` 不是 NOP 而是**非法指令**,且 `if_id_pc = 0` 与复位向量同形、无法区分。**必须用 `valid` 标记气泡**,并让每个副作用(`rf_we`/`mem_write`/`br_taken`)与 `valid` 相与。见 4.4。 |

---

## 2. 现象复现

用**Pango 官方 RTL 行为模型**(`GTP_DRM36K_E1.v`)+ 工程真实文件(`inst_rom_init_param.v` 固化的初始化数据)在 iverilog 下复现,激励与 `source/tb_topcpu.v` 完全一致(10 ns 周期、`resetn` 在 95 ns 释放):

```
  time | resetn |   pc    | next_pc | rom_addr(word) | ada_reg |  rom_inst  | if_id_pc | if_id_inst
-------+--------+---------+---------+----------------+---------+------------+----------+-----------
    91 |   0    | 00000000 | 00000004  |       1        |    1    | 00000000 | 00000000 | 00000000
   101 |   1    | 00000004 | 00000008  |       2        |    1    | 00508113 | 00000000 | 00000000   <-- 现象
   111 |   1    | 00000008 | 0000000c  |       3        |    2    | 002081b3 | 00000004 | 00508113
   121 |   1    | 0000000c | 00000010  |       4        |    3    | 40118233 | 00000008 | 002081b3
   131 |   1    | 00000010 | 00000014  |       5        |    4    | 00209293 | 0000000c | 40118233
```

- 与你的观察完全一致:100 ns 处 `(00000000, 00000000)`,之后一一对应。
- 注意 `ada_reg` 一列:**从第 11 ns 起就已经是 1**(复位期间也是 1),说明 ROM 内部地址寄存器在复位期间照常工作,而且指向的是 word 1。

---

## 3. 根因链

### 3.1 为什么复位期间 ROM 地址端口是 word 1

```
pc  = 0(复位值)
next_pc = pc + 4 = 4
inst_sram_addr = next_pc = 4
inst_rom.addr = inst_sram_addr[11:2] = 4>>2 = 1     <-- word 1
```

**`addr` 接的是 `next_pc`,不是 `pc`**,而 `next_pc` 在复位期间照样是 `pc + 4`。所以 ROM 从复位第一天起要读的就是 word 1;word 0 从来没有出现在地址端口上。

### 3.2 为什么 ROM 会在复位期间就把它锁进去

`GTP_DRM36K_E1.v` 第 711–725 行:

```verilog
always @(posedge CLKA) begin
    if (CEA) begin
        if (ADDRA_HOLD == 1'b0) begin
            if (CSA == CSA_MASK) begin
                ada_reg <= ADDRA;          // ★ 没有 rst 判断!
            end
            csa_reg <= (CSA == CSA_MASK);
        end
        ...
    end
end
```

- `ada_reg` 声明时给了初值 `16'b0`(第 236 行),但**块里没有任何复位分支**;
- 给 DRM 的 `.RSTA(rst)` 只用来复位**输出**(见下),不复位地址寄存器。

所以复位期间它每个沿都在跟 `ADDRA`,复位结束时停在 **word 1**。

### 3.3 为什么 100 ns 那拍 `rd_data` 是 0

输出寄存器受 `rsta_int` 控制(`GTP_DRM36K_E1.v` 第 1143–1149 行 / 1315–1321 行):

```verilog
always @(negedge CLKA_active or posedge rsta_int) begin
    if (rsta_int)  a_out = rsta_val_int;        // = RSTA_VAL = 0
    else if (read_en_a) a_out[width_a-1:0] = mem_read_a(ada_reg[14:0]);
end
```

而 `rsta_int` 是 `RSTA` **打了一拍**之后的结果(第 1433–1440 行):

```verilog
always @(posedge CLKA_for_or) rsta_grsn_d <= RSTA;
assign rsta_int = rsta_grsn_d;                  // RST_TYPE = "SYNC"
```

时间线(时钟 10 ns,上升沿在 10/20/…/100/110):

| 时刻 | `RSTA` | `rsta_int` | `ada_reg` | `a_out`(= `rd_data`) |
| :-- | :-- | :-- | :-- | :-- |
| 90 ns | 1 | 1 | 1 | 0(被强制) |
| 95 ns | **0**(复位释放) | 1(还没跟上) | 1 | 0(保持) |
| **100 ns 沿** | 0 | 0 | **← 1** | 沿后 → `mem[1]` |
| 100 ns 时刻的 IF/ID | — | — | — | **锁到「沿前」的 0** → `(0, 0)` |

`if_id_inst <= inst` 采的是**沿之前**的值(0),所以第一次写 IF/ID 就是 `(0, 0)`。而 110 ns 那一沿锁到的 `(4, mem[1])` 已经是对的了。

### 3.4 为什么"之后都一一对应"

稳态不变式:**`ada_reg == pc/4`**。

- 该沿 `ada_reg <= ADDRA = next_pc[11:2] = (pc+4)>>2 = pc/4 + 1`;
- 同一沿 `pc <= pc + 4`。

所以每个沿过后两者同时 +1,始终锁步。于是 `rd_data = mem[pc/4]` 恒等于**当前 PC 处的那条指令**,配对永远是对的。

唯一没救的是 `pc = 0` 那一拍:要拿到 `(0, mem[0])`,需要 ROM 在「`pc = 0` 的那个周期里」把 `mem[0]` 打出来。而那个周期(95–100 ns)ROM 的输出还被 `rsta_int` 强制为 0 —— 于是这一对**从来没有机会形成**,`mem[0] = 00A00093` 就此丢失。

---

## 4. 修复

### 4.1 思路

> ROM 的复位是**同步**的,内部又把 `rst` 打了一拍,所以 `rst` 撤销后 ROM 还需要**一个完整时钟**才能给出有效数据。
> 那就让 **CPU 侧的复位(管 PC 和 IF/ID)比 ROM 侧的复位晚一拍释放** —— 这多出的一个周期里,ROM 地址端口停在复位向量(word 0),它的输出正好把 `mem[0]` 准备好。

### 4.2 代码(在 `topcpu.v` 上改动很小)

```verilog
    //---- 新增:CPU 侧复位比 resetn 晚一拍释放 ----
    reg resetn_1;
    always @(posedge clk) resetn_1 <= resetn;
    wire pc_hold = !resetn_1;          // 复位中 + 复位释放后一拍,都保持

    inst_rom u_inst_rom(
        .addr(inst_sram_addr[11:2]),
        .clk(clk),
        .rst(!resetn),                 // ROM 用原始 resetn(早一拍释放)
        .rd_data(inst)
    );

    wire [31:0] next_pc = pc + 32'd4;
    wire [31:0] pc_next = pc_hold ? pc : next_pc;    // ★ 复位期间 next_pc = pc
    assign      inst_sram_addr = pc_next;

    always @(posedge clk) begin
        if (!resetn)       pc <= 32'h0000_0000;
        else if (!pc_hold) pc <= next_pc;            // ★ 多保持一拍
    end

    always @(posedge clk) begin
        if (!resetn_1) begin                         // ★ 用 resetn_1,首拍即为有效取指
            if_id_inst <= 0; if_id_pc <= 0; if_id_valid <= 1'b0;
        end else begin
            if_id_inst <= inst; if_id_pc <= pc; if_id_valid <= 1'b1;
        end
    end
```

### 4.3 实测结果

```
  time | pc      | rom_inst  | if_id_pc | if_id_inst
-------+---------+-----------+----------+-----------
   101 | 00000000 | 00a00093 | 00000000 | 00000000   <-- 1 个气泡(IF/ID 还没写)
   111 | 00000004 | 00508113 | 00000000 | 00a00093   <-- ✅ 第 0 条指令,配对正确
   121 | 00000008 | 002081b3 | 00000004 | 00508113
   131 | 0000000c | 40118233 | 00000008 | 002081b3
   141 | 00000010 | 00209293 | 0000000c | 40118233
```

- **代价:复位后 1 个气泡**(与"老方案 + `run_d1`"同价),但**指令一条不丢**。
- 顺带得到的好处:复位期间 ROM 地址 = `pc` = 复位向量,`ada_reg` 也被从有效的 `next_pc` 路径灌成 0,**不再依赖 IP 的 `RST_VAL` 功能**(你的 `.idf` 里 `RST_VAL_EN = false`,本来就不能指望)。

### 4.4 气泡不能只靠"全零"表示 —— `valid` 必须随指令流动

这是这个 bug 的**第二半**,同样要处理:

复位释放后那一拍,IF/ID 里是 `(if_id_pc = 0, if_id_inst = 0)`。如果 `if_id_valid` 被无条件置 1(你现在的写法就是 `if_id_valid <= 1'b1;`),下游流水线会把它当成一条**有效指令**执行。三个问题:

**① `0x0000_0000` 不是 NOP。**
RV32I 里 `opcode = 7'b0000000` 根本没有定义 → 它是**非法指令**;RISC-V 规范还特意把全零编码保留作非法指令,用来捕获"跳到未映射内存"。真正的 NOP 是 `addi x0, x0, 0` = **`0x0000_0013`**。
你自己的 `idu.v` 可以验证:`opcode = 7'b0000000` 不会命中任何一个 `inst_*`,所以**所有控制位都会落到默认值**。默认值若不是全 0(比如 `alu_op`、`rf_we`、`mem_write` 的默认),这条假指令就会真的改状态。

**② `if_id_pc = 0` 是个合法地址,而且正是复位向量。**
波形上、异常上报里,这个气泡和"pc = 0 处那条真指令"**长得一模一样**,根本分不出来。真出问题时极难定位。

**③ 占了一个流水槽。**
即使它什么也不做,它也会流到 EXE/MEM/WB,影响 `load-use` 判定、旁路优先级、以及将来异常优先级(最老指令优先)的排序。

**关键:IF 级是"制造" valid 的地方,不是"继承"来的**

IF 是最前一级,没有上游 valid 可以传下来 —— 它必须自己回答一个问题:

> **这一拍我交给 ID 的 `{pc, inst}`,可不可信?**

把这个问题的答案写成一个组合条件,就是 `if_id_valid` 的 D 端。气泡一共有**三个来源**,分别对应三种不同的处理:

| 气泡来源 | 条件 | 对 `if_id_valid` 的处理 |
| :-- | :-- | :-- |
| 复位期间 / ROM 输出还没有效 | `!resetn_1` | **清 0** |
| 分支·跳转·异常造成的冲刷 | `flush_req` | **清 0** |
| 下游不接受(阻塞) | `stall_req` | **保持原值**(不是清 0!) |

⚠️ **`stall` 是"保持",`flush` 是"清 0"——这两个千万别混。** stall 时 IF/ID 整组不动,valid 跟着不动;flush 时指令作废,valid 才清 0。

标准写法:

```verilog
// ---- IF 级:唯一权威来源 ----
wire if_id_write = resetn_1 & ~stall_req;   // 何时更新 IF/ID
wire fetch_valid = resetn_1 & ~flush_req;   // 这一拍取到的东西可不可信

always @(posedge clk) begin
    if (!resetn_1) begin                    // ① 复位:清 0
        if_id_pc    <= 32'hFFFF_FFFF;       //    填一个不可能成为 PC 的值,便于看波形
        if_id_inst  <= 32'h0000_0013;       //    真 NOP(addi x0,x0,0),只是为了好读
        if_id_valid <= 1'b0;
    end
    else if (if_id_write) begin             // ② stall 时不进这里 = 保持
        if_id_pc    <= pc_r;
        if_id_inst  <= inst_sram_rdata;
        if_id_valid <= fetch_valid;         // ③ flush 时 = 0
    end
end
```

注意:一旦用了 `valid`,**指令字段填什么就无关紧要了**(上面填 `NOP` / `FFFF_FFFF` 纯粹是为了波形好认)。判断权全部在 `valid` 手上。

**下游:valid 随级打拍 + 与每个副作用相与**

```verilog
always @(posedge clk) begin                 // ID → EXE
    if (!resetn)          id_ex_valid  <= 1'b0;
    else if (!ex_stall)   id_ex_valid  <= if_id_valid;
end

assign rf_we     = rf_we_dec     & if_id_valid;   // 在 ID 阶段就生效的,乘当级 valid
assign mem_write = mem_write_dec & ex_mem_valid;  // 在 MEM 阶段生效的,乘 MEM 级 valid
assign br_taken  = br_taken_dec  & ex_mem_valid;
```

> 第 3 条是最容易漏的一条。组合派生出来的 `rf_we` / `mem_write` / `br_taken` 只要漏了一个 `& valid`,一条被冲刷或被标记为气泡的指令就能把寄存器堆或数据 RAM 写脏。

**关于"能不能直接 `if_id_valid <= valid`"**

很多工程里会有一个全局的 `valid`(通常就是 `resetn` 打一拍,和你 `topcpu.v` 里注释掉的那段一模一样)。**在只有复位这一种气泡来源、且已经用 `resetn_1` 压住写使能的前提下,`if_id_valid <= valid` 与上面的写法是等价的** —— 因为那个 `valid` 就是 `resetn` 打一拍,和 `resetn_1` 是同一个信号。

**但它一旦加入冲刷就不够了**:那个 `valid` 完全不理会 `flush_req`,分支跳转时会把已经作废的指令标成有效。所以**建议不要用那种"全域 valid"**,而是老老实实按上面把三个来源写清楚。

**白送的一个检查**:既然 `inst_*` 已经是全集判定,顺手加一条

```verilog
wire inst_illegal = ~(inst_add | inst_sub | ... | inst_ecall | inst_ebreak);
```

将来接异常时直接用,还能立刻发现"跑到 ROM 空白区"这类问题。

**两种方案在这件事上的差别:**

| | 复位释放后第一拍 | 有没有"假有效"气泡 |
| :-- | :-- | :-- |
| 方案二 + 修复 | `valid = 0`(被 `resetn_1` 压住) | 有 1 个,但**已被正确标为无效** |
| 方案一-B | `valid = 1`,`inst = mem[0]`(真指令) | **没有** |

> 这也说明 `valid` 这条约定是**两套方案都必须做的**,不是方案二专属的补丁。你在 `topcpu.v` 里现在就把 `if_id_valid` 的语义定好,后面 `idu`/`exu`/`memu`/`wbu` 加控制信号时直接照着相与即可,不会返工。

> 小技巧(可选):复位期间把 `if_id_pc` 置成 `32'hFFFF_FFFF` 这种**不可能成为 PC** 的值,波形上一眼就能认出是气泡。但这只是调试便利,**不能替代 `valid`**。

### 4.5 复位后这**一个气泡**到底怎么"处理"

先分清两件完全不同的事,它们的严重程度差一个数量级:

| | 本质 | 后果 | 要不要"处理" |
| :-- | :-- | :-- | :-- |
| **丢指令** | `mem[0]` 被永久跳过,程序从 `mem[1]` 开始跑 | **程序语义错了** | ❌ 必须修(已由 `resetn_1` + `pc_hold` 修好) |
| **气泡** | 一个 `valid = 0` 的空槽 | 只多 1 拍启动延迟,**没有任何语义影响** | ✅ 标成无效即可,不需要"消除" |

**① 气泡不需要任何"复位专用"的处理逻辑。**

它和下面这两种东西**是同一种**:stall 时插进来的气泡、分支冲刷产生的气泡。流水线本来就必须支持它们(否则 `load-use`、分支都做不了)。所以"处理"它就三件事,而且**都是 4.4 里已经写过的通用机制**:

1. 标记 `if_id_valid = 0`(三个来源之一:**复位**);
2. 让它无害:所有副作用与当级 valid 相与;
3. **不要为它写任何"复位后第一拍特殊处理"的代码** —— 多余,而且很容易引入新 bug。

**② 关键:气泡不会让后面的指令错位。**

这是它和"丢指令"的本质区别。气泡只是**占一个槽**,后面的指令照原来的顺序一条条流过去,谁也不受影响。而丢指令是**整个程序从第二条开始跑**,后面全错。

打个比方:气泡 = 队列里多了一个空位;丢指令 = 队列少了一个人,所有人往前挪一号。

**③ 方案二里这个气泡在物理上消除不掉。**

ROM 的同步复位是"内部把 `rst` 打一拍",`rst` 撤销后**必须过一个完整时钟**才可能有数据。这段时间里 IF/ID 拿不到任何可信的东西 → 无论如何都是 1 拍空转。想做到 0 气泡,只有换**方案一-B**(指令不寄存,ID 直接消费 ROM 输出),实测首条指令 100 ns 到 ID,见 6.1。

**④ 代价量化。**

| | 首条有效指令进 ID | 稳态吞吐率 |
| :-- | :-- | :-- |
| 方案二 + 修复 | 110 ns(复位释放后 1 拍) | 每拍 1 条(不变) |
| 方案一-B | 100 ns(复位释放后立即) | 每拍 1 条 |

5 级流水在复位后本来就要 4 拍才能填满,**多这 1 拍并不改变吞吐率**,只影响启动延迟。对绝大多数场景可以忽略。

**⑤ 三种写法的对照(只有前两种是对的):**

| 写法 | IF/ID 里放什么 | 下游靠什么认出是气泡 | 判定 |
| :-- | :-- | :-- | :-- |
| A. 复位期间**不写**(保持) | 保持复位值(0) | `if_id_valid = 0` | ✅ 本工程方案二采用 |
| B. 写进去,但 `valid = 0` | pc/inst 填任意值 | `if_id_valid = 0` | ✅ 等效 |
| C. 写进去且 `valid = 1` | 全 0(或 NOP) | **认不出来** | ❌ 错误(4.4) |

> **唯一要避免的就是 C。** 另外,**别用 `if_id_inst == 0` 去判断气泡** —— 那是"靠数据认气泡",一旦 ROM 里真的有一处全 0 就误判;只认 `valid`。

**⑥ 一个省事的说法**

如果你在 tb 里就是"等 `if_id_valid` 拉高才开始算有效指令",那这个气泡你**完全不用管** —— 它自己会被过滤掉。你现在 tb 里那个"100 ns 应该有 `(0, 00A00093)`"的预期,改成"复位释放后第一个 `if_id_valid = 1` 的拍,应当是 `(0, 00A00093)`"就对了。

### 4.6 三道闸:不让气泡写坏状态

担心是合理的:**只要 `if_id_valid` 被误标成 1,译码器就可能吐出 `rf_we = 1` / `mem_write = 1`,把寄存器堆或数据 RAM 写脏。** 那怎么办?

不要只靠一道闸。**三道一起上,任何一道失效都不会写坏状态** —— 流水线里气泡的来源以后只会越来越多(分支、load-time、异常、中断…),单点防护迟早会漏。

**第 1 道(源头):气泡标 `valid = 0`** —— 见 4.4 的三个来源。

**第 2 道(数据通路):译码器对"未匹配的编码"必须输出确定的全 0。**

```verilog
// 先赋默认值,再按指令改写 —— 纯组合,不推锁存器
always @(*) begin
    rf_we_dec     = 1'b0;      // ← 默认全 0 是这条闸的全部
    mem_write_dec = 1'b0;
    mem_read_dec  = 1'b0;
    br_taken_dec  = 1'b0;
    alu_src_dec   = 2'b00;
    alu_op_dec    = 4'b0000;
    wb_sel_dec    = 2'b00;
    case (opcode)
        7'b0110011: begin rf_we_dec = 1'b1; alu_src_dec = 2'b00; wb_sel_dec = 2'b00; end // R
        7'b0010011: begin rf_we_dec = 1'b1; alu_src_dec = 2'b01; wb_sel_dec = 2'b00; end // I
        7'b0000011: begin rf_we_dec = 1'b1; mem_read_dec = 1'b1; wb_sel_dec = 2'b01; end // load
        7'b0100011: begin mem_write_dec = 1'b1; alu_src_dec = 2'b01;               end // store
        7'b1100011: begin br_taken_dec = 1'b1;                                     end // branch
        7'b1101111: begin rf_we_dec = 1'b1; wb_sel_dec = 2'b10;                    end // jal
        7'b1100111: begin rf_we_dec = 1'b1; alu_src_dec = 2'b01; wb_sel_dec = 2'b10; end // jalr
        default:    ;          // ★ 全 0 —— 任何非法编码自动"什么都不做"
    endcase
end
```

⚠️ **反例**:如果写成"没有 default 的 `case`"或者"用 `assign` 拼但没有兜底",综合出来可能是**锁存器** —— 使能会**保持上一拍的值**,那才是真正的灾难(一条气泡能把上一拍的 `mem_write=1` 带下去)。**开头统一赋默认值**是唯一稳妥的写法。

**第 3 道(出口):使能与"当级 valid"相与。**

```verilog
assign rf_we     = rf_we_dec     & id_ex_valid;    // 在哪一级生效,就乘哪一级的 valid
assign mem_write = mem_write_dec & ex_mem_valid;
assign br_taken  = br_taken_dec  & ex_mem_valid;
```

> **建议**:把寄存器堆写和内存写**统一放到 WB 级提交**,只在那一个地方乘 `mem_wb_valid`。这样闸门只有一处,不用每级都记着乘 —— 之后加异常/中断时也只改这一个点。

**外加一条断言 —— 它能自动抓住"气泡被误标有效"这类 bug**

```verilog
wire inst_illegal = ~(inst_add | inst_sub | ... | inst_ecall | inst_ebreak);  // idu 里已有全集判定,白送

// 仿真期检查:有效指令不应该是非法编码
// synopsys translate_off
always @(posedge clk) begin
    if (if_id_valid && inst_illegal)
        $display("ERROR @%0t: if_id_valid=1 但指令非法! pc=%h inst=%h <- 气泡被误标成有效?",
                 $time, if_id_pc, if_id_inst);
    if (if_id_valid && (if_id_pc == 32'hFFFF_FFFF))
        $display("ERROR @%0t: 有效指令却带着哨兵 PC <- valid 逻辑写错了", $time);
end
// synopsys translate_on
```

**这两条断言是专门为本次这个 bug 量身定做的**:
- 第一条:气泡被标成有效时,它的编码 `0x0000_0000` 是非法指令 → 立刻报错;
- 第二条:配合 4.4 里"复位期间把 `if_id_pc` 置成 `FFFF_FFFF`"的哨兵值,任何一次 `valid` 逻辑改错都会被抓住。

比"看波形猜"可靠得多,而且以后每次改冲刷/阻塞逻辑,它都会替你回归。

### 4.7 针对你当前 `topcpu_instrom.v` 的最小改动清单

**你已经做对的(第一条指令已经拿回来了):**

```verilog
reg vaild;
always@(posedge clk) vaild <= resetn;                    // = 4.2 里的 resetn_1
assign inst_sram_addr = vaild ? next_pc : pc;            // = pc_hold 门控
always@(posedge clk) begin
    if(!resetn)      pc <= 32'h00000000;
    else if(vaild)   pc <= next_pc;                       // 复位释放后再多保持一拍
end
```

这一套就是 4.2 的 `pc_hold` 方案,**`mem[0]` 不会再丢**。

**还差一处(实测验证):**

```diff
  always@(posedge clk)begin
-     if(!resetn)begin              // ← if_id 块用的是 resetn
+     if(!vaild)begin               // ★ 改成 vaild,一行
          if_id_inst  <= 32'h00000000;
          if_id_pc    <= 32'h00000000;
          if_id_valid <= 1'b0;
      end
      else begin
          if_id_inst  <= inst;
          if_id_pc    <= pc;
          if_id_valid <= 1'b1;
      end
  end
```

**实测对照**(同一个激励、同一个官方 IP 模型,两组同时跑):

| 时刻 | 当前版 `valid / pc / inst` | 改一处后 `valid / pc / inst` |
| :-- | :-- | :-- |
| 101 ns | **1** / `00000000` / `00000000` ← **假有效气泡** | **0** / `00000000` / `00000000` |
| 111 ns | 1 / `00000000` / `00a00093` | 1 / `00000000` / `00a00093` |
| 121 ns | 1 / `00000004` / `00508113` | 1 / `00000004` / `00508113` |

断言 `if_id_valid && (if_id_inst == 0)` 的报错次数:**当前版 1 次,改一处 0 次**。

**为什么一行就够?**
你的 `vaild` 就是 `resetn` 打一拍(等价于 4.2 的 `resetn_1`)。IF/ID 用它当复位,含义就是"**复位释放那一拍不写**" —— 而那一拍 ROM 输出还停在 0,本来就不该写。下一拍才写,正好拿到 `(0, mem[0])`。

**剩下两处建议(4.6 的第 2、3 道闸),等写控制译码时一起做:**

1. 译码器**开头统一赋默认值**(default 全 0);
2. `rf_we` / `mem_write` **与当级 valid 相与**;
3. 加上那条 `inst_illegal` 断言 —— 以后每次改冲刷/阻塞都会替你回归。

> 小建议:`vaild` 这个名字其实名不副实 —— 它是"复位释放后再延一拍",不是"有效"。改成 `rst_n_d1` 或 `start` 会更不容易误读。

---

## 5. 三条硬约束(缺一条都会丢指令)

| # | 约束 | 违反后果 |
| :-- | :-- | :-- |
| 1 | ROM 的 `addr` 必须由**组合路径**驱动,中间不夹寄存器 | 白丢一拍 |
| 2 | **复位期间地址端口 = 复位向量**(`next_pc = pc`),且要保持到 ROM 的第一个有效沿之后 | ROM 内部地址寄存器从复位起就指向 word 1 → `mem[0]` 永久跳过 |
| 3 | **CPU 侧复位比 ROM 侧复位晚一拍释放** | 复位释放那拍 ROM 输出还是 0,IF/ID 锁到 `(0, 0)` → 仍是丢一条指令 |

---

## 6. 对照实验:只加门控为什么不够

把方案退化成"只在复位期间门控"(即 `pc_hold = !resetn`,PC 不多保持一拍),其余不变:

```
  time | pc      | rom_inst  | if_id_pc | if_id_inst
-------+---------+-----------+----------+-----------
   101 | 00000004 | 00508113 | 00000000 | 00000000   <-- pc 已经跑到 4 了
   111 | 00000008 | 002081b3 | 00000004 | 00508113
   121 | 0000000c | 40118233 | 00000008 | 002081b3
```

`(0, mem[0])` 仍然缺失。原因:95 ns 复位一释放,`pc_hold` 立刻变 0,`next_pc` 马上变成 4;而 ROM 要等到 100 ns 那个沿才锁地址 —— 它锁到的是**已经变成 4 的地址**(word 1)。

**结论:门控必须多保持一拍**(等价于 CPU 侧复位晚一拍释放),否则 ROM 的"同步复位 + 内部再打一拍"这段延迟没人替它兜住。

> 这也修正了之前用简化 ROM 模型得到的"加一行门控就能 0 气泡"的结论 —— 那个模型没有模拟 IP 的**同步复位打拍**行为,过于乐观。

### 6.1 三种接法在真 IP 下的实测对照

既然 `addr` 接谁决定了复位行为,我把三种接法都在**同一个官方模型、同一激励**下跑了一遍:

| 接法 | 复位后气泡 | 首条指令进 ID | 额外硬件 | 判定 |
| :-- | :-- | :-- | :-- | :-- |
| 方案一-A `addr=PC`,指令也寄存 | 1 | — | 无 | ✅ 但整机 6 级 |
| **方案一-B `addr=PC`,指令直通** | **0** | **~100 ns** | **无** | ✅ **最优(复位维度)** |
| 方案二 `addr=nextPC` + 门控 + 复位晚一拍 | 1 | ~110 ns | +1 个 FF | ✅ 可用 |
| 方案二 `addr=nextPC` + 仅门控 | — | — | 无 | ❌ 丢 `mem[0]` |
| 方案二 `addr=nextPC`(当前实现) | — | — | 无 | ❌ 丢 `mem[0]`(你观察到的现象) |

**方案一-B 的真 IP 实测波形**(`addr = pc_r`,指令不寄存,`debug_inst` 就是 ROM 输出):

```
  time | pc_r    | if_id_pc | valid | debug_inst
-------+---------+----------+-------+-----------
    91 | 00000000 | 00000000 |   0   | 00000000   <-- 复位中,标记 invalid
   101 | 00000004 | 00000000 |   1   | 00a00093   <-- ✅ (0, 00A00093) 配对正确
   111 | 00000008 | 00000004 |   1   | 00508113
   121 | 0000000c | 00000008 |   1   | 002081b3
   131 | 00000010 | 0000000c |   1   | 40118233
```

**为什么方案一-B 不需要任何技巧?** 因为它的地址端口本来就是 `pc_r`,而 `pc_r` 的复位值就是确定的 0 —— 整个复位期间 `ada_reg = 0`,复位一释放、`rsta_int` 一解除,输出立刻就是 `mem[0]`;而 `if_id_pc <= pc_r` 也正好落后一拍,和 ROM 输出天然配对。**"门控"和"复位晚一拍"这两件事它都不需要。**

**那为什么还选方案二?** 唯一理由还是关键路径:

| | 方案一-B | 方案二 + 修复 |
| :-- | :-- | :-- |
| ROM 同步读延迟落在 | **ID 级**(tCO + 阵列 + 走线 + 译码 + RF 读) | **IF 级**(与算 nextPC / 分支 mux 并行) |
| 复位代价 | 0 气泡,无额外逻辑 | 1 气泡 + 1 个 FF |
| 阻塞处理 | 必须冻结 `pc_r`(否则 `rd_data` 跟着 PC 跑) | 冻结 `if_id` 即可 |

**两者都是 5 级、吞吐率相同**,差别只在"复位填充深度"与"关键路径分布"。务实做法:先按方案二把主干跑通(接口不用动),综合跑静态时序分析后再决定要不要切方案一-B —— 切换改动很小(`inst_sram_addr` 由 `pc_next` 换回 `pc_r`;`if_id_inst` 由寄存器改为连线;顺带省掉那个 FF)。

> 参考实现:本次实测用的方案一-B 模块在 `.workbuddy/sim_rom/topcpu_plan1b.v`,日志 `sim_1b.log`。

---

## 7. 顺带更正:IP 固化的初始化数据其实是对的

之前一份文档(`doc/inst_rom仿真与初始化数据核对.md` 第 5 节)得出过"IP 内固化数据与 `rom_test.dat` 不一致(地址 0~5 不同)、IP 忘了重新生成"的结论。**那个结论是错的**,原因是解码口径错了:把 288 bit 里的 36 bit 槽直接当成 32 bit 字读,而没有按 DRM 模型的实际读取规则抽取字节。

`GTP_DRM36K_E1.v` 的真实读取规则:

```verilog
mem[cnt] = INIT_xx[cnt*9 +: 9];                            // cnt = 0..31
// 32bit 字 = { mem[4W+3][7:0], mem[4W+2][7:0], mem[4W+1][7:0], mem[4W][7:0] }
```

按这个规则重新解码 `inst_rom_init_param.v` 的 128 个 `INIT_xx_0_0`,得到 1024 个字,与 `rom_test.dat` 逐字比对:

```
 addr | IP 固化   | rom_test.dat | 判定
------+-----------+--------------+-----
    0 | 0x00A00093 | 0x00A00093   | OK
    1 | 0x00508113 | 0x00508113   | OK
    2 | 0x002081B3 | 0x002081B3   | OK
    ...
全部 1024 个地址中,不一致 0 个
```

出错口径对照(地址 0):

| 口径 | 结果 |
| :-- | :-- |
| 低 36 bit 槽直接截成 32 bit | `0x02800093` ← 旧文档用的(错) |
| 低 32 bit 直接截取 | `0x02800093`(同一个错) |
| **按 `mem_read_a` 规则解码** | **`0x00A00093`** ← DUT 实际读出值 |
| `rom_test.dat[0]` | `0x00A00093` ✓ |

**所以 ROM 里烧的就是当前程序,不需要重新生成 IP。** 本次仿真里 `if_id_inst` 依次得到 `00A00093 / 00508113 / 002081B3 / 40118233 / 00209293 / 00328333 / 0000006F / 1 / 2 / 3 …`,与 `rom_test.dat` 完全一致,也从行为上再次印证了这一点。

---

## 8. 相关文件

```
source/tb_topcpu.v                                ← 你的激励(未改动)
myriscv/topcpu.v                                  ← 你的顶层(未改动,修复代码见 4.2)
ipcore/inst_rom/rtl/inst_rom_init_param.v         ← IP 固化的初始化数据
C:\pango\PDS_2022.2-SP6.4\arch\vendor\pango\verilog\simulation\GTP_DRM36K_E1.v
                                                  ← 官方 DRM 行为模型(根因判定依据)

本次复现与验证(放在 .workbuddy/sim_rom/,不影响工程):
  tb_probe.v          ← 复现你的现象(含 DRM 内部信号探针)
  tb_probe_fix.v + topcpu_fix.v    ← 方案二 + 门控 + 复位晚一拍,验证通过(1 气泡)
  tb_probe_gate.v + topcpu_gate.v  ← 方案二 + 仅门控的对照版,仍丢指令
  tb_probe_plan1b.v + topcpu_plan1b.v ← 方案一-B(addr=PC,指令直通),0 气泡
  sim.log / sim_fix.log / sim_gate.log / sim_1b.log   ← 四组运行日志
  decode_rom.py + decode_report.txt      ← 初始化数据逐字比对
  src/                ← 为跑 iverilog 而打的本地副本(见下)
```

> ⚠️ `src/` 里是**改动过的副本**,只为绕过 iverilog 的两处限制,工程原文件未动:
> 1. `{{8*DATA_LOOP_NUM}{1'b1}}` 这种不定宽复制表达式 iverilog 不接受 → 换成常量;
> 2. iverilog 不执行"无敏感信号"的 `always @(*)`(CS 生成块),会让 CS 变 X、地址寄存器永不加载 → 加了 `initial` 显式赋初值。**Modelsim 没有这个问题。**
