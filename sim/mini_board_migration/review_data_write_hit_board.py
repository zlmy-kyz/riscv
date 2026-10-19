"""Read-only serial evidence review; no PDS/bitstream or serial operations."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/perf_2b'))
import run_data_write_hit_measurement as measurement
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    folder=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01'
    old=ROOT/'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul'
    out=folder/'codex_review_20261013'
    assert not out.exists(), 'Preserve existing review'
    modes={}; evidence={}
    for name in ('performance_300','validation_300'):
        path=folder/(name+'.json'); baseline=old/(name+'.json')
        result=measurement.verify(path); reference=measurement.verify(baseline)
        raw=json.loads(path.read_text()); prior=json.loads(baseline.read_text())
        assert raw['application_info']==prior['application_info']
        assert raw['manifest_sha256']==prior['manifest_sha256']
        assert len(raw['records'])==123 and sum(r['cmd']==4 for r in raw['records'])==1
        a=result['application']; b=reference['application']; c=a['counters']; d=b['counters']
        assert all(c[k]==d[k] for k in ('instret','branch_redirects','ddr_aw_commands'))
        modes[name]=dict(current=a,baseline=b,comparison_kind='Same frozen BIN and 300 iterations',
            seconds_saved=b['seconds']-a['seconds'],time_reduction_percent=100*(1-a['ticks']/b['ticks']),
            throughput_speedup=b['ticks']/a['ticks'],AR_reduction_percent=100*(1-c['ddr_ar_commands']/d['ddr_ar_commands']),
            delta_counters={k:c[k]-d[k] for k in c},
            stall_percent={k:100*c[k]/c['cycles'] for k in ('if_stall_cycles','mem_stall_cycles','other_cycles')})
        for p in (path,baseline):evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    out.mkdir()
    receipt=dict(status='DATA_WRITE_HIT_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS',
        modes=modes,evidence_sha256=evidence,serial_opened_by_Codex=False,PDS_or_bitstream_review=False,
        FPGA_programming_independently_observed=False,formal_benchmark=False,
        scope='Actual UART protocol, DDR readback CRC, CoreMark CRC and counters; under 10 seconds, performance comparison only')
    (out/'result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for n,r in modes.items():print(n,'seconds',r['current']['seconds'],'reduction%',r['time_reduction_percent'])


if __name__=='__main__':main()
