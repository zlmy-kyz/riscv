# 任务032时序修复 结果：指令响应来源寄存器关键仿真（`ds_data_bus_turnover_timing_repair_20261014_a`）

**状态：`TASK032_INST_RESPONSE_SELECTOR_TIMING_REPAIR_KEY_PASS`。一次执行完成，未重试、未改任何既有文件。**

- 三条原生 job（`vlib` / `vlog` / `key vsim`）全部 exit/native 0、未超时、`cleanup=None`；38 模块、`Errors: 0, Warnings: 0`、正常 `$finish`、console 与 transcript 归一后逐字相同；`IPSpecCheck` **恰好 2 条**且值均 `04030130`。
- **只跑了 key**；control 与"修复前 key"分别用已复核收据复用，未重跑。
- **修复后 key 与修复前 key 逐字段完全相同**：unit 33 拍/51 接续、SoC **617 拍 / MEM 415 拍 / 18 接续**（runner 用 `checked_key` 整段相等断言，`key_identical_to_pre_repair=true`）——即本时序修复**不加拍**。
- 相对复用 control 的差值：unit **−31** 拍、SoC 总周期 **−2** 拍、MEM 等待 **−28** 拍。
- **PDS 时序、位流、串口、实板全部 NOT_RUN**；本仿真不证明 WNS 修复。

原始目录：`sim/data_bus_turnover/build/ds_data_bus_turnover_timing_repair_20261014_a/`

## 1. 本轮实现代码与最终身份

| 项 | 值 |
| --- | --- |
| 新清单 | `sim/data_bus_turnover/inputs_timing_repair.json` |
| 新清单 SHA256 | **`5e5c0c309320b3d73ff48eed5a68a4940fbc4b0d86a10c6d28a6cf33051f71c4`** |
| 被修桥 | `myriscv/dual_sram_to_pango_ddr_bridge.v`：`97273a85137600e596b38a3e061cf2841bf24bc397bf9412688cd580fa164c20` → **`1df26c253243f6419390b733d4d6479efd4a7eb91f8439fe17587a7b55c03c08`** |
| 工程输入 | **168**（= 上一轮 166，其中**只有桥身份改变**，另加本轮 2 个实现文件） |
| 保护证据 | **821**（上一轮 626 ∪ 旧 229 清单 ∪ 旧 key 目录除 `work` 库的 **184** 个文件（含 Codex 门/输入副本/原生元数据/日志/轨迹/Git/result）∪ 旧收尾报告 ∪ 本轮修复准备目录 **9** 个文件），重复路径哈希全部相等 |
| 未变 | checker `0bdf70c4…c68242`、TB `cb1adf6f…990b10`、CPU `b1114fa3…f4a41d3`、互连 `b0afffb5…131f24`；`compile_sources`(33)/`expected_modules`(38)/`include_dependencies`(5)/`timeouts`/厂家(3)/工具(3) 与上一轮**逐字相同** |
| 绑定 | control 收据 `61c2dc2d…91ba13`（`source_run` = `…grs_resume_20261014_a`，`checked` 整段）；修复前 key 门 `cd6a9fb6…f7eaaf`（`checked_key` 整段即本轮 `expected_key`） |

新增实现（均已登记进清单并随输入副本封存）：

| 文件 | 作用 |
| --- | --- |
| `sim/data_bus_turnover/run_timing_repair.py` | 新主入口：核输入→新目录→vlib/vlog→**仅 key**→以 `checked_key` 整段相等核验"未加拍"→Git 前后/结果 |
| `sim/data_bus_turnover/seal_timing_repair.py` | 封存脚本（含 `--check` 自查） |

**未修改** RTL 之外任何文件：TB/include/模型/独立参考/DAT/checker/成功镜像/PDS/约束/判据/超时全部保持；也未复用 `run_ip_count_key_resume.require_inputs()`（它绑定旧桥），改由本入口按新清单做限定核验。

自查（native 启动前全部通过）：

```powershell
python -B sim/data_bus_turnover/seal_timing_repair.py --check
python -B sim/data_bus_turnover/run_timing_repair.py --check-inputs
python -B sim/data_bus_turnover/run_timing_repair.py --plan-only
```

输出：`SEAL CHECK PASS project=168 protected=821 bridge=1df26c253243f641 control_review=61c2dc2dbb638646 key_review=cd6a9fb6fc004e35`；
`RESULT: PASS Task032 instruction-response selector repair inputs; bridge 97273a85->1df26c25; control reused 64/619/443; key must stay 33/617/415/18; HDL NOT_RUN; ISA=0`；
`--plan-only` 的 jobs 恰为 `["vlib","compile","key"]`（**无 control**）。
自查项还包括：与上一轮相比**只有桥**变化（其余 165 项逐项相等）；compile/include/模块/超时/厂家/工具逐字等于上一轮；checker 仍是"冻结文件 + 唯一一处提示条数修正"的字节级证明；旧 control 收据与旧 key 门 SHA 与 `checked`/`checked_key` 内容仍与绑定一致；5 条 include 闭合、两个 `*_init_param.v` 就位、TB 顶层含 `GTP_GRS GRS_INST`；`reference.json` 由 `program.dat` 独立重算仍相等；Python AST 全过。

## 2. 三条原生命令的真实元数据

| job | exit | native | elapsed(s) | 上限 | timed_out | cleanup |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| `vlib <run>/work` | 0 | 0 | 0.0927 | 60 | false | none |
| `vlog -sv +incdir… -work <run>/work <3 厂家源><35 模块源>` | 0 | 0 | 0.3836 | 60 | false | none |
| `vsim -batch -lib <run>/work tb_data_bus_turnover -gTURNOVER=1 +DAT=… +UNIT_LOG=… +EV_LOG=… +BUS_LOG=… -logfile … -do "run -all; quit -f"` | 0 | 0 | 1.9484 | 180 | false | none |

