# 异常与中断：第 2 步 CSR 模块

> GitHub 发布说明（2026-10-10）：下文标为“仅本地”的历史档案/参考材料保留在开发机，未随本次源码发布；原验收结论和哈希不变。当前开发入口见 doc/CODEX_HANDOFF.md。

本步新增独立的 [`csr_file.v`](/D:/riscv/RISCV/myriscv/csr_file.v)。第 2 步交付时它尚未连接 `mycpu_sync.v`；第 4 步已接入 CSR 指令流水，第 6 步已接入同步 trap 和 MRET 提交。中断提交仍待后续步骤。

## 接口约定

- `csr_addr` 选择 CSR；`csr_read_en` 控制组合读值，关闭时 `csr_rdata=0`。`csr_exists` 给出地址是否在实现白名单；`csr_readonly_addr` 标记五个只读机器信息地址。
- `csr_access_illegal` 在本次读/写请求访问不存在的地址、或写只读标识地址时为 1。`misa`、`mstatush` 和 `mip` 是可访问地址，其首版实现字段不可软件更改；对这些地址的写请求合法但无效果。
- CPU 在 WB 算出六条 CSR 指令的**最终候选值**，放入 `csr_wdata`，并仅在合法、正常提交的一拍拉高 `csr_commit`。只有 `csr_commit && csr_write_intent && !csr_access_illegal` 才改状态；本模块不负责译码、停顿或取消。
- `trap_enter`、`mret_commit` 是一次性提交脉冲。预期与 `csr_commit` 互斥；若上层误同时给出，复位 > trap > MRET > CSR 写。`trap_target` 为 Direct 模式入口；`mret_target` 为当前 `mepc`。
- 三根 `irq_*` 输入视为**已同步的电平**，直接组成 `mip` 视图。`irq_pending` 不受 `mie` 和 `mstatus.MIE` 屏蔽；使能分别通过 `irq_enable`、`irq_global_enable` 输出。外部异步引脚的同步在后续 SoC 层完成。

### `csr_file` 端口信号表

方向以 `csr_file` 模块为准。除 `csr_rdata`、合法性和目标地址等组合输出外，状态只在 `clk` 上升沿改变。

| 信号 | 方向/位宽 | 具体作用 |
|---|---|---|
| `clk`、`resetn` | 输入，1/1 | 时钟；`resetn=0` 在上升沿同步复位可变 CSR，复位优先于全部提交。 |
| `csr_addr` | 输入，12 | 本次 CSR 访问地址；同时驱动白名单、只读地址判断和读多路选择器。 |
| `csr_read_en` | 输入，1 | CSR 指令确实需要旧值时为 1；为 0 时 `csr_rdata=0`。例如 `CSRRW rd=x0` 不请求读。 |
| `csr_write_intent` | 输入，1 | 指令语义要求写 CSR 时为 1；由源寄存器**编号**或 zimm 是否为零决定，不能只看源数据值。 |
| `csr_wdata` | 输入，32 | CPU 已算好的完整写入候选值；本模块再施加各 CSR 的写掩码和固定值约束。 |
| `csr_commit` | 输入，1 | 合法 CSR 指令在 WB 的一次性提交脉冲；只有它与写意图同为 1 且访问合法，CSR 才会写入。 |
| `csr_rdata` | 输出，32 | 组合读出的 CSR 旧值；供后续 WB 写回 rd、计算 CSRRS/CSRRC 候选值。 |
| `csr_exists` | 输出，1 | `csr_addr` 属于已实现地址白名单时为 1，与是否发起读写请求无关。 |
| `csr_readonly_addr` | 输出，1 | 地址属于五个只读机器信息 CSR 时为 1；`mip` 含只读字段，但该信号对整个 `mip` 地址为 0。 |
| `csr_access_illegal` | 输出，1 | 有读/写请求，且地址不存在或试图写只读地址时为 1；CPU 后续将其转成非法指令异常。 |
| `trap_enter` | 输入，1 | 一次性 trap 提交脉冲；本沿写 `mepc/mcause/mtval` 并更新 `mstatus`。 |
| `trap_pc` | 输入，32 | 同步异常指令 PC，或中断排空后的架构续执行 PC；保存到 `mepc` 时低两位清零。 |
| `trap_is_interrupt`、`trap_cause`、`trap_tval` | 输入，1/5/32 | 构成 `mcause[31]`、低五位原因码及故障附加信息。 |
| `mret_commit` | 输入，1 | 一次性 MRET 提交脉冲；本沿从 MPIE 恢复 MIE，置 MPIE=1。 |
| `irq_external`、`irq_timer`、`irq_software` | 输入，各 1 | 已同步的电平输入，分别映射 `mip` 位 11、7、3；输入撤销后对应 pending 立即撤销。 |
| `trap_target`、`mret_target` | 输出，各 32 | 当前 `mtvec` Direct 基址和 `mepc`；供 CPU 修改 PC，本模块自身不修改 PC。 |
| `irq_pending`、`irq_enable`、`irq_global_enable` | 输出，32/32/1 | 分别为原始 `mip` 视图、`mie` 和 `mstatus.MIE`；后续中断仲裁器组合判断是否响应。 |

`csr_commit`、`trap_enter`、`mret_commit` 应由 CPU 保证互斥且各只脉冲一拍；若误同时拉高，模块按复位 > trap > MRET > CSR 写执行。`csr_access_illegal` 只是检查结果，当前独立模块不会自行生成 cause 2 或阻止 CPU 的 GPR 写回。

## 状态规则

`mstatus` 仅保留 MIE、MPIE 和固定的 MPP=3；`mie` 仅保留 11/7/3 位；`mtvec` 仅 Direct 且 4 字节对齐；`mepc` 低两位为 0。`mscratch`、`mtval` 为 32 位读写。`mcause` 保留中断位与低五位原因码，其余位读零。`misa` 固定 `0x40000100`；`mstatush` 和五个机器信息 CSR 固定零。新增的 `mconfigptr` 位于 `0xF15`，只读零表示未提供配置数据结构。`mip` 由输入电平形成，无软件存储位。未列出的 CSR 地址不存在。

trap 同时写入对齐后的 `mepc`、`mcause`、`mtval`，把进入前 MIE 复制到 MPIE，然后清 MIE。MRET 从 MPIE 恢复 MIE，置 MPIE=1，MPP 保持 3。所有状态由一个时序块驱动，后续流水线必须保证事件各发生一次。

## 验证

独立测试台：`tb_csr_file.v`（仅本地：`/D:/riscv/RISCV/difftest/tb/tb_csr_file.v`）。编译运行命令：

```powershell
& 'D:\iverilog\bin\iverilog.exe' -g2012 -Wall -I 'myriscv' -s tb_csr_file -o 'difftest\build\tb_csr_file_step2.vvp' 'myriscv\csr_file.v' 'difftest\tb\tb_csr_file.v'
& 'D:\iverilog\bin\vvp.exe' 'difftest\build\tb_csr_file_step2.vvp'
```

测试覆盖复位值、软件写掩码、mepc/mtvec 对齐、固定值 CSR、无效 CSR/只读地址、`mconfigptr` 的合法读和非法写、mip 电平变化，以及 trap/MRET 对 `mstatus` 与原因寄存器的更新。结果：`RESULT: PASS csr_file reset, WARL, legality, IRQ view, trap and MRET`。
