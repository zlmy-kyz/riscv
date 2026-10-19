"""Codex offline review after DeepSeek execution; creates the existing functional gate."""
import argparse
import json
import re
from pathlib import Path
from check_inputs import HERE, ROOT, MANIFEST, sha
from simulation_completion_runner import DESIGN, TAG, read, require_completion_inputs
from check_completion_evidence import review_job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check-inputs', action='store_true')
    args = parser.parse_args()
    design = require_completion_inputs()
    if args.check_inputs:
        print('RESULT: PASS review inputs; HDL NOT_RUN; no gate created')
        return
    out = HERE / 'build' / TAG
    gate_path = out / 'codex_review.json'
    assert not gate_path.exists(), 'Preserve existing review'
    result = json.loads(read(out / 'result.json'))
    assert result['status'] == 'WRITE_BUFFER_TURNOVER_COMPLETION_KEY_AND_CONTROL_PASS'
    assert result['input_manifest_sha256'] == sha(MANIFEST)
    assert result['completion_manifest_sha256'] == sha(DESIGN)
    assert sha(out / 'inputs.json') == sha(MANIFEST)
    assert sha(out / 'simulation_completion_inputs.json') == sha(DESIGN)
    before = json.loads(read(out / 'git_before.json'))
    assert before == json.loads(read(out / 'git_after.json'))
    project = out / 'inputs/project'
    expected_compile = ['D:/modelsim/win64pe/vlog.exe', '-sv',
        '+incdir+' + (project / 'myriscv').as_posix(),
        '+incdir+' + (project / 'sim/write_buffer_turnover').as_posix(),
        '+incdir+' + (project / 'ipcore/inst_rom/rtl').as_posix(),
        '+incdir+' + (project / 'ipcore/data_ram/rtl').as_posix(), '-work', str(out / 'work'),
        *[str(out / 'inputs/vendor' / name.rsplit('/', 1)[-1]) for name in design['vendor_sha256']],
        *[str(project / name) for name in design['compile_sources']]]
    # Path rendering of tool binaries follows the native runner's Path objects.
    expected_compile[0] = str(Path(expected_compile[0]))
    for name in ('vlib', 'compile', 'control', 'key'):
        meta = json.loads(read(out / (name + '.command.json')))
        assert meta['exit_code'] == meta['native_exit_after_wait'] == 0 and not meta['timed_out']
        assert meta['timeout_seconds'] == (60 if name in ('vlib', 'compile') else 180)
        assert meta['cleanup'] is None and meta['stdout_direct_to_file']
        assert meta['cwd'] == str(out) and 0 <= meta['seconds'] <= meta['timeout_seconds'] + 30
        if name == 'vlib':
            assert meta['argv'] == [str(Path('D:/modelsim/win64pe/vlib.exe')), str(out / 'work')]
        elif name == 'compile':
            assert meta['argv'] == expected_compile
        else:
            expected_argv = [str(Path('D:/modelsim/win64pe/vsim.exe')), '-batch',
                '-lib', str(out / 'work'), 'tb_write_buffer_turnover_completion', '-gPOSTED=1',
                '-gTURNOVER=' + ('0' if name == 'control' else '1'),
                '+CPU_IMAGE=' + str(project / design['cpu_image']),
                '+EV_LOG=' + str(out / (name + '.events.log')), '+BUS_LOG=' + str(out / (name + '.bus.log'))]
            expected_argv += ['+%s=%d' % (key, value) for key, value in design['plusargs'].items() if key != 'CPU_IMAGE']
            expected_argv += ['-logfile', str(out / (name + '.transcript')), '-do', 'run -all; quit -f']
            assert meta['argv'] == expected_argv
    compiled = re.findall(r'-- Compiling module (\w+)', read(out / 'compile.log'))
    assert len(compiled) == 36 and set(compiled) == set(design['expected_modules'])
    assert 'Errors: 0, Warnings: 0' in read(out / 'compile.log')
    for name in ('control', 'key'):
        assert review_job(out, name, design) == result['completed'][name]
    for name, digest in design['project_sha256'].items():
        assert sha(out / 'inputs/project' / name) == digest, name
    for name, digest in design['vendor_sha256'].items():
        assert sha(out / 'inputs/vendor' / name.rsplit('/', 1)[-1]) == digest
    evidence = {p.relative_to(ROOT).as_posix(): sha(p) for p in out.rglob('*') if p.is_file() and
                'work' not in p.relative_to(out).parts}
    evidence[DESIGN.relative_to(ROOT).as_posix()] = sha(DESIGN)
    evidence.update(design['project_sha256'])
    gate = dict(status='WRITE_BUFFER_TURNOVER_RAW_EVIDENCE_REVIEW_PASS',
        input_manifest_sha256=sha(MANIFEST), completion_manifest_sha256=sha(DESIGN),
        evidence_sha256=evidence, CPU_changed=False, ISA_samples=[], board='NOT_RUN',
        original_design_check_preserved=True, key=result['completed']['key'],
        control=result['completed']['control'], controlled_cycles_saved=5)
    with gate_path.open('x', encoding='utf-8') as stream:
        json.dump(gate, stream, ensure_ascii=False, indent=2)
    print('RESULT: PASS Task031 raw evidence review; functional gate ready; board NOT_RUN')


if __name__ == '__main__':
    main()
