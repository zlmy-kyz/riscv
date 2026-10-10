# 统一 BSP 验证环境

对外仿真入口check.py，支持--application、--native、--build-tag、--tag，以及Hello的--timer-wrap。共享worker run.py使用真实CPU、原Loader DAT、原MMIO/UART/DDR桥和带延迟/背压模型，DDR应用仅由UART装载。IRQ专用TB等DDR应用开启RX IRQ后再注入四字节，避免触发Loader跳转前保护。

仿真包括完整Hello、CRC32、两组CoreMark短迭代、两组60次启动、真实UART IRQ和计时回绕。60次完整算法与正式计时已由本批实板第9/10轮补齐；不将旧不同BIN的算法证据算作新完整仿真。

离线测试仅fixture；freeze.py生成不可覆盖的新部署门控与源快照。check_board.py单轮独立审查，check_ten.py严格审查10轮原始日志、复位确认、SEQ1空状态、不同原始文件哈希、共同BSP/位流及正式CRC前置证据。2026-10-10十轮实板及独立核验已PASS，两组新60次完整正式结果已补齐；518项成功快照在board/first_success，归档收据board/first_submission_result.json。见 [实板验收](../../doc/software/统一BSP与十轮复位下载实板验收_2026-10-10.md) 与 [准备记录](../../doc/software/统一BSP与十轮复位下载验收准备_2026-10-10.md)。
