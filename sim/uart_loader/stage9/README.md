# 阶段⑨真实CPU/DDR与UART确认

2026-10-09最新：阶段⑨random_stage9两轮各1000镜像实板PASS。每轮17946响应、3700127有效文件字节，整镜像DDR CRC及尾哨兵全部通过，零错误/零重试；约550秒/轮、6.73kB/s。两轮原始日志、当前PDS/IP/位流配置副本已离线核验归档，成功阶段⑦/⑧及1186冻结输入不变。当前主IP由用户指向random_stage9同一对DAT。正式LOAD/VERIFY/RUN尚未实现，下一开发步骤为⑩真实program.bin的LOAD完整END/LOADED_UNVERIFIED，继续ROM驻留、不执行。见[两轮实板验收](../../../doc/uart_loader/UART_Loader随机二进制两轮实板验收_2026-10-09.md)。已成功C/工具/ELF/DAT不重建；上板、复位和串口由用户操作。

`run.py --suite negative/legacy/bulk/native --tag 新标签`读取已构建候选，不自动重建；已有结果目录拒绝覆盖。bulk/negative/legacy使用真实MMIO/FIFO边界的字节模型，TIME_SCALE512，只确认CPU/DDR算法/保护/错误恢复，不代表原速UART持续吞吐。native通过实际RX/TX引脚、TIME_SCALE1确认原115200收发。`faults/run.py --suite native`对新固件另复验真实BREAK/溢出与恢复。

`check_pc.py`17项离线测试和1000镜像fixture，不是实板证据；`finalize.py`要求全部六组仿真/离线检查PASS后冻结源码、镜像和输入BIN。`check_board.py`/`finalize_board.py`独立核验实际两轮板级日志并新增固定副本，不打开串口。

当前状态见[阶段⑨记录](../../../doc/uart_loader/UART_Loader随机二进制与DDR读回CRC阶段9_2026-10-09.md)。原RTL/IP/PDS/成功镜像保留；模型不含PHY训练，实板必须另验，禁止随机数据RUN。
