#!/usr/bin/env python3
"""Build simulation-only RAM sources for CPU-driven RV32I image loading.

The boot ROM copies the code and optional .data spans from the on-chip RAM
source into DDR.  No test image is placed directly in the DDR model.
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from extract_data import data_start


ROOT = Path(__file__).resolve().parent
DAT = ROOT / "dat"
BIN = ROOT / "bin"
DUMP = ROOT / "dump"
OUT = ROOT / "ddr_stage"
DEPTH = 4096
BASE = 0x80000000


def read_words(path: Path) -> list[int]:
    words = [int(line, 16) for line in path.read_text(encoding="utf-8").split()]
    if len(words) != DEPTH or any(not 0 <= value <= 0xFFFFFFFF for value in words):
        raise ValueError(f"{path}: expected {DEPTH} 32-bit words")
    return words


def write_words(path: Path, words: list[int]) -> None:
    path.write_text("".join(f"{value:08x}\n" for value in words), encoding="ascii")


def lui(rd: int, imm20: int) -> int:
    return (imm20 << 12) | (rd << 7) | 0x37


def op_imm(rd: int, rs1: int, imm: int) -> int:
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (rd << 7) | 0x13


def load(rd: int, rs1: int, imm: int) -> int:
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (2 << 12) | (rd << 7) | 0x03


def store(rs2: int, rs1: int, imm: int) -> int:
    value = imm & 0xFFF
    return ((value >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (2 << 12) | ((value & 31) << 7) | 0x23


def add(rd: int, rs1: int, rs2: int) -> int:
    return (rs2 << 20) | (rs1 << 15) | (rd << 7) | 0x33


def branch(rs1: int, rs2: int, offset: int, funct3: int) -> int:
    if offset % 2 or not -4096 <= offset <= 4094:
        raise ValueError(f"invalid branch offset: {offset}")
    value = offset & 0x1FFF
    return (((value >> 12) & 1) << 31) | (((value >> 5) & 63) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (((value >> 1) & 15) << 8) | (((value >> 11) & 1) << 7) | 0x63


def jalr(rd: int, rs1: int) -> int:
    return (rs1 << 15) | (rd << 7) | 0x67


def boot_program() -> list[int]:
    # x5=manifest pointer, x6=word, x7=entry, x8=DDR destination,
    # x9=on-chip RAM source, x18=remaining word count.
    return [
        lui(8, 0x80000),       # DDR target 0x80000000
        op_imm(9, 0, 0),      # source 0
        lui(5, 4),
        op_imm(5, 5, -16),    # manifest at on-chip RAM 0x3ff0
        load(18, 5, 0),       # code word count
        load(6, 9, 0),       # code_loop:
        store(6, 8, 0),
        op_imm(9, 9, 4),
        op_imm(8, 8, 4),
        op_imm(18, 18, -1),
        branch(18, 0, -20, 1),  # bne code_loop
        load(9, 5, 4),       # optional .data source byte offset
        load(18, 5, 8),      # .data word count
        branch(18, 0, 36, 0),  # beq launch
        lui(8, 0x80000),
        add(8, 8, 9),        # DDR .data destination
        load(6, 9, 0),      # data_loop:
        store(6, 8, 0),
        op_imm(9, 9, 4),
        op_imm(8, 8, 4),
        op_imm(18, 18, -1),
        branch(18, 0, -20, 1),  # bne data_loop
        lui(7, 0x80000),    # launch:
        jalr(0, 7),
    ]


def build_one(name: str) -> tuple[int, int, int]:
    folder = DAT / name
    rom = read_words(folder / f"{name}_rom.dat")
    # The ROM images are padded with NOPs to 4096 words. Copy all meaningful
    # words, including internal zero gaps, and leave the NOP tail out.
    meaningful = [i for i, word in enumerate(rom) if word not in (0, 0x13)]
    if not meaningful:
        raise ValueError(f"{name}: empty ROM image")
    code_words = max(meaningful) + 1
    image = rom[:]
    start_word = data_words = 0
    ram_path = folder / f"{name}_ram.dat"
    dump_path = DUMP / f"rv32ui-p-{name}.dump"
    matches = set(re.findall(r"#\s*([0-9a-fA-F]{8})\s+<tohost>",
                             dump_path.read_text(encoding="utf-8", errors="replace")))
    if len(matches) != 1:
        raise ValueError(f"{name}: expected one tohost address, got {matches}")
    tohost = int(matches.pop(), 16)
    if ram_path.exists():
        start = data_start(dump_path)
        if start is None or (start - BASE) % 4:
            raise ValueError(f"{name}: invalid .data start")
        start_word = (start - BASE) // 4
        binary = BIN / f"rv32ui-p-{name}.bin"
        data_bytes = binary.stat().st_size - (start - BASE)
        if data_bytes <= 0:
            raise ValueError(f"{name}: empty or malformed .data image")
        data_words = (data_bytes + 3) // 4
        if start_word < code_words or start_word + data_words > DEPTH - 4:
            raise ValueError(f"{name}: image spans overlap or exceed staging RAM")
        ram = read_words(ram_path)
        image[start_word:start_word + data_words] = ram[start_word:start_word + data_words]
    image[-4:] = [code_words, start_word * 4, data_words, 0]
    write_words(OUT / f"{name}.dat", image)
    return code_words, data_words, tohost


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="*", help="test names; default: all images")
    args = parser.parse_args()
    names = args.tests or sorted(p.name for p in DAT.iterdir() if p.is_dir())
    OUT.mkdir(exist_ok=True)
    boot = boot_program()
    write_words(OUT / "boot_rom.dat", boot + [0x0000006F] * (DEPTH - len(boot)))
    tohost_rows = []
    for name in names:
        code, data, tohost = build_one(name)
        tohost_rows.append(f"{name} {tohost:08x}")
        print(f"STAGE {name}: code={code} words, data={data} words, tohost=0x{tohost:08x}")
    (OUT / "cases.txt").write_text("\n".join(names) + "\n", encoding="ascii")
    (OUT / "tohost.tsv").write_text("\n".join(tohost_rows) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
