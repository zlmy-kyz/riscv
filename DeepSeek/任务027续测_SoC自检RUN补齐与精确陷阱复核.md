# 任务027续测：SoC自检RUN补齐与精确陷阱复核

当前唯一待领取入口。原027 **STOPPED_FIRST_FAILURE** 已由Codex核原始证据：control8、前六组426通过；key于51575ns同步陷阱FAIL，原日志无cause/PC/tval，两ISA未执行、git_after缺失。原目录35文件完整冻结，不清理、复用或补造；不得再执行原027入口。

## 定位与修订范围

Codex静态发现原SoC测试程序直接写TEST_STATUS=2，却从未写TEST_STATUS=1。现有simple_mmio只允许IDLE→RUN→PASS；IDLE写PASS返回error，CPU将store错误映射cause7。原日志没打印陷阱字段，所以**静态已证实程序缺陷，但原51575ns陷阱是否确由此触发尚待精确复现**，不能写成已观察cause7或RTL无回归。

主桥b64f756d、CPU3faf81a6、数据互连e8582e27、SoC3fdbe2f5，全部137登记源、8冻结软件及IP/Loader保持027失败时身份。原TB/模型/生成器/程序/清单/判据不改。新增续测TB复用相同DDR模型和SoC观察判据，只进入尚未完成的SoC组；新测试程序仅在末段LUI x10之后增加一条`sw x6,16(x10)`（x6=1，写RUN），PASS仍写2。RUN不会提前结束CPU观察；独立oracle继续到PASS。

新正确路径414架构事件（多一条RUN），64load/67DDR store/1IRQ、内存64/2080/1/1不变。前六组426、关闭控制8直接复用原证据，无历史桥、CoreMark或旧CPU重跑。新增逐事件/总线日志与同步陷阱字段，仅观察，不驱动DUT。

## 固定输入与单次执行

tag：**ds_mini_write_buffer_soc_resume_20261013_a**。

清单：`sim/mini_board_migration/write_buffer_soc_resume_inputs.json`；SHA256 **98aa2479a5fe08c3dfcf37d7af94a78752760f35fd596d6280272a6f96e001ea**。

236工程输入+10外部、13执行副本、37唯一模块；含旧189输入、失败目录35文件/失败复核收据及新入口。主设计完整SHA仍见原任务027清单，不重新冻结或更新历史身份。Codex静态检查/程序离线oracle/PowerShell语法/离线P-V计划通过，新HDL未执行。

```powershell
Set-Location 'D:\riscv\RISCV'
python -B sim/mini_board_migration/run_write_buffer_soc_resume.py --check-inputs
python -B sim/mini_board_migration/run_write_buffer_soc_resume.py --tag ds_mini_write_buffer_soc_resume_20261013_a
```

只启动第二条一次；新目录须不存在。一次vlib60秒、vlog60秒，四次独立vsim-batch各180秒：**old_program → soc → isa_or → isa_lhu**。使用新库、不加载旧失败库；真实I/D DRM、mul、ROM/RAM、CPU/SoC/MMIO/UART及厂家原语同原37模块，顶层名称变为tb_write_buffer_soc_resume，ISA顶层保持。

1. `old_program`：仅原SoC组的一次最小故障复现，使用冻结原程序。严格要求观测trap PC **4000007c**、指令 **00b52823**、cause **7**、tval **10000010**；陷阱前412事件/IRQ1/67AW-W/busy0/selftest0/无RUN且PASS写一次、PERF DONE3/冻结AW67。只有全部匹配才以`RESULT: PASS write_buffer_old_program_diagnosis events=412 original_functional_status=FAIL`结束，含精确DIAG_TRAP与CHECK。这是**诊断预测匹配**，不是原程序功能PASS，更不改写原失败结论。其它trap/提前失败/不收敛均首次失败停止，不转下一job。
2. `soc`：新RUN程序、严格无同步trap，`CHECK: real_soc_fence_irq_stop PASS checks=414`及唯一`RESULT: PASS write_buffer_soc_resume tests=414 cpu_events=414 IRQ=1 early_acks=… I_OVERLAP=… FENCE_WAIT=… IRQ_WAIT=… STOP_WAIT=… fills=1 updates=65`。五覆盖值均正，67store入条=67W完成/0取消；RUN/PASS各一次、selftest2、handler1、最终数据不变、PERF冻结AW67。FENCE/IRQ/MMIO/字节缓存/前后端守恒原判据保持。
3. `isa_or`、`isa_lhu`：原未完成两样本，seed2026101327不重选；严格5trap（4个启动cause2/tval编码/目标及结束ECALL cause11）、tohost1/muls0，分别匹配冻结530/320架构事件。ISA TB/ROM/RAM/参考表保持，不重跑旧CPU或扩大ISA。

四job皆正常finish、exit/native0、未超时、ErrorsWarnings0、无FAIL/Fatal/RPC，console/transcript归一同。old_program/soc各四条原04030130完整保留。两个SoC job均必须有非空events.log，含EV/BUS；诊断trap字段在console和trace中可查。新成功收尾才生成git_after，验证输入/13副本/Git一致并汇总426+414=840当前关键检查，另control8复用；不能称原839全部在本tag重跑PASS。

首次**非预期**失败保留停止：不重试/换tag/清理、不改超时/权限/RPC/源码/判据/清单、不补造缺失文件。不执行PDS/串口/上板/Git提交推送，不跑前六组/旧control/物理PHY/CoreMark/Hello/历史全套。

## 交付

原始产物：`sim/mini_board_migration/build/ds_mini_write_buffer_soc_resume_20261013_a/`。

报告：`DeepSeek/任务027续测_结果_ds_mini_write_buffer_soc_resume_20261013_a.md`。逐命令argv/exit-native/时间/超时、模块编译与加载、精确陷阱/414事件/覆盖/两个ISA轨迹，提示、事件trace、输入/快照/Git/旧35文件保持和未覆盖范围都写实。若故障预测不吻合，记录真实字段并停止，不能自行放宽。

Codex随后只读review_write_buffer_soc_resume.py核原始证据并组合原控制8/前426；完整PASS才开放run_write_buffer_soc_resume_measurements.ps1的功能门。用户自行PDS生成/下载，Codex直接给PowerShell COM9同冻结P300/V300各一次，不例行核位流。新wbuf_300_01目录、成功turnover_300_01 P283353216/V282589565cycles对照不变；新实际收益未测，x16仅静态。[同阶段记录](../doc/cpu/MINI_单条顺序写缓冲与SoC排空接入_2026-10-13.md)。
