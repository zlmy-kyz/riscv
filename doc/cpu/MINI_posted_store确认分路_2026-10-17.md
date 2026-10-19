# MINI posted store确认分路（任务034）

## 2026-10-17：034固定P/V原证据通过，耗时缩短0.249%/0.227%

用户要求性能分析。本轮离线调用034专用verify，检查成功P/V各123条完整RVLD响应、唯一RUN、零重试、冻结软件身份、完整UART输出/CRC5275与8803、13计数/timer及分类守恒。现行非PDS/FDC输入与034静态清单保持。[审查脚本](../../sim/cpu_store_ack/board/review_20261017_01/review_board.py)、[合并收据](../../sim/cpu_store_ack/board/review_20261017_01/board_review.json)状态`TASK034_FIXED_P300_V300_BOARD_RAW_PASS_HDL_NOT_RUN`。没有打开串口/运行HDL/PDS或修改RTL，不重复测量。

| 指标 | 033 P | 034 P | 033 V | 034 V |
|---|---:|---:|---:|---:|
| cycles | 227882946 | 227315593 | 227937510 | 227420763 |
| seconds@93.75MHz | 2.430751424 | 2.424699659 | 2.431333440 | 2.425821472 |
| CPI | 2.102400 | 2.097166 | 2.103418 | 2.098650 |
| 耗时缩短 | — | 0.248967% | — | 0.226706% |
| 吞吐增加 | — | 0.249588% | — | 0.227221% |

同冻结BIN/同集成033为本轮比较基线。P/V分别少567353/516747周期，即6.052/5.512毫秒；这次观测为小幅改善，单轮未测方差，不能作统计显著性断言。两组不足10秒，不是正式CoreMark成绩；UART显示150是整秒截断产物，真实吞吐约123.727/123.669次每秒。

### 周期变化与实际瓶颈

| 分类差（034−033） | P | V |
|---|---:|---:|
| MEM | −4260288 | −4255301 |
| IF | +2540641 | +2596943 |
| 分支恢复 | +1152294 | +1141611 |
| load-use / OTHER / control | 0 | 0 |
| 合计 | −567353 | −516747 |

退休指令数、branch_redirects和AW均保持，AR各少1，不支持“工作量减少”或“缓存miss明显减少”的解释。MEM分类约减少5.8%，但其减少量的86.68%/87.86%被IF与分支恢复分类增长抵消。当前MEM约30.4%、IF1.9%、分支恢复10.0%–10.1%、load-use3.7%–3.8%。分类互斥且MEM优先，不能把IF/branch增长直接归为其硬件延迟变坏，也不能把MEM减少全部算净提速；可能包含原重叠等待显露及仲裁/相位变化，现13项计数无法拆开。

此前约2.27%的量级假设是“每笔store少一拍全部进入净收益、其他等待不变”。本次净省拍只有写次数约10%–11%的量级，实测说明该假设不成立，不能继续拿它作收益承诺，也不能将这个比例误称ACK快速路径触发率。RTL的确认分路机制仍存在，实板没有逐周期ACK轨迹，触发/掩盖比例需要相关轨迹才可确定。

下一单项优先**静态评估I/D普通缓存命中能否减少串行争用**：033仅允许D miss期间I查询，普通主槽仍D优先、每拍最多接受一个I或D请求。store更早完成后仍可能等取指，值得分析同周期I/D hit机会及CPU单取指缓冲限制。该方向是基于结构和分类迁移的候选，不是已证明根因或035实施授权；先找真实可省的消费边沿，不能直接用IF+branch约12%作为收益预测。load响应寄存为时序保留，现阶段不直接拆除，不修改CPU/缓存容量/队列多项并进。

本轮只更新分析及收据，无需重跑已成功P/V或旧测试。034按用户直接板试指令仍无动态功能仿真验收；本次CoreMark不能扩大为所有背压/复位/异常/Camera并发覆盖。P/V每轮重新配置的操作安排不证明KEY0暖复位问题修复，原问题和失败证据保持。

## 2026-10-17：用户时序通过并明确要求直接板试

用户最新直接要求“时序通过，直接给上板命令”。本轮按该指令准备直接板试工具，覆盖此前本轮动态仿真复核后才给入口的阶段安排；**034动态仿真仍未执行/验收，不继承033功能门、不创建034功能PASS门**。时序通过仅为用户反馈，未独立审查数值。本次只新增PC入口和离线计划，未改RTL/IP/PDS/约束/固定BIN，未开串口或执行HDL。

