"""Task030 diagnostic only: why is the TB load_use probe (LOAD coverage) never asserted?

Frozen TB / manifest / fixtures / RTL / oracle are NOT modified. This script derives a
per-cycle probe TB from sim/cpu_branch_turnover/tb_branch_turnover.sv, writes it into a
NEW tag directory and runs the key suite once, printing load_use and its terms for the
load_branch_jalr case.
"""
from pathlib import Path
import json, subprocess, sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'sim/mini_board_migration'))
from resume_inst_drm64 import command  # noqa: E402

MS = Path('D:/modelsim/win64pe')
TAG = 'diag_load_use_20261014_c'
FROZEN_TB = HERE / 'tb_branch_turnover.sv'
OLD_MODULE = 'module tb_branch_turnover #'
NEW_MODULE = 'module tb_branch_turnover_diag2 #'
ANCHOR = '''            if(dut.load_use) load_stalls=load_stalls+1;'''
PROBE = ANCHOR + '''
            if(name=="load_branch_jalr") $display("PROBE cy=%0d pc=%h lu=%b ixv=%b ixl=%b ixw=%b ixrd=%0d rs1=%0d rs2=%0d u1=%b u2=%b ifidv=%b dps=%b fire=%b exmemv=%b done=%b",cycle,dut.pc,dut.load_use,dut.id_ex_valid,dut.id_ex_i_l,dut.id_ex_gf_we,dut.id_ex_rd,dut.rs1,dut.rs2,dut.uses_rs1,dut.uses_rs2,dut.if_id_valid,dut.data_pipeline_stall,dut.id_fire,dut.ex_mem_valid,dut.ex_mem_complete);'''


def main():
    m = json.loads((HERE / 'inputs.json').read_text(encoding='utf-8'))
    text = FROZEN_TB.read_bytes().decode('utf-8')
    assert text.count(OLD_MODULE) == 1 and text.count(ANCHOR) == 1
    diag = text.replace(OLD_MODULE, NEW_MODULE).replace(ANCHOR, PROBE)

    out = HERE / 'build' / TAG
    out.mkdir(parents=True, exist_ok=False)
    diag_tb = out / 'tb_branch_turnover_diag2.sv'
    diag_tb.write_bytes(diag.encode('utf-8'))
    (out / 'diag_tb.diff.json').write_text(json.dumps(dict(
        source=str(FROZEN_TB.relative_to(ROOT)).replace('\\', '/'),
        derived=str(diag_tb.relative_to(ROOT)).replace('\\', '/'),
        substitutions=[OLD_MODULE, 'insert per-cycle PROBE $display after the load_use counter line'],
        line_count=len(diag.splitlines())), indent=2) + '\n', encoding='utf-8')
    (out / 'inputs.json').write_bytes((HERE / 'inputs.json').read_bytes())

    sources = [n for n in m['compile_sources'] if Path(n).name != FROZEN_TB.name]
    command([MS / 'vlib.exe', out / 'work'], out, out / 'vlib', 60)
    log = command([MS / 'vlog.exe', '-sv', '-work', out / 'work',
                   '+incdir+' + (ROOT / 'myriscv').as_posix(),
                   *[Path(n) for n in m['vendor_compile_sources']],
                   *[ROOT / n for n in sources], diag_tb], out, out / 'compile', 60)
    assert 'Errors: 0, Warnings: 0' in log

    argv = [str(MS / 'vsim.exe'), '-batch', '-lib', str(out / 'work'), 'tb_branch_turnover_diag2',
            '-gENABLE=1', '+SPECS=' + str(HERE / 'fixtures/key_specs.txt'), '+CASES=9',
            '+EVENT_LOG=' + str(out / 'key.events.log'),
            '-logfile', str(out / 'key.transcript'), '-do', 'run -all; quit -f']
    p = subprocess.run(argv, cwd=str(out), capture_output=True, text=True, errors='replace')
    (out / 'key.log').write_text(p.stdout + p.stderr, encoding='utf-8')
    (out / 'key.command.json').write_text(json.dumps(
        dict(argv=argv, cwd=str(out), exit_code=p.returncode), indent=2) + '\n', encoding='utf-8')
    lines = (out / 'key.log').read_text(encoding='utf-8').splitlines()
    for line in lines:
        if 'PROBE' in line or 'CHECK:' in line or 'RESULT' in line or 'Errors:' in line:
            print(line)


if __name__ == '__main__':
    main()
