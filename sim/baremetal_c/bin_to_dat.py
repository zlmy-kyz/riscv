"""Compatibility entry point; test image construction lives with each experiment."""
from pathlib import Path
import runpy

CONVERTER = Path(__file__).resolve().parents[2] / "tests/fpga_uart_pc_output_30/bin_to_dat.py"

if __name__ == "__main__":
    runpy.run_path(str(CONVERTER), run_name="__main__")
else:
    convert = runpy.run_path(str(CONVERTER))["convert"]
