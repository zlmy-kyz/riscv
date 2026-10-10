# mycpu_sync.v 代码问题清单

- 复核对象：`myriscv/mycpu_sync.v`（655 行，module `mycpu_sync`，5 级流水 IF|ID|EX|MEM|WB）
- 本轮复核：2026-09-15
- 上一轮：2026-09-13，对象是 **213 行版本**（module 还叫 `mycpu_single_async`）。那份清单里的
  A~K 已经**逐条核对过**，现状见第 0 节 —— 保留这张表是为了别让人对着旧结论改新代码。

---

## 0 上一轮 A~K 的现状

| # | 旧问题 | 现状 | 核对依据 |
|---|---|---|---|
| A | 存储与观测口整体缺失，无 `data_ram` 例化 | ✅ 已修 | 端口表 5 个 debug 口齐全；`data_ram the_instance_name` 已例化 |
| B | `valid` / `vaild` 拼写不一致 | ✅ 已修 | `vaild` 0 次，`valid` 16 次 |
| C | `.rst_n(resetn)` 挂到没有该端口的 `regfile` | ✅ 已修 | 现为 `.rst(!resetn)`；`regfile.v` 也已补上 rst 端口 |
| D | 分支/跳转完全不改 PC | ✅ 已修 | `next_pc = flush ? bj_pc : pc + 4`，`flush = id_taken & if_id_valid & ~load_use` |
| E | load "读当拍出数"（真 IP 下必错） | ✅ 已修 | 走**访存方案一**：`alu_result` 组合直连 RAM 地址口，RAM 内部地址寄存器充当 EX/MEM 边界，数据在 MEM 级消费。`difftest prog1_mem` 已 PASS |
| F | `if_id_*` 是死代码 | ✅ 已修 | `assign inst = if_id_inst`，IF/ID 已是流水寄存器 |
| G | `alu_op` 编码与链接进来的 `alu` 不一致 | ✅ 已修 | `myriscv/alu.v` 已存在且是同一套 11 位编码。⚠️ 但见 §5 遗留雷 |
| **H** | **写回条件太宽：CSR / 非法指令 / ecall / fence 都会写回 rd** | ❌ **未修，且已实测复现** | 见 §1.1 |
| I | 地址切片与复位极性 | ✅ 已修 | `inst_sram_addr[11:2]` / `data_sram_addr[11:2]` 都切了 |
| J | 观测口相位与 tb 约定对不上 | ✅ 已修 | debug 口来自 `mem_wb_*`（寄存输出），与 tb 的提交级采样对齐 |
| K | 模块名 ≠ 文件名 | ✅ 已修 | 均为 `mycpu_sync` |

> E 条值得记一笔：旧清单给的三个选项是"加等待拍 / 改回 5 级 / 只在行为模型下仿真"，
> 实际采用的是**第四种**——访存方案一。它比"加等待拍"更好：RAM 内部那个地址寄存器
> 直接充当 EX/MEM 边界，地址路径全程组合，load 不多占拍，代价是**地址路径上
> 一个寄存器都不能夹**（`doc/cpu/ROM与RAM时序处理方案总结.md` 第 2 节的三条硬约束）。

---

## 1 仍未修的问题（RTL）

### 1.1 🔴 CSR 指令静默把 rd 清零（旧清单 H，已实测复现）

根因链：

```verilog
assign wmem  = inst_sw | inst_sh | inst_sb;
assign gf_we = ~wmem & ~inst_b;          // ← CSR(1110011) 既不是 S 也不是 B → gf_we = 1
```

CSR 的 opcode 是 `1110011`，`inst_b` 只看 `1100011`，所以 `gf_we = 1`；
而 `alu_op` 11 位里**没有任何一位**被 6 条 CSR 点亮 → `alu_result = 0`
→ 沿 EX/MEM/MEM/WB 一路传下去，最后把 **0 写进 rd**。

**实测**（`iverilog` + 行为级存储模型）：

```
指令: addi x10,0x5A5 / li x11,0x1234 / csrrw x11,0x300,x0
结果: x10=0x000005a5   x11=0x00000000      ← x11 本来是 0x1234，被清零
```

比"没实现 CSR"更糟：**它悄悄改掉一个通用寄存器的值，不报错、不留痕**。
程序里只要有一条 `csrrw x5, mstatus, x1`，x5 之后就废了。

修法两个层次：

