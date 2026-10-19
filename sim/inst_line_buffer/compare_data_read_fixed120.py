"""Offline fixed120 serial comparison for the reviewed single-line data-read buffer stage."""
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
BASELINE_SHA = 'a1bf18ff0f48ea0801269ae77fdb1b04f80788d381a4b8c5a1c785b0ac30006d'
CANDIDATE_SHA = 'b7c2b3664b80b22bdf353d4c4236edfcd93cf59e0a5f6602683421b6692c8e97'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--baseline-directory', required=True, type=Path)
    p.add_argument('--optimized-directory', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    assert not a.output.exists(), 'Preserve previous evidence; use a fresh output'
    spec = importlib.util.spec_from_file_location('data_read_measurement', TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    inputs = {}
    files = []

    def protect(path, target):
        inputs[str(path.resolve())] = sha(path)
        files.append((path, target))

    protect(Path(__file__), 'review_tools/compare_data_read_fixed120.py')
    protect(TOOL, 'review_tools/run_measurement.py')
    cases = {}
    for name in tool.FORMAL_APPLICATIONS:
        paths = [d / (name + '.json') for d in
                 (a.baseline_directory, a.optimized_directory)]
        raw = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
        checked = [tool.verify_record(r) for r in raw]
        assert raw[0]['application_info'] == raw[1]['application_info']
        assert raw[0]['manifest_sha256'] == raw[1]['manifest_sha256']
        apps = [r['application'] for r in checked]
        assert all(r['iterations'] == 120 and r['status'] ==
                   ('COREMARK_FORMAL_BOARD_PASS' if r['seconds'] >= 10 else
                    'COREMARK_FIXED_BIN_MEASUREMENT_PASS') for r in apps)
        assert apps[0]['crcfinal'] == apps[1]['crcfinal']
        bc, oc = [r['counters'] for r in apps]
        unchanged = ['instret', 'branch_redirects', 'ddr_aw_commands']
        assert all(bc[n] == oc[n] for n in unchanged)
        saved = bc['cycles'] - oc['cycles']
        cases[name] = dict(
            baseline=checked[0], optimized=checked[1], same_software=True,
            same_work_counters=unchanged,
            same_bin_sha256=raw[0]['application_info']['bin_sha256'],
            seconds_saved=apps[0]['seconds'] - apps[1]['seconds'],
            time_reduction_percent=saved * 100 / bc['cycles'],
            throughput_increase_percent=(bc['cycles'] / oc['cycles'] - 1) * 100,
            iterations_per_second={label: 120 / app['seconds'] for label, app
                                   in zip(('baseline', 'optimized'), apps)},
            cycle_shares_percent={n: oc[n] * 100 / oc['cycles']
                                  for n in tool.NAMES[2:9]},
            cpi_components={n: oc[n] / oc['instret'] for n in tool.NAMES[2:9]},
            counter_delta={n: dict(before=bc[n], after=oc[n], delta=oc[n] - bc[n],
                                  change_percent=(oc[n] / bc[n] - 1) * 100
                                  if bc[n] else None) for n in tool.NAMES},
            branch_recovery_cycles_per_redirect={label:
                counts['branch_flush_cycles'] / counts['branch_redirects']
                for label, counts in zip(('baseline', 'optimized'), (bc, oc))})
        for label, path in zip(('baseline', 'optimized'), paths):
            protect(path, 'frozen_logs/' + label + '/' + path.name)
        manifest = tool.manifest_for(name)
        info = tool.require_manifest(manifest)
        for path in (manifest, ROOT / info['bin_path'], ROOT / info['elf_path']):
            protect(path, 'software/' + name + '/' + path.name)

    bridge = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
    bit = ROOT / 'generate_bitstream/board_top.sbit'
    baseline_bridge = ROOT / 'sim/inst_line_buffer/build/data_read_baseline_20261011_a/dual_sram_to_pango_ddr_bridge.v'
    baseline_bit = ROOT / 'sim/inst_line_buffer/build/data_read_baseline_20261011_a/board_top.sbit'
    assert sha(bridge) == CANDIDATE_SHA and sha(baseline_bridge) == BASELINE_SHA
    for label, path in (('baseline', baseline_bit), ('optimized', bit)):
        hashes = {case[label]['bitstream_local_file']['sha256']
                  for case in cases.values()}
        assert hashes == {sha(path)}, 'Local bit identity mismatch'
    review = ROOT / 'sim/uart_mmio/build/review_wait_chain_20261011_a/review_result.json'
    review_data = json.loads(review.read_text(encoding='utf-8'))
    assert review_data['status'] == 'UART_WAIT_CHAIN_EVIDENCE_AUDIT_PASS'
    for name, digest in review_data['protected_sha256'].items():
        assert sha(ROOT / name) == digest, 'Reviewed input changed: ' + name
    for label, path in (('baseline', baseline_bridge), ('baseline', baseline_bit),
                        ('optimized', bridge), ('optimized', bit)):
        protect(path, 'local_file_snapshot/' + label + '/' + path.name)
    protect(review, 'review_tools/UART_simulation_review.json')
    uart = ROOT / 'myriscv/uart_mmio.v'
    protect(uart, 'local_file_snapshot/optimized/uart_mmio.v')
    d_review = ROOT / 'sim/inst_line_buffer/build/review_data_read_cpu_20261011_a/review_result.json'
    d_data = json.loads(d_review.read_text(encoding='utf-8'))
    assert d_data['status'] == 'DATA_READ_BUFFER_EVIDENCE_AUDIT_PASS'
    assert d_data['protected_sha256']['myriscv/dual_sram_to_pango_ddr_bridge.v'] == sha(bridge)
    protect(d_review, 'review_tools/D_simulation_review.json')
    pds_review = ROOT / 'sim/uart_mmio/build/review_wait_chain_pds_20261011_a/review_result.json'
    pds = json.loads(pds_review.read_text(encoding='utf-8'))
    assert pds['status'] == 'UART_WAIT_CHAIN_POST_PNR_TIMING_AUDIT_PASS'
    assert pds['bitstream_sha256'] == sha(bit)
    assert pds['slow_setup_WNS_ns'] >= 0 and pds['all_reported_failing_endpoints'] == 0
    protect(pds_review, 'review_tools/PDS_review.json')
    a.output.mkdir(parents=True)
    for path, relative in files:
        target = a.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == inputs[str(path.resolve())]
    for path, digest in inputs.items():
        assert sha(Path(path)) == digest, 'Input changed during audit: ' + path
    receipt = dict(status='DATA_READ_BUFFER_SAME_BIN_BOARD_COMPARISON_PASS',
                   cases=cases, input_sha256=inputs,
                   both_optimized_modes_formal=all(c['optimized']['application']['formal_benchmark'] for c in cases.values()),
                   runs_per_mode_per_version=1,
                   FPGA_programming_independently_observed=False,
                   hardware_change_causality_independently_proven=False,
                   pds_started=False, simulation_started=False, serial_opened=False,
                   limitations=['No repeated-run variance estimate',
                                'AR combines instruction and data reads',
                                'Branch recovery includes target fetch wait',
                                'No cache hit/miss/invalidation-cause counters',
                                'Candidate also contains UART timing-only refinement; sampled interface equivalence previously passed'])
    (a.output / 'comparison.json').write_text(
        json.dumps(receipt, indent=2) + '\n', encoding='utf-8')
    with (a.output / 'counter_deltas.csv').open('w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(['application', 'counter', 'before', 'after', 'delta', 'change_percent'])
        for name, case in cases.items():
            for counter, delta in case['counter_delta'].items():
                w.writerow([name, counter, *[delta[k] for k in
                           ('before', 'after', 'delta', 'change_percent')]])
    print(receipt['status'])
    for name, case in cases.items():
        print(name, 'seconds_saved=', case['seconds_saved'],
              'throughput_increase_percent=', case['throughput_increase_percent'])


if __name__ == '__main__':
    main()
