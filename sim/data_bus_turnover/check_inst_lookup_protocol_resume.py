"""Independent edge-level reference for the Task032 protocol-resume group B.

The trace is written by tb_inst_lookup_protocol_resume.sv: one "E ..." snapshot per
posedge, plus SCEN/TOK/BUS markers and a SUM summary. This checker:

  * owns the stimulus plan (PLAN) and derives the expected accepts / responses /
    cancels from that plan alone - never from the trace, never from DUT internals;
  * replays the trace edge by edge as whole groups: the CPU responses are checked
    against the byte memory and cache as they were BEFORE the edge, then the DDR
    command handshakes and R beats, then the same-edge write bytes, fills and
    invalidations, and only then the requests this edge accepts;
  * keeps its own byte memory (initialised exactly like the testbench), its own I/D
    cache model, an address/lane model and a per-token state machine;
  * rejects a token accepted twice, a token both responded and cancelled, a response
    without an owner, overlapping owners, a beat that disagrees with the independent
    memory, and any trace whose coverage or conservation disagrees with the plan.
"""
from pathlib import Path

ROWS = 64
T_I, T_D = 0, 1


# --------------------------------------------------------------------------- plan
def _build_plan():
    """The stimulus plan in the exact order the testbench drives it."""
    plan = []

    def add(scen, target, addr, write=0, size=2, wdata=0, wstrb=0, cancel=False):
        plan.append(dict(id=len(plan), scen=scen, target=target, addr=addr, write=write,
                         size=size, wdata=wdata, wstrb=wstrb, cancel=cancel))

    add(1, T_I, 0x40000000)
    add(1, T_I, 0x40000000)

    add(2, T_I, 0x40000040)
    for i in range(8):
        add(2, T_I, 0x40000040 + i * 4)

    add(3, T_I, 0x40000100)
    add(4, T_I, 0x40000140)
    add(4, T_I, 0x40000150)
    add(4, T_I, 0x40000144)
    add(5, T_I, 0x40000180)
    add(5, T_I, 0x40000200)
    add(6, T_I, 0x40000240)
    add(6, T_I, 0x40000244)
    add(7, T_I, 0x40000280)
    add(7, T_D, 0x40000280)
    add(8, T_D, 0x400002c0)
    add(8, T_I, 0x400002c0)

    add(9, T_D, 0x40000300, write=1, wdata=0x11223344, wstrb=0xf)
    add(9, T_I, 0x40000000)
    add(9, T_I, 0x40000340)
    add(10, T_D, 0x40000380, write=1, wdata=0x55667788, wstrb=0xf)
    add(10, T_I, 0x40000000)
    add(10, T_I, 0x400003c0)
    add(11, T_D, 0x40000400, write=1, wdata=0x99aabbcc, wstrb=0xf)
    add(11, T_I, 0x40000000)
    add(11, T_I, 0x40000408)

    add(12, T_I, 0x40000040)
    add(12, T_I, 0x40000040)
    add(12, T_D, 0x40000040, write=1, wdata=0xdeadbeef, wstrb=0xf)

    add(13, T_D, 0x40000440, write=1, wdata=0x0badf00d, wstrb=0xf)
    add(13, T_I, 0x40000440)

    add(15, T_I, 0x40000000, cancel=True)
    add(15, T_I, 0x40000000)
    add(16, T_I, 0x40000480, cancel=True)
    add(16, T_I, 0x40000480)
    add(17, T_I, 0x400004c0, cancel=True)
    add(17, T_I, 0x400004c0)
    return plan


PLAN = _build_plan()
SCENARIOS = 17


def plan_summary():
    cancels = [t['id'] for t in PLAN if t['cancel']]
    return dict(scenarios=SCENARIOS, tokens=len(PLAN), accepts=len(PLAN),
                responses=len(PLAN) - len(cancels), cancels=len(cancels),
                resets=len(cancels), planned_cancel_ids=cancels)


