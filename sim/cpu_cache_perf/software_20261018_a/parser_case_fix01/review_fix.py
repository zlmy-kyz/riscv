"""Recover actual P CRC/counts offline; preserve original FAIL and missing RX-tail check."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT/'tests/cpu_performance_2b'))
from perf27_software import require_manifest, parse_measurement, sha
from zmmul300_software import measurement as legacy

def main():
    assert not (HERE/'review.json').exists(), 'Preserve review evidence'
    rawpath = ROOT/'sim/cpu_cache_perf/board/perf27_300_20261018_124013/performance_300.json'
    idpath = rawpath.with_name('identity.json')
    source = ROOT/'tests/cpu_performance_2b/perf27_software.py'
    rawhash = sha(rawpath)
    ident = json.loads(idpath.read_text(encoding='utf-8'))
    raw = json.loads(rawpath.read_text(encoding='utf-8'))
    before = source.read_bytes().replace(b'[0-9a-fA-F]{8}', b'[0-9a-f]{8}').replace(b'[0-9a-fA-F]{16}', b'[0-9a-f]{16}')
    assert hashlib.sha256(before).hexdigest() == ident['sha256']['tests/cpu_performance_2b/perf27_software.py']
    (HERE/'perf27_software_before.py').write_bytes(before)
    (HERE/'perf27_software_after.py').write_bytes(source.read_bytes())
    (HERE/'parser_case.patch').write_text(''.join(difflib.unified_diff(
        before.decode().splitlines(True), source.read_text().splitlines(True), 'before', 'after')), encoding='utf-8')
    for n,h in ident['sha256'].items():
        if n != 'tests/cpu_performance_2b/perf27_software.py': assert sha(ROOT/n) == h, n
    assert raw['status'] == 'FAIL' and raw['application']['result'] == 'FAIL'
    assert raw['application']['error'] == 'PERF27 extension metadata mismatch'
    assert raw['evidence_origin'] == 'ACTUAL_SERIAL' and raw['serial_opened'] and raw['user_KEY0_confirmation']
    assert raw['no_automatic_retry'] and raw['retry_count'] == 0
    info = require_manifest(raw['manifest_path'])
    assert raw['manifest_sha256'] == sha(Path(raw['manifest_path'])) and raw['application_info'] == info
    plan = legacy.make_plan(info)
    assert len(plan) == len(raw['records']) == 151 and sum(bool(p.get('run')) for p in plan) == 1
    for p,r in zip(plan, raw['records']):
        assert r['result'] == 'PASS' and r['extra_rx_hex'] == ''
        assert all(r[k] == v for k,v in p.items())
        assert r['written_bytes'] == len(bytes.fromhex(p['tx_hex']))
        assert r['decoded'] == legacy.rvld.decode(bytes.fromhex(r['rx_hex']), bytes.fromhex(p['expected_hex']))
    uart = bytes.fromhex(raw['application']['rx_hex'])
    parsed = parse_measurement(info, uart, board=True, elapsed=raw['application']['seconds'])
    def change_case(data, mode):
        def convert(m):
            text = m[0]
            if mode == 'lower': return text.lower()
            return ''.join(c.lower() if i%2 else c.upper() for i,c in enumerate(text))
        return re.sub(r'(?<==)[0-9a-fA-F]{8,16}(?= |$)', convert, data.decode('ascii'), flags=re.M).encode('ascii')
    for case in ['lower','mixed']:
        assert parse_measurement(info, change_case(uart,case), board=True, elapsed=raw['application']['seconds']) == parsed
    bad = {
        'invalid_hex':uart.replace(b'cache_status=0000000F',b'cache_status=0000000G'),
        'short_hex':uart.replace(b'diag_status=0000000B',b'diag_status=000000B'),
        'not_ready':uart.replace(b'cache_status=0000000F',b'cache_status=00000007'),
        'tail_pending':uart.replace(b'diag_status=0000000B',b'diag_status=0000001B'),
        'cache_unbalanced':uart.replace(b'icache_misses=0000000000028385',b'icache_misses=0000000000028386'),
        'incorrect_rate':uart.replace(b'icache_hit_rate_bp=9988',b'icache_hit_rate_bp=9989'),
        'duplicate_tail':uart+b'PERF2B_DONE\n',
        'missing_tail':uart[:-len(b'PERF2B_DONE\n')],
        'old_13_only':uart.partition(b'PERF27 version=')[0]+b'PERF2B_DONE\n',
    }
    for name, fixture in bad.items():
        assert fixture != uart
        try: parse_measurement(info, fixture, board=True, elapsed=raw['application']['seconds'])
        except (AssertionError, ValueError, UnicodeError): pass
        else: raise AssertionError('Accepted invalid input: '+name)
    assert 'extra_rx_hex' not in raw['application'], 'Reassess RX-tail scope if original contains a drain record'
    assert sha(rawpath) == rawhash
    report = dict(status='PERF27_P_ACTUAL_CRC_AND_27_COUNTS_RECOVERED_WITH_DOCUMENTED_RX_TAIL_GAP',
        raw_log=str(rawpath.relative_to(ROOT)), raw_log_sha256=rawhash, raw_log_status_preserved='FAIL',
        identity_sha256=sha(idpath), parser_before_sha256=hashlib.sha256(before).hexdigest(),
        parser_after_sha256=sha(source), software_BIN_RTL_unchanged=True,
        actual_RVLD_responses=151, run_count=1, application=parsed,
        fix='Accept uppercase/lowercase A-F only in the existing exact-width hex fields; all semantic checks retained',
        case_fixtures_passed=['ACTUAL_UPPERCASE','OFFLINE_LOWERCASE','OFFLINE_MIXEDCASE'],
        invalid_fixtures_rejected=list(bad),
        remaining_gap='Original parser raised before post-application 0.1s extra-RX drain. No recorded extra_rx_hex; full original board-tool PASS is not asserted.',
        next_action='Preserve P; validation_300 was not started. Run only V with fixed parser/new directory.',
        PDS_started=False, serial_opened_by_review=False)
    (HERE/'review.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(report['status'])
    print('P cycles',parsed['ticks'],'seconds',parsed['seconds'],'rates',parsed['cache_hit_rates_basis_points'])
if __name__ == '__main__': main()
