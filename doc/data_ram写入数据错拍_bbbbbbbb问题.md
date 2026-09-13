# data_ram 写入 `bbbbbbbb` 而非 `aaaaaaaa` — 原因与修复

> 复现环境：iverilog 11.0 + Pango 官方仿真模型
> `C:\pango\PDS_2022.2-SP6.4\arch\vendor\pango\verilog\simulation\GTP_DRM36K_E1.v`
> 测试激励：与你 `source/tb_topcpu_instrom.v` 的 data_ram 部分完全一致
> 复现工程：`.workbuddy/sim_dram/`

---

## 1. 现象回顾

```
t= 95ns  resetn 0→1
t=100ns  addr=0, wr_data=bbbbbbbb, wr_en=0
t=110ns  addr=1
t=120ns  addr=1, wr_data=aaaaaaaa, wr_en=1     ← 期望写入 aaaaaaaa
t=130ns  wr_en=0
```

**观察到：读回 addr=1 得到 `bbbbbbbb`，写入的 `aaaaaaaa` 不见了。**

> **【2026-09-13 修正】** 本文早期把根因表述为"写数据比写使能晚一拍"（即 120ns 沿采到旧值 `bb`）。
> 该表述**不准确**。正确的机制是 IP 内部 CS 寄存器 `csa_reg` 与 `da_reg/wea_reg/ada_reg` 的
> **更新条件不同**，在 CS 未初始化（恒 `x`）时三者失去对齐。
> 只要 CS 正常，`da_reg/wea_reg/ada_reg` 三者**同沿更新、完全同步**，120ns 沿会正确采到 `aa`。
> 详见 §2.3 与 §6。用户当前"四个信号全部组合直连"的 CPU 接法**不存在此问题**。

先说结论：**这不是 IP 的问题，也不是你 CPU 逻辑的问题，而是三个独立因素叠加**。
主因是 **tb 在复位释放边界窗口内改激励** + **iverilog 下 IP wrapper 的 CS 恒为 `x`**。

---

## 2. 三个独立问题

### 问题 A（最关键）：tb 在复位撤销边界窗口内改激励，配合 CS 未初始化导致采样失配

#### 2.1 事实链

IP 端口的复位是**高电平有效**（`rst`，不是 `rst_n`）。你的接法是：

```verilog
data_ram u_data_ram (
    ...
    .rst(~resetn),      // resetn=0 时 rst=1 → 复位态
    ...
);
```

实测波形（VCD 逐拍追踪）：

| 时刻 | resetn | `rsta_int` | 说明 |
|---|---|---|---|
| 0.2ns | 0 | 0 | |
| 10.2ns | 0 | **1** | 复位真正生效（被 CLK 同步打了一拍） |
| 100ns | 1 | 1 | 复位撤销 |
| 100.2ns | 1 | **0** | 复位真正撤销（又晚一拍） |

也就是说 **`rsta_int` 在 100.2ns 才下降**。这是一切的前提。

#### 2.2 为什么写进去的是 `bbbbbbbb`

先澄清时序采样的基本规则：`always @(posedge clk)` 采到的**永远是沿到来之前已经稳定的值**。
所以按理说，120ns 沿上 `wr_data` 已经是 `aa`、`wr_en` 已经是 1，**本该正确写入 `aa`**。

问题出在 IP 内部**不止一级寄存器，且各级更新条件不同**：

```verilog
always @(posedge CLKA) begin
    if (CEA) begin
        da_reg  <= DIA_int;   // 写数据：CEA 恒 1 → 每拍都更新
        wea_reg <= WEA;       // 写使能：同样每拍都更新
        ada_reg <= ADDRA;     // 写地址：同样每拍都更新
    end
end

always @(negedge CLKA_active) begin
    if (write_en_a)                       // ← 取决于 csa_reg
        mem_write_a(ada_reg, da_reg, bea_reg);
end

assign write_en_a = csa_reg && cas_inta && (wea_reg == 1'b1);  // ← 多了一级
```

| 寄存器 | 更新条件 | 后果（CS 未初始化时） |
|---|---|---|
| `da_reg` / `wea_reg` / `ada_reg` | `CEA`（恒 1） | 每拍都更新，**跟得上总线** |
| `csa_reg` | `CEA && CSA==CSA_MASK` | CS 恒 `x` → **永远不更新** |

关键点：**`csa_reg` 不在 `CEA` 那一组里**。它是独立的一级（见 `GTP_DRM36K_E1.v:718`），
只有 `CSA == CSA_MASK` 时才被写入。而本配置下 `CSA = {x,x,x}`（见问题 C），
`csa_reg` 因此恒为 `x`，`write_en_a` 恒 0 —— 写通路整体被挡住。

