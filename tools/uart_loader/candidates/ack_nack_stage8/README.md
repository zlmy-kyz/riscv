# 阶段⑧隔离 PC 异常专项工具

旧版有恢复ACK计时误判，实板复测改用兄弟目录ack_nack_stage8_r2/acceptance.py；旧脚本作为失败输入保留。

使用与阶段⑦成功位流相同的诊断协议，无需重建或部署新镜像。先读 [阶段⑧记录](../../../../doc/uart_loader/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。108 帧/35 个普通串口负例；每个错误后 PING/固定 DDR CRC 恢复。失败保存原始字节并停止，不自动重试、不覆盖旧日志。

从工程根运行，必须先关闭串口助手、KEY0 复位并等待 DDR 初始化；仅在阶段⑧仿真 PASS 后实板使用：

```powershell
& C:/python/python.exe tools/uart_loader/candidates/ack_nack_stage8/acceptance.py --port COM11 --log sim/uart_loader/board/ack_nack_stage8_first.json
```

另一次复位后用新的 after_reset 日志名复测。使用 --plan-only --log <新路径> 可离线保存计划，不打开串口。

通过仅标记主机可注入项 PASS，UART 帧错/溢出实板仍未覆盖，不自动推进随机 BIN 或 LOAD/VERIFY/RUN。
