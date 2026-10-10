# UART 下载 CoreMark

2026-10-09 最新：第二程序、CoreMark两组短迭代CRC及两组60次正式运行五步实板PASS；437响应独立核验和279项成功快照归档完成。详见[实板验收](../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。下方NOT_TESTED为开发准备时状态。

2026-10-09：四套构建从原CoreMark裸机实验逐字节复制，origin.json绑定原始构建和完整算法证据，未重编译或修改算法。build/performance_1、validation_1、performance_60、validation_60分别保存ELF/BIN/manifest。根目录保留裸机端口源文件副本，原算法源包 `D:/riscv/RISCV/coremark-main/` 保留。

新UART下载→VERIFY→RUN真实CPU仿真：两组1次完整算法/CRC/输出PASS；两组60次装载/启动及main退休PASS，完整60次算法复用原同一BIN的Full Boot证据。新UART下载实板尚未测试，不把历史预置RAM启动PASS当作本次结果。

用户运行 `D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1`，先两组1次CRC，再两组60次正式运行。1次的时间不足ERROR只用于功能检查；60次需全部算法CRC正确、Correct operation validated、无错误且不少于10秒。正式工具必须提供对应模式1次实际串口日志。

全部沿用成功Loader位流，不重新生成FPGA位流。详见 [准备记录](../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。
