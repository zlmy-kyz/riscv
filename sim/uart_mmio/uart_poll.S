# Simulation-only CPU polling test. Never replaces the board boot image.
        .org 0
        lui t0, 0x10001
        lui t1, 0x10000
        addi t2, zero, 1
        sw t2, 16(t1)             # old MMIO TEST_STATUS = RUN
tx_h:
        lw t2, 8(t0)
        andi t2, t2, 1
        beq t2, zero, tx_h
        addi t2, zero, 72
        sb t2, 0(t0)
tx_e:
        lw t2, 8(t0)
        andi t2, t2, 1
        beq t2, zero, tx_e
        addi t2, zero, 101
        sh t2, 0(t0)
tx_l1:
        lw t2, 8(t0)
        andi t2, t2, 1
        beq t2, zero, tx_l1
        addi t2, zero, 108
        sw t2, 0(t0)
tx_l2:
        lw t2, 8(t0)
        andi t2, t2, 1
        beq t2, zero, tx_l2
        addi t2, zero, 108
        sb t2, 0(t0)
tx_o:
        lw t2, 8(t0)
        andi t2, t2, 1
        beq t2, zero, tx_o
        addi t2, zero, 111
        sh t2, 0(t0)
rx_h:
        lw t2, 8(t0)
        andi t2, t2, 4
        beq t2, zero, rx_h
        lbu t3, 4(t0)
        addi t2, zero, 72
        bne t3, t2, fail
rx_e:
        lw t2, 8(t0)
        andi t2, t2, 4
        beq t2, zero, rx_e
        lb t3, 4(t0)
        addi t2, zero, 101
        bne t3, t2, fail
rx_l1:
        lw t2, 8(t0)
        andi t2, t2, 4
        beq t2, zero, rx_l1
        lhu t3, 4(t0)
        addi t2, zero, 108
        bne t3, t2, fail
rx_l2:
        lw t2, 8(t0)
        andi t2, t2, 4
        beq t2, zero, rx_l2
        lh t3, 4(t0)
        addi t2, zero, 108
        bne t3, t2, fail
rx_o:
        lw t2, 8(t0)
        andi t2, t2, 4
        beq t2, zero, rx_o
        lw t3, 4(t0)
        addi t2, zero, 111
        bne t3, t2, fail
        lw t2, 8(t0)
        andi t2, t2, 4
        bne t2, zero, fail
        addi t2, zero, 2
        sw t2, 16(t1)             # PASS
halt:
        jal zero, halt
fail:
        addi t2, zero, 3
        sw t2, 16(t1)             # FAIL
        jal zero, halt
