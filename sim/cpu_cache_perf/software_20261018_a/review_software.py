"""Offline software/output-format audit only; synthetic extensions are NOT board evidence."""
from pathlib import Path
import json
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT/'tests/cpu_performance_2b'))
from perf27_software import DEFAULT_TAG, CACHE_NAMES, DIAG_NAMES, require_manifest, parse_measurement, sha

def main():
    assert not (HERE/'review.json').exists(), 'Preserve audit evidence'
    build = ROOT/'tests/cpu_performance_2b/build'/DEFAULT_TAG
    report = json.loads((build/'build_review.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/n) == h for n,h in report['protected_sha256'].items())
    results = {}
    for app in ['performance_300', 'validation_300']:
        info = require_manifest(build/app/'manifest.json')
        oldpath = ROOT/f'sim/cpu_ex_redirect/board/task039_target_fetch_300_01/{app}.json'
        old = json.loads(oldpath.read_text(encoding='utf-8'))
        raw = bytes.fromhex(old['application']['rx_hex'])
        assert raw.endswith(b'PERF2B_DONE\n')
        values = dict(zip(CACHE_NAMES+DIAG_NAMES,
            [1000,950,50,400,300,100,200,300,10,20,5,1000,1,2]))
        def fixture(cs=15, ds=11, counts=values):
            extra = ['PERF27 version=1 count=27 clock_hz=93750000',
                f'PERF27 cache_id=43414301 cache_status={cs:08x} cache_count=6 diag_id=44494101 diag_status={ds:08x} diag_count=8']
            extra += [f'PERF27 {n}={counts[n]:016x}' for n in CACHE_NAMES+DIAG_NAMES]
            for label,h,m,mask in [('icache_hit_rate_bp','icache_hits','icache_misses',3),
                                   ('dcache_read_hit_rate_bp','dcache_read_hits','dcache_read_misses',5)]:
                total = counts[h]+counts[m]
                bp = str(counts[h]*10000//total) if cs & mask == mask and total else 'NA'
                extra.append(f'PERF27 {label}={bp}')
            extra += ['PERF27_DONE','PERF2B_DONE']
            return raw[:-len(b'PERF2B_DONE\n')] + ('\n'.join(extra)+'\n').encode('ascii')
        valid = fixture()
        parsed = parse_measurement(info, valid)
        assert len(parsed['counters']) == 27
        assert parsed['cache_hit_rates_basis_points'] == {'icache_hit_rate_bp':9500, 'dcache_read_hit_rate_bp':7500}
        # Explicitly synthetic format fixtures, never relabelled as actual UART.
        (HERE/(app+'_OFFLINE_SYNTHETIC.txt')).write_bytes(valid)
        zero = {n:0 for n in values}
        disabled = parse_measurement(info, fixture(8,8,zero))
        assert all(v is None for v in disabled['cache_hit_rates_basis_points'].values())
        empty = parse_measurement(info, fixture(15,11,zero))
        assert all(v is None for v in empty['cache_hit_rates_basis_points'].values())
        negative = {
            'old_13_only':raw,
            'wrong_rate':valid.replace(b'icache_hit_rate_bp=9500',b'icache_hit_rate_bp=9499'),
            'not_ready':valid.replace(b'cache_status=0000000f',b'cache_status=00000007'),
            'tail_pending':valid.replace(b'diag_status=0000000b',b'diag_status=0000001b'),
            'missing_counter':valid.replace(b'PERF27 target_response_match=0000000000000002\n',b''),
            'unbalanced_cache':fixture(counts=dict(values,icache_misses=51)),
            'wrong_metadata':valid.replace(b'diag_count=8',b'diag_count=7'),
            'truncated_tail':valid[:-len(b'PERF2B_DONE\n')],
            'duplicate_tail':valid+b'PERF2B_DONE\n',
            'failed_reader':valid.replace(b'PERF27_DONE\n',b'PERF27_FAILED code=3\n'),
            'wrong_clock':valid.replace(b'clock_hz=93750000',b'clock_hz=125000000'),
            'other_cross_too_large':fixture(counts=dict(values,other_with_retire_cycles=parsed['counters']['other_cycles']+1)),
            'too_many_target_matches':fixture(counts=dict(values,target_response_match=parsed['counters']['branch_redirects'])),
        }
        for name, data in negative.items():
            try: parse_measurement(info, data)
            except (AssertionError, ValueError, UnicodeError): pass
            else: raise AssertionError('Accepted invalid fixture: '+name)
        results[app] = dict(bin_sha256=info['bin_sha256'], bytes=info['bytes'],
            original_UART_source=str(oldpath.relative_to(ROOT)), original_UART_sha256=sha(oldpath),
            synthetic_fixture=app+'_OFFLINE_SYNTHETIC.txt', synthetic_sha256=sha(HERE/(app+'_OFFLINE_SYNTHETIC.txt')),
            positive_format_cases=['enabled','disabled','zero_denominator'], rejected_format_cases=list(negative),
            counters=27, actual_new_CPU_or_board_execution=False)
    output = dict(status='PERF27_SOFTWARE_BUILD_AND_OFFLINE_FORMAT_AUDIT_PASS',
        fixture_origin='HISTORICAL_UART_PREFIX_PLUS_SYNTHETIC_EXTENSION_NOT_NEW_BOARD_EVIDENCE',
        results=results, hardware_counters_not_dynamically_verified=True,
        dynamic_simulation='NOT_RUN', PDS='NOT_RUN', serial_opened=False,
        source_sha256={str(p.relative_to(ROOT).as_posix()):sha(p) for p in
            [Path(__file__), ROOT/'tests/cpu_performance_2b/perf27.c',
             ROOT/'tests/cpu_performance_2b/build_perf27.py', ROOT/'tests/cpu_performance_2b/perf27_software.py',
             ROOT/'tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py',
             ROOT/'tools/uart_loader/candidates/perf_2b/run_perf27_measurements.ps1']})
    (HERE/'review.json').write_text(json.dumps(output, indent=2)+'\n',encoding='utf-8')
    print(output['status'], '; two modes; 3 positive + 13 rejected fixtures each; NOT board evidence')
if __name__ == '__main__': main()
