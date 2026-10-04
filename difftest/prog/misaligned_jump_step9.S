# 第 9 步：被采用目标非对齐、未采用分支、JALR bit0、load-use 与老故障优先级。
# handler 记录 mcause/mepc/mtval，并将 mepc 加 4 后返回。
.org 0
    addi sp, x0, 0x3f0
    addi x20, x0, 0x200
    addi x8, x0, 0x180
    csrw mtvec, x8
    addi x1, x0, 0x300
    addi x16, x0, 0x202
    sw x16, 4(x1)               # JALR 目标放在普通 RAM
    addi x5, x0, 0x55           # 错误 JAL 的链接目标哨兵
    addi x9, x0, 0x77           # 错误 JALR 的链接目标哨兵
    addi x12, x0, 0x12          # 后面故障 load 的目的寄存器哨兵

not_taken:
    bne x0, x0, not_taken+2   # 目标虽非对齐，但分支不采用
bad_branch:
    beq x0, x0, bad_branch+2  # cause 0，mtval=自身 PC+2
bad_jal:
    jal x5, bad_jal+2         # cause 0，不写链接寄存器 x5

    addi x7, x0, 1
    sw x0, 0(x1)
    lw x7, 0(x1)
load_branch:
    beq x7, x0, load_branch+2 # 必须等待 load-use，再判采用与对齐

    lw x8, 4(x1)
bad_jalr:
    jalr x9, x8, 0            # x8=0x202；bit0 清后仍非对齐

    addi x10, x0, after_jalr+1
    jalr x11, x10, 0          # bit0 清除后对齐，合法跳到 after_jalr
    .word 0x00000000         # 被上述 JALR 取消的错误路径
after_jalr:
    lw x12, 1(x1)             # 老 EX 数据非对齐 cause 4
old_fault_branch:
    beq x0, x0, old_fault_branch+2 # 年轻 ID 故障不得越过老 EX 故障
after_old:
    beq x0, x0, after_branch
    .word 0x00000000         # 普通采用分支取消错误路径上的非法指令
after_branch:
    addi x13, x0, 1
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
