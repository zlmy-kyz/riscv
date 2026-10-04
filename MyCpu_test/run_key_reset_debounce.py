#!/usr/bin/env python3
"""Exercise reset-button filtering and the board clock/reset dependency."""
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / 'sim/key_reset_debounce'

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for top in ('tb_reset_button_debounce', 'tb_board_key_reset'):
        binary = OUT / (top + '.vvp')
        compile_run = subprocess.run([
            'D:/iverilog/bin/iverilog.exe', '-g2012', '-DKEY_RESET_BOARD_STUB',
            '-s', top, '-o', str(binary), 'myriscv/reset_button_debounce.v',
            'myriscv/board_top.v', 'source/tb_reset_button_debounce.v'
        ], cwd=ROOT, capture_output=True, text=True, timeout=30)
        (OUT / (top + '_compile.log')).write_text(compile_run.stdout + compile_run.stderr, encoding='utf-8')
        if compile_run.returncode:
            print(compile_run.stdout + compile_run.stderr)
            return 1
        run = subprocess.run(['D:/iverilog/bin/vvp.exe', str(binary)], cwd=ROOT,
                             capture_output=True, text=True, timeout=90)
        output = run.stdout + run.stderr
        (OUT / (top + '.log')).write_text(output, encoding='utf-8')
        print(output, end='')
        if run.returncode or output.count('RESULT: PASS') != 1:
            return 1
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
