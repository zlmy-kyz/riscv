"""Single combined board acceptance. No automatic retries; RUN only once."""
import argparse,hashlib,json,time
from pathlib import Path
from board_cases import board_cases
from cases import PROGRAM
from protocol import decode
ROOT=Path(__file__).resolve().parents[4]
IMAGE=ROOT/'tests/uart_loader/candidates/verify_run_hello/build'
GATE=ROOT/'sim/uart_loader/build/verify_run_hello/deployment_gate.json'
HELLO=b'Hello World\r\n'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()


def require_gate():
    g=json.loads(GATE.read_text())
    assert g['status']=='COMBINED_SIM_PASS', 'concentrated simulation must pass first'
    for rel,h in g['input_sha256'].items():
        assert sha(ROOT/rel)==h, 'frozen input changed: '+rel
    return sha(GATE)


def read_exact(port,size):
    raw=bytearray();deadline=time.monotonic()+5
    while len(raw)<size and time.monotonic()<deadline:
        part=port.read(size-len(raw))
        if part:raw+=part
    return bytes(raw)


def run_cases(port,selected,records,quiet=time.sleep,progress=None):
    if port.in_waiting:raise ValueError('unexpected startup RX; reset first; no automatic flush')
    for case in selected:
        row=dict(case,result='INCOMPLETE');records.append(row);start=time.monotonic()
        try:
            tx=bytes.fromhex(case['tx_hex']);row['written_bytes']=port.write(tx)
            if row['written_bytes']!=len(tx):raise ValueError('short serial write')
            raw=read_exact(port,60);row['rx_hex']=raw.hex()
            row['decoded']=decode(raw,bytes.fromhex(case['expected_hex']))
            row['application_rx_hex']=''
            if case.get('run'):
                app=read_exact(port,len(HELLO));row['application_rx_hex']=app.hex()
                if app!=HELLO:raise ValueError('exact Hello World/data/BSS confirmation missing')
            quiet(.02 if case.get('run') else .002)
            extra=port.read(port.in_waiting) if port.in_waiting else b'';row['extra_rx_hex']=extra.hex()
            if extra:raise ValueError('unexpected extra UART bytes')
            row['result']='PASS';row['seconds']=time.monotonic()-start
            if progress:progress(case)
        except BaseException as error:
            row.update(result='FAIL',error=str(error),seconds=time.monotonic()-start);raise
    return len(records)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',default='COM11')
    p.add_argument('--log',type=Path,required=True);p.add_argument('--plan-only',action='store_true')
    p.add_argument('--bitstream',type=Path);a=p.parse_args()
    assert a.port=='COM11';assert not a.log.exists(),'preserve log; use a new filename'
    selected=board_cases();app=json.loads((PROGRAM.parent/'manifest.json').read_text())
    data=dict(status='COMBINED_BOARD_PLAN' if a.plan_only else 'RUNNING',board_result='NOT_TESTED',
              evidence_origin='OFFLINE_PLAN_NOT_BOARD' if a.plan_only else 'ACTUAL_SERIAL',
              port=a.port,baud=115200,retry_count=0,no_automatic_retry=True,
              planned_frames=len(selected),program_bytes=app['bytes'],program_crc32=app['crc32'],
              program_sha256=sha(PROGRAM),image_sha256=json.loads((IMAGE/'manifest.json').read_text())['sha256'],
              records=[],formal_verify_implemented=True,run_implemented=True,hello_expected_hex=HELLO.hex(),
              downloaded_bitstream_identity=None,reset_independently_observed=False,
              physical_DDR_damage_injection_on_board=False)
    if a.bitstream:data['downloaded_bitstream_identity']=dict(path=a.bitstream.resolve().as_posix(),sha256=sha(a.bitstream))
    a.log.parent.mkdir(parents=True,exist_ok=True)
    if a.plan_only:
        data['serial_opened']=False
        with a.log.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
        print('PLAN ONLY',len(selected),'responses; one RUN; no serial opened');return
    data['gate_sha256']=require_gate()
    with a.log.open('x',encoding='utf-8') as f:json.dump(data,f,indent=2)
    start=time.monotonic()
    try:
        import serial
        with serial.Serial(a.port,115200,bytesize=8,parity='N',stopbits=1,timeout=.25,
                           write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as port:
            time.sleep(.25)
            count=run_cases(port,selected,data['records'],progress=lambda c:print('PASS',c['name'],flush=True))
        assert count==len(selected)
        data.update(status='COMBINED_BOARD_PASS',board_result='PASS_VERIFY_RUN_DDR_HELLO',
                    frames=count,program_execute=True,hello_received_hex=HELLO.hex(),
                    expected_nacks=sum(bool(c['status']&0x8000) for c in selected))
        print('RESULT: PASS combined LOAD -> VERIFY -> RUN -> Hello World',flush=True)
    except BaseException as error:
        data.update(status='FAIL',board_result='NOT_COMPLETE',error=str(error));raise
    finally:
        data['seconds']=time.monotonic()-start
        a.log.write_text(json.dumps(data,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':main()
