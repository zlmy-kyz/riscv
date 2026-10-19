"""Codex Task032 raw evidence review, no HDL/board/PDS execution."""
import argparse
import json
import re
from pathlib import Path
import run


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--check-inputs', action='store_true')
    args = p.parse_args()
    data = run.require_inputs()
    if args.check_inputs:
        print('RESULT: PASS Task032 review preparation; HDL NOT_RUN')
        return
    out = run.HERE / 'build' / run.TAG
    raw = json.loads(run.common.read(out / 'result.json'))
    assert raw['status'] == 'DATA_BUS_RESPONSE_TURNOVER_KEY_GROUP_PASS'
    assert raw['manifest_sha256'] == run.sha(run.MANIFEST) == run.sha(out / 'inputs.json')
    project = out / 'inputs/project'
    for name, digest in data['project_sha256'].items():
        assert run.sha(project / name) == digest
    for name, digest in data['vendor_sha256'].items():
        assert run.sha(out / 'inputs/vendor' / Path(name).name) == digest
    assert run.check_includes(project, data['compile_sources']) == data['include_dependencies']
    commands = dict(vlib=[run.MS / 'vlib.exe', out / 'work'], compile=run.compile_command(out, project, data),
        control=run.job_command(out, project, 'control'), key=run.job_command(out, project, 'key'))
    for name, argv in commands.items():
        meta = json.loads(run.common.read(out / (name + '.command.json')))
        assert meta['argv'] == list(map(str, argv)) and meta['cwd'] == str(out)
        assert meta['exit_code'] == meta['native_exit_after_wait'] == 0
        assert not meta['timed_out'] and meta['cleanup'] is None and meta['stdout_direct_to_file']
        assert meta['timeout_seconds'] == (60 if name in ('vlib','compile') else 180)
        assert 0 <= meta['seconds'] <= meta['timeout_seconds'] + 30
        log = run.common.read(out / (name + '.log'))
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', log)
    modules = re.findall(r'-- Compiling module (\w+)', run.common.read(out / 'compile.log'))
    assert len(modules) == 38 and set(modules) == set(data['expected_modules'])
    assert 'Errors: 0, Warnings: 0' in run.common.read(out / 'compile.log')
    checked = {name: run.review_job(out, name, project) for name in ('control','key')}
    assert raw['completed'] == checked
    assert checked['control']['unit_cycles'] - checked['key']['unit_cycles'] == raw['unit_cycles_saved'] == 31
    for k, n in [('cycles','soc_cycles_saved'), ('mem_wait','soc_mem_wait_saved')]:
        assert checked['control']['fields'][k] - checked['key']['fields'][k] == raw[n] > 0
    assert json.loads(run.common.read(out / 'git_before.json')) == json.loads(run.common.read(out / 'git_after.json'))
    gate = out / 'codex_review.json'
    assert not gate.exists()
    evidence = dict(data['project_sha256'])
    evidence[run.MANIFEST.relative_to(run.ROOT).as_posix()] = run.sha(run.MANIFEST)
    evidence.update({p.relative_to(run.ROOT).as_posix(): run.sha(p) for p in out.rglob('*')
        if p.is_file() and 'work' not in p.relative_to(out).parts})
    value = dict(status='DATA_BUS_RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS',
        manifest_sha256=run.sha(run.MANIFEST),evidence_sha256=evidence,control=checked['control'],key=checked['key'],
        unit_cycles_saved=31,soc_cycles_saved=raw['soc_cycles_saved'],soc_mem_wait_saved=raw['soc_mem_wait_saved'],
        CPU_changed=False,ISA_samples=[],board='NOT_RUN',timing='NOT_RUN',PDS_review='NOT_RUN',serial='NOT_OPENED')
    with gate.open('x',encoding='utf-8') as f:
        json.dump(value,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps({k:value[k] for k in ('status','unit_cycles_saved','soc_cycles_saved','soc_mem_wait_saved')},indent=2))


if __name__ == '__main__':
    main()
