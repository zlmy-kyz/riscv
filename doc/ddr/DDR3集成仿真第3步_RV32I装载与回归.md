# DDR3 集成仿真第 3 步：CPU 装载 RV32I 镜像并从 DDR 运行

日期：2026-09-28。承接第 1、2 步 DDR3 定向联仿。用户已确认片内路径无退化；本步没有把该确认写成本轮重跑的片内测试结果。

## 目的

验证 CPU 在 DDR 初始化完成后，能从片内装载源把程序和 `.data` 写入 DDR，再从 DDR 取指并运行现有 RV32I 测试。批量功能回归与完整 DDR3 IP＋物理模型联仿分别记录，避免混用 PASS 范围。

## 改动和装载顺序

- `soc_ddr3_top` 新增可覆写的 `DDR_BASE` 参数并传给 `soc_top`。默认值仍为 `0x4000_0000`；本步 TB 设 `RESET_PC=0`、`DDR_BASE=0x8000_0000`，使现有测试无需重链接即可在 DDR 运行。片内指令 ROM 和数据 RAM 分挂两路总线，均从 0 开始。
- `MyCpu_test/build_ddr_stage.py` 从每项 `*_rom.dat` 以及配套 `*_ram.dat` 生成 4096 字的仿真装载源，依据 dump/bin 确定 `.data` 范围，并从 dump 提取该项的 `tohost` 地址。`ld_st` 使用 `0x8000_2000`，其余 41 项使用 `0x8000_1000`。
- 仿真专用片内 ROM 放一段启动程序；仿真专用片内 RAM 保存测试镜像及复制长度。DDR3 训练完成后，CPU 从 ROM 启动，用 `LW/SW` 经数据总线和共享 DDR 桥把代码段、数据段逐字复制到 DDR，然后跳转 `0x8000_0000`。DDR 物理模型**没有**通过层次访问或 `$readmemh` 直接预装测试镜像。
- `source/tb_soc_ddr3_top.v` 的 `DDR_RV32I` 分支检查复制字数、DDR 取指、访问故障、实际 `tohost` 值和超时。`source/tb_soc_ddr3_rv32i_mem.v` 只替代片内 IP；DDR3 IP 和外部模型仍是厂家版本。
- `source/tb_soc_ddr3_rv32i_fast.v` 提供快速的 Pango 用户口存储模型，复用相同 CPU、互连、DDR 桥和 CPU 装载程序，供 42 项批量功能回归。这个模型不覆盖 DDR3 控制器、PHY 或物理存储器时序。

## 复现命令

在仓库根目录运行快速批量回归；脚本会生成装载源、编译一次 Icarus、逐项运行并保存日志：

```powershell
python MyCpu_test/run_ddr_rv32i_fast.py
```

仅跑指定用例可在末尾写测试名，例如 `python MyCpu_test/run_ddr_rv32i_fast.py add lb ld_st`。汇总为 `MyCpu_test/ddr_stage/fast_summary.csv`，各项原始日志为 `fast_<test>.log`。

完整 DDR3 IP＋物理模型联仿先生成全部装载源，再从厂家脚本目录执行；省略 `rv32i_cases` 时脚本会依次运行 `cases.txt` 中全部用例，每项有独立日志。运行时间较长。

```powershell
python MyCpu_test/build_ddr_stage.py
Push-Location 'D:\riscv\RISCV\ipcore\ddr3\sim\modelsim'
& 'D:\modelsim\win64pe\vsim.exe' -c -do 'set rv32i_cases {add lb}; do soc_ddr3_rv32i_sim.tcl; quit -f'
Pop-Location
```

脚本只把 `DDR_RV32I` 定义给本步仿真；原第 1、2 步仍由 `soc_ddr3_sim.tcl` 和 `soc_ddr3_regress_sim.tcl` 分别运行。
ModelSim 完全退出后，使用下列命令核对各项独立日志的唯一 `RESULT: PASS`、装载检查和末尾 `Errors: 0`；这一步生成权威的 `soc_ddr3_rv32i_verified.csv` 与文本汇总：

```powershell
python MyCpu_test/summarize_ddr_rv32i_physical.py add lb ld_st
```

## 本轮实测结果

