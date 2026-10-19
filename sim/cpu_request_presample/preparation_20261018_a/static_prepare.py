"""036 preparation: preserve inputs and elaborate only. No simulation/PDS/board."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TARGET = 'myriscv/dual_sram_to_pango_ddr_bridge.v'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (HERE/name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def sources():
    prior = ROOT/'sim/cpu_dual_read/rdata_timing_repair_20261018_a/after_manifest.json'
    names = set(json.loads(prior.read_text(encoding='utf-8')))
    names.update(p.relative_to(ROOT).as_posix() for p in (ROOT/'myriscv').rglob('*') if p.is_file())
    names.update([
        prior.relative_to(ROOT).as_posix(),
        'sim/cpu_dual_read/board/review_20261018_01/board_review.json',
        'sim/cpu_dual_read/timing_review_20261018_a/review.json'])
    return sorted(names)

def git_record(name, args):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True)
    (HERE/name).write_bytes(r.stdout+r.stderr)

def snapshot():
    (HERE/'before').mkdir(exist_ok=False)
    manifest = {}
    for rel in sources():
        dst = HERE/'before'/rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        dst.write_bytes((ROOT/rel).read_bytes())
        manifest[rel] = digest(dst)
    assert manifest[TARGET] == '1abf54fe01fb76659943fd14818154cfffe1bde23cd9f996b711b185452afe67'
    save('before_manifest.json', manifest)
    git_record('git_before.txt', ['status', '--porcelain=v1', '-uall'])
    git_record('bridge_before_head.diff', ['diff', '--', TARGET])
    git_record('head.txt', ['rev-parse', 'HEAD'])
    print(json.dumps({'status':'SNAPSHOT_ONLY', 'inputs':len(manifest), 'bridge':manifest[TARGET]}))

def review():
    if (HERE/'review.json').exists():
        raise RuntimeError('preserve existing receipt')
    before = json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    after = {rel:digest(ROOT/rel) for rel in sources()}
    changed = [k for k in sorted(set(before)|set(after)) if before.get(k) != after.get(k)]
    assert changed == [TARGET], changed
    assert all(digest(HERE/'before'/k) == v for k,v in before.items())
    old = (HERE/'before'/TARGET).read_text(encoding='utf-8')
    new = (ROOT/TARGET).read_text(encoding='utf-8')
    save('after_manifest.json', after)
    (HERE/'bridge.patch').write_text(''.join(difflib.unified_diff(
        old.splitlines(True), new.splitlines(True), 'before/'+TARGET, 'after/'+TARGET)), encoding='utf-8')
    # Mechanical check of the intended narrow transformation; not a formal proof.
    fields = ('request_ctrl_addr', 'request_lane', 'request_line_tag')
    reduced = lambda s: re.sub(r'^[ \t]*(?:'+'|'.join(fields)+r')\s*<=.*?;\n', '', s,
                              flags=re.MULTILINE|re.DOTALL)
    block = re.search(r'    // 036:.*?    // End 036 field sampling\.\n', new, re.DOTALL)
    assert block is not None
    strip_added = new[:block.start()] + new[block.end():]
    strip_added = strip_added.replace('    wire [31:0] field_sample_addr;\n', '')
    assert reduced(old) == reduced(strip_added), 'change escaped the three-field sampling scope'
    assert 'take_inst' not in block.group() and 'inst_req_valid' not in block.group()
    src = [p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'myriscv').glob('*.v'))]
    src += ['ipcore/icache/icache.v', 'ipcore/dcache/dcache.v']
    bridge = 'dual_sram_to_pango_ddr_bridge'
    configs = [('board', 'board_top', {}),
        ('x32', bridge, {'MEM_DQ_WIDTH':32}),
        ('posted', bridge, {'MEM_DQ_WIDTH':32, 'POSTED_WRITE_ENABLE':1}),
        ('only035', bridge, {'MEM_DQ_WIDTH':32, 'INST_HIT_UNDER_DATA_MISS_ENABLE':0}),
        ('only033', bridge, {'MEM_DQ_WIDTH':32, 'INST_WITH_DATA_REQ_ENABLE':0}),
        ('serial', bridge, {'MEM_DQ_WIDTH':32, 'INST_WITH_DATA_REQ_ENABLE':0, 'INST_HIT_UNDER_DATA_MISS_ENABLE':0}),
        ('no_dcache', bridge, {'MEM_DQ_WIDTH':32, 'DATA_LINE_BUFFER_ENABLE':0}),
        ('no_icache', bridge, {'MEM_DQ_WIDTH':32, 'INST_LINE_BUFFER_ENABLE':0}),
        ('x16', bridge, {})]
    logs = HERE/'checks_01'
    logs.mkdir(exist_ok=False)
    checks = []
    for name,top,params in configs:
        argv = ['D:/iverilog/bin/iverilog.exe', '-g2005', '-tnull', '-i', '-I', 'myriscv', '-s', top]
        for k,v in params.items():
            argv += ['-P', f'{top}.{k}={v}']
        argv += src
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
        output = (r.stdout+r.stderr).decode('utf-8', errors='replace')
        (logs/(name+'.log')).write_text(output, encoding='utf-8')
        checks.append({'name':name, 'cwd':str(ROOT), 'argv':argv, 'exit_code':r.returncode, 'output':output})
        if r.returncode:
            save('static_failure.json', checks)
            raise RuntimeError(name)
    subprocess.run(['git', 'diff', '--check', '--', TARGET], cwd=ROOT, check=True)
    git_record('git_after.txt', ['status', '--porcelain=v1', '-uall'])
    save('review.json', {'status':'TASK036_STATIC_ONLY_PENDING_USER_PDS', 'changed':changed,
        'before_sha256':before[TARGET], 'after_sha256':after[TARGET], 'unchanged_inputs':len(after)-1,
        'scope_check':'After removing only the new field block and all assignments to the three fields, old/new text is identical.',
        'checks':checks, 'dynamic_simulation':'NOT_RUN', 'pds':'NOT_RUN', 'board':'NOT_RUN',
        'limits':'Null-target syntax/elaboration with real cache port wrappers; missing vendor internals blackboxed by -i. No timing/performance or dynamic equivalence claim.'})
    print(json.dumps({'status':'TASK036_STATIC_ONLY_PENDING_USER_PDS', 'checks':len(checks), 'bridge':after[TARGET]}))

if __name__ == '__main__':
    {'snapshot':snapshot, 'review':review}[sys.argv[1]]()
