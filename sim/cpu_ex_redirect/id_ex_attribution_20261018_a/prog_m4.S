# Mode 4: same condition branch NOT taken. Everything after it is the correct
# path, so its sequential fetch must not be attributed as wrong-path occupancy.
        addi x1, x0, 1
        addi x2, x0, 5
        beq  x1, x2, BAD4
        addi x3, x0, 1
        sw   x3, 0(x0)
        j    D4
BAD4:   addi x31, x0, 0x2AA
D4:     j    D4
