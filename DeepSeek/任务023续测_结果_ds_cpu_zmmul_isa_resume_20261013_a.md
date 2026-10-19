# 任务023续测 结果：ISA 启动 CSR 探测精确核验 PASS（tag ds_cpu_zmmul_isa_resume_20261013_a）

**结论：`PASS`，`functional_status=KEY_MULTIPLY_SUITE_PLUS_TWO_ISA_SAMPLES_PASS`。**
三例全部通过：旧 CPU `baseline_lhu` 对照、当前 CPU `isa_lhu`、当前 CPU `isa_or`；每例恰好 **5 条 trap（4 个启动探测 + 1 个通过 ECALL）**、`tohost=1`、`muls=0`。**四个启动探测的 PC/指令/cause/tval/目标已按精确参考逐条实测确认**，旧/新 lhu 的架构事件轨迹**逐字节相同**（`IDENTICAL_ARCHITECTURAL_EVENTS`）。未重跑七乘法用例（按证据复用）、未跑全 ISA/Hello/CoreMark/桥/DDR PHY/工具实验；未执行 PDS、串口、上板、Git 提交或推送。

## 1. 身份与前置

| 项目 | 值 |
| --- | --- |
| 当前 CPU | `myriscv/mycpu_sync.v` SHA256 `43e451038cc14b3402ff159629d18783fbd8d1364e7c05197fadbb1e8e5d6cfe` |
| 旧 CPU（冻结对照，只作仿真输入） | `build/preparation_20261013_a/mycpu_sync.v` SHA256 `746db2f648276e706f766cced8848038e0b93a194ef0a077d0613d96cca9f7e7` |
| PDS（仅登记 IP，未执行） | `RISCV.pds` SHA256 `c5f87d111f751e0f2205fa5471a4002dc88d59c67b3de43f813c47395eaa6916` |
| 真实 mul IDF | `ipcore/mul/mul.idf` SHA256 `1f583b2ee87c795c7f7ae41b4c6263703b6bdeeb8f7fb0af7f7932bb22ae9a33` |
| I64/D64 桥（本轮未涉及） | `d8ae040965e92b97b859b5125c775cc95a4493f752d64100486da2f3c5b5cf09` |
| 续测清单 | `sim/cpu_zmmul/isa_resume_inputs.json` SHA256 `dbd4f0fee409fd27166b79d55979aa908b16220b792c1fa6d39c11a7bff10c1d`（原 305+10 之外新增 40 项） |
| 原清单（未刷新） | `sim/cpu_zmmul/inputs.json` SHA256 `f8ebb23bb096017e2b373872adc100042732289bc24c242564d9e9c09de6fa86` |

固定 tag `ds_cpu_zmmul_isa_resume_20261013_a` 启动前确认不存在（未换 tag、未清理）；`pds_shell` 计数 0。只读检查退出 0：

```text
INPUTS_MATCH_ISA_CONTINUATION_NOT_SIMULATED original=305+10 continuation=40 reused=7 jobs=baseline_lhu,isa_lhu,isa_or
```

## 2. 编译与七个命令

两个独立库，均 14 模块、单顶层 `tb_cpu_rv32i_sample`，`Errors: 0, Warnings: 0`：

- 模块：`GTP_GRS, GTP_APM_E2, alu, br_alu, l_alu, regfile, csr_file, mycpu_sync, mul, ipm2l_mult_v1_3_mul, ipm2l_apm_data_pipeline, ipm2l_apm_distributed_sdpram, ipm2l_apm_distributed_shiftregister, tb_cpu_rv32i_sample`
- baseline 库编入的是**冻结旧 CPU** `build/preparation_20261013_a/mycpu_sync.v`，current 库编入主 CPU `myriscv/mycpu_sync.v`；乘法模块在 baseline 中编译但未被旧 CPU 例化。

| 命令 | 上限 | 用时 | 退出码 | 超时 |
| --- | ---: | ---: | ---: | --- |
| vlib_baseline | 60 s | 0.09 s | 0 | 否 |
| compile_baseline | 60 s | 0.18 s | 0 | 否 |
| baseline_lhu | 180 s | 1.55 s | 0 | 否 |
| vlib_current | 60 s | 0.05 s | 0 | 否 |
| compile_current | 60 s | 0.18 s | 0 | 否 |
| isa_lhu | 180 s | 1.52 s | 0 | 否 |
| isa_or | 180 s | 1.61 s | 0 | 否 |

