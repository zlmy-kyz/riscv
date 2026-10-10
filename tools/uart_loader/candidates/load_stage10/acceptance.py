"""User-operated COM11 real program LOAD acceptance; never sends VERIFY/RUN."""
from pathlib import Path
import argparse,hashlib,json,sys,time
from cases import cases,PROGRAM
from protocol import decode
ROOT=Path(__file__).resolve().parents[4];BUILD=ROOT/'sim/uart_loader/build/load_stage10'
IMAGE=ROOT/'tests/uart_loader/candidates/load_stage10/build'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def require_gate():
    p=BUILD/'deployment_gate.json';g=json.loads(p.read_text())
    if g['status']!='STAGE10_SIM_PASS':raise ValueError('stage10 simulation gate not PASS')
    for name,h in g['input_sha256'].items():
        if sha(ROOT/name)!=h:raise ValueError('frozen input changed: '+name)
    return g,sha(p)

def read_exact(port):
    raw=bytearray();deadline=time.monotonic()+5
    while len(raw)<60 and time.monotonic()<deadline:
        part=port.read(60-len(raw))
        if part:raw+=part
    return bytes(raw)

def run_cases(port,selected,records,quiet=time.sleep,progress=None):
    if port.in_waiting:raise ValueError('unexpected startup RX; reset first, no automatic flush')
    for case in selected:
        record=dict(case,result='INCOMPLETE');records.append(record);start=time.monotonic()
        try:
            tx=bytes.fromhex(case['tx_hex']);record['written_bytes']=port.write(tx)
            if record['written_bytes']!=len(tx):raise ValueError('short serial write')
            raw=read_exact(port);record['rx_hex']=raw.hex();record['seconds']=time.monotonic()-start
            record['decoded']=decode(raw,bytes.fromhex(case['expected_hex']))
            quiet(.002)
            extra=port.read(port.in_waiting) if port.in_waiting else b'';record['extra_rx_hex']=extra.hex()
            if extra:raise ValueError('unexpected extra RX/application output')
            record['result']='PASS'
            if progress:progress(case)
        except BaseException as error:
            record.update(result='FAIL',error=str(error),seconds=time.monotonic()-start);raise
    return len(records)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',default='COM11')
    p.add_argument('--log',type=Path,required=True);p.add_argument('--plan-only',action='store_true')
    p.add_argument('--bitstream',type=Path);a=p.parse_args()
    assert a.port=='COM11';assert not a.log.exists(),'preserve logs; use a new filename'
    selected=cases('native');manifest=json.loads((PROGRAM.parent/'manifest.json').read_text())
    metadata=dict(stage='LOAD_STAGE10_REAL_PROGRAM',port=a.port,baud=115200,planned_frames=len(selected),
        program_bytes=manifest['bytes'],program_crc32=manifest['crc32'],program_sha256=sha(PROGRAM),
        program_manifest_sha256=sha(PROGRAM.parent/'manifest.json'),no_automatic_retry=True,retry_count=0,
        formal_load_implemented=True,formal_verify_implemented=False,run_implemented=False,program_execute=False,
        state='LOADED_UNVERIFIED',reset_independently_observed=False,downloaded_bitstream_identity=None,
        image_sha256=json.loads((IMAGE/'manifest.json').read_text())['sha256'],
        pc_input_sha256={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))})
    if a.bitstream:metadata['downloaded_bitstream_identity']=dict(path=a.bitstream.resolve().as_posix(),sha256=sha(a.bitstream))
    a.log.parent.mkdir(parents=True,exist_ok=True)
    if a.plan_only:
        metadata.update(status='STAGE10_BOARD_PLAN',board_result='NOT_TESTED',evidence_origin='OFFLINE_PLAN_NOT_BOARD',serial_opened=False)
        with a.log.open('x',encoding='utf8') as f:json.dump(metadata,f,indent=2)
        print('PLAN ONLY:',manifest['bytes'],'byte real BIN;',len(selected),'responses; no serial opened');return
    g,gate_sha=require_gate();metadata.update(gate_sha256=gate_sha,status='RUNNING',board_result='NOT_COMPLETE',records=[])
    with a.log.open('x',encoding='utf8') as f:json.dump(metadata,f,indent=2)
    started=time.monotonic()
    try:
        import serial
        with serial.Serial(a.port,115200,bytesize=8,parity='N',stopbits=1,timeout=.25,write_timeout=2,
                           xonxoff=False,rtscts=False,dsrdtr=False) as port:
            time.sleep(.25)
            count=run_cases(port,selected,metadata['records'],progress=lambda c:print('PASS',c['name'],flush=True))
        assert count==len(selected)
        metadata.update(status='STAGE10_REAL_PROGRAM_BOARD_PASS',board_result='PASS_LOAD_ONLY_UNVERIFIED',
                        frames=count,crc_errors=0,uart_errors=0)
        print('RESULT: PASS stage10 real program LOAD; LOADED_UNVERIFIED; diagnostic DDR CRC matches; no Hello/RUN',flush=True)
    except BaseException as error:
        metadata.update(status='FAIL',board_result='NOT_COMPLETE',error=str(error));raise
    finally:
        metadata['seconds']=time.monotonic()-started
        a.log.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
