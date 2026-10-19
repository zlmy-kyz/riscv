# 037：数据互连并行译码与ready，缩短最差两条取指接受路径

## 2026-10-18：若进行流水架构改造，推荐五级真EX分支与EX前递（仅建议）

用户询问改流水架构时推荐如何修改。本轮结合实际CPU控制只做架构评估，不改RTL、不新增038、不启动仿真/PDS/板测。037功能/实板待验收边界保持。

推荐目标仍为单发射、顺序五级`IF→ID→EX→MEM→WB`，职责重新划分：

| 级 | 推荐职责 |
|---|---|
| IF | 寄存PC/请求与响应缓冲；消费已寄存redirect，维护已接受错误路径响应的丢弃归属 |
| ID | 译码、寄存器堆读取、立即数、源寄存器编号/实际使用标记；寄存原始操作数和控制信息 |
| EX | 以EX/MEM及MEM/WB寄存结果做最终前递；ALU、分支比较、目标计算、采用目标的对齐检查；在真正推进时形成单次redirect事件 |
| MEM | 从寄存地址/写数据/strobe发总线请求并保持到接受，等待响应；load抽取/扩展后寄存结果 |
| WB | 寄存器写回、精确提交/异常；load仅在其返回结果已寄存且无错误时成为可前递来源 |

**一、将分支比较和目标计算真正移到EX，并把最终前递移到EX输入。** ID/EX需保存branch/JAL/JALR类型、源寄存器号、原始rs1/rs2、PC、立即数；ALU的立即数操作数和分支/store的rs2必须各有正确选择，不能把现id_ex_src2（可能已替换为立即数或4）直接作为分支rs2。EX优先选择较年轻的有效EX/MEM生产者，再选MEM/WB，最后用保存的寄存器值；x0、实际uses_rs、load/乘法未就绪、异常和取消均须处理。ID计算taken后仅延迟提交的方案，仍把load返回→ID前递→比较留在同周期，不作为推荐的目标结构。

**二、规定load数据在结果寄存后才能被消费。** 不保留当拍`data_rsp_rdata→load格式化→EX比较→取指`的新长旁路。对尚未可用的最近生产者，必须互锁，不能因为老MEM/WB也命中就取较旧值。依赖覆盖ALU、分支/JALR、store地址与数据和CSR源；乘法仍按实际结果可用时机解除。由此引入的load依赖停顿要真实计数，旧load-use分类不是新增代价上界。

**三、把redirect做成有生命周期的寄存事件，IF只消费寄存结果。** EX真推进且没有更老故障时，记录redirect_valid/target；随后IF消费一次。必须保持WB同步异常/MRET和IRQ等既有精确性约束，不能在EX停顿期间重复跳转。普通分支仅清更年轻的IF/ID和ID/EX，不误杀分支自身及更老MEM/WB；更老load响应故障须压制年轻分支与store。分支实际next_pc随本条指令前进，目标错位cause/tval改由EX产生；arch_next_pc、trap恢复PC、IRQ排空、FENCE/WFI及性能观察事件同步适配。接受后的错误路径取指仍须按token丢弃，不能靠撤销已握手请求冲刷。

**四、目标架构把数据请求移到寄存地址之后。** EX计算地址/对齐/写lane后锁入EX/MEM，MEM发一次并保持，单独跟踪请求已接受/等待响应；不能每个等待周期重复发送。这样可缩短旧EX ALU→互连decode/ready→ID发射/分支链。该调整可能增加访存延迟，须单独评估；保持当前桥、单读/单写条、034快ACK与load响应时序合同，不能和移除SoC响应寄存混为一项。若最终返回路径仍过长，再据新报告考虑单独LSU返回级，不预先将流水加深到六/七级。

**五、前端与后端按寄存valid/局部ready组织。** 使用现有或小容量取指队列隔离IF与执行停顿，不让DDR/数据ready贯穿所有级再决定取指字段CE；已有单笔外部取指归属可先保留，不因内部缓冲增大自动增加DDR读在途。ready控制本身仍需时序审查，增加一个缓冲不自动等于切断全链。初版可保持顺序取指/未跳转预测；取得EX分支实测恢复代价后，再独立评估小BTB/BHT，不能用预测命中率假设预支收益。

