# 任务038：EX重定向冲刷串行排空，定位RUN后零输出

日期2026-10-18。Sol要求/判据，DeepSeek实现并执行测试。本任务是已有失败候选的最小定位，不是新优化或上板授权；不要修改设计RTL、PDS/IP、成功镜像、PC超时/验收口径，不执行PDS/串口/Git提交推送。任务文件不会自动调用DeepSeek。

## 已知输入与真实失败

- 新增第二次原始失败：`sim/cpu_ex_redirect/board/new_bit_0615_300_01/performance_300.json`，06:15位流本地SHA`2ad9a50b…7afcf4b`；123完整应答/VERIFY/唯一RUN全部逐字节核过，40.049121秒应用RX=0，V未运行。见`sim/cpu_ex_redirect/board/failure_review_20261018_02/failure_review.json`。其PNR网表与03:59版逐字节相同、CPU同一冻结EX身份，本任务输入及最小定位范围保持。附加identity.json为空系入口元数据ROOT错误，已修工具但不倒填原证据；实际应用日志独立记录本地位流与固定BIN身份，勿把元数据修复当CPU根因。
- [原P300失败](../sim/cpu_ex_redirect/board/ex_redirect_reviewed_300_01/performance_300.json)：123RVLD应答全部逐字节/CRC核过，VERIFY和唯一RUN均成功，应用40.04654949999531秒RX=0；V未开始。见[失败收据](../sim/cpu_ex_redirect/board/failure_review_20261018_01/failure_review.json)。不能写为CRC失败、PING失败或正常多1拍分支耗时。
- 位流仍为封存03:59 EX候选SHA`0e15e517…b2b9d94`，93.75MHz/WNS+0.609ns。该候选时序已通过，本定位可针对其冻结副本动态复现；不重跑PDS或物理DDR全套。
- **必须用冻结EX CPU**：`sim/cpu_ex_redirect/board_review_20261018_a/observed/candidate_cpu_from_HEAD.v.txt`，SHA`ef6bfec7853f6b0e93f976c7038ad25cdb4f6e04b14251331fdbf79906cc87e6`。任务建立后用户要求用最新CPU，主工作树现已恢复同一EX身份；仍从上述冻结副本封存，不依赖可变主文件。旧ID对照使用`sim/cpu_ex_redirect/board_review_20261018_a/observed/myriscv/mycpu_sync.v`，SHA`b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3`；禁止混淆两版或为测试覆盖主文件。
- 首选静态缺陷：EX跳转同时或更早周期，年轻ID的CSR/FENCE/WFI可启动FLOW_SERIAL_DRAIN；跳转冲刷ID后，flow_state未撤销排空，而serial_issue要求ID仍有serial_candidate，故可能永久等空令牌。
- 固定P300已有真实触发形态：`program.bin`偏移0x120为`104080e7`（PC0x40000120的JALR到trap_dispatch），紧随PC0x40000124为`34151073`（CSRW MEPC,a0）。它位于BSP trap probe路径，可能在应用首次UART输出之前执行。必须以轨迹确认触发，不能把静态推断写为实板根因已证实。

## 实现一组最小定位

产物置于`sim/br_ex_redirect/serial_drain_20261018_a/`下新开发/封存/运行目录，首败或预期缺陷复现都原样保留。可复用既有汇编/模型框架，但新TB/模型/输入清单另存，不覆盖原成功/失败目录。正式运行前核封存副本递归include闭合，CSR头文件、所有被编译模块/乘法替身均登记SHA，禁止偷偷从主工作树补依赖。

### A：真实一拍指令命中，EX跳转同沿年轻ID串行指令

构造已知必taken的branch/JAL/JALR，顺序下一条放CSR（优先CSRW MEPC/a0或无副作用mscratch），目标写唯一完成标志并进入自环。目标不返回时，顺序CSR属于错误路径，不得发射/写CSR/阻塞目标。最小组覆盖CSR、FENCE，WFI若使用则按现RTL支持语义检查。检查与普通ALU顺序下一条对照。

