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
    la t0,trap_entry
    .word 0x30529073
    la t0,__bss_start
    la t1,__bss_end
1:  bgeu t0,t1,2f
    sw zero,0(t0)
    addi t0,t0,4
    j 1b
2:  call main
3:  j 3b
    .section .text.trap,"ax",@progbits
    .balign 4
trap_entry:
    .word 0x34202573
    .word 0x341025f3
    .word 0x34302673
    la sp,__stack_top
    tail camera_trap

