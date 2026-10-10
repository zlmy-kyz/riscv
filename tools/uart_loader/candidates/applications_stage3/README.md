# 同位流应用下载与验收

2026-10-09 最新：第二程序、CoreMark两组短迭代CRC及两组60次正式运行五步实板PASS；437响应独立核验和279项成功快照归档完成。详见[实板验收](../../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark实板验收_2026-10-09.md)。下方NOT_TESTED为开发准备时状态。

2026-10-09：部署门控SAME_LOADER_APPLICATIONS_SIM_PASS，五组集中仿真和35项PC离线检查PASS；实板NOT_TESTED。仅复用已验收Loader协议，不改成功工具、固件或位流。

用户在PowerShell执行：

```powershell
& 'D:/riscv/RISCV/tools/uart_loader/candidates/applications_stage3/run_board.ps1'
```

保持此前Hello成功的位流，关闭串口助手。脚本依次second、performance_1、validation_1、performance_60、validation_60；每次用户KEY0后等DDR初始化再回车。正式60次先独立核验对应1次实际CRC日志。五份原始JSON和总验收写入 `D:/riscv/RISCV/sim/uart_loader/board/applications_stage3_first/`，失败停止、不重试、不重复RUN、不覆盖旧日志。

upload.py支持固定 `--application` 名称，或已冻结且严格审查的 `--manifest`；实际模式必须通过门控所有输入哈希。`--plan-only`不打开串口，也不能成为实板证据。正式运行手动入口另需 `--crc-log <对应模式1次实际JSON>`。

application.py审查RV32I、DDR链接布局、BIN/ELF一致性和严格UART输出；plan.py分256字节块，PING/LOAD/VERIFY/唯一RUN；sim目录的check_board.py/check_all.py离线核验实际响应、整输出、CRC前置证据及同位流身份。位流文件哈希不等于独立观察JTAG下载。

完整复现、成功镜像身份和未覆盖范围见 [准备记录](../../../../doc/uart_loader/UART_Loader同位流第二程序与CoreMark准备_2026-10-09.md)。
