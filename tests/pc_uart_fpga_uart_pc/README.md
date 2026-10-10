# UART Echo（实板功能验收PASS，用户确认）

2026-10-07：用户确认已下载Echo位流、USB-TTL连接FPGA并拆除适配器自身回环。
截图中nb（两次）、小写a、hello 123（带空格）及符号/大小写混合文本均有一致回显。
随后用户在复位重复发送建议后反馈“成功”，新截图增加a和字母/数字/符号混合文本回显，
TX/RX累计均36字节。记录Echo实板功能验收PASS及复位后重复通信成功；
长时间无间隙压力、二进制/错误注入/IRQ实板测试不在本次结论范围。
证据见 `doc/uart/UART_Echo实板基本回显确认_2026-10-07.md`。

根目录 `main.dat` 为本次成功镜像的直接归档，源自 `build/main.dat`，未重编译。
SHA-256：`2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20`。
`verified_image.json` 保存归档来源/日期/验收范围；根基准不得被后续构建覆盖。
当前Full Boot及RAM IP使用的仍是相同字节的 `build/main.dat`。

目的：PC → FPGA UART RX → FIFO/MMIO → 真实 CPU 裸机 C → UART TX → PC。
逐字节原样回显，无提示文字、CR/LF 转换或 IRQ；不是 RTL 引脚回环。

`main.c` 关闭 RX IRQ、清 sticky error，轮询 STATUS，使用 LBU 读取 RX_DATA、
SB 写 TX_DATA，并递增 `echo_count`。发现 frame/overflow 后保存 `echo_error` 并停止，
保留证据至复位。`uart_echo.c/.h` 提供寄存器和轮询接口；
`startup.S` 设置 gp/sp、清 BSS，`linker.ld` 链接到 DDR 0x40000000，
保留 64 KiB 地址范围及顶部 4 KiB 栈。`build.ps1/bin_to_dat.py` 构建/转换镜像。

从工程根目录编译一次：

```powershell
& ./tests/pc_uart_fpga_uart_pc/build.ps1
```

所有程序构建产物在本目录 `build/`：main.elf、main.bin、main.dis、main.dat，
另含 map、编译记录及 manifest。最终 RAM IP 镜像固定为：

```text
D:/riscv/RISCV/tests/pc_uart_fpga_uart_pc/build/main.dat
```

DAT 为4096个32位HEX字；末四字含 ROM loader 清单。已有 ROM loader 兼容，
不用替换 ROM。程序只能使用 RV32I/ILP32；精简裸机链接保留原有 RWX LOAD warning。

编译后运行四层验收：

```powershell
& C:/python/python.exe sim/uart_echo/run.py
```

PASS 条件：A、hello123、多组连续字符及二进制字节全部有序、无丢失/重复；
RX 输入、UART 解码、MMIO RX 读响应、TX 写数据、TXD 独立解码相等；
无 framing/overflow、CPU异常、总线错误或超时。仿真详见 `sim/uart_echo/README.md`。
本目录独立保存main.c、uart_echo.c/.h、startup.S、linker.ld和构建/转换器，
不依赖common目录。build/previous_layout仅保护此前重复文件。
本程序不写 TEST_STATUS；原板级 LED watchdog 可能在5秒后指示超时，
LED 不作为这个持续 Echo 程序的验收条件。

## 上板（由用户执行）

1. 确认四层全部 PASS，并核对 `sim/uart_echo/build/modelsim_validated_image.json`
   的 DAT SHA-256 与当前 `build/main.dat` 一致。仿真后不要重编译、另生成 DAT；
   如修改或重建，必须重新四层验收。
2. 在 PDS 将 data_ram 的 INIT_FILE 指向上述同一份 main.dat，保持 HEX、
   32位数据/12位地址配置并重新生成 RAM IP。只改路径不会更新生成初始化字。
   inst_rom 保持既有 boot_rom.dat；不把 main.dat 装入 ROM。
3. Compile → Synthesize → Device Map → Place & Route → Report Timing →
   Generate Bitstream，核对 board_top 和时序，下载。
4. USB-TTL：TXD → FPGA RXD，RXD ← FPGA TXD，GND ↔ GND；拆掉适配器回环。
   当前 FDC 为 FPGA RX=AA21、TX=AA20，按已经使用的板卡实际引脚/连线核对。
   板卡独立供电，不接 USB-TTL 的5V/3V3供电端。
5. PC 串口115200、8N1、无流控；关闭本地回显、自动添加换行。
   启动/复位后发送 A，应收到 A；发送 hello123，应收到 hello123。
   连续多次发送，检查逐字节相同且无重复/丢失。

当前已有用户确认的Echo实板功能验收PASS与复位重复通信成功。
截图未提供原始串口字节捕获、实板sticky error/IRQ读数或长时间连续压力结果。
已有四层仿真PASS与本次实板功能证据分别记录，不能扩大各自验证范围。
