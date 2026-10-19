"""Seal the Task032 key-only manifest from the GRS-resume manifest plus one edit.

Produces sim/data_bus_turnover/inputs_ip_count_key_resume.json:
  * the previous 164-entry project input set with only check_evidence.py updated,
    plus the new implementation files of this closing run;
  * the previous compile sources / module list / include closure / timeouts and
    3 vendor + 3 tool identities unchanged;
  * the union of the previous 437 protected evidence files, the 188 files bound by
    the reused control receipt, and the control receipt itself;
  * the control receipt SHA plus its source run, source manifest and checked content.

Run with --check to re-verify the seal (AST + input identity + the byte-level
one-line checker proof) without starting any native command.
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_grs_resume.json'
MANIFEST = HERE / 'inputs_ip_count_key_resume.json'
CHECKER = 'sim/data_bus_turnover/check_evidence.py'
CONTROL_REVIEW = 'sim/data_bus_turnover/build/ip_count_key_preparation_20261014_a/control_review.json'
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/run_ip_count_key_resume.py',
                      'sim/data_bus_turnover/seal_ip_count_key_resume.py']
MUST_MATCH = ['sim/data_bus_turnover/tb_data_bus_turnover.sv',
              'sim/data_bus_turnover/unit_cases.svh',
              'sim/data_bus_turnover/program.dat',
              'sim/data_bus_turnover/reference.json',
              'sim/data_bus_turnover/reference.trace',
              'sim/data_bus_turnover/prepare_program.py',
              'myriscv/data_bus_interconnect.v',
              'myriscv/mycpu_sync.v',
              'myriscv/dual_sram_to_pango_ddr_bridge.v']
TAG = 'ds_data_bus_response_turnover_ip_count_key_20261014_a'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8'))
    receipt = json.loads((ROOT / CONTROL_REVIEW).read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_response_turnover_grs_resume_20261014_a'
    assert receipt['status'] == 'TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING'
    assert receipt['key'] == 'NOT_RUN' and receipt['HDL_rerun'] is False
    assert receipt['old_git_after'] == 'ABSENT_NOT_BACKFILLED'

    project = dict(previous['project_sha256'])
    changed_before = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed_before == {CHECKER}, sorted(changed_before)
    project[CHECKER] = sha(ROOT / CHECKER)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    protected = dict(previous['protected_evidence_sha256'])
    overlap = set(protected) & set(receipt['prior_files_sha256'])
    assert not overlap, sorted(overlap)
    protected.update(receipt['prior_files_sha256'])
    protected[CONTROL_REVIEW] = sha(ROOT / CONTROL_REVIEW)
    protected['sim/data_bus_turnover/inputs_grs_resume.json'] = sha(
        ROOT / 'sim/data_bus_turnover/inputs_grs_resume.json')
    missing = [n for n, h in protected.items() if not (ROOT / n).is_file() or sha(ROOT / n) != h]
    assert not missing, missing[:5]

    data = dict(
        status='TASK032_IP_COUNT_KEY_RESUME_PREPARED_HDL_NOT_RUN',
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
        previous_manifest='sim/data_bus_turnover/inputs_grs_resume.json',
        previous_manifest_sha256=sha(PREVIOUS),
        old_frozen_checker=('sim/data_bus_turnover/build/'
                            'ds_data_bus_response_turnover_grs_resume_20261014_a/inputs/project/'
                            'sim/data_bus_turnover/check_evidence.py'),
        new_implementation_files=NEW_IMPLEMENTATION,
        must_match_previous=MUST_MATCH,
        reused_control_review=CONTROL_REVIEW,
        reused_control_review_sha256=sha(ROOT / CONTROL_REVIEW),
        reused_control=dict(source_run=receipt['source_run'],
                            source_manifest_sha256=receipt['source_manifest_sha256'],
                            checked=receipt['checked']),
        old_control_git_after='ABSENT_NOT_BACKFILLED',
        checker_edit=("exactly one line: IPSpecCheck 04030130 count ['04030130'] * 4 -> * 2 "
                      "(one SoC, one icache/dcache pair); all other predicates unchanged"),
        changed_design_files=previous['changed_design_files'],
        CPU_changed=False,
        ISA_samples=[],
        reference_events=previous['reference_events'],
        reference_requests=previous['reference_requests'],
        unit_cases=previous['unit_cases'],
        unit_control_cycles=previous['unit_control_cycles'],
        unit_key_cycles=previous['unit_key_cycles'],
        unit_key_turns=51,
        unit_control_cycles_saving=31,
        baseline=previous['baseline'],
        baseline_P_seconds=previous['baseline_P_seconds'],
        baseline_V_seconds=previous['baseline_V_seconds'],
        roles=previous['roles'],
        board='NOT_RUN', PDS='NOT_RUN', serial='NOT_OPENED',
        scope=('Key-only rerun on the corrected device-spec notice count; the reviewed '
               'GRS-resume control run is reused (64 unit cycles / 619 SoC cycles / '
               '443 memory-wait cycles) and must not be re-executed.'),
    )
    data['protected_count'] = len(protected)
    data['project_count'] = len(project)
    return data


def check():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name in NEW_IMPLEMENTATION:
        ast.parse((ROOT / name).read_text(encoding='utf-8'), filename=name)
    sys.path.insert(0, str(HERE))
    import run_ip_count_key_resume as runner
    assert runner.require_inputs() == data
    print('SEAL CHECK PASS project=%d protected=%d control_review=%s' %
          (len(data['project_sha256']), len(data['protected_evidence_sha256']),
           data['reused_control_review_sha256'][:16]))


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