- **止血（几行）**：加 `wire i_csr = inst_csrrw|inst_csrrs|inst_csrrc|inst_csrrwi|inst_csrrsi|inst_csrrci;`
  然后 `gf_we = ~wmem & ~inst_b & ~i_csr;`。副作用是 CSR 变成"什么都不做"——仍然是错的，
  但至少不再破坏 rd。
- **做对**：实现 CSR 寄存器堆。而 `mstatus/mtvec/mepc/mcause` 本来就是 trap 机制的一部分 ——
  这一步会自然引向异常/中断，见 §4。

### 1.2 🟠 非对齐 `lh` / `lhu` 取错半字（已实测复现）

`l_alu.v` 第 29-36 行：

```verilog
assign mem_result_lh = (sel_addr == 2'b00) ? {{16{halfword_data1[15]}}, halfword_data1} :
                       (sel_addr == 2'b10) ? {{16{halfword_data2[15]}}, halfword_data2} :
                                             {{16{halfword_data2[15]}}, halfword_data2};
```

`sel_addr` 为 **1** 和 **3** 时都走默认支（取 `halfword_data2` = `data[31:16]`），
但偏移 1 的正确半字是 `data[23:8]`。**实测**：

```
mem[0x40] = 0x12345678
lh  x7, 1(x1)    应得 0x00003456    实得 0x00001234
lh  x8, 3(x1)    应得 0x00000012    实得 0x00001234
```

- **偏移 1**：一行 mux 就能修（改取 `data[23:8]`）
- **偏移 3**：那半字跨到下一个字，**单字输入根本拼不出来** —— 要么把通路加宽到 64 位，要么不支持
- `lb` / `lbu` 四个偏移都对，所以这是**半字专属**的洞

### 1.3 🟠 跨字 `sw` / `sh` 静默丢数据

```verilog
assign data_sram_wdata = id_ex_rs2_data << {2'b00, alu_result[1:0], 3'b000};
assign st_we  = id_ex_sw ? 4'b1111 : ...        // 整字四个字节道全使能
assign data_sram_addr  = alu_result;            // 但地址只有一个字
```

地址 0x3E 的 `sw`：`addr[11:2]` = word 0x3C，数据左移 16 位后写进去。
本该落到 word 0x40 的那两个字节**直接没了**，同时还把 word 0x3C 的低两个字节写成 0。

⚠️ **这一条目前无法用黄金轨迹证明** —— 因为黄金模拟器有同样的限制，见 §2.1。

### 1.4 🟡 `debug_wb_rf_we` 与文档不一致

`difftest/README.md` 第 103 行写"`debug_wb_rf_we` 已按 `rf_waddr != 0` 门控，两边口径一致"，
但 RTL 是：

```verilog
assign debug_wb_rf_we = {4{rf_we}};      // rf_we = mem_wb_valid & mem_wb_gf_we，没看 wnum
```

`jal x0, L` 这类指令 `gf_we = 1` 且 `rd = 0` → `we = 4'b1111, wnum = 0`。
本工程的 tb 用 `we != 0 && wnum != 0` 兜住了，但**别的差分框架若直接看 `we` 就会多算一次写回**。
要么改 RTL 加门控，要么改文档的说法 —— 二选一，别让两边说法不一致。

### 1.5 🟡 地址空间只有 4 KiB 且静默回绕

真 IP `ADDR_WIDTH = 10`（`ipcore/data_ram/data_ram.v:39`、`inst_rom.v:29`），
RTL 送的是 `[11:2]`。ROM 和 RAM 各 4 KiB，**越界直接回绕，没有任何标志位**。
当前测试程序 711 条 = 2.8 KB，够用；程序再长大就会莫名跑飞，且很难查。

---

## 2 测试侧的问题（不是 RTL 的，但同样决定"能不能验出来"）

### 2.1 🔴 黄金模型不跨字 —— 和 DUT 的盲区正好重合

`tbtb/gen_all_test.py`：

```python
def setmem(mem, addr, val, size, off):
    for i in range(size):
        lane = off + i
        if lane > 3:
            break          # ← 跨字的部分悄悄丢掉
        mem[(addr >> 2) & 0x3FF] = ...
```

`getmem` 同样只读一个字。

后果：**跨字访存上模拟器和 DUT 一致地错**，黄金轨迹永远发现不了。
所以 `tball.md` 里"已知限制 2：`sw`/`sh` 不跨字"的措辞要改 ——
不是"受 DUT 限制所以避开"，而是"**模拟器也不支持，想测也测不了**"。

