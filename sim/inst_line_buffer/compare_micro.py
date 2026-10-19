"""Compare fixed micro workloads without changing accepted-CYCLE windows."""
from collections import Counter
from pathlib import Path
import csv
import hashlib
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'sim/cpu_performance'))
from analyze import check_micro_trace, check_partition, metrics


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(newline='') as stream:
        return list(csv.DictReader(stream))


def verify_trace_pair(brows, orows, cases, btimers, otimers, binary):
    """Only marker LW values may differ; all other architectural writes agree.

    Boundary attribution changes are accepted only for the retirement immediately
    before an explicit start/stop marker. This describes the current pipeline;
    larger or unrelated changes require a new review, not a numeric tolerance.
    """
    assert len(brows) == len(orows) > 0, 'retirement length changed'
    markers = {}
    for c in cases:
        for kind in ('start', 'stop'):
            pc = c[kind]
            assert pc not in markers, 'duplicate marker PC'
            word = int.from_bytes(binary[pc-0x40000000:pc-0x40000000+4], 'little')
            assert word & 0x7f == 3 and (word >> 12) & 7 == 2
            assert (word >> 15) & 31 == 27 and word >> 20 == 0, 'marker must read CYCLE through s11'
            markers[pc] = (c['id'], kind, (word >> 7) & 31)
    indices = {}
    boundary = []
    timer_values = []
    for rows in (brows, orows):
        assert all(int(a['cycle']) < int(z['cycle']) for a, z in zip(rows, rows[1:])), 'unordered retirement'
    for i, (b, o) in enumerate(zip(brows, orows)):
        assert all(b[k] == o[k] for k in ('pc', 'write', 'rd')), f'retirement stream changed at {i}'
        pc = int(b['pc'], 16)
        if pc in markers:
            assert pc not in indices, 'marker retired twice'
            indices[pc] = i
            w, kind, rd = markers[pc]
            assert b['write'] == '1' and int(b['rd']) == rd
            assert int(b['value'], 16) == btimers[w][kind]
            assert int(o['value'], 16) == otimers[w][kind]
            timer_values.append(dict(pc=b['pc'], window=w, kind=kind,
                                     baseline=b['value'], optimized=o['value']))
        else:
            assert b['value'] == o['value'], f'non-timer value changed at {pc:08x}'
        if b['window'] != o['window']:
            assert i+1 < len(brows), 'unexplained final window tag'
            next_pc = int(brows[i+1]['pc'], 16)
            assert next_pc in markers, f'non-boundary window tag change at {pc:08x}'
            w, kind, _ = markers[next_pc]
            assert {int(b['window']), int(o['window'])} == {0, w}, 'wrong window attribution'
            boundary.append(dict(index=i, pc=b['pc'], marker_pc=f'{next_pc:08x}',
                kind=kind, baseline_window=int(b['window']), optimized_window=int(o['window'])))
    assert set(indices) == set(markers), 'missing marker retirement'
    workloads = []
    for c in cases:
        s, t = indices[c['start']], indices[c['stop']]
        assert s < t
        assert not any(int(r['pc'], 16) in markers for r in brows[s+1:t]), 'nested workload markers'
        # Labels and cycle numbers are intentionally excluded from the workload.
        stream = [[r[k] for k in ('pc', 'write', 'rd', 'value')] for r in brows[s+1:t]]
        assert stream == [[r[k] for k in ('pc', 'write', 'rd', 'value')] for r in orows[s+1:t]]
        workloads.append(dict(id=c['id'], name=c['name'], retired_body_instructions=t-s-1,
                              body_sha256=hashlib.sha256(json.dumps(stream).encode()).hexdigest()))
    return dict(total_retirement=len(brows), workloads=workloads,
                boundary_attribution_changes=boundary, timer_reads=timer_values)


