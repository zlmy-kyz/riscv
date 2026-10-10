"""User-operated PERF2B candidate only. --plan-only/--verify-log never open serial."""
from pathlib import Path
import argparse,hashlib,inspect,json,re,sys,time
ROOT=Path(__file__).resolve().parents[4]
sys.path.insert(0,str(ROOT/'tools/uart_loader/candidates/bsp_workflow'))
import upload
from application import require_manifest,parse_output
from plan import make_plan,rvld
sys.path.insert(0,str(ROOT/'sim/cpu_performance_2b'))
from check_output import check
GATE=ROOT/'sim/cpu_performance_2b/build/deployment_gate.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def require_gate(path):
    g=json.loads(GATE.read_text());assert g['status']=='PERF2B_PRE_BOARD_AUDIT_PASS'
    rel=Path(path).resolve().relative_to(ROOT).as_posix();assert g['manifests'].get(rel)==sha(path)
    for name,digest in g['input_sha256'].items():assert sha(ROOT/name)==digest,'changed candidate input: '+name
    for name,digest in g['evidence_sha256'].items():assert sha(ROOT/name)==digest,'changed evidence: '+name
    bit=ROOT/g['bitstream']['path'];assert sha(bit)==g['bitstream']['sha256']
    return g
def output_parser(info,data,board=False,elapsed=None):
    if info['kind']!='coremark':return parse_output(info,data,board=board,elapsed=elapsed)
    result=check(info,data,board=board,elapsed=elapsed)
    return dict(result,counter_status=result['status'],**result['crc'])
# Reuse the proven stop-and-wait transport; completion must include the frozen
# counter dump, rather than stopping at the earlier PORT_DONE line.
code=inspect.getsource(upload.execute).replace("b'PORT_DONE ticks=' in output and output.endswith(b'\\n')", "output.endswith(b'PERF2B_DONE\\n')")
assert "b'PERF2B_DONE\\n'" in code
namespace=dict(upload.__dict__,parse_output=output_parser);exec(code,namespace);execute=namespace['execute']
def verify(path):
    raw=json.loads(Path(path).read_text());assert raw['evidence_origin']=='ACTUAL_SERIAL' and raw['status']=='PERF2B_APPLICATION_BOARD_PASS'
    assert raw['serial_opened'] and raw['user_KEY0_confirmation'] and raw['retry_count']==0
    manifest=Path(raw['manifest_path']);g=require_gate(manifest);info=require_manifest(manifest)
    assert raw['manifest_sha256']==sha(manifest) and raw['gate_sha256']==sha(GATE)
    assert raw['bitstream']==g['bitstream'] and raw['application_info']==info
    rows=make_plan(info);assert len(rows)==len(raw['records'])
    for planned,row in zip(rows,raw['records']):
        assert row['result']=='PASS' and row['extra_rx_hex']=='' and row['written_bytes']==len(bytes.fromhex(planned['tx_hex']))
        assert all(row[k]==v for k,v in planned.items())
        assert row['decoded']==rvld.decode(bytes.fromhex(row['rx_hex']),bytes.fromhex(planned['expected_hex']))
    app=raw['application'];assert app['result']=='PASS' and app['extra_rx_hex']==''
    parsed=output_parser(info,bytes.fromhex(app['rx_hex']),board=True,elapsed=app['seconds']);assert parsed==app['parsed']
    if info['kind']=='coremark' and info['iterations']==60:
        pre=raw['crc_prerequisite'];assert sha(pre['path'])==pre['sha256']
        short=verify(pre['path']);assert short['info']['mode']==info['mode'] and short['info']['iterations']==1
        assert short['gate_sha256']==sha(GATE) and short['bitstream']==g['bitstream']
    return dict(status='PERF2B_ACTUAL_BOARD_INDEPENDENTLY_VERIFIED',info=info,application=parsed,
        responses=len(rows),run_count=sum(bool(r.get('run')) for r in rows),gate_sha256=sha(GATE),bitstream=g['bitstream'])
def main():
    p=argparse.ArgumentParser();p.add_argument('--application',choices=['hello','crc32','performance_1','validation_1','performance_60','validation_60'])
    p.add_argument('--log',type=Path);p.add_argument('--crc-log',type=Path);p.add_argument('--plan-only',action='store_true')
    p.add_argument('--verify-log',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
    if a.verify_log:
        assert a.output is not None and not a.output.exists() and not a.application
        result=verify(a.verify_log);a.output.parent.mkdir(parents=True,exist_ok=True)
        with a.output.open('x') as f:json.dump(result,f,indent=2)
        print('RESULT: PASS offline actual log audit; serial not opened');return
    assert a.application and a.log and not a.log.exists()
    g=json.loads(GATE.read_text());manifest=ROOT/g['applications'][a.application]
    g=require_gate(manifest);info=require_manifest(manifest);rows=make_plan(info)
    result=dict(status='PERF2B_PLAN_ONLY' if a.plan_only else 'RUNNING',evidence_origin='OFFLINE_PLAN_NOT_BOARD' if a.plan_only else 'ACTUAL_SERIAL',
        application_info=info,manifest_path=manifest.as_posix(),manifest_sha256=sha(manifest),gate_sha256=sha(GATE),bitstream=g['bitstream'],
        port='COM11',baud=115200,retry_count=0,no_automatic_retry=True,serial_opened=False,records=[],application={},
        FPGA_programming_independently_observed=False,KEY0_independently_observed=False)
    if not a.plan_only and info['kind']=='coremark' and info['iterations']==60:
        assert a.crc_log,'Matching measurement BIN short CRC log is required first'
        short=verify(a.crc_log);assert short['info']['mode']==info['mode'] and short['info']['iterations']==1
        result['crc_prerequisite']=dict(path=a.crc_log.resolve().as_posix(),sha256=sha(a.crc_log))
    a.log.parent.mkdir(parents=True,exist_ok=True)
    with a.log.open('x') as f:json.dump(result,f,indent=2)
    if a.plan_only:
        result['plan']=rows;a.log.write_text(json.dumps(result,indent=2)+'\n')
        print('RESULT: PASS offline plan; responses=',len(rows),'RUN=1; serial not opened');return
    print('Use candidate bitstream:',ROOT/g['bitstream']['path'])
    input('Close serial terminal. Press KEY0, release, wait for DDR ready, then Enter: ')
    result['user_KEY0_confirmation']=True
    try:
        import serial
        with serial.Serial('COM11',115200,bytesize=8,parity='N',stopbits=1,timeout=.05,write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as port:
            result['serial_opened']=True;time.sleep(.25)
            execute(port,info,result['records'],result['application'],board=True)
        result['status']='PERF2B_APPLICATION_BOARD_PASS'
        print(bytes.fromhex(result['application']['rx_hex']).decode('ascii'),end='')
    except BaseException as e:result.update(status='FAIL',error=str(e));raise
    finally:a.log.write_text(json.dumps(result,indent=2)+'\n')
    audited=verify(a.log)
    print('RESULT: PASS',audited['status'])
if __name__=='__main__':main()
