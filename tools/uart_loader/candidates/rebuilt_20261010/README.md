# 用户重建位流的独立复验入口

2026-10-10：六轮已全部实板PASS，540响应及6次RUN独立核验，Hello/CRC32/CoreMark正式CRC通过；549项成功快照已保存。详见[实板验收](../../../../doc/board/主工程新位流六轮实板验收_2026-10-10.md)。下方待用户操作描述保留准备历史。

绑定 `D:/riscv/RISCV/generate_bitstream/board_top.sbit`，SHA256 7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf；原成功位流和BSP工具保留。

新候选415项输入冻结，综合Loader初始化及现有时序约束核对PASS，8项离线检查PASS；当前实板NOT_TESTED。用户下载新位流、关闭串口助手，在PowerShell执行 `& C:/python/python.exe D:/riscv/RISCV/tools/uart_loader/candidates/rebuilt_20261010/run_board.py`，按提示KEY0/等待DDR/回车，共六轮。日志保存sim/bsp_workflow/rebuilt_20261010/board/first；旧目录存在选新--directory。

详细证据、限制及复核命令见[准备记录](../../../../doc/board/主工程新位流实板复验准备_2026-10-10.md)。
