.option norvc
.option norelax
.section .text
.globl _start
_start:
addi x1, x0, 0
addi x2, x0, 0
addi x3, x0, 0
addi x4, x0, 0
addi x5, x0, 0
addi x6, x0, 0
addi x7, x0, 0
addi x8, x0, 0
addi x9, x0, 0
addi x10, x0, 0
addi x11, x0, 0
addi x12, x0, 0
addi x13, x0, 0
addi x14, x0, 0
addi x15, x0, 0
addi x16, x0, 0
addi x17, x0, 0
addi x18, x0, 0
addi x19, x0, 0
addi x20, x0, 0
addi x21, x0, 0
addi x22, x0, 0
addi x23, x0, 0
addi x24, x0, 0
addi x25, x0, 0
addi x26, x0, 0
addi x27, x0, 0
addi x28, x0, 0
addi x29, x0, 0
addi x30, x0, 0
addi x31, x0, 0
li sp, 0x40010000
li s11, 0x10000008
li s8, 0x10000000
li t0, 1
sw t0, 16(s8)
li a0, 0
li s7, 1
.globl start_sequential_alu
start_sequential_alu:
lw s10, 0(s11)
.globl body_sequential_alu
body_sequential_alu:
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
addi a0, a0, 1
.globl stop_sequential_alu
stop_sequential_alu:
lw s9, 0(s11)
li t6, 128
bne a0, t6, fail
sw a0, 0(s8)
li a0, 0
li t0, 32
li s7, 2
.globl start_small_loop
start_small_loop:
lw s10, 0(s11)
.globl body_small_loop
body_small_loop:
1: addi a0, a0, 2
addi t0, t0, -1
bne t0, zero, 1b
.globl stop_small_loop
stop_small_loop:
lw s9, 0(s11)
li t6, 64
bne a0, t6, fail
sw a0, 0(s8)
li a0, 0
li s7, 3
.globl start_not_taken
start_not_taken:
lw s10, 0(s11)
.globl body_not_taken
body_not_taken:
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
beq zero, s11, fail
addi a0, a0, 1
.globl stop_not_taken
stop_not_taken:
lw s9, 0(s11)
li t6, 32
bne a0, t6, fail
sw a0, 0(s8)
li a0, 0
li s7, 4
.globl start_random_fetch
start_random_fetch:
lw s10, 0(s11)
.globl body_random_fetch
body_random_fetch:
j block_19
.balign 16
block_0:
addi a0, a0, 1
j block_25
.balign 16
block_1:
addi a0, a0, 1
j block_8
.balign 16
block_2:
addi a0, a0, 1
j block_13
.balign 16
block_3:
addi a0, a0, 1
j block_18
.balign 16
block_4:
addi a0, a0, 1
j block_16
.balign 16
block_5:
addi a0, a0, 1
j block_12
.balign 16
block_6:
addi a0, a0, 1
j block_24
.balign 16
block_7:
addi a0, a0, 1
j block_5
.balign 16
block_8:
addi a0, a0, 1
j block_10
.balign 16
block_9:
addi a0, a0, 1
j block_27
.balign 16
block_10:
addi a0, a0, 1
j block_15
.balign 16
block_11:
addi a0, a0, 1
j block_31
.balign 16
block_12:
addi a0, a0, 1
j block_2
.balign 16
block_13:
addi a0, a0, 1
j block_3
.balign 16
block_14:
addi a0, a0, 1
j block_17
.balign 16
block_15:
addi a0, a0, 1
j block_11
.balign 16
block_16:
addi a0, a0, 1
j block_6
.balign 16
block_17:
addi a0, a0, 1
j block_7
.balign 16
block_18:
addi a0, a0, 1
j block_21
.balign 16
block_19:
addi a0, a0, 1
j block_9
.balign 16
block_20:
addi a0, a0, 1
j block_22
.balign 16
block_21:
addi a0, a0, 1
j block_23
.balign 16
block_22:
addi a0, a0, 1
j block_14
.balign 16
block_23:
addi a0, a0, 1
j block_4
.balign 16
block_24:
addi a0, a0, 1
j block_0
.balign 16
block_25:
addi a0, a0, 1
j block_29
.balign 16
block_26:
addi a0, a0, 1
j block_1
.balign 16
block_27:
addi a0, a0, 1
j block_28
.balign 16
block_28:
addi a0, a0, 1
j block_20
.balign 16
block_29:
addi a0, a0, 1
j block_30
.balign 16
block_30:
addi a0, a0, 1
j block_26
.balign 16
block_31:
addi a0, a0, 1
j block_done
block_done:
.globl stop_random_fetch
stop_random_fetch:
lw s9, 0(s11)
li t6, 32
bne a0, t6, fail
sw a0, 0(s8)
la s0, values
li a0, 0
li s7, 5
.globl start_sequential_load
start_sequential_load:
lw s10, 0(s11)
.globl body_sequential_load
body_sequential_load:
lw t0, 0(s0)
add a0, a0, t0
lw t0, 4(s0)
add a0, a0, t0
lw t0, 8(s0)
add a0, a0, t0
lw t0, 12(s0)
add a0, a0, t0
lw t0, 16(s0)
add a0, a0, t0
lw t0, 20(s0)
add a0, a0, t0
lw t0, 24(s0)
add a0, a0, t0
lw t0, 28(s0)
add a0, a0, t0
lw t0, 32(s0)
add a0, a0, t0
lw t0, 36(s0)
add a0, a0, t0
lw t0, 40(s0)
add a0, a0, t0
lw t0, 44(s0)
add a0, a0, t0
lw t0, 48(s0)
add a0, a0, t0
lw t0, 52(s0)
add a0, a0, t0
lw t0, 56(s0)
add a0, a0, t0
lw t0, 60(s0)
add a0, a0, t0
lw t0, 64(s0)
add a0, a0, t0
lw t0, 68(s0)
add a0, a0, t0
lw t0, 72(s0)
add a0, a0, t0
lw t0, 76(s0)
add a0, a0, t0
lw t0, 80(s0)
add a0, a0, t0
lw t0, 84(s0)
add a0, a0, t0
lw t0, 88(s0)
add a0, a0, t0
lw t0, 92(s0)
add a0, a0, t0
lw t0, 96(s0)
add a0, a0, t0
lw t0, 100(s0)
add a0, a0, t0
lw t0, 104(s0)
add a0, a0, t0
lw t0, 108(s0)
add a0, a0, t0
lw t0, 112(s0)
add a0, a0, t0
lw t0, 116(s0)
add a0, a0, t0
lw t0, 120(s0)
add a0, a0, t0
lw t0, 124(s0)
add a0, a0, t0
lw t0, 128(s0)
add a0, a0, t0
lw t0, 132(s0)
add a0, a0, t0
lw t0, 136(s0)
add a0, a0, t0
lw t0, 140(s0)
add a0, a0, t0
lw t0, 144(s0)
add a0, a0, t0
lw t0, 148(s0)
add a0, a0, t0
lw t0, 152(s0)
add a0, a0, t0
lw t0, 156(s0)
add a0, a0, t0
lw t0, 160(s0)
add a0, a0, t0
lw t0, 164(s0)
add a0, a0, t0
lw t0, 168(s0)
add a0, a0, t0
lw t0, 172(s0)
add a0, a0, t0
lw t0, 176(s0)
add a0, a0, t0
lw t0, 180(s0)
add a0, a0, t0
lw t0, 184(s0)
add a0, a0, t0
lw t0, 188(s0)
add a0, a0, t0
lw t0, 192(s0)
add a0, a0, t0
lw t0, 196(s0)
add a0, a0, t0
lw t0, 200(s0)
add a0, a0, t0
lw t0, 204(s0)
add a0, a0, t0
lw t0, 208(s0)
add a0, a0, t0
lw t0, 212(s0)
add a0, a0, t0
lw t0, 216(s0)
add a0, a0, t0
lw t0, 220(s0)
add a0, a0, t0
lw t0, 224(s0)
add a0, a0, t0
lw t0, 228(s0)
add a0, a0, t0
lw t0, 232(s0)
add a0, a0, t0
lw t0, 236(s0)
add a0, a0, t0
lw t0, 240(s0)
add a0, a0, t0
lw t0, 244(s0)
add a0, a0, t0
lw t0, 248(s0)
add a0, a0, t0
lw t0, 252(s0)
add a0, a0, t0
.globl stop_sequential_load
stop_sequential_load:
lw s9, 0(s11)
li t6, 2016
bne a0, t6, fail
sw a0, 0(s8)
la s0, values
li a0, 0
li s7, 6
.globl start_random_load
start_random_load:
lw s10, 0(s11)
.globl body_random_load
body_random_load:
lw t0, 200(s0)
add a0, a0, t0
lw t0, 180(s0)
add a0, a0, t0
lw t0, 252(s0)
add a0, a0, t0
lw t0, 196(s0)
add a0, a0, t0
lw t0, 136(s0)
add a0, a0, t0
lw t0, 132(s0)
add a0, a0, t0
lw t0, 28(s0)
add a0, a0, t0
lw t0, 164(s0)
add a0, a0, t0
lw t0, 172(s0)
add a0, a0, t0
lw t0, 232(s0)
add a0, a0, t0
lw t0, 240(s0)
add a0, a0, t0
lw t0, 124(s0)
add a0, a0, t0
lw t0, 188(s0)
add a0, a0, t0
lw t0, 60(s0)
add a0, a0, t0
lw t0, 120(s0)
add a0, a0, t0
lw t0, 52(s0)
add a0, a0, t0
lw t0, 92(s0)
add a0, a0, t0
lw t0, 140(s0)
add a0, a0, t0
lw t0, 68(s0)
add a0, a0, t0
lw t0, 96(s0)
add a0, a0, t0
lw t0, 16(s0)
add a0, a0, t0
lw t0, 104(s0)
add a0, a0, t0
lw t0, 248(s0)
add a0, a0, t0
lw t0, 4(s0)
add a0, a0, t0
lw t0, 220(s0)
add a0, a0, t0
lw t0, 36(s0)
add a0, a0, t0
lw t0, 148(s0)
add a0, a0, t0
lw t0, 108(s0)
add a0, a0, t0
lw t0, 156(s0)
add a0, a0, t0
lw t0, 32(s0)
add a0, a0, t0
lw t0, 236(s0)
add a0, a0, t0
lw t0, 12(s0)
add a0, a0, t0
lw t0, 20(s0)
add a0, a0, t0
lw t0, 24(s0)
add a0, a0, t0
lw t0, 76(s0)
add a0, a0, t0
lw t0, 244(s0)
add a0, a0, t0
lw t0, 208(s0)
add a0, a0, t0
lw t0, 48(s0)
add a0, a0, t0
lw t0, 192(s0)
add a0, a0, t0
lw t0, 152(s0)
add a0, a0, t0
lw t0, 112(s0)
add a0, a0, t0
lw t0, 228(s0)
add a0, a0, t0
lw t0, 72(s0)
add a0, a0, t0
lw t0, 128(s0)
add a0, a0, t0
lw t0, 144(s0)
add a0, a0, t0
lw t0, 0(s0)
add a0, a0, t0
lw t0, 116(s0)
add a0, a0, t0
lw t0, 216(s0)
add a0, a0, t0
lw t0, 40(s0)
add a0, a0, t0
lw t0, 44(s0)
add a0, a0, t0
lw t0, 160(s0)
add a0, a0, t0
lw t0, 224(s0)
add a0, a0, t0
lw t0, 88(s0)
add a0, a0, t0
lw t0, 80(s0)
add a0, a0, t0
lw t0, 100(s0)
add a0, a0, t0
lw t0, 84(s0)
add a0, a0, t0
lw t0, 64(s0)
add a0, a0, t0
lw t0, 212(s0)
add a0, a0, t0
lw t0, 184(s0)
add a0, a0, t0
lw t0, 8(s0)
add a0, a0, t0
lw t0, 204(s0)
add a0, a0, t0
lw t0, 168(s0)
add a0, a0, t0
lw t0, 56(s0)
add a0, a0, t0
lw t0, 176(s0)
add a0, a0, t0
.globl stop_random_load
stop_random_load:
lw s9, 0(s11)
li t6, 2016
bne a0, t6, fail
sw a0, 0(s8)
la s0, node_50
li a0, 0
li s7, 7
.globl start_pointer_chase
start_pointer_chase:
lw s10, 0(s11)
.globl body_pointer_chase
body_pointer_chase:
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
lw t0, 4(s0)
add a0, a0, t0
lw s0, 0(s0)
.globl stop_pointer_chase
stop_pointer_chase:
lw s9, 0(s11)
li t6, 2016
bne a0, t6, fail
sw a0, 0(s8)
la s0, destination
li a0, 0
li s7, 8
.globl start_sequential_store
start_sequential_store:
lw s10, 0(s11)
.globl body_sequential_store
body_sequential_store:
addi a0, a0, 1
sw a0, 0(s0)
addi a0, a0, 1
sw a0, 4(s0)
addi a0, a0, 1
sw a0, 8(s0)
addi a0, a0, 1
sw a0, 12(s0)
addi a0, a0, 1
sw a0, 16(s0)
addi a0, a0, 1
sw a0, 20(s0)
addi a0, a0, 1
sw a0, 24(s0)
addi a0, a0, 1
sw a0, 28(s0)
addi a0, a0, 1
sw a0, 32(s0)
addi a0, a0, 1
sw a0, 36(s0)
addi a0, a0, 1
sw a0, 40(s0)
addi a0, a0, 1
sw a0, 44(s0)
addi a0, a0, 1
sw a0, 48(s0)
addi a0, a0, 1
sw a0, 52(s0)
addi a0, a0, 1
sw a0, 56(s0)
addi a0, a0, 1
sw a0, 60(s0)
addi a0, a0, 1
sw a0, 64(s0)
addi a0, a0, 1
sw a0, 68(s0)
addi a0, a0, 1
sw a0, 72(s0)
addi a0, a0, 1
sw a0, 76(s0)
addi a0, a0, 1
sw a0, 80(s0)
addi a0, a0, 1
sw a0, 84(s0)
addi a0, a0, 1
sw a0, 88(s0)
addi a0, a0, 1
sw a0, 92(s0)
addi a0, a0, 1
sw a0, 96(s0)
addi a0, a0, 1
sw a0, 100(s0)
addi a0, a0, 1
sw a0, 104(s0)
addi a0, a0, 1
sw a0, 108(s0)
addi a0, a0, 1
sw a0, 112(s0)
addi a0, a0, 1
sw a0, 116(s0)
addi a0, a0, 1
sw a0, 120(s0)
addi a0, a0, 1
sw a0, 124(s0)
addi a0, a0, 1
sw a0, 128(s0)
addi a0, a0, 1
sw a0, 132(s0)
addi a0, a0, 1
sw a0, 136(s0)
addi a0, a0, 1
sw a0, 140(s0)
addi a0, a0, 1
sw a0, 144(s0)
addi a0, a0, 1
sw a0, 148(s0)
addi a0, a0, 1
sw a0, 152(s0)
addi a0, a0, 1
sw a0, 156(s0)
addi a0, a0, 1
sw a0, 160(s0)
addi a0, a0, 1
sw a0, 164(s0)
addi a0, a0, 1
sw a0, 168(s0)
addi a0, a0, 1
sw a0, 172(s0)
addi a0, a0, 1
sw a0, 176(s0)
addi a0, a0, 1
sw a0, 180(s0)
addi a0, a0, 1
sw a0, 184(s0)
addi a0, a0, 1
sw a0, 188(s0)
addi a0, a0, 1
sw a0, 192(s0)
addi a0, a0, 1
sw a0, 196(s0)
addi a0, a0, 1
sw a0, 200(s0)
addi a0, a0, 1
sw a0, 204(s0)
addi a0, a0, 1
sw a0, 208(s0)
addi a0, a0, 1
sw a0, 212(s0)
addi a0, a0, 1
sw a0, 216(s0)
addi a0, a0, 1
sw a0, 220(s0)
addi a0, a0, 1
sw a0, 224(s0)
addi a0, a0, 1
sw a0, 228(s0)
addi a0, a0, 1
sw a0, 232(s0)
addi a0, a0, 1
sw a0, 236(s0)
addi a0, a0, 1
sw a0, 240(s0)
addi a0, a0, 1
sw a0, 244(s0)
addi a0, a0, 1
sw a0, 248(s0)
addi a0, a0, 1
sw a0, 252(s0)
.globl stop_sequential_store
stop_sequential_store:
lw s9, 0(s11)
li t6, 64
bne a0, t6, fail
sw a0, 0(s8)
li a0, 0
lw t0, 0(s0)
add a0, a0, t0
lw t0, 4(s0)
add a0, a0, t0
lw t0, 8(s0)
add a0, a0, t0
lw t0, 12(s0)
add a0, a0, t0
lw t0, 16(s0)
add a0, a0, t0
lw t0, 20(s0)
add a0, a0, t0
lw t0, 24(s0)
add a0, a0, t0
lw t0, 28(s0)
add a0, a0, t0
lw t0, 32(s0)
add a0, a0, t0
lw t0, 36(s0)
add a0, a0, t0
lw t0, 40(s0)
add a0, a0, t0
lw t0, 44(s0)
add a0, a0, t0
lw t0, 48(s0)
add a0, a0, t0
lw t0, 52(s0)
add a0, a0, t0
lw t0, 56(s0)
add a0, a0, t0
lw t0, 60(s0)
add a0, a0, t0
lw t0, 64(s0)
add a0, a0, t0
lw t0, 68(s0)
add a0, a0, t0
lw t0, 72(s0)
add a0, a0, t0
lw t0, 76(s0)
add a0, a0, t0
lw t0, 80(s0)
add a0, a0, t0
lw t0, 84(s0)
add a0, a0, t0
lw t0, 88(s0)
add a0, a0, t0
lw t0, 92(s0)
add a0, a0, t0
lw t0, 96(s0)
add a0, a0, t0
lw t0, 100(s0)
add a0, a0, t0
lw t0, 104(s0)
add a0, a0, t0
lw t0, 108(s0)
add a0, a0, t0
lw t0, 112(s0)
add a0, a0, t0
lw t0, 116(s0)
add a0, a0, t0
lw t0, 120(s0)
add a0, a0, t0
lw t0, 124(s0)
add a0, a0, t0
lw t0, 128(s0)
add a0, a0, t0
lw t0, 132(s0)
add a0, a0, t0
lw t0, 136(s0)
add a0, a0, t0
lw t0, 140(s0)
add a0, a0, t0
lw t0, 144(s0)
add a0, a0, t0
lw t0, 148(s0)
add a0, a0, t0
lw t0, 152(s0)
add a0, a0, t0
lw t0, 156(s0)
add a0, a0, t0
lw t0, 160(s0)
add a0, a0, t0
lw t0, 164(s0)
add a0, a0, t0
lw t0, 168(s0)
add a0, a0, t0
lw t0, 172(s0)
add a0, a0, t0
lw t0, 176(s0)
add a0, a0, t0
lw t0, 180(s0)
add a0, a0, t0
lw t0, 184(s0)
add a0, a0, t0
lw t0, 188(s0)
add a0, a0, t0
lw t0, 192(s0)
add a0, a0, t0
lw t0, 196(s0)
add a0, a0, t0
lw t0, 200(s0)
add a0, a0, t0
lw t0, 204(s0)
add a0, a0, t0
lw t0, 208(s0)
add a0, a0, t0
lw t0, 212(s0)
add a0, a0, t0
lw t0, 216(s0)
add a0, a0, t0
lw t0, 220(s0)
add a0, a0, t0
lw t0, 224(s0)
add a0, a0, t0
lw t0, 228(s0)
add a0, a0, t0
lw t0, 232(s0)
add a0, a0, t0
lw t0, 236(s0)
add a0, a0, t0
lw t0, 240(s0)
add a0, a0, t0
lw t0, 244(s0)
add a0, a0, t0
lw t0, 248(s0)
add a0, a0, t0
lw t0, 252(s0)
add a0, a0, t0
li t6, 2080
bne a0, t6, fail
la s0, destination
li t0, 0x11223344
li a0, 0
li s7, 9
.globl start_subword_lanes
start_subword_lanes:
lw s10, 0(s11)
.globl body_subword_lanes
body_subword_lanes:
sw t0, 0(s0)
li t1, 0x80
sb t1, 1(s0)
li t1, 0x8001
sh t1, 2(s0)
lw a0, 0(s0)
lb t2, 1(s0)
lbu t3, 1(s0)
lh t4, 2(s0)
lhu t5, 2(s0)
.globl stop_subword_lanes
stop_subword_lanes:
lw s9, 0(s11)
li t6, 2147582020
bne a0, t6, fail
sw a0, 0(s8)
li t6, -128
bne t2, t6, fail
li t6, 128
bne t3, t6, fail
li t6, -32767
bne t4, t6, fail
li t6, 32769
bne t5, t6, fail
li t0, 2
sw t0, 16(s8)
.globl program_return
program_return: j program_return
fail: li t0, 3
sw t0, 16(s8)
j fail
.section .data
.balign 16
values:
.word 0
.word 1
.word 2
.word 3
.word 4
.word 5
.word 6
.word 7
.word 8
.word 9
.word 10
.word 11
.word 12
.word 13
.word 14
.word 15
.word 16
.word 17
.word 18
.word 19
.word 20
.word 21
.word 22
.word 23
.word 24
.word 25
.word 26
.word 27
.word 28
.word 29
.word 30
.word 31
.word 32
.word 33
.word 34
.word 35
.word 36
.word 37
.word 38
.word 39
.word 40
.word 41
.word 42
.word 43
.word 44
.word 45
.word 46
.word 47
.word 48
.word 49
.word 50
.word 51
.word 52
.word 53
.word 54
.word 55
.word 56
.word 57
.word 58
.word 59
.word 60
.word 61
.word 62
.word 63
.balign 16
nodes:
node_0: .word node_29, 0
node_1: .word node_55, 1
node_2: .word node_51, 2
node_3: .word node_5, 3
node_4: .word node_26, 4
node_5: .word node_6, 5
node_6: .word node_19, 6
node_7: .word node_41, 7
node_8: .word node_59, 8
node_9: .word node_37, 9
node_10: .word node_11, 10
node_11: .word node_40, 11
node_12: .word node_48, 12
node_13: .word node_23, 13
node_14: .word node_44, 14
node_15: .word node_30, 15
node_16: .word node_53, 16
node_17: .word node_24, 17
node_18: .word node_32, 18
node_19: .word node_61, 19
node_20: .word node_25, 20
node_21: .word node_16, 21
node_22: .word node_20, 22
node_23: .word node_35, 23
node_24: .word node_4, 24
node_25: .word node_21, 25
node_26: .word node_62, 26
node_27: .word node_39, 27
node_28: .word node_57, 28
node_29: .word node_54, 29
node_30: .word node_13, 30
node_31: .word node_47, 31
node_32: .word node_36, 32
node_33: .word node_7, 33
node_34: .word node_33, 34
node_35: .word node_17, 35
node_36: .word node_0, 36
node_37: .word node_27, 37
node_38: .word node_28, 38
node_39: .word node_8, 39
node_40: .word node_56, 40
node_41: .word node_43, 41
node_42: .word node_14, 42
node_43: .word node_58, 43
node_44: .word node_50, 44
node_45: .word node_63, 45
node_46: .word node_2, 46
node_47: .word node_15, 47
node_48: .word node_38, 48
node_49: .word node_34, 49
node_50: .word node_45, 50
node_51: .word node_42, 51
node_52: .word node_12, 52
node_53: .word node_46, 53
node_54: .word node_10, 54
node_55: .word node_9, 55
node_56: .word node_22, 56
node_57: .word node_18, 57
node_58: .word node_60, 58
node_59: .word node_3, 59
node_60: .word node_31, 60
node_61: .word node_52, 61
node_62: .word node_1, 62
node_63: .word node_49, 63
.balign 16
destination:
.zero 256
