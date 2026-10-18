"""Offline review of fix01b, preserving all sealed and run inputs."""
from pathlib import Path
from collections import Counter
import hashlib
import json
import re

HERE = Path(__file__).resolve().parent
TASK = HERE.parent
ROOT = TASK.parents[2]
SEALED = TASK / 'sealed_fix01b'
RUN = TASK / 'build/fix01b'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert not (HERE / 'review.json').exists(), 'Preserve review'
manifest = json.loads((SEALED / 'manifest.json').read_text())['files_sha256']
assert len(manifest) == 17
assert all(sha(SEALED / rel) == digest for rel, digest in manifest.items())
result = json.loads((RUN / 'result.json').read_text())
assert manifest == result['manifest']
assert manifest['myriscv/mycpu_sync.v'] == '5c26df0229ab00365b2eca1412499f988981fdfe1d1b7292e43a8317f0d47745'
includes = []
for rel in manifest:
    if Path(rel).suffix in ('.v', '.vh', '.sv', '.svh'):
        for inc in re.findall(r'`include\s+"([^"]+)"', (SEALED / rel).read_text(encoding='utf-8')):
            matches = [p for p in ((SEALED / rel).parent / inc, SEALED / 'myriscv' / inc) if p.is_file()]
            assert matches and all(p.relative_to(SEALED).as_posix() in manifest for p in matches)
            includes.append(dict(source=rel, include=inc))

def parse_events(raw):
    rows = []
    for line in raw.splitlines():
        if not line.startswith('EV,'):
            continue
        fields, key = {}, None
        for part in line.split(',')[1:]:
            if '=' in part:
                key, value = part.split('=', 1)
                fields[key] = [value]
            elif key is not None:
                fields[key].append(part)
        if fields.get('ph') == ['0']:
            fields['cycle'] = int(fields['cyc'][0])
            rows.append(fields)
    return rows

observations = {}
for name, summary in result['runs'].items():
    raw = (RUN / name / 'run.log').read_text()
    assert all(line in raw for line in summary['lines'])
    assert 'RESULT: FAIL' not in raw and 'RESULT: INCOMPLETE' not in raw
    rows = parse_events(raw)
    by_cycle = {r['cycle']: r for r in rows}
    assert len(rows) == len(by_cycle)
    events = list(map(int, re.search(r'EVENT t0=(-?\d+) t1=(-?\d+) t2=(-?\d+) t3=(-?\d+) t4=(-?\d+)', raw).groups()))
    ia = list(map(int, re.search(r'IAUDIT acc=(\d+) rspgen=(\d+) consume=(\d+) deliver=(\d+) drop=(\d+) inflight=(\d+)', raw).groups()))
    da = list(map(int, re.search(r'DAUDIT acc=(\d+) rspgen=(\d+) consume=(\d+) stores=(\d+)', raw).groups()))
    assert ia[0] == ia[1] == ia[2] == ia[3]+ia[4] and ia[5] == 0
    assert da[0] == da[1] == da[2] and da[3] == 1
    assert 'X31CHECK wrong_path_reg=00000000' in raw
    listing = {}
    for line in (RUN / name / 'program.lst').read_text().splitlines():
        m = re.match(r'\s*([0-9a-fA-F]+):\s+([0-9a-fA-F]{8})', line)
        if m:
            listing[int(m[1], 16)] = int(m[2], 16)
    # Check the logged PC+instruction prefix independently for every program,
    # including nottaken, whose runner skips its reference entirely.
    golden, pc = [], 0
    for _ in range(30):
        inst = listing[pc]
        golden.append([pc, inst])
        if inst & 0x7f == 0x23:
            break
        if inst & 0x7f == 0x63:
            a, b = (inst >> 15) & 31, (inst >> 20) & 31
            imm = ((inst >> 31) << 12) | (((inst >> 7) & 1) << 11) | (((inst >> 25) & 63) << 5) | (((inst >> 8) & 15) << 1)
            if imm & 4096:
                imm -= 8192
            pc += imm if a == b == 0 else 4
        else:
            pc += 4
    retired = [[int(m[1], 16), int(m[2], 16)] for m in re.finditer(r'^RET,\d+,([0-9a-f]+),([0-9a-f]+)$', raw, re.M)]
    assert retired[:len(golden)] == golden
    obs = dict(reported_events=events, aggregate_i_audit=ia, aggregate_d_audit=da,
               offline_pc_instruction_prefix_match=True, golden_prefix=golden,
               full_architectural_value_next_pc_reference='NOT_AVAILABLE')
    if events[0] >= 0:
        t0, t1, t2, _, t4 = events
        target = int(by_cycle[t0]['bj'][0], 16)
        load = next(r for r in rows if r['cycle'] > t2 and r['rdir'] == ['0'] and r['front'] == ['0'] and
            ((r['buf'][0] == '1' and int(r['buf'][1], 16) == target) or
             (r['buf'][0] == '0' and r['pend'][0] == '1' and r['pend'][2] == '0' and
              r['irsp'][0] == '1' and int(r['pend'][1], 16) == target)))
        t3 = load['cycle']
        assert by_cycle[t4]['idfire'] == ['1'] and int(by_cycle[t4]['ifid'][1], 16) == target
        assert int(by_cycle[t1]['idex'][1], 16) == int(by_cycle[t0]['ifid'][1], 16)
        obs.update(phase0_inferred_events=[t0, t1, t2, t3, t4],
                   phase0_inferred_intervals=[t1-t0, t2-t1, t3-t2, t4-t3],
                   observed_phase0_load_inputs=load,
                   phase1_label_offset_from_load=events[3]-t3)
        roi_end = next(r['cycle'] for r in rows if r['cycle'] >= t0 and r['ret'][0] == '1' and int(r['ret'][1], 16) == golden[-1][0])
        roi = [r for r in rows if t0 <= r['cycle'] <= roi_end]
        counts = Counter(int(r['cls'][0]) for r in roi)
        obs['offline_roi'] = dict(start=t0, end_inclusive=roi_end, cycles=len(roi), classifications=dict(counts),
            OTHER_with_retire=sum(r['cls']==['8'] and r['ret'][0]=='1' for r in roi),
            OTHER_with_idfire=sum(r['cls']==['8'] and r['idfire']==['1'] for r in roi))
    if name == 'slowwrong':
        accepted = next(r for r in rows if r['ireq'][0]=='11' and int(r['ireq'][1], 16)==8)
        response = next(r for r in rows if r['cycle']>accepted['cycle'] and r['irsp'][0]=='1'
                        and r['pend'][0]=='1' and int(r['pend'][1], 16)==8)
        assert response['cycle']-accepted['cycle']==8
        obs['slow_latency_phase0'] = dict(accept=accepted['cycle'], consume=response['cycle'], latency=8)
    observations[name] = obs

