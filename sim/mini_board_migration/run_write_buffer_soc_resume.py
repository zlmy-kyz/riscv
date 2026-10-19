"""Task027 continuation: precise old-program diagnosis, corrected SoC, two pending ISA."""
from pathlib import Path
import argparse,ast,json,re,shutil
import run_write_buffer as old
from generate_write_buffer_soc_resume_tb import build_resume_tb
ROOT=old.ROOT;HERE=old.HERE;MS=old.MS;VENDOR=old.VENDOR
sha=old.sha;read=old.read;write=old.write;command=old.command
TAG='ds_mini_write_buffer_soc_resume_20261013_a'
MANIFEST=HERE/'write_buffer_soc_resume_inputs.json'

def require_inputs():
    baseline=old.require_inputs();m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    assert m['source_sha256']==baseline['source_sha256'] and m['software_sha256']==baseline['software_sha256']
    assert m['isa_jobs']==baseline['isa_jobs'] and m['isa_seed']==2026101327
    assert m['original_manifest_sha256']==sha(old.MANIFEST)
    failure=json.loads(read(ROOT/m['failure_review']))
    failed_out=HERE/'build'/old.TAG
    assert {p.relative_to(ROOT).as_posix() for p in failed_out.rglob('*') if p.is_file()}==set(failure['old_artifact_sha256'])
    assert not (failed_out/'git_after.json').exists()
    assert read(HERE/'tb_write_buffer_soc_resume.sv')==build_resume_tb()
    assert m['expected_checks']==414 and len(m['expected_modules'])==37
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m

def compile_argv(out,m):return old.compile_argv(out,m)
def job_argv(out,m,name):
    if name.startswith('isa_'):return old.job_argv(out,m,name)
    original=name=='old_program'
    return [MS/'vsim.exe','-batch','-lib',out/'work','tb_write_buffer_soc_resume','-gPOSTED=1',
        '-gREPRO_OLD_PROGRAM='+('1' if original else '0'),
        '+CPU_IMAGE='+str(ROOT/(m['old_cpu_image'] if original else m['cpu_image'])),
        '+EVENT_LOG='+str(out/(name+'.events.log')),'-logfile',out/(name+'.transcript'),'-do','run -all; quit -f']

def check_job(out,m,name):
    if name.startswith('isa_'):return old.check_job(out,m,name)
    log=read(out/(name+'.log'));assert log.strip()==read(out/(name+'.transcript')).strip()
    assert '$finish' in log and 'Errors: 0, Warnings: 0' in log
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',log)
    assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130']*4
    trace=read(out/(name+'.events.log'));assert 'EV ' in trace and 'BUS ' in trace
    if name=='old_program':
        traps=re.findall(r'DIAG_TRAP pc=(\w+) inst=(\w+) cause=(\d+) tval=(\w+) cpu_events=(\d+) AW=(\d+) W=(\d+) selftest=(\d+) busy=(\d+) flow=(\d+)',log)
        assert len(traps)==1 and traps[0][:-1]==('4000007c','00b52823','7','10000010','412','67','67','0','0')
        assert re.findall(r'CHECK: (.*)',log)==['original_missing_RUN_store_fault PASS pc=4000007c cause=7 tval=10000010']
        assert re.findall(r'RESULT: (.*)',log)==['PASS write_buffer_old_program_diagnosis events=412 original_functional_status=FAIL']
        return dict(diagnostic_status='EXACT_MISSING_RUN_STORE_FAULT_REPRODUCED',original_functional_status='FAIL',
            pc='4000007c',instruction='00b52823',cause=7,tval='10000010',events_before_fault=412)
    assert 'DIAG_TRAP' not in log
    assert re.findall(r'CHECK: (.*)',log)==['real_soc_fence_irq_stop PASS checks=414']
    rows=re.findall(r'RESULT: PASS write_buffer_soc_resume tests=(\d+) cpu_events=(\d+) IRQ=(\d+) early_acks=(\d+) I_OVERLAP=(\d+) FENCE_WAIT=(\d+) IRQ_WAIT=(\d+) STOP_WAIT=(\d+) fills=(\d+) updates=(\d+)',log)
    assert len(rows)==1 and rows[0][:3]==('414','414','1') and rows[0][-2:]==('1','65')
    assert all(int(n)>0 for n in rows[0][3:8])
    return dict(zip(('tests','cpu_events','IRQ','early_acks','I_OVERLAP','FENCE_WAIT','IRQ_WAIT','STOP_WAIT','fills','updates'),map(int,rows[0])))

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-inputs',action='store_true');p.add_argument('--tag')
    a=p.parse_args();m=require_inputs()
    if a.check_inputs:print('INPUTS_MATCH_SOC_RESUME_HDL_NOT_RUN old-program exact diagnosis + SoC414 + ISA or/lhu; prior 426/control8 reused');return
    assert a.tag==TAG and old.pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=old.git_snapshot();write(out/'git_before.json',before)
    result=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),completed={},reused_control=8,reused_key_checks=426,
                PDS_started=False,serial_opened=False)
    write(out/'result.json',result)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
            assert sha(dest)==m['sha256'][n]
        command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=command(compile_argv(out,m),out,out/'compile',60);assert 'Errors: 0, Warnings: 0' in log
        for name in ['old_program','soc','isa_or','isa_lhu']:
            command(job_argv(out,m,name),out,out/name,180)
            result['completed'][name]=check_job(out,m,name);write(out/'result.json',result)
        assert require_inputs()==m
        after=old.git_snapshot();write(out/'git_after.json',after);assert before==after
        result.update(status='WRITE_BUFFER_SOC_REPAIR_AND_TWO_ISA_PASS',inputs_unchanged=True,git_unchanged=True,
            aggregate_current_key_checks=840,scope=m['scope'],board_status='NOT_RUN')
        print('RESULT: PASS write-buffer SoC repair + precise old-program diagnosis + two pending ISA; board NOT_RUN')
    except Exception as exc:result.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',result)
if __name__=='__main__':main()
