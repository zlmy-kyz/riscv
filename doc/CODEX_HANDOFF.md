# RISCV SoC 开发交接

## 2026-10-19：视觉识别交同学，GitHub复现包与PDS依赖已整理、独立解压验证通过

用户要求上传GitHub并更新PDS相关文件，明确授权原始数据集也公开上传。目标现有公开仓库`zlmy-kyz/riscv`的master，不另开分支、不整仓盲推。交付`share/vision_handoff_20261019_a.zip`（33342312byte，SHA256 `4aa6cc4173f6c0a3d402bd98c8ffe66257b92f6f84d45ebe912fc8d29b85bad1`），入口[同学交接记录](cnn/视觉识别同学交接与复现_2026-10-19.md)及[完整手册](../tools/vision_handoff/README_交接.md)。

包含6219项文件、5339张源28灰度、准备NPZ/训练checkpoint/量化参数/独立整数参考、固定BIN与审计、7份真实采样和错例/诊断、当前PDS/6个IP/include/init/独立Loader DAT及当前生成sbit快照；源码发布清单189项、setup引用153项。sbit仅当前生成文件身份，不冒充FPGA回读匹配；KEY0暖复位仍未解决，沿每次先对准再JTAG恢复、KEY0保持释放。安装环境/工具链不上传。普通Git文本换行可能改变严格字节身份，视觉操作使用ZIP中project原字节副本。

独立解压新b目录后，全部文件/源图校验、离线plan及7次原始RX/TX回放、包外PDS副本路径迁移、153引用/独立初始化路径检查及篡改/目录复用拒绝均通过，178项保护原输入保持；收据`share/vision_handoff_20261019_a_validation.json`。首次辅助迁移断言因验证目录位于原根下误报，原a失败目录保持，修正精确INIT_FILE比较后新b通过，ZIP未改变。没有训练/HDL/PDS/串口/新实板动作。5次记录标签不匹配照实保留，不写整体识别通过；前一张1诊断及未覆盖范围保持，后续改进建议不当作已实现功能。

## 2026-10-19：实拍1仍预测0；固定模型离线对照已量化输入分布差异

用户要求分析最新`sim/cnn/board/handwritten_perf46_trial01_1_01`（sample7）。原始RX/TX只读复核通过，标签1/预测0、10分数与独立参考全部一致，584012周期/6.229461333ms、28包/完整尾部/释放闭合、零重试。收据`sim/cnn/handwritten_perf46_20261019_a/board_review_06.json`。图中是白纸黑色细小1，不是上一张黑底白字；该张错识别不能仅归因极性。

本次仅PC诊断：`diagnose_inputs_01.py`生成不可覆盖`input_diagnosis_01`，保持模型/BIN/合同/原图，3张既有实拍各7个预先固定的原样/反色/对比/中心裁剪组合，另取训练1/8各前2张及3个均匀底色控制。四张训练控制均判对，PC模型不是对所有输入恒0；实拍1所有变换仍未判1，小纸上8仅中心裁剪判8，黑底白8反色仍0，不能把裁剪或反色宣称为修复。空白灰192也判8，故猜中一个裁剪样本不足以证明真实辨字泛化。

实拍1输入均值146.416、像素中位数179，低于1200张增强训练1的每图均值196.288–250.677（中位数222.535）；未增强训练1均值中位数248.585。相机灰背景/暗边、尺度及笔画分布差异已有量化证据，不是模型未加载/板PC分数不一致；仍未确诊唯一根因。下一步优先以合同不变的实拍开发集和更匹配的增强方案准备训练/验证，独立最终session另留，不盲改RTL/正式PC输入；未自动重训、PDS或开串口。脚本、逐变换分数/张量/哈希、增强统计及边界见同一手写阶段末尾。

## 2026-10-19：sample6黑底白色8仍预测0，极性与约定训练输入相反

用户要求查看最新`sim/cnn/board/handwritten_perf46_trial01_8_05`（sample6）。只读原始RX/TX回放、75项输入身份、28包/ACK、退出/释放及零重试复核通过，真实标签记录8、预测0，CNN584023周期/6.229578667ms，全部10分数`[7440,-10270,-4087,-544,-3160,-1967,-2862,-5714,1252,2766]`与独立整数参考相同。正式收据`sim/cnn/handwritten_perf46_20261019_a/board_review_05.json`。识别仍错误，快模式未核源到PP。

本张RGB96和gray32清楚显示**黑底白色粗体8**，不同于此前纸上小/细笔画；不能继续把本张归为字太小。其极性与约定白底黑字及主要训练图相反，是直接可见的输入差异，但尚未做受控实验确认是否唯一原因。sample.medium为软件预填，不能当作本张确为白纸黑笔的证明。优先按约定改白底黑色8再采样，或在PC副本作反色诊断；正式输入合同/RTL/模型不自动反色或修改。当前只读复核，不打开串口、不重训，错例及原标签全部保持。

## 2026-10-19：第三张8仍错识别0，接续应转离线输入/模型诊断

最新sample5目录`sim/cnn/board/handwritten_perf46_trial01_8_04`只读原始回放通过，标签8/预测0、10分数与独立参考全部相同，584023周期/6.229578667ms、28包、正常尾部/释放、零重试；正式收据`sim/cnn/handwritten_perf46_20261019_a/board_review_04.json`。快模式未验证源到PP，不能记识别通过。将实际gray32与已有训练preview目视对照，实拍字形占比更小、纸背景偏灰，存在训练/实拍域差异线索，尚未确诊唯一根因。用户询问下一步：停止同条件盲拍，先在PC保持固定模型和合同做输入分布/受控变换诊断，诊断副本不替换正式实拍输入；依据证据再选训练增强/分session实拍数据路线，不先改RTL/正式预处理或立即重训。此次仅日志复核/计划，未运行新变换实验、训练、PDS或串口，详见同一手写阶段末尾。

## 2026-10-19：第二张标签8仍预测0，独立参考复核同样为0

最新`sim/cnn/board/handwritten_perf46_trial01_8_03`（sample4）原始RX/TX只读回放通过，28包、尾部、释放、零重试；标签8、预测0，CNN584038周期/6.229738667ms。10分数`[1724,-3744,127,-1584,589,-1132,-84,-2186,-1154,470]`与PC参考全部一致，正式收据`sim/cnn/handwritten_perf46_20261019_a/board_review_03.json`。这是再次错识别，不是识别PASS；快模式不验证源到PP。实际图中8仍偏小，笔画有细线及重复描画。下一步优先分析实际32灰度与训练输入分布，不重复同条件采样或盲改RTL；未重训/改模型、未打开串口，根因及原有验收缺项保持，详见同一手写阶段末尾。

## 2026-10-19：手写8快采样错识别为0，原始协议及全部10分数仍一致

用户要求查看日志，最新目录`sim/cnn/board/handwritten_perf46_trial01_8_02`（sample_number=3，session=trial046_01）。只读回放完整RX/TX、档案哈希及RGB96独立整数参考，28包和尾部/释放账本闭合，75项固定输入保持、零重试；正式收据`sim/cnn/handwritten_perf46_20261019_a/board_review_02.json`。真实标签记录8，预测0，`label_match=false`；板10分数`[1722,-3684,191,-1433,136,-991,-338,-2273,-743,623]`与PC逐项相同，CNN584037周期=6.229728ms。因此是该张识别错误，不是当前证据中的板/PC算术分数分歧；快模式未导出源帧，不追加源到PP通过结论。

目视RGB96/gray32中字形为偏小、较淡的细笔画8；尺寸/对比及真实相机域差异可能影响分类，尚未确定根因。下一步可保持同一模型/BIN，黑笔加粗并放大到中央区域约60%–75%重拍，使用真实标签8和新目录；不因单样本错识别改RTL、重训或覆盖原数据。此前`_0_02`目录已有完成日志，重复命令被保护性拒绝且未打开串口，原标签0/预测0记录保持，不擅自回填为8。单样本数据复核PASS与识别正确是两件事，当前不报总体准确率，KEY0/关键HDL/长稳等边界保持。

## 2026-10-19：PERF46首张手写0实拍原始证据通过，完整导出并非卡死

用户运行当前入口，看到SCORES后暂时无输出。本地只读查看确认`source.partial`从0持续增长至1843200byte，随后应用正常结束；这是完整串口导出阶段没有进度打印，不是CNN停住，未中断/复位/重试或修改代码。`sim/cnn/board/handwritten_perf46_trial01_0_01`完整原始RX/TX经新入口只读回放复核，正式收据`sim/cnn/handwritten_perf46_20261019_a/board_review_01.json`。

模型4c8b5aca/原固定BIN保持，用户标签0、预测0，10个整数分数与独立参考全部一致；CNN583794周期=6.227136ms。源1843200byte CRC32 c90374b0闭合，PP27648byte全部与源帧独立参考一致、CRC059d33fa，1829数据包/ACK及尾部完整，目标/尾帧2次claim、1次discard、释放账本闭合，零重试。RGB96已目视检查：白纸黑色环形手写数字，上沿可见手指及背景。

这是当前PERF46上**首张手写0**的数据通路及10分数正确，不是十类准确率、长稳/全部异常并发、关键HDL或硬件逐层dump验收；JTAG为操作者确认，未回读位流，KEY0暖复位仍未解决。复核不开串口，不要求PDS或重新训练。下一张可换白纸黑笔1，先对准固定、JTAG重新下载同一046位流、KEY0保持释放，用新目录并改真实`--label/--sample`；省略`--full-source`可快速探索，但不重新证明源到PP。原图和原日志保持，后续分数相等与是否识别正确仍分别记录。

## 2026-10-19：当前PERF46手写试识别PC入口已封存，JTAG恢复、不按KEY0，待用户首张实拍

用户授权“执行”，已新增独立`tools/cnn_handwritten_perf46/run.py`及README，对齐当前046的54项RTL/IP源码、有效CAM2 FDC和93.75MHz，显式登记相对旧CNN身份的6项CPU/互连变化。仅适配PC身份及复位记录，原58项软件输入、模型4c8b5aca、42568byte固定BIN（SHA256 `5b3364b064a4687a2e141bef504031fdc31a09d1e681b8cd1518133d4ee9f49c`）及历史证据保持，178项保护输入逐项核对未变；没有修改RTL/约束/IP/固件、重新训练或运行HDL/PDS/串口。

新入口每次要求用户JTAG重新下载当前046同一位流，KEY0保持释放、不再按键，等待DDR就绪后Enter。无需因本次PC适配重新PDS；操作者确认不冒充位流回读，KEY0暖复位仍未闭合。旧入口严格拒绝当前CPU身份，原代码/封存不改。新收据`sim/cnn/handwritten_perf46_20261019_a/ready.json`状态`HANDWRITTEN_PERF46_PC_READY_PENDING_BOARD`，75项运行输入绑定、软件增量封存`sealed_20261019_a`，复用原软件归档而不重复归档同一BIN。

本次离线`checks_02/review.json`通过两种原始串口合成回放（28/1829包）、15项错误身份/复位/证据语义拒绝及确认前取消不开串口检查；完整模式仍比较源到PP的27648字节及10分数。原数学/协议/C控制证据复用，不重跑历史全套。`checks_01`保留子进程CP936输出被按UTF-8解析的辅助脚本失败；修正显式UTF-8后用新目录执行，没有覆盖失败。均不是HDL、真实CPU或046相机/CNN实板PASS，更不是识别准确率验收。

下一步白纸黑笔写0，CAM2/J5、载板J10、两个测试模式0；关闭串口助手，按上述JTAG恢复，运行：`python -X utf8 tools/cnn_handwritten_perf46/run.py --port COM9 --label 0 --session trial046_01 --sample 1 --full-source --log-dir sim/cnn/board/handwritten_perf46_trial01_0_01`。确认画面稳定后Enter，首次完整源约3分钟或更久；每次新目录且先JTAG恢复，不能直接重复运行已退出的应用。端口按实物调整。详见[当前操作说明](../tools/cnn_handwritten_perf46/README.md)及[同一CNN阶段记录](cnn/手写数字数据准备与INT8训练_2026-10-17.md)。等待用户原始实板日志，未自动采样、不继承旧CAM2诊断模型PASS。

## 2026-10-19：恢复数字识别工作，模型/固定BIN保持，旧CNN入口需对齐CPU优化后的身份与复位

用户结束本轮CPU性能工作，要求重读文档恢复数字识别上下文。本轮只读合同/阶段记录及当前封存哈希，没有改设计/程序、重新训练、运行HDL/PDS或打开串口。目标仍为白纸黑笔、居中正向单个手写数字0–9；训练模型4c8b5aca、本地INT8 1045/1069=97.7549%、42568byte固定BIN5b3364b0…ee9f49c及58项封存软件输入均保持，当前`sim/cnn/board`未发现手写模型实板运行目录。

CPU最新046短P/V应用及46项读出已核，但不代替相机/CNN验收。与10月17日CNN硬件清单相比，当前data_bus_interconnect、dual_sram_to_pango_ddr_bridge、inst_bram_adapter、mycpu_sync、simple_mmio、soc_top六项源码不同；相机/CNN本体、有效约束及板级两测试模式0保持。旧`tools/cnn_handwritten_photo/run.py`在硬件身份校验处会拒绝当前源码，不能直接沿用此前命令，也不能仅删除校验来放行。当前CPU板试采用JTAG冷恢复，KEY0暖复位仍未闭合，旧CNN固定KEY0提示同样待适配。

恢复时先明确使用当前优化硬件或旧CNN成功硬件，再为选定身份准备匹配的PC入口/复位记录，保留原软件/模型/BIN和历史证据；本轮未实施此适配，不要求重训或重跑CPU历史全套。详细接续点见[同一CNN阶段记录](cnn/手写数字数据准备与INT8训练_2026-10-17.md)。

## 2026-10-19：046实板46项读出已核，MEM样本闭合，store容量/命中load资格是明确等待

用户要求性能分析。`sim/cpu_perf_detail/board/task046_pv300_20261019_040620`P/V各307完整实际回应、唯一RUN、零重试、完整尾RX、CRC5275/8803、46项/新bank状态ID/count/ROI/分类/缓存及新增守恒离线复核通过。[归因收据](../sim/cpu_perf_detail/board/review_task046_20261019_01/review.json)。热点/工作区布局和计时区字节再次与045实际BIN核对保持（仅ROI后跳板8字节不同），旧16项稳定计数不变。P232679213/2.481911605秒，V232972325/2.485038133秒，较045仅+755/+3418周期（+0.0003245%/+0.0014671%），各一次不作统计结论。

本次MEM严格闭合：等接受=旧写阻塞+D等I槽；等响应=D hit CPU等待+D miss原等待+每miss一拍；D hit CPU等待恰等于hit次数。store入队等待P23165557/V23316209（9.956%/10.008%总周期），按当前双条/允许周转配置即满队容量等待，占旧写阻塞74.36%/73.69%；命中load资格P7043446/V6964623（约3%），同线完成保护仅1762/1586（<0.001%）。D hit响应等待19393431/19572109（8.33%/8.40%），与时序切断的SoC load寄存一致，不能直接撤掉承诺收益。

MUL P/V均2827200条，busy=4×、未就绪阻挡=5×，且全为EX/MEM可前进时单独阻挡，done被MEM按住0；未就绪窗口约6.07%，但OTHER无退休交集只有8481600（约3.64%）。OTHER无退休还含EX空闲约6.35%及剩余EX非空约16.1%，不能当全部空转。045实际tail-only放行P317/V24，机会24136/17972，不再优先抠小碰撞窗口。[详细分解](cpu/CPU诊断计数器PERF46与固定布局读出_2026-10-19.md)。

下一单项优先评估约10% store容量等待的突发/排空机制，其次约3% load资格建立；MUL每条少一拍仅约1.21%机会量级，时序与数据有效沿需另外证明。本轮只分析/记录、不改RTL/IP/软件、不启动HDL/PDS/串口或重复P/V。046定向/时序及历史045/044/043/041042/KEY0/正式成绩缺项保持，不由应用计数通过扩大PASS。

## 2026-10-19：046已新增19项诊断（总46），固定布局软件已构建，待用户PDS

用户明确“全部添加，注意之前计数器地址错误”。已接D写阻塞四桶、独立I写阻塞、045机会/接受、MUL数量/占用/阻挡及交集、MEM等响应/等接受、D命中CPU侧响应等待、D等I槽和OTHER无退休EX空闲。四个RTL只加观察输出/接线/独立bank，CPU与桥功能正文保持；原27项ABI/软件保持。新metadata 0x10000300/304/308，19项计数0x10000340–3D4，[合同/完整身份](cpu/CPU诊断计数器PERF46与固定布局读出_2026-10-19.md)。

14配置静态展开通过（厂家黑盒），145旧输入只变4 RTL、141保持。[静态收据](../sim/cpu_perf_detail/preparation_20261019_a/review.json)。新固定软件tag measure_perf46_fixed_20261019_a，P/V各38800字节，原86符号/热点/工作区/栈地址保持、原装载字节只允许ROI后8字节跳板改变；扩展0x40008000–9790，栈仍0x4000F000–10000。[布局收据](../tests/cpu_performance_2b/build/measure_perf46_fixed_20261019_a/build_review.json)保护161项旧对象。新PERF46脚本离线plan各307应答/一个RUN，未开串口；旧27入口不会自动获得新计数，需新位流及新46入口。

下一步用户PDS检查观察扇出/采样/累加及MMIO mux时序；通过后DeepSeek按[任务046](../DeepSeek/任务046_PERF46观察计数与固定地址读出.md)开发封存/执行一组相关关键验证，含同拍参考/ROI/尾部、真实MUL/桥事件/归属、旧27兼容及新reader运行/解析反例，Sol核原证据后给上板命令。没有HDL/PDS/实板运行PASS，不把新BIN静态构建当验收；不改频率/IP/执行策略，不重复045成功板试或扩历史缺项。

## 2026-10-19：用户独立分析已核，下一轮诊断口径收敛，未改RTL

用户提供045分解及增加观察计数建议。本轮核RTL确认先诊断方向，补正：稳定事务数不变不能证明差异只可能是噪声，也没有重复样本证明噪声底；I侧AR等待不是现有D写阻塞的子集；MEM辅助等待有重叠，D hit×1拍约8.33%仅估算不能闭合或视为净可省。正常未取消MUL的busy为4拍，加启动拍则有5个ex_mul_ready=0采样沿，需分别计start/retire、busy、有效阻挡及OTHER无退休交集。CPU inst_buffer是一条32bit指令；x32 I-cache行是32字节，target_buffer_match=0不是“16字节I缓冲”的结论。细节与下一轮观察合同见[同一阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。本轮完成口径审查/文档，不改RTL/软件、不运行测试/PDS/板试；045结果和未闭合范围保持。

## 2026-10-19：045短应用P/V日志已核，性能近乎持平，未建立稳定收益

用户请求分析性能。离线复核`sim/write_buffer_read_overlap/board/task045_pv300_20261019_031833`，P/V各295实际完整60字节回应、唯一RUN、零重试、末尾extra RX空，固定布局同BIN/CRC5275与8803、27项/ROI/分类/缓存守恒通过。[比较收据](../sim/write_buffer_read_overlap/board/review_task045_20261019_01/review.json)保存原日志/离线verified/比较脚本哈希及044原证据核验。11观察源+BIN/ELF/manifest身份与当前一致，仅桥由044换为045 cb5b2fcc…a33cfd，CPU/MMIO保持044；JTAG为用户记录，不是FPGA回读证明。

P232678458周期/2.481903552秒，较044少2342周期（24.981微秒）、耗时变化-0.0010065%；V232968907/2.485001675秒，少4483周期（47.819微秒）、-0.0019243%。退休、分支数、I/D请求及hit/miss、DDR AR/AW、load-use、OTHER全不变。写阻塞P+3938/V-1417周期，未见一致下降；MEM只少2293/3880周期。当前各一次且没有实际tail-only放行计数，无法将这么小的差值与DDR时序相位/运行波动区分，不能宣传045已稳定提速，也不能反推候选从未触发。

剩余仍为MEM约25.0%–25.2%、写缓冲相关阻塞13.4%–13.6%、branch约9.7%、load-use约3.7%，诊断与分类重叠。下一项优先取得写阻塞原因真实分布（store容量、load资格、miss排空、同线完成保护等），再选主导项；现有日志不足以盲目扩队或推断全部13.5%能消除。[详细阶段分析](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。本轮仅分析记录，不改RTL/计数/BIN，不重复P/V或启动HDL/PDS/串口；045定向和历史044/043/041042/KEY0/正式>=10秒等未闭合范围保持。下文“待实测”为历史，板试成功也不反推PDS时序或完整功能通过。

## 2026-10-19：045精确跟踪写队头冲突，主桥单项修改静态通过，待用户PDS

用户要求下一步。拆读写阻塞后选中一个确定的过度保护：load命中B、旧head A异行、仅tail与B同行时，原注册标志head_match|tail_match会在A完成沿误挡load。045保持ready/资格/前递/队列/响应/DDR命令逻辑，仅将注册冲突位更新为下一周期真实head的匹配：本沿pop选旧tail，否则选旧head；真正head同行完成仍挡，连续提升不能漏保护。新DATA_READ_TAIL_OVERLAP_ENABLE默认1，0沿原逻辑；不加流水或新数据通路，不扩大缓存/队列，也不直接释放写busy/AR。

只改`myriscv/dual_sram_to_pango_ddr_bridge.v`，SHA256 `cb5b2fcc1c98af029419274f4972babbbaab966360cdeab45e50c64cefa33cfd`；CPU/MMIO保持044。静态105输入只变桥、104保持，[13配置展开收据](../sim/write_buffer_read_overlap/preparation_20261019_a/review.json)含board/x32/禁PERF/禁DDR、深度1/2及开关、x16/nonposted/禁前递/禁读写重叠/禁Dcache。厂家内部黑盒，仅静态展开，不等于功能/时序PASS。

下一步用户PDS检查本版时序，重点W完成到冲突标志D端及原ready路径；保留前轮内存不足排查，避免四seed并发压力。时序通过后DeepSeek按[任务045](../DeepSeek/任务045_写队头精确冲突与队尾同行读重叠.md)开发封存/执行一组相关关键验证，Sol核原证据后给上板命令。CPU未改，不新增ISA抽样；044/043/041042/KEY0未闭合范围保持。基线044 P232680800/V232973390周期，固定PERF27、93.75MHz；没有目标场景次数，不承诺总收益或可消除全部13.5%阻塞。本轮未运行HDL/PDS/串口、不重复P/V。

## 2026-10-19：044固定布局P/V实板日志已核，小幅观测收益0.085%/0.038%

用户交来上板后要求性能分析。本轮离线复核`sim/cpu_ex_redirect/board/task044_pv300_20261019_024009`：P/V各295实际完整60字节回应、唯一RUN、零重试、末尾extra RX空，固定布局同BIN/CRC5275与8803、27项/ROI/分类/缓存守恒通过。[原证据比较收据](../sim/cpu_ex_redirect/board/review_task044_20261019_01/review.json)保存逐项差值、当前11观察源及BIN/ELF/manifest身份、历史证据校验。CPU98e24594…47304b、MMIO e1a55e55…a50c06、043桥855318ee…83262f保持。记录JTAG启动，非FPGA回读证明。

P232680800周期/2.481928533秒/CPI2.146664，较043少198001周期（2.112ms）、耗时下降0.085023%；V232973390/2.485049493秒/CPI2.149890，少88597周期（0.945ms）、下降0.038014%。I请求及hit分别净少112497/112715，退休/redirect、I-D miss、D读及DDR AR/AW不变，支持重复命中取指减少；约193万目标响应匹配仍不等于实际复用数。净少请求/匹配机会约5.8%，不能当实测复用率，busy等拒绝原因未计。

当前MEM分类25.03%/25.18%，写缓冲相关阻塞13.39%/13.58%，branch分类9.69%/9.68%、load-use3.65%/3.68%，I/D miss等待各约2.5%–2.9%。诊断项与分类重叠不能相加。OTHER含80608764/80558272个伴随退休周期，剩余约6090万/6076万也不能自动视为空转。下一项优先评估有序写引起的D请求阻塞，区分store队满、load等待排空/重叠许可及同线保护，再决定单项改动；不能仅凭13.5%扩队或去掉044有序保护。详见[同一阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。

本轮仅分析/记录，未改RTL、未开串口或启动HDL/PDS、不重复成功P/V。各一次短运行，只称观测小幅收益，不作统计显著性或正式>=10秒成绩；044定向/两ISA/观察器边界未补齐，也未审查新版PDS时序。原043主动忙队FENCE、041/042完整动态、KEY0暖复位缺项保持。以下“无实测/最新PnR失败”为此前状态，不覆盖本次原串口证据，也不能用串口成功反推时序通过。

## 2026-10-19：044本轮PnR因内存分配失败中止，尚未得到时序结果

用户要求定位place/route失败。最新`pds.log`在02:15:59及02:20:08两次启动seed 2–5四路并行；四路均先报`Memory alloc failed for size 1048512`，随后报Flow-0013（输入map DB应处于DEVMAP）。保留的`place_route/seed_2/run.log:259–263`显示停在Phase 1.1首次全局布局、Design Utilization 11%，内存错误在先；Flow-0013暂按连带错误，若单路仍单独出现再查DB，不据此先删产物/重做RTL。`RISCV.pds:648–650`配置gplace_seed=2、gplace_times=4、parallel=4。当前读取内存为物理15.74GiB/可用9.62GiB、系统提交上限31.48GiB/余12.68GiB，仅为退出后的快照，不能证明失败时内存峰值；四seed并行的内存压力是优先排查方向。

建议用户在PDS先改为单seed/单并行（times=1、parallel=1，seed仍2）、关闭无关高内存程序后重试；本次只查日志/记录，未改PDS/RTL、未启动实现或仿真。若内存问题消除后仍报独立Flow-0013，再由用户重做Device Map；若仍分配失败，继续核系统提交/分页与进程限制。根`place_route/run.log`仍是10月18日21:29:59的旧成功日志，不能用于本次044时序结论。044保持待PDS通过及后续关键功能验证。

## 2026-10-19：044同拍分支目标响应复用已改，静态通过，待用户PDS

用户要求分析并提升性能。043固定布局P/V实测232878801/233061987周期、2.484040544/2.485994528秒，相对单条耗时下降3.152217%/3.111063%。写阻塞仍约13.4%–13.6%，但不据此扩队；本轮选每轮约193万次“重定向目标与同拍响应PC匹配”的前端机会，机会数不等于可省周期。

044只改`mycpu_sync.v`前端与`simple_mmio.v`恢复观察器：普通EX重定向T遇到有主、成功、PC匹配的旧I响应且有序写已排空，旧数据直接进入IF/ID，同拍新I改为T+4；接受则PC=T+8，背压则PC=T+4重试。未匹配/错误/写busy走原路径，旧buffer仍冲刷，trap/MRET/复位保留优先级。同步修正同拍交付目标时恢复观察器的结束条件，避免等待已经交付且不再重取的T。后端、DDR桥、固定BIN及93.75MHz不变。

[静态收据](../sim/cpu_ex_redirect/response_reuse_20261019_a/review.json)：98输入中仅CPU/MMIO两项变化，96项保持；12配置静态展开通过（厂家内部黑盒，非功能/时序PASS）。CPU SHA98e24594…47304b，MMIO e1a55e55…a50c06，完整身份/边沿说明见[阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)及[任务044](../DeepSeek/任务044_分支同拍目标响应复用.md)。

**下一步用户用RISCV.pds重新实现检查时序**，重点看寄存PC比较到取指地址/IF-ID使能、T+4/T+8及恢复观察器路径；通过后再由DeepSeek按044实施本组验证及种子2026101944抽样auipc/slti，Sol核原证据后给上板命令。本轮未执行HDL、PDS或串口，044收益尚未实测；043直接板试授权不扩成044跳过验证，原FENCE/041042/KEY0缺项保持。

## 2026-10-19：043双条写缓冲实板应用P/V通过，耗时降低3.15%/3.11%，FENCE缺项保持

用户要求性能分析。本轮离线核`sim/write_buffer_two_entry/board/task043_pv300_20261019_012040`两日志各295完整回应/唯一RUN/零重试、固定布局同BIN/CRC5275与8803、27项/ROI/分类/缓存守恒/末尾extra RX均通过。[比较收据](../sim/write_buffer_two_entry/board/review_20261019_01/review.json)保存原始身份和相对单条固定布局基线的差值。P232878801cycles/2.484040544秒/CPI2.148491，V233061987/2.485994528秒/CPI2.150707；耗时分别缩短3.152217%/3.111063%，吞吐增加3.254816%/3.210958%。

写阻塞减少8239910/8160411周期（约20.9%/20.5%），MEM分类减少约807万/814万；IF/branch小增后净省7579776/7483522周期。退休/redirect/AR/AW/I-D请求命中失配数量全不变，支持同工作量等待隐藏收益；I miss等待增加57万/75万，诊断计数可重叠不重复相加。当前写阻塞仍13.4%–13.6%，不能由此自动扩四条队列。详细数据见[同一阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。

本轮仅离线复核记录，无RTL/HDL/PDS/串口操作、不重复成功P/V。各一次不足10秒，非正式成绩；用户直接板试不补齐FENCE主动忙队触发、原041/042完整动态、KEY0暖复位等缺项，两轮JTAG成功不证明暖复位修复。下文“尚无结果”为此前状态。

## 2026-10-19：用户授权043直接上板，固定布局P/V各一次，FENCE缺项保留

用户明确“直接上板”，本轮按直接应用板试推进，不再以FENCE忙队收尾或PDS审查收据作前置；未补做FENCE、不将时序/完整043验证记PASS。PDS生成/下载由用户操作，Sol未检查位流或运行硬件。桥保持855318ee…83262f；固定布局`measure_perf27_fixed_20261018_a`P/V BIN哈希保持4a090b36…a63310/8dd05805…24cb4，93.75MHz，对照已核P240458577/V240545509cycles（2.564891488/2.565818762667秒），旧成功基线不重跑。

仅主PERF27双项PS1追加`-ResetMethod key0|jtag`并传给已有Python入口，默认key0兼容历史；本轮指定jtag。离线`-PlanOnly -ResetMethod jtag`至`sim/write_buffer_two_entry/board/task043_direct_plan_20261019_01`已核P/V各295预期应答/唯一RUN、未开串口。实际命令/步骤见[同一阶段直接板试](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)及[工具当前入口](../tools/uart_loader/candidates/perf_2b/README.md)。两轮各先JTAG下载同一043位流、KEY0保持释放、等DDR就绪再Enter；运行不复位，首败停止保留日志，新目录自动时间戳不覆盖旧证据。

尚无本轮实际CRC/27计数/性能结果，不认定提速；公平小片段41/41无净收益结论保持。用户返日志后继续核原始应答/CRC/计数/时间和同BIN总cycles，未收到本轮实测不另起优化。KEY0根因、FENCE主动忙队触发、原27项完整回归及正式>=10秒范围仍未闭合，用户直接板试不会扩大PASS。

## 2026-10-19：043补正02原证据已核，公平41/41无净收益，仅FENCE忙队触发待补

Sol已核`xs_{fair_d1,fair_d2,edge,x16,noposted,ruw0,soc}_20261018_d`，[审查收据](../sim/write_buffer_two_entry/review_20261019_01/review.json)接受桥各12项/SoC49项封存与递归include/当前RTL身份、命令/退出码、外部事务和独立字节账；未运行HDL/PDS/串口或修改测试/RTL。公平两深度同后端、6逻辑请求/4AW/4W/初末内存相同，41/41周期、净0；第二store22→13更早接受，store容量等待14→7而load miss排空6→13，支持等待转移，不能写提速。现桥SHA855318ee…83262f保持。

新增边沿7store/11load/6I、全32768字节末内存一致，tail独自同行跨提升、warm I毒化、AR/R同沿2次、AW后init暂停、互补mask/SH及旧响应接续均有实际证据；x16/nonposted/RUW关闭最小片段也已核。SoC两epoch10AW/10W、11AR/11R，84退休PC/inst与冻结程序、有效GPR结果/数据访问和全16384字节末dump一致；UART56/RAM57晚于初始两W45/55、严格head已完/tail未W的46–55窗口实际背压10沿（原报告11沿包含head完成沿45），IRQ301晚于两W290/300，mcause8000000b及handler标记正确。Camera/PP各两实际AR和变化数据通过，只是功能模型窗口/缓存边界，不是实拍或完整IRQ。48份变异FAIL已核，逐次原stdout/native调用未齐，保留限制。

仅余FENCE忙队触发：现程序两store→UART→RAM→FENCE，UART先等排空，故FENCE64退休只证明正常顺序，不能写其主动阻挡未完成写已验。[唯一收尾](../DeepSeek/任务043_收尾_仅补FENCE忙队触发.md)只补“两store→FENCE→完成标记”一个真实CPU片段，必须让FENCE实际处于head已完/tail未完窗口；前后14项成功组/公平/IRQ/旧P/V不重跑，不改RTL/系统环境。当前不标043完整功能PASS或上板就绪；本版PDS通过仍须有效回执，文件不自动执行，缺项核完直接准备板测。KEY0/正式成绩/原27项完整范围不扩张。

## 2026-10-19：ModelSim -c重新测试通过，IPv6回环和最小HDL运行已恢复

用户要求重新测试。本轮原样复制20261018的`check.py`与`tool_health.v`到新目录，不改旧失败证据。IPv4/IPv6回环listen/connect均成功；vlib/vlog退出0，编译Errors/Warnings0；同一空模块两次`vsim -c -onfinish exit ... -do "run -all; quit -f"`都实际运行到1ns，输出`TOOL_KERNEL_OK time=1000`，退出0、Errors/Warnings0、无RPC_Init、无超时。当前默认执行环境下**-c最小HDL运行已恢复**，此前工具阻断不再复现。本轮没有修改或复核代理配置，不推断用户具体改了哪个开关，也不扩大为所有网络策略已修复。

[复测原始结果](../sim/modelsim_health_20261019_retest_a/results.json)与[输入/日志SHA收据](../sim/modelsim_health_20261019_retest_a/review.json)保存在新目录。仅工具复测，不编译工程RTL、不跑043/历史功能测试/PDS/实板；GUI未测。后续工程测试仍按有效任务及本版时序回执条件执行。

## 2026-10-19：ModelSim -c阻断已定位到Clash TUN的block ipv6规则，配置未改

用户询问修复。经Windows UAC授权只读导出WFP后，确认`Meta / block ipv6`（filterId71204）在`FWPM_LAYER_ALE_AUTH_CONNECT_V6`无条件BLOCK，覆盖::1；同sublayer的高优先permit只匹配`clash-verge-service/cores/verge-mihomo.exe`。管理员独立回环探针也是IPv4成功、IPv6 connect阶段10013，排除只归因普通执行权限。已只读核Clash当前TUN enable/auto-route/strict-route均true、顶层ipv6=false，与上游MetaCubeX/sing-tun创建该动态拦截的条件一致。直接阻断来源已定位，不归因Tailscale或许可证。

[修复说明和原始诊断](../sim/modelsim_repair_20261019_a/README.md)：可在Clash TUN关闭严格路由并重启TUN/内核，但会同时取消该模式DNS防泄漏过滤；需要保留严格路由时应配置可用的TUN IPv6地址/支持。当前未修改代理/网络/防火墙/hosts/注册表/工具安装，尚未复验修改后的-c，不记修复PASS。此前-batch空模块成功保持，工程功能/043/PDS/实板边界保持；只读管理员诊断不等于功能测试。

## 2026-10-18：本机ModelSim环境复核，-c内核RPC失败，-batch空模块可运行

用户要求检查“ModelSim本机已不可用”。本轮只做独立工具诊断，不编译工程RTL、不运行043或历史功能测试。`D:/modelsim/win64pe/{vsim,vlog}.exe`版本查询均为DE-64 10.6c、退出0；命令行Tcl启动/退出正常，独立`tool_health.v`编译Errors/Warnings0。默认环境两次`-c`加载空模块均报`RPC_Init ... ::1 ... couldn't open socket: invalid argument`，20秒超时终止，无HDL标记；经批准沙箱外同样报错并15秒超时。两种上下文IPv4回环listen/connect成功，IPv6回环WinError10013。可确认当前-c内核启动阻塞及IPv6回环异常，具体宿主/会话/网络过滤根因未确定，不据此归因防火墙、代理或许可证。

依本机帮助及既有021记录改用标准`-batch -onfinish exit -logfile batch_transcript.log work.tool_health -do "run -all; quit -f"`，同一空模块实际运行至1ns，`TOOL_KERNEL_OK time=1000`、退出0、Errors/Warnings0。结论为**-c当前不可用，-batch最小HDL运行可用**，不能笼统记整个ModelSim不可用或系统IPv6已修复；未检查GUI，不扩大为工程/IP/043功能通过。未改系统网络/权限/许可证、RTL/PDS/IP/BIN或现有测试入口，也未派发DeepSeek。后续工程执行可沿标准batch入口，仍遵守本版PDS时序回执和任务范围。

诊断源码、复现命令及原始输出见[工具记录](../sim/modelsim_health_20261018_a/README.md)，默认/沙箱外结果与batch日志均保存在该独立目录。历史失败保持。

## 2026-10-18：043新版桥片段/封存已核，9拍差异不是公平净收益，待最小缺项

Sol已离线复核`xs_key_20261018_c`、`xs_short_{old,new_d1,new_d2}_20261018_c`和三项posted兼容短序列，各11项封存输入/前后SHA/副本编译命令与实际退出码通过。[新收据](../sim/write_buffer_two_entry/review_20261018_02/review.json)独立重建主组44store=40W+4取消、90D=88响应+2取消，46load+2I数据和全8192字节末内存一致，满队同沿接续及真实W/load碰撞触发；旧桥与新depth1的44沿/mark一致。仅接受实际所见桥片段，不等于043完整功能通过。

短序列第二store18→11、S_done40→31为真，但冻结刺激depth1条件分支设w_hold2并晚释放后端，depth2保持0拍并更早释放；9拍含不同DDR条件，不能记队列净提升或CoreMark加速。ModelSim与xsim key计数虽同，TB/参考SHA不同且edge58 init采样不同，不作同一输入跨后端逐沿等价；厂家IPSpecCheck04030130诊断在旧/新均存在并保留。

剩余SoC全队排空/FENCE/IRQ/CameraPP、非posted模型失败、x16/RUW关闭及tail独自同行提升/warm I hit毒化/AR-R同沿等缺项；测试参考还有I归属及非posted布尔优先级问题。[补正02](../DeepSeek/任务043_补正02_集成兼容与固定后端对照.md)只补缺项和公平短对照，不重跑已核7项/旧成功P/V、不改RTL或系统环境；本版PDS通过仍未有回执记录，不自动执行。桥SHA855318ee…83262f保持，本轮只离线审查/记录，无新HDL/PDS/实板；后续缺项核完才给板测，KEY0及正式成绩边界保持。

## 2026-10-18：043返回实验未接受，局部事务一致，测试与运行需补正

用户要求查任务结果。Sol只离线核`sim/write_buffer_two_entry/key_20261018_b`、`key_20261018_c`及`tmp_probe`，未运行HDL/PDS/串口、未改RTL/TB/参考/runner。[审查收据](../sim/write_buffer_two_entry/review_20261018_01/review.json)固定现有证据和当前测试源码SHA；桥保持855318ee…83262f。b原checker FAIL含沿前busy与沿后队列比较、初始DDR未入账问题；当前测试已局部修改但b没有封存/命令/退出码，不能认定其运行身份或改原FAIL为PASS。

b476沿外部账独立重建：41 store=37实际W+4复位取消，38 AW=37 W+1 AW后取消；D80接受=78响应+2取消，I2/2，AR/R14/14。39 load+2 I读值按观测R/cache/逐字节转发重建一致，已知500 DDR字节与末dump一致；未知初始字节未验。满队同沿接续在edge23真实触发。仅支持所见局部机制，不能扩为新RTL功能验收或性能提升。

缺项明确：G2_same_edge实际同沿AW/W0次，G4 load在ready0时撤valid后才W（edge358），G5也撤未接受请求；旧版入口仍编译当前桥、depth1短序列会卡住，SoC顺序/兼容/完整封存未完成。c vlog Errors0/Warnings0、8项源SHA与当前匹配，但vsim.log空且无新轨迹；probe为ModelSim RPC socket启动错误，未获得仿真结果。

[补正01](../DeepSeek/任务043_补正01_参考边沿与真实覆盖.md)要求DeepSeek修参考/刺激/旧版选择/DDR模型/失败保存，真实封存后完成原043一组相关验证；不改RTL/降判据、不倒填旧失败、不重复旧成功P/V。当前仍无本版用户PDS时序通过记录，不自动运行/派发；待明确通过及环境恢复后按补正推进，原证据复核通过再上板。详情见[同一阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)，KEY0及其他未验范围保持。

## 2026-10-18：043两条顺序写缓冲已接主桥，静态完成，待用户PDS

用户要求沿Astra单项方案继续，并明确“你来修改”。本对话只改`myriscv/dual_sram_to_pango_ddr_bridge.v`：追加`WRITE_BUFFER_DEPTH=2`参数（1兼容单条），x32 posted增加年轻tail，head独占AW/W、不合并写；空余条目接收新store，满队可在head完成同沿提升旧tail并入新tail。两条命中同word时按字节新覆盖旧，forward锁存归属响应；注册load资格/DRM碰撞保护检查两条，full tag/lane匹配。busy覆盖全队，原SoC的非DDR/FENCE/IRQ和AR排空连接保持；I接受store失效、D实际head W更新及035冲突/停放/034 ACK不变。

[静态收据](../sim/write_buffer_two_entry/preparation_20261018_a/review.json)=TASK043_TWO_ENTRY_STATIC_ONLY_PENDING_USER_PDS：14配置空目标展开通过，厂家内部黑盒，原board两条端口coerced-to-inout warning保留。当前桥SHA=`855318eebf7fc75a0b17d15a620b6d8d08bb54ff9348d663cbcd6aca0883262f`，其余78项当前输入保持，CPU/SoC/MMIO与固定布局P/V BIN未改。042后现有PDS工程/rtr身份变化已另记，不继承其时序。没有动态仿真/PDS/串口或新实测，不能声称提速。

边沿状态表、forward/排空审查及复现见[同一阶段043](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。下一步用户根`RISCV.pds`重新实现检查本版时序；通过后才依[043单组方案](../DeepSeek/任务043_两条顺序写缓冲关键验证.md)交DeepSeek实现/执行并由Sol核原证据，再同一固定布局PERF27板测。旧P/V240458577/240545509周期复用不重跑；不改频、不承诺16.5%收益，不扩大KEY0/041+042完整验收范围。

## 2026-10-18：依据固定布局27项计数，推荐两条顺序写缓冲候选，未实施

用户要求推荐一个CoreMark提升思路。本轮复用并核固定布局PERF27最终原证据，写缓冲阻塞P/V为39484828/39774499周期（16.42%/16.54%），I/D miss等待各约2.5%，I命中99.88%、D读约98.9%，目标buffer匹配0/同沿响应匹配约193万。推荐优先评估两条顺序posted写缓冲，保持物理写顺序且不合并写，尝试隐藏连续store等待；该计数也含load排空/资格/冲突，不能把16.5%视作可全消除收益。

实施需保留全队排空、逐字节最新写转发、每笔实际W更新D、接受时I失效及满队/同拍出入队/复位语义；关键轨迹分清store和load阻塞，以固定布局同BIN总周期作收益判据。完整建议见[同一EX/计数阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。本轮仅分析与记录，未改RTL/仿真/PDS/串口、不重复P/V或自动实施新阶段。

## 2026-10-18：固定布局PERF27 P/V实板应用均已核通过，耗时恢复，JTAG冷恢复成功

用户确认恢复成功，Sol已核`perf27_fixed_v_jtag_01/validation_300.json`全部295实际应答（逐笔60/60字节）/唯一RUN、CRC8803、27项/ROI/分类/缓存守恒/末尾extra RX为空，与此前固定布局P组成[最终P/V原证据收据](../sim/cpu_cache_perf/fixed_layout_20261018_a/board_review_final_01/review.json)。P240458577cycles/2.564891488秒、V240545509/2.565818762667秒；相对042原固定BIN仅+0.001892%/+0.000733%，新增读出导致的移址性能干扰已基本消除。I打印命中率P/V均99.88%，D读P98.94%/V98.98%。

P/V各295回应/唯一RUN、CRC5275/8803和27项链路的短应用实板验收闭合；旧P/V和首败日志、独立段BIN身份保持。P/V之间仅PC部分RX记录/JTAG提示改变，RTL和两BIN身份一致，登记本地位流同为e7a6b244…e4b3；未独立读回FPGA。V自报reset_method=jtag、KEY0未按，说明同位流JTAG冷恢复成功；原`perf27_fixed_300_01/validation_300.json`首PING FAIL不覆盖，KEY0暖复位根因仍未解决，不能标暖复位修复。

本轮不重复成功P/V，不生成新位流、不自动启动其他优化。时间不足10秒只作对比，不记正式CoreMark成绩；应用通过不扩大为041+042完整握手/冲突/背压/复位/IRQ回归。后续性能分析以此固定布局27项日志为入口，旧移址版只留诊断/历史对照。

## 2026-10-18：固定布局P已实板通过并恢复原耗时，V首PING超时未下载，改同位流JTAG冷恢复仅补V

已核`sim/cpu_cache_perf/board/perf27_fixed_300_01`：P295实际RVLD回应/唯一RUN、CRC5275、27项/READY/守恒及末尾extra RX通过，240458577cycles/2.564891488秒；对042原固定BIN240454027仅+4550cycles/+0.001892%，布局造成的约1.45%开销已在P基本消除。I打印99.88%、D读98.94%，AR378782（原固定378768）。不是>=10秒正式跑分，也不扩大完整041+042范围。

V仅发送第一条`PING_fresh_loader`36字节后5.00554秒等待60字节应答失败；无LOAD/VERIFY/RUN、app空，尚未执行validation程序。旧read_exact丢弃了短返回缓冲，原日志无rx_hex，不能声称收到0字节或确认具体硬件根因。症状与既有KEY0/启动恢复问题一致，仍未解决。[原证据收据](../sim/cpu_cache_perf/fixed_layout_20261018_a/board_review_01/review.json)保存P独立审查、原P/V/identity SHA、原host源码及失败缺项。

只修PERF27 PC入口：保持原5秒deadline/无自动重试/无flush，今后保存0/部分应答原始字节与实际/预期长度；增加`--reset-method jtag`提示KEY0保持释放、不再按键，并记录用户声明的复位方法。主BSP Loader/RTL/BIN/PDS不改，host碎片完整60字节/0字节/7字节超时记录检查通过；旧失败目录不补填。新V-only PlanOnly在`sim/cpu_cache_perf/board/perf27_fixed_v_jtag_plan_01`，295预期回应/唯一RUN，未开串口。

用户下一步JTAG重新下载同一现有e7a6b244…e4b3位流（不重新PDS），KEY0始终释放，等DDR就绪后直接Enter，本轮不再按KEY0；只执行`python tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py --application validation_300 --port COM9 --reset-method jtag --log sim/cpu_cache_perf/board/perf27_fixed_v_jtag_01/validation_300.json`。不重复P、保留首败；若fresh JTAG仍首PING失败，只依据新部分RX/实际停点定位，不延长超时或扩整套。当前只有P完整应用通过、V待恢复，KEY0/完整动态未PASS。

## 2026-10-18：PERF27固定布局版已完成，原被测字节/86符号保持，待用户同位流实测

用户明确固定热点代码/工作区，把新增读出放独立段。新增`tests/cpu_performance_2b/{build_perf27_fixed.py,perf27_fixed_software.py}`，以冻结P/V300 ELF的原text/rodata/data字节和BSS范围建立新ELF，不重编或重链接CoreMark算法。每项原86符号、原四段地址/大小全部保持；旧加载区只在`perf_dump=0x40001410`入口8字节改LUI t0+JALR zero跳到`perf27_dump=0x40008014`，保留RA/SP，原函数仅在冻结后调用。其余15204/15212字节加载区逐字节一致。

独立`.perf27_text=0x40008000`、`.perf27_rodata=0x40008bf8`、`.perf27_data=0x400090f0`，结束0x400091d0，避开原BSS末尾0x40004378和原栈0x4000f000–0x40010000。计数暂存为初始化装载字节，未扩大原startup清BSS循环。原main0x40001570、iterate0x400014d8、工作区static_memblk0x40003ba8及timer/GP/栈保持。所有新旧可执行段仍逐指令白名单检查，所有装载字节与ELF/空洞零填充核对、段不重叠/栈边界检查通过。

新BIN为`tests/cpu_performance_2b/build/measure_perf27_fixed_20261018_a/{performance_300,validation_300}/program.bin`，均37328字节；P SHA=`4a090b360f0889e961c2cfe1e6ae90fa1298bb868d65ae8aebf23f9a01a63310`，V=`8dd0580509e2357e6742b925ae13986abbbf2a5fd206bc7e3b4deec54f224cb4`。原固定/首版PERF27成功与失败BIN、日志保持，RTL及位流不改。[静态及离线收据](../sim/cpu_cache_perf/fixed_layout_20261018_a/review.json)为RUNTIME_PENDING；既有UART仅重放检查新schema，不冒充新BIN执行证据。PlanOnly各295预期响应/唯一RUN，串口未打开；平坦BIN含独立段前的填充，下载更长但不计入ROI。尚不能承诺准确周期或性能恢复。

`run_perf27_measurements.ps1`与Python入口默认已切固定布局tag，兼容显式旧tag，旧日志verify可从manifest自动识别tag。下一步用户保持当前含041+042的位流、无需PDS/重下载位流，按提示KEY0释放/等DDR/Enter，只运行新布局P/V各一次：`& tools/uart_loader/candidates/perf_2b/run_perf27_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_cache_perf/board/perf27_fixed_300_01`。对照042原固定BIN P240454027/V240543747周期；按93.75MHz比较，收到日志再核是否恢复。不重跑旧BIN、不自动启动其他优化或DeepSeek；041+042完整动态/KEY0边界保持。

## 2026-10-18：PERF27变慢来自新BIN布局的证据，旧固定BIN在042硬件上基本不变

用户询问时间变长。已离线核此前尚未审的`task042_fixed_pv_300_01`固定P/V两日志及刚返回`perf27_v_parser_fix01_01`V：123/151实际RVLD回应、唯一RUN、CRC/分类/计数/末尾extra RX均通过；PERF27 V CRC8803/27项通过，P仍沿前节CRC/27数值恢复与末尾extra RX缺项口径。新[比较收据](../sim/cpu_cache_perf/software_20261018_a/timing_comparison_01/comparison.json)保存三项离线审查、原日志SHA及布局。

042旧固定BIN：P240454027cycles/2.564842954667秒，V240543747/2.565799968秒，相对039同BIN仅−2411/−863周期（−0.001003%/−0.000359%），无明显计数硬件周期退化。登记为同一本地e7a6b244…e4b3位流的新PERF27：P243950601/2.602139744秒、V244006001/2.602730677333秒，分别比本轮固定BIN+1.454155%/+1.439345%。登记位流哈希相同不等于独立读回板上内容。

两版退休数、AW和branch数保持；P AR378768→513899（+135131），MEM66417820→70341915（+3924095），V AR+137922、MEM+3854983。ELF显示CoreMark热点函数统一后移1008字节，工作区static_memblk从0x40003ba8移至0x40004b18，计时port完全相同、start/stop地址保持。证据支持新增读出改变代码/数据布局进而改变cache映射，未采逐miss因果轨迹，不把推断写成逐笔证明。打印在ROI冻结之后，不计入上述CoreMark时间；串口全过程另有更多输出等待。

本轮只核已有证据/记录，不重跑P/V或改RTL/软件/PDS。PERF27目前用作瓶颈诊断，严格CPU性能对照继续用旧固定BIN；后续若要让新增读出不扰动测量，需固定被测热点/数据地址并独立安排读出段，尚未实施此布局修复。不因本轮结果自动开始其他优化，041+042完整动态/KEY0范围仍未扩张。

## 2026-10-18：PERF27首P实际已完整输出，解析器十六进制大小写错误已修，下一步仅补V

`sim/cpu_cache_perf/board/perf27_300_20261018_124013/performance_300.json`原FAIL保留：151实际RVLD应答/唯一RUN均通过，实际UART含完整27项与两个DONE；BSP`uart.c:number`将`%x/%X`都输出大写，而新扩展解析仅接受a–f，故在status=0000000F/0000000B误拒绝。现只修`perf27_software.py`元数据及新增计数值为a–f/A–F，位宽/ID/READY/语义判据保持；RTL、C、ELF/BIN与其他登记输入逐项SHA保持，不需要PDS/重建/重下载新BIN。

[修复及原证据收据](../sim/cpu_cache_perf/software_20261018_a/parser_case_fix01/review.json)复核实际P CRC5275、243950601cycles/2.602139744秒、全部27项/两缓存req=hit+miss/原13分类守恒与新约束；I打印99.88%、D读98.21%，原AR513899也恰为I miss164741+D miss349158。真实大写与离线小写/混合均通过，9种错误格式/READY/守恒/率等仍拒绝。原始FAIL不改为PASS：解析异常发生在末尾0.1秒额外RX检查之前，app缺extra_rx_hex，该尾检查缺项保持；仅接受实际CRC/27计数，不称原完整工具板测PASS。新BIN与旧固定BIN不同，不据此声称RTL性能变化，完整041+042动态/KEY0边界保持。

V未开始，不重复已有P。修复后V-only PlanOnly在`sim/cpu_cache_perf/board/perf27_v_parser_fix01_plan_01`，151预期响应/唯一RUN、未开串口；实际只执行`python tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py --application validation_300 --port COM9 --log sim/cpu_cache_perf/board/perf27_v_parser_fix01_01/validation_300.json`，保持当前同一位流，按提示KEY0释放/等DDR/Enter，运行不复位。原失败目录与旧离线收据保持。

## 2026-10-18：PERF27串口读出软件/构建/解析与上板入口已补齐

用户指出没有新输出并要求更新相关文件。已新增`tests/cpu_performance_2b/{perf27.c,perf27_software.py,build_perf27.py}`及`tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py`、`run_perf27_measurements.ps1`；原固定P/V300整目录、`perf.c/.h`与RTL保持。新程序冻结后核两扩展ID、等待两READY，读全27项并打印新增14项/命中率；PC严格解析27项，拒绝旧13项/缺项/重复/错误率/尾样本未完/不守恒。当前使用新PERF27入口，下文“软件未实现”和旧13项命令为历史。

P/V新BIN在`tests/cpu_performance_2b/build/measure_perf27_20261018_a`，18936/18944字节；P SHA=`b4a64b8c7d8dc09c03641e387fedd05332add17e6c1501f2875be6ae2677066c`，V=`5540da8b5f05c4c1b0855fc027bed6aee2158913f37277094902cbdfd0ce9c9c`。完整ELF布局/可执行指令白名单通过，新程序尚未执行CPU/实板CRC，5275/8803仅沿用独立参考。不同BIN/布局不能当旧固定P/V同输入性能对照；当前软件及BSP要求实际93.75MHz，改频须配套调整。

[软件离线审查](../sim/cpu_cache_perf/software_20261018_a/review.json)P/V各3正例+13拒绝样本通过，扩展字段是明确标记的合成格式检查；最终`sim/cpu_cache_perf/board/perf27_plan_20261018_02`各151预期响应/唯一RUN，串口未打开。不是硬件动态、PDS或实板PASS。041+042时序/相关动态及KEY0问题保持，DeepSeek后续复用本软件验证，不再重复实现读出。入口/KEY0步骤见[EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)和[工具README](../tools/uart_loader/candidates/perf_2b/README.md)：`& tools/uart_loader/candidates/perf_2b/run_perf27_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_cache_perf/board/perf27_300_01`。

## 2026-10-18：042等待与目标复用机会八项计数已接入，共27项，等待用户PDS

用户随后索取上板命令：已核现有固定P/V入口，离线`-PlanOnly`在`sim/cpu_cache_perf/board/task042_fixed_pv_plan_01`通过（P/V各123预期回应、唯一RUN、未打开串口）。实际命令及KEY0步骤见[EX阶段042板测入口](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。该入口仍只读原13项，新增14项诊断软件尚未实现，不能把该板试称为27项计数验收；本版PDS/动态/实板结论仍待外部结果。

用户授权添加刚推荐的六项周期（I miss等待、D读miss等待、写缓冲阻塞、旧I阻挡、EX分支等老MEM、OTHER同时退休）及目标buffer/同沿响应匹配两项次数。只增加观察口/跟踪/银行，CPU流水控制及桥原功能体保持；旧13项和041六项时序块保持。当前27项，不包含历史其他可选指标，没有实现指令复用/提速。新银行`0x10000280–2BC`，元数据`0x10000130/134/138`，冻结后等134.bit3；读全27项需DONE并同时等124.bit3。源E同沿原始包→E+1比较/追踪→E+2累加，窗口按源沿裁剪，START初始化及尾事件完成后READY。

旧I占用含redirect沿、不含旧返回沿；目标匹配用旧buffer/pending与注册目标同源快照，错误不计、buffer优先互斥。I等待包含停放/共享DDR，D只跟踪真正接受的cacheable读miss，store/Camera/PP uncached不算。等待数可重叠，只是窗口占用；不直接当可删周期或用接受miss数除得严格平均延迟。完整[接口定义](cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)与[EX阶段](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。固定P/V BIN保持，旧软件不会自动打印新项。

[042静态收据](../sim/cpu_cache_perf/diagnostics_20261018_a/review.json)=TASK042_DIAGNOSTICS_STATIC_ONLY_PENDING_USER_PDS；13配置空目标展开通过，厂家内部黑盒，75项其余输入保持。当前SHA：CPU`01be622cd5a727210c938b705e6cc0d44fba9d148d340964836d5509f68689a0`；桥`57f13e335ebcbba9b1d45ff4712284f4786d8291041c0d80ad82138309a95b35`；MMIO`15b04be11bda313faec6129c0d89bb7f9f1fd9fd9e6c9efd8b0f36a693e9afec`；SoC`5c5a68500feed374fb234327d1278a45b487df80592e2b197c7fc5b508bea64e`。CPU只观察输出变化，不再沿用039文件哈希；旧成功证据保留。

下一步用户根RISCV.pds重新实现检查本版时序；[042合并方案](../DeepSeek/任务042_等待周期与目标复用机会计数.md)待通过后才由DeepSeek实现/执行041+042一组，旧041草案身份被本版替代，不单独重复跑。CPU流水行为未改不加ISA，本轮无动态仿真/PDS/板测或自动联系其他对话。新寄存器时序代价待确认，不能继承旧时序/功能PASS，KEY0问题及其他未覆盖保持。

## 2026-10-18：041 I/D缓存六项计数已接入，静态完成，等待用户PDS

按用户“添加上面这些性能计数器”实施最近确认的六项64位I requests/hits/misses与D read_requests/read_hits/read_misses，未同时加8项分支诊断。仅主桥、SoC、MMIO改变；CPU039保持5c26df02…0d47745，桥原功能体和旧13项时序块保持。I接受后下一沿按真实裁决分类，同行store毒化为miss，停放提升不重复；D只算可缓存DDR load，排除store/Camera/PP，写缓冲叠加命中一次。接受ROI跨沿追踪，冻结扩展等尾样本完整后才READY。

银行`0x10000200–22C`，元数据`0x10000120/124/128`；软件先原DONE再等124.bit3，读六项，命中率H/(H+M)，关闭或0分母=N/A。原13项与固定P/V BIN保持，旧BIN不会自动打印新计数。详见[接口合同](cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)及[EX阶段](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。

[静态收据](../sim/cpu_cache_perf/preparation_20261018_a/review.json)=TASK041_CACHE_COUNTERS_STATIC_ONLY_PENDING_USER_PDS；十种空目标展开通过、厂家内部黑盒，其余76项输入保持，尚无动态功能/时序/实板结论。当前SHA256：桥`0d6b131670b52749933e102b04b48a6f4750422c6279cd384451a673e3951f75`；MMIO`18cc48c4221c802ee21d49050a0695e1068f1dda26b6a83848b20334b67478e7`；SoC`a7333ac035e34afe37b51609c4da88e638cd9b91cece196622a959d327be5cc8`。

下一步用户根RISCV.pds重新实现检查时序；[041方案](../DeepSeek/任务041_ID缓存命中率计数与冻结读出.md)仅待时序通过草案，当前不开发/封存/执行动态测试，不自动调用DeepSeek。通过后相关单组验证含独立cache参考/ROI尾样本/原13项兼容、观察开关同刺激逐沿比较和独立诊断读出；CPU未改不跑ISA，不重跑039成功P/V。旧位流未获得新硬件，KEY0暖复位及历史未覆盖范围保持。

## 2026-10-18：用户关注I/D命中率，首批计数建议已明确，未实施

建议先加I requests/hits/misses与D read_requests/read_hits/read_misses六个64位计数。只计桥真实接受的可缓存DDR访问，D只算load，store与Camera/PP uncached另列；I停放miss提升不重复计数，x32查询在首次稳定有效裁决处分类，035同沿store毒化算miss；D缓存读叠加写缓冲前递仍只计一次命中。命中率按已分类hit/(hit+miss)，在途/取消/ROI边界余额要明确。现13项AR/AW不能准确推回两缓存命中率。[详细口径](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)已更新，未改RTL/BIN/寄存器或跑PDS/测试。原8项恢复诊断仍只是可选建议，不自动扩大实施范围。

## 2026-10-18：新增性能计数寄存器建议，未实施

用户询问更多性能统计。建议先在原13项之外扩8个64位观察计数：target_buffer_match、target_response_match（来源优先互斥）、old_i_block_branches、old_i_block_cycles、target_ready_wait_cycles、ex_branch_mem_wait_cycles、empty_serial_drain_cycles、other_with_retire_cycles。用于估计目标复用机会、单I槽/接受背压、更老MEM等待和OTHER正常退休交叉；事件/周期不可相加，OTHER减去退休也不是可删空转。详细合同在[EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。

原始观察包先寄存、后比较PC/追踪/累加，不反馈控制；redirect与旧pending/buffer需同源样本，ROI/尾样本与扩展READY对齐。原13项/七分类/UART格式保持，扩展MMIO偏移0x200–0x23F只是建议，诊断读出软件另封存，旧固定BIN不自动获得新输出。新增观察可能有时序代价，方案未实施，无RTL/BIN/测试/PDS/板测。

## 2026-10-18：040 fix02d核心归因原证据已核，完整证据缺项如实保留

17项封存/include与25条真实命令exit0已核；六例完整trace的退休PC/inst/we/next_pc及有效写回值、x31/mscratch通过离线核对。自行从phase0逐笔重建I事务账（399/392/399/385/399/384笔），地址/数据/单在途/接受响应丢弃守恒吻合。统一物理沿实测普通1/0/1/1，错路实际8沿响应使目标接受多等6沿，年轻CSR相同老MEM条件下多1沿buffer中转。OTHER短ROI含正常退休，不可全部删。[审查收据及重建账](../sim/cpu_ex_redirect/id_ex_attribution_20261018_a/review_20261018_03/review.json)仅接受核心归因，不标完整040/CPU/SoC/IRQ/复位验收。

剩余：phase1所谓old归属仍读NBA后新值，报告“冻结旧值”未实现；审查用完整phase0重建绕开错误字段。缺逐D地址/数据/strobe/实际延迟账及工具版本，commands只截末4000字符（VVP全日志另审）。本轮不为已独立闭合的核心五沿/I归属重跑整组，缺项保留，需相关完整验收时补。下一候选可评估目标PC匹配的已返回/buffer复用：fast redirect沿旧response已是target却被丢弃重取，有明确重复机会；不新增在途、不提前承诺性能。目前只评估，尚无RTL/HDL/PDS/串口或新任务派发。详情见[EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。

## 2026-10-18：040 fix01b改善已核，t3错位根因在TB跨进程cycle读写

已核17项封存哈希/include、6例日志及PC+inst前缀，实际错路慢响应差8沿、I/D汇总守恒和x31=0有证据。t3偏差已定位：模型posedge更新cycle，观察器另一个块在#1前后读到不同编号，同一物理沿phase1误记下一沿；oldpending/buffer亦读新值。fast实为8/9/9/10/11，slowwrong8/9/15/16/17，普通target接受→装入1沿→发射1沿。正确8沿错路模型阻挡target6沿；老MEM对照serial多1沿来自DRAIN撤销时buffer中转，不是所有分支代价。短ROI分类重算相符，OTHER含正常退休，不能全删。

完整040仍未接受：现参考只PC、runner非taken跳参考却置true，缺rd/value/next_pc及CSR副作用、完整逐事务/D字节/命令退出码，非taken未开ROI。详见[审查收据](../sim/cpu_ex_redirect/id_ex_attribution_20261018_a/review_20261018_02/review.json)与[同一阶段](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。[补正02](../DeepSeek/任务040_补正02_统一边沿号与补齐现有参考.md)只修已定位监视器/参考、同6例新封存重跑，不改RTL或扩矩阵；旧证据不改。本轮未执行HDL/PDS/串口或自动调用其他对话。

## 2026-10-18：040 run2局部机制有证据，完整归因未接受，需最小补正

Sol已审报告/TB/runner/5份原始轨迹与登记输入，CPU仍0395c26df02…0d47745。原日志支持错路pending推迟target7沿及无老等待ID→EX1沿；但t3检测沿前IF/ID已有值，实际fast五沿11/12/12/13/14（报告14为晚记），target接受→装入1沿、装入→发射1沿，不是“2拍装入结构下限”。slowwrong接受10/返回19实际9沿，不是参数名8沿；该错路请求在ID发射11之前已接受。报告不能据此承诺少发ID同沿请求会消除此例。

[审查收据](../sim/cpu_ex_redirect/id_ex_attribution_20261018_a/review_20261018_01/review.json)=PARTIAL_MECHANISM_SUPPORTED_NOT_ACCEPTED_REPAIR_REQUIRED。还缺封存副本编译/递归include最终清单、完整独立退休参考/x31污染检查、真实响应消费守恒、短ROI完整轨迹、串行变体/D守恒；reset采样race和runner失败传播需修。400沿统计主要是末尾自旋，不可外推CoreMark或OTHER全可删。已备[040补正要求](../DeepSeek/任务040_补正_五沿采样与输入封存.md)，仅原5短配置加1串行变体，DeepSeek修测试并新封存/新目录执行。旧结果保持，当前不改RTL/PDS/时钟、不重复板测/全套仿真。本轮仅原证据复核，无HDL执行。

## 2026-10-18：040动态归因要求已准备，DeepSeek实现/执行，当前未运行

用户明确进行下一步。已准备[任务040](../DeepSeek/任务040_ID到EX重定向与错路取指占用归因.md)：仅量化当前039 ID→EX推进和错路I单槽占用，四组短片段及独立参考/五沿配对/OTHER交叉统计，不改RTL、不重跑板测/PDS/ISA/完整039。当前CPU与冻结039一致5c26df02…0d47745，039原证据11项哈希保持；[输入要求收据](../sim/cpu_ex_redirect/id_ex_attribution_20261018_a/requirements_identity.json)已记录身份，尚非最终TB封存或执行结果。

现有普通bench一拍延迟名不符实际两沿可见，038 TR又把实时ID taken/target记在idex组且缺完整pending响应身份，不能直接用于本次量化。任务要求真实一拍、沿前/沿后分清、注册EX元数据与动态branch_id、错误路径延迟按静态地址注入、正常退休及取消守恒。DeepSeek按既定分工实现/封存/执行并交原始证据，Sol复核后决定下一RTL。本轮无动态量化结果，未编写新测试代码/运行HDL或自动向其他对话发消息；详细边界见[EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。

## 2026-10-18：ID→EX与错路占用静态检查完成，尚无新增RTL

按用户下一归因方向，复用039成功证据（11项哈希保持）并读CPU/计数器。taken/target随id_fire入EX，普通EX分支自身无访存/MUL等待，推进主要受更老MEM可用/故障资格限制，不能直接绕过。年轻ID串行/依赖不直接阻止EX推进；ID分支发射同沿仍可能接受顺序I，下一周期redirect虽清年轻ID/buffer，已接受错路请求必须等返回才能释放唯一I槽，039尚未消除这个机会。机制可达但未量化实际频次/代价。

OTHER是未落前六类的兜底，含正常执行/MUL等；branch恢复从EX redirect才开始、到目标进入IF/ID结束，ID→EX阶段可能落OTHER或被MEM/control覆盖。后续按分支PC/epoch测id_fire捕获taken→EX redirect→target fire→target入IF/ID→target id_fire，并记录老MEM、错路pending/返回、目标背压、WB退休，不能把OTHER或其增量直接当可删空转。详见[EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。本轮仅静态分析/记录，无RTL/仿真/PDS/板测或新任务派发。

## 2026-10-18：039原P/V应用实板通过，对EX基线快5.4%，对036仍慢6.1%

用户要求分析性能。本轮核`sim/cpu_ex_redirect/board/task039_target_fetch_300_01`两日志各123完整响应/唯一RUN/零重试、固定BIN与CRC5275/8803、完整UART/13计数/timer及分类守恒；11项身份与当前CPU5c26df02…0d47745/本地位流97e78672…31660a相同，板上内容未独立读取。[新收据](../sim/cpu_ex_redirect/board/review_task039_20261018_01/board_review.json)保存原日志哈希及对06:47 EX/036双比较。

039 P240456438cycles/2.564868672秒/CPI2.218400554；V240544610/2.565809173秒/CPI2.219757154。相对06:47 EX省13754444/13720402周期，耗时下降5.410643%/5.396103%；branch分类减少约1904万/1890万，MEM增加约519万/516万，退休/redirect/AR/AW/load-use/OTHER保持。相对036仍慢6.089010%/6.124319%；branch分类已接近036，OTHER仍多约1900万，不能直接统称空转。固定周期下打平频率约99.46/99.49MHz，非已验证工作点，不套用旧EX时序报告。

详细归因与边界见[同一EX阶段](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。本轮应用正常完成，不触发无结果时最小仿真定位；完整039动态/ISA/IRQ/复位仍未验收，KEY0问题保持。仅离线复核与记录，未改RTL/跑PDS/HDL/串口或重复P/V，未自动开启下一优化。

## 2026-10-18：用户调整039顺序，先固定P/V实板，无结果再最小仿真定位

用户最新明确“先上板看有没有跑分结果，没有就仿真找问题”，覆盖本轮此前先仿真再板测的等待顺序。按直接板试授权使用现有`run_ex_redirect_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_ex_redirect/board/task039_target_fetch_300_01`，固定P300/V300各一次、首败停止保留。用户下载当前新位流；本轮仅观察生成目录已更新至07:21:26、SHA `97e78672020abc2b1dfd8aca2243771a88af672f985a5afe310022446c31660a`，CPU仍039 `5c26df02…0d47745`，不例行核PDS或声明其时序/功能通过。PlanOnly保存在`sim/cpu_ex_redirect/board/task039_target_fetch_plan_01`，11项身份齐全、P/V各123应答/唯一RUN、串口未打开。每轮重新下载同一039位流、KEY0释放等DDR就绪后Enter，运行不复位。

收到实板日志先核协议/CRC/13计数，与06:47 EX修复基线比较；若没有完整跑分结果，保留首败按实际停点开展最小相关仿真定位，不延长超时或重复旧P/V。不自动启动完整039测试/ISA/物理DDR全套，也不把直接板试扩大为完整CPU/SoC/IRQ/复位验收。用户负责PDS/下载/KEY0/串口；本轮未实际操作板卡、仿真或PDS。

## 2026-10-18：039 EX重定向当拍目标取指已改，静态完成，等待用户PDS

用户指定EX阶段文档要求性能提升，本轮仅修改主CPU IF请求目标选择及PC推进：普通EX redirect当拍在I无在途或旧响应同拍完成时提交寄存目标；握手后PC=target+4，未接受则PC=target，旧响应含error丢弃。仍单在途，TRAP/MRET/更老故障优先、pending/drop/buffer和已修串行排空/退休逻辑保持。原BRANCH_FETCH_TURNOVER_ENABLE默认1重新实现实际功能，0保留06:47基线行为。CPU SHA从9eb80313…05093f变为 **5c26df0229ab00365b2eca1412499f988981fdfe1d1b7292e43a8317f0d47745**，其他77项输入保持。

[静态收据](../sim/cpu_ex_redirect/target_fetch_20261018_a/review.json)保留前后副本、清单和diff；五项空目标静态展开通过（board默认+CPU两参数四组合），厂家内部黑盒，未运行动态仿真/PDS/串口。边沿推导及范围见[EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。新路径使用ID/EX寄存目标，EX推进资格仍可能晚到，不能继承旧+0.797ns时序或承诺收益。旧位流不含本次修改，下一步用户根RISCV.pds重新实现；时序不通过先交回本项修复。

[任务039方案](../DeepSeek/任务039_EX重定向当拍目标取指.md)为PDS通过后待启动草案，当前不开发/封存/执行测试。新一组涵盖单在途接续/背压/丢弃/取消、串行排空、异常/IRQ/复位、最小ROM/DDR互连，以及种子2026101839抽出的lhu/sb；DeepSeek实现/执行，Sol审原证据。性能对照采用06:47成功EX P254210882/V254265012周期，不重跑基线P/V、不提前上板/提频或另起其他优化。当前仅STATIC_ONLY_PENDING_USER_PDS。

## 2026-10-18：EX修复版日志复用核对，下一建议为EX当拍提交目标取指

用户说明“ID判定、EX重定向已实现”并要求看日志/推荐下一步。本轮核06:47成功审查全部原证据哈希保持、当前CPU9eb80313…05093f未变；应用P/V通过但相对036耗时增加约12.2%。当前RTL在EX redirect当拍强制inst_req_valid=0，先更新PC、下一拍再发目标。建议保留寄存taken/target和EX重定向资格，只在I槽空或旧响应到达时恢复当拍目标提交，握手后PC=target+4，否则保留target；旧pending/drop/冲刷及串行排空修复保持。旧BRANCH_FETCH_TURNOVER_ENABLE目前不生效，不能仅改参数。

这可针对明确发射空档，避免立刻改变比较阶段/预测/频率；是否节省总周期及能否保持时序须新证据。下一单项以06:47 EX修复版作同配置对照，不将与036的混合差值全归一个改动。详见[同一EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。本轮只评估/记录，未改RTL、未派发或执行仿真/PDS/串口。

## 2026-10-18：06:47修复版P/V原证据通过，运行时间回退约12.2%

已离线逐项复核用户`sim/cpu_ex_redirect/board/serial_drain_fix_0647_300_01`：P/V各123条完整协议应答、唯一RUN、零重试，完整UART CRC分别5275/8803，timer与13计数/分类和/DDR AR+AW守恒通过；身份清单11项齐全，本地位流`6ddf1736…86056e`及CPU`9eb80313…05093f`与06:47检查一致。P254210882cycles/2.711582741秒，V254265012/2.712160128秒，均93.75MHz。本轮两次应用已正常完成，旧RUN后零RX症状未再出现；仅固定应用验收，不扩大为完整CPU/SoC/IRQ/复位PASS。小于10秒的duration ERROR和Errors detected是已冻结参考的预期文本，不是本轮CRC失败或正式CoreMark成绩。

相对036 P226655369/V226663043周期：P净增27555513（耗时+12.15745%，吞吐-10.83963%），V净增27601969（耗时+12.17753%，吞吐-10.85559%）。P分类差为branch_flush+19338474、OTHER+19093060、mem_stall-10796513、IF-81308、load_use+1800；V同趋势。退休数/重定向数/DDR写命令均相同，AR额外5076/5996，不能以丢请求换时序。分类差支持分支恢复相关代价是后续重点，但不单凭计数证明每次分支具体气泡数；OTHER不能统称空转。

按本轮周期需105.148/105.166MHz才与036耗时打平；即假设能跑报告估计101.3211MHz仍慢3.78%/3.80%，该估计不是可用DDR时钟方案。结论为时序改善但应用性能回退，不推荐直接靠提频宣称获益。比较含EX CPU+037互连对036，缺独立037板测，不能把全部差值严格归因一个修改。下一评估优先检查EX重定向到目标有效指令的恢复空拍；本轮未开始RTL优化/仿真/PDS/串口或重复P/V。正式[复核收据与对比](../sim/cpu_ex_redirect/board/review_serial_drain_fix_20261018_01/board_review.json)及解码UART已保存。

## 2026-10-18：06:47新位流已包含串行排空修复来源，时序+0.797ns，板测待验

用户要求检查新位流。本轮观察CPU已由其他工作更新至提交`ce11dfe`，SHA `9eb803138292427293db785e27eeff9f15295622a95514e695f017cca505093f`：FLOW_RUN进入串行排空时增加`!redirect_valid`，FLOW_SERIAL_DRAIN在`!serial_candidate`时回RUN。源码06:33、综合06:38、布局06:45、报告06:46、位流06:47的生成链及已变化的EX布局网表支持本次实现来自修复版；未独立重建/解码位流。`generate_bitstream/board_top.sbit`06:47:08生成、9188552字节、SHA `6ddf1736f33b506ee844faae5f11c9d9360e81e98c645919acf4fd15d186056e`，生成日志完成。报告06:46:22为All Constraints Met，93.75MHz、WNS+0.797ns/TNS0、估计Fmax101.3211MHz，比上版余量增加0.188ns，未提频。[本轮收据](../sim/cpu_ex_redirect/board_review_20261018_c/review.json)保存证据和边界。

最差core路径为EX src2经地址/Camera控制到frame_crc32 CE，10级、逻辑1.845ns/布线7.449ns；不是新增优化授权。已看到任务038定位/修复报告，但本次位流检查未独立完成全冻结输入/轨迹验收，不能直接扩大为完整功能PASS；修复版板测尚无结果。旧03:59/06:15失败属于旧身份，保留原结论。本轮无RTL修改/HDL/PDS/串口操作。

## 2026-10-18：06:15新位流再次P300零RX，传输通过，停止重复板测

用户交回`new_bit_0615_300_01`失败。已逐条解码123RVLD应答并核发送/接收/CRC/唯一RUN，15204字节装载与VERIFY CRC3569018250正确，零重试；RUN应答后40.049121秒应用RX=0，V未开始。原日志本地位流哈希为06:15版`2ad9a50b…7afcf4b`，不能独立证明板上编程内容。[失败复核](../sim/cpu_ex_redirect/board/failure_review_20261018_02/failure_review.json)保持原证据，结论为传输成功、应用失败，无应用CRC/性能成绩。与首败症状一致；当前CPU仍`ef6bfec7…cc87e6`，串行排空为待动态证明的首选疑点，继续[任务038](../DeepSeek/任务038_EX重定向冲刷串行排空与RUN零输出定位.md)，不延长超时/重复P/V/追加优化。

同时发现现有`run_ex_redirect_measurement.py`的ROOT多向上一层，令附加`identity.json`哈希清单为空。已仅修该元数据路径及缺失输入显式拒收，原失败清单不倒填；实际应用日志独立记录的本地位流/BIN身份与123原始应答仍可核。修复后仅PlanOnly验证于`sim/cpu_ex_redirect/board/identity_root_fix_plan_01`，11项身份齐全、P/V各123响应/唯一RUN、串口未打开。未改设计RTL、超时/传输/验收口径，未运行HDL/PDS/板测，不把工具修复解释为CPU故障修复。

## 2026-10-18：新增06:15 EX位流已核，时序通过，原应用失败未解决

用户要求查看新增位流。本轮只读检查现有PDS产物并封存[复核收据](../sim/cpu_ex_redirect/board_review_20261018_b/review.json)：`generate_bitstream/board_top.sbit`于06:15:22生成，9188552字节，SHA256 `2ad9a50bcd7ec04afe0c26e64474e638c62b73d61f34ba80482f650427afcf4b`。生成日志完成，06:14:38时序报告All Constraints Met，core仍93.75MHz，WNS+0.609ns/TNS0，估计Fmax99.4270MHz。当前CPU为最新EX候选`ef6bfec7…cc87e6`，新综合/布局网表含EX分支寄存器；布局网表SHA与03:59封存版完全相同。新位流文件变化不代表逻辑修复，原RUN后零RX失败及串行排空疑点保持；未独立解码初始化位，无新仿真/板测/PDS执行。原reviewed板测入口固定旧位流身份，本次未更改该工具或授权重复P/V。

## 2026-10-18：用户要求用最新CPU，工作树已恢复EX重定向版本

用户明确“用最新的”。本轮仅将`myriscv/mycpu_sync.v`工作树恢复为Git HEAD `ed52ef6`中的最新EX候选，SHA **`ef6bfec7853f6b0e93f976c7038ad25cdb4f6e04b14251331fdbf79906cc87e6`**，与已封存03:59候选CPU逐字节一致，PDS现在读取该EX源码。原ID文件与暂存差异已保存于[恢复收据目录](../sim/cpu_ex_redirect/source_restore_20261018_a/restore.json)，其他39个myriscv文件保持；未改用户Git暂存区，旧ID回退仍在index，不能把后续仅提交暂存区误作已提交本次恢复。

这是版本选择，不是修复：恢复的正是已有零输出失败位流对应的同一候选，串行排空静态缺陷及任务038继续待最小复现；重新生成同版不能自动记为故障解决。没有新RTL逻辑改造、仿真/PDS/下载/串口或提交推送，不重复P/V。下文“工作树是旧ID”的描述是恢复前观察，原日志/收据/位流不改写。

## 2026-10-18：EX P300装载/VERIFY/RUN应答通过，随后40秒零应用RX，先定位串行排空

用户交回EX板测失败。原P日志123完整RVLD响应/唯一RUN/零重试、DDR VERIFY CRC3569018250全部逐字节核过；RUN_ACK后40.04654949999531秒应用RX0byte、V未开始。[失败收据](../sim/cpu_ex_redirect/board/failure_review_20261018_01/failure_review.json)=`EX_P300_TRANSPORT_LOAD_VERIFY_RUN_RAW_PASS_APPLICATION_ZERO_RX_TIMEOUT_V_NOT_STARTED`。不能证明CPU已跳入DDR，更不能记CRC/性能PASS或把40秒解释为通常的分支多一拍耗时。保留原目录与封存EX位流，不延时、不重复P/V。

冻结EX CPU发现首选静态缺陷：EX跳转清年轻ID的CSR/FENCE，却未取消它同沿或更早启动的FLOW_SERIAL_DRAIN；之后serial_candidate消失，serial_issue永远不成立，frontend_hold可锁住目标取指。固定P300的0x40000120 JALR紧随0x40000124 CSRW MEPC具备触发形态，但尚无板上PC/第一分歧证据，根因未最终证明。原隔离TB的I侧两拍可见返回也未证明该同沿重叠。

[任务038](../DeepSeek/任务038_EX重定向冲刷串行排空与RUN零输出定位.md)已写冻结EX/旧ID身份、一拍命中与CSR/FENCE、排空同沿/提前进入、具体程序片段及逐沿独立参考要求，交DeepSeek实现/封存/执行最小定位；不会自动调用。只修FLOW_RUN入口不覆盖已进入排空情况，后续修复须取消年轻排空且保留老异常/IRQ语义。详见[同一EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)。本轮未改RTL/工作树回退/固定BIN，未运行HDL/PDS/串口，未准备重试命令或其他优化。

## 2026-10-18：用户EX候选位流上板前复核完成，源码已回ID，按封存位流直接板试

用户表示已完成ID判定/EX重定向，要求核位流/时序并上板。核现有03:58:14报告All Constraints Met，主域仍93.75MHz、WNS+0.609ns/TNS0/0失败端点，估计Fmax99.4270MHz；位流03:59:16生成9188552byte/SHA`0e15e517…b2b9d94`，生成日志完成，综合/布局网表均有id_ex_br_taken/target。**但工作树与暂存CPU已回ID版本b1114fa3…a41d3，HEAD的EX候选ef6bfec7…c87e6与之不同。** 未恢复/覆盖源码或改Git暂存，按现有实现产物识别EX并封存同字节位流，身份观察不等于独立重建实现或板上证明。

用户下载[封存EX位流](../sim/cpu_ex_redirect/board_review_20261018_a/observed/generate_bitstream/board_top.sbit)，随后：

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_ex_redirect_reviewed_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_ex_redirect/board/ex_redirect_reviewed_300_01
```

P/V每轮先JTAG重新下载同一封存位流，关闭串口助手、KEY0释放/等DDR就绪/Enter；固定P300/V300不重建，各一次/首败停止。新入口区分实现EX与当前源码回退，避免原EX工具按当前源码记录错归属；离线计划各123应答/唯一RUN、解析/比较/错误身份拒收通过，serial_opened=false。[复核收据](../sim/cpu_ex_redirect/board_review_20261018_a/review.json)、[准备收据](../sim/cpu_ex_redirect/board_review_20261018_a/ready.json)及[同一EX阶段顶部](cpu/ID判定EX重定向实现与指令集回归_2026-10-18.md)保存完整身份/边界。

成功对照为036 P2.417657269/V2.417739125秒；EX实现还含037数据互连，无独立037板测，不能分离全部性能归因。实际时钟未提高，新功能/性能待板测，完整CPU/SoC/ISA/IRQ/复位未独立核，KEY0问题保持。本轮未运行RTL仿真/PDS/下载/串口，用户负责板级操作，不重复历史P/V或另起优化。

## 2026-10-18：流水架构改造建议为真EX分支＋EX前递，仅评估未实施

用户询问“如果要改流水线架构推荐怎么改”。结合当前RTL，建议目标保持单发射顺序五级：ID轻译码/读寄存器，EX作最终前递/分支比较与目标计算；load只在返回结果寄存后供依赖使用，redirect作为仅发一次的寄存事件由IF消费；后续再单独评估MEM从寄存地址发总线请求及前端局部valid/ready。EX分支必须同步改源寄存器/原始rs2元数据、互锁、精确冲刷/更老异常优先、next_pc/目标错位/IRQ和store副作用，不能只延迟taken。当前最小桥CE候选与上述架构方案均未实施。

按036实测redirect量，每redirect净增1拍的无重叠敏感度约+8.4%cycles，2拍约+16.8%，非预测或上界；需以实际C/f比较，当前估计Fmax95.91MHz不证明架构收益，更不承诺109.375/125MHz。详细职责、边界及分步建议已加入[同一阶段](cpu/MINI_数据互连并行译码与ready_2026-10-18.md)顶部。本轮只读评估/文档，无RTL、测试、PDS或串口操作，未启动038；037功能/实板与KEY0问题边界保持。

## 2026-10-18：037时序报告已满足约束，WNS+0.240ns，最长链转为load返回到独立I字段CE

用户要求查看日志分析最长路径，本轮仅只读核报告/源码并记录。最新02:49:50报告All Constraints Met，93.75MHz slow WNS+0.240ns/TNS0/0失败端点，估计Fmax95.9081MHz；较改前+0.115ns增加0.125ns，尚未提频或实测加速。当前源码/IP/BIN与037静态身份保持，仅PDS/报告更新；[观察收据](../sim/cpu_data_decode/timing_review_20261018_a/review.json)保存原report/run.log/PDS及身份，不独立重建实现输入。

所列最差三条均为data_q[21]→数据响应mux→load字节选择/MEM前递→ID分支比较/异常/取指接受→take_inst_overlap→独立I store标记CE（+0.240ns）与地址[2]/[10] CE（各+0.255ns）。17级，最差数据路径9.985ns=逻辑3.501ns+布线6.484ns（64.937%）。旧EX数据地址译码路径不再列主域前三，不能据此说全部消失。完整分段与候选见[037阶段顶部](cpu/MINI_数据互连并行译码与ready_2026-10-18.md)。

下一最小候选仅建议评估独立I addr/store payload随inst_tag_sample预采、pending保持真实接受，须保证停放miss保持与旧hit同沿消费，不加拍；本轮未实施/未启动038。037动态/板测仍待验证，036应用PASS及KEY0问题边界保持。只分析未改RTL，不运行仿真/PDS/串口，不派发DeepSeek或重复历史测量。

## 2026-10-18：036日志已核，037优化最差两条共用数据译码段，待用户PDS

用户要求先看日志再优化最差路径。036两份原始P/V各123完整RVLD响应/唯一RUN/零重试、固定BIN/CRC5275和8803、完整UART/timer/13计数/分类与DDR守恒全部通过，[实板收据](../sim/cpu_request_presample/board/review_20261018_01/board_review.json)=`TASK036_FIXED_P300_V300_APPLICATION_BOARD_RAW_PASS_HDL_NOT_RUN`。P226655369cycles/2.417657269秒，V226663043cycles/2.417739125秒；较035仅−3645/−1317cycles（耗时−0.001608%/−0.000581%），退休/branch/AR/AW保持，不据单轮微小差异认定提速。完整动态及KEY0边界保持，详见[036阶段顶部](cpu/MINI_桥请求字段预采样_2026-10-18.md)。

最新02:07:14报告All Constraints Met，93.75MHz slow WNS+0.115ns/TNS0，估计Fmax94.7718MHz。最差两条为EX src2→ALU→数据地址→数据互连译码/ready→分支取指接受→指令互连response_target CE（+0.115ns）/CPU inst_pending_pc CE（+0.173ns）；第三条为数据地址动态tag选择/写失效→I tag CE（+0.231ns）。本轮先单独处理前两条共用数据译码段，第三条保持待新PDS评估，不同时改桥或CPU。

仅改主`data_bus_interconnect.v`：并行raw译码，以mask/base常量证明不重叠后删除无效优先排斥，特殊参数重叠仍保原顺序；互斥selected的ready改为并行not-ready归约。权限/排空/响应/真实接受/寄存器及拍数不变，CPU/036桥/IP/PDS/FDC/93.75MHz/成功BIN保持。最终数据互连SHA **e1aca083d8343fb454575052bdd3134730a803e803497fa387b9bbda4a0aa847**；[静态收据](../sim/cpu_data_decode/preparation_20261018_a/review.json)=`TASK037_DATA_DECODE_STATIC_ONLY_PENDING_USER_PDS`，77项输入仅该文件变化，八配置null-target展开通过，完整边沿论证/相关验证边界见[037阶段](cpu/MINI_数据互连并行译码与ready_2026-10-18.md)。

**下一步用户保持93.75MHz重新综合/映射/布局布线并回传时序。** 当前+0.115ns属于037改前，不能预填新改善；未运行或派发037动态仿真/PDS/串口，不重复036成功P/V，不自动提频。时序通过后再由DeepSeek按相关方案实现/执行单组关键测试，CPU未改不例行ISA；板测或完整功能未完成均不记PASS。

## 2026-10-18：用户要求036直接上板，固定P/V专用入口已准备

用户在局部修复后明确“上板吧”，本次按直接板试指令准备工具，不再等待或例行核PDS/位流；不宣称修复后时序通过或动态豁免。当前桥仍`4d628cfa…21db589`，soc_top/ROM适配器/固定P300/V300保持。新增[036双轮入口](../tools/uart_loader/candidates/perf_2b/run_task036_measurements.ps1)，非PDS输入/BIN/035基线原证据核过，PlanOnly各123响应/唯一RUN、serial_opened=false，[准备收据](../sim/cpu_request_presample/board_tool_preparation_20261018_a/ready.json)。

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_task036_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_request_presample/board/task036_300_01
```

P/V每轮都按提示先重新下载同一个**最终036冲突CE修复版位流、保持93.75MHz**，关闭串口助手、KEY0释放/等DDR就绪/Enter；用户负责PDS/下载/KEY0/串口。首败保留，不自动重试。工具核固定BIN/CRC5275和8803/13计数，输出VS035；比较基线P226659014cycles/2.417696149秒、V226664360cycles/2.417753173秒。详见[同一036阶段顶部](cpu/MINI_桥请求字段预采样_2026-10-18.md)。

本轮未改RTL/运行HDL/PDS/串口，没有036板测结果；修复后新时序未核、完整握手/冲突/复位动态NOT_RUN、KEY0问题均保留。成功P/V亦不扩大为这些范围PASS。频率未变，036预采样本身不预期减少周期；不足10秒仅工程比较，不重跑035成功基线或自动开展其他优化。

## 2026-10-18：036初版setup违例，已局部预采冲突向量，待用户重新PDS

用户报告违例，核最新01:43:54报告：93.75MHz主域slow WNS−0.034ns/TNS−0.045ns/2端点，终点为`inst_overlap_line_match_q[0]/CE`、`[5]/CE`，最差`if_id_inst[17]→操作数选择→分支/异常→取指接受→take_inst_overlap→冲突向量CE`，13级、布线74.560%。初版036未闭合，不记时序改善/提频成功。

仅将该向量CE从实际独立I接受改为已有`inst_tag_sample`，匹配表达式保持；实际接受必在该采样窗口，pending miss关闭窗口保持向量，旧hit同沿消费旧值，新样本只有原pending/地址/store实际接受后才有归属。不新增拍数，不改主三字段036采样、CPU/034快ACK/load寄存/035优先与冲突/时钟/IP/PDS/FDC/BIN。

当前桥SHA **4d628cfa4e9f68e18671b1e42399ceaddcb2ddabeca3d9b505e5d632821db589**；[静态收据](../sim/cpu_request_presample/timing_repair_20261018_a/review.json)为`TASK036_CONFLICT_CE_STATIC_REPAIR_PENDING_USER_PDS`，九配置null-target展开通过，76输入中其余75保持。仅新增保存失败报告、桥/PDS变化，未变输入复用；完整边沿证明/身份/后续最小验证补充见[同一036阶段顶部](cpu/MINI_桥请求字段预采样_2026-10-18.md)。未运行或派发动态仿真/PDS/串口，未重复035 P/V。

**下一步用户保持93.75MHz重新综合/映射/布局布线并回传新时序。** −0.034ns属于修复前，修复效果待新报告；未通过前不派发DeepSeek。035完整握手/冲突/复位与KEY0暖复位未解决边界保持，不自动提频或另起优化。

## 2026-10-18：036桥请求字段预采样已静态完成，待用户PDS核时序

用户授权接续035，仅改主DDR桥`request_ctrl_addr/request_lane/request_line_tag`：主槽IDLE/RSP/寄存I命中LOOKUP时预采，D真实接受→停放I提升→当前I地址；字段CE不再依赖`take_inst_front`或live I valid。事务状态/响应归属仍由原真实接受/提升更新，等待AR/R/非posted AW/W保持旧字段，旧响应同沿消费旧值，不新增拍数。035同行store冲突/停放/单DDR读、034快ACK及load寄存、CPU/IP/PDS/FDC/93.75MHz/固定BIN均保持。

036桥SHA **34e9fa3851163c4912f0a9fbed65ae73b8494638c5dfa788fd540b291f4c7fe2**；[静态收据](../sim/cpu_request_presample/preparation_20261018_a/review.json)为`TASK036_STATIC_ONLY_PENDING_USER_PDS`，76项改前输入仅桥变化，其余75项保持。九配置null-target展开exit0，厂商内部IP黑盒；剔除三个字段赋值和新增块后其余RTL文本相同。边沿证明、输入/检查及待时序后的单组关键验证草案见[036阶段](cpu/MINI_桥请求字段预采样_2026-10-18.md)。没有派发DeepSeek执行任务、运行动态仿真/PDS/串口或重复035成功P/V。

**下一步用户保持现93.75MHz重新PDS实现，回传本版时序。** 改前+0.151ns不代表036通过；收益尚未知。时序通过后才由DeepSeek实现并执行相关关键组，需独立参考和一次035/036同刺激逐沿/总周期对照；不能用少接受/丢请求换时序。频率不变只记时序改善，具体提频须另核DDR/IP/core_clk及UART/计时/LED等参数，不承诺109.375/125MHz。035 P226659014/V226664360cycles仍作成功应用比较基线，完整握手/冲突/复位NOT_RUN和KEY0暖复位未解决边界保持。

## 2026-10-18：035最终版固定P/V实板已核，应用功能通过，性能较034小幅提升

用户要求查看日志。核`sim/cpu_dual_read/board/task035_300_01/`两日志各123RVLD完整响应/唯一RUN/零重试、冻结BIN与CRC5275/8803、完整UART/13计数/timer及分类守恒通过；现035输入和034基线保持。[收据](../sim/cpu_dual_read/board/review_20261018_01/board_review.json)=`TASK035_FIXED_P300_V300_APPLICATION_BOARD_RAW_PASS_HDL_NOT_RUN`。P226659014cycles/2.417696149秒/CPI2.091108420；V226664360cycles/2.417753173秒/CPI2.091669544。较034耗时减少0.288840%/0.332601%，净省656579/756403周期，作为当前同集成比较基线。

IF/branch分类合计减少约362万/371万周期，但MEM增加约296万，抵消80%–82%；退休/branch次数/AW/load-use/OTHER不变，AR各多1，MEM仍约31.8%。这是并行接受＋两次时序修复最终组合版的小幅单轮工程收益，不是每项独立收益或正式CoreMark成绩。035完整RTL握手/冲突/复位动态验收仍NOT_RUN，KEY0问题仍未解决，不扩大应用CRC验收范围。详见[同一阶段](cpu/MINI_I查询与D请求同拍接受_2026-10-17.md)；本轮仅离线复核与记录，无RTL/HDL/PDS/串口操作，不重复成功测量、不自动开启036。

## 2026-10-18：按用户035功能/实际性能验收要求，固定P/V应用功能与板测入口就绪

用户明确“验收035的功能和实际性能，给上板命令”。本轮准备035专用**应用功能CRC/协议与实际DDR性能**入口，绑定最新返回数据修复SoC `cd3d820aee9ad2572e52972ba4f8942221054d42ea7457e87f7517a90322232b`、035桥`1abf54fe…52afe67`、ROM适配器`fa4ac709…456b7d`。73项最新静态清单只有已记录的PDS/时序报告变化；工具不以PDS/FDC/位流哈希作板测门，不调用旧034硬件输入门。本次是用户对035的新板测指令，不沿用034单轮授权宣称035动态豁免或功能PASS。

新增[035双轮入口](../tools/uart_loader/candidates/perf_2b/run_task035_measurements.ps1)及Python入口；固定P300/V300各123响应/唯一RUN计划、解析/对比离线检查通过，未开串口，[准备收据](../sim/cpu_dual_read/board_tool_preparation_20261018_a/ready.json)。日志明确035完整RTL握手/冲突/复位动态验收NOT_RUN；本命令的功能范围为实际程序CRC、装载/VERIFY/RUN、完整输出和13计数，不扩大为全部035定向功能通过。用户执行：

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_task035_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_dual_read/board/task035_300_01
```

P/V每轮提示时都先JTAG重新下载同一个**最终035位流**，再关闭串口助手、KEY0释放/等DDR就绪/Enter，避免将未定位的KEY0恢复问题当作已修复。固定BIN不重建；新目录保护、首败保存、不自动重试。工具每轮打印VS034周期差/耗时变化/吞吐变化；034基线P227315593cycles/2.424699659秒、V227420763cycles/2.425821472秒。性能与应用功能均待新实板日志，动态完整协议/复位验收仍待单独证据。详见[同一035阶段](cpu/MINI_I查询与D请求同拍接受_2026-10-17.md)，本轮未改RTL/运行HDL/PDS/串口。

## 2026-10-18：最新报告All Constraints Met，93.75MHz WNS+0.151ns，035功能仍待验收

核用户“四刀＋load前递后移”方案时发现最新报告内时间10-18 00:48:20，全部约束满足；主域slow setup WNS+0.151ns/TNS0/0失败端点，估计Fmax95.0963MHz，旧−0.116ns已非最新。副本及当前源码观察身份见[报告收据](../sim/cpu_dual_read/timing_review_20261018_a/review.json)，不等于独立重建实现输入或板上功能验收。最差已由类型位rdata路径转为EX源操作数→桥地址/标签CE。

本轮仅核方案：D的输出mux上一轮已移除；br_alu已并行表达六种比较，perf已有一级采样。接受预判寄存不能默认零气泡，3.6% load-use分类不能当延后load前递的最坏代价；各项预估ns不能相加或据此保证109.375/125MHz。详见[同一035阶段顶部](cpu/MINI_I查询与D请求同拍接受_2026-10-17.md)。未新增RTL/测试/时钟修改或启动PDS/HDL/串口；建议先完成本版功能与性能验收，再单项提频研究。

## 2026-10-18：035返回数据mux修复已完成，保留ID分支，待重新PDS

用户确认先做局部修复。本轮仅改soc_top：接受快速posted store时在边沿清data_q，其他原桥响应按原边沿捕获，返回数据直接接data_q；移除类型寄存位驱动的输出数据mux。旧load响应与新store同沿时先消费旧值再沿后清0，valid/error/ACK周期及写排空保持，无新流水级，CPU/035桥/前次ROM适配器/IP/PDS/FDC/BIN均不改。新soc_top SHA **cd3d820aee9ad2572e52972ba4f8942221054d42ea7457e87f7517a90322232b**。

[静态收据](../sim/cpu_dual_read/rdata_timing_repair_20261018_a/review.json)保存73项改前输入/旧−0.116ns报告，除soc_top外72项保持；七配置语法展开通过，厂家内部IP黑盒，未动态仿真/PDS/串口。详细边沿审查与后续最小验证见[同一035阶段顶部](cpu/MINI_I查询与D请求同拍接受_2026-10-17.md)。**下一步用户重新综合/映射/布局布线检查时序**，不能预填PASS；类型位仍参与valid/error，其他长路径可能继续出现。本次不是EX分支改造，也不另起性能阶段；后续功能输入必须绑定新SoC与现035桥/ROM修复身份。

## 2026-10-18：用户讨论EX跳转，建议先局部修复响应数据mux，尚未改RTL

当前最新时序报告为10-17 15:10:56：主域slow WNS−0.116ns/TNS−2.270ns/38端点，最差为034响应类型寄存位→数据mux/load前递→ID分支→取指译码→桥地址CE，不能继承下方旧报告结论。用户提出ID/EX寄存后EX跳转，本轮只评估两类实现及分支气泡代价；建议先将store返回0改为接受边沿清data_q、输出直接接寄存data_q，以移除当前输出mux，保留ID分支/034快ACK/load寄存。该候选未实施，不能记时序修复完成。EX分支需配套前递、冲刷、精确异常/next_pc及停顿控制，不能只延迟跳转信号。完整分析见[同一035阶段顶部](cpu/MINI_I查询与D请求同拍接受_2026-10-17.md)，本轮无RTL/仿真/PDS/串口操作。

## 2026-10-17：035时序修复已改指令ROM地址选择，待用户重新PDS

用户报告违例。已核最新14:45:57报告：ddrphy_sysclk slow setup WNS−0.067ns/TNS−0.263ns/6端点；最差为CPU CSR合法性→WB前递→ID分支→ROM译码→地址mux→ROM地址，20级、布线70.24%，非035同行冲突寄存器本身的直接路径。失败报告/72项输入保存在`sim/cpu_dual_read/timing_repair_20261017_a/before/`。

只改`myriscv/inst_bram_adapter.v`：零附加响应延迟时ROM地址直连当前请求；延迟配置仅在pending且响应未到期时保持已接受地址。同步ROM在消费旧响应边沿可采下一地址，无新接受时采样结果没有响应token；req/response握手、周期及权限不改，不改CPU/CSR/IP/FDC/频率、不加拍。adapter最终SHA **fa4ac709ef35b606f02f17b96383f5f0c0f09bd76bba1af8065343e2e9456b7d**；035桥仍1abf54fe…52afe67、034 soc_top仍7e43a9d5…64c2d04。六配置静态展开通过，[最终收据](../sim/cpu_dual_read/timing_repair_20261017_a/final_review.json)，细节见[同一035阶段](cpu/MINI_I查询与D请求同拍接受_2026-10-17.md)顶部。

**待用户重新综合/映射/布局布线核新时序**，未运行仿真/PDS/串口，不能提前写时序PASS。时序通过后的035关键组需包含ROM同拍接续/无新请求、延迟保持、地址毒化/重定向/复位；CPU未改不例行ISA。原035静态清单仅覆盖旧adapter，后续须绑定本次final清单，不能用旧输入门放行新设计。

## 2026-10-17：035 I查询与D请求同拍接受RTL完成，同行store强制I miss，待PDS时序

用户要求下一步性能提升。本轮仅改主DDR桥，新增默认开启`INST_WITH_DATA_REQ_ENABLE`：x32/I缓存开启时，在主槽接受D请求的同一沿可接受I查询进入033独立槽；D持有主字段，I miss停放后提升，物理DDR仍单读。覆盖store时将完整行地址逐位匹配先寄存后归约，同拍同行store强制I查询miss，保留写排空后重读；异行I hit可和034快速store ACK并行返回。CPU/034 soc_top/load寄存/IP/PDS/FDC/固定BIN未改。

最终桥SHA **1abf54fe01fb76659943fd14818154cfffe1bde23cd9f996b711b185452afe67**；[最终静态收据](../sim/cpu_dual_read/preparation_20261017_a/final_review.json)与final_after_manifest/final_bridge.patch为有效身份。71输入除桥外70项保持，九配置null-target语法展开通过，厂家内部IP黑盒。仅并行D读的中间版本及第一次收据保留但已被最终版本替代：load额外寄存可能掩盖其收益，因此最终补齐store冲突处理，不能只以桥吞吐判断CPU提速。见[035阶段](cpu/MINI_I查询与D请求同拍接受_2026-10-17.md)。

**下一步用户重新PDS实现核最终035时序**，有违例回本对话修复。尚未运行/派发动态仿真、PDS或串口，没有功能/性能PASS，不使用旧034工具门部署035。时序后关键组须核双接受、store同行/异行失效、miss归属、旧写完成接续、复位及真实CPU净省拍；034单轮直接板试授权不自动扩大为035流程。当前比较基线为034 P2.424699659/V2.425821472秒；实测收益未知，KEY0问题保持。

## 2026-10-17：034固定P/V实板已核，较033快0.249%/0.227%，无动态仿真验收

用户要求性能分析。离线核`sim/cpu_store_ack/board/coremark_store_ack_300_01/`成功P/V：各123RVLD响应/单RUN/零重试、同固定BIN、CRC5275/8803、完整UART和13计数/timer守恒通过。[034合并收据](../sim/cpu_store_ack/board/review_20261017_01/board_review.json)=`TASK034_FIXED_P300_V300_BOARD_RAW_PASS_HDL_NOT_RUN`。P227315593cycles/2.424699659秒/CPI2.097166，V227420763cycles/2.425821472秒/CPI2.098650；相对同集成033少567353/516747周期，耗时缩短0.248967%/0.226706%，仅工程单轮比较，不作正式成绩或显著性断言。

MEM分类减少4260288/4255301，但IF增加2540641/2596943、branch恢复增加1152294/1141611，抵消约87%；instret/branch次数/AW/load-use/OTHER不变，AR各少1。当前MEM约30.4%，IF约1.9%，branch约10%；不能把分类变化当已证明的具体延迟根因。下一候选静态评估普通I/D hit串行争用，033仅在D miss时允许额外I查询；未实施035或派发测试。详情见[034阶段](cpu/MINI_posted_store确认分路_2026-10-17.md)。

本轮未改RTL/开串口/运行HDL/PDS，不重复成功P/V；用户直接板试安排下034动态功能仿真仍NOT_RUN，KEY0恢复问题仍未定位，不能由本次每轮重配置成功扩大验收范围。下文上板待结果为历史状态。

## 2026-10-17：用户报告034时序通过并要求直接上板，专用直接板试入口就绪

用户最新明确“时序通过，直接给上板命令”，本次按该直接板试指令执行，覆盖本轮此前“必须动态仿真复核后才给入口”的安排；不再追问确认，也不虚构034动态功能PASS。soc_top仍`7e43a9d55c04db6372bd906b7e244debd544ae840681146842440d50764c2d04`，桥仍033的7ab9d34c…52d933，未改设计/成功BIN。新增[034双轮入口](../tools/uart_loader/candidates/perf_2b/run_posted_store_ack_measurements.ps1)与Python入口，绑定034静态输入身份及同集成033实板基线，日志明确`dynamic_functional_simulation=NOT_RUN`、用户直接授权/用户报告时序通过，未调用旧033硬件功能门或创建034功能PASS门。

两份离线计划各123响应/单RUN核过、未开串口；工具收据`sim/cpu_store_ack/board_tool_preparation_20261017_a/ready.json`。当前不是034功能/实板验收通过，仅可由用户按授权直接板试：

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_posted_store_ack_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_store_ack/board/coremark_store_ack_300_01
```

沿固定P300/V300各一次，不重建BIN。因既有KEY0后Loader无响应问题未定位，P、V每轮在工具提示时都先JTAG重新下载同一个034位流，再KEY0释放/等DDR就绪/Enter；不自动重试，首败保存新日志。用户负责PDS/位流下载/KEY0/串口，Codex本轮未操作；不要求PDS报告/位流哈希作为入口门。性能对照033 P2.430751424/V2.431333440秒；正文及限制见[034阶段](cpu/MINI_posted_store确认分路_2026-10-17.md)。下文待PDS/待仿真的步骤为本次用户直接指令前状态。

## 2026-10-17：034 posted store确认分路RTL完成，保留load响应寄存，待用户PDS时序

用户在033性能分析后要求“执行下一步”。本对话仅改主soc_top：新增默认开启`DDR_POSTED_STORE_ACK_BYPASS_ENABLE`，Camera+x32+posted条件下，在桥实际D请求接受边沿锁读写类型，posted store ACK绕过额外响应寄存；load的valid/data/error仍整体寄存，快ACK不进入延迟valid以防重复。同拍旧响应/新请求使用旧归属，写缓冲排空、桥033/CPU/IP/PDS/FDC/成功BIN均保持。

soc_top SHA047cf3cc…6821a→**7e43a9d55c04db6372bd906b7e244debd544ae840681146842440d50764c2d04**；[034静态收据](../sim/cpu_store_ack/preparation_20261017_a/review.json)保存71项输入，除soc_top外70项保持。七配置null-target语法展开通过，厂家内部IP黑盒，不是功能/时序验收。设计、逐边沿审查及待时序后的关键组要求见[034阶段](cpu/MINI_posted_store确认分路_2026-10-17.md)。没有运行或派发动态仿真、PDS、下载或串口。

**下一步用户重新综合/映射/布局布线检查034时序，暂不直接下载跑分。** 违例先回本对话修复，时序通过后Sol准备执行方案、DeepSeek实现并执行一组相关测试，Codex核原证据后再给实板入口。同集成性能对照使用已核033的P2.430751424/V2.431333440秒；预计每store少一拍只是机制与量级估算，实际收益未知，不继承旧PASS。KEY0恢复问题保持未定位，不宣称本次修复。

## 2026-10-17：033 P/V固定BIN实板原证据已核通过，较历史032慢8.39%/8.51%，KEY0恢复问题仍保留

用户随后要求分析性能：只读核成功P/V与soc_top身份保持，补充当前MEM约32.2%、IF约0.76%；033只覆盖D读miss期间I查询，不能加速全部D hit/store确认。若每笔DDR写净少1拍且其他条件不变，单拍敏感度约0.055秒/当前2.27%，不足以据此承诺追回对032的全部差距；并非预测或硬上界。详见同一阶段顶部补充；未改RTL、未新增仿真/板测或自动实施034。

用户要求查新日志。Codex核原P及`coremark_i64_d64_zmmul_overlap_vreload_300_01/validation_300.json`：各123RVLD完整响应/唯一RUN、固定P300/V300 BIN与manifest、完整UART、CRC5275/8803、全部13计数/timer与分类守恒通过。[合并实板收据](../sim/cpu_inst_hit_overlap/board/final_review_20261017_01/board_review.json)为`TASK033_FROZEN_P300_V300_BOARD_RAW_PASS_WITH_RESET_RECOVERY_LIMITATION`，原两次首PING0/60失败原样保留。新V在重新配置步骤对应的新目录成功，但日志不独立证明物理JTAG操作或具体恢复根因，不记KEY0暖复位可靠性通过。

P227882946cycles/2.430751424秒/CPI2.1024001593，V227937510cycles/2.431333440秒/CPI2.1034182332；相对032历史同BIN分别增加8.3884%/8.5122%时间，当前集成版没有整体提速，人工桥省6拍不能替代该实测。当前Camera启用使soc_top的DDR数据响应多寄存1拍，032冻结SoC无此级，MEM分类分别多29.07M/29.38M；这是已核配置差异，033净收益仍缺同集成配置开关对照，不能归因全部退化。受测P/V均不足10秒，仅工程对比。

当前无需重跑P/V/仿真/PDS；已收到本轮实测，可进入下一项静态评估：优先审posted store确认是否可独立于load数据响应寄存级，保留读数据时序、写排空和所有权，暂未改RTL或派发新测试；不能直接撤销为时序闭合加的寄存器。Loader在KEY0后无回应而重新配置后恢复的根因仍未确定，另保持问题边界。目的/数值/收据/评估约束见[同一阶段](cpu/CPU性能恢复评估_2026-10-17.md)。Codex本轮未操作串口/HDL/PDS，未更换BIN或覆盖历史日志。

## 2026-10-17：用户确认KEY0时DDR就绪指示灭后重亮，转同033位流重新配置后的仅V定位

用户直接反馈“按住熄灭，释放后重新亮起”，[观察记录](../sim/cpu_inst_hit_overlap/board/review_20261017_02/user_reset_observation_01.json)。现象与复位断言、DDR/PLL完成后SoC解除复位一致，不再把“完全没触发复位/DDR一直未就绪”作为当前首选解释；仍不能证明Loader常量自检/轮询或UART接收已运行。P及两份首PING零响应证据保持，根因未定，未改RTL/软件/串口判据。

下一步由用户通过JTAG重新下载跑P所用的同一个033位流，恢复配置时ROM/RAM初值，再仅V一次；本地现有文件`generate_bitstream/board_top.sbit`为9188552byte/2026-10-17 10:39:58，记录存在性而非证明板上身份。新功能门只读检查仍通过，不启动PDS实现，也不重跑P：

```powershell
Set-Location D:\riscv\RISCV
python -B tools/uart_loader/candidates/perf_2b/run_inst_hit_overlap_measurement.py --application validation_300 --port COM9 --log sim/cpu_inst_hit_overlap/board/coremark_i64_d64_zmmul_overlap_vreload_300_01/validation_300.json
```

重新配置后关闭串口助手，按工具提示KEY0/释放/等DDR就绪/Enter。与上次只重复KEY0不同，本次增加FPGA完整重新配置，用于区分暖复位残留与持续Loader启动/串口问题；通过也不直接断言具体RAM损坏根因。再次失败保留新日志后转Loader启动诊断，不循环重试。用户操作尚待结果，Codex本轮未开串口或运行HDL/PDS。

## 2026-10-17：033仅补V仍首PING零响应，停止同条件重试，待确认KEY0/DDR就绪状态

用户提交新V失败，Codex核`board/coremark_i64_d64_zmmul_overlap_vresume_300_01/validation_300.json`：唯一首PING，与首失败相同36byte已发送，5.0405488秒后实际RX0/60，application为空，LOAD/VERIFY/RUN未发。原P及两份失败均保持，[二次失败收据](../sim/cpu_inst_hit_overlap/board/review_20261017_02/board_review.json)为`TASK033_P_RAW_PASS_V_INITIAL_PING_ZERO_RX_TWICE_RESET_OBSERVATION_PENDING`；不认定V算法/CRC失败或已定位RTL缺陷，不再给相同条件第三次V命令。

只读核当前源码：KEY0/resetn经参考时钟消抖同时复位DDR和SoC；释放须DDR init/PLL lock，DDR就绪指示仅代表SoC解除复位，不代表Loader活着。现行Loader启动明确清BSS且链接器要求.data为空，没有证据把故障直接归为旧session状态残留。IDF选择verify_run_hello ROM/RAM对，但尚未观察实板下载内容/复位电平/CPU停点。已向用户询问“按住KEY0时DDR就绪指示是否熄灭、释放后是否重新亮起”，待这一物理现象决定查复位输入、DDR重新训练或Loader启动/串口路径；不要用旧板M17等PAD识别当前MINI指示灯，当前FDC led_ddr_ready为C19。

本轮只审原始日志和静态连接，未开串口/HDL/PDS、未改RTL/工具/BIN。P仅工程对比通过、较历史032慢8.39%的结论保持，尚无完整V/整体实板验收，不开始下一轮优化。详情见[同一阶段](cpu/CPU性能恢复评估_2026-10-17.md)。

## 2026-10-17：033实板P300原证据通过，较历史032慢8.39%；V首PING零响应，待用户仅补V

收到用户串口结果后，只读核`sim/cpu_inst_hit_overlap/board/coremark_i64_d64_zmmul_overlap_300_01/`两原始JSON。新[实板审查收据](../sim/cpu_inst_hit_overlap/board/review_20261017_01/board_review.json)状态`TASK033_BOARD_P300_RAW_PASS_V300_INITIAL_PING_FAILED`：P完整123响应/唯一RUN、同冻结BIN、CRC5275、全段输出/13计数/timer守恒通过，227882946cycles、108391804instret、2.430751424秒、CPI2.1024001593。不足10秒提示为预期，只记工程对比；033未获P/V整体或正式成绩PASS。

相对历史032 P210246597cycles/2.242630368秒，总+17636349周期/+8.3884%时间；MEM分类+29072126、IF−10566692、branch−1801050、load-use+931965，instret/OTHER/AW相同、AR+1。分类互斥且集成配置/RAM响应路径与032不同，不能把IF下降当总收益，也不能把全部退化归于033。V唯一记录首PING36byte发送后5.0249222秒收到0/60byte，application为空，LOAD/VERIFY/RUN均未发；是Loader没有回应，未证实V算法/RTL失败或KEY0物理原因。

原P与失败V保持；沿用同版033位流，不要求重新PDS或重跑P/HDL。只补固定V300，新目录：

```powershell
Set-Location D:\riscv\RISCV
python -B tools/uart_loader/candidates/perf_2b/run_inst_hit_overlap_measurement.py --application validation_300 --port COM9 --log sim/cpu_inst_hit_overlap/board/coremark_i64_d64_zmmul_overlap_vresume_300_01/validation_300.json
```

关闭串口助手，在本命令提示出现后按住KEY0约1秒并释放、等待DDR就绪再Enter，运行期间不复位。若再失败保留新目录交回定位，不自动重试。Codex本轮未开串口/HDL/PDS、未改RTL/工具/BIN；等V结果再做整体结论/性能归因，不另起优化。详情见[同一阶段](cpu/CPU性能恢复评估_2026-10-17.md)。

## 2026-10-17：033初组＋补齐原证据复核通过，专用固定P300/V300入口就绪，待用户实板

Codex读取补齐报告、源码/输入副本/原始轨迹，离线重放三项硬门与旧数据加强参考/10项合成检查；[最终收据](../sim/cpu_inst_hit_overlap/review_20261017_02/codex_review.json)为`TASK033_RAW_FUNCTIONAL_EVIDENCE_REVIEW_PASS`。新16项输入现行/封存/运行副本逐SHA相同，311保护项独立逐字节核验，只有此前已声明RISCV.pds会话元数据变化；执行者将部分设计IP误列metadata_only的口径未采用，设计/include仍逐字节核。桥仍7ab9d34c…52d933；原首败后复跑偏差保留，不删除旧失败证据。

独立I hit接受19/复位20、提升I miss在旧D响应75后AR76/复位80、Camera/PP延迟R同沿I接受130/176和双响应131/177均真实触发，18接受=15响应+3取消；初组CPU46/47/62/66及架构/错误路径/权限证据复用。独立桥Camera/PP地址的I预热只验证cache隔离，不代表真实SoC允许从这些窗口执行。受控人工场景省6拍，尚无033实板性能结论。本轮Codex未重跑HDL/PDS/串口。

新增[033专用双轮入口](../tools/uart_loader/candidates/perf_2b/run_inst_hit_overlap_measurements.ps1)及Python入口，绑定本版功能收据/源码/原证据，复用原串口传输/精确输出与13计数器检查，无PDS/位流审查门。固定P300/V300 BIN不变、不重建；两份离线计划各123响应、RUN1且未打开串口，见[工具收据](../sim/cpu_inst_hit_overlap/review_20261017_02/board_tool_ready.json)。用户下载033新位流，关闭串口助手后运行：

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_inst_hit_overlap_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_inst_hit_overlap/board/coremark_i64_d64_zmmul_overlap_300_01
```

P、V各一次，**每轮按脚本提示KEY0按下/释放、等DDR就绪后Enter**，运行期间不复位，不启动Camera/PP/CNN任务；首败保留日志停止，不自动重试。若已下载同版033，不需重复PDS。日志目录须新建；旧032同BIN基线P210246597/2.242630368秒、V210056980/2.240607787秒；当前集成配置与032不同，差异不可全归于033。细节/BIN身份/复核入口见[同一阶段](cpu/CPU性能恢复评估_2026-10-17.md)。实板/PHY/正式成绩仍未验收，下文“尚未放行”为此前状态。

## 2026-10-17：033结果已复核，原数据回放通过但三项未触发，先最小补齐

Codex只读核正式运行及封存50项输入/93项保护哈希、三job原始日志并重放独立checker，已有数据通过；CPU并行I接受46/响应47、缓冲48–61/62消费/66退休已核。桥保持7ab9d34c…52d933，未改设计/成功BIN，未重跑HDL/PDS/串口。受控场景全部D/I完成口径为19 vs25拍，**省6拍**，原报告省19错误。

尚不能放行实板：s9a测的是普通I槽复位；s9c复位时旧D尚未完成、无提升I AR；s10声称I hit实际发了I AR。没有已证实RTL错误，是覆盖门缺失/统计问题；另记录首败后自行修runner同tag重跑偏差。收据[review.json](../sim/cpu_inst_hit_overlap/review_20261017_01/review.json)，详情[同一阶段记录](cpu/CPU性能恢复评估_2026-10-17.md)。唯一后续[033最小补齐任务](../DeepSeek/任务033补齐_三个未触发场景与统计修正.md)：新目录一个桥job补三项，旧CPU/性能只读加强，不跑历史全套；原证据保持。DeepSeek补齐结果经Codex复核后直接给固定P300/V300上板入口。下文“待首次结果”为此前状态。

## 2026-10-17：033关键仿真任务已交付DeepSeek，待实现执行及原证据复核

用户反馈PDS时序结果完成并直接要求开始测试/仿真。当前桥SHA核仍为`7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933`；新增唯一[033执行任务](../DeepSeek/任务033_D读miss期间I缓存查询并行_关键仿真.md)。DeepSeek领取后按方案实现并封存TB、合法Pango用户口模型、独立参考/checker和最小真实CPU程序，直接一次执行bridge_on/bridge_off/soc关键组，保存全部轨迹/命令/原始日志，首败停止交回。本轮Codex只写测试方案和入口文档，未启动HDL/PDS/串口，未改设计或成功BIN；CLI尚待DeepSeek实现，无新功能PASS。

不再等待额外派发或PDS审查收据；用户时序完成信息不冒充独立时序签核。复用历史证据，不跑长CoreMark/旧全套/PHY。结果由Codex复核后才给新固定BIN实板比较入口；详情见[同一阶段记录](cpu/CPU性能恢复评估_2026-10-17.md)。下文“暂无可领取动态任务/待用户PDS”为此前状态。

## 2026-10-17：用户授权033 RTL实现，D读miss期间I查询并行，待用户PDS时序

用户明确“开始写rtl吧”，本对话直接完成[主桥](../myriscv/dual_sram_to_pango_ddr_bridge.v)单模块修改，覆盖本轮此前仅评估/交另一对话实施安排。新增默认开启`INST_HIT_UNDER_DATA_MISS_ENABLE`，仅x32/I缓存开启生效：D读RADDR/RDATA期间额外接受一笔I查询，寄存tag＋同步DRM命中后独立响应；miss保存地址/判定，旧D响应完成且无新D接受后提升到原主读槽，仍最多一笔物理DDR读，D优先及写排空/字节转发/失效保持。I/D可同拍返回，CPU核/接口/IP/约束/PDS/成功BIN均未改。

桥SHA b8d2aad8…948305→**7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933**；[准备收据](../sim/cpu_inst_hit_overlap/preparation_20261017_a/review.json)保存70项改前输入，除桥外69项未变。首轮真实cache内部实现因Icarus不支持既有厂家拼接表达式失败，原日志保留；真实端口封装/内部黑盒的六配置null-target语法展开通过，不能称厂家模型功能验证。逐边沿所有权/停放miss判定保持/新store失效/复位静态审查及后续关键组要求见[同一阶段记录](cpu/CPU性能恢复评估_2026-10-17.md)。未运行动态仿真/PDS/串口，收益未知。

**下一步用户重新综合、映射、布局布线检查本版时序，暂不直接下载跑分。** 有违例回本对话修复；时序通过后才按方案由DeepSeek编写并执行一组相关关键测试，再复核原始证据后给上板入口。当前无可领取动态仿真任务，不继承032或CAM2/CNN旧PASS；当前集成版与032历史性能比较边界仍保持。以下此前“尚未实施033”为历史状态。

## 2026-10-17：用户恢复CPU性能评估，032为历史基线，尚未实施033

用户要求查看相关文件并提升CPU性能。本轮读取AGENTS/Git、032已核P/V收据及当前CPU/桥/SoC，记录见[CPU性能恢复评估](cpu/CPU性能恢复评估_2026-10-17.md)。032固定P300/V300为2.242630368/2.240607787秒，CPI约1.94；最大已识别等待为MEM约21%，但032的MEM下降大部分被IF分类增加抵消，不能用分类下降代替总收益。

当前I/D独立DRM仍共用桥前端事务槽，RADDR/RDATA期间阻止另一侧命中请求，建议优先评估I/D命中路径解耦。尚无触发频率或净省拍证据；单在途取指/单缓冲限制潜在收益，不承诺提速百分比。当前Camera/PP/CNN集成及片内RAM响应寄存与032不同，032不自动作为当前集成版PASS。只新增评估文档，未改RTL/IP/约束/软件/成功镜像、未运行仿真/PDS/串口或发消息；下一步仍按Astra设计、用户时序、Sol测试要求/DeepSeek实现执行及原证据复核的有效分工推进。CAM2与CNN当前验收状态保持下文入口。

## 2026-10-17：Sol已封存训练模型CAM2试识别软件，快速RGB96/完整源帧双模式，待用户实拍

用户授权“你先准备吧”。新增`tests/cnn_handwritten_photo/`和`tools/cnn_handwritten_photo/`，模型固定4c8b5aca/CRC b9749177；不改RTL/FDC/PDS/IP、旧05a032af诊断包/成功BIN或历史证据。沿用已成功CAM2/J5、载板J10、真实拍照两测试模式0，无需本轮重新PDS/位流。用户仍负责KEY0/串口实板，本轮Sol未打开串口或运行HDL/PDS/真实CPU。

固定新BIN `tests/cnn_handwritten_photo/build/handwritten_20261017_b/program.bin`，42568byte，SHA256 `5b3364b064a4687a2e141bef504031fdc31a09d1e681b8cd1518133d4ee9f49c`，Loader CRC32 `2157dd62`，入口/装载0x40000000。RV32I静态指令/布局审计、栈界368byte、ELF实际嵌入24888byte模型装载流完全相等检查通过。a目录是准备过程静态构建，同BIN但依赖清单初版，正式PC只绑定b版，不重建后直接部署。

新CN03应用严格区分旧诊断banner/模型。默认快速`d`只导实际PP RGB96 27648byte，生成合同灰度32与独立整数全网10分数对照；不冒充本次源CPU/PC CRC或源→PP逐字节验收。`--full-source`发送`D`，另导同帧720p 1843200byte，核整帧CRC及源→PP27648byte全部一致。两模式均STOP/排空、CPU持有源帧至导出完成、释放所有发布帧；逐样本记录label/session/sample，预测错但全部分数一致会正常保存`label_match=false`，协议/CRC/计算错首败停止，不重试。

`sim/cnn/handwritten_photo_20261017_a/checks_01/review.json`通过11个native C设备模型场景、15个拒收：快/全、无尾帧、错误标签保留、6222word/CRC、分数/数量/释放/超时/源CRC/ACK/PP不一致、旧CN02/旧模型/损坏/截断、合成不作实板、取消前不打开串口。CNN分数由独立参考注入模型，只验证应用/PC控制协议，不是CNN硬件计算或真实CPU/HDL。58项软件输入已封存`sealed_20261017_a/`；`ready.json`为HANDWRITTEN_SOFTWARE_READY_FOR_USER_TRIAL_NOT_BOARD_PASS，71项既有成功源码/设计/PDS/FDC/原证据哈希保持。

用户摆白纸黑笔0，居中正向，关闭串口助手；首次建议完整源帧，运行后按提示KEY0按下/释放，等DDR就绪及画面稳定后Enter（约3分钟或更久）：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_handwritten_photo/run.py --port COM9 --label 0 --session trial01 --sample 1 --full-source --log-dir sim/cnn/board/handwritten_trial01_0_01
```

后续省略`--full-source`快速采样，每次新目录/KEY0；真实数字换`--label`，同一数字重复换`--sample`和目录，下一独立拍摄换session。首轮每类3–5张只作探索，不作为95%正式实拍准确率。只读`python -X utf8 tools/cnn_handwritten_photo/run.py --verify sim/cnn/board/handwritten_trial01_0_01`。详细步骤/范围见[新PC入口](../tools/cnn_handwritten_photo/README.md)及[同一训练阶段记录](cnn/手写数字数据准备与INT8训练_2026-10-17.md)，尚无新模型实板PASS，不将旧关键HDL缺项或CAM1根因写成通过。

## 2026-10-17：手写数字本地训练包已生成，Sol复核通过，尚非CAM2实拍准确率验收

用户要求查看新生成产物。发现`sim/cnn/training/handwritten_run_20261017_a/`已完成100轮浮点/40轮QAT，日志记录PyTorch2.7.1+cu128、CUDA12.8、RTX4070 Laptop GPU；首个最佳验证checkpoint为浮点第32轮、QAT第9轮。本轮Sol只复核既有产物，未重新训练、下载环境、操作PDS/HDL/串口或替换成功固件。

固定本地测试1069张：浮点1044/1069=97.6614%，INT8 1045/1069=97.7549%，量化后高0.0935个百分点；INT8各类召回最低96%，验证1054/1067=98.7816%。满足本地候选参考目标，但输入仍为28灰度图生成的合成RGB96后按合同取灰度32，不是真实相机PP数据；没有writer/session隔离或近重复保证，不能写成CAM2白纸黑笔识别、印刷体、HDL或实板PASS。

训练包MODEL_ID `4c8b5aca`，weights6152byte/bias264byte，shifts `[8,8,8,0]`，ABI1装载6222word/24888byte、CRC32 `b9749177`，load_words.bin SHA256 `c816999861d52fdd18446c39522c71d277f9221c3c850425af24d2b60df5de36`。封存manifest SHA256 `84182b2c448f17a175b819492a35ae222b9bd312d374307588f0c2f979fedc0a`。

Sol新收据`sim/cnn/training/handwritten_sol_review_20261017_01.json`通过：5339个原始哈希/基础输入转换、split无精确同源交集、214项封存哈希、24个输入的全部层参考及装载编码/累加界。`handwritten_sol_numeric_review_20261017_01.json`额外确认QAT第9轮checkpoint权重/bias逐项等于导出包，在CPU只读重放验证/测试2136样本、21360个INT32分数，向量整数/QAT/已存分数全部相等。现行7项训练源码/合同与冻结副本及身份清单一致；旧成功BIN的2f72e829…d7bd4保持。原日志/收据/封存目录不改，细节见[同一训练阶段记录](cnn/手写数字数据准备与INT8训练_2026-10-17.md)。后续仍需CAM2真实手写数据/独立session验收，旧诊断固件不会自动加载该训练包。

## 2026-10-17：手写数字数据已准备，用户要求停止等待自装PyTorch/CUDA

用户先选择以本地80bfd手写数据为主，要求重读原打印合同后再次明确“按刚才选择改为手写，另记任务范围变更”。固定中央白底黑字单字符0–9；原合同已加范围增补，数值合同digits10_int8_v1/SoC ABI1不改，微软雅黑粗体仅作可选打印对照。阶段入口[手写数字数据准备与INT8训练](cnn/手写数字数据准备与INT8训练_2026-10-17.md)。

本地只读核5339张28×28灰度BMP、9941218字节，0类839、其余各500，全可解码、无精确像素重复；缺原始writer/session身份，不将随机划分写为书写者独立或实拍验收。用户明确最终白纸黑笔、每张一个居中正向手写数字。固定划分训练3203/验证1067/测试1069，训练增强12812份；`sim/cnn/training/handwritten_data_review_20261017_a.json`通过全部5339个原始哈希/基础RGB96→灰度32及split无精确同源交集复核。新标准库整数参考与既有CAM2输入的全部层/10分数一致，历史证据只读。

新工具`tools/cnn_digits_training/`含准备/训练/QAT/ABI1导出/标量参考/封存复核，5个Python脚本语法检查通过；**PyTorch运行时和端到端未验证，尚无训练权重/量化参数/准确率PASS**。用户要求自己下载PyTorch/CUDA、Sol先停止等待：已终止所有下载，没有启动训练或残留Python进程，不自动恢复。已有隔离环境`sim/cnn/training_env/Scripts/python.exe`，用户安装完成后提供可用python路径再核CUDA并续训。`sim/cnn/training/wheels_20261017_a/*.whl.part`只是未完成预分配文件，不能安装或写成整包SHA通过。

后续数据/权重/日志留sim/cnn/training，不替换旧诊断包/固定BIN，不改RTL/FDC/PDS/IP，不启动HDL/PDS/串口。下列CAM2单帧成功基线继续有效，不能归为训练数字识别成功。

## 2026-10-17：CAM2/J5本轮实板采图/PP/CNN闭环通过，用户确认无彩点，建立CAM2成功基线

用户确认“已没有彩点,修复成功”。Sol查看`sim/cnn/board/cam2_20261017_01/source.png`，未见此前密集绿紫点，并只读重放`python -X utf8 tools/cnn_cam2_photo/run.py --verify sim/cnn/board/cam2_20261017_01`：完整源1843200字节/捕获→CPU→PC CRC闭合，源独立重算PP27648字节全部相等，实际RGB96的诊断CNN10分数及argmax一致，584159周期/6.231029ms，结果类别5仅为非训练模型输出。模型05a032af及固定BIN2f72e829…d7bd4保持，未自动重试；相机STOP及所有发布帧领取/释放账本按原始终态闭合。

本轮正式收据`sim/camera/cam2_photo_20261017_a/board_review_01.json`状态CAM2_ONE_FRAME_BOARD_DATA_AND_USER_VISUAL_ACCEPTANCE_PASS，绑定原始RX/TX/源/硬件记录/比较文件哈希。原result/verified/live_assessment中的VISUAL_PENDING及全部日志保持不变，用户视觉验收单独记录。CAM2/J5、载板J10、单摄像头、A/B为DDR双缓冲，是当前成功基线；不用旧CAM1位流或绑定旧接口的工具覆盖本版身份。

切换CAM2后观察到的彩点已消失，但具体CAM1接触/电气/引脚等根因没有证实，不能写CAM1硬件已修复。本次只是一帧源/PP/诊断CNN数据及用户看图验收，不扩大为长稳、全部异常/并发、硬件逐层、真实数字准确率或新实现时序签核。没有新增设计修改，不要求重跑PDS或历史全套；本轮仅核实板证据，未重新打开串口或运行仿真。

## 2026-10-17：Sol已封存CAM2/J5专用拍照PC入口，固定BIN不变，待用户新位流采图

用户切CAM2/J5后，新增`tools/cnn_cam2_photo/run.py`及`sim/camera/cam2_photo_20261017_a/`，硬件预期版本OV5640_LIVE_CAM2_J5_ON_J10_20261017_A。已核新有效FDC与Astra14项PAD映射收据一致，40项RTL/include与前真实拍照版本完全相同，两测试模式0；本轮没有改RTL/FDC/PDS/IP/固件或启动HDL/PDS/串口。载板J10、模组CAM2/J5，**仅单摄像头采集，A/B是该相机的DDR双缓冲**。

固定BIN仍为`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节/SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，未重建。原Loader、所有权/STOP尾帧、完整源导图、CRC/源→PP全部字节/CNN10分数不变。新PC记录CAM2/PAD/单摄像头/双DDR缓冲及用户新位流/J10/J5/KEY0操作确认，固定BIN本身不提供摄像头物理接口或实际下载版本的自动识别。原CAM1时序/图像证据不作为CAM2验收。

PC离线收据`sim/camera/cam2_photo_20261017_a/checks_01/review.json`通过：CAM2提示及新身份/14项PAD一致、旧CAM1/旧PCLK/J25/双摄像头等拒收、取消提示不打开串口、1829包合成原字节回放及合成不可冒充实板。未重复原数学/HDL/Full Boot/历史全套；新输入封存`sealed_20261017_a`，ready为CAM2_PHOTO_PC_READY_PENDING_USER_NEW_BITSTREAM_AND_BOARD。旧工具/固定BIN/所有旧日志哈希保持，CAM2实拍待完成。

用户重新实现核CAM2 PCLK时序及输入FF打包、生成并下载新位流后，关闭串口助手，使用新入口/新空目录，按提示KEY0复位后采图：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_cam2_photo/run.py --port COM9 --log-dir sim/cnn/board/cam2_20261017_01
```

原图`source.png`及`source.rgb565`和其余全部证据保存到该目录，约3分钟或更久，首败停止不自动重试。只读复核`python -X utf8 tools/cnn_cam2_photo/run.py --verify sim/cnn/board/cam2_20261017_01`。详见[CAM2单目PC入口](../tools/cnn_cam2_photo/README.md)，不要使用绑定旧CAM1或测试图身份的入口代替本版。

## 2026-10-17：按用户要求切换CAM2/J5单目采集，载板仍接J10，待新位流

核对DOUBLE-DVP-OV5640-1113原理图（PDF视觉核查）、硬件指导手册J10针表和厂家ov5640_200k通道1约束，当前有效constraint_check/temp_constraint_file.fdc只替换14项PAP_IO_LOC。CAM2接口为载板J5，不是更换底板J25；M21为手册L5_G1_11P_GMCLK引脚。原SCCB开漏INOUT、电压/IO标准、PCLK约束、采样沿、I/O寄存器属性与数据顺序均保持，未修改RTL、PDS、IP或软件；两测试模式均0，仍是真实拍照。

| 信号 | J10/J17针号 | CAM2 FPGA PAD |
|---|---:|---|
| D0/D1/D2/D3 | 31/25/26/24 | M22/R23/T23/AB24 |
| D4/D5/D6/D7 | 27/29/22/21 | P26/M26/AA24/AB25 |
| PCLK | 32 | M21 |
| HREF/VSYNC | 33/34 | U26/U25 |
| SDA/SCL | 20/23 | Y25/AC24 |
| RESETB | 35 | AC26 |

前CAM1约束完整副本、原理图截图及逐项映射/哈希收据在sim/camera/cam2_switch_20261017_a。静态核14个新PAD唯一且与其他已约束端口无冲突，全部匹配厂家通道1，反向替换后与原FDC逐字节相同，证明其他约束未变；git diff --check通过。未运行PDS/仿真/实板，不将CAM1时序或图像证据归给CAM2。

用户需重新综合/映射/布局布线/检查CAM2 PCLK时序及输入FF打包，生成并下载新位流后KEY0配置CAM2。模组放CAM2/J5，载板保持J10；只切约束不会改变已下载旧位流。单路采集逻辑不再配置或读取CAM1，A/B仍是CAM2同一相机的DDR双缓冲。Sol后续保留固定真实拍照BIN并更新硬件身份/新日志目录，不用绑定旧CAM1或测试图的入口冒充当前身份。CAM2采图用于后续对照，不预先承诺彩点消失。

## 2026-10-17：Sol已准备恢复真实拍照的PC入口，固定BIN不变，使用新目录

用户说明已恢复拍照模式。核当前board_top的COLORBAR/DVP_TEST均0及restore_live静态收据，新增`tools/cnn_live_photo/run.py`和`sim/camera/live_photo_20261017_a/`，绑定预期身份OV5640_LIVE_RESTORED_J10_20261017_A。原固定BIN2f72e829…d7bd4/42544字节不重建，历史彩条/DVP工具及全部旧日志保持；没有修改RTL/FDC/IP/PDS或运行HDL/PDS/串口。关闭测试不等于此前彩点根因修复。

正常配置244写/8读，503D00由表写入，4741通过传感器硬复位/表首软件复位恢复默认00，不伪称本模式显式写入/额外读回4741。PC保存预期40项源码/include身份及用户正常位流/J10/KEY0确认，不能独立证明板上位流/寄存器值，不继承旧时序PASS。若用户仅恢复RTL，须重新生成并下载正常模式位流；如果已下载，无需再实现，KEY0使传感器重配置后采图即可。

必要PC检查在`sim/camera/live_photo_20261017_a/checks_02/review.json`：提示/身份/错误模式/J25拒收、取消提示不打开串口、既有1829包合成原字节回放。checks_01为检查器误沿用旧彩条提示字面要求导致首败，修复检查器后新目录通过，旧目录不覆盖。`sealed_20261017_a`封存当前输入，ready为LIVE_PHOTO_PC_READY_PENDING_USER_NEW_BITSTREAM_AND_BOARD；没有新增实拍PASS，不重复历史全套。

确认恢复拍照位流已下载且实物J10/CAM1-J4后，关闭串口助手，在新空目录运行，按提示KEY0按下/释放、等DDR就绪后Enter：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_live_photo/run.py --port COM9 --log-dir sim/cnn/board/live_20261017_01
```

输出原图`source.png`、`source.rgb565`、实际/参考RGB96、灰度和完整串口/比较证据；首败停止、不自动重试。只读复核`python -X utf8 tools/cnn_live_photo/run.py --verify sim/cnn/board/live_20261017_01`。详见[恢复拍照入口](../tools/cnn_live_photo/README.md)。

## 2026-10-17：按用户要求恢复真实拍照模式，待重新下载正常模式位流

仅将board_top的CAMERA_COLORBAR_ENABLE=0、CAMERA_DVP_TEST_ENABLE=0，恢复原244笔配置写/8笔读回；表中503D00关闭PRE-ISP彩条，传感器硬复位及表首软件复位恢复4741默认00。两个诊断模式实现保留，历史照片及测试证据不改。采样沿、帧格式、DVP输入寄存器、时钟/引脚约束、DMA/PP/CNN均未改；关闭测试不代表此前彩点根因已修复。

静态板级语法展开exit0（厂家黑盒忽略），记录sim/camera/restore_live_20261017_a；未运行PDS/实板。用户重新生成并下载本版位流，KEY0重新配置后才能拍真实画面；只重跑PC工具不能关闭旧位流测试发生器。恢复使用真实画面的photo流程，不使用绑定DVP/彩条硬件身份的专用入口，运行时保存新目录；固定固件ABI不变，旧日志不覆盖。

## 2026-10-17：DVP测试原始通路复核一致，10字节结构多位变化，排查不再局限D0

用户交回sim/cnn/board/dvp_test_20261017_01。本对话只读执行`python tools/cnn_dvp_test_photo/run.py --verify sim/cnn/board/dvp_test_20261017_01`，源1843200字节/PP27648字节/10个诊断分数复核通过，CNN6.229664ms。图片为密集竖线，不能因非八色条认定异常；模式0的精确字节序列尚无独立golden，原verified/日志保持不变。当前仍非图像质量、完整关键HDL或真实数字准确率PASS。

将小端RGB565高字节先行还原DVP顺序后，每行2560字节呈明显10字节重复结构。按每行起点模10统计，每相位184320样本：p0=00全，p1=00全，p2=02(163410)/00(20910)，p3=04(136238)/00(48082)，p4=00全，p5=10(122210)/00(62110)，p6=00全，p7=40(184057)/00(263)，p8=80全，p9=ff全。720行均不同。统计收据sim/camera/dvp_pixels_20261017_a/review.json绑定原源SHA，记录期望周期为观测假设，不写误码率或已证明的丢位数。

该结果使“只查D0/只有PRE-ISP处理”的解释不足，D1/D2/D4/D6也出现同相位0/单bit变化；FF阶段全部数据线可以为高，因此不能简单解释成永久接地。优先考虑共同采样窗口或数据相关信号完整性，仍需核实模式定义和电气波形才能确诊。下一单变量对照可在保持DVP测试/引脚/采样沿不变时降低输出速率（先核PLL/分频寄存器定义），或同步测PCLK与D0/D1/D2稳定窗；不根据此图直接翻转采样沿，不滤波，不强制数据位。本轮未改RTL/约束/IP/固件，也未重跑实板。

## 2026-10-17：Sol已封存DVP模式0/8bit专用PC入口，沿用固定BIN，待用户新位流采图

用户确认切换503D00/474105后要求更新诊断入口，新增`tools/cnn_dvp_test_photo/run.py`及`sim/camera/dvp_photo_20261017_a/`，保留旧PRE-ISP彩条/真实画面入口及全部历史日志。固定BIN仍为`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节，SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，未重建。新预期硬件版本OV5640_DVP_MODE0_8BIT_J10_20261017_A，绑定本轮Astra静态收据和40项RTL/include、J10约束；COLORBAR0/DVP_TEST1，245写/10读预期强制核503D00/474105。

本轮只新增PC身份/提示及原始字节统计，没有改RTL/IP/FDC/PDS/固件、启动HDL/PDS/串口。新位流必须由用户重新综合/实现/核时序/生成/下载，J10、CAM1/J4，下载后KEY0重新配置；旧PRE-ISP彩条模式及旧寄存器身份均被新工具拒收，不继承旧时序或实板PASS。PC记录预期源码身份与用户操作确认，固定BIN没有独立读取503D/4741或硬件版本的接口，不将确认当PC实测版本证明。

新工具保留严格2560字节×720行、源CRC/所有权/STOP排空、源→PP27648字节/CNN10分数以及1829包CN02原流程。DVP测试模式0不能预设为原RGB八色条，PNG仅为既有RGB565解释预览。新增`dvp_assessment.json`按原始字节保存两字节位置的直方图/D0零一及变化次数、常见拼接word、720行CRC/相同行统计；不设未经核实的图案像素/整帧CRC或D0误码率。模式图案/几何、条内及跨帧稳定性仍待实板，若格式错首败停，不改行长/清错继续。

必要离线收据`sim/camera/dvp_photo_20261017_a/checks_01/review.json`通过：新身份/提示、旧PRE-ISP模式/寄存器/J25等拒收、取消提示不打开串口、已知字节位置/D0单次翻转与行一致性检查、既有1829包合成原字节回放及合成不能冒充实板。复用原固定BIN和PP/CNN数学证据，不重跑HDL/Full Boot/历史全套。封存`sealed_20261017_a/`共43项输入，ready状态DVP_TEST_PC_READY_PENDING_USER_NEW_BITSTREAM_AND_BOARD，尚无本版实拍结果。

用户完成本版位流生成/下载并确认J10后，关闭串口助手，使用新空目录，按提示KEY0按下/释放、等DDR就绪再Enter：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_dvp_test_photo/run.py --port COM9 --log-dir sim/cnn/board/dvp_test_20261017_01
```

主要保留`source.rgb565`、`source.png`、`dvp_assessment.json`及完整RX/TX/源PP/CNN比较。只读复核：`python -X utf8 tools/cnn_dvp_test_photo/run.py --verify sim/cnn/board/dvp_test_20261017_01`。详见[DVP测试PC入口](../tools/cnn_dvp_test_photo/README.md)。本入口不会替用户执行PDS、下载或KEY0，不把数据闭环一致扩大为测试图正确或故障已解决。

## 2026-10-17：按用户要求切换DVP级测试模式0/8bit，PRE-ISP彩条关闭，待新实现及采图

board_top设置CAMERA_COLORBAR_ENABLE=0、CAMERA_DVP_TEST_ENABLE=1；参数逐级传入config/ROM，index239写503D00、index244写474105，245笔配置后10笔读回，额外确认503D=00/4741=05才CONFIG_DONE。4741依据数据手册DVP control bit2启用/bit1模式0/bit0为8bit；若两个参数均开启，DVP优先并强制503D00，避免同时测试源。两参数均0恢复原244写/8读真实成像，PRE-ISP单独开启仍可复现前版。

修改前全部myriscv/PDS/FDC及SHA保存在sim/camera/dvp_test_20261017_a/before与before_manifest.json，本轮仅改5个配置/参数文件；原卷取图、FIFO/DMA、RGB565拼接、720p严格帧长度、PCLK上升沿、IP/FDC/PDS/CPU/CNN/软件均不变。主板级与config live/PRE-ISP/DVP/双开优先级5个静态展开均exit0，review.json为静态准备，不是功能/PDS/实板PASS；未运行PDS或串口。

下一步用户重新综合/实现/检查时序/生成并下载本版位流，KEY0使传感器重新配置，实物继续匹配J10。旧colorbar专用PC入口绑定503D80/474100及旧源码身份，不能原样当本版放行；交Sol沿原固定photo BIN新增DVP诊断入口或版本记录，绑定本次设计身份，保存新的原始图/串口目录，不改旧封存与证据。本模式输出不能预设为原来的RGB八色条；RGB565 PNG仅作可视化，核心检查原始字节规律、条内/跨帧稳定性以及D0位变化。模式0具体图案及有效帧几何仍需实板确认，若严格格式失败保留首败，不改长度或清错继续。

本轮没有改ISP控制寄存器5000/5001/501F、PCLK极性4740或数据顺序4745，以测试源为唯一实验变量。DVP模式干净与否都只用于进一步定位，不能直接证明根因或代替实际引脚波形。

## 2026-10-17：D0映射/当前STA/ISP路径已核对，尚无实际引脚波形，不能确诊D0故障

按用户要求只读核查，收据`sim/camera/d0_isp_review_20261017_a/review.json`绑定当前约束/映射/实现/STA/配置源码及彩条硬件记录。资料表J10/J17第8脚→M24，当前FDC与device_map/board_top.pcf一致；place_route/board_top.prr确认camera_data[0]位于M24/BANKL5、IREGIS。载板D0是8bit总线低位，对应OV5640传感器D[9:2]中的D2，不能拿裸片D0当探测信号。这里只确认文档/实现映射，未测实物导通或电气波形。

当前磁盘report_timing为All Constraints Met：camera_pclk slow setup组WNS1.441ns/hold0.195ns、fast setup3.072ns/hold0.132ns，无失败端点。RTL同PCLK上升沿采D/HREF/VSYNC，FDC仍是假设周期10ns、相对下降沿0..3ns输入预算，非实测传感器数据窗口。报告详细路径未逐条列D0，组裕量不能当D0独立物理测量；0x4740极性寄存器当前未写/未读，数据手册默认20不能冒充实测值。实际相位需在J10第18脚PCLK(L22)和第8脚D0(M24)同步测量，并对照D1/电平/振铃/数据稳定窗，当前没有仪器波形。

ISP核查：503D80是PRE ISP标准八色条，474100关闭独立DVP测试发生器；501F01选ISP RGB，不是501F02的ISP dither支路。5000=A7启用LENC/raw gamma/坏点及插值，5001=A3启用SDE/缩放/色矩阵/AWB，因此不能把本次彩条当完全绕过ISP的数字输出。5020未显式配置或读回；手册5.1中的dither字段00标为Not allowed，不应猜测写502000就是关闭抖动。青条2efc/2ffc相差绿色6bit数值8，不是普通量化末位±1，不能用正常dither直接解释；红条低位±1单独则不足以证明物理错误。

结论：未发现D0逻辑/约束错接；当前实现满足既定STA预算；ISP可改变彩条数值，但是否造成观察到的两值跳变仍未证实。下一最小隔离实验可采用DVP级测试模式（datasheet4741 bit2启用、bit0选8bit，模式0候选05）并关闭PRE ISP测试，保持其他时序/引脚不变且读回确认；需另立配置身份，不能预设为相同RGB八色条或沿用旧期望值。本轮仅核查，未改寄存器/RTL/FDC、未派发重拍、未运行PDS或仿真。

## 2026-10-17：用户确认八色条稳定，但原始青条/红条仍有位变化，不能记为纯净彩条PASS

查看sim/cnn/board/colorbar_20261017_01/source.png：八条布局稳定，青条内部仍有密集细点。独立从小端RGB565位复制生成RGB，全部像素与PNG相等。避开边界取y20..699、青条x335..449共78200像素，0x2efc=39136、0x2ffc=39064，异或0x0100；红条x830..939共74800像素，0xd003=74239、0xd002=561，异或0x0001。其余六条所取内部ROI各为单一像素值。原目录verified记录源→PP27648字节及10分数一致；本轮未重新执行整套串口验证，也不改原verified/日志。

统计收据sim/camera/colorbar_pixels_20261017_a/review.json绑定source.rgb565 SHA。高字节bit0和低字节bit0均对应物理DVP D0，是下一步重点核查线索，尚不能排除传感器测试图后ISP/格式等因素，不能仅据单帧判定引脚损坏或采样沿错误。用户“稳定”作为用户观察记录；单次导图不证明跨帧或遮挡不变性。未改RTL/FDC/IP/软件，未重复上板。后续重点核对D0映射/连接/真实采样相位以及测试图ISP路径，不用滤波或强制某位掩盖异常。

## 2026-10-17：Sol已准备彩条专用PC入口，固定拍图BIN不变，必须用户重新生成/下载彩条位流后使用

按用户要求纠正“沿用旧位流/仅换软件”的历史提示，但不修改已封存`tools/cnn_digits_photo/run.py`及固定固件，新增专用`tools/cnn_colorbar_photo/run.py`。**本次必须用户重新综合/映射/布局布线、检查新时序、生成并下载内部彩条位流，实物J10/CAM1-J4，下载后KEY0重新配置传感器。旧位流不会因重跑脚本而开启彩条。** 未启动PDS/下载/串口；彩条版HDL/时序/实板不继承旧J10 PASS。

固定BIN仍为`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节，SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，未重建；模型05a032af/CRC0ca5949e不变。新预期硬件版本`OV5640_COLORBAR_J10_20261016_A`，`sim/camera/colorbar_photo_20261017_a/hardware.json`固定40项RTL/include及J10约束身份，与Astra5项配置修改/静态收据相符。新入口明确要求新位流并将用户新彩条下载/J10/KEY0确认、预期源码身份及存在时的本地sbit文件指纹写入`hardware_record.json`；不把操作确认或本地指纹写成板上位流自动识别，固定BIN也不能向PC独立暴露503D/4741读回值。新RTL CONFIG_DONE预期包含这两项读回检查，旧版同样有CONFIG=OK文字，不能只凭该文字宣称彩条已开启。

必要PC离线检查收据`sim/camera/colorbar_photo_20261017_a/checks_01/review.json`：新提示/硬件记录、J25/旧模式/不重建/错源码SHA拒收、取消前置提示不打开串口、1829包既有合成RX/TX回放及合成不能冒充实板；视觉和遮挡不变性始终PENDING。只查新增PC功能，复用原固定BIN和源→PP/CNN参考证据，不重跑HDL/Full Boot/历史全套。输入封存`sealed_20261017_a/`共43项，原软件/全部旧实板文件哈希未变，ready状态COLORBAR_PC_READY_PENDING_USER_NEW_BITSTREAM_AND_BOARD；无本轮实拍结果。

用户完成新彩条位流生成/下载并确认J10后，关闭串口助手，使用新入口/新空目录，按提示下载后KEY0按下/释放、等DDR就绪再Enter：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_colorbar_photo/run.py --port COM9 --log-dir sim/cnn/board/colorbar_20261017_01
```

原图`source.png`/`source.rgb565`及全部原有源CRC/PP逐字节/CNN10分数、完整RX/TX均保留。`colorbar_assessment.json`明确记录视觉待验、单次采集未验证遮挡不变；不预设未经核实的八色顺序/边界/像素值或固定整帧CRC。先看原图是否稳定八色条及是否仍有绿紫点，再分析PP/CNN，不能把数据闭环PASS扩成彩条图像质量PASS。只读复核`python -X utf8 tools/cnn_colorbar_photo/run.py --verify sim/cnn/board/colorbar_20261017_01`。说明见[彩条PC入口](../tools/cnn_colorbar_photo/README.md)。

## 2026-10-16：用户要求启用OV5640内部固定彩条，配置RTL已准备，待新位流

用户说明重新插拔摄像头并要求内部固定彩条。按本机OV5640 DVP应用指南4.7（提取文本1135–1136行）及datasheet test pattern表，主board_top设置CAMERA_COLORBAR_ENABLE=1，经soc_ddr3_top→camera_mmio→ov5640_config/ROM传递。原表index239由503D00切为503D80，末尾增加index244写474100；彩条模式245笔写后10笔读回，额外强制读503D=80、4741=00才CONFIG_DONE。普通参数默认0保留244笔写/8笔读流程，恢复真实画面只需board_top该参数改0后重新生成下载位流。未改采样沿、RGB565/720p、DMA/帧长度、FIFO/DDR IP、CPU/CNN或MMIO ABI。

前像及静态收据在sim/camera/colorbar_20261016_a，确认仅改5个配置/参数文件，PDS/FDC保持；板级彩条与config普通/彩条三配置Icarus静态展开均exit0（板级忽略厂家黑盒），未运行HDL/PDS/实板。此次不是PC生成彩条，不允许把有CRC闭合的彩点图认定为图像正常。

下一步用户重新综合/映射/布局布线/生成并下载新位流，KEY0触发传感器重配置；旧位流/只重跑PC脚本不能启用彩条。当前引脚约束仍沿原J10配置，若实物仍插J25须先正确迁移约束，不能仅换插口沿用旧映射。沿用户板优先诊断授权，Sol可沿现有固定photo软件逻辑（ABI不变）记录本版硬件身份并准备新目录彩条采图；不要重写/覆盖旧日志或把原设计清单冒充当前身份。

预期为标准八色条，画面应不随镜头遮挡/场景改变；先检查source.rgb565/source.png本身，再核PP/CNN。同色条内部应稳定，具体方向/边界/数值需结合现有ISP路径核对，不预设一个未经核实的整帧CRC。彩条仍有点优先排查测试图输出之后的格式/传输/采样链路；彩条干净则把排查重点移向真实成像/ISP等环节，两者都不是单凭图片完成根因证明。

## 2026-10-16：用户将载板移至J25，当前实现仍为J10引脚，不能直接沿用位流重拍

用户报告“换到j25端口”。按底板40针扩展口理解：本机官方硬件手册提取文本`doc/camera/evidence_2026-10-15/教程1_盘古MINI系列开发板硬件指导手册_V1.3.txt`第36–38页明确J10/J25是不同FPGA管脚集合。保持同针序插接时，PCLK第18脚由J10 L22改为J25 Y22，SDA第4脚由R20改U14，SCL第6脚由P19改T17；其余数据/HREF/VSYNC/reset引脚也不同。

当前有效FDC及`device_map/board_top.pcf`仍固定PCLK L22、SDA R20、SCL P19等J10映射，已有PCLK STA/I/O打包收据仅适用于该实现。物理改J25不改变位流引脚，不能直接给新日志目录当作同一实现重拍。若保留J25，须由Astra先核载板针序/电源地/目标bank及PCLK时钟能力，再迁移相机引脚约束，由用户重新PDS/下载；不把文字表格直接当已验证的J25约束。CPU固件/PC工具原则上可沿用，但需新硬件身份/时序和运行目录，不继承J10实板/时序PASS。本轮只读核资料并记录，未改RTL/FDC/PDS/固件、未运行PDS/串口或自动发消息。

## 2026-10-16：photo_04再次首帧格式错，三轮格式失败已复核，停止无改动盲拍

用户photo_04报CAM_ERR3。本轮核全部原文件哈希、337条Loader响应、应用模型/传感器就绪行、GC及唯一失败文本，RX/TX无剩余。SEQ0/CLAIMS0/GLOBAL_SEQ0、BUFSTATE100（两块FREE），busy/stream0、overflow0，PP0/CNN8：与photo_02同为首帧发布前DVP格式失败；约0.78109秒为应用累计。photo_03是A已发布/领取后B在途错误，复用前条收据，不混淆两种现场。三次失败BIN/模型一致，当前40项设计/include仍与封存相符。

既有photo_01源帧已含彩点、源CRC闭合且源→PP全部字节一致；用户重新插拔后仍出现格式错。当前不能区分传感器/电气/真实采样相位或格式逻辑，不归因Python解析，不把模型VALID当CNN已运行，也不继续给无改动盲拍命令。需要实际DVP信号核查/固定测试图；必要时由Astra增加首次格式子原因、行号/行字节计数及同步信号快照，严格判据和原ABI/所有权不放宽。

本轮收据及可转交Astra的最小定位说明在`sim/cnn/camera_failure_photo04_20261016/review.json`和`ASTRA_HANDOFF.md`，引用既有原证据而不重复归档。未改RTL/IP/FDC/PDS/软件/原日志，未启动HDL/PDS/串口；根因仍未确诊，不声称明确RTL缺陷。未自动给其他对话发消息。

## 2026-10-16：photo_03为领取A/SEQ1后B在途帧格式错误，PP/CNN未启动

本对话复核`sim/cnn/board/photo_20261016_03/`：result中全部file_sha256与文件一致，按固定manifest逐条匹配完整Loader TX/RX，剩余TX精确GC；应用原始串口确认模型6222word/CRC0ca5949e/ID05a032af有效、传感器配置OK，随后唯一CAMERA_ERROR，无CNN_JOB/导图。只读复核收据`sim/cnn/camera_failure_photo03_20261016/review.json`，未改原日志/软件/RTL，未重开串口。

与photo_02不同，本次CLAIMS1/TARGET_CLAIMS1、BUF0/SEQ1、GLOBAL_SEQ1，说明A完整发布且CPU领取；BUFSTATE0x123解码A=CPU(3)、B=FREE(0)、active_buf=1、dual=1、busy/stream=0。结合capture_group的wait_target→stop_and_drain→pp_start顺序及CAM_ERR3来自format_sync，定位为领取A后B在途采集发生格式错误并排空至FREE。不能将此前photo_02“两块FREE/CLAIMS0”的结论套到此目录；本次A仍归CPU，不擅自重启流或覆盖。PP_STATUS0和CNN_STATUS8只说明PP未启动/CNN模型有效，CNN_ERROR0，无CNN运算结果；约0.82849秒为应用累计而非CNN耗时。

本次只证明A帧格式/发布检查通过，不证明A图像没有彩点；已有photo_01原图彩点与photo_02/03格式错共同要求定位传感器/DVP数据及同步信号链路。现有ERR3没有首错子类/行号/字节计数，尚不能区分采样相位、电气连接、传感器输出或逻辑问题，不据此盲改采样沿或放宽2560字节×720行判据。下一定位应先断电核实载板/排线/公共地与供电，仍异常则扩展首错诊断和固定测试图；每次只变一个条件，保留新目录，用户操作实板。当前不清错继续CNN，不把软件抛异常当PC解码器故障。

## 2026-10-16：photo_01同帧源/PP/CNN一致但原图有彩点；photo_02首帧DVP格式错，保持首败待定位

收到用户photo_02 traceback，本轮核验两目录原始文件哈希、完整Loader响应及串口命令/终态：`sim/cnn/board/photo_20261016_02`状态STOPPED_FIRST_FAILURE，模型6222word/CRC0ca5949e/ID05a032af已VALID，SENSOR_ID5640/CONFIG OK；仅发G/C，随后硬件CAM_ERR=3，捕获帧格式错误。CAM_STATUS31表示配置完成/dual/error，busy/stream/overflow均0；BUFSTATE100两块FREE，GLOBAL_SEQ0、CLAIMS0。PP_STATUS0、CNN_STATUS8表示PP/CNN均未启动，不能解释成CNN计算或UART导图超时。ELAPSED_TICKS69543011约0.742秒为自应用启动累计，非单独捕获时间。原始RX/TX逐字节消费完毕、没有D/导图请求、未自动重试。

相同固定BIN2f72e829…d7bd4的photo_01完整回放复核通过：源1843200字节捕获/CPU导出/PC CRC闭合，源独立生成PP的27648字节全相等，实际RGB96的CNN10分数也相等，6.227ms。视觉检查`source.png`确认完整原始帧已经有密集绿紫点；不是PNG/串口/PP缩放或CNN引入。当前证据优先指向捕获CRC之前的传感器/DVP输入/采样链路，但不据此直接确诊具体引脚或RTL缺陷。PCLK报告满足实现预算不等于已测实际相位。

camera_mmio将format_sync映射为错误码3；ov5640_capture的四类触发为接受帧首时HREF已高、有效字节/行数超限、HREF结束行字节数不等2560/行数超限、VSYNC结束不满足720完整行及HREF低。现有单码无法知道是哪类、哪行或哪次采样出错；保留严格2560字节×720行判据，不清错继续/忽略坏帧/放宽长度。失败时无发布或领取，硬件已停采并排空到FREE，无待释放CPU所有权。

收据`sim/cnn/board_photo_20261016_a/failure_review_photo02.json`保存成功/失败原证据身份和最小复现范围，可交Astra/板级定位；尚非已证明RTL缺陷。当前40项RTL/include仍与封存一致，本轮未改RTL/IP/PDS/软件/日志、未跑仿真/PDS/实板或重试。优先核实际PCLK/data/HREF/VSYNC相位与连接/供电稳定性，固定测试图定位；如需细化格式子原因，由Astra按既有RTL/用户PDS流程实施，不由Sol盲改采样沿。

## 2026-10-16：CNN拍图追加同帧完整720p原图导出，新软件封存完成，待用户实拍

用户要求“加上输出原始拍摄画面”。新增`tests/cnn_digits_photo/`、`tools/cnn_digits_photo/`及`sim/cnn/board_photo_20261016_a/`，未修改旧`cnn_digits_diag`软件、RTL/IP/FDC/PDS或前两轮实板证据。沿用最新RAM+1拍/DVP I/O修复CNN位流，本轮不需要再次PDS/下载位流。现有报告约束下STA满足、10个输入FF打包已复核，实际传感器输入相位未测、关键HDL未完成，沿用用户授权板优先诊断。

固定新BIN：`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节，SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，Loader CRC `093ba2e9`。同一非训练参数包05a032af/6222word/CRC0ca5949e不变。原流程模型装载/采A/STOP排空/PP/CNN10分数核对保持；新CN02先导出RGB96，再导同一次1280×720小端RGB565原图1843200字节，两条流共1829个包/ACK。A直到两条流END被ACK后才释放，再按各自SEQ领取/释放可能的B尾帧并核账本。

CPU源导出累计CRC与Camera捕获CRC比较，PC核逐包/整帧CRC。PC保存`source.rgb565`及未滤波的`source.png`；仅从原始帧独立重算`expected96.rgb/.png`，与实际`rgb96.bin/.png`逐字节比全部27648字节，记录首差异源/输出坐标，继续从实际RGB96计算完整整数CNN比10分数。差异时完整收到的图/参考/日志先保存，再首败停止、不重试。原图传输纯线速理论160秒，加协议/CPU开销需更久，预留约3分钟或更多，PC总导出截止600秒。

新软件必要离线收据`sim/cnn/board_photo_20261016_a/checks_01/review.json`：7个实际固件C/原生设备模型场景、13个拒绝检查，包含完整720p源/所有1829包、PNG逐像素展开、尾帧有/无、源CRC/源ACK/释放失败、源序号/地址/种类/长度/载荷CRC/截断，以及“所有CRC和CNN分数一致但PP与源差一字节”准确拒绝。RV32I/ELF/BIN/存储边界及368字节静态栈审计通过；CNN参考未改，复用原7图案C int64/Python宽整数证据，不重复历史全套。原生检查不是HDL/真实CPU仿真，本版新增软件未实板通过。

封存`sim/cnn/board_photo_20261016_a/sealed_photo_20261016_a/`共52项软件/模型/检查输入，复用原设计快照。`ready_review.json`状态SOURCE_PHOTO_SOFTWARE_READY_USER_BOARD_FIRST_NOT_BOARD_PASS，旧photo成功软件、cnn_digits_diag固定软件及diag_20261016_01/02原日志身份全部未变。见[新增导原图说明](../tests/cnn_digits_photo/README.md)。关闭串口助手，使用新的空目录执行，按提示KEY0按下/释放、等DDR就绪、画面稳定后Enter：

```powershell
Set-Location D:\riscv\RISCV
python tools/cnn_digits_photo/run.py --port COM9 --log-dir sim/cnn/board/photo_20261016_01
```

实拍后保留整个目录，原图`source.png`、预处理图`rgb96.png`、灰度`gray32.png`，差异看`preprocess_comparison.json`；原始回放入口`python tools/cnn_digits_photo/run.py --verify sim/cnn/board/photo_20261016_01`。若源像素已有彩点且PP全字节一致，可把问题范围缩到PP之前/源路径；不能据单次一致断言图像质量、实际输入时序或数字准确率通过。

## 2026-10-16：绿紫点定位——本版磁盘PCLK时序满足现有约束，10个DVP首级FF全部实际打包进I/O

按用户明确要求检查已有PDS产物，未启动PDS。当前`report_timing/board_top.rtr`工具记录为10月16日本轮实现，Design Summary为All Constraints Met；PCLK slow/fast setup分别+1.651/+3.072ns，slow/fast hold分别+0.200/+0.119ns，各325端点、0失败。不能把之前修复前PCLK负裕量继续当当前实现结论。39项RTL及csr_defs.vh共40项源码身份全部与本轮CNN封存相符。

`device_map/run.log`明确记录din_q[7:0]/href_q/vsync_q十个FF均“packed in IFF ... success”，`place_route/board_top.prr`十个相机输入的IO_REGISTER全部为IREGIS，确认属性实际生效。D2=K26落在IOLHR_16_828；已打印的fast setup路径为+3.072ns，输入到IFF仅0.059ns route，不再是旧版远处CLM长线。该条是D2的fast setup，不冒充全部输入每个corner的逐项路径；原报告只打印部分最差路径。

边界仍在板级输入合同：有效FDC为100MHz/PCLK下降沿launch、上升沿capture、输入延迟min0/max3ns，这是历史注明的实现目标，未测实际传感器推出相位/板级偏斜。现有报告排除了“报告仍违例/未打包”的解释，不能排除真实DVP相位/信号完整性、传感器、源DDR/PP读入问题；磁盘报告也不能单独证明本次板上下载的是哪个位流。下一个最小定位仍为固定测试图/同帧源RGB565与PP输出比较，结合实际PCLK/D2测量，不盲目翻采样沿或放宽约束。

复核脚本/原报告副本/收据在`sim/cnn/pclk_review_20261016_a/`，入口`review.py`仅读取既有报告，禁止覆盖既有收据。已记录本版约束下STA满足及IO打包事实；实际输入电气/相位和绿紫点原因未确诊，关键HDL仍未完成，未改RTL/FDC/IP/PDS/成功固件或实板原始证据。

## 2026-10-16：CNN单次实板10分数原证据一致，但RGB96出现绿紫点，图像质量问题待定位

用户提供`sim/cnn/board/diag_20261016_01/rgb96.png`并报告大量绿紫点。本轮只读复核`run.py --verify`成功：ACTUAL_SERIAL完整Loader/RX/TX/27648字节/PNG/元数据及10个signed分数一致，分数`[-19,-179,107,149,-244,163,138,-78,115,155]`、argmax=5、584012周期/6.229ms。非训练包ID仍为05a032af，仅证明该输入/参数包整网输出一致。时序仍未收到用户通过确认，关键HDL未完成；不以工具中的新位流操作确认冒充时序PASS。

图像彩点确实存在，旧photo成功图无同类密集点；本次9216像素全部符合RGB565位复制展开规则，PP CRC=71fe306c与CPU/串口完整字节一致，PNG回放也一致。彩点在PP已产生的字节中，不能归因于PNG转换或本次记录的UART误码。上方视觉灰背景区域有234点呈现“翻转绿色最高位后接近灰色”的特征；RGB565 bit10经DVP高字节D2传输，优先怀疑DVP采样/输入时序等上游位错误，但这只是定位线索，未导出本次720p源，不能排除源DDR/PP读入或传感器侧问题。不能因为CNN参考一致而判图像正确，也不能据此直接确诊某一引脚/RTL缺陷。

分析收据`sim/cnn/board_diag_20261016_a/image_review_01.json`保留原图/RX/TX身份、像素特征及未覆盖边界，未改原证据/RTL/IP/PDS/软件，未启动仿真或PDS。下一最小定位为核本版PCLK setup/hold及IO首级FF实际打包、导同一帧源RGB565与PP输出对照，或使用传感器固定测试图定位位错误；不重跑历史全套。

## 2026-10-16：用户授权数字CNN板优先诊断，软件与非训练参数已封存，HDL未完成/修复版时序待确认

用户本轮明确覆盖此前“关键HDL复核后才上板”的顺序：先准备单次实际采图的硬件计算闭环诊断。**用户授权板优先诊断、关键HDL未完成、时序待确认**。本轮只新增`tests/cnn_digits_diag/`、`tools/cnn_digits_diag/`及`sim/cnn/board_diag_20261016_a/`的软件/参考/证据，未改RTL/IP/PDS/成功固件，未开串口、HDL、Full Boot或PDS。用户须重新生成并下载包含最新片内RAM完整响应增加1拍、DVP首级FF I/O打包属性的新CNN位流，旧位流不能当本版；未收到该修复版时序通过确认，不记时序PASS。以下原时序/集成条目保留为历史。

固定BIN为`tests/cnn_digits_diag/build/diag_20261016_c/program.bin`，41940字节，装载/入口`0x40000000`，SHA256 `d08909dd14a5226c4a8ae58a6d07b8f3c7d31e46b4d66d6a9e9917a44153bff4`，Loader CRC `a608d0f6`。确定性非训练包`tests/cnn_digits_diag/model/diag_20261016_a/`：ID `05a032af`，6222个装载word，CRC `0ca5949e`，24888字节装载流SHA256 `fa210d89f4ef30a4f26e90f556f7ce3e351756df6f22f982b8081335da7fccfd`。6152个权重全非零且含正负，66个非零bias、合法shift `[5,5,4,0]`；包已编入BIN，无训练质量含义。

固件检查Camera/PP/CNN ID→装载并核模型数量/CRC/ID/VALID→实际采A/领取/STOP排空→PP→CNN核BUF/SEQ、864读拍、1024灰度字节、10个signed分数/argmax/周期→导出同一次实际DDR RGB96的27648字节。PP至导出完成不再START/CLEAR；A及可能的B尾帧全部按令牌领取/释放、账本核闭合。PC由实际RGB96按digits10合同生成灰度并执行完整整数CNN，逐项比10分数，不以类别或CRC代替。首败停止，无重传/自动重试；错误作业按原状态留证，不假报所有权闭环。

必要离线检查在`sim/cnn/board_diag_20261016_a/checks_02/review.json`：7种图案Python宽整数/C int64全部参考层字节与分数相等；实际固件C在原生设备模型下12场景，28个拒绝检查包含“同类别/错分数”、坏模型、超时、身份/计数、ACK、释放失败及合成证据不能冒充实板。交叉编译核RV32I指令、ELF/BIN一致、60KiB程序/BSS边界和368字节静态栈；原生模型不是真实CPU/RTL。首次构建a的缩进告警失败日志、后续b、checks_01均保留，最终只用c/checks_02。

封存`sim/cnn/board_diag_20261016_a/sealed_diag_20261016_c/`共97项输入；39项RTL及递归`csr_defs.vh`源码身份与最新时序修复收据一致（只读，不是完整厂家HDL执行包）。历史photo成功BIN/软件及实板证据哈希未变。准备收据`ready_review.json`状态为`SOFTWARE_READY_USER_BOARD_FIRST_TIMING_PENDING_NOT_HW_PASS`，`board_release.json`仅表示本轮用户授权诊断，不表示关键HDL/时序/实板通过。未例行复核PDS或位流身份。

用户生成并下载最新修复位流后，关闭串口助手；执行下列命令，按工具提示按下/释放KEY0、等DDR就绪，再Enter。COM9按实际端口替换，日志目录须不存在：

```powershell
Set-Location D:\riscv\RISCV
python tools/cnn_digits_diag/run.py --port COM9 --log-dir sim/cnn/board/diag_20261016_01
```

保留整个新目录，含完整RX/TX、固定BIN/参数副本、实际RGB/PNG、灰度、PC各层参考与10分数、板端分数、比较/错误日志。成功后工具自动原始字节回放复核；独立重核入口为`python tools/cnn_digits_diag/run.py --verify sim/cnn/board/diag_20261016_01`。见[诊断程序说明](../tests/cnn_digits_diag/README.md)。本次即使成功，最多证明该实际输入/诊断参数包整网10分数一致，不扩写为硬件逐层验证、全部异常/并发通过或真实数字识别成功。

## 2026-10-16：CNN首轮时序失败已定位，RAM响应寄存与DVP I/O打包修复A待用户重实现

本版用户报告主域setup WNS=-0.502ns/TNS=-44.856ns/242端点，camera_pclk=-0.314ns/-0.608ns/4端点。最差主路径是data_ram→CPU分支→inst_rom，DVP路径是camera_data→远处CLM中的din_q；未把CNN近零正裕量路径误判成setup失败。报告/43项输入保存在sim/cnn/timing_20261016_a/before及manifest，原失败证据不覆盖。

只修改soc_top（CNN启用时片内RAM完整响应寄存1拍，互连owner/写入行为保持）和ov5640_capture（现有10个DVP首级FF加厂商syn_useioff=1，保持采样边沿/延迟/复位），不改CPU核、CNN算术、PDS/IP/FDC/成功软件，不放宽时序约束。依据及协议审查见[ABI1第7节](cnn/数字CNN整网与SoC_ABI1_2026-10-16.md)。两配置静态展开exit0，启用仅DDR黑盒方向提示，receipt在sim/cnn/timing_20261016_a/review.json；未跑HDL/PDS/实板，无时序PASS。

下一步用户重新综合→映射→布局布线核时序，并确认DVP首级FF实际打包进I/O；若属性未生效或仍失败，回传本版报告继续定位。时序通过后Sol才准备/执行本版关键组，并补RAM响应增加1拍后的load依赖分支/store-read/复位最小覆盖，CPU流水线未改不跑历史全套。

## 2026-10-16：修复新增CNN的PDS文件条目格式，待用户重新打开工程

用户PDS报Flow-0130（原152行）/Flow-0121，尚未进入RTL编译。原接线脚本新增6个CNN `_file` 条目只有 `_format`，遗漏现有PDS条目的 `_timespec`；已按各源文件实际mtime补齐六项，并修正一次性生成脚本避免再生成缺字段条目。只读结构检查覆盖全部主设计源条目的格式/时间字段/路径，确认工程内容除此六项外完全不变。未改RTL、IP、FDC、固件，未启动PDS或仿真，不声称PDS解析/时序已通过。此前Icarus语法检查不覆盖PDS文件语法，此遗漏由本次用户解析失败揭示。

原失败工程与本次精确修改收据保存于sim/cnn/pds_format_fix_20261016_a/RISCV.before.pds及review.json；之前static_review.json保留原输入身份，不倒改。用户关闭后重新打开根RISCV.pds，再继续原本综合/实现流程。许可证“18天后到期”是另一个提示，不是本次源码条目解析错误。

## 2026-10-16：数字CNN整网/片内存储/SoC ABI1已接入，待用户本版PDS时序

按用户要求新增cnn_digits_engine/cnn_mmio，复用四个基础模块；两块2048字节激活RAM、6152字节权重及66个bias、4个shift实现Conv8/16/32→GAP16→FC10，输出signed分数/类别。CPU从0x10004000 MMIO装载6222个参数word并按数量/CRC提交模型；无有效模型不能START。CNN读DMA取PP输出864个256bit拍，串行适配32灰度；CPU+PP组与CNN增加外层整笔读仲裁，原CPU/相机/PP写路径不改。CNN busy期间PP START/CLEAR被硬件输出锁拒绝，取消需排空公开AR/R，读协议错保持锁至复位。详细[整网与SoC ABI1](cnn/数字CNN整网与SoC_ABI1_2026-10-16.md)为本版软件/测试接口。

主board_top启用CNN，RISCV.pds已列6个CNN文件；修改前39项源码/PDS/FDC保存在sim/cnn/integrated_20261016_a/baseline。原CPU、DDR桥/缓存、相机/FIFO/DDR IP、约束和成功固件保持。既有读仲裁增加PP_ID参数并阻止坏RID/RLAST拍交付，新增行为需本版关键测试，不继承旧PASS。

仅静态语法/展开与地址/身份核对：CNN完整模块、板级启用、CNN关闭PP启用、全关闭四配置exit0；板级-i忽略厂家黑盒，warnings原样保存，非厂商综合或功能测试。入口sim/cnn/integrated_20261016_a/review_static.py，收据static_review.json。未运行HDL/PDS/训练/实板，无本版功能、时序或识别准确率PASS。

下一步用户重开根RISCV.pds，重新综合/映射/布局布线检查本版时序与RAM/DSP映射；本对话未启动PDS。时序通过后Sol按ABI1准备固定参数包、逐层整数参考、MMIO装载/输出锁/读仲裁/取消与真实CPU关键组，DeepSeek依封存执行，复核后再给实板BIN。当前没有训练模型或可部署CNN测试软件，不直接上板识别，也不重跑历史CoreMark/720p长仿真。

## 2026-10-16：数字CNN四个基础RTL模块已实现，静态语法通过，未接整网或SoC

按用户“基础计算模块先实现”新增myriscv/cnn_rgb96_gray32.v、cnn_int8_mac.v、cnn_requantize.v、cnn_gap16.v。分别实现完整RGB96字节流选点/32灰度INT8、寄存乘法与INT32累加/溢出标记、33bit半值远离0重定标/ReLU裁剪、单通道16点平均。接口均可背压；适配检查最后字节与1024输出消费，MAC接受精确项数，结果保持到消费。说明及后续Sol关键测试要求见[基础模块接口](cnn/数字CNN基础模块RTL与接口_2026-10-16.md)。

四模块Icarus Verilog2005静态语法/展开exit0、无诊断，日志/身份在sim/cnn/base_20261016_a。未执行功能仿真/PDS/训练/实板，无新增功能或时序PASS。没有修改已有RTL/PDS/IP/FDC/成功软件；没有CNN整网、DMA串行器、片内存储、MMIO或PP输出锁，基础模块不可直接连接无RREADY的DDR返回。主PDS未加入未例化模块，重做当前主工程不能覆盖新模块时序，不要求用户此时重新生成旧位流。

下一步实现整网调度/存储及SoC连接，形成真实综合路径后用户PDS时序→Sol关键测试/DeepSeek执行及复核→实板。若用户选择提前独立时序，须提供单独有效综合顶层/时钟约束，不能以裁除逻辑的时序PASS代替。数据与训练仍按digits10合同并行，旧desktop4暂停。

## 2026-10-16：用户改为单字符数字识别，固定中央打印数字0–9，四分类暂停

用户按推荐确认：先单个数字，再英文和中文；第一版固定中央位置、白底黑字打印数字，板端RISC-V控制/FPGA CNN执行，4070电脑训练。新入口为[数字识别合同](cnn/单字符数字识别_INT8首版合同_2026-10-16.md)和[digits10机器合同](cnn/digits10_int8_v1.json)，旧desktop4合同保持但停止其采集/训练任务。

保留已成功PP输出96RGB888；计划在CNN读入端采样(3x+1,3y+1)，以(77R+150G+29B+128)>>8转灰度，再减128得到32×32 INT8。三层3×3/s2/p1卷积8/16/32→GAP除16→FC10，总6152字节权重、264字节bias、166208 MAC，两个2048字节激活bank。量化F仍待训练；没有数字模型、CNN/输入适配RTL或新MMIO ABI。固定位置分类不提供自动定位/检测框，不宣称空白/未知拒识。

本轮仅新合同、拓扑静态核算及入口更新，未修改RTL/PDS/IP/成功程序，未运行HDL/训练/上板，无新增功能PASS。下一步Sol依新合同准备仅导实际RGB96的批量采集软件及32灰度预览/训练导出/独立参考；用户准备0–9数字卡，每类约100张分5个独立session按60/20/20训练/验证/测试划分。本对话后续实施适配及计算核，再接MMIO/读仲裁/PP输出持有锁；新增RTL仍先由用户检查PDS时序。此条不自动向其他对话派发任务。

## 2026-10-16：进入四分类CNN，首版网络及INT8合同已固定，尚未实现CNN RTL或训练模型

用户接受推荐并指示“执行”：固定手机/书本/水杯/鼠标四件实物，一个目标居中，首版仅验收四类有效输入，目标1次分类/秒，串口输出四个分数及耗时。入口为[四分类CNN合同](cnn/四分类CNN_INT8首版合同_2026-10-16.md)及[机器可读网络](cnn/desktop4_int8_v1.json)。沿用已成功96×96 RGB888预处理，CNN入口做u8减128；三层3×3/s2/p1普通卷积8/16/32通道→GAP→FC4，6104字节权重、240字节bias、1824896 MAC。signed INT8权重/激活、INT32累加、逐层幂二尺度、半值远离0舍入、精确GAP除144，详细布局/溢出/输出分数口径已定义。量化F参数等待训练/校准，不填假权重。

本轮仅设计合同及拓扑参数，不修改myriscv/PDS/IP/FDC/成功软件，不运行HDL或板级，不需要用户本轮重新PDS。后续RTL方案为复用乘加核、片内中间张量/参数、CNN只读PP输出；必须新增硬件PP输出持有锁与读仲裁，当前尚未实现。CNN MMIO仅候选0x10004000，未译码，无可访问ABI。旧2026-10-10方案地址/DDR/缓存描述不再适用。

下一步Sol按合同准备仅导出实际96RGB888的批量采集工具、训练/导出及独立整数参考（不覆盖成功单张工具）；用户每类约200张、5个独立session，按session隔离120/40/40训练/验证/测试。本对话随后实施计算核及集成；新增RTL仍按用户PDS时序→关键测试/原证据复核→实板顺序。无自动跨对话消息，无训练或CNN PASS；预处理单张实板成功及其未覆盖范围保持下方原结论。

## 2026-10-15：新拍单张预处理实板逐字节验收通过，96RGB888实际输出与独立参考完全一致

用户回报“成功”，实际目录`sim/camera_preprocess/board/photo_20261015_01/`已写回。Sol执行`python tools/camera_preprocess_photo/run.py --verify sim/camera_preprocess/board/photo_20261015_01`，原始Loader/RX/TX、1829包及ACK/摘要/释放账本/结束、独立源参考与PNG像素全部通过，与原verified一致；再用[独立复核脚本](../sim/camera_preprocess/board_first_20261015_a/review_board_photo.py)直接从导出源按整数公式重算27648字节。[正式实板收据](../sim/camera_preprocess/board/photo_20261015_01/sol_review.json) SHA **7a42f95eeec35710961cb2a58fb574e8707ae583d2774fe7f353b18e94a770c5**，状态 **CAMERA_PREPROCESS_SINGLE_PHOTO_BOARD_BYTE_ACCEPTANCE_PASS**。原14个日志/镜像/结果/图片文件保持，不修改原result/verified中的VISUAL_PENDING；30项本轮固定软件/审计输入、固定ELF/BIN/C/PC工具及放行身份匹配，未改RTL/PDS或重新开串口。

真实Camera ABI2/PP ID分别43414d02/50525001，SENSOR_ID5640、CONFIG=OK。本次新拍 **A/SEQ1**，原始源1280×720 RGB565/921600像素/1843200字节/57600拍；源capture/CPU/PC CRC一致为 **cddc099b**。PP输出42000000，96×96 RGB888/HWC、**27648/27648字节与PC从同一完整源生成的期望相等，首不匹配null**；CPU整数参考逐字节比较、CPU输出复读、硬件和PC输出CRC全部为 **1ee57037**。源采样首(283,3)/末(996,716)，位复制展开；实际864个输出写拍、9216个源读拍、27648个已产生字节和源BUF/SEQ经固件核对，ERROR=0。CPU独立DDR输出确实经UART回传，actual96.png来自actual.rgb，未用CPU重算图冒充硬件结果。

实际159个Loader应答、整BIN VERIFY/唯一RUN、G/C/D/Q各一次；1800个源DATA包、27个RGB888 DATA包和两个END，共1829包均有唯一ACK，无重传。原始RX **1939459字节**、TX **24529字节**。固定BIN仍19780字节/SHA8a7b1c57…bb7b3、manifest1255f078…38f5。源在导出期间保持领取；结束CLAIMS2/DISCARDS1/GLOBAL_SEQ2，表示目标A/SEQ1及非选B/SEQ2均已正确领取释放，CAM_STATE=00000130的SELECT/残留ACTIVE_BUF/DUAL_MODE合法，两块FREE且流停，PP_STATUS=00000002，最终session CPU_CHECK=PASS。

PP CYCLES=**303844**，按93.75MHz约 **3.241003ms**，这是本作业硬件busy计数的处理时间。释放行ELAPSED_TICKS=16287277984，约 **173.730965秒**，包括启动、CPU参考/CRC、完整原图与结果的UART导出等，不能当成预处理延迟；64bit软件计时覆盖了32bit回绕。全图UART传输是本次交互耗时主体，不需据此改预处理RTL。Sol已查看source.png及actual96.png：缩略图显示同一桌面和白/绿魔方的中心裁剪区域，actual96.png与expected96.png文件及解码像素均一致；用户只回报“成功”，未另声称用户已逐图人工确认。

**已证明这一张真实相机图像经DDR源→硬件裁剪/缩放/展开→DDR输出→CPU→UART→PC逐字节闭环正确。** 本次不追加重复上板、PDS或长仿真，无明确RTL反例。范围仅单次A源正常通路，不扩写为B源重复作业、源锁提前RELEASE拒绝、三方仲裁压力、ABORT/协议错误排空或最终W/DONE逐周期验证；这些关键HDL尚未在本轮完成。此前软件native/时序/双缓冲成功证据各自保留，不冒充新增Full Boot/PHY；CNN/INT8仍另阶段。下方“待用户单张实板”为当时准备记录，以本条续接。

## 2026-10-15：用户改为先上板新拍一张；独立单张预处理程序与PC逐字节/导图工具已固定，待用户执行

用户明确要求“先上板吧”，同意新拍一张，并指示“执行,准备上板”，覆盖此前等待关键仿真才放行实板的顺序。本次由Sol直接实现并检查**软件**，不等待DeepSeek/HDL关键组，不改RTL/IP/PDS/成功BIN，不打开串口；不把板优先放行命名为关键测试PASS。当前预处理位流/时序以用户确认继续使用，无再次PDS或位流审查。原关键组任务及已有两组软件准备完整保留，不消息其他对话。

[单张程序与说明](../tests/camera_preprocess_photo/README.md)、[PC工具](../tools/camera_preprocess_photo/run.py)。从已有两组准备只读复制到新目录，改为**一次新拍A/SEQ1**，真实Camera发布→CPU领取→STOP并排空在途B→PP START→元数据/27648字节CPU独立参考比较/输出复读CRC/整个源帧CRC→同源保持CPU拥有直到源/结果导出结束→释放A、正确领取/释放未选B→账本闭合和流停两块FREE。修复测试侧空闲mask：ACTIVE_BUF即使空闲也可保留B，检查FREE/流停使用0x2cf，忽略SELECT/ACTIVE_BUF/DUAL_MODE，未放宽所有权/忙/流/等待或错误条件；原两组源码保持。程序诊断含首不匹配坐标/通道/期望和实际、源坐标；失败停，无重传/重新采集/自动ABORT清错。

最终固定 `tests/camera_preprocess_photo/build/photo_20261015_d/program.bin`：**19780字节**，SHA **8a7b1c57cce723753ff73fd6c62dd8f8a099d4f1522902bbb3bb0b4a933bb7b3**，Loader CRC **ac263d07**；manifest SHA **1255f0788b0de78a195fe3eea69b366a89322c2746fa2662c6c09ae577d038f5**。RV32I ELF/指令/段/独立4KiB栈检查通过，考虑failing已置1禁止错误诊断递归的保守栈上界400字节，.su与反汇编一致；DAT为同BIN表达，不改ROM/RAM初始化。固定BIN不重建。复用旧Loader的159个应答、整BIN VERIFY和唯一RUN，应用发G/C/D/Q各一次，1829个有效PP01包各ACK一次。

[软件检查](../sim/camera_preprocess/board_first_20261015_a/checks_d/review.json) SHA **afce2d6b0dc5b1a8cbb7cae4c82cb2c04a944e10d3d61112e960e6669302ee37**：13个实际main.c及参考/CRC函数的native MMIO/UART模型场景，含纯红/绿/蓝/非对称坐标完整导出、B尾帧残留ACTIVE_BUF与无尾帧、错误/超时/元数据/源或PP CRC/逐字节错误/坏ACK/释放失败；无失败后第二次STREAM_START/PP START，64bit ticks跨32bit回绕。实际C产生的完整收发经PC工具碎片读重放、PNG像素/全部27648字节/CRC/包与结束检查通过；11个负例含错误包头/内容/序号/偏移/长度/ACK/短读/错误摘要、合成数据冒充实板及**构造CRC碰撞但字节不等**全部拒收。**native模型不是RTL、真实CPU HDL或实板PASS**。初次build a调用图未处理已有防递归guard而中止；checks_a测试夹具MinGW编译错误、checks_b错误诊断期待字串失配保持，修软件检查后checks_c/d通过，b/c中间构建保持，最终d。

[板优先软件放行收据](../sim/camera_preprocess/board_first_20261015_a/ready_review.json) SHA **13e741576ddfbc21ab0ab373e43d0c7e8a981806d4432136bd7be3e703586f1b**，状态 **PHOTO_SOFTWARE_REVIEW_PASS_BOARD_FIRST_READY_NOT_HARDWARE_PASS**。30项固定软件/参考/输入/审计文件复制到`sealed_photo_20261015_d/project/`，80项本轮软件原始证据有哈希；208项设计、122项历史保护及8项原两组准备身份保持。新门文件`sim/camera_preprocess/board_first_20261015_a/board_release.json`明确记 **SOL_SOFTWARE_REVIEWED_USER_AUTHORIZED_BOARD_FIRST** 和HDL未跑，绑定上述BIN与收据，不伪造SOL_KEY_REVIEW_PASS。原关键组board_release未创建。

用户关闭串口助手，使用当前含PP ID50525001的预处理位流，从根目录执行（COM9按实际端口替换）：

```powershell
python tools/camera_preprocess_photo/run.py --port COM9 --log-dir sim/camera_preprocess/board/photo_20261015_01
```

新日志目录执行前不存在。按工具提示按KEY0后释放、等DDR就绪，摆好**新的画面**后Enter；工具自动装载、只新拍一次。UART二进制传回源RGB565 **1843200字节**和实际DDR RGB888 **27648字节**，115200/8N1净数据理论162.4秒，另有包头/ACK和CPU开销，约3分钟或更久；整组成对导出600秒上限。PC从原始源按中心采样/位复制生成expected，不以CRC代替逐字节比较。保留source.rgb565/actual.rgb/expected.rgb、source.png/actual96.png/expected96.png、comparison.json、完整原始RX/TX及Loader/包ledger/释放终态/result/verified、固定BIN/manifest和放行文件。实际RGB888 PNG只来自actual.rgb；全字节/CRC数据通过后人工看图仍PENDING。

完成或失败回传整个新目录，并查看source.png与actual96.png；首败目录不覆盖、不自动重试。离线复核命令`python tools/camera_preprocess_photo/run.py --verify sim/camera_preprocess/board/photo_20261015_01`只读重放，不开串口。当前**实板/RTL功能尚未验收**；本次单张正常通路不扩写为A/B连续复用、周期级仲裁、最后W/DONE或ABORT/读协议异常全面覆盖。旧单/双缓冲成功证据、PDS通过和本轮软件通过是各自独立事实；CNN/INT8未接入，CPU性能优化仍暂停。下方双组准备与先仿真计划为历史状态，由本条用户板优先指令续接。

## 2026-10-15：用户确认预处理本版PDS时序通过；Sol已固定设计身份并给DeepSeek逐字节/串口验收实施方案

用户在本对话明确答复 **“已通过，可准备封存与执行”**，覆盖下方等待时序状态；Sol未启动PDS或复审当前PDS/位流。按新版AGENTS分工，Sol写方案、身份、参考规则及严格判据，DeepSeek依方案实现TB/模型/独立参考/CPU程序/PC工具/封存runner并执行，Sol收原始证据后复核；本条不自动发跨对话消息。

唯一[DeepSeek实施与执行任务](../DeepSeek/预处理96RGB888_逐字节参考与串口导图测试_2026-10-15.md)。[Sol设计输入清单](../sim/camera_preprocess/plan_20261015_a/design_inputs.json) SHA **a21f061174e2e0bb1a56a25177c96e6de274d68455f273a7e8adfba6eeed5125**：208项活动设计/RTL/IP/include/初始化及同身份design_snapshot，15项合同/任务/软件参考依赖，122项单/双缓冲成功证据及预处理前像保护。10项新增/改变myriscv源码与Astra静态收据逐项相符；原双缓冲101帧实板收据仍538ddaaa…6e5c9，原始7文件保持。这个清单是设计开发输入身份，**不是还未生成的最终测试封存清单**；未构建预处理串口BIN、未执行功能仿真/串口，无新增功能/实板PASS。

DeepSeek先读上述任务并从根目录执行只读核对：

```powershell
python sim/camera_preprocess/plan_20261015_a/check_design_inputs.py
```

然后按任务在新`sim/camera_preprocess/key_20261015_a/`、`tests/camera_preprocess_uart/`、`tools/camera_preprocess_uart/`实现代码与静态/离线检查，登记最终全部输入/工具/SHA并封存，再从运行副本执行 **unit→独立检查→soc→独立检查**。新运行目录固定`sim/camera_preprocess/key_20261015_a/build/ds_pp_key_20261015_a/`，当前不存在；unit300秒/soc600秒/检查120秒墙钟，首败停、禁止自动延时重试。必须封入递归include、*_init_param.v、实际初始化、厂家原语及GRS；不重跑720p长CPU采帧/CoreMark/ISA/PHY。最终清单SHA/完整命令/退出码/超时/Warnings原样、总线与CPU原始轨迹/独立checked和evidence_sha256交Sol，成功仍PENDING_SOL_REVIEW，不提前开串口或建board_release。

参考固定中心720方形→96×96、整数中心采样、RGB565位复制展开，27648字节逐字节核对；五个unit作业含纯RGB及非对称坐标图，真实CPU至少A/B/A重复同一输出地址，CPU每次完整读6912字做CRC，参考从输入生成。新增读仲裁/两层写仲裁、源锁/提前释放拒绝、no-hit/no-fill/权限、AR/R及AW/W同拍/分离、背压、最终实际W后DONE、ABORT/超时/协议错误隔离与排空均要求原始触发。为控制时长，CPU组可用明确标记Camera MMIO/所有权模型和预置全尺寸源，实际Camera external_hold最小集成另在unit验证；不宣称完整DVP/board_top/PHY仿真，生产连接需逐项静态核对。

实板工具准备为两组成对导出（选A、B，独立stream，中间用户改变画面）：每组完整**1843200字节源RGB565＋27648字节实际DDR RGB888**，同一BUF/SEQ源持有到导出结束，CPU整数参考/输出/复读与硬件CRC闭合，PC从完整源按公式生成expected.rgb与actual.rgb逐字节核对，保存source/actual/expected PNG和原始RX/TX/包ledger；不只导出CPU重算缩略图。1024字节分块/无重传，理论每组约163秒起，不逐字节HDL模拟串口。所有非目标/STOP尾帧显式领取/释放并记DISCARD，不能误用旧帧。无CNN/INT8、不新增100帧阶段，图像人工查看另计；关键原始证据经Sol复核后才给固定BIN、用户串口命令、新目录及KEY0步骤。原合同/静态文档中的等待时序和未有软件状态属于其建立时点，由本条续接，不修改已固定合同身份。

## 2026-10-15：96×96 RGB888预处理RTL已接入，等待用户本版PDS时序

用户确认中心720×720裁剪、最近邻96×96、RGB888/HWC输出独立DDR，首版不含CNN/INT8量化。现已在主RTL接入预处理MMIO与读DMA、CPU/预处理完整读事务仲裁，复用现有写仲裁增加外层PP写主机；新增两文件已列入RISCV.pds设计/仿真源表。CPU CLAIM源A/B后PP核序号并锁住源，处理期间Camera RELEASE拒绝；输出固定0x42000000、27648字节，最后实际W后才DONE，CPU输出区无缓存/不可执行/不可写，busy或失败时不可读。

合同与Sol交接见[96RGB888预处理阶段](camera/OV5640预处理96RGB888与DDR接口_2026-10-15.md)。MMIO0x10003000–0x1000303f、ID50525001；坐标`sx=280+floor((2*x+1)*15/4)`、`sy=floor((2*y+1)*15/4)`，RGB565位复制展开；9216笔原生读/864笔整拍写，带输出CRC及原源SEQ。训练脚本必须按同一公式，不能假定默认nearest一致。

[修改前双缓冲源码](../sim/camera_preprocess/baseline_double_20261015/manifest.json)保存34项与实板收据身份；[静态审查清单](../sim/camera_preprocess/static_20261015_a/review.json)核9项已有文件修改、2项新增RTL、25项前像保持，包括有效FDC。CPU核、SCCB/DVP、FIFO、DDR IP及原成功软件未改，无新DSP/IP/时钟约束。Icarus null部分展开启用/禁用两配置退出0，启用组仅未展开DDR黑盒方向警告。**没有执行HDL/PDS/实板，没有本版功能或时序PASS**；双缓冲既有成功结论仍仅对应旧版本。

下一步用户重新打开根RISCV.pds，重新综合→映射→布局布线→时序报告；新增DDR返回路由必须用本版结果确认。时序通过后Sol准备一组采样/打包/权限/并发/异常/真实CPU小程序关键测试，DeepSeek仅执行，再交串口RGB888导图验收。当前没有预处理串口BIN/采集工具，不自动发跨对话消息、不启动历史720p长仿真或CoreMark/ISA/PHY全套。

## 2026-10-15：ABI2双缓冲720p100帧实板原始复核通过；CPU整帧读取与CRC成为主要耗时

用户写回`sim/camera_double/board/abi2_100_20261015_01/`。Sol执行`python tools/camera_uart/double100.py --verify sim/camera_double/board/abi2_100_20261015_01`，逐字节重放原始Loader/RX/TX、应用摘要/结束、CSV及ledger，与原verified完全一致；另由[复核脚本](../sim/camera_double/review_board100_20261015.py)独立重算CSV与原始结束行的各项耗时。[实板收据](../sim/camera_double/board/abi2_100_20261015_01/sol_review.json) SHA **538ddaaa51acffd68c2dc2dd4f743857c5a9ecf0aa83b589faeca3a58a26e5c9**，正式结论 **CAMERA_ABI2_DOUBLE100_BOARD_DATA_ACCEPTANCE_PASS**。固定BIN12520字节/SHA4684f077…ed4d2、manifest 3b4963b6…ae87f、ELF/C源/串口工具及放行收据身份匹配；B清单中除RISCV.pds外328项相关输入和79项历史保护保持，按用户要求未复审PDS/位流。原7个实板日志/镜像/报告文件保持，未改RTL/IP/程序或开启串口/HDL/PDS。

实际ABI ID=43414d02、SENSOR_ID=5640、CONFIG=OK。101个Loader应答含整BIN VERIFY、唯一RUN后只发一个G，无重试。正式帧 **SEQ1..100、A/B各50次**，加STOP已在途尾帧 **A/SEQ101**；**101/101采集CRC与CPU整帧CRC一致**，全部ERROR=00000000。CRC首d3aeb582、正式末f60f77e7、尾d84d8a8d，101个均不同；相同CRC也合法，CRC变化本身不单独证明用户主动改画面。按固定固件的元数据/所有权/稳定性检查，每帧921600像素/1843200字节/57600个256bit写拍；累计CPU检查186163200字节/46540800字。DB_END仅在流停、两块FREE及GLOBAL_SEQ与最后释放SEQ闭合后打印PASS，SUCCESS100/TAIL1是预期的STOP排空行为，尾帧没有误计正式100帧。

| 实测指标 | 原单缓冲100帧 | 本次双缓冲100帧＋1尾帧 |
|---|---:|---:|
| 软件记录总耗时 | 114.613935s | **44.453988s** |
| 正式帧平均采集等待 | 702.201935ms | **7.588462ms**（首帧占主要部分） |
| 正式帧平均CPU读取＋CRC | 432.845087ms | **420.008233ms** |
| 正式校验完成率 | 0.872494帧/s | **2.249517帧/s** |

总耗时减少 **61.214%**、正式100帧完成率约为原来的 **2.578倍**；本次还完整处理了1个尾帧，软件流程不同，不作为隔离DDR/CPU基准。首帧等待 **758.164ms**，后99帧只需 **6.773–9.259μs，均值6.886μs**：它们被CPU领取时已经READY，不能理解为相机几微秒采一帧。同流后续不再重复丢10个启动帧，采集与CPU处理可流水推进，这与等待显著减少一致。逐周期另一块DMA与CPU读交织继续依据已复核关键仿真，串口摘要本身没有原生总线轨迹。

正式100帧CPU读取＋CRC合计 **42.000823s，占总耗时94.482%**，每帧419.997227–420.018240ms，四个连续25帧分组均值420.007232/420.008648/420.009073/420.007979ms，无持续变慢。尾帧读取＋CRC419.925ms，其余元数据/打印/循环等约1.274386s；读取加CRC有效约 **4.388MB/s**，不是裸DDR带宽。WAIT_FREE累计 **3139302550周期/33.485894s**、未饱和；它与CPU处理时间重叠，是两块占满时等待软件释放的正常背压，不能额外加到总耗时，也不按错误或被覆盖的帧数解读。当前瓶颈已由重复采集预热等待转为CPU整帧读取＋CRC；没有明确RTL缺陷，本轮正常通路实板验收完成，无需重做PDS或重复长仿真，CPU性能优化仍暂停。

本轮未导出原始图像、未做PC整帧CRC或新的人工看图验收；此前单缓冲两帧图片成功证据保留，不扩写为本版导图PASS。完整720p实板结果与小尺寸异常/所有权/并发关键仿真共同支撑本阶段验收；不新增Full Boot、PHY、任意压力测试或PDS独立审查PASS。下方“待用户实板”和门文件中的NOT_RUN是当时放行状态，保持历史身份，由本条续接。

## 2026-10-15：ABI2关键测试原始复核通过，放行固定720p双缓冲100帧程序，待用户实板

用户回报“全部通过”，Sol复核B运行`sim/camera_double/key_20261016_b/build/ds_abi2_soc_resume_20261016_b/`，并只读重放其冻结副本内A的unit原始轨迹。[复核收据](../sim/camera_double/key_20261016_b/review_b/review.json) SHA **479fe75a42cb77785d56698771f90c2cef0d839a3a37803f0a4495bb77eefacd**，结论 **ABI2_KEY_RAW_REVIEW_PASS_BOARD_PROGRAM_RELEASED_BOARD_NOT_RUN**；[复核脚本](../sim/camera_double/key_20261016_b/review_b.py)。B清单 SHA **5e262312b626ea8473db910f0372297ae79a3fc0321dd22a8fe30fc1415ce61a**，329项活动/封存/运行三份输入、79项历史保护、厂家/工具/INI/递归include/GRS、运行后身份、Git前后及全部原始证据哈希一致。仅新增复核收据、放行文件与本交接条目，未改RTL/IP/PDS、固件、测试、冻结输入或原运行证据。目录名20261016沿用已封存身份；本条采用当前America/Denver日期。

unit复用原8次发布、19非法MMIO应答、132项译码权限和8类异常/STOP/ABORT/占满/复位场景，独立原始检查通过。A首败是发布后异步复位导致dropped=0的检查器期望错误，原失败目录仍为 **STOPPED_FIRST_FAILURE**，没有倒填或改成PASS；B保持外部首次11/后续1帧起点及全部数据/所有权/时序判据。原阶段文档、A/B README及下方待执行条目是冻结时点记录，以本条为当前结论，不重复运行已有目录。

B五个命令unit_recheck/vlib/compile/soc/soc_check均native0且未超时。编译54模块Errors0/Warnings0；SoC仿真实耗 **202.2233s**，Errors0/Warnings30（3017×2、3722×28，为未使用顶层观察/物理输出和DDR延时输出，保留原日志）。真实CPU完成 **A/B/A/B/A、SEQ1..5**，每帧256字整读及对应256次原生AR/R全部逐字匹配输入公式参考，CRC依次 **c351bc7c/e868aa8b/3235a3e8/1f3b833c/496de9da**。160个CPU压力写及其数据正确；18次相机实际W位于另一缓冲CPU原生AR/R之间，6904周期CPU/相机AW同时请求，同拍/分离AW/W均触发。两块占满60974周期无相机覆盖，真实UART令牌触发中途释放后恢复完整帧；最后STOP在途第5帧也整帧校验并释放，最终两块FREE、流停。5次发布全部严格晚于最后实际W（间隔1/7746/1/1/1周期）；16条真实启动退休指令与固定小BIN/DAT吻合，无CPU trap。独立参考仍由DVP输入图案公式生成，不从DUT写数据推导。

已创建[Sol实板放行文件](../sim/camera_double/key_20261016_a/board_release.json)，绑定上述B清单/收据及固定完整程序`tests/camera_double100/build/abi2_20261016_d/program.bin`：**12520字节**、SHA **4684f0775e3a611588b0ea5df373dbf5b3d6ce94deda175d6c62a0dda72ed4d2**、Loader CRC **0901d151**、manifest SHA **3b4963b69ed057d9d1f0dcd8d1779da0f2fc2dbc49270d4664660807296ae87f**。完整720p100与小尺寸4帧程序同一C源，已核两份ELF/BIN/源身份及小DAT逐字对应；完整BIN不重建。**本轮关键功能已通过，完整720p双缓冲实板尚待；未新增Full Boot、PHY或PDS独立审查PASS。** 不重跑7200秒或历史全套。

用户沿用当前已确认时序正确的ABI2位流，无需重新PDS；关闭串口助手，从工程根目录执行（COM9按实际端口替换）：

```powershell
python tools/camera_uart/double100.py --port COM9 --log-dir sim/camera_double/board/abi2_100_20261015_01
```

这是新的日志目录，执行前不存在。程序提示后按KEY0并释放，等待DDR就绪后按Enter；运行期间主动遮挡镜头/改变画面。工具装载上述固定BIN，完整Loader VERIFY和唯一RUN后只发一个G；1280×720、每帧921600像素/1843200字节/57600拍保持。连续校验100帧，逐帧只打印缓冲号/序号/CRC比较/错误/耗时，不导图、不自动重试，相同CRC合法。第100次领取后STOP，已在途尾帧最多1个也校验/释放，单列TAIL，不计SUCCESS100；结束要求两块FREE、序号闭合、流停。运行完成或失败回传整个新目录及改画面反馈；保留原始RX/TX、CSV、固定BIN/manifest和result/verified。失败保留首败，不在同一目录重跑；明确RTL反例才整理最小证据交Astra。串口摘要本身不证明逐周期并发，相关结论来自上述关键仿真。

## 2026-10-16：ABI2 A首败为发布后dropped取样期望错误；unit原始复核通过，封存B仅续未跑SoC

已复核`sim/camera_double/key_20261016_a/build/ds_abi2_key_20261016_a/`：[Sol收据](../sim/camera_double/key_20261016_b/review_a/review.json)SHA **686231a7b9628d6bbc8a7fe2b3de45d0a43f020f5411108015c72d4647f1ae98**。A清单639c6ace…fda7a的308项活动/封存/运行三份输入、58历史保护、厂家/工具/INI/原始证据哈希与Git前后全部一致。vlib/compile native0，54模块/Errors0/Warnings0；unit native0、12.7170516秒、Errors0/Warnings40（3017×3、3722×37，原样保留）；unit_check native1且未超时，无soc命令。A原result/异常堆栈/日志/清单和封存保持 **STOPPED_FIRST_FAILURE**，不补写旧checked.json或修改原报告。

这是Sol检查器错误，并非已证实RTL反例：发布边沿`camera_mmio.busy<=0`，使`capture_resetn=resetn&&busy`立即异步复位`wr_reset_pipe`和采集器；TB在`#0.001`之后取样的内部`dropped`已经是0，原checker误期待预热结束的10。首PUB cycle724182/A/SEQ1/CRC **e9ee1be4**，最后实际W724173，前面实有11个外部VSYNC起点，全部512拍地址/字节正确。新checker明确要求发布后dropped=0，同时完整保留首11/后1外部EDGE判据；soc的同一后取样字段一并修正。数据、CRC、最后W后发布、所有权、权限、并发和所有超时判据不改、不放宽，RTL/TB/模型/程序/采集参数均不改，无需重新PDS。

用新检查器只读重放A完整unit原证据：**8次正常发布**、SEQ1..8、19非法MMIO应答、132权限/地址检查、15个DVP帧及STOP/ABORT/占满/短帧/overflow/缺PCLK/CPU＋WRITING复位全部通过，成功发布起点数为 **11/1/1/1/11/11/11/11**。对缺预热边界、错误发布后dropped、错CRC、发布不晚于W、损坏DMA字节5个构造反例均拒收。unit已覆盖范围可复用；**不改A首败为PASS，也没有SoC/整体ABI2、实板、Full Boot或PHY PASS**。

新唯一[DeepSeek仅SoC续测任务](../DeepSeek/双缓冲ABI2_发布后计数检查修复_仅SoC续测_2026-10-16.md)。B清单`sim/camera_double/key_20261016_b/inputs.json` SHA **5e262312b626ea8473db910f0372297ae79a3fc0321dd22a8fe30fc1415ce61a**，329工程/参考/复用原始输入，79历史/原失败保护项，封存`sealed_20261016_b/`。唯一新运行目录`build/ds_abi2_soc_resume_20261016_b/`尚未创建，check-inputs/plan-only已通过，递归include/GRS/厂家/副本闭合。固定两份CPU程序身份和原48源54模块、5include不变。入口：

```powershell
python sim/camera_double/key_20261016_b/run.py --check-inputs
python sim/camera_double/key_20261016_b/run.py
```

顺序仅 **unit_recheck（B冻结副本内复用A原轨迹，结果写B新目录）→vlib→compile→soc→soc_check**，不重跑unit HDL/7200秒/历史全套。soc仍限300秒、检查器120秒；首败保留完整新目录、命令/native/Errors/Warnings/超时/轨迹与独立结果。测试问题交Sol新身份修复，明确RTL才给最小复现；不自动发消息。**继续不给用户实板命令，不创建board_release.json、不打开double100串口。** 原阶段文档及A任务属于冻结输入，保持原文字，当前正式结论由本条及B组README续接。

## 2026-10-16：用户确认双缓冲位流/时序正确；ABI2关键组与CPU程序已封存，待DeepSeek仅执行

用户本轮明确确认本版比特流已生成且时序正确，要求无需再次核对PDS/位流。Sol按此进入测试准备，未启动PDS或读取/复审时序、位流；不补写WNS/位流哈希。当前RTL/IP/约束、单缓冲源码前像、两份成功BIN及全部历史原始证据保持，ABI ID=43414d02、A=41000000/B=41200000，未修改设计或判据，不继承单缓冲PASS。

唯一[DeepSeek任务](../DeepSeek/双缓冲ABI2_精简关键测试_2026-10-16.md)，[组内范围/证据](../sim/camera_double/key_20261016_a/README.md)。固定清单`sim/camera_double/key_20261016_a/inputs.json` SHA **639c6ace530086754a673e65e90d2c9fe59119f10223a87417658c59c40fda7a**：308项工程/程序/模型/输入图案/检查器/参考与准备证据，48编译源、54模块含3厂家原语，5条递归include边（CSR头×2、ROM/RAM初始化参数、DDR模型header），两个顶层各有GTP_GRS GRS_INST，初始化DAT也保留；工具/私有INI与历史保护哈希另登记。封存`sealed_20261016_a/`，新运行目录`build/ds_abi2_key_20261016_a/`**尚未创建**。只读check-inputs/plan-only已通过，递归依赖和副本/活动输入一致。执行入口：

```powershell
python sim/camera_double/key_20261016_a/run.py --check-inputs
python sim/camera_double/key_20261016_a/run.py
```

只做vlib→compile→unit→unit_check→soc→soc_check。unit64×128/512拍、8次正常发布，覆盖token/领取释放/非法MMIO无副作用、132项真实译码边界/权限、占满3帧不覆盖/WAIT/中途释放完整帧恢复、同沿发布释放另一块、STOP分配竞争与扣最后W排空、ABORT保持另一CPU块且排空公开AW/W、短帧/自然overflow/缺PCLK、CPU＋WRITING全局复位。soc64×8/32拍，同一份真实CPU C目标4次发布/校验，若STOP已分配额外尾帧则第5次也校验；A/B均复用同址、每帧256次完整CPU字读及原生AR/R、独立逐字/逐拍CRC/地址/strobe、最后W后READY，必须实际看到另一块W落在CPU块AR/R间、真实CPU/相机AW竞争和背压/同拍/分离。外部真实UART RX令牌同步场景，避免外部更新DDR邮箱被Cache误读；行间空白加长只是刺激，不改几何或DUT。无force/伪CPU/缓存清空，golden由输入图案生成，不从DUT写数据反推。首次丢10、后续不重复丢需核DVP边界原证据。

[ABI2软件说明](../tests/camera_double100/README.md)：固定完整720p100帧BIN `tests/camera_double100/build/abi2_20261016_d/program.bin` **12520字节**、SHA **4684f0775e3a611588b0ea5df373dbf5b3d6ce94deda175d6c62a0dda72ed4d2**、Loader CRC **0901d151**；小尺寸同源C `abi2_small_20261016_d/program.bin` **4680字节**、SHA **f46e564f5e85cfb19b856f2b5458718d1d02120cad965efcad9e1a5b91dc8dd0**、CRC8eefbc51。完整程序SELECT/SEQ/TOKEN/CLAIM→逐帧元数据及整帧CPU CRC→恢复SELECT/TOKEN/RELEASE，允许另一块BUSY；只打印BUFFER/SEQ/CRC/错误/等待和读取时间，不导图，不以相同CRC判旧帧。第100次CLAIM后STOP，对可能在途的尾帧完整CRC/释放并单独TAIL计数，再要求流停且两块FREE；失败即停保留诊断，不自动重试/清错/ABORT。串口工具`tools/camera_uart/double100.py`已准备，Loader101应答/VERIFY/唯一RUN/单G，保存原始RX/TX/CSV/固定身份。**待关键测试原始证据经Sol复核通过，才给用户实板命令**；工具打开串口前有绑定该BIN的Sol放行文件门，当前不存在，不由DeepSeek创建。

[准备收据](../sim/camera_double/key_20261016_a/preparation/ready_review.json)：最终ModelSim完整静态编译Errors0/Warnings0（static_f），RV32I ELF/BIN/段/栈审计、17个输入图案及串口正反/统计/原始RX拒收检查通过（offline_b），合成数据不冒充实板。初次C构建a的Werror缩进、初次模型静态编译a的字面量/问号语法错误保持原日志，仅修测试；b/c中间构建保留，最终d。Icarus全厂家IPnull展开因既有无定宽拼接失败，未改IP；忽略未展开IP的SoC空展开退出0，只作层级检查。**Sol未run vsim/vvp或功能仿真、未串口/实板；当前是PREPARED/SEALED，尚无ABI2功能/Full Boot/实板PASS。** 不重跑7200秒SoC、CoreMark、ISA或PHY，CNN不在本轮。

DeepSeek从副本运行，功能job各300秒、检查器120秒；不构建、不重封、不延时，不修改测试/RTL/成功输入、不删warning；首败保持整个新目录，原始unit.log/cpu.log/bus.log、每job DVP、完整命令/native退出码/Errors/Warnings/超时/耗时/stdout/transcript、独立checked.json、Git前后/输入身份/副本及evidence_sha256齐交。runner成功仍PENDING_SOL_REVIEW，不等于实板；失败由Sol分类，测试问题新身份修复，明确RTL问题整理最小复现及原证据交回。本任务不自动消息其他对话。

## 2026-10-15：双缓冲RTL/ABI2已接入，等待用户重新PDS实现

用户在单缓冲100帧成功后授权执行双缓冲。本版在主camera_mmio加入A/B独立FREE→WRITING→READY→CPU→FREE所有权；相机写B时CPU可读已领取的A。每块CRC/SEQ独立冻结，CLAIM/RELEASE须匹配SELECT及EXPECTED_SEQ，READY/CPU不自动覆盖；两块占满只等待/跳过传感器整帧，释放后从下一完整帧开始。首个流仍丢10帧，后续不重复预热；STREAM_STOP排完当前帧，ABORT只使当前帧无效并保留其他已完成/CPU帧。

入口：[双缓冲所有权、MMIO与Sol交接](camera/OV5640双缓冲所有权与CPU并发读取_2026-10-15.md)。A=0x41000000、B=0x41200000，各2MiB；整个0x41000000–0x413fffff无缓存且不可执行。双缓冲模式只准CPU读已CLAIM缓冲，禁止CPU写帧区。ID升级**0x43414d02**，窗口保持64字节；新增SELECT/BUFFER_STATE/GLOBAL_SEQ/EXPECTED_SEQ/WAIT_CYCLES。旧成功BIN/日志保持，不能直接当本版程序；CNN未接入。

本轮修改7个已有RTL及有效/参考FDC两份，CPU核、DDR IP、FIFO、SCCB表、写仲裁、PDS源表及成功软件未改。[单缓冲源码前像](../sim/camera_double/baseline_single_20261015/manifest.json)保存35项；[静态审查清单](../sim/camera_double/static_20261015_a/review.json)核9项改变/26项保持，两份成功BIN身份保持。Icarus null部分展开两种配置退出0，启用组仅缺省DDR黑盒方向警告；没有执行功能仿真/PDS/实板，不继承旧PASS。CRC新增目的寄存器与warmup同步已加入10ns具体端点约束，原复位同步器精确例外保持。

**下一步由用户重新综合→映射→布局布线→时序报告**，本版RTL已改变，不能复用单缓冲时序结果。时序通过后Sol按新接口准备一组关键测试，DeepSeek仅执行；优先小尺寸真实CPU并发/完整帧边界/重复复用及异常，复用成功单缓冲证据，不重启7200秒长仿真或历史全套。原720p单缓冲100帧与两帧导图成功记录继续保留，下方为其原结论。

## 2026-10-15：单缓冲100帧实板原始日志复核通过；主要耗时为含丢10帧的采集等待

用户回传`sim/camera/board/loop100_20261015_01/`。Sol执行`python tools/camera_uart/loop100.py --verify sim/camera/board/loop100_20261015_01`，完整原始89个Loader应答/唯一RUN/单G、应用身份/ID5640/CONFIG=OK、100行摘要和结束统计逐字节一致；另从CSV独立重算各阶段统计。固定BIN10896字节/SHA82f6698d…7cc6及manifest/source/tool身份匹配，受保护RTL/PDS/成功两帧固件保持，未运行仿真/PDS/串口。[Sol收据](../sim/camera/board/loop100_20261015_01/sol_review.json)SHA **43a0eeff10170ce3e44d4801dabadee11e4661645b540f403da35fd0c06ae0d2**，结论 **CAMERA_LOOP100_BOARD_DATA_ACCEPTANCE_PASS**；原7个日志/镜像/报告文件保持不改。

真实序号1→100连续，采集与CPU全帧CRC **100/100匹配**，每行STATUS=00000005/ERROR=00000000，结束SUCCESS=100，无重试。依固定固件检查的元数据每帧均为921600像素/1843200字节/57600拍，BUSY→DONE及读取前后稳定；累计CPU读取46080000字/184320000字节。100个CRC均不同（首595dd45e、末b6fd87cf），不把相同CRC判错，也不以变化本身证明用户主动改画面；本次日志没有单独的人工作业确认。

按93.75MHz计时：总 **114.613935328s**，采集等待合计70.220193493s/**61.267%**，CPU读取加CRC合计43.284508704s/**37.765%**，其余元数据/打印/循环约1.109233131s/**0.968%**。每帧平均等待 **702.202ms**，首帧749.465ms，后99帧701.709–701.806ms/均值701.725ms；CPU检查均值 **432.845ms**，范围432.843659–432.854069ms，跨度仅10.411μs。未见累积变慢或超时；第一帧稍长，原日志无法单独归因到具体传感器阶段。

主要耗时是每次ARM含丢10个启动帧的采集等待；CPU全帧读取/CRC也占约38%，但不是裸DDR带宽测试。完成率约 **0.8725个已校验帧/s**，不能称相机原始FPS；读取加CRC有效约 **4.258MB/s**，不能称DDR峰值带宽。本轮不导图/不做PC全帧CRC，图片正确性仍复用此前两帧人工验收，原长SoC超时仍未完成；不扩展到异常压力/PHY/ISA或独立位流审查通过。**当前100帧正常循环验收已完成，无明确RTL异常，无需改RTL/PDS或重跑长仿真。** CPU性能优化仍暂停；下方“待用户100帧”是历史准备状态。

## 2026-10-15：单缓冲100帧循环程序已准备，沿用成功Camera位流，待用户实板执行

用户要求不改成功RTL/位流/采集参数，新增软件100帧循环：ARM→BUSY/DONE或ERROR/超时→元数据→CPU全帧CRC与硬件比较→下一ARM，首败停止。Sol已实现[程序及运行说明](../tests/camera_loop100/README.md)、[串口执行/原始字节复核工具](../tools/camera_uart/loop100.py)。单缓冲0x41000000，1280×720 RGB565/1843200字节/57600拍，DROP_FRAMES=10保持；相同CRC合法，只统计重复数，不判旧帧。每帧打印序号/CRC比较/状态和错误/等待与CPU校验ticks，最终成功帧数及总计/最小/最大值，PC补均值毫秒和总秒数；等待包含每次ARM丢10个启动帧，64位软件计时支持CYCLE回绕。配置5秒、采集5秒、CPU读取20秒及PC每行30秒超时，原RTL3秒采集超时不变；失败保留诊断、锁存FAIL并停止，不重试/不导图。

固定`tests/camera_loop100/build/camera_loop100_20261015_a/program.bin`：**10896字节**，SHA **82f6698dfeb820219a698b5d752c9c0d033e734ecde52c99b33ad805ad3c7cc6**，Loader CRC **7c9c3d04**，manifest SHA48095be4a669da91ba7f9585f2b8397bb58e358da32f7e72eb8da8c4a177754c。复用原Loader，89应答/整BIN VERIFY/唯一RUN，应用READY后只发一个G，自动连续100帧，不重建固定BIN。

[交接收据](../sim/camera/loop100_preparation_20261015_a/handoff_review.json)SHA **6fe7f5d1a06062ff6808117a7c67ccdd9675b28698476a21ba8833addec46ffa**：RV32I ELF/BIN/栈及2187条指令静态审计通过；实际C源在native模拟MMIO14例，正例逐个读46080000字，独立输入图案/zlib CRC核对、计数器及序号回绕、相邻98次CRC重复不误报；采集错误/超时、序号/长度/像素/写拍/稳定性、CRC错误、BUSY/DONE异常、CPU读取超时/配置/命令异常均首败后无再ARM。串口8例正常/错误原始字节和统计检查通过，合成不得冒充实板，全部相同CRC也合法；初次native测试夹具因MinGW printf格式编译失败保留offline_tests，修夹具后offline_tests_b通过，固件未因此修改。207项设计/IP/PDS输入和旧两帧成功证据保持，未运行HDL/PDS/串口/上板；**100帧当前尚无实板PASS**。本轮不在PC重算帧CRC（不导图），图像正确性复用已验收两帧。

用户关闭串口助手，保持当前成功Camera位流，无需重新PDS，执行：

```powershell
python tools/camera_uart/loop100.py --port COM9 --log-dir sim/camera/board/loop100_20261015_01
```

工具提示KEY0释放并等DDR后Enter。中途主动改变画面，第50帧会提醒但不暂停。完成/失败后回传新日志目录及改画面反馈；原始RX/TX、CSV、固定BIN/manifest、result/verified均保存。首败保留，不覆盖重试，不自动发消息；若有明确RTL反例再交Astra。下方两帧成功基线不变，不重跑长SoC/CoreMark/ISA/PHY。

## 2026-10-15：单目OV5640→DDR→CPU→串口导图，两帧实板验收通过

用户已写回`sim/camera/board/uart_frames_20261015_01/`并明确确认“日志已写回,图片正确”。Sol离线逐字节重放实际Loader/RX/TX、每块包头/数据CRC、偏移/序号/ACK、会话结束及PNG映射，结果与原`verified.json`一致；已查看两张1280×720 PNG，结合用户看图反馈，正式结论为 **CAMERA_UART_TWO_FRAME_BOARD_ACCEPTANCE_PASS**。[本次复核收据](../sim/camera/board/uart_frames_20261015_01/sol_review.json)SHA **4aac1ccd43974c57d2dad71e71d76099120898becf5ee61a565b4a04804c8088**，原result/verified/串口字节和图片保持不改。

实际SENSOR_ID=5640、CONFIG=OK；重复ARM序号1→2，每帧921600像素/1843200字节/57600写拍，OVERFLOW=0、ERROR=0。两帧采集CRC＝CPU整帧首读CRC＝CPU整帧复读CRC＝PC原始帧CRC，分别 **31167575 / 3F8A68B9**，画面发生变化。每帧1800个1024字节数据块及END/ACK完整；53个Loader应答、唯一RUN、会话`CAPTURES=2 EXPORTS=2 CPU_CHECK=PASS`与完整实际收发字节一致（RX3805334字节、TX10827字节）。固定BIN仍为6212字节/SHA373940da…f529/Loader CRC26abe2d1，运行副本、构建源和PC工具身份匹配；不重建成功BIN。

本轮完成用户操作的实际相机→DDR→真实CPU两次整帧CRC→串口→PC CRC/PNG及人工看图验收；沿用前次SCCB/faults和仿真DONE晚于最终实际W的证据。**原7200秒SoC长仿真仍为超时未完成，不改成仿真PASS；串口结果本身不提供最终W/DONE逐周期轨迹，不扩写穷尽压力/ISA/CoreMark/PHY或独立PDS/位流审查通过。** 不再要求续跑长仿真或重复两帧验收，性能优化仍暂停。日常只需摘要时使用`--summary-only --captures 1`与新日志目录；无新增修改/异常不主动重测。下方“实板待验收”为历史准备状态，由本条更新。

## 2026-10-15：长SoC仿真超时前缀已核；转用户串口采帧＋CRC＋PNG验收

按用户提出的串口采帧方案，**不再续跑/重启完整720p真实CPU长仿真**；已有原始证据仍复核保留。`ds_camera_soc_bootmap_20261015_a`实际native1、timeout=true、7200.4879822s，原STOPPED_FIRST_FAILURE不改。控制台输出因缓冲停在SCCB，不能作进度依据。[超时原始前缀收据](../sim/camera/key/review_timeout_20261015_a/review.json)=SOC_TIMEOUT_COMPLETE_PREFIXES_REVIEWED_NOT_FULL_PASS：317项输入/运行副本/封存/Git/证据身份保持，前16条退休与固定镜像吻合；两套完整DVP图案、各57600次相机W全部字节/地址/strobe正确；DONE分别3178629/27960479，均晚于最后实际W两周期，CRC为AD4E00C3/68C5601B。CPU第一帧460800字＋3复读已核、已上报AD4E00C3；第二帧已核73042个CPU读值，原生AR/R只保存73013个完整前缀（硬杀后两个文件缓冲尾部不同且各留半行）。CPU实际非帧DDR写302955次也逐项匹配。缺第二次完整CPU CRC、最终覆盖与PASS，不补造，不交Astra猜改RTL。旧SCCB/faults成功证据继续复用。

Sol已实现[串口验收程序/步骤](../tests/camera_uart/README.md)与[PC接收工具](../tools/camera_uart/README.md)：固定BIN `tests/camera_uart/build/camera_uart_20261015_a/program.bin` **6212字节**、SHA **373940dab9b1c1a4e444d5fa4467580b490d4bdd288fc4c516c90f32aed9f529**、Loader CRC **26abe2d1**。通过既有Loader的53应答/VERIFY/唯一RUN装载，不改ROM/RAM/IP/RTL或启动PDS。程序检查真实ID/配置、两次ARM/元数据、每帧两次CPU整帧CRC，1024字节二进制块导出；PC核Header/Data/全帧CRC、序号/偏移/ACK和实际原始收发字节，保存RGB565与PNG。两帧之间提示用户改变画面，要求序号与CRC变化。摘要模式不导图、不冒充PC全帧检查。

[软件交接收据](../sim/camera/uart_preparation_20261015_a/handoff_review.json)：RV32I ELF/BIN/布局/栈/1151条指令合法性静态检查过；真实固件C的CRC函数在本机native上与zlib核对0/9/256字节及两套完整1843200字节图案，C包头与Python3例一致；两帧合成分块收发/原始复核和坏包头/坏数据/错序号/错偏移/画面未变/原RX篡改/短读拒收通过，合成证据明确OFFLINE而非实板，plan-only不打开串口。**新C BIN没有新Full Boot/完整CPU仿真PASS，首次实板仍待用户执行**；本轮按用户串口验收建议把剩余完整校验放到实际DDR，不以原长仿真缺项或静态构建代替实板PASS。

用户使用已通过时序的Camera位流，关闭串口助手，在根目录运行：

```powershell
python tools/camera_uart/capture.py --port COM9 --log-dir sim/camera/board/uart_frames_20261015_01
```

工具提示用户KEY0释放/DDR就绪后Enter，下载固定BIN，第一帧导出后再提示改变画面并Enter。原始帧约160秒/帧，加包头理论约165秒及USB/ACK延迟，两帧约6分钟以上。新日志目录不得存在，首败停，不重试、不自动重建；用户回传目录及两张PNG的颜色/行序/画面反馈。自动结论只到UART_FRAME_DATA_CHECK_PASS_VISUAL_PENDING，用户仍需看图；摘要模式为不同范围的CPU_CHECK结果。Sol未打开COM口、未下载位流/按KEY0或实板操作。本轮旧SoC续测任务停止领取，不追加DeepSeek仿真。

## 2026-10-15：SCCB/faults原始证据通过；SoC发现TB启动地址重叠，封存仅SoC修复续测

已核`ds_camera_ini_resume_20261015_a`：[原始复核收据](../sim/camera/key/review_soc_bootmap_20261015_a/review.json)=**CAMERA_SCCB_FAULTS_RAW_REVIEW_PASS_SOC_BLOCKED_BY_TEST_BOOT_MAP**。271项活动/封存/运行副本、3厂家/4工具/INI/5include/55模块及Git前后全部一致。重新离线执行封存独立checker：SCCB **7例/244写/8读/4位置NACK**、faults **8例**通过，DMA实际写前缀1024/1023/1/1/1/0/0/0拍；另独立重放仲裁12AW/30W的owner、地址、数据和strobe正确（CPU6个四拍、相机6个单拍）。复用这两组，不再仿真。faults35条为现有未接端口提示（3017×2、3722×33），完整保留，Errors0；不改成零warning或完整720p通过。

SoC在 **3290461ps** 报`RESULT: FAIL CPU trap`，native0但Fatal/Errors1，runner正确停止；bus/cpu/dvp原日志均0字节，无ARM/帧/CRC证据。旧TB只打印trap标记，**PC/cause/tval未记录，不补猜具体异常指令**。已证明测试配置错误：TB仅设置RESET_PC=40000000，子soc_top的INST_ROM_BASE/DATA_RAM_BASE默认同样40000000；ROM优先译码遮住DDR测试入口，软件CRC表0x1000也不在旧RAM窗口。不能以此形成预期相机CPU程序的RTL反例，先修测试，不交Astra猜改CPU。

新增`tb_soc_bootmap.sv`，原TB/旧封存保持：仅把子soc_top的ROM/RAM基址设0、复位PC仍40000000，并补参数/入口DDR路由/首条退休40000000与10002437/CRC表写RAM检查、最初16条退休和完整trap诊断。相机/CPU/缓存/模型/图案/程序/独立checker/全部720p与CRC、缓存隔离、重复ARM、最终W/DONE判据和超时不改。[静态收据](../sim/camera/key/preparation_soc_bootmap_20261015_a/static_review.json)：ModelSim55模块编译0错0警告；未执行的Icarus部分展开编译产物直接确认旧/新参数40000000→0，PC保持40000000，不运行vvp。设计RTL/PDS/IP/成功镜像未改，无需重新PDS。

当前唯一[仅SoC续测任务](../DeepSeek/相机首版_SoC启动映射修复_仅SoC续测_2026-10-15.md)：`python sim/camera/key/run_soc_bootmap.py --check-inputs`后`python sim/camera/key/run_soc_bootmap.py`。新清单`inputs_soc_bootmap.json` SHA **44437cb7042b70b7430336105696b7aacc84863cc51c0d2629afca12af33eecb**，317项，封存`sealed_soc_bootmap_20261015_a/`；新目录`build/ds_camera_soc_bootmap_20261015_a/`尚未创建，check-inputs/plan-only通过，只有vlib/compile/soc/soc_check，不再运行SCCB/faults或历史全套。DeepSeek仅执行、首败保留，新trap先交完整诊断由Sol复核分类；当前无SoC/实板PASS，不自动发消息。

## 2026-10-15：相机A首败已复核，为ModelSim INI启动参数问题；仅修入口封存续测

已核`sim/camera/key/build/ds_camera_key_20261015_a/`原始证据：[复核收据](../sim/camera/key/review_first_failure_20261015_a/review.json)SHA **dc045315eedcb56592c8c6c795ff863cc88ac0bf160babd9265e0a159f702f45**。246项活动/原封存/运行输入、3厂家原语/4工具、INI与5include全部一致，git_before/after相同，已登记证据哈希全匹配；vlib和55模块编译均native0、Errors0/Warnings0。首个sccb命令native **12**、**3.2414095s**、未超时：`vsim-7 Failed to open -modelsimini file "{D:\...\modelsim.ini}"`、EINVAL、Error loading design、Errors2/Warnings0。没有进入DUT/run-all，**SCCB案例0，faults/SoC未启动，没有本版功能PASS或RTL失败证据**。

这是Sol运行脚本的INI参数问题。保留原A目录、清单859fca5c…064d3、246输入及原任务/入口原样；新增薄入口仅在三个vsim命令中把`-modelsimini`绝对路径参数改为私有cwd中的`modelsim.ini`。同字节私有INI的无设计/无run启动探测native0、Errors0/Warnings0；只证明参数修复，不是设计载入或功能通过。RTL/TB/模型/CPU程序/独立参考/判据/超时/49源55模块均不变，不需再做PDS。

当前唯一[INI参数修复续测任务](../DeepSeek/相机首版_INI启动参数修复续测_2026-10-15.md)：`python sim/camera/key/run_ini_resume.py --check-inputs`后`python sim/camera/key/run_ini_resume.py`。新清单`inputs_ini_resume.json` SHA **0cadecef11c33d41d52b233a9aa629a51791843756f235c829c3fa32c08ce3f7**，271工程/参考/旧证据，封存`sealed_ini_resume_20261015_a/`，新目录`sim/camera/key/build/ds_camera_ini_resume_20261015_a/`尚未创建；只读check-inputs/plan-only均通过。三个功能job原本均未执行，在新目录各执行一次，不复跑历史CoreMark/ISA/PHY，不重试或续写A。

Sol没有运行DUT功能仿真，DeepSeek仍仅执行、首败停止，失败先交Sol分类。未修改RTL/PDS/IP/成功镜像，未PDS/串口/KEY0/实板，不自动发消息。收到新原始证据再复核；当前不能上板验收或写相机功能PASS。下方旧run.py执行入口已停止领取。

## 2026-10-15：用户确认相机新版PDS时序通过；Sol关键测试封存交DeepSeek仅执行

用户本轮直接确认重新实现时序通过，授权Sol编写并封存相机关键测试，DeepSeek仅执行。本轮按用户确认进入功能验证准备；未独立重审PDS报告/位流，不补写WNS，不启动PDS或实板。下方“等待重新实现”是先前历史。当前RTL五项时序修复after身份逐项核对，CPU b1114fa3/主桥d99a137a/soc_top1be16948/capture c3a6779a/camera_mmio8f926c21；未改设计/PDS/IP/成功镜像，032证据保留且不作为相机PASS。

唯一[DeepSeek执行任务](../DeepSeek/相机首版_精简关键测试_2026-10-15.md)，入口`python sim/camera/key/run.py --check-inputs`后`python sim/camera/key/run.py`。Sol已准备TB、外部开漏SCCB传感器/异步DVP/原生DDR模型、941条指令的真实CPU程序、独立逐像素/逐拍/逐字检查器与封存/执行脚本；清单`sim/camera/key/inputs.json`、封存副本`sim/camera/key/sealed_20261015_a/`，唯一新运行目录`sim/camera/key/build/ds_camera_key_20261015_a/`。执行前不得重建/重封，目录存在即停，首败保留，不擅自修测试或放宽判据。

一组只有SCCB、faults、SoC三个job：244写/8读回及4个字节位置NACK、ID/格式读回错；128×128自然溢出/短帧/ABORT/复位不报DONE、原生CPU四拍burst/相机单拍仲裁、9个地址边界；真实soc_ddr3_top/CPU/Cache两次默认720p采集、重复ARM及全部921600个32位全帧load（另6个预读）。完整驱动DVP像素、115200次相机W、每次原生AR/R和CPU load均留原始日志；golden由图案独立生成，CRC **AD4E00C3 / 68C5601B**。扣住最终W检查DONE时序、元数据原子性，禁止以DUT写数据反推期望。

49个编译源的递归include含csr_defs.vh、两个IP初始化参数和DDR测试头文件；3个厂家原语及每顶层GRS实例齐全。Sol静态ModelSim编译Errors0/Warnings0，Icarus仅忽略未展开IP的null部分展开退出0，离线编码CPU CRC核6个样本与zlib相符；未run vsim/vvp。DDR仅原生用户口模型，配置计数加速，CPU从测试DDR预装镜像启动，不能记PHY、Loader Full Boot、真实传感器或实板通过，也没有可直接部署的本轮相机BIN。详见[同阶段新增测试准备记录](camera/OV5640单目_DDR_CPU通路复用清单与Astra交接_2026-10-15.md)。

最终[清单](../sim/camera/key/inputs.json)SHA **859fca5ca0e87c77976b3d3fbe3d80d408c37bb8e62ad9e720ca1d549e3064d3**：246项工程/参考/历史证据、3厂家原语、4工具（含Python）及私有INI；49源实际编译55模块（含3原语）。[静态收据](../sim/camera/key/preparation_20261015_a/static_review.json)记录修复after逐项匹配、6个离线CRC样本、完整编译0错0警告和include闭合；check-inputs/plan-only通过，正式新运行目录尚未创建。

当前状态：**测试已准备封存，HDL功能未执行，待DeepSeek原始结果与Sol复核**。不重跑CoreMark/ISA/DDR PHY历史全套、不自动发消息；若证实RTL问题，由Sol整理最小复现和原证据交Astra，测试问题交Sol。用户继续负责下载/KEY0/串口，功能证据核过后才安排本轮实板。

## 2026-10-15：相机首轮时序失败已定位并修复，等待重新实现

用户提供14:27:21的report_timing：核心setup WNS−0.797ns/TNS−73.111ns/228端点，相机setup−0.029ns/2端点，core→PCLK复位同步器recovery−4.568ns/2端点。详细失败路径为D缓存DRM→数据响应→load前递/ID分支→指令ROM，以及camera_data[1]→CRC，复位终点为wr_reset_pipe[0:1]的RS。原报告和修改前输入已保存在`sim/camera/timing_fix_20261015_a/before/`，失败结论保留。

已修复：仅ENABLE_CAMERA时在soc_top给DDR数据响应valid/data/error一起寄存一拍，切断DRM到分支/ROM长链；ov5640_capture将DVP数据/HREF/VSYNC统一寄存一拍，CRC走完整PCLK周期；保持两级异步置位/同步释放复位结构，增加syn_preserve，并仅对综合网表GTP_DFF_C的`wr_reset_pipe*/C`异步清零脚设置false path，映射后对应RS。D/CLK和后级复位检查不切断，DDR频率/PCLK预算/10ns Gray限制不变。CPU核、DDR IP、软件镜像未改；相机模式数据响应新增一拍，不能套用032性能结果。

[本次修复清单与原路径](../sim/camera/timing_fix_20261015_a/repair_review.json)记录输入SHA；camera启用/禁用两种分支的Icarus null静态展开退出0，启用分支仅现有黑盒DDR时钟方向警告。不代表功能或时序通过，未执行PDS/HDL仿真。**下一步用户重新综合、映射、布局布线及报告时序，不能只在旧网表重报时序；新端点匹配/剩余违例仍待反馈。** 时序通过后才由Sol准备关键仿真，当前不派DeepSeek。

## 2026-10-15：修复FIFO CDC约束缺少ASYN_CTRL综合层级

用户反馈temp FDC第847/848行CommandTiming-0057。核当前`synthesize/run.log`两条约束的四个端点均未匹配；现存`synthesize/bak/board_top_syn.vm`明确给出`ASYN_CTRL.wptr/rwptr1`各13位、`ASYN_CTRL.rptr/wrptr1`各9位寄存器。原约束遗漏该生成层级，现已在两条约束的起终点均补`.ASYN_CTRL.`，同步修正参考camera_single.fdc与其生成脚本；10ns datapath限制保持，没有改RTL或扩大false path。[修复依据/前后SHA](../sim/camera/static_20261015/fdc_fifo_hierarchy_fix.json)保存原错误与网表身份，当前有效FDC SHA为`f12d24af2b81f1468d32343e8cbae3031cc6649842c772e1a2d54df8810951dc`。未运行PDS；请用户重新加载当前FDC并继续实现，实际端点匹配/时序仍待PDS反馈，不能记PASS。

## 2026-10-15：按用户要求补齐当前有效FDC的相机时序入口

已把相机1条create_clock、2条DVP输入延迟及10条具体端点CDC最大延时追加至`constraint_check/temp_constraint_file.fdc`第839–855行；原48982字节逐字保留，未改已有DDR/引脚、RTL或PDS。当前PDS仍只加载这份temp文件，不再需要另加camera_single.fdc，避免重复时钟/约束。13条命令各恰好一次，diff空白检查通过，[合并身份记录](../sim/camera/static_20261015/fdc_timing_merge.json)绑定前后SHA；合并后SHA为`c9e2d1107f47224d3bc1262454d0c70902ca3469e3b4ef96ad75eb0b85447a0c`。

下方“入口缺失”为已修复历史问题。现在由用户在PDS重新加载当前FDC并实现，核对时序及CDC端点是否匹配；PCLK10ns/DVP下降沿0–3ns仍是实现预算，不是实测外部时序保证。本次未运行PDS/仿真，无新增时序或功能PASS。

## 2026-10-15补充：用户指定临时FDC检查发现相机时序入口缺失

当前`constraint_check/temp_constraint_file.fdc`已追加14项相机IO，共93个标量端口的PAD/方向与board_top逐项一致，无PAD冲突；原761行DDR/板级约束保持。但当前RISCV.pds逻辑约束仅引用该temp文件，独立camera_single.fdc已不在引用列表；temp文件也没有相机create_clock、DVP输入延迟和CDC最大延时。**引脚部分静态匹配，整套相机时序约束不完整，不能据此记时序PASS。** 需先恢复唯一有效的相机时序约束入口，再检查本版PDS；下方“独立相机FDC已接入”是前次状态。详见[同一相机阶段记录的FDC检查段](camera/OV5640单目_DDR_CPU通路复用清单与Astra交接_2026-10-15.md)。本次仅只读检查并更新记录，未改FDC/PDS/RTL或启动实现/仿真。

## 2026-10-15：单目相机首版RTL已接入，等待用户本版PDS时序

用户已确认DOUBLE-DVP载板/J10/CAM1-J4/24MHz振荡器。本对话已将SCCB配置/8项读回、RGB565完整帧检查、16→256bit异步FIFO、单拍相机DMA、CPU/相机写口仲裁、Camera MMIO和无缓存/不可执行帧区接入主RTL。板顶启用Camera，主CPU实现/原DDR IP/Loader及成功BIN/DAT保持；新增设计/仿真源表和独立`fdc/camera_single.fdc`，未改当前DDR约束文件。032前像与历史成功证据保留，本版功能/性能不继承032 PASS。

详见[同一阶段记录顶部“当前进度”](camera/OV5640单目_DDR_CPU通路复用清单与Astra交接_2026-10-15.md)。MMIO为0x10002000–0x1000203f，帧区0x41000000–0x411fffff；本版1280×720 RGB565、1843200字节、57600个32字节单拍事务；0x28新增采集输入CRC32供真实CPU全帧读回比较。单缓冲，DONE与元数据/CRC原子发布后停止，CPU显式ARM才覆盖。ABORT不撤回已公开AW，排空失败保留busy/error等待全局复位。

[静态输入审查](../sim/camera/static_20261015/source_review.json)与[最终语法日志](../sim/camera/static_20261015/iverilog_final.log)已保存；Icarus仅`-tnull -i`语法/部分展开，缺省厂家IP黑盒，**未执行HDL仿真/PDS/实板**。新增FIFO RAM副本修复一处复制表达式及两处常量CS敏感列表，原demo保持。PCLK10ns与DVP下降沿0–3ns是实现预算，不是实物时序已核；具体CDC最大延时端点匹配与复位释放须用户本版PDS检查。

**下一步：用户重新打开根RISCV.pds，以board_top实现并反馈时序/约束未匹配或违例。** 不直接下载、没有相机CPU校验BIN或DeepSeek执行任务。时序通过后Sol写本版精简关键测试/CPU程序，DeepSeek仅执行，Sol核证据后才实板；不自动跨对话发消息或运行历史CoreMark/ISA/DDR PHY。下方“只分析/未改RTL”为历史状态。

## 2026-10-15接续补充：相机实现前源码核对与合同草案

已按用户接续要求读取入口、检查工作树并核对当前顶层/I-D互连/DDR桥及demo配置/采集/FIFO。详见[本阶段清单新增“实现前源码核对与设计合同草案”](camera/OV5640单目_DDR_CPU通路复用清单与Astra交接_2026-10-15.md)。主桥仍为032成功身份f14b16cb…52ba0，myriscv与RISCV.pds无本次改动。新确认需把帧区不可执行落实至指令译码，D缓存对局部帧地址同时no-hit/no-fill；AW背压期间也须保持owner，ABORT不能取消已公开/已接受的DDR事务。已写拟实施MMIO、帧/像素字序、CDC和完成判据，均未成为实际硬件接口。

实物DOUBLE-DVP/J10/CAM1及本地24MHz振荡器已询问待确认，候选引脚尚未应用。当前仍仅分析/设计文档，摄像头RTL、PDS时序、关键仿真与实板均未完成；没有新PASS或DeepSeek执行任务。本次直接分工为本对话负责RTL设计/修改，Sol负责测试代码/方案/证据复核，DeepSeek仅执行，用户负责PDS/下载/实板。CPU性能优化继续暂停，032与所有历史证据保留。

## 新对话接续入口（2026-10-15，CPU性能优化暂放置；单目OV5640→DDR→CPU资料已整理，交Astra）

用户明确暂停继续CPU性能提升，当前任务改为**单目OV5640 → DDR → CPU读取**。用户提供demo根`100K200KMINI/2_Demo`与四份实验手册，Sol已完成只读源码/手册/同包硬件资料分析；[Astra交接与完整复用清单](camera/OV5640单目_DDR_CPU通路复用清单与Astra交接_2026-10-15.md)为当前唯一入口，[机器清单](camera/evidence_2026-10-15/reuse_manifest.json)登记53个文件及SHA、14项通道0引脚核对和关键静态问题。性能032实板P/V成功基线和原日志保留，不推进033性能优化。

主要来源`5_1 双目摄像头例程/ov5640_200k`：完整16→256bit异步FIFO IP依赖包为可原样复制候选；OV5640配置/采集、帧控制、DMA与原生AW/W仲裁必须适配。已发现末项配置越界/额外启动窗口、末尾4条写只读ID300A、SCCB不采ACK、FIFO水位高位未驱动、640×720流却用129600拍长度、字节地址与本SoC原生word地址混用、写FIFO引用RD_LEN/假BVALID完成、CPU D64对外部DMA无一致性等问题；不是已仿真PASS的集成设计。

默认第一阶段保留传感器1280×720 RGB565，先单帧写完停住→CPU从明确无缓存帧区读/CRC；不引入双目/缩放/HDMI/滤波。建议MMIO0x10002000和帧区0x41000000为**待实现提案**，不是已有接口；不得覆盖当前DDR IP1.16a/93.75MHz、KEY0/Loader/UART与性能032成果。当前demo DDR IP1.10/DFI周期8000与主IP10666不同，旧工程不能整套照搬。

单目14项GPIO候选已与同包DOUBLE-DVP原理图J17、底板J10映射表核对相符；载板自带24MHz XVCLK、PWDN下拉、SCCB上拉/DOVDD2.8V，不能由demo LVCMOS33标签认定模组电平。用户实物是否同载板/J10尚未独立确认。四份实验手册未定位到5_1 OV5640专章，新增找到同包传感器Datasheet/DVP应用指南/载板原理图更直接；PDF页码、候选引脚表、测试边界在交接文档。

本轮只写doc/camera资料清单/分析证据和更新入口，master已有无关修改保持，**未改RTL/PDS/IP/BIN，未运行仿真/PDS/串口/KEY0，未向另一对话发消息**。用户把文档交Astra负责RTL，Sol后续写最小关键测试和复核，DeepSeek只执行；先用户时序通过再派本版仿真。当前没有新HDL执行任务或摄像头功能PASS。下方CPU下一轮建议均为暂停前的历史。

## 新对话接续入口（2026-10-15，032冻结P300/V300实板验收PASS，收益较小，下一轮评估MEM等待）

原P成功日志与新V-only日志已经独立核123个RVLD响应、各唯一RUN、整段UART/CRC5275与8803/13冻结计数/同BIN/同300次/93.75MHz、计时差值和周期分类守恒通过。P **2.242630368s / 210246597cycles / CPI1.9396909106**；V **2.2406077866666667s / 210056980cycles / CPI1.9384158480**。较031冻结基线耗时分别减少 **0.410816649% / 0.334917638%**。本轮以首目录P+vresume目录V组成成功基线；首目录V首PING失败保留，未下载/运行程序，不改原FAIL，不重跑P或历史。

[实板总原始审查收据](../sim/data_bus_turnover/build/registered_board_final_review_20261015_a/board_review.json) **TASK032_REGISTERED_LOOKUP_FROZEN_P300_V300_BOARD_RAW_PASS**，SHA **f7c4049708667c1518d48cef4c385d22e6994536afcd686081f3f538dd9ff365**。P SHA78979a18…11a3b0，成功V SHA38036eae…8e795b；主桥f14b16cb…52ba0、CPU/互连/IP/冻结BIN未改。032规定关键仿真与实板工程对比验收完成，不足10秒不称正式CoreMark成绩，不再次PDS/串口/KEY0或重复测试。

性能主结论：P/V MEM等待分别−4369318/−4401369，但IF分类+4380743/+4519802，几乎抵消；load-use−815865/−848700，branch recovery−62851/+24385，OTHER/退休/DDR命令/分支事件保持，净cycles−867291/−705882。**更正此前口径：七项周期分类互斥，合计等于cycles；instret独立、不能加进该守恒式。** MEM优先于IF计类，IF增加可能包含此前被MEM掩盖的等待，不能仅凭冻结总数断言取指额外加拍或时序修复造成性能退化。

当前可识别等待的最大项仍MEM：P/V **44264117/44071317cycles（21.053%/20.981%，CPI贡献0.40837/0.40669）**；之后branch recovery约11.2%、IF约5.9%、load-use约3.6%。OTHER约58.3%含正常运行与纯乘法等待，不能整体当单一可消除瓶颈。下一轮另一对话Astra先针对MEM请求/响应与共享I/D槽分析，只选择一个有明确周期路径依据的RTL优化；现13项不能区分44M中D命中响应、posted/仲裁背压与DDR返回等待，不猜具体模块/收益。详细表和下一对话入口见[032阶段顶部](cpu/MINI_数据互连响应同拍接续_2026-10-14.md)。本对话只核日志/分析/文档，未改RTL或启动033仿真；Astra改RTL→用户时序通过→Sol写最小关键测试→DeepSeek执行→Sol核原证据的分工保持。

## 新对话接续入口（2026-10-14，032实板P300已核PASS，V300首PING超时，待仅补V）

用户首次本版P/V目录`sim/data_bus_turnover/board/coremark_i64_d64_zmmul_dturn_registered_300_01`已返回。[实板部分审查收据](../sim/data_bus_turnover/build/registered_board_failure_review_20261014_a/board_review.json) SHA **ec1e86193bccbd3ef1f38b11388b5dab714860599738c639865b5e48a59a1a6d**，状态 **TASK032_BOARD_P300_RAW_PASS_V300_INITIAL_PING_FAILED**。P原123个RVLD响应、唯一RUN、完整UART文本/CRC5275/13冻结计数/同BIN身份独立重算通过：**210246597cycles、108391804instret、CPI1.9396909106、2.242630368s**。较031P211113888cycles/2.251881472s减少867291cycles/**0.410816649%**；MEM等待−4369318（−8.984%），IF等待+4380743（+55.434%），DDR命令与退休数保持，计数不作互斥相加或归因猜测。

V只执行第一条`PING_fresh_loader`：36字节已写出，5.0389102s未收到完整60字节响应，**V BIN尚未下载、VERIFY/RUN未发、程序未运行**。原日志没有保存短于60字节的RX，不能区分0回应与短帧；KEY0仅用户确认、未独立观察，尚不能认定RTL错误。原P/V日志SHA分别78979a18…11a3b0/5e51334a…cd4460，失败不覆盖、P不重跑。

当前唯一待用户操作：重新按KEY0并释放、等待DDR/Loader就绪，再**单独V300**进入新目录 **sim/data_bus_turnover/board/coremark_i64_d64_zmmul_dturn_registered_vresume_300_01**。命令见[032阶段顶部](cpu/MINI_数据互连响应同拍接续_2026-10-14.md)。Sol仅改善新PC入口的失败证据，保留原read_exact/5秒截止/协议/无自动重试规则，把已消费短RX字节数和hex写入异常/失败日志；fake-port正例/短帧/零帧检查通过，未开启串口。冻结软件/RTL/IP/原门与仿真证据保持，无PDS/HDL/板上操作。本版整体实板仍V_PENDING，032未完成，033不启动；后续结果先核失败或V成功再推进。

## 新对话接续入口（2026-10-14，032寄存查询关键功能验收PASS，等待用户实板P300/V300）

最新[旧I命中响应双请求补测报告](../DeepSeek/任务032旧命中响应双请求_结果_ds_data_bus_inst_lookup_triple_20261014_a.md)已原始复核。199工程/3厂家/3工具/2869保护、执行副本/5include/两个init_param/GRS均一致；39模块、vlib/vlog/triple各一次native0、零错零警告、两04030130、正常finish、console/transcript一致、Git/输入不变。真实edge8满足`i_rsp&&i_v&&d_v&&d_r&&!i_r`，旧word **0x471cf1c6**正确；D token3仅接受一次，I token2保持至edge9接受，同行失效后miss、edge10 AR/R、edge11返回 **0x011c03c6**，未使能字节保持。4接受=4响应，AR=R2/AW=W1/零outstanding。没有在规定关键场景中发现RTL缺陷，Sol未重跑HDL。

复用已核key617/415/18、A1472确定性+512随机（256hit/256miss）和completion17场景44=41+3/AR19-R18/AW=W6/真实AR-R同拍2/双请求2/8lane/背压/排空/三复位；本次补齐最后规定组合边沿。[总功能原始审查门](../sim/data_bus_turnover/build/registered_lookup_final_review_20261014_a/codex_review.json) 状态 **DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS**，review_kind **TASK032_REGISTERED_INST_LOOKUP_RAW_REVIEW**，SHA **0729d81615cfe7aaccefbdc22530c894358552243afa1945093b7085276d8008**；清单fdd0e64a…4b13d，主桥仍f14b16cb…52ba0。此前coverage阻断收据保留为当时事实，最后缺项已由新补测补齐。

**当前不再派发仿真，不重做PDS审查、不启动033；等待用户下载本版位流并实板测量。** 用户反馈的本版时序PASS保持，未经本次独立PDS复核；功能仿真PASS不是实板或收益PASS。新上板入口与KEY0步骤见[032阶段顶部](cpu/MINI_数据互连响应同拍接续_2026-10-14.md)，COM9新日志目录 **sim/data_bus_turnover/board/coremark_i64_d64_zmmul_dturn_registered_300_01**（当前不存在）。固定Zmmul P300/V300 BIN不重建，P/V各一次；031成功基线 **P2.251881472s / V2.2481371946666666s**，不足10秒只作性能比较。

分工保持另一对话Astra改RTL、本对话Sol写测试/方案/审原证据、DeepSeek仅执行、用户PDS/下载/KEY0/串口。本步只新增总审查证据和板测入口、更新进度，RTL/IP/BIN/所有旧失败与PASS证据均保持。下方旧“未验收/待补测”是历史，不再领取。

## 新对话接续入口（2026-10-14，completion原证据通过，单补旧I命中响应沿双请求）

最新[completion报告](../DeepSeek/任务032协议B覆盖补齐_结果_ds_data_bus_inst_lookup_protocol_completion_20261014_a.md)已原始复核：清单d9d215ea…1cb7，196工程/3厂家/3工具/2651保护及副本闭合；39模块、三native0、零错零警告、两04030130、正常finish、Git/输入不变。44接受=41响应+3取消，AR19/R18、AW=W6，真实AR/R同沿edge16/121、I/D双valid edge68/86，计划字段及非零lane部分字节写正确。保留原PASS，不重跑。

**整体功能门仍待一个规定组合边沿**：原任务要求旧I hit响应消费沿同时I/D valid，实际`dual_with_i_rsp=0`，checker只计数未断言；固定计划不能覆盖不是RTL无法构成此输入的证据。[本次审查收据](../sim/data_bus_turnover/build/protocol_completion_review_20261014_a/evidence_review.json) SHA **c7e77bf82b668173773ed508d09dc2991c04b0c4ff0d0f0d7049e6bca506b601**，状态`TASK032_COMPLETION_RAW_PASS_ACCEPTANCE_BLOCKED_OLD_HIT_DUAL_REQUEST`。尚未确认RTL缺陷，无上板命令。

当前唯一领取[旧命中响应双请求单场景执行](../DeepSeek/任务032旧命中响应双请求_单场景执行.md)。Sol写成新TB/checker/runner、封存`inputs_inst_lookup_triple.json`、新tag **ds_data_bus_inst_lookup_triple_20261014_a**；只4笔请求的一个桥级用例，旧响应/D优先/I保持/同行失效后miss及新数据同时验证。复用completion、key617/415/18和A1984；只vlib/vlog/新用例各一次，不重跑整组。Python合成参考QA通过不等于RTL仿真PASS，新HDL未执行。原completion/失败链/未派发准备稿保持。

新清单SHA **fdd0e64a8fb5654f31010e44a5e24c1bee23ad7959cb3c56ddb32e08f0d4b13d**，199工程/3厂家/3工具/2869保护，静态身份/AST/5include/GRS核通过。DeepSeek直接按任务执行，无需开发测试代码或重封存。

最新分工按用户直接指令：**另一个对话GPT-6 Astra改RTL，本对话GPT-6.1 Sol写仿真/测试代码与方案及复核，DeepSeek只执行**；历史“DeepSeek写测试”不再适用于新增工作。PDS/下载/KEY0/串口仍用户执行，Astra改RTL→用户检查时序→通过后相关关键仿真→Sol复核→用户上板。主桥f14b…52ba0未改，用户反馈时序PASS保持，无PDS/串口重验，033不启动。以下旧入口为历史，不再领取。

## 新对话接续入口（2026-10-14，032协议E运行PASS但覆盖/模型未满足验收，交DeepSeek新B补齐）

已核[最新E报告](../DeepSeek/任务032寄存查询协议B续测E_结果_ds_data_bus_inst_lookup_protocol_resume_e_20261014_a.md)及原始副本/日志：清单SHA **e7ca966c62d4ba59f4c5f8ae6fc24a4704c10b649c6fee5480cb018bbb746f74**，192工程/3厂家/3工具/2439保护、39模块、三native0/零错零警告/无超时、Git前后及原参考重放通过；B实际43接受=40响应+3取消，AR19/R18（1笔复位取消）、AW=W5，188记录边沿/计数器终值189。key/A复用原收据，不重跑。原E PASS/前序STOP和C未执行事实保持。

**Codex整体验收不通过，不能上板**。[审查收据](../sim/data_bus_turnover/build/protocol_coverage_preparation_20261014_a/evidence_review.json)=**TASK032_PROTOCOL_E_RAW_REPLAY_PASS_ACCEPTANCE_BLOCKED_COVERAGE_MODEL**，SHA **5bdabc0ba5614d2e644009faa0f4a8b7282e1280d56bb8a92c8f34b29964ac49**。直接从E快照重算AR/R同拍=0、I/D同时valid=0，报告competition3只是旧响应与另一端接受，不能代替双请求优先覆盖。TB在AW而非W提交内存（edge102→110与116→122分离），参考未按独立CPU计划校验Wdata/wstrb且未读取plan_path；plan.log43个scenario全0。Codex额外核5个实际W payload与计划一致，但不能因此放宽既定覆盖/模型要求。没有发现本次必须改RTL的证据，没有写总功能门。

当前唯一领取[032协议B覆盖补齐](../DeepSeek/任务032协议B覆盖补齐_真实同拍与独立写数据验收.md)。DeepSeek新增completion B-only顶层/独立checker/runner/sealer，新inputs_inst_lookup_protocol_completion.json/tag **ds_data_bus_inst_lookup_protocol_completion_20261014_a**。保持原192工程与全部历史身份，改本轮编译顶层仍39模块，输入先封存；只vlib/vlog60秒+B180秒各一次，复用key/A，不重跑control/旧版/历史。要求至少两个明确token的真实AR/R同沿、实际I/D双valid的D优先、W完成提交/计划数据strobe严格比对、完整token场景取消计划与逐edge覆盖。新代码尚待实现，不把拟定CLI当已可执行；首败保留交回，不自动追加运行。

主桥仍f14b16cb…52ba0，用户时序反馈PASS保持，不要求重PDS；当前只补测试/参考，无串口/KEY0/上板，033不启动。key617/415/18及A1984观察原始证据保持，整体B完成且Codex核通过后再直接给新COM9目录/冻结P300-V300/031基线。

## 前次032协议B-only派发（E已返回，现按新覆盖要求补齐，不再执行旧tag）

已核[逐行命中寄存修复报告](../DeepSeek/任务032逐行命中寄存修复_结果_ds_data_bus_inst_lookup_registered_repair_20261014_a.md)。原正式tag STOP保持，180工程/3厂家/3工具/1621保护与副本/include、39模块、四原生退出/超时/log已核。registered native0但Fatal/Errors1，不等于仿真PASS；Codex未重跑HDL。完整key **617/415/18**与架构/DDR字节/异常/顺序通过；新A独立核1472确定性+512随机，其中256随机hit/256miss，合计320hit/1664miss/320接续，1984连续id及边沿关联通过。

新[部分收据](../sim/data_bus_turnover/build/registered_protocol_repair_preparation_20261014_a/failure_review.json)=**TASK032_REGISTERED_LOOKUP_KEY_AND_A_RAW_PASS_B_FAILED**，SHA **2a48284482553a91d311df3d19fa26678d9359e1b8a20e738bc05e4c2a0614a1**。B实际70接受/60响应/8计取消/outstanding2，188事件；独立B首先失败“miss response without an R beat”。cy8051和8122同时I/D接受，与桥D优先不相容；已定位TB立即驱动后未等组合稳定、reset期间误计握手、固定N拍valid重复接受、R记录与消费边沿错位、同沿参考逐行更新。还不能证明本版全部功能；没有改RTL/旧结果/判据，旧git_after缺失保持。

当前唯一领取[032协议B-only续测四项修订](../DeepSeek/任务032寄存查询协议B续测_边沿采样与事务守恒修订.md)。DeepSeek实现新B-only TB/独立edge-token参考/runner/sealer、inputs_inst_lookup_protocol_resume.json，tag **ds_data_bus_inst_lookup_protocol_resume_20261014_a**。只vlib/vlog60秒与新B180秒各一次；**复用已核key/A，不重跑key/A/control/历史**。保留原16语义场景、真实8lane数据/优先/接续/posted排空/3复位取消，CPU与物理DDR两套所有权守恒；新代码尚未实现，不把拟定CLI当已可用，输入先封存、首败返回，不另加未封存试跑。

原b2f清单把活doc/CODEX_HANDOFF.md列保护；更新前已逐字保存[handoff_before_review.md](../sim/data_bus_turnover/build/registered_protocol_repair_preparation_20261014_a/handoff_before_review.md)，SHA与原项完全相同，部分收据绑定。原清单不改，新清单仅迁移此历史项到副本并登记映射，其余1620原保护保持，旧入口停用。桥仍f14b16cb…52ba0，用户反馈时序PASS保持，本步未审/运行PDS，不要求重实现；整体功能门关闭、无上板命令，033不启动。等新B结果，通过后同一步核原证据并给冻结P300/V300、031基线、新COM9目录。

## 前次032时序通过后的仿真派发（已执行停止，不再领取旧tag）

用户最新反馈 **“时序通过”**，按用户结果记录本轮PDS时序通过，不独立审查或虚构新WNS/TNS/资源/位流身份。当前桥SHA仍为 **f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0**；只读核原C清单176工程输入，除桥1170→f14b外，其余175项保持。master原有修改保留，本次只写任务与阶段文档，未改RTL或运行HDL/PDS/串口。

**当前唯一待领取任务**：[032逐行命中寄存修复：时序通过后关键仿真](../DeepSeek/任务032逐行命中寄存修复_时序通过后关键仿真.md)。DeepSeek编写新TB/独立参考/checker/runner/sealer，封存新 `inputs_inst_lookup_registered_repair.json`，tag **ds_data_bus_inst_lookup_registered_repair_20261014_a**；实现尚待完成，不把拟定文件名当已可执行命令。任务文件不会自动调用DeepSeek。

范围仅原SoC key + 一个新x32桥寄存查询/协议组。原key/TB/模型/参考不改，完整checked_key必须与C门一致：**33unit/617SoC/415MEM/18接续**；新组覆盖1472确定性标签观察、512随机（明确256hit/256miss）、真实DRM填充/响应接续/接受后换址/miss背压/posted排空/AR-R同拍/复位取消。只在新目录vlib60s、vlog60s、key180s、新组180s各一次，首败停止保留，不能先试跑后封存；control/旧桥/历史/ISA/PHY不重跑。全部递归include/初始化参数/GRS、原生输出、最终输入及旧证据保护要求见任务。

本版**功能待验证、实板未验收**。旧1170门不能放行f14b；Codex收到DeepSeek结果后核实现与原证据，通过后直接给固定BIN/031基线/新日志目录/KEY0和串口步骤，再由用户下载实板。当前不提供上板命令、不重新要求PDS、不启动033。以下“等时序/不派发”及旧任务/COM9入口均为历史阶段记录。

## 前次032逐行命中寄存修复准备（现用户已确认时序通过，功能待DeepSeek）

已核用户指定的更新报告 `report_timing/board_top.rtr`，报告内日期 **19:32:52**：93.75MHz、WNS **−0.264ns**、TNS **−1.414ns**、8失败端点。210a版仍时序FAIL；最差片内RAM→load扩展/CPU前递→ID分支比较→inst_req_addr[29]（fanout66）→I标签比较/分层归并→桥state_reg[1]，16级，logic4.338ns/route6.086ns。此前只改比较/归并结构没有切断整条跨模块组合依赖。

本轮仅修改主桥 `myriscv/dual_sram_to_pango_ddr_bridge.v`：x32 I逐行命中在同步DRM读地址采样边沿寄存为64-bit `way_hit_q`，全局归并移到寄存器之后；接受I请求统一进 `STATE_INST_LOOKUP`，不再由实时命中决定接受边沿的状态。下一周期hit立即响应并可接续，miss立即发AR，不额外等一个RADDR周期；包括AR/R同拍返回的捕获/填充和来源清除。逻辑状态增加一个，接口预期 **hit/miss均不加拍**；新增64位寄存器，实际资源/新关键路径待PDS。CPU/数据互连/写缓冲/IP/频率/约束/冻结BIN保持，不改false path或multicycle，不启动033。

桥 **210af94b0c6f282c60e6a2a2ce8d33d24e25fd99f3940d0696965a53fd2421dc → f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0**。详见[032阶段顶部](cpu/MINI_数据互连响应同拍接续_2026-10-14.md)。[本轮静态收据](../sim/data_bus_turnover/build/inst_lookup_register_repair_preparation_20261014_a/static_review.json) SHA **823be9af4c5253e1e795b7cb944ffe4c5bf40816871a9123f8df5e27acfbc373**；1801项改前身份仅桥变化，原1408保护及C门198项证据保持，master无关修改未动。原19:32报告、210a桥、git状态/HEAD/diff已保存。

**当前只等用户重新PDS实现的时序结果**。未运行仿真/编译/PDS/串口，当前功能与时序均未验收。时序仍违例则继续修032，通过后才交DeepSeek写/改测试并执行；Codex写要求/方案/判据及审原证据。原1170的617总周期/415MEM/18接续仅为本版保持目标，不能作本版PASS。旧lookup TB观察组合 `inst_line_hit`，现x32该信号为寄存结果归并，需按阶段文档改为接受边沿后的独立核验；现在不派发、不运行旧入口，旧COM9门不适用。以下所有旧派发和上板命令均为对应旧版历史。

## 前次032小块标签比较与分层归并（210a版19:32时序FAIL，未做功能仿真）

**用户最新执行顺序优先于下方历史**：Codex改RTL/静态审查→用户PDS重新实现检查时序→违例则继续交Codex修改、通过才交DeepSeek相关仿真→Codex原证据复核→用户下载/实板。当前无待领取仿真，不写或执行新的测试入口。分工仍是Codex负责RTL、测试要求/方案/判据和原始证据审查；DeepSeek写测试代码并执行。用户本次询问“现在是Codex写仿真测试代码吗”不自动改写此前已确认分工。

最新report内日期19:06:52：WNS **−0.251ns**、TNS **−1.134ns**、9失败端点，93.75MHz/10.6667ns保持。打印路径仍为片内RAM读数据→CPU load扩展/前递/分支→inst_req_addr[21]/[30]→I标签比较→way_hit→64路归并→桥state_reg[1] D；最差18级、logic5.019/route5.453ns。并行查表已去掉宽tag选择，但新报告显示比较/归并仍映射carry链，前次1170版时序FAIL，原功能PASS保持。

只改主桥`myriscv/dual_sram_to_pango_ddr_bridge.v`中I查询：21位高tag比较拆成7个3位比较，再4/3分组AND；64路命中用4路一组→16组→4组→最终归并，syn_keep保留小块边界而不保留每个way_hit。取消宽比较/宽归并表达式供下一实现验证，逻辑函数与响应拍数不变，不加状态/降频/设置例外。桥1170cfd2…80406→**210af94b0c6f282c60e6a2a2ce8d33d24e25fd99f3940d0696965a53fd2421dc**；CPU/数据互连/Cache/IP/BIN保持，不开始033。

改前报告/多seed/桥/Git/HEAD与diff已保存在`sim/data_bus_turnover/build/tag_tree_repair_preparation_20261014_a/`。[静态收据](../sim/data_bus_turnover/build/tag_tree_repair_preparation_20261014_a/static_review.json)=TASK032_SMALL_TAG_COMPARE_REDUCTION_TREE_STATIC_REVIEW_PASS_HDL_NOT_RUN，SHA **d1c4483a2057c8d26933fda49c22c1b24dd3df88cfb5494b45661e0765af10b0**：原176工程只有桥变，1408保护及原C功能门198证据保持，比较与归并分区覆盖全部位/全部行，查询块以外不变。未运行HDL/PDS/串口/KEY0，当前210a新时序/功能尚未证明；旧C仿真/COM9门只对应1170，不能用于当前桥。现在用户先重实现看新时序，有违例交回继续修、无违例再准备最终版仿真，不重复历史测试。

## 前次032并行查表功能复核（1170版功能PASS，但19:06新实现时序FAIL，旧COM9不用）

已核[DeepSeek最终C结果](../DeepSeek/任务032二次时序修复_结果_ds_data_bus_tag_lookup_repair_c_20261014_a.md)：限定测试实现、176工程/3厂家/3工具/1408保护、运行副本/5include/两个GRS顶层、39模块、四原生命令、原UNIT/82EV/49请求/BUS、lookup完整trace和Git前后全部通过。key **33unit/617SoC/415MEM/18接续** 与原完整checked_key相同，不加拍；lookup **1472确定性+512随机=1984观察**，64行/21高bit/valid/index/非选中行干扰，零不匹配。新[功能收据](../sim/data_bus_turnover/build/ds_data_bus_tag_lookup_repair_c_20261014_a/codex_review.json)=**DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS**，review_kind=TASK032_PARALLEL_INST_TAG_LOOKUP_REPAIR_RAW_REVIEW，SHA **8ffa90fcdcf7480844974940844effebb651c6f7ec1ca4319809174b1a17a169**。新清单SHA **b41b38a146d906833f23fbc46bc9babdf5a501a8cd5379910c53ce6a9182b600**。主桥1170cfd2…80406，CPU/数据互连/固定BIN保持。

覆盖限制：随机LCG的低位相关使512随机观察实际均miss；64个hit全部来自每行确定性匹配场景，不能写随机命中覆盖。x16及AR/R同拍返回未新增动态覆盖。A/B原STOP、缺失git_after和封存副本保持；修正为stdout路径/scenario初值/逐场景valid参考，未改RTL或原key判据。A/B/C共三次执行，原方案为单次首败停止；本审查只核已有技术证据，不从报告中的“已授权”字样追补重跑授权。没有再跑HDL，不修改旧结果。

当前无待领取仿真。用户重新PDS实现、生成并下载当前1170桥的新位流后，用新[COM9入口](../tools/uart_loader/candidates/perf_2b/run_data_bus_tag_lookup_repair_measurements.ps1)：

```powershell
Set-Location 'D:\riscv\RISCV'
& 'D:\riscv\RISCV\tools\uart_loader\candidates\perf_2b\run_data_bus_tag_lookup_repair_measurements.ps1' -Port COM9 -LogDirectory 'D:\riscv\RISCV\sim\data_bus_turnover\board\coremark_i64_d64_zmmul_dturn_tagfix_300_01'
```

冻结Zmmul P300/V300各一次，BIN677ee766…4517d/461c635c…719b、CRC5275/8803、93.75MHz保持。新目录尚未创建，不复用历史；每模式用户KEY0释放、等DDR就绪后Enter，运行中不复位、首败停止保留。成功对照031 wturn_timing_300_01：P **2.251881472s** / V **2.248137195s**，不重测基线。入口绑定C新功能门，Python/PowerShell静态、require_gate、离线P/V各123响应/唯一RUN通过，未打开串口，见[上板交接收据](../sim/data_bus_turnover/build/tag_lookup_repair_preparation_20261014_a/handoff_review.json)。不例行PDS/位流审查，不以仿真PASS证明新时序；此前18:21报告−0.218ns仍是旧实现结果。用户新报告才能确认修复效果，面积可能增加，实板性能未测；300次不足10秒只记性能对比。等待032新实板结果，033不启动。

## 前次032并行标签查询准备（现已复验并核原证据，不再运行旧入口）

用户再次报告时序违例。最新report内日期18:21:49：93.75MHz正确，慢角WNS **−0.218ns**、TNS **−0.431ns**、2失败端点。端点已从来源寄存器转到桥state_reg[3]/[1]，两路径均片内RAM读数据→load扩展/CPU前递/分支→inst_req_addr[8]→动态I tag mux/串行比较→state D，16级。前次修复只移除一个来源端点依赖，未解决共同的标签查询长路径；不降频、不加时序例外。

前次DeepSeek来源修复结果已由Codex本次离线复核：168工程/821保护及执行副本、3原生命令/38模块/UNIT-EV-BUS/Git全部通过，key仍33unit/617SoC/415MEM/18接续。新[前次原证据收据](../sim/data_bus_turnover/build/tag_lookup_repair_preparation_20261014_a/previous_key_review.json)=TASK032_FIRST_SELECTOR_REPAIR_RAW_FUNCTIONAL_REVIEW_PASS_TIMING_FAIL，SHA **4de7282d07bd407560b9f1496cc4d78fbdd8dbe66cdfd7b4a5a0ed0336e4e319**，明确用户新PDS时序FAIL，不是当前新桥PASS门；未重跑前次仿真。

本次仍只改主桥`myriscv/dual_sram_to_pango_ddr_bridge.v`，SHA1df26c25…03c08→**1170cfd21a9dc01fe526256a778309f0f657b0445ff53707ddfdc877a7280406**：x32 I标签每固定行并行比较高位，再与valid/index相与、归并hit，移除先选择整条tag再比较的串行路径。valid行tag低6位必等于该行index，由原fill保证；容量、tag寄存器、填充/失效、hit规则与状态/响应拍数不改，非x32保持旧表达式，前次来源修复保留。syn_keep属性已核本机PDS官方综合手册，用于保留组合网；可能增加LUT，实际时序/面积待用户新实现确认。

改前报告/多seed/桥/Git/HEAD与diff保存在`sim/data_bus_turnover/build/tag_lookup_repair_preparation_20261014_a/`。[静态收据](../sim/data_bus_turnover/build/tag_lookup_repair_preparation_20261014_a/static_review.json)=TASK032_PARALLEL_INST_TAG_LOOKUP_STATIC_REPAIR_PASS_HDL_NOT_RUN，SHA **8bbe6648588ea2b760640304357018b719b23bbe9272d883bed94ccc02e97400**：原168输入只有桥变，821保护及前次原证据保持，valid/tag不变量与新旧表达式等价已静态审查。CPU b1114fa3/数据互连b0afffb5/PDS/频率/BIN保持，新HDL/时序/上板未验收。

当前唯一领取[032二次时序修复要求](../DeepSeek/任务032二次时序修复_I标签并行查询关键仿真.md)：DeepSeek实现新lookup TB/独立checker/runner/sealer与`inputs_tag_lookup_repair.json`，tag **ds_data_bus_tag_lookup_repair_20261014_a**。保留原SoC key/TB/模型/独立参考/判据，只补最小64行高标签/valid/index查表组；仅新目录vlib/vlog60秒、原key180秒、新lookup60秒各一次。原key须完整checked_key与33/617/415/18保持，新查表至少1472确定性+512随机（种子20261014）观察逐项独立参考。38原模块加新TB为39，5include/GRS闭合，严格两条原语提示/零错零警告，首败保留，不重跑control/历史/ISA/PHY。

新测试代码与最终清单尚待DeepSeek，不把拟定命令当可执行。旧032门/COM9入口不对应1170新桥，不修改旧门放行。Codex收到新原证据通过后给新上板入口，用户重实现的新时序报告才可确认效果；033不启动，固定P300/V300与031成功基线保持。

## 前次032来源寄存器修复（功能已核，用户新报告仍时序FAIL，不再领取旧任务）

用户报告新位流时序违例，按该明确问题只读核最新`report_timing/board_top.rtr`（17:36:22）：93.75MHz/10.6667ns正确，慢角WNS/TNS **−0.035ns**、**1个失败端点**，hold正裕量；seed2/3/4/5分别−0.105/−0.143/−0.098/−0.035。唯一失败路径D DRM QB[26]→数据响应选择→CPU前递/分支→指令地址→I tag→桥`response_from_inst_drm` D，13级。报告指向剩余响应来源选择路径，不能仅凭本次实现把原因都归于032互连新增逻辑；未改约束/频率/设置例外。

本次只改主`myriscv/dual_sram_to_pango_ddr_bridge.v`：接收x32指令请求时来源标志置1，去掉该寄存器对I命中比较的直接依赖；miss进入RADDR清0，随后RSP仍选捕获DDR数据（包括AR/R同拍），hit仍直接选同步DRM。无新增状态/拍数，CPU/互连接续/Cache/IP/时钟不改。桥97273a85…64c20→**1df26c253243f6419390b733d4d6479efd4a7eb91f8439fe17587a7b55c03c08**。只属于032时序修复，033未启动。

改前报告/多seed/桥/Git/HEAD已保存在`sim/data_bus_turnover/build/timing_repair_preparation_20261014_a/`。[静态收据](../sim/data_bus_turnover/build/timing_repair_preparation_20261014_a/static_review.json)=TASK032_INST_RESPONSE_SELECTOR_STATIC_REPAIR_PASS_HDL_NOT_RUN，SHAbe2076ca…81926：旧166工程只有桥变化，626保护和185旧原证据保持，修复diff仅预置/清来源两处；静态核hit/miss/同拍AR-R/非x32有效响应语义，不等于新功能或时序PASS。

当前唯一领取[032时序修复关键仿真方案](../DeepSeek/任务032时序修复_指令响应来源寄存器关键仿真.md)。按最新分工由DeepSeek实现新runner/sealer与`inputs_timing_repair.json`，tag **ds_data_bus_turnover_timing_repair_20261014_a**；只vlib/vlog60秒和原key180秒一次，复用control不重跑。要求原68unit/82EV/49请求与全部错误/副作用/DDR字节检查通过，key **33unit/617SoC/415MEM/18接续** 与修复前完全相同。只允许新执行/封存代码，不改TB/模型/参考/原判据/超时；新最终哈希由DeepSeek登记，入口未实现前不作已可执行。首败保留，不跑历史/ISA/PHY/PDS/串口。

**此前COM9门仅对应旧97273a85桥，不能验收本修复版。** 新仿真原证据复核后再准备修复版入口；用户随后重新PDS实现/下载，新的报告才能证明时序效果。当前未执行HDL/PDS/串口/KEY0，新功能/时序/实板均待验收，冻结BIN和031成功P/V基线保持；本轮实板结果前不开始033。详见[032阶段顶部](cpu/MINI_数据互连响应同拍接续_2026-10-14.md)。

## 前次032收尾与上板交接（修复前旧桥已核PASS，旧入口不用于新桥）

任务032收尾已完成。[DeepSeek收尾报告](../DeepSeek/任务032收尾_结果_ds_data_bus_response_turnover_ip_count_key_20261014_a.md)的限定实现代码、新清单、运行副本和原始UNIT/EV/BUS/命令/Git已由Codex离线核验，未重跑HDL。新[功能收据](../sim/data_bus_turnover/build/ds_data_bus_response_turnover_ip_count_key_20261014_a/codex_review.json)=**DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS**，SHA **cd6a9fb6fc004e359dbf6b9c7eccfaf74bd7a596a6b734396b7c5215afe7eaaf**。清单22959513e1113e097ffafd2c245ce57ee10d054cab8deca8fccd27dd2501334f绑定166工程/3厂家/3工具与626旧证据；5include闭合，两初始化参数和GRS实例齐全。新三job native0/无超时，38模块零错零警告，key正常finish、两条同值IP提示；Git前后完全一致。

复用已核control，不再执行：unit64→33省31拍；真实SoC **619→617（−0.3231%）**，MEM等待 **443→415（−6.3205%）**，18次同拍接受。全部68场景、82EV/49请求、5AW=W/40AR=R、精确load fault/年轻store抑制和FENCE排空通过。非MEM周期176→202，故MEM省28拍只带来净省2拍；这些短程序比例不能预测CoreMark实板收益。设计仍只有数据互连b0afffb5变化，CPU b1114fa3/桥97273a85/固定BIN保持；CPU未改，ISA0。

当前无待领取仿真。用户生成并下载当前RTL的新位流后，执行新[COM9入口](../tools/uart_loader/candidates/perf_2b/run_data_bus_turnover_measurements.ps1)：

```powershell
Set-Location 'D:\riscv\RISCV'
& 'D:\riscv\RISCV\tools\uart_loader\candidates\perf_2b\run_data_bus_turnover_measurements.ps1' -Port COM9 -LogDirectory 'D:\riscv\RISCV\sim\data_bus_turnover\board\coremark_i64_d64_zmmul_dturn_300_01'
```

冻结Zmmul P300/V300各一次，BIN SHA677ee766…4517d/461c635c…719b、CRC5275/8803、93.75MHz保持。新日志目录尚未创建，不复用历史目录；每模式用户KEY0释放、等待DDR就绪，再Enter，运行中不复位，首败停止保留。成功对照为031 wturn_timing_300_01：P2.251881472/V2.248137195秒，不重测基线。工具绑定新功能收据，无PDS/位流审查前置门；require_gate与离线P/V各123响应/唯一RUN均通过，未打开串口，见[上板入口静态收据](../sim/data_bus_turnover/build/ip_count_key_preparation_20261014_a/handoff_review.json)。PDS时序和实际DDR收益尚未验收；不足10秒仍只作工程性能对比。收到本轮实板日志后再分析，**033不启动**。详见[032同阶段](cpu/MINI_数据互连响应同拍接续_2026-10-14.md)。

## 前次032 control闭合与key派发记录（现已收尾，旧入口不再执行）

**最新长期分工（用户本次再次调整，优先于下方历史）**：以后的仿真与测试由Codex写明确要求、方案、场景/刺激/独立参考约束、验收标准和证据要求；DeepSeek按方案编写TB/模型/独立参考/测试程序/运行与封存脚本，执行仿真/测试、保存原始命令/日志/轨迹并报告；Codex复核输入与原始结果、做性能分析及阶段文档。RTL/软件仍由Codex负责，PDS/下载/KEY0/实板仍由用户负责。DeepSeek实现任务范围内测试代码时不需另沿用旧“只执行”限制，既定判据由Codex指定、失败不得自行降低；原失败目录与冻结身份继续保留，新修复用新清单/tag。

当前032 GRS续测已执行，原tag停止并保留，不再运行。后续修复检查/封存/执行代码按最新分工交DeepSeek实现，Codex本次只核原证据并写下方新方案，没有改RTL/测试代码或运行HDL/PDS/串口。

收到[GRS续测报告](../DeepSeek/任务032续测_结果_ds_data_bus_response_turnover_grs_resume_20261014_a.md)：GRS已解决，vlib/vlog/control均exit/native0、无超时、38模块零错零警告、control正常finish；runner仅因预期4条IPSpecCheck04030130而实际2条STOP，key未派发。032只有单SoC/I-D对，两个生成Cache各打印一次；031还有手工桥才为4条。这是Codex初始检查口径沿用错误，正确要求严格2条同值，不放宽错误/警告或任何功能判据。

Codex仅在内存中校正该一处计数并执行其余完全相同的严格control审查，全部UNIT/82EV/49请求/5AW-W/AR-R/字节数据/异常与排空通过。[control复用收据](../sim/data_bus_turnover/build/ip_count_key_preparation_20261014_a/control_review.json)=**TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING**，SHA **61c2dc2dbb6386465fd9dc6e9a8bcb21cf42bda11ae69c465a2dbd2cda91ba13**。control unit64拍，SoC619拍/MEM443，FENCE等待8；100unit接受=99响应+1取消，CPU49请求/响应，AR=R40，AW=W5。旧STOP/缺失git_after保持，未写总功能门。

当前唯一领取[032两条提示口径与仅key续测方案](../DeepSeek/任务032收尾_两条原语提示口径与仅key续测方案.md)。**由DeepSeek编写限定代码后执行**：checker仅4→2；新run_ip_count_key_resume.py/封存脚本与inputs_ip_count_key_resume.json，tag固定ds_data_bus_response_turnover_ip_count_key_20261014_a。绑定上述control收据和188当前失败目录/清单/报告文件；原437保护保持，设计/TB/模型/参考/参数/38模块/阈值/超时均保持。新实现文件SHA由DeepSeek封存并报告，尚未编写，不把拟定入口当已存在。

仅vlib/vlog各60秒+key180秒三job，复用control，不再跑control/历史。key须原68unit/33拍/51接续/82EV/49请求及全部原检查通过，SoC周期<619/MEM<443、turns>0、FENCE等待>0；受控省31，实际省拍从新原始key计算。首败保留、不重试。新结果DATA_BUS_RESPONSE_TURNOVER_KEY_ONLY_WITH_REUSED_CONTROL_PASS由DeepSeek报告，Codex核新代码/封存和原证据后才给COM9。当前key未完成、总功能/实际收益未验收，033不开始。

## 前次032 GRS修复准备（续测已执行，原入口停用）

DeepSeek原032在control设计载入阶段STOPPED_FIRST_FAILURE。Codex已核[原始失败收据](../sim/data_bus_turnover/build/grs_resume_preparation_20261014_a/failure_review.json)：vlib/vlog native0，38模块Errors/Warnings0；control native12/1.6946396s未超时，20条GRS_INST未解析+Error loading design，Errors21/Warnings0。实际4条APM、16条DRM（原报告全部归DRM的文字不准确，原报告保持）。仿真时间0，没有UNIT/EV/BUS/key/git_after，不补造。是Codex新TB漏必要全局复位原语实例，不能判RTL功能FAIL。

按用户要求仅在`sim/data_bus_turnover/tb_data_bus_turnover.sv`顶层补`GTP_GRS GRS_INST (.GRS_N(1'b1));`，其厂家源原已编译/复制。TB新SHAcb1adf6f…90b10；互连b0afffb5/CPU b1114fa3/桥97273a85、unit/模型/独立参考/程序/编译参数/38模块/全部判据/超时保持。原427844a5清单、原tag和原报告全部保留，不复用或倒写PASS。

当前仅领取[032 GRS新授权续测](../DeepSeek/任务032续测_GRS顶层实例补齐.md)，新清单`inputs_grs_resume.json` SHA **fa8bf3ae379103f3450dc18c9a037f5711f3fbc12228e418b4719049ae5b6eee**：164工程/3厂家/3工具、5include闭合，437旧证据保护，其中183原失败目录/清单/报告文件；新增薄入口只绑定新清单/tag。字节级一行差异、副本/include/AST/check-inputs/plan-only/reviewer静态通过，[静态收据](../sim/data_bus_turnover/build/grs_resume_preparation_20261014_a/static_review.json)=TASK032_GRS_RESUME_STATIC_PREPARATION_PASS_HDL_NOT_RUN；新tag不存在，新HDL/PDS/串口未执行。

```powershell
Set-Location 'D:\riscv\RISCV'
python -B sim/data_bus_turnover/run_grs_resume.py --check-inputs
python -B sim/data_bus_turnover/run_grs_resume.py --tag ds_data_bus_response_turnover_grs_resume_20261014_a
```

明确只授权DeepSeek新入口单次vlib/vlog60秒、原未开始control/key各180秒，原68 unit/82EV-49请求/64→33与真实SoC收益全部判据保持，首败保留、不重试。不得运行旧run.py/tag或改源/参考/判据，不跑历史/PDS/串口。Codex收到后review_grs_resume.py核原证据，通过才给COM9；当前功能门关闭、实板收益未测，031成功基线不重测，033未启动。下方原入口为此前派发历史。

## 前次032初始准备（原tag载入失败，不再执行此入口）

用户明确授权“进行数据互连响应同拍接续的性能提升”。本轮只改已有`myriscv/data_bus_interconnect.v`，原e8582e27…5524e→**b0afffb5c45f8a635b90482cc15bd94f17ce2c748fd6f1bdad9db0b098131f24**，新增默认开启RESPONSE_TURNOVER_ENABLE。成功旧响应当拍可释放单槽接新，旧目标/data/error仍用锁存归属，原清旧/接新优先级保持；旧error当拍不接年轻请求，slave ready及posted-write非DDR排空保持。CPU b1114fa3、桥97273a85、Cache/IP/时钟/PDS/冻结BIN不改，未覆盖无关修改。性能依据是031MEM48633435/48472686（约23%）与原`!pending`阻止CPU在旧响应完成拍推进年轻访存的直接RTL空档，不以AW占93.3%推断全部写等待。

当前唯一领取[DeepSeek任务032](../DeepSeek/任务032_数据互连响应同拍接续关键仿真.md)，见[032阶段](cpu/MINI_数据互连响应同拍接续_2026-10-14.md)。新[清单](../sim/data_bus_turnover/inputs.json) SHA **427844a5db518bfbd95953426a82da7e4a31c6c67b535d8b791c493be2f2c370**：162工程/3厂家/3工具，38编译模块、5条include闭合含两初始化参数，252原证据保护；原031的211输入只有数据互连改变。Python AST/独立参考/check-inputs/plan-only/review静态/162+3副本复制与差异检查通过，[静态收据](../sim/data_bus_turnover/build/preparation_20261014_a/static_review.json)=TASK032_DATA_BUS_RESPONSE_TURNOVER_STATIC_PREPARATION_PASS_HDL_NOT_RUN，正式tag不存在。

```powershell
Set-Location 'D:\riscv\RISCV'
python -B sim/data_bus_turnover/run.py --check-inputs
python -B sim/data_bus_turnover/run.py --tag ds_data_bus_response_turnover_20261014_a
```

新TB只做相关一组：Unit68场景（旧/新响应目标、背压、error、posted排空、延迟/reset、32连续请求，control64/key33拍）；真实CPU/SoC82EV/49请求，5笔DDR写/字节更新/所有AR-R/AW-W、MMIO/UART/RAM/FENCE/STOP排空与精确load access fault（40000094/cause5/tval20000000→40000300，年轻40000808 store不得执行）。原x32 DDR模型未改，真实I/D/APM/ROM/RAM IP。新刺激需同新RTL关闭参数control一次，再key一次；key实际SoC周期/MEM等待须比control小。vlib/vlog60秒，control/key各-batch180秒，首败保留，不重试。CPU未改/ISA0，不跑旧031/历史/PHY。

Codex负责设计与审查，DeepSeek只执行/保存完整原始命令、退出/超时、输入副本/Git、UNIT/EV/BUS并报告。Codex收到后review.py核证据，通过才给COM9新门入口；当前仿真/功能门/时序/实板均未验收，未启动HDL/PDS/串口。固定031成功对照P2.251881472/V2.248137195秒，P/V300 BIN/CRC/93.75MHz保持；新板级目录计划`sim/data_bus_turnover/board/coremark_i64_d64_zmmul_dturn_300_01`，不重测基线/重建BIN、不例行核PDS/位流，实板新结果前不开始033。下面031记录是已成功基线，不再执行其测量。

## 前次031修复版实板核验与032评估（现已授权实施032）

用户交新日志并要求性能分析。已核`sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_timing_300_01`两份实际串口JSON：同冻结BIN/CRC5275与8803/300次/93.75MHz，COM9/115200、各123协议响应/唯一RUN、零重试、计时与cycles一致、七类周期相加守恒、DDR交易=AR+AW。新[实板核验与比较收据](../sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_timing_300_01/codex_review_20261014/result.json)=**TASK031_WRITE_BUFFER_TURNOVER_TIMING_REPAIR_FIXED_P300_V300_BOARD_LOG_REVIEW_PASS**，SHAe97864df…97c91。

P300 **211113888cycles / 2.251881472s / CPI1.947692**，相对030213993695cycles/2.282599413s耗时 **−1.3457%**；V300 **210762862cycles / 2.248137195s / CPI1.944930**，相对030214068190cycles/2.283394027s耗时 **−1.5441%**。最新成功对照改为上述wturn_timing_300_01，030成功日志原样保留、不重测。软件原文整数2秒/150iterations/sec有取整损失，按ticks正确吞吐133.2219/133.4438次每秒；ERROR/Errors detected来自不足10秒判据，CRC全通过，仅工程性能对比，不正式成绩。

收益主要在MEM：P51602799→48633435（−2969364拍/−5.7543%），V51701605→48472686（−3228919拍/−6.2453%）；净周期分别省2879807/3305328。P IF+46597、branch+42960抵消部分收益；V IF−29926、branch−46483补充收益，逐分类delta与净delta严格一致。退休指令/AR/AW/DDR总命令/分支次数/load-use/OTHER完全相同，符合减少写缓冲交接等待的机制；没有独立上板A/B把031接续收益和CE时序修复分别测量，不把总收益都归于清零修复。

剩余独立停顿：MEM **23.0366%/22.9987%**（CPI约0.449/0.447）> branch recovery11.2091%/11.1214% > load-use3.9723%/4.0095% > IF3.7433%/3.7476%。OTHER58.0387%/58.1228%含正常执行，不能作为58%可消除停顿。AW5179976/5160563占DDR命令93.2713%/93.3402%，但MEM未拆读写/请求/响应等待，不能断言全部是写。

本步仅核日志、分析并更新文档，没有改RTL/测试/软件，没有启动仿真/PDS/串口或重新验证历史。当前桥97273a85…64c20、CPU b1114fa3及冻结BIN保持；新功能门已通过，**本次实板CRC/性能对比PASS不证明PDS时序PASS**，本步未审PDS报告/位流。

下一轮单项评估方向：数据互连响应同拍接续。实际`data_bus_interconnect.v`的`issue_allowed = !pending && ...`仍在旧响应返回拍挡住新请求；CPU `ex_mem_ready`已经支持同拍MEM完成，所以EX年轻访存可能多等一拍，并由perf_memory_stall计入MEM。该空档有RTL直接依据，但本轮计数没有独立触发次数，不能用AW数量或全部MEM等待预测收益。当前只完成评估、尚未改032 RTL/准备新仿真；后续只动数据互连一项，需保持旧响应归属、error抑制与非DDR排空，Codex设计、DeepSeek执行。无需重跑031或历史测量。

## 前次031时序修复功能闭合与上板交接（两轮实板现已完成，不重跑）

收到[DeepSeek时序修复结果](../DeepSeek/任务031时序修复_结果_ds_write_buffer_turnover_timing_repair_20261014_a.md)，Codex已运行`review_timing_repair.py`独立核原始证据，未重跑HDL。新[功能门](../sim/write_buffer_turnover/build/ds_write_buffer_turnover_timing_repair_20261014_a/codex_review.json)=**WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS**，repair_kind=TASK031_X32_RESPONSE_REGISTER_CE_TIMING_REPAIR，SHA **65391a85058e7a77f540d48b7bc676b0dd45cd0bb0acb54f5c60057233cee61f**。三命令exit/native0、未超时，36模块零错零警告，key889/430EV/143请求严格通过、完整BUS守恒与字节更新/IRQ-FENCE-MMIO排空通过。key44拍、复用control49拍省5拍；全部覆盖/模型计数保持原031，SoC69机会/68实际接受、唯一late RADDR占槽仍正确。211工程+3厂家副本与当前封存输入、6include闭合、Git前后完全一致；旧失败及旧门保持。

当前无待领取仿真。桥仍97273a85…64c20，CPU/软件/模型不变，本次只审证据并更新交接。**功能已通过，PDS时序和实板尚未验证**；原−1.002ns/149端点是否消除必须看用户重新实现后的新报告，不用仿真PASS替代时序PASS。用户负责重新实现、生成/下载修复位流；Codex不启动PDS或串口，不例行位流/资源审查，实板结果前不另起032。

修复版[COM9入口](../tools/uart_loader/candidates/perf_2b/run_write_buffer_turnover_timing_repair_measurements.ps1)绑定上述新门，无PDS/位流哈希前置门；require_gate、Python/PowerShell静态与离线P/V各123响应/唯一RUN通过，serial_opened=false，见[交接收据](../sim/write_buffer_turnover/build/timing_repair_preparation_20261014_a/handoff_review.json)。下载修复位流后执行：

```powershell
Set-Location 'D:\riscv\RISCV'
& 'D:\riscv\RISCV\tools\uart_loader\candidates\perf_2b\run_write_buffer_turnover_timing_repair_measurements.ps1' -Port COM9 -LogDirectory 'D:\riscv\RISCV\sim\write_buffer_turnover\board\coremark_i64_d64_zmmul_wturn_timing_300_01'
```

沿用冻结Zmmul P300/V300各一次、BIN SHA677ee766…4517d/461c635c…719b、CRC5275/8803/93.75MHz，不重建/重测历史基线。新日志目录未创建，不复用旧wturn目录。每模式用户KEY0释放、等DDR就绪再Enter，运行中不复位、首败停止保留；关闭其他串口程序。对照030 bturn P2.282599413/V2.283394027秒，300次不足10秒仅性能对比。以下“待DeepSeek/功能未开放”为此前准备历史。

## 前次031时序修复准备记录（现已完成仿真并核原证据）

用户报告031新位流时序违例并要求处理。按该明确请求只读核最新`report_timing/board_top.rtr`（14:50:50）：core_clk约束93.75MHz/10.6667ns正确，慢角WNS **−1.002ns**、TNS **−60.104ns**、149失败端点；多seed2/3/4/5分别−1.234/−1.227/−1.176/−1.002ns。报告打印的三条最差路径均D DRM→CPU load/ID前递→分支→目标I地址→I tag→桥response_rdata CE，19级。10月5日旧hold-fix PASS文件不是本轮证据。

Codex已只改主桥`myriscv/dual_sram_to_pango_ddr_bridge.v`：x32命中响应直接选DRM，把未使用fallback清零移到IDLE/RSP默认动作，去掉该清零对请求/tag的依赖；miss在RADDR/RDATA覆盖后才产生有效响应，store ACK仍零，旧非x32赋值保持。桥2dfa96ca…b53e0→**97273a85137600e596b38a3e061cf2841bf24bc397bf9412688cd580fa164c20**。CPU/ready/接续/Cache/IP/时钟/约束不改，不加拍；原031性能计数预测保持。只是031时序修复，不开启032，新的仿真与PDS时序均NOT_RUN。

当前唯一领取[031时序修复任务](../DeepSeek/任务031时序修复_x32响应寄存器使能关键仿真.md)：`python -B sim/write_buffer_turnover/simulation_timing_repair.py --check-inputs`后，`--tag ds_write_buffer_turnover_timing_repair_20261014_a`执行一次。新清单SHA **c552686a8f4b96d6b71df53055b17519ae5b7784c0266884432fa84662036aff**：211工程/3厂家/3工具、6条include闭合含两初始化参数；原207项只有桥变化，257原证据保持。只编译和跑原key889/430EV/143请求组一次，复用已核control49拍，保持独立IRQ排空参考40000060、全部刺激/模型/检查/超时。原生vlib/vlog60秒、key180秒，首败保留新tag，不重试、不跑历史/ISA/PHY。

[静态准备](../sim/write_buffer_turnover/build/timing_repair_preparation_20261014_a/static_review.json)与副本include/精确差异核验通过，CPU b1114fa3保持；`review_timing_repair.py --check-inputs`静态通过，正式运行目录不存在。DeepSeek仅执行与整理结果；Codex审原始证据。**旧031功能门只对应旧桥，本修复版尚不能用旧COM9入口上板**。功能核验后用户重新PDS实现，新报告才能证明时序效果；不以本次路径改写宣称149端点全部满足。未执行HDL/PDS/串口/KEY0，冻结BIN及030实板基线保持。

## 前次031功能闭合记录（时序修复前的2dfa96ca版本，以下上板入口暂不适用）

任务031续测四个原生命令exit/native0、未超时、36模块零错零警告，control6/key889、正常finish与console/transcript一致；include缺失已闭合。runner保留STOPPED_FIRST_FAILURE原因是Codex独立参考把IRQ插在store退休后立即发生。实际TB接受store后下一negedge才拉高IRQ，先前ID已发射的ADD必须排空，mepc为40000060而非4000005c。BUS证明ADD取指响应cy1917/第一store接受cy1924/IRQ等待1925；封存CPU发射/排空/arch_next_pc规则与TB原精确golden_pc检查一致。

Codex独立重生成IRQ排空契约参考，不读DUT输出生成期望，仅四条参考EV位置变动；现有原始430EV全部逐字段严格匹配，143请求与软件结果保持，原参考/两STOP结果/缺失git_after不修改不补造。独立[功能收据](../sim/write_buffer_turnover/build/codex_irq_contract_closure_20261014_a/codex_review.json)=**WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS**，OFFLINE_IRQ_CONTRACT_REFERENCE_REPAIR_NO_HDL_RERUN；核全部原命令/完整log/207执行副本/3厂家/源码/EV-BUS，未重跑HDL。232接受=231AW/W+1取消，SoC73写/143请求，cache12fill/203字节更新，非DDR副作用busy0，FENCE49/IRQ26/STOP26等待，短程序49→44省5拍。总82机会/81接受，SoC69机会/68接受，唯一late cy3784为桥RADDR占槽，正确阻塞。

**当前无待领取仿真，直接给用户上板步骤**：用户PDS生成/下载新位流后，PowerShell执行`tools/uart_loader/candidates/perf_2b/run_write_buffer_turnover_irq_closure_measurements.ps1 -Port COM9 -LogDirectory 'D:\riscv\RISCV\sim\write_buffer_turnover\board\coremark_i64_d64_zmmul_wturn_300_01'`，完整绝对命令见[同阶段顶部](cpu/MINI_写缓冲完成同拍接续_2026-10-14.md)。新工具绑定独立Codex门，require_gate与离线P/V各123帧/唯一RUN通过，未打开串口；旧init_resume测量工具绑定旧STOP tag，不使用。每模式KEY0释放、等DDR就绪后Enter，失败停止保留，不例行审PDS/位流。

固定P/V BIN SHA677ee766…4517d/461c635c…719b、CRC5275/8803、300次、93.75MHz保持，对照成功030 bturn_300_01 P2.282599413/V2.283394027秒，不重建/重测。CPU b1114fa3、桥2dfa96ca不变，仅验证参考契约修正，无新RTL优化。未审PDS/PHY/全ISA/实际DDR收益不记PASS；新板级结果前不另起032。下方旧任务待续测/功能门未开放均为历史。

## 前次031接续记录（初始化参数漏封存已修，当时待新tag续测）

031正式收尾`ds_write_buffer_turnover_20261014_a`在编译处STOPPED_FIRST_FAILURE，Codex已核原证据：vlib native0，vlog native2/Errors258/Warnings0未超时，两include漏封存+256 INIT未定义，control/key/EV/BUS/git_after未执行/缺失保持。是Codex准备副本缺依赖，未构成RTL功能FAIL。原197输入副本及209失败文件/报告保持，不重写513b578c清单/不复用原tag。

当前唯一领取[031初始化参数续测](../DeepSeek/任务031续测_ROMRAM初始化参数封存补齐.md)：补原ROM/RAM两个`*_init_param.v`到新清单并随副本复制，CPU b1114fa3/桥2dfa96ca、全部TB/模型/oracle/BIN/判据/超时/36模块保持。新清单SHA **a891161f231a0ac81784432d2054d0941f655a2de240e57f2717ade3f3309763**，207工程+3厂家+3工具，启动前/副本include递归闭合检查、6include复制演练/两header128 INIT定义及SHA通过；静态收据TASK031_INIT_INCLUDE_RESUME_STATIC_PREPARATION_PASS_HDL_NOT_RUN。未启动新HDL/PDS/串口。

DeepSeek单次`python -B sim/write_buffer_turnover/simulation_completion_init_resume.py --check-inputs`，再`--tag ds_write_buffer_turnover_init_resume_20261014_a`。新目录必须不存在，vlib/vlog60秒、control/key各-batch180秒，首败停止，仅补原未完成范围，原control6/key889/EV430/BUS143/短组49→44保持，不历史回归/不修改设计和判据。Codex收到后review_completion_init_resume.py核原始证据，新tag PASS门通过才直接给run_write_buffer_turnover_init_resume_measurements.ps1 COM9同冻结P300/V300、新wturn_300_01对照成功bturn，不例行核PDS/位流，实测前不另起优化。旧门不写入失败tag。下方“原正式tag不存在/可领取原收尾”均为历史，旧命令不得重跑。

## 前次031接续记录（设计检查PASS，正式证据收尾准备，当时尚未编译）

**当前收尾已可交DeepSeek执行**：Codex按最新分工完成新观察TB、独立430事件/143请求参考、冻结副本原生runner和review_completion.py。剥离观察块/还原模块名称后行为逐字等价，刺激/判据/RTL/BIN/旧设计检查日志保持。新清单SHA **513b578cf6d91ed50700194664b720027e49a7ba3d67867a8cda23466fb13c96**（197工程/3厂家/3工具、36模块），静态收据WRITE_BUFFER_TURNOVER_COMPLETION_STATIC_PREPARATION_PASS_HDL_NOT_RUN，check-inputs/plan-only/审查静态均通过，正式tag不存在。

唯一待领取[任务031收尾](../DeepSeek/任务031收尾_补齐原始命令与独立轨迹.md)，执行`python -B sim/write_buffer_turnover/simulation_completion_runner.py --check-inputs`后，单次`--tag ds_write_buffer_turnover_20261014_a`。vlib/vlog各60秒、control/key各-batch180秒，首败停止，DeepSeek只执行/保存证据/报告，不设计或改文件，不旧入口/历史回归/PDS/串口。control6/49拍、key889/44拍、430EV/143 CPU数据请求、完整6笔短程序W及AW/W/响应/取消/排空轨迹严格核；原SOC_TURNOVER69是机会统计，新OP记录实际接受及唯一late的前端状态，不能直接把69记作成功接续数。Codex收到后review_completion.py核原始证据，通过再直接给COM9同冻结P300/V300新wturn_300_01，不审PDS/位流。本轮功能门未开放、HDL/实板未验收；下方“新观察TB/runner未交付”已被本段覆盖。

**最新长期分工（用户2026-10-14纠正，优先于本文下方031临时分工）**：Codex负责优化/RTL以及TB、模型、独立参考、测试脚本设计与封存、任务文档及原始证据审查；DeepSeek负责执行已准备好的仿真/测试并保存整理原始结果；用户负责PDS/下载/KEY0/实板。后续任务和031待办收尾按此执行。031新观察TB/收尾runner/清单已由Codex准备完成，按上方新冻结入口执行，旧“DeepSeek创建后执行”授权已撤销。角色调整与后续静态准备均未改RTL或运行HDL/PDS/串口。

用户要求查看任务结果。Codex发现DeepSeek已有新设计并执行`sim/write_buffer_turnover/build/design_check_20261014_a`编译/control/key，[只读核验收据](../sim/write_buffer_turnover/build/codex_design_check_review_20261014_a/result.json)=DESIGN_CHECK_LOGS_PASS_FORMAL_HANDOFF_INCOMPLETE。36模块/零错零警告、两job正常finish、console/transcript一致；control6/49拍与key889/44拍，同6store/5机会，省5拍；key报告SoC430事件/IRQ1/69接续、总81接续、MLATE0，排空正覆盖。源/软件/7设计身份保持，未发现日志RTL FAIL，实板收益未测。

正式tag目录及DeepSeek报告不存在，control/key真实命令元数据、运行输入副本/Git前后、独立EV/BUS/AW/W轨迹缺失；短组WLOG少最后一笔，外部源/helper/数字检查数未封存。当前**功能门未开放，不给正式上板命令**。不补造缺失metadata，不依据PASS文字宣称独立430事件核验通过。现有runner正则匹配正确。当前唯一待交付[任务031收尾](../DeepSeek/任务031收尾_补齐原始命令与独立轨迹.md)，先找真实遗留证据，必要时仅新观察副本保持刺激/阈值，在尚未占用原正式tag一次补齐，不扩历史回归。角色保持，Codex未重跑HDL/PDS/位流/串口，桥和CPU不改。详见[同阶段顶部](cpu/MINI_写缓冲完成同拍接续_2026-10-14.md)。以下仿真未运行/待设计为初始历史。

## 初始031接续入口（031单项RTL已改，待DeepSeek设计/执行仿真）

用户明确要求030之后下一轮单项优化，先读AGENTS、原接续、001—030总览、030阶段并检查工作树。当前master有大量未提交/未跟踪修改，完整改前清单保存`sim/write_buffer_turnover/build/preparation_20261014_a/git_before.txt`，不清理/回滚。**当前唯一待领取[任务031](../DeepSeek/任务031_写缓冲完成同拍接续关键仿真.md)**，阶段见[写缓冲完成同拍接续](cpu/MINI_写缓冲完成同拍接续_2026-10-14.md)。

030已有原始计数P/V MEM51602799/51701605（24.114%/24.152%），大于分支恢复11.0%、load-use3.9%、IF3.7%；OTHER含正常执行。AW5179976/5160563占命令约93.3%，无读写等待分项，不能把MEM全归因写。RTL确认旧写完成边沿仍因busy拒绝新store，选择只消除该交接空档。主桥新增默认WRITE_BUFFER_TURNOVER_ENABLE1：前端槽空/旧响应周期，旧W确实完成且新请求store可同边沿替换单条写缓冲；旧AW/W/D更新使用旧字段，push保留valid、新aw_sent0，load碰撞保护与排空仍按原路径。

仅主桥变更，旧SHA355145f2…13d7aa保存完整副本与本轮patch，新SHA **2dfa96cac3334c74732d1c2dc5d3f40ffc1aec332ae07296643a033a256b53e0**；CPU仍 **b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3**，135其他登记源/8软件保持，ISA0。I64/D64各2KiB、Zmmul四乘法、030确定分支目标接续保持，仍不是分支预测。静态收据WRITE_BUFFER_TURNOVER_STATIC_PREPARATION_PASS_HDL_NOT_RUN；inputs.json SHA **1b19dad3e2c9321b6729d42cd2455ea49fcb3f7bf7e1e3cbc5cc0406b403b692**。

**本轮分工以用户新要求为准：DeepSeek设计仿真、执行脚本、分析结果；Codex改RTL/任务和阶段文档、审查原始证据。** DeepSeek仅在sim/write_buffer_turnover新增TB/model/独立oracle/最小SoC程序、simulation_runner.py及simulation_inputs.json，封存后一次新control/key；run.py是已有派发入口，设计未交付时拒绝HDL。vlib/vlog各60秒、control/key各-batch180秒，首败停止。CPU不改不抽ISA，不重复030/029/历史CoreMark/PHY，不执行PDS/串口/Git提交；完整覆盖和交付要求见任务。当前**HDL NOT_RUN、功能未验收、实板收益未测**，不把静态PASS写成仿真PASS。任务文件不会自动调用DeepSeek。

收益条件预测：每次符合条件且原空档暴露的接续省一拍，MEM/cycles主要下降，AW无减少机制。接续频率未知，按原AW每笔最多一个直接省拍机会估算约5.16—5.18M周期/0.055秒/原cycles2.41—2.42%，只是机会量估计，非保证收益；分类/重叠可能变化。新增AW/W ready反馈路径实现效果由用户PDS/实际DDR测量体现，不例行审PDS/位流。

最新成功同BIN对照仍 **coremark_i64_d64_zmmul_bturn_300_01：P2.282599413/V2.283394027秒**，不重测。原P300/V300 measure_zmmul300_20261013_a，BIN SHA677ee766…4517d/461c635c…719b、CRC5275/8803保持。新板级目录`sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_300_01`；run_write_buffer_turnover_measurements.ps1已准备COM9/P-V各一次，目前等待Codex WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS而拒绝串口。工具没有PDS或位流检查门。收到DeepSeek结果，同一步核原始证据/更新文档/正式给上板命令；用户实现下载与KEY0，收到本轮新实板结果前不另起032。下节030“无待领取/新优化未实施”为当时历史。

## 前次新对话接续入口（030实板P/V已核PASS，换对话资料已更新）

用户本轮要求换对话前更新交接，并汇总每个任务做过的性能改动。[CPU性能优化任务001—030总览](cpu/CPU性能优化任务001-030总览_2026-10-14.md)已按编号写清硬件改动、目的、测量/软件/测试修复的区别、实际收益及续测边界；新对话先读AGENTS、此入口、总览与[030同阶段顶部](cpu/MINI_CPU分支目标取指同拍接续_2026-10-14.md)。本次只核新日志/写文档，没有启动下一项RTL优化。

整理时发现用户已保存030新实板日志，Codex已独立核验。[最新实板收据](../sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01/codex_review_20261014/result.json)=BRANCH_TURNOVER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS：同冻结P300/V300各123帧/唯一RUN/DDR VERIFY/五CRC5275-8803/KEY0/0重试/13计数及计时守恒，原证据保持。**新成功基线bturn_300_01：P213993695/V214068190cycles、2.282599413/2.283394027秒**；较029 sfwd缩时5.7292%/5.5851%、吞吐+6.0773%/+5.9155%，精确131.429/131.383次每秒。时长不足10秒仅性能比较，原300次不变，无需重复本轮测量。

分支恢复少17078422/16911117cycles，MEM等待增加4092946/4213502，IF−19633/+34474；三者守恒为总cycles减少13005109/12663141。退休、分支次数、AR/AW/总DDR命令、load-use与OTHER保持。当前MEM约24.1%、分支恢复约11.0%、IF约3.7%、load-use约3.9%、OTHER约57.2%含正常执行；AW约93.3%总DDR命令但无读写等待分项，不把MEM全归因写，也不把MEM增量直接判为缓存失效回归。下一单项尚未选择/实施，从该瓶颈评估，不承诺全部等待可消除。

主源码仍CPU b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3、桥355145f2fca4c08cac12525f7ab16a2faae7466953baf49fc021c7bce413d7aa；I64/D64各2KiB真实DRM、Zmmul四乘法、D写命中字节更新、RSP接续、一条顺序写条、D读重叠与同行转发、普通分支目标取指同拍接续。**030不是分支预测**，仍ID确定目标；未实现DIV/REM、misa.M仍0。板级soc_ddr3_top实际覆写MEM_DQ_WIDTH32/DDR_ADDR_MASKc0000000，即256bit用户拍与1GiB窗口；soc_top通用默认仍x16/512MiB，注意按实际实例核对。CPU/UART计时域保持93.75MHz。

固定软件tests/cpu_performance_2b/build/measure_zmmul300_20261013_a：P BIN677ee766fd0fc34d1558d778a343743a1cd9287ecdbbc182cb4681af3374517d，V BIN461c635c46c86c8e719ced403b045bca468ded7299870bf2f87f8547ce11719b，CRC5275/8803。同BIN新优化继续用原300软件与成功bturn日志对照，不重建、不重跑基线。**当前无待领取仿真/待补ISA/待上板测量**；旧030失败/诊断与原Warnings2记录保留，不运行旧tag/备用计数诊断。指定功能收据与key455/control94/两ISA auipc-sb已闭合，不写全量ISA/SoC/PHY或未审PDS时序资源PASS。

协作：Codex负责RTL/TB/软件、关键验证准备、原始证据审查与阶段/交接文档；DeepSeek只执行最新明确任务并写新结果报告/运行目录；用户做PDS、下载、KEY0/COM9。按最新约定不例行审PDS/位流，不新增全量回归或反复询问继续；只有新改动/失败才补直接相关测试。本轮文档更新不授权自动上板或下一项优化。工作树有大量未提交/未跟踪源、IP和成功证据，不清理/重置/覆盖无关改动。

## 前次接续记录（030功能门闭合，当时待用户P300/V300）

[030收尾结果](../DeepSeek/任务030收尾_结果_ds_cpu_branch_isa_port_resume_20261014_a.md)已核原始证据，[最终功能收据](../sim/cpu_branch_turnover/build/ds_cpu_branch_isa_port_resume_20261014_a/codex_review.json)=BRANCH_TURNOVER_KEY_PLUS_ISA_PORT_RESUME_RAW_EVIDENCE_REVIEW_PASS，SHA308e0dfa…538f1c8；四命令exit/native0未超时、14编译模块ErrorsWarnings0、两job零错零警告/正常finish/无RPC，console-transcript归一相同。auipc100/sb496事件各5精确trap/tohost1/muls0/IRQ0、各1MRET，auipc归一架构与旧100事件相同，端口3017/3722警告消失。410+5/25副本/Git与全部历史证据保持，CPU b1114fa3/TB4ee8ada8不再改。

正式key455/LOAD3/TRAP3-IRQ1-RESET1与control94复用不重跑，flow_fast148<194仅为模型内周期。功能门闭合范围限指定CPU关键功能及两ISA样本，不是全SoC/PHY/时序资源/实板PASS。[补充上板交接](../sim/cpu_branch_turnover/build/ds_cpu_branch_isa_port_resume_20261014_a/codex_board_handoff.json)核事件类别、原基线与工具require_gate通过，新bturn日志目录不存在，Codex未运行HDL/PDS/串口，无待领取仿真。

用户生成下载本轮新位流后，直接PowerShell run_branch_isa_port_measurements.ps1 COM9同冻结P300/V300各一次，不例行审PDS/位流；关闭其它串口，每模式KEY0释放等DDR就绪后Enter。新sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01，对照成功sfwd P226998804/V226731331cycles（2.421321/2.418468秒），300次/BIN/CRC5275-8803保持，不重建/重测基线，不足10秒仅比较。完整命令见[同阶段顶部与最后一节](cpu/MINI_CPU分支目标取指同拍接续_2026-10-14.md)。收到日志再核协议/CRC/计数并分析收益，新实测前不另起优化。以下功能门未闭合与待执行均为历史。

## 前次接续记录（030正式key已核PASS，当时ISA收尾待执行）

前续测key455/LOAD3正式PASS已由Codex复核，[key收据](../sim/cpu_branch_turnover/build/isa_port_preparation_20261014_a/key_review.json)=BRANCH_TURNOVER_FORMAL_KEY_RAW_PASS_ISA_PORT_WARNING_STOP：八覆盖56/5/51/96/47/5/35/3、TRAP3/IRQ1/RESET1、flow_fast148<control194；auipc五trap/tohost1/100事件但Warnings2，sb未跑，原git_after缺失保持。只剩旧ISA TB漏连memory_order_busy，Codex已加常量0，未放宽零警告判据，RTL/其它136源/8软件保持。新TB4ee8ada8…92bc3，旧TB归档；旧e26f0bac/7cb5c88e清单和所有失败/诊断不重写，旧入口失效由新清单重绑定。

当前唯一领取[任务030收尾](../DeepSeek/任务030收尾_ISA空闲端口补连与双样本复验.md)，tag ds_cpu_branch_isa_port_resume_20261014_a，清单3672e60a…f17a66/410+5/25副本/14模块。一次vlib/vlog60秒、仅isa_auipc/isa_sb各-batch180秒，首败保留停止；key455/control94复用不重跑。原seed2026101430/五精确trap/tohost1/muls0保持，新两jobWarnings0，auipc架构与旧100事件归一对照。静态精确单行/输入/离线P/V计划通过，tag不存在，Codex没运行HDL/PDS/串口。Codex维护修改/清单/审查及阶段文档，DeepSeek只执行新入口与结果报告，备用诊断入口不派发。

结果后review_isa_port_resume.py核原证据，通过直接给run_branch_isa_port_measurements.ps1 COM9同P300/V300各一次，用户PDS/下载/KEY0，不例行审位流。bturn_300_01对照成功sfwd P226998804/V226731331cycles（2.421321/2.418468秒），300次/BIN/CRC5275-8803保持。当前功能门未闭合，不给上板命令；详见[同阶段顶部](cpu/MINI_CPU分支目标取指同拍接续_2026-10-14.md)。以下原待执行/待授权为历史。

## 前次接续记录（030 LOAD激励缺口已核，当时正式续测待执行）

原030 control94/194cycles PASS、key九组455事件与oracle一致但coverage总闸FAIL，ISA未跑。Codex已核用户追加三诊断：[收据](../sim/cpu_branch_turnover/build/loaduse_resume_preparation_20261014_a/diagnosis_review.json)=LOAD_USE_STIMULUS_GAP_RAW_DIAGNOSIS_CONFIRMED；唯一LOAD0，profile1取指延迟使依赖分支到ID时load已离EX，MEM吸收等待。仅该用例profile0后LOAD3/455事件一致、覆盖全过，load_use RTL表达式与改前相同，限本激励缺口而非全CPU结论。原67失败文件/三诊断/原e26f0bac清单/CPU b1114fa3保持，三诊断key元数据不完整不当正式闭合。Codex自己创建但未执行的coverage_diag_preparation备用入口已替代，不派发。

当前只领取[任务030续测](../DeepSeek/任务030续测_LOAD激励修正与两项ISA补跑.md)，tag ds_cpu_branch_loaduse_resume_20261014_a、清单7cb5c88e…902ccd/327+5/53副本/16模块；新spec唯一load_branch_jalr profile1→0，CPU/TB/model/oracle/阈值/旧冻结文件不改。一次vlib/vlog60秒、key455与isa_auipc/isa_sb三个-batch各180秒、首败保留停止，control94复用不重跑。保持八正覆盖/TRAP3/IRQ1/RESET1、flow_fast<control194、两ISA seed2026101430/五精确trap/tohost1，未全量ISA/SoC/PHY。check-inputs及新测量离线计划静态通过，HDL/新实现/串口未运行，tag不存在。

收到结果Codexreview_resume_loaduse.py核证据，通过直接给run_branch_loaduse_resume_measurements.ps1 COM9同P300/V300各一次；用户PDS/下载/KEY0、不例行审位流。新bturn_300_01对照成功sfwd P226998804/V226731331cycles（2.421321/2.418468秒），300次/BIN/CRC5275-8803保持。当前功能门未闭合，不给上板操作命令；详见[同阶段顶部](cpu/MINI_CPU分支目标取指同拍接续_2026-10-14.md)。以下原030待执行为历史。

## 前次接续记录（普通分支目标取指接续已改，当时030待执行）

用户授权“进行下一步的性能提升”。只改主CPU IF请求/PC：默认BRANCH_FETCH_TURNOVER_ENABLE1，普通ID分支在无pending或旧响应到达时可同拍发目标；真正接受后PC目标+4，背压保留目标，旧pending未返则继续drop/等待，trap/MRET路径保持。新CPU b1114fa3…4a41d3，旧成功3faf81a6快照保留，其他136登记源/桥355145f2/IP/SoC/时钟/Loader/软件8保持；静态通过，HDL/时序资源/实板收益NOT_RUN。

当前唯一领取[任务030](../DeepSeek/任务030_CPU分支目标取指接续关键验证.md)，tag ds_cpu_branch_turnover_20261014_a、清单e26f0bac…81dd08/196+5输入/46副本/16模块。一次编译、关闭功能control94事件、一个key job九程序455事件（94/94/94/94/10/14/16/17/22）、两ISA auipc/sb（seed2026101430，39支持无缺口池），vlib/vlog60秒、四个vsim-batch各180秒、首败保留停止。key含旧响应同拍/延迟drop、目标背压、buffer/load-use、wrong-path error、reset、cause0/1/5、精确IRQ/MRET，八覆盖计数均正、TRAP3/IRQ1/RESET1，要求同模型flow_fast cycles少于control。CPU变更按约定抽2项ISA，沿用五精确trap判据；不历史029/CoreMark/MUL/PHY/旧CPU全套。check-inputs/独立架构参考/PowerShell计划静态通过，tag目录不存在，任务文件不自动执行。

收到结果Codex用sim/cpu_branch_turnover/review.py核原证据，通过直接给PowerShell run_branch_turnover_measurements.ps1 COM9原冻结P300/V300各一次；用户PDS/下载/KEY0，不例行核位流。新日志sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01，对照成功sfwd_300_01 P226998804/V226731331cycles（2.421321/2.418468秒），300次/BIN/CRC5275-8803保持，不足10秒仅比较。详见[本轮阶段](cpu/MINI_CPU分支目标取指同拍接续_2026-10-14.md)。新实测前不另起优化，以下仅评估与无待领取状态为历史。

## 前次接续记录（同行字节转发实板P/V已核，约2.42秒）

用户“查看日志，性能分析”。sfwd_300_01同冻结P300/V300原始日志已独立核验，[实板收据](../sim/mini_board_migration/board/coremark_i64_d64_zmmul_sfwd_300_01/codex_review_20261014/result.json)=STORE_FORWARD_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS：各123帧/唯一RUN/DDR VERIFY/五CRC5275-8803/KEY0/0重试/13计数与计时守恒，BIN/ELF/manifest保持、原日志不动，未重跑/开串口/审PDS位流。

P226998804/V226731331cycles、2.421320576/2.418467531秒、精确123.8993/124.0455次每秒、CPI2.09424/2.09229。对照dread的2.472884/2.468991秒，缩时2.0852%/2.0463%、吞吐+2.1296%/+2.0891%，MEM等待少4789916/4748638cycles（−9.1586%/−9.0906%），几乎解释全部净收益；退休/分支次数/AR/AW/DDR事务/load-use/OTHER相同。当前MEM约20.94%、分支恢复17.8–17.9%、IF约3.48%、load-use约3.7%，OTHER约54%含正常执行。累计较D写优化前同Zmmul300缩时约55.56%、吞吐约2.25倍。UART150来自整秒截断，真实约124；不足10秒仅性能比较，不正式成绩。

保留本轮，新成功同BIN基线sfwd_300_01。下一方向可评估普通分支重定向的目标取指接续，当前CPU redirect时强制关闭取指，重点安全消费/丢弃旧响应及精确异常IRQ；性能收益待实施与实测，不能把分支恢复约18%全算可消除。本次只核日志/分析/更新记录，没有改RTL/IP/BIN或新建任务/运行HDL/PDS/上板，当前无待领取仿真或重复测量。完整分析见[同阶段顶部](cpu/MINI_写缓冲字节转发与同行命中读_2026-10-14.md)。以下待实板记录为历史。

## 前次接续记录（任务029原始证据核验通过，当时待用户同BIN实板测量）

任务029 STORE_FORWARD_KEY_PASS已由Codex核原始命令/日志/输入/副本/Git及事件轨迹。[功能收据](../sim/mini_board_migration/build/ds_mini_store_forward_20261014_a/codex_review.json)=STORE_FORWARD_RAW_EVIDENCE_REVIEW_PASS，SHA d408c91c…5770e8；36模块编译零错零警告、control8/key2238八组全PASS、四命令exit/native0无超时、114920ns finish，两job各4条04030130原文保留、无RPC/FAIL、console/transcript归一相同。268+10输入/11副本/清单46888164…c94494/桥355145f2…13d7aa保持，CPU不改/ISA0。x32同行命中读字节转发关键功能与最小真实SoC通过，x16仅静态，PHY/时序资源/实板收益未测。

[交付报告](../DeepSeek/任务029_结果_ds_mini_store_forward_20261014_a.md)与原日志一致；手工同行1184/同字217、SoC同行同字130、两个W边界各16，FENCE/IRQ/STOP等待各44、fills2/updates69。[补充轨迹与上板交接](../sim/mini_board_migration/build/ds_mini_store_forward_20261014_a/codex_trace_handoff.json)核EV494=489有效事件+5终止JAL、BUS1129、0同步陷阱/1IRQ、133load/71store及AW=W=71；四typed load值−128/128/−128/65408均在写条未排空时实测。功能门已只读通过，新sfwd实板目录不存在。Codex没重跑HDL/PDS/串口；历史027/028与原始029不改，无待领取仿真。

下一步用户生成下载新位流后PowerShell run_store_forward_measurements.ps1 COM9同冻结P300/V300各一次，不例行审PDS/位流；每模式KEY0释放等DDR就绪后Enter，关闭其他串口程序。新日志coremark_i64_d64_zmmul_sfwd_300_01，对照成功dread_300_01 P231832909/V231467889cycles（2.472884/2.468991秒），BIN/300次/CRC5275-8803保持，不重建/重测基线，不足10秒只比较。完整命令见[本轮阶段](cpu/MINI_写缓冲字节转发与同行命中读_2026-10-14.md)。收到日志再核协议/CRC/计数并分析收益，新实测前不另起优化。

## 前次接续记录（D命中读重叠实板P/V已核，约2.47秒）

用户“查看日志，分析性能”。coremark_i64_d64_zmmul_dread_300_01原P300/V300已只读核验通过，[独立实板收据](../sim/mini_board_migration/board/coremark_i64_d64_zmmul_dread_300_01/codex_review_20261013/result.json)=DATA_READ_OVERLAP_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS：各123帧/唯一RUN/DDR VERIFY/五CRC及5275-8803/KEY0/0重试/13计数守恒，BIN/ELF/manifest与wbuf_300_01相同，原证据保持；未打开串口或核PDS/位流。

P231832909/V231467889cycles，2.472884/2.468991秒、121.3158/121.5071次每秒、CPI2.13884/2.13600。对照wbuf的2.667808/2.663332秒，缩时7.3065%/7.2969%、吞吐+7.8825%/+7.8713%。MEM等待再降25.9605%/25.8768%，份额约22.6%；退休/branch次数/AR/AW/总DDR命令/load-use/OTHER保持，收益基本由MEM减少解释。分支恢复约17.5%、IF约3.4%、OTHER约52.9%含正常执行；四项累计较D写优化前同Zmmul300缩时约54.63%、吞吐约2.204倍。不将UART整数150当真实吞吐，不足10秒仅比较，300次保持。

建议保留本轮，新成功同BIN基线dread_300_01。下一方向优先评估写缓冲向同字/同缓存行load按字节转发，保留miss/MMIO/FENCE有序，写完成与DRM读写边沿须处理；计数未拆读/写等待，不能承诺22.6%都可消除，分支约17.5%为另一方向。本次未改RTL/IP/BIN或新建任务/运行HDL/PDS/上板，当前无待领取仿真，不重复历史。完整分析见[同阶段顶部](cpu/MINI_D缓存命中读与写缓冲重叠_2026-10-13.md)。以下待上板/收益未测为历史。

## 前次接续记录（028功能证据已核PASS，当时待用户上板）

[028报告](../DeepSeek/任务028_结果_ds_mini_data_read_overlap_20261013_a.md)已核原始日志/命令/输入/快照/Git，[独立收据](../sim/mini_board_migration/build/ds_mini_data_read_overlap_20261013_a/codex_review.json)=DATA_READ_OVERLAP_RAW_EVIDENCE_REVIEW_PASS，SHA39453df0…b27b46：36模块干净编译及真实SoC/IP加载，control8/key六组1597全PASS，CPU480/IRQ1、early_acks267/I_OVERLAP383/FENCE-IRQ-STOP各44/fills2-updates65/D_OVERLAP578/SOC_D_OVERLAP64，578−64=514。四命令exit/native0/无超时/ErrorsWarnings0/正常finish/无RPC，console-transcript归一同，两job各四原提示；252+10/11副本/Git均匹配，源主桥3e1e6f98/其他136/软件8保持。

额外key trace485EV=480至PASS+5终态JAL，1036BUS/无同步trap/IRQ1；64笔busy1且W0的D读接受地址均820，实测匹配SOC覆盖。control trace0byte符合只记录soc_mode，完整control日志通过，不重跑。旧027原始证据与快照已逐SHA保持；CPU未改、ISA0，x16仅静态，实际DDR收益/新时序资源未测。功能门已只读通过、新板级目录不存在，当前无待领取或重复仿真，Codex未启动HDL/PDS/串口。

下一步用户自行PDS生成/下载本轮设计，直接执行[同阶段顶部PowerShell命令](cpu/MINI_D缓存命中读与写缓冲重叠_2026-10-13.md)：run_data_read_overlap_measurements.ps1 COM9同冻结P300/V300各一次；每模式关闭串口助手/KEY0释放/DDR就绪/Enter，日志coremark_i64_d64_zmmul_dread_300_01，对照成功wbuf_300_01 P250107028/V249687374cycles（2.667808/2.663332秒）。300次/BIN/CRC5275-8803保持，不例行核PDS/位流，不足10秒只比较；收到日志核实际协议/CRC/计数并分析性能，失败先定位，新实测前不另起优化。以下028待领取为历史。

## 首次准备记录（D命中读重叠接入，当时028待执行）

用户“执行下一步性能提升”。基于已核wbuf_300_01 P250107028/V249687374cycles（2.667808/2.663332秒），仅修改主桥：x32 posted写忙时，命中其他完整行的D读经一拍资格寄存放行，tag比较不直接进ready；同一行读/miss/新store仍等旧W，非DDR/FENCE/IRQ排空保持。默认参数DATA_READ_UNDER_WRITE_ENABLE=1自动接已有SoC，其他136登记源/CPU/IP/固定P300-V300保持。新桥3e1e6f98…876794，静态已通过，新HDL/PDS/实际收益NOT_RUN。

当前唯一领取[任务028](../DeepSeek/任务028_D缓存命中读与写缓冲重叠关键仿真.md)，tag ds_mini_data_read_overlap_20261013_a，清单4cbe8ece…0bfd47/252+10/11副本/36真实模块；一次编译、关闭新重叠控制8及关键1597含真实SoC480（129load/67store/1IRQ）、手工提前D读514及SoC提前D读正数，60/60/两次180秒-batch首败停止。CPU不改，ISA0，旧CPU/027/历史CoreMark/PHY不重跑。run_data_read_overlap.py --check-inputs、程序离线oracle和PowerShell离线计划静态通过，新tag目录不存在，任务未自动执行。

结果后Codex核原始证据，通过直接给PowerShell run_data_read_overlap_measurements.ps1 COM9同冻结P300/V300各一次；用户自行PDS生成/下载/KEY0，不例行核位流。新日志coremark_i64_d64_zmmul_dread_300_01，对照上述wbuf成功基线，不改变300次/BIN/CRC5275-8803；不足10秒只比较，新实测前不另起优化。完整边界/判据/后续命令见[本轮阶段](cpu/MINI_D缓存命中读与写缓冲重叠_2026-10-13.md)。以下仅评估/无待领取为历史。

## 前次接续记录（写缓冲实板P/V已核，约2.67秒）

用户“查看日志，性能分析”。coremark_i64_d64_zmmul_wbuf_300_01原P300/V300经只读核验通过，[独立实板收据](../sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01/codex_review_20261013/result.json)=WRITE_BUFFER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS：各123帧/唯一RUN/DDR VERIFY/五CRC及5275-8803/KEY0/0重试/13计数守恒，BIN/ELF/manifest与turnover_300_01一致，原日志保持；无PDS/位流审查或串口执行。

P250107028/V249687374cycles，2.667808/2.663332秒、112.4519/112.6409次每秒、CPI2.30743/2.30413；对照turnover的3.022434/3.014289秒，缩时11.7331%/11.6431%、吞吐+13.2928%/+13.1774%。MEM等待减少约32.2%，目前份额约28.2%；退休/分支次数/AR/AW/DDR总命令完全相同，收益主要来自隐藏写等待。IF/branch周期小增、OTHER/load-use绝对保持，三项累计较D写优化前同Zmmul300缩时约51.05%、吞吐约2.043倍。UART整数2秒/150不是精确成绩，不足10秒只比较，300次保持。

建议保留本轮，新成功同BIN基线wbuf_300_01；下一方向优先评估写条忙时允许命中其他缓存行的D读继续，同址/同缓存行、miss、MMIO/FENCE顺序保持，当前计数未拆读/写等待，不承诺未测收益；分支恢复约16.2%是另一方向。本次未改RTL/IP/BIN或新建任务/运行HDL/PDS/上板，当前无待领取仿真，不重复历史。[同阶段顶部](cpu/MINI_单条顺序写缓冲与SoC排空接入_2026-10-13.md)含完整计数和证据边界。以下待上板/收益未测为历史。

## 前次接续记录（027写缓冲功能核验PASS，当时待用户上板）

[027续测报告](../DeepSeek/任务027续测_结果_ds_mini_write_buffer_soc_resume_20261013_a.md)已核原始证据，[独立收据](../sim/mini_board_migration/build/ds_mini_write_buffer_soc_resume_20261013_a/codex_review.json)=WRITE_BUFFER_RAW_EVIDENCE_REVIEW_PASS，SHA7dd67f6f…fe4aa6。old_program精确复现4000007c/00b52823/cause7/tval10000010/412事件，确认原FAIL为测试程序漏TEST_STATUS RUN导致MMIO拒绝store；原失败35文件及缺失状态保持。修正SoC414事件/无同步trap，early_acks67、I_OVERLAP318、FENCE/IRQ/STOP各等44、fills1/updates65；原前426/control8复用，当前关键840。or530/lhu320各5trap/tohost1/muls0、架构事件与冻结一致，限两ISA样本。

37模块编译及真实SoC/IP加载、236+10输入/13副本、六命令exit/native0/正常finish/ErrorsWarnings0/无RPC或超时、console-transcript归一同/两SoC各四提示、新Git前后全部核过。额外EV trace旧412+fault、新414+5终态JAL核实；源137/软件8/IP保持。功能门已只读通过，新日志目录不存在。当前无待领取/重跑仿真；Codex未执行HDL/PDS/串口，x16仅静态，新时序资源及实际DDR收益未测。

下一步用户自行PDS生成/下载本轮设计，按[同阶段顶部PowerShell命令](cpu/MINI_单条顺序写缓冲与SoC排空接入_2026-10-13.md)运行run_write_buffer_soc_resume_measurements.ps1，COM9同冻结Zmmul P300/V300各一次；每模式关闭串口助手/KEY0释放/DDR就绪/Enter，日志coremark_i64_d64_zmmul_wbuf_300_01，对照成功turnover_300_01 P283353216/V282589565cycles（3.022434/3.014289秒）。300次/BIN/CRC5275-8803保持，不足10秒只比较；不例行核PDS/位流，不先另起优化。收到日志核实际协议/CRC/计数与性能，失败先定位。以下待续测为历史。

## 失败定位与续测准备记录（当时027续测待执行）

027原始证据已核：37模块干净编译、control8/前六组426 PASS，key SoC组51575ns同步trap/Fatal/Errors1、工具exit/native0无超时；两ISA未执行/无git_after，原35文件冻结。静态发现原测试程序直接写TEST_STATUS PASS=2、遗漏RUN=1，原MMIO合同会返回store error；原日志未记录cause/PC/tval，精确归因尚待新复现。主RTL137/软件8/IP身份保持，新增程序仅一条RUN store、正确路径414事件，严格FENCE/IRQ/STOP与自检判据保持。

当前唯一领取[027续测](../DeepSeek/任务027续测_SoC自检RUN补齐与精确陷阱复核.md)，tag ds_mini_write_buffer_soc_resume_20261013_a，清单98aa2479…e001ea/236+10/13副本/37模块；一次编译、原SoC故障精确复现（预测4000007c/00b52823/cause7/tval10000010）→补RUN SoC414→未完成ISA or-lhu（原seed2026101327/530-320事件参考），60/60/四次180秒-batch首个非预期失败停止。control8/前426直接复用，不重复前六组/旧CPU/历史。run_write_buffer_soc_resume.py --check-inputs及离线程序/PowerShell计划静态通过，新HDL未运行，原FAIL不改写PASS。

结果后Codex用review_write_buffer_soc_resume.py核原始证据，完整PASS才直接给PowerShell run_write_buffer_soc_resume_measurements.ps1 COM9同P300/V300命令；不例行核PDS/位流，用户生成/下载/KEY0。wbuf_300_01新目录和成功turnover_300_01 P283353216/V282589565cycles对照保持，300次/CRC5275-8803不改，新性能未测。详见[本轮同阶段顶部](cpu/MINI_单条顺序写缓冲与SoC排空接入_2026-10-13.md)。以下原027待首次执行记录为历史，不再领取。

## 首次准备记录（单条顺序写缓冲主RTL接入，当时027待执行）

用户“执行下一步”。基于已核成功turnover_300_01 P283353216/V282589565cycles（3.022434/3.014289秒），实现x32单条顺序写缓冲：store入条即响应，缓存I可继续、I miss先锁存但AR等旧W排空；全部后续D/非DDR访问有序，CPU FENCE/CSR/MRET/WFI/IRQ覆盖外部排空。仅主桥/CPU/数据互连/SoC四RTL变化，其余133登记源/IP/固定Zmmul P300-V300保持。当前静态检查通过，HDL/PDS/新实板NOT_RUN，不能记功能PASS或性能收益。

唯一领取[任务027](../DeepSeek/任务027_单条顺序写缓冲与SoC排空关键仿真.md)，tag ds_mini_write_buffer_20261013_a，清单ea0ba519…a49c0、189+10输入/16副本/37真实模块；一次编译、关闭功能控制8/七组关键839（含真实SoC413事件及FENCE-IRQ-STOP）、CPU两ISA or/lhu（seed2026101327，旧成功530/320事件直接复用比较），60/60/四次180秒-batch首败停止。入口run_write_buffer.py --check-inputs已通过；任务未自动执行，新tag目录不存在。主桥b64f756d/CPU3faf81a6/互连e8582e27/SoC3fdbe2f5，完整身份及改变前快照见[本轮阶段](cpu/MINI_单条顺序写缓冲与SoC排空接入_2026-10-13.md)。

结果回交后Codex核原始证据、更新本轮记录并直接给PowerShell COM9同P300/V300命令，用户自行生成/下载新位流；不例行审PDS/位流。新日志coremark_i64_d64_zmmul_wbuf_300_01，对照上述turnover成功基线；300次和CRC5275/8803保持，不足10秒只比較。现在实际上板门尚未通过；不重跑历史或在新实测前另起优化。以下“无待领取/仅评估写缓冲”是此前记录。

## 前次接续记录（响应同拍接续实板P/V已核，再缩时约28.5%，约3.02秒）

用户“查看日志，性能分析”。coremark_i64_d64_zmmul_turnover_300_01原P300/V300日志经Codex只读核验通过，[本轮实板收据](../sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01/codex_review_20261013/result.json)=RESPONSE_TURNOVER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS。各123原RVLD帧/唯一RUN/DDR VERIFY/CRC5275-8803/13计数守恒，KEY0/0重试、同冻结BIN/ELF/manifest身份保持；无PDS/位流审查或串口执行。

P283353216/V282589565cycles，按93.75MHz换算3.022434/3.014289秒、99.2577/99.5260次每秒、CPI2.61416/2.60775。对照dwh_300_01的395967938/395398048cycles、4.223658/4.217579秒，缩时28.44%/28.53%、吞吐+39.74%/+39.92%；相对D写优化前同Zmmul300累计缩时约44.57%、吞吐1.804倍。UART整数3秒/100次每秒不是精确吞吐，不足10秒仅比较，原300次不变。

IF等待减少约93.2%至约2.77%份额；MEM绝对减少约11.5%，当前份额36.8%（比例上升不代表绝对退化）；branch恢复约14.2%、load-use新增约3%、OTHER绝对不变。退休/branch_redirects/AW保持，AR小增9902/9002，当前无I/D读或读写等待拆分，不作超出证据的归因。完整分析见[同阶段顶部](cpu/MINI_DDR桥响应同拍接续与性能交接_2026-10-13.md)。

下一方向优先评估写路径/小容量顺序写缓冲：约518万/516万AW占DDR命令93%，需统一读回/缓存/FENCE/MMIO/perf stop排空，不只提前ACK；MEM36.8%不能全算可消除。用户本次要求性能分析，本次未改RTL/IP/BIN、未新建仿真任务/运行HDL/PDS/实板，不重测历史；当前无待领取仿真，新成功同BIN基线为turnover_300_01。以下待上板/收益待测状态为历史。

## 前次接续记录（2026-10-13，026续测功能已核，当时待同P300/V300上板）

[026续测报告](../DeepSeek/任务026续测_结果_ds_mini_response_turnover_decl_resume_20261013_a.md)已核原始证据。[独立收据](../sim/mini_board_migration/build/ds_mini_response_turnover_decl_resume_20261013_a/codex_review.json)=RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS，SHA2b218795…cfd35：20模块编译/实际加载、七组1832/CPU392、1744接续=I1002+D742/CPU522/fills71/updates97、46860ns正常finish。vsim2.824247秒、三command exit/native0/无timeout，ErrorsWarnings0、两原04030130/无FAIL/RPC，console/transcript归一同；214+10输入/21副本/Git前后守恒，原失败30文件保持且原git_after仍缺失。主桥f47ca39d/CPU43e45103/修复TBbc99d609/清单9bfa2e52匹配。

本次独立审查脚本review_response_turnover_decl_result.py兼容ModelSim实际Loading绝对库路径；原任务清单/runner/判据/旧审查源码与原失败证据未改，没重跑HDL。PASS仅x32桥/真实I-D-mul源/最小真实CPU DDR循环，非全SoC/PHY/全ISA/时序/资源/板级性能，x16仅静态。当前无待领取仿真，不重复026/历史或另起优化。

按用户最新流程直接上板，不核PDS/位流。run_response_turnover_measurement.require_gate已只读通过，新日志coremark_i64_d64_zmmul_turnover_300_01不存在；用户自行生成/下载本轮新位流后，关闭串口助手、各模式KEY0释放/等DDR就绪/按Enter，在COM9同冻结P300/V300各一次。完整CMD命令见[同阶段顶部](cpu/MINI_DDR桥响应同拍接续与性能交接_2026-10-13.md)，功能门收据与后续计划见build/response_turnover_decl_resume_preparation_20261013_a/board_handoff.json。P BIN677ee766/CRC5275，V461c635c/CRC8803、300次/93.75MHz保持，不重建/复跑基线，对照dwh_300_01 P395967938/V395398048cycles、4.223658/4.217579秒。PDS/位流本轮未审查、实板NOT_RUN、实际收益待新日志，不记已下载或已测量。

收到新板级日志后继续核协议/DDR VERIFY/CRC/13计数与同BIN性能，基于实测推进下一单项；失败先定位，必要时再核相关PDS产物，不逐步询问继续。以下待续测/未验证状态为历史。

## 前次接续记录（2026-10-13，026声明顺序修复后当时待单次续测）

原026已核原始证据：[失败复核](../sim/mini_board_migration/build/response_turnover_decl_resume_preparation_20261013_a/failure_review.json)=RESPONSE_TURNOVER_TB_DECLARATION_ORDER_COMPILE_BLOCK_CONFIRMED。vlib0/vlog-native2、8处vlog-2388/Errors8Warnings0，DUT端口使用8个mux网早于声明；20模块被尝试编译，主桥无诊断，不能写20模块全部通过。vsim未启动、0/1832、原git_after缺失，不记功能FAIL/PASS或Git前后相等。旧目录30文件/17冻结副本与旧清单05989313已核并保持，未补造/重试。

Codex仅修生成器插入位置与生成TB，将完整mux声明/CPU实例块移到DUT前，新增8网声明前置静态检查；新TB逐文本证明只有块移动，cases/模型/CPU镜像/七组/1832判据/超时保持。RTL桥仍f47ca39d…ba224、CPU43e45103…d6cfe及137源/8软件不变；上板工具功能门仅改到新tag。修复静态PASS，未编译/执行HDL。当前只领取[026续测](../DeepSeek/任务026续测_TB声明顺序修复后单次验证.md)，完整[同阶段顶部](cpu/MINI_DDR桥响应同拍接续与性能交接_2026-10-13.md)。

唯一新tag ds_mini_response_turnover_decl_resume_20261013_a，resume_response_turnover.py --check-inputs已通过；目录不存在，续测清单9bfa2e52…3e218、214工程+10外部、21副本，保护旧30失败文件且不重写旧输入。复用原runner/review，vlib/vlog60秒、-batch单vsim180秒，仅原七组1832/CPU392/fills71-updates97一次，首败停止。无CPU改动ISA0、无旧版/历史CoreMark/PHY/PDS/串口/Git操作。任务文件不自动调用DeepSeek。

结果后用review_response_turnover_decl_resume.py独立核原证据；功能完整核通过后直接给run_response_turnover_measurements.ps1原COM9同P300/V300命令，不核PDS/位流。用户自己生成/下载新位流，新日志turnover_300_01对照成功dwh_300_01 P395967938/V395398048cycles，固定BIN/300/各一次保持；未通过前不上板。以下原026待执行入口为历史，原tag不可再用。

## 前次接续记录（2026-10-13，D写命中实板缩时约22.5%，当时026待首次执行）

用户“查看日志，进行性能提升”。coremark_i64_d64_zmmul_dwh_300_01原始P300/V300已核通过，[本轮实板收据](../sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01/codex_review_20261013/result.json)PASS：各123响应/唯一RUN/完整DDR VERIFY与CRC5275/8803/计数守恒，同冻结BIN。P395967938/V395398048cycles、4.223658/4.217579秒，对照旧同BIN缩时22.54%/22.45%、吞吐1.291/1.290倍；AR363789/359200降92.07%/92.13%，退休/分支/AW保持。当前IF/MEM各约29%，主要旧收益为MEM下降。不足10秒只比较，原300次不变，没有PDS/位流审查。

已推进下一单项：主桥f47ca39df5b17968e653afabd80ab62564d23cd227a71290c5673c96703ba224，ready在IDLE/RSP可用，旧响应消费边沿接受新请求，消除强制IDLE空档。CPU43e45103/I-D-mul IP/容量/SoC/DDR状态/缓存填充与字节写/固定软件保持；数据优先/单笔DDR不变。旧90385桥快照保留，精确指定变换/静态输入检查通过，新的HDL/PDS/板级未运行。完整[阶段记录](cpu/MINI_DDR桥响应同拍接续与性能交接_2026-10-13.md)。

当前只领取[任务026](../DeepSeek/任务026_DDR桥响应同拍接续关键仿真.md)，固定ds_mini_response_turnover_20261013_a（目录不存在），run_response_turnover.py单次vlib/vlog/-batch 60/60/180秒。清单05989313…24cca，177工程+10外部、17新副本、20模块/单顶层，七组576/576/128/128/24/8/392=1832；真实CPU循环392逐退休/64load/66store/1 D AR、预期fills71/updates97。复用DDR模型/transfer并接手工-CPU mux，独立旧响应出队→新接受入队、真实byte write/背压/优先/复位监视。CPU未改ISA0，不重复025/历史CoreMark/SoC全套/PHY。首败保留停止，不重试/改判据或权限，任务文件不自动调用DeepSeek。

结果交来后只读review_response_turnover.py核原始证据，通过就直接给新工具run_response_turnover_measurements.ps1上板命令，不审PDS/位流。用户生成/下载新位流及KEY0/COM9，新日志coremark_i64_d64_zmmul_turnover_300_01，原P300/V300各一次（123响应/唯一RUN离线计划已准备），对照刚成功dwh_300_01的395967938/395398048cycles；不重建BIN/复跑基线。待026前不开展其它RTL优化。以下旧等待实板/旧PDS审查记录为历史。

## 当前流程约定（2026-10-13，DeepSeek审查后直接给上板命令）

用户最新要求：DeepSeek任务结果经Codex原始证据核验通过，直接提供上板/跑分命令；不再例行核对PDS产物或位流，不等PDS审查收据。用户自行生成并下载新位流、执行KEY0/COM9；上板不成功时再按需定位。收到实板日志后继续核验、分析性能并推进下一轮单项提升，无需逐步确认。固定BIN/成功对照/新日志目录和首败保留原则保持，未审查PDS不记PASS。

本轮run_data_write_hit_measurement.py已改为仅依赖025独立功能收据与已审核源/原始证据，原冻结300软件检查保持；不读取PDS最终收据或比特流。当前仍待用户新位流下载及COM9 P300/V300日志，上板命令见[D写命中阶段顶部](cpu/MINI_D缓存写命中更新与字节写接入_2026-10-13.md)。以下本轮已完成的PDS审查是历史事实，不是今后上板前置步骤。

## 前次接续记录（2026-10-13，D写命中最终PDS已核PASS，当时待用户下载及同BIN实板测量）

[025交付报告](../DeepSeek/任务025_结果_ds_mini_data_write_hit_20261013_a.md)已核原始证据，[本轮codex_review](../sim/mini_board_migration/build/ds_mini_data_write_hit_20261013_a/codex_review.json)=DATA_WRITE_HIT_RAW_EVIDENCE_REVIEW_PASS：八设计模块、七组512/384/8/16/12/9/4共945、唯一RESULT/fills80/updates135、47380ns正常finish、三命令exit-native0/no timeout，vsim1.6052982秒。ErrorsWarnings0、两原04030130/无RPC，console/transcript换行归一相同；226+9输入/10副本/Git前后保持，桥90385fdd/新D byte IP/CPU43e45103/固定300软件匹配。Codex没重跑HDL/PDS/serial，PASS限x32桥+真实I/D DRM用户口模型，非SoC执行/PHY/时序/资源/实板，x16仅静态。

用户已生成新PDS，Codex已核最终原始证据。[本阶段PDS收据](../sim/mini_board_migration/build/data_write_hit_preparation_20261013_a/pds_review.json)=DATA_WRITE_HIT_FINAL_PDS_AND_BOARD_HANDOFF_PASS，SHA6fa31cad…e5f92；137登记源/固定软件保持，RISCV.pds仅生成元数据变化、语义配置保持。六阶段Errors0、seed5根产物匹配，全部已声明约束满足；93.75MHz core setup慢/快+0.661/+4.695ns，hold+0.136/+0.100ns，TNS/失败路径0。资源11098LUT/12656FF/16DRM/4APM，相对旧位流+331LUT/−11FF。D四DRM的BWEA分组及32byte mask的8192真值检查符合fill/strobe；Loader两DAT与当前综合8单元INIT逐项匹配，当前PNR清单无INIT且旧generate_netlist不复用，未独立解码位流INIT/映射。完整边界见[同一阶段顶部](cpu/MINI_D缓存写命中更新与字节写接入_2026-10-13.md)。

新根位流generate_bitstream/board_top.sbit SHA **e5045f66bec0268c644a0a7666a46599490cf16e327b6185557fe6173d4daa48**，9188552byte、17:10:20 +08:00生成。新工具require_gate已只读通过；新实板目录不存在。用户尚未报告下载这份新位流，实际DDR收益仍未测；Codex没启动PDS/HDL/下载/串口。不重跑025/历史，不更新冻结旧输入清单，不启动另一优化。

用户下载上述新位流后COM9同冻结P300/V300各一次，新日志sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01；新工具run_data_write_hit_measurements.ps1/CMD命令/每模式KEY0释放等DDR就绪/123响应各唯一RUN均已写同阶段。对照成功coremark_i64_d64_zmmul_300_01/zmmul P511184720/V509875909cycles，BIN677ee766/461c635c与CRC5275/8803保持，不重建/重复基线，不足10秒只比较。收到新板级日志后继续核完整协议、CRC/计数守恒、同BIN cycles/AR/MEM收益，不逐步询问继续。以下待PDS/待领取/静态准备为历史。

## 前次接续记录（2026-10-13，D写命中字节更新主RTL已接入SoC，025关键仿真待DeepSeek）

用户生成dcache字节写后已授权“修改RTL，接入SoC”。主桥SHA90385fdda4b5eb5018e988187827c3675558ae7ce19cf6b9e53a992c519f4b44，现连接wr_byte_en32：fill mask全1，x32写命中在原AW/W完成边沿用锁存行/槽/数据/strobe更新，保留Dvalid/tag；写miss不分配，I仍原失效，x16保持旧数组/失效。外部请求响应/共享仲裁/DDR控制状态转移保持，CPU43e45103/SoC顶层/Loader/软件不改；已有soc_top g_ddr.u_ddr_bridge和MEM_DQ_WIDTH32设置自动使用新设计。登记137源中只桥和用户新D IDF/wrapper3项改变，项目61adbe3c保持。完整[新阶段记录](cpu/MINI_D缓存写命中更新与字节写接入_2026-10-13.md)。

当前只领取[任务025：D写命中关键仿真](../DeepSeek/任务025_D缓存写命中更新关键仿真.md)，run_data_write_hit.py --check-inputs已静态通过，固定tag ds_mini_data_write_hit_20261013_a，226工程+9外部/清单7d88cd3ef7f31af185531cd0358498810336710029c1284ac310bb5d44b06133；单次vlib/vlog/-batch单顶层945项七组，60/60/180秒、首败停止。真实I/D DRM8模块，旧DDR模型/transfer复用、接受后毒化当前请求线，独立metadata/backing memory/真实byte write时刻监控。CPU没改ISA0，控制器/仲裁没改不补历史SoC/PHY/CoreMark；10新副本/Git/原两04030130/唯一RESULT945必需。Codex没有编译/执行HDL，任务文件不自动调用DeepSeek。static_review=DATA_WRITE_HIT_RTL_AND_KEY_TEST_STATIC_PREPARATION_PASS_HDL_NOT_RUN，x16仅静态，无新功能/时序/板级PASS。

已连续准备本阶段pds_handoff.json绑定137源、board_top/PG2L200H/FBB676/-6/core93.75MHz/Loader INIT/预期APM4-DRM16，board_plan.json及两离线123响应/唯一RUN计划使用原冻结Zmmul P300/V300（677ee766/461c635c、CRC5275/8803）。仿真核证后用户新PDS，Codex核多角时序/源/实际byte write映射/初始化/新位流再生成本阶段PDS gate，用户下载新位流后COM9新P/V各一次。新工具run_data_write_hit_measurements.ps1及CMD命令见阶段文档，新日志sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01，对照成功同BINcoremark_i64_d64_zmmul_300_01/zmmul P/V511184720/509875909cycles，不重复原测量/不重建BIN；不足10秒仅比较。旧根bit64445ecf仍旧D写失效，不能用于新收益验收；新功能/时序/资源/收益都待结果。收到025报告连续核证据并衔接用户PDS/板级，无需询问继续，不自动其它优化。

## 前次接续记录（2026-10-13，Zmmul300实板P/V核验通过，同位流归一吞吐约1.91/1.98倍）

用户已重新生成dcache字节写配置，Codex本次只读核验，[IP配置收据](../sim/mini_board_migration/build/data_write_hit_preparation_20261013_a/ip_config_review.json)=DCACHE_BYTE_WRITE_IP_STATIC_CONFIG_PASS_BRIDGE_PORT_PENDING。IDF/wrapper一致：WR_BYTE_EN1/BE_WIDTH32/BYTE_SIZE8、写256×64/读32×512=2KiB、OUTPUT_REG/FAB_REG0、SYNC复位/原clock-strobe-init选项保持；新增wr_byte_en[31:0]，RD_BE_WIDTH4为相应派生值，宽度比8符合厂家byte-write静态限制。相对既有137登记源仅D IDF与wrapper改变，厂家底层、I IP/CPU/桥/Loader/项目均保持，项目SHA仍61adbe3c，根位流仍64445ecf旧已验配置；新IP源码不改变已下载硬件。当前桥d8ae0409的u_data_data_ram没有连接wr_byte_en，写命中仍整行失效，不能把静态IP配置PASS写成接入/功能PASS。接入需整行填充mask全1、写命中使用槽位扩展CPU wstrb并在原DDR写完成边沿更新D、I仍失效；本次用户只要求检查，未修改RTL/生成任务或执行HDL/PDS/串口。旧冻结功能收据/任务不刷新，不重跑旧测试，新优化尚未实施。

前次性能评估记录：用户询问下一步提升，当时仅只读评估/记录，未改RTL/IP/BIN/PDS或新建/执行测试。下一项建议D-Cache写命中按strobe更新、仍阻塞write-through/no-write-allocate：当前store命中即整行失效，后续同行load可能重新读DDR。评估时D IP byte write未开启；用户后续授权实施时需其生成开启8bit字节写、预期32byte enable的原256×64写/32×512读D IP，核实际端口/配置，I64容量/CPU/DDR原写完成时刻/单事务保持。新收益幅度未知，无写致重填或读写等待分项，不把MEM45.5%全算可消除；写缓冲为后续更大排序阶段。具体方案/验证范围/官方排序参考见[本轮阶段顶部](cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。当前没有新的待领取任务，等待用户选择/授权下一项，原300完成结果保持。

用户完成新P300/V300各一次，日志sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul。Codex只读核完整RVLD各123响应/唯一RUN/VERIFY/无额外RX或自动重试、UART五CRC(final5275/8803)/rv32i_zmmul/300次/93.75MHz/state3/13计数守恒、新固定BIN/manifest/137登记源/项目/软件门与位流64445ecf…ac8ee4匹配。[本轮审查收据](../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/codex_review_20261013/result.json)=ZMMUL300_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_NORMALIZED_PERFORMANCE_REVIEW_PASS，原6份新/同位流旧/历史日志逐哈希保持，Codex未开串口/启动HDL/PDS。FPGA下载为用户报告，本地位流SHA不是独立读回。

新P/V分别511184720/509875909cycles、5.452637013/5.438676363秒、精确55.019250/55.160480次每秒、每次1703949.067/1699586.363cycles。对照同位流原RV32I120（每次3251083.342/3368090.025cycles、28.836542/27.834767次每秒），归一吞吐1.907970/1.981712倍，每次耗时下降47.5883%/49.5386%；含ISA/代码生成及布局变化、迭代不同初始化摊销差，不能当纯IP延迟倍数。新CPI4.716083/4.705159较旧3.918106/3.816455上升，但每次退休指令下降56.4565%/59.0697%，总工作周期下降。每次DDR事务下降40.3575%/40.4035%、AR36.8040%/36.7865%、AW43.1860%/43.2738%、分支次数63.8119%/66.5179%。

新MEM周期占45.6177%/45.4735%，IF22.5899%/22.7058%，branch recovery约7.8%，OTHER约24%；OTHER比instret均多14136000周期（约2.8%全周期），与EX乘法等待归类相符，但无专用板级MUL计数不能当直接MUL退休/等待观测。访存/取指仍是主要瓶颈，现有计数不分I/D读或读写等待，不能仅凭AW量归因store。UART打印60来自整秒5截断，真实约55；时长不足10秒提示为预期门，CRC正常，仅固定软件性能比较，不正式成绩。每模式单次无波动估计，不自动加迭代数或重跑。

硬件乘法CPU关键功能/短CRC、用户PDS时序资源/身份、原RV32I120与新Zmmul300实际DDR测量这条已授权路径完成。无待领取仿真/上板步骤，不启动另一RTL优化；原P1退出UNKNOWN和旧编排记录保持历史，24续测功能门有效。当前范围仍Zmmul而非完整M，DIV/REM不支持。完整分析/证据与未覆盖范围见[阶段顶部](cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。以下待300实板/待V1/旧计划为历史。

## 前次接续记录（2026-10-13，024 V1原始证据核验PASS，300次软件门完成；下一步用户同位流P300/V300）

[024续测交付报告](../DeepSeek/任务024续测_结果_ds_cpu_zmmul_coremark_v1_resume_20261013_a.md)已由Codex核原始证据，实际运行一次V1、复用原compile/P1、不重跑P1/vlib/vlog。新vsim1321.167秒/exit0/native0/not timed_out3600，唯一RESULT PASS、正常finish、ErrorsWarnings0、两条04030130/无RPC，console/transcript一致，UART1121byte/五CRC18f2-e3c1-0747-8d84-e3c1/rv32i_zmmul/iterations1/state3，冻结1842118cycles/361057instret/七分类及AR66429+AW17173=83602守恒；全程TB11085406cycles/4275052retired/AR72198/AW21363，MUL9618/矩阵9396。两统计区间不混为性能成绩。

[独立收据](../sim/cpu_zmmul/build/ds_cpu_zmmul_coremark_v1_resume_20261013_a/codex_review.json)=ZMMUL_P_V_SHORT_CRC_AND_300_HANDOFF_RAW_EVIDENCE_REVIEW_PASS：新74输入/旧62产物及原421+11门、67新冻结副本、137登记源/新300软件/位流匹配、Git前后相同；另核worker launch/entered/result同pid44368且单V1，6库文件新旧全文SHA都相同。software_gate SHAcb94c1e3…447eca，旧目录不改、旧P1 native exit UNKNOWN仍保持，不倒填旧runner PASS。新软件功能门以P1原始证据复用+V1本次正常执行闭合；不是300实板或成绩。

当前无待领取仿真，不再运行续测--start。工具run_zmmul300_measurement.require_gate只读确认通过，[300上板交接收据](../sim/cpu_zmmul/build/preparation_20261013_a/board_handoff_zmmul300_after_v1.json)=ZMMUL300_SAME_BITSTREAM_BOARD_HANDOFF_READY_NOT_RUN，新板级日志目录尚不存在。沿用用户已下载的64445ecf…ac8ee4位流，不需新PDS/下载，COM9新P300/V300各一次/123响应/唯一RUN/KEY0每轮，P300 BIN677ee766…74517d/CRC5275，V300461c635c…11719b/CRC8803。CMD完整命令见[本轮顶部](cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。原RV32I120实板结果复用，比较cycles/iteration与iterations/second，实际不足10秒只比较、迭代差/初始化摊销披露，不自动增迭代数或重复测量。Codex没有重跑HDL/启动PDS/开串口，等待用户300日志；新实板收益仍未测。以下V1待运行/旧报告等待/120新软件计划均为历史。

## 前次接续记录（2026-10-13，用户授权V1最小续测，新Zmmul改300次；构建与续测静态准备完成）

用户明确要求补024 V1/收尾后同已下载位流运行新Zmmul，并进一步指定Iterations从120提高到300。已独立构建tests/cpu_performance_2b/build/measure_zmmul300_20261013_a的P/V300：P BIN677ee766…74517d（15204byte、final CRC5275）、V461c635c…11719b（15212byte、final8803）。同配方GCC15.2.0/-Os/ilp32/noLTO/93.75MHz/2000byte/rv32i_zmmul，native300 CRC参考新生成（dummy clock不是成绩）、全ELF白名单通过/28 MUL/DIV-REM禁用；与冻结Zmmul120 BIN逐字节核只有seed4_volatile四字节120→300，sections/symbols/代码/port相同。旧RV32I120/Zmmul1和120所有产物与源逐哈希保持，未重跑旧仿真或板级测量。

当前只交[任务024续测：V1与300次软件交接](../DeepSeek/任务024续测_V1验证与300次软件交接.md)。原P1功能证据完整、native exit缺失/旧result RUNNING的中断原因未知，旧编排不倒填；没有新的旧停止报告，用户本轮新指令授权最小续测，不再等旧报告作为前置。新tag ds_cpu_zmmul_coremark_v1_resume_20261013_a，resume_coremark_v1.py --start后--status查询，独立后台worker/原生日志；仅V1一次，复用/复制原已验6份编译库、P1不重跑、不重编译。基于P1实测26:12，新V1单vsim3600秒，保留原900秒任务不改，首败停止。清单coremark_v1_resume_inputs.json SHA119e0853d69fa4aac1a55bbf36c226c9b53a59393a5053796d9b8362f2e1632a保护74新项、旧024目录62文件及原421+11输入门；当前.settings纳入新Git基线，不删除。v1_300_static_review=V1_ONLY_CONTINUATION_AND_ZMMUL300_STATIC_PREPARATION_PASS_HDL_NOT_RUN，入口AST/PS语法/旧输入/软件身份/离线parser好CRC及坏CRC拒绝、123响应+唯一RUN计划均通过。Codex没有编译/启动HDL或worker、没有开串口/PDS；任务文件不自动调用DeepSeek。

DeepSeek交V1报告后Codex只读review_coremark_v1.py核原始证据生成codex_review.json，新的software_gate+Codex收据闭合软件功能门，同时保留旧P1 native exit UNKNOWN。之后用户用已下载新位流64445ecf…ac8ee4/COM9，新工具run_zmmul300_measurements.ps1运行新P300/V300各一次至sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul；工具在功能门/Codex收据缺失时阻止实板，离线plan不受影响。CMD兼容完整命令已写本轮顶部/任务，不用CMD直接输入&。

原本轮RV32I120 P/V390130001/404170803cycles（4.161387/4.311155秒）日志复用，不重复；与新300按cycles/iteration和iterations/second比较，不直接比较总秒数，披露迭代数与初始化摊销差。300次不保证至少10秒，实际不足只性能比较，不擅自再加迭代数。新Zmmul300实板收益仍未测、V1仍未运行，不改RTL/IP/PDS/时钟或自动另一优化。以下120新软件计划/等待旧报告/待PDS等为历史。

## 前次接续记录（2026-10-13，I64/D64+Zmmul位流原RV32I固定120次实板P/V核验通过，新乘法软件仍待V1）

用户已完成COM9原固定RV32I120次performance/validation各一次。Codex只读复核完整UART/五CRC/129响应及唯一RUN/DDR VERIFY/13计数守恒/原BIN身份，两个日志绑定新本地位流64445ecf…ac8ee4；当前137登记输入与PDS收据全部保持。新日志在sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/rv32i，[独立审查收据](../sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/codex_review_rv32i_20261013/result.json)=I64_D64_ZMMUL_BOARD_FIXED_RV32I_PV_RAW_EVIDENCE_REVIEW_PASS，原始四份日志保持、Codex未开串口/启动仿真或PDS。FPGA下载为用户报告，本地位流SHA不是独立读回。

对照成功I32/D32 coremark_idrm_d32_01的同BIN：P398389378→390130001cycles、4.249487→4.161387秒、CPI4.001056→3.918106、吞吐+2.1171%；V412352500→404170803cycles、4.398427→4.311155秒、CPI3.893712→3.816455、吞吐+2.0243%。新精确120/秒为28.836542/27.834767，UART打印30为整秒截断结果。两模式DDR AR减少9.2146%/9.2767%、AW/instret/branch_redirects逐项相同；新MEM周期占38.8945%/37.4998%、IF24.4511%/24.8121%。归因范围为组合新硬件配置的同BIN结果，不能拆分I64/D64或当成乘法收益；原RV32I ELF没有硬件MUL。每模式单次无方差估计，不足10秒只性能比较，UART Errors detected是时长门而非CRC失败。

本轮原RV32I实板测量已经完成，不重复。024仍result RUNNING/completed空，V1不存在；P1完整功能证据复用、编排收尾/native exit仍缺，保持原证据与.settings差异，不伪补。下一步先收DeepSeek停止/中断报告，补必要V1/收尾，功能门完整后同已下载新位流跑独立Zmmul120次P/V各一次到同根zmmul目录，与本轮rv32i比较乘法软件路径收益；既有步骤/命令见[本轮阶段顶部](cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。不自动另一RTL优化，不重建BIN或重跑历史。以下实板尚未执行/待PDS等内容是历史记录。

## 前次接续记录（2026-10-13，用户已下载新Zmmul位流，PDS审查通过；024 P1证据完整、V1未完成）

用户报告已下载当前I64/D64+Zmmul位流，根board_top.sbit 13:19:03生成、9188552byte、SHA64445ecf…ac8ee4，旧成功d60f9ce2证据保留。当前PDS审查收据sim/cpu_zmmul/build/preparation_20261013_a/pds_review_20261013/receipt.json=ZMMUL_FINAL_PDS_TIMING_RESOURCE_SOURCE_AND_SYNTH_INIT_REVIEW_PASS：137源/IP/约束保持，项目只IP组顺序/元数据变化，CPU43e45103/桥d8ae0409；六阶段无错误、seed5、core93.75MHz setup慢快+0.520/+4.608ns、hold+0.146/+0.105ns，LUT10767/FF12667/APM4/DRM16。PNR实际四u_mul APM/16DRM/13计数器，Loader IDF/生成/综合8DRM所有INIT位与成功DAT相同、cache INIT0；当前PNR无INIT、末级导出网表旧，未伪用，精确INIT审至综合级并匹配新生成链，未独立解码位流INIT。用户下载为用户报告，Codex未编程/开串口，实板跑分未执行。

[任务024](../DeepSeek/任务024_Zmmul新CoreMark短CRC关键仿真.md)原tag的P1现有完整RAW PASS/finish/ErrorsWarnings0、1122byteUART/五CRC/13计数守恒、9618 MUL/9396矩阵MUL；Codex只读严格parser核通过，pds_review_20261013/task024_p1_readonly_review.json留证。原result仍RUNNING/completed空，P1 command.json/native exit未生成、V1目录及git_after不存在，当前无vsim进程；整体尚未完成，编排中断原因未证，不补造exit/timeout/git或复跑P1。024 git_before后唯一新增ipcore/mul/.settings（[not_show_again]、20byte、13:39:36），421输入全部保持；未删除用户元数据，收尾Git差异与功能判据分开。先待DeepSeek原完整停止/中断报告，再补必要V1/收尾，不启动其它仿真或改当前源/清单/日志。

用户已下载新位流，现可先按[同一阶段最新顶部](cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)原120次rv32i P/V各1轮（已有成功软件，不依赖新ISA软件门）；新Zmmul120次P/V待V1及024完整证据后。COM9/每轮KEY0/原129新123响应/唯一RUN/先败停止，新日志sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/{rv32i,zmmul}，Codex无串口/跑分。不重复原测量、不足10秒仅比較，新CRC套件/实板性能仍待；用户下载为用户报告，末级INIT未独立解码，不写实板PASS。下文PDS待生成/根bit旧/024待启动或仍运行为历史。

023续测原始证据已核：两库各14模块/七命令0/ErrorsWarnings0，旧新lhu各320架构事件及events.log逐字节同（fa225db4…bc6e），or530事件，三例5精确trap/tohost1/MUL0、console/transcript/40+原305/10/冻结源/新git守恒，无RPC/超时。原E4 FAIL确认为旧TB漏启动CSR探测的判据缺口，限lhu样本；旧失败/缺失git_after保留。续测目录codex_review.json=CPU_ZMMUL_KEY_FUNCTION_AND_TWO_ISA_RAW_EVIDENCE_REVIEW_PASS。合并原七例IP128/168、CPU2839/396与两ISA样本，硬件乘法关键功能门关闭；非全ISA/SoC/PHY/PDS/板级PASS。CPU仍43e45103…d6cfe，PDS c5f87d11…a6916，桥I64/D64 d8ae0409，misa40000100/DIV-REM非法，原Loader/120次BIN保持。

已独立构建tests/cpu_performance_2b/build/measure_zmmul_20261013_a/的P/V1与P/V120。保持算法/端口/-Os/ilp32/noLTO/同RV32I libgcc/2000byte/93.75MHz，仅-march/FLAGS=rv32i_zmmul；全ELF白名单/arch属性正确，无DIV-REM，每份28静态MUL/矩阵5点，短/120 BIN仅seed4=1/120四字节不同，原输出源身份保持。新P120 ab956eb4…39906/15204byte、V120 4168c1c4…febc1/15212byte；各较原少732byte，是代码大小变化而非性能结果。build_review=ZMMUL_SOFTWARE_BUILD_AND_ISA_AUDIT_PASS_CRC_SIM_PENDING，新CPU CRC尚未运行。

当前只领取[任务024新Zmmul CoreMark短CRC](../DeepSeek/任务024_Zmmul新CoreMark短CRC关键仿真.md)，run_coremark_crc.py --tag ds_cpu_zmmul_coremark_crc_20261013_a，421工程+11外部、清单ca07e018…47605；真实MUL/I-D原语+当前SoC/x32用户口模型34模块，一编译/P1-V1各一次，真实UART解码/热点MUL退休/CRC五项/13计数守恒。vlib-vlog60秒、明确新增CoreMark单vsim900秒、60Mcycle watchdog/-batch/首败停止，不重跑023/旧版/ISA/旧CoreMark/PHY/工具预检，不改环境/权限/源码/判据，不碰PDS/串口/Git。Codex只软件构建和静态核对，coremark_crc_static_review=ZMMUL_SOFTWARE_AND_CRC_PREPARATION_STATIC_PASS_HDL_NOT_RUN，新HDL未编译或运行；任务文件不自动调用DeepSeek。

[同一阶段顶部](cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)已连续准备最终PDS和实板四次固定测量：pds_handoff_zmmul.json绑定137实际登记源（旧130+mul6+补计未改csr_defs.vh1）、board_top/core93.75MHz、预计APM4/DRM16、Loader INIT/新bit；仅用户执行PDS，建议024后且不与仿真并发。board_plan_zmmul.json绑定同新位流原120 P/V各1轮129响应、新Zmmul120 P/V各1轮123响应，COM9，新日志sim/cpu_zmmul/board/coremark_i64_d64_zmmul_01/{rv32i,zmmul}，两工具命令/KEY0步骤已写好，计划无串口。新软件CRC通过且新PDS/位流核验后用户上板；同BIN比较组合硬件配置，再同硬件比较ISA/乘法代码路径，新旧退休/分支不要求相等。不足10秒只比较。根成功bit仍I32/D32 d60f9ce2，新CRC/时序/资源/实板性能未验收。收到外部结果后继续核证据/实施交接，不重复询问继续、不自动另一RTL优化；下文旧等待/诊断/仅评估为历史。

用户询问下一项性能提升，本次仅只读评估、未改RTL/IP/BIN/判据或创建新任务/执行测试。建议后续转CPU硬件乘法，先四条Zmmul再补除法为完整M；原120次P/V反汇编重新核对14个软件mul静态调用、矩阵5个调用点，非动态占比，不承诺倍数。此路线需独立新增ISA软件，原rv32i BIN加硬件不能自动受益；原固定BIN约定未取消，只有用户后续授权才新增软件/CPU实施。若严格原BIN，写缓冲为后续候选但缺读写等待分项，不盲目实施。详见D64阶段顶部评估，当前仍等待最终I64/D64用户PDS/实板，新时序/收益未测，所有既有成功证据保持。

022 `ds_mini_ddrm64_20261013_a`已由Codex核验原始证据PASS：三命令0，真实8模块/单顶层，Errors/Warnings0，八组645/147/271/139/640/515/584/22共2963、唯一RESULT PASS、TB483行163480ns/Iteration1正常finish，vsim1.598504秒；两条04030130原文/无其他错误或RPC。console2856byte/transcript2815byte统一换行后全文同，原始字节不同；Loading实际9条=sv_std.std+8 work模块。桥d8ae0409…5cf09、清单c709ff32…cc672、259+2+5+2/八副本/git前后快照保持。执行目录codex_review.json=MINI_DATA_DRM64_RAW_EVIDENCE_REVIEW_PASS，旧021/原失败证据保持，Codex没有重跑HDL或修改设计。

当前无待领取仿真，不重复022/021/旧版/ISA/Hello/CoreMark/PHY/工具预检。PASS限x32 I64/D64真实I/D DRM桥级关键功能+功能DDR用户口模型；CPU未改ISA0、x16仅静态，没有完整SoC/PHY/实板结论，batch不等于宿主IPv6修复。**下一步用户最终I64/D64 PDS，板子不可用不妨碍用户实现，实板待可用；完整[本轮阶段顶部](cpu/MINI六十四行D缓存评估修改与交接_2026-10-13.md)已准备PDS核对/上板步骤，不逐步问继续。**

build/data_drm64_preparation_20261013_a/pds_handoff.json=MINI_DATA_DRM64_READY_FOR_USER_PDS_BOARD_NOT_TESTED绑定功能收据/130实际登记源-IP-约束/项目配置、原成功Loader/10软件项和I32/D32基线；项目快照与20份冻结PDS原证据引用复用、不重复复制。board_plan.json绑定COM9原120次P/V各129响应/唯一RUN/BIN-manifest及coremark_i64_d64_01（当前不存在），仅离线准备、未开串口。

用户重新载入RISCV.pds沿用board_top/PG2L200H/-6/FBB676/core93.75MHz/原两IP及约束，完成最终编译-综合-映射-PNR-多角时序-位流。Codex核130源d8ae版/输出时间/所选seed根ADFs-netlist-bit同源、各setup-hold汇总/最差core路径/FF-LUT-DRM、I/D各64 metadata和完整2KiB地址使用/宽数据FF阵列消失、Loader8单元各128 INIT/config/原DAT-BIN保持、新位流SHA。预计I/D各4DRM/全局16仅估计，相对I32/D32两项metadata理论增1792bit不等于物理FF；旧基线FF11273/LUT10639/DRM16、setup慢/快+.681/+4.639ns/hold+.142/+.102ns。根位流仍d60f9ce2 I32/D32，新时序/资源/位流未核验。

PDS通过、用户下载核过新位流且板子可用后，COM9原performance_120/validation_120各1轮，新coremark_i64_d64_01，对照成功coremark_idrm_d32_01 P/V398389378/412352500cycles、4.249486699/4.398426667秒。原BIN不重建/不补短测或中间I64/D32，不覆盖旧日志；组合收益不能拆分归因D64，I64/D32只有功能证据没有硬件测量。回交后连续核完整协议/DDR VERIFY/CRC d340-200d/13计数/固定软件和本地位流身份及性能，不足10秒仅比较。本地SHA不是FPGA独立读回。新硬件收益待测，用户执行PDS/下载/KEY0/串口，不自动其他RTL/CPU优化。下文022待执行/NOT_RUN为准备历史。

用户不在板子旁边，明确要求进行下一步性能提升；本轮单项D32→64，主RTL现I64/D64各2KiB。桥SHA **d8ae040965e92b97b859b5125c775cc95a4493f752d64100486da2f3c5b5cf09**，D valid/tag64/read-fill index6、IP写6bit fill/读DA[10:2]、reset64；I64/DDR FSM/响应/数据优先/CPU/93.75MHz/IP/PDS/Loader/原120次软件保持，所有store仍DDR直达/完整tag失效。现有dcache WR256/AW6-RD32/AW9满足容量，不重生成IP。只有static/精确最小变换/AST/计划/输入检查通过，新的HDL/PDS/实板未运行。用户其他未提交改动保持。

当前只领取[任务022](../DeepSeek/任务022_MINI_I64_D64关键仿真.md)，[本轮D64记录](cpu/MINI六十四行D缓存评估修改与交接_2026-10-13.md)。run_data_drm64.py标准-batch/-logfile/单顶层，原8真实模块，60/60/180秒，只一次八组645/147/271/139/640/515/584/22=2963检查，ISA0。新清单c709ff32…cc672保护259项+2厂家模型/5工具/2参考；--check-inputs退出0。模型/transfer/同步hit时延/1ms watchdog保留，I监视任务保持；D64全512word、1KiB分离/2KiB冲突、D63写失效/锁地址/坏ID-last/复位/源切换覆盖。准备build/data_drm64_preparation_20261013_a/preparation.json=MINI_DATA_DRM64_STATIC_PREPARATION_PASS_HDL_NOT_RUN，rtl/tb patch留证。固定tag ds_mini_ddrm64_20261013_a不存在才运行，首败停止，不重做RPC/环回/权限实验或旧版/ISA/Hello/CoreMark/PHY/历史。

评估依据：旧I32/D32实板MEM占39.15%/37.76%，已有D IP只用半容量；此前D扩容+DRM组合收益约1%，不承诺本次增益或用等待占比推导可节省量。D理论多896 metadata bit，D DRM预计仍4/全局16，仅估计，实际资源/时序/收益待测。用户允许继续开发后，I64/D32 021已测a0c4e2f6快照/原2449证据/旧PDS-board准备全部保持，不覆盖。其PDS/上板仍未做；默认后续只最终I64/D64，不补中间I64/D32，对照最近完整成功I32/D32 coremark_idrm_d32_01，所以实板组合收益不能单独归因D64。

022结果回交后Codex连续核原始证据并准备用户最终I64/D64 PDS源/所选seed/多角时序/FF-LUT-DRM/两IP完整地址/Loader INIT/新位流核验；板子当前不可用，实板待可用后COM9原120次P/V各1轮，新日志coremark_i64_d64_01，原BIN不重建，详见新阶段预备命令。根位流仍d60f9ce2 I32/D32，新功能/实现/收益均待结果。用户执行PDS/下载/KEY0/串口，不逐步问继续，不同时M/写缓冲/提频等其他改变。旧I64 manifest绑定旧桥，不能对新主RTL重跑旧021入口/审查或直接按旧准备做I64/D32身份结论；下文无待仿真/下一步仅I64 PDS为此前历史。

021 batch `ds_mini_idrm64_batch_20261013_a`已由Codex核验原始证据PASS：三命令0，实际8真实模块/单顶层，Errors/Warnings0，八组645/147/207/139/480/515/294/22共2449、唯一RESULT PASS、TB483行133570ns/Iteration1正常finish；两条04030130原文保持，无RPC或功能错误。console2905byte/transcript2864byte因换行不同，规范换行后全文同，不写原始字节相等。加载日志9条=sv_std.std+8 work模块。233+5+2及原179+2身份保持，桥a0c4e2f6…601b、清单98cee935…7b1ec、八副本及git前后快照哈希保持。执行目录codex_review.json=MINI_INST_DRM64_RAW_EVIDENCE_REVIEW_PASS；Codex未重跑HDL/串口/PDS。

当前无待领取仿真，所有021入口停止、不重复旧版/ISA/Hello/CoreMark/PHY或工具预检。PASS范围是x32 I64/D32真实I/D DRM桥级关键功能+功能DDR用户口模型，x16仅静态；没有CPU/PHY/完整SoC/实板验收。batch只是当前可用模式，不等于IPv6修复，也不能证明原60秒RPC同因。**下一步用户重新载入RISCV.pds完成I64 PDS，完整[本轮阶段顶部](cpu/MINI六十四行I缓存评估修改与交接_2026-10-13.md)已准备核对/上板步骤，不逐步问继续。**

准备目录build/inst_drm64_preparation_20261013_a/pds_handoff.json=MINI_INST_DRM64_READY_FOR_USER_PDS_BOARD_NOT_TESTED绑定功能收据/130实际登记输入、项目身份和RISCV_before_I64_PDS.pds，除桥外与成功I32/D32源同；board_plan.json绑定COM9原120次P/V、BIN/manifest、各129响应/唯一RUN及新目录，离线准备未开串口。成功20份冻结PDS/10软件项/原实板证据复核保持，只引用复用。

用户执行board_top/PG2L200H/-6/FBB676/core93.75MHz原IP/约束最终实现。Codex随后核所选seed与根ADFs/网表/位流同源、多角setup/hold/最差路径、FF-LUT-DRM、I valid/tag64与完整2KiB地址使用/D32映射、Loader8存储128 INIT/config及软件身份、新位流SHA。预计I/D各4DRM、全局16仅估计，理论多896 metadata bit，实际资源/时序待报告；旧基线FF11273/LUT10639/DRM16、core setup慢/快+.681/+4.639ns/hold+.142/+.102ns。根位流仍d60f9ce2 I32/D32，不能称I64。

新PDS核过并由用户下载后，COM9原performance_120/validation_120各1轮，运行脚本/KEY0-DDR ready步骤见阶段顶部，新日志coremark_i64_d32_01（当前不存在），原BIN不重建/不补短测、不覆盖历史。对照成功coremark_idrm_d32_01 P/V398389378/412352500cycles、4.249486699/4.398426667秒；固定CRC d340/200d/退休/branch/AW口径保持。回交后连续核协议/CRC/13计数/软件与本地位流身份及性能变化，不足10秒仅比较。I64新时序/资源/位流/实际DDR收益仍未验证；用户执行PDS/下载/KEY0/串口，不自动M/D64/写缓冲/提频等优化。下文batch待执行/功能INCOMPLETE为此前历史。

最新CLI `ds_mini_idrm64_cli_20261013_a`原始证据核对：真实8模块/单顶层编译Errors/Warnings0，vsim180.360140秒超时，520字节输出明确RPC_Init ::1:65511 socket invalid argument，transcript0、无run/check/finish，0/2449可观察检查/INCOMPLETE，无功能FAIL，缺git_after/8副本不声明快照相等。210项+5工具及原179+2保持。**CLI也失败，推翻此前Tcl加载路径特有解释。** 原第一次60秒日志无RPC，三次同根因仍仅假设，不能写全部已证明或所有其他测试必失败。

Codex已处理工具条件并保存新原始证据：loopback_default.json和经批准沙箱外loopback_outside.json均IPv4 PASS、IPv6 connect WinError10013，单提升执行权限无效，具体宿主/会话机制未确定，未改权限/hosts/防火墙/注册表/IPv6。按本机10.6c手册第718页采用标准-batch，纯工具启动预检0.873799秒、退出0/ErrorsWarnings0、无RPC，未加载设计或执行run，batch_startup_preflight/result=MODELSIM_BATCH_TOOL_STARTUP_PASS_NO_HDL。启动PASS不能作I64功能PASS或Windows网络修复完成。task021_cli_rpc_review.json记录CLI失败/环回/预检SHA，状态MINI_INST_DRM64_CLI_RPC_BLOCK_REVIEW_BATCH_STARTUP_ONLY_PASS；Codex未执行I64 HDL测试。

当前只领取[任务021批处理续测](../DeepSeek/任务021批处理续测_I64真实DRM单次验收.md)。新resume_inst_drm64_batch.py单次标准-batch单顶层，-logfile/原run-all-quit，原8模块/2449/1ms watchdog/60-60-180秒不变。清单98cee935…7b1ec保护233项+5工具+2本机参考配置，原179+2保持，batch_resume_preparation.json=MINI_INST_DRM64_BATCH_PREPARATION_PASS_HDL_NOT_RUN，静态检查通过。固定新tag ds_mini_idrm64_batch_20261013_a，默认执行权限，用户PDS结束且tag不存在才由DeepSeek单次运行；再失败保留停止、不改环境/权限/RTL/TB/判据、不追加历史/工具实验。旧021/诊断/CLI入口均停止，三失败目录/报告保持。I64功能/PDS/实板仍待结果，完整功能PASS后才连续衔接原固定120次BIN/成功coremark_idrm_d32_01/新日志coremark_i64_d32_01及用户PDS/上板步骤，下文旧待执行入口为历史。

021诊断`ds_mini_idrm64_diag_20261013_021854`原始证据已核对：9真实模块编译Errors/Warnings0，vsim180.340530秒终止，阶段仅TCL_ENTERED/BEFORE_LOAD；768字节原生输出明确RPC_Init IPv6环回::1:49689 socket invalid argument，transcript200字节，无HDL探针/run/check/finish，观察检查0/2449，功能INCOMPLETE。这是本次Tcl设计加载路径的环境/工具阻塞，不是RTL FAIL，也未解释原021命令行60秒超时。报告IPv6禁止/IPv4正常测试只有摘要，无独立套接字原日志，不把具体宿主策略作为已证根因；taskkill exit0但输出编码不完整，当前进程数0，失败无git_after/9副本。准备目录task021_rpc_review.json记录本次证据SHA，MINI_INST_DRM64_RPC_LOAD_BLOCK_REVIEW_INCOMPLETE。

当前只领取[任务021命令行续测](../DeepSeek/任务021命令行续测_I64真实DRM单次验收.md)。恢复019/020及原021的单顶层CLI加载，原-do "run -all; quit -f"，去掉诊断Tcl vsim/第二观察顶层，保留原生直写/显式transcript和vsim180秒、vlib/vlog60秒；不保证路径一定可用，单次验证建立结果。新resume_inst_drm64_cli.py/清单b0640ab8…682c8保护210项+5工具文件，原179+2保持。静态入口/AST/参数审查通过，cli_resume_preparation.json=MINI_INST_DRM64_CLI_PREPARATION_PASS_HDL_NOT_RUN。固定新tag ds_mini_idrm64_cli_20261013_a，目录已存在即停止；只执行一次，不改环境/权限/IPv6/源码/2449判据，不自动重试/历史/PDS/串口。Codex未执行新HDL，I64功能/PDS/实板仍待结果。下文原021/诊断待执行入口已被本CLI入口取代；成功基线、原120次BIN与coremark_i64_d32_01上板计划保持。

021原执行`ds_mini_idrm64_20261013_013143`原始证据已核对：输入179+2保持，真实I/D DRM源8模块编译退出0、Errors/Warnings0；vsim被60秒runner上限终止（-1标志/60.164754秒），94字节simulation.log/0字节transcript，无加载/run/CHECK/RESULT/finish证据。功能INCOMPLETE，不记PASS/RTL功能FAIL，也不能断定收尾问题。原失败路径无git_after/八副本，不能声明快照相等；当前Get-Process无残留，未改权限。准备目录task021_timeout_review.json记录原证据SHA，状态MINI_INST_DRM64_TIMEOUT_AUDIT_INCOMPLETE_NOT_FUNCTIONAL_FAIL。

当前只领取[任务021续测：启动、运行、退出定位](../DeepSeek/任务021续测_I64启动运行退出定位.md)，不执行旧021入口。新resume_inst_drm64.py一次vlib/vlog各60秒、vsim180秒，原生输出直接入文件、独立flush阶段链、每10μs只读HDL进度探针、onfinish stop/显式quit；原RTL/TB/DDR模型/2449判据/1ms watchdog未改。新清单d1b0b468…df6d保护194项（原179及失败证据/诊断入口等）+5模拟器文件，原2厂家模型继续保护。只读--check-inputs退出0，resume_preparation.json=MINI_INST_DRM64_DIAGNOSTIC_PREPARATION_PASS_HDL_NOT_RUN；Codex未重跑HDL。续测首次失败继续保留停止；完整2449/八组/两提示/finish/退出0和身份守恒后才记PASS。I64 PDS/实板待功能结果，仍用户执行，沿用下文原BIN/成功对照/新日志计划；下文021待首次执行/HDL NOT_RUN为准备历史。

用户要求“改成i64”，核对IP截图后本轮只扩I32→64，D32/32byte行/93.75MHz保持。当前主桥SHA **a0c4e2f6eef67f31333e5e350c5cf84b50025a4141e0fb03a6ce51540c96601b**，I valid/tag64、取指/写失效/fill索引6bit，I RAM写6bit index、读addr[10:2]使用现有IP全部2KiB；D实际read/fill索引仍5bit、D32/DDR FSM/响应/CPU全文保持。用户截图写256/address6、读32/address9已满足I64，生成源身份保持，未重生成IP或改RISCV.pds。

静态精确最小变换/源身份/模型判据/八组2449检查审查通过，清单179工程+2厂家原语。当前只领取[任务021](../DeepSeek/任务021_MINI_I64_D32关键仿真.md)，[本轮I64记录](cpu/MINI六十四行I缓存评估修改与交接_2026-10-13.md)，run_inst_drm64.py一次真实IP/DRM TB、ISA0，无020/旧版/历史重跑。HDL/PDS/新实板NOT_RUN；两条原厂家04030130提示保留，其他错误停止。I低/高32行、2KiB冲突、I63部分/零strobe/异tag失效、锁定地址、bad RID/last、同步hit保持/reset均准备。D两组与DDR模型/transfer逐字复用，未放宽判据。

成功对照仍已完成的双DRM I32/D32：020冻结桥918efab7、位流d60f9ce2、coremark_idrm_d32_01 P/V398389378/412352500cycles、4.249486699/4.398426667秒。旧20份PDS/板级证据复用。021回来连续核原始证据、用户新PDS来源/时序/FF-LUT-DRM/I64完整地址/Loader INIT/新位流，再COM9原120次P/V各1轮，日志coremark_i64_d32_01，不重建BIN或覆盖旧目录，不逐步问继续。预计I DRM仍4、全局16，资源/收益待测；当前旧位流不代表I64。用户执行PDS/下载/KEY0/串口，暂不M/D64/提频等其他改动。下文“仅评估/无新RTL/本阶段完成”为此前成功I32阶段。

用户询问下一步性能提升，仅评估未执行：按原120次BIN口径，建议优先单独I32→64、D32/93.75MHz保持。现有icache逻辑配置64×32byte=2KiB，只用低32行，扩64可沿用同IP，预计4个I DRM不变，但tag/valid/比较及时序须验证；IF+branch仍占约36%、历史I扩容收益高于此次D扩容，不能据此承诺I64增益。M/Zmmul适合允许新增ISA软件的后续路线，旧BIN不会自动受益；写缓冲缺读写等待分项/一致性验证复杂、提频暂不优先。完整评估见双DRM阶段顶部；当前无新RTL/任务/测试，成功基线保持，下一实施项等用户指示。

最新实板`coremark_idrm_d32_01`原120次P/V各1轮已完整核验PASS（01:02:30/01:02:52日志）：ACTUAL_SERIAL/COM9、每模式129响应/唯一RUN、DDR VERIFY/CRC d340/200d/13计数守恒、原BIN/ELF/manifest及d60f9ce2本地位流身份保持。cycles398389378/412352500、秒4.249486699/4.398426667、CPI4.001056/3.893712、精确迭代/秒28.238705/27.282483；相对FF I32/D16 coremark_i32_01耗时降1.0645%/0.8917%、吞吐升1.0759%/0.8997%。MEM少2.6736%/2.3247%，解释99.9495%/99.8818%净周期节省，IF/branch基本不变，退休/分支次数/AW/other相同，混合AR少4.4898%/4.2310%。MEM新占39.1479%/37.7590%，无读写等待/单独I-D miss分项，不拆分D扩容与DRM迁移收益。

建议保留I32/D32双DRM/93.75MHz：速度约1%小幅改善，FF少51.50%/LUT少22.60%和setup余量增0.333ns为更明显收益。两模式不足10秒仅同BIN比较，每模式单次无方差估计；没有FPGA独立读回，不能用本地SHA替代已编程内容证明。准备目录`board_review.json=MINI_DATA_DRM32_ACTUAL_DDR_FIXED120_REVIEW_PASS`，只冻结两新日志、复用旧基线/PDS/020。130登记输入/20新PDS证据/Loader/原软件保持。完整[阶段实板分析](cpu/MINI_I32_D32双DRM接入与交接_2026-10-12.md)已更新，本阶段完成，无待领取仿真/重复PDS或测量，不自动M/提频/扩缓存，后续开发等待用户指示。下文“待板子/待跑分/性能待测”为此前历史。

最新用户位流/PDS核验PASS：board_top、PG2L200H/-6/FBB676、seed5、93.75MHz、Pre-silicon多角十组失败0。core setup慢/快+0.681/+4.639ns、hold+0.142/+0.102ns；物理FF11273（较FF I32/D16少11972，51.5035%）、LUT10639（少3106，22.5973%）、DRM16（+8，I/D各4），桥FF1511/层次LUT948、宽数据FF阵列消失、valid各32及完整tag保持。最差CPU有效地址→I9 tag18.CE，11级、route73.676%。CSV fast setup4.455是跨core→PHY路径组，不混作core-core4.639；不自动提频。

新位流`generate_bitstream/board_top.sbit`北京时间2026-10-13 00:04:57、9188552byte，SHA **d60f9ce20469fe3e7c0ebb0ffe3d1d3c2c7228c1424cb8a64572e2faf04b46cc**。主桥仍918efab7 I32/D32，各1KiB；130登记文件与020一致，181+2输入/功能证据保持。PDS只重排I/D登记位置与生成元数据，真实选项保持；Loader8个DRM全INIT/config及原DAT/固定120BIN保持，另有8缓存DRM。六阶段日志无错误，厂家两条04030130及既有IO/SCBV提示保留。准备目录`pds_review.json=MINI_DATA_DRM32_PDS_EVIDENCE_REVIEW_PASS`，冻结20份新产物，旧020/成功基线复用。详见[双DRM阶段顶部最终PDS](cpu/MINI_I32_D32双DRM接入与交接_2026-10-12.md)。

当前无待领取仿真/重复PDS，实板仍待板子可用。用户下载核过的d60f9ce2位流，COM9原120次P/V各1轮，新日志coremark_idrm_d32_01，KEY0/DDR ready步骤及命令已在阶段记录准备；原BIN不重建，对照FF I32/D16 coremark_i32_01。用户只剩下载/串口/交日志，Codex回交后连续核验/性能分析；不足10秒仅比较，不补I-only/历史，不自动M/提频。未独立读回FPGA配置，PDS不能等同实板PASS。下文“待用户PDS/根位流仍99cdb3d0/尚未生成”等为此前历史。

用户随后询问M扩展，仅静态评估、未实施/建任务：当前CPU/misa仍RV32I，固定120次BIN含软件乘除，矩阵乘法有潜在收益。建议作为下一独立CPU升级，先保存/核当前双DRM PDS基线，再分乘法/除法完成8条完整RV32M；仅乘法叫Zmmul。旧rv32i BIN加硬件M不会自动使用M，未来需独立rv32im软件目录、保留原BIN，比较口径不能再声称同BIN/退休相同。详见双DRM记录顶部M评估；当前仍待双DRM用户PDS/板子，没有新M RTL或仿真任务。

最新020`ds_mini_ddrm32_20261012_185339`原始证据核验PASS：实际I/D IP+真实DRM原语、三命令0、Errors/Warnings0、八组1521检查、TB483行/85570ns正常结束，181+2输入/八副本/git保持，current桥918efab7版。两条已知非致命04030130保留，无其他错误。执行目录`codex_review.json=MINI_DATA_DRM32_RAW_EVIDENCE_REVIEW_PASS`，没有HDL重跑或源码修改。当前无待领取仿真，不重跑019/020/历史；完整[双DRM记录](cpu/MINI_I32_D32双DRM接入与交接_2026-10-12.md)已更新。

准备目录`build/data_drm32_preparation_20261012_a/pds_handoff.json`绑定130项实际登记源/IP/约束、项目配置及成功Loader/原BIN/旧PDS/位流身份，状态READY_FOR_USER_PDS_BOARD_DEFERRED。下一步用户重新载入RISCV.pds并完成最终双DRM实现，Codex核最终seed/多角时序/FF-LUT-DRM/两IP层次与32valid/27bit完整tag/Loader综合INIT/新位流身份。预期新增8 DRM、总16仅估计；现有成功时序与99cdb3d0位流仍FF版I32/D16，新时序/资源/位流待生成核验，未启动PDS。

板子借给别人做摄像头，实板暂不可用，待板子可用后只最终新配置原120次P/V各1轮，COM9、新目录coremark_idrm_d32_01，命令已在本轮记录准备；对照成功FF版coremark_i32_01 P/V402675844/416062610cycles、4.295209003/4.438001173秒，原BIN不重建。不要求补I-only中间PDS/上板，不新开优化/重复测试；不足10秒仅同BIN比较，收益同时含D扩容与DRM迁移不能拆分归因。用户执行PDS/下载/KEY0/串口。下文020待执行/HDL NOT_RUN为准备阶段历史。

019报告`ds_mini_idrm_20261012_181906`原始证据已核验PASS：真实ICache/厂家DRM、三命令0、Errors/Warnings0、六组1093、TB397行/62700ns正常finish，172+2输入/六副本/git保持。执行目录`codex_review.json=MINI_INST_DRM_RAW_EVIDENCE_REVIEW_PASS`，厂家唯一04030130提示保留。未运行I-only PDS/实板，不重复019。用户板子借给别人做摄像头，允许先接DCache并明确“dcache改为和icache的容量一样”；按新要求当前源码已为**I32/D32双DRM，各1KiB**。

新桥SHA918efab7…525851；D valid/tag各32行，索引5bit，生成dcache同步读/完整256bit填充，hit仍下一周期；I路径与DDR FSM/仲裁保持019已测版，CPU/PHY/时钟/Loader/原软件未改。RISCV.pds仅追加D IDF/两源登记，两IP均实际使用低32行。静态精确逆变换/来源/项目/1521计数审查通过，HDL/PDS/新实板NOT_RUN。当前只领取[任务020](../DeepSeek/任务020_MINI_I32_D32双DRM关键仿真.md)，完整[双DRM阶段记录](cpu/MINI_I32_D32双DRM接入与交接_2026-10-12.md)。清单181工程+2厂家模型，八组1521、ISA0、三HDL命令一次，真实I/D IP；不重跑旧版/019/历史。两IP各一条04030130非致命提示保留，其他错误停止。

收到020后连续复核原始证据并准备用户最终双DRM PDS时序/FF/LUT/DRM/源与INIT/位流核对。板子不可用，新实板待执行；不要求补I-only中间PDS/上板。成功板级对照仍FF版I32/D16 `coremark_i32_01`/99cdb3d0（402675844/416062610cycles、4.295209003/4.438001173秒），原120次BIN不重建。板子可用后只最终新配置P/V各1轮，新目录coremark_idrm_d32_01，不覆盖历史，不足10秒仅比较。收益同时包含D扩容与DRM迁移，不能拆分归因。用户执行PDS/下载/KEY0/串口，Codex不启动这些操作或其他优化。下文019待执行/I32D16候选/未接DIP等均是此前历史。

用户已生成`ipcore/icache`/`dcache`，要求“先修改之前的icache”。本轮只在主桥x32分支接入ICache数据DRM，I32/D16容量、tag/valid、D16数据/维护、数据优先及DDR命令FSM保持，未接DIP/扩D32。新桥SHAb1ec2497…f04572d；`RISCV.pds`只追加ICache IDF和两份生成源码。同步读在接受边沿采样地址，STATE_RSP直接选IP输出，保持下一周期hit；miss原DDR旁路、reset清valid并取消响应。x16兼容数组分支静态保留。本轮无CPU/DDR/Loader/软件改动。

当前只领取[任务019](../DeepSeek/任务019_MINI_I32接入DRM_IP关键仿真.md)，记录[MINI_I32接入DRM_IP与交接](cpu/MINI_I32接入DRM_IP与交接_2026-10-12.md)。静态逆变换/来源/项目登记/检查数审查通过，清单172工程输入+2厂家原语，六组1093（原834逐字保留+同步读259），HDL/PDS/新实板NOT_RUN；DeepSeek用真实生成IP/GTP_DRM36K_E1执行一次，ISA0，不重跑018/历史。厂家旧AW<9检查对GUI AW6打印非致命04030130，保留并单独核对，其他诊断/功能错误停止。入口`python -B -X utf8 sim/mini_board_migration/run_inst_drm.py --check-inputs`已退出0。

成功对照仍FF版I32/D16 `coremark_i32_01`和99cdb3d0位流，402675844/416062610cycles、4.295209003/4.438001173秒。019原始证据返回后连续准备用户PDS最终时序/FF/LUT/DRM/来源/INIT/新位流核验及COM9原120次P/V各1轮，日志`coremark_idrm_01`，BIN不重建、不覆盖历史。用户执行PDS/下载/KEY0/串口；PDS打开时重新载入新增登记的RISCV.pds。新功能/时序/资源/实板待外部结果，不自动开始DIP或其他优化。下文“无待领取/等待指示/已完成”描述此前FF版I32阶段。

最新实板：用户`coremark_i32_01`实际DDR原120次P/V各1轮已完整核验PASS，COM9/129响应/唯一RUN、DDR VERIFY、CRC d340/200d、13计数守恒及固定软件/99cdb3d0本地位流身份保持。cycles402675844/416062610、时间4.295209003/4.438001173秒、CPI4.044105/3.928745；对照成功I16/D16 coremark_d16_01，耗时降8.6500%/8.2482%、吞吐升9.4691%/8.9897%。IF少9.0751%/8.8130%、branch恢复少37.0212%/35.1683%，二者解释95.3216%/97.6884%周期节省；MEM绝对周期略降约1.1%/0.54%、AR少29.23%/29.27%，退休/分支次数/AW/other相同。恢复类别含目标取指等待，不是BTB或分支次数减少。

建议保留I32/D16及93.75MHz，本轮018续测、最终PDS、实际DDR比较均完成；两轮不足10秒仅同BIN性能比较。新MEM占39.7951%/38.3129%，占比上升来自分母减少，不是D恶化；无I/D动态miss/读写等待分项。收据`build/inst_cache32_preparation_20261012_a/board_review.json`为`MINI_INST_CACHE32_ACTUAL_DDR_FIXED120_REVIEW_PASS`，只冻结两新日志、复用旧基线/PDS/018证据。124项登记输入及18份PDS产物、软件保持；每模式单次无方差估计，未独立读回FPGA配置。当前无待领取仿真或重复测量，不自动开始其他RTL优化，下一开发项等待用户指示。

最新：018续测`ds_mini_i32_resume_20261012_170046`原始证据核验PASS，三命令退出0、Errors/Warnings0、五组834、54790ns正常结束，182项/六副本/执行git快照保持、D/FSM及最小变换通过，ISA=0。收据该目录`codex_review.json`为`MINI_INST_CACHE32_EVIDENCE_REVIEW_PASS`。原报告HEAD写cb，以原始快照bc为准；原停止报告追加后已字节精确恢复，现SHA与原审查/清单一致，事件和缺少临时版本的范围在本轮记录保留。没有待领取仿真，不重跑018或历史。

用户当前I32最终PDS已核验PASS：board_top、PG2L200H/-6/FBB676、Pre-silicon多角、seed2、十组汇总失败0。CPU93.75MHz，setup慢/快+0.348/+4.456ns、hold+0.105/+0.100ns；物理FF23245/LUT13745（较I16/D16 +4455/+1237）、DRM8，桥13461FF/4379层次LUT。slow setup余量少0.225ns，最差CPU有效地址bit6→D6.CE，9级、布线77.184%。124项登记输入、I32/D16容量、成功Loader8个综合存储INIT/配置、原120次软件保持；根PnR与seed2 ADF/网表一致。已复用本次用户产物，无需重复PDS。

新根位流`generate_bitstream/board_top.sbit`16:47:21生成、9188552byte，SHA **`99cdb3d0d0ccfa7245695f9ebc9de35c1d826f5a7fd0c023868555c3833dbaf9`**，与两新实板日志记录一致。PDS收据`build/inst_cache32_preparation_20261012_a/pds_review.json`为`MINI_INST_CACHE32_PDS_EVIDENCE_REVIEW_PASS`，冻结18份本轮实现证据，旧成功对照复用。`coremark_i32_01`已完成核验，不能覆盖或复用作新运行目录；原120次BIN保持，完整比较见[同一I32阶段记录](cpu/MINI三十二行I缓存评估修改与交接_2026-10-12.md)。Codex本轮只离线分析/记录，未运行HDL/PDS/串口或修改RTL/软件；下方前置停止/待续测/NOT_RUN/待上板/收益待测均为历史。

### I32准备及018停止/续测过程历史

用户在D16成功后要求“执行下一轮”，已按建议单独I16→32。先读根`AGENTS.md`、[本轮I32记录](cpu/MINI三十二行I缓存评估修改与交接_2026-10-12.md)、[任务018](../DeepSeek/任务018_MINI三十二行I缓存关键仿真.md)。下方D16成功/仅建议I32/无新任务均是上一轮历史，不能覆盖本段。当前MINI200H/x32 DDR、256bit用户拍/32byte行、CPU93.75MHz，工程仍D:/riscv/RISCV、RISCV.pds顶层board_top。

最新：[任务018停止报告](../DeepSeek/任务018_结果_STOPPED_未执行_20261012_161015.md)已核实，原check-inputs因RISCV.pds变化退出1，**HDL未执行，不是RTL仿真FAIL**。179项164匹配/15差异均为用户提前PDS生成的项目/实现输出；Codex只读复现同一失败，原任务/runner/清单/报告/RTL/判据保留。18项原实现证据SHA全部由既有D16冻结副本验证，实际设计配置保持，变化仅生成状态/时间/输出登记。

当前只领取[任务018续测](../DeepSeek/任务018续测_I32冻结基线输入与单次关键仿真.md)：`resume_inst_cache32.py`、新182项`inst_cache32_resume_inputs.json` SHA **`aba5c36fd4795c982767792d171c95f996e18870ac1eb6effa7c2fd55977a58f`**。18项实时实现证据改绑定原SHA一致的已有冻结副本，实时设计配置仍核对；不是刷新旧清单或采用新产物作成功基线。只读检查`INPUTS_MATCH_NOT_SIMULATED 182 checks=834 ISA=0`已通过。停止审查收据`build/inst_cache32_preparation_20261012_a/task018_stop_review.json`，不记功能PASS。

核验时用户PDS仍在运行；等其结束后DeepSeek用续测入口单次跑当前I32关键TB，执行前pds_shell非零会停止。原018未跑，续测仍是首次HDL，不重跑旧版/ISA/历史。不停止用户PDS、不改权限/设计/原判据。当前实现产物保留；功能审查后源/IP/约束/初始化未变即可核现有最终产物，无需因先后顺序重复PDS；通过才下载并COM9原120次双模式各1轮。完整核对和命令已在同一I32文档准备，原179项入口拒绝当前产物保持为历史/预期。

现有`myriscv/dual_sram_to_pango_ddr_bridge.v`当前I32/D16，SHA **`78c624e8eb8a7ea1ad0fd8186873c5ba17f4e98d7623bce83006e5336bdccb34`**：I容量512→1024byte、读/写失效索引[8:5]→[9:5]，fill锁存tag[4:0]、reset32；D16声明/索引/维护、总线输出/FSM逐字保持。头部旧D8注释更正，不改D行为。未改CPU/IP/PDS/Loader/原120次BIN。理论新增4544bit状态，新32路选择/写失效扇出及布局风险待PDS，旧+0.573ns不作新PASS。

新`sim/mini_board_migration/{tb_inst_cache32_x32.sv,run_inst_cache32.py,inst_cache32_inputs.json}`准备完成，179项清单SHA **`59ddf2d42893f2682142617ac189b63d8761ec3f42184b328b0d26efbb3d2a33`**；AST/手算/静态展开及D/FSM/最小变换/模型监测守卫、只读输入检查PASS。五组325/83/111/75/240合计834，当前x32 TB一次、三条HDL命令、ISA=0；模型握手/时序/判据复用，后备存储64→128行覆盖新高地址。准备收据/最小patch在`build/inst_cache32_preparation_20261012_a/`。**HDL NOT_RUN，新I32时序/资源/实板收益未测。** 只交任务018，仿真结束前不并行PDS；不重跑旧版/ISA/Hello/CoreMark/PHY或历史全套，不刷新旧清单。

唯一相邻成功基线I16/D16：源码复用任务017运行目录的32218ed3版；成功位流 **`f2540aec916476bf15eb02c0fefb174b0af06c9a801cde92d704083ceaca6ccd`**、9188552byte在既有D16 pds_evidence保留，不含新I32。原根位流/最终报告已由用户PDS生成流程移除，不能继续声称当前根文件存在或是成功版。完整PDS/实板证据复用`build/data_cache16_preparation_20261012_a/`，不重复归档。对照`board/coremark_d16_01` P/V4.701925600/4.836962304秒、cycles440805525/453465216、CPI4.427044/4.281926、AR4730667/4698703；原BIN/ELF/manifest保持。新日志目录`board/coremark_i32_01`尚不存在，不覆盖成功目录。

DeepSeek执行018续测交回后Codex连续核原始证据、更新同一I32记录和剩余PDS/上板准备，不逐步询问；用户执行PDS/位流下载/KEY0/串口，Codex核最终93.75MHz多角时序/资源/源/初始化/位流。通过并下载后COM9原120次P/V各1轮，命令已在本轮I32记录准备，当前不打开串口。不足10秒仅同BIN比较。当前等PDS结束后交DeepSeek续测；任务文件不会自动调用DeepSeek，未自行运行HDL/PDS或提交推送。

## I16/D16完整验收与后续评估历史（2026-10-12）

用户已完成新D16实际DDR运行，Codex完成两模式日志核验和性能分析。本轮任务017、最终PDS、实际DDR同BIN比较全部通过，建议保留I16/D16及93.75MHz，无待领取仿真或需要重复的测量。下方准备阶段NOT_RUN/待017/待PDS/待上板/收益待测及按阶段保留的“当前”“下一步”均为此前历史，不用旧状态覆盖本段。

最新实板：`coremark_d16_01`原120次P/V每模式129响应/唯一RUN、DDR VERIFY、CRC d340/200d、13计数守恒及同BIN/ELF/manifest、f2540aec本地位流身份通过。cycles440805525/453465216、时间4.701925600/4.836962304秒、CPI4.427044/4.281926；相对成功I16/D8 `coremark_i16_01`耗时降6.2890%/6.0657%、吞吐升6.7111%/6.4574%。MEM少15.4498%/15.5022%、AR少18.8880%/18.6348%，退休/分支次数/AW/other相同，收益集中MEM；IF/branch恢复绝对变化很小。新MEM占36.7575%/35.3435%，AR混合I/D不能推D hit率。两轮不足10秒仅性能比较；整数输出4秒/30次每秒不是精确成绩。

实板收据`sim/mini_board_migration/build/data_cache16_preparation_20261012_a/board_review.json`为`MINI_DATA_CACHE16_ACTUAL_DDR_FIXED120_REVIEW_PASS`，只保存两份新日志并复用成功对照/PDS/017证据。124项登记输入、18份实现产物及软件身份保持。本轮只离线审查/记录，未改RTL/软件或运行HDL/PDS/串口；每模式单次无方差估计，未独立读回FPGA配置。详细比较见[同一D16阶段记录](cpu/MINI十六行D缓冲评估修改与交接_2026-10-12.md)，下一开发项等待用户指示，不自动开始其他优化。

用户随后询问下一步方案，已只做静态评估：推荐下一单项实验I16→32、D16保持，IF+branch占约40.7%/41.3%；固定`core_bench_list`跨度18行超过I16，矩阵/软件乘法辅助的部分静态索引重叠可由I32分开，但无动态miss证据，不预报收益。理论新增4544bit状态，32路选择及I写失效扇出/全局布局风险须新PDS核验；D32、写命中更新、写缓冲/突发及M/预测为后续候选。结果`build/data_cache16_preparation_20261012_a/next_options_evaluation.json`及方案比较记录在同一D16文档；**尚未修改RTL/软件、创建任务或运行仿真/PDS/串口**。下一候选若获实施指示，复用coremark_d16_01及32218ed3/f2540aec成功基线，不覆盖原120次BIN和成功目录。

最新：`ds_mini_d16_20261012_143018`三条HDL命令退出0、Errors/Warnings0、五组498项、34630ns正常结束；四副本及初始173项输入一致、执行git快照字节相同，I/FSM保持、ISA=0。审查收据为该目录`codex_review.json`的`MINI_DATA_CACHE16_EVIDENCE_REVIEW_PASS`。报告HEAD抄写错误以原始`7af48d2185bc01a62be528c70b83c42689394c31`为准；原证据不改。无待领取仿真，不重跑017或历史测试。

最新D16 PDS：PG2L200H/-6/FBB676、board_top、Pre-silicon多角、所选seed4，十组时序汇总失败0；CPU93.75MHz，setup慢/快+0.573/+4.500ns、hold+0.155/+0.100ns。物理FF18790/LUT12508（较I16/D8 +2224/+775），DRM8；桥9029FF/3044层次LUT。最差CPU有效地址→D15.CE，地址bit8扇出1259、10级、布线74.280%，慢角setup余量少0.119ns。124项登记输入与017匹配；综合I16/D16各512byte，成功Loader8个综合存储实例INIT/配置及固定软件保持。根PnR与seed4 ADF/网表一致；既有未约束IO/SCBV提示保留。

根`generate_bitstream/board_top.sbit`为新D16：15:19:07生成、9188552byte，SHA **`f2540aec916476bf15eb02c0fefb174b0af06c9a801cde92d704083ceaca6ccd`**，本轮两实板日志记录同一身份。收据`build/data_cache16_preparation_20261012_a/pds_review.json`为`MINI_DATA_CACHE16_PDS_EVIDENCE_REVIEW_PASS`，保存18份本轮新实现证据，旧143fa795位流及I16/D8对照复用。实际DDR日志`coremark_d16_01`已核验，原120次P/V BIN保持，成功对照为`coremark_i16_01`；不补仿真/PDS或历史测试。

先读根`AGENTS.md`、本段、[本轮D16评估修改及剩余操作](cpu/MINI十六行D缓冲评估修改与交接_2026-10-12.md)、[任务017](../DeepSeek/任务017_MINI十六行D缓冲关键仿真.md)。需要核对成功基线时读[上一轮I16完整验收](cpu/MINI十六行I缓存评估修改与交接_2026-10-12.md)。工程为D:/riscv/RISCV，PDS顶层board_top，当前实际MINI200H/x32 DDR、用户拍256bit/行32byte、CPU93.75MHz；早期文档/默认参数中的x16/128bit不是当前板级配置。

### 当前候选与完成范围

- 现有`myriscv/dual_sram_to_pango_ddr_bridge.v`已单独D8→16，当前源码I16/D16，SHA `32218ed30625d34a85db3d4f5bafd7142de56276c67651ef20eed017a5bbe084`。D512byte，I512byte；只改D声明/索引/reset，I维护及总线FSM保持。未修改CPU/DDR IP/PDS/Loader/原BIN。
- `sim/mini_board_migration/{tb_data_cache16_x32.sv,run_data_cache16.py,data_cache16_inputs.json}`已准备，173项清单SHA `f85e5e40b795a52eee3007b79839897f792279150b594b658bc7e9fefc0528ec`；五组165/51/79/43/160合计498已由017验证并核验PASS。准备/PDS/实板收据及最小patch为`build/data_cache16_preparation_20261012_a/`，原NOT_RUN收据保留为准备历史；D16时序/资源/实际收益已核验。
- 已发现并核验[任务017结果](../DeepSeek/任务017_结果_ds_mini_d16_20261012_143018.md)、对应原始产物和`board/coremark_d16_01`两实板日志。无需重复准备、运行ModelSim或重复测量。
- 017当前x32 TB一次、三条vlib/vlog/vsim命令、ISA=0，功能模型与事务监测复用016；当前无待领取仿真，PASS不追加旧版/ISA/Hello/CoreMark/PHY或历史测试，不刷新保护清单绕过后续PDS变化。

### 唯一相邻成功基线

成功I16/D8源码复用`sim/mini_board_migration/build/ds_mini_i16_20261012_133046/dual_sram_to_pango_ddr_bridge.v`，SHA `0b1b2faca33d31500320df73116a5f37b23be0de7b09b37a8b58a794ce3abc69`。任务016仿真、新PDS和实际DDR原120次P/V均独立核验PASS。

根`generate_bitstream/board_top.sbit`交接时SHA仍为 **`143fa795396f4e25bf648da3d9960aeeee3d781691ff6e0a20b844a901a4b62a`**，9188552byte，属于成功I16/D8，不含当前候选D16。成功位流和必要PDS证据已冻结在`build/inst_cache16_preparation_20261012_a/pds_evidence/`，对应`pds_review.json`；实际DDR收据`board_review.json`及两冻结日志也在该准备目录，不重复归档。

PDS seed4、Pre-silicon多角、core setup慢/快+0.692/+4.754ns、hold+0.148/+0.100ns；物理FF16566/LUT11733、DRM8。最差CPU有效地址→D数据行CE，11级、布线77.927%，D16扩容重点审查选择/写使能扇出和布局，不能套用旧余量作新PASS。

相邻实板对照为`sim/mini_board_migration/board/coremark_i16_01/`，不是coremark_d8_01或coremark_01。固定P/V cycles470388387/482747078、时间5.017476128/5.149302165秒、CPI4.724147/4.558425；instret99571067/105902157、branch_redirects21124467/22634887、AR5832265/5774833、AW3646970/3638930，CRC d340/200d。两轮均不足10秒，只作同BIN性能比较；软件身份、完整计数与输出版式在基线日志/收据中，不另重编译。当前MEM约39%～41%，没有D miss/写等待细分，不能预报D16收益。

### 连续推进约定及此前操作命令

用户明确要求：交来DeepSeek结果后Codex同一步核原始日志、command/快照/源码/清单身份并更新同一阶段文档，直接准备剩余PDS、上板与跑分操作，不逐步问是否继续。收到用户PDS产物后衔接核对最终时序/资源/源与初始化/位流，收到实板日志后衔接分析并更新结论。PDS编译/综合/映射/PnR/时序/位流、下载位流与KEY0/串口运行均仍由用户执行；Codex不自动启动它们，不增加Generate Netlist或新部署门控。

本轮017/PDS/实际DDR已核验。以下是已完成的用户COM9原120次双模式命令，保留供复现，不要求重跑：

```powershell
& 'D:/riscv/RISCV/tools/uart_loader/candidates/perf_2b/run_measurements.ps1' -Port COM9 -Applications @('performance_120','validation_120') -LogDirectory 'D:/riscv/RISCV/sim/mini_board_migration/board/coremark_d16_01'
```

该命令已经完成，`coremark_d16_01`已有成功日志，不能覆盖或再次用于新运行。原BIN位于`tests/cpu_performance_2b/build/measure_20261011_120/{performance_120,validation_120}/`；固定软件，不拿纯BRAM替代实际DDR验收，不足10秒不记正式成绩。下方停交017/待上板描述为历史。

工作树有大量此前RTL/IP/PDS/软件/文档的未提交改动；先git status/diff，保护不相关文件，不clean/reset、不删IP/镜像，不自行提交推送。设计只改现有myriscv .v，仿真文件/日志留sim；下一阶段沿用同一D16记录，不为重复审查新建文档或重复保存全套成功证据。

## 当前实施：MINI D8→16已改，停交任务017（2026-10-12）

用户执行下一项，Codex单独改现有桥D8→16，x32 D容量256→512byte、读/失效索引[7:5]→[8:5]，I16/32byte行/完整tag/总线FSM逐字保持。新桥SHA32218ed3…bbe084；理论增2272bit状态，旧最差CPU有效地址→D.CE、setup+0.692ns使本轮需要重点核对D选择/写使能扇出及布局，新时序/资源/收益未测。MEM约39%～41%但没有D miss/写等待细分，不认定扩D必有效或最佳。

只领取[任务017](../DeepSeek/任务017_MINI十六行D缓冲关键仿真.md)：当前I16/D16 x32 TB一次、五组498检查（165/51/79/43/160）、三条HDL命令、ISA=0，模型及事务判据复用016，不重跑旧版/历史/PHY/CoreMark。新173项清单SHAf85e5e40…528ec，AST/静态计数及只读输入检查通过，HDL NOT_RUN；Codex停交DeepSeek。成功基线复用016源码和143fa795位流/PDS/实板证据，以coremark_i16_01 P/V5.017/5.149秒为相邻对照，后续实际DDR日志coremark_d16_01，不重建原120次BIN。仿真期间不并行PDS，避免保护产物改变。见[本轮评估修改及完整剩余操作](cpu/MINI十六行D缓冲评估修改与交接_2026-10-12.md)。下文I16无待领取及仅建议D16为实施前历史。

用户2026-10-12补充：以后交来DeepSeek结果，Codex连续完成证据审查、记录更新及本轮剩余PDS/上板/新跑分准备，不逐步询问是否继续。PDS与实板仍由用户执行；交来对应产物/日志后自动衔接核对与性能分析。当前D16剩余操作及新日志命令见[同一阶段记录](cpu/MINI十六行D缓冲评估修改与交接_2026-10-12.md)。

## 当前实施：MINI I16实际DDR验收PASS，吞吐升16.64%/16.38%（2026-10-12）

新`board/coremark_i16_01`原120次P/V各1轮经完整原始日志核验：COM9、129响应/唯一RUN、DDR VERIFY、CRC d340/200d、13项计数守恒、同BIN/ELF/manifest及143fa795本地位流身份通过。cycles470388387/482747078、时间5.017476128/5.149302165秒、CPI4.724147/4.558425；相对成功I8/D8 coremark_d8_01耗时降14.2627%/14.0766%、吞吐升16.6354%/16.3828%。退休/分支次数/AW相同；IF少19.58%/19.02%、branch恢复少42.02%/40.60%，合计解释99.86%/98.73%周期减少；恢复类别含目标取指等待，不是分支数或BTB变化。MEM绝对周期基本持平、当前占40.74%/39.29%，AR少33.09%/33.43%但不能推I命中率。

建议保留I16/D8、93.75MHz，无需追加仿真或重复测量；两轮不足10秒仅作同BIN性能比较。收据`sim/mini_board_migration/build/inst_cache16_preparation_20261012_a/board_review.json`只冻结两新日志并复用旧基线/PDS证据。124项登记输入保持，PDS仅生成注释更新，其他实现证据保持；本轮只离线审查/记录，未改RTL/软件或启动HDL/PDS/串口。下一候选仅建议评估D8→16的容量与时序，尚未实施；缺少D miss/读写等待细分，不能先认定收益，新最差CPU→D.CE路径须关注。见[本轮完整记录](cpu/MINI十六行I缓存评估修改与交接_2026-10-12.md)。下文待上板/待PDS/收益待测为此前历史。

用户新位流143fa795版已核验：最终PG2L200H/-6/FBB676、Pre-silicon多角十组汇总失败0、seed4根PnR一致；CPU93.75MHz，setup慢/快+0.692/+4.754ns、hold+0.148/+0.100ns，慢角余量比I8/D8少0.114ns。物理FF16566/LUT11733（+2224/+616）、DRM8不变，桥6805FF/2420层次LUT；新最差CPU有效地址→D行2 bit81.CE，11级、布线77.927%。124项登记输入与016一致，综合I16/D8，成功Loader及原120次BIN保持。位流13:51:01生成、9188552byte，SHA `143fa795396f4e25bf648da3d9960aeeee3d781691ff6e0a20b844a901a4b62a`。收据`sim/mini_board_migration/build/inst_cache16_preparation_20261012_a/pds_review.json`冻结16份新实现证据，未重复归档整套输入；既有未约束IO/SCBV及综合清理/高扇出提示保留，不记零PDS警告。下一步用户下载这份位流，COM9原120次P/V各1轮，新日志coremark_i16_01，对照成功I8/D8 coremark_d8_01，具体命令见[同一阶段记录](cpu/MINI十六行I缓存评估修改与交接_2026-10-12.md)。新实板收益待测，不足10秒仅比较；不补仿真，下文待PDS为此前历史。

用户确认继续单项优化并交DeepSeek关键仿真。只改现有桥I8→16，x32 I容量256→512byte、索引[7:5]→[8:5]，D8/32byte行/完整tag/CPU接口/总线FSM保持，桥SHA0b1b2fac…3abc69。静态原BIN9～14行函数跨度支持实验，仍有调用索引重叠，不证明动态瓶颈或收益。理论增2272bit状态，16路选择/填充/reset扇出及布局风险待新PDS；旧+0.806ns不能套用。

[任务016报告](../DeepSeek/任务016_结果_ds_mini_i16_20261012_133046.md)经原始证据核验PASS：当前I16/D8 x32一个TB一次，五组442检查（165/51/63/43/120），三条命令退出0、Errors/Warnings 0，30070ns正常结束。四份源码/清单副本一致，执行Git快照字节相同，D8及总线/FSM保持；ISA=0，无追加仿真。收据`sim/mini_board_migration/build/ds_mini_i16_20261012_133046/codex_review.json`。执行171项保护输入一致；审查初次全部匹配，用户PDS开始后收据时160项匹配，11项项目/实现产物的旧身份由既有冻结D8证据验证。报告HEAD抄写错误以原始快照为准，不影响PASS。当前无待领取仿真；用户完成PDS后交新I16最终时序/资源/位流，随后实际DDR原120次P/V各1轮，对照成功I8/D8任务015源码、1fc7eff0冻结位流及coremark_d8_01 P/V5.852/5.993秒，不用旧coremark_01。新时序/资源/收益待测，不足10秒仅比较。见[本轮评估修改及审查](cpu/MINI十六行I缓存评估修改与交接_2026-10-12.md)。下文旧待执行状态为历史。

## 当前实施：MINI D8实际DDR对比PASS，吞吐提高8.14%/8.69%（2026-10-12）

用户完成D8上板及COM9固定120次P/V各1轮，`sim/mini_board_migration/board/coremark_d8_01/`两日志经独立核验：129响应/唯一RUN、DDR VERIFY、CRC d340/200d、13项计数守恒、同BIN/ELF/manifest及1fc7eff0本地位流身份通过。cycles548639306/561834467、时间5.852152597/5.992900981秒、CPI5.510027/5.305222。相对MINI D4 coremark_01耗时降7.5279%/7.9927%、吞吐升8.1407%/8.6871%；MEM少18.7585%/20.3352%、AR少15.8589%/17.2291%，退休/分支次数/AW相同，约99%周期减少来自MEM类别。当前MEM仍约34%～35%、IF24.4%、分支恢复22.6%～22.8%；混合AR不能推D命中率。

两轮均不足10秒，仅是正确同BIN性能比较，不记正式CoreMark成绩。原120次BIN保持，本轮建议保留I8/D8，无需新增仿真或重复测量。收据`sim/mini_board_migration/build/data_cache8_preparation_20261012_a/board_review.json`只保存两份新日志并复用旧基线；124项登记输入和14份PDS产物身份仍匹配。本次仅离线审查/记录，未改RTL/软件或启动HDL/PDS/串口。见[本轮完整记录](cpu/MINI八行D缓冲评估修改与交接_2026-10-12.md)。下文待上板/收益待测为此前历史。

用户新PDS已核验：PG2L200H/-6/FBB676、Pre-silicon多角、所选seed4，十组汇总失败端点0；CPU仍93.75MHz，主时钟setup慢/快+0.806/+4.853ns、hold+0.148/+0.101ns，慢角setup比MINI D4增0.082ns。最终物理FF14342/LUT11117（较D4 +1116/+386）、DRM8不变；桥FF4581/LUT1774。最差路径data_ram→load/前递→ID分支/取指控制→inst_pending_pc[22].CE，11级、布线59.859%。既有未约束IO/SCBV提示保持，不冒称零警告或提频。

新本地位流SHA `1fc7eff0baa336c78c6b03fa5ede19a38d7ea9e781eb375c25d64a4fd10b666b`，12:36:20生成，输入根PnR与seed_4 ADF相同。124项登记源/IP/约束与任务015匹配，桥aafa7daf版、综合确为I8/D8各256byte，成功Loader/原120次BIN保持。收据`sim/mini_board_migration/build/data_cache8_preparation_20261012_a/pds_review.json`仅保存14份新实现证据，旧基线复用。下一步用户下载1fc7eff0版及实际DDR固定120次P/V各1轮，对照MINI coremark_01；实板收益待测，不足10秒仅比较，不追加仿真。见[本轮完整记录](cpu/MINI八行D缓冲评估修改与交接_2026-10-12.md)。

此前按用户授权直接修改现有myriscv桥，x32 D数据容量128→256byte、索引[6:5]→[7:5]，完整tag/32byte行保持。I8维护及总线/FSM逐字不变，CPU/IP/UART/计数器/原120次BIN未改。理论增1136bit状态；原MINI成功D4桥4780997a及位流5aea57d5已在前轮167项证据中冻结，不重复归档。下文新时序待测/待用户PDS为本轮实现前历史。

[任务015报告](../DeepSeek/任务015_结果_ds_mini_d8_20261012_115734.md)已独立核验：当前D8一组x32关键TB一次，5组274检查（85/35/47/27/80）、三条命令退出0、Errors/Warnings 0，19970ns正常结束；ISA=0。桥/TB/runner/清单四副本一致，执行git前后字节相同，I维护及总线/FSM与D4逐字一致。收据`sim/mini_board_migration/build/ds_mini_d8_20261012_115734/codex_review.json`。清单171项是执行时保护口径；审查采样161项当前匹配，10项PDS/实现产物已变化或移除，其旧身份全部由既有冻结基线验证，设计/IP/BIN身份保持。当前无待领取仿真，不重跑历史；用户完成PDS后交最终D8时序/资源/位流，再实际DDR原120次双模式各1轮，对照MINI coremark_01成功D4，不足10秒仅比较。新时序与收益仍待测。见[同一阶段评估及审查](cpu/MINI八行D缓冲评估修改与交接_2026-10-12.md)。下方“未实施D8/无仿真任务”为实施前历史。

## 流程进一步精简（2026-10-12）

按用户要求，后续默认三步：Codex评估并完成单项RTL修改/审查；DeepSeek跑一组直接相关的关键仿真一次，Codex合并核对原始日志；用户执行PDS并交最终时序/资源审查，再实际DDR上固定BIN的CoreMark P/V各1轮。CPU未改时不例行跑2项ISA，已有基线及历史PASS不重复跑；只有CPU行为变化、TB/模型/判据变化或新增失败时补相应最小覆盖。DDR IP/PHY/时钟改动保留相关物理测试。只评估不改RTL时不跑验证，审查不另拆多轮，记录优先在本轮同一文档更新，不重复归档相同输入。

正式成绩仍需单次至少10秒；本轮MINI原120次6.33/6.51秒仍只作性能比较。没有改RTL/软件/PDS、没有新增测试或DeepSeek任务。下文每轮固定ISA及独立审查流程为历史，长期默认以更新后的AGENTS.md为准。

## 最新MINI实板审查：实际DDR固定120次正确，吞吐提升约24.8%（2026-10-12）

用户完成MINI新位流下载和COM9实板运行，Hello23响应/1 RUN及原120次P/V各129响应/1 RUN全部独立核验：DDR CRC32 VERIFY、CoreMark final d340/200d、软件身份和13项计数守恒通过。P/V时间6.328557963/6.513508448秒、cycles593302309/610641417、CPI5.958581/5.766090；不足10秒只记正确同BIN性能比较，不记正式成绩。对照换板前163128_455 I8/D4，耗时降19.8772%/19.6989%，吞吐升24.8084%/24.5312%；MEM仍占39.78%/39.20%，IF约22.5%，分支恢复约20.9%。

迁移同时改变DDR x16→x32、用户拍128→256bit、行16→32byte，I8容量变256byte、D4变128byte，当前桥SHA4780997a；不能把跨板收益全部归因D4或DDR带宽。新本地位流SHA5aea57d5…bd62a与三份日志匹配，用户说明已下载，工具未独立观察配置。新PDS报告PG2L200H/-6/FBB676、Pre-silicon多角模型、所选seed5，十组汇总无违例，CPU仍93.75MHz，主时钟setup慢/快+0.724/+4.760ns、hold+0.137/+0.102ns；既有未约束IO范围保留。最终物理表FF13226/LUT10731/DRM8，层次表LUT10069为另一口径。当前Loader DAT及71 DDR球位保持。

收据sim/mini_board_migration/build/review_board_performance_20261012_a冻结167份证据，状态MINI200H_ACTUAL_DDR_FIXED120_EVIDENCE_AUDIT_PASS。本轮只读审查/归档/文档更新，没有改RTL/IP/PDS/BIN或运行HDL/PDS/串口，无待领取DeepSeek任务。建议下一阶段先单独评估D4→D8及读miss/写等待分项；正式≥10秒程序另一个软件阶段准备，240次时长仅估算，不同时改硬件。见[完整分析](cpu/MINI200H换板实板性能与时序分析_2026-10-12.md)。下方MINI实板/PDS待验证为上板前历史，x16旧成功记录不套用于当前新板。

# 盘古 MINI-(200H) 换板更新（2026-10-11）

新 ROM/RAM/DDR3 三 IP 已接入主 RTL 与 PDS。用户在 DDR IP Step 3 导入板级 FDC 后重新 Generate，71 个 DDR 球位全部匹配、生成日志 0 error/0 warning。上板前 x32 桥、当前 Loader 真实 UART 引脚下载 Hello、CoreMark performance/validation 各 1 次短迭代 CRC 仿真 PASS；120 次下载计划离线核对通过。DDR IP 两片物理模型训练及训练后真实 REFRESH 复验 PASS，ModelSim Errors 0、模型无 `ERROR:`；前几轮测试平台判据失误及失败日志保留。该物理模型测试没有 SoC 数据事务。PDS 实现、时序、新位流和 MINI 实板仍待用户验证。ROM/RAM 当前为 `verify_run_hello` 同一对 Loader DAT。详见 [上板前仿真与 CoreMark 交接](board/盘古MINI上板前仿真与CoreMark交接_2026-10-12.md)及[三 IP 适配与脚位记录](board/盘古MINI三IP适配与DDR脚位待修正_2026-10-11.md)。下文性能、位流、实板状态均为原板卡历史记录。


## 最新审查：四行D关键功能PASS，交用户PDS（2026-10-11）

任务014 ds_data_cache4_20261011_161118原始证据已独立核验：旧I8/D1 130项、新I8/D4 175项、两版六组CHECK与Errors/Warnings 0；lb/sll抽测装载273/454 words、tohost=1、cycles3603/5949，seed2026101114可复现。lb实际D_READS24/D_AR1/D_HITS23，仅是该用例覆盖。九条HDL命令身份/参数/退出码、97项输入、五份准备镜像、冻结基线及前后git快照一致。收据sim/inst_line_buffer/build/review_data_cache4_20261011_a冻结56份证据与编译源码，状态DATA_CACHE4_EVIDENCE_AUDIT_PASS。

当前桥f4a168e4版I8/D4关键功能PASS，无待领取仿真，不重跑014/013/009或历史全套。Codex仅复核归档与更新文档，未改RTL/TB/runner/软件或启动HDL/PDS/串口。下一步用户执行主RISCV.pds实现，再核对D4新时序/资源/源身份及Loader初始化；I8/D1旧+0.278ns不能套用，新D4时序/实际收益尚未核验。通过后用户下载位流、原run_measurements.ps1固定120次P/V各1轮实际DDR，对照155529成功I8/D1，软件保持；不足10秒仅作正确对比。无需Generate Netlist或新部署门控。见[完整审查及实板步骤](cpu/四行数据读缓冲实现与仿真交接_2026-10-11.md)及[原报告](../DeepSeek/任务014_结果_ds_data_cache4_20261011_161118.md)。下方014待执行/HDL NOT_RUN为准备阶段历史。

## 实施记录：八行I实板收益已核验，单独试作四行D，停交任务014（2026-10-11）

155529_327实际DDR原120次P/V日志正确，时间8.508050336/8.682317643秒、CPI8.010658/7.686031，CRC d340/200d、129响应/1唯一RUN各一次、13计数守恒和软件/本地9d632d44位流身份一致。相对143832四行I+单行D耗时降低19.2318%/18.6575%、吞吐提高23.8111%/22.9370%，IF降约25%/24%、branch恢复降约40%、AR降约29%/28%，instret/branch次数/AW不变。两项不足10秒只记正确同BIN性能对比，不冒称正式成绩；compare_cache8_20261011_a冻结四日志/软件/源码/位流。见[实板分析](cpu/八行指令缓存实板性能分析_2026-10-11.md)。

用户要求继续性能优化，选择只将D从1→4行64-byte（当前MEM占41%～42%，不保证容量收益），直接改myriscv桥为f4a168e4…50bbf：D索引[5:4]、锁存fill tag[1:0]、完整tag写失效、reset覆盖4行，I8维护块不变、总线/FSM只有D命中行选择变化。单拍/单事务/数据优先/CPU32位接口及原软件保持。成功I8/D1桥a2c28dce和位流9d632d44冻结在data_cache4_baseline_20261011_a；本地位流仍成功D1，不是D4。

只准备[任务014](../DeepSeek/任务014_四行数据读缓冲关键仿真.md)：新TB旧D1/新D4各一次，静态预期130/175项、6组CHECK；种子2026101114分层随机lb/sll各一次，装载273/454 words，lb强制正数D_HITS，不追加第三轮或历史全套。新97项清单、镜像、AST/静态计数/只读检查通过；HDL NOT_RUN，新D4时序/资源/收益NOT_MEASURED，Codex停交DeepSeek。见[实现交接](cpu/四行数据读缓冲实现与仿真交接_2026-10-11.md)。后续仅在仿真核验后由用户PDS及实际DDR固定120次P/V各一轮，对照155529成功I8/D1基线；不同时换测量软件，正式更长BIN另阶段。下方无待领取/时序PASS描述前序I8/D1，不描述当前未验证D4。

## 最新PDS审查：八行I缓存所选seed2时序PASS，交用户实板对比（2026-10-11）

新report_timing/board_top.rtr（15:42:38）All Constraints Met，93.75MHz不变，主时钟慢/快setup+0.278/+4.257ns、hold+0.134/+0.100ns，十组报告全部失败端点0。所选seed2通过且根PnR DB SHA匹配seed2；seed3/4/5慢角仍负，不记全部seed PASS。最终PnR FF8444/LUT7534/DRM8/Distributed RAM44，相对四行+604FF/+139LUT；map摘要LUT7611（+216）是另一阶段口径。桥模块+604FF/+188LUT。最差路径CPU if_id_inst[23]→性能计数器recovery_target[31] CE，18级逻辑、布线70.810%，不能由报告推出新性能收益。

任务01372项输入一致，综合网表8行I、单行D/计数器保留、UART等待链消失；成功Loader IDF/DAT及8个综合DRM配置/INIT与四行成功版相同。新本地位流15:42:59生成，SHA9d632d44894061c3247214885c4e5f3c0436596973543d3ae91a998fbbeb6427；收据sim/inst_line_buffer/build/review_cache8_pds_20261011_a冻结22份证据，状态INST_CACHE8_POST_PNR_TIMING_AUDIT_PASS。保留既有未约束IO与未独立解码位流INIT/观察FPGA配置的范围限制。Codex未改RTL/PDS/软件或启动实现/仿真/串口，无待领取DeepSeek任务。

下一步用户下载新位流，关闭串口助手后执行原run_measurements.ps1（默认COM11），按KEY0提示原固定120次P/V各1轮实际DDR，对照143832四行I+单行D基线；不足10秒只记正确同BIN对比，正式成绩仍至少10秒。八行实板收益NOT_MEASURED，不补历史全套，不要求Generate Netlist/新门控。见[完整PDS审查及步骤](cpu/八行指令缓存PDS时序审查_2026-10-11.md)。下方新时序/资源待测及旧本地位流为历史。

## 最新审查：八行I缓存关键功能PASS，交用户PDS（2026-10-11）

任务013的ds_cache8_resume_20261011_153003原始证据独立核验通过：八行176项/6组CHECK、ModelSim Errors/Warnings均0；随机ld_st/xor实际CPU装载DDR模型1056/418 words、tohost=1、cycles14534/5559，seed2026101112。六条实际工具命令源路径/参数正确、退出0，72项输入及5份ISA准备镜像SHA相同，前后git快照一致；复用四行124项，原012 FAIL保留。RTL静态审查未发现新阻断，桥仍a2c28dce、UART0f51c37d。收据sim/inst_line_buffer/build/review_cache8_evidence_20261011_a归档53份证据，状态INST_CACHE8_EVIDENCE_AUDIT_PASS。

当前无待领取仿真，不重跑013/012或历史全套；Codex未修改RTL/TB/runner/BIN或启动HDL/PDS/串口。下一步用户完成主RISCV.pds PDS实现，核对八行版新时序/资源及成功Loader初始化身份；旧四行+0.147ns不能套用。通过后用户下载位流，沿用原run_measurements.ps1固定120次P/V各1轮实际DDR，与143832基线比较；不足10秒只记正确对比。新时序/资源/实板收益待测，无需Generate Netlist/新门控。见[完整审查](cpu/八行指令缓存计数判据复核与续测_2026-10-11.md)及[任务013报告](../DeepSeek/任务013_结果_ds_cache8_resume_20261011_153003.md)。下方013待执行/八行未运行均为历史。

## 最新复核：任务012数量预期错误，停交任务013（2026-10-11）

原ds_cache8_20261011_151153四行基线6组CHECK/124项PASS、编译仿真Errors/Warnings均0，57项输入不变；runner因Codex把预期数量加错而中止，八行及ld_st/xor未运行。正确合计13L+72：四行124、八行预期176。原FAIL/任务012/清单/runner/报告保留，复核收据在sim/inst_line_buffer/build/review_cache8_count_20261011_a，归档14份证据/57份输入。

当前只领取[任务013](../DeepSeek/任务013_八行指令缓存计数修正续测.md)：新resume_cache8.py/72项清单，只补八行关键TB及原ld_st/xor各一次，seed2026101112，装载1056/418 words；四行不重跑。AST/只读检查通过，HDL待运行，RTL/TB未改。八行整体功能/新时序/资源/实际DDR收益仍待验证，旧四行+0.147ns不能套用。见[复核与续测](cpu/八行指令缓存计数判据复核与续测_2026-10-11.md)。下方012待领取及144/196为原准备阶段错误记录，已由本条更正。

## 当前实施：八行128-byte I缓存已改，停交任务012（2026-10-11）

用户确认8行候选，直接改myriscv/dual_sram_to_pango_ddr_bridge.v：I数组/valid扩大为8行、取指/写失效索引[6:4]、锁存fill索引tag[2:0]、复位覆盖8行。桥新SHA a2c28dce…4091a；单行D维护块与总线/FSM尾部逐字不变，UART仍0f51c37d，未改CPU/PDS/IP/成功120次BIN。旧四行I+单行D成功桥b7c2b366及位流e22a936f冻结在sim/inst_line_buffer/build/eight_line_baseline_20261011_a。

只准备[任务012](../DeepSeek/任务012_八行指令缓存关键仿真.md)：同TB旧4/新8行关键对照（预期144/196项、6组CHECK），随机ld_st/xor各1次，seed2026101112，CPU装载DDR分别1056/418 words。新57项清单SHA54f0edf0…872af，静态准备/镜像完成，--check-inputs通过；**HDL NOT_RUN，新时序/资源/收益NOT_MEASURED**。Codex停在HDL编译之前，交DeepSeek执行，不追加历史全套。当前本地位流/PDS报告仍旧成功4行版，+0.147ns不能套到8行。续测经核验后交用户PDS及实际DDR同120次双模式各1轮，对照143832基线；不足10秒只记正确对比。见[实现交接](cpu/八行指令缓存实现与仿真交接_2026-10-11.md)。下方仅评估/无待领取任务为实施前历史。

## 最新评估：扩大I缓存，建议下一候选8行128-byte（2026-10-11）

已单独核对当前4行I/单行D桥、120次原BIN反汇编与PDS时序：4/8/16行索引重复周期为64/128/256 byte，完整tag方案理论状态628/1256/2512 bits。部分向后分支地址跨度6～8行、另有9～14行；矩阵调用乘法示例重叠索引4行3个、8/16行均1个，证明扩容能分开部分冲突但不能消除全部，未测动态miss频率。当前setup+0.147ns、最差路径布线83.238%，更大选择/填充扇出和布局可能侵蚀余量。

建议只选8行128-byte直接映射进入下一实施阶段，保持16-byte行、单行D、32位CPU总线、单拍DDR和原响应节拍；16行保留为后续候选，不承诺收益或断言最佳容量。静态证据sim/inst_line_buffer/build/evaluate_icache_capacity_20261011_a归档15份输入与CSV，状态ICACHE_CAPACITY_STATIC_EVALUATION_NOT_SIMULATED。本轮只评估，RTL/PDS/IP/BIN未改，未启动仿真/PDS/串口，没有待领取DeepSeek任务。已给出确认后的最小实施/验收范围，评估完成后停止。见[完整评估](cpu/I缓存扩容容量冲突与时序评估_2026-10-11.md)。

## 最新实板：单行D读缓冲双模式正式运行通过，收益约3%（2026-10-11）

measure_20261011_143832_643原固定120次performance/validation实际DDR日志已离线核验：时间10.533914485/10.673780000秒，cycles987554483/1000666875，CPI9.918087/9.448975，CRC d340/200d正确，两项均满足10秒门槛。软件身份、13计数、周期分类与AR+AW守恒、258响应/2唯一RUN/零重试均通过，本地位流e22a936f版与已有PDS审查一致。相对四行I/无D的125621基线，同BIN耗时减少3.0810%/2.9285%、吞吐提高3.1790%/3.0168%；MEM减少8.33%/7.98%，AR减少4.67%/4.65%，instret、branch_redirects、AW不变。不能由混合I/D的AR计算D命中率。

收据在sim/inst_line_buffer/build/review_data_read_board_20261011_a及compare_data_read_20261011_a，比较目录冻结四份日志、软件、源码/位流与既有审查证据。每模式仅1轮，无方差估计；候选还含UART等待链精简，未分别实板隔离因果，FPGA配置未独立读取。本轮未改RTL/BIN或启动HDL/PDS/串口。建议保留单行D，下一步单独评估扩大I缓存；当前无待领取仿真任务，分析后停止等待指示。详见[实板性能分析](cpu/单行数据读缓冲实板性能分析_2026-10-11.md)。下方实板NOT_TESTED/收益NOT_MEASURED为历史。

## 最新PDS审查：UART精简后最终时序PASS，交用户实际DDR测量（2026-10-11）

用户新report_timing/board_top.rtr（14:20:50）为All Constraints Met，93.75MHz保持，主时钟慢/快setup+0.147/+4.274 ns、hold+0.140/+0.101 ns，两角所有报告类别失败端点0。所选seed2最终通过；seed3/4仍负，不记所有seed PASS。综合网表已无wait_count/g_rsp_delay，D缓冲data_line_valid/data保留；任务01146项输入及成功Loader IDF/DAT身份一致，主myriscv编译路径正确。新FF7840/LUT7395/DRM8/Distributed RAM44，资源变化不当作模块独立收益。

新本地位流生成14:21:11，SHA e22a936f9bd36b3f1ce1f86a2bdefc052069f399d88592091a1d74a355fb703a；收据sim/uart_mmio/build/review_wait_chain_pds_20261011_a/review_result.json为UART_WAIT_CHAIN_POST_PNR_TIMING_AUDIT_PASS，归档20份证据。既有约束下时序通过，未约束IO及未完整审计位流INIT的范围限制保留，FPGA配置未独立观察。Codex本轮未运行PDS/HDL/串口，未改设计/软件、未建立新门控或要求Generate Netlist。

下一步用户下载新位流、关闭串口助手，运行tools/uart_loader/candidates/perf_2b/run_measurements.ps1（默认COM11），按提示逐模式KEY0复位。原120次performance/validation BIN各1轮，实际DDR与measure_20261011_125621_924基线比较；不足10秒仅记对比，正式仍>=10秒。当前新实板NOT_TESTED、D缓冲收益NOT_MEASURED，无待领取仿真，不追加重复实现。见[最新审查及实板步骤](cpu/UART等待计数链精简与仿真交接_2026-10-11.md)。下方等待PDS/旧位流/WNS−0.028为历史。

## 最新审查：UART等待链关键验证PASS，交用户重新PDS（2026-10-11）

任务011原始ds_uart_wait_20261011_140553独立核验通过：delay0/1/2/6每参数28笔事务、29次接受/28次响应、1个TX字节/1笔复位取消，4组CHECK完整，选定激励下旧/新外部输出采样相同及独立判据PASS；lbu/jal CPU实际DDR装载273/135 words、tohost=1、cycles3603/1711，seed2026101111。5条工具命令源路径/参数正确、退出0，编译日志空、无error/warning/FAIL。46项输入及5份准备镜像一致，前后git快照相同，UART仍0f51c37d、桥仍b7c2b366，RTL静态审查无新增阻断发现。

收据sim/uart_mmio/build/review_wait_chain_20261011_a/review_result.json为UART_WAIT_CHAIN_EVIDENCE_AUDIT_PASS，保存24份原始证据/46份输入。原报告把实例索引写反（实际baseline0/new1）及“4组×28”歧义已在审查文档说明，实际TB/计数正确，不改原证据。本轮未修改RTL/TB/BIN或运行HDL/PDS/串口，当前无待领取仿真任务，不重跑011/009/010或历史全套。

下一步由用户RISCV.pds重新实现/生成位流，确认零延迟UART计数链消失及最终Post-PnR时序满足93.75MHz；当前报告/本地位流仍精简前13:45:59/58161d79版，旧WNS−0.028 ns未被新测量覆盖，新UART时序/资源及D缓冲实板收益NOT_MEASURED。功能PASS不记时序PASS。无需Generate Netlist/新门控，成功Loader DAT不变；时序通过后下载并运行原run_measurements.ps1，实际DDR固定120次双模式各1轮，不足10秒只记对比。见[完整审查与交接](cpu/UART等待计数链精简与仿真交接_2026-10-11.md)及[任务011报告](../DeepSeek/任务011_结果_ds_uart_wait_20261011_140553.md)。下方待011/NOT_RUN为历史。

## 当前步骤：UART零延迟等待链已精简，停交任务011（2026-10-11）

用户授权只精简UART等待链，直接改myriscv/uart_mmio.v：零/负延迟generate分支rsp_valid=pending，无计数器/比较链；正延迟按N+1所需宽度倒计数，延迟6缩为3位。请求接受后下一拍响应语义保持，主副作用/pending/response块除3处旧counter写语句外逐字相同，译码/TX/RX/FIFO/IRQ连接相同。UART新SHA0f51c37d…01ace7，D桥仍b7c2b366；CPU/MMIO计数器/PDS/IP/时钟/BIN未改，原最终WNS−0.028 ns记录保留，新时序NOT_MEASURED。

只准备[任务011](../DeepSeek/任务011_UART等待计数链关键仿真.md)：一个TB旧/新外部输出对比与独立判据，delay0/1/2/6同时运行，每模式28笔完整事务+1笔复位取消；随机ISA lbu/jal各一次，seed2026101111、CPU加载273/135 words到DDR用户口模型。共5条Icarus/vvp命令，不重跑009/010、历史UART底层/IRQ/Loader/CoreMark/物理DDR或全ISA。新46项清单SHA72a32da9…b0d27e6；Python/只读检查/静态镜像准备完成，**HDL NOT_RUN，新实板NOT_TESTED**。Codex未运行HDL/PDS/串口，当前停下交DeepSeek；原任务清单不改写，因新UART变化拒绝当前输入是预期。

旧UART原文/只改模块名对照在sim/uart_mmio/build/wait_chain_baseline_20261011_a，准备收据在wait_chain_preparation_20261011_a。续测经Codex核验后才由用户重新PDS核对等待链消失及最终时序；无Generate Netlist或新门控。实际DDR同120次BIN双模式各1轮计划保持，正式>=10秒。见[实现与交接](cpu/UART等待计数链精简与仿真交接_2026-10-11.md)。下方未修改UART/无待领取仿真为本轮实施前历史。

## 最新时序审查：新D缓冲实现setup差28 ps，尚未时序PASS（2026-10-11）

用户13:45:59最终report_timing/board_top.rtr为Some Constraints Violated。93.75MHz主时钟慢角WNS/TNS−0.028 ns、1个失败端点；快角setup、两角hold/recovery/removal/pulse width均通过。seed2/3/4/5慢角setup分别−0.028/−0.251/−0.332/−0.042 ns，CSV State=OK不是时序PASS。根after_hold_fix文件为10月5日历史，seed2同名+0.063 ns是中间结果，不能替代最终−0.028 ns。

最差路径UART wait_count→数据互连→CPU分支/控制→性能classification_q，16级、布线占78.051%，没有直接经过D缓冲；不能断言D是根因。板级UART响应延迟为0，仍综合出32-bit等待计数链，建议下一开发步骤只精简该链、保持下一拍响应/副作用语义；尚未修改RTL，不追加重复seed或仿真。原功能验收PASS保留，新硬件尚未时序PASS/实板验收。当前本地位流已由用户重建为58161d79…04ca3（13:46:22），旧76eaffa3身份仅作成功基线，FPGA配置未独立观察。

本轮只读审查/归档/文档，Codex没有启动PDS/HDL/串口；16份证据及收据在sim/inst_line_buffer/build/review_data_read_timing_20261011_a，状态POST_PNR_TIMING_SETUP_FAIL。先处理时序再继续正式实板验收；收益仍NOT_MEASURED。详见[时序报告审查](cpu/单行数据读缓冲PDS时序审查_2026-10-11.md)。下方交用户重建记录为本次实现前状态。

## 最新审查：单行D缓冲功能验证通过，交用户PDS/实板（2026-10-11）

任务010原始ds_data_cpu_20261011_132836已独立核验：lw装载297 words、24次CPU数据读、1次DDR数据AR、23次缓冲命中，tohost=1、cycles3915；仅一次Icarus编译/一次vvp，退出0、无error/warning/FAIL。89项输入及4份准备镜像一致，前后git快照相同。原任务009旧/新桥各201项及随机xori/bne（seed2026101109）保留，原冻结证据再次核验；返回ID的CPU命中覆盖缺口已关闭，不重跑历史PASS。

综合审查收据sim/inst_line_buffer/build/review_data_read_cpu_20261011_a/review_result.json为DATA_READ_BUFFER_EVIDENCE_AUDIT_PASS，同目录归档19份证据/89份输入。RTL仍b7c2b366，新静态审查无阻断发现；此次只审查/归档/更新文档，未改RTL/TB/BIN/PDS/IP、未启动HDL/PDS/串口。当前无待领取仿真任务。lw的24/1/23只证明用例覆盖，不当作CoreMark命中率或实板提速；新版实板NOT_TESTED，收益/时序/资源NOT_MEASURED。

下一步用户在根目录RISCV.pds自行重建、核对93.75MHz时序/资源并下载，保持成功Loader ROM/RAM DAT；无需Generate Netlist或新门控。随后运行tools/uart_loader/candidates/perf_2b/run_measurements.ps1，原固定120次performance/validation各1轮，经实际DDR3与measure_20261011_125621_924比较。正确但不足10秒只记同BIN对比，正式仍至少10秒；必要时再准备更长正式软件，不重建原成功BIN。旧compare_cache4_formal120.py绑定前阶段，待新日志另适配D候选离线比较，不改旧清单/收据。见[审查及实板交接](cpu/单行数据读缓冲仿真审查与CPU续测_2026-10-11.md)和[任务010报告](../DeepSeek/任务010_结果_ds_data_cpu_20261011_132836.md)。下方待010/009为历史状态。

## 最新审查：D缓冲桥各201项PASS，CPU返回ID缺口只补lw（2026-10-11）

任务009原始ds_data_read_20261011_131855已独立核验：旧/新桥各201项，Errors0/Warnings0；xori/bne tohost=1，实际CPU加载235/291 words、cycles3069/3847，9命令退出0、镜像与准备版一致、原84项输入未变。34份原始证据/84份待测输入已保存于review_data_read_20261011_a；收据为DATA_READ_BUFFER_UNIT_PASS_ISA_RID_RESUME_REQUIRED。RTL静态审查无新增阻断问题，桥仍b7c2b366。

发现共用source/tb_soc_ddr3_rv32i_fast.v原RID固定0，不能分配要求RID1的D缓冲；xori/bne本身无load，保留已有PASS但不作为D命中覆盖，不重跑。只修正仿真TB回显AR ID、增加可选端口读/AR计数，交任务010补一个lw并强制正数D_HITS。新89项清单SHA18ab90cb…3bc6f4，TB SHAefa56bdd…edc81f，Python/镜像/只读检查完成；code293+data4=297 words。**适配TB/lw HDL NOT_RUN，整体验收暂未完成，新实板/性能待测**。不重跑201项/两个ISA/历史全量，不启动PDS或串口。

装载字数旧预估239/295误含留在RAM的4个元数据字，文字已更正为235/291，更正前原文已保存，原日志/清单/报告不改。原审查“两例重跑”建议已由followup_plan缩减为单例lw。当前只领取[任务010](../DeepSeek/任务010_数据读缓冲CPU返回ID适配续测.md)，续测原始证据复核后才交用户PDS/实板；见[审查及最小续测](cpu/单行数据读缓冲仿真审查与CPU续测_2026-10-11.md)。下方任务009停交接为历史，旧manifest因TB变化拒绝当前输入，不能重写绕过。

## 当前步骤：单行D读缓冲已实现，停在任务009仿真交接（2026-10-11）

用户授权采用。只改现有myriscv/dual_sram_to_pango_ddr_bridge.v：单行16-byte D读缓冲，DATA_LINE_BUFFER_ENABLE默认1，命中接受后下一拍RSP/no AR；miss锁原tag、RID1/last有效才填128-bit。写仍直达DDR、同行同时清I/D（部分/零strobe保守失效），reset/DDR未就绪清D。原四行I维护块、总线输出和RADDR之后DDR状态静态逐字相同；CPU/MMIO/软件/PDS/IP未改。主桥SHA b7c2b3664b80b22bdf353d4c4236edfcd93cf59e0a5f6602683421b6692c8e97。

四行成功桥a1bf18ff、本地成功位流76eaffa3及旧工具冻结于data_read_baseline_20261011_a，实际基线仍measure_20261011_125621_924的固定120次双模式。旧清单/报告/收据/成功BIN不改写。新data_read_input_manifest.json含84项，SHA cb9abbff…fdc01b；任务009仅一个TB旧/新对照及随机xori/bne（seed2026101109），静态检查/独立镜像准备完成。**HDL NOT_RUN，新版实板NOT_TESTED，收益/时序/资源NOT_MEASURED**；Codex未启动HDL/PDS/串口，当前停止交DeepSeek，无额外测试。

run_measurement.py和review_formal120.py已允许正确短120次只记同BIN对比，正式PASS仍至少10秒；CRC/13计数/完整输出/协议判据保留，PS脚本正确短时会继续第二模式。7项离线分类检查PASS，合成短时文本明确OFFLINE_FIXTURE，不记实板。原120次BIN不重建，不足10秒时才另建更长正式软件。见[实现与任务交接](cpu/单行数据读缓冲实现与仿真交接_2026-10-11.md)及[任务009](../DeepSeek/任务009_单行数据读缓冲关键仿真.md)。下方评估尚未实施及四行最新实板为本候选实施前历史。

## 当前步骤：128-bit单行数据读缓冲评估完成，尚未实施（2026-10-11）

用户要求单独评估。本轮核对CPU/数据互连/桥、CoreMark矩阵和链表访问及DDR链接布局，建议单行16-byte D读缓冲：仅数据读有效拍分配，32-bit槽命中下一拍RSP，不发AR；写保持原AW/W路径且同行同时失效I/D，reset/DDR未就绪清valid。若实施只改现有myriscv桥，保留四行I、仲裁/单在途/单拍接口。关键接入点：现有request_line_tag只锁指令，数据miss需锁原tag；D填充RID=1/last，I仍RID=0，不能漏双缓存失效。

MEM约37%含读写/等待桥/流水阻塞，不是可消除的数据读延迟；单行可能因A/B/栈交替和同行写频繁失效，无实测命中率或预期提速百分比。未来旁路DMA写必须另有不可缓存窗口/失效及所有权协议，volatile不保证硬件一致性。

当前120次只需再快约8%–9%即可不足10秒，现有正式工具会拒绝；实施时先适配固定120次“正确但短时只记对比”并继续双模式，至少10秒正式判据不变，不足10秒才另建更长正式软件。只规划一个桥关键TB及随机2ISA，准备后交DeepSeek；本轮未修改RTL/BIN/测试判据、未运行HDL/PDS/串口，没有新增仿真任务。详见[单独评估及最小验收](cpu/128bit数据读缓冲单独评估_2026-10-11.md)。当前桥/位流仍a1bf18ff/76eaffa3成功四行版，等待后续实施授权。

## 最新实测：四行指令缓存正式双模式PASS，吞吐提高57.25%/62.80%（2026-10-11）

measure_20261011_125621_924已独立核验：performance_120实际10.868786944秒、cycles1018948776、instret99571067、CPI10.233382、CRC d340；validation_120实际10.995790731秒、cycles1030855381、instret105902157、CPI9.734036、CRC200d。两项均超过10秒，软件身份/完整CRC及13计数、分类和AR+AW守恒、258响应/2唯一RUN/零重试或额外RX通过。audit_formal120_20261011_a为COREMARK_FORMAL120_TWO_MODE_BOARD_LOGS_VERIFIED。

与单行measure_20261011_121321_483同120次BIN相比，时间减少36.4052%/38.5766%，吞吐提高57.2456%/62.8043%；instret、branch_redirects、AW不变。IF等待下降38.71%/40.98%，branch恢复下降59.63%/62.06%，MEM下降8.32%/8.67%，AR下降46.09%/48.77%。约63%净周期节省记入branch恢复，符合该分类含目标指令等待的口径，不代表分支次数减少或BTB收益。剩余MEM约37.7%/37.3%，IF约28.2%/28.1%，branch约24.4%/24.3%。

compare_cache4_20261011_a/comparison.json为FOUR_LINE_CACHE_SAME_BIN_BOARD_COMPARISON_PASS，四份日志、软件身份及旧/新桥和本地位流副本已归档。新日志本地位流SHA76eaffa3…abc18d2与当前文件一致，桥仍任务008通过的a1bf18ff版，71项保护输入未变。仅各1轮，无方差估计；未独立观察FPGA配置或核验完整PDS时序/资源。本轮仅分析/离线归档，未改RTL/BIN、未运行HDL/PDS/串口。

建议保留四行优化；下一步先评估128-bit数据读缓冲，不同时修改I-Cache容量/BTB/Burst/M，不承诺收益。当前无新增RTL或待领取仿真任务，等待用户授权下一开发步骤。详见[四行缓存实板性能分析](cpu/四行指令缓存实板性能分析_2026-10-11.md)。下方四行实板NOT_TESTED及比较入口待适配均为测量前历史。

## 当前步骤：四行缓存关键仿真审查PASS，交用户PDS及同BIN实板比较（2026-10-11）

任务008输出ds_cache4_20261011_122922已由Codex独立核验：旧单行/新四行定向各113项PASS，ModelSim编译/仿真Errors0、Warnings0；lh/bge抽测（seed2026101108）由CPU装载285/314 words到DDR用户口模型后tohost=1，cycles3807/4129。9份命令回执退出0，实际源路径/参数正确，生成镜像与准备版一致，71项保护输入及历史清单未变。收据sim/inst_line_buffer/build/review_cache4_20261011_a/review_result.json为INST_CACHE4_EVIDENCE_AUDIT_PASS；29份原始证据及71份待测输入副本已保存。

RTL审查未发现新增阻断问题，新桥仍a1bf18ff版；仅功能模型与两个ISA抽测，不能称全量ISA或实板提速。**新版实板NOT_TESTED，资源/时序/收益NOT_MEASURED**。Codex本轮未改RTL/软件/判据，未启动HDL/PDS/串口；当前无待领取仿真任务，不追加历史回归。

下一步用户在根目录RISCV.pds自行完整重建并下载，保持93.75MHz和成功Loader ROM/RAM DAT；随后运行现有run_measurements.ps1，固定performance_120/validation_120各1轮，与单行measure_20261011_121321_483基线比较。无需Generate Netlist或新部署门控。现有compare_formal120.py绑定上一轮单行身份，新日志返回后另适配四行比较，不能改旧收据；正式时长至少10秒要求保留。见[审查与实板交接](cpu/四行指令缓存实现与仿真交接_2026-10-11.md)及[任务008报告](../DeepSeek/任务008_结果_ds_cache4_20261011_122922.md)。下方HDL NOT_RUN/停止交DeepSeek为执行前历史。

## 当前步骤：64-byte四行指令缓存已实现，停在仿真交DeepSeek（2026-10-11）

用户授权下一步。本轮只改现有myriscv/dual_sram_to_pango_ddr_bridge.v：4行×16-byte直接映射指令缓存，局部地址[5:4]选行、完整[31:4] tag比较；每行独立valid/tag/data，单拍miss填充和同行写失效，其他行保留。数据优先/单outstanding/32-bit CPU接口/DDR握手不变，原总线/FSM区只改命中数据bank选择；CPU/MMIO/软件/PDS/IP未改。新桥SHA a1bf18ff0f48ea0801269ae77fdb1b04f80788d381a4b8c5a1c785b0ac30006d，收益/资源/时序均未测量。

旧单行桥5fbf40c1版和本地成功位流32b07eef版保存于sim/inst_line_buffer/build/four_line_baseline_20261011_a，正式性能基线仍measure_20261011_121321_483的固定120次双模式；旧软件/三个历史manifest/任务007输入清单和原始证据不改写。

[任务008](../DeepSeek/任务008_四行指令缓存关键仿真.md)只跑一个关键TB旧/新对照及随机lh/bge两例ISA（seed2026101108）。新four_line_input_manifest.json含71项，SHA7e7d28fb…d310af8；runner/TB/独立仿真镜像准备完成，Python语法/静态差分/只读输入检查通过。**HDL全部NOT_RUN，新版实板NOT_TESTED，性能NOT_MEASURED**。Codex未运行HDL/PDS/串口；当前停下交DeepSeek，暂无用户上板步骤。待原始仿真日志核验后用户自行重建/下载、同120次BIN双模式各1轮比较，不要求Generate Netlist或新部署门控，不追加全量回归。详见[实现与验收交接](cpu/四行指令缓存实现与仿真交接_2026-10-11.md)。下方“无新增RTL/任务”和实板PASS是单行版历史状态。

## 最新实测：按地址失效双模式正式PASS，吞吐增加约2.35%/2.24%（2026-10-11）

用户新日志measure_20261011_121321_483已独立核验：performance_120 17.090684523秒、cycles1602251674、instret99571067、CPI16.091539、CRC d340；validation_120 17.901621685秒、1678277033、105902157、15.847430、CRC200d。两项超过10秒，完整软件身份/CRC/13计数/分类及AR+AW守恒、258响应/2唯一RUN/零重试/额外RX通过。新audit_formal120_20261011_a为COREMARK_FORMAL120_TWO_MODE_BOARD_LOGS_VERIFIED。

与112443同120次BIN相比，时间减少2.2929%/2.1880%，吞吐增加2.3467%/2.2370%；instret、branch事件、AW完全相同。IF等待减少7.4958%/7.1942%，AR各减少1288550/1282432；MEM和branch绝对周期仅微小变化，净收益集中IF等待。新占比IF29.23/29.28%、MEM26.12/25.09%、branch38.43/39.33%，branch含目标取指且占比受分母影响，不能据此宣称BTB预期收益。

compare_20261011_a/comparison.json为SELECTIVE_INVALIDATION_SAME_BIN_BOARD_COMPARISON_PASS，四份新旧日志、13计数CSV及新桥/本地位流副本已归档。两新日志本地位流SHA32b07eef…da9c5d与当前文件相同，新桥仍5fbf40c1版；未独立观察FPGA配置或审查完整新PDS实现。每模式每版1轮，无方差估计，不追加测试。本轮仅核验/分析，未改RTL/软件、未运行HDL/PDS/串口。

建议保留优化，下一步单独研究小容量多行指令缓存，仍保留CPU32-bit/单拍填充/同行写失效；先不同时改BTB/D-Cache/Burst/M。现有计数不能量化容量miss或精确命中率，收益需新测量。**当前没有新增RTL或待执行仿真任务**。详见[按地址失效实板性能分析](cpu/按地址失效实板性能分析_2026-10-11.md)。下方新版实板NOT_TESTED为上板前历史。

## 最新复核：任务007关键仿真PASS，交用户重建并实板同BIN比较（2026-10-11）

DeepSeek输出ds_invalidation_20261011_115005已由Codex离线独立核验：旧/新桥各54项定向PASS，ModelSim编译/仿真Errors0/Warnings0；ISA随机slti/lb（seed2026101107）分别CPU装载271/273 words至DDR用户口模型后tohost=1 PASS，cycles3535/3685。9份命令回执退出码0、实际源路径/参数正确，生成镜像与准备版本逐字节一致，71项输入及原三个历史manifest哈希不变。审查JSON为sim/inst_line_buffer/build/review_invalidation_20261011_a/review_result.json，INST_LINE_SELECTIVE_INVALIDATION_EVIDENCE_AUDIT_PASS；27份原始证据及71份待测输入副本已保存。

新桥SHA仍5fbf40c1…3c9e58a，按地址失效功能关键范围通过，抽测不等于全量ISA。**新版实板NOT_TESTED，DDR性能增益NOT_MEASURED**；功能模型5400→4670ns不作为CoreMark/实板提速结论。未追加全量测试；Codex本轮未改RTL/软件/测试判据，未运行HDL/PDS或开串口。DeepSeek报告未归档原始git status前后快照，输入未变结论限71项保护文件。

下一步用户在根目录RISCV.pds自行完整重建并下载新位流，保持93.75MHz、成功Loader ROM/RAM DAT；无需Generate Netlist或新部署门控。随后执行现有tools/uart_loader/candidates/perf_2b/run_measurements.ps1，固定performance_120/validation_120 BIN各1轮；与measure_20261011_112443_078旧版正式120次基线比较，保留CRC/13计数及至少10秒判据。用户提交新日志后Codex分析实际收益，再决定后续优化。见[正式计数与本轮复核](cpu/正式120次计数与按地址失效优化_2026-10-11.md)及[任务007执行报告](../DeepSeek/任务007_结果_ds_invalidation_20261011_115005.md)。下方HDL NOT_RUN是交接前历史状态。

## 最新步骤：正式120次实板双模式PASS，按地址失效改动交DeepSeek（2026-10-11）

用户新日志measure_20261011_112443_078已独立离线核验：performance_120 17.491745835秒、cycles1639851172、instret99571067、CPI16.469153、CRCfinal d340；validation_120 18.302074272秒、1715819463、105902157、16.201931、final200d。两项实际超过10秒，完整CRC/13计数/计时和分类守恒、258协议响应/2唯一RUN、零重试/额外RX、原固定120次BIN身份通过。audit_formal120_20261011_a/review_result.json为COREMARK_FORMAL120_TWO_MODE_BOARD_LOGS_VERIFIED，原日志已归档。只有各1轮；本地位流c661bcdf…fe0a50身份不等于独立观察FPGA配置。

据此选择小范围后续优化：只改myriscv/dual_sram_to_pango_ddr_bridge.v，将任意DDR写清指令缓冲改为接受的写与缓存完整16-byte行地址相等时清除；其他行写保留，同一行SB/SH/SW和零strobe仍失效。新桥SHA 5fbf40c186c1250151769de098e9a5f2a53d46d6810402b44db5f235c3c9e58a；从selected_addr起输出/FSM静态逐字相同。当前计数无法量化无关写失效频率，收益尚未测量。旧桥3509576版与旧位流保存在selective_invalidation_baseline_20261011_a，原软件/历史FAIL/三个旧manifest未改。

[任务007](../DeepSeek/任务007_指令缓冲按地址失效关键仿真.md)仅一个关键TB旧/新对照及随机2个ISA slti/lb（seed2026101107），输入71项SHA572a29aa…d13d91，源码/TB/runner已准备；**HDL NOT_RUN、新版实板NOT_TESTED**。Codex仅离线检查，未运行HDL/PDS/串口，当前停止交DeepSeek。复核其原始日志通过后用户自行重建/下载位流，再用现有run_measurements.ps1固定performance_120/validation_120各1轮，与本次正式基线比较。无需Generate Netlist、新部署门控或全量回归。详见[正式计数与本轮优化](cpu/正式120次计数与按地址失效优化_2026-10-11.md)。下方软件待测、旧全局失效版或旧门控要求均为历史步骤。

## 当前步骤：120次正式CoreMark软件已准备，用户运行双模式各1轮（2026-10-11）

用户要求CoreMark至少10秒，已构建measure_20261011_120的performance_120/validation_120，预计17.49/18.30秒，实际板级时间待确认。BIN15936/15944字节，与各自原60次BIN仅seed4_volatile数据60→120不同，所有指令/符号/段布局相同；旧成功软件和算法未改。主机原算法CRC参考先匹配60次，再取得120次final d340/200d。构建总收据FORMAL120_SOFTWARE_BUILD_AND_NATIVE_CRC_PASS；原计数窗口/13项UART读出不变。

run_measurements.ps1默认已切换两组120次，原命令可用；每组实测至少10秒且完整CRC/计数正确才PASS。两下载计划和8项关键离线检查通过，没有HDL/PDS/串口操作，无需重建位流。用户保留当前硬件并运行两项各1轮，日志自动新目录；120次实板NOT_TESTED。详见[120次正式运行准备](coremark/CoreMark计数测量120次正式运行准备_2026-10-11.md)。下方默认60次/仅性能对比是历史，原60次收益记录不变。

## 当前约定：精简验证，只留关键定向、两个ISA抽测及正式验收（2026-10-11）

用户要求减少仿真/测试。已更新AGENTS.md与DeepSeek模板：按改动保留关键用例，ISA默认随机抽2个并记录种子/名称，不默认完整ISA/IRQ/MMIO/Loader、两条物理DDR/九微基准或三轮重复。新失败只补相关定位/复验。当前已有实板结果不重跑，上一节分析提出的三轮追加建议取消。

run_measurements.ps1默认只跑performance_60/validation_60，显式-Applications才选其他项目，协议/CRC/13计数判据不变；当前60次不足10秒仍仅作同BIN性能对比，正式成绩时长要求保留。本轮未改RTL/BIN、未启动HDL/PDS/串口。详见[精简验证约定](project/精简验证约定_2026-10-11.md)；下面全量测试/多轮建议是历史。

## 最新结果：读缓冲六应用实板日志PASS，同BIN内核约2.03–2.05倍速度（2026-10-11）

用户运行新工具得到measure_20261011_110113_999，Codex离线独立核验六应用、564响应（291ACK/273READY）、6唯一RUN、零重试/额外RX、软件身份/CRC/13计数及守恒通过。audit_20261011_a/review_result.json为INST_LINE_BUFFER_SIX_APPLICATION_BOARD_LOGS_VERIFIED，新旧六份原始日志已逐字节归档，旧2B成功基线重新核验，无新门控要求。

performance_60 cycles1664861170→819951139、CPI33.440103→16.469392、秒17.758519147→8.746145483；validation_60为1758849025→857923609、33.216176→16.202040、18.761056267→9.151185163。instret49786365/52951580、branch事件与AW均不变。IF等待减少约75%，DDR AR减少约57%；branch恢复新占37.53/38.45%，MEM25.52/24.52%、IF30.88/30.86%，branch含目标取指不能全当BTB收益。

新60次均不足10秒：固定BIN正确性/性能比较PASS，**正式CoreMark成绩不成立**；各仅一轮，无多轮波动。六日志记录本地位流SHA c661bcdf…fe0a50，FPGA加载由用户执行，没有新PDS/网表审查。Codex本轮未改RTL/BIN、运行仿真/PDS或开串口。建议先补多轮稳定性，再独立研究按地址失效/多行I-Cache及分支目标等待。详见[首轮实板计数分析](cpu/指令读缓冲首轮实板性能计数分析_2026-10-11.md)。下方“优化版实板NOT_TESTED”为此前历史。

## 当前安排：只准备固定BIN下载测试工具，不要求网表导出或新门控（2026-10-11）

用户运行PS1出现编码解析错误后，仅将四处提示改成ASCII；Windows PowerShell 5.1.26100.8115实际语法检查和六项PlanOnly均通过，共564响应/6 RUN，未开串口。新离线日志measurement_windowsps51_20261011_a，原下载命令可直接重跑；Python工具/RTL/BIN未改。

用户明确简化后续流程。Codex新增tools/uart_loader/candidates/perf_2b/run_measurement.py及run_measurements.ps1，复用成功Loader传输和固定版本c BIN，默认COM11/115200；六项逐次KEY0、协议校验、唯一RUN、UART/CRC/13计数收集，失败停止并保留日志。新入口不要求Generate Netlist、不建立/检查新部署门控。旧run_board.py/旧门控/成功软件与实板档案不改。

15项离线检查、六计划564响应/6唯一RUN通过；未打开串口、运行HDL或PDS，本轮未改RTL。60次不足10秒允许正确固定BIN测量但formal_benchmark=false。用户生成并下载新位流后，直接运行新PowerShell入口，日志自动保存到sim/inst_line_buffer/board/measure_<时间戳>。优化版实板NOT_TESTED。详见[下载工具说明](cpu/读缓冲固定BIN下载测试工具_2026-10-11.md)。下方“Generate Netlist/新部署门控必需”已被本次用户安排替代，历史核验结果保留。

## 当前步骤：读缓冲仿真验收完成，交用户完整重建PDS（2026-10-11）

任务006五次Loader已独立核验PASS：hello关闭对照、hello/crc32/performance_1/validation_1启用；编译与仿真均Errors0/Warnings0，协议全部字节/唯一RUN、精确应用输出、独立IF命中/miss与AR/AW/R/W账本、末尾trap/IRQ/timer/guards实际通过。短CoreMark13计数守恒、CRC及窗口instret829739/882363正确；这是功能用户口模型，不是实板性能。原1423/71/270项清单均不变，桥SHA仍3509576c…c3dfe6d，历史FAIL保留。

离线审查JSON为sim/inst_line_buffer/build/review_checks_20261011_a/review_result.json，INST_LINE_BUFFER_LOADER_EVIDENCE_AUDIT_PASS；78份证据哈希与23份源码/工程副本保存。结合004/005同版本unit、支持ISA/并发、物理DDR/九窗口严格比较、IRQ/MMIO证据，本阶段所列仿真验收完成；已知FENCE.I/ma_data缺口仍保留。Codex未改RTL或运行HDL/PDS/串口。

**下一步用户打开根目录RISCV.pds（board_top）完整Compile→Synthesize→Map→PnR→Timing→Bitstream，并对同一最终结果Generate Netlist**；保持93.75MHz、成功Loader DAT和固定版本c BIN。之后Codex审查新产物、建立新门控，再由用户跑实板同BIN对比；优化版实板NOT_TESTED。旧位流/门控及无缓冲实板基线保留，旧PDS审查脚本绑定2B不能直接套用。详见[仿真验收与重建交接](cpu/指令读缓冲仿真验收与PDS重建交接_2026-10-11.md)。下面NOT_RUN/整体未验收是历史状态。

## 当前步骤：两处判据已适配，物理比较离线PASS，Loader交DeepSeek（2026-10-11）

用户授权后，Codex只新增sim/inst_line_buffer/{compare_micro.py,loader_traffic_check.svh,resume_checks.py,check_adapters.py}。原RTL/TB/runner/1423与71项清单、旧FAIL/门控/位流/成功BIN均未改。新比较器保留CYCLE接受边沿及原instret/CPI，用全退休流和PC标记间工作量严格比较；对原物理IP/PHY证据离线PASS，8处边界归属变化已解释。16项离线检查通过，包括10类坏轨迹拒绝、两种enable生成TB原检查逐字保留。

Loader新TB副本插入独立valid/tag/128-bit模型及单事务账本，分别守恒CPU请求/响应、命中/miss、DDR AR/AW/R/W，保留全部原CRC/协议/退休/trap/timer/guards；未编译或运行HDL，**Loader仍NOT_RUN，整体未验收**。追加checks_input_manifest.json270项，SHA a7828210…391e812；新桥SHA仍3509576c…c3dfe6d。[任务006](../DeepSeek/任务006_指令读缓冲判据适配后Loader续测.md)只跑hello关闭对照和四项启用Loader，失败立即停止，其余已有PASS不重复。当前交DeepSeek，不安排PDS/上板；详见[判据适配记录](cpu/指令读缓冲测试判据适配与交接_2026-10-11.md)。下面为前次审查及历史。

## 最新复核：读缓冲续测部分PASS，两处测试判据待适配（2026-10-11）

任务005已执行，Codex离线核验1423项原输入/71项续测输入零变化：40支持ISA+6并发PASS，2已知缺口真实基线复现；短CoreMark CRC及13项计数、两条物理DDR Tcl、32 CPU+2 UART IRQ及3 MMIO回归分别PASS。unit沿用004同RTL/TB的两模式各49项PASS。

九窗口完整Pango IP/PHY物理模型运行分别PASS，但原比较器因时间窗口instret变化FAIL。两版1199条实际退休PC/写回使能/目标寄存器序列相同，值差异仅18条计时器load；8处窗口标签边界变化解释4个窗口各+1退休计数。顺序ALU窗口cycles3694→1083、AR129→33为物理模型原始证据，不是实板/CoreMark正式增益。

四项Loader原测试均FAIL：旧“CPU请求=DDR事务”守恒断言不适用于读缓冲命中。协议字节和应用输出独立解析正确，但末尾trap/IRQ、guards、timer检查未执行到，不能改记PASS。**整体NOT_PASS**，设计RTL未再次修改；两处测试适配尚未实现/仿真，后续准备新入口再交DeepSeek，当前不安排用户PDS/上板。旧位流/部署门控及实板基线保留。详见[续测结果复核](cpu/指令读缓冲续测结果复核_2026-10-11.md)，审查JSON位于sim/inst_line_buffer/build/review_resume_20261011_a/review_result.json。下面各段为历史步骤。

## 最新复核：指令读缓冲unit PASS，快速回归需修正时间诊断后续测（2026-10-11）

DeepSeek任务004于10月10日执行：桥enable0/1各49项PASS，Errors:0/Warnings:0；fast仅11支持用例PASS，在FENCE.I已知缺口处停止。新旧失败均tohost00000539/failed_test668，仅cycles2106/2228不同，旧脚本整行相等断言中止。原1423项输入和52项fast保护输入不变。后续29支持用例/ma_data/6并发及CoreMark/物理DDR/IRQ/MMIO/Loader均NOT_RUN，整体未验证，没有DDR性能收益结论。

Codex只离线复核并新增resume_fast.py，不改RTL/TB/冻结旧脚本或原manifest；仅排除已知缺口末尾cycles，保持其他诊断严格相等并真实复现基线。已有日志解析及五类错误数据拒绝通过，新入口未运行仿真。续测附加manifest71项，原证据全部保留。[任务005](../DeepSeek/任务005_指令读缓冲快速回归续测.md)由DeepSeek重跑fast后继续任务004 B/C/D，unit因RTL/TB未变不重复。详见[复核记录](cpu/指令读缓冲首次仿真复核与续测_2026-10-11.md)。当前停下等待DeepSeek，不安排用户PDS/上板。

## 当前步骤：16-byte指令读缓冲已写入桥，停在仿真交DeepSeek（2026-10-10）

用户确认执行下一步，并要求遇仿真停下交DeepSeek。本轮只改myriscv/dual_sram_to_pango_ddr_bridge.v：单项16-byte指令读缓冲、下一拍命中响应、数据优先、所有被接受DDR写保守失效，原CPU32-bit接口/单拍Pango/单事务不改。CPU/SoC/MMIO/计数器/PDS/IP/成功软件及位流未改；未来旁路DMA写仍需独立一致性协议。

新增sim/inst_line_buffer定向TB、基线/候选runner及input_manifest.json，原桥基线选2B成功冻结源码；[DeepSeek任务004](../DeepSeek/任务004_16字节指令读缓冲仿真.md)含分阶段直接命令、输入SHA、物理DDR性能对比及必要CPU/DDR/IRQ/MMIO/Loader回归。**全部仿真NOT_RUN，设计NOT_TESTED**，Codex未启动编译/仿真/PDS/串口。任务文件不自动调用DeepSeek，等其执行结果后Codex复核，当前停下不继续实施。

旧2B位流/门控/六应用实板基线保留；源桥变化后旧门控应拒绝当前工作树，不重写哈希跳过保护。先交DeepSeek，不要求用户现在重建位流。行为、风险与未覆盖见[实现和交接记录](cpu/16字节指令读缓冲实现与仿真交接_2026-10-10.md)；下面2B PASS是上一版硬件基线，不是缓冲候选PASS。

## 最新结果：2B六应用实板计数基线PASS（2026-10-10）

用户23:06补跑performance_60成功，原始日志performance_60_retry1.json的CRCfinal a14c、完整UART计数尾及计时守恒独立核验通过。选取六份成功应用后，audit_retry1_20261010_a/independent_result.json为PERF2B_SIX_APPLICATION_ACTUAL_BOARD_VERIFIED，6/6应用、564协议响应（291ACK/273READY）、6唯一RUN、零传输重试/额外RX，主门控272输入/820证据/272冻结副本一致。六份成功日志/CSV/门控副本已归档；原人工复位中止及5/6记录保留，门控创建时NOT_TESTED不改写。

正式performance/validation 60次时间17.758519147/18.761056267秒，cycles1,664,861,170/1,758,849,025，instret49,786,365/52,951,580，CPI33.440103/33.216176；IF等待60.1906%/60.8206%，MEM17.8879%/17.0153%，分支恢复18.9310%/19.1535%。全部13计数和CRC通过，代码/数据走实际DDR3。同固定版本c BIN、93.75MHz；尚无多轮波动或优化提速结论。

下一阶段建议独立评估16-byte指令读缓冲，保留CPU32-bit接口，并覆盖写入失效、背压、错误及复位/冲刷；不同时修改Cache/M/Burst/BTB。用户本轮只确认补跑成功，Codex仅审查/归档，未实现优化、运行PDS或操作串口。详见[双模式完整统计及证据](cpu/CPU计数器2B首轮实板统计与补测_2026-10-10.md)。DeepSeek任务003已有同版本Codex核验，不需重复；下方“待补测/NOT_TESTED”为历史。

## 最新结果：2B首轮实板5/6通过，performance 60次待补测（2026-10-10）

用户提交六份实际UART日志，独立核验全部564协议响应（291ACK/273READY）、6次唯一RUN及主门控272输入/820证据/272冻结副本一致。Hello、CRC32、两组短CoreMark和validation 60次应用PASS；performance 60次下载/VERIFY/RUN正常但应用输出为空，用户确认等待中按了复位，记人工复位中止，整组仍INCOMPLETE，不作RTL故障或正式跑分结果。原六日志及五项成功结果已冻结，门控创建时NOT_TESTED保留原哈希。

正式validation实测cycles1,758,849,025、instret52,951,580、CPI33.216176、18.761056267秒，IF/MEM/branch分类60.8206%/17.0153%/19.1535%，CRCfinal6770及13计数守恒通过。优先研究取指路径；branch恢复包含目标取指等待，不能全当BTB收益。本轮没有优化RTL、PDS运行或串口操作。

用户只需按[首轮统计中的补测命令](cpu/CPU计数器2B首轮实板统计与补测_2026-10-10.md)运行performance_60，输出新文件performance_60_retry1.json，运行中不要复位。原五项及位流/BIN无需重跑重建。新只读入口sim/cpu_performance_2b/check_board.py保存汇总/CSV/原始日志副本；首轮audit_20261010_b状态PERF2B_BOARD_AUDIT_INCOMPLETE。补测后可交[DeepSeek任务003](../DeepSeek/任务003_2B实板日志离线复核.md)复核，再完成双模式基线并决定独立16-byte I读缓冲；DeepSeek本轮NOT_RUN。下方“实板仍NOT_TESTED”为上板前历史状态。

## 最新结果：2B主工程实现网表补审通过，已绑定新上板门控（2026-10-10）

用户22:20完成Generate Netlist，当前VM含计数器，8个实现存储实例全部INIT与当前综合/成功Loader DAT匹配；main_pds_review_20261010_d为PERF2B_MAIN_PDS_ARTIFACT_AUDIT_PASS。位流仍为21:13根目录board_top.sbit，SHA256 `4231dcd62362f567b7ce47553c472832604fd78bed99ece6913004f24614fe76`，93.75MHz setup +0.526ns，LUT6910/FF7070/DRM8。既有RTL/仿真输入未变，不重跑整套仿真。

新门控main_pds_board_20261010_a/deployment_gate.json为PERF2B_MAIN_PRE_BOARD_AUDIT_PASS，冻结272项输入/820项证据及272份输入副本。perf_2b/run_board.py默认已改绑新门控，固定测量BIN仍为版本c；六份离线计划564响应/6次RUN及四类错误门控拒绝通过，129响应计数尾mock与四类错误数据拒绝通过。旧门控/成功位流/档案保留；Codex未启动PDS或打开串口，实板仍NOT_TESTED。

用户下一步下载根目录新位流，按[上板工具说明](../tools/uart_loader/candidates/perf_2b/README.md)逐条执行Hello/CRC32/两组短CoreMark/两组正式60次，新日志在sim/cpu_performance_2b/board/main_pds_first。完整结果见[审查记录](board/CPU计数器2B主工程新位流审查_2026-10-10.md)。下方“缺导出/未绑定”仅历史状态，现已解决。

## 最新审查：2B主工程21:13新位流，待补实现网表导出（2026-10-10）

用户生成根目录位流，SHA256 `4231dcd62362f567b7ce47553c472832604fd78bed99ece6913004f24614fe76`。现有93.75MHz约束通过，slow setup +0.526ns，slow/fast hold +0.137/+0.103ns；LUT6910/FF7070/DRM8，seed5。主RTL和六组既有回归输入一致，8192个生成初始化字及8个综合网表存储实例与成功Loader DAT匹配，当前PNR连接包含13计数银行且与已验证候选逐字节相同；六应用固定软件身份通过。

**审查为PERF2B_MAIN_PDS_AUDIT_INCOMPLETE**：generate_netlist/board_top_sim.v和SDF仍为10月3日旧导出，VM不含计数器。用户只需在根目录RISCV.pds对当前已布线结果执行Generate Netlist，不必重新综合布线/生成位流；Codex核验新实现INIT后才创建新门控和更新工具绑定。原门控/工具保持历史身份，实板仍NOT_TESTED；本轮未运行PDS、仿真或串口。详见[审查报告](board/CPU计数器2B主工程新位流审查_2026-10-10.md)，重复离线核验入口可交[DeepSeek任务002](../DeepSeek/任务002_新主位流离线审查.md)。

## 协作入口：DeepSeek 重复仿真任务（2026-10-10）

用户要求建立 `DeepSeek/`，今后将重复仿真命令写成任务文件交给DeepSeek执行并整理日志。入口见[DeepSeek README](../DeepSeek/README.md)，预置[任务001](../DeepSeek/任务001_2B主RTL仿真回归.md)，本轮只创建文件，NOT_RUN；当前已通过的基线不因建目录而重复跑。Codex负责测试范围、设计修改和原始结果复核，用户继续负责PDS/实板。新任务和结果放DeepSeek，TB/模型/完整运行日志仍放sim；本目录不会自动调用外部模型。目的、分工与未覆盖见[记录](project/DeepSeek仿真任务交接入口_2026-10-10.md)。

## GitHub 协作入口：摄像头与 CNN（2026-10-10）

主设计直接维护在 `myriscv/`，摄像头/CNN 同学先读 [开发交接](project/摄像头与CNN开发交接_2026-10-10.md)。当前没有摄像头、CNN 或 DMA RTL；其中新外设地址和接入步骤是建议，尚未实现。共享 DDR 用户口是 Pango AXI-like，不能按标准 AXI4 直接挂新主机；DDR 仲裁、跨时钟与完成可见性须单独验证。

本次整理发布当前 RTL/PDS/IP 配置、Loader 必要初始化镜像、软件与仿真入口、固定测量 BIN 和精选结果。完整本地冻结档案、位流、编译工具链及大部分运行日志不上传；历史文档里的档案路径不代表新克隆已包含对应文件。新克隆运行板级下载前必须由用户生成并审查当前主工程位流、建立对应的新门控，不能沿用历史成功位流身份。2B 主 RTL 仿真已通过，当前主设计计数器实板仍 **NOT_TESTED**；本次发布不运行 PDS，也没有新增 RTL 功能。发布范围和复现入口见 [发布记录](project/GitHub协作发布_2026-10-10.md)。

## 最新整理：2B 重复设计与缓存已清理（2026-10-10）

按用户要求删除已迁入主设计的myriscv/candidates/perf_2b、未使用独立PDS工程pds_user_20261010_a、早期软件a/b、重复计数模板、旧生成/审查脚本、旧独立重建步骤及相关仿真缓存。主设计、最终测量BIN c、成功位流/快照、日志/统计与必要实现报告保留。run.py/regress.py已直接读取myriscv，清理后MMIO oracle和下载读出离线mock PASS；冻结246副本/339证据校验保留。详见[清理记录](cpu/CPU计数器2B冗余文件清理_2026-10-10.md)。当前入口为根目录RISCV.pds，PDS由用户执行；下方独立工程/目录保留等是清理前历史。

## 最新入口：2B 计数器直接并入 myriscv 主 RTL（2026-10-10）

用户要求直接修改myriscv已有.v，不再新增设计候选文件夹。已将已验证2B的CPU只读观察、SoC连线和MMIO计数器逐字节并入 `myriscv/mycpu_sync.v`、`soc_top.v`、`simple_mmio.v`。根目录RISCV.pds已经使用这些路径，无需切换工程；IP/初始化/成功BIN/位流不改，本轮不运行PDS。今后主设计直接修改，历史candidate目录保留证据。

主路径回归入口 `sim/cpu_performance_2b/main_rtl.py`，直接编译主RTL，日志为build/main_*_20261010_a。六组回归均完成：MMIO窗口/计数、两条完整DDR物理定向、40个RV32I支持用例+6并发背压、32CPU+2UART IRQ、三条MMIO/UART/access-fault、两组短CoreMark CRC与13项计数。FENCE.I/ma_data原有缺口用迁入前快照独立复现；短CoreMark不是正式跑分。汇总main_integration_20261010_a.json为PERF2B_MAIN_RTL_INTEGRATION_REGRESSION_PASS，两组13项统计与上一候选相同。结果与未覆盖范围见[主RTL集成记录](cpu/CPU性能计数器2B并入主RTL_2026-10-10.md)。用户现在应打开根目录RISCV.pds完整重建，包含实现网表导出；完成后Codex审查新位流并绑定新门控。原门控因主RTL哈希改变将拒绝部署，这是正确行为；旧246项冻结副本/339项证据及成功档案保留。下方“主RTL未改/使用pds_user独立工程”为历史状态，当前计数器实板仍NOT_TESTED。

## 最新准备：用户重建 2B 候选工程（2026-10-10）

当时用户表示自行生成比特流，曾准备 `sim/cpu_performance_2b/build/pds_user_20261010_a/combined.pds`，顶层board_top，状态PERF2B_USER_PDS_INPUT_PREPARATION_PASS；未运行PDS。随后按用户要求将RTL并入主文件，该独立工程及重复步骤已清理，最新入口见[主RTL集成](cpu/CPU性能计数器2B并入主RTL_2026-10-10.md)。用户完成后Codex核对新产物并绑定新的门控/工具，不能沿用旧位流哈希。

## 最新分工：PDS 实现交给用户（2026-10-10）

用户明确要求后续 PDS 编译、综合、布局布线相关步骤交由用户执行。Codex 负责代码与仿真、准备候选工程/步骤，并审查用户生成的时序、资源、初始化、源文件身份和位流；默认不再启动 PDS 实现或生成比特流。此长期约定已写入 AGENTS.md。已生成的 2B 候选与证据保留，不因本次分工调整重新构建；下面记录为既有结果，实板仍 NOT_TESTED。本次只更新分工文档，没有运行 PDS 或修改 RTL。

## 最新结果：CPU 性能计数器 2B MMIO 隔离候选（2026-10-10）

用户授权下一步并选择独立测量 BIN 通过 UART 打印。计数器用 MMIO 实现，候选为 `myriscv/candidates/perf_2b/` 的 CPU/SoC/MMIO 三文件：只读事件输出、13项64-bit冻结计数、ARM/CANCEL/手动起停及PC过滤，旧总线握手和寄存器保持原语义。观察增加一级寄存以通过时序，`[S,T)` 口径与2A observer逐项一致。尚无Cache/M/Burst/BTB或提速结论。

最终MMIO定向、两组短CoreMark CRC/UART读出、两条DDR物理定向、RV32I/并发背压、CPU/UART IRQ、MMIO/access-fault回归通过。完整Pango IP/PHY/物理DDR九微基准1199退休核验通过，首硬件窗口13项与observer相等，九窗口cycles/instret/DDR命令与2A direct基线相等。FENCE.I/ma_data原RTL同失败的已知缺口保留；60次只完成下载/校验/启动仿真，不算完整CRC或实板PASS。

隔离PDS最终 `sim/cpu_performance_2b/build/pds_20261010_b` 四个种子满足现有93.75MHz约束，best seed5 setup +0.526ns；LUT6910/FF7070/DRM8，主工程5714/6052/8。候选位流SHA256 `dc5121b8857a08c053698def358cc07f3be083252cb0b7274f27e6277b5dbb46`。启动脚本两条探测诊断保留，成功加载后七阶段全部完成且无E:，详情见报告；首个直接组合草案时序失败，保留且禁止部署。

新 `sim/cpu_performance_2b/build/deployment_gate.json` 为PERF2B_PRE_BOARD_AUDIT_PASS，246项输入/副本、339项证据冻结，8192初始化字及实现网表8个存储实例核验；52项主RTL/PDS/IP/原成功BIN/位流/CoreMark算法保护输入不变。六份离线计划564响应、6次RUN通过，Codex未打开串口。新测量BIN在 `tests/cpu_performance_2b/build/measure_20261010_c`，后续优化固定同一批BIN；原成功BIN保留。

**实板仍NOT_TESTED。** 用户下载候选位流，再按[六应用操作步骤](../tools/uart_loader/candidates/perf_2b/README.md)执行Hello/CRC32/两组短CRC/两组正式60次；每轮KEY0等待DDR后回车，正式模式绑定同候选短测量BIN的实板CRC日志。工具等待PERF2B_DONE后独立核验协议与统计。完成实板基线后再独立开发16-byte I读缓冲，不与本轮计数器同时优化。完整设计、复现、证据和限制见[2B计数器记录](cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)。下方2A“无硬件计数器/等待确认”为历史状态。

## 最新结果：CPU 性能测量 2A 首批物理基线（2026-10-10）

用户确认执行阶段1方案后，新增 `tests/cpu_performance/` 和 `sim/cpu_performance/`，主 RTL/PDS/IP/成功 BIN/位流不变。仿真observer的窗口、互斥分类、退休/MRET、请求响应守恒、turnover、64-bit carry及32-bit CYCLE wrap通过，三类故意错误被拒绝。九组微基准在当前Pango IP/PHY/物理DDR模型完整PASS，1199条DDR退休逐条解释器核验，Errors:0、无物理ERROR。52项关键保护输入前后SHA256一致。

CPU copy-loader物理基线中，顺序ALU cycles3694/instret129/CPI28.636，IF等待96.51%，129笔DDR读命令，IF响应中位数26周期；顺序64-word load cycles5692、MEM分类63.55%。这些是指定小微基准的物理模型结果，不是实板CoreMark瓶颈份额。现有两组短CoreMark原BIN完整功能CRC通过，动态退休中软件乘法占52.116%/54.998%；用户口模型时间不作真实DDR性能证据，不能直接推算60次CPI或提速。

仿真专用128-bit Pango入口完成358拍物理写入/回读后释放CPU的第二路径也九窗口PASS，1199条退休及各窗口DDR命令数与CPU copy-loader一致，Errors:0/无物理ERROR。短窗口可因背景等待相位出现211-cycle差异，不算硬件提速；默认入口用此方式，生产UART Loader和位流不变。

结果、原始CSV/日志、复现及未覆盖范围见 [2A测量记录](cpu/CPU_DDR性能测量2A与首批物理基线_2026-10-10.md)，入口见 [仿真说明](../sim/cpu_performance/README.md)。本轮没有硬件计数器、cache/M/BTB或新位流；下一步待确认2B板级计数读出及独立16-byte I读缓冲候选。下方“CPU性能分析尚未实施”等描述为历史状态；最新主位流六轮实板和正式60次基线仍保留。

## 最新软件能力：通用新 C 程序入口（2026-10-10）

新增 `tests/c_app/`，提供 `run_app.py --source ... --expect ...`：编译 RV32I ELF/BIN、审查地址/大小/ISA、真实 CPU 完整下载执行仿真、独立应用门控，再由用户确认 KEY0/DDR 就绪后自动 COM11 LOAD/VERIFY/RUN 与输出验证。`--prepare` 不开串口，`--deploy` 复用已准备结果，`--verify-log` 离线复核日志；多 C 文件及精确输出文件可用。原 Loader/BSP/主 IP/位流/旧门控及成功镜像保持不变。

示例与另一份多文件/软件除法程序通过完整仿真；协议、输出及编译/ISA/布局错误检查通过。新入口实板仍 NOT_TESTED，上板/KEY0/串口由用户执行；下方“通用入口未实现”是历史状态。操作见 [c_app README](../tests/c_app/README.md)，目的、命令、证据和限制见 [实现记录](software/通用C程序自动构建下载验证_2026-10-10.md)。CPU 性能分析尚未实施，无 RTL 优化或提速结论。

## 最新结果：用户重建主工程位流六轮实板 PASS（2026-10-10）

新位流 `generate_bitstream/board_top.sbit`（SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf）已由用户上板，六份原始JSON独立核验540/540响应（279ACK/261READY）、6次唯一成功RUN、零CRC错误/重试/额外RX。Hello/CRC32及两组短CoreMark CRC正确，新位流两组正式60次无ERROR且CRC正确，17.750024053/18.752304203秒。主IP当前verify_run_hello Loader DAT，旧“load_stage10配置”仅历史。

`sim/bsp_workflow/rebuilt_20261010/board/independent_result.json` 为REBUILT_SIX_APPLICATION_ACTUAL_BOARD_VERIFIED，submission_result.json为REBUILT_SIX_APPLICATION_ACTUAL_BOARD_ARCHIVE_PASS，549项成功快照在first_success/。415项冻结输入/副本、原116项证据及旧518项十轮快照匹配。新门控NOT_TESTED保留生成时历史，最新看实板报告。新工具绑定此次主工程位流，原BSP工具仍绑定旧隔离位流；不要混用正式CRC日志或覆盖成功文件。

本轮重建复验已完成，不再等待用户测试。Codex未操作板子或串口，CPU/Loader/BSP未改；新旧CoreMark时间基本一致，没有性能优化结论。下一任务继续CPU瓶颈统计及性能优化。见[新位流实板验收](board/主工程新位流六轮实板验收_2026-10-10.md)，下方准备记录仅历史。

## 最新准备：主工程新位流可进行六轮实板复验（2026-10-10）

用户新位流SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf已完成初始化/综合/时序离线审查：原CPU/Loader/BSP仿真输入与证据不变，主IP生成初始化及本次综合网表8个存储实例与成功版本匹配，93.75MHz现有约束通过。generate_netlist导出仍为10月3日旧文件，已排除；未宣称本次完整实现仿真网表初始化核验。新门控REBUILT_LOADER_PRE_BOARD_AUDIT_PASS冻结415项输入/副本，8项PC离线检查PASS，实板NOT_TESTED。

用户先下载 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`，关闭串口助手，再执行 `& C:/python/python.exe D:/riscv/RISCV/tools/uart_loader/candidates/rebuilt_20261010/run_board.py`。六轮Hello/CRC32/两组短CoreMark/两组正式CoreMark，各提示KEY0等待DDR后回车；日志在sim/bsp_workflow/rebuilt_20261010/board/first。新工具绑定新位流，不套用旧位流CRC日志或门控；原工具、十轮成功档案均保留，Codex未操作板子。完成后独立核验实际日志，再归档新位流。详见[复验准备](board/主工程新位流实板复验准备_2026-10-10.md)。CPU性能优化方向保持，尚未改CPU RTL。

## 最新配置观察：用户重新生成主工程位流（2026-10-10 14:34）

新文件 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`，3791112字节，SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf；生成日志记录完成。当前两主IP INIT_FILE已由用户切到verify_run_hello/build同一对loader_rom.dat/loader_ram.dat，下方“主IP仍为load_stage10”保留重建前历史。原十轮成功隔离位流未覆盖，SHA仍31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0。新位流尚未完成独立初始化/网表/时序审查或实板验收，现有PC工具仍绑定原成功版本。见[新位流定位记录](board/主工程新位流定位记录_2026-10-10.md)。本轮只定位与核对配置，未修改RTL或操作板子。

## 当前任务：转入 CPU 性能优化（2026-10-10）

用户要求更新文档，下一项工作为CPU性能优化。本轮仅整理交接，不改RTL、不实现通用软件入口、不重新构建或上板。统一BSP及十轮实板任务已经完成，成功镜像与518项快照保留；下方历史待验描述不再是当前任务。

优化起点见[CPU性能优化约定](CPU性能优化起点与验收约定_2026-10-10.md)：固定93.75MHz及本次两份成功CoreMark BIN（performance_60 17.749998571秒、validation_60 18.752320843秒），先统计CoreMark计时区间的退休、CPI、取指/数据等待、分支和流水线停顿，再依据证据选择优化点。目前尚无瓶颈分解或优化RTL。CPU变更须新隔离PDS/位流、回归和新门控，不能让旧哈希门控认可修改后的硬件；主IP仍为load_stage10，优化候选明确采用成功verify_run_hello Loader DAT/IP。

软件能力边界：build.py/run.py只接入已验收的Hello、CRC32和CoreMark；任意新main.c的一键构建/下载/验证尚未实现，讨论过的run_app.py仅为示例。新程序需注册构建与预期输出，--tag只隔离构建不自动接入。此工具扩展暂留后续，不阻塞现有CoreMark性能分析。全部实板操作继续由用户负责。

## 最新结果：统一 BSP 与十轮复位下载实板 PASS（2026-10-10）

用户完成同一Hello成功Loader位流的十轮KEY0/COM11验收，Codex直接独立核验十份原始JSON：834/834响应（432ACK/402READY）、10次唯一成功RUN，零CRC错误、零重试/额外RX；每轮SEQ1 PING空状态、完整LOAD/VERIFY/RUN及程序输出通过。Hello和独立CRC32各两轮、CoreMark短迭代四轮及正式60次两轮均通过同一BSP构建/审查/下载流程；新BSP正式performance/validation分别17.749998571/18.752320843秒，所有算法CRC正确且无ERROR。

`sim/bsp_workflow/board/first_independent_result.json` 为UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_VERIFIED；`first_submission_result.json` 为UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_ARCHIVE_PASS，518项完整成功快照在 `first_success/`。380项冻结输入/116项证据/380项源副本、旧Hello170项及18项PDS源/副本、旧应用279项快照均匹配。历史门控NOT_TESTED保留生成时状态，当前结论看新增报告。

统一BSP、统一软件流程及十轮连续复位下载任务已完成；精简第③关剩余十轮已补齐。未改CPU/DDR桥/ROM Loader、未重建成功软件或位流；Codex未打开串口或操作板子。KEY0/JTAG由用户确认，日志独立证明十轮Loader空状态重新启动；UART IRQ仍只仿真PASS。详见[十轮实板验收](software/统一BSP与十轮复位下载实板验收_2026-10-10.md)。后续使用已验收软件和成功位流；新程序单独隔离构建验证，不重复本次开发与上板。

## 最新准备：统一 BSP 与十轮复位下载（2026-10-10）

用户已将统一软件流程及至少10轮KEY0复位验收纳入当前任务。隔离目录 `tests/bsp_workflow/` 已完成 startup/linker、UART轻量printf、cycle延时、trap/IRQ和CRC32驱动，以及统一 build.py/run.py。Hello、CRC32和两种CoreMark配置通过同一构建、镜像审查、LOAD/VERIFY/RUN和严格结果核验流程；未修改CPU、DDR桥、ROM Loader或成功位流。

八组真实CPU仿真及54项PC离线检查PASS；Hello原速115200真实引脚仿真通过，另含完整短迭代CoreMark CRC、UART RX IRQ/ECALL上下文和cycle回绕。新60次BIN仅完成装载/校验/启动仿真，完整正式算法与时长待本轮实板，不能沿用旧不同BIN的PASS。门控 `sim/bsp_workflow/build/deployment_gate.json` 为UNIFIED_BSP_SIM_PASS，冻结380项输入/116项证据/380项源副本；六个可部署manifest，IRQ仅仿真。最终 `pre_board_audit.json` 核验冻结文件、六份离线计划及旧170/279项成功快照PASS。

**本轮十轮实板仍NOT_TESTED。** 用户保持此前Hello成功Loader位流（SHA256 31386f785e59f3de2a3499202fb404fc39dde6bbc4a2e5ecb906d754acc02eb0），关闭串口助手，在PowerShell执行 `& C:/python/python.exe D:/riscv/RISCV/tests/bsp_workflow/run.py --acceptance`。每轮按KEY0、释放并等DDR初始化完成后回车；脚本连续安排Hello/CRC32/短CoreMark/正式CoreMark共10轮，正式模式绑定本批第7/8轮CRC日志。结果保存 `sim/bsp_workflow/board/first/`，用户完成后Codex直接独立核验及归档，再更新实板PASS。Codex未打开COM11或操作板子；旧成功镜像与失败记录保留。详见[准备与步骤](software/统一BSP与十轮复位下载验收准备_2026-10-10.md)。下方历史“额外10轮不在本次范围”仅指2026-10-09任务。

## 最新结果：同位流第二程序与 CoreMark 实板 PASS（2026-10-09）

用户完成五次COM11下载，Codex独立核验五份原始JSON：第二程序精确输出SECOND_PROGRAM_PASS sum=11440；CoreMark两组1次算法CRC正确，两组60次正式运行CRC正确且无ERROR，分别17.756533472秒和18.758810933秒。437/437响应（226ACK/211READY）、5次唯一成功RUN，零响应CRC错误、零重试/额外RX。均沿用此前Hello成功的同一Loader位流文件身份，无Loader/IP/位流重建。

独立结果 `sim/uart_loader/board/applications_stage3_independent_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_PASS；归档收据 `applications_stage3_submission_result.json` 为SECOND_PROGRAM_AND_COREMARK_ACTUAL_BOARD_ARCHIVE_PASS。279项完整成功快照在 `sim/uart_loader/board/applications_stage3_success/`；196项输入/74项证据/196项源副本、旧Hello170项成功快照及PDS副本均匹配。门控生成时NOT_TESTED保留历史，当前结果看新增板级报告。

本次用户指定“第二程序/CoreMark先CRC后正式”两步已完成。额外10轮复位不在本次任务范围，尚未执行，不将原更宽的第③关所有检查记为PASS。Codex未打开串口或操作板子；未独立观察JTAG/KEY0。详见[实板验收](uart_loader/UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。

## 历史准备：同位流第二程序与 CoreMark（2026-10-09）

用户本次选择换第二个C程序，以及CoreMark先验算法CRC再正式运行。隔离开发和集中仿真全部完成：587-byte第二程序原速115200引脚收发/输出PASS，两组CoreMark 1次完整算法CRC PASS，两组60次新UART装载/VERIFY/RUN/启动PASS；60次完整算法复用原逐字节相同BIN的既有Full Boot证据。本次UART实板仍NOT_TESTED，额外10轮复位不在此次任务范围内。

门控 `sim/uart_loader/build/applications_stage3/deployment_gate.json` 为SAME_LOADER_APPLICATIONS_SIM_PASS，冻结196项输入/74项证据/196项源副本，35项PC离线检查PASS。沿用此前Hello成功的同一Loader位流，无Loader/IP/PDS重建；成功170项快照及旧76项输入/71项证据核对一致。失败日志保留，不修改成功镜像。上板/KEY0/COM11由用户操作，Codex未打开串口或下载位流。

下一步用户执行 `D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1`，按提示五次KEY0：second、performance_1、validation_1、performance_60、validation_60。正式模式必须先提供对应短迭代实际CRC日志；结果在 `sim/uart_loader/board/applications_stage3_first/`。完成后离线核验/归档，再记录实板结果。详见[准备记录](uart_loader/UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。

## 最新结果：VERIFY / RUN / DDR / Hello 合并实板 PASS（2026-10-09）

用户完成隔离候选下载和COM11测试，Codex独立核验实际原始JSON：157/157响应（83ACK/49READY/25预期NACK）、4次正式VERIFY的367-byte DDR CRC32均5E142E06，最终SEQ106唯一成功RUN后精确收到13-byte `Hello World\r\n`，零响应CRC错误、零重试/额外RX，用时4.301259秒。精简计划第②关完成，已验收UART下载→正式VERIFY→RUN→DDR应用Hello链路。

汇总 `sim/uart_loader/board/verify_run_hello_board_result.json` 为COMBINED_ACTUAL_BOARD_VERIFIED；归档收据 `verify_run_hello_submission_result.json` 为COMBINED_ACTUAL_BOARD_ARCHIVE_PASS。170项完整成功快照保存在 `sim/uart_loader/board/verify_run_hello_success/`，冻结76项输入/71项证据/76源副本、阶段⑦至⑩成功档案及主PDS/IP/旧成功位流均匹配。原仿真门控内NOT_TESTED是历史生成状态，当前结论看新增板级汇总。详见[实板验收](uart_loader/UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md)。

主工程配置继续保留阶段⑩；用户报告本次下载隔离verify_run_hello位流，PC日志中的位流文件哈希与已审计快照一致。未独立观察下载/KEY0或读回FPGA配置；本轮没有物理DDR损坏或UART线级故障注入。上板、供电、复位和串口由用户负责，Codex只离线核验和归档。本轮不重建镜像、不重复仿真。下一步第③关同位流至少10轮复位、第二BIN和CoreMark；本轮尚未启动。

## 历史准备：VERIFY / RUN / DDR / Hello 合并仿真 PASS（2026-10-09）

精简计划第②关已在新隔离候选 `verify_run_hello` 完成，Loader 与 367-byte Hello 各构建一次。五组真实 CPU 仿真全部 PASS：正向11、错误矩阵157、原速 UART9、UART事件失效恢复25、控制截断/CRC34响应；14项 PC 离线检查 PASS。门控 `COMBINED_SIM_PASS` 冻结76项输入、71项证据和76项源副本，实板仍 NOT_TESTED。

正式 VERIFY 重读整个 DDR 文件 CRC，RUN 要求 VERIFIED 且再次重读，全部 ACK 发完才跳转。仿真已证明真实 DDR 指令退休、应用 gp/sp、非空 data/BSS 清零及精确 Hello。主 PDS/IP/成功位流保持阶段⑩配置，阶段⑦至⑩成功档案保留；新候选 PDS/IP/位流在 `sim/uart_loader/build/verify_run_hello/pds_candidate/`，不重建成功 DAT。

用户最新要求：上板、供电、JTAG下载、KEY0复位和COM11测试由用户操作；Codex提供步骤并离线核验日志，不再操作下载器或串口。隔离位流已生成并审计PASS，最终seed4满足93.75 MHz已有时序约束，8192个初始化字和8个实现网表存储实例均与冻结DAT一致；收据为 `sim/uart_loader/build/verify_run_hello/pds_build_result.json`。JTAG两次扫描仅识别USB Cable II、未发现FPGA，等待现场通电/接好JTAG；COM11仅枚举，尚未下载或打开串口，实板未完成。详情及后续入口见[合并验收记录](uart_loader/UART_Loader_VERIFY_RUN_DDR_Hello合并验收_2026-10-09.md)。后续继续现有候选和冻结镜像，不重新开始开发。

## 历史结果：阶段⑩真实程序LOAD两轮实板PASS（2026-10-09）

用户完成两轮COM11测试；Codex独立核验工程内原始日志，每轮8响应、383-byte真实BIN的DDR读回CRC32均B2E24920，零CRC/UART错误、零重试/额外RX。汇总STAGE10_TWO_ROUND_BOARD_PASS / PASS_LOAD_ONLY_UNVERIFIED，第①关完成。正式VERIFY/RUN和执行尚未实现。

两份固定原始日志和当前PDS/IP/sbit共10文件配置已归档；79项冻结输入、110项证据及79项源副本相同，阶段⑦/⑧/⑨成功档案保留。历史STAGE10_SIM_PASS门控内NOT_TESTED保持生成时状态，当前实板结论看新增汇总。详见[两轮实板验收](uart_loader/UART_Loader真实程序LOAD两轮实板验收_2026-10-09.md)。

当前主IP指向load_stage10成功DAT；下一开发步骤为精简计划第②关：新隔离候选一起实现正式VERIFY、RUN、DDR执行及Hello。上板/复位/供电/COM11全部由用户操作，Codex负责开发、仿真与离线核验。本次已完成板级核验归档，尚未开发第②关功能，不重建成功DAT/BIN。

更新日期：2026-10-09（Asia/Shanghai）。工程根目录：`D:/riscv/RISCV`。

## 精简计划制定时记录：三个关口（2026-10-09）

用户要求精简阶段，剩余原⑩至⑮合并为：①真实程序下载（原⑩，两轮实板PASS）；②校验并运行Hello（原⑪至⑬及⑭基本Hello）；③同位流换程序与CoreMark（原⑭至少10轮复位/第二BIN及⑮）。第②关通过即可UART下载并运行DDR程序。关键检查保留，按LOAD→VERIFY→RUN顺序验收，原编号仅作为检查项和历史证据索引。详细通过条件见[剩余阶段精简计划](uart_loader/UART_Loader剩余阶段精简计划_2026-10-09.md)。

第①关两轮实板验收已完成；下一步一起开发第②关隔离候选。上板、复位、供电和COM11全部由用户操作，Codex不打开串口。此次只调整文档，不改冻结代码或成功镜像；下方历史“下一阶段”按本文合并计划解释。

计划精简时的工作区观察（历史）：两主IP INIT_FILE已指向load_stage10同一对DAT，board_top.sbit修改时间2026-10-09 16:37:49；未观察实际下载，工程内阶段⑩两轮日志和汇总均不存在，实板仍待验。冻结输入79项/证据110项/源副本79项哈希匹配；先前439项保护文件中22项PDS/IP/位流产物已有变化，本次未写这些文件，详见精简计划记录。

## 换对话快速入口（2026-10-08）

先读 [UART Loader 换对话交接](uart_loader/UART_Loader换对话交接_2026-10-08.md)，包含地址、现行协议、成功镜像哈希、证据、构建注意事项和可复制的新对话指令。最新实板结论为阶段⑩真实程序LOAD两轮PASS；阶段⑨随机二进制/DDR CRC两轮各1000镜像PASS保留；阶段⑦、⑧成功证据均保留，见下方最新结果；历史小节里的“当前/下一步”仅对应其记录时间。

阶段⑨验收时主 IP 初始化为 `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat` 与同目录 `loader_ram.dat`；本次核对已指向 `load_stage10/build` 同一对 DAT。PC0 从 ROM 常驻 Loader 等待 UART，数据 RAM 是常量/状态/缓冲/栈，不走旧自检或 CoreMark 的预置 RAM 复制启动。主IP配置不能证明板上已运行对应镜像。

阶段⑦源码及完整构建已保存 `tests/uart_loader/verified/ddr_crc_stage7/`；PC工具保存 `tools/uart_loader/verified/ddr_crc_stage7/`；runner/TB/模型保存 `sim/uart_loader/build/ddr_crc_stage7_sources/`。该目录 `archive_receipt.json` 核对 37 个副本相同，全部仿真输入和成功 ELF/DAT 哈希一致，未重建镜像。

**不要运行无参数 build.ps1 覆盖 `build/ddr_crc`；它尚未保护这份新实板成功目录。** 后续使用隔离 `-OutputDirectory`。阶段⑧完整约定实板矩阵已在隔离诊断候选两轮验收，仍不能任意 BIN 下载或 RUN。阶段⑦归档交接时只更新入口和成功快照；本轮阶段⑧开发与仿真结果见下方最新进展，原阶段⑦工具/C/RTL/IP和成功镜像不改。

## 历史准备：阶段⑩真实program.bin正式LOAD隔离候选（2026-10-09）

阶段⑨已两轮实板PASS，现开发新load_stage10候选和独立program_stage10应用。新增正式CMD2两次应答：Header→READY→DATA/CRC→CPU写DDR→最终ACK；BEGIN/END、连续地址、total/image_crc身份、重复块精确字节比较且无重写、错误失效及未完成会话5秒超时已实现。383-byte真实ELF/BIN含非空data/bss，两块256+127，最终仅LOADED_UNVERIFIED；VERIFY3/RUN4仍拒绝，持续ROM驻留，没有应用执行。

编译/Harvard/1354条ISA及真实ELF/BIN审查、七组真实CPU/DDR/UART仿真和19项PC离线检查全部PASS：positive49、negative71、extended50、最大61440字节window483、unverified6、原速native8、原速实际BREAK/overflow会话失效及恢复14响应。部署门控STAGE10_SIM_PASS已冻结79项输入和110项证据；阶段⑩实板NOT_TESTED。当前主IP仍为阶段⑨random_stage9成功DAT，PDS/RTL和阶段⑦/⑧/⑨成功档案未改，未打开COM11。

下一步由用户把两IP临时指向load_stage10/build同一对DAT，生成下载位流；KEY0后专用acceptance.py两轮各8响应，得到LOADED_UNVERIFIED/诊断DDR CRC匹配且无Hello，再离线核验两份日志。正式VERIFY在精简计划第②关验收，不能用CMD14诊断CRC授予VERIFIED。操作命令、哈希、复现证据与失败保留见[阶段⑩记录](uart_loader/UART_Loader真实program.bin与LOAD阶段10_2026-10-09.md)。

## 最新结果：阶段⑨随机二进制两轮实板PASS（2026-10-09）

用户完成COM11首轮及after_reset轮；Codex直接读取工程内原始JSON，独立逐帧核验请求、60-byte响应的全部字段/CRC、固定seed输入、镜像/PC工具/部署门控身份及完整数量。每轮1000镜像、17946响应、3700127有效文件字节，1000个整镜像DDR CRC ACK及999个尾哨兵CRC ACK全部通过，零CRC/UART错误、零重试。合计2000镜像、35892响应、7400254有效文件字节；两轮分别549.845/550.179秒，约6729.41/6725.32 B/s，SEQ均1–17946。

板级汇总 `sim/uart_loader/board/random_stage9_board_result.json` 为STAGE9_TWO_ROUND_DIAGNOSTIC_BOARD_PASS / PASS_RANDOM_DIAGNOSTIC_ONLY。两份固定原始日志副本及PDS/IP/当前sbit共10文件配置副本已新增保存；1186项冻结输入及副本、103项仿真证据、阶段⑦37项原始/副本和阶段⑧成功配置档案均未变。部署前286项保护文件中277项未变、9项变化均为用户本次PDS/ROM/RAM/位流部署文件；未覆盖旧成功档案。详见[两轮实板验收](uart_loader/UART_Loader随机二进制两轮实板验收_2026-10-09.md)。

当前两主IP INIT_FILE已由用户指向 `tests/uart_loader/candidates/random_stage9/build/loader_rom.dat` 和同目录 `loader_ram.dat`。Loader从ROM驻留，RAM存放常量/状态/缓冲/栈；CMD13/14仅低60KiB诊断写/真实DDR CRC，不执行随机数据。满61440-byte文件没有实板栈探针，栈保护另有仿真证据；after_reset重新接受SEQ1已核实，KEY0和已下载位流文件身份未独立观察。部署门控的历史NOT_TESTED保持生成时状态，当前实板结论看新增板级汇总。

下一开发步骤为阶段⑩：新独立Hello ELF/BIN/manifest（含非空data/bss），正式LOAD完整END，每块ACK，最终LOADED_UNVERIFIED，持续在ROM、不得输出Hello或自动执行。VERIFY和RUN按后续阶段验收，当前均未实现；本轮只离线核验归档，未开始阶段⑩。成功DAT不重建，后续继续使用隔离候选；上板、复位和串口由用户操作。

## 历史准备：阶段⑨随机二进制/DDR读回CRC隔离候选（2026-10-09）

阶段⑧完整诊断矩阵已两轮实板PASS，用户授权下一步；新候选tests/uart_loader/candidates/random_stage9、新工具tools/uart_loader/candidates/random_stage9、新TB/脚本sim/uart_loader/stage9。新增受限CMD13分块写/CMD14范围CRC，低60KiB窗口，256-byte块，SB前缀/尾部与SW中部；严格同SEQ完整字节比较，重复写不重写且重读CRC；无正式LOAD/VERIFY/RUN或随机数据执行。

编译/Harvard布局/1005条ISA审查、62项负例及恢复、108项旧命令兼容、114镜像/148171字节bulk、原速41响应/10边界文件、原速BREAK/洪泛9响应、独立写后物理损坏7响应及17项PC/独立核验器离线检查全部PASS。部署门控STAGE9_SIM_PASS已冻结1186项输入和103项证据；阶段⑨实板仍NOT_TESTED，当前主IP仍为阶段⑧成功诊断候选。原成功镜像/C/RTL/IP/PDS不改，未打开COM11。

已生成1000实板镜像、3700127有效payload字节、17946停等请求计划（14边界+100组全窗口随机+886组小随机）；每轮至少1000镜像，正常0错误/0重试。现已完成全部仿真/冻结部署门控；下一步由用户用random_stage9/build同一对DAT生成下载诊断位流，KEY0后两轮各1000镜像实板验收，日志再离线核验。详细状态、范围及命令见[阶段⑨记录](uart_loader/UART_Loader随机二进制与DDR读回CRC阶段9_2026-10-09.md)。

## 历史结果：阶段⑧完整异常矩阵诊断候选两轮实板PASS（2026-10-09）

用户提交COM11首轮和after_reset轮，各117/117 PASS。独立struct/zlib核验两轮原始请求/响应、全部字段与CRC、错误恢复、时序和候选/工具/部署门控身份，另逐条对照234条终端PASS。每轮80ACK、37个预期NACK、40个实际DDR CRC ACK；合计234响应、160ACK/74NACK/80CRC ACK，实际DDR CRC均23C3E508。BREAK返回NACK8005且真实UART原因0x10，洪泛先PING ACK再NACK8005且原因0x20，两类故障后PING/DDR CRC全部恢复通过。两轮分别SEQ1–80，日志哈希不同；未独立观察KEY0。

阶段⑧约定的完整实板矩阵已补齐，结论绑定隔离uart_fault_stage8_diag。板级汇总sim/uart_loader/board/uart_fault_stage8_diag_board_result.json为STAGE8_DIAGNOSTIC_TWO_ROUND_BOARD_PASS、PASS_DIAGNOSTIC_CANDIDATE_ONLY；固定两轮JSON/终端及部署工作区10个文件副本已保存。66项输入/58项仿真证据及阶段⑦37项原始/副本哈希仍一致。原成功镜像、r2和原FAIL全部保留；没有改写原二进制验收范围或历史NOT_TESTED报告。

当前两IP已由用户指向tests/uart_loader/candidates/uart_fault_stage8_diag/build/loader_rom.dat与loader_ram.dat；本轮Codex只离线核验归档，未打开COM11、修改RTL/C/工具或重建DAT。磁盘当前sbit已保存副本，未独立核实已下载位流文件身份。详细证据/哈希/复验命令见[两轮实板验收](uart_loader/UART_Loader_UART帧错与FIFO溢出两轮实板验收_2026-10-09.md)。

下一开发步骤为阶段⑨隔离随机二进制/DDR实际读回CRC压力验收；本轮未启动。仍仅固定64-byte DDR诊断，不支持任意BIN或正式LOAD/VERIFY/RUN。上板、复位、串口继续由用户负责。

## 历史准备：阶段⑧UART帧错/溢出实板注入准备（2026-10-09）

用户要求补齐剩余两类实板故障，所有上板/复位/串口操作仍由用户负责。原成功镜像和主IP不改，新增隔离诊断候选tests/uart_loader/candidates/uart_fault_stage8_diag：清错前记录真实STATUS[4:5]，8005响应capabilities bit24/25镜像原因，分别要求0x10/0x20，避免仅凭共用8005推测两项通过。

原速纯引脚9响应和三次ROM启动PASS：BREAK产生1次真实帧错，PING ACK期间96-byte洪泛产生43次真实FIFO溢出、丢43字节，峰值16、两次W1C；不force CPU/UART/FIFO。105.348/116.719ms恢复，PING/DDR CRC通过。PC13项与独立核验器11项离线PASS，108帧候选host回归PASS；部署门控STAGE8_UART_DIAGNOSTIC_SIM_PASS，已冻结66项输入副本。新候选实板仍NOT_TESTED，现可交给用户上板验收。详见[注入准备与用户操作](uart_loader/UART_Loader_UART帧错与FIFO溢出实板注入准备_2026-10-09.md)。

候选host回归、部署门控和同一DAT身份已完成冻结；下一步由用户临时切换两IP/生成下载诊断位流，KEY0后运行诊断acceptance.py --mode all两轮（每轮117响应，原108+线级9）。原阶段⑦/阶段⑧r2成功和FAIL证据全部保留，诊断候选身份与旧二进制分开记录，尚不推进⑨或LOAD/VERIFY/RUN。

## 历史结果：阶段⑧主机可注入异常两轮实板PASS（2026-10-08）

用户用PC工具r2在COM11提交首轮与after_reset轮；独立struct/zlib逐帧核验两份原始日志、请求矩阵、响应全部字段/CRC、时序、额外RX检查记录与终端输出，每轮108/108 PASS：73ACK、35个预期NACK、37个DDR CRC ACK。合计216帧、146ACK、70个预期NACK、74个CRC ACK，实际DDR CRC均23C3E508；错误后的合法PING/CRC恢复全部通过。两轮均接受新SEQ1并完成至SEQ73；未独立观察KEY0，未采集板上位流文件身份。

现行板级汇总为sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json，board_result=PASS_HOST_INJECTABLE_ONLY；UART帧错/FIFO溢出实板仍NOT_TESTED，阶段⑧完整实板范围NOT_COMPLETE。旧ack_nack_stage8_board_result.json及原首轮误报FAIL保留为历史证据，不覆盖；旧仿真报告内NOT_TESTED也保留生成时状态。详见[两轮验收记录](uart_loader/UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。

成功ELF/ROM/RAM、阶段⑦37项快照、阶段⑧27项候选、PC原/r2的11项输入档案及全矩阵221项保护文件/25项仿真输入哈希均匹配。未重建DAT、修改C/RTL/IP/PDS或重新仿真；Codex仅离线核验/归档，所有上板操作继续由用户负责。本轮未启动⑨随机BIN或正式LOAD/VERIFY/RUN；后续须保留上述实板覆盖边界并使用隔离候选。

## 历史记录：首轮PC时序误报与r2复验准备（2026-10-08）

用户已运行首轮：终端94条PASS后停止，第95条truncated_magic_recover_ping记录FAIL。独立struct/zlib核对全部已收95个原始响应及请求矩阵，字段/CRC/预期状态全部一致；truncated_magic正确NACK8004为207.309ms，随后SEQ64合法PING ACK为10.289ms。错误来自PC工具：startswith('truncated_')把恢复PING/CRC也要求>=195ms；旧离线fixture同样给这些恢复ACK加延迟，掩盖了误判。原FAIL日志/终端和输入副本保留，不改写PASS；最后一帧没有完成额外RX检查，整轮仅记录94个完整工具PASS，第二轮尚未提交。

修正版在tools/uart_loader/candidates/ack_nack_stage8_r2/acceptance.py，仅对negative且预期status8004的真正截断包施加195ms下限；独立核验器sim/uart_loader/stage8/check_board_r2.py同步修正。12项时序回归复现旧95帧失败、修正版108帧快速ACK通过，且4类早到超时NACK仍拒绝；另8项通用PC离线检查PASS。成功C/RTL/IP/DAT和原仿真输入不变，不需要新位流/重建DAT。Codex未打开COM11，实板操作仍由用户负责。

板级门控sim/uart_loader/board/ack_nack_stage8_board_result.json为INCOMPLETE_RETEST_REQUIRED_PC_TIMING_FIX，不是阶段⑧实板PASS。详见[PC时序误报及r2复验](uart_loader/UART_Loader_ACK_NACK实板首轮时序误报与PC工具r2_2026-10-08.md)。下一步用户KEY0复位并等DDR后，使用r2工具和新日志ack_nack_stage8_first_pc_r2.json；再复位后另跑ack_nack_stage8_after_reset_pc_r2.json。每轮108/108 PASS再离线核验。不得继续阶段⑨，UART帧错/溢出实板仍未覆盖。

## 历史记录：阶段⑧专项仿真PASS与实板准备（2026-10-08）

用户分工（2026-10-08）：实板下载、供电、KEY0复位和COM11串口验收由用户自行操作；Codex提供脚本/命令，并在用户提交日志后进行离线核验与归档。本阶段不由Codex打开COM11。每轮预期108帧全部PASS（73ACK/35个预期NACK，37个CRC ACK）；预期NACK本身是通过条件，任何RESULT: FAIL/超时/字段或CRC异常均须保留日志后停止。UART帧错/溢出实板仍未覆盖。

阶段⑦成功源/ELF/DAT逐字节复制到tests/uart_loader/candidates/ack_nack_stage8，未重建镜像；PC专项工具在tools/uart_loader/candidates/ack_nack_stage8。主IP继续引用原build/ddr_crc，生产C/RTL/IP/PDS不改，阶段⑦37个原始/归档文件哈希全部一致。

完整114帧/37负例从头重跑PASS：77ACK/37NACK、39CRC ACK，16SW/656LW；RX6000/消费5999（真实FIFO溢出丢1）、TX/解码6840、FIFO峰值16，Errors/Warnings0、退出0，全部保护/镜像/输入哈希不变。全矩阵仅隔离TB的MMIO计时源TIME_SCALE64；另外native8帧原速PASS，坏Header113.941ms、截断body209.509ms；UART8帧独立重测PASS。首次长矩阵因检查器漏计丢字节而FAIL，原日志/输入保留；只修复隔离TB一行计数，已有全矩阵干净重跑，未改C/RTL。

机器门控sim/uart_loader/build/ack_nack_stage8/stage8_sim_result.json为STAGE8_ACK_NACK_SIM_PASS、board_result=NOT_TESTED；完整新日志在sim/uart_loader/build/ack_nack_stage8_repaired/full，最终输入副本在ack_nack_stage8/final_sources。PC工具8项及独立实板核验器5项离线检查PASS，不能当作实板证据。详见[阶段⑧记录](uart_loader/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。

用户说明阶段⑦验收后板子已断电且串口关闭；本轮未打开COM11或生成/下载位流。下一步唯一动作：恢复板子及已有阶段⑦成功位流，关闭串口助手、KEY0复位并等DDR初始化，运行候选acceptance.py的108帧/35个主机可注入负例，首轮与复位后第二轮各用新日志名。仿真已经通过，不需要重建DAT/更换IP。UART帧错/溢出实板无法用普通串口可靠注入的部分继续单独标明未覆盖，不能记作专项实板全PASS；尚不推进⑨随机BIN或LOAD/VERIFY/RUN。

## 当前结果：阶段⑦DDR读回CRC32实板PASS，两轮各100次CRC32 PASS

用户提交COM11的两轮完整输出：每轮100次固定64-byte DDR写/读/比较ACK，再100次只读CRC ACK。
独立struct/zlib逐帧核对ddr_crc100.json和ddr_crc100_after_reset.json，每份200条SEQ1–200：
CMD11奇数帧DATA64、CMD12偶数帧DATA空且LENGTH64/IMAGE_CRC=23C3E508；地址均40000000，
Header/DATA CRC、响应命令/status0/accepted64/字段、实际DDR CRC和日志元数据全部PASS。
写比较响应DDRCRC0，CRC响应PC=DDR=23C3E508；日志均含100组匹配测试编号，无NACK/超时。
两轮共400 ACK（200写比较+200CRC校验），27200请求字节/24000响应字节/12800写入payload字节；
始终重复操作同一64-byte区域，不表示随机数据、12800个不同DDR字节或大程序已验收。
复位证据为按要求提交的after_reset轮和重新从SEQ1成功，未独立观察KEY0。
首轮归档sim/uart_loader/board/ddr_crc100_first_verified.json，SHA256=
87b4dd7c284083a578a848a10fe8d07827f3a71c653a2cfce993910797a39c26；CRC RTT9.843–10.501ms。
第二轮归档ddr_crc100_after_reset_verified.json，SHA256=
2661f01148a5772d1750bc2d76d45ede2e1b3df08ef7ac428d2437b5fa62974b；CRC RTT9.847–10.182ms。
提交输出另保存ddr_crc100_console_verified.txt，200条CRC32 PASS/200写ACK/无FAIL，SHA256=
0b58b955f825523b98d85f3a08a4f300c08a600602ddbe2f7a2f34087bd3045f。
机器汇总sim/uart_loader/board/ddr_crc_stage7_board_result.json为board_result=PASS，
两单轮result.json和独立核验脚本build/check_ddr_crc_board_2026-10-08.py保存复现和范围。
当前两IP的IDF已由用户指向build/ddr_crc对应DAT，ELF/ROM/RAM及仿真全部输入hash仍匹配receipt。
本轮未操作串口、改RTL/C/PC工具、重建镜像或生成/下载位流；未采集已下载位流文件身份。
只有固定64-byte正常CRC实板路径通过；新阶段坏CRC/非法地址/长度/超时/UART错误等实板负例仍待验。
下一步唯一动作：阶段⑧ACK/NACK异常路径专项验收；通过后再进入⑨随机二进制压力测试。
仍不支持任意program.bin下载、正式VERIFY3或RUN4/DDR取指。本轮仅核验归档，不推进后续编码。

## 已有结果：阶段⑦DDR实际读回CRC32仿真PASS

前级固定DDR实板两轮PASS。新增CMD0x12只读0x40000000起64字节，LENGTH描述DDR范围、
UART DATA为空、IMAGE_CRC为PC期望。16次LW的实际内容保存RAM readback后CRC32，
相等ACK64，失配8001且返回actual_ddr_crc；重复校验重新读取，不从UART buffer计算CRC。
PC ddr-crc-test每次先旧DDR_TEST写比较，再CRC只读校验；--count100为100次CRC/200响应。
独立build/ddr_crc，代码2920/常量48/BSS128、730条ISA审查PASS；三次ROM启动PASS，
21帧/两次启动完整真实CPU联仿PASS，覆盖DDR物理损坏、错误PC CRC、未写/复位保留DDR和非法包。
9次CRC校验共144笔真实LW（5次CRC ACK含重复、4次CRC失配NACK），3次旧写比较48 SW/48 LW；
总48 SW/192 LW、Pango AW/W48和AR192。正常23C3E508，损坏AE4B18EA连续两次8001；
错误PC预期23C3E509返回真实DDR23C3E508并8001，同SEQ正确重试ACK；CRC不重写DDR。
非法包/SEQ更换预期/坏DATA CRC/地址/长度/RUN拒绝且不读DDR；复位后直接读取保留DDR也PASS。
RX/pop/MMIO/LBU各1012字节、TX/引脚解码各1260与独立Python/zlib基准匹配；
FIFO峰值1、最低sp3F40/动态栈176字节，20540978退休/56212153周期、Errors0/Warnings0、退出0。
驻留2.06秒、CRC层992.76秒；sim/uart_loader/build/ddr_crc/results.json为DDR_CRC_STAGE_PASS，
保护/候选hash不变、全部输入hash最终核验一致，validated_image.json绑定同一DAT，验收后未重建。
21个共享RTL与前阶段hash相同；未改RTL/IP/PDS或操作串口，无新阶段实板部署。
PC工具离线100次/200应答及每次最多7字节read测试PASS；拒绝包CRC有效但DDR CRC错误的伪ACK。
ROM SHA256=21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a，
RAM SHA256=59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a。
当时共享RTL/IP/PDS不改，生产IP保留用户ddr_fixed引用；原阶段源码/镜像/工具先归档ddr_fixed_stage3。
详见doc/uart_loader/UART_Loader_DDR读回CRC32阶段7_2026-10-08.md；仿真完成时实板待验，后续结果见上方。
下一步唯一动作：同时用build/ddr_crc的ROM/RAM两DAT生成IP/位流并上板，COM11每轮先KEY0复位、
等待DDR初始化，执行--count100 ddr-crc-test；每轮100条CRC32 PASS/200应答，分别保存
board/ddr_crc100.json与ddr_crc100_after_reset.json。前级ddr_fixed位流会拒绝新CMD0x12。

## 已有结果：阶段④⑤⑥固定数据DDR写读比较实板PASS，两轮各100次ACK

用户提交COM11首轮DDR_TEST1–100 ACK输出，随后第二次从SEQ1开始得到NACK8009。
8009是SEQUENCE_ERROR，区别于DDR失配800B；提示序号状态未重新初始化，复位未生效是推断。
核验期间用户更新了ddr_fixed100_after_reset.json，最新文件为SEQ1–100全部ACK。
独立使用struct/zlib逐帧核对两轮全部200帧：请求Header/地址0x40000000/64-byte固定payload、
SEQ1–100、Header和DATA CRC，以及响应Header/命令/status0/accepted64等全部PASS。
复位凭据是此前要求的after_reset日志及SEQ重新从1成功，未独立观察实体按钮；
不能把最初的8009当作复位后PASS，早先失败保留在提交附件来源记录中，原临时JSON已被重测覆盖。
首轮固定归档sim/uart_loader/board/ddr_fixed100_first_verified.json，SHA256=
4f753811e65ea711306a04938a14a33ead3473c9ff8b8d5424504f52166f59a8，RTT15.395–16.111ms。
第二轮归档ddr_fixed100_after_reset_verified.json，SHA256=
94876ca7bb2dd8a5ce2f29b0cbf026a324ecf22508eba8123456370506ef5a33，RTT15.390–16.070ms。
机器汇总sim/uart_loader/board/ddr_fixed_stage3_board_result.json为board_result=PASS；
共200 ACK、12800字节固定payload、20000字节请求、12000字节响应，重复操作同一64-byte DDR区域。
两块IDF已由用户切到build/ddr_fixed的对应DAT，ELF/ROM/RAM与仿真receipt哈希一致；
本轮只读核验并保存证据，没有操作串口、重建DAT、生成/下载位流，未采集下载位流身份。
此PASS只覆盖固定64-byte数据的DDR写读比较；尚无DDR读回CRC32、随机/大文件下载或RUN。
下一步唯一动作：阶段⑦从DDR实际读回计算CRC32，与PC固定数据CRC比较；本轮未继续编码。

## 已有结果：阶段④⑤⑥固定数据DDR写读比较仿真PASS

按用户指令推进CPU写DDR→读回→比较，只新增受控CMD0x11 DDR_TEST与PC ddr-test。
只允许真实DDR基址0x40000000起64字节；16次对齐SW、fence rw,rw、16次LW及实际读回比较，
匹配才ACK64，失配DDR_ERROR800B；不支持任意BIN/LOAD/VERIFY/RUN，不DDR取指。
独立候选tests/uart_loader/build/ddr_fixed，默认仿真--stage ddr-fixed；三次ROM启动PASS，
17帧/两次启动真实CPU/用户口DDR模型联仿PASS，含真实DDR字节损坏→NACK→同SEQ重写恢复。
80 SW/80 LW、Pango用户AW/W/AR各80；重复/非法包不写DDR，RX/pop/MMIO/LBU各1381，
TX/引脚解码各1020字节与Python基准完全一致。FIFO峰值1、最低sp3F40，栈176/4080字节。
24505631退休/66605160周期，Errors0/Warnings0、退出0；驻留3.49秒、DDR阶段1123.60秒。
sim/uart_loader/build/ddr_fixed/results.json为FIXED_DDR_STAGE_PASS，保护/镜像hash不变，
全部输入hash最终复核一致，validated_image.json绑定同一候选DAT，验收后未重建。
ROM SHA256=a24df3ee6ed1ca07b40bbb258fbfa9160ad2070be099d8e8bb2f795b3a04cae7，
RAM SHA256=59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a。
软件/TB/PC修改前阶段②快照已保存，仿真开发完成时各生产IP仍指向用户已验收rx_fixed，未改共享RTL。
当时无串口操作、IP生成/位流部署，实板待验；后续用户部署和实板结果见上方。详见
doc/uart_loader/UART_Loader固定数据DDR写读比较阶段4至6_2026-10-08.md。
下一步唯一动作：同时用build/ddr_fixed的loader_rom.dat与loader_ram.dat生成IP/位流并上板，
COM11复位前后各100次ddr-test，分别保存board/ddr_fixed100.json和ddr_fixed100_after_reset.json。
该64字节实板PASS前不进入DDR CRC、任意BIN下载或RUN。现有PHY/实板DDR历史证据不替代本诊断实板验收。

## 已有结果：阶段②/③固定接收实板PASS，复位前后各100次ACK

用户提供COM11的RX_TEST1–100全部ACK输出；本机rx_fixed100.json逐帧独立核对请求的
固定64-byte向量、SEQ1–100、响应Header/Payload CRC、status=ACK及accepted_bytes=64均PASS。
共6400 bytes有效payload、10000 bytes请求、6000 bytes响应，往返15.411–16.064ms。
首轮固定归档sim/uart_loader/board/rx_fixed100_first_verified.json，SHA256为
6bc43e1bb6acceeb78387556e55ee8216a76c62cba9bfe003dd8de0d334be38c，汇总rx_fixed100_first_result.json。
当前用户已将两个IDF引用切到build/rx_fixed下对应ROM/RAM DAT，两DAT与仿真验收哈希一致；
本轮只读核对并归档，没有生成/下载位流或操作串口。未采集下载位流文件身份。
用户按此前要求提供复位后第二轮RX_TEST1–100 ACK输出；独立解析rx_fixed100_after_reset.json，
100帧请求编码/SEQ/响应Header与Payload CRC/status/accepted_bytes全部PASS，往返15.450–15.909ms。
固定归档sim/uart_loader/board/rx_fixed100_after_reset_verified.json，SHA256为
2665249a3e5884550d3591570658afda2f424f24acccbc5ace909e8f6aa57f37。
复位操作依据用户提交的所要求第二轮结果，未独立观察按钮；两轮共200 ACK、12800 bytes固定payload。
机器汇总sim/uart_loader/board/rx_fixed_stage2_board_result.json为board_result=PASS。
阶段②/③片内固定接收实板PASS；仍未实现DDR写入/LOAD/VERIFY/RUN，不等于程序下载。
推荐下一步唯一动作：受控固定数据CPU→DDR写入、DDR→CPU读回并逐字节比较验证；本轮只归档，未继续编码。

## 已有结果：阶段②/③固定64-byte接收与CPU轮询FIFO仿真PASS

用户要求执行下一步，仅新增受控CMD0x10 RX_TEST与PC rx-test命令，CPU轮询UART FIFO，
存入片内RAM并校CRC/逐字节比较固定64-byte向量，正确才ACK；不写DDR，不实现LOAD/VERIFY/RUN。
新构建默认tests/uart_loader/build/rx_fixed；当时保留原build/根阶段①镜像与生产IP引用，后续用户部署见上方。
源码/build与TB/PC工具已先保存阶段①快照，说明见doc/uart_loader/UART_Loader固定小数据接收阶段2_2026-10-07.md。
首次65-byte超长用例暴露Header拒绝后阻塞TX导致FIFO不能继续接收；已改为先排空坏帧，
100ms连续空闲后再NACK，失败证据保存在sim/uart_loader/build/debug/rx_fixed_fifo_before_drain。
修复后构建ROM2236/常量48/BSS92 bytes、559条ISA审查PASS；新候选驻留3次复位PASS，最低sp3F40。
真实CPU14帧/两次启动全部PASS：4唯一接收+1重复、4正常PING与5个NACK；
RX/FIFO pop/MMIO/CPU LBU各1017 bytes、TX/引脚解码各840 bytes匹配Python/zlib基准与实际RAM。
FIFO峰值1/16、栈176/4080 bytes，19361664退休/52771383周期、DDR请求0、Errors0/Warnings0、退出0。
墙钟876.17秒；sim/uart_loader/build/rx_fixed/results.json为FIXED_RX_STAGE_PASS，
protected_unchanged/image_unchanged均true，validated_image.json绑定同一候选，验收后未重建DAT。
仿真完成时未改IP/PDS、未开串口，实板为NOT_TESTED；后续用户部署/首轮结果见上方当前条目。
两轮固定接收实板PASS后才进入DDR写入/读回。

## 已有结果：UART Loader阶段①PING实板PASS，复位前后各100次ACK

用户提供COM11首轮PING1–100全部ACK的输出；本机ping100.json独立解析核对100帧请求、
SEQ、响应Header/Payload CRC与ACK状态均PASS，往返9.760–10.563ms。
固定证据归档sim/uart_loader/board/ping100_first.json，SHA256为
1595057243e7ed1413fe4e7a047f186575d4dee5c74f78f3e457ee49dc0c9282。
当前ROM/RAM IDF分别已引用tests/uart_loader/build/loader_rom.dat与loader_ram.dat，
两份候选DAT仍匹配仿真验收哈希；这是用户进行的部署，本轮只读核对并归档，未生成或下载位流。
pyserial3.5已由用户安装，COM11为CH340；COM5为蓝牙，之前端口打开失败不属于Loader协议FAIL。
用户确认复位后100次通过；本机ping100_after_reset.json再次独立核对SEQ1–100、请求编码、
响应Header/Payload CRC及ACK状态全部PASS，往返9.758–10.665ms。复位操作依据用户确认记录。
固定归档sim/uart_loader/board/ping100_after_reset_verified.json，SHA256为
f49444d2bbebc409c54faa8023ffac5115bb989f88c015afcdbd6245eb6804d0。
两轮实板共200次有效PING通过，阶段①实板验收PASS；未采集下载位流路径/哈希，
未覆盖断电重上电或高速UART，仍不能声称DDR下载/执行已通过。
推荐下一步唯一动作：阶段②固定小数据接收测试，先核CPU轮询FIFO收到的字节，再逐层接DDR写入与读回。
LOAD/VERIFY/RUN仍未实现，本轮仅归档实板结果，未修改Loader/RTL或重建镜像。

## 已有结果：UART Loader ROM驻留与阶段①PING仿真PASS

用户确认上一轮方案并要求执行，当前仅建立独立ROM常驻最小Loader与PING/ACK，未进入LOAD/RUN。
入口tests/uart_loader/build.ps1、sim/uart_loader/run.py、tools/uart_loader/loader.py；
说明见doc/uart_loader/UART_Loader_ROM驻留与PING阶段1_2026-10-07.md及各README。
构建ROM1876/常量32/BSS76 bytes、469条RV32I机器码审查通过；3次SoC复位/BSS毒化清零/
RAM常量CRC/片内栈验证PASS，ModelSim Errors0/Warnings0、无UART/DDR请求。
默认100次有效PING、1次重复PING和LOAD/VERIFY/RUN三个拒绝应答均PASS，分两次启动且复位后SEQ1可用。
RX/FIFO pop/MMIO/CPU LBU各3744字节、TX/引脚解码各6240字节完全匹配独立Python/zlib基准；
FIFO峰值4/16、最低sp3F60、DDR请求0，编译/运行Errors0/Warnings0、进程退出0。
PING墙钟1863.29秒；results.json为PING_STAGE_PASS，protected_unchanged与image_unchanged均true，
validated_image.json绑定同一候选；LOAD/VERIFY/RUN尚未实现，不宣称DDR下载或执行PASS。
仿真完成时主IP/RAM INIT_FILE/位流未切换，仍为CoreMark validation_60；后续用户部署状态见上方当前结果。
仿真期间生产RTL/IP/PDS及成功Echo/CoreMark镜像受哈希保护；当时未上板或打开串口、pyserial未安装。
推荐下一步唯一动作：用同一已验收ROM/RAM DAT部署最小Loader并做实板PING/KEY0复位验收。
实板PING未PASS前不推进固定数据下载。下方为已有实板结果，不能当成新UART Loader实板PASS。

## 已有结果：两组实板60次CRC与运行时长验收通过

用户2026-10-07标注performance_60/main.dat、validation_60/main.dat并提供两组完整UART。
均Iterations=60、hz=93750000、有Correct operation validated，无ERROR/Errors detected，
Total ticks与PORT_DONE ticks一致；两组seed/list/matrix/state/final全部匹配对应DAT Full Boot凭据。
performance ticks=1664676818，时间17.7565527253秒，final=a14c；
validation ticks=1758636430，时间18.7587885867秒，final=6770。
按配置93.75MHz计时，两组均超过10秒，低于约45.81秒单次测量上限。
据用户UART证据记录两组实板验收PASS；performance按ticks计算约3.379034迭代/秒，
约0.036043迭代/秒/MHz。HAS_FLOAT=0使整数秒和整数除法打印Iterations/Sec=3，未改验收镜像。

原始文本/机器记录在sim/coremark/board/*iter60_user_20261007*；成功DAT直接复制原字节至
tests/coremark_baremetal/verified/{performance_60,validation_60}/main.dat，每组另存verified_image.json。
归档与现有构建DAT哈希均与Full Boot凭据一致；本轮未重建软件或修改算法/RTL/IP/存储深度。
当前主RAM IDF/wrapper/IP TB均引用build/validation_60/main.dat，保持32位数据/12位地址。
保留用户现有PDS/impl/IP生成及其他工作树改动，没有再次下载或运行数小时仿真。
完整结果、复现和证据范围见doc/coremark/CoreMark实板60次验收_2026-10-07.md。
尚未独立测量时钟、采集下载位流哈希或申请EEMBC认证；精确吞吐按配置频率计算。
后续重现用归档原DAT；如修改软件或RTL，重新验收后才能沿用新的结果。以下为此前阶段快照。

## 历史仿真结果：60次两组Full Boot CRC功能验收通过

用户要求执行60次步骤，沙箱外命令已成功。构建显式传ITERATIONS=60和CLOCKS_PER_SEC=93750000，
core_portme.c计时/PORT_DONE频率引用同一编译宏。-Os performance BIN=13220、validation=13228，
各2768条RV32I指令、入口/ABI/ELF-BIN-DAT清单均审查通过，未扩RAM/ROM深度。
输出在tests/coremark_baremetal/build/{performance_60,validation_60}/，保留所有单迭代成功DAT。
ModelSim第一次因小数秒格式启动失败，runner已改整数微秒并使用同一DAT重新启动。
两组完整执行60次，runner退出0，均CRC_FUNCTIONAL_PASS、RESULT: PASS，ModelSim Errors0/Warnings0。
performance seed/list/matrix/state/final=e9f5/e714/1fd7/8e3a/a14c，ticks=736356597；
validation=18f2/e3c1/0747/8d84/6770，ticks=778648235。栈实测均1472/4096字节。
仿真墙钟分别5540.29/5387.02秒（约92/90分钟），两组顺序执行共约3.04小时。
模型程序计时分别约7.85/8.31秒，原版不足10秒错误预期保留；这是功能验收，不是正式实板分数。
完成后重新核对两组ELF/BIN/DAT当前SHA-256，均与验收凭据一致；生产RTL/IP及原成功镜像受保护。
最终凭据目录为sim/coremark/build/{performance_60,validation_60}/，总结果results_60.json。
下一步用已验收performance_60/main.dat切换RAM IP INIT_FILE、重新生成IP和PDS实现后上板，
再用validation_60/main.dat验证。两组实板60次仍未测试，需ticks>=937500000且低于32位计时上限，
核各CRC及Correct operation validated提示，并保存完整UART。无需修改RAM/ROM深度。
最新结果及DAT哈希见doc/coremark/CoreMark_60次迭代构建与上板步骤_2026-10-07.md，以下准备/进行中描述为历史快照。

## 历史准备：60次候选构建与Full Boot入口（当时未执行）

用户问如何进行下一步，已增加tests/coremark_baremetal/build_60.ps1与run.py --iterations 60，
候选放build/{performance_60,validation_60}，保留单迭代成功DAT；TB周期上限按迭代扩展。
多迭代final CRC从对应DAT模型UART记录供实板比较，不能用单迭代final作为期望。
操作说明见doc/coremark/CoreMark_60次迭代构建与上板步骤_2026-10-07.md。
本机exec仍启动失败，本轮无法读取最新git或构建/运行，新入口未验证、60次镜像尚未生成。
用户本机执行build_60.ps1→run.py --iterations 60 --audit-only→run.py --iterations 60，
同一DAT Full Boot通过后才能切RAM INIT_FILE并PDS实现/下载。完整RTL仿真可能数小时/组。
没有修改IP/RTL/深度；尺寸超限时先向用户说明容量缺口和扩深度方案。

## 最新反馈：两组CoreMark单迭代UART CRC均正确（2026-10-07）

用户补充validation串口文本：seed/list/matrix/state/final为18f2/e3c1/0747/8d84/e3c1，
ITERATIONS=1，Total ticks和PORT_DONE ticks均29302693，与已知CRC全部一致。
原文保存于sim/coremark/board/validation_iter1_user_20261007.txt，证据来源为用户粘贴文本。
按93750000Hz换算约0.312562秒，整数秒0及唯一的时间不足ERROR/Errors detected正常。
结合此前performance文本，两组短迭代CRC功能检查均通过，仍不作为正式CoreMark跑分或完整实板PASS。

下一阶段可准备performance/validation各60次的独立候选；按单次线性估算分别17.755/18.754秒，
实际次数/耗时须以新运行ticks为准。先隔离构建、检查尺寸、验收同一DAT，再上板；
多迭代crcfinal不能沿用单迭代e714/e3c1，需独立参考或对应仿真结果。
正式运行需至少10秒、32位计时不溢出、两组CRC正确，并保存完整串口输出。
仍无独立时钟校准或正式分数。本轮终端与Node辅助进程启动失败，未读取最新git/IP状态、
未构建新镜像/跑仿真；仅通过文件补丁保存用户文本、更新相关记录，不修改RTL/IP/已有DAT。
此前16KiB短镜像已装入，当前无扩RAM/ROM深度的理由；新镜像若超限，先告知用户再考虑扩深度。
下方validation实板待验证为此前步骤快照，本条补充新的用户输出证据。

## 最新实板反馈：CoreMark performance单迭代CRC通过（2026-10-07）

用户在上板步骤之后提供完整串口输出，performance seed/list/matrix/state/final为
e9f5/e714/1fd7/8e3a/e714，ITERATIONS=1、ticks=27742465，两处ticks一致。
按用户文本记录performance实板短迭代CRC功能通过，原始文本保存
sim/coremark/board/performance_iter1_user_20261007.txt；详情见CoreMark裸机构建与短迭代CRC文档。
93750000Hz换算约0.29592秒，整数秒=0；唯一ERROR是不足10秒，Errors detected正常保留。
尚无正式分数，亦未独立校准实际时钟。下步先实板validation单迭代（已验收DAT），
核18f2/e3c1/0747/8d84和final=e3c1；performance60次可作后续候选，约17.755秒仅为线性估计，
新镜像须另构建/检查/验收，正式结果以实测ticks>=10秒且计时不溢出及CRC为准。

当前主RAM IDF/wrapper/IP TB已由用户侧切换到tests/coremark_baremetal/build/performance/main.dat，
其哈希仍为已验收52b8b8eafa58bc924c1497e1ff2ba49d071c81e4c0b2bb563a338ee4b04de075。
RAM仍12位地址/32位数据（16KiB），ROM loader未改。本轮保留PDS/impl/IP生成等新工作区变化，
仅记录用户文本与读配置，没有重编译/仿真/修改IP或下载；未确认位流哈希和validation实板结果。
用户要求修改RAM/ROM深度前先说明容量缺口、建议深度和原因，当前不需要扩深度。
下方主RAM仍为Echo、实板NOT_TESTED等内容为上一阶段快照，最新状态以本条为准。

## 最新接续：CoreMark裸机移植与短迭代CRC通过（2026-10-07）

用户明确授权继续移植，先做构建尺寸和短迭代CRC；本条替代下方“尚未移植/构建”的最新状态。
已建立tests/coremark_baremetal独立端口、构建/转换与sim/coremark真实CPU Full Boot验收，
保留coremark-main五个算法.c、coremark.h和清单原字节，没有修改CPU/互连/UART/DDR生产RTL。
详见doc/coremark/CoreMark裸机构建与短迭代CRC_2026-10-07.md；旧源码核对文档继续保留版本/MD5说明。

统一-O2的performance BIN=17108超过16368，转换拒绝；统一-Os后performance=13216、
validation=13224，两组ELF入口0x40000000，RV32I/ILP32，2766条最终指令审查，无未解析符号。
静态2000字节、单线程、volatile种子、整数MMIO计时93750000Hz，原版时间检查保留。
ModelSim ITERATIONS=1两组2/2 CRC_FUNCTIONAL_PASS：
performance seed/list/matrix/state=e9f5/e714/1fd7/8e3a，final=e714，ticks=12271801；
validation=18f2/e3c1/0747/8d84，final=e3c1，ticks=12974244。
两组都验证原ROM搬最终DAT、毒化BSS清零、UART TXD独立解码和计时接受周期差，
栈实测1472/4096字节，ModelSim编译/运行Errors0/Warnings0，无异常/总线错误。
短运行约0.13秒，原版ERROR时间不足及Errors detected预期存在；不是正式CoreMark分数。

复现：先./tests/coremark_baremetal/build.ps1 -Mode performance -Iterations 1，再-Mode validation，
然后C:/python/python.exe sim/coremark/run.py（仅读已有DAT，不自动重建；--audit-only仅尺寸/布局检查）。
已验收镜像在tests/coremark_baremetal/build/{performance,validation}/main.dat；日志/UART/哈希凭据在
sim/coremark/build/<mode>/，总结果results.json。验收后不要另生成DAT直接上板。
主RAM IP仍引用Echo，输出30/Echo成功DAT哈希不变，PDS/impl/既有日志和删除等改动保留。
无IP切换/PDS实现/下载/实板CoreMark，无PHY训练/长迭代或跨32位回绕测试；生产RTL及共用TB未改，
本次没有重跑完整DDR/全CPU/UART回归。下一步可先用同一短DAT上板校准计时并捕获UART，
再据实板速度确定10–30秒迭代，performance/validation各满足至少10秒且不超过32位计时上限后报告分数。
没有提交/推送或联系其他对话。

## 本次交接入口：CoreMark源码已提供并核对（2026-10-07）

用户提供D:/riscv/RISCV/coremark-main，要求阅读源码并更新相关文件，准备移交下一对话。
本次完成源码/平台静态核对和文档更新，未移植/构建/运行CoreMark，没有CoreMark PASS或分数。
优先读doc/coremark/CoreMark源码核对与移植交接_2026-10-07.md，里面给出缺口、配置、CRC、
装载/栈/计时限制和下一步实施顺序；2026-10-04准备文档保留为旧快照。

五个算法.c与随包MD5清单一致，coremark.h与清单不一致，但其Git blob
d0542004edffe6685e093892980b35d96db5ab04与本次官方GitHub文件相同；不改源码/清单。
barebones有计时/初始化/UART三个#error占位，默认主机配置不能直接上板。
本机GCC15.2.0已确认RV32I/ILP32 libgcc路径；仍须检查CoreMark最终镜像及完整运行库。
移植先用静态2000字节、单线程、volatile种子、整数计时/输出；计时MMIO=0x10000008，
93.75MHz，不能rdcycle，32位约45.81秒回绕。当前BIN装载上限16368字节，
64KiB DDR链接范围/4KiB栈也须按实际需求核对；不假定源码存在就能装入现有RAM。
先短Full Boot核对performance/validation CRC，再实板各至少10秒；整数秒截断时
保存iterations/ticks在PC算精确分数。main返回0或LED状态不能单独作为验收依据。

既有Echo实板功能PASS和成功DAT保持不变，当前RAM IP仍指向Echo build/main.dat。
PC→UART→DDR装载器未实现，视镜像尺寸/部署需要再安排，不是开始CoreMark移植的前置。
早期“CoreMark由他人负责”属于历史分工，本次已获源码核对/交接授权；下一对话按最新
用户请求确定开发范围。本轮没有接管完整移植或联系别人。
此前GitHub推送已完成，origin/master与本地HEAD均为f35609d890ddded06f1ac238f4fce95eb91625d5；
本次新增文档/源码尚未提交。源码目录为未跟踪用户文件，PDS/impl/DDR日志/摘要/删除等
原本地改动仍保留，先看git status/diff，勿git add -A或清理/重置。

## GitHub同步准备与发布前复验（2026-10-07）

用户要求更新相关文件到GitHub。发布范围包括tests独立实验、成功镜像、C/Echo仿真
环境、UART引脚/RAM初始化配置及相关文档/实板截图；无关PDS运行状态和临时产物保留本地。
本次没有重编译或转换DAT，直接重跑ModelSim四层4/4 PASS，每层97字节，
Errors0/Warnings0；Echo构建DAT及根归档哈希保持不变。
验收ELF/BIN/DIS/DAT与结果/镜像凭据纳入发布，DAT以.gitattributes保留原字节。
实板结论仍来自此前用户确认，本次没有新增下载/实板测试。
范围、命令和核对记录见doc/uart/UART_Echo_GitHub发布核对_2026-10-07.md。

## 最新反馈：Echo实板功能验收PASS，成功镜像已归档（2026-10-07）

用户已确认Echo位流下载、FPGA双向连线及拆除USB-TTL自身回环；在补充复位/重复
发送建议后进一步反馈“成功”，提交新截图，增加小写a和字母/数字/符号混合文本
对应回显，TX/RX累计均36字节。按用户操作反馈记录复位后重复通信成功，
Echo实板功能验收PASS；截图本身没有KEY0动作轨迹，复位结论来源于用户反馈。
不据此声称长时间无间隙压力、二进制、错误寄存器/注入或IRQ实板PASS。

原build/main.dat直接复制归档为tests/pc_uart_fpga_uart_pc/main.dat，
与输出30成功归档同样保留固定根DAT；本次没有重新构建/转换镜像。
根DAT与原build/main.dat逐字节一致，SHA-256均为
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20。
verified_image.json记录来源/验收范围，build.ps1不会覆盖根基准；
Full Boot和当前RAM IP仍使用原build/main.dat，没有改生产代码/IP/PDS或下载。
截图、两次用户确认及限制见doc/uart/UART_Echo实板基本回显确认_2026-10-07.md。

下一阶段为PC→UART→DDR装载器：先规划装载器、目标程序和栈的互不覆盖地址区间，
做长度/目标地址检查、校验、ACK、超时与读回校验，再做跳转执行。尚未开始该阶段代码。
下方“复位待补齐/仅基本回显”的描述为前一轮快照，已由本条更新。

## 最新实板进展：Echo基本回显样本PASS（2026-10-07）

用户提交UartAssist截图，随后明确确认已下载Echo位流、USB-TTL连接FPGA并拆除
适配器自身回环。nb两次、小写a、hello 123（带空格）及符号/大小写混合文本都有
对应回显；第二张累计TX/RX均26字节。串口为115200/8N1/无流控。
当前可记录PC→FPGA→PC **实板基本回显样本PASS**，不是适配器自身短接回环。
完整记录及保存截图见doc/uart/UART_Echo实板基本回显确认_2026-10-07.md。

本机当前data_ram的IDF/wrapper/IP TB三处INIT_FILE已引用
tests/pc_uart_fpga_uart_pc/build/main.dat；本地DAT哈希仍为
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20，与四层验收一致。
本次仅更新文档并保存截图，没有修改软件/RTL/TB/IP/PDS/镜像或运行构建/下载/仿真。
未保存本次下载位流哈希或原始串口捕获，不能独立核定其所有部署产物对应关系。

KEY0复位后重复、连续多组/长串、实板二进制/错误寄存器/IRQ尚未报告；
截图hello 123带空格，不能改写为已实测无空格hello123。建议补齐复位后A、hello123和
连续多组验收，再固定成功镜像/位流，进入PC→UART→DDR分块装载（尚未实现）。
下方“仅仿真/尚未上板”和“主RAM仍指向输出30”均为各步骤历史快照，已由本条更新。

## 最新目录修正：恢复development与成功归档，Echo迁移（2026-10-06）

用户要求恢复原tests结构，新增pc_uart_fpga_uart_pc放Echo内容；本条替代下方上一阶段
tests/common、src分层和uart_output_30/uart_echo测试目录约定。sim/uart_echo保持不动。

- tests/development：原输出30工作副本、README、uart_printf.c/.h、启动/链接/build.ps1
  和全部已有build产物原样恢复；不是将Echo自动覆盖到development。
- tests/fpga_uart_pc_output_30：原成功归档整目录恢复，根main.dat原字节不变；
  主RAM IP三处INIT_FILE恢复指向此根main.dat，生成初始化字未改。
- tests/pc_uart_fpga_uart_pc：迁入原Echo全部产物，源码放根main.c，功能代码配套
  uart_echo.c/.h，独立startup.S/linker.ld/build.ps1/bin_to_dat.py；不依赖common。
  最终Echo DAT改为tests/pc_uart_fpga_uart_pc/build/main.dat。
- 此前公共代码和输出30的重复新布局移至各build/previous_layout保护保存，不清理用户文件。

原成功输出30DAT仍为e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5；
Echo DAT仍为2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20。
Echo仅修改include/header guard和构建引用，独立脚本在sim build隔离重建核对BIN/DAT
与移动前逐字节一致，没有覆盖最终DAT。新路径ModelSim四层4/4 PASS，
每层97字节；CPU MMIO响应/退休LBU/写TX/引脚解码均一致。
输出30从恢复的归档路径重跑CPU UART验收PASS，Errors0/Warnings0。
Icarus新路径四层也4/4 PASS，保护/布局/.c/.h配对检查PASS，详见本次目录恢复记录；
不重复运行未改动的DDR PHY/RTL回归。
没有修改生产RTL/TB、PDS/FDC、RAM初始化字或下载；Echo仍仅仿真PASS、实板待验证。

从工程根目录：

```powershell
& ./tests/pc_uart_fpga_uart_pc/build.ps1
# 验收后不再重建另一个DAT直接上板
& C:/python/python.exe sim/uart_echo/run.py
```

README、仿真runner、旧C runner、AGENTS和主RAM IP引用同步恢复。
完整说明见doc/software/tests恢复旧结构与Echo实验迁移_2026-10-06.md。

## 上一阶段快照（其中测试目录/构建命令已由上条替代）

## UART Echo 分层仿真完成，实板待验证（2026-10-06）

用户要求在输出30已实板成功的基础上实现PC → FPGA → PC字节Echo。
当前软件/目录已完成，ModelSim和Icarus四层各4/4仿真PASS；Echo尚未上板，
不得记录Echo实板PASS。原输出30实板证据仍仅为用户此前“成功输出30”的反馈。

目录约定已替代旧development规则：

- tests/common：复用启动、链接、UART字节/精简printf、build.py、BIN→DAT转换。
- tests/uart_output_30/src/main.c及build/main.dat：输出30成功基准；原DAT直接保存，
  SHA-256仍为e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5。
  原development/旧归档及全部已有产物完整移至其build/legacy_development、legacy_archive，
  没有清理/丢弃用户工作。build.py重建只比较候选，不覆盖已验证DAT。
- tests/uart_echo/src/main.c及build/{main.elf,main.bin,main.dis,main.dat}：真实CPU轮询
  STATUS、LBU读RX_DATA、SB写TX_DATA；无提示文字、换行变换或IRQ，不是RTL pin回环。
- sim/uart_echo：唯一Echo分层仿真区；run.py、tb/tb_uart_echo.v、tb/echo_bram.v，
  build/uart_module、uart_mmio、cpu_echo、full_boot保存各层编译/仿真/临时产物。

最终Echo上板DAT（仿真直接读取此绝对路径，runner不编译/转换）：
`D:/riscv/RISCV/tests/uart_echo/build/main.dat`。
BIN为240字节/60字，DDR入口0x40000000、main=0x4000003c，初始SP=0x40010000；
BSS含echo_error/echo_count共8字节。DAT SHA-256为：

```text
2cdb17a5a55869f46d14dcf3db5e91a749e010f904f787d8011bb4c64aa88c20
```

| 层 | ModelSim | Icarus | 验收 |
| --- | --- | --- | --- |
| UART RX/TX module | PASS | PASS | 输入/RX/FIFO字节/TX写值/TXD解码均97，最终空闲 |
| UART MMIO | PASS | PASS | 同上，97次RX读响应相等，响应延迟7拍，副作用仅一次 |
| CPU Echo | PASS | PASS | 真实CPU从DDR启动，97次退休LBU值/97次TX写值/97次解码一致 |
| Full Boot | PASS | PASS | 原ROM loader从RAM最终DAT搬60字到毒化DDR后执行，与CPU层同样字节闭环 |

刺激为A、hello123、九组连续hello123和00/11/…/FF二进制，共97字节。
115200/8N1/无流控，RXD按真实8.680556us位周期驱动，TXD独立start检测/中心采样/
LSB-first/stop检查/字节比较，末尾等待20个位时间检查重复输出。
无丢字节、重复、乱序、frame/overflow、CPU同步异常/IRQ、总线错误或超时；FIFO峰值1。
CPU软件echo_count=97、echo_error=0；Full Boot逐字检查loader地址/数据/strobe、
DDR payload、startup SP、BSS毒化后由startup清零及main退休。
ModelSim四层编译/运行Errors0、Warnings0。完整证据在
sim/uart_echo/build/{modelsim,iverilog}_results.json及每层对应.log；镜像凭据为
build/{modelsim,iverilog}_validated_image.json，仿真前后main.dat哈希不变。

复现（工程根目录）：

```powershell
# 仅在修改程序时先构建；构建后必须重新验收，验收后不再生成另一个DAT。
& C:/python/python.exe tests/common/build.py uart_echo
# 一条命令依次重跑所有四层，上一层PASS后才进入下一层。
& C:/python/python.exe sim/uart_echo/run.py
& C:/python/python.exe sim/uart_echo/run.py --simulator iverilog
```

本次没有修改任何myriscv生产RTL、RAM生成初始化字、ROM/DDR初始化、PDS/FDC或位流。
主RAM IP三处INIT_FILE仅从旧已移动路径更新为tests/uart_output_30/build/main.dat，
仍为输出30基准，没有推广Echo、运行PDS或下载。保护核对在
sim/uart_echo/build/layout_before.json、layout_verification.json。
输出30原C五项ModelSim回归因路径迁移重跑5/5 PASS。
完整DDR IP＋物理模型两条回归本轮按序均退出0、RESULT: PASS、无FAIL，
Errors0/Warnings357（store/load/fetch 81.584us，lanes/masks/boundary/DDR-code 90.704us）。
记录见doc/uart/UART_Echo分层仿真与目录统一_2026-10-06.md和原DDR日志；这些原DDR测试
不使用Echo软件。Echo Full Boot采用同步BRAM及带背压/延迟DDR用户口模型，
不含DDR PHY训练、板级复位/电气或USB-TTL实板验证。

下一步由用户将上述同一个已验收main.dat用于RAM IP、重新生成IP、PDS实现/时序/
位流下载，完成实板接收回显。USB-TTL TXD→FPGA RXD，RXD←FPGA TXD，GND共地；
PC 115200/8N1/无流控，关闭本地回显和自动换行；发送hello123应收到hello123。
Echo无限运行且不写TEST_STATUS，原5秒LED watchdog可能超时，LED不是Echo验收依据。
用户确认前保持“仿真PASS、实板待验证”；后续UART分块装载/通用C ISR仍未实现。

## 下方历史快照（旧路径/目录规则已由上述最新接续替代）

历史目录规则（2026-10-06整理时）：`tests/development/` 曾是唯一当前测试程序开发区；
`tests/<其他目录>/` 是已完成验证的测试程序归档。tests只负责测试源码、启动/链接、
构建/转换和最终DAT，不负责RTL、testbench、DDR模型或仿真日志。
本次实板成功输出30归档在 `tests/fpga_uart_pc_output_30/`，其main.dat在重编译前
直接复制自成功镜像，SHA-256为
`e240a9bff8fe79b387b6814315b043214fcec7eeb5d1d6b9fa76a56abce80ff5`。
复制前后完全一致，作为已验证基准固定保存；各build.ps1仅写各自build/，不会覆盖基准。
主RAM IP的INIT_FILE引用已改为归档main.dat，生成初始化字及生产RTL逻辑未变。
从development执行 `./build.ps1`，当前输出 `tests/development/build/main.dat`。
仿真仍在sim/baremetal_c；各目录README和
`doc/software/tests目录整理与成功镜像归档_2026-10-06.md`记录构建、迁移及验证。
以下历史段落中的路径已更新以便访问，但日期、当时程序大小/验证范围仍按原步骤理解。

后续进展（2026-10-06）：第 12.1 项已完成独立 C 装载/DDR 执行验收，ModelSim 与
Icarus 各 4/4 PASS，并验证非空 `.data/.bss`、LED PASS/FAIL/超时。
详见 `doc/software/裸机C_BIN到DAT与DDR_LED仿真验收_2026-10-06.md` 及
`sim/baremetal_c/README.md`。下文第 8/9/11/12 节保留交接时快照；其中 C
“尚无执行验证”的描述已由本补充更新。主板级镜像/IP/生产 RTL 仍未切换，未上板。

再后续（2026-10-06）：用户反馈USB-TTL已到货并通过Hello回环，且已手动将
data_ram初始化指向先前 `sim/baremetal_c/build/converted/main.dat`。
对应程序已归档，development中保留工作副本；提供精简printf输出 `30\r\n`，RAM基准为
`tests/fpga_uart_pc_output_30/main.dat`（680字节/170字），原ROM loader兼容。
ModelSim/Icarus各5/5 PASS，真实CPU/DDR执行且TX引脚自动解码30 CR LF通过。
本次没有修改用户当前主IP/PDS/FDC或下载，用户计划自己替换新DAT并上板。
详见 `doc/software/C裸机printf输出30与RAM镜像_2026-10-06.md`。

最新实板反馈（2026-10-06）：用户明确报告“成功输出30”，本次C镜像的
FPGA → USB-TTL → PC发送链路已获用户实板确认。没有独立位流哈希/串口捕获；
LED、重复复位、FPGA RX接收及UART IRQ实板结果尚未报告。本文下方的
“尚未到货/没有串口实测/尚未部署”等历史描述须结合本条更新阅读。

本文供新 Codex 对话直接接续开发，汇总本对话的结构分析、启动/通信方案和频率核对，并以交接时实际仓库核对后续已集成的 UART、IRQ 与裸机 C 构建。后续代码变动须重新核对，不能把历史 PASS 当成新代码 PASS。本次仅阅读代码、文档和已有日志并创建本文，没有重跑仿真/PDS、下载或修改功能代码。

## 1. 用户目标与开发边界

- 继续完善 FPGA 上的 RISC-V SoC，最终用于物体识别程序及模型计算；CoreMark 已交给别人负责，不要自行重新接管或联系对方。当前没有本对话可确认的 CoreMark 分数。
- 用户明确要求运行方案只能使用 FPGA，不能依赖 RK3568。早期讨论的 RK Linux、FSPI、PCIe 通信方案不作为当前实施方向。
- 用户 USB 转 TTL 已到货并通过 Hello 回环；2026-10-06 进一步反馈 FPGA 串口成功输出30。端子为 5V、3V3、TXD、RXD、GND；FPGA RX/IRQ 实板验证仍待开展。
- 当前优先把已有 UART 和真实 CPU 软件跑通、观察状态，再建立程序/数据装载方式。Cache、DMA、AI 加速器仍是后续规划。
- 遵守当前根目录 `AGENTS.md`。先检查 git status/diff，保留不相关改动，不 clean/reset，不凭文件名删除 IP、初始化内容或镜像。每个独立开发/验证步骤在 doc 记录命令、结果和未覆盖范围。
- 用户请求本次只生成交接文档；本文的后续建议不等于授权立即切换板级镜像、发布或提交其他文件。

## 2. 当前 Git 与工程状态

交接时分支 `master`，HEAD：`f42709275304d47b6159ae5d91bf7c8e671e4035`。

最近与功能相关提交：

| 提交 | 内容 |
| --- | --- |
| f427092 | Wire board UART ports and add verified RX interrupts：贯通板级 TX/RX、UART RX IRQ 及验收 |
| ee1e7f6 | Integrate polling UART MMIO and publish verified SoC diagrams：UART 阶段 1/2/3、数据互连、CPU 轮询、公开验证输入 |
| de3b16d | 仓库入口、构建和仿真工作流文档 |

创建本文前，`git status --short` 显示：

```text
 M RISCV.pds
 M constraint_check/temp_constraint_file.fdc
 M impl.tcl
 M multiseed_summary.csv
 D zongxian.md
?? constraint_check/constraint_backup/temp_constraint_file_2026_10_05_16_02_23.fdc
?? tests/
?? xpack-riscv-none-elf-gcc-15.2.0-1/
```

以上是接手前已有状态，不能归因于本次交接文档。不要恢复删除的 zongxian.md 或覆盖 PDS 会话改动。`impl.tcl` 是累计工具操作记录，含大量历史路径，不是从头重建入口。

`.gitignore` 忽略大部分 doc、旧 difftest、构建库/数据库/波形；本文当前也被 `/doc/*` 忽略，已实际保存但默认不会出现在普通 git status 中。用户没有要求本次提交/发布，也没有要求修改忽略规则。新对话在本机能直接读本文；若将来要克隆携带它，另行处理精确例外或明确添加文件。

## 3. 当前 SoC 结构与模块名称

PDS 主工程：`RISCV.pds`；器件 `PG2L100H`，`FBG484`，速度等级 `-6`。实际设计顶层 `board_top`，主行为仿真顶层 `tb_board_top_selftest`，两个入口要分别核对。

```text
board_top
  ├─ GTP_INBUFDS：125 MHz 差分参考时钟输入
  ├─ GTP_CLKBUFG + reset_button_debounce：参考域 KEY0 消抖
  └─ soc_ddr3_top u_soc
       ├─ ddr3 u_ddr3
       │    ├─ ips2l_mcdq_wrapper_v1_2b：DDR 控制器
       │    └─ ddr3_ddrphy_top：PHY/PLL/训练
       ├─ soc_ddr3_leds u_leds
       └─ soc_top u_soc
            ├─ mycpu_sync u_cpu
            │    ├─ regfile
            │    ├─ alu / br_alu / l_alu
            │    └─ csr_file u_csr_file
            ├─ inst_bus_interconnect
            │    ├─ inst_bram_adapter → inst_rom
            │    └─ 共享 DDR 桥指令端
            ├─ data_bus_interconnect
            │    ├─ data_bram_adapter → data_ram
            │    ├─ simple_mmio
            │    ├─ uart_mmio u_uart_mmio
            │    │    ├─ uart_tx u_tx
            │    │    ├─ uart_rx u_rx
            │    │    └─ uart_rx_fifo u_fifo（16 字节）
            │    └─ 共享 DDR 桥数据端
            └─ dual_sram_to_pango_ddr_bridge → ddr3 用户口
```

CPU 是核内直接实现 IF/ID/EX/MEM/WB 的五级流水。分支判定在 ID，EX 发访存请求、MEM 等待响应、WB 写回/退休并提交 CSR/异常。前递、load-use、等待、冲刷和中断排空均是现有行为，新增外设不得绕开。

指令和数据是分离的 SRAM-like 请求/响应接口。请求接受为 `req_valid && req_ready`；响应为 `rsp_valid/rsp_rdata/rsp_error`，当前无 rsp_ready。互连接受时锁存返回目标，单 outstanding，等待期间不能随 master 当前地址切换响应。

两个 BRAM adapter 适配片内 ROM/RAM IP 的同步时序，不是 DDR 模拟器；仿真 DDR 用户口模型与这两个 adapter 是不同对象。CPU 根据 PC 发字节地址，由指令互连译码决定 ROM 或 DDR，CPU 无需识别存储器种类。

DDR 桥处理一次一笔单拍事务，两路同时请求时数据优先；32 位 CPU 数据映射到 128 位用户拍的槽位和 byte enable。Pango 用户口是 AXI-like，不能套标准 AXI4；没有标准 WVALID/B/RREADY。用户地址按 16 位字计，CPU 地址按字节计，地址/掩码转换须沿用桥实现。

## 4. 时钟、复位和板级状态

- 参考时钟 125 MHz；生成 DDR IP 的系统 GPLL 为输入分频 1、反馈倍频 6、输出分频 8：`125 × 6 / 8 = 93.75 MHz`。
- `ddr3.v` 中 `core_clk = ddrphy_sysclk`；CPU、互连、ROM/RAM、MMIO、UART、桥和 LED 在此域。`CORE_CLK_HZ`/`UART_CLK_HZ` 是计时参数，改数字不会改变实际 PLL 时钟。
- `ddr_init_done && pll_lock` 在 core_clk 两拍同步后释放 soc_resetn。KEY0 按下立即复位，释放稳定 20 ms 后解除；消抖必须用参考时钟，不能用复位期间可能停下的 core_clk。
- `soc_top` 默认 ENABLE_DDR=0；`soc_ddr3_top` 显式启用 DDR。不要把独立 soc_top 仿真默认配置当成板级配置。
- LED：J16 心跳约 1 Hz，M17 表示 DDR ready/SoC 释放复位，K17 自检 IDLE 灭、RUN 慢闪、PASS 常亮、FAIL/超时快闪。5 秒超时是指示逻辑，不等于 CPU 自动复位。

频率核对有两个不同日期的结果：

| 报告 | core_clk 请求频率 | 同域时序估计最高频率 | Setup 余量 |
| --- | --- | --- | --- |
| 本对话 10-04 13:55:43 所读旧报告 | 93.75 MHz | 96.1571 MHz | 0.267 ns |
| 交接时当前 report_timing/board_top.rtr，10-05 22:46:27 | 93.75 MHz | 96.8462 MHz | 0.341 ns |

当前报告为 multi corner、显示 All Constraints Met，Slow/Fast 已分析 setup/hold 无违规；Fast 同域 hold 余量 0.102 ns。它是当前实现时序估计，不是 CPU 独立固定上限或实板升频结果。旧最慢路径由 data_ram 输出经数据互连、CPU 前递、分支比较及取指控制至 PC CE；更改 RTL/探针/布局后须重新确认路径，不能沿用旧瓶颈结论。

当前本地 `place_route/run.log` 记录 10-05 22:40:22 布局布线成功；`generate_bitstream/run.log` 记录 22:50:25 生成成功，存在 `generate_bitstream/board_top.sbit`（3791112 字节）。报告中含 DebugCore 时钟，PDS 输入有 `synthesize/board_top_syn.fic`。这些本地生成产物不在日常 Git 发布范围；尚无本对话可确认的该版本下载、Debugger 捕获或 USB-TTL 实测。UART/复位/DDR 等外部端口仍有未约束 warning，All Constraints Met 仅涵盖实际分析的约束路径。

## 5. 地址、启动和 DDR 内容来源

| 区域 | CPU 字节地址 | 边界 |
| --- | --- | --- |
| 指令 ROM | 0x00000000–0x00003FFF | 16 KiB，仅指令总线 |
| 数据 RAM | 0x00000000–0x00003FFF | 16 KiB，仅数据总线；与 ROM 同址但不同总线 |
| simple_mmio | 0x10000000–0x10000FFF | 4 KiB 原窗口 |
| UART | 0x10001000–0x1000100F | 精确 16 字节，基址 16 字节对齐 |
| DDR | 0x40000000–0x5FFFFFFF | 512 MiB CPU 窗口，需启用 DDR |

simple_mmio 偏移：0 SCRATCH、4 ID、8 CYCLE、C STATUS、10 TEST_STATUS。TEST_STATUS 为 0/1/2/3=IDLE/RUN/PASS/FAIL，PASS/FAIL 锁存至复位。MMIO CYCLE 是 32 位周期计数，93.75 MHz 下约 45.81 秒回绕；当前不能假设已具备完整 mcycle/minstret 计时。

板级 boot flow 保持：DDR 训练完成 → CPU 从 ROM 地址 0 开始 → 从片内 RAM 清单得长度 → CPU load/store 复制 payload 到 DDR 0x40000000 → 跳转 DDR 执行。没有独立 DMA 装载器。

实际 IP INIT_FILE 已核对：

- inst_rom：`MyCpu_test/board_selftest/boot_rom.dat`。
- data_ram：`MyCpu_test/board_selftest/ddr_selftest.dat`。
- 清单为 `MyCpu_test/board_selftest/manifest.tsv`，不是 manifest.json；RAM 末 4 字保留 loader manifest（0x3FF0 起），当前 payload 245 字。镜像构建入口 `MyCpu_test/build_ddr_stage.py`、`build_ddr_selftest.py`。
- 当前 DDR 自检程序仍未访问 UART，不会自动发 H、Hello 或进入 UART ISR。阶段 3 Hello 程序仅是独立仿真镜像。
- 自检使用 DDR 0x40001000 诊断区、0x40002000 scratch；替换 payload 必须重新核对代码、数据、诊断、栈与清单边界。原 payload 长度不能占用诊断区。
- 编辑 DAT 不保证 IP 生成初始化已同步，必须核对 IDF 和实际生成初始化内容，必要时重新生成相关存储 IP。`prepare_board_selftest_ip.py` 默认也会重建镜像，`--promote` 会覆盖主 IP，不要误当只读检查运行。

关于大程序/模型：ROM 容量小则保留精简启动程序；DDR 易失，需要真实装载来源。现有 RAM staging 有约 16 KiB 的总容量限制，不能靠跳转 DDR 自动解决来源问题。将来可从 PC UART 分块接收，CPU 从 FIFO 搬到 DDR，或增加经核对的 FPGA Flash 装载器；这两种正式 loader 均未实现。模型权重、图像、计算缓冲可布局在 DDR，但当前没有既定的生产地址规划、模型导入程序、图像接口或内存管理器。

## 6. UART 已完成的功能与接口约定

已实现独立 TX、RX、16 字节 RX FIFO；MMIO 接入数据互连；真实 CPU 软件轮询；板级 TX/RX 逻辑直连；RX 电平 IRQ 接入 CPU。

- 115200、8N1、idle high、LSB first；93.75 MHz 下取 814 clk/bit，实际 115171.990 baud，误差约 -0.024314%。每帧 8140 拍。
- RX 两拍同步，验证假起始过滤、停止位错误/恢复、异步相位和 ±2% 波特率。错误帧不入 FIFO。
- FIFO 队首组合读（FWFT），empty 返回 0；满且无 pop 时拒绝新字节并报 overflow；满同时 pop/push 可保持深度并接受新字节。底层 error/overflow 是事件，MMIO 负责 sticky 锁存。

| 偏移 | 寄存器 | 当前语义 |
| --- | --- | --- |
| 0x0 | TX_DATA（W） | 低 lane 写入字节；ready 才发送；busy 误写返回既有总线 error，不破坏当前帧 |
| 0x4 | RX_DATA（R） | 合法低字节地址读在接受边沿锁存队首并 pop 一次；empty 返回 0 不 pop |
| 0x8 | STATUS（R） | bit0 TX_READY、1 TX_BUSY、2 RX_NOT_EMPTY、3 RX_FULL、4 FRAME_ERROR、5 RX_OVERFLOW、6 RX_IRQ_ENABLE、7 UART IRQ；31:8=0 |
| 0xC | CONTROL（命令写，读0） | bit0/1 W1C 清 frame/overflow；bit8 写1使能 RX IRQ，bit9 写1禁用，同写禁用优先 |

所有副作用仅在 req_valid && req_ready 执行；等待响应期间不能重复 pop/send/clear。SB/SH/SW 遵守 CPU 移位 wdata/strobe。TX 和 W1C 要 lane0；CONTROL IRQ 命令要 lane1。上 lane RX 访问不消费字节；无效方向/size/非对齐访问/窗口外遵循已有 access fault。新 error 事件与 W1C 同拍时事件优先。CONTROL 写0或只写旧 W1C 不改变 IRQ 使能。

IRQ：`uart_irq = rx_irq_enable && !fifo_empty`，复位禁用，与 generic irq_external 做 OR 送 CPU external。FIFO 读空即撤销；禁用不清 FIFO。board_top 的原三路外部 IRQ 输入仍接0。UART IRQ 在 core_clk 域，不需额外 CDC，不能用 rx_valid 脉冲代替电平。

CPU 原有 machine IRQ：mip MEIP/MSIP/MTIP，mie 掩码0x888，全局 mstatus.MIE；优先级 external→software→timer。排空已发射流水和已接受数据事务后以退休边界 arch_next_pc 入中断；同步异常优先；mepc/mcause/mtval、MIE/MPIE、Direct mtvec 和 MRET 已有机制。本阶段未修改 CPU/CSR。软件还需配置 mtvec、mie.MEIE 和 mstatus.MIE；UART 使能本身不等于 CPU 已开启中断。

## 7. 修改/新增文件交接索引

下面区分功能改动和测试/工程依赖；不是把整个仓库历史都归为本对话修改。

| 文件或目录 | 已完成内容 |
| --- | --- |
| myriscv/uart_tx.v、uart_rx.v、uart_rx_fifo.v | 新 UART 底层；后续 MMIO/IRQ 复用，未重写 |
| myriscv/uart_mmio.v | MMIO、pending 响应、sticky/W1C、FIFO pop；后续新增 IRQ enable/输出 |
| myriscv/data_bus_interconnect.v | 新 UART 精确译码/请求转发/锁存响应目标；target 位宽由2到3，旧目标保持 |
| myriscv/soc_top.v | 例化 UART、连接互连及串口，UART IRQ OR 接 CPU external |
| myriscv/soc_ddr3_top.v、board_top.v | TX/RX 顶层直连；其他时钟/复位/boot flow 保持 |
| source/tb_uart_tx.v、tb_uart_rx.v | 串口独立激励/解码、FIFO/环回测试 |
| source/tb_uart_mmio.v、tb_soc_uart_cpu.v | 总线副作用、地址/strobe/error、真实 CPU Hello 轮询 |
| source/tb_soc_irq.v、sim/uart_irq/* | 16 个 CPU IRQ 场景、真实 UART ISR 闭环及独立退休检查 |
| source/tb_data_bus_interconnect.v、tb_ddr_bus_path.v、tb_soc_top.v、tb_soc_ddr3_rv32i_fast.v | 新端口兼容，非 UART RX 接高 |
| source/tb_soc_ddr3_top.v、tb_soc_ddr3_pds_ip.v、tb_reset_button_debounce.v；sim/board_* 的板级 TB | 同步顶层端口，原功能保留 |
| sim/uart_tx/、uart_rx/、uart_mmio/ 的 Tcl 与日志 | ModelSim 独立运行入口和精选证据；uart_poll.S 是仿真软件 |
| sim/uart_mmio/uart_synth/ | UART 模块独立 PDS 综合输入/主要日志 |
| ipcore/ddr3/sim/modelsim/soc_ddr3_{sim,regress_sim,rv32i_sim}.tcl | 增加 UART 编译依赖；前两项日志随回归更新 |
| MyCpu_test/run_ddr_rv32i_fast.py、run_cpu_ddr_overlap_fast.py | 增加 UART 编译依赖 |
| sim/pds_ddr_{selftest,ip,reset}_compile.tcl、sim/board_*/compile.tcl | 当前共享 SoC 编译依赖更新 |
| 本地 difftest/run*.ps1 与 difftest/tb/* | UART 编译/idle RX 兼容；大部分仍被忽略，完整新克隆未必存在 |
| difftest/golden/rvtool.py、model/inst_rom.v、data_ram.v | 已公开的 UART/IRQ 仿真必要依赖 |
| tests/development/main.c、startup.S、linker.ld、build.ps1 | 当前未跟踪的裸机 C 构建，见下一节 |
| AGENTS.md、README.md、.gitignore、精选 doc/结构图与绘图源 | 同步工程入口、UART 接口、验证和发布依赖 |

本对话早期新增/维护了 SoC结构说明、CoreMark准备、总线评估、RK接口核对和 CPU工作频率核对记录；部分仅本地保存。后续仓库精选文档包含 UART 阶段1/2/3、顶层DebugCore准备、CPU中断验收和结构 PNG/SVG。结构图文件名是阶段3快照，最新 IRQ/板级连接以 RTL 和本文为准。

## 8. 裸机 C 构建现状（交接时新增的本地工作）

工程内已存在 `xpack-riscv-none-elf-gcc-15.2.0-1/bin`，不能继续使用早期“本机没有 RISC-V GCC”的结论。`tests/development/build.ps1` 通过本地路径构建，不依赖全局 PATH。

- `-march=rv32i -mabi=ilp32 -O2`，freestanding、nostdlib/nostartfiles、禁 relax，链接 -lgcc，未链接 libc。
- startup 设置 gp/sp、清 word 对齐 BSS、调用 main，返回则循环；未配置 CSR/中断/异常。
- linker：DDR 起点0x40000000、测试使用64 KiB，顶部4 KiB栈，初始sp=0x40010000；.data LMA=VMA，由 loader 放最终地址；BSS NOLOAD 由 startup 清零。这不是整个 SoC 的永久 DDR 分区。
- 当前 main 是 volatile a=10、b=20、c=a+b 后无限循环，无 UART/TEST_STATUS 上报。包含 stdio.h 不等于支持 printf。
- 已有构建记录和产物：ELF32 小端 RISC-V EXEC，入口0x40000000、rv32i2p1，text=100/data=0/bss=0，BIN100字节；静态反汇编无 M/C/F/A 指令。编译有 c 未读取、链接 RWX LOAD warning。
- 静态推导 main=0x4000003C、最终循环=0x40000060，a/b/c 在0x4000FFF4/FFF8/FFFC，预期10/20/30；尚无运行内存实测。当前 BSS/data 为空，不能宣称这两项初始化已运行验证。
- ELF/BIN 未转换为现有 DAT/清单或接入启动镜像。没有 C 执行仿真或实板 PASS。后续需要独立镜像转换和真实 CPU 验收，再考虑板级部署。

## 9. 已完成测试及实际结果

以下为已存日志/2026-10-05 验证记录，交接时查读而非本次重跑。最主要原始证据可直接读对应日志。

| 测试 | 已完成结果 | 证据路径 |
| --- | --- | --- |
| UART TX | PASS，解码12帧、814 clk/bit，Errors0/Warnings0 | sim/uart_tx/uart_tx.log |
| UART RX/FIFO/loopback | PASS，good75、预期注错frame1/overflow4，writes71/reads70，Errors0/Warnings0 | sim/uart_rx/uart_rx.log |
| UART MMIO + IRQ扩展 | PASS，TX9、req/rsp8247、pop26，Errors0/Warnings0 | sim/uart_mmio/uart_mmio.log |
| 真实 CPU polling Hello | PASS，SB/SH/SW TX、LBU/LB/LHU/LH/LW RX，poll2014，Errors0/Warnings0 | sim/uart_mmio/soc_uart_cpu.log |
| CPU IRQ专项，ROM与DDR取指 | 16场景×2=32/32 PASS；精确退休PC、trap CSR、MRET、访存不重放 | sim/uart_irq/validation_20261005.log；build下逐例sim.log/results.json |
| 真实引脚RX→FIFO→IRQ→ISR→MRET | ROM/DDR共2/2 PASS；pin10/pop10、ISR/MRET4、FIFO峰值5，DDR写一次 | 同上，uart_rx_closed_loop* |
| 原CPU ALU/memory/hazard差分 | 3/3 PASS，终值一致 | 本地 difftest/build/prog*/sim.log |
| 原MMIO/data fault/inst fault | 3/3 PASS，153/445/193 cycles | 本地 difftest/build/*_e2e/sim.log |
| 数据互连/DDR桥 | PASS/PASS，Errors0，原未用端口warning9/0 | sim/uart_mmio/tb_data_bus_interconnect.log、tb_ddr_bus_path.log |
| CPU DDR并发与背压 | 5/5 PASS，背压ld_st PASS | sim/cpu_ddr_*_fast_*.log；runner控制台记录 |
| 完整DDR IP+物理模型基线 | PASS store/load/fetch，81.584 us；Errors0/Warnings357 | ipcore/ddr3/sim/modelsim/soc_ddr3_sim.log |
| 完整DDR IP+物理模型定向 | PASS lanes/masks/boundary/DDR-code，90.704 us；Errors0/Warnings357 | 同目录soc_ddr3_regress_sim.log |
| DDR RV32I fast | supported40/40 PASS；全量40/42 | MyCpu_test/ddr_stage/fast_summary.csv |
| 板级UART端口200 ns检查 | PASS idle-high及逐层连接；未等待训练/启动，Errors0/Warnings353 | 本地tmp/uart_board_debug_20261005/board_boundary.log |
| KEY0 board stand-in测试 | PASS；不是DDR真实长时板级测试 | 同目录key_reset.vvp相关记录 |
| UART独立PDS综合 | Compile/Synthesize退出0、无E、latches0；133条既有/未约束等warning | sim/uart_mmio/uart_synth/run.log |
| 当前本地整板PnR/时序/bitstream | 已有成功日志，时序已分析路径满足；未实板确认 | place_route/run.log、report_timing/board_top.rtr、generate_bitstream/run.log |
| 裸机C编译/链接 | 构建退出0、ELF/BIN属性核对；未执行CPU | tests/development/build/* 与本地构建文档 |

IRQ用户口模型测试涵盖 DDR背压/延迟，不是 DDR PHY IRQ物理联仿；完整物理模型回归单独PASS。CPU验收包括mask、store/load/MMIO等待和响应边界、同步异常优先、IRQ撤销/持续、三路优先级，独立退休模型计算mepc，不能用DUT内部arch_next_pc作为期望值。

UART 发布前还从 Git index 导出65份输入到独立目录、重新生成仿真镜像，四项UART和两项总线测试PASS，确认公开文件依赖完整。完整旧difftest未发布；不能承诺仅新克隆即可运行所有本地旧回归。

## 10. 复现命令与工具

本机工具：ModelSim `D:/modelsim/win64pe/vsim.exe`；PDS `C:/pango/PDS_2022.2-SP6.4`；Icarus `D:/iverilog/bin/{iverilog.exe,vvp.exe}`；Python实际可用 `C:/python/python.exe`。

先从根目录检查状态/源码。下面按需运行，不能把列表理解为每次写说明文档都要重跑全部测试。

```powershell
Set-Location D:/riscv/RISCV
git status --short
git diff --stat
Get-Content AGENTS.md

# CPU polling独立镜像，不改板级IP
& C:/python/python.exe difftest/golden/rvtool.py asm sim/uart_mmio/uart_poll.S sim/uart_mmio/cpu_image

# IRQ专项与真实串口闭环；可加 --case 5 --wave 保存单例
& C:/python/python.exe sim/uart_irq/run_irq.py --stage cpu
& C:/python/python.exe sim/uart_irq/run_irq.py --stage cpu --ddr-code
& C:/python/python.exe sim/uart_irq/run_irq.py --stage uart
& C:/python/python.exe sim/uart_irq/run_irq.py --stage uart --ddr-code

Set-Location D:/riscv/RISCV/sim/uart_tx
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_tx.tcl; quit -f'
Set-Location D:/riscv/RISCV/sim/uart_rx
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_rx.tcl; quit -f'
Set-Location D:/riscv/RISCV/sim/uart_mmio
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_uart_mmio.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_soc_uart_cpu.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do run_bus_regression.tcl; quit -f'

# 完整DDR两条须在此工作目录依次运行，相对file list不能换目录
Set-Location D:/riscv/RISCV/ipcore/ddr3/sim/modelsim
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_sim.tcl; quit -f'
& D:/modelsim/win64pe/vsim.exe -c -do 'do soc_ddr3_regress_sim.tcl; quit -f'

Set-Location D:/riscv/RISCV
& C:/python/python.exe MyCpu_test/run_ddr_rv32i_fast.py
& C:/python/python.exe MyCpu_test/run_cpu_ddr_overlap_fast.py
& C:/python/python.exe MyCpu_test/run_cpu_ddr_overlap_fast.py --backpressure

# 本地完整旧difftest存在时才能运行以下命令
powershell -NoProfile -File difftest/run.ps1 -Prog prog0_alu
powershell -NoProfile -File difftest/run.ps1 -Prog prog1_mem
powershell -NoProfile -File difftest/run.ps1 -Prog prog2_hazard_precision
powershell -NoProfile -File difftest/run_mmio.ps1
powershell -NoProfile -File difftest/run_access_fault.ps1
powershell -NoProfile -File difftest/run_inst_access_fault.ps1

# 裸机C：仅生成产物，不部署
& ./tests/development/build.ps1
```

DDR Tcl `LIB_DIR` 为 `C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation`。通过标准：出现对应 RESULT: PASS、无 RESULT: FAIL、ModelSim Errors:0；厂家warning无需0，但应与基线比较。IRQ runner build在 `sim/uart_irq/build/`，依赖公开rvtool及行为ROM/RAM，可重新生成。

板级主仿真由 `RISCV.pds` 指定 `sim/board_main_selftest/compile.tcl` 与 `run.tcl`，不同于独立DDR两条脚本。在 ModelSim Transcript 从DDR modelsim目录依次 do 这两份绝对路径脚本。依赖 `D:/modelsim/pango_sim_libraries` 的匹配预编译库及 `sim/compile_ddr3_physical_model.tcl` 派生模型；库映射未准备时不能假设装好ModelSim即可运行。

整板构建用 PDS 打开 RISCV.pds，核对 board_top、三块IP、4个UART源及实际FDC后，按 Compile→Synthesize→Device Map→Place & Route→Report Timing→Generate Bitstream。不回放历史impl.tcl。首次克隆不带本地数据库，不凭PDS旧完成标识跳过构建。

改CPU/互连/桥/DDR顶层或共用TB至少跑完整DDR两条，并跑受影响RV32I/异常回归；改UART底层跑TX/RX/FIFO/环回；改MMIO/中断跑MMIO/CPU polling及四组IRQ，同时保证原MMIO/access-fault回归。所有编译soc_top的入口要包含四个UART RTL，非UART TB显式RX=1。

## 11. 已知问题与尚未覆盖事项

1. RV32I fast仍有 `fence_i` 和 `ma_data` 两个known_gap，日志FAIL且tohost=0x539；不能写42/42 PASS。具体原因需另读测试/RTL定位，本次未修CPU。
2. UART逻辑已通，实板软件仍是DDR自检，无串口发送/IRQ；启动镜像部署未完成。之前顶层准备步骤按当时用户失败停止条件停在候选H代码，不能把停止点当成已部署。
3. 当前FDC已有未提交 `uart_tx=AA20`、`uart_rx=AA21`、LVCMOS33/VCCIO3.3及PAP_IO_UNUSED TRUE。它们是外部PDS会话更新，不是已核准连线；不能自动改或宣称可用。
4. 手册FPGA扩展排针J8表中35/36对应AA21/AA20，但图标有RS485共享提示。需核实际原理图、收发器占用、Bank供电、方向和约束属性，尤其避免USB-TTL TX与板上输出相接。不能把ARM UART2 Type-C当成FPGA UART。
5. 对话另提过普通GPIO候选J8 pin3=AB21作RX、pin4=P14作TX，GND pin37；这是备选方案，未在当前FDC实施，不可与AA20/21方案混用。最终排针编号/板修订以官方图纸和实物确认。
6. USB-TTL基本连法为TXD→FPGA RX、RXD←FPGA TX、GND共地；板卡独立供电，通常不接模块5V/3V3。必须核实际TX逻辑电平，模块有3V3电源端不保证TX为3.3V。本对话未测量电平或上板。
7. 当前时序/bitstream已有新本地产物，但功能开发记录中的“未运行PDS”描述的是各步骤当时范围，不代表交接时目录里没有实现结果。现有产物对应性、探针配置和实板结果仍须接手确认。
8. 还无Cache、DMA、CLINT、PLIC、TX IRQ、通用C ISR上下文保存、嵌套中断、模型推理程序或AI加速硬件。IRQ测试ISR专用x20–x28仅为测试约定，不能直接当C ABI处理器。
9. 本地C只完成构建；BIN不是IP DAT。程序、BSS/栈/诊断区布局及装载必须显式设计；没有模型权重、图像或中间结果写入DDR的正式链路。
10. CoreMark尚需独立baremetal port、计时/输出和装载约定。不要用LED5秒超时判断至少10秒的性能运行，32位周期计数要处理回绕。这个任务由他人负责，本对话无分数验收。
11. 当前桥单笔单拍且数据优先，有吞吐/取指等待限制；尚无burst、多outstanding、公平仲裁和DMA一致性。这不妨碍当前基础load/store/fetch已验证，优化应按实际需求另立步骤。

## 12. 建议新对话从哪里继续

先读取本文及当前AGENTS、git状态，再针对用户新指令选择路径，避免从已完成UART TX/RX阶段重做：

1. 若先跑C：在独立sim目录将tests/development/build/main.bin转换为CPU/DDR模型镜像，核入口、loader内容和sp，使用真实SoC验证a/b/c终值及0x40000060退休循环；增加非空.data/.bss用例后再宣称C初始化通过。保持主IP/镜像不动，验收后再设计板级部署。
2. 若先调实板UART：核定物理脚/电平，确认当前FIC和捕获节点；在独立候选payload的DDR自检成功路径加入轮询发H，核代码不越0x40001000、清单长度、原自检与TEST_STATUS，先完整板级联仿自动解码H。之后按用户授权再推广主RAM/IP。
3. DebugCore最小观测选 `board_top.u_soc.u_soc.u_uart_mmio` 的tx_send/tx_ready/tx_busy/tx_data/data_latched和实际TX寄存器；RTL别名可能综合合并，按网表来源核对。core_clk采样，All Data，8192样本且触发靠窗口开头（0–32）或用16384样本；每帧8140拍。触发tx_valid&&tx_ready&&data=0x48，不能用busy过滤采样来计算位宽。新插探针后重跑时序。
4. 串口验收通过再建立PC→UART分块装载协议，第一版CPU搬FIFO到DDR：长度/目标地址/校验/ACK/流控/超时/范围检查明确，读回校验后跳转；这是新功能，尚未实现。随后再规划权重/图像/缓冲DDR区域和加速器接口。

完成每步时写清“RTL接通、仿真PASS、时序通过、镜像生成、下载成功、实板收发PASS”分别有哪些证据，不能互相替代。
