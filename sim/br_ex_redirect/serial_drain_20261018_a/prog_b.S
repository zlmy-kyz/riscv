# Mode B: drain starts while an older load still holds MEM, then the EX branch
# advances and redirects. Sequence: load (slow) -> taken branch -> CSR.
# The branch sits in EX while the load waits in MEM, so the younger CSR in ID
# can raise serial_candidate before the redirect happens.
        addi x1, x0, 1
        li   x6, 0x40
        lw   x5, 0(x6)
        beq  x0, x0, TB
        csrw mscratch, x1
TB:     sw   x1, 0(x0)
DB:     j    DB
