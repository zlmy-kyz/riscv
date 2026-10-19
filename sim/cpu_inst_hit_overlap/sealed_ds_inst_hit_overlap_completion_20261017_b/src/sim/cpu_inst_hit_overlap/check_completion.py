"""Task033 completion checker (independent of the original harness).

Modes
  completion <rundir>   verify the new single-run bridge trace and the three
                        hard coverage gates
  legacy <oldrundir>    re-verify the original on/off traces from their frozen
                        copies, pin the corrected completion statistic and bind
                        the CPU instruction token 46/47/48-61/62/66
  selftest <rundir>     offline synthetic traces that must be rejected

Every expected value is recomputed from the frozen inputs (plan, model memory)
and the recorded external handshakes. No DUT internal state is read, except the
observation-only fields the testbench also writes (front-end buffer/pop) which
are only used for the CPU binding evidence.
"""
import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

CAM_LO, CAM_HI = 0x01000000, 0x01400000
PP_LO, PP_HI = 0x02000000, 0x02010000
HEX = {'ia', 'da', 'dwd', 'ds', 'id', 'dd', 'ara', 'awa', 'wdv', 'wsv', 'rdv'}
CTRL = ('rst', 'init', 'iv', 'ir', 'dv', 'dr', 'dw', 'ip', 'dp', 'ie', 'de',
        'busy', 'arv', 'arr', 'awv', 'awr', 'wrdy', 'rv', 'rl')


class CheckError(Exception):
    pass


def fail(msg):
    raise CheckError(msg)


# ------------------------------------------------------------------ log/fields
def parse_log(path):
    pre, post = {}, {}
    p = Path(path)
    if not p.exists():
        fail('edge log missing: %s' % p)
    for line in p.read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w or w[0] != 'E':
            continue
        d = dict(item.split('=', 1) for item in w[1:])
        n = int(d['n'])
        (pre if d['ph'] == 'PRE' else post)[n] = d
    if not pre:
        fail('edge log empty: %s' % p)
    if sorted(pre) != list(range(1, len(pre) + 1)):
        fail('edge numbering is not contiguous in %s' % p)
    if set(pre) != set(post):
        fail('PRE/POST mismatch in %s' % p)
    return [dict(n=n, pre=pre[n], post=post[n]) for n in sorted(pre)]


def known(e, k):
    v = e['pre'].get(k)
    return v is not None and all(c in '01' for c in v)


def num(e, k):
    v = e['pre'][k]
    try:
        return int(v, 16) if k in HEX else int(v)
    except ValueError:
        fail('edge %d: field %s is unknown (%r)' % (e['n'], k, v))


def bit(e, k, default=0):
    v = e['pre'].get(k)
    if v is None or any(c not in '01' for c in v):
        return default
    return int(v)


def validate_known(edges):
    """X/Z is only tolerated while reset is asserted or nothing is valid."""
    live = False
    for e in edges:
        if not known(e, 'rst'):
            continue
        if num(e, 'rst') == 1:
            live = True
        if not live:
            continue
        for k in CTRL:
            if not known(e, k):
                fail('edge %d: control %s is unknown (%r) after reset release'
                     % (e['n'], k, e['pre'][k]))
        if bit(e, 'iv') and not all(c in '0123456789abcdef' for c in e['pre']['ia']):
            fail('edge %d: I request address is unknown with valid=1' % e['n'])
        if bit(e, 'dv'):
            for k in ('da', 'dwd', 'ds', 'sz'):
                if any(c not in '0123456789abcdef' for c in e['pre'][k]):
                    fail('edge %d: D request field %s is unknown with valid=1'
                         % (e['n'], k))
        if bit(e, 'ip'):
            if any(c not in '0123456789abcdef' for c in e['pre']['id']):
                fail('edge %d: I response data is unknown while valid' % e['n'])
        if bit(e, 'dp'):
            if any(c not in '0123456789abcdef' for c in e['pre']['dd']):
                fail('edge %d: D response data is unknown while valid' % e['n'])
        if bit(e, 'arv'):
            for k in ('ara', 'ari', 'arl'):
                if any(c not in '0123456789abcdef' for c in e['pre'][k]):
                    fail('edge %d: AR field %s is unknown while valid' % (e['n'], k))
        if bit(e, 'awv'):
            for k in ('awa', 'awi', 'awl', 'wdv', 'wsv'):
                if any(c not in '0123456789abcdef' for c in e['pre'][k]):
                    fail('edge %d: AW field %s is unknown while valid' % (e['n'], k))
        if bit(e, 'rv'):
            for k in ('rdv', 'rid', 'rl'):
                if any(c not in '0123456789abcdef' for c in e['pre'][k]):
                    fail('edge %d: R field %s is unknown while valid' % (e['n'], k))


def load_tokens(path):
    """TB-side record of model pokes and phase markers (never used as a fact)."""
    pokes, marks = {}, []
    p = Path(path)
    if not p.exists():
        fail('token log missing: %s' % p)
    for line in p.read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w:
            continue
        if w[0] == 'M':
            d = dict(item.split('=', 1) for item in w[2:])
            edge = int(d['edge']) + 1          # visible from the next rising edge
            pokes.setdefault(edge, []).append((int(d['addr'], 16),
                                               int(d['data'], 16),
                                               int(d['strb'], 16)))
        elif w[0] == 'S':
            d = dict(item.split('=', 1) for item in w[2:])
            marks.append((w[1], int(d['edge'])))
    return pokes, marks


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
        return addr >> 5

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

    @staticmethod
    def idx(addr):
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
        """Byte-lane update of a cached line, used by the frozen legacy replay."""
        i = self.idx(addr)
        w = self.data[i][(addr >> 2) & 7]
        for k in range(4):
            if (wstrb >> k) & 1:
                w = (w & ~(0xFF << (8 * k))) | (((wdata >> (8 * k)) & 0xFF) << (8 * k))
        self.data[i][(addr >> 2) & 7] = w

    def clear(self):
        self.valid = [False] * 64


def uncached(addr):
    return CAM_LO <= addr < CAM_HI or PP_LO <= addr < PP_HI


# ------------------------------------------------------------ completion replay
def new_stats():
    return dict(i_acc=0, i_rsp=0, d_acc=0, d_rsp=0, i_cancel=0, d_cancel=0,
                ar=0, r=0, reset_rsp=0)


