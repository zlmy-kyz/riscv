# 统一 BSP 的隔离 PC 工具

复用成功Loader协议，新增Hello/CRC32/CoreMark严格输出检查及suite十轮流程。application.py审查ELF/BIN，plan.py生成PING/LOAD/VERIFY/唯一RUN；upload.py保存实际串口结果，suite.py由用户确认KEY0后调用统一run.py。门控与成功位流哈希必须匹配，正式60次必须有对应短迭代实际日志；plan-only和offline fixture不是实板证据。

不修改原成功PC工具、Loader、CPU或DDR桥。用户执行 `C:/python/python.exe D:/riscv/RISCV/tests/bsp_workflow/run.py --acceptance`。完整步骤见 [准备记录](../../../../doc/software/统一BSP与十轮复位下载验收准备_2026-10-10.md)。

2026-10-10用户十轮已全部实板PASS，独立逐帧核验834响应与10次RUN及全部程序输出，518项成功快照归档。详见 [实板验收](../../../../doc/software/统一BSP与十轮复位下载实板验收_2026-10-10.md)。
