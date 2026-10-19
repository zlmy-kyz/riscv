# 任务040：ID→EX重定向与错路取指占用的最小动态归因

日期2026-10-18。用户在静态分析后明确“进行下一步”。本任务由Sol规定范围/参考/判据，DeepSeek实现测试、封存并执行；**仅量化当前039，不修改设计RTL或预先选定优化**。不是040新RTL功能验收，不重跑PDS、实板、P300/V300、全量ISA/IRQ/物理DDR。本任务文件不会自动启动DeepSeek。

## 目的和已知边界

039已恢复EX redirect当拍目标提交，实板P/V应用通过，耗时2.564868672/2.565809173秒，比06:47 EX版本缩短约5.4%，仍比036慢约6.1%。OTHER相对036约增加一次redirect数量，但OTHER包含正常执行，不能直接作为空转或可省周期。

要回答：ID实际发射taken分支到EX实际redirect之间有多少等待？其中哪些是更老MEM/异常资格所必需？分支发射前/同沿/之后接受的顺序错路I是否占据唯一pending，真实推迟了目标接受？目标进入ID后正常处理和停顿如何区分？本任务输出机制和微程序下的周期归因，**不能外推固定P/V的占比或保证下一RTL收益**。

现有`sim/br_ex_redirect/tb_br_ex_redirect.v`默认延迟1实际上E接受、E+1 NBA置rsp_valid、E+2消费，不能直接称一拍命中；038的`tb_serial_drain.v`已有真实一拍I模型可参考，但其TR行把`id_taken/bj_pc`放在标成idex的组里，实际不是已寄存的EX taken/target，还缺pending PC/响应身份且只打印前40周期。不能直接用旧文本得出当前039五阶段时间或错路归因。新记录必须明确区分ID组合字段与`id_ex_br_taken/id_ex_br_target`。

## 固定输入

- 当前CPU039 SHA256 **`5c26df0229ab00365b2eca1412499f988981fdfe1d1b7292e43a8317f0d47745`**，优先从已有`sim/cpu_ex_redirect/target_fetch_20261018_a/after/myriscv/mycpu_sync.v`取封存输入；主文件应同哈希，但禁止覆盖主文件。
- 静态清单/范围证据：同目录`after_manifest.json`与`review.json`。CPU默认为`BRANCH_FETCH_TURNOVER_ENABLE=1`；不改参数使其变成旧06:47行为。本组只跑这一设计身份。
- 039实板审查与原日志引用：`sim/cpu_ex_redirect/board/review_task039_20261018_01/board_review.json`及其evidence_sha256；只复用，不重跑。旧ID/旧EX不是本组新的完整对照，也不得把旧迹误标当前CPU。
- 功能依赖沿当前regfile/alu/br_alu/l_alu/csr_file及csr_defs.vh，测试可复用既有mul_behavioral，但微程序不含MUL，不据替身测乘法性能。归因OTHER正常执行时也不把所有剩余OTHER误记成MUL。

工作目录`sim/cpu_ex_redirect/id_ex_attribution_20261018_a/`，开发、最终输入清单、封存副本和运行各自分开，首次运行及失败目录不覆盖。

## 一套TB、四组片段

独立参考从固定机器码/初始寄存器与内存生成正确退休PC/inst、rd/value、next_pc和存储标志。参考不读取DUT分支控制。每个正确路径末尾写唯一完成字，并观察其退休/响应完成；错误路径放唯一可识别的写寄存器或store，禁止实际副作用。B/JAL/JALR可在同一短片段串联，目标与顺序地址互异便于配对；不为了覆盖数目造长基准。非taken有自己的正确参考，不能拿它的不同工作量直接当taken提速。

1. **纯一拍I命中，D无额外等待**：E接受I、E+1消费该响应，允许同沿下一接受；绝不组合零拍。给出实际请求ID/采样沿见证，证明taken元数据在id_fire装入ID/EX、正常下一沿redirect，并分离目标接受/交付/发射。至少一次真实看到分支装EX同沿顺序请求接受；若未触发，调整合法程序布局/时序并保留初版，不能伪造内部信号。
2. **仅固定顺序地址慢返回**：使用同一taken微程序，按事先声明的地址/请求序号配置延迟（例如1与8拍两个档）；目标地址保持一拍，其余刺激不变。慢地址位于架构不执行的顺序路径。模型禁止读DUT的taken/redirect来选择延迟，否则形成循环解释。给出该地址实际在branch ID发射前/同沿/之后哪个沿被接受、redirect时是否仍在途、响应返回时如何drop、何时接target。若程序布局未产生错路pending则INCOMPLETE，不能拿全局I延迟作为错路占用证据。这是模型注入延迟，未接真实缓存时不得称真实I miss概率或DDR统计。
3. **更老MEM等待**：独立于load结果的taken分支在EX等待老load完成，I仍一拍。D分别配置1与8拍，其值相同。记录EX分支驻留和ex_mem_complete，证明这部分等待来自老指令而非年轻ID。将年轻顺序项换成CSR或FENCE作一个最小变体，沿用038正确路径参考，区分SERIAL_DRAIN取消的一拍与I单槽占用；不得省略已发射串行项语义。
4. **非taken对照**：同类条件分支不跳，顺序指令均属正确路径；核正常吞吐与提交，不允许将其顺序请求标成错路。目标地址等于顺序地址的歧义不在本组用作核心证据，若包含则以控制流动态实例判归属，不能单按地址等于target就叫交付。

