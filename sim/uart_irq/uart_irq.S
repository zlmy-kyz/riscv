# Simulation-only ISR program; board boot ROM/RAM are never regenerated.
.org 0
addi x2,x0,1024
csrw mtvec,x2
lui x3,1
addi x3,x3,-2048
csrw mie,x3
addi x4,x0,8
csrw mstatus,x4
lui x5,0x10001
lui x16,0x40000
lui x30,0x10000
addi x1,x0,768
addi x26,x0,2047
addi x26,x26,1
addi x31,x0,1
sw x31,16(x30)
# Disabled by reset: polling consumes D without entering ISR.
addi x6,x0,1
sw x6,0(x1)
poll_disabled: lw x7,8(x5)
andi x7,x7,4
beq x7,x0,poll_disabled
lbu x24,4(x5)
sb x24,0(x26)
addi x26,x26,1
# Enable with empty FIFO, leave enough time to detect spurious IRQ.
addi x6,x0,256
sw x6,12(x5)
addi x6,x0,2
sw x6,0(x1)
addi x7,x0,100
empty_delay: addi x7,x7,-1
bne x7,x0,empty_delay
# One H enters ISR and returns to this ordinary loop.
addi x6,x0,3
sw x6,0(x1)
addi x8,x0,1
wait_one: bne x27,x8,wait_one
# Queue five bytes during DDR load with global interrupts masked.
csrw mstatus,x0
addi x6,x0,4
sw x6,0(x1)
queue_load: lw x10,0(x16)
csrw mstatus,x4
addi x8,x0,6
wait_queue: bne x27,x8,wait_queue
# Actual UART IRQ arrives while the CPU store waits for DDR WREADY.
addi x6,x0,5
sw x6,0(x1)
addi x11,x0,85
target: sw x11,4(x16)
resume: csrr x9,mip
addi x8,x0,7
wait_store: bne x27,x8,wait_store
# Actual UART IRQ arrives while a delayed MMIO load waits for its response.
addi x6,x0,6
sw x6,0(x1)
wait_mmio: lw x12,8(x5)
csrr x9,mip
addi x8,x0,8
wait_mmio_irq: bne x27,x8,wait_mmio_irq
# Disable by command, then consume Z using the original polling interface.
addi x6,x0,512
sw x6,12(x5)
addi x6,x0,7
sw x6,0(x1)
poll_disabled_again: lw x7,8(x5)
andi x7,x7,4
beq x7,x0,poll_disabled_again
lbu x24,4(x5)
sb x24,0(x26)
addi x26,x26,1
addi x31,x0,2
sw x31,16(x30)
done: jal x0,done
.org 1024
handler: csrr x20,mcause
csrr x21,mepc
csrr x22,mtval
addi x23,x23,1
isr_poll: lw x28,8(x5)
andi x28,x28,4
beq x28,x0,isr_return
lbu x24,4(x5)
sb x24,0(x26)
addi x26,x26,1
addi x27,x27,1
jal x0,isr_poll
isr_return: mret
