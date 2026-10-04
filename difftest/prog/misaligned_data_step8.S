# 第 8 步：11 次半字/字非对齐异常，随后执行合法字节与对齐访存。
# handler 记录 mcause/mepc/mtval 并跳过故障指令。
.org 0
    addi sp, x0, 0x3f0
    addi x20, x0, 0x200
    addi x8, x0, 0x180
    csrw mtvec, x8
    addi x1, x0, 0x300
    addi x16, x0, 0x7b
    sw x16, 0(x1)         # 目标字哨兵
    sw x16, 4(x1)         # 相邻字哨兵
    addi x3, x0, 0x33
    addi x4, x0, 0x44
    addi x5, x0, 0x55
    addi x6, x0, 0x56
    addi x7, x0, 0x57

bad_lh:  lh  x3, 1(x1)
bad_lhu: lhu x4, 3(x1)
bad_lw1: lw  x5, 1(x1)
bad_lw2: lw  x6, 2(x1)
bad_lw3: lw  x7, 3(x1)
bad_sh1: sh  x16, 1(x1)
bad_sh3: sh  x16, 3(x1)
bad_sw1: sw  x16, 1(x1)
bad_sw2: sw  x16, 2(x1)
bad_sw3: sw  x16, 3(x1)

    addi x15, x0, 0x5f
    lui x17, 0x1
    addi x17, x17, 0x300
bad_lh_high: lh x15, 1(x17) # mtval 必须保存 0x1301，不能被 BRAM 地址截断

    lh  x8, 0(x1)
    lhu x9, 0(x1)
    lw  x10, 4(x1)
    sb  x16, 7(x1)       # 字节访问不要求对齐
    lb  x11, 7(x1)
    lbu x12, 7(x1)
    sh  x16, 2(x1)       # 合法半字写
    lh  x13, 2(x1)
    sw  x16, 8(x1)       # 合法字写
    lw  x14, 8(x1)
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
