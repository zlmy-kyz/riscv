# 同位流第二程序和 CoreMark 验证

2026-10-09 最新：第二程序、CoreMark两组短迭代CRC及两组60次正式运行五步实板PASS；437响应独立核验和279项成功快照归档完成。详见[实板验收](../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。下方NOT_TESTED为开发准备时状态。

最终结果：第二程序v3原速、performance_1和validation_1的v3完整算法、performance_60和validation_60的v4专用启动均PASS；35项PC离线检查PASS。196项输入、74项证据及196项副本冻结于 `D:/riscv/RISCV/sim/uart_loader/build/applications_stage3/`。本次实际板级NOT_TESTED。

run.py覆盖完整应用；run_partial.py限定两组60次，用独立partial TB等待所有已接受数据事务退休/响应后结束。旧v3/performance_60的结束检查失败保留，不放入最终门控；已通过完整应用的TB不变。60次不是本轮完整算法仿真，原同一BIN完整Full Boot证据另行绑定。

check_pc.py的28项和check_controls.py的7项均离线fixture，不是板级证据。check_board.py核验一份实际日志；check_all.py要求第二程序、两个短CRC和两个正式运行，共五份实际日志与成功Hello使用相同Loader位流文件身份。

用户操作和全部复现命令见 [准备记录](../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。
