"""Offline final review of Task033. Never launches HDL or opens a serial port."""
import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = ROOT / 'sim/cpu_inst_hit_overlap'
RUN = BASE / 'build/ds_inst_hit_overlap_completion_20261017_b'
OLD = BASE / 'build/ds_inst_hit_overlap_20261017_a'
SEALED = BASE / 'sealed_ds_inst_hit_overlap_completion_20261017_b'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def key(path):
    p = Path(path).resolve()
    try:
        return p.relative_to(ROOT).as_posix()
    except ValueError:
        return str(p)


def record(path):
    evidence[key(path)] = sha(path)


evidence = {}
m = read(RUN / 'manifest.json')
meta = read(RUN / 'run_meta.json')
assert sha(RUN / 'manifest.json') == sha(SEALED / 'manifest.json')
sources = {}
for r in m['files']:
    for p in (Path(r['source']), RUN / r['sealed'], SEALED / r['sealed']):
        assert sha(p) == r['sha256'], str(p)
        record(p)
    sources[key(r['source'])] = r['sha256']

# Do not rely on the executor's overly broad metadata_only exemption: check
# every protected design/include/IP file byte-for-byte. Only the previously
# documented PDS project-session drift is exempted, and never used as a gate.
drift = []
for r in m['protected']:
    p = ROOT / r['source']
    actual = sha(p)
    if actual != r['sha256']:
        drift.append(dict(path=key(p), expected=r['sha256'], actual=actual))
assert {r['path'] for r in drift} <= {'RISCV.pds'}, drift
prior = read(BASE / 'review_20261017_01/review.json')
for name, digest in prior['evidence_sha256'].items():
    assert sha(ROOT / name) == digest, name
for r in prior['identity']:
    for cp in r['copies']:
        assert sha(cp['path']) == r['expected'], cp['path']
for name, digest in read(BASE / 'preparation_20261017_a/after_manifest.json').items():
    if name != 'RISCV.pds':
        assert sha(ROOT / name) == digest, name

assert meta['status'] == 'TASK033_COMPLETION_PASS_PENDING_CODEX_REVIEW'
assert [j['name'] for j in meta['jobs']] == ['check_legacy','vlib_work','vlog_work','sim_completion','check_completion','selftest_completion']
for j in meta['jobs']:
    assert j['exit'] == 0 and not j['timeout'] and j['verdict'] == 'PASS', j
assert all(meta['git']['before'][k]['sha256'] == meta['git']['after'][k]['sha256']
           for k in ('head','status','diff'))
transcript = (RUN / 'logs/completion.transcript').read_text()
assert transcript.count('RESULT: PASS inst_hit_completion') == 1
assert 'Errors: 0, Warnings: 0' in transcript and '** Note: $finish' in transcript
assert transcript.count('IPSpecCheck: 04030130') == 2
assert not any(x in transcript for x in ('** Error','** Fatal','** Warning','RESULT: FAIL'))

frozen = RUN / 'src/sim/cpu_inst_hit_overlap'
spec = importlib.util.spec_from_file_location('frozen_completion_checker', frozen/'check_completion.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
completed = c.run_completion(RUN)
legacy = c.legacy_mode(OLD)
assert completed['accepts'] == 18 and completed['responses'] == 15
assert completed['cancels'] == [(20,'I','00000104'),(20,'D','00001000'),(80,'I','00000140')]
g = completed['gates']
assert g['independent_hit']['accept'] == 19 and g['independent_hit']['reset_edge'] == 20
assert g['promoted_miss']['d_resp'] == 75 and g['promoted_miss']['i_ar'] == 76 and g['promoted_miss']['reset_edge'] == 80
assert [(x['first_d']['r'],x['hits'][1]['accept'],x['hits'][1]['resp'])
        for x in g['uncached']] == [(130,130,131),(176,176,177)]
assert legacy['saved_cycles'] == 6

negative = subprocess.run([sys.executable,'-B',str(frozen/'selftest_completion.py'),str(RUN),str(OLD)],
                          capture_output=True,text=True,timeout=60)
(OUT/'selftest_replay.txt').write_text(negative.stdout+negative.stderr,encoding='utf-8')
assert negative.returncode == 0 and 'SELFTEST: PASS 10/10' in negative.stdout

# Scope of the uncached bridge test: I-side addresses in the Camera/PP regions
# are driven directly at the standalone bridge to stress split I/D cache fill.
# Such fetches are forbidden by the real SoC decoder; permission is covered by
# the prior real-CPU cause=1/tval tests, not by this standalone job.
for run in (RUN, OLD):
    for p in run.rglob('*'):
        if p.is_file() and p.relative_to(run).parts[0] not in ('work','socwork'):
            record(p)
for p in SEALED.rglob('*'):
    if p.is_file():
        record(p)
for p in (BASE/'review_20261017_01/review.json', OUT/'audit.py', OUT/'selftest_replay.txt'):
    record(p)

software = {}
for app, digest in [('performance_300','677ee766fd0fc34d1558d778a343743a1cd9287ecdbbc182cb4681af3374517d'),
                    ('validation_300','461c635c46c86c8e719ced403b045bca468ded7299870bf2f87f8547ce11719b')]:
    p = ROOT / 'tests/cpu_performance_2b/build/measure_zmmul300_20261013_a' / app / 'program.bin'
    assert sha(p) == digest
    software[key(p)] = digest

receipt = dict(status='TASK033_RAW_FUNCTIONAL_EVIDENCE_REVIEW_PASS',review_kind='TASK033_INITIAL_AND_COMPLETION_RAW_REVIEW',
    bridge_sha256=sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'),
    manifest_sha256=sha(RUN/'manifest.json'), initial_manifest_sha256=sha(OLD/'manifest.json'),
    copied_inputs=len(m['files']), protected_rows=len(m['protected']), independently_checked_protection_drift=drift,
    completed=completed, reused_legacy=legacy, synthetic_cases=10,
    evidence_sha256=evidence, design_and_test_sha256=sources, software_sha256=software,
    limitations=['Functional Pango user-port model, no DDR PHY or board run.',
                 'Standalone Camera/PP I addresses stress cache isolation; real SoC permission remains forbidden and was separately verified.',
                 'Original first-failure execution deviation remains recorded; original failed and successful evidence remains unchanged.',
                 'Executor metadata_only classification included design IP files; all were independently checked byte-for-byte here.',
                 'Controlled bridge workload saves 6 cycles; CoreMark benefit is unmeasured.'],
    board='NOT_RUN',pds_report_independently_reviewed=False,
    historical_board_baseline=dict(task='032',performance_cycles=210246597,validation_cycles=210056980,
                                   scope='Historical integrated configuration differs; do not attribute all delta solely to 033.'))
target=OUT/'codex_review.json'
assert not target.exists(), 'Preserve previous final review receipt'
target.write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status=receipt['status'],copied_inputs=receipt['copied_inputs'],protected_rows=receipt['protected_rows'],
                      protection_drift=drift,coverage=completed['gates'],saved_cycles=legacy['saved_cycles']),indent=2))
