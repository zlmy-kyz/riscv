"""Task032 registered instruction-look-up repair: original SoC key plus the new bridge group.

The bridge registers the per-row x32 instruction look-up results together with the
synchronous DRM read. The repair must not add a cycle, so the original SoC key has to
reproduce the reviewed key exactly (33 unit / 617 SoC / 415 memory wait / 18
turnarounds), and the new directed group must prove the acceptance-edge snapshot
(group A) and the real handshake/DRM/fill protocol (group B).

Jobs dispatched: vlib, vlog, original SoC key, tb_inst_lookup_registered. Control is
reused; the reviewed C gate belongs to the previous bridge and is bound only as a
historical comparison.
"""
import argparse
import ast
import json
import re
from pathlib import Path

import run as base
from check_evidence import review_job
from check_inst_lookup_registered import review as review_registered

HERE = base.HERE
ROOT = base.ROOT
MS = base.MS

MANIFEST = HERE / 'inputs_inst_lookup_registered_repair.json'
TAG = 'ds_data_bus_inst_lookup_registered_repair_20261014_a'
PREVIOUS = 'sim/data_bus_turnover/inputs_tag_lookup_repair_c.json'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
OLD_LOOKUP_TB = 'sim/data_bus_turnover/tb_inst_tag_lookup.sv'
NEW_LOOKUP_TB = 'sim/data_bus_turnover/tb_inst_lookup_registered.sv'
CHECKER = 'sim/data_bus_turnover/check_evidence.py'
FROZEN_CHECKER = ('sim/data_bus_turnover/build/'
                  'ds_data_bus_response_turnover_grs_resume_20261014_a/inputs/project/'
                  'sim/data_bus_turnover/check_evidence.py')
CHECKER_ACTIVE = "['04030130'] * 2"
CHECKER_FROZEN = "['04030130'] * 4"
CONSOLE = 'registered.log'
TRACE_A = 'lookup.log'
TRACE_B = 'bus.log'
EXPECTED_A_DET = 64 * 23
EXPECTED_A_RND = 64 * 8
EXPECTED_RND_HITS = 256
EXPECTED_RND_MISSES = 256


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

    # --- previous identity: only the repaired bridge may differ ---------------
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
    assert previous['project_sha256'][BRIDGE] == data['bridge_repair']['sha_before']
    assert data['project_sha256'][BRIDGE] == data['bridge_repair']['sha_after']
    sources = list(previous['compile_sources'])
    sources[sources.index(OLD_LOOKUP_TB)] = NEW_LOOKUP_TB
    assert data['compile_sources'] == sources, 'compile list must only swap the look-up top'
    modules = list(previous['expected_modules'])
    modules[modules.index('tb_inst_tag_lookup')] = 'tb_inst_lookup_registered'
    assert data['expected_modules'] == modules and len(modules) == 39
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
    c_gate = json.loads(base.common.read(ROOT / data['reused_C_gate']['path']))
    assert sha(ROOT / data['reused_C_gate']['path']) == data['reused_C_gate']['sha256']
    assert c_gate['manifest_sha256'] == data['previous_manifest_sha256']
    assert c_gate['checked_key'] == data['reused_C_gate']['checked_key'] == data['expected_key']
    assert data['bridge_repair']['sha_after'][:8] not in c_gate['manifest_sha256']
    static = json.loads(base.common.read(ROOT / data['static_preparation']['path']))
    assert sha(ROOT / data['static_preparation']['path']) == data['static_preparation']['sha256']
    assert static['new_bridge_sha256'] == data['bridge_repair']['sha_after']

    # --- frozen stimulus/reference and include closure ------------------------
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
    for tb in ('sim/data_bus_turnover/tb_data_bus_turnover.sv', NEW_LOOKUP_TB):
        assert 'GTP_GRS GRS_INST' in base.common.read(project / tb), 'missing GRS instance in ' + tb
    for name in ('ipcore/inst_rom/rtl/inst_rom_init_param.v',
                 'ipcore/data_ram/rtl/data_ram_init_param.v'):
        assert (project / name).is_file(), 'Missing init parameter copy: ' + name
    assert sha(project / BRIDGE) == data['bridge_repair']['sha_after']
    return project


def registered_command(out):
    return [MS / 'vsim.exe', '-batch', '-lib', out / 'work', 'tb_inst_lookup_registered',
            '+LOOKUP_LOG=' + str(out / TRACE_A), '+BUS_LOG=' + str(out / TRACE_B),
            '-logfile', out / 'registered.transcript', '-do', 'run -all; quit -f']


