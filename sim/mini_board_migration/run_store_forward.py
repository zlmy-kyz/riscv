"""Task029: one byte-forwarding key suite and disabled-forwarding control; CPU unchanged."""
import argparse,ast,inspect,json,re
import run_data_read_overlap as base
from generate_store_forward_tb import build_tb
ROOT=base.ROOT;HERE=base.HERE;MS=base.MS;VENDOR=base.VENDOR
sha=base.sha;read=base.read;write=base.write
TAG='ds_mini_store_forward_20261014_a';MANIFEST=HERE/'store_forward_inputs.json'
def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    assert read(HERE/'tb_store_forward_x32.sv')==build_tb()
    assert sum(g['checks'] for g in m['groups'])==2238 and len(m['expected_modules'])==36
    assert not m['CPU_changed'] and m['ISA_samples']==[]
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m
compile_argv=base.compile_argv
def job_argv(out,m,name):
    return [MS/'vsim.exe','-batch','-lib',out/'work','tb_store_forward_x32',
        '-gFORWARD_ENABLE='+('0' if name=='control' else '1'),'+CPU_IMAGE='+str(ROOT/m['cpu_image']),
        '+EVENT_LOG='+str(out/(name+'.events.log')),'-logfile',out/(name+'.transcript'),'-do','run -all; quit -f']
def check_job(out,m,name):
    log=read(out/(name+'.log'));assert log.strip()==read(out/(name+'.transcript')).strip()
    assert '$finish' in log and 'Errors: 0, Warnings: 0' in log
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',log)
    assert re.findall(r'IPSpecCheck: (\d+)',log)==['04030130']*4
    if name=='control':
        assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',log)==[('disabled_store_forward_control','8')]
        assert re.findall(r'RESULT: PASS store_forward_control tests=(\d+)',log)==['8']
        return dict(tests=8)
    assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',log)==[(g['name'],str(g['checks'])) for g in m['groups']]
    names=('tests','cpu_events','IRQ','early_acks','I_OVERLAP','FENCE_WAIT','IRQ_WAIT','STOP_WAIT','fills','updates',
        'D_OVERLAP','SOC_D_OVERLAP','SAME_LINE','WORD_FORWARD','SOC_SAME_LINE','SOC_WORD_FORWARD','COLLISION_BLOCKS','RSP_W_OVERLAP')
    pattern='RESULT: PASS store_forward_x32 '+' '.join(n+r'=(\d+)' for n in names)
    rows=re.findall(pattern,log);assert len(rows)==1
    d=dict(zip(names,map(int,rows[0])))
    assert d['tests']==2238 and d['cpu_events']==489 and d['IRQ']==1 and d['fills']==2 and d['updates']==69
    assert all(d[n]>0 for n in names[3:8]) and d['SOC_WORD_FORWARD']>0 and d['SOC_SAME_LINE']>0
    assert d['SAME_LINE']-d['SOC_SAME_LINE']==1184 and d['WORD_FORWARD']-d['SOC_WORD_FORWARD']==217
    assert d['COLLISION_BLOCKS']>=16 and d['RSP_W_OVERLAP']>=16
    trace=read(out/'key.events.log');assert 'EV ' in trace and 'BUS ' in trace
    return d
def main():
    source=inspect.getsource(base.main).replace('DATA_READ_OVERLAP_KEY_PASS','STORE_FORWARD_KEY_PASS',1)
    source=source.replace('INPUTS_MATCH_DATA_READ_OVERLAP_HDL_NOT_RUN key=1597 control=8 ISA=0 CPU480',
        'INPUTS_MATCH_STORE_FORWARD_HDL_NOT_RUN key=2238 control=8 ISA=0 CPU489',1)
    source=source.replace('D-read overlap key + minimal disabled control','store-forward key + minimal disabled control',1)
    namespace=dict(base.__dict__,TAG=TAG,MANIFEST=MANIFEST,require_inputs=require_inputs,
                   compile_argv=compile_argv,job_argv=job_argv,check_job=check_job)
    exec(compile(source,'<Task029_same_once_runner>','exec'),namespace);namespace['main']()
if __name__=='__main__':main()
