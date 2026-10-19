# ModelSim -c复测（2026-10-19）

用户要求重新测试。`check.py`和`tool_health.v`原样复制自`../modelsim_health_20261018_a`，旧目录保持。

执行命令：

```powershell
python sim/modelsim_health_20261019_retest_a/check.py
```

结果：IPv4 127.0.0.1与IPv6 ::1回环listen/connect均成功；vlib/vlog退出0，编译Errors/Warnings0；两次ModelSim DE-64 10.6c的-c加载/运行均至1ns，出现`TOOL_KERNEL_OK time=1000`，退出0、Errors/Warnings0、无RPC_Init、无超时。完整argv/cwd/实际退出码在`results.json`，原输出在`vlog.log`、`kernel_1.log`、`kernel_2.log`和对应transcript。当前-c最小HDL运行恢复。

只检查工具，不运行RISCV工程/IP/043功能测试、PDS或实板；GUI未测。未改系统/代理配置，也未复核用户具体配置变更，不能将恢复归于某个未经确认的操作。历史失败证据保留。再次运行会覆盖同名复测输出；今后复测使用新目录。
