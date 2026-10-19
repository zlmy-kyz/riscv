"""Independent RV32I-subset reference for the fix02 programs.

Interprets the assembled listing from the architectural state only (no DUT
signal is consulted) and emits one line per retired instruction:
    RET,index,pc,inst,rd,we,value,next_pc
Only the instructions used by these six micro programs are implemented:
addi/add/sub/xor/or/and/lw/sw/beq/bne/blt/bge/jal/csrw.
"""
from pathlib import Path
import json
import sys

MASK = 0xFFFFFFFF


def sx(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def load_listing(lst):
    mem = {}
    for line in lst.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        head, rest = line.split(":", 1)
        try:
            pc = int(head.strip(), 16)
        except ValueError:
            continue
        hexw = rest.strip().split("  ")[0].strip()
        if len(hexw) == 8:
            try:
                mem[pc] = int(hexw, 16)
            except ValueError:
                pass
    return mem


def run(code, dmem, max_steps=400):
    regs = [0] * 32
    pc = 0
    out = []
    stores = []
    for _ in range(max_steps):
        if pc not in code:
            raise SystemExit(f"pc {pc:#x} outside listing")
        inst = code[pc]
        op = inst & 0x7F
        rd = (inst >> 7) & 0x1F
        f3 = (inst >> 12) & 7
        rs1 = (inst >> 15) & 0x1F
        rs2 = (inst >> 20) & 0x1F
        imm_i = sx((inst >> 20) & 0xFFF, 12)
        next_pc = pc + 4
        we = 0
        val = 0

        if op == 0x13:                                    # addi
            we, val = 1, (regs[rs1] + imm_i) & MASK
        elif op == 0x33:                                  # R-type
            f7 = inst >> 25
            a, b = regs[rs1], regs[rs2]
            if f3 == 0:   val = (a - b) & MASK if f7 == 0x20 else (a + b) & MASK
            elif f3 == 4: val = a ^ b
            elif f3 == 6: val = a | b
            elif f3 == 7: val = a & b
            else: raise SystemExit(f"unsupported R funct3 {f3}")
            we = 1
        elif op == 0x03 and f3 == 2:                      # lw
            addr = (regs[rs1] + imm_i) & MASK
            val = dmem.get(addr, 0)
            we = 1
        elif op == 0x23 and f3 == 2:                      # sw
            imm_s = (((inst >> 25) & 0x7F) << 5) | ((inst >> 7) & 0x1F)
            addr = (regs[rs1] + sx(imm_s, 12)) & MASK
            dmem[addr] = regs[rs2]
            stores.append((addr, regs[rs2]))
        elif op == 0x63:                                  # branches
            imm = (((inst >> 31) & 1) << 12) | (((inst >> 7) & 1) << 11) | \
                  (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1)
            off = sx(imm, 13)
            a, b = regs[rs1], regs[rs2]
            sa, sb = sx(a, 32), sx(b, 32)
            taken = {0: a == b, 1: a != b, 4: sa < sb, 5: sa >= sb}.get(f3)
            if taken is None:
                raise SystemExit(f"unsupported branch funct3 {f3}")
            if taken:
                next_pc = (pc + off) & MASK
        elif op == 0x6F:                                  # jal
            rd_j = rd
            imm = (((inst >> 31) & 1) << 20) | (((inst >> 12) & 0xFF) << 12) | \
                  (((inst >> 20) & 1) << 11) | (((inst >> 21) & 0x3FF) << 1)
            next_pc = (pc + sx(imm, 21)) & MASK
            if rd_j: we, val = 1, pc + 4
            rd = rd_j
        elif op == 0x73 and f3 == 1:                      # csrrw (csrw)
            if ((inst >> 20) & 0xFFF) != 0x340:
                raise SystemExit("only mscratch csrw is supported")
            val = regs[rs1]                               # rd = x0, no writeback
            we = 0
        else:
            raise SystemExit(f"unsupported inst {inst:#x} at {pc:#x}")

        if we and rd:
            regs[rd] = val
        out.append((pc, inst, rd, 1 if we and rd else 0, val if (we and rd) else 0, next_pc))
        pc = next_pc
    return out, stores


def main():
    src = Path(sys.argv[1])
    lst = Path(sys.argv[2])
    stpc = int(sys.argv[3], 0) if len(sys.argv) > 3 else -1
    code = load_listing(lst)
    dmem = {}
    trace, stores = run(code, dmem, max_steps=60)
    rows = []
    for pc, inst, rd, we, val, npc in trace:
        rows.append({"pc": pc, "inst": inst, "rd": rd, "we": we, "value": val, "next_pc": npc})
        if stpc >= 0 and pc == stpc:
            break
    (src / "ref_ret.json").write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")
    (src / "ref_store.json").write_text(json.dumps(stores, indent=2) + "\n", encoding="utf-8")
    (src / "ref_meta.json").write_text(json.dumps({
        "stpc": stpc, "retire_count": len(rows), "stores": len(stores),
        "note": "architectural interpretation of the listing only; no DUT signal used",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"ref: {len(rows)} retired, {len(stores)} stores, stop at {stpc:#x}")


if __name__ == "__main__":
    main()