完整 argv/cwd/exit/native/elapsed/timeout/pid 由 runner 原生直写保存在 `*.command.json`；stdout 与 `-logfile` transcript 双份保留。

## 3. 全部功能检查（原 strict 判据逐条保持）

```
CHECK: response_owner_matrix PASS cases=24      （68 场景 = 24+5+5+2+32）
CHECK: old_error_blocks      PASS cases=5
CHECK: posted_write_order    PASS cases=5
CHECK: delayed_reset         PASS cases=2
CHECK: consecutive_requests  PASS cases=32 cycles=33
UNIT: pairs=24 errors=5 order=5 burst=32 cycles=33 turns=51 cancelled=1
SOC: cycles=617 events=82 turns=18 mem_wait=415 fault=1 error_rsp=1 mmio=5 uart=1 ram=1 fence=1 fence_wait=8 aw=5 w=5
RESULT: PASS data_bus_turnover key_group TURNOVER=1
Errors: 0, Warnings: 0        （IPSpecCheck: 恰好 2 × 04030130）
```

- **unit**：`UREQ 100 = URSP 99 + URESET 1`、`URESET=1`、`turns=51`、`cycles=33`；每笔 UREQ 的目标译码/token/error 位与"响应同拍发新请求"判定逐条核验。
- **SoC**：`CPU_REQ = CPU_RSP = 49` 逐字段对独立参考；`AR 40 = R 40`（每拍 8×32bit 独立重算并逐拍比对）、`AW 5 = W 5`（地址/data/strobe 展开与 W 拍逐字节相等）、`TURN 18` 与 `turns=18` 一致；
  `SIDE_MMIO=6 / SIDE_RAM=2 / SIDE_UART=1 / FENCE=1`；DDR 最终字 `0x800=0x33444444`、`0x804=0x80c=0x11223344`、`0x808=0xa5a5a5a5`；
  `fault=1 / error_rsp=1`（精确 PC 40000094 / cause5 / tval 20000000→40000300，年轻 40000808 store 未被接受/写 DDR/退休）；排空与原响应归属保持。
- **EV**：`key.events.log` **82 行**与冻结参考逐事件（逐 PC/inst/we/rd/data/cause/tval/next）相等。
- **轨迹非空**：`key.unit.log` 200 行、`key.events.log` 82 行、`key.bus.log` 216 行。

## 4. 实际周期（与修复前、与 control）

| 指标 | 复用 control | 修复前 key（已复核门） | **本次修复后 key** | 与修复前 |
| --- | ---: | ---: | ---: | --- |
| unit cycles | 64 | 33 | **33** | **相同** |
| unit turns | 0 | 51 | **51** | 相同 |
| SoC cycles | 619 | 617 | **617** | **相同（不加拍）** |
| SoC MEM 等待 | 443 | 415 | **415** | **相同** |
| SoC turns | 0 | 18 | **18** | 相同 |
| EV / 请求 / AR=R / AW=W / MMIO / UART / RAM / FENCE / fence_wait | 82/49/40/5/6/1/2/1/8 | 同左 | **同左** | 相同 |

`result.json` 记录 `new_key_cycles=617`、`new_key_mem_wait=415`、`new_key_turns=18`、`deltas={unit_cycles_saved:31, soc_cycles_saved:2, soc_mem_wait_saved:28, key_identical_to_pre_repair:true}`，并绑定 `bridge_sha_before/after`、`reused_control_review_sha256`、`reused_key_review_sha256`。

## 5. 输入、保护与 Git

- 新清单 168 工程 / 821 保护**逐项 SHA256 全等（0 处不符）**；运行副本 `inputs.json` SHA = 冻结清单 SHA；171 份输入文件落盘；5 条 include 在副本目录闭合。
- `git_before.json` 与 `git_after.json` **完全相等**（runner 内断言通过）；运行后只读复核：当前 `git status --porcelain -uall` 与 `git_before.json` 逐行相同。
- 全部旧目录/清单/报告/门保持原样：`ds_data_bus_response_turnover_20261014_a`、`…_grs_resume_…`、`…_ip_count_key_…`、三个 preparation 目录与两份旧清单（`427844a5…`、`fa8bf3ae…`、`22959513…`）均未改动；旧缺失 `git_after.json` 继续为缺（不倒填）。

## 6. 未覆盖范围与边界（含方案声明的未动态覆盖项）

- **AR 接受同拍 R 返回的来源选择相位**：冻结的用户口模型未模拟该相位，因此该相位**未获动态覆盖**，仅由 Codex 的状态逻辑审查覆盖——本次不宣称已覆盖全部 DDR 返回相位。
- **PDS 时序/资源、位流、串口、KEY0、实板全部未执行**（`timing=NOT_RUN`、`board=NOT_RUN`）：本次只证明"功能与周期等价（不加拍）"，**不证明** WNS −0.035 ns / 1 个失败端点已修复；时序是否通过必须由用户重新实现后的新 PDS 报告判定，不能沿用旧门或旧位流。
- 未跑 031/030 历史、ISA、CoreMark、PHY；未运行 `review.py`/`review_grs_resume.py`/旧 runner/旧 tag；未生成 `codex_review.json` 或任何 Codex PASS 门；未做 Git 提交推送。
- 未修改设计 RTL 之外的任何输入、判据、超时；未放宽原语提示口径。

## 7. 交回 Codex

证据齐备（新清单/168+821 输入副本/三条原生命令/UNIT/EV/BUS/Git/result 全部落盘），可只读核验本轮"只改桥 + checker 一行"的实现与原始证据。当前总功能门未开放，033 不启动；实板新日志目录待 Codex 通过后单独准备。
