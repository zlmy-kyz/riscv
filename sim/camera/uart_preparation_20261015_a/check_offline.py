"""Native C CRC/header and synthetic wire checks. Never board/HDL evidence."""
import ctypes,hashlib,json,shutil,subprocess,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[2]
sys.path.insert(0,str(ROOT/'tools/camera_uart'))
import protocol as p
import capture
sha=lambda f:hashlib.sha256(Path(f).read_bytes()).hexdigest()

class SensorWire:
    def __init__(self,info,frames,mode=None):
        self.plan=capture.loader_plan(info);self.loader=0;self.buf=bytearray();self.frames=frames
        self.seq=0;self.exporting=False;self.offset=0;self.mode=mode
    @property
    def in_waiting(self):return len(self.buf)
    def read(self,n):
        n=min(n,37,len(self.buf));r=bytes(self.buf[:n]);del self.buf[:n];return r
    def packet(self):
        frame=self.frames[self.seq-1];off=self.offset
        if off==p.BYTES:
            self.buf.extend(p.header(2,self.seq,off,0,p.crc(frame)));return
        raw=frame[off:off+p.CHUNK];seq=self.seq;offset=off
        if self.mode=='bad_seq' and off==0:seq+=1
        if self.mode=='bad_offset' and off==0:offset+=4
        h=p.header(1,seq,offset,len(raw),p.crc(raw))
        if self.mode=='bad_header' and off==0:h=bytes([h[0]^1])+h[1:]
        if self.mode=='bad_payload' and off==0:raw=bytes([raw[0]^1])+raw[1:]
        self.buf.extend(h+raw)
    def write(self,b):
        if self.loader<len(self.plan):
            r=self.plan[self.loader];assert b==bytes.fromhex(r['tx_hex']);self.loader+=1
            self.buf.extend(bytes.fromhex(r['expected_hex']))
            if r.get('run'):self.buf.extend(b'CAMERA_APP=1\nSENSOR_ID=00005640 CONFIG=OK\nCAMERA_READY\n')
        elif self.exporting:
            assert b==b'K'
            if self.offset==p.BYTES:
                self.exporting=False;self.buf.extend(f'EXPORT_DONE FRAME={self.seq} PC_ACK=1\n'.encode())
            else:self.offset+=p.CHUNK;self.packet()
        elif b==b'C':
            self.seq+=1;c=p.crc(self.frames[self.seq-1])
            self.buf.extend((f'FRAME={self.seq} PIXELS=921600 BYTES=1843200 WRITES=57600\n'
                             f'CRC_CAPTURE={c:08x} CRC_CPU={c:08x} CRC_REREAD={c:08x}\n'
                             'REREAD=OK OVERFLOW=0 ERROR=0 CPU_CHECK=PASS\n').encode())
        elif b==b'D':self.buf.extend(b'EXPORT_BEGIN\n');self.exporting=True;self.offset=0;self.packet()
        elif b==b'Q':self.buf.extend(f'SESSION_DONE CAPTURES={self.seq} EXPORTS={self.seq} CPU_CHECK=PASS\n'.encode())
        else:raise AssertionError(b)
        return len(b)

