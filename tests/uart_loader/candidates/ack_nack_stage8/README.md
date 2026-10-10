# 阶段⑧隔离镜像候选

本目录从阶段⑦成功快照逐字节复制，源码/ELF/DAT未重建。镜像与主IP当前build/ddr_crc相同。阶段⑧仿真已PASS，实板待验；详见[专项记录](../../../../doc/uart_loader/UART_Loader_ACK_NACK异常专项阶段8_2026-10-08.md)。

build.ps1只是原成功源码快照，不是本隔离路径的构建入口，不运行它重建DAT。现阶段使用已验收同一ROM/RAM DAT；PC专项工具在tools/uart_loader/candidates/ack_nack_stage8，测试不要求换IP或新位流。
