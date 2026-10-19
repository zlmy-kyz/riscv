"""Independent reference/checker for the task032 group-B completion run.

Companion of ``tb_inst_lookup_protocol_completion.sv`` (tag
``ds_data_bus_inst_lookup_protocol_completion_20261014_a``).  The trace format is
byte-for-byte the one already used by the protocol-resume group E:

    E <edge> <scen> <resetn> <init> <33 interface fields...>   (one per posedge)
    SCEN <n> <name> / TOK <edge> <tok> ACC|RSP|CAN [<acc_edge>] / BUS <edge> AR|AW|W|R
    PLAN <tok_id> <scen> <tgt> <write> <addr> <size> <wdata> <wstrb>   (+PLAN_LOG)
    SUM <k=v ...>

This checker is deliberately not a copy of the testbench and not a copy of the group-E
checker's loose W handling.  What it owns and what it refuses to take from the trace:

  * the stimulus plan (``PLAN``) with, per token, id / scenario / target / write / addr /
    size / wdata / wstrb / planned_cancel **and** the declared expectation (hit, miss,
    store, cancelled-hit, cancelled-miss, cancelled-miss-with-AR).  AR/R/AW/W and the
    cancel events are therefore derived from the plan, not from the trace;
  * ``plan.log`` is really read and compared field by field against ``PLAN``; a missing
    file, a missing/extra token or any changed field fails the run (including the
    scenario field, which group E wrote as a constant 0);
  * its own byte memory, its own I/D cache model, its own address/lane model and its own
    per-token state machine;
  * the 256-bit W data and 32-bit W strobe are **derived from the CPU store plan fields**
    (addr/lane/wdata/wstrb), compared field by field with the trace's AW/W record, and
    only then is the reference memory updated from the plan fields.  The trace's w_data /
    w_strb never seed the reference memory;
  * AW only latches owner/address; the reference memory is untouched until the physical W
    completion edge (WREADY with an own or same-edge AW), and the AW address as well as
    the driven data/strobe must stay stable while the write waits;
  * a CPU posted store ACK is kept separate from the physical W completion (two terminal
    states and two conservation chains);
  * two hard coverage gates that group E never triggered: an edge where ARVALID/ARREADY and
    RVALID are all high for the same token (AR and R on the same posedge, response on the
    next edge), and an edge where I_VALID and D_VALID are high together with a D-wins
    (d_v && d_r && !i_r) case and a held, later accepted I token;
  * the SUM counters are re-derived from the raw E records (AR/R/AW/W/reset/observation
    counts) and only then compared with the SUM string; the final edge counter, the number
    of logged edges and the first edge are reported separately;
  * same-edge R/W visibility: an R beat is taken from the reference memory *before* the
    edge's write bytes are committed, and the W commit happens after.  If no edge in the
    run has an actual W and R together this is reported as not triggered instead of being
    claimed as verified.

``review()`` returns a dict with the plan/coverage counters plus the group-E coverage
statistics, and ``mismatches`` is always 0 (any mismatch raises).
"""
from hashlib import sha256
from pathlib import Path

ROWS = 64
T_I, T_D = 0, 1
DDR_BASE = 0x40000000
PLAN_VERSION = 'task032-protocol-completion-plan-v1'

SCENARIOS = 17
# Hard gates requested by the task032 completion plan.
AR_R_SAME_MIN = 2
DUAL_PRESENT_MIN = 2

SCENARIO_NAMES = (
    'cold miss delayed R then same line hit',              # 1
    'AR R same edge then all eight lanes',                 # 2
    'AR back pressure and live decoy',                     # 3
    'hit to hit different index and lane',                 # 4
    'hit to miss',                                         # 5
    'miss response then hit',                              # 6
    'I response edge with D request data priority',        # 7
    'D response edge with I request',                      # 8
    'posted write AW not accepted',                        # 9
    'AW accepted W waiting',                               # 10
    'lookup miss with write drain boundary',               # 11
    'old I hit with same edge invalidating store',         # 12
    'same line write then refetch',                        # 13
    'idle valid zero silence',                             # 14
    'reset before consuming a registered hit',             # 15
    'reset at miss AR back pressure',                      # 16
    'reset at RDATA wait',                                 # 17
)

# Token ids that must show ARVALID/ARREADY and RVALID on one and the same posedge and a
# CPU response on the very next edge: the cold I miss and the I miss that follows the
# posted-write drain.
AR_R_SAME_TOKENS = (2, 31)

EXPECTS = ('hit', 'miss', 'store', 'cancel_hit', 'cancel_miss', 'cancel_miss_ar')


