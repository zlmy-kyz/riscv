"""One fresh camera photo: actual source + hardware RGB888 export and byte-exact PC audit."""
import argparse,hashlib,json,re,shutil,struct,sys,time,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
import reference
sys.path.insert(0,str(ROOT/'tools/camera_uart'))
from capture import loader_plan
from protocol import Wire,exact,need
DEFAULT=ROOT/'tests/camera_preprocess_photo/build/photo_20261015_d/manifest.json'
RELEASE=ROOT/'sim/camera_preprocess/board_first_20261015_a/board_release.json'
HEADER='PP_APP=1 ID=50525001 HZ=93750000 TARGET=1 WIDTH=1280 HEIGHT=720 OUT=96x96'
END='PPX_SESSION_DONE GROUPS=1 CPU_CHECK=PASS'
crc=lambda b:zlib.crc32(b)&0xffffffff
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
SUMMARY=re.compile(r'PP_GROUP=1 BUF=0 SEQ=1 SRC=0 SRC_SEQ=1 LAYOUT=1280x720x2 SRC_CRC=([0-9a-f]{8}) SRC_BYTES=1843200 BASE=42000000 BYTES=27648 SIZE=00600060 READ=9216 WRITE=864 PRODUCED=27648 CRC_PP=([0-9a-f]{8}) CRC_CPU=([0-9a-f]{8}) CRC_REREAD=([0-9a-f]{8}) ERR=00000000')
RELEASED=re.compile(r'PP_RELEASED BUF=0 SEQ=1 CLAIMS=(\d+) DISCARDS=(\d+) GLOBAL_SEQ=(\d+) CAM_STATE=([0-9a-f]{8}) PP_STATUS=00000002 PP_CYCLES=(\d+) ELAPSED_TICKS=(\d+)')

