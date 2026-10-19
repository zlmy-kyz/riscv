"""Task033 synthetic negative cases for check_evidence.py.

The checker is only worth something if it rejects wrong evidence.  This module
takes the *real* bridge trace of the overlap job, re-emits it in a normalised
one-record-per-line form (the control case has to stay PASS), then corrupts one
aspect at a time and requires the checker to reject every variant.  Nothing is
written outside a scratch directory.
"""
import shutil
import sys
import tempfile
from pathlib import Path

import check_evidence as ce

HEX_FIELDS = ('ia', 'da', 'dwd', 'ds', 'id', 'dd', 'ara', 'awa', 'wdv', 'wsv', 'rdv')
DEC_FIELDS = ('sz', 'ep')


# --------------------------------------------------------------------- emitter
def emit_edges(edges, path):
    """Write the parsed edge list back out, one record per line."""
    out = []
    for e in edges:
        for ph, src in (('PRE', e), ('POST', e['post'])):
            parts = ['E', 'n=%d' % e['n'], 'ph=%s' % ph]
            for k in ce.NUMFIELDS:
                v = src[k] if src is e else src[k]
                if isinstance(v, str):          # raw POST text
                    parts.append('%s=%s' % (k, v))
                elif k in DEC_FIELDS:
                    parts.append('%s=%d' % (k, v))
                elif k in HEX_FIELDS:
                    parts.append('%s=%x' % (k, v))
                else:
                    parts.append('%s=%s' % (k, bin(v)[2:]))
            out.append(' '.join(parts))
    Path(path).write_text('\n'.join(out) + '\n', encoding='ascii')


def copy_run(src, dst):
    dst = Path(dst)
    dst.mkdir(parents=True, exist_ok=True)
    for name in ('bridge_on.edges.log', 'bridge_on.tok.log', 'bridge_on.mem.log'):
        shutil.copyfile(Path(src) / name, dst / name)
    return dst


def fresh_edges(src):
    return ce.load_edges(Path(src) / 'bridge_on.edges.log')


# ------------------------------------------------------------------ mutations
def m_duplicate_response(edges):
    """A second instruction response with no request behind it."""
    for i in range(1, len(edges)):
        if edges[i - 1]['ip'] and not edges[i]['ip']:
            edges[i]['ip'] = 1
            return 'a response was delivered twice'


def m_missing_response(edges):
    """Swallow one instruction response."""
    for e in edges:
        if e['ip']:
            e['ip'] = 0
            return 'an instruction response was lost'


def m_cross_source(edges):
    """Let the DDR answer an instruction read with the data owner id."""
    for e in edges:
        if e['rv']:
            e['rid'] = 1 if e['rid'] == 0 else 0
            return 'the response id was swapped between the two owners'


def m_wrong_lane(edges):
    """Move a store's byte strobe by one lane inside the beat."""
    for e in edges:
        if e['wrdy'] and e['wsv']:
            e['wsv'] = ((e['wsv'] << 1) | (e['wsv'] >> 31)) & 0xFFFFFFFF
            return 'the store byte strobe shifted inside the beat'


def m_parked_address(edges):
    """Change the address of the buffered miss while it is parked."""
    seen = 0
    for e in edges:
        if e['arv'] and e['arr']:
            seen += 1
            if seen == 4:
                e['ara'] = e['ara'] ^ 0x10
                return 'the parked miss was re-addressed'


def m_second_read(edges):
    """Issue a second physical read for a line that is already in flight."""
    first = None
    for i, e in enumerate(edges):
        if e['arv'] and e['arr']:
            first = (i, e['ara'], e['ari'], e['arl'])
            break
    if first is None:
        return None
    i, ara, ari, arl = first
    for j in range(i + 1, len(edges)):
        if not edges[j]['arv']:
            edges[j]['arv'], edges[j]['arr'] = 1, 1
            edges[j]['ara'], edges[j]['ari'], edges[j]['arl'] = ara, ari, arl
            return 'the same line was read twice'


def m_ar_before_drain(edges):
    """Assert an instruction read while the write buffer is still busy."""
    for e in edges:
        if e['awv'] and e['awr']:
            e['arv'] = 1
            return 'an instruction read started before the store drained'


def m_store_bytes(edges):
    """Return the wrong beat for a line a store will partially overwrite."""
    for e in edges:
        if e['rv'] and e['rdv']:
            e['rdv'] = e['rdv'] ^ (0xFF << 8)
            return 'the read beat did not match the reference memory'


def m_reset_cancel(edges):
    """Deliver a response on the first edge after the reset released."""
    for e in edges:
        if e['rst'] == 1 and e['init'] == 1:
            e['ip'] = 1
            return 'a response outlived the reset that cancelled it'


MUTATIONS = [
    ('duplicate_response', m_duplicate_response),
    ('missing_response', m_missing_response),
    ('cross_source_rid', m_cross_source),
    ('wrong_store_lane', m_wrong_lane),
    ('parked_miss_readdressed', m_parked_address),
    ('second_physical_read', m_second_read),
    ('read_before_write_drain', m_ar_before_drain),
    ('wrong_read_beat', m_store_bytes),
    ('response_across_reset', m_reset_cancel),
]


# -------------------------------------------------------------------- harness
def check_variant(scratch, src, name, fn):
    edges = fresh_edges(src)
    note = fn(edges)
    run = copy_run(src, Path(scratch) / name)
    emit_edges(edges, run / 'bridge_on.edges.log')
    try:
        ce.run_bridge(run, 'on')
    except ce.CheckError as exc:
        return True, note, str(exc)
    return False, note, 'accepted the corrupted trace'


def main(src_rundir):
    src = Path(src_rundir)
    if not (src / 'bridge_on.edges.log').exists():
        print('SELFTEST: SKIP no bridge_on trace in %s' % src)
        return 1
    with tempfile.TemporaryDirectory() as scratch:
        # control: the re-emitted trace must still pass
        edges = fresh_edges(src)
        run = copy_run(src, Path(scratch) / 'control')
        emit_edges(edges, run / 'bridge_on.edges.log')
        try:
            ce.run_bridge(run, 'on')
        except ce.CheckError as exc:
            print('SELFTEST: FAIL the re-emitted control trace was rejected: %s' % exc)
            return 1
        print('SELFTEST control: PASS the normalised trace is still accepted')

        bad = 0
        for name, fn in MUTATIONS:
            ok, note, msg = check_variant(scratch, src, name, fn)
            print('SELFTEST %-24s %s  %s' % (name, 'PASS' if ok else 'FAIL', msg))
            if note:
                print('    planted: %s' % note)
            if not ok:
                bad += 1
    if bad:
        print('SELFTEST: FAIL %d of %d negative cases were accepted'
              % (bad, len(MUTATIONS)))
        return 1
    print('SELFTEST: PASS %d of %d planted faults were rejected'
          % (len(MUTATIONS), len(MUTATIONS)))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else
                  Path(__file__).resolve().parent / 'build' / 'ds_inst_hit_overlap_20261017_a'))
