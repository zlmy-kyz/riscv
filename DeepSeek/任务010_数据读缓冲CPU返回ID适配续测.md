# 任务010：数据读缓冲CPU返回ID适配续测

先读AGENTS.md和doc/CODEX_HANDOFF.md顶部。只领取本任务，任务009旧/新桥各201项和xori/bne已独立核验，不重跑。

Codex发现CPU模型原RID固定0，使新D缓冲无法分配；xori/bne又不含load，因此重跑这两个用例无助于覆盖。现只修正source/tb_soc_ddr3_rv32i_fast.v回显接受的AR ID，并用端口读请求/数据AR计数验证命中。设计RTL未改，主桥仍b7c2b3664b80b22bdf353d4c4236edfcd93cf59e0a5f6602683421b6692c8e97。详见[审查及续测](../doc/cpu/单行数据读缓冲仿真审查与CPU续测_2026-10-11.md)。

## 唯一执行范围

当前CPU/SoC/桥加适配TB，只运行既有lw用例一次；Icarus编译一次、vvp一次。软件镜像由CPU从片内RAM复制到DDR用户口模型后执行，预期加载297 words。这个用例是补缺失行为的最小定向，不是新的随机ISA清单。

不跑ModelSim桥TB/xori/bne/全ISA/CoreMark/IRQ/MMIO/Loader/九微基准/物理DDR，不重复短时工具检查。不修改RTL/TB/软件/断言/manifest，不运行PDS/串口/上板/Git提交推送。功能模型不作为性能或实板证据；当前HDL NOT_RUN。

## 命令

根目录PowerShell，选择新tag：

```powershell
Set-Location D:/riscv/RISCV
C:/python/python.exe -B sim/inst_line_buffer/resume_data_read_cpu.py --check-inputs
$task010Tag = 'ds_data_cpu_' + (Get-Date -Format yyyyMMdd_HHmmss)
C:/python/python.exe -B sim/inst_line_buffer/resume_data_read_cpu.py --tag $task010Tag
```

新data_read_cpu_resume_input_manifest.json含89项，SHA `18ab90cbc836bb7d12108f61bc4af588c0567985a5d09fcdf8030be6873bc6f4`，共用TB SHA `efa56bdd26f7276eb412f4af87ff30e855f9edeaba2c66b66898c5ef73edc81f`。不更改任务00984项旧清单；它绑定旧TB，不能套用本轮。输入变化时记录WAITING_INPUT_STABLE并停，不改哈希绕过。静态参考镜像在build/data_read_cpu_resume_preparation_20261011_a/images，生成镜像仅放本次输出，不覆盖原DAT。

## 判据和输出

compile/vvp退出码0，无FAIL/FATAL/timeout；原始日志必须同时包含：

- `CHECK: lw CPU loaded 297 words into DDR`；
- 一条`CHECK: lw D_READS=... D_AR=... D_HITS=...`，D_READS>D_AR>0，D_HITS=D_READS−D_AR>0；
- 唯一`RESULT: PASS lw DDR RV32I tohost=1 cycles=...`。

仅tohost=1但没有正数命中证据不能PASS。runner核对这些条件及输入前后相同后记录DATA_READ_BUFFER_CPU_LW_RESUME_PASS，不降低断言。如果失败，保留现场/日志，停止，交Codex定位，不自行扩展历史测试。

完整输出sim/inst_line_buffer/build/<tag>/：compile.log/lw.log及.command.json，images及selected.vvp，result.json、git_before/after.json。按[结果模板](结果模板.md)写DeepSeek/任务010_结果_<tag>.md，给出实际D_READS/AR/HITS、CPU加载数/结果、命令退出码、两版输入SHA、warnings和未覆盖范围。原任务009结果不改写，完整证据交Codex独立复核后才由用户PDS/实板。
