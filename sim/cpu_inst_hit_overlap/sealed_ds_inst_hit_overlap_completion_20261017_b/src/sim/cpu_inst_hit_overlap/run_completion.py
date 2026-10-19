"""Single entry point for the Task033 completion job.

  python -B sim/cpu_inst_hit_overlap/prepare_completion.py
  python -B sim/cpu_inst_hit_overlap/run_completion.py --check-inputs
  python -B sim/cpu_inst_hit_overlap/run_completion.py --run --tag ds_inst_hit_overlap_completion_20261017_b

`--check-inputs` is static: it never creates the formal build directory.
`--run` copies the sealed tree into `build/<tag>/src`, compiles only that copy
and executes

    old-evidence offline re-check -> vlib -> vlog -> one bridge vsim
        -> completion checker -> synthetic negatives

with per-job timeouts, first-failure stop, and an unconditional record of argv,
cwd, pid, exit code, elapsed time, timeout flag, stdout, git state and the
before/after hash of every protected original file.
"""
import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
MS = Path(r'D:/modelsim/win64pe')
TAG = 'ds_inst_hit_overlap_completion_20261017_b'
SEALED = HERE / ('sealed_' + TAG)
BUILD = HERE / 'build'
OLD = HERE / 'build/ds_inst_hit_overlap_20261017_a'
DESIGN = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
DESIGN_SHA = '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933'
PASS_STATUS = 'TASK033_COMPLETION_PASS_PENDING_CODEX_REVIEW'
FAIL_STATUS = 'STOPPED_FIRST_FAILURE'


class RunError(Exception):
    pass


def utc():
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, obj):
    Path(path).write_text(json.dumps(obj, indent=2) + '\n', encoding='ascii')


def check_inputs():
    problems, notes = [], []
    man_path = SEALED / 'manifest.json'
    if not man_path.exists():
        raise RunError('sealed manifest missing: run prepare_completion.py first')
    manifest = json.loads(man_path.read_text(encoding='ascii'))

    for row in manifest['files']:
        sealed = SEALED / row['sealed']
        if not sealed.exists():
            problems.append('sealed file missing: %s' % row['sealed'])
            continue
        if sha256(sealed) != row['sha256']:
            problems.append('sealed copy changed: %s' % row['sealed'])
        if row['role'] in ('rtl', 'testbench', 'model', 'include'):
            src = Path(row['source'])
            if not src.exists():
                problems.append('worktree source missing: %s' % row['source'])
            elif sha256(src) != row['sha256']:
                problems.append('worktree source changed after sealing: %s' % row['source'])

    tools_path = SEALED / 'tools.json'
    if not tools_path.exists():
        problems.append('tools.json missing')
    else:
        tools = json.loads(tools_path.read_text(encoding='ascii'))
        notes.append('simulator: %s' % ' '.join(tools.get('vsim_version') or []))

    if not DESIGN.exists():
        problems.append('bridge RTL missing')
    elif sha256(DESIGN) != DESIGN_SHA:
        problems.append('bridge SHA256 %s != %s' % (sha256(DESIGN), DESIGN_SHA))
    else:
        notes.append('bridge identity match: %s' % DESIGN_SHA)

    if not OLD.exists():
        problems.append('original evidence run missing: %s' % OLD)
    else:
        old_man = json.loads((OLD / 'manifest.json').read_text(encoding='ascii'))
        bad = [r['sealed'] for r in old_man['files']
               if not (OLD / r['sealed']).exists()
               or sha256(OLD / r['sealed']) != r['sha256']]
        if bad:
            problems.append('original run copy changed: %s' % ', '.join(bad[:3]))
        else:
            notes.append('original run copies verified: %d' % len(old_man['files']))
        meta = json.loads((OLD / 'run_meta.json').read_text(encoding='ascii'))
        notes.append('original run status: %s' % meta['status'])

    drift = []
    for row in manifest['protected']:
        p = ROOT / row['source']
        if not p.exists():
            drift.append('%s (missing)' % row['source'])
        elif sha256(p) != row['sha256'] and not row['metadata_only']:
            drift.append('%s (changed)' % row['source'])
    if drift:
        problems.append('protected evidence drift: %s' % ', '.join(drift[:4]))
    else:
        notes.append('protected rows verified: %d' % len(manifest['protected']))

    target = BUILD / TAG
    if target.exists():
        problems.append('formal build directory already exists: %s' % target)

    for n in ('prepare_completion.py', 'seal_completion.py', 'run_completion.py',
              'check_completion.py', 'selftest_completion.py',
              'inputs_completion.json', 'completion_plan.txt'):
        if not (HERE / n).exists():
            problems.append('harness file missing: %s' % n)

    print('CHECK-INPUTS: %s' % ('PASS' if not problems else 'FAIL'))
    for n in notes:
        print('  note: %s' % n)
    for p in problems:
        print('  problem: %s' % p)
    print('  formal build dir %s: %s'
          % (target, 'absent' if not target.exists() else 'PRESENT'))
    return 0 if not problems else 1


