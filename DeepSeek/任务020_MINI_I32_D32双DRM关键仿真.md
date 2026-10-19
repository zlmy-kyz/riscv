# 任务020：I32/D32 双DRM，单次关键仿真

先读根`AGENTS.md`、`doc/CODEX_HANDOFF.md`顶部及`doc/cpu/MINI_I32_D32双DRM接入与交接_2026-10-12.md`。019原始证据已核验PASS，不重跑；用户板子暂借出，允许先接DCache并明确“dcache改为和icache的容量一样”。本轮候选**I32/D32，x32各1KiB**，真实生成`icache`和`dcache`两个DRM IP；I路径保持已验证版本，只改D容量/数据实现/响应选择。

## 身份与输入

- 主桥`myriscv/dual_sram_to_pango_ddr_bridge.v` SHA **`918efab77d6e00d609529599d13be6b6b004c34199692c2ca8556c2e04525851`**。
- 清单`sim/mini_board_migration/data_drm32_inputs.json` SHA **`c5cbd73db8c9a6b5af5cc567520450e9863ba0378b50a8e607514aa4806d1c4f`**，181项工程/软件/新旧IP/成功证据，加2厂家原语。实时RISCV.pds按设计配置保护，只新增DCache IDF和两生成源，两个IP均登记一次。不得刷新哈希绕过输入变化。
- 两IP配置保持已生成版本：256bit写/address6、32bit同步读/address9、SYNC、OUTPUT_REG/FAB_REG/init/byte write关闭；写`{0,index[4:0]}`、读`{0,addr[9:2]}`，只用低32行。tag/valid仍FF，所有store直达DDR并失效完整tag命中行，无writeback/dirty。
- 原功能基线019 `build/ds_mini_idrm_20261012_181906`，b1ec2497 I32DRM/D16FF；Codex收据`codex_review.json=MINI_INST_DRM_RAW_EVIDENCE_REVIEW_PASS`。旧成功实板仍FF I32/D16 `coremark_i32_01`/99cdb3d0版；I-only DRM没有PDS/实板成功证据。
- Codex静态审查通过，HDL未执行。不要运行prepare/review旧脚本，不改RTL/IP/PDS/TB/runner/判据/软件/历史报告，不自动追加测试。

## 唯一执行

等用户PDS结束，不并行，不停止其进程/改权限。只读可先执行：

```powershell
C:/python/python.exe -B -X utf8 sim/mini_board_migration/run_data_drm32.py --check-inputs
```

预期退出0：`INPUTS_MATCH_NOT_SIMULATED 181 vendor=2 checks=1521 ISA=0`。新tag替换HHMMSS，选择不存在目录，HDL只执行一次：

```powershell
C:/python/python.exe -B -X utf8 sim/mini_board_migration/run_data_drm32.py --tag ds_mini_ddrm32_20261012_HHMMSS
```

vlib/vlog -sv/vsim -c三命令，每条60秒；编译厂家`GTP_GRS.v/GTP_DRM36K_E1.v`、实际I/D两个IP的四个生成源、当前主桥与`tb_data_drm32_x32.sv`；顶层`tb_data_drm32_x32`，run-all/quit。不能换RAM行为替身。ISA0，无CPU/Hello/CoreMark、PHY或历史全套，无旧版重测。

## 八组判据，共1521检查

| CHECK组 | 检查数 |
| --- | ---: |
| thirtytwo_rows_slots_512_split_1024_conflict | 325 |
| upper_I31_full_tag_partial_zero_write_I_D_invalidation | 83 |
| independent_D32_locked_upper_I31_fill_data_priority | 143 |
| same_cycle_bad_ID_last_idle_preserve_upper_I31_victim | 75 |
| readiness_reset_clear_I32_D32_cancel_pending_IF | 320 |
| synchronous_read_accepted_address_all_rows_words_hit_reset | 259 |
| D32_all_words_synchronous_accepted_address_1024_conflict_hit_reset | 294 |
| D31_bad_ID_last_same_cycle_fill_cancel_and_I_D_source_switch | 22 |

前六组由已成功019按D32循环扩展、queued D目标改上半D31；DDR功能模型及transfer/命中下一周期判据保持，复用019对照，不重复旧版。D32增加128项原循环检查，原1093→1205；最后两组新增316→1521。259项I同步地址保持检查沿用。1521是检查计数，非事务数。

新增D覆盖32行×8word的256次同步hit，接受后改DA和IA，响应直到下一CPU捕获边沿仍正确，无额外AR/重复响应；32行填充、512byte不冲突/1024byte冲突、D31 hit复位取消及残留RAM不得绕过valid；D31坏RID/last/cross-ID保留原victim、AR同拍fill、AW/W同拍store与重新填充、blocked D miss reset取消，I/D/miss/hit/store间切换响应源。持续核两IP完整fill资格和高地址位恒0。原SB/SH/SW/零strobe、写失效、数据优先、I/D独立/锁定已接受地址、背压与守恒保持。不能放宽hit周期或数据判据。

两生成核心各有已知非致命`IPSpecCheck: 04030130 ... AW between 9-20`提示，GUI允许AW6、容量一致、其$finish被厂家注释。**预期恰好两条04030130**，保留原文；不改厂家源、不屏蔽日志。其他IPSpecCheck、原语ERROR/ModelSim Error/Fatal、功能FAIL或超时停止。Warnings如实记录。

## 交回

- 三命令退出0、compile/simulation Errors0、八组顺序完整、唯一`RESULT: PASS data_drm32_x32 tests=1521`、正常$finish，无FAIL/错误/超时。
- result状态`MINI_DATA_DRM32_KEY_TEST_PASS`，checks1521、inputs_unchanged/git_snapshots_identical=true、ISA[]、ip_spec_diagnostics两个04030130、PDS/serial=false、formal_board=NOT_TESTED。
- 保存原始log/command.json/transcript/work/git/result和**八份副本**：桥、TB、runner、manifest、I/D各两生成源。原厂家模型/IDF/旧结果按清单身份引用，不重新归档历史。
- 新报告`DeepSeek/任务020_结果_<tag>.md`如实记录身份、三命令/退出码、ModelSim Errors/Warnings、两条IP提示、八组/总数、正常结束时间、原始路径及未覆盖范围。

首次失败保留停止，不自动重试/改源码/判据/输入/历史报告/权限，禁止PDS/串口/上板/Git提交推送。PASS也不追加历史。板子暂不可用，新性能与实板验收保留待执行；Codex收到结果后连续核原始证据与准备用户PDS核对要点。用户后续只需实现最终双DRM配置并在板子可用时跑原120次P/V各1轮，日志`coremark_idrm_d32_01`，对照成功FF版I32/D16 `coremark_i32_01`，不足10秒仅同BIN比较。不要要求补I-only中间配置PDS/上板。
