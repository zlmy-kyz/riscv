# OV5640 串口采帧验收程序

**2026-10-15实板结果：两帧验收通过。** `sim/camera/board/uart_frames_20261015_01/`实际原始字节已由Sol离线复核，采集/CPU首读/CPU复读/PC CRC分别一致为31167575与3F8A68B9，ID5640、配置OK、各921600像素/1843200字节/57600写拍、序号1→2、无溢出错误；用户已确认图片正确。正式收据为该目录`sol_review.json`，原result/verified中的自动VISUAL_PENDING保留，不改写人工确认前的报告。继续使用下述同一固定BIN；无需重复长仿真或本轮两帧验收。以下为原准备说明和后续复现步骤。

2026-10-15，按用户提出的CRC＋PC导图流程实现。完整720p真实CPU仿真不再续跑；已有SCCB/faults成功证据和本轮SoC超时前缀已复核保留。**本程序已构建及离线校验，尚未实板验收，不声称新BIN通过Full Boot仿真。** 本轮改用用户操作的实际DDR/Loader/相机串口采帧验证剩余范围，不再把耗时SoC仿真作为前置门。

固定构建目录`build/camera_uart_20261015_a/`：program.bin **6212字节**，SHA256 **373940dab9b1c1a4e444d5fa4467580b490d4bdd288fc4c516c90f32aed9f529**，Loader整镜像CRC32 **26abe2d1**，入口0x40000000，程序/BSS在低60KiB、4KiB栈在0x4000F000–0x40010000，帧区0x41000000–0x411fffff隔离。program.dat只是同BIN的DDR字表示，**不能替换指令ROM/数据RAM初始化**；不改现有成功Loader镜像或PDS/IP。上板工具固定使用该BIN，不自动构建。

使用已通过时序的Camera版位流和现有Loader，关闭串口助手，由用户下载/KEY0/串口操作。根目录执行：

```powershell
Set-Location 'D:\riscv\RISCV'
python tools/camera_uart/capture.py --plan-only
python tools/camera_uart/capture.py --port COM9 --log-dir sim/camera/board/uart_frames_20261015_01
```

`--plan-only`不打开串口。正式命令要求新日志目录，随后提示用户按KEY0、释放并等DDR就绪。现有RVLD v1 stop-and-wait协议完成53个应答、整BIN VERIFY和唯一RUN，原始下载应答、程序身份均保存；没有PDS/位流哈希审查前置门，不自动下载FPGA。

程序实际读Camera MMIO ID、传感器ID5640及配置状态；每次C命令ARM一帧并停止，核921600像素、1843200字节、57600实际写拍及序号递增。CPU逐32位读取整帧CRC，再完整读取一遍CRC，同时检查前后元数据/状态不变；两次CPU CRC均须等于采集CRC。所有MMIO仍使用真实总线，未清Cache或force内部信号。

默认导出第一帧PNG/RGB565后，PC提示遮镜头或明显改变画面，用户按Enter再采第二帧。要求序号1→2且CRC变化；CRC无固定标准值，仿真图案AD4E00C3/68C5601B不是实物画面的期望CRC。每帧以1024字节块二进制传输，逐块Header/Data CRC、序号和字节偏移检查，PC重算全帧CRC与采集/CPU/reread全部相等后确认。无自动重传或重同步，首败保留目录/已收前缀，不能覆盖重试。

115200 8N1有效约11520字节/秒，原帧理论160秒，加32字节包头后约165秒/帧，再加USB/ACK延迟可能更久。默认两帧约6分钟以上。完整SoC CPU仿真此前7200秒仍未完成，与实板串口导图的耗时不同。

成功后目录含`frame_001.rgb565`、`frame_002.rgb565`、两张同名PNG、完整`uart.rx.bin`/`uart.tx.bin`、固定application.bin/manifest.json、逐包记录/result.json与独立verified.json。PNG按RGB565**小端、行优先、1280×720**展开，无翻转、无缩放、无红蓝交换。用户仍须打开图片检查颜色、行序、黑帧/撕裂及第二帧画面变化，自动结论为`UART_FRAME_DATA_CHECK_PASS_VISUAL_PENDING`，不会伪造人工看图PASS。收到实板目录与看图反馈后Sol再更新正式结论。

离线复核实际日志（不打开串口）：

```powershell
python tools/camera_uart/capture.py --verify sim/camera/board/uart_frames_20261015_01
```

日常只查摘要，不花时间导图：

```powershell
python tools/camera_uart/capture.py --port COM9 --summary-only --captures 1 --log-dir sim/camera/board/uart_summary_20261015_01
```

摘要模式仍做两次CPU整帧CRC，但不导数据、不计算PC CRC/PNG；结论单独为`UART_CPU_SUMMARY_CHECK_PASS_NO_PC_FRAME_CHECK`，不能冒充完整采帧验收。

开发构建入口`python tests/camera_uart/build.py --tag 新名称`或build.ps1；不能覆盖当前构建目录。GCC RV32I/ILP32、完整ELF/BIN/段/入口/栈/指令合法性静态审计已过，CRC与CAM1包头的真实C函数经本机native调用和Python zlib/struct独立核对，PC收发/导图/逐字节复核经过明确标注OFFLINE_SYNTHETIC_TEST的两帧合成传输及错误拒收测试。离线测试不记实板PASS。记录在`sim/camera/uart_preparation_20261015_a/`。