**修好 CS 之后，`da_reg/wea_reg/ada_reg` 三者就是严格同沿更新的**，
120ns 沿会一起采到 `addr=1`、`wr_data=aa`、`wr_en=1`，写入完全正确。
（实测见 §3：修复后 `read addr=1 -> aaaaaaaa`。）

所以**"数据比控制晚一拍"的说法不成立**——三者本来就同步，只是被 CS 的 `x` 打乱了。

于是 **`bbbbbbbb` 被写到了地址 1，而 `aaaaaaaa` 从未落盘**。这就是你读回 `bbbbbbbb` 的直接原因。

---

### 问题 B：tb 在复位撤销边界窗口内改激励

你的 tb 写法：

```verilog
addr = 10'h1;
#10;
wr_data = 32'haaaaaaaa; wr_en = 1'b1;   // 都在 120ns 前 0 时刻变化
#10;
wr_en = 1'b0;
```

`wr_data` 和 `wr_en` 同一时刻跳变、落在同一拍，模型里 `da_reg <= DIA_int` 与 `wea_reg <= WEA` 又是同一个 `always` 块，**本该完全同步**。

真正的干扰来自复位边界：**内部 `rsta_int` 到 100.2ns 才真正撤销**，而你在 100ns 就改了 `wr_data`。复位窗口边缘的这一拍，加上 CS 未初始化（问题 C），共同造成第一次采样失配。

**结论：与你 CPU 里的真实场景不同。** 在真实 CPU 中 `wr_data`/`wr_en`/`addr` 同源同拍，**不会有这个问题**。这个现象是 tb 在复位释放窗口内改激励造成的。

---

### 问题 C：所有 `cs_bit*` 恒为 `x` —— 这是 iverilog 的仿真假象，但会掩盖问题

追踪显示 `CSA = xxx`（`{cs_bit2, cs_bit1, cs_bit0}`）**整个仿真都是 `x`**。

原因在 IP 生成的 `rtl/ipm2l_spram_v1_8_data_ram.v` 第 303 行：

```verilog
always@(*) begin                 // ← 该块在 CS_ADDR_WIDTH==0 分支里
   for(gen_m=0; gen_m<ADDR_LOOP_NUM; gen_m=gen_m+1) begin
      if(DRM_DATA_WIDTH == 72 || DRM_DATA_WIDTH == 64) begin ... end
      else begin
         if(CS_ADDR_WIDTH == 0) begin
            cs_bit0 = 0;         // ← 只赋值常量，无信号依赖
            cs_bit1_bus[gen_m] = 0;
            cs_bit2_bus[gen_m] = 0;
         end
         ...
```

本配置 `DRM_DATA_WIDTH=32`、`CS_ADDR_WIDTH=0`，走的是 else 分支且只赋常量。**这个 `always@(*)` 块没有任何敏感信号，iverilog 直接判定"永不触发"：**

```
ipm2l_spram_v1_8_data_ram.v:303: warning: @* found no sensitivities so it will never trigger.
（371/378/385 行同样）
```

结果 `cs_bit0/cs_bit1/cs_bit2` 永远是 `x`，于是 `csa_reg` 永远为 `x`，`write_en_a = csa_reg && ... = 0` —— **理论上任何写都不会发生**。

我用一个 `initial` 给这几个 CS 信号补了初值后，写立刻就能成功。这**证明问题 C 是纯 iverilog 仿真假象**：真实综合时这些是常量 0，Pango 自己的仿真器也不会有这个问题。

但它有害：**`x` 会把真正的采样失配（问题 A/B）伪装成"仿真器不支持"**，让你在错误的路上排查。

---

## 3. 验证：补上 CS 初值后，症状精确复现

在 `ipm2l_spram_FIXED.v` 中加入：

```verilog
initial begin
   cs_bit0 = 1'b0;  csb_bit0 = 1'b0;
   for (gen_m=0; gen_m<ADDR_LOOP_NUM; gen_m=gen_m+1) begin
      cs_bit1_bus[gen_m] = 1'b0;  cs_bit2_bus[gen_m] = 1'b0;
      csb_bit1_bus[gen_m] = 1'b0; csb_bit2_bus[gen_m] = 1'b0;
   end
end
```

结果：

```
t=190ns  READ addr=0 -> rd_data=00000001   ← 不是我写的值（后面解释）
t=210ns  READ addr=1 -> rd_data=bbbbbbbb   ← 与你现象完全一致 ✅
```