## 3. 实测五条 trap 行（逐字，来自各例 console）

`baseline_lhu` 与 `isa_lhu` 的行完全相同（tval 与目标均按精确参考）：

```text
# ISA_TRAP: baseline_lhu index=0 pc=800000e4 inst=74445073 cause=2 tval=74445073 target=800000e8 rf_we=0
# ISA_TRAP: baseline_lhu index=1 pc=800000f4 inst=18005073 cause=2 tval=18005073 target=800000f8 rf_we=0
# ISA_TRAP: baseline_lhu index=2 pc=8000010c inst=3b029073 cause=2 tval=3b029073 target=80000118 rf_we=0
# ISA_TRAP: baseline_lhu index=3 pc=80000128 inst=30205073 cause=2 tval=30205073 target=80000130 rf_we=0
# ISA_TRAP: baseline_lhu index=4 pc=80000478 inst=00000073 cause=11 tval=00000000 target=80000004 rf_we=0
```

```text
# ISA_TRAP: isa_lhu index=0 pc=800000e4 inst=74445073 cause=2 tval=74445073 target=800000e8 rf_we=0
# ISA_TRAP: isa_lhu index=1 pc=800000f4 inst=18005073 cause=2 tval=18005073 target=800000f8 rf_we=0
# ISA_TRAP: isa_lhu index=2 pc=8000010c inst=3b029073 cause=2 tval=3b029073 target=80000118 rf_we=0
# ISA_TRAP: isa_lhu index=3 pc=80000128 inst=30205073 cause=2 tval=30205073 target=80000130 rf_we=0
# ISA_TRAP: isa_lhu index=4 pc=80000478 inst=00000073 cause=11 tval=00000000 target=80000004 rf_we=0
```

```text
# ISA_TRAP: isa_or index=0 pc=800000e4 inst=74445073 cause=2 tval=74445073 target=800000e8 rf_we=0
# ISA_TRAP: isa_or index=1 pc=800000f4 inst=18005073 cause=2 tval=18005073 target=800000f8 rf_we=0
# ISA_TRAP: isa_or index=2 pc=8000010c inst=3b029073 cause=2 tval=3b029073 target=80000118 rf_we=0
# ISA_TRAP: isa_or index=3 pc=80000128 inst=30205073 cause=2 tval=30205073 target=80000130 rf_we=0
# ISA_TRAP: isa_or index=4 pc=80000684 inst=00000073 cause=11 tval=00000000 target=80000004 rf_we=0
```

与任务书第 41–47 行的参考表**逐字段一致**：三条 `CSRWI/CSRW` 启动探测均为 `cause=2` 且 `tval=指令编码`，目标分别跳过 `pmpcfg0`（→80000118）与 `mideleg`（→80000130），**不是六个启动 trap**；通过路径 ECALL 为 `cause=11`、`tval=0`、目标 80000004。所有 trap `rf_we=0`，无 IRQ。

## 4. 每例 CHECK / RESULT / 结束状态

```text
# CHECK: baseline_lhu PASS tohost=00000001 traps=5 probes=4 muls=0 events=320
# RESULT: PASS rv32i_sample case=baseline_lhu tohost=1 traps=5 probes=4 muls=0

# CHECK: isa_lhu PASS tohost=00000001 traps=5 probes=4 muls=0 events=320
# RESULT: PASS rv32i_sample case=isa_lhu tohost=1 traps=5 probes=4 muls=0

# CHECK: isa_or PASS tohost=00000001 traps=5 probes=4 muls=0 events=530
# RESULT: PASS rv32i_sample case=isa_or tohost=1 traps=5 probes=4 muls=0
```

三例均：`ISA_TRAP` 行 = 5、`CHECK` 行 = 1、`RESULT` 行 = 1、`$finish` 存在、`Errors: 0, Warnings: 0`、`RPC_Init` = 0、无超时；console 与 transcript **非空且换行归一后全文相同**（2991/2954、3620/3577、3554/3511 字节）。

## 5. 旧/新 lhu 架构轨迹比较

