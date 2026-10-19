# 2026-10-19当前：043用户授权直接板试，P/V各一次，COM9/JTAG

当前运行用户生成的043两条顺序写缓冲位流，以同一固定布局`measure_perf27_fixed_20261018_a`P/V300各一次比较，保持93.75MHz，不重建BIN或重跑旧硬件基线。双项入口新支持`-ResetMethod key0|jtag`，默认key0兼容历史，本轮指定jtag：

```powershell
Set-Location D:\riscv\RISCV
& D:\riscv\RISCV\tools\uart_loader\candidates\perf_2b\run_perf27_measurements.ps1 -Port COM9 -ResetMethod jtag -BuildTag measure_perf27_fixed_20261018_a -LogDirectory ("sim/write_buffer_two_entry/board/task043_pv300_" + (Get-Date -Format 'yyyyMMdd_HHmmss'))
```

P/V每轮都先JTAG下载同一份043位流，关闭串口助手，KEY0保持释放不再按键；等DDR就绪再Enter装载，运行不复位。首败停止/原日志不覆盖。对照旧P240458577/V240545509周期，CRC5275/8803；应用输出27项计数，完整RVLD各295应答/唯一RUN。

离线`-PlanOnly -ResetMethod jtag`已至`sim/write_buffer_two_entry/board/task043_direct_plan_20261019_01`通过，串口未打开。本轮是用户直接板试授权，FENCE忙队触发未完成、KEY0暖复位及完整043/时序范围不因此成为PASS；尚无新实测或提速结论。下方旧版“无需再跑”及“保持041+042旧位流”均为历史，不能用于本轮043身份。

# 2026-10-18：PERF27固定布局版（以下历史）

当前状态已完成：固定布局P与JTAG恢复后的V均已核295实际应答/唯一RUN、CRC5275/8803、27项和尾RX通过，耗时2.564891488/2.565818762667秒。[最终原证据收据](../../../../sim/cpu_cache_perf/fixed_layout_20261018_a/board_review_final_01/review.json)。**本轮无需重跑成功P/V。** 下方“只补V”为恢复前的历史步骤；同位流JTAG恢复成功，KEY0暖复位问题仍待定位，原首PING失败日志保持。默认固定布局tag继续作为后续已授权测量入口，不自动开启新轮次。

当前固定布局P已完整通过295回应/CRC5275/27项，2.564891488秒，恢复原固定BIN附近；V在第一条PING超时，尚无下载/运行，原日志保留。现在只补V，不再运行双项PS1重跑P。JTAG重新下载当前同一现有位流，KEY0保持释放，不再按键，等DDR就绪后Enter：

```powershell
python tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py --application validation_300 --port COM9 --reset-method jtag --log sim/cpu_cache_perf/board/perf27_fixed_v_jtag_01/validation_300.json
```

新增`--reset-method key0|jtag`，默认key0兼容原流程；jtag模式记录用户声明方法及`user_reported_KEY0_press=false`，旧`user_KEY0_confirmation`兼容字段在此只确认KEY0释放，不代表按键或JTAG被独立观察。PC新增read_response保留超时时0/部分原始应答及expected/received长度，原5秒deadline/无重试/无flush不变。旧失败缺失的rx_hex不补填、不推断为0RX。V-only PlanOnly已核295回应，未开串口，[证据](../../../../sim/cpu_cache_perf/fixed_layout_20261018_a/board_review_01/review.json)。无需重编RTL/BIN或PDS；本轮KEY0问题未宣告修复。下方双项命令为本次首败前入口。

`run_perf27_measurements.ps1`及Python默认BuildTag已切`measure_perf27_fixed_20261018_a`。原热点/工作区/计时地址保持，新增读出在独立段；每项295个RVLD应答/唯一RUN，输出仍为27项。原固定及首版PERF27 BIN/日志保持，显式`--build-tag`或`-BuildTag`可选择历史tag，`--verify-log`未指定tag时从原记录manifest路径自动识别，兼容旧日志。

