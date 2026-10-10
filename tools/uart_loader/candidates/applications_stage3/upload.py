"""One validated BIN/manifest on the unchanged successful Loader bitstream."""
from pathlib import Path
import argparse,hashlib,json,time,sys
from application import ROOT,require_manifest,parse_output,SECOND
from plan import make_plan,rvld
GATE=ROOT/'sim/uart_loader/build/applications_stage3/deployment_gate.json'
BIT=ROOT/'sim/uart_loader/build/verify_run_hello/pds_candidate/generate_bitstream/board_top.sbit'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def require_gate(manifest):
    gate=json.loads(GATE.read_text());assert gate['status']=='SAME_LOADER_APPLICATIONS_SIM_PASS'
    rel=Path(manifest).resolve().relative_to(ROOT).as_posix()
    assert rel in gate['manifests'] and sha(Path(manifest))==gate['manifests'][rel]
    for p,h in gate['input_sha256'].items():assert sha(ROOT/p)==h,'frozen input changed: '+p
    assert sha(BIT)==gate['successful_bitstream_sha256']
    return sha(GATE)

def read_exact(port,n,timeout=5):
    data=bytearray();end=time.monotonic()+timeout
    while len(data)<n and time.monotonic()<end:
        part=port.read(n-len(data))
        if part:data+=part
    if len(data)!=n:raise ValueError('response timeout/short read')
    return bytes(data)

def execute(port,info,records,application_record,*,quiet=time.sleep,progress=None,board=True):
    if port.in_waiting:raise ValueError('unexpected startup RX; reset first; no automatic flush')
    for request in make_plan(info):
        row=dict(request,result='INCOMPLETE',extra_rx_hex='');records.append(row);start=time.monotonic()
        try:
            tx=bytes.fromhex(request['tx_hex']);row['written_bytes']=port.write(tx)
            if row['written_bytes']!=len(tx):raise ValueError('short serial write')
            raw=read_exact(port,60);row['rx_hex']=raw.hex();row['decoded']=rvld.decode(raw,bytes.fromhex(request['expected_hex']))
            if not request.get('run'):
                quiet(.002);extra=port.read(port.in_waiting) if port.in_waiting else b'';row['extra_rx_hex']=extra.hex()
                if extra:raise ValueError('unexpected UART bytes before next request')
            row['seconds']=time.monotonic()-start;row['result']='PASS'
            if progress:progress(request)
        except BaseException as e:row.update(result='FAIL',error=str(e),seconds=time.monotonic()-start);raise
    start=time.monotonic();output=bytearray();deadline=start+40
    try:
        while time.monotonic()<deadline:
            data=port.read(port.in_waiting or 1)
            if data:output+=data;application_record['rx_hex']=output.hex()
            if len(output)>8192:raise ValueError('excess application UART output')
            complete=(len(output)>=len(SECOND)) if info['kind']=='second' else (
                b'PORT_DONE ticks=' in output and output.endswith(b'\n'))
            if complete:break
        else:raise ValueError('application deadline (40s, below timer period)')
        elapsed=time.monotonic()-start
        parsed=parse_output(info,bytes(output),board=board,elapsed=elapsed)
        quiet(.1);extra=port.read(port.in_waiting) if port.in_waiting else b''
        application_record.update(rx_hex=output.hex(),extra_rx_hex=extra.hex(),seconds=elapsed,parsed=parsed)
        if extra:raise ValueError('extra/duplicate application output')
        application_record['result']='PASS'
        return parsed
    except BaseException as e:
        application_record.update(result='FAIL',rx_hex=output.hex(),seconds=time.monotonic()-start,error=str(e));raise

def main():
    p=argparse.ArgumentParser(description=__doc__);group=p.add_mutually_exclusive_group(required=True)
    group.add_argument('--manifest',type=Path)
    group.add_argument('--application',choices=['second','performance_1','validation_1','performance_60','validation_60'])
    p.add_argument('--port',default='COM11');p.add_argument('--log',type=Path,required=True);p.add_argument('--plan-only',action='store_true')
    p.add_argument('--crc-log',type=Path,help='Required for 60 iterations: actual same-mode 1-iteration CRC log')
    a=p.parse_args()
    if a.application:
        a.manifest=ROOT/('tests/uart_loader/program_second/build/manifest.json' if a.application=='second' else
                        f'tests/uart_loader/coremark_uart/build/{a.application}/manifest.json')
    assert a.port=='COM11' and not a.log.exists(),'COM11 only; preserve existing log'
    info=require_manifest(a.manifest);rows=make_plan(info)
    result=dict(status='APPLICATION_PLAN_ONLY' if a.plan_only else 'RUNNING',
        evidence_origin='OFFLINE_PLAN_NOT_BOARD' if a.plan_only else 'ACTUAL_SERIAL',
        manifest_path=a.manifest.resolve().as_posix(),manifest_sha256=sha(a.manifest),application_info=info,
        planned_responses=len(rows),port=a.port,baud=115200,retry_count=0,no_automatic_retry=True,
        successful_bitstream_identity=dict(path=BIT.as_posix(),sha256=sha(BIT)),
        reset_independently_observed=False,JTAG_programming_independently_observed=False,
        records=[],application=dict(result='NOT_STARTED'),board_result='NOT_TESTED')
    a.log.parent.mkdir(parents=True,exist_ok=True)
    if a.plan_only:
        result['serial_opened']=False;result['plan']=rows
        with a.log.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
        print('PLAN ONLY',len(rows),'responses; one RUN; no serial opened');return
    result['gate_sha256']=require_gate(a.manifest)
    if info['kind']=='coremark' and info['iterations']==60:
        assert a.crc_log is not None,'Run the matching 1-iteration CRC check first; pass --crc-log'
        sys.path.insert(0,str(ROOT/'sim/uart_loader/applications_stage3'))
        from check_board import verify
        short=verify(a.crc_log)
        assert short['application_info']['kind']=='coremark' and short['application_info']['mode']==info['mode']
        assert short['application_info']['iterations']==1 and short['board_result']=='COREMARK_CRC_FUNCTIONAL_PASS'
        assert short['gate_sha256']==result['gate_sha256'] and short['successful_bitstream_identity']==result['successful_bitstream_identity']
        result['crc_prerequisite']=dict(path=a.crc_log.resolve().as_posix(),sha256=sha(a.crc_log),board_result=short['board_result'])
    with a.log.open('x',encoding='utf-8') as f:json.dump(result,f,indent=2)
    start=time.monotonic()
    try:
        import serial
        with serial.Serial(a.port,115200,bytesize=8,parity='N',stopbits=1,timeout=.05,write_timeout=2,
                           xonxoff=False,rtscts=False,dsrdtr=False) as port:
            time.sleep(.25)
            execute(port,info,result['records'],result['application'],progress=lambda c:print('PASS',c['name'],flush=True))
        result.update(status='SAME_LOADER_APPLICATION_BOARD_PASS',board_result=result['application']['parsed']['status'])
        print(bytes.fromhex(result['application']['rx_hex']).decode('ascii'),end='',flush=True)
        print('RESULT: PASS',result['board_result'],'same Loader bitstream',flush=True)
    except BaseException as e:result.update(status='FAIL',board_result='NOT_COMPLETE',error=str(e));raise
    finally:
        result['seconds']=time.monotonic()-start;a.log.write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
