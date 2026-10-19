# 16-byte 指令读缓冲验证入口

最新审查：任务014原始日志独立核验PASS，旧I8/D1 130项、新I8/D4 175项及lb/sll两例通过，97项输入/五镜像/九命令身份一致，git前后相同；lb实际24次数据读/1次AR/23次命中。build/review_data_cache4_20261011_a冻结56份证据及实际编译源码，状态DATA_CACHE4_EVIDENCE_AUDIT_PASS。无待领取仿真，不重跑014/013/009或历史全套。下一步用户PDS核验新D4时序/资源/初始化，再原run_measurements.ps1固定120次双模式各1轮实际DDR对照155529 I8/D1；新收益待测，旧+0.278ns不能套用。见[完整审查](../../doc/cpu/四行数据读缓冲实现与仿真交接_2026-10-11.md)。下方HDL NOT_RUN与等待任务014为历史。

最新实施：155529实际DDR原120次P/V正确但不足10秒，I8相对I4同BIN吞吐提高23.81%/22.94%，比较在build/compare_cache8_20261011_a。主桥现单独D1→D4（SHAf4a168e4），I8/单拍/数据优先不变，成功I8/D1在build/data_cache4_baseline_20261011_a。只交[任务014](../../DeepSeek/任务014_四行数据读缓冲关键仿真.md)：run_data_cache4.py/data_cache4_input_manifest.json的97项、新tb_data_cache4.sv旧/新130/175项、随机lb/sll两例，seed2026101114。check_data_cache4_plan.py只做静态数量核验，HDL NOT_RUN；新时序/资源/收益待测，不重跑历史PASS。后续用户PDS及原固定120次实际DDR各1轮对照155529；见[实板分析](../../doc/cpu/八行指令缓存实板性能分析_2026-10-11.md)及[实现](../../doc/cpu/四行数据读缓冲实现与仿真交接_2026-10-11.md)。下文无任务/现硬件时序PASS为成功I8/D1历史。

最新PDS：build/review_cache8_pds_20261011_a已只读核验PASS并冻结22份证据。所选seed2最终慢/快setup+0.278/+4.257ns，hold+0.134/+0.100ns；最终PnR FF8444/LUT7534（相对四行+604/+139），新位流9d632d44…6427，综合八行I和成功Loader初始化身份通过。用户下载后原run_measurements.ps1固定120次P/V各1轮实际DDR对照143832；新实板收益待测，无待领取DeepSeek仿真，见[审查](../../doc/cpu/八行指令缓存PDS时序审查_2026-10-11.md)。下文等待PDS是历史。

最新：任务013的ds_cache8_resume_20261011_153003已独立核验PASS：八行176项/6组、Errors/Warnings 0，ld_st/xor CPU装载DDR模型1056/418 words并tohost=1，72项及5镜像SHA匹配、六条命令退出0、git快照相同。build/review_cache8_evidence_20261011_a冻结53份证据，状态INST_CACHE8_EVIDENCE_AUDIT_PASS。四行124项复用，原012 FAIL保留；无待领取仿真，不重跑已通过项。下一步用户PDS/新时序与资源核验，再用原run_measurements.ps1固定120次双模式各1轮实际DDR对照143832；新收益待测，见[审查](../../doc/cpu/八行指令缓存计数判据复核与续测_2026-10-11.md)。下文待013/NOT_RUN为历史。

最新：任务012四行124项/6组PASS，Codex原144/196预期加法错误使runner中止，八行/ISA未跑；正确合计13L+72，八行预期176。原FAIL/清单/runner保留；只用新resume_cache8.py/eight_line_resume_input_manifest.json领取[任务013](../../DeepSeek/任务013_八行指令缓存计数修正续测.md)，补八行和ld_st/xor，不重跑四行。72项及冻结证据检查通过，RTL/TB未改、续测HDL未运行；证据在build/review_cache8_count_20261011_a，准备在build/eight_line_resume_preparation_20261011_a；见[复核](../../doc/cpu/八行指令缓存计数判据复核与续测_2026-10-11.md)。下文012待领取为历史。

当前实施：主桥已改8行128-byte I缓存，单行D及原握手保持。`run_cache8.py`交DeepSeek执行旧4/新8同`tb_inst_cache8.sv`关键对照及随机ld_st/xor，57项`eight_line_input_manifest.json`，seed2026101112。`--check-inputs`只读检查通过，准备镜像/差分在`build/eight_line_preparation_20261011_a/`，HDL NOT_RUN；旧成功桥/位流在`build/eight_line_baseline_20261011_a/`。只领取[任务012](../../DeepSeek/任务012_八行指令缓存关键仿真.md)，不重跑历史PASS；新资源/时序/实际DDR收益待测，见[实现交接](../../doc/cpu/八行指令缓存实现与仿真交接_2026-10-11.md)。

