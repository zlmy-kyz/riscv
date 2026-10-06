# 测试程序和已验证镜像

```text
tests/
├── README.md
├── development/                 # 当前开发工作区，恢复原输出30工作副本
│   ├── README.md
│   ├── main.c
│   ├── uart_printf.c / uart_printf.h
│   ├── startup.S / linker.ld
│   ├── build.ps1 / bin_to_dat.py
│   └── build/                   # 构建产物
├── fpga_uart_pc_output_30/       # 输出30：已实板验证
│   ├── README.md
│   ├── main.c
│   ├── uart_printf.c / uart_printf.h
│   ├── startup.S / linker.ld
│   ├── build.ps1 / bin_to_dat.py
│   ├── build/
│   └── main.dat                 # 固定保存的原成功上板镜像
└── pc_uart_fpga_uart_pc/         # Echo实验：仿真PASS，实板功能PASS（用户确认）
    ├── README.md
    ├── main.c
    ├── uart_echo.c / uart_echo.h
    ├── startup.S / linker.ld
    ├── build.ps1 / bin_to_dat.py
    ├── main.dat                 # 固定成功镜像，直接保存原字节
    ├── verified_image.json      # 镜像哈希与验证范围
    └── build/                   # main.elf / main.bin / main.dis / main.dat
```

恢复development与成功归档的旧结构。每个实验自带对应.c/.h、启动/链接和构建/转换
脚本，不依赖tests/common。原uart_echo内容已搬至pc_uart_fpga_uart_pc，未丢弃已有产物。
此前common及uart_output_30的重复布局保护保存在两个实验build/previous_layout内，
仅为历史保留，不是构建入口。

| 目录 | 用途 | 仿真 | 实板 | DAT |
| --- | --- | --- | --- | --- |
| development | 当前工作副本，现为输出30 | 修改后重验 | 不自动继承实板验证 | build/main.dat |
| fpga_uart_pc_output_30 | 成功输出30归档 | PASS | 用户确认收到30 | main.dat |
| pc_uart_fpga_uart_pc | PC→FPGA→PC Echo成功实验 | 四层PASS | 功能PASS，用户确认复位后重复回显 | main.dat归档；build/main.dat为原验收/上板输入 |

从工程根目录构建：

构建脚本使用工程根目录的 `xpack-riscv-none-elf-gcc-15.2.0-1/bin/`，
需自行安装相同版本的 Windows xPack RISC-V 工具链；编译器发行包不上传仓库。
转换需要 Python 3。Echo 已验收的 ELF/BIN/DIS/DAT 一并保存，首次克隆后可以直接
安装工具链（runner 使用其中的 nm）并运行仿真，无需先重建成功镜像。

```powershell
& ./tests/development/build.ps1
& ./tests/fpga_uart_pc_output_30/build.ps1
& ./tests/pc_uart_fpga_uart_pc/build.ps1
```

输出30归档的根main.dat不得被重新构建覆盖；该目录构建只写build/。
Echo最终文件为tests/pc_uart_fpga_uart_pc/build/main.dat；仿真直接读取同一个文件：

```powershell
& C:/python/python.exe sim/uart_echo/run.py
```

仿真环境、TB、模型、运行脚本及日志仍在sim/uart_echo，tests只保存CPU软件和构建产物。
先构建→Full Boot验收同一DAT→RAM IP→FPGA；仿真后不能另生成DAT直接上板。
Echo实板功能及复位重复回显已由截图和用户反馈确认；长时间压力/二进制/错误/IRQ另立验收。
详情见doc/UART_Echo实板基本回显确认_2026-10-07.md；输出30历史TX成功不代替双向验收。
