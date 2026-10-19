"""Independent 27-counter software/layout/UART audit; frozen P/V300 unchanged."""
from pathlib import Path
import json
import re
from zmmul300_software import audit as audit13, parse_measurement as parse13, FLAGS, sha, ROOT, HERE

DEFAULT_TAG = 'measure_perf27_20261018_a'
CACHE_NAMES = 'icache_requests icache_hits icache_misses dcache_read_requests dcache_read_hits dcache_read_misses'.split()
DIAG_NAMES = ('icache_miss_wait_cycles dcache_read_miss_wait_cycles write_buffer_block_cycles '
              'old_i_block_cycles ex_branch_mem_wait_cycles other_with_retire_cycles '
              'target_buffer_match target_response_match').split()

def audit(elf, binary, kind, mode=None, iterations=None):
    info = audit13(elf, binary, kind, mode, iterations)
    assert info['clock_hz'] == 93_750_000
    ref = HERE/f'build/measure_zmmul300_20261013_a/{mode}_300/reference.txt'
    return dict(info, counter_schema='PERF27_V1', counter_count=27,
                reference_path=ref.relative_to(ROOT).as_posix(), reference_sha256=sha(ref),
                comparison_kind='NEW_PERF27_BIN_NOT_THE_FROZEN_P300_V300_BIN')

def require_manifest(path):
    path = Path(path)
    info = json.loads(path.read_text(encoding='utf-8'))
    assert info['counter_schema'] == 'PERF27_V1' and info['counter_count'] == 27
    assert sha(ROOT/info['bin_path']) == info['bin_sha256']
    assert sha(ROOT/info['elf_path']) == info['elf_sha256']
    assert audit(ROOT/info['elf_path'], ROOT/info['bin_path'], info['kind'], info['mode'], info['iterations']) == info
    receipt = json.loads(path.with_name('build_receipt.json').read_text(encoding='utf-8'))
    assert receipt['info'] == info
    assert all(sha(ROOT/n) == h for n,h in receipt['source_sha256'].items()), 'Compiled software source changed; use a new build tag'
    return info

def parse_measurement(info, data, *, board=False, elapsed=None):
    assert info['counter_schema'] == 'PERF27_V1' and info['counter_count'] == 27
    assert info['clock_hz'] == 93_750_000 and info['compiler_flags'] == FLAGS
    assert sha(ROOT/info['reference_path']) == info['reference_sha256']
    prefix, sep, tail = data.partition(b'PERF27 version=')
    assert sep and b'PERF27' not in prefix, 'Missing/failed PERF27 dump; old 13-counter output is not accepted'
    lines = (sep+tail).decode('ascii').splitlines()
    assert b'\r' not in data and len(lines) == 20
    assert lines[0] == 'PERF27 version=1 count=27 clock_hz=93750000'
    assert lines[-2:] == ['PERF27_DONE', 'PERF2B_DONE']
    meta = re.fullmatch(r'PERF27 cache_id=43414301 cache_status=([0-9a-f]{8}) cache_count=6 '
                        r'diag_id=44494101 diag_status=([0-9a-f]{8}) diag_count=8', lines[1])
    assert meta, 'PERF27 extension metadata mismatch'
    cs, ds = (int(s,16) for s in meta.groups())
    assert cs & 8 and ds & 8 and not cs & ~15 and not ds & ~11, 'Not a stable frozen snapshot'
    result = parse13(info, prefix+b'PERF2B_DONE\n', board=board, elapsed=elapsed)
    counts = dict(result['counters'])
    for name, line in zip(CACHE_NAMES+DIAG_NAMES, lines[2:16]):
        value = re.fullmatch(r'PERF27 '+name+r'=([0-9a-f]{16})', line)
        assert value, 'Missing/duplicate/out-of-order extension counter: '+name
        counts[name] = int(value[1],16)
        assert counts[name] <= counts['cycles'], name
    assert counts['icache_requests'] == counts['icache_hits'] + counts['icache_misses']
    assert counts['dcache_read_requests'] == counts['dcache_read_hits'] + counts['dcache_read_misses']
    if not cs & 1: assert not cs & 6
    if cs & 3 != 3: assert all(counts[n] == 0 for n in CACHE_NAMES[:3]) and counts[DIAG_NAMES[0]] == 0
    if cs & 5 != 5: assert all(counts[n] == 0 for n in CACHE_NAMES[3:]) and counts[DIAG_NAMES[1]] == 0
    if not ds & 1: assert not ds & 2 and all(counts[n] == 0 for n in DIAG_NAMES)
    if not ds & 2: assert all(counts[n] == 0 for n in DIAG_NAMES[:3])
    assert counts['other_with_retire_cycles'] <= min(counts['other_cycles'], counts['instret'])
    assert counts['ex_branch_mem_wait_cycles'] <= counts['mem_stall_cycles']
    assert counts['target_buffer_match'] + counts['target_response_match'] <= counts['branch_redirects']
    rates = {}
    for line, label, hits, misses, mask in [
        (lines[16], 'icache_hit_rate_bp', 'icache_hits', 'icache_misses', 3),
        (lines[17], 'dcache_read_hit_rate_bp', 'dcache_read_hits', 'dcache_read_misses', 5)]:
        total = counts[hits] + counts[misses]
        bp = counts[hits]*10000//total if cs & mask == mask and total else None
        assert line == f'PERF27 {label}={bp if bp is not None else "NA"}', 'Incorrect cache rate'
        rates[label] = bp
    return dict(result, status='PERF27_APPLICATION_CRC_AND_COUNTERS_PASS', counters=counts,
                counter_schema='PERF27_V1', counter_count=27, cache_status=cs, diag_status=ds,
                cache_hit_rates_basis_points=rates,
                comparison_kind='NEW_PERF27_BIN_NOT_THE_FROZEN_P300_V300_BIN')
