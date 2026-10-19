"""Task043 independent checker for the two-entry ordered posted write buffer.

Reads ONLY the bridge TB's external-pin trace and re-derives, with its own copy of
the rules, the physical AW/W, the queue order, the byte memory, the D-cache fill, the
forwarded load value and the posted ACK. No DUT internal signal is used as an
expectation.

Per-edge order (per the review): the queue/busy state sampled at the edge belongs to
the edge that is ABOUT to be applied, so

    1. front-end responses are matched against the ledger built so far,
    2. an AW handshake is attributed to the head that existed when the edge began,
    3. a W beat (with its AW already accepted or accepted on this same edge) pops it,
    4. AR/R update the read model,
    5. a CPU accept pushes the new store or load,
    6. the invariants are checked against the pre-edge snapshot.

usage:  check_wb2.py [--short] <run-dir>
"""
from pathlib import Path
import json
import sys

COLS = ('cyc rstn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata '
        'av ardy aa wdata wstrb wrdy arv ardy2 ara rv rid rlast rdata busy').split()
HEX = ('ia', 'idata', 'da', 'wd', 'ws', 'ddata', 'aa', 'wdata', 'wstrb',
       'ara', 'rdata')
SNAMES = ('cyc aw w ar r dacc drsp iacc irsp pend store_acc store_ack '
          'load_rsp inst_rsp wb_cancel fc_st fc_ld').split()

DEFAULTS = dict(Dq=32, Posted=1, Depth=2, Turnover=1, Forward=1, Ruw=1,
                Icache=1, Dcache=1, Camera=0, Preproc=0, Plane=0)


def _num(v, base):
    if v and all(ch in '0123456789abcdefABCDEF' for ch in v):
        return int(v, base), True
    return 0, False


class Cfg(object):
    def __init__(self, d):
        self.dq = int(d.get('Dq', 32))
        self.bytes = self.dq
        self.beatb = 5 if self.dq == 32 else 4
        self.lines = 64
        self.tagshift = self.beatb + 6
        self.posted = int(d.get('Posted', 1))
        self.depth = int(d.get('Depth', 2))
        self.forward = int(d.get('Forward', 1))
        self.ruw = int(d.get('Ruw', 1))
        self.dcache = int(d.get('Dcache', 1))
        self.icache = int(d.get('Icache', 1))
        self.camera = int(d.get('Camera', 0))
        self.preproc = int(d.get('Preproc', 0))
        self.plane = int(d.get('Plane', 0))

    def lane_of(self, a):
        return (a & ((1 << self.beatb) - 1)) // 4

    def uncached(self, a):
        return bool((self.camera and (a >> 22) == 0x004) or
                    (self.preproc and (a >> 16) == 0x0200))


def read_cfg(run_dir):
    p = Path(run_dir) / 'run_meta.json'
    d = dict(DEFAULTS)
    if p.exists():
        try:
            meta = json.loads(p.read_text(encoding='utf-8-sig', errors='replace'))
            d.update(meta.get('params') or {})
        except Exception:
            pass
    return Cfg(d)


def parse(path):
    edges, marks, summary, dump, init_mem, unknown = [], {}, {}, {}, {}, []
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if not line or line[0] not in 'EMPSN':
            continue
        w = line.split()
        if w[0] == 'N':
            init_mem[int(w[1])] = int(w[2], 16)
        elif w[0] == 'E':
            d, bad = {}, []
            for k, v in zip(COLS, w[1:]):
                d[k], known = _num(v, 16 if k in HEX else 10)
                if not known:
                    bad.append(k)
            d['_unknown'] = bad
            if bad:
                unknown.append([d.get('cyc'), bad])
            edges.append(d)
        elif w[0] == 'M':
            marks.setdefault(w[2], []).append(int(w[1]))
        elif w[0] == 'P':
            dump[int(w[1])] = int(w[2], 16)
        elif w[0] == 'S':
            summary = {}
            for k, v in zip(SNAMES, w[1:]):
                summary[k] = int(v)
    return edges, marks, summary, dump, init_mem, unknown


