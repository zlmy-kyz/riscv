# 第 6 步：纯汇编 trap/MRET 闭环。x20 是测试专用日志指针。
# sp=0x3f0、handler=0x180、日志=0x200、哨兵=0x2f0，均位于当前 4KB 存储器。
.org 0
    addi sp, x0, 0x3f0
    addi x20, x0, 0x200
    addi x8, x0, 0x180
    csrw mtvec, x8
    addi x7, x0, 8
    csrrs x0, mstatus, x7  # 进入异常前设置 MIE=1
    addi x5, x0, 33
    addi x6, x0, 44
    addi x1, x0, 85
    ecall                    # PC=0x24 / 36，cause=11
    sw x1, 0x2f0(x0)        # 必须等 MRET 后才能执行
    ebreak                   # PC=0x2c / 44，cause=3
    addi x9, x0, 1
    csrr x10, mstatus
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
    csrr x5, mstatus
    sw x5, 8(x20)
    addi x20, x20, 12
    addi x6, x6, 4
    csrw mepc, x6
    lw x6, 4(sp)
    lw x5, 0(sp)
    addi sp, sp, 8
    mret
