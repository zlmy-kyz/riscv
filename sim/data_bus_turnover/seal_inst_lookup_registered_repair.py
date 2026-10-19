"""Seal the Task032 registered-instruction-lookup manifest.

inputs_inst_lookup_registered_repair.json is derived from inputs_tag_lookup_repair_c.json
(the reviewed C design):
  * the only changed project entry is myriscv/dual_sram_to_pango_ddr_bridge.v
    (1170cfd2... -> f14b16cb...);
  * the four implementation files of this round are added;
  * the previous combined look-up testbench leaves the compile list and is replaced by
    the new registered-look-up top level, keeping 39 compiled modules; the old file is
    kept as a protected input;
  * every other source, include dependency, timeout, vendor and tool identity stays
    byte-identical;
  * the protected set adds the reviewed C manifest, its run directory, its report and
    gate, the tag-tree and registered-lookup preparation directories, this plan, the
    031 success baseline identity and the hand-off document that records the frozen
    image identity.

--check re-verifies the seal (AST, input identity, receipt bindings, checker proof).
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_tag_lookup_repair_c.json'
MANIFEST = HERE / 'inputs_inst_lookup_registered_repair.json'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'
OLD_LOOKUP_TB = 'sim/data_bus_turnover/tb_inst_tag_lookup.sv'
NEW_LOOKUP_TB = 'sim/data_bus_turnover/tb_inst_lookup_registered.sv'
CONTROL_REVIEW = 'sim/data_bus_turnover/build/ip_count_key_preparation_20261014_a/control_review.json'
KEY_REVIEW = ('sim/data_bus_turnover/build/'
              'ds_data_bus_response_turnover_ip_count_key_20261014_a/codex_review.json')
C_RUN = 'sim/data_bus_turnover/build/ds_data_bus_tag_lookup_repair_c_20261014_a'
C_GATE = C_RUN + '/codex_review.json'
C_REPORT = ('DeepSeek/任务032二次时序修复_结果_'
            'ds_data_bus_tag_lookup_repair_c_20261014_a.md')
TAG_TREE_PREP = 'sim/data_bus_turnover/build/tag_lookup_repair_preparation_20261014_a'
PREV_PREP = TAG_TREE_PREP + '/previous_key_review.json'
REG_PREP = 'sim/data_bus_turnover/build/inst_lookup_register_repair_preparation_20261014_a'
REG_STATIC = REG_PREP + '/static_review.json'
PLAN = 'DeepSeek/任务032逐行命中寄存修复_时序通过后关键仿真.md'
BASELINE = 'sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_timing_300_01'
HANDOFF = 'doc/CODEX_HANDOFF.md'
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/tb_inst_lookup_registered.sv',
                      'sim/data_bus_turnover/check_inst_lookup_registered.py',
                      'sim/data_bus_turnover/run_inst_lookup_registered_repair.py',
                      'sim/data_bus_turnover/seal_inst_lookup_registered_repair.py']
MUST_MATCH = ['sim/data_bus_turnover/check_evidence.py',
              'sim/data_bus_turnover/tb_data_bus_turnover.sv',
              'sim/data_bus_turnover/tb_inst_tag_lookup.sv',
              'sim/data_bus_turnover/check_tag_lookup.py',
              'sim/data_bus_turnover/unit_cases.svh',
              'sim/data_bus_turnover/program.dat',
              'sim/data_bus_turnover/reference.json',
              'sim/data_bus_turnover/reference.trace',
              'sim/data_bus_turnover/prepare_program.py',
              'myriscv/mycpu_sync.v',
              'myriscv/data_bus_interconnect.v']
TAG = 'ds_data_bus_inst_lookup_registered_repair_20261014_a'
PRIOR_REVIEW_SHA = '4de7282d07bd407560b9f1496cc4d78fbdd8dbe66cdfd7b4a5a0ed0336e4e319'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(directory):
    return sorted(str(p.relative_to(ROOT)).replace('\\', '/')
                  for p in (ROOT / directory).rglob('*') if p.is_file())


def build():
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8'))
    control = json.loads((ROOT / CONTROL_REVIEW).read_text(encoding='utf-8'))
    key_receipt = json.loads((ROOT / KEY_REVIEW).read_text(encoding='utf-8'))
    c_gate = json.loads((ROOT / C_GATE).read_text(encoding='utf-8'))
    prior = json.loads((ROOT / PREV_PREP).read_text(encoding='utf-8'))
    static = json.loads((ROOT / REG_STATIC).read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_tag_lookup_repair_c_20261014_a'
    assert control['status'] == 'TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING'
    assert key_receipt['status'] == 'DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS'
    assert c_gate['manifest_sha256'] == sha(PREVIOUS), 'C gate must belong to the C manifest'
    assert sha(PREV_PREP) == PRIOR_REVIEW_SHA
    assert prior['status'] == 'TASK032_FIRST_SELECTOR_REPAIR_RAW_FUNCTIONAL_REVIEW_PASS_TIMING_FAIL'
    assert static['new_bridge_sha256'] == sha(ROOT / BRIDGE), static['new_bridge_sha256']

    project = dict(previous['project_sha256'])
    changed = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed == {BRIDGE}, sorted(changed)
    project[BRIDGE] = sha(ROOT / BRIDGE)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    sources = list(previous['compile_sources'])
    assert sources.count(OLD_LOOKUP_TB) == 1, 'previous compile list must contain the old look-up top'
    sources[sources.index(OLD_LOOKUP_TB)] = NEW_LOOKUP_TB
    modules = list(previous['expected_modules'])
    assert modules.count('tb_inst_tag_lookup') == 1
    modules[modules.index('tb_inst_tag_lookup')] = 'tb_inst_lookup_registered'
    assert len(modules) == 39, 'expected 39 compiled modules'
    sys.path.insert(0, str(ROOT / 'sim/write_buffer_turnover'))
    from check_include_dependencies import check_includes
    includes = check_includes(ROOT, sources)
    assert includes == previous['include_dependencies'], 'include closure changed'

    protected = dict(previous['protected_evidence_sha256'])
    extra = {'sim/data_bus_turnover/inputs_tag_lookup_repair_c.json': sha(PREVIOUS),
             C_REPORT: sha(ROOT / C_REPORT),
             C_GATE: sha(ROOT / C_GATE),
             PLAN: sha(ROOT / PLAN),
             HANDOFF: sha(ROOT / HANDOFF),
             REG_STATIC: sha(ROOT / REG_STATIC)}
    for name in tree(C_RUN):
        if '/work/' in name or name.endswith('/work'):
            continue
        extra[name] = sha(ROOT / name)
    for directory in (REG_PREP, BASELINE):
        for name in tree(directory):
            extra[name] = sha(ROOT / name)
    for name, digest in extra.items():
        if name in protected:
            assert protected[name] == digest, 'Duplicate protected path with different hash: ' + name
        else:
            protected[name] = digest
    missing = [n for n, h in protected.items() if not (ROOT / n).is_file() or sha(ROOT / n) != h]
    assert not missing, missing[:5]

    data = dict(
        status='TASK032_REGISTERED_INST_LOOKUP_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        control_reused=True,
        key_replayed=True,
        extra_job='inst_lookup_registered',
        project_sha256=project,
        vendor_sha256=previous['vendor_sha256'],
        tool_sha256=previous['tool_sha256'],
        compile_sources=sources,
        expected_modules=modules,
        include_dependencies=includes,
        timeouts=previous['timeouts'],
        protected_evidence_sha256=protected,
        previous_manifest='sim/data_bus_turnover/inputs_tag_lookup_repair_c.json',
        previous_manifest_sha256=sha(PREVIOUS),
        changed_project_files=[BRIDGE],
        new_implementation_files=NEW_IMPLEMENTATION,
        must_match_previous=MUST_MATCH,
        bridge_repair=dict(file=BRIDGE,
                           sha_before=previous['project_sha256'][BRIDGE],
                           sha_after=sha(ROOT / BRIDGE),
                           change=('per-row x32 I look-up results are registered together with the '
                                   'synchronous DRM read at the acceptance edge; STATE_INST_LOOKUP '
                                   'serves the registered hit response and issues AR on a registered '
                                   'miss, both expected without an extra cycle')),
        lookup_tb=NEW_LOOKUP_TB,
        replaced_compile_top=OLD_LOOKUP_TB,
        reused_control_review=CONTROL_REVIEW,
        reused_control_review_sha256=sha(ROOT / CONTROL_REVIEW),
        reused_control=dict(source_run=control['source_run'],
                            source_manifest_sha256=control['source_manifest_sha256'],
                            checked=control['checked']),
        reused_key_review=KEY_REVIEW,
        reused_key_review_sha256=sha(ROOT / KEY_REVIEW),
        reused_key=dict(manifest_sha256=key_receipt['manifest_sha256'],
                        checked_key=key_receipt['checked_key'],
                        status=key_receipt['status'],
                        note='reviewed key before the registered look-up repair'),
        expected_key=key_receipt['checked_key'],
        reused_C_gate=dict(path=C_GATE, sha256=sha(ROOT / C_GATE),
                           manifest_sha256=c_gate['manifest_sha256'],
                           status=c_gate['status'],
                           checked_key=c_gate['checked_key'],
                           note=('historical functional gate for bridge 1170cfd2 only; it must not be '
                                 'reused as the gate for bridge ' + sha(ROOT / BRIDGE)[:8])),
        previous_timing_review=PREV_PREP,
        previous_timing_review_sha256=PRIOR_REVIEW_SHA,
        static_preparation=dict(path=REG_STATIC, sha256=sha(ROOT / REG_STATIC),
                                status=static['status'],
                                timing_before=static.get('timing_before'),
                                cycle_expectation=static.get('cycle_expectation_NOT_MEASURED')),
        frozen_baseline=dict(directory=BASELINE, handoff=HANDOFF,
                             note=('031 real-board success baseline and the frozen Zmmul P300/V300 '
                                   'image identity recorded in the hand-off document')),
        checker_edit=previous['checker_edit'],
        changed_design_files=previous['changed_design_files'] + [BRIDGE],
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
        user_reported_pds_timing='PASS_REPORTED_BY_USER_NOT_INDEPENDENTLY_REVIEWED',
        scope=('Original SoC key replay on the registered x32 I look-up repair plus one new '
               'bridge-level directed group: acceptance-edge tag sampling (group A) and real '
               'handshake/DRM/fill protocol scenarios (group B).'),
        limitations=['Group B does not emulate a physical DDR PHY, x16 mode or a second CPU.',
                     'The isolated group A tag hits are not data-correctness evidence.',
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
    import run_inst_lookup_registered_repair as runner
    assert runner.require_inputs() == data
    print('SEAL CHECK PASS project=%d protected=%d modules=%d changed=%s bridge=%s' %
          (len(data['project_sha256']), len(data['protected_evidence_sha256']),
           len(data['expected_modules']), data['changed_project_files'],
           data['bridge_repair']['sha_after'][:16]))


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
