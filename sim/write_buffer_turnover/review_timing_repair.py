"""Codex raw evidence review for the Task031 timing repair; never runs HDL."""
import argparse
import json
import re
from pathlib import Path
import simulation_timing_repair as run


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-inputs', action='store_true')
    args = parser.parse_args()
    design = run.require_inputs()
    if args.check_inputs:
        print('RESULT: PASS review preparation; HDL NOT_RUN')
        return
    out = run.HERE / 'build' / run.TAG
    result = json.loads(run.common.read(out / 'result.json'))
    assert result['status'] == 'TASK031_TIMING_REPAIR_KEY_PASS'
    assert result['manifest_sha256'] == run.sha(run.DESIGN)
    assert run.sha(out / 'simulation_timing_repair_inputs.json') == run.sha(run.DESIGN)
    project = out / 'inputs/project'
    for name, digest in design['project_sha256'].items():
        assert run.sha(project / name) == digest, name
    for name, digest in design['vendor_sha256'].items():
        assert run.sha(out / 'inputs/vendor' / Path(name).name) == digest
    assert run.check_includes(project, design['compile_sources']) == design['include_dependencies']
    expected = dict(vlib=[run.MS / 'vlib.exe', out / 'work'],
        compile=run.compile_command(out, project, design), key=run.key_command(out, project, design))
    for name, argv in expected.items():
        meta = json.loads(run.common.read(out / (name + '.command.json')))
        assert meta['argv'] == list(map(str, argv)) and meta['cwd'] == str(out)
        assert meta['exit_code'] == meta['native_exit_after_wait'] == 0
        assert not meta['timed_out'] and meta['cleanup'] is None and meta['stdout_direct_to_file']
        assert meta['timeout_seconds'] == (180 if name == 'key' else 60)
        assert 0 <= meta['seconds'] <= meta['timeout_seconds'] + 30
    compiled = re.findall(r'-- Compiling module (\w+)', run.common.read(out / 'compile.log'))
    assert len(compiled) == 36 and set(compiled) == set(design['expected_modules'])
    assert 'Errors: 0, Warnings: 0' in run.common.read(out / 'compile.log')
    checked = run.review_key(out, project, design)
    assert result['completed'] == dict(key=checked)
    assert json.loads(run.common.read(out / 'git_before.json')) == json.loads(run.common.read(out / 'git_after.json'))
    gate_path = out / 'codex_review.json'
    assert not gate_path.exists(), 'Preserve existing review'
    hashes = dict(design['project_sha256'])
    hashes[run.DESIGN.relative_to(run.ROOT).as_posix()] = run.sha(run.DESIGN)
    hashes.update({p.relative_to(run.ROOT).as_posix(): run.sha(p) for p in out.rglob('*')
        if p.is_file() and 'work' not in p.relative_to(out).parts})
    prior = json.loads(run.common.read(run.OLD_GATE))
    gate = dict(status='WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS',
        repair_kind='TASK031_X32_RESPONSE_REGISTER_CE_TIMING_REPAIR', evidence_sha256=hashes,
        manifest_sha256=run.sha(run.DESIGN), key=checked, control=prior['control'], control_reused=True,
        controlled_cycles_saved=5, CPU_changed=False, TB_model_stimulus_changed=False,
        ISA_samples=[], board='NOT_RUN', PDS_timing='NOT_RUN', serial='NOT_OPENED')
    with gate_path.open('x', encoding='utf-8') as stream:
        json.dump(gate, stream, ensure_ascii=False, indent=2)
        stream.write('\n')
    print(json.dumps(dict(status=gate['status'], key_checks=889, events=430,
        CPU_requests=143, PDS_timing='NOT_RUN'), indent=2))


if __name__ == '__main__':
    main()
