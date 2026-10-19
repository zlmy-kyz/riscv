"""Task032 closing entry: device-spec notice count corrected once, key only.

Authorised scope (Codex plan): reuse the original runner helpers, checker and
parameters, change only the run directory/tag, and dispatch exactly three native
jobs (vlib, vlog, key). The GRS-resume control run is reused from its reviewed
receipt instead of being re-executed.

Self-check at every start:
  * the previous 164-entry project input set differs in exactly one file
    (sim/data_bus_turnover/check_evidence.py);
  * stripping that one substitution makes the active checker byte-identical to
    the frozen copy of the crashed control run;
  * TB/interconnect/CPU/bridge identities, compile sources, include closure,
    module list and timeouts equal the previous manifest;
  * the reused control receipt still hashes to its bound SHA and its checked
    content still says 64 unit cycles / 619 SoC cycles / 443 memory-wait cycles.
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path

import run as base
from check_evidence import review_job

HERE = base.HERE
ROOT = base.ROOT
MS = base.MS

MANIFEST = HERE / 'inputs_ip_count_key_resume.json'
TAG = 'ds_data_bus_response_turnover_ip_count_key_20261014_a'
CHECKER = 'sim/data_bus_turnover/check_evidence.py'
OLD_FROZEN_CHECKER = ('sim/data_bus_turnover/build/'
                      'ds_data_bus_response_turnover_grs_resume_20261014_a/inputs/project/'
                      'sim/data_bus_turnover/check_evidence.py')
CONTROL_REVIEW = 'sim/data_bus_turnover/build/ip_count_key_preparation_20261014_a/control_review.json'
PREVIOUS_MANIFEST = 'sim/data_bus_turnover/inputs_grs_resume.json'
CHECKER_ACTIVE = "['04030130'] * 2"
CHECKER_FROZEN = "['04030130'] * 4"
EXPECTED_UNIT_SAVING = 31
EXPECTED_UNIT_KEY_CYCLES = 33
EXPECTED_UNIT_TURNS = 51


def sha(path):
    return base.sha(path)


def require_inputs():
    data = json.loads(base.common.read(MANIFEST))
    assert data['tag'] == TAG, 'Unexpected tag binding'
    assert data['control_reused'] is True and data['key_only'] is True
    for name, digest in data['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed input: ' + name
        if name.endswith('.py'):
            ast.parse(base.common.read(ROOT / name), filename=name)
    for name, digest in {**data['vendor_sha256'], **data['tool_sha256']}.items():
        assert sha(name) == digest, name
    for name, digest in data['protected_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed original evidence: ' + name

    # --- previous identity: exactly one project file may differ ---------------
    previous = json.loads(base.common.read(ROOT / data['previous_manifest']))
    assert sha(ROOT / data['previous_manifest']) == data['previous_manifest_sha256']
    changed = {n for n, h in previous['project_sha256'].items()
               if data['project_sha256'].get(n) != h}
    assert changed == {CHECKER}, 'Unauthorised project input change: %s' % sorted(changed)
    added = set(data['project_sha256']) - set(previous['project_sha256'])
    assert added == set(data['new_implementation_files']), sorted(added)
    for key in ('compile_sources', 'expected_modules', 'include_dependencies',
                'vendor_sha256', 'tool_sha256', 'timeouts'):
        assert data[key] == previous[key], 'Changed frozen field: ' + key
    for name in data['must_match_previous']:
        assert data['project_sha256'][name] == previous['project_sha256'][name], name
    assert sha(ROOT / data['old_frozen_checker']) == previous['project_sha256'][CHECKER]

    # --- the one authorised edit, verified at byte level ---------------------
    current = (ROOT / CHECKER).read_bytes()
    frozen = (ROOT / data['old_frozen_checker']).read_bytes()
    assert current.count(CHECKER_ACTIVE.encode()) == 1
    assert CHECKER_FROZEN.encode() not in current
    assert current.replace(CHECKER_ACTIVE.encode(), CHECKER_FROZEN.encode()) == frozen, \
        'The only authorised checker edit must be the exact IPSpecCheck count correction'

    # --- reused control receipt ---------------------------------------------
    receipt = json.loads(base.common.read(ROOT / data['reused_control_review']))
    assert sha(ROOT / data['reused_control_review']) == data['reused_control_review_sha256']
    assert receipt['status'] == 'TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING'
    assert receipt['source_run'] == data['reused_control']['source_run']
    assert receipt['source_manifest_sha256'] == data['reused_control']['source_manifest_sha256']
    assert receipt['checked'] == data['reused_control']['checked']
    assert receipt['old_git_after'] == 'ABSENT_NOT_BACKFILLED'
    assert receipt['key'] == 'NOT_RUN' and receipt['HDL_rerun'] is False
    checked = data['reused_control']['checked']
    assert checked['unit_cycles'] == 64
    assert checked['unit']['turns'] == 0 and checked['unit']['counts']['URESET'] == 1
    assert checked['fields']['cycles'] == 619 and checked['fields']['mem_wait'] == 443
    assert checked['fields']['turns'] == 0 and checked['fields']['fence_wait'] == 8

    # --- frozen stimulus/reference and include closure ----------------------
    assert base.check_includes(ROOT, data['compile_sources']) == data['include_dependencies']
    words = [int(w, 16) for w in base.common.read(HERE / 'program.dat').split()]
    assert json.loads(base.common.read(HERE / 'reference.json')) == base.reference(words)
    assert data['CPU_changed'] is False
    assert data['changed_design_files'] == ['myriscv/data_bus_interconnect.v']
    return data


def snapshot(out, data):
    project = out / 'inputs/project'
    for name, digest in data['project_sha256'].items():
        dst = project / name
        dst.parent.mkdir(parents=True, exist_ok=True)
        base.shutil.copyfile(ROOT / name, dst)
        assert sha(dst) == digest
    for name, digest in data['vendor_sha256'].items():
        dst = out / 'inputs/vendor' / Path(name).name
        dst.parent.mkdir(parents=True, exist_ok=True)
        base.shutil.copyfile(name, dst)
        assert sha(dst) == digest
    base.shutil.copyfile(MANIFEST, out / 'inputs.json')
    assert sha(out / 'inputs.json') == sha(MANIFEST)
    assert base.check_includes(project, data['compile_sources']) == data['include_dependencies']
    tb = project / 'sim/data_bus_turnover/tb_data_bus_turnover.sv'
    text = base.common.read(tb)
    assert 'GTP_GRS GRS_INST' in text, 'GRS top-level instance missing in the run copy'
    for name in ('ipcore/inst_rom/rtl/inst_rom_init_param.v',
                 'ipcore/data_ram/rtl/data_ram_init_param.v'):
        assert (project / name).is_file(), 'Missing init parameter copy: ' + name
    return project


def check_key(review, control):
    checked = control['checked']
    assert review['unit_cycles'] == EXPECTED_UNIT_KEY_CYCLES, review['unit_cycles']
    assert review['unit']['turns'] == EXPECTED_UNIT_TURNS, review['unit']
    assert review['unit']['counts']['URESET'] == 1
    assert review['unit']['counts']['UREQ'] == review['unit']['counts']['URSP'] + 1
    assert checked['unit_cycles'] - review['unit_cycles'] == EXPECTED_UNIT_SAVING
    fields = review['fields']
    assert fields['turns'] > 0, 'key SoC has no accepted turnover'
    assert fields['cycles'] < checked['fields']['cycles'], 'No integrated cycle improvement'
    assert fields['mem_wait'] < checked['fields']['mem_wait'], 'No integrated memory-wait improvement'
    assert fields['fence_wait'] > 0
    assert fields['events'] == 82 and fields['fault'] == 1 and fields['error_rsp'] == 1
    assert fields['mmio'] == 5 and fields['uart'] == 1 and fields['ram'] == 1 and fields['fence'] == 1
    assert fields['aw'] == 5 and fields['w'] == 5
    soc = review['soc']
    assert soc['counts']['CPU_REQ'] == soc['counts']['CPU_RSP'] == 49
    assert soc['counts']['AW'] == soc['counts']['W'] == 5
    assert soc['counts']['AR'] == soc['counts']['R']
    assert soc['counts']['SIDE_MMIO'] == 6 and soc['counts']['SIDE_UART'] == 1
    assert soc['counts']['SIDE_RAM'] == 2 and soc['counts']['FENCE'] == 1
    assert soc['turns'] == fields['turns']
    assert soc['CPU_requests'] == 49
    return dict(unit_cycles_saved=checked['unit_cycles'] - review['unit_cycles'],
                soc_cycles_saved=checked['fields']['cycles'] - fields['cycles'],
                soc_mem_wait_saved=checked['fields']['mem_wait'] - fields['mem_wait'])


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
        print('RESULT: PASS Task032 ip-count key-resume inputs; checker edit=1 line; '
              'control reused 64/619/443; HDL NOT_RUN; ISA=0')
        if args.plan_only:
            print(json.dumps(dict(tag=TAG, jobs=['vlib', 'compile', 'key'], module_count=38,
                                  control_reused=True, control_source_run=data['reused_control']['source_run'],
                                  timeouts=data['timeouts'], serial_opened=False, PDS_started=False), indent=2))
        return
    control = data['reused_control']
    before = base.common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), completed={}, HDL_started=False,
                  control_reused=True, reused_control_review_sha256=data['reused_control_review_sha256'],
                  control_source_run=control['source_run'],
                  control_source_manifest_sha256=control['source_manifest_sha256'],
                  old_control_git_after='ABSENT_NOT_BACKFILLED', key_only=True,
                  PDS_started=False, serial_opened=False, board='NOT_RUN', timing='NOT_RUN')
    base.common.save(out / 'git_before.json', before)
    base.common.save(out / 'result.json', result)
    try:
        project = snapshot(out, data)
        result['HDL_started'] = True
        base.common.save(out / 'result.json', result)
        base.common.command([MS / 'vlib.exe', out / 'work'], out, out / 'vlib', 60)
        log = base.common.command(base.compile_command(out, project, data), out, out / 'compile', 60)
        modules = re.findall(r'-- Compiling module (\w+)', log)
        assert len(modules) == 38 and set(modules) == set(data['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        base.common.command(base.job_command(out, project, 'key'), out, out / 'key', 180)
        review = review_job(out, 'key', project)
        result['completed']['key'] = review
        result['control_reused_check'] = control['checked']
        result['deltas'] = check_key(review, control)
        base.common.save(out / 'result.json', result)
        assert require_inputs() == data
        after = base.common.git_snapshot()
        base.common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during execution'
        result.update(status='DATA_BUS_RESPONSE_TURNOVER_KEY_ONLY_WITH_REUSED_CONTROL_PASS',
                      inputs_unchanged=True, git_unchanged=True, key_passed=True)
        print('RESULT: PASS Task032 key-only with reused control; board/timing NOT_RUN')
    except Exception as exc:  # noqa: BLE001
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        base.common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
