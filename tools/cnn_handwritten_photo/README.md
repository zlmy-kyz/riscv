# CAM2手写数字小批量试识别

使用已训练模型`4c8b5aca`，保持已成功的CAM2/J5、载板J10和真实拍照位流。仅经原UART Loader加载新应用，不修改RTL/FDC/PDS/IP或旧诊断固件。A/B仍是同一个相机的DDR双缓冲。

先准备白纸黑笔数字0–9，每张一个，居中、正向，字符高度约占画面中央720×720正方形的60%–75%。关闭串口助手。首次建议保存完整源帧，按工具提示按下并释放KEY0，等DDR就绪及画面稳定后Enter：

```powershell
Set-Location D:\riscv\RISCV
python -X utf8 tools/cnn_handwritten_photo/run.py --port COM9 --label 0 --session trial01 --sample 1 --full-source --log-dir sim/cnn/board/handwritten_trial01_0_01
```

完整源帧约3分钟或更久，核源1843200byte CRC、源→PP27648byte全部相等、PP→灰度32及全部10分数。保留`source.rgb565/source.png`、RGB96/灰度图、整数参考、所有权账本和完整UART原始字节。

随后使用快速模式收集样本，每次摆好纸张、使用新目录并按提示KEY0。示例同一个0的第二次摆放：

```powershell
python -X utf8 tools/cnn_handwritten_photo/run.py --port COM9 --label 0 --session trial01 --sample 2 --log-dir sim/cnn/board/handwritten_trial01_0_02
```

省略`--full-source`只导出实际DDR中的RGB96共27648byte，不传1.8MB源帧。仍验证PP导出CRC、CNN元数据/10分数、源帧身份和释放账本；**本次没有源帧CPU/PC CRC或源→PP逐字节对照**，结果明确记录`NOT_RUN_RGB96_ONLY`。RGB96由板端PP产生，PC不以自己的resize替代硬件输出。每个session至少保留一组完整源帧配对用于来源抽查。

首轮每类3–5张即可，改变摆放或距离；下一次独立拍摄换`--session trial02`。`--label`填写纸上的真实数字，不能照模型预测填写。预测错误但全部10分数一致时，记录`label_match=false`并正常结束，保留该真实错误样本；数据/CRC/协议/分数不一致则首败停止，不自动重试、清FIFO或过滤错误数据。每次新运行必须KEY0重新回到Loader；原BIN不会因为替换文件自动更新。

每次运行自动固定加载：`tests/cnn_handwritten_photo/build/handwritten_20261017_b/program.bin`，42568byte，SHA256 `5b3364b064a4687a2e141bef504031fdc31a09d1e681b8cd1518133d4ee9f49c`，Loader CRC32 `2157dd62`。模型ABI1为6222word/24888byte，CRC32 `b9749177`，shift `[8,8,8,0]`。新CN03协议/应用banner与旧CN02诊断05a032af严格区分，不覆盖旧模型目录或成功BIN。

只读复核与无串口计划：

```powershell
python -X utf8 tools/cnn_handwritten_photo/run.py --verify sim/cnn/board/handwritten_trial01_0_01
python -X utf8 tools/cnn_handwritten_photo/run.py --plan-only
```

结果`comparison.json`区分“FPGA等于独立整数参考”与“预测等于标签”。`sample.json`保存label/session/sample编号；`integer_reference/`保存PC由实际RGB96生成的完整1024/2048/1024/512/32及10分数参考，**不是硬件逐层dump**。`result.json`中的实物/KEY0为操作者确认，不能自动证明板上位流身份。小批量只用于发现实拍差异，不能作为95%正式准确率、书写者独立或全量异常/并发/长稳验收。

准备证据在`sim/cnn/handwritten_photo_20261017_a/`。离线native模型执行真实应用C并注入独立参考的设备数据，核装载/控制/导出/错误路径；不含真实CPU/HDL/物理DDR。本版尚未实板运行，原关键HDL缺项保持，旧单帧成功不扩大为新模型PASS。原CAM2成功位流仍需保持CAM2/J5/J10、两测试模式0；若实物或下载版本改变，应先恢复该条件。
