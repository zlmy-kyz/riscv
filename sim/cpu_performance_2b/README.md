# 2B MMIO 硬件计数器验证

最新实板结果：performance_60_retry1补测通过，六应用6/6 PASS，564协议响应及主门控身份一致。正式performance/validation为17.758519147/18.761056267秒、CPI33.440103/33.216176、IF等待60.1906%/60.8206%。完整成功汇总/四份计数CSV/六份冻结日志在board/main_pds_first/audit_retry1_20261010_a；原人工复位中止及audit_20261010_b的5/6历史保留。详见[实板完整统计与补测记录](../../doc/cpu/CPU计数器2B首轮实板统计与补测_2026-10-10.md)。

离线入口：`python -B sim/cpu_performance_2b/check_board.py --logs sim/cpu_performance_2b/board/main_pds_first --tag <新tag> --performance-60-log sim/cpu_performance_2b/board/main_pds_first/performance_60_retry1.json`；不打开串口，六应用全部通过才返回0，否则返回2并保留部分结果。明确选择补测日志，避免覆盖/误用原中止记录。本轮只审查日志，不修改RTL、重跑仿真或PDS。

设计直接维护在 `myriscv/{mycpu_sync,soc_top,simple_mmio}.v`，根目录 `RISCV.pds` 使用原路径。
CPU 只增加观察输出，流水线控制与原 32-bit 请求/响应接口保持原逻辑。重复候选设计和未使用的独立PDS工程已清理。
PDS 编译/综合/布局布线/比特流生成由用户执行；IP/成功镜像保留。

用户21:13新主位流离线审查入口为 `python -B sim/cpu_performance_2b/review_main_pds.py --tag review_new`（从根目录执行，用新tag）。用户22:20补导出后，main_pds_review_20261010_d为ARTIFACT_AUDIT_PASS；新门控main_pds_board_20261010_a冻结输入并已绑定perf_2b上板工具，其NOT_TESTED为创建时状态，最新实板见上文。审查脚本只读取产物，不执行PDS/仿真/串口，不创建部署门控；退出码0不等于审查PASS，须检查JSON状态。通过后的冻结由freeze_main_pds.py另行执行，不覆盖旧门控。详情见[新位流审查](../../doc/board/CPU计数器2B主工程新位流审查_2026-10-10.md)。

```powershell
C:/python/python.exe sim/cpu_performance_2b/run.py --suite oracle --tag oracle_new
C:/python/python.exe sim/cpu_performance_2b/run.py --suite coremark --engine functional --tag crc_new
C:/python/python.exe sim/cpu_performance_2b/run.py --suite micro --engine physical --tag physical_new
C:/python/python.exe sim/cpu_performance_2b/main_rtl.py --suite fast --tag rv32i_new
C:/python/python.exe sim/cpu_performance_2b/main_rtl.py --suite irq --tag irq_new
C:/python/python.exe sim/cpu_performance_2b/main_rtl.py --suite mmio --tag mmio_new
C:/python/python.exe sim/cpu_performance_2b/main_rtl.py --suite ddr --tag ddr_new
C:/python/python.exe sim/cpu_performance_2b/loader.py --application performance_1 --tag load_crc_new
C:/python/python.exe sim/cpu_performance_2b/check_transport.py --tag transport_new
```

`run.py` 在真实 CPU/共享 DDR 桥下将 13 个硬件计数与独立 2A observer 比较；
`physical` 使用完整 Pango IP/PHY/物理 DDR 模型，128-bit 用户口写入/全量回读载荷后释放 CPU。
固定九窗口微基准不改 BIN，硬件以无 PC 过滤的自动 ARM 统计首个窗口，后八窗口由 observer 做行为回归。
因此九窗口行为 PASS 不等于九个硬件计数窗口；完整 CoreMark 两个软件 ARM 窗口另外验证硬件/MMIO/打印。
`functional` 使用延迟用户口模型，只作正确性与窗口验证，不能作真实 DDR 性能证据。

两条 DDR 定向 Tcl、RV32I、并发/背压、32 个 CPU IRQ、2 个 UART IRQ、总线/access-fault/UART MMIO/CPU 和六应用 Loader 仿真沿用原 TB 判断，输出隔离。
FENCE.I/ma_data 失败在原 RTL 复现一致，保持既有范围，不包装成支持。
Hello 的 Loader 传输按原速 UART 引脚验证；较大的 CoreMark 下载使用快速字节传输，但真实 UART FIFO/MMIO 和 CPU 执行链路不变。

事件增加一级寄存：边沿 E 的采样在 E+1 加入计数；T 边沿写入最后一个 `[S,T)` 样本，DONE 后银行完整冻结。
主路径六组回归与统计见 `build/main_integration_20261010_a.json`。
早期 PDS a 的时序失败报告及最终 PDS b 的成功报告/位流作为历史证据保留，不重用为用户新实现的验收结论。
旧输入副本在 `build/frozen_inputs`，旧门控JSON及日志保留。旧candidate生成/审查脚本已清理；用户重建主工程后，另行审查和绑定新位流。
Codex 不打开串口，不操作板子。当前入口见[主RTL集成](../../doc/cpu/CPU性能计数器2B并入主RTL_2026-10-10.md)，计数口径见[2B设计](../../doc/cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)。
