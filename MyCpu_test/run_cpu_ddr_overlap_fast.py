#!/usr/bin/env python3
"""Check CPU-originated instruction/data DDR overlap with the fast SoC model."""

from __future__ import annotations

import argparse
import re
import subprocess
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
STAGE = ROOT / "MyCpu_test" / "ddr_stage"
SIM = ROOT / "sim"
DEFAULT_CASES = ("ld_st", "lb", "st_ld", "sw", "lw")
SOURCES = (
    "source/tb_soc_ddr3_rv32i_mem.v",
    "source/tb_soc_ddr3_rv32i_fast.v",
    "source/tb_cpu_ddr_overlap_fast.v",
    "myriscv/alu.v", "myriscv/br_alu.v", "myriscv/l_alu.v",
    "myriscv/regfile.v", "myriscv/csr_file.v", "myriscv/mycpu_sync.v",
    "myriscv/inst_bus_interconnect.v", "myriscv/data_bus_interconnect.v",
    "myriscv/inst_bram_adapter.v", "myriscv/data_bram_adapter.v",
    "myriscv/simple_mmio.v", "myriscv/dual_sram_to_pango_ddr_bridge.v",
    "myriscv/soc_top.v",
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backpressure", action="store_true",
                        help="hold one CPU fetch ready after a DDR load/store")
    parser.add_argument("cases", nargs="*")
    args = parser.parse_args()
    cases = args.cases or (("ld_st",) if args.backpressure else DEFAULT_CASES)
    tohost = dict(line.split() for line in
                  (STAGE / "tohost.tsv").read_text(encoding="ascii").splitlines())
    with tempfile.TemporaryDirectory(prefix="cpu_ddr_overlap_") as temp_dir:
        binary = Path(temp_dir) / "overlap.vvp"
        sources = list(SOURCES)
        top = "tb_cpu_ddr_overlap_fast"
        if args.backpressure:
            sources[sources.index("source/tb_cpu_ddr_overlap_fast.v")] = (
                "source/tb_cpu_ddr_backpressure_fast.v")
            top = "tb_cpu_ddr_backpressure_fast"
        compile_cmd = [
            "D:/iverilog/bin/iverilog.exe", "-g2012", "-Imyriscv",
            "-s", top, "-o", str(binary), *sources,
        ]
        compiled = subprocess.run(compile_cmd, cwd=ROOT, capture_output=True,
                                  text=True)
        if compiled.returncode:
            print(compiled.stdout + compiled.stderr)
            return compiled.returncode

        failed = False
        for name in cases:
            if name not in tohost or not (STAGE / f"{name}.dat").is_file():
                raise ValueError(f"missing staged image or tohost for {name}")
            command = [
                "D:/iverilog/bin/vvp.exe", str(binary),
                f"+BOOT={(STAGE / 'boot_rom.dat').as_posix()}",
                f"+IMAGE={(STAGE / (name + '.dat')).as_posix()}",
                f"+TEST={name}", f"+TOHOST={tohost[name]}",
            ]
            result = subprocess.run(command, cwd=ROOT, capture_output=True,
                                    text=True, timeout=90)
            output = result.stdout + result.stderr
            log_stem = "cpu_ddr_backpressure_fast" if args.backpressure else "cpu_ddr_overlap_fast"
            (SIM / f"{log_stem}_{name}.log").write_text(
                output, encoding="utf-8")
            match = re.search(
                r"OBS: CPU origin both=(\d+) DDR both=(\d+) "
                r"idle_priority=(\d+) inst_grants=(\d+)", output)
            passed = (result.returncode == 0 and
                      len(re.findall(r"^RESULT: PASS ", output, re.M)) == 1 and
                      f"RESULT: PASS {name} DDR RV32I tohost=1" in output and
                      "RESULT: FAIL" not in output)
            if args.backpressure:
                passed &= "CHECK: CPU-origin DDR overlap" in output
            else:
                passed &= (match is not None and
                           int(match.group(1)) > 0 and int(match.group(2)) > 0 and
                           int(match.group(3)) > 0 and int(match.group(4)) > 0)
            failed |= not passed
            print(f"{name}: {'PASS' if passed else 'FAIL'}")
            if match and not args.backpressure:
                print(f"  CPU both={match.group(1)} DDR both={match.group(2)} "
                      f"idle priority={match.group(3)} inst grants={match.group(4)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
