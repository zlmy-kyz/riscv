"""Offline fixed120 audit; short correct runs are comparisons, never formal PASS."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'tools/uart_loader/candidates/perf_2b/run_measurement.py'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists(), 'Use a fresh output directory'
    spec = importlib.util.spec_from_file_location('formal_measurement', TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    results = {}
    inputs = {TOOL: sha(TOOL)}
    for name in tool.FORMAL_APPLICATIONS:
        path = a.directory / (name + '.json')
        inputs[path] = sha(path)
        result = tool.verify(path)
        app = result['application']
        assert app['iterations'] == 120
        formal = app['seconds'] >= 10
        assert app['status'] == ('COREMARK_FORMAL_BOARD_PASS' if formal else
                                 'COREMARK_FIXED_BIN_MEASUREMENT_PASS')
        assert app['formal_benchmark'] == formal and app['duration_requirement_met'] == formal
        assert result['run_count'] == 1 and result['responses'] == 129
        counts = app['counters']
        result['cycle_shares_percent'] = {
            k: counts[k] * 100 / counts['cycles'] for k in tool.NAMES[2:9]}
        results[name] = result
        manifest = tool.manifest_for(name)
        info = tool.require_manifest(manifest)
        for entry in (manifest, ROOT / info['bin_path'], ROOT / info['elf_path']):
            inputs[entry] = sha(entry)
    a.output.mkdir(parents=True)
    frozen = a.output / 'frozen_logs'
    frozen.mkdir()
    for name in results:
        shutil.copyfile(a.directory / (name + '.json'), frozen / (name + '.json'))
    for path, digest in inputs.items():
        assert sha(path) == digest, 'Input changed during audit: ' + str(path)
    all_formal = all(r['application']['formal_benchmark'] for r in results.values())
    receipt = dict(status=('COREMARK_FORMAL120_TWO_MODE_BOARD_LOGS_VERIFIED' if all_formal else
                           'COREMARK_FIXED120_TWO_MODE_COMPARISON_LOGS_VERIFIED'),
                   both_modes_formal=all_formal,
                   applications=results, total_responses=258, unique_runs=2,
                   input_sha256={str(p.resolve()): d for p, d in inputs.items()},
                   FPGA_programming_independently_observed=False,
                   pds_started=False, serial_opened=False,
                   deployment_gate_required=False)
    (a.output / 'review_result.json').write_text(
        json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    with (a.output / 'metrics.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['application', 'seconds', 'CPI', *tool.NAMES])
        for name, result in results.items():
            app = result['application']
            w.writerow([name, app['seconds'], app['cpi'],
                        *[app['counters'][k] for k in tool.NAMES]])
    print(receipt['status'])
    for name, result in results.items():
        app = result['application']
        print(name, app['seconds'], app['cpi'], result['cycle_shares_percent'])


if __name__ == '__main__':
    main()
