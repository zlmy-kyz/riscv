# DDR3 集成仿真第 2 步：槽位、写掩码、跨拍与连续取指

日期：2026-09-27。接续《DDR3 集成仿真第 1 步：CPU 写、读与从 DDR3 取指》。

## 本步目的

第 1 步只验证了一个 32 位数据位置和一条 DDR 指令。本步验证 CPU 经
`soc_top`、指令/数据互连、共享 DDR 桥、Pango DDR3 IP 到 x16 DDR3
物理模型的路径，在**一个 128 位用户拍内四个 32 位槽位**、相邻拍、
部分字节写和连续从 DDR 取指时仍能保持正确。

## 做了什么

- 在 `source/tb_soc_ddr3_mem.v` 中增加 `DDR_REGRESSION` 条件编译程序。
  不定义该宏时仍使用第 1 步的原程序。
- 在 `source/tb_soc_ddr3_top.v` 中增加对应检查器：观察 CPU 数据请求
  握手时的写地址和字节使能；在写回端逐项比较 load 和 DDR 指令结果；
  检查点缺失、数值错误、总线故障或超时都会输出 `RESULT: FAIL`。
- 新增 `ipcore/ddr3/sim/modelsim/soc_ddr3_regress_sim.tcl`。它用独立的
  `soc_ddr3_regress_work` 库和 `soc_ddr3_regress_sim.log`，编译时只对
  CPU/SoC/TB 文件定义 `DDR_REGRESSION`；不修改 CPU、总线、桥或 DDR3 IP RTL。

## 测试内容及预期

DDR CPU 窗口起点为 `0x4000_0000`，以下偏移均相对该地址。

| 检查 | 程序操作 | 预期 |
| --- | --- | --- |
| 拍内四槽 | 分别向 `+0/+4/+8/+12` 写入 `0x11/0x22/0x33/0x44`，再逐个 `LW` | 四个读数各自正确；写一个槽不覆盖其他槽 |
| 相邻 128 位拍 | 向 `+16` 写入并读回 `0x55` | `+12` 和 `+16` 都正确；桥在 16 字节边界切换拍地址 |
| 字节/半字掩码 | `SB 0x80 → +5`，`SH 0x8001 → +6`，再读 `+4` | `LW(+4)=0x80018022`，`+0/+8` 邻居不变 |
| 符号扩展 | `LB/LBU(+5)`、`LH/LHU(+6)` | `0xffffff80/0x80`、`0xffff8001/0x8001` |
| 拍末字节 | `SB 0xfe → +15`，再读 `+12/+16` | `0xfe000044/0x55`；下一拍未被写坏 |
| DDR 代码 | CPU 数据端把四条指令写到 `+0x40/+0x44/+0x48/+0x4c`，随后 `JALR` 到 DDR | DDR 指令端连续取指；其中两条 `LW` 从 DDR 读数据，`ADD` 写回 `0xfe000099` |

这里所有 `LW/SH/LH` 都按各自宽度对齐。`+15` 只写一个字节；没有把
不对齐的跨 16 字节访问当作应成功的功能。当前 CPU 对不对齐访问走异常路径。

## 复现方法

前提与第 1 步相同：本机 Pango 仿真库与 DDR3 IP 配置可用，
`soc_ddr3_regress_sim.tcl` 的 `LIB_DIR` 与安装位置相符。
在 ModelSim 命令窗口执行：

```tcl
cd D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
do soc_ddr3_regress_sim.tcl
```

命令行也可在该目录运行：

```powershell
& 'D:\modelsim\win64pe\vsim.exe' -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'
```

检查 `soc_ddr3_regress_sim.log`：应有 14 条 `CHECK: DDR data`，以及
`RESULT: PASS DDR regression lanes/masks/boundary/DDR-code`；任何
`RESULT: FAIL`、编译错误或仿真错误都不能算通过。若要单独复现第 1 步，
仍运行未定义宏的 `do soc_ddr3_sim.tcl`。

## 本次结果与实现效果

2026-09-27 本机 ModelSim DE-64 10.6c 的完整 DDR3 IP＋物理模型仿真
在约 **87.712 µs** 输出
`RESULT: PASS DDR regression lanes/masks/boundary/DDR-code`。
日志中有 14 条 CPU 写回读数检查，最终 `Errors: 0, Warnings: 353`；
warning 来自与第 1 步相同的厂家原语/PHY 仿真模型。

因此，本步验证了当前 CPU/桥的单笔、单拍 32 位读写在四槽选择、部分
字节写、拍边界切换以及 DDR 取指后再访存的**这些定向场景**中正确。
此外，重新运行未定义 `DDR_REGRESSION` 的第 1 步脚本，仍在约
**79.132 µs** 输出 `RESULT: PASS soc_ddr3_top DDR store/load/fetch`，
且 `Errors: 0`；新增程序没有破坏原来的测试路径。

它尚不证明随机请求/返回延迟、长期压力、DDR 中断、板级时序和引脚、
程序装载，或 Cache/burst 的正确性。`soc_ddr3_top` 仍不是 PDS 的默认
综合顶层，不能将此仿真 PASS 等同于上板成功。
