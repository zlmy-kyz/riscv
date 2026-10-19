"""Codex Task031 preparation; DeepSeek executes once, with complete raw evidence."""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from check_inputs import ROOT, HERE, MANIFEST, require_inputs, sha
from check_completion_evidence import review_job

DESIGN = HERE / 'simulation_completion_inputs.json'
TAG = 'ds_write_buffer_turnover_20261014_a'
MS = Path('D:/modelsim/win64pe')


def read(path):
    return Path(path).read_text(encoding='utf-8', errors='replace')


def save(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def require_completion_inputs():
    require_inputs()
    design = json.loads(read(DESIGN))
    assert design['input_manifest_sha256'] == sha(MANIFEST)
    assert design['fixed_tag'] == TAG
    for name, digest in design['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed task input: ' + name
    for name, digest in {**design['vendor_sha256'], **design['tool_sha256']}.items():
        assert sha(name) == digest, 'Changed external input: ' + name
    for name in design['project_sha256']:
        if name.endswith('.py'):
            ast.parse(read(ROOT / name), filename=name)
    assert sum(g['checks'] for g in design['groups']) == 889
    assert design['observation_only_equivalence'] is True and design['CPU_changed'] is False
    return design


def git_snapshot():
    def run(*args):
        return subprocess.run(['git', *args], cwd=ROOT, check=True, capture_output=True,
                              text=True, encoding='utf-8').stdout
    return dict(head=run('rev-parse', 'HEAD').strip(), branch=run('branch', '--show-current').strip(),
                status=run('status', '--porcelain=v1', '-uall'))


def command(argv, cwd, prefix, timeout):
    assert os.name == 'nt'
    start = time.monotonic()
    timed_out, cleanup = False, None
    with prefix.with_suffix('.log').open('wb') as stream:
        proc = subprocess.Popen(list(map(str, argv)), cwd=cwd, stdin=subprocess.DEVNULL,
            stdout=stream, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code = proc.wait(timeout=timeout)
        except subprocess.TimeoutExpired:
            timed_out, code = True, -1
            if proc.poll() is None:
                try:
                    killed = subprocess.run(['taskkill.exe', '/PID', str(proc.pid), '/T', '/F'],
                        capture_output=True, text=True, errors='replace', timeout=15,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                    cleanup = dict(exit_code=killed.returncode, output=killed.stdout + killed.stderr)
                except Exception as exc:
                    cleanup = dict(error=str(exc))
            if proc.poll() is None:
                proc.kill()
            proc.wait(timeout=15)
    save(prefix.with_suffix('.command.json'), dict(argv=list(map(str, argv)), cwd=str(cwd),
        exit_code=code, native_exit_after_wait=proc.returncode, seconds=time.monotonic()-start,
        timeout_seconds=timeout, timed_out=timed_out, pid=proc.pid, cleanup=cleanup,
        stdout_direct_to_file=True))
    output = read(prefix.with_suffix('.log'))
    assert not timed_out and code == proc.returncode == 0, str(prefix)
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', output), str(prefix)
    return output


def snapshot_inputs(out, design):
    project = out / 'inputs/project'
    for name, digest in design['project_sha256'].items():
        dst = project / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dst)
        assert sha(dst) == digest, name
    shutil.copyfile(DESIGN, out / 'simulation_completion_inputs.json')
    shutil.copyfile(MANIFEST, out / 'inputs.json')
    vendor_files = []
    for name, digest in design['vendor_sha256'].items():
        dst = out / 'inputs/vendor' / Path(name).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(name, dst)
        assert sha(dst) == digest, name
        vendor_files.append(dst)
    return project, vendor_files


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-inputs', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--tag', default=TAG)
    args = parser.parse_args()
    design = require_completion_inputs()
    assert args.tag == TAG
    out = HERE / 'build' / TAG
    assert not out.exists(), 'Preserve the assigned run directory; no automatic retry'
    if args.check_inputs or args.plan_only:
        print('RESULT: PASS completion inputs; observation-only equivalence; reference EV430; HDL NOT_RUN; ISA=0')
        if args.plan_only:
            print(json.dumps(dict(tag=TAG, jobs=['vlib', 'compile', 'control', 'key'],
                timeouts=design['timeouts'], module_count=36, control_checks=6, key_checks=889,
                serial_opened=False, PDS_started=False), indent=2))
        return
    before = git_snapshot()
    out.mkdir(parents=True, exist_ok=False)
    result = dict(status='RUNNING', input_manifest_sha256=sha(MANIFEST),
        completion_manifest_sha256=sha(DESIGN), completed={}, HDL_started=False,
        serial_opened=False, PDS_started=False, board='NOT_RUN', CPU_changed=False)
    save(out / 'git_before.json', before)
    save(out / 'result.json', result)
    try:
        project, vendors = snapshot_inputs(out, design)
        result['HDL_started'] = True
        save(out / 'result.json', result)
        command([MS / 'vlib.exe', out / 'work'], out, out / 'vlib', 60)
        compile_argv = [MS / 'vlog.exe', '-sv',
            '+incdir+' + (project / 'myriscv').as_posix(),
            '+incdir+' + (project / 'sim/write_buffer_turnover').as_posix(),
            '+incdir+' + (project / 'ipcore/inst_rom/rtl').as_posix(),
            '+incdir+' + (project / 'ipcore/data_ram/rtl').as_posix(), '-work', out / 'work',
            *vendors, *[project / name for name in design['compile_sources']]]
        log = command(compile_argv, out, out / 'compile', 60)
        modules = re.findall(r'-- Compiling module (\w+)', log)
        assert len(modules) == 36 and set(modules) == set(design['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        for name in ('control', 'key'):
            argv = [MS / 'vsim.exe', '-batch', '-lib', out / 'work', 'tb_write_buffer_turnover_completion',
                    '-gPOSTED=1', '-gTURNOVER=' + ('0' if name == 'control' else '1'),
                    '+CPU_IMAGE=' + str(project / design['cpu_image']),
                    '+EV_LOG=' + str(out / (name + '.events.log')),
                    '+BUS_LOG=' + str(out / (name + '.bus.log'))]
            argv += ['+%s=%d' % (key, value) for key, value in design['plusargs'].items() if key != 'CPU_IMAGE']
            argv += ['-logfile', out / (name + '.transcript'), '-do', 'run -all; quit -f']
            command(argv, out, out / name, 180)
            result['completed'][name] = review_job(out, name, design)
            save(out / 'result.json', result)
        assert result['completed']['control']['cycles'] - result['completed']['key']['cycles'] == 5
        assert require_completion_inputs() == design
        after = git_snapshot()
        save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during the formal run'
        result.update(status='WRITE_BUFFER_TURNOVER_COMPLETION_KEY_AND_CONTROL_PASS',
                      inputs_unchanged=True, git_unchanged=True, controlled_cycles_saved=5)
        print('RESULT: PASS Task031 formal completion; key889 EV430; board NOT_RUN')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        save(out / 'result.json', result)


if __name__ == '__main__':
    main()
