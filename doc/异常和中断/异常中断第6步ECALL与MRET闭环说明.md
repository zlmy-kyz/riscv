# 异常与中断：第 6 步 ECALL、EBREAK、trap 和 MRET 闭环

本步把 ECALL、EBREAK 和 MRET 接入 [`mycpu_sync.v`](/D:/riscv/RISCV/myriscv/mycpu_sync.v) 的第 3～5 步流水控制，并使 WB 的 trap/MRET 事件驱动 [`csr_file.v`](/D:/riscv/RISCV/myriscv/csr_file.v)。首版仍为单核 M 模式、无 C 扩展、`mtvec` Direct 模式。

## 硬件时序

| 指令或事件 | ID | WB 上升沿 |
|---|---|---|
| ECALL `0x00000073` | 精确匹配 32 位编码，形成 `exc_valid=1`、cause 11、`tval=0`，以串行项等待老指令排空。 | `sync_trap_event` 同拍驱动 `csr_file.trap_enter` 和 PC 重定向；`mepc=ECALL 自身 PC`、`mcause=11`、`mtval=0`；旧 MIE 进入 MPIE，MIE 清零。故障项不正常退休或写回。 |
| EBREAK `0x00100073` | 同上，cause 3。 | 同上，`mepc=EBREAK 自身 PC`、`mcause=3`。 |
| MRET `0x30200073` | 精确匹配完整编码，串行执行，不读写 GPR。 | `mret_commit` 同拍驱动 `csr_file.mret_commit` 和 PC 重定向；使用当前 `mepc` 作为返回地址，MPIE 恢复到 MIE，MPIE 置 1。返回目标第一条重新取指。 |

新增加的 `id_ex_mret`、`ex_mem_mret`、`mem_wb_mret` 随有效指令传递，气泡、复位或 kill 清零。`mret_commit` 只在 WB 有效且无异常时成立。异常与 MRET 共用原有重定向优先级：trap > MRET > 普通分支。CSR 写 `mepc` 在自身 WB 提交完成后，MRET 才能经串行排空发射，因此 MRET 读取的是更新后的 `mepc`。MRET 重定向后保留 `FLOW_IRQ_CHECK` 控制周期，供后续中断仲裁使用。

第 6 步的 `csr_file` trap 输入来自 `mem_wb_pc`、`mem_wb_exc_cause`、`mem_wb_exc_tval`；`trap_is_interrupt=0`。进入 trap 时，`mstatus.MIE→MPIE` 并清 MIE，MPP 固定为 M；MRET 时 `MPIE→MIE` 且置 MPIE。`mepc` 与 `mtvec` 仍按无 C 扩展强制 4 字节对齐。后续第 7、8、9 步分别接入非法指令/CSR、数据地址非对齐和跳转目标非对齐检测；中断检测仍待后续步骤。

## 最小汇编处理程序

[trap_mret_step6.S](/D:/riscv/RISCV/difftest/prog/trap_mret_step6.S) 在启动时设置 `sp=0x3f0`、日志指针 `x20=0x200`、`mtvec=0x180`，全部处于当前 4KB ROM/RAM 范围。处理程序位于 ROM `0x180`：先把使用的 `x5/x6` 压栈，随后将 `mcause/mepc/mstatus` 记录到 RAM；把 `mepc` 加 4 后写回，恢复寄存器和栈指针，最后执行 MRET。`x20` 专用于跨两次 trap 的测试日志指针，每次推进 12 字节。

测试程序依次执行 ECALL 和 EBREAK。第一次 ECALL 位于 PC `0x24`，第二次 EBREAK 位于 PC `0x2c`。handler 分别将 `mepc` 改为 `0x28` 与 `0x30`，所以 MRET 返回到故障指令下一条。ECALL 紧接着的 store 指向 RAM `0x2f0`：测试先确认 trap 发生时该哨兵仍为零，然后确认第一次 MRET 返回后它才执行一次。handler 在两次 trap 中记录的 `mstatus` 均为 `0x1880`（MIE=0、MPIE=1）；两次 MRET 后恢复为 `0x1888`。栈内保存的值和最终 `x5/x6/sp` 也会检查。

当前环境未找到 RISC-V GNU 工具链。测试使用 [`build_trap_rom.py`](/D:/riscv/RISCV/difftest/build_trap_rom.py) 调用工程已有 RV32I 汇编器，并只为本测试补充 CSR、ECALL、EBREAK、MRET 助记符编码，生成 `rom.hex`、`ram.hex` 与 `prog.lst`。它只负责汇编；黄金 ISS 尚不支持 trap，因此结果由独立测试台直接检查。生成及运行步骤：

```powershell
python difftest\build_trap_rom.py difftest\prog\trap_mret_step6.S difftest\build\trap_mret_step6
& D:\iverilog\bin\iverilog.exe -g2012 -I myriscv -s tb_trap_mret -o difftest\build\trap_mret_step6\tb.vvp myriscv\mycpu_sync.v myriscv\regfile.v myriscv\alu.v myriscv\l_alu.v myriscv\br_alu.v myriscv\csr_file.v difftest\model\inst_rom.v difftest\model\data_ram.v difftest\tb\tb_trap_mret.v
Push-Location difftest\build\trap_mret_step6
try { & D:\iverilog\bin\vvp.exe tb.vvp } finally { Pop-Location }
```

结果：`RESULT: PASS ECALL, EBREAK, trap CSR, handler, MRET and younger-store ordering`。三组既有普通程序差分测试、CSR 指令测试、流水控制测试、冒险测试和异常注入测试均通过。真实 FPGA 工程的综合、时序和 IP 仿真仍需单独验证。
