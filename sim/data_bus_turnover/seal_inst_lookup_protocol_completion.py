"""Seal the Task032 B-only protocol-completion manifest.

inputs_inst_lookup_protocol_completion.json is derived from the reviewed E manifest
(inputs_inst_lookup_protocol_resume_e.json, SHA e7ca966c...):

  * no existing project file changes: the E testbench, the E reference, the E runners
    and every E result stay byte-identical historical inputs;
  * the only compile-top substitution is
    sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv ->
    sim/data_bus_turnover/tb_inst_lookup_protocol_completion.sv, and
    expected_modules swaps tb_inst_lookup_protocol_resume for
    tb_inst_lookup_protocol_completion (still 39 modules);
  * four new implementation files are added: the completion testbench, the completion
    checker, this round's runner and this sealer;
  * vendor/tool hashes, include dependencies and timeouts stay identical to E;
  * the protected set is E's protected set, plus the E manifest, the complete E run
    directory (except the work library), the E report, the Codex coverage-review
    receipt and every prior file it binds, plus this round's preparation directory;
    a path present twice with different hashes stops the seal;
  * historical identity relocation for the live hand-off document follows the old
    rule: the live doc stays updatable, the saved copy keeps the identity, and the
    partial receipt 2a482844... keeps the same checked_key/checked_A binding;
  * coverage_contract records the thresholds the completion checker declares
    (ar_r_same_min, dual_present_min, plan_sha256, ...) together with the plan.
"""
import argparse
import ast
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_inst_lookup_protocol_resume_e.json'
MANIFEST = HERE / 'inputs_inst_lookup_protocol_completion.json'
E_TAG = 'ds_data_bus_inst_lookup_protocol_resume_e_20261014_a'
E_MANIFEST_SHA = 'e7ca966c62d4ba59f4c5f8ae6fc24a4704c10b649c6fee5480cb018bbb746f74'
TAG = 'ds_data_bus_inst_lookup_protocol_completion_20261014_a'
OLD_PROTOCOL_TB = 'sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv'
TB = 'sim/data_bus_turnover/tb_inst_lookup_protocol_completion.sv'
CHECKER = 'sim/data_bus_turnover/check_inst_lookup_protocol_completion.py'
RUNNER = 'sim/data_bus_turnover/run_inst_lookup_protocol_completion.py'
SEALER = 'sim/data_bus_turnover/seal_inst_lookup_protocol_completion.py'
NEW_IMPLEMENTATION = [TB, CHECKER, RUNNER, SEALER]
JOBS = ['vlib', 'compile', 'inst_lookup_protocol_completion']
E_RUN = 'sim/data_bus_turnover/build/ds_data_bus_inst_lookup_protocol_resume_e_20261014_a'
E_REPORT = ('DeepSeek/任务032寄存查询协议B续测E_结果_'
            'ds_data_bus_inst_lookup_protocol_resume_e_20261014_a.md')
PREP = 'sim/data_bus_turnover/build/protocol_coverage_preparation_20261014_a'
RECEIPT = PREP + '/evidence_review.json'
RECEIPT_SHA = '5bdabc0ba5614d2e644009faa0f4a8b7282e1280d56bb8a92c8f34b29964ac49'
PARTIAL_RECEIPT = 'sim/data_bus_turnover/build/registered_protocol_repair_preparation_20261014_a/failure_review.json'
PARTIAL_RECEIPT_SHA = '2a48284482553a91d311df3d19fa26678d9359e1b8a20e738bc05e4c2a0614a1'
CONTRACT_KEYS = ('ar_r_same_min', 'dual_present_min', 'plan_sha256')


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def read(path):
    return Path(path).read_text(encoding='utf-8')


def rel(path):
    return str(Path(path).resolve().relative_to(ROOT)).replace('\\', '/')


def tree(directory):
    return sorted(str(p.relative_to(ROOT)).replace('\\', '/')
                  for p in (ROOT / directory).rglob('*') if p.is_file())


def plan_summary():
    sys.path.insert(0, str(HERE))
    import check_inst_lookup_protocol_completion as checker
    return checker.plan_summary()


def coverage_contract(plan):
    contract = dict(plan)
    contract.update(same_edge_required=True, dual_present_required=True,
                    plan_source=CHECKER,
                    w_commit_rule=('WREADY && (AW accepted on this edge or the owner AW '
                                   'was accepted earlier)'))
    return contract


