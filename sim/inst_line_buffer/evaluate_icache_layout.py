"""Static instruction-address inventory; no RTL or instruction simulation."""
import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
SOFTWARE = ROOT / 'tests/cpu_performance_2b/build/measure_20261011_120'
SELECTED = ('core_list_mergesort', 'core_bench_list', 'matrix_mul_matrix',
            'matrix_mul_matrix_bitextract', 'core_state_transition',
            'crcu8', 'crcu16', '__mulsi3')
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()


def inventory(path):
    functions = {}
    current = None
    for line in path.read_text(encoding='utf-8').splitlines():
        match = re.fullmatch(r'([0-9a-f]+) <([^>]+)>:', line)
        if match:
            current = match[2]
            functions[current] = []
        match = re.match(r'^([0-9a-f]+):\s+([0-9a-f]{8})\s+(\S+)\s*(.*)', line)
        if match and current:
            functions[current].append((int(match[1], 16), match[3], match[4]))
    rows, edges = [], []
    for name in SELECTED:
        ins = functions[name]
        start, end = ins[0][0], ins[-1][0] + 4
        line_count = (end - 1) // 16 - start // 16 + 1
        rows.append(dict(function=name, start=f'{start:08x}',
                         end_exclusive=f'{end:08x}', bytes=end-start,
                         address_span_lines=line_count,
                         first_index_4=(start >> 4) % 4,
                         first_index_8=(start >> 4) % 8,
                         first_index_16=(start >> 4) % 16))
        for pc, op, args in ins:
            if not (op.startswith('b') or op == 'j'):
                continue
            target = re.search(r'\b([0-9a-f]{8}) <', args)
            if target and start <= int(target[1], 16) <= pc:
                target_pc = int(target[1], 16)
                span = pc // 16 - target_pc // 16 + 1
                edges.append(dict(function=name, branch_pc=f'{pc:08x}',
                                  target_pc=f'{target_pc:08x}',
                                  contiguous_address_span_lines=span))
    return rows, edges


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve previous evidence; use a fresh output'
    paths = [Path(__file__), ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v',
             ROOT / 'myriscv/uart_mmio.v', ROOT / 'myriscv/mycpu_sync.v',
             ROOT / 'report_timing/board_top.rtr',
             ROOT / 'sim/uart_mmio/build/review_wait_chain_pds_20261011_a/review_result.json',
             ROOT / 'sim/inst_line_buffer/build/compare_data_read_20261011_a/comparison.json']
    for mode in ('performance_120', 'validation_120'):
        paths += [SOFTWARE / mode / name for name in
                  ('program.dis', 'program.bin', 'program.elf', 'manifest.json')]
    inputs = {str(p.relative_to(ROOT)): sha(p) for p in paths}
    modes = {}
    for mode in ('performance_120', 'validation_120'):
        rows, edges = inventory(SOFTWARE / mode / 'program.dis')
        modes[mode] = dict(functions=rows, backward_edges=edges)
    # This union describes address ranges, not a dynamically observed working set.
    loop_lines = set(range(0x40002934 >> 4, (0x40002964 >> 4) + 1))
    helper_lines = set(range(0x40003310 >> 4, (0x40003330 >> 4) + 1))
    overlap = {}
    for n in (4, 8, 16):
        overlap[str(n)] = sorted({a % n for a in loop_lines} &
                                {a % n for a in helper_lines})
    timing = json.loads(paths[5].read_text(encoding='utf-8'))
    assert timing['status'] == 'UART_WAIT_CHAIN_POST_PNR_TIMING_AUDIT_PASS'
    comparison = json.loads(paths[6].read_text(encoding='utf-8'))
    assert comparison['status'] == 'DATA_READ_BUFFER_SAME_BIN_BOARD_COMPARISON_PASS'
    result = dict(status='ICACHE_CAPACITY_STATIC_EVALUATION_NOT_SIMULATED',
                  modes=modes, line_bytes=16,
                  candidate_state_bits_full_28_bit_tags={str(n): n * 157 for n in (4, 8, 16)},
                  illustrative_matrix_loop_lines=[f'{a << 4:08x}' for a in sorted(loop_lines)],
                  illustrative_multiply_lines=[f'{a << 4:08x}' for a in sorted(helper_lines)],
                  illustrative_overlapping_indices=overlap,
                  current_slow_setup_WNS_ns=timing['slow_setup_WNS_ns'],
                  current_cycle_shares_percent={k: v['cycle_shares_percent']
                                                for k, v in comparison['cases'].items()},
                  input_sha256=inputs, RTL_modified=False, software_rebuilt=False,
                  simulation_started=False, pds_started=False, serial_opened=False,
                  dynamic_hit_rate_measured=False, new_capacity_timing_measured=False,
                  limitations=['Address spans do not measure execution frequencies',
                               'Backward edges are syntactic spans, not traced loop footprints',
                               'Index overlap alone does not establish a dynamic conflict miss'])
    args.output.mkdir(parents=True)
    for path in paths:
        target = args.output / 'inputs' / path.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(path, target)
        assert sha(target) == inputs[str(path.relative_to(ROOT))]
        assert sha(path) == inputs[str(path.relative_to(ROOT))]
    (args.output / 'evaluation.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    for mode, data in modes.items():
        for key in ('functions', 'backward_edges'):
            with (args.output / (mode + '_' + key + '.csv')).open('w', encoding='utf-8', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=list(data[key][0]))
                writer.writeheader()
                writer.writerows(data[key])
    print(result['status'])
    print('matrix / multiply overlapping indices:', overlap)
    for row in modes['performance_120']['functions']:
        print(row)


if __name__ == '__main__':
    main()
