# CoreMark 裸机独立实验

使用工程根目录 `coremark-main/` 的五个原版算法/主程序源和 `coremark.h`，不修改其字节。
平台文件由官方 barebones 模板移植：整数 `ee_printf`、轮询 UART、MMIO 周期计时。
`core_main.c` 自带 main，本目录不另造 main.c。无 libc、无 IRQ、无浮点、无 LTO，
RV32I 软件乘除由匹配 ILP32 libgcc 提供。

从工程根目录执行：

```powershell
& ./tests/coremark_baremetal/build.ps1 -Mode performance -Iterations 1
& ./tests/coremark_baremetal/build.ps1 -Mode validation -Iterations 1
& C:/python/python.exe sim/coremark/run.py --audit-only
& C:/python/python.exe sim/coremark/run.py
```

默认统一 `-Os`，`-Optimization O2` 可作尺寸比较。`-OutputDirectory` 可隔离构建，
最终产物在 `build/performance/` 和 `build/validation/`，各有 ELF/BIN/DAT、map、
反汇编、段/ABI信息、栈用量 `.su`、构建日志及参数。构建只写 build，不覆盖其他实验。
BIN 超过 16368 字节会拒绝生成 DAT，原版 `-O2` 首次构建超限。

配置：TOTAL_DATA_SIZE=2000、MULTITHREAD=1、MEM_STATIC、SEED_VOLATILE、
MAIN_HAS_NOARGC=1、HAS_FLOAT/HAS_TIME_H/USE_CLOCK/HAS_STDIO/HAS_PRINTF=0。
DDR 入口 `0x40000000`，64 KiB 链接区，顶部 4 KiB 栈；初始化数据 LMA=VMA，
BSS由 startup 清零，不进入BIN。DAT尾16字节为现有ROM loader清单。

计时读 `0x10000008`，93,750,000 ticks/s，32位无符号差支持一次跨界，
要求单次测量低于约45.81秒。整数秒截断保留原算法行为；`PORT_DONE` 额外打印
ticks/iterations/hz，只标记软件完成，不表示 CRC 或正式分数有效。
UART读 `0x10001008` 的TX_READY，SB写 `0x10001000`，115200 8N1。

短迭代不足10秒时原版程序保留 `ERROR! Must execute ...` 和 `Errors detected`。
验收必须独立核对种子和list/matrix/state/final CRC、计时、UART引脚及异常，
不能用main返回0、PORT_DONE或LED作为PASS。短测试不报告CoreMark分数。
2026-10-07用户侧已将板级RAM IP指向本实验performance/main.dat并反馈短迭代串口，
用户已提供performance与validation单迭代UART文本，两组CRC功能检查通过；
后续两组实板60次已完成CRC与至少10秒验收，结果见下文；尚无独立时钟校准。
本实验脚本不自动切换IP、PDS实现或下载；RAM/ROM深度无需调整，需要调整时先告知用户。
验收凭据与未覆盖范围见 `doc/coremark/CoreMark裸机构建与短迭代CRC_2026-10-07.md`。

60次候选独立构建入口为`./tests/coremark_baremetal/build_60.ps1`，随后执行
`C:/python/python.exe sim/coremark/run.py --iterations 60 --audit-only`及完整Full Boot
`--iterations 60`。2026-10-07两组60次Full Boot均CRC_FUNCTIONAL_PASS，ModelSim Errors0/Warnings0；
BIN分别13220/13228字节，final CRC分别a14c/6770，验收后文件哈希一致。
原构建在build/performance_60/main.dat和build/validation_60/main.dat。
模型计时约7.85/8.31秒，保留原版时间不足错误；随后用户两组实板60次验收PASS，
ticks分别1664676818/1758636430，即17.75655/18.75879秒，CRC全部匹配且无错误。
performance按配置93.75MHz及ticks计算约3.379034迭代/秒；整数打印3是截断。
成功DAT原字节归档在verified/performance_60/main.dat和verified/validation_60/main.dat，
各有verified_image.json，不受build.ps1覆盖；重现使用归档原DAT，不另生成后直接部署。
记录见`doc/coremark/CoreMark实板60次验收_2026-10-07.md`，精确吞吐按配置频率计算。
详细构建/验收/PDS上板步骤见`doc/coremark/CoreMark_60次迭代构建与上板步骤_2026-10-07.md`。
