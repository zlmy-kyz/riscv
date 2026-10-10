# PDS 调用 ModelSim 仿真真实片内 ROM/RAM 与 DDR3

记录日期：2026-09-28；PDS 按钮复核日期：2026-09-29。本步骤为 PDS 行为仿真准备专用入口，验证 CPU → 两路总线 → **Pango 生成的片内 ROM/RAM IP** → DDR 桥 → DDR3 IP → DDR3 物理模型。下文首先记录 `add` 阶段；2026-09-29 的 `lb`、`ld_st` 结果和当前配置见文末增量记录。

## 目的和前提

- 保留真实 `ipcore/inst_rom/inst_rom.v`、`ipcore/data_ram/data_ram.v`，不使用 `source/tb_soc_ddr3_mem.v` 或 `source/tb_soc_ddr3_rv32i_mem.v` 替代片内存储。
- 用户已在 PDS 重新生成两个片内 IP。核对到 ROM `INIT_FILE=D:/riscv/RISCV/MyCpu_test/ddr_stage/boot_rom.dat`，RAM `INIT_FILE=D:/riscv/RISCV/MyCpu_test/ddr_stage/add.dat`。
- 本轮程序固定为 `add`，期望 CPU 从片内 RAM 向 DDR 复制 426 个 32 位字，跳转 DDR 执行，并写 `0x80001000` 的 `tohost=1`。
- 仍使用项目原有 `myriscv/soc_ddr3_top.v` 和 Pango `ddr3` IP。PDS 综合顶层不因本步骤自动切换。

## 本步骤新增文件

| 文件 | 用途 |
| --- | --- |
| `source/tb_soc_ddr3_pds_ip.v` | DDR3 全链 TB；从现有 `tb_soc_ddr3_top.v` 派生，去掉对仿真 RAM `words[]` 的依赖，以 `+EXPECTED_WRITES` 核对装载数。 |
| `sim/pds_ddr_ip_compile.tcl` | 编译厂家 DDR3 仿真文件、真实片内 ROM/RAM IP、CPU/SoC 和专用 TB，建立独立 ModelSim 库 `sim/pds_ddr_ip_work`。 |
| `sim/pds_ddr_ip_run.tcl` | 运行 `add`，生成 `sim/pds_ddr_ip_add.log`。 |

DDR3 采用 `ipcore/ddr3/sim/modelsim/sim_file_list.f` 的仿真源，不编译 `ipcore/ddr3/rtl/*.vp` 综合加密源。`sim_file_list.f` 内有相对路径，两份脚本会先切到厂家 `sim/modelsim` 目录。脚本中的 PDS 仿真库路径和 ModelSim 库路径与本机安装绑定，换机器须核对。

## 本机独立复现

在 PowerShell 执行：

```powershell
Push-Location 'D:\riscv\RISCV\ipcore\ddr3\sim\modelsim'
& 'D:\modelsim\win64pe\vsim.exe' -c -do 'do D:/riscv/RISCV/sim/pds_ddr_ip_compile.tcl; quit -f'
& 'D:\modelsim\win64pe\vsim.exe' -c -do 'do D:/riscv/RISCV/sim/pds_ddr_ip_run.tcl; quit -f'
Pop-Location
```

2026-09-28 实测：编译厂家 DDR3 文件为 `Errors: 0, Warnings: 6`；编译 CPU、真实 ROM/RAM IP、TB 为 `Errors: 0, Warnings: 0`。`sim/pds_ddr_ip_add.log` 显示加载 `pds_ddr_ip_work.inst_rom`、`pds_ddr_ip_work.data_ram` 和 `pds_ddr_ip_work.ddr3_mem`；随后输出：

```text
CHECK: add CPU copied 426 words then fetched from DDR
RESULT: PASS add DDR RV32I tohost=1 cycles=26145
Errors: 0, Warnings: 353
```

可用 `rg -n 'Loading .*\.(inst_rom|data_ram|ddr3_mem)|CHECK:|RESULT:|Errors:' sim/pds_ddr_ip_add.log` 复核。该日志没有 `RESULT: FAIL`。厂家原语 warning 未要求为零。

## PDS GUI 一键运行设置与实测

