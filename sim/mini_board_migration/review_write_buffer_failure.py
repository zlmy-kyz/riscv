"""Read Task027 failure evidence without changing the failed execution directory."""
import json,re
from run_write_buffer import ROOT,HERE,TAG,MANIFEST,MS,require_inputs,sha,read,write,compile_argv,job_argv,check_job
PREP=HERE/'build/write_buffer_soc_resume_preparation_20261013_a'
def main():
    m=require_inputs();out=HERE/'build'/TAG
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    result=json.loads(read(out/'result.json'))
    assert result['status']=='STOPPED_FIRST_FAILURE' and result['completed']=={'control':{'tests':8}}
    assert result['manifest_sha256']==sha(MANIFEST)
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    expected={'vlib':([MS/'vlib.exe',out/'work'],60),'compile':(compile_argv(out,m),60),
              'control':(job_argv(out,m,'control'),180),'key':(job_argv(out,m,'key'),180)}
    commands={}
    for name,(argv,limit) in expected.items():
        d=json.loads(read(out/(name+'.command.json')))
        assert d['argv']==list(map(str,argv)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out']
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit and d['cleanup'] is None
        commands[name]=d
    compiled=re.findall(r'-- Compiling module (\w+)',read(out/'compile.log'))
    assert len(compiled)==37 and set(compiled)==set(m['expected_modules'])
    assert 'Errors: 0, Warnings: 0' in read(out/'compile.log')
    assert check_job(out,m,'control')=={'tests':8}
    log=read(out/'key.log');assert log.strip()==read(out/'key.transcript').strip()
    assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',log)==[(g['name'],str(g['checks'])) for g in m['groups'][:-1]]
    assert log.count('RESULT: FAIL unexpected synchronous CPU trap')==1
    assert 'Time: 51575 ns' in log and 'Errors: 1, Warnings: 0' in log and '$finish' in log
    assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130']*4
    assert 'RESULT: PASS write_buffer_x32' not in log and 'RPC_Init' not in log
    assert not (out/'git_after.json').exists()
    for j in ('isa_or','isa_lhu'):
        for suffix in ('.command.json','.log','.transcript','.events.log'):assert not (out/(j+suffix)).exists()
    raw={p.relative_to(ROOT).as_posix():sha(p) for p in out.rglob('*') if p.is_file()}
    PREP.mkdir(parents=True,exist_ok=True);target=PREP/'failure_review.json';assert not target.exists()
    write(target,dict(status='WRITE_BUFFER_FAILURE_RAW_EVIDENCE_REVIEW_CONFIRMED',
        control_checks=8,key_completed_checks=426,key_unfinished_group='real_soc_fence_irq_stop',
        first_failure_time_ns=51575,original_trap_PC_cause_tval='NOT_LOGGED',
        diagnosis='Static program defect: TEST_STATUS PASS without prior RUN; exact observed cause still needs reproduction',
        commands=commands,source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],
        old_artifact_sha256=raw,old_git_after='ABSENT_PRESERVED',ISA='NOT_RUN',
        HDL_started_by_Codex=False,PDS_started=False,serial_opened=False))
    print('FAILURE CONFIRMED; control 8/key first 426; frozen old artifacts',len(raw),'cause NOT_LOGGED')
if __name__=='__main__':main()
