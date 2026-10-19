# OV5640 DVP级模式0/8bit诊断入口

2026-10-17。此入口用于 **503D=00（PRE-ISP测试关闭）、4741=05（DVP测试模式0、8bit）** 的新RTL。旧PRE-ISP彩条入口及封存全部保留，不能用它绑定本次硬件身份。Sol仅新增PC工具、硬件记录和必要离线检查，未修改RTL/IP/FDC/PDS或固定BIN，未启动PDS/串口。

## 用户执行

用户重新综合、映射、布局布线检查本版时序，生成并下载新DVP测试位流；当前约束仍为 **J10、CAM1/J4**。旧真实画面/PRE-ISP彩条位流不能代替本版。关闭串口助手，执行下列命令，按提示在下载后按下/释放KEY0、等待DDR就绪，再Enter采图：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_dvp_test_photo/run.py --port COM9 --log-dir sim/cnn/board/dvp_test_20261017_01
```

目录必须不存在，首败保留，不自动重试；完整传输约3分钟或更久。固定BIN仍为`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节，SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，模型ID05a032af/CRC0ca5949e。沿用Loader及1829包CN02传输、源CRC→CPU→PC闭环、源→PP27648字节及CNN10分数独立比较，不重建固件或改变所有权流程。

## 身份及预期

预期版本`OV5640_DVP_MODE0_8BIT_J10_20261017_A`。`hardware.json`固定本版40项RTL/include、J10约束及Astra静态收据`sim/camera/dvp_test_20261017_a/review.json`。board_top的COLORBAR=0/DVP_TEST=1，245笔写后10笔读回；预期503D00/474105必须读回正确才CONFIG_DONE。PCLK采样沿/720p/数据拼接/FIFO/DMA/原ABI保持。

工具记录用户新位流/J10/KEY0确认、预期硬件版本和本地存在时的sbit文件指纹，不要求PDS或位流哈希审查收据。固定BIN只输出SENSOR_ID/CONFIG=OK，无法向PC独立暴露503D/4741或实际位流ID，所以操作确认不写成板上版本/寄存器自动验证。新实现时序及关键HDL状态仍待确认，不继承旧版PASS。

**DVP模式0不能预设为原来的RGB八色条。** 既有采集每两个DVP字节组成一个RGB565 word，固定BIN仍严格要求2560字节×720行；本测试模式的实际图案和帧几何需实板确认。若CAM_ERR3，保留首败，不把行长改小、不忽略错误继续导出。

## 保存产物

- `source.rgb565`：完整1843200字节原始DVP采集数据，按既有拼接以小端word存储。
- `source.png`：将上述数据按RGB565解释的预览，**不能用颜色外观判断DVP模式图案是否正确**。
- `dvp_assessment.json`：原始文件SHA、两字节位置的256值直方图、D0零/一计数及相邻同位置采样的D0变化次数、常见拼接word、720行CRC及相邻相同行统计。均是观测事实，没有预设正确值/误码率或黄金CRC。
- 原有实际/参考RGB96、灰度32、CNN参考/分数、完整RX/TX、模型/BIN/manifest、硬件记录、错误/比较结果全部保留。

载板DVP D0在第一/高字节对应拼接word bit8，在第二/低字节对应word bit0；小端文件奇数偏移存第一字节、偶数偏移存第二字节。该D0是载板8bit总线低位，不是裸传感器D0。图案本身可合法变化D0，统计值不是物理误码率；一次采集也不证明跨帧稳定或遮挡不变。新目录可用于后续原始字节/条内/跨帧定位，不应用滤波或强制某位“修图”。

只读复核：

```powershell
python -X utf8 tools/cnn_dvp_test_photo/run.py --verify sim/cnn/board/dvp_test_20261017_01
```

本轮工具检查在`sim/camera/dvp_photo_20261017_a/checks_01/review.json`：新增模式/寄存器/版本身份及提示，旧PRE-ISP模式/寄存器和J25拒收，取消提示不打开串口，已知原始字节对D0位置/计数/单次翻转/行稳定性的独立检查，1829包既有合成原字节回放及合成不能冒充实板。复用固定BIN、原PP/CNN参考及成功软件证据，不重跑HDL/Full Boot/历史全套。尚无本版实板结果，数据闭环通过不等于测试图正确、D0无故障或根因已解决。
