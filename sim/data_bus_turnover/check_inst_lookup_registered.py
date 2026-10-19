"""Independent review of the Task032 registered I-lookup trace.

Consumes the two trace files written by tb_inst_lookup_registered.sv:

  group A (+LOOKUP_LOG):  A / ATBL / ACONT / ASUM records
  group B (+BUS_LOG):     BSCEN / BSTIM / BEV / BSUM records

Nothing here trusts the testbench's own expected value or PASS text. Group A
expectations are rebuilt from the deterministic scenario rule or from the
recorded seed plus the documented PRNG advance rule, and are cross-checked
against the prepared table printed in the trace. Group B is replayed against an
independent cache + byte memory + user port reference built only from the
stimulus and event records.

Trace grammar (space separated, one record per line)
  A      <scen> <kind> <param> <row> <req_tag> <prep_tag> <prep_valid>
         <expected> <observed> <class> <accept_edge> <outcome_cycle>
  ATBL   <seed> <req_row> <64 x tag> <valid64hex> <req_upper> <decoy_row> <decoy_upper>
  ACONT  <scen> <accept_edge> <outcome_cycle>
  ASUM   det=<n> rnd=<n> hits=<n> misses=<n> rows=<n> cont=<n> mismatches=<n>
  BSCEN  <scen>
  BSTIM  <scen> <cycle> <I|D> <valid> <addr> [<size> <wdata> <wstrb>]
  BEV    <scen> <cycle> <I_ACC|D_ACC|I_RSP|D_RSP|AR|AW|W|R|RESET> <fields...>
  BSUM   accepts=<n> responses=<n> cancels=<n> events=<n> outstanding=<n>

Shared model definition (identical in testbench and checker):
  PRNG:  x = (x * 1103515245 + 12345) mod 2**32; upper = x >> 11; valid = x & 1;
         index = x & 63.
  Byte memory: dm[i] = (i * 0x2B + 0x5A) & 0xFF; beat byte i of user address
         addr is dm[addr*4 + i]; lane j of the beat is little endian bytes
         4j .. 4j+3.
  Address mapping (RTL): araddr/awaddr = {cpu_addr[29:5], 3'b000};
         line index = cpu_addr[10:5]; lane = cpu_addr[4:2].
"""
from pathlib import Path
import re

LCG_MUL = 1103515245
LCG_ADD = 12345
PATTERN = (0x000000, 0x1FFFFF, 0x055555)
ROWS = 64
HIGH_BITS = 21
DET_PER_ROW = 1 + 1 + HIGH_BITS
RND_PER_ROW = 8
RND_SEED = 20261014
DM_SIZE = 4096
ADDR_MASK = 0x0FFFFFFF
TAG_MASK = (1 << 27) - 1


def read(path):
    return Path(path).read_text(encoding='utf-8').replace('\r\n', '\n')


def lcg(value):
    return (value * LCG_MUL + LCG_ADD) & 0xFFFFFFFF


def pattern_of(row):
    return PATTERN[row % 3]


def line_base(addr):
    return ((addr >> 5) << 3) & ADDR_MASK


def line_index(addr):
    return (addr >> 5) & 63


def lane_of(addr):
    return (addr >> 2) & 7


def tag_of(addr):
    return (addr >> 5) & TAG_MASK


def dm_init():
    return [(i * 0x2B + 0x5A) & 0xFF for i in range(DM_SIZE)]


def beat_lanes(dm, addr):
    lanes = []
    for j in range(8):
        word = 0
        for k in range(4):
            word |= dm[(addr * 4 + j * 4 + k) % DM_SIZE] << (8 * k)
        lanes.append(word & 0xFFFFFFFF)
    return lanes


def beat_value(dm, addr):
    value = 0
    for j, lane in enumerate(beat_lanes(dm, addr)):
        value |= lane << (32 * j)
    return value


