"""Freeze Task031's single RTL change and evidence references; no HDL execution."""
import ast
import difflib
import json
from pathlib import Path
from check_inputs import ROOT, HERE, MANIFEST, sha

PREP = HERE / 'build/preparation_20261014_a'
BRIDGE = 'myriscv/dual_sram_to_pango_ddr_bridge.v'


def write_new(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        stream.write(value)


def main():
    before = (PREP / 'bridge_before.v').read_text(encoding='utf-8')
    after = (ROOT / BRIDGE).read_text(encoding='utf-8')
    assert sha(PREP / 'bridge_before.v') == '355145f2fca4c08cac12525f7ab16a2faae7466953baf49fc021c7bce413d7aa'
    # Exact scoped edit, including comments; no other FSM, cache or data changes.
    replacements = [
        ('//   * posted 模式 store 入缓冲即响应；下一写与读 miss 等排空。',
         '//   * posted 模式 store 入缓冲即响应；下一写可在旧写完成边沿接续，读 miss 等排空。'),
        ('    parameter integer DATA_STORE_FORWARD_ENABLE = 1\n',
         '    parameter integer DATA_STORE_FORWARD_ENABLE = 1,\n'
         '    // Reuse the sole posted entry on its W completion edge; no extra queue slot.\n'
         '    parameter integer WRITE_BUFFER_TURNOVER_ENABLE = 1\n'),
        ('    wire write_buffer_complete;\n',
         '    wire write_buffer_complete;\n    wire write_buffer_turnover_ready;\n'),
        ('    assign data_req_ready = idle_ready && (!write_buffer_busy ||\n',
         '    // Only stores reuse a completing entry. Loads keep the existing DRM collision guard.\n'
         '    // Completion depends on the OLD AW/W fields, never on the incoming store.\n'
         '    assign write_buffer_turnover_ready = (WRITE_BUFFER_TURNOVER_ENABLE != 0) &&\n'
         '                                        data_req_write && write_buffer_complete;\n'
         '    assign data_req_ready = idle_ready && (!write_buffer_busy ||\n'
         '                             write_buffer_turnover_ready ||\n'),
        ('            if (write_buffer_push) begin\n',
         '            // Push wins over completion: old data updates D RAM at this edge,\n'
         '            // then the new entry owns AW/W and must obtain its own AW acceptance.\n'
         '            if (write_buffer_push) begin\n'),
    ]
    expected = before
    for old, new in replacements:
        assert expected.count(old) == 1
        expected = expected.replace(old, new)
    assert after == expected, 'Unexpected bridge change'
    old_gate = json.loads((ROOT / 'sim/cpu_branch_turnover/build/ds_cpu_branch_isa_port_resume_20261014_a/codex_review.json').read_text())
    sources = {}
    for name, digest in old_gate['source_sha256'].items():
        if Path(name).suffix not in ('.v', '.vp', '.vh', '.idf'):
            continue
        current = sha(ROOT / name)
        assert name == BRIDGE or current == digest, name
        sources[name] = current
    software = old_gate['software_sha256']
    for name, digest in software.items():
        assert sha(ROOT / name) == digest, name
    baseline_dir = ROOT / 'sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01'
    baseline_files = [baseline_dir / 'performance_300.json', baseline_dir / 'validation_300.json',
                      baseline_dir / 'codex_review_20261014/result.json']
    baseline = {p.relative_to(ROOT).as_posix(): sha(p) for p in baseline_files}
    prior = json.loads(baseline_files[-1].read_text())
    counters = {name: row['current']['counters'] for name, row in prior['modes'].items()}
    write_new(PREP / 'bridge.patch', ''.join(difflib.unified_diff(before.splitlines(True), after.splitlines(True),
              fromfile='bridge_before.v', tofile=BRIDGE)))
    write_new(PREP / 'baseline_counters.json', json.dumps(counters, indent=2) + '\n')
    prepared = [HERE / 'check_inputs.py', HERE / 'prepare.py',
                ROOT / 'tools/uart_loader/candidates/perf_2b/run_write_buffer_turnover_measurement.py',
                ROOT / 'tools/uart_loader/candidates/perf_2b/run_write_buffer_turnover_measurements.ps1']
    # Freeze the reused transport too, without inspecting a PDS or bitstream.
    prepared += [p for p in (ROOT / 'tools/uart_loader/candidates/perf_2b').glob('*.py') if p not in prepared]
    prepared += [ROOT / 'tests/cpu_performance_2b/zmmul300_software.py']
    prepared += list(PREP.iterdir())
    for path in prepared:
        if path.suffix == '.py':
            ast.parse(path.read_text(encoding='utf-8-sig'), filename=str(path))
    manifest = dict(status='WRITE_BUFFER_TURNOVER_PREPARED_HDL_NOT_RUN',
        fixed_tag='ds_write_buffer_turnover_20261014_a', CPU_changed=False, ISA_samples=[],
        source_sha256=sources, software_sha256=software,
        preparation_sha256={p.relative_to(ROOT).as_posix(): sha(p) for p in prepared},
        baseline_evidence_sha256=baseline,
        DeepSeek_owns='simulation design, execution, result analysis',
        Codex_owns='RTL, task and stage documentation, raw evidence review')
    write_new(MANIFEST, json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    review = dict(status='WRITE_BUFFER_TURNOVER_STATIC_PREPARATION_PASS_HDL_NOT_RUN',
        input_manifest_sha256=sha(MANIFEST), bridge_before_sha256=sha(PREP / 'bridge_before.v'),
        bridge_after_sha256=sha(ROOT / BRIDGE), CPU_sha256=sha(ROOT / 'myriscv/mycpu_sync.v'),
        exact_scoped_edit=True, unchanged_other_registered_sources=len(sources)-1,
        frozen_software_files=len(software), HDL='NOT_RUN', board='NOT_RUN', PDS='NOT_RUN',
        simulation_design='DELEGATED_TO_DEEPSEEK_NOT_YET_DELIVERED')
    write_new(PREP / 'static_review.json', json.dumps(review, indent=2) + '\n')
    print(json.dumps(review, indent=2))


if __name__ == '__main__':
    main()