def replay_completion(edges, mem, pokes):
    ic, dc = Cache(), Cache()
    iq, dq = [], []
    inflight = None
    ar_hold = None
    stats = {}
    facts = dict(accepts=[], ars=[], rs=[], resps=[], cancels=[])

    for e in edges:
        n = e['n']
        ep = num(e, 'ep')
        s = stats.setdefault(ep, new_stats())

        for (pa, pd, ps) in (pokes or {}).get(n, ()):
            mem.poke(pa, pd, ps)

        rst, init = num(e, 'rst'), num(e, 'init')
        if rst == 0 or init == 0:
            if (bit(e, 'iv') and bit(e, 'ir')) or (bit(e, 'dv') and bit(e, 'dr')):
                fail('request accepted on the reset edge %d' % n)
            if bit(e, 'ip'):
                s['reset_rsp'] += 1
            if bit(e, 'dp'):
                s['reset_rsp'] += 1
            for op in iq:
                s['i_cancel'] += 1
                facts['cancels'].append((n, 'I', op))
            for op in dq:
                s['d_cancel'] += 1
                facts['cancels'].append((n, 'D', op))
            iq[:] = []
            dq[:] = []
            inflight = None
            ar_hold = None
            ic.clear()
            dc.clear()
            continue

        # ---- responses
        if bit(e, 'ip'):
            if not iq:
                fail('I response without an outstanding request at edge %d' % n)
            op = iq.pop(0)
            check_response(op, 'I', n, e)
            s['i_rsp'] += 1
            facts['resps'].append((n, 'I', op))
        elif iq and iq[0]['kind'] == 'hit' and n > iq[0]['accept'] + 1:
            fail('I hit response missing after accept edge %d' % iq[0]['accept'])
        if bit(e, 'dp'):
            if not dq:
                fail('D response without an outstanding request at edge %d' % n)
            op = dq.pop(0)
            check_response(op, 'D', n, e)
            s['d_rsp'] += 1
            facts['resps'].append((n, 'D', op))
        elif dq and dq[0]['kind'] == 'hit' and n > dq[0]['accept'] + 1:
            fail('D hit response missing after accept edge %d' % dq[0]['accept'])

        # ---- AR channel
        arv, arr = bit(e, 'arv'), bit(e, 'arr')
        if ar_hold is not None:
            if not arv:
                fail('AR withdrawn before acceptance at edge %d' % n)
            if (num(e, 'ara'), num(e, 'ari')) != ar_hold:
                fail('AR fields changed under backpressure at edge %d' % n)
        if arv and not arr:
            ar_hold = (num(e, 'ara'), num(e, 'ari'))
        if arv and arr:
            ar_hold = None
            if num(e, 'ara') & 7:
                fail('AR is not 32-byte aligned at edge %d' % n)
            if num(e, 'arl') != 0:
                fail('AR length is not zero at edge %d' % n)
            if bit(e, 'busy'):
                fail('AR asserted while the posted store drains at edge %d' % n)
            if inflight is not None:
                fail('a second physical read is in flight at edge %d' % n)
            ari = num(e, 'ari')
            if ari not in (0, 1):
                fail('AR owner id %d is not I(0)/D(1) at edge %d' % (ari, n))
            side = 'D' if ari == 1 else 'I'
            q = dq if side == 'D' else iq
            cand = [o for o in q if o['kind'] == 'miss' and o['ar_edge'] is None]
            if not cand:
                fail('AR at edge %d has no served %s miss' % (n, side))
            op = cand[0]
            line = (num(e, 'ara') >> 3) << 5
            if line != (op['addr'] & ~31):
                fail('AR %08x at edge %d is not the line of the pending %s miss %08x'
                     % (line, n, side, op['addr']))
            op['ar_edge'] = n
            op['line'] = line
            inflight = op
            s['ar'] += 1
            facts['ars'].append((n, side, line, op))

        # ---- R channel
        if bit(e, 'rv'):
            if inflight is None:
                fail('R without an accepted read at edge %d' % n)
            op = inflight
            if num(e, 'rid') != (1 if op['side'] == 'D' else 0):
                fail('R id %d does not match the %s owner at edge %d'
                     % (num(e, 'rid'), op['side'], n))
            if num(e, 'rl') != 1:
                fail('R last is not asserted at edge %d' % n)
            beat = mem.beat(op['line'])
            got = num(e, 'rdv').to_bytes(32, 'little')
            if got != beat:
                bad = [k for k in range(32) if got[k] != beat[k]]
                fail('R beat mismatch for %s at edge %d (line %08x bytes %s %s/%s)'
                     % (op['side'], n, op['line'], bad[:4],
                        ['%02x' % got[k] for k in bad[:4]],
                        ['%02x' % beat[k] for k in bad[:4]]))
            lane = (op['addr'] >> 2) & 7
            op['data'] = int.from_bytes(beat[lane * 4:lane * 4 + 4], 'little')
            op['r_edge'] = n
            if op['side'] == 'I':
                ic.fill(op['line'], beat)
            elif not uncached(op['line']):
                dc.fill(op['line'], beat)
            inflight = None
            s['r'] += 1
            facts['rs'].append((n, op['side'], op['line'], op))

        # ---- accepts
        if bit(e, 'iv') and bit(e, 'ir'):
            a = num(e, 'ia')
            if ic.hit(a):
                op = dict(side='I', addr=a, kind='hit', accept=n, data=ic.word(a),
                          ar_edge=None, r_edge=None, resp=None, line=None, ep=ep)
            else:
                op = dict(side='I', addr=a, kind='miss', accept=n, data=None,
                          ar_edge=None, r_edge=None, resp=None, line=None, ep=ep)
            iq.append(op)
            s['i_acc'] += 1
            facts['accepts'].append(op)
        if bit(e, 'dv') and bit(e, 'dr'):
            if bit(e, 'dw'):
                fail('unexpected store accepted at edge %d' % n)
            a = num(e, 'da')
            if not uncached(a) and dc.hit(a):
                op = dict(side='D', addr=a, kind='hit', accept=n, data=dc.word(a),
                          ar_edge=None, r_edge=None, resp=None, line=None, ep=ep)
            else:
                op = dict(side='D', addr=a, kind='miss', accept=n, data=None,
                          ar_edge=None, r_edge=None, resp=None, line=None, ep=ep)
            dq.append(op)
            s['d_acc'] += 1
            facts['accepts'].append(op)

    if inflight is not None:
        fail('a physical read is still in flight at the end of the trace')
    if iq or dq:
        fail('%d I and %d D requests never got a response' % (len(iq), len(dq)))

    for ep, s in sorted(stats.items()):
        if s['i_acc'] != s['i_rsp'] + s['i_cancel']:
            fail('epoch %d: %d I accepts but %d responses and %d cancels'
                 % (ep, s['i_acc'], s['i_rsp'], s['i_cancel']))
        if s['d_acc'] != s['d_rsp'] + s['d_cancel']:
            fail('epoch %d: %d D accepts but %d responses and %d cancels'
                 % (ep, s['d_acc'], s['d_rsp'], s['d_cancel']))
    return facts, stats


