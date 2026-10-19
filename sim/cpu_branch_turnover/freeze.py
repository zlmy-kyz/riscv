"""Task030 freeze/static preparation only; never starts HDL, PDS, or serial."""
from pathlib import Path
import ast,difflib,json,re,random,sys,itertools
from run import ROOT,HERE,MS,VENDOR,TAG,MANIFEST,sha,read,write
from prepare import programs,oracle
PREP=HERE/'build/preparation_20261014_a'
def main():
    assert not MANIFEST.exists() and not (HERE/'build'/TAG).exists()
    before=json.loads(read(PREP/'before.json'));cpu='myriscv/mycpu_sync.v'
    assert sha(PREP/'mycpu_sync_before.v')==before['source_sha256'][cpu]
    assert {n for n,h in before['source_sha256'].items() if sha(ROOT/n)!=h}=={cpu}
    for n,h in before['software_sha256'].items():assert sha(ROOT/n)==h,n
    plan=json.loads(read(HERE/'plan.json'))
    assert random.Random(plan['ISA_seed']).sample(plan['ISA_population'],2)==['auipc','sb']
    jobs=programs();assert len(jobs)==len(plan['cases'])==9
    for (name,profile,p,reset),c in zip(jobs,plan['cases']):
        assert name==c['name'] and profile==c['profile'] and reset==c['reset_pending']
        events=oracle(p);assert events==[[int(w,16) for w in row.split()] for row in read(ROOT/c['trace']).splitlines()]
        assert len(events)==c['events']
        assert [int(w,16) for w in read(ROOT/c['rom']).splitlines()]==[p.words.get(0x80000000+4*i,0x13) for i in range(4096)]
    # Exhaust the eligibility/owner transition table; this is static logic, not HDL.
    count=0
    for enabled,pending,rsp,buffer,ready,drop in itertools.product((0,1),repeat=6):
        eligible=enabled and (not pending or rsp)
        fire=eligible and ready
        pc_after=0x1004 if fire else 0x1000
        pending_after=True if fire else bool(pending and not rsp)
        dropped_after=False if fire or not pending_after else True
        assert not fire or (pc_after==0x1004 and pending_after and not dropped_after)
        assert not (pending and not rsp and fire)
        assert enabled or not fire
        count+=1
    old=read(PREP/'mycpu_sync_before.v');new=read(ROOT/cpu)
    expected=old.replace('parameter integer EXTERNAL_MEM_DRAIN_ENABLE = 0\n',
        'parameter integer EXTERNAL_MEM_DRAIN_ENABLE = 0,\n    // Ordinary ID branches may launch their target while flushing wrong-path IF.\n    parameter integer BRANCH_FETCH_TURNOVER_ENABLE = 1\n',1)
    expected=expected.replace('    wire       inst_turnover_safe;\n','    wire       inst_turnover_safe;\n    wire       branch_fetch_turnover;\n',1)
    oldlogic='''    assign inst_req_valid = resetn && fetch_valid && !redirect_valid &&
                            inst_turnover_safe &&
                            (!inst_buffer_valid || inst_buffer_pop);
    assign inst_req_addr = pc;'''
    newlogic='''    // A branch flush discards the IF buffer and any response completing now.
    // An outstanding request without a response still occupies the sole slot.
    // Trap/MRET redirects keep the original request suppression and drain path.
    assign branch_fetch_turnover = (BRANCH_FETCH_TURNOVER_ENABLE != 0) &&
                                   branch_redirect && !trap_redirect_req && !mret_redirect_req;
    assign inst_req_valid = resetn && fetch_valid &&
                            (branch_fetch_turnover ? (!inst_pending || inst_rsp_valid) :
                             (!redirect_valid && inst_turnover_safe &&
                              (!inst_buffer_valid || inst_buffer_pop)));
    assign inst_req_addr = branch_fetch_turnover ? redirect_pc : pc;'''
    assert expected.count(oldlogic)==1;expected=expected.replace(oldlogic,newlogic,1)
    expected=expected.replace('pc <= redirect_pc;','pc <= (branch_fetch_turnover && inst_req_fire) ? redirect_pc + 32\'d4 : redirect_pc;',1)
    assert expected==new,'Change outside the specified IF logic'
    (PREP/'cpu.patch').write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='before/'+cpu,tofile=cpu)),encoding='utf-8')
    for field,cases in [('control_specs',plan['cases'][:1]),('key_specs',plan['cases'])]:
        path=HERE/'fixtures'/(field+'.txt');assert not path.exists()
        path.write_text(''.join(f'{c["name"]} {c["profile"]} {c["events"]} {int(c["reset_pending"])} '
            + ' '.join(f'{c[k]:08x}' for k in ('if_fault','data_fault','irq_load','memory_target'))
            +f' {(ROOT/c["rom"]).as_posix()} {(ROOT/c["trace"]).as_posix()}\n' for c in cases))
    legacy=json.loads(read(ROOT/'sim/cpu_zmmul/isa_resume_inputs.json'))
    sources=legacy['compile_sources']+['myriscv/inst_bus_interconnect.v','sim/cpu_branch_turnover/tb_branch_turnover.sv']
    assert len(sources)==len(set(sources))
    vendors=[VENDOR/'GTP_GRS.v',VENDOR/'GTP_APM_E2.v']
    modules=[n for path in [*vendors,*[ROOT/n for n in sources]] for n in re.findall(r'^\s*module\s+(\w+)',read(path),re.M)]
    assert len(modules)==len(set(modules))
    files=set(before['source_sha256'])|set(before['software_sha256'])|set(sources)|{'myriscv/csr_defs.vh',
        'sim/cpu_zmmul/prepare_tests.py','sim/cpu_zmmul/isa_resume_inputs.json','sim/cpu_zmmul/test_plan.json','difftest/golden/rvtool.py',
        'sim/mini_board_migration/resume_inst_drm64.py','sim/mini_board_migration/resume_inst_cache32.py',
        'sim/mini_board_migration/run_inst_drm64.py'}
    for module in list(sys.modules.values()):
        filename=getattr(module,'__file__',None)
        if filename and str(Path(filename).resolve()).startswith(str(ROOT)):
            path=Path(filename).resolve()
            if path.suffix=='.py':files.add(path.relative_to(ROOT).as_posix())
    newfiles=[p.relative_to(ROOT).as_posix() for p in HERE.glob('*') if p.is_file() and p.name!='inputs.json']
    newfiles += [p.relative_to(ROOT).as_posix() for p in (HERE/'fixtures').iterdir() if p.is_file()]
    newfiles += ['tools/uart_loader/candidates/perf_2b/run_branch_turnover_measurement.py',
                 'tools/uart_loader/candidates/perf_2b/run_branch_turnover_measurements.ps1']
    files.update(newfiles)
    for c in plan['ISA_samples']:
        files.update(n for n in (c['rom'],c['ram'],c['dump'],c['traps']) if n)
    before_cpu=(PREP/'mycpu_sync_before.v').relative_to(ROOT).as_posix();files.add(before_cpu)
    files.add((PREP/'before.json').relative_to(ROOT).as_posix())
    for path in (ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_sfwd_300_01').rglob('*.json'):
        files.add(path.relative_to(ROOT).as_posix())
    for n in ('tools/uart_loader/candidates/perf_2b/run_zmmul300_measurement.py','tests/cpu_performance_2b/zmmul300_software.py'):
        files.add(n)
    for n in newfiles:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    probes=set(re.findall(r'\bdut\.(\w+)',read(HERE/'tb_branch_turnover.sv')))
    assert all(re.search(r'\b'+n+r'\b',new) for n in probes),'Unknown CPU probe'
    snapshots=sorted(set(newfiles)|set(sources)|{'myriscv/csr_defs.vh',before_cpu})
    m=dict(status='BRANCH_TURNOVER_PREPARED_HDL_NOT_RUN',fixed_tag=TAG,sha256={n:sha(ROOT/n) for n in sorted(files)},
        external_sha256={p.as_posix():sha(p) for p in [*vendors,*[MS/(n+'.exe') for n in ('vlib','vlog','vsim')]]},
        source_sha256={n:sha(ROOT/n) for n in before['source_sha256']},software_sha256=before['software_sha256'],
        compile_sources=sources,vendor_compile_sources=[p.as_posix() for p in vendors],expected_modules=modules,snapshot_files=snapshots,
        plan=plan,ISA_seed=plan['ISA_seed'],changed_registered_sources=[cpu],
        control_specs='sim/cpu_branch_turnover/fixtures/control_specs.txt',key_specs='sim/cpu_branch_turnover/fixtures/key_specs.txt',
        scope='CPU ordinary branch fetch target turnover with real inst interconnect and multiplier; strict independent event oracle455; two ISA samples only; no SoC/DDR PHY/PDS/board')
    write(MANIFEST,m)
    write(PREP/'static_review.json',dict(status='BRANCH_TURNOVER_STATIC_PREPARATION_PASS_HDL_NOT_RUN',CPU_sha256=sha(ROOT/cpu),
        previous_CPU_sha256=sha(PREP/'mycpu_sync_before.v'),manifest_sha256=sha(MANIFEST),engineering_inputs=len(files),external_inputs=5,
        snapshots=len(snapshots),modules=len(modules),changed_registered_sources=[cpu],unchanged_registered_sources=136,
        key_events=455,control_events=94,eligibility_table_rows=count,ISA_seed=plan['ISA_seed'],ISA_samples=['auipc','sb'],
        HDL_started=False,PDS_started=False,serial_opened=False))
    write(PREP/'board_plan.json',dict(status='BRANCH_TURNOVER_BOARD_PREPARED_NOT_RUN',port='COM9',iterations=300,
        baseline='sim/mini_board_migration/board/coremark_i64_d64_zmmul_sfwd_300_01',baseline_cycles=[226998804,226731331],
        baseline_seconds=[2.421320576,2.4184675306666668],new_log_directory='sim/cpu_branch_turnover/board/coremark_i64_d64_zmmul_bturn_300_01',
        software_sha256=before['software_sha256'],PDS_or_bitstream_review_required=False,serial_opened=False))
    print('BRANCH_TURNOVER_STATIC_PASS inputs',len(files),'+5 snapshots',len(snapshots),'modules',len(modules),'SHA',sha(MANIFEST),'CPU',sha(ROOT/cpu))
if __name__=='__main__':main()
