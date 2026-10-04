#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
rv32i_tool.py —— RV32I 指令速查 / 反汇编工具

用法:
    python rv32i_tool.py              # 打印完整指令表(地址/指令/反汇编/做什么)
    python rv32i_tool.py --dis        # 反汇编内置的程序(等价于上面的"程序"部分)
    python rv32i_tool.py 0x00f00093   # 反汇编单条编码
    python rv32i_tool.py 00f00093 00a00113 ...   # 反汇编一串编码

设计要点(与 mycpu_sync.v 的译码保持一致):
  · RV32I 六种指令格式 R / I / S / B / U / J
  · 立即数符号扩展;x0 恒 0
  · 真 NOP = addi x0,x0,0 = 0x0000_0013
"""

import sys
import io

# Windows 控制台编码兜底
try:
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
except Exception:
    pass


# ==========================================================================
# 一、编码器(把汇编意图编成 32 位机器码)
# ==========================================================================
def R(f3, f7, rd, rs1, rs2, op=0x33):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def I(imm, rd, rs1, f3=0b000, op=0x13):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def S(imm, rs2, rs1, f3=0b010, op=0x23):
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) \
         | (f3 << 12) | ((imm & 0x1F) << 7) | op


def B(imm, rs2, rs1, f3, op=0x63):
    i = imm & 0x1FFF
    return (((i >> 12) & 1) << 31) | (((i >> 5) & 0x3F) << 25) | (rs2 << 20) \
         | (rs1 << 15) | (f3 << 12) | (((i >> 1) & 0xF) << 8) \
         | (((i >> 11) & 1) << 7) | op


def U(imm20, rd, op=0x37):
    return (imm20 << 12) | (rd << 7) | op


def J(imm, rd, op=0x6F):
    i = imm & 0x1FFFFF
    return (((i >> 20) & 1) << 31) | (((i >> 1) & 0x3FF) << 21) \
         | (((i >> 11) & 1) << 20) | (((i >> 12) & 0xFF) << 12) \
         | (rd << 7) | op


def pad(s, width):
    """按显示宽度对齐:CJK 字符占 2 列,ASCII 占 1 列"""
    w = 0
    for ch in s:
        w += 2 if ('\u4e00' <= ch <= '\u9fff' or '\uff00' <= ch <= '\uffef') else 1
    return s + " " * max(0, width - w)


# ==========================================================================
# 二、译码器(32 位机器码 → 助记符 + 操作数说明 + "做了什么")
# ==========================================================================

def sx(v, bits):
    """把 bits 位的无符号数按二补数符号扩展成 Python 整数"""
    m = 1 << (bits - 1)
    return (v ^ m) - m


def reg(i):
    return "x%d" % i


def imm_str(v):
    """立即数显示:正数用 0x 十六进制 + 十进制,负数用十进制"""
    if v < 0:
        return "%d" % v
    return "0x%X" % v


def expand(inst):
    """
    伪指令识别:识别汇编器会生成的常见伪指令写法。
    返回 (asm, pseudo) —— asm 是真实指令, pseudo 是等价的伪指令写法(None 表示无)。
    判定从严到宽:先认最特殊的写法,再退化到通用写法。
    """
    op = inst & 0x7F
    rd = (inst >> 7) & 0x1F
    rs1 = (inst >> 15) & 0x1F
    f3 = (inst >> 12) & 0x7
    f7 = (inst >> 25) & 0x7F
    imm12 = (inst >> 20) & 0xFFF
    simm = sx(imm12, 12)

    if inst == 0x00000013:                      # addi x0,x0,0
        return ("addi x0, x0, 0x0", "nop")
    if inst == 0x00008067:                      # jalr x0,0(x1)
        return ("jalr x0, 0x0(x1)", "ret")
    if op == 0b1101111 and rd == 0:             # jal x0,imm
        return (None, "j    <imm>")
    if op == 0b0010011 and f3 == 0b000:
        # inc:addi rd,rd,1
        if rd == rs1 and simm == 1:
            return ("addi x%d, x%d, 0x1" % (rd, rs1), "inc  x%d" % rd)
        # dec:addi rd,rd,-1
        if rd == rs1 and simm == -1:
            return ("addi x%d, x%d, -1" % (rd, rs1), "dec  x%d" % rd)
        # li:addi rd,x0,imm  → 显示有符号立即数更贴近汇编写法
        if rs1 == 0:
            return ("addi x%d, x0, %s" % (rd, imm_str(simm)),
                    "li   x%d, %s" % (rd, imm_str(simm)))
        # mv:addi rd,rs1,0
        if imm12 == 0 and f7 == 0x00:
            return ("addi x%d, x%d, 0x0" % (rd, rs1), "mv   x%d, x%d" % (rd, rs1))
        # seqz / snez 这类经典单指令伪指令
        if f3 == 0b000 and rs1 == rd:
            pass
    return (None, None)


def _decode_core(inst):
    """
    返回 dict:
      kind    : 格式类型 R/I/S/B/U/J/?
      asm     : 反汇编文本
      target  : 跳转/分支目标偏移(仅 B/J 型有),否则 None
      what    : 这条指令"做了什么"的自然语言描述
    """
    op = inst & 0x7F
    rd = (inst >> 7) & 0x1F
    f3 = (inst >> 12) & 0x7
    rs1 = (inst >> 15) & 0x1F
    rs2 = (inst >> 20) & 0x1F
    f7 = (inst >> 25) & 0x7F

    # ---- 立即数六种生成方式 ----
    i_imm = sx((inst >> 20) & 0xFFF, 12)
    s_imm = sx(((inst >> 25) << 5) | ((inst >> 7) & 0x1F), 12)
    b_imm = sx((((inst >> 31) & 1) << 12) | (((inst >> 7) & 1) << 11)
               | (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1), 13)
    u_imm = inst & 0xFFFFF000
    j_imm = sx((((inst >> 31) & 1) << 20) | (((inst >> 12) & 0xFF) << 12)
               | (((inst >> 20) & 1) << 11) | (((inst >> 21) & 0x3FF) << 1), 21)
    shamt = (inst >> 20) & 0x1F

    R_ALU = {
        (0b000, 0x00): ("add",  "rd = rs1 + rs2          (算术加,忽略溢出)"),
        (0b000, 0x20): ("sub",  "rd = rs1 - rs2          (算术减)"),
        (0b001, 0x00): ("sll",  "rd = rs1 << rs2[4:0]    (逻辑左移)"),
        (0b010, 0x00): ("slt",  "rd = (rs1 < rs2) ? 1:0  (有符号比较小于)"),
        (0b011, 0x00): ("sltu", "rd = (rs1 < rs2) ? 1:0  (无符号比较小于)"),
        (0b100, 0x00): ("xor",  "rd = rs1 ^ rs2          (按位异或)"),
        (0b101, 0x00): ("srl",  "rd = rs1 >> rs2[4:0]    (逻辑右移,高位补0)"),
        (0b101, 0x20): ("sra",  "rd = rs1 >>> rs2[4:0]   (算术右移,高位补符号)"),
        (0b110, 0x00): ("or",   "rd = rs1 | rs2          (按位或)"),
        (0b111, 0x00): ("and",  "rd = rs1 & rs2          (按位与)"),
    }
    I_ALU = {
        0b000: ("addi",  "rd = rs1 + sext(imm)     (立即数加)"),
        0b010: ("slti",  "rd = (rs1 < sext(imm)) ? 1:0 (有符号)"),
        0b011: ("sltiu", "rd = (rs1 < sext(imm)) ? 1:0 (无符号比较)"),
        0b100: ("xori",  "rd = rs1 ^ sext(imm)     (立即数异或)"),
        0b110: ("ori",   "rd = rs1 | sext(imm)     (立即数或)"),
        0b111: ("andi",  "rd = rs1 & sext(imm)     (立即数与)"),
    }
    SHIFT_I = {
        (0b001, 0x00): ("slli", "rd = rs1 << shamt        (立即数逻辑左移)"),
        (0b101, 0x00): ("srli", "rd = rs1 >> shamt        (立即数逻辑右移)"),
        (0b101, 0x20): ("srai", "rd = rs1 >>> shamt       (立即数算术右移)"),
    }
    LOAD = {
        0b000: ("lb",  "rd = sext(mem[rs1+imm][7:0])    (读字节,符号扩展)"),
        0b001: ("lh",  "rd = sext(mem[rs1+imm][15:0])   (读半字,符号扩展)"),
        0b010: ("lw",  "rd = mem[rs1+imm]               (读字,32 位)"),
        0b100: ("lbu", "rd = zext(mem[rs1+imm][7:0])    (读字节,零扩展)"),
        0b101: ("lhu", "rd = zext(mem[rs1+imm][15:0])   (读半字,零扩展)"),
    }
    STORE = {
        0b000: ("sb", "mem[rs1+imm][7:0]   = rs2[7:0]    (写字节)"),
        0b001: ("sh", "mem[rs1+imm][15:0]  = rs2[15:0]   (写半字)"),
        0b010: ("sw", "mem[rs1+imm]        = rs2         (写字)"),
    }
    BRANCH = {
        0b000: ("beq",  "if (rs1 == rs2) pc += imm      (相等则跳)"),
        0b001: ("bne",  "if (rs1 != rs2) pc += imm      (不等则跳)"),
        0b100: ("blt",  "if (rs1 <  rs2) pc += imm      (有符号小于则跳)"),
        0b101: ("bge",  "if (rs1 >= rs2) pc += imm      (有符号大于等于则跳)"),
        0b110: ("bltu", "if (rs1 <  rs2) pc += imm      (无符号小于则跳)"),
        0b111: ("bgeu", "if (rs1 >= rs2) pc += imm      (无符号大于等于则跳)"),
    }

    # ---------- opcode 0000011:load ----------
    if op == 0b0000011 and f3 in LOAD:
        m, what = LOAD[f3]
        return dict(kind='I', asm="%s %s, %s(%s)" % (m, reg(rd), imm_str(i_imm), reg(rs1)),
                    target=None, what=what)
    # ---------- opcode 0100011:store ----------
    if op == 0b0100011 and f3 in STORE:
        m, what = STORE[f3]
        return dict(kind='S', asm="%s %s, %s(%s)" % (m, reg(rs2), imm_str(s_imm), reg(rs1)),
                    target=None, what=what)
    # ---------- opcode 0110011:R 型 ----------
    if op == 0b0110011 and (f3, f7) in R_ALU:
        m, what = R_ALU[(f3, f7)]
        return dict(kind='R', asm="%s %s, %s, %s" % (m, reg(rd), reg(rs1), reg(rs2)),
                    target=None, what=what)
    # ---------- opcode 0010011:立即数 ALU / 移位 ----------
    if op == 0b0010011:
        if (f3, f7) in SHIFT_I:
            m, what = SHIFT_I[(f3, f7)]
            return dict(kind='I', asm="%s %s, %s, %d" % (m, reg(rd), reg(rs1), shamt),
                        target=None, what=what)
        if f3 in I_ALU:
            m, what = I_ALU[f3]
            return dict(kind='I', asm="%s %s, %s, %s" % (m, reg(rd), reg(rs1), imm_str(i_imm)),
                        target=None, what=what)
    # ---------- opcode 0110111:lui ----------
    if op == 0b0110111:
        return dict(kind='U', asm="lui %s, 0x%X" % (reg(rd), u_imm >> 12),
                    target=None, what="rd = imm << 12             (装入 20 位立即数到高 20 位,低 12 位清零)")
    # ---------- opcode 0010111:auipc ----------
    if op == 0b0010111:
        return dict(kind='U', asm="auipc %s, 0x%X" % (reg(rd), u_imm >> 12),
                    target=None, what="rd = pc + (imm << 12)       (当前 PC 加高位立即数,用于 PC 相对寻址)")
    # ---------- opcode 1101111:jal ----------
    if op == 0b1101111:
        return dict(kind='J', asm="jal %s, %s" % (reg(rd), imm_str(j_imm)),
                    target=j_imm,
                    what="rd = pc + 4;  pc += imm    (跳转,并把返回地址 pc+4 存 rd)")
    # ---------- opcode 1100111:jalr ----------
    if op == 0b1100111 and f3 == 0b000:
        return dict(kind='I', asm="jalr %s, %s(%s)" % (reg(rd), imm_str(i_imm), reg(rs1)),
                    target=None,
                    what="rd = pc + 4;  pc = (rs1+imm) & ~1  (间接跳转,目标地址最低位清零)")
    # ---------- opcode 1100011:分支 ----------
    if op == 0b1100011 and f3 in BRANCH:
        m, what = BRANCH[f3]
        return dict(kind='B', asm="%s %s, %s, %s" % (m, reg(rs1), reg(rs2), imm_str(b_imm)),
                    target=b_imm, what=what)
    # ---------- opcode 0001111:fence ----------
    if op == 0b0001111 and f3 == 0b000:
        return dict(kind='I', asm="fence", target=None,
                    what="内存/IO 读写顺序屏障(本 CPU 未实现,当 NOP)")
    # ---------- opcode 1110011:系统 ----------
    if op == 0b1110011:
        if inst == 0x00000073:
            return dict(kind='I', asm="ecall", target=None,
                        what="环境调用(陷入系统/陷入异常,本 CPU 未实现)")
        if inst == 0x00100073:
            return dict(kind='I', asm="ebreak", target=None,
                        what="断点(调试陷阱,本 CPU 未实现)")
        if f3 == 0b000:
            return dict(kind='I', asm="csrrw/csrrs/... (未实现)", target=None,
                        what="CSR 访问(本 CPU 未实现)")
    # ---------- 全零:非法 ----------
    if inst == 0:
        return dict(kind='?', asm="<非法指令 0x00000000>", target=None,
                    what="0x0000_0000 不是 NOP!真 NOP 是 addi x0,x0,0 = 0x0000_0013")
    return dict(kind='?', asm="<未实现/非法编码>", target=None,
                what="不在本 RV32I 子集内")


def decode(inst):
    """对 _decode_core 包一层,补上 pseudo(等价伪指令)字段"""
    d = _decode_core(inst)
    d['pseudo'] = expand(inst)[1]
    return d


# ==========================================================================
# 三、指令表(带地址 → 用一条条真实指令拼出程序)
# ==========================================================================

def build_program():
    """
    返回 [(地址, 编码, 汇编源码), ...]
    分成几组,每组演示一类指令。
    """
    prog = []
    a = 0x0000_0000

    def emit(code, src):
        nonlocal a
        prog.append((a, code, src))
        a += 4

    # ---- A. 算术/逻辑(U 型 + I 型 + R 型) ----
    emit(U(0x12345, 10),     "lui   x10, 0x12345")
    emit(U(0x00001, 11, 0x17),"auipc x11, 0x1")
    emit(I(0x00A, 1, 0),     "addi  x1, x0, 10")
    emit(I(0x014, 2, 0),     "addi  x2, x0, 20")
    emit(R(0b000, 0x00, 3, 1, 2), "add   x3, x1, x2")
    emit(R(0b000, 0x20, 4, 2, 1), "sub   x4, x2, x1")
    emit(R(0b111, 0x00, 5, 1, 2), "and   x5, x1, x2")
    emit(R(0b110, 0x00, 6, 1, 2), "or    x6, x1, x2")
    emit(R(0b100, 0x00, 7, 1, 2), "xor   x7, x1, x2")
    emit(R(0b001, 0x00, 8, 1, 2), "sll   x8, x1, x2")
    emit(R(0b101, 0x00, 9, 1, 2), "srl   x9, x1, x2")
    emit(R(0b010, 0x00, 12, 1, 2),"slt   x12, x1, x2")
    emit(R(0b011, 0x00, 13, 1, 2),"sltu  x13, x1, x2")

    # ---- B. 立即数运算 + 移位立即数 ----
    emit(I(0x7FF, 14, 0),         "addi  x14, x0, 0x7FF")
    emit(I(0xFFF, 15, 0),         "addi  x15, x0, -1")
    emit(I(0x004, 16, 15, 0b001), "slli  x16, x15, 4")
    emit(I(0x01C, 17, 15, 0b101), "srli  x17, x15, 28")
    emit(I(0x401, 18, 15, 0b101), "srai  x18, x15, 1")

    # ---- C. 访存 ----
    emit(S(0x004, 1, 0),          "sw    x1, 4(x0)")
    emit(S(0x008, 2, 0),          "sw    x2, 8(x0)")
    emit(I(0x004, 19, 0, 0b010, 0x03), "lw    x19, 4(x0)")
    emit(I(0x005, 20, 0, 0b000, 0x03), "lb    x20, 5(x0)")
    emit(I(0x004, 21, 0, 0b100, 0x03), "lbu   x21, 4(x0)")
    emit(S(0x00C, 1, 0),          "sw    x1, 12(x0)")

    # ---- D. 分支 ----
    emit(B(12, 2, 1, 0b000),  "beq   x1, x2, +12")
    emit(B(8,  2, 1, 0b001),  "bne   x1, x2, +8")
    emit(B(4,  2, 1, 0b100),  "blt   x1, x2, +4")
    emit(B(4,  2, 1, 0b101),  "bge   x1, x2, +4")
    emit(B(4,  2, 1, 0b110),  "bltu  x1, x2, +4")
    emit(B(4,  2, 1, 0b111),  "bgeu  x1, x2, +4")

    # ---- E. 跳转 ----
    emit(J(0x00000010, 1),    "jal   x1, +16")
    emit(I(0x020, 1, 1, 0b000, 0x67), "jalr  x1, x1, 0x20")

    # ---- F. 伪指令 / 特殊 ----
    emit(I(0x000, 0, 0),      "nop")
    emit(I(0x000, 5, 0),      "li    x5, 0")
    emit(I(0x001, 6, 6),      "inc   x6")
    emit(I(0xFFF, 7, 7),      "dec   x7")
    emit(I(0x000, 8, 9),      "mv    x8, x9")
    emit(0x00008067,          "ret")
    emit(0x00000073,          "ecall")
    emit(0x00100073,          "ebreak")

    return prog


# ==========================================================================
# 四、输出
# ==========================================================================

def show_table(prog):
    print("=" * 132)
    print("RV32I 指令表  (地址 | 机器码 | 汇编源码 | 反汇编 | 格式 | 伪指令 | 这条指令做了什么)")
    print("=" * 132)
    print(pad("地址", 10) + pad("机器码", 10) + pad("汇编源码", 30)
          + pad("反汇编", 26) + pad("格式", 6) + pad("伪指令", 12) + "这条指令做了什么")
    print("-" * 132)
    for addr, code, src in prog:
        d = decode(code)
        print("0x%08X  " % addr + "0x%08X  " % code
              + pad(src, 30) + pad(d['asm'], 26) + pad(d['kind'], 6)
              + pad(d['pseudo'] or "-", 14) + d['what'])
    print("-" * 132)
    print("共 %d 条,占用 0x%X 字节" % (len(prog), len(prog) * 4))


def show_word(hexs):
    """反汇编命令行给的一串编码"""
    print("=" * 124)
    print(pad("地址", 10) + pad("机器码", 10) + pad("反汇编", 26)
          + pad("格式", 6) + pad("伪指令", 12) + "做了什么")
    print("-" * 124)
    for i, h in enumerate(hexs):
        try:
            code = int(h, 16) & 0xFFFFFFFF
        except ValueError:
            print("跳过无法解析的输入: %s" % h)
            continue
        d = decode(code)
        print("0x%08X  " % (i * 4) + "0x%08X  " % code
              + pad(d['asm'], 26) + pad(d['kind'], 6)
              + pad(d['pseudo'] or "-", 14) + d['what'])
    print("=" * 124)


def show_markdown(prog):
    """输出 Markdown 表格,方便直接贴进文档"""
    print("| 地址 | 机器码 | 汇编源码 | 反汇编 | 格式 | 伪指令 | 这条指令做了什么 |")
    print("|---|---|---|---|---|---|---|")
    for addr, code, src in prog:
        d = decode(code)
        print("| `0x%08X` | `0x%08X` | `%s` | `%s` | %s | %s | %s |"
              % (addr, code, src, d['asm'], d['kind'],
                 ("`%s`" % d['pseudo']) if d['pseudo'] else "—", d['what']))
    print()
    print("共 %d 条,占用 0x%X 字节" % (len(prog), len(prog) * 4))


def dump_file(path, text):
    """把文本按 UTF-8 写文件(绕过 Windows 控制台编码问题)"""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def selftest():
    """
    往返自检:每条指令"汇编源码 → 编码 → 反汇编",看助记符是否对得上。
    伪指令允许源码写伪指令形式(nop/li/inc/dec/mv/ret),此时比对 pseudo 列。
    用来保证编码器和译码器没有互相漂移。
    """
    ok = bad = 0
    print("=== 编码/译码 往返自检 ===")
    for addr, code, src in build_program():
        d = decode(code)
        mnem = src.split()[0].strip()
        got = d['asm'].split()[0].strip()
        # 源码若是伪指令形式,则与 pseudo 列比对
        pseudo_mnem = (d['pseudo'] or "").split()[0].strip() if d['pseudo'] else ""
        good = (mnem == got) or (pseudo_mnem != "" and mnem == pseudo_mnem)
        if good:
            ok += 1
        else:
            bad += 1
            print("  [FAIL] @0x%08X  %-28s -> 0x%08X -> %s (pseudo=%s)"
                  % (addr, src, code, d['asm'], d['pseudo']))
    print("通过 %d 条,失败 %d 条" % (ok, bad))

    # 再跑一批边界编码(立即数符号扩展 / 负数偏移)
    edge = [
        (0x00000013, "addi"), (0x00000000, "非法"), (0xFFFFFFFF, "未实现"),
        (0x00008067, "jalr"), (0x00000073, "ecall"), (0x00100073, "ebreak"),
        (I(-2048, 1, 0), "addi 负立即数下界"),
        (I(2047, 1, 0), "addi 正立即数上界"),
        (J(-8, 1), "jal 负偏移"), (B(-4, 1, 2, 0b000), "beq 负偏移"),
        (J(0x7FFFF << 1, 1), "jal 正偏移上界"),
    ]
    print("--- 边界编码 ---")
    for c, tag in edge:
        d = decode(c)
        print("  0x%08X  %-26s %-3s %s" % (c, d['asm'], d['kind'], tag))


def main():
    # Windows 控制台把 stdout 重定向时会按本地代码页重新编码,中文会乱码。
    # 统一改成 UTF-8,并在极端情况下退回 errors='replace' 防崩。
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

    args = sys.argv[1:]
    # --selftest:编码 → 译码 往返一致性自检
    if args and args[0] == "--selftest":
        selftest()
        return

    # --out <file>:把命令行编码的反汇编结果写文件(绕开 Windows 控制台编码)
    if len(args) >= 2 and args[0] == "--out":
        import os, io as _io, contextlib
        base = os.path.dirname(os.path.abspath(__file__))
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            show_word(args[2:])
        dump_file(os.path.join(base, args[1]), buf.getvalue())
        print("已写出: %s" % os.path.join(base, args[1]))
        return
    if args and args[0] == "--save":
        # 把表格和 Markdown 都按 UTF-8 写盘(Windows 控制台中文会乱码)
        import os, io as _io, contextlib
        base = os.path.dirname(os.path.abspath(__file__))
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            show_table(build_program())
            print()
            show_markdown(build_program())
        out = os.path.join(base, "rv32i_table.txt")
        dump_file(out, buf.getvalue())

        # 单独再写一份纯 Markdown,供文档引用
        buf2 = _io.StringIO()
        with contextlib.redirect_stdout(buf2):
            show_markdown(build_program())
        docdir = os.path.normpath(os.path.join(base, "..", "..", "doc"))
        if os.path.isdir(docdir):
            dump_file(os.path.join(docdir, "RV32I指令速查表.md"), buf2.getvalue())
        print("已写出: %s" % out)
        return
    if args and args[0] == "--md":
        # 直接写 Markdown 到 stdout 会被 Windows 控制台编码破坏,
        # 所以 --md 也走文件输出
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        out = os.path.join(base, "rv32i_table.md")
        import io as _io, contextlib
        buf = _io.StringIO()
        with contextlib.redirect_stdout(buf):
            show_markdown(build_program())
        dump_file(out, buf.getvalue())
        print("已写出: %s" % out)
        return
    if args and args[0] in ("--dis", "-d"):
        show_table(build_program())
        return
    args = [a for a in args if a not in ("--hex", "-x")]
    if args:
        show_word(args)
        return
    show_table(build_program())


if __name__ == "__main__":
    main()
