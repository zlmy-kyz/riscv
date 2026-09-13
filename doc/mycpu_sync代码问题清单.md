# mycpu_sync.v 代码问题清单

- 复核对象：`myriscv/mycpu_sync.v`（module `mycpu_single_async`，213 行）
- 时间：2026-09-13
- 方式：逐行静态复核 + **iverilog 11.0 单文件编译复核**（日志见 `.workbuddy/review_sync/lint1.log` / `lint2.log` / `lint3.log`）
- **工程文件一个字没动**；`.workbuddy/review_sync/` 下只有三个空壳 stub 和一份"只改了两处"的副本（`mycpu_sync_fixed.v`，用来把 6 个 error 降到 0 后看剩余告警）

---

## 0 先说对的：取指侧时序已经正确（不用再改）

不变式推导（`vaild` = 复位释放后延一拍）：

| 时刻 | pc | vaild | ROM 地址口 | ROM 输出 |
|---|---|---|---|---|
| 复位期间 | 0 | 0 | `pc` = 0 | 0/未定 |
| E0（复位释放那一沿）| 保持 0（因为沿前 vaild=0）| ← 1 | 沿前 = `pc` = 0 → ROM 锁 0 | 0 |
| E0 之后 | 0 | 1 | `next_pc` = 4 | **mem[0]** |
| 稳态每拍 | P | 1 | P+4 | **mem[P]** |

- `if_id` 块用的是 `if(!vaild)` 而不是 `if(!resetn)` → **复位释放那一拍不会出现"假有效气泡"**，上次 4.7 节给的最小修改你已经改对了。
- 稳态恒有 `inst == mem[pc]`，且 pc 与 ROM 内部地址寄存器**锁步** → mem[0] 不丢、指令与 pc 天然配对、0 气泡。**取指这条链是对的。**
- 唯一的硬约束（沿用旧结论）：`next_pc` 必须在时钟沿前充分稳定（满足 ROM 地址寄存器 setup）→ 分支判定必须当拍组合完成。第 3 节修 `next_pc` 时这一点会变成真实的关键路径。

---

## 1 结论速览

| # | 位置 | 级别 | 问题 | 后果 |
|---|---|---|---|---|
| A | 1–4 / 15 / 182–190 / 208–211 | 🔴 阻塞 | 顶层只有 `clk/resetn`；**没有 data_ram 例化**，8 个信号（`data_sram_we/addr/wdata/rdata`、`debug_wb_*`）成了**隐式 1 位线网** | 无法接存储/观测口；32 位信号被截成 1 位；`-Wall` 逐条报 implicit |
| B | 6 vs 182/197 | 🔴 阻塞 | 声明的是 `vaild`，用的是 `valid`（拼写） | iverilog **error**:Unable to bind wire/reg/memory `valid`；侥幸跑起来则写使能变 x |
| C | 129–135 | 🔴 阻塞 | `.rst_n(resetn)` —— 本工程 `regfile.v` **没有 rst_n 端口** | iverilog **error**:port `rst_n` is not a port of u_regfile |
| D | 26 / 32 / 53 / 139 | 🔴 功能 | `next_pc = pc+4` 恒定；`b_pc`、`br_taken` 算了不用；`imm_j` 未使用 | **所有分支/跳转都不跳**：beq/bne/blt/bge/bltu/bgeu/jal/jalr 全部顺序执行 |
| E | 184 / 199 | 🟠 功能 | load 假设"读当拍出数"，但真 data_ram 是**同步读、延迟 1 拍** | `lw/lh/lb` 写回的是**上一个地址**的数据 |
| F | 36–50 | 🟡 结构 | `if_id_inst/pc/valid` 只写不读 | 死逻辑，会被优化掉；与"单周期"架构自相矛盾 |
| G | 148–172 | 🟠 一致性 | `alu_op` 是 11 位自定义编码；工程里现存的 `risv_loon/alu.v` 是 12 位**另一套编码** | 链接错版本 → lui/and/or/xor/sll/srl/sra/slt… 大面积错 |
| H | 196–201 | 🟡 功能 | `gf_we = ~wmem & ~inst_b` → 非法指令 / CSR / ecall / fence 都会写回 rd | `csrrw x1,…` 之类会把垃圾写进 x1，而 CSR 寄存器根本没实现 |
| I | 15 / 19–22 / 183 | 🟡 接线 | `inst_sram_addr` 是内部 wire；`data_sram_addr` 给 IP 前没做 `[11:2]` 字地址切片 | 顶层拿不到取指地址；字节地址直接接 10 位 addr 口会错位 |
| J | 203–211 | 🟡 观测 | 注释写"必须拍存沿前值"，代码却是组合直出 | debug 口比"该沿提交的指令"差一拍，与 tb 约定要对齐 |
| K | 1 | ⚪ 命名 | 模块名 `mycpu_single_async` ≠ 文件名 `mycpu_sync.v`，且 `async`(异步) 与"同步存储"矛盾 | 容易混；tb 按名例化时改名要同步 |

