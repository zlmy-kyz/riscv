# 任务011：UART等待计数链关键仿真

先读AGENTS.md和doc/CODEX_HANDOFF.md顶部。本轮只领取011；009/010的数据缓冲桥检查与CPU命中覆盖已审查，不重跑。

用户授权单独精简零延迟UART的32-bit等待链。只改myriscv/uart_mmio.v：零/负延迟分支无计数器，由pending产生下一拍响应；正延迟计数器按参数所需宽度生成。TX/RX/FIFO/IRQ、pending、响应数据/error及副作用主块不变。新UART SHA `0f51c37d806230dff85cdff589ad8b12a4965dc76eb1ed92a88475659001ace7`；桥仍b7c2b366版。详见[实现记录](../doc/cpu/UART等待计数链精简与仿真交接_2026-10-11.md)。**HDL NOT_RUN，时序改善未测量**。

## 唯一执行范围

只执行下列runner：一次Icarus编译+一次vvp运行定向tb_wait_chain，同时验证delay=0/1/2/6四种参数，每种旧/新成对；然后CPU DDR用户口模型只编译一次、运行随机lbu/jal各一次。合计5条HDL工具命令，不运行ModelSim或额外脚本。

单位TB有独立时序/数据判据及串口TX解码、RX引脚刺激；每参数28笔完整事务、1笔复位取消。验证请求接受/下一拍响应、非零等待/保持valid、TX忙/字节lane、RX顺序/每读只pop一次/空读、IRQ控制和清空、非法访问、frame/W1C与复位。旧UART来源为冻结原文件，只把模块名改为uart_mmio_baseline，不改其逻辑；日志必须明确新旧外部输出等价。TB串口采用100MHz/10MHz baud加速，只作功能验证，不能作93.75MHz硬件时序/性能证据。

ISA seed2026101111从40个支持用例抽取lbu/jal，排除fence_i/ma_data。CPU分别装载273/135 words至DDR模型后执行，tohost=1。不把ISA抽测当作UART CPU串口程序或全量ISA验证。

不重跑旧UART底层全套/旧MMIO长TB/IRQ/Loader/CoreMark/201项D桥/其他ISA/物理DDR/九微基准。不运行PDS、Generate Netlist、上板/串口、Git提交推送；不得修改RTL/TB/软件/判据或manifest，遇新失败保留证据后停下，交Codex定位，不自行扩大测试。

## 命令

根目录PowerShell：

```powershell
Set-Location D:/riscv/RISCV
C:/python/python.exe -B sim/uart_mmio/run_wait_chain.py --check-inputs
$task011Tag = 'ds_uart_wait_' + (Get-Date -Format yyyyMMdd_HHmmss)
C:/python/python.exe -B sim/uart_mmio/run_wait_chain.py --tag $task011Tag
```

新wait_chain_input_manifest.json保护46项输入，SHA `72a32da9159df617e6b1a5b1ac0ed4c3fde46afa3f47cb85f6975c01eb0d27e6`。准备镜像/收据在sim/uart_mmio/build/wait_chain_preparation_20261011_a，旧UART及只改模块名的对照在build/wait_chain_baseline_20261011_a。输入变化记录WAITING_INPUT_STABLE并停，不重写哈希。旧任务清单绑定原UART，当前会因本轮UART修改拒绝，不改旧清单绕过。

## 判据与输出

5命令退出0，无FAIL/FATAL/ERROR/timeout；Icarus没有ModelSim Errors字段，分别给出编译warning及日志结果。

- unit.log每个delay=0/1/2/6都必须有4组CHECK PASS；唯一该模式`RESULT: PASS uart_wait_chain delay=N transactions=28 accepted=29 responses=28 decoded=1 canceled=1`。
- unit.log唯一总结果`RESULT: PASS uart_wait_chain_all modes=4`，不得只凭最后一句忽略前面的FAIL。
- lbu/jal各唯一`RESULT: PASS <name> DDR RV32I tohost=1 cycles=...`，CPU loaded分别273/135 words。
- 5份生成镜像与准备版逐字节一致，输入前后SHA不变；runner最后状态`UART_WAIT_CHAIN_KEY_TESTS_PASS`。

全部产物仅在sim/uart_mmio/build/<tag>/：unit/isa编译日志、unit.log/lbu.log/jal.log和5份.command.json，images、两个vvp、result.json及git_before/after。按[结果模板](结果模板.md)写DeepSeek/任务011_结果_<tag>.md，列实际模式计数、装载字数、命令/退出码、warning、输入及未覆盖范围。完整原始证据交Codex审查后才由用户重新PDS核对零延迟等待链是否消失、最终WNS是否非负；本任务不声明时序PASS或实板提速。
