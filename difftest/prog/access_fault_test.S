# =============================================================================
# access_fault_test.S -- 未映射地址访问异常端到端测试
#
# 验证：
#   lw 0x2000_0000 -> mcause=5，mtval=0x2000_0000
#   sw 0x2000_0004 -> mcause=7，mtval=0x2000_0004
#   mepc精确指向故障指令，处理程序写 mepc+4 后 mret 正常返回
#   故障load不修改目的寄存器，未映射store不写入任何从机
# =============================================================================
        .org 0
_start:
        lui   t0, 0x80000
        addi  t0, t0, 0x100
        csrw  mtvec, t0
        addi  s0, zero, 0

        lui   t1, 0x20000
        addi  t2, zero, 0x55

faulting_load:
        lw    t2, 0(t1)
        addi  t3, zero, 0x55
        bne   t2, t3, fail_precise

faulting_store:
        sw    t2, 4(t1)
        addi  t3, zero, 2
        bne   s0, t3, fail_stage

pass:
        addi  gp, zero, 1
        jal   zero, write_tohost

fail_cause:
        addi  gp, zero, 3
        jal   zero, write_tohost

fail_tval:
        addi  gp, zero, 5
        jal   zero, write_tohost

fail_stage:
        addi  gp, zero, 7
        jal   zero, write_tohost

fail_precise:
        addi  gp, zero, 9
        jal   zero, write_tohost

fail_mepc:
        addi  gp, zero, 11

write_tohost:
        lui   t5, 0x80001
        sw    gp, 0(t5)

halt:
        jal   zero, halt

        .org 0x100
trap_handler:
        csrr  t4, mcause
        beq   s0, zero, check_load_fault

        # 第二次陷阱必须是store access fault。
        addi  t5, zero, 1
        bne   s0, t5, fail_stage
        addi  t5, zero, 7
        bne   t4, t5, fail_cause
        csrr  t4, mtval
        lui   t5, 0x20000
        addi  t5, t5, 4
        bne   t4, t5, fail_tval
        csrr  t4, mepc
        lui   t5, 0x80000
        addi  t5, t5, 0x24
        bne   t4, t5, fail_mepc
        jal   zero, resume

check_load_fault:
        addi  t5, zero, 5
        bne   t4, t5, fail_cause
        csrr  t4, mtval
        lui   t5, 0x20000
        bne   t4, t5, fail_tval
        csrr  t4, mepc
        lui   t5, 0x80000
        addi  t5, t5, 0x18
        bne   t4, t5, fail_mepc

resume:
        addi  s0, s0, 1
        addi  t4, t4, 4
        csrw  mepc, t4
        mret