### 性能与实施次序

当前同冻结BIN的036 P226655369cycles含19111364次redirect，V226663043cycles含18946595次。若每次redirect净多一拍、没有重叠或其他周期变化，总cycles敏感度约P+8.4319%/V+8.3589%；净多两拍则约+16.8638%/+16.7179%。寄存redirect、EX判定后移、取指队列及依赖等待的组合决定真实增量，不能直接指定“总共只多一拍”。以上不是预测或上界，也不包含请求后移可能增加的访存停顿。

性能判据为`C_new / f_new < C_old / f_old`，即实际频率增幅须高于实际cycles增幅。当前报告估计95.9081MHz与93.75MHz仅约2.3%的差距，不足以证明架构后移的恢复代价能被抵消；改架构可能带来更大余量，但没有新实现证据前不承诺109.375/125MHz。

若后续实施，先独立做“EX最终前递＋真EX分支＋单次redirect/精确取消”这一完整功能块；核时序与相关功能/实测代价后，再单独做MEM请求寄存化/前端局部握手，最后才评估预测或加级。保留每项可回退的源码和旧应用/提交证据，不同时混改缓存容量、写条深度或DDR频率。仅评估时按既有约定不运行测试/PDS；当前未选择实施或创建新任务。

## 2026-10-18：最新037报告WNS+0.240ns，当前最长链转为load返回到独立I字段CE

用户要求“查看日志，分析时序最长的路径”，本轮仅只读分析与记录，不继续改RTL或派发测试。最新`report_timing/run.log`明确报告完成，报告内时间为10-18 02:49:50，**All Constraints Met**。93.75MHz主域slow setup WNS **+0.240ns**、TNS0、0失败端点；fast setup+4.530ns，camera_pclk setup+0.893ns，各组hold摘要无失败。工具估计Fmax95.9081MHz，实际时钟仍93.75MHz。

相对037改前02:07:14的+0.115ns，整体最差余量增加**0.125ns**，估计Fmax由94.7718变为95.9081MHz。这是本次所读实现报告的时序改善，不是已提频或CPU程序加速。原先EX ALU→数据地址译码/ready→取指接受及I tag失效的三个端点已不在报告所列主域前三；不能据未列出就说相关路径已完全消失或精确量化每条改善。

[观察收据](../../sim/cpu_data_decode/timing_review_20261018_a/review.json)为`TASK037_CURRENT_TIMING_REPORT_MET_SOURCE_OBSERVATION_ONLY`，保存报告/run.log/PDS副本及77项当前输入哈希。相对037静态最终清单只有PDS和报告变化，数据互连/CPU/036桥/SoC/BIN保持；未独立重建PDS实现源集或观察板上编程。原日志有外部端口约束warning，结论限定于报告现有约束与Pre-silicon模型，不将All Constraints Met扩为引脚约束覆盖完整或功能验收。

### 当前限制主频的前三条

三条均从`g_camera_data_rsp_register.data_q[21]`出发，路径前缀完全相同，均为17级：

| 终点 | slack | 数据路径总延迟 | 逻辑/布线 |
|---|---:|---:|---:|
| DDR桥inst_overlap_store_q/CE | +0.240ns | 9.985ns | 3.501/6.484ns |
| DDR桥inst_overlap_addr[2]/CE | +0.255ns | 9.982ns | 3.501/6.481ns |
| DDR桥inst_overlap_addr[10]/CE | +0.255ns | 9.982ns | 3.501/6.481ns |

完整链为：**DDR load返回寄存data_q[21] → 数据互连响应mux → l_alu字节选择/格式化 → MEM写回数据选择及MEM→ID前递 → id_rs1[5] → br_alu大小比较进位链 → id_taken → 目标异常/前端消费控制 → 指令互连请求有效 → take_inst_overlap → 独立I地址/store标记CE。**

