"""Minimal RV32I assembler for the branch/EX-redirect regression.

Supports only the instructions the directed tests need, plus the `li`, `la`
and `nop` pseudo forms. Emits imem.hex / dmem_init.hex / program.lst.
"""
from pathlib import Path
import sys

REGS = {f"x{i}": i for i in range(32)}
REGS.update({
    "zero": 0, "ra": 1, "sp": 2, "gp": 3, "tp": 4, "t0": 5, "t1": 6, "t2": 7,
    "s0": 8, "s1": 9, "a0": 10, "a1": 11, "a2": 12, "a3": 13, "a4": 14,
    "a5": 15, "a6": 16, "a7": 17, "s2": 18, "s3": 19, "s4": 20, "s5": 21,
    "s6": 22, "s7": 23, "s8": 24, "s9": 25, "s10": 26, "s11": 27,
    "t3": 28, "t4": 29, "t5": 30, "t6": 31,
})

CSRS = {
    "mstatus": 0x300, "misa": 0x301, "mie": 0x304, "mtvec": 0x305,
    "mscratch": 0x340, "mepc": 0x341, "mcause": 0x342, "mtval": 0x343,
    "mip": 0x344, "mhartid": 0xF14, "mcycle": 0xB00, "minstret": 0xB02,
}


def csr_num(tok):
    tok = tok.strip()
    return CSRS.get(tok, None) if tok in CSRS else parse_imm(tok)

R_OPS = {    "add": (0x00, 0), "sub": (0x20, 0), "sll": (0x00, 1), "slt": (0x00, 2),
    "sltu": (0x00, 3), "xor": (0x00, 4), "srl": (0x00, 5), "sra": (0x20, 5),
    "or": (0x00, 6), "and": (0x00, 7),
}
I_OPS = {"addi": 0, "slti": 2, "sltiu": 3, "xori": 4, "ori": 6, "andi": 7}
SHIFT_I = {"slli": 1, "srli": 5, "srai": 5}
LOAD = {"lb": 0, "lh": 1, "lw": 2, "lbu": 4, "lhu": 5}
STORE = {"sb": 0, "sh": 1, "sw": 2}
BRANCH = {"beq": 0, "bne": 1, "blt": 4, "bge": 5, "bltu": 6, "bgeu": 7}


