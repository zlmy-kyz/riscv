"""Task032 timing repair: instruction-response selector fix, key only.

The bridge now presets response_from_inst_drm=1 for x32 instruction requests instead
of deriving it from inst_line_hit. The fix must not add a cycle, so the key SoC result
has to be *identical* to the reviewed pre-repair key (617 cycles / 415 memory wait /
18 SoC turnarounds). The control run is reused from its review receipt.

Self-check before any native command:
  * compared with inputs_ip_count_key_resume.json the only changed project file is
    myriscv/dual_sram_to_pango_ddr_bridge.v (97273a85... -> 1df26c25...);
  * checker / TB / CPU / interconnect and every frozen stimulus, reference, compile
    source, include closure and timeout are unchanged;
  * the active checker is still exactly the frozen file with the single device-spec
    notice-count correction;
  * the reused control receipt and the reviewed pre-repair key receipt still hash to
    their bound SHAs and carry the counters this run must reproduce exactly.
"""
import argparse
import ast
import json
import re
from pathlib import Path

import run as base
from check_evidence import review_job

HERE = base.HERE
ROOT = base.ROOT
MS = base.MS

MANIFEST = HERE / 'inputs_timing_repair.json'
TAG = 'ds_data_bus_turnover_timing_repair_20261014_a'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
CHECKER = 'sim/data_bus_turnover/check_evidence.py'
FROZEN_CHECKER = ('sim/data_bus_turnover/build/'
                  'ds_data_bus_response_turnover_grs_resume_20261014_a/inputs/project/'
                  'sim/data_bus_turnover/check_evidence.py')
CHECKER_ACTIVE = "['04030130'] * 2"
CHECKER_FROZEN = "['04030130'] * 4"
OLD_KEY_RUN = 'sim/data_bus_turnover/build/ds_data_bus_response_turnover_ip_count_key_20261014_a'


def sha(path):
    return base.sha(path)


def key_shape(review):
    """The exact key counters a timing-neutral repair must reproduce unchanged."""
    return dict(unit=review['unit'], unit_cycles=review['unit_cycles'], soc=review['soc'],
                fields=review['fields'], Errors=review['Errors'], Warnings=review['Warnings'])


