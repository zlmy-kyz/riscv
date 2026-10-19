# fix01 older MEM: load then an independent taken branch.
        addi x1, x0, 1
        li   x6, 0x40
        lw   x5, 0(x6)
        beq  x0, x0, F3T
        addi x31, x0, 0x2AA
F3T:    sw   x1, 0(x0)
F3D:    j    F3D
