# 任务026 结果：首次失败停止 —— 新 TB 编译报 8 处重复声明，HDL 未执行（tag ds_mini_response_turnover_20261013_a）

**结论：`STOPPED_FIRST_FAILURE`，失败发生在 **编译** 阶段，**HDL 一次都没有运行**，七组 1832 项检查执行 0 项。**
这是**工具/编译层面的失败**（vlog 退出码 2），**不是功能 FAIL，也不是桥 RTL 的行为问题**：20 个设计模块全部编译通过，唯一报错集中在新增 TB `tb_response_turnover_x32.sv`。按任务约定“首次失败保留停止”，未重试、未换 tag、未清理目录、未改任何源码/TB/判据/清单/超时/权限，也未补造缺失文件。

## 1. 入口与前置

固定 tag `ds_mini_response_turnover_20261013_a` 启动前确认**不存在**；无 `pds_shell` 实现进程（仅剩空闲 PDS GUI）、无既有 `vsim/vsimk` 会话；未改权限/RPC/IPv6/工具配置，无额外启动预检。

```powershell
python -B sim/mini_board_migration/run_response_turnover.py --check-inputs
# 退出 0：INPUTS_MATCH_RESPONSE_TURNOVER_HDL_NOT_RUN tests=1832 cpu_events=392 groups=7
python -B sim/mini_board_migration/run_response_turnover.py --tag ds_mini_response_turnover_20261013_a
# RUN_EXIT=1  →  AssertionError: ...\build\ds_mini_response_turnover_20261013_a\compile
```

## 2. 三条命令的执行情况

| 命令 | 上限 | 用时 | exit_code | native_exit_after_wait | timed_out | 结果 |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| vlib | 60 s | 0.08 s | 0 | 0 | false | 通过（`vlib.log` 0 字节） |
| **vlog** | 60 s | 0.22 s | **2** | **2** | false | **失败：`Errors: 8, Warnings: 0`** |
| vsim | 180 s | — | — | — | — | **未执行** |

vsim 的 argv 由 runner 生成但在编译失败后未启动，因此本 tag 内**不存在** `simulation.log`、`transcript`、`simulation.command.json`，也**不存在** `git_after.json`。

## 3. 原始编译错误（`compile.log` 逐字）

20 个设计模块均编译成功（`GTP_GRS, GTP_DRM36K_E1, GTP_APM_E2, ipm2l_sdpram_v1_10_icache, ipm2l_sdpram_v1_10_dcache, icache, dcache, alu, br_alu, l_alu, regfile, csr_file, mycpu_sync, mul, ipm2l_mult_v1_3_mul, ipm2l_apm_data_pipeline, ipm2l_apm_distributed_sdpram, ipm2l_apm_distributed_shiftregister, dual_sram_to_pango_ddr_bridge, tb_response_turnover_x32`），随后报错：

```text
-- Compiling module dual_sram_to_pango_ddr_bridge
-- Compiling module tb_response_turnover_x32
** Error (suppressible): D:\riscv\RISCV\sim\mini_board_migration\tb_response_turnover_x32.sv(78): (vlog-2388) 'biv' already declared in this scope (tb_response_turnover_x32).
** Error (suppressible): ...(79): (vlog-2388) 'bdv' already declared in this scope (tb_response_turnover_x32).
** Error (suppressible): ...(80): (vlog-2388) 'bdw' already declared in this scope (tb_response_turnover_x32).
** Error (suppressible): ...(81): (vlog-2388) 'bia' already declared in this scope (tb_response_turnover_x32).
** Error (suppressible): ...(82): (vlog-2388) 'bda' already declared in this scope (tb_response_turnover_x32).
** Error (suppressible): ...(83): (vlog-2388) 'bwd' already declared in this scope (tb_response_turnover_x32).
** Error (suppressible): ...(84): (vlog-2388) 'bws' already declared in this scope (tb_response_turnover_x32).
** Error (suppressible): ...(85): (vlog-2388) 'bds' already declared in this scope (tb_response_turnover_x32).
Errors: 8, Warnings: 0
```

## 4. 根因证据（供 Codex 确认，我未做任何修改）