这次起点是load数据返回，而上轮是EX ALU数据地址；新的瓶颈确实已经转移。数据互连请求译码虽已优化，响应数据mux仍是原编码target选择，不能把请求侧并行化理解为响应mux也已变。报告中的mem_wb_wdata寄存器名用于共享组合逻辑命名，路径未跨过它新增一拍；关键链仍在同一主时钟周期内完成。

最差路径9.985ns中，逻辑35.063%，布线64.937%。报告绝对arrival为16.352ns，包含6.367ns发射时钟延迟，**不能把16.352ns当纯组合延迟**。按实际节点累计值可分为：

| 段 | 增量 |
|---|---:|
| data_q至数据互连data_rsp_rdata，含clock-to-Q | 1.927ns |
| load选择/格式化及MEM前递至id_rs1 | 2.854ns |
| 分支大小比较与taken选择 | 2.136ns |
| 异常/前端/指令互连至独立I接受CE | 3.068ns |

四段合计9.985ns；这些是当前所读单条实现路径的定位，不是每项优化可直接节省的ns。最后`take_inst_overlap`扇出30；全链还经过多处跨位置布线，因此单改br_alu比较表达式或只减少一层门不能保证整体收益。

### 下一候选的静态判断（尚未实施）

当前最小范围候选是把**独立I槽`inst_overlap_addr`及`inst_overlap_store_q`**同已预采的冲突向量一样，评估改为在现有`inst_tag_sample`窗口采样；pending/真实接受和响应归属仍保持实际握手。这样可解除地址与store payload CE对晚到take_inst_overlap的依赖，不新增拍数。

该候选需明确证明：每次真实独立I接受必命中采样窗口；pending=0时任意样本不生效；pending miss关闭窗口保持原地址/store/冲突；旧hit消费同沿使用旧值，新接受同沿建立新归属；提升、D优先、store同行强制miss和复位不变。地址预采样也可能把关键路径移到地址D输入或pending控制，不能仅凭RTL写法许诺Fmax。当前只是评估建议，没有创建038、修改桥、延后load前递或迁移分支阶段。

本轮复现入口`python -B sim/cpu_data_decode/timing_review_20261018_a/review_timing.py`已执行，收据保护不覆盖。没有HDL/PDS/串口运行或新增测试代码。037相关动态/实板仍未完成，不从036应用成功继承PASS；用户本次只要求分析，不自动开始后续优化或派发DeepSeek。

## 037原静态准备（以下待PDS为历史状态）

2026-10-18用户要求看完036日志后开始优化时序最差路径。036原始P/V复核完成，见[036阶段顶部](MINI_桥请求字段预采样_2026-10-18.md)与[实板收据](../../sim/cpu_request_presample/board/review_20261018_01/board_review.json)：P226655369cycles/2.417657269秒、V226663043cycles/2.417739125秒，93.75MHz；协议/应用CRC/13计数通过，较035差异不足0.002%，不宣称提速。完整动态握手/冲突/复位NOT_RUN、KEY0暖复位未解决。

本轮仅修改主`data_bus_interconnect.v`的组合译码和ready表达式，静态审查/八配置null-target展开通过；**待用户PDS重新实现**。CPU、指令互连、036桥、分支/load前递、缓存/写条、IP/PDS/FDC、时钟及成功BIN不改。没有运行动态HDL、PDS、下载或串口，不重测036，不自动提频。

## 最新最差路径及本轮选择

所读报告`report_timing/board_top.rtr`内时间为10-18 02:07:14，All Constraints Met；主域93.75MHz slow setup WNS+0.115ns/TNS0/0失败端点，估计Fmax94.7718MHz。报告观察与原文见[准备目录](../../sim/cpu_data_decode/preparation_20261018_a/)，不是本轮修改后实现结果。