# --------------------------------------------------------------------------- plan
def _build_plan():
    """The completion stimulus plan, in the exact order the testbench drives it.

    The 43 group-E tokens are preserved unchanged (same scenarios, order, addresses and
    payloads) except for one addition required by the completion plan: a non-zero-lane,
    partial-strobe store in scenario 13, so that "unstrobed bytes are preserved" is
    observed instead of only full-lane stores.
    """
    plan = []

    def add(scen, target, addr, write=0, size=2, wdata=0, wstrb=0, cancel=False,
            expect='miss'):
        assert 1 <= scen <= SCENARIOS, scen
        assert expect in EXPECTS, expect
        assert size == 2, size
        if expect == 'store':
            assert write == 1 and wstrb != 0, (write, wstrb)
        else:
            assert write == 0, write
        plan.append(dict(id=len(plan), scen=scen, target=target, addr=addr, write=write,
                         size=size, wdata=wdata, wstrb=wstrb, cancel=cancel, expect=expect))

    # 1: cold miss with delayed R, then the same line hits without AR
    add(1, T_I, 0x40000000, expect='miss')
    add(1, T_I, 0x40000000, expect='hit')
    # 2: AR/R on the same edge (cold I miss), then every lane of the filled line
    add(2, T_I, 0x40000040, expect='miss')
    for i in range(8):
        add(2, T_I, 0x40000040 + i * 4, expect='hit')
    # 3: AR back pressure and a live decoy address
    add(3, T_I, 0x40000100, expect='miss')
    # 4: hit to hit on a different index and lane
    add(4, T_I, 0x40000140, expect='miss')
    add(4, T_I, 0x40000150, expect='hit')
    add(4, T_I, 0x40000144, expect='hit')
    # 5: hit to miss
    add(5, T_I, 0x40000180, expect='miss')
    add(5, T_I, 0x40000200, expect='miss')
    # 6: miss response then hit
    add(6, T_I, 0x40000240, expect='miss')
    add(6, T_I, 0x40000244, expect='hit')
    # 7: I/D request competition on one edge, data wins
    add(7, T_I, 0x40000280, expect='miss')
    add(7, T_D, 0x40000280, expect='miss')
    # 8: D response edge also presents an I request
    add(8, T_D, 0x400002c0, expect='miss')
    add(8, T_I, 0x400002c0, expect='miss')
    # 9: posted store with AW not accepted: I hit completes, I miss waits
    add(9, T_D, 0x40000300, write=1, wdata=0x11223344, wstrb=0xf, expect='store')
    add(9, T_I, 0x40000000, expect='hit')
    add(9, T_I, 0x40000340, expect='miss')
    # 10: AW accepted, W waiting
    add(10, T_D, 0x40000380, write=1, wdata=0x55667788, wstrb=0xf, expect='store')
    add(10, T_I, 0x40000000, expect='hit')
    add(10, T_I, 0x400003c0, expect='miss')
    # 11: I miss at the posted-write drain boundary, AR/R on the same edge, the refetch
    #     must return the bytes the store already committed
    add(11, T_D, 0x40000400, write=1, wdata=0x99aabbcc, wstrb=0xf, expect='store')
    add(11, T_I, 0x40000000, expect='hit')
    add(11, T_I, 0x40000408, expect='miss')
    # 12: old I hit response on the same edge as an invalidating store
    add(12, T_I, 0x40000040, expect='hit')
    add(12, T_I, 0x40000040, expect='hit')
    add(12, T_D, 0x40000040, write=1, wdata=0xdeadbeef, wstrb=0xf, expect='store')
    # 13: full-word store, then the added non-zero-lane partial-byte store, then refetch
    add(13, T_D, 0x40000440, write=1, wdata=0x0badf00d, wstrb=0xf, expect='store')
    add(13, T_D, 0x40000444, write=1, wdata=0x01020304, wstrb=0xa, expect='store')
    add(13, T_I, 0x40000440, expect='miss')
    # 14: idle with valid zero stays silent (no token)
    # 15: reset between a hit acceptance and its response consumption
    add(15, T_I, 0x40000000, cancel=True, expect='cancel_hit')
    add(15, T_I, 0x40000000, expect='miss')
    # 16: reset while a miss can only wait for AR back pressure (no AR was issued)
    add(16, T_I, 0x40000480, cancel=True, expect='cancel_miss')
    add(16, T_I, 0x40000480, expect='miss')
    # 17: reset while an accepted AR waits for R data (AR issued, no beat)
    add(17, T_I, 0x400004c0, cancel=True, expect='cancel_miss_ar')
    add(17, T_I, 0x400004c0, expect='miss')
    # 18 is not a scenario: the plan deliberately ends after scenario 17.
    return plan


PLAN = _build_plan()
PLANNED_CANCELS = [t['id'] for t in PLAN if t['cancel']]
PLANNED_RESETS = len(PLANNED_CANCELS)


def _plan_canonical():
    """Canonical, line-oriented serialisation of the whole plan contract."""
    lines = ['PLAN-SHA256 v1', 'version ' + PLAN_VERSION,
             'scenarios %d' % SCENARIOS,
             'ar_r_same_min %d' % AR_R_SAME_MIN,
             'dual_present_min %d' % DUAL_PRESENT_MIN,
             'ar_r_same_tokens ' + ','.join(str(t) for t in AR_R_SAME_TOKENS)]
    for n, name in enumerate(SCENARIO_NAMES, start=1):
        lines.append('SCENARIO %d %s' % (n, name))
    for t in PLAN:
        lines.append('TOKEN %d %d %d %d %08x %d %08x %01x %d %s' % (
            t['id'], t['scen'], t['target'], t['write'], t['addr'], t['size'],
            t['wdata'], t['wstrb'], 1 if t['cancel'] else 0, t['expect']))
    return '\n'.join(lines) + '\n'


