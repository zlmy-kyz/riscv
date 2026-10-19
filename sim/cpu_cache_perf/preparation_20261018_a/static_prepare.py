"""041 cache-perf observation: snapshot/static elaboration, no HDL execution."""
from pathlib import Path
import difflib
import hashlib
import json
import subprocess
import sys

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[2]
TARGETS=['myriscv/dual_sram_to_pango_ddr_bridge.v','myriscv/simple_mmio.v','myriscv/soc_top.v']
BASE='sim/cpu_ex_redirect/board/review_task039_20261018_01/board_review.json'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
def save(name,value):
    (HERE/name).write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def snapshot():
    assert not (HERE/'before_manifest.json').exists(), 'Preserve snapshot'
    prior=json.loads((ROOT/'sim/cpu_ex_redirect/target_fetch_20261018_a/after_manifest.json').read_text(encoding='utf-8'))
    paths=set(prior)|{BASE}
    before={rel:sha(ROOT/rel) for rel in sorted(paths)}
    assert before['myriscv/mycpu_sync.v']=='5c26df0229ab00365b2eca1412499f988981fdfe1d1b7292e43a8317f0d47745'
    for rel,digest in json.loads((ROOT/BASE).read_text(encoding='utf-8'))['evidence_sha256'].items():
        assert sha(ROOT/rel)==digest,rel
    for rel in TARGETS:
        dst=HERE/'before'/rel;dst.parent.mkdir(parents=True,exist_ok=True)
        dst.write_bytes((ROOT/rel).read_bytes())
    save('before_manifest.json',before)
    r=subprocess.run(['git','status','--porcelain=v1','-uno'],cwd=ROOT,capture_output=True,check=True)
    (HERE/'git_before.txt').write_bytes(r.stdout+r.stderr)
    print('SNAPSHOT_ONLY; current039 CPU and board evidence preserved')
def review():
    assert not (HERE/'review.json').exists(), 'Preserve review'
    before=json.loads((HERE/'before_manifest.json').read_text(encoding='utf-8'))
    after={rel:sha(ROOT/rel) for rel in before}
    changed=[rel for rel in before if before[rel]!=after[rel]]
    assert set(changed)==set(TARGETS),changed
    for rel in TARGETS:
        old=(HERE/'before'/rel).read_text(encoding='utf-8');new=(ROOT/rel).read_text(encoding='utf-8')
        dst=HERE/'after'/rel;dst.parent.mkdir(parents=True,exist_ok=True);dst.write_bytes((ROOT/rel).read_bytes())
        (HERE/(Path(rel).stem+'.patch')).write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),'before/'+rel,'after/'+rel)),encoding='utf-8')
        if rel.endswith('bridge.v'):
            start='    localparam [2:0] STATE_IDLE'
            end='    // 首版不根据这些返回旁带信号产生 CPU fault'
            marker='    // 041 cache performance observer'
            assert old[old.index(start):old.index(end)]==new[new.index(start):new.index(marker)],'Functional bridge body changed'
        if rel.endswith('simple_mmio.v'):
            marker='    // 041: independent cache counter bank'
            old_seq=old[old.index('    always @(posedge clk) begin',old.index('module cpu_perf_counters')):old.rindex('endmodule')]
            new_start=new.index('    always @(posedge clk) begin',new.index('module cpu_perf_counters'))
            assert new[new_start:new.index(marker)]==old_seq,'Legacy13 sequential block changed'
    save('after_manifest.json',after)
    src=sorted(p.relative_to(ROOT).as_posix() for p in (ROOT/'myriscv').glob('*.v'))
    src+=['ipcore/icache/icache.v','ipcore/dcache/dcache.v']
    configs=[('board','board_top',{}),('soc_no_ddr','soc_top',{}),('perf_default','cpu_perf_counters',{}),
        ('perf_cache_on','cpu_perf_counters',{'CACHE_PERF_ENABLE':1}),
        ('soc_perf_off','soc_top',{'ENABLE_DDR':1,'DDR_MEM_DQ_WIDTH':32,'PERF_ENABLE':0})]
    for width,ic,dc,enabled in [(16,1,1,1),(32,1,1,1),(32,0,1,1),(32,1,0,1),(32,1,1,0)]:
        configs.append((f'bridge_{width}_i{ic}_d{dc}_perf{enabled}','dual_sram_to_pango_ddr_bridge',
            {'MEM_DQ_WIDTH':width,'INST_LINE_BUFFER_ENABLE':ic,'DATA_LINE_BUFFER_ENABLE':dc,'CACHE_PERF_ENABLE':enabled,'POSTED_WRITE_ENABLE':1}))
    checks=[]
    for name,top,params in configs:
        argv=['D:/iverilog/bin/iverilog.exe','-g2005','-tnull','-i','-I','myriscv','-s',top]
        for k,v in params.items():argv+=['-P',f'{top}.{k}={v}']
        argv+=src
        r=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=60)
        output=(r.stdout+r.stderr).decode('utf-8',errors='replace');(HERE/(name+'.log')).write_text(output,encoding='utf-8')
        checks.append(dict(name=name,argv=argv,exit_code=r.returncode,output=output))
        if r.returncode:
            save('static_failure.json',checks);raise RuntimeError(name)
    subprocess.run(['git','diff','--check','--',*TARGETS],cwd=ROOT,check=True)
    save('review.json',dict(status='TASK041_CACHE_COUNTERS_STATIC_ONLY_PENDING_USER_PDS',changed=changed,
        before_sha256={k:before[k] for k in TARGETS},after_sha256={k:after[k] for k in TARGETS},
        unchanged_inputs=len(after)-len(changed),checks=checks,
        functional_scope='Bridge functional body and legacy13 sequential logic text preserved. New observer outputs and six-counter MMIO extension only; CPU unchanged.',
        dynamic_simulation='NOT_RUN',PDS='NOT_RUN',board='NOT_RUN',
        limits='Null-target elaboration with vendor internals blackboxed, not functional/timing acceptance.'))
    print(json.dumps(dict(status='TASK041_STATIC_ONLY_PENDING_USER_PDS',checks=len(checks),hashes={k:after[k] for k in TARGETS})))
if __name__=='__main__':
    {'snapshot':snapshot,'review':review}[sys.argv[1]]()
