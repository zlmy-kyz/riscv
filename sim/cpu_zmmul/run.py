"""Task023 single real-Pango multiplier CPU suite; first failure stop, no PDS/board."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'sim/mini_board_migration'))
from resume_inst_drm64 import command
from resume_inst_cache32 import pds_shell_count, git_snapshot

MS = Path('D:/modelsim/win64pe')
VENDOR = Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
MANIFEST = HERE / 'inputs.json'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
write = lambda p, obj: p.write_text(json.dumps(obj, indent=2)+'\n', encoding='utf-8')
read = lambda p: p.read_text(encoding='utf-8', errors='replace')


def require_inputs():
    m = json.loads(read(MANIFEST))
    for n, h in m['sha256'].items():
        assert sha(ROOT/n) == h, 'Changed protected input: '+n
    for n, h in m['external_sha256'].items():
        assert sha(n) == h, 'Changed external input: '+n
    plan = json.loads(read(HERE/'test_plan.json'))
    assert plan == m['test_plan']
    assert [x['name'] for x in plan['isa_cases']] == ['lhu', 'or']
    assert sum(c['events'] for c in plan['cases']) == 2839
    assert sum(c['mul_retirements'] for c in plan['cases']) == 396
    assert plan['raw_ip_vectors'] == 128 and plan['multiply_math_vectors'] == 384
    ip = read(ROOT/'ipcore/mul/mul.v')
    parameters = dict(re.findall(r'localparam\s+(\w+)\s*=\s*(\d+)\s*;', ip))
    assert all(parameters[k] == str(v) for k,v in m['ip_parameters'].items())
    cpu = read(ROOT/'myriscv/mycpu_sync.v')
    assert '.rst(!resetn)' in cpu and 'mul u_mul' in cpu
    assert "!funct3[2]" in cpu and 'mul_product[63:32]' in cpu
    assert "`define RV_MISA_RV32I       32'h4000_0100" in read(ROOT/'myriscv/csr_defs.vh') or \
           "32'h4000_0100" in read(ROOT/'myriscv/csr_defs.vh')
    project = read(ROOT/'RISCV.pds')
    for p in m['ip_sources']:
        assert project.count('"'+p+'"') == 1, p
    for p in ['prepare_tests.py', 'run.py']:
        ast.parse(read(HERE/p))
    # Catch invalid hierarchical observations before delegating compile to DeepSeek.
    for name in set(re.findall(r'\bdut\.(\w+)', read(HERE/'tb_cpu_zmmul.sv'))):
        assert re.search(r'\b'+name+r'\b', cpu), 'Unknown CPU probe: '+name
    return m


def check_log(console, transcript, expected):
    for output in (console, transcript):
        assert len(re.findall(re.escape(expected), output)) == 1, expected
        assert '$finish' in output and re.search(r'Errors:\s*0,\s*Warnings:\s*0', output)
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', output)
    def normalized(s):
        return '\n'.join(s.replace('\r\n','\n').replace('\r','\n').splitlines()).strip()
    assert normalized(console) == normalized(transcript), 'Console/transcript differ'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-inputs', action='store_true')
    parser.add_argument('--tag')
    args = parser.parse_args()
    m = require_inputs()
    if args.check_inputs:
        print('INPUTS_MATCH_NOT_SIMULATED', len(m['sha256']), 'IP=128 CPU_events=2839 muls=396 ISA=lhu,or seed=2026101323')
        return
    assert args.tag == 'ds_cpu_zmmul_20261013_a', 'Use the fixed Task023 tag only'
    assert pds_shell_count() == 0, 'Wait for user PDS completion'
    out = HERE/'build'/args.tag
    out.mkdir(parents=True, exist_ok=False)
    work = out/'work'
    before = git_snapshot()
    write(out/'git_before.json', before)
    result = dict(status='RUNNING', functional_status='INCOMPLETE', input_manifest_sha256=sha(MANIFEST),
                  completed=[], pds_started=False, serial_opened=False, board_status='NOT_TESTED')
    write(out/'result.json', result)
    try:
        # Freeze inputs before HDL; failures retain the exact invoked sources.
        frozen = {}
        for n,h in m['sha256'].items():
            dest = out/'inputs'/n
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(ROOT/n, dest)
            assert sha(dest) == h
            frozen[n] = h
        shutil.copyfile(MANIFEST, out/'inputs.json')
        write(out/'frozen_inputs.json', frozen)
        command([MS/'vlib.exe', work], out, out/'vlib', 60)
        sources = [ROOT/n for n in m['compile_sources']]
        output = command([MS/'vlog.exe', '-sv', '-work', work, '+incdir+'+(ROOT/'myriscv').as_posix(),
                          VENDOR/'GTP_GRS.v', VENDOR/'GTP_APM_E2.v', *sources], out, out/'compile', 60)
        assert re.search(r'Errors:\s*0,\s*Warnings:\s*0', output)
        jobs = [('mul_ip', 'tb_mul_ip', ['+VECTORS='+str(HERE/'fixtures/ip_vectors.txt')],
                 'RESULT: PASS mul_ip vectors=128 checks=168')]
        for c in m['test_plan']['cases']:
            name = c['name']
            plus = [f'+CASE={c["index"]}', '+NAME='+name, '+ROM='+str(HERE/'fixtures'/f'{name}_rom.hex'),
                    '+RAM='+str(HERE/'fixtures'/f'{name}_ram.hex'), '+TRACE='+str(HERE/'fixtures'/f'{name}_trace.txt'),
                    f'+EVENTS={c["events"]}', f'+MULS={c["mul_retirements"]}', f'+IRQ_PC={c.get("irq_mul_pc",0):08x}']
            jobs.append((name, 'tb_cpu_zmmul', plus, f'RESULT: PASS cpu_zmmul case={name} events={c["events"]} muls={c["mul_retirements"]}'))
        for c in m['test_plan']['isa_cases']:
            name = 'isa_'+c['name']
            plus = ['+CASE=6', '+ISA=1', '+NAME='+name, '+ROM='+str(ROOT/c['rom']), f'+STATUS={c["tohost"]:08x}']
            if c['ram']:
                plus.append('+RAM='+str(ROOT/c['ram']))
            jobs.append((name, 'tb_cpu_zmmul', plus, 'RESULT: PASS cpu_zmmul case='+name))
        for name, top, plus, expected in jobs:
            transcript = out/(name+'.transcript')
            console = command([MS/'vsim.exe', '-batch', '-lib', work, top, *plus,
                               '-logfile', transcript, '-do', 'run -all; quit -f'], out, out/name, 180)
            assert transcript.exists() and transcript.stat().st_size
            check_log(console, read(transcript), expected)
            assert re.search(r'^#?\s*CHECK: '+name+r' PASS', console, re.M) if name!='mul_ip' else 'CHECK: raw_ip_stream_ce_reset PASS' in console
            result['completed'].append(name)
            write(out/'result.json', result)
        require_inputs()
        after = git_snapshot(); write(out/'git_after.json', after)
        assert after == before, 'Git snapshot changed during HDL'
        assert len(result['completed']) == 9
        result.update(status='PASS', functional_status='PASS', cpu_events=2839, mul_retirements=396,
                      ip_vectors=128, ip_checks=168, isa_cases=['lhu','or'], untouched_inputs=True)
        print('RESULT: PASS cpu_zmmul_suite ip_vectors=128 cpu_events=2839 muls=396 isa=lhu,or')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE', functional_status='INCOMPLETE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        write(out/'result.json', result)


if __name__ == '__main__':
    main()
