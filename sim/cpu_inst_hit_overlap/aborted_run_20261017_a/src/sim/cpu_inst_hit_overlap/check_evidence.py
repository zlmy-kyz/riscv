"""Task033 independent checker.

Recomputes every expected value from the frozen plan, the DDR model's frozen
initial memory and the recorded edge log. It never reads DUT internal state:
the log only carries ports plus a few observation-only fields.

Modes:
  bridge <rundir> <on|off>   verify one bridge job
  soc <rundir>               verify the SoC job (bridge facts + RV32I retires)
  selftest                   synthetic traces that must be rejected
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


class CheckError(Exception):
    pass


def fail(msg):
    raise CheckError(msg)


# ------------------------------------------------------------------ plan/edges
def load_plan(path):
    toks = []
    for line in Path(path).read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w or w[0] != 'TOK':
            continue
        if len(w) != 11:
            fail('plan line malformed: %r' % line)
        toks.append(dict(idx=int(w[1]), kind=w[2], addr=int(w[3], 16), data=int(w[4], 16),
                         strb=int(w[5], 16), size=int(w[6]), wmode=int(w[7]),
                         warg=int(w[8]), grp=int(w[9]), scen=w[10]))
    if not toks:
        fail('empty plan')
    for i, t in enumerate(toks):
        if t['idx'] != i:
            fail('plan index gap at %d' % i)
    return toks


NUMFIELDS = ('rst', 'init', 'iv', 'ir', 'ia', 'dv', 'dr', 'dw', 'sz', 'da', 'dwd', 'ds',
             'ip', 'ie', 'id', 'dp', 'de', 'dd', 'busy', 'arv', 'arr', 'ara', 'ari', 'arl',
             'awv', 'awr', 'awa', 'awi', 'awl', 'wrdy', 'wdv', 'wsv', 'rv', 'rdv', 'rid',
             'rl', 'ep')


def load_edges(path):
    """Returns a list indexed by edge number. Only PRE is used for semantics."""
    pre, post = {}, {}
    for line in Path(path).read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w or w[0] != 'E':
            continue
        d = {}
        for item in w[1:]:
            k, v = item.split('=', 1)
            d[k] = v
        n = int(d['n'])
        (pre if d['ph'] == 'PRE' else post)[n] = d
    if not pre:
        fail('edge log empty')
    missing = [n for n in pre if n not in post]
    if missing:
        fail('edge log has PRE without POST at %d' % missing[0])
    edges = []
    for n in sorted(pre):
        if n != len(edges) + 1:
            fail('edge numbering gap at %d' % n)
        e = {'n': n}
        for k in NUMFIELDS:
            if k not in pre[n]:
                fail('edge %d missing field %s' % (n, k))
            raw = pre[n][k].lower().replace('x', '0').replace('z', '0')
            if k in ('sz', 'ep'):
                e[k] = int(raw)
            elif k in ('ia', 'da', 'dwd', 'ds', 'id', 'dd', 'ara', 'awa', 'wdv', 'wsv', 'rdv'):
                e[k] = int(raw, 16)
            else:
                e[k] = int(raw, 2)
        e['post'] = post[n]
        edges.append(e)
    return edges


# ------------------------------------------------------------------- reference
class Mem:
    def __init__(self, nbeat=8256):
        self.nbeat = nbeat
        seed = 1
        beats = []
        for _ in range(nbeat):
            b = bytearray(32)
            for k in range(32):
                seed = (seed * 1103515245 + 12345) & 0xFFFFFFFF
                b[k] = (seed >> 16) & 0xFF
            beats.append(b)
        self.beats = beats

    @staticmethod
    def beat_of(addr):
        if (addr >> 22) & 0x3FF == 0x004:
            return 0x2000 + ((addr >> 5) & 0x1F)
        if (addr >> 22) & 0x3FF == 0x008:
            return 0x2020 + ((addr >> 5) & 0x1F)
        return (addr >> 5) & (0xFFFFFFFF)

    def word(self, addr):
        b = self.beats[self.beat_of(addr)]
        o = addr & 31
        return int.from_bytes(bytes(b[o:o + 4]), 'little')

    def beat(self, addr):
        return bytes(self.beats[self.beat_of(addr)])

    def write_beat(self, addr, wdata256, wstrb32):
        """x32 user port: 32 byte lanes and a 32-bit byte strobe."""
        b = self.beats[self.beat_of(addr)]
        for k in range(32):
            if (wstrb32 >> k) & 1:
                b[k] = (wdata256 >> (8 * k)) & 0xFF

    def poke(self, addr, data, strb):
        """Model-side external update used by the uncached-region scenario."""
        b = self.beats[self.beat_of(addr)]
        o = addr & 31
        for k in range(4):
            if (strb >> k) & 1:
                b[o + k] = (data >> (8 * k)) & 0xFF


class Cache:
    def __init__(self):
        self.valid = [False] * 64
        self.tag = [0] * 64
        self.data = [[0] * 8 for _ in range(64)]

    def idx(self, addr):
        return (addr >> 5) & 63

    def hit(self, addr):
        i = self.idx(addr)
        return self.valid[i] and self.tag[i] == (addr >> 5)

    def word(self, addr):
        return self.data[self.idx(addr)][(addr >> 2) & 7]

    def fill(self, addr, beat):
        i = self.idx(addr)
        self.valid[i] = True
        self.tag[i] = addr >> 5
        self.data[i] = [int.from_bytes(beat[w * 4:w * 4 + 4], 'little') for w in range(8)]

    def poke_bytes(self, addr, wdata, wstrb):
        i = self.idx(addr)
        o = (addr & 31) & ~3
        w = self.data[i][(addr >> 2) & 7]
        for k in range(4):
            if (wstrb >> k) & 1:
                w = (w & ~(0xFF << (8 * k))) | (((wdata >> (8 * k)) & 0xFF) << (8 * k))
        self.data[i][(addr >> 2) & 7] = w

    def clear(self):
        self.valid = [False] * 64

    def invalidate(self, addr):
        i = self.idx(addr)
        if self.valid[i] and self.tag[i] == (addr >> 5):
            self.valid[i] = False


def is_camera(addr):
    return (addr >> 22) == 0x004


def is_pp(addr):
    return (addr >> 22) == 0x008


# --------------------------------------------------------------------- replay
class Pending:
    __slots__ = ('tok', 'side', 'kind', 'data', 'accept', 'r_edge', 'line')

    def __init__(self, tok, side, kind, data, accept, line):
        self.tok = tok
        self.side = side
        self.kind = kind          # 'hit' / 'miss' / 'store'
        self.data = data
        self.accept = accept
        self.r_edge = None
        self.line = line


def load_pokes(path):
    """Model-side updates recorded by the TB. A poke driven on the negedge after
    edge k is visible to the DUT from edge k+1, so it is applied there."""
    pokes = {}
    p = Path(path)
    if not p.exists():
        fail('token log missing: %s' % p)
    for line in p.read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w or w[0] != 'M':
            continue
        d = dict(item.split('=', 1) for item in w[2:])
        edge = int(d['edge']) + 1
        pokes.setdefault(edge, []).append((int(d['addr'], 16), int(d['data'], 16),
                                           int(d['strb'], 16)))
    return pokes


def replay(plan, edges, mem, extra=None, pokes=None):
    icache, dcache = Cache(), Cache()
    wb = None                      # pending posted store entry
    pend_i, pend_d = [], []
    read_inflight = 0
    read_tok = None
    ar_hold = None
    aw_hold = None
    i_tokens = [t for t in plan if t['kind'] == 'I']
    d_tokens = [t for t in plan if t['kind'] in ('D', 'W')]
    ci = cd = 0
    resp_edge = {}
    accept_edge = {}
    cancels = []
    ar_log = []
    aw_log = []
    w_log = []
    facts = {}
    epoch = 0
    stats = dict(accepts=0, responses=0, cancels=0, ar=0, aw=0, w=0, mem_writes=0,
                 reset_edge_rsp=0, pokes=0)
    pending_misses = []

    for e in edges:
        n = e['n']
        epoch = e['ep']
        # ---------------- model-side updates ----------------
        for (pa, pd, ps) in (pokes or {}).get(n, ()):
            mem.poke(pa, pd, ps)
            stats['pokes'] += 1
        # ---------------- reset / init ----------------
        # A reset edge cancels the whole pipeline. The reset in this plan is
        # applied at a negedge, so a response that was already asserted for the
        # interrupted cycle is indeterminate and is recorded, not graded. What
        # IS graded: no request may be accepted on the reset edge, nothing may
        # survive the reset, and no stray response may appear afterwards.
        if e['rst'] == 0 or e['init'] == 0:
            if e['iv'] and e['ir'] or e['dv'] and e['dr']:
                fail('request accepted on a reset edge %d' % n)
            if e['ip'] or e['dp']:
                stats['reset_edge_rsp'] += 1
            for p in pend_i + pend_d:
                cancels.append((n, p.tok['scen'], p.side))
            stats['cancels'] += len(pend_i) + len(pend_d)
            pend_i, pend_d = [], []
            pending_misses = []
            read_inflight = 0
            read_tok = None
            wb = None
            ar_hold = None
            aw_hold = None
            icache.clear()
            dcache.clear()
            continue

        # ---------------- responses ----------------
        if e['ip']:
            if not pend_i:
                fail('I response without outstanding request at edge %d' % n)
            p = pend_i.pop(0)
            if p.kind == 'hit':
                if n != p.accept + 1:
                    fail('I hit response edge %d != accept+1 edge %d (%s)' % (n, p.accept, p.tok['scen']))
                if e['id'] != p.data:
                    fail('I hit data %08x != expected %08x at edge %d (%s)'
                         % (e['id'], p.data, n, p.tok['scen']))
            else:
                if p.r_edge is None or n != p.r_edge + 1:
                    fail('I miss response edge %d != R+1 (%s r=%s)' % (n, p.tok['scen'], p.r_edge))
                if e['id'] != p.data:
                    fail('I miss data %08x != expected %08x at edge %d (%s)'
                         % (e['id'], p.data, n, p.tok['scen']))
            if e['ie'] != 0:
                fail('I response error at edge %d' % n)
            resp_edge[p.tok['idx']] = n
            stats['responses'] += 1
        elif pend_i and pend_i[0].kind == 'hit' and n > pend_i[0].accept + 1:
            fail('I hit response missing after accept edge %d (%s)'
                 % (pend_i[0].accept, pend_i[0].tok['scen']))

        if e['dp']:
            if not pend_d:
                fail('D response without outstanding request at edge %d' % n)
            p = pend_d.pop(0)
            if p.kind == 'store':
                if n not in (p.accept + 1, p.accept + 2):
                    fail('D store ack edge %d out of range (%s)' % (n, p.tok['scen']))
            elif p.kind == 'hit':
                if n != p.accept + 1:
                    fail('D hit response edge %d != accept+1 (%s)' % (n, p.tok['scen']))
                if e['dd'] != p.data:
                    fail('D hit data %08x != expected %08x at edge %d (%s)'
                         % (e['dd'], p.data, n, p.tok['scen']))
            else:
                if p.r_edge is None or n != p.r_edge + 1:
                    fail('D miss response edge %d != R+1 (%s r=%s)' % (n, p.tok['scen'], p.r_edge))
                if e['dd'] != p.data:
                    fail('D miss data %08x != expected %08x at edge %d (%s)'
                         % (e['dd'], p.data, n, p.tok['scen']))
            if e['de'] != 0:
                fail('D response error at edge %d' % n)
            resp_edge[p.tok['idx']] = n
            stats['responses'] += 1
        elif pend_d and pend_d[0].kind in ('hit', 'store') and n > pend_d[0].accept + 2:
            fail('D response missing after accept edge %d (%s)'
                 % (pend_d[0].accept, pend_d[0].tok['scen']))

        # ---------------- DDR read ----------------
        if ar_hold is not None:
            if not e['arv']:
                fail('AR withdrawn before acceptance at edge %d' % n)
            if (e['ara'], e['ari']) != ar_hold:
                fail('AR fields changed under backpressure at edge %d' % n)
            if e['arr']:
                ar_hold = None
        if e['arv'] and not e['arr']:
            ar_hold = (e['ara'], e['ari'])
        if e['arv'] and e['busy']:
            fail('AR asserted while the posted write is draining at edge %d' % n)
        if e['arv'] and e['arr']:
            if e['ara'] & 7:
                fail('AR not 32-byte aligned at edge %d' % n)
            if read_inflight != 0:
                fail('second physical read in flight at edge %d' % n)
            read_inflight = 1
            line = e['ara'] << 2
            cand = [p for p in pending_misses if (p.tok['addr'] >> 5) == (line >> 5)]
            if len(cand) != 1:
                fail('AR %08x matches %d pending misses at edge %d' % (line, len(cand), n))
            read_tok = cand[0]
            read_tok.line = line
            ar_log.append((n, line, read_tok.tok['scen']))
            stats['ar'] += 1
        if e['rv']:
            if read_inflight != 1 or read_tok is None:
                fail('R without an accepted read at edge %d' % n)
            if e['rid'] != (1 if read_tok.side == 'D' else 0):
                fail('R id %d does not match owner %s at edge %d' % (e['rid'], read_tok.side, n))
            if e['rl'] != 1:
                fail('R last not asserted at edge %d' % n)
            beat = mem.beat(read_tok.line)
            got = e['rdv'].to_bytes(32, 'little')
            if got != beat:
                bad = [k for k in range(32) if got[k] != beat[k]]
                fail('R beat mismatch for %s at edge %d (line %08x, bytes %s: got %s want %s)'
                     % (read_tok.tok['scen'], n, read_tok.line, bad[:4],
                        ['%02x' % got[k] for k in bad[:4]],
                        ['%02x' % beat[k] for k in bad[:4]]))
            read_inflight = 0
            lane = (read_tok.tok['addr'] >> 2) & 7
            data = int.from_bytes(beat[lane * 4:lane * 4 + 4], 'little')
            read_tok.r_edge = n
            read_tok.kind = 'miss'
            read_tok.data = data
            if read_tok.side == 'I':
                if not (is_camera(read_tok.line) or is_pp(read_tok.line)):
                    icache.fill(read_tok.line, beat)
            else:
                if not (is_camera(read_tok.line) or is_pp(read_tok.line)):
                    dcache.fill(read_tok.line, beat)
            pending_misses.remove(read_tok)
            read_tok = None

        # ---------------- DDR write ----------------
        if aw_hold is not None:
            if not e['awv']:
                fail('AW withdrawn before acceptance at edge %d' % n)
            if (e['awa'], e['wdv'], e['wsv']) != aw_hold:
                fail('AW/W fields changed under backpressure at edge %d' % n)
            if e['awr']:
                aw_hold = None
        if e['awv'] and not e['awr']:
            aw_hold = (e['awa'], e['wdv'], e['wsv'])
        if e['awv'] and e['awr']:
            if e['awa'] & 7:
                fail('AW not 32-byte aligned at edge %d' % n)
            if e['awl'] != 0:
                fail('AW len != 0 at edge %d' % n)
            aw_log.append(dict(edge=n, addr=e['awa'] << 2, wdata=e['wdv'],
                               wstrb=e['wsv'], done=False))
            stats['aw'] += 1
        if e['wrdy']:
            if not aw_log or aw_log[-1]['done']:
                fail('W without an open AW at edge %d' % n)
            cur = aw_log[-1]
            if cur['wdata'] != e['wdv'] or cur['wstrb'] != e['wsv']:
                fail('W data/strobe differ from the accepted AW at edge %d' % n)
            cur['done'] = True
            if wb is not None:
                # the posted store must land in exactly the bytes the CPU selected
                shift = wb['addr'] & 31
                if cur['addr'] != (wb['addr'] & ~31):
                    fail('store AW %08x is not the line of %08x (%s)'
                         % (cur['addr'], wb['addr'], wb['scen']))
                if cur['wstrb'] != (wb['wstrb'] << shift) & 0xFFFFFFFF:
                    fail('store byte strobe %08x != expected %08x (%s)'
                         % (cur['wstrb'], (wb['wstrb'] << shift) & 0xFFFFFFFF, wb['scen']))
                if cur['wdata'] != (wb['wdata'] << (8 * shift)) & ((1 << 256) - 1):
                    fail('store data lane placement wrong for %s' % wb['scen'])
            mem.write_beat(cur['addr'], cur['wdata'], cur['wstrb'])
            stats['w'] += 1
            stats['mem_writes'] += 1
            if wb is not None:
                if wb['hit'] and dcache.valid[dcache.idx(wb['addr'])] and \
                        dcache.tag[dcache.idx(wb['addr'])] == (wb['addr'] >> 5):
                    dcache.poke_bytes(wb['addr'], wb['wdata'], wb['wstrb'])
                wb = None

        # ---------------- accepts ----------------
        if e['iv'] and e['ir']:
            if ci >= len(i_tokens):
                fail('unexpected I accept at edge %d addr=%08x' % (n, e['ia']))
            t = i_tokens[ci]
            if t['addr'] != e['ia']:
                fail('I accept %08x != plan %08x (%s) at edge %d' % (e['ia'], t['addr'], t['scen'], n))
            ci += 1
            accept_edge[t['idx']] = n
            stats['accepts'] += 1
            if icache.hit(t['addr']):
                p = Pending(t, 'I', 'hit', icache.word(t['addr']), n, t['addr'] & ~31)
            else:
                p = Pending(t, 'I', 'miss', None, n, t['addr'] & ~31)
                pending_misses.append(p)
            pend_i.append(p)

        if e['dv'] and e['dr']:
            if cd >= len(d_tokens):
                fail('unexpected D accept at edge %d addr=%08x' % (n, e['da']))
            t = d_tokens[cd]
            if t['addr'] != e['da']:
                fail('D accept %08x != plan %08x (%s) at edge %d' % (e['da'], t['addr'], t['scen'], n))
            if t['kind'] == 'D' and e['dw']:
                fail('D read token accepted as a write at edge %d' % n)
            if t['kind'] == 'W':
                if not e['dw'] or e['dwd'] != t['data'] or e['ds'] != t['strb']:
                    fail('store fields differ from plan at edge %d (%s)' % (n, t['scen']))
            cd += 1
            accept_edge[t['idx']] = n
            stats['accepts'] += 1
            if t['kind'] == 'W':
                uncached = is_camera(t['addr']) or is_pp(t['addr'])
                hit_line = (not uncached) and dcache.hit(t['addr'])
                wb = dict(addr=t['addr'], lane=(t['addr'] >> 2) & 7, wdata=t['data'],
                          wstrb=t['strb'], hit=hit_line, scen=t['scen'])
                if not uncached and icache.hit(t['addr']):
                    icache.invalidate(t['addr'])
                pend_d.append(Pending(t, 'D', 'store', None, n, t['addr'] & ~31))
            else:
                uncached = is_camera(t['addr']) or is_pp(t['addr'])
                if (not uncached) and dcache.hit(t['addr']):
                    data = dcache.word(t['addr'])
                    if wb is not None and wb['addr'] >> 5 == t['addr'] >> 5 and \
                            wb['lane'] == ((t['addr'] >> 2) & 7):
                        for k in range(4):
                            if (wb['wstrb'] >> k) & 1:
                                data = (data & ~(0xFF << (8 * k))) | \
                                       (((wb['wdata'] >> (8 * k)) & 0xFF) << (8 * k))
                    p = Pending(t, 'D', 'hit', data, n, t['addr'] & ~31)
                else:
                    p = Pending(t, 'D', 'miss', None, n, t['addr'] & ~31)
                    pending_misses.append(p)
                pend_d.append(p)

    if ci != len(i_tokens):
        fail('only %d/%d I tokens accepted' % (ci, len(i_tokens)))
    if cd != len(d_tokens):
        fail('only %d/%d D tokens accepted' % (cd, len(d_tokens)))
    if read_inflight:
        fail('physical read still in flight at the end')
    if pend_i or pend_d:
        fail('outstanding request without response at the end')

    for a in aw_log:
        if not a['done']:
            fail('accepted AW never completed')

    return dict(edges=edges, icache=icache, dcache=dcache, mem=mem, resp=resp_edge,
                accept=accept_edge, ar=ar_log, aw=aw_log, cancels=cancels, stats=stats,
                plan=plan, extra=extra)


# ------------------------------------------------------------- bridge scenarios
def need(summ, scen, what):
    t = next((x for x in summ['plan'] if x['scen'] == scen), None)
    if t is None:
        fail('plan has no token %s' % scen)
    if t['idx'] not in summ['accept']:
        fail('token %s was never accepted' % scen)
    if what == 'resp' and t['idx'] not in summ['resp']:
        fail('token %s has no response' % scen)
    return t


def edge_of(summ, scen):
    t = need(summ, scen, 'resp')
    return summ['accept'][t['idx']], summ['resp'][t['idx']]


def first_ar_after(summ, edge, line=None):
    for (n, ln, scen) in summ['ar']:
        if n >= edge and (line is None or (ln >> 5) == (line >> 5)):
            return n
    return None


def scenario_checks_off(summ):
    """Control job: with INST_HIT_UNDER_DATA_MISS_ENABLE=0 the same plan must
    show the opposite causality - no I request is served while a D miss owns
    the only DDR slot, so every one of them starts after the D response."""
    E = summ['edges']
    A, R = summ['accept'], summ['resp']
    get = lambda scen: next(x for x in summ['plan'] if x['scen'] == scen)
    ev = lambda scen, which: (A if which == 'a' else R)[get(scen)['idx']]

    pairs = [('s1_i_hit_under_ar_stall', 's1_d_miss_ar_backpressure'),
             ('s1b_i_hit_under_r_wait_1', 's1b_d_miss_r_wait'),
             ('s1b_i_hit_under_r_wait_2', 's1b_d_miss_r_wait'),
             ('s2b_i_hit_during_late_r', 's2b_d_late_r'),
             ('s10_i_hit_no_camera_fill', 's10_camera_under_i_hit')]
    pairs += [('s3_i_hit_burst_%d' % k, 's3_d_miss_window') for k in (1, 2, 3, 4)]
    pairs += [('s3_i_miss_parked', 's3_d_miss_window'),
              ('s4_i_miss_parked', 's4_d_miss_window'),
              ('s4b_i_miss_parked', 's4b_d_miss_window'),
              ('s5_i_blocked_at_completion', 's5_d_miss_window')]
    blocked = 0
    for scen_i, scen_d in pairs:
        if scen_i not in [t['scen'] for t in summ['plan']]:
            continue
        ai, rd = ev(scen_i, 'a'), ev(scen_d, 'r')
        if ai < rd:
            fail('off: %s was accepted at %d inside the D miss window that ends at %d'
                 % (scen_i, ai, rd))
        blocked += 1
    # The parallel-hit path must not exist at all: every I miss inside a D
    # window issues its AR only after the D response.
    for scen in ('s3_i_miss_parked', 's4_i_miss_parked', 's4b_i_miss_parked'):
        ap = ev(scen, 'a')
        rd = ev('s3_d_miss_window' if scen.startswith('s3') else
                ('s4_d_miss_window' if scen.startswith('s4_') else 's4b_d_miss_window'), 'r')
        ar = first_ar_after(summ, ap, get(scen)['addr'])
        if ar is None:
            fail('off: %s never issued its AR' % scen)
        if ar < rd:
            fail('off: %s issued its AR inside the D window (%d < %d)' % (scen, ar, rd))
    # No double response edge may exist in the control job.
    for n in range(1, len(E) + 1):
        if E[n - 1]['ip'] and E[n - 1]['dp']:
            fail('off: I and D responses still overlap at edge %d' % n)
    return dict(blocked_pairs=blocked)


def scenario_checks(summ):
    E = summ['edges']
    A, R = summ['accept'], summ['resp']
    get = lambda scen: next(x for x in summ['plan'] if x['scen'] == scen)
    ev = lambda scen, which: (A if which == 'a' else R)[get(scen)['idx']]
    at = lambda n: E[n - 1]

    # S1: I hit accepted inside the D AR-backpressure window, returned before D.
    for scen_i, scen_d in (('s1_i_hit_under_ar_stall', 's1_d_miss_ar_backpressure'),
                           ('s1b_i_hit_under_r_wait_1', 's1b_d_miss_r_wait'),
                           ('s1b_i_hit_under_r_wait_2', 's1b_d_miss_r_wait')):
        ai, ad = ev(scen_i, 'a'), ev(scen_d, 'a')
        ri, rd = ev(scen_i, 'r'), ev(scen_d, 'r')
        if not (ad < ai < rd):
            fail('%s: I accept %d not inside the D miss window [%d,%d]' % (scen_i, ai, ad, rd))
        if not ri < rd:
            fail('%s: I response %d did not precede the D response %d' % (scen_i, ri, rd))
        if scen_i == 's1_i_hit_under_ar_stall' and not (at(ai)['arv'] and not at(ai)['arr']):
            fail('s1: I was not accepted while AR was back-pressured (edge %d)' % ai)
        if scen_i.startswith('s1b'):
            if not (at(ai)['arv'] is not None and at(ai)['rv'] == 0):
                fail('s1b: I was not accepted while the read was outstanding (edge %d)' % ai)
    # S2a: AR and R on the same edge with the I accepted there.
    ai = ev('s2a_i_accept_on_ar_r_edge', 'a')
    if not (at(ai)['arv'] and at(ai)['arr'] and at(ai)['rv']):
        fail('s2a: I accept edge %d is not an AR/R edge' % ai)
    if ev('s2a_i_accept_on_ar_r_edge', 'r') != ev('s2a_d_ar_r_same_edge', 'r'):
        fail('s2a: expected the D/I double response on one edge')
    # S2c: R bus edge equals the old I hit consumption edge.
    ai = ev('s2c_i_rsp_on_r_edge', 'r')
    if not at(ai)['rv']:
        fail('s2c: I response edge %d is not an R edge' % ai)
    rd = ev('s2c_d_r_on_i_rsp_edge', 'r')
    if rd != ai + 1:
        fail('s2c: D response %d is not one edge after the R edge %d' % (rd, ai))
    # S2d: I response and D response on the same edge.
    if ev('s2d_i_double_response', 'r') != ev('s2d_d_double_response', 'r'):
        fail('s2d: no double response edge')
    # S3: four I hits accepted inside the D miss window.
    ad, rd = ev('s3_d_miss_window', 'a'), ev('s3_d_miss_window', 'r')
    burst = ['s3_i_hit_burst_1', 's3_i_hit_burst_2', 's3_i_hit_burst_3', 's3_i_hit_burst_4']
    prev = ad
    for s in burst:
        a, r = ev(s, 'a'), ev(s, 'r')
        if not (ad < a < rd):
            fail('%s: hit accepted outside the D miss window' % s)
        if r >= rd:
            fail('%s: hit returned after the D response' % s)
        if a <= prev:
            fail('%s: not consecutive' % s)
        prev = a
    ap = ev('s3_i_miss_parked', 'a')
    if not (ad < ap < rd):
        fail('s3: parked miss not accepted inside the window')
    line = get('s3_i_miss_parked')['addr']
    n_ar = first_ar_after(summ, ap, line)
    if n_ar is not None and n_ar < rd:
        fail('s3: AR for the parked miss issued before the D response (%d < %d)' % (n_ar, rd))
    if n_ar is None:
        fail('s3: parked miss never issued its AR')
    # S4: poisoned live address must not change the parked verdict.
    ap = ev('s4_i_miss_parked', 'a')
    ad, rd = ev('s4_d_miss_window', 'a'), ev('s4_d_miss_window', 'r')
    n_ar = first_ar_after(summ, ap, get('s4_i_miss_parked')['addr'])
    if n_ar is not None and n_ar < rd:
        fail('s4: parked AR issued inside the D window')
    if n_ar is None or (E[n_ar - 1]['ara'] << 2) >> 5 != get('s4_i_miss_parked')['addr'] >> 5:
        fail('s4: parked miss resolved to a poisoned live address')
    if ev('s4_parked_line_hit_after_fill', 'r') < rd:
        fail('s4: post-fill hit completed before the promoted fill')
    # two new D requests are accepted before the promoted AR
    ar_prom = first_ar_after(summ, rd, get('s4_i_miss_parked')['addr'])
    if not (A[get('s4_new_d_1')['idx']] < ar_prom and A[get('s4_new_d_2')['idx']] < ar_prom):
        fail('s4: the parked miss was promoted before the two new D requests')
    # S4b: earliest promotion with no competition.
    rd = ev('s4b_d_miss_window', 'r')
    ar = first_ar_after(summ, rd, get('s4b_i_miss_parked')['addr'])
    if ar is None or ar > rd + 2:
        fail('s4b: promotion AR %s is not the earliest edge after %d' % (ar, rd))
    # S5: D keeps priority at the completion edge.
    ad = ev('s5_new_d_at_completion', 'a')
    if ad != ev('s5_d_miss_window', 'r'):
        fail('s5: new D was not accepted on the old completion edge')
    ai = ev('s5_i_blocked_at_completion', 'a')
    if ai <= ad:
        fail('s5: I was accepted at or before the D-priority edge')
    # S6: store on the old hit consumption edge; young I blocked there.
    old_r = ev('s6_old_i_hit_before_store', 'r')
    st_a = ev('s6_store_hits_i_line', 'a')
    if st_a != old_r:
        fail('s6: store was not accepted on the old hit consumption edge')
    yng = ev('s6_young_i_blocked_on_store', 'a')
    if yng <= st_a:
        fail('s6: young I was accepted on the store edge')
    # the young I must miss because the line was invalidated
    for scen in ('s6_byte_store_i_miss', 's6_half_store_i_miss', 's6_zero_strobe_i_miss'):
        n = first_ar_after(summ, ev(scen, 'a'), get(scen)['addr'])
        if n is None:
            fail('%s: expected a miss AR after the store invalidated the line' % scen)
    # S7: I hit completes while the write drains, I miss waits for the drain.
    for n, ln, scen in summ['ar']:
        e = at(n)
        if e['busy']:
            fail('AR issued while the write buffer was busy (edge %d, %s)' % (n, scen))
    bw = ev('s7_i_hit_under_write_busy', 'r')
    if not at(bw - 1)['busy'] and not at(bw)['busy']:
        fail('s7: the I hit did not complete while the write was pending')
    ap = ev('s7_i_miss_waits_drain', 'a')
    ar = first_ar_after(summ, ap, get('s7_i_miss_waits_drain')['addr'])
    if ar is None:
        fail('s7: I miss never issued AR')
    # S8: forwarding expectations are already asserted through the replay data.
    # S10: uncached reads must both go to DDR and see the poke.
    for s1, s2 in (('s10_camera_first_read', 's10_camera_second_read'),
                   ('s10_pp_first_read', 's10_pp_second_read')):
        t1, t2 = get(s1), get(s2)
        n1 = first_ar_after(summ, A[t1['idx']], t1['addr'])
        n2 = first_ar_after(summ, A[t2['idx']], t2['addr'])
        if n1 is None or n2 is None:
            fail('%s/%s: uncached read did not reach DDR twice' % (s1, s2))
    # S9: every reset epoch must be balanced.
    return True


def bridge_checks(summ, inputs, mode):
    if mode == 'on':
        scenario_checks(summ)
    else:
        summ['off'] = scenario_checks_off(summ)
    return True


# ------------------------------------------------------------- SoC reference
DDR_BASE = 0x4000_0000


def load_soc_trace(path):
    """Split the SoC trace into bridge edges, front-end lines and retires."""
    fe, ret = {}, {}
    for line in Path(path).read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w:
            continue
        d = dict(item.split('=', 1) for item in w[1:])
        n = int(d['n'])
        if w[0] == 'F' and d['ph'] == 'PRE':
            fe[n] = d
        elif w[0] == 'R':
            ret.setdefault(n, d)
    return fe, [ret[k] for k in sorted(ret)]


class Rv32:
    """Reference for the exact RV32I subset the frozen program uses."""
    NAMES = 'lui jal jalr beq bne lw sw addi add'.split()

    def __init__(self, mem, pc):
        self.mem = mem
        self.pc = pc
        self.reg = [0] * 32

    def word(self, cpu_addr):
        if DDR_BASE <= cpu_addr < DDR_BASE + 0x1000_0000:
            return self.mem.word(cpu_addr - DDR_BASE)
        fail('reference touched a non-DDR word at %08x' % cpu_addr)

    def step(self):
        pc, inst = self.pc, self.mem.word((self.pc - DDR_BASE))
        op = inst & 0x7F
        rd = (inst >> 7) & 0x1F
        f3 = (inst >> 12) & 7
        rs1 = (inst >> 15) & 0x1F
        rs2 = (inst >> 20) & 0x1F
        imm_i = (inst >> 20) & 0xFFF
        imm_i = imm_i - 0x1000 if imm_i & 0x800 else imm_i
        imm_s = (((inst >> 25) & 0x7F) << 5) | ((inst >> 7) & 0x1F)
        imm_s = imm_s - 0x1000 if imm_s & 0x800 else imm_s
        imm_b = (((inst >> 31) & 1) << 12) | (((inst >> 7) & 1) << 11) | \
                (((inst >> 25) & 0x3F) << 5) | (((inst >> 8) & 0xF) << 1)
        imm_b = imm_b - 0x2000 if imm_b & 0x1000 else imm_b
        imm_j = (((inst >> 31) & 1) << 20) | (((inst >> 12) & 0xFF) << 12) | \
                (((inst >> 20) & 1) << 11) | (((inst >> 21) & 0x3FF) << 1)
        imm_j = imm_j - 0x200000 if imm_j & 0x100000 else imm_j
        we, wd = 0, 0
        npc = (pc + 4) & 0xFFFFFFFF
        name = None
        if op == 0x37:                                    # lui
            name = 'lui'
            we, wd = 1, (inst & 0xFFFFF000)
        elif op == 0x6F:                                  # jal
            name = 'jal'
            we = 1 if rd else 0
            wd = npc
            npc = (pc + imm_j) & 0xFFFFFFFF
        elif op == 0x67:                                  # jalr
            name = 'jalr'
            tgt = (self.reg[rs1] + imm_i) & 0xFFFFFFFF
            we = 1 if rd else 0
            wd = npc
            npc = tgt & ~1
        elif op == 0x63:                                  # beq / bne
            name = 'beq' if f3 == 0 else ('bne' if f3 == 1 else None)
            if name is None:
                fail('reference: unsupported branch f3=%d at %08x' % (f3, pc))
            eq = self.reg[rs1] == self.reg[rs2]
            if (name == 'beq') == eq:
                npc = (pc + imm_b) & 0xFFFFFFFF
        elif op == 0x03:                                  # lw
            name = 'lw'
            if f3 != 2:
                fail('reference: unsupported load f3=%d at %08x' % (f3, pc))
            we, wd = 1, self.word((self.reg[rs1] + imm_i) & 0xFFFFFFFF)
        elif op == 0x23:                                  # sw
            name = 'sw'
            if f3 != 2:
                fail('reference: unsupported store f3=%d at %08x' % (f3, pc))
            addr = (self.reg[rs1] + imm_s) & 0xFFFFFFFF
            if DDR_BASE <= addr < DDR_BASE + 0x1000_0000:
                self.mem.write_beat(addr - DDR_BASE,
                                    self.reg[rs2] << (8 * ((addr - DDR_BASE) & 31)),
                                    (0xF << ((addr - DDR_BASE) & 31)) & 0xFFFFFFFF)
            elif not (0x1000_0000 <= addr < 0x1000_1000):
                fail('reference: store outside the modelled apertures at %08x' % addr)
        elif op == 0x13:                                  # addi
            name = 'addi'
            we = 1 if rd else 0
            wd = (self.reg[rs1] + imm_i) & 0xFFFFFFFF
        elif op == 0x33:                                  # add
            name = 'add'
            if f3 != 0 or (inst >> 25) & 0x7F:
                fail('reference: unsupported OP at %08x' % pc)
            we = 1 if rd else 0
            wd = (self.reg[rs1] + self.reg[rs2]) & 0xFFFFFFFF
        else:
            fail('reference: unsupported opcode 0x%02x at %08x' % (op, pc))
        rec = dict(pc=pc, inst=inst, we=we, rd=rd, wd=wd, npc=npc, op=name)
        if we and rd:
            self.reg[rd] = wd
        self.pc = npc
        return rec


def soc_retire_check(edges, retires, mem, prog_words, epoch, stop_pcs):
    """Replay the frozen program against the retire stream of one epoch."""
    got = [r for r in retires if int(r['ep']) == epoch]
    if not got:
        fail('epoch %d has no retire records' % epoch)
    cpu = Rv32(mem, 0x4000_0000)
    used = 0
    for r in got:
        want = cpu.step()
        if used >= len(stop_pcs):
            pass
        pc = int(r['pc'], 16)
        if pc in stop_pcs:
            # trailing self-loop: the reference stops advancing
            break
        if pc != want['pc']:
            fail('epoch %d retire %d: pc %08x != reference %08x'
                 % (epoch, used, pc, want['pc']))
        if int(r['inst'], 16) != want['inst']:
            fail('epoch %d retire at %08x: inst %08x != reference %08x'
                 % (epoch, pc, int(r['inst'], 16), want['inst']))
        if int(r['we'], 16) != want['we']:
            fail('epoch %d retire at %08x: rf_we %d != reference %d'
                 % (epoch, pc, int(r['we'], 16), want['we']))
        if int(r['trap']) != 0:
            fail('epoch %d: unexpected trap retire at %08x' % (epoch, pc))
        if want['we']:
            if int(r['rd'], 16) != want['rd']:
                fail('epoch %d retire at %08x: rd x%d != reference x%d'
                     % (epoch, pc, int(r['rd'], 16), want['rd']))
            if int(r['wd'], 16) != want['wd']:
                fail('epoch %d retire at %08x: wdata %08x != reference %08x'
                     % (epoch, pc, int(r['wd'], 16), want['wd']))
        if int(r['npc'], 16) != want['npc']:
            fail('epoch %d retire at %08x: next_pc %08x != reference %08x'
                 % (epoch, pc, int(r['npc'], 16), want['npc']))
        used += 1
    return used, cpu

def new_soc_stats():
    return dict(i_acc=0, i_rsp=0, d_acc=0, d_rsp=0, ar=0, aw=0, w=0,
                i_cancel=0, d_cancel=0,
                d_miss_windows=0, i_rsp_in_d_window=0, max_i_rsp_in_window=0,
                fills=0, store_bytes=0)


def soc_protocol(edges, mem, preloads=None):
    """One-pass, token-free bridge protocol replay of the real-CPU trace.

    Every expectation (hit/miss verdict, response data, beat data, store bytes)
    is derived from the reference line buffers and the reference memory, never
    from DUT internals. A reset cancels whatever is outstanding, exactly as the
    bridge job does, and must not leak into the next epoch.
    """
    icache, dcache = Cache(), Cache()
    stats = {}
    st = new_soc_stats()
    i_q, d_q, pend_miss = [], [], []
    read_inflight, read_tok = 0, None
    pending = aw_open = None
    ar_hold = aw_hold = None
    d_win = None
    cur_ep = None
    for e in edges:
        ep = int(e['ep'])
        if ep != cur_ep:
            if cur_ep is not None:
                # Whatever the previous epoch left in flight is cancelled by the
                # reset that opens the new one; keep the books balanced per epoch.
                stats[cur_ep]['i_cancel'] += len(i_q)
                stats[cur_ep]['d_cancel'] += len(d_q)
                i_q, d_q, pend_miss = [], [], []
                read_inflight, read_tok, pending, aw_open = 0, None, None, None
                ar_hold = aw_hold = None
                icache.clear()
                dcache.clear()
                d_win = None
            cur_ep = ep
            st = stats[ep] = new_soc_stats()
            if preloads and ep in preloads:
                preload(mem, preloads[ep])
        n = e['n']
        if e['rst'] == 0 or e['init'] == 0:
            st['i_cancel'] += len(i_q)
            st['d_cancel'] += len(d_q)
            i_q, d_q, pend_miss = [], [], []
            read_inflight, read_tok, pending, aw_open = 0, None, None, None
            ar_hold = aw_hold = None
            icache.clear()
            dcache.clear()
            d_win = None
            continue

        # ---------------------------------------------------------- responses
        if e['ip']:
            st['i_rsp'] += 1
            if not i_q:
                fail('epoch %d: inst response without an outstanding request at %d'
                     % (ep, n))
            p = i_q.pop(0)
            if p['kind'] == 'hit':
                if n != p['accept'] + 1:
                    fail('epoch %d: I hit response edge %d != accept+1 (%d)'
                         % (ep, n, p['accept']))
            elif p['r_edge'] is None or n != p['r_edge'] + 1:
                fail('epoch %d: I miss response edge %d is not R+1 (%s)'
                     % (ep, n, p['r_edge']))
            if e['id'] != p['data']:
                fail('epoch %d: I response data %08x != reference %08x at %d'
                     % (ep, e['id'], p['data'], n))
            if e['ie']:
                fail('epoch %d: I response error at %d' % (ep, n))
            if d_win is not None:
                st['i_rsp_in_d_window'] += 1
                d_win['hits'] += 1
        if e['dp']:
            st['d_rsp'] += 1
            if not d_q:
                fail('epoch %d: data response without an outstanding request at %d'
                     % (ep, n))
            p = d_q.pop(0)
            if e['de']:
                fail('epoch %d: data response error at %d' % (ep, n))
            if p['kind'] == 'store':
                pass
            elif p['kind'] == 'hit':
                if n != p['accept'] + 1:
                    fail('epoch %d: D hit response edge %d != accept+1 (%d)'
                         % (ep, n, p['accept']))
                if e['dd'] != p['data']:
                    fail('epoch %d: D hit data %08x != reference %08x at %d'
                         % (ep, e['dd'], p['data'], n))
            else:
                if p['r_edge'] is None or n != p['r_edge'] + 1:
                    fail('epoch %d: D miss response edge %d is not R+1 (%s)'
                         % (ep, n, p['r_edge']))
                if e['dd'] != p['data']:
                    fail('epoch %d: D miss data %08x != reference %08x at %d'
                         % (ep, e['dd'], p['data'], n))
                d_win['close'] = n
                st['d_miss_windows'] += 1
                st['max_i_rsp_in_window'] = max(st['max_i_rsp_in_window'], d_win['hits'])
                d_win = None

        # -------------------------------------------------------- DDR read
        if ar_hold is not None:
            if not e['arv']:
                fail('epoch %d: AR withdrawn before acceptance at %d' % (ep, n))
            if (e['ara'], e['ari']) != ar_hold:
                fail('epoch %d: AR fields changed under backpressure at %d' % (ep, n))
            if e['arr']:
                ar_hold = None
        if e['arv'] and not e['arr']:
            ar_hold = (e['ara'], e['ari'])
        if e['arv'] and e['busy']:
            fail('epoch %d: AR while the posted write drains at %d' % (ep, n))
        if e['arv'] and e['arr']:
            if e['ara'] & 7:
                fail('epoch %d: AR not 32-byte aligned at %d' % (ep, n))
            if read_inflight:
                fail('epoch %d: second physical read in flight at %d' % (ep, n))
            line = e['ara'] << 2
            cand = [p for p in pend_miss if (p['line'] >> 5) == (line >> 5)]
            if len(cand) != 1:
                fail('epoch %d: AR %08x matches %d parked misses at %d'
                     % (ep, line, len(cand), n))
            read_inflight = 1
            read_tok = cand[0]
            st['ar'] += 1
        if e['rv']:
            if not read_inflight or read_tok is None:
                fail('epoch %d: R without an accepted read at %d' % (ep, n))
            beat = mem.beat(read_tok['line'])
            got = e['rdv'].to_bytes(32, 'little')
            if got != beat:
                bad = [k for k in range(32) if got[k] != beat[k]]
                fail('epoch %d: R beat mismatch at %d (line %08x bytes %s)'
                     % (ep, n, read_tok['line'], bad[:4]))
            if e['rid'] != (1 if read_tok['side'] == 'D' else 0):
                fail('epoch %d: R id %d for the %s beat at %d'
                     % (ep, e['rid'], read_tok['side'], n))
            lane = (read_tok['addr'] >> 2) & 7
            read_tok['data'] = int.from_bytes(beat[lane * 4:lane * 4 + 4], 'little')
            read_tok['r_edge'] = n
            read_tok['kind'] = 'miss'
            (icache if read_tok['side'] == 'I' else dcache).fill(read_tok['line'], beat)
            pend_miss.remove(read_tok)
            st['fills'] += 1
            read_inflight = 0
            read_tok = None

        # ------------------------------------------------------- DDR write
        if aw_hold is not None:
            if not e['awv']:
                fail('epoch %d: AW withdrawn before acceptance at %d' % (ep, n))
            if (e['awa'], e['wdv'], e['wsv']) != aw_hold:
                fail('epoch %d: AW/W fields changed under backpressure at %d' % (ep, n))
        if e['awv'] and not e['awr']:
            aw_hold = (e['awa'], e['wdv'], e['wsv'])
        if e['awv'] and e['awr']:
            if e['awa'] & 7 or e['awl'] != 0:
                fail('epoch %d: AW alignment/len wrong at %d' % (ep, n))
            if pending is None:
                fail('epoch %d: AW without an accepted store at %d' % (ep, n))
            shift = pending['addr'] & 31
            if (e['awa'] << 2) != (pending['addr'] & ~31):
                fail('epoch %d: AW %08x is not the store line %08x at %d'
                     % (ep, e['awa'] << 2, pending['addr'] & ~31, n))
            if e['wsv'] != (pending['wstrb'] << shift) & 0xFFFFFFFF or \
                    e['wdv'] != (pending['wdata'] << (8 * shift)) & ((1 << 256) - 1):
                fail('epoch %d: AW data/strobe do not match the store at %d' % (ep, n))
            aw_hold = None
            aw_open = dict(addr=e['awa'] << 2, wdata=e['wdv'], wstrb=e['wsv'])
            st['aw'] += 1
        if e['wrdy']:
            if aw_open is None:
                fail('epoch %d: W without an open AW at %d' % (ep, n))
            if aw_open['wdata'] != e['wdv'] or aw_open['wstrb'] != e['wsv']:
                fail('epoch %d: W differs from the accepted AW at %d' % (ep, n))
            mem.write_beat(aw_open['addr'], aw_open['wdata'], aw_open['wstrb'])
            st['store_bytes'] += bin(aw_open['wstrb']).count('1')
            st['w'] += 1
            if dcache.valid[dcache.idx(aw_open['addr'])] and \
                    dcache.tag[dcache.idx(aw_open['addr'])] == (aw_open['addr'] >> 5):
                dcache.poke_bytes(aw_open['addr'], pending['wdata'], pending['wstrb'])
            pending = None
            aw_open = None

        # -------------------------------------------------------- accepts
        if e['iv'] and e['ir']:
            st['i_acc'] += 1
            addr = e['ia']
            if icache.hit(addr):
                p = dict(side='I', kind='hit', accept=n, addr=addr, line=addr & ~31,
                         data=icache.word(addr), r_edge=None)
            else:
                p = dict(side='I', kind='miss', accept=n, addr=addr, line=addr & ~31,
                         data=None, r_edge=None)
                pend_miss.append(p)
            i_q.append(p)
        if e['dv'] and e['dr']:
            st['d_acc'] += 1
            addr = e['da']
            if e['dw']:
                if icache.hit(addr):
                    icache.invalidate(addr)
                pending = dict(addr=addr, wdata=e['dwd'], wstrb=e['ds'],
                               lane=(addr >> 2) & 7)
                d_q.append(dict(side='D', kind='store', accept=n, addr=addr,
                                line=addr & ~31, data=None, r_edge=None))
            elif dcache.hit(addr):
                data = dcache.word(addr)
                if pending is not None and (pending['addr'] >> 5) == (addr >> 5) and \
                        pending['lane'] == ((addr >> 2) & 7):
                    for k in range(4):
                        if (pending['wstrb'] >> k) & 1:
                            data = (data & ~(0xFF << (8 * k))) | \
                                   (((pending['wdata'] >> (8 * k)) & 0xFF) << (8 * k))
                d_q.append(dict(side='D', kind='hit', accept=n, addr=addr,
                                line=addr & ~31, data=data, r_edge=None))
            else:
                if d_win is not None:
                    fail('epoch %d: nested D miss window at %d' % (ep, n))
                p = dict(side='D', kind='miss', accept=n, addr=addr, line=addr & ~31,
                         data=None, r_edge=None)
                pend_miss.append(p)
                d_q.append(p)
                d_win = dict(open=n, hits=0)

    if i_q or d_q or pend_miss or read_inflight:
        fail('unfinished traffic at the end of the trace (i=%d d=%d miss=%d rd=%d)'
             % (len(i_q), len(d_q), len(pend_miss), read_inflight))
    for ep, st in stats.items():
        if st['i_acc'] != st['i_rsp'] + st['i_cancel']:
            fail('epoch %d: %d I accepts but %d responses and %d cancels'
                 % (ep, st['i_acc'], st['i_rsp'], st['i_cancel']))
        if st['d_acc'] != st['d_rsp'] + st['d_cancel']:
            fail('epoch %d: %d D accepts but %d responses and %d cancels'
                 % (ep, st['d_acc'], st['d_rsp'], st['d_cancel']))
    return stats

def load_hex_image(path):
    words = []
    for line in Path(path).read_text(encoding='ascii').splitlines():
        if line.strip():
            words.append(int(line.strip(), 16))
    return words


def preload(mem, words, base_word=0):
    for i, w in enumerate(words):
        b = (base_word + i) * 4
        beat = mem.beats[mem.beat_of(b)]
        for k in range(4):
            beat[(b & 31) + k] = (w >> (8 * k)) & 0xFF


WRONG_PATH_LOCAL = {0x38, 0x3C, 0x40, 0x44, 0x48, 0x114}
WRONG_PATH_PCS = {DDR_BASE + a for a in WRONG_PATH_LOCAL}
WRONG_PATH_STORE = 0x1140
WRONG_PATH_STORE_WORD = 0x0460A023
STOP_PCS = {0x4000_01C8}


def run_soc(rundir):
    rundir = Path(rundir)
    inputs = json.loads((HERE / 'inputs.json').read_text(encoding='utf-8'))
    trace = rundir / 'soc.edges.log'
    edges = load_edges(trace)
    fe, retires = load_soc_trace(trace)

    prog = load_hex_image(HERE / 'soc_program.hex')
    fcam = load_hex_image(HERE / 'soc_fault_camera.hex')
    fpp = load_hex_image(HERE / 'soc_fault_pp.hex')
    preloads = {1: prog, 2: fcam, 3: fpp}

    # Two independent references from the same frozen image: one follows the
    # DDR traffic in time order, the other follows program order. Both apply
    # the same stores, so they must end identical.
    mem_proto = Mem(inputs['memory']['beats'])
    mem_ref = Mem(inputs['memory']['beats'])
    stats = soc_protocol(edges, mem_proto, preloads)
    p1 = stats[1]

    preload(mem_ref, prog)
    used, _ = soc_retire_check(edges, retires, mem_ref, None, 1, STOP_PCS)

    # --- parallel I service must exist inside a D miss window -------------
    if p1['d_miss_windows'] == 0:
        fail('epoch 1: the workload produced no D miss window')
    if p1['max_i_rsp_in_window'] == 0:
        fail('epoch 1: no instruction response was served inside a D miss window')
    # --- the wrong path must leave no trace ------------------------------
    for r in retires:
        if int(r['ep']) != 1:
            continue
        if int(r['pc'], 16) in WRONG_PATH_PCS:
            fail('epoch 1: wrong-path instruction %s retired at edge %d'
                 % (r['pc'], int(r['n'])))
    for e in edges:
        if int(e['ep']) != 1:
            continue
        if e['dv'] and e['dr'] and e['da'] == WRONG_PATH_STORE:
            fail('epoch 1: wrong-path store reached the bus at edge %d' % e['n'])
        if e['awv'] and e['awr'] and (e['awa'] << 2) == WRONG_PATH_STORE:
            fail('epoch 1: wrong-path store reached DDR at edge %d' % e['n'])
    pristine = Mem(inputs['memory']['beats'])
    if mem_proto.word(WRONG_PATH_STORE) != pristine.word(WRONG_PATH_STORE):
        fail('epoch 1: the wrong-path store line changed')
    # --- each fetched instruction is consumed exactly once ----------------
    # The front end owns a single-entry response buffer.  An entry may leave it
    # in exactly two ways: popped into IF/ID, or discarded by a redirect.  A
    # fill (0->1 on bufv) therefore has to be matched by one of those two, so
    # counting the transitions proves nothing is consumed twice and nothing is
    # silently overwritten.
    ep1_edges = sorted(n for n, v in fe.items() if v['ep'] == '1')
    if not ep1_edges:
        fail('epoch 1: no front-end records')
    fills = pops = discards = 0
    prev = prev_pop = '0'
    for n in ep1_edges:
        cur, popv = fe[n]['bufv'], fe[n]['pop']
        if prev == '0' and cur == '1':
            fills += 1
        elif prev == '1' and cur == '0' and prev_pop != '1':
            discards += 1
        if cur == '1' and popv == '1':
            pops += 1
        prev, prev_pop = cur, popv
    residual = 1 if (prev == '1' and prev_pop != '1') else 0
    if fills == 0:
        fail('epoch 1: no fetched instruction ever entered the response buffer')
    if pops == 0:
        fail('epoch 1: a buffered instruction was never popped into IF/ID')
    if fills != pops + discards + residual:
        fail('epoch 1: %d buffer fills but %d pops, %d discards, residual %d'
             % (fills, pops, discards, residual))
    # The retire stream must still be exactly the frozen program: the reference
    # walk consumed `used` records and everything after it has to be the
    # trailing self-loop, never a duplicate or a wrong-path instruction.
    for r in [x for x in retires if int(x['ep']) == 1][used:]:
        if int(r['pc'], 16) not in STOP_PCS:
            fail('epoch 1: retire %s after the reference program ended' % r['pc'])
    drops = sum(1 for v in fe.values() if v['drop'] == '1' and v['ep'] == '1')

    # --- the wrong path was really fetched, then thrown away --------------
    # Both redirects leave a sequential candidate behind: the taken branch at
    # 0x34 leaves 0x38.., the jal at 0x110 leaves 0x114.  Those candidates must
    # have been requested over the I channel (otherwise the redirect has no
    # stale response to discard) and must never reach IF/ID or retirement.
    i_acc = [(int(e['n']), e['ia']) for e in edges
             if int(e['ep']) == 1 and e['iv'] and e['ir']]
    fetched_wrong = [(n, a) for n, a in i_acc if a in WRONG_PATH_LOCAL]
    if not fetched_wrong:
        fail('epoch 1: the redirects never fetched a wrong-path instruction')
    if len({a for _, a in fetched_wrong}) < 2:
        fail('epoch 1: only %d distinct wrong-path fetches' % len(fetched_wrong))
    # The word at 0x38 is `sw x6,0x40(x1)`, unique inside the image, so seeing
    # it on the I response channel while it never retires is direct proof that
    # the taken branch flushed a stale instruction response.
    flushed = [int(e['n']) for e in edges
               if int(e['ep']) == 1 and e['ip'] and e['id'] == WRONG_PATH_STORE_WORD]
    if not flushed:
        fail('epoch 1: no wrong-path instruction ever came back on the I channel')
    for v in fe.values():
        if v['ep'] != '1' or v['bufv'] != '1':
            continue
        if (int(v['bufp'], 16) - DDR_BASE) in WRONG_PATH_LOCAL:
            fail('epoch 1: wrong-path instruction %s entered the response buffer'
                 % v['bufp'])

    # --- illegal fetch epochs -------------------------------------------
    faults = {}
    preload(mem_ref, fcam)
    for epoch, target, img in ((2, 0x4100_0000, fcam), (3, 0x4200_0000, fpp)):
        if epoch == 3:
            preload(mem_ref, fpp)
        st = stats[epoch]
        traps = [r for r in retires if int(r['ep']) == epoch and int(r['trap']) == 1]
        if len(traps) != 1:
            fail('epoch %d: %d trap records, expected exactly 1' % (epoch, len(traps)))
        t = traps[0]
        if int(t['cause'], 16) != 1:
            fail('epoch %d: trap cause %s != 1 (instruction access fault)'
                 % (epoch, t['cause']))
        if int(t['tval'], 16) != target:
            fail('epoch %d: trap tval %s != %08x' % (epoch, t['tval'], target))
        if int(t['pc'], 16) != target:
            fail('epoch %d: trap pc %s != %08x' % (epoch, t['pc'], target))
        for e in edges:
            if int(e['ep']) != epoch:
                continue
            if e['arv'] and e['arr'] and (e['ara'] << 2) >> 5 == target >> 5:
                fail('epoch %d: DDR fetch AR for the illegal window at edge %d'
                     % (epoch, e['n']))
        # the two-instruction program itself must retire correctly
        cpu2 = Rv32(mem_ref, 0x4000_0000)
        rets = 0
        for r in [x for x in retires if int(x['ep']) == epoch]:
            if int(r['trap']) == 1:
                break
            want = cpu2.step()
            if int(r['pc'], 16) != want['pc'] or int(r['inst'], 16) != want['inst']:
                fail('epoch %d: retire mismatch at %s' % (epoch, r['pc']))
            if want['we'] and int(r['wd'], 16) != want['wd']:
                fail('epoch %d: writeback mismatch at %s' % (epoch, r['pc']))
            rets += 1
        if rets != 2:
            fail('epoch %d: only %d of the 2 setup instructions retired' % (epoch, rets))
        faults[epoch] = dict(cause=int(t['cause'], 16), tval=t['tval'],
                             trap_pc=t['pc'], ar=st['ar'], fills=st['fills'])

    # --- final memory must equal the reference ---------------------------
    for i in range(inputs['memory']['beats']):
        if mem_proto.beats[i] != mem_ref.beats[i]:
            fail('soc: traffic-order and program-order references disagree at beat %d' % i)
    dump = {}
    for line in (rundir / 'soc.mem.log').read_text(encoding='ascii').splitlines():
        w = line.split()
        dump[int(w[0])] = int(w[1], 16)
    for i in range(inputs['memory']['beats']):
        if dump[i] != int.from_bytes(mem_proto.beats[i], 'little'):
            fail('soc: final memory beat %d differs from the reference' % i)

    return dict(status='PASS', epoch1=p1, epochs=stats, retires=used, pops=pops,
                drops=drops, faults=faults, edges=len(edges))


# --------------------------------------------------------------- performance
def perf_cycles(summ, mode='on'):
    plan = summ['plan']
    toks = [t for t in plan if t['scen'].startswith('perf_') and t['kind'] in ('I', 'D')]
    if not toks:
        fail('no perf tokens')
    d = next(t for t in toks if t['scen'] == 'perf_d_miss')
    ar = first_ar_after(summ, summ['accept'][d['idx']], d['addr'])
    if ar is None:
        fail('perf: no D AR')
    hits = [t for t in toks if t['scen'].startswith('perf_i_hit')]
    for t in hits:
        if t['idx'] not in summ['resp']:
            fail('perf: I hit %s got no response' % t['scen'])
    if mode == 'on':
        if max(summ['resp'][t['idx']] for t in hits) >= summ['resp'][d['idx']]:
            fail('perf: an I hit was not served inside the D miss window')
    else:
        if min(summ['accept'][t['idx']] for t in hits) < summ['resp'][d['idx']]:
            fail('perf: an I hit was still accepted inside the D miss window')
    last = max(summ['resp'][t['idx']] for t in hits)
    first_accept = min(summ['accept'][t['idx']] for t in hits)
    before = sum(1 for t in hits if summ['resp'][t['idx']] < summ['resp'][d['idx']])
    return dict(d_ar_edge=ar, d_accept=summ['accept'][d['idx']], d_resp=summ['resp'][d['idx']],
                first_accept=first_accept, last_resp=last,
                span_from_ar=last - ar, span_from_accept=last - first_accept,
                i_hits=len(hits), i_hits_before_d_resp=before,
                last_hit_minus_d_resp=last - summ['resp'][d['idx']])


# ---------------------------------------------------------------------- main
def run_bridge(rundir, mode):
    rundir = Path(rundir)
    inputs = json.loads((HERE / 'inputs.json').read_text(encoding='utf-8'))
    plan = load_plan(HERE / 'plan_bridge.txt')
    edges = load_edges(rundir / ('bridge_%s.edges.log' % mode))
    pokes = load_pokes(rundir / ('bridge_%s.tok.log' % mode))
    mem = Mem(inputs['memory']['beats'])
    summ = replay(plan, edges, mem, pokes=pokes)
    bridge_checks(summ, inputs, mode)
    # final memory must equal the model's dump
    dump = {}
    for line in (rundir / ('bridge_%s.mem.log' % mode)).read_text(encoding='ascii').splitlines():
        w = line.split()
        dump[int(w[0])] = w[1]
    for i in range(inputs['memory']['beats']):
        want = int.from_bytes(mem.beats[i], 'little')
        got = int(dump[i], 16)
        if got != want:
            fail('final memory beat %d differs from the reference: %064x vs %064x'
                 % (i, got, want))
    perf = perf_cycles(summ, mode)
    return dict(status='PASS', mode=mode, stats=summ['stats'], perf=perf,
                accepts=len(summ['accept']), responses=len(summ['resp']),
                cancels=len(summ['cancels']),
                off=summ.get('off'),
                ar=[(n, '%08x' % ln, s) for n, ln, s in summ['ar']],
                aw=[(a['edge'], '%08x' % a['addr'], '%04x' % a['wstrb']) for a in summ['aw']])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=('bridge', 'soc', 'selftest'))
    ap.add_argument('rundir', nargs='?')
    ap.add_argument('onoff', nargs='?', default='on')
    a = ap.parse_args()
    if a.mode == 'bridge':
        out = run_bridge(a.rundir, a.onoff)
        print(json.dumps(out, indent=2))
    elif a.mode == 'soc':
        out = run_soc(a.rundir)
        print(json.dumps(out, indent=2))
    else:
        import selftest
        selftest.main()


if __name__ == '__main__':
    try:
        main()
    except CheckError as exc:
        print('CHECK: FAIL %s' % exc)
        sys.exit(1)
