"""Independent Task030 command/log/trace/source audit; no HDL or serial."""
import json,re
from run import ROOT,HERE,TAG,MANIFEST,MS,read,write,sha,require_inputs,compile_argv,job_argv,check_job
def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    r=json.loads(read(out/'result.json'));assert r['status']=='BRANCH_TURNOVER_KEY_AND_TWO_ISA_PASS'
    assert r['manifest_sha256']==sha(MANIFEST) and r['inputs_unchanged'] and r['git_unchanged'] and r['CPU_changed']
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    expected={'vlib':([MS/'vlib.exe',out/'work'],60),'compile':(compile_argv(out,m),60)}
    expected.update({n:(job_argv(out,m,n),180) for n in ('control','key','isa_auipc','isa_sb')})
    commands={}
    for n,(argv,limit) in expected.items():
        d=json.loads(read(out/(n+'.command.json')))
        assert d['argv']==list(map(str,argv)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out'] and d['cleanup'] is None
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit;commands[n]=d
    compiled=re.findall(r'-- Compiling module (\w+)',read(out/'compile.log'))
    assert len(compiled)==len(m['expected_modules']) and set(compiled)==set(m['expected_modules'])
    for n in ('control','key','isa_auipc','isa_sb'):assert check_job(out,m,n)==r['completed'][n]
    assert r['completed']['key']['case_cycles']['flow_fast']<r['completed']['control']['case_cycles']['flow_fast']
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in out.iterdir() if p.is_file()}
    write(target,dict(status='BRANCH_TURNOVER_RAW_EVIDENCE_REVIEW_PASS',results=r['completed'],commands=commands,
        source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],evidence_sha256=evidence,
        CPU_changed=True,ISA_seed=m['ISA_seed'],ISA_samples=['auipc','sb'],PDS_started=False,serial_opened=False,scope=m['scope']))
    print('BRANCH_TURNOVER_RAW_EVIDENCE_REVIEW_PASS; user PowerShell board command ready')
if __name__=='__main__':main()
