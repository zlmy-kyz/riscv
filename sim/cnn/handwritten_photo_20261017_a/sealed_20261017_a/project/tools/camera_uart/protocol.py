"""CAM1 framed RGB565 receiver. Standard library only; no serial side effects."""
import hashlib,json,re,struct,time,zlib
from pathlib import Path
WIDTH,HEIGHT=1280,720
BYTES=WIDTH*HEIGHT*2
CHUNK=1024
crc=lambda b:zlib.crc32(b)&0xffffffff

def need(ok,why):
    if not ok:raise ValueError(why)

def header(kind,seq,offset,length,data_crc):
    p=struct.pack('<4s6I',b'CAM1',kind,seq,offset,length,BYTES,data_crc)
    return p+struct.pack('<I',crc(p))

def unpack(raw):
    need(len(raw)==32,'short CAM1 header')
    magic,kind,seq,offset,length,total,data_crc,hcrc=struct.unpack('<4s7I',raw)
    need(magic==b'CAM1' and hcrc==crc(raw[:28]),'CAM1 magic/header CRC')
    need(total==BYTES and kind in (1,2),'CAM1 type/total')
    return dict(kind=kind,seq=seq,offset=offset,length=length,total=total,crc=data_crc)

def exact(port,n,seconds=5):
    end=time.monotonic()+seconds;b=bytearray()
    while len(b)<n:
        need(time.monotonic()<end,'UART timeout/short read')
        part=port.read(n-len(b))
        if part:b.extend(part)
    return bytes(b)

def line(port,seconds=30):
    b=bytearray();end=time.monotonic()+seconds
    while True:
        b+=exact(port,1,max(.001,end-time.monotonic()))
        need(len(b)<=512,'excess UART line length')
        if b.endswith(b'\n'):break
    s=b.decode('ascii').strip()
    need(not s.startswith(('ERROR=','TRAP_CAUSE=')),s)
    return s

def parse_summary(lines,seq):
    text='\n'.join(lines)
    def one(pattern):
        r=re.findall(pattern,text,re.M);need(len(r)==1,'missing/duplicate summary: '+pattern);return r[0]
    dims=tuple(map(int,one(r'^FRAME=(\d+) PIXELS=(\d+) BYTES=(\d+) WRITES=(\d+)$')))
    need(dims==(seq,921600,BYTES,57600),'frame sequence/geometry/write count')
    c=tuple(int(v,16) for v in one(r'^CRC_CAPTURE=([0-9a-fA-F]{8}) CRC_CPU=([0-9a-fA-F]{8}) CRC_REREAD=([0-9a-fA-F]{8})$'))
    need(c[0]==c[1]==c[2],'capture/CPU/reread CRC mismatch')
    need(one(r'^(REREAD=OK OVERFLOW=0 ERROR=0 CPU_CHECK=PASS)$') is not None,'CPU completion')
    return dict(seq=seq,pixels=dims[1],bytes=dims[2],writes=dims[3],crc32=c[0])

def read_summary(port,seq):
    start=port.rx_count;lines=[]
    for _ in range(12):
        s=line(port);lines.append(s)
        if s=='REREAD=OK OVERFLOW=0 ERROR=0 CPU_CHECK=PASS':break
    else:raise ValueError('missing CPU summary finish')
    info=parse_summary(lines,seq)
    return dict(info,lines=lines,rx_start=start,rx_end=port.rx_count)

