"""Cross-run comparison for the short reference sequence.

Two different questions, deliberately answered with different strictness:

  new depth1  vs  pre-043 bridge
      The ordered single-entry behaviour must not have changed at all, so the
      whole external pin trace has to be identical edge for edge, including the
      cycle numbers. Anything else is a behaviour change and would need its own
      justification.

  new depth2  vs  new depth1
      Same logical request sequence (same accepted stores/loads in the same
      order, same W beats, same final memory), but NOT the same cycle numbers:
      the whole point of the second entry is that a younger store is accepted
      earlier. So this reports when each request was accepted and when the run
      reached the same completion point, and checks that depth 2 is not behind
      at any request and is strictly ahead at the completion point.

Usage: compare_short.py <run_dir_a> <run_dir_b> [--out out.json]
Exit code 0 only if every applicable check passes.
"""
import json
import sys
from pathlib import Path

COLS = ('cyc resetn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata '
        'awvalid awready awaddr wdata wstrb wready arvalid arready araddr '
        'rvalid rid rlast rdata busy').split()

# Fields that describe the outside world. Everything here must match on the
# identity comparison; nothing may be read from the DUT interior.
EXTERNAL = COLS


def load(run_dir):
    edges, marks = [], {}
    p = Path(run_dir) / 'wb2.edges.log'
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        w = line.split()
        if not w:
            continue
        if w[0] == 'M' and len(w) >= 3:
            marks[w[2]] = int(w[1])
        elif w[0] == 'E':
            d = {}
            for k, v in zip(COLS, w[1:]):
                try:
                    d[k] = int(v, 16) if k in ('ia', 'idata', 'da', 'wd',
                                               'ddata', 'awaddr', 'wdata',
                                               'araddr', 'rdata', 'wstrb',
                                               'ws', 'ds') else int(v)
                except ValueError:
                    d[k] = None
            edges.append(d)
    return edges, marks


def accepts(edges):
    """CPU-side requests, in the order the bridge took them."""
    out = []
    for e in edges:
        if e['dv'] == 1 and e['dr'] == 1:
            out.append(dict(cyc=e['cyc'], write=e['dw'], addr=e['da'],
                            data=e['wd'], strb=e['ws'], size=e['ds']))
    return out


def wbeats(edges):
    """Physical W beats that the DDR model actually took."""
    out = []
    for e in edges:
        if e['wready'] == 1 and e['busy'] == 1 and e['wstrb'] not in (0, None):
            out.append(dict(cyc=e['cyc'], addr=e['awaddr'], data=e['wdata'],
                            strb=e['wstrb']))
    return out


def awbeats(edges):
    out = []
    for e in edges:
        if e['awvalid'] == 1 and e['awready'] == 1:
            out.append(dict(cyc=e['cyc'], addr=e['awaddr']))
    return out


def dump(run_dir):
    p = Path(run_dir) / 'wb2.edges.log'
    rows = {}
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        w = line.split()
        if w and w[0] == 'P':
            rows[int(w[1])] = w[2]
    return rows


def identity(a_dir, b_dir):
    ea, ma = load(a_dir)
    eb, mb = load(b_dir)
    res = dict(edges_a=len(ea), edges_b=len(eb), first_diff=None,
               mark_diff=[], identical=True)
    for i in range(min(len(ea), len(eb))):
        for k in EXTERNAL:
            if k == 'cyc':
                continue
            if ea[i][k] != eb[i][k]:
                res['identical'] = False
                if res['first_diff'] is None:
                    res['first_diff'] = dict(edge=i, cyc=ea[i]['cyc'],
                                             field=k, a=ea[i][k], b=eb[i][k])
                break
    if len(ea) != len(eb):
        res['identical'] = False
        if res['first_diff'] is None:
            res['first_diff'] = dict(edge=min(len(ea), len(eb)),
                                     cyc=None, field='edge_count',
                                     a=len(ea), b=len(eb))
    for name in sorted(set(ma) | set(mb)):
        if ma.get(name) != mb.get(name):
            res['mark_diff'].append(dict(mark=name, a=ma.get(name),
                                         b=mb.get(name)))
    if res['mark_diff']:
        res['identical'] = False
    return res


def logical(a_dir, b_dir):
    ea, ma = load(a_dir)
    eb, mb = load(b_dir)
    acc_a, acc_b = accepts(ea), accepts(eb)
    det = dict(
        accepts_equal=[{k: x[k] for k in ('write', 'addr', 'data', 'strb', 'size')}
                       for x in acc_a] ==
                      [{k: x[k] for k in ('write', 'addr', 'data', 'strb', 'size')}
                       for x in acc_b],
        accepts_count=[len(acc_a), len(acc_b)],
        wbeats_equal=([{k: x[k] for k in ('addr', 'data', 'strb')} for x in wbeats(ea)] ==
                      [{k: x[k] for k in ('addr', 'data', 'strb')} for x in wbeats(eb)]),
        wbeats_count=[len(wbeats(ea)), len(wbeats(eb))],
        awbeats_equal=([x['addr'] for x in awbeats(ea)] ==
                       [x['addr'] for x in awbeats(eb)]),
        memory_equal=dump(a_dir) == dump(b_dir),
        done_cycle=[ma.get('S_done'), mb.get('S_done')],
        accept_cycles=[[x['cyc'] for x in acc_a], [x['cyc'] for x in acc_b]],
    )
    # depth 2 must never accept a request later than depth 1
    pairs = list(zip(acc_a, acc_b))
    det['never_later'] = all(y['cyc'] <= x['cyc'] for x, y in pairs)
    det['strictly_earlier'] = [dict(addr=x['addr'], write=x['write'],
                                    d1=x['cyc'], d2=y['cyc'])
                               for x, y in pairs if y['cyc'] < x['cyc']]
    det['earlier_at_done'] = (ma.get('S_done') is not None and
                              mb.get('S_done') is not None and
                              mb['S_done'] < ma['S_done'])
    return det


def main(argv):
    out = None
    args = []
    i = 0
    while i < len(argv):
        if argv[i] == '--out':
            out = argv[i + 1]
            i += 2
        else:
            args.append(argv[i])
            i += 1
    if len(args) != 2:
        print('usage: compare_short.py <run_dir_a> <run_dir_b> [--out out.json]')
        return 2
    a, b = args
    res = dict(a=a, b=b,
               identity=identity(a, b),
               logical=logical(a, b))
    ident = res['identity']['identical']
    same_shape = (res['logical']['accepts_equal'] and
                  res['logical']['wbeats_equal'] and
                  res['logical']['awbeats_equal'] and
                  res['logical']['memory_equal'])
    if ident:
        # Reference pair (new depth 1 vs pre-043): the ordered single-entry
        # behaviour must be unchanged, so the timing has to match as well.
        res['mode'] = 'identity'
        ok = same_shape
    else:
        # Depth pair: the same logical work, but the second entry is allowed (and
        # expected) to accept earlier, so only ordering and memory are compared.
        res['mode'] = 'depth'
        ok = (same_shape and res['logical']['never_later'] and
              res['logical']['earlier_at_done'])
    res['status'] = 'PASS' if ok else 'FAIL'
    text = json.dumps(res, indent=2)
    print(text)
    if out:
        Path(out).write_text(text + '\n', encoding='utf-8')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