soc_top保持7e43a9d5…64c2d04、桥保持7ab9d34c…52d933。`run_posted_store_ack_measurement.py`在实际串口前核034 after_manifest的非PDS/FDC输入身份，保持原RVLD报文/5秒读上限/partial_rx_hex证据/无自动重试/冻结软件精确输出与13计数检查；PDS/FDC/位流不作为板测工具门。日志保存task034的静态身份、用户授权与时序反馈、动态仿真NOT_RUN、033同集成对照，不把板试前的软件身份检查称硬件功能验收。两份PlanOnly均123响应/唯一RUN、serial_opened=false，见`sim/cpu_store_ack/board_tool_preparation_20261017_a/ready.json`。

```powershell
Set-Location D:\riscv\RISCV
& tools/uart_loader/candidates/perf_2b/run_posted_store_ack_measurements.ps1 -Port COM9 -LogDirectory sim/cpu_store_ack/board/coremark_store_ack_300_01
```

**P、V每轮都在工具提示时先JTAG重新下载同一个034位流**，再关闭串口助手、KEY0按下释放、等DDR就绪后Enter；这是保留033暖复位问题后的会话初始化安排，不宣称已修复该问题。不重复生成位流或重建BIN，不开Camera/PP/CNN任务。新日志目录不可覆盖；首败停止交回。

固定BIN目录仍`tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/`：P为`performance_300/program.bin`，SHA677ee766…74517d；V为`validation_300/program.bin`，SHA461c635c…11719b，分别15204/15212byte，入口/装载0x40000000。对照033实板P227882946cycles/2.430751424秒、V227937510cycles/2.431333440秒；不足10秒仅工程对比。收到日志后核固定BIN、全部协议/CRC/计数及性能，仿真/暖复位/异常并发未覆盖边界仍明确保留。

## 当前状态

2026-10-17用户在033性能分析后要求“执行下一步”，本对话据此实现单项RTL优化。只修改主`soc_top.v`，静态审查及七配置语法展开完成；**待用户重新PDS实现检查时序，当前不派发动态仿真，也不直接下载跑分**。若时序通过，Sol按下述要求准备关键测试方案，DeepSeek实现、封存并执行，Codex复核原始证据后再给本版板测入口。时序违例先回RTL修复。

## 性能依据与范围

复用[033已核P/V实板收据](../../sim/cpu_inst_hit_overlap/board/final_review_20261017_01/board_review.json)：P227882946cycles/2.430751424秒，V227937510cycles/2.431333440秒，CPI约2.10，MEM分类约32.2%。软件工作量相同，当前Camera集成的DDR数据响应比历史032多寄存一拍；这个级原为隔离D-cache DRM→load前递→ID分支→I-ROM时序路径。不能删除load寄存级来追赶旧成绩。

posted store确认表示写缓冲已接管请求，不携带load数据。本轮只将该确认绕过额外响应寄存级，维持原写缓冲/后端AW-W过程。按每笔DDR写净省一拍且其他条件不变的敏感度估算，约5.18M/5.16M周期，即0.055秒/当前约2.27%；这不是实测收益或硬上界。最终对照应使用当前033同集成P/V，不用032来隔离034收益。

## RTL变化

[soc_top.v](../../myriscv/soc_top.v)追加默认开启参数`DDR_POSTED_STORE_ACK_BYPASS_ENABLE=1`，实际仅ENABLE_DDR、ENABLE_CAMERA、x32及posted写开启时生效。现主板默认生效，无需改PDS文件或外部端口；参数0保留033全响应寄存路径；x16/nonposted仍全响应寄存；Camera关闭仍走原直通分支，DDR关闭路径不变。

在`g_camera_data_rsp_register`中新增寄存位`response_is_posted_store_q`：只在`data_ddr_req_valid && data_ddr_req_ready`边沿锁存当前请求是否属于可快速确认的posted store，复位清0。桥I请求不能更新此位，未接受的年轻D请求不能更新此位。

- 快确认有效为锁存类型与`bridge_data_rsp_valid`之与，不提前于桥确认。
- 快确认不再进入`valid_q`，杜绝下一拍重复响应；load和非posted响应仍把valid/data/error整组寄存。
- 输出valid为延迟响应或快确认。快store返回数据0，error从对应桥响应传递；其余使用寄存data/error。数据选择依据锁存类型，不依据live req_write。
- 本位可保留至下一笔D接受，实际响应仍由bridge valid限定；接续边沿先用旧位消费旧响应，再锁存新请求类型。

桥、互连、CPU、IP、Camera/PP/CNN控制、地址权限及成功BIN均不改。该确认可以早于实际W完成，这是原posted语义；FENCE/MMIO/IRQ等仍使用未改的`ddr_write_buffer_busy`排空门，不能把确认视为DDR落地。

## 逐边沿审查

用E0表示桥接受请求边沿，桥现实现最早在E0后给响应、E1消费（无接受同沿零延迟组合响应）。

