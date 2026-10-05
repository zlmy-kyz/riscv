# RISCV FPGA 工程

本仓库包含面向 **RK3568_MES2L100H / PG2L100H-6IFBG484** 板卡的五级流水 RV32I CPU、SoC、Pango DDR3 集成工程、支持轮询与 RX 中断的 UART，以及启动镜像和仿真入口。PDS 工程为 [`RISCV.pds`](RISCV.pds)，当前板级顶层为 `board_top`。

**当前建议将整个仓库放在 `D:\riscv\RISCV`。** 部分脚本、IP 初始化配置和仿真库映射仍使用本机绝对路径；打开工程之后还需完成构建和下载。

## 1. 文件结构

```text
RISCV/
├─ README.md                           # 本文：结构、精简范围、使用步骤
├─ RISCV.pds                           # PDS 主工程，设计顶层 board_top
├─ myriscv/                            # CPU、SoC 与板级 RTL
│  ├─ board_top.v                       # 板级引脚、差分时钟与 KEY0 消抖
│  ├─ soc_ddr3_top.v                    # SoC、DDR3 IP 和 LED 状态逻辑
│  ├─ soc_top.v                         # CPU、互连、ROM/RAM、MMIO、UART、DDR 桥
│  ├─ uart_tx.v / uart_rx.v             # 115200 8N1 收发
│  ├─ uart_rx_fifo.v / uart_mmio.v      # RX FIFO、轮询 MMIO、RX 电平 IRQ
│  ├─ mycpu_sync.v                      # 五级流水 CPU
│  └─ ...                              # CSR、ALU、互连、适配器、DDR 桥等
├─ constraint_check/
│  └─ temp_constraint_file.fdc          # 当前主工程实际使用的引脚/时钟约束
├─ ipcore/                             # PDS 生成的 IP 配置与构建/仿真源码
│  ├─ inst_rom/                        # 16 KiB 启动 ROM
│  ├─ data_ram/                        # 16 KiB 数据 RAM / DDR 程序装载源
│  └─ ddr3/                            # DDR3 配置、RTL、仿真源码与物理模型
├─ MyCpu_test/                         # 测试程序、镜像生成和回归脚本
│  ├─ board_selftest/                  # 当前板级启动与 DDR 自检镜像
│  ├─ dat/、dump/、bin/、hex/          # RV32I 测试与镜像转换输入
│  ├─ ddr_stage/                      # 独立 DDR RV32I 回归镜像/清单/IP
│  ├─ ddr_selftest/                   # 独立旧布局自检镜像/清单/IP
│  └─ *.py                            # 镜像生成、IP 准备、仿真运行与汇总
├─ source/                             # CPU/SoC/总线/DDR/复位/LED 测试台
├─ sim/                                # 仿真脚本、板级测试台和历史验证记录
│  ├─ board_main_selftest/             # 当前 PDS 主仿真入口
│  │  ├─ compile.tcl
│  │  ├─ run.tcl
│  │  └─ tb_board_top_selftest.v
│  ├─ compile_ddr3_physical_model.tcl  # 生成并编译派生 DDR 物理模型
│  ├─ behav/run_behav.bat              # 当前行为仿真启动脚本
│  ├─ uart_tx/、uart_rx/、uart_mmio/   # 独立 UART 与真实 CPU 轮询验证
│  ├─ uart_irq/                        # CPU IRQ 验收、真实引脚 RX→ISR→MRET
│  └─ ...                             # 独立回归、候选工程与历史记录
├─ difftest/                           # 仅公开 UART CPU 测试所需的三个依赖
│  ├─ golden/rvtool.py                 # Python 汇编工具 / 指令级参考工具
│  └─ model/inst_rom.v、data_ram.v     # 仿真存储模型
├─ doc/                                # 当前公开的结构、UART 阶段记录与图示
│  ├─ SoC结构说明_2026-10-04.md
│  ├─ AI加速多方案比较与推荐实施方案.md
│  └─ UART 阶段1/2/3记录、SoC PNG/SVG 和绘图脚本
├─ AGENTS.md                           # 工程长期约定和协作入口
├─ .gitignore                          # 构建产物与本地资料的忽略规则
├─ impl.tcl                            # PDS 累计操作记录，含旧路径
├─ multiseed_summary.csv                # 已有实现结果记录
└─ zongxian.md                          # 总线学习笔记
```