def save(folder,r):(folder/'result.json').write_text(json.dumps(r,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def image(path):
    m=json.loads(Path(path).read_text(encoding='utf-8'))
    need(m['status']=='PHOTO_BUILD_STATIC_AUDIT_PASS','wrong firmware build')
    for k in ('bin','elf'):need(sha(ROOT/m[k+'_path'])==m[k+'_sha256'],'changed '+k)
    for n,d in m['source_sha256'].items():need(sha(ROOT/n)==d,'changed source '+n)
    return m

def line(w):
    data=bytearray();deadline=time.monotonic()+30
    while not data.endswith(b'\n'):
        data+=exact(w,1,max(.001,deadline-time.monotonic()))
        need(len(data)<=1024,'excess ASCII line')
    need(b'\r' not in data,'unexpected CR')
    return data[:-1].decode('ascii')

def packets(w,total,kind,seq,ledger,progress,deadline):
    output=bytearray()
    while True:
        remaining=deadline-time.monotonic();need(remaining>0,'whole photo export deadline')
        rx=w.rx_count;h=exact(w,32,min(5,remaining))
        magic,k,s,off,n,t,c,hc=struct.unpack('<4s7I',h)
        need(magic==b'PP01' and crc(h[:28])==hc,'packet magic/header CRC')
        need(s==seq and t==total and off==len(output),'packet sequence/total/offset')
        if k==kind:
            need(n==min(1024,total-off) and n>0,'packet DATA length')
            remaining=deadline-time.monotonic();need(remaining>0,'whole photo export deadline')
            b=exact(w,n,min(5,remaining));need(crc(b)==c,'packet payload CRC');output+=b
        else:
            need(k==kind+1 and off==total and n==0 and c==crc(output),'packet END/full CRC')
        tx=w.tx_count;w.write(b'K')
        ledger.append(dict(rx_offset=rx,tx_ack_offset=tx,header_hex=h.hex()))
        if k==kind+1:break
        if len(output)%102400==0:progress(f'RX={len(output)}/{total}')
    return bytes(output)

def artifacts(folder,src,actual,summary,write):
    expected=reference.expected_from_source(src)
    need(expected==reference.expected_second_implementation(src),'reference implementations differ')
    comparison=reference.compare(expected,actual,src)
    blobs={'source.rgb565':src,'actual.rgb':actual,'expected.rgb':expected}
    # Preserve all raw artifacts and first mismatch even on data rejection.
    if write:
        for n,b in blobs.items():(folder/n).write_bytes(b)
        (folder/'comparison.json').write_text(json.dumps(comparison,indent=2)+'\n')
    need(comparison['all_equal'],'PC BYTE MISMATCH: '+str(comparison['first_mismatch']))
    need(crc(src)==int(summary[0],16),'source PC CRC differs from capture CRC')
    need(len(set(summary[1:]))==1 and crc(actual)==crc(expected)==int(summary[1],16),'output CRC closure')
    blobs.update({'source.png':reference.png_source565(src),'actual96.png':reference.png_rgb888(actual),
                  'expected96.png':reference.png_rgb888(expected)})
    # Verify encoded PNG pixels, not just their file hashes.
    for n,raw in (('actual96.png',actual),('expected96.png',expected)):
        width,height,pixels=reference.decode_png(blobs[n]);need((width,height,pixels)==(96,96,raw),'PNG pixels '+n)
    width,height,pixels=reference.decode_png(blobs['source.png'])
    want=b''.join(bytes(reference.expand565(int.from_bytes(src[i:i+2],'little'))) for i in range(0,len(src),2))
    need((width,height,pixels)==(1280,720,want),'source PNG pixel expansion')
    for n,b in blobs.items():
        if write:(folder/n).write_bytes(b)
        else:need((folder/n).read_bytes()==b,'artifact differs from original RX '+n)
    if not write:need(json.loads((folder/'comparison.json').read_text())==comparison,'comparison ledger')
    return comparison

def exchange(w,m,folder,write=True,progress=lambda _:None):
    result=dict(loader_records=[],packets=[])
    for p in loader_plan(m):
        result['loader_records'].append(dict(name=p['name'],tx_offset=w.tx_count,rx_offset=w.rx_count))
        w.write(bytes.fromhex(p['tx_hex']));need(exact(w,60)==bytes.fromhex(p['expected_hex']),'Loader '+p['name'])
    for s in (HEADER,'SENSOR_ID=00005640 CONFIG=OK','PP_READY'):
        got=line(w);need(got==s,'application banner/error: '+got);progress(got)
    w.write(b'G');w.write(b'C')
    s=line(w);match=SUMMARY.fullmatch(s);need(match is not None,'capture/PP summary/error: '+s)
    result['summary']=s;summary=match.groups();progress(s)
    w.write(b'D');need(line(w)=='PPX_BEGIN','missing export boundary')
    deadline=time.monotonic()+600
    src=packets(w,1843200,1,1,result['packets'],progress,deadline)
    actual=packets(w,27648,3,1,result['packets'],progress,deadline)
    need(line(w)=='PPX_DONE','missing export end')
    s=line(w);r=RELEASED.fullmatch(s);need(r is not None,'release/error: '+s)
    claims,discards,glob,state,cycles,elapsed=r.groups()
    need(int(claims)==int(glob)==1+int(discards) and int(discards) in (0,1),'claim/discard/global ledger')
    need(int(state,16)&0x2cf==0 and 0<int(cycles)<3*93750000,'camera not FREE/stopped or PP cycles')
    result['release']=s;result['comparison']=artifacts(folder,src,actual,summary,write)
    progress('PC_BYTE_COMPARE=PASS 27648/27648; PC_CRC=MATCH')
    w.write(b'Q');got=line(w);need(got==END,'session finish/error: '+got)
    result['finish']=got
    return result

class Replay:
    def __init__(self,rx,tx):self.rx=rx;self.tx=tx;self.rx_count=0;self.tx_count=0
    def read(self,n):
        b=self.rx[self.rx_count:self.rx_count+n];self.rx_count+=len(b);return b
    def write(self,b):
        need(self.tx[self.tx_count:self.tx_count+len(b)]==b,'original TX differs/no retries allowed')
        self.tx_count+=len(b);return len(b)

def verify(folder,origin='ACTUAL_SERIAL'):
    folder=Path(folder);r=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    need(origin in ('ACTUAL_SERIAL','OFFLINE_SYNTHETIC_TEST') and r['evidence_origin']==origin,'synthetic is not actual board evidence')
    need(r['status']=='PHOTO_DATA_PASS_VISUAL_PENDING','incomplete/failed session')
    if origin=='ACTUAL_SERIAL':need(r['serial_opened'] and r['user_KEY0_confirmation'],'serial/reset not confirmed')
    m=json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
    need(m==r['application'] and sha(folder/'manifest.json')==r['manifest_sha256'],'manifest/application identity')
    need(sha(folder/'application.bin')==m['bin_sha256'] and crc((folder/'application.bin').read_bytes())==m['crc32'],'fixed BIN identity')
    for n,d in r['file_sha256'].items():need(sha(folder/n)==d,'changed original evidence '+n)
    w=Replay((folder/'uart.rx.bin').read_bytes(),(folder/'uart.tx.bin').read_bytes())
    rebuilt=exchange(w,m,folder,False);need(rebuilt==r['session'],'raw/ledger mismatch')
    need(w.rx_count==len(w.rx) and w.tx_count==len(w.tx),'extra RX/TX')
    return dict(status='PHOTO_RAW_REPLAY_BYTE_CRC_PNG_PASS_VISUAL_PENDING',evidence_origin=origin,
                bytes_compared=27648,groups=1,source_seq=1,source_buf=0,packets=len(rebuilt['packets']),
                visual_review='PENDING',CRC_is_not_substitute_for_byte_compare=True)

def live(args,m):
    gate=json.loads(RELEASE.read_text(encoding='utf-8'))
    need(gate['status']=='SOL_SOFTWARE_REVIEWED_USER_AUTHORIZED_BOARD_FIRST' and gate['firmware_sha256']==m['bin_sha256'],'wrong board-first release identity')
    need(args.log_dir is not None and not args.log_dir.exists(),'new --log-dir required')
    folder=args.log_dir.resolve();folder.mkdir(parents=True,exist_ok=False)
    shutil.copyfile(args.manifest,folder/'manifest.json');shutil.copyfile(ROOT/m['bin_path'],folder/'application.bin')
    shutil.copyfile(RELEASE,folder/'board_release.json')
    r=dict(status='RUNNING',evidence_origin='ACTUAL_SERIAL',application=m,manifest_sha256=sha(args.manifest),
           serial_opened=False,user_KEY0_confirmation=False,retry_count=0,port=args.port,baud=115200,
           tool_sha256={p.name:sha(p) for p in HERE.glob('*.py')},PDS_started=False,visual_review='PENDING')
    save(folder,r);w=None
    try:
        input('使用本版已通过时序的预处理位流。关闭串口助手，按KEY0后释放，等待DDR就绪；摆好新画面后按Enter：')
        r['user_KEY0_confirmation']=True
        import serial
        with serial.Serial(args.port,115200,timeout=.05,write_timeout=2,xonxoff=False,rtscts=False,dsrdtr=False) as p:
            r['serial_opened']=True;w=Wire(p,folder)
            try:
                need(p.in_waiting==0,'unexpected initial bytes; no flush/retry')
                r['session']=exchange(w,m,folder,True,print)
                time.sleep(.05);need(p.in_waiting==0,'extra bytes after finish')
            except BaseException:
                deadline=time.monotonic()+2
                while time.monotonic()<deadline:
                    try:w.read(4096)
                    except Exception:break
                raise
        w.close();w=None;r['status']='PHOTO_DATA_PASS_VISUAL_PENDING'
    except BaseException as e:r.update(status='STOPPED_FIRST_FAILURE',error=repr(e));raise
    finally:
        if w:w.close()
        r['file_sha256']={p.name:sha(p) for p in folder.iterdir() if p.is_file() and p.name not in ('result.json','verified.json')}
        save(folder,r)
    checked=verify(folder);(folder/'verified.json').write_text(json.dumps(checked,indent=2)+'\n')
    print(json.dumps(checked,indent=2));print('查看图片：',folder/'source.png',folder/'actual96.png')

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--manifest',type=Path,default=DEFAULT)
    p.add_argument('--port',default='COM9');p.add_argument('--log-dir',type=Path)
    p.add_argument('--plan-only',action='store_true');p.add_argument('--verify',type=Path);a=p.parse_args()
    if a.verify:print(json.dumps(verify(a.verify),indent=2));return
    m=image(a.manifest)
    if a.plan_only:
        print(json.dumps(dict(status='PHOTO_PLAN_ONLY_NO_SERIAL',bytes=m['bytes'],sha256=m['bin_sha256'],
            loader_responses=len(loader_plan(m)),photos=1,source_bytes=1843200,output_bytes=27648,
            wire_payload_min_seconds=(1843200+27648)*10/115200),indent=2));return
    live(a,m)
if __name__=='__main__':main()