保持当前含041+042的位流，无需PDS或重下载位流；关闭串口助手，P/V各轮按提示KEY0释放/等待DDR/Enter，运行不复位：

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_perf27_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_cache_perf/board/perf27_fixed_300_01
```

当前新布局版尚未实板执行，新P/V各一次对照本轮原固定BIN240454027/240543747周期，不重跑旧基线。实际时钟仍须93.75MHz。新BIN均37328字节，包含独立段前的零填充，下载比旧BIN慢，但不计入CoreMark窗口；不要把UART下载/打印的整段时间当内核成绩。新目录/首败停止/原始日志保留规则不变。

[布局与离线收据](../../../../sim/cpu_cache_perf/fixed_layout_20261018_a/review.json)确认原86符号/四段及旧加载字节除post-ROI跳转8字节外全保持，所有代码ISA/ELF边界审查通过；`perf27_fixed_plan_20261018_01`PlanOnly每项295预期应答、未开串口。旧UART只用于schema重放，不是新BIN运行证据；下方“仅补V”是首版移址软件的历史状态，不用于当前新布局轮次。

# 2026-10-18：27项计数PERF27入口（以下历史）

当前只补V：首P实际完整输出27项，但新解析器只认小写hex，误拒绝BSP输出的大写。现只修PC匹配，原C/BIN/位流保持；P CRC5275/27项已离线复核，原FAIL与末尾额外RX检查缺项不覆盖，不重复P。新命令保持当前同一位流，KEY0释放等DDR后Enter：

```powershell
python tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py --application validation_300 --port COM9 --log sim/cpu_cache_perf/board/perf27_v_parser_fix01_01/validation_300.json
```

本次V-only PlanOnly已核151预期回应/唯一RUN，串口未开。[修复收据](../../../../sim/cpu_cache_perf/software_20261018_a/parser_case_fix01/review.json)保留原FAIL身份及解析器前后差异；支持大小写没有放宽ID/位宽/READY/守恒。下方双项PS1留作新的完整轮次，本次不要用它重复P。

新增`run_perf27_measurements.ps1`和`run_perf27_measurement.py`，默认COM9，新独立BIN在`tests/cpu_performance_2b/build/measure_perf27_20261018_a`。它读取27项，拒绝旧13项输出/缺项/重复/未READY/不守恒/错误率/错误频率，命中率在UART中以basis points输出，PC再显示百分比；旧工具与固定BIN保持。每项151条RVLD应答（旧BIN为123条），唯一RUN，首败停止，不自动重试或覆盖日志。元数据和源码/新BIN身份另存identity.json；本地位流哈希只作本地文件记录，不证明板上内容，不要求旧PDS门控。

用户下载包含041+042的本次位流、关闭串口助手，P/V每轮按提示按KEY0并释放、等待DDR就绪再Enter；运行期间不复位：

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_perf27_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_cache_perf/board/perf27_300_01
```

默认`-CoreClockHz 93750000`必须对应实际时钟；当前BIN/BSP仅支持该工作点，其他值在打开串口前拒绝。新输出格式/布局改变，不能与旧固定P/V直接称为严格同BIN性能对照；旧EX工具仍只打印13项。软件构建/静态ISA审查、离线格式检查、PlanOnly已完成，最终PlanOnly目录`sim/cpu_cache_perf/board/perf27_plan_20261018_02`，串口未打开；本版动态/计数/板测尚未验证，不把离线PASS当实板PASS。

离线计划可加`-PlanOnly`并使用新的日志目录。单项原始板测日志复核入口：`python tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py --verify-log <原始JSON> --output <新审查JSON>`，自定义构建须附相同`--build-tag`。它复用严格CoreMark CRC/13项窗口与分类守恒判据，再核新增14项及能力/READY/命中率。完整硬件与软件验证要求见[任务042](../../../../DeepSeek/任务042_等待周期与目标复用机会计数.md)。

# 2026-10-18：已复核的现有EX位流直接板试（以下历史）

最新P300首败：123装载/VERIFY/RUN应答成功，随后40秒应用RX0，V未开始。**当前停止重复板测，原失败目录保留，不延长deadline**；转[任务038最小定位](../../../../DeepSeek/任务038_EX重定向冲刷串行排空与RUN零输出定位.md)。下文命令为该首败之前的入口，不据此再次运行。

