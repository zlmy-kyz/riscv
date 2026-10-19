"""Offline UART evidence/13-counter comparison; no deployment gate or hardware IO."""
from pathlib import Path
import argparse
import csv
import importlib.util
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('measurement', ROOT / 'tools/uart_loader/candidates/perf_2b/run_measurement.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)
BASELINE = ROOT / 'sim/cpu_performance_2b/board/main_pds_first/audit_retry1_20261010_a/independent_result.json'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--logs', type=Path, required=True)
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+', a.tag)
    folder = a.logs.resolve()
    out = folder / a.tag
    assert not out.exists(), 'Preserve previous audits; use a fresh tag'
    original = json.loads(BASELINE.read_text())
    assert original['status'] == 'PERF2B_SIX_APPLICATION_ACTUAL_BOARD_VERIFIED'
    evidence = {BASELINE.relative_to(ROOT).as_posix(): tool.sha(BASELINE)}
    items, rows, bit_hashes, paths = {}, [], set(), []
    ack = ready = run = 0
    for name in tool.APPLICATIONS:
        path = folder / (name + '.json')
        baseline_path = ROOT / original['archived_logs'][name]['path']
        assert tool.sha(baseline_path) == original['archived_logs'][name]['sha256']
        evidence[path.relative_to(ROOT).as_posix()] = tool.sha(path)
        evidence[baseline_path.relative_to(ROOT).as_posix()] = tool.sha(baseline_path)
        new = json.loads(path.read_text())
        old = json.loads(baseline_path.read_text())
        verified = tool.verify(path)
        assert old['status'] == 'PERF2B_APPLICATION_BOARD_PASS'
        assert old['evidence_origin'] == 'ACTUAL_SERIAL' and old['serial_opened']
        assert new['application_info'] == old['application_info']
        assert new['manifest_sha256'] == old['manifest_sha256']
        # Verify archived baseline protocol and output again without requiring
        # its old PDS workspace (the user has intentionally rebuilt that).
        adapter = dict(old, status='MEASUREMENT_APPLICATION_BOARD_PASS',
                       application_name=name, bitstream_local_file={'identity_scope': 'ARCHIVED_BASELINE'})
        adapter['application'] = dict(old['application'], parsed=tool.parse_measurement(
            old['application_info'], bytes.fromhex(old['application']['rx_hex']),
            board=True, elapsed=old['application']['seconds']))
        base_verified = tool.verify_record(adapter)
        bit_hashes.add(new['bitstream_local_file']['sha256'])
        protocol = dict(ACK=0, READY=0, RUN=0)
        for row in new['records']:
            protocol['ACK' if row['decoded']['status'] == 0 else 'READY'] += 1
            protocol['RUN'] += bool(row.get('run'))
        ack += protocol['ACK']
        ready += protocol['READY']
        run += protocol['RUN']
        item = dict(verified=verified, protocol=protocol, baseline=base_verified)
        if name not in ('hello', 'crc32'):
            nc = verified['application']['counters']
            bc = base_verified['application']['counters']
            assert bc == old['application']['parsed']['counters']
            assert nc['instret'] == bc['instret']
            assert nc['branch_redirects'] == bc['branch_redirects']
            assert nc['ddr_aw_commands'] == bc['ddr_aw_commands']
            assert verified['application']['crcfinal'] == base_verified['application']['crcfinal']
            saved = bc['cycles'] - nc['cycles']
            comparison = dict(speedup=bc['cycles'] / nc['cycles'], saved_cycles=saved,
                              time_reduction_percent=100 * (1 - nc['cycles'] / bc['cycles']),
                              counters={}, branch_cycles_per_redirect_before=bc['branch_flush_cycles'] / bc['branch_redirects'],
                              branch_cycles_per_redirect_after=nc['branch_flush_cycles'] / nc['branch_redirects'])
            for counter in tool.NAMES:
                change = nc[counter] - bc[counter]
                values = dict(baseline=bc[counter], current=nc[counter], delta=change,
                              reduction_percent=100 * (1 - nc[counter] / bc[counter]) if bc[counter] else None)
                if counter in tool.NAMES[2:9]:
                    values.update(baseline_share_percent=100 * bc[counter] / bc['cycles'],
                                  current_share_percent=100 * nc[counter] / nc['cycles'],
                                  current_cpi_component=nc[counter] / nc['instret'],
                                  saved_cycle_share_percent=100 * (bc[counter] - nc[counter]) / saved)
                comparison['counters'][counter] = values
            item['comparison'] = comparison
            rows.append(dict(application=name, **nc, cpi=verified['application']['cpi'],
                             seconds=verified['application']['seconds'],
                             baseline_cycles=bc['cycles'], baseline_seconds=base_verified['application']['seconds'],
                             baseline_cpi=base_verified['application']['cpi'], speedup=comparison['speedup'],
                             formal_benchmark=verified['application']['formal_benchmark'],
                             crcfinal=verified['application']['crcfinal']))
        else:
            assert verified['application'] == base_verified['application']
        items[name] = item
        paths.extend([(path, 'current', name), (baseline_path, 'baseline', name)])
    assert len(bit_hashes) == 1 and None not in bit_hashes
    assert ack + ready == 564 and run == 6
    assert all(tool.sha(ROOT / n) == h for n, h in evidence.items())
    out.mkdir()
    for path, group, name in paths:
        target = out / 'frozen_logs' / group / (name + '.json')
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert tool.sha(target) == tool.sha(path)
    with (out / 'metrics.csv').open('w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    assert all(tool.sha(ROOT / n) == h for n, h in evidence.items())
    report = dict(status='INST_LINE_BUFFER_SIX_APPLICATION_BOARD_LOGS_VERIFIED',
                  applications_passed=6, protocol_responses=564, ACK=ack, READY=ready, RUN=run,
                  items=items, evidence_sha256=evidence, local_bitstream_sha256=list(bit_hashes)[0],
                  bitstream_identity_scope='LOCAL_FILE_RECORDED_NOT_OBSERVED_FPGA_PROGRAMMING',
                  tool_sha256=tool.sha(Path(tool.__file__)), auditor_sha256=tool.sha(Path(__file__)),
                  original_logs_unchanged=True, serial_opened_by_auditor=False,
                  pds_started=False, simulation_started=False, deployment_gate_created=False,
                  optimized_formal_coremark=False, repeated_run_variance='NOT_MEASURED')
    (out / 'review_result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('RESULT: PASS offline six-application audit; responses', ack + ready, 'RUN', run)
    for row in rows:
        print(row['application'], 'cycles', row['cycles'], 'CPI', f"{row['cpi']:.6f}",
              'seconds', f"{row['seconds']:.9f}", 'speedup', f"{row['speedup']:.6f}",
              'formal', row['formal_benchmark'])


if __name__ == '__main__':
    main()
