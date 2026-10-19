"""Single entry point for the Task033 key simulation.

  python -B sim/cpu_inst_hit_overlap/run.py --check-inputs
  python -B sim/cpu_inst_hit_overlap/run.py --run --tag ds_inst_hit_overlap_20261017_a

`--check-inputs` is static: it never creates the formal build directory. It
re-verifies the sealed manifest, the live worktree against it, the measured
bridge identity and the read-only preparation baseline.

`--run` copies the sealed tree into `build/<tag>/src` and only ever compiles
from that copy, then executes the fixed sequence

    vlib -> vlog -> bridge_on + checker -> bridge_off + checker/perf
         -> selftest -> vlib -> vlog -> soc + checker

with per-job timeouts, first-failure stop and an unconditional record of argv,
cwd, pid, exit code, elapsed time, timeout flag, stdout and git state.
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
PDS = Path(r'C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
TAG = 'ds_inst_hit_overlap_20261017_a'
SEALED = HERE / ('sealed_' + TAG)
BUILD = HERE / 'build'
DESIGN = ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'
DESIGN_SHA = '7ab9d34c3f13caa092c8fbee933cf9e495729dcbe90520a23c9cbdeded52d933'
IDENTITY = HERE / 'preparation_20261017_b/identity.json'
PASS_STATUS = 'TASK033_KEY_SIMULATION_PASS_PENDING_CODEX_REVIEW'
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


# ---------------------------------------------------------------- static check
def check_inputs():
    problems, notes = [], []
    if not (SEALED / 'manifest.json').exists():
        raise RunError('sealed manifest missing: run seal_inputs.py first')
    manifest = json.loads((SEALED / 'manifest.json').read_text(encoding='ascii'))

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
                problems.append('worktree source changed after sealing: %s'
                                % row['source'])
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

    if IDENTITY.exists():
        ident = json.loads(IDENTITY.read_text(encoding='utf-8'))
        bad = []
        changed = []
        for rel, row in ident['all_rows'].items():
            p = ROOT / rel
            if not p.exists():
                bad.append('%s (missing)' % rel)
                continue
            now = sha256(p)
            if now != row['expected']:
                if row.get('metadata_only'):
                    changed.append(rel)
                else:
                    bad.append('%s (%s)' % (rel, now[:12]))
        if bad:
            problems.append('design/IP/BIN identity drift: %s' % ', '.join(bad))
        notes.append('identity rows checked: %d, metadata-only drift: %d'
                     % (len(ident['all_rows']), len(changed)))
        if changed:
            notes.append('metadata-only changed: %s' % ', '.join(sorted(changed)))
        if ident.get('bridge_match') is not True:
            problems.append('preparation baseline bridge_match is not true')
    else:
        problems.append('preparation identity baseline missing')

    target = BUILD / TAG
    if target.exists():
        problems.append('formal build directory already exists: %s' % target)

    for p in (HERE / 'prepare_program.py', HERE / 'check_evidence.py',
              HERE / 'selftest.py', HERE / 'inputs.json'):
        if not p.exists():
            problems.append('harness file missing: %s' % p.name)

    print('CHECK-INPUTS: %s' % ('PASS' if not problems else 'FAIL'))
    for n in notes:
        print('  note: %s' % n)
    for p in problems:
        print('  problem: %s' % p)
    print('  formal build dir %s: %s'
          % (target, 'absent' if not target.exists() else 'PRESENT'))
    return 0 if not problems else 1


# ------------------------------------------------------------------ job runner
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
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
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
        print('  %-16s %-8s %s  %6.2fs  %s'
              % (name, rec['verdict'], 'timeout' if rec['timeout'] else 'exit=%s' % rec['exit'],
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
        if kind == 'sim':
            if 'RESULT: PASS' not in out:
                line = [ln.strip() for ln in out.splitlines() if 'RESULT: FAIL' in ln]
                return 'FAIL', line[0] if line else 'no RESULT: PASS line'
        if kind == 'check':
            if 'CHECK: FAIL' in out:
                return 'FAIL', [ln for ln in out.splitlines()
                                if ln.startswith('CHECK: FAIL')][0]
            if 'SELFTEST: PASS' in out or '"status": "PASS"' in out:
                return 'PASS', ''
            if 'SELFTEST: SKIP' in out:
                return 'FAIL', 'selftest skipped'
            return 'FAIL', 'checker did not report PASS'
        return 'PASS', ''


# ------------------------------------------------------------------- run setup
def prepare_build(tag):
    build = BUILD / tag
    if build.exists():
        raise RunError('build directory already exists, refusing to reuse: %s' % build)
    build.mkdir(parents=True)
    manifest = json.loads((SEALED / 'manifest.json').read_text(encoding='ascii'))
    # only the run copy is ever compiled
    shutil.copytree(SEALED / 'src', build / 'src')
    shutil.copyfile(SEALED / 'manifest.json', build / 'manifest.json')
    shutil.copyfile(SEALED / 'tools.json', build / 'tools.json')
    for row in manifest['files']:
        dst = build / row['sealed']
        if not dst.exists() or sha256(dst) != row['sha256']:
            raise RunError('run copy differs from the sealed manifest: %s'
                           % row['sealed'])
    return build, manifest


def translate(manifest, original):
    """Map a frozen source path onto its copy inside the build directory."""
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
    sim = (build / 'src/sim/cpu_inst_hit_overlap')
    checker = sim / 'check_evidence.py'
    selftest = sim / 'selftest.py'
    incdirs = ['+incdir+' + str(build / d) for d in manifest['incdirs']]

    meta = dict(tag=tag, argv=sys.argv, cwd=os.getcwd(), started_utc=utc(),
                pid=os.getpid(), sealed_dir=str(SEALED),
                sealed_manifest_sha256=sha256(SEALED / 'manifest.json'),
                bridge=dict(path=str(DESIGN), sha256=DESIGN_SHA),
                status=None, jobs=runner.jobs, git={}, protected={})
    write_json(build / 'run_meta.json', meta)
    meta['git']['before'] = git_state(build, 'before')
    write_json(build / 'run_meta.json', meta)

    def srcs(key):
        return [build / translate(manifest, p) for p in manifest[key]]

    steps = [
        # vlib prints no summary line: judge it on the native exit code and on
        # the absence of ** Error/** Fatal lines only.
        ('vlib_work', [MS / 'vlib.exe', 'work'], 60, 'vlib'),
        ('vlog_work', [MS / 'vlog.exe', '-sv', '-work', 'work'] + incdirs + srcs('bridge_job'),
         60, 'compile'),
        ('sim_bridge_on', [MS / 'vsim.exe', '-batch', '-lib', 'work',
                           'tb_inst_hit_overlap', '-gOVERLAP=1',
                           '+PLAN=%s' % (sim / 'plan_bridge.txt'),
                           '+EDGE_LOG=%s' % (build / 'bridge_on.edges.log'),
                           '+TOK_LOG=%s' % (build / 'bridge_on.tok.log'),
                           '+MEM_DUMP=%s' % (build / 'bridge_on.mem.log'),
                           '-logfile', str(runner.logs / 'bridge_on.transcript'),
                           '-do', 'run -all; quit -f'], 180, 'sim'),
        ('check_bridge_on', [py, '-B', checker, 'bridge', build, 'on'], 60, 'check'),
        ('sim_bridge_off', [MS / 'vsim.exe', '-batch', '-lib', 'work',
                            'tb_inst_hit_overlap', '-gOVERLAP=0',
                            '+PLAN=%s' % (sim / 'plan_bridge.txt'),
                            '+EDGE_LOG=%s' % (build / 'bridge_off.edges.log'),
                            '+TOK_LOG=%s' % (build / 'bridge_off.tok.log'),
                            '+MEM_DUMP=%s' % (build / 'bridge_off.mem.log'),
                            '-logfile', str(runner.logs / 'bridge_off.transcript'),
                            '-do', 'run -all; quit -f'], 180, 'sim'),
        ('check_bridge_off', [py, '-B', checker, 'bridge', build, 'off'], 60, 'check'),
        ('selftest', [py, '-B', selftest, build], 60, 'check'),
        ('vlib_soc', [MS / 'vlib.exe', 'socwork'], 60, 'vlib'),
        ('vlog_soc', [MS / 'vlog.exe', '-sv', '-work', 'socwork'] + incdirs + srcs('soc_job'),
         60, 'compile'),
        ('sim_soc', [MS / 'vsim.exe', '-batch', '-lib', 'socwork',
                     'tb_inst_hit_overlap_soc',
                     '+EDGE_LOG=%s' % (build / 'soc.edges.log'),
                     '+MEM_DUMP=%s' % (build / 'soc.mem.log'),
                     '+PROG=%s' % (sim / 'soc_program.hex'),
                     '+FAULT_CAM=%s' % (sim / 'soc_fault_camera.hex'),
                     '+FAULT_PP=%s' % (sim / 'soc_fault_pp.hex'),
                     '-logfile', str(runner.logs / 'soc.transcript'),
                     '-do', 'run -all; quit -f'], 180, 'sim'),
        ('check_soc', [py, '-B', checker, 'soc', build], 60, 'check'),
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
        for p in (DESIGN,):
            meta['protected']['design_after'] = dict(path=str(p), sha256=sha256(p))
        for row in manifest['protected']:
            p = ROOT / row['source']
            now = sha256(p) if p.exists() else 'MISSING'
            meta['protected'][row['source']] = dict(
                before=row['sha256'], after=now, match=(now == row['sha256']))
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