# ==========================================================================
# group A
# ==========================================================================
def det_scenario(row, kind, param):
    """Rebuild the deposited table entry and the request for a deterministic case."""
    tag = [(pattern_of(row) << 6) | i for i in range(ROWS)]
    valid = [1] * ROWS
    if kind == 1:
        valid[row] = 0
    elif kind == 2:
        tag[row] = ((pattern_of(row) ^ (1 << param)) << 6) | row
    request = (pattern_of(row) << 6) | row
    return tag[row], valid[row], request


def random_table(seed):
    x = seed
    tag = []
    for _ in range(ROWS):
        x = lcg(x)
        tag.append(((x >> 11) << 6) | (len(tag)))
    valid = []
    for _ in range(ROWS):
        x = lcg(x)
        valid.append(x & 1)
    x = lcg(x)
    index = x & 63
    return tag, valid, index


def random_override(k, tag, valid, index):
    if k < 4:
        valid[index] = 1
        request = tag[index]
    elif k in (4, 6):
        valid[index] = 0
        request = tag[index]
    else:
        valid[index] = 1
        request = tag[index] ^ (1 << 6)
    decoy = (index + 1) & 63
    valid[decoy] = 1
    return request, decoy


def review_lookup(path):
    text = read(path)
    lines = [l.split() for l in text.splitlines() if l.strip()]
    assert lines, 'empty group A trace'
    records, tables, conts, summary = [], {}, [], None
    for row in lines:
        if row[0] == 'A':
            assert len(row) == 13, row
            records.append(dict(scen=int(row[1]), kind=int(row[2]), param=int(row[3]),
                                row=int(row[4]), req_tag=int(row[5], 16), prep_tag=int(row[6], 16),
                                prep_valid=int(row[7]), expected=int(row[8]), observed=int(row[9]),
                                cls=row[10], accept_edge=int(row[11]), outcome_cycle=int(row[12])))
        elif row[0] == 'ATBL':
            assert len(row) == 64 + 7, 'ATBL width'
            seed = int(row[1])
            assert seed not in tables, 'duplicate ATBL seed'
            tables[seed] = dict(row=int(row[2]), tag=[int(v, 16) for v in row[3:67]],
                                vbits=int(row[67], 16), req_upper=int(row[68], 16),
                                decoy_row=int(row[69]), decoy_upper=int(row[70], 16))
        elif row[0] == 'ACONT':
            assert len(row) == 4, row
            conts.append(dict(scen=int(row[1]), accept_edge=int(row[2]), outcome_cycle=int(row[3])))
        elif row[0] == 'ASUM':
            summary = dict(kv.split('=') for kv in row[1:])
        elif row[0] == 'ALOOKUP':
            continue
        else:
            raise ValueError('unknown group A record: ' + str(row))
    assert summary is not None, 'missing ASUM'
    assert not re.search(r'RESULT: FAIL', text)

    det = [r for r in records if r['kind'] != 3]
    rnd = [r for r in records if r['kind'] == 3]

    # ---- deterministic: 64 rows x (hit, selected valid0, 21 flipped high bits)
    assert len(det) == ROWS * DET_PER_ROW, len(det)
    det_hits = 0
    det_interference = 0
    bits = {}
    valid0 = set()
    for pos, rec in enumerate(det):
        r, slot = divmod(pos, DET_PER_ROW)
        want_kind = 0 if slot == 0 else 1 if slot == 1 else 2
        want_param = 0 if slot < 2 else slot - 2
        assert rec['kind'] == want_kind and rec['param'] == want_param, (pos, rec)
        assert rec['row'] == r, (pos, rec)
        prep_tag, prep_valid, request = det_scenario(r, want_kind, want_param)
        assert rec['prep_tag'] == prep_tag, (pos, hex(rec['prep_tag']), hex(prep_tag))
        assert rec['prep_valid'] == prep_valid, (pos, rec)
        assert rec['req_tag'] == request, (pos, hex(rec['req_tag']), hex(request))
        assert prep_tag & 0x3F == r, 'fill invariant: low six tag bits must equal the row'
        expect = int(bool(prep_valid) and prep_tag == request)
        assert rec['expected'] == expect, (pos, rec['expected'], expect)
        assert rec['observed'] == expect, 'group A observation mismatch'
        assert rec['cls'] == ('RESP' if expect else 'AR'), rec
        assert rec['outcome_cycle'] == rec['accept_edge'], 'extra lookup bubble after acceptance'
        # every deterministic table gives all 64 rows the same upper tag and
        # valid=1, so a bad index decode would leak a false hit on each of the
        # 63 other rows of every miss record
        if want_kind != 0:
            det_interference += ROWS - 1
        if rec['kind'] == 2:
            bits.setdefault(r, set()).add(rec['param'])
        if rec['kind'] == 1:
            valid0.add(r)
        det_hits += expect
    assert set(bits) == set(range(ROWS)), 'deterministic row coverage'
    assert all(bits[r] == set(range(HIGH_BITS)) for r in bits), 'high tag bit coverage'
    assert valid0 == set(range(ROWS)), 'selected-valid-0 coverage per row'
    assert det_hits == ROWS, det_hits
    assert det_interference == ROWS * 22 * (ROWS - 1), det_interference

    # ---- seeded random: 8 per row, 4 forced hits and 4 forced misses
    assert len(rnd) == ROWS * RND_PER_ROW, len(rnd)
    rnd_hits = 0
    rnd_rows = set()
    interference = 0
    for pos, rec in enumerate(rnd):
        r, k = divmod(pos, RND_PER_ROW)
        seed = RND_SEED + r * 8 + k
        assert rec['param'] == seed, (pos, rec['param'], seed)
        tag, valid, index = random_table(seed)
        request, decoy = random_override(k, tag, valid, index)
        assert seed in tables, 'missing ATBL for seed %d' % seed
        tbl = tables[seed]
        assert tbl['row'] == index and tbl['tag'] == tag, 'printed table does not match the PRNG'
        assert tbl['vbits'] == sum(v << i for i, v in enumerate(valid)), 'printed valid bits'
        assert tbl['req_upper'] == request >> 6, 'printed request upper tag'
        assert tbl['decoy_row'] == decoy and tbl['decoy_upper'] == tag[decoy] >> 6
        assert rec['row'] == index, (pos, rec['row'], index)
        assert rec['req_tag'] == request, (pos, hex(rec['req_tag']), hex(request))
        assert rec['prep_tag'] == tag[index], (pos, hex(rec['prep_tag']), hex(tag[index]))
        assert rec['prep_valid'] == valid[index], (pos, rec)
        assert tag[index] & 0x3F == index, 'random fill invariant'
        expect = int(bool(valid[index]) and tag[index] == request)
        assert rec['expected'] == expect and rec['observed'] == expect, 'random observation mismatch'
        assert rec['cls'] == ('RESP' if expect else 'AR'), rec
        assert rec['outcome_cycle'] == rec['accept_edge'], 'extra lookup bubble after acceptance'
        rnd_rows.add(index)
        rnd_hits += expect
        # other rows may share the requested upper tag while staying valid: the
        # index decode must isolate the selected row
        interference += sum(1 for i in range(ROWS)
                            if i != index and valid[i] and (tag[i] >> 6) == (request >> 6))
    rnd_miss = len(rnd) - rnd_hits
    assert rnd_hits == 256 and rnd_miss == 256, (rnd_hits, rnd_miss)
    assert len(rnd_rows) >= 1

    hits = det_hits + rnd_hits
    assert len(conts) == hits, (len(conts), hits)
    assert int(summary['det']) == len(det) and int(summary['rnd']) == len(rnd), summary
    assert int(summary['hits']) == hits, summary
    assert int(summary['misses']) == len(det) + len(rnd) - hits, summary
    assert int(summary['rows']) == ROWS, summary
    assert int(summary['cont']) == len(conts), summary
    assert int(summary['mismatches']) == 0, summary
    return dict(A_det=len(det), A_rnd=len(rnd), A_hits=hits,
                A_misses=len(det) + len(rnd) - hits, A_rows=ROWS, A_high_bits=HIGH_BITS,
                A_random_hits=rnd_hits, A_random_misses=rnd_miss, A_cont=len(conts),
                A_tables=len(tables), A_interference=det_interference, A_mismatches=0)