# ------------------------------------------------------------------- byte memory
def dm_init():
    return [((i & 0xFF) * 0x2B + 0x5A) & 0xFF for i in range(4096)]


def line_index(addr):
    return (addr >> 5) & 63


def lane_of(addr):
    return (addr >> 2) & 7


def line_base(addr):
    # CPU byte address -> DDR user line base: user address is (addr - DDR base) >> 2
    # in 16-bit words, and a cache line is 32 bytes (8 user addresses).
    return (((addr - 0x40000000) & 0x1FFFFFFF) >> 5) << 3


def beat_from(dm, araddr):
    return [dm[(araddr * 4 + k) & 4095] for k in range(32)]


def word_of(bs, lane):
    return sum(bs[lane * 4 + j] << (8 * j) for j in range(4))


class Cache:
    def __init__(self):
        self.valid = [False] * ROWS
        self.tag = [0] * ROWS
        self.lanes = [[0] * 8 for _ in range(ROWS)]

    def hit(self, addr):
        i = line_index(addr)
        return self.valid[i] and self.tag[i] == (addr >> 5)

    def word(self, addr):
        return self.lanes[line_index(addr)][lane_of(addr)]

    def fill(self, addr, bs):
        i = line_index(addr)
        self.valid[i] = True
        self.tag[i] = addr >> 5
        self.lanes[i] = [word_of(bs, lane) for lane in range(8)]

    def reset(self):
        # SoC reset clears every valid bit in the bridge line buffers.
        self.valid = [False] * ROWS
        self.tag = [0] * ROWS
        self.lanes = [[0] * 8 for _ in range(ROWS)]

    def invalidate(self, addr):
        i = line_index(addr)
        if self.valid[i] and self.tag[i] == (addr >> 5):
            self.valid[i] = False

    def store(self, addr, data, strobe):
        i = line_index(addr)
        if self.valid[i] and self.tag[i] == (addr >> 5):
            mask = 0
            for b in range(4):
                if strobe >> b & 1:
                    mask |= 0xFF << (8 * b)
            lane = lane_of(addr)
            self.lanes[i][lane] = (self.lanes[i][lane] & ~mask) | (data & mask)


# ------------------------------------------------------------------------ parsing
def read(path):
    return Path(path).read_text(encoding='utf-8').replace('\r\n', '\n')


def parse_edges(path):
    edges, scen_order, toks, sums = [], [], [], None
    for row in read(path).splitlines():
        if not row.strip():
            continue
        f = row.split()
        if f[0] == 'E':
            assert len(f) == 34, 'edge record width'
            edges.append(dict(
                edge=int(f[1]), scen=int(f[2]), resetn=int(f[3]), init=int(f[4]),
                i_v=int(f[5]), i_r=int(f[6]), i_addr=int(f[7], 16),
                d_v=int(f[8]), d_r=int(f[9]), d_wr=int(f[10]), d_size=int(f[11]),
                d_addr=int(f[12], 16), d_wdata=int(f[13], 16), d_wstrb=int(f[14], 16),
                i_rsp=int(f[15]), i_rdata=int(f[16], 16),
                d_rsp=int(f[17]), d_rdata=int(f[18], 16),
                ar_v=int(f[19]), ar_r=int(f[20]), ar_addr=int(f[21], 16), ar_id=int(f[22]),
                aw_v=int(f[23]), aw_r=int(f[24]), aw_addr=int(f[25], 16),
                w_data=int(f[26], 16), w_strb=int(f[27], 16),
                w_r=int(f[28]), r_v=int(f[29]), r_data=int(f[30], 16), r_id=int(f[31]),
                r_last=int(f[32]), busy=int(f[33])))
        elif f[0] == 'SCEN':
            scen_order.append(int(f[1]))
        elif f[0] == 'TOK':
            toks.append(dict(edge=int(f[1]), tok=int(f[2]), kind=f[3]))
        elif f[0] == 'SUM':
            sums = dict(kv.split('=') for kv in f[1:])
        elif f[0] in ('PLAN', 'BUS'):
            continue
        else:
            raise ValueError('unknown protocol-resume record: ' + row)
    assert sums is not None, 'missing SUM record'
    assert not [l for l in read(path).splitlines() if 'RESULT: FAIL' in l]
    return edges, scen_order, toks, sums


