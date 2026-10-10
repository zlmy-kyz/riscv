# PDS Inserter / Debugger 官方资料研究笔记

日期：2026-10-03。范围：仅第一阶段文档研究。目标环境：PDS 2022.2-SP6.4。

本次仅新增这份资料笔记；没有分析工程 RTL、PDS 顶层和约束，没有修改设计、运行综合或实现、创建 DebugCore 或连接开发板。工程原有未提交内容保持原样。本笔记中的 DDR 信号名称均来自官方 IP 手册，不能视为当前工程已存在的信号或 Probe 路径。

## 1. 文档来源、版本与阅读范围

主要依据是本机 `C:/pango/PDS_2022.2-SP6.4` 内的紫光同创官方文档。安装包版本与手册版本分别记录，不能把每份手册都称为“2022.2-SP6.4 手册”。下面页码统一为 PDF 文件从 1 开始的物理页码，避免与页脚页码混淆。

| 编号 | 文档名称、版本 | 来源 | 本次相关章节 / PDF 页 | 关键结论 |
| --- | --- | --- | --- | --- |
| I | Fabric Inserter 用户手册，V1.0，修订记录 2022-07-12，49 页 | [本机官方 PDF](C:/pango/PDS_2022.2-SP6.4/doc/Fabric_Inserter_User_Guide.pdf) | 术语 p7；软件简介 p8；§2 p9-17；§3.4 p20-39；§4 p40-42；§5 p43-48 | 自动网表插核；保存 FIC 后运行 Map 调用插核；采样、触发、连线配置；ADS 专属 RTL 标记方式 |
| D | Fabric Debugger 用户手册，V1.1，2023-04-24，107 页 | [本机官方 PDF](C:/pango/PDS_2022.2-SP6.4/doc/Fabric_Debugger_User_Guide.pdf) | §1-3 p9-16；§4 p17-24；§5.1-5.4 p25-40；§5.12-5.14 p71-73；§7 p105-106 | JTAG Server / Cable / 扫链 / 下载；Run、强制触发和波形回读；上电数据读取；软件版本匹配 |
| C | DebugCore IP 用户指南，UG062006，V1.3_i1，2023-06-05，26 页 | [本机官方 PDF](C:/pango/PDS_2022.2-SP6.4/ip/system_ip/ips_debug_core/ips_debug_core_eval/ips_debug_core/UG062006_DebugCore_IP.pdf) | 总体介绍 p7；JTAG Hub p8-11；DebugCore p12-25，表3-11 | JTAG Hub 与 DebugCore 是 FPGA 内的 IP；采样时钟和 JTAG 时钟不同；IPC 例化方式及参数 |
| P | Pango Design Suite 用户手册，V1.5，2022-11-18，274 页 | [本机官方 PDF](C:/pango/PDS_2022.2-SP6.4/doc/Pango_Design_Suite_User_Guide.pdf) | §2.4 Tools p41-42；§3.4 p108 起；§3.5 p127-141；§4.7-4.8 p162-163 | 工具入口；实现流程；Setup / Hold / Recovery / Removal / Minimum Pulse Width、Fmax、Clock Interaction、High Fanout 报告 |
| Q | Pango Design Suite 快速入门，V1.1，2022-08-19，31 页 | [本机官方 PDF](C:/pango/PDS_2022.2-SP6.4/doc/Pango_Design_Suite_Quick_Start_Tutorial.pdf) | §5-8 p26-31 | Synthesize、Device Map、Place & Route、Generate Bitstream 的顺序和含义 |
| T | Timing Analyzer 用户手册，V1.4，2022-11-09，26 页 | [本机官方 PDF](C:/pango/PDS_2022.2-SP6.4/doc/Timing_Analyzer_User_Guide.pdf) | §1-2 p6-8；§3 p9 起 | 基于指定 Design DB 和约束进行时序分析；约束来源会影响结果 |
| H | Logos 系列产品 HMIC_S IP 用户指南，UG022003，V1.5，2023-04-28，55 页 | [本机官方 PDF](C:/pango/PDS_2022.2-SP6.4/ip/system_ip/ipsxb_hmic_s/ipsxb_hmic_eval/ipsxb_hmic_s/UG022003_Logos_HMIC_S_IP.pdf) | §2.5.3 p37-39；§2.5.5 p45-46；§2.8 p49-51；§2.9 p51-52 | PHY 有软逻辑时钟和高速 IO 时钟；提供训练 Debug 输出；内部位置约束不可改；可通过示例串口调试 |