PDS 安装目录 `C:/pango/PDS_2022.2-SP6.4/doc/Simulation_User_Guide.pdf` 的 ModelSim 仿真设置说明支持 `Modelsim.simulate.custom_do`（自定义编译脚本）和 `Modelsim.simulate.custom_udo`（自定义仿真脚本），入口为 **Project → Project Setting → Simulation**。不要直接改 PDS 自动生成的 `sim/behav/run_behav_*.tcl`，下次运行会覆盖。

1. 保留专用 TB 文件 `D:/riscv/RISCV/source/tb_soc_ddr3_pds_ip.v`。当前 `RISCV.pds` 的 **Simulation** 树列出的是 `tb_soc_ddr3_top`，但下述自定义运行 Tcl 会明确选择 `tb_soc_ddr3_pds_ip`；按钮实际运行哪个 TB，应核对生成的 `run_behav.bat`、运行 Tcl 和 ModelSim 日志。
2. 打开 **Project → Project Setting → Simulation**，确认仿真器是 ModelSim，设置 `Modelsim.simulate.custom_do` 为 `D:/riscv/RISCV/sim/pds_ddr_ip_compile.tcl`，`Modelsim.simulate.custom_udo` 为 `D:/riscv/RISCV/sim/pds_ddr_ip_run.tcl`；保存设置。
3. 点击 **Run Behavior Simulation**。在 ModelSim Transcript 中确认实际执行了这两份脚本，再看 `sim/pds_ddr_ip_add.log` 最后一次运行的 `RESULT: PASS`、没有 `RESULT: FAIL`、`Errors: 0`。

2026-09-29 00:06，PDS 生成的 `sim/behav/run_behav_simulate.log` 显示先后执行上述两份 Tcl，编译厂家文件和 CPU/IP/TB 均为 `Errors: 0`。本次运行生成的 `sim/pds_ddr_ip_add.log` 于 00:16:15 结束，包含 `CHECK: add CPU copied 426 words then fetched from DDR`、`RESULT: PASS add DDR RV32I tohost=1 cycles=26145`、末尾 `Errors: 0, Warnings: 353`；耗时 9 分 26 秒。这是 **PDS 按钮入口的真实片内 IP＋DDR3 物理模型 add PASS**。

## `add` 阶段的未覆盖范围（2026-09-29 00:16）

- 截至本段记录时，PDS 按钮的真实片内 IP＋DDR3 物理模型只验证 `add` 一项。切换其它程序时，必须把新 `<test>.dat` 设为片内 `data_ram` 的初始化文件并重新生成该 IP，同时更新运行脚本中的 `TEST`、`TOHOST`、`EXPECTED_WRITES` 和日志名；启动程序不变时，`boot_rom.dat` 与 `inst_rom` 不需切换。不能沿用 `add` 的 PASS 标签。
- 尚未覆盖实板 DDR3、自检、程序装载接口及掉电后启动顺序。
- 本步骤只新增专用 TB 和 Tcl；未修改共用 CPU、互连、桥、DDR 顶层或原有 TB。原有两条 DDR 定向脚本的历史 PASS 不算作本次新运行。

## 2026-09-28：TB 时间精度提速试验

目的：验证把专用 TB 的 `` `timescale 1ns / 10fs `` 改为 `` `timescale 1ns / 1ps `` 是否缩短完整 DDR3 物理模型的墙钟耗时。DDR3 物理模型本身采用 `1ps / 1ps`，TB 中最小的显式延时 `#0.15` 仍可用 1 ps 精度准确表示。

只临时修改 `source/tb_soc_ddr3_pds_ip.v` 首行；用上节相同的 ModelSim 编译、运行命令重测 `add`。编译为 `Errors: 0`，运行输出 `CHECK: add CPU copied 426 words then fetched from DDR`、`RESULT: PASS add DDR RV32I tohost=1 cycles=26145`，末尾 `Errors: 0, Warnings: 353`。本次耗时 **16 分 20 秒**，1 ps 版本日志另存为 `sim/pds_ddr_ip_add_timescale_1ps.log`；之前 10 fs 版本同项独立运行耗时约 **8 分 51 秒**。两次不是受控性能基准，不能证明精度改动造成了减速，但没有观察到提速，所以已把专用 TB 恢复为 `1ns / 10fs`，并重新编译。此后 PDS 按钮使用恢复后的 TB。