| 场景 | 行为 |
|---|---|
| posted store | E0锁类型，E0后桥ACK直接有效，E1 CPU/互连消费；033原本经E1寄存到E2消费，本版省一拍 |
| load hit | E0锁类型为load，E1寄存桥data/valid/error，E2消费；原时序隔离保留 |
| load miss | 等原桥R响应后再寄存一拍，数据/错误/归属不变 |
| store→load接续 | E1消费旧ACK并接受新load；寄存逻辑使用旧store位抑制旧ACK，之后新位为load，正确延迟其响应 |
| load→store接续 | E2消费寄存load并接受新store；该沿旧valid_q清除，新store桥ACK才在边沿后出现，不与旧load响应叠加 |
| store→store接续 | 旧ACK不进valid_q，新store有独立桥接受与ACK；若写条忙，仍按原ready背压/完成接续规则等待 |
| 旧响应error | 仍交互连的error优先逻辑，不能接受跨越旧fault的年轻副作用；当前桥error常0，接口传递规则仍保留 |
| 复位 | 类型位和延迟valid均清0，原桥/互连同复位，不补发或重放ACK |

延迟响应与年轻快ACK互斥依赖**上游单在途事务与桥至少一拍响应**：上游只有消费旧响应时才能接受下一笔请求，下一笔桥响应最早在该接受边沿后出现。若未来改变这些接口约束，应重新设计响应队列，不能原样复用此分路。

没有增加组合自反馈：快ACK仅由旧类型寄存位与桥旧响应状态产生，不依赖当前请求接受。新增valid路径可能改变综合布局和接续路径时序，不能以静态逻辑审查代替PDS。

## 输入身份与静态证据

[准备目录](../../sim/cpu_store_ack/preparation_20261017_a/)保存71项改前输入副本、Git状态、前后清单及本轮soc.patch；除soc_top外70项保持，含033桥、CPU、PDS/FDC、I/D IP、冻结P/V BIN和033总实板收据。

- soc_top改前SHA256：`047cf3ccecbcd002c4b648883e7706d488813e22ba1b37eca8c2ab396c56821a`
- soc_top改后SHA256：`7e43a9d55c04db6372bd906b7e244debd544ae840681146842440d50764c2d04`
- 桥保持033 SHA256：`7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933`
- [静态收据](../../sim/cpu_store_ack/preparation_20261017_a/review.json)：`TASK034_STATIC_ONLY_PENDING_USER_PDS`。

主board_top、x32 Camera启用、关闭本参数、nonposted、x16、Camera关闭、DDR关闭七配置Icarus `-g2005 -tnull -i`展开exit0。真实cache端口封装参与，厂家内部实现及缺失IP视为黑盒；主板两条既有DDR core_clk/ddr_init_done方向提示，不能记完整IP功能通过。未执行vvp/vsim、综合、布局布线或串口。

本轮记录入口为`python -B sim/cpu_store_ack/preparation_20261017_a/static_prepare.py snapshot`与`review`，已经执行，已有快照/收据保护停止；精确argv/cwd/输出在收据与checks_01日志。未编写动态TB/模型/参考或执行脚本。

## 时序通过后的一组关键测试要求（当前不派发）

由Sol确定可执行任务、DeepSeek实现测试，复用033成功输入与厂家IP；编译封存应递归闭合include/初始化文件并提供GRS顶层实例。最小control/key保持同Camera/PP/CNN配置，仅034参数开关不同，不跑旧全套CoreMark/ISA/PHY。CPU未修改，例行ISA抽测0。

必须真实触发并从逐边沿轨迹核定：

1. posted store桥确认→CPU确认由两边沿间隔变为一边沿，且每笔仅一次；load hit/miss的寄存延迟和返回数据保持。
2. store→store、store→load、load→store、load→load接续，未接受请求类型/地址毒化，旧响应不得被新请求类型选错；D接续可同时有I响应，不能污染读写归属。
3. AW背压、AW/W同拍、分离W、旧写完成同拍接新store，确认允许早于落地但写数据/strobe/地址不变；部分字节写/后续转发继续正确。
4. FENCE、非DDR MMIO/UART、IRQ保持写排空；旧fault禁止年轻副作用。当前桥error恒0，如用接口级刺激检查错误传递，须明确其层次，不冒充真实DDR错误来源。
5. 快ACK期间、load待寄存/已寄存期间、后端写尚未完成期间分别复位，精确记录接受=响应+取消+在途，不重放ACK/W。
6. 真实CPU最小程序以独立架构参考核store/load/依赖/排空，所有有效字节和最终内存一致；受控store序列总周期必须减少，不能只以MEM分类减少判提速。

当前没有动态功能PASS、034时序PASS或实板收益。KEY0暖复位后Loader不响应的问题仍独立保留，未因本修改被宣称修复；旧P/V失败/成功证据保持。后续板测仍由用户操作，沿冻结同BIN及新目录，功能复核前不提供直接部署入口。
