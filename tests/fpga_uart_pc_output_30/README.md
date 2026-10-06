# FPGA UART 向 PC 输出 30：已验证归档

目的：裸机C → RAM DAT → ROM Loader → DDR → CPU执行C → printf →
UART TX → USB-TTL → PC，确认PC收到30。

验证日期：2026-10-06（Asia/Shanghai）。仿真：PASS（ModelSim/Icarus）。
实板：PASS，用户明确反馈“成功输出30”。此归档原则上固定，未来开发使用development。
用户未报告本次LED观察、FPGA RX接收或UART IRQ实板结果，不能将TX结果扩大为双向验收。

| 文件 | 作用 |
| --- | --- |
| `main.c` | volatile a=10、b=20、c=a+b；printf输出30，等待TX结束后上报结果 |
| `uart_printf.c` | 裸机UART轮询发送及精简printf，支持%d、%%与普通文本，不链接完整libc |
| `uart_printf.h` | UART printf/flush接口所需声明 |
| `startup.S` | 初始化gp/sp，清零BSS，然后调用main |
| `linker.ld` | ELF入口0x40000000，64KiB DDR程序空间，顶部4KiB栈 |
| `build.ps1` | 源码到ELF/BIN/DAT，重新生成的所有文件只进入本目录build/ |
| `bin_to_dat.py` | 本次构建转换器的固定副本，自包含loader编码及小端DAT转换 |
| `main.dat` | 实际成功上板的RAM初始化基准镜像；从整理前文件直接复制，未重编译替换 |

串口参数：115200 baud、8 data bits、no parity、1 stop bit、no flow control。
实板连接：FPGA TX → USB-TTL RXD；FPGA GND → USB-TTL GND。
原USB-TTL自身RXD/TXD回环短接应移除；本程序只发送，无需USB-TTL TXD参与。
具体板级物理连线仍以本次用户实际接线为准。

预期显示：

```text
30
```

实际发送 `30\r\n`，每次启动/复位一次。PC先打开串口，再复位FPGA可重新观察。

基准DAT：4096行32位HEX字；680字节payload、170字，末四字为
`000000aa 00000000 00000000 00000000`。链接入口0x40000000，BSS4字节由startup清零。
基准文件SHA-256（整理前与复制后完全一致）：

```text
e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5
```

在本目录复现：

```powershell
& ./build.ps1
Get-FileHash ./main.dat -Algorithm SHA256
Get-FileHash ./build/main.dat -Algorithm SHA256
```

新生成的镜像为build/main.dat，根目录main.dat不自动覆盖。
重建后可比较哈希；即使相同也保留“原实板基准”和“本次重建产物”的来源区别。
编译器需工程内xPack RV32I工具链，转换需Python；源码/转换不依赖sim目录。
`.elf/.bin/.dis`、readelf、map、日志等可重建，不进入成功归档内容，build由Git忽略。

当前data_ram INIT_FILE已随路径整理指向本目录main.dat，只改文件引用，不改生成的
4096字初始化内容。ROM仍使用既有boot_rom.dat，不需要换成此payload。
若重新部署，应在PDS核对HEX/32位/12位和IP初始化，再构建/下载相应位流。

源码与DAT证据详见 `doc/C裸机printf输出30与RAM镜像_2026-10-06.md`。
仿真程序、DDR模型、日志和结果汇总均留在sim，未复制到此目录。
