# Mode 1: pure one-cycle I hit, no data wait.
# taken branch -> wrong-path slot (unique write to x31, never committed)
# target writes dmem[0]=1, then spins.
        addi x1, x0, 1
        beq  x0, x0, T1T
        addi x31, x0, 0x2AA
T1T:    sw   x1, 0(x0)
D1:     j    D1
