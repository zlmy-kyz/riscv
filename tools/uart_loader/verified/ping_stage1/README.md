# RVLD 阶段① PC PING 工具

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
