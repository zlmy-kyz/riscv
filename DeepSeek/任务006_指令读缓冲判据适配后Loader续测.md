# 任务006：指令读缓冲判据适配后的Loader续测

状态：READY / HDL_NOT_RUN，2026-10-11。用户授权Codex适配两处测试判据；Codex已完成实现及离线检查，未启动HDL编译/仿真。请先读AGENTS.md、doc/CODEX_HANDOFF.md及[适配记录](../doc/cpu/指令读缓冲测试判据适配与交接_2026-10-11.md)。本任务文件不自动调用DeepSeek。

## 已完成与执行范围

- 新物理比较器已离线核对原任务005物理日志：九窗口固定退休工作量一致，8处差异只位于计时标记紧邻边界。原CYCLE接受边沿、metrics、instret、CPI均保留，原FAIL不覆盖。
- Codex已通过16项离线检查，包括10类坏轨迹拒绝和enable0/1生成TB的原检查逐字恢复验证；未编译这些TB，不能把它写成Loader仿真PASS。
- 只运行下列5次真实CPU Loader功能模型仿真：hello关闭缓冲对照；hello、crc32、performance_1、validation_1启用缓冲。四项启用测试关闭任务005的Loader缺口。关闭对照检查新账本在无命中时仍成立。
- 不重复unit、fast、短CoreMark功能A/B、物理DDR九窗口、两条DDR Tcl、IRQ或MMIO；源码未变且既有PASS已经独立复核。
- Loader使用真实CPU→共享桥→带背压的DDR用户口模型，不是纯BRAM；不含Pango IP/PHY，不用其周期报实板或物理DDR收益。物理性能证据沿用已冻结的任务005完整IP/PHY日志。

## 身份及权限