def read_run(folder, mode, original_manifest_sha256, expected_bridge_sha256):
    receipt = read(folder / 'line_buffer_receipt.json')
    assert receipt['status'] == 'INST_LINE_BUFFER_VERIFICATION_PASS'
    assert receipt['suite'] == 'micro' and receipt['engine'] == 'physical'
    assert receipt['mode'] == mode and receipt['inputs_unchanged']
    assert receipt['input_manifest_sha256'] == original_manifest_sha256
    assert read(folder / 'protected_before.json') == read(folder / 'protected_after.json')
    snap = folder / 'compile/source_snapshot'
    hashes = read(snap / 'sha256.json')
    assert all(sha(snap / n) == h for n, h in hashes.items()), 'source snapshot changed'
    bridge_keys = [n for n in hashes if n.endswith('myriscv/dual_sram_to_pango_ddr_bridge.v')]
    assert len(bridge_keys) == 1 and hashes[bridge_keys[0]] == expected_bridge_sha256
    for name in ('compile.log', 'vendor_ip_compile.log', 'physical_model_compile.log'):
        s = (folder / 'compile' / name).read_text(errors='replace')
        assert 'Errors: 0' in s and not re.search(r'\*\* (?:Error|Fatal):', s)
    p = folder / 'micro'
    info, summary = read(p / 'input_manifest.json'), read(p / 'summary.json')
    assert summary['status'] == 'PASS' and summary['engine'] == 'physical'
    assert info['kind'] == 'micro' and summary['clock_hz'] == info['clock_hz'] == 93750000
    s = (p / 'simulation.log').read_text(errors='replace')
    assert 'RESULT: PASS cpu_performance windows=9' in s and 'Errors: 0' in s
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal):', s)
    assert 'CHECK: Pango IP/PHY/physical DDR wrote and read back' in s
    assert s.count('CHECK: 13 hardware counters match independent 2A observer') == 1
    binary = Path(info['bin_path']).read_bytes()
    assert hashlib.sha256(binary).hexdigest() == info['sha256']['program.bin']
    measured = metrics(p)
    timers = {}
    for r in csv_rows(p / 'timer.csv'):
        w = int(r['window'])
        assert w not in timers, 'duplicate timer window'
        timers[w] = {k: int(r[k]) for k in ('start', 'stop', 'ticks')}
        assert (timers[w]['stop']-timers[w]['start']) & 0xffffffff == timers[w]['ticks']
    trace = csv_rows(p / 'retire_trace.csv')
    hist = Counter()
    for r in csv_rows(p / 'retire_pc.csv'):
        key = (int(r['window']), int(r['pc'], 16))
        assert key not in hist, 'duplicate PC histogram row'
        hist[key] = int(r['count'])
    assert hist == Counter((int(r['window']), int(r['pc'], 16)) for r in trace if int(r['window']))
    assert set(measured) == set(timers) == {c['id'] for c in info['cases']}
    assert len(info['cases']) == len(summary['windows']) == 9
    for c, w in zip(info['cases'], summary['windows']):
        assert all(w[k] == v for k, v in c.items()), 'case metadata changed'
        check_partition(measured[w['id']])
        assert all(w[k] == v for k, v in measured[w['id']].items()), 'summary differs from raw metrics'
        assert w['cycles'] == timers[w['id']]['ticks']
        assert w['instret'] == sum(v for (wid, pc), v in hist.items() if wid == w['id'])
        assert w['cpi'] == w['cycles']/w['instret']
    oracle = check_micro_trace(p, binary)
    assert json.loads(json.dumps(oracle)) == summary['retirement_oracle']
    return dict(info=info, summary=summary, trace=trace, timers=timers, binary=binary, hashes=hashes)


def compare(bfolder, ofolder, original_manifest_sha256, baseline_sha, optimized_sha):
    b = read_run(bfolder, 'baseline', original_manifest_sha256, baseline_sha)
    o = read_run(ofolder, 'optimized', original_manifest_sha256, optimized_sha)
    assert b['info'] == o['info'] and b['binary'] == o['binary'], 'workload input changed'
    # Check every non-bridge common source. Generated TB/wrapper names contain tags;
    # their contents must still be identical between the two compilations.
    common = set(b['hashes']) & set(o['hashes'])
    for n in common:
        assert b['hashes'][n] == o['hashes'][n], 'common source changed: '+n
    for name in ('tb_performance_2b.sv', 'perf_ddr3_setup.sv', 'ddr3_mem.v'):
        assert sha(bfolder / 'compile' / name) == sha(ofolder / 'compile' / name)
    verified = verify_trace_pair(b['trace'], o['trace'], b['info']['cases'], b['timers'], o['timers'], b['binary'])
    assert b['summary']['retirement_oracle']['final_a0'] == o['summary']['retirement_oracle']['final_a0']
    rows = []
    for bw, ow, workload in zip(b['summary']['windows'], o['summary']['windows'], verified['workloads']):
        rows.append(dict(window=bw['name'], baseline=bw, optimized=ow, workload=workload,
            cycle_ratio=bw['cycles']/ow['cycles'], ar_reduction=bw['ddr_ar_commands']-ow['ddr_ar_commands'],
            window_instret_delta=ow['instret']-bw['instret'],
            cpi_scope='actual retirements during accepted CYCLE [S,T), including boundary attribution',
            workload_scope='retirement sequence strictly between the start/stop LW markers',
            physical_performance_evidence=True, board_result='NOT_TESTED'))
    assert rows[0]['window'] == 'sequential_alu' and rows[0]['ar_reduction'] > 0
    return dict(status='INST_LINE_BUFFER_PHYSICAL_COMPARE_PASS', comparisons=rows, trace_verification=verified,
                time_window_unchanged=True, previous_comparison_not_overwritten=True, board_result='NOT_TESTED')
