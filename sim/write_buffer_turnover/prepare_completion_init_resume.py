"""Review Task031's compile failure and seal the minimal include-only resume."""
import ast
import json
import re
from pathlib import Path
from check_inputs import ROOT, HERE, MANIFEST, require_inputs, sha
from check_include_dependencies import check_includes

OLD_TAG = 'ds_write_buffer_turnover_20261014_a'
NEW_TAG = 'ds_write_buffer_turnover_init_resume_20261014_a'
PARAMS = {
    'ipcore/inst_rom/rtl/inst_rom_init_param.v': '77fdcc689dcfdfac13258f3754ae1f60351f806b055e7f4ae0e75e130a3af3a0',
    'ipcore/data_ram/rtl/data_ram_init_param.v': 'ad79a0fe32e541c0ec03f05fa44c4fd9870b9cd6bc3686815b4e25c222b550d3',
}


def read(path):
    return Path(path).read_text(encoding='utf-8')


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    require_inputs()
    old_path = HERE / 'simulation_completion_inputs.json'
    assert sha(old_path) == '513b578cf6d91ed50700194664b720027e49a7ba3d67867a8cda23466fb13c96'
    old = json.loads(read(old_path))
    for name, digest in old['project_sha256'].items():
        assert sha(ROOT / name) == digest, name
    failed = HERE / 'build' / OLD_TAG
    result = json.loads(read(failed / 'result.json'))
    assert result['status'] == 'STOPPED_FIRST_FAILURE' and result['completed'] == {}
    assert result['completion_manifest_sha256'] == sha(old_path)
    assert sha(failed / 'simulation_completion_inputs.json') == sha(old_path)
    assert sha(failed / 'inputs.json') == sha(MANIFEST)
    for name, digest in old['project_sha256'].items():
        assert sha(failed / 'inputs/project' / name) == digest, name
    for name, digest in old['vendor_sha256'].items():
        assert sha(failed / 'inputs/vendor' / Path(name).name) == digest
    log = read(failed / 'compile.log')
    assert 'Errors: 258, Warnings: 0' in log
    errors = [line for line in log.splitlines() if line.startswith('** Error:')]
    assert len(errors) == 258
    missing = [line for line in errors if 'Cannot find `include file' in line]
    assert len(missing) == 2 and all(any(Path(name).name in line for line in missing) for name in PARAMS)
    undefined = re.findall(r"Undefined variable: 'INIT_([0-9A-F]{2})'", log)
    assert len(undefined) == 256 and all(undefined.count(f'{i:02X}') == 2 for i in range(128))
    assert len(re.findall(r'-- Compiling module (\w+)', log)) == 36
    command_meta = {}
    for name, expected_code in (('vlib', 0), ('compile', 2)):
        meta = json.loads(read(failed / (name + '.command.json')))
        assert meta['exit_code'] == meta['native_exit_after_wait'] == expected_code
        assert not meta['timed_out'] and meta['timeout_seconds'] == 60 and meta['cleanup'] is None
        command_meta[name] = meta
    for name in ('control.log', 'key.log', 'control.command.json', 'key.command.json',
                 'git_after.json', 'codex_review.json'):
        assert not (failed / name).exists(), name
    report = ROOT / 'DeepSeek/任务031_结果_ds_write_buffer_turnover_20261014_a.md'
    preserved = {p.relative_to(ROOT).as_posix(): sha(p) for p in failed.rglob('*') if p.is_file() and
                 'work' not in p.relative_to(failed).parts}
    preserved[report.relative_to(ROOT).as_posix()] = sha(report)
    prep = HERE / 'build/init_resume_preparation_20261014_a'
    prep.mkdir(exist_ok=False)
    failure_review = dict(status='TASK031_MISSING_INIT_INCLUDE_RAW_FAILURE_CONFIRMED',
        compile_errors=258, warnings=0, missing_include_errors=2, undefined_INIT_errors=256,
        command_metadata=command_meta, control='NOT_RUN', key='NOT_RUN',
        absent_git_after_preserved=True, old_result_preserved=True,
        old_project_snapshots_checked=197, old_evidence_sha256=preserved,
        report_timing_note='vlib elapsed uses native metadata 0.2483402s; report 0.192s is a text mistake',
        HDL_rerun=False, PDS='NOT_RUN', board='NOT_RUN')
    review_path = prep / 'failure_review.json'
    save_new(review_path, failure_review)
    for name, digest in PARAMS.items():
        assert name not in old['project_sha256']
        assert not (failed / 'inputs/project' / name).exists()
        assert sha(ROOT / name) == digest
        definitions = re.findall(r'^localparam INIT_([0-9A-F]{2})\s*=', read(ROOT / name), re.M)
        assert definitions == [f'{i:02X}' for i in range(128)]
    new = dict(old)
    new['project_sha256'] = {**old['project_sha256'], **PARAMS}
    new['fixed_tag'] = NEW_TAG
    new['status'] = 'WRITE_BUFFER_TURNOVER_INIT_INCLUDE_RESUME_PREPARED_HDL_NOT_RUN'
    new['prior_completion_manifest_sha256'] = sha(old_path)
    new['prior_failure_sha256'] = preserved
    new['include_dependencies'] = check_includes(ROOT, old['compile_sources'])
    new['minimal_change'] = 'two include dependencies, include-closure check, new dispatch/review/gate identity only'
    additions = [HERE / name for name in ('check_include_dependencies.py', 'simulation_completion_init_resume.py',
                 'review_completion_init_resume.py', 'prepare_completion_init_resume.py', 'simulation_completion_inputs.json')]
    additions += [ROOT / 'tools/uart_loader/candidates/perf_2b' / name for name in (
        'run_write_buffer_turnover_init_resume_measurement.py', 'run_write_buffer_turnover_init_resume_measurements.ps1')]
    additions += [review_path]
    for path in additions:
        new['project_sha256'][path.relative_to(ROOT).as_posix()] = sha(path)
    for name in new['project_sha256']:
        if name.endswith('.py'):
            ast.parse(read(ROOT / name), filename=name)
    for name in ('compile_sources', 'expected_modules', 'module_count', 'groups', 'key_result_fields',
                 'plusargs', 'cpu_image', 'image_relative_to_here', 'timeouts', 'CPU_changed', 'ISA_samples'):
        assert new[name] == old[name], name
    new_path = HERE / 'simulation_completion_init_resume_inputs.json'
    save_new(new_path, new)
    # Copy and inspect the exact frozen layout. This does not invoke vlib/vlog/vsim.
    import simulation_completion_init_resume as resume
    assert resume.require_completion_inputs() == new
    copy_check = prep / 'copy_check'
    copy_check.mkdir(exist_ok=False)
    project, vendors = resume.snapshot_inputs(copy_check, new)
    assert len(vendors) == 3
    for name, digest in PARAMS.items():
        assert sha(project / name) == digest
    for name, digest in preserved.items():
        assert sha(ROOT / name) == digest, name
    receipt = dict(status='TASK031_INIT_INCLUDE_RESUME_STATIC_PREPARATION_PASS_HDL_NOT_RUN',
        resume_manifest_sha256=sha(new_path), original_manifest_sha256=sha(old_path),
        input_manifest_sha256=sha(MANIFEST), project_files=len(new['project_sha256']),
        added_include_sha256=PARAMS, include_dependencies=new['include_dependencies'],
        copy_check_pass=True, stimulus_model_oracle_checks_timeouts_unchanged=True,
        previous_failure_evidence_files=len(preserved), previous_failure_preserved=True,
        new_tag=NEW_TAG, new_directory_exists=(HERE / 'build' / NEW_TAG).exists(),
        CPU_sha256=sha(ROOT / 'myriscv/mycpu_sync.v'),
        bridge_sha256=sha(ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'),
        HDL='NOT_RUN', PDS='NOT_RUN', serial='NOT_OPENED')
    assert not receipt['new_directory_exists']
    save_new(prep / 'static_review.json', receipt)
    print(json.dumps(receipt, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
