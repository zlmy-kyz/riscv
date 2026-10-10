# DDR3 集成仿真第 1 步：CPU 写、读与从 DDR3 取指

## 本步的目的

此前已分别验证过 DDR3 厂家例程，以及“地址译码器 → DDR 桥”的行为模型，
但这两种测试都不能证明 **CPU 发出的请求能经过真实 DDR3 IP 和 DDR3 存储器模型**。
本步把两条路径接成闭环：

```text
CPU → 指令/数据总线 → 共享 DDR 桥 → Pango DDR3 IP → x16 DDR3 模型
```

先只测试一次 32 位数据写入、读回和从 DDR3 执行指令。这样若失败，排查范围比
直接运行完整 RISC-V 指令测试或启动加载程序小得多。

## 本步做了什么

1. 新建 `source/tb_soc_ddr3_top.v`，例化现有的 `soc_ddr3_top`，并按照厂家
   `ddr3_test_top_tb.v` 的接法连接同一个 `ddr3_mem` 物理模型、100 MHz
   参考时钟、复位以及命令/地址走线延迟。`GTP_GRS` 实例名保持为
   `GRS_INST`，以满足 Pango 原语仿真模型的层级引用。
2. 新建 `source/tb_soc_ddr3_mem.v`，提供**仅用于本次仿真**的同步
   `inst_rom` 和 `data_ram`。它们替代片内存储器 IP，避免测试程序依赖当前
   PDS 中为 `st_ld` 测试配置的 ROM/RAM 初始化文件；DDR3 控制器和外部
   DDR3 存储器模型仍使用厂家的真实仿真文件。
3. 新建 `ipcore/ddr3/sim/modelsim/soc_ddr3_sim.tcl`，复用厂家
   `sim_file_list.f` 编译 DDR3 IP/存储器模型，再编译 CPU、总线、桥和本步
   TB。脚本使用独立的 `soc_ddr3_work` 库与 `soc_ddr3_sim.log`，不删除
   厂家例程的 `work` 库，也不修改 `RISCV.pds` 的默认顶层。
4. TB 在 CPU 写回端检查 DDR 读回值和从 DDR 执行的指令结果；超时、
   总线访问错误、数值错误都会打印 `RESULT: FAIL`。

## 测试程序如何工作

本次 CPU 的 `RESET_PC` 是 `0x8000_0000`，仿真 ROM 从该地址开始提供
下面的程序。DDR 的 CPU 地址窗口从 `0x4000_0000` 开始。

| 阶段 | 程序动作 | TB 检查点 |
| --- | --- | --- |
| 数据写入 | `x1 = 0x4000_0000`，`x2 = 42`，执行 `sw x2, 0(x1)` | 观察到 CPU 对 DDR 窗口发出写请求 |
| 数据读回 | 执行 `lw x3, 0(x1)` | `PC=0x8000_000c` 写回 `x3=42` |
| 写入指令 | 将 `addi x5,x0,0x5a`（机器码 `0x05a00293`）写入 `0x4000_0020`，将 `jal x0,0` 写入 `0x4000_0024` | DDR 中出现可取指的机器码 |
| 从 DDR 执行 | `jalr x0,0x20(x1)` 跳至 `0x4000_0020` | `PC=0x4000_0020` 写回 `x5=0x5a` |

这里既用到了 CPU **数据端口**写 DDR，也用到了 **指令端口**读 DDR。
数据端先将机器码写入 DDR，再跳转到该地址，因此不需要预先向 DDR 模型
强制灌入指令。当前没有 Cache，故这个测试不依赖 `fence.i`；以后加入
I-Cache 后需重新处理写代码与取指之间的可见性。

以写指令的地址 `0x4000_0020` 为例：数据互连减去 `DDR_BASE` 后得到
局部字节地址 `0x20`；桥将其换算成 DDR 控制器的 16 位字地址 `0x10`，
并把 32 位机器码放入 128 位用户数据拍的第 0 个槽位。`0x4000_0024`
则使用同一 128 位拍的第 1 个 32 位槽位。

## 如何复现

前提：已安装并能运行厂家 DDR3 example_design 使用的 ModelSim/Pango
仿真库；当前 IP 配置为 x16 DDR3、100 MHz 参考时钟。本机脚本中的
`LIB_DIR` 指向 `C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation`。
若 PDS 安装目录不同，先改脚本中的该路径。

在 ModelSim 命令窗口执行：

```tcl
cd D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
do soc_ddr3_sim.tcl
```

必须先 `cd` 到脚本所在目录，因为厂家的 `sim_file_list.f` 使用相对路径，
脚本也以当前目录计算工程根目录。首次运行会在当前目录创建
`soc_ddr3_work`、更新当前目录的 `modelsim.ini` 库映射，并生成
`soc_ddr3_sim.log`。它不需要修改 `RISCV.pds` 或启动 PDS 的默认
`tb_soc_top` 仿真。

检查日志：

```text
CHECK: CPU DDR store/load returned 42
RESULT: PASS soc_ddr3_top DDR store/load/fetch
Errors: 0
```

本次实际日志 `ipcore/ddr3/sim/modelsim/soc_ddr3_sim.log` 在约
**78.442 µs** 打印读回检查，在约 **79.132 µs** 打印 `RESULT: PASS`；
ModelSim 最终报告 `Errors: 0`。厂家原语/PHY 模型仍产生若干 warning，
因此不能把“零 warning”作为本步的通过条件。

## 实现的效果与尚未覆盖的内容

本步证实了：DDR 初始化完成后 CPU 才运行；CPU 的 store 能经真实 IP
写到 DDR3 模型；随后 load 能读回正确数值；CPU 还能从已写入 DDR3
的地址取指并正确写回结果。

这**不是**正式启动加载器，也不代表已经验证了板级时钟/引脚。仿真 ROM
中的测试程序是硬编码的，没有从 Flash、串口或 RK3568 搬运程序。当前
也只覆盖少量地址、单拍事务和一条 DDR 指令，尚未覆盖长程序、所有
32 位槽位、字节/半字访问、随机延迟、Cache/burst、异常或实板稳定性。

后续每完成一个独立步骤，继续在 `doc/` 下新增一篇同类记录，保留目的、
改动、复现方法、结果和边界，避免把不同验证阶段混为一谈。

后续第 2 步在同一组 TB 文件中增加了 `DDR_REGRESSION` 条件编译路径；
本页的 `do soc_ddr3_sim.tcl` **不定义该宏**，仍会运行本页原程序与检查器。
第 2 步使用独立脚本和日志，详见
`doc/ddr/DDR3集成仿真第2步_槽位字节掩码与连续取指.md`。
