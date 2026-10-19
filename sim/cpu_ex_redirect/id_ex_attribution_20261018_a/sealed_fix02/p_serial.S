# fix01 young serial variant: older slow load, taken branch, wrong-path CSR.
# Exercises the serial-drain cancel path while MEM is held by an older load.
        addi x1, x0, 1
        li   x6, 0x40
        lw   x5, 0(x6)
        beq  x0, x0, F5T
        csrw mscratch, x1
        addi x31, x0, 0x2AB
F5T:    sw   x1, 0(x0)
F5D:    j    F5D