报错的 8 个名字与 TB 中**DUT 实例端口连接**用到的 8 个名字完全一致，而该实例出现在这些名字的 `wire` 声明**之前**：

- `tb_response_turnover_x32.sv` 第 56–68 行实例化 `dual_sram_to_pango_ddr_bridge ... dut(...)`，其中第 58/60/61 行使用：
  `.inst_req_valid(biv), .inst_req_addr(bia), .data_req_valid(bdv), .data_req_write(bdw), .data_req_size(bds), .data_req_addr(bda), .data_req_wdata(bwd), .data_req_wstrb(bws)` —— **正是报错的 8 个名字**；
- 这 8 个名字的 `wire` 声明在第 **78–85** 行，**晚于**上面的使用点；
- 于是 vlog 在端口连接处先隐式建立这些网络，随后第 78–85 行的显式声明被判为“already declared in this scope”；
- 同一段 mux 逻辑在 `sim/mini_board_migration/response_turnover_cpu_mux.svh` 中是以“先声明、后 `mycpu_sync` 实例”的顺序书写的（该头文件中的 8 条 `wire b*=` 与 TB 第 78–85 行逐字相同）；TB 只 `include` 了 `response_turnover_cases.svh`（第 219 行），未包含该 mux 头。

因此该冲突是**新增 TB 内部的声明/使用顺序问题**（很可能是 TB 生成时把 DUT 实例放到了 mux 声明块之前），与主桥 `f47ca39d…` 的响应接续改动无关；具体修法与是否需要重新生成 TB 由 Codex 决定。**本轮 DeepSeek 未修改 TB 或任何源文件。**

## 5. 守恒与完整性核对

- 清单 `response_turnover_inputs.json` SHA256 `05989313a254c6c105ad9837b42f02e367e8949a0f7d616105207bdadec24cca`、主桥 SHA256 `f47ca39df5b17968e653afabd80ab62564d23cd227a71290c5673c96703ba224`、CPU SHA256 `43e451038cc14b3402ff159629d18783fbd8d1364e7c05197fadbb1e8e5d6cfe`，均与任务书一致；旧桥快照 `response_turnover_preparation_20261013_a/dual_sram_to_pango_ddr_bridge_before.v` 仍在。
- **17 份冻结副本**齐全（runner 在 HDL 前复制），其中冻结 TB 与工作副本 SHA256 相同（`fc524cf45683746560cc8b20b52bb144850c5df8ea339880036026dc297601b5`），可用于复核失败输入。
- `result.json`：`status=STOPPED_FIRST_FAILURE`、`expected_checks=1832`、`CPU_changed=false`、`PDS_started=false`、`serial_opened=false`，`error` 指向本 tag 的 `compile`。
- **`git_after.json` 缺失**（失败发生在 runner 收尾之前）——因此本报告**不声称**执行前后快照相等；未补造。执行后无残留 `vsim/vsimk/python` 进程。

## 6. 完成度与未覆盖

- 未执行：七组 CHECK（576/576/128/128/24/8/392）、唯一 `RESULT: PASS response_turnover_x32 tests=1832 ...`、`$finish`、Errors/Warnings 0、两条 `04030130`、console/transcript 一致性检查——**全部未发生**（0/1832）。
- 真实 CPU 15-word 程序的 392 事件/D AR=1/AW=W=66、内存 64/2080/1 等判据未验证。
- 未执行 Codex 的 `review_response_turnover.py`、未跑板级工具、未执行 PDS、未开串口/上板、未提交或推送 Git。
- 该 tag 目录现已存在；按任务约定**不得**清理或复用，重跑需要 Codex 修订授权与新 tag。

## 7. 交回 Codex

1. 复核本报告与原始 `compile.log`/`compile.command.json`（vlog exit 2、Errors 8）。
2. 修 TB 的声明顺序（或按其生成脚本修正），确认 20 模块编译 `Errors: 0, Warnings: 0`。
3. 因固定 tag 已存在，需给出新的授权与 tag，再由 DeepSeek 单次执行；**在收到修订授权前我不会重试、不改 TB/源码、不清理目录**。
4. 尚不进入上板步骤：1832 项功能验证未完成，七组与真实 CPU 循环均未运行。
