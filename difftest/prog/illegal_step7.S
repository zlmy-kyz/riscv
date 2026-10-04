# 第 7 步：非法指令、非法 CSR、合法 FENCE/WFI。
# handler 以 3 个字/次记录 mcause、mepc、mtval，并跳过故障字。
.org 0
    addi sp, x0, 0x3f0
    addi x20, x0, 0x200
    addi x8, x0, 0x180
    csrw mtvec, x8
    addi x1, x0, 0x55
    csrw mscratch, x1
    addi x3, x0, 0x44
    addi x4, x0, 0x77
    addi x10, x0, 0x123
    addi x11, x0, 0x234
    addi x9, x0, 0       # x9 编号非零，内容为零

bad_length:
    .word 0x00000000    # 不支持的 16 位/零编码
bad_compressed:
    .word 0x00000001    # C.NOP 的 16 位编码；本核无 C 扩展
bad_r_funct7:
    .word 0x020001b3    # MUL x3,x0,x0；无 M 扩展
bad_shift_funct7:
    .word 0x02101213    # SLLI x4,x0,1，funct7 非法
bad_fence_i:
    .word 0x0000100f    # FENCE.I 未实现
bad_fence_funct3:
    .word 0x0000200f    # opcode=FENCE，funct3 无效
bad_readonly:
    csrrs x10, mconfigptr, x9  # x9 的值虽为 0，编号非零仍是非法写
bad_missing:
    csrr x11, 0x306           # 未实现 CSR 地址

    csrr x12, mconfigptr      # 只读 CSR 合法读取零
    .word 0x0002840f         # FENCE：保留的 rd=x8、rs1=x5 不读写 GPR
    .word 0x10500073         # WFI：首版串行 NOP
    csrr x13, mscratch       # 前面的非法指令未破坏 CSR
    addi x14, x0, 1
halt: jal x0, halt

.org 0x180
handler:
    addi sp, sp, -8
    sw x5, 0(sp)
    sw x6, 4(sp)
    csrr x5, mcause
    sw x5, 0(x20)
    csrr x6, mepc
    sw x6, 4(x20)
    csrr x5, mtval
    sw x5, 8(x20)
    addi x20, x20, 12
    addi x6, x6, 4
    csrw mepc, x6
    lw x6, 4(sp)
    lw x5, 0(sp)
    addi sp, sp, 8
    mret
