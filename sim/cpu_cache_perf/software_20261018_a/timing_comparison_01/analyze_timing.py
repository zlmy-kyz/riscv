"""Offline attribution from existing logs and ELF manifests; no new measurement."""
from pathlib import Path
import hashlib
import json
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
def read(p): return json.loads((ROOT/p).read_text(encoding='utf-8'))
def sha(p): return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def main():
    assert not (HERE/'comparison.json').exists(), 'Preserve comparison evidence'
    evidence = {}
    rows = {}
    for mode in ['performance','validation']:
        name = mode+'_300'
        baseline_path = f'sim/cpu_ex_redirect/board/task039_target_fetch_300_01/{name}.json'
        fixed_path = f'sim/cpu_cache_perf/board/task042_fixed_pv_300_01/{name}.json'
        extended_path = ('sim/cpu_cache_perf/board/perf27_300_20261018_124013/performance_300.json'
            if mode == 'performance' else 'sim/cpu_cache_perf/board/perf27_v_parser_fix01_01/validation_300.json')
        baseline, fixed, extended = [read(p) for p in [baseline_path,fixed_path,extended_path]]
        old = baseline['application']['parsed']
        a = fixed['application']['parsed']
        fixed_review = read(str((HERE/f'fixed_{"P" if mode=="performance" else "V"}_review.json').relative_to(ROOT)))
        assert fixed_review['application'] == a
        if mode == 'performance':
            recovery_path = 'sim/cpu_cache_perf/software_20261018_a/parser_case_fix01/review.json'
            recovery = read(recovery_path)
            assert recovery['raw_log_sha256'] == sha(extended_path)
            b = recovery['application']
            evidence[recovery_path] = sha(recovery_path)
        else:
            b = extended['application']['parsed']
            assert read(str((HERE/'perf27_V_review.json').relative_to(ROOT)))['application'] == b
            assert extended['application']['extra_rx_hex'] == '' and b['crcfinal'] == '8803'
        assert baseline['application_info']['bin_sha256'] == fixed['application_info']['bin_sha256']
        assert fixed['application_info']['bin_sha256'] != extended['application_info']['bin_sha256']
        assert fixed['bitstream_local_file'] == extended['bitstream_local_file']
        assert old['counters']['instret'] == a['counters']['instret'] == b['counters']['instret']
        delta = {n:b['counters'][n]-v for n,v in a['counters'].items()}
        assert sum(delta[n] for n in ['if_stall_cycles','mem_stall_cycles','branch_flush_cycles',
            'control_redirect_cycles','control_hold_cycles','load_use_cycles','other_cycles']) == delta['cycles']
        rows[mode] = dict(baseline039_cycles=old['ticks'], hardware042_frozen_BIN_cycles=a['ticks'],
            hardware042_perf27_BIN_cycles=b['ticks'], frozen_BIN_seconds=a['seconds'], perf27_BIN_seconds=b['seconds'],
            hardware_same_BIN_delta_cycles=a['ticks']-old['ticks'],
            hardware_same_BIN_delta_percent=100*(a['ticks']-old['ticks'])/old['ticks'],
            new_BIN_delta_cycles=delta['cycles'], new_BIN_delta_percent=100*delta['cycles']/a['ticks'],
            new_BIN_delta_seconds=b['seconds']-a['seconds'], legacy_counter_deltas=delta,
            new_BIN_AR_increase_percent=100*delta['ddr_ar_commands']/a['counters']['ddr_ar_commands'],
            local_bitstream_SHA256=fixed['bitstream_local_file']['sha256'],
            programmed_FPGA_independently_observed=False,
            original_P_post_application_extra_RX_gap_preserved=(mode=='performance'))
        for p in [baseline_path,fixed_path,extended_path]: evidence[p] = sha(p)
    base = 'tests/cpu_performance_2b/build/'
    oldpath = base+'measure_zmmul300_20261013_a/performance_300/manifest.json'
    newpath = base+'measure_perf27_20261018_a/performance_300/manifest.json'
    old, new = read(oldpath), read(newpath)
    layout = {n:dict(old=hex(old['symbols'][n]), new=hex(new['symbols'][n]),
        delta_bytes=new['symbols'][n]-old['symbols'][n]) for n in
        ['main','iterate','core_bench_list','core_bench_matrix','core_bench_state',
         'matrix_mul_matrix','start_time','stop_time','static_memblk']}
    port1 = (ROOT/oldpath).with_name('core_portme.c')
    port2 = (ROOT/newpath).with_name('core_portme.c')
    assert port1.read_bytes() == port2.read_bytes()
    for p in [oldpath,newpath]: evidence[p] = sha(p)
    for p in HERE.glob('*_review.json'): evidence[str(p.relative_to(ROOT))] = sha(str(p.relative_to(ROOT)))
    report = dict(status='EXISTING_LOGS_SHOW_PERF27_LAYOUT_COST_NOT_SAME_BIN_COUNTER_HARDWARE_SLOWDOWN',
        comparisons=rows, ELF_symbol_layout=layout, timer_port_source_byte_identical=True,
        printing_after_frozen_ROI=True,
        attribution='Layout/cache mapping is supported by relocated code/data, identical instret/AW, increased AR/MEM wait, and near-identical same-frozen-BIN hardware cycles. A per-miss causality trace was not collected.',
        limits='P CRC/27 counts recovered; original FAIL and unrecorded post-application extra RX remain. Same local bitstream record is not independent observation of programmed FPGA. No new test, PDS, board run or optimization.',
        evidence_sha256=evidence)
    (HERE/'comparison.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    for name,r in rows.items():
        print(name, 'fixed',r['frozen_BIN_seconds'],'perf27',r['perf27_BIN_seconds'],
              'delta',r['new_BIN_delta_percent'],'%','AR delta',r['legacy_counter_deltas']['ddr_ar_commands'],
              'MEM delta',r['legacy_counter_deltas']['mem_stall_cycles'])
if __name__ == '__main__': main()
