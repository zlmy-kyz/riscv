"""Compare the same fixed120 BINs using verified actual serial evidence only."""
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
    p.add_argument('--baseline-directory', required=True, type=Path)
    p.add_argument('--optimized-directory', required=True, type=Path)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    assert not a.output.exists(), 'Preserve previous evidence; use a fresh output'
    spec = importlib.util.spec_from_file_location('measurement_compare', TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    input_sha = {str(TOOL.resolve()): sha(TOOL)}
    cases = {}
    raw_files = []
    for name in tool.FORMAL_APPLICATIONS:
        paths = [folder / (name + '.json') for folder in
                 (a.baseline_directory, a.optimized_directory)]
        raw = [json.loads(path.read_text(encoding='utf-8')) for path in paths]
        checked = [tool.verify_record(r) for r in raw]
        for path in paths:
            input_sha[str(path.resolve())] = sha(path)
        assert raw[0]['application_info'] == raw[1]['application_info']
        assert raw[0]['manifest_sha256'] == raw[1]['manifest_sha256']
        apps = [r['application'] for r in checked]
        assert all(r['status'] == 'COREMARK_FORMAL_BOARD_PASS' and
                   r['iterations'] == 120 and r['seconds'] >= 10 for r in apps)
        assert apps[0]['crcfinal'] == apps[1]['crcfinal']
        bc, oc = [r['counters'] for r in apps]
        unchanged = ['instret', 'branch_redirects', 'ddr_aw_commands']
        assert all(bc[n] == oc[n] for n in unchanged)
        saved = bc['cycles'] - oc['cycles']
        cases[name] = dict(
            baseline=checked[0], optimized=checked[1],
            same_software=True, same_work_counters=unchanged,
            same_bin_sha256=raw[0]['application_info']['bin_sha256'],
            seconds_saved=apps[0]['seconds'] - apps[1]['seconds'],
            time_reduction_percent=saved * 100 / bc['cycles'],
            throughput_increase_percent=(bc['cycles'] / oc['cycles'] - 1) * 100,
            cycle_shares_percent={n: oc[n] * 100 / oc['cycles']
                                  for n in tool.NAMES[2:9]},
            cpi_components={n: oc[n] / oc['instret'] for n in tool.NAMES[2:9]},
            counter_delta={n: dict(before=bc[n], after=oc[n], delta=oc[n] - bc[n],
                                  change_percent=(oc[n] / bc[n] - 1) * 100
                                  if bc[n] else None) for n in tool.NAMES},
            if_savings_fraction_of_net_savings=(bc['if_stall_cycles'] -
                                               oc['if_stall_cycles']) / saved
            if saved else None,
            branch_recovery_cycles_per_redirect={
                label: counts['branch_flush_cycles'] / counts['branch_redirects']
                for label, counts in zip(('baseline', 'optimized'), (bc, oc))})
        for label, path in zip(('baseline', 'optimized'), paths):
            raw_files.append((label, path))
        manifest = tool.manifest_for(name)
        info = tool.require_manifest(manifest)
        for path in (manifest, ROOT / info['bin_path'], ROOT / info['elf_path']):
            input_sha[str(path.resolve())] = sha(path)
    assert len({cases[n]['optimized']['bitstream_local_file']['sha256']
                for n in cases}) == 1
    bit = ROOT / 'generate_bitstream/board_top.sbit'
    bridge = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
    assert sha(bit) == next(iter(cases.values()))['optimized']['bitstream_local_file']['sha256']
    assert sha(bridge) == '5fbf40c186c1250151769de098e9a5f2a53d46d6810402b44db5f235c3c9e58a'
    for path in (bit, bridge):
        input_sha[str(path.resolve())] = sha(path)
    a.output.mkdir(parents=True)
    for label, path in raw_files:
        target = a.output / 'frozen_logs' / label / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == input_sha[str(path.resolve())]
    for path in (bit, bridge):
        target = a.output / 'local_file_snapshot' / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == input_sha[str(path.resolve())]
    for path, digest in input_sha.items():
        assert sha(Path(path)) == digest, 'Input changed during audit: ' + path
    receipt = dict(status='SELECTIVE_INVALIDATION_SAME_BIN_BOARD_COMPARISON_PASS',
                   cases=cases, input_sha256=input_sha,
                   runs_per_mode_per_version=1,
                   FPGA_programming_independently_observed=False,
                   hardware_change_causality_independently_proven=False,
                   pds_started=False, serial_opened=False,
                   limitations=['No repeated-run variance estimate',
                                'AR combines instruction and data reads',
                                'Branch recovery includes target fetch wait',
                                'No cache hit/miss/invalidation-cause counters'])
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
