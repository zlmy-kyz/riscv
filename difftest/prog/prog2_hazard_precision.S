# Check that only a real load-use dependency inserts a bubble.
        .org 0
        addi x1, x0, 0x55
        sw   x1, 0(x0)
        lw   x5, 0(x0)
        lui  x6, 0x28       # inst[19:15] == 5, but LUI does not read rs1
        lw   x5, 0(x0)
        addi x7, x0, 5     # inst[24:20] == 5, but ADDI does not read rs2
        lw   x5, 0(x0)
        addi x8, x5, 1     # real rs1 dependency: one bubble required
halt:   jal  x0, halt
