"""Task032 B-only protocol completion (true same-edge AR/R and independent write data).

Successor of the resume E entry. The only compile top that changes is the B-only
testbench: `tb_inst_lookup_protocol_resume.sv` (kept byte-identical as a historical
input) is replaced in `compile_sources` by `tb_inst_lookup_protocol_completion.sv`,
which adds:

  * a genuine AR/R same posedge (the driver pre-drives R from the combinational
    ARVALID one phase before the DUT consumes it, never by moving an edge number);
  * byte-memory commits only on a real W completion, with AW address/data/strobe
    stability checked across an AW/W split;
  * true simultaneous inst/data requests with data priority and a held request;
  * a non-zero-lane partial-byte store with the untouched bytes preserved;
  * build-time scenario identity in plan.log and separate edge/log-line reporting.

Jobs: vlib 60s -> vlog 60s -> completion B-only vsim -batch 180s, each exactly once.
"""
import argparse
import ast
import json
import re
from pathlib import Path

import run as base
from check_inst_lookup_protocol_completion import PLAN, plan_summary
from check_inst_lookup_protocol_completion import review as review_protocol

HERE = base.HERE
ROOT = base.ROOT
MS = base.MS

MANIFEST = HERE / 'inputs_inst_lookup_protocol_completion.json'
TAG = 'ds_data_bus_inst_lookup_protocol_completion_20261014_a'
PREVIOUS = 'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_e.json'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
PROTOCOL_TB = 'sim/data_bus_turnover/tb_inst_lookup_protocol_completion.sv'
OLD_PROTOCOL_TB = 'sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv'
NEW_MODULE = 'tb_inst_lookup_protocol_completion'
OLD_MODULE = 'tb_inst_lookup_protocol_resume'
HANDOFF = 'doc/CODEX_HANDOFF.md'
HANDOFF_SAVED = ('sim/data_bus_turnover/build/'
                 'registered_protocol_repair_preparation_20261014_a/handoff_before_review.md')
HANDOFF_SHA = '55be65f67944f2dfcf143ed8d19606a6244dfa68de99f46efd1ec5e2a880949c'
CONSOLE = 'protocol.log'
EDGE_LOG = 'edge.log'
PLAN_LOG = 'plan.log'
CHECKER = 'sim/data_bus_turnover/check_inst_lookup_protocol_completion.py'
RUNNER = 'sim/data_bus_turnover/run_inst_lookup_protocol_completion.py'
SEALER = 'sim/data_bus_turnover/seal_inst_lookup_protocol_completion.py'
NEW_IMPLEMENTATION = [PROTOCOL_TB, CHECKER, RUNNER, SEALER]
JOBS = ['vlib', 'compile', 'inst_lookup_protocol_completion']


def sha(path):
    return base.sha(path)


