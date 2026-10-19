# 任务031 结果：`ds_write_buffer_turnover_20261014_a` 正式收尾执行

**状态：`STOPPED_FIRST_FAILURE`（首次失败即停止，未重试、未换 tag、未改任何文件）。**

- 第 1 条静态入口：**PASS**（exit 0）。
- 第 2 条正式运行：在 **vlib 之后的 vlog 编译** 处失败——rom/ram IP 包装文件找不到被 `include` 的 `*_init_param.v`，`vlog` 报 **258 个 Error / 0 Warning、native exit 2**。
- **vsim 从未启动**：`control` / `key` 两个 job 未执行，`git_after.json` 未生成，EV/BUS/AW/W 新轨迹均不存在。
- 失败原因位于**封存输入副本不完整**（缺少两个被 `include` 的文件），不是 RTL/TB/判据问题。

原始目录：`sim/write_buffer_turnover/build/ds_write_buffer_turnover_20261014_a/`
`result.json`：`status=STOPPED_FIRST_FAILURE`、`HDL_started=true`、`completed={}`、`board=NOT_RUN`、`serial_opened=false`、`PDS_started=false`。

## 1. 两条命令的原始记录

| # | 命令 | 结果 | 证据 |
| --- | --- | --- | --- |
| 1 | `python -B sim/write_buffer_turnover/simulation_completion_runner.py --check-inputs` | exit 0，输出 `RESULT: PASS completion inputs; observation-only equivalence; reference EV430; HDL NOT_RUN; ISA=0` | 无独立日志（stdout） |
| 2 | `python -B sim/write_buffer_turnover/simulation_completion_runner.py --tag ds_write_buffer_turnover_20261014_a` | exit 1（`AssertionError: ...\compile`），native **2** | `vlib.command.json`、`compile.command.json`、`compile.log`、`vlib.log`、`git_before.json`、`result.json` |

真实命令元数据（runner 原生直写保存，未倒填）：

| 命令 | exit_code | native_exit_after_wait | elapsed(s) | timeout(s) | timed_out | pid |
| --- | ---: | ---: | ---: | ---: | --- | ---: |
| `vlib <run>/work` | 0 | 0 | 0.192（见 command.json） | 60 | false | 见文件 |
| `vlog -sv +incdir… -work <run>/work <3 厂家源> <33 工程源> <新 TB>` | **2** | **2** | 0.481 | 60 | false | 68972 |

`compile.log` 结论行：`Errors: 258, Warnings: 0`；`-- Compiling module` 共出现 **36** 个模块（与清单 `module_count=36` 一致），即所有源都被读到，失败发生在 IP 包装文件的 `` `include `` 解析。

## 2. 失败根因（只读定位，未修改任何文件）

```
** Error: .../inputs/project/ipcore/inst_rom/rtl/ipm2l_spram_v1_8_inst_rom.v(50):
   Cannot find `include file "inst_rom_init_param.v" in directories:
** Error: .../inputs/project/ipcore/data_ram/rtl/ipm2l_spram_v1_8_data_ram.v(...):
   Cannot find `include file "data_ram_init_param.v" ...
