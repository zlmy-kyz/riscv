"""Review existing fixed-layout P and V first-PING failure; host diagnostic checks only."""
from pathlib import Path
import importlib.util
import json
import sys
from unittest.mock import patch
HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0,str(ROOT/'tests/cpu_performance_2b'))
from perf27_software import sha

def main():
    assert not (HERE/'review.json').exists(), 'Preserve review'
    folder = ROOT/'sim/cpu_cache_perf/board/perf27_fixed_300_01'
    ppath,vpath,ipath = [folder/n for n in ['performance_300.json','validation_300.json','identity.json']]
    before = {str(p.relative_to(ROOT)):sha(p) for p in [ppath,vpath,ipath]}
    p,v,ident = [json.loads(f.read_text(encoding='utf-8')) for f in [ppath,vpath,ipath]]
    p_review = json.loads((HERE/'performance_review.json').read_text(encoding='utf-8'))
    assert p_review['application'] == p['application']['parsed']
    assert p_review['responses'] == 295 and p_review['run_count'] == 1
    assert p['application']['extra_rx_hex'] == '' and p_review['application']['crcfinal'] == '5275'
    assert v['status']=='FAIL' and v['serial_opened'] and v['user_KEY0_confirmation']
    assert len(v['records']) == 1 and not v['application']
    row = v['records'][0]
    assert row['name']=='PING_fresh_loader' and row['result']=='FAIL' and row['written_bytes']==36
    assert row['error']=='response timeout/short read' and 'rx_hex' not in row
    assert not any(x.get('run') for x in v['records'])
    tool_path = ROOT/'tools/uart_loader/candidates/perf_2b/run_perf27_measurement.py'
    assert sha(HERE/'run_perf27_measurement_before.py') == ident['sha256'][str(tool_path.relative_to(ROOT)).replace('\\','/')]
    for n,h in ident['sha256'].items():
        if n != tool_path.relative_to(ROOT).as_posix(): assert sha(ROOT/n)==h,n
    spec = importlib.util.spec_from_file_location('perf27_host_diagnostics',tool_path)
    tool = importlib.util.module_from_spec(spec); spec.loader.exec_module(tool)
    class Port:
        def __init__(self,parts): self.parts=list(parts); self.requests=[]
        def read(self,n):
            self.requests.append(n)
            return self.parts.pop(0) if self.parts else b''
    record = {}
    port = Port([b'a'*17,b'b'*43])
    with patch.object(tool.time,'monotonic',side_effect=[0,0,0]):
        assert tool.read_response(port,60,record)==b'a'*17+b'b'*43
    assert record['received_response_bytes']==record['expected_response_bytes']==60
    assert port.requests == [60,43]
    host_checks = ['fragmented_60_byte_success']
    for data in [b'',b'partial']:
        record = {}
        with patch.object(tool.time,'monotonic',side_effect=[0,0,6]):
            try: tool.read_response(Port([data]),60,record)
            except ValueError as error:
                assert str(error)==f'response timeout/short read: received {len(data)}/60 bytes'
            else: raise AssertionError('Short read unexpectedly accepted')
        assert record['rx_hex']==data.hex() and record['received_response_bytes']==len(data)
        assert record['expected_response_bytes']==60
        host_checks.append('record_short_'+str(len(data))+'_of_60')
    planpath = ROOT/'sim/cpu_cache_perf/board/perf27_fixed_v_jtag_plan_01/validation_300.json'
    plan = json.loads(planpath.read_text(encoding='utf-8'))
    assert not plan['serial_opened'] and len(plan['plan'])==295 and sum(bool(x.get('run')) for x in plan['plan'])==1
    assert plan['bitstream_local_file'] == p['bitstream_local_file']
    requested = json.loads(planpath.with_name('identity.json').read_text(encoding='utf-8'))
    assert requested['requested_reset_method']=='jtag'
    baseline = json.loads((ROOT/'sim/cpu_cache_perf/board/task042_fixed_pv_300_01/performance_300.json').read_text())['application']['parsed']
    a = p_review['application']
    assert all(sha(ROOT/n)==h for n,h in before.items())
    report = dict(status='FIXED_LAYOUT_P_APPLICATION_PASS_V_NOT_LOADED_FIRST_PING_TIMEOUT',
        performance=a, performance_RVLD_responses=295, performance_RUN_count=1,
        delta_vs_original_fixed_P_cycles=a['ticks']-baseline['ticks'],
        delta_vs_original_fixed_P_percent=100*(a['ticks']-baseline['ticks'])/baseline['ticks'],
        V_failure=dict(stage='FIRST_PING',request_written_bytes=36,expected_response_bytes=60,
            received_response_bytes='UNKNOWN_OLD_HELPER_DISCARDED_PARTIAL_DATA',
            actual_seconds=row['seconds'],application_loaded=False,application_RUN=False),
        diagnosis='Loader fresh-ready state was not established by V first PING. Consistent with existing KEY0/boot recovery issue; exact hardware/serial cause not proven.',
        host_fix='Only PERF27 host entry: retain partial/zero RX on the original 5s deadline; no auto retry/flush. Explicit jtag reset mode gives KEY0-released cold-loader prompt and records self-reported method.',
        host_check_cases=host_checks,host_source_before_sha256=sha(HERE/'run_perf27_measurement_before.py'),
        host_source_after_sha256=sha(tool_path),evidence_sha256=before,
        next_action='User reprograms the SAME existing bitstream via JTAG, KEY0 held released, wait DDR ready; V-only new directory with --reset-method jtag. No P repeat, PDS rebuild or BIN/RTL change.',
        plan_sha256=sha(planpath),serial_opened_by_review=False,HDL_started=False,PDS_started=False,
        scope='P300 application CRC/protocol/27 counts accepted; not formal >=10s benchmark or complete041/042/KEY0 acceptance.')
    (HERE/'review.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['status'])
    print('P',a['ticks'],a['seconds'],'delta %',report['delta_vs_original_fixed_P_percent'])
    print('Host-only partial RX checks passed; same-bitstream V-only offline plan prepared; serial not opened')
if __name__=='__main__': main()
