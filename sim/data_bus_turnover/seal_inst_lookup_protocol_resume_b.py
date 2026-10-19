"""Seal the Task032 B-only protocol resume re-run manifest (attempt B).

inputs_inst_lookup_protocol_resume_b.json is derived from
inputs_inst_lookup_protocol_resume.json, the manifest of the stopped first attempt
(which never reached the simulation because the testbench used the SystemVerilog
reserved word `edge` as a task parameter):
  * the only changed project entry is the protocol testbench, renamed to `edge_id`
    with no logic, stimulus, criteria or coverage change;
  * the re-run runner and this sealer are added; everything else stays byte-identical;
  * the protected set adds the stopped manifest, its report and its run directory.

--check re-verifies the seal (AST, input identity, receipt bindings, plan identity).
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_inst_lookup_protocol_resume.json'
MANIFEST = HERE / 'inputs_inst_lookup_protocol_resume_b.json'
PROTOCOL_TB = 'sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv'
STOPPED_RUN = 'sim/data_bus_turnover/build/ds_data_bus_inst_lookup_protocol_resume_20261014_a'
STOPPED_REPORT = ('DeepSeek/任务032寄存查询协议B续测_结果_'
                  'ds_data_bus_inst_lookup_protocol_resume_20261014_a.md')
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/run_inst_lookup_protocol_resume_b.py',
                      'sim/data_bus_turnover/seal_inst_lookup_protocol_resume_b.py']
TAG = 'ds_data_bus_inst_lookup_protocol_resume_b_20261014_a'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(directory):
    return sorted(str(p.relative_to(ROOT)).replace('\\', '/')
                  for p in (ROOT / directory).rglob('*') if p.is_file())


def build():
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_inst_lookup_protocol_resume_20261014_a'
    project = dict(previous['project_sha256'])
    changed = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed == {PROTOCOL_TB}, sorted(changed)
    project[PROTOCOL_TB] = sha(ROOT / PROTOCOL_TB)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    protected = dict(previous['protected_evidence_sha256'])
    extra = {'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume.json': sha(PREVIOUS),
             STOPPED_REPORT: sha(ROOT / STOPPED_REPORT)}
    for name in tree(STOPPED_RUN):
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

    data = dict(previous)
    data.update(
        status='TASK032_REGISTERED_LOOKUP_PROTOCOL_RESUME_B_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        retry_of=previous['tag'],
        retry_reason=('the first attempt stopped in vlog: the protocol testbench used the '
                      'SystemVerilog reserved word `edge` as a task parameter; the identifier is '
                      'renamed to `edge_id` with no logic, stimulus or criteria change'),
        project_sha256=project,
        protected_evidence_sha256=protected,
        previous_manifest='sim/data_bus_turnover/inputs_inst_lookup_protocol_resume.json',
        previous_manifest_sha256=sha(PREVIOUS),
        changed_project_files=[PROTOCOL_TB],
        new_implementation_files=NEW_IMPLEMENTATION,
        project_count=len(project),
        protected_count=len(protected),
    )
    return data


def check():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name in NEW_IMPLEMENTATION:
        ast.parse((ROOT / name).read_text(encoding='utf-8'), filename=name)
    sys.path.insert(0, str(HERE))
    import run_inst_lookup_protocol_resume_b as runner
    assert runner.require_inputs() == data
    print('SEAL CHECK PASS project=%d protected=%d modules=%d jobs=%s plan=%s tb=%s' %
          (len(data['project_sha256']), len(data['protected_evidence_sha256']),
           len(data['expected_modules']), data['jobs'], data['stimulus_plan'],
           sha(ROOT / PROTOCOL_TB)[:16]))


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
