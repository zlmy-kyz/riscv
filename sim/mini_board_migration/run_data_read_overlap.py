"""Task028: one D-hit-under-write key suite plus minimal disabled control; no ISA rerun."""
import argparse,ast,json,re,shutil
import run_write_buffer as base
from generate_data_read_overlap_tb import build_tb
ROOT=base.ROOT;HERE=base.HERE;MS=base.MS;VENDOR=base.VENDOR
sha=base.sha;read=base.read;write=base.write;command=base.command
TAG='ds_mini_data_read_overlap_20261013_a';MANIFEST=HERE/'data_read_overlap_inputs.json'
def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    assert read(HERE/'tb_data_read_overlap_x32.sv')==build_tb()
    assert sum(g['checks'] for g in m['groups'])==1597 and not m['CPU_changed'] and m['ISA_samples']==[]
    assert len(m['expected_modules'])==36
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m
def compile_argv(out,m):return base.compile_argv(out,m)
def job_argv(out,m,name):
    return [MS/'vsim.exe','-batch','-lib',out/'work','tb_data_read_overlap_x32',
        '-gREAD_OVERLAP='+('0' if name=='control' else '1'),'+CPU_IMAGE='+str(ROOT/m['cpu_image']),
        '+EVENT_LOG='+str(out/(name+'.events.log')),'-logfile',out/(name+'.transcript'),'-do','run -all; quit -f']
def check_job(out,m,name):
    log=read(out/(name+'.log'));assert log.strip()==read(out/(name+'.transcript')).strip()
    assert '$finish' in log and 'Errors: 0, Warnings: 0' in log
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',log)
    assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130']*4
    if name=='control':
        assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',log)==[('disabled_read_overlap_control','8')]
        assert re.findall(r'RESULT: PASS data_read_overlap_control tests=(\d+)',log)==['8']
        return dict(tests=8)
    assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',log)==[(g['name'],str(g['checks'])) for g in m['groups']]
    rows=re.findall(r'RESULT: PASS data_read_overlap_x32 tests=(\d+) cpu_events=(\d+) IRQ=(\d+) early_acks=(\d+) I_OVERLAP=(\d+) FENCE_WAIT=(\d+) IRQ_WAIT=(\d+) STOP_WAIT=(\d+) fills=(\d+) updates=(\d+) D_OVERLAP=(\d+) SOC_D_OVERLAP=(\d+)',log)
    assert len(rows)==1 and rows[0][:3]==('1597','480','1') and rows[0][8:10]==('2','65')
    assert all(int(v)>0 for v in rows[0][3:8]) and int(rows[0][11])>0 and int(rows[0][10])-int(rows[0][11])==514
    trace=read(out/'key.events.log');assert 'EV ' in trace and 'BUS ' in trace
    return dict(zip(('tests','cpu_events','IRQ','early_acks','I_OVERLAP','FENCE_WAIT','IRQ_WAIT','STOP_WAIT',
        'soc_fills','soc_updates','D_OVERLAP','SOC_D_OVERLAP'),map(int,rows[0])))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-inputs',action='store_true');p.add_argument('--tag')
    a=p.parse_args();m=require_inputs()
    if a.check_inputs:print('INPUTS_MATCH_DATA_READ_OVERLAP_HDL_NOT_RUN key=1597 control=8 ISA=0 CPU480');return
    assert a.tag==TAG and base.pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=base.git_snapshot();write(out/'git_before.json',before)
    r=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),completed={},PDS_started=False,serial_opened=False,CPU_changed=False)
    write(out/'result.json',r)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
            assert sha(dest)==m['sha256'][n]
        command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=command(compile_argv(out,m),out,out/'compile',60);assert 'Errors: 0, Warnings: 0' in log
        for name in ('control','key'):
            command(job_argv(out,m,name),out,out/name,180)
            r['completed'][name]=check_job(out,m,name);write(out/'result.json',r)
        assert require_inputs()==m
        after=base.git_snapshot();write(out/'git_after.json',after);assert before==after
        r.update(status='DATA_READ_OVERLAP_KEY_PASS',inputs_unchanged=True,git_unchanged=True,scope=m['scope'],board_status='NOT_RUN')
        print('RESULT: PASS D-read overlap key + minimal disabled control; board NOT_RUN')
    except Exception as exc:r.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',r)
if __name__=='__main__':main()