def require_inputs():
    data = json.loads(base.common.read(MANIFEST))
    assert data['tag'] == TAG
    assert data['b_only'] is True and data['key_and_A_reused'] is True
    assert data['jobs'] == JOBS, data['jobs']
    for name, digest in data['project_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed input: ' + name
        if name.endswith('.py'):
            ast.parse(base.common.read(ROOT / name), filename=name)
    for name, digest in {**data['vendor_sha256'], **data['tool_sha256']}.items():
        assert sha(name) == digest, name
    for name, digest in data['protected_evidence_sha256'].items():
        assert sha(ROOT / name) == digest, 'Changed original evidence: ' + name

    # --- previous identity: no existing project file may change ---------------
    previous = json.loads(base.common.read(ROOT / PREVIOUS))
    assert sha(ROOT / data['previous_manifest']) == data['previous_manifest_sha256']
    changed = {n for n, h in previous['project_sha256'].items()
               if data['project_sha256'].get(n) != h}
    assert changed == set(data['changed_project_files']) == set(), \
        'Unauthorised project input change: %s' % sorted(changed)
    added = set(data['project_sha256']) - set(previous['project_sha256'])
    assert added == set(data['new_implementation_files']) == set(NEW_IMPLEMENTATION), sorted(added)
    for name in data['must_match_previous']:
        assert data['project_sha256'][name] == previous['project_sha256'][name], name
    # --- the only compile-top substitution ------------------------------------
    assert OLD_PROTOCOL_TB in previous['compile_sources']
    assert OLD_PROTOCOL_TB not in data['compile_sources']
    assert PROTOCOL_TB in data['compile_sources']
    expected = [PROTOCOL_TB if n == OLD_PROTOCOL_TB else n for n in previous['compile_sources']]
    assert data['compile_sources'] == expected, 'compile source substitution changed'
    assert OLD_PROTOCOL_TB in data['project_sha256'], 'historical testbench dropped'
    assert data['project_sha256'][OLD_PROTOCOL_TB] == previous['project_sha256'][OLD_PROTOCOL_TB]
    modules = [NEW_MODULE if m == OLD_MODULE else m for m in previous['expected_modules']]
    assert data['expected_modules'] == modules, 'module list substitution changed'
    assert OLD_MODULE not in data['expected_modules'] and NEW_MODULE in data['expected_modules']
    assert len(data['expected_modules']) == 39
    for key in ('include_dependencies', 'vendor_sha256', 'tool_sha256', 'timeouts'):
        assert data[key] == previous[key], 'Changed frozen field: ' + key

    # --- the new testbench must not reuse the SystemVerilog reserved word `edge`
    for line in base.common.read(ROOT / PROTOCOL_TB).splitlines():
        code = line.split('//')[0]
        if '"' in code:
            continue
        for word in code.replace('edge_id', '').replace('tok_acc_edge', '').replace(
                'fd_edge', '').replace('edge_logged', '').replace('first_logged', '').replace(
                'edge_path', '').split():
            assert word != 'edge', 'reserved word still used as an identifier: ' + line

    # --- historical hand-off identity relocation -----------------------------
    assert HANDOFF not in data['protected_evidence_sha256']
    assert data['protected_evidence_sha256'][HANDOFF_SAVED] == HANDOFF_SHA
    assert data['historical_identity_relocations'][HANDOFF]['saved_path'] == HANDOFF_SAVED

    # --- partial review receipt and reused key/A evidence ---------------------
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

    # --- sealed stimulus plan and coverage thresholds -------------------------
    plan = plan_summary()
    assert data['stimulus_plan'] == plan, 'sealed stimulus plan changed'
    assert len(PLAN) == plan['tokens'], (len(PLAN), plan)
    contract = data['coverage_contract']
    for key in ('ar_r_same_min', 'dual_present_min', 'tokens', 'scenarios',
                'accepts', 'responses', 'cancels', 'resets', 'plan_sha256'):
        assert contract[key] == plan[key], ('coverage contract', key)
    assert contract['ar_r_same_min'] >= 1 and contract['dual_present_min'] >= 1

    # --- frozen bridge and include closure ------------------------------------
    assert base.check_includes(ROOT, data['compile_sources']) == data['include_dependencies']
    words = [int(w, 16) for w in base.common.read(HERE / 'program.dat').split()]
    assert json.loads(base.common.read(HERE / 'reference.json')) == base.reference(words)
    assert data['CPU_changed'] is False
    assert data['changed_design_files_this_round'] == []
    assert data['bridge_repair']['sha_after'] == sha(ROOT / BRIDGE)
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
    return [MS / 'vsim.exe', '-batch', '-lib', out / 'work', NEW_MODULE,
            '+EDGE_LOG=' + str(out / EDGE_LOG), '+PLAN_LOG=' + str(out / PLAN_LOG),
            '-logfile', out / 'protocol.transcript', '-do', 'run -all; quit -f']


def check_protocol(out, data):
    console = base.common.read(out / CONSOLE)
    transcript = base.common.read(out / 'protocol.transcript')
    assert console.strip() == transcript.strip(), 'protocol console/transcript differ'
    assert '$finish' in console and 'Errors: 0, Warnings: 0' in console
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', console)
    assert re.findall(r'IPSpecCheck: (\d+)', console) == ['04030130'] * 2, 'device notices'
    printed = re.findall(r'RESULT: PASS inst_lookup_protocol_completion (.*)', console)
    assert len(printed) == 1, 'missing or duplicated protocol PASS line'
    result = review_protocol(out / EDGE_LOG, out / PLAN_LOG)
    plan = data['stimulus_plan']
    for key in ('scenarios', 'tokens', 'accepts', 'responses', 'cancels'):
        assert result[key] == plan[key], (key, result.get(key), plan)
    assert result['accepts'] == result['responses'] + result['cancels']
    assert result['mismatches'] == 0
    assert result['ar_r_same'] >= plan['ar_r_same_min'], (result['ar_r_same'], plan)
    assert result['dual_present'] >= plan['dual_present_min'], (result['dual_present'], plan)
    fields = dict(kv.split('=') for kv in printed[0].split())
    for key in ('scenarios', 'tokens', 'accepts', 'responses', 'cancels', 'resets',
                'ar', 'r', 'aw', 'w', 'ar_r_same', 'dual_present', 'mismatches'):
        assert key in result, 'reference does not report ' + key
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
        print('RESULT: PASS Task032 protocol completion inputs; bridge %s; jobs=%s; plan=%s; '
              'contract ar_r_same_min=%s dual_present_min=%s; tb=%s; key/A reused; '
              'HDL NOT_RUN; ISA=0'
              % (data['bridge_repair']['sha_after'][:8], json.dumps(data['jobs']),
                 json.dumps(data['stimulus_plan']),
                 data['coverage_contract']['ar_r_same_min'],
                 data['coverage_contract']['dual_present_min'],
                 sha(ROOT / PROTOCOL_TB)[:16]))
        return
    before = base.common.git_snapshot()
    out.mkdir(exist_ok=False)
    result = dict(status='RUNNING', manifest_sha256=sha(MANIFEST), completed={}, HDL_started=False,
                  b_only=True, key_and_A_reused=True,
                  retry_of='ds_data_bus_inst_lookup_protocol_resume_e_20261014_a',
                  partial_review_sha256=data['partial_review']['sha256'],
                  coverage_contract=data['coverage_contract'],
                  stimulus_plan=data['stimulus_plan'],
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
        result['completed'][NEW_MODULE] = check_protocol(out, data)
        base.common.save(out / 'result.json', result)
        assert require_inputs() == data
        after = base.common.git_snapshot()
        base.common.save(out / 'git_after.json', after)
        assert before == after, 'Worktree changed during execution'
        result.update(status='TASK032_PROTOCOL_COMPLETION_REUSED_KEY_A_PASS',
                      inputs_unchanged=True, git_unchanged=True, protocol_passed=True)
        print('RESULT: PASS Task032 protocol completion; PDS timing/board NOT_RUN')
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
        try:
            result['inputs_after'] = require_inputs() == data
        except Exception as exc:  # noqa: BLE001
            result['inputs_after_error'] = f'{type(exc).__name__}: {exc}'
        base.common.save(out / 'result.json', result)


if __name__ == '__main__':
    main()
