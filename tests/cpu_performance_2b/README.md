# 2026-10-18当前：固定原被测布局，新增读出独立段

最新验收：固定布局P/V均已实板完成295实际回应/唯一RUN、CRC5275/8803、27项/冻结/守恒及完整尾RX，P240458577/V240545509cycles，2.564891488/2.565818762667秒，对原固定BIN不足0.002%差异。[最终收据](../../sim/cpu_cache_perf/fixed_layout_20261018_a/board_review_final_01/review.json)。旧移址约1.45%开销已基本消除，不重复本轮P/V；V由同位流JTAG冷恢复成功，KEY0暖复位根因不算已修。下文V未运行/待补描述为历史。

固定布局P最新实板CRC5275/295应答/27项完整通过，240458577cycles/2.564891488秒，对原固定P只差+0.001892%，已恢复；V在第一条Loader PING超时，程序尚未下载/执行，不是新的软件运行失败。原BIN不改，只按[当前工具入口](../../tools/uart_loader/candidates/perf_2b/README.md)同位流JTAG冷恢复仅补V；PC现在保留部分RX，不延长超时、不覆盖原失败证据。完整动态/KEY0边界保持。

使用`build_perf27_fixed.py`，新产物`build/measure_perf27_fixed_20261018_a/{performance_300,validation_300}`，均37328字节。以原冻结ELF段字节为主体，仅原perf_dump入口8字节跳到0x40008014；原86符号、text/rodata/data/BSS地址/大小与其余旧加载字节全部保持。不重编算法，工作区0x40003ba8、计时/GP/栈保持。新增读出代码/常量/暂存独立放0x40008000–0x400091cf，暂存随BIN初始化，不扩大原BSS清零循环。

`perf27_fixed_software.py`严格核原布局与字节、跳转ABI、所有可执行段ISA白名单/ELF装载字节/非重叠/栈边界；`perf27_software.py`根据layout_schema选择对应审查，27项打印/大小写/READY/守恒判据保持。旧原固定BIN与首版PERF27 BIN保持，旧构建脚本未改；要复现新构建用`python tests/cpu_performance_2b/build_perf27_fixed.py --tag <新标签>`，不覆盖现有输出。

上板脚本默认新tag，见[工具当前入口](../../tools/uart_loader/candidates/perf_2b/README.md)。[静态及离线收据](../../sim/cpu_cache_perf/fixed_layout_20261018_a/review.json)通过、PlanOnly各295预期应答/唯一RUN；未运行新CPU/实板，不承诺准确周期。BIN因填充到独立地址而增大，下载等待在ROI外；硬件未改，保持当前041+042位流即可，无需PDS。

# 2026-10-18：PERF27独立串口读出程序已构建（以下历史）

首P后修正：生产BSP把`%x`也打印为大写，`perf27_software.py`现同时接受a–f/A–F，保持8/16位宽及全部语义判据；C/ELF/BIN未改，不重建。原首败P已完整打印27项，CRC5275和计数由[离线修复审查](../../sim/cpu_cache_perf/software_20261018_a/parser_case_fix01/review.json)核对；原FAIL和未执行末尾额外RX检查缺项保持。V未运行，按[当前工具说明](../../tools/uart_loader/candidates/perf_2b/README.md)仅补V，不重复P。下文“尚未CPU/实板执行”为首P之前的构建状态。

新增`perf27.c`、`build_perf27.py`、`perf27_software.py`；原`perf.c/.h`与固定`measure_zmmul300_20261013_a`整目录保持。新P/V300在`build/measure_perf27_20261018_a/{performance_300,validation_300}`，BIN为18936/18944字节，ELF布局/全部可执行指令白名单审查通过，未执行新CPU仿真或实板。

PERF27复用原ARM/两次CYCLE窗口，在CoreMark打印结束后核扩展ID/项数、等待124.bit3与134.bit3（最多0.5秒），读取原13+缓存6+诊断8项低/高字。打印全部27项、能力与命中率basis points（10000=100.00%，NA=关闭或分母0），最后`PERF27_DONE`、`PERF2B_DONE`。非法元数据/未冻结/超时/计数越界或不守恒打印`PERF27_FAILED`，解析器拒绝，不冒充成功。CoreMark算法、RV32I+Zmmul与300迭代保留，CRC5275/8803参考复用；新BIN/布局不同，不能作为与旧固定BIN严格同输入的性能对照。