```

- 259 行错误中 **258 条** 全部来自这两个文件（各 129 条：1 条找不到 include + 128 条 `INIT_xx` 未定义）。
- 工作树里这两个文件**存在**，但**不在**封存清单的 197 项工程输入里，因此 runner 也没有把它们复制进运行目录：

| 工作树文件 | 大小 | SHA256 | 是否在 `project_sha256` | 是否在运行副本 |
| --- | ---: | --- | --- | --- |
| `ipcore/inst_rom/rtl/inst_rom_init_param.v` | 63918 | `77fdcc689dcfdfac13258f3754ae1f60351f806b055e7f4ae0e75e130a3af3a0` | **否** | **否** |
| `ipcore/data_ram/rtl/data_ram_init_param.v` | 63919 | `ad79a0fe32e541c0ec03f05fa44c4fd9870b9cd6bc3686815b4e25c222b550d3` | **否** | **否** |
| `ipcore/icache/rtl/icache_init_param.v` | 1032 | `f4f76865d9681707…` | 否 | 否（本次无相关报错） |
| `ipcore/dcache/rtl/dcache_init_param.v` | 1032 | `f4f76865d9681707…` | 否 | 否（本次无相关报错） |

- 运行副本中 `inputs/project/` 下**没有任何 `*_init_param*` 文件**（唯一的 `.vh` 是 `myriscv/csr_defs.vh`）。
- 编译 argv 的 incdir 已包含 `inputs/project/ipcore/inst_rom/rtl` 与 `inputs/project/ipcore/data_ram/rtl`，因此**只要把这两个文件按相同相对路径加入封存输入，包含即可解析**。
- 也就是说：这不是 RTL、TB、模型、参考或判据的问题，而是**收尾清单的项目输入集合漏收了两个 `include` 依赖**。

## 3. 已保存的原始证据（本次正式运行）

| 文件 | 说明 |
| --- | --- |
| `result.json` | `STOPPED_FIRST_FAILURE` 及错误字符串 |
| `vlib.command.json` / `vlib.log` | vlib 原生 argv/cwd/exit/native/elapsed/timeout |
| `compile.command.json` / `compile.log` | vlog 完整 argv（含全部 36 个源与 incdir）、native exit 2、258 错 0 警全文 |
| `git_before.json` | 运行前 HEAD + `git status --porcelain -uall` 全文 |
| `inputs/` | 197+3+3 封存输入副本（与清单逐项 SHA 一致） |
| `inputs.json` | 原 Codex inputs SHA `1b19dad3…b692` 的副本 |
| `simulation_completion_inputs.json` | 收尾清单 SHA `513b578c…13c96` 的副本（运行前已核对） |

身份核对（执行前）：`simulation_completion_inputs.json` SHA = `513b578cf6d91ed50700194664b720027e49a7ba3d67867a8cda23466fb13c96` ✔；原 Codex `inputs.json` SHA = `1b19dad3e2c9321b6729d42cd2455ea49fcb3f7bf7e1e3cbc5cc0406b403b692` ✔；`pds_shell` 计数 0 ✔；正式 tag 目录执行前不存在 ✔。

运行后只读复核：清单 `project_sha256` 197 项、`vendor_sha256` 3 项、`tool_sha256` 3 项**逐项存在且 SHA256 一致**（0 处不符）；`git status --porcelain -uall` 与 `git_before.json` **逐行相同**（本任务新增产物均被 gitignore，`build/` 下无新未跟踪项），HEAD 未变；`git_after.json` **未生成**（失败于其写入之前，如实记录、不补造）。

## 4. 追加说明：设计检查阶段是否有可复用的真实元数据

按收尾范围第 1 条先查了上一轮设计自校验目录 `sim/write_buffer_turnover/build/design_check_20261014_a/`：

- 其中 **vlib/compile 有真实 `command.json`**：`vlib` exit 0 / native 0 / 0.053 s / 60 s 上限 / 未超时；`compile` exit 0 / native 0 / 0.384 s / 60 s 上限 / 未超时。
- 其中 **`control`/`key` 只有 `.log` 与 `.transcript`，没有 `command.json`**（当时由直接 subprocess 调用产生），因此这两个 job 的真实 exit/native/elapsed/timeout **不存在可复用来源**；按约定**没有倒填**，也不把它们当作本次正式证据。
- 该目录的 `control.log`/`key.log` 属于历史设计检查日志（Codex 收据 `DESIGN_CHECK_LOGS_PASS_FORMAL_HANDOFF_INCOMPLETE`），**不是功能门 PASS**，本次也未从它们推导任何 PASS 结论。

## 5. 未执行 / 未覆盖范围

- `control`、`key` 两个 vsim job **未运行**（未启动 HDL 仿真，vsim 进程从未创建）。
- 新 TB 的独立 CPU EV / BUS / AW/W / 接续机会 / 取消与 busy 轨迹 **均未产生**；短程序完整 6 笔 W 轨迹、82 机会/81 接受/1 late 的逐拍解释 **均未取得**。
- `git_after.json`、`result.json` 的 `completed`/`inputs_unchanged`/`git_unchanged` 等收尾字段未写入。
- 未执行 PDS、未开串口、未做 KEY0/实板、未做 Git 提交推送。
- 未运行 `review_completion.py`（Codex 审查入口，按约定不交 DeepSeek）。
- 未运行原 `run.py` / `simulation_runner.py` / `prepare*.py`，未修改 TB、include、模型、参考、脚本、清单、判据或超时。

## 6. 交回 Codex 的最小修复线索（本次未实施）

把这两个 `include` 依赖补入 `simulation_completion_inputs.json` 的工程输入集合，并按相同相对路径随输入副本一起复制（incdir 已覆盖其目录，无需改编译参数）：

```
ipcore/inst_rom/rtl/inst_rom_init_param.v   SHA256 77fdcc689dcfdfac13258f3754ae1f60351f806b055e7f4ae0e75e130a3af3a0
ipcore/data_ram/rtl/data_ram_init_param.v   SHA256 ad79a0fe32e541c0ec03f05fa44c4fd9870b9cd6bc3686815b4e25c222b550d3
```

修复后需要新的授权与新的运行目录（本次 tag 目录按约定保留、不清理、不复用）。当前功能门仍关闭，**不给上板命令**，实板收益未测。
