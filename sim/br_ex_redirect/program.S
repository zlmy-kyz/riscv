# ===========================================================================
# Directed program for the "ID decide + EX redirect" change.
# Every case writes its architectural result into DMEM so the testbench can
# check it without hierarchy references.
#   dmem[0]  = 0x0C  basic conditional branches (6 forms)
#   dmem[1]  = 0x2A  jal / jalr targets and link handling
#   dmem[2]  = 1     load result consumed by a branch on the next instruction
#   dmem[3]  = 7     load result consumed by jalr on the next instruction
#   dmem[4]  = 5     back-to-back taken branch loop
#   dmem[5]  = 9     taken branch must stop once while a load holds MEM
# ===========================================================================

        # ---- case 1: conditional branches, taken and not-taken ----
        addi x1, x0, 5
        addi x2, x0, 5
        addi x3, x0, 0
        beq  x1, x2, T1L1
        addi x3, x0, 0x7FF
T1L1:   bne  x1, x2, T1L2
        addi x3, x0, 1
T1L2:   blt  x1, x2, T1L3
        addi x3, x3, 1
T1L3:   bge  x1, x2, T1L4
        addi x3, x0, 0x7FF
T1L4:   addi x3, x3, 10
        sw   x3, 0(x0)

        # ---- case 2: jal / jalr ----
        jal  x5, T2F1
        addi x6, x0, 0x7FF
T2F1:   la   x7, T2F2
        jalr x8, x7, 0
        addi x6, x0, 0x7FE
T2F2:   la   x9, T2F3
        jalr x0, x9, 0
        addi x6, x0, 0x7FD
T2F3:   addi x10, x0, 42
        sw   x10, 4(x0)

        # ---- case 3: load -> branch in the very next instruction ----
        li   x1, 0x100
        lw   x2, 0(x1)
        beq  x2, x0, T3BAD
        addi x3, x0, 1
        lw   x4, 4(x1)
        beq  x4, x0, T3OK
        addi x3, x0, 0x7FF
T3OK:   sw   x3, 8(x0)
        j    T3DONE
T3BAD:  sw   x0, 8(x0)
T3DONE:

        # ---- case 4: load -> jalr in the very next instruction ----
        li   x1, 0x110
        la   x2, T4F4
        sw   x2, 0(x1)
        lw   x3, 0(x1)
        jalr x0, x3, 0
        addi x4, x0, 0x7FF
T4F4:   addi x4, x0, 7
        sw   x4, 12(x0)

        # ---- case 5: loop with a taken branch every iteration ----
        addi x1, x0, 5
        addi x2, x0, 0
T5LOOP: addi x2, x2, 1
        blt  x2, x1, T5LOOP
        sw   x2, 16(x0)

        # ---- case 6: taken branch while a load still holds MEM ----
        li   x1, 0x120
        lw   x2, 0(x1)
        beq  x0, x0, T6SKIP
        addi x5, x0, 0x7FF
T6SKIP: addi x5, x0, 9
        sw   x5, 20(x0)

TEND:   j    TEND
