#!/usr/bin/env python3
"""Verify completed ModelSim DDR3 RV32I logs after the simulator exits."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = ROOT / "ipcore" / "ddr3" / "sim" / "modelsim"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="+", help="completed test names to verify")
    args = parser.parse_args()
    rows = []
    for name in args.tests:
        if not re.fullmatch(r"[a-z0-9_]+", name):
            raise ValueError(f"invalid test name: {name}")
        path = LOG_DIR / f"soc_ddr3_rv32i_{name}.log"
        if not path.exists():
            status, detail = "MISSING", "log not found"
        else:
            output = path.read_text(encoding="utf-8", errors="replace")
            results = re.findall(r"^# RESULT: (?:PASS|FAIL).*?$", output, re.MULTILINE)
            errors = re.findall(r"^# Errors: (\d+), Warnings: (\d+)", output,
                                re.MULTILINE)
            valid = (len(results) == 1 and
                     results[0].startswith(f"# RESULT: PASS {name} DDR RV32I tohost=1 ") and
                     len(errors) == 1 and errors[0][0] == "0" and
                     f"# CHECK: {name} CPU copied" in output and
                     "# RESULT: FAIL" not in output)
            status = "PASS" if valid else "FAIL"
            detail = results[-1] if results else "no RESULT line"
            if errors:
                detail += f"; Errors={errors[-1][0]}, Warnings={errors[-1][1]}"
        rows.append((name, status, detail, str(path)))
        print(f"{name:9} {status:7} {detail}")
    summary = LOG_DIR / "soc_ddr3_rv32i_verified.csv"
    with summary.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("test", "status", "detail", "log"))
        writer.writerows(rows)
    passed = sum(status == "PASS" for _, status, _, _ in rows)
    # Replace the in-simulator provisional summary, whose log footer may not
    # yet have been flushed when the Tcl loop reads it.
    text_summary = LOG_DIR / "soc_ddr3_rv32i_summary.txt"
    text_summary.write_text(
        "VERIFIED after ModelSim exit\n" +
        "\n".join(f"{name} {status} {detail}" for name, status, detail, _ in rows) +
        f"\nTOTAL pass={passed} fail={len(rows) - passed}\n",
        encoding="utf-8")
    print(f"TOTAL {passed}/{len(rows)} PASS; summary={summary}")
    return 0 if passed == len(rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
