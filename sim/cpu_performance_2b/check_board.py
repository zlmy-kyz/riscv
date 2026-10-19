"""Read-only six-application audit; preserve partial runs and original UART logs."""
from pathlib import Path
import argparse
import csv
import importlib.util
import json
import shutil
import sys

ROOT = Path(__file__).resolve().parents[2]
NAMES = ('hello', 'crc32', 'performance_1', 'validation_1',
         'performance_60', 'validation_60')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--logs', type=Path, required=True)
    parser.add_argument('--tag', required=True)
    parser.add_argument('--performance-60-log', type=Path)
    parser.add_argument('--validation-60-log', type=Path)
    args = parser.parse_args()
    assert args.tag and all(c.isalnum() or c in '_-' for c in args.tag)
    logs = args.logs.resolve()
    out = logs / args.tag
    assert not out.exists(), 'Use a fresh audit tag; preserve old evidence'
    spec = importlib.util.spec_from_file_location(
        'perf_board', ROOT / 'tools/uart_loader/candidates/perf_2b/run_board.py')
    board = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(board)
    paths = {name: logs / (name + '.json') for name in NAMES}
    for name in ('performance_60', 'validation_60'):
        override = getattr(args, name + '_log')
        if override is not None:
            paths[name] = override.resolve()
    before = {name: board.sha(path) for name, path in paths.items()}
    gate_digest = board.sha(board.GATE)
    gate = json.loads(board.GATE.read_text())
    items = {}
    metrics = []
    for name, path in paths.items():
        raw = json.loads(path.read_text())
        manifest = Path(raw['manifest_path'])
        board.require_gate(manifest)
        info = board.require_manifest(manifest)
        assert raw['application_info'] == info
        assert raw['manifest_sha256'] == board.sha(manifest)
        assert raw['gate_sha256'] == gate_digest
        assert raw['bitstream'] == gate['bitstream']
        assert raw['evidence_origin'] == 'ACTUAL_SERIAL'
        assert raw['serial_opened'] and raw['user_KEY0_confirmation']
        assert raw['retry_count'] == 0 and raw['no_automatic_retry']
        planned = board.make_plan(info)
        assert len(raw['records']) == len(planned)
        counts = {'ACK': 0, 'READY': 0, 'RUN': 0}
        for request, response in zip(planned, raw['records']):
            assert response['result'] == 'PASS' and response['extra_rx_hex'] == ''
            assert response['written_bytes'] == len(bytes.fromhex(request['tx_hex']))
            assert all(response[key] == value for key, value in request.items())
            decoded = board.rvld.decode(bytes.fromhex(response['rx_hex']),
                                        bytes.fromhex(request['expected_hex']))
            assert response['decoded'] == decoded
            assert decoded['status'] in (0, 1)
            counts['ACK' if decoded['status'] == 0 else 'READY'] += 1
            counts['RUN'] += bool(request.get('run'))
        assert counts['RUN'] == 1
        item = dict(log=path.relative_to(ROOT).as_posix(), sha256=before[name],
                    raw_status=raw['status'], protocol_status='PASS',
                    responses=len(planned), **counts)
        if raw['status'] == 'PERF2B_APPLICATION_BOARD_PASS':
            verified = board.verify(path)
            item.update(application_status='PASS', verified=verified)
            if info['kind'] == 'coremark':
                app = verified['application']
                c = app['counters']
                metrics.append(dict(application=name, **c, cpi=app['cpi'],
                                    seconds=app['seconds'], crcfinal=app['crcfinal'],
                                    **{key + '_percent': c[key] * 100 / c['cycles']
                                       for key in ('if_stall_cycles', 'mem_stall_cycles',
                                                   'branch_flush_cycles', 'other_cycles')}))
        else:
            item.update(application_status='NOT_VERIFIED',
                        error=raw.get('error'),
                        application_rx_bytes=len(bytes.fromhex(raw['application'].get('rx_hex', ''))),
                        application_record=raw['application'])
        items[name] = item
    assert before == {name: board.sha(path) for name, path in paths.items()}
    assert board.sha(board.GATE) == gate_digest
    passed = sum(item['application_status'] == 'PASS' for item in items.values())
    out.mkdir()
    frozen = out / 'frozen_logs'
    frozen.mkdir()
    archives = {}
    for name, path in paths.items():
        dest = frozen / (name + '.json')
        shutil.copyfile(path, dest)
        assert board.sha(dest) == before[name]
        archives[name] = dict(path=dest.relative_to(ROOT).as_posix(), sha256=before[name])
    shutil.copyfile(board.GATE, out / 'deployment_gate.json')
    with (out / 'metrics.csv').open('w', newline='', encoding='utf-8') as stream:
        if metrics:
            writer = csv.DictWriter(stream, fieldnames=list(metrics[0]))
            writer.writeheader()
            writer.writerows(metrics)
    report = dict(status='PERF2B_SIX_APPLICATION_ACTUAL_BOARD_VERIFIED' if passed == 6
                  else 'PERF2B_BOARD_AUDIT_INCOMPLETE',
                  applications_passed=passed, applications_expected=6,
                  protocol_responses=sum(item['responses'] for item in items.values()),
                  ACK=sum(item['ACK'] for item in items.values()),
                  READY=sum(item['READY'] for item in items.values()),
                  RUN=sum(item['RUN'] for item in items.values()),
                  gate_sha256=gate_digest, bitstream=gate['bitstream'],
                  checked_inputs=len(gate['input_sha256']),
                  checked_evidence=len(gate['evidence_sha256']),
                  checked_frozen_source_copies=len(gate['frozen_source_copies']),
                  original_logs_unchanged=True, archived_logs=archives,
                  auditor_sha256=board.sha(Path(__file__)),
                  codex_opened_serial=False, items=items)
    (out / 'independent_result.json').write_text(json.dumps(report, indent=2) + '\n')
    print(report['status'], f'{passed}/6 applications; '
          f"{report['protocol_responses']} responses; serial not opened")
    return 0 if passed == 6 else 2


if __name__ == '__main__':
    sys.exit(main())
