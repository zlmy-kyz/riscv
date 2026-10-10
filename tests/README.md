# 测试程序和已验证镜像

更新日期：2026-10-10。UART Loader、统一BSP及旧成功位流十轮复位下载/VERIFY/RUN已完成实板验收；用户重建的主工程新位流也已完成六轮Hello/CRC32/CoreMark复验，540响应及6次RUN全部PASS，549项成功快照保存。下一任务是[CPU性能瓶颈分析与优化](../doc/CPU性能优化起点与验收约定_2026-10-10.md)，当前没有优化RTL或性能提升结论。

当前软件入口为 `bsp_workflow/`，ROM常驻Loader在 `uart_loader/candidates/verify_run_hello/`。不要重建覆盖成功ELF/BIN/DAT、位流或日志；主工程新位流与此前隔离位流使用各自工具和门控。最新结论见[开发交接](../doc/CODEX_HANDOFF.md)、[新位流六轮实板验收](../doc/board/主工程新位流六轮实板验收_2026-10-10.md)及[Loader交接](../doc/uart_loader/UART_Loader换对话交接_2026-10-08.md)。

新 C 程序使用 [c_app 通用入口](c_app/README.md)：`run_app.py --source ... --expect ...` 自动编译、审查、完整仿真并生成独立门控，随后按用户确认进行 COM11 下载和输出验证；`--prepare` 只准备，`--deploy` 复用准备结果。工具及示例已通过仿真/离线检查，新程序实板验收仍由用户完成。

正式 CoreMark 跑分请看 [CoreMark 跑分操作](CoreMark跑分操作.md)：包含 KEY0/COM11 准备、60 次正式运行命令、精确分数读取及短 CRC 检查方法。

```text
tests/
├── README.md
├── CoreMark跑分操作.md          # 当前成功主工程位流的正式跑分步骤
├── c_app/                      # 新C通用入口；源文件、wrapper、run_app.py/pipeline.py及README
├── uart_loader/                 # ROM常驻Loader；verify_run_hello成功DAT，旧阶段快照保留
├── bsp_workflow/                # 统一BSP和UART下载DDR应用，十轮及新位流六轮实板PASS
│   ├── README.md
│   ├── main_hello.c / main_crc32.c / main_irq.c
│   ├── bsp.h / uart.c / timer.c / crc32.c
│   ├── startup.S / linker.ld / trap.S / trap.c
│   ├── core_portme.c / core_portme.h / ee_printf.c
│   ├── build.py / run.py
│   ├── build/                   # 已成功应用的program.elf/bin、manifest和构建收据
│   └── build_versions/          # 后续--tag隔离输出，须另行验证和冻结
├── coremark_baremetal/          # 原独立裸机端口与旧预置RAM→DDR启动成功归档
│   ├── build.ps1 / startup.S / linker.ld
│   ├── build/                   # 原ELF/BIN/DAT保留
│   └── verified/               # 两组旧60次成功DAT与verified_image.json
├── development/                 # 历史C实验工作副本，现为输出30
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

| 目录 | 用途 | 仿真 | 实板 | 成功镜像/归档 |
| --- | --- | --- | --- | --- |
| uart_loader | ROM常驻Loader，UART分块LOAD、完整DDR CRC32 VERIFY、RUN重校验后跳转 | 阶段⑦至⑩及合并VERIFY/RUN/DDR/Hello定向验收PASS | 原阶段、Hello合并验收、后续应用及新位流复验PASS | candidates/verify_run_hello/build/loader_rom.dat与loader_ram.dat；原阶段verified归档保留 |
| development | 当前工作副本，现为输出30 | 修改后重验 | 不自动继承实板验证 | build/main.dat |
| fpga_uart_pc_output_30 | 成功输出30归档 | PASS | 用户确认收到30 | main.dat |
| pc_uart_fpga_uart_pc | PC→FPGA→PC Echo成功实验 | 四层PASS | 功能PASS，用户确认复位后重复回显 | main.dat归档；build/main.dat为原验收/上板输入 |
| coremark_baremetal | CoreMark独立裸机端口，原算法源在coremark-main | 两组单迭代及两组60次Full Boot CRC通过 | 用户UART确认两组60次CRC与至少10秒验收PASS，约17.76/18.76秒 | 成功归档verified/performance_60/main.dat、verified/validation_60/main.dat，各附verified_image.json；原构建保留 |
| bsp_workflow | 统一startup/linker/UART/timer/trap/CRC32及构建/下载流程 | 八组真实CPU仿真与54项离线检查PASS；两组60次仿真仅验证启动，完整算法已由实板补齐 | 原位流十轮PASS；主工程新位流六轮PASS，正式CoreMark约17.75/18.75秒；IRQ探针仅仿真PASS | build/各应用ELF/BIN；原518项及新549项快照分别在sim/bsp_workflow/board/first_success/和sim/bsp_workflow/rebuilt_20261010/board/first_success/ |

## 当前DDR应用流程

`C源码+BSP → GCC → ELF/BIN及manifest审查 → UART LOAD写DDR → CRC32 VERIFY → 唯一RUN → 严格应用输出检查与日志`。ROM仅保存Loader代码，片内RAM为Loader常量、状态、缓冲及栈；CoreMark应用BIN通过UART写到DDR运行，不需要为每个应用重新生成FPGA位流。

`bsp_workflow/linker.ld`将应用入口设为0x40000000，代码/常量/data/BSS共用低60KiB，顶部0x4000F000–0x4000FFFF为4KiB栈；startup初始化gp/sp、data/BSS及trap入口。轻量printf支持整数、字符串、字符及十六进制，不支持浮点格式；IRQ软件队列等限制见[准备记录](../doc/software/统一BSP与十轮复位下载验收准备_2026-10-10.md)。

**通用新 C 入口已在 `c_app/` 独立实现。** `run_app.py --source ... --expect ...` 支持项目内新 C 程序及多文件，用新应用仿真门控复用成功 Loader；无需修改旧应用白名单。原 `bsp_workflow/build.py` 仍只接入Hello、CRC32、CoreMark及仅仿真的IRQ探针，原下载门控仍只允许六个已验收manifest。--tag仅隔离旧入口的构建；新程序操作、结束条件和使用限制见 [c_app 说明](c_app/README.md)。

后续构建已有应用时使用尚未存在的新tag，例如：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tests/bsp_workflow/build.py --application hello --tag trial_01
```

