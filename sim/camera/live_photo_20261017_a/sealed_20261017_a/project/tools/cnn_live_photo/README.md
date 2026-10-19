# 恢复真实拍照入口

2026-10-17。本入口对应`CAMERA_COLORBAR_ENABLE=0`、`CAMERA_DVP_TEST_ENABLE=0`，恢复真实画面。不要用绑定PRE-ISP彩条/DVP模式的专用入口。固定拍图BIN不变，未重建固件；旧源码/工具/日志不覆盖。

先生成并下载恢复拍照的正常模式位流；如果已完成，无需再次生成。当前接口仍是 **J10、CAM1/J4**。关闭串口助手，执行以下命令，按提示KEY0按下/释放、等DDR就绪、画面稳定后Enter：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_live_photo/run.py --port COM9 --log-dir sim/cnn/board/live_20261017_01
```

目录必须为空且不存在，首败停止，不自动重试。约3分钟或更久后，原图在`source.png`、原始数据在`source.rgb565`，同时保留`rgb96.png`、`gray32.png`、完整RX/TX以及源→PP逐字节/CNN10分数比较。正常模式可改变画面；本工具不自动判定照片无彩点或之前故障已修复。

预期身份`OV5640_LIVE_RESTORED_J10_20261017_A`，对应`sim/camera/restore_live_20261017_a/review.json`及当前40项设计/include身份。244笔配置写、8笔读回；表写503D00，4741依赖传感器硬复位/表首软件复位恢复默认00，**不是本模式新增的显式4741写/读回**。固定BIN不提供这两项的独立PC读回或实际位流识别；操作确认仅为用户确认。本版时序/HDL不继承旧PASS。

固定BIN仍为`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节、SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，模型05a032af/0ca5949e。身份/提示及1829包既有合成原字节回放离线收据在`sim/camera/live_photo_20261017_a/checks_02/review.json`；checks_01为旧提示字面判据不适配导致的检查器首败，保留原目录，修正后在新目录检查。未运行HDL/PDS/Full Boot/串口。

只读复核：

```powershell
python -X utf8 tools/cnn_live_photo/run.py --verify sim/cnn/board/live_20261017_01
```
