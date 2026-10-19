# 任务033：D读miss期间I缓存查询并行，编写测试并直接执行

2026-10-17。用户已反馈本版PDS时序结果完成，并直接要求“开写测试和仿真，我交给deepseek，直接让他执行”。据此领取后立即完成本任务的测试实现、封存及一次关键组执行，不再等待另一份派发或PDS收据。时序信息仅来源于用户，未独立审查报告，不填造WNS/TNS或时序PASS数值。

## 设计与权限

- 根目录 `D:/riscv/RISCV`；ModelSim `D:/modelsim/win64pe/`；厂家原语 `C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation/`。
- 唯一被测桥 `myriscv/dual_sram_to_pango_ddr_bridge.v`，SHA256 **7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933**，参数 `INST_HIT_UNDER_DATA_MISS_ENABLE=1` 默认开启，仅x32且I缓存开启生效。
- 读 `doc/cpu/CPU性能恢复评估_2026-10-17.md`、`sim/cpu_inst_hit_overlap/preparation_20261017_a/review.json` 和 `after_manifest.json`。静态六配置展开不算功能PASS。
- 允许在 `sim/cpu_inst_hit_overlap/` 新增本任务TB、DDR模型、最小程序、独立参考、checker、封存与运行脚本、清单及产物；在 `DeepSeek/` 新增本任务结果报告。已有 `preparation_20261017_a/` 完整只读。
- 不改主RTL、CPU、IP、PDS、约束、成功BIN、历史测试/证据/验收门，不操作PDS/串口/实板，不提交或推送Git。不启动其他对话。
- 开始先保存Git状态/差异及输入身份；按准备清单核当前设计、cache IP和固定P300/V300 BIN。设计/IP/BIN身份不符即停。PDS实现产生的工程元数据与旧快照不同须记录，不把旧PDS/FDC哈希当动态仿真放行前置条件；若有影响被测RTL配置的变化则停报。

## 实现与唯一执行入口

新增 `tb_inst_hit_overlap.sv`、`tb_inst_hit_overlap_soc.sv`、`ddr_model.sv`、`prepare_program.py`、`check_evidence.py`、`seal_inputs.py`、`run.py`、`inputs.json`；如需辅助文件，在封存前登记。可只读参考 `sim/data_bus_turnover/` 现有模型/工具/独立退休参考的写法，不能调用旧main、旧require_inputs或旧板测门替新设计放行。

正式tag固定 `ds_inst_hit_overlap_20261017_a`，目录 `sim/cpu_inst_hit_overlap/build/ds_inst_hit_overlap_20261017_a/` 必须此前不存在。准备/静态检查不得创建该正式目录。实现以下命令并执行；这些是本任务要求实现的CLI，不声称当前已存在：

```powershell
Set-Location D:\riscv\RISCV
python -B sim/cpu_inst_hit_overlap/prepare_program.py
python -B sim/cpu_inst_hit_overlap/seal_inputs.py
python -B sim/cpu_inst_hit_overlap/run.py --check-inputs
python -B sim/cpu_inst_hit_overlap/run.py --run --tag ds_inst_hit_overlap_20261017_a
```

新程序镜像只写本任务sim目录。封存后只从运行副本编译；执行入口顺序固定 **vlib → vlog → bridge_on及独立检查 → bridge_off及独立检查/周期比较 → soc及独立架构检查**。vlib/vlog各60秒，各vsim上限180秒，每次checker60秒；每个HDL顶层另设不超过100000周期watchdog，非以延长仿真等串口输出。bridge_off只是同一新桥参数0的必要因果对照，不重跑旧桥/历史全套。两个桥job用同一TB、数据与逻辑请求序列，只有开关参数不同；SoC只运行默认开启版。

不运行ISA抽测（CPU未改）、CoreMark、Loader Full Boot、物理DDR/PHY、相机采帧、CNN推理或历史032全套。本组DDR为带独立背压/延迟的Pango用户口模型，不能写成真实PHY/训练或当前全部应用兼容性通过。

## 一次把编译依赖准备齐

1. 真实 `icache`/`dcache` 封装、内部实现、初始化参数及厂家DRM原语必须参与功能仿真；SoC还包含实际ROM/RAM及其依赖。不能用黑盒、行为RAM、Icarus `-i` 或替换IP绕过厂家模型。
2. 每个仿真顶层都实例化 `GTP_GRS GRS_INST (.GRS_N(1'b1));`，从GRS所在顶层启动，检查厂家层次引用。仿真不需要编译DDR PHY。
3. 递归封存所有Verilog include（`.vh/.svh`、各IP `*_init_param.v` 等）、实际读入的初始化文件、程序/参考/checker/runner、厂家源及工具身份。运行副本的include和初始化路径闭合，不能偷偷读取工作树原文件；外部固定厂家库须列绝对路径与SHA。
4. 正式HDL前完成语法/清单/路径/参数/顶层/原语实例静态核对，登记实际源和模块清单、预期IP初始化提示。不因旧任务模块数相近就硬套旧计数。两个cache每实例的04030130提示按真实配置核值/数量，不把其当warning。
5. 所有动态输入与预期、超时在正式执行前冻结。可做Python参考的合成自检并保留结果；禁止先试跑HDL再挑成功一次称正式运行。

