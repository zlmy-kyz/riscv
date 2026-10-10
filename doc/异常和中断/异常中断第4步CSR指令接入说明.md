# 异常与中断：第 4 步接入 CSR 指令

> GitHub 发布说明（2026-10-10）：下文标为“仅本地”的历史档案/参考材料保留在开发机，未随本次源码发布；原验收结论和哈希不变。当前开发入口见 doc/CODEX_HANDOFF.md。

本步把 [`csr_file.v`](/D:/riscv/RISCV/myriscv/csr_file.v) 接入 [`mycpu_sync.v`](/D:/riscv/RISCV/myriscv/mycpu_sync.v)，实现六条 Zicsr 指令的读、读改写和 GPR 写回。沿用第 3 步的串行控制：CSR 在 ID 等待老指令排空，只发射一次，到 WB 提交后经过一个 `FLOW_IRQ_CHECK` 控制周期，才释放后续指令。这个控制周期目前只预留位置，中断仲裁尚未接入。

## 指令语义

| 指令 | CSR 新值候选 | 是否读旧值 | 是否写 CSR |
|---|---|---|---|
| CSRRW | `rs1` 的值 | `rd != x0` | 始终写；`rs1=x0` 也写零 |
| CSRRS | `旧值 \| rs1` | 是 | `rs1` 编号非零时写 |
| CSRRC | `旧值 & ~rs1` | 是 | `rs1` 编号非零时写 |
| CSRRWI | 零扩展的 `zimm` | `rd != x0` | 始终写；`zimm=0` 也写零 |
| CSRRSI | `旧值 \| zimm` | 是 | `zimm != 0` 时写 |
| CSRRCI | `旧值 & ~zimm` | 是 | `zimm != 0` 时写 |

上述“是否写”看 `rs1` 字段的**编号**或 `zimm`，不看寄存器中的数据。例如 `CSRRS x10, mconfigptr, x9` 中即使 `x9=0`，仍是对只读 CSR 的非法写访问。`rd=x0` 只抑制 GPR 写回；CSRRW/CSRRWI 还抑制 CSR 旧值读取。其他四条在 `rd=x0` 时仍按语义读取 CSR。

CSR 地址由指令 `inst[31:20]` 提取。操作选择由 `funct3[1:0]` 传递：`01` 直接写、`10` 置位、`11` 清位。寄存器形式使用 ID 级 `id_rs1`，所以可以取得已有前递结果；立即数形式使用零扩展 `zimm=inst[19:15]`，不会把该字段当作 GPR 编号使用。

## 五级流水线中的数据流

| 阶段 | 本步操作 |
|---|---|
| IF | 取指并保持指令与 PC 配对。 |
| ID | 识别六条 CSR 指令；生成读许可、写意图、CSR 地址、操作和源值。CSR 在这里等待旧项排空，然后一次性 `id_fire`。 |
| EX、MEM | CSR 不访问数据 RAM；地址、操作、源值、读/写意图随 `valid` 和原有 `rd`、PC、指令字逐级传递。气泡、取消或复位时清除 CSR 元数据。 |
| WB 组合逻辑 | `csr_file` 按地址和读许可给出**提交前旧值**及 `csr_access_illegal`。CPU 按操作算出 `csr_wdata`，并选择旧值作为 `rf_wdata`。 |
| WB 上升沿 | 合法且有写意图时更新 CSR；`rd != x0` 时把旧值写入 GPR。`debug_wb_rf_wdata` 与 GPR 写口共用 `rf_wdata`。 |

连续 CSR 的后条指令会在前条 WB 提交并经过 `FLOW_IRQ_CHECK` 后再发射，因此能读到前条写入的新值。CSR 结果后接 ALU、branch 或 store 也能使用正确的 GPR 值。首版为精确提交和后续中断处理保留串行停顿；这是当前的性能代价，后续若放开流水并行，需要另外处理 CSR 顺序、转发和异常取消。

### 新增或改变的 CPU 内部信号

