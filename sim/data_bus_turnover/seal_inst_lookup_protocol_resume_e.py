"""Seal the Task032 B-only protocol resume re-run manifest (attempt E).

inputs_inst_lookup_protocol_resume_e.json is derived from
inputs_inst_lookup_protocol_resume_d.json:
  * the only changed project entry is the re-run B entry, whose redundant assertion on a
    key the reference does not return is removed;
  * the re-run E runner (a thin binding wrapper) and this sealer are added; the protocol
    testbench, the independent reference, the bridge and the sealed stimulus plan stay
    byte-identical;
  * the protected set adds the re-run D manifest, its run directory and this round's
    report.
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_inst_lookup_protocol_resume_d.json'
MANIFEST = HERE / 'inputs_inst_lookup_protocol_resume_e.json'
RUNNER_B = 'sim/data_bus_turnover/run_inst_lookup_protocol_resume_b.py'
STOPPED_RUN = 'sim/data_bus_turnover/build/ds_data_bus_inst_lookup_protocol_resume_d_20261014_a'
STOPPED_REPORT = ('DeepSeek/任务032寄存查询协议B续测D_结果_'
                  'ds_data_bus_inst_lookup_protocol_resume_d_20261014_a.md')
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/run_inst_lookup_protocol_resume_e.py',
                      'sim/data_bus_turnover/seal_inst_lookup_protocol_resume_e.py']
TAG = 'ds_data_bus_inst_lookup_protocol_resume_e_20261014_a'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def tree(directory):
    return sorted(str(p.relative_to(ROOT)).replace('\\', '/')
                  for p in (ROOT / directory).rglob('*') if p.is_file())


def build():
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_inst_lookup_protocol_resume_d_20261014_a'
    project = dict(previous['project_sha256'])
    changed = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed == {RUNNER_B}, sorted(changed)
    project[RUNNER_B] = sha(ROOT / RUNNER_B)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    protected = dict(previous['protected_evidence_sha256'])
    extra = {'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_d.json': sha(PREVIOUS),
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
        status='TASK032_REGISTERED_LOOKUP_PROTOCOL_RESUME_E_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        retry_of=previous['tag'],
        retry_reason=('re-run D executed cleanly (protocol simulation and the independent '
                      'reference both passed, verified by offline replay of its own trace); the '
                      'only failure was a runner assertion on a key the reference does not return, '
                      'now removed'),
        project_sha256=project,
        protected_evidence_sha256=protected,
        previous_manifest='sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_d.json',
        previous_manifest_sha256=sha(PREVIOUS),
        changed_project_files=[RUNNER_B],
        new_implementation_files=NEW_IMPLEMENTATION,
        project_count=len(project),
        protected_count=len(protected),
        offline_replay=dict(trace=STOPPED_RUN + '/edge.log', status='REPLAY_PASS',
                            edges=188, mismatches=0),
    )
    return data


def check():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name in NEW_IMPLEMENTATION:
        ast.parse((ROOT / name).read_text(encoding='utf-8'), filename=name)
    sys.path.insert(0, str(HERE))
    import run_inst_lookup_protocol_resume_e as runner
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
