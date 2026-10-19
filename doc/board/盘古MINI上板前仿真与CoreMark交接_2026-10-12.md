# 盘古 MINI-(200H) 上板前仿真与 CoreMark 交接（2026-10-12）

后续用户已完成MINI新位流与实际DDR测试，Hello及固定120次P/V正确性已独立核验，时间6.33/6.51秒不足10秒只作性能对比；新PDS报告在Pre-silicon模型和已有约束下满足。详见[实板性能与时序分析](../cpu/MINI200H换板实板性能与时序分析_2026-10-12.md)。以下“MINI实板未运行/PDS待用户验证”均为上板前记录。

## 本次输入

- 板级目标：PG2L200H-6IFBG676；两片 x16 DDR3 构成 x32，按 1 GiB 地址窗口 `0x4000_0000–0x7fff_ffff`。PDS 顶层 `board_top`，三个新 IP 为 `inst_rom`、`data_ram`、`ddr3`。
- ROM/RAM IDF 分别指向 `tests/uart_loader/candidates/verify_run_hello/build/loader_rom.dat` 与 `loader_ram.dat`。SHA-256 分别为 `53a2d9912e85b6b5c90768fb0422be6cde8d5bdab37ef07b7eabfb065b76cea1` 和 `986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975`。
- DDR IDF：`MEM_DQ_WIDTH=32`、`CTRL_ADDR_WIDTH=28`、`AXI_REDUCED_EN=true`、`USER_PINS_CON_EN=true`。生成文件及板级 FDC 的 DDR 71 个球位一致。

## 已完成的关键测试

| 测试 | 复现命令或证据 | 实测结果与范围 |
| --- | --- | --- |
| FDC 球位 | `python sim/mini_board_migration/check_ddr_pinmap.py` | `RESULT: PASS all 71 DDR pin locations match`；有效板级约束无重复属性或球位冲突。 |
| 板级顶层静态编译 | `iverilog -g2012 -i -tnull -s board_top -I myriscv -I ipcore/ddr3`，输入 `myriscv/*.v` 与三 IP 顶层 | 退出码 0；一条 `ddr_init_done` 被转为 inout 的 Icarus 提示。仅检语法与端口，不是 PDS 综合/时序。 |
| x32 DDR 桥 | `iverilog -g2012 -s tb_ddr_bridge_x32 -o sim/mini_board_migration/tb_ddr_bridge_x32.vvp sim/mini_board_migration/tb_ddr_bridge_x32.v myriscv/dual_sram_to_pango_ddr_bridge.v`；`vvp sim/mini_board_migration/tb_ddr_bridge_x32.vvp` | PASS；覆盖 256 位拍槽位、写掩码、缓存失效、512 MiB 分界与 1 GiB 末地址。 |
| CoreMark x32 短迭代 | `python sim/mini_board_migration/run_coremark_x32.py --tag mini200h_preboard_20261011_d`；[结果](../../sim/mini_board_migration/build/mini200h_preboard_20261011_d/results.json) | performance/validation 各 1 次，真实 CPU 与 256 位 DDR 用户口模型，独立 UART TX 引脚解码；final CRC `e714`/`e3c1`，两组均 `CRC_FUNCTIONAL_PASS`。程序预装入仿真 DDR，未经过 Loader 下载或 PHY。短迭代不是正式跑分。 |
| 当前 Loader x32 下载与运行 | `python sim/mini_board_migration/run_loader_x32.py --tag <新目录名>`；[本次结果](../../sim/mini_board_migration/build/mini200h_loader_20261012_c/result.json) | PASS；当前 ROM/RAM 镜像、真实 UART RX/TX 引脚、x32 DDR 用户口模型，9 帧、RX 619 字节、TX 553 字节，Hello 程序从 DDR 运行。三次启动自检与物理字节 oracle 校验通过。该用例下载 Hello，未下载 CoreMark。 |
| 120 次上板下载计划 | `run_measurement.py --plan-only`，performance/validation 各一份；产物在 `sim/mini_board_migration/build/mini200h_loader_20261012_c/plan_*.json` | 两组均 PASS，各 129 个预期响应、一次 RUN；未打开串口，未观察 FPGA 配置，不是 120 次运行结果。 |
| 新 DDR IP 物理模型 | `python sim/mini_board_migration/run_ddr_phy.py --tag mini200h_ddr_phy_20261012_j`；[结果](../../sim/mini_board_migration/build/mini200h_ddr_phy_20261012_j/result.json) | `DDR_IP_PHY_TRAINING_PASS`；两片 x16 模型组成 x32，训练在约 374.773 µs 完成，训练后两片模型均观察到真实 REFRESH，仿真运行至 450 µs 正常退出；ModelSim `Errors: 0, Warnings: 561`，模型日志无 `ERROR:`。厂家示例测试没有 SoC 访问。 |

离线计划绑定的 120 次 BIN：performance 为 15,936 字节、SHA-256 `e321bacabfc093321a9dd8c29449b45348fcb3b6ab6dd1762c178c5be2e96d31`；validation 为 15,944 字节、SHA-256 `0651a64ca0e2aa5a4e8294991d93e9a2d019f10881065fae8c1f901b23ab6594`。这两份 BIN 尚未在 MINI 实板上运行；本次 CoreMark x32 功能仿真使用的是各 1 次短迭代 BIN。

