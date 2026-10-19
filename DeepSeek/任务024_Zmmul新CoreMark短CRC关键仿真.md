# 任务024：Zmmul新CoreMark软件短CRC关键仿真

## 当前唯一入口与范围

工程`D:/riscv/RISCV`。先读AGENTS、CODEX_HANDOFF顶部、本轮同一`doc/cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md`顶部。023原七例乘法与续测两例ISA已由Codex核原始证据PASS，旧/新lhu 320事件逐字节相同，or530事件/5trap正确；原FAIL确认为旧TB漏启动CSR探测的判据缺口，范围仅lhu样本。原成功证据复用，不重跑023/ISA/旧软件/历史。

用户已授权硬件乘法及独立新ISA软件，本任务只验**新增rv32i_zmmul软件**：performance_1、validation_1各一次真实CPU/SoC/x32 DDR用户口模型短CRC。主RTL/PDS/IP/Loader/原120次BIN未改；Codex已构建独立输出`tests/cpu_performance_2b/build/measure_zmmul_20261013_a/`，代码/端口/优化/计数器与原120源码一致，只改-march及打印FLAGS。每份ELF静态28个MUL、矩阵函数5个MUL，DIV/REM不允许；短版与120版BIN仅seed4_volatile=1/120字段不同，其余字节/sections/symbols相同。

本轮不测性能、不跑新120次全仿真、不重建原软件/host CRC/Loader，未覆盖完整Loader下载/PHY/实板。最终新120次实板CRC另由用户操作。任务文件不会自动调用DeepSeek。

固定tag **`ds_cpu_zmmul_coremark_crc_20261013_a`**，输出`sim/cpu_zmmul/build/ds_cpu_zmmul_coremark_crc_20261013_a/`。存在即停止，不换tag、不清理/重试或覆盖。执行前用户PDS已结束、无并发pds_shell；原权限、不改RPC/IPv6/工具配置，不追加工具启动预检。

```powershell
Set-Location 'D:\riscv\RISCV'
python sim/cpu_zmmul/run_coremark_crc.py --check-inputs
python sim/cpu_zmmul/run_coremark_crc.py --tag ds_cpu_zmmul_coremark_crc_20261013_a
```

**超时口径明确新增授权：vlib/vlog各60秒，每条vsim 900秒。** 不是沿023的180秒重试；这是新CoreMark带实际115200波特串行输出、13计数器的新任务。历史x32短CoreMark单例已用约161秒，本轮还包含真实MUL/I-D DRM及更长计数器UART输出，因此显式预留900秒；首次超时仍停止，不自行加时。整个Python入口用工具异步session等待，不以60秒外层命令上限终止已规定900秒的子进程；跟进输出使用工具wait/poll。不得自行修改任何超时/判据/权限或另起隐藏绕过入口。

## 冻结输入

清单`sim/cpu_zmmul/coremark_crc_inputs.json` SHA **ca07e018b059616254f58e198cc939522a9e7295708352b8839136a5a5147605**，保护421工程项+11外部依赖；包括原305输入/旧证据、新CPU功能审查、新软件ELF/BIN/源/反汇编/参考、当前SoC/桥、厂家MUL/I/D和新TB/入口。CPU仍43e45103…d6cfe，PDS c5f87d11…a6916，I64/D64桥d8ae0409…5cf09，Loader和旧位流/原软件保持。三厂家GTP_GRS/GTP_APM_E2/GTP_DRM36K_E1、五ModelSim工具/两本机参考/GCC可执行身份都冻结。

| 软件 | BIN SHA256 | bytes | 预期CRC最后一项 |
| --- | --- | ---: | --- |
| 新performance_1 | cd3a6c75bce420e386782321a6c161c2622a6edf81fb4a988a72ff1d146a0183 | 15204 | e714 |
| 新validation_1 | f2fd2202855a510a5ef6671a1cb385b6f4ae7d464e716bc3d3b3e1cf6e51b84c | 15212 | e3c1 |

原CoreMark算法不改；已有正确CRC参考复用，不把宿主参考的dummy clock当性能测量。新120 P/V SHA ab956eb4…39906 / 4168c1c4…febc1，以后上板使用，不在本任务执行。

