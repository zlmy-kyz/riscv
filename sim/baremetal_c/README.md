# 裸机 C：BIN → DAT → ROM loader → DDR → LED

这里是独立仿真入口，复用真实 `soc_top`、CPU、互连、DDR 桥和 `soc_ddr3_leds`。
DDR 仅使用 Pango 用户口行为模型；不包含 DDR PHY/训练或 FPGA 实板验证。
不会推广主 IP，不会修改 `MyCpu_test/board_selftest` 的镜像。

从工程根目录执行：

```powershell
# 构建输出30归档，所有新产物只写build，不覆盖根main.dat
& ./tests/fpga_uart_pc_output_30/build.ps1

# 单独转换现有 BIN；输出目录自行选择，不能指向主 IP 镜像目录
& C:/python/python.exe sim/baremetal_c/bin_to_dat.py tests/fpga_uart_pc_output_30/build/main.bin sim/baremetal_c/build/manual_candidate

# 默认 ModelSim，包含构建候选、转换和五个验收用例
& C:/python/python.exe sim/baremetal_c/run.py

# 可选 Icarus，或只运行一个用例并保存 VCD
& C:/python/python.exe sim/baremetal_c/run.py --simulator iverilog
& C:/python/python.exe sim/baremetal_c/run.py --case led_pass --wave
& C:/python/python.exe sim/baremetal_c/run.py --case uart_printf
# 归档目录重新构建后，也可独立验收该目录的构建产物
& C:/python/python.exe sim/baremetal_c/run.py --case uart_printf --program-dir tests/fpga_uart_pc_output_30
```

`bin_to_dat.py` 仅适用于入口在指定 DDR 基址、连续装载的平坦 BIN。
BIN 本身没有链接地址信息；runner 会另外检查 ELF，确认入口、LMA/VMA、
装载范围和 BIN 内容一致。它不是通用 ELF 重定位器。

生成的 `main.dat` 是 4096 行、每行 8 位十六进制的 32 位字。
BIN 每四个字节按小端转为一个字，不足四字节补零；最大 payload 16368 字节。
RAM 最后四字 `[payload_words, 0, 0, 0]` 保留现有 loader 清单格式。
`boot_rom.dat` 从地址 0 启动，将这些字复制至 DDR `0x40000000` 并跳转。
此处 `manifest.json` 是新工具的说明文件，与板级 `manifest.tsv` 并不混用。
构建转换逻辑位于tests/fpga_uart_pc_output_30/bin_to_dat.py；本sim目录同名文件仅保留旧入口兼容。
成功镜像固定在tests/fpga_uart_pc_output_30/main.dat，runner会校验该文件在仿真期间未改。

五个用例（原始 100 字节基线保存在 `original_main.c`，独立编译，不受当前 main 改动影响）：

| 用例 | 软件与验收 |
| --- | --- |
| original | 原始加法基线，检查三处栈值 10/20/30 与 `0x40000060` 至少八次退休；无状态上报，LED 保持 IDLE |
| led_pass | 独立编译 `led_main.c`，非空 `.data/.bss`，RUN 后 PASS 常亮 |
| injected_fail | 比较期望故意设为 31，计算结果仍为 30，软件上报 FAIL，LED 快闪 |
| timeout | 原始 C 不上报，等 LED watchdog 超时后检查快闪 |
| uart_printf | 当前 `tests/fpga_uart_pc_output_30/build/main.bin`，CPU 从 ROM 搬入 DDR，调用精简 printf，独立解码 TX 引脚为 `30\r\n`，最终 stop 完成后 LED PASS |

DDR 模型的 64 KiB 初始全部为 `0xA5A5A5A5`，没有预放 C 代码。
自动检查 loader 每次接受的地址/数据/strobe、DDR 写入后逐字内容、启动 SP、
BSS 清零顺序及 main 入口内容、最终 SP、真实退休循环、无总线错误和同步异常。
AW/AR 背压及写/读延迟均非零；模型检查高地址防止截断别名。

LED 复用生产模块，仅本 TB 参数为 `CORE_CLK_HZ=32`、超时 30000 拍，
RUN 每 16 拍切换、FAIL 每 4 拍切换，以缩短仿真。实际 CPU 仿真时钟仍为
93.75 MHz，板级 93.75 MHz/5 秒 LED 参数及逻辑均未改。
UART 用例将 TB watchdog 单独设为 200000 拍，仿真超时 220000 拍，
以覆盖四个 115200 波特率帧；其他四项仍使用原 30000/40000 拍限值。

全部产物在 `build/`：DAT、BIN/ELF、清单、反汇编、逐例日志、可选波形和
`modelsim_results.json` / `iverilog_results.json`。通过须同时有单个对应 PASS、
无 FAIL、进程退出 0；ModelSim 另须 `Errors: 0`。
runner 检查主 PDS/FDC、主 ROM/RAM IP 初始化和板级镜像 SHA256 未变化。