def png565(raw):
    need(len(raw)==BYTES,'RGB565 size')
    scan=bytearray()
    for y in range(HEIGHT):
        scan.append(0)
        for x in range(WIDTH):
            v=struct.unpack_from('<H',raw,(y*WIDTH+x)*2)[0]
            scan.extend((((v>>11)*255+15)//31,(((v>>5)&63)*255+31)//63,((v&31)*255+15)//31))
    def block(kind,data):return struct.pack('>I',len(data))+kind+data+struct.pack('>I',crc(kind+data))
    return b'\x89PNG\r\n\x1a\n'+block(b'IHDR',struct.pack('>2I5B',WIDTH,HEIGHT,8,2,0,0,0))+block(b'IDAT',zlib.compress(scan,6))+block(b'IEND',b'')

class Wire:
    """Record the complete actual byte streams, including invalid/partial packets."""
    def __init__(self,port,folder):
        self.port=port;self.rx_count=0;self.tx_count=0
        self.rx=(Path(folder)/'uart.rx.bin').open('xb');self.tx=(Path(folder)/'uart.tx.bin').open('xb')
    @property
    def in_waiting(self):return self.port.in_waiting
    def read(self,n):
        b=self.port.read(n);self.rx.write(b);self.rx_count+=len(b);return b
    def write(self,b):
        n=self.port.write(b);self.tx.write(b[:n]);self.tx_count+=n
        need(n==len(b),'short UART write');return n
    def close(self):self.rx.close();self.tx.close()

def receive_frame(port,folder,summary,row,progress=None):
    folder=Path(folder);seq=summary['seq'];expected=summary['crc32']
    partial=folder/f'frame_{seq:03d}.rgb565.partial'
    chunks=row.setdefault('chunks',[]);offset=0;whole=0
    deadline=time.monotonic()+600
    with partial.open('xb') as f:
        while True:
            need(time.monotonic()<deadline,'frame export deadline')
            position=port.rx_count;raw=exact(port,32);h=unpack(raw)
            need(h['seq']==seq and h['offset']==offset,'CAM1 sequence/offset')
            if h['kind']==2:
                need(offset==BYTES and h['length']==0 and h['crc']==expected and whole==expected,'PC full-frame CRC/END')
                ack=port.tx_count;port.write(b'K')
                row['end']=dict(rx_offset=position,header_hex=raw.hex(),tx_ack_offset=ack)
                break
            need(h['length']==min(CHUNK,BYTES-offset) and h['length']>0,'CAM1 block length')
            payload=exact(port,h['length']);need(crc(payload)==h['crc'],'CAM1 block CRC')
            f.write(payload);whole=zlib.crc32(payload,whole)&0xffffffff
            ack=port.tx_count;port.write(b'K')
            chunks.append(dict(rx_offset=position,header_hex=raw.hex(),offset=offset,length=len(payload),crc32=h['crc'],tx_ack_offset=ack))
            offset+=len(payload)
            if progress and len(chunks)%100==0:progress(offset)
    result=folder/f'frame_{seq:03d}.rgb565';partial.rename(result)
    raw=result.read_bytes();image=folder/f'frame_{seq:03d}.png';image.write_bytes(png565(raw))
    row.update(pc_crc32=whole,raw_path=result.name,png_path=image.name,visual_review='NOT_CONFIRMED',bytes=offset)
    return row

def verify_session(folder,loader_plan,expected_origin='ACTUAL_SERIAL'):
    """Offline byte-by-byte audit. Does not open serial or regenerate board evidence."""
    folder=Path(folder);r=json.loads((folder/'result.json').read_text(encoding='utf-8'))
    need(expected_origin in ('ACTUAL_SERIAL','OFFLINE_SYNTHETIC_TEST'),'unsupported evidence origin')
    need(r['evidence_origin']==expected_origin and r['status']=='UART_FRAME_DATA_CHECK_PASS_VISUAL_PENDING','session not completed frame data')
    if expected_origin=='ACTUAL_SERIAL':need(r['serial_opened'],'serial was not opened')
    need(hashlib.sha256((folder/'manifest.json').read_bytes()).hexdigest()==r['manifest_sha256'],'session manifest changed')
    need(json.loads((folder/'manifest.json').read_text(encoding='utf-8'))==r['application'],'manifest/application mismatch')
    image=(folder/'application.bin').read_bytes()
    need(hashlib.sha256(image).hexdigest()==r['application']['bin_sha256'] and crc(image)==r['application']['crc32'],'downloaded image identity')
    rx=(folder/'uart.rx.bin').read_bytes();tx=(folder/'uart.tx.bin').read_bytes();a=b=0
    rows=loader_plan(r['application'])
    need(len(rows)==len(r['loader_records']),'Loader response count')
    for plan,record in zip(rows,r['loader_records']):
        sent=bytes.fromhex(plan['tx_hex']);reply=bytes.fromhex(plan['expected_hex'])
        need(tx[a:a+len(sent)]==sent and rx[b:b+60]==reply,'actual Loader transcript mismatch')
        need(record['tx_offset']==a and record['rx_offset']==b,'Loader offsets')
        a+=len(sent);b+=60
    ready=rx[r['ready_rx_start']:r['ready_rx_end']].decode('ascii')
    need(r['ready_rx_start']==b,'ready byte order');b=r['ready_rx_end']
    need('SENSOR_ID=00005640 CONFIG=OK\n' in ready and ready.endswith('CAMERA_READY\n'),'sensor/config original UART bytes')
    prior=None
    for seq,row in enumerate(r['frames'],1):
        s=row['summary'];lines=rx[s['rx_start']:s['rx_end']].decode('ascii').strip().splitlines()
        need(s['seq']==seq and row['capture_tx_offset']==a and s['rx_start']==b,'capture byte order')
        a+=1;b=s['rx_end']
        need(parse_summary(lines,s['seq'])=={k:s[k] for k in ['seq','pixels','bytes','writes','crc32']},'summary differs from raw RX')
        need(tx[row['capture_tx_offset']:row['capture_tx_offset']+1]==b'C','capture command')
        if prior is not None:need(s['seq']==prior['seq']+1 and s['crc32']!=prior['crc32'],'sequence/changed scene')
        prior=s
        need(row['export_tx_offset']==a and tx[a:a+1]==b'D' and row['export_rx_start']==b,'export command/order')
        a+=1;need(rx[b:b+13]==b'EXPORT_BEGIN\n','export start bytes');b+=13
        raw=(folder/row['raw_path']).read_bytes();need(len(raw)==BYTES and crc(raw)==s['crc32']==row['pc_crc32'],'raw file/PC CRC')
        offset=0
        for c in row['chunks']:
            need(c['rx_offset']==b and c['tx_ack_offset']==a,'chunk byte order')
            wire=rx[c['rx_offset']:c['rx_offset']+32];h=unpack(wire)
            need(wire.hex()==c['header_hex'] and h==dict(kind=1,seq=s['seq'],offset=offset,length=min(CHUNK,BYTES-offset),total=BYTES,crc=c['crc32']),'chunk header ledger')
            payload=rx[c['rx_offset']+32:c['rx_offset']+32+h['length']]
            need(payload==raw[offset:offset+len(payload)] and crc(payload)==h['crc'],'raw RX payload')
            need(tx[c['tx_ack_offset']:c['tx_ack_offset']+1]==b'K','chunk ACK')
            offset+=len(payload)
            b+=32+len(payload);a+=1
        need(offset==BYTES,'full export coverage')
        end=row['end'];h=unpack(rx[end['rx_offset']:end['rx_offset']+32])
        need(end['rx_offset']==b and end['tx_ack_offset']==a,'END byte order')
        need(h==dict(kind=2,seq=s['seq'],offset=BYTES,length=0,total=BYTES,crc=s['crc32']),'END metadata')
        need(tx[end['tx_ack_offset']:end['tx_ack_offset']+1]==b'K','END ACK')
        b+=32;a+=1
        ending=f'EXPORT_DONE FRAME={seq} PC_ACK=1\n'.encode()
        need(rx[b:b+len(ending)]==ending,'export finish bytes');b+=len(ending)
        need((folder/row['png_path']).read_bytes()==png565(raw),'PNG mapping differs from RGB565 LE row-major')
    need(len(r['frames'])==r['requested_frames'] and r['user_KEY0_confirmation'] and not r['summary_only'],'session scope')
    if len(r['frames'])==2:need(r['user_scene_change_confirmation'],'scene change confirmation missing')
    ending=f'SESSION_DONE CAPTURES={len(r["frames"])} EXPORTS={len(r["frames"])} CPU_CHECK=PASS\n'.encode()
    need(r['finish_tx_offset']==a and tx[a:a+1]==b'Q' and a+1==len(tx),'finish command/extra TX')
    need(r['finish_rx_start']==b and rx[b:]==ending,'finish/extra RX')
    return dict(status='ACTUAL_UART_FRAMES_RAW_BYTES_CRC_AND_PNG_VERIFIED_VISUAL_PENDING' if expected_origin=='ACTUAL_SERIAL' else 'OFFLINE_SYNTHETIC_WIRE_REPLAY_PASS',frames=len(r['frames']),crc32=[f"{f['summary']['crc32']:08x}" for f in r['frames']],visual_review='NOT_CONFIRMED')