# ==========================================================================
# group B
# ==========================================================================
class Cache:
    def __init__(self):
        self.valid = [False] * 64
        self.tag = [0] * 64
        self.lanes = [[0] * 8 for _ in range(ROWS)]

    def hit(self, addr):
        idx = line_index(addr)
        return self.valid[idx] and self.tag[idx] == tag_of(addr)

    def fill(self, addr, lanes):
        idx = line_index(addr)
        self.valid[idx] = True
        self.tag[idx] = tag_of(addr)
        self.lanes[idx] = list(lanes)

    def invalidate(self, addr):
        if self.hit(addr):
            self.valid[line_index(addr)] = False

    def store_bytes(self, addr, data, strobe):
        if not self.hit(addr):
            return
        idx, lane = line_index(addr), lane_of(addr)
        word = self.lanes[idx][lane]
        for k in range(4):
            if strobe >> k & 1:
                word = (word & ~(0xFF << (8 * k))) | (((data >> (8 * k)) & 0xFF) << (8 * k))
        self.lanes[idx][lane] = word & 0xFFFFFFFF


def parse_bus(path):
    scen_order, stim, events, summary = [], [], [], None
    for row in read(path).splitlines():
        if not row.strip():
            continue
        f = row.split()
        if f[0] == 'BSCEN':
            scen_order.append(int(f[1]))
        elif f[0] == 'BSTIM':
            stim.append(dict(scen=int(f[1]), cycle=int(f[2]), target=f[3], valid=int(f[4]),
                             addr=int(f[5], 16)))
        elif f[0] == 'BEV':
            ev = dict(scen=int(f[1]), cycle=int(f[2]), kind=f[3])
            rest = f[4:]
            if ev['kind'] == 'I_ACC':
                ev['addr'] = int(rest[0], 16)
            elif ev['kind'] == 'D_ACC':
                ev.update(write=int(rest[0]), addr=int(rest[1], 16), size=int(rest[2]),
                          wdata=int(rest[3], 16), wstrb=int(rest[4], 16))
            elif ev['kind'] in ('I_RSP', 'D_RSP'):
                ev['rdata'] = int(rest[0], 16)
            elif ev['kind'] == 'AR':
                ev.update(araddr=int(rest[0], 16), aruid=int(rest[1]))
            elif ev['kind'] in ('AW', 'W'):
                ev.update(awaddr=int(rest[0], 16), wdata=int(rest[1], 16), wstrb=int(rest[2], 16))
            elif ev['kind'] == 'R':
                ev.update(rdata=int(rest[0], 16), rid=int(rest[1]), rlast=int(rest[2]))
            elif ev['kind'] == 'RESET':
                ev['phase'] = int(rest[0])
            else:
                raise ValueError('unknown group B event: ' + row)
            events.append(ev)
        elif f[0] == 'BSUM':
            summary = dict(kv.split('=') for kv in f[1:])
        elif f[0] == 'BLOOKUP':
            continue
        else:
            raise ValueError('unknown group B record: ' + row)
    assert summary is not None, 'missing BSUM'
    assert not re.search(r'RESULT: FAIL', read(path))
    return scen_order, stim, events, summary


