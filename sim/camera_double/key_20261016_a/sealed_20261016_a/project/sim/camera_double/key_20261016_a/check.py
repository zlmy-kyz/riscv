"""Independent byte/address/CRC/ownership/interleaving replay from original trace, never DUT-derived golden."""
import argparse,collections,json,re,zlib
from pathlib import Path
from prepare import frame
def data_input(path,kind):
    lines=iter(path.read_text().splitlines());count=0
    for line in lines:
        r=line.split();assert r[0]=='FRAME',r
        p,w,h,k=map(int,r[1:]);assert w==64 and h==(8 if kind=='soc' else 128)
        want=frame(p,w,h);actual=bytearray()
        for y in range(h):
            for x in range(w-(1 if k==1 and y==h-1 else 0)):
                raw=bytes.fromhex(next(lines));assert raw==want[(y*w+x)*2:(y*w+x)*2+2][::-1]
                actual+=raw[::-1]
        count+=1
    return count
def check_unit(out):
    path=out/'unit.log';rows=[r.split() for r in path.read_text().splitlines()];pub=[];pending=None
    offsets=collections.Counter();last={};starts=[];edges=0;cases=set();state=[0,0];bad=0
    full_begin=None;warm=[]
    for r in rows:
        if r[0]=='START':
            _,cycle,b,warmed=r;starts.append((int(cycle),int(b),int(warmed)));edges=0
        elif r[0]=='EDGE':edges+=1
        elif r[0]=='AW':
            assert pending is None;pending=(int(r[1]),int(r[3],16))
        elif r[0]=='W':
            p,cycle,address=int(r[1]),int(r[2]),int(r[3],16);assert pending==(p,address);pending=None
            b=int(address>=0x480000);base=0x480000 if b else 0x400000;off=offsets[p]*32
            assert p!=9,'DMA wrote an occupied/partial sensor frame'
            assert state[b]==1 and address==base+off//4
            want=frame(p,64,128);assert int(r[4],16).to_bytes(32,'little')==want[off:off+32]
            offsets[p]+=1;last[b]=cycle
        elif r[0]=='PUB':
            p,cycle,b,seq,crc,lastw,dropped=int(r[1]),int(r[2]),int(r[3]),int(r[4]),int(r[5],16),int(r[6]),int(r[7])
            assert seq==len(pub)+1 and offsets[p]==512 and cycle>last[b]==lastw
            assert crc==zlib.crc32(frame(p,64,128))&0xffffffff
            assert starts and edges==(1 if starts[-1][2] else 11) and dropped==(0 if starts[-1][2] else 10)
            warm.append(edges);pub.append((p,b,seq))
        elif r[0]=='STATE':
            cy,b,old,new=map(int,r[1:])
            assert state[b]==old;state[b]=new
        elif r[0]=='MMIO':
            _,cy,write,a,d,size,st,e,value=r
            if int(e):bad+=1
        elif r[0]=='CASE':cases.add(r[1])
        elif r[0]=='COVER':assert len(r)==8 and all(int(x)>0 for x in r[1:])
    assert pending is None and [p for p,b,s in pub]==[1,2,3,4,5,7,10,12] and bad>=16
    assert cases=={'FULL_WAIT_STABLE','STOP_DRAIN','STOP_ALLOCATION_RACE','ABORT_DRAIN_PRESERVE','SHORT_FRAME_PRESERVE','OVERFLOW_PRESERVE','MISSING_PCLK_TIMEOUT','RESET_CLEAR'}
    stdout=(out/'unit.stdout.log').read_text(errors='replace');probes=re.findall(r'^#?\s*APERTURE ([0-9a-f]{8}) (\d) (\d) (\d) (\d) (\d) (\d)',stdout,re.M)
    assert len(probes)==132
    for a,w,dual,busy,owned,ie,de in probes:
        a=int(a,16);w=int(w);dual=int(dual);owned=int(owned);inside=0x41000000<=a<0x41400000
        assert int(ie)==inside
        assert int(de)==(inside and (w or not (owned>>(bool(a&0x200000))&1)) if dual else inside and int(busy))
    return dict(publications=pub,illegal_MMIO_responses=bad,permissions=len(probes),frame_edges_per_publication=warm,cases=sorted(cases))
