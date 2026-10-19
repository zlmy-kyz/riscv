"""Independent raw-data checks; no expected data is recovered from DUT writes."""
import argparse
import json
import re
import zlib
from pathlib import Path
from prepare import frame

HERE = Path(__file__).resolve().parent

def need(test, message):
    if not test:
        raise AssertionError(message)

def rows(path):
    with Path(path).open(encoding='utf-8', errors='strict') as f:
        for line in f:
            yield line.rstrip('\n').split()

def text_ok(path, marker):
    text = Path(path).read_text(encoding='utf-8')
    need(text.count(marker)==1, f'{path}: missing/duplicate finish marker')
    need(not re.search(r'RESULT: FAIL|\*\* (?:Fatal|Error)|Error loading design|Iteration limit',text,re.I),f'{path}: failure')
    return text

def check_sccb(out):
    text=text_ok(out/'sccb.transcript','RESULT: PASS camera_sccb')
    cases=re.findall(r'^#?\s*CASE SCCB (\d+) (\d+) (\d+) (\d+)',text,re.M)
    need([tuple(map(int,r)) for r in cases]==[(0,244,8,0),*( (k,4,0,1) for k in range(1,5)),(5,244,1,6),(6,244,7,7)],'SCCB cases/counts')
    # Reconstruct wire transactions, compare the write table and read list directly.
    table=[int(s,16) for s in (HERE/'generated/config.hex').read_text().splitlines()]
    normal=text.split('CASE SCCB 0')[0]
    packets={}
    for txn,idx,value,ack in re.findall(r'SCCB_BYTE \d+ (\d+) (\d+) ([\da-fA-F]+) (\d+)',normal):
        packets.setdefault(int(txn),[]).append((int(idx),int(value,16),int(ack)))
    writes=[]
    for packet in packets.values():
        need(all(a==1 for _,_,a in packet),'normal SCCB NACK')
        if len(packet)==4:
            need([i for i,_,_ in packet]==[0,1,2,3] and packet[0][1]==0x78,'SCCB byte order')
            writes.append((packet[1][1]<<16)|(packet[2][1]<<8)|packet[3][1])
    need(writes==table,'SCCB missing/reordered/extra table write')
    reads=[(int(a,16),int(b,16)) for a,b in re.findall(r'SCCB_READ \d+ ([\da-fA-F]+) ([\da-fA-F]+)',normal)]
    need(reads==[(0x300a,0x56),(0x300b,0x40),(0x3808,5),(0x3809,0),(0x380a,2),(0x380b,0xd0),(0x4300,0x61),(0x501f,1)],'SCCB eight readbacks')
    return dict(cases=7,writes=244,readbacks=8,nack_byte_positions=4)

def check_faults(out):
    text=text_ok(out/'faults.transcript','RESULT: PASS camera_faults')
    cases=re.findall(r'^#?\s*CASE FAULT (\d+) (\d+) (\d+) (\d+)',text,re.M)
    need([int(c[0]) for c in cases]==list(range(8)),'missing fault case')
    need([int(c[2]) for c in cases]==[0,3,2,5,5,0,0,5],'fault error codes')
    need(int(cases[0][1])==1024 and cases[-1][3]=='1','fault normal/stuck abort')
    need(len(re.findall(r'OVERFLOW_PENDING 0 2',text))==1,'overflow did not retain outstanding write')
    arb=re.findall(r'\bARB (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+) (\d+)',text)
    need(len(arb)==1,'arbiter summary')
    a=list(map(int,arb[0]));need(a[:4]==[6,6,24,6] and all(a[4:]),'arbiter trigger coverage')
    need(len(re.findall(r'\bAPERTURE [0-9a-fA-F]+ [01] [01] [01] [01]',text))==9,'aperture boundary/busy access coverage')
    expected=frame(1,128,128)
    current=None;count=0;counts=[]
    for line in text.splitlines():
        r=line.lstrip('# ').split()
        if not r:continue
        if r[0]=='ARMU':
            if current is not None:counts.append(count)
            current=int(r[1]);count=0
        elif r[0]=='CAMW':
            _,which,index,address,value=r
            need(int(index)==count and int(address,16)==0x400000+count*8,'fault DMA address/order')
            actual=int(value,16).to_bytes(32,'little')
            need(actual==expected[count*32:(count+1)*32],f'fault DMA bytes case {current} beat {count}')
            count+=1
    counts.append(count)
    need(len(counts)==8 and counts[0]==1024 and counts[2]==1,'fault actual write coverage')
    t=re.findall(r'FAULT_TIMING (\d+) (\d+)',text)
    need(len(t)==1 and all(map(int,t[0])),'same-edge/delayed W not exercised')
    return dict(cases=8,write_prefix_beats=counts,arbiter=a)

