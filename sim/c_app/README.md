# 通用 C 程序验证

软件入口和操作见 `D:/riscv/RISCV/tests/c_app/README.md`。

`run.py --build <已审查构建目录>` 复用 `sim/bsp_workflow/tb/tb_applications.v`、真实 SoC RTL、Loader ROM/RAM 和带延迟 DDR 用户口模型，完整运行新应用的 LOAD/VERIFY/RUN 及用户 main。用户 main 被自动包装，BSP 自检执行一次；程序返回后自动输出结束标记。默认加速 UART 字节传输，保留真实 MMIO/FIFO 和 CPU，未执行 DDR PHY 训练。

`build/<构建名>/results.json` 为仿真结果，`application_uart.txt`、`uart_rx.bin`、`uart_tx.bin`、`cases.json`、`ddr_trace.csv` 和 ModelSim 日志作为门控证据；实板日志单独放 `board/`。

`check.py --build <已准备目录> --output <新文件>` 检查分片协议收发、错误 CRC/短写/意外 RX 停止、输出/结束标记/返回值/超时、BIN 与仿真证据变更拒绝、禁止覆盖日志及离线夹具不能作为实板证据。夹具不打开串口。

`check_build.py` 在独立目录检查无 main、编译错误、BSS 超限、M/C 扩展指令及不支持的分配段会被拒绝。失败产物保留。

本次最终版本的两个完整仿真在 `build/20261010_161146_75750db9/` 和 `build/20261010_161206_bc470150/`，各 25 个响应、一次 RUN，全算法输出精确匹配。19+19 项离线检查为 `offline_final_main.json`、`offline_final_second.json`；6 项编译/ISA/布局拒绝为 `build_checks/6ebd9f0c/results.json`。此前开发中间目录保留历史，是否可部署看当前门控哈希，不套用旧准备结果。

当前新入口实板 NOT_TESTED；用户完成测试后用 `tests/c_app/run_app.py --verify-log <实际日志>` 离线核验。
