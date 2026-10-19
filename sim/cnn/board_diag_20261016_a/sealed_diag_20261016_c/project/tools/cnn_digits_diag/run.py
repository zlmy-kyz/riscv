"""User-authorized board-first digits10 diagnostic. Timing pending, key HDL not completed."""
import argparse,hashlib,importlib.util,json,re,shutil,struct,sys,time,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
import reference
sys.path.insert(0,str(ROOT/'tools/camera_uart'))
from capture import loader_plan
from protocol import Wire,exact,need
DEFAULT=ROOT/'tests/cnn_digits_diag/build/diag_20261016_c/manifest.json'
RELEASE=ROOT/'sim/cnn/board_diag_20261016_a/board_release.json'
MODEL=ROOT/'tests/cnn_digits_diag/model/diag_20261016_a'
HEADER='CNN_DIAG_APP=1 CONTRACT=digits10_int8_v1 HZ=93750000 DIAGNOSTIC=1 TIMING=PENDING'
JOB=re.compile(r'CNN_JOB BUF=0 SEQ=1 MODEL=([0-9a-f]{8}) MODEL_CRC=([0-9a-f]{8}) PP_CRC=([0-9a-f]{8}) BYTES=27648 READS=864 GRAY=1024 STATUS=0000000a ERROR=00000000 CLASS=(\d+) CYCLES=(\d+) PP_CYCLES=(\d+)')
RELEASED=re.compile(r'CNN_RELEASED CLAIMS=(\d+) DISCARDS=(\d+) GLOBAL_SEQ=(\d+) CAM_STATE=([0-9a-f]{8}) PP_STATUS=00000002 CNN_STATUS=0000000a')
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
crc=lambda b:zlib.crc32(b)&0xffffffff
def save(folder,r):(folder/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def image(path):
    m=json.loads(Path(path).read_text(encoding='utf-8'));need(m['status']=='CNN_DIAG_BUILD_STATIC_AUDIT_PASS','wrong build')
    for k in ('bin','elf'):need(sha(ROOT/m[k+'_path'])==m[k+'_sha256'],'changed '+k)
    for n,d in m['source_sha256'].items():need(sha(ROOT/n)==d,'changed source '+n)
    return m
def line(w):
    data=bytearray();deadline=time.monotonic()+30
    while not data.endswith(b'\n'):
        data+=exact(w,1,max(.001,deadline-time.monotonic()));need(len(data)<=2048,'excess ASCII line')
    need(b'\r' not in data,'unexpected CR');return data[:-1].decode('ascii')
def model_info(model):
    m=model['meta'];return f"MODEL ID={m['model_id']:08x} WORDS=6222 CRC={m['load_crc32']:08x} STATUS=00000008"
def artifacts(folder,rgb,job,scores,model,write):
    result=reference.infer(rgb,model)
    # All reference tensors are PC-derived from actual exported RGB, never from scores.
    if write:
        (folder/'rgb96.bin').write_bytes(rgb);(folder/'board_scores.json').write_text(json.dumps(dict(scores=scores,prediction=job['prediction'],cycles=job['cycles']),indent=2)+'\n')
        reference.save_trace(folder/'integer_reference',result)
    else:
        need((folder/'rgb96.bin').read_bytes()==rgb,'RGB artifact differs from actual RX')
        for name,data in result['layers'].items():need((folder/'integer_reference'/(name+'.bin')).read_bytes()==bytes(v&255 for v in data),'reference tensor '+name)
        need((folder/'integer_reference/scores.bin').read_bytes()==struct.pack('<10i',*result['scores']),'reference scores')
        need(json.loads((folder/'board_scores.json').read_text())==dict(scores=scores,prediction=job['prediction'],cycles=job['cycles']),'board score ledger')
    mismatches=[dict(index=i,board=scores[i],expected=result['scores'][i]) for i in range(10) if scores[i]!=result['scores'][i]]
    comparison=dict(all_10_scores_equal=not mismatches,mismatches=mismatches,board_scores=scores,expected_scores=result['scores'],
        board_class=job['prediction'],expected_class=result['prediction'],argmax_equal=job['prediction']==result['prediction'],
        model_id=model['meta']['model_id_hex'],cnn_cycles=job['cycles'],cnn_ms=job['cycles']/93750000*1000,
        purpose='NONTRAINED_DIAGNOSTIC_NOT_DIGIT_ACCURACY',scope='One input and parameter package; no hardware layer dumps')
    if write:(folder/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    else:need(json.loads((folder/'comparison.json').read_text())==comparison,'comparison ledger')
    # PNG using independent lossless standard-library writer, preserving the original byte tensor.
    spec=importlib.util.spec_from_file_location('cnn_diag_png',ROOT/'tools/camera_preprocess_photo/reference.py')
    png=importlib.util.module_from_spec(spec);spec.loader.exec_module(png)
    data=png.png_rgb888(rgb)
    gray=bytes(v+128 for v in result['layers']['gray32'])
    graypng=png.png_rgb(32,32,(b''.join(bytes((v,v,v)) for v in gray[y*32:(y+1)*32]) for y in range(32)))
    for name,b in (('rgb96.png',data),('gray32.png',graypng)):
        if write:(folder/name).write_bytes(b)
        else:need((folder/name).read_bytes()==b,'PNG '+name)
    need(not mismatches,'SCORE MISMATCH: '+str(mismatches))
    need(comparison['argmax_equal'],'argmax differs from independent scores')
    return comparison
def exchange(w,m,folder,model,write=True,progress=lambda _:None):
    result=dict(loader_records=[],packets=[])
    for p in loader_plan(m):
        result['loader_records'].append(dict(name=p['name'],tx_offset=w.tx_count,rx_offset=w.rx_count))
        w.write(bytes.fromhex(p['tx_hex']));need(exact(w,60)==bytes.fromhex(p['expected_hex']),'Loader '+p['name'])
    for want in (HEADER,model_info(model),'SENSOR_ID=00005640 CONFIG=OK','CNN_READY'):
        got=line(w);need(got==want,'banner/model/error: '+got);progress(got)
    w.write(b'G');w.write(b'C');raw=line(w);match=JOB.fullmatch(raw);need(match is not None,'CNN job/error: '+raw)
    model_id,model_crc,ppcrc,cl,cycles,ppcycles=match.groups()
    need(model_id==model['meta']['model_id_hex'] and int(model_crc,16)==model['meta']['load_crc32'],'job model identity')
    job=dict(model_id=model_id,model_crc=model_crc,pp_crc=ppcrc,prediction=int(cl),cycles=int(cycles),pp_cycles=int(ppcycles))
    need(0<=job['prediction']<10 and 0<job['cycles']<3*93750000 and 0<job['pp_cycles']<3*93750000,'job class/cycles')
    scores_raw=line(w);need(re.fullmatch(r'SCORES(?: -?\d+){10}',scores_raw) is not None,'ten scores missing/error: '+scores_raw)
    scores=list(map(int,scores_raw.split()[1:]));need(all(-2**31<=s<2**31 for s in scores),'score signed range')
    need(max(range(10),key=lambda i:scores[i])==job['prediction'],'board scores/class inconsistent')
    result.update(job=job,job_line=raw,scores=scores);progress(raw);progress(scores_raw)
    w.write(b'D');need(line(w)=='CNN_EXPORT_BEGIN','export begin')
    rgb=bytearray();deadline=time.monotonic()+30
    partial=folder/'rgb96.partial'
    f=partial.open('xb') if write else None
    try:
        while True:
            remain=deadline-time.monotonic();need(remain>0,'RGB export deadline');rx=w.rx_count;h=exact(w,32,min(5,remain))
            magic,kind,seq,off,n,total,c,hc=struct.unpack('<4s7I',h)
            need(magic==b'CN01' and crc(h[:28])==hc,'CN01 header/magic CRC')
            need(seq==1 and off==len(rgb) and total==27648,'packet identity/order')
            if kind==1:
                need(n==min(1024,27648-off) and n>0,'packet DATA length')
                b=exact(w,n);need(crc(b)==c,'packet data CRC');rgb+=b
                if f:f.write(b);f.flush()
            else:need(kind==2 and len(rgb)==27648 and n==0 and c==crc(rgb)==int(ppcrc,16),'END/whole RGB CRC')
            tx=w.tx_count;w.write(b'K');result['packets'].append(dict(rx_offset=rx,tx_ack_offset=tx,header_hex=h.hex()))
            if kind==2:break
    finally:
        if f:f.close()
    need(line(w)=='CNN_EXPORT_DONE','export done/error')
    raw=line(w);match=RELEASED.fullmatch(raw);need(match is not None,'release/error: '+raw)
    claims,discard,glob,state=match.groups()
    need(int(claims)==int(glob)==1+int(discard) and int(discard) in (0,1) and int(state,16)&0x2cf==0,'ownership not closed')
    result['release']=raw;result['comparison']=artifacts(folder,bytes(rgb),job,scores,model,write)
    progress('PC_ALL_10_SCORES=MATCH ARGMAX=MATCH (nontrained diagnostic)')
    w.write(b'Q');end=line(w);need(end==f"CNN_DIAG_DONE JOBS=1 CPU_CONTROL=PASS MODEL={model_id}",'session done/error: '+end)
    result['finish']=end;return result
class Replay:
    def __init__(self,rx,tx):self.rx=rx;self.tx=tx;self.rx_count=self.tx_count=0
    def read(self,n):b=self.rx[self.rx_count:self.rx_count+n];self.rx_count+=len(b);return b
    def write(self,b):need(self.tx[self.tx_count:self.tx_count+len(b)]==b,'raw TX/no retry');self.tx_count+=len(b);return len(b)
def verify(folder,origin='ACTUAL_SERIAL'):
    folder=Path(folder);r=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    need(origin in ('ACTUAL_SERIAL','OFFLINE_SYNTHETIC_TEST') and r['evidence_origin']==origin,'synthetic is not actual serial')
    need(r['status']=='CNN_DIAG_ONE_JOB_SCORES_PASS','session not completed')
    if origin=='ACTUAL_SERIAL':need(r['serial_opened'] and r['user_KEY0_confirmation'] and r['user_current_repaired_bitstream_confirmation'],'actual prerequisites')
    m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    need(m==r['application'] and sha(folder/'manifest.json')==r['manifest_sha256'],'manifest identity')
    need(sha(folder/'application.bin')==m['bin_sha256'],'BIN identity')
    for n,d in r['file_sha256'].items():need(sha(folder/n)==d,'changed evidence '+n)
    model=reference.load(folder/'model');need(model['meta']==m['diagnostic_model'],'model manifest differs')
    w=Replay((folder/'uart.rx.bin').read_bytes(),(folder/'uart.tx.bin').read_bytes())
    session=exchange(w,m,folder,model,False);need(session==r['session'],'raw/session ledger mismatch')
    need(w.rx_count==len(w.rx) and w.tx_count==len(w.tx),'extra RX/TX')
    return dict(status='CNN_DIAG_ONE_INPUT_PACKAGE_RAW_10_SCORES_VERIFIED',scores=session['scores'],prediction=session['job']['prediction'],
        model_id=model['meta']['model_id_hex'],cnn_ms=session['comparison']['cnn_ms'],trained_digit_accuracy=False,
        key_HDL='NOT_COMPLETED',timing='PENDING_USER_CONFIRMATION',scope='One actual RGB96 and diagnostic parameter package only')
def live(args,m):
    gate=json.loads(RELEASE.read_text());need(gate['status']=='USER_AUTHORIZED_BOARD_DIAGNOSTIC_TIMING_PENDING' and gate['firmware_sha256']==m['bin_sha256'],'board diagnostic release identity')
    need(args.log_dir is not None and not args.log_dir.exists(),'new --log-dir required')
    folder=args.log_dir.resolve();folder.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(args.manifest,folder/'manifest.json');shutil.copyfile(ROOT/m['bin_path'],folder/'application.bin');shutil.copyfile(RELEASE,folder/'board_release.json')
    shutil.copytree(MODEL,folder/'model');model=reference.load(folder/'model')
    r=dict(status='RUNNING',evidence_origin='ACTUAL_SERIAL',application=m,manifest_sha256=sha(args.manifest),
        serial_opened=False,user_KEY0_confirmation=False,user_current_repaired_bitstream_confirmation=False,
        port=args.port,baud=115200,retry_count=0,timing='PENDING_USER_CONFIRMATION',key_HDL='NOT_COMPLETED',
        PDS_started=False,tool_sha256={p.name:sha(p) for p in HERE.glob('*.py')})
    save(folder,r);w=None;started=time.monotonic()
    try:
        print('用户授权板优先诊断；关键HDL未完成；最新RAM响应+1拍/DVP I/O打包修复版时序待确认。')
        input('请先由你重新生成并下载包含最新修复的CNN位流，旧位流不能作为本版。关闭串口助手，按KEY0释放、等DDR就绪，摆好画面后Enter：')
        r['user_KEY0_confirmation']=True;r['user_current_repaired_bitstream_confirmation']=True
        import serial
        with serial.Serial(args.port,115200,timeout=.05,write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as p:
            r['serial_opened']=True;w=Wire(p,folder)
            try:
                need(p.in_waiting==0,'unexpected initial bytes; no flush/retry')
                r['session']=exchange(w,m,folder,model,True,print)
                time.sleep(.05);need(p.in_waiting==0,'extra final bytes')
            except BaseException:
                until=time.monotonic()+2
                while time.monotonic()<until:
                    try:w.read(4096)
                    except Exception:break
                raise
        w.close();w=None;r['status']='CNN_DIAG_ONE_JOB_SCORES_PASS'
    except BaseException as e:r.update(status='STOPPED_FIRST_FAILURE',error=repr(e));raise
    finally:
        if w:w.close()
        r['wall_seconds_including_user_confirmation']=time.monotonic()-started
        r['file_sha256']={p.relative_to(folder).as_posix():sha(p) for p in folder.rglob('*') if p.is_file() and p.name not in ('result.json','verified.json')}
        save(folder,r)
    checked=verify(folder);(folder/'verified.json').write_text(json.dumps(checked,indent=2)+'\n');print(json.dumps(checked,indent=2))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--port',default='COM9');p.add_argument('--manifest',type=Path,default=DEFAULT)
    p.add_argument('--log-dir',type=Path);p.add_argument('--verify',type=Path);p.add_argument('--plan-only',action='store_true');a=p.parse_args()
    if a.verify:print(json.dumps(verify(a.verify),indent=2));return
    m=image(a.manifest);model=reference.load(MODEL);need(model['meta']==m['diagnostic_model'],'model identity')
    if a.plan_only:
        print(json.dumps(dict(status='CNN_DIAG_PLAN_NO_SERIAL_TIMING_PENDING',bytes=m['bytes'],bin_sha256=m['bin_sha256'],
            model_id=model['meta']['model_id_hex'],model_words=6222,model_crc=f"{model['meta']['load_crc32']:08x}",
            loader_responses=len(loader_plan(m)),export_bytes=27648,key_HDL='NOT_COMPLETED',timing='PENDING_USER_CONFIRMATION'),indent=2));return
    live(a,m)
if __name__=='__main__':main()
