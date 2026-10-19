# CNN单次诊断：追加同帧完整720p原图

2026-10-16。仅新增软件，不修改RTL/IP/PDS、不覆盖`cnn_digits_diag`成功软件或前两次实板日志。沿用最新RAM响应增加1拍、DVP首级FF I/O打包修复后的CNN位流，**无需重新做PDS或下载位流**。磁盘实现报告已复核PCLK约束下STA满足、10个首级FF打包成功，实际传感器输入相位尚未测量，关键HDL未完成；继续沿用用户授权板优先诊断。

固定应用`build/photo_20261016_a/program.bin`：42544字节，入口/装载`0x40000000`，SHA256 `2f72e829b3044e1ce8f5996d6b9ddb39877c3c6f15048cf9a040b64bd78d7bd4`，Loader CRC `093ba2e9`。复用原确定性非训练模型ID `05a032af`、6222个装载word、CRC `0ca5949e`、装载流SHA256 `fa210d89f4ef30a4f26e90f556f7ce3e351756df6f22f982b8081335da7fccfd`；参数已编入新BIN。

```powershell
Set-Location D:\riscv\RISCV
python tools/cnn_digits_photo/run.py --port COM9 --log-dir sim/cnn/board/photo_20261016_01
```

关闭串口助手，按工具提示按下、释放KEY0，等DDR就绪、画面稳定后Enter。目录必须不存在；不覆盖或续跑旧目录。工具沿用现有Loader自动装载新应用，波特率仍为115200 8N1。完整原图1843200字节的纯串口理论下限160秒，加上RGB96、包头/ACK、固件下载和CPU开销会更久，预留约3分钟或更多；PC整次导出截止600秒，每包/ACK仍独立5秒，不自动重试。

## 新增产物及检查

- `source.rgb565`：同一次采集的完整1280×720、小端RGB565，1843200字节；未做中心裁剪/96缩放，不是传感器Bayer RAW。
- `source.png`：完整原始拍摄画面的无损RGB预览，RGB565按位复制展开，无滤波、去噪或补点。
- `rgb96.bin` / `rgb96.png`：同帧实际DDR预处理输出，27648字节；先导出RGB96，完整原图随后传输。
- `expected96.rgb` / `expected96.png`：PC仅由`source.rgb565`独立按合同重算的预处理参考；`preprocess_comparison.json`逐字节核对全部27648字节，并保存首个差异的输出坐标/通道、源坐标/字节地址/像素值。
- `gray32.png`、`integer_reference/`、`board_scores.json`及`comparison.json`：由实际RGB96生成的完整整数CNN参考与板端10分数比较。保留非训练诊断属性。
- 完整`uart.rx.bin` / `uart.tx.bin`、源/RGB两条流的`.partial`、模型/BIN/manifest副本及`result.json`；成功后生成`verified.json`并自动回放原始字节复核。

两条流使用新`CN02`包头，32字节小端：magic/kind/SEQ/offset/length/total/dataCRC/headerCRC。kind1/2为RGB96 DATA/END，kind3/4为源RGB565 DATA/END，严格按该顺序。RGB为27个DATA+END，源为1800个DATA+END，共1829个ACK；DATA至多1024字节，END无载荷。PC严格核种类、长度、偏移、SEQ及逐包/整帧CRC，不接受另一帧替代。

Camera领取A后立即STOP并等待尾帧结束。CPU读取A对应捕获CRC，运行PP/CNN，冻结同一BUF/SEQ。导出前后核Camera所有权/源SEQ/源CRC与PP/CNN身份；软件不再START/CLEAR，A在两条流完整导出、END被ACK前始终CPU持有。CPU导出源时累计整帧CRC，与捕获硬件CRC比较，PC也独立计算。导出完成后释放A，并按自身令牌领取/释放可能的B尾帧，关闭账本；PC完成两个比较才发送Q。

若PC发现PP差异或CNN分数差异，完整收到的原图/输出/参考/差异记录会保留，此时Camera已停止并关闭账本，不发Q、不重试。若串口中途或源CRC失败，只保存实际收到的原始流/partial及错误，不补造完整图像；固件保持首败现场，用户KEY0后用新目录复测。

## 验证与边界

必要离线收据：`sim/cnn/board_photo_20261016_a/checks_01/review.json`。只测新增源导出相关行为：实际固件C+原生设备模型完成完整720p非对称图案的两条流、1829包/ACK及尾帧有/无；检查源CRC错误、源ACK错误、释放错误。构造“所有CRC和CNN10分数均正确但PP输出一字节与源不符”的场景，PC必须拒绝并给准确源坐标；另检查错分数、源SEQ/offset/kind/长度/载荷CRC/截断。正常回放逐像素核PNG展开；合成证据不能冒充实板。7个原生场景、13个拒绝检查通过，程序/BSS/栈与RV32I指令审计通过，静态栈368字节。

CNN数学/模型未改，复用`board_diag_20261016_a/checks_02`的7种图案Python宽整数/C int64全部参考层检查，不重跑。原生模型不是HDL或真实CPU仿真；未跑PDS、HDL、Full Boot、ISA、CoreMark或DDR PHY。新软件尚未实板验收。

后续原证据复核：

```powershell
python tools/cnn_digits_photo/run.py --verify sim/cnn/board/photo_20261016_01
```

若原图对应源像素已有彩点且PP全字节一致，问题位于PP之前或源路径；若原图到PP对照不一致，可用首个差异进一步定位。即使全部比较一致，也不能单凭此证明图像视觉质量、实际DVP输入时序、全部异常/并发或真实数字准确率通过。