1. 原input_manifest.json：1423项，SHA256 `1173f29a185651c99bdbc3053946c2b109aea789b9e14851543994d2dc6027ea`。
2. 原resume_input_manifest.json：71项，SHA256 `40f5bb2227483cc8fc5d8ea3e5156455c38f90ea7d0a9b316a95d270c1134002`。
3. 新checks_input_manifest.json：270项，SHA256 `a7828210c3e461c38359ae1c2d49adba748aeeae14a98d552971e96fc391e812`。三份都在sim/inst_line_buffer/，前后必须匹配。
4. 设计桥仍`3509576cb761a6d984c526d51fd48966cb405011472bfc6c03b0b0299c3dfe6d`；CPU/SoC/MMIO、成功Loader ROM/RAM、四个固定应用BIN、PDS/IP/位流、旧部署门控没有改变。
5. 新入口resume_checks.py只在新输出目录生成原TB的适配副本，设计源直接用myriscv/*.v。仅替换旧的Pango总数守恒断言并插入独立账本，其余原测试逐字保留；enable参数只在仿真副本通过defparam设置，不改RTL。
6. 仅授权执行所列命令、收集日志和写结果报告。不得修改RTL/TB/模型/判据/runner/清单/PDS/IP/成功软件/门控；不串口、上板、PDS实现、Git提交推送或清理工作树。任何新失败立即停止，保存现场，不跑剩余应用、不自行放宽或修判据。

已完成离线证据在sim/inst_line_buffer/build/：

- checks_static_20261011_a/result.json：INST_LINE_BUFFER_ADAPTER_OFFLINE_CHECK_PASS，16项，HDL_compile_result=NOT_RUN。
- checks_compare_20261011_a/adapted_check_receipt.json：INST_LINE_BUFFER_ADAPTED_CHECK_PASS，suite=compare，simulation_started=false；内部comparison=INST_LINE_BUFFER_PHYSICAL_COMPARE_PASS。

这两个结果不必再跑；只核对状态/清单一致。不得把“比较器通过”写成旧比较器FAIL已删除或整体验收PASS。

## 命令

PowerShell从根目录运行。各命令fresh tag，不覆盖旧结果；非零立即停止。

```powershell
Set-Location D:/riscv/RISCV
$lineCheckTag = 'ds_line_checks_' + (Get-Date -Format 'yyyyMMdd_HHmmss')
& C:/python/python.exe -B -c "import sys; sys.path.insert(0,'sim/inst_line_buffer'); import resume_checks; print(resume_checks.require_inputs())"
if ($LASTEXITCODE -ne 0) { throw 'INPUT_CHANGED: stop and return evidence' }

$lineCases = @(
    @{app='hello'; enable=0; suffix='hello_off'},
    @{app='hello'; enable=1; suffix='hello_on'},
    @{app='crc32'; enable=1; suffix='crc32_on'},
    @{app='performance_1'; enable=1; suffix='perf1_on'},
    @{app='validation_1'; enable=1; suffix='val1_on'}
)
foreach ($lineCase in $lineCases) {
    & C:/python/python.exe -B sim/inst_line_buffer/resume_checks.py --suite loader --application $lineCase.app --buffer-enable $lineCase.enable --tag "${lineCheckTag}_$($lineCase.suffix)"
    $lineCaseExit = $LASTEXITCODE
    if ($lineCaseExit -ne 0) {
        throw "Loader FAIL: $($lineCase.app), enable=$($lineCase.enable), exit=$lineCaseExit. Stop all remaining cases."
    }
}
```

## 必须检查

所有产物在sim/inst_line_buffer/build/<tag>/：generated/tb_applications_checked.sv、application/{compile.log,modelsim.log,results.json,uart_tx.bin,uart_rx.bin,application_uart.txt,ddr_trace.csv,run.tcl}、adapted_check_receipt.json。

- compile.log Errors:0；modelsim.log有唯一RESULT:PASS applications_stage3、Errors:0，无RESULT:FAIL/**Error/**Fatal。
- application/results.json为SAME_LOADER_APPLICATION_SIM_PASS，inputs_unchanged/protected_unchanged=true；实际编译的generated TB必须列在input_sha256并匹配。
- adapted_check_receipt.json为INST_LINE_BUFFER_ADAPTED_CHECK_PASS，inputs_unchanged=true，三个清单身份正确；buffer_enable实际值与本轮命令相同。
- 原下载字节、每个CPU数据请求/响应/退休、每条IF响应对BIN、CRC、UART协议和应用输出、字节lane/strobe、异常/IRQ、最后guards和timer汇总全部保留并实际到达。CoreMark需完整PERF2B_DONE及13项计数，timer_ticks等于PORT_DONE，timer_bench_reads=2；短运行仍不是正式CoreMark分数。
- CHECK:LINE_LEDGER enable=...必须恰好一行。启用缓冲hit>0且miss>0；关闭对照hit=0。IF=hit+miss；AR_IF与miss差只能是明确正在等待发命令的那一笔IF，不能用差额反推hit；AR_DATA对应数据读，AW/W对应写，R对应AR。data==data_rsp，pending只能0/1且若1必须是明确IF在途。
- 命中分类仅来自监视器独立valid/tag/128-bit模型；写接受使其失效。没有读取DUT inst_line_hit/tag/valid寄存器去自证，不删除事务守恒上限。
- 脚本失败时新receipt应保留FAIL/error和底层results/log；remaining cases写NOT_RUN。编译失败也立即返回Codex，不帮忙改SV或通过文本。

## 返回

在DeepSeek/写任务006_结果_<lineCheckTag>.md，记录执行起止、git状态、工具版本、三份清单前后哈希/条目数、每条命令与退出码、5行应用结果表及原始日志路径。逐行列出LINE_LEDGER计数、CRC/PERF2B/计时、trap/guards完成证据、warnings、新失败和未执行项。

不要把软件执行正确、物理DDR训练、PDS实现或实板收益合并成一个结论。返回后由Codex独立复核，本任务不安排用户生成位流或上板。
