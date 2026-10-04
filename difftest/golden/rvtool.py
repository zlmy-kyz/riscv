#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rvtool.py -- myCPU 差分验证的"黄金模型"工具链
============================================================

一份脚本，三个角色：

  1) 汇编器   把 RISC-V 汇编（本工程 DUT 支持的 RV32I 子集）编成 32-bit 机器码
  2) 黄金模型 指令级模拟器(ISS)，严格按架构语义逐条执行
  3) 轨迹导出 输出 golden trace（写回事件）与 golden itrace（指令流）

为什么要有它
------------------------------------------------------------
差分验证的关键是"参考结果必须绝对可信"。手写期望值 / 手算指令编码
在真实工程里出错率极高（本工程已踩过三次）。所以参考结果一律由本
脚本生成，人不参与任何一位的计算。

产出（全部写进 build 目录）
------------------------------------------------------------
  rom.hex         1024 行十六进制，一行一个 32-bit 字 -> 指令存储器初值
  ram.hex         数据存储器初值（默认全 0）
  trace.txt       首行 "<halt_pc> <n_wb>"，其后每行 "<pc> <wnum> <wdata>"
  itrace.txt      首行 "<halt_pc> <n_inst>"，其后每行 "<pc> <inst>"
  rf_golden.txt   首行 "<n>"，其后每行 "<idx> <value>"
  mem_golden.txt  同上（数据存储器）
  prog.lst        反汇编清单（给人看）

用法
------------------------------------------------------------
  python rvtool.py build  prog/prog0_alu.S [build]
  python rvtool.py asm    prog/mmio_test.S [build]
  python rvtool.py check  build
