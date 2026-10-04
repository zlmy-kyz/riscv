# =============================================================================
# mmio_test.S -- CPU -> 数据总线 -> 地址译码 -> MMIO/RAM 端到端测试
#
# 地址：
#   0x1000_0000  MMIO SCRATCH
#   0x1000_0004  MMIO ID（期望 0x4d4d494f，即 "MMIO"）
#   0x8000_1000  RAM 中的 tohost
#
# tohost：1=PASS；3/5/7 分别表示字读写、字节写、ID读取失败。
# =============================================================================
        .org 0
_start:
        lui   t0, 0x10000

        # 32位 scratch 写回读。
        lui   t1, 0x12345
        addi  t1, t1, 0x678
        sw    t1, 0(t0)
        lw    t2, 0(t0)
        bne   t2, t1, fail_word

        # 对 scratch 的 byte1 写 0xaa，再用 lbu 验证字节通道。
        addi  t3, zero, 0xaa
        sb    t3, 1(t0)
        lbu   t2, 1(t0)
        bne   t2, t3, fail_byte

        # 读取只读设备ID。
        lw    t2, 4(t0)
        lui   t1, 0x4d4d5
        addi  t1, t1, -1713
        bne   t2, t1, fail_id

pass:
        addi  gp, zero, 1
        jal   zero, write_tohost

fail_word:
        addi  gp, zero, 3
        jal   zero, write_tohost

fail_byte:
        addi  gp, zero, 5
        jal   zero, write_tohost

fail_id:
        addi  gp, zero, 7

write_tohost:
        lui   t5, 0x80001
        sw    gp, 0(t5)

halt:
        jal   zero, halt
