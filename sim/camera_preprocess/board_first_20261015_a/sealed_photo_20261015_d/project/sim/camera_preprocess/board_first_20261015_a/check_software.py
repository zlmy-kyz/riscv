"""Exercise exact photo firmware C and actual PC wire exchange on synthetic native models."""
import argparse,hashlib,json,shutil,struct,subprocess,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/camera_preprocess_photo'))
import run as photo
import reference
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',default='checks_a');a=p.parse_args()
    out=HERE/a.out;out.mkdir(exist_ok=False)
    def cmd(label,argv):
        r=subprocess.run(list(map(str,argv)),cwd=ROOT,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=60)
        (out/(label+'.stdout.log')).write_bytes(r.stdout)
        (out/(label+'.command.json')).write_text(json.dumps(dict(argv=list(map(str,argv)),cwd=str(ROOT),returncode=r.returncode),indent=2)+'\n')
        assert r.returncode==0,(label,r.stdout.decode(errors='replace'));return r.stdout
    test=ROOT/'tests/camera_preprocess_photo';exe=out/'native_flow.exe'
    cmd('native_compile',['D:/mingw64/bin/gcc.exe','-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-int-to-pointer-cast',
                         test/'native_flow.c',test/'preprocess_ref.c',test/'pp01_wire.c','-o',exe])
    m=photo.image(photo.DEFAULT);patterns={}
    for name,color in [('red',0xf800),('green',0x07e0),('blue',0x001f)]:patterns[name]=struct.pack('<H',color)*(1280*720)
    patterns['coordinate']=b''.join(struct.pack('<H',(((3*x+5*y+7)&31)<<11)|(((11*x+7*y+13)&63)<<5)|((x^(3*y)^17)&31)) for y in range(720) for x in range(1280))
    cases={};paths={}
    for name,src in patterns.items():
        folder=out/name;folder.mkdir();source=folder/'input.rgb565';expected=folder/'golden.rgb'
        source.write_bytes(src);expected.write_bytes(reference.expected_from_source(src));paths[name]=(source,expected)
        meta=json.loads(cmd('flow_'+name,[exe,source,expected,'normal',folder/'native']))
        assert meta['status']==2 and meta['pp_starts']==meta['stream_starts']==1 and meta['releases']==2
        assert meta['final_state']&0x2cf==0 and meta['final_state']&32!=0,'idle ACTIVE_BUF=B must be accepted'
        assert meta['clock_elapsed']>2**32 and meta['software_elapsed']==meta['clock_elapsed']-4000,'64-bit tick extension across wraps'
        cases[name]=meta
    src,expected=paths['coordinate']
    for case,reason in [('no_tail',None),('pp_error','PP_ERROR'),('timeout','PP_TIMEOUT'),('metadata','PP_READ_BEATS'),
                        ('data','OUTPUT_BYTE_MISMATCH'),('source_crc','SOURCE_CRC_MISMATCH'),
                        ('pp_crc','CPU_READ_CRC_MISMATCH'),('ack','EXPORT_ACK_BYTE'),('release','RELEASE_NOT_ACCEPTED')]:
        folder=out/case;folder.mkdir();meta=json.loads(cmd('flow_'+case,[exe,src,expected,case,folder/'native']))
        wire=(folder/'native.fw.tx.bin').read_bytes()
        assert meta['status']==(2 if reason is None else 3),(case,meta)
        assert meta['stream_starts']==1 and meta['pp_starts']==1,'first failure must not recapture or restart'
        if reason:assert ('REASON='+reason).encode() in wire and photo.END.encode() not in wire,case
        if case=='no_tail':assert meta['releases']==1
        cases[case]=meta
    # Native firmware UART output, not a separately invented successful ASCII transcript.
    firmware_tx=(out/'coordinate/native.fw.tx.bin').read_bytes()
    firmware_rx=(out/'coordinate/native.fw.rx.bin').read_bytes()
    plans=photo.loader_plan(m)
    raw_rx=b''.join(bytes.fromhex(p['expected_hex']) for p in plans)+firmware_tx
    raw_tx=b''.join(bytes.fromhex(p['tx_hex']) for p in plans)+firmware_rx
    class Fragmented:
        def __init__(self,rx,tx):self.rx=rx;self.tx=tx;self.rx_count=self.tx_count=0
        def read(self,n):
            b=self.rx[self.rx_count:self.rx_count+min(n,7)];self.rx_count+=len(b);return b
        def write(self,b):
            assert self.tx[self.tx_count:self.tx_count+len(b)]==b,'CPU/PC command/ACK incompatibility'
            self.tx_count+=len(b);return len(b)
    good=out/'wire_good';good.mkdir();w=Fragmented(raw_rx,raw_tx)
    session=photo.exchange(w,m,good)
    assert w.rx_count==len(raw_rx) and w.tx_count==len(raw_tx)
    (good/'uart.rx.bin').write_bytes(raw_rx);(good/'uart.tx.bin').write_bytes(raw_tx)
    shutil.copyfile(photo.DEFAULT,good/'manifest.json');shutil.copyfile(ROOT/m['bin_path'],good/'application.bin')
    r=dict(status='PHOTO_DATA_PASS_VISUAL_PENDING',evidence_origin='OFFLINE_SYNTHETIC_TEST',
        application=m,manifest_sha256=sha(photo.DEFAULT),session=session,serial_opened=False,retry_count=0)
    r['file_sha256']={p.name:sha(p) for p in good.iterdir() if p.is_file()}
    photo.save(good,r);replay=photo.verify(good,'OFFLINE_SYNTHETIC_TEST')
    rejected={}
    try:photo.verify(good)
    except ValueError:rejected['synthetic_is_not_board']='REJECTED'
    else:raise AssertionError('synthetic accepted as board')
    # Mutate actual bytes and ledger inputs independently of the checker.
    first=session['packets'][0]['rx_offset'];rgb=session['packets'][1801]['rx_offset']
    variants={}
    def changed(offset):b=bytearray(raw_rx);b[offset]^=1;return bytes(b)
    variants['header_crc']=(changed(first+31),raw_tx)
    variants['payload_crc']=(changed(first+32),raw_tx)
    for kind,index,value in [('wrong_kind',4,3),('wrong_seq',8,2),('wrong_offset',12,1),('wrong_length',16,1023)]:
        b=bytearray(raw_rx);struct.pack_into('<I',b,first+index,value);struct.pack_into('<I',b,first+28,zlib.crc32(b[first:first+28])&0xffffffff)
        variants[kind]=(bytes(b),raw_tx)
    variants['short_rx']=(raw_rx[:rgb+36],raw_tx)
    variants['bad_ack']=(raw_rx,raw_tx[:session['packets'][0]['tx_ack_offset']]+b'X'+raw_tx[session['packets'][0]['tx_ack_offset']+1:])
    variants['bad_summary']=(raw_rx.replace(b'ERR=00000000',b'ERR=00000001',1),raw_tx)
    for name,(rx,tx) in variants.items():
        d=out/('reject_'+name);d.mkdir();w=Fragmented(rx,tx)
        try:photo.exchange(w,m,d)
        except (ValueError,AssertionError):rejected[name]='REJECTED'
        else:raise AssertionError('bad wire accepted: '+name)
    # Same-CRC corruption: solve the last four bytes so CRC agrees, then require byte comparison to reject.
    source=src.read_bytes();original=expected.read_bytes();bad=bytearray(original);bad[17]^=1
    patch=len(bad)-4;base=zlib.crc32(bad)&0xffffffff;columns=[]
    for bit in range(32):
        b=bytearray(bad);b[patch+bit//8]^=1<<(bit%8);columns.append((zlib.crc32(b)&0xffffffff)^base)
    basis={}
    for i,value in enumerate(columns):
        mask=1<<i
        while value:
            top=value.bit_length()-1
            if top not in basis:basis[top]=(value,mask);break
            v,k=basis[top];value^=v;mask^=k
    target=(zlib.crc32(original)&0xffffffff)^base;solution=0
    while target:
        v,k=basis[target.bit_length()-1];target^=v;solution^=k
    for bit in range(32):
        if solution>>bit&1:bad[patch+bit//8]^=1<<(bit%8)
    assert bad!=original and photo.crc(bad)==photo.crc(original)
    d=out/'reject_equal_crc_unequal_bytes';d.mkdir()
    c=f'{photo.crc(original):08x}';s=f'{photo.crc(source):08x}'
    try:photo.artifacts(d,source,bytes(bad),(s,c,c,c),True)
    except ValueError as e:assert 'BYTE MISMATCH' in str(e);rejected['equal_crc_unequal_bytes']='REJECTED'
    else:raise AssertionError('CRC collision bypassed byte compare')
    report=dict(status='PHOTO_SOFTWARE_NATIVE_AND_WIRE_PASS_NOT_BOARD',native_cases=cases,rejected=rejected,
        wire_replay=replay,firmware_sha256=m['bin_sha256'],manifest_sha256=sha(photo.DEFAULT),
        native_C_source_sha256=sha(test/'main.c'),script_sha256=sha(__file__),serial_opened=False,HDL_run=False,PDS_started=False)
    (out/'review.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(dict(status=report['status'],native_cases=len(cases),negative_cases=len(rejected),
                         review_sha256=sha(out/'review.json')),indent=2))
if __name__=='__main__':main()