`sim/` 中保留了一些历史实验、备份和日志。使用当前工程时，以 `RISCV.pds`、主 RTL、主 IP、`board_selftest/` 和 `board_main_selftest/` 为入口；根目录 `impl.tcl` 不作为从头重建工程的入口。

## 2. 仓库已精简的内容

当前 GitHub 版本聚焦于上板和仿真输入，以下内容已从当前版本移除，并通过 `.gitignore` 排除：

- `.workbuddy/`：本地开发记录与旧实验。
- `bug/` 和大部分 `difftest/`：本地问题记录与差分验证工程；仅保留 UART CPU 测试所需的汇编工具和两份存储模型。
- `constraints/`、`fdc/`、`ip_backup/`：旧约束、约束备份和 IP 备份。
- `rv32i_table.txt` 及 `doc/` 中未选中的文档。

PDS 构建数据库、ModelSim 编译库、`.vvp`、波形、Python 缓存和部分临时输出也不作为日常源码上传，可由工具重新生成。仓库仍保留部分代表日志、历史候选及备份，后续可继续整理。

**必须保留 `constraint_check/temp_constraint_file.fdc`。** 虽然文件名含 `temp`，它是当前 `RISCV.pds` 的实际约束输入。IP 中的 `*_init_param.v` 等生成文件也参与构建，不能统一当作缓存删除。

完整克隆包含当前公开的文件；GitHub 历史提交中仍可能有旧资料。本地已有开发资料可自行保留，新克隆只包含 `difftest/golden/rvtool.py` 和 `difftest/model/{inst_rom.v,data_ram.v}`，不包含完整旧差分回归工程。`MyCpu_test/check_board_top.py` 是依赖旧 `constraints/`、`fdc/` 的历史审计脚本，不作为当前使用步骤。

## 3. 工具与目录准备

主要使用 Windows。上板需要 PDS 与板卡适用下载器；仿真和镜像修改再按需安装其他工具。

| 用途 | 参考工具与当前路径 |
| --- | --- |
| 构建、生成烧录文件、下载 | Pango PDS `2022.2-SP6.4`；`C:\pango\PDS_2022.2-SP6.4` |
| 完整 DDR IP + 物理模型仿真 | ModelSim DE-64 `10.6c`；`D:\modelsim\win64pe` |
| 快速 RTL 回归 | Icarus Verilog；`D:\iverilog\bin\iverilog.exe`、`vvp.exe` |
| 镜像生成与回归运行 | Python 3；`python` 命令可用 |
| 主板级仿真的预编译库 | `D:\modelsim\pango_sim_libraries`，需按 PDS 提供的仿真库流程准备并映射 |

克隆到当前脚本预期的位置：

```powershell
git clone https://github.com/zlmy-kyz/riscv.git D:\riscv\RISCV
Set-Location D:\riscv\RISCV
```

如果下载 ZIP，将解压后的工程目录命名为 `RISCV`，直接放到 `D:\riscv`。最终应能找到 `D:\riscv\RISCV\RISCV.pds`，避免多套一层目录。

如果使用其他路径，请先修改实际依赖的位置：

- `sim/board_main_selftest/*.tcl`、`sim/behav/run_behav.bat` 及相关 Python 脚本中的工程/工具路径。
- ROM/RAM `.idf` 和生成包装模块中的 `INIT_FILE`；修改初始化配置后用匹配镜像重新生成相关 IP，核对初始化参数。
- DDR Tcl 的 `LIB_DIR`、`sim_file_list.f` 中的 PDS 安装路径，以及 `modelsim.ini`/`vmap` 的库映射。
- PDS 的仿真器和 `compiled_lib_location` 设置，以及快速回归脚本中的 Icarus 路径。

