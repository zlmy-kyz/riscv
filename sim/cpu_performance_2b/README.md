# 2B MMIO 硬件计数器验证

设计直接维护在 `myriscv/{mycpu_sync,soc_top,simple_mmio}.v`，根目录 `RISCV.pds` 使用原路径。
CPU 只增加观察输出，流水线控制与原 32-bit 请求/响应接口保持原逻辑。重复候选设计和未使用的独立PDS工程已清理。
PDS 编译/综合/布局布线/比特流生成由用户执行；IP/成功镜像保留。

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