当前软件/BSP固定实际core_clk=93.75MHz、UART115200；改变频率须先调整对应软件与外设参数，不能套旧时间。运行使用`tools/uart_loader/candidates/perf_2b/run_perf27_measurements.ps1`，不是旧`run_ex_redirect_measurements.ps1`。详见[工具说明](../../tools/uart_loader/candidates/perf_2b/README.md)和[接口合同](../../doc/cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)。

已完成构建、严格解析离线格式检查（明确标注合成扩展）与PlanOnly，见[软件收据](../../sim/cpu_cache_perf/software_20261018_a/review.json)；不等同新CRC/计数硬件/DDR或板测PASS。已有构建不覆盖；需要重建时`python tests/cpu_performance_2b/build_perf27.py --tag <新标签>`，上板工具用对应`-BuildTag`。041+042相关动态验证仍按任务042及用户PDS顺序进行。

# 2026-10-13补充：新Zmmul改300次

用户指定新Zmmul CoreMark迭代数300。独立build_zmmul300.py已构建build/measure_zmmul300_20261013_a，P/V各28 MUL、全ISA白名单/无DIV-REM，BIN15204/15212byte，与旧Zmmul120只seed4四字节120→300；旧软件和端口保持。300次native CRC final5275/8803，dummy clock不记成绩。真实CPU P/V短CRC已由Codex核原始证据PASS（P1复用、V1仅一次），codex_review已生成；新300实际DDR P/V现已核通过：5.452637/5.438676秒，按cycles/iteration比较同位流原120归一吞吐1.907970/1.981712倍；不足10秒只比较，原120和新300均无需重跑。入口见[当前阶段](../../doc/cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。以下历史120构建和验收记录保留。

# 2B 独立测量软件

最新正式软件（2026-10-11）：`build/measure_20261011_120/{performance_120,validation_120}`已准备，默认下载工具使用120次，按当前实测预计17.49/18.30秒，须实板确认至少10秒。新BIN只比原60次改变seed4_volatile数据，指令代码/布局不变；native CRC参考final d340/200d，软件审查通过，不是实板PASS。构建入口`build_120.py`，旧1/60次BIN和算法保留。[正式运行准备](../../doc/coremark/CoreMark计数测量120次正式运行准备_2026-10-11.md)。

本目录只新增计数读出。算法、统一 BSP、原成功 CoreMark BIN、Loader DAT 都保留。
`perf.c/.h` 通过 32-bit MMIO 配置和读取 13 个冻结的 64-bit 计数器，再通过既有 UART 打印。
测量 BIN 在 `portable_init` 的 BSP 自检后 CANCEL → START_PC=0 → STOP_PC=0 → ARM；
下一次 CYCLE 接受边沿 S 开始，第二次 CYCLE 接受边沿 T 冻结，统计 `[S,T)`。
打印在 CoreMark 的 `PORT_DONE` 之后，排除下载、CRC、BSP 自检、算法结果打印与计数器打印。

验收版本：`build/measure_20261010_c/{performance_1,validation_1,performance_60,validation_60}`。
四个 BIN 已独立构建/ISA/布局审查；两组 1 次完整 CRC 与 MMIO/UART 读出通过。
60 次仿真只覆盖下载/VERIFY/RUN/启动，完整正式测量待用户实板。
`measure_20261010_a/b` 为早期未验收软件，已清理；最终c版本保留。

```powershell
C:/python/python.exe tests/cpu_performance_2b/build.py --tag new_tag
```

新 tag 拒绝覆盖。保持 RV32I/ILP32、GCC15.2.0、-Os、无 LTO、2000-byte buffer、93.75MHz。
后续硬件基线和优化候选必须使用逐字节相同的测量 BIN。不能把测量 BIN 与旧成功 BIN 的布局差异解释为硬件提速。
`start_time/stop_time` 地址仍为 `0x400007d0/0x400007f4`；硬件另支持原成功 BIN 的 PC 标记自动窗口，但原 BIN 没有 UART counter dump。

寄存器、统计口径、证据和实板命令见 [2B 记录](../../doc/cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)。
