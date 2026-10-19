"""Task032 B-only protocol resume, re-run B (reserved-word fix).

The first attempt stopped in vlog because the protocol testbench used the
SystemVerilog reserved word `edge` as a task parameter; the identifier is renamed to
`edge_id` with no logic, stimulus or criteria change. The original SoC key and the
group A acceptance-edge evidence are reused from the partial receipt; this entry only
measures the rewritten race-free protocol group. Jobs: vlib, vlog, B-only vsim.
"""
import argparse
import ast
import json
import re
from pathlib import Path

import run as base
from check_inst_lookup_protocol_resume import PLAN, plan_summary
from check_inst_lookup_protocol_resume import review as review_protocol

HERE = base.HERE
ROOT = base.ROOT
MS = base.MS

MANIFEST = HERE / 'inputs_inst_lookup_protocol_resume_b.json'
TAG = 'ds_data_bus_inst_lookup_protocol_resume_b_20261014_a'
PREVIOUS = 'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume.json'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
PROTOCOL_TB = 'sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv'
CHECKER = 'sim/data_bus_turnover/check_evidence.py'
FROZEN_CHECKER = ('sim/data_bus_turnover/build/'
                  'ds_data_bus_response_turnover_grs_resume_20261014_a/inputs/project/'
                  'sim/data_bus_turnover/check_evidence.py')
CHECKER_ACTIVE = "['04030130'] * 2"
CHECKER_FROZEN = "['04030130'] * 4"
HANDOFF = 'doc/CODEX_HANDOFF.md'
HANDOFF_SAVED = ('sim/data_bus_turnover/build/'
                 'registered_protocol_repair_preparation_20261014_a/handoff_before_review.md')
HANDOFF_SHA = '55be65f67944f2dfcf143ed8d19606a6244dfa68de99f46efd1ec5e2a880949c'
CONSOLE = 'protocol.log'
EDGE_LOG = 'edge.log'
PLAN_LOG = 'plan.log'


def sha(path):
    return base.sha(path)


