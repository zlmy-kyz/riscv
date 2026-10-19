# 任务023：CPU硬件乘法Zmmul真实IP关键仿真

## 当前唯一入口

工程`D:/riscv/RISCV`。先读`AGENTS.md`、`doc/CODEX_HANDOFF.md`顶部新接续入口及`doc/cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md`顶部。本任务已获用户“实现硬件乘法/已生成”授权，只做以下一次关键验证，不另询问继续。任务文件本身不会自动启动DeepSeek。

真实生成实例为`mul`（不是历史建议名cpu_mul）；Signed33×33，全宽66，标准4级、同步高有效reset，Optimal/Advanced关闭。主CPU已接入四条MUL/MULH/MULHSU/MULHU，DIV/REM仍非法、misa.M=0。PDS登记增加实际mul IDF和五份生成源；I64/D64桥d8ae0409…5cf09、Loader INIT、原120次RV32I BIN、旧成功位流保持。

固定tag **`ds_cpu_zmmul_20261013_a`**；输出`sim/cpu_zmmul/build/ds_cpu_zmmul_20261013_a/`，存在即停止，不能换tag、清理、覆盖或重试。开始前必须无用户PDS实现并发；runner检查pds_shell。默认原权限，禁止修改IPv6/RPC/防火墙/权限或追加工具启动预检。

```powershell
Set-Location 'D:\riscv\RISCV'
python sim/cpu_zmmul/run.py --check-inputs
python sim/cpu_zmmul/run.py --tag ds_cpu_zmmul_20261013_a
```

不要重新执行prepare_tests.py，已生成的fixtures/golden是冻结输入。输入检查或任一命令/判据失败立即保留停止，不继续后续用例。只有修订任务授权后才能再次执行；不能自行延长超时或修改判据。vlib/vlog单条60秒，vsim单条180秒，TB独立20ms仿真时间watchdog（原语TB100us）。原生stdout/stderr直接写文件，`vsim -batch -lib <work> <top> <plusargs> -logfile <transcript> -do "run -all; quit -f"`；不用-c/GUI/Tcl内部vsim路径。

## 身份与运行范围

`sim/cpu_zmmul/inputs.json`保护305项工程输入和10项外部依赖（五工具、三厂家原语/两参考），SHA **f8ebb23bb096017e2b373872adc100042732289bc24c242564d9e9c09de6fa86**。

- CPU SHA：`43e451038cc14b3402ff159629d18783fbd8d1364e7c05197fadbb1e8e5d6cfe`。
- PDS SHA：`c5f87d111f751e0f2205fa5471a4002dc88d59c67b3de43f813c47395eaa6916`（只登记IP，不执行PDS）。
- 真实mul IDF SHA：`1f583b2ee87c795c7f7ae41b4c6263703b6bdeeb8f7fb0af7f7932bb22ae9a33`；生成源码身份见清单和preparation/ip_review.json，禁止behavioral stub替代。
- 旧022清单及原始审查保持，CPU/PDS旧版本在preparation目录已冻结；新任务不调用旧022require_inputs或重复022，因为旧清单绑定旧CPU/PDS。

runner一次vlib、一次vlog；编译CPU六模块、生成mul五源、真实GTP_APM_E2/GTP_GRS、两个TB。然后九个固定仿真进程，各单顶层，第一失败停止。实例依赖清单已写死于inputs，不运行厂家随机示例TB。

| 顺序 | 用例 | 验收 |
| --- | --- | --- |
| 1 | mul_ip | 128组33bit signed全66bit产品，连续4级延迟/CE保持/reset恢复，168项断言检查 |
| 2 | math_dependencies | 384组四种32bit乘法边界/随机输入，含负数/INT_MIN/最大无符号/低32溢出；别名、x0、load-use、连续乘法、乘法→addi/store/branch/jalr；2718事件/391条MUL退休 |
| 3 | memory_backpressure | 旧load响应延迟35周期，年轻乘法完成后至少保持2周期、CE关闭、结果不变；15事件/1条MUL |
| 4 | reset_mid_mul | 先不同操作数运行到busy/count2，同步复位后重跑冻结新操作数程序；10事件/1条MUL，无迟到写回 |
| 5 | older_fault_cancel | 旧load error取消已经启动但未退休的年轻乘法，核cause5/tval/mepc，handler跳过故障load后MRET，重新执行乘法仅退休一次；22事件/1条MUL，启动比退休多1，必须观察取消 |
| 6 | irq_drain | busy/count2发MEI，乘法先精确退休，排空后进入handler，mepc为下一PC、cause外部IRQ，MRET后消费者值正确；24事件/1条MUL/1个IRQ |
| 7 | illegal_div_rem_misa | DIV/DIVU/REM/REMU及未知funct7各一次illegal trap，misa写不置M、读40000100；50事件/1条合法MUL/5trap |
| 8 | isa_lhu | 原成功ROM/RAM，tohost=1；允许标准结束ECALL11，禁止其他异常/IRQ/MUL启动 |
| 9 | isa_or | 原成功ROM，tohost=1；同上 |

CPU关键六例合计 **2839个架构事件、396条乘法退休**。Python独立整数oracle事先生成PC/指令/寄存器写值/异常原因和tval/IRQ续执行PC，TB不能把DUT结果填入golden。纯乘法等待不得提前前递/推进、不得记入MEM等待；保留既有性能分类优先级。旧load取消覆盖“完成但未退休”的乘法，reset覆盖busy取消；不能扩大为所有精确异常已验收。

ISA样本种子2026101323，从40个支持且无已知缺口的目录排序后random.sample选择`lhu`、`or`；排除fence_i/ma_data，仅两例抽测PASS，不能写全ISA PASS。不运行旧版对照、历史ISA全集、Hello/CoreMark/DDR桥/PHY回归。

## 交付与结论边界

必须逐一核vlib/compile/九个仿真command.json退出0、无timeout；compile和每条仿真Errors/Warnings0；每例唯一对应CHECK及RESULT PASS、正常$finish，console/transcript换行归一后一致、transcript非空，RPC_Init零出现。原语非错误IP提示保留，不滤掉。runner完成后result.json必须PASS且completed九项按序；运行前冻结305项副本/input manifest，git_before/git_after一致、最终inputs重新核对一致。结果卡片给出CPU/IP/清单SHA、事件/退休数、两例ISA、所有实际时长和文件路径；不能只读runner摘要宣布PASS。

失败时交原始失败命令/阶段/完整日志、已完成与未执行用例，功能标INCOMPLETE或日志确证的FAIL，不把环境终止当RTL功能FAIL。不为了补git_after而自行重试。

只允许runner生成本tag中的work/日志/身份副本及DeepSeek结果报告。禁止修改RTL/PDS/IP/fixture/oracle/清单/超时/成功镜像，禁止PDS实现、串口/实板、Git提交推送。Codex收到报告后核原始证据并继续准备新ISA软件及用户最终PDS/上板；当前仅CPU直连接口+真实乘法原语，不代表完整SoC/DDR PHY/时序/资源/实板性能PASS。
