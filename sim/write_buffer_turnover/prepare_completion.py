"""Codex static completion preparation: observation copies and independent oracle only."""
import ast
import json
import re
from pathlib import Path
from check_inputs import ROOT, HERE, MANIFEST, require_inputs, sha
from completion_reference import build_reference, event_line

START = '    // CODEX_OBSERVATION_BEGIN\n'
END = '    // CODEX_OBSERVATION_END\n'


def insert_observation(code, needle, added):
    assert code.count(needle) == 1, needle
    return code.replace(needle, START + added + END + needle)


def remove_observation(code):
    return re.sub(r'^ *// CODEX_OBSERVATION_BEGIN\n.*?^ *// CODEX_OBSERVATION_END\n', '', code, flags=re.M | re.S)


def write_new(path, text):
    with Path(path).open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(text)


def main():
    original = require_inputs()
    old_manifest = HERE / 'simulation_inputs.json'
    old = json.loads(old_manifest.read_text())
    assert old['input_manifest_sha256'] == sha(MANIFEST)
    for name, digest in old['sha256'].items():
        assert sha(ROOT / name) == digest, name
    assert not (HERE / 'build/ds_write_buffer_turnover_20261014_a').exists()
    assert not (HERE / 'simulation_completion_inputs.json').exists()
    prep = HERE / 'build/completion_preparation_20261014_a'
    prep.mkdir(exist_ok=False)
    tb = (HERE / 'tb_write_buffer_turnover_x32.sv').read_text(encoding='utf-8')
    cases = (HERE / 'turnover_cases.svh').read_text(encoding='utf-8')
    new_tb = tb.replace('tb_write_buffer_turnover_x32', 'tb_write_buffer_turnover_completion', 1)
    new_tb = new_tb.replace('"turnover_cases.svh"', '"turnover_completion_cases.svh"', 1)
    declarations = '''    integer completion_ev_fd=0, completion_bus_fd=0;
    integer completion_ev_index=0, completion_cycle=0;
    bit completion_short_trace=0, completion_prev_reset=1, completion_prev_init=0;
    reg [31:0] completion_owned_addr=0;
    string completion_ev_path, completion_bus_path;
'''
    new_tb = insert_observation(new_tb, '    GTP_GRS GRS_INST', declarations)
    new_tb = insert_observation(new_tb, 'endmodule\n', '`include "turnover_completion_observe.svh"\n')
    new_cases = insert_observation(cases, '            prog_active=1;prog_cycles=0;',
                                  '            completion_short_trace=1;\n')
    new_cases = insert_observation(new_cases, '            $display("SHORT: cycles=',
                                  '            completion_short_trace=0;\n')
    irq_hook = '''                $fdisplay(completion_ev_fd,"EV %0d I %08h %08h %01h %0d %08h %08h %08h %08h",
                    completion_ev_index,soc.u_cpu.arch_next_pc,32'b0,cwe,
                    cwe ? crd : 5'b0,cwe ? cvalue : 32'b0,soc.u_cpu.irq_cause,32'b0,soc.u_cpu.csr_trap_target);
                completion_ev_index=completion_ev_index+1;
                $fflush(completion_ev_fd);
'''
    new_cases = insert_observation(new_cases, '                golden_mepc=golden_pc;golden_pc=golden_mtvec;', irq_hook)
    normal_hook = '''                $fdisplay(completion_ev_fd,"EV %0d %s %08h %08h %01h %0d %08h %08h %08h %08h",
                    completion_ev_index,soc.u_cpu.mret_commit ? "M" : "N",cpc,cinst,cwe,
                    cwe ? crd : 5'b0,cwe ? cvalue : 32'b0,32'b0,32'b0,
                    soc.u_cpu.mret_commit ? soc.u_cpu.csr_mret_target : soc.u_cpu.mem_wb_next_pc);
                completion_ev_index=completion_ev_index+1;
                $fflush(completion_ev_fd);
'''
    new_cases = insert_observation(new_cases, '                if(expected_we) golden_regs[rdn]=expected_value;', normal_hook)
    assert remove_observation(new_cases) == cases
    restored_tb = remove_observation(new_tb).replace('tb_write_buffer_turnover_completion', 'tb_write_buffer_turnover_x32', 1)
    restored_tb = restored_tb.replace('"turnover_completion_cases.svh"', '"turnover_cases.svh"', 1)
    assert restored_tb == tb
    observer = (HERE / 'turnover_completion_observe.svh').read_text()
    assert all(name.startswith('completion_') for name in re.findall(r'^\s*(\w+)\s*=(?!=)', observer, re.M))
    write_new(HERE / 'tb_write_buffer_turnover_completion.sv', new_tb)
    write_new(HERE / 'turnover_completion_cases.svh', new_cases)
    reference = build_reference(ROOT / old['cpu_image'])
    write_new(HERE / 'completion_reference.json', json.dumps(reference, indent=2) + '\n')
    write_new(HERE / 'completion_reference.trace', '\n'.join(event_line(event) for event in reference['events']) + '\n')
    new_files = ['check_inputs.py', 'prepare_completion.py', 'simulation_completion_runner.py',
                 'check_completion_evidence.py', 'review_completion.py', 'completion_reference.py',
                 'completion_reference.json', 'completion_reference.trace',
                 'tb_write_buffer_turnover_completion.sv', 'turnover_completion_cases.svh',
                 'turnover_completion_observe.svh', 'simulation_inputs.json']
    project = {**original['source_sha256'], **original['software_sha256'],
               **original['preparation_sha256'], **original['baseline_evidence_sha256'], **old['sha256']}
    project.update({(HERE / name).relative_to(ROOT).as_posix(): sha(HERE / name) for name in new_files})
    old_evidence = HERE / 'build/design_check_20261014_a'
    project.update({p.relative_to(ROOT).as_posix(): sha(p) for p in old_evidence.iterdir() if p.is_file()})
    for name, digest in project.items():
        assert sha(ROOT / name) == digest
        if name.endswith('.py'):
            ast.parse((ROOT / name).read_text(encoding='utf-8-sig'), filename=name)
    vendor = Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
    external = {(vendor / name).as_posix(): sha(vendor / name) for name in old['vendor_compile_sources']}
    ms = Path('D:/modelsim/win64pe')
    tools = {(ms / name).as_posix(): sha(ms / name) for name in ('vlib.exe', 'vlog.exe', 'vsim.exe')}
    sources = [name.replace('tb_write_buffer_turnover_x32.sv', 'tb_write_buffer_turnover_completion.sv') for name in old['compile_sources']]
    groups = [dict(name=name, checks=count) for name, count in zip(old['groups'], [10,7,6,407,12,7,10,430])]
    key_result = dict(tests=889,cpu_events=430,IRQ=1,OPPORTUNITIES=82,ACCEPTED=81,LATE=1,MLATE=0,
        EARLY=197,I_OVERLAP=454,OVERLAP=164,GATE=1,FENCE_WAIT=49,IRQ_WAIT=26,STOP_WAIT=26,
        UART=1,RAM=2,SOC_TURNOVER=69,fills=12,updates=203,cancelled=1)
    design = dict(status='WRITE_BUFFER_TURNOVER_COMPLETION_PREPARED_HDL_NOT_RUN',
        fixed_tag=old['fixed_tag'], input_manifest_sha256=sha(MANIFEST),
        original_design_sha256=sha(old_manifest), project_sha256=project,
        vendor_sha256=external, tool_sha256=tools, compile_sources=sources,
        expected_modules=[name.replace('tb_write_buffer_turnover_x32', 'tb_write_buffer_turnover_completion') for name in old['expected_modules']],
        module_count=36, groups=groups, key_result_fields=key_result,
        plusargs=old['plusargs'], cpu_image=old['cpu_image'],
        image_relative_to_here=Path(old['cpu_image']).relative_to('sim/write_buffer_turnover').as_posix(),
        observation_only_equivalence=True, CPU_changed=False, ISA_samples=[],
        timeouts=dict(vlib=60,compile=60,control=180,key=180),
        roles=dict(Codex='design, preparation and raw review', DeepSeek='simulation/test execution and report'))
    new_manifest = HERE / 'simulation_completion_inputs.json'
    write_new(new_manifest, json.dumps(design, ensure_ascii=False, indent=2) + '\n')
    receipt = dict(status='WRITE_BUFFER_TURNOVER_COMPLETION_STATIC_PREPARATION_PASS_HDL_NOT_RUN',
        input_manifest_sha256=sha(MANIFEST), completion_manifest_sha256=sha(new_manifest),
        original_design_sha256=sha(old_manifest), behavior_equivalence_without_observation=True,
        project_files=len(project), vendor_files=3, tools=3, modules=36, key_checks=889,
        reference_events=len(reference['events']), reference_requests=len(reference['requests']),
        CPU_sha256=sha(ROOT / 'myriscv/mycpu_sync.v'), bridge_sha256=sha(ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'),
        original_evidence_preserved=True, HDL='NOT_RUN', PDS='NOT_RUN', serial='NOT_OPENED',
        formal_directory_exists=False)
    write_new(prep / 'static_review.json', json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
