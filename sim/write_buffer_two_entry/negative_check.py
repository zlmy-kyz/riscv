"""Task043 补正02 item 5: prove the repaired references reject tampered evidence.

Every mutation below edits a *copy* of one frozen run's trace inside
<run>/negatives/<name>/ and re-runs the sealed checker from that run's own
src/tools. A mutation is only accepted as "rejected" when the checker exits
non-zero AND its JSON status is not PASS. The sealed trace itself is never
modified.

usage: negative_check.py <run_dir> [<run_dir> ...]
       the run's run_meta.json decides the plane (check_mode).
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

PY = sys.executable

# column order of the bridge trace (see check_wb2.py COLS)
BCOLS = ('cyc rstn init iv ir isv ia idata dv dw ds dr da wd ws dsv ddata '
         'av ardy aa wdata wstrb wrdy arv ardy2 ara rv rid rlast rdata busy').split()


def read_lines(p):
    return p.read_text(encoding='utf-8', errors='replace').splitlines()


def write_lines(p, lines):
    p.write_text('\n'.join(lines) + '\n', encoding='utf-8')


def btokens(line):
    # the trace rows are prefixed by the record kind, so drop "E" before indexing
    return line.split()


def bfields(line):
    return line.split()[1:]


def set_bcol(line, col, value):
    t = bfields(line)
    t[BCOLS.index(col)] = value
    return ' '.join([line.split()[0]] + t)


def bcol(line, col):
    return bfields(line)[BCOLS.index(col)]


def first_edge(lines, pred):
    for i, ln in enumerate(lines):
        if ln.startswith('E ') and pred(ln):
            return i
    return None


# ------------------------------------------------------------------ mutations
def mut_drop_aw(lines):
    i = first_edge(lines, lambda ln: bcol(ln, 'av') == '1' and bcol(ln, 'ardy') == '1')
    if i is None:
        return None
    cyc = bcol(lines[i], 'cyc')
    lines[i] = set_bcol(lines[i], 'av', '0')
    return 'AW handshake removed at edge %s' % cyc


def mut_w_payload(lines):
    i = first_edge(lines, lambda ln: bcol(ln, 'wrdy') == '1')
    if i is None:
        return None
    t = btokens(lines[i])
    j = 1 + BCOLS.index('wdata')
    h = t[j]
    t[j] = h[:-1] + ('0' if h[-1] != '0' else '1')
    cyc = bcol(lines[i], 'cyc')
    lines[i] = ' '.join(t)
    return 'W beat payload altered at edge %s' % cyc


def _response_kinds(lines):
    """Map each data-response line index to 'load' or 'ack' by replaying the
    acceptance order. The trace has no explicit kind field, so this is the only
    way to pick a real load response instead of a posted store ACK."""
    from collections import deque
    q = deque()
    out = {}
    for i, ln in enumerate(lines):
        if not ln.startswith('E '):
            continue
        if bcol(ln, 'dv') == '1' and bcol(ln, 'dr') == '1':
            q.append('store' if bcol(ln, 'dw') == '1' else 'load')
        if bcol(ln, 'dsv') == '1' and q:
            out[i] = q.popleft()
    return out


def mut_load_data(lines):
    kinds = _response_kinds(lines)
    i = next((k for k in sorted(kinds) if kinds[k] == 'load'), None)
    if i is None:
        return None
    t = btokens(lines[i])
    j = 1 + BCOLS.index('ddata')
    h = t[j]
    t[j] = h[:-2] + ('ff' if h[-2:] != 'ff' else '00')
    cyc = bcol(lines[i], 'cyc')
    lines[i] = ' '.join(t)
    return 'load response data altered at edge %s' % cyc


def mut_i_data(lines):
    i = first_edge(lines, lambda ln: bcol(ln, 'isv') == '1')
    if i is None:
        return None
    t = btokens(lines[i])
    j = 1 + BCOLS.index('idata')
    h = t[j]
    t[j] = h[:-2] + ('ff' if h[-2:] != 'ff' else '00')
    cyc = bcol(lines[i], 'cyc')
    lines[i] = ' '.join(t)
    return 'instruction response data altered at edge %s' % cyc


def mut_rid(lines):
    i = first_edge(lines, lambda ln: bcol(ln, 'rv') == '1')
    if i is None:
        return None
    cyc = bcol(lines[i], 'cyc')
    cur = bcol(lines[i], 'rid')
    lines[i] = set_bcol(lines[i], 'rid', '1' if cur == '0' else '0')
    return 'R id owner flipped at edge %s' % cyc


def mut_dup_n(lines):
    for i, ln in enumerate(lines):
        if ln.startswith('N '):
            lines.insert(i, ln)
            return 'initial DDR record duplicated (%s)' % ln.split()[1]
    return None


def mut_drop_marker(lines):
    for i, ln in enumerate(lines):
        if ln.startswith('M '):
            return _drop(lines, i)
    return None


def _drop(lines, i):
    name = lines[i].split()[2]
    del lines[i]
    return 'marker %s removed' % name


def mut_invent_accept(lines):
    i = first_edge(lines, lambda ln: bcol(ln, 'dv') == '0' and bcol(ln, 'dr') == '1' and
                   bcol(ln, 'busy') == '0')
    if i is None:
        return None
    cyc = bcol(lines[i], 'cyc')
    lines[i] = set_bcol(set_bcol(lines[i], 'dv', '1'), 'dw', '0')
    return 'request accepted with no source at edge %s' % cyc


BRIDGE_MUTATIONS = [
    ('drop_aw', mut_drop_aw),
    ('w_payload', mut_w_payload),
    ('load_data', mut_load_data),
    ('i_data', mut_i_data),
    ('rid_owner', mut_rid),
    ('dup_n', mut_dup_n),
    ('drop_marker', mut_drop_marker),
    ('invent_accept', mut_invent_accept),
]


# ------------------------------------------------------------- SoC mutations
def soc_tokens(line):
    return line.split()


def soc_set(line, key, value):
    t = soc_tokens(line)
    for i, tok in enumerate(t):
        if tok.startswith(key + '='):
            t[i] = '%s=%s' % (key, value)
            return ' '.join(t)
    return line


def soc_get(line, key):
    for tok in soc_tokens(line):
        if tok.startswith(key + '='):
            return tok.split('=', 1)[1]
    return None


def soc_first(lines, pred):
    for i, ln in enumerate(lines):
        if ln.startswith('E ') and pred(ln):
            return i
    return None


def smut_non_ddr(lines):
    i = soc_first(lines, lambda ln: soc_get(ln, 'busy') == '1' and
                  soc_get(ln, 'dv') == '1' and soc_get(ln, 'dr') == '1' and
                  soc_get(ln, 'ds') in ('8', '0'))
    if i is None:
        return None
    lines[i] = soc_set(lines[i], 'ds', '9')     # pretend the UART was accepted
    return 'non-DDR acceptance faked on a busy edge %s' % soc_get(lines[i], 'n')


def smut_irq_early(lines):
    idx = None
    for i, ln in enumerate(lines):
        if ln.startswith('I '):
            idx = i
            break
    if idx is None:
        return None
    # reinsert the trap right after the first AW, with the queue still busy
    aw = None
    for i, ln in enumerate(lines):
        if ln.startswith('E ') and soc_get(ln, 'awv') == '1' and soc_get(ln, 'busy') == '1':
            aw = i
            break
    if aw is None:
        return None
    tr = lines.pop(idx)
    tr = soc_set(tr, 'busy', '1')
    lines.insert(aw + 1, tr)
    return 'trap taken while the queue was still busy'


def smut_fence_busy(lines):
    i = soc_first(lines, lambda ln: soc_get(ln, 'fret') == '1')
    if i is None:
        return None
    lines[i] = soc_set(lines[i], 'busy', '1')
    return 'FENCE retires with the queue marked busy'


def smut_cam_ar(lines):
    # only a real handshake counts; the address is also driven on other edges
    i = soc_first(lines, lambda ln: soc_get(ln, 'ara') == '0400000' and
                  soc_get(ln, 'arv') == '1' and soc_get(ln, 'arr') == '1')
    if i is None:
        return None
    lines[i] = soc_set(lines[i], 'ara', '0400004')
    return 'one camera AR handshake address perturbed at edge %s' % soc_get(lines[i], 'n')


def smut_mem_dump_case(lines):
    # the dump edit happens after the trace lines are written; keep the trace intact
    return 'see dump edit'


def smut_mem_dump(run_dir, dst):
    """Rewrite one expected dump word in the copy."""
    p = dst / 'soc.mem.log'
    lines = read_lines(p)
    for i, ln in enumerate(lines):
        if ln.startswith('P 131 '):
            t = ln.split()
            t[2] = t[2][:-4] + 'dead'
            lines[i] = ' '.join(t)
            write_lines(p, lines)
            return 'final DDR word 0x4000_1060 altered'
    return None


SOC_MUTATIONS = [
    ('non_ddr_while_busy', smut_non_ddr),
    ('irq_before_drain', smut_irq_early),
    ('fence_while_busy', smut_fence_busy),
    ('camera_ar_lost', smut_cam_ar),
]


def run_case(run, name, mutate, plane, soc):
    dst = run / 'negatives' / name
    if dst.exists():
        shutil.rmtree(dst)
    dst.mkdir(parents=True)
    for f in ('run_meta.json',):
        if (run / f).exists():
            shutil.copy2(run / f, dst / f)
    trace = 'soc.edges.log' if soc else 'wb2.edges.log'
    dump = 'soc.mem.log' if soc else 'wb2.mem.log'
    shutil.copy2(run / trace, dst / trace)
    if (run / dump).exists():
        shutil.copy2(run / dump, dst / dump)

    lines = read_lines(dst / trace)
    note = mutate(lines)
    if note is None:
        return dict(name=name, applied=False, note='mutation not applicable')
    write_lines(dst / trace, lines)
    if name == 'm1_word':
        note = smut_mem_dump(run, dst) or note

    checker = run / 'src/tools' / ('check_soc.py' if soc else 'check_wb2.py')
    argv = [PY, '-B', str(checker)]
    if not soc:
        argv += ['--plane', plane]
    argv.append(str(dst))
    proc = subprocess.run(argv, cwd=str(Path(__file__).resolve().parents[3]),
                          capture_output=True, text=True)
    status = 'NO_JSON'
    for cand in dst.glob('check_*.json'):
        try:
            status = json.loads(cand.read_text(encoding='utf-8'))['status']
        except Exception:                                   # noqa: BLE001
            status = 'UNREADABLE'
    rejected = proc.returncode != 0 and status != 'PASS'
    return dict(name=name, applied=True, note=note, exit=proc.returncode,
                status=status, rejected=rejected)


def main(argv):
    runs = [Path(a).resolve() for a in argv[1:]]
    if not runs:
        print('usage: negative_check.py <run_dir> [...]')
        return 2
    overall = True
    summary = {}
    for run in runs:
        meta = json.loads((run / 'run_meta.json').read_text(encoding='utf-8'))
        plane = meta.get('check_mode', 'key')
        soc = plane == 'soc'
        rows = []
        for name, fn in (SOC_MUTATIONS if soc else BRIDGE_MUTATIONS):
            rows.append(run_case(run, name, fn, plane, soc))
        if soc:
            rows.append(run_case(run, 'm1_word', smut_mem_dump_case, plane, soc))
        rejected = [r for r in rows if r.get('applied') and r.get('rejected')]
        applied = [r for r in rows if r.get('applied')]
        ok = len(rejected) == len(applied) and len(applied) > 0
        overall = overall and ok
        summary[str(run.name)] = dict(plane=plane, ok=ok, rows=rows)
        print('%-28s plane=%-8s rejected %d/%d  %s'
              % (run.name, plane, len(rejected), len(applied), 'OK' if ok else 'PROBLEM'))
        for r in rows:
            if not r.get('applied'):
                print('    %-20s not applicable (%s)' % (r['name'], r.get('note')))
            else:
                print('    %-20s exit=%-3s status=%-6s %s  (%s)'
                      % (r['name'], r['exit'], r['status'],
                         'REJECTED' if r['rejected'] else 'ACCEPTED!', r['note']))
    out = Path(runs[0]).parent / 'negatives_summary.json'
    out.write_text(json.dumps(dict(ok=overall, runs=summary), indent=2) + '\n',
                   encoding='utf-8')
    print('\nRESULT: %s' % ('PASS' if overall else 'FAIL'))
    return 0 if overall else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