这不是"验证通过"，是两者的盲区重合。**要暴露 §1.3，必须先改 `setmem`/`getmem`**
（拆成跨字的字节通道读写），改完 DUT 会立刻报错。

### 2.2 🟠 没有第三方独立参考

605 条指令的比对发生在"本工程写的 RTL"和"本工程写的模拟器"之间。
两边独立实现，一致是有力证据（编码器/译码器不一致就会露馅，`jal` 目标那次就抓出来了），
但**没有一个已知正确的实现兜底**。

建议：把 `rom_test_all.dat` 喂给 **spike**（或 QEMU / riscv-tests）跑一遍对轨迹 ——
那是完全独立的第三方实现，能盖住"两边共享同一个误解"这类风险。

### 2.3 🟠 只跑行为模型，没跑真 IP；没综合过

`difftest/model/inst_rom.v`、`data_ram.v` 是照 `doc/` 实测结论写的**行为模型**，
不是 Pango IP 本身。`difftest/README.md` 自己也说最终要在 vsim + 真 IP 上复跑 —— 目前没做。

综合侧：RTL 里 `initial` 块数为 0（✅ 可综合），但建立/保持、CDC、资源占用都没验过。

### 2.4 🟡 覆盖是"挑的场景"，不是穷举

605 条指令 / 738 拍，很短。没有随机/约束随机，也没有边界扫描：

- 立即数边界（-2048 / 2047）、移位量 0 / 31
- `x0` 恒零的各种写法与读法
- 地址回绕（§1.5）
- 连续同类型指令的背靠背压力

目前**冒险通路**这一块覆盖得不错（`tbtb/mutate_check_all.py` 18 条变异全部抓住或证明等价），
薄的是**指令边界值**和**长时间运行**。

---

## 3 已经验证可靠的部分（改了要重验）

这几块有变异测试背书，不是"看起来对"：

| 通路 | 证据 |
|---|---|
| 三级前递 EX / MEM / WB | 关掉任一级，黄金轨迹立刻报错 |
| 前递优先级 EX > MEM > WB | 三路同拍命中（T21）能抓出写反 |
| `rd != 0` 前递门控 | 去掉后 T18 的 `rd=x0` 专项立刻报错（该专项是唯一拦截点）|
| load-use 阻塞 + 冻结 pc + 冻结 ROM 地址口 + 冻结 IF/ID | 分别改坏，四条都死在 T23 |
| 分支冲刷 | 关掉后 T01 就错 |
| 存数数据前递（`id_ex_rs2_data`） | 改取 `src2` 后 T09/T22 立刻报错 |

复现：`cd tbtb && python mutate_check_all.py`

### 3.1 与既往 LoongArch 流水线调试记录的对照

`D:\xilinx\output\exp8\think.md`（五级流水 控制/数据冒险）与 `exp12\think.md`（异常与 CSR）
里记录的 8 个坑，逐条对照本核：

| 记录 | 本核 | 依据 |
|---|---|---|
| exp8-1 分支目标已进流水，需冲刷 IF/ID | ✅ 有 | `flush` 清 IF/ID |
| exp8-2 RAW 前递 + 优先级 ID/EX > EX/MEM > MEM/WB | ✅ 有 | EX > MEM > WB；`前递优先级写反` 变异被 T19 抓住 |
| exp8-3 load-use 停顿 + 转发 | ✅ 有 | `load_use` 停 1 拍 + MEM→ID 前递 |
| **exp8-4 阻塞期间指令被 BRAM 输出顶掉** | ✅ **结构性免疫** | 译码吃的是 **IF/ID 寄存器**（`assign inst = if_id_inst`）而不是 ROM 组合输出；且 `inst_sram_addr`／`if_id_*`／`pc` 三者一起冻。四条冻结各自都有变异测试背书 |
| **exp12-1 ld 喂分支要停 2 拍** | ✅ **不存在** | 见下 |
| exp12-2 CSR 复位值 | ⚠️ 未实现 CSR，暂不涉及 |
| exp12-3 CSR 前递（ertn 读到旧 ERA） | ⚠️ 同上 |
| exp12-4 CSR 指令写晚于异常写，跨拍错序 | ⚠️ 同上 |