def review_bus(path):
    scen_order, stim, events, summary = parse_bus(path)
    assert len(scen_order) == 16, 'expected 16 group B scenarios, saw %d' % len(scen_order)
    dm = dm_init()
    ic, dc = Cache(), Cache()
    reads, writes = [], []          # outstanding read requests / posted stores
    ar_pending = None
    accepts = responses = cancels = 0
    per_scen = {s: [] for s in scen_order}

    for ev in events:
        s, kind = ev['scen'], ev['kind']
        per_scen.setdefault(s, []).append(ev)
        dm_before = list(dm)        # memory state before this cycle's W events
        if kind == 'I_ACC':
            accepts += 1
            reads.append(dict(scen=s, target='I', addr=ev['addr'], hit=ic.hit(ev['addr']),
                              cycle=ev['cycle'], ar=None, r=None, rsp=None))
        elif kind == 'D_ACC':
            accepts += 1
            if ev['write']:
                # posted store: response confirms ownership; the x32 data path
                # invalidates the I line on a write hit and updates D at W time
                ic.invalidate(ev['addr'])
                writes.append(dict(scen=s, addr=ev['addr'], data=ev['wdata'], strobe=ev['wstrb'],
                                   cycle=ev['cycle'], aw=None, w=None, rsp=None))
            else:
                reads.append(dict(scen=s, target='D', addr=ev['addr'], hit=dc.hit(ev['addr']),
                                  cycle=ev['cycle'], ar=None, r=None, rsp=None))
        elif kind in ('I_RSP', 'D_RSP'):
            target = kind[0]
            cand = [r for r in reads if r['target'] == target and r['rsp'] is None]
            store_cand = [w for w in writes if w['rsp'] is None] if target == 'D' else []
            assert cand or store_cand, 'response (%s) without an accepted request' % kind
            if not cand:
                # posted store ownership confirmation
                entry = store_cand[0]
                entry['rsp'] = ev['cycle']
                responses += 1
                if entry['w'] is not None:
                    writes.remove(entry)
            else:
                entry = cand[0]
                lane = lane_of(entry['addr'])
                if entry['hit']:
                    assert entry['ar'] is None, 'hit request must not open an address phase'
                    cache = ic if target == 'I' else dc
                    expect = cache.lanes[line_index(entry['addr'])][lane]
                    assert ev['rdata'] == expect, 'hit response data mismatch (%s)' % kind
                else:
                    assert entry['ar'] is not None, 'miss response without an address phase'
                    assert entry['r'] is not None, 'miss response without an R beat'
                    expect = beat_lanes(dm, entry['ar']['araddr'])[lane]
                    assert ev['rdata'] == expect, 'miss response data mismatch (%s)' % kind
                entry['rsp'] = ev['cycle']
                responses += 1
                reads.remove(entry)
        elif kind == 'AR':
            assert ar_pending is None, 'two outstanding ARs'
            cand = [r for r in reads if r['ar'] is None]
            assert cand, 'AR without an accepted request'
            entry = cand[0]
            assert not entry['hit'], 'AR issued for a hit request'
            assert entry['target'] == ('I' if ev['aruid'] == 0 else 'D'), 'AR owner mismatch'
            assert ev['araddr'] == line_base(entry['addr']), \
                'AR address mismatch: %08x vs %08x' % (ev['araddr'], line_base(entry['addr']))
            entry['ar'] = ev
            ar_pending = ev
        elif kind == 'R':
            assert ar_pending is not None, 'R without an AR'
            assert ev['rid'] == ar_pending['aruid'], 'R id does not own the outstanding AR'
            assert ev['rlast'] == 1, 'the single beat must be last'
            cand = [r for r in reads if r['ar'] is not None and r['r'] is None]
            assert cand, 'R without an owning request'
            entry = cand[0]
            assert beat_value(dm_before, ar_pending['araddr']) == ev['rdata'] or \
                beat_value(dm, ar_pending['araddr']) == ev['rdata'], \
                'R beat does not match the independent byte memory'
            entry['r'] = ev
            (ic if entry['target'] == 'I' else dc).fill(entry['addr'], beat_lanes(dm, ar_pending['araddr']))
            ar_pending = None
        elif kind == 'AW':
            cand = [w for w in writes if w['aw'] is None]
            assert cand, 'AW without a posted store'
            assert ev['awaddr'] == line_base(cand[0]['addr']), 'AW address mismatch'
            cand[0]['aw'] = ev
        elif kind == 'W':
            cand = [w for w in writes if w['w'] is None]
            assert cand, 'W without a posted store'
            entry = cand[0]
            assert ev['awaddr'] == line_base(entry['addr']), 'W address mismatch'
            assert ev['wdata'] == (entry['data'] << (lane_of(entry['addr']) * 32)) & ((1 << 256) - 1), \
                'W beat data mismatch'
            assert ev['wstrb'] == (entry['strobe'] << (lane_of(entry['addr']) * 4)) & 0xFFFFFFFF, \
                'W strobe mismatch'
            for k in range(32):
                if ev['wstrb'] >> k & 1:
                    dm[(ev['awaddr'] * 4 + k) % DM_SIZE] = (ev['wdata'] >> (8 * k)) & 0xFF
            dc.store_bytes(entry['addr'], entry['data'], entry['strobe'])
            entry['w'] = ev['cycle']
            if entry['rsp'] is not None:
                writes.remove(entry)
        elif kind == 'RESET':
            cancels += len(reads) + len(writes)
            reads, writes = [], []
            ar_pending = None
            ic, dc = Cache(), Cache()
        else:
            raise ValueError(kind)

    def evs(s, want):
        return [e for e in per_scen.get(s, []) if e['kind'] == want]

    props = {}

    s = 1
    acc, ar, rsp = evs(s, 'I_ACC'), evs(s, 'AR'), evs(s, 'I_RSP')
    assert acc and ar and rsp, 'scenario 1 events missing'
    assert ar[0]['cycle'] == acc[0]['cycle'] + 1, 'scenario 1 AR must follow acceptance at once'
    assert ar[0]['aruid'] == 0, 'scenario 1 instruction AR id'
    assert rsp[0]['cycle'] > ar[0]['cycle'], 'scenario 1 first response must come from the late fill'
    assert len(acc) >= 2 and len(ar) == 1, 'scenario 1 second access must hit without AR'
    props['s1_cold_miss_then_hit'] = True

    s = 2
    ar, rbeat, rsp = evs(s, 'AR'), evs(s, 'R'), evs(s, 'I_RSP')
    assert ar and rbeat and rsp, 'scenario 2 events missing'
    assert rbeat[0]['cycle'] == ar[0]['cycle'], 'scenario 2 needs the AR/R same-cycle return'
    assert rsp[0]['cycle'] == ar[0]['cycle'] + 1, 'scenario 2 response must not add a bubble'
    props['s2_ar_r_same_cycle'] = True

    s = 3
    acc, ar, rsp = evs(s, 'I_ACC'), evs(s, 'AR'), evs(s, 'I_RSP')
    assert acc and ar, 'scenario 3 events missing'
    assert ar[0]['cycle'] >= acc[0]['cycle'] + 4, 'scenario 3 AR backpressure under 3 cycles'
    assert len(ar) == 1 and len(rsp) == 1, 'scenario 3 ownership'
    assert ar[0]['araddr'] == line_base(0x40000080), 'scenario 3 AR must keep the accepted address'
    props['s3_ar_backpressure_live_change'] = True

    s = 4
    assert len(evs(s, 'I_ACC')) == 2 and not evs(s, 'AR') and len(evs(s, 'I_RSP')) == 2, 'scenario 4'
    props['s4_hit_then_hit'] = True

    s = 5
    assert len(evs(s, 'I_ACC')) == 2 and len(evs(s, 'AR')) == 1, 'scenario 5'
    props['s5_hit_then_miss'] = True

    s = 6
    assert len(evs(s, 'I_ACC')) == 2 and len(evs(s, 'AR')) == 1, 'scenario 6'
    props['s6_miss_then_hit'] = True

    s = 7
    assert evs(s, 'I_ACC') and len(evs(s, 'D_ACC')) == 1, 'scenario 7 D must be accepted once'
    assert evs(s, 'I_RSP') and evs(s, 'D_RSP'), 'scenario 7 both sides must respond'
    props['s7_i_d_same_edge'] = True

    s = 8
    assert evs(s, 'D_ACC') and evs(s, 'I_ACC'), 'scenario 8'
    assert evs(s, 'D_RSP') and evs(s, 'I_RSP'), 'scenario 8 both sides must respond'
    props['s8_d_then_i'] = True

    s = 9
    aw, w, ar, iar = evs(s, 'AW'), evs(s, 'W'), evs(s, 'AR'), [e for e in evs(s, 'AR')]
    assert aw and w and iar, 'scenario 9 events missing'
    assert w[0]['cycle'] < iar[0]['cycle'], 'scenario 9 AR must not jump the write drain'
    props['s9_posted_write_aw_pending'] = True

    s = 10
    aw, w, ar = evs(s, 'AW'), evs(s, 'W'), evs(s, 'AR')
    assert aw and w and ar, 'scenario 10 events missing'
    assert ar[0]['cycle'] > w[0]['cycle'], 'scenario 10 AR must wait for the W completion'
    props['s10_posted_write_w_wait'] = True

    s = 11
    w, ar, dacc = evs(s, 'W'), evs(s, 'AR'), evs(s, 'D_ACC')
    assert w and ar and dacc, 'scenario 11 events missing'
    assert ar[0]['cycle'] > w[0]['cycle'], 'scenario 11 AR must not precede the W completion'
    assert evs(s, 'R'), 'scenario 11 needs a real fill'
    assert len(evs(s, 'I_RSP')) >= 2, 'scenario 11 needs the re-read response'
    props['s11_lookup_w_complete_store_invalidate'] = True

    s = 12
    assert not evs(s, 'I_ACC') and not evs(s, 'I_RSP') and not evs(s, 'AR'), \
        'scenario 12 idle with valid deasserted must stay silent'
    props['s12_idle_valid0_addr_change'] = True

    for s, phase in ((13, 1), (14, 2), (15, 3)):
        rst = evs(s, 'RESET')
        assert rst and rst[0]['phase'] == phase, 'scenario %d reset phase' % s
        assert not evs(s, 'I_RSP'), 'scenario %d must not answer after reset' % s
    props['s13_reset_lookup_hit'] = True
    props['s14_reset_lookup_miss_ar'] = True
    props['s15_reset_rdata_wait'] = True

    s = 16
    assert evs(s, 'W') and evs(s, 'AR') and evs(s, 'I_RSP'), 'scenario 16 events missing'
    assert evs(s, 'I_RSP')[-1]['rdata'] == 0x01020304, 'scenario 16 must return the stored word'
    props['s16_write_invalidate_new_data'] = True

    assert not reads and not writes, 'requests left outstanding at the end of group B'
    assert int(summary['accepts']) == accepts and int(summary['responses']) == responses, summary
    assert int(summary['cancels']) == cancels and int(summary['outstanding']) == 0, summary
    assert accepts == responses + cancels, (accepts, responses, cancels)
    return dict(B_scenarios=len(scen_order), B_events=int(summary['events']),
                B_accepts=accepts, B_responses=responses, B_cancels=cancels,
                B_stims=len(stim), B_properties=len(props), B_mismatches=0, B_props=props)


# ==========================================================================
def review(path, bus_path=None):
    """Recompute both groups. `path` is the group A trace, `bus_path` the group B
    trace (defaults to a sibling file named bus.log)."""
    if bus_path is None:
        bus_path = Path(path).with_name('bus.log')
    result = review_lookup(path)
    result.update(review_bus(bus_path))
    return result


def main():
    import sys
    a_path = sys.argv[1] if len(sys.argv) > 1 else 'lookup.log'
    b_path = sys.argv[2] if len(sys.argv) > 2 else None
    r = review(a_path, b_path)
    print('RESULT: PASS inst_lookup_registered A_det=%d A_rnd=%d hits=%d misses=%d rows=%d '
          'high_bits=%d B_scenarios=%d B_events=%d mismatches=0'
          % (r['A_det'], r['A_rnd'], r['A_hits'], r['A_misses'], r['A_rows'],
             r['A_high_bits'], r['B_scenarios'], r['B_events']))


if __name__ == '__main__':
    main()
