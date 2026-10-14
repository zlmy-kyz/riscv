# MINI-200H DDR3 跑分与 C 程序交接

这个目录提供一次可独立使用的板上交接：下载本目录的 `board_top.sbit`，用 `board.py` 经 UART Loader 把 BIN 写入 DDR3，执行并收取 CPU 的串口输出。对象是 **PG2L200H MINI 板**；串口为 115200 8N1，端口号以使用者电脑为准。摄像头仍处于设计阶段，不包含在这份位流中。

## 文件和身份

| 文件 | SHA-256 | 用途 |
| --- | --- | --- |
| `board_top.sbit` | `41aeec27af4dbe2cf177f9e7b51add48040a82d8ad794c22cf6842fb03e9d284` | 本机 2026-10-14 19:53 生成的 MINI 主工程位流，内含 ROM/RAM Loader 初始化 |
| `performance_300.bin` | `677ee766fd0fc34d1558d778a343743a1cd9287ecdbbc182cb4681af3374517d` | 已用于任务032实板 P300 对比 |
| `validation_300.bin` | `461c635c46c86c8e719ced403b045bca468ded7299870bf2f87f8547ce11719b` | 已用于任务032实板 V300 对比 |

冻结 P300/V300 在原板实测分别为 **2.242630368 秒**、**2.240607787 秒**，都不足 CoreMark 正式成绩所需的 10 秒，只能作工程比较。本机位流文件的 SHA 已核对；旧实板串口日志没有记录位流 SHA，因此不能仅凭该日志独立证明下载的恰为此文件。同学应在相同板型下载本目录文件后重新验收。

仓库同时提供与本机 MINI PDS 工程对应的 CPU/SoC RTL、六块 IP 的配置及生成源、约束、Loader ROM/RAM 初始化 DAT、BSP、CoreMark 算法源码和 Loader 协议源码。本目录的 `pds_inputs.json` 锁定这次交接的 **143 个实际工程输入**，`check_pds.py` 核对其路径和 SHA。旧的 `tests/c_app/run_app.py`、`tools/uart_loader/candidates/perf_2b` 工具带有本地冻结门控及旧板位流路径，不用于这个交接入口。

## 准备

1. 克隆本仓库，安装 Python 3 和 `pyserial`（`python -m pip install pyserial`）。如需编译 C，另装 RV32 交叉 GCC，给 `--toolchain` 传入含 `riscv-none-elf-gcc.exe` 的目录；Windows 本机若已有 `xpack-riscv-none-elf-gcc-15.2.0-1/bin` 可省略。编译器不随 GitHub 仓库发布。
2. 使用 Pango 下载工具把 `share/mini_ddr3/board_top.sbit` 下载到相同的 PG2L200H MINI 板。关闭占用串口的其他程序。
3. 每次 `run` 命令按提示按下并释放 KEY0，等待 DDR 初始化完成，再回车。掉电后 FPGA 配置和 DDR 数据都需要重新建立。工具不自动重试，不覆盖既有日志。

## 从源码重新运行 PDS

本工程的 PDS 输入现已和本目录位流一同交接。先克隆到 `D:/riscv/RISCV`；ROM/RAM 的 `.idf` 和生成包装器、DDR `.idf` 的约束入口仍含该绝对路径。换目录时须在 PDS 中重新指定两份 Loader DAT 与 DDR 约束、重新生成相关 IP；路径变动后清单哈希自然不再相同，需要建立自己的输入身份。使用 **PDS 2022.2-SP6.4** 打开根目录 [`RISCV.pds`](../../RISCV.pds)，目标为 **PG2L200H、FBB676、-6**，顶层 `board_top`，约束为 `constraint_check/temp_constraint_file.fdc`。在编译前执行：

```powershell
python share/mini_ddr3/check_pds.py
```

显示 `PDS INPUTS PASS ... inputs=143` 表示本地 CPU/SoC RTL、ROM/RAM、DDR3、I64/D64 Cache、乘法 IP、include 和初始化 DAT 与这次交接相符。随后从 **Compile → Synthesize → Device Map → Place & Route → Report Timing → Generate Bitstream** 完整运行；检查工具报告中的错误、时序和板卡引脚。重新实现产生的是**新位流**，即使源输入一致，也要用新结果验收串口 Loader、DDR 执行和跑分，不能套用上文冻结位流的板上通过结论。PDS 安装目录、器件许可和下载器由使用者本机提供；仓库不包含编译数据库。

## 使用冻结程序进行工程性能比较