| 所列主域slow最差路径 | slack | 路径特征 |
|---|---:|---|
| id_ex_src2[1]→EX ALU→data_req_addr→数据互连译码/ready→CPU停顿/ID发射→分支目标取指→指令互连response_target[0]/CE | +0.115ns | 15级，逻辑3.401ns/布线6.634ns |
| 同源/同前缀→CPU inst_pending_pc[3]/CE | +0.173ns | 15级，逻辑3.401ns/布线6.612ns |
| id_ex_src2[0]→EX ALU→data_req_addr[10]→I行tag动态选择/比较→I tag[57][7]/CE | +0.231ns | 11级，逻辑2.482ns/布线7.379ns；data_req_addr[10]扇出826 |

前两条的共同瓶颈包含数据互连串行排斥译码及ready优先mux；并非只由ID分支比较或load前递造成。报告中的CNN/写条寄存器名也可用于命名共享组合逻辑，不能据名称认定路径经过对应寄存器新加一拍。当前先单独处理共同数据译码段，作用于最差两条；第三条的I失效/高扇出作为下一份新报告后的候选，不同时重写桥，避免混淆效果。未保证前两条消除后第三条不会成为新WNS。

## 唯一改动

[data_bus_interconnect.v](../../myriscv/data_bus_interconnect.v)原先递归使用已带优先级的select作后续排斥：RAM→MMIO→UART→Camera→PP→CNN→DDR。当前板这些窗口实际两两不重叠，但原表达式仍可能映射出串联选择；接着ready再走一组嵌套条件mux。

现在先对各窗口并行计算`raw_hits`，再用**常量窗口相交判定**构造高优先级mask：

```verilog
windows_overlap = (((base_a ^ base_b) & mask_a & mask_b) == 0);
select_i = raw_hit_i && !(|(raw_hits & HIGHER_PRIORITY_MASK_i));
```

只有常量地址位证明不可能重叠的屏蔽项才被删除。实际板RAM0/16KiB、MMIO0x10000000/4KiB、UART0x10001000/16B、Camera0x10002000/64B、PP0x10003000/64B、CNN0x10004000/256B、DDR0x40000000/512MiB互不重叠，所有priority mask可在展开时归零。可配置BASE/MASK人为重叠时，仍按原RAM>MMIO>UART>Camera>PP>CNN>DDR优先级选择，未把硬件合同缩为“只支持当前地址”。禁用外设raw hit为0。

互斥selected的ready采用：

```verilog
m_req_ready = issue_allowed && !((ram_select && !ram_req_ready) || ... ||
                                 (ddr_select && !ddr_req_ready));
```

未映射或被DDR权限阻止且没有其他selected时，ready仍按原默认1接受后返回error；非DDR写排空门仍可阻止issue。`frame_blocked`、`pp_blocked`、`response_turnover`、`issue_allowed`表达式保持，防止绕过Camera所有权、PP完成/长度/只读和posted写排空。**不新增寄存器，不改变请求/响应拍数或CPU分支阶段。**

## 静态代数与边沿审查

改码前论证见[edge_analysis_before_edit.md](../../sim/cpu_data_decode/preparation_20261018_a/edge_analysis_before_edit.md)。

1. 两个mask/base窗口存在公共地址当且仅当它们共同约束位没有相反值，即上述overlap公式。只在已证明无交集时删排斥项，故无地址可使被删的高优先raw hit和当前raw hit同时成立。
2. 递归selected优先级的高位并集等于高位raw hit并集；将串行排斥改为并行raw并集不改变任意二进制地址的最终selected。即使不规范mask、零mask、参数重叠或外设禁用也保持优先级。
3. selected互斥，因此原ready优先mux严格等于“没有被选从机处于not-ready”。对任意下游ready、当前请求地址和权限/排空状态，m_req_ready相同；未映射默认ready也相同。
4. req_fire及其后slave valid/addr/write/size/strobe、响应选择/data/error、pending/response_target全部逐字保持。由组合selected/ready相等，每个接受边沿、旧响应同沿新接受、error禁止turnover、背压和复位归属相同；没有无接受副作用。

此为静态代数审查，非动态或形式等价验证；不对X/Z地址的未定义传播声称新合同。八配置语法展开只证明编译/展开，不验证真实请求与响应行为，也不保证综合器的实际映射和布线收益。

