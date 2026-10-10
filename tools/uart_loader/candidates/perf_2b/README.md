# 用户操作的 2B 候选上板工具

当前主设计已迁入myriscv，用户将从根目录RISCV.pds重新实现；以下工具/门控仍绑定此前历史位流，等待用户新产物审查与重新绑定，不能直接用于新主位流。当前入口见[主RTL集成](../../../../doc/cpu/CPU性能计数器2B并入主RTL_2026-10-10.md)。工具代码保留用于后续MMIO/UART读出。

仅接受 `sim/cpu_performance_2b/build/deployment_gate.json` 白名单中的六个 manifest 和候选位流。
旧 BSP/rebuilt 工具继续绑定旧成功硬件，不能用旧门控部署 2B。
Codex 只运行 `--plan-only` / `--verify-log` 和离线 mock；实际 COM11 操作由用户执行。

用户在 PDS 配置下载窗口选择：

`D:/riscv/RISCV/sim/cpu_performance_2b/build/pds_20261010_b/generate_bitstream/board_top.sbit`

SHA256：`dc5121b8857a08c053698def358cc07f3be083252cb0b7274f27e6277b5dbb46`。
下载后关闭串口助手。每个命令会提示 KEY0/DDR ready，再打开 COM11，115200 8N1。
日志不覆盖，RUN 不重试。先 Hello、CRC32、两组短 CRC，再运行匹配正式 60 次。

```powershell
$perfTool = 'D:/riscv/RISCV/tools/uart_loader/candidates/perf_2b/run_board.py'
$perfLogs = 'D:/riscv/RISCV/sim/cpu_performance_2b/board/first'
& C:/python/python.exe $perfTool --application hello --log "$perfLogs/hello.json"
& C:/python/python.exe $perfTool --application crc32 --log "$perfLogs/crc32.json"
& C:/python/python.exe $perfTool --application performance_1 --log "$perfLogs/performance_1.json"
& C:/python/python.exe $perfTool --application validation_1 --log "$perfLogs/validation_1.json"
& C:/python/python.exe $perfTool --application performance_60 --crc-log "$perfLogs/performance_1.json" --log "$perfLogs/performance_60.json"
& C:/python/python.exe $perfTool --application validation_60 --crc-log "$perfLogs/validation_1.json" --log "$perfLogs/validation_60.json"
```

各命令结束自动独立复核原始协议帧和计数打印。正式模式要求本候选同 gate/位流/模式的短测量 BIN 实板 CRC 日志。
离线计划不会打开串口：`--application performance_60 --plan-only --log <新路径>`。
已有实板日志可离线重核：`--verify-log <日志> --output <新审查JSON>`。
有效实板结果包含 cycles/instret/CPI/IF/MEM/branch/DDR 命令，以及 CRC、时间、93.75MHz 和候选位流身份。
目前实板为 NOT_TESTED；不能把离线计划或模拟串口 fixture 当实板证据。
