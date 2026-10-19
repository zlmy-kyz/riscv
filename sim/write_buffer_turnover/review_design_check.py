"""Read Task031's existing design-check evidence. Never starts HDL or board tools."""
import ast
import json
import re
from pathlib import Path
from check_inputs import ROOT, HERE, MANIFEST, require_inputs, sha


def main():
    require_inputs()
    out = HERE / 'build/design_check_20261014_a'
    design_path = HERE / 'simulation_inputs.json'
    design = json.loads(design_path.read_text(encoding='utf-8'))
    assert design['input_manifest_sha256'] == sha(MANIFEST)
    for name, digest in design['sha256'].items():
        assert sha(ROOT / name) == digest, name
    logs = {name: (out / (name + '.log')).read_text(encoding='utf-8')
            for name in ('compile', 'control', 'key')}
    modules = re.findall(r'-- Compiling module (\w+)', logs['compile'])
    assert len(modules) == design['module_count'] == 36
    assert set(modules) == set(design['expected_modules'])
    for name, log in logs.items():
        assert 'Errors: 0, Warnings: 0' in log
        assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT', log)
        if name != 'compile':
            assert '$finish' in log
            assert log.strip() == (out / (name + '.transcript')).read_text(encoding='utf-8').strip()
            assert re.findall(r'IPSpecCheck: (\d+)', log) == ['04030130'] * 4
    groups = re.findall(r'CHECK: (\w+) PASS checks=(\d+)', logs['key'])
    assert [name for name, _ in groups] == design['groups']
    assert [int(count) for _, count in groups] == [10, 7, 6, 407, 12, 7, 10, 430]
    fields = dict(re.findall(r'(\w+)=(\d+)', next(line for line in logs['key'].splitlines()
                  if 'RESULT: PASS write_buffer_turnover_x32 ' in line)))
    fields = {name: int(value) for name, value in fields.items()}
    assert fields['tests'] == sum(int(count) for _, count in groups) == 889
    assert fields['cpu_events'] == 430 and fields['IRQ'] == 1
    assert fields['ACCEPTED'] == 81 and fields['SOC_TURNOVER'] == 69 and fields['MLATE'] == 0
    assert all(fields[name] > 0 for name in design['positive_key_coverage'])
    short_pattern = r'SHORT: cycles=(\d+) stores=(\d+) opportunities=(\d+) accepted=(\d+) late=(\d+) aw=(\d+) w=(\d+)'
    short = {name: list(map(int, re.findall(short_pattern, logs[name])[0])) for name in ('control', 'key')}
    assert short['control'][:5] == [49, 6, 5, 0, 5]
    assert short['key'][:5] == [44, 6, 5, 5, 0]
    assert short['control'][0] - short['key'][0] == 5
    # Inspect the supplied runner's regex constants, without importing/executing it.
    assignments = {}
    tree = ast.parse((HERE / 'simulation_runner.py').read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            if name in ('SHORT', 'RESULT_CTL', 'RESULT_KEY'):
                assignments[name] = ast.literal_eval(node.value)
    regex_matches = {name: len(re.findall(pattern, logs['key' if name == 'RESULT_KEY' else 'control']))
                     for name, pattern in assignments.items()}
    command_metadata = {}
    for name in ('vlib', 'compile'):
        data = json.loads((out / (name + '.command.json')).read_text(encoding='utf-8'))
        assert data['exit_code'] == data['native_exit_after_wait'] == 0 and not data['timed_out']
        command_metadata[name] = data
    missing = [name for name in ('control.command.json', 'key.command.json', 'git_before.json',
               'git_after.json', 'result.json', 'inputs.json', 'simulation_inputs.json') if not (out / name).exists()]
    evidence = {p.relative_to(ROOT).as_posix(): sha(p) for p in out.iterdir() if p.is_file()}
    result = dict(status='DESIGN_CHECK_LOGS_PASS_FORMAL_HANDOFF_INCOMPLETE',
        input_manifest_sha256=sha(MANIFEST), simulation_design_sha256=sha(design_path),
        current_inputs_match=True, compiled_modules=modules, groups=dict(groups),
        key_fields=fields, controlled_short=short, cycles_saved=5,
        console_transcript_match=True, vlib_compile_command_metadata=command_metadata,
        missing_design_check_artifacts=missing,
        formal_directory_exists=(HERE / 'build/ds_write_buffer_turnover_20261014_a').exists(),
        DeepSeek_report_exists=(ROOT / 'DeepSeek/任务031_结果_ds_write_buffer_turnover_20261014_a.md').exists(),
        saved_independent_EV_BUS_trace=False,
        runner_regex_match_counts=regex_matches,
        runner_regex_issue=None if all(value == 1 for value in regex_matches.values()) else
                           'Runner regexes do not match exactly one existing PASS/SHORT line',
        unsealed_inputs=['external vendor source hashes', 'reused runner helpers',
                         'numeric expected check counts'],
        evidence_sha256=evidence, functional_gate_open=False, HDL_rerun=False,
        PDS='NOT_RUN', serial='NOT_OPENED', board='NOT_RUN')
    review_dir = HERE / 'build/codex_design_check_review_20261014_a'
    review_dir.mkdir(exist_ok=False)
    with (review_dir / 'result.json').open('x', encoding='utf-8') as stream:
        json.dump(result, stream, ensure_ascii=False, indent=2)
    print(json.dumps({key: result[key] for key in ('status', 'cycles_saved', 'key_fields',
                     'missing_design_check_artifacts', 'runner_regex_match_counts', 'functional_gate_open')}, indent=2))


if __name__ == '__main__':
    main()