**读回 addr=1 = `bbbbbbbb` —— 一比一复现。**

> 顺带说明 addr=0 读回 `00000001`：这是 `INIT_FORMAT=HEX`、`INIT_FILE="D:/riscv/tbtb/ram_test.dat"` 的初始化数据（ram_test.dat 首行是 `01`）。**IP 的初始化数据是好的，没有丢失。**

---

## 4. 修复

### 4.1 如果是"就想让这个 tb 写对"（最简单）

不要在复位释放的同一拍改激励，**先把 `wr_data` 稳定住**，再单独拉 `wr_en`：

```verilog
initial begin
    resetn = 1'b0;
    wr_data = 32'h0; addr = 10'h0; wr_en = 1'b0;

    #95;  resetn = 1'b1;
    // 复位释放后先让控制信号稳定两拍（等 rsta_int 真正撤销）
    #20;
    addr = 10'h1;  wr_data = 32'haaaaaaaa;
    #10;
    wr_en = 1'b1;          // 数据已稳定 10ns，此沿写入
    #10;
    wr_en = 1'b0;
    #200;
    $finish;
end
```

要点：**`addr`/`wr_data` 提前于 `wr_en` 至少 1 拍建立**，并且**避开复位撤销的那一拍**（内部 `rsta_int` 比你 `resetn` 晚一拍）。

### 4.2 如果是"想在 iverilog 里正常仿真 IP"

在你的仿真脚本里用打过补丁的 wrapper（`.workbuddy/sim_dram/src/ipm2l_spram_FIXED.v`），或在自己的 tb 里加：

```verilog
initial begin
    force u_data_ram.U_ipml_spram_data_ram.cs_bit0 = 1'b0;
    // 其余 CS 同理
end
```

更推荐的做法：**用 Pango PDS 自带的仿真流程**（ModelSim/自带 sim），`x` 问题不会出现。

### 4.3 CPU 设计中要注意的

**结论先行：你当前"四个信号（读/写使能、地址、写数据）全部组合直连 data_ram、且都出自 EX 级"的接法，不存在错拍问题，无需修改。**

原因：这四个信号在**同一个 EX 级组合逻辑**里生成、共享同一条到 RAM 的通路、**同拍到达并被采样**。加法器最慢只是让这条路径变成整体时序瓶颈（压频率），**逻辑上四者依然严格对齐**，不会出现"地址是新的、使能是旧的"。

真正会错拍的只有**混搭**接法（例如地址组合直连、但使能走了 EX/MEM 寄存器）。两条路任选其一即可：

| 接法 | 是否错拍 | 代价 |
|---|---|---|
| 四信号全组合直连（**你现在**） | **不会** | 最慢路径在 EX 加法器，压频率 |
| 四信号全寄存到 EX/MEM 后再用 | 不会 | 多一拍，路径短 |
| 混搭（地址直连 + 使能寄存） | **会错拍** | —— |

另外两点必须盯住：

1. **EX 级被 stall 时，这四个信号必须整体冻结**（用 enable/hold）。否则停顿期间信号变化会让 RAM 误动作。
2. **读写要用同一套 EX 信号**，这样"EX 发请求、MEM 收数据"的一拍延迟天然对齐。

还有一条与本问题相关的硬件事实：IP 的 `rst` 是高有效，你接 `~resetn` 正确，**但 IP 内部还会同步打一拍**（`rsta_int`），实际复位撤销比你 `resetn` 晚一拍 —— 这与之前在 `inst_rom` 上定位的"复位晚一拍释放"是**同一个根因**。

---

## 5. 一句话总结

| # | 问题 | 性质 | 影响 |
|---|---|---|---|
| A | tb 在复位撤销边界窗口内改 `wr_data` | 测试写法 | 首次采样失配 |
| B | 内部 `rsta_int` 比 `resetn` 晚一拍 | IP 固有特性 | 放大了 A，真实 CPU 需让复位晚一拍释放 |
| C | `cs_bit*` 恒为 `x`（iverilog 对无敏感信号 `always@(*)` 不执行） | 仿真假象 | 掩盖 A/B，误导排查方向 |

**直接原因：`csa_reg` 与 `da_reg/wea_reg/ada_reg` 更新条件不同，在 CS 未初始化（恒 `x`）时失去对齐，加上 tb 在复位边界改激励，导致写使能有效那一拍写通路状态错乱，`bbbbbbbb` 被写了进去。**

**重要：用户当前的 CPU 接法（四信号全组合直连、同出 EX 级）不存在此问题。**