本试验只覆盖 `add` 一项和命令行模式；没有证明 PDS 图形界面的墙钟耗时。`ModelSim.simulate.runtime` 的单位变化只改时间写法；自定义运行脚本中的 `run 5ms` 是最长仿真时长，不决定到达 PASS 所需的计算量。

## 2026-09-29：后续用例、复位/争用与当前入口

本节更新的是上述 `add` 阶段后的状态；原有 `add` 的 IP 镜像、脚本参数及“仅验证一项”描述是当时的记录，不是当前配置。`lb` 和 `ld_st` 均由 PDS **Run Behavior Simulation** 按钮调用同一专用编译/运行 Tcl；切换用例时在 PDS 重新生成 `data_ram` IP，并同步更新 `+TEST`、`+TOHOST`、`+EXPECTED_WRITES` 和独立日志名。复现细节分别见 [lb 记录](PDS真实片内IP_lb测试准备_2026-09-29.md) 和 [ld_st 记录](PDS真实片内IP_ld_st测试准备_2026-09-29.md)。

| 用例 | 片内 `data_ram` 初始化 | 复制字数 | 结果日志 | 已核对结果 |
| --- | --- | ---: | --- | --- |
| `add` | `add.dat` | 426 | `sim/pds_ddr_ip_add.log` | `tohost=1`、`RESULT: PASS`、`Errors: 0` |
| `lb` | `lb.dat` | 273 | `sim/pds_ddr_ip_lb.log` | `tohost=1`、`RESULT: PASS`、`Errors: 0` |
| `ld_st` | `ld_st.dat` | 1056 | `sim/pds_ddr_ip_ld_st.log` | `tohost=1`、`RESULT: PASS`、`Errors: 0` |

当前生成的 `ipcore/inst_rom/inst_rom.v` 指向 `MyCpu_test/ddr_stage/boot_rom.dat`，`ipcore/data_ram/data_ram.v` 指向 `MyCpu_test/ddr_stage/ld_st.dat`。`sim/pds_ddr_ip_run.tcl` 当前为 `+TEST=ld_st +TOHOST=80002000 +EXPECTED_WRITES=1056`，结果写入 `sim/pds_ddr_ip_ld_st.log`。`RISCV.pds` 设计树选中 `soc_ddr3_top`，仿真树列 `tb_soc_ddr3_top`；PDS 按钮生成的 `sim/behav/run_behav.bat` 实际调用本页两份自定义 Tcl，ModelSim 由运行 Tcl 选择 `tb_soc_ddr3_pds_ip`。核对按钮实际测试时，以生成脚本、运行 Tcl 与日志为准。

在同一真实片内 IP＋DDR3 物理模型条件下，`sim/pds_ddr_reset_ld_st.log` 记录装载中外部复位、DDR 再训练、CPU 重新复制 1056 字并完成；`sim/pds_ddr_contention.log` 记录 TB 向已译码 DDR 入口注入两路读，数据优先且都读回正确值；两项均 PASS、`Errors: 0`。此外 `sim/pds_ddr_cpu_overlap_ld_st.log` 在 TB 延后一次取指 ready 两拍后，观察到 **CPU 发出的**两路 DDR 请求同时有效，并完成 `ld_st`，`Errors: 0`。自然物理时序下的 `ld_st` 重叠周期为 0，不能把反压测试说成自然重叠。目的、命令、实测效果和边界见 [复位与注入争用记录](../ddr/DDR3复位与指令数据争用验证_2026-09-29.md) 与 [CPU 原生争用记录](../ddr/CPU原生DDR指令数据争用验证_2026-09-29.md)。

目前仍无其它 39 项 RV32I 的真实片内 IP＋物理模型逐项结果，也无综合/时序或实板验证。下一阶段需核对板上 DDR3 器件、参考时钟、复位及引脚约束，确定板上程序来源与可见输出，然后执行最小 DDR 写入/读回自检。板级结果应另立文档记录，不能沿用仿真 PASS。
