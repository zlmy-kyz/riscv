# RVLD PC工具：PING与阶段②固定接收

新增rx-test：固定发送64-byte向量，CRC=23C3E508；CPU存入片内RAM并逐字节比较，
正确才返回ACK64。没有DDR下载或RUN。仅适用于阶段②build/rx_fixed的ROM/RAM同时部署后。
pyserial3.5已由用户安装，COM11已确认CH340。关闭串口助手，每条独立命令前KEY0复位并等待初始化。

```powershell
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/rx_fixed100.json rx-test
# 再复位并等待初始化，另存第二轮：
& C:/python/python.exe tools/uart_loader/loader.py --port COM11 --count 100 --log sim/uart_loader/board/rx_fixed100_after_reset.json rx-test
```

预期100条RX_TEST N: ACK; 64 bytes matched in RAM，退出0；JSON含原始tx/rx hex。
NACK/超时/CRC/SEQ不符即停止并非零退出，不自动重试。新位流PING也需复位后独立回归。
两轮固定接收均实板PASS后才推进DDR写入/读回；当前仿真进度以CODEX_HANDOFF为准。

以下为阶段①工具的历史说明；PING格式与命令继续兼容，原日志和镜像保留原样。

只提供PING；没有LOAD/VERIFY/RUN命令。protocol.py使用Python标准库CRC32编码36-byte PING，
严格检查60-byte应答的Header/Payload CRC、SEQ、命令、基址和PING-only能力。
协议编解码已用于 `sim/uart_loader/run.py` 与真实CPU C程序互操作。

当前 `C:/python/python.exe` 未安装pyserial，实板调用前需安装requirements；本阶段未安装依赖、
未打开任何串口，也未部署Loader位流。当前Echo或CoreMark位流不会响应这个协议。

```powershell
# 实板Loader部署并确认端口后执行，不要照搬COM编号。
& C:/python/python.exe -m pip install -r tools/uart_loader/requirements.txt
& C:/python/python.exe tools/uart_loader/loader.py --port COMx --count 100 --log sim/uart_loader/board/ping.json ping
```

CLI固定115200/8N1/无流控，停等，响应5秒超时，无自动重试或RUN。
每个新CLI从SEQ1开始，需先复位Loader，避免复用旧会话序号；重试场景和自动会话续接留后续实现。
输出ACK/SEQ、ROM驻留候选阶段、地址/容量/块长与往返时长。容量字段不是下载能力声明。
