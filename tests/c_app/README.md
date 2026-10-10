# 新 C 程序自动构建、审查、下载和验证

本目录提供通用 `run_app.py`，不用将每个新程序注册到旧 Hello/CoreMark 白名单。流程为：

```text
C 源码 + 已验证 BSP → GCC → ELF/BIN → 镜像审查
→ 真实 CPU/DDR 模型完整下载和执行仿真 → 本应用独立门控
→ 用户 KEY0 复位 → UART LOAD → DDR CRC32 VERIFY → RUN → 输出验证 → JSON 日志
```

复用 2026-10-10 成功的主工程位流 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`，SHA256 为 `7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf`。不用为每个 C 程序重新生成 FPGA 位流。旧 BSP、Loader、IP、位流、CoreMark 成功镜像和原下载门控均保留。

## 最短使用方式

新建或编辑本目录的 `main.c`：

```c
#include "bsp.h"

int main(void) {
    printf("MY_PROGRAM_PASS value=%u\n", 123u);
    return 0;
}
```

在任意目录的 PowerShell 执行：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tests/c_app/run_app.py `
  --source D:/riscv/RISCV/tests/c_app/main.c `
  --expect MY_PROGRAM_PASS
```

脚本自动编译、审查、仿真，生成本次独立门控。全部通过后，终端提示你确认板子运行上述成功位流、关闭串口助手、按下并释放 KEY0、等待 DDR 初始化，再按回车。随后自动打开 COM11，完成下载、校验、执行和输出验证。板级操作由用户执行。

`--expect` 是你自行定义的成功文本，需要在程序输出中出现**恰好一次**。程序必须 `return 0`，工具自动追加 `C_APP_DONE return=0` 完成标记；非零返回、异常、错误输出、缺少结束标记或超时均失败。不要在自己的输出中使用保留文本 `C_APP_DONE`。`--expect` 不自动判断算法是否正确，程序应自行检查计算结果后才输出成功文本。

本目录自带示例检查非零 data、清零 BSS，计算 1 到 10 的和，输出 `MY_PROGRAM_PASS sum=55`。

最终实板成功标志：

```text
RESULT: PASS C_APP_ACTUAL_BOARD_PASS
```

## 只准备程序，之后上板

加 `--prepare` 只进行编译、审查和完整仿真，绝不打开串口：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tests/c_app/run_app.py `
  --source D:/riscv/RISCV/tests/c_app/main.c `
  --expect MY_PROGRAM_PASS --prepare
```

成功后打印本次构建目录。本轮已经准备好的示例为 `D:/riscv/RISCV/tests/c_app/build/20261010_161146_75750db9`，可直接下载验证；你以后新建程序时使用自己那次实际打印的目录：

```powershell
# 下载本轮已通过完整仿真的示例，无需重新编译和仿真。
& C:/python/python.exe D:/riscv/RISCV/tests/c_app/run_app.py `
  --deploy D:/riscv/RISCV/tests/c_app/build/20261010_161146_75750db9 `
  --log D:/riscv/RISCV/sim/c_app/board/my_program_01.json
```

`--deploy` 复用已准备的 ELF/BIN 和门控，不重复编译或仿真。每次重新下载都按提示 KEY0 复位。重复测试改用新的日志名。更改 C、依赖头文件或工具后，旧门控会拒绝，需要重新执行 `--source` 生成新版本。

## 多文件与严格输出匹配

多份 C 文件重复使用 `--source`，各源文件所在目录自动加入头文件搜索路径；源码和项目依赖头文件须放在工程内。例如：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tests/c_app/run_app.py `
  --source D:/riscv/RISCV/tests/c_app/main.c `
  --source D:/riscv/RISCV/tests/c_app/calc.c `
  --expect MY_PROGRAM_PASS
