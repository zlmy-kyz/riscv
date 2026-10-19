# 任务023续测：ISA启动CSR探测精确核验

## 本轮唯一授权入口

工程`D:/riscv/RISCV`。先读AGENTS、CODEX_HANDOFF顶部及同一本轮`doc/cpu/MINI_CPU硬件乘法Zmmul_IP配置与交接_2026-10-13.md`顶部。Codex已核原023停止报告与原始证据，按用户持续推进授权准备本次最小续测；不再执行原run.py标签或自行重复七例PASS。

原固定tag `ds_cpu_zmmul_20261013_a`保持。七例原始PASS已核：IP128组/168检查，CPU六例2839事件/396乘法退休，编译15模块、Errors/Warnings0，实际命令无timeout/RPC，305冻结输入及当前305+10身份保持。原`isa_lhu`断言FAIL于1335ns/PC800000e4，`isa_or`未运行、无git_after；不要补写旧git_after或改旧报告/结果。Codex新审查收据为原目录codex_review.json=CPU_ZMMUL_SEVEN_CASES_RAW_EVIDENCE_PASS_ISA_GATE_OPEN，整体ISA门仍开放。

静态核对原ROM指令：800000e4=74445073，是故意探测未实现CSR744的CSRWI，前序已设置mtvec800000e8；现有CSR白名单必应产生cause2/tval74445073再跳E8。原TB仅允许结束ECALL，遗漏了原ISA启动探测流程。**旧日志未记录实际cause/指令，这些值仍须本次严格实测确认，不能把静态期望当已观察值。** 本轮不修改CPU/CSR/IP/PDS/ROM/RAM/BIN/原TB/原清单；只新增ISA专用TB、精确参考和续测runner。

固定新tag **`ds_cpu_zmmul_isa_resume_20261013_a`**，输出`sim/cpu_zmmul/build/ds_cpu_zmmul_isa_resume_20261013_a/`。存在即停止，不换tag、不覆盖，不清理/重试。无用户PDS实现并发、原默认权限；禁止IPv6/RPC/权限/工具预检及调整超时。

```powershell
Set-Location 'D:\riscv\RISCV'
python sim/cpu_zmmul/resume_isa.py --check-inputs
python sim/cpu_zmmul/resume_isa.py --tag ds_cpu_zmmul_isa_resume_20261013_a
```

第一条只读输入/旧PASS审查；任一前置或HDL命令/判据失败立即保留停止，不能继续下一例。任务文件不会自动调用DeepSeek。禁止run.py原全套和prepare_tests.py，不生成/修改原镜像。

## 固定范围和身份

新清单`sim/cpu_zmmul/isa_resume_inputs.json` SHA **dbd4f0fee409fd27166b79d55979aa908b16220b792c1fa6d39c11a7bff10c1d**：在原305工程+10外部依赖保护基础上增加40项续测源码/精确参考/原日志证据保护。原清单f8ebb23b…6fa86保持。

CPU仍`43e451038cc14b3402ff159629d18783fbd8d1364e7c05197fadbb1e8e5d6cfe`，PDS仍c5f87d11…a6916、mul IDF仍1f583b2e…ae9a33、桥仍d8ae0409…5cf09。旧CPU是修改前真实冻结文件`sim/cpu_zmmul/build/preparation_20261013_a/mycpu_sync.v`，SHA `746db2f648276e706f766cced8848038e0b93a194ef0a077d0613d96cca9f7e7`；其余五CPU模块/CSR定义与当前相同。旧文件只作独立仿真输入，不替换主RTL、不改PDS。

新版ISA专用`tb_cpu_rv32i_sample.sv`只用于这三例。指令/数据接口模型与旧023 ISA模式逐字保持，唯一添加的是接受状态store时只读记录ID/EX PC，以确认该store真实退休后才结束。独立trace/精确trap判据不改变CPU输入/响应时序。原tb_cpu_zmmul.sv完全保持，七个乘法用例不重跑。

因为新ISA观察判据不能直接沿用旧tohost-only成功结论，按照AGENTS“TB/判据发生变化才补相关旧版对照”，只补**一次旧CPU lhu**。执行顺序固定：

1. `baseline_lhu`：旧CPU、原lhu ROM/RAM、新精确ISA TB，一次。
2. `isa_lhu`：当前CPU、同ROM/RAM/同TB，一次；架构事件轨迹必须与旧CPU逐项相同。
3. `isa_or`：当前CPU、原or ROM、同TB，一次。