class Runner:
    def __init__(self, build):
        self.build = build
        self.logs = build / 'logs'
        self.logs.mkdir(parents=True, exist_ok=True)
        self.jobs = []

    def run(self, name, argv, cwd, timeout, kind):
        rec = dict(name=name, kind=kind, argv=[str(a) for a in argv],
                   cwd=str(cwd), timeout_s=timeout, started_utc=utc(),
                   pid=None, exit=None, timeout=False, elapsed_s=None,
                   stdout_log=None, verdict=None, note=None)
        t0 = time.time()
        out = ''
        try:
            proc = subprocess.Popen([str(a) for a in argv], cwd=str(cwd),
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT,
                                    text=True, errors='replace')
            rec['pid'] = proc.pid
            try:
                out, _ = proc.communicate(timeout=timeout)
                rec['exit'] = proc.returncode
            except subprocess.TimeoutExpired:
                rec['timeout'] = True
                try:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(proc.pid)],
                                   capture_output=True, timeout=60)
                except Exception:                       # noqa: BLE001
                    pass
                out, _ = proc.communicate()
                rec['exit'] = proc.returncode
        except Exception as exc:                        # noqa: BLE001
            out = 'runner exception: %r' % (exc,)
            rec['exit'] = None
        rec['elapsed_s'] = round(time.time() - t0, 2)
        log = self.logs / (name + '.console.txt')
        log.write_text(out or '', encoding='ascii', errors='replace')
        rec['stdout_log'] = str(log)
        rec['verdict'], rec['note'] = self.judge(kind, rec, out or '')
        self.jobs.append(rec)
        print('  %-18s %-6s %s  %6.2fs  %s'
              % (name, rec['verdict'],
                 'timeout' if rec['timeout'] else 'exit=%s' % rec['exit'],
                 rec['elapsed_s'], rec['note'] or ''))
        return rec

    @staticmethod
    def judge(kind, rec, out):
        if rec['timeout']:
            return 'FAIL', 'timeout after %ss' % rec['timeout_s']
        if rec['exit'] != 0:
            return 'FAIL', 'native exit %s' % rec['exit']
        bad = [ln.strip() for ln in out.splitlines()
               if ln.lstrip('# ').startswith(('** Error', '** Fatal', '** Warning'))]
        if bad:
            return 'FAIL', bad[0]
        if kind in ('compile', 'sim'):
            errs = [ln for ln in out.splitlines() if 'Errors:' in ln]
            if not errs or not errs[-1].strip().endswith('Errors: 0, Warnings: 0'):
                return 'FAIL', 'ModelSim did not report Errors: 0, Warnings: 0'
        if kind == 'sim' and 'RESULT: PASS' not in out:
            line = [ln.strip() for ln in out.splitlines() if 'RESULT: FAIL' in ln]
            return 'FAIL', line[0] if line else 'no RESULT: PASS line'
        if kind == 'check':
            if 'CHECK: FAIL' in out:
                return 'FAIL', [ln for ln in out.splitlines()
                                if ln.startswith('CHECK: FAIL')][0]
            if '"status": "PASS"' in out:
                return 'PASS', ''
            return 'FAIL', 'checker did not report PASS'
        if kind == 'selftest':
            if 'SELFTEST: FAIL' in out:
                line = [ln for ln in out.splitlines() if ln.startswith('SELFTEST: FAIL')]
                return 'FAIL', line[0] if line else 'selftest failed'
            if 'SELFTEST: PASS' in out:
                return 'PASS', ''
            return 'FAIL', 'selftest produced no verdict'
        return 'PASS', ''


def prepare_build(tag):
    build = BUILD / tag
    if build.exists():
        raise RunError('build directory already exists, refusing to reuse: %s' % build)
    build.mkdir(parents=True)
    manifest = json.loads((SEALED / 'manifest.json').read_text(encoding='ascii'))
    shutil.copytree(SEALED / 'src', build / 'src')
    shutil.copyfile(SEALED / 'manifest.json', build / 'manifest.json')
    shutil.copyfile(SEALED / 'tools.json', build / 'tools.json')
    for row in manifest['files']:
        dst = build / row['sealed']
        if not dst.exists() or sha256(dst) != row['sha256']:
            raise RunError('run copy differs from the sealed manifest: %s' % row['sealed'])
    return build, manifest


def translate(manifest, original):
    key = os.path.normcase(str(Path(original)))
    for row in manifest['files']:
        if os.path.normcase(row['source']) == key:
            return row['sealed']
    raise RunError('source %s is not in the sealed manifest' % key)


