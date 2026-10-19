"""Task043 independent checker for the two-entry ordered posted write buffer.

Reads ONLY the bridge TB's external-pin trace and re-derives, with its own copy of
the rules, the physical AW/W, the queue order, the byte memory, the D-cache and
I-cache fills, the forwarded load value, the posted ACK and the instruction data.
No DUT internal signal is used as an expectation.

Per-edge order: the queue/busy state sampled at the edge belongs to the edge that
is ABOUT to be applied, so

    1. front-end responses are matched against the ledger built so far,
    2. an AW handshake is attributed to the head that existed when the edge began,
    3. a W beat (with its AW already accepted or accepted on this same edge) pops it,
    4. AR/R update the read model; the RID selects which line buffer is filled,
    5. a CPU accept pushes the new store or load, or the new I lookup,
    6. the invariants are checked against the pre-edge snapshot.

Plane selection (--plane):
  key       seven posted scenarios (default)
  short     legacy short reference stimulus
  fair      fixed-backend short stimulus, compared offline across depths
  edge      remaining bridge edges (tail-only promotion, I poison, parked I, etc.)
  x16       128-bit user port minimal read/write
  noposted  x32 with POSTED_WRITE_ENABLE=0
  ruw0      DATA_READ_UNDER_WRITE_ENABLE=0

usage:  check_wb2.py [--plane NAME] <run-dir>
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

PLANES = ('key', 'short', 'fair', 'edge', 'x16', 'noposted', 'ruw0')


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
        # The bridge only instantiates the posted queue for the x32 user port.
        self.posted_active = bool(self.posted) and self.dq == 32
        self.depth = int(d.get('Depth', 2))
        self.second = self.posted_active and self.depth == 2
        self.turnover = int(d.get('Turnover', 1))
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

    def line_of(self, a):
        return a >> self.beatb


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
    n_dups, p_dups = [], []
    n_seen = set()
    for line in Path(path).read_text(encoding='utf-8', errors='replace').splitlines():
        if not line or line[0] not in 'EMPSN':
            continue
        w = line.split()
        if w[0] == 'N':
            k = int(w[1])
            if k in n_seen:
                n_dups.append(k)
            n_seen.add(k)
            init_mem[k] = int(w[2], 16)
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
            k = int(w[1])
            if k in dump:
                p_dups.append(k)
            dump[k] = int(w[2], 16)
        elif w[0] == 'S':
            summary = {}
            for k, v in zip(SNAMES, w[1:]):
                summary[k] = int(v)
    return edges, marks, summary, dump, init_mem, unknown, n_dups, p_dups


class Model(object):
    def __init__(self, cfg):
        self.cfg = cfg
        self.mem = {}
        self.dcache = {}
        self.icache = {}
        self.q = []
        self.rq = []
        self.iq = []
        self.aw = self.w = self.ar = self.r = 0
        self.store_acc = self.store_ack = 0
        self.load_acc = self.load_rsp = 0
        self.i_acc = self.i_rsp = 0
        self.wb_cancel = self.wb_cancel_aw = 0
        self.fc_store = 0
        self.fc_load = 0
        self.fc_inst = 0
        self.problems = []
        self.fwd_bytes = 0
        self.hit_loads = self.miss_loads = 0
        self.i_hits = self.i_misses = 0
        self.i_fill = self.d_fill = 0
        self.i_data_checks = 0
        self.r_owner = {0: 0, 1: 0}
        self.last_ar = None
        self.ar_owner = None
        self.last_req_owner = None
        self.rd_owners = []
        self.ar_saved_candidate = False
        self.last_w = {}
        self.blk = dict(store_capacity=0, store_turnover_wait=0,
                        load_queue_miss=0, load_hit_permit=0,
                        load_same_line_completion=0, load_ruw_disabled=0,
                        main_slot=0, init_low=0)
        self.edge_gates = dict(
            tail_only_blocked=0, same_line_blocked=0,
            i_rsp_after_store_w=0, aw_while_init_low=0, w_while_init_low=0,
            ar_while_init_low=0, aw_reissued=0, parked_ar_after_d=0,
            same_edge_ar_r=0, parked_ar_saved=0)

    def idx(self, a):
        return (a >> self.cfg.beatb) & (self.cfg.lines - 1)

    def tag(self, a):
        return a >> self.cfg.tagshift

    def dhit(self, a):
        e = self.dcache.get(self.idx(a))
        return e is not None and e[0] == self.tag(a)

    def ihit(self, a):
        e = self.icache.get(self.idx(a))
        return e is not None and e[0] == self.tag(a)

    def fill(self, cache, line_no, beat):
        bs = self.cfg.bytes
        cache[line_no & (self.cfg.lines - 1)] = (
            line_no >> 6, bytes((beat >> (8 * b)) & 0xFF for b in range(bs)))

    def line_bytes(self, a):
        if self.dhit(a):
            return list(self.dcache[self.idx(a)][1])
        base = (a >> self.cfg.beatb) * self.cfg.bytes
        return [self.mem.get(base + b, 0) for b in range(self.cfg.bytes)]

    def load_word(self, a, pend):
        lane = self.cfg.lane_of(a)
        data = self.line_bytes(a)
        word = data[lane * 4:lane * 4 + 4]
        if self.cfg.forward and self.dhit(a):
            for ent in pend:
                if (ent['addr'] >> self.cfg.beatb) == (a >> self.cfg.beatb) and \
                        self.cfg.lane_of(ent['addr']) == lane:
                    for b in range(4):
                        if (ent['strb'] >> b) & 1:
                            word[b] = (ent['data'] >> (8 * b)) & 0xFF
                            self.fwd_bytes += 1
        return word

    def mem_word(self, a):
        lane = self.cfg.lane_of(a)
        base = (a >> self.cfg.beatb) * self.cfg.bytes
        return [self.mem.get(base + lane * 4 + b, 0) for b in range(4)]

    def icache_word(self, a):
        line = self.icache[self.idx(a)][1]
        lane = self.cfg.lane_of(a)
        return list(line[lane * 4:lane * 4 + 4])

    def fail(self, edge, msg):
        self.problems.append('edge %s: %s' % (edge, msg))


def beat_bytes(cfg, wdata):
    return [(wdata >> (8 * b)) & 0xFF for b in range(cfg.bytes)]


def run(path, plane='key', cfg=None):
    cfg = cfg or Cfg(DEFAULTS)
    (edges, marks, summary, dump, init_mem, unknown,
     n_dups, p_dups) = parse(path)
    m = Model(cfg)
    gates = {}

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

    permit_prev = False
    same_line_prev = False

    for e in edges:
        c = e['cyc']
        ar_claim = False
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
            m.fc_inst += len(m.iq)
            m.q = []
            m.rq = []
            m.iq = []
            m.dcache = {}
            m.icache = {}
            m.last_ar = None
            m.ar_owner = None
            m.last_req_owner = None
            m.rd_owners = []
            permit_prev = False
            same_line_prev = False
            continue

        q_pre = len(m.q)
        busy_pre = bool(e['busy'])
        head = m.q[0] if m.q else None
        tail = m.q[1] if len(m.q) > 1 else None
        e['_head_line'] = cfg.line_of(head['addr']) if head else None
        e['_tail_line'] = cfg.line_of(tail['addr']) if tail else None
        load_line = cfg.line_of(e['da'])
        # A completion on THIS edge: WREADY plus an AW already accepted (or on this
        # edge). Used only to classify the pin-level conflict, never as a ready input.
        complete_now = bool(head and e['wrdy'] and head['aw_sent'])
        dhit_now = cfg.dcache != 0 and not cfg.uncached(e['da']) and m.dhit(e['da'])
        # An I lookup is a hit only when the line is valid and no same-edge store
        # to that line poisons it (035 rule).
        i_hit_now = (cfg.icache != 0 and not cfg.uncached(e['ia']) and
                     m.ihit(e['ia']) and
                     not (e['dv'] and e['dr'] and e['dw'] and
                          cfg.line_of(e['da']) == cfg.line_of(e['ia'])))

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
            if not m.iq:
                m.fail(c, 'instruction response without an accepted request')
            else:
                ent = m.iq.pop(0)
                kind, addr = ent['kind'], ent['addr']
                if kind == 1:
                    exp = m.icache_word(addr) if m.ihit(addr) else m.mem_word(addr)
                else:
                    exp = m.mem_word(addr)       # re-read after the drain
                got = beat_bytes(cfg, e['idata'])[:4]
                m.i_data_checks += 1
                if got != exp:
                    m.fail(c, 'instruction data %02x%02x%02x%02x != '
                              '%02x%02x%02x%02x (addr %08x kind %d)'
                           % tuple(got + exp + [addr, kind]))
                if ent['poison']:
                    wcyc = m.last_w.get(cfg.line_of(addr))
                    if wcyc is None or c <= wcyc:
                        m.fail(c, 'poisoned I lookup for %08x answered at edge %d, '
                                  'not after its store W (last W %s)'
                               % (addr, c, wcyc))
                    else:
                        m.edge_gates['i_rsp_after_store_w'] += 1
                else:
                    m.edge_gates['i_rsp_after_store_w'] += 1

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
                    m.edge_gates['aw_reissued'] += 1
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
            # D line update at completion, only when this store hit that line.
            if head['hit'] and m.dhit(head['addr']):
                data = bytearray(m.dcache[m.idx(head['addr'])][1])
                for b in range(cfg.bytes):
                    if strobe[b]:
                        data[b] = exp[b]
                m.dcache[m.idx(head['addr'])] = (
                    m.dcache[m.idx(head['addr'])][0], bytes(data))
            m.q.pop(0)
            m.last_w[cfg.line_of(head['addr'])] = c

        # ---------- 4. read channel ----------
        if e['arv'] and e['ardy2']:
            if q_pre and cfg.posted_active:
                m.fail(c, 'AR while the queue held %d entries' % q_pre)
            if m.last_ar is not None:
                m.fail(c, 'AR accepted while a read is still outstanding')
            m.ar += 1
            m.last_ar = e['ara'] >> 3
            # Expected owner of the response. Only reads that really need DDR ask
            # for an AR, and they are served in issue order, so the AR must belong
            # to the oldest such request; a same-edge acceptance that needs DDR is
            # claimed directly.
            if e['dv'] and e['dr'] and not e['dw'] and not dhit_now:
                m.ar_owner = 1
                ar_claim = True
            elif e['iv'] and e['ir'] and not i_hit_now:
                m.ar_owner = 0
                ar_claim = True
            elif getattr(m, 'rd_owners', None):
                m.ar_owner = m.rd_owners.pop(0)
            else:
                m.ar_owner = None
            if e['rv']:
                m.edge_gates['same_edge_ar_r'] += 1
            # Promoted parked miss: the AR must carry the SAVED address, which is
            # provable from the outside because the live I address was changed.
            m.ar_saved_candidate = bool((m.last_ar << cfg.beatb) == 0x2400 and
                                        e['ia'] != 0x2400)
        if e['rv']:
            m.r += 1
            if m.last_ar is None:
                m.fail(c, 'read data without a read address')
            else:
                byte_addr = m.last_ar << cfg.beatb
                owner = getattr(m, 'ar_owner', None)
                if owner is not None and e['rid'] != owner:
                    m.fail(c, 'R id %d does not belong to the request that issued '
                              'AR %08x (expected owner %d)'
                           % (e['rid'], byte_addr, owner))
                if e['rid'] == 0:
                    m.r_owner[0] += 1
                    if getattr(m, 'ar_saved_candidate', False):
                        m.edge_gates['parked_ar_saved'] += 1
                    if cfg.icache and not cfg.uncached(byte_addr):
                        m.fill(m.icache, m.last_ar, e['rdata'])
                        m.i_fill += 1
                elif e['rid'] == 1:
                    m.r_owner[1] += 1
                    if cfg.dcache and not cfg.uncached(byte_addr):
                        m.fill(m.dcache, m.last_ar, e['rdata'])
                        m.d_fill += 1
                else:
                    m.fail(c, 'read data with unknown RID %d (owner must be 0=I or 1=D)'
                           % e['rid'])
                m.last_ar = None
                m.ar_saved_candidate = False

        # ---------- 5. accepted CPU requests ----------
        if e['dv'] and e['dr']:
            if e['dw']:
                m.last_req_owner = None          # a store never owns a read slot
                if cfg.posted_active:
                    cap = 2 if cfg.second else 1
                    if len(m.q) >= cap:
                        m.fail(c, 'a store entered a full queue (%d entries)' % cap)
                m.store_acc += 1
                m.q.append(dict(addr=e['da'], data=e['wd'], strb=e['ws'],
                                aw_sent=False,
                                hit=cfg.dcache != 0 and not cfg.uncached(e['da'])
                                and m.dhit(e['da'])))
                m.rq.append(('ack',))
                # A store to a valid I line invalidates it, whatever the strobe.
                if cfg.icache and not cfg.uncached(e['da']) and m.ihit(e['da']):
                    del m.icache[m.idx(e['da'])]
            else:
                exp = m.load_word(e['da'], m.q)
                if dhit_now:
                    m.hit_loads += 1
                else:
                    m.miss_loads += 1
                m.load_acc += 1
                m.last_req_owner = 1
                if not ar_claim and not dhit_now:
                    m.rd_owners.append(1)
                m.rq.append(('ld', exp, e['da']))
        if e['iv'] and e['ir']:
            m.i_acc += 1
            m.last_req_owner = 0
            if not ar_claim and not i_hit_now:
                m.rd_owners.append(0)
            # Same-edge full-line store poisons the lookup: it must be served from
            # DDR after the write, not from the still-valid cached beat.
            poison = bool(e['dv'] and e['dr'] and e['dw'] and
                          cfg.line_of(e['da']) == cfg.line_of(e['ia']))
            hit = (cfg.icache != 0 and not cfg.uncached(e['ia']) and
                   m.ihit(e['ia']) and not poison)
            m.iq.append(dict(kind=1 if hit else 2, addr=e['ia'], cyc=c,
                             poison=poison))
            if hit:
                m.i_hits += 1
            else:
                m.i_misses += 1

        # ---------- 6. init / qualification gates ----------
        if not e['init']:
            if e['av']:
                m.edge_gates['aw_while_init_low'] += 1
            if e['wrdy'] and (e['av'] or (head and head['aw_sent'])):
                m.edge_gates['w_while_init_low'] += 1
            if e['arv']:
                m.edge_gates['ar_while_init_low'] += 1

        # ---------- 7. pre-edge invariants ----------
        if cfg.posted_active:
            if busy_pre != (q_pre != 0):
                m.fail(c, 'busy=%d while the ledger held %d entries at the edge'
                       % (e['busy'], q_pre))
        if e['av'] and not q_pre:
            m.fail(c, 'AW sampled with an empty queue')

        # ---------- 8. pin-level blocking attribution (overlapping causes) ----------
        if e['dv'] and not e['dr']:
            if not e['init']:
                m.blk['init_low'] += 1
            elif e['dw']:
                if cfg.posted_active and q_pre:
                    cap = 2 if cfg.second else 1
                    if q_pre >= cap:
                        m.blk['store_capacity'] += 1
                    else:
                        m.blk['store_turnover_wait'] += 1
                else:
                    m.blk['main_slot'] += 1
            else:
                if cfg.posted_active and q_pre:
                    if cfg.ruw == 0:
                        m.blk['load_ruw_disabled'] += 1
                    elif not dhit_now:
                        m.blk['load_queue_miss'] += 1
                    elif permit_prev and same_line_prev and complete_now:
                        m.blk['load_same_line_completion'] += 1
                        if e['_head_line'] is not None and load_line != e['_head_line']:
                            m.edge_gates['tail_only_blocked'] += 1
                        else:
                            m.edge_gates['same_line_blocked'] += 1
                    else:
                        m.blk['load_hit_permit'] += 1
                else:
                    m.blk['main_slot'] += 1

        # Qualification snapshot for the NEXT edge, exactly like the DUT: a held
        # load registers whether it may overlap and whether it touches the queue.
        if (e['dv'] and not e['dw'] and e['busy'] and not e['dr'] and
                cfg.posted_active):
            same_line_prev = ((e['_head_line'] is not None and
                               load_line == e['_head_line']) or
                              (e['_tail_line'] is not None and
                               load_line == e['_tail_line']))
            permit_prev = bool(dhit_now and cfg.ruw and
                               (cfg.forward or not same_line_prev))
        else:
            same_line_prev = False
            permit_prev = False

    # ---------- accounting ----------
    gates['store_accepts'] = m.store_acc
    gates['store_acks'] = m.store_ack
    gates['load_accepts'] = m.load_acc
    gates['load_responses'] = m.load_rsp
    gates['inst_accepts'] = m.i_acc
    gates['inst_responses'] = m.i_rsp
    gates['front_cancel_store'] = m.fc_store
    # The TB counts both a cancelled data load and a cancelled I lookup in fc_ld, so
    # the cross-check uses the same total; the accounting below keeps them apart.
    gates['front_cancel_load'] = m.fc_load + m.fc_inst
    gates['front_cancel_inst'] = m.fc_inst
    gates['wb_cancel'] = m.wb_cancel
    gates['wb_cancel_after_aw'] = m.wb_cancel_aw
    gates['aw'] = m.aw
    gates['w'] = m.w
    gates['ar'] = m.ar
    gates['r'] = m.r
    gates['r_owner_i'] = m.r_owner[0]
    gates['r_owner_d'] = m.r_owner[1]
    gates['forward_byte_merges'] = m.fwd_bytes
    gates['hit_loads'] = m.hit_loads
    gates['miss_loads'] = m.miss_loads
    gates['i_hits'] = m.i_hits
    gates['i_misses'] = m.i_misses
    gates['i_fills'] = m.i_fill
    gates['d_fills'] = m.d_fill
    gates['i_data_checks'] = m.i_data_checks
    gates['blocking'] = m.blk
    gates['edge'] = m.edge_gates
    gates['n_records'] = len(init_mem)
    gates['p_records'] = len(dump)
    gates['n_duplicates'] = n_dups
    gates['p_duplicates'] = p_dups
    gates['pre_reset_unknown_fields'] = pre_reset_unknowns
    gates['summary'] = summary

    if m.store_acc != m.store_ack + m.fc_store:
        m.fail('-', 'store accepts %d != acks %d + cancelled %d'
               % (m.store_acc, m.store_ack, m.fc_store))
    if m.load_acc != m.load_rsp + m.fc_load:
        m.fail('-', 'load accepts %d != responses %d + cancelled %d'
               % (m.load_acc, m.load_rsp, m.fc_load))
    if m.i_acc != m.i_rsp + m.fc_inst:
        m.fail('-', 'I accepts %d != I responses %d + cancelled %d'
               % (m.i_acc, m.i_rsp, m.fc_inst))
    if m.aw != m.w + m.wb_cancel_aw:
        m.fail('-', 'AW %d != W %d + cancelled-after-AW %d'
               % (m.aw, m.w, m.wb_cancel_aw))
    if cfg.posted_active and m.store_acc != m.w + m.wb_cancel:
        m.fail('-', 'posted store accepts %d != W %d + queue-cancelled %d'
               % (m.store_acc, m.w, m.wb_cancel))
    if not cfg.posted_active and m.store_acc != m.w:
        m.fail('-', 'non-posted store accepts %d != W %d' % (m.store_acc, m.w))
    if m.i_data_checks != m.i_rsp:
        m.fail('-', 'I data was checked on %d of %d responses'
               % (m.i_data_checks, m.i_rsp))
    # Every read that needed DDR must have produced exactly one AR.
    if getattr(m, 'rd_owners', []):
        m.fail('-', '%d read request(s) never issued their AR' % len(m.rd_owners))

    # ---------- trace/summary cross-check ----------
    if not summary:
        m.fail('-', 'no S record: the trace summary is missing')
    else:
        pairs = [('aw', 'aw'), ('w', 'w'), ('ar', 'ar'), ('r', 'r'),
                 ('iacc', 'inst_accepts'), ('irsp', 'inst_responses'),
                 ('store_acc', 'store_accepts'), ('store_ack', 'store_acks'),
                 ('load_rsp', 'load_responses'), ('inst_rsp', 'inst_responses'),
                 ('wb_cancel', 'wb_cancel'), ('fc_st', 'front_cancel_store'),
                 ('fc_ld', 'front_cancel_load')]
        # dacc/drsp are the totals over both data request kinds.
        summary_tot = {'dacc': gates['store_accepts'] + gates['load_accepts'],
                       'drsp': gates['store_acks'] + gates['load_responses']}
        for sk, gk in pairs:
            if sk in summary and summary[sk] != gates.get(gk):
                m.fail('-', 'summary %s=%d but the checker rebuilt %d'
                       % (sk, summary[sk], gates.get(gk)))
        for sk, val in summary_tot.items():
            if sk in summary and summary[sk] != val:
                m.fail('-', 'summary %s=%d but the checker rebuilt %d'
                       % (sk, summary[sk], val))

    # ---------- marker gates: real handshakes only ----------
    def window(a, b):
        return [x for x in edges if a <= x['cyc'] <= b]

    required = {
        'key': ['G1', 'G1_full', 'G1_release', 'G1_done', 'G2_same_edge',
                'G3_head_tail', 'G3_promotion', 'G4_completion_edge',
                'G4_head_other_line', 'G4_tail_same_line',
                'G5_no_ar', 'G5_i_park', 'G7_head_only', 'G7_after_aw',
                'G7_full_reset', 'G7_new_epoch'],
        'short': ['S', 'S_done'],
        'fair': ['S2', 'S2_done'],
        'edge': ['E1_tail_only', 'E2_i_poison', 'E3_park', 'E4_ar_same_edge',
                 'E5_init_pause', 'E5_done', 'E6_partial_mask', 'E6_done',
                 'E7_rsp_turnover', 'E7_done'],
        'x16': ['X', 'X_done'],
        'noposted': ['N', 'N_done'],
        'ruw0': ['R0', 'R0_done'],
    }[plane]
    for n in required:
        if n not in marks:
            m.problems.append('marker %s never reached' % n)

    if plane == 'key':
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

        seg = window(marks.get('G5_no_ar', [0])[0],
                     marks.get('G5_i_park', [0])[0]) if 'G5_no_ar' in marks else []
        gates['drain_accept_while_busy'] = sum(
            1 for x in seg if x['dv'] and x['dr'] and not x['dw'] and x['busy'])
        gates['ar_while_busy'] = sum(1 for x in seg if x['arv'] and x['busy'])

        gates['reset_cancels'] = m.wb_cancel
        gates['reset_cancelled_after_aw'] = m.wb_cancel_aw
        if 'G7_new_epoch' in marks:
            b = marks['G7_new_epoch'][0]
            gates['new_epoch_store'] = any(x['dv'] and x['dr']
                                           for x in edges if x['cyc'] >= b)

    if plane == 'edge':
        seg = window(marks.get('E5_init_pause', [0])[0],
                     marks.get('E5_done', [0])[0]) if 'E5_init_pause' in marks else []
        gates['init_pause_edges'] = len(seg)
        gates['init_pause_aw'] = sum(1 for x in seg if x['av'] and x['ardy'])

    if plane == 'ruw0':
        gates['drain_accept_while_busy'] = sum(
            1 for x in edges if x['dv'] and x['dr'] and not x['dw'] and x['busy'])
        gates['ar_while_busy'] = sum(1 for x in edges if x['arv'] and x['busy'])

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
    if n_dups:
        m.fail('-', 'duplicate N records for lines %s' % n_dups[:8])
    if p_dups:
        m.fail('-', 'duplicate P records for lines %s' % p_dups[:8])
    if dump and init_mem and len(dump) != len(init_mem):
        m.fail('-', 'the final dump covers %d lines but the pre-load image %d'
               % (len(dump), len(init_mem)))

    gates['unmatched_aw'] = m.aw - m.w - m.wb_cancel_aw
    gates['unmatched_ar'] = m.ar - m.r

    ok = (not m.problems)
    checks = {
        'dump_bytes': gates.get('dump_bytes_mismatch', 1) == 0,
        'unmatched_aw': gates['unmatched_aw'] == 0,
        'unmatched_ar': gates['unmatched_ar'] == 0,
        'store_ack': m.store_acc == m.store_ack + m.fc_store,
        'load_rsp': m.load_acc == m.load_rsp + m.fc_load,
        'i_rsp': m.i_acc == m.i_rsp + (m.fc_load - (m.load_acc - m.load_rsp)),
    }
    # Explicit branch, not a chain with a trailing "or": a non-posted run must not
    # be able to mask an earlier failure with its own acceptance rule.
    if cfg.posted_active:
        checks['posted_queue'] = m.store_acc == m.w + m.wb_cancel
    else:
        checks['nonposted_queue'] = m.store_acc == m.w
    if plane == 'key':
        checks['third_store_on_w_edge'] = gates.get('third_store_on_w_edge', True)
        checks['completion_blocked'] = gates.get('completion_blocked_same_line', 0) > 0
        checks['completion_no_accept'] = gates.get('completion_accept_same_line', 0) == 0
        checks['other_line_accept'] = gates.get('other_line_accept_on_completion', 0) > 0
        checks['tail_blocked'] = gates.get('tail_blocked_same_line', 0) > 0
        checks['same_edge_aw_w'] = gates.get('same_edge_aw_w', 0) > 0
        checks['new_epoch_store'] = gates.get('new_epoch_store', True)
        checks['full_backpressure'] = gates.get('full_backpressure_cycles', 6) >= 6
        checks['drain_accept_while_busy'] = gates.get('drain_accept_while_busy', 0) == 0
        checks['ar_while_busy'] = gates.get('ar_while_busy', 0) == 0
    if plane == 'edge':
        checks['tail_only_blocked'] = gates['edge']['tail_only_blocked'] > 0
        checks['i_rsp_after_store_w'] = gates['edge']['i_rsp_after_store_w'] > 0
        checks['i_owner'] = gates['r_owner_i'] > 0
        checks['d_owner'] = gates['r_owner_d'] > 0
        checks['i_data'] = gates['i_data_checks'] == gates['inst_responses']
        checks['init_aw'] = gates['edge']['aw_while_init_low'] == 0
        checks['init_w'] = gates['edge']['w_while_init_low'] == 0
        checks['init_ar'] = gates['edge']['ar_while_init_low'] == 0
        checks['aw_reissued'] = gates['edge']['aw_reissued'] == 0
        checks['same_edge_ar_r'] = gates['edge']['same_edge_ar_r'] > 0
        checks['parked_ar_saved'] = gates['edge']['parked_ar_saved'] > 0
        checks['init_pause_aw'] = gates.get('init_pause_aw', 0) == 1
        # E6: the two complementary-mask stores must produce a forwarded load in
        # this window, and the checker's own byte model (not the TB) supplies the
        # expected word.
        if 'E6_partial_mask' in marks and 'E6_done' in marks:
            seg = window(marks['E6_partial_mask'][0], marks['E6_done'][0])
            gates['edge']['partial_mask_loads'] = sum(
                1 for x in seg if x['dsv'] and not x['dw'])
            gates['edge']['dual_pending_load_accepts'] = sum(
                1 for x in seg if x['dv'] and x['dr'] and not x['dw'] and
                x.get('_head_line') is not None and x.get('_tail_line') is not None)
        else:
            gates['edge']['partial_mask_loads'] = 0
            gates['edge']['dual_pending_load_accepts'] = 0
        checks['partial_mask_forward'] = (gates['edge']['partial_mask_loads'] >= 2 and
                                         gates['edge']['dual_pending_load_accepts'] >= 1)
        # E7: a response consumed while a younger request is accepted on the very
        # same edge.
        if 'E7_rsp_turnover' in marks and 'E7_done' in marks:
            seg = window(marks['E7_rsp_turnover'][0], marks['E7_done'][0])
            gates['edge']['rsp_turnover_same_edge'] = sum(
                1 for x in seg if x['dsv'] and x['dv'] and x['dr'])
        else:
            gates['edge']['rsp_turnover_same_edge'] = 0
        checks['rsp_turnover'] = gates['edge']['rsp_turnover_same_edge'] >= 1
    if plane == 'ruw0':
        checks['drain_accept_while_busy'] = gates.get('drain_accept_while_busy', 0) == 0
        checks['ar_while_busy'] = gates.get('ar_while_busy', 0) == 0
    if plane in ('x16', 'noposted'):
        checks['all_aw_settled'] = m.aw == m.w
    for name, cond in checks.items():
        if not cond:
            ok = False
            m.problems.append('gate %s failed' % name)
    ok = ok and all(checks.values())

    return dict(status='PASS' if ok else 'FAIL', plane=plane, cfg=vars(cfg),
                edges=len(edges), problems=m.problems[:30], gates=gates)


def main(argv):
    plane = 'key'
    args = []
    i = 0
    while i < len(argv):
        a = argv[i]
        if a == '--plane' and i + 1 < len(argv):
            plane = argv[i + 1]
            i += 2
            continue
        if a == '--short':
            plane = 'short'
            i += 1
            continue
        if a.startswith('--'):
            i += 1
            continue
        args.append(a)
        i += 1
    if plane not in PLANES:
        print('unknown plane %s (choose from %s)' % (plane, ', '.join(PLANES)))
        return 2
    if not args:
        print('usage: check_wb2.py [--plane NAME] <run-dir>')
        return 2
    run_dir = Path(args[0])
    cfg = read_cfg(run_dir)
    res = run(run_dir / 'wb2.edges.log', plane=plane, cfg=cfg)
    print(json.dumps(res, indent=2, default=str))
    (run_dir / ('check_%s.json' % plane)).write_text(
        json.dumps(res, indent=2, default=str) + '\n', encoding='utf-8')
    return 0 if res['status'] == 'PASS' else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
