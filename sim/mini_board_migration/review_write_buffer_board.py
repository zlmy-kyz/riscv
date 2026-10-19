"""Read actual P300/V300 UART evidence and compare the same frozen BIN baseline."""
from pathlib import Path
import hashlib,json,sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/perf_2b'))
import run_write_buffer_soc_resume_measurement as tool
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    folder=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01'
    prior=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01'
    initial=ROOT/'sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01/zmmul'
    out=folder/'codex_review_20261013';assert not out.exists(),'Preserve existing review'
    modes={};evidence={}
    for name in ('performance_300','validation_300'):
        path=folder/(name+'.json');baseline=prior/(name+'.json');first=initial/(name+'.json')
        current=tool.transport.verify(path);reference=tool.transport.verify(baseline);original=tool.transport.verify(first)
        raw=json.loads(path.read_text());old=json.loads(baseline.read_text())
        assert raw['application_info']==old['application_info'] and raw['manifest_sha256']==old['manifest_sha256']
        assert len(raw['records'])==123 and sum(r['cmd']==4 for r in raw['records'])==1
        assert raw['status']=='MEASUREMENT_APPLICATION_BOARD_PASS' and raw['user_KEY0_confirmation'] and raw['retry_count']==0
        a=current['application'];b=reference['application'];z=original['application'];c=a['counters'];d=b['counters']
        assert all(c[k]==d[k] for k in ('instret','branch_redirects','ddr_ar_commands','ddr_aw_commands','ddr_transactions',
                                      'load_use_cycles','other_cycles'))
        modes[name]=dict(current=a,baseline=b,comparison_kind='Same frozen BIN and 300 iterations',
            seconds_saved=b['seconds']-a['seconds'],cycles_saved=b['ticks']-a['ticks'],
            time_reduction_percent=100*(1-a['ticks']/b['ticks']),throughput_speedup=b['ticks']/a['ticks'],
            throughput_increase_percent=100*(b['ticks']/a['ticks']-1),
            delta_counters={k:c[k]-d[k] for k in c},
            stall_percent={k:100*c[k]/c['cycles'] for k in ('if_stall_cycles','mem_stall_cycles',
                'branch_flush_cycles','load_use_cycles','other_cycles')},
            MEM_reduction_percent=100*(1-c['mem_stall_cycles']/d['mem_stall_cycles']),
            AW_share_of_DDR_commands=100*c['ddr_aw_commands']/c['ddr_transactions'],
            cumulative_from_zmmul300=dict(seconds=z['seconds'],time_reduction_percent=100*(1-a['ticks']/z['ticks']),
                                         speedup=z['ticks']/a['ticks']))
        for p in (path,baseline,first):evidence[p.relative_to(ROOT).as_posix()]=sha(p)
    out.mkdir()
    receipt=dict(status='WRITE_BUFFER_ACTUAL_DDR_P_V_RAW_EVIDENCE_AND_SAME_BIN_PERFORMANCE_REVIEW_PASS',modes=modes,
        evidence_sha256=evidence,serial_opened_by_Codex=False,PDS_or_bitstream_review=False,
        FPGA_programming_independently_observed=False,formal_benchmark=False,RTL_changed=False,
        scope='Actual UART protocol, DDR readback CRC, five CoreMark CRCs, counters, same-BIN performance; under 10 seconds')
    (out/'result.json').write_text(json.dumps(receipt,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    for name,r in modes.items():
        print(name,json.dumps({k:v for k,v in r.items() if k not in ('current','baseline')},ensure_ascii=False))
if __name__=='__main__':main()
