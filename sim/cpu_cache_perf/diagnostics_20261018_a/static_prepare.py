"""042 observation-only snapshot and null-target elaboration; no HDL execution."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TARGETS = ['myriscv/mycpu_sync.v', 'myriscv/dual_sram_to_pango_ddr_bridge.v',
           'myriscv/simple_mmio.v', 'myriscv/soc_top.v']
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, value):
    (HERE/name).write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
def snapshot():
    assert not (HERE/'before_manifest.json').exists(), 'Preserve previous snapshot'
    prior = json.loads((ROOT/'sim/cpu_cache_perf/preparation_20261018_a/after_manifest.json').read_text(encoding='utf-8'))
    before = {n: sha(ROOT/n) for n in prior}
    assert before == prior, '041 inputs changed; review before editing'
    for n in TARGETS:
        p = HERE/'before'/n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT/n).read_bytes())
    save('before_manifest.json', before)
    r = subprocess.run(['git', 'diff', '--', *TARGETS], cwd=ROOT, capture_output=True, check=True)
    (HERE/'git_before.patch').write_bytes(r.stdout)
    print('042 BEFORE SNAPSHOT SAVED; 041 input identity preserved')
def review():
    assert not (HERE/'review.json').exists(), 'Preserve previous review'
    before = json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    after = {n: sha(ROOT/n) for n in before}
    changed = [n for n in before if before[n] != after[n]]
    assert set(changed) == set(TARGETS), changed
    for n in TARGETS:
        old = (HERE/'before'/n).read_text(encoding='utf-8')
        new = (ROOT/n).read_text(encoding='utf-8')
        p = HERE/'after'/n
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes((ROOT/n).read_bytes())
        (HERE/(Path(n).stem+'.patch')).write_text(''.join(difflib.unified_diff(
            old.splitlines(True), new.splitlines(True), 'before/'+n, 'after/'+n)), encoding='utf-8')
        if n.endswith('mycpu_sync.v'):
            a = '    // ================================================================================'
            b = '    // 042 raw observation sideband'
            assert old[old.index(a):old.rindex('endmodule')] == new[new.index(a):new.index(b)]
        if n.endswith('bridge.v'):
            a = '    localparam [2:0] STATE_IDLE'
            b = '    // 首版不根据这些返回旁带信号产生 CPU fault'
            c = '    // 042 wait observation'
            assert old[old.index(a):old.index(b)] == new[new.index(a):new.index(c)]
        if n.endswith('simple_mmio.v'):
            a = old.index('    always @(posedge clk) begin', old.index('module cpu_perf_counters'))
            b = new.index('    always @(posedge clk) begin', new.index('module cpu_perf_counters'))
            assert old[a:old.rindex('endmodule')] == new[b:new.index('    // 042 diagnostic bank')]
    save('after_manifest.json', after)
    src = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'myriscv').glob('*.v'))
    src += ['ipcore/icache/icache.v', 'ipcore/dcache/dcache.v']
    configs = [('board', 'board_top', {}), ('soc_no_ddr', 'soc_top', {}),
        ('soc_diag_off', 'soc_top', {'ENABLE_DDR':1, 'DDR_MEM_DQ_WIDTH':32, 'PERF_DIAG_ENABLE':0}),
        ('soc_perf_off', 'soc_top', {'ENABLE_DDR':1, 'DDR_MEM_DQ_WIDTH':32, 'PERF_ENABLE':0}),
        ('cpu_diag_off', 'mycpu_sync', {'DIAG_PERF_ENABLE':0}),
        ('cpu_diag_on', 'mycpu_sync', {'DIAG_PERF_ENABLE':1}),
        ('perf_diag_off', 'cpu_perf_counters', {}),
        ('perf_diag_on', 'cpu_perf_counters', {'CACHE_PERF_ENABLE':1, 'DIAG_PERF_ENABLE':1})]
    for width, ic, dc, diag in [(16,1,1,1), (32,1,1,1), (32,0,1,1), (32,1,0,1), (32,1,1,0)]:
        configs.append((f'bridge_{width}_{ic}{dc}_{diag}', 'dual_sram_to_pango_ddr_bridge',
            {'MEM_DQ_WIDTH':width, 'INST_LINE_BUFFER_ENABLE':ic, 'DATA_LINE_BUFFER_ENABLE':dc,
             'CACHE_PERF_ENABLE':1, 'DIAG_PERF_ENABLE':diag, 'POSTED_WRITE_ENABLE':1}))
    checks = []
    for name, top, params in configs:
        argv = ['D:/iverilog/bin/iverilog.exe', '-g2005', '-tnull', '-i', '-I', 'myriscv', '-s', top]
        for k,v in params.items(): argv += ['-P', f'{top}.{k}={v}']
        argv += src
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
        output = (r.stdout+r.stderr).decode('utf-8', errors='replace')
        (HERE/(name+'.log')).write_text(output, encoding='utf-8')
        checks.append(dict(name=name, argv=argv, exit_code=r.returncode, output=output))
        if r.returncode:
            save('static_failure.json', checks)
            raise RuntimeError(name)
    subprocess.run(['git','diff','--check','--',*TARGETS], cwd=ROOT, check=True)
    save('review.json', dict(status='TASK042_DIAGNOSTICS_STATIC_ONLY_PENDING_USER_PDS',
        changed=changed, before_sha256={n:before[n] for n in TARGETS},
        after_sha256={n:after[n] for n in TARGETS}, unchanged_inputs=len(before)-len(changed),
        checks=checks, structural_review='CPU functional body, bridge including041 observer, legacy13 and041 counter sequential blocks text preserved.',
        dynamic_simulation='NOT_RUN', PDS='NOT_RUN', board='NOT_RUN',
        limits='Null-target elaboration with vendor internals blackboxed; not functional or timing acceptance.'))
    print('042 STATIC ONLY: input identity and', len(checks), 'elaborations passed')
if __name__ == '__main__':
    {'snapshot':snapshot, 'review':review}[sys.argv[1]]()
