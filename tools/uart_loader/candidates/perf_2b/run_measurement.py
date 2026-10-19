"""Download fixed measurement BINs; no deployment gate or PDS export required."""
from pathlib import Path
import argparse
import hashlib
import inspect
import json
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / 'tools/uart_loader/candidates/bsp_workflow'))
import upload
from application import require_manifest, parse_output, TIME_ERROR, HZ
from plan import make_plan, rvld
sys.path.insert(0, str(ROOT / 'sim/cpu_performance_2b'))
from check_output import NAMES
sys.path.insert(0, str(ROOT / 'tests/cpu_performance_2b'))
from measurement_software import require_manifest, FORMAL_DIR

APPLICATIONS = ('hello', 'crc32', 'performance_1', 'validation_1', 'performance_60', 'validation_60')
FORMAL_APPLICATIONS = ('performance_120', 'validation_120')
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def manifest_for(name):
    assert name in APPLICATIONS + FORMAL_APPLICATIONS
    if name in FORMAL_APPLICATIONS:
        return FORMAL_DIR / name / 'manifest.json'
    base = 'tests/bsp_workflow/build' if name in ('hello', 'crc32') else 'tests/cpu_performance_2b/build/measure_20261010_c'
    return ROOT / base / name / 'manifest.json'


def parse_measurement(info, data, *, board=False, elapsed=None):
    if info['kind'] != 'coremark':
        return parse_output(info, data, board=board, elapsed=elapsed)
    prefix, sep, suffix = data.partition(b'PERF2B version=')
    assert sep and b'PERF2B ' not in prefix, 'Missing counter dump'
    text = prefix.decode('ascii')
    assert '\r' not in text
    ticks = re.findall(r'^Total ticks\s*:\s*(\d+)$', text, re.M)
    assert len(ticks) == 1
    ticks = int(ticks[0])
    assert 0 < ticks < 2**32
    seconds = ticks // HZ
    mode, iterations = info['mode'], info['iterations']
    # Derive the exact print format from the frozen references. core_main.c
    # prints the duration error for every run below 10 seconds, including 60.
    reference = (FORMAL_DIR / f'{mode}_120/reference.txt' if iterations == 120 else
                 ROOT / f'tools/uart_loader/candidates/bsp_workflow/references/{mode}_{iterations}.txt')
    lines = reference.read_text().splitlines()
    lines = [s for s in lines if not s.startswith('Iterations/Sec') and
             s not in (TIME_ERROR, 'Errors detected') and not s.startswith('Correct operation validated.')]
    expected = []
    for line in lines:
        if line.startswith('Total ticks'):
            line = re.sub(r'\d+$', str(ticks), line)
        elif line.startswith('Total time (secs)'):
            line = re.sub(r'\d+$', str(seconds), line)
            expected.append(line)
            if seconds:
                expected.append(f'Iterations/Sec   : {iterations // seconds}')
            if seconds < 10:
                expected.append(TIME_ERROR)
            continue
        elif line.startswith('PORT_DONE'):
            expected.append('Errors detected' if seconds < 10 else
                            'Correct operation validated. See README.md for run and reporting rules.')
            line = f'PORT_DONE ticks={ticks} iterations={iterations} hz={HZ}'
        expected.append(line)
    assert text == '\n'.join(expected) + '\n', 'CRC/output mismatch, missing or unexpected lines'
    counter_lines = (sep + suffix).decode('ascii').replace('\r\n', '\n').splitlines()
    assert len(counter_lines) == 15 and counter_lines[-1] == 'PERF2B_DONE'
    header = re.fullmatch(r'PERF2B version=1 state=3 start=(\d+) stop=(\d+)', counter_lines[0])
    assert header
    start, stop = map(int, header.groups())
    counts = {}
    for name, line in zip(NAMES, counter_lines[1:-1]):
        value = re.fullmatch(r'PERF2B ' + name + r'=([0-9a-fA-F]{16})', line)
        assert value, 'Malformed counter: ' + name
        counts[name] = int(value[1], 16)
    assert ((stop - start) & 0xffffffff) == ticks == counts['cycles']
    assert sum(counts[n] for n in NAMES[2:9]) == ticks
    assert counts['ddr_transactions'] == counts['ddr_ar_commands'] + counts['ddr_aw_commands']
    assert 0 < counts['instret'] <= ticks
    if board:
        assert elapsed is not None and 0 < elapsed < 40
        assert elapsed + .5 >= ticks / HZ
        # Correct fixed120 runs below 10 s remain comparisons. The formal
        # status below still requires >=10 s; CRC/transport/counters stay strict.
    formal = bool(board and iterations in (60, 120) and seconds >= 10)
    crcfinal = re.search(r'^\[0\]crcfinal\s*:\s*0x([0-9a-f]{4})$', text, re.M)[1]
    result = dict(status='COREMARK_FORMAL_BOARD_PASS' if formal else 'COREMARK_FIXED_BIN_MEASUREMENT_PASS',
                mode=mode, iterations=iterations, ticks=ticks, seconds=ticks / HZ,
                clock_hz=HZ, crcfinal=crcfinal, formal_benchmark=formal,
                duration_requirement_met=seconds >= 10, counters=counts,
                cpi=counts['cycles'] / counts['instret'], timer_start=start, timer_stop=stop,
                origin='ACTUAL_SERIAL' if board else 'OFFLINE_FIXTURE')
    if iterations == 120:
        result['iterations_per_second'] = iterations * HZ / ticks
    return result


