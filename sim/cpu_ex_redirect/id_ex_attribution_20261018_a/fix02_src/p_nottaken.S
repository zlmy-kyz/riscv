# fix01 not-taken control: the conditional branch is not taken.
        addi x1, x0, 1
        addi x2, x0, 5
        beq  x1, x2, F4B
        addi x3, x0, 1
        sw   x3, 0(x0)
        j    F4D
F4B:    addi x31, x0, 0x2AA
F4D:    j    F4D
