"""Independent completed Task026 continuation audit; accepts ModelSim absolute library paths."""
import json
import re
from resume_response_turnover import ROOT,HERE,TAG,MANIFEST,require_inputs,compile_argv,simulation_argv,check_evidence
from run_response_turnover import MS,sha,read,write


def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    result=json.loads(read(out/'result.json'))
    assert result['status']=='RESPONSE_TURNOVER_KEY_TEST_PASS' and result['functional_status']=='PASS'
    assert result['manifest_sha256']==sha(MANIFEST) and result['inputs_unchanged'] and result['git_unchanged']
    counts=check_evidence(out,m)
    for k,v in counts.items():assert result[k]==v
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n],n
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    commands={}
    for step,expected,limit in [('vlib',[MS/'vlib.exe',out/'work'],60),('compile',compile_argv(out,m),60),
                                ('simulation',simulation_argv(out,m),180)]:
        meta=json.loads(read(out/(step+'.command.json')))
        assert meta['argv']==list(map(str,expected)) and meta['cwd']==str(out)
        assert meta['exit_code']==meta['native_exit_after_wait']==0 and not meta['timed_out']
        assert meta['timeout_seconds']==limit and 0<meta['seconds']<limit
        assert meta['stdout_direct_to_file'] and meta['cleanup'] is None
        commands[step]=meta
    compile_log=read(out/'compile.log');assert 'Errors: 0, Warnings: 0' in compile_log
    assert not re.search(r'\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',compile_log)
    compiled=re.findall(r'-- Compiling module (\w+)',compile_log)
    assert len(compiled)==20 and len(set(compiled))==20
    console=read(out/'simulation.log')
    # The same library is printed as either work.module or <absolute path>/work.module.
    library=re.escape((out/'work').as_posix())
    loaded=re.findall(r'^# Loading (?:work|'+library+r')\.(\w+)',console.replace('\\','/'),re.M)
    assert len(loaded)==20 and set(loaded)==set(compiled)
    assert re.search(r'Time: 46860 ns\s+Iteration: 1',console)
    assert counts['turnovers']==counts['I_TURN']+counts['D_TURN']
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in [out/'result.json',out/'simulation.log',
        out/'transcript',out/'compile.log',out/'vlib.command.json',out/'compile.command.json',
        out/'simulation.command.json',out/'git_before.json',out/'git_after.json',out/'inputs.json',MANIFEST]}
    write(target,dict(status='RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS',**counts,groups=m['groups'],commands=commands,
        compiled_modules=compiled,loaded_modules=loaded,finish_ns=46860,
        source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],evidence_sha256=evidence,
        original_failure_files_verified=len(m['original_failure_files_sha256']),
        frozen_copies_verified=len(m['snapshot_files']),inputs_unchanged=True,git_unchanged=True,
        CPU_changed=False,PDS_started=False,serial_opened=False,scope=m['scope']))
    print('RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS tests=1832 CPU=392 compiled/loaded=20 copies=21 old_files=30')


if __name__=='__main__':main()
