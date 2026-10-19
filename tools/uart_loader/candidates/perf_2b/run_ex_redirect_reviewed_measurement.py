"""User-run P300/V300 for the observed EX implementation, distinct from reverted source."""
from pathlib import Path
import inspect
import json
import sys
import run_task036_measurement as transport

software=transport.software
ROOT=Path(__file__).resolve().parents[4]
REVIEW=ROOT/'sim/cpu_ex_redirect/board_review_20261018_a/review.json'
BASELINE=ROOT/'sim/cpu_request_presample/board/review_20261018_01/board_review.json'

def load_review():
    return json.loads(REVIEW.read_text(encoding='utf-8'))

def require_inputs():
    r=load_review()
    for name,digest in r['observed_sha256'].items():
        if software.sha(REVIEW.parent/name)!=digest:
            raise ValueError('Reviewed artifact changed: '+name)
    for name,digest in r['unchanged_runtime_input_sha256'].items():
        if software.sha(ROOT/name)!=digest:
            raise ValueError('Runtime input changed: '+name)
    if software.sha(BASELINE)!=r['baseline_review_sha256']:
        raise ValueError('036 baseline review changed')
    base=json.loads(BASELINE.read_text(encoding='utf-8'))
    for name,digest in base['evidence_sha256'].items():
        if name.startswith('sim/cpu_request_presample/board/task036_300_01/') and software.sha(ROOT/name)!=digest:
            raise ValueError('036 baseline UART evidence changed: '+name)
    return r

def task_metadata():
    r=load_review()
    return dict(candidate=r['candidate'],review_sha256=software.sha(REVIEW),
        candidate_cpu_git_sha256=r['candidate_cpu_git_sha256'],
        working_tree_cpu_at_review_sha256=r['working_tree_cpu_sha256'],
        working_tree_cpu_is_candidate=False,bitstream_sha256=r['bitstream_sha256'],
        observed_netlist_contains_EX_branch_registers=True,clock_hz=93750000,
        timing='OBSERVED_ALL_CONSTRAINTS_MET_WNS_PLUS_0_609NS',
        authorization='USER_REQUESTED_REVIEW_EXISTING_BITSTREAM_AND_DIRECT_BOARD_TRIAL',
        acceptance_scope='FIXED_P300_V300_APPLICATION_CRC_UART_TIMER_AND_13_COUNTERS',
        full_CPU_SoC_IRQ_reset_acceptance='NOT_REVIEWED',
        programmed_design='USER_SELECTED_NOT_INDEPENDENTLY_OBSERVED',
        baseline_task='036',baseline_review_sha256=software.sha(BASELINE),
        comparison_scope='EX_CPU_plus_037_decoder_vs_036_ID_CPU; no isolated 037 board baseline')

def verify_record(raw):
    if raw.get('ex_redirect_reviewed')!=task_metadata():
        raise ValueError('Reviewed EX implementation metadata differs')
    if raw['bitstream_local_file']['sha256']!=load_review()['bitstream_sha256']:
        raise ValueError('Log local bitstream differs from the reviewed artifact')
    out=software.namespace['verify_record'](raw)
    mode='P' if out['application_name']=='performance_300' else 'V'
    old=json.loads(BASELINE.read_text(encoding='utf-8'))['verified'][mode]['application']
    cur=out['application']
    assert cur['clock_hz']==old['clock_hz']==93750000
    comparison=dict(baseline_task='036',baseline_cycles=old['ticks'],baseline_seconds=old['seconds'],
        current_cycles=cur['ticks'],current_seconds=cur['seconds'],cycles_delta=cur['ticks']-old['ticks'],
        time_change_percent=100*(cur['ticks']/old['ticks']-1),
        throughput_change_percent=100*(old['ticks']/cur['ticks']-1),
        counter_deltas={k:v-old['counters'][k] for k,v in cur['counters'].items()},
        scope=task_metadata()['comparison_scope'])
    return dict(out,ex_redirect_reviewed=raw['ex_redirect_reviewed'],comparison_to_036=comparison)

def verify(path):
    return verify_record(json.loads(Path(path).read_text(encoding='utf-8')))

def print_comparison(out):
    c=out['comparison_to_036']
    print(f"VS036 cycles_delta={c['cycles_delta']:+d} time_change={c['time_change_percent']:+.6f}% "
          f"throughput_change={c['throughput_change_percent']:+.6f}%")

def main():
    if sys.argv[1:]==['--check-inputs']:
        require_inputs()
        print('Reviewed EX bitstream/metadata/BIN verified; reverted working-tree CPU is recorded separately; serial NOT_OPENED')
        return
    if '--verify-log' not in sys.argv:
        r=require_inputs()
        if '--bitstream' not in sys.argv:
            sys.argv+=['--bitstream',str(ROOT/r['bitstream_path'])]
        else:
            chosen=Path(sys.argv[sys.argv.index('--bitstream')+1])
            if software.sha(chosen)!=r['bitstream_sha256']:
                raise ValueError('Select the reviewed existing EX bitstream')
    code=inspect.getsource(software.measurement.main)
    marker='    a.log.parent.mkdir(parents=True, exist_ok=True)'
    prompt="    print('先下载你生成的FPGA位流。关闭串口助手；按KEY0并释放，等待DDR就绪。')"
    done="        print('RESULT: PASS measurement application')"
    assert all(code.count(s)==1 for s in (marker,prompt,done))
    code=code.replace(marker,"    result['ex_redirect_reviewed'] = task_metadata()\n"+marker)
    code=code.replace(prompt,"    print('先JTAG重新下载已复核封存的03:59 EX位流；关闭串口助手，KEY0释放并等DDR就绪，再Enter。当前工作树CPU是旧ID版本，不能据此重建或标记EX。')")
    code=code.replace(done,done+'\n        print_comparison(verified)')
    ns=dict(software.namespace,task_metadata=task_metadata,verify_record=verify_record,verify=verify,print_comparison=print_comparison)
    exec(compile(code,'<reviewed_EX_fixed_BIN_board_entry>','exec'),ns)
    ns['main']()

if __name__=='__main__': main()
