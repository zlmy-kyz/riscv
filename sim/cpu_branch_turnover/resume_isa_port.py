"""Task030 closure: explicit idle memory-order input, two ISA jobs only."""
from pathlib import Path
import argparse,ast,json,re,shutil
import run as stage
ROOT=stage.ROOT;HERE=stage.HERE;MS=stage.MS
sha=stage.sha;read=stage.read;write=stage.write
TAG='ds_cpu_branch_isa_port_resume_20261014_a';MANIFEST=HERE/'isa_port_resume_inputs.json'
TB='sim/cpu_zmmul/tb_cpu_rv32i_sample.sv'
ANCHOR="        .clk(clk),.resetn(resetn),.irq_external(irq),.irq_software(1'b0),.irq_timer(1'b0),\n"
def architectural_events(path):
    result=[]
    for row in read(path).splitlines():
        w=row.split();assert len(w)==11 and w[0]=='EV'
        k=int(w[1]);we=int(w[4],2);assert k in (0,1,3) and we in (0,1)
        result.append([k,int(w[2],16),int(w[3],16),we,int(w[5]) if we else 0,int(w[6],16) if we else 0,
            int(w[7]) if k==1 else 0,int(w[8],16) if k==1 else 0,int(w[9],16) if k==1 else 0])
    assert result and sum(e[0]==1 for e in result)==5
    return result
def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    old=json.loads(read(ROOT/m['previous_manifest']))
    assert sha(ROOT/m['previous_manifest'])==m['previous_manifest_sha256']
    assert {n for n,h in old['sha256'].items() if sha(ROOT/n)!=h}=={TB}
    before=read(ROOT/m['old_TB_copy']);assert before.count(ANCHOR)==1
    assert read(ROOT/TB)==before.replace(ANCHOR,ANCHOR+"        .memory_order_busy(1'b0),\n",1)
    assert sha(ROOT/m['old_TB_copy'])==old['sha256'][TB]
    key=stage.check_job(ROOT/m['reused_key_directory'],old,'key')
    assert key==m['reused_key'] and key['LOAD']==3 and key['case_cycles']['flow_fast']==148
    assert m['reused_control']['case_cycles']['flow_fast']==194
    assert m['plan']['ISA_seed']==2026101430 and [s['name'] for s in m['plan']['ISA_samples']]==['auipc','sb']
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m
compile_argv=stage.compile_argv;job_argv=stage.job_argv;check_job=stage.check_job
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag');p.add_argument('--check-inputs',action='store_true');a=p.parse_args()
    m=require_inputs()
    if a.check_inputs:print('ISA_PORT_INPUTS_MATCH_HDL_NOT_RUN; only memory_order_busy tie0; key455/control94 reused; ISA auipc,sb');return
    assert a.tag==TAG and stage.pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=stage.git_snapshot();write(out/'git_before.json',before)
    r=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),completed={},reused_key=m['reused_key'],reused_control=m['reused_control'],
        RTL_changed=False,PDS_started=False,serial_opened=False,board_status='NOT_RUN')
    write(out/'result.json',r)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest);assert sha(dest)==m['sha256'][n]
        stage.command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=stage.command(compile_argv(out,m),out,out/'compile',60)
        modules=re.findall(r'-- Compiling module (\w+)',log)
        assert len(modules)==14 and set(modules)==set(m['expected_modules']) and 'Errors: 0, Warnings: 0' in log
        for name in ('isa_auipc','isa_sb'):
            stage.command(job_argv(out,m,name),out,out/name,180)
            r['completed'][name]=check_job(out,m,name);architectural_events(out/(name+'.events.log'))
            if name=='isa_auipc':
                assert architectural_events(out/'isa_auipc.events.log')==architectural_events(ROOT/m['warning_auipc_trace'])
            write(out/'result.json',r)
        assert require_inputs()==m
        after=stage.git_snapshot();write(out/'git_after.json',after);assert after==before
        r.update(status='BRANCH_TURNOVER_REUSED_KEY_PLUS_TWO_ISA_PASS',inputs_unchanged=True,git_unchanged=True,
            old_evidence_preserved=True,scope=m['scope'])
        print('RESULT: PASS CPU branch key455/control94 reused + zero-warning ISA auipc,sb; board NOT_RUN')
    except Exception as exc:r.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',r)
if __name__=='__main__':main()
