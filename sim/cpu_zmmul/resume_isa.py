"""Task023 scoped ISA continuation: old-CPU lhu control, current lhu/or; no MUL rerun."""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import re
import shutil
from run import HERE, ROOT, MS, VENDOR, require_inputs as original_inputs, command, read, write, check_log, pds_shell_count, git_snapshot
from review_task023 import audit

MANIFEST=HERE/'isa_resume_inputs.json'
TAG='ds_cpu_zmmul_isa_resume_20261013_a'
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
BOOT=[(0x800000e4,0x74445073,2,0x74445073,0x800000e8),
      (0x800000f4,0x18005073,2,0x18005073,0x800000f8),
      (0x8000010c,0x3b029073,2,0x3b029073,0x80000118),
      (0x80000128,0x30205073,2,0x30205073,0x80000130)]


def model_text(s):
    return s[s.index('    // Independent single-outstanding'):s.index('    // Compare every committed') if '    // Compare every committed' in s else s.index('    // Only five exact')]


def require_inputs():
    old=original_inputs();review=audit();m=json.loads(read(MANIFEST))
    for n,h in m['sha256'].items():assert sha(ROOT/n)==h,'Changed continuation input: '+n
    assert m['original_input_manifest_sha256']==sha(HERE/'inputs.json')
    assert review['status']=='CPU_ZMMUL_SEVEN_CASES_RAW_EVIDENCE_PASS_ISA_GATE_OPEN'
    assert m['cpu_sha256']==old['current_cpu_sha256'] and m['baseline_cpu_sha256']==old['baseline_cpu_sha256']
    assert sha(ROOT/m['baseline_cpu'])==m['baseline_cpu_sha256']
    # The new ISA monitor changes only observations. The bus model must be byte-identical
    # except one read-only accepted store-PC marker used to wait for store retirement.
    source=read(HERE/'tb_cpu_zmmul.sv');new=read(HERE/'tb_cpu_rv32i_sample.sv')
    normalized=model_text(new).replace('status_seen<=1;status_store_pc<=dut.id_ex_pc;', 'status_seen<=1;')
    assert normalized.rstrip()==model_text(source).rstrip(),'Bus-model change beyond read-only store-PC marker'
    assert 'case_id=6,isa=1' in new and 'mul_start' not in new and 'mul_busy' not in new
    assert len(m['jobs'])==3 and [j['name'] for j in m['jobs']]==['baseline_lhu','isa_lhu','isa_or']
    for sample in old['test_plan']['isa_cases']:
        words=[int(w,16) for w in read(ROOT/sample['rom']).split()]
        endpc=0x80000478 if sample['name']=='lhu' else 0x80000684
        expected=BOOT+[(endpc,0x73,11,0,0x80000004)]
        oracle=HERE/'fixtures'/('isa_'+sample['name']+'_traps.txt')
        assert [tuple(int(w,16) for w in row.split()) for row in read(oracle).splitlines()]==expected
        assert all(words[(pc-0x80000000)//4]==inst for pc,inst,_,_,_ in expected)
        # AUIPC/ADDI/CSRW install the exact probe target; the early fault skips
        # pmpcfg0 and mideleg. Do not allow blanket cause-2 exceptions.
        for auipc,addi,csrw,target in [(0xd8,0xdc,0xe0,0xe8),(0xe8,0xec,0xf0,0xf8),
                                      (0xf8,0xfc,0x100,0x118),(0x11c,0x120,0x124,0x130)]:
            assert words[auipc//4]==0x297 and words[csrw//4]==0x30529073
            imm=words[addi//4]>>20
            assert words[addi//4]&0xfffff==0x28293 and auipc+imm==target
    for name in ['resume_isa.py','review_task023.py']:ast.parse(read(HERE/name))
    return m


def architectural_events(path):
    events=[]
    for row in read(path).splitlines():
        w=row.split();assert len(w)==11 and w[0]=='EV',row
        kind=int(w[1]);pc=int(w[2],16);inst=int(w[3],16);we=int(w[4],2)
        rd=int(w[5]) if we else 0;data=int(w[6],16) if we else 0
        cause=int(w[7]) if kind==1 else 0;tval=int(w[8],16) if kind==1 else 0;target=int(w[9],16) if kind==1 else 0
        assert kind in (0,1,3) and we in (0,1)
        events.append([kind,pc,inst,we,rd if we else 0,data if we else 0,
                       cause if kind==1 else 0,tval if kind==1 else 0,target if kind==1 else 0])
    assert events and sum(e[0]==1 for e in events)==5
    return events


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--tag');p.add_argument('--check-inputs',action='store_true');a=p.parse_args()
    m=require_inputs()
    if a.check_inputs:
        print('INPUTS_MATCH_ISA_CONTINUATION_NOT_SIMULATED original=305+10 continuation='+str(len(m['sha256']))+' reused=7 jobs=baseline_lhu,isa_lhu,isa_or');return
    assert a.tag==TAG and pds_shell_count()==0,'Fixed new tag and no PDS concurrency required'
    out=HERE/'build'/TAG;out.mkdir(parents=True,exist_ok=False)
    before=git_snapshot();write(out/'git_before.json',before)
    result=dict(status='RUNNING',functional_status='INCOMPLETE',input_manifest_sha256=sha(MANIFEST),
                reused_original_cases=7,new_completed=[],pds_started=False,serial_opened=False,board_status='NOT_TESTED')
    write(out/'result.json',result)
    try:
        # Reuse original 305 frozen inputs. Archive only new continuation source/oracles.
        shutil.copyfile(MANIFEST,out/'inputs.json')
        for n in m['new_snapshot_files']:
            destination=out/'new_inputs'/n;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/n,destination);assert sha(destination)==m['sha256'][n]
        write(out/'source_identity.json',dict(original_frozen_inputs='sim/cpu_zmmul/build/ds_cpu_zmmul_20261013_a/inputs',
              original_input_manifest_sha256=m['original_input_manifest_sha256'],continuation_sha256=m['sha256']))
        compiled=set()
        for j in m['jobs']:
            variant=j['variant'];work=out/('work_'+variant)
            if variant not in compiled:
                command([MS/'vlib.exe',work],out,out/('vlib_'+variant),60)
                sources=[ROOT/n for n in m['compile_sources']]
                if variant=='baseline':sources=[ROOT/m['baseline_cpu'] if n==ROOT/'myriscv/mycpu_sync.v' else n for n in sources]
                output=command([MS/'vlog.exe','-sv','-work',work,'+incdir+'+(ROOT/'myriscv').as_posix(),
                                VENDOR/'GTP_GRS.v',VENDOR/'GTP_APM_E2.v',*sources],out,out/('compile_'+variant),60)
                assert 'Errors: 0, Warnings: 0' in output
                compiled.add(variant)
            sample=j['sample'];name=j['name'];trace=out/(name+'.events.log')
            plus=['+NAME='+name,'+ROM='+str(ROOT/sample['rom']),f'+STATUS={sample["tohost"]:08x}',
                  '+TRAPS='+str(HERE/'fixtures'/('isa_'+sample['name']+'_traps.txt')),'+EVENT_LOG='+str(trace)]
            if sample['ram']:plus+=['+RAM='+str(ROOT/sample['ram'])]
            transcript=out/(name+'.transcript')
            output=command([MS/'vsim.exe','-batch','-lib',work,'tb_cpu_rv32i_sample',*plus,
                            '-logfile',transcript,'-do','run -all; quit -f'],out,out/name,180)
            expected=f'RESULT: PASS rv32i_sample case={name} tohost=1 traps=5 probes=4 muls=0'
            check_log(output,read(transcript),expected)
            assert len(re.findall(r'^#\s*CHECK: '+name+r' PASS',output,re.M))==1
            assert len(re.findall(r'^#\s*ISA_TRAP: '+name+r' index=',output,re.M))==5
            events=architectural_events(trace)
            if name=='isa_lhu':
                baseline=architectural_events(out/'baseline_lhu.events.log')
                assert events==baseline,'Current lhu retirement/trap trace differs from frozen old CPU'
                write(out/'lhu_architectural_comparison.json',dict(status='IDENTICAL_ARCHITECTURAL_EVENTS',events=len(events),
                       baseline_trace_sha256=sha(out/'baseline_lhu.events.log'),current_trace_sha256=sha(trace),
                       ignored_fields='clock timestamp; non-writing rd/data; non-trap cause/tval/target'))
            result['new_completed'].append(dict(name=name,events=len(events),traps=5,bootstrap_probes=4,muls=0))
            write(out/'result.json',result)
        require_inputs();after=git_snapshot();write(out/'git_after.json',after);assert after==before,'Git snapshot changed'
        assert len(result['new_completed'])==3
        result.update(status='PASS',functional_status='KEY_MULTIPLY_SUITE_PLUS_TWO_ISA_SAMPLES_PASS',
                      original_cases_revalidated_from_evidence=True,cpu_events_reused=2839,muls_reused=396,
                      isa_cases=['lhu','or'],scope='CPU direct model and real multiplier; no SoC/PHY/PDS/board')
        print('RESULT: PASS cpu_zmmul_isa_continuation reused=7 isa=lhu,or old_lhu_control=PASS')
    except Exception as exc:
        result.update(status='STOPPED_FIRST_FAILURE',functional_status='INCOMPLETE',error=f'{type(exc).__name__}: {exc}')
        raise
    finally:write(out/'result.json',result)


if __name__=='__main__':main()