def require_inputs():
    data = json.loads(base.common.read(MANIFEST))
    assert data['tag'] == TAG
    assert data['control_reused'] is True and data['key_only'] is True
    for name, digest in data['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed input: ' + name
        if name.endswith('.py'):
            ast.parse(base.common.read(ROOT / name), filename=name)
    for name, digest in {**data['vendor_sha256'], **data['tool_sha256']}.items():
        assert sha(name) == digest, name
    for name, digest in data['protected_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed original evidence: ' + name

    # --- previous identity: only the repaired bridge may differ ---------------
    previous = json.loads(base.common.read(ROOT / data['previous_manifest']))
    assert sha(ROOT / data['previous_manifest']) == data['previous_manifest_sha256']
    changed = {n for n, h in previous['project_sha256'].items()
               if data['project_sha256'].get(n) != h}
    assert changed == {BRIDGE}, 'Unauthorised project input change: %s' % sorted(changed)
    added = set(data['project_sha256']) - set(previous['project_sha256'])
    assert added == set(data['new_implementation_files']), sorted(added)
    for key in ('compile_sources', 'expected_modules', 'include_dependencies',
                'vendor_sha256', 'tool_sha256', 'timeouts'):
        assert data[key] == previous[key], 'Changed frozen field: ' + key
    for name in data['must_match_previous']:
        assert data['project_sha256'][name] == previous['project_sha256'][name], name
    assert previous['project_sha256'][BRIDGE] == data['bridge_repair']['sha_before']
    assert data['project_sha256'][BRIDGE] == data['bridge_repair']['sha_after']
    assert data['bridge_repair']['sha_before'] != data['bridge_repair']['sha_after']

    # --- the checker is still the single-line corrected file -----------------
    current = (ROOT / CHECKER).read_bytes()
    frozen = (ROOT / FROZEN_CHECKER).read_bytes()
    assert current.count(CHECKER_ACTIVE.encode()) == 1
    assert CHECKER_FROZEN.encode() not in current
    assert current.replace(CHECKER_ACTIVE.encode(), CHECKER_FROZEN.encode()) == frozen, \
        'Active checker is not the frozen file with exactly the notice-count correction'

    # --- reused control receipt ---------------------------------------------
    receipt = json.loads(base.common.read(ROOT / data['reused_control_review']))
    assert sha(ROOT / data['reused_control_review']) == data['reused_control_review_sha256']
    assert receipt['status'] == 'TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING'
    assert receipt['source_run'] == data['reused_control']['source_run']
    assert receipt['source_manifest_sha256'] == data['reused_control']['source_manifest_sha256']
    assert receipt['checked'] == data['reused_control']['checked']
    assert receipt['old_git_after'] == 'ABSENT_NOT_BACKFILLED'
    checked = data['reused_control']['checked']
    assert checked['unit_cycles'] == 64 and checked['unit']['turns'] == 0
    assert checked['fields']['cycles'] == 619 and checked['fields']['mem_wait'] == 443

    # --- reviewed pre-repair key receipt ------------------------------------
    key_receipt = json.loads(base.common.read(ROOT / data['reused_key_review']))
    assert sha(ROOT / data['reused_key_review']) == data['reused_key_review_sha256']
    assert key_receipt['status'] == 'DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS'
    assert key_receipt['manifest_sha256'] == data['reused_key']['manifest_sha256']
    assert key_receipt['checked_key'] == data['reused_key']['checked_key']
    assert key_receipt['HDL_rerun'] is False and key_receipt['CPU_changed'] is False
    expected = data['expected_key']
    assert key_receipt['checked_key'] == expected, 'Pre-repair key counters changed'

    # --- frozen stimulus/reference and include closure ----------------------
    assert base.check_includes(ROOT, data['compile_sources']) == data['include_dependencies']
    words = [int(w, 16) for w in base.common.read(HERE / 'program.dat').split()]
    assert json.loads(base.common.read(HERE / 'reference.json')) == base.reference(words)
    assert data['CPU_changed'] is False
    assert data['changed_design_files_this_round'] == [BRIDGE]
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
    assert 'GTP_GRS GRS_INST' in base.common.read(
        project / 'sim/data_bus_turnover/tb_data_bus_turnover.sv')
    for name in ('ipcore/inst_rom/rtl/inst_rom_init_param.v',
                 'ipcore/data_ram/rtl/data_ram_init_param.v'):
        assert (project / name).is_file(), 'Missing init parameter copy: ' + name
    assert sha(project / BRIDGE) == data['bridge_repair']['sha_after']
    return project


def check_key(review, data):
    """Exact reproduction of the reviewed pre-repair key, plus control deltas."""
    expected = data['expected_key']
    shape = key_shape(review)
    assert shape == expected, 'Repaired key differs from the reviewed pre-repair key'
    assert review['unit_cycles'] == 33 and review['unit']['turns'] == 51
    assert review['unit']['counts'] == {'UREQ': 100, 'URSP': 99, 'URESET': 1}
    fields = review['fields']
    assert fields['cycles'] == 617 and fields['mem_wait'] == 415 and fields['turns'] == 18
    assert fields['fence_wait'] == 8 and fields['events'] == 82
    assert fields['fault'] == 1 and fields['error_rsp'] == 1
    assert fields['mmio'] == 5 and fields['uart'] == 1 and fields['ram'] == 1 and fields['fence'] == 1
    assert fields['aw'] == 5 and fields['w'] == 5
    soc = review['soc']
    assert soc['counts']['CPU_REQ'] == soc['counts']['CPU_RSP'] == 49
    assert soc['counts']['AR'] == soc['counts']['R'] == 40
    assert soc['counts']['AW'] == soc['counts']['W'] == 5
    assert soc['counts']['TURN'] == 18 and soc['turns'] == 18
    assert soc['counts']['SIDE_MMIO'] == 6 and soc['counts']['SIDE_RAM'] == 2
    assert soc['counts']['SIDE_UART'] == 1 and soc['counts']['FENCE'] == 1
    assert soc['CPU_requests'] == 49
    assert review['Errors'] == 0 and review['Warnings'] == 0
    control = data['reused_control']['checked']
    return dict(unit_cycles_saved=control['unit_cycles'] - review['unit_cycles'],
                soc_cycles_saved=control['fields']['cycles'] - fields['cycles'],
                soc_mem_wait_saved=control['fields']['mem_wait'] - fields['mem_wait'],
                key_identical_to_pre_repair=True)


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
        print('RESULT: PASS Task032 instruction-response selector repair inputs; '
              'bridge %s->%s; control reused 64/619/443; key must stay 33/617/415/18; HDL NOT_RUN; ISA=0'
              % (data['bridge_repair']['sha_before'][:8], data['bridge_repair']['sha_after'][:8]))
        if args.plan_only:
            print(json.dumps(dict(tag=TAG, jobs=['vlib', 'compile', 'key'], module_count=38,
                                  control_reused=True, key_only=True,
                                  expected_key=data['expected_key'],
                                  timeouts=data['timeouts'], serial_opened=False, PDS_started=False), indent=2))
        return
    control = data['reused_control']
    before = base.common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), completed={}, HDL_started=False,
                  control_reused=True, key_only=True,
                  reused_control_review_sha256=data['reused_control_review_sha256'],
                  control_source_run=control['source_run'],
                  reused_key_review=data['reused_key_review'],
                  reused_key_review_sha256=data['reused_key_review_sha256'],
                  old_control_git_after='ABSENT_NOT_BACKFILLED',
                  bridge_sha_before=data['bridge_repair']['sha_before'],
                  bridge_sha_after=data['bridge_repair']['sha_after'],
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
        result['reused_key_checked'] = data['reused_key']['checked_key']
        result['deltas'] = check_key(review, data)
        base.common.save(out / 'result.json', result)
        assert require_inputs() == data
        after = base.common.git_snapshot()
        base.common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during execution'
        result.update(status='TASK032_INST_RESPONSE_SELECTOR_TIMING_REPAIR_KEY_PASS',
                      inputs_unchanged=True, git_unchanged=True, key_passed=True,
                      new_key_cycles=review['fields']['cycles'],
                      new_key_mem_wait=review['fields']['mem_wait'],
                      new_key_turns=review['fields']['turns'])
        print('RESULT: PASS Task032 instruction-response selector repair key; '
              'PDS timing/board NOT_RUN')
    except Exception as exc:  # noqa: BLE001
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        base.common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