## 公共参考与协议口径

请求在下降沿驱动，未接受前valid/字段保持；接受边沿为E0，下一边沿为E1。I/D响应没有ready，valid所在边沿即消费，不能自行添加响应背压。轨迹同时记录上升沿采样前的握手值及NBA/DRM稳定后的值并标明phase，不用同沿race制造PASS。

参考是独立字节内存、按完整地址组织的cache参考和每侧token队列。内存初值、程序、地址序列、预期架构事件先生成并封存；每个word/lane/tag须能区分。checker从完整外部输入和握手轨迹重算预期，不读取DUT的state/hit/tag/pending或实际返回值生成expected；内部信号仅用于说明覆盖。禁止force/deposit任何DUT状态、cache内容、寄存器、返回、ready或PC，所有预热经真实请求/DDR填充。

x32每拍256bit/32byte/8word，用户地址单位4byte，单拍地址低3bit清零；不得把CPU字节地址直接接AR/AW。特别注意互连先减DDR_BASE：桥请求为DDR局部字节地址，Camera/PP在桥级分别用0x01000000/0x02000000，在SoC级才用0x41000000/0x42000000。该接口无WVALID/B/RREADY；按AW接受后或AW同边沿的WREADY计算W完成。逐笔核ID/AP/len/last、AR/AW字段背压稳定、全部R拍、W数据/strobe和最终内存。单物理读在途始终≤1，AR/R同拍合法；模型仅返回已接受的读，复位时与DUT共同取消旧事务，不能把非法旧R当复位功能判据。

每侧独立统计 `接受 = 响应 + 明确复位取消 + 当前在途`，结束在途为0；每token最多一个响应，D和I同时响应分别记账。新I命中必须在E0后的周期有效、E1消费；停放miss没有第二次外部接受，但以后必须恰好一个响应。

## 桥定向组：必须实际命中的覆盖

bridge_on主配置x32、I/D cache各64行、posted写/写接续/字节转发开启，Camera/PP无缓存开。bridge_off仅关闭新参数。相同场景在off版本的接受时刻可不同，不要求其也触发新并发；两版最终响应数据/内存/逻辑token顺序都须等于独立参考。

| 场景 | 开启版必须证明的事实 |
| --- | --- |
| 预热与D长miss | 正常预热I后，D冷读在AR背压至少3周期、AR已接受等R至少5周期两种窗口分别接受I hit；I在D完成前正确返回，D地址/lane/归属不被改写。所有8个I word lane均覆盖，至少两个不同index及同index不同高tag的miss。 |
| 接受/返回边界 | 覆盖D AR/R同拍且接受I、延迟D R到达且接受I、D R到达且消费旧I hit、D响应与I命中双响应。明确区分R总线边沿与D侧响应边沿；每种列真实cycle/token。 |
| 连续I接续 | D等R期间至少4笔连续已缓存I hit，消费旧I同时接受新I，地址/index/lane不同；旧响应属于旧地址，新响应属于新地址。hit→miss后独立槽满，不得继续接受I。 |
| 停放miss与地址毒化 | D等待期间接受I miss，接受后撤valid并把live地址改为预热hit/不同lane，保存原miss不得变假hit；D R返回前不得发I AR。D完成后先接受至少2个新D请求，I miss地址/判定仍保持，解除D竞争后用保存地址发唯一I AR、返回正确word，随后同一行hit。另覆盖D响应无竞争时的最早提升。 |
| 主槽D优先 | 原D完成时，同时给新D和I请求，合法主槽仍D优先；已停放I不得被旁路新I覆盖。D优先可推迟I，有限竞争解除后必须完成。 |
| store与I失效 | 旧I hit消费沿接受命中该I行的D store，同时保持下一I请求；旧I数据正确，该沿新I不能被接受。store实际更新独立内存，后续I请求必须miss，排空后读到按strobe合并的新数据。包括1字节、半字和零strobe的现行语义，不臆改失效规则。 |
| 旧写排空 | 旧posted写AW未接受、AW已接受W等待各一次，分别给I hit及I miss；I hit可完成，I miss AR等待写排空。另持续提出D miss，证明它等旧写排空才被接受，随后进入新的I并行查询窗口。当前D miss不能在旧写忙时接受，不要求制造“旧写忙且D miss已在途”的不可达场景。覆盖W完成与I接受、随后D AR/R相邻/同拍的合法组合，核稳定字段与唯一写完成。 |
| 转发保持 | 通过真实预热和store分别测同word部分字节转发、同行邻word读取；以独立内存加尚未排空的旧写覆盖计算返回。不得用整个wdata覆盖未选字节；该场景不强求触发D miss并行。 |
| 复位取消 | 分别在独立I hit待消费、I miss停放、I提升后等R复位；每个epoch守恒，取消数从复位前token重算。复位后冷请求不得得到旧数据/多余响应。ddr_init_done=0时不接受新请求；不对仅init掉线但未复位的旧事务另造取消语义。 |
| 无缓存边界 | 对Camera区局部0x01000000–0x013fffff、PP区局部0x02000000–0x0200ffff，同址D读两次、在两次之间由模型合法外部更新内存，确认均发DDR且读到新值；I并行hit不得误填D区。I禁止执行由SoC译码场景验，桥本身不承担权限。 |

