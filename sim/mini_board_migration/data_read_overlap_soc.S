    lui x1, 0x40001
    addi x1, x1, -2048
    addi x2, x0, 0
    addi x3, x0, 64
    addi x4, x0, 0
    addi x20, x0, 0
    lui x12, 1
    addi x12, x12, -2048
    .word 0x30461073 # csrw mie, x12
    lui x13, 0x40000
    addi x13, x13, 256
    .word 0x30569073 # csrw mtvec, x13
    .word 0x30046073 # csrsi mstatus, 8
    addi x7, x1, 32
    lw x8, 0(x7) # Preload an independent D-cache line
    lui x10, 0x10000
    addi x11, x0, 3
    sw x11, 264(x10) # PERF CTRL START (0x108, command 3)
loop:
    lw x5, 0(x1)
    addi x5, x5, 1
    sw x5, 0(x1)
    lw x8, 0(x7) # Hit this other line while the store drains
    add x4, x4, x5
    addi x2, x2, 1
    blt x2, x3, loop
    sw x4, 4(x1)
    addi x6, x0, 1
    sw x6, 64(x1)
    .word 0x0ff0000f # fence iorw, iorw
    lui x10, 0x10000
    sw x6, 16(x10) # TEST_STATUS RUN before PASS
    addi x11, x0, 4
    sw x6, 68(x1)
    sw x11, 264(x10) # PERF CTRL STOP (0x108, command 4)
    addi x11, x0, 2
pass_store:
    sw x11, 16(x10)
done:
    jal x0, done
    .org 0x100
handler:
    addi x20, x20, 1
    .word 0x30200073 # mret