最新静态评估：`evaluate_icache_layout.py`只读取原120次BIN反汇编、当前源码与既有报告，清点4/8/16行索引映射及函数/分支地址跨度，不执行CPU/HDL或缓存轨迹仿真。证据在`build/evaluate_icache_capacity_20261011_a/`，建议下一候选8行128-byte，收益/新时序未知；未改RTL，无待领取DeepSeek任务。见[扩容评估](../../doc/cpu/I缓存扩容容量冲突与时序评估_2026-10-11.md)。

最新实板：`board/measure_20261011_143832_643`双模式120次正确且超过10秒。`build/review_data_read_board_20261011_a`及`build/compare_data_read_20261011_a`已离线核验/冻结证据；同BIN相对四行I/无D耗时降低3.08%/2.93%、吞吐提高3.18%/3.02%。`compare_data_read_fixed120.py`只用于本轮身份及日志比较，不能改旧收据或使用旧I阶段比较工具代替；当前无待领取仿真，不重复历史PASS。见[性能分析](../../doc/cpu/单行数据读缓冲实板性能分析_2026-10-11.md)，下方待测状态为历史。

最新审查：单行D读缓冲功能验证通过。任务010的lw实际297 words、24次数据读/1次AR/23次命中、tohost=1；89项输入及4份镜像匹配，原201+201桥检查和随机xori/bne保留、不重跑。综合收据`build/review_data_read_cpu_20261011_a/review_result.json`为DATA_READ_BUFFER_EVIDENCE_AUDIT_PASS，归档19份证据/89份输入，RTL仍b7c2b366，无新增阻断发现。当前无待领取仿真；用户下一步PDS重建/下载，用原run_measurements.ps1固定120次双模式各1轮作实际DDR比较，收益/时序/资源待测。lw命中计数不是CoreMark命中率；不足10秒只记对比。见[审查与实板交接](../../doc/cpu/单行数据读缓冲仿真审查与CPU续测_2026-10-11.md)。下方待补测/NOT_RUN为历史。

最新审查：任务009旧/新桥各201项及xori/bne已独立核验，证据在build/review_data_read_20261011_a；共用CPU模型RID0不能填D，随机两例无load，故整体待补CPU命中覆盖。只交DeepSeek`resume_data_read_cpu.py --tag <新tag>`跑一个lw（297 words、强制D_READS>D_AR>0及正数D_HITS），新89项清单，RTL仍b7c2b366。未运行适配TB/lw，旧84项清单/原结果不改写，不重跑已通过项。见[任务010](../../DeepSeek/任务010_数据读缓冲CPU返回ID适配续测.md)及[审查](../../doc/cpu/单行数据读缓冲仿真审查与CPU续测_2026-10-11.md)。

当前开发：主桥加入单行16-byte D读缓冲，HDL NOT_RUN。只交DeepSeek执行`run_data_read_buffer.py --tag <新tag>`：冻结四行I/无D与当前四行I/单行D同TB对照，随机xori/bne两例，84项输入；`--check-inputs`仅只读。短120次工具7项离线检查已通过，不追加重复；见[任务009](../../DeepSeek/任务009_单行数据读缓冲关键仿真.md)及[实现记录](../../doc/cpu/单行数据读缓冲实现与仿真交接_2026-10-11.md)。新版实板性能待测，下面四行成功日志是本轮基线。

最新实板：`measure_20261011_125621_924`固定120次双模式正式PASS，实际10.869/10.996秒，相对单行同BIN吞吐提高57.25%/62.80%。审查及四份原始日志/源码和位流副本在该目录`audit_formal120_20261011_a/`、`compare_cache4_20261011_a/`；新`compare_cache4_formal120.py`仅离线核验本轮日志及身份，不运行仿真/PDS/串口，不修改旧比较入口和收据。当前无新增RTL或仿真任务；见[实板分析](../../doc/cpu/四行指令缓存实板性能分析_2026-10-11.md)。下方四行实板待测为历史。

最新复核：四行缓存任务008的`ds_cache4_20261011_122922`旧单行/新四行定向各113项、随机lh/bge两例PASS，71项输入匹配；审查收据及29份证据/71份输入副本在`build/review_cache4_20261011_a/`。当前不追加仿真，用户下一步自行PDS/下载并跑固定120次双模式各1轮。新版实板性能、资源和时序待测，下面17.091/17.902秒是单行基线。见[审查交接](../../doc/cpu/四行指令缓存实现与仿真交接_2026-10-11.md)及[任务008报告](../../DeepSeek/任务008_结果_ds_cache4_20261011_122922.md)。旧runner/manifest/FAIL保留；`compare_formal120.py`绑定上一轮单行身份，不直接用于四行比较。下方NOT_RUN及旧门控要求为历史。

