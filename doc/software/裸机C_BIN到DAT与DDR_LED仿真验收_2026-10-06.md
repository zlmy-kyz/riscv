# 裸机 C BIN 到 DAT、DDR 执行及 LED 状态验收

日期：2026-10-06（Asia/Shanghai）。对应 CODEX_HANDOFF 第 12.1 项。

## 目的和改动

先运行既有 100 字节 C BIN，再用独立候选 C 验证非空 `.data/.bss` 与 LED 上报。
新增 `sim/baremetal_c/bin_to_dat.py`、`led_main.c`、`tb_baremetal_c.v`、`run.py`、
README 和局部构建忽略规则。复用 `tests/development/startup.S/linker.ld`。

没有修改 CPU/总线/DDR 桥/UART/LED 生产 RTL；既有 LED 已支持所需状态，
只在新 TB 的实例中缩短计时参数。没有修改主 PDS/FDC、存储 IP 或板级镜像。
没有覆盖原始 `tests/development/main.c`、`tests/development/build/main.bin`。

转换按 32 位小端打包，RAM DAT 4096 字，末 16 字节放现有 loader 清单。
原始 BIN 为 25 字；状态候选为 332 字节/83 字，其中 `.data` 8 字节、BSS 32 字节。
DDR 基址 0x40000000，64 KiB 仿真内存覆盖栈；初始全部毒化为 A5A5A5A5。
CPU 从 ROM 地址 0 读取装载程序，从 RAM 接收 payload，经过真实桥写入 DDR
后跳转。模型未直接预加载 C 指令或将 BSS 清零。

## 复现

在 D:/riscv/RISCV 根目录：

```powershell
# 原始产物缺失时运行，验收本身读取现有产物
& ./tests/development/build.ps1
& C:/python/python.exe sim/baremetal_c/run.py --simulator iverilog
& C:/python/python.exe sim/baremetal_c/run.py --simulator modelsim
```

单独转换：

```powershell
& C:/python/python.exe sim/baremetal_c/bin_to_dat.py tests/development/build/main.bin sim/baremetal_c/build/converted
```

## 实测结果

ModelSim 与 Icarus 各 4/4 PASS，ModelSim 编译和逐例运行 Errors 0 / Warnings 0。
候选 C 链接仍有既有 RWX LOAD warning，不影响本次裸机执行。

| 用例 | 实测 |
| --- | --- |
| original | CPU 搬运 25 字；a/b/c 在 0x4000FFF4/FFF8/FFFC 为 10/20/30；0x40000060 退休 8 次；873 cycles；status=IDLE，LED 灭 |
| led_pass | CPU 搬运 83 字，startup 清零 8 个 BSS 字；结果 10/20/30；RUN 慢闪后 status=PASS/LED 常亮；6880 cycles |
| injected_fail | 相同算术结果，故意要求 c=31；软件 status=FAIL，观察到 28 次快闪切换；6880 cycles；这是预期失败路径验收 PASS |
| timeout | 原始 C 继续退休，status=IDLE；30000 拍 watchdog 超时，观察到 19 次快闪切换；30079 cycles |

原始/候选 main 都为 0x4000003C；候选停循环为 0x40000134。
运行时核对 startup SP 写回 0x40010000、最终 C SP 0x4000FFF0。
自动比较 loader 接受的每字地址/内容/strobe、首次 DDR 取指前的全 payload，
检查 BSS 在装载后仍为毒值、startup 顺序清零、main 首条退休时全部为零。
验收也检查真实退休循环、总线错误/同步异常、LED RUN 与 FAIL 切换周期和心跳。

证据目录：`sim/baremetal_c/build/{original,led_pass,injected_fail,timeout}/`。
逐例包含 `main.dat`、`boot_rom.dat`、`manifest.json`、`acceptance.json`、
ELF/BIN、反汇编、`modelsim.log` 与 `iverilog.log`。
汇总为 build 下的 `modelsim_results.json`、`iverilog_results.json`，含保护输入 SHA256。

## 未覆盖范围与下一步

这是真实 CPU/SoC/桥配合 Pango 用户口模型的功能仿真，不含 DDR IP 训练、PHY
或物理内存模型；本步骤没有重跑完整 DDR 物理联仿。没有新 PDS 时序/bitstream
或下载、实板 LED/串口结果；主板级启动仍为原 DDR 自检。
不涉及 UART 装载、printf/libc、C ISR、模型推理或 CoreMark。

LED TB 的加速参数不表示实际板级时钟改变。原始 C 仍不写 TEST_STATUS，
板级部署应选带状态上报的候选；当前 332 字节候选不占原自检诊断地址 0x40001000。
后续如选板级部署，须核对候选布局、重新生成相关存储 IP、完整板级联仿和 PDS
实现，再分别记录镜像生成、时序、下载及实板结果。
