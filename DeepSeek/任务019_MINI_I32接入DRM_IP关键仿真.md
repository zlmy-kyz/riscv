# 任务019：MINI I32 接入 DRM IP，单次关键仿真

先读根`AGENTS.md`、`doc/CODEX_HANDOFF.md`顶部入口及`doc/cpu/MINI_I32接入DRM_IP与交接_2026-10-12.md`。用户已生成`icache`/`dcache`，本轮明确只接入之前的ICache；实际候选仍I32/D16。DCache未接IP、未扩D32，CPU/DDR IP/时钟/成功Loader/原120次BIN保持。

## 身份与范围

- 根目录`D:/riscv/RISCV`。当前主桥SHA **`b1ec2497bcd6974f1de0fec56c2d9f14ae517853a09b279458f49ea88f04572d`**；板级层次`board_top → soc_ddr3_top.u_soc → soc_top.g_ddr.u_ddr_bridge → g_inst_drm.u_inst_data_ram`，generate实例名以实际RTL为准。
- 新IP：`ipcore/icache/icache.idf`及其两份生成源码，DRM Simple Dual Port RAM1.10、PG2L200H/-6/FBB676、写256×64/读32×512、SYNC、无额外输出寄存器/初始化/byte write。逻辑只用低32行，1KiB，tag/valid仍FF。`RISCV.pds`仅追加该IP登记；不操作用户PDS。
- 清单`sim/mini_board_migration/inst_drm_inputs.json` SHA **`0bbdbc02e42f31a6a70204e5d65f5b208117f8cbeac91bd6b2c48691aeafc0fd`**，保护172项工程/新旧IP/原软件/成功证据，加2份本机厂家原语。实时PDS只比较去掉生成元数据后的设计配置，不能改设计选项或换IP。成功I32/D16基线位流99cdb3d0版及`coremark_i32_01`复用；旧018结果不重跑。
- Codex已执行静态准备与只读检查，HDL/PDS/新实板均NOT_RUN。只用下面入口执行一次，不运行prepare脚本，不刷新清单，不改RTL/IP/TB/判据/软件/旧报告，不运行ISA、Hello/CoreMark仿真、PHY或历史全套。

## 唯一入口

先等用户PDS结束，不能并行。runner检查`pds_shell=0`才创建新tag并启动HDL；不要停止用户进程或更改权限。可先只读：

```powershell
C:/python/python.exe -B -X utf8 sim/mini_board_migration/run_inst_drm.py --check-inputs
```

应退出0：`INPUTS_MATCH_NOT_SIMULATED 172 vendor=2 checks=1093 ISA=0`。实际执行替换HHMMSS，选不存在tag，仅执行一次：

```powershell
C:/python/python.exe -B -X utf8 sim/mini_board_migration/run_inst_drm.py --tag ds_mini_idrm_20261012_HHMMSS
```

仅vlib/vlog/vsim三条工具命令，每条60秒超时；编译**厂家GTP_GRS.v、GTP_DRM36K_E1.v、实际生成的icache两源码、当前主桥、新TB**。顶层`tb_inst_drm_x32`，run-all/quit。不使用自写RAM行为替身；TB的DDR功能用户口模型沿用已成功版本，不含PHY性能证据。

## 检查口径

原834项五组及DDR模型/transfer oracle字节保留，增加一组259项，合计1093检查（不是1093事务）：

| CHECK组 | 检查数 |
| --- | ---: |
| thirtytwo_rows_slots_512_split_1024_conflict | 325 |
| upper_I31_full_tag_partial_zero_write_I_D_invalidation | 83 |
| independent_D16_locked_upper_I31_fill_data_priority | 111 |
| same_cycle_bad_ID_last_idle_preserve_upper_I31_victim | 75 |
| readiness_reset_clear_I32_D16_cancel_pending_IF | 240 |
| synchronous_read_accepted_address_all_rows_words_hit_reset | 259 |

覆盖32行全部8word、1KiB冲突、完整tag/写失效/零strobe、I/D独立/数据优先、接受后地址变化、延期/AR同拍填充、坏RID/last不填充、reset/init有效位清除。新256次命中在接受边沿后改变实时IA，检查RAM数据在下一CPU捕获边沿前仍是已接受word、无额外AR；补一次hit被reset取消及保留RAM内容不能越过清除valid。持续检查填充写使能、低半区写行/读word地址映射。命中延迟判据仍要求下一周期，不能放宽。

**已知厂家非致命提示**：生成源码包含`c_WR_ADDR_WIDTH<9`旧检查，会在当前GUI允许的AW6配置打印`IPSpecCheck: 04030130 ... parameter setting error !!! ... between 9-20`。该分支标为PAP_WARNING，`$finish`被注释；生成日志0error/0warning、两端容量相等。保留提示，runner只接受恰好这一条ID；不改厂家代码、参数或屏蔽日志。其他IPSpecCheck、原语ERROR、ModelSim Error/Fatal、功能FAIL/超时必须停止。最终以真实原语全部数据/时序检查及正常结束确认该配置功能，不能仅凭生成成功认定功能PASS。

## 交回与停止

- 三命令退出0，编译/仿真Errors:0；warnings/原语碰撞提示如实保留解释，不声称零warning。六组CHECK顺序与次数完整，唯一`RESULT: PASS inst_drm_x32 tests=1093`，无FAIL/Error/Fatal/超时，正常$finish。
- `result.json.status=MINI_INST_DRM_KEY_TEST_PASS`，checks1093、inputs_unchanged/git_snapshots_identical=true、isa_cases=[]、ip_spec_diagnostics=[04030130]。172工程输入+2厂家模型及清单身份前后保持，git前后相同。
- 原始`vlib/compile/simulation.log`及各`command.json`、transcript、work、git前后、result保留在新tag；六份副本：桥/TB/runner/manifest/生成icache.v/生成核心rtl源码。引用清单保护的IDF/厂家模型/依赖runner身份，不重新归档历史证据。
- 新报告`DeepSeek/任务019_结果_<tag>.md`记录真实命令/退出码、Errors/Warnings、04030130原文、六组总数、正常结束时间、原始路径及未覆盖范围。

首次失败保留证据立即停止，不自动重试、不改源码/判据/输入哈希/旧报告/权限，不操作PDS/串口/上板或Git提交推送；PASS也不追加历史测试。Codex核对原始证据后，连续衔接用户新PDS时序/资源/初始化/位流核验及实际DDR原BIN各1轮，不逐步询问继续。本轮新日志目录`sim/mini_board_migration/board/coremark_idrm_01`，对照成功I32/D16 `coremark_i32_01`，不足10秒仅同BIN比较。
