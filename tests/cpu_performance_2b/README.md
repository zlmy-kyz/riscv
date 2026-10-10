# 2B 独立测量软件

本目录只新增计数读出。算法、统一 BSP、原成功 CoreMark BIN、Loader DAT 都保留。
`perf.c/.h` 通过 32-bit MMIO 配置和读取 13 个冻结的 64-bit 计数器，再通过既有 UART 打印。
测量 BIN 在 `portable_init` 的 BSP 自检后 CANCEL → START_PC=0 → STOP_PC=0 → ARM；
下一次 CYCLE 接受边沿 S 开始，第二次 CYCLE 接受边沿 T 冻结，统计 `[S,T)`。
打印在 CoreMark 的 `PORT_DONE` 之后，排除下载、CRC、BSP 自检、算法结果打印与计数器打印。

验收版本：`build/measure_20261010_c/{performance_1,validation_1,performance_60,validation_60}`。
四个 BIN 已独立构建/ISA/布局审查；两组 1 次完整 CRC 与 MMIO/UART 读出通过。
60 次仿真只覆盖下载/VERIFY/RUN/启动，完整正式测量待用户实板。
`measure_20261010_a/b` 为早期未验收软件，已清理；最终c版本保留。

```powershell
C:/python/python.exe tests/cpu_performance_2b/build.py --tag new_tag
```

新 tag 拒绝覆盖。保持 RV32I/ILP32、GCC15.2.0、-Os、无 LTO、2000-byte buffer、93.75MHz。
后续硬件基线和优化候选必须使用逐字节相同的测量 BIN。不能把测量 BIN 与旧成功 BIN 的布局差异解释为硬件提速。
`start_time/stop_time` 地址仍为 `0x400007d0/0x400007f4`；硬件另支持原成功 BIN 的 PC 标记自动窗口，但原 BIN 没有 UART counter dump。

寄存器、统计口径、证据和实板命令见 [2B 记录](../../doc/cpu/CPU性能计数器2B_MMIO与隔离候选_2026-10-10.md)。
