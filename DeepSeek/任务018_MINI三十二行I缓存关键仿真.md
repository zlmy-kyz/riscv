# 任务018：MINI三十二行I缓存关键仿真

只执行当前I32/D16的x32桥关键TB一次。本文件不会自动调用DeepSeek。Codex按用户“执行下一轮”授权单独I16→32；CPU未改，ISA=0，不跑旧I16对照、Hello/CoreMark仿真、PHY或历史全套，PDS和实板由用户执行。

## 输入与边界

- 根目录`D:/riscv/RISCV`；Python `C:/python/python.exe`；ModelSim `D:/modelsim/win64pe/{vlib,vlog,vsim}.exe`。
- 当前主桥`myriscv/dual_sram_to_pango_ddr_bridge.v` SHA256 **`78c624e8eb8a7ea1ad0fd8186873c5ba17f4e98d7623bce83006e5336bdccb34`**。I16→32，MINI x32下512→1024byte、取指及I写失效索引[8:5]→[9:5]、锁存fill tag[4:0]；D16/32byte行/完整tag/命中响应/总线FSM保持。头部旧D8注释同时更正为实际D16，不是另一项行为改动。
- 成功I16/D16源码复用`sim/mini_board_migration/build/ds_mini_d16_20261012_143018/dual_sram_to_pango_ddr_bridge.v`，SHA `32218ed30625d34a85db3d4f5bafd7142de56276c67651ef20eed017a5bbe084`，仅用于差分守卫，不重新仿真。
- 成功PDS/实板收据及冻结位流复用`sim/mini_board_migration/build/data_cache16_preparation_20261012_a/`；位流SHA **`f2540aec916476bf15eb02c0fefb174b0af06c9a801cde92d704083ceaca6ccd`**仍属成功I16/D16，不含新I32。对照为`sim/mini_board_migration/board/coremark_d16_01`，P/V4.701925600/4.836962304秒，原120次BIN保持。
- 新清单`sim/mini_board_migration/inst_cache32_inputs.json`保护179项，SHA256 **`59ddf2d42893f2682142617ac189b63d8761ec3f42184b328b0d26efbb3d2a33`**。保护124项登记源/IP/约束、CSR头文件、成功证据、固定软件/Loader/工具、本轮TB/runner及原TB/清单。不要刷新017/016清单或改变哈希绕过失败。
- 准备收据和最小patch在`sim/mini_board_migration/build/inst_cache32_preparation_20261012_a/`，状态`MINI_I32_PREPARED_HDL_NOT_RUN`。Python AST、独立手算/静态展开、D/FSM及最小变换守卫、只读输入检查已通过；HDL尚未执行。

## 唯一入口

在根目录先只读检查：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_inst_cache32.py --check-inputs
```

应退出0，打印`INPUTS_MATCH_NOT_SIMULATED 179 checks=834 ISA=0`。不匹配保留停止，不改清单。

替换HHMMSS为实际时间，选择尚不存在的tag，仅执行一次：

```powershell
C:/python/python.exe -B sim/mini_board_migration/run_inst_cache32.py --tag ds_mini_i32_20261012_HHMMSS
```

runner只依序调用三条HDL命令：vlib创建独立work；vlog -sv编译当前桥及`tb_inst_cache32_x32.sv`；vsim -c -lib该work `tb_inst_cache32_x32 -do "run -all; quit -f"`。每条60秒超时，不覆盖参数、不改执行权限、不另跑基线。

复用成功功能模型的256bit x32读写握手、背压、延迟、同拍返回、byte strobe、请求/响应与AW/W守恒及命中下一拍判据。只扩独立I/D容量预期、定向地址、模型后备存储64→128行以覆盖0x800–0xbff；既有逐行数据公式、传输时序/判据逐字保持，不含DDR IP/PHY，不测性能。仿真结束前不要并行启动PDS或改变输入/工作树。

## 验收

三条命令退出0；compile/simulation均Errors: 0，Warnings原值如实保留；唯一`RESULT: PASS inst_cache32_x32 tests=834`，无FAIL/FATAL/Error/超时，正常$finish。以下五组CHECK按顺序PASS：

| CHECK组名 | 检查数 |
| --- | ---: |
| thirtytwo_rows_slots_512_split_1024_conflict | 325 |
| upper_I31_full_tag_partial_zero_write_I_D_invalidation | 83 |
| independent_D16_locked_upper_I31_fill_data_priority | 111 |
| same_cycle_bad_ID_last_idle_preserve_upper_I31_victim | 75 |
| readiness_reset_clear_I32_D16_cancel_pending_IF | 240 |

合计834为完成检查数，不是事务数。覆盖全部32行×8槽/高I31，0/0x200可共存、0/0x400仍冲突；高I31及对应D15的SW/SB/SH/零strobe同时失效，完整tag不同的同索引写保留受害行；D16与I32独立，IF接受0x3ec后IA变0x14且排队0x3e4/0x7e4写，D接受0x1fc后DA变0x5c且排队IF；数据优先，RID/last异常、串owner及idle返回不污染高行；同拍AR返回/AW-W、readiness/reset清全部I32/D16及取消已接受且AR背压的IF。取消地址0x7fc与已暖I31 0xbe0不同完整tag，必须是miss。

`result.json.status=MINI_INST_CACHE32_KEY_TEST_PASS`、checks=834、inputs_unchanged=true、git_snapshots_identical=true、isa_cases=[]；179项和清单前后保持。独立核对command.json实际版本/路径/参数/cwd/顶层与日志，不只抄runner状态。

## 交回并停止

原始日志、command.json、transcript、git前后快照、work、result.json及成功时桥/TB/runner/清单四副本保留在`sim/mini_board_migration/build/<tag>/`。写`DeepSeek/任务018_结果_<tag>.md`，记录输入SHA、三条实际命令/退出码、Errors/Warnings、五组/总检查数、原始路径和未覆盖范围。

首次失败保留停止，不自动重试/修改RTL/TB/runner/判据/清单/PDS/IP/BIN/DAT，不运行PDS/串口/上板或Git提交推送。PASS不追加旧版/ISA/历史套件。Codex收到结果后连续核原始证据、更新同一阶段、衔接用户PDS核验及新跑分准备。

新I32时序/资源/实板收益均未测。仿真审查后用户PDS，最终时序及位流身份核验通过再下载并实际DDR原120次P/V各1轮，日志新目录`coremark_i32_01`对照成功`coremark_d16_01`；不足10秒仅性能比较。