def plan_sha256():
    return sha256(_plan_canonical().encode('utf-8')).hexdigest()


def plan_summary():
    """The plan-side contract: counts, thresholds and the sealed plan identity."""
    ar_expected = sum(1 for t in PLAN if t['expect'] in ('miss', 'cancel_miss_ar'))
    r_expected = sum(1 for t in PLAN if t['expect'] == 'miss')
    stores = sum(1 for t in PLAN if t['expect'] == 'store')
    cancels = [t['id'] for t in PLAN if t['cancel']]
    assert PLAN_VERSION == 'task032-protocol-completion-plan-v1'
    assert len(PLAN) == 44, len(PLAN)
    assert cancels == [38, 40, 42], cancels
    assert ar_expected == 19 and r_expected == 18, (ar_expected, r_expected)
    assert stores == 6, stores
    assert set(t['scen'] for t in PLAN) == set(range(1, SCENARIOS + 1)) - {14}
    return dict(scenarios=SCENARIOS, tokens=len(PLAN), accepts=len(PLAN),
                responses=len(PLAN) - len(cancels), cancels=len(cancels),
                resets=PLANNED_RESETS, power_on_resets=1,
                ar=ar_expected, r=r_expected, aw=stores, w=stores,
                ar_r_same_min=AR_R_SAME_MIN, dual_present_min=DUAL_PRESENT_MIN,
                ar_r_same_tokens=list(AR_R_SAME_TOKENS),
                planned_cancel_ids=cancels, plan_sha256=plan_sha256())


# ------------------------------------------------------------------- byte memory
def dm_init():
    return [((i & 0xFF) * 0x2B + 0x5A) & 0xFF for i in range(4096)]


def line_index(addr):
    return (addr >> 5) & 63


def lane_of(addr):
    return (addr >> 2) & 7


def line_base(addr):
    # CPU byte address -> DDR user line base: user address is (addr - DDR base) >> 2 in
    # 16-bit words and a cache line is 32 bytes (8 user addresses).
    return (((addr - DDR_BASE) & 0x1FFFFFFF) >> 5) << 3


def beat_from(dm, araddr):
    return [dm[(araddr * 4 + k) & 4095] for k in range(32)]


def word_of(bs, lane):
    return sum(bs[lane * 4 + j] << (8 * j) for j in range(4))


def derive_write(tok):
    """The 256-bit write data and 32-bit strobe implied by the CPU store plan fields.

    The CPU store is a 32-bit word with a 4-bit byte strobe at ``tok['addr']``; the DDR
    user beat covers the 32-byte line that contains it.  Only the enabled byte lanes are
    defined by the plan; the remaining byte positions are not driven by the CPU store and
    are therefore not compared (the exact 32-bit strobe is compared strictly).
    """
    off = tok['addr'] & 0x1F
    assert off % 4 == 0, 'CPU store must be 32-bit aligned'
    strobe = 0
    bytes_at = [None] * 32
    for j in range(4):
        if (tok['wstrb'] >> j) & 1:
            strobe |= 1 << (off + j)
            bytes_at[off + j] = (tok['wdata'] >> (8 * j)) & 0xFF
    return dict(addr=line_base(tok['addr']), off=off, strobe=strobe, bytes=bytes_at)


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
    edges, scen_order, toks, sums, bus = [], [], [], None, []
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
            toks.append(dict(edge=int(f[1]), tok=int(f[2]), kind=f[3],
                             accept_edge=(int(f[4]) if len(f) > 4 else None)))
        elif f[0] == 'BUS':
            bus.append(dict(edge=int(f[1]), kind=f[2]))
        elif f[0] == 'SUM':
            sums = dict(kv.split('=') for kv in f[1:])
        elif f[0] == 'PLAN':
            continue
        else:
            raise ValueError('unknown protocol-completion record: ' + row)
    assert sums is not None, 'missing SUM record'
    assert not [l for l in read(path).splitlines() if 'RESULT: FAIL' in l]
    assert edges, 'no edge records'
    assert all(b['edge'] > a['edge'] for a, b in zip(edges, edges[1:])), \
        'edge counter is not strictly increasing'
    return edges, scen_order, toks, sums, bus


def read_plan_log(path):
    """Read the testbench's PLAN log; missing file or malformed row is fatal."""
    assert path is not None, 'plan_path is required'
    assert Path(path).is_file(), 'plan.log is missing: %s' % path
    rows = []
    for row in read(path).splitlines():
        if not row.strip():
            continue
        f = row.split()
        assert f[0] == 'PLAN', 'unexpected plan record: ' + row
        assert len(f) in (9, 10), 'PLAN record width: ' + row
        rows.append(dict(id=int(f[1]), scen=int(f[2]), target=int(f[3]), write=int(f[4]),
                         addr=int(f[5], 16), size=int(f[6]), wdata=int(f[7], 16),
                         wstrb=int(f[8], 16),
                         cancel=(int(f[9]) if len(f) == 10 else None)))
    assert rows, 'plan.log is empty'
    return rows


