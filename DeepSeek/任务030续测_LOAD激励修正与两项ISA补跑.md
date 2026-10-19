# 任务030续测：LOAD激励修正与两项ISA补跑

当前唯一执行入口。Codex已复核用户交来的三段诊断，确认唯一覆盖缺口为LOAD0：原load_branch_jalr profile1让依赖项到ID时load已离开EX，等待落到MEM；profile0可达LOAD3、455事件仍匹配参考。继续用户已授权的本轮性能优化与相关修复，**明确授权这一个仿真激励档位修正与本入口单次正式执行**，不需再逐步询问继续。

原030失败目录/三诊断/冻结输入全部保留，不刷新原inputs.json，不降低覆盖阈值、不修改RTL/TB/oracle，不重跑已成功control94。Codex此前自行准备的coverage_diag_preparation_20261014_a与run_diag.py尚未执行，**已被本续测替代，不派发**。

## 固定输入

tag **ds_cpu_branch_loaduse_resume_20261014_a**，清单`sim/cpu_branch_turnover/loaduse_resume_inputs.json` SHA **7cb5c88efd5564c271b981aae9a865b8433869496a43d10c39d48f84c2902ccd**；327工程+5外部输入、53执行副本、16模块。CPU仍**b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3**，原inputs.json仍e26f0bac…81dd08，其他136登记源/桥/IP/SoC/时钟/Loader/8软件保持。

唯一激励差异：[新spec](../sim/cpu_branch_turnover/build/loaduse_resume_preparation_20261014_a/key_specs_profile0.txt)第5行load_branch_jalr的profile **1→0**。其余八行、程序ROM、逐退休trace、测试模型、覆盖判据全保持。修正的是load-use测试刺激时序，不改CPU互锁；延迟取指仍由flow_delayed/reset_pending等覆盖。三诊断只用于定位，不替代正式key/ISA验收，其key命令记录未包含完整native/time/timeout字段，新正式runner恢复原生直写与完整元数据。

## 单次执行

```powershell
Set-Location 'D:\riscv\RISCV'
python -B sim/cpu_branch_turnover/resume_loaduse.py --check-inputs
python -B sim/cpu_branch_turnover/resume_loaduse.py --tag ds_cpu_branch_loaduse_resume_20261014_a
```

第一条静态已通过。第二条仅DeepSeek一次：新tag不存在、PDS不并发；vlib/vlog各60秒，key→isa_auipc→isa_sb三个vsim **-batch** job各180秒。同真实CPU/乘法/inst_bus_interconnect、原16模块/原TB。control不派发，复用原94事件/194cycles证据，每次require_inputs重新核原control及所有历史输入哈希。

首次意外失败保留停止，不重试/清理/换tag，不再改profile/阈值/RTL/TB/模型/清单/超时/权限/RPC，不补造缺失git_after/后续日志。不执行其他诊断、历史CoreMark/MUL/PHY/全量ISA/PDS/串口/上板/Git提交推送。诊断三的PASS不跳过本次正式key与ISA。

## 验收

五个命令exit/native0、未超时、compile及三job Errors/Warnings0、正常finish、无FAIL/Fatal/RPC/timeout，console/transcript换行归一相同。原67份失败证据和三诊断产物保持；本轮输入327+5/53副本/Git前后一致。16唯一模块与原030相同，没有缓存DRM/PHY，不要求04030130。

key九组CHECK仍94/94/94/94/10/14/16/17/22，合计455架构事件，逐字段oracle一致。唯一RESULT PASS branch_turnover enable1/cases9/events455；FAST/EMPTY/RSP/LATE/READY/BUFFER/DROP_ERR/**LOAD**均正，TRAP3/IRQ1/RESET1，不放宽任何条件。参考诊断三FAST56/EMPTY5/RSP51/LATE96/READY47/BUFFER5/DROP_ERR35/LOAD3（正式门仍用原正值阈值，不把诊断计数另设新阈值）。每组cycles如实记录；flow_fast必须小于复用control194，诊断已有148，但未作为板级收益。全key事件trace非空并独立逐架构对照。

ISA auipc/sb按原seed2026101430和原ROM/RAM/五精确trap参考各跑一次：tohost1、五trap（四启动cause2，最后pass ECALL cause11/tval0→80000004）、muls0/IRQ0；PC/指令/cause/tval/target逐字段符合冻结.traps。禁止宽松cause2白名单；本次只两项抽测，不写全量ISA或全SoC PASS。

成功状态必须为**BRANCH_TURNOVER_LOADUSE_KEY_AND_TWO_ISA_PASS**。报告`DeepSeek/任务030续测_结果_ds_cpu_branch_loaduse_resume_20261014_a.md`，完整原始目录`sim/cpu_branch_turnover/build/ds_cpu_branch_loaduse_resume_20261014_a/`；列argv/exit-native/time/上限、模块、九组/覆盖/trace/同模型cycles、两ISA traps/tohost、复用control身份、所有副本/历史哈希/Git和未覆盖范围。不要自行执行Codex收据脚本。

Codex用`review_resume_loaduse.py`核证据，通过直接给新`run_branch_loaduse_resume_measurements.ps1` COM9命令；用户PDS/下载/KEY0，不例行核位流。原P300/V300、300次/CRC5275-8803不变，新bturn_300_01对照成功sfwd的P226998804/V226731331cycles（2.421321/2.418468秒）；无重建BIN/重复基线，不足10秒仅比较。当前功能门未闭合、不给上板命令；见[同阶段记录](../doc/cpu/MINI_CPU分支目标取指同拍接续_2026-10-14.md)。
