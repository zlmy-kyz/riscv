"""Build a 16-KiB RAM DAT and compatible ROM loader from a flat RV32I BIN.

No RTL, simulation model, storage IP or archived DAT is modified by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

DEPTH = 4096


def boot_program(base: int) -> list[int]:
    """Existing CPU ROM loader: copy code, optional data span, then jump to base."""
    if not 0 <= base <= 0xFFFFFFFF or base & 0xFFF:
        raise ValueError("DDR base must be a 32-bit, 4-KiB-aligned address")
    words = [
        0x40000437, 0x00000493, 0x000042B7, 0xFF028293,
        0x0002A903, 0x0004A303, 0x00642023, 0x00448493,
        0x00440413, 0xFFF90913, 0xFE0916E3, 0x0042A483,
        0x0082A903, 0x02090263, 0x40000437, 0x00940433,
        0x0004A303, 0x00642023, 0x00448493, 0x00440413,
        0xFFF90913, 0xFE0916E3, 0x400003B7, 0x00038067,
    ]
    # Change only the three LUI destination bases, preserving registers/opcodes.
    for index in (0, 14, 22):
        words[index] = base | (words[index] & 0xFFF)
    return words


def write_words(path: Path, words: list[int]) -> None:
    path.write_text("".join(f"{value:08x}\n" for value in words), encoding="ascii")


def convert(binary: Path, output: Path, base: int = 0x40000000) -> dict:
    payload = binary.read_bytes()
    if not payload or len(payload) > (DEPTH - 4) * 4:
        raise ValueError("BIN must contain 1..16368 bytes; last 16 RAM bytes are reserved")
    if base & 0xFFF or not 0 <= base <= 0xFFFFFFFF or base + len(payload) > 2**32:
        raise ValueError("DDR base must be a 32-bit, 4-KiB-aligned address with no overflow")
    padded = payload + bytes((-len(payload)) % 4)
    words = [int.from_bytes(padded[i:i + 4], "little") for i in range(0, len(padded), 4)]
    image = words + [0] * (DEPTH - len(words))
    image[-4:] = [len(words), 0, 0, 0]
    boot = boot_program(base)
    output.mkdir(parents=True, exist_ok=True)
    dat = output / (binary.stem + ".dat")
    write_words(dat, image)
    write_words(output / "boot_rom.dat", boot + [0x0000006F] * (DEPTH - len(boot)))
    actual = [int(x, 16) for x in dat.read_text(encoding="ascii").split()]
    decoded = b"".join(x.to_bytes(4, "little") for x in actual[:len(words)])
    if len(actual) != DEPTH or decoded != padded or actual[-4:] != [len(words), 0, 0, 0]:
        raise ValueError("DAT round-trip verification failed")
    info = {"source_bin": str(binary.resolve()), "sha256": hashlib.sha256(payload).hexdigest(),
            "base": base, "entry": base, "payload_bytes": len(payload),
            "payload_words": len(words), "ram_manifest_address": 0x3FF0,
            "ram_manifest": image[-4:], "dat": str(dat.resolve())}
    (output / "manifest.json").write_text(json.dumps(info, indent=2) + "\n", encoding="utf-8")
    return info


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("binary", type=Path)
    parser.add_argument("output", type=Path)
    parser.add_argument("--base", type=lambda x: int(x, 0), default=0x40000000)
    args = parser.parse_args()
    print(json.dumps(convert(args.binary, args.output, args.base), indent=2))
