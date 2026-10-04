# difftest —— myCPU 黄金轨迹差分验证环境

一句话：**用一份独立生成的"黄金轨迹"，逐条卡住 myCPU 每一次写寄存器，对不上就立刻报错停机。**

```
                  ┌─────────────────────────────┐
                  │  golden/rvtool.py           │
   程序 .S  ────► │  ① 汇编  ② 指令级仿真(ISS)  │ ───► rom.hex / trace.txt / itrace.txt
                  │  ③ 导出黄金轨迹与终值        │      rf_golden.txt / mem_golden.txt
                  └─────────────────────────────┘
                                                        │
   myCPU RTL ────► tb/tb_difftest.v ── 每拍比对 ──────────┘  不一致 → 打印现场 + $finish
                    model/*.v  (时序忠实的存储器行为模型)
```

---

## 1. 快速开始

```powershell
cd D:\riscv\RISCV\difftest

# 无访存覆盖测试（算术/逻辑/移位/比较/lui/auipc/6 条分支/jal/jalr/循环）
.\run.ps1 -Prog prog0_alu

# 含访存覆盖测试（sw/sh/sb + lw/lh/lb/lhu/lbu）
.\run.ps1 -Prog prog1_mem

# 换一份 CPU 源码再跑同一套黄金轨迹（例如修复版）
.\run.ps1 -Prog prog1_mem -Dut .\rtl\mycpu_sync_loadfix.v -Tag _loadfix

# 额外导出波形，便于失败时看时序
.\run.ps1 -Prog prog1_mem -Wave
```

退出码 `0` = PASS，`1` = FAIL。每次运行的产物都在 `build\<程序名><Tag>\`。

### 结果矩阵（当前 RTL 实测）

| 程序 | `myriscv/mycpu_sync.v`（原版） | `difftest/rtl/mycpu_sync_loadfix.v` |
|---|---|---|
| `prog0_alu`（不访存） | **PASS**（78/78 条指令，54/54 次写回） | **PASS** |
| `prog1_mem`（含访存） | **FAIL** `@pc=00000060` 第 18 次写回<br>`DUT x19<=00000000` / `黄金 x19<=00000123` | **PASS** |

原版的失败不是环境问题，是 `data_ram` 同步读 1 拍延迟没有在 load 写回里算进去
（`doc/mycpu_sync代码问题清单.md` 的 E 项）。修法见 `doc/黄金轨迹差分验证方法.md` 第 6 节。

---

## 2. 目录说明

```
difftest/
├─ golden/
│  ├─ rvtool.py        汇编器 + RV32I 指令级模拟器 + 轨迹生成 + 终值比对
│  └─ selftest.py      自检：汇编器 vs 工程 ROM 实际固化值、黄金模型行为、trace/itrace 一致性
├─ prog/
│  ├─ prog0_alu.S      覆盖测试 0：不访存（定位"控制流与运算"）
│  └─ prog1_mem.S      覆盖测试 1：含访存（定位"访存路径时序"）
├─ model/
│  ├─ inst_rom.v       指令存储器行为模型（1 拍同步读 + 复位后输出强制 0 一拍）
│  └─ data_ram.v       数据存储器行为模型（1 拍同步读、字节使能写）
├─ tb/
│  └─ tb_difftest.v    差分比对测试台（唯一的 checker）
├─ rtl/
│  └─ mycpu_sync_loadfix.v   mycpu_sync.v + load 停一拍（参考实现，未合入工程）
├─ run.ps1             一键脚本
└─ build/<程序>/       每次运行的产物（rom.hex、日志、DUT 终值导出…）
```

---

## 3. 三路比对，各有分工

| # | 比对内容 | 采样点 | 能抓到什么 |
|---|---|---|---|
| 1 | **写回轨迹** `{pc, wnum, wdata}` | 每拍 `debug_wb_rf_we != 0` 时 | 运算结果错、写错寄存器、漏写/多写 |
| 2 | **指令流** `{pc, inst}` | 每拍 ID 级有有效指令时 | 取指错、分支目标错、冲刷漏冲/多冲、PC 错位 |
| 3 | **终值** 寄存器堆 + 数据存储器 | 跑到停机点后整体导出 | 数据通路与存储器交互的整体一致性 |

第 3 路由 `rvtool.py check` 完成；不跑到停机点就导不出终值。

> **为什么第 2 路比第 1 路更值钱**
> prog1 里最早那几条 `lw` 之所以"侥幸对上了"，是因为前一条指令算出的地址恰好和
> load 地址相同。只看写回，会以为访存没问题。第 2 路 + 循环里换地址的 load
> 才把它钉死。**覆盖不到的地方，比对器再严也没用。**

---

## 4. 黄金轨迹格式

```
trace.txt                      itrace.txt
-----------                    -----------
00000060 00000017              ← halt_pc, 写回事件数      00000060 00000020   ← halt_pc, 指令数
00000000 01 00000040           ← pc, wnum, wdata          00000000 04000093   ← pc, inst
00000004 02 00000123                                      00000004 12300113
...                                                        ...
```

- 全是纯十六进制数字，`$fscanf` 直接读，无需字符串解析。
- 只记录**真正写寄存器**的事件（`rd != 0`）。写 x0 不算写回 —— RTL 侧
  `debug_wb_rf_we` 已按 `rf_waddr != 0` 门控，两边口径一致。
- **停机标记是 `jal x0, self`（自环跳转）**。黄金模型与 RTL 都认它，程序必须以它结尾。

---

## 5. 加一个新的测试程序

```powershell
# 1) 写汇编，放到 prog\myprog.S
#    可用指令就是 DUT 已实现的那批；表外助记符汇编器会直接报错（不让你编出跑不了的东西）
#    必须以  halt: jal x0, halt  结尾

