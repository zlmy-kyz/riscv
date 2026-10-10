# tests 恢复旧结构与 Echo 实验迁移

日期：2026-10-06（Asia/Shanghai）。按用户新要求，恢复development工作区和
fpga_uart_pc_output_30成功归档，并新增pc_uart_fpga_uart_pc保存原uart_echo实验。

## 完成内容

- development整目录从前一步legacy_development原样移回；保持原输出30工作副本，
  含main.c、uart_printf.c/.h、startup.S、linker.ld、build.ps1、转换器和全部build产物。
- fpga_uart_pc_output_30整目录从legacy_archive原样移回；原实板成功根main.dat不变。
- uart_echo整目录搬到pc_uart_fpga_uart_pc；src/main.c移到根main.c，新增本实验
  独立uart_echo.c/.h（原字节UART实现），启动/链接/转换器各自保存。
  只改include名称和header guard，函数行为不变，独立build.ps1选择uart_echo.c编译。
- 原common和重复uart_output_30布局移动至两个实验build/previous_layout保护保存，
  不删除用户文件，不再作为构建入口；tests顶层只保留README和上述三个目录。
- sim/uart_echo保持位置、四层结构及TB不变；runner改读新的实验build/main.dat。
  旧sim/baremetal_c恢复引用成功归档自己的startup/linker/转换器和镜像。
- RAM IP三处INIT_FILE仅恢复为tests/fpga_uart_pc_output_30/main.dat，未切换Echo；
  保持原文件行尾和其他字节。生成初始化字、生产RTL、PDS/FDC和位流均未改变。
- tests、各实验、sim README以及AGENTS、根README、CODEX_HANDOFF同步最新约定。

当前文件：

```text
tests/
├── README.md
├── development/
│   ├── README.md / main.c / uart_printf.c / uart_printf.h
│   ├── startup.S / linker.ld / build.ps1 / bin_to_dat.py
│   └── build/
├── fpga_uart_pc_output_30/
│   ├── README.md / main.c / uart_printf.c / uart_printf.h
│   ├── startup.S / linker.ld / build.ps1 / bin_to_dat.py
│   ├── build/
│   └── main.dat             # 原实板成功字节
└── pc_uart_fpga_uart_pc/
    ├── README.md / main.c / uart_echo.c / uart_echo.h
    ├── startup.S / linker.ld / build.ps1 / bin_to_dat.py
    └── build/               # 原Echo ELF/BIN/DIS/DAT整体搬迁
```

## 验证和复现

新Echo独立构建入口（用户修改后使用，构建后须重新验收）：

```powershell
Set-Location D:/riscv/RISCV
& ./tests/pc_uart_fpga_uart_pc/build.ps1
& C:/python/python.exe sim/uart_echo/run.py
& C:/python/python.exe sim/uart_echo/run.py --simulator iverilog
```

本轮为保留最终已验证DAT，独立构建脚本实际用隔离输出参数核对：

```powershell
& ./tests/pc_uart_fpga_uart_pc/build.ps1 -OutputDirectory sim/uart_echo/build/restore_layout/rebuild_check
& C:/python/python.exe sim/uart_echo/run.py
& C:/python/python.exe sim/uart_echo/run.py --simulator iverilog
& C:/python/python.exe sim/baremetal_c/run.py --case uart_printf
```

隔离构建退出0，text240/data0/bss8，保留原裸机链接RWX warning；
重建BIN和DAT均与搬迁前逐字节相同，没有覆盖最终Echo DAT或输出30基准。
新路径ModelSim四层4/4 PASS，编译/各层Errors0/Warnings0，每层97字节，
Full Boot从最终新路径DAT经ROM loader复制60字入DDR，CPU轮询RX/TX精确回显。
输出30归档路径单项CPU回归PASS，解码30 CR LF，Errors0/Warnings0。
Icarus新路径四层4/4 PASS，各层结果与ModelSim一致，Full Boot为841064 cycles。
两种模拟器报告均直接引用tests/pc_uart_fpga_uart_pc/build/main.dat，
DAT在本轮所有构建比较/仿真前后哈希一致；Echo仍为实板待验证。

移动前后Echo DAT SHA-256：

```text
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20
```

输出30实板基准SHA-256：

```text
e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5
```

保护和布局核对均PASS；证据在sim/uart_echo/build/restore_layout/before.json、
verification.json；前次两种模拟器汇总/镜像凭据保存为该目录previous_*.json。
当前新路径验收报告由runner更新至sim/uart_echo/build/<simulator>_results.json。
Python构建/转换文件、最终DAT均存在，各实验.c/.h配对检查通过。
定向git diff --check通过，根main.dat和Echo build/main.dat可见，中间产物正确忽略。

## 未覆盖范围

仅目录和构建引用调整，无新功能RTL/TB变更，因此不重复未受影响的DDR PHY回归。
Echo仍是同一镜像仿真PASS，未运行PDS/下载/双向实板测试，不记录Echo实板PASS。
上板使用tests/pc_uart_fpga_uart_pc/build/main.dat的同一已验收文件；
Full Boot仍为DDR用户口模型，不含PHY训练或物理接线验证。
