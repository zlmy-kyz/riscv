# UART Echo GitHub 发布核对

日期：2026-10-07。目的：将当前成功实验、软件镜像、仿真入口及验证记录同步到
`zlmy-kyz/riscv`，保留无关本地工作。

## 发布范围

- `tests/`：development 工作副本、输出30实板基准、Echo独立实验及配套.c/.h、构建脚本。
- `tests/pc_uart_fpga_uart_pc/build/`：验收时的ELF/BIN/DIS/DAT；根main.dat为成功归档。
- `sim/baremetal_c/`、`sim/uart_echo/`：C启动/输出30与Echo分层仿真源码、运行说明；
  Echo汇总结果和镜像凭据保留，仿真编译库与临时文件不上传。
- 当前UART引脚约束（TX=AA20、RX=AA21）、data_ram配置/wrapper/IP TB及生成初始化参数。
- 项目说明、AGENTS、交接文档、C/Echo阶段记录及三张用户实板截图。

本地编译器发行包不上传；构建/符号核对需要
`xpack-riscv-none-elf-gcc-15.2.0-1/bin/`。ModelSim使用本机
`D:/modelsim/win64pe`，Python命令在工程根目录运行。
PDS运行时间戳、impl.tcl、多seed摘要、约束备份、DDR旧日志改动及无关文档删除
留在本地；不清理或重置。当前PDS设计顶层仍为board_top，无需为发布修改顶层。

## 本次验证

没有重新编译或转换成功DAT。直接运行：

```powershell
& C:/python/python.exe sim/uart_echo/run.py
```

| 层 | 本次ModelSim结果 | 字节数 |
| --- | --- | --- |
| UART RX/TX module | PASS | 97 |
| UART MMIO | PASS | 97 |
| CPU Echo | PASS | 97 |
| Full Boot | PASS | 97 |

各层编译/仿真Errors:0、Warnings:0；总RESULT: PASS 4/4。
CPU两层MMIO响应、退休LBU、TX写值和TXD解码均97次且逐字节一致。
Full Boot直接读取`tests/pc_uart_fpga_uart_pc/build/main.dat`，ROM loader搬至DDR后
由真实CPU执行；DDR为用户口行为模型，此入口不含PHY训练。
日志在`sim/uart_echo/build/<layer>/{compile.log,modelsim.log}`，汇总结果与镜像凭据
在同build目录。Icarus凭据保留2026-10-06目录迁移后的4/4 PASS，本次不重复运行。

Echo构建DAT与根归档DAT SHA-256均为：

```text
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20
```

输出30根DAT仍为：

```text
e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5
```

`.gitattributes`禁止这些软件DAT的换行转换，以保护克隆后的完整文件哈希。
实板结论沿用用户已确认的Echo功能PASS及复位后重复回显反馈，详见
[实板记录](UART_Echo实板基本回显确认_2026-10-07.md)；本次没有下载或新增实板测试。
尚未覆盖的长时间压力、二进制、错误/IRQ实板测试保持待验收。
