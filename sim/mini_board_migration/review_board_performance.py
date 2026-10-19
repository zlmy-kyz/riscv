"""Audit existing MINI serial/PDS evidence; never simulate, implement or open UART."""
from pathlib import Path
import argparse
import csv
import hashlib
import importlib.util
import json
import re
import shutil

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    assert not args.output.exists(), 'Preserve existing evidence'
    spec = importlib.util.spec_from_file_location('mini_measurement_review',
        ROOT / 'tools/uart_loader/candidates/perf_2b/run_measurement.py')
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)  # Defines parsers; no main/execute/serial calls.
    current_bit = ROOT / 'generate_bitstream/board_top.sbit'
    old_bit = ROOT / 'generate_bitstream/bak/board_top.sbit'
    assert sha(current_bit) == '5aea57d52a65cf9a79f599bc9a1a2d33231bebead895c9aedefd2609a56bd62a'
    assert sha(old_bit) == 'a83ba41bbc25569b9d2fa115df22ab0ce33504c7d2e4c4daba62a15ce04b5e25'
    sources = set()
    cases = {}
    rows = []
    directories = {
        'mini': ROOT / 'sim/mini_board_migration/board/coremark_01',
        'old_D4': ROOT / 'sim/inst_line_buffer/board/measure_20261011_163128_455',
        'old_D4_prior': ROOT / 'sim/inst_line_buffer/board/measure_20261011_162927_851',
        'old_D1': ROOT / 'sim/inst_line_buffer/board/measure_20261011_155529_327',
    }
    for name in tool.FORMAL_APPLICATIONS:
        raw = {label: read(folder / (name + '.json')) for label, folder in directories.items()}
        checked = {label: tool.verify_record(record) for label, record in raw.items()}
        assert all(record['application_info'] == raw['mini']['application_info'] for record in raw.values())
        assert all(record['manifest_sha256'] == raw['mini']['manifest_sha256'] for record in raw.values())
        assert all(x['responses'] == 129 and x['run_count'] == 1 for x in checked.values())
        assert raw['mini']['port'] == 'COM9'
        assert raw['mini']['bitstream_local_file']['sha256'] == sha(current_bit)
        assert all(raw[k]['bitstream_local_file']['sha256'] == sha(old_bit) for k in ['old_D4', 'old_D4_prior'])
        apps = {label: x['application'] for label, x in checked.items()}
        nc = apps['mini']['counters']
        assert apps['mini']['iterations'] == 120 and not apps['mini']['formal_benchmark']
        comparisons = {}
        for label in ['old_D4', 'old_D4_prior', 'old_D1']:
            bc = apps[label]['counters']
            assert all(nc[k] == bc[k] for k in ['instret', 'branch_redirects', 'ddr_aw_commands'])
            delta = {k: dict(before=bc[k], after=nc[k], delta=nc[k]-bc[k],
                     change_percent=(nc[k]/bc[k]-1)*100 if bc[k] else None) for k in tool.NAMES}
            assert bc['cycles']-nc['cycles'] == sum(bc[k]-nc[k] for k in tool.NAMES[2:9])
            comparisons[label] = dict(time_reduction_percent=(1-nc['cycles']/bc['cycles'])*100,
                throughput_increase_percent=(bc['cycles']/nc['cycles']-1)*100, counter_delta=delta)
            for k, d in delta.items():
                rows.append([name, label, k, d['before'], d['after'], d['delta'], d['change_percent']])
        cases[name] = dict(logs_verified=checked, comparisons=comparisons,
            new_cycle_shares_percent={k: nc[k]*100/nc['cycles'] for k in tool.NAMES[2:9]},
            new_cpi_components={k: nc[k]/nc['instret'] for k in tool.NAMES[2:9]})
        sources.update(folder / (name + '.json') for folder in directories.values())
        info = raw['mini']['application_info']
        sources.update([tool.manifest_for(name), ROOT / info['bin_path'], ROOT / info['elf_path']])
        sources.add(tool.manifest_for(name).parent / 'reference.txt')
    hello_path = ROOT / 'sim/mini_board_migration/board/hello_01.json'
    hello = tool.verify(hello_path)
    assert hello['responses'] == 23 and hello['run_count'] == 1
    assert hello['bitstream_local_file']['sha256'] == sha(current_bit)
    sources.add(hello_path)
    hi = read(hello_path)['application_info']
    sources.update([tool.manifest_for('hello'), ROOT / hi['bin_path'], ROOT / hi['elf_path']])

    timing_path = ROOT / 'report_timing/board_top.rtr'
    timing = timing_path.read_text()
    assert all(t in timing for t in ['Device       : PG2L200H', 'Package      : FBB676',
        'Timing Models: Pre-silicon', 'Design Summary : All Constraints Met.'])
    sections = re.split(r'(?m)^((?:Setup|Hold|Recovery|Removal|Minimum Pulse Width) Summary\((?:Slow|Fast) Corner\):)', timing)[1:]
    assert len(sections) == 20
    summaries = {}
    for title, body in zip(sections[::2], sections[1::2]):
        parsed = []
        for line in body.split('====')[0].splitlines():
            tokens = line.split()
            if len(tokens) in [5, 6] and re.fullmatch(r'[-+]?\d+\.\d+', tokens[-4]):
                assert int(tokens[-2]) == 0 and float(tokens[-3]) == 0 and float(tokens[-4]) >= 0
                parsed.append(tokens)
        assert parsed
        summaries[title] = dict(rows=parsed, failing_endpoints=0, minimum_slack_ns=min(float(p[-4]) for p in parsed))
    core = {}
    for label in ['Setup Summary(Slow Corner):', 'Setup Summary(Fast Corner):',
                  'Hold Summary(Slow Corner):', 'Hold Summary(Fast Corner):']:
        row = next(p for p in summaries[label]['rows'] if p[:2] == ['ddrphy_sysclk', 'ddrphy_sysclk'])
        core[label] = float(row[-4])
    assert list(core.values()) == [.724, 4.760, .137, .102]
    critical = next(b for b in re.split(r'(?m)(?=^Startpoint)', timing)
                    if 'Path Group  : ddrphy_sysclk' in b and 'Path Type   : max (slow corner)' in b)
    critical_excerpt = '\n'.join(l for l in critical.splitlines() if re.search(
        r'^(Startpoint|Endpoint|Path Group|Path Type)|Logic Levels:|Logic:|Slack \(MET\)', l))
    assert 'u_cpu/id_ex_src1[26]' in critical_excerpt and 'u_uart_mmio/u_tx/state_reg[3]' in critical_excerpt
    assert '0.724' in critical_excerpt
    assert 'Reading design from pnr DB.' in (ROOT / 'report_timing/run.log').read_text()
    assert sha(ROOT / 'place_route/board_top_pnr.adf') == sha(ROOT / 'place_route/seed_5/board_top_pnr.adf')
    seeds = (ROOT / 'place_route/multiseed_result.csv').read_text()
    assert 'Best Slack Seed:5' in seeds
    netlist = (ROOT / 'synthesize/board_top_syn.vm').read_text()
    assert re.findall(r'wire \[255:0\] \\inst_line_data\[(\d+)\]', netlist) == list(map(str, range(8)))
    assert re.findall(r'wire \[255:0\] \\data_line_data\[(\d+)\]', netlist) == list(map(str, range(4)))
    assert 'wait_count' not in netlist
    prr = (ROOT / 'place_route/board_top.prr').read_text()
    utilization = prr.split('Device Utilization Summary :', 1)[1].split('Device Utilization Summary Of Each Module:', 1)[0]
    ff = [int(x) for x in re.findall(r'\|\s+FF\s+\|\s+(\d+)', utilization)]
    lut = [int(x) for x in re.findall(r'\|\s+LUT\s+\|\s+(\d+)', utilization)]
    assert ff == [9583, 3643] and lut == [7915, 2816]
    hierarchy = next(line for line in prr.splitlines() if re.match(r'\| board_top\s+\|', line))
    assert [int(x.strip()) for x in hierarchy.split('|')[2:4]] == [10069, 13226]
    pds = (ROOT / 'RISCV.pds').read_text()
    paths = sorted(set(re.findall(r'"([^"\n]+\.(?:v|vp|idf|fdc|sdc))"', pds, re.I)))
    assert len(paths) == 124 and all((ROOT / p).exists() for p in paths)
    sources.update(ROOT / p for p in paths)
    simulation_inputs_path = ROOT / 'sim/mini_board_migration/build/mini200h_preboard_20261011_d/inputs.json'
    for name, digest in read(simulation_inputs_path).items():
        assert sha(ROOT / name) == digest, 'Preboard simulation input changed: ' + name
    sources.add(simulation_inputs_path)
    loader_rom = ROOT / 'tests/uart_loader/candidates/verify_run_hello/build/loader_rom.dat'
    loader_ram = ROOT / 'tests/uart_loader/candidates/verify_run_hello/build/loader_ram.dat'
    assert sha(loader_rom) == '53a2d9912e85b6b5c90768fb0422be6cde8d5bdab37ef07b7eabfb065b76cea1'
    assert sha(loader_ram) == '986cda2d60cc4d4d97bf71b6bcc90c938126b241ef1656c3275c41b0999f2975'
    sources.update([loader_rom, loader_ram])
    sources.update(ROOT / n for n in ['RISCV.pds', 'ipcore/ddr3/pnr/ddr_test.fdc',
        'synthesize/board_top.snr', 'synthesize/run.log', 'place_route/board_top.prr',
        'place_route/run.log', 'place_route/board_top_pnr.adf', 'place_route/multiseed_result.csv',
        'report_timing/board_top.rtr', 'report_timing/run.log', 'generate_bitstream/board_top.bgr',
        'generate_bitstream/run.log', 'tools/uart_loader/candidates/perf_2b/run_measurement.py',
        'tools/uart_loader/candidates/bsp_workflow/application.py',
        'tools/uart_loader/candidates/bsp_workflow/plan.py',
        'tools/uart_loader/candidates/bsp_workflow/upload.py',
        'tests/cpu_performance_2b/measurement_software.py'])
    sources.update([current_bit, old_bit, Path(__file__).resolve()])
    inputs = {p.relative_to(ROOT).as_posix(): dict(sha256=sha(p), bytes=p.stat().st_size,
              mtime_ns=p.stat().st_mtime_ns) for p in sorted(sources)}
    args.output.mkdir(parents=True)
    for p in sorted(sources):
        dest = args.output / 'frozen_evidence' / p.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(p, dest)
        assert sha(dest) == inputs[p.relative_to(ROOT).as_posix()]['sha256']
    assert all(sha(ROOT / p) == data['sha256'] for p, data in inputs.items())
    result = dict(status='MINI200H_ACTUAL_DDR_FIXED120_EVIDENCE_AUDIT_PASS', date='2026-10-12',
        hello=hello, cases=cases, bitstream_sha256=sha(current_bit), input_identity=inputs,
        frozen_evidence_count=len(inputs), timing_report_all_constraints_met=True,
        timing_models='Pre-silicon', core_clock_hz=93750000, timing_summaries=summaries,
        core_clock_slack_ns=core, selected_seed=5, selected_pnr_sha256_matches=True,
        critical_core_setup_path=critical_excerpt,
        resources=dict(FF_physical=13226, LUT_physical=10731, LUT_hierarchy=10069, DRM=8, Distributed_RAM=44),
        cache=dict(I_rows=8, D_rows=4, line_bytes=32, I_bytes=256, D_bytes=128),
        all_current_modes_formal=False, serial_opened_by_review=False,
        pds_started_by_review=False, simulation_started_by_review=False,
        limitations=['Cross-board change includes device/IP/DDR bus width and cache line capacity; no isolated attribution',
            'Current board one run per mode; no repeated-run variance estimate',
            'AR combines IF and data; no dynamic miss/conflict/read-write stall split',
            'Branch recovery includes target-fetch wait; not a BTB gain estimate',
            'PDS model Pre-silicon and unconstrained IO scope retained',
            'Local bitstream identified; FPGA programming not independently observed',
            'IDF/DAT verified; programmed memory INIT not independently decoded'])
    (args.output / 'review_result.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    with (args.output / 'counter_comparisons.csv').open('w', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(['application', 'baseline', 'counter', 'before', 'after', 'delta', 'change_percent'])
        writer.writerows(rows)
    print(result['status'], 'frozen_evidence_count=', len(inputs))
    for name, case in cases.items():
        print(name, json.dumps(case['comparisons']['old_D4'], ensure_ascii=True)[:180])


if __name__ == '__main__':
    main()