def check_response(op, side, n, e):
    if op['kind'] == 'hit':
        if n != op['accept'] + 1:
            fail('%s hit response edge %d is not accept+1 (accept %d, %08x)'
                 % (side, n, op['accept'], op['addr']))
        want = op['data']
    else:
        if op['r_edge'] is None or n != op['r_edge'] + 1:
            fail('%s miss response edge %d is not R+1 (R %s, %08x)'
                 % (side, n, op['r_edge'], op['addr']))
        want = op['data']
    got = num(e, 'id' if side == 'I' else 'dd')
    if got != want:
        fail('%s response data %08x != expected %08x at edge %d (%08x)'
             % (side, got, want, n, op['addr']))
    if num(e, 'ie' if side == 'I' else 'de') != 0:
        fail('%s response error flag set at edge %d' % (side, n))
    op['resp'] = n


# ---------------------------------------------------------------- gate helpers
def ic_rows_at(facts, edge):
    rows = {}
    for (n, side, line, op) in facts['rs']:
        if n >= edge:
            break
        if side == 'I':
            rows[(line >> 5) & 63] = line >> 5
    return rows


def one(items, what):
    if len(items) != 1:
        fail('%s: expected exactly one, found %d' % (what, len(items)))
    return items[0]


def gate_independent_hit(edges, facts, stats):
    s1 = stats.get(1)
    if s1 is None:
        fail('epoch 1 is missing')
    if s1['i_cancel'] != 1 or s1['d_cancel'] != 1:
        fail('epoch 1 cancels: I=%d D=%d, expected I=1 D=1'
             % (s1['i_cancel'], s1['d_cancel']))
    ci = [x for x in facts['cancels'] if x[1] == 'I' and x[2]['ep'] == 1]
    cd = [x for x in facts['cancels'] if x[1] == 'D' and x[2]['ep'] == 1]
    ic_op = one(ci, 'cancelled independent I request')[2]
    d_op = one(cd, 'cancelled D read')[2]
    if ic_op['kind'] != 'hit':
        fail('the independent I accept at edge %d was not a cached hit' % ic_op['accept'])
    if ic_op['ar_edge'] is not None:
        fail('the independent I hit issued an AR')
    if d_op['kind'] != 'miss' or d_op['ar_edge'] is None:
        fail('the paralleled D request was not a miss with its own AR')
    a1 = ic_op['accept']
    if not (d_op['ar_edge'] < a1 and d_op['resp'] is None):
        fail('the I hit at edge %d was not accepted inside an open D miss window' % a1)
    rst_edge = one([x[0] for x in facts['cancels']
                    if x[1] == 'I' and x[2] is ic_op], 'reset edge of the I hit')
    if rst_edge != a1 + 1:
        fail('the reset landed on edge %d, not on the planned consume edge %d'
             % (rst_edge, a1 + 1))
    if num(edges[a1 - 1], 'rst') != 1:
        fail('the I hit was not accepted on a live edge')
    if edges[a1 - 1]['post'].get('ip') != '1':
        fail('the POST sample at the independent accept edge did not show a response')
    pre = [o for o in facts['accepts']
           if o['side'] == 'I' and o['ep'] == 1 and o['kind'] == 'miss'
           and o['line'] == (ic_op['addr'] & ~31) and o['r_edge'] is not None]
    if not pre:
        fail('the I line was never really filled from DDR before the hit')
    if pre[0]['r_edge'] >= a1:
        fail('the I fill completed after the hit accept')
    ar_same = [x for x in facts['ars'] if x[1] == 'I' and x[2] == (ic_op['addr'] & ~31)
               and num(edges[x[0] - 1], 'ep') == 1]
    if len(ar_same) != 1:
        fail('epoch 1 issued %d ARs for the hit line, expected only the fill'
             % len(ar_same))
    # the post-reset cold read must go back to DDR
    cold = [o for o in facts['accepts']
            if o['side'] == 'I' and o['ep'] == 2 and o['addr'] == ic_op['addr']]
    if not cold:
        fail('no cold read of the interrupted line after the reset')
    if cold[0]['kind'] != 'miss' or cold[0]['r_edge'] is None:
        fail('the post-reset read hit the cache: the reset did not clear the line')
    if cold[0]['line'] != (ic_op['addr'] & ~31):
        fail('the post-reset read did not fetch the interrupted line')
    return dict(accept=a1, reset_edge=rst_edge, d_accept=d_op['accept'],
                d_ar=d_op['ar_edge'], post_ip=edges[a1 - 1]['post']['ip'],
                cold_accept=cold[0]['accept'], cold_ar=cold[0]['ar_edge'],
                cold_resp=cold[0]['resp'])


