.option norvc
.option norelax
.section .text
.globl _start
_start:
li t0, 0
li t1, 0x40000000
li t2, 0x3ff0
lw t3, 0(t2)
1: lw t4, 0(t0)
sw t4, 0(t1)
addi t0, t0, 4
addi t1, t1, 4
addi t3, t3, -1
bne t3, zero, 1b
fence rw, rw
li t1, 0x40000000
jalr zero, 0(t1)
