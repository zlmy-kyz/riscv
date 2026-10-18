# Mode 3: an older slow load holds MEM while a taken branch waits in EX.
# Branch does not depend on the load result, so the wait is purely the older
# instruction's, not a young-ID dependency.
        addi x1, x0, 1
        li   x6, 0x40
        lw   x5, 0(x6)
        beq  x0, x0, T3T
        addi x31, x0, 0x2AA
T3T:    sw   x1, 0(x0)
D3:     j    D3
