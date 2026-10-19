"""Independent Task028 raw command/log/snapshot/source audit; no HDL or serial."""
import json,re
from run_data_read_overlap import ROOT,HERE,TAG,MANIFEST,MS,require_inputs,compile_argv,job_argv,check_job,sha,read,write
def main():
    m=require_inputs();out=HERE/'build'/TAG;target=out/'codex_review.json';assert not target.exists()
    r=json.loads(read(out/'result.json'));assert r['status']=='DATA_READ_OVERLAP_KEY_PASS'
    assert r['manifest_sha256']==sha(MANIFEST) and r['inputs_unchanged'] and r['git_unchanged'] and not r['CPU_changed']
    assert (out/'inputs.json').read_bytes()==MANIFEST.read_bytes()
    for n in m['snapshot_files']:assert sha(out/'inputs'/n)==m['sha256'][n]
    assert json.loads(read(out/'git_before.json'))==json.loads(read(out/'git_after.json'))
    expected={'vlib':([MS/'vlib.exe',out/'work'],60),'compile':(compile_argv(out,m),60)}
    expected.update({n:(job_argv(out,m,n),180) for n in ('control','key')});commands={}
    for n,(argv,limit) in expected.items():
        d=json.loads(read(out/(n+'.command.json')))
        assert d['argv']==list(map(str,argv)) and d['cwd']==str(out)
        assert d['exit_code']==d['native_exit_after_wait']==0 and not d['timed_out'] and d['cleanup'] is None
        assert d['timeout_seconds']==limit and 0<d['seconds']<limit;commands[n]=d
    compiled=re.findall(r'-- Compiling module (\w+)',read(out/'compile.log'))
    assert len(compiled)==36 and set(compiled)==set(m['expected_modules'])
    assert 'Errors: 0, Warnings: 0' in read(out/'compile.log')
    for n in ('control','key'):assert check_job(out,m,n)==r['completed'][n]
    loaded=re.findall(r'^# Loading (?:work|'+re.escape((out/'work').as_posix())+r')\.(\w+)',read(out/'key.log').replace('\\','/'),re.M)
    assert {'tb_data_read_overlap_x32','soc_top','mycpu_sync','data_bus_interconnect','dual_sram_to_pango_ddr_bridge',
        'icache','dcache','inst_rom','data_ram','uart_mmio','simple_mmio','cpu_perf_counters'}<=set(loaded)
    evidence={p.relative_to(ROOT).as_posix():sha(p) for p in out.glob('*') if p.is_file()}
    write(target,dict(status='DATA_READ_OVERLAP_RAW_EVIDENCE_REVIEW_PASS',results=r['completed'],commands=commands,
        source_sha256=m['source_sha256'],software_sha256=m['software_sha256'],evidence_sha256=evidence,
        CPU_changed=False,ISA_samples=[],PDS_started=False,serial_opened=False,scope=m['scope']))
    print('DATA_READ_OVERLAP_RAW_EVIDENCE_REVIEW_PASS; give user PowerShell board command directly')
if __name__=='__main__':main()