```

若要验证整个程序输出，用 `--expect-file` 替代 `--expect`。文件内容是**精确字节**，包括换行；UTF-8 文件不得带 BOM。不要包含工具自动追加的完成标记。例如下面的命令创建预期 `MY_PROGRAM_PASS sum=55\n`：

```powershell
& C:/python/python.exe -c "from pathlib import Path; Path('D:/riscv/RISCV/tests/c_app/expected.txt').write_bytes(b'MY_PROGRAM_PASS sum=55\n')"
& C:/python/python.exe D:/riscv/RISCV/tests/c_app/run_app.py `
  --source D:/riscv/RISCV/tests/c_app/main.c `
  --expect-file D:/riscv/RISCV/tests/c_app/expected.txt
```

`puts` 追加 LF；`printf` 的 `\n` 输出 LF，不会自动转换为 CRLF。

## 文件与检查范围

| 路径 | 内容 |
| --- | --- |
| main.c | 可修改的用户示例 |
| run_app.py、pipeline.py | 通用入口、构建、审查、应用门控及串口输出验证 |
| wrapper.c | 调用 BSP 自检、用户 main 和打印返回值 |
| build/时间戳_随机号/ | 每次独立 ELF/BIN、反汇编、链接图、栈使用文件、manifest、构建收据及源/工具快照 |
| 同一 build 目录的 deployment_gate.json | 本应用仿真通过后生成的门控，绑定已成功硬件、软件与仿真证据 |
| D:/riscv/RISCV/sim/c_app/build/同名目录/ | ModelSim 日志、完整协议记录、原始 UART 字节、DDR 轨迹和结果 |
| D:/riscv/RISCV/sim/c_app/board/ | 默认实板 JSON 日志 |

`--log` 可指定新日志路径；不覆盖已有文件。失败保留产物和日志，不自动重试或清空串口。下载日志离线复核：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tests/c_app/run_app.py `
  --verify-log D:/riscv/RISCV/sim/c_app/board/my_program_01.json
```

镜像审查检查 ELF32 小端 RISC-V、入口 0x40000000、RV32I 指令、ELF/BIN 一致、段地址、装载地址和栈布局。代码、常量、data、BSS 合计位于低 60 KiB；0x4000F000–0x4000FFFF 为 4 KiB 栈。BSP 自动初始化 gp/sp、data/BSS、trap，并执行一次自检；每个用户源文件单独编译时将其 `main` 改名为 `app_main`。

仿真复用真实 CPU/互连/桥/UART MMIO/FIFO 及 DDR 用户口延迟模型，完整检查 LOAD/VERIFY/RUN、DDR 取指和退休、data/BSS、栈和输出；默认加速 UART 字节传输，不模拟真实 115200 引脚时序或 DDR PHY 训练。原成功位流的原速 UART/实板证据保留；每份新程序仍须用户完成实板验证。

## 当前边界

- 使用 `int main(void)`，完成检查与输出后返回。需要交互输入或永远运行的程序暂不适用这个自动结束验收。
- 复用现有 BSP `bsp.h`：UART、整数 printf、cycle/延时和 CRC32；未提供完整 libc、文件系统、malloc 或浮点 printf。默认 UART 轮询，新程序的中断/其他 MMIO 扩展需另建对应测试。
- 工具链为工程内 xPack GCC 15.2.0，RV32I / ILP32 / -Os；不启用硬件 M、C、F 扩展。仿真需要 `D:/modelsim/win64pe`，板级下载需要当前 Python 环境的 pyserial。
- 默认仿真限制 4000 万周期（含下载），宿主等待最多 2400 秒；必要时使用 `--sim-max-cycles` 增大周期预算，上限 20 亿。板级应用输出等待最多 40 秒，输出最多 64 KiB。不会因超时而绕过仿真或输出验证。
- 静态布局检查与仿真栈边界检查无法证明所有输入和路径都不会越界；这里验证的是本次完整执行。硬件、时钟或位流变更需要新的硬件候选和门控，旧门控不能自动认可。

当前开发/仿真与实板状态见 [实现验收记录](../../doc/software/通用C程序自动构建下载验证_2026-10-10.md)。CoreMark 正式跑分仍使用 [已有专用入口](../CoreMark跑分操作.md)，无需重新构建成功 CoreMark。
