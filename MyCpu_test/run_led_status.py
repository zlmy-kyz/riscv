#!/usr/bin/env python3
"""Check the LED/MMIO state machine, byte enables, watchdog and reset."""
from __future__ import annotations

import subprocess
from run_ddr_rv32i_fast import IVERILOG, ROOT, VVP


def main() -> int:
    binary = ROOT / "sim" / "led_status.vvp"
    comp = subprocess.run([str(IVERILOG), "-g2012", "-s", "tb_soc_ddr3_leds",
                           "-o", str(binary), "myriscv/simple_mmio.v",
                           "myriscv/soc_ddr3_top.v", "source/tb_soc_ddr3_leds.v"],
                          cwd=ROOT, capture_output=True, text=True, timeout=30)
    (ROOT / "sim" / "led_status_compile.log").write_text(
        comp.stdout + comp.stderr, encoding="utf-8")
    if comp.returncode:
        print("FAIL LED compile; see sim/led_status_compile.log")
        return 1
    run = subprocess.run([str(VVP), str(binary)], cwd=ROOT,
                         capture_output=True, text=True, timeout=30)
    output = run.stdout + run.stderr
    (ROOT / "sim" / "led_status.log").write_text(output, encoding="utf-8")
    print(output, end="")
    return 0 if (run.returncode == 0 and output.count("RESULT: PASS") == 1 and
                 "RESULT: FAIL" not in output) else 1


if __name__ == "__main__":
    raise SystemExit(main())