# 2) 跑
.\run.ps1 -Prog myprog
```

程序里能用的东西：

| 类别 | 指令 |
|---|---|
| R 型 | `add sub and or xor sll srl sra slt sltu` |
| I 型 | `addi andi ori xori slti sltiu slli srli srai` |
| U 型 | `lui auipc` |
| 跳转 | `jal jalr` |
| 分支 | `beq bne blt bge bltu bgeu` |
| 访存 | `lw lh lb lhu lbu` / `sw sh sb`（**只支持对齐访问**，见下） |
| 伪指令 | `nop mv li not neg` |
| 指令数 | `.org` `.word` `.space` |

**跳转/分支的操作数写绝对目标地址**（标签或字面量），不是相对偏移：
`jal x0, halt`、`beq x1, x1, _b2`、`jal x0, 0x18`。

### 已知限制（写程序时避开）

- **非对齐访存不要用**：`l_alu` 对 `offset=01/11` 的 `lh/lhu` 没有正确实现
  （`myriscv/l_alu.v` 第 29–36 行两个分支都取 `halfword_data2`）。混进去会把
  "时序错"和"译码错"搅在一起。差分验证会如实报出来，但定位会变慢。
- **`sw` 跨字边界不要用**：`data_ram` 的地址是 `byte_addr[11:2]`，跨字写会被卷回同一字。
- 地址空间 4 KB（1024 字），`inst_rom` 与 `data_ram` 是**两块独立存储器**，
  所以取指地址和数据地址可以重叠，不冲突。

---

## 6. 为什么用行为模型而不是厂商 IP

| | 行为模型（本环境默认） | 厂商 `ipcore/inst_rom` + `ipcore/data_ram` |
|---|---|---|
| 工具 | iverilog（本机可用） | vsim / ModelSim（Pango 库在 `D:\modelsim\...\pango_sim_libraries`，**没有 .v 源文件**） |
| 换程序 | 改 `rom.hex` 即可 | 必须重新生成 IP 的 `INIT_xx` 常量 |
| 用途 | **日常功能回归（本环境）** | 上板前的最终时序签核 |

两个行为模型的时序是**照真 IP 的实测结论写的**，不是简化版：

- 同步单端口、**读延迟 1 拍**（地址在沿上锁存，数据沿后有效）；
- `OUTPUT_REG=0 / FAB_REG=0` → 读通路里只有那一个地址寄存器，所以数据不是"再打一拍"；
- ROM 内部地址寄存器**不带复位**（`RST_VAL_EN=false`）；
- ROM 输出在 `rst` 撤销后**仍被强制为 0 一个时钟**（IP 内部把 `rst` 打了一拍）。

最后一条是 `doc/取指ROM复位后丢第一条指令_原因与修复.md` 里那个坑的根源，本模型保留了它，
所以它比"乐观模型"更悲观 —— **能在这个模型下过，才是真的过**。

### 换到真 IP（vsim）

`tb/tb_difftest.v` 与工具无关，换存储器只需换编译文件表：

1. 用 `golden/rvtool.py` 生成的 `rom.hex` 去重新生成 inst_rom 的初始化常量
   （把 1024 个字按 IP 的 `INIT_xx_0_0` 打包规则写进 `inst_rom_init_param.v`），
   或者直接把 IP 的 `INIT_FILE` 指到 `rom.hex` 并置 `INIT_FORMAT="HEX"`；
2. 编译 `ipcore/inst_rom/*` + `ipcore/data_ram/*`，**不要**编译 `model/*.v`；
3. 把 `tb_difftest.v` 的 `rom.hex` / `ram.hex` 依赖去掉（改由 IP 自带初始化）；
4. 注意 `dump_final` 里的层次名 `dut.the_instance_name.mem[i]` 是行为模型专用的，
   真 IP 下要先探到内部阵列名，或把这一路比对关掉（前两路照样有效）。

---

## 7. 常见失败与处置

| 现象 | 含义 |
|---|---|
| `写回 PC 不一致` | 控制流错了：分支/jal/jalr/冲刷错，或取指与 ID 错位 |
| `写回内容不一致` | 运算结果错 / 读到了旧值（load 时序、RAW） |
| `多出的写回` | 不该写寄存器的指令写了（非法指令、CSR 占位指令） |
| `指令流不一致` | 取指地址错、气泡数不对、错路指令没冲干净 |
| `多执行的指令` | 黄金程序已结束还在跑：停机判定或 PC 跑飞 |
| `超过 N 拍仍未到停机点` | 死循环、PC 卡死、停机标记找不到 |
| `已到停机点，但轨迹没走完` | 漏执行指令或漏写回 |

失败时打印的格式固定为「第几次写回 / 第几条指令 + DUT 值 + 黄金值」，
直接可以拿去做二分定位；配合 `-Wave` 看 `build\<prog>\wave.vcd`。