def main():
    out=HERE/'offline_tests';out.mkdir(exist_ok=False)
    src=ROOT/'tests/camera_uart/crc32.c';dll=out/'crc_host.dll'
    argv=['D:/mingw64/bin/gcc.exe','-shared','-O2','-Wall','-Wextra','-Werror',str(src),'-o',str(dll)]
    r=subprocess.run(argv,capture_output=True,text=True,timeout=60)
    (out/'native_compile.log').write_text(r.stdout+r.stderr,encoding='utf-8')
    (out/'native_compile.command.json').write_text(json.dumps(dict(argv=argv,returncode=r.returncode),indent=2));assert r.returncode==0,r.stderr
    lib=ctypes.CDLL(str(dll));u8=ctypes.c_uint8;u32=ctypes.c_uint32
    lib.crc32_bytes.argtypes=[ctypes.POINTER(u8),u32];lib.crc32_bytes.restype=u32
    lib.crc32_words.argtypes=[ctypes.POINTER(u32),u32];lib.crc32_words.restype=u32
    lib.camera_header.argtypes=[ctypes.POINTER(u8),u32,u32,u32,u32,u32,u32]
    lib.crc32_init()
    frames=[(ROOT/f'sim/camera/key/generated/frame{i}.bin').read_bytes() for i in (1,2)]
    native=[]
    for raw in [b'',b'123456789',bytes(range(256)),*frames]:
        buf=(u8*len(raw)).from_buffer_copy(raw);c=lib.crc32_bytes(buf,len(raw));assert c==p.crc(raw)
        if len(raw)%4==0:
            words=(u32*(len(raw)//4)).from_buffer_copy(raw)
            assert lib.crc32_words(words,len(raw)//4)==c
        native.append(dict(bytes=len(raw),CRC=f'{c:08x}'))
    for kind,seq,off,n,c in [(1,1,0,1024,0x12345678),(1,2,p.BYTES-1024,1024,0),(2,2,p.BYTES,0,p.crc(frames[1]))]:
        buf=(u8*32)();lib.camera_header(buf,kind,seq,off,n,p.BYTES,c)
        assert bytes(buf)==p.header(kind,seq,off,n,c)
    fixture=out/'offline_fixture.bin';fixture.write_bytes(bytes(range(256))*4)
    info=dict(status='OFFLINE_FIXTURE_NOT_A_BOARD_IMAGE',bin_path=fixture.relative_to(ROOT).as_posix(),
              bin_sha256=sha(fixture),bytes=fixture.stat().st_size,crc32=p.crc(fixture.read_bytes()))
    outcomes={}
    for mode in [None,'bad_header','bad_payload','bad_seq','bad_offset','same_scene']:
        folder=out/('positive' if mode is None else mode);folder.mkdir()
        case_frames=frames if mode!='same_scene' else [frames[0],frames[0]]
        r=dict(status='RUNNING',evidence_origin='OFFLINE_SYNTHETIC_TEST',serial_opened=False,
               application=info,loader_records=[],frames=[],requested_frames=2,summary_only=False,user_KEY0_confirmation=True)
        (folder/'manifest.json').write_text(json.dumps(info,indent=2)+'\n',encoding='utf-8')
        r['manifest_sha256']=sha(folder/'manifest.json');shutil.copyfile(fixture,folder/'application.bin')
        wire=p.Wire(SensorWire(info,case_frames,mode),folder)
        try:
            capture.execute(wire,info,folder,r,scene_confirm=lambda _:None,progress=lambda _:None)
            assert mode is None,'negative case was accepted'
            wire.close();wire=None;r['status']='UART_FRAME_DATA_CHECK_PASS_VISUAL_PENDING';capture.save(folder,r)
            result=p.verify_session(folder,capture.loader_plan,expected_origin='OFFLINE_SYNTHETIC_TEST')
            assert result['status']=='OFFLINE_SYNTHETIC_WIRE_REPLAY_PASS';outcomes['positive']=result
        except ValueError as exc:
            assert mode is not None,str(exc);outcomes[mode]=dict(status='EXPECTED_REJECTION',reason=str(exc))
            r.update(status='EXPECTED_OFFLINE_REJECTION',error=str(exc))
        finally:
            if wire:wire.close()
            capture.save(folder,r)
    # Replay must reject tampering in the preserved original RX stream.
    altered=out/'tampered_rx';shutil.copytree(out/'positive',altered)
    record=json.loads((altered/'result.json').read_text());position=record['frames'][0]['chunks'][0]['rx_offset']+32
    data=bytearray((altered/'uart.rx.bin').read_bytes());data[position]^=1;(altered/'uart.rx.bin').write_bytes(data)
    try:p.verify_session(altered,capture.loader_plan,expected_origin='OFFLINE_SYNTHETIC_TEST');raise AssertionError('tampering accepted')
    except ValueError as exc:outcomes['tampered_rx']=dict(status='EXPECTED_REJECTION',reason=str(exc))
    report=dict(status='CAMERA_UART_OFFLINE_NATIVE_C_AND_PROTOCOL_CHECK_PASS_NOT_BOARD',native_C=native,
                headers_C_vs_Python=3,wire_cases=outcomes,HDL_run=False,serial_opened=False,board='NOT_RUN')
    (HERE/'offline_review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
