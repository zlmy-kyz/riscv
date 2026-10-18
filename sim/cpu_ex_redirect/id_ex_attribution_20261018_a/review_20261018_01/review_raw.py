"""Offline review of task040 evidence, without repairing/rerunning the tests."""
from pathlib import Path
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
ROOT = TASK.parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE / 'review.json').exists(), 'Preserve review'
run = TASK / 'build/run2'
result = json.loads((run / 'result.json').read_text())
assert result['cpu_sha256'] == '5c26df0229ab00365b2eca1412499f988981fdfe1d1b7292e43a8317f0d47745'
registered = {name: sha(Path(name)) == digest for name, digest in result['inputs_sha256'].items()}
assert all(registered.values()), registered
requirements = json.loads((TASK / 'requirements_identity.json').read_text(encoding='utf-8'))
requirement_changes = [rel for rel, digest in requirements['input_requirement_sha256'].items()
                       if sha(ROOT / rel) != digest]
observations = {}
for name, summary in result['runs'].items():
    path = run / name / 'run.log'
    raw = path.read_text()
    for line in summary['lines']:
        assert line in raw
    rows = []
    for line in raw.splitlines():
        if not line.startswith('EV,'):
            continue
        fields, key = {}, None
        for part in line.split(',')[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                fields[key] = [value]
            else:
                fields[key].append(part)
        fields['cycle'] = int(fields['cyc'][0])
        rows.append(fields)
    table = {r['cycle']: r for r in rows}
    match = re.search(r'EVENT t0=(-?\d+) t1=(-?\d+) t2=(-?\d+) t3=(-?\d+) t4=(-?\d+)', raw)
    reported = dict(zip(('t0', 't1', 't2', 't3', 't4'), map(int, match.groups())))
    obs = dict(reported_events=reported, raw_trace_rows=len(rows))
    if reported['t0'] >= 0:
        t0, t1, t2, t4 = (reported[k] for k in ('t0', 't1', 't2', 't4'))
        start = table[t0]
        target = int(start['bj'][0], 16)
        assert table[t1]['rdir'] == ['1']
        assert int(table[t1]['idex'][1], 16) == int(start['ifid'][1], 16)
        assert table[t2]['ireq'][0] == '11' and int(table[t2]['ireq'][1], 16) == target
        # Infer the true IF/ID loading edge from OLD pending response/buffer.
        load = next(r for r in rows if r['cycle'] > t2 and
                    r['rdir'] == ['0'] and r['front'] == ['0'] and
                    ((r['buf'][0] == '1' and int(r['buf'][1], 16) == target) or
                     (r['buf'][0] == '0' and r['pend'][0] == '1' and
                      r['irsp'][0] == '1' and r['pend'][2] == '0' and
                      int(r['pend'][1], 16) == target)))
        t3 = load['cycle']
        assert table[t4]['id_fire'] == ['1'] and int(table[t4]['ifid'][1], 16) == target
        obs.update(raw_inferred_load_edge=t3, corrected_events=[t0, t1, t2, t3, t4],
                   corrected_intervals=[t1-t0, t2-t1, t3-t2, t4-t3],
                   load_edge_inference_limit='Derived from existing pre-edge trace and unchanged CPU equations, not an independent complete architectural acceptance.')
    if name == 'm1_slowwrong':
        accepted = next(r for r in rows if r['ireq'][0] == '11' and int(r['ireq'][1], 16) == 8)
        returned = next(r for r in rows if r['cycle'] > accepted['cycle'] and r['pend'][0] == '1'
                        and int(r['pend'][1], 16) == 8 and r['irsp'][0] == '1')
        obs['slow_address_accept_edge'] = accepted['cycle']
        obs['slow_address_response_consumption_edge'] = returned['cycle']
        obs['actual_slow_response_edges'] = returned['cycle'] - accepted['cycle']
        assert obs['actual_slow_response_edges'] == 9
    observations[name] = obs

compile_text = (run / 'compile.log').read_text()
evidence = [TASK / 'report.md', TASK / 'run.py', TASK / 'tb_id_ex_attribution.v',
            TASK / 'requirements_identity.json', run / 'result.json', run / 'compile.log',
            run / 'tb.vvp', Path(__file__)]
evidence += list(run.glob('*/run.log')) + list(run.glob('*/imem.hex')) + list(run.glob('*/program.lst'))
review = dict(status='TASK040_PARTIAL_MECHANISM_SUPPORTED_NOT_ACCEPTED_REPAIR_REQUIRED',
    registered_input_hashes_match_current=registered,
    requirement_input_changes=requirement_changes,
    observed_compile_warning_lines=[line for line in compile_text.splitlines() if 'warning:' in line],
    observations=observations,
    accepted_scope=['Current039 code and raw trace support normal ID-to-EX interval of one edge in this fragment.',
                    'Injected wrong-path response is accepted at edge10, consumed at edge19; redirect12 and target acceptance19 show seven-edge blocking in this specific model.',
                    'Existing fast trace implies target acceptance12, actual IFID loading13 and ID issue14; not a two-edge IFID loading lower bound.'],
    defects=['Reported t3 samples pre-edge IFID visibility, one edge after real loading. Reported t4-t3=0 conflates two different events.',
             'Slow delay8 produces nine-edge CPU-visible response. Older-MEM configured delay8 likewise is not a measured eight-edge response contract.',
             'Reset is released at posedge despite report claiming non-sampling-edge release; end-of-run counters also sampled at posedge.',
             'No sealed-copy-only compilation and no recursively closed include manifest; csr_defs.vh, runner, assembler and programs absent from final inputs_sha256.',
             'No independent retirement PC/inst/rd/value/next_pc oracle; wrong-path x31 write is not checked, completion flag alone is insufficient.',
             'I rsp counter increments on response generation, including fast acceptance edge, not CPU consumption; inflight=i_busy omits generated-but-not-consumed response.',
             'Only first60 cycles logged, but 400-cycle statistics mostly include terminal spin. Full ROI stage/activity cross-statistics and conservation assertions absent.',
             'Younger CSR/FENCE variant and D acceptance/response counters absent; MEM16 in slow case includes both load and completion-store waits.',
             'Compile log has two array sensitivity warnings; report says zero warnings. Report claims changed asm/TB requirements, but current requirement hashes are unchanged.',
             'Runner does not save all assembly/execution commands and return codes or reject failed verdicts before returning zero.',
             'Report suggests old-response-same-edge target submission as a new direction, but039 already implements it.'],
    next_action='Minimal corrective implementation/execution by DeepSeek in new sealed run; preserve run1/run2 and report unchanged. No RTL optimization based on rejected timing lower bound.',
    evidence_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in evidence},
    RTL_modified=False, HDL_started=False, PDS_started=False, serial_opened=False)
(HERE / 'review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
print(json.dumps(dict(status=review['status'], requirement_input_changes=requirement_changes,
                     compile_warnings=len(review['observed_compile_warning_lines']), observations=observations), ensure_ascii=False, indent=2))