**指令模型必须复现实际ROM/I-cache hit的一拍合同**：E接受地址、E后valid/data对应它，E+1消费旧响应并允许同沿下一接受；不能沿用“E接受→E+1才将rsp_valid置1→E+2才消费”的两拍模型，后者可能根本没有EX分支与年轻ID串行重叠。无组合零拍响应。提供实际fire、返回、ID/EX驻留周期见证，未触发则INCOMPLETE，不算PASS。

两版运行同刺激：冻结EX应按独立架构参考完成；若它进入SERIAL_DRAIN无法完成，报告**EXPECTED_BUG_REPRODUCED**并列第一分歧周期，不能把失败候选的死锁作为功能PASS。旧ID对照用于证明程序/模型有效，至少完成同一最小CSR用例；这不是重跑历史ISA全套。

### B：先进入SERIAL_DRAIN，之后EX跳转才解除等待

在更老MEM load等待期间，让EX中的taken分支和年轻ID中的串行指令共存，先真实观察排空状态被年轻ID启动；延迟返回老load，随后分支推进/重定向并冲刷ID。目标仍须能继续，不能永久停SERIAL_DRAIN。I侧使用上述一拍命中，D侧延迟至少覆盖这一驻留关系。

此例必须实际触发`flow_state==FLOW_SERIAL_DRAIN`早于branch_redirect；仅在FLOW_RUN入口加`!branch_redirect`不能修复已进入排空的情况。本任务不允许修改RTL，但定位报告必须指出两类场景的区别，避免后续只修入口条件。

### C：冻结应用的精确启动片段

不跑数亿周期整P300。使用固定P300 ELF/BIN中启动/BSP trap probe到`0x40000120/124`的真实指令与独立架构参考，或据A/B已证明机制构造字节一致的局部调用片段：使JALR目标写标志，再返回，使MEPC CSR在正确路径上恰好执行一次。记录早期JALR重定向时错误路径CSR被取消，返回后正确路径CSR可发射/提交，不能为了避错跳过ECALL/CSR/串行控制。

若首次A/B已复现且C受环境缺口阻塞，保留最小复现及时序见证报告，不扩成整SoC/全量ISA或完整CoreMark；C标记未完成，不把硬件根因写成已证明。无复现时，不臆测改设计；提交第一处覆盖缺口或继续执行下述最小启动轨迹方案要求交Sol确认。

## 必需轨迹和判据

每沿原始CSV/JSONL至少含：cycle、pc、inst_req/ready/fire/addr、响应PC/data、pending/drop/buffer、IF/ID valid/PC/inst、ID/EX valid/PC/branch taken/target、id_fire/id_ex_advance、branch_redirect/redirect_target、flow_state、serial_candidate/issue/done、pipeline_empty、frontend_hold、MEM请求/响应、WB提交PC/inst/rd/value、异常/IRQ事件、目标完成标志/CSR写入。

独立参考按架构指令流生成提交序列/期望CSR和标志，不用DUT内部控制作为oracle；内部信号仅证明触发和第一分歧。错误路径串行指令不能产生CSR/FENCE副作用，也不能改变控制状态导致目标停顿；合法串行指令完成仍保持原语义。请求接受=响应+复位取消+在途，错误路径已接受取指只丢弃而不消失。

仿真采用有限周期超时用于判停滞，保存超时前完整轨迹。报告明确：A/B各场景触发次数与周期、EX和ID结果、第一分歧/停滞状态、精确编译/运行命令和退出码、输入哈希、模型延迟合同、已覆盖与缺项。预期缺陷不能只写PASS；零warning也不能替代上述实际见证。乘法替身仅在这些无MUL微程序中使用，不据此验收真实乘法IP。

本组不追加随机ISA/旧P/V/物理DDR。若后续Sol/Astra修了CPU，才按该修复的新身份及用户PDS顺序安排最小复验和必要CPU行为抽测；本任务不自改设计、不降判据。
