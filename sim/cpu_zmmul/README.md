# CPU Zmmul真实IP验证

最新Zmmul300实际DDR P/V已核通过，日志board/coremark_i64_d64_zmmul_300_01/zmmul，收据同根codex_review_20261013/result.json。完整CRC5275/8803/123响应各唯一RUN/13计数与软件、源、同位流身份保持；P/V5.452637/5.438676秒、精确55.019250/55.160480次每秒，对同位流RV32I120归一吞吐1.907970/1.981712倍、每次耗时−47.5883%/−49.5386%。不同迭代数/代码布局须披露，均不足10秒只比较。当前路径已完成，无待领取仿真或上板，不重跑历史/自动另一RTL优化；以下等待300日志/旧计划为历史，完整分析见阶段顶部。

最新024 V1续测已由Codex核原始证据PASS，build/ds_cpu_zmmul_coremark_v1_resume_20261013_a/codex_review.json已生成；一次V1、1321.167秒、完整CRC/计数/9618 MUL/9396矩阵MUL，P1复用且原native exit未知保持，旧日志不改。当前无待运行仿真，不执行--start或重跑历史；新300工具门已确认通过，下一步用户同位流COM9 P300/V300各一次，日志board/coremark_i64_d64_zmmul_300_01/zmmul，按每迭代指标比较已完成rv32i120，实际不足10秒只比较。最新收据/命令见阶段顶部；以下未运行/待领取为历史。

用户已授权024只补V1/收尾，新软件改300次。当前入口[任务024续测](../../DeepSeek/任务024续测_V1验证与300次软件交接.md)：resume_coremark_v1.py --check-inputs后--start --tag ds_cpu_zmmul_coremark_v1_resume_20261013_a，只V1一次3600秒、start立即返回/status查询，复用原编译/P1，原目录不改/不倒填未知退出。74+62项及421+11输入静态门通过，新的HDL未启动。独立P/V300构建与native CRC5275/8803通过，代码比Zmmul120仅seed4参数变化；V1和Codex只读核证通过后，用户同新位流run_zmmul300_measurements.ps1跑P/V300各一次，新目录board/coremark_i64_d64_zmmul_300_01/zmmul，按每迭代指标比本轮rv32i120，无需重复旧测试。最新状态见阶段顶部，以下新120计划/旧024入口属于历史。

最新原RV32I固定120次实板P/V已核通过：新I64/D64+Zmmul位流64445ecf…ac8ee4，P/V4.161387/4.311155秒，对照I32/D32同BIN吞吐+2.1171%/+2.0243%，AR减少约9.2%，AW/instret/分支次数保持。这还没有测硬件乘法软件收益，均不足10秒，只性能比较。原日志在board/coremark_i64_d64_zmmul_01/rv32i，独立审查收据在同根codex_review_rv32i_20261013/result.json；无需重复原测量。024 P1已有完整功能证据、V1及编排收尾仍待，以下未运行/待PDS等表述是历史；最新入口见[阶段顶部](../../doc/cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。

当前CPU乘法关键功能及两ISA样本已经Codex核原始证据PASS，原七例复用、旧新lhu320事件逐字节相同、or530事件/5trap，原FAIL为旧TB漏启动探测的判据缺口。当前只领取[024新Zmmul短CRC](../../DeepSeek/任务024_Zmmul新CoreMark短CRC关键仿真.md)：

```powershell
python sim/cpu_zmmul/run_coremark_crc.py --check-inputs
python sim/cpu_zmmul/run_coremark_crc.py --tag ds_cpu_zmmul_coremark_crc_20261013_a
```

新P/V1、120独立软件已构建，28静态MUL/矩阵5点/无DIV-REM，短与固定版只seed4不同；原120次BIN保持。421工程+11外部/34模块、真实SoC和MUL/I-D原语，P1/V1各一次，实际UART/MUL/五CRC/13计数检查，-batch/60-60-900秒首败停止。静态准备通过，新的CRC HDL未运行。任务文件不会自动调用DeepSeek，不重跑023/旧版/历史。

preparation_20261013_a/pds_handoff_zmmul.json和board_plan_zmmul.json绑定137实际PDS输入及同新位流原、新120 P/V各一轮；Codex未运行PDS或开串口，新CRC/时序/资源/实板性能未验收。实际步骤/软件SHA/比较边界见[同一阶段顶部](../../doc/cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md)。下文023续测与准备为历史。

当前唯一入口为[023严格ISA续测](../../DeepSeek/任务023续测_ISA启动CSR探测精确核验.md)：

```powershell
python sim/cpu_zmmul/resume_isa.py --check-inputs
python sim/cpu_zmmul/resume_isa.py --tag ds_cpu_zmmul_isa_resume_20261013_a
```

原七例乘法PASS（128组IP/168检查、CPU2839事件/396乘法）已核原始证据。原isa_lhu在E4启动CSR744探测处被TB只允许最终ECALL的判据停止，or未运行、无git_after；actual cause没有记录，不提前标ISA通过。原run.py/tb_cpu_zmmul.sv/inputs.json/原305副本保持，不再执行旧全套。

新tb_cpu_rv32i_sample.sv核精确四启动trap+一次通过ECALL、实际CSR提交/重定向和状态store退休，每事件原生flush；总线模型保持。因为修订观察判据，只旧冻结CPU lhu对照一次→当前lhu一次→当前or一次，旧新lhu架构轨迹逐项相同；七例不重跑。新40项+旧305/10输入守恒、两库/-batch/60-60-180秒/首败停止，新HDL尚未执行。任务文件不会自动调用DeepSeek。

下文是原023准备历史，当前以此续测入口为准。

主CPU接入`ipcore/mul/mul.v`，四条乘法共享Signed33×33/66bit/标准4级同步复位IP。四条之外M扩展仍未实现，misa.M保持0。PDS及实板由用户执行，HDL由DeepSeek任务023执行。

当前fixtures已经静态生成、oracle核对及输入封存，**没有运行HDL**。唯一入口：

```powershell
python sim/cpu_zmmul/run.py --check-inputs
python sim/cpu_zmmul/run.py --tag ds_cpu_zmmul_20261013_a
```

第一条只读核305项+10外部输入。第二条只能单次执行，无并发PDS；一次编译、真实厂家APM/GRS源，标准-batch九个固定仿真用例，第一失败停止。不要重新生成fixtures或旧版对照，不执行其他历史脚本。

计划详见[test_plan.json](test_plan.json)及[任务023](../../DeepSeek/任务023_CPU硬件乘法Zmmul关键仿真.md)：128组IP/168检查、六例CPU共2839事件/396乘法退休，ISA种子2026101323的lhu/or。CPU自定义用例采用一周期可周转指令模型；ISA采用延迟模型。数据模型单outstanding、带请求/响应背压，旧load的长延迟使年轻乘法完成但暂不能退休；Python用整数语义独立生成全部自定义架构事件。

证据输出`build/ds_cpu_zmmul_20261013_a/`；执行前封存所有工程输入及git，成功后再核inputs/git。preparation_20261013_a保存修改前CPU/PDS及生成IP核对。旧I64/D64 022保护清单绑定旧CPU/PDS，不在新CPU上复跑。

原120次rv32i BIN保持。独立rv32i_zmmul CoreMark及CRC验证待本CPU功能门通过后准备；旧软件没有MUL不会自动获得硬件乘法收益。
