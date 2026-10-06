# UART Echo 分层仿真

程序源码/ELF/BIN/最终 DAT 在 tests/pc_uart_fpga_uart_pc；这里仅保存 TB、模型、runner 和
仿真日志/临时文件。run.py 只读取既有程序，绝不调用编译器重建/转换 DAT。

工程根目录的一条重跑命令：

```powershell
& C:/python/python.exe sim/uart_echo/run.py
# 可选独立 Icarus 交叉验证
& C:/python/python.exe sim/uart_echo/run.py --simulator iverilog
```

首次先按 tests/pc_uart_fpga_uart_pc/README.md 构建一次。四层严格顺序运行，任一编译/
仿真/校验失败即非零退出并输出 RESULT: FAIL，不进入下一层。

| build 子目录 | 验证范围 |
| --- | --- |
| uart_module | 生产 UART RX → FIFO → TB 字节握手驱动 → 生产 TX；无 RXD/TXD 直连 |
| uart_mmio | 生产 uart_mmio，TB 轮询读 RX/写 TX，响应额外延迟7拍，比较读响应 |
| cpu_echo | 同一 DAT 的 payload 预装到 DDR 用户口模型，真实 CPU 从0x40000000运行 startup/C，轮询 MMIO Echo |
| full_boot | RAM 直接读取最终 DAT，ROM 原 loader 从0启动，CPU 搬至毒化 DDR → startup/C → UART RX/MMIO → CPU → TXD |

`tb/tb_uart_echo.v` 提供四层配置、独立 RX 驱动、TX monitor 和逐字 scoreboard，
并包含 Pango 用户口模型（AW/AR 背压及 W/R 延迟）。
`tb/echo_bram.v` 是同步 ROM/RAM 行为模型，沿用地址寄存器/延迟复位语义。
Full Boot 不预加载 DDR；逐字核对 CPU loader 的地址、数据、strobe、DDR 内容，
并检查 startup SP、毒化 BSS 清零、main 退休和真实 CPU 执行。
这里的 Full Boot 是完整软件装载/执行链路，不含 DDR IP PHY、训练或板级引脚电气验证。
两条既有完整 DDR IP＋物理模型回归独立保留在 ipcore/ddr3/sim/modelsim。

## 时序与字节检查

UART 为115200/8N1/无流控；TB 输入 Tbit=1/115200≈8.680556 us，
异步相位起始，start低、8位LSB first、stop高，连续帧之间不插额外空隙。
生产93.75 MHz时钟下 UART 分频814拍/bit。
独立 TXD monitor 检测下降沿、半位后确认start、逐位中心采样、检查stop、比较字节。
不会仅以引脚跳变作为通过依据。

每层97字节：A、单组hello123、后续九组hello123和16个00/11/…/FF二进制字节。
后88字节连续发送，最后等待20个位时间捕捉重复/多余输出。
逐字核对 RXD输入=UART RX结果=FIFO pop=MMIO RX读响应=TX写值=TXD解码。
CPU层明确检查LBU/SB lane0、每次LBU退休写回值，以及无frame/overflow、总线错误、同步异常或IRQ。
最终软件echo_count=97、echo_error=0，与五段字节scoreboard一致。
所有层检查最终计数97、FIFO空、TX idle，无丢失/重复/乱序/超时。
module层无CPU/MMIO，mmio_read=0；CPU字节链路只在cpu_echo/full_boot获得验证。

## 日志及判断

各层 `build/<layer>/{compile.log,modelsim.log,iverilog.log}`；ModelSim库、Tcl、
Icarus可执行文件也在该层目录。汇总 `build/<simulator>_results.json`，
最后验收镜像凭据 `build/<simulator>_validated_image.json`。

每层必须有且仅有一条对应 RESULT: PASS、无 RESULT: FAIL、进程退出0；
ModelSim编译和仿真还必须 Errors:0。全层完成才输出总 RESULT: PASS 4/4。
runner 核对 DAT/BIN/ELF一致、入口/装载范围/栈、所有生产 RTL/IP/PDS/FDC哈希未变。
Full Boot 的 `$readmemh` 直接使用
`D:/riscv/RISCV/tests/pc_uart_fpga_uart_pc/build/main.dat`，不使用重新转换副本。
仿真前后DAT哈希一致；上板使用同一个文件。重新构建后旧验收凭据失效，须重跑。

仿真 PASS 不能代替实板 PASS。2026-10-07用户已确认FPGA连接和Echo下载，
截图中的nb、a、hello 123（带空格）及混合文本基本回显PASS。
随后用户在复位重复发送建议后反馈成功，实板功能验收PASS；新截图TX/RX均36字节。
长时间压力/二进制/错误/IRQ未覆盖，记录见doc/UART_Echo实板基本回显确认_2026-10-07.md。
runner的board_result=NOT_TESTED表示该仿真进程不测试实板，不用于覆盖用户实板记录。
