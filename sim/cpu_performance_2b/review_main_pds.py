"""Read-only audit of user-generated main PDS artifacts; never invokes PDS."""
from pathlib import Path
import argparse
import hashlib
import importlib.util
import json
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
read = lambda p: json.loads(p.read_text(encoding='utf-8'))


def memories(path):
    text = path.read_text()
    heads = list(re.finditer(r'(?:GTP|V)_DRM36K_E1\s*/\*\s*(.*?)\s*\*/\s*#\(', text))
    result = {}
    for i, head in enumerate(heads):
        where = re.search(r'ADDR_LOOP\[(\d+)\]\.DATA_LOOP\[(\d+)\]', head[1])
        if not where:
            continue
        # Stop at this cell's parameter-list close. Scanning until the next
        # DRM can accidentally include later distributed-RAM INIT parameters.
        depth = 1
        end = head.end()
        while depth:
            if text[end] == '(':
                depth += 1
            elif text[end] == ')':
                depth -= 1
            end += 1
        body = text[head.end():end - 1]
        blocks = {int(n, 16): (int(width), int(value, 2 if radix.lower() == 'b' else 16))
                  for n, width, radix, value in re.findall(
                      r"\.INIT_([0-9A-F]+)\(\s*(\d+)\s*'([bh])([0-9a-fA-F]+)\s*\)", body)}
        assert len(blocks) == 128, (path, head[1], len(blocks))
        config = {n: re.search(r'\.' + n + r'\(([^)]+)\)', body)[1].strip()
                  for n in ('RAM_MODE', 'DATA_WIDTH_A', 'DATA_WIDTH_B', 'RAM_CASCADE', 'DOA_REG', 'DOB_REG')}
        kind = 'inst_rom' if config['RAM_MODE'] == '"ROM"' else 'data_ram'
        key = (kind, int(where[1]), int(where[2]))
        assert key not in result, key
        result[key] = dict(blocks=blocks, config=config)
    assert len(result) == 8, (path, len(result))
    return result


def check_implementation(synthesized, implemented, reference):
    assert set(implemented) == set(synthesized) == set(reference)
    for key in implemented:
        assert implemented[key]['blocks'] == synthesized[key]['blocks'], ('Implementation INIT', key)
        # The Pango exported simulation model represents mapped SINGLE_PORT
        # data RAM as TRUE_DUAL_PORT. Compare model configs with the verified
        # export, while checking every current INIT bit against synthesis.
        assert implemented[key]['config'] == reference[key]['config'], ('Implementation config', key)