def gate_promoted_miss(edges, facts, stats):
    s2 = stats.get(2)
    if s2 is None:
        fail('epoch 2 is missing')
    if s2['i_cancel'] != 1 or s2['d_cancel'] != 0:
        fail('epoch 2 cancels: I=%d D=%d, expected I=1 D=0'
             % (s2['i_cancel'], s2['d_cancel']))
    i_op = one([x[2] for x in facts['cancels'] if x[1] == 'I' and x[2]['ep'] == 2],
               'cancelled I read')
    d_ops = [o for o in facts['accepts'] if o['side'] == 'D' and o['ep'] == 2]
    d_op = one(d_ops, 'D read in epoch 2')
    if d_op['kind'] != 'miss' or d_op['resp'] is None:
        fail('the epoch 2 D read was not a completed miss')
    if i_op['kind'] != 'miss':
        fail('the parked I request was not a miss')
    if not (d_op['ar_edge'] < i_op['accept'] < d_op['resp']):
        fail('the parked I miss was not accepted inside the D miss window')
    if i_op['ar_edge'] is None:
        fail('the parked I miss was never promoted to its own AR')
    if i_op['r_edge'] is not None:
        fail('the promoted I read returned before the reset')
    if i_op['ar_edge'] <= d_op['resp']:
        fail('the promoted AR did not wait for the D response')
    rst_edge = one([x[0] for x in facts['cancels']
                    if x[1] == 'I' and x[2] is i_op], 'reset edge of the promoted read')
    if rst_edge - i_op['ar_edge'] < 2:
        fail('the reset came %d edges after the AR, expected at least 2'
             % (rst_edge - i_op['ar_edge']))
    if num(edges[rst_edge - 1], 'rst') != 0:
        fail('the reset edge is not a reset edge')
    live = num(edges[i_op['ar_edge'] - 1], 'ia')
    if (live & ~31) == (i_op['addr'] & ~31):
        fail('the live address at the AR edge was not poisoned')
    rows = ic_rows_at(facts, i_op['ar_edge'])
    if rows.get((live >> 5) & 63) != (live >> 5):
        fail('the poisoned live address %08x was not a cached line' % live)
    after = [x for x in facts['ars']
             if x[1] == 'I' and x[0] > d_op['resp']
             and num(edges[x[0] - 1], 'ep') == 2]
    ar = one(after, 'I AR after the D response')
    if ar[2] != (i_op['addr'] & ~31):
        fail('the promoted AR used %08x, not the saved line %08x'
             % (ar[2], i_op['addr'] & ~31))
    cold = [o for o in facts['accepts']
            if o['side'] == 'I' and o['ep'] == 3 and o['addr'] == i_op['addr']]
    if not cold:
        fail('no cold read of the cancelled line after the reset')
    if cold[0]['kind'] != 'miss' or cold[0]['r_edge'] is None:
        fail('the post-reset read of the cancelled line did not succeed from DDR')
    return dict(d_accept=d_op['accept'], d_ar=d_op['ar_edge'], d_resp=d_op['resp'],
                i_accept=i_op['accept'], i_ar=i_op['ar_edge'], reset_edge=rst_edge,
                live_poison='%08x' % live, ar_line='%08x' % ar[2],
                cold_accept=cold[0]['accept'], cold_resp=cold[0]['resp'])


def gate_uncached_parallel(edges, facts, pokes, name, lo, hi):
    ops = [o for o in facts['accepts']
           if o['ep'] == 3 and lo <= o['addr'] < hi]
    d_ops = [o for o in ops if o['side'] == 'D']
    i_ops = [o for o in ops if o['side'] == 'I']
    if len(d_ops) != 2:
        fail('%s: %d D reads in the uncached window, expected 2' % (name, len(d_ops)))
    d1, d2 = d_ops
    for o in (d1, d2):
        if o['kind'] != 'miss' or o['ar_edge'] is None or o['resp'] is None:
            fail('%s: uncached D read %08x was not a completed miss' % (name, o['addr']))
    hits = [o for o in i_ops if o['kind'] == 'hit']
    if len(hits) != 2:
        fail('%s: %d cached I hits in the window, expected 2' % (name, len(hits)))
    pre = [o for o in i_ops if o['kind'] == 'miss']
    pre = one(pre, '%s: I line preheat' % name)
    if pre['r_edge'] is None or pre['accept'] > d1['accept']:
        fail('%s: the I line was not really filled before the D read' % name)
    h1, h2 = hits
    if not (d1['ar_edge'] < h1['accept'] < d1['r_edge']):
        fail('%s: the first I hit was not accepted while the D read waited for R' % name)
    if h1['resp'] != h1['accept'] + 1:
        fail('%s: the first I hit was not answered on the next edge' % name)
    if h2['accept'] != d1['r_edge']:
        fail('%s: the second I hit was accepted on edge %d, not on the D R edge %d'
             % (name, h2['accept'], d1['r_edge']))
    e = edges[h2['accept'] - 1]
    if not (bit(e, 'rv') and num(e, 'rid') == 1):
        fail('%s: the second I hit was not accepted on the R edge' % name)
    if h2['resp'] != d1['resp']:
        fail('%s: the D and I responses did not arrive on the same edge' % name)
    e = edges[d1['resp'] - 1]
    if not (bit(e, 'ip') and bit(e, 'dp')):
        fail('%s: the dual response edge does not show both responses' % name)
    lane1 = (h1['addr'] >> 2) & 7
    lane2 = (h2['addr'] >> 2) & 7
    if lane1 == lane2:
        fail('%s: both I hits used word lane %d' % (name, lane1))
    bp = [e for e in edges
          if d1['accept'] < e['n'] <= d1['ar_edge']
          and bit(e, 'arv') and not bit(e, 'arr')]
    if not bp:
        fail('%s: the D AR never saw backpressure' % name)
    if d1['r_edge'] - d1['ar_edge'] < 2:
        fail('%s: the D R arrived on the AR edge, not on a later edge' % name)
    ars = [x for x in facts['ars'] if x[1] == 'I' and lo <= x[2] < hi]
    if len(ars) != 1 or ars[0][3] is not pre:
        fail('%s: %d I ARs in the window, expected only the preheat' % (name, len(ars)))
    pk = [(edge, p) for edge, rows in sorted(pokes.items()) for p in rows
          if p[0] == d1['addr']]
    if len(pk) != 1:
        fail('%s: %d model pokes at the read address, expected 1' % (name, len(pk)))
    poke_edge = pk[0][0]
    if d2['accept'] < poke_edge:
        fail('%s: the second D read started before the model update' % name)
    if d1['data'] == d2['data']:
        fail('%s: the second D read returned the stale value %08x' % (name, d1['data']))
    return dict(first_d=dict(accept=d1['accept'], ar=d1['ar_edge'], r=d1['r_edge'],
                             resp=d1['resp'], data='%08x' % d1['data'],
                             backpressure=len(bp)),
                hits=[dict(accept=h1['accept'], resp=h1['resp'],
                           addr='%08x' % h1['addr'], lane=lane1),
                      dict(accept=h2['accept'], resp=h2['resp'],
                           addr='%08x' % h2['addr'], lane=lane2)],
                preheat=dict(accept=pre['accept'], ar=pre['ar_edge'],
                             r=pre['r_edge'], resp=pre['resp']),
                second_d=dict(accept=d2['accept'], ar=d2['ar_edge'],
                              resp=d2['resp'], data='%08x' % d2['data']),
                poke_edge=poke_edge)


