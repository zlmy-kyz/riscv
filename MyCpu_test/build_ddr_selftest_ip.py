#!/usr/bin/env python3
"""Generate isolated legacy 0x80000000 self-test or ld_st ROM/RAM IP pairs."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from build_ddr_selftest import OUT, ROOT

PROJECT = ROOT.parent
PANGO = Path("C:/pango/PDS_2022.2-SP6.4/bin/ip_generate.exe")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", choices=("selftest", "ld_st"), default="selftest")
    args = parser.parse_args()
    out = OUT if args.suite == "selftest" else ROOT / "ddr_stage"
    image_name = "ddr_selftest.dat" if args.suite == "selftest" else "ld_st.dat"
    if not (out / "boot_rom.dat").exists() or not (out / image_name).exists():
        script = "build_ddr_selftest.py" if args.suite == "selftest" else "build_ddr_stage.py"
        extra = [] if args.suite == "selftest" else ["ld_st"]
        subprocess.run([sys.executable, str(ROOT / script), *extra], cwd=PROJECT, check=True)
    for name, filename in (("inst_rom", "boot_rom.dat"), ("data_ram", image_name)):
        if generate_one(name, filename, out):
            return 1
    return 0


def generate_one(name: str, filename: str, OUT: Path) -> int:
    IP_DIR = OUT / "ipcore" / name
    SOURCE_IDF = PROJECT / "ipcore" / name / f"{name}.idf"
    image = OUT / filename
    if not image.is_file():
        raise FileNotFoundError(image)
    IP_DIR.mkdir(parents=True, exist_ok=True)
    source = SOURCE_IDF.read_text(encoding="utf-8")
    replacement = image.as_posix()
    copied, count = re.subn(r"(<name>INIT_FILE</name>\s*<value>)[^<]*(</value>)",
                            lambda m: m.group(1) + replacement + m.group(2),
                            source, count=1)
    if count != 1:
        raise ValueError(f"could not find INIT_FILE in {name}.idf")
    idf = IP_DIR / f"{name}.idf"
    idf.write_text(copied, encoding="utf-8")
    cmd = [str(PANGO), "-i", str(idf), "-disable-syn"]
    run = subprocess.run(cmd, cwd=IP_DIR, capture_output=True, text=True, timeout=120)
    (OUT / f"{name}_generate_console.log").write_text(run.stdout + run.stderr,
                                                  encoding="utf-8")
    wrapper = IP_DIR / f"{name}.v"
    init = IP_DIR / "rtl" / f"{name}_init_param.v"
    if run.returncode or not wrapper.exists() or not init.exists():
        print(f"FAIL isolated IP generation; see {OUT / (name + '_generate_console.log')}")
        return 1
    if f'localparam INIT_FILE = "{replacement}"' not in wrapper.read_text(encoding="utf-8"):
        print("FAIL isolated IP INIT_FILE does not name the self-test image")
        return 1
    print(f"PASS isolated real {name} IP: {wrapper}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