def audit(report):
    baseline_path = ROOT / 'sim/cpu_performance_2b/build/main_integration_20261010_a.json'
    baseline = read(baseline_path)
    assert baseline['status'] == 'PERF2B_MAIN_RTL_INTEGRATION_REGRESSION_PASS'
    changed = []
    for relative, digest in baseline['protected_current'].items():
        if sha(ROOT / relative) != digest:
            changed.append(relative)
    assert set(changed) <= {'RISCV.pds', 'generate_bitstream/board_top.sbit'}, changed
    for relative, digest in baseline['transferred_rtl_sha256'].items():
        assert sha(ROOT / relative) == digest, relative
    for field in ('suites', 'source_receipts'):
        for row in baseline[field].values():
            assert sha(ROOT / row['path']) == row['sha256'], row['path']
    compiled_count = 0
    for path in (ROOT / 'sim/cpu_performance_2b/build/main_coremark_20261010_a').rglob('source_snapshot/sha256.json'):
        for relative, digest in read(path).items():
            assert sha(ROOT / relative) == digest, relative
            compiled_count += 1
    assert compiled_count > 0
    report['functional_baseline'] = dict(status='PASS_REUSED_UNCHANGED_INPUTS',
        receipt=baseline_path.relative_to(ROOT).as_posix(), suites=baseline['suites'],
        compiled_sources_verified=compiled_count, intentionally_changed_protected_inputs=changed,
        no_new_simulation_executed=True)

    historical = read(ROOT / 'sim/cpu_performance_2b/build/deployment_gate.json')
    for relative, digest in historical['input_sha256'].items():
        assert sha(ROOT / 'sim/cpu_performance_2b/build/frozen_inputs' / relative) == digest, relative
    for relative, digest in historical['evidence_sha256'].items():
        assert sha(ROOT / relative) == digest, relative
    report['historical_evidence'] = dict(frozen_input_copies=len(historical['input_sha256']),
                                       evidence_files=len(historical['evidence_sha256']))

    timing_path = ROOT / 'report_timing/board_top.rtr'
    timing = timing_path.read_text()
    assert 'Design Summary : All Constraints Met.' in timing
    assert 'Slack (VIOLATED)' not in timing
    assert all(s in timing for s in ('PG2L100H', 'FBG484', 'Speed Grade  : -6'))
    match = re.search(r'ddrphy_sysclk\s+93\.7500 MHz\s+([\d.]+) MHz\s+10\.6667\s+([\d.]+)\s+([\d.-]+)', timing)
    assert match and float(match[3]) >= 0
    report['timing'] = dict(core_clock_mhz=93.75, estimated_clock_mhz=float(match[1]),
                            slow_setup_slack_ns=float(match[3]), existing_constraints='ALL_MET',
                            scope='Existing constraints only; unconstrained physical I/O warnings remain')
    rows = {}
    for corner in ('Slow', 'Fast'):
        table = timing.split(f'Hold Summary({corner} Corner):', 1)[1].split('Recovery Summary', 1)[0]
        row = re.search(r'ddrphy_sysclk\s+ddrphy_sysclk\s+([\d.-]+)\s+([\d.-]+)\s+(\d+)', table)
        assert row and float(row[1]) >= 0 and int(row[3]) == 0
        rows[corner.lower() + '_hold_slack_ns'] = float(row[1])
    report['timing'].update(rows)
    prr = (ROOT / 'place_route/board_top.prr').read_text()
    total = re.search(r'\|\s*board_top\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)', prr)
    assert total
    report['resources'] = dict(zip(('LUT', 'FF', 'distributed_RAM', 'APM', 'DRM'), map(int, total.groups())))
    seed_text = (ROOT / 'place_route/multiseed_result.csv').read_text()
    assert 'Best Slack Seed:5' in seed_text
    report['best_seed'] = 5
    report['flow_logs'] = {}
    for directory in ('compile', 'synthesize', 'device_map', 'place_route', 'report_timing', 'generate_bitstream'):
        path = ROOT / directory / 'run.log'
        text = path.read_text(errors='replace')
        errors = re.findall(r'^(?:E:|ERROR:|\*\* Error).*', text, re.M)
        assert not errors, (directory, errors)
        report['flow_logs'][directory] = dict(errors=errors, warnings=len(re.findall(r'^W:', text, re.M)))
    compile_log = (ROOT / 'compile/run.log').read_text()
    for n in ('mycpu_sync', 'soc_top', 'simple_mmio'):
        assert f'Analyzing file D:/riscv/RISCV/myriscv/{n}.v' in compile_log
        assert (ROOT / f'myriscv/{n}.v').stat().st_mtime < (ROOT / 'compile/run.log').stat().st_mtime
    assert 'myriscv/candidates/perf_2b' not in compile_log
    parameters = compile_log.split('board_top/u_soc/u_soc/u_simple_mmio/g_perf.u_perf} parameter value:', 1)[1][:260]
    for name, value in (('AUTO_ARM', 1), ('DEFAULT_START_PC', 0x400007d0), ('DEFAULT_STOP_PC', 0x400007f4)):
        assert int(re.search(name + r" = 32'b([01]+)", parameters)[1], 2) == value
    report['compiled_counter_parameters'] = dict(auto_arm=1, start_pc='0x400007d0', stop_pc='0x400007f4')

    synthesized = memories(ROOT / 'synthesize/board_top_syn.vm')
    initializations = {}
    for name, kind, width, address_bits, lanes, banks in (
            ('inst_rom', 'rom', 8, 12, 4, 1), ('data_ram', 'ram', 16, 11, 2, 2)):
        dat = ROOT / f'tests/uart_loader/candidates/verify_run_hello/build/loader_{kind}.dat'
        values = [int(s, 16) for s in dat.read_text().split()]
        assert len(values) == 4096
        init = ROOT / f'ipcore/{name}/rtl/{name}_init_param.v'
        params = {(int(index, 16), int(bank), int(lane)): int(value, 16)
                  for index, bank, lane, value in re.findall(
                      r"localparam INIT_([0-9A-F]+)_([0-9]+)_([0-9]+) = 288'h([0-9a-f]+);", init.read_text())}
        assert len(params) == 128 * lanes * banks
        reconstructed = []
        bytes_per_lane = width // 8
        steps = 288 // (9 * bytes_per_lane)
        for i in range(4096):
            bank, offset = divmod(i, 1 << address_bits)
            word = 0
            for lane in range(lanes):
                raw = params[(offset // steps, bank, lane)] >> (9 * bytes_per_lane * (offset % steps))
                part = sum(((raw >> (9 * byte)) & 255) << (8 * byte) for byte in range(bytes_per_lane))
                word |= part << (width * lane)
            reconstructed.append(word)
        assert reconstructed == values, name
        idf = ROOT / f'ipcore/{name}/{name}.idf'
        files = [p.findtext('value') for p in ET.parse(idf).iter() if p.findtext('name') == 'INIT_FILE']
        assert files == [dat.resolve().as_posix()], files
        assert f'localparam INIT_FILE = "{dat.resolve().as_posix()}"' in (ROOT / f'ipcore/{name}/{name}.v').read_text()
        for bank in range(banks):
            for lane in range(lanes):
                cell = synthesized[(name, bank, lane)]
                assert int(cell['config']['DATA_WIDTH_A']) == width
                assert cell['blocks'] == {index: (288, params[(index, bank, lane)]) for index in range(128)}, (name, bank, lane)
        initializations[name] = dict(words=4096, dat_sha256=sha(dat), generated_INIT_matches_DAT=True,
                                     synthesized_memory_instances=banks * lanes)
    report['initializations'] = initializations

    pnr_path = ROOT / 'place_route/board_top_pnr.netlist'
    pnr = pnr_path.read_text()
    banks_present = re.findall(r'^.*ADDR_LOOP\[\d+\]\.DATA_LOOP\[\d+\].*;gopDRM$', pnr, re.M)
    assert len(banks_present) == 8
    counter_banks = sorted(set(map(int, re.findall(r'g_perf\.u_perf/count\[(\d+)\]', pnr))))
    assert counter_banks == list(range(13)), counter_banks
    candidate_pnr = ROOT / 'sim/cpu_performance_2b/build/pds_20261010_b/place_route/seed_5/board_top_pnr.netlist'
    assert sha(candidate_pnr) == sha(pnr_path)
    report['pnr_connectivity'] = dict(memory_instances=8, counter_banks=counter_banks,
        sha256=sha(pnr_path), matches_previous_verified_2B_candidate=True,
        limitation='This PNR connectivity file contains no INIT payload; cannot replace current implementation INIT export')

    bit = ROOT / 'generate_bitstream/board_top.sbit'
    assert bit.stat().st_size > 100000
    bit_log = (ROOT / 'generate_bitstream/run.log').read_text()
    assert 'Generating Programming File done.' in bit_log
    assert f'The bitstream file is "{bit.resolve().as_posix()}"' in bit_log
    assert (ROOT / 'synthesize/board_top_syn.vm').stat().st_mtime <= pnr_path.stat().st_mtime <= timing_path.stat().st_mtime <= bit.stat().st_mtime
    report['bitstream'] = dict(path=bit.relative_to(ROOT).as_posix(), sha256=sha(bit), bytes=bit.stat().st_size)

    app_path = ROOT / 'tools/uart_loader/candidates/bsp_workflow/application.py'
    spec = importlib.util.spec_from_file_location('review_app', app_path)
    app = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(app)
    report['applications'] = {}
    for name, relative in historical['applications'].items():
        assert sha(ROOT / relative) == historical['manifests'][relative], relative
        info = app.require_manifest(ROOT / relative)
        report['applications'][name] = dict(manifest=relative, bytes=(ROOT / info['bin_path']).stat().st_size,
                                          manifest_sha256=sha(ROOT / relative))

    implementation = ROOT / 'generate_netlist/board_top_sim.v'
    fresh = implementation.is_file() and implementation.stat().st_mtime >= pnr_path.stat().st_mtime
    report['implementation_export'] = dict(path=implementation.relative_to(ROOT).as_posix(),
        fresh=fresh, contains_perf_counter='g_perf' in implementation.read_text() if implementation.is_file() else False)
    if not fresh:
        report['status'] = 'PERF2B_MAIN_PDS_AUDIT_INCOMPLETE'
        report['remaining'] = ['User: Generate Netlist for the current routed main project; re-audit its 8 memory INIT payloads.']
        report['deployment_gate_created'] = False
        return
    implemented = memories(implementation)
    reference = memories(ROOT / 'sim/cpu_performance_2b/build/pds_20261010_b/generate_netlist/board_top_sim.v')
    check_implementation(synthesized, implemented, reference)
    assert report['implementation_export']['contains_perf_counter'], 'Counter absent from implementation export'
    report['implementation_export']['all_8_memory_INIT_payloads_verified'] = True
    report['status'] = 'PERF2B_MAIN_PDS_ARTIFACT_AUDIT_PASS'
    report['remaining'] = ['Bind a new frozen deployment gate and test the actual board; this script does not open serial.']
    report['deployment_gate_created'] = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    assert re.fullmatch('[a-z0-9_-]+', args.tag)
    out = ROOT / 'sim/cpu_performance_2b/build' / args.tag
    out.mkdir(parents=True, exist_ok=False)
    paths = [Path(__file__).resolve(), ROOT / 'RISCV.pds', ROOT / 'constraint_check/temp_constraint_file.fdc',
             ROOT / 'generate_bitstream/board_top.sbit', ROOT / 'synthesize/board_top_syn.vm',
             ROOT / 'place_route/board_top_pnr.netlist', ROOT / 'report_timing/board_top.rtr',
             ROOT / 'generate_netlist/board_top_sim.v']
    paths += list((ROOT / 'myriscv').glob('*.v')) + list((ROOT / 'myriscv').glob('*.vh'))
    for directory in ('ipcore/inst_rom', 'ipcore/data_ram', 'ipcore/ddr3'):
        paths += [p for p in (ROOT / directory).rglob('*') if p.is_file() and p.suffix in ('.v', '.vh', '.idf')]
    before = {p.relative_to(ROOT).as_posix(): sha(p) for p in paths if p.is_file()}
    report = dict(status='RUNNING', board_result='NOT_TESTED', pds_started=False,
                  codex_opened_serial=False, input_sha256=before, deployment_gate_created=False)
    try:
        audit(report)
    except Exception as exc:
        report.update(status='PERF2B_MAIN_PDS_AUDIT_FAIL', error=f'{type(exc).__name__}: {exc}')
        raise
    finally:
        report['inputs_unchanged'] = all(sha(ROOT / p) == digest for p, digest in before.items())
        if not report['inputs_unchanged']:
            report.update(status='INPUT_CHANGED', deployment_gate_created=False)
        (out / 'review_result.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(report['status'], out / 'review_result.json', flush=True)


if __name__ == '__main__':
    main()