def check_soc(out):
    text_ok(out/'soc.transcript','RESULT: PASS camera_soc_two_full_frames')
    expected={p:frame(p) for p in (1,2)}
    # Check the *driven pins* trace independently of both DUT and DDR writes.
    p=None;offset=0;seen=[]
    for r in rows(out/'dvp.log'):
        if r[0]=='FRAME':
            if p is not None:need(offset==1843200,'short actual DVP input')
            p=int(r[1]);need(r[2:4]==['1280','720'] and int(r[4])==(3 if p==2 else 0),'DVP geometry/boundary kind')
            seen.append(p);offset=0
        else:
            need(p in (1,2) and int(r[0],16).to_bytes(2,'little')==expected[p][offset:offset+2],'driven DVP input differs from independent pattern')
            offset+=2
    need(seen==[1,2] and offset==1843200,'actual input frame count/length')
    camera={1:0,2:0};last={};cpu_writes=0;pending=None;reads_pending=None;ar_counts=[0,0,0]
    aw_same=aw_sep=0;aw_cycle=None
    for r in rows(out/'bus.log'):
        kind=r[0];p,cycle,owner,address=int(r[1]),int(r[2]),int(r[3]),int(r[4],16)
        need(address%8==0,'native address alignment')
        if kind=='AW':
            need(pending is None,'AW while write pending');pending=(owner,address,p);aw_cycle=cycle
            need(owner in (1,2),'AW owner')
        elif kind=='W':
            need(pending==(owner,address,p),'W owner/address/epoch');pending=None
            aw_same+=cycle==aw_cycle;aw_sep+=cycle>aw_cycle
            value=int(r[5],16).to_bytes(32,'little');mask=int(r[6],16)
            if owner==2:
                need(p in (1,2),'camera outside frame epoch')
                offset=camera[p]*32
                need(address==0x400000+offset//4 and mask==0xffffffff,'camera native address/stride/strobe')
                need(value==expected[p][offset:offset+32],f'camera DDR data p={p} beat={camera[p]}')
                camera[p]+=1;last[p]=cycle
            else:
                need(address==0x4000 and mask==15 and int.from_bytes(value[:4],'little')==p,'CPU scratch write corrupted/routed')
                cpu_writes+=1
        elif kind=='AR':
            need(reads_pending is None,'AR while read outstanding');reads_pending=(p,owner,address)
            if 0x400000<=address<0x470800:
                need(owner==1,'frame fetched as instructions');ar_counts[p]+=1
        elif kind=='R':
            need(reads_pending==(p,owner,address),'R owner/address/epoch');reads_pending=None
            if 0x400000<=address<0x470800:
                actual=int(r[5],16).to_bytes(32,'little');offset=(address-0x400000)*4
                want=expected[p][offset:offset+32] if p else (0xdeadbeef).to_bytes(4,'little')*8
                need(actual==want,'native returned frame bytes')
        else:raise AssertionError('unknown bus record '+kind)
    need(pending is None and reads_pending is None,'unfinished transaction')
    need(camera=={1:57600,2:57600} and cpu_writes>0 and aw_same>0 and aw_sep>0,'native actual transaction coverage')
    need(ar_counts==[3,460803,460800],'frame cache/missing native reads')
    loads=[0,0,0];arms=[];done=[];reported=[];covers=[];status=[]
    for r in rows(out/'cpu.log'):
        kind=r[0]
        if kind=='LOAD':
            p,cycle,address,value=int(r[1]),int(r[2]),int(r[3],16),int(r[4],16)
            index=loads[p]
            if p==0:offset=[0,32,0][index]
            elif p==1 and index>=460800:offset=[0,32,0][index-460800]
            else:offset=index*4
            need(address==0x41000000+offset,'CPU full frame sequential read / priming address')
            want=int.from_bytes(expected[p][offset:offset+4],'little') if p else 0xdeadbeef
            need(value==want,'CPU returned stale/wrong frame data');loads[p]+=1
        elif kind=='ARM':arms.append((int(r[1]),int(r[2])))
        elif kind=='DONE':
            p,cycle,write_cycle,crc,size,pixels,seq=[int(v,16) if i==3 else int(v) for i,v in enumerate(r[1:])]
            need(write_cycle==last[p] and cycle>write_cycle,'DONE earlier than physical last W')
            need(crc==zlib.crc32(expected[p]) and size==1843200 and pixels==921600 and seq==p,'DONE atomic metadata/CRC')
            done.append((p,cycle))
        elif kind=='MMIO':
            p,cycle,off,value=int(r[1]),int(r[2]),int(r[3],16),int(r[4],16)
            if off==0 and value>2:
                need(value==zlib.crc32(expected[p]),'real CPU CRC report');reported.append((p,cycle))
            if off==16:status.append(value)
        elif kind=='COVER':covers.append(list(map(int,r[1:])))
        else:raise AssertionError('unknown CPU record '+kind)
    need(loads==[3,460803,460800] and [p for p,_ in arms]==[1,2] and [p for p,_ in done]==[1,2] and
         [p for p,_ in reported]==[1,2] and status==[1,2],'CPU full-frame/ARM/status coverage')
    need(arms[0][1]<done[0][1]<reported[0][1]<arms[1][1]<done[1][1]<reported[1][1],'capture/CRC/ARM ordering')
    need(len(covers)==1 and all(covers[0]) and covers[0][-1]==2,'SoC contention/backpressure coverage')
    return dict(camera_beats=camera,CPU_loads=loads,native_frame_AR=ar_counts,CPU_scratch_writes=cpu_writes,
                CRC32=[f'{zlib.crc32(expected[p]):08x}' for p in (1,2)],coverage=covers[0])

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);ap.add_argument('--job',choices=['sccb','faults','soc'],required=True)
    a=ap.parse_args()
    result={'sccb':check_sccb,'faults':check_faults,'soc':check_soc}[a.job](a.out)
    (a.out/(a.job+'.checked.json')).write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(status='RAW_CHECK_PASS',job=a.job,result=result)))

if __name__=='__main__':main()