主板级仿真依赖 `usim`、`adc_e2`、`ddc_e2`、`dll_e2`、`hsstlp_lane`、`hsstlp_pll`、`iolhr_dft`、`ipal_e1`、`ipal_e2`、`iserdes_e2`、`oserdes_e2`、`pciegen2` 库。应通过匹配 PDS 版本准备这些库；仅安装 ModelSim、加入工具 PATH 不等于已经完成库配置。

## 4. 打开工程与上板

1. 使用 PDS 打开 `RISCV.pds`。
2. 核对器件为 `PG2L100H`、封装 `FBG484`、速度等级 `-6`，设计顶层为 `board_top`。
3. 确认约束入口为 `constraint_check/temp_constraint_file.fdc`，三块 IP 为 `inst_rom`、`data_ram`、`ddr3`。
4. 首次克隆或清理构建目录后，从头运行：**Compile → Synthesize → Device Map → Place & Route → Report Timing → Generate Bitstream**。仓库不包含主工程构建缓存，不能仅凭 PDS 显示的旧完成状态判断当前文件可用。
5. 检查构建错误和时序结果，然后用 PDS 下载工具连接对应板卡下载器，选择本次新生成的 `generate_bitstream/board_top.sbit` 下载。
6. 按下并释放 KEY0，观察启动、自检与 LED。

板级层次为 `board_top → soc_ddr3_top → soc_top → mycpu_sync`。参考时钟为 125 MHz，当前 DDR IP 用户域 `core_clk` 为 93.75 MHz。DDR 完成初始化并锁定后才释放 SoC 复位。

约束面向上述板卡；换板或修订版时应按实际连线、Bank 供电和时钟核对。若生成工具提示 `SCBV has not been set`，按实际 PCB 配置 Bank 电压填写，不能根据其他 IO 标准猜测。

`sim/board_boot_fix_20261003/before/board_top.sbit` 是旧备份；归档自检 `.sbit` 也不自动对应当前源码。日常使用优先从当前工程重新构建，不按扩展名随意选择历史文件。

### 启动程序与 LED

当前主 IP 的初始化输入为：

- `MyCpu_test/board_selftest/boot_rom.dat`：CPU 从地址 0 执行的 ROM 装载程序。
- `MyCpu_test/board_selftest/ddr_selftest.dat`：片内 RAM 中预置的 DDR 自检程序。

CPU 执行 ROM 装载程序，将当前 245 字自检代码复制到 `0x40000000`，然后跳转到 DDR 执行。DDR 易失，每次复位后的启动由 CPU 完成装载。

| LED / 引脚 | 含义 |
| --- | --- |
| J16 / `led_clk_alive` | 约 1 Hz 心跳，表示用户域时钟运行 |
| M17 / `led_ddr_ready` | DDR 初始化/锁定后，SoC 已解除复位 |
| K17 / `led_selftest` | IDLE 灭；RUN 约 1 Hz 慢闪；PASS 常亮；FAIL 或超时约 4 Hz 快闪 |

KEY0/M15 按下立即复位，释放稳定 20 ms 后允许继续启动。正常自检较快，RUN 慢闪可能肉眼看不到；通过后应看到 J16 心跳，M17、K17 常亮。重复复位可检查启动是否稳定。K17 快闪仅表示失败或超时，需要进一步区分原因。

## 5. 当前工程仿真

### 5.1 主板级完整自检（ModelSim）

测试台：`tb_board_top_selftest`。使用实际 ROM/RAM IP、DDR IP 和物理模型，CPU 自行装载 DDR；包含板级时钟、启动和自检状态观察。

配置好工具与库后，可从 PDS 仿真按钮运行。项目中的自定义编译/运行入口应为：

