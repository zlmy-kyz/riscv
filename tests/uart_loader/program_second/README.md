# 第二个 DDR 应用

2026-10-09 最新：第二程序、CoreMark两组短迭代CRC及两组60次正式运行五步实板PASS；437响应独立核验和279项成功快照归档完成。详见[实板验收](../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。下方NOT_TESTED为开发准备时状态。

2026-10-09：新 C 已构建一次并审查RV32I ELF/BIN，587字节，CRC32 280DE354。真实Loader下载/VERIFY/RUN仿真及115200引脚仿真均PASS；本次实板NOT_TESTED。非空data/BSS检查后平方和11440，精确输出 `SECOND_PROGRAM_PASS sum=11440\r\n`。

main.c、startup.S、linker.ld、build.py在根目录，build内保存成功ELF/BIN和manifest；构建器拒绝覆盖现有ELF，验收直接使用同一BIN。复用已成功VERIFY/RUN/Hello Loader位流，不改片内ROM/RAM初始化。

用户实板执行 `D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1`，每次按提示KEY0后继续。完整步骤和范围见 [准备记录](../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。