def check_soc(out):
    rows=[r.split() for r in (out/'cpu.log').read_text().splitlines()];pubs={};loads=collections.Counter();state=[0,0];owned=[];cases={};edges=0;warm=[];active=None
    for r in rows:
        if r[0]=='START':edges=0;active=int(r[2]);warm.append((int(r[1]),int(r[2]),int(r[3])))
        elif r[0]=='EDGE':edges+=1
        elif r[0]=='PUB':
            cycle,b,seq,crc,lastw,drop=int(r[1]),int(r[2]),int(r[3]),int(r[4],16),int(r[5]),int(r[6])
            assert seq==len(pubs)+1 and cycle>lastw
            assert crc==zlib.crc32(frame(seq,64,8))&0xffffffff
            assert edges==(11 if seq==1 else 1) and drop==(10 if seq==1 else 0)
            pubs[seq]=(b,cycle,crc,lastw)
        elif r[0]=='STATE':
            cy,b,old,new=map(int,r[1:]);assert state[b]==old;state[b]=new
        elif r[0]=='LOAD':
            cy,b,seq,a,d=int(r[1]),int(r[2]),int(r[3]),int(r[4],16),int(r[5],16)
            assert state[b]==3 and pubs[seq][0]==b
            off=a-(0x41000000+b*0x200000);assert off==loads[seq]*4
            assert d==int.from_bytes(frame(seq,64,8)[off:off+4],'little');loads[seq]+=1
        elif r[0]=='FULL_BEGIN':cases['begin']=int(r[1])
        elif r[0]=='FULL_END':cases['end']=int(r[1])
        elif r[0]=='COVER':assert len(r)==7 and all(int(v)>0 for v in r[1:])
    assert 4<=len(pubs)<=5 and all(loads[s]==256 for s in pubs) and set(state)=={0}
    bus=[r.split() for r in (out/'bus.log').read_text().splitlines()];pending=None;read=None;offsets=collections.Counter();native_reads=collections.Counter();lastW={};interleaved=0;cpu_stores=0;stress_values=[];same=0;separate=0
    for r in bus:
        k,p,cy,owner,a=r[0],int(r[1]),int(r[2]),int(r[3]),int(r[4],16)
        b=int(a>=0x480000);base=0x480000 if b else 0x400000
        if k=='AW':assert pending is None;pending=(p,cy,owner,a)
        elif k=='W':
            assert pending and pending[0]==p and pending[2:]==(owner,a)
            same+=pending[1]==cy;separate+=pending[1]!=cy;pending=None
            if owner==2:
                assert p in pubs and pubs[p][0]==b and a==base+offsets[p]*8 and int(r[6],16)==0xffffffff
                assert int(r[5],16).to_bytes(32,'little')==frame(p,64,8)[offsets[p]*32:offsets[p]*32+32]
                assert not cases['begin']<=cy<cases['end'];offsets[p]+=1;lastW[p]=cy
                if read and read[2]==1 and 0x400000<=read[3]<0x500000 and int(read[3]>=0x480000)!=b:interleaved+=1
            elif a==0x7000:
                assert int(r[6],16)==15;cpu_stores+=1;stress_values.append(int(r[5],16)&0xffffffff)
            else:assert a<0x8000,'CPU wrote a protected frame'
        elif k=='AR':assert read is None;read=(p,cy,owner,a)
        elif k=='R':
            assert read and read[0]==p and read[2:]==(owner,a);read=None
            if 0x400000<=a<0x500000:
                seq=max(s for s,v in pubs.items() if v[0]==b and v[1]<cy)
                off=(a-base)*4;assert int(r[5],16).to_bytes(32,'little')==frame(seq,64,8)[off:off+32];native_reads[seq]+=1
    assert pending is None and read is None and interleaved>0 and cpu_stores>0 and same>0 and separate>0
    assert all(offsets[s]==32 and lastW[s]==pubs[s][3] and native_reads[s]==loads[s]==256 for s in pubs)
    assert stress_values==[seq^n for seq in sorted(pubs) for n in range(0,256,8)]
    return dict(publications=len(pubs),full_CPU_words=dict(loads),native_frame_AR_R=dict(native_reads),DMA_W_between_other_buffer_AR_R=interleaved,
                CPU_test_stores=cpu_stores,same_AW_W=same,separate_AW_W=separate,full_wait_cycles=cases['end']-cases['begin'])
def main():
    p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--job',choices=['unit','soc'],required=True);a=p.parse_args()
    expected='ABI2_OWNERSHIP_FAULTS_PERMISSIONS' if a.job=='unit' else 'ABI2_SMALL_REAL_CPU'
    stdout=(a.out/(a.job+'.stdout.log')).read_text(errors='replace')
    assert 'RESULT: PASS '+expected in stdout and not any(s in stdout for s in ('RESULT: FAIL','** Error','** Fatal'))
    trace_count=data_input(a.out/(a.job+'.dvp.log'),a.job)
    result=(check_unit if a.job=='unit' else check_soc)(a.out);result.update(status='ABI2_INDEPENDENT_RAW_CHECK_PASS',DVP_input_frames=trace_count)
    (a.out/(a.job+'.checked.json')).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
if __name__=='__main__':main()
