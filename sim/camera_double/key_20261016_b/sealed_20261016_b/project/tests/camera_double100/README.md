# ABI 2 双缓冲真实CPU校验程序

2026-10-16。用户已确认本版位流生成且时序正确，Sol不复查PDS/位流。当前阶段为**程序/测试封存完成，等待DeepSeek执行关键仿真及Sol核原始证据**。没有双缓冲功能/实板PASS；单缓冲成功源码、两份BIN和原始日志保持。

固定完整720p程序：`build/abi2_20261016_d/program.bin`，12520字节，SHA256 **4684f0775e3a611588b0ea5df373dbf5b3d6ce94deda175d6c62a0dda72ed4d2**，Loader CRC32 **0901d151**。固定小尺寸真实CPU镜像：`build/abi2_small_20261016_d/program.bin`，4680字节，SHA256 **f46e564f5e85cfb19b856f2b5458718d1d02120cad965efcad9e1a5b91dc8dd0**，CRC **8eefbc51**。两者来自同一main.c；小尺寸用CAMERA_SIM/64×8/4帧，增加真实UART RX输入同步、占满保留两块及非帧DDR写竞争，不以此冒充720p。同步输入经过实际UART/CPU总线，不使用可能缓存的可外部更新DDR邮箱。小尺寸镜像预装DDR，ROM/RAM基址0、复位入口40000000；不修改主ROM/RAM初始化。

共用既有startup.S和linker.ld，不修改旧文件。DDR程序/数据/BSS位于低60KiB，4KiB栈为4000F000–40010000，帧区独立。生成的program.dat只是DDR镜像表示，不能替换ROM/RAM DAT。ABI必须ID=43414d02；A=41000000、B=41200000。真实CPU等待最旧的下一个SEQ，SELECT→读取冻结元数据→写EXPECTED_SEQ→CLAIM→确认CPU所有权→读完整帧计算IEEE CRC→核元数据稳定→恢复SELECT/TOKEN→RELEASE。允许另一块DMA期间BUSY=1；不能沿用ABI1的STATUS=5判据，禁止CPU写帧区。不force、不清Cache或伪造CRC。

完整程序持续流校验100帧，每帧仅打印BUFFER、SEQ、采集CRC/CPU CRC及MATCH、ERROR、等待/读校验ticks和WAIT_CYCLES。相同CRC合法，用户中途改变画面；不逐帧导图或PC重算原始帧CRC。第100帧领取后STOP，已分配的另一块可能还会正常发布；该尾帧也完整CLAIM/CRC/RELEASE，以DB_TAIL单独打印、不计入主SUCCESS=100，最多一帧。最后要求流已停、不BUSY、两块FREE、GLOBAL_SEQ与全部已处理序号一致，才输出DB_END并锁存PASS；不会静默丢弃READY。

首流仍丢10个预热帧，后续同流跳过重复预热。等待5秒、CPU完整校验20秒、STOP排空25秒超时；RTL原3秒超时不改。计时使用93.75MHz CYCLE软件扩展64位，CPU每256个字采样。失败立即停止，保留缓冲/SEQ/token/metadata/CRC/状态/错误/等待计数/已成功数诊断；不自动清错、ABORT、RELEASE或重试。PC每行30秒超时保留原始RX/TX，不能保证CPU或总线彻底无响应时固件还能输出诊断。

PC工具为`tools/camera_uart/double100.py`，复用现有Loader整BIN VERIFY/唯一RUN，固定完整BIN对应101个Loader应答，应用READY后只发单G。新日志目录、固定BIN/manifest/原始收发/逐帧CSV/报告均保存，独立检查器逐字节复核原始流，合成证据不能冒充实板。**本阶段不提供串口实板执行命令**；工具在打开串口/创建运行目录之前要求Sol核关键仿真后生成绑定此BIN的board_release.json，DeepSeek无权创建或修改该放行文件。关键测试原证据核过后由Sol给用户命令，PDS/下载/KEY0仍由用户负责。

可用只读入口（不打开串口）：

```powershell
python tools/camera_uart/double100.py --plan-only
```

正式DeepSeek入口见`DeepSeek/双缓冲ABI2_精简关键测试_2026-10-16.md`，只执行冻结的run.py，不构建或重封。48源54模块完整ModelSim编译Errors0/Warnings0，RV32I ELF/BIN/布局/栈审计和主机离线正反检查通过，仅证明准备状态。初次C构建a因Werror缩进被拒、初次静态编译a因模型字面量与问号连写被拒，原目录保留，修复只在测试侧；b/c为中间构建，静态审查修正同步方式后最终使用d，不覆盖旧输入。Icarus全IP空展开因既有厂家表达式的无定宽拼接失败，记录保留，不改IP；忽略未展开IP的SoC null展开退出0，既不执行仿真也不代替完整ModelSim功能验收。

后续若修测试，须新构建名、新清单/封存/运行目录；不得修改d目录或当前封存。当前没有新Full Boot、PHY、100帧实板PASS，不继承旧单缓冲PASS，也不把去掉每帧预热的收益全部归为双缓冲。