输出在 `tests/bsp_workflow/build_versions/trial_01/hello/`。这是新构建，须完成对应仿真与新的隔离门控，不能直接用当前冻结工具下载。性能分析优先复用已成功的两份CoreMark BIN，固定软件身份，不重复编译。

## 位流和测试入口

| 版本 | 成功位流（工程相对路径） | PC入口 | 实板证据 |
| --- | --- | --- | --- |
| 当前主工程重建版 | generate_bitstream/board_top.sbit，SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf | tools/uart_loader/candidates/rebuilt_20261010/run_board.py | sim/bsp_workflow/rebuilt_20261010/board/；六轮、540响应、6次RUN，549项快照 |
| 原隔离成功版 | sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit，SHA256 31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0 | tests/bsp_workflow/run.py --acceptance | sim/bsp_workflow/board/；十轮、834响应、10次RUN，518项快照 |

两批均已完成验收，不必重新跑才能使用。需要复测当前主工程版时，使用新的日志目录：

```powershell
& C:/python/python.exe D:/riscv/RISCV/tools/uart_loader/candidates/rebuilt_20261010/run_board.py --directory D:/riscv/RISCV/sim/bsp_workflow/rebuilt_20261010/board/retest_01
```

用户负责下载指定位流、关闭串口助手、每轮KEY0后等待DDR初始化再回车；工具使用COM11、115200 8N1，自动执行Hello/CRC32/两组短CoreMark/两组正式CoreMark六轮。正式60次必须引用本批同一位流的对应短CRC实际日志，不能混用两批位流证据。已有日志目录保留，失败停止且不自动重试；完成后独立核验原始日志。Codex不操作板子或串口。

当前两主IP INIT_FILE为 `tests/uart_loader/candidates/verify_run_hello/build/loader_rom.dat`与loader_ram.dat。只换应用BIN复用成功位流；修改CPU/互连/桥、初始化或硬件配置后须新候选位流、相应回归及时序检查，并生成新门控，不跳过旧哈希检查。

详见[新位流验收](../doc/board/主工程新位流六轮实板验收_2026-10-10.md)和[原十轮验收](../doc/software/统一BSP与十轮复位下载实板验收_2026-10-10.md)。

## 历史C/DAT实验构建

下面是输出30、Echo及原CoreMark预置RAM镜像流程，独立保留，不作为当前UART下载DDR应用的默认入口。从工程根目录执行：

构建脚本使用工程根目录的 `xpack-riscv-none-elf-gcc-15.2.0-1/bin/`，
需自行安装相同版本的 Windows xPack RISC-V 工具链；编译器发行包不上传仓库。
转换需要 Python 3。Echo 已验收的 ELF/BIN/DIS/DAT 一并保存，首次克隆后可以直接
安装工具链（runner 使用其中的 nm）并运行仿真，无需先重建成功镜像。

```powershell
& ./tests/development/build.ps1
& ./tests/fpga_uart_pc_output_30/build.ps1
& ./tests/pc_uart_fpga_uart_pc/build.ps1
& ./tests/coremark_baremetal/build.ps1 -Mode performance -Iterations 1 -OutputDirectory D:/riscv/RISCV/tests/coremark_baremetal/build_versions/performance_trial_01
& ./tests/coremark_baremetal/build.ps1 -Mode validation -Iterations 1 -OutputDirectory D:/riscv/RISCV/tests/coremark_baremetal/build_versions/validation_trial_01
```

输出30归档的根main.dat不得被重新构建覆盖；该目录构建只写build/。
Echo最终文件为tests/pc_uart_fpga_uart_pc/build/main.dat；仿真直接读取同一个文件：

```powershell
& C:/python/python.exe sim/uart_echo/run.py
```

仿真环境、TB、模型、运行脚本及日志仍在sim/uart_echo，tests只保存CPU软件和构建产物。
先构建→Full Boot验收同一DAT→RAM IP→FPGA；仿真后不能另生成DAT直接上板。
Echo实板功能及复位重复回显已由截图和用户反馈确认；长时间压力/二进制/错误/IRQ另立验收。
详情见[Echo实板确认](../doc/uart/UART_Echo实板基本回显确认_2026-10-07.md)；输出30历史TX成功不代替双向验收。原CoreMark成功镜像不重建，新的OutputDirectory选择尚不存在的目录；仿真PASS不能自动继承实板PASS。