两个独立库，vlib/vlog各60秒，vsim各180秒；顺序是旧库vlib/vlog/baseline_lhu，再当前库vlib/vlog/isa_lhu/isa_or。各编CPU六模块/真实mul五源/厂家GTP_GRS和GTP_APM_E2/ISA单TB，共14模块，baseline的乘法模块未例化，当前CPU实际例化mul。每例`vsim -batch -lib <work> tb_cpu_rv32i_sample <固定plusargs> -logfile <transcript> -do "run -all; quit -f"`，原生输出直写，20ms TB watchdog；不用-c/GUI/do内加载。

## 精确判据，不能宽泛放过cause2

三例均要求以下顺序；每条trap必须无GPR写、无IRQ，CSR在下一半周期确认mepc/mcause/mtval，并且trap后第一条实际退休指令PC必须等于目标。

| 序号 | PC | 指令 | cause | tval | 目标 |
| --- | --- | --- | ---: | --- | --- |
| 0 | 800000e4 | 74445073：CSRWI 744,8 | 2 | 74445073 | 800000e8 |
| 1 | 800000f4 | 18005073：CSRWI satp,0 | 2 | 18005073 | 800000f8 |
| 2 | 8000010c | 3b029073：CSRW pmpaddr0,t0 | 2 | 3b029073 | 80000118 |
| 3 | 80000128 | 30205073：CSRWI medeleg,0 | 2 | 30205073 | 80000130 |
| 4 | lhu 80000478 / or 80000684 | 00000073：通过路径ECALL | 11 | 00000000 | 80000004 |

probe2的目标跳过pmpcfg0，probe3跳过mideleg，所以不是六个启动trap。不得把任何其他PC/cause2或提前失败ECALL列为可接受。各例必须四个启动探测+一个通过ECALL，共5trap；tohost只接受完整SW写1，须收到响应且状态store正常退休；正常退休中不得出现M扩展编码。所有退休/trap/MRET逐条写`<name>.events.log`并及时flush，失败console含PC/inst/cause/tval/rf_we/IRQ/target/时间；禁止把DUT字段写回trap参考表。

每例应有五条ISA_TRAP及唯一对应CHECK/RESULT：

```text
CHECK: <name> PASS tohost=00000001 traps=5 probes=4 muls=0 events=<实测>
RESULT: PASS rv32i_sample case=<name> tohost=1 traps=5 probes=4 muls=0
```

三个仿真均正常$finish、Errors/Warnings0，无RESULT FAIL/Fatal/RPC/timeout；stdout/transcript非空且换行归一后全文相同。vlib/vlog/仿真共七个command.json均退出0。旧/新lhu架构轨迹比较覆盖事件种类、PC、指令、写许可、写寄存器和值、trap cause/tval/target；仅忽略时钟时间戳及不生效的旁带字段，不能只比较末尾tohost。比较收据必须IDENTICAL_ARCHITECTURAL_EVENTS。

成功时result.json=PASS、new_completed三项按序，旧七例原始证据再次只读核验、当前/旧冻结输入一致，新git_before/after相等。新输出只冻结五个新增源/参考和新清单，不重复复制旧305份源或旧日志；source_identity.json引用原冻结输入。原缺失git_after仍缺失，不能因本次新快照而补推旧收尾已经完成。

## 交付与禁止范围

交报告卡片和原始路径/摘要，列实际五trap行、旧/新lhu完整事件数/比较、or结果、编译模块/退出/时长、清单和CPU/IP身份及新输入/git守恒。失败同样首败保留停止、指出已完成/未执行，别改判据/文件/超时/权限或继续测试。只有这三例，无七乘法/全ISA/Hello/CoreMark/桥/DDR PHY/工具实验，不能追加其它随机ISA。

不得修改任何主RTL/CSR/PDS/IP、旧TB/fixtures/判据/旧清单/成功镜像/原报告；不得开PDS/串口/实板或提交推送Git。CPU/PDS/板级收益及独立Zmmul软件CRC仍待后续门。本轮三例PASS且Codex原始核验后，才合并旧七例为“乘法关键功能+两例ISA抽测”完成；不能声明全ISA/SoC/PHY/时序/实板PASS。
