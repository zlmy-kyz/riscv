"""Independent architectural reference for the fix01 programs.

Generates the retired-PC sequence of the CORRECT path up to (and including)
the target completion store, from the assembled listing only. It never reads
DUT internals or the simulation trace.

Branch rule used here is a property of these tiny programs, not a CPU model:
the only conditional branches are `beq x0,x0` (always taken) and
`beq x1,x2` (not taken, x1=1 x2=5). Anything else is sequential; `jal`
(including the `j` pseudo) is taken.
"""
from pathlib import Path
import json
import sys


def sx(v, bits):
    return v - (1 << bits) if v & (1 << (bits - 1)) else v


def decode(inst, pc):
    op = inst & 0x7F
    if op == 0x63:
        rs1 = (inst >> 15) & 0x1F
        rs2 = (inst >> 20) & 0x1F
        imm = (((inst >> 31) & 1) << 12) | (((inst >> 7) & 1) << 11) | \
              (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1)
        return ("branch", rs1, rs2, sx(imm, 13))
    if op == 0x6F:
        imm = (((inst >> 31) & 1) << 20) | (((inst >> 12) & 0xFF) << 12) | \
              (((inst >> 20) & 1) << 11) | (((inst >> 21) & 0x3FF) << 1)
        return ("jal", sx(imm, 21))
    return ("other",)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
    lst = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("program.lst")
    mem, store_pcs = {}, []
    for line in lst.read_text(encoding="utf-8").splitlines():
        if ":" not in line:
            continue
        head, rest = line.split(":", 1)
        try:
            pc = int(head.strip(), 16)
        except ValueError:
            continue
        hexw = rest.strip().split("  ")[0].strip()
        if len(hexw) != 8:
            continue
        try:
            mem[pc] = int(hexw, 16)
        except ValueError:
            continue
        if (mem[pc] & 0x7F) == 0x23:        # store
            store_pcs.append(pc)

    if not store_pcs:
        raise SystemExit("no store found in listing")
    stpc = store_pcs[-1]                     # the completion store

    path, pc, guard = [], 0, 0
    while guard < 200:
        guard += 1
        if pc not in mem:
            raise SystemExit(f"pc {pc:#x} outside listing")
        path.append(pc)
        if pc == stpc:
            break
        d = decode(mem[pc], pc)
        if d[0] == "branch":
            taken = (d[1] == 0 and d[2] == 0)
            pc = pc + d[3] if taken else pc + 4
        elif d[0] == "jal":
            pc = pc + d[1]
        else:
            pc = pc + 4

    (src / "ref_pc.txt").write_text("\n".join(f"{p:08x}" for p in path) + "\n", encoding="ascii")
    (src / "ref_meta.json").write_text(json.dumps({
        "stpc": stpc, "retire_count": len(path),
        "rule": "beq x0,x0 taken; beq x1,x2 not taken; jal always taken; else sequential",
    }, indent=2) + "\n", encoding="utf-8")
    print(f"ref: {len(path)} retired PCs up to store at {stpc:#x}")


if __name__ == "__main__":
    main()
