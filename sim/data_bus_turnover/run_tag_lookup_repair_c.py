"""Task032 second timing repair, re-run C: parallel I-tag lookup, key plus look-up group.

Third authorised attempt (A: console path + trace counter; B: look-up checker state
model, fixed and re-verified offline against the run B trace before sealing). The A
and B manifests, run directories and reports are preserved untouched.

The bridge compares the 64 fixed I tag rows in parallel and decodes the index
separately. The repair must not add a cycle, so the original SoC key has to reproduce
the reviewed key exactly (33 unit / 617 SoC / 415 memory wait / 18 turnarounds), and
the look-up group must match the fill invariant for every one of the 64 rows.

Jobs dispatched: vlib, vlog, original SoC key, tb_inst_tag_lookup. Control is reused.
"""
import argparse
import ast
import json
import re
from pathlib import Path

import run as base
from check_evidence import review_job
from check_tag_lookup import review as review_lookup

HERE = base.HERE
ROOT = base.ROOT
MS = base.MS

MANIFEST = HERE / 'inputs_tag_lookup_repair_c.json'
TAG = 'ds_data_bus_tag_lookup_repair_c_20261014_a'
PREVIOUS = 'sim/data_bus_turnover/inputs_tag_lookup_repair_b.json'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
CHECKER = 'sim/data_bus_turnover/check_evidence.py'
FROZEN_CHECKER = ('sim/data_bus_turnover/build/'
                  'ds_data_bus_response_turnover_grs_resume_20261014_a/inputs/project/'
                  'sim/data_bus_turnover/check_evidence.py')
CHECKER_ACTIVE = "['04030130'] * 2"
CHECKER_FROZEN = "['04030130'] * 4"
LOOKUP_TB = 'sim/data_bus_turnover/tb_inst_tag_lookup.sv'
CONSOLE = 'tag_lookup.log'
TRACE = 'lookup.log'


def sha(path):
    return base.sha(path)


