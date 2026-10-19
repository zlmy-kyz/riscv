"""Audit actual UART logs and compare same frozen 300-iteration BINs; no PDS/serial."""
from pathlib import Path
import hashlib
import json
import sys

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/perf_2b'))
import run_response_turnover_measurement as measurement
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    folder=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01'
    old=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01'
    first=ROOT/'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul'
    out=folder/'codex_review_20261013';assert not out.exists(),'Preserve existing review'
    modes={};evidence={}
    for name in ('performance_300','validation_300'):
        path=folder/(name+'.json');baseline=old/(name+'.json');start=first/(name+'.json')
        result=measurement.verify(path);reference=measurement.verify(baseline);original=measurement.verify(start)
        raw=json.loads(path.read_text());prior=json.loads(baseline.read_text())
        assert raw['application_info']==prior['application_info'] and raw['manifest_sha256']==prior['manifest_sha256']
        assert len(raw['records'])==123 and sum(r['cmd']==4 for r in raw['records'])==1
        a=result['application'];b=reference['application'];z=original['application'];c=a['counters'];d=b['counters']
        assert all(c[k]==d[k] for k in ('instret','branch_redirects','ddr_aw_commands'))
        modes[name]=dict(current=a,baseline=b,comparison_kind='Same frozen BIN and 300 iterations',
            seconds_saved=b['seconds']-a['seconds'],time_reduction_percent=100*(1-a['ticks']/b['ticks']),
            throughput_speedup=b['ticks']/a['ticks'],throughput_increase_percent=100*(b['ticks']/a['ticks']-1),
            cumulative_from_zmmul300=dict(seconds=z['seconds'],time_reduction_percent=100*(1-a['ticks']/z['ticks']),
                                         speedup=z['ticks']/a['ticks']),
            delta_counters={k:c[k]-d[k] for k in c},
            stall_percent={k:100*c[k]/c['cycles'] for k in ('if_stall_cycles','mem_stall_cycles',
                           'branch_flush_cycles','load_use_cycles','other_cycles')},
            IF_reduction_percent=100*(1-c['if_stall_cycles']/d['if_stall_cycles']),
            MEM_reduction_percent=100*(1-c['mem_stall_cycles']/d['mem_stall_cycles']),
            AR_increase_percent=100*(c['ddr_ar_commands']/d['ddr_ar_commands']-1),
            AW_share_of_DDR_commands=100*c['ddr_aw_commands']/c['ddr_transactions'])
        for p in (path,baseline,start):evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    out.mkdir()
    receipt=dict(status='RESPONSE_TURNOVER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS',
        modes=modes,evidence_sha256=evidence,serial_opened_by_Codex=False,PDS_or_bitstream_review=False,
        FPGA_programming_independently_observed=False,formal_benchmark=False,RTL_changed=False,
        scope='Actual UART protocol, DDR readback CRC, CoreMark CRC, counters and same-BIN performance; under 10 seconds')
    (out/'result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,r in modes.items():
        print(name,json.dumps({k:v for k,v in r.items() if k not in ('current','baseline')},ensure_ascii=False))


if __name__=='__main__':main()
