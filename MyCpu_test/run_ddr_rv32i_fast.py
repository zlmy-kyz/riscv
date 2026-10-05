#!/usr/bin/env python3
"""Run RV32I images through the CPU, SoC buses and DDR bridge model."""

from __future__ import annotations

import argparse
import csv
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "MyCpu_test" / "ddr_stage"
IVERILOG = Path("D:/iverilog/bin/iverilog.exe")
VVP = Path("D:/iverilog/bin/vvp.exe")
SOURCES = [
    "source/tb_soc_ddr3_rv32i_mem.v",
    "source/tb_soc_ddr3_rv32i_fast.v",
    "myriscv/alu.v", "myriscv/br_alu.v", "myriscv/l_alu.v",
    "myriscv/regfile.v", "myriscv/csr_file.v", "myriscv/mycpu_sync.v",
    "myriscv/inst_bus_interconnect.v", "myriscv/data_bus_interconnect.v",
    "myriscv/inst_bram_adapter.v", "myriscv/data_bram_adapter.v",
    "myriscv/simple_mmio.v", "myriscv/dual_sram_to_pango_ddr_bridge.v",
    "myriscv/soc_top.v",
    "myriscv/uart_tx.v", "myriscv/uart_rx.v", "myriscv/uart_rx_fifo.v", "myriscv/uart_mmio.v",
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tests", nargs="*", help="test names; default: all 42")
    args = parser.parse_args()
    subprocess.run([sys.executable, str(ROOT / "MyCpu_test" / "build_ddr_stage.py"),
                    *args.tests], cwd=ROOT, check=True)
    names = (STAGE / "cases.txt").read_text(encoding="ascii").split()
    tohost = dict(line.split() for line in
                  (STAGE / "tohost.tsv").read_text(encoding="ascii").splitlines())
    binary = STAGE / "rv32i_fast.vvp"
    compile_cmd = [str(IVERILOG), "-g2012", "-Imyriscv",
                   "-s", "tb_soc_ddr3_rv32i_fast", "-o", str(binary), *SOURCES]
    compile_result = subprocess.run(compile_cmd, cwd=ROOT, capture_output=True, text=True)
    (STAGE / "fast_compile.log").write_text(
        compile_result.stdout + compile_result.stderr, encoding="utf-8")
    if compile_result.returncode:
        print("Compile failed; see", STAGE / "fast_compile.log")
        return 1
    rows = []
    for name in names:
        cmd = [str(VVP), str(binary),
               f"+BOOT={(STAGE / 'boot_rom.dat').as_posix()}",
               f"+IMAGE={(STAGE / (name + '.dat')).as_posix()}",
               f"+TEST={name}", f"+TOHOST={tohost[name]}"]
        try:
            run = subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True,
                                 timeout=90)
            output = run.stdout + run.stderr
            exit_code = run.returncode
        except subprocess.TimeoutExpired as exc:
            output = (exc.stdout or b"").decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            output += "\nRUNNER TIMEOUT\n"
            exit_code = -1
        log_path = STAGE / f"fast_{name}.log"
        log_path.write_text(output, encoding="utf-8")
        result_lines = re.findall(r"^RESULT: (?:PASS|FAIL).*?$", output, re.MULTILINE)
        status = "PASS" if (exit_code == 0 and len(result_lines) == 1 and
                            result_lines[0].startswith(f"RESULT: PASS {name} ") and
                            f"CHECK: {name} CPU loaded" in output) else "FAIL"
        rows.append((name, status, "known_gap" if name in ("fence_i", "ma_data") else "supported",
                     result_lines[-1] if result_lines else f"exit={exit_code}"))
        print(f"{name:9} {status:4} {rows[-1][3]}", flush=True)
    with (STAGE / "fast_summary.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(("test", "status", "expectation", "result"))
        writer.writerows(rows)
    passed = sum(status == "PASS" for _, status, _, _ in rows)
    print(f"TOTAL {passed}/{len(rows)} PASS; summary={STAGE / 'fast_summary.csv'}")
    # Only the known trap report is tolerated for the two unsupported cases;
    # a loader error or timeout in either case must still fail the run.
    return 0 if all(status == "PASS" or
                    (expectation == "known_gap" and
                     result.startswith(f"RESULT: FAIL {name} DDR RV32I tohost=00000539"))
                    for name, status, expectation, result in rows) else 1


if __name__ == "__main__":
    raise SystemExit(main())
