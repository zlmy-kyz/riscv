"""Audit preserved complete prefixes after the 7200 s kill; never rerun HDL."""
import collections,json,re,sys,zlib
from pathlib import Path
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[3];KEY=ROOT/'sim/camera/key'
sys.path.insert(0,str(KEY))
from seal import sha,closure,VENDOR
sys.dont_write_bytecode=True
from prepare import frame
OUT=KEY/'build/ds_camera_soc_bootmap_20261015_a'

def rows(path,truncated):
    with path.open(encoding='ascii') as stream:
        for index,line in enumerate(stream,1):
            if not line.endswith('\n'):
                truncated[path.name]=dict(line=index,bytes=len(line),text=line[:160]);break
            yield line.split()

def main():
    m=json.loads((OUT/'inputs.json').read_text(encoding='utf-8'))
    assert sha(OUT/'inputs.json')==sha(KEY/'inputs_soc_bootmap.json')=='44437cb7042b70b7430336105696b7aacc84863cc51c0d2629afca12af33eecb'
    for folder in (ROOT,KEY/'sealed_soc_bootmap_20261015_a/project',OUT/'inputs/project'):
        for n,d in m['project_sha256'].items():assert sha(folder/n)==d,(folder,n)
    for n,d in {**m['vendor_sha256'],**m['tool_sha256']}.items():assert sha(n)==d,n
    for n,d in json.loads((OUT/'evidence_sha256.json').read_text(encoding='utf-8')).items():assert sha(OUT/n)==d,n
    assert json.loads((OUT/'input_identity_after.json').read_text(encoding='utf-8'))==m['project_sha256']
    assert (OUT/'git_before.json').read_bytes()==(OUT/'git_after.json').read_bytes()
    assert closure(OUT/'inputs/project',m['compile_sources'])==m['include_dependencies']
    command=json.loads((OUT/'soc.command.json').read_text(encoding='utf-8'))
    assert command['timed_out'] and command['timeout_seconds']==7200 and command['returncode']==1
    stdout=(OUT/'soc.stdout.log').read_text(encoding='utf-8',errors='replace')
    assert 'BOOTMAP reset=40000000 rom=00000000 ram=00000000' in stdout
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|TRAP cycle=',stdout)
    image=[int(s,16) for s in (KEY/'generated/cpu.dat').read_text().splitlines()]
    boot=re.findall(r'BOOT_RETIRE cycle=(\d+) pc=([0-9a-f]+) inst=([0-9a-f]+)',stdout)
    assert len(boot)==16
    for cycle,pc,ins in boot:assert image[(int(pc,16)-0x40000000)//4]==int(ins,16)
    expected={1:frame(1),2:frame(2)};truncated={};seen=[];offset=0;p=None
    for r in rows(OUT/'dvp.log',truncated):
        if r[0]=='FRAME':
            if p is not None:assert offset==1843200
            p=int(r[1]);seen.append(p);offset=0
            assert r[2:4]==['1280','720']
        else:
            assert int(r[0],16).to_bytes(2,'little')==expected[p][offset:offset+2]
            offset+=2
    assert seen==[1,2] and offset==1843200
    camera={1:0,2:0};last={};pending=None;read_pending=None;ars=[0,0,0];returns=[0,0,0];cpu_writes=0
    for r in rows(OUT/'bus.log',truncated):
        kind=r[0];p,cycle,owner,address=int(r[1]),int(r[2]),int(r[3]),int(r[4],16)
        assert address%8==0
        if kind=='AW':assert pending is None;pending=(p,owner,address,cycle)
        elif kind=='W':
            assert pending and pending[:3]==(p,owner,address);pending=None
            value=int(r[5],16).to_bytes(32,'little');mask=int(r[6],16)
            if owner==2:
                off=camera[p]*32;assert address==0x400000+off//4 and mask==0xffffffff
                assert value==expected[p][off:off+32]
                camera[p]+=1;last[p]=cycle
            else:
                assert owner==1 and address==0x4000 and mask==15 and int.from_bytes(value[:4],'little')==p
                cpu_writes+=1
        elif kind=='AR':
            assert read_pending is None;read_pending=(p,owner,address)
            if 0x400000<=address<0x470800:assert owner==1;ars[p]+=1
        elif kind=='R':
            assert read_pending==(p,owner,address);read_pending=None
            if 0x400000<=address<0x470800:
                off=(address-0x400000)*4
                want=expected[p][off:off+32] if p else bytes.fromhex('efbeadde')*8
                assert int(r[5],16).to_bytes(32,'little')==want;returns[p]+=1
        else:raise AssertionError(r)
    assert camera=={1:57600,2:57600} and ars[:2]==[3,460803] and returns[:2]==[3,460803]
    loads=[0,0,0];done=[];crcs=[];arms=[]
    for r in rows(OUT/'cpu.log',truncated):
        kind=r[0]
        if kind=='LOAD':
            p,cycle,address,value=int(r[1]),int(r[2]),int(r[3],16),int(r[4],16);n=loads[p]
            off=[0,32,0][n] if p==0 else ([0,32,0][n-460800] if p==1 and n>=460800 else n*4)
            assert address==0x41000000+off
            assert value==(int.from_bytes(expected[p][off:off+4],'little') if p else 0xdeadbeef)
            loads[p]+=1
        elif kind=='ARM':arms.append(int(r[1]))
        elif kind=='DONE':
            p,cycle,wcycle,crc,size,pixels,seq=int(r[1]),int(r[2]),int(r[3]),int(r[4],16),int(r[5]),int(r[6]),int(r[7])
            assert last[p]==wcycle and cycle>wcycle and crc==zlib.crc32(expected[p])
            assert (size,pixels,seq)==(1843200,921600,p)
            done.append(dict(frame=p,cycle=cycle,last_W=wcycle,CRC=f'{crc:08x}'))
        elif kind=='MMIO':
            p,cycle,off,value=int(r[1]),int(r[2]),int(r[3],16),int(r[4],16)
            if off==0 and value>2:assert value==zlib.crc32(expected[p]);crcs.append([p,f'{value:08x}'])
        elif kind=='COVER':raise AssertionError('Unexpected complete PASS after timeout')
        else:raise AssertionError(r)
    assert arms==[1,2] and len(done)==2 and loads[:2]==[3,460803] and 0<loads[2]<460800
    assert crcs==[[1,'ad4e00c3']]
    result=dict(status='SOC_TIMEOUT_COMPLETE_PREFIXES_REVIEWED_NOT_FULL_PASS',date='2026-10-15',
        manifest_sha256=sha(OUT/'inputs.json'),inputs=317,command=command,first_16_retirements_match_image=True,
        full_DVP_frames_checked=2,camera_W=camera,DONE=done,CPU_frame_load_prefixes=loads,native_frame_AR_prefixes=ars,
        native_frame_R_prefixes=returns,CPU_reported_CRC=crcs,CPU_scratch_W=cpu_writes,
        truncated_last_lines=truncated,pending_write=pending,pending_read=read_pending,
        limitation='Hard kill left independently buffered prefixes. Frame2 CPU CRC, final coverage and completion are missing. Original run remains STOPPED_FIRST_FAILURE.',
        decision='No continuation of the expensive full-frame real-CPU simulation; reuse unit successes and audited prefixes; remaining acceptance moves to user-operated UART frame/CRC/image tests.',
        RTL_functional_failure_observed=False,HDL_rerun=False,PDS_run=False,serial_opened=False,
        evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in OUT.iterdir() if p.is_file()})
    (HERE/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({k:v for k,v in result.items() if k not in ('evidence_sha256','command')},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
