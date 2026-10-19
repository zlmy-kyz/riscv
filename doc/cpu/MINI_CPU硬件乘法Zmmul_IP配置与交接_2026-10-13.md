# MINI CPU硬件乘法Zmmul：IP配置与接入交接

用户后续已授权D写命中字节更新，主RTL与新IP已接入，当前开发入口转到[独立D缓存写命中阶段](MINI_D缓存写命中更新与字节写接入_2026-10-13.md)和任务025；下文“仅评估/尚未接入”是此前记录。Zmmul300成功结果和软件继续复用，未改CPU/构建软件或重跑旧测量。

## 最新：Zmmul300实板P/V核验通过，同位流每次迭代耗时减少47.6%/49.5%（2026-10-13）

用户已按方案重新生成D IP并要求检查。Codex只读核IDF/生成wrapper/template/厂家底层/PDS登记及当前桥，[配置收据](../../sim/mini_board_migration/build/data_write_hit_preparation_20261013_a/ip_config_review.json)=**DCACHE_BYTE_WRITE_IP_STATIC_CONFIG_PASS_BRIDGE_PORT_PENDING**。WR_BYTE_EN从0→1、BE_WIDTH从1→32、RD_BE_WIDTH从1→4，其余IDF配置相同，新增真实输入wr_byte_en[31:0]且经wr_byte_en_mux接入底层。写256bit/addr6与读32bit/addr9都为2048byte；Byte Size8、OUTPUT_REG/FAB_REG0、SYNC复位、低功耗/地址strobe/clock enable/初始化关闭均保持。256:32比8满足厂家开启byte-write且无address-strobe的静态上限，未执行编译/仿真，不把静态检查当新功能/时序/资源PASS。

新wrapper SHA bf62d32342a11ba6fad55f11c2413716a834c7028e9a1d8660a5f1a5477514a7，IDF60e668a1a1912fec3ca12d0f8bb59181639a494f032c16743a0c8d9beffefa51；厂家底层66905d13…303f保持。相对已核PDS137登记输入只有D wrapper/IDF两项改变，项目仍61adbe3c…5d475、I IP/CPU/桥/Loader均保持；根位流仍64445ecf…ac8ee4，已下载硬件和新源码配置是两个不同事实。旧成功冻结源/结果不修改，新配置尚无功能证据。

当前桥d8ae0409…5cf09的dcache实例未连接新wr_byte_en，仍仅完整填充写入并将写命中行失效。接入前不能按已完整接通设计直接实现：整行填充要mask32'hffffffff，写命中要把锁存CPU4bit wstrb按32bit槽扩为32bit字节掩码，并在原DDR写完成边沿进行局部数据写入、保留D valid/tag；I侧仍沿用失效。本次只完成配置/接线检查，未修改RTL/PDS/IP、未新建仿真任务/启动HDL或开串口，不自动补造新阶段PASS。

前次用户询问下一步性能提升，当时只读评估当前CPU/桥/IP与既有实板计数，未改RTL/IP/PDS/软件或新建仿真任务，未运行仿真/PDS/上板。建议下一项优先**D-Cache写命中按字节更新，继续阻塞write-through/no-write-allocate**：当前桥在data_line_write_hit把整行valid清0，store仍等原AW/W完成；下一次同行load可能重新读DDR。新300每次仍有约15200个共享AR/17200个AW，MEM约45.5%、IF约22.6%，存在减少写后再读填充的明确机制，但没有写命中/写致失效后重新填充分项，不能承诺收益百分比或将全部AR认作这种浪费。

评估时生成dcache.v WR_BYTE_EN=0、WR_DATA_WIDTH256/WR_ADDR_WIDTH6、RD_DATA_WIDTH32/RD_ADDR_WIDTH9，无法直接局部改写缓存的几个字节。若用户授权实施，需用户通过PDS IP配置对**dcache**开启Enable Byte Write/Byte Size8、预期32字节使能，保留2KiB与原读延迟/时钟/复位，并核生成实际端口/参数；厂家生成源支持字节使能，256:32比8在其启用byte-write且无address-strobe的静态限制内，但新生成配置、实际DRM资源/时序与功能仍需新证据，不凭静态参数承诺。I64配置不需因这项改变。

单项方案：接受store时锁存D写命中/tag/行/32bit槽/wstrb；保持原DDR AW/W稳定与响应完成时刻；确认原写被DDR用户口接收后按strobe更新D命中行，保留其valid/tag。读填充仍整拍写全32字节；写miss不分配、不读取旧整行；I侧同址写仍沿用失效以维护代码写入/Loader路径，MMIO不走这个缓存。此方案不提前答复store、不增加在途DDR事务/改仲裁，因此可限定在桥和D IP，CPU不需要随之修改。若实施，关键验证覆盖SB/SH/SW字节合并、零strobe、写后读/同行其它word/tag冲突、DDR AW/W背压、I侧失效/复位；按现有精简约定一组关键桥测试及直接相关最小集成，再用户PDS/同冻结P300-V300各一次，不重跑历史。

