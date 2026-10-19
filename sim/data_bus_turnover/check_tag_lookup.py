"""Independent review of the Task032 parallel I-tag lookup trace.

The trace is produced by tb_inst_tag_lookup.sv from the real bridge. This checker
never reads a DUT value to build an expectation: it regenerates the deposited tables
either from the documented deterministic rule or from the recorded seed with the same
integer generator the testbench uses, then recomputes every hit from
"request index selects the row; hit requires valid and the full row tag to match".

Checks performed:
  * every record is well formed and every recorded preparation value follows the real
    fill invariant low six tag bits == row index;
  * deterministic groups cover all 64 rows, both patterns, the selected-valid-0 case
    and all 21 upper tag bits per row;
  * random groups replay seed 20261014 (8 per row, 512 records) and their printed
    tables are byte-identical to the regenerated ones;
  * exactly one expectation per record and zero mismatches between expectation and
    the observed DUT hit.
"""
from pathlib import Path
import json
import re

LCG_MUL = 1103515245
LCG_ADD = 12345
PATTERN = (0x000000, 0x1FFFFF, 0x055555)
HIGH_BITS = 21
ROWS = 64
DET_PER_ROW = 1 + 1 + HIGH_BITS
RND_PER_ROW = 8
RND_SEED = 20261014


def read(path):
    return Path(path).read_text(encoding='utf-8').replace('\r\n', '\n')


def lcg(value):
    return (value * LCG_MUL + LCG_ADD) & 0xFFFFFFFF


def pattern_of(row):
    return PATTERN[row % 3]


def random_table(seed):
    """Mirror of the testbench generator."""
    x = seed
    upper = []
    for _ in range(ROWS):
        x = lcg(x)
        upper.append(x >> 11)
    valid = []
    for _ in range(ROWS):
        x = lcg(x)
        valid.append(x & 1)
    x = lcg(x)
    index = x & 0x3F
    x = lcg(x)
    request = x >> 11
    return upper, valid, index, request


