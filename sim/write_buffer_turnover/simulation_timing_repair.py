"""Task031 timing repair: one unchanged key group; DeepSeek executes once."""
import argparse
import ast
import inspect
import json
import re
import shutil
from pathlib import Path
from check_inputs import ROOT, HERE, sha
from check_include_dependencies import check_includes
from completion_irq_drain_reference import build_reference
import simulation_completion_runner as common
import check_completion_evidence as evidence

DESIGN = HERE / 'simulation_timing_repair_inputs.json'
TAG = 'ds_write_buffer_turnover_timing_repair_20261014_a'
MS = Path('D:/modelsim/win64pe')
OLD_GATE = HERE / 'build/codex_irq_contract_closure_20261014_a/codex_review.json'
REFERENCE = 'sim/write_buffer_turnover/timing_repair_reference.json'


def require_inputs():
    design = json.loads(common.read(DESIGN))
    assert design['fixed_tag'] == TAG and design['CPU_changed'] is False
    for name, digest in design['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed project input: ' + name
        if name.endswith('.py'):
            ast.parse(common.read(ROOT / name), filename=name)
    for name, digest in {**design['vendor_sha256'], **design['tool_sha256']}.items():
        assert sha(name) == digest, 'Changed external input: ' + name
    for name, digest in design['protected_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed prior evidence: ' + name
    prior = json.loads(common.read(OLD_GATE))
    assert prior['status'] == 'WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS'
    assert prior['control']['cycles'] == 49 and prior['key']['cycles'] == 44
    assert check_includes(ROOT, design['compile_sources']) == design['include_dependencies']
    assert json.loads(common.read(ROOT / REFERENCE)) == build_reference(ROOT / design['cpu_image'])
    assert sum(g['checks'] for g in design['groups']) == 889
    return design


def snapshot(out, design):
    project = out / 'inputs/project'
    for name, digest in design['project_sha256'].items():
        dst = project / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / name, dst)
        assert sha(dst) == digest, name
    shutil.copyfile(DESIGN, out / 'simulation_timing_repair_inputs.json')
    vendors = []
    for name, digest in design['vendor_sha256'].items():
        dst = out / 'inputs/vendor' / Path(name).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(name, dst)
        assert sha(dst) == digest
        vendors.append(dst)
    assert check_includes(project, design['compile_sources']) == design['include_dependencies']
    return project, vendors


def compile_command(out, project, design):
    return [MS / 'vlog.exe', '-sv', *['+incdir+' + (project / name).as_posix() for name in (
        'myriscv', 'sim/write_buffer_turnover', 'ipcore/inst_rom/rtl', 'ipcore/data_ram/rtl')],
        '-work', out / 'work', *[out / 'inputs/vendor' / Path(name).name for name in design['vendor_sha256']],
        *[project / name for name in design['compile_sources']]]


def key_command(out, project, design):
    return [MS / 'vsim.exe', '-batch', '-lib', out / 'work', 'tb_write_buffer_turnover_completion',
        '-gPOSTED=1', '-gTURNOVER=1', '+CPU_IMAGE=' + str(project / design['cpu_image']),
        '+EV_LOG=' + str(out / 'key.events.log'), '+BUS_LOG=' + str(out / 'key.bus.log'),
        *['+%s=%d' % (key, value) for key, value in design['plusargs'].items() if key != 'CPU_IMAGE'],
        '-logfile', out / 'key.transcript', '-do', 'run -all; quit -f']


def review_key(out, project, design):
    # Reuse every existing strict predicate; only bind the corrected independent
    # IRQ reference and image to the current immutable execution copy.
    source = inspect.getsource(evidence.review_job)
    assert source.count("HERE / 'completion_reference.json'") == 2
    namespace = dict(evidence.__dict__, HERE=project / 'sim/write_buffer_turnover',
                     CORRECTED_REFERENCE_PATH=project / REFERENCE)
    exec(compile(source.replace("HERE / 'completion_reference.json'", 'CORRECTED_REFERENCE_PATH'),
                 '<strict_key_review_corrected_reference>', 'exec'), namespace)
    return namespace['review_job'](out, 'key', design)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-inputs', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    parser.add_argument('--tag', default=TAG)
    args = parser.parse_args()
    design = require_inputs()
    assert args.tag == TAG
    out = HERE / 'build' / TAG
    assert not out.exists(), 'Preserve assigned directory; no retry or reuse'
    if args.check_inputs or args.plan_only:
        print('RESULT: PASS timing repair frozen inputs; HDL NOT_RUN; ISA=0')
        if args.plan_only:
            print(json.dumps(dict(tag=TAG, jobs=['vlib', 'compile', 'key'], modules=36,
                key_checks=889, events=430, reused_control_cycles=49,
                timeouts=design['timeouts'], serial_opened=False, PDS_started=False), indent=2))
        return
    before = common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(DESIGN), completed={},
        HDL_started=False, serial_opened=False, PDS_started=False, board='NOT_RUN', timing='NOT_RUN')
    common.save(out / 'git_before.json', before)
    common.save(out / 'result.json', result)
    try:
        project, _ = snapshot(out, design)
        result['HDL_started'] = True
        common.save(out / 'result.json', result)
        common.command([MS / 'vlib.exe', out / 'work'], out, out / 'vlib', 60)
        log = common.command(compile_command(out, project, design), out, out / 'compile', 60)
        modules = re.findall(r'-- Compiling module (\w+)', log)
        assert len(modules) == 36 and set(modules) == set(design['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        common.command(key_command(out, project, design), out, out / 'key', 180)
        result['completed']['key'] = review_key(out, project, design)
        assert result['completed']['key']['cycles'] == 44
        assert require_inputs() == design
        after = common.git_snapshot()
        common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during run'
        result.update(status='TASK031_TIMING_REPAIR_KEY_PASS', inputs_unchanged=True,
            git_unchanged=True, control_reused=True, controlled_cycles_saved=5)
        print('RESULT: PASS Task031 timing repair key889 EV430; PDS timing NOT_RUN')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
