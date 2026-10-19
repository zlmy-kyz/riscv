"""Offline synthetic negatives for the Task033 completion checker.

Each mutation replays a trace that represents one of the defects the review
found, and the checker must reject it. No HDL is executed here: the traces are
the recorded external handshakes with a single semantic change applied.
"""
import copy
import json
import sys
from pathlib import Path

import check_completion as cc

HERE = Path(__file__).resolve().parent
OK = 'SELFTEST: PASS'
BAD = 'SELFTEST: FAIL'


def load(rundir):
    rundir = Path(rundir)
    edges = cc.parse_log(rundir / 'completion.edges.log')
    pokes, _ = cc.load_tokens(rundir / 'completion.tok.log')
    return edges, pokes


def put(edges, n, key, value, both=False):
    e = edges[n - 1]
    e['pre'][key] = value
    if both:
        e['post'][key] = value


def m_main_slot_hit(edges, pokes):
    """The hit is accepted before the D AR: a plain front-slot hit."""
    put(edges, 16, 'iv', '1'); put(edges, 16, 'ir', '1')
    put(edges, 16, 'ia', '00000104')
    put(edges, 17, 'ip', '1'); put(edges, 17, 'id', '7e714b5d')
    put(edges, 19, 'iv', '0'); put(edges, 19, 'ir', '0')
    put(edges, 19, 'ip', '0', both=True); put(edges, 19, 'id', '00000000', both=True)
    cc.analyze(edges, pokes)


def m_promoted_ar_missing(edges, pokes):
    """The parked miss is never promoted, so no I AR appears."""
    put(edges, 76, 'arv', '0', both=True); put(edges, 76, 'arr', '0', both=True)
    cc.analyze(edges, pokes)


def m_reset_before_d_done(edges, pokes):
    """Reset while the D read is still waiting for R (its response is gone)."""
    for n in range(73, 84):
        put(edges, n, 'rst', '0', both=True); put(edges, n, 'init', '0', both=True)
    put(edges, 74, 'rv', '0', both=True)
    put(edges, 75, 'dp', '0', both=True)
    cc.analyze(edges, pokes)


def m_parallel_i_miss(edges, pokes):
    """The 'parallel hit' was really a miss answered as if it were cached."""
    put(edges, 120, 'ia', '01000108')
    put(edges, 121, 'ia', '01000108')
    cc.analyze(edges, pokes)


def m_perf_claim_19(edges, pokes):
    """The original mis-measurement: the window closes at the last I response."""
    perfs = dict(
        on=dict(d_response=565, last_i_response=552, all_done=565,
                all_done_minus_ar=6, all_done_minus_accept=7),
        off=dict(d_response=595, last_i_response=601, all_done=601,
                 all_done_minus_ar=25, all_done_minus_accept=26))
    cc.assert_perf(perfs)


def m_cancel_split(edges, pokes):
    """Reset cancels attributed to the wrong side."""
    out = cc.analyze(edges, pokes)
    stats = copy.deepcopy(out['stats'])
    stats[1]['i_cancel'], stats[1]['d_cancel'] = 0, 2
    cc.gate_independent_hit(edges, out['facts'], stats)


def m_soc_double_pop(old):
    """The CPU consumes the same response twice."""
    pre, fx, retires = _soc_split(Path(old) / 'soc.edges.log')
    fx[63]['pop'] = '1'
    fx[63]['bufp'] = '40000024'
    return _binding_from(pre, fx, retires)


def m_store_escape(old):
    """A young wrong-path store reaches the DDR image."""
    mem = cc.Mem()
    dump = {}
    for text in (Path(old) / 'soc.mem.log').read_text(encoding='ascii').splitlines():
        w = text.split()
        dump[int(w[0])] = int(w[1], 16)
    beat = mem.beat_of(cc.WRONG_PATH_STORE)
    dump[beat] ^= 0xFF
    cc.soc_store_guard(old, dump=dump)


def m_valid_byte_x(edges, pokes):
    """A valid response carries an unknown data byte."""
    put(edges, 122, 'id', 'xxxxxxxx')
    cc.analyze(edges, pokes)


def _soc_split(path):
    pre, fx, retires = {}, {}, []
    for line in Path(path).read_text(encoding='ascii').splitlines():
        w = line.split()
        if not w:
            continue
        d = dict(item.split('=', 1) for item in w[1:])
        if w[0] == 'E':
            if d['ph'] == 'PRE':
                pre[int(d['n'])] = d
        elif w[0] == 'F' and d['ph'] == 'PRE':
            fx[int(d['n'])] = d
        elif w[0] == 'R':
            retires.append(d)
    return pre, fx, retires


def _binding_from(pre, fx, retires):
    """cpu_binding over in-memory records (the file is never rewritten)."""
    acc = [n for n, d in pre.items()
           if d['iv'] == '1' and d['ir'] == '1' and int(d['ia'], 16) == 0x24]
    if not acc or acc[0] != 46:
        cc.fail('CPU binding: first I accept of 0x24 is %s' % (acc[0] if acc else None))
    pops = [n for n, d in fx.items() if d['pop'] == '1' and d['bufp'] == '40000024']
    if pops[0] != 62:
        cc.fail('CPU binding: the held entry was first popped at %d' % pops[0])
    if len(pops) != len(acc):
        cc.fail('CPU binding: %d pops but %d accepts of the same PC'
                % (len(pops), len(acc)))
    for a, p in zip(acc, pops):
        if p <= a:
            cc.fail('CPU binding: pop %d does not follow accept %d' % (p, a))


def main(rundir=None, olddir=None):
    base = Path(rundir or HERE)
    if olddir is not None:
        old = Path(olddir)
    else:
        old = HERE / 'build/ds_inst_hit_overlap_20261017_a'

    cases = [
        ('main_slot_hit', lambda e, p: m_main_slot_hit(e, p)),
        ('promoted_ar_missing', lambda e, p: m_promoted_ar_missing(e, p)),
        ('reset_before_d_done', lambda e, p: m_reset_before_d_done(e, p)),
        ('parallel_i_miss', lambda e, p: m_parallel_i_miss(e, p)),
        ('perf_claim_19', lambda e, p: m_perf_claim_19(e, p)),
        ('cancel_split', lambda e, p: m_cancel_split(e, p)),
        ('valid_byte_x', lambda e, p: m_valid_byte_x(e, p)),
    ]
    results = []
    for name, fn in cases:
        edges, pokes = load(base)
        try:
            fn(edges, pokes)
        except cc.CheckError as exc:
            results.append((name, 'rejected', str(exc)))
        else:
            results.append((name, 'ACCEPTED', 'the checker did not reject this trace'))

    for name, fn in (('cpu_double_pop', m_soc_double_pop),
                     ('store_escape', m_store_escape)):
        try:
            fn(old)
        except cc.CheckError as exc:
            results.append((name, 'rejected', str(exc)))
        else:
            results.append((name, 'ACCEPTED', 'the checker did not reject this trace'))

    # the unmodified trace must still pass, so the negatives are not vacuous
    try:
        cc.analyze(*load(base))
        results.append(('control', 'accepted', 'the unmodified trace still passes'))
    except cc.CheckError as exc:
        results.append(('control', 'REJECTED', str(exc)))

    bad = [r for r in results if r[1] in ('ACCEPTED', 'REJECTED')]
    for name, verdict, note in results:
        print('  %-22s %-9s %s' % (name, verdict, note))
    print('%s %d/%d' % (BAD if bad else OK, len(results) - len(bad), len(results)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None,
                  sys.argv[2] if len(sys.argv) > 2 else None))