后续写缓冲用于隐藏DDR写等待，但需处理RAW、指令可见性、MMIO/FENCE排空与复位；当前既无读写等待分项也无write-invalidate重填统计，先不选其作为这次更大的变更。RISC-V对内存/IO排序与指令写入后的取指可见性有独立要求，不能把提前答复store当无语义变化的局部改动，参考[官方内存序说明](https://docs.riscv.org/reference/isa/unpriv/mm-eplan.html)及[官方Zifencei说明](https://docs.riscv.org/reference/isa/_attachments/riscv-unprivileged.pdf)。本工程实际支持范围仍以CPU解码为准，不因引用规范新增支持声明。继续扩容量/减少乘法级数/改频各需另评估；本轮只选下一项候选，不自动实施或追加测量。

用户已完成[performance_300日志](../../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul/performance_300.json)和[validation_300日志](../../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul/validation_300.json)，各COM9/115200一次，KEY0确认/无自动重试。Codex只读重解完整RVLD各123响应、唯一RUN、VERIFY/无额外RX，严格比对manifest/ELF/BIN与全部UART输出、五CRC final5275/8803、300次/rv32i_zmmul/93.75MHz/state3/PERF2B_DONE、timer差=ticks=cycles、七分类和=cycles、DDRtransactions=AR+AW全部通过。两新日志绑定同新本地位流64445ecf…ac8ee4，源137项/当前RISCV.pds/300全软件与既有PDS、功能门保持；没有重新生成软件/位流或重复旧测量。

[独立审查收据](../../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/codex_review_20261013/result.json)=**ZMMUL300_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_NORMALIZED_PERFORMANCE_REVIEW_PASS**。复现审查入口python -B sim/cpu_zmmul/build/preparation_20261013_a/review_board_zmmul300.py已执行，输出存在即停止，不能为复核重跑实板。新P日志SHA7d22774ec4a87eacdf940bfcfc11378674683ff6241cbd8963509d29eb2add55，新V33b28e89458af3cd85561797b2fddd4933de7bd576834a2828dd9a7afe2848e1；连同同位流旧RV32I120和历史I32/D32各两份，共6日志逐哈希保持，报告引用原路径，不重复归档相同输入。Codex未开串口/启动HDL/PDS；下载为用户报告，本地SHA不是独立FPGA读回。

下表旧列为同I64/D64+Zmmul位流运行原RV32I120，新增列为Zmmul300；两边同算法、种子模式、-Os/ilp32/noLTO/93.75MHz/2000byte，ISA、代码生成/布局和迭代数不同。按每次迭代归一，披露初始化摊销差，不能直接拿总秒数比较快慢。

| 指标 | performance：RV32I120 → Zmmul300 | validation：RV32I120 → Zmmul300 |
| --- | --- | --- |
| 总cycles | 390130001 → 511184720 | 404170803 → 509875909 |
| 总秒 | 4.161386677 → 5.452637013 | 4.311155232 → 5.438676363 |
| cycles/iteration | 3251083.342 → 1703949.067 | 3368090.025 → 1699586.363 |
| 精确iterations/second | 28.836542 → 55.019250 | 27.834767 → 55.160480 |
| 归一吞吐倍数 / 每次耗时下降 | 1.907970倍 / 47.5883% | 1.981712倍 / 49.5386% |
| CPI | 3.918106 → 4.716083 | 3.816455 → 4.705159 |
| instret/iteration | 829758.892 → 361306.013（−56.4565%） | 882517.975 → 361217.607（−59.0697%） |
| DDRtransactions/iteration | 54582.333 → 32554.270（−40.3575%） | 54388.425 → 32413.580（−40.4035%） |

MUL软件路径显著减少每次迭代的退休指令和软件乘法相关控制流，分支次数/iteration下降63.8119%/66.5179%；共享DDR AR/iteration下降36.8040%/36.7865%，AW下降43.1860%/43.2738%。CPI上升不能判断CoreMark变慢：它的分母退休指令数和指令组合变了，原软件乘法循环中大量便宜指令被移除，同时硬件MUL按EX等待执行；真正的工作单位指标cycles/iteration下降约一半。约1.91–1.98倍是同位流新软件路径的观察结果，含代码生成/布局与不同迭代摊销，不单独声称乘法IP纯延迟倍数。

新互斥周期占比：MEM45.6177%/45.4735%、IF22.5899%/22.7058%、branch recovery7.8230%/7.7950%、OTHER23.9694%/24.0257%，其余三类0。每次MEM等待已减少38.5286%/38.8089%、IF等待减少51.5777%/53.8224%，占比提高是总周期减少更快，并非访存绝对变慢。MEM+IF仍约68.2%，后续性能评估应关注访存/取指等待。当前计数不区分指令/数据AR和读/写等待，AW数量大不能直接证明store延迟为主；本轮只分析，不改RTL或追加测量。

新OTHER均比instret多14136000周期（每次47120cycle，约占全周期2.8%），与当前CPU纯EX乘法等待计入OTHER的实现相符。板级没有专用MUL退休/等待计数器，不能把这个差值当直接MUL观测，也不能将约24%的OTHER全部归给乘法延迟；实际退休乘法的直接观察证据来自023与024短CRC仿真，本轮通过新ISA已审BIN的实际DDR CRC/输出验证执行路径。

两模式均约5.45秒、不足10秒，结果为COREMARK_FIXED_BIN_MEASUREMENT_PASS，**不是正式CoreMark成绩**。UARTIterations/Sec=60由300除以截断整数秒5得出，精确值约55；时长ERROR与Errors detected为预期门，CRC通过。每模式只测一次，无波动估计，不自动增加到其它迭代数或重跑。本次授权的Zmmul接入→关键功能/短CRC→PDS核验→实际DDR原120与新300路径已完成，范围仍Zmmul/DIV-REM不支持，无全ISA结论；旧P1未知退出保持、无需新的仿真或上板任务。

以下为此前V1核验/300上板准备与历史记录，以上最新结果为准。

## 前次：024续测原始证据与300软件交接核验PASS，下一步用户同已下载位流实板P300/V300（2026-10-13）

[DeepSeek交付报告](../../DeepSeek/任务024续测_结果_ds_cpu_zmmul_coremark_v1_resume_20261013_a.md)已核原始log/transcript/UART/native命令/输入/冻结副本与Git。[独立收据](../../sim/cpu_zmmul/build/ds_cpu_zmmul_coremark_v1_resume_20261013_a/codex_review.json)=**ZMMUL_P_V_SHORT_CRC_AND_300_HANDOFF_RAW_EVIDENCE_REVIEW_PASS**。只运行V1一次，P1功能证据与编译结果复用，无P1/vlib/vlog重跑；Codex只执行只读review_coremark_v1.py，未启动HDL/PDS/串口。

V1 vsim实际**1321.1670269秒**、上限3600秒，exit_code/native_exit_after_wait均0、未超时、无cleanup，标准-batch/单顶层/既定plusargs与计划完整相同。唯一RESULT PASS、正常$finish、ErrorsWarnings0、两条原04030130保留、RPC/FAIL/Error/Fatal/timeout零；console/transcript换行归一全文一致。实际UART1121byte=TB报告UART，完整输出五CRC **18f2/e3c1/0747/8d84/e3c1**、FLAGS rv32i_zmmul、iterations1、hz93750000、state3、PERF2B_DONE均正确。

全程TB实测11085406cycles、4275052retired、AR72198/AW21363、**MUL9618/矩阵MUL9396**；测量冻结窗口1842118cycles、361057instret，start87238/stop1929356，差=ticks=cycles，七分类382038+923086+128817+0+0+0+408177=1842118，DDRtransactions83602=AR66429+AW17173。全程TB统计含启动/输出，冻结窗口是软件测量区间，两者不能混用。短CRC仅功能门，不将其模型秒数或22分钟宿主运行耗时当实板性能。

新74项/原目录62项及原421+11依赖门全部保持，67新冻结副本逐哈希核验、Git before=after。另只读确认worker_launch/entered/result同pid44368、唯一V1，6份复制编译库新旧SHA全部相同。137登记源/独立300全软件产物与新位流匹配，software_gate SHA **cb94c1e36eac70b4ce1af4856b95f7f21000982faf69e39b2fea5aef48447eca**。原P1完整功能证据复用，原native exit仍UNKNOWN；旧result RUNNING/缺失command/git_after保持，不补造或篡改旧执行结论。新的P/V软件功能门已闭合，旧编排元数据边界仍明确。

新300工具require_gate已由Codex只读检查通过，[上板交接收据](../../sim/cpu_zmmul/build/preparation_20261013_a/board_handoff_zmmul300_after_v1.json)=ZMMUL300_SAME_BITSTREAM_BOARD_HANDOFF_READY_NOT_RUN；新日志目录尚不存在，未开串口或进行300测量。当前无待领取仿真，不再执行--start，不改RTL/IP/PDS/时钟或重建BIN；已下载的新位流64445ecf…ac8ee4可继续使用，无需新PDS或再次下载。

用户关闭串口助手，每模式按KEY0并释放、等待DDR就绪、按工具Enter，一次LOAD/VERIFY/RUN，运行期间不复位。新P300/V300各一次，123响应+唯一RUN，final CRC分别 **5275/8803**；首次失败保留日志并停止后续模式。用户当前CMD窗口使用：

```cmd
powershell -NoProfile -File "D:\riscv\RISCV\tools\uart_loader\candidates\perf_2b\run_zmmul300_measurements.ps1" -Port COM9 -LogDirectory "D:\riscv\RISCV\sim\cpu_zmmul\board\coremark_i64_d64_zmmul_300_01\zmmul"
```

固定新软件为tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/P300 BIN677ee766…74517d（15204byte）、V300461c635c…11719b（15212byte）；软件和28 MUL/算法/port已核，不因实板待测重建。收到新日志后继续核Loader/CRC/13计数/同本地位流，并按每次迭代周期和吞吐对照本轮同位流RV32I120（P3251083.342cycles/iteration、28.836542次/秒；V3368090.025、27.834767）。迭代数不同须披露初始化摊销差，不能直接比较总秒数；300次是否达到10秒由实测决定，不足仅比较，不自动加迭代数或重复测试。实板收益现在仍未测。

以下为此前V1准备与旧测量记录，以上最新结果为准。

## 前次：用户授权024只补V1，新Zmmul改300次，独立软件已构建；HDL与300实板待执行（2026-10-13）

用户授权“下一步补齐任务024的V1验证与收尾，再用同一位流运行新Zmmul BIN”，随后指定Iterations120→300。本轮只准备这条路径，不改RTL/IP/PDS/时钟，原RV32I120和Zmmul1/120产物、已成功实板日志全部保持，不再要求运行新Zmmul120或重新测试原RV32I120。

新构建入口[build_zmmul300.py](../../tests/cpu_performance_2b/build_zmmul300.py)已执行，只生成独立[measure_zmmul300_20261013_a](../../tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/build_review.json)。同GCC15.2.0/-Os/ilp32/noLTO/93.75MHz/2000byte/rv32i_zmmul/原算法与端口/同libgcc，P/V300分别全ELF可执行word白名单与架构属性通过，无DIV/REM/其它扩展；与旧Zmmul120 BIN比，仅seed4_volatile偏移15196处四字节120→300，sections/symbols/实际代码及28条静态MUL完全相同，core_portme.c逐字节同。新短CRC仍使用未改P1/V1 BIN，不为300追加全仿真。

| 软件 | BIN SHA256 | bytes | 300次预期final CRC |
| --- | --- | ---: | --- |
| performance_300 | 677ee766fd0fc34d1558d778a343743a1cd9287ecdbbc182cb4681af3374517d | 15204 | 5275 |
| validation_300 | 461c635c46c86c8e719ced403b045bca468ded7299870bf2f87f8547ce11719b | 15212 | 8803 |

300次CRC参考通过同算法原生host新执行生成，完整五CRC前四项与既有种子参考相同，最终值随迭代数改变；参考dummy clock不是性能或实板证据。build_review=ZMMUL300_BUILD_ISA_AND_NATIVE_CRC_PASS_REAL_CPU_V1_PENDING；原输出和源逐哈希保持。新[zmmul300_software.py](../../tests/cpu_performance_2b/zmmul300_software.py)只独立适配300允许值/参考及正式时长判断，不改旧parser。离线合成UART fixture验证完整CRC/parser/13计数守恒，坏final CRC被拒绝；这是parser检查，未冒充300实板执行。P/V两个离线Loader计划各123响应、唯一RUN，未开串口。

[任务024续测](../../DeepSeek/任务024续测_V1验证与300次软件交接.md)现在是唯一DeepSeek入口。原024没有新的停止报告，当前无vsim/vsimk，P1已有完整原始功能证据；本轮用户新授权足以进行最小V1，不再等待旧报告才能准备续测。旧P1缺native exit/原900秒期限状态、result仍RUNNING/completed空、旧git_after缺失的事实在新original_observation中记录UNKNOWN，原因不能推断，不修改旧目录/报告或伪补。新增.settings纳入当前新Git基线，不删除。

新[resume_coremark_v1.py](../../sim/cpu_zmmul/resume_coremark_v1.py)只复制已干净编译的6份库文件到新tag/work并逐SHA核对，复用原compile argv/exit/log与P1原始证据；只启动一次validation_1，不跑P1/vlib/vlog/历史。原TB/模型/UART速度/MAX_CYCLES/判据/权限不变。P1 ModelSim实测26:12，故为**新V1明确设3600秒**，原任务900秒不改，超时/首次失败停止。启动命令立即返回，后台worker无可见窗口/stdin空/stdout原生直写，避免外层60秒终止入口；--status查询状态。Codex没有启动worker或ModelSim。

```powershell
Set-Location 'D:\riscv\RISCV'
python -B sim/cpu_zmmul/resume_coremark_v1.py --check-inputs
python -B sim/cpu_zmmul/resume_coremark_v1.py --start --tag ds_cpu_zmmul_coremark_v1_resume_20261013_a
# start只一次；之后每30–60秒查询，不因无输出重启。
python -B sim/cpu_zmmul/resume_coremark_v1.py --status --tag ds_cpu_zmmul_coremark_v1_resume_20261013_a
```

清单coremark_v1_resume_inputs.json SHA119e0853d69fa4aac1a55bbf36c226c9b53a59393a5053796d9b8362f2e1632a，74新项/原目录62文件（含6库）继续原421+11输入门；snapshot只复制本次新项，旧设计证据不重复归档。[静态收据](../../sim/cpu_zmmul/build/preparation_20261013_a/v1_300_static_review.json)=V1_ONLY_CONTINUATION_AND_ZMMUL300_STATIC_PREPARATION_PASS_HDL_NOT_RUN；新入口AST/PS语法/原始输入/新软件/离线parser/计划通过，HDL/PDS/serial均未执行。任务文件不会自动调用DeepSeek，收到报告后Codex用[review_coremark_v1.py](../../sim/cpu_zmmul/review_coremark_v1.py)独立核原始log/transcript/UART/native metadata/冻结副本与Git，再生成codex_review.json，旧编排保持历史未知，不改写旧result为PASS。

V1与独立审查通过后，用户仍用同已下载位流64445ecf…ac8ee4，只运行新P300/V300各一次。新工具要求software_gate与Codex独立审查收据匹配、位流/137源/新软件/CRC证据保持，门未完成时不会打开串口。关闭串口助手，每轮KEY0释放/等DDR就绪/Enter，首次失败保存停止。用户当前为CMD，使用绝对路径命令：

```cmd
powershell -NoProfile -File "D:\riscv\RISCV\tools\uart_loader\candidates\perf_2b\run_zmmul300_measurements.ps1" -Port COM9 -LogDirectory "D:\riscv\RISCV\sim\cpu_zmmul\board\coremark_i64_d64_zmmul_300_01\zmmul"
```

与本轮同位流原RV32I120（P/V390130001/404170803cycles，折合每次3251083.342/3368090.025cycles）比较新300的cycles/iteration和iterations/second，不能直接比较总耗时并宣称变慢/变快。迭代数不同，有初始化摊销差，报告须明确；原120无需重跑。增加到300延长测量区间，硬件MUL目标是降低每次迭代耗时，300是否满足10秒取决于实测。实际不足10秒只比较，不自动改为更多迭代。本轮未获得新300性能结果。

以下为此前120次测量和旧交接记录，以上最新口径为准。

## 前次：新位流原RV32I固定120次实板P/V通过，吞吐提高约2%，乘法软件性能尚未测（2026-10-13）

用户执行COM9测量后，Codex只读核对本轮[performance日志](../../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/rv32i/performance_120.json)和[validation日志](../../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/rv32i/validation_120.json)。原BIN e321baca…96d31/0651a64c…b6594及manifest一致，每轮129条完整RVLD响应、一次RUN、无额外RX/自动重试、VERIFY通过；UART全部预期输出/五CRC（final d340/200d）/冻结状态3/13计数守恒通过。两个日志绑定本地新位流64445ecf…ac8ee4，当前位流SHA及PDS收据137输入/项目身份保持。下载是用户报告而非Codex独立FPGA读回；Codex没有打开串口、运行HDL/PDS或重跑测量。

[独立审查收据](../../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/codex_review_rv32i_20261013/result.json)=I64_D64_ZMMUL_BOARD_FIXED_RV32I_PV_RAW_EVIDENCE_REVIEW_PASS；新P日志SHA63ac65e4974539f4be9ff237a487ac8fbc728e2d7bc34d5ea260207316a2367e、新V f3041c4c2c632315f7188d8898d30611da5fea054c9d2de8a2a998fde7546df9，连同旧基线逐协议/严格输出重新离线解析，四份原日志逐哈希保持。复核入口为python sim/cpu_zmmul/build/preparation_20261013_a/review_board_rv32i.py（已执行，输出目录存在即停止，勿为重复复核另跑测量）。

| 指标 | performance：旧I32/D32 → 新I64/D64+Zmmul | validation：旧 → 新 |
| --- | --- | --- |
| cycles | 398389378 → 390130001 | 412352500 → 404170803 |
| 秒（93.75MHz） | 4.249486699 → 4.161386677 | 4.398426667 → 4.311155232 |
| CPI | 4.001056 → 3.918106 | 3.893712 → 3.816455 |
| 精确120次/秒 | 28.238705 → 28.836542 | 27.282483 → 27.834767 |
| 吞吐提升 / 周期减少 | +2.1171% / −2.0732% | +2.0243% / −1.9842% |
| DDR AR | 3197553 → 2902910（−9.2146%） | 3182953 → 2887681（−9.2767%） |
| DDR AW | 3646970 → 3646970 | 3638930 → 3638930 |
| instret | 99571067 → 99571067 | 105902157 → 105902157 |
| branch_redirects | 21124467 → 21124467 | 22634887 → 22634887 |

周期减少精确分解：P8259377=MEM4221829+IF2219079+branch recovery1818469；V8181697=MEM4136537+IF1118842+branch recovery2926318。分支次数没变，branch_flush包含目标取指恢复等待，不能称分支预测提升。AR只统计共享桥读命令，没有I/D分项；MEM分类也不区分读写等待，不能单凭AW较多推断store占主要延迟。缓存扩容后AR减少与等待周期减少相符，当前数据只能支持组合新硬件收益，不能独立拆分I64与D64收益或排除单次DDR时延差异。

新P/V互斥周期占比分别：MEM38.8945%/37.4998%，IF24.4511%/24.8121%，branch recovery11.1319%/11.4857%，other25.5225%/26.2023%；其它三类为0，0是此口径归类结果，不等于体系无相关冒险。仍以访存和取指等待为主要瓶颈。本轮BIN仍rv32i，原ELF审计禁止M指令，增加乘法IP不会改写软件乘法，不能将约2%归因硬件MUL，也不能称完整RV32IM实板通过。

每模式仅一次，未测波动；均不足10秒，只记固定BIN性能比较。UART打印Iterations/Sec=30来自整数Total time=4秒，真实精确值为28.8365/27.8348；ERROR至少10秒与Errors detected是预期时长门，CRC本轮正常。

原RV32I120次两轮已完成，不重复。024只读状态仍RUNNING/completed空且V1不存在；先收DeepSeek停止/中断说明，再按必要V1/收尾最小范围推进，复用现有P1完整证据，不伪补native exit或覆盖原日志。新软件功能门完整后，用户在同一已下载位流上运行独立Zmmul120次P/V各一次，日志同根zmmul目录，比较本轮rv32i以量化乘法指令/代码生成收益；下文命令保留。无需因本轮约2%而重测旧基线或继续扩大缓存/自动启动下一项RTL优化。

以下是此前PDS与上板准备记录，以上最新结果为准。

## 前次：用户已下载新I64/D64+Zmmul位流，PDS审查通过，024 P1有完整证据/V1未完成（2026-10-13）

用户报告“已下载比特流”。根目录新board_top.sbit生成于13:19:03，SHA **64445ecf1e72d11eef96c0e488053d77e0ef74f978d22b040861803831ac8ee4**，9188552byte；用户下载为用户报告，Codex未操作或独立观察FPGA编程。旧成功d60f9ce2位流证据保留，根文件已是新版本，不能继续称根文件旧I32/D32。

当前[PDS审查收据](../../sim/cpu_zmmul/build/preparation_20261013_a/pds_review_20261013/receipt.json)=ZMMUL_FINAL_PDS_TIMING_RESOURCE_SOURCE_AND_SYNTH_INIT_REVIEW_PASS。137登记源/IP/约束全部与准备身份一致，CPU43e45103…d6cfe、桥d8ae0409…5cf09未改，项目源码选项仅IP组排列及生成元数据变化；归一排序后完整配置相同，不是硬件修改。当前项目SHA61adbe3c…5d475。原准备project_snapshot误指023未包含的PDS副本，现用真实修改前fc16262b项目+既有精确mul插入块在内存重建原c5f87d11项目、完整SHA确认后归档，并归档当前项目；未重建/启动PDS或更改主文件。

PDS六阶段日志无错误，选中seed5，当前最终STA All Constraints Met；core93.75MHz setup慢/快 **+0.520/+4.608ns**、hold慢/快 **+0.146/+0.105ns**，核心TNS失败端点0。既有IO约束范围沿用，不把STA当实板证明。物理LUT10767、FF12667、分布RAM44、**APM4、DRM16**；u_cpu2242LUT/2169FF/4APM，u_mul32LUT/64FF/4APM，桥1648LUT/2793FF/8DRM；I/D分别4DRM、Loader ROM/RAM各4，总16。较旧I32/D32 LUT+128/FF+1394/APM+4，含I/D扩容与CPU乘法，不归因单项。

PNR连接表实际包含u_soc/u_soc/u_cpu/u_mul下四个gopAPM、16个gopDRM及13项性能计数器；不是只凭IP目录宣称DSP接通。Loader ROM/RAM各4096word，IDF INIT_FILE、生成INIT和当前综合网表四+四DRM的全部INIT位与成功DAT一致（ROM53a2d991…6cea1/RAM986cda2d…f2975），缓存8DRM INIT为0。**当前PNR连接表不含INIT，generate_netlist导出仍是10月10日旧产物，未当本轮INIT证据；精确INIT核到综合级，映射/PNR/STA/位流生成链新鲜且匹配，未独立从位流解码末级INIT。** 这个证据边界在审查收据保留，不因用户下载而虚写实板PASS。

任务024原固定tag已出现完整P1日志（13:47:14结束，ModelSim打印Elapsed26:12）：唯一RESULT PASS、正常finish、ErrorsWarnings0、两个原DRM提示保留、console/transcript全文相同、UART1122byte。Codex只读用新严格parser核P1五CRC/全部输出/13计数守恒通过，实测MUL退休9618、矩阵MUL9396。[P1只读审查](../../sim/cpu_zmmul/build/preparation_20261013_a/pds_review_20261013/task024_p1_readonly_review.json)保存字段和日志SHA；这仅是用户口模型中的P1功能证据，不是实板性能。

**编排尚未收尾**：原result.json仍RUNNING/completed空，P1 simulation.command.json/native exit记录未生成，V1目录不存在、git_after缺失；目前无vsim/vsimk进程，不能把RUNNING当仍有仿真、不能伪补exit/原900秒timeout状态或宣称整套PASS，具体编排中断原因未有证据。应由DeepSeek先交完整停止/中断说明，再按必要最小口径补V1与收尾，P1不重复。Codex没有重试、停止进程或修改024源/清单/运行目录。

另观察到024 git_before之后新增ipcore/mul/.settings（20byte、内容[not_show_again]、13:39:36），这是当前与原Git快照的唯一新增路径，421项保护输入全部仍匹配。未删除/修改用户元数据，也未改旧Git快照；该文件可能影响原Git收尾守恒，必须与功能判据区分。PDS审查receipt已记录这项差异。本次归档只写已忽略build目录和原有文档，未新增Git可见路径。

用户已经下载新位流，现在可以先按下述原成功rv32i BIN进行**新硬件固定120次P/V各一轮**，不依赖尚未通过的新Zmmul软件；原BIN不重建。新Zmmul120次P/V仍等V1及024收尾问题明确、功能证据完整后执行。每模式KEY0释放/等DDR就绪、COM9/关闭串口助手，原129响应、新123响应+唯一RUN，首次失败保留停止。新日志sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/{rv32i,zmmul}，Codex未开串口/未执行跑分：

```powershell
Set-Location 'D:\riscv\RISCV'
& 'tools/uart_loader/candidates/perf_2b/run_measurements.ps1' -Port COM9 -Applications @('performance_120','validation_120') -LogDirectory 'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/rv32i'
```

只有新软件门完成后才执行后面的Zmmul工具命令；不要重跑已完成的原BIN测量。时序/资源通过不代表新CRC全套、实际DDR收益或正式成绩；不足10秒只性能比较。末级INIT独立解码边界仍保留在PDS收据，板级Loader/VERIFY及CRC需实际记录。

以下“待PDS/根位流旧/024待启动”为此前准备历史，以上文最新状态为准。

## 当前接续：CPU关键功能核验PASS，新Zmmul软件已构建，024短CRC待执行（2026-10-13）

[023续测报告](../../DeepSeek/任务023续测_结果_ds_cpu_zmmul_isa_resume_20261013_a.md)已核原始证据。[续测原目录codex_review.json](../../sim/cpu_zmmul/build/ds_cpu_zmmul_isa_resume_20261013_a/codex_review.json)=CPU_ZMMUL_KEY_FUNCTION_AND_TWO_ISA_RAW_EVIDENCE_REVIEW_PASS：两库各14模块/七命令0/ErrorsWarnings0，baseline_lhu与当前lhu各320事件、or530事件；三例各5精确trap（四启动cause2/tval原指令+通过ECALL11/tval0）、tohost1/MUL0，console/transcript一致、无RPC/超时、新git前后相同、40新输入+原305/10和原冻结副本保持。旧新lhu两events.log逐字节相同，SHA fa225db4be529a0316ba9cb479b9710935a1140f19fa16cd1df47fd25371bc6e。原E4 FAIL确认为旧TB只认结束ECALL、遗漏启动探测的判据缺口，在lhu样本上无Zmmul回归。原失败目录/报告/缺失git_after仍保留，不倒填旧结果。

合并复用原七例：IP128组/168检查、CPU六例2839事件/396乘法退休，以及当前lhu/or两支持ISA样本，可以关闭**CPU硬件乘法关键功能+两ISA抽测**门。没有全ISA/完整SoC/PHY/时序/资源/实板结论；范围Zmmul，DIV/REM非法、misa40000100。CPU43e45103…d6cfe、PDS c5f87d11…a6916、桥I64/D64 d8ae0409…5cf09及成功Loader保持。

## 独立新ISA软件及已完成的构建审计

已执行`python tests/cpu_performance_2b/build_zmmul.py`，只生成独立[measure_zmmul_20261013_a](../../tests/cpu_performance_2b/build/measure_zmmul_20261013_a/build_review.json)。原120次rv32i全产物/源与已有CoreMark算法均逐哈希保持。保持GCC15.2.0、-Os、ilp32、无LTO、2000byte静态数据、93.75MHz端口/计数器/启动链接，仅-march及打印FLAGS换为rv32i_zmmul。相同rv32i/ilp32 libgcc未换；全部ELF可执行word严格白名单只新增四乘法，架构属性rv32i2p1_zmmul1p0，DIV/REM/其它扩展禁用。

每份ELF静态28个MUL，其中matrix_mul_const/vect/matrix各1、bitextract2共5个矩阵热点；这是静态点数，不是动态占比或性能收益。新P BIN15204byte、新V15212byte，各较原15936/15944少732byte。P/V的1次与120次版sections/symbols相同，BIN只有seed4_volatile四字节从1到120改变，编译端口文件与原120次版逐字节相同；算法及测量区间不改。新版reference复用已有正确短迭代/原生120CRC参考，只改变FLAGS，不重跑host算法或虚拟时钟。

| 软件 | BIN SHA256 | 状态 |
| --- | --- | --- |
| 新P1 | cd3a6c75bce420e386782321a6c161c2622a6edf81fb4a988a72ff1d146a0183 | 新CPU短CRC待024 |
| 新V1 | f2fd2202855a510a5ef6671a1cb385b6f4ae7d464e716bc3d3b3e1cf6e51b84c | 新CPU短CRC待024 |
| 新P120 | ab956eb447292c75b74f67e0bbc88cfcb3cd70c8334b52a89514a80d55639906 | 实板CRC/性能待测 |
| 新V120 | 4168c1c4d41812e798a07bc08f3bf9accc7bc7c54ba054d28900b42a1f1febc1 | 实板CRC/性能待测 |

原P120 e321baca…96d31、V120 0651a64c…b6594保持，无覆盖。软件构建/ELF审查和纯离线parser正常/坏CRC拒绝、13计数守恒检查已通过，不等于新CPU执行CRC PASS。build_review=ZMMUL_SOFTWARE_BUILD_AND_ISA_AUDIT_PASS_CRC_SIM_PENDING。

## 当前唯一DeepSeek任务024

[任务024：新Zmmul CoreMark短CRC](../../DeepSeek/任务024_Zmmul新CoreMark短CRC关键仿真.md)只跑新P1/V1各一次，不重跑023/ISA/旧版/历史/PHY，不执行新120全仿真。当前CPU/SoC/x32用户口模型、真实mul和I/D DRM源+三厂家原语，34模块，一次编译/-batch两个单顶层仿真。未经过Loader下载/PHY；UART真实115200引脚解码、程序真实MUL及矩阵5热点MUL退休>0、CRC五项/完整输出/13计数守恒均要求。短CRC不作性能结论。

```powershell
Set-Location 'D:\riscv\RISCV'
python sim/cpu_zmmul/run_coremark_crc.py --check-inputs
python sim/cpu_zmmul/run_coremark_crc.py --tag ds_cpu_zmmul_coremark_crc_20261013_a
```

Codex只执行第一条静态输入门，第二条新HDL**未执行**，由DeepSeek领取单次固定tag，存在即停止、首败不重试。新清单[coremark_crc_inputs.json](../../sim/cpu_zmmul/coremark_crc_inputs.json) SHA ca07e018b059616254f58e198cc939522a9e7295708352b8839136a5a5147605，421工程项+11外部；DAT只仿真且逐字还原新BIN、长度/padding/5热点PC已核，不改IP INIT。vlib/vlog60秒，单vsim**900秒**（新增CoreMark任务明确授权，历史短CoreMark约161秒，本轮真实DRM/MUL/较长PERF UART），TB60Mcycle watchdog；保持实际UART不加速、原生直写、无外层60秒截断，禁止改权限/环境/判据或追加预检。

[coremark_crc_static_review.json](../../sim/cpu_zmmul/build/preparation_20261013_a/coremark_crc_static_review.json)=ZMMUL_SOFTWARE_AND_CRC_PREPARATION_STATIC_PASS_HDL_NOT_RUN，Python AST/新TB结构/34模块依赖/真实生成源/旧软件守恒及新parser/镜像静态核对通过，未编译或运行新HDL。任务文件不会自动调用DeepSeek。P1预期CRC e9f5/e714/1fd7/8e3a/e714；V1 18f2/e3c1/0747/8d84/e3c1。新120最终CRC分别d340/200d由用户实板检查，短仿真不能替代120实板。

## 用户最终PDS准备（未执行）

[pds_handoff_zmmul.json](../../sim/cpu_zmmul/build/preparation_20261013_a/pds_handoff_zmmul.json)绑定当前CPU/IP/PDS、023功能收据、022缓存功能及**实际137登记源/IP/约束**。旧130统计未计PDS中已经登记且未改的csr_defs.vh，本轮补计1项+新增mul IDF/五RTL6项；不是新增CSR行为。项目快照复用023冻结新PDS，不重复存旧设计。固定board_top、PG2L200H/FBB676/-6，参考125MHz/core93.75MHz，I/D各2KiB，Loader ROM/RAM IDF/生成INIT/原镜像身份保持。仅用户启动实现，建议024结果核证后开始，避免PDS与DeepSeek HDL并发；Codex没有启动PDS。

交回最终PDS后核：各阶段完成/选中seed/实际新位流；core93.75MHz setup/hold慢快角均通过、新u_mul相关关键路径；实际netlist/资源中board_top.u_soc.u_soc.u_cpu.u_mul使用APM（生成配置理论4，最终映射报告权威），不能只凭IP目录断言用了DSP；I/D DRM各4、Loader8、总DRM预计16，cache row6/read word9bit完整，tag/valid64；137源/完整Loader INIT/生成新bit对应验收CPU。资源/时序/面积可能变化，尚无PDS实测。原成功bit仍I32/D32 d60f9ce2…b46cc，不能当新M位流。

## 板子可用后的四次固定测量准备（尚未执行）

[board_plan_zmmul.json](../../sim/cpu_zmmul/build/preparation_20261013_a/board_plan_zmmul.json)及两离线新软件plan已准备：COM9/115200，原rv32i120 P/V各129响应+唯一RUN，新Zmmul120 P/V各123响应+唯一RUN。新增[Zmmul工具](../../tools/uart_loader/candidates/perf_2b/run_zmmul_measurement.py)复用原成功RVLD传输/原13计数parser，只选择新manifest/reference，不改旧工具或打开串口。第一次失败保留停止，无自动重试；新旧每模式各一次，既有成功基线不再运行。

前置：024原始CRC证据通过、用户最终PDS由Codex核验、用户下载该新位流、板子可用。四次都用同一新位流；每次按工具提示关闭串口助手、按KEY0并释放、等DDR就绪、按Enter下载，运行中不复位。程序LOAD/VERIFY/RUN一次，原BIN和已验新BIN均不重建。日志根目录`sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01`当前不存在：

```powershell
$ErrorActionPreference = 'Stop'
Set-Location 'D:\riscv\RISCV'
& 'tools/uart_loader/candidates/perf_2b/run_measurements.ps1' -Port COM9 -Applications @('performance_120','validation_120') -LogDirectory 'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/rv32i'
& 'tools/uart_loader/candidates/perf_2b/run_zmmul_measurements.ps1' -Port COM9 -LogDirectory 'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/zmmul'
```

比较：最终硬件原BIN对成功coremark_idrm_d32_01（P/V398389378/412352500cycle，4.249486699/4.398426667秒）是组合缓存/CPU配置收益；同一最终硬件新Zmmul BIN对原rv32i BIN是同源ISA/代码生成与硬件乘法路径收益；新BIN对原成功硬件是总体收益，不能全归乘法。新旧BIN不同，不要求instret/branch/AW相等，逐份CRC及13分类守恒必须满足。120次单次不足10秒仍只记性能比较，不称正式成绩，不自行追加长跑或许诺加速比例。

收到024/PDS/实板结果后按相应门连续核原始证据/时序/资源/初始化/位流/CRC/真实性能并更新本阶段，不再询问是否继续。当前新CRC/PDS/实板仍待外部结果，不记为完成、不自动另做RTL优化。

以下023接入/等待/诊断为此前历史，当前入口以上文024为准。

## 当前接续：023七例原始PASS核验，ISA启动探测判据修订（2026-10-13）

用户交回023停止报告，Codex已独立审查原始日志、命令/退出、console/transcript、真实编译源、清单及305冻结输入。审查收据[原目录codex_review.json](../../sim/cpu_zmmul/build/ds_cpu_zmmul_20261013_a/codex_review.json)=CPU_ZMMUL_SEVEN_CASES_RAW_EVIDENCE_PASS_ISA_GATE_OPEN。编译15模块/ErrorsWarnings0，vlib/vlog退出0；IP128组/168检查及CPU六例2839事件/396乘法退休均实际PASS、七仿真无超时/RPC/错误。math2718/391，背压15/1，reset10/1，旧fault22/1（启动2/取消1），IRQ24/1，非法DIV/REM及misa50/1。旧结果继续STOPPED_FIRST_FAILURE，不能写九例全PASS。

原isa_lhu于1335ns、event38、PC800000e4打印TB FAIL/Fatal、Errors1，命令退出0但判据失败；isa_or未执行，无旧git_after，不补写或声明旧前后Git相等。现有完整日志没有cause/tval/inst，实际陷阱字段仍未观察；已核当前305+10和旧305副本身份均匹配，不能拿当前身份替代缺失的当时收尾快照。

静态定位：原ROM与dump均证明800000e4是74445073，即CSRWI744,8；其前AUIPC/ADDI/CSRW已安装mtvec800000e8。当前和修改前CSR白名单都未实现744，按既有语义应cause2/tval74445073转到E8。原023 TB只允许最终ECALL，漏掉原riscv-tests启动CSR探测，这是Codex编写ISA观察判据的遗漏。该静态依据足以修订精确期望，但**不能说旧日志实际已经记录cause2，更不能宣布ISA功能已通过**。不据此次断言去改CPU/CSR或新增CSR支持。

当前唯一入口[任务023续测：ISA启动CSR探测精确核验](../../DeepSeek/任务023续测_ISA启动CSR探测精确核验.md)。新增ISA专用TB及只读trace/精确trap参考，原tb_cpu_zmmul.sv/run.py/inputs.json/六例golden全部保持；七例乘法PASS复用，不重跑。新ISA总线模型与原023 ISA模式逐字相同，仅添加接受状态store的只读PC标记，以等真实退休才结束。新增判据严格核每个trap的PC/指令/cause/tval/无写回/目标、trap CSR提交及跳转后第一退休PC；拒绝任何未列异常。允许四个原启动探测：E4/744→E8，F4/satp→F8，10C/pmpaddr0→118（跳过pmpcfg0），128/medeleg→130（跳过mideleg），均cause2/tval原指令；最终只接受lhu478或or684的通过ECALL，cause11/tval0→80000004，tohost完整SW=1且实际退休，合计5trap/4probe、无IRQ/M扩展正常退休。所有架构事件原生flush，失败打印实际inst/cause/tval/rf_we/IRQ/target。

按AGENTS“TB/判据改变且旧基线不能直接复用才补相关旧版对照”，只补**一次修改前CPU lhu**，然后当前CPU lhu、or各一次；共三仿真，不扩历史。旧CPU为preparation真实冻结746db2f6…9f7e7，不替换主设计。旧/新lhu用同模型/原ROM-RAM/新判据，完整架构事件必须相同，仅忽略时间及不生效旁带。当前CPU仍43e45103…d6cfe、PDS c5f87d11…a6916、mul IDF/桥/原镜像保持，未改任何RTL。

```powershell
Set-Location 'D:\riscv\RISCV'
python sim/cpu_zmmul/resume_isa.py --check-inputs
python sim/cpu_zmmul/resume_isa.py --tag ds_cpu_zmmul_isa_resume_20261013_a
```

Codex已执行第一条只读静态核验，第二条**未执行**，只由DeepSeek领取固定新tag。新清单[isa_resume_inputs.json](../../sim/cpu_zmmul/isa_resume_inputs.json) SHA dbd4f0fee409fd27166b79d55979aa908b16220b792c1fa6d39c11a7bff10c1d，在原305+10门外保护40项新源码/参考/旧原始证据。两库、每库14模块，2×vlib/vlog各60秒、三条-batch仿真各180秒、20ms watchdog；顺序baseline_lhu→isa_lhu→isa_or，第一失败保留停止，不换tag/改权限/超时/判据/PDS/串口/Git，不追加原七例/全ISA/Hello/CoreMark/桥/PHY/工具预检。源只新增，不重存旧305份或旧日志，引用已验身份；原缺失git_after保持缺失。

[isa_resume_static_review.json](../../sim/cpu_zmmul/build/preparation_20261013_a/isa_resume_static_review.json)=CPU_ZMMUL_ISA_CONTINUATION_STATIC_PASS_HDL_NOT_RUN：旧七例原始审查、ROM字/mtvec安装/通过ECALL精确核、总线模型保持、两个CPU静态探针/新TB结构/Python AST/输入门通过。不是新编译或新功能PASS。续测全PASS且Codex核原始证据后，才合并旧七例为乘法关键功能+两例ISA抽测完成，并继续独立Zmmul软件CRC和用户最终PDS/上板准备。新软件/PDS/实板仍待，原120次BIN/Loader/成功位流保持。

以下原023实施/待执行状态保留为本次续测前历史；实际入口以上文为准。

用户已生成真实乘法IP，实例为`mul`、目录`ipcore/mul/`。Codex已核对IDF/生成源码和依赖，完成主`myriscv/mycpu_sync.v`四条乘法接入及`RISCV.pds`登记，静态输入/代码审查通过，**新的HDL编译、仿真、PDS及实板尚未执行**。当前唯一待领取[DeepSeek任务023](../../DeepSeek/任务023_CPU硬件乘法Zmmul关键仿真.md)，无需重复确认继续。

## 本轮实施与静态交付（2026-10-13）

实际IP：Simple Multiplier1.5，A/B Signed33、输出66；ASYNC_RST0、INREG0、PIPEREG1/2/3均1、OUTREG1、PIPE_STATUS4、OPTIMAL_TIMING0、Advanced关闭。接口ce/rst/clk/a/b/p；生成源码未改。本配置按厂家拆分公式需4个APM实例，最终使用量仍以用户PDS报告为准。真实依赖为mul.v、ipm2l_mult_v1_3_mul.v及三个apm_data_pipeline源，仿真再编厂家GTP_APM_E2/GTP_GRS；不使用行为替身。PDS仅增加一个实际mul IDF及五源登记，删除该唯一块后与修改前项目逐字节相同。

CPU增加四乘法解码白名单、ID/EX操作旁带及EX启动/等待/结果保持。单个IP共享四指令；保持ID/EX操作数直到完成，MUL取31:0、高乘取63:32。IP四个CE边沿更新结果，CPU下一边沿采样已稳定的p，避免同沿NBA读旧值：T0启动并进入XY，T1 M，T2 P，T3 OUT，T4捕获/置done，T5允许进入EX/MEM（MEM背压时继续保持）。这是当前保守完成口径，真实延迟必须通过任务023；不称CPU单周期或四周期完成。

结果未就绪不能EX前递/推进，完成后走既有MEM/WB和GPR写回，每条只正常退休一次。reset、kill_id_ex、旧MEM/WB故障取消busy/done；IRQ走原精确排空、乘法先退休后入trap。DIV/REM保持非法；csr_file/csr_defs全文保持、misa仍40000100，只有Zmmul，未实现完整M。

性能旁带MEM改为原访存等待表达式，纯乘法等待不再因共用data_pipeline_stall而混记DDR等待；无其他高优先级事件时记OTHER，原13分类优先级/MMIO布局/计数器源码保持。不能用新ISA软件退休数与旧BIN相等作为验收。

源身份：CPU `43e451038cc14b3402ff159629d18783fbd8d1364e7c05197fadbb1e8e5d6cfe`，PDS `c5f87d111f751e0f2205fa5471a4002dc88d59c67b3de43f813c47395eaa6916`，mul.idf `1f583b2ee87c795c7f7ae41b4c6263703b6bdeeb8f7fb0af7f7932bb22ae9a33`。输入清单[inputs.json](../../sim/cpu_zmmul/inputs.json) SHA `f8ebb23bb096017e2b373872adc100042732289bc24c242564d9e9c09de6fa86`保护305工程项+10外部依赖，旧259项只有授权CPU/PDS改变，其旧身份在[preparation](../../sim/cpu_zmmul/build/preparation_20261013_a/ip_review.json)留存；其余老RTL/IP/镜像/成功证据保持。旧022清单绑定旧CPU/PDS，不在新CPU上调用旧输入门或重跑022。

静态收据[static_review.json](../../sim/cpu_zmmul/build/preparation_20261013_a/static_review.json)=CPU_ZMMUL_STATIC_PREPARATION_PASS_HDL_NOT_RUN。核实际IP端口/参数/寄存路径、CPU解码/流水/前递/取消、PDS最小登记、Python参考重现及独立边界结果、TB结构/探针、原输入身份；git diff --check通过。这不是HDL编译或功能PASS。

## 当前唯一关键仿真

```powershell
Set-Location 'D:\riscv\RISCV'
python sim/cpu_zmmul/run.py --check-inputs
python sim/cpu_zmmul/run.py --tag ds_cpu_zmmul_20261013_a
```

第一条Codex已执行且通过，只读静态核对；第二条仅由DeepSeek单次执行。不要重新生成fixture/oracle，不换tag或改超时/判据。一次vlib/vlog和九个标准-batch单顶层仿真，60/60/180秒、原生直写、独立watchdog，首次失败保留停止，不追加旧版/历史/CoreMark/PHY或工具RPC诊断，不操作PDS/串口/Git。

计划：真实IP128组全66bit产品/168检查；六例CPU共2839架构事件、396乘法退休（384组四乘法边界/随机+别名/x0/连续/依赖），逐项独立Python golden核PC/指令/GPR/异常/IRQ/MRET；包括长MEM背压、不同操作数busy复位、旧load fault取消已完成未退休乘法、MEI精确排空、DIV/REM非法及misa边界。ISA种子2026101323从40个支持目录选择lhu/or，旧ROM/RAM，tohost1；标准结束ECALL11保留，不能宣称全ISA通过。用例/数量/命令/判据见任务023，当前全部HDL NOT_RUN。

完整功能PASS后Codex核原始日志/唯一RESULT/finish/ErrorsWarnings/退出/console-transcript一致/305输入副本/git守恒，连续准备独立Zmmul软件、最终用户PDS和上板步骤。失败仅处理相关原因，不擅自重试。

## 软件及硬件剩余工作

原固定120次rv32i P/V BIN及Loader INIT不覆盖。原BIN没有MUL，不会自动受益；独立rv32i_zmmul CoreMark尚未构建/CRC验证，待CPU关键功能门通过后准备，保持算法/优化等级/迭代/测量范围，反汇编排除DIV/REM并确认热循环使用MUL。新软件必须CRC通过再测，比较是同源不同ISA。PDS/实板仍用户执行；当前不能认定新时序、APM/面积或实际DDR性能通过。

I64/D64桥d8ae0409…5cf09及022 2963原始功能PASS保留，缓存新PDS/实板仍未做；成功根位流仍I32/D32 d60f9ce2。旧data_drm64_preparation/PDS计划保存为改CPU前状态，最终实现须绑定新CPU/mul身份及功能收据，不能直接沿旧130项准备声明新CPU已验收，也不能把桥级PASS当CPU/SoC/实板PASS。用户需要时可先看源码，但当前下一道门是023。

以下保留初次IP选择和设计边界说明；实例建议cpu_mul/待生成字样以本节实际mul/已接入状态为准。

## 选定IP与配置

选`Multiplier → Simple Multiplier (1.5)`。本机对应`C:/pango/PDS_2022.2-SP6.4/ip/module_ip/ipm2l_flex_apm/ipm2l_flex_apm_eval/ipm2l_mult/`，index中family为Logos2/Titan2、version1.5；使用APM乘法资源。安装模板接口为`ce/rst/clk/a/b/p`，不是带ready/valid的事务接口，CPU侧须自行管理完成与取消。

实际已生成实例`mul`到`ipcore/mul/`，核对参数：

| GUI参数 | 设置 |
| --- | --- |
| A Data Type / Width | Signed / 33 |
| B Data Type / Width | Signed / 33 |
| Product Width | 全宽66（A+B，界面计算） |
| Pipeline Stages | 4 |
| Async Reset | 不勾选，采用同步高有效rst |
| Optimal Timing | 不勾选，固定可核对流水线配置 |
| Advanced Mode | 不勾选，由GUI自动配置寄存器 |

本机ui允许位宽2..82；标准4级配置选XYREG/MREG/PREG并增加OUTREG，INREG关闭。选择输出寄存器以方便CPU完成/前递接口时序；不能仅凭GUI数字确定CPU完成边沿，生成后要核IDF/模块/内部各路径实际延迟，再由DeepSeek真实原语验证。具体APM资源及93.75MHz时序由后续PDS确认，不预言单周期或固定收益。

用33bit signed是为了在同一个固定符号IP上实现32bit有符号/无符号混合乘法。CPU按指令扩展操作数：

| 指令 | A扩展 | B扩展 | 返回32bit |
| --- | --- | --- | --- |
| MUL | 0:A[31:0] | 0:B[31:0] | P[31:0] |
| MULH | A[31]:A[31:0] | B[31]:B[31:0] | P[63:32] |
| MULHSU | A[31]:A[31:0] | 0:B[31:0] | P[63:32] |
| MULHU | 0:A[31:0] | 0:B[31:0] | P[63:32] |

高位乘法取原32×32乘积的[63:32]，不能因IP输出66bit而取[65:34]。MUL低32bit不受符号解释影响，零扩展可统一处理。四条共享一个33×33 signed IP，不需动态修改IP符号参数。

## CPU实施边界与验证准备

主RTL继续在`myriscv/mycpu_sync.v`及已有设计文件维护。新增funct7=0000001/funct3=000..011白名单与乘法操作旁带；DIV/REM仍非法，misa.M保持0。EX锁存/持有操作数和目的寄存器、单次启动、等待真实IP结果；结果就绪前不能把普通ALU值前递，结果必须在MEM背压期间保持。reset/trap/MRET取消不得留下迟到写回；IRQ沿既有精确排空规则完成，x0不写、每条只退休一次。不得绕开既有异常/中断/CSR或load-use规则。

目前`data_pipeline_stall`也用于非访存EX阻塞，乘法等待接入后须核性能统计分类，不能把乘法等待误记为DDR MEM等待或破坏13分类守恒；新ISA运行的instret/branch数量本来就可能变化，不套用旧同BIN计数相等判据。

真实生成源已用于主CPU接入及PDS清单，实例/端口/参数/寄存路径及依赖已核；功能延迟和边界仍待任务023真实原语验证，不提前标PASS。

软件以后独立生成rv32i_zmmul输出，原120次rv32i BIN/ELF/manifest和Loader成功镜像不覆盖；保持算法/优化等级/迭代/测量范围，反汇编确认mul进入循环，CRC验证通过后才能比较性能。这是同源不同ISA对比，没有硬件实测前不承诺加速比例。

## 当前已验证缓存及待办

I64/D64桥d8ae0409…5cf09及022 2963检查原始证据保持，现有成功位流仍I32/D32 d60f9ce2；缓存新PDS/实板未完成，不能因CPU新阶段开始记作已完成。本轮只按授权修改CPU及PDS乘法登记；缓存、原软件和成功位流身份保持。CPU修改前保存必要源身份，后续最终PDS必须对应真实CPU/IP源及功能验收版本；不拿旧缓存桥级PASS替代CPU仿真或新硬件时序/实板验收。PDS实现、下载及KEY0/串口仍由用户执行，仿真交DeepSeek。
