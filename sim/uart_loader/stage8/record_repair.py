from pathlib import Path
import json
R=Path('D:/riscv/RISCV');p=R/'doc/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md'
s=p.read_text(encoding='utf-8-sig')
s=s.replace('full 矩阵仍进行中；最终状态以 results.json 为准，未获得 full 最终 PASS 前不能进行实板专项。', '首次 full 长矩阵在第113项最后 CRC 恢复请求处 FAIL：检查器把已退休 LBU 总数（丢字节后少1）与原始线缆字节位置比较，错误拦截合法 DDR 读；首次报告/日志保留 FAIL，不作为完整 PASS。原输入已逐文件按报告哈希保存 attempt1_sources/receipt.json。仅修正隔离 TB 一行：完整包门控由 cpu_lbu>=frame_end 改为 lbu_index>=frame_end；LBU 值、丢字节事件、原始 RX/FIFO/MMIO/退休映射检查仍保留。C/RTL/二进制均未改。新增 --suite uart 重跑8帧：真实低停止位与真实FIFO17-byte溢出、各自 NACK8005、CONTROL清错、PING及只读CRC恢复全部 PASS，Errors/Warnings0；16 SW/64 LW，FIFO峰值16。run_repaired.py 正在新目录 sim/uart_loader/build/ack_nack_stage8_repaired/full 从头重跑114帧。最终状态以该新目录 results.json 为准，未获得完整最终 PASS 前不进行实板专项。')
s=s.replace('& C:/python/python.exe sim/uart_loader/stage8/run.py --suite native', '& C:/python/python.exe sim/uart_loader/stage8/run.py --suite native\n# 检查器修复后的UART专项及完整新证据目录：\n& C:/python/python.exe sim/uart_loader/stage8/run.py --suite uart\n& C:/python/python.exe sim/uart_loader/stage8/run_repaired.py --suite full')
s=s.replace('非法包禁止 DDR 请求；', '格式/地址/长度/序号等预先拒绝的包禁止 DDR 请求；有效CMD12的PC预期CRC失配仅允许16次LW、没有SW；')
p.write_text(s,encoding='utf8')
print('Documented checker failure and isolated UART recheck; original FAIL retained')
