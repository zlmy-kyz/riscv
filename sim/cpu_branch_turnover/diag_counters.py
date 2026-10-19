"""Task030 diagnostic only: rerun the key suite with the frozen TB plus a counter printout.

The frozen TB / manifest / fixtures / RTL / oracle are NOT modified. This script
reads sim/cpu_branch_turnover/tb_branch_turnover.sv, applies exactly two textual
changes (module rename + one extra $display of the 12 coverage counters), writes the
derived TB into a NEW tag directory, and runs the key suite once.
"""
from pathlib import Path
import json, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'sim/mini_board_migration'))
from resume_inst_drm64 import command  # noqa: E402

MS = Path('D:/modelsim/win64pe')
TAG = 'diag_counters_20261014_b'
FROZEN_TB = HERE / 'tb_branch_turnover.sv'
OLD_MODULE = 'module tb_branch_turnover #'
NEW_MODULE = 'module tb_branch_turnover_diag #'
OLD_DISPLAY = '$display("CHECK: %s PASS events=%0d cycles=%0d",name,index,cycle);'
NEW_DISPLAY = ('$display("CHECK: %s PASS events=%0d cycles=%0d DIAG FAST=%0d EMPTY=%0d RSP=%0d '
               'LATE=%0d READY=%0d BUFFER=%0d DROP_ERR=%0d LOAD=%0d TRAP=%0d IRQ=%0d RESET=%0d '
               'CASES=%0d",name,index,cycle,fast,empty_fast,response_fast,late_wait,ready_wait,'
               'buffer_flush,discarded_errors,load_stalls,traps,irqs,resets,case_count);')


def main():
    m = json.loads((HERE / 'inputs.json').read_text(encoding='utf-8'))
    text = FROZEN_TB.read_bytes().decode('utf-8')
    assert text.count(OLD_MODULE) == 1 and text.count(OLD_DISPLAY) == 1
    diag = text.replace(OLD_MODULE, NEW_MODULE).replace(OLD_DISPLAY, NEW_DISPLAY)

    out = HERE / 'build' / TAG
    out.mkdir(parents=True, exist_ok=False)
    diag_tb = out / 'tb_branch_turnover_diag.sv'
    diag_tb.write_bytes(diag.encode('utf-8'))
    (out / 'diag_tb.diff.json').write_text(json.dumps(dict(
        source=str(FROZEN_TB.relative_to(ROOT)).replace('\\', '/'),
        derived=str(diag_tb.relative_to(ROOT)).replace('\\', '/'),
        substitutions=[OLD_MODULE, OLD_DISPLAY],
        changed_lines=[i + 1 for i, (a, b) in
                       enumerate(zip(text.splitlines(), diag.splitlines())) if a != b],
        line_count=len(diag.splitlines())), indent=2) + '\n', encoding='utf-8')
    (out / 'inputs.json').write_bytes((HERE / 'inputs.json').read_bytes())

    sources = [n for n in m['compile_sources'] if Path(n).name != FROZEN_TB.name]
    command([MS / 'vlib.exe', out / 'work'], out, out / 'vlib', 60)
    log = command([MS / 'vlog.exe', '-sv', '-work', out / 'work',
                   '+incdir+' + (ROOT / 'myriscv').as_posix(),
                   *[Path(n) for n in m['vendor_compile_sources']],
                   *[ROOT / n for n in sources], diag_tb], out, out / 'compile', 60)
    assert 'Errors: 0, Warnings: 0' in log

    argv = [str(MS / 'vsim.exe'), '-batch', '-lib', str(out / 'work'), 'tb_branch_turnover_diag',
            '-gENABLE=1', '+SPECS=' + str(HERE / 'fixtures/key_specs.txt'), '+CASES=9',
            '+EVENT_LOG=' + str(out / 'key.events.log'),
            '-logfile', str(out / 'key.transcript'), '-do', 'run -all; quit -f']
    p = subprocess.run(argv, cwd=str(out), capture_output=True, text=True, errors='replace')
    (out / 'key.log').write_text(p.stdout + p.stderr, encoding='utf-8')
    (out / 'key.command.json').write_text(json.dumps(
        dict(argv=argv, cwd=str(out), exit_code=p.returncode), indent=2) + '\n', encoding='utf-8')
    for line in (out / 'key.log').read_text(encoding='utf-8').splitlines():
        if 'CHECK:' in line or 'RESULT' in line or 'Fatal' in line or 'Errors:' in line:
            print(line)


if __name__ == '__main__':
    main()
