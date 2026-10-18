# Mode 3 control: same shape as A but the wrong-path slot is a plain ALU
# instruction. Both RTL revisions must reach the target.
        addi x1, x0, 1
        beq  x0, x0, TC
        addi x2, x0, 0x7FF
TC:     sw   x1, 0(x0)
DC:     j    DC
