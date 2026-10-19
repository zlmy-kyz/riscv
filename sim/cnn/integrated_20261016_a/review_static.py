"""Syntax elaboration, source identity and address bounds; no HDL execution."""
import hashlib
import json
import subprocess
from pathlib import Path

root = Path(__file__).resolve().parents[3]
out = Path(__file__).resolve().parent
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
baseline=json.loads((out/'baseline/manifest.json').read_text(encoding='utf-8'))
changed=[]
for name,digest in baseline.items():
    assert sha(out/'baseline'/name)==digest, name
    if sha(root/name)!=digest: changed.append(name.replace('\\','/'))
expected={'myriscv/board_top.v','myriscv/soc_top.v','myriscv/soc_ddr3_top.v',
          'myriscv/data_bus_interconnect.v','myriscv/preprocess_mmio.v',
          'myriscv/preprocess_ddr_read_arbiter.v','RISCV.pds'}
assert set(changed)==expected,changed
sources=[str(p.relative_to(root)) for p in (root/'myriscv').glob('*.v')]
cnn=[f'myriscv/{name}.v' for name in ['cnn_mmio','cnn_digits_engine',
     'cnn_rgb96_gray32','cnn_int8_mac','cnn_requantize','cnn_gap16']]
pds=(root/'RISCV.pds').read_text(encoding='utf-8')
for f in cnn: assert pds.count(f)==1,(f,pds.count(f))
# Verify native address units, tensor/weight offsets and bounded physical indices.
assert (0x42000000-0x40000000)//4==0x800000
assert 864*32==27648 and 32*32==1024
assert 6152+66+4==6222
counts=[]
for layer,(width,ci,co,base) in enumerate([(32,1,8,0),(16,8,16,72),(8,16,32,1224)]):
    count=0
    for y in range(width//2):
        for x in range(width//2):
            for oc in range(co):
                for ky in range(3):
                    for kx in range(3):
                        for ic in range(ci):
                            sx,sy=2*x+kx-1,2*y+ky-1
                            wa=base+oc*(9*ci)+(ky*3+kx)*ci+ic
                            assert 0<=wa<6152
                            # RTL masks negative padding coordinates before RAM lookup.
                            mask=width-1
                            aa=((sy&mask)*width+(sx&mask))*ci+ic
                            assert 0<=aa<2048
                            if 0<=sx<width and 0<=sy<width:
                                assert aa==(sy*width+sx)*ci+ic
                            count+=1
    assert (width//2)**2*co<=2048
    counts.append(count)
assert counts==[18432,73728,73728]
assert sum(counts)+320==166208
checks={
    'cnn_full':(['-s','cnn_mmio'],cnn),
    'board_enabled':(['-i','-s','board_top'],sources),
    'cnn_disabled':(['-i','-s','soc_ddr3_top','-P','soc_ddr3_top.ENABLE_CAMERA=1',
        '-P','soc_ddr3_top.ENABLE_PREPROCESS=1','-P','soc_ddr3_top.ENABLE_CNN=0'],sources),
    'camera_disabled':(['-i','-s','soc_ddr3_top'],sources),
}
results={}
for name,(options,files) in checks.items():
    cmd=['D:/iverilog/bin/iverilog.exe','-g2005','-Wall','-tnull','-I','myriscv']+options+files
    r=subprocess.run(cmd,cwd=root,capture_output=True,text=True,timeout=60)
    log=out/(name+'_final.log')
    log.write_text(r.stdout+r.stderr,encoding='utf-8')
    results[name]={'command':cmd,'exit_code':r.returncode,'log_sha256':sha(log)}
    assert r.returncode==0,(name,r.stdout,r.stderr)
receipt={'status':'CNN_INTEGRATED_STATIC_ONLY_PENDING_USER_PDS_AND_FUNCTIONAL_VALIDATION',
    'date':'2026-10-16','hdl_simulation_run':False,'pds_run':False,'board_run':False,
    'baseline_changed':sorted(changed),'baseline_unchanged':len(baseline)-len(changed),
    'syntax':results,'conv_macs':counts,'total_macs':166208,
    'sources':{f:sha(root/f) for f in sorted(set(sources+['RISCV.pds','constraint_check/temp_constraint_file.fdc']))}}
(out/'static_review.json').write_text(json.dumps(receipt,indent=2),encoding='utf-8')
print(receipt['status'])
print('baseline changed:',len(changed),'unchanged:',receipt['baseline_unchanged'])
for name in results: print(name,results[name]['exit_code'])
