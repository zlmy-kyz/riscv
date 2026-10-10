"""Offline rejection tests for the new application pipeline; never open serial."""
from pathlib import Path
import argparse
import copy
import json
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'tests/c_app'))
import pipeline as app


class Port:
    def __init__(self, info, output, *, corrupt=False, short=False, startup=False, extra=False):
        self.rows = app.plan.make_plan(info)
        self.output = output
        self.corrupt, self.short, self.extra = corrupt, short, extra
        self.buf = bytearray(b'x' if startup else b'')
        self.index = 0
        self.writes = []
        self.pending = b''

    @property
    def in_waiting(self):
        return len(self.buf)

    def write(self, data):
        row = self.rows[self.index]
        assert data == bytes.fromhex(row['tx_hex'])
        self.writes.append(data)
        raw = bytes.fromhex(row['expected_hex'])
        if self.corrupt:
            raw = raw[:-1] + bytes([raw[-1] ^ 1])
        self.buf += raw
        if row.get('run'):
            self.buf += self.output
            self.pending = b'extra' if self.extra else b''
        self.index += 1
        return len(data) - int(self.short)

    def read(self, size):
        data = bytes(self.buf[:min(size, 7)])
        del self.buf[:len(data)]
        return data

    def quiet(self, seconds):
        if seconds == .1:
            self.buf += self.pending
            self.pending = b''


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--build', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    assert not a.output.exists()
    out = a.build.resolve()
    info, _ = app.require_gate(out)
    actual = (app.SIM / 'build' / out.name / 'application_uart.txt').read_bytes()
    checks = []

    def reject(name, callback):
        try:
            callback()
        except (ValueError, AssertionError, RuntimeError):
            checks.append(dict(name=name, result='PASS'))
            return
        raise AssertionError('Did not reject: ' + name)

    port = Port(info, actual)
    records, output = [], {}
    app.execute(port, info, records, output, quiet=port.quiet)
    assert len(records) == len(port.rows) and sum(bool(r.get('run')) for r in records) == 1
    assert output['parsed']['status'] == 'C_APP_OUTPUT_PASS'
    checks.append(dict(name='fragmented_UART_LOAD_VERIFY_RUN_and_output', result='PASS'))

    for name, options in [('bad_response_crc', dict(corrupt=True)), ('short_write', dict(short=True)), ('startup_RX', dict(startup=True))]:
        def bad(options=options):
            port = Port(info, actual, **options)
            try:
                app.execute(port, info, [], {}, quiet=port.quiet)
            finally:
                assert len(port.writes) <= 1 and not any(r.get('run') for r in port.rows[:port.index])
        reject(name + '_stops_before_LOAD_without_retry', bad)

    reject('wrong_expected_output', lambda: app.parse_output(info, actual.replace(bytes.fromhex(info['expected_hex']), b'WRONG')))
    reject('nonzero_main_return', lambda: app.parse_output(info, actual.replace(b'return=0', b'return=1')))
    reject('duplicate_completion', lambda: app.parse_output(info, actual + app.DONE))
    reject('missing_completion', lambda: app.parse_output(info, actual[:-len(app.DONE)]))
    reject('trap_failure', lambda: app.parse_output(info, b'TRAP_FAIL\n' + actual))
    reject('BSP_failure', lambda: app.parse_output(info, b'C_APP_BSP_FAIL\n' + actual))
    reject('oversize_output', lambda: app.parse_output(info, b'x' * app.MAX_OUTPUT + actual))
    exact = dict(info, expect_mode='exact', expected_hex=actual[:-len(app.DONE)].hex())
    app.parse_output(exact, actual)
    reject('exact_output_extra_bytes', lambda: app.parse_output(exact, b'x' + actual))
    reject('duplicate_expected_text', lambda: app.parse_output(info, actual[:-len(app.DONE)] + bytes.fromhex(info['expected_hex']) + app.DONE))
    def extra():
        port = Port(info, actual, extra=True)
        app.execute(port, info, [], {}, quiet=port.quiet)
    reject('extra_UART_after_completion', extra)
    def timeout():
        port = Port(info, b'no completion')
        app.execute(port, info, [], {}, quiet=port.quiet, timeout=.001)
    reject('missing_completion_deadline', timeout)

    binary = ROOT / info['bin_path']
    original = binary.read_bytes()
    try:
        binary.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        reject('modified_BIN_rejected_before_serial', lambda: app.require_gate(out))
    finally:
        binary.write_bytes(original)
    app.require_gate(out)
    fixture = a.output.with_suffix('.fixture.json')
    assert not fixture.exists()
    app.save(fixture, dict(status='C_APP_ACTUAL_BOARD_PASS', evidence_origin='OFFLINE_FIXTURE_NOT_BOARD'))
    reject('offline_fixture_is_not_actual_board_evidence', lambda: app.verify_log(fixture))
    existing_log = a.output.with_suffix('.existing.json')
    assert not existing_log.exists()
    app.save(existing_log, dict(evidence_origin='OFFLINE_EXISTING_LOG_TEST'))
    reject('existing_log_stops_before_prompt_or_serial', lambda: app.deploy(out, existing_log))
    evidence = app.SIM / 'build' / out.name / 'application_uart.txt'
    original = evidence.read_bytes()
    try:
        evidence.write_bytes(original + b'x')
        reject('modified_simulation_evidence_stops_before_serial', lambda: app.deploy(out, a.output.with_suffix('.unused.json')))
    finally:
        evidence.write_bytes(original)
    app.require_gate(out)
    # All fixtures here are explicitly offline; not evidence of physical UART.
    app.save(a.output, dict(status='C_APP_OFFLINE_CHECKS_PASS', evidence_origin='OFFLINE_FIXTURE_NOT_BOARD',
                           count=len(checks), checks=checks, serial_opened=False, board_result='NOT_TESTED'))
    print('RESULT: PASS', len(checks), 'generic application offline checks; no serial opened')


if __name__ == '__main__':
    main()
