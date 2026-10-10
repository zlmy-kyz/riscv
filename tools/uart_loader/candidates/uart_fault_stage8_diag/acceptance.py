"""Stage8 diagnostic board acceptance: checked BREAK, ACK-time wire flood, raw UART flags."""
import argparse,hashlib,json,os,sys,time
from pathlib import Path
from cases import board_cases,CRC,BREAK_SECONDS
from protocol import decode_response,expected_response
ROOT=Path(__file__).resolve().parents[4]
IMAGE=ROOT/'tests/uart_loader/candidates/uart_fault_stage8_diag/build'
GATE=ROOT/'sim/uart_loader/build/uart_fault_stage8_diag/deployment_gate.json'

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def image_identity():
    saved=json.loads((IMAGE/'manifest.json').read_text(encoding='utf8'))['sha256']
    actual={name:sha(IMAGE/name) for name in saved}
    if actual!=saved:raise RuntimeError('candidate ELF/DAT differs from build manifest')
    return actual

def require_gate(identity):
    gate=json.loads(GATE.read_text(encoding='utf8'))
    if gate['status']!='STAGE8_UART_DIAGNOSTIC_SIM_PASS' or gate['image_sha256']!=identity:
        raise RuntimeError('diagnostic candidate is not simulation-approved')
    for path,digest in gate['input_sha256'].items():
        if sha(ROOT/path)!=digest:raise RuntimeError('validated input changed: '+path)
    return sha(GATE)

def checked_break(port):
    # pySerial Windows setter does not check the native BOOL. Check it explicitly.
    if os.name!='nt':raise RuntimeError('this controlled BREAK implementation requires Windows')
    import ctypes
    from serial import win32
    start=time.monotonic()
    if not win32.SetCommBreak(port._port_handle):raise ctypes.WinError()
    try:time.sleep(BREAK_SECONDS)
    finally:
        if not win32.ClearCommBreak(port._port_handle):raise ctypes.WinError()
    duration=time.monotonic()-start
    if not .002<=duration<.075:raise RuntimeError('BREAK timing outside controlled 2..75ms window')
    return dict(api='Windows SetCommBreak/ClearCommBreak',set_success=True,clear_success=True,hold_seconds=duration)