最新实板：measure_20261011_121321_483两项正式120次已核验PASS，同BIN吞吐增加2.35%/2.24%；原始审查、对比JSON/CSV及四份原始日志在该目录audit_formal120_20261011_a和compare_20261011_a。`compare_formal120.py`只离线核验两版实际UART证据，不能作为仿真或PDS工具。详见[最新性能分析](../../doc/cpu/按地址失效实板性能分析_2026-10-11.md)。本轮无RTL修改/新增仿真任务；下方实板NOT_TESTED为历史。

最新复核：`ds_invalidation_20261011_115005`关键TB新旧各54项、slti/lb两例已独立核验PASS，71项输入未变；审查及27份原始证据/71份输入副本位于`build/review_invalidation_20261011_a/`。新桥仍5fbf40c1版，当前无须追加仿真，交用户重建/下载位流并跑固定120次双模式各1轮。实际DDR性能NOT_MEASURED；下方HDL NOT_RUN是原交接状态。详见[复核记录](../../doc/cpu/正式120次计数与按地址失效优化_2026-10-11.md)。

当前阶段（2026-10-11）：正式120次实板双模式PASS；本轮桥按完整行地址选择性失效已准备，HDL NOT_RUN。只执行`run_invalidation.py --tag <新tag>`，一个关键TB旧/新对照和随机slti/lb两个ISA；`--check-inputs`仅离线检查。详见[任务007](../../DeepSeek/任务007_指令缓冲按地址失效关键仿真.md)和[正式计数及改动](../../doc/cpu/正式120次计数与按地址失效优化_2026-10-11.md)。旧run.py/resume_*及其清单绑定历史输入，不能套用到本轮新源码或修改旧哈希跳过保护。PDS/上板由用户完成，无需Generate Netlist或新门控；下方入口及未测试状态均为历史。

最新验收（2026-10-11）：任务006五次Loader全部经`review_loader_results.py`离线核验PASS，输出`build/review_checks_20261011_a/review_result.json`，三份原输入清单不变；23份通过的主RTL/工程源码保存于该目录`tested_sources/`。结合004/005已核验结果，本阶段所列仿真验收完成，已知FENCE.I/ma_data缺口保留。下一步用户完整重建PDS并Generate Netlist，Codex随后审查并建立新门控；优化版实板NOT_TESTED。[交接和步骤](../../doc/cpu/指令读缓冲仿真验收与PDS重建交接_2026-10-11.md)。旧门控/位流/FAIL不改写，下面NOT_RUN/未验收为历史。

当前入口（2026-10-11）：两处判据已适配。[任务006](../../DeepSeek/任务006_指令读缓冲判据适配后Loader续测.md)交DeepSeek，仅执行hello关闭缓冲对照及四项启用Loader。`resume_checks.py --suite compare`只离线严格核对原物理日志，已PASS；`--suite loader`才会编译/仿真新生成TB，当前NOT_RUN。`check_adapters.py`16项离线检查通过，不表示SV编译或整体验收PASS。新增checks_input_manifest.json270项，原两个manifest/旧runner/TB/原FAIL保留。详见[适配记录](../../doc/cpu/指令读缓冲测试判据适配与交接_2026-10-11.md)。下面为之前步骤历史。

最新结果（2026-10-11）：任务005的40支持ISA+6并发、短CoreMark CRC/计数、两条物理DDR Tcl、IRQ/MMIO分别PASS；物理九窗口单次运行PASS，原比较器因计时边界instret变化FAIL；四Loader因旧请求/事务一一对应假设FAIL，末尾检查未执行到。Codex完整离线审查后仍记整体NOT_PASS。两处测试适配尚未实现，不启动PDS/实板；设计RTL/原TB/runner/两份manifest/原FAIL未改。详见[续测结果复核](../../doc/cpu/指令读缓冲续测结果复核_2026-10-11.md)。`review_results.py`仅离线核对既有原始证据，不编译或仿真。下面“待续测/NOT_RUN”为之前步骤历史。