```json
{
  "status": "IDENTICAL_ARCHITECTURAL_EVENTS",
  "events": 320,
  "baseline_trace_sha256": "fa225db4be529a0316ba9cb479b9710935a1140f19fa16cd1df47fd25371bc6e",
  "current_trace_sha256": "fa225db4be529a0316ba9cb479b9710935a1140f19fa16cd1df47fd25371bc6e",
  "ignored_fields": "clock timestamp; non-writing rd/data; non-trap cause/tval/target"
}
```

我独立哈希复核：`baseline_lhu.events.log` 与 `isa_lhu.events.log` **SHA256 完全相同**（`fa225db4…bc6e`，各 20966 字节）；`isa_or.events.log` 为 `adbd18e6…91c2`（34846 字节，530 事件）。比较覆盖事件种类、PC、指令、写许可/写寄存器/写值、trap 的 cause/tval/target，仅忽略时钟时间戳和不生效旁带字段——**不是只比末尾 tohost**。

**关于原 023 的 `isa_lhu` FAIL**：本轮实测表明原 TB 在第 38 号事件、PC `800000e4`（即第一个启动探测 `CSRWI 744,8`）上先于通过路径触发，而旧判据只允许标准结束 ECALL，因此报“unexpected ISA trap/IRQ”。新证据显示该 trap 是**ROM 固有启动流程的一部分**（cause2/tval=74445073/目标 800000e8），且旧 CPU 与当前 CPU 在该样本上的架构轨迹**逐字节一致**——即对 `lhu` 样本，Zmmul 改动未造成任何架构差异，原 FAIL 归因于旧 TB 的判据缺口而非 RTL 回归。**该结论仅覆盖 lhu 样本（320 事件）**；`or` 仅跑了当前 CPU 一例（530 事件），本轮按任务要求未做 `or` 的旧 CPU 对照。

## 6. 输入冻结、复用与 git 守恒

- 复用原 023 的 305 份冻结输入（`source_identity.json` 指向 `build/ds_cpu_zmmul_20261013_a/inputs`），新 tag 只**新增 5 份**续测快照：`resume_isa.py`、`review_task023.py`、`tb_cpu_rv32i_sample.sv`、`fixtures/isa_lhu_traps.txt`、`fixtures/isa_or_traps.txt`（`new_inputs/` 内实测 5 份）；未重复复制旧 305 源或旧日志。
- `git_before.json` 与 `git_after.json` 内容哈希相同；HEAD `7af48d2185bc01a62be528c70b83c42689394c31`。
- 原 023 目录保持原状：`result.json` 仍为 `STOPPED_FIRST_FAILURE`，`git_after.json` **仍缺失**（未因本次新快照而补推旧收尾）。
- `source_identity.json` 同时保护了我 023 停止报告的哈希（`04e1166b…339d`）。
- 执行后无残留仿真进程；未修改任何主 RTL/CSR/PDS/IP/旧 TB/fixtures/判据/旧清单/成功镜像/原报告。

## 7. 未覆盖范围

- 未重跑七个乘法用例（按原 023 原始 PASS 证据复用：2839 事件 / 396 乘法退休）；未跑全 ISA、Hello/CoreMark、桥/DDR PHY 或工具 RPC 实验；未追加其它随机 ISA。
- 仅为 **CPU 直连接口 + 真实乘法原语** 的仿真：不代表完整 SoC、DDR PHY、时序、资源或实板性能 PASS；本轮与 I64/D64 桥、成功位流无关。
- 独立 Zmmul 软件（rv32i_zmmul CoreMark）尚未构建/CRC 验证；CPU/PDS/板级收益仍待后续门。
- 未执行 PDS 实现、未开串口、未上板、未提交或推送 Git。

## 8. 交回 Codex

按约定停在本轮三例。原始证据在 `sim/cpu_zmmul/build/ds_cpu_zmmul_isa_resume_20261013_a/`：两库的 `vlib_*/compile_*.command.json` 与 `*.log`、三例 `*.log`/`*.transcript`/`*.command.json`/`*.events.log`、`lhu_architectural_comparison.json`、`result.json`、`git_before/after.json`、`source_identity.json`、`new_inputs/`。Codex 原始核验通过后，才可把旧七例与本轮三例合并记为“乘法关键功能 + 两例 ISA 抽测”完成；仍**不能**声明全 ISA / SoC / PHY / 时序 / 实板 PASS。
