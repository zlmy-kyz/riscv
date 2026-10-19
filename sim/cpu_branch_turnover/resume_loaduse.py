"""Task030 formal continuation: repaired stimulus key once + two pending ISA jobs."""
import argparse,ast,json,shutil
import run as stage
ROOT=stage.ROOT;HERE=stage.HERE;MS=stage.MS
sha=stage.sha;read=stage.read;write=stage.write
TAG='ds_cpu_branch_loaduse_resume_20261014_a';MANIFEST=HERE/'loaduse_resume_inputs.json'
def require_inputs():
    old=stage.require_inputs();m=json.loads(read(MANIFEST))
    assert m['original_manifest_sha256']==sha(stage.MANIFEST)
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    a=[s.split() for s in read(ROOT/old['key_specs']).splitlines()]
    b=[s.split() for s in read(ROOT/m['key_specs']).splitlines()]
    assert len(a)==len(b)==9
    assert [(i,j,x,y) for i,(aa,bb) in enumerate(zip(a,b)) for j,(x,y) in enumerate(zip(aa,bb)) if x!=y]==[(4,1,'1','0')]
    assert [c['profile'] for c in m['plan']['cases']]==[0,1,2,1,0,0,1,1,1]
    assert m['plan']['ISA_seed']==2026101430
    control=stage.check_job(HERE/'build'/stage.TAG,old,'control')
    assert control==m['reused_control'] and control['case_cycles']['flow_fast']==194
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m
compile_argv=stage.compile_argv;job_argv=stage.job_argv;check_job=stage.check_job
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag');p.add_argument('--check-inputs',action='store_true');a=p.parse_args()
    m=require_inputs()
    if a.check_inputs:print('INPUTS_MATCH_LOADUSE_RESUME_HDL_NOT_RUN key455/LOAD>0 ISA=auipc,sb control94 reused; RTL/TB/oracle unchanged');return
    assert a.tag==TAG and stage.pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=stage.git_snapshot();write(out/'git_before.json',before)
    r=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),completed={},reused_control=m['reused_control'],
        CPU_changed_since_Task030=False,PDS_started=False,serial_opened=False,board_status='NOT_RUN')
    write(out/'result.json',r)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest);assert sha(dest)==m['sha256'][n]
        stage.command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=stage.command(compile_argv(out,m),out,out/'compile',60);assert 'Errors: 0, Warnings: 0' in log
        for name in ('key','isa_auipc','isa_sb'):
            stage.command(job_argv(out,m,name),out,out/name,180)
            r['completed'][name]=check_job(out,m,name);write(out/'result.json',r)
        assert r['completed']['key']['case_cycles']['flow_fast']<m['reused_control']['case_cycles']['flow_fast']
        assert require_inputs()==m
        after=stage.git_snapshot();write(out/'git_after.json',after);assert after==before
        r.update(status='BRANCH_TURNOVER_LOADUSE_KEY_AND_TWO_ISA_PASS',inputs_unchanged=True,git_unchanged=True,
            old_evidence_preserved=True,scope=m['scope'])
        print('RESULT: PASS repaired load-use stimulus key + ISA auipc,sb; control94 reused; board NOT_RUN')
    except Exception as exc:r.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',r)
if __name__=='__main__':main()
