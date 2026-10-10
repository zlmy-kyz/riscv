# 阶段⑧PC工具r2

修复恢复PING/CRC因truncated_前缀被误要求195ms的问题。只给真正negative/status8004的截断包NACK施加下限；固件/镜像和协议不变。12项专项回归与8项PC检查PASS；用户已完成两轮实板复验，每轮108/108 PASS，独立核验通过。

KEY0复位并等DDR初始化，每轮用新first_pc_r2/after_reset_pc_r2日志；不要覆盖旧FAIL。详见[误报记录与命令](../../../../doc/uart_loader/UART_Loader_ACK_NACK实板首轮时序误报与PC工具r2_2026-10-08.md)。独立核验器使用sim/uart_loader/stage8/check_board_r2.py。

当前结果：sim/uart_loader/board/ack_nack_stage8_pc_r2_board_result.json，PASS_HOST_INJECTABLE_ONLY。每轮73ACK/35预期NACK/37CRC ACK，UART帧错/溢出实板未覆盖，完整实板范围NOT_COMPLETE。原FAIL日志保留；成功镜像未重建。详见[两轮验收](../../../../doc/uart_loader/UART_Loader_ACK_NACK主机可注入异常两轮实板验收_2026-10-08.md)。
