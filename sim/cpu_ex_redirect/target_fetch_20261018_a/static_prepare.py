"""039: snapshot and statically elaborate EX same-edge target submission only."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
CPU = 'myriscv/mycpu_sync.v'
BASE = 'sim/cpu_ex_redirect/board/review_serial_drain_fix_20261018_01/board_review.json'
def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()
def save(name, data):
    (HERE / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
def git(name, *args):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True)
    (HERE / name).write_bytes(r.stdout + r.stderr)

def snapshot():
    assert not (HERE / 'before_manifest.json').exists(), 'Preserve snapshot'
    baseline = json.loads((ROOT / BASE).read_text(encoding='utf-8'))
    assert baseline['status'] == 'EX_SERIAL_DRAIN_FIX_P300_V300_APPLICATION_RAW_PASS_PERFORMANCE_REGRESSION'
    for rel, digest in baseline['evidence_sha256'].items():
        assert sha(ROOT / rel) == digest, rel
    prior = json.loads((ROOT / 'sim/cpu_data_decode/preparation_20261018_a/after_manifest.json').read_text(encoding='utf-8'))
    paths = set(prior) | {p.relative_to(ROOT).as_posix() for p in (ROOT / 'myriscv').glob('*.v')}
    paths |= {p.relative_to(ROOT).as_posix() for p in (ROOT / 'myriscv').glob('*.vh')}
    paths.add(BASE)
    before = {rel: sha(ROOT / rel) for rel in sorted(paths)}
    assert before[CPU] == '9eb803138292427293db785e27eeff9f15295622a95514e695f017cca505093f'
    dst = HERE / 'before' / CPU
    dst.parent.mkdir(parents=True, exist_ok=False)
    dst.write_bytes((ROOT / CPU).read_bytes())
    save('before_manifest.json', before)
    git('git_before.txt', 'status', '--porcelain=v1', '-uno')
    git('cpu_before_head.diff', 'diff', 'HEAD', '--', CPU)
    print('SNAPSHOT_ONLY; baseline raw evidence hashes verified; CPU saved')

def review():
    assert not (HERE / 'review.json').exists(), 'Preserve review'
    before = json.loads((HERE / 'before_manifest.json').read_text(encoding='utf-8'))
    after = {rel: sha(ROOT / rel) for rel in before}
    changed = [rel for rel in before if before[rel] != after[rel]]
    assert changed == [CPU], changed
    old = (HERE / 'before' / CPU).read_text(encoding='utf-8')
    new = (ROOT / CPU).read_text(encoding='utf-8')
    assert old[old.index('    // 单 outstanding 请求跟踪。'):] == new[new.index('    // 单 outstanding 请求跟踪。'):], 'Unexpected downstream pipeline change'
    assert 'BRANCH_FETCH_TURNOVER_ENABLE != 0' in new
    assert 'branch_fetch_redirect ? id_ex_br_target : pc' in new
    assert '(!inst_pending || inst_rsp_valid)' in new
    (HERE / 'cpu.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
        'before/' + CPU, 'after/' + CPU)), encoding='utf-8')
    dst = HERE / 'after' / CPU
    dst.parent.mkdir(parents=True, exist_ok=False)
    dst.write_bytes((ROOT / CPU).read_bytes())
    save('after_manifest.json', after)
    src = sorted(p.relative_to(ROOT).as_posix() for p in (ROOT / 'myriscv').glob('*.v'))
    src += ['ipcore/icache/icache.v', 'ipcore/dcache/dcache.v']
    configs = [('board_default', 'board_top', {})]
    for fast in (0, 1):
        for drain in (0, 1):
            configs.append((f'cpu_fast{fast}_drain{drain}', 'mycpu_sync',
                            {'BRANCH_FETCH_TURNOVER_ENABLE': fast, 'EXTERNAL_MEM_DRAIN_ENABLE': drain}))
    checks = []
    for name, module, params in configs:
        argv = ['D:/iverilog/bin/iverilog.exe', '-g2005', '-tnull', '-i', '-I', 'myriscv', '-s', module]
        for key, value in params.items():
            argv += ['-P', f'{module}.{key}={value}']
        argv += src
        r = subprocess.run(argv, cwd=ROOT, capture_output=True, timeout=60)
        output = (r.stdout + r.stderr).decode('utf-8', errors='replace')
        (HERE / (name + '.log')).write_text(output, encoding='utf-8')
        checks.append(dict(name=name, argv=argv, exit_code=r.returncode, output=output))
        if r.returncode:
            save('static_failure.json', checks)
            raise RuntimeError(name)
    subprocess.run(['git', 'diff', '--check', '--', CPU], cwd=ROOT, check=True)
    save('review.json', dict(status='TASK039_EX_TARGET_FETCH_STATIC_ONLY_PENDING_USER_PDS',
        changed=changed, before_cpu_sha256=before[CPU], after_cpu_sha256=after[CPU],
        unchanged_inputs=len(after)-1, checks=checks,
        scope='Only IF target submission, PC progression and related declarations/comments changed. Pending/drop, flush, serial FSM, retirement and all downstream RTL byte-equivalent as text.',
        dynamic_simulation='NOT_RUN', PDS='NOT_RUN', board='NOT_RUN',
        limits='Null-target elaboration with vendor internals blackboxed by -i; not functional equivalence, timing or performance acceptance.'))
    print(json.dumps(dict(status='TASK039_STATIC_ONLY_PENDING_USER_PDS', cpu=after[CPU], checks=len(checks))))

if __name__ == '__main__':
    {'snapshot': snapshot, 'review': review}[sys.argv[1]]()
