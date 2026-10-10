"""Stage 8 host-injectable ACK/NACK acceptance for unchanged stage7 firmware."""
import argparse, hashlib, json, struct, sys, time
from pathlib import Path
from cases import cases, CRC
from protocol import decode_response, expected_response
ROOT=Path(__file__).resolve().parents[4]
IMAGE=ROOT/'tests/uart_loader/candidates/ack_nack_stage8/build'
IDENTITY={'loader.elf':'49744ef735f2c14461594969004641f318f62991589aadf2209f9e15cf6de178',
          'loader_rom.dat':'21a590346a9a433cade6a4e85c34829620f86ae8ea0238b7be514ff78fa2376a',
          'loader_ram.dat':'59a4105c17b2224ec28b5bf87c080672c940501cdf519091cf8e33c3e2239d7a'}

def image_identity():
    result={n:hashlib.sha256((IMAGE/n).read_bytes()).hexdigest() for n in IDENTITY}
    if result!=IDENTITY: raise RuntimeError('candidate differs from successful stage7 image')
    return result

def exercise(port,selected,report,save,timeout=5,clock=time.monotonic,emit=print):
    for index,c in enumerate(selected):
        request=bytes.fromhex(c['tx_hex']); response=bytearray(); start=clock()
        record=dict(**c,rx_hex='',seconds=0,result='RUNNING')
        report['records'].append(record);save()
        try:
            if port.write(request)!=len(request): raise RuntimeError('short serial write')
            port.flush()
            while len(response)<60 and clock()-start<timeout:
                response.extend(port.read(60-len(response)))
            record.update(rx_hex=response.hex(),seconds=clock()-start)
            decoded=decode_response(bytes(response),c['seq'],c['cmd'],expected_crc=c.get('expected_crc',CRC))
            record['decoded']=decoded
            actual=CRC if c.get('crc_read') else 0
            expected=expected_response(c['seq'],c['cmd'],c['status'],actual)
            if bytes(response)!=expected: raise RuntimeError('response fields/status differ from expected raw ACK/NACK')
            # These are board timings, including serial transfer; tolerate USB scheduling above minimum.
            if c['name']=='bad_header_crc' and record['seconds']<.095: raise RuntimeError('NACK before 100ms recovery')
            if c.get('negative') and c['status']==0x8004 and record['seconds']<.195: raise RuntimeError('NACK before receive timeout plus recovery')
            extra=port.read(1)
            if extra:
                record['extra_rx_hex']=extra.hex(); raise RuntimeError('unexpected extra response/data')
            record['result']='PASS';save()
            emit(f'{index+1:03d}/{len(selected)} {c["name"]}: '+('ACK' if c['status']==0 else f'NACK 0x{c["status"]:04X}')+f' PASS {record["seconds"]:.3f}s',flush=True)
        except Exception as error:
            record.update(rx_hex=response.hex(),seconds=clock()-start,result='FAIL',error=str(error))
            report.update(status='FAIL',board_result='FAIL',failed_case=c['name']);save();raise
    report.update(status='STAGE8_HOST_INJECTABLE_BOARD_PASS',board_result='PASS_HOST_INJECTABLE_ONLY',
        uart_frame_error_board='NOT_TESTED',uart_overflow_board='NOT_TESTED',stage8_full_board_result='NOT_COMPLETE')
    save()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port')
    parser.add_argument('--log',type=Path,required=True)
    parser.add_argument('--plan-only',action='store_true')
    args=parser.parse_args()
    if not args.plan_only and not args.port: parser.error('--port required for board test')
    args.log.parent.mkdir(parents=True,exist_ok=True)
    # Exclusive create: a live or archived evidence file is never replaced.
    stream=args.log.open('x',encoding='utf8')
    selected=cases(uart_faults=False)
    report=dict(stage='ACK_NACK_STAGE8',status='PLAN_ONLY' if args.plan_only else 'RUNNING',
        board_result='NOT_TESTED',port=args.port,baud=115200,image_sha256=image_identity(),
        reset_evidence='USER_MUST_PRESS_KEY0_AND_WAIT_DDR_BEFORE_COMMAND',downloaded_bitstream_identity=None,
        input_sha256={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in [Path(__file__),Path(__file__).with_name('cases.py'),Path(__file__).with_name('protocol.py')]},
        scope='Fixed64 only; host-injectable negative paths followed by PING and read-only fixed DDR CRC',
        no_automatic_retry=True,load_verify_run_implemented=False,records=[])
    def save():
        stream.seek(0);stream.write(json.dumps(report,indent=2)+'\n');stream.truncate();stream.flush()
    try:
        save()
        if args.plan_only:
            report['planned_cases']=selected;save();print(f'PLAN_ONLY: {len(selected)} frames / {sum(bool(c.get("negative")) for c in selected)} negative cases; no serial opened');return
        import serial
        with serial.Serial(args.port,115200,bytesize=serial.EIGHTBITS,parity=serial.PARITY_NONE,
                           stopbits=serial.STOPBITS_ONE,timeout=.05,write_timeout=5,xonxoff=False,rtscts=False,dsrdtr=False) as port:
            time.sleep(.25)
            startup=port.read(4096)
            if startup:
                report['startup_rx_hex']=startup.hex();raise RuntimeError('unexpected pending UART data; ensure reset and correct firmware')
            exercise(port,selected,report,save)
        print('RESULT: PASS Stage8 host-injectable paths; UART frame/overflow board NOT_TESTED')
    except Exception as e:
        report.update(status='FAIL',board_result='FAIL',error=str(e));save();raise
    finally: stream.close()

if __name__=='__main__':
    try: main()
    except Exception as e: print('RESULT: FAIL stage8:',e,file=sys.stderr);sys.exit(1)