# ---------------------------------------------------------------- mode: bridge
def analyze(edges, pokes):
    """Full independent analysis of one completion trace."""
    validate_known(edges)
    mem = Mem()
    facts, stats = replay_completion(edges, mem, pokes)
    g1 = gate_independent_hit(edges, facts, stats)
    g2 = gate_promoted_miss(edges, facts, stats)
    g3 = [gate_uncached_parallel(edges, facts, pokes, 'camera', CAM_LO, CAM_HI),
          gate_uncached_parallel(edges, facts, pokes, 'preprocess', PP_LO, PP_HI)]
    return dict(mem=mem, facts=facts, stats=stats,
                gates=dict(independent_hit=g1, promoted_miss=g2, uncached=g3))


def run_completion(rundir):
    rundir = Path(rundir)
    edges = parse_log(rundir / 'completion.edges.log')
    pokes, marks = load_tokens(rundir / 'completion.tok.log')
    out = analyze(edges, pokes)
    mem, facts, stats = out['mem'], out['facts'], out['stats']

    frozen = json.loads((HERE / 'inputs_completion.json').read_text(encoding='ascii'))
    want = [(r['side'], int(r['addr'], 16), r['kind']) for r in frozen['expected_sequence']]
    got = [(o['side'], o['addr'], o['kind']) for o in facts['accepts']]
    if got != want:
        for i, (g, w) in enumerate(zip(got, want)):
            if g != w:
                fail('accept %d is %s, the frozen sequence says %s'
                     % (i, g, w))
        fail('the trace accepted %d requests, the frozen sequence has %d'
             % (len(got), len(want)))
    for op, row in zip(facts['accepts'], frozen['expected_sequence']):
        if op['ep'] != row['epoch']:
            fail('accept of %08x landed in epoch %d, expected %d'
                 % (op['addr'], op['ep'], row['epoch']))
    cam = frozen['windows']['camera']
    pp = frozen['windows']['preprocess']
    if (int(cam[0], 16), int(cam[1], 16)) != (CAM_LO, CAM_HI):
        fail('the frozen camera window does not match the bridge decode')
    if (int(pp[0], 16), int(pp[1], 16)) != (PP_LO, PP_HI):
        fail('the frozen preprocess window does not match the bridge decode')

    dump = {}
    for line in (rundir / 'completion.mem.log').read_text(encoding='ascii').splitlines():
        w = line.split()
        dump[int(w[0])] = w[1]
    for i in range(mem.nbeat):
        want = int.from_bytes(mem.beats[i], 'little')
        if int(dump[i], 16) != want:
            fail('final memory beat %d differs from the reference' % i)

    for ep, s in sorted(stats.items()):
        if s['reset_rsp'] and ep not in (1, 2):
            fail('epoch %d counted %d responses on reset edges' % (ep, s['reset_rsp']))

    return dict(status='PASS', edges=len(edges),
                episodes={str(k): v for k, v in sorted(stats.items())},
                gates=out['gates'],
                accepts=len(facts['accepts']), responses=len(facts['resps']),
                cancels=[(n, side, '%08x' % op['addr']) for n, side, op in facts['cancels']],
                ars=[(n, side, '%08x' % line) for n, side, line, op in facts['ars']],
                marks=marks)


# ---------------------------------------------------------------- mode: legacy
def load_plan(path):
    toks = []
    for line in Path(path).read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w or w[0] != 'TOK':
            continue
        toks.append(dict(idx=int(w[1]), kind=w[2], addr=int(w[3], 16),
                         data=int(w[4], 16), strb=int(w[5], 16), size=int(w[6]),
                         wmode=int(w[7]), warg=int(w[8]), grp=int(w[9]), scen=w[10]))
    if not toks:
        fail('legacy plan is empty')
    return toks


