# Loader固件：VERIFY / RUN / DDR / Hello

2026-10-09最新：合并实板157/157响应与唯一RUN后的Hello PASS，独立原始日志核验与成功归档完成。成功快照在 `sim/uart_loader/board/verify_run_hello_success/`；功能输入已冻结，请勿修改或重建。详情见[实板验收](../../../../doc/uart_loader/UART_Loader_VERIFY_RUN_Hello实板验收_2026-10-09.md)。

以下是开发准备时历史记录。

2026-10-09：集中仿真 COMBINED_SIM_PASS，实板 NOT_TESTED。冻结输入禁止改写；成功旧镜像保留，隔离 PDS/IP 已生成并归档位流，时序及完整初始化审计 PASS；JTAG 未发现 FPGA，等待现场连接。

完整范围、复现命令与当前部署状态见 [合并验收记录](../../../../doc/uart_loader/UART_Loader_VERIFY_RUN_DDR_Hello合并验收_2026-10-09.md)。
