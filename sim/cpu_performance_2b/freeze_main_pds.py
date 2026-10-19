"""Freeze an already-audited main bitstream; never run PDS or open serial."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--review-tag', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    assert all(re.fullmatch('[a-z0-9_-]+', value) for value in (args.review_tag, args.tag))
    review_path = ROOT / 'sim/cpu_performance_2b/build' / args.review_tag / 'review_result.json'
    review = read(review_path)
    assert review['status'] == 'PERF2B_MAIN_PDS_ARTIFACT_AUDIT_PASS'
    assert review['inputs_unchanged'] and review['implementation_export']['fresh']
    assert review['implementation_export']['all_8_memory_INIT_payloads_verified']
    assert review['implementation_export']['contains_perf_counter']
    for relative, digest in review['input_sha256'].items():
        assert sha(ROOT / relative) == digest, relative

    previous_path = ROOT / 'sim/cpu_performance_2b/build/deployment_gate.json'
    previous = read(previous_path)
    evidence = dict(previous['evidence_sha256'])
    for relative, digest in previous['input_sha256'].items():
        frozen = 'sim/cpu_performance_2b/build/frozen_inputs/' + relative
        assert sha(ROOT / frozen) == digest, frozen
        evidence[frozen] = digest
    for relative, digest in evidence.items():
        assert sha(ROOT / relative) == digest, relative
    evidence[review_path.relative_to(ROOT).as_posix()] = sha(review_path)
    baseline_path = ROOT / 'sim/cpu_performance_2b/build/main_integration_20261010_a.json'
    baseline = read(baseline_path)
    evidence[baseline_path.relative_to(ROOT).as_posix()] = sha(baseline_path)
    for field in ('suites', 'source_receipts'):
        for row in baseline[field].values():
            assert sha(ROOT / row['path']) == row['sha256'], row['path']
            evidence[row['path']] = row['sha256']
            folder = (ROOT / row['path']).parent
            for path in folder.rglob('*'):
                if path.is_file() and path.suffix in ('.json', '.log', '.csv', '.txt', '.tcl', '.sv', '.v', '.dat', '.bin') and 'work' not in path.parts:
                    evidence[path.relative_to(ROOT).as_posix()] = sha(path)

    inputs = set(review['input_sha256'])
    inputs.add(previous_path.relative_to(ROOT).as_posix())
    inputs.add(Path(__file__).resolve().relative_to(ROOT).as_posix())
    for folder in ('sim/cpu_performance_2b', 'tools/uart_loader/candidates/bsp_workflow',
                   'tools/uart_loader/candidates/perf_2b', 'tools/uart_loader/candidates/verify_run_hello',
                   'tools/uart_loader/candidates/load_stage10', 'tests/uart_loader/candidates/verify_run_hello'):
        inputs.update(path.relative_to(ROOT).as_posix() for path in (ROOT / folder).glob('*.py'))
    for folder in ('tests/bsp_workflow', 'tests/cpu_performance_2b'):
        inputs.update(path.relative_to(ROOT).as_posix() for path in (ROOT / folder).iterdir()
                      if path.is_file() and path.suffix in ('.c', '.h', '.S', '.ld', '.py', '.ps1'))
    for relative in ('generate_netlist/board_top_sta.sdf', 'generate_netlist/run.log',
                     'place_route/board_top_pnr.adf', 'place_route/board_top.prr',
                     'place_route/multiseed_result.csv'):
        inputs.add(relative)
    for stage in ('compile', 'synthesize', 'device_map', 'place_route', 'report_timing', 'generate_bitstream'):
        inputs.add(stage + '/run.log')
    inputs.update(path.relative_to(ROOT).as_posix() for path in
                  (ROOT / 'tests/uart_loader/candidates/verify_run_hello/build').glob('*') if path.is_file())

    app_spec = importlib.util.spec_from_file_location('freeze_app', ROOT / 'tools/uart_loader/candidates/bsp_workflow/application.py')
    app = importlib.util.module_from_spec(app_spec)
    app_spec.loader.exec_module(app)
    for relative in previous['applications'].values():
        assert sha(ROOT / relative) == previous['manifests'][relative], relative
        app.require_manifest(ROOT / relative)
        inputs.update(path.relative_to(ROOT).as_posix() for path in (ROOT / relative).parent.iterdir() if path.is_file())
    hashes = {relative: sha(ROOT / relative) for relative in sorted(inputs)}
    out = ROOT / 'sim/cpu_performance_2b/build' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    copies = []
    for relative, digest in hashes.items():
        target = out / 'frozen_inputs' / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
        assert sha(target) == digest and sha(ROOT / relative) == digest, relative
        copies.append(dict(source=relative, archive=target.relative_to(ROOT).as_posix(), sha256=digest))
    for relative, digest in evidence.items():
        assert sha(ROOT / relative) == digest, relative
    gate = dict(status='PERF2B_MAIN_PRE_BOARD_AUDIT_PASS', board_result='NOT_TESTED',
        bitstream=review['bitstream'], applications=previous['applications'], manifests=previous['manifests'],
        input_sha256=hashes, evidence_sha256=evidence, frozen_source_copies=copies,
        review=review_path.relative_to(ROOT).as_posix(), review_sha256=sha(review_path),
        timing=review['timing'], resources=review['resources'], initializations=review['initializations'],
        implementation_export=review['implementation_export'], functional_baseline=review['functional_baseline'],
        core_clock_mhz=93.75, best_seed=review['best_seed'], cpu_behavior_optimization=False,
        formal60_full_simulation=False, pds_started=False, codex_opened_serial=False,
        FPGA_programming_independently_observed=False, previous_gate_preserved=True)
    with (out / 'deployment_gate.json').open('x', encoding='utf-8') as stream:
        json.dump(gate, stream, indent=2)
        stream.write('\n')
    print('RESULT: PASS', gate['status'], 'inputs', len(hashes), 'evidence', len(evidence),
          'bit', gate['bitstream']['sha256'], 'board NOT_TESTED', flush=True)


if __name__ == '__main__':
    main()