def legacy_replay(plan, edges, mem, pokes):
    """Frozen copy of the original expected-value replay (stores included)."""
    ic, dc = Cache(), Cache()
    wb = None
    pend_i, pend_d = [], []
    read_inflight = 0
    read_op = None
    ar_hold = None
    aw_hold = None
    i_tokens = [t for t in plan if t['kind'] == 'I']
    d_tokens = [t for t in plan if t['kind'] in ('D', 'W')]
    ci = cd = 0
    resp_edge, accept_edge = {}, {}
    cancels, ar_log, aw_log = [], [], []
    stats = dict(accepts=0, responses=0, cancels=0, ar=0, aw=0, w=0)

    for e in edges:
        n = e['n']
        for (pa, pd, ps) in (pokes or {}).get(n, ()):
            mem.poke(pa, pd, ps)
        if num(e, 'rst') == 0 or num(e, 'init') == 0:
            if bit(e, 'iv') and bit(e, 'ir') or bit(e, 'dv') and bit(e, 'dr'):
                fail('legacy edge %d accepted a request on reset' % n)
            for p in pend_i + pend_d:
                cancels.append((n, p['scen'], p['side']))
            stats['cancels'] += len(pend_i) + len(pend_d)
            pend_i, pend_d = [], []
            read_inflight = 0
            read_op = None
            wb = None
            ar_hold = None
            ic.clear()
            dc.clear()
            continue

        if bit(e, 'ip'):
            if not pend_i:
                fail('legacy edge %d: I response without a request' % n)
            p = pend_i.pop(0)
            if p['kind'] == 'hit':
                if n != p['accept'] + 1:
                    fail('legacy %s: I hit response edge %d != accept+1' % (p['scen'], n))
                if num(e, 'id') != p['data']:
                    fail('legacy %s: I hit data mismatch at edge %d' % (p['scen'], n))
            else:
                if p['r_edge'] is None or n != p['r_edge'] + 1:
                    fail('legacy %s: I miss response not R+1' % p['scen'])
                if num(e, 'id') != p['data']:
                    fail('legacy %s: I miss data mismatch' % p['scen'])
            resp_edge[p['idx']] = n
            stats['responses'] += 1
        elif pend_i and pend_i[0]['kind'] == 'hit' and n > pend_i[0]['accept'] + 1:
            fail('legacy %s: I hit response missing' % pend_i[0]['scen'])

        if bit(e, 'dp'):
            if not pend_d:
                fail('legacy edge %d: D response without a request' % n)
            p = pend_d.pop(0)
            if p['kind'] == 'store':
                if n not in (p['accept'] + 1, p['accept'] + 2):
                    fail('legacy %s: store ack edge out of range' % p['scen'])
            elif p['kind'] == 'hit':
                if n != p['accept'] + 1:
                    fail('legacy %s: D hit response edge %d != accept+1' % (p['scen'], n))
                if num(e, 'dd') != p['data']:
                    fail('legacy %s: D hit data mismatch at edge %d' % (p['scen'], n))
            else:
                if p['r_edge'] is None or n != p['r_edge'] + 1:
                    fail('legacy %s: D miss response not R+1' % p['scen'])
                if num(e, 'dd') != p['data']:
                    fail('legacy %s: D miss data mismatch at edge %d' % (p['scen'], n))
            resp_edge[p['idx']] = n
            stats['responses'] += 1
        elif pend_d and pend_d[0]['kind'] in ('hit', 'store') and n > pend_d[0]['accept'] + 2:
            fail('legacy %s: D response missing' % pend_d[0]['scen'])

        arv, arr = bit(e, 'arv'), bit(e, 'arr')
        if ar_hold is not None:
            if not arv:
                fail('legacy edge %d: AR withdrawn before acceptance' % n)
            if (num(e, 'ara'), num(e, 'ari')) != ar_hold:
                fail('legacy edge %d: AR fields changed under backpressure' % n)
        if arv and not arr:
            ar_hold = (num(e, 'ara'), num(e, 'ari'))
        if arv and arr:
            ar_hold = None
            if num(e, 'ara') & 7:
                fail('legacy edge %d: AR misaligned' % n)
            if read_inflight:
                fail('legacy edge %d: second physical read in flight' % n)
            read_inflight = 1
            line = (num(e, 'ara') >> 3) << 5
            cand = [p for p in pend_i + pend_d
                    if p['kind'] == 'miss' and p['ar_edge'] is None
                    and (p['addr'] & ~31) == line]
            if len(cand) != 1:
                fail('legacy edge %d: AR %08x matches %d pending misses'
                     % (n, line, len(cand)))
            read_op = cand[0]
            read_op['ar_edge'] = n
            read_op['line'] = line
            ar_log.append((n, line, read_op['scen']))
            stats['ar'] += 1
        if bit(e, 'rv'):
            if not read_inflight or read_op is None:
                fail('legacy edge %d: R without an accepted read' % n)
            if num(e, 'rid') != (1 if read_op['side'] == 'D' else 0):
                fail('legacy edge %d: R id does not match the owner' % n)
            beat = mem.beat(read_op['line'])
            if num(e, 'rdv').to_bytes(32, 'little') != beat:
                fail('legacy %s: R beat mismatch at edge %d' % (read_op['scen'], n))
            lane = (read_op['addr'] >> 2) & 7
            read_op['data'] = int.from_bytes(beat[lane * 4:lane * 4 + 4], 'little')
            read_op['r_edge'] = n
            read_op['kind'] = 'miss'
            if read_op['side'] == 'I':
                if not uncached_broad(read_op['line']):
                    ic.fill(read_op['line'], beat)
            else:
                if not uncached_broad(read_op['line']):
                    dc.fill(read_op['line'], beat)
            read_inflight = 0
            read_op = None

        if bit(e, 'awv') and not bit(e, 'awr'):
            aw_hold = (num(e, 'awa'), num(e, 'wdv'), num(e, 'wsv'))
        if bit(e, 'awv') and bit(e, 'awr'):
            aw_hold = None
            if num(e, 'awa') & 7:
                fail('legacy edge %d: AW misaligned' % n)
            if num(e, 'awl') != 0:
                fail('legacy edge %d: AW length is not zero' % n)
            aw_log.append(dict(edge=n, addr=(num(e, 'awa') >> 3) << 5,
                               wdata=num(e, 'wdv'), wstrb=num(e, 'wsv'),
                               pending=wb))
            stats['aw'] += 1
        if bit(e, 'wrdy'):
            if not aw_log or aw_log[-1].get('done'):
                fail('legacy edge %d: W without an open AW' % n)
            cur = aw_log[-1]
            cur['done'] = True
            if cur['wdata'] != num(e, 'wdv') or cur['wstrb'] != num(e, 'wsv'):
                fail('legacy edge %d: W data/strobe differ from the accepted AW' % n)
            if cur['pending'] is not None:
                st = cur['pending']
                shift = st['addr'] & 31
                if cur['addr'] != (st['addr'] & ~31):
                    fail('legacy %s: store AW is not the line of the address' % st['scen'])
                if cur['wstrb'] != (st['wstrb'] << shift) & 0xFFFFFFFF:
                    fail('legacy %s: store byte strobe is wrong' % st['scen'])
                if cur['wdata'] != (st['wdata'] << (8 * shift)) & ((1 << 256) - 1):
                    fail('legacy %s: store data lane placement is wrong' % st['scen'])
            mem.write_beat(cur['addr'], cur['wdata'], cur['wstrb'])
            if cur['pending'] is not None:
                st = cur['pending']
                if st['hit'] and dc.hit(st['addr']):
                    dc.poke_bytes(st['addr'], st['wdata'], st['wstrb'])
            stats['w'] += 1

        if bit(e, 'iv') and bit(e, 'ir'):
            if ci >= len(i_tokens):
                fail('legacy edge %d: unexpected I accept' % n)
            t = i_tokens[ci]
            if t['addr'] != num(e, 'ia'):
                fail('legacy edge %d: I accept %08x != plan %08x'
                     % (n, num(e, 'ia'), t['addr']))
            ci += 1
            accept_edge[t['idx']] = n
            stats['accepts'] += 1
            if ic.hit(t['addr']):
                p = dict(tok=t, idx=t['idx'], side='I', kind='hit',
                         data=ic.word(t['addr']), accept=n, addr=t['addr'],
                         scen=t['scen'], r_edge=None, ar_edge=None, line=None)
            else:
                p = dict(tok=t, idx=t['idx'], side='I', kind='miss', data=None,
                         accept=n, addr=t['addr'], scen=t['scen'], r_edge=None,
                         ar_edge=None, line=None)
            pend_i.append(p)

        if bit(e, 'dv') and bit(e, 'dr'):
            if cd >= len(d_tokens):
                fail('legacy edge %d: unexpected D accept' % n)
            t = d_tokens[cd]
            if t['addr'] != num(e, 'da'):
                fail('legacy edge %d: D accept %08x != plan %08x'
                     % (n, num(e, 'da'), t['addr']))
            cd += 1
            accept_edge[t['idx']] = n
            stats['accepts'] += 1
            if t['kind'] == 'W':
                unc = uncached_broad(t['addr'])
                hit_line = (not unc) and dc.hit(t['addr'])
                wb = dict(addr=t['addr'], lane=(t['addr'] >> 2) & 7, wdata=t['data'],
                          wstrb=t['strb'], hit=hit_line, scen=t['scen'])
                if not unc and ic.hit(t['addr']):
                    ic.valid[ic.idx(t['addr'])] = False
                pend_d.append(dict(tok=t, idx=t['idx'], side='D', kind='store',
                                   data=None, accept=n, addr=t['addr'], scen=t['scen'],
                                   r_edge=None, ar_edge=None, line=None))
            else:
                unc = uncached_broad(t['addr'])
                if (not unc) and dc.hit(t['addr']):
                    data = dc.word(t['addr'])
                    if wb is not None and (wb['addr'] >> 5) == (t['addr'] >> 5) and \
                            wb['lane'] == ((t['addr'] >> 2) & 7):
                        for k in range(4):
                            if (wb['wstrb'] >> k) & 1:
                                data = (data & ~(0xFF << (8 * k))) | \
                                       (((wb['wdata'] >> (8 * k)) & 0xFF) << (8 * k))
                    p = dict(tok=t, idx=t['idx'], side='D', kind='hit', data=data,
                             accept=n, addr=t['addr'], scen=t['scen'], r_edge=None,
                             ar_edge=None, line=None)
                else:
                    p = dict(tok=t, idx=t['idx'], side='D', kind='miss', data=None,
                             accept=n, addr=t['addr'], scen=t['scen'], r_edge=None,
                             ar_edge=None, line=None)
                pend_d.append(p)

    if ci != len(i_tokens) or cd != len(d_tokens):
        fail('legacy: only %d/%d I and %d/%d D tokens were accepted'
             % (ci, len(i_tokens), cd, len(d_tokens)))
    if read_inflight:
        fail('legacy: a physical read is still in flight at the end')
    if pend_i or pend_d:
        fail('legacy: an outstanding request never got a response')
    return dict(resp=resp_edge, accept=accept_edge, ar=ar_log, aw=aw_log,
                stats=stats, plan=plan)