def compare_plan(rows):
    """PLAN log must equal the independent PLAN token by token, field by field."""
    assert len(rows) == len(PLAN), \
        'plan.log has %d tokens, PLAN has %d' % (len(rows), len(PLAN))
    for got, want in zip(rows, PLAN):
        for key in ('id', 'scen', 'target', 'write', 'addr', 'size', 'wdata', 'wstrb'):
            assert got[key] == want[key], \
                'plan.log token %d field %s=%r, PLAN=%r' % (want['id'], key, got[key],
                                                            want[key])
        if got['cancel'] is not None:
            assert bool(got['cancel']) == bool(want['cancel']), \
                'plan.log token %d planned_cancel=%r, PLAN=%r' % (
                    want['id'], got['cancel'], want['cancel'])
    # planned_cancel is not a mandatory PLAN-log column in the group-E format; when the
    # testbench prints it, it is compared above.  Either way it is bound through the
    # replay (each planned cancel must be the token the reset edges really cancel) and
    # through plan_sha256, which serialises it.
    if any(t['cancel'] is not None for t in rows):
        flagged = [t['id'] for t in rows if t['cancel']]
        assert flagged == PLANNED_CANCELS, flagged


# ------------------------------------------------------------------------- replay
def review(edge_path, plan_path=None):
    assert plan_path is not None, \
        'plan_path is required: the checker must read plan.log (missing path is fatal)'
    edges, scen_order, toks, sums, bus = parse_edges(edge_path)
    compare_plan(read_plan_log(plan_path))

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
    acc_edge, rsp_edge, cancel_edge, ar_edge, beat_of, aw_edge = {}, {}, {}, {}, {}, {}
    is_hit, hit_word = {}, {}
    acked, written = {}, {}
    aw_wait_payload = {}
    read_owner = write_owner = None
    ready_blocked = busy_blocked = 0
    idle_silent = competition = 0
    lanes_seen = {}
    hit_after_miss = miss_after_hit = hit_after_hit = 0
    refetch_changed = 0
    last_rsp_kind = {T_I: None, T_D: None}
    ar_r_same = 0
    ar_r_same_records = []
    ar_r_same_tokens = set()
    dual_present = 0
    dual_present_edges = []
    dual_present_scenarios = set()
    dual_d_wins = 0
    dual_with_i_rsp = 0
    r_w_same_edge = 0
    r_w_same_edges = []
    hold_tid = None
    reset_edges = 0
    reset_runs = 0
    in_reset = True

    for e in edges:
        e['i_acc'] = bool(e['i_v'] and e['i_r'] and e['resetn'])
        e['d_acc'] = bool(e['d_v'] and e['d_r'] and e['resetn'])
        e['ar_hs'] = bool(e['ar_v'] and e['ar_r'] and e['resetn'])
        e['aw_hs'] = bool(e['aw_v'] and e['aw_r'] and e['resetn'])
        # The user port has no WVALID: a write beat completes when WREADY is high and the
        # write owns the buffer, i.e. its AW was accepted earlier or is accepted on this
        # very edge (bridge RTL write_buffer_complete).  Reset edges neither handshake.
        e['w_hs'] = bool(e['w_r'] and e['resetn'] and
                         (e['aw_hs'] or (write_owner is not None and write_owner in aw_edge)))
        e['r_hs'] = bool(e['r_v'] and e['resetn'])
        e['i_rsp'] = bool(e['i_rsp'] and e['resetn'])
        e['d_rsp'] = bool(e['d_rsp'] and e['resetn'])

        # ---- reset bookkeeping: explicit resets are counted separately from power-on
        if not e['resetn']:
            reset_edges += 1
            if not in_reset:
                reset_runs += 1
                in_reset = True
        else:
            in_reset = False

        # ---- a held I request must stay presented, unchanged, until it is accepted
        if hold_tid is not None:
            if not e['resetn']:
                hold_tid = None
            else:
                assert e['i_v'] and e['i_addr'] == plan[hold_tid]['addr'], \
                    'edge %d: I token %d was not held until acceptance (i_v=%d addr=%08x)' \
                    % (e['edge'], hold_tid, e['i_v'], e['i_addr'])

        assert not (e['i_acc'] and e['d_acc']), \
            'edge %d accepts I and D together' % e['edge']

        # ---- presented request fields must never drift from the planned token
        if e['resetn']:
            if e['i_v'] and ptr[T_I] < len(order[T_I]):
                tid = order[T_I][ptr[T_I]]
                assert e['i_addr'] == plan[tid]['addr'], \
                    'edge %d I address %08x drifted from planned token %d %08x' % (
                        e['edge'], e['i_addr'], tid, plan[tid]['addr'])
            if e['d_v'] and ptr[T_D] < len(order[T_D]):
                tid = order[T_D][ptr[T_D]]
                assert (e['d_addr'] == plan[tid]['addr'] and
                        e['d_wr'] == plan[tid]['write']), \
                    'edge %d D request drifted from planned token %d (%08x/%d)' % (
                        e['edge'], tid, e['d_addr'], e['d_wr'])

        busy_at_start = bool(pending[T_I] or pending[T_D] or read_owner is not None
                             or write_owner is not None)
        if e['resetn']:
            if e['i_rsp'] and e['d_acc']:
                competition += 1
            if e['d_rsp'] and e['i_acc']:
                competition += 1

        # ---- real I/D dual request coverage (valid flags, not responses)
        if e['resetn'] and e['i_v'] and e['d_v']:
            dual_present += 1
            dual_present_edges.append(e['edge'])
            dual_present_scenarios.add(e['scen'])
            if e['i_rsp']:
                dual_with_i_rsp += 1
            if e['d_v'] and e['d_r'] and not e['i_r']:
                dual_d_wins += 1
                assert not e['i_acc'], \
                    'edge %d: D won the competition but I was accepted too' % e['edge']
                assert ptr[T_I] < len(order[T_I]), \
                    'edge %d: dual request with no pending I token' % e['edge']
                held = order[T_I][ptr[T_I]]
                assert e['i_addr'] == plan[held]['addr'], \
                    'edge %d: competing I token %d address mismatch' % (e['edge'], held)
                hold_tid = held

        # ---- reset edges cancel the unfinished CPU tokens only
        if not e['resetn']:
            assert not (e['ar_hs'] or e['aw_hs'] or e['w_hs'] or e['r_hs']), \
                'edge %d issues a DDR command during reset' % e['edge']
            for tgt in (T_I, T_D):
                for tid in list(pending[tgt]):
                    assert state[tid] == 'accepted'
                    assert plan[tid]['cancel'], 'token %d cancelled but not planned' % tid
                    state[tid] = 'cancelled'
                    cancel_edge[tid] = e['edge']
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
            assert e['scen'] == tok['scen'], \
                'edge %d response of token %d in scenario %d, plan scenario %d' % (
                    e['edge'], tid, e['scen'], tok['scen'])
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
                acked[tid] = True
                assert e['edge'] == acc_edge[tid] + 1, 'store token %d acked late' % tid
            else:
                assert tid in ar_edge, 'edge %d miss response without an AR (token %d)' % (
                    e['edge'], tid)
                assert tid in beat_of, 'edge %d miss response without an R beat (token %d)' % (
                    e['edge'], tid)
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
        same_edge_ar_r = bool(e['ar_hs'] and e['r_hs'])
        if e['ar_hs']:
            assert read_owner is not None, 'edge %d AR without an owner' % e['edge']
            tok = plan[read_owner]
            assert not is_hit[read_owner], 'AR issued for a cached line'
            assert e['ar_addr'] == line_base(tok['addr']), \
                'edge %d AR address %08x, owner %08x' % (e['edge'], e['ar_addr'], tok['addr'])
            assert e['ar_id'] == (0 if tok['target'] == T_I else 1), 'AR id/owner mismatch'
            assert read_owner not in ar_edge, 'token %d issued two ARs' % read_owner
            assert e['scen'] == tok['scen'], \
                'edge %d AR of token %d in scenario %d, plan scenario %d' % (
                    e['edge'], read_owner, e['scen'], tok['scen'])
            ar_edge[read_owner] = e['edge']
        if e['r_hs']:
            assert read_owner is not None, 'edge %d R without an outstanding AR' % e['edge']
            tok = plan[read_owner]
            assert e['r_id'] == (0 if tok['target'] == T_I else 1), 'R id/owner mismatch'
            assert e['r_last'] == 1, 'the single beat must be last'
            assert read_owner in ar_edge, 'R without a preceding AR'
            if same_edge_ar_r:
                ar_r_same += 1
                ar_r_same_tokens.add(read_owner)
                ar_r_same_records.append(dict(edge=e['edge'], token=read_owner,
                                              scen=e['scen']))
            # The beat is built from the independent memory as it is BEFORE this edge's
            # write bytes are committed (the W commit below happens after this read).
            bs = [(e['r_data'] >> (8 * k)) & 0xFF for k in range(32)]
            assert bs == beat_from(dm, e['ar_addr']), \
                'edge %d R beat disagrees with the independent memory' % e['edge']
            beat_of[read_owner] = (bs, e['edge'])
            (ic if tok['target'] == T_I else dc).fill(tok['addr'], bs)
        if e['aw_hs']:
            assert write_owner is not None, 'edge %d AW without an owner' % e['edge']
            assert write_owner not in aw_edge, 'token %d issued two AWs' % write_owner
            assert e['aw_addr'] == derive_write(plan[write_owner])['addr'], \
                'AW address/owner mismatch'
            assert e['scen'] == plan[write_owner]['scen'], \
                'edge %d AW of token %d in scenario %d, plan scenario %d' % (
                    e['edge'], write_owner, e['scen'], plan[write_owner]['scen'])
            aw_edge[write_owner] = e['edge']
        # AW only latches owner/address; address and payload must stay stable while the
        # write waits for its W completion.
        if write_owner is not None:
            tok = plan[write_owner]
            exp = derive_write(tok)
            if e['aw_v']:
                assert e['aw_addr'] == exp['addr'], \
                    'edge %d AW address changed while waiting (token %d)' % (
                        e['edge'], write_owner)
            cur = (e['w_data'], e['w_strb'])
            if cur != (0, 0):
                seen = aw_wait_payload.setdefault(write_owner, cur)
                if write_owner in aw_edge:
                    assert cur == seen, \
                        'edge %d W payload changed while waiting for WREADY (token %d)' % (
                            e['edge'], write_owner)
                else:
                    assert e['w_strb'] == exp['strobe'], \
                        'edge %d driven W strobe %08x, plan %08x (token %d)' % (
                            e['edge'], e['w_strb'], exp['strobe'], write_owner)
        if e['r_hs'] and e['w_hs']:
            r_w_same_edge += 1
            r_w_same_edges.append(e['edge'])
        if e['w_hs']:
            assert write_owner is not None, 'edge %d W without an owner' % e['edge']
            tid = write_owner
            tok = plan[tid]
            exp = derive_write(tok)
            assert e['w_strb'] == exp['strobe'], \
                'edge %d W strobe %08x, plan-derived %08x (token %d)' % (
                    e['edge'], e['w_strb'], exp['strobe'], tid)
            for p in range(32):
                if exp['strobe'] >> p & 1:
                    got = (e['w_data'] >> (8 * p)) & 0xFF
                    assert got == exp['bytes'][p], \
                        'edge %d W byte %d = %02x, plan-derived %02x (token %d)' % (
                            e['edge'], p, got, exp['bytes'][p], tid)
            # Only now, from the PLAN fields, commit the reference bytes and the cache.
            for j in range(4):
                if (tok['wstrb'] >> j) & 1:
                    dm[(line_base(tok['addr']) * 4 + (tok['addr'] & 0x1F) + j) & 4095] = \
                        (tok['wdata'] >> (8 * j)) & 0xFF
            dc.store(tok['addr'], tok['wdata'], tok['wstrb'])
            written[tid] = True
            state[tid] = 'written'
            write_owner = None

        # ---- (c) this edge's new accepts
        if e['i_acc']:
            assert ptr[T_I] < len(order[T_I]), 'unplanned I accept'
            tid = order[T_I][ptr[T_I]]
            assert plan[tid]['target'] == T_I
            assert plan[tid]['addr'] == e['i_addr'], \
                'edge %d I accept %08x, plan %08x (token %d)' % (
                    e['edge'], e['i_addr'], plan[tid]['addr'], tid)
            assert state[tid] == 'pending', 'token %d accepted twice' % tid
            assert e['scen'] == plan[tid]['scen'], \
                'edge %d I token %d accepted in scenario %d, plan scenario %d' % (
                    e['edge'], tid, e['scen'], plan[tid]['scen'])
            state[tid] = 'accepted'
            acc_edge[tid] = e['edge']
            pending[T_I].append(tid)
            ptr[T_I] += 1
            is_hit[tid] = ic.hit(e['i_addr'])
            if is_hit[tid]:
                hit_word[tid] = ic.word(e['i_addr'])
            else:
                read_owner = tid
            if plan[tid]['expect'] in ('hit', 'cancel_hit'):
                assert is_hit[tid], 'token %d planned as a hit but missed' % tid
            else:
                assert not is_hit[tid], 'token %d planned as a miss but hit' % tid
        if e['d_acc']:
            assert ptr[T_D] < len(order[T_D]), 'unplanned D accept'
            tid = order[T_D][ptr[T_D]]
            tok = plan[tid]
            assert tok['target'] == T_D
            assert (tok['addr'] == e['d_addr'] and tok['write'] == e['d_wr']
                    and tok['size'] == e['d_size']), \
                'edge %d D accept disagrees with the plan (token %d)' % (e['edge'], tid)
            if tok['write']:
                assert e['d_wdata'] == tok['wdata'] and e['d_wstrb'] == tok['wstrb'], \
                    'edge %d D store payload disagrees with the plan (token %d)' % (
                        e['edge'], tid)
            assert state[tid] == 'pending', 'token %d accepted twice' % tid
            assert e['scen'] == tok['scen'], \
                'edge %d D token %d accepted in scenario %d, plan scenario %d' % (
                    e['edge'], tid, e['scen'], tok['scen'])
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
                assert is_hit[tid] == (tok['expect'] == 'hit'), \
                    'D token %d hit/miss disagrees with the plan (%s)' % (tid, tok['expect'])

        if hold_tid is not None and state[hold_tid] != 'pending':
            hold_tid = None

        # ---- (d) a miss may only be delayed by write_buffer_busy / ARREADY
        if read_owner is not None and read_owner not in ar_edge:
            if e['busy']:
                assert not e['ar_v'], 'edge %d AR raised while the write buffer is busy' % e['edge']
                busy_blocked += 1
            elif e['edge'] > acc_edge.get(read_owner, 0):
                assert e['ar_v'], 'edge %d AR eligible but not raised (token %d)' % (
                    e['edge'], read_owner)
            if e['ar_v'] and not e['ar_r']:
                ready_blocked += 1

        # ---- (e) idle silence: nothing presented and nothing owned at edge start
        if not e['i_v'] and not e['d_v'] and not busy_at_start:
            assert not e['i_rsp'] and not e['d_rsp'] and not e['ar_v'], \
                'edge %d is idle but still drives a response/AR' % e['edge']
            idle_silent += 1

    # ------------------------------------------------------------------ conservation
    accepted = ptr[T_I] + ptr[T_D]
    assert accepted == len(plan), 'only %d of %d planned tokens were accepted' % (
        accepted, len(plan))
    for t in plan:
        tid = t['id']
        exp = t['expect']
        if t['cancel']:
            assert state[tid] == 'cancelled', 'planned cancel token %d ended %s' % (tid, state[tid])
        elif exp == 'store':
            assert state[tid] in ('responded', 'written'), 'store token %d ended %s' % (tid, state[tid])
            assert acked.get(tid), 'store token %d never got its posted ACK' % tid
            assert written.get(tid), 'store token %d never completed its physical W' % tid
        else:
            assert state[tid] == 'responded', 'read token %d ended %s' % (tid, state[tid])
        if exp in ('hit', 'cancel_hit'):
            assert is_hit.get(tid) is True, 'token %d planned as hit' % tid
        if exp in ('miss', 'cancel_miss', 'cancel_miss_ar'):
            assert is_hit.get(tid) is False, 'token %d planned as miss' % tid
        if exp == 'cancel_miss':
            assert tid not in ar_edge, 'token %d must be cancelled before its AR' % tid
        if exp == 'cancel_miss_ar':
            assert tid in ar_edge, 'token %d must have issued its AR' % tid
            assert tid not in beat_of, 'token %d must be cancelled before its R' % tid
    orphan_ar = sorted(tid for tid in ar_edge if tid not in beat_of)
    assert orphan_ar == sorted(t['id'] for t in plan if t['expect'] == 'cancel_miss_ar'), \
        'AR/payload conservation: ARs without R are %s' % (orphan_ar,)

    cancels = sum(1 for t in plan if state[t['id']] == 'cancelled')
    responses = sum(1 for t in plan if state[t['id']] in ('responded', 'written'))
    assert cancels == len(summary['planned_cancel_ids']) == PLANNED_RESETS, cancels
    assert responses + cancels == len(plan), (responses, cancels, len(plan))
    assert not pending[T_I] and not pending[T_D], 'outstanding CPU tokens remain'
    assert read_owner is None and write_owner is None, 'outstanding DDR owner remains'
    assert len(ar_r_same_records) == ar_r_same

    # ------------------------------------------------------- recomputed DDR counters
    ar_n = sum(1 for e in edges if e['ar_hs'])
    r_n = sum(1 for e in edges if e['r_hs'])
    aw_n = sum(1 for e in edges if e['aw_hs'])
    w_n = sum(1 for e in edges if e['w_hs'])
    assert ar_n == summary['ar'], 'AR count %d, plan %d' % (ar_n, summary['ar'])
    assert r_n == summary['r'], 'R count %d, plan %d' % (r_n, summary['r'])
    assert aw_n == w_n == summary['aw'], 'AW/W %d/%d, plan %d' % (aw_n, w_n, summary['aw'])
    assert aw_n == sum(1 for t in plan if t['expect'] == 'store')
    assert sum(1 for tid in written if written[tid]) == aw_n

    # ------------------------------------------------------------------- SUM checks
    for key in ('scenarios', 'tokens', 'accepts', 'responses', 'cancels', 'resets',
                'ar', 'r', 'aw', 'w', 'edges', 'mismatches'):
        assert key in sums, 'SUM record is missing %s' % key
    assert int(sums['scenarios']) == len(scen_order) == SCENARIOS
    assert int(sums['tokens']) == len(plan)
    assert int(sums['accepts']) == accepted
    assert int(sums['responses']) == responses
    assert int(sums['cancels']) == cancels
    assert int(sums['resets']) == reset_runs == summary['resets'], \
        'SUM resets=%s, explicit reset runs=%d, plan %d' % (sums['resets'], reset_runs,
                                                            summary['resets'])
    assert int(sums['ar']) == ar_n
    assert int(sums['r']) == r_n
    assert int(sums['aw']) == aw_n
    assert int(sums['w']) == w_n
    assert int(sums['edges']) == edges[-1]['edge']
    assert int(sums['mismatches']) == 0
    assert int(sums['accepts']) == int(sums['responses']) + int(sums['cancels'])
    # The testbench may not claim more coverage than the raw records contain.
    if 'ar_r_same' in sums:
        assert int(sums['ar_r_same']) <= ar_r_same, \
            'SUM ar_r_same=%s exceeds the %d same-edge AR/R records' % (sums['ar_r_same'],
                                                                       ar_r_same)
    if 'dual_present' in sums:
        assert int(sums['dual_present']) <= dual_present, \
            'SUM dual_present=%s exceeds the %d I/D dual-valid edges' % (
                sums['dual_present'], dual_present)

    # --------------------------------------------------------------- marker checks
    # The SCEN/TOK/BUS markers must agree with the replay; a duplicated or missing marker
    # is a mismatch, not a cosmetic detail (lists, not sets, so duplicates are visible).
    acc_markers = sorted((t['edge'], t['tok']) for t in toks if t['kind'] == 'ACC')
    rsp_markers = sorted((t['edge'], t['tok']) for t in toks if t['kind'] == 'RSP')
    can_markers = sorted((t['edge'], t['tok']) for t in toks if t['kind'] == 'CAN')
    assert acc_markers == sorted((acc_edge[t['id']], t['id']) for t in plan), \
        'ACC markers disagree with the replayed accept edges'
    assert rsp_markers == sorted((rsp_edge[t['id']], t['id'])
                                 for t in plan if t['id'] in rsp_edge), \
        'RSP markers disagree with the replayed response edges'
    assert can_markers == sorted((cancel_edge[t['id']], t['id'])
                                 for t in plan if t['id'] in cancel_edge), \
        'CAN markers disagree with the replayed cancel edges'
    assert len(can_markers) == len(cancel_edge) == cancels
    assert not [t for t in toks if t['kind'] not in ('ACC', 'RSP', 'CAN')], 'unknown TOK kind'
    bus_expected = {'AR': sorted(e['edge'] for e in edges if e['ar_hs']),
                    'R': sorted(e['edge'] for e in edges if e['r_hs']),
                    'AW': sorted(e['edge'] for e in edges if e['aw_hs']),
                    'W': sorted(e['edge'] for e in edges if e['w_hs'])}
    for kind, want in bus_expected.items():
        got = sorted(b['edge'] for b in bus if b['kind'] == kind)
        assert got == want, 'BUS %s markers disagree with the raw records' % kind
    assert not [b for b in bus if b['kind'] not in bus_expected], 'unknown BUS kind'
    assert set(scen_order) == set(range(1, SCENARIOS + 1)), sorted(scen_order)

    # ------------------------------------------------------------------- coverage
    assert max(len(v) for v in lanes_seen.values()) == 8, 'the filled line must hit in all lanes'
    assert ready_blocked >= 3, 'ARREADY back pressure was not observed (%d)' % ready_blocked
    assert busy_blocked >= 1, 'the posted-write drain boundary was not observed'
    assert competition >= 2, 'old-response vs other-end accept was not observed (%d)' % competition
    assert idle_silent >= 3, 'idle valid-zero silence was not observed'
    assert hit_after_miss >= 1 and miss_after_hit >= 1 and hit_after_hit >= 1, \
        (hit_after_miss, miss_after_hit, hit_after_hit)
    assert refetch_changed >= 1, 'no refetch returned data changed by an earlier store'
    assert ar_r_same >= summary['ar_r_same_min'], \
        'AR/R on one posedge: %d, required >= %d' % (ar_r_same, summary['ar_r_same_min'])
    assert set(AR_R_SAME_TOKENS).issubset(ar_r_same_tokens), \
        'same-edge AR/R not seen for the declared tokens (saw %s)' % sorted(ar_r_same_tokens)
    for rec in ar_r_same_records:
        assert rsp_edge.get(rec['token']) == rec['edge'] + 1, \
            'token %d must be responded one edge after its same-edge AR/R (edge %d)' % (
                rec['token'], rec['edge'])
    assert dual_present >= summary['dual_present_min'], \
        'I/D dual-valid edges: %d, required >= %d' % (dual_present,
                                                      summary['dual_present_min'])
    assert dual_d_wins >= 1, 'no edge with d_v && d_r && !i_r (no real data priority)'
    assert plan_summary()['plan_sha256'] == summary['plan_sha256']

    return dict(scenarios=len(scen_order), tokens=len(plan), accepts=accepted,
                responses=responses, cancels=cancels, resets=reset_runs,
                power_on_resets=1, reset_edges=reset_edges,
                ar=ar_n, r=r_n, aw=aw_n, w=w_n,
                ar_r_same=ar_r_same, dual_present=dual_present, dual_d_wins=dual_d_wins,
                dual_with_i_rsp=dual_with_i_rsp,
                ar_r_same_edges=[(r['edge'], r['token'], r['scen'])
                                 for r in ar_r_same_records],
                dual_present_edges=dual_present_edges,
                dual_present_scenarios=sorted(dual_present_scenarios),
                r_w_same_edge=r_w_same_edge, r_w_same_edges=r_w_same_edges,
                edges=edges[-1]['edge'], log_lines=len(edges), first_edge=edges[0]['edge'],
                mismatches=0, plan_sha256=summary['plan_sha256'],
                lanes=max(len(v) for v in lanes_seen.values()),
                ready_blocked=ready_blocked, busy_blocked=busy_blocked,
                competition=competition, idle_silent=idle_silent,
                hit_after_miss=hit_after_miss, miss_after_hit=miss_after_hit,
                hit_after_hit=hit_after_hit, refetch_changed=refetch_changed,
                planned=summary)


def main():
    import sys
    edge = sys.argv[1] if len(sys.argv) > 1 else 'edge.log'
    plan = sys.argv[2] if len(sys.argv) > 2 else 'plan.log'
    r = review(edge, plan)
    print('RESULT: PASS inst_lookup_protocol_completion scenarios=%d tokens=%d accepts=%d '
          'responses=%d cancels=%d resets=%d ar=%d r=%d aw=%d w=%d ar_r_same=%d '
          'dual_present=%d edges=%d log_lines=%d first_edge=%d mismatches=0'
          % (r['scenarios'], r['tokens'], r['accepts'], r['responses'], r['cancels'],
             r['resets'], r['ar'], r['r'], r['aw'], r['w'], r['ar_r_same'],
             r['dual_present'], r['edges'], r['log_lines'], r['first_edge']))
    if r['r_w_same_edge'] == 0:
        print('NOTE: no edge had an actual W and R together; same-edge R/W visibility '
              'is NOT triggered in this run (edges=%s)' % r['r_w_same_edges'])


if __name__ == '__main__':
    main()
