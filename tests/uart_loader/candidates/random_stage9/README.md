# 阶段⑨随机二进制DDR诊断候选

2026-10-09最新：阶段⑨random_stage9两轮各1000镜像实板PASS。每轮17946响应、3700127有效文件字节，整镜像DDR CRC及尾哨兵全部通过，零错误/零重试；约550秒/轮、6.73kB/s。两轮原始日志、当前PDS/IP/位流配置副本已离线核验归档，成功阶段⑦/⑧及1186冻结输入不变。当前主IP由用户指向random_stage9同一对DAT。正式LOAD/VERIFY/RUN尚未实现，下一开发步骤为⑩真实program.bin的LOAD完整END/LOADED_UNVERIFIED，继续ROM驻留、不执行。见[两轮实板验收](../../../../doc/uart_loader/UART_Loader随机二进制两轮实板验收_2026-10-09.md)。已成功C/工具/ELF/DAT不重建；上板、复位和串口由用户操作。

从阶段⑧成功候选复制并记录13个初始文件身份。新增受限CMD13分块写/CMD14实际读回CRC，最多低60KiB，256字节块，应用栈4KiB禁止写。正式LOAD/VERIFY/RUN仍不支持，随机数据不执行。原成功目录/IP不替换，已有ELF不允许覆盖重建。

当前仿真进度和验收范围以[阶段⑨记录](../../../../doc/uart_loader/UART_Loader随机二进制与DDR读回CRC阶段9_2026-10-09.md)为准；只有部署门控STAGE9_SIM_PASS后才能由用户使用同一对DAT生成下载位流。实板由用户操作，Codex仅离线核验。