Loader x32 首轮测试在末尾使用了历史 TB 的“每笔 CPU DDR 请求均产生一笔用户口事务”判据，当前 8 行 I 缓存/4 行 D 读缓冲会命中并省略用户口 AR，因此该判据不适用。原失败日志保留在 `build/mini200h_loader_20261011_b/`。复验只把该判据改为 `AW=W` 且用户口事务数不超过请求数；逐笔 DDR 写地址、256 位数据与 strobe、读响应对照独立 shadow、全 64 KiB DDR 内容和 UART 引脚检查均保留。复验 PASS 在 `mini200h_loader_20261012_c/`。

DDR IP 厂家物理模型测试使用隔离副本解决 `ddr3` 模块重名和本机 FSDB 插件缺失。`mini200h_ddr_phy_20261012_f/` 曾记录训练完成，却在下一条 NOP 出现两片模型的 `tRFC maximum violation`，因此该次标记为 `DDR_IP_PHY_TRAINING_COMPLETE_MODEL_ERROR`，不计 PASS。厂家示例在训练期间禁用最大刷新间隔检查、完成后立即重新启用；隔离平台尝试重置刷新计时起点。`mini200h_ddr_phy_20261012_h/` 仍报同样错误，定位为测试顶层 ns 与 Micron 模型 ps 的换算错误；`mini200h_ddr_phy_20261012_i/` 改正换算后又在 ACT 命令出现最小 tRFC 间隔错误，说明人工重置计时会干扰另一项模型检查。两次日志均保留且不计 PASS。最终 `mini200h_ddr_phy_20261012_j/` 不改模型计时，等待控制器真正发出训练后的 REFRESH，再重新启用最大间隔检查；该轮运行至 450 µs、双模型无 `ERROR:`，正常退出 PASS。这个判据仅覆盖 IP 厂家示例的训练及其后 75 µs，不覆盖当前 SoC 经 PHY 的应用数据事务。

## 用户上板步骤与边界

1. 在 PDS 中核对设计顶层 `board_top`、三个新 IP、当前 FDC、ROM/RAM 初始化文件；执行综合、映射、布局布线、时序检查及新 MINI-(200H) 位流生成。保存器件型号、资源、所有时钟和失败端点、位流 SHA-256。旧板位流及其时序报告不适用于 MINI-(200H)。
2. 下载新位流。根据板卡实际串口号设置 `-Port`；每次应用测试按 KEY0 复位并等 DDR 就绪。可先用 `hello` 验证 MINI 串口与 Loader，再运行 `performance_120`、`validation_120` 各一轮。PC 工具入口为 `tools/uart_loader/candidates/perf_2b/run_measurement.py`，批量入口为 `run_measurements.ps1`；两者会保留独立日志。
3. 两组 120 次结果须分别核对 Loader DDR CRC32 VERIFY、CoreMark CRC 与 `PERF2B` 13 项计数、`formal_benchmark`、运行至少 10 秒的门槛。用户实际串口日志和位流身份审查完成前，状态保持“仿真通过、实板未验证”；仿真输出的迭代速度不是实板分数。

2026-10-12 当前 Windows `pnputil /enum-devices /connected /class Ports` 显示 `Silicon Labs CP210x USB to UART Bridge (COM9)`，与 MINI 手册所述 CP2102 USB 转串口类型一致；其他当前 COM3/4/5/6 为蓝牙串口。COM9 是当前最可能的板载串口，拔插后应再次核对端口号。手册 PDF 第 30 页把 Type-C 定义为 USB-UART 通信口；第 41 页要求开发板使用随板 +12 V 电源，由底板转换出 +5 V 并经板间连接器供核心板。仅连接 Type-C 不能据此认定核心板已经正确供电；手册示意图没有完整 USB VBUS 与底板电源隔离细节，双路连接时仍以实物原理图和板厂要求为准。

新位流生成并下载后，可在 PowerShell 中按实际串口号调整当前检测到的 `COM9`，使用尚不存在的日志路径：

```powershell
& 'C:/python/python.exe' 'D:/riscv/RISCV/tools/uart_loader/candidates/perf_2b/run_measurement.py' --application hello --port COM9 --log 'D:/riscv/RISCV/sim/mini_board_migration/board/hello_01.json'
& 'D:/riscv/RISCV/tools/uart_loader/candidates/perf_2b/run_measurements.ps1' -Port COM9 -Applications @('performance_120','validation_120') -LogDirectory 'D:/riscv/RISCV/sim/mini_board_migration/board/coremark_01'
```

每个应用开始前按工具提示先复位 KEY0 并等待 DDR 就绪；不要把原板卡旧位流的 SHA 或实板成绩用于判定新板通过。上述操作由用户执行，本轮未打开实板串口。

本轮没有启动 PDS 实现、生成位流或操作实板。x32 用户口模型与 DDR IP 厂家物理模型是两项分开的验证；当前没有覆盖新 SoC 经真实 DDR PHY 下载并运行 CoreMark 的全链物理联仿。
