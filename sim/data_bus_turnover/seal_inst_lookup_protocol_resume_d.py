"""Seal the Task032 B-only protocol resume re-run manifest (attempt D).

inputs_inst_lookup_protocol_resume_d.json is derived from
inputs_inst_lookup_protocol_resume_c.json (sealed but never executed):
  * two project entries change: the protocol testbench (pre-edge W/R visibility per the
    sealed plan) and the independent reference (W completion accepts an already-accepted
    AW, and reset clears the cache valid bits);
  * the re-run D runner (a thin binding wrapper over the re-run B entry) and this sealer
    are added; everything else, including the sealed stimulus plan, stays byte-identical;
  * the protected set adds the never-executed C manifest and this round's reports.
"""
import argparse
import ast
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]

PREVIOUS = HERE / 'inputs_inst_lookup_protocol_resume_c.json'
MANIFEST = HERE / 'inputs_inst_lookup_protocol_resume_d.json'
REFERENCE = 'sim/data_bus_turnover/check_inst_lookup_protocol_resume.py'
PROTOCOL_TB = 'sim/data_bus_turnover/tb_inst_lookup_protocol_resume.sv'
C_STATE = 'DeepSeek/任务032寄存查询协议B续测C_准备状态与离线发现.md'
C_PROGRESS = 'DeepSeek/任务032寄存查询协议B续测C_离线根因进展.md'
NEW_IMPLEMENTATION = ['sim/data_bus_turnover/run_inst_lookup_protocol_resume_d.py',
                      'sim/data_bus_turnover/seal_inst_lookup_protocol_resume_d.py']
TAG = 'ds_data_bus_inst_lookup_protocol_resume_d_20261014_a'


def sha(path):
    import hashlib
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build():
    previous = json.loads(PREVIOUS.read_text(encoding='utf-8'))
    assert previous['tag'] == 'ds_data_bus_inst_lookup_protocol_resume_c_20261014_a'
    project = dict(previous['project_sha256'])
    changed = {n for n in project if sha(ROOT / n) != project[n]}
    assert changed == {REFERENCE, PROTOCOL_TB}, sorted(changed)
    for name in (REFERENCE, PROTOCOL_TB):
        project[name] = sha(ROOT / name)
    for name in NEW_IMPLEMENTATION:
        assert (ROOT / name).is_file(), name
        assert name not in project, name
        project[name] = sha(ROOT / name)

    protected = dict(previous['protected_evidence_sha256'])
    extra = {'sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_c.json': sha(PREVIOUS),
             C_STATE: sha(ROOT / C_STATE), C_PROGRESS: sha(ROOT / C_PROGRESS)}
    for name, digest in extra.items():
        if name in protected:
            assert protected[name] == digest, 'Duplicate protected path with different hash: ' + name
        else:
            protected[name] = digest
    missing = [n for n, h in protected.items() if not (ROOT / n).is_file() or sha(ROOT / n) != h]
    assert not missing, missing[:5]

    data = dict(previous)
    data.update(
        status='TASK032_REGISTERED_LOOKUP_PROTOCOL_RESUME_D_PREPARED_HDL_NOT_RUN',
        tag=TAG,
        retry_of=previous['tag'],
        retry_reason=('re-run C was sealed but never executed: the independent reference failed the '
                      'offline replay of the re-run B trace. Fixed: W completion now accepts an '
                      'already-accepted AW, reset clears the cache valid bits, and the protocol '
                      'testbench takes the plan-mandated pre-edge write visibility. The full 188-edge '
                      'trace now replays clean with every coverage counter non-zero.'),
        project_sha256=project,
        protected_evidence_sha256=protected,
        previous_manifest='sim/data_bus_turnover/inputs_inst_lookup_protocol_resume_c.json',
        previous_manifest_sha256=sha(PREVIOUS),
        changed_project_files=sorted({REFERENCE, PROTOCOL_TB}),
        new_implementation_files=NEW_IMPLEMENTATION,
        project_count=len(project),
        protected_count=len(protected),
        offline_replay=dict(trace='sim/data_bus_turnover/build/'
                                  'ds_data_bus_inst_lookup_protocol_resume_b_20261014_a/edge.log',
                            status='REPLAY_PASS', edges=188, mismatches=0,
                            coverage='all plan counters non-zero'),
    )
    return data


def check():
    data = json.loads(MANIFEST.read_text(encoding='utf-8'))
    for name in NEW_IMPLEMENTATION:
        ast.parse((ROOT / name).read_text(encoding='utf-8'), filename=name)
    sys.path.insert(0, str(HERE))
    import run_inst_lookup_protocol_resume_d as runner
    assert runner.require_inputs() == data
    print('SEAL CHECK PASS project=%d protected=%d modules=%d jobs=%s plan=%s ref=%s tb=%s' %
          (len(data['project_sha256']), len(data['protected_evidence_sha256']),
           len(data['expected_modules']), data['jobs'], data['stimulus_plan'],
           sha(ROOT / REFERENCE)[:16], sha(ROOT / PROTOCOL_TB)[:16]))


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