```text
sim/board_main_selftest/compile.tcl
sim/board_main_selftest/run.tcl
```

也可在 ModelSim Transcript 中执行：

```tcl
cd D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
do D:/riscv/RISCV/sim/board_main_selftest/compile.tcl
do D:/riscv/RISCV/sim/board_main_selftest/run.tcl
```

主仿真日志为 `sim/board_main_selftest/physical.log`。通过应同时看到以下结果，并确认无 `RESULT: FAIL`、`** Error`、`** Fatal`，编译与仿真报告均为 `Errors: 0`：

```text
CHECK: ddr_selftest CPU copied 245 words then fetched from DDR
CHECK: MMIO selftest RUN
CHECK: MMIO selftest PASS LED=1
RESULT: PASS ddr_selftest DDR RV32I tohost=1 ...
```

厂家原语 warning 不要求为零。该 TB 将按键消抖计数缩短以节省时间，实际默认 20 ms 由单独消抖测试覆盖。

### 5.2 两条完整 DDR 定向仿真（ModelSim）

```tcl
cd D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
do soc_ddr3_sim.tcl
do soc_ddr3_regress_sim.tcl
```

两个脚本分别检查 DDR 读写/取指，以及槽位、字节掩码、边界和 DDR 代码执行等行为，生成独立库与 `soc_ddr3_sim.log`、`soc_ddr3_regress_sim.log`。通过条件为相应 `RESULT: PASS`、无 `RESULT: FAIL`，编译与运行 `Errors: 0`。

执行目录不可省略：厂家 `sim_file_list.f` 使用相对路径。若已清理编译库，重新执行上述完整脚本即可编译；主板级自检则先运行 `compile.tcl`，再运行 `run.tcl`。

### 5.3 快速回归（Python + Icarus）

在仓库根目录执行，先核对脚本内 Icarus 路径：

```powershell
python MyCpu_test/run_led_status.py
python MyCpu_test/run_key_reset_debounce.py
python MyCpu_test/run_ddr_selftest_fast.py --base 0x40000000
python MyCpu_test/run_ddr_rv32i_fast.py add lb ld_st
```

第三条使用当前板级地址；自检包含三个正常镜像和一个故意注入错误的镜像，预期汇总为 `TOTAL 4/4 EXPECTED`，错误镜像明确报告 FAIL 才符合该用例预期。

快速回归使用行为模型，适合改动后的快速检查，完整 DDR 物理联仿仍需运行。RV32I 独立回归使用历史 `0x80000000` TB 布局，与当前板级 `0x40000000` 布局区分。

全部 RV32I 镜像运行入口为：

```powershell
python MyCpu_test/run_ddr_rv32i_fast.py
```

已有记录为 40/42，`fence_i`、`ma_data` 是既有覆盖缺口；不能把全量回归称为全部通过。新运行以本次输出与 `MyCpu_test/ddr_stage/fast_summary.csv` 为准，旧日志中的 PASS 不代表新代码已验证。

### 5.4 UART 独立验证与真实 CPU 轮询（ModelSim）

UART 参数为 93.75 MHz、115200 8N1，整数分频 814 clk/bit；实际波特率约 115171.990，误差 -0.024314%。下列 UART 测试不依赖厂家仿真库，CPU 测试使用仓库内行为存储模型。

```powershell
Set-Location D:/riscv/RISCV/sim/uart_tx
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_tx.tcl'
Set-Location D:/riscv/RISCV/sim/uart_rx
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_rx.tcl'
Set-Location D:/riscv/RISCV/sim/uart_mmio
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_uart_mmio.tcl'
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_bus_regression.tcl'

Set-Location D:/riscv/RISCV
python difftest/golden/rvtool.py asm sim/uart_mmio/uart_poll.S sim/uart_mmio/cpu_image
Set-Location sim/uart_mmio
& 'D:/modelsim/win64pe/vsim.exe' -c -do 'do run_soc_uart_cpu.tcl'
```

