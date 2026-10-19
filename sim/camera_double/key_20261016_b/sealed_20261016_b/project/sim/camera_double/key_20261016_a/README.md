# ABI2精简关键测试冻结组

用户已确认本版时序/位流，准备与执行分工：Sol写全部输入与检查器并封存，DeepSeek仅执行，Sol核原证据。**未执行DUT功能仿真**，无新双缓冲PASS。输入清单`inputs.json`、封存`sealed_20261016_a/`、唯一运行目录`build/ds_abi2_key_20261016_a/`。清单SHA以交接顶部和`run.py --check-inputs`输出为准，不在自身输入文档内造成循环哈希。

只有unit和soc两项功能job，分别跟独立check，不重跑SCCB错误集、CoreMark、ISA、物理DDR或7200秒720p长仿真。正常SCCB电气模型仍用于两组配置；只在测试参数中加速配置延时。模拟DDR原生x32/256bit、4字节地址单位，不是标准AXI4/PHY。异步PCLK=14.274ns、core周期10.666ns，输入沿PCLK下降沿驱动，输出数据逐字节/地址/CRC独立参考由Python输入图案公式生成，绝不从DUT W反推golden。

unit为64×128、DROP10，512拍/帧，硬件timeout参数CLK_HZ100000以快速测缺PCLK，配置独立1600000；8次正常发布，输入pattern为1/2/3/4/5/7/10/12，序号1..8。覆盖：FREE/WRITING/READY/CPU，错token、重复CLAIM、READY直接RELEASE、非法位宽/地址/SELECT/strobe/组合命令和无副作用；两CPU块占满跨三完整DVP帧、WAIT与元数据保持、中途释放下一个完整帧恢复；发布与释放另一块同沿；STOP与auto分配竞争、扣最终W不早发布、STOP排空；ABORT公开AW/W排空保留另一CPU块、短帧、自然FIFO溢出、缺PCLK、复位清除CPU＋WRITING所有权。原生同拍/分离AW/W、数据稳定、背压均须实际触发。真实data/inst译码器另做132个地址/所有权/读写/busy组合，覆盖A/B有效末字节/保留末字节、窗口外、未领取读、CPU写及取指禁止、旧单帧权限。

soc为真实soc_ddr3_top/CPU/缓存/互连/桥/Camera，64×8、32拍/帧、DROP10、配置1600000，其余CLK参数不变；同一C镜像目标4次校验，STOP在途尾帧若已分配则第5次也完整校验。CPU在A/B复用前后均读每个字；每发布必须有256次CPU load及256个原生AR/R，直接证明两块no-hit/no-fill；每块新内容/CRC/序号独立检查。必须有CPU读一块时另一块真实DMA W落在其AR/R之间，AW双方同时请求与原生背压/同拍/分离均非零，禁止只看BUSY或串行两次CRC。模拟B及占满时丢弃帧的行间空白加长以保证并发和中途释放刺激，像素/行几何和完整帧不变。同步使用真实UART RX线输入令牌1/2（115200/814clk每bit），CPU通过真实MMIO接收，不用可被缓存的外部DDR邮箱；非帧写竞争地址4001C000。不force设计状态或绕过总线。

证据：unit.log（MMIO/AW/W/STATE/START/EDGE/PUB/CASE/COVER）、cpu.log（真实CPU入口退休/LOAD/发布/状态/报告/占满区间/竞争）、bus.log（原生AW/W/AR/R），每job独立DVP输入像素/帧日志、原始stdout/transcript/完整命令/native退出码/超时/耗时、独立checked.json、三个输入副本/递归include/厂家原语/初始化参数/工具与INI、Git前后及证据SHA。以真实最终W时刻判READY，不以模型接受AW或CRC上报当写完成。

执行前不构建、不修改、不更换DAT、不重封。目录存在即停，首败保留；即使ModelSim退出0，只要Fatal/Error/FAIL或checker失败都不通过。当前私有INI使用相对`modelsim.ini`，复用此前已核修复。功能job各限300秒墙钟，checker120秒；不自行延长，不在失败目录重试。失败先交Sol分类，测试修复新身份，明确RTL缺陷才提供原证据/最小复现交Astra。
