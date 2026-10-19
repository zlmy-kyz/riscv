"""Task032 prepared by Codex; DeepSeek runs one control/key group once."""
import argparse
import ast
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path
from prepare_program import reference
from check_evidence import review_job

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'sim/write_buffer_turnover'))
from check_include_dependencies import check_includes
import simulation_completion_runner as common

MANIFEST = HERE / 'inputs.json'
TAG = 'ds_data_bus_response_turnover_20261014_a'
MS = Path('D:/modelsim/win64pe')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def require_inputs():
    data = json.loads(common.read(MANIFEST))
    assert data['tag'] == TAG
    for name, digest in data['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed input: ' + name
        if name.endswith('.py'):
            ast.parse(common.read(ROOT / name), filename=name)
    for name, digest in {**data['vendor_sha256'], **data['tool_sha256']}.items():
        assert sha(name) == digest, name
    for name, digest in data['protected_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed original evidence: ' + name
    assert check_includes(ROOT, data['compile_sources']) == data['include_dependencies']
    words = [int(w,16) for w in common.read(HERE / 'program.dat').split()]
    assert json.loads(common.read(HERE / 'reference.json')) == reference(words)
    assert data['CPU_changed'] is False and data['changed_design_files'] == ['myriscv/data_bus_interconnect.v']
    return data


def snapshot(out, data):
    project = out / 'inputs/project'
    for name, digest in data['project_sha256'].items():
        dst = project / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dst)
        assert sha(dst) == digest
    for name, digest in data['vendor_sha256'].items():
        dst = out / 'inputs/vendor' / Path(name).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(name, dst)
        assert sha(dst) == digest
    shutil.copyfile(MANIFEST, out / 'inputs.json')
    assert check_includes(project, data['compile_sources']) == data['include_dependencies']
    return project


def compile_command(out, project, data):
    return [MS / 'vlog.exe', '-sv', *['+incdir+' + (project / name).as_posix() for name in (
        'myriscv', 'sim/data_bus_turnover', 'ipcore/inst_rom/rtl', 'ipcore/data_ram/rtl')],
        '-work', out / 'work', *[out / 'inputs/vendor' / Path(name).name for name in data['vendor_sha256']],
        *[project / name for name in data['compile_sources']]]


def job_command(out, project, name):
    return [MS / 'vsim.exe', '-batch', '-lib', out / 'work', 'tb_data_bus_turnover',
        '-gTURNOVER=' + ('1' if name == 'key' else '0'),
        '+DAT=' + str(project / 'sim/data_bus_turnover/program.dat'),
        '+UNIT_LOG=' + str(out / (name + '.unit.log')),
        '+EV_LOG=' + str(out / (name + '.events.log')),
        '+BUS_LOG=' + str(out / (name + '.bus.log')),
        '-logfile', out / (name + '.transcript'), '-do', 'run -all; quit -f']


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tag', default=TAG)
    parser.add_argument('--check-inputs', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    data = require_inputs()
    assert args.tag == TAG
    out = HERE / 'build' / TAG
    assert not out.exists(), 'Preserve assigned run directory, no retry'
    if args.check_inputs or args.plan_only:
        print('RESULT: PASS Task032 inputs; reference82/requests49; HDL NOT_RUN; ISA=0')
        if args.plan_only:
            print(json.dumps(dict(tag=TAG, jobs=['vlib','compile','control','key'],
                module_count=38, timeouts=data['timeouts'], serial_opened=False, PDS_started=False), indent=2))
        return
    before = common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), completed={},
        HDL_started=False, PDS_started=False, serial_opened=False, board='NOT_RUN', timing='NOT_RUN')
    common.save(out / 'git_before.json', before)
    common.save(out / 'result.json', result)
    try:
        project = snapshot(out, data)
        result['HDL_started'] = True
        common.save(out / 'result.json', result)
        common.command([MS / 'vlib.exe', out / 'work'], out, out / 'vlib', 60)
        log = common.command(compile_command(out, project, data), out, out / 'compile', 60)
        modules = re.findall(r'-- Compiling module (\w+)', log)
        assert len(modules) == 38 and set(modules) == set(data['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        for name in ('control','key'):
            common.command(job_command(out, project, name), out, out / name, 180)
            result['completed'][name] = review_job(out, name, project)
            common.save(out / 'result.json', result)
        a, b = result['completed']['control'], result['completed']['key']
        assert a['unit_cycles'] - b['unit_cycles'] == 31
        assert b['fields']['cycles'] < a['fields']['cycles'], 'No integrated cycle improvement'
        assert b['fields']['mem_wait'] < a['fields']['mem_wait'], 'No integrated memory wait improvement'
        assert require_inputs() == data
        after = common.git_snapshot()
        common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during execution'
        result.update(status='DATA_BUS_RESPONSE_TURNOVER_KEY_GROUP_PASS', inputs_unchanged=True,
            git_unchanged=True, unit_cycles_saved=31,
            soc_cycles_saved=a['fields']['cycles']-b['fields']['cycles'],
            soc_mem_wait_saved=a['fields']['mem_wait']-b['fields']['mem_wait'])
        print('RESULT: PASS Task032 key group; board/timing NOT_RUN')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