def git_state(build, moment):
    out = {}
    for name, argv in (('head', ['git', 'rev-parse', 'HEAD']),
                       ('status', ['git', 'status', '--porcelain']),
                       ('diff', ['git', 'diff'])):
        try:
            r = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True,
                               errors='replace', timeout=120)
            text = (r.stdout or '') + (r.stderr or '')
        except Exception as exc:                        # noqa: BLE001
            text = 'unavailable: %r' % (exc,)
        p = build / ('git_%s_%s.txt' % (moment, name))
        p.write_text(text, encoding='ascii', errors='replace')
        out[name] = dict(path=str(p), sha256=sha256(p), lines=len(text.splitlines()))
    return out


def do_run(tag):
    if tag != TAG:
        raise RunError('tag %r is not the frozen tag %r' % (tag, TAG))
    build, manifest = prepare_build(tag)
    runner = Runner(build)
    py = sys.executable
    sim = build / 'src/sim/cpu_inst_hit_overlap'
    incdirs = ['+incdir+' + str(build / d) for d in manifest['incdirs']]

    meta = dict(tag=tag, argv=sys.argv, cwd=os.getcwd(), started_utc=utc(),
                pid=os.getpid(), sealed_dir=str(SEALED),
                sealed_manifest_sha256=sha256(SEALED / 'manifest.json'),
                bridge=dict(path=str(DESIGN), sha256=DESIGN_SHA),
                status=None, jobs=runner.jobs, git={}, protected={})
    write_json(build / 'run_meta.json', meta)
    meta['git']['before'] = git_state(build, 'before')
    write_json(build / 'run_meta.json', meta)

    def srcs():
        return [build / translate(manifest, p) for p in manifest['job']]

    steps = [
        # 1. the original evidence is re-verified offline before any HDL runs
        ('check_legacy', [py, '-B', sim / 'check_completion.py', 'legacy', OLD],
         60, 'check'),
        ('vlib_work', [MS / 'vlib.exe', 'work'], 60, 'vlib'),
        ('vlog_work', [MS / 'vlog.exe', '-sv', '-work', 'work'] + incdirs + srcs(),
         60, 'compile'),
        ('sim_completion', [MS / 'vsim.exe', '-batch', '-lib', 'work',
                            'tb_inst_hit_completion',
                            '+PLAN=%s' % (sim / 'completion_plan.txt'),
                            '+EDGE_LOG=%s' % (build / 'completion.edges.log'),
                            '+TOK_LOG=%s' % (build / 'completion.tok.log'),
                            '+MEM_DUMP=%s' % (build / 'completion.mem.log'),
                            '-logfile', str(runner.logs / 'completion.transcript'),
                            '-do', 'run -all; quit -f'], 180, 'sim'),
        ('check_completion', [py, '-B', sim / 'check_completion.py', 'completion', build],
         60, 'check'),
        ('selftest_completion', [py, '-B', sim / 'selftest_completion.py', build, OLD],
         60, 'selftest'),
    ]

    failed = None
    try:
        for name, argv, timeout, kind in steps:
            rec = runner.run(name, argv, build, timeout, kind)
            write_json(build / 'run_meta.json', meta)
            if rec['verdict'] != 'PASS':
                failed = rec
                break
    finally:
        meta['git']['after'] = git_state(build, 'after')
        meta['protected']['design_after'] = dict(path=str(DESIGN), sha256=sha256(DESIGN))
        drift = 0
        for row in manifest['protected']:
            p = ROOT / row['source']
            now = sha256(p) if p.exists() else 'MISSING'
            ok = (now == row['sha256']) or row['metadata_only']
            drift += 0 if ok else 1
            meta['protected'][row['source']] = dict(
                before=row['sha256'], after=now, match=ok,
                metadata_only=row['metadata_only'])
        meta['protected']['_drift_rows'] = drift
        meta['finished_utc'] = utc()
        meta['status'] = FAIL_STATUS if failed else PASS_STATUS
        write_json(build / 'run_meta.json', meta)

    print()
    if failed:
        print('STATUS: %s (job %s)' % (FAIL_STATUS, failed['name']))
        print('  %s' % (failed['note'] or ''))
        print('  evidence kept in %s' % build)
        return 1
    print('STATUS: %s' % PASS_STATUS)
    print('  protected drift rows: %d' % meta['protected']['_drift_rows'])
    print('  evidence in %s' % build)
    return 0


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--check-inputs', action='store_true')
    ap.add_argument('--run', action='store_true')
    ap.add_argument('--tag', default=TAG)
    a = ap.parse_args()
    if a.check_inputs and not a.run:
        return check_inputs()
    if a.run:
        return do_run(a.tag)
    ap.print_help()
    return 2


if __name__ == '__main__':
    try:
        sys.exit(main())
    except RunError as exc:
        print('RUN: FAIL %s' % exc)
        sys.exit(1)
