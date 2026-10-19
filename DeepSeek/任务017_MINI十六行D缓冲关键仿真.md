# 任务017：MINI十六行D读缓冲关键仿真

只执行当前I16/D16的x32桥关键TB一次。本文件不会自动调用DeepSeek。Codex已评估并单独修改现有桥；CPU未改，ISA=0，不跑旧D8对照、CoreMark仿真、PHY、Hello或历史全套。完成后交回原始证据，Codex衔接核验与后续跑分准备。

## 输入和执行范围

- 根目录`D:/riscv/RISCV`；Python `C:/python/python.exe`；ModelSim `D:/modelsim/win64pe/{vlib,vlog,vsim}.exe`。
- 当前桥`myriscv/dual_sram_to_pango_ddr_bridge.v` SHA256 **`32218ed30625d34a85db3d4f5bafd7142de56276c67651ef20eed017a5bbe084`**。仅D8→16，MINI x32容量256→512byte、读/失效索引[7:5]→[8:5]；I16、32byte行、完整tag、CPU32bit接口、命中响应及全部总线FSM保持。
- 成功I16/D8源码复用`sim/mini_board_migration/build/ds_mini_i16_20261012_133046/dual_sram_to_pango_ddr_bridge.v`，SHA `0b1b2faca33d31500320df73116a5f37b23be0de7b09b37a8b58a794ce3abc69`，只用于差分保护，不重新仿真。
- 成功基线是`sim/mini_board_migration/board/coremark_i16_01/`，原120次P/V5.017476128/5.149302165秒。本地成功位流SHA `143fa795396f4e25bf648da3d9960aeeee3d781691ff6e0a20b844a901a4b62a`，冻结PDS/实板收据在`build/inst_cache16_preparation_20261012_a/`。根目录这份位流仍是I16/D8，不含新D16。
- 新清单`sim/mini_board_migration/data_cache16_inputs.json`保护173项，SHA256 **`f85e5e40b795a52eee3007b79839897f792279150b594b658bc7e9fefc0528ec`**，包括124项登记RTL/IP/约束、本轮TB/runner、成功基线及固定软件。不要刷新旧015/016清单或改哈希绕过失败。
- 准备收据与最小差分在`sim/mini_board_migration/build/data_cache16_preparation_20261012_a/`，状态`MINI_D16_PREPARED_HDL_NOT_RUN`。AST/静态展开/只读输入检查通过，不等于HDL PASS。

## 唯一入口

在根目录先只读检查：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_data_cache16.py --check-inputs
```

应退出0并打印`INPUTS_MATCH_NOT_SIMULATED 173 checks=498 ISA=0`。不匹配立即保留并停止，不改清单。

把HHMMSS替换为实际时间，选尚不存在的tag，只执行一次：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_data_cache16.py --tag ds_mini_d16_20261012_HHMMSS
```

runner仅调用三条HDL命令：vlib创建独立work；vlog -sv编译当前桥及`tb_data_cache16_x32.sv`；vsim -c -lib该work `tb_data_cache16_x32 -do "run -all; quit -f"`。不覆盖参数、不另跑基线；每命令60秒超时。模型及请求/响应、AW/W和背压判据沿用任务016已通过版本，只调整独立容量预期和定向地址。模型为256bit x32功能用户口，不含DDR IP/PHY，不能作性能结论。

仿真结束前不要并行启动PDS或改源文件，保护输入/Git快照必须一致。PDS和KEY0/串口实板操作仍由用户执行；DeepSeek不执行。

## 验收和检查数

三条命令退出0；compile/simulation均Errors: 0，Warnings保留原值；唯一`RESULT: PASS data_cache16_x32 tests=498`，无FAIL/FATAL/Error/超时且正常$finish。以下五组按顺序PASS：

| CHECK组名 | 检查数 |
| --- | ---: |
| sixteen_D_rows_slots_256_split_512_conflict | 165 |
| upper_D15_full_tag_partial_zero_write_I_D_invalidation | 51 |
| independent_I16_locked_upper_D15_fill_data_priority | 79 |
| same_cycle_bad_ID_last_idle_preserve_upper_D_victim | 43 |
| readiness_reset_clear_I16_D16_cancel_pending_D | 160 |

共498项是完成检查数，不等于事务数；组合helper部分一次计数。覆盖：全部16条D行及各8槽，0/0x100冲突分离及0/0x200仍冲突；高D15/I15 SW/SB/SH/零strobe同时失效、同索引不同完整tag及其他行保留；I16/D16独立、锁存高D15 tag/槽（接受0x1fc后CPU地址变0x5c）、排队IF/写、数据优先；异常ID/last/串owner/idle返回不污染D受害行，同拍AR返回及AW/W；readiness/reset清全部I/D行、取消已接受且AR背压的D请求。复位取消地址0x5fc，与已暖0x3e0同索引不同tag，必须是miss。

`result.json.status=MINI_DATA_CACHE16_KEY_TEST_PASS`、checks=498、inputs_unchanged=true、git_snapshots_identical=true、isa_cases=[]。173项及清单前后匹配；检查三份command.json的版本、顶层、参数、cwd和日志，不只抄runner最终状态。

## 交回并停止

原始日志、command.json、transcript、git前后快照、work、result.json及成功时桥/TB/runner/清单四份副本留在`sim/mini_board_migration/build/<tag>/`。写`DeepSeek/任务017_结果_<tag>.md`，记录源码/清单SHA、实际三条命令和退出码、Errors/Warnings、五组/总检查数、证据路径及未覆盖范围。

首次失败保留并停止，不自动重试或修改RTL/TB/runner/判据/清单/PDS/IP/BIN/DAT，不改权限、操作串口或Git提交推送；PASS不追加历史测试。Codex复核后用户PDS实现，之后实际DDR原120次P/V各1轮，新目录coremark_d16_01对照成功I16/D8 coremark_i16_01。D16新时序、资源和收益尚未测量；不足10秒只作同BIN性能比较。
