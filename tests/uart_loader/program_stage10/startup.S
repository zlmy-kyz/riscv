    .section .text.startup,"ax",@progbits
    .globl _start
    .type _start,@function
_start:
    .word 0x30047073 # CSRRCI x0,mstatus,8; CPU machine CSR, no Zicsr tool flag
    .word 0x30401073 # CSRRW x0,mie,x0
    .option push
    .option norelax
    la gp,__global_pointer$
    .option pop
    la sp,__stack_top
    la t0,__bss_start
    la t1,__bss_end
1:
    bgeu t0,t1,2f
    sw zero,0(t0)
    addi t0,t0,4
    j 1b
2:
    call main
3:
    j 3b
    .size _start,.-_start
