# 新拍一张：预处理上板验收

用户明确选择先上板，本次不等待预处理RTL关键仿真。沿用已确认时序通过的本版位流，**不改RTL/IP/PDS，不把软件检查写成硬件功能PASS**。下载、KEY0、串口由用户执行。

程序在新画面确认后才采集A/SEQ1，CPU领取并STOP相机、排完在途B；从同一源启动PP。核PP的源BUF/SEQ、输出地址42000000、27648字节、96×96、9216读/864写及DONE/错误。CPU按合同独立计算9216个源像素，逐字节比较RGB888；另做整输出CRC复读和整个源帧CRC。源一直持有到完整导出结束，实际DDR输出不会被新的PP START覆盖。

UART按PP01二进制1024字节块回传源RGB565 1843200字节及实际输出RGB888 27648字节。PC用完整源按整数中心采样、RGB565位复制展开生成expected.rgb，逐字节比较，不从DUT选址或输出反推期望。输出PNG来自实际actual.rgb。每包CRC/offset/seq/总长/结束及ACK严格核对，无重传、重同步、自动重拍。源释放及未选B的领取/释放、总发布账本最后闭合；失败立即停止留证。

最终固定程序：`build/photo_20261015_d/program.bin`，19780字节，SHA256 **8a7b1c57cce723753ff73fd6c62dd8f8a099d4f1522902bbb3bb0b4a933bb7b3**，Loader CRC **ac263d07**。RV32I静态指令/ELF布局审计、60KiB程序区和4KiB独立栈审计通过，保守最大栈400字节。复用原Loader的159个应答、整个BIN VERIFY和唯一RUN，不更换ROM/RAM初始化。旧双缓冲/单缓冲成功BIN和准备中的两组预处理程序保持不变；不要重建固定BIN后直接上板。

软件检查为`sim/camera_preprocess/board_first_20261015_a/checks_d/review.json`：13个实际固件C/native MMIO场景，含RGB纯色/坐标图、无尾帧与B尾帧残留ACTIVE_BUF、源/输出CRC错、逐字节错、PP错误/超时、元数据错、坏ACK、释放失败，首败没有再次START。64bit软件时钟跨32bit回绕，整图原始收发与PC工具对接、PNG像素及11个协议/来源/CRC碰撞反例检查通过。**native模型不是RTL仿真，也不等于真实CPU或实板PASS**。

新版本仅修测试侧两组程序的空闲检查：FREE/流停条件不应要求无效的ACTIVE_BUF位为0，正确mask为0x2cf（忽略SELECT、ACTIVE_BUF及DUAL_MODE），其余所有权/流/错误判据保持。初次构建a的静态调用图未识别已有failing防递归保护而中止，保留原产物；b/c是中间静态构建，d为最终身份。checks_a保留MinGW native测试夹具编译错误，checks_b保留检查器错误诊断字串，修正夹具/检查器后checks_c/d通过，不改RTL。

运行前关闭串口助手，使用当前预处理位流（Camera ID43414d02、PP ID50525001）。新日志目录必须不存在：

```powershell
python tools/camera_preprocess_photo/run.py --port COM9 --log-dir sim/camera_preprocess/board/photo_20261015_01
```

按提示按KEY0后释放、等DDR就绪，摆好新画面再Enter。工具会装载固定程序、发G/C采集一次并自动导出。115200/8N1下净数据理论162.4秒，另有块头/ACK/CPU开销，通常约3分钟或更久；整组成对导出600秒上限。不要同时打开串口助手，不重复运行旧日志目录。

完成后目录保留固定application.bin/manifest、放行收据、原始uart.rx.bin/uart.tx.bin、包ledger/result/verified、source.rgb565、actual.rgb、expected.rgb、comparison.json和source.png/actual96.png/expected96.png。PC数据全部通过后仍记人工看图PENDING，回传整个目录并查看source.png和actual96.png。离线复核不会开串口：

```powershell
python tools/camera_preprocess_photo/run.py --verify sim/camera_preprocess/board/photo_20261015_01
```

本次只验一张新照片的正常预处理通路，不宣称A/B循环、提前释放拒绝、全部背压/ABORT/读协议异常、周期级仲裁或最后W/DONE的穷尽验证。原关键测试任务保留；不等待它作为本次用户授权上板的前置条件。不新增PDS/位流审查门、Full Boot、PHY、CNN或INT8量化验收。