def review(path):
    rows = [line.split() for line in read(path).splitlines() if line.strip()]
    assert rows, 'empty look-up trace'
    det, rnd, tbls = [], [], {}
    summary = None
    pending_table = None
    for row in rows:
        if row[0] == 'OBS':
            assert len(row) == 10, row
            record = dict(scenario=int(row[1]), kind=int(row[2]), param=int(row[3]),
                          index=int(row[4]), request=int(row[5], 16), sel_tag=int(row[6], 16),
                          valid=int(row[7]), expected=int(row[8]), observed=int(row[9]))
            if record['kind'] == 3:
                rnd.append(record)
            else:
                det.append(record)
        elif row[0] == 'TBL':
            assert len(row) == 67, 'TBL record width'
            seed = int(row[1])
            upper = [int(v, 16) for v in row[2:66]]
            vbits = int(row[66], 16)
            assert seed not in tbls
            tbls[seed] = (upper, vbits)
        elif row[0] == 'LOOKUP-SUMMARY':
            summary = dict(kv.split('=') for kv in row[1:])
        else:
            raise ValueError('unknown look-up record: ' + str(row))
    assert summary is not None, 'missing LOOKUP-SUMMARY'
    assert not re.search(r'RESULT: FAIL', read(path))

    # ---- deterministic groups -------------------------------------------------
    det_rows, det_bits, det_hit, det_valid0 = set(), {}, 0, set()
    pos = 0
    for r in range(ROWS):
        group = det[pos:pos + DET_PER_ROW]
        assert len(group) == DET_PER_ROW, 'deterministic group truncated'
        pos += DET_PER_ROW
        base = pattern_of(r)
        kinds = [g['kind'] for g in group]
        assert kinds[0] == 0 and kinds[1] == 1 and kinds[2:] == [2] * HIGH_BITS, kinds
        assert [g['param'] for g in group[2:]] == list(range(HIGH_BITS)), 'flip bit order'
        for g in group:
            assert g['index'] == r, 'deterministic index must follow the row'
            assert g['sel_tag'] & 0x3F == r, 'fill invariant low six tag bits'
            assert g['request'] == base, 'deterministic request must use the base pattern'
            if g['kind'] == 1:
                selected_upper, selected_valid = base, 0
            elif g['kind'] == 2:
                selected_upper, selected_valid = base ^ (1 << g['param']), 1
            else:
                assert g['kind'] == 0, g['kind']
                selected_upper, selected_valid = base, 1
            assert g['sel_tag'] >> 6 == selected_upper, (g['sel_tag'] >> 6, selected_upper)
            assert g['valid'] == selected_valid, (g['valid'], selected_valid)
            expect = int(bool(selected_valid) and selected_upper == g['request'])
            assert g['expected'] == expect and g['observed'] == expect, 'deterministic expectation mismatch'
            det_rows.add(r)
            if g['kind'] == 2:
                det_bits.setdefault(r, set()).add(g['param'])
            if g['kind'] == 0:
                det_hit += 1
            if g['kind'] == 1:
                det_valid0.add(r)
    assert pos == len(det), 'trailing deterministic records'
    assert len(det) == ROWS * DET_PER_ROW, len(det)
    assert det_rows == set(range(ROWS)), 'deterministic row coverage'
    assert det_valid0 == set(range(ROWS)), 'selected-valid-0 coverage'
    assert all(det_bits[r] == set(range(HIGH_BITS)) for r in range(ROWS)), 'high tag bit coverage'
    assert det_hit == ROWS, det_hit

    # ---- seeded random groups -------------------------------------------------
    assert len(rnd) == ROWS * RND_PER_ROW, len(rnd)
    rnd_hit = rnd_miss = 0
    seed_pos = 0
    for r in range(ROWS):
        for k in range(RND_PER_ROW):
            seed = RND_SEED + r * 8 + k
            upper, valid, index, request = random_table(seed)
            if k % 2 == 0:
                request = upper[index]
            else:
                request = upper[index] ^ 1
            record = rnd[seed_pos]
            seed_pos += 1
            assert seed in tbls, 'missing TBL record for seed %d' % seed
            printed_upper, printed_vbits = tbls[seed]
            assert printed_upper == upper[:len(printed_upper)], 'regenerated tag table mismatch'
            assert len(printed_upper) == ROWS
            assert printed_vbits == sum(v << i for i, v in enumerate(valid)), 'regenerated valid table mismatch'
            assert record['param'] == seed and record['index'] == index, 'random stimulus replay mismatch'
            assert record['request'] == request, (record['request'], request)
            assert record['sel_tag'] == (upper[index] << 6) | index, 'random selected tag'
            assert record['sel_tag'] & 0x3F == index, 'random fill invariant'
            assert record['valid'] == valid[index], 'random selected valid'
            expect = int(bool(valid[index]) and upper[index] == request)
            assert record['expected'] == expect and record['observed'] == expect, 'random expectation mismatch'
            if expect:
                rnd_hit += 1
            else:
                rnd_miss += 1
    assert seed_pos == len(rnd)

    # ---- reported summary and coverage ---------------------------------------
    assert int(summary['det']) == len(det), summary
    assert int(summary['rnd']) == len(rnd), summary
    assert int(summary['mismatches']) == 0
    assert int(summary['hits']) == det_hit + rnd_hit, summary
    assert int(summary['misses']) == (len(det) - det_hit) + rnd_miss, summary
    assert int(summary['rows']) == ROWS and int(summary['high_bits']) == HIGH_BITS
    assert int(summary['seed']) == RND_SEED
    total_hits = det_hit + rnd_hit
    total = len(det) + len(rnd)
    assert total_hits > 0 and total - total_hits > 0, 'both hit and miss must be covered'
    return dict(det=len(det), rnd=len(rnd), det_rows=len(det_rows), high_bits=HIGH_BITS,
                random_seed=RND_SEED, tables=len(tbls), hits=total_hits,
                misses=total - total_hits, mismatches=0)


def main():
    import sys
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(
        'sim/data_bus_turnover/build/ds_data_bus_tag_lookup_repair_20261014_a/lookup.log')
    result = review(path)
    print('RESULT: PASS tag_lookup det=%d rnd=%d rows=%d high_bits=%d tables=%d hits=%d misses=%d mismatches=%d'
          % (result['det'], result['rnd'], result['det_rows'], result['high_bits'],
             result['tables'], result['hits'], result['misses'], result['mismatches']))


if __name__ == '__main__':
    main()
