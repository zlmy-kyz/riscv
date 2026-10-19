"""Close fixed-layout P/V application evidence only; no new run or broad reset claim."""
from pathlib import Path
import json
import sys
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT/'tests/cpu_performance_2b'))
from perf27_software import sha,require_manifest

def read(path): return json.loads(path.read_text(encoding='utf-8'))
def main():
    assert not (HERE/'review.json').exists(), 'Preserve completed review'
    pdir = ROOT/'sim/cpu_cache_perf/board/perf27_fixed_300_01'
    vdir = ROOT/'sim/cpu_cache_perf/board/perf27_fixed_v_jtag_01'
    identities = [read(d/'identity.json') for d in [pdir,vdir]]
    changed = [n for n,h in identities[0]['sha256'].items() if identities[1]['sha256'].get(n)!=h]
    assert changed == ['tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py'],changed
    assert all(sha(ROOT/n)==h for n,h in identities[1]['sha256'].items())
    results,evidence = {},{}
    for mode,directory,review_path in [
        ('performance',pdir,ROOT/'sim/cpu_cache_perf/fixed_layout_20261018_a/board_review_01/performance_review.json'),
        ('validation',vdir,HERE/'validation_review.json')]:
        rawpath = directory/(mode+'_300.json')
        raw,review = read(rawpath),read(review_path)
        assert raw['status']=='MEASUREMENT_APPLICATION_BOARD_PASS' and raw['serial_opened']
        assert review['responses']==295 and review['run_count']==1
        app = review['application']
        assert app==raw['application']['parsed'] and raw['application']['extra_rx_hex']==''
        assert app['crcfinal']==('5275' if mode=='performance' else '8803')
        assert len(app['counters'])==27 and raw['application_info']==require_manifest(raw['manifest_path'])
        c = app['counters']
        assert c['ddr_ar_commands']==c['icache_misses']+c['dcache_read_misses']
        if mode=='validation':
            assert raw['user_reset_method']=='jtag' and raw['user_reported_KEY0_press'] is False
            assert all(r['received_response_bytes']==r['expected_response_bytes']==60 for r in raw['records'])
        basepath = ROOT/f'sim/cpu_cache_perf/board/task042_fixed_pv_300_01/{mode}_300.json'
        baseline = read(basepath)['application']['parsed']
        results[mode] = dict(application=app,delta_vs_original_fixed_cycles=app['ticks']-baseline['ticks'],
            delta_vs_original_fixed_percent=100*(app['ticks']-baseline['ticks'])/baseline['ticks'],
            wait_cycle_percent={n:100*c[n]/c['cycles'] for n in
                ['icache_miss_wait_cycles','dcache_read_miss_wait_cycles','write_buffer_block_cycles',
                 'old_i_block_cycles','ex_branch_mem_wait_cycles']},
            wait_metrics_can_overlap=True)
        for p in [rawpath,directory/'identity.json',review_path,basepath]:
            evidence[p.relative_to(ROOT).as_posix()] = sha(p)
    assert read(pdir/'performance_300.json')['bitstream_local_file']==read(vdir/'validation_300.json')['bitstream_local_file']
    report = dict(status='PERF27_FIXED_LAYOUT_P_V300_ACTUAL_APPLICATION_CRC_PROTOCOL_27_COUNTERS_REVIEW_PASS',
        results=results,evidence_sha256=evidence,
        host_change_between_P_and_V='Partial-response recording and explicit JTAG prompt only; no RTL/BIN change',
        V_recovery='Same local bitstream reprogrammed via user-reported JTAG; first PING succeeded. KEY0 warm reset root cause remains unresolved.',
        preserved_failure='sim/cpu_cache_perf/board/perf27_fixed_300_01/validation_300.json remains FAIL; no LOAD/RUN occurred there.',
        limits='Short application comparison, not formal >=10s score; not full041/042 handshake/reset/IRQ regression; FPGA programming not independently observed.',
        no_new_run=True,no_PDS=True,no_automatic_next_optimization=True)
    (HERE/'review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['status'])
    for n,r in results.items():
        print(n,r['application']['ticks'],r['application']['seconds'],r['delta_vs_original_fixed_percent'])
if __name__=='__main__':main()