在仓库根目录的 PowerShell 中先离线核对下载计划：

```powershell
python share/mini_ddr3/board.py run --bin share/mini_ddr3/performance_300.bin --kind coremark --mode performance --iterations 300 --plan-only
python share/mini_ddr3/board.py run --bin share/mini_ddr3/validation_300.bin --kind coremark --mode validation --iterations 300 --plan-only
```

实板运行时分别使用新日志名；工具严格比较每条 Loader 应答，完成 `PING → LOAD → DDR CRC32 VERIFY → RUN`，最后检查 CoreMark CRC、计时和 13 项计数：

```powershell
python share/mini_ddr3/board.py run --bin share/mini_ddr3/performance_300.bin --kind coremark --mode performance --iterations 300 --port COM9 --log sim/mini_share/board/p300_01.json
python share/mini_ddr3/board.py run --bin share/mini_ddr3/validation_300.bin --kind coremark --mode validation --iterations 300 --port COM9 --log sim/mini_share/board/v300_01.json
```

命令结束显示 `RESULT: PASS`，JSON 的 `parsed.seconds`、`parsed.iterations_per_second` 和 `parsed.formal_10s` 给出板上结果。300 次在当前基线属于短测，即使协议和 CRC 全通过，`formal_10s` 仍为 `false`。每次运行都须使用新的日志路径和新一次 KEY0 复位；COM9 只是原板实例，其他电脑按实际端口修改。

## 新建 C 程序并从 DDR3 执行

参考 [`tests/c_app/main.c`](../../tests/c_app/main.c)，使用 [`tests/bsp_workflow/bsp.h`](../../tests/bsp_workflow/bsp.h) 的整数 `printf`、UART、计时和 CRC32 接口。入口为 `int main(void)`，自行检查结果，成功时打印一个唯一的标志并返回 0。不能依赖完整 libc、动态分配或浮点 `printf`。应用链接到 `0x40000000` 起的 DDR 区，程序上限 60 KiB，最高 4 KiB 作为栈；不要与本交接的 Loader ROM/RAM 内容混放。

```powershell
python share/mini_ddr3/board.py build-c --tag my_first_c --source tests/c_app/main.c --toolchain C:/path/to/xpack/bin
python share/mini_ddr3/board.py run --bin tests/c_app/build/share_my_first_c/program.bin --kind c --expect 'MY_PROGRAM_PASS sum=55' --port COM9 --log sim/mini_share/board/my_first_c_01.json
```

`--source` 可以重复指定仓库内的多个 `.c` 文件，构建目录用新的 `--tag` 创建，不覆盖旧程序。构建后工具调用现有 ELF/ISA/布局审查，生成 BIN 和 `share_manifest.json`；`run` 比对 Loader 回应、等待 `C_APP_DONE return=0`，并确认 `--expect` 文本只出现一次。`--expect` 是使用者提供的结果声明，程序本身必须先检查计算是否正确。

## 构建时长满足要求的 CoreMark

当前 P300 约 2.24 秒。可先尝试 1800 次，预计约 13.5 秒；这是估计，最终以板上 `parsed.seconds >= 10` 为准。新 BIN 与冻结 P300 不同，要给它新的日志和独立结果，不沿用历史通过结论。命令会编译包含 13 项计数输出的 Zmmul 版本：

```powershell
python share/mini_ddr3/board.py build-coremark --tag p1800_01 --mode performance --iterations 1800 --toolchain C:/path/to/xpack/bin
python share/mini_ddr3/board.py run --bin tests/cpu_performance_2b/build/share_p1800_01/program.bin --kind coremark --mode performance --iterations 1800 --port COM9 --log sim/mini_share/board/p1800_01.json
```

`build-coremark` 对生成的 ELF/BIN 做布局和 RV32I+Zmmul 指令审查；串口运行会检查 CoreMark 自校验、种子 CRC、计时与性能计数。只有 `formal_10s=true` 且 `RESULT: PASS` 的实板运行才可称符合本项目的正式时长条件。CoreMark 官方报告还需遵守源码包自身的规则。

## 已检查范围

本交接制作时，本机对两个冻结 BIN 各生成了 **123 条严格 Loader 响应计划**，且 P300 计划逐条与原实板日志相同；新 C 示例成功编译并通过 ELF/ISA/DDR 布局审查，1800 次 CoreMark P 版成功编译并通过 Zmmul 指令审查。新的交接工具未打开串口，也未重新下载位流；新同学的实板结果需要用其新 JSON 日志确认。
