"""Codex independent raw evidence audit after Task026; no HDL/PDS/serial."""
import json
import re
from run_response_turnover import ROOT,HERE,MS,TAG,MANIFEST,require_inputs,check_evidence,compile_argv,simulation_argv,sha,read,write


def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    result=json.loads(read(out/'result.json'))
    assert result['status']=='RESPONSE_TURNOVER_KEY_TEST_PASS' and result['manifest_sha256']==sha(MANIFEST)
    counts=check_evidence(out,m)
    for k,v in counts.items():assert result[k]==v
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    commands={}
    for step,expected,limit in [('vlib',[MS/'vlib.exe',out/'work'],60),('compile',compile_argv(out,m),60),
                                ('simulation',simulation_argv(out,m),180)]:
        meta=json.loads(read(out/(step+'.command.json')))
        assert meta['argv']==list(map(str,expected))
        assert meta['exit_code']==meta['native_exit_after_wait']==0 and not meta['timed_out']
        assert meta['timeout_seconds']==limit and 0<meta['seconds']<limit
        assert meta['stdout_direct_to_file'] and meta['cleanup'] is None
        commands[step]=meta
    compile_log=read(out/'compile.log');assert 'Errors: 0, Warnings: 0' in compile_log
    compiled=re.findall(r'-- Compiling module (\w+)',compile_log)
    assert len(compiled)==20 and len(set(compiled))==20
    modules=re.findall(r'^# Loading work\.(\w+)',read(out/'simulation.log'),re.M)
    assert {'GTP_GRS','GTP_DRM36K_E1','GTP_APM_E2','mycpu_sync','dual_sram_to_pango_ddr_bridge',
            'alu','br_alu','l_alu','regfile','csr_file','icache','dcache','mul','tb_response_turnover_x32'}<=set(modules)
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in (out/'result.json',out/'simulation.log',
              out/'transcript',out/'compile.log',out/'simulation.command.json')}
    write(target,dict(status='RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS',**counts,groups=m['groups'],commands=commands,
        source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],evidence_sha256=evidence,
        CPU_changed=False,PDS_started=False,serial_opened=False,scope=m['scope']))
    print('RESPONSE_TURNOVER_RAW_EVIDENCE_REVIEW_PASS; provide user COM9 command directly')


if __name__=='__main__':
    main()
