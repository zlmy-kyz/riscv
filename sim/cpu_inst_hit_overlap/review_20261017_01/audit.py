"""Read-only Task033 evidence audit; writes only this new review directory."""
import hashlib
import importlib.util
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[2]
BASE = ROOT / 'sim/cpu_inst_hit_overlap'
RUN = BASE / 'build/ds_inst_hit_overlap_20261017_a'
SEALED = BASE / 'sealed_ds_inst_hit_overlap_20261017_a'


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    return json.loads(Path(p).read_text(encoding='utf-8'))


manifest = read(RUN / 'manifest.json')
meta = read(RUN / 'run_meta.json')
frozen = RUN / 'src/sim/cpu_inst_hit_overlap'
spec = importlib.util.spec_from_file_location('task033_frozen_checker', frozen / 'check_evidence.py')
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
identity = []
for row in manifest['files']:
    paths = [Path(row['source']), RUN / row['sealed'], SEALED / row['sealed']]
    identity.append(dict(source=row['source'], expected=row['sha256'],
                         copies=[dict(path=str(p), sha256=sha(p), match=sha(p) == row['sha256'])
                                 for p in paths]))
protected = [dict(source=row['source'], match=sha(ROOT / row['source']) == row['sha256'])
             for row in manifest['protected']]
baseline = read(BASE / 'preparation_20261017_a/after_manifest.json')
baseline_drift = {name: dict(expected=digest, actual=sha(ROOT / name))
                  for name, digest in baseline.items() if sha(ROOT / name) != digest}
replayed = {mode: c.run_bridge(RUN, mode) for mode in ('on', 'off')}
replayed['soc'] = c.run_soc(RUN)

inputs = read(frozen / 'inputs.json')
plan = c.load_plan(frozen / 'plan_bridge.txt')
summaries = {}
for mode in ('on', 'off'):
    edges = c.load_edges(RUN / ('bridge_%s.edges.log' % mode))
    summaries[mode] = c.replay(plan, edges, c.Mem(inputs['memory']['beats']),
                               pokes=c.load_pokes(RUN / ('bridge_%s.tok.log' % mode)))

perf = {}
for mode in ('on', 'off'):
    p = replayed[mode]['perf']
    perf[mode] = dict(d_accept=p['d_accept'], d_ar=p['d_ar_edge'], d_response=p['d_resp'],
                     last_i_response=p['last_resp'],
                     all_done=max(p['d_resp'], p['last_resp']),
                     all_done_minus_d_ar=max(p['d_resp'], p['last_resp']) - p['d_ar_edge'],
                     all_done_minus_d_accept=max(p['d_resp'], p['last_resp']) - p['d_accept'])
perf['saved_cycles'] = perf['off']['all_done_minus_d_ar'] - perf['on']['all_done_minus_d_ar']

on = summaries['on']
selected = {}
for name in ('s9a_i_hit_pending_consume', 's9b_d_miss_window', 's9b_i_miss_parked',
             's9c_d_miss_window', 's9c_i_miss_parked', 's10_i_hit_no_camera_fill'):
    tok = next(t for t in plan if t['scen'] == name)
    a = on['accept'][tok['idx']]
    selected[name] = dict(addr=hex(tok['addr']), accept=a, response=on['resp'].get(tok['idx']),
                          ar=[(n, hex(line), scen) for n, line, scen in on['ar'] if scen == name],
                          cancellations=[x for x in on['cancels'] if x[1] == name],
                          nearby_edges=[e for e in on['edges'] if a-1 <= e['n'] <= a+3])

soc_edges = c.load_edges(RUN / 'soc.edges.log')
fe, retires = c.load_soc_trace(RUN / 'soc.edges.log')
iq, dq, overlaps = [], [], []
for e in soc_edges:
    if not e['rst'] or not e['init']:
        iq, dq = [], []
        continue
    if e['ip']:
        req = iq.pop(0)
        if dq and not dq[0]['write']:
            overlaps.append(dict(i_accept=req, i_response=e['n'], d_accept=dq[0],
                                 front_window=[fe[n] for n in sorted(fe)
                                               if e['n']-1 <= n <= e['n']+18],
                                 retires=[r for r in retires if int(r['pc'],16) == req['addr']+0x40000000]))
    if e['dp']:
        dq.pop(0)
    if e['iv'] and e['ir']:
        iq.append(dict(edge=e['n'], addr=e['ia']))
    if e['dv'] and e['dr']:
        dq.append(dict(edge=e['n'], addr=e['da'], write=e['dw']))

unknown = {}
for p in RUN.glob('*.edges.log'):
    unknown[p.name] = []
    for line in p.read_text().splitlines():
        if not line.startswith('E ') or 'ph=PRE' not in line:
            continue
        row = dict(x.split('=',1) for x in line.split()[1:])
        fields = {k:v for k,v in row.items() if k in c.NUMFIELDS and any(ch in v.lower() for ch in 'xz')}
        if fields:
            unknown[p.name].append(dict(n=row['n'], reset=row['rst'], fields=fields))

abort = BASE / 'aborted_run_20261017_a'
old = read(abort / 'manifest.json')
oldfiles = {x['source']:x['sha256'] for x in old['files']}
changed_since_aborted = [x['source'] for x in manifest['files'] if oldfiles.get(x['source']) != x['sha256']]

receipt = dict(status='TASK033_RAW_REPLAY_PASS_ACCEPTANCE_BLOCKED_COVERAGE_AND_EXECUTION_DEVIATIONS',
    manifest_sha256=sha(RUN/'manifest.json'), sealed_manifest_equal=sha(RUN/'manifest.json') == sha(SEALED/'manifest.json'),
    all_input_copies_match=all(x['match'] for r in identity for x in r['copies']),
    identity=identity, protected=protected, baseline_drift=baseline_drift,
    jobs=[{k:j[k] for k in ('name','exit','timeout','elapsed_s','verdict')} for j in meta['jobs']],
    replay=replayed, corrected_perf=perf, selected_bridge=selected, soc_overlap=overlaps,
    unknown_pre_fields=unknown, changed_since_aborted=changed_since_aborted,
    aborted_status=read(abort/'run_meta.json')['status'],
    git_recorded_before_after_equal=all(meta['git']['before'][k]['sha256']==meta['git']['after'][k]['sha256'] for k in ('head','status','diff')),
    findings=[
      'Performance all-done boundary yields 19 vs 25 edges from D AR, saving 6, not 19.',
      's9a reset hit was accepted outside a D miss, so it did not exercise the new independent hit slot.',
      's9c cancels the D transaction too; no promoted I AR occurred before reset.',
      's10_i_hit_no_camera_fill actually misses (it issues I AR), so the claimed simultaneous cached-hit scenario was not exercised.',
      'A failed vlib attempt was moved aside, runner changed and the same formal tag reused without required stop-and-return.',
      'Report and runner omit a cross-version assertion on all-done performance; the raw trace permits offline correction.',
    ],
    evidence_sha256={str(p.relative_to(ROOT)):sha(p) for p in RUN.rglob('*')
                     if p.is_file() and p.relative_to(RUN).parts[0] not in ('work','socwork','src')})
(OUT/'review.json').write_text(json.dumps(receipt,indent=2)+'\n',encoding='utf-8')
print(json.dumps({k:receipt[k] for k in ('status','all_input_copies_match','baseline_drift','corrected_perf','findings')},indent=2))
print('soc_overlap', [(x['i_accept'],x['i_response'],x['d_accept']) for x in overlaps])
print('selected_bridge', {k:{f:v[f] for f in ('accept','response','ar','cancellations')} for k,v in selected.items()})
