"""Fair short comparison: depth 1 vs depth 2 on one frozen stimulus.

The point of this comparison is that the backend calendar is a property of the
stimulus, not of the acceptance result:

  * both runs use the same TB source, the same initial DDR bytes, the same fixed
    AW/W release edges and the same per-AW W delay (declared by the wrapper only),
  * every request is offered from its first edge and held until the bridge really
    accepts it,
  * the run ends on one quiescence rule, and the cycle count is measured between
    the same two marks (S2 -> S2_done).

So a shorter run can only come from the second queue entry accepting a younger
store earlier, and the per-AW W interval must be identical in both runs.
If there is no net gain, that is reported as such.

usage: compare_fair.py <depth1_dir> <depth2_dir> [--out out.json]
"""
import json
import sys
from pathlib import Path

COLS = ('cyc resetn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata '
        'awvalid awready awaddr wdata wstrb wready arvalid arready araddr '
        'rvalid rid rlast rdata busy').split()
HEX = {'ia', 'idata', 'da', 'wd', 'ws', 'ddata', 'awaddr', 'wdata', 'wstrb',
       'araddr', 'rdata', 'ds'}


def load(run_dir):
    edges, marks, dump = [], {}, {}
    p = Path(run_dir) / 'wb2.edges.log'
    for line in p.read_text(encoding='utf-8', errors='replace').splitlines():
        w = line.split()
        if not w:
            continue
        if w[0] == 'M':
            marks[w[2]] = int(w[1])
        elif w[0] == 'P':
            dump[int(w[1])] = w[2]
        elif w[0] == 'E':
            d = {}
            for k, v in zip(COLS, w[1:]):
                try:
                    d[k] = int(v, 16) if k in HEX else int(v)
                except ValueError:
                    d[k] = None
            edges.append(d)
    return edges, marks, dump


def accepts(edges, start, end):
    return [dict(cyc=e['cyc'], write=e['dw'], addr=e['da'], data=e['wd'],
                 strb=e['ws'], size=e['ds'])
            for e in edges if start <= e['cyc'] <= end and e['dv'] and e['dr']]


def aws(edges, start, end):
    return [dict(cyc=e['cyc'], addr=e['awaddr'])
            for e in edges if start <= e['cyc'] <= end
            and e['awvalid'] and e['awready']]


def ws(edges, start, end):
    return [dict(cyc=e['cyc'], addr=e['awaddr'], data=e['wdata'],
                 strb=e['wstrb'])
            for e in edges if start <= e['cyc'] <= end and e['wready']
            and e['busy'] and e['wstrb'] not in (0, None)]


def backpressure(edges, start, end):
    """Edges on which the backend itself was the blocker, as seen at the pins."""
    seg = [e for e in edges if start <= e['cyc'] <= end]
    return dict(aw_not_ready=sum(1 for e in seg if e['awvalid'] and not e['awready']),
                w_not_ready=sum(1 for e in seg if e['busy'] and not e['wready']),
                d_blocked=sum(1 for e in seg if e['dv'] and not e['dr']))


def side(run_dir):
    edges, marks, dump = load(run_dir)
    if 'S2' not in marks or 'S2_done' not in marks:
        raise SystemExit('%s: missing S2/S2_done marks' % run_dir)
    a, b = marks['S2'], marks['S2_done']
    acc = accepts(edges, a, b)
    aw = aws(edges, a, b)
    wb = ws(edges, a, b)
    return dict(dir=str(run_dir), start=a, end=b, cycles=b - a,
                accepts=acc, aw=aw, w=wb,
                aw_cycles=[x['cyc'] for x in aw],
                w_cycles=[x['cyc'] for x in wb],
                aw_to_w=[w['cyc'] - x['cyc'] for x, w in zip(aw, wb)],
                backpressure=backpressure(edges, a, b), mem=dump,
                edges=len(edges))


def key_logical(acc):
    return [(x['write'], x['addr'], x['data'], x['strb'], x['size']) for x in acc]


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
        print('usage: compare_fair.py <depth1_dir> <depth2_dir> [--out out.json]')
        return 2
    d1, d2 = side(args[0]), side(args[1])
    res = dict(depth1={k: d1[k] for k in
                       ('dir', 'start', 'end', 'cycles', 'aw_cycles', 'w_cycles',
                        'aw_to_w', 'backpressure', 'edges')},
               depth2={k: d2[k] for k in
                       ('dir', 'start', 'end', 'cycles', 'aw_cycles', 'w_cycles',
                        'aw_to_w', 'backpressure', 'edges')})
    res['logical_requests_equal'] = key_logical(d1['accepts']) == key_logical(d2['accepts'])
    res['aw_sequence_equal'] = [x['addr'] for x in d1['aw']] == \
                               [x['addr'] for x in d2['aw']]
    res['w_sequence_equal'] = [(x['addr'], x['data'], x['strb']) for x in d1['w']] == \
                              [(x['addr'], x['data'], x['strb']) for x in d2['w']]
    res['memory_equal'] = d1['mem'] == d2['mem']
    res['aw_to_w_equal'] = d1['aw_to_w'] == d2['aw_to_w']
    res['aw_cycles_equal'] = d1['aw_cycles'] == d2['aw_cycles']
    res['w_cycles_equal'] = d1['w_cycles'] == d2['w_cycles']
    res['accept_cycles'] = dict(depth1=[x['cyc'] for x in d1['accepts']],
                                depth2=[x['cyc'] for x in d2['accepts']])
    res['depth2_never_later'] = all(
        y['cyc'] <= x['cyc'] for x, y in zip(d1['accepts'], d2['accepts']))
    res['second_store'] = dict(
        depth1=d1['accepts'][1]['cyc'] - d1['start'] if len(d1['accepts']) > 1 else None,
        depth2=d2['accepts'][1]['cyc'] - d2['start'] if len(d2['accepts']) > 1 else None)
    res['net_cycles'] = d1['cycles'] - d2['cycles']
    res['net_gain_established'] = res['net_cycles'] > 0 and res['depth2_never_later']
    # Pass criteria: the same work really happened, and the backend really was the
    # same. Whether it got faster is reported separately and never faked.
    ok = (res['logical_requests_equal'] and res['aw_sequence_equal'] and
          res['w_sequence_equal'] and res['memory_equal'] and
          res['aw_to_w_equal'] and res['aw_cycles_equal'] and
          res['w_cycles_equal'] and res['depth2_never_later'])
    res['status'] = 'PASS' if ok else 'FAIL'
    text = json.dumps(res, indent=2)
    print(text)
    if out:
        Path(out).write_text(text + '\n', encoding='utf-8')
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
