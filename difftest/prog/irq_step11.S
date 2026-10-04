# 三源机器中断：优先级、MRET 重判、老异常优先、store 排空和撤销。
.org 0
    addi x1, x0, 0x300        # 数据 RAM 起点
    addi x2, x0, 0x100        # handler
    csrw mtvec, x2
    csrr x9, mip             # 全局/局部使能关闭时，仍应看到原始 0x888
    addi x3, x0, 0x888
    csrw mie, x3
    addi x4, x0, 8
    csrw mstatus, x4         # 三源从此都可响应；下一架构 PC = 0x20
    addi x5, x0, 0x55
bad_load:
    lw x10, 1(x1)           # cause 4；测试台在 EX 同拍拉高软件中断
loop:
    sw x5, 0(x1)
    lw x6, 0(x1)
    addi x7, x6, 1
    sw x7, 4(x1)
    addi x8, x8, 1
    jal x0, loop
    sw x0, 8(x1)             # JAL 的错误路径：不得产生 RAM 写请求

.org 0x100
handler:
    csrr x20, mcause
    csrr x21, mepc
    csrr x22, mtval
    addi x23, x23, 1
    blt x20, x0, irq_return  # mcause[31]=1 的中断直接返回原 PC
    addi x21, x21, 4         # 同步异常跳过故障指令
    csrw mepc, x21
irq_return:
    mret