"""

import os
import re
import sys

# ---------------------------------------------------------------- 常量

MASK32 = 0xFFFFFFFF
ROM_WORDS = 1024          # inst_rom : 1024 x 32bit = 4KB
RAM_BYTES = 4096          # data_ram : 1024 x 32bit = 4KB
BRAM_WORDS = 4096         # 当前PDS ROM/RAM IP：12位字地址，4096 x 32bit
MAX_STEPS = 500000        # 黄金模型步数上限，防跑飞


def s32(v):
    v &= MASK32
    return v - (1 << 32) if v & 0x80000000 else v


def sext(v, bits):
    """把 v 从 bits 位宽符号扩展到 32 位。

    必须按字段宽度扩，不能对拼好的值调 s32()：
    12 位的 0xFFD 在 32 位整数里最高位是 0，s32() 不会补符号，
    结果 -3 会变成 4093 —— 这是最容易悄悄错掉的一处。
    """
    m = 1 << (bits - 1)
    return ((v & ((1 << bits) - 1)) ^ m) - m


def imm_i(inst):
    return sext(inst >> 20, 12)


def imm_s(inst):
    return sext(((inst >> 25) << 5) | ((inst >> 7) & 0x1F), 12)


def imm_b(inst):
    return sext(((inst >> 31) << 12) | (((inst >> 7) & 1) << 11)
                | (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1), 13)


def imm_j(inst):
    return sext(((inst >> 31) << 20) | (((inst >> 12) & 0xFF) << 12)
                | (((inst >> 20) & 1) << 11) | (((inst >> 21) & 0x3FF) << 1), 21)


# ---------------------------------------------------------------- 编码器
# 每个函数把各字段拼成一条 32-bit 指令，拼接顺序即 RISC-V 规范原文。

def enc_r(f7, rs2, rs1, f3, rd, op):
    return ((f7 & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) \
         | ((f3 & 0x07) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def enc_i(imm, rs1, f3, rd, op):
    return ((imm & 0xFFF) << 20) | ((rs1 & 0x1F) << 15) \
         | ((f3 & 0x07) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def enc_i_sh(f7, shamt, rs1, f3, rd, op):
    return ((f7 & 0x7F) << 25) | ((shamt & 0x1F) << 20) | ((rs1 & 0x1F) << 15) \
         | ((f3 & 0x07) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def enc_s(imm, rs2, rs1, f3, op):
    i = imm & 0xFFF
    return (((i >> 5) & 0x7F) << 25) | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) \
         | ((f3 & 0x07) << 12) | ((i & 0x1F) << 7) | (op & 0x7F)


def enc_b(imm, rs2, rs1, f3, op):
    i = imm & 0x1FFF
    return (((i >> 12) & 0x1) << 31) | (((i >> 5) & 0x3F) << 25) \
         | ((rs2 & 0x1F) << 20) | ((rs1 & 0x1F) << 15) | ((f3 & 0x07) << 12) \
         | (((i >> 1) & 0xF) << 8) | (((i >> 11) & 0x1) << 7) | (op & 0x7F)


def enc_u(imm20, rd, op):
    return ((imm20 & 0xFFFFF) << 12) | ((rd & 0x1F) << 7) | (op & 0x7F)


def enc_j(imm, rd, op):
    i = imm & 0x1FFFFF
    return (((i >> 20) & 0x1) << 31) | (((i >> 1) & 0x3FF) << 21) \
         | (((i >> 11) & 0x1) << 20) | (((i >> 12) & 0xFF) << 12) \
         | ((rd & 0x1F) << 7) | (op & 0x7F)


# ---------------------------------------------------------------- 指令表
# 只列 DUT 已译码并实现的指令。表外的一律报错，避免"编了就以为能跑"。

REG_R = {  # mnem : (funct7, funct3, opcode)   rd, rs1, rs2
    'add': (0x00, 0x0, 0x33), 'sub': (0x20, 0x0, 0x33),
    'sll': (0x00, 0x1, 0x33), 'slt': (0x00, 0x2, 0x33),
    'sltu': (0x00, 0x3, 0x33), 'xor': (0x00, 0x4, 0x33),
    'srl': (0x00, 0x5, 0x33), 'sra': (0x20, 0x5, 0x33),
    'or': (0x00, 0x6, 0x33), 'and': (0x00, 0x7, 0x33),
}
REG_I = {  # mnem : (funct3, opcode)           rd, rs1, imm12
    'addi': (0x0, 0x13), 'slti': (0x2, 0x13), 'sltiu': (0x3, 0x13),
    'xori': (0x4, 0x13), 'ori': (0x6, 0x13), 'andi': (0x7, 0x13),
}
REG_ISH = {  # mnem : (funct7, funct3, opcode)  rd, rs1, shamt
    'slli': (0x00, 0x1, 0x13), 'srli': (0x00, 0x5, 0x13), 'srai': (0x20, 0x5, 0x13),
}
REG_LD = {'lb': (0x0, 0x03), 'lh': (0x1, 0x03), 'lw': (0x2, 0x03),
          'lbu': (0x4, 0x03), 'lhu': (0x5, 0x03)}          # rd, imm(rs1)
REG_ST = {'sb': (0x0, 0x23), 'sh': (0x1, 0x23), 'sw': (0x2, 0x23)}   # rs2, imm(rs1)
REG_B = {'beq': (0x0, 0x63), 'bne': (0x1, 0x63), 'blt': (0x4, 0x63),
         'bge': (0x5, 0x63), 'bltu': (0x6, 0x63), 'bgeu': (0x7, 0x63)}  # rs1, rs2, target
REG_U = {'lui': 0x37, 'auipc': 0x17}          # rd, imm20  (imm20 已就位于 [31:12])
REG_J = {'jal': 0x6F}                          # rd, target
REG_JR = {'jalr': (0x0, 0x67)}                 # rd, rs1, imm12

ABI = {'zero': 0, 'ra': 1, 'sp': 2, 'gp': 3, 'tp': 4, 't0': 5, 't1': 6, 't2': 7,
       's0': 8, 'fp': 8, 's1': 9, 'a0': 10, 'a1': 11, 'a2': 12, 'a3': 13,
       'a4': 14, 'a5': 15, 'a6': 16, 'a7': 17, 's2': 18, 's3': 19, 's4': 20,
       's5': 21, 's6': 22, 's7': 23, 's8': 24, 's9': 25, 's10': 26, 's11': 27,
       't3': 28, 't4': 29, 't5': 30, 't6': 31}


def parse_reg(tok):
    tok = tok.strip()
    m = re.fullmatch(r'[xX](\d+)', tok)
    if m and 0 <= int(m.group(1)) <= 31:
        return int(m.group(1))
    if tok in ABI:
        return ABI[tok]
    raise ValueError('无法识别的寄存器 %r' % tok)


# ---------------------------------------------------------------- 汇编器

class Assembler:
    """两遍汇编：第一遍定位 label 与地址，第二遍编码。"""

    def __init__(self):
        self.sym = {}
        self.items = []            # (addr, kind, payload, raw_line)
        self.listing = []          # (addr, hex|None, raw_line)

    def assemble(self, text):
        self._pass1(text)
        out = {}
        for (a, kind, payload, raw) in self.items:
            if kind == 'word':
                v = self.eval_imm(payload) & MASK32
            elif kind == 'inst':
                v = self.encode(payload, a) & MASK32
            else:                                   # org / space
                self.listing.append((a, None, raw))
                continue
            out[a] = v
            self.listing.append((a, '%08x' % v, raw))
        return out

    def _pass1(self, text):
        self.sym = {}
        self.items = []
        addr = 0
        for lineno, raw in enumerate(text.splitlines(), 1):
            line = raw.split('#')[0].split('//')[0].strip()
            if not line:
                continue
            while True:
                m = re.match(r'^([A-Za-z_.$][\w.$]*)\s*:\s*(.*)$', line)
                if not m:
                    break
                name = m.group(1)
                if name in self.sym:
                    raise ValueError('第 %d 行：标签 %r 重复' % (lineno, name))
                self.sym[name] = addr
                line = m.group(2).strip()
            if not line:
                continue
            parts = re.split(r'\s+', line, maxsplit=1)
            op = parts[0].lower()
            operands = parts[1] if len(parts) > 1 else ''
            if op == '.org':
                addr = int(operands.strip(), 0)
                self.items.append((addr, 'org', operands, raw))
            elif op == '.space':
                self.items.append((addr, 'space', operands, raw))
                addr += int(operands.strip(), 0)
            elif op == '.word':
                for w in operands.split(','):
                    self.items.append((addr, 'word', w.strip(), raw))
                    addr += 4
            elif op in ('.text', '.data'):
                pass
            else:
                self.items.append((addr, 'inst', op + ' ' + operands, raw))
                addr += 4

    def eval_imm(self, expr):
        expr = expr.strip()
        if expr == '':
            return 0
        m = re.fullmatch(r'([A-Za-z_.$][\w.$]*)\s*([+-])\s*(.+)', expr)
        if m and m.group(1) in self.sym:
            base = self.sym[m.group(1)]
            off = int(m.group(3), 0)
            return base + off if m.group(2) == '+' else base - off
        if expr in self.sym:
            return self.sym[expr]
        return int(expr, 0)

    def encode(self, text, cur):
        parts = re.split(r'\s+', text.strip(), maxsplit=1)
        mnem = parts[0].lower()
        ops = [o.strip() for o in parts[1].split(',')] if len(parts) > 1 else []

        # ---- 伪指令 ----
        if mnem == 'nop':
            return enc_i(0, 0, 0x0, 0, 0x13)
        if mnem == 'mv':
            return enc_i(0, parse_reg(ops[1]), 0x0, parse_reg(ops[0]), 0x13)
        if mnem == 'li':
            v = self.eval_imm(ops[1])
            if not -2048 <= v <= 2047:
                raise ValueError('li 的立即数 %d 超出 12 位，请手写 lui+addi' % v)
            return enc_i(v, 0, 0x0, parse_reg(ops[0]), 0x13)
        if mnem == 'not':
            return enc_i(-1, parse_reg(ops[1]), 0x4, parse_reg(ops[0]), 0x13)
        if mnem == 'neg':
            return enc_r(0x20, parse_reg(ops[1]), 0, 0x0, parse_reg(ops[0]), 0x33)

        def mem_operand(s):
            m = re.fullmatch(r'(.*)\((.+)\)', s)
            if not m:
                raise ValueError('访存操作数要写 imm(rs1) 形式：%r' % text)
            return self.eval_imm(m.group(1)), parse_reg(m.group(2))

        if mnem in REG_R:
            f7, f3, op = REG_R[mnem]
            return enc_r(f7, parse_reg(ops[2]), parse_reg(ops[1]), f3, parse_reg(ops[0]), op)
        if mnem in REG_I:
            f3, op = REG_I[mnem]
            return enc_i(self.eval_imm(ops[2]), parse_reg(ops[1]), f3, parse_reg(ops[0]), op)
        if mnem in REG_ISH:
            f7, f3, op = REG_ISH[mnem]
            return enc_i_sh(f7, self.eval_imm(ops[2]), parse_reg(ops[1]), f3, parse_reg(ops[0]), op)
        if mnem in REG_LD:
            f3, op = REG_LD[mnem]
            imm, rs1 = mem_operand(ops[1])
            return enc_i(imm, rs1, f3, parse_reg(ops[0]), op)
        if mnem in REG_ST:
            f3, op = REG_ST[mnem]
            imm, rs1 = mem_operand(ops[1])
            return enc_s(imm, parse_reg(ops[0]), rs1, f3, op)
        if mnem in REG_B:
            f3, op = REG_B[mnem]
            tgt = self.eval_imm(ops[2])
            return enc_b(tgt - cur, parse_reg(ops[1]), parse_reg(ops[0]), f3, op)
        if mnem in REG_U:
            return enc_u(self.eval_imm(ops[1]), parse_reg(ops[0]), REG_U[mnem])
        if mnem in REG_J:
            tgt = self.eval_imm(ops[1])
            return enc_j(tgt - cur, parse_reg(ops[0]), REG_J[mnem])
        if mnem in REG_JR:
            f3, op = REG_JR[mnem]
            imm = self.eval_imm(ops[2]) if len(ops) > 2 else 0
            return enc_i(imm, parse_reg(ops[1]), f3, parse_reg(ops[0]), op)

        raise ValueError('DUT 未实现 / 不认识的助记符 %r' % mnem)


# ---------------------------------------------------------------- 黄金模型(ISS)

class ISS:
    """RV32I 指令级模拟器：严格按架构语义执行。"""

    def __init__(self, imem):
        self.imem = list(imem) + [0] * (ROM_WORDS - len(imem))
        self.imem = self.imem[:ROM_WORDS]
        self.dmem = bytearray(RAM_BYTES)
        self.rf = [0] * 32
        self.pc = 0
        self.itrace = []       # (pc, inst)          —— 每条执行的指令
        self.wbtrace = []      # (pc, wnum, wdata)   —— 每次寄存器写
        self.halt_pc = None
        self.steps = 0

    # ---- 数据存储器：纯字节数组（小端），4KB ----
    def ld(self, addr, size, signed):
        b = self.dmem[addr % RAM_BYTES: addr % RAM_BYTES + size]
        if len(b) < size:
            b = b + bytes(size - len(b))
        v = int.from_bytes(b, 'little')
        if signed and size == 2 and v & 0x8000:
            v |= 0xFFFF0000
        if signed and size == 1 and v & 0x80:
            v |= 0xFFFFFF00
        return v & MASK32

    def st(self, addr, size, val):
        a = addr % RAM_BYTES
        data = (val & MASK32).to_bytes(4, 'little')[:size]
        for k in range(size):
            self.dmem[(a + k) % RAM_BYTES] = data[k]

    def run(self):
        while True:
            self.steps += 1
            if self.steps > MAX_STEPS:
                raise RuntimeError('ISS：超过 %d 步仍未停机，程序可能跑飞' % MAX_STEPS)

            pc = self.pc
            inst = self.imem[(pc >> 2) & (ROM_WORDS - 1)]
            op = inst & 0x7F
            rd = (inst >> 7) & 0x1F
            f3 = (inst >> 12) & 0x7
            rs1 = (inst >> 15) & 0x1F
            rs2 = (inst >> 20) & 0x1F
            f7 = (inst >> 25) & 0x7F
            a = self.rf[rs1]
            b = self.rf[rs2]
            nxt = (pc + 4) & MASK32
            wb = None

            if op == 0x33:                                        # R 型
                if f7 == 0x00:
                    wb = {0x0: a + b, 0x1: a << (b & 31),
                          0x2: 1 if s32(a) < s32(b) else 0,
                          0x3: 1 if (a & MASK32) < (b & MASK32) else 0,
                          0x4: a ^ b, 0x5: (a & MASK32) >> (b & 31),
                          0x6: a | b, 0x7: a & b}[f3]
                elif f7 == 0x20 and f3 == 0x0:
                    wb = a - b
                elif f7 == 0x20 and f3 == 0x5:
                    wb = s32(a) >> (b & 31)
                else:
                    raise RuntimeError('ISS：非法 R 型 @%08x (%08x)' % (pc, inst))

            elif op == 0x13:                                      # I 型 / 移位立即数
                imm = imm_i(inst)
                if f3 == 0x0:
                    wb = a + imm
                elif f3 == 0x2:
                    wb = 1 if s32(a) < imm else 0
                elif f3 == 0x3:
                    wb = 1 if (a & MASK32) < (imm & MASK32) else 0
                elif f3 == 0x4:
                    wb = a ^ imm
                elif f3 == 0x6:
                    wb = a | imm
                elif f3 == 0x7:
                    wb = a & imm
                elif f3 == 0x1:
                    wb = a << ((inst >> 20) & 0x1F)
                elif f3 == 0x5:
                    sh = (inst >> 20) & 0x1F
                    wb = (s32(a) >> sh) if (f7 & 0x20) else ((a & MASK32) >> sh)
                else:
                    raise RuntimeError('ISS：非法 I 型 @%08x (%08x)' % (pc, inst))

            elif op == 0x03:                                      # load
                addr = (a + imm_i(inst)) & MASK32
                size = 4 if f3 == 2 else (2 if f3 in (1, 5) else 1)
                wb = self.ld(addr, size, f3 in (0, 1, 2))

            elif op == 0x23:                                      # store
                addr = (a + imm_s(inst)) & MASK32
                size = 4 if f3 == 2 else (2 if f3 == 1 else 1)
                self.st(addr, size, b)

            elif op == 0x63:                                      # branch
                imm = imm_b(inst)
                take = {0x0: a == b, 0x1: a != b,
                        0x4: s32(a) < s32(b), 0x5: s32(a) >= s32(b),
                        0x6: (a & MASK32) < (b & MASK32),
                        0x7: (a & MASK32) >= (b & MASK32)}[f3]
                if take:
                    nxt = (pc + imm) & MASK32

            elif op == 0x37:                                      # lui
                wb = inst & 0xFFFFF000

            elif op == 0x17:                                      # auipc
                wb = (pc + (inst & 0xFFFFF000)) & MASK32

            elif op == 0x6F:                                      # jal
                imm = imm_j(inst)
                tgt = (pc + imm) & MASK32
                if rd == 0 and tgt == pc:                         # 自环 jal x0 -> 停机
                    self.itrace.append((pc, inst))
                    self.halt_pc = pc
                    return self
                wb = pc + 4
                nxt = tgt

            elif op == 0x67:                                      # jalr
                tgt = (a + imm_i(inst)) & ~1 & MASK32
                wb = pc + 4
                nxt = tgt

            else:
                raise RuntimeError('ISS：DUT 未实现的 opcode %02x @%08x (%08x)' % (op, pc, inst))

            self.itrace.append((pc, inst))
            if wb is not None and rd != 0:
                self.rf[rd] = wb & MASK32
                self.wbtrace.append((pc, rd, wb & MASK32))
            self.pc = nxt


# ---------------------------------------------------------------- 反汇编(仅给人看)

def disasm(w, addr, sym_rev):
    op = w & 0x7F
    rd = (w >> 7) & 0x1F
    f3 = (w >> 12) & 0x7
    rs1 = (w >> 15) & 0x1F
    rs2 = (w >> 20) & 0x1F
    f7 = (w >> 25) & 0x7F

    def lbl(t):
        return sym_rev.get(t, '%08x' % t)

    if op == 0x33:
        mn = {0x0: 'add', 0x1: 'sll', 0x2: 'slt', 0x3: 'sltu', 0x4: 'xor',
              0x5: 'srl', 0x6: 'or', 0x7: 'and'}.get(f3, '??')
        if f7 == 0x20:
            mn = {0x0: 'sub', 0x5: 'sra'}.get(f3, mn)
        return '%s x%d, x%d, x%d' % (mn, rd, rs1, rs2)
    if op == 0x13:
        mn = {0x0: 'addi', 0x1: 'slli', 0x2: 'slti', 0x3: 'sltiu',
              0x4: 'xori', 0x5: 'srli', 0x6: 'ori', 0x7: 'andi'}.get(f3, '??')
        if f3 == 5 and f7 == 0x20:
            mn = 'srai'
        if f3 in (1, 5):
            return '%s x%d, x%d, %d' % (mn, rd, rs1, (w >> 20) & 0x1F)
        return '%s x%d, x%d, %d' % (mn, rd, rs1, imm_i(w))
    if op == 0x03:
        mn = {0x0: 'lb', 0x1: 'lh', 0x2: 'lw', 0x4: 'lbu', 0x5: 'lhu'}.get(f3, '??')
        return '%s x%d, %d(x%d)' % (mn, rd, imm_i(w), rs1)
    if op == 0x23:
        mn = {0x0: 'sb', 0x1: 'sh', 0x2: 'sw'}.get(f3, '??')
        return '%s x%d, %d(x%d)' % (mn, rs2, imm_s(w), rs1)
    if op == 0x63:
        mn = {0x0: 'beq', 0x1: 'bne', 0x4: 'blt', 0x5: 'bge', 0x6: 'bltu', 0x7: 'bgeu'}.get(f3, '??')
        return '%s x%d, x%d, %s' % (mn, rs1, rs2, lbl((addr + imm_b(w)) & MASK32))
    if op == 0x37:
        return 'lui x%d, 0x%x' % (rd, w >> 12)
    if op == 0x17:
        return 'auipc x%d, 0x%x' % (rd, w >> 12)
    if op == 0x6F:
        return 'jal x%d, %s' % (rd, lbl((addr + imm_j(w)) & MASK32))
    if op == 0x67:
        return 'jalr x%d, x%d, %d' % (rd, rs1, imm_i(w))
    return '.word 0x%08x' % w


# ---------------------------------------------------------------- 输出

def write_hex(path, words, n):
    with open(path, 'w') as f:
        for i in range(n):
            f.write('%08x\n' % (words.get(i * 4, 0) & MASK32))


def cmd_assemble(src, build_dir):
    """只汇编并生成存储器镜像，不运行不认识MMIO语义的黄金ISS。"""
    os.makedirs(build_dir, exist_ok=True)
    text = open(src, encoding='utf-8').read()

    asm = Assembler()
    prog = asm.assemble(text)
    sym_rev = {v: k for k, v in asm.sym.items()}

    with open(os.path.join(build_dir, 'prog.lst'), 'w', encoding='utf-8') as f:
        f.write('# 地址      机器码     源码 / 反汇编\n')
        for (a, hx, raw) in asm.listing:
            if hx is None:
                f.write('%08x  ---------- %s\n' % (a, raw.strip()))
            else:
                f.write('%08x  %s  %-28s ; %s\n'
                        % (a, hx, raw.strip(), disasm(int(hx, 16), a, sym_rev)))

    write_hex(os.path.join(build_dir, 'rom.hex'), prog, BRAM_WORDS)
    write_hex(os.path.join(build_dir, 'ram.hex'), {}, BRAM_WORDS)
    print('== 汇编完成：%s ==' % os.path.basename(src))
    print('   指令数 = %d' % len(prog))
    print('   -> rom.hex / ram.hex / prog.lst')


def cmd_build(src, build_dir):
    os.makedirs(build_dir, exist_ok=True)
    text = open(src, encoding='utf-8').read()

    asm = Assembler()
    prog = asm.assemble(text)
    sym_rev = {v: k for k, v in asm.sym.items()}

    with open(os.path.join(build_dir, 'prog.lst'), 'w', encoding='utf-8') as f:
        f.write('# 地址      机器码     源码 / 反汇编\n')
        for (a, hx, raw) in asm.listing:
            if hx is None:
                f.write('%08x  ---------- %s\n' % (a, raw.strip()))
            else:
                f.write('%08x  %s  %-28s ; %s\n'
                        % (a, hx, raw.strip(), disasm(int(hx, 16), a, sym_rev)))

    write_hex(os.path.join(build_dir, 'rom.hex'), prog, ROM_WORDS)
    write_hex(os.path.join(build_dir, 'ram.hex'), {}, ROM_WORDS)

    imem = [prog.get(i * 4, 0) for i in range(ROM_WORDS)]
    iss = ISS(imem)
    iss.run()
    if iss.halt_pc is None:
        raise RuntimeError('程序没有停机标记（请用 "halt: jal x0, halt" 结尾）')

    with open(os.path.join(build_dir, 'trace.txt'), 'w') as f:
        f.write('%08x %08x\n' % (iss.halt_pc, len(iss.wbtrace)))
        for (pc, wn, wd) in iss.wbtrace:
            f.write('%08x %02x %08x\n' % (pc, wn, wd))

    with open(os.path.join(build_dir, 'itrace.txt'), 'w') as f:
        f.write('%08x %08x\n' % (iss.halt_pc, len(iss.itrace)))
        for (pc, ins) in iss.itrace:
            f.write('%08x %08x\n' % (pc, ins))

    with open(os.path.join(build_dir, 'rf_golden.txt'), 'w') as f:
        f.write('%08x\n' % 32)
        for i in range(32):
            f.write('%02x %08x\n' % (i, iss.rf[i]))

    with open(os.path.join(build_dir, 'mem_golden.txt'), 'w') as f:
        f.write('%08x\n' % ROM_WORDS)
        for i in range(ROM_WORDS):
            w = int.from_bytes(iss.dmem[i * 4:i * 4 + 4], 'little')
            f.write('%04x %08x\n' % (i, w))

    print('== 黄金模型完成：%s ==' % os.path.basename(src))
    print('   halt_pc  = %08x' % iss.halt_pc)
    print('   执行指令 = %d 条' % len(iss.itrace))
    print('   写回事件 = %d 次' % len(iss.wbtrace))
    nz = ['x%d=%08x' % (i, iss.rf[i]) for i in range(1, 32) if iss.rf[i]]
    print('   最终非零寄存器：%s' % (', '.join(nz) if nz else '(无)'))
    nzm = [(i, int.from_bytes(iss.dmem[i * 4:i * 4 + 4], 'little')) for i in range(ROM_WORDS)]
    nzm = [t for t in nzm if t[1]]
    print('   最终非零内存字：%d 个 %s'
          % (len(nzm), ' '.join('mem[%d]=%08x' % t for t in nzm[:8])))
    print('   -> rom.hex / ram.hex / trace.txt / itrace.txt / rf_golden.txt / mem_golden.txt / prog.lst')


def cmd_check(build_dir):
    bad = 0
    for tag, dutf, gldf in (('寄存器堆', 'rf_dut.txt', 'rf_golden.txt'),
                            ('数据存储器', 'mem_dut.txt', 'mem_golden.txt')):
        dp = os.path.join(build_dir, dutf)
        gp = os.path.join(build_dir, gldf)
        if not os.path.exists(dp):
            print('  [跳过] 没找到 %s —— DUT 仿真可能没跑到结束' % dutf)
            bad += 1
            continue
        d = [l.split() for l in open(dp) if l.strip()][1:]
        g = [l.split() for l in open(gp) if l.strip()][1:]
        n = min(len(d), len(g))
        diff = [k for k in range(n) if int(d[k][1], 16) != int(g[k][1], 16)]
        if diff:
            print('  [FAIL] %s 终值不一致：共 %d 处，前 8 处：' % (tag, len(diff)))
            for k in diff[:8]:
                print('         idx=%-6s DUT=%s  黄金=%s' % (d[k][0], d[k][1], g[k][1]))
            bad += 1
        else:
            print('  [ OK ] %s 终值一致（%d 项）' % (tag, n))
    return 0 if bad == 0 else 1


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 2
    if sys.argv[1] == 'build':
        cmd_build(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'build')
        return 0
    if sys.argv[1] == 'asm':
        cmd_assemble(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else 'build')
        return 0
    if sys.argv[1] == 'check':
        return cmd_check(sys.argv[2] if len(sys.argv) > 2 else 'build')
    print('未知子命令 %r' % sys.argv[1])
    return 2


if __name__ == '__main__':
    sys.exit(main())
