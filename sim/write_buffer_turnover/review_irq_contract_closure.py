"""Codex closes the existing raw run with the independently repaired IRQ schedule.

No HDL rerun, no edits to failed run folders, and no fabricated git_after/result.
"""
import inspect
import json
import re
import subprocess
from pathlib import Path
from check_inputs import ROOT, HERE, MANIFEST, sha
import simulation_completion_init_resume as resume
import check_completion_evidence as evidence
from completion_irq_drain_reference import build_reference, event_line

OUT = HERE / 'build/ds_write_buffer_turnover_init_resume_20261014_a'
CLOSURE = HERE / 'build/codex_irq_contract_closure_20261014_a'


def read(path):
    return Path(path).read_text(encoding='utf-8')


def save_new(path, value):
    with Path(path).open('x', encoding='utf-8') as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)
        stream.write('\n')


def main():
    design = resume.require_completion_inputs()
    raw_result = json.loads(read(OUT / 'result.json'))
    assert raw_result['status'] == 'STOPPED_FIRST_FAILURE' and set(raw_result['completed']) == {'control'}
    assert raw_result['error'] == 'AssertionError: '
    assert raw_result['completion_manifest_sha256'] == sha(resume.DESIGN)
    assert sha(OUT / 'simulation_completion_inputs.json') == sha(resume.DESIGN)
    assert sha(OUT / 'inputs.json') == sha(MANIFEST)
    assert not (OUT / 'git_after.json').exists() and not (OUT / 'codex_review.json').exists()
    for name, digest in design['project_sha256'].items():
        assert sha(OUT / 'inputs/project' / name) == digest, name
    for name, digest in design['vendor_sha256'].items():
        assert sha(OUT / 'inputs/vendor' / Path(name).name) == digest
    before = json.loads(read(OUT / 'git_before.json'))
    current = resume.base.git_snapshot()
    assert before['head'] == current['head'] and before['branch'] == current['branch']
    allowed_paths = [
        'DeepSeek/任务031续测_结果_ds_write_buffer_turnover_init_resume_20261014_a.md',
        'sim/write_buffer_turnover/completion_irq_drain_reference.py',
        'sim/write_buffer_turnover/review_irq_contract_closure.py',
        'tools/uart_loader/candidates/perf_2b/run_write_buffer_turnover_irq_closure_measurement.py',
        'tools/uart_loader/candidates/perf_2b/run_write_buffer_turnover_irq_closure_measurements.ps1',
    ]
    allowed = set(subprocess.run(['git', 'status', '--porcelain=v1', '-uall', '--', *allowed_paths],
        cwd=ROOT, check=True, capture_output=True, text=True, encoding='utf-8').stdout.splitlines())
    added = set(current['status'].splitlines()) - set(before['status'].splitlines())
    removed = set(before['status'].splitlines()) - set(current['status'].splitlines())
    assert added <= allowed and not removed, (added - allowed, removed)
    project = OUT / 'inputs/project'
    cases = read(project / 'sim/write_buffer_turnover/turnover_cases.svh')
    cpu = read(project / 'myriscv/mycpu_sync.v')
    csr = read(project / 'myriscv/csr_file.v')
    assert "if(bdv && bdr && bdw && bda=='h800 && !irq_sent) irq_schedule=1;" in cases
    assert 'always @(negedge clk)' in cases and 'begin soc_irq=1;irq_sent=1;end' in cases
    assert '((flow_state == FLOW_RUN) && !irq_candidate' in cpu
    assert 'pipeline_empty && irq_candidate && !sync_trap_event' in cpu
    assert '!id_ex_valid && !ex_mem_valid && !mem_wb_valid' in cpu
    assert 'else if (normal_retire)' in cpu and 'arch_next_pc <= mem_wb_next_pc;' in cpu
    assert 'assign irq_pending = (irq_external ?' in csr
    bus_rows = [line.split() for line in read(OUT / 'key.bus.log').splitlines()]
    first_store = next(row for row in bus_rows if row[0] == 'CPU_REQ' and row[2] == '1' and row[4] == '40000800')
    store_cycle = int(first_store[1])
    add_response = next(row for row in bus_rows if row[0] == 'IRSP' and row[2] == '1' and row[4] == '00520233')
    assert int(add_response[1]) < store_cycle
    assert any(row[:2] == ['WAIT', str(store_cycle + 1)] and row[2] == 'IRQ' for row in bus_rows)
    # The contract is fixed before consulting EV values: one issued ADD drains.
    reference = build_reference(project / design['cpu_image'])
    old_reference = json.loads(read(HERE / 'completion_reference.json'))
    assert reference['requests'] == old_reference['requests'] and reference['final_words'] == old_reference['final_words']
    changed = [i for i, (a, b) in enumerate(zip(reference['events'], old_reference['events'])) if a != b]
    assert changed == [23, 24, 25, 26] and reference['irq_pc'] == 0x40000060
    CLOSURE.mkdir(exist_ok=False)
    corrected_path = CLOSURE / 'completion_reference.json'
    save_new(corrected_path, reference)
    with (CLOSURE / 'completion_reference.trace').open('x', encoding='utf-8') as stream:
        stream.write('\n'.join(event_line(event) for event in reference['events']) + '\n')
    source = inspect.getsource(evidence.review_job)
    assert source.count("HERE / 'completion_reference.json'") == 2
    namespace = dict(evidence.__dict__, CORRECTED_REFERENCE_PATH=corrected_path)
    exec(compile(source.replace("HERE / 'completion_reference.json'", 'CORRECTED_REFERENCE_PATH'),
                 '<same_strict_review_with_correct_IRQ_schedule>', 'exec'), namespace)
    checked = {name: namespace['review_job'](OUT, name, design) for name in ('control', 'key')}
    assert checked['control'] == raw_result['completed']['control']
    assert checked['key']['cycles'] == 44 and checked['control']['cycles'] == 49
    assert checked['key']['events_checked'] == 430 and checked['key']['bus']['SoC_accepted'] == 68
    command_meta = {}
    for name in ('vlib', 'compile', 'control', 'key'):
        meta = json.loads(read(OUT / (name + '.command.json')))
        assert meta['exit_code'] == meta['native_exit_after_wait'] == 0 and not meta['timed_out']
        assert meta['cleanup'] is None and meta['stdout_direct_to_file']
        assert meta['cwd'] == str(OUT) and 0 <= meta['seconds'] <= meta['timeout_seconds'] + 30
        assert meta['timeout_seconds'] == (60 if name in ('vlib', 'compile') else 180)
        assert Path(meta['argv'][0]).name == {'vlib':'vlib.exe','compile':'vlog.exe','control':'vsim.exe','key':'vsim.exe'}[name]
        command_meta[name] = meta
    expected_compile = [str(Path('D:/modelsim/win64pe/vlog.exe')), '-sv',
        '+incdir+' + (project / 'myriscv').as_posix(),
        '+incdir+' + (project / 'sim/write_buffer_turnover').as_posix(),
        '+incdir+' + (project / 'ipcore/inst_rom/rtl').as_posix(),
        '+incdir+' + (project / 'ipcore/data_ram/rtl').as_posix(), '-work', str(OUT / 'work'),
        *[str(OUT / 'inputs/vendor' / Path(name).name) for name in design['vendor_sha256']],
        *[str(project / name) for name in design['compile_sources']]]
    assert command_meta['compile']['argv'] == expected_compile
    assert command_meta['vlib']['argv'] == [str(Path('D:/modelsim/win64pe/vlib.exe')), str(OUT / 'work')]
    for name in ('control', 'key'):
        expected_job = [str(Path('D:/modelsim/win64pe/vsim.exe')), '-batch', '-lib', str(OUT / 'work'),
            'tb_write_buffer_turnover_completion', '-gPOSTED=1', '-gTURNOVER=' + ('0' if name == 'control' else '1'),
            '+CPU_IMAGE=' + str(project / design['cpu_image']), '+EV_LOG=' + str(OUT / (name + '.events.log')),
            '+BUS_LOG=' + str(OUT / (name + '.bus.log'))]
        expected_job += ['+%s=%d' % (key, value) for key, value in design['plusargs'].items() if key != 'CPU_IMAGE']
        expected_job += ['-logfile', str(OUT / (name + '.transcript')), '-do', 'run -all; quit -f']
        assert command_meta[name]['argv'] == expected_job
    compiled = re.findall(r'-- Compiling module (\w+)', read(OUT / 'compile.log'))
    assert len(compiled) == 36 and set(compiled) == set(design['expected_modules'])
    assert 'Errors: 0, Warnings: 0' in read(OUT / 'compile.log')
    save_new(CLOSURE / 'git_at_codex_review.json', dict(current=current,
        original_git_after='ABSENT_NOT_BACKFILLED', allowed_added_status_rows=sorted(added),
        all_207_registered_inputs_and_frozen_execution_copies_match=True))
    save_new(CLOSURE / 'irq_contract_diagnosis.json', dict(status='IRQ_REFERENCE_IMMEDIATE_INSERTION_ERROR_CONFIRMED',
        first_store_cycle=store_cycle, following_ADD_instruction_response_cycle=int(add_response[1]),
        IRQ_pin_assertion='TB next negedge after store acceptance',
        expected_drained_instruction='4000005c:00520233 ADD x4,x4,x5',
        expected_irq_PC='40000060', cause=11, tval=0, target='40000100', mret_target='40000060',
        corrected_reference_event_indices=changed, event_count=430, unchanged_CPU_data_requests=143,
        old_reference_preserved=True, old_STOP_result_preserved=True, HDL_rerun=False))
    hashes = {p.relative_to(ROOT).as_posix(): sha(p) for p in OUT.rglob('*') if p.is_file() and
              'work' not in p.relative_to(OUT).parts}
    hashes.update(design['project_sha256'])
    hashes.update({resume.DESIGN.relative_to(ROOT).as_posix(): sha(resume.DESIGN)})
    hashes.update({p.relative_to(ROOT).as_posix(): sha(p) for p in CLOSURE.iterdir() if p.is_file()})
    for name in allowed_paths:
        hashes[name] = sha(ROOT / name)
    gate = dict(status='WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS', input_manifest_sha256=sha(MANIFEST),
        evidence_sha256=hashes, closure_kind='OFFLINE_IRQ_CONTRACT_REFERENCE_REPAIR_NO_HDL_RERUN',
        source_run=OUT.relative_to(ROOT).as_posix(), source_runner_status='STOPPED_FIRST_FAILURE_PRESERVED',
        original_git_after='ABSENT_NOT_BACKFILLED', key=checked['key'], control=checked['control'],
        command_metadata=command_meta, controlled_cycles_saved=5, corrected_IRQ_PC='40000060',
        CPU_changed=False, RTL_changed=False, TB_model_stimulus_changed=False,
        ISA_samples=[], board='NOT_RUN', PDS_review='NOT_RUN', serial='NOT_OPENED')
    save_new(CLOSURE / 'codex_review.json', gate)
    print(json.dumps(dict(status=gate['status'], events=430, CPU_requests=143, SoC_stores=73,
        SoC_opportunities=69, SoC_accepted=68, cycles_saved=5, IRQ_PC='40000060',
        old_STOP_result_preserved=True, HDL_rerun=False, board='NOT_RUN'), indent=2))


if __name__ == '__main__':
    main()
