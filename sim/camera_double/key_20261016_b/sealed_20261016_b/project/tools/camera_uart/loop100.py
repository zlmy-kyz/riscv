"""Fixed single-buffer 100-frame board run. No PDS, images, retry or serial on --verify."""
import argparse,csv,hashlib,json,re,shutil,sys,time
from pathlib import Path
from capture import loader_plan
from protocol import Wire,need,line,exact
ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/'tests/camera_loop100/build/camera_loop100_20261015_a/manifest.json'
HZ=93750000
HEADER='LOOP100_APP=1 HZ=93750000 TARGET=100 DROP_FRAMES=10'
START=' FRAME_BASE=41000000 PIXELS=921600 BYTES=1843200 WRITES=57600 WAIT_TIMEOUT_TICKS=468750000'
ROW=re.compile(r'FRAME=(\d+) CRC_CAPTURE=([0-9a-f]{8}) CRC_CPU=([0-9a-f]{8}) MATCH=1 STATUS=00000005 ERROR=00000000 WAIT_TICKS=(\d+) CHECK_TICKS=(\d+)')
END=re.compile(r'LOOP100_END RESULT=PASS SUCCESS=100 TOTAL_TICKS=(\d+) WAIT_SUM=(\d+) WAIT_MIN=(\d+) WAIT_MAX=(\d+) CHECK_SUM=(\d+) CHECK_MIN=(\d+) CHECK_MAX=(\d+)')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(folder,r):(folder/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def require_image(path):
    m=json.loads(Path(path).read_text(encoding='utf-8'))
    need(m['status']=='CAMERA_LOOP100_STATIC_AUDIT_PASS','wrong image status')
    for kind in ('bin','elf'):need(sha(ROOT/m[kind+'_path'])==m[kind+'_sha256'],'fixed '+kind+' changed')
    for n,d in m['source_sha256'].items():need(sha(ROOT/n)==d,'source changed: '+n)
    return m
def row_parse(s,index,base):
    m=ROW.fullmatch(s);need(m is not None,'frame failure/format: '+s)
    seq,hw,cpu,wait,check=m.groups();seq=int(seq);wait=int(wait);check=int(check)
    need(seq==((base+index)&0xffffffff),'frame sequence skipped/repeated')
    need(hw==cpu,'hardware/CPU CRC mismatch')
    need(0<wait<5*HZ and 0<check<20*HZ,'phase duration outside firmware deadlines')
    return dict(index=index,seq=seq,crc32=hw,wait_ticks=wait,check_ticks=check)
def end_parse(s,frames):
    m=END.fullmatch(s);need(m is not None,'final success/format missing: '+s)
    values=list(map(int,m.groups()));wait=[f['wait_ticks'] for f in frames];check=[f['check_ticks'] for f in frames]
    need(len(frames)==100 and values[1:]==[sum(wait),min(wait),max(wait),sum(check),min(check),max(check)],'timing statistics/count mismatch')
    need(values[0]>=sum(wait)+sum(check),'total duration too small')
    return dict(total_ticks=values[0],wait_sum=values[1],wait_min=values[2],wait_max=values[3],
                check_sum=values[4],check_min=values[5],check_max=values[6],
                total_seconds=values[0]/HZ,wait_mean_ms=sum(wait)*1000/(100*HZ),check_mean_ms=sum(check)*1000/(100*HZ),
                distinct_crcs=len({f['crc32'] for f in frames}),adjacent_equal_crc=sum(a['crc32']==b['crc32'] for a,b in zip(frames,frames[1:])))
def start_parse(s):
    m=re.fullmatch(r'LOOP100_START SEQ_BASE=(\d+)'+re.escape(START),s)
    need(m is not None,'start geometry/identity mismatch');base=int(m[1]);need(base<2**32,'sequence base range');return base
def read_line(wire):
    s=line(wire,seconds=30)
    if s.startswith(('FAIL ','TRAP_CAUSE=')):raise ValueError('firmware stopped: '+s)
    return s
def execute(wire,info,folder,r,progress=print):
    need(wire.in_waiting==0,'unexpected UART bytes before Loader; no automatic flush')
    for p in loader_plan(info):
        record=dict(name=p['name'],tx_offset=wire.tx_count,rx_offset=wire.rx_count);r['loader_records'].append(record)
        wire.write(bytes.fromhex(p['tx_hex']));need(exact(wire,60)==bytes.fromhex(p['expected_hex']),'Loader response mismatch: '+p['name'])
        if not p.get('run'):need(wire.in_waiting==0,'extra Loader bytes')
    for want in (HEADER,'SENSOR_ID=00005640 CONFIG=OK','LOOP100_READY'):
        s=read_line(wire);need(s==want,'ready identity/config: '+s);progress(s)
    r['go_tx_offset']=wire.tx_count;wire.write(b'G');s=read_line(wire);r['start_line']=s;base=start_parse(s);progress(s)
    progress('连续采集已开始，请在中途主动改变画面；相同CRC只记录，不判失败。')
    with (folder/'frames.csv').open('x',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=['index','seq','crc32','wait_ticks','check_ticks']);writer.writeheader()
        for i in range(1,101):
            s=read_line(wire);row=row_parse(s,i,base);r['frames'].append(row);writer.writerow(row);stream.flush();save(folder,r);progress(s)
            if i==50:progress('已到第50帧，请主动改变画面；程序继续，不重试。')
        s=read_line(wire);r['end_line']=s;r['statistics']=end_parse(s,r['frames']);progress(s)
def verify(folder,expected_origin='ACTUAL_SERIAL'):
    folder=Path(folder);r=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    need(expected_origin in ('ACTUAL_SERIAL','OFFLINE_SYNTHETIC_TEST'),'origin')
    need(r['evidence_origin']==expected_origin and r['status']=='UART_LOOP100_DATA_CHECK_PASS','incomplete/nonactual session')
    if expected_origin=='ACTUAL_SERIAL':need(r['serial_opened'] and r['user_KEY0_confirmation'],'missing actual user/serial')
    m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    need(m==r['application'] and sha(folder/'manifest.json')==r['manifest_sha256'],'manifest identity')
    need(sha(folder/'application.bin')==m['bin_sha256'],'run image identity')
    rx=(folder/'uart.rx.bin').read_bytes();tx=(folder/'uart.tx.bin').read_bytes();a=b=0
    plans=loader_plan(m);need(len(plans)==len(r['loader_records']),'Loader count')
    for p,record in zip(plans,r['loader_records']):
        sent=bytes.fromhex(p['tx_hex']);reply=bytes.fromhex(p['expected_hex'])
        need(tx[a:a+len(sent)]==sent and rx[b:b+60]==reply,'Loader raw bytes')
        need(record['tx_offset']==a and record['rx_offset']==b and record['name']==p['name'],'Loader ledger')
        a+=len(sent);b+=60
    need(tx[a:]==b'G' and r['go_tx_offset']==a,'one start command/extra TX')
    text=rx[b:].decode('ascii');lines=text.splitlines()
    need(text.endswith('\n') and '\r' not in text and len(lines)==105,'raw app line count/truncation/extra bytes')
    need(lines[:3]==[HEADER,'SENSOR_ID=00005640 CONFIG=OK','LOOP100_READY'],'actual ready/sensor/config')
    base=start_parse(lines[3]);need(lines[3]==r['start_line'],'start ledger')
    frames=[row_parse(s,i,base) for i,s in enumerate(lines[4:104],1)]
    need(frames==r['frames'],'frames ledger differs from raw bytes')
    stats=end_parse(lines[104],frames);need(lines[104]==r['end_line'] and stats==r['statistics'],'end/statistics ledger')
    with (folder/'frames.csv').open(newline='',encoding='utf-8') as stream:
        csv_rows=list(csv.DictReader(stream))
    need(csv_rows==[{k:str(v) for k,v in f.items()} for f in frames],'CSV differs from raw bytes')
    return dict(status='ACTUAL_UART_LOOP100_RAW_REPLAY_PASS' if expected_origin=='ACTUAL_SERIAL' else 'OFFLINE_LOOP100_REPLAY_PASS',
                frames=100,statistics=stats,same_crc_is_failure=False,images_exported=False,PC_full_frame_CRC=False,
                scene_change='User instructed; CRC variation recorded only; no automatic stale-frame claim')
def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--port',default='COM9');ap.add_argument('--manifest',type=Path,default=DEFAULT)
    ap.add_argument('--log-dir',type=Path);ap.add_argument('--plan-only',action='store_true');ap.add_argument('--verify',type=Path);args=ap.parse_args()
    if args.verify:print(json.dumps(verify(args.verify),indent=2));return
    info=require_image(args.manifest);plans=loader_plan(info)
    if args.plan_only:
        print(json.dumps(dict(status='LOOP100_PLAN_ONLY_SERIAL_NOT_OPENED',bin_sha256=info['bin_sha256'],bytes=info['bytes'],
                              loader_responses=len(plans),RUN_commands=sum(bool(p.get('run')) for p in plans),frames=100,retries=0,images=False),indent=2));return
    need(args.log_dir is not None and not args.log_dir.exists(),'use a new --log-dir; never overwrite failures')
    folder=args.log_dir.resolve();folder.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(args.manifest,folder/'manifest.json');shutil.copyfile(ROOT/info['bin_path'],folder/'application.bin')
    r=dict(status='RUNNING',evidence_origin='ACTUAL_SERIAL',application=info,manifest_sha256=sha(args.manifest),
           port=args.port,baud=115200,serial_opened=False,PDS_started=False,retry_count=0,loader_records=[],frames=[],
           user_KEY0_confirmation=False,scene_change_instruction_shown=True,tool_sha256={Path(__file__).name:sha(__file__)})
    save(folder,r);wire=None
    try:
        input('关闭串口助手；沿用成功位流，按KEY0后释放，等DDR就绪再Enter。请在100帧中途改变画面：')
        r['user_KEY0_confirmation']=True
        import serial
        with serial.Serial(args.port,115200,timeout=.05,write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as port:
            r['serial_opened']=True;time.sleep(.25);wire=Wire(port,folder)
            execute(wire,info,folder,r)
            time.sleep(.05);need(wire.in_waiting==0,'extra bytes after terminal summary')
        wire.close();wire=None;r['status']='UART_LOOP100_DATA_CHECK_PASS';save(folder,r)
        checked=verify(folder);(folder/'verified.json').write_text(json.dumps(checked,indent=2)+'\n',encoding='utf-8')
        print(json.dumps(checked,indent=2))
    except BaseException as exc:
        r.update(status='STOPPED_FIRST_FAILURE',error=repr(exc))
        # Preserve all diagnostic lines already emitted by a halted firmware, without commands/retry.
        if wire:
            deadline=time.monotonic()+2
            while time.monotonic()<deadline:
                try:wire.read(4096)
                except Exception:break
        raise
    finally:
        if wire:wire.close()
        save(folder,r)
    print('日志目录：',folder)
if __name__=='__main__':main()
