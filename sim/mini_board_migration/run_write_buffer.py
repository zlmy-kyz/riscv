"""Task027 one key suite, minimal disabled control and two mandated CPU ISA samples."""
from pathlib import Path
import argparse,ast,hashlib,json,re,shutil
from resume_inst_drm64 import command
from resume_inst_cache32 import git_snapshot,pds_shell_count
from generate_write_buffer_tb import build_tb

HERE=Path(__file__).resolve().parent;ROOT=HERE.parents[1]
MS=Path('D:/modelsim/win64pe');VENDOR=Path('C:/pango/PDS_2022.2-SP6.4/arch/vendor/pango/verilog/simulation')
MANIFEST=HERE/'write_buffer_inputs.json';TAG='ds_mini_write_buffer_20261013_a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:Path(p).read_text(encoding='utf-8',errors='replace')
write=lambda p,d:Path(p).write_text(json.dumps(d,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')


def require_inputs():
    m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    assert read(HERE/'tb_write_buffer_x32.sv')==build_tb()
    assert sum(g['checks'] for g in m['groups'])==839
    cases=read(HERE/'write_buffer_cases.svh')
    assert re.findall(r'checkpoint\("(\w+)",(\d+)\)',cases)==[('disabled_legacy_contract','8')]+[(g['name'],str(g['checks'])) for g in m['groups'][:-1]]
    assert 'real_soc_fence_irq_stop PASS checks=413' in cases
    source=read(ROOT/'sim/cpu_zmmul/tb_cpu_rv32i_sample.sv')
    expected=source.replace('module tb_cpu_rv32i_sample;','module tb_write_buffer_isa;').replace(
        ".irq_timer(1'b0),", ".irq_timer(1'b0),.memory_order_busy(1'b0),",1)
    assert read(HERE/'tb_write_buffer_isa.sv')==expected
    assert m['cpu_changed'] and m['isa_seed']==2026101327 and len(m['isa_jobs'])==2
    assert {j['name'] for j in m['isa_jobs']}=={'lhu','or'}
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    assert '.memory_order_busy (ddr_write_buffer_busy)' in read(ROOT/'myriscv/soc_top.v')
    assert '.ddr_write_buffer_busy(ddr_write_buffer_busy)' in read(ROOT/'myriscv/soc_top.v')
    assert '.POSTED_WRITE_ENABLE(DDR_WRITE_ORDER_ACTIVE)' in read(ROOT/'myriscv/soc_top.v')
    return m


def compile_argv(out,m):
    return [MS/'vlog.exe','-sv','+incdir+'+str(ROOT/'myriscv'),'+incdir+'+str(HERE),
            '+incdir+'+str(ROOT/'ipcore/inst_rom/rtl'),'+incdir+'+str(ROOT/'ipcore/data_ram/rtl'),'-work',out/'work',
            *[VENDOR/n for n in m['vendor_compile_sources']],*[ROOT/n for n in m['compile_sources']]]


def job_argv(out,m,name):
    if name in ('control','key'):
        return [MS/'vsim.exe','-batch','-lib',out/'work','tb_write_buffer_x32',
                '-gPOSTED='+('0' if name=='control' else '1'),'+CPU_IMAGE='+str(ROOT/m['cpu_image']),
                '-logfile',out/(name+'.transcript'),'-do','run -all; quit -f']
    job=next(j for j in m['isa_jobs'] if 'isa_'+j['name']==name)
    args=['+NAME='+name,'+ROM='+str(ROOT/job['rom']),f'+STATUS={job["tohost"]:08x}',
          '+TRAPS='+str(ROOT/job['traps']),'+EVENT_LOG='+str(out/(name+'.events.log'))]
    if job['ram']:args+=['+RAM='+str(ROOT/job['ram'])]
    return [MS/'vsim.exe','-batch','-lib',out/'work','tb_write_buffer_isa',*args,
            '-logfile',out/(name+'.transcript'),'-do','run -all; quit -f']


def events(p):
    result=[]
    for row in read(p).splitlines():
        w=row.split();assert len(w)==11 and w[0]=='EV'
        k=int(w[1]);we=int(w[4],2);assert k in (0,1,3) and we in (0,1)
        result.append([k,int(w[2],16),int(w[3],16),we,int(w[5]) if we else 0,
            int(w[6],16) if we else 0,int(w[7]) if k==1 else 0,int(w[8],16) if k==1 else 0,int(w[9],16) if k==1 else 0])
    assert result and sum(e[0]==1 for e in result)==5
    return result


def check_job(out,m,name):
    console=read(out/(name+'.log'));transcript=read(out/(name+'.transcript'))
    assert console.strip()==transcript.strip() and '$finish' in console and 'Errors: 0, Warnings: 0' in console
    assert not re.search(r'RESULT: FAIL|\*\* (?:Error|Fatal)|RPC_Init|RUNNER TIMEOUT',console)
    if name in ('key','control'):
        assert re.findall(r'IPSpecCheck: (\d+)',console)==['04030130']*4
        if name=='control':
            assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',console)==[('disabled_legacy_contract','8')]
            assert re.findall(r'RESULT: PASS write_buffer_control tests=(\d+)',console)==['8']
            return {'tests':8}
        assert re.findall(r'CHECK: (\w+) PASS checks=(\d+)',console)==[(g['name'],str(g['checks'])) for g in m['groups']]
        rows=re.findall(r'RESULT: PASS write_buffer_x32 tests=(\d+) cpu_events=(\d+) IRQ=(\d+) early_acks=(\d+) I_OVERLAP=(\d+) FENCE_WAIT=(\d+) IRQ_WAIT=(\d+) STOP_WAIT=(\d+) fills=(\d+) updates=(\d+)',console)
        assert len(rows)==1 and rows[0][:3]==('839','413','1') and rows[0][-2:]==('8','198')
        assert all(int(v)>0 for v in rows[0][3:8])
        return dict(zip(('tests','cpu_events','IRQ','early_acks','I_OVERLAP','FENCE_WAIT','IRQ_WAIT','STOP_WAIT','fills','updates'),map(int,rows[0])))
    assert len(re.findall(r'RESULT: PASS rv32i_sample case='+name+r' tohost=1 traps=5 probes=4 muls=0',console))==1
    j=next(j for j in m['isa_jobs'] if name=='isa_'+j['name'])
    current=events(out/(name+'.events.log'));baseline=events(ROOT/j['baseline_events'])
    assert current==baseline and len(current)==j['expected_events']
    return {'events':len(current),'traps':5,'architectural_events_identical':True}


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--check-inputs',action='store_true');p.add_argument('--tag')
    a=p.parse_args();m=require_inputs()
    if a.check_inputs:print('INPUTS_MATCH_WRITE_BUFFER_HDL_NOT_RUN key=839 control=8 ISA='+','.join(j['name'] for j in m['isa_jobs']));return
    assert a.tag==TAG and pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=git_snapshot();write(out/'git_before.json',before)
    result={'status':'RUNNING','manifest_sha256':sha(MANIFEST),'completed':{},'PDS_started':False,'serial_opened':False}
    write(out/'result.json',result)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
            assert sha(dest)==m['sha256'][n]
        command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=command(compile_argv(out,m),out,out/'compile',60);assert 'Errors: 0, Warnings: 0' in log
        for name in ['control','key',*['isa_'+j['name'] for j in m['isa_jobs']]]:
            command(job_argv(out,m,name),out,out/name,180)
            result['completed'][name]=check_job(out,m,name);write(out/'result.json',result)
        assert require_inputs()==m
        after=git_snapshot();write(out/'git_after.json',after);assert before==after
        result.update(status='WRITE_BUFFER_KEY_AND_TWO_ISA_PASS',inputs_unchanged=True,git_unchanged=True,CPU_changed=True,
                      scope=m['scope'],board_status='NOT_RUN')
        print('RESULT: PASS write buffer key + disabled control + two ISA samples; board NOT_RUN')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',result)


if __name__=='__main__':main()
