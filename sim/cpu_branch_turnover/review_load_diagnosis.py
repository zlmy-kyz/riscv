"""Codex audit of reported LOAD diagnostics; no HDL and no functional gate."""
import json,re
from pathlib import Path
import run as stage
import diag_counters as counters
import diag_load_use as probe
import diag_load_profile as profile
from review_failure import compare_key
ROOT=stage.ROOT;HERE=stage.HERE;PREP=HERE/'build/loaduse_resume_preparation_20261014_a'
def main():
    m=stage.require_inputs();PREP.mkdir(parents=True,exist_ok=True);assert not (PREP/'diagnosis_review.json').exists()
    source=stage.read(HERE/'tb_branch_turnover.sv');evidence={};jobs={}
    for script,filename in [(counters,'tb_branch_turnover_diag.sv'),(probe,'tb_branch_turnover_diag2.sv'),(profile,'tb_branch_turnover_diag3.sv')]:
        out=HERE/'build'/script.TAG;tb=out/filename
        expected=source.replace(script.OLD_MODULE,script.NEW_MODULE,1)
        if script is probe:expected=expected.replace(script.ANCHOR,script.PROBE,1)
        else:expected=expected.replace(script.OLD_DISPLAY,script.NEW_DISPLAY,1)
        assert stage.read(tb)==expected,'Diagnostic changed model/criteria'
        assert (out/'inputs.json').read_bytes()==stage.MANIFEST.read_bytes()
        for name in ('vlib','compile','key'):
            c=json.loads(stage.read(out/(name+'.command.json')));assert c['exit_code']==0 and c['cwd']==str(out)
            if name!='key':assert c['native_exit_after_wait']==0 and not c['timed_out']
            if name=='key':
                spec=out/'key_specs_profile0.txt' if script is profile else HERE/'fixtures/key_specs.txt'
                args=[stage.MS/'vsim.exe','-batch','-lib',out/'work',script.NEW_MODULE.split()[1],'-gENABLE=1',
                    '+SPECS='+str(spec),'+CASES=9','+EVENT_LOG='+str(out/'key.events.log'),
                    '-logfile',out/'key.transcript','-do','run -all; quit -f']
            elif name=='vlib':args=[stage.MS/'vlib.exe',out/'work']
            else:args=[stage.MS/'vlog.exe','-sv','-work',out/'work','+incdir+'+(ROOT/'myriscv').as_posix(),
                *[Path(p) for p in m['vendor_compile_sources']],*[ROOT/n for n in m['compile_sources'] if not n.endswith('/tb_branch_turnover.sv')],tb]
            assert c['argv']==list(map(str,args)),name
        log=stage.read(out/'key.log');assert log.strip()==stage.read(out/'key.transcript').strip()
        assert '$finish' in log and 'RPC_Init' not in log and 'RUNNER TIMEOUT' not in log
        modules=re.findall(r'-- Compiling module (\w+)',stage.read(out/'compile.log'))
        assert len(modules)==16 and 'Errors: 0, Warnings: 0' in stage.read(out/'compile.log')
        trace=compare_key(out,m);jobs[script.TAG]=trace
        for p in out.rglob('*'):
            if p.is_file():evidence[p.relative_to(ROOT).as_posix()]=stage.sha(p)
    first=stage.read(HERE/'build'/counters.TAG/'key.log')
    counts=dict(re.findall(r'(FAST|EMPTY|RSP|LATE|READY|BUFFER|DROP_ERR|LOAD|TRAP|IRQ|RESET|CASES)=(\d+)',
        re.findall(r'CHECK: irq_load_drain[^\n]+',first)[0]))
    assert {k:int(v) for k,v in counts.items()}==dict(FAST=55,EMPTY=5,RSP=50,LATE=96,READY=47,BUFFER=5,DROP_ERR=35,LOAD=0,TRAP=3,IRQ=1,RESET=1,CASES=9)
    assert 'coverage totals' in first and 'Errors: 1, Warnings: 0' in first
    plog=stage.read(HERE/'build'/probe.TAG/'key.log')
    rows=[dict(re.findall(r'(\w+)=(\w+)',l)) for l in plog.splitlines() if 'PROBE ' in l]
    row12=next(r for r in rows if r['cy']=='12');row13=next(r for r in rows if r['cy']=='13')
    assert (row12['ixv'],row12['ixl'],row12['ifidv'],row12['lu'])==('1','1','0','0')
    assert (row13['ixl'],row13['ifidv'],row13['dps'],row13['lu'])==('0','1','1','0')
    assert all(r['lu']=='0' for r in rows)
    current=stage.read(ROOT/'myriscv/mycpu_sync.v');before=stage.read(HERE/'build/preparation_20261014_a/mycpu_sync_before.v')
    assert re.findall(r'assign load_use =.*?;',current,re.S)==re.findall(r'assign load_use =.*?;',before,re.S)
    oldspec=[row.split() for row in stage.read(HERE/'fixtures/key_specs.txt').splitlines()]
    newspec=[row.split() for row in stage.read(HERE/'build'/profile.TAG/'key_specs_profile0.txt').splitlines()]
    changes=[(i,j,a,b) for i,(aa,bb) in enumerate(zip(oldspec,newspec)) for j,(a,b) in enumerate(zip(aa,bb)) if a!=b]
    assert len(oldspec)==len(newspec)==9 and changes==[(4,1,'1','0')]
    fixed=stage.read(HERE/'build'/profile.TAG/'key.log')
    assert 'Errors: 0, Warnings: 0' in fixed and 'RESULT: FAIL' not in fixed
    assert 'events=455 FAST=56 EMPTY=5 RSP=51 LATE=96 READY=47 BUFFER=5 DROP_ERR=35 LOAD=3 TRAP=3 IRQ=1 RESET=1' in fixed
    old=json.loads(stage.read(HERE/'build/coverage_diag_preparation_20261014_a/old_failure_review.json'))
    for n,h in old['old_evidence_sha256'].items():assert stage.sha(ROOT/n)==h,n
    evidence.update(old['old_evidence_sha256'])
    for p in (HERE/'diag_counters.py',HERE/'diag_load_use.py',HERE/'diag_load_profile.py'):
        evidence[p.relative_to(ROOT).as_posix()]=stage.sha(p)
    stage.write(PREP/'diagnosis_review.json',dict(status='LOAD_USE_STIMULUS_GAP_RAW_DIAGNOSIS_CONFIRMED',
        old_unmet='LOAD',old_counters={k:int(v) for k,v in counts.items()},three_diagnostic_traces=jobs,
        probe_cycle12=row12,probe_cycle13=row13,spec_change='Only load_branch_jalr profile1 to profile0',
        profile0_LOAD=3,oracle_mismatches=0,load_use_RTL_unchanged=True,evidence_sha256=evidence,
        diagnostic_metadata_limitation='Key diagnostic command records contain only argv/cwd/exit_code; native/time/timeout fields absent; not credited as formal runner closure',
        ISA_status='NOT_RUN',functional_gate='INCOMPLETE',HDL_started_by_Codex=False,PDS_started=False,serial_opened=False))
    print('LOAD_USE_STIMULUS_GAP_RAW_DIAGNOSIS_CONFIRMED; profile0 LOAD3; original67 files preserved; formal gate incomplete')
if __name__=='__main__':main()
