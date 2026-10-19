# 单缓冲100帧循环验收

**2026-10-15：100帧实板正常循环复核通过。** 原始目录`sim/camera/board/loop100_20261015_01/`，独立收据`sol_review.json`为CAMERA_LOOP100_BOARD_DATA_ACCEPTANCE_PASS。序号1→100、硬件/CPU CRC100/100一致、无错误/溢出/重试；总114.614秒，等待均值702.202ms（含丢10个启动帧），CPU整帧读取/CRC均值432.845ms。原始报告保持；本轮没有图像导出或PC帧CRC，100个CRC不同也不代替人工作业确认。下述“待用户执行”为原准备状态，使用同一成功BIN即可复现，无需因本次验收再重跑。

沿用当前已成功导出两帧的Camera位流、RTL及1280×720 RGB565参数，**不用重新PDS**。新程序经现有Loader装入DDR执行，不更换ROM/RAM初始化或成功两帧BIN。每次ARM仍丢弃10个启动帧；单缓冲逐帧串行，等待DONE后CPU读完整帧，再ARM下一次，没有采读重叠。

固定程序`build/camera_loop100_20261015_a/program.bin`为10896字节，SHA256 **82f6698dfeb820219a698b5d752c9c0d033e734ecde52c99b33ad805ad3c7cc6**，Loader镜像CRC32 **7c9c3d04**。入口0x40000000，代码/数据/BSS在低60KiB，4KiB栈在0x4000F000–0x40010000；帧区仍0x41000000，长度1843200字节。不自动重建BIN。

关闭其他串口程序，在工程根目录执行（按实际端口改COM9）：

```powershell
Set-Location 'D:\riscv\RISCV'
python tools/camera_uart/loop100.py --port COM9 --log-dir sim/camera/board/loop100_20261015_01
```

目录必须不存在。工具提示用户按KEY0并释放、等DDR就绪后Enter，再打开串口；89个Loader应答含整BIN VERIFY和唯一RUN，应用READY后PC只发一个G启动100帧。运行中主动遮挡镜头、移动物体或改变画面，工具到第50帧会提醒，不暂停采集。无需每帧操作，不导RGB565/PNG，无自动重试或重同步。

每帧必须经过ARM→观测BUSY且DONE清除→DONE且BUSY撤销；帧序号递增、基址41000000、921600像素、1843200字节、57600写拍、无错误/溢出。CPU以460800个32位读计算全帧IEEE CRC32，读取前后元数据稳定，结果须等于采集CRC。每帧只打印序号、硬件/CPU CRC及MATCH、状态/错误、WAIT_TICKS和CHECK_TICKS。**CRC相同合法，不判旧帧，也不以CRC变化替代完整采集流程。** PC仅检查摘要和原始串口协议，不声称本轮在PC重算全帧CRC；图像可视正确性复用两帧成功证据。

计时基准93750000Hz，毫秒＝ticks÷93750。WAIT从ARM前至DONE观察后，包含硬件丢弃10个启动帧及软件轮询开销；CHECK包括CPU完整CRC及读后稳定性/比较，不包含该帧串口打印。最终统计100帧各阶段总计/最小/最大值，PC另给均值毫秒和总秒数。TOTAL从第一帧ARM前计至输出最终摘要前，包含循环中的元数据检查/打印等开销。软件将硬件32位CYCLE扩展为64位，读取时至少每1024字采样一次，支持长循环跨回绕，不用整个100帧的32位差值计算总耗时。

配置等待5秒、单帧采集等待5秒、CPU整帧读取20秒、启动命令等待30秒均有超时；原RTL本身的采集超时仍保持3秒。本轮不放宽该硬件判据。首败不再ARM、不清状态、不自动ABORT重试；输出FAIL原因、成功数、当前序号/长度/像素数/写拍、硬件/CPU CRC、UART/Camera状态及统计，锁存FAIL后停机。若CPU/总线彻底无响应，PC每行30秒超时仍停并保存前缀，不能保证失去CPU响应时仍有固件诊断。

成功末行为`LOOP100_END RESULT=PASS SUCCESS=100 ...`，测试状态此时才写PASS。目录保存固定application.bin/manifest.json、完整原始uart.rx.bin/uart.tx.bin、逐帧frames.csv、result.json、独立verified.json。失败保留同一目录和已收诊断，重试须新目录并由用户再次KEY0，不能覆盖首败。

只读检查计划或复核实际日志：

```powershell
python tools/camera_uart/loop100.py --plan-only
python tools/camera_uart/loop100.py --verify sim/camera/board/loop100_20261015_01
```

静态RV32I/ELF/BIN/栈审计已过；`sim/camera/loop100_preparation_20261015_a/`保存实际C程序的native模拟MMIO 14例和串口/统计8例正反检查。正例独立输入图案经zlib生成期望、逐个读取46080000字、序号及计数器回绕，重复CRC98次仍通过；错误例检查首败后无后续ARM。合成数据明确OFFLINE，不作实板。没有运行新CPU HDL、CoreMark/ISA/PHY/PDS或打开COM；**当前100帧实板待用户执行**，不继承两帧实板PASS。

若需修改程序，使用新构建名`python tests/camera_loop100/build.py --tag 新名称`；不得覆盖此冻结构建。program.dat只是同BIN的DDR表示，不可替换ROM/RAM初始化。成功/失败结果交Sol核原始日志；只有明确RTL反例才整理最小复现交Astra。
