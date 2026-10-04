# 异常与中断：第 7 步非法指令与非法 CSR

本步在 [`mycpu_sync.v`](/D:/riscv/RISCV/myriscv/mycpu_sync.v) 中把不支持的指令编码和非法 CSR 访问接入第 5、6 步的同步 trap 通路。异常原因均为 **cause 2**；`mepc` 保存故障指令自身 PC，`mtval` 保存完整的 32 位故障指令编码。故障项不正常退休，不写 GPR 或 CSR。

## 检测和提交位置

| 来源 | 检测点 | 处理 |
|---|---|---|
| 不支持的 opcode、funct3/funct7 或指令长度 | ID 的 `id_inst_supported` 白名单 | `id_illegal_inst=1`，生成 `id_exc_valid`、cause 2、`id_exc_tval=inst`；异常项与 PC/指令字逐级传到 WB。 |
| 不存在的 CSR 地址 | WB 的 `csr_file.csr_access_illegal` | `wb_csr_illegal=1`，在 WB 与流水异常项共用 `sync_trap_event`；cause 2，`tval=mem_wb_inst`。 |
| 写只读 CSR 地址 | WB，同上 | 写意图按 `rs1` **编号**或 `zimm` 判断，不能按源数据是否为零判断；故障指令的 `rd` 保持原值。 |

ID 白名单只包含当前实现的 RV32I 整数指令、六条 CSR、精确编码的 ECALL/EBREAK/MRET/WFI，以及 `funct3=000` 的 FENCE。R 型与移位立即数要求正确的 `funct7`；load/store、branch、JALR 要求已实现的 `funct3`。这些合法 opcode 的低两位都是 `11`，因此零指令和无 C 扩展时的压缩指令编码都会进入 cause 2。IF/ID 气泡即使含有零编码也因 `if_id_valid=0` 而不会 `id_fire` 或形成异常项。

非法 CSR 地址直到 WB 才能由 `csr_file` 判断。CSR 指令此前已串行排空并保持年轻指令，因此 WB 检查失败时仍可精确 trap。`wb_trap_cause/tval` 在已有流水异常与非法 CSR 之间选择，`csr_file.trap_enter` 与 PC 重定向由同一个 `sync_trap_event` 驱动。`csr_commit`、GPR 写口和 WB 前递均受非法访问门控。若指令本身已有异常记录，该记录优先，不能被 CSR 检查覆盖。

## FENCE、FENCE.I 和 WFI

- FENCE 在首版作为串行内存屏障：等待老指令完成，自己不访问 GPR、不写寄存器或 RAM，年轻指令在它完成后才继续。指令中的保留 `rd/rs1` 字段不作为 GPR 操作数。当前尚无总线或 Cache，因此后续接入这些部件时还需复核外部请求完成顺序。
- FENCE.I（`funct3=001`）未实现，进入 cause 2；本核目前不宣称支持 Zifencei。
- 精确编码的 WFI `0x10500073` 在首版作为**合法的串行 NOP**：经过串行排空和预留的中断重评估周期，但不等待中断输入。其他不支持的 SYSTEM 编码进入 cause 2。

## 验证

[illegal_step7.S](/D:/riscv/RISCV/difftest/prog/illegal_step7.S) 包含八个故障样例：零编码、非零压缩编码、未实现的 MUL、错误移位 `funct7`、FENCE.I、错误 FENCE `funct3`、对只读 `mconfigptr` 的写访问，以及不存在的 `0x306` CSR。对于只读写访问，`rs1=x9` 的编号非零而寄存器值为零。handler 将每次的 `mcause/mepc/mtval` 写入 RAM，给 `mepc` 加 4 后 MRET；[tb_illegal_step7.v](/D:/riscv/RISCV/difftest/tb/tb_illegal_step7.v) 逐项比对日志和最终 GPR/CSR 状态。

测试还包含合法读取 `mconfigptr`、合法读取 `mscratch`、带非零 `rd/rs1` 字段的 FENCE 和 WFI。它检查非法 CSR 不会清零预置的 `x10/x11`，FENCE 不改 `x8`，WFI 后续指令能执行，trap 总数恰好为八次。结果：`RESULT: PASS illegal instruction/CSR trap, mtval, FENCE and WFI`。

生成 ROM 并运行测试：

```powershell
python difftest\build_trap_rom.py difftest\prog\illegal_step7.S difftest\build\illegal_step7
& D:\iverilog\bin\iverilog.exe -g2012 -I myriscv -s tb_illegal_step7 -o difftest\build\illegal_step7\tb.vvp myriscv\mycpu_sync.v myriscv\regfile.v myriscv\alu.v myriscv\l_alu.v myriscv\br_alu.v myriscv\csr_file.v difftest\model\inst_rom.v difftest\model\data_ram.v difftest\tb\tb_illegal_step7.v
Push-Location difftest\build\illegal_step7
try { & D:\iverilog\bin\vvp.exe tb.vvp } finally { Pop-Location }
```

此外，三组既有普通程序差分测试、合法 CSR 指令测试、流水控制测试、冒险测试、异常注入测试和 ECALL/EBREAK/MRET 闭环测试均通过。后续第 8、9 步分别接入数据地址非对齐和跳转目标非对齐异常。真实 FPGA 综合与 IP 时序仿真未在本步执行。
