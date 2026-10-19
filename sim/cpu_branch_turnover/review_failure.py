"""Audit Task030 first failure without editing its original evidence."""
import json,re
from collections import Counter
from run import ROOT,HERE,TAG,MANIFEST,MS,read,write,sha,require_inputs,compile_argv,job_argv,check_job
PREP=HERE/'build/coverage_diag_preparation_20261014_a'
def compare_key(out,m):
    expected=[]
    for c in m['plan']['cases']:
        for row in read(ROOT/c['trace']).splitlines():expected.append((c['name'],[int(w,16) for w in row.split()]))
    actual=[]
    for row in read(out/'key.events.log').splitlines():
        w=row.split();assert len(w)==10 and w[0]=='EV'
        a=[int(w[2]),int(w[3],16),int(w[4],16),int(w[5]),int(w[6]),int(w[7],16),int(w[8],16),int(w[9],16)]
        actual.append((w[1],a))
    assert len(actual)==len(expected)==455
    for (n,a),(name,b) in zip(actual,expected):
        assert n==name and a[:4]==b[:4]
        if b[3]:assert a[4:6]==b[4:6]
        if b[0] in (1,2):assert a[6:]==b[6:]
    return dict(events=455,per_case=dict(Counter(n for n,_ in actual)),traps=sum(a[0]==1 for _,a in actual),IRQ=sum(a[0]==2 for _,a in actual))
def main():
    m=require_inputs();out=HERE/'build'/TAG;PREP.mkdir(parents=True,exist_ok=False)
    r=json.loads(read(out/'result.json'));assert r['status']=='STOPPED_FIRST_FAILURE' and set(r['completed'])=={'control'}
    assert r['manifest_sha256']==sha(MANIFEST) and (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    assert not (out/'git_after.json').exists()
    for n in ('isa_auipc','isa_sb'):assert not (out/(n+'.command.json')).exists()
    commands={}
    argv={'vlib':([MS/'vlib.exe',out/'work'],60),'compile':(compile_argv(out,m),60)}
    argv.update({n:(job_argv(out,m,n),180) for n in ('control','key')})
    for n,(args,limit) in argv.items():
        d=json.loads(read(out/(n+'.command.json')))
        assert d['argv']==list(map(str,args)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out'] and d['cleanup'] is None
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit;commands[n]=d
    compiled=re.findall(r'-- Compiling module (\w+)',read(out/'compile.log'))
    assert len(compiled)==16 and set(compiled)==set(m['expected_modules']) and 'Errors: 0, Warnings: 0' in read(out/'compile.log')
    control=check_job(out,m,'control');assert control==r['completed']['control']
    log=read(out/'key.log');assert log.strip()==read(out/'key.transcript').strip()
    checks=re.findall(r'CHECK: (\w+) PASS events=(\d+) cycles=(\d+)',log)
    assert [(n,e) for n,e,_ in checks]==[(c['name'],str(c['events'])) for c in m['plan']['cases']]
    fails=re.findall(r'RESULT: FAIL[^\n]*',log)
    assert len(fails)==1 and fails[0].endswith('coverage totals')
    assert '$finish' in log and 'Errors: 1, Warnings: 0' in log and 'RPC_Init' not in log and 'RUNNER TIMEOUT' not in log
    assert 'RESULT: PASS branch_turnover' not in log
    trace=compare_key(out,m);cycles={n:int(c) for n,_,c in checks}
    assert cycles['flow_fast']==148 and control['case_cycles']['flow_fast']==194
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    write(PREP/'old_failure_review.json',dict(status='BRANCH_TURNOVER_FIRST_FAILURE_RAW_REVIEW_COVERAGE_UNRESOLVED',
        commands=commands,control=control,key_trace=trace,key_case_cycles=cycles,
        controlled_model_cycles_saved=46,ISA_samples_status='NOT_RUN',git_after_status='MISSING_PRESERVED',
        old_evidence_sha256=evidence,source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],
        functional_gate='INCOMPLETE',diagnosis='Coverage totals failed; counter values absent; no specific unmet condition inferred',
        HDL_started=False,PDS_started=False,serial_opened=False))
    print('OLD_FAILURE_RAW_REVIEW_COMPLETE control94/key455 exact; coverage unresolved; ISA NOT_RUN; old files',len(evidence))
if __name__=='__main__':main()
