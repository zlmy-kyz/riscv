"""Independent final functional gate from reused key and repaired ISA TB evidence."""
import json,re
from resume_isa_port import ROOT,HERE,TAG,MANIFEST,MS,read,write,sha,require_inputs,compile_argv,job_argv,check_job,architectural_events
def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    r=json.loads(read(out/'result.json'));assert r['status']=='BRANCH_TURNOVER_REUSED_KEY_PLUS_TWO_ISA_PASS'
    assert r['manifest_sha256']==sha(MANIFEST) and r['inputs_unchanged'] and r['git_unchanged']
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    expected={'vlib':([MS/'vlib.exe',out/'work'],60),'compile':(compile_argv(out,m),60)}
    expected.update({n:(job_argv(out,m,n),180) for n in ('isa_auipc','isa_sb')});commands={}
    for n,(argv,limit) in expected.items():
        d=json.loads(read(out/(n+'.command.json')))
        assert d['argv']==list(map(str,argv)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out'] and d['cleanup'] is None
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit;commands[n]=d
    compiled=re.findall(r'-- Compiling module (\w+)',read(out/'compile.log'))
    assert len(compiled)==14 and set(compiled)==set(m['expected_modules'])
    for n in ('isa_auipc','isa_sb'):assert check_job(out,m,n)==r['completed'][n];architectural_events(out/(n+'.events.log'))
    assert architectural_events(out/'isa_auipc.events.log')==architectural_events(ROOT/m['warning_auipc_trace'])
    write(target,dict(status='BRANCH_TURNOVER_KEY_PLUS_ISA_PORT_RESUME_RAW_EVIDENCE_REVIEW_PASS',results=r['completed'],
        reused_key=m['reused_key'],reused_control=m['reused_control'],commands=commands,source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],
        evidence_sha256={**m['historical_evidence_sha256'],**{p.relative_to(ROOT).as_posix():sha(p) for p in out.iterdir() if p.is_file()}},
        CPU_changed=True,RTL_changed_since_Task030=False,ISA_seed=2026101430,ISA_samples=['auipc','sb'],PDS_started=False,serial_opened=False,scope=m['scope']))
    print('BRANCH_TURNOVER_KEY_PLUS_ISA_PORT_RESUME_RAW_EVIDENCE_REVIEW_PASS; give user board command')
if __name__=='__main__':main()
