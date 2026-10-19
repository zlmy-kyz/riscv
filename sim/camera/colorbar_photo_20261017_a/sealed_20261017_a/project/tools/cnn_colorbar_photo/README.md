# OV5640内部彩条原图导出

2026-10-17。只新增PC入口及硬件身份记录，**沿用现有固定拍图BIN，不重建固件，不修改RTL/IP/FDC/PDS**。旧`tools/cnn_digits_photo/run.py`和已封存软件/日志保持原身份，其中“沿用位流/本次仅换软件”的提示属于历史真实画面流程，**不得用于本次彩条测试**。

## 用户执行顺序

1. 实物连接恢复为底板 **J10、CAM1/J4**，与当前约束一致；J25不能直接沿用。
2. 用户重新综合、映射、布局布线，检查本版时序，生成并下载启用`CAMERA_COLORBAR_ENABLE=1`的**新彩条位流**。旧位流不会输出内部彩条，仅重跑PC程序不能开启该功能。
3. 关闭串口助手，执行下列新入口，按提示在下载后按下/释放KEY0、等待DDR就绪，再Enter导图：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_colorbar_photo/run.py --port COM9 --log-dir sim/cnn/board/colorbar_20261017_01
```

目录必须不存在，首败停止，禁止覆盖旧目录或自动重试。完整传输约3分钟或更久。工具复用现有Loader、固定BIN以及严格CRC/源帧→PP逐字节/CNN10分数检查，无新相机寄存器写入或图像处理。BIN仍是`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节，SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，模型仍为05a032af/0ca5949e。

## 新硬件身份

预期版本`OV5640_COLORBAR_J10_20261016_A`。`hardware.json`固定本版40项RTL/include及当前J10约束的身份，关联Astra静态收据`sim/camera/colorbar_20261016_a/review.json`。实际改动为5个配置/参数文件，245笔配置写、10笔读回，预期强制核503D=80、4741=00。没有修改RGB565/720p、采样沿、DMA或MMIO ABI。

每次运行保存`hardware.json`、`hardware_record.json`和新的放行收据，明确记录用户确认新彩条位流/J10/KEY0、预期源码身份，以及当前本地sbit存在时的文件指纹。本地文件指纹不是“板上下载身份已自动验证”，不作为位流哈希/时序报告前置门。固定BIN仅输出原SENSOR_ID/CONFIG=OK，PC不能独立从该接口读出503D/4741或区别旧版位流，不能把操作确认写成寄存器实测证据。

本版彩条新增RTL的时序/HDL/实板不能继承旧J10实现PASS；工具记录`NEW_COLORBAR_IMPLEMENTATION_NOT_REVIEWED`与`key_HDL=NOT_COMPLETED`。PDS/下载由用户完成，本工具不会启动PDS、下载位流或代替KEY0。

## 产物与验收边界

先看`source.png`及完整1843200字节`source.rgb565`。预期为稳定八色条，同色条内部应稳定，遮挡镜头不应改变画面。方向、边界、具体RGB565值和整帧CRC未预先固定，不伪造一个黄金CRC或把PC图替代传感器图。

同时保留`rgb96.png/.bin`、`expected96.png/.rgb`、`gray32.png`、完整RX/TX、模型/BIN/manifest及所有原有比较记录。`colorbar_assessment.json`明确标记视觉检查与遮挡不变性待验：一次采集的CRC/PP/CNN一致只能证明数据闭环，不能宣布八色条正常、无彩点或根因已解决。

如果彩条仍有绿紫点，排查重点转向测试图产生之后的格式/传输/采样链路；彩条干净则重点核真实成像/ISP路径。两种结果均需结合原始数据，不单凭一张图完成根因证明。失败时保留整个目录，不清错自动重拍。

离线复核：

```powershell
python -X utf8 tools/cnn_colorbar_photo/run.py --verify sim/cnn/board/colorbar_20261017_01
```

本轮工具检查收据`sim/camera/colorbar_photo_20261017_a/checks_01/review.json`，覆盖新提示/硬件身份、J25/旧模式/不重建/错误源码SHA拒收、取消前置提示不打开串口、既有1829包合成原字节回放以及合成证据不得冒充实板。未重跑CNN数学、HDL、Full Boot或历史全套，没有本轮实板结果。
