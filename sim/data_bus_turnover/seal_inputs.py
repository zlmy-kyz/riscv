"""Codex Task032 single-use sealing; no HDL/PDS/serial calls."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'sim/write_buffer_turnover'))
from check_include_dependencies import check_includes


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    assert not (HERE / 'inputs.json').exists()
    prior_path = ROOT / 'sim/write_buffer_turnover/simulation_timing_repair_inputs.json'
    prior = json.loads(prior_path.read_text(encoding='utf-8'))
    changed = [n for n, d in prior['project_sha256'].items() if sha(ROOT / n) != d]
    assert changed == ['myriscv/data_bus_interconnect.v'], changed
    initial = json.loads((ROOT / 'sim/write_buffer_turnover/inputs.json').read_text(encoding='utf-8'))
    names = set(initial['source_sha256']) | set(initial['software_sha256'])
    names.update(p.relative_to(ROOT).as_posix() for p in HERE.iterdir() if p.is_file() and p.suffix in ('.py','.sv','.svh','.dat','.json','.trace'))
    names.update(['sim/mini_board_migration/ddr_model_x32.v',
        'sim/write_buffer_turnover/check_inputs.py', 'sim/write_buffer_turnover/check_include_dependencies.py',
        'sim/write_buffer_turnover/simulation_completion_runner.py', 'sim/write_buffer_turnover/check_completion_evidence.py',
        'sim/write_buffer_turnover/completion_reference.py'])
    compile_sources = prior['compile_sources'][:-1] + [
        'sim/mini_board_migration/ddr_model_x32.v', 'sim/data_bus_turnover/tb_data_bus_turnover.sv']
    includes = check_includes(ROOT, compile_sources)
    names.update(includes.values())
    expected = prior['expected_modules'][:-1] + ['mini_ddr_model_x32','tb_data_bus_turnover','data_turnover_unit']
    assert len(expected) == 38 and len(includes) == 5
    gate_path = ROOT / 'sim/write_buffer_turnover/build/ds_write_buffer_turnover_timing_repair_20261014_a/codex_review.json'
    gate = json.loads(gate_path.read_text(encoding='utf-8'))
    protected = {n:d for n,d in gate['evidence_sha256'].items() if n.startswith('sim/write_buffer_turnover/build/')}
    for p in [prior_path,gate_path,ROOT/'sim/write_buffer_turnover/inputs.json',
        *[ROOT / ('sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_timing_300_01/' + name)
          for name in ('performance_300.json','validation_300.json','codex_review_20261014/result.json')]]:
        protected[p.relative_to(ROOT).as_posix()] = sha(p)
    for p in (HERE / 'build/preparation_20261014_a/before').rglob('*'):
        if p.is_file():
            protected[p.relative_to(ROOT).as_posix()] = sha(p)
    for name,digest in protected.items():
        assert sha(ROOT / name) == digest, name
    data = dict(status='TASK032_DATA_BUS_RESPONSE_TURNOVER_PREPARED_HDL_NOT_RUN',
        tag='ds_data_bus_response_turnover_20261014_a',
        project_sha256={n:sha(ROOT/n) for n in sorted(names)},vendor_sha256=prior['vendor_sha256'],tool_sha256=prior['tool_sha256'],
        compile_sources=compile_sources,expected_modules=expected,include_dependencies=includes,
        protected_evidence_sha256=protected,prior_031_manifest_sha256=sha(prior_path),
        changed_design_files=changed,CPU_changed=False,ISA_samples=[],timeouts=dict(vlib=60,compile=60,control=180,key=180),
        control_rationale='New stimulus/reference cannot reuse an old execution; same RTL feature off is the only relevant control',
        baseline='sim/write_buffer_turnover/board/coremark_i64_d64_zmmul_wturn_timing_300_01',
        baseline_P_seconds=2.251881472,baseline_V_seconds=2.2481371946666666,
        reference_events=82,reference_requests=49,unit_cases=68,unit_control_cycles=64,unit_key_cycles=33,
        board='NOT_RUN',PDS='NOT_RUN',serial='NOT_OPENED',roles=dict(Codex='design/seal/review',DeepSeek='execute/report',user='PDS/physical board'))
    with (HERE / 'inputs.json').open('x',encoding='utf-8') as f:
        json.dump(data,f,ensure_ascii=False,indent=2);f.write('\n')
    print(json.dumps(dict(status=data['status'],manifest_sha256=sha(HERE/'inputs.json'),
        project_inputs=len(names),vendor_inputs=3,tools=3,includes=len(includes),protected=len(protected)),indent=2))


if __name__ == '__main__':
    main()