def require_inputs():
    data = json.loads(base.common.read(MANIFEST))
    assert data['tag'] == TAG
    assert data['control_reused'] is True and data['key_replayed'] is True
    for name, digest in data['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed input: ' + name
        if name.endswith('.py'):
            ast.parse(base.common.read(ROOT / name), filename=name)
    for name, digest in {**data['vendor_sha256'], **data['tool_sha256']}.items():
        assert sha(name) == digest, name
    for name, digest in data['protected_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed original evidence: ' + name

    # --- previous identity: only the fixed look-up checker may differ ---------
    previous = json.loads(base.common.read(ROOT / PREVIOUS))
    assert sha(ROOT / data['previous_manifest']) == data['previous_manifest_sha256']
    changed = {n for n, h in previous['project_sha256'].items()
               if data['project_sha256'].get(n) != h}
    assert changed == set(data['changed_project_files']), \
        'Unauthorised project input change: %s' % sorted(changed)
    added = set(data['project_sha256']) - set(previous['project_sha256'])
    assert added == set(data['new_implementation_files']), sorted(added)
    for name in data['must_match_previous']:
        assert data['project_sha256'][name] == previous['project_sha256'][name], name
    assert previous['project_sha256'][BRIDGE] == data['bridge_repair']['sha_after']
    assert data['compile_sources'] == previous['compile_sources']
    assert data['expected_modules'] == previous['expected_modules']
    assert len(data['expected_modules']) == 39
    for key in ('include_dependencies', 'vendor_sha256', 'tool_sha256', 'timeouts'):
        assert data[key] == previous[key], 'Changed frozen field: ' + key

    # --- the original key checker is still the corrected frozen file ----------
    current = (ROOT / CHECKER).read_bytes()
    frozen = (ROOT / FROZEN_CHECKER).read_bytes()
    assert current.count(CHECKER_ACTIVE.encode()) == 1
    assert CHECKER_FROZEN.encode() not in current
    assert current.replace(CHECKER_ACTIVE.encode(), CHECKER_FROZEN.encode()) == frozen

    # --- reused receipts ------------------------------------------------------
    receipt = json.loads(base.common.read(ROOT / data['reused_control_review']))
    assert sha(ROOT / data['reused_control_review']) == data['reused_control_review_sha256']
    assert receipt['status'] == 'TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING'
    assert receipt['checked'] == data['reused_control']['checked']
    key_receipt = json.loads(base.common.read(ROOT / data['reused_key_review']))
    assert sha(ROOT / data['reused_key_review']) == data['reused_key_review_sha256']
    assert key_receipt['status'] == 'DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS'
    assert key_receipt['checked_key'] == data['reused_key']['checked_key'] == data['expected_key']
    assert data['expected_key']['fields']['cycles'] == 617
    assert data['expected_key']['fields']['mem_wait'] == 415
    assert data['expected_key']['fields']['turns'] == 18
    prior = json.loads(base.common.read(ROOT / data['previous_timing_review']))
    assert sha(ROOT / data['previous_timing_review']) == data['previous_timing_review_sha256']
    assert prior['status'] == 'TASK032_FIRST_SELECTOR_REPAIR_RAW_FUNCTIONAL_REVIEW_PASS_TIMING_FAIL'
    assert data['previous_timing_review_sha256'] == \
        '4de7282d07bd407560b9f1496cc4d78fbdd8dbe66cdfd7b4a5a0ed0336e4e319'

    # --- frozen stimulus/reference and include closure ------------------------
    assert base.check_includes(ROOT, data['compile_sources']) == data['include_dependencies']
    words = [int(w, 16) for w in base.common.read(HERE / 'program.dat').split()]
    assert json.loads(base.common.read(HERE / 'reference.json')) == base.reference(words)
    assert data['CPU_changed'] is False
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
    assert 'GTP_GRS GRS_INST' in base.common.read(project / LOOKUP_TB)
    for name in ('ipcore/inst_rom/rtl/inst_rom_init_param.v',
                 'ipcore/data_ram/rtl/data_ram_init_param.v'):
        assert (project / name).is_file(), 'Missing init parameter copy: ' + name
    assert sha(project / BRIDGE) == data['bridge_repair']['sha_after']
    return project


def lookup_command(out):
    return [MS / 'vsim.exe', '-batch', '-lib', out / 'work', 'tb_inst_tag_lookup',
            '+LOOKUP_LOG=' + str(out / TRACE),
            '-logfile', out / 'lookup.transcript', '-do', 'run -all; quit -f']


def check_lookup(out, data):
    # The job's stdout is captured by command() as tag_lookup.log; the testbench
    # writes its OBS/TBL trace to lookup.log. Compare console against transcript.
    console = base.common.read(out / CONSOLE)
    transcript = base.common.read(out / 'lookup.transcript')
    assert console.strip() == transcript.strip(), 'lookup console/transcript differ'
    assert '$finish' in console and 'Errors: 0, Warnings: 0' in console
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', console)
    assert re.findall(r'IPSpecCheck: (\d+)', console) == ['04030130'] * 2, 'lookup device notices'
    result = review_lookup(out / TRACE)
    expected = data['lookup_expected']
    assert result['det'] == expected['det'] and result['rnd'] == expected['rnd']
    assert result['det_rows'] == expected['rows'] and result['high_bits'] == expected['high_bits']
    assert result['random_seed'] == expected['seed']
    assert result['tables'] == expected['tables']
    assert result['mismatches'] == 0 and result['hits'] > 0 and result['misses'] > 0
    return result


def check_key(review, data):
    expected = data['expected_key']
    shape = dict(unit=review['unit'], unit_cycles=review['unit_cycles'], soc=review['soc'],
                 fields=review['fields'], Errors=review['Errors'], Warnings=review['Warnings'])
    assert shape == expected, 'Repaired key differs from the reviewed key'
    control = data['reused_control']['checked']
    return dict(unit_cycles_saved=control['unit_cycles'] - review['unit_cycles'],
                soc_cycles_saved=control['fields']['cycles'] - review['fields']['cycles'],
                soc_mem_wait_saved=control['fields']['mem_wait'] - review['fields']['mem_wait'],
                key_identical_to_reviewed=True)


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
        print('RESULT: PASS Task032 parallel I-tag lookup repair C inputs; bridge %s; '
              'key must stay 33/617/415/18; lookup det=%d rnd=%d rows=%d high_bits=%d tables=%d; '
              'HDL NOT_RUN; ISA=0'
              % (data['bridge_repair']['sha_after'][:8],
                 data['lookup_expected']['det'], data['lookup_expected']['rnd'],
                 data['lookup_expected']['rows'], data['lookup_expected']['high_bits'],
                 data['lookup_expected']['tables']))
        if args.plan_only:
            print(json.dumps(dict(tag=TAG, jobs=['vlib', 'compile', 'key', 'tag_lookup'],
                                  module_count=39, control_reused=True,
                                  lookup_expected=data['lookup_expected'],
                                  expected_key=data['expected_key'],
                                  timeouts=data['timeouts'], serial_opened=False,
                                  PDS_started=False), indent=2))
        return
    control = data['reused_control']
    before = base.common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), completed={}, HDL_started=False,
                  control_reused=True, key_replayed=True,
                  retry_of='ds_data_bus_tag_lookup_repair_b_20261014_a',
                  retry_reason=('run B stopped in the look-up checker state model, which was fixed and '
                                're-verified offline against the run B trace before this attempt'),
                  reused_control_review_sha256=data['reused_control_review_sha256'],
                  control_source_run=control['source_run'],
                  reused_key_review_sha256=data['reused_key_review_sha256'],
                  previous_timing_review_sha256=data['previous_timing_review_sha256'],
                  old_control_git_after='ABSENT_NOT_BACKFILLED',
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
        assert len(modules) == 39 and set(modules) == set(data['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        # key first: the look-up group is only dispatched after the key passes
        base.common.command(base.job_command(out, project, 'key'), out, out / 'key', 180)
        review = review_job(out, 'key', project)
        result['completed']['key'] = review
        result['reused_key_checked'] = data['expected_key']
        result['deltas'] = check_key(review, data)
        base.common.save(out / 'result.json', result)
        base.common.command(lookup_command(out), out, out / 'tag_lookup', 60)
        result['completed']['tag_lookup'] = check_lookup(out, data)
        base.common.save(out / 'result.json', result)
        assert require_inputs() == data
        after = base.common.git_snapshot()
        base.common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during execution'
        result.update(status='TASK032_PARALLEL_INST_TAG_LOOKUP_REPAIR_KEY_AND_LOOKUP_PASS',
                      inputs_unchanged=True, git_unchanged=True, key_passed=True,
                      lookup_passed=True,
                      new_key_cycles=review['fields']['cycles'],
                      new_key_mem_wait=review['fields']['mem_wait'],
                      new_key_turns=review['fields']['turns'])
        print('RESULT: PASS Task032 parallel I-tag lookup repair key + lookup group; '
              'PDS timing/board NOT_RUN')
    except Exception as exc:  # noqa: BLE001
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        base.common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
