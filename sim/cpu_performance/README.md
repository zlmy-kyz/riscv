# CPU/DDR 性能测量 2A

仅新增仿真 observer 和独立软件，CPU/互连/DDR 桥/成功 BIN/主 IP/位流不改。输出目录必须使用新 tag；失败日志也保留，不清理或覆盖旧成功证据。

```powershell
C:/python/python.exe tests/cpu_performance/build.py --tag measure_new
C:/python/python.exe sim/cpu_performance/run.py --suite oracle --engine functional --tag oracle_new
C:/python/python.exe sim/cpu_performance/run.py --suite micro --engine functional --timer-wrap --tag wrap_new --micro-build tests/cpu_performance/build/measure_new
C:/python/python.exe sim/cpu_performance/run.py --suite micro --engine physical --tag physical_new --micro-build tests/cpu_performance/build/measure_new
C:/python/python.exe sim/cpu_performance/run.py --suite coremark --engine functional --tag crc_new --micro-build tests/cpu_performance/build/measure_new
```

`physical` 编译当前 Pango IP、PHY、Micron x16/4Gb/sg25E 物理模型，保留厂家 `IPS_DDR_SPEEDUP_SIM`、`RTL_SIM` 等现有仿真定义，时间检查不关闭。仿真派生包装器通过同一真实 128-bit 用户口写入 DAT payload，每拍回读比较、检查 RLAST/RID 后才同步释放 CPU，CPU 从 DDR 入口执行。测量时用户口 mux 完全选择原共享桥，所有取指、数据访存均经过真实控制器/PHY/DDR 模型。装载与训练不计入窗口。它不是生产 Loader/板级复位验收。

`physical-copy` 使用原 `soc_ddr3_top` 和仿真 ROM copy-loader；前置装载慢，可用于启动路径补充检查。`functional` 使用现有带背压用户口模型，证明计数/退休/CRC功能；其 cycles/CPI/延迟只供模型诊断，不能作为实际 DDR 性能或实板预测。CoreMark 两组使用已有 BSP 的 `performance_1`/`validation_1` ELF/BIN，并重新审查原 manifest，不重建成功 BIN。正式60次仍以实板成功证据为基线。

`setup-functional` 单验派生初始化包装器，使用显式命名的用户口 stub 和空物理管脚模型；其 `performance_evidence=false`，不能用于 DDR 性能。直接 DDR 复位入口必须同时保留 `.INST_ROM_BASE(0), .DATA_RAM_BASE(0)`，避免这两项随 RESET_PC 默认移动而覆盖 DDR 地址译码。

`perf_monitor.sv` 在 pre-NBA 时钟边沿采样，窗口为 `[S,T)`。S 包含、T 排除；`cycles` 必须等于两次 MMIO CYCLE 锁存值的模 2^32 差，`instret=normal_retire || mret_commit`，异常指令不退休。主周期分类按 control redirect → MEM wait → control hold → load-use → branch recovery → IF starvation → other 的优先级互斥；分类和等于 cycles。`cycles` 不要求等于 instret 加等待数。

分支恢复从 ID redirect 开始，直到目标进入 IF/ID；目标交付边沿不计恢复，异常/MRET取消恢复。包含 JAL/JALR。只统计主分类中未被高优先级原因占用的恢复周期，不能解释成可被 BTB 全部消除的周期。

DDR transactions=ARREADY&ARVALID 命令数 + AWREADY&AWVALID 命令数。R/W beats、桥状态驻留、两路竞争、背压/未完成请求/丢弃响应另记，可重叠且不能累加为总 stall。无标准 AXI4 B/RREADY/WVALID 假设。

两路请求只允许一笔 outstanding；旧响应先完成再接受同周期新请求。每个窗口检查 requests-responses=pending_end-pending_start。延迟直方图统计窗口内完成的响应，允许请求发生在 S 前，T 时未完成者截尾；4096 桶表示 >=4096 周期，不把它当精确值。data 延迟包括计时 MMIO，与 DDR load/store 混合，解释时查看 bridge_data_requests；本批没有窗口内 UART/RAM workload，不覆盖分后端计数实现。

`metrics.csv`、`latency.csv`、`retire_pc.csv`、`timer.csv` 是原始数据；微基准还有完整 `retire_trace.csv`，由独立 RV32I 解释器逐条校验 PC、RF写入、load/store结果及窗口退休数。CoreMark通过真实 UART 引脚解码、接受字节对比及原输出校验器检查完整 CRC；PC histogram 校验总和等于 instret。函数 profile 仅给动态指令占比，不给物理 stall/时间占比。

Oracle 覆盖互斥优先级、MRET、丢弃、同边沿 turnover、窗口边界、64-bit carry；还要求错误额外响应、重复请求及无 start 的 stop 被拒绝。`--timer-wrap` 只在功能微基准中预置既有 MMIO 计数状态来跨越 32-bit wrap，不用于性能测量。

每轮保存输入清单、编译/仿真日志、派生源及源快照。原 RTL/IP/PDS/主要成功 BIN/主位流前后 SHA256 必须相等。ModelSim PASS、Errors:0 和无物理 ERROR 同时检查；训练 warning 的具体来源另记。Windows Python、ModelSim、GCC、Pango 路径沿用工程入口。

可用 `C:/python/python.exe sim/cpu_performance/reanalyze.py <结果目录>` 重核原始 CSV/CRC；`--canonical-micro-build` 只允许同 BIN、同 marker/checksum 的说明字段修正，不更换 workload。实现硬件计数器、任何桥/cache/CPU优化、新位流和实板性能分解都需下一阶段。