最新复核（2026-10-11）：DeepSeek unit enable0/1各49项PASS，Errors:0；fast仅11支持用例PASS，FENCE.I已知缺口诊断仅cycles不同导致旧整行比对中止，后续NOT_RUN。新增resume_fast.py和追加resume_input_manifest.json，仅排除末尾cycles且严格核验其他诊断，不改冻结原脚本/RTL/TB/原manifest。使用[任务005](../../DeepSeek/任务005_指令读缓冲快速回归续测.md)续测；unit无需重复，整体尚未验证。详见[复核记录](../../doc/cpu/指令读缓冲首次仿真复核与续测_2026-10-11.md)。下文NOT_RUN是初次准备历史。

状态：RTL/TB/执行入口已准备，**NOT_RUN**。用户要求出现仿真测试即停止交给DeepSeek；Codex本轮没有启动vlog/vsim/Icarus、PDS或串口。执行任务见[DeepSeek任务004](../../DeepSeek/任务004_16字节指令读缓冲仿真.md)。

设计仅改`myriscv/dual_sram_to_pango_ddr_bridge.v`：单项128-bit指令读缓冲、全地址tag，数据请求继续优先；所有被接受的DDR数据写保守失效。CPU、互连、MMIO、计数器和地址映射不改。参数INST_LINE_BUFFER_ENABLE默认1，0用于定向关闭测试；旧桥基线直接使用2B成功冻结源码，不通过修改当前RTL切换。

`input_manifest.json`固定本轮源/脚本/原位流/成功软件/既有证据身份。开始及结束均须匹配；输入变化停止，不能更新哈希冒充本轮通过。没有新位流或部署门控；旧2B门控会因桥源改变拒绝当前工作树，这是预期保护。

## 入口和输出

```powershell
& C:/python/python.exe -B sim/inst_line_buffer/run.py --suite unit --tag <新tag>
& C:/python/python.exe -B sim/inst_line_buffer/run.py --suite coremark --mode baseline --engine functional --tag <基线tag>
& C:/python/python.exe -B sim/inst_line_buffer/run.py --suite coremark --mode optimized --engine functional --tag <候选tag>
& C:/python/python.exe -B sim/inst_line_buffer/run.py --suite micro --mode baseline --engine physical --tag <物理基线tag>
& C:/python/python.exe -B sim/inst_line_buffer/run.py --suite micro --mode optimized --engine physical --tag <物理候选tag>
& C:/python/python.exe -B sim/inst_line_buffer/run.py --suite compare --engine physical --baseline-tag <物理基线tag> --optimized-tag <物理候选tag> --tag <对比tag>
```

目录为`sim/inst_line_buffer/build/<tag>/`，保存原始compile/simulation日志、计数CSV、退休轨迹、source_snapshot和line_buffer_receipt.json。coremark/micro复用既有2B oracle与2A性能分析，不改变CRC、退休解释器或统计判据。unit分别测新桥参数0/1，功能用户口模型只用于握手和数据正确性，不能用其时间宣称DDR性能提升。

baseline精确选择主工程2B成功冻结桥，SHA256 `dd7496ce3efda6133d0afbf6713c1f6b4fc4912ea4312a86505fa02edf72f8ea`；其余设计保持当前2B成功版本。optimized选择主myriscv桥。物理微基准复用同一固定BIN、128-bit用户口装载/全量回读、完整DDR IP/PHY/物理DDR模型及93.75MHz。九个observer窗口仍由既有逐退休解释器核验，13项硬件计数只覆盖该入口的首个自动窗口；短CoreMark的完整MMIO窗口另外验证全部13项。

compare要求两份执行receipt正确、相同manifest/模型/测试、基线与候选身份不同且instret一致，输出cycles/CPI/等待分类/DDR AR-AW变化。instret变化须返回原始PC/边界证据交Codex审查，不能降低断言或直接当作少执行指令的提速。无实测前不填写收益。功能模型对比的physical_performance_evidence=false。

## 必要回归

沿用`sim/cpu_performance_2b/main_rtl.py --suite fast|ddr|irq|mmio|loader`，不同新tag输出仍在`sim/cpu_performance_2b/build/`。fast覆盖40个既有支持ISA用例及6个并发/背压，FENCE.I/ma_data缺口由旧冻结RTL独立复现，不能白名单新失败。ddr隔离执行AGENTS要求的两条完整物理DDR Tcl；不覆盖旧日志。irq覆盖32 CPU+2 UART IRQ；mmio覆盖地址/access-fault/UART副作用；loader覆盖真实CPU从ROM下载校验到DDR运行。

DeepSeek按任务004逐阶段执行、完整返回原始证据；不得修改RTL/TB/判断、PDS/IP/软件/门控，不上板或Git推送。本轮默认不重跑未改变的UART底层TX/RX模块测试。全部仿真通过后由Codex独立审查，再由用户完成新PDS实现；旧位流和六应用基线不改写为优化成功。