def require_inputs():
    data = json.loads(base.common.read(MANIFEST))
    assert data['tag'] == TAG
    assert data['b_only'] is True and data['key_and_A_reused'] is True
    assert data['jobs'] == ['vlib', 'compile', 'inst_lookup_protocol_resume']
    for name, digest in data['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed input: ' + name
        if name.endswith('.py'):
            ast.parse(base.common.read(ROOT / name), filename=name)
    for name, digest in {**data['vendor_sha256'], **data['tool_sha256']}.items():
        assert sha(name) == digest, name
    for name, digest in data['protected_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed original evidence: ' + name

    # --- previous identity: only the fixed protocol testbench may differ ------
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
    assert data['compile_sources'] == previous['compile_sources']
    assert data['expected_modules'] == previous['expected_modules']
    assert len(data['expected_modules']) == 39
    for key in ('include_dependencies', 'vendor_sha256', 'tool_sha256', 'timeouts'):
        assert data[key] == previous[key], 'Changed frozen field: ' + key

    # --- the reserved word must be gone from the code, not from string data ---
    for line in base.common.read(ROOT / PROTOCOL_TB).splitlines():
        code = line.split('//')[0]
        if '"' in code:
            continue
        for word in code.replace('edge_id', '').replace('tok_acc_edge', '').replace(
                'fd_edge', '').split():
            assert word != 'edge', 'reserved word still used as an identifier: ' + line

    # --- historical hand-off identity relocation -----------------------------
    assert HANDOFF not in data['protected_evidence_sha256']
    assert data['protected_evidence_sha256'][HANDOFF_SAVED] == HANDOFF_SHA
    assert data['historical_identity_relocations'][HANDOFF]['saved_path'] == HANDOFF_SAVED

    # --- the original key checker is still the corrected frozen file ----------
    current = (ROOT / CHECKER).read_bytes()
    frozen = (ROOT / FROZEN_CHECKER).read_bytes()
    assert current.count(CHECKER_ACTIVE.encode()) == 1
    assert CHECKER_FROZEN.encode() not in current
    assert current.replace(CHECKER_ACTIVE.encode(), CHECKER_FROZEN.encode()) == frozen

    # --- partial review receipt and reused evidence ---------------------------
    receipt = json.loads(base.common.read(ROOT / data['partial_review']['path']))
    assert sha(ROOT / data['partial_review']['path']) == data['partial_review']['sha256']
    assert receipt['status'] == 'TASK032_REGISTERED_LOOKUP_KEY_AND_A_RAW_PASS_B_FAILED'
    assert receipt['checked_key'] == data['partial_review']['checked_key'] == data['expected_key']
    assert receipt['checked_A'] == data['partial_review']['checked_A']
    assert data['expected_key']['fields']['cycles'] == 617
    assert data['expected_key']['fields']['mem_wait'] == 415
    assert receipt['checked_A']['A_det'] == 1472 and receipt['checked_A']['A_rnd'] == 512
    for name, digest in receipt.get('prior_files_sha256', {}).items():
        assert data['protected_evidence_sha256'].get(name) == digest, \
            'receipt prior file not protected with the same identity: ' + name
    plan = plan_summary()
    assert data['stimulus_plan'] == plan, 'sealed stimulus plan changed'
    assert len(PLAN) == plan['tokens'], (len(PLAN), plan)
    assert data['bridge_repair']['sha_after'] == sha(ROOT / BRIDGE)

    # --- frozen stimulus/reference and include closure ------------------------
    assert base.check_includes(ROOT, data['compile_sources']) == data['include_dependencies']
    words = [int(w, 16) for w in base.common.read(HERE / 'program.dat').split()]
    assert json.loads(base.common.read(HERE / 'reference.json')) == base.reference(words)
    assert data['CPU_changed'] is False
    assert data['changed_design_files_this_round'] == []
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
    assert 'GTP_GRS GRS_INST' in base.common.read(project / PROTOCOL_TB)
    for name in ('ipcore/inst_rom/rtl/inst_rom_init_param.v',
                 'ipcore/data_ram/rtl/data_ram_init_param.v'):
        assert (project / name).is_file(), 'Missing init parameter copy: ' + name
    assert sha(project / BRIDGE) == data['bridge_repair']['sha_after']
    return project


def protocol_command(out):
    return [MS / 'vsim.exe', '-batch', '-lib', out / 'work', 'tb_inst_lookup_protocol_resume',
            '+EDGE_LOG=' + str(out / EDGE_LOG), '+PLAN_LOG=' + str(out / PLAN_LOG),
            '-logfile', out / 'protocol.transcript', '-do', 'run -all; quit -f']


def check_protocol(out, data):
    console = base.common.read(out / CONSOLE)
    transcript = base.common.read(out / 'protocol.transcript')
    assert console.strip() == transcript.strip(), 'protocol console/transcript differ'
    assert '$finish' in console and 'Errors: 0, Warnings: 0' in console
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', console)
    assert re.findall(r'IPSpecCheck: (\d+)', console) == ['04030130'] * 2, 'device notices'
    printed = re.findall(r'RESULT: PASS inst_lookup_protocol_resume (.*)', console)
    assert len(printed) == 1, 'missing or duplicated protocol PASS line'
    result = review_protocol(out / EDGE_LOG, out / PLAN_LOG)
    plan = data['stimulus_plan']
    for key in ('scenarios', 'tokens', 'accepts', 'responses', 'cancels'):
        assert result[key] == plan[key], (key, result.get(key), plan)
    assert result['accepts'] == result['responses'] + result['cancels']
    assert result['mismatches'] == 0
    fields = dict(kv.split('=') for kv in printed[0].split())
    for key in ('scenarios', 'tokens', 'accepts', 'responses', 'cancels', 'mismatches'):
        assert int(fields[key]) == int(result[key]), (key, fields, result)
    return dict(result)


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
        print('RESULT: PASS Task032 B-only protocol resume B inputs; bridge %s; jobs=%s; plan=%s; '
              'tb=%s; key/A reused; HDL NOT_RUN; ISA=0'
              % (data['bridge_repair']['sha_after'][:8], json.dumps(data['jobs']),
                 json.dumps(data['stimulus_plan']),
                 sha(ROOT / PROTOCOL_TB)[:16]))
        return
    before = base.common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), completed={}, HDL_started=False,
                  b_only=True, key_and_A_reused=True,
                  retry_of='ds_data_bus_inst_lookup_protocol_resume_20261014_a',
                  partial_review_sha256=data['partial_review']['sha256'],
                  reused_control_review_sha256=data['reused_control_review_sha256'],
                  reused_key_review_sha256=data['reused_key_review_sha256'],
                  user_reported_pds_timing=data['user_reported_pds_timing'],
                  old_control_git_after='ABSENT_NOT_BACKFILLED',
                  bridge_sha_after=data['bridge_repair']['sha_after'],
                  PDS_started=False, serial_opened=False, board='NOT_RUN', timing='NOT_RUN')
    after = None
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
        base.common.command(protocol_command(out), out, out / 'protocol', 180)
        result['completed']['inst_lookup_protocol_resume'] = check_protocol(out, data)
        base.common.save(out / 'result.json', result)
        assert require_inputs() == data
        after = base.common.git_snapshot()
        base.common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during execution'
        result.update(status='TASK032_REGISTERED_LOOKUP_REUSED_KEY_A_PROTOCOL_B_PASS',
                      inputs_unchanged=True, git_unchanged=True, protocol_passed=True)
        print('RESULT: PASS Task032 B-only protocol resume; PDS timing/board NOT_RUN')
    except Exception as exc:  # noqa: BLE001
        result.update(status='STOPPED_FIRST_FAILURE', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        if after is None:
            try:
                after = base.common.git_snapshot()
                base.common.save(out / 'git_after.json', after)
                result['git_after_captured_in_finally'] = True
            except Exception as exc:  # noqa: BLE001
                result['git_after_error'] = f'{type(exc).__name__}: {exc}'
        if after is not None:
            result['git_unchanged'] = before == after
        base.common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