补充检索：

- [紫光同创官方 PDS 产品页](https://www.pangomicro.com/product/pds/)确认 PDS 覆盖 HDL、位流生成、下载调试的完整流程；该网页没有提供本次所需的 Inserter 详细参数说明。
- 官网检索发现 [HMIC_S 英文指南 UG022003 V1.6](https://www.pangomicro.com/en/uploads/59186237_1711509831.pdf)，但全文打开超时。本笔记的 DDR 具体结论仍以已完整读取相关章节的本机 V1.5 为依据，未将搜索摘要作为操作依据。
- 在仓库检索 PDF / README，并阅读 `ipcore/ddr3/readme.txt`。它说明厂家例程包含串口控制目录，但不证明这些模块已经集成到当前 SoC。仓库内未找到单独的 Inserter / Debugger PDF。
- 搜索中有第三方教程混用 ILA、其他厂商属性和文件类型，未采用为 PDS 操作依据。无需依赖第三方资料即可回答主要问题。
- [尚未从文档确认]：独立的 SP6.4 Inserter / Debugger 变更说明，以及本机每个 GUI 控件是否与手册截图完全一致。后续实际操作时使用本机 Help 和 About 复核。

## 2. 必答的 15 个问题

### 1）Inserter 是什么？

Fabric Inserter 是配置并自动把 DebugCore 插入用户设计网表的工具，输出含调试逻辑的新网表，通常不需要用户手工在 HDL 中例化调试核。它结合 PDS 使用，读取 PDS 提供的设计和器件信息。（I p8-10、20）

### 2）Debugger 是什么？

Fabric Debugger 是 PC 端 FPGA 在线调试软件。它与 FPGA 内的 JtagHub、DebugCore 交互，支持位流下载、配置触发、回读采样、波形 / 列表显示和读取调试状态等。（D p9、25-26）

### 3）DebugCore 是什么？

DebugCore 是在 FPGA 中实现的采样、触发和存储 IP。用户逻辑连接至它的触发端口、数据端口和采样时钟端口；它通过 JTAG Hub 与芯片 JTAG 接口通信。JTAG Hub 使用 Fabric 资源，可以连接最多 15 个 User Unit APP，例如 DebugCore。（C p7-9、12-13）

### 4）Inserter 和 Debugger 的关系？

Inserter 决定并构建调试硬件及 Probe 连线；Debugger 在这份硬件已经编入位流并下载到 FPGA 后使用它。两者之间通过对应的位流和 `.fic` 配置文件保持信号映射一致。

`.fic` 是 Inserter 配置文件，不是 FPGA 位流。导入与位流对应的 FIC 可以恢复 Trigger / Data 名称和总线；不能拿旧 FIC 给新 Probe 布局命名。（I p17、27；D p15）

### 5）Inserter 在编译流程哪个阶段使用？

网表方式使用设计网表作为输入；手册将输入称为 ADF。保存配置、退出 Inserter 后，回到 PDS 执行 Flow 的 Map，PDS 自动调用插核流程。因此文档支持的定位是：基于有效输入网表配置，在 Map 流程衔接插核，再进入映射与布局布线。（I p10、17）

另有 ADS 配合的 RTL 标记方式：在 RTL 中使用 `PAP_MARK_DEBUG` 标记；打开 Inserter 前 PDS 自动执行 Synthesize 等操作。这是另一种入口，不能混同为“综合后随便都能找到 RTL 原名”。本阶段未采用或修改任何 RTL 标记。（I p40-42）

### 6）插入后需要重跑哪些步骤？

| 步骤 | 文档能确认的结论 |
| --- | --- |
| 原设计 Synthesize | RTL 标记方式明确会执行综合。修改 RTL 或输入网表已失效时，需先得到有效输入网表。仅改变网表插核的 FIC 是否一律需要手工重跑原设计 Synthesize：[尚未从文档确认]，不能笼统宣称必需或不必需。 |
| 插核流程 | 保存 FIC、退出 Inserter，执行 Map，PDS 自动调用。不是 Save 按钮本身已经完成插核。 |
| Device Map | 需要让含调试核的新网表进行映射。I 明确要求运行 Map。 |
| Place & Route | 含新逻辑的新设计需要布局布线，不能继续使用插核前的实现结果。（I 与 Q 的流程推导） |
| Report Timing / 资源报告 | 应检查含调试核的新实现，不能引用旧结果作为新设计验证。（工程验收要求；报告项目见 P） |
| Generate Bitstream | 需要生成并下载含调试核的新位流。（C p25；Q p31） |

还应区分运行期修改：Debugger 的 Trigger Setup 可以在线修改匹配值、触发逻辑、采样窗口及触发位置，不用重新编译；仅能在已生成硬件支持的能力内修改。更换 Probe、时钟、总存储容量或硬件触发能力属于另一类变化，需重新实现。（D p30；后半为硬件配置与运行寄存器区别的推导）

### 7）Sampling Clock 如何选择？

官方定义：Clock Port 同时是 DebugCore 工作时钟和采样时钟。IP 接口中的 `clk` 是用户提供的触发采样时钟；`drck_in` 是来自 JTAG Hub 的 JTAG 时钟，两者不同。Inserter 的 `Sample On` 支持 Rising / Falling。（I p7、24、26；C p13）

工程建议：按观测信号的真实时钟域选择稳定、运行中的设计时钟，并使被探测路径在所选采样沿满足时序；优先同域观测。不能把下载器 TCK 频率当成采样频率，也不能只因某个参考时钟频率合适就把它用于其他域。

Debugger 的 `Hardware Sample Rate` 用于计算波形时间测量值。它不是改变 FPGA 实际采样时钟的控件。（D p71 的描述与 C 的时钟接口推导）

[尚未从文档确认]：所有器件和配置通用的 DebugCore 最大采样频率、最小频率、停钟后全部状态行为；应以具体实现时序与本机软件为准。

### 8）Data Signal 和 Trigger Signal 有何区别？

Trigger Port 的信号参与触发条件判断；Data Port 的信号是实际存储和显示的来源。只接 Trigger 而没有参与 Data 捕获的信号，不能据此认为会出现在波形中。（I p7）

`Data Same As Trigger` 可把勾选 `Used As Data` 的 Trigger Port 信号同时用于 Data；启用时不能另外向 Data Port 添加独立连线。需要少量触发位、更多观测位时，可以关闭此选项，分别连接 Trigger 与 Data。（I p23-24）

### 9）Trigger Condition 如何设置？

分两层：先为 Trigger Unit 设置 Function、Value 和需要时的 Counter；再用一个或多个 TU 组成 Boolean 条件或 Sequencer 条件。（I p31-34；D p30-35）

- Boolean：使能所需 TU，可做 AND / OR、单个 TU 取反或整体取反。Debugger 正文有 `Add Equation` 的拼写，但图5-10实际是 `And Equation`，已核对截图。
- Sequencer：按 Level 顺序等待匹配，可选择是否必须连续匹配；最大级数受生成硬件参数限制，文档上限 16。
- Counter：支持禁用、恰好 N 次、至少 N 次、连续至少 N 次；计数能力受创建核时的 Counter Width 限制。
- 在支持边沿的 Match Type 下，二进制 Value 支持 R / F / B / N 和不关心 X。边沿判定基于数字采样，不能据此测量 DDR 引脚的模拟质量。
- Debugger 可保存多个 Trigger Condition，但一次只有一个 Active。（D p32-33）

这里只说明官方能力，不为当前工程虚构 TU 对应的信号或触发表达式。

### 10）Sampling Depth / Trigger Position 是什么？

`Sample Depth` 是硬件采样存储的深度，I p24 给出的范围为 64~131072；不代表该范围内所有整数都可选。具体离散值由当前 GUI 确认。

运行时 `Capture Settings` 中的 `Depth` 是每个窗口的深度，不能与总 Sample Depth 混淆。Windows 模式每窗口深度为 2 的幂，`Position` 是触发点的采样索引，范围 `0 <= Position <= Depth - 1`。N Samples 模式的触发点是每个窗口第一个采样点。（I p35-36；D p36-37）

例如一个 1024 点窗口、Position=512，可理解为触发点位于第512索引，便于观察事件前后；具体预触发有效数据、启动填充等实现细节：[尚未从文档确认]。

关闭存储过滤且连续等间隔采样时，时间窗口约为“点数 / 实际采样频率”（通用计算）；启用 Storage Qualification 会过滤数据，不能将所有相邻存储点自动解释成相邻时钟周期。总容量还受窗口划分限制。（I、D 的存储条件定义与通用推导）

### 11）Debugger 如何通过 JTAG 获取结果？

PC Debugger 通过 TCP/IP 连接 JTAG Server，选择 Cable 与 TCK，经下载器访问 FPGA JTAG；JTAG Hub 选择对应 DebugCore。`Run` 把当前触发设置写入核，条件成立后按 Capture Settings 捕获；缓冲区填满后数据回传到 Debugger，显示在 Waveform / Listing。（D p12-15、26、35；C p7-9、13-14）

这是 FPGA 本地采样再回读；不能把 TCK 当成用户逻辑采样速度。

手册已确认的按钮是 `Run`、`Stop Acquisition` 和 `Trigger Immediate`。`Run` 对应设置并启动等待触发的用途；单独名为 `Arm` 或 `Capture` 的按钮：[尚未从文档确认]。不把其他厂商按钮名写成 PDS 步骤。

`Trigger Immediate` 忽略触发和存储条件，以单窗口、sample0 触发方式填满 buffer；它不保留正常条件触发的窗口语义。（D p26、35）

### 12）会增加哪些 FPGA 资源？

DebugCore / JTAG Hub 增加 Fabric 调试逻辑；触发比较、计数、控制及采样会消耗逻辑和寄存器资源；采样存储可选择 Block RAM 或 Distribute RAM，因而增加对应存储资源和连接布线。Inserter 有 `Core Occupancy (Estimated)` 估算窗口。（I p18、20、24；C p8、17）

数据缓冲原始容量约为“Data 位宽 × Sample Depth”bit，不包含控制、对齐和 RAM 分块损耗。最终数量以含核实现的 Resource Usage 为准。增加采样位宽、深度、TU 数和计数器宽度一般会增加资源，这是工程推导，不能替代实现报告。

[尚未从文档确认]：固定 LUT / FF / RAM 增量、每核是否必然需要新增 PLL / 时钟 Buffer；本阶段没有生成核或测量资源。

### 13）会改变原来时序吗？

可能。I p24 明确指出 Enable Multi-windows and NSample 会影响 DebugCore 时序，高频工作不建议启用。C p17 的 Area speed 参数也说明速度和逻辑资源之间存在权衡；该参数属于 IPC 页面，不能直接假定 Inserter 有同名选项。

工程推导：Probe 增加被观测网线负载和 fanout；核占用资源后可能改变 placement、routing 和 clock 负载分布。因此原设计路径和调试核自身都要重新检查，没有“插核后仍保持原时序”的保证。

P §3.5 明确提供 Slow / Fast Corner 的 Setup、Hold、Recovery、Removal、Minimum Pulse Width，以及 Fmax、Clock Interaction 和 Clock Network。Fmax 不计跨域路径，只能作为性能参考，不能独立证明时序收敛。（P p130、134-139）

### 14）多时钟域如何处理？

已确认：一个 DebugCore 的采样接口是一个 `clk`；可以放多个 DebugCore。Debugger 支持同一器件多个核单次采集；同一时间最多一个核连续触发。（C p7、13；D p73）

[尚未从文档确认]：Inserter 自动同步异步 Probe、自动保障跨域总线一致性、不同域核的共同时间轴 / 精确同步触发，以及所有采样输入内建同步器。不能假定工具自动解决 CDC。

工程建议：不同域分别设核，优先观察设计中已有的同步后状态和握手边界。用某域时钟直接采另一域的短脉冲可能漏采，多位总线可能出现不一致快照；“同时点击启动多个核”不等于采样周期对齐。本阶段不为此修改 RTL 或添加同步器。

### 15）哪些 DDR3 / PHY 信号不适合直接探测？

官方 H p50 区分软逻辑系统时钟 `ddrphy_clkin` 与快速 `ioclk`，并明确内部模块位置约束需要与 IP FDC 一致、位置不可更改；p51 提醒优先布线 RCF 的加载。I p26 还写明与用户设计端口相连的信号存在无法连接观测的限制，实际可选网线需以当前 Inserter 为准，不能承诺任何 RTL 名称都可探测。

工程建议，非官方“全面禁止 PHY”的清单：

- DDR 双向 DQ、差分 DQS、CK 等引脚侧信号不适合用普通低速 Fabric 采样来验证眼图、信号完整性或 DDR 双沿数据。
- 高速 IO 时钟、DQS gate、DLL / delay、serializer / deserializer 和专用原语内部节点，不作为首轮直接 Probe；可能不对 Fabric 网表开放，或涉及专用路由和特殊时序。
- 不能把异步或高速节点接到无关采样时钟后把采样结果当作完整 PHY 时序。

[尚未从文档确认]：PDS 对全部 PHY 原语内部节点的可探测 / 禁探清单及每个节点的实现限制。不能说“所有 PHY 信号都禁止探测”。

官方提供了可读的训练调试输出，如 `debug_data`、`debug_calib_ctrl`、`debug_slice_state`、`dll_lock` / `dll_step`，详见 H 表2-19、2-22~2-24；还给出初始化完成等关键指示信号和 Example Design 串口调试方法。（H p39、45-46、51-52）

这些是“官方接口类别”的参考，不是当前工程 Probe 表。是否启用、是否接出、实际名字、层级路径、位宽和时钟域，留给第二阶段按本工程核对。调试输出与会改变 training 行为的控制输入必须分开，不使用控制输入去改变原设计。

## 3. 已查证的 GUI 流程参考（本次没有执行）

本节是文档流程索引，不是已创建 DebugCore 的记录。每一项若后续实际执行均需人工操作。

| 次序 | 手册确认的操作 | 依据 / 待确认事项 |
| --- | --- | --- |
| 1 | [需要你手动操作] PDS Tools 的 Inserter，或双击 Constraints 中的 FIC | P p41；I p9-10。打开前需有设计资源和有效输入网表。 |
| 2 | [需要你手动操作] JtagHub 页添加 `New DebugCore Unit`，核对 Boundary Scan Chain / Select Jtag | I p21-22；Default JTAG 与通过 GTP_JTAGIF 的 USER JTAG 区分。当前板卡选择尚未核对。 |
| 3 | [需要你手动操作] Trigger Parameters 配置 TU 数、类型、存储、Sample On 等 | I p23-24；所需能力必须在硬件阶段生成。 |
| 4 | [需要你手动操作] Net Connections → Modify Connection → Select Net，连接 Clock、Trigger 和 Data | I p25-30；用真实网表信号。可选 Reset Port 为低有效，需正确连接或保持不启用。 |
| 5 | [需要你手动操作] 如需抓启动瞬间，在 PowerOn Init Parameters 启用并设置初始触发和 Capture | I p30-36；本阶段未设置。 |
| 6 | [需要你手动操作] Save Project 保存 FIC，退出后在 PDS 执行 Map，再 P&R、检查时序和资源、Generate Bitstream | I p17；Q p28-31。原设计综合的依赖按第6问区分。 |
| 7 | [需要你手动操作] 给板卡供电，连接合适下载器、JTAG 及 VREF，核对驱动 | D p9-11；引脚接法以实际下载器说明和板卡文档为准，本阶段未确认硬件。 |
| 8 | [需要你手动操作] 打开 Debugger，Connect to server，选择 Cable / TCK，Search JTAG Chain | D p12-15、22。不臆定本板可稳定工作的 TCK 数值。 |
| 9 | [需要你手动操作] Configure Bitstream File 下载新位流，导入对应 FIC | D p15；可自动搜索位流目录及上层的同名或 `_trs.fic`，仍需核对对应关系。 |
| 10 | [需要你手动操作] Trigger Setup 设置 Function / Value / Counter、Active 条件、Capture Settings | D p30-37；在已生成核能力内在线调整。 |
| 11 | [需要你手动操作] Data Ports → Add All to View → Waveform / Listing，或选择部分信号添加 | D p27-29；没有 Data 捕获连接的 Trigger 位不能靠显示菜单补采。 |
| 12 | [需要你手动操作] 点击 Run 等待条件触发，再查看返回波形；必要时 Trigger Immediate | D p26、35。Arm 的对应按钮：[需要在当前PDS界面确认]，手册采用 Run。 |
| 13 | [需要你手动操作] 依据采样率、索引、触发标记和总线位序分析 | D §5.4、§5.12。时间测量依赖 Hardware Sample Rate 设置。 |

### 启动 / DDR 训练数据的重要区别

通过位流预置的上电采集可以捕捉软件尚未连接时的启动事件。Debugger 用 `Show Power on Initial Data` 读这份数据；一旦执行 Run、Stop 或 Trigger Immediate，上电数据会失效。（D p26）

工程建议：如果要看首次 DDR training，应先考虑上电采集是否满足所需事件窗口；连接 Debugger 后才启动普通 Run，可能已经错过训练。复位是否会重新训练、是否同时复位 DebugCore，以及训练时采样时钟何时可用：[尚未从文档确认当前工程行为]，留给第二阶段。

### 常见异常不能直接等同设计功能错误

- 全部 channel 为 0：官方建议检查复位约束和时序违例。（D p105）
- Waiting for trigger 且提示核处于 reset：官方建议检查时钟源和时钟引脚约束，同时核对核的 Clock / Reset 连线。（D p105-106；I p26）
- 软件与 JTAG Server 版本不匹配：官方说明不允许通信。（D p73）

## 4. 参数上限与文档差异

I 已确认的上限：最多15核；每核最多16 Trigger Ports；每Port最多256位；所有Port的TU合计最多16；Data最多4096位。上限不能证明当前器件资源足以同时使用所有最大值。（I p8、23、26）

需要谨慎的差异：

1. C p17 的 Sample Data Depth 选项列表有重复、且范围表述与 I p24 不完全一致。实际可选深度标记为 [需要在当前PDS界面确认]，不自行补全缺失选项。
2. C p17 对 Data Same As Trigger 写了总宽度不超过256bit，而 I 同时描述多个 Trigger Port 和 Used As Data。该模式跨Port的实际总宽度限制 [尚未从文档确认统一结论]，须在本机生成配置中核实，不能直接乘出4096bit作为已验证能力。
3. C p23 对窗口数写为2的整数幂，I / D 相关正文写正整数并由深度联动。实际可用窗口数以本机 GUI 校验为准；首轮单窗口可避免这项歧义。
4. IPC 手册的 Area speed、Trigger Output Port 等名称不能自动搬到 Inserter 页面。GUI 名称按所属工具分别引用。
5. Debugger 中匹配值、窗口参数可在线调整；硬件总深度、连接关系、类型能力不能因为出现在线 Trigger Setup 就认为都可任意变更。

## 5. 插核后的时序与资源复核原则（未执行第五阶段）

文档已证明 PDS 能提供相应报告；实际比较留到将来插核后，当前不生成时序结果。

- 同器件、同约束、同速度等级及可比实现设置，保存插核前后报告和位流 / FIC 对应关系。
- 比较 Slow / Fast Corner 下的 Setup、Hold、Recovery、Removal、Minimum Pulse Width，Fmax 和跨域 Clock Interaction；同时检查 no_clock 等约束覆盖。
- 比较 High Fanout、Clock Network、逻辑 / RAM 资源、关键路径 Logic Delay / Route Delay。Inserter 估算不代替最终 Map / P&R 用量。
- 若恶化，优先缩小采样位宽 / 深度 / 触发能力并分析负载、资源占用、布局、布线和时钟变化；不把添加 false path、删除或改动 DDR PHY 约束作为通用解法。
- 保留 HMIC_S 官方要求的内部位置和必要路由约束。（H p50-51）

## 6. 本次复现与实测边界

资料检索示例（PowerShell，只读）：

```powershell
rg --files 'C:\pango\PDS_2022.2-SP6.4\doc'
rg --files 'C:\pango\PDS_2022.2-SP6.4\ip' -g '*.pdf' -g '*readme*'
rg --files doc ipcore -g '*.pdf' -g '*README*' -g '*readme*'
```

使用本机 bundled Python 的 pypdf 提取全文，按 PDF 物理页核对上述章节；使用 pypdfium2 渲染并视觉核对 Inserter 采样设置、Debugger Boolean 和 Capture Settings 截图。提取文本和截图位于 Codex 本次会话的 visualizations/pds_research 缓存，未向工程写入这些中间文件。

实测效果：找到了本机官方 Inserter、Debugger、DebugCore、PDS 流程、时序与 DDR 指南；完成核心参数及操作名称核对。没有硬件采集结果、生成核结果、插核资源测量或插核后时序结果，不作板级成功结论。

尚未覆盖：当前工程真实 Probe 路径和时钟域、具体板卡 JTAG 接法、下载器稳定 TCK、本工程 DDR IP 版本与指南的对应关系、本机 GUI 与手册差异、实际编译调度日志、跨核精确时间关联、PHY 节点可探测清单。

第一阶段到此结束；第二阶段需按实际 RTL / 网表 / 约束分析工程后再制定 Probe 方案。
