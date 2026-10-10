"""Read-only review of the user's rebuild; freeze a new identity without rewriting old gates."""
from pathlib import Path
import hashlib, json, re, shutil, xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
gate_path = OUT / 'deployment_gate.json'
assert not gate_path.exists()
old_gate_path = ROOT / 'sim/bsp_workflow/build/deployment_gate.json'
old = json.loads(old_gate_path.read_text())
inputs = dict(old['input_sha256'])
for field in ('input_sha256', 'evidence_sha256'):
    for path, expected in old[field].items():
        assert sha(ROOT / path) == expected, path
for row in old['frozen_source_copies']:
    assert sha(ROOT / row['archive']) == row['sha256']

prior_path = ROOT / 'sim/bsp_workflow/board/first_submission_result.json'
prior = json.loads(prior_path.read_text())
assert prior['status'] == 'UNIFIED_BSP_TEN_ROUND_ACTUAL_BOARD_ARCHIVE_PASS'
for row in prior['success_archive_entries']:
    assert sha(ROOT / row['archive']) == row['sha256']

initializations = {}
for name, kind in [('inst_rom', 'rom'), ('data_ram', 'ram')]:
    dat = ROOT / f'tests/uart_loader/candidates/verify_run_hello/build/loader_{kind}.dat'
    idf = ROOT / f'ipcore/{name}/{name}.idf'
    params = {p.findtext('name'): p.findtext('value') for p in ET.parse(idf).iter() if p.find('name') is not None}
    assert Path(params['INIT_FILE']).resolve() == dat.resolve()
    new = ROOT / f'ipcore/{name}/rtl/{name}_init_param.v'
    previous = ROOT / f'sim/uart_loader/build/verify_run_hello/pds_candidate/ipcore/{name}/rtl/{name}_init_param.v'
    assert new.read_bytes() == previous.read_bytes()
    initializations[name] = dict(dat=dat.relative_to(ROOT).as_posix(), dat_sha256=sha(dat),
                                generated_init_sha256=sha(new), matches_previous_4096_word_verified_initialization=True)

def cells(path):
    text = path.read_text()
    matches = list(re.finditer(r'(?:GTP|V)_DRM36K_E1\s*/\*\s*(.*?)\s*\*/\s*#\(', text))
    result = {}
    for i, match in enumerate(matches):
        name = match[1]
        if 'ADDR_LOOP[' not in name:
            continue
        body = text[match.end():matches[i + 1].start() if i + 1 < len(matches) else len(text)]
        blocks = {key: (int(bits), int(value, 2 if base.lower() == 'b' else 16))
                  for key, bits, base, value in re.findall(r'\.INIT_([0-9A-F]{2})\(\s*(\d+)\s*\x27([bh])([0-9a-fA-F]+)\s*\)', body)}
        assert len(blocks) == 128, name
        configs = {key: re.search(r'\.' + key + r'\(([^)]+)\)', body)[1].strip()
                   for key in ('DATA_WIDTH_A', 'DATA_WIDTH_B', 'RAM_MODE', 'RAM_CASCADE', 'DOA_REG', 'DOB_REG')}
        location = re.search(r'ADDR_LOOP\[(\d+)\]\.DATA_LOOP\[(\d+)\]', name)
        assert location is not None
        key = (configs['RAM_MODE'], int(location[1]), int(location[2]))
        assert key not in result
        result[key] = dict(blocks=blocks, configs=configs)
    assert len(result) == 8
    return result

netlist = ROOT / 'synthesize/board_top_syn.vm'
old_netlist = ROOT / 'sim/uart_loader/build/verify_run_hello/pds_candidate/synthesize/board_top_syn.vm'
assert cells(netlist) == cells(old_netlist), 'Synthesized memory initialization/configuration mismatch'
timing_path = ROOT / 'report_timing/board_top.rtr'
timing = timing_path.read_text()
assert 'Design Summary : All Constraints Met.' in timing
assert 'ddrphy_sysclk              93.7500 MHz' in timing
assert 'Slack (VIOLATED)' not in timing
program_log = ROOT / 'generate_bitstream/run.log'
assert 'Generating Programming File done.' in program_log.read_text()
bit = ROOT / 'generate_bitstream/board_top.sbit'
assert sha(bit) == '7d752ee531164302e772d191f165cd6f87bd2e6128b9367ac83dd32b4709cacf'
assert netlist.stat().st_mtime <= bit.stat().st_mtime and timing_path.stat().st_mtime <= bit.stat().st_mtime

sources = [ROOT / 'RISCV.pds', old_gate_path, prior_path, Path(__file__).resolve(),
           ROOT / 'tools/uart_loader/candidates/rebuilt_20261010/run_board.py',
           ROOT / 'constraint_check/temp_constraint_file.fdc', bit, netlist, timing_path, program_log,
           ROOT / 'place_route/board_top.prr', ROOT / 'synthesize/run.log']
for directory in ('myriscv', 'ipcore/inst_rom', 'ipcore/data_ram', 'ipcore/ddr3/rtl'):
    for path in (ROOT / directory).rglob('*'):
        if path.is_file() and path.suffix in ('.v', '.vh', '.idf'):
            sources.append(path)
sources += [ROOT / 'ipcore/ddr3/ddr3.idf', ROOT / 'ipcore/ddr3/ddr3.v']
for path in sources:
    inputs[path.relative_to(ROOT).as_posix()] = sha(path)
snapshot = OUT / 'frozen_inputs'
assert not snapshot.exists()
copies = []
for path, expected in sorted(inputs.items()):
    target = snapshot / path
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ROOT / path, target)
    assert sha(target) == expected
    copies.append(dict(source=path, archive=target.relative_to(ROOT).as_posix(), sha256=expected))
gate = dict(status='REBUILT_LOADER_PRE_BOARD_AUDIT_PASS', date='2026-10-10',
            board_result='NOT_TESTED', manifests=old['manifests'], input_sha256=inputs,
            frozen_source_copies=copies, successful_bitstream_sha256=sha(bit),
            bitstream_path=bit.relative_to(ROOT).as_posix(), original_sim_gate_sha256=sha(old_gate_path),
            original_sim_inputs_unchanged=True, original_sim_evidence_unchanged=True,
            prior_success_snapshot_checked=len(prior['success_archive_entries']),
            initializations=initializations, synthesized_memory_instances_verified=8,
            implementation_netlist_initialization_check='NOT_AVAILABLE; generate_netlist export is dated 2026-10-03 and excluded',
            timing_constraints='ALL_EXISTING_CONSTRAINTS_MET', core_clock_mhz=93.75,
            timing_scope='Existing constraints; this does not imply every physical I/O is constrained',
            CPU_RTL_changed=False, Loader_changed=False, functional_RTL_simulation_reused=True,
            codex_opened_serial=False, JTAG_programming_independently_observed=False)
with gate_path.open('x', encoding='utf-8') as stream:
    json.dump(gate, stream, indent=2)
print('RESULT: PASS rebuilt pre-board audit;', len(inputs), 'frozen inputs; 8 implementation memories; board NOT_TESTED')