def check_registered(out, data):
    console = base.common.read(out / CONSOLE)
    transcript = base.common.read(out / 'registered.transcript')
    assert console.strip() == transcript.strip(), 'registered console/transcript differ'
    assert '$finish' in console and 'Errors: 0, Warnings: 0' in console
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', console)
    assert re.findall(r'IPSpecCheck: (\d+)', console) == ['04030130'] * 2, 'device notices'
    printed = re.findall(r'RESULT: PASS inst_lookup_registered (.*)', console)
    assert len(printed) == 1, 'missing or duplicated registered PASS line'
    result = review_registered(out / TRACE_A, out / TRACE_B)
    assert result['A_det'] == EXPECTED_A_DET, result['A_det']
    assert result['A_rnd'] == EXPECTED_A_RND, result['A_rnd']
    assert result['A_random_hits'] == EXPECTED_RND_HITS, result['A_random_hits']
    assert result['A_random_misses'] == EXPECTED_RND_MISSES, result['A_random_misses']
    assert result['A_rows'] == 64 and result['A_high_bits'] == 21
    assert result['A_mismatches'] == 0 and result['B_mismatches'] == 0
    assert result['B_scenarios'] >= 16, result['B_scenarios']
    assert result['B_accepts'] == result['B_responses'] + result['B_cancels'], result
    assert result['B_cancels'] == 3, result['B_cancels']
    assert result['B_properties'] >= 16, result['B_properties']
    fields = dict(kv.split('=') for kv in printed[0].split())
    assert int(fields['A_det']) == result['A_det'] and int(fields['A_rnd']) == result['A_rnd']
    assert int(fields['hits']) == result['A_hits'] and int(fields['misses']) == result['A_misses']
    assert int(fields['mismatches']) == 0
    assert int(fields['B_scenarios']) == result['B_scenarios']
    return dict(result)


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
        print('RESULT: PASS Task032 registered inst look-up inputs; bridge %s->%s; '
              'key must stay 33/617/415/18; group A det=%d rnd=%d rnd_hit=%d rnd_miss=%d; '
              'HDL NOT_RUN; ISA=0'
              % (data['bridge_repair']['sha_before'][:8], data['bridge_repair']['sha_after'][:8],
                 EXPECTED_A_DET, EXPECTED_A_RND, EXPECTED_RND_HITS, EXPECTED_RND_MISSES))
        if args.plan_only:
            print(json.dumps(dict(tag=TAG, jobs=['vlib', 'compile', 'key', 'inst_lookup_registered'],
                                  module_count=39, control_reused=True,
                                  expected_key=data['expected_key'],
                                  new_top=NEW_LOOKUP_TB, replaced_top=OLD_LOOKUP_TB,
                                  timeouts=data['timeouts'], serial_opened=False,
                                  PDS_started=False), indent=2))
        return
    control = data['reused_control']
    before = base.common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), completed={}, HDL_started=False,
                  control_reused=True, key_replayed=True,
                  reused_control_review_sha256=data['reused_control_review_sha256'],
                  control_source_run=control['source_run'],
                  reused_key_review_sha256=data['reused_key_review_sha256'],
                  reused_C_gate_sha256=data['reused_C_gate']['sha256'],
                  reused_C_gate_note='historical functional gate for the previous bridge only',
                  static_preparation_sha256=data['static_preparation']['sha256'],
                  user_reported_pds_timing=data['user_reported_pds_timing'],
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
        assert len(modules) == 39 and set(modules) == set(data['expected_modules'])
        assert 'Errors: 0, Warnings: 0' in log
        # key first: the new directed group is only dispatched after the key passes
        base.common.command(base.job_command(out, project, 'key'), out, out / 'key', 180)
        review = review_job(out, 'key', project)
        result['completed']['key'] = review
        result['reused_key_checked'] = data['expected_key']
        result['deltas'] = check_key(review, data)
        base.common.save(out / 'result.json', result)
        base.common.command(registered_command(out), out, out / 'registered', 180)
        result['completed']['inst_lookup_registered'] = check_registered(out, data)
        base.common.save(out / 'result.json', result)
        assert require_inputs() == data
        after = base.common.git_snapshot()
        base.common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during execution'
        result.update(status='TASK032_REGISTERED_INST_LOOKUP_KEY_AND_PROTOCOL_PASS',
                      inputs_unchanged=True, git_unchanged=True, key_passed=True,
                      registered_passed=True,
                      new_key_cycles=review['fields']['cycles'],
                      new_key_mem_wait=review['fields']['mem_wait'],
                      new_key_turns=review['fields']['turns'])
        print('RESULT: PASS Task032 registered inst look-up key + protocol group; '
              'PDS timing/board NOT_RUN')
    except Exception as exc:  # noqa: BLE001
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        base.common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