尽量合并程序和配置，预计约6–8个短运行；若实际需更多，先报告哪个必需触发缺失，不自动扩矩阵。总模型只一个I在途槽，ready必须反映旧响应同沿释放，不能被新请求覆盖丢失旧事务；D按现类SRAM的无response-ready合同。复位在非采样沿解除，避免TB race。需要更复杂SoC/IP实物频次才可下的结论标为未覆盖，本轮不新增真实IP/DDR物理联仿。

## 五个沿与周期关联

每个动态分支实例分配branch_id，至少由复位epoch、branch PC及发射序号唯一标识，不只按PC（循环同PC会重复）。以沿前稳定值定义handshake/推进；如另记沿后值，另设phase字段，不将NBA后新寄存器当本沿旧响应归属。

| 事件 | 必需条件/身份 |
|---|---|
| t0 ID发射 | id_fire、实际B/JAL/JALR、id_taken且无ID异常；此时采样PC及最终target |
| t1 EX redirect | id_ex_pc/指令及注册taken/target属于同一实例，ex_br_redirect成立 |
| t2 目标接受 | target对应的inst_req_valid&&ready，接口唯一request_id；允许t2=t1 |
| t3 目标交IF/ID | 来自buffer pop或旧pending响应，检查旧PC、drop/error、实际装载而非只看地址线 |
| t4 目标ID发射 | 对应动态目标指令id_fire；不是只看IF/ID出现或WB正常退休 |

报告t1−t0、t2−t1、t3−t2、t4−t3；目标可能因更老合法控制事件取消时必须单列取消而非强行算无限等待，基础无异常片段不应发生这类取消。每个t2必须可追到正确的t3/t4，旧wrong-path response不能冒充新target response。

逐沿轨迹含：epoch/cycle/phase、I req/ready/fire/address/request_id、rsp_valid/error/data/对应旧request_id、inst_pending/pc/drop、buffer valid/pc、CPU pc；IF/ID valid/pc/inst、id_fire/id_taken/bj_pc/id_exc_valid/load_use；ID/EX valid/pc/inst/**id_ex_br_taken/id_ex_br_target**/advance/can_advance、ex_mem_ready/complete、data_pipeline_stall、older_fault_for_ex、branch_redirect、target；flow_state/serial_candidate/issue/frontend_hold/fault；D请求/响应数据、WB normal_retire/PC/inst/rd/value/next_pc、正确目标完成标志。必要时列架构oracle序列号，禁止DUT内部控制充当正确性参考。

## OTHER归因与守恒

- 复用实际`simple_mmio.v`里的`cpu_perf_counters`模块或观察其真实分类，采用短ROI起止，不修改分类优先级。明确观测寄存延后一拍，事件E对应的分类不要错配到E+1的流水阶段；分类只用于归因，不作架构oracle。若模块接入阻塞，先报告，不编造OTHER数。
- 输出每沿真实分类及WB retire/id_fire/id_ex_advance。OTHER∧retire、OTHER∧有效正常指令、OTHER∧等待、OTHER∧无可观察推进可以作为**交叉统计**，必须声明可能重叠，不相加伪装互斥分解。即使无推进，也可能是必需延迟，不命名“可省气泡”。
- t0之前、t0到t1之前、t1到t3之前、t3到t4的半开区间边界明确，跨分支重叠不能重复求总损失。按区间报告分类优先级覆盖，解释为什么某个等待记MEM或OTHER。
- 每个I请求：接受=已响应（其中deliver/drop区分）+在途+复位取消；未接受地址变动不算事务。结束前排空或明确在途清单。D接受/响应/副作用/取消同样核，错误路径store不允许有一次fire。正常退休序列/最终架构状态必须与独立参考一致。

## 交付、状态与后续动作

保存全部最终源码/TB/模型/参考/程序/脚本及递归include的SHA和封存副本，尤其csr_defs.vh、IP *_init_param.v依赖；include路径闭合后只从副本编译。真实原语若使用必须有正确顶层GTP_GRS，但本组优先用已声明的纯行为模型。保存完整命令、工具版本、退出码、编译/运行原日志、原始CSV/JSONL及其解析脚本、五事件表和每个断言/覆盖结果，失败保留第一分歧/首个缺失覆盖。

报告四项结论：①无老等待时ID→EX正常最短间隔；②错路占槽是否实际延迟target以及给定片段的周期数；③老MEM/串行控制必需等待；④OTHER与正常执行/各阶段的交叉关系。无法量化的实板占比明确留空。没有证明优化可行前不修改RTL或承诺追回19M周期。

本组是用户授权的下一步归因工作，现有039设计已完成P/V应用板测；不是另一个新RTL版本，不等待新的PDS才开始本组测量。CPU未改，不追加ISA抽测。DeepSeek可按方案编写/封存/执行测试，不能改设计/PDS/IP/成功BIN/UART时限、降判据、上板或Git提交推送；需要方案变化时交Sol。Sol复核原始轨迹后再决定下一单项RTL，仍遵守新RTL→用户PDS的顺序。
