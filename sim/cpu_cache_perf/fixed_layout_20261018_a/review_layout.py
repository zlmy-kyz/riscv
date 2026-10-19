"""Static layout/ABI and offline schema preparation; no new CPU or board run."""
from pathlib import Path
import json
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0,str(ROOT/'tests/cpu_performance_2b'))
from perf27_software import require_manifest,parse_measurement,sha
from perf27_fixed_software import DEFAULT_FIXED_TAG

def main():
    assert not (HERE/'review.json').exists(), 'Preserve static review'
    folder = ROOT/'tests/cpu_performance_2b/build'/DEFAULT_FIXED_TAG
    build = json.loads((folder/'build_review.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT/n)==h for n,h in build['protected_sha256'].items())
    rows = {}
    for name in ['performance_300','validation_300']:
        info = require_manifest(folder/name/'manifest.json')
        plan_path = ROOT/f'sim/cpu_cache_perf/board/perf27_fixed_plan_20261018_01/{name}.json'
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
        assert not plan['serial_opened'] and plan['application_info'] == info
        assert len(plan['plan']) == 295 and sum(bool(p.get('run')) for p in plan['plan']) == 1
        source_log = ROOT/('sim/cpu_cache_perf/board/perf27_300_20261018_124013/performance_300.json'
            if name=='performance_300' else 'sim/cpu_cache_perf/board/perf27_v_parser_fix01_01/validation_300.json')
        old = json.loads(source_log.read_text(encoding='utf-8'))
        # Schema replay only: those counts were NOT produced by the fixed BIN.
        parsed = parse_measurement(info,bytes.fromhex(old['application']['rx_hex']),board=False)
        assert parsed['counter_count']==27 and parsed['comparison_kind']==info['comparison_kind']
        rows[name] = dict(bin_sha256=info['bin_sha256'],bytes=info['bytes'],
            frozen_manifest_sha256=info['frozen_manifest_sha256'],layout_proof=info['layout_proof'],
            preserved_symbol_addresses={n:hex(info['symbols'][n]) for n in
                ['main','iterate','core_bench_list','core_bench_matrix','core_bench_state','static_memblk',
                 'start_time','stop_time','__global_pointer$','__stack_bottom','__stack_top']},
            reader_sections={n:v for n,v in info['sections'].items() if n.startswith('.perf27')},
            plan_path=str(plan_path.relative_to(ROOT)),plan_sha256=sha(plan_path),
            offline_schema_replay_source_sha256=sha(source_log),
            replay_is_new_hardware_or_runtime_evidence=False)
    old_review = json.loads((HERE/'old_V_compat_review.json').read_text(encoding='utf-8'))
    assert old_review['application']['counter_count']==27 and old_review['application']['crcfinal']=='8803'
    sources = [ROOT/'tests/cpu_performance_2b'/n for n in
        ['build_perf27_fixed.py','perf27_fixed_software.py','perf27_software.py','perf27.c','perf.h']]
    sources += [ROOT/'tools/uart_loader/candidates/perf_2b'/n for n in
        ['run_perf27_measurement.py','run_perf27_measurements.ps1']]
    sources.append(Path(__file__))
    report = dict(status='PERF27_FIXED_LAYOUT_STATIC_AND_OFFLINE_SCHEMA_PASS_RUNTIME_PENDING',
        results=rows,old_frozen_and_unfixed_BINs_and_RTL_unchanged=True,
        ABI='Entry is LUI t0 + JALR zero through t0; RA/SP preserved before normal C reader prologue. Calls old printf/timer at original addresses.',
        initialization='Original startup and BSS bounds unchanged; isolated reader scratch is zero-loaded PROGBITS in the new image, not added to the timed startup BSS loop.',
        flat_BIN_padding_note='37328 bytes include the gap to 0x40008000; upload takes longer, outside the benchmark ROI.',
        runtime_limit='No fixed-layout CPU/board execution; DDR/cache initial phase can still vary. Do not promise exact cycles or record runtime PASS.',
        dynamic_simulation='NOT_RUN',PDS='NOT_RUN',serial_opened=False,
        source_sha256={str(p.relative_to(ROOT)):sha(p) for p in sources})
    (HERE/'review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['status'])
if __name__=='__main__': main()
