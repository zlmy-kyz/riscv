"""ABI2 board tool. Deployment gated until Sol reviews this frozen key simulation evidence."""
import argparse,csv,json,re,shutil,sys,time
from pathlib import Path
from capture import loader_plan
from protocol import Wire,need,exact,line
from loop100 import sha
ROOT=Path(__file__).resolve().parents[2]
DEFAULT=ROOT/'tests/camera_double100/build/abi2_20261016_d/manifest.json'
ROW=re.compile(r'DB_(FRAME|TAIL) BUFFER=([01]) SEQ=(\d+) CRC_CAPTURE=([0-9a-f]{8}) CRC_CPU=([0-9a-f]{8}) MATCH=1 ERROR=00000000 WAIT_TICKS=(\d+) READ_TICKS=(\d+) WAIT_CYCLES=(\d+)')
END=re.compile(r'DB_END RESULT=PASS SUCCESS=100 TAIL=([01]) TOTAL_TICKS=(\d+) WAIT_SUM=(\d+) WAIT_MIN=(\d+) WAIT_MAX=(\d+) READ_SUM=(\d+) READ_MIN=(\d+) READ_MAX=(\d+) WAIT_CYCLES=(\d+)')
HEADER='DB_APP=2 ID=43414d02 HZ=93750000 TARGET=100 WIDTH=1280 HEIGHT=720'
def save(folder,r):(folder/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def image(path):
    m=json.loads(Path(path).read_text(encoding='utf-8'));need(m['status']=='ABI2_SOFTWARE_STATIC_PASS','wrong ABI/build')
    for k in ('bin','elf'):need(sha(ROOT/m[k+'_path'])==m[k+'_sha256'],'fixed '+k+' changed')
    for n,d in m['source_sha256'].items():need(sha(ROOT/n)==d,'changed source '+n)
    return m
def parse(lines):
    need(lines[:3]==[HEADER,'SENSOR_ID=00005640 CONFIG=OK','DB_READY'],'ABI/sensor/config')
    rows=[]
    for s in lines[3:-1]:
        m=ROW.fullmatch(s);need(m is not None,'row/error: '+s)
        kind,b,seq,c,cpu,w,t,q=m.groups();seq=int(seq);w=int(w);t=int(t);q=int(q)
        need(seq==len(rows)+1 and c==cpu,'sequence/CRC mismatch')
        need(kind==('FRAME' if seq<=100 else 'TAIL') and seq<=101,'main/tail count')
        need(0<w<5*93750000 and 0<t<20*93750000,'phase time')
        need(q<2**32 and (not rows or q>=rows[-1]['wait_cycles']),'WAIT_CYCLES decreasing')
        rows.append(dict(kind=kind,buffer=int(b),seq=seq,crc32=c,wait_ticks=w,read_ticks=t,wait_cycles=q))
    m=END.fullmatch(lines[-1]);need(m is not None,'incomplete final summary')
    vals=list(map(int,m.groups()));need(len(rows)==100+vals[0],'success/tail count')
    main=rows[:100];w=[r['wait_ticks'] for r in main];t=[r['read_ticks'] for r in main]
    need(vals[2:8]==[sum(w),min(w),max(w),sum(t),min(t),max(t)],'statistical sums')
    need(vals[1]>=sum(w)+sum(t) and vals[-1]>=rows[-1]['wait_cycles'],'total/wait counter')
    need({r['buffer'] for r in main}=={0,1},'both buffers unused')
    return rows,dict(success=100,tail=vals[0],total_ticks=vals[1],total_seconds=vals[1]/93750000,
                    wait_mean_ms=sum(w)/9375000,read_mean_ms=sum(t)/9375000,wait_cycles=vals[-1],
                    distinct_crcs=len({r['crc32'] for r in main}),buffer_counts=[sum(r['buffer']==b for r in main) for b in (0,1)])
def verify(folder,origin='ACTUAL_SERIAL'):
    folder=Path(folder);r=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    need(origin in ('ACTUAL_SERIAL','OFFLINE_SYNTHETIC_TEST') and r['evidence_origin']==origin,'evidence origin')
    need(r['status']=='ABI2_UART100_DATA_PASS' and (origin!='ACTUAL_SERIAL' or r['serial_opened']),'session not completed')
    m=json.loads((folder/'manifest.json').read_text());need(m==r['application'] and sha(folder/'manifest.json')==r['manifest_sha256'],'manifest')
    need(sha(folder/'application.bin')==m['bin_sha256'],'BIN identity')
    rx=(folder/'uart.rx.bin').read_bytes();tx=(folder/'uart.tx.bin').read_bytes();a=b=0
    plans=loader_plan(m);need(len(plans)==len(r['loader_records']),'loader count')
    for p,rec in zip(plans,r['loader_records']):
        data=bytes.fromhex(p['tx_hex']);need(tx[a:a+len(data)]==data and rx[b:b+60]==bytes.fromhex(p['expected_hex']),'raw loader bytes')
        need(rec==dict(name=p['name'],tx_offset=a,rx_offset=b),'loader ledger');a+=len(data);b+=60
    need(tx[a:]==b'G' and r['go_tx_offset']==a,'single G/no retry')
    raw=rx[b:].decode('ascii');need(raw.endswith('\n') and '\r' not in raw,'partial line')
    rows,stats=parse(raw.splitlines());need(rows==r['frames'] and stats==r['statistics'],'raw/ledger mismatch')
    with (folder/'frames.csv').open(newline='',encoding='utf-8') as f:csvrows=list(csv.DictReader(f))
    need(csvrows==[{k:str(v) for k,v in row.items()} for row in rows],'CSV mismatch')
    return dict(status='ABI2_ACTUAL_RAW_REPLAY_PASS' if origin=='ACTUAL_SERIAL' else 'ABI2_OFFLINE_REPLAY_PASS',statistics=stats,
                PC_full_frame_CRC=False,images_exported=False,same_CRC_is_error=False,
                concurrent_DMA='Cycle-level interleaving proved by separate key simulation, not serial summary alone')
def execute(wire,m,folder,r,progress=print):
    need(wire.in_waiting==0,'unexpected initial bytes; no flush/retry')
    for p in loader_plan(m):
        r['loader_records'].append(dict(name=p['name'],tx_offset=wire.tx_count,rx_offset=wire.rx_count))
        wire.write(bytes.fromhex(p['tx_hex']));need(exact(wire,60)==bytes.fromhex(p['expected_hex']),'Loader '+p['name'])
    lines=[]
    for want in (HEADER,'SENSOR_ID=00005640 CONFIG=OK','DB_READY'):
        s=line(wire);need(s==want,'ready: '+s);lines.append(s);progress(s)
    r['go_tx_offset']=wire.tx_count;wire.write(b'G')
    for _ in range(103):
        s=line(wire,30);lines.append(s);progress(s)
        if s.startswith(('DB_FAIL','TRAP_')):raise ValueError(s)
        if s.startswith('DB_END '):break
        need(ROW.fullmatch(s) is not None,'unknown frame/error: '+s)
        r['prefix_lines']=lines;save(folder,r)
    rows,stats=parse(lines);r['frames']=rows;r['statistics']=stats
    with (folder/'frames.csv').open('x',newline='',encoding='utf-8') as f:
        writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,default=DEFAULT);p.add_argument('--plan-only',action='store_true')
    p.add_argument('--verify',type=Path);p.add_argument('--port',default='COM9');p.add_argument('--log-dir',type=Path);a=p.parse_args()
    if a.verify:print(json.dumps(verify(a.verify),indent=2));return
    m=image(a.manifest)
    if a.plan_only:print(json.dumps(dict(status='ABI2_PLAN_ONLY_NO_SERIAL',bytes=m['bytes'],bin_sha256=m['bin_sha256'],responses=len(loader_plan(m)),frames=100)));return
    # No command is supplied to the user until the key raw evidence is reviewed. This explicit gate binds that review.
    gate=ROOT/'sim/camera_double/key_20261016_a/board_release.json'
    need(gate.exists(),'ABI2 board deployment pending Sol key-evidence review; no serial opened')
    g=json.loads(gate.read_text());need(g['status']=='SOL_KEY_REVIEW_PASS_BOARD_RELEASED' and g['firmware_sha256']==m['bin_sha256'],'wrong release identity')
    need(a.log_dir is not None and not a.log_dir.exists(),'new --log-dir required')
    folder=a.log_dir.resolve();folder.mkdir(parents=True,exist_ok=False);shutil.copyfile(a.manifest,folder/'manifest.json');shutil.copyfile(ROOT/m['bin_path'],folder/'application.bin')
    r=dict(status='RUNNING',evidence_origin='ACTUAL_SERIAL',application=m,manifest_sha256=sha(a.manifest),serial_opened=False,
           port=a.port,baud=115200,retry_count=0,loader_records=[],frames=[],tool_sha256=sha(__file__),PDS_started=False)
    save(folder,r);wire=None
    try:
        input('使用已确认时序正确的ABI2位流；关闭串口助手，按KEY0释放并等DDR就绪后Enter，运行中改变画面：')
        import serial
        with serial.Serial(a.port,115200,timeout=.05,write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as port:
            r['serial_opened']=True;wire=Wire(port,folder);execute(wire,m,folder,r)
            time.sleep(.05);need(wire.in_waiting==0,'extra terminal bytes')
        wire.close();wire=None;r['status']='ABI2_UART100_DATA_PASS';save(folder,r)
        (folder/'verified.json').write_text(json.dumps(verify(folder),indent=2)+'\n')
    except BaseException as exc:
        r.update(status='STOPPED_FIRST_FAILURE',error=repr(exc))
        if wire:
            until=time.monotonic()+2
            while time.monotonic()<until:
                try:wire.read(4096)
                except Exception:break
        raise
    finally:
        if wire:wire.close()
        save(folder,r)
if __name__=='__main__':main()