DAT在`sim/cpu_zmmul/fixtures/coremark_{performance,validation}_1.dat`，已由冻结新BIN生成：4096个word，4092项是用户口模型读取的有效长度，前有效word逐字还原BIN，剩余padding为0；只供仿真，不写IP INIT或上板DAT。热点PC文件各5条，来源新ELF/反汇编的matrix_mul_*静态MUL地址，不能由DUT填充/改变。

## 命令与验收

一次vlib、一次vlog（34模块），当前SoC17 RTL文件（simple_mmio.v还包含cpu_perf_counters模块）、五mul源、四I/D生成源、三个真实厂家原语、只供未使用片内接口的ROM/RAM行为模型、未修改x32 DDR用户口模型、新TB。DDR和UART模型语义/时序沿现有x32直接加载入口，不含PHY训练；RESET_PC=40000000，CPU/SoC93.75MHz、UART115200不加速。未经过Loader协议下载，不能当Full Boot PASS。

然后performance_1→validation_1各一个标准-batch单顶层`tb_coremark_zmmul`，-logfile transcript、-do "run -all; quit -f"、MAX_CYCLES=60000000。命令stdout/stderr原生直写，首次失败保留停止，后续模式不执行，不用-c/Tcl内部vsim。编译与每例Errors/Warnings0；两条DRM04030130厂家非错误提示保留，不能滤掉；其它错误/Fatal/RPC/timeout停止。

每例须唯一：

```text
RESULT: PASS coremark_zmmul_direct cycles=<实测> retired=<实测> AR=<实测> AW=<实测> UART=<实测> MUL=<实测> MATRIX_MUL=<实测>
```

所有数须正数，正常$finish、console/transcript非空且换行归一后一致。TB检查总线error/CPU非ECALL异常/IRQ、真实UART引脚逐字节解码与发送字节相等、程序回到program_return、实际DDR AR/AW。新增只读观察必须证明真实MUL指令退休和matrix热点MUL退休均>0，不能只看静态反汇编。

`uart.txt`由新严格parser核完整输出、CRC五项、flags、hz/iterations/ticks及PERF2B13项，不能仅grep PASS。预期：

- performance：seed e9f5 / list e714 / matrix1fd7 / state8e3a / final e714。
- validation：seed18f2 / liste3c1 / matrix0747 / state8d84 / finale3c1。
- Compiler flags必须`-Os -march=rv32i_zmmul -mabi=ilp32; no LTO`，GCC15.2.0、iterations1、hz93750000。
- PERF2B state3、13计数完整/无重复；timer差=ticks=cycles，七分类之和=cycles，DDR transactions=AR+AW，0<instret<=cycles。
- 短迭代不到10秒的标准duration error可存在，但精确位置/其它输出/CRC必须匹配；**短CRC不记正式成绩或实板性能**，不能把“Errors detected”持续时间信息当算法FAIL或宽泛忽略其它error。

runner完成时result.json=PASS、两completed记录、每模式crc_review.json和实际MUL统计、四command.json退出0、输入再核/新git_before-after相等。只冻结新入口/TB/软件/仿真fixture，引用原023源身份，不重复复制所有历史设计/日志。DeepSeek不额外重跑Codex软件构建/parser fixture或旧coremark_x32入口。

## 交付与后续

报告列完整CRC五项、UART字节数/引脚校验、MUL/MATRIX_MUL实际退休数、13计数守恒、命令时长/退出/$finish/RPC、冻结输入/git、新BIN/ELF/DAT身份和实际日志路径。失败交原命令/日志/已完成与未执行，保留停止；不改源/清单/判据/超时/权限/成功镜像，禁止PDS/串口/上板/Git。

Codex收到后核原始证据并继续用户最终I64/D64+Zmmul PDS核时序/137登记源/实际APM/Loader INIT/位流，以及同位流原120次P/V各一轮+新Zmmul120次P/V各一轮。板子可用后用户执行，程序不由Codex打开串口。新软件CRC尚未通过、新位流/性能尚未测量；不因CPU023功能PASS提前标本任务或实板PASS。
