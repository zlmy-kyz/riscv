# Minimal real-CPU DDR integration, not a historical ISA/CoreMark suite.
# DDR code at 0x40000000; data at 0x40000800. Final: 64, sum 2080, done 1.
    lui x1, 0x40001
    addi x1, x1, -2048
    addi x2, x0, 0
    addi x3, x0, 64
    addi x4, x0, 0
loop:
    lw x5, 0(x1)
    addi x5, x5, 1
    sw x5, 0(x1)
    add x4, x4, x5
    addi x2, x2, 1
    blt x2, x3, loop
    sw x4, 4(x1)
    addi x6, x0, 1
    sw x6, 64(x1)
done:
    jal x0, done
