    /* GCC 15 separates Zicsr from RV32I; these explicit CSR instructions
       are already implemented in this CPU. C/libgcc remain -march=rv32i. */
    .option push
    .option arch, +zicsr
    .section .text.startup, "ax", @progbits
    .globl _start
_start:
    .option push
    .option norelax
    la gp, __global_pointer$
    .option pop
    la sp, __stack_top
    .globl loader_stack_ready
loader_stack_ready:
    csrw mie, zero
    csrci mstatus, 8
    la t0, loader_trap
    csrw mtvec, t0
    la t0, __bss_start
    la t1, __bss_end
1:  bgeu t0, t1, 2f
    sw zero, 0(t0)
    addi t0, t0, 4
    j 1b
2:  call main
3:  j 3b

    .section .text.trap, "ax", @progbits
    .balign 4
    .globl loader_trap
loader_trap:
    /* No C call or stack dependency in the fatal trap path. */
    csrr t1, mcause
    la t0, loader_trap_cause
    sw t1, 0(t0)
    csrr t1, mepc
    la t0, loader_trap_pc
    sw t1, 0(t0)
    csrr t1, mtval
    la t0, loader_trap_value
    sw t1, 0(t0)
4:  j 4b
    .option pop
