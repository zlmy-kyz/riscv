"""Read-only same-BIN actual-DDR comparison: four versus eight I rows."""
import argparse
import csv
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--baseline-directory', required=True, type=Path)
    parser.add_argument('--optimized-directory', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve previous evidence'
    tool_path = ROOT / 'tools/uart_loader/candidates/perf_2b/run_measurement.py'
    spec = importlib.util.spec_from_file_location('cache8_measurement', tool_path)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)  # Defines parsers; does not open a serial port.
    inputs = {}
    copies = []

    def protect(path, relative):
        path = Path(path).resolve()
        inputs[path.as_posix()] = sha(path)
        copies.append((path, relative))

    baseline = ROOT / 'sim/inst_line_buffer/build/eight_line_baseline_20261011_a'
    pds_path = ROOT / 'sim/inst_line_buffer/build/review_cache8_pds_20261011_a/review_result.json'
    pds = read(pds_path)
    assert pds['status'] == 'INST_CACHE8_POST_PNR_TIMING_AUDIT_PASS'
    simulation_path = ROOT / 'sim/inst_line_buffer/build/review_cache8_evidence_20261011_a/review_result.json'
    simulation = read(simulation_path)
    assert simulation['status'] == 'INST_CACHE8_EVIDENCE_AUDIT_PASS'
    for name, digest in simulation['protected_sha256'].items():
        assert sha(ROOT / name) == digest, 'Reviewed input changed: ' + name
    bridge = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
    bit = ROOT / 'generate_bitstream/board_top.sbit'
    assert sha(bridge) == 'a2c28dce9c8d1c1ab2af2fc98fbc8c1a46f3fb17bc67cacb12b36c9a2504091a'
    assert sha(baseline / bridge.name) == 'b7c2b3664b80b22bdf353d4c4236edfcd93cf59e0a5f6602683421b6692c8e97'
    assert pds['bitstream_sha256'] == sha(bit)
    for path, relative in ((Path(__file__), 'tools/compare_cache8_fixed120.py'),
                           (tool_path, 'tools/run_measurement.py'),
                           (pds_path, 'reviews/PDS.json'),
                           (simulation_path, 'reviews/simulation.json'),
                           (baseline / bridge.name, 'hardware/baseline/' + bridge.name),
                           (baseline / 'board_top.sbit', 'hardware/baseline/board_top.sbit'),
                           (bridge, 'hardware/optimized/' + bridge.name),
                           (bit, 'hardware/optimized/board_top.sbit'),
                           (ROOT / 'myriscv/uart_mmio.v', 'hardware/optimized/uart_mmio.v')):
        protect(path, relative)
    cases = {}
    for name in tool.FORMAL_APPLICATIONS:
        paths = [directory / (name + '.json') for directory in
                 (args.baseline_directory, args.optimized_directory)]
        raw = [read(path) for path in paths]
        checked = [tool.verify_record(record) for record in raw]
        assert raw[0]['application_info'] == raw[1]['application_info']
        assert raw[0]['manifest_sha256'] == raw[1]['manifest_sha256']
        apps = [item['application'] for item in checked]
        assert all(app['iterations'] == 120 for app in apps)
        assert apps[0]['crcfinal'] == apps[1]['crcfinal']
        bc, oc = [app['counters'] for app in apps]
        assert all(bc[key] == oc[key] for key in ('instret', 'branch_redirects', 'ddr_aw_commands'))
        assert checked[0]['bitstream_local_file']['sha256'] == sha(baseline / 'board_top.sbit')
        assert checked[1]['bitstream_local_file']['sha256'] == sha(bit)
        cases[name] = dict(baseline=checked[0], optimized=checked[1], same_software=True,
            time_reduction_percent=(1 - oc['cycles'] / bc['cycles']) * 100,
            throughput_increase_percent=(bc['cycles'] / oc['cycles'] - 1) * 100,
            counter_delta={key: dict(before=bc[key], after=oc[key], delta=oc[key]-bc[key],
                change_percent=(oc[key]/bc[key]-1)*100 if bc[key] else None) for key in tool.NAMES},
            cycle_shares_percent={key: oc[key]*100/oc['cycles'] for key in tool.NAMES[2:9]},
            cpi_components={key: oc[key]/oc['instret'] for key in tool.NAMES[2:9]},
            branch_recovery_cycles_per_redirect=oc['branch_flush_cycles']/oc['branch_redirects'])
        for label, path in zip(('baseline', 'optimized'), paths):
            protect(path, 'logs/' + label + '/' + path.name)
        manifest = tool.manifest_for(name)
        info = tool.require_manifest(manifest)
        for path in (manifest, ROOT / info['bin_path'], ROOT / info['elf_path']):
            protect(path, 'software/' + name + '/' + path.name)
    args.output.mkdir(parents=True)
    for path, relative in copies:
        target = args.output / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == inputs[path.as_posix()]
    assert all(sha(Path(path)) == digest for path, digest in inputs.items())
    result = dict(status='INST_CACHE8_SAME_BIN_BOARD_COMPARISON_PASS', cases=cases,
        input_sha256=inputs, both_optimized_modes_formal=all(c['optimized']['application']['formal_benchmark'] for c in cases.values()),
        runs_per_mode_per_version=1, FPGA_programming_independently_observed=False,
        pds_started=False, simulation_started=False, serial_opened=False,
        limitations=['No repeated-run variance estimate', 'AR combines IF and data',
                     'Branch recovery includes target fetch wait', 'No dynamic cache miss/conflict attribution'])
    (args.output / 'comparison.json').write_text(json.dumps(result, indent=2)+'\n', encoding='utf-8')
    with (args.output / 'counter_deltas.csv').open('w', newline='', encoding='utf-8') as stream:
        writer = csv.writer(stream)
        writer.writerow(['application', 'counter', 'before', 'after', 'delta', 'change_percent'])
        for name, case in cases.items():
            for key, delta in case['counter_delta'].items():
                writer.writerow([name, key, *[delta[k] for k in ('before','after','delta','change_percent')]])
    print(result['status'])
    for name, case in cases.items():
        print(name, 'time_reduction_percent=', case['time_reduction_percent'],
              'throughput_increase_percent=', case['throughput_increase_percent'],
              'cycle_shares_percent=', case['cycle_shares_percent'])


if __name__ == '__main__':
    main()
