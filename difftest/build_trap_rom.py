#!/usr/bin/env python3
"""把 trap/CSR 专项汇编编为 ROM/RAM 镜像；ISS 留给后续联合验证。"""

import pathlib
import sys

from golden.rvtool import Assembler, BRAM_WORDS, enc_i, parse_reg


CSR_ADDR = {"mstatus": 0x300, "mie": 0x304, "mtvec": 0x305,
            "mscratch": 0x340,
            "mepc": 0x341, "mcause": 0x342, "mtval": 0x343,
            "mip": 0x344,
            "mconfigptr": 0xF15}


class TrapAssembler(Assembler):
    def encode(self, text, cur):
        fields = text.strip().split(None, 1)
        op = fields[0].lower()
        args = [a.strip() for a in fields[1].split(",")] if len(fields) > 1 else []
        if op in ("ecall", "ebreak", "mret"):
            if args:
                raise ValueError(f"{op} 不接受操作数")
            return {"ecall": 0x00000073, "ebreak": 0x00100073,
                    "mret": 0x30200073}[op]
        if op in ("csrr", "csrw", "csrrs"):
            expected = {"csrr": 2, "csrw": 2, "csrrs": 3}[op]
            if len(args) != expected:
                raise ValueError(f"{op} 需要 {expected} 个操作数")
            name = args[1] if op != "csrw" else args[0]
            addr = CSR_ADDR[name.lower()] if name.lower() in CSR_ADDR else int(name, 0)
            if not 0 <= addr <= 0xFFF:
                raise ValueError(f"CSR 地址越界：{name}")
            if op == "csrr":
                return enc_i(addr, 0, 2, parse_reg(args[0]), 0x73)
            if op == "csrw":
                return enc_i(addr, parse_reg(args[1]), 1, 0, 0x73)
            return enc_i(addr, parse_reg(args[2]), 2, parse_reg(args[0]), 0x73)
        return super().encode(text, cur)


def main():
    source = pathlib.Path(sys.argv[1])
    output = pathlib.Path(sys.argv[2])
    output.mkdir(parents=True, exist_ok=True)
    assembler = TrapAssembler()
    program = assembler.assemble(source.read_text(encoding="utf-8"))
    rom = [0] * BRAM_WORDS
    for addr, word in program.items():
        if addr % 4 or not 0 <= addr // 4 < BRAM_WORDS:
            raise ValueError(f"指令地址超出 ROM 或未对齐：0x{addr:x}")
        rom[addr // 4] = word
    (output / "rom.hex").write_text("".join(f"{word:08x}\n" for word in rom))
    (output / "ram.hex").write_text("00000000\n" * BRAM_WORDS)
    (output / "prog.lst").write_text(
        "".join(f"{addr:08x} {encoded or '        '} {raw}\n"
                for addr, encoded, raw in assembler.listing), encoding="utf-8")
    print(f"assembled {len(program)} instructions from {source.name}")


if __name__ == "__main__":
    main()