| 信号 | 位宽 | 作用 |
|---|---:|---|
| `csr_inst`、`csr_imm_form` | 各 1 | 六条 CSR 的总识别、三条立即数形式的识别。 |
| `csr_read_req`、`csr_write_req` | 各 1 | ID 级根据指令字段生成读许可和写意图。 |
| `csr_src` | 32 | ID 级选择前递后的 `rs1` 值或零扩展的 `zimm`。 |
| `id_ex_csr_*`、`ex_mem_csr_*`、`mem_wb_csr_*` | 标志 1、地址 12、操作 2、源值 32、读许可 1、写意图 1 | CSR 元数据随有效流水项移动。PC、指令字、`rd` 继续使用原有流水寄存器。 |
| `wb_csr_valid`、`wb_csr_read_en`、`wb_csr_write_intent` | 各 1 | WB 有效项和提交请求门控；复位或气泡不会访问 CSR。 |
| `csr_rdata`、`csr_wdata` | 各 32 | CSR 旧值及本条指令计算的新值候选。 |
| `wb_csr_illegal` | 1 | `csr_access_illegal` 与 WB 有效 CSR 项结合后的检查结果。 |
| `csr_commit` | 1 | 合法 CSR 项在 WB 的一次性提交脉冲；`csr_file` 再用写意图决定是否更新状态。 |
| `rf_we`、`rf_wdata` | 1、32 | 非法 CSR 关闭 GPR 写；合法 CSR 选择旧值写 `rd`。调试写回数据使用相同选择结果。 |
| `gf_we`、`uses_rs1` | 各 1 | GPR 写许可改为已实现指令白名单；寄存器型 CSR 纳入 `rs1` 使用判断，立即数型 CSR 不使用 GPR。 |
| `trap_redirect_target`、`mret_redirect_target` | 各 32 | 已连到 `csr_file` 的目标地址；第 5 步接入同步异常控制重定向，第 6 步接入 trap CSR 状态更新和 MRET 提交。 |

`csr_access_illegal` 对不存在的 CSR 地址及写只读 CSR 地址置位。第 4 步在 WB 抑制这条指令的 GPR 和 CSR 写入，但当时**尚未产生 cause 2、写 `mepc/mcause/mtval` 或跳转 `mtvec`**；非法 CSR 指令当时顺序流过。第 5 步接入异常记录和重定向，第 6 步接入 ECALL/EBREAK、trap CSR 更新与 MRET，第 7 步把非法 CSR 转为 cause 2。

## 验证

新测试台 `tb_csr_pipeline.v`（仅本地：`/D:/riscv/RISCV/difftest/tb/tb_csr_pipeline.v`） 覆盖六条 CSR、连续读改写、CSR 结果接 branch/ALU/store、`rd=x0`、`rs1=x0`、合法只读 CSR、固定值 CSR、`mstatus` 位、`mepc` 对齐及 WB 调试数据。第 7 步接入非法 CSR trap 后，非法地址、只读写访问和“`rs1` 编号非零但值为零”的检查移到 `tb_illegal_step7.v`（仅本地：`/D:/riscv/RISCV/difftest/tb/tb_illegal_step7.v`）。前者结果：`RESULT: PASS six CSR instructions, hazards, x0, legality and WB data`。

普通程序 `prog0_alu`、`prog1_mem`、`prog2_hazard_precision` 的指令流、写回轨迹及 GPR/RAM 终值差分测试均通过。`tb_hazard_precision` 和 `tb_pipeline_control` 也通过。第 2 步的 `csr_file` 独立测试覆盖其寄存器写掩码与 trap/MRET 状态规则；本步没有启动真实 trap/MRET。

仿真编译需要同时加入 `myriscv/csr_file.v`，并以 `-I myriscv` 让 `csr_defs.vh` 可见；`difftest/run.ps1`（仅本地：`/D:/riscv/RISCV/difftest/run.ps1`） 已加入这两项。真实 FPGA 工程也需要把 `csr_file.v` 和头文件纳入源文件/搜索路径，之后仍需综合与板级时序验证。