使用`run_ex_redirect_reviewed_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_ex_redirect/board/ex_redirect_reviewed_300_01`，每轮下载`sim/cpu_ex_redirect/board_review_20261018_a/observed/generate_bitstream/board_top.sbit`后KEY0/等待DDR/Enter。现有网表/位流为EX候选，但工作树CPU已回旧ID版本；新工具分别记录身份，原`run_ex_redirect_measurements.ps1`记录当前源码的方式不适用于本次版本差异。P/V固定BIN各一次，对比036、频率保持93.75MHz，首败停止。详情见[EX阶段顶部](../../../../doc/cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。

# 2026-10-18：036实板已核，037待PDS（历史）

036固定P/V已核，P2.417657269/V2.417739125秒，较035差异不足0.002%不认定提速，不重跑成功测量。当前037修改了数据互连译码/ready，先由用户PDS，尚无037板测入口；下文036工具绑定原036身份，不用于当前037候选。[037阶段](../../../../doc/cpu/MINI_数据互连并行译码与ready_2026-10-18.md)。

# 2026-10-18：036用户直接板试（历史命令）

当前使用`run_task036_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_request_presample/board/task036_300_01`，固定P300/V300各一次，对比035成功实板基线。两轮均先JTAG重新下载同一个最终036冲突CE修复版位流，再按提示KEY0/等DDR就绪/Enter；保持93.75MHz，首败停止、新目录保留。修复后时序未核、完整动态验收NOT_RUN和KEY0问题保留，工具不以PDS/位流审查作门。命令与边界见[036阶段顶部](../../../../doc/cpu/MINI_桥请求字段预采样_2026-10-18.md)。

# 2026-10-13补充：Zmmul300固定测量

新工具run_zmmul300_measurements.ps1选择performance_300/validation_300，各123条RVLD响应+唯一RUN，COM9，默认新日志sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul。300次CRC final5275/8803，保持原UART协议与13计数口径，原工具不改。实际串口执行前要求024 V1续测software_gate和Codex独立codex_review存在并身份一致，当前两项均已核验通过，用户已完成新300实板P/V且Codex原始证据复核通过，各123响应+唯一RUN、CRC5275/8803，原日志保留，不重复测量；PlanOnly仅离线不会开串口。用户继续同已下载位流，每轮KEY0/等待DDR/Enter，首败停止，不覆盖日志。CMD使用powershell -NoProfile -File绝对脚本路径，详见[本轮阶段顶部](../../../../doc/cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。新300按每迭代指标对照已完成RV32I120，不重跑旧120；实际不足10秒仍只比较。以下历史工具与120计划保留。

# 用户操作的 2B 主工程上板工具

最新正式运行：默认两项已改为performance_120/validation_120，预计约17.5/18.3秒，必须实测达到10秒且CRC/13计数正确。保持当前已下载位流，用原PowerShell命令即可，默认COM11/115200。新final CRC为d340/200d，旧60次软件/日志保留；不直接比较不同迭代数总时间。[120次准备与运行](../../../../doc/coremark/CoreMark计数测量120次正式运行准备_2026-10-11.md)。下方“默认两组60次”为此前历史。

最新精简约定：`run_measurements.ps1`默认仅跑performance_60和validation_60各1轮，原命令可直接使用；其他项目须显式`-Applications hello,crc32`等选择，不默认追加短测/六应用/三轮重复。Windows PowerShell 5.1的默认两项PlanOnly已通过，未打开串口。[精简约定](../../../../doc/project/精简验证约定_2026-10-11.md)。下方六项默认顺序为此前历史；当前固定60次不足10秒时仅作性能对比。

最新实际结果：[读缓冲首轮实板计数分析](../../../../doc/cpu/指令读缓冲首轮实板性能计数分析_2026-10-11.md)：measure_20261011_110113_999六应用核验PASS；固定60次内核8.746145483/9.151185163秒，同BIN约2.03/2.05倍速度，但不足10秒不记正式CoreMark成绩。原2B基线保留，新日志已归档；以下NOT_TESTED为工具准备时历史。

最新入口（2026-10-11）：用户要求只准备下载测试工具，新增`run_measurements.ps1`/`run_measurement.py`，**不依赖Generate Netlist或新部署门控**。保持原Loader和固定版本c BIN，默认COM11/115200，六项按顺序、失败停止、日志自动新目录；下载目标位流后执行：

```powershell
& D:/riscv/RISCV/tools/uart_loader/candidates/perf_2b/run_measurements.ps1
```

每项提示KEY0/DDR就绪后回车；CoreMark等待完整13项计数及PERF2B_DONE。60次不足10秒可通过固定BIN测量校验但不记正式成绩。离线15项检查与六下载计划通过，未打开串口，新硬件实板NOT_TESTED。操作、单项补测和日志复核见[新下载工具说明](../../../../doc/cpu/读缓冲固定BIN下载测试工具_2026-10-11.md)。下面`run_board.py`/旧门控/位流身份为2B历史入口，保持原样，不能用其命令测试新桥。

用户21:13生成主位流，22:20补导出实现网表，源码/时序/8192字初始化/8个实现存储实例与计数器审查通过。工具默认已绑定本次主位流的新门控。用户23:06完成performance_60_retry1补测，当前六应用6/6实板PASS；此前等待中人工复位记录保留。正式performance/validation为17.758519147/18.761056267秒；见[完整实板统计](../../../../doc/cpu/CPU计数器2B首轮实板统计与补测_2026-10-10.md)。完整实现身份见[新位流审查](../../../../doc/board/CPU计数器2B主工程新位流审查_2026-10-10.md)。Codex未重新生成软件、运行PDS或打开串口。

默认仅接受 `sim/cpu_performance_2b/build/main_pds_board_20261010_a/deployment_gate.json` 白名单中的六个manifest和根目录位流。状态PERF2B_MAIN_PRE_BOARD_AUDIT_PASS，272项输入/820项证据及272份冻结副本逐项核验；任一绑定输入变化会拒绝执行。`--gate <路径>`可选择明确的门控；不能把旧门控当新硬件身份。历史隔离门控/位流/成功档案没有覆盖。
旧 BSP/rebuilt 工具继续绑定旧成功硬件，不能用旧门控部署 2B。
Codex 只运行 `--plan-only` / `--verify-log` 和离线 mock；实际 COM11 操作由用户执行。

用户在 PDS 配置下载窗口选择：

`D:/riscv/RISCV/generate_bitstream/board_top.sbit`

SHA256：`4231dcd62362f567b7ce47553c472832604fd78bed99ece6913004f24614fe76`。
下载后关闭串口助手。每个命令会提示 KEY0/DDR ready，再打开 COM11，115200 8N1。
日志不覆盖，RUN 不重试。先 Hello、CRC32、两组短 CRC，再运行匹配正式 60 次。

```powershell
$perfTool = 'D:/riscv/RISCV/tools/uart_loader/candidates/perf_2b/run_board.py'
$perfLogs = 'D:/riscv/RISCV/sim/cpu_performance_2b/board/main_pds_first'
& C:/python/python.exe $perfTool --application hello --log "$perfLogs/hello.json"
& C:/python/python.exe $perfTool --application crc32 --log "$perfLogs/crc32.json"
& C:/python/python.exe $perfTool --application performance_1 --log "$perfLogs/performance_1.json"
& C:/python/python.exe $perfTool --application validation_1 --log "$perfLogs/validation_1.json"
& C:/python/python.exe $perfTool --application performance_60 --crc-log "$perfLogs/performance_1.json" --log "$perfLogs/performance_60.json"
& C:/python/python.exe $perfTool --application validation_60 --crc-log "$perfLogs/validation_1.json" --log "$perfLogs/validation_60.json"
```

各命令结束自动独立复核原始协议帧和计数打印。正式模式要求本候选同 gate/位流/模式的短测量 BIN 实板 CRC 日志。
逐条执行，上一步成功后再执行下一条；先完成FPGA位流下载，PC脚本只负责UART应用下载。每条会要求按KEY0等待DDR就绪再回车。使用新的日志路径，不覆盖原记录；第二轮请换日志目录并使用该轮匹配短CRC日志。
离线计划不会打开串口：`--application performance_60 --plan-only --log <新路径>`。
已有实板日志可离线重核：`--verify-log <日志> --output <新审查JSON>`。
有效实板结果包含 cycles/instret/CPI/IF/MEM/branch/DDR 命令，以及 CRC、时间、93.75MHz 和候选位流身份。
门控中NOT_TESTED是创建时历史状态，当前实际应用结果见完整统计；不能把离线计划或模拟串口 fixture 当实板证据。已有首轮及补测日志不要覆盖，当前成功performance 60次为performance_60_retry1.json；以上命令是首次操作流程，复验使用全新日志目录。

本次离线检查：`sim/cpu_performance_2b/build/main_pds_board_20261010_a/offline/result.json`，六计划564响应/6次RUN，错误位流、CPU输入、manifest与冻结副本四种篡改均被拒绝；下载/打印mock为`sim/cpu_performance_2b/build/main_pds_transport_20261010_a/result.json`，129响应及四种错误帧/输出拒绝通过。两者均serial_opened=false，不是实板PASS。
# 最新约定：固定120次短时比较（2026-10-11）

单行数据读缓冲候选已准备但尚未仿真/部署。原run_measurements.ps1默认双模式不变；完整CRC/计数/协议正确的120次若不足10秒，只记COREMARK_FIXED_BIN_MEASUREMENT_PASS并继续第二模式，formal=false，正式成绩仍须至少10秒。review_formal120.py对应输出COMPARISON状态，不把短时当正式PASS；原成功BIN不重建。CRC/协议/输出/守恒失败仍拒绝。7项离线工具检查已通过，不表示新硬件实板PASS。见[本轮交接](../../../../doc/cpu/单行数据读缓冲实现与仿真交接_2026-10-11.md)。