# ------------------------------------------------------------------------- replay
def review(edge_path, plan_path=None):
    edges, scen_order, toks, sums = parse_edges(edge_path)
    plan = PLAN
    summary = plan_summary()
    initial = dm_init()
    dm = dm_init()
    ic, dc = Cache(), Cache()

    order = {T_I: [t['id'] for t in plan if t['target'] == T_I],
             T_D: [t['id'] for t in plan if t['target'] == T_D]}
    ptr = {T_I: 0, T_D: 0}
    pending = {T_I: [], T_D: []}
    state = {t['id']: 'pending' for t in plan}
    acc_edge, rsp_edge, ar_edge, beat_of, aw_edge = {}, {}, {}, {}, {}
    is_hit, hit_word = {}, {}
    read_owner = write_owner = None
    ready_blocked = busy_blocked = 0
    idle_silent = competition = 0
    lanes_seen = {}
    hit_after_miss = miss_after_hit = hit_after_hit = 0
    refetch_changed = 0
    last_rsp_kind = {T_I: None, T_D: None}

    for e in edges:
        e['i_acc'] = bool(e['i_v'] and e['i_r'] and e['resetn'])
        e['d_acc'] = bool(e['d_v'] and e['d_r'] and e['resetn'])
        e['ar_hs'] = bool(e['ar_v'] and e['ar_r'] and e['resetn'])
        e['aw_hs'] = bool(e['aw_v'] and e['aw_r'] and e['resetn'])
        # The user port has no WVALID: a write beat completes when WREADY is high and
        # the write owns the buffer, i.e. its AW was accepted earlier or is accepted on
        # this very edge (bridge RTL write_buffer_complete). Reset edges neither handshake.
        e['w_hs'] = bool(e['w_r'] and e['resetn'] and
                         (e['aw_hs'] or (write_owner is not None and write_owner in aw_edge)))
        e['r_hs'] = bool(e['r_v'] and e['resetn'])
        e['i_rsp'] = bool(e['i_rsp'] and e['resetn'])
        e['d_rsp'] = bool(e['d_rsp'] and e['resetn'])
        assert not (e['i_acc'] and e['d_acc']), 'edge %d accepts I and D together' % e['edge']
        busy_at_start = bool(pending[T_I] or pending[T_D] or read_owner is not None
                             or write_owner is not None)
        if e['resetn']:
            if e['i_rsp'] and e['d_acc']:
                competition += 1
            if e['d_rsp'] and e['i_acc']:
                competition += 1

        # ---- reset edges cancel unfinished CPU tokens only
        if not e['resetn']:
            assert not (e['ar_hs'] or e['aw_hs'] or e['w_hs'] or e['r_hs']), \
                'edge %d issues a DDR command during reset' % e['edge']
            for tgt in (T_I, T_D):
                for tid in list(pending[tgt]):
                    assert state[tid] == 'accepted'
                    assert plan[tid]['cancel'], 'token %d cancelled but not planned' % tid
                    state[tid] = 'cancelled'
                    pending[tgt].remove(tid)
            read_owner = write_owner = None
            ic.reset()
            dc.reset()
            continue

        # ---- (a) responses of the OLD owners, against the pre-edge reference
        for tgt, rsp_key, data_key, cache in ((T_I, 'i_rsp', 'i_rdata', ic),
                                              (T_D, 'd_rsp', 'd_rdata', dc)):
            if not e[rsp_key]:
                continue
            assert pending[tgt], 'edge %d %s response without an accepted owner' % (e['edge'], tgt)
            tid = pending[tgt][0]
            tok = plan[tid]
            assert state[tid] == 'accepted'
            got = e[data_key]
            if not tok['write'] and is_hit[tid]:
                assert got == hit_word[tid], \
                    'edge %d hit data %08x, reference %08x (token %d)' % (
                        e['edge'], got, hit_word[tid], tid)
                lanes_seen.setdefault(line_index(tok['addr']), set()).add(lane_of(tok['addr']))
                kind = 'hit'
                assert e['edge'] == acc_edge[tid] + 1, 'hit token %d responded late' % tid
            elif tok['write']:
                # posted store ACK: ownership confirmation, rdata is not a read result
                kind = 'store'
                assert e['edge'] == acc_edge[tid] + 1, 'store token %d acked late' % tid
            else:
                assert tid in ar_edge, 'edge %d miss response without an AR (token %d)' % (e['edge'], tid)
                assert tid in beat_of, 'edge %d miss response without an R beat (token %d)' % (e['edge'], tid)
                bs, r_edge = beat_of[tid]
                assert got == word_of(bs, lane_of(tok['addr'])), \
                    'edge %d miss data %08x, beat %08x (token %d)' % (
                        e['edge'], got, word_of(bs, lane_of(tok['addr'])), tid)
                kind = 'miss'
                assert e['edge'] == r_edge + 1 or e['edge'] == ar_edge[tid] + 1, \
                    'miss token %d responded at the wrong edge' % tid
                if word_of(bs, lane_of(tok['addr'])) != word_of(
                        beat_from(initial, line_base(tok['addr'])), lane_of(tok['addr'])):
                    refetch_changed += 1
            if kind == 'hit':
                if last_rsp_kind[tgt] == 'miss':
                    hit_after_miss += 1
                elif last_rsp_kind[tgt] == 'hit':
                    hit_after_hit += 1
            elif kind == 'miss' and last_rsp_kind[tgt] == 'hit':
                miss_after_hit += 1
            last_rsp_kind[tgt] = kind
            state[tid] = 'responded'
            rsp_edge[tid] = e['edge']
            pending[tgt].remove(tid)
            if tid == read_owner:
                read_owner = None

        # ---- (b) DDR command handshakes and beats
        if e['ar_hs']:
            assert read_owner is not None, 'edge %d AR without an owner' % e['edge']
            tok = plan[read_owner]
            assert not is_hit[read_owner], 'AR issued for a cached line'
            assert e['ar_addr'] == line_base(tok['addr']), \
                'edge %d AR address %08x, owner %08x' % (e['edge'], e['ar_addr'], tok['addr'])
            assert e['ar_id'] == (0 if tok['target'] == T_I else 1), 'AR id/owner mismatch'
            assert read_owner not in ar_edge, 'token %d issued two ARs' % read_owner
            ar_edge[read_owner] = e['edge']
        if e['r_hs']:
            assert read_owner is not None, 'edge %d R without an outstanding AR' % e['edge']
            tok = plan[read_owner]
            assert e['r_id'] == (0 if tok['target'] == T_I else 1), 'R id/owner mismatch'
            assert e['r_last'] == 1, 'the single beat must be last'
            assert read_owner in ar_edge, 'R without a preceding AR'
            bs = [(e['r_data'] >> (8 * k)) & 0xFF for k in range(32)]
            assert bs == beat_from(dm, e['ar_addr']), \
                'edge %d R beat disagrees with the independent memory' % e['edge']
            beat_of[read_owner] = (bs, e['edge'])
            (ic if tok['target'] == T_I else dc).fill(tok['addr'], bs)
            e['_beat'] = bs
        if e['aw_hs']:
            assert write_owner is not None, 'edge %d AW without an owner' % e['edge']
            assert write_owner not in aw_edge, 'token %d issued two AWs' % write_owner
            assert e['aw_addr'] == line_base(plan[write_owner]['addr']), 'AW address/owner mismatch'
            aw_edge[write_owner] = e['edge']
        if e['w_hs']:
            assert write_owner is not None, 'edge %d W without an owner' % e['edge']
            tok = plan[write_owner]
            assert e['aw_addr'] == line_base(tok['addr']), 'W beat belongs to another owner'
            for lane in range(8):
                for j in range(4):
                    if e['w_strb'] >> (lane * 4 + j) & 1:
                        dm[(e['aw_addr'] * 4 + lane * 4 + j) & 4095] = \
                            (e['w_data'] >> (lane * 32 + j * 8)) & 0xFF
            dc.store(tok['addr'], tok['wdata'], tok['wstrb'])
            state[tok['id']] = 'written'
            write_owner = None

        # ---- (c) this edge's new accepts
        if e['i_acc']:
            assert ptr[T_I] < len(order[T_I]), 'unplanned I accept'
            tid = order[T_I][ptr[T_I]]
            assert plan[tid]['target'] == T_I
            assert plan[tid]['addr'] == e['i_addr'], \
                'edge %d I accept %08x, plan %08x (token %d)' % (e['edge'], e['i_addr'], plan[tid]['addr'], tid)
            assert state[tid] == 'pending', 'token %d accepted twice' % tid
            state[tid] = 'accepted'
            acc_edge[tid] = e['edge']
            pending[T_I].append(tid)
            ptr[T_I] += 1
            is_hit[tid] = ic.hit(e['i_addr'])
            if is_hit[tid]:
                hit_word[tid] = ic.word(e['i_addr'])
            else:
                read_owner = tid
        if e['d_acc']:
            assert ptr[T_D] < len(order[T_D]), 'unplanned D accept'
            tid = order[T_D][ptr[T_D]]
            tok = plan[tid]
            assert tok['target'] == T_D
            assert tok['addr'] == e['d_addr'] and tok['write'] == e['d_wr'], \
                'edge %d D accept disagrees with the plan (token %d)' % (e['edge'], tid)
            if tok['write']:
                assert e['d_wdata'] == tok['wdata'] and e['d_wstrb'] == tok['wstrb'], \
                    'D store payload disagrees with the plan'
            assert state[tid] == 'pending', 'token %d accepted twice' % tid
            state[tid] = 'accepted'
            acc_edge[tid] = e['edge']
            pending[T_D].append(tid)
            ptr[T_D] += 1
            if tok['write']:
                write_owner = tid
                ic.invalidate(tok['addr'])
            else:
                is_hit[tid] = dc.hit(tok['addr'])
                if is_hit[tid]:
                    hit_word[tid] = dc.word(tok['addr'])
                else:
                    read_owner = tid

        # ---- (d) a miss may only be delayed by write_buffer_busy / ARREADY
        if read_owner is not None and read_owner not in ar_edge:
            if e['busy']:
                assert not e['ar_v'], 'edge %d AR raised while the write buffer is busy' % e['edge']
                busy_blocked += 1
            elif e['edge'] > acc_edge.get(read_owner, 0):
                assert e['ar_v'], 'edge %d AR eligible but not raised (token %d)' % (e['edge'], read_owner)
            if e['ar_v'] and not e['ar_r']:
                ready_blocked += 1

        # ---- (e) idle silence: nothing presented and nothing owned at edge start
        if not e['i_v'] and not e['d_v'] and not busy_at_start:
            assert not e['i_rsp'] and not e['d_rsp'] and not e['ar_v'], \
                'edge %d is idle but still drives a response/AR' % e['edge']
            idle_silent += 1

    # ------------------------------------------------------------------ conserve
    accepted = ptr[T_I] + ptr[T_D]
    assert accepted == len(plan), 'only %d of %d planned tokens were accepted' % (accepted, len(plan))
    for t in plan:
        tid = t['id']
        if t['cancel']:
            assert state[tid] == 'cancelled', 'planned cancel token %d ended %s' % (tid, state[tid])
        elif t['write']:
            assert state[tid] in ('responded', 'written'), 'store token %d ended %s' % (tid, state[tid])
        else:
            assert state[tid] == 'responded', 'read token %d ended %s' % (tid, state[tid])
    cancels = sum(1 for t in plan if state[t['id']] == 'cancelled')
    responses = sum(1 for t in plan if state[t['id']] in ('responded', 'written'))
    assert cancels == len(summary['planned_cancel_ids']) == 3, cancels
    assert responses + cancels == len(plan), (responses, cancels, len(plan))
    assert not pending[T_I] and not pending[T_D], 'outstanding CPU tokens remain'
    assert read_owner is None and write_owner is None, 'outstanding DDR owner remains'

    # ------------------------------------------------------------------ coverage
    assert max(len(v) for v in lanes_seen.values()) == 8, 'the filled line must hit in all lanes'
    assert ready_blocked >= 3, 'ARREADY back pressure was not observed (%d)' % ready_blocked
    assert busy_blocked >= 1, 'the posted-write drain boundary was not observed'
    assert competition >= 2, 'I/D same-edge competition was not observed (%d)' % competition
    assert idle_silent >= 3, 'idle valid-zero silence was not observed'
    assert hit_after_miss >= 1 and miss_after_hit >= 1 and hit_after_hit >= 1, \
        (hit_after_miss, miss_after_hit, hit_after_hit)
    assert refetch_changed >= 1, 'no refetch returned data changed by an earlier store'
    assert set(scen_order) == set(range(1, SCENARIOS + 1)), sorted(scen_order)

    kinds = {}
    for t in toks:
        kinds[t['kind']] = kinds.get(t['kind'], 0) + 1
    assert kinds.get('ACC', 0) == accepted, kinds
    assert kinds.get('RSP', 0) == responses, kinds
    assert kinds.get('CAN', 0) == cancels, kinds

    for key in ('scenarios', 'tokens', 'accepts', 'responses', 'cancels', 'resets'):
        want = summary['resets'] if key == 'resets' else summary[key]
        assert int(sums[key]) == want, 'SUM %s=%s, plan %s' % (key, sums[key], want)
    assert int(sums['mismatches']) == 0
    assert int(sums['accepts']) == int(sums['responses']) + int(sums['cancels'])
    return dict(scenarios=len(scen_order), tokens=len(plan), accepts=accepted,
                responses=responses, cancels=cancels, resets=int(sums['resets']),
                ar=int(sums['ar']), r=int(sums['r']), aw=int(sums['aw']), w=int(sums['w']),
                edges=len(edges), mismatches=0, lanes=max(len(v) for v in lanes_seen.values()),
                ready_blocked=ready_blocked, busy_blocked=busy_blocked,
                competition=competition, idle_silent=idle_silent,
                hit_after_miss=hit_after_miss, miss_after_hit=miss_after_hit,
                hit_after_hit=hit_after_hit, refetch_changed=refetch_changed,
                planned=summary)


def main():
    import sys
    edge = sys.argv[1] if len(sys.argv) > 1 else 'edge.log'
    plan = sys.argv[2] if len(sys.argv) > 2 else None
    r = review(edge, plan)
    print('RESULT: PASS inst_lookup_protocol_resume scenarios=%d tokens=%d accepts=%d '
          'responses=%d cancels=%d resets=%d ar=%d r=%d aw=%d w=%d edges=%d mismatches=0'
          % (r['scenarios'], r['tokens'], r['accepts'], r['responses'], r['cancels'],
             r['resets'], r['ar'], r['r'], r['aw'], r['w'], r['edges']))


if __name__ == '__main__':
    main()