def uncached_broad(addr):
    """Original checker's 4 MiB comparison, kept only for the frozen replay."""
    return (addr >> 22) == 0x004 or (addr >> 22) == 0x008


WANT_PERF = dict(on=(19, 20), off=(25, 26))
WRONG_PATH_STORE = 0x1140


def assert_perf(perfs):
    """Pinned expectations for the corrected completion statistic."""
    for mode in ('on', 'off'):
        p = perfs[mode]
        if p['all_done'] != max(p['d_response'], p['last_i_response']):
            fail('legacy %s: the completion point is not max(D R, last I R)' % mode)
        if p['all_done_minus_ar'] != WANT_PERF[mode][0]:
            fail('legacy %s: all-done minus D AR is %d, expected %d'
                 % (mode, p['all_done_minus_ar'], WANT_PERF[mode][0]))
        if p['all_done_minus_accept'] != WANT_PERF[mode][1]:
            fail('legacy %s: all-done minus D accept is %d, expected %d'
                 % (mode, p['all_done_minus_accept'], WANT_PERF[mode][1]))
    saved = perfs['off']['all_done_minus_ar'] - perfs['on']['all_done_minus_ar']
    if saved != 6:
        fail('legacy: saved cycles %d, expected 6' % saved)
    return saved


def legacy_mode(oldrundir):
    old = Path(oldrundir)
    manifest = json.loads((old / 'manifest.json').read_text(encoding='ascii'))
    import hashlib
    for row in manifest['files']:
        p = old / row['sealed']
        if not p.exists():
            fail('frozen copy missing: %s' % row['sealed'])
        if hashlib.sha256(p.read_bytes()).hexdigest() != row['sha256']:
            fail('frozen copy changed: %s' % row['sealed'])
    src = old / 'src/sim/cpu_inst_hit_overlap'
    plan = load_plan(src / 'plan_bridge.txt')
    base = json.loads((src / 'inputs.json').read_text(encoding='utf-8'))
    perfs = {}
    seqs = {}
    for mode in ('on', 'off'):
        edges = parse_log(old / ('bridge_%s.edges.log' % mode))
        validate_known(edges)
        pokes, _ = load_tokens(old / ('bridge_%s.tok.log' % mode))
        summ = legacy_replay(plan, edges, Mem(base['memory']['beats']), pokes)
        toks = [t for t in plan if t['scen'].startswith('perf_') and t['kind'] in ('I', 'D')]
        d = next(t for t in toks if t['scen'] == 'perf_d_miss')
        hits = [t for t in toks if t['scen'].startswith('perf_i_hit')]
        ar = [n for (n, line, scen) in summ['ar']
              if line == (d['addr'] & ~31) and n > summ['accept'][d['idx']]]
        if not ar:
            fail('legacy %s: the perf D read never issued its AR' % mode)
        d_ar = ar[0]
        d_acc = summ['accept'][d['idx']]
        d_rsp = summ['resp'][d['idx']]
        last_i = max(summ['resp'][t['idx']] for t in hits)
        perfs[mode] = dict(d_accept=d_acc, d_ar=d_ar, d_response=d_rsp,
                           last_i_response=last_i,
                           all_done=max(d_rsp, last_i),
                           all_done_minus_ar=max(d_rsp, last_i) - d_ar,
                           all_done_minus_accept=max(d_rsp, last_i) - d_acc)
        if mode == 'on':
            if last_i >= d_rsp:
                fail('legacy on: an I hit was not served inside the D miss window')
        else:
            if min(summ['accept'][t['idx']] for t in hits) < d_rsp:
                fail('legacy off: an I hit was accepted inside the D miss window')
        seqs[mode] = [(t['kind'], t['addr'], summ['accept'][t['idx']])
                      for t in plan if t['idx'] in summ['accept']]

    # fixed expectations of the corrected statistic, never taken from the trace
    saved = assert_perf(perfs)
    if [x[0:2] for x in seqs['on']] != [x[0:2] for x in seqs['off']]:
        fail('legacy: the two parameter sets did not issue the same logical requests')
    if len(seqs['on']) != len(seqs['off']):
        fail('legacy: the two parameter sets accepted different request counts')

    binding = cpu_binding(old / 'soc.edges.log')
    guard = soc_store_guard(old)
    return dict(status='PASS', perf=perfs, saved_cycles=saved,
                accepts=dict(on=len(seqs['on']), off=len(seqs['off'])),
                cpu_binding=binding, store_guard=guard,
                legacy_manifest_sha256=hashlib.sha256(
                    (old / 'manifest.json').read_bytes()).hexdigest())


