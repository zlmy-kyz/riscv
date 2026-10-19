"""Offline audit of task 005 evidence; never compiles or simulates HDL."""
from collections import Counter
from pathlib import Path
import argparse
import csv
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / 'sim/cpu_performance'))
from analyze import metrics, check_partition, check_micro_trace
sys.path.insert(0, str(ROOT / 'sim/cpu_performance_2b'))
from check_output import check, NAMES
from application import parse_output


def digest(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def read(p):
    return json.loads(p.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-tag', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    assert all(re.fullmatch('[a-z0-9_-]+', t) for t in (args.tag, args.run_tag))
    out = HERE / 'build' / args.tag
    assert not out.exists(), 'Use a fresh review tag'
    evidence = {}

    def retain(p):
        evidence[p.relative_to(ROOT).as_posix()] = digest(p)
        return p

    def load(p):
        return read(retain(p))

    def log(p, passed=True):
        s = retain(p).read_text(encoding='utf-8', errors='replace')
        if passed:
            assert 'RESULT: PASS' in s, p
            assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal):', s), p
        return s

    manifests = {}
    for name, expected in (
        ('input_manifest.json', '1173f29a185651c99bdbc3053946c2b109aea789b9e14851543994d2dc6027ea'),
        ('resume_input_manifest.json', '40f5bb2227483cc8fc5d8ea3e5156455c38f90ea7d0a9b316a95d270c1134002'),
    ):
        p = HERE / name
        assert digest(p) == expected
        d = load(p)
        bad = [n for n, h in d['sha256'].items() if digest(ROOT / n) != h]
        assert not bad, bad
        manifests[name] = dict(sha256=expected, entries=len(d['sha256']), mismatches=bad)

    line = lambda suffix: HERE / 'build' / (args.run_tag + '_' + suffix)
    cpu = lambda suffix: ROOT / 'sim/cpu_performance_2b/build' / (args.run_tag + '_' + suffix)
    fast = load(line('fast') / 'result.json')
    assert fast['status'] == 'INST_LINE_BUFFER_FAST_REGRESSION_PASS'
    assert fast['inputs_unchanged'] and len(fast['checks']) == 48
    assert Counter(fast['checks'].values()) == Counter(PASS=46, KNOWN_BASELINE_GAP_REPRODUCED=2)
    for case, status in fast['checks'].items():
        p = line('fast') / (case + '.log')
        if status == 'PASS':
            log(p)
        else:
            texts = [log(line('fast') / (n + '.log'), False)
                     for n in (case, 'baseline_' + case)]
            failures = [re.findall(r'RESULT: FAIL[^\r\n]*', s) for s in texts]
            assert all(len(x) == 1 for x in failures)
            assert re.sub(r' cycles=\d+$', '', failures[0][0]) == re.sub(r' cycles=\d+$', '', failures[1][0])

    functional = []
    physical = []
    for engine, suffixes in [('functional', ('crc_base', 'crc_opt')), ('physical', ('phy_base', 'phy_opt'))]:
        runs = []
        for mode, suffix in zip(('baseline', 'optimized'), suffixes):
            folder = line(suffix)
            receipt = load(folder / 'line_buffer_receipt.json')
            assert receipt['status'] == 'INST_LINE_BUFFER_VERIFICATION_PASS'
            assert receipt['engine'] == engine and receipt['mode'] == mode and receipt['inputs_unchanged']
            assert load(folder / 'protected_before.json') == load(folder / 'protected_after.json')
            snapdir = folder / 'compile/source_snapshot'
            snapshot = load(snapdir / 'sha256.json')
            for n, h in snapshot.items():
                assert digest(snapdir / n) == h, n
            for p in (folder / 'compile').glob('*.log'):
                s = retain(p).read_text(errors='replace')
                assert not re.search(r'\*\* (?:Error|Fatal):', s), p
                if p.name not in ('vlib.log',):
                    assert 'Errors: 0' in s, p
            bridge = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
            source = bridge if mode == 'optimized' else read(HERE / 'input_manifest.json')['baseline_bridge']
            expected = read(HERE / 'input_manifest.json')[mode + '_bridge_sha256']
            assert snapshot[source] == expected
            results = {}
            for app in (['micro'] if engine == 'physical' else ['performance_1', 'validation_1']):
                p = folder / app
                info, summary = load(p / 'input_manifest.json'), load(p / 'summary.json')
                raw_metrics = metrics(retain(p / 'metrics.csv').parent)
                timers = {int(r['window']): int(r['ticks']) for r in csv.DictReader(retain(p / 'timer.csv').open())}
                s = log(p / 'simulation.log')
                assert 'Errors: 0' in s
                assert s.count('CHECK: 13 hardware counters match independent 2A observer') == 1
                for w in summary['windows']:
                    check_partition(raw_metrics[w['id']])
                    assert all(w[k] == v for k, v in raw_metrics[w['id']].items())
                    assert w['cycles'] == timers[w['id']]
                if app == 'micro':
                    assert 'CHECK: Pango IP/PHY/physical DDR wrote and read back' in s
                    binary = retain(Path(info['bin_path'])).read_bytes()
                    assert hashlib.sha256(binary).hexdigest() == info['sha256']['program.bin']
                    oracle = check_micro_trace(retain(p / 'retire_trace.csv').parent, binary)
                    assert json.loads(json.dumps(oracle)) == summary['retirement_oracle']
                    retain(p / 'retire_pc.csv')
                else:
                    parsed = check(info['original'], retain(p / 'uart.txt').read_bytes())
                    assert all(parsed['counters'][k] == summary['windows'][0][k] for k in NAMES)
                results[app] = dict(info=info, summary=summary)
            runs.append(results)
        if engine == 'functional':
            for app in runs[0]:
                b, o = [r[app]['summary']['windows'][0] for r in runs]
                assert b['instret'] == o['instret']
                functional.append(dict(application=app, baseline=b, optimized=o,
                                       physical_performance_evidence=False))
        else:
            b, o = [r['micro'] for r in runs]
            assert b['info'] == o['info']
            traces = [list(csv.DictReader((line(s) / 'micro/retire_trace.csv').open())) for s in suffixes]
            assert len(traces[0]) == len(traces[1]) == 1199
            marker_pcs = {c[k] for c in b['info']['cases'] for k in ('start', 'stop')}
            timer_differences = []
            window_tag_differences = []
            for i, (a, z) in enumerate(zip(*traces)):
                assert all(a[k] == z[k] for k in ('pc', 'write', 'rd')), i
                if a['value'] != z['value']:
                    assert int(a['pc'], 16) in marker_pcs, i
                    timer_differences.append(dict(index=i, pc=a['pc'], baseline=a['value'], optimized=z['value']))
                if a['window'] != z['window']:
                    window_tag_differences.append(dict(index=i, pc=a['pc'], baseline=a['window'], optimized=z['window']))
            assert len(timer_differences) == 18
            for bw, ow in zip(b['summary']['windows'], o['summary']['windows']):
                assert bw['id'] == ow['id'] and bw['name'] == ow['name']
                physical.append(dict(window=bw['name'], baseline=bw, optimized=ow,
                    time_ratio=bw['cycles']/ow['cycles'], ar_reduction=bw['ddr_ar_commands']-ow['ddr_ar_commands'],
                    observer_instret_delta=ow['instret']-bw['instret'], physical_model_only=True,
                    original_compare_status='FAIL'))
            physical_trace = dict(retired=1199, pc_write_rd_sequence_identical=True,
                timer_differences=timer_differences, window_tag_differences=window_tag_differences,
                oracle_baseline=b['summary']['retirement_oracle'], oracle_optimized=o['summary']['retirement_oracle'])

    compare = load(line('phy_compare') / 'line_buffer_receipt.json')
    assert compare['status'] == 'FAIL' and compare['error'] == 'retirement/window change requires review'
    other = {}
    for suite in ('ddr', 'irq', 'mmio'):
        folder = cpu(suite)
        d = load(folder / 'result.json')
        assert d['status'] == 'PERF2B_REGRESSION_PASS'
        assert d['protected_before'] == d['protected_after']
        receipt = load(folder / 'main_rtl_receipt.json')
        assert receipt['status'] == 'MAIN_RTL_REGRESSION_PASS'
        paths = list(folder.glob('*/sim.log')) if suite == 'irq' else list(folder.glob('*/console.log'))
        assert len(paths) == {'ddr': 2, 'irq': 34, 'mmio': 3}[suite]
        for p in paths:
            log(p)
        other[suite] = dict(status='PASS', raw_logs_checked=len(paths), checks=d['checks'])

    loaders = []
    for suffix in ('load_hello', 'load_crc32', 'load_perf1', 'load_val1'):
        p = cpu(suffix) / 'application'
        d = load(p / 'results.json')
        assert d['status'] == 'FAIL' and d['inputs_unchanged'] and d['protected_unchanged']
        s = log(p / 'modelsim.log', False)
        fatals = re.findall(r'\*\* Fatal: (.*)', s)
        assert len(fatals) == 1 and fatals[0].endswith(': Pango transaction conservation')
        assert 'Errors: 1, Warnings: 0' in s
        expected = bytes(int(x, 16) for x in retain(p / 'responses.hex').read_text().split())
        requests = bytes(int(x, 16) for x in retain(p / 'requests.hex').read_text().split())
        assert retain(p / 'uart_rx.bin').read_bytes() == requests
        actual = retain(p / 'uart_tx.bin').read_bytes()
        assert actual[:len(expected)] == expected
        app_data = actual[len(expected):]
        parsed = check(d['application_info'], app_data) if d['application_info']['kind'] == 'coremark' else parse_output(d['application_info'], app_data)
        loaders.append(dict(application=d['application'], original_status='FAIL', fatal=fatals[0],
                            protocol_response_bytes=len(expected), uart_independent_parse=parsed,
                            remaining_checks_not_reached=['BSP trap/IRQ acceptance', 'final guards', 'APP timer summary']))

    report = dict(status='INST_LINE_BUFFER_RESULTS_REVIEWED_TEST_GATE_FAIL', run_tag=args.run_tag,
        offline_only=True, simulation_started=False, pds_started=False, board_result='NOT_TESTED',
        manifests=manifests, fast=dict(status='PASS', checks=fast['checks'], failure_comparisons=fast['failure_comparisons']),
        functional_coremark=functional, physical_windows=physical, physical_trace=physical_trace,
        original_physical_compare=compare, other_regressions=other, loaders=loaders,
        overall_verification='NOT_PASS', evidence_sha256=evidence)
    out.mkdir(parents=True)
    (out / 'review_result.json').write_text(json.dumps(report, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')
    print(json.dumps({k: report[k] for k in ('status', 'manifests', 'overall_verification')}, ensure_ascii=False))
    print('Physical trace:', len(timer_differences), 'timer differences;', len(window_tag_differences), 'window tag differences')
    print('Loader UART independently correct:', len(loaders), '; original FAIL retained')
    print('Saved:', out / 'review_result.json')


if __name__ == '__main__':
    main()