def exercise(port,selected,report,save,timeout=5,clock=time.monotonic,break_fn=checked_break,emit=print):
    injection_start=None
    for index,c in enumerate(selected):
        response=bytearray();start=clock()
        record=dict(**c,rx_hex='',seconds=0,result='RUNNING')
        report['records'].append(record);save()
        try:
            if c['name']=='wire_break':
                injection_start=start;record['break_control']=break_fn(port)
            elif c['name']!='wire_fifo_overflow':
                data=bytes.fromhex(c['tx_hex'])
                if c['name']=='wire_flood_trigger_ping':injection_start=start
                if port.write(data)!=len(data):raise RuntimeError('short serial write')
                port.flush()
            while len(response)<60 and clock()-start<timeout:
                response.extend(port.read(60-len(response)))
            record.update(rx_hex=response.hex(),seconds=clock()-start)
            flags=c.get('uart_error_flags',0)
            decoded=decode_response(bytes(response),c['seq'],c['cmd'],expected_crc=c.get('expected_crc',CRC),uart_error_flags=flags)
            record['decoded']=decoded
            expected=expected_response(c['seq'],c['cmd'],c['status'],CRC if c.get('crc_read') else 0,flags)
            if bytes(response)!=expected:raise RuntimeError('raw response differs from expected fields/status/UART cause')
            if c['name']=='bad_header_crc' and record['seconds']<.095:raise RuntimeError('NACK before header recovery')
            if c.get('negative') and c['status']==0x8004 and record['seconds']<.195:raise RuntimeError('early receive-timeout NACK')
            if flags:
                record['seconds_since_injection']=clock()-injection_start
                if record['seconds_since_injection']<.095:raise RuntimeError('UART NACK before 100ms recovery')
            # Flood intentionally generates two responses. Preserve queued NACK for next record.
            if c['name']!='wire_flood_trigger_ping':
                extra=port.read(1)
                if extra:record['extra_rx_hex']=extra.hex();raise RuntimeError('unexpected extra UART response/data')
            record['result']='PASS';save()
            suffix=f' raw_UART=0x{flags:02X}' if flags else ''
            emit(f'{index+1:03d}/{len(selected)} {c["name"]}: '+('ACK' if c['status']==0 else f'NACK 0x{c["status"]:04X}')+f' PASS {record["seconds"]:.3f}s'+suffix,flush=True)
        except Exception as error:
            record.update(rx_hex=response.hex(),seconds=clock()-start,result='FAIL',error=str(error))
            report.update(status='FAIL',board_result='FAIL',failed_case=c['name']);save();raise
    report.update(status='STAGE8_DIAGNOSTIC_BOARD_PASS',board_result='PASS_DIAGNOSTIC_CANDIDATE_ONLY',
                  uart_frame_error_board='PASS',uart_overflow_board='PASS',host_matrix_board='PASS' if report['mode']=='all' else 'NOT_TESTED_THIS_CANDIDATE')
    save()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port');parser.add_argument('--mode',choices=['all','faults'],default='all')
    parser.add_argument('--log',type=Path,required=True);parser.add_argument('--plan-only',action='store_true')
    parser.add_argument('--bitstream',type=Path)
    args=parser.parse_args()
    if not args.plan_only and not args.port:parser.error('--port required')
    identity=image_identity();gate_hash=None if args.plan_only else require_gate(identity)
    selected=board_cases(args.mode)
    report=dict(stage='STAGE8_UART_DIAGNOSTIC',status='PLAN_ONLY' if args.plan_only else 'RUNNING',
                board_result='NOT_TESTED',port=args.port,baud=115200,mode=args.mode,image_sha256=identity,
                reset_evidence='USER_MUST_PRESS_KEY0_AND_WAIT_DDR_BEFORE_EACH_ROUND',
                downloaded_bitstream_identity=sha(args.bitstream) if args.bitstream else None,
                gate_sha256=gate_hash,input_sha256={p.name:sha(p) for p in sorted(Path(__file__).parent.glob('*.py'))},
                no_automatic_retry=True,load_verify_run_implemented=False,records=[],
                uart_frame_error_board='NOT_TESTED',uart_overflow_board='NOT_TESTED',
                host_matrix_board='NOT_TESTED_THIS_CANDIDATE',
                scope='New diagnostic candidate only; real sticky bits mirrored at RESPONSE capabilities bits24/25; fixed64 DDR')
    args.log.parent.mkdir(parents=True,exist_ok=True)
    with args.log.open('x',encoding='utf8') as stream:
        def save():
            stream.seek(0);stream.write(json.dumps(report,indent=2)+'\n');stream.truncate();stream.flush()
        try:
            save()
            if args.plan_only:
                report['planned_cases']=selected;save();print(f'PLAN_ONLY {len(selected)} responses; no serial opened');return
            import serial
            with serial.Serial(args.port,115200,bytesize=serial.EIGHTBITS,parity=serial.PARITY_NONE,stopbits=serial.STOPBITS_ONE,
                               timeout=.05,write_timeout=5,xonxoff=False,rtscts=False,dsrdtr=False) as port:
                time.sleep(.25)
                startup=port.read(4096)
                if startup:report['startup_rx_hex']=startup.hex();raise RuntimeError('pending UART data: reset and wait DDR')
                exercise(port,selected,report,save)
            print('RESULT: PASS diagnostic UART frame_error=0x10 overflow=0x20; original image identity remains separate')
        except Exception as error:
            report.update(status='FAIL',board_result='FAIL',error=str(error));save();raise

if __name__=='__main__':
    try:main()
    except Exception as error:print('RESULT: FAIL stage8 diagnostic:',error,file=sys.stderr);sys.exit(1)