def r_type(rd, rs1, rs2, f3, f7, op=0x33):
    return (f7 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def i_type(rd, rs1, imm, f3, op):
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (f3 << 12) | (rd << 7) | op


def s_type(rs2, rs1, imm, f3, op=0x23):
    imm &= 0xFFF
    return (((imm >> 5) & 0x7F) << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | ((imm & 0x1F) << 7) | op


def b_type(rs1, rs2, imm, f3):
    imm &= 0x1FFF
    b12 = (imm >> 12) & 1
    b11 = (imm >> 11) & 1
    b10_5 = (imm >> 5) & 0x3F
    b4_1 = (imm >> 1) & 0xF
    return (b12 << 31) | (b10_5 << 25) | (rs2 << 20) | (rs1 << 15) | (f3 << 12) | (b4_1 << 8) | (b11 << 7) | 0x63


def u_type(rd, imm20, op=0x37):
    return ((imm20 & 0xFFFFF) << 12) | (rd << 7) | op


def j_type(rd, imm):
    imm &= 0x1FFFFF
    b20 = (imm >> 20) & 1
    b10_1 = (imm >> 1) & 0x3FF
    b11 = (imm >> 11) & 1
    b19_12 = (imm >> 12) & 0xFF
    return (b20 << 31) | (b10_1 << 21) | (b11 << 20) | (b19_12 << 12) | (rd << 7) | 0x6F


def parse_imm(tok):
    tok = tok.strip()
    return int(tok, 0)


def li_words(rd, imm):
    """Return list of (mnemonic_args, is_two_word) encoded later; expand form."""
    if -2048 <= imm <= 2047:
        return [("addi", rd, 0, imm)]
    hi = ((imm + 0x800) >> 12) & 0xFFFFF
    lo = imm - (hi << 12)
    return [("lui", rd, hi), ("addi", rd, rd, lo)]


def split_operands(text):
    return [t.strip() for t in text.split(",") if t.strip()]


def assemble(source_lines):
    # pass 1: normalise into records, assign addresses
    recs = []   # (addr, item) item = ('raw', words_placeholder, text) or ('label', name)
    labels = {}
    addr = 0
    for raw in source_lines:
        line = raw.split("#")[0].strip()
        if not line:
            continue
        if line.endswith(":"):
            labels[line[:-1]] = addr
            recs.append((addr, ("label", line[:-1])))
            continue
        if ":" in line.split()[0]:
            lbl, rest = line.split(":", 1)
            labels[lbl] = addr
            recs.append((addr, ("label", lbl)))
            line = rest.strip()
            if not line:
                continue
        parts = line.split(None, 1)
        mn = parts[0].lower()
        ops = split_operands(parts[1]) if len(parts) > 1 else []

        if mn in ("nop",):
            recs.append((addr, ("i", "addi", [0, 0, 0], line)))
            addr += 4
            continue
        if mn == "li":
            rd = REGS[ops[0]]
            imm = parse_imm(ops[1])
            for it in li_words(rd, imm):
                if it[0] == "addi":
                    recs.append((addr, ("i", "addi", [it[1], it[2], it[3]], line)))
                else:
                    recs.append((addr, ("u", "lui", [it[1], it[2]], line)))
                addr += 4
            continue
        if mn == "la":
            rd = REGS[ops[0]]
            recs.append((addr, ("la", rd, ops[1], line)))
            addr += 8
            continue
        if mn == "j" or (mn == "jal" and len(ops) == 1):
            if mn == "j":
                recs.append((addr, ("j", 0, ops[0], line)))
            else:
                recs.append((addr, ("j", 1, ops[0], line)))
            addr += 4
            continue
        if mn == "jal":
            recs.append((addr, ("j", REGS[ops[0]], ops[1], line)))
            addr += 4
            continue
        if mn == "jalr":
            if len(ops) == 1:
                recs.append((addr, ("i", "jalr", [1, REGS[ops[0]], 0], line)))
            elif len(ops) == 2:
                recs.append((addr, ("i", "jalr", [REGS[ops[0]], REGS[ops[1]], 0], line)))
            else:
                recs.append((addr, ("i", "jalr", [REGS[ops[0]], REGS[ops[1]], parse_imm(ops[2])], line)))
            addr += 4
            continue
        if mn == "ebreak":
            recs.append((addr, ("i", "ebreak", [], line)))
            addr += 4
            continue
        if mn in R_OPS:
            recs.append((addr, ("r", mn, [REGS[ops[0]], REGS[ops[1]], REGS[ops[2]]], line)))
            addr += 4
            continue
        if mn == "csrw":
            recs.append((addr, ("i", "csrrw", [0, REGS[ops[1]], csr_num(ops[0])], line)))
            addr += 4
            continue
        if mn == "fence":
            recs.append((addr, ("i", "fence", [], line)))
            addr += 4
            continue
        if mn in I_OPS:
            recs.append((addr, ("i", mn, [REGS[ops[0]], REGS[ops[1]], parse_imm(ops[2])], line)))
            addr += 4
            continue
        if mn in SHIFT_I:
            recs.append((addr, ("i", mn, [REGS[ops[0]], REGS[ops[1]], parse_imm(ops[2])], line)))
            addr += 4
            continue
        if mn in LOAD:
            m = ops[1].strip()
            off, base = m.split("(")
            recs.append((addr, ("i", mn, [REGS[ops[0]], REGS[base.strip(")")], parse_imm(off or "0")], line)))
            addr += 4
            continue
        if mn in STORE:
            m = ops[1].strip()
            off, base = m.split("(")
            recs.append((addr, ("s", mn, [REGS[ops[0]], REGS[base.strip(")")], parse_imm(off or "0")], line)))
            addr += 4
            continue
        if mn in BRANCH:
            recs.append((addr, ("b", mn, [REGS[ops[0]], REGS[ops[1]], ops[2]], line)))
            addr += 4
            continue
        raise SystemExit(f"unsupported: {line}")

    # pass 2: encode
    words = []
    listing = []
    seen_label_at = {}
    for ad, rec in recs:
        if rec[0] == "label":
            seen_label_at[rec[1]] = ad
            listing.append((ad, None, f"{rec[1]}:"))
            continue
        kind = rec[0]
        if kind == "r":
            mn, (rd, rs1, rs2) = rec[1], rec[2]
            f7, f3 = R_OPS[mn]
            w = r_type(rd, rs1, rs2, f3, f7)
        elif kind == "i":
            mn, o = rec[1], rec[2]
            if mn == "ebreak":
                w = 0x00100073
            elif mn == "fence":
                w = 0x0ff0000f
            elif mn == "csrrw":
                rd, rs1, csr = o
                w = i_type(rd, rs1, csr, 1, 0x73)
            elif mn == "jalr":
                rd, rs1, imm = o
                w = i_type(rd, rs1, imm, 0, 0x67)
            elif mn in SHIFT_I:
                rd, rs1, sh = o
                f3 = SHIFT_I[mn]
                f7 = 0x20 if mn == "srai" else 0
                w = i_type(rd, rs1, sh & 0x1F, f3, 0x13) | (f7 << 25)
            elif mn in I_OPS:
                rd, rs1, imm = o
                w = i_type(rd, rs1, imm, I_OPS[mn], 0x13)
            elif mn in LOAD:
                rd, rs1, imm = o
                w = i_type(rd, rs1, imm, LOAD[mn], 0x03)
            else:
                raise SystemExit(f"bad i op {mn}")
        elif kind == "s":
            mn, (rs2, rs1, imm) = rec[1], rec[2]
            w = s_type(rs2, rs1, imm, STORE[mn])
        elif kind == "b":
            mn, (rs1, rs2, tgt) = rec[1], rec[2]
            if tgt not in labels:
                raise SystemExit(f"unknown label {tgt}")
            off = labels[tgt] - ad
            w = b_type(rs1, rs2, off, BRANCH[mn])
        elif kind == "u":
            rd, imm20 = rec[2]
            w = u_type(rd, imm20)
        elif kind == "j":
            rd, tgt = rec[1], rec[2]
            w = j_type(rd, labels[tgt] - ad)
        elif kind == "la":
            rd, tgt, _ = rec[1], rec[2], rec[3]
            a = labels[tgt]
            hi = ((a + 0x800) >> 12) & 0xFFFFF
            lo = a - (hi << 12)
            words.append((ad, u_type(rd, hi), rec[3] + "  [lui]"))
            words.append((ad + 4, i_type(rd, rd, lo, 0, 0x13), rec[3] + "  [addi]"))
            continue
        else:
            raise SystemExit("bad record")
        words.append((ad, w, rec[-1]))

    listing = sorted(words, key=lambda x: x[0])
    return labels, listing


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("program.S")
    out = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(".")
    labels, listing = assemble(src.read_text(encoding="utf-8").splitlines())
    words_out = [f"{w:08x}" for _, w, _ in listing]
    words_out += ["00000013"] * max(0, 512 - len(words_out))
    (out / "imem.hex").write_text("\n".join(words_out) + "\n", encoding="ascii")
    (out / "program.lst").write_text(
        "\n".join(f"{a:04x}: {('        ' if w is None else f'{w:08x}')}  {t}"
                  for a, w, t in listing) + "\n",
        encoding="utf-8")
    with (out / "labels.txt").open("w", encoding="ascii") as f:
        for k, v in sorted(labels.items(), key=lambda kv: kv[1]):
            f.write(f"{k} {v:04x}\n")
    print(f"assembled {len(listing)} words, {len(labels)} labels")


if __name__ == "__main__":
    main()
