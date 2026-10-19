# 任务015：MINI八行D缓冲关键仿真

只执行当前D8桥的一组关键TB一次，Codex已完成RTL修改与静态准备。遵循2026-10-12精简流程：**不跑旧版对照、ISA、CoreMark仿真、PHY或历史全套**。用户自行执行后续PDS与实板；本文件不会自动调用DeepSeek。

## 输入身份与范围

- 工程：`D:/riscv/RISCV`；工具：`C:/python/python.exe -B`、`D:/modelsim/win64pe/{vlib,vlog,vsim}.exe`。
- 当前桥：`myriscv/dual_sram_to_pango_ddr_bridge.v`，SHA256 `aafa7daf9fcdbde92146ac57c6f1c53167c72b948def9b2b59cdc849e4fb4bf7`。
- 成功MINI D4桥SHA `4780997a10548c4e479a80631363999c3ad95f05b182fcbc27d4b017e65741a5`，在`sim/mini_board_migration/build/review_board_performance_20261012_a/frozen_evidence/myriscv/dual_sram_to_pango_ddr_bridge.v`，只用于身份/差分检查，**不重新仿真**。
- 当前为x32/256-bit DDR用户口、32-byte行、I8/D8；CPU/时钟/IP/总线/FSM/成功软件未改。
- 新清单：`sim/mini_board_migration/data_cache8_inputs.json`，171项保护输入，SHA256 `df0338c452650262233f9696fbb1ef65f5b4d9ca4f29767cceecae8f06528dce`。复用已有167项MINI成功身份，仅明确桥变更，并绑定新TB/runner/原审查收据及冻结D4桥。不能修改或刷新清单来绕过失败。
- 准备记录：`sim/mini_board_migration/build/data_cache8_preparation_20261012_a/`，Python AST/静态计数/只读哈希检查已通过；**HDL编译和仿真尚未执行**。

## 唯一执行入口

在工程根目录，先只读检查：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_data_cache8.py --check-inputs
```

应退出0并打印`INPUTS_MATCH_NOT_SIMULATED 171 checks=274 ISA=0`。不匹配就保留证据并停止，不能运行旧任务014或改清单。

选择尚不存在的新tag（例：`ds_mini_d8_20261012_HHMMSS`，用实际时分秒替换），只运行一次：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_data_cache8.py --tag ds_mini_d8_20261012_HHMMSS
```

runner顺序调用三条HDL命令：vlib建独立work；vlog `-sv`编译当前桥与`sim/mini_board_migration/tb_data_cache8_x32.sv`；vsim `-c -lib <work> tb_data_cache8_x32 -do "run -all; quit -f"`。不另加编译或测试。TB内功能用户口模型带AR/AW背压、延迟和同拍返回，不含Pango控制器/PHY。

## 严格验收

1. 三条命令退出码均0；编译/仿真均`Errors: 0`，保留Warnings原值，不能只抄runner PASS。
2. `simulation.log`唯一`RESULT: PASS data_cache8_x32 tests=274`，无FAIL/FATAL/Error/超时，正常结束。
3. 五组CHECK按下表顺序全PASS；静态分组计数与日志总数相符，不放宽或重写判据。

| CHECK组名 | 静态检查计数 |
| --- | ---: |
| eight_rows_slots_128_split_256_conflict | 85 |
| upper_row_full_tag_partial_zero_write_I_D_invalidation | 35 |
| independent_I8_locked_upper_D_fill_data_priority | 47 |
| same_cycle_bad_ID_last_idle_preserve_upper_victim | 27 |
| readiness_reset_clear_all_eight_rows_cancel_pending | 80 |

274是TB的完成检查计数，部分组合helper计一次，不冒称274笔CPU事务；请求/响应与AW/W守恒另有断言。包含全部8行/每行8槽、128字节冲突分离/256字节仍冲突、高行部分/零strobe写及完整tag保留、I/D独立与数据优先、接受地址变动时锁存填充、错误ID/last/空闲返回不污染缓存、readiness/reset清8行及取消待发AR。

4. `result.json.status=MINI_DATA_CACHE8_KEY_TEST_PASS`、`checks=274`、`inputs_unchanged=true`、`git_snapshots_identical=true`、`isa_cases=[]`。清单及171项前后身份一致；三份command.json的源码、顶层、工作目录与参数正确。

## 结果交付与停止条件

原始产物留在`sim/mini_board_migration/build/<tag>/`：vlib/compile/simulation的log及command.json、transcript、git_before/after.json、result.json、work和成功时冻结的桥/TB/runner/清单。新结果报告写`DeepSeek/任务015_结果_<tag>.md`，列出实际命令、退出码、Errors/Warnings、五组CHECK和唯一总数、清单/桥哈希、结果路径及未覆盖范围。

首次失败就停，保留完整日志和异常，不自动重试、不改RTL/TB/runner/PDS/IP/BIN/DAT/判据，不执行PDS、串口、上板、Git提交或推送。即便PASS也不追加ISA/旧基线/CoreMark/历史测试。结果仅为关键功能验证，**新D8时序、资源与实际DDR收益均未测量**。交回Codex核对后停止；下一步由用户PDS及固定120次双模式各1轮实际DDR对比本轮MINI D4成功基线。
