"""Read-only task 006 evidence audit. No HDL tools, PDS or serial access."""
from pathlib import Path
import argparse
import hashlib
import json
import re
import shutil
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from resume_checks import require_inputs, generate_loader_tb
sys.path.insert(0, str(ROOT / 'sim/cpu_performance_2b'))
from check_output import check
from application import require_manifest, parse_output
from plan import make_plan


def sha(p):
    with p.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-tag', required=True)
    parser.add_argument('--tag', required=True)
    args = parser.parse_args()
    assert all(re.fullmatch('[a-z0-9_-]+', s) for s in (args.run_tag, args.tag))
    manifests = require_inputs()
    assert manifests['checks_input_manifest.json'] == 'a7828210c3e461c38359ae1c2d49adba748aeeae14a98d552971e96fc391e812'
    out = HERE / 'build' / args.tag
    assert not out.exists(), 'Use a fresh review tag'
    evidence = {}

    def retain(p):
        evidence[p.relative_to(ROOT).as_posix()] = sha(p)
        return p

    def read(p):
        return json.loads(retain(p).read_text())

    reviewed = {}
    for suffix, name, enable in [('hello_off', 'hello', 0), ('hello_on', 'hello', 1),
                                 ('crc32_on', 'crc32', 1), ('perf1_on', 'performance_1', 1),
                                 ('val1_on', 'validation_1', 1)]:
        folder = HERE / 'build' / (args.run_tag + '_' + suffix)
        app = folder / 'application'
        receipt = read(folder / 'adapted_check_receipt.json')
        result = read(app / 'results.json')
        assert receipt['status'] == 'INST_LINE_BUFFER_ADAPTED_CHECK_PASS'
        assert receipt['suite'] == 'loader' and receipt['simulation_started']
        assert receipt['inputs_unchanged'] and receipt['manifests'] == manifests
        assert not receipt['pds_started'] and not receipt['serial_opened']
        assert receipt['board_result'] == result['board_result'] == 'NOT_TESTED'
        assert result['status'] == 'SAME_LOADER_APPLICATION_SIM_PASS'
        assert result['application'] == name and not result['partial']
        assert result['protected_unchanged'] and result['inputs_unchanged']
        assert result['timer_scale'] == 1
        for field in ('input_sha256', 'protected_sha256'):
            for n, h in result[field].items():
                assert sha(ROOT / n) == h, 'INPUT_CHANGED: ' + n
        tb = retain(folder / 'generated/tb_applications_checked.sv')
        assert tb.read_text(encoding='utf-8') == generate_loader_tb(enable)
        assert sha(tb) == receipt['loader']['generated_tb_sha256']
        assert result['input_sha256'][tb.relative_to(ROOT).as_posix()] == sha(tb)
        assert receipt['loader']['original_tb_sha256'] == sha(ROOT / 'sim/bsp_workflow/tb/tb_applications.v')
        log = retain(app / 'modelsim.log').read_text(errors='replace')
        compiled = retain(app / 'compile.log').read_text(errors='replace')
        for text in (log, compiled):
            assert re.search(r'Errors: 0, Warnings: 0', text)
            assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal):', text)
        assert 'myriscv\\dual_sram_to_pango_ddr_bridge.v' in compiled.replace('/', '\\')
        assert tb.name in compiled and 'work.loader_ddr_model' in log
        passes = re.findall(r'^# RESULT: PASS applications_stage3 .+$', log, re.M)
        assert len(passes) == 1 and passes[0] == result['evidence']
        totals = dict(re.findall(r'(\w+|AW/W)=(\d+)', passes[0]))
        totals = {k: int(v) for k, v in totals.items()}
        matches = re.findall(r'^# CHECK: LINE_LEDGER (.+)$', log, re.M)
        assert len(matches) == 1
        ledger = dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)', matches[0]))
        keys = 'enable IF hit miss IF_rsp data data_rsp AR_IF AR_DATA AW R W pending'.split()
        aliases = 'enable if_requests hits misses if_responses data_requests data_responses ar_if ar_data aw r w pending'.split()
        assert dict(zip(aliases, (ledger[k] for k in keys))) == receipt['loader']['ledger']
        assert ledger['enable'] == enable and ledger['IF'] == ledger['hit'] + ledger['miss']
        assert ledger['hit'] > 0 and ledger['miss'] > 0 if enable else ledger['hit'] == 0
        assert ledger['data'] == ledger['data_rsp'] == ledger['AR_DATA'] + ledger['AW']
        assert ledger['AW'] == ledger['W'] and ledger['R'] == ledger['AR_IF'] + ledger['AR_DATA']
        assert ledger['IF'] - ledger['IF_rsp'] == ledger['miss'] - ledger['AR_IF'] == ledger['pending']
        assert ledger['pending'] == (1 if suffix == 'hello_off' else 0)
        assert ledger['IF'] == totals['if_req'] and ledger['IF_rsp'] == totals['if_rsp']
        assert ledger['data'] == totals['DDR_req'] == totals['retired_DDR']
        assert ledger['AW'] == totals['AW/W'] and ledger['R'] == totals['AR']
        app_lines = re.findall(r'^# APP: (.+)$', log, re.M)
        assert len(app_lines) == 1
        summary = dict((k, int(v)) for k, v in re.findall(r'(\w+)=(\d+)(?= |$)', app_lines[0]))
        assert summary['partial'] == 0 and summary['done'] == 1
        assert summary['ecalls'] == 1 and summary['irqs'] == 0
        manifest = (ROOT / ('tests/bsp_workflow/build' if name in ('hello', 'crc32')
                    else 'tests/cpu_performance_2b/build/measure_20261010_c') / name / 'manifest.json')
        info = require_manifest(manifest)
        assert info == result['application_info']
        rows = make_plan(info)
        assert rows == read(app / 'cases.json') and len(rows) == result['frames'] == totals['frames']
        assert sum(bool(row.get('run')) for row in rows) == 1
        requests = b''.join(bytes.fromhex(row['tx_hex']) for row in rows)
        responses = b''.join(bytes.fromhex(row['expected_hex']) for row in rows)
        for filename, expected in [('requests.hex', requests), ('responses.hex', responses)]:
            assert bytes.fromhex(retain(app / filename).read_text()) == expected
        assert retain(app / 'uart_rx.bin').read_bytes() == requests
        tx = retain(app / 'uart_tx.bin').read_bytes()
        assert tx[:len(responses)] == responses
        raw = retain(app / 'application_uart.txt').read_bytes()
        assert tx[len(responses):] == raw and len(raw) == summary['output']
        assert sha(app / 'application_uart.txt') == result['application_uart_sha256']
        if info['kind'] == 'coremark':
            parsed = check(info, raw)
            parsed = dict(parsed, **parsed['crc'])
            assert parsed['ticks'] == summary['timer_ticks'] and summary['timer_bench_reads'] == 2
            assert parsed['counters']['instret'] == (829739 if name == 'performance_1' else 882363)
        else:
            parsed = parse_output(info, raw)
        assert parsed == result['application_result'] == receipt['loader']['application_result']
        for filename in ('metadata.hex', 'ddr_trace.csv', 'run.tcl', 'vlib.log'):
            retain(app / filename)
        reviewed[suffix] = dict(application=name, enable=enable, ledger=ledger,
                                totals=totals, application_result=parsed, final_checks_executed=True)
    assert reviewed['hello_off']['application_result'] == reviewed['hello_on']['application_result']
    for n, expected_hash, expected_status in [
        ('checks_static_20261011_a/result.json', '7542755962ac326613d08e9373581c39f90294ead60642c5cde6d45ac5897c83', 'INST_LINE_BUFFER_ADAPTER_OFFLINE_CHECK_PASS'),
        ('checks_compare_20261011_a/adapted_check_receipt.json', 'c9966426bb980164705d4e647481f81ee2d790cd7749463f99683a745b2db1d9', 'INST_LINE_BUFFER_ADAPTED_CHECK_PASS')]:
        p = HERE / 'build' / n
        prior = read(p)
        assert sha(p) == expected_hash and prior['status'] == expected_status and prior['inputs_unchanged']
        for path, h in prior.get('evidence_sha256', {}).items():
            assert sha(ROOT / path) == h
    old_bit = retain(ROOT / 'sim/cpu_performance_2b/build/main_pds_board_20261010_a/frozen_inputs/generate_bitstream/board_top.sbit')
    assert sha(old_bit) == '4231dcd62362f567b7ce47553c472832604fd78bed99ece6913004f24614fe76'
    assert require_inputs() == manifests
    assert all(sha(ROOT / n) == h for n, h in evidence.items())
    out.mkdir()
    # Preserve the tested design before the user's PDS run changes reports/bitstream.
    frozen = {}
    sources = list((ROOT / 'myriscv').glob('*.v')) + list((ROOT / 'myriscv').glob('*.vh')) + [ROOT / 'RISCV.pds']
    for p in sources:
        relative = p.relative_to(ROOT)
        copy = out / 'tested_sources' / relative
        copy.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, copy)
        assert sha(copy) == sha(p)
        frozen[relative.as_posix()] = sha(copy)
    result = dict(status='INST_LINE_BUFFER_LOADER_EVIDENCE_AUDIT_PASS', reviewed=reviewed,
                  manifests=manifests, evidence_sha256=evidence, tested_sources_sha256=frozen,
                  old_bitstream_preserved=True, source_bridge_sha256=sha(ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'),
                  simulation_started=False, pds_started=False, serial_opened=False,
                  optimized_board_result='NOT_TESTED', next_step='USER_PDS_REBUILD_THEN_NEW_ARTIFACT_GATE',
                  scope='Task006 functional Loader; unchanged Task004/005 evidence retained. Known ISA gaps remain.')
    (out / 'review_result.json').write_text(json.dumps(result, indent=2) + '\n')
    print('RESULT: PASS offline Loader audit', len(reviewed), 'cases;', out)


if __name__ == '__main__':
    main()
