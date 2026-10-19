"""Read-only audit of Task023 evidence; optionally save a new Codex receipt, no HDL."""
from pathlib import Path
import argparse
import hashlib
import json
import re
from run import HERE, ROOT, MANIFEST, require_inputs, check_log, read

OUT = HERE/'build/ds_cpu_zmmul_20261013_a'
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def audit():
    m = require_inputs()
    assert sha(OUT/'inputs.json') == sha(MANIFEST)
    frozen = json.loads(read(OUT/'frozen_inputs.json'))
    assert frozen == m['sha256']
    for name,digest in frozen.items():
        assert sha(OUT/'inputs'/name) == digest, name
    receipt_files = ['inputs.json','frozen_inputs.json','git_before.json','result.json',
                     'vlib.command.json','vlib.log','compile.command.json','compile.log']
    for name in ['vlib','compile']:
        c = json.loads(read(OUT/(name+'.command.json')))
        assert c['exit_code']==0 and not c['timed_out']
    compile_log = read(OUT/'compile.log')
    assert 'Errors: 0, Warnings: 0' in compile_log
    assert re.findall(r'-- Compiling module (\w+)',compile_log) == [
        'GTP_GRS','GTP_APM_E2','alu','br_alu','l_alu','regfile','csr_file','mycpu_sync',
        'mul','ipm2l_mult_v1_3_mul','ipm2l_apm_data_pipeline',
        'ipm2l_apm_distributed_sdpram','ipm2l_apm_distributed_shiftregister','tb_mul_ip','tb_cpu_zmmul']
    completed = []
    for name,expected in [('mul_ip','RESULT: PASS mul_ip vectors=128 checks=168')] + [
        (c['name'],f'RESULT: PASS cpu_zmmul case={c["name"]} events={c["events"]} muls={c["mul_retirements"]}') for c in m['test_plan']['cases']]:
        command = json.loads(read(OUT/(name+'.command.json')))
        assert command['exit_code']==0 and not command['timed_out']
        assert '-batch' in command['argv'] and command['timeout_seconds']==180
        console = read(OUT/(name+'.log')); transcript=read(OUT/(name+'.transcript'))
        check_log(console,transcript,expected)
        check = re.findall(r'^#\s*CHECK: (.*) PASS(.*)$',console,re.M)
        assert len(check)==1
        completed.append(dict(name=name,seconds=command['seconds'],check=check[0],result=expected))
        receipt_files += [name+'.command.json',name+'.log',name+'.transcript']
    failed = read(OUT/'isa_lhu.log')
    assert failed.replace('\r\n','\n') == read(OUT/'isa_lhu.transcript').replace('\r\n','\n')
    assert failed.count('RESULT: FAIL')==1 and 'unexpected ISA trap/IRQ event=38 pc=800000e4' in failed
    assert '** Fatal: Assertion error.' in failed and 'Errors: 1, Warnings: 0' in failed
    assert 'RPC_Init' not in failed and 'RESULT: PASS' not in failed
    c=json.loads(read(OUT/'isa_lhu.command.json'))
    assert c['exit_code']==0 and not c['timed_out']
    assert not (OUT/'isa_or.log').exists() and not (OUT/'git_after.json').exists()
    result=json.loads(read(OUT/'result.json'))
    assert result['status']=='STOPPED_FIRST_FAILURE' and result['completed']==[c['name'] for c in completed]
    receipt_files += ['isa_lhu.command.json','isa_lhu.log','isa_lhu.transcript']
    evidence = {('sim/cpu_zmmul/build/ds_cpu_zmmul_20261013_a/'+n):sha(OUT/n) for n in receipt_files}
    probes = []
    for sample in m['test_plan']['isa_cases']:
        words=[int(w,16) for w in read(ROOT/sample['rom']).split()]
        assert words[0xe4//4]==0x74445073
        assert words[0xd8//4]==0x00000297 and words[0xdc//4]==0x01028293 and words[0xe0//4]==0x30529073
        probes.append(dict(sample=sample['name'],pc='800000e4',instruction='74445073',
                           expected_cause=2,expected_tval='74445073',preinstalled_mtvec='800000e8'))
    return dict(status='CPU_ZMMUL_SEVEN_CASES_RAW_EVIDENCE_PASS_ISA_GATE_OPEN',
                original_input_manifest_sha256=sha(MANIFEST),engineering_inputs=len(frozen),external_inputs=len(m['external_sha256']),
                completed=completed,cpu_events=2839,mul_retirements=396,ip_vectors=128,ip_checks=168,
                isa_lhu='TB_ASSERTION_FAIL_AT_STARTUP_PROBE',isa_or='NOT_RUN',git_after='ABSENT_NOT_RECONSTRUCTED',
                current_inputs_match=True,frozen_inputs_match=True,evidence_sha256=evidence,rom_static_probes=probes,
                diagnosis='The original ISA TB incorrectly disallows intentional bootstrap CSR probes. The observed cause/instruction were not logged; strict continuation must confirm them.',
                RTL_changed=False,HDL_reexecuted=False,PDS_started=False,serial_opened=False)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--save',action='store_true');args=p.parse_args()
    report=audit()
    if args.save:
        destination=OUT/'codex_review.json'
        assert not destination.exists(),'Preserve an existing audit receipt'
        destination.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(report['status'],'PASS_cases=7 CPU_events=2839 muls=396 ISA_gate=OPEN cause_not_logged')


if __name__=='__main__':main()
