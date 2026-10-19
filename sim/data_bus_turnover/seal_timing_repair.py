"""Seal the Task032 timing-repair manifest (instruction-response selector fix).

Inputs_timing_repair.json is derived from inputs_ip_count_key_resume.json:
  * the repaired bridge identity is the only changed project entry; the two new
    implementation files of this round are added;
  * compile sources, module list, include closure, timeouts, vendor and tool
    identities stay byte-identical;
  * the protected set is the union of the previous 626 entries, the previous
    key-only manifest, every file of the reviewed key-only run directory except the
    compiled work library, the key-only closing report and this repair preparation
    directory;
  * the reused control receipt and the reviewed pre-repair key receipt are bound by
    SHA together with the counters the repaired key must reproduce exactly.

--check re-verifies the seal (AST, input identity, receipt bindings, checker proof).
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_ip_count_key_resume.json'
MANIFEST = HERE / 'inputs_timing_repair.json'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
CHECKER = 'sim/data_bus_turnover/check_evidence.py'
CONTROL_REVIEW = 'sim/data_bus_turnover/build/ip_count_key_preparation_20261014_a/control_review.json'
KEY_RUN = 'sim/data_bus_turnover/build/ds_data_bus_response_turnover_ip_count_key_20261014_a'
KEY_REVIEW = KEY_RUN + '/codex_review.json'
PREPARATION = 'sim/data_bus_turnover/build/timing_repair_preparation_20261014_a'
REPORT = 'DeepSeek/任务032收尾_结果_ds_data_bus_response_turnover_ip_count_key_20261014_a.md'
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/run_timing_repair.py',
                      'sim/data_bus_turnover/seal_timing_repair.py']
MUST_MATCH = ['sim/data_bus_turnover/check_evidence.py',
              'sim/data_bus_turnover/tb_data_bus_turnover.sv',
              'sim/data_bus_turnover/unit_cases.svh',
              'sim/data_bus_turnover/program.dat',
              'sim/data_bus_turnover/reference.json',
              'sim/data_bus_turnover/reference.trace',
              'sim/data_bus_turnover/prepare_program.py',
              'myriscv/mycpu_sync.v',
              'myriscv/data_bus_interconnect.v']
TAG = 'ds_data_bus_turnover_timing_repair_20261014_a'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(directory):
    return sorted(str(p.relative_to(ROOT)).replace('\\', '/')
                  for p in (ROOT / directory).rglob('*') if p.is_file())


def build():
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8'))
    receipt = json.loads((ROOT / CONTROL_REVIEW).read_text(encoding='utf-8'))
    key_receipt = json.loads((ROOT / KEY_REVIEW).read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_response_turnover_ip_count_key_20261014_a'
    assert receipt['status'] == 'TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING'
    assert key_receipt['status'] == 'DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS'
    assert key_receipt['manifest_sha256'] == sha(PREVIOUS)
    assert key_receipt['HDL_rerun'] is False and key_receipt['CPU_changed'] is False
    assert key_receipt['checked_key']['fields']['cycles'] == 617
    assert key_receipt['checked_key']['fields']['mem_wait'] == 415
    assert key_receipt['checked_key']['fields']['turns'] == 18

    project = dict(previous['project_sha256'])
    changed = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed == {BRIDGE}, sorted(changed)
    project[BRIDGE] = sha(ROOT / BRIDGE)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    protected = dict(previous['protected_evidence_sha256'])
    extra = {'sim/data_bus_turnover/inputs_ip_count_key_resume.json':
             sha(ROOT / 'sim/data_bus_turnover/inputs_ip_count_key_resume.json')}
    extra[REPORT] = sha(ROOT / REPORT)
    for name in tree(KEY_RUN):
        if '/work/' in name or name.endswith('/work'):
            continue
        extra[name] = sha(ROOT / name)
    for name in tree(PREPARATION):
        extra[name] = sha(ROOT / name)
    for name, digest in extra.items():
        if name in protected:
            assert protected[name] == digest, 'Duplicate protected path with different hash: ' + name
        else:
            protected[name] = digest
    missing = [n for n, h in protected.items() if not (ROOT / n).is_file() or sha(ROOT / n) != h]
    assert not missing, missing[:5]

    data = dict(
        status='TASK032_INSTRUCTION_RESPONSE_SELECTOR_TIMING_REPAIR_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        key_only=True,
        control_reused=True,
        project_sha256=project,
        vendor_sha256=previous['vendor_sha256'],
        tool_sha256=previous['tool_sha256'],
        compile_sources=previous['compile_sources'],
        expected_modules=previous['expected_modules'],
        include_dependencies=previous['include_dependencies'],
        timeouts=previous['timeouts'],
        protected_evidence_sha256=protected,
        previous_manifest='sim/data_bus_turnover/inputs_ip_count_key_resume.json',
        previous_manifest_sha256=sha(PREVIOUS),
        new_implementation_files=NEW_IMPLEMENTATION,
        must_match_previous=MUST_MATCH,
        bridge_repair=dict(file=BRIDGE,
                           sha_before=previous['project_sha256'][BRIDGE],
                           sha_after=sha(ROOT / BRIDGE),
                           change=('x32 instruction request presets response_from_inst_drm=1 instead of '
                                   'depending on inst_line_hit; miss clears it in RADDR; hit path, ready, '
                                   'state and all data-source logic unchanged')),
        reused_control_review=CONTROL_REVIEW,
        reused_control_review_sha256=sha(ROOT / CONTROL_REVIEW),
        reused_control=dict(source_run=receipt['source_run'],
                            source_manifest_sha256=receipt['source_manifest_sha256'],
                            checked=receipt['checked']),
        reused_key_review=KEY_REVIEW,
        reused_key_review_sha256=sha(ROOT / KEY_REVIEW),
        reused_key=dict(manifest_sha256=key_receipt['manifest_sha256'],
                        checked_key=key_receipt['checked_key'],
                        status=key_receipt['status'],
                        note='reviewed pre-repair key; used only as the exact-reproduction reference'),
        expected_key=key_receipt['checked_key'],
        checker_edit=previous['checker_edit'],
        changed_design_files=['myriscv/data_bus_interconnect.v', BRIDGE],
        changed_design_files_this_round=[BRIDGE],
        CPU_changed=False,
        ISA_samples=[],
        reference_events=previous['reference_events'],
        reference_requests=previous['reference_requests'],
        unit_cases=previous['unit_cases'],
        unit_control_cycles=previous['unit_control_cycles'],
        unit_key_cycles=previous['unit_key_cycles'],
        unit_key_turns=previous['unit_key_turns'],
        baseline=previous['baseline'],
        baseline_P_seconds=previous['baseline_P_seconds'],
        baseline_V_seconds=previous['baseline_V_seconds'],
        roles=previous['roles'],
        old_control_git_after='ABSENT_NOT_BACKFILLED',
        board='NOT_RUN', PDS='NOT_RUN', serial='NOT_OPENED', timing='NOT_RUN',
        scope=('Key-only rerun on the instruction-response selector timing repair; the reviewed '
               'GRS-resume control (64 unit / 619 SoC / 443 memory wait) and the reviewed '
               'pre-repair key (33 unit / 617 SoC / 415 memory wait / 18 turnarounds) are reused '
               'as comparison and exact-reproduction references. No new control run.'),
        limitations=['AR-accept-same-cycle R-return phase is covered by Codex state review, not by '
                     'the frozen DDR model.',
                     'Simulation is not PDS timing, real DDR or board performance.'],
    )
    data['project_count'] = len(project)
    data['protected_count'] = len(protected)
    return data


def check():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name in NEW_IMPLEMENTATION:
        ast.parse((ROOT / name).read_text(encoding='utf-8'), filename=name)
    sys.path.insert(0, str(HERE))
    import run_timing_repair as runner
    assert runner.require_inputs() == data
    print('SEAL CHECK PASS project=%d protected=%d bridge=%s control_review=%s key_review=%s' %
          (len(data['project_sha256']), len(data['protected_evidence_sha256']),
           data['bridge_repair']['sha_after'][:16], data['reused_control_review_sha256'][:16],
           data['reused_key_review_sha256'][:16]))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    if args.check:
        check()
        return
    assert not MANIFEST.exists(), 'do not overwrite the sealed manifest'
    data = build()
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('SEALED', len(data['project_sha256']), 'project,',
          len(data['protected_evidence_sha256']), 'protected, SHA', sha(MANIFEST))


if __name__ == '__main__':
    main()
