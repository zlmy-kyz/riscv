"""Independent Task027 raw review; no simulator/PDS/serial launch."""
import json,re
from run_write_buffer import ROOT,HERE,TAG,MANIFEST,MS,require_inputs,compile_argv,job_argv,check_job,sha,read,write


def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    result=json.loads(read(out/'result.json'));assert result['status']=='WRITE_BUFFER_KEY_AND_TWO_ISA_PASS'
    assert result['manifest_sha256']==sha(MANIFEST) and result['inputs_unchanged'] and result['git_unchanged']
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    jobs=['control','key',*['isa_'+j['name'] for j in m['isa_jobs']]]
    commands={};expected={'vlib':([MS/'vlib.exe',out/'work'],60),'compile':(compile_argv(out,m),60)}
    expected.update({name:(job_argv(out,m,name),180) for name in jobs})
    for name,(argv,limit) in expected.items():
        d=json.loads(read(out/(name+'.command.json')))
        assert d['argv']==list(map(str,argv)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out']
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit and d['cleanup'] is None
        commands[name]=d
    compile_log=read(out/'compile.log');assert 'Errors: 0, Warnings: 0' in compile_log
    modules=re.findall(r'-- Compiling module (\w+)',compile_log)
    assert set(modules)==set(m['expected_modules']) and len(modules)==len(set(modules))
    for name in jobs:assert check_job(out,m,name)==result['completed'][name]
    key=read(out/'key.log').replace('\\','/')
    loaded=re.findall(r'^# Loading (?:work|'+re.escape((out/'work').as_posix())+r')\.(\w+)',key,re.M)
    assert {'soc_top','mycpu_sync','data_bus_interconnect','dual_sram_to_pango_ddr_bridge','inst_rom','data_ram',
            'icache','dcache','simple_mmio','uart_mmio','tb_write_buffer_x32'}<=set(loaded)
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in out.glob('*') if p.is_file()}
    write(target,dict(status='WRITE_BUFFER_RAW_EVIDENCE_REVIEW_PASS',results=result['completed'],commands=commands,
        source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],evidence_sha256=evidence,
        CPU_changed=True,PDS_started=False,serial_opened=False,scope=m['scope']))
    print('WRITE_BUFFER_RAW_EVIDENCE_REVIEW_PASS; provide user board command directly')


if __name__=='__main__':main()