TX/RX/MMIO/CPU UART 测试通过条件为自动串行解码及结果比较 PASS、无 FAIL、Errors: 0 / Warnings: 0。旧总线 TB 的未用端口 warning 与上述 UART 测试区分。CPU 程序轮询 STATUS，通过 SB/SH/SW 发送 Hello、LBU/LB/LHU/LH/LW 接收引脚注入的 Hello；不会替换板级启动镜像。CPU 仿真 hex/listing、编译库和波形由命令重新生成，不上传。

独立 UART PDS 综合入口为 `sim/uart_mmio/uart_synth/uart_synth.pds`，只包含 UART 模块，无 DDR IP 生成；综合 warning 与板级时序未覆盖范围见阶段 3 记录。修改共享互连后仍须执行第 5.2 节的两条完整 DDR 测试。

### 5.5 CPU IRQ 验收与真实 UART RX 中断（Icarus）

在根目录执行，沿用仓库内汇编器、存储模型及 Icarus，不调用 PDS：

```powershell
python sim/uart_irq/run_irq.py --stage cpu
python sim/uart_irq/run_irq.py --stage cpu --ddr-code
python sim/uart_irq/run_irq.py --stage uart
python sim/uart_irq/run_irq.py --stage uart --ddr-code
```

CPU 阶段覆盖 16 个中断场景，两种取指方式分别自动核对退休 PC、trap CSR、MRET、访存请求/响应/退休及实际 DDR 写次数。UART 阶段用真实 RX 串行引脚注入 10 字节，核对 ISR、FIFO、IRQ 撤销和 DDR/MMIO 等待。产物仅在忽略的 `sim/uart_irq/build/`；`--case 5 --wave --ddr-code` 保存单个 CPU 用例波形，不改变板级初始化。复现详情见 [中断验收记录](doc/CPU中断验收与UART_RX_IRQ_2026-10-05.md)。

## 6. 修改程序或 RTL

修改 CPU、互连、DDR 桥或顶层后，按影响范围执行快速回归、主板级自检和两条完整 DDR 定向；需要上板时重新完整构建并下载新烧录文件。

只使用已有镜像上板时，不需要重新运行镜像生成器。需要重新生成当前板级启动/自检镜像及两块片内 IP 时，在确认工具路径后执行：

```powershell
python MyCpu_test/prepare_board_selftest_ip.py
python MyCpu_test/run_ddr_selftest_fast.py --base 0x40000000
python MyCpu_test/prepare_board_selftest_ip.py --promote
python MyCpu_test/run_board_top_physical.py
```

不带 `--promote` 时生成并核对隔离候选 IP；`--promote` 在两块候选检查通过后更新主 `ipcore/inst_rom`、`ipcore/data_ram`。该流程会生成文件并在 promote 时修改主 IP，之后需重新生成烧录文件。DDR IP 不由这个脚本重新生成。

装载源 RAM 为 16 KiB，尾部保留清单。换程序时应统一装载长度、链接地址、跳转入口和诊断区；仅修改 `.dat` 不保证生成的 IP 初始化内容同步。不要把现有汇编自检生成器当作通用 C 程序装载工具。

## 7. 地址与当前能力

| 地址范围 | 用途 |
| --- | --- |
| `0x00000000–0x00003FFF`，指令总线 | 16 KiB 启动 ROM |
| `0x00000000–0x00003FFF`，数据总线 | 独立的 16 KiB RAM，两条分离总线允许同基址 |
| `0x10000000–0x10000FFF` | MMIO；`0x10000010` 为 TEST_STATUS：0/1/2/3 = IDLE/RUN/PASS/FAIL |
| `0x10001000–0x1000100F` | UART MMIO：TX_DATA / RX_DATA / STATUS / CONTROL，仅数据总线 |
| `0x40000000–0x5FFFFFFF` | 板级 DDR 窗口，512 MiB |

