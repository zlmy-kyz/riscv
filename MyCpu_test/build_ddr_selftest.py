#!/usr/bin/env python3
"""Build a standalone RV32I DDR self-test and an intentional-failure image.

The existing on-chip boot loader copies this program to DDR, then jumps to it.
No DDR model is initialized through a hierarchy or readmemh call.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path

from build_ddr_stage import DEPTH, boot_program, write_words

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "ddr_selftest"
BASE = 0x8000_0000
DIAG = BASE + 0x1000
SCRATCH = BASE + 0x2000
SEED = 0x1357_9BDF


def signed12(value: int) -> int:
    value &= 0xFFF
    return value - 0x1000 if value & 0x800 else value


def i_type(opcode: int, funct3: int, rd: int, rs1: int, imm: int) -> int:
    if not -2048 <= imm <= 2047:
        raise ValueError(f"I immediate out of range: {imm}")
    return ((imm & 0xFFF) << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | opcode


def s_type(funct3: int, rs2: int, rs1: int, imm: int) -> int:
    if not -2048 <= imm <= 2047:
        raise ValueError(f"S immediate out of range: {imm}")
    v = imm & 0xFFF
    return ((v >> 5) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | ((v & 31) << 7) | 0x23


def r_type(funct3: int, rd: int, rs1: int, rs2: int) -> int:
    return (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (rd << 7) | 0x33


def b_type(funct3: int, rs1: int, rs2: int, offset: int) -> int:
    if offset % 2 or not -4096 <= offset <= 4094:
        raise ValueError(f"branch out of range: {offset}")
    v = offset & 0x1FFF
    return (((v >> 12) & 1) << 31) | (((v >> 5) & 63) << 25) | (rs2 << 20) | (rs1 << 15) | (funct3 << 12) | (((v >> 1) & 15) << 8) | (((v >> 11) & 1) << 7) | 0x63


def jal(offset: int) -> int:
    if offset % 2 or not -(1 << 20) <= offset < (1 << 20):
        raise ValueError(f"JAL out of range: {offset}")
    v = offset & 0x1FFFFF
    return (((v >> 20) & 1) << 31) | (((v >> 1) & 0x3FF) << 21) | (((v >> 11) & 1) << 20) | (((v >> 12) & 0xFF) << 12) | 0x6F


@dataclass
class Program:
    words: list[int] = field(default_factory=list)
    labels: dict[str, int] = field(default_factory=dict)
    fixups: list[tuple[int, str, str, tuple[int, ...]]] = field(default_factory=list)
    checks: int = 0

    def emit(self, value: int) -> None:
        self.words.append(value & 0xFFFF_FFFF)

    def mark(self, name: str) -> None:
        if name in self.labels:
            raise ValueError(f"duplicate label: {name}")
        self.labels[name] = len(self.words)

    def li(self, rd: int, value: int) -> None:
        value &= 0xFFFF_FFFF
        low = signed12(value)
        high = ((value + 0x800) >> 12) & 0xFFFFF
        self.emit((high << 12) | (rd << 7) | 0x37)
        self.emit(i_type(0x13, 0, rd, rd, low))

    def addi(self, rd: int, rs1: int, imm: int) -> None:
        self.emit(i_type(0x13, 0, rd, rs1, imm))

    def shift(self, rd: int, rs1: int, count: int, right: bool = False) -> None:
        self.emit(i_type(0x13, 5 if right else 1, rd, rs1, count))

    def xor(self, rd: int, rs1: int, rs2: int) -> None:
        self.emit(r_type(4, rd, rs1, rs2))

    def load(self, funct3: int, rd: int, rs1: int, offset: int) -> None:
        self.emit(i_type(0x03, funct3, rd, rs1, offset))

    def store(self, funct3: int, rs2: int, rs1: int, offset: int) -> None:
        self.emit(s_type(funct3, rs2, rs1, offset))

    def branch(self, funct3: int, rs1: int, rs2: int, target: str) -> None:
        self.fixups.append((len(self.words), "branch", target, (funct3, rs1, rs2)))
        self.emit(0)

    def jump(self, target: str) -> None:
        self.fixups.append((len(self.words), "jal", target, ()))
        self.emit(0)

    def resolve(self) -> list[int]:
        for pc, kind, target, args in self.fixups:
            offset = (self.labels[target] - pc) * 4
            self.words[pc] = b_type(*args, offset) if kind == "branch" else jal(offset)
        return self.words


def xorshift(p: Program) -> None:
    # x9 state, x10 temporary. No M extension or library calls.
    p.shift(10, 9, 13); p.xor(9, 9, 10)
    p.shift(10, 9, 17, right=True); p.xor(9, 9, 10)
    p.shift(10, 9, 5); p.xor(9, 9, 10)


def check(p: Program, addr: int, expected: int, funct3: int = 2) -> None:
    p.li(13, addr)             # failing address
    p.li(14, expected)         # expected value
    p.load(funct3, 15, 13, 0)  # observed value
    p.branch(1, 15, 14, "fail")
    p.addi(19, 19, 1)
    p.checks += 1


def build_program(inject_fault: bool, seed: int, base: int = BASE) -> tuple[list[int], int]:
    DIAG = base + 0x1000
    SCRATCH = base + 0x2000
    p = Program()
    p.li(21, 0x1000_0010)     # TEST_STATUS MMIO, independent of DDR diagnostics
    p.addi(22, 0, 1)
    p.store(2, 22, 21, 0)     # RUN
    p.li(20, DIAG)            # tohost and diagnostic record
    p.li(1, 1)                # PASS code
    p.li(19, 0)               # completed comparison count

    # 64 sequential words span 16 DDR user beats, all four 32-bit slots.
    p.li(16, 1)
    p.li(5, SCRATCH)
    p.li(6, SCRATCH + 64 * 4)
    p.li(9, seed)
    p.mark("random_write")
    xorshift(p)
    p.store(2, 9, 5, 0)
    p.addi(5, 5, 4)
    p.branch(1, 5, 6, "random_write")

    p.li(16, 2)
    p.li(5, SCRATCH)
    p.li(9, seed)
    p.mark("random_verify")
    xorshift(p)
    p.addi(13, 5, 0)
    p.addi(14, 9, 0)
    p.load(2, 15, 5, 0)
    p.branch(1, 15, 14, "fail")
    p.addi(19, 19, 1)
    p.addi(5, 5, 4)
    p.branch(1, 5, 6, "random_verify")

    # Walking one through every data bit, at 32 separate addresses.
    p.li(16, 3)
    p.li(5, SCRATCH + 0x100)
    p.li(6, SCRATCH + 0x180)
    p.li(9, 1)
    p.mark("walking_write")
    p.store(2, 9, 5, 0)
    p.shift(9, 9, 1)
    p.addi(5, 5, 4)
    p.branch(1, 5, 6, "walking_write")
    p.li(16, 4)
    p.li(5, SCRATCH + 0x100)
    p.li(9, 1)
    p.mark("walking_verify")
    p.addi(13, 5, 0)
    p.addi(14, 9, 0)
    p.load(2, 15, 5, 0)
    p.branch(1, 15, 14, "fail")
    p.addi(19, 19, 1)
    p.shift(9, 9, 1)
    p.addi(5, 5, 4)
    p.branch(1, 5, 6, "walking_verify")

    # Directed byte/halfword masks, sign extension and adjacent-beat boundary.
    p.li(16, 5)
    for lane, value in enumerate((0x11223344, 0x55667788, 0xAABBCCDD, 0x80FF7F01)):
        p.li(9, value)
        p.li(13, SCRATCH + 0x200 + lane * 4)
        p.store(2, 9, 13, 0)
        check(p, SCRATCH + 0x200 + lane * 4,
              value + (1 if inject_fault and lane == 0 else 0))
    p.li(9, 0xAA)
    p.li(13, SCRATCH + 0x201)
    p.store(0, 9, 13, 0)
    check(p, SCRATCH + 0x200, 0x1122AA44)
    check(p, SCRATCH + 0x201, 0xFFFFFFAA, 0)
    check(p, SCRATCH + 0x201, 0xAA, 4)
    p.li(9, 0x80FF)
    p.li(13, SCRATCH + 0x202)
    p.store(1, 9, 13, 0)
    check(p, SCRATCH + 0x200, 0x80FFAA44)
    check(p, SCRATCH + 0x202, 0xFFFF80FF, 1)
    check(p, SCRATCH + 0x202, 0x80FF, 5)
    check(p, SCRATCH + 0x20D, 0x7F, 0)
    check(p, SCRATCH + 0x20E, 0xFFFFFFFF, 0)
    check(p, SCRATCH + 0x20F, 0xFFFFFF80, 0)
    check(p, SCRATCH + 0x20F, 0x80, 4)
    p.li(9, 0xDEADBEEF)
    p.li(13, SCRATCH + 0x210)
    p.store(2, 9, 13, 0)
    p.li(9, 0x66)
    p.li(13, SCRATCH + 0x20F)
    p.store(0, 9, 13, 0)
    check(p, SCRATCH + 0x20C, 0x66FF7F01)
    check(p, SCRATCH + 0x210, 0xDEADBEEF)

    # The status record is written before tohost, so observers can retain it.
    p.li(16, 0)
    p.store(2, 19, 20, 20)  # checked comparisons
    p.store(2, 9, 20, 24)   # final marker
    p.addi(22, 0, 2)
    p.store(2, 22, 21, 0)   # PASS, latched by MMIO
    p.store(2, 1, 20, 0)    # tohost=1
    p.mark("done")
    p.jump("done")

    p.mark("fail")
    p.addi(22, 0, 3)
    p.store(2, 22, 21, 0)   # FAIL before diagnostic DDR writes can stall
    p.store(2, 13, 20, 4)
    p.store(2, 14, 20, 8)
    p.store(2, 15, 20, 12)
    p.store(2, 16, 20, 16)
    p.store(2, 19, 20, 20)
    p.li(12, 2)
    p.store(2, 12, 20, 0)  # tohost=2
    p.mark("failed_stop")
    p.jump("failed_stop")

    words = p.resolve()
    if len(words) >= 1024:
        raise ValueError(f"program overlaps tohost diagnostic area: {len(words)} words")
    return words, 64 + 32 + p.checks


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=lambda value: int(value, 0), default=BASE)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    boot = boot_program(args.base)
    if args.base + 0x3000 > 0x1_0000_0000:
        parser.error("self-test regions exceed the 32-bit address space")
    out = args.out.resolve()
    out.mkdir(parents=True, exist_ok=True)
    write_words(out / "boot_rom.dat", boot + [0x0000006F] * (DEPTH - len(boot)))
    counts = []
    cases = (
        ("ddr_selftest", False, SEED),
        ("ddr_selftest_seed2", False, 0x2468_ACE1),
        ("ddr_selftest_seed3", False, 0xA5C3_F00D),
        ("ddr_selftest_injected", True, SEED),
    )
    for name, fault, seed in cases:
        code, checks = build_program(fault, seed, args.base)
        words = [0x00000013] * DEPTH
        words[:len(code)] = code
        words[-4:] = [len(code), 0, 0, 0]  # existing loader manifest
        write_words(out / f"{name}.dat", words)
        counts.append(f"{name}\t{len(code)}\t{checks}\t{seed:08x}")
        print(f"STAGE {name}: code={len(code)} words checks={checks} seed=0x{seed:08x} tohost=0x{args.base + 0x1000:08x}")
    (out / "manifest.tsv").write_text("\n".join(counts) + "\n", encoding="ascii")


if __name__ == "__main__":
    main()