iverilog 实测（`lint1.log`，未修版）：

```
EXIT=6
mycpu_sync.v:129: error: port ``rst_n'' is not a port of u_regfile.
mycpu_sync.v:182: error: Unable to bind wire/reg/memory `valid' in `mycpu_single_async'
mycpu_sync.v:182: error: Concatenation/replication may not have zero width in this context.
mycpu_sync.v:182: error: Unable to elaborate r-value: (st_we)&({'sd4{valid}})
mycpu_sync.v:187: warning: Port 3 (data_sram_rdata) of l_alu expects 32 bits, got 1.
mycpu_sync.v:197: error: Unable to bind wire/reg/memory `valid' in `mycpu_single_async'
6 error(s) during elaboration.
```

修掉 B、C 两处后再编译（`lint3.log`，挂在 `-Wall` 上）——**剩余 8 条 implicit，全部点名**：

```
mycpu_sync.v:182: warning: implicit definition of wire 'data_sram_we'.
mycpu_sync.v:183: warning: implicit definition of wire 'data_sram_addr'.
mycpu_sync.v:184: warning: implicit definition of wire 'data_sram_wdata'.
mycpu_sync.v:190: warning: implicit definition of wire 'data_sram_rdata'.
mycpu_sync.v:208: warning: implicit definition of wire 'debug_wb_pc'.
mycpu_sync.v:209: warning: implicit definition of wire 'debug_wb_rf_we'.
mycpu_sync.v:210: warning: implicit definition of wire 'debug_wb_rf_wnum'.
mycpu_sync.v:211: warning: implicit definition of wire 'debug_wb_rf_wdata'.
```

---

## 2 逐条说明

### A. 存储与观测口整体缺失（最致命）

现象：module 头只有 `clk/resetn`，但正文里
- `inst_sram_addr`（15 行）= **内部** wire，外面看不到（这个至少还是 32 位）；
- `data_sram_we/addr/wdata/rdata`（182–190 行）= **完全没声明** → 隐式**标量**线网；
- `debug_wb_pc/rf_we/rf_wnum/rf_wdata`（208–211 行）= 同上，32 位值被**截断成 1 位**。

更关键的是：**文件里根本没有 data_ram 例化**。`inst_rom` 在第 18 行例化了，data 侧什么都没有 → 送出去的写使能/地址/写数据没有落点，读回来的 `data_sram_rdata` 永远是 z/0。

两种补法（按你的 tb 约定选一个）：
1. **把 data_ram 例化进来**（和你 `topcpu_instrom.v` 一致：IP 在 CPU 顶层内，tb 通过 `wr_data/addr/wr_en` 写数据，再层次化取内部信号探针）：
   ```verilog
   data_ram u_data_ram (
       .addr       (data_sram_addr[11:2]),
       .wr_data    (data_sram_wdata),
       .wr_en      (|data_sram_we),        // 或 data_sram_we[0] 单比特写法
       .wr_byte_en (data_sram_we),         // sb/sh 的字节掩码
       .clk        (clk),
       .rst        (!resetn),
       .rd_data    (data_sram_rdata)
   );
   ```
   注意 `source/tb_topcpu_instrom.v` 那种 tb 只给了 `wr_data[31:0]/addr[9:0]/wr_en`，**没有字节使能**，所以 sb/sh 若要走 tb 写通路还得扩 tb 接口。
2. **提成顶层端口**（和 `topcpu.v` 一致）：把 8 个信号写进端口表，并在端口表里删掉第 15 行的 `wire [31:0] inst_sram_addr;`（否则重复驱动）。
   建议 `data_sram_we` 直接定成 **`[3:0]`**（你 178–181 行算出来的 `st_we` 本来就是 4 位字节掩码，按 1 位截会把 sb/sh 全变整字写）。

### B. `valid` / `vaild` 拼写不一致

`reg vaild;`（6 行）声明，但 182 行 `{4{valid}}`、197 行 `gf_we & valid` 用了另一个名字。iverilog 直接把这两行判成 **error**（RHS 未声明标识符不像 LHS 那样能隐式建网）；ModelSim 也是编译错误。即使某个工具容忍，`valid` 也会是**恒 z**的 1 位线网 → `rf_we`/`data_sram_we` 变 x → "有时写有时不写"，比没有闸门更糟。

顺带：`vaild` 这个名字本身名不副实（它是"复位释放后延一拍 = 可以提交指令"）。建议：

```verilog
reg rst_n_d1;
always@(posedge clk) rst_n_d1 <= resetn;   // 原 vaild 的全部逻辑(含复位分支)保留亦可
wire valid = rst_n_d1;                     // 语义：运行中；所有副作用与它相与
```
改名时记得同步 4 处：6–13（定义）、27（`inst_sram_addr` 三目）、32（pc 更新）、40（if_id 块）。

### C. `regfile` 多了一个不存在的端口

`myriscv/regfile.v` 的端口是 `(clk, raddr1, rdata1, raddr2, rdata2, we, waddr, wdata)` —— **没有 `rst_n`**，所以 `.rst_n(resetn)` 直接编译报错。删掉它即可；如果确实想要"复位清空寄存器堆"，就去 regfile.v 加端口并想清楚：**x0 恒 0 由读口保证，复位清零不是必须的**（还会多一条全局复位线进 RF）。

### D. 分支/跳转完全不改 PC

- 26 行 `next_pc = pc + 4` 是常量表达式；
- 53 行 `b_pc`、139/144 行 `br_taken` 都算出来了却**没有任何消费者** → 分支/跳转对 PC 零影响；
- 121 行 `imm_j` 声明后从未使用（jal 目标压根没算）；
- `jalr` 还缺"rs1 + imm_i 再清最低位"这一步。

补法（单周期下分支**零气泡**：`br_taken` 本来就是当拍组合出结果，而 ROM 地址口用的就是 `next_pc`）：

```verilog
wire [31:0] jalr_pc = (rdata1 + imm_i) & ~32'h1;      // jalr 目标
wire [31:0] bj_pc   = inst_jalr ? jalr_pc
                    : inst_jal  ? pc + imm_j
                    :             pc + imm_b;          // b_pc 在这里复用，别留着不用
wire        pc_sel  = br_taken | inst_jal | inst_jalr;
assign      next_pc = pc_sel ? bj_pc : pc + 32'h4;
```
`pc <= vaild ? next_pc : pc;` 保持不变即可（地址口也用 `next_pc`，两边自然同沿跳转）。

### E. load 的"读当拍出数"是错的（真 IP 下必错）

176 行注释说"读当拍出数，故删 wb_mem_sel 延迟"。但按 `.workbuddy/sim_dram` 那轮实测（与 09-11 的 inst_rom 同源）：Pango `data_ram` 是**同步读、读延迟 1 拍**——地址在沿上被采样，数据**下一个沿**才更新。

于是本文件的做法是：
- 拍 N：`alu_result`（load 地址）送 `data_sram_addr`，同拍 `rf_wdata = l_alu(data_sram_rdata)`；
- 而拍 N 的 `data_sram_rdata` 是**拍 N-1 那个地址**的数据（NORMAL_WRITE 模式下即使刚写过也不透明）→ **在沿 N 把错数据写进 rd**；正确数据在拍 N+1 才出现，那时指令已经走过去了。

取指侧之所以能一拍完成，是因为地址被"提前一拍预取"（地址口给 `next_pc`）；**数据侧地址依赖当拍译码结果，没有提前量**，所以：
- store 没问题（写发生在沿上，与 `sim_memwr` 那轮实测一致）；
- **load 必须多占一拍**，或者干脆不要坚持单周期。

三个选项：
1. **给 load 加等待拍**（推荐，改动可控）：`mem_stall = i_l`；拍 1 发地址并冻结 `pc`、`rf_we=0`；拍 2 用**锁存的 `{rd, rf_we, is_load}`** 把 `mem_result` 写回。代价：load 变 2 拍。
2. **改回 5 级**（你已经有一版 `topcpu.v` 的骨架）：RAM 的地址寄存器当 EXE/MEM 边界，数据在 MEM 级取用 —— 这是"同步读 RAM"的标准接法。
3. 只在**行为级组合读 RAM 模型**下仿真：能跑通，但与真 IP 不一致，上板必错。

> ⚠️ 有个前提要你确认：这个文件名叫 `mycpu_sync.v`、module 又叫 `mycpu_single_async`。**如果它的存储是"组合读（异步）模型"，E 这一条不成立**；但只要接的是 `ipcore/data_ram` 真 IP（同步读），E 就一定成立。这一条决定了后面要不要引入等待拍。

### F. `if_id_*` 是死代码

36–50 行写 `if_id_inst/if_id_pc/if_id_valid`，全文没有任何读取者（译码用的是组合的 `inst`、PC 用的是 `pc`）。也就是说这版其实是"**指令直通 ID（方案一-B）**"的接法，和 `if_id` 寄存器、和 203 行"经典单周期"注释混在一起 → 两套架构的残渣。综合会把它们优化掉；但若以后接异常/CSR，必须先定死"指令是直通还是寄存"，不能一半一半。

### G. `alu_op` 编码必须与链接进来的 `alu` 对齐

本文件 149–161 行的编码：`[0]add [1]sub [2]lui [3]and [4]or [5]xor [6]sll [7]slt [8]srl [9]sra [10]sltu`（11 位）。
工程里现存的 `risv_loon/alu.v` 用的是**另一套 12 位**编码：`[0]add [1]sub [2]slt [3]sltu [4]and [5]nor [6]or [7]xor [8]sll [9]srl [10]sra [11]lui`。

| 位 | 本文件期望 | risv_loon/alu.v |
|---|---|---|
| 2 | lui | **slt** |
| 3 | and | **sltu** |
| 4 | or | **and** |
| 5 | xor | **nor** |
| 6 | sll | **or** |
| 7 | slt | **xor** |
| 8 | srl | **sll** |
| 9 | sra | **srl** |
| 10 | sltu | **sra** |
| 11 | — | lui |

链接错版本时只有 add/sub 侥幸对上，其余全错。另外 `myriscv/` 目录里**没有** `alu.v` / `l_alu.v` / `inst_rom.v`，只有 `regfile.v / Reg.v / mux.v / topcpu_instrom.v / br_alu.v / mycpu_sync.v`——编译时到底挂哪几个文件、哪个版本，得先定下来（这次复核用的是我自己写的空壳，只能验语法与端口，验不了功能）。

### H. 写回条件太宽

`wmem = sw|sh|sb; gf_we = ~wmem & ~inst_b;` → 除了 store/分支，**所有**译码不中的编码（`opcode=0` 非法指令、`fence`、`ecall/ebreak`、以及 102–107 行已译码但没有实现的 6 条 CSR 指令）都会 `rf_we=1`，把 `alu_result` 写进 rd。
建议：
- 加 `wire inst_illegal = ~(|{inst_add,...,inst_csrrci});`，`gf_we = 写回类指令 & ~inst_illegal`；
- 或者显式列出写回集合（R 型 / I 型算术 / 移位 / lw 类 / lui / auipc / jal / jalr / csr*），别用"取反"。

### I. 地址切片与复位极性

- `inst_sram_addr[11:2]` 给 ROM（18–19 行）✓ 正确；
- `data_sram_addr = alu_result;`（183 行）**没有**切片 → 接 IP 的 10 位 `addr` 口时应写 `alu_result[11:2]`（4KB 外会静默回绕）；
- `inst_rom` 的 `rst` 接 `!resetn`（21 行）✓ 极性正确，但记住这个 IP 是**高有效同步复位**，且"外部撤销后内部还会再同步一拍"（旧结论），所以 CPU 侧的 `rst_n_d1/vaild` 这类延迟一拍的做法要保持。

### J. 观测口的相位与 tb 约定

203–205 行注释自己写了"tb 在沿后采样（显示该沿提交的指令）……**必须拍存沿前值**"，但 208–211 行是**组合直出**：沿后采样看到的是"下一拍才会提交的那条指令"（`pc` 已经 +4、`inst` 已是下一条）。要让 trace 显示"该沿提交的指令"，就得把观测口寄存一拍：
```verilog
reg [31:0] dbg_pc, dbg_wdata;  reg [3:0] dbg_we;  reg [4:0] dbg_wnum;
always@(posedge clk) begin
    dbg_pc <= pc; dbg_wdata <= rf_wdata; dbg_we <= {4{rf_we}}; dbg_wnum <= rf_waddr;
end
```
或者反过来，把 tb 的采样点/预期表整体挪一拍（现在 `source/` 下**没有** `mycpu_sync` 的 tb，只有 `tb_topcpu_instrom.v`，正好趁写 tb 时把约定定死）。

### K. 命名

模块名 `mycpu_single_async` 与文件名 `mycpu_sync.v` 不一致，而且 `async`（异步）和"同步存储/同步打拍"语义相反，容易在 tb 例化和后续对比实验里搞混。建议统一成 `mycpu_single_sync` 之类（改名时同步 tb）。

---

## 3 最小修复优先级

1. **B、C**（两行，编译级）→ 先把 6 个 error 清零；
2. **A**（补 data_ram 例化或端口，`data_sram_we` 定 4 位）→ 才谈得上跑起来；
3. **D**（分支/跳转接 `next_pc`）→ 程序才有控制流；
4. **E**（确认存储是同步还是异步；同步就必须给 load 加等待拍）→ 这是最影响"结果对不对"的一条；
5. F/G/H/I/J/K 属于收尾清理与一致性核对。

## 4 复核命令（可复现）

```powershell
# 1) 原文件:应报 6 个 error
& "D:\iverilog\bin\iverilog.exe" -g2012 -t null -s mycpu_single_async `
  D:\riscv\RISCV\myriscv\mycpu_sync.v D:\riscv\RISCV\myriscv\regfile.v `
  D:\riscv\RISCV\myriscv\br_alu.v D:\riscv\RISCV\.workbuddy\review_sync\stubs.v

# 2) 加 -Wall 看隐式线网(修掉 B/C 之后再跑)
& "D:\iverilog\bin\iverilog.exe" -g2012 -Wall -t null -s mycpu_single_async `
  D:\riscv\RISCV\.workbuddy\review_sync\mycpu_sync_fixed.v ...
```

> 本机 PowerShell 抓不到原生命令的 stdout，需要 `| Out-String` 再 `Set-Content -Encoding ASCII` 落盘看（见 `.workbuddy/review_sync/*.log`）。
