# 任务016：MINI十六行I缓存关键仿真

只执行当前I16/D8的一组x32桥关键TB一次。Codex已评估并单独修改现有桥；本文件不自动调用DeepSeek。CPU未改，ISA=0；不跑旧I8对照、CoreMark仿真、PHY、Hello或历史全套，用户执行后续PDS及实际DDR验收。

## 输入与边界

- 工程`D:/riscv/RISCV`，Python `C:/python/python.exe`，ModelSim `D:/modelsim/win64pe/{vlib,vlog,vsim}.exe`。
- 当前`myriscv/dual_sram_to_pango_ddr_bridge.v` SHA256 **`0b1b2faca33d31500320df73116a5f37b23be0de7b09b37a8b58a794ce3abc69`**：I8→16，x32下I容量256→512byte、索引[7:5]→[8:5]，D8/32byte行/完整tag/CPU接口/总线FSM保持。
- 成功I8/D8桥复用`sim/mini_board_migration/build/ds_mini_d8_20261012_115734/dual_sram_to_pango_ddr_bridge.v`，SHA aafa7daf9fcdbde92146ac57c6f1c53167c72b948def9b2b59cdc849e4fb4bf7，仅用于差分保护，不重新仿真。
- 成功I8/D8位流1fc7eff0…10b666b及PDS/实板收据复用`sim/mini_board_migration/build/data_cache8_preparation_20261012_a/`；实板基线是`sim/mini_board_migration/board/coremark_d8_01/`，不是旧coremark_01。
- 新清单`sim/mini_board_migration/inst_cache16_inputs.json`，171项，SHA256 **`676cf0ad2eab0892b88859dc49d754f48fe89a685a17a24085ed82b4a50576a9`**。这是新任务清单，不修改或刷新旧015清单。保护设计/IP/约束、成功位流/报告/收据、原BIN/ELF/manifest/反汇编/参考、Loader及本轮TB/runner等。
- 准备记录`sim/mini_board_migration/build/inst_cache16_preparation_20261012_a/`，状态`MINI_I16_PREPARED_HDL_NOT_RUN`。只有Python AST、静态展开/地址清点及只读输入检查通过，不是仿真PASS。

## 唯一入口

在工程根目录先执行只读检查：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_inst_cache16.py --check-inputs
```

应打印`INPUTS_MATCH_NOT_SIMULATED 171 checks=442 ISA=0`并退出0。不匹配就保留停止，不能改清单绕过。

替换HHMMSS为实际时间，选择不存在的tag，仅执行一次：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_inst_cache16.py --tag ds_mini_i16_20261012_HHMMSS
```

runner只调用三条命令：vlib创建独立work；vlog -sv编译现有桥及`sim/mini_board_migration/tb_inst_cache16_x32.sv`；vsim -c -lib该work `tb_inst_cache16_x32 -do "run -all; quit -f"`。无参数覆盖，当前生产源码决定实际I16/D8容量。模型为带AR/AW背压、延迟、同拍返回及写掩码的x32功能用户口，不含Pango控制器/PHY，不能测性能。

## 验收

三条命令退出0，compile/simulation均Errors: 0，保留Warnings原值；唯一`RESULT: PASS inst_cache16_x32 tests=442`、无FAIL/FATAL/Error/超时且正常$finish。下列CHECK按顺序全部PASS，静态计数165/51/63/43/120合计442：

| CHECK组名 | 检查数 |
| --- | ---: |
| sixteen_rows_slots_256_split_512_conflict | 165 |
| upper_I15_full_tag_partial_zero_write_I_D_invalidation | 51 |
| independent_D8_locked_upper_I_fill_data_priority | 63 |
| same_cycle_bad_ID_last_idle_preserve_upper_I_victim | 43 |
| readiness_reset_clear_I16_D8_cancel_pending_IF | 120 |

覆盖全部16行/每行8槽、256byte冲突分离/512byte仍冲突、I高索引15与D索引7的SW/SB/SH/零strobe失效、同索引不同完整tag及其他行保留、D8不被I填充污染、锁存高索引IF tag/槽与排队写、数据优先、错误ID/last/空闲返回不污染受害行、readiness/reset清所有I/D行及取消已接受待发AR。请求/响应及AW/W守恒、背压稳定、命中接受下一拍响应另有断言；442是完成检查计数，部分组合helper计一次，不等于442笔CPU事务。

`result.json.status=MINI_INST_CACHE16_KEY_TEST_PASS`、checks=442、inputs_unchanged=true、git_snapshots_identical=true、isa_cases=[]；清单及171项前后匹配。核对三份command.json的源码/顶层/cwd/参数与日志，不只抄runner结果。

## 交回与停止

原始日志、command.json、transcript、git前后快照、work、result.json及成功时四份桥/TB/runner/清单副本保留在`sim/mini_board_migration/build/<tag>/`。写`DeepSeek/任务016_结果_<tag>.md`，记录版本/清单哈希、实际命令及退出码、Errors/Warnings、五组CHECK/总数、原始路径和未覆盖范围。

首次失败保留停止，不自动重试、不修改RTL/TB/runner/判据/清单/PDS/IP/BIN/DAT；不运行PDS、串口/上板、Git提交推送。PASS也不追加旧版/ISA/历史测试。Codex核验原始证据后用户PDS，实际DDR原120次P/V各1轮对照成功I8/D8；新I16时序、资源、真实收益均未测量，不足10秒只作性能比较。
