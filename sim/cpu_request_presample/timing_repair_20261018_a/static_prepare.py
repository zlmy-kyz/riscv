"""036 conflict-vector CE repair: preserve changed evidence, static elaboration only."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
PRIOR = ROOT/'sim/cpu_request_presample/preparation_20261018_a'
TARGET = 'myriscv/dual_sram_to_pango_ddr_bridge.v'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')

def record_git(name, args):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True)
    (HERE/name).write_bytes(r.stdout+r.stderr)

def snapshot():
    prior = json.loads((PRIOR/'after_manifest.json').read_text(encoding='utf-8'))
    current = {rel:digest(ROOT/rel) for rel in prior}
    observed = [k for k in prior if prior[k] != current[k]]
    assert set(observed) <= {'RISCV.pds', 'report_timing/board_top.rtr'}, observed
    assert current[TARGET] == '34e9fa3851163c4912f0a9fbed65ae73b8494638c5dfa788fd540b291f4c7fe2'
    (HERE/'before').mkdir(exist_ok=False)
    # Reuse unchanged input snapshots; save only the implemented bridge/report/PDS.
    copied = sorted(set(observed)|{TARGET})
    for rel in copied:
        dst = HERE/'before'/rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((ROOT/rel).read_bytes())
    save('before_manifest.json', current)
    save('snapshot_index.json', {'previous_manifest':str(PRIOR/'after_manifest.json'),
        'changed_since_036_preparation':observed, 'copied_inputs':copied,
        'remaining_inputs':'Unchanged; reuse previous preparation inputs and hashes.'})
    save('timing_observation.json', {'report':'report_timing/board_top.rtr',
        'sha256':current['report_timing/board_top.rtr'], 'report_date':'Sun Oct 18 01:43:54 2026',
        'core_mhz':93.75, 'slow_wns_ns':-0.034, 'slow_tns_ns':-0.045, 'failing_endpoints':2,
        'estimated_fmax_mhz':93.4521, 'source':'u_soc/u_soc/u_cpu/if_id_inst[17]',
        'endpoints':['inst_overlap_line_match_q[0]/CE','inst_overlap_line_match_q[5]/CE'],
        'logic_levels':13, 'logic_ns':2.603, 'route_ns':7.629,
        'limits':'Observed report and current source identities; not an independently reconstructed implementation input set.'})
    record_git('git_before.txt', ['status','--porcelain=v1','-uall'])
    record_git('bridge_before_head.diff', ['diff','--',TARGET])
    print(json.dumps({'status':'SNAPSHOT_ONLY','inputs':len(current),'copied':copied}))

def review():
    if (HERE/'review.json').exists():
        raise RuntimeError('preserve existing review')
    before = json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    after = {k:digest(ROOT/k) for k in before}
    changed = [k for k in before if before[k] != after[k]]
    assert changed == [TARGET], changed
    for rel in json.loads((HERE/'snapshot_index.json').read_text(encoding='utf-8'))['copied_inputs']:
        assert digest(HERE/'before'/rel) == before[rel]
    old = (HERE/'before'/TARGET).read_text(encoding='utf-8')
    new = (ROOT/TARGET).read_text(encoding='utf-8')
    block = re.search(r'    // 036 timing repair:.*?    // End 036 conflict sampling\.\n', new, re.S)
    assert block is not None
    stripped = new[:block.start()]+new[block.end():]
    reduced = re.sub(r'^[ \t]*inst_overlap_line_match_q\s*<=.*?;\n', '', old, flags=re.M|re.S)
    assert reduced == stripped, 'changes escaped conflict-vector sampling'
    assert 'take_inst' not in block.group() and 'inst_req_valid' not in block.group()
    (HERE/'bridge.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),
        new.splitlines(True), 'before/'+TARGET, 'after/'+TARGET)), encoding='utf-8')
    save('after_manifest.json', after)
    (HERE/'checks_01').mkdir(exist_ok=False)
    checks = []
    for check in json.loads((PRIOR/'review.json').read_text(encoding='utf-8'))['checks']:
        r = subprocess.run(check['argv'], cwd=ROOT, capture_output=True, timeout=60)
        output = (r.stdout+r.stderr).decode('utf-8', errors='replace')
        (HERE/'checks_01'/(check['name']+'.log')).write_text(output, encoding='utf-8')
        checks.append(dict(check, exit_code=r.returncode, output=output))
        if r.returncode:
            save('static_failure.json', checks)
            raise RuntimeError(check['name'])
    subprocess.run(['git','diff','--check','--',TARGET], cwd=ROOT, check=True)
    record_git('git_after.txt', ['status','--porcelain=v1','-uall'])
    save('review.json', {'status':'TASK036_CONFLICT_CE_STATIC_REPAIR_PENDING_USER_PDS',
        'changed':changed, 'before_sha256':before[TARGET], 'after_sha256':after[TARGET],
        'unchanged_inputs':len(after)-1, 'checks':checks,
        'scope_check':'Only inst_overlap_line_match_q sampling moved; all remaining RTL text identical.',
        'dynamic_simulation':'NOT_RUN', 'pds':'NOT_RUN', 'board':'NOT_RUN',
        'limits':'Null-target elaboration; real cache port wrappers, missing vendor internals blackboxed by -i. No timing or dynamic equivalence PASS.'})
    print(json.dumps({'status':'STATIC_REPAIR_PENDING_USER_PDS','checks':len(checks),'bridge':after[TARGET]}))

if __name__ == '__main__':
    {'snapshot':snapshot,'review':review}[sys.argv[1]]()
