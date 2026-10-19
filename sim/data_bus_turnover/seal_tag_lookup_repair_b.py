"""Seal the Task032 parallel-I-tag-lookup re-run manifest (attempt B).

inputs_tag_lookup_repair_b.json is derived from inputs_tag_lookup_repair.json, the
manifest of the stopped first attempt, which stays untouched together with its run
directory and report:
  * the only changed project entry is sim/data_bus_turnover/tb_inst_tag_lookup.sv
    (the trace scenario counter is now initialised);
  * the re-run runner and this sealer are added; the first attempt's runner, sealer,
    checker and all frozen stimulus/reference/compile/module/include/timeout
    identities stay byte-identical;
  * the protected set adds the stopped manifest, its report and every file of its run
    directory except the compiled work library;
  * the reused control receipt, the reviewed key receipt and the first-repair review
    stay bound by SHA.

--check re-verifies the seal (AST, input identity, receipt bindings, checker proof).
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_tag_lookup_repair.json'
MANIFEST = HERE / 'inputs_tag_lookup_repair_b.json'
LOOKUP_TB = 'sim/data_bus_turnover/tb_inst_tag_lookup.sv'
CONTROL_REVIEW = 'sim/data_bus_turnover/build/ip_count_key_preparation_20261014_a/control_review.json'
KEY_REVIEW = ('sim/data_bus_turnover/build/'
              'ds_data_bus_response_turnover_ip_count_key_20261014_a/codex_review.json')
PRIOR_STOP_RUN = 'sim/data_bus_turnover/build/ds_data_bus_tag_lookup_repair_20261014_a'
PRIOR_STOP_REPORT = ('DeepSeek/任务032二次时序修复_结果_'
                     'ds_data_bus_tag_lookup_repair_20261014_a.md')
PREPARATION = 'sim/data_bus_turnover/build/tag_lookup_repair_preparation_20261014_a'
PRIOR_REVIEW = PREPARATION + '/previous_key_review.json'
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/run_tag_lookup_repair_b.py',
                      'sim/data_bus_turnover/seal_tag_lookup_repair_b.py']
MUST_MATCH = ['sim/data_bus_turnover/check_evidence.py',
              'sim/data_bus_turnover/check_tag_lookup.py',
              'sim/data_bus_turnover/tb_data_bus_turnover.sv',
              'sim/data_bus_turnover/run_tag_lookup_repair.py',
              'sim/data_bus_turnover/seal_tag_lookup_repair.py',
              'sim/data_bus_turnover/unit_cases.svh',
              'sim/data_bus_turnover/program.dat',
              'sim/data_bus_turnover/reference.json',
              'sim/data_bus_turnover/reference.trace',
              'sim/data_bus_turnover/prepare_program.py',
              'myriscv/mycpu_sync.v',
              'myriscv/data_bus_interconnect.v']
TAG = 'ds_data_bus_tag_lookup_repair_b_20261014_a'
PRIOR_REVIEW_SHA = '4de7282d07bd407560b9f1496cc4d78fbdd8dbe66cdfd7b4a5a0ed0336e4e319'
LOOKUP_EXPECTED = dict(det=64 * 23, rnd=64 * 8, rows=64, high_bits=21, tables=64, seed=20261014)


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
    prior = json.loads((ROOT / PRIOR_REVIEW).read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_tag_lookup_repair_20261014_a'
    assert control['status'] == 'TASK032_CONTROL_RAW_EVIDENCE_REVIEW_PASS_KEY_PENDING'
    assert key_receipt['status'] == 'DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS'
    assert sha(PRIOR_REVIEW) == PRIOR_REVIEW_SHA
    assert prior['status'] == 'TASK032_FIRST_SELECTOR_REPAIR_RAW_FUNCTIONAL_REVIEW_PASS_TIMING_FAIL'

    project = dict(previous['project_sha256'])
    changed = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed == {LOOKUP_TB}, sorted(changed)
    project[LOOKUP_TB] = sha(ROOT / LOOKUP_TB)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    protected = dict(previous['protected_evidence_sha256'])
    extra = {'sim/data_bus_turnover/inputs_tag_lookup_repair.json': sha(PREVIOUS),
             PRIOR_STOP_REPORT: sha(ROOT / PRIOR_STOP_REPORT)}
    for name in tree(PRIOR_STOP_RUN):
        if '/work/' in name or name.endswith('/work'):
            continue
        extra[name] = sha(ROOT / name)
    for name, digest in extra.items():
        if name in protected:
            assert protected[name] == digest, 'Duplicate protected path with different hash: ' + name
        else:
            protected[name] = digest
    missing = [n for n, h in protected.items() if not (ROOT / n).is_file() or sha(ROOT / n) != h]
    assert not missing, missing[:5]

    data = dict(
        status='TASK032_PARALLEL_INST_TAG_LOOKUP_REPAIR_B_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        control_reused=True,
        key_replayed=True,
        extra_job='tag_lookup',
        retry_of=previous['tag'],
        retry_reason=('first attempt stopped in its own harness: the look-up console was read from the '
                      'testbench trace file and the trace scenario counter printed x; the DUT key and '
                      'look-up behaviour themselves passed in that run'),
        project_sha256=project,
        vendor_sha256=previous['vendor_sha256'],
        tool_sha256=previous['tool_sha256'],
        compile_sources=previous['compile_sources'],
        expected_modules=previous['expected_modules'],
        include_dependencies=previous['include_dependencies'],
        timeouts=previous['timeouts'],
        protected_evidence_sha256=protected,
        previous_manifest='sim/data_bus_turnover/inputs_tag_lookup_repair.json',
        previous_manifest_sha256=sha(PREVIOUS),
        changed_project_files=[LOOKUP_TB],
        new_implementation_files=NEW_IMPLEMENTATION,
        must_match_previous=MUST_MATCH,
        bridge_repair=previous['bridge_repair'],
        lookup_tb=LOOKUP_TB,
        lookup_expected=LOOKUP_EXPECTED,
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
                        note='reviewed key; used as the exact-reproduction reference'),
        expected_key=key_receipt['checked_key'],
        previous_timing_review=PRIOR_REVIEW,
        previous_timing_review_sha256=PRIOR_REVIEW_SHA,
        checker_edit=previous['checker_edit'],
        changed_design_files=previous['changed_design_files'],
        changed_design_files_this_round=previous['changed_design_files_this_round'],
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
        scope=previous['scope'],
        limitations=previous['limitations'],
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
    import run_tag_lookup_repair_b as runner
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