| 范围 | 结果 | 证据 |
| --- | --- | --- |
| 快速用户口模型，42 项 | **40 PASS、2 FAIL**。`fence_i` 与 `ma_data` 是已知未实现能力，分别涉及 FENCE.I 和非对齐数据访问；其余 40 项均在 CPU 完成 DDR 装载与 DDR 取指后向各自 `tohost` 写入 1。 | `MyCpu_test/ddr_stage/fast_summary.csv` 与 42 份 `fast_<test>.log`；2026-09-28 本轮生成。 |
| 完整 DDR3 IP＋物理模型，`add` | **PASS**：CPU 复制 426 字，随后从 DDR 取指，最终 `tohost=1`，`cycles=26145`，约 339.362 µs；ModelSim `Errors: 0, Warnings: 353`。 | `ipcore/ddr3/sim/modelsim/soc_ddr3_rv32i_add.log`，2026-09-28 14:09。 |
| 完整 DDR3 IP＋物理模型，含 `.data` 的 `lb` | **PASS**：CPU 复制 273 字（含 4 个 `.data` 字），随后从 DDR 取指，最终 `tohost=1`，`cycles=16738`，约 245.292 µs；ModelSim `Errors: 0, Warnings: 353`。 | `ipcore/ddr3/sim/modelsim/soc_ddr3_rv32i_lb.log`，2026-09-28 14:28。 |
| 完整 DDR3 IP＋物理模型，长代码和独立数据段 `ld_st` | **PASS**：CPU 复制 1056 字（含 20 个 `.data` 字），从 DDR 取指，在本项的 `0x8000_2000` 写 `tohost=1`，`cycles=67203`，约 749.942 µs；ModelSim `Errors: 0, Warnings: 353`。 | `ipcore/ddr3/sim/modelsim/soc_ddr3_rv32i_ld_st.log`，2026-09-28 14:53；三项物理模型汇总见 `soc_ddr3_rv32i_verified.csv`。 |
| 原第 1 步回归 | **PASS**：`RESULT: PASS soc_ddr3_top DDR store/load/fetch`，`Errors: 0, Warnings: 353`。 | `ipcore/ddr3/sim/modelsim/soc_ddr3_sim.log`，2026-09-28 本轮重跑。 |
| 原第 2 步回归 | **PASS**：14 条 `CHECK: DDR data`，`RESULT: PASS DDR regression lanes/masks/boundary/DDR-code`，`Errors: 0, Warnings: 353`。 | `ipcore/ddr3/sim/modelsim/soc_ddr3_regress_sim.log`，2026-09-28 本轮重跑。 |

`ld_st` 的代码跨过 `0x8000_1000`；装载程序复制该地址的代码字时，不应误当成测试写 `tohost`。检查器现在只在首次 DDR 取指之后判断 `tohost`，并使用该用例 dump 里的实际地址。

本步改动了 `soc_ddr3_top` 参数转发和共用 TB，因此按 `AGENTS.md` 要求重新运行上述两条 DDR 定向脚本；本次结果均来自 2026-09-28 新日志。完整物理模型的 RV32I 批量 Tcl 补了 `onfinish stop`，使 `$finish` 返回 Tcl 循环。ModelSim 直到进程退出才把末尾 `Errors: 0` 刷到独立日志，因此循环内汇总只检查明确的 `RESULT` 和即时错误；退出后的 Python 汇总才同时验证 `RESULT` 与 `Errors: 0`。`ld_st` 运行时，修正前的循环因过早检查日志页脚曾把实际 PASS 误写成 FAIL；该误判已由退出后汇总纠正并留有原始日志可核对。

## 实现效果和未覆盖范围

当前批量功能结果表明，现有 40 项可支持 RV32I 测试在 CPU→互连→DDR 桥的快速模型路径上完成了装载、取指、访存与 `tohost` 检查；完整物理模型已有 `add`、含 `.data` 的 `lb` 和较长的 `ld_st` 三项闭环证据，退出后汇总为 **3/3 PASS**。完整物理模型尚未逐项跑完 42 项，因此不能将 40/42 写成“42 项 DDR3 物理模型联仿结果”。

片内 RAM 的初始装载源来自仿真文件，尚不是 FPGA 实板可用的 Flash、串口或 RK3568 通信装载方案；DDR3 易失，正式启动仍需确定程序来源、上电顺序和完成信号。本步也没有完成 PDS DDR 专用顶层、板级时钟/引脚、随机压力、Cache 或 `FENCE.I`。当前无 Cache、无写缓冲、单笔事务的装载程序未使用 `FENCE.I`；以后改变存储层次时必须重新设计代码写入后取指的一致性流程。