## 输入与本轮证据

[准备目录](../../sim/cpu_data_decode/preparation_20261018_a/)保存77项输入清单，仅新增备份当前数据互连、最新报告与变化PDS，其余未变源码/固定BIN复用036快照，036实板收据引用原不可变文件。只有数据互连变化，其他76项保持。

- 数据互连改前：`b59d38413b01775f66f29959509ea4a10616e50c9a87eb6f8b55947be9fe4994`。
- 数据互连最终：`e1aca083d8343fb454575052bdd3134730a803e803497fa387b9bbda4a0aa847`。
- 036桥保持：`4d628cfa4e9f68e18671b1e42399ceaddcb2ddabeca3d9b505e5d632821db589`。
- CPU保持：`b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3`。
- [review.json](../../sim/cpu_data_decode/preparation_20261018_a/review.json)：`TASK037_DATA_DECODE_STATIC_ONLY_PENDING_USER_PDS`；有效输入为同目录[after_manifest.json](../../sim/cpu_data_decode/preparation_20261018_a/after_manifest.json)及[decoder.patch](../../sim/cpu_data_decode/preparation_20261018_a/decoder.patch)。

已执行入口（已有证据保护不覆盖重跑）：

```powershell
Set-Location D:\riscv\RISCV
python -B sim/cpu_data_decode/preparation_20261018_a/static_prepare.py snapshot
python -B sim/cpu_data_decode/preparation_20261018_a/static_prepare.py review
```

board_top、数据互连默认、全外设/写排空开启、RAM覆盖外设、MMIO宽窗覆盖DDR、UART与Camera重叠、turnover关闭、RAM零mask覆盖全部，共八配置`iverilog -g2005 -tnull -i` exit0；真实cache封装、缺失厂家内部模块黑盒，主板仅既有两条DDR端口方向提示。机械检查确认接口/参数段及req_fire起到末尾全部文本保持，`git diff --check`通过。精确argv/cwd/输出保留于收据，不记功能/时序PASS。

## 下一步与相关验证边界

用户保持93.75MHz运行根`RISCV.pds`的综合/映射/布局布线，回传新时序。对比上述两条路径的译码/ready段、整体WNS及是否转向第三条I失效/其他端点。只看一条路径变短不等于整体改善；提频还需DDR/IP/core_clk支持及相关UART/计时/外设参数独立核对。当前不改频率、不承诺109.375/125MHz。

时序通过后Sol再定稿单组任务，DeepSeek实现并执行；当前只有方案边界，无待领取执行入口。此轮数据互连shared译码改变，相关最小组应覆盖：

- 当前板所有窗口边界/非法地址，全部外设ready背压及互斥valid，独立参考判译码/局部地址/写lane与strobe/响应归属；未选择从机的ready不得影响接受。
- 旧正常响应与新接受同沿、旧error禁止接续、pending背压、复位取消，真实接受=响应+取消+在途；不能用PASS文本代替逐沿事件。
- Camera两个槽读所有权/写拒绝/释放后禁止，PP busy/done、0x6c00长度边界与只读合同，非DDR MMIO/UART/PERF STOP不越过posted写排空；权限拒绝仍返回原access fault且无副作用。
- 最小特殊参数重叠（RAM宽窗、MMIO宽窗、UART/Camera同址）及禁用开关，保持原最高优先级，不同时向多个从机发有效请求。
- 因新增decoder/ready判据而需要的一次036旧数据互连与037同刺激对照，配独立参考，逐拍真实接受/响应/副作用及总周期一致；不重跑036成功P/V。真实CPU最小程序触发EX load/store地址与紧邻分支/取指、同沿接续与异常，保持当前Camera/PP/CNN集成、036桥和034快ACK/load寄存；CPU未修改，不例行ISA。

封存运行时依既有include闭合/真实IP/GTP_GRS要求，记录所有最终输入与脚本哈希和完整命令/日志/轨迹；首败保留停止，测试问题交Sol，RTL问题用最小证据定位。不提前记037功能/板测PASS，不因本轮改动追加物理DDR全套。
