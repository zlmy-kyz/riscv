# 任务032 结果：数据互连响应同拍接续关键仿真（`ds_data_bus_response_turnover_20261014_a`）

**状态：`STOPPED_FIRST_FAILURE`（首次失败即停止，未重试、未换 tag、未改任何文件）。**

- 第 1 条静态入口：**PASS**（exit 0）。
- 第 2 条正式运行：`vlib`、`vlog` 正常（38 模块、`Errors: 0, Warnings: 0`），
  但 **`control` 的 `vsim` 在载入设计（elaboration）时失败**：20 条 `Unresolved reference to 'GRS_INST'` + 1 条 `Error loading design`，native exit **12**、`Errors: 21, Warnings: 0`，**没有 `$finish`**。
- **`key` job 未派发**；无任何 UNIT/EV/BUS 原始轨迹；`git_after.json` 未生成。
- 根因是**冻结的新 TB 缺少厂家 DRM 仿真模型必需的 `GTP_GRS GRS_INST` 实例**，属准备阶段缺件，不是 RTL 功能失败。

原始目录：`sim/data_bus_turnover/build/ds_data_bus_response_turnover_20261014_a/`
`result.json`：`status=STOPPED_FIRST_FAILURE`、`HDL_started=true`、`completed={}`、`board=NOT_RUN`、`timing=NOT_RUN`、`PDS_started=false`、`serial_opened=false`。

## 1. 命令与真实元数据（runner 原生直写，未倒填）

| # | 命令 | exit | native | elapsed(s) | 上限(s) | timed_out |
| --- | --- | ---: | ---: | ---: | ---: | --- |
| 1 | `python -B sim/data_bus_turnover/run.py --check-inputs` | 0 | — | — | — | — |
| 2 | `vlib <run>/work` | 0 | 0 | 0.0841 | 60 | false |
| 3 | `vlog -sv +incdir… -work <run>/work <3 厂家源><35 模块源>` | 0 | 0 | 0.3274 | 60 | false |
| 4 | `vsim -batch -lib <run>/work tb_data_bus_turnover -gTURNOVER=0 …`（control） | **12** | **12** | 1.6946 | 180 | false |
| 5 | `vsim … -gTURNOVER=1 …`（key） | **未派发** | — | — | 180 | — |

第 1 条输出：`RESULT: PASS Task032 inputs; reference82/requests49; HDL NOT_RUN; ISA=0`。
编译日志：`-- Compiling module` 共 **38** 个，`Errors: 0, Warnings: 0`，Top level modules 为 `GTP_GRS`、`tb_data_bus_turnover`。

## 2. 失败点：control 载入设计失败（只读定位）

`control.log` 结尾：

```
** Error: (vsim-3043) Unresolved reference to 'GRS_INST'.
   Instance: /tb_data_bus_turnover/soc/u_inst_rom/U_ipm2l_rom_inst_rom/U_ipm2l_spram/…/U_GTP_DRM36K_E1
   File: .../inputs/vendor/GTP_DRM36K_E1.v Line: 1426      （同类共 20 条）
# Error loading design
# Errors: 21, Warnings: 0
```

- 20 条未解析引用**全部**是 `GRS_INST`（没有其他未解析信号）。
- 涉及实例：`soc/u_inst_rom`、`soc/u_data_ram`（多组 ADDR_LOOP/DATA_LOOP）、`soc/g_ddr/u_ddr_bridge/g_inst_drm/…/icache`、`…/g_data_drm/…/dcache`——即全部真实 ROM/RAM/DRM 原语。

根因（厂家源逐字）：`C:\pango\PDS_2022.2-SP6.4\arch\vendor\pango\verilog\simulation\GTP_DRM36K_E1.v:1426`

```verilog
assign grsn =  (GRS_EN == "TRUE") ? GRS_INST.GRSNET : 1'b1;
```

