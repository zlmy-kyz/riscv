# Mode 4 control: the same CSR executed on the correct path. Must complete on
# both revisions, proving the serial mechanism itself still works.
        addi x1, x0, 1
        csrw mscratch, x1
        sw   x1, 0(x0)
DD:     j    DD
