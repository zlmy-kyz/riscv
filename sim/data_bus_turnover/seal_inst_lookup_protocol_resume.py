"""Seal the Task032 B-only protocol resume manifest.

inputs_inst_lookup_protocol_resume.json is derived from inputs_inst_lookup_registered_repair.json
(the design that produced the stopped protocol group) with no design change:
  * every previous project input is kept byte-identical, including the defective old
    protocol testbench and checker, which stay as frozen historical identities;
  * the four implementation files of this round are added;
  * only the compiled top level changes: the old protocol testbench leaves the compile
    list and the B-only resume top level takes its place, keeping 39 compiled modules;
  * the protected set keeps the previous 1621 logical identities, adds the stopped run
    directory, the failed-run manifest/report and this round's preparation receipt, and
    relocates the single live hand-off document identity to the byte-identical saved
    copy (recorded in historical_identity_relocations);
  * the partial review receipt is bound by SHA together with its checked_key, checked_A
    and the pre-declared stimulus plan of the new group.

--check re-verifies the seal (AST, input identity, receipt bindings, plan identity).
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_inst_lookup_registered_repair.json'
MANIFEST = HERE / 'inputs_inst_lookup_protocol_resume.json'
OLD_TOP = 'sim/data_bus_turnover/tb_inst_lookup_registered.sv'
NEW_TOP = 'sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv'
FAILURE_REVIEW = ('sim/data_bus_turnover/build/'
                  'registered_protocol_repair_preparation_20261014_a/failure_review.json')
PREP_DIR = 'sim/data_bus_turnover/build/registered_protocol_repair_preparation_20261014_a'
HANDOFF = 'doc/CODEX_HANDOFF.md'
HANDOFF_SAVED = PREP_DIR + '/handoff_before_review.md'
HANDOFF_SHA = '55be65f67944f2dfcf143ed8d19606a6244dfa68de99f46efd1ec5e2a880949c'
STOPPED_RUN = 'sim/data_bus_turnover/build/ds_data_bus_inst_lookup_registered_repair_20261014_a'
STOPPED_REPORT = ('DeepSeek/任务032逐行命中寄存修复_结果_'
                  'ds_data_bus_inst_lookup_registered_repair_20261014_a.md')
PLAN_DOC = 'DeepSeek/任务032寄存查询协议B续测_边沿采样与事务守恒修订.md'
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv',
                      'sim/data_bus_turnover/check_inst_lookup_protocol_resume.py',
                      'sim/data_bus_turnover/run_inst_lookup_protocol_resume.py',
                      'sim/data_bus_turnover/seal_inst_lookup_protocol_resume.py']
MUST_MATCH = ['sim/data_bus_turnover/check_evidence.py',
              'sim/data_bus_turnover/tb_data_bus_turnover.sv',
              'sim/data_bus_turnover/tb_inst_tag_lookup.sv',
              'sim/data_bus_turnover/check_tag_lookup.py',
              'sim/data_bus_turnover/tb_inst_lookup_registered.sv',
              'sim/data_bus_turnover/check_inst_lookup_registered.py',
              'sim/data_bus_turnover/unit_cases.svh',
              'sim/data_bus_turnover/program.dat',
              'sim/data_bus_turnover/reference.json',
              'sim/data_bus_turnover/reference.trace',
              'sim/data_bus_turnover/prepare_program.py',
              'myriscv/mycpu_sync.v',
              'myriscv/data_bus_interconnect.v',
              'myriscv/dual_sram_to_pango_ddr_bridge.v']
TAG = 'ds_data_bus_inst_lookup_protocol_resume_20261014_a'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(directory):
    return sorted(str(p.relative_to(ROOT)).replace('\\', '/')
                  for p in (ROOT / directory).rglob('*') if p.is_file())


def plan_summary():
    sys.path.insert(0, str(HERE))
    import check_inst_lookup_protocol_resume as checker
    return checker.plan_summary()


def build():
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8'))
    receipt = json.loads((ROOT / FAILURE_REVIEW).read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_inst_lookup_registered_repair_20261014_a'
    assert receipt['status'] == 'TASK032_REGISTERED_LOOKUP_KEY_AND_A_RAW_PASS_B_FAILED'
    assert receipt['source_manifest_sha256'] == sha(PREVIOUS)
    assert receipt['bridge_sha256'] == previous['project_sha256'][
        'myriscv/dual_sram_to_pango_ddr_bridge.v']
    assert receipt['handoff_historical_identity']['sha256'] == HANDOFF_SHA

    project = dict(previous['project_sha256'])
    changed = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed == set(), 'no previous project input may change: %s' % sorted(changed)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    sources = list(previous['compile_sources'])
    assert sources.count(OLD_TOP) == 1
    sources[sources.index(OLD_TOP)] = NEW_TOP
    modules = list(previous['expected_modules'])
    assert modules.count('tb_inst_lookup_registered') == 1
    modules[modules.index('tb_inst_lookup_registered')] = 'tb_inst_lookup_protocol_resume'
    assert len(modules) == 39
    sys.path.insert(0, str(ROOT / 'sim/write_buffer_turnover'))
    from check_include_dependencies import check_includes
    includes = check_includes(ROOT, sources)
    assert includes == previous['include_dependencies'], 'include closure changed'

    protected = dict(previous['protected_evidence_sha256'])
    assert protected.get(HANDOFF) == HANDOFF_SHA, 'unexpected historical hand-off identity'
    del protected[HANDOFF]
    relocations = {HANDOFF: dict(saved_path=HANDOFF_SAVED, sha256=HANDOFF_SHA,
                                 reason=('the live hand-off document must stay updatable across '
                                         'this hand-over; Codex saved it byte-identically before '
                                         'updating, so the historical identity binds to the copy'))}
    extra = {'sim/data_bus_turnover/inputs_inst_lookup_registered_repair.json': sha(PREVIOUS),
             STOPPED_REPORT: sha(ROOT / STOPPED_REPORT),
             FAILURE_REVIEW: sha(ROOT / FAILURE_REVIEW),
             PLAN_DOC: sha(ROOT / PLAN_DOC),
             HANDOFF_SAVED: HANDOFF_SHA}
    for name in tree(STOPPED_RUN):
        if '/work/' in name or name.endswith('/work'):
            continue
        extra[name] = sha(ROOT / name)
    for name in tree(PREP_DIR):
        extra[name] = sha(ROOT / name)
    for name, digest in extra.items():
        if name in protected:
            assert protected[name] == digest, 'Duplicate protected path with different hash: ' + name
        else:
            protected[name] = digest
    missing = [n for n, h in protected.items() if not (ROOT / n).is_file() or sha(ROOT / n) != h]
    assert not missing, missing[:5]
    for name, digest in receipt.get('prior_files_sha256', {}).items():
        assert protected.get(name) == digest, 'receipt prior file not protected: ' + name

    plan = plan_summary()
    data = dict(
        status='TASK032_REGISTERED_LOOKUP_PROTOCOL_RESUME_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        b_only=True,
        key_and_A_reused=True,
        jobs=['vlib', 'compile', 'inst_lookup_protocol_resume'],
        project_sha256=project,
        vendor_sha256=previous['vendor_sha256'],
        tool_sha256=previous['tool_sha256'],
        compile_sources=sources,
        expected_modules=modules,
        include_dependencies=includes,
        timeouts=previous['timeouts'],
        protected_evidence_sha256=protected,
        historical_identity_relocations=relocations,
        previous_manifest='sim/data_bus_turnover/inputs_inst_lookup_registered_repair.json',
        previous_manifest_sha256=sha(PREVIOUS),
        changed_project_files=[],
        new_implementation_files=NEW_IMPLEMENTATION,
        must_match_previous=MUST_MATCH,
        bridge_repair=previous['bridge_repair'],
        protocol_tb=NEW_TOP,
        replaced_compile_top=OLD_TOP,
        stimulus_plan=plan,
        partial_review=dict(path=FAILURE_REVIEW, sha256=sha(ROOT / FAILURE_REVIEW),
                            status=receipt['status'],
                            checked_key=receipt['checked_key'],
                            checked_A=receipt['checked_A'],
                            source_run=receipt['source_run'],
                            note=('key and group A raw evidence passed; the protocol group failed. '
                                  'Reused as evidence, never as the overall functional gate.')),
        reused_control_review=previous['reused_control_review'],
        reused_control_review_sha256=previous['reused_control_review_sha256'],
        reused_control=previous['reused_control'],
        reused_key_review=previous['reused_key_review'],
        reused_key_review_sha256=previous['reused_key_review_sha256'],
        reused_key=previous['reused_key'],
        expected_key=previous['expected_key'],
        reused_C_gate=previous['reused_C_gate'],
        static_preparation=previous['static_preparation'],
        previous_timing_review=previous['previous_timing_review'],
        previous_timing_review_sha256=previous['previous_timing_review_sha256'],
        checker_edit=previous['checker_edit'],
        changed_design_files=previous['changed_design_files'],
        changed_design_files_this_round=[],
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
        user_reported_pds_timing=previous['user_reported_pds_timing'],
        scope=('B-only protocol resume: the original SoC key and the group A acceptance-edge '
               'sampling evidence are reused from the reviewed partial receipt; this run only '
               'measures the rewritten race-free protocol group.'),
        limitations=['The protocol group does not emulate a physical DDR PHY, x16 mode or a second CPU.',
                     'Group A tag hits and the original key are reused, not re-measured here.',
                     'Simulation is not PDS timing, real DDR or board performance.'],
    )
    data['project_count'] = len(project)
    data['protected_count'] = len(protected)
    return data


def check():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name in NEW_IMPLEMENTATION:
        if name.endswith('.py'):
            ast.parse((ROOT / name).read_text(encoding='utf-8'), filename=name)
    sys.path.insert(0, str(HERE))
    import run_inst_lookup_protocol_resume as runner
    assert runner.require_inputs() == data
    print('SEAL CHECK PASS project=%d protected=%d modules=%d jobs=%s plan=%s' %
          (len(data['project_sha256']), len(data['protected_evidence_sha256']),
           len(data['expected_modules']), data['jobs'], data['stimulus_plan']))


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
          len(data['protected_evidence_sha256']), 'protected,',
          len(data['expected_modules']), 'modules, SHA', sha(MANIFEST))


if __name__ == '__main__':
    main()