class Model(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.mem = {}
        self.dcache = {}
        self.q = []
        self.rq = []
        self.aw = self.w = self.ar = self.r = 0
        self.store_acc = self.store_ack = 0
        self.load_acc = self.load_rsp = 0
        self.i_acc = self.i_rsp = 0
        self.wb_cancel = self.wb_cancel_aw = 0
        self.fc_store = self.fc_load = 0
        self.problems = []
        self.fwd_bytes = 0
        self.hit_loads = self.miss_loads = 0

    def idx(self, a):
        return (a >> self.cfg.beatb) & (self.cfg.lines - 1)

    def tag(self, a):
        return a >> self.cfg.tagshift

    def hit(self, a):
        e = self.dcache.get(self.idx(a))
        return e is not None and e[0] == self.tag(a)

    def fill(self, line_no, beat):
        bs = self.cfg.bytes
        self.dcache[line_no & (self.cfg.lines - 1)] = (
            line_no >> 6, bytes((beat >> (8 * b)) & 0xFF for b in range(bs)))

    def line_bytes(self, a):
        if self.hit(a):
            return list(self.dcache[self.idx(a)][1])
        base = (a >> self.cfg.beatb) * self.cfg.bytes
        return [self.mem.get(base + b, 0) for b in range(self.cfg.bytes)]

    def load_word(self, a, pend):
        lane = self.cfg.lane_of(a)
        data = self.line_bytes(a)
        word = data[lane * 4:lane * 4 + 4]
        if self.cfg.forward and self.hit(a):
            for ent in pend:
                if (ent['addr'] >> self.cfg.beatb) == (a >> self.cfg.beatb) and \
                        self.cfg.lane_of(ent['addr']) == lane:
                    for b in range(4):
                        if (ent['strb'] >> b) & 1:
                            word[b] = (ent['data'] >> (8 * b)) & 0xFF
                            self.fwd_bytes += 1
        return word

    def fail(self, edge, msg):
        self.problems.append('edge %s: %s' % (edge, msg))


def beat_bytes(cfg, wdata):
    return [(wdata >> (8 * b)) & 0xFF for b in range(cfg.bytes)]


def run(path, short=False, cfg=None):
    cfg = cfg or Cfg(DEFAULTS)
    edges, marks, summary, dump, init_mem, unknown = parse(path)
    m = Model(cfg)
    gates = {}
    last_ar = None

    for line_no, val in init_mem.items():
        for b in range(cfg.bytes):
            m.mem[line_no * cfg.bytes + b] = (val >> (8 * b)) & 0xFF

    first_cyc = edges[0]['cyc'] if edges else None
    pre_reset_unknowns = 0
    for cyc, names in unknown:
        if cyc == first_cyc:
            pre_reset_unknowns += len(names)
        else:
            m.fail(cyc, 'undefined (x/z) external signals: %s' % ','.join(names))

    for e in edges:
        c = e['cyc']
        if e['rstn'] == 0:
            for ent in m.q:
                m.wb_cancel += 1
                if ent['aw_sent']:
                    m.wb_cancel_aw += 1
            for kind in m.rq:
                if kind[0] == 'ack':
                    m.fc_store += 1
                else:
                    m.fc_load += 1
            m.q = []
            m.rq = []
            m.dcache = {}
            last_ar = None
            continue

        q_pre = len(m.q)
        busy_pre = bool(e['busy'])
        head = m.q[0] if m.q else None
        e['_head_line'] = (head['addr'] >> cfg.beatb) if head else None

        # ---------- 1. front-end responses ----------
        if e['dsv']:
            if not m.rq:
                m.fail(c, 'data response without an accepted request')
            else:
                kind = m.rq.pop(0)
                if kind[0] == 'ack':
                    m.store_ack += 1
                else:
                    m.load_rsp += 1
                    got = beat_bytes(cfg, e['ddata'])[:4]
                    if got != kind[1]:
                        m.fail(c, 'load data %02x%02x%02x%02x != %02x%02x%02x%02x '
                                  '(addr %08x)' % tuple(got + kind[1] + [kind[2]]))
        if e['isv']:
            m.i_rsp += 1

        # ---------- 2. AW handshake belongs to the pre-edge head ----------
        if e['av'] and e['ardy']:
            if head is None:
                m.fail(c, 'AW handshake with an empty queue')
            else:
                m.aw += 1
                if (head['addr'] >> cfg.beatb) << 3 != e['aa']:
                    m.fail(c, 'AW address is not the head line')
                if head['aw_sent']:
                    m.fail(c, 'AW re-issued for an already accepted head')
                head['aw_sent'] = True

        # ---------- 3. physical write: only the head, one beat ----------
        if e['wrdy'] and head is not None and head['aw_sent']:
            m.w += 1
            lane = cfg.lane_of(head['addr'])
            raw = [(head['data'] >> (8 * b)) & 0xFF for b in range(4)]
            exp = [0] * cfg.bytes
            for b in range(4):
                exp[lane * 4 + b] = raw[b]
            if beat_bytes(cfg, e['wdata']) != exp:
                m.fail(c, 'W data is not the head word in lane %d' % lane)
            strobe = [(e['wstrb'] >> b) & 1 for b in range(cfg.bytes)]
            want = [0] * cfg.bytes
            for b in range(4):
                want[lane * 4 + b] = (head['strb'] >> b) & 1
            if strobe != want:
                m.fail(c, 'W strobe is not the head strobe in lane %d' % lane)
            base = (head['addr'] >> cfg.beatb) * cfg.bytes
            for b in range(cfg.bytes):
                if strobe[b]:
                    m.mem[base + b] = exp[b]
            if head['hit'] and m.hit(head['addr']):
                data = bytearray(m.dcache[m.idx(head['addr'])][1])
                for b in range(cfg.bytes):
                    if strobe[b]:
                        data[b] = exp[b]
                m.dcache[m.idx(head['addr'])] = (
                    m.dcache[m.idx(head['addr'])][0], bytes(data))
            m.q.pop(0)

        # ---------- 4. read channel ----------
        if e['arv'] and e['ardy2']:
            if q_pre:
                m.fail(c, 'AR while the queue held %d entries' % q_pre)
            m.ar += 1
            last_ar = e['ara'] >> 3
        if e['rv']:
            m.r += 1
            if last_ar is None:
                m.fail(c, 'read data without a read address')
            else:
                byte_addr = last_ar << (cfg.beatb - 3)
                if e['rid'] == 1 and (cfg.dcache == 0 or cfg.uncached(byte_addr)):
                    pass
                else:
                    m.fill(last_ar, e['rdata'])
                last_ar = None

        # ---------- 5. accepted CPU requests ----------
        if e['dv'] and e['dr']:
            if e['dw']:
                if cfg.depth < 2 and len(m.q) >= 1 and cfg.posted:
                    m.fail(c, 'a second store entered a one-entry queue')
                if cfg.depth >= 2 and len(m.q) >= 2:
                    m.fail(c, 'a third store entered a full queue')
                m.store_acc += 1
                m.q.append(dict(addr=e['da'], data=e['wd'], strb=e['ws'],
                                aw_sent=False,
                                hit=(cfg.dcache != 0) and not cfg.uncached(e['da'])
                                and m.hit(e['da'])))
                m.rq.append(('ack',))
            else:
                exp = m.load_word(e['da'], m.q)
                if cfg.dcache and not cfg.uncached(e['da']) and m.hit(e['da']):
                    m.hit_loads += 1
                else:
                    m.miss_loads += 1
                m.load_acc += 1
                m.rq.append(('ld', exp, e['da']))
        if e['iv'] and e['ir']:
            m.i_acc += 1

        # ---------- 6. invariants against the pre-edge snapshot ----------
        if cfg.posted:
            if busy_pre != (q_pre != 0):
                m.fail(c, 'busy=%d while the ledger held %d entries at the edge'
                       % (e['busy'], q_pre))
        if e['av'] and not q_pre:
            m.fail(c, 'AW sampled with an empty queue')

    # ---------- accounting ----------
    gates['store_accepts'] = m.store_acc
    gates['store_acks'] = m.store_ack
    gates['load_accepts'] = m.load_acc
    gates['load_responses'] = m.load_rsp
    gates['front_cancel_store'] = m.fc_store
    gates['front_cancel_load'] = m.fc_load
    gates['wb_cancel'] = m.wb_cancel
    gates['wb_cancel_after_aw'] = m.wb_cancel_aw
    gates['aw'] = m.aw
    gates['w'] = m.w
    gates['ar'] = m.ar
    gates['r'] = m.r
    gates['forward_byte_merges'] = m.fwd_bytes
    gates['hit_loads'] = m.hit_loads
    gates['miss_loads'] = m.miss_loads
    gates['pre_reset_unknown_fields'] = pre_reset_unknowns
    gates['summary'] = summary

    if m.store_acc != m.store_ack + m.fc_store:
        m.fail('-', 'store accepts %d != acks %d + cancelled %d'
               % (m.store_acc, m.store_ack, m.fc_store))
    if m.load_acc != m.load_rsp + m.fc_load:
        m.fail('-', 'load accepts %d != responses %d + cancelled %d'
               % (m.load_acc, m.load_rsp, m.fc_load))
    if m.aw != m.w + m.wb_cancel_aw:
        m.fail('-', 'AW %d != W %d + cancelled-after-AW %d'
               % (m.aw, m.w, m.wb_cancel_aw))
    if cfg.posted and m.store_acc != m.w + m.wb_cancel:
        m.fail('-', 'posted store accepts %d != W %d + queue-cancelled %d'
               % (m.store_acc, m.w, m.wb_cancel))

    # ---------- marker gates: real handshakes only ----------
    def window(a, b):
        return [x for x in edges if a <= x['cyc'] <= b]

    required = ['G1', 'G1_full', 'G1_release', 'G1_done', 'G2_same_edge',
                'G3_head_tail', 'G3_promotion', 'G4_completion_edge',
                'G4_head_other_line', 'G4_tail_same_line',
                'G5_no_ar', 'G5_i_park', 'G7_head_only', 'G7_after_aw',
                'G7_full_reset', 'G7_new_epoch']
    if short:
        required = ['S', 'S_done']
    for n in required:
        if n not in marks:
            m.problems.append('marker %s never reached' % n)

    if not short:
        if 'G1_full' in marks and 'G1_release' in marks:
            seg = window(marks['G1_full'][0], marks['G1_release'][0])
            gates['full_backpressure_cycles'] = sum(
                1 for x in seg if x['dv'] and not x['dr'])
        if 'G1_release' in marks and 'G1_done' in marks:
            seg = window(marks['G1_release'][0], marks['G1_done'][0])
            acc = [x for x in seg if x['dv'] and x['dr']]
            gates['third_store_accept_cyc'] = acc[0]['cyc'] if acc else None
            gates['third_store_on_w_edge'] = bool(acc and acc[0]['wrdy'])

        seg = window(marks.get('G2_same_edge', [0])[0],
                     marks.get('G2_same_edge', [0])[0] + 24) if 'G2_same_edge' in marks else []
        gates['same_edge_aw_w'] = sum(
            1 for x in seg if x['av'] and x['ardy'] and x['wrdy'])

        # A real completion-edge conflict: the head W lands while a valid same-line
        # load is held, and that load is not accepted on that edge.
        seg = window(marks.get('G4_completion_edge', [0])[0],
                     marks.get('G4_completion_edge', [0])[0] + 24) \
            if 'G4_completion_edge' in marks else []
        gates['completion_blocked_same_line'] = sum(
            1 for x in seg if x['wrdy'] and x['dv'] and not x['dr'] and
            x.get('_head_line') is not None and
            (x['da'] >> cfg.beatb) == x['_head_line'])
        gates['completion_accept_same_line'] = sum(
            1 for x in seg if x['wrdy'] and x['dv'] and x['dr'] and
            x.get('_head_line') is not None and
            (x['da'] >> cfg.beatb) == x['_head_line'])

        seg = window(marks.get('G4_head_other_line', [0])[0],
                     marks.get('G4_head_other_line', [0])[0] + 24) \
            if 'G4_head_other_line' in marks else []
        gates['other_line_accept_on_completion'] = sum(
            1 for x in seg if x['wrdy'] and x['dv'] and x['dr'] and
            x.get('_head_line') is not None and
            (x['da'] >> cfg.beatb) != x['_head_line'])

        seg = window(marks.get('G4_tail_same_line', [0])[0],
                     marks.get('G4_tail_same_line', [0])[0] + 24) \
            if 'G4_tail_same_line' in marks else []
        gates['tail_blocked_same_line'] = sum(
            1 for x in seg if x['wrdy'] and x['dv'] and not x['dr'] and
            x.get('_head_line') is not None and
            (x['da'] >> cfg.beatb) == x['_head_line'])

        # An uncached load may only be accepted once the whole queue is empty.
        seg = window(marks.get('G5_no_ar', [0])[0],
                     marks.get('G5_i_park', [0])[0]) \
            if 'G5_no_ar' in marks else []
        gates['drain_accept_while_busy'] = sum(
            1 for x in seg if x['dv'] and x['dr'] and not x['dw'] and x['busy'])
        gates['ar_while_busy'] = sum(
            1 for x in seg if x['arv'] and x['busy'])

        gates['reset_cancels'] = m.wb_cancel
        gates['reset_cancelled_after_aw'] = m.wb_cancel_aw
        if 'G7_new_epoch' in marks:
            b = marks['G7_new_epoch'][0]
            gates['new_epoch_store'] = any(x['dv'] and x['dr']
                                           for x in edges if x['cyc'] >= b)

    # ---------- final memory ----------
    if dump:
        diff = []
        for line_no, val in sorted(dump.items()):
            for b in range(cfg.bytes):
                got = (val >> (8 * b)) & 0xFF
                if m.mem.get(line_no * cfg.bytes + b, 0) != got:
                    diff.append([line_no, b, m.mem.get(line_no * cfg.bytes + b, 0), got])
        gates['dump_bytes_mismatch'] = len(diff)
        gates['dump_first_diff'] = diff[:4]
    else:
        m.fail('-', 'no final memory dump: full-memory verification impossible')
    if not init_mem:
        m.fail('-', 'no N records: the pre-load image is unknown, a load expectation '
                    'cannot be established')

    gates['unmatched_aw'] = m.aw - m.w - m.wb_cancel_aw
    gates['unmatched_ar'] = m.ar - m.r

    ok = (not m.problems)
    ok = ok and gates.get('dump_bytes_mismatch', 1) == 0
    # Every AW must end in exactly one W, unless the reset threw that entry away,
    # and every AR must end in exactly one R. This holds on both planes.
    ok = ok and gates['unmatched_aw'] == 0
    ok = ok and gates['unmatched_ar'] == 0
    if short:
        # The short reference sequence only has the ordering/forwarding scenarios,
        # so the full-plane conflict gates below are not applicable to it. Its own
        # acceptance and completion cycles are compared across depths offline.
        ok = ok and gates.get('store_accepts', 1) == gates.get('store_acks', 0) or cfg.posted == 0
    else:
        ok = ok and gates.get('third_store_on_w_edge', True)
        ok = ok and gates.get('completion_blocked_same_line', 0) > 0
        ok = ok and gates.get('completion_accept_same_line', 0) == 0
        ok = ok and gates.get('other_line_accept_on_completion', 0) > 0
        ok = ok and gates.get('tail_blocked_same_line', 0) > 0
        ok = ok and gates.get('same_edge_aw_w', 0) > 0
        ok = ok and gates.get('new_epoch_store', True)
        ok = ok and gates.get('full_backpressure_cycles', 6) >= 6
    ok = ok and gates.get('drain_accept_while_busy', 0) == 0
    ok = ok and gates.get('ar_while_busy', 0) == 0
    return dict(status='PASS' if ok else 'FAIL', cfg=vars(cfg), edges=len(edges),
                problems=m.problems[:25], gates=gates)


def main(argv):
    short = '--short' in argv
    args = [a for a in argv if not a.startswith('--')]
    if not args:
        print('usage: check_wb2.py [--short] <run-dir>')
        return 2
    run_dir = Path(args[0])
    cfg = read_cfg(run_dir)
    res = run(run_dir / 'wb2.edges.log', short=short, cfg=cfg)
    print(json.dumps(res, indent=2, default=str))
    (run_dir / ('check_%s.json' % ('short' if short else 'key'))).write_text(
        json.dumps(res, indent=2, default=str) + '\n', encoding='utf-8')
    return 0 if res['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
