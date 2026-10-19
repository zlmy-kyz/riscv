    lui x1, 0x40001
    addi x1, x1, -2048          # x1 = 0x40000800 data base (local 0x800)
    lui x6, 0x40001
    addi x6, x6, -2016          # x6 = 0x40000820 burst base (local 0x820)
    addi x2, x0, 0
    addi x3, x0, 64
    addi x4, x0, 0
    addi x20, x0, 0
    lui x12, 1
    addi x12, x12, -2048
    .word 0x30461073            # csrw mie, x12 (bit 11)
    lui x13, 0x40000
    addi x13, x13, 256
    .word 0x30569073            # csrw mtvec, x13 (0x40000100)
    .word 0x30046073            # csrsi mstatus, 8
    lui x10, 0x10000
    addi x11, x0, 3
    sw x11, 264(x10)            # PERF CTRL START (0x108 command 3)
    addi x11, x0, 1
    sw x11, 16(x10)             # TEST_STATUS RUN (0x10 = 1)
loop:
    lw x5, 0(x1)
    addi x5, x5, 1
    sw x5, 0(x1)
    add x4, x4, x5
    addi x2, x2, 1
    blt x2, x3, loop
    sw x4, 4(x1)                # 0x40000804 accumulator
    addi x7, x0, 0x11
    sw x7, 0(x6)                # burst store 1 (0x40000820, line 65)
    sw x7, 4(x6)                # burst store 2, back-to-back -> turnover
    addi x11, x0, 0x41
    lui x9, 0x10001
    sw x11, 0(x9)               # UART TX_DATA 0x10001000 (non-DDR)
    sw x11, 0(x0)               # data RAM store at 0x0 (non-DDR)
    sw x7, 8(x6)                # burst store 3
    sw x7, 12(x6)               # burst store 4
    addi x7, x0, 0x5a
    sb x7, 1(x6)                # 0x40000821 partial byte, same line as the burst
    addi x7, x0, 0x7b
    sb x7, 2(x1)                # 0x40000802 partial byte, same line as the loop data
    addi x6, x0, 1
    sw x6, 64(x1)               # 0x40000840
    .word 0x0ff0000f            # fence iorw, iorw
    lui x10, 0x10000
    addi x11, x0, 4
    sw x6, 68(x1)               # 0x40000844 issued just before the stop
    sw x11, 264(x10)            # PERF CTRL STOP (0x108 command 4), waits for drain
    addi x11, x0, 2
    sw x11, 16(x10)             # TEST_STATUS PASS (0x10 = 2)
done:
    jal x0, done
    .org 0x100
handler:
    addi x20, x20, 1
    .word 0x30200073            # mret
