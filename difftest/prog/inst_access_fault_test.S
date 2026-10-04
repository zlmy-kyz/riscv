# =============================================================================
# inst_access_fault_test.S -- 指令地址译码/Instruction Access Fault端到端测试
#
# 跳转到ROM窗口末端之后的0x8000_4000。正确行为是：互连不选中ROM，CPU
# 收到错误响应并进入异常，mcause=1，mtval/mepc=0x8000_4000。
# 处理程序把mepc改为resume，mret后通过RAM中的tohost报告结果。
# =============================================================================
        .org 0
_start:
        lui   t0, 0x80000
        addi  t0, t0, 0x100
        csrw  mtvec, t0

        lui   t1, 0x80004
faulting_target:
        jalr  zero, t1, 0

wrong_path:
        addi  gp, zero, 9
        jal   zero, write_tohost

resume:
        addi  gp, zero, 1
        jal   zero, write_tohost

fail_cause:
        addi  gp, zero, 3
        jal   zero, write_tohost

fail_tval:
        addi  gp, zero, 5
        jal   zero, write_tohost

fail_mepc:
        addi  gp, zero, 7

write_tohost:
        lui   t5, 0x80001
        sw    gp, 0(t5)

halt:
        jal   zero, halt

        .org 0x100
trap_handler:
        csrr  t2, mcause
        addi  t3, zero, 1
        bne   t2, t3, fail_cause

        csrr  t2, mtval
        lui   t3, 0x80004
        bne   t2, t3, fail_tval

        csrr  t2, mepc
        bne   t2, t3, fail_mepc

        lui   t2, 0x80000
        addi  t2, t2, 0x1c
        csrw  mepc, t2
        mret