# Reuse the successful stop-and-wait transport without modifying its frozen
# source. Wait for the counter tail after PORT_DONE before declaring completion.
code = inspect.getsource(upload.execute)
old = "b'PORT_DONE ticks=' in output and output.endswith(b'\\n')"
assert code.count(old) == 1
code = code.replace(old, "output.endswith(b'PERF2B_DONE\\n')", 1)
namespace = dict(upload.__dict__, parse_output=parse_measurement)
exec(compile(code, '<measurement_transport>', 'exec'), namespace)
execute = namespace['execute']


def verify_record(raw):
    assert raw['status'] == 'MEASUREMENT_APPLICATION_BOARD_PASS'
    assert raw['evidence_origin'] == 'ACTUAL_SERIAL' and raw['serial_opened']
    assert raw['user_KEY0_confirmation'] and raw['retry_count'] == 0 and raw['no_automatic_retry']
    manifest = manifest_for(raw['application_name'])
    info = require_manifest(manifest)
    assert raw['manifest_sha256'] == sha(manifest) and raw['application_info'] == info
    rows = make_plan(info)
    assert len(rows) == len(raw['records'])
    for planned, row in zip(rows, raw['records']):
        assert row['result'] == 'PASS' and row['extra_rx_hex'] == ''
        assert row['written_bytes'] == len(bytes.fromhex(planned['tx_hex']))
        assert all(row[k] == v for k, v in planned.items())
        assert row['decoded'] == rvld.decode(bytes.fromhex(row['rx_hex']), bytes.fromhex(planned['expected_hex']))
    app = raw['application']
    assert app['result'] == 'PASS' and app['extra_rx_hex'] == ''
    parsed = parse_measurement(info, bytes.fromhex(app['rx_hex']), board=True, elapsed=app['seconds'])
    assert app['parsed'] == parsed
    return dict(status='MEASUREMENT_LOG_VERIFIED', application_name=raw['application_name'],
                responses=len(rows), run_count=sum(bool(r.get('run')) for r in rows),
                application=parsed, bitstream_local_file=raw['bitstream_local_file'],
                FPGA_programming_independently_observed=False, deployment_gate_required=False)


def verify(path):
    return verify_record(json.loads(Path(path).read_text()))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--application', choices=APPLICATIONS + FORMAL_APPLICATIONS)
    p.add_argument('--port', default='COM11')
    p.add_argument('--log', type=Path)
    p.add_argument('--plan-only', action='store_true')
    p.add_argument('--verify-log', type=Path)
    p.add_argument('--output', type=Path)
    p.add_argument('--bitstream', type=Path, default=ROOT / 'generate_bitstream/board_top.sbit')
    a = p.parse_args()
    if a.verify_log:
        assert a.output and not a.output.exists() and not a.application
        result = verify(a.verify_log)
        a.output.parent.mkdir(parents=True, exist_ok=True)
        with a.output.open('x') as f:
            json.dump(result, f, indent=2)
        print('RESULT: PASS offline log verification; serial not opened')
        return
    assert a.application and a.log and not a.log.exists(), 'Choose application and a new log path'
    manifest = manifest_for(a.application)
    info = require_manifest(manifest)
    rows = make_plan(info)
    bit = a.bitstream.resolve()
    # A local file hash is metadata, not proof of what is programmed in FPGA.
    bit_info = dict(path=bit.as_posix(), sha256=sha(bit) if bit.is_file() else None,
                    identity_scope='LOCAL_FILE_ONLY_NOT_OBSERVED_FPGA')
    result = dict(status='MEASUREMENT_PLAN_ONLY' if a.plan_only else 'RUNNING',
                  evidence_origin='OFFLINE_PLAN_NOT_BOARD' if a.plan_only else 'ACTUAL_SERIAL',
                  application_name=a.application, application_info=info,
                  manifest_path=manifest.as_posix(), manifest_sha256=sha(manifest),
                  bitstream_local_file=bit_info, deployment_gate_required=False,
                  port=a.port, baud=115200, retry_count=0, no_automatic_retry=True,
                  serial_opened=False, FPGA_programming_independently_observed=False,
                  records=[], application={})
    a.log.parent.mkdir(parents=True, exist_ok=True)
    if a.plan_only:
        result['plan'] = rows
        with a.log.open('x') as f:
            json.dump(result, f, indent=2)
        print('RESULT: PASS offline plan;', len(rows), 'responses; RUN=1; serial not opened')
        return
    with a.log.open('x') as f:
        json.dump(result, f, indent=2)
    print('Application:', a.application, 'BIN:', ROOT / info['bin_path'])
    print('先下载你生成的FPGA位流。关闭串口助手；按KEY0并释放，等待DDR就绪。')
    try:
        input('准备好后按Enter开始UART下载（运行期间不要复位）：')
        result['user_KEY0_confirmation'] = True
        import serial
        with serial.Serial(a.port, 115200, bytesize=8, parity='N', stopbits=1, timeout=.05,
                          write_timeout=2, xonxoff=False, rtscts=False, dsrdtr=False) as port:
            result['serial_opened'] = True
            time.sleep(.25)
            execute(port, info, result['records'], result['application'], board=True)
        result['status'] = 'MEASUREMENT_APPLICATION_BOARD_PASS'
        print(bytes.fromhex(result['application']['rx_hex']).decode('ascii'), end='')
        verified = verify_record(result)
        parsed = verified['application']
        if info['kind'] == 'coremark':
            print(f"MEASURE cycles={parsed['ticks']} instret={parsed['counters']['instret']} "
                  f"CPI={parsed['cpi']:.6f} seconds={parsed['seconds']:.9f} formal={parsed['formal_benchmark']}")
        print('RESULT: PASS measurement application')
    except BaseException as error:
        result.update(status='FAIL', error=str(error))
        raise
    finally:
        a.log.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
