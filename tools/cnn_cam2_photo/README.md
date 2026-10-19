# CAM2/J5单摄像头真实拍照，载板J10

2026-10-17。有效约束切至DOUBLE-DVP载板 **CAM2/J5**，载板仍插底板 **J10**，不是底板J25。当前只有一条相机采集链路，**A/B是同一个CAM2相机的DDR双缓冲，不是两个相机**。两测试发生器参数均0，真实拍照模式保持。

用户重新综合、映射、布局布线检查CAM2 PCLK时序和输入FF打包，生成并下载新位流；旧CAM1位流不会因移动模组或重跑软件而切换。关闭串口助手，执行新入口，按提示下载后KEY0按下/释放、等DDR就绪及画面稳定后Enter：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_cam2_photo/run.py --port COM9 --log-dir sim/cnn/board/cam2_20261017_01
```

目录必须不存在，首败停止、不自动重试。完整导出约3分钟或更久，原图`source.png`/`source.rgb565`、实际及参考RGB96、灰度图、完整RX/TX和原有CRC/源→PP逐字节/CNN10分数证据均保留。固定BIN仍为`tests/cnn_digits_photo/build/photo_20261016_a/program.bin`，42544字节、SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，模型05a032af/CRC0ca5949e，没有重建。

硬件预期版本`OV5640_LIVE_CAM2_J5_ON_J10_20261017_A`。`hardware.json`记录同一40项RTL/include、新有效FDC、Astra映射收据、单摄像头/两DDR缓冲及14项PAD，关键为PCLK M21、SDA Y25、SCL AC24、RESET AC26。旧`fdc/camera_single.fdc`为CAM1历史资料，不是本次有效PDS输入。当前PC入口读取有效FDC核硬件记录，但不能自动识别板上下载的是哪一位流，也不能把操作确认记为实测硬件ID。

源码恢复真实拍照时保持244写/8读；503D00由表写入，4741由传感器复位恢复默认00，无新增显式4741读回。必须KEY0重新初始化CAM2。以前CAM1的时序、图像或颜色问题结论不能迁移为CAM2 PASS，换接口也不预先承诺彩点消失。

必要PC离线检查在`sim/camera/cam2_photo_20261017_a/checks_01/review.json`：新提示/硬件身份/14项PAD匹配、旧CAM1/旧PCLK/J25/双相机身份拒收、取消提示不打开串口、1829包既有合成原字节回放及合成不得冒充实板。固定BIN/数学/导图协议未变，复用历史相关证据，不跑HDL/Full Boot/旧全套。Sol未改RTL/FDC/PDS/IP/成功固件或旧日志，未启动PDS/实板。

独立原字节复核：

```powershell
python -X utf8 tools/cnn_cam2_photo/run.py --verify sim/cnn/board/cam2_20261017_01
```
