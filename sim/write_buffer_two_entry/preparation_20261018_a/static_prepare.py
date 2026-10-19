"""043 input snapshot and null-target elaboration; never executes HDL or PDS."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def snapshot():
    assert not (HERE/'before_manifest.json').exists(), 'Preserve prior inputs'
    prior = json.loads((ROOT/'sim/cpu_cache_perf/diagnostics_20261018_a/after_manifest.json').read_text(encoding='utf-8'))
    current = {n:sha(ROOT/n) for n in prior}
    prior_changes = [n for n in prior if current[n] != prior[n]]
    assert set(prior_changes) <= {'RISCV.pds', 'report_timing/board_top.rtr'}, prior_changes
    (HERE/'before').mkdir()
    (HERE/'before'/Path(BRIDGE).name).write_bytes((ROOT/BRIDGE).read_bytes())
    save('before_manifest.json', current)
    save('prior_artifact_changes.json', {n:dict(task042=prior[n], current=current[n]) for n in prior_changes})
    print('043 baseline saved; 042 RTL/IP inputs unchanged; current PDS/report identities recorded')

def review():
    assert not (HERE/'review.json').exists(), 'Preserve prior review'
    before = json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    after = {n:sha(ROOT/n) for n in before}
    changed = [n for n in before if before[n] != after[n]]
    assert changed == [BRIDGE], changed
    old = (HERE/'before'/Path(BRIDGE).name).read_text(encoding='utf-8')
    new = (ROOT/BRIDGE).read_text(encoding='utf-8')
    marker = '    // 042 wait observation'
    assert old[old.index(marker):] == new[new.index(marker):], 'Observation body changed'
    (HERE/'after').mkdir()
    (HERE/'after'/Path(BRIDGE).name).write_bytes((ROOT/BRIDGE).read_bytes())
    (HERE/'bridge.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True), 'before/'+BRIDGE, 'after/'+BRIDGE)), encoding='utf-8')
    sources = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'myriscv').glob('*.v'))
    sources += ['ipcore/icache/icache.v', 'ipcore/dcache/dcache.v']
    configs = [('board', 'board_top', {}), ('soc_no_ddr', 'soc_top', {}),
               ('soc_x32', 'soc_top', {'ENABLE_DDR':1, 'DDR_MEM_DQ_WIDTH':32}),
               ('soc_perf_off', 'soc_top', {'ENABLE_DDR':1, 'DDR_MEM_DQ_WIDTH':32, 'PERF_ENABLE':0})]
    base = {'MEM_DQ_WIDTH':32, 'POSTED_WRITE_ENABLE':1, 'CACHE_PERF_ENABLE':1, 'DIAG_PERF_ENABLE':1}
    variants = [('depth2', {}), ('depth1', {'WRITE_BUFFER_DEPTH':1}),
                ('nonposted', {'POSTED_WRITE_ENABLE':0}), ('x16', {'MEM_DQ_WIDTH':16}),
                ('no_forward', {'DATA_STORE_FORWARD_ENABLE':0}),
                ('no_overlap', {'DATA_READ_UNDER_WRITE_ENABLE':0}),
                ('no_turnover', {'WRITE_BUFFER_TURNOVER_ENABLE':0}),
                ('no_icache', {'INST_LINE_BUFFER_ENABLE':0}),
                ('no_dcache', {'DATA_LINE_BUFFER_ENABLE':0}),
                ('no_counters', {'CACHE_PERF_ENABLE':0, 'DIAG_PERF_ENABLE':0})]
    configs += [('bridge_'+name, 'dual_sram_to_pango_ddr_bridge', dict(base, **params)) for name,params in variants]
    checks = []
    for name,top,params in configs:
        argv = ['D:/iverilog/bin/iverilog.exe', '-g2005', '-tnull', '-i', '-I', 'myriscv', '-s', top]
        for key,value in params.items():
            argv += ['-P', f'{top}.{key}={value}']
        argv += sources
        result = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
        output = (result.stdout+result.stderr).decode('utf-8', errors='replace')
        (HERE/(name+'.log')).write_text(output, encoding='utf-8')
        checks.append(dict(name=name, argv=argv, exit_code=result.returncode, output=output))
        if result.returncode:
            save('static_failure.json', checks)
            raise RuntimeError(name)
    subprocess.run(['git','diff','--check','--',BRIDGE], cwd=ROOT, check=True)
    assert after == {n:sha(ROOT/n) for n in before}, 'Inputs changed during static review'
    save('after_manifest.json', after)
    save('review.json', dict(status='TASK043_TWO_ENTRY_STATIC_ONLY_PENDING_USER_PDS',
        changed=changed, before_sha256=before[BRIDGE], after_sha256=after[BRIDGE],
        unchanged_inputs=len(before)-1, checks=checks,
        HDL_execution='NOT_RUN', PDS='NOT_RUN', board='NOT_RUN',
        limits='Null-target elaboration; vendor internals blackboxed. No functional or timing PASS.'))
    print('043 static only:', len(checks), 'elaborations passed; only bridge changed')

if __name__ == '__main__':
    {'snapshot':snapshot, 'review':review}[sys.argv[1]]()