UART 已接入 `soc_top` 数据互连，支持轮询和可使能 RX 电平中断；TX/RX 已通过 `soc_ddr3_top` 引出至 `board_top.uart_tx/uart_rx`。当前工作树有外部会话保存的 TX=AA20/RX=AA21 约束，本轮未核验原理图依据或 USB-TTL 实板效果。当前板级启动镜像仍为 DDR 自检，没有 UART 输出；单字符 H 的候选程序及 DebugCore 准备见下方文档，尚未更新主 ROM/RAM 初始化。`board_top` 的三个外部 IRQ 输入仍接 0，`soc_top` 内部将 UART IRQ 与原 external 输入 OR 后送 CPU。CONTROL bit8/9 分别写 1 使能/禁用 RX IRQ，STATUS bit6/7 为使能/实际 IRQ；默认禁用，FIFO 读空自动撤销，旧低位 W1C 保留。当前没有 Cache、DMA、CLINT、PLIC 或 RK3568 通信接口。**CoreMark 尚未移植，当前仓库没有可运行的 CoreMark 构建入口。** AI 文档描述后续方案，不能视为已实现硬件能力。

## 8. 常见问题

| 现象 | 优先检查 |
| --- | --- |
| PDS 找不到源文件或初始化文件 | 目录是否为 `D:\riscv\RISCV`，IP INIT_FILE 是否有效 |
| ModelSim 找不到库/模块 | Pango 预编译库与 `vmap`/`modelsim.ini`，PDS 安装路径，是否先执行编译 |
| 厂家文件列表找不到相对路径 | 是否在 `ipcore/ddr3/sim/modelsim` 目录执行 |
| 修改 `.dat` 后表现未变化 | IP 初始化参数是否重新生成，是否重新构建/下载 |
| M17 不亮 | DDR 参考时钟、复位、初始化、PLL 锁定与板卡/IP 配置 |
| M17 亮但 K17 快闪 | 下载版本、主 ROM/RAM 镜像、DDR 地址/装载流程、MMIO 上报及 5 秒超时 |
| 旧引脚审计脚本找不到 constraints/fdc | 它是历史入口；当前工程使用 `constraint_check/temp_constraint_file.fdc` |

## 9. 文档

- [SoC 结构说明](doc/SoC结构说明_2026-10-04.md)：模块层次、总线、地址、时钟、复位和启动流程。
- [阶段 3 SoC 总览图](doc/SoC结构图_UART阶段3_2026-10-05.png) / [SVG 原图](doc/SoC结构图_UART阶段3_2026-10-05.svg)：顶层 UART 接线前的历史快照；当前 TX/RX 已引出至 board_top。`python doc/draw_soc_uart_stage3.py` 可重绘该快照，需要 Pillow 和 Windows 微软雅黑字体。
- [UART 阶段 1](doc/UART发送模块阶段1_2026-10-05.md)、[阶段 2](doc/UART接收FIFO与环回阶段2_2026-10-05.md)、[阶段 3](doc/UART_MMIO与CPU轮询阶段3_2026-10-05.md)：独立收发、FIFO/loopback、MMIO/真实 CPU 及回归证据。
- [UART 顶层接入与 DebugCore 准备](doc/UART顶层接入与DebugCore准备_2026-10-05.md)：串行端口路径、候选 Probe、单字符 H、手动 PDS 步骤及启动镜像停止条件。
- [CPU 中断验收与 UART RX IRQ](doc/CPU中断验收与UART_RX_IRQ_2026-10-05.md)：32 项 CPU IRQ 验收、真实串行 ISR 闭环、DDR/MMIO 精确访存及回归。
- [AI 加速多方案比较与推荐实施方案](doc/AI加速多方案比较与推荐实施方案.md)：后续开发方向及方案比较。

以上文档和部分验证记录带有日期，以实际 RTL、PDS 和 IP 配置为准。DDR 初始化成功、仿真通过、时序通过和实板验证分别记录。当前自检覆盖指定区域与花样，不代表整块 DDR 的长期稳定性验收。
