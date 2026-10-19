"""Offline checks of the serial tool using retained bytes and an in-memory port.

No serial device or HDL simulator is opened. Synthetic fixtures are not board
evidence and do not establish performance of the new instruction buffer.
"""
from pathlib import Path
import argparse
import importlib.util
import json
import re

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location('measurement', ROOT / 'tools/uart_loader/candidates/perf_2b/run_measurement.py')
tool = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tool)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--tag', required=True)
    a = p.parse_args()
    assert re.fullmatch('[a-z0-9_-]+', a.tag)
    out = ROOT / 'sim/inst_line_buffer/build' / a.tag
    assert not out.exists()
    checks = {}
    retained = {}
    raw_bytes = {}
    for name in tool.APPLICATIONS:
        filename = 'performance_60_retry1.json' if name == 'performance_60' else name + '.json'
        source = ROOT / 'sim/cpu_performance_2b/board/main_pds_first' / filename
        old = json.loads(source.read_text())
        info = tool.require_manifest(tool.manifest_for(name))
        data = bytes.fromhex(old['application']['rx_hex'])
        parsed = tool.parse_measurement(info, data, board=True, elapsed=old['application']['seconds'])
        assert parsed.get('counters') == old['application']['parsed'].get('counters')
        record = dict(old, status='MEASUREMENT_APPLICATION_BOARD_PASS', application_name=name,
                      deployment_gate_required=False, bitstream_local_file={'identity_scope': 'FIXTURE_ONLY'})
        record['application'] = dict(record['application'], parsed=parsed)
        assert tool.verify_record(record)['responses'] == len(old['records'])
        checks['retained_' + name] = 'PASS_PARSER_ONLY_NOT_NEW_BOARD_RUN'
        retained[source.relative_to(ROOT).as_posix()] = tool.sha(source)
        raw_bytes[name] = data

    info = tool.require_manifest(tool.manifest_for('performance_60'))
    data = raw_bytes['performance_60']
    prefix, sep, suffix = data.partition(b'PERF2B version=')
    ticks = 9 * tool.HZ
    text = prefix.decode()
    text = re.sub(r'(^Total ticks\s*:\s*)\d+', lambda m: m[1] + str(ticks), text, flags=re.M)
    text = re.sub(r'(^Total time \(secs\)\s*:\s*)\d+', lambda m: m[1] + '9', text, flags=re.M)
    text = re.sub(r'(^Iterations/Sec\s*:\s*)\d+', lambda m: m[1] + '6', text, flags=re.M)
    text = text.replace('Iterations       : 60\n', tool.TIME_ERROR + '\nIterations       : 60\n')
    text = re.sub(r'^Correct operation validated\..*$', 'Errors detected', text, flags=re.M)
    text = re.sub(r'PORT_DONE ticks=\d+', 'PORT_DONE ticks=' + str(ticks), text)
    counts = tool.parse_measurement(info, data, board=False)['counters']
    other = sum(counts[n] for n in tool.NAMES[2:9] if n != 'if_stall_cycles')
    assert ticks > other
    tail = (sep + suffix).decode()
    start = int(re.search(r'start=(\d+)', tail)[1])
    tail = re.sub(r'stop=\d+', 'stop=' + str((start + ticks) & 0xffffffff), tail)
    for name, value in [('cycles', ticks), ('if_stall_cycles', ticks - other)]:
        tail = re.sub(r'(PERF2B ' + name + r'=)[0-9a-fA-F]{16}', lambda m: m[1] + f'{value:016X}', tail)
    fast_fixture = text.encode() + tail.encode()
    parsed = tool.parse_measurement(info, fast_fixture, board=True, elapsed=9.1)
    assert parsed['status'] == 'COREMARK_FIXED_BIN_MEASUREMENT_PASS' and not parsed['formal_benchmark']
    checks['60_iterations_below_10_seconds'] = 'PASS_SYNTHETIC_FIXTURE_NOT_BOARD'

    info = tool.require_manifest(tool.manifest_for('performance_1'))
    rows = tool.make_plan(info)
    data = raw_bytes['performance_1']

    class Port:
        def __init__(self, corrupt=False):
            self.index = 0
            self.buffer = b''
            self.tail = []
            self.corrupt = corrupt
            self.chunks = 0

        @property
        def in_waiting(self):
            return len(self.buffer)

        def write(self, payload):
            row = rows[self.index]
            assert payload == bytes.fromhex(row['tx_hex'])
            self.index += 1
            self.buffer = bytes.fromhex(row['expected_hex'])
            if self.corrupt:
                self.buffer = bytes([self.buffer[0] ^ 1]) + self.buffer[1:]
            if row.get('run'):
                prefix, sep, suffix = data.partition(b'PERF2B version=')
                self.tail = [prefix, sep + suffix]
            return len(payload)

        def read(self, count):
            if not self.buffer and self.tail:
                self.buffer = self.tail.pop(0)
                self.chunks += 1
            result = self.buffer[:count]
            self.buffer = self.buffer[count:]
            return result

    port = Port()
    records, app = [], {}
    tool.execute(port, info, records, app, quiet=lambda _: None, board=False)
    assert len(records) == 129 and port.chunks == 2 and not port.tail
    assert app['result'] == 'PASS'
    assert sum(bool(row.get('run')) for row in records) == 1
    checks['stop_and_wait_and_split_counter_tail'] = 'PASS_IN_MEMORY_PORT'
    bad = [
        ('bad_crc', data.replace(b'[0]crcfinal      : 0xe714', b'[0]crcfinal      : 0xe715')),
        ('missing_counter', re.sub(rb'^PERF2B instret=.*\n', b'', data, flags=re.M)),
        ('extra_output', data + b'EXTRA\n'),
        ('wrong_cycles', re.sub(rb'(PERF2B cycles=)[0-9a-fA-F]{16}', rb'\g<1>0000000000000001', data)),
        ('unknown_error', data.replace(tool.TIME_ERROR.encode(), b'ERROR! incorrect CRC')),
        ('false_validation_below_10_seconds', fast_fixture.replace(b'Errors detected\n', b'Correct operation validated. See README.md for run and reporting rules.\n')),
    ]
    assert all(payload != (fast_fixture if name.startswith('false_') else data) for name, payload in bad)
    for name, payload in bad:
        selected = tool.require_manifest(tool.manifest_for('performance_60')) if name.startswith('false_') else info
        try:
            tool.parse_measurement(selected, payload, board=False)
        except (AssertionError, ValueError):
            checks[name] = 'REJECTED_AS_REQUIRED'
        else:
            raise AssertionError('Bad fixture accepted: ' + name)
    try:
        tool.execute(Port(corrupt=True), info, [], {}, quiet=lambda _: None, board=False)
    except (AssertionError, ValueError):
        checks['bad_protocol_response'] = 'REJECTED_AS_REQUIRED'
    else:
        raise AssertionError('Bad protocol accepted')
    assert all(tool.sha(ROOT / n) == h for n, h in retained.items())
    out.mkdir()
    report = dict(status='MEASUREMENT_TOOL_OFFLINE_CHECK_PASS', checks=checks,
                  retained_evidence_sha256=retained, tool_sha256=tool.sha(Path(tool.__file__)),
                  serial_opened=False, simulation_started=False, pds_started=False,
                  optimized_board_result='NOT_TESTED', deployment_gate_created=False)
    (out / 'result.json').write_text(json.dumps(report, indent=2) + '\n')
    print('RESULT: PASS offline measurement tool;', len(checks), 'checks; no serial or HDL')


if __name__ == '__main__':
    main()
