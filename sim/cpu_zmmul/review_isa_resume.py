"""Audit Task023 continuation raw evidence without executing HDL."""
from pathlib import Path
import argparse
import json
import re
from resume_isa import HERE, ROOT, MANIFEST, sha, require_inputs, architectural_events, read, write, check_log, BOOT

OUT=HERE/'build/ds_cpu_zmmul_isa_resume_20261013_a'


def audit():
    m=require_inputs();assert sha(OUT/'inputs.json')==sha(MANIFEST)
    source=json.loads(read(OUT/'source_identity.json'))
    assert source['continuation_sha256']==m['sha256']
    for n in m['new_snapshot_files']:assert sha(OUT/'new_inputs'/n)==m['sha256'][n]
    files=['inputs.json','source_identity.json','git_before.json','git_after.json','result.json','lhu_architectural_comparison.json']
    command_rows=[]
    for n in ['vlib_baseline','compile_baseline','baseline_lhu','vlib_current','compile_current','isa_lhu','isa_or']:
        c=json.loads(read(OUT/(n+'.command.json')))
        assert c['exit_code']==0 and not c['timed_out']
        assert c['timeout_seconds']==(180 if 'lhu' in n or n=='isa_or' else 60)
        command_rows.append(dict(name=n,seconds=c['seconds'],exit_code=c['exit_code']))
        files += [n+'.command.json',n+'.log']
    modules=['GTP_GRS','GTP_APM_E2','alu','br_alu','l_alu','regfile','csr_file','mycpu_sync','mul',
             'ipm2l_mult_v1_3_mul','ipm2l_apm_data_pipeline','ipm2l_apm_distributed_sdpram',
             'ipm2l_apm_distributed_shiftregister','tb_cpu_rv32i_sample']
    for variant in ['baseline','current']:
        log=read(OUT/('compile_'+variant+'.log'));assert 'Errors: 0, Warnings: 0' in log
        assert re.findall(r'-- Compiling module (\w+)',log)==modules
        argv=json.loads(read(OUT/('compile_'+variant+'.command.json')))['argv']
        cpu=ROOT/m['baseline_cpu'] if variant=='baseline' else ROOT/'myriscv/mycpu_sync.v'
        assert str(cpu) in argv
    rows=[]
    for j in m['jobs']:
        name=j['name'];log=read(OUT/(name+'.log'))
        expected=f'RESULT: PASS rv32i_sample case={name} tohost=1 traps=5 probes=4 muls=0'
        check_log(log,read(OUT/(name+'.transcript')),expected)
        traps=re.findall(r'ISA_TRAP: '+name+r' index=(\d+) pc=(\w+) inst=(\w+) cause=(\d+) tval=(\w+) target=(\w+) rf_we=(\w+)',log)
        endpc=0x80000684 if name=='isa_or' else 0x80000478
        assert len(traps)==5
        for index,(observed,reference) in enumerate(zip(traps,BOOT+[(endpc,0x73,11,0,0x80000004)])):
            i,pc,inst,cause,tval,target,we=observed
            assert int(i)==index and tuple(int(x,16) for x in [pc,inst])+(int(cause),)+tuple(int(x,16) for x in [tval,target])==reference
            assert we=='0'
        events=architectural_events(OUT/(name+'.events.log'))
        assert len(events)==(530 if name=='isa_or' else 320)
        rows.append(dict(name=name,events=len(events),trap_count=5,trace_sha256=sha(OUT/(name+'.events.log'))))
        files += [name+'.transcript',name+'.events.log']
    assert (OUT/'baseline_lhu.events.log').read_bytes()==(OUT/'isa_lhu.events.log').read_bytes()
    assert architectural_events(OUT/'baseline_lhu.events.log')==architectural_events(OUT/'isa_lhu.events.log')
    assert json.loads(read(OUT/'lhu_architectural_comparison.json'))['status']=='IDENTICAL_ARCHITECTURAL_EVENTS'
    assert read(OUT/'git_before.json')==read(OUT/'git_after.json')
    result=json.loads(read(OUT/'result.json'));assert result['status']=='PASS' and result['reused_original_cases']==7
    assert result['functional_status']=='KEY_MULTIPLY_SUITE_PLUS_TWO_ISA_SAMPLES_PASS'
    assert [c['name'] for c in result['new_completed']]==[j['name'] for j in m['jobs']]
    return dict(status='CPU_ZMMUL_KEY_FUNCTION_AND_TWO_ISA_RAW_EVIDENCE_REVIEW_PASS',
                cpu_sha256=m['cpu_sha256'],baseline_cpu_sha256=m['baseline_cpu_sha256'],
                input_manifest_sha256=sha(MANIFEST),original_cases_reused=7,cpu_events=2839,mul_retirements=396,
                commands=command_rows,isa_results=rows,exact_old_new_lhu_trace_identical=True,
                original_failure_diagnosis='Old ISA TB omitted intentional bootstrap CSR probes; lhu has no observed Zmmul regression',
                original_git_after_still_missing=True,new_git_before_after_identical=True,all_input_identities_match=True,
                evidence_sha256={('sim/cpu_zmmul/build/ds_cpu_zmmul_isa_resume_20261013_a/'+n):sha(OUT/n) for n in files},
                scope='CPU key function and two RV32I samples only; no whole ISA/SoC/PHY/PDS/board',HDL_reexecuted=False,
                PDS_started=False,serial_opened=False)


def main():
    p=argparse.ArgumentParser();p.add_argument('--save',action='store_true');a=p.parse_args();r=audit()
    if a.save:
        destination=OUT/'codex_review.json';assert not destination.exists();write(destination,r)
    print(r['status'],'old/new_lhu=320 identical bytes or=530 muls=396 reused')


if __name__=='__main__':main()
