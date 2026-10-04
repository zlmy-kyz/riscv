#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
selftest.py -- 汇编器/黄金模型自检
============================================================
用两批**外部已知**的证据校验 rvtool.py，避免"自己编自己验"的循环论证：

  A) 工程里 ROM 实际固化的 7 条指令（来自 doc/inst_rom仿真与初始化数据核对.md，
     已用官方 GTP 行为模型复核过）——逐条比对汇编器输出。
  B) 黄金模型在工程原程序上的行为，与 doc 里记录的 IP 实测取指序列比对。

任何一项不一致，整条验证链就不可信，所以这一步失败就不许往下走。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rvtool  # noqa: E402

# ---- A) 工程 ROM 里固化的 7 条指令（外部证据，不是本脚本生成的）----
KNOWN = [
    ('addi x1, x0, 0x0A', 0x00A00093),
    ('addi x2, x1, 5',    0x00508113),
    ('add  x3, x1, x2',   0x002081B3),
    ('sub  x4, x3, x1',   0x40118233),
    ('slli x5, x1, 2',    0x00209293),
    ('add  x6, x5, x3',   0x00328333),
    # 注意：本工具的跳转/分支操作数一律写**绝对目标地址**（标签或字面量），
    # 不是相对偏移。工程 ROM 里 0x18 处的 0x0000006F 就是"自环到 0x18"。
    ('jal  x0, 0x18',     0x0000006F),
]

fails = 0

print('== A) 汇编器 vs 工程 ROM 实际固化值 ==')
asm = rvtool.Assembler()
for i, (src, want) in enumerate(KNOWN):
    got = asm.encode(src, i * 4) & rvtool.MASK32
    ok = (got == want)
    fails += 0 if ok else 1
    print('  [%s] %-20s got=%08x want=%08x' % ('OK' if ok else 'FAIL', src, got, want))

# ---- B) 黄金模型跑工程原程序，比对期望的行为 ----
print('== B) 黄金模型在工程原程序上的行为 ==')
imem = [w for (_, w) in KNOWN] + [0] * (rvtool.ROM_WORDS - len(KNOWN))
iss = rvtool.ISS(imem)
iss.run()

expect_rf = {1: 10, 2: 15, 3: 25, 4: 15, 5: 40, 6: 65}   # x4 = x3 - x1 = 25 - 10 = 15
for k, v in expect_rf.items():
    ok = (iss.rf[k] == v)
    fails += 0 if ok else 1
    print('  [%s] x%d = %d (期望 %d)' % ('OK' if ok else 'FAIL', k, iss.rf[k], v))

ok = (iss.halt_pc == 0x18)
fails += 0 if ok else 1
print('  [%s] halt_pc = %08x (期望 00000018)' % ('OK' if ok else 'FAIL', iss.halt_pc))

# 写回事件应为 6 次（x1..x6），jal x0 不写寄存器
ok = (len(iss.wbtrace) == 6)
fails += 0 if ok else 1
print('  [%s] 写回事件 = %d 次 (期望 6)' % ('OK' if ok else 'FAIL', len(iss.wbtrace)))

# ---- C) VCD/轨迹格式自检：trace 的 pc 序列必须与 itrace 中"写了寄存器的那些"一致 ----
print('== C) trace / itrace 一致性 ==')
wb_pcs = [pc for (pc, _, _) in iss.wbtrace]
it_pcs = [pc for (pc, ins) in iss.itrace if ((ins >> 7) & 0x1F) != 0
          and (ins & 0x7F) not in (0x23, 0x63)]
ok = (wb_pcs == it_pcs)
fails += 0 if ok else 1
print('  [%s] 写回 pc 序列与指令流一致：%s' % ('OK' if ok else 'FAIL', [hex(p) for p in wb_pcs]))

print('---- 自检结果：%s ----' % ('全部通过' if fails == 0 else '%d 项失败' % fails))
sys.exit(1 if fails else 0)
