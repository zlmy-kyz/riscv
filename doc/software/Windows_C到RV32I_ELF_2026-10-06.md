# Windows C 到 RV32I ELF 的首次构建

日期：2026-10-06。

## 目的与改动

使用根目录新增的 `xpack-riscv-none-elf-gcc-15.2.0-1/` 编译用户提供的 `tests/development/main.c`，建立可重复的裸机构建入口。保留 main.c 原内容。

- `tests/development/startup.S`：提供 `_start`，初始化 gp 和 16 字节对齐的 sp，清零 word 对齐的 BSS，再调用 main；main 返回则循环停留。未设置 CSR、异常处理或中断。
- `tests/development/linker.ld`：入口与代码从 DDR `0x40000000` 开始，在 DDR 首个 64 KiB 内布局；顶部保留 4 KiB 栈，初始 sp 为 `0x40010000`。此为本测试选择的布局，并非重新划分整个工程的 DDR 地址。
- `.data` 的 LMA 与 VMA 相同，要求装载器将其放入最终 DDR 地址；startup 不从 ROM 另行复制 `.data`。BSS 为 NOLOAD，由 startup 清零。
- `tests/development/build.ps1`：通过工程内的工具链路径编译，无须全局修改 PATH。输出集中在 `tests/development/build/`。

本步骤未修改 CPU、SoC、RTL、TB、PDS、存储 IP 或现有板级 ROM/RAM 镜像。

## 复现

在 PowerShell 中执行：

```powershell
Set-Location D:\riscv\RISCV
& .\tests\development\build.ps1
```

如果终端执行策略不允许运行 ps1，可仅对新启动的进程指定策略：

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\riscv\RISCV\tests\development\build.ps1
```

主要参数：`-march=rv32i -mabi=ilp32 -O2 -g -ffreestanding -fno-builtin -fno-pic -fno-pie -msmall-data-limit=0 -nostdlib -nostartfiles -Wl,--no-relax -Wl,--build-id=none`；使用本目录的 startup/linker，并在输入源之后链接 `-lgcc`。未链接 libc，若未来调用 printf/malloc/memcpy 等，需要另行提供实现或适配库。

输出：`main.elf`、`main.bin`、`main.map`、`main.dis`、`main.readelf.txt`、`compile.log`、`size.txt`。BIN 是 objcopy 得到的原始字节文件，不是本工程 IP 所需的 DAT 或已配套清单的 RAM 镜像。

## 实测结果

- GCC 能运行，版本为 xPack 15.2.0。
- `-march=rv32i -mabi=ilp32 -print-multi-directory` 返回 `rv32i/ilp32`。
- 构建退出码为 0；ELF 为 ELF32、小端、RISC-V EXEC，入口 `0x40000000`，属性 `rv32i2p1`，栈对齐属性 16 字节。
- size：text=100、data=0、bss=0；原始 BIN 大小 100 字节。ELF 文件还含调试信息，文件长度不等于代码大小。
- 用 `objdump -d -M no-aliases` 核对当前反汇编，只见 RV32I 指令，无乘除、压缩、浮点或原子指令。
- main 为局部 volatile 变量分配 16 字节栈帧，执行 10+20，将 c 写到栈中；最终循环地址为 `0x40000060`。按该静态代码推导 c 的地址为 `0x4000fffc`，此处并未通过仿真或实板读取数值。
- 编译 warning：c 未被后续读取。volatile 访问仍被保留，已核对反汇编。
- 链接 warning：LOAD 段为 RWX；当前裸机统一 DDR 布局没有配置段级权限，仍可生成 ELF，不代表已完成硬件运行验证。

## 未覆盖与后续

本步只验证编译、链接、ELF 属性和当前程序的静态指令。未进行 CPU 执行、异常、中断、C 全局数据初始化定向仿真或实板验证。当前程序没有 UART 输出或 MMIO PASS 上报。

下一步若要在当前 SoC 上运行，需要建立独立镜像转换/仿真入口，核对装载地址、加载内容、入口、BSS/栈与诊断区域不重叠，再验证执行结果。切换板级镜像时还必须适配片内 RAM 容量及装载清单，并重新生成存储 IP；不能直接把 ELF 或 BIN 指向现有 IP 初始化配置。
