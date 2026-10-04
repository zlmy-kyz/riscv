#!/usr/bin/env python3
"""Run the DDR self-test images through CPU, buses and fast DDR port model."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

from run_ddr_rv32i_fast import IVERILOG, ROOT, SOURCES, VVP

STAGE = ROOT / "MyCpu_test" / "ddr_selftest"
CASES = (
    ("ddr_selftest", True),
    ("ddr_selftest_seed2", True),
    ("ddr_selftest_seed3", True),
    ("ddr_selftest_injected", False),
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base", type=lambda value: int(value, 0), default=0x80000000,
                        choices=(0x40000000, 0x80000000))
    args = parser.parse_args()
    STAGE = ROOT / "MyCpu_test" / ("board_selftest" if args.base == 0x40000000 else "ddr_selftest")
    subprocess.run([sys.executable, str(ROOT / "MyCpu_test/build_ddr_selftest.py"),
                    "--base", hex(args.base), "--out", str(STAGE)], cwd=ROOT, check=True)
    binary = STAGE / "selftest_fast.vvp"
    counts = {name: int(count) for name, count, *_ in
              (line.split() for line in (STAGE / "manifest.tsv").read_text().splitlines())}
    sources = list(SOURCES)
    selftest_tb = "source/tb_ddr_selftest_fast.v"
    if args.base == 0x40000000:
        for original in ("source/tb_soc_ddr3_rv32i_fast.v", selftest_tb):
            generated = STAGE / Path(original).name
            generated.write_text((ROOT / original).read_text().replace("32'h8000_", "32'h4000_"))
            if original in sources:
                sources[sources.index(original)] = str(generated)
            else:
                selftest_tb = str(generated)
    compile_cmd = [str(IVERILOG), "-g2012", "-Imyriscv", "-s", "tb_ddr_selftest_fast",
                   "-o", str(binary), *sources, "myriscv/soc_ddr3_top.v", selftest_tb]
    comp = subprocess.run(compile_cmd, cwd=ROOT, capture_output=True, text=True)
    (STAGE / "fast_compile.log").write_text(comp.stdout + comp.stderr, encoding="utf-8")
    if comp.returncode:
        print(f"FAIL compile: {STAGE / 'fast_compile.log'}")
        return 1

    failures = 0
    for name, should_pass in CASES:
        cmd = [str(VVP), str(binary),
               f"+BOOT={(STAGE / 'boot_rom.dat').as_posix()}",
               f"+IMAGE={(STAGE / (name + '.dat')).as_posix()}",
               f"+TEST={name}", f"+TOHOST={args.base + 0x1000:08x}"]
        try:
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                 timeout=120)
            output = run.stdout + run.stderr
            exit_code = run.returncode
        except subprocess.TimeoutExpired as exc:
            output = ((exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes)
                      else (exc.stdout or "")) + "\nRUNNER TIMEOUT\n"
            exit_code = -1
        (STAGE / f"fast_{name}.log").write_text(output, encoding="utf-8")
        results = re.findall(r"^RESULT: (?:PASS|FAIL).*?$", output, re.MULTILINE)
        copied = f"CHECK: {name} CPU loaded {counts[name]} words into DDR" in output
        reported = ("CHECK: MMIO selftest RUN" in output and
                    f"CHECK: MMIO selftest {'PASS LED=1' if should_pass else 'FAIL'}" in output)
        if should_pass:
            good = (exit_code == 0 and copied and reported and len(results) == 1 and
                    results[0].startswith(f"RESULT: PASS {name} DDR RV32I tohost=1") and
                    "DIAG: checks=112" in output and "DIAG: address=" not in output)
        else:
            good = (exit_code == 0 and copied and reported and len(results) == 1 and
                    results[0].startswith(f"RESULT: FAIL {name} DDR RV32I tohost=00000002") and
                    f"DIAG: address={args.base + 0x2200:08x}" in output and
                    "DIAG: expected=11223345" in output and
                    "DIAG: observed=11223344" in output and
                    "DIAG: phase=5" in output and "DIAG: checks=96" in output)
        print(f"{name}: {'PASS' if good else 'FAIL'}; {results[-1] if results else 'no result'}",
              flush=True)
        failures += not good
    print(f"TOTAL {len(CASES)-failures}/{len(CASES)} EXPECTED; logs={STAGE}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