review = dict(status='TASK040_FIX01B_PARTIAL_EVIDENCE_IMPROVED_TIMESTAMPS_STILL_REQUIRE_REPAIR',
    sealed_manifest_files_verified=17, recursive_include_closure=includes, observations=observations,
    verified_improvements=['Sealed source identities and header closure verified; compile log refers to sealed source.',
                           'Slow address actual response interval is eight edges in phase0 and model clocks separately.',
                           'Six runs have matching aggregate I/D totals, no remaining aggregate I inflight, and x31 zero.',
                           'PC+instruction correct-path prefix verified offline for all six, including nottaken.',
                           'ROI is bounded by branch issue and completion store retirement for taken cases.'],
    remaining_defects=['cycle is incremented by a separate model posedge block, while observer reads it at entry and after #1. The SAME physical edge acquires two labels.',
        'phase1 reads post-NBA pending/buffer and calls them old owners; capture old fields before the edge instead.',
        'Reported fast t3=11 coincides with following phase0=11; actual loading inferred at phase0=10, and IF buffer is zero. Buffer-detour hypothesis is refuted for this fast case.',
        'Only PC prefix is compared by runner. PC/inst prefix now reviewed, but rd/we/value/next_pc absent from RET; nottaken skips runner oracle and ROI, ref_match=true is not evidence for it.',
        'IAUDIT/DAUDIT improved aggregate totals do not provide complete per-request ledger or recorded D latency/byte side effects; trace still truncates at80 edges.',
        'Actual command/cwd/tool version/return-code transcripts not delivered; runner tests first verdict only, not all FAIL/INCOMPLETE lines and independent audit predicates.',
        'Wrong-path CSR may not retire per reviewed prefix, but mscratch side-effect value is not observed/checked.'],
    next_action='Do not rerun a wider matrix. Repair monitor timestamps/old-owner snapshots and complete existing reference/ledger for same six cases in a new sealed run.',
    evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in [TASK/'report_fix01.md', SEALED/'manifest.json', RUN/'result.json', RUN/'compile.log', RUN/'tb.vvp', Path(__file__), *RUN.glob('*/run.log'), *RUN.glob('*/program.lst')]},
    RTL_modified=False, HDL_started=False, PDS_started=False, serial_opened=False)
(HERE/'review.json').write_text(json.dumps(review, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
print(json.dumps(dict(status=review['status'], sealed_files=17,
    modes={k:{q:v[q] for q in ('phase0_inferred_events','phase0_inferred_intervals','offline_roi') if q in v} for k,v in observations.items()}), ensure_ascii=False, indent=2))