def build():
    previous = json.loads(read(PREVIOUS))
    assert previous['tag'] == E_TAG
    assert sha(PREVIOUS) == E_MANIFEST_SHA, 'the reviewed E manifest changed'

    project = dict(previous['project_sha256'])
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, 'already a project input: ' + name
        project[name] = sha(ROOT / name)
    changed = sorted(n for n, h in previous['project_sha256'].items()
                     if sha(ROOT / n) != h)
    assert not changed, 'existing project input changed: ' + str(changed)

    compile_sources = [TB if n == OLD_PROTOCOL_TB else n for n in previous['compile_sources']]
    assert compile_sources != previous['compile_sources']
    assert compile_sources.count(TB) == 1 and OLD_PROTOCOL_TB not in compile_sources
    expected_modules = [('tb_inst_lookup_protocol_completion' if m == 'tb_inst_lookup_protocol_resume'
                         else m) for m in previous['expected_modules']]
    assert len(expected_modules) == 39
    assert 'tb_inst_lookup_protocol_completion' in expected_modules
    assert 'tb_inst_lookup_protocol_resume' not in expected_modules

    # ---- protected set -------------------------------------------------------
    protected = dict(previous['protected_evidence_sha256'])
    extra = {rel(PREVIOUS): sha(PREVIOUS)}
    for name in tree(E_RUN):
        if '/work/' in name or name.endswith('/work'):
            continue
        extra[name] = sha(ROOT / name)
    extra[E_REPORT] = sha(ROOT / E_REPORT)
    receipt = json.loads(read(ROOT / RECEIPT))
    assert sha(ROOT / RECEIPT) == RECEIPT_SHA
    extra[RECEIPT] = RECEIPT_SHA
    for name, digest in receipt['prior_files_sha256'].items():
        extra[name] = digest
    for name in tree(PREP):
        extra[name] = sha(ROOT / name)
    for name, digest in extra.items():
        if name in protected:
            assert protected[name] == digest, \
                'duplicate protected path with different hash: ' + name
        else:
            protected[name] = digest
    missing = [n for n, h in protected.items()
               if not (ROOT / n).is_file() or sha(ROOT / n) != h]
    assert not missing, missing[:5]

    # ---- partial-receipt binding --------------------------------------------
    assert previous['partial_review']['sha256'] == PARTIAL_RECEIPT_SHA
    assert previous['partial_review']['path'] == PARTIAL_RECEIPT
    assert sha(ROOT / PARTIAL_RECEIPT) == PARTIAL_RECEIPT_SHA
    assert protected.get(PARTIAL_RECEIPT) in (None, PARTIAL_RECEIPT_SHA)

    plan = plan_summary()
    for key in CONTRACT_KEYS:
        assert key in plan, 'checker plan_summary lacks ' + key
    assert plan['ar_r_same_min'] >= 1 and plan['dual_present_min'] >= 1
    contract = coverage_contract(plan)

    data = dict(previous)
    data.update(
        status='TASK032_PROTOCOL_COMPLETION_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        retry_of=previous['tag'],
        retry_reason=('the reviewed E run passed natively but its coverage model and stimulus '
                      'identity were incomplete (AR/R never on one edge, I/D never both valid, '
                      'memory committed on AW instead of W, plan scenario all zero); this round '
                      'replaces only the B-only compile top and adds the completion reference, '
                      'runner and sealer'),
        jobs=JOBS,
        project_sha256=project,
        protected_evidence_sha256=protected,
        compile_sources=compile_sources,
        expected_modules=expected_modules,
        protocol_tb=TB,
        replaced_compile_top=OLD_PROTOCOL_TB,
        previous_manifest=rel(PREVIOUS),
        previous_manifest_sha256=sha(PREVIOUS),
        changed_project_files=[],
        new_implementation_files=NEW_IMPLEMENTATION,
        project_count=len(project),
        protected_count=len(protected),
        stimulus_plan=plan,
        coverage_contract=contract,
    )
    return data


def check():
    data = json.loads(read(MANIFEST))
    assert data['tag'] == TAG
    for name in NEW_IMPLEMENTATION:
        if name.endswith('.py'):
            ast.parse(read(ROOT / name), filename=name)
    sys.path.insert(0, str(HERE))
    import run_inst_lookup_protocol_completion as runner
    assert runner.require_inputs() == data
    print('SEAL CHECK PASS project=%d protected=%d modules=%d jobs=%s plan=%s '
          'ar_r_same_min=%s dual_present_min=%s'
          % (len(data['project_sha256']), len(data['protected_evidence_sha256']),
             len(data['expected_modules']), data['jobs'], data['stimulus_plan'],
             data['coverage_contract']['ar_r_same_min'],
             data['coverage_contract']['dual_present_min']))


def plan_only():
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
    plan = plan_summary()
    print(json.dumps(dict(tag=TAG, manifest=MANIFEST.name, previous=PREVIOUS.name,
                          jobs=JOBS, compile_top=TB, replaced_compile_top=OLD_PROTOCOL_TB,
                          new_implementation_files=NEW_IMPLEMENTATION,
                          stimulus_plan=plan,
                          coverage_contract=coverage_contract(plan)),
                     ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    parser.add_argument('--check-inputs', action='store_true')
    parser.add_argument('--plan-only', action='store_true')
    args = parser.parse_args()
    if args.check:
        check()
        return
    if args.check_inputs or args.plan_only:
        plan_only()
        return
    assert not MANIFEST.exists(), 'do not overwrite the sealed manifest'
    data = build()
    MANIFEST.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('SEALED', len(data['project_sha256']), 'project,',
          len(data['protected_evidence_sha256']), 'protected,',
          len(data['expected_modules']), 'modules, SHA', sha(MANIFEST))


if __name__ == '__main__':
    main()
