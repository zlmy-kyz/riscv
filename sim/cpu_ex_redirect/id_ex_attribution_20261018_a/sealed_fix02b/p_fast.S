# fix01 fast: pure one-cycle I hit, no data wait.
        addi x1, x0, 1
        beq  x0, x0, F1T
        addi x31, x0, 0x2AA
F1T:    sw   x1, 0(x0)
F1D:    j    F1D
