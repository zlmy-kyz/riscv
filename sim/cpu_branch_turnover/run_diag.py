"""One Task030 coverage diagnostic key job, unchanged RTL/model/thresholds."""
from pathlib import Path
import argparse,ast,json,re,shutil
import run as original
from review_failure import compare_key
ROOT=original.ROOT;HERE=original.HERE;MS=original.MS
sha=original.sha;read=original.read;write=original.write
TAG='ds_cpu_branch_coverage_diag_20261014_a';MANIFEST=HERE/'coverage_diag_inputs.json'
FIELDS=('enable','cases','events','FAST','EMPTY','RSP','LATE','READY','BUFFER','DROP_ERR','LOAD','TRAP','IRQ','RESET')
def diagnostic_tb():
    s=read(HERE/'tb_branch_turnover.sv')
    s=s.replace('module tb_branch_turnover #','module tb_branch_turnover_diag #',1)
    anchor='    task automatic fail(input string reason);\n';assert s.count(anchor)==1
    observation='''        if(reason=="coverage totals")
            $display("COVERAGE_DIAG enable=%0d cases=%0d events=%0d FAST=%0d EMPTY=%0d RSP=%0d LATE=%0d READY=%0d BUFFER=%0d DROP_ERR=%0d LOAD=%0d TRAP=%0d IRQ=%0d RESET=%0d",
                ENABLE,case_count,total_events,fast,empty_fast,response_fast,late_wait,ready_wait,buffer_flush,discarded_errors,load_stalls,traps,irqs,resets);
'''
    return s.replace(anchor,anchor+observation,1)
def require_inputs():
    old=original.require_inputs();m=json.loads(read(MANIFEST))
    assert m['original_manifest_sha256']==sha(original.MANIFEST)
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,n
    for n,h in m['external_sha256'].items():assert sha(n)==h,n
    assert read(HERE/'tb_branch_turnover_diag.sv')==diagnostic_tb()
    for n in m['snapshot_files']:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    return m,old
def compile_argv(out,m):
    return [MS/'vlog.exe','-sv','-work',out/'work','+incdir+'+(ROOT/'myriscv').as_posix(),
        *[Path(n) for n in m['vendor_compile_sources']],*[ROOT/n for n in m['compile_sources']]]
def job_argv(out,m):
    return [MS/'vsim.exe','-batch','-lib',out/'work','tb_branch_turnover_diag','-gENABLE=1',
        '+SPECS='+str(ROOT/m['key_specs']),'+CASES=9','+EVENT_LOG='+str(out/'key.events.log'),
        '-logfile',out/'key.transcript','-do','run -all; quit -f']
def check_diag(out,m,old):
    log=read(out/'key.log');assert log.strip()==read(out/'key.transcript').strip()
    assert '$finish' in log and 'RPC_Init' not in log and 'RUNNER TIMEOUT' not in log
    checks=re.findall(r'CHECK: (\w+) PASS events=(\d+) cycles=(\d+)',log)
    assert [(n,e) for n,e,_ in checks]==[(c['name'],str(c['events'])) for c in old['plan']['cases']]
    trace=compare_key(out,old)
    fail=re.findall(r'RESULT: FAIL[^\n]*',log)
    if fail:
        assert len(fail)==1 and fail[0].endswith('coverage totals')
        assert 'Errors: 1, Warnings: 0' in log and 'RESULT: PASS branch_turnover' not in log
        prefix='COVERAGE_DIAG '
    else:
        assert 'Errors: 0, Warnings: 0' in log
        original.check_job(out,old,'key');prefix='RESULT: PASS branch_turnover '
    rows=re.findall(prefix+' '.join(k+r'=(\d+)' for k in FIELDS),log);assert len(rows)==1
    d=dict(zip(FIELDS,map(int,rows[0])))
    unmet=[k for k,v in {'enable':1,'cases':9,'events':455,'TRAP':3,'IRQ':1,'RESET':1}.items() if d[k]!=v]
    unmet += [k for k in ('FAST','EMPTY','RSP','LATE','READY','BUFFER','DROP_ERR','LOAD') if d[k]<=0]
    assert bool(unmet)==bool(fail)
    return dict(status='EXPECTED_COVERAGE_FAILURE_DIAGNOSED' if fail else 'COVERAGE_DIAGNOSTIC_PASS_ONLY',
        counters=d,unmet_conditions=unmet,trace=trace,case_cycles={n:int(c) for n,_,c in checks},
        ISA_status='NOT_RUN',functional_gate='INCOMPLETE')
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag');p.add_argument('--check-inputs',action='store_true');a=p.parse_args()
    m,old=require_inputs()
    if a.check_inputs:print('DIAGNOSTIC_INPUTS_MATCH_RTL_MODEL_THRESHOLDS_UNCHANGED; one key; HDL NOT_RUN');return
    assert a.tag==TAG and original.pds_shell_count()==0
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=original.git_snapshot();write(out/'git_before.json',before)
    r=dict(status='RUNNING',manifest_sha256=sha(MANIFEST),HDL_jobs=1,ISA_status='NOT_RUN',PDS_started=False,serial_opened=False)
    write(out/'result.json',r)
    try:
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['snapshot_files']:
            dest=out/'inputs'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest);assert sha(dest)==m['sha256'][n]
        original.command([MS/'vlib.exe',out/'work'],out,out/'vlib',60)
        log=original.command(compile_argv(out,m),out,out/'compile',60)
        modules=re.findall(r'-- Compiling module (\w+)',log)
        assert len(modules)==16 and set(modules)==set(m['expected_modules']) and 'Errors: 0, Warnings: 0' in log
        try:original.command(job_argv(out,m),out,out/'key',180)
        except AssertionError:
            # The already known coverage fatal is the observation target. Every other
            # failure/timeout still stops, preserving incomplete diagnostic evidence.
            assert re.search(r'RESULT: FAIL[^\n]*coverage totals',read(out/'key.log'))
        meta=json.loads(read(out/'key.command.json'))
        assert meta['exit_code']==meta['native_exit_after_wait']==0 and not meta['timed_out'] and meta['cleanup'] is None
        r['diagnostic']=check_diag(out,m,old)
        assert require_inputs()==(m,old)
        after=original.git_snapshot();write(out/'git_after.json',after);assert after==before
        r.update(status='COVERAGE_DIAGNOSTIC_COMPLETE_NOT_FUNCTIONAL_PASS',inputs_unchanged=True,git_unchanged=True,
            old_evidence_preserved=True,functional_gate='INCOMPLETE')
        print('DIAGNOSTIC COMPLETE unmet='+','.join(r['diagnostic']['unmet_conditions'])+'; ISA/board NOT_RUN')
    except Exception as exc:r.update(status='STOPPED_FIRST_UNEXPECTED_FAILURE',error=f'{type(exc).__name__}: {exc}');raise
    finally:write(out/'result.json',r)
if __name__=='__main__':main()
