    .section .text.startup,"ax",@progbits
    .globl _start
_start:
    .word 0x30047073
    .word 0x30401073
    .option push
    .option norelax
    la gp,__global_pointer$
    .option pop
    la sp,__stack_top
    # UART Loader already loads .data at its VMA. Copy only for differing LMA.
    la t0,__data_load_start
    la t1,__data_start
    la t2,__data_end
    beq t0,t1,2f
1:  bgeu t1,t2,2f
    lw t3,0(t0)
    sw t3,0(t1)
    addi t0,t0,4
    addi t1,t1,4
    j 1b
2:  la t0,__bss_start
    la t1,__bss_end
3:  bgeu t0,t1,4f
    sw zero,0(t0)
    addi t0,t0,4
    j 3b
4:  la t0,trap_entry
    .word 0x30529073 # csrw mtvec,t0
    call main
    .globl program_return
program_return:
5:  j 5b
