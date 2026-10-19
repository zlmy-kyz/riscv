"""Task030 one key suite, minimal disabled control and two random ISA samples."""
from pathlib import Path
import argparse,ast,json,re,sys,shutil,hashlib
HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
sys.path.insert(0,str(ROOT/'sim/mini_board_migration'))
from resume_inst_drm64 import command
from resume_inst_cache32 import pds_shell_count,git_snapshot
MS=Path('D:/modelsim/win64pe');VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
TAG='ds_cpu_branch_turnover_20261014_a';MANIFEST=HERE/'inputs.json'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:Path(p).read_text(encoding='utf-8',errors='replace')
write=lambda p,v:Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    assert m['ISA_seed']==2026101430 and [s['name'] for s in m['plan']['ISA_samples']]==['auipc','sb']
    assert sum(c['events'] for c in m['plan']['cases'])==455
    assert m['changed_registered_sources']==['myriscv/mycpu_sync.v']
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m
def compile_argv(out,m):
    return [MS/'vlog.exe','-sv','-work',out/'work','+incdir+'+(ROOT/'myriscv').as_posix(),
        *[Path(n) for n in m['vendor_compile_sources']],*[ROOT/n for n in m['compile_sources']]]
def job_argv(out,m,name):
    if name in ('control','key'):
        plus=['-gENABLE='+str(int(name=='key')),'+SPECS='+str(ROOT/m[name+'_specs']),
            '+CASES='+str(1 if name=='control' else 9),'+EVENT_LOG='+str(out/(name+'.events.log'))]
        top='tb_branch_turnover'
    else:
        s=next(s for s in m['plan']['ISA_samples'] if 'isa_'+s['name']==name)
        plus=['+NAME='+name,'+ROM='+str(ROOT/s['rom']),f'+STATUS={s["tohost"]:08x}',
              '+TRAPS='+str(ROOT/s['traps']),'+EVENT_LOG='+str(out/(name+'.events.log'))]
        if s['ram']:plus.append('+RAM='+str(ROOT/s['ram']))
        top='tb_cpu_rv32i_sample'
    return [MS/'vsim.exe','-batch','-lib',out/'work',top,*plus,'-logfile',out/(name+'.transcript'),'-do','run -all; quit -f']
def check_job(out,m,name):
    log=read(out/(name+'.log'));assert log.strip()==read(out/(name+'.transcript')).strip()
    assert '$finish' in log and 'Errors: 0, Warnings: 0' in log
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',log)
    trace=read(out/(name+'.events.log'));assert trace.strip()
    if name in ('control','key'):
        cases=m['plan']['cases'][:1] if name=='control' else m['plan']['cases']
        checks=re.findall(r'CHECK: (\w+) PASS events=(\d+) cycles=(\d+)',log)
        assert [(n,e) for n,e,_ in checks]==[(c['name'],str(c['events'])) for c in cases]
        fields=('enable','cases','events','FAST','EMPTY','RSP','LATE','READY','BUFFER','DROP_ERR','LOAD','TRAP','IRQ','RESET')
        rows=re.findall('RESULT: PASS branch_turnover '+' '.join(k+r'=(\d+)' for k in fields),log);assert len(rows)==1
        result=dict(zip(fields,map(int,rows[0])))
        assert result['enable']==int(name=='key') and result['cases']==len(cases) and result['events']==sum(c['events'] for c in cases)
        if name=='key':
            assert all(result[k]>0 for k in ('FAST','EMPTY','RSP','LATE','READY','BUFFER','DROP_ERR','LOAD'))
            assert result['TRAP']==3 and result['IRQ']==result['RESET']==1
        else:assert result['FAST']==0
        expected=[]
        for c in cases:
            for row in read(ROOT/c['trace']).splitlines():expected.append((c['name'],[int(w,16) for w in row.split()]))
        actual=[]
        for row in trace.splitlines():
            w=row.split();assert len(w)==10 and w[0]=='EV'
            actual.append((w[1],[int(w[2]),int(w[3],16),int(w[4],16),int(w[5]),int(w[6]),int(w[7],16),int(w[8],16),int(w[9],16)]))
        assert len(actual)==len(expected)
        for (n,a),(e,b) in zip(actual,expected):
            assert n==e and a[:4]==b[:4]
            if b[3]:assert a[4:6]==b[4:6]
            if b[0] in (1,2):assert a[6:]==b[6:]
        result['case_cycles']={n:int(c) for n,_,c in checks}
        return result
    assert re.findall(r'RESULT: PASS rv32i_sample case='+name+r' tohost=1 traps=5 probes=4 muls=0',log)==[
        'RESULT: PASS rv32i_sample case='+name+' tohost=1 traps=5 probes=4 muls=0']
    rows=re.findall(r'ISA_TRAP: '+name+r' index=(\d+) pc=(\w+) inst=(\w+) cause=(\d+) tval=(\w+) target=(\w+) rf_we=(\d+)',log)
    s=next(s for s in m['plan']['ISA_samples'] if 'isa_'+s['name']==name)
    expected=[tuple(int(v,16) for v in row.split()) for row in read(ROOT/s['traps']).splitlines()]
    assert len(rows)==5
    for i,(idx,pc,ins,cause,tval,target,we) in enumerate(rows):
        assert int(idx)==i and int(we)==0 and (int(pc,16),int(ins,16),int(cause),int(tval,16),int(target,16))==expected[i]
    assert sum(row.split()[1]=='1' for row in trace.splitlines())==5
    return dict(tohost=1,traps=5,probes=4,muls=0,events=len(trace.splitlines()))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag');p.add_argument('--check-inputs',action='store_true');a=p.parse_args()
    m=require_inputs()
    if a.check_inputs:print('INPUTS_MATCH_BRANCH_TURNOVER_HDL_NOT_RUN key=455 control='+str(m['plan']['cases'][0]['events'])+' ISA=auipc,sb seed=2026101430');return
    assert a.tag==TAG and pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=git_snapshot();write(out/'git_before.json',before)
    r=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),completed={},CPU_changed=True,PDS_started=False,serial_opened=False,board_status='NOT_RUN')
    write(out/'result.json',r)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest);assert sha(dest)==m['sha256'][n]
        command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=command(compile_argv(out,m),out,out/'compile',60)
        assert 'Errors: 0, Warnings: 0' in log
        compiled=re.findall(r'-- Compiling module (\w+)',log);assert len(compiled)==len(m['expected_modules']) and set(compiled)==set(m['expected_modules'])
        for name in ('control','key','isa_auipc','isa_sb'):
            command(job_argv(out,m,name),out,out/name,180)
            r['completed'][name]=check_job(out,m,name);write(out/'result.json',r)
        assert r['completed']['key']['case_cycles']['flow_fast']<r['completed']['control']['case_cycles']['flow_fast'], 'No controlled fetch-cycle improvement'
        assert require_inputs()==m
        after=git_snapshot();write(out/'git_after.json',after);assert before==after
        r.update(status='BRANCH_TURNOVER_KEY_AND_TWO_ISA_PASS',inputs_unchanged=True,git_unchanged=True,scope=m['scope'])
        print('RESULT: PASS branch target turnover key + disabled control + ISA auipc,sb; board NOT_RUN')
    except Exception as exc:r.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',r)
if __name__=='__main__':main()
