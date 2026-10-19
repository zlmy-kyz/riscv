"""Audit formal key PASS and ISA port-warning stop before touching the old TB."""
import json,re
import resume_loaduse as resume
import run as stage
ROOT=resume.ROOT;HERE=resume.HERE;PREP=HERE/'build/isa_port_preparation_20261014_a'
def main():
    m=resume.require_inputs();out=HERE/'build'/resume.TAG
    PREP.mkdir(parents=True,exist_ok=False)
    r=json.loads(resume.read(out/'result.json'));assert r['status']=='STOPPED_FIRST_FAILURE' and set(r['completed'])=={'key'}
    assert r['manifest_sha256']==resume.sha(resume.MANIFEST)
    assert (out/'inputs.json').read_bytes()==resume.MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert resume.sha(out/'inputs'/n)==m['sha256'][n]
    assert not (out/'git_after.json').exists() and not (out/'isa_sb.command.json').exists()
    commands={}
    expected={'vlib':([stage.MS/'vlib.exe',out/'work'],60),'compile':(resume.compile_argv(out,m),60)}
    expected.update({n:(resume.job_argv(out,m,n),180) for n in ('key','isa_auipc')})
    for n,(argv,limit) in expected.items():
        d=json.loads(resume.read(out/(n+'.command.json')))
        assert d['argv']==list(map(str,argv)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out'] and d['cleanup'] is None
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit;commands[n]=d
    log=resume.read(out/'compile.log');modules=re.findall(r'-- Compiling module (\w+)',log)
    assert len(modules)==16 and set(modules)==set(m['expected_modules']) and 'Errors: 0, Warnings: 0' in log
    key=stage.check_job(out,m,'key');assert key==r['completed']['key'] and key['LOAD']==3
    assert key['case_cycles']['flow_fast']==148<m['reused_control']['case_cycles']['flow_fast']==194
    isa=resume.read(out/'isa_auipc.log');assert isa.strip()==resume.read(out/'isa_auipc.transcript').strip()
    assert re.findall(r'\*\* Warning: \(vsim-(\d+)\)',isa)==['3017','3722']
    assert 'Errors: 0, Warnings: 2' in isa and '$finish' in isa and 'RESULT: FAIL' not in isa and 'RPC_Init' not in isa
    # Verify architecture without crediting this warning-bearing job as a formal PASS.
    rows=re.findall(r'ISA_TRAP: isa_auipc index=(\d+) pc=(\w+) inst=(\w+) cause=(\d+) tval=(\w+) target=(\w+) rf_we=(\d+)',isa)
    sample=m['plan']['ISA_samples'][0]
    expected=[tuple(int(v,16) for v in row.split()) for row in resume.read(ROOT/sample['traps']).splitlines()]
    assert len(rows)==5
    for i,(idx,pc,ins,cause,tval,target,we) in enumerate(rows):
        assert int(idx)==i and int(we)==0 and (int(pc,16),int(ins,16),int(cause),int(tval,16),int(target,16))==expected[i]
    assert 'RESULT: PASS rv32i_sample case=isa_auipc tohost=1 traps=5 probes=4 muls=0' in isa
    events=resume.read(out/'isa_auipc.events.log').splitlines();assert len(events)==100
    oldtb=ROOT/'sim/cpu_zmmul/tb_cpu_rv32i_sample.sv'
    (PREP/'tb_cpu_rv32i_sample_before.sv').write_bytes(oldtb.read_bytes())
    assert resume.sha(oldtb)==m['sha256'][oldtb.relative_to(ROOT).as_posix()]
    evidence={p.relative_to(ROOT).as_posix():resume.sha(p) for p in out.rglob('*') if p.is_file()}
    evidence.update(m['historical_evidence_sha256'])
    resume.write(PREP/'key_review.json',dict(status='BRANCH_TURNOVER_FORMAL_KEY_RAW_PASS_ISA_PORT_WARNING_STOP',
        key=key,reused_control=m['reused_control'],commands=commands,source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],
        original_resume_manifest_sha256=resume.sha(resume.MANIFEST),old_TB_sha256=resume.sha(oldtb),evidence_sha256=evidence,
        auipc_architectural_events=100,auipc_warning_codes=['vsim-3017','vsim-3722'],auipc_formal_status='NOT_ACCEPTED_WARNINGS2',
        sb_status='NOT_RUN',git_after_status='MISSING_PRESERVED',functional_gate='INCOMPLETE',HDL_started=False,PDS_started=False,serial_opened=False))
    print('FORMAL_KEY_RAW_PASS455 LOAD3/control94; ISA blocked only by two missing-port warnings; evidence preserved')
if __name__=='__main__':main()