def soc_store_guard(old, dump=None):
    """The young wrong-path store must never reach the bus or the DDR image."""
    old = Path(old)
    for line in (old / 'soc.edges.log').read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w or w[0] != 'E':
            continue
        d = dict(item.split('=', 1) for item in w[1:])
        if d['ph'] != 'PRE':
            continue
        if d['dv'] == '1' and d['dr'] == '1' and int(d['da'], 16) == WRONG_PATH_STORE:
            fail('a request for the wrong-path store address reached the D port')
        if d['awv'] == '1' and d['awr'] == '1' and (int(d['awa'], 16) << 2) == WRONG_PATH_STORE:
            fail('the wrong-path store reached the DDR write port')
    mem = Mem()
    want = int.from_bytes(mem.beat(WRONG_PATH_STORE), 'little')
    line = mem.beat_of(WRONG_PATH_STORE)
    if dump is None:
        dump = {}
        for text in (old / 'soc.mem.log').read_text(encoding='ascii').splitlines():
            w = text.split()
            dump[int(w[0])] = int(w[1], 16)
    if dump.get(line) != want:
        fail('the wrong-path store changed DDR beat %d' % line)
    return dict(addr='%08x' % WRONG_PATH_STORE, beat=line,
                word_before='%08x' % int.from_bytes(
                    mem.beat(WRONG_PATH_STORE)[(WRONG_PATH_STORE & 31):(WRONG_PATH_STORE & 31) + 4],
                    'little'),
                beat_unchanged=True)


def cpu_binding(path):
    """Bind the parallel I response 46/47 to buffer 48-61, pop 62, retire 66."""
    pre, post, fx = {}, {}, {}
    retires = []
    for line in Path(path).read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w:
            continue
        if w[0] == 'E':
            d = dict(item.split('=', 1) for item in w[1:])
            (pre if d['ph'] == 'PRE' else post)[int(d['n'])] = d
        elif w[0] == 'F':
            d = dict(item.split('=', 1) for item in w[1:])
            if d['ph'] == 'PRE':
                fx[int(d['n'])] = d
        elif w[0] == 'R':
            retires.append(dict(item.split('=', 1) for item in w[1:]))
    if not fx:
        fail('CPU binding: no front-end records in %s' % path)
    fe = pre

    acc = [n for n, d in fe.items()
           if d['iv'] == '1' and d['ir'] == '1' and int(d['ia'], 16) == 0x24]
    if not acc or acc[0] != 46:
        fail('CPU binding: first I accept of 0x24 is %s, expected 46'
             % (acc[0] if acc else None))
    dacc = [n for n, d in fe.items()
            if d['dv'] == '1' and d['dr'] == '1' and d['dw'] == '0'
            and n < 46]
    if not dacc:
        fail('CPU binding: no D read accepted before the I accept')
    if fe[47]['ip'] != '1':
        fail('CPU binding: no I response on edge 47')
    if fe[47]['id'] != '02008093':
        fail('CPU binding: edge 47 did not return the fetched word')
    for n in range(48, 62):
        d = fx[n]
        if d['bufv'] != '1' or d['bufp'] != '40000024':
            fail('CPU binding: edge %d does not hold 0x40000024 (bufv=%s bufp=%s)'
                 % (n, d['bufv'], d['bufp']))
    if fx[62]['pop'] != '1' or fx[62]['bufv'] != '1':
        fail('CPU binding: edge 62 is not the pop of the held entry')
    pops = [n for n, d in fx.items() if d['pop'] == '1' and d['bufp'] == '40000024']
    if pops[0] != 62:
        fail('CPU binding: the held entry was first popped at %d, expected 62' % pops[0])
    if len(pops) != len(acc):
        fail('CPU binding: %d pops but %d accepts of the same PC' % (len(pops), len(acc)))
    for a, p in zip(acc, pops):
        if p <= a:
            fail('CPU binding: pop %d does not follow accept %d' % (p, a))
    ret = [r for r in retires if r['pc'] == '40000024' and r['ep'] == '1']
    if not ret or int(ret[0]['n']) != 66:
        fail('CPU binding: first retire of 0x40000024 is %s, expected 66'
             % (ret[0]['n'] if ret else None))
    r = ret[0]
    if r['inst'] != '02008093' or r['we'] != '1' or r['rd'] != '01':
        fail('CPU binding: retire 66 is not the addi of the fetched word')
    return dict(i_accept=46, i_response=47, buffer_hold=[48, 61], pop=62,
                retire=66, d_accept=dacc[-1], inst=r['inst'], wdata=r['wd'],
                accepts=len(acc), pops=len(pops))


# ---------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('mode', choices=('completion', 'legacy', 'selftest'))
    ap.add_argument('rundir', nargs='?')
    ap.add_argument('--selftest-only', action='store_true')
    a = ap.parse_args()
    if a.mode == 'completion':
        print(json.dumps(run_completion(a.rundir), indent=2))
    elif a.mode == 'legacy':
        print(json.dumps(legacy_mode(a.rundir), indent=2))
    else:
        import selftest_completion
        selftest_completion.main(a.rundir)
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except CheckError as exc:
        print('CHECK: FAIL %s' % exc)
        sys.exit(1)
