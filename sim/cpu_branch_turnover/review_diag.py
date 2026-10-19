"""Codex raw diagnostic receipt; does not open board/function gates."""
import json
from run_diag import ROOT,HERE,TAG,MANIFEST,MS,sha,read,write,require_inputs,compile_argv,job_argv,check_diag
def main():
    m,old=require_inputs();out=HERE/'build'/TAG;target=out/'codex_diag_review.json';assert not target.exists()
    r=json.loads(read(out/'result.json'));assert r['status']=='COVERAGE_DIAGNOSTIC_COMPLETE_NOT_FUNCTIONAL_PASS'
    assert r['manifest_sha256']==sha(MANIFEST) and r['inputs_unchanged'] and r['git_unchanged']
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    for name,argv,limit in [('vlib',[MS/'vlib.exe',out/'work'],60),('compile',compile_argv(out,m),60),('key',job_argv(out,m),180)]:
        c=json.loads(read(out/(name+'.command.json')))
        assert c['argv']==list(map(str,argv)) and c['cwd']==str(out) and c['timeout_seconds']==limit
        assert c['exit_code']==c['native_exit_after_wait']==0 and not c['timed_out'] and c['cleanup'] is None
    d=check_diag(out,m,old);assert d==r['diagnostic']
    write(target,dict(status='COVERAGE_DIAGNOSTIC_RAW_REVIEW_COMPLETE_FUNCTIONAL_GATE_INCOMPLETE',diagnostic=d,
        old_evidence_preserved=True,ISA_status='NOT_RUN',PDS_started=False,serial_opened=False,
        evidence_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in out.iterdir() if p.is_file()}))
    print('DIAGNOSTIC REVIEWED unmet='+','.join(d['unmet_conditions'])+'; no board gate')
if __name__=='__main__':main()