**exp12-1 为什么在本核不存在**：那台核里分支在 ID 决议、而 load 数据要到 **WB** 才就绪，
所以 ld 相邻喂分支要停 2 拍。本核因为走**访存方案一**（RAM 内部地址寄存器充当 EX/MEM
边界），load 数据在 **MEM 整拍就有效**，并且有 `mem_fwd_data` 这条 MEM→ID 前递。
于是不管消费者是 ALU、分支、jalr 还是存数，**load-use 一律只停 1 拍**，没有例外分支。

这是方案一的一个隐性红利：**所有消费者的取数点统一在 ID 级那一个 mux**（书里说的
"前递路径终点一致"），所以不需要为"ID 级决议的读者"（分支/jalr）单独开一条更长的阻塞路径。

**exp12-3 / exp12-4 是加 CSR+trap 时最值钱的两条教训**，设计时要一开始就定死：

1. **CSR 也要做前递**。`mepc`/`mtvec` 会被 `csrwr` 写、被 `mret` 读，紧邻就是 RAW。
   "只要写目标是寄存器（GR 或 CSR），紧邻的读就需要前递" —— 别只给 GR 做。
2. **指令写与异常写必须同一点**。exp12-4 的根因是"更老的 `csrwr` 在 WB 才落账，
   更新的异常在 EX 就写了现场"→ 老的反而后写、把异常值覆盖。**优先级只能解决同拍冲突，
   解决不了跨拍错序**。所以要么两边都在 EX、要么两边都在 WB，不能一半一半。
   本核若走"EX 检测 misaligned + WB 精确提交"，就得让异常的那几个 CSR 写在 WB 落账，
   和 `csrwr` 对齐。

---

## 4 决策点：修到什么程度

RV32I 对**非对齐访问**给了两个都合规的选择：

- **(a) 硬件直接支持** —— 存储器通路加宽到 64 位（或一次访问拆成两次）。**不需要碰异常机制**
- **(b) 抛 address-misaligned 异常** —— 需要 mtvec / mepc / mcause / mstatus + 流水线冲刷重定向

当前实现是**第三条：静默给出错误结果**。这是唯一不合规的选项。

由此可以把上面几条分成两类：

| 要修的 | 需要异常机制吗 |
|---|---|
| §1.2 非对齐 `lh`/`lhu` **偏移 1** | ❌ 不需要，纯 mux 取错字节道 |
| §2.1 黄金模型跨字 | ❌ 不需要，测试台的事 |
| §2.2 / §2.3 交叉验证 / 真 IP | ❌ 不需要，纯验证手段 |
| §1.1 CSR | ⚠️ 止血不需要；**做对**需要（CSR 和 trap 共用 mstatus/mtvec/mepc/mcause） |
| §1.2 偏移 3、§1.3 跨字 `sw` | ⚠️ 选 (a) 不用，选 (b) 就要 |

**结论**：四项里三项跟异常无关，可以在现有核上独立做完。
只有"CSR 做对"和"跨字访存选 (b)"会把异常/中断机制引进来。

课程验收若只要求"实现 RV32I 基础整数指令子集 + 流水线"，那么把非对齐显式声明为
**不支持**是合理的 —— 但必须先把"静默出错"这个行为去掉（要么硬件支持，要么 trap），
因为静默错值比明确不支持危险得多。

---

## 5 遗留雷：`risv_loon/alu.v` 还在

`myriscv_repo/risv_loon/alu.v` 用的是**另一套 12 位 `alu_op` 编码**：

| 位 | `myriscv/alu.v`（现用） | `risv_loon/alu.v` |
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

链接错版本时只有 add/sub 侥幸对上，其余全错。两份文件同名，摆在不同目录 —— 编译脚本
或综合文件列表里一旦挂错就是大面积静默出错。建议删掉或改名成 `alu_loon_12bit.v`。

---

## 6 复核命令

```bash
# 1) 全指令 + 冒险差分验证
cd tbtb && python gen_all_test.py && ./run_all.ps1     # 期望 RESULT: PASS (605/605, 424/424)

# 2) 变异测试：证明上面那些通路真的被测到
cd tbtb && python mutate_check_all.py                  # 期望 抓住 18 / 漏测 0 / 等价 1

# 3) 项目自带差分（另一套独立程序）
cd RISCV/difftest && ./run.ps1 -Prog prog0_alu
cd RISCV/difftest && ./run.ps1 -Prog prog1_mem
```
