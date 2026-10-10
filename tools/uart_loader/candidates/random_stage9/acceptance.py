"""Stage9 user-operated COM11 diagnostic stress; never executes downloaded bytes."""
from pathlib import Path
import argparse,hashlib,json,sys,time
from cases import corpus,Builder
from protocol import decode,LIMIT
ROOT=Path(__file__).resolve().parents[4]
IMAGE=ROOT/'tests/uart_loader/candidates/random_stage9/build'
BUILD=ROOT/'sim/uart_loader/build/random_stage9'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()

def board_cases(directory):
    directory=Path(directory);plan=corpus(directory,'board');builder=Builder()
    builder.add('start_ping')
    for entry in plan['images']:
        raw=(directory/entry['file']).read_bytes()
        builder.image(raw,f"image_{entry['index']:04d}_{entry['bytes']}")
        builder.cases[-1]['completed_image']=entry
    builder.add('finish_ping')
    return plan,builder.cases

def require_gate():
    path=BUILD/'deployment_gate.json';gate=json.loads(path.read_text())
    assert gate['status']=='STAGE9_SIM_PASS' and gate['board_result']=='NOT_TESTED'
    identity=json.loads((IMAGE/'manifest.json').read_text())['sha256'];assert identity==gate['image_sha256']
    for name,h in gate['input_sha256'].items():assert sha(ROOT/name)==h,name
    for name,h in identity.items():assert sha(IMAGE/name)==h,name
    return identity,sha(path)

def read_exact(port,length):
    result=bytearray();deadline=time.monotonic()+5
    while len(result)<length and time.monotonic()<deadline:
        part=port.read(length-len(result))
        if part:result+=part
    return bytes(result)

def run_cases(port,cases,records,quiet=time.sleep,progress=None):
    if port.in_waiting:raise ValueError('unexpected startup RX; reset board first, no automatic flush')
    images=0;payload=0
    for case in cases:
        record=dict(case,result='INCOMPLETE');records.append(record)
        start=time.monotonic();raw=bytes.fromhex(case['tx_hex'])
        try:
            count=port.write(raw);record['written_bytes']=count
            if count!=len(raw):raise ValueError('short serial write')
            rx=read_exact(port,60);record['rx_hex']=rx.hex();record['seconds']=time.monotonic()-start
            record['decoded']=decode(rx,case)
            quiet(.002)
            extra=port.read(port.in_waiting) if port.in_waiting else b'';record['extra_rx_hex']=extra.hex()
            if extra:raise ValueError('extra UART response bytes')
            record['result']='PASS'
            if case.get('completed_image'):
                images+=1;payload+=case['completed_image']['bytes']
                if progress:progress(images,case['completed_image'],payload)
        except BaseException as error:
            record['seconds']=time.monotonic()-start;record['result']='FAIL';record['error']=str(error);raise
    return images,payload

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port',default='COM11');parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--corpus',type=Path,default=BUILD/'corpus/board');parser.add_argument('--plan-only',action='store_true')
    parser.add_argument('--bitstream',type=Path);args=parser.parse_args()
    assert args.port=='COM11','this validated board plan is for COM11'
    assert not args.log.exists(),'use a new log name; successful and failed evidence must not be overwritten'
    plan,cases=board_cases(args.corpus)
    metadata=dict(stage='RANDOM_STAGE9_DIAGNOSTIC',port=args.port,baud=115200,corpus_sha256=sha(args.corpus/'manifest.json'),
                  corpus_path=args.corpus.resolve().as_posix(),seed=plan['seed'],planned_images=plan['image_count'],
                  planned_payload_bytes=plan['payload_bytes'],planned_frames=len(cases),no_automatic_retry=True,retry_count=0,
                  formal_load_verify_run_implemented=False,random_execute=False,reset_independently_observed=False,
                  reset_evidence='USER_REQUESTED_KEY0_BEFORE_THIS_RUN',downloaded_bitstream_identity=None)
    metadata['image_sha256']=json.loads((IMAGE/'manifest.json').read_text())['sha256']
    metadata['pc_input_sha256']={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))}
    if args.bitstream:metadata['downloaded_bitstream_identity']=dict(path=args.bitstream.resolve().as_posix(),sha256=sha(args.bitstream))
    args.log.parent.mkdir(parents=True,exist_ok=True)
    if args.plan_only:
        metadata.update(status='STAGE9_BOARD_PLAN',board_result='NOT_TESTED',evidence_origin='OFFLINE_PLAN_NOT_BOARD',serial_opened=False)
        with args.log.open('x',encoding='utf8') as f:f.write(json.dumps(metadata,indent=2)+'\n')
        print(f"PLAN ONLY: {plan['image_count']} images, {plan['payload_bytes']} payload bytes, {len(cases)} frames; no serial opened")
        return
    identity,gate_sha=require_gate();metadata.update(image_sha256=identity,gate_sha256=gate_sha,status='RUNNING',board_result='NOT_COMPLETE',records=[])
    with args.log.open('x',encoding='utf8') as f:f.write(json.dumps(metadata,indent=2)+'\n')
    start=time.monotonic()
    try:
        import serial
        with serial.Serial(args.port,115200,bytesize=8,parity='N',stopbits=1,timeout=.25,write_timeout=2,
                           xonxoff=False,rtscts=False,dsrdtr=False) as port:
            time.sleep(.25)
            def progress(number,entry,payload):
                tail='PASS' if entry['bytes']+3<=LIMIT else 'WINDOW_END_NO_BOARD_PROBE'
                print(f"{number:04d}/{plan['image_count']} IMAGE bytes={entry['bytes']} PC=DDR={entry['crc32']:08X} tail_guard={tail} elapsed={time.monotonic()-start:.3f}s",flush=True)
            images,payload=run_cases(port,cases,metadata['records'],progress=progress)
        assert images==plan['image_count'] and payload==plan['payload_bytes'] and (images>=1000 or payload>=16*1024*1024)
        metadata.update(status='STAGE9_DIAGNOSTIC_BOARD_PASS',board_result='PASS_RANDOM_DIAGNOSTIC_ONLY',
                        completed_images=images,payload_bytes=payload,frames=len(cases),crc_errors=0,uart_errors=0,
                        bytes_per_second=payload/(time.monotonic()-start))
        print(f'RESULT: PASS stage9 {images} random/boundary images, {payload} bytes; zero errors/retries; no RUN',flush=True)
    except BaseException as error:
        metadata.update(status='FAIL',board_result='NOT_COMPLETE',error=str(error));print('RESULT: FAIL stage9:',error,file=sys.stderr,flush=True);raise
    finally:
        metadata['seconds']=time.monotonic()-start
        args.log.write_text(json.dumps(metadata,indent=2)+'\n',encoding='utf8')

if __name__=='__main__':main()
