"""Small offline checks of fixed120 duration classification; no serial or HDL."""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / 'tools/uart_loader/candidates/perf_2b/run_measurement.py'
BASELINE = ROOT / 'sim/inst_line_buffer/board/measure_20261011_125621_924'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', required=True, type=Path)
    a = p.parse_args()
    assert not a.output.exists()
    spec = importlib.util.spec_from_file_location('duration_adapter', TOOL)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    checks = []
    raw = {}
    for name in tool.FORMAL_APPLICATIONS:
        raw[name] = json.loads((BASELINE / (name + '.json')).read_text())
        result = tool.verify_record(raw[name])
        assert result['application']['formal_benchmark']
        checks.append(name + '_historical_formal_unchanged')
    original = raw['performance_120']
    info = original['application_info']
    original_data = bytes.fromhex(original['application']['rx_hex']).decode('ascii')
    original_counts = original['application']['parsed']['counters']

    def fixture(ticks):
        text = original_data.replace('\r\n', '\n')
        seconds = ticks // tool.HZ
        text = re.sub(r'(?m)^(Total ticks\s*:\s*)\d+$', lambda m: m[1] + str(ticks), text)
        text = re.sub(r'(?m)^(Total time \(secs\)\s*:\s*)\d+$',
                      lambda m: m[1] + str(seconds), text)
        text = re.sub(r'(?m)^(Iterations/Sec\s*:\s*)\d+$',
                      lambda m: m[1] + str(120 // seconds) + '\n' + tool.TIME_ERROR, text)
        text = text.replace('Correct operation validated. See README.md for run and reporting rules.',
                            'Errors detected')
        text = re.sub(r'(?m)^(PORT_DONE ticks=)\d+', lambda m: m[1] + str(ticks), text)
        start = original['application']['parsed']['timer_start']
        text = re.sub(r'(PERF2B version=1 state=3 start=\d+ stop=)\d+',
                      lambda m: m[1] + str((start + ticks) & 0xffffffff), text)
        for name, value in (('cycles', ticks), ('if_stall_cycles',
                            original_counts['if_stall_cycles'] - original_counts['cycles'] + ticks)):
            assert value >= 0
            text = re.sub(r'(?m)^(PERF2B ' + name + r'=)[0-9a-fA-F]{16}$',
                          lambda m: m[1] + f'{value:016x}', text)
        return text.encode('ascii')

    fixtures = {}
    for label, ticks in (('nine_seconds', 9 * tool.HZ),
                         ('one_tick_below_ten_seconds', 10 * tool.HZ - 1)):
        data = fixture(ticks)
        result = tool.parse_measurement(info, data, board=True, elapsed=12)
        assert result['status'] == 'COREMARK_FIXED_BIN_MEASUREMENT_PASS'
        assert not result['formal_benchmark'] and not result['duration_requirement_met']
        assert result['crcfinal'] == 'd340' and result['iterations'] == 120
        assert result['counters']['instret'] == original_counts['instret']
        fixtures[label] = data
        checks.append(label + '_comparison_only')

    def rejected(label, data):
        try:
            tool.parse_measurement(info, data, board=True, elapsed=12)
        except (AssertionError, ValueError):
            checks.append(label + '_rejected')
        else:
            raise AssertionError(label + ' incorrectly accepted')

    data = fixtures['nine_seconds']
    rejected('bad_crc', data.replace(b'0xd340', b'0xd341'))
    rejected('missing_counter_tail', data.replace(b'PERF2B_DONE\n', b''))
    old_value = re.search(rb'PERF2B if_stall_cycles=([0-9a-fA-F]{16})', data)[1]
    rejected('nonconserving_counters', data.replace(
        b'PERF2B if_stall_cycles=' + old_value,
        b'PERF2B if_stall_cycles=' + f'{int(old_value,16)+1:016x}'.encode()))
    a.output.mkdir(parents=True)
    for label, data in fixtures.items():
        (a.output / ('OFFLINE_FIXTURE_' + label + '.txt')).write_bytes(data)
    receipt = dict(status='SHORT120_OFFLINE_ADAPTER_CHECKS_PASS', checks=checks,
                   input_sha256={str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                 for p in [Path(__file__), TOOL,
                                           *[BASELINE / (n + '.json') for n in tool.FORMAL_APPLICATIONS]]},
                   evidence_origin='OFFLINE_SYNTHETIC_DURATION_FIXTURES_NOT_BOARD',
                   serial_opened=False, simulation_started=False, pds_started=False)
    (a.output / 'result.json').write_text(json.dumps(receipt, indent=2) + '\n')
    print(receipt['status'], len(checks))


if __name__ == '__main__':
    main()
