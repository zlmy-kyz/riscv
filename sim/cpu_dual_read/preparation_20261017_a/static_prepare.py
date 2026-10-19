"""035: snapshot and null-target elaboration only; no dynamic simulation."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys
import difflib

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
TARGET = 'myriscv/dual_sram_to_pango_ddr_bridge.v'

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def save(name, value):
    (HERE / name).write_text(json.dumps(value, indent=2, ensure_ascii=False)+'\n', encoding='utf-8')

def sources():
    files = [p for p in (ROOT/'myriscv').rglob('*') if p.is_file()]
    for d in ('ipcore/icache', 'ipcore/dcache'):
        files += [p for p in (ROOT/d).rglob('*') if p.is_file()]
    files += [ROOT/p for p in ('RISCV.pds', 'constraint_check/temp_constraint_file.fdc',
        'tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/performance_300/program.bin',
        'tests/cpu_performance_2b/build/measure_zmmul300_20261013_a/validation_300/program.bin',
        'sim/cpu_store_ack/board/review_20261017_01/board_review.json')]
    return sorted(set(files))

def git_record(name, args):
    r = subprocess.run(['git', *args], cwd=ROOT, capture_output=True, check=True)
    (HERE/name).write_bytes(r.stdout+r.stderr)

def snapshot():
    (HERE/'before').mkdir(exist_ok=False)
    manifest = {}
    for p in sources():
        rel=p.relative_to(ROOT).as_posix()
        dst=HERE/'before'/rel
        dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes(p.read_bytes())
        manifest[rel]=digest(dst)
    save('before_manifest.json',manifest)
    git_record('git_before.txt',['status','--porcelain=v1','-uall'])
    git_record('bridge_before_head.diff',['diff','--',TARGET])
    git_record('head.txt',['rev-parse','HEAD'])
    print(json.dumps({'inputs':len(manifest),'bridge_sha256':manifest[TARGET]}))

def review():
    if (HERE/'review.json').exists():
        raise RuntimeError('preserve existing review')
    before=json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    after={p.relative_to(ROOT).as_posix():digest(p) for p in sources()}
    changed=[k for k in sorted(set(before)|set(after)) if before.get(k)!=after.get(k)]
    assert changed==[TARGET],changed
    assert all(digest(HERE/'before'/k)==v for k,v in before.items())
    save('after_manifest.json',after)
    (HERE/'bridge.patch').write_text(''.join(difflib.unified_diff(
        (HERE/'before'/TARGET).read_text(encoding='utf-8').splitlines(True),
        (ROOT/TARGET).read_text(encoding='utf-8').splitlines(True), 'before/'+TARGET,'after/'+TARGET)),encoding='utf-8')
    src=[p.relative_to(ROOT).as_posix() for p in sorted((ROOT/'myriscv').glob('*.v'))]
    src+=['ipcore/icache/icache.v','ipcore/dcache/dcache.v']
    top='dual_sram_to_pango_ddr_bridge'
    configs=[('board','board_top',{}),
      ('enabled',top,{'MEM_DQ_WIDTH':32}),
      ('disabled',top,{'MEM_DQ_WIDTH':32,'INST_WITH_DATA_READ_ENABLE':0}),
      ('only035',top,{'MEM_DQ_WIDTH':32,'INST_HIT_UNDER_DATA_MISS_ENABLE':0}),
      ('both_disabled',top,{'MEM_DQ_WIDTH':32,'INST_HIT_UNDER_DATA_MISS_ENABLE':0,'INST_WITH_DATA_READ_ENABLE':0}),
      ('posted',top,{'MEM_DQ_WIDTH':32,'POSTED_WRITE_ENABLE':1}),
      ('no_dcache',top,{'MEM_DQ_WIDTH':32,'DATA_LINE_BUFFER_ENABLE':0}),
      ('no_icache',top,{'MEM_DQ_WIDTH':32,'INST_LINE_BUFFER_ENABLE':0}),
      ('x16',top,{'MEM_DQ_WIDTH':16})]
    logs=HERE/'checks_01'
    logs.mkdir(exist_ok=False)
    checks=[]
    for name,top,params in configs:
        argv=['D:/iverilog/bin/iverilog.exe','-g2005','-tnull','-i','-I','myriscv','-s',top]
        for k,v in params.items():
            argv+=['-P',f'{top}.{k}={v}']
        argv+=src
        r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
        output=(r.stdout+r.stderr).decode('utf-8',errors='replace')
        (logs/(name+'.log')).write_text(output,encoding='utf-8')
        checks.append({'name':name,'cwd':str(ROOT),'argv':argv,'exit_code':r.returncode,'output':output})
        if r.returncode:
            save('static_failure.json',checks)
            raise RuntimeError(name)
    subprocess.run(['git','diff','--check','--',TARGET],cwd=ROOT,check=True)
    git_record('git_after.txt',['status','--porcelain=v1','-uall'])
    save('review.json',{'status':'TASK035_STATIC_ONLY_PENDING_USER_PDS','changed':changed,
      'before_sha256':before[TARGET],'after_sha256':after[TARGET],
      'unchanged_inputs':len(after)-1,'checks':checks,
      'limits':'Real cache port wrappers, vendor implementations and missing IP blackboxed by -i; no HDL simulation, synthesis, timing or board PASS.'})
    print(json.dumps({'status':'STATIC_ONLY_PENDING_USER_PDS','checks':len(checks),'bridge_sha256':after[TARGET]}))

if __name__=='__main__':
    {'snapshot':snapshot,'review':review}[sys.argv[1]]()