DRM 原语在**elaboration 期**需要层次路径 `GRS_INST` 存在。而本次冻结的新 TB
`sim/data_bus_turnover/tb_data_bus_turnover.sv` **既没有 `GRS_INST` 也没有 `GTP_GRS`**（只例化了 `soc_top` 与 `mini_ddr_model_x32`），
运行副本中的 TB 同样没有。作为对照，已完成并跑通的 TB 都在 TB 顶层例化了它：

| 文件 | 行 | 内容 |
| --- | --- | --- |
| `sim/write_buffer_turnover/tb_write_buffer_turnover_completion.sv` | 14 | `GTP_GRS GRS_INST (.GRS_N(1'b1));` |
| `sim/cpu_branch_turnover/tb_branch_turnover.sv` | 25 | `GTP_GRS GRS_INST(.GRS_N(1'b1));` |

因此本次失败是**新 TB 缺少 Pango DRM 模型所需的 GRS 实例**，`vsim` 连设计都没载入（无 `$finish`、无任何仿真时间推进），与 `data_bus_interconnect` 的改动、判据和激励都无关。

## 3. 身份与输入（执行前核对 + 运行后只读复核）

| 项 | 值 |
| --- | --- |
| 清单 `sim/data_bus_turnover/inputs.json` SHA256 | `427844a5db518bfbd95953426a82da7e4a31c6c67b535d8b791c493be2f2c370` ✔ |
| 新 tag 目录 | 执行前不存在 ✔ |
| `pds_shell` 并发 | 0 ✔ |
| `myriscv/data_bus_interconnect.v` | `b0afffb5c45f8a635b90482cc15bd94f17ce2c748fd6f1bdad9db0b098131f24`（新）✔，运行副本与工作树一致 |
| CPU `myriscv/mycpu_sync.v` | `b1114fa388b0da4a3c914da38f1b169d607b8ebed839dd018eab37fd0f4a41d3`（未变）✔ |
| 桥 `myriscv/dual_sram_to_pango_ddr_bridge.v` | `97273a85137600e596b38a3e061cf2841bf24bc397bf9412688cd580fa164c20`（未变）✔ |
| 输入集合 | 162 工程 + 3 厂家 + 3 工具，逐项存在且 SHA256 一致（0 处不符）；165 份副本落盘；清单副本 SHA = 冻结清单 SHA；两条 `*_init_param.v` include 已在副本中 |
| 旧证据 | `build/preparation_20261014_a` 及其余历史目录保持，未清理 ✔ |

`git_before.json` 已保存；`git_after.json` **未生成**（失败于其写入之前），按约定不补造。

## 4. 未执行 / 未覆盖范围

- **`key` job 未运行**；UNIT 五组 68 项、独立 EV/BUS、真实 SoC 82 事件/49 请求、MMIO/UART/RAM 副作用、FENCE/STOP 排空、access-fault 精确判定等**全部未取得证据**。
- `control` 只有失败日志（无 `$finish`、无仿真输出），未产生 UNIT/EV/BUS 轨迹；`control.command.json` 已保存真实 argv/exit/native/elapsed/timeout。
- 未执行 PDS/串口/KEY0/实板/Git 提交推送；未运行 `prepare_program.py`、`seal_inputs.py`、`review.py`；
  未修改任何 RTL/TB/include/模型/参考/脚本/清单/阈值/超时；未生成任何 Codex PASS 门。
- 因此 `DATA_BUS_RESPONSE_TURNOVER_KEY_GROUP_PASS` 未达成，功能门保持关闭。

## 5. 交回 Codex 的最小修复线索（本次未实施）

在新 TB（`sim/data_bus_turnover/tb_data_bus_turnover.sv`）的 TB 顶层补一个厂家 GRS 实例，与既有跑通 TB 完全一致：

```verilog
GTP_GRS GRS_INST (.GRS_N(1'b1));
```

`GTP_GRS.v` 已在编译源与运行副本中（Top level modules 里也出现了 `GTP_GRS`），无需新增文件或改编译参数。
修复后需**新授权 + 新运行目录**重跑（本次 tag 目录按约定保留、不清理、不复用）；本次的 control/key 判定与判据均未改动。
