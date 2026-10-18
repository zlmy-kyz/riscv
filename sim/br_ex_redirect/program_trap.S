# Trap-priority case for the EX-redirect change.
# jalr with (rs1+imm)&~1 == 2 is a 2-byte-aligned target, which must raise
# instruction-address-misaligned instead of being taken as a redirect.
# The handler is the default mtvec (0), so the CPU restarts and traps again;
# the testbench only requires that the trap happened and that the instruction
# after the jalr never retired.
        addi x1, x0, 1
        sw   x1, 24(x0)          # dmem[6] = 1, proves the program ran
        li   x2, 0x2
        jalr x0, x2, 0           # misaligned target -> trap
        addi x3, x0, 0x7FF
        sw   x3, 28(x0)          # dmem[7] must stay 0
TEND:   j    TEND
