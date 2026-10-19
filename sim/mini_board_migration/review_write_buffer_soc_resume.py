"""Independently combine original 426/control8 evidence with repaired SoC and pending ISA."""
import json,re
from run_write_buffer_soc_resume import ROOT,HERE,TAG,MANIFEST,MS,require_inputs,compile_argv,job_argv,check_job,sha,read,write
def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    result=json.loads(read(out/'result.json'));assert result['status']=='WRITE_BUFFER_SOC_REPAIR_AND_TWO_ISA_PASS'
    assert result['manifest_sha256']==sha(MANIFEST) and result['inputs_unchanged'] and result['git_unchanged']
    assert result['reused_control']==8 and result['reused_key_checks']==426 and result['aggregate_current_key_checks']==840
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    jobs=['old_program','soc','isa_or','isa_lhu']
    commands={};expected={'vlib':([MS/'vlib.exe',out/'work'],60),'compile':(compile_argv(out,m),60)}
    expected.update({n:(job_argv(out,m,n),180) for n in jobs})
    for n,(argv,limit) in expected.items():
        d=json.loads(read(out/(n+'.command.json')))
        assert d['argv']==list(map(str,argv)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out']
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit and d['cleanup'] is None
        commands[n]=d
    log=read(out/'compile.log');assert 'Errors: 0, Warnings: 0' in log
    modules=re.findall(r'-- Compiling module (\w+)',log)
    assert len(modules)==37 and set(modules)==set(m['expected_modules'])
    for n in jobs:assert check_job(out,m,n)==result['completed'][n]
    loaded=re.findall(r'^# Loading (?:work|'+re.escape((out/'work').as_posix())+r')\.(\w+)',read(out/'soc.log').replace('\\','/'),re.M)
    assert {'soc_top','mycpu_sync','data_bus_interconnect','dual_sram_to_pango_ddr_bridge','inst_rom','data_ram',
        'icache','dcache','simple_mmio','cpu_perf_counters','uart_mmio','tb_write_buffer_soc_resume'}<=set(loaded)
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in out.glob('*') if p.is_file()}
    original=json.loads(read(ROOT/m['failure_review']))
    assert original['status']=='WRITE_BUFFER_FAILURE_RAW_EVIDENCE_REVIEW_CONFIRMED'
    evidence.update(original['old_artifact_sha256']);evidence[m['failure_review']]=sha(ROOT/m['failure_review'])
    write(target,dict(status='WRITE_BUFFER_RAW_EVIDENCE_REVIEW_PASS',results=result['completed'],commands=commands,
        source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],evidence_sha256=evidence,
        reused_control_checks=8,reused_front_key_checks=426,current_soc_checks=414,aggregate_key_checks=840,
        old_result_remains='STOPPED_FIRST_FAILURE',diagnosis='Original TEST_STATUS PASS in IDLE reproduced as exact store access fault; corrected RUN->PASS passes',
        CPU_changed_since_original_027=False,PDS_started=False,serial_opened=False,scope=m['scope']))
    print('WRITE_BUFFER_RAW_EVIDENCE_REVIEW_PASS; old failure preserved; provide user PowerShell board command directly')
if __name__=='__main__':main()
