# ModelSim工具诊断（2026-10-18）

仅检查本机工具，不代表RISCV工程、厂家IP或任务043功能验收。工具路径为`D:/modelsim/win64pe`，DE-64 10.6c。系统时间原文保留在日志；本文日期使用用户会话日期。

## 所见结果

- `vsim -version`、`vlog -version`及不加载设计的`vsim -c -do "puts {TOOL_STARTUP_OK}; quit -f"`成功。
- `vlib work`与`vlog -work work tool_health.v`退出0，编译Errors/Warnings0。
- 默认环境两次`vsim -c -onfinish exit -l transcript_N.log work.tool_health -do "run -all; quit -f"`均RPC_Init IPv6 socket错误，20秒超时终止，未出现HDL标记。
- 经批准沙箱外同一空模块-c加载亦失败，15秒超时；`outside_results.json`保存完整argv，`outside.log`保存合并stdout/stderr。
- 默认与沙箱外均IPv4回环成功、IPv6回环WinError10013。未确定具体系统策略原因。
- `-batch`加载同一空模块并执行至1ns成功：标记`TOOL_KERNEL_OK time=1000`，退出0，Errors/Warnings0，见`batch_transcript.log`、`batch_console.log`与`batch_exit_code.txt`。该结果同时证明本次最小Verilog内核运行成功，未观察到授权错误。

## 命令

本次默认诊断命令（已执行，不需重复）：

```powershell
python sim/modelsim_health_20261018_a/check.py
```

本次成功batch命令，工作目录为`D:/riscv/RISCV/sim/modelsim_health_20261018_a`：

```powershell
& 'D:\modelsim\win64pe\vsim.exe' -batch -onfinish exit -logfile batch_transcript.log work.tool_health -do 'run -all; quit -f'
```

`check.py`用于记录此次故障复现，包含失败的-c调用，并非后续工程执行入口；再次运行会覆盖同名诊断日志。后续诊断应选新目录保留本轮身份。

## 边界

本轮没有改系统网络、防火墙、hosts、注册表、许可证或工具安装；没有运行工程功能仿真、PDS或实板。GUI未测。标准batch是本次已证实可用的最小运行模式，不能保证任意工程脚本/IP均可运行。系统IPv6未修复，不把历史失败改写为PASS。
