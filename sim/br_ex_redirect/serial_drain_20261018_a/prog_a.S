# Mode A: taken branch with a CSR in the very next slot (wrong path).
# If the EX redirect flushes the CSR after the drain FSM has already latched
# FLOW_SERIAL_DRAIN, the FSM can wait forever for a serial_candidate that no
# longer exists. Target writes dmem[0]=1 to prove it was reached.
        addi x1, x0, 1
        beq  x0, x0, TA
        csrw mscratch, x1
        addi x2, x0, 0x7FF
TA:     sw   x1, 0(x0)
DA:     j    DA
