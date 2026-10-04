#!/usr/bin/env python3
"""Generate and verify board ROM/RAM candidates; --promote updates live IP files."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent.parent
IMAGES = ROOT / "MyCpu_test/board_selftest"
OUT = ROOT / "sim/board_boot_fix_20261003"
GEN = Path("C:/pango/PDS_2022.2-SP6.4/bin/ip_generate.exe")


def verify(name: str, folder: Path, image: Path) -> None:
    xml = ET.parse(folder / f"{name}.idf")
    params = {p.findtext("name"): p.findtext("value") for p in xml.findall("./param_list/param")}
    assert params["INIT_FILE"] == image.as_posix()
    assert params["ADDR_WIDTH"] == "12" and params["DATA_WIDTH"] == "32"
    text = (folder / "rtl" / f"{name}_init_param.v").read_text()
    width = int(re.search(r"//DRM_DATA_WIDTH_A = (\d+)", text)[1])
    addr_width = int(re.search(r"//DRM_ADDR_WIDTH_A = (\d+)", text)[1])
    stride = width + width // 8  # Pango stores parity bits alongside each byte.
    words_per_block = 288 // stride
    values = {(int(block, 16), int(bank), int(lane)): int(value, 16)
              for block, bank, lane, value in re.findall(
                  r"localparam INIT_([0-9A-Fa-f]+)_(\d+)_(\d+)\s*=\s*288'h([0-9A-Fa-f]+)", text)}
    words = [int(v, 16) for v in image.read_text().split()]
    assert len(words) == 4096 and len(values) == 512, (len(words), len(values))
    for index, expected in enumerate(words):
        bank, offset = divmod(index, 1 << addr_width)
        actual = 0
        for lane in range(32 // width):
            packed = values[offset // words_per_block, bank, lane] >> ((offset % words_per_block) * stride)
            for byte in range(width // 8):
                actual |= ((packed >> (byte * 9)) & 255) << (lane * width + byte * 8)
        assert actual == expected, (name, index, hex(actual), hex(expected))
    print(f"CHECK: {name} all 4096 generated initialization words match {image.name}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--promote", action="store_true")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / "MyCpu_test/build_ddr_selftest.py"),
                    "--base", "0x40000000", "--out", str(IMAGES)], check=True, cwd=ROOT)
    report = {}
    for name, filename in (("inst_rom", "boot_rom.dat"), ("data_ram", "ddr_selftest.dat")):
        candidate = OUT / "candidate/ipcore" / name
        candidate.mkdir(parents=True, exist_ok=True)
        image = IMAGES / filename
        live = ROOT / "ipcore" / name
        source = (live / f"{name}.idf").read_text(encoding="utf-8")
        updated, count = re.subn(r"(<name>INIT_FILE</name>\s*<value>)[^<]*(</value>)",
                                lambda m: m[1] + image.as_posix() + m[2], source)
        assert count == 1
        idf = candidate / f"{name}.idf"
        idf.write_text(updated, encoding="utf-8")
        run = subprocess.run([str(GEN), "-i", str(idf), "-disable-syn"], cwd=candidate,
                             capture_output=True, timeout=120)
        (candidate / "console.log").write_bytes(run.stdout + run.stderr)
        assert run.returncode == 0
        assert "Done: 0 error(s), 0 warning(s)" in (candidate / "generate.log").read_text()
        verify(name, candidate, image)
        report[name] = {"image": image.as_posix(), "sha256": hashlib.sha256(image.read_bytes()).hexdigest()}
    # Verify both candidates before replacing any live file. Backups preserve
    # all pre-existing IP content, including unrelated parameters and templates.
    if args.promote:
        for name in report:
            live = ROOT / "ipcore" / name
            backup = OUT / "before/ipcore" / name
            if not backup.exists():
                shutil.copytree(live, backup)
            candidate = OUT / "candidate/ipcore" / name
            for file in candidate.rglob("*"):
                if file.is_file() and file.name != "console.log":
                    dest = live / file.relative_to(candidate)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file, dest)
            verify(name, live, Path(report[name]["image"]))
        print("PASS: promoted board ROM/RAM initialization; DDR and IO constraints unchanged")
    (OUT / "images.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