受控性能子场景单独划计时边界，含相同预热后的一次D长miss与一串真实I hit，D返回时序以D AR接受为相对基准固定。逻辑任务完成定义为两侧全部请求响应收齐，不能只比较首个I ready或内部分类。开启版实际完成周期必须小于关闭版，checker重算差值，列出隐藏等待的具体边沿；不将此人工场景差值当CoreMark收益。若未省总周期或覆盖不可达，首败交回Codex，不修改既定判据。

## 最小真实CPU集成

一个新 `soc_top` 顶层，x32/posted写、真实CPU/互连/cache/片内存储/UART，UART RX接idle high；Camera/PP/CNN参数均开启以保留当前译码及片内RAM响应寄存路径，接口空闲端明确连常量，不启动相机/PP/CNN运算。仅在TB用当前参数设置复位PC到DDR程序入口，初始DDR经模型装入已封存小程序，明确非Full Boot。

程序需真实预热取指行并制造D冷miss，使默认开启桥至少实际接受并返回一次并行I hit；记录CPU暂停前端时该I响应进入响应缓冲、暂停解除后只消费/退休一次。再构造有在途错误路径取指的taken branch/flush，证明旧响应被丢弃、错误路径store没有请求接受/DDR写/退休。若安排真实延迟下不能触发，按已冻结刺激失败返回，不能force CPU状态或只检查内部标志代替事务。

独立RV32I最小解释参考逐事件核PC/inst/写回/next PC，覆盖程序中全部退休，保存错误路径集合和无年轻副作用证据；使用支持的少量指令，不为本任务改CPU。另用最小无副作用非法取指检查Camera/PP窗口不可执行（可在同job的独立复位epoch执行），核精确cause/tval及无DDR取指AR，不能因桥响应error恒0就省掉外层权限检查。核全部CPU请求/响应和实际内存，不只核最后签名。周期只记录，不套032的617/415固定值，不强求真实CPU也达到人工桥场景提速比例。

## 执行、证据、首败

- 保护准备目录、当前设计/IP/固定BIN、所有只读引用的历史测试/收据，逐文件前后SHA一致。不要对整个sim递归复制自身；封存源/输入和保护证据分开列，原运行编译库不复制。
- 正式各job只执行一次，前一项通过才执行下一项。native exit=0、无超时、ModelSim Errors:0/Warnings:0、正常finish；已声明IP note单列。发现未声明warning、FAIL/Error/Fatal、未解析原语/黑盒、缺轨迹或独立checker失败都停止。失败不重试、不换tag/seed、不加超时、不改测试/参考/设计后再跑；保留新目录交回Codex判断。
- 无论成败保存全部argv/cwd/开始时间/pid/native退出码/耗时/超时/cleanup、stdout及完整ModelSim transcript、输入manifest及SHA/副本/工具身份、Gitbefore/after/设计与保护哈希复核。即使提前失败也在finally保存能取得的after状态；未执行项目如实NOT_RUN。
- 保存每周期I/D valid/ready/addr/size/write/wdata/strobe、响应/data/error、AR/AW/W/R/ID/地址/数据/背压、reset/init、场景/epoch/token、CPU取指接受/响应/缓冲消费或丢弃/退休、完整内存参考和checker覆盖账本。按边沿外部信号重算所有守恒、双响应、停放地址、在途上限和周期差；内部诊断不替代外部证据。
- 新增checker至少用合成轨迹验证拒收：重复/丢失响应、I/D串源或错误lane、停放地址被live地址替换、第二笔物理读、未排空即AR、store未选字节错误、年轻错误路径store、复位取消账不平。合成自检不计HDL覆盖。
- 报告写 `DeepSeek/任务033_结果_ds_inst_hit_overlap_20261017_a.md`，给最终可复现命令、清单SHA、每job耗时/退出/Errors/Warnings、全部场景的真实cycle/token与计数、两版周期差、CPU架构结果、首败及未覆盖项，链接完整运行目录。不要贴整份日志，不生成Codex验收门。
- 成功状态仅 `TASK033_KEY_SIMULATION_PASS_PENDING_CODEX_REVIEW`，实板/PHY/Full Boot均NOT_RUN；失败 `STOPPED_FIRST_FAILURE`。交回Codex复核新测试实现、冻结身份和原始证据后才安排用户固定BIN实板比较；历史032与CAM2/CNN PASS不移用。
