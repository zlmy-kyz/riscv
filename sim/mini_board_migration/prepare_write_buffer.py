"""Static Task027 preparation only; real HDL belongs to DeepSeek."""
from pathlib import Path
import ast,json,random,re,sys,difflib
from generate_write_buffer_tb import build_tb
from run_write_buffer import ROOT,HERE,MANIFEST,TAG,VENDOR,sha,read,write,events

PREP=HERE/'build/write_buffer_preparation_20261013_a'


def offline_program(program):
    # Architectural path/count check, not an HDL run or timing measurement.
    regs=[0]*32;mem={};pc=0;total=0;irq=False;mepc=0;mtvec=0;stores=0;loads=0;perf=0
    sext=lambda v,b:(v&((1<<b)-1))-(1<<b) if v&(1<<(b-1)) else v&((1<<b)-1)
    for _ in range(1000):
        ins=program[pc];op=ins&127;rd=(ins>>7)&31;rs1=(ins>>15)&31;rs2=(ins>>20)&31
        nextpc=pc+4;value=None;address=None;total+=1
        if op==0x37:value=ins&0xfffff000
        elif op==0x13:value=regs[rs1]+sext(ins>>20,12)
        elif op==0x33:value=regs[rs1]+regs[rs2]
        elif op==3:
            address=regs[rs1]+sext(ins>>20,12);value=mem.get(address,0);loads+=1
        elif op==0x23:
            address=regs[rs1]+sext(((ins>>25)<<5)|((ins>>7)&31),12)
            if address>>12==0x40000:mem[address]=regs[rs2];stores+=1
            elif address==0x10000108:
                if regs[rs2]==3:assert perf==0;perf=1
                else:assert regs[rs2]==4 and perf==1 and stores==67;perf=2
            else:assert address==0x10000010 and regs[rs2]==2 and perf==2
        elif op==0x63:
            imm=sext(((ins>>31)<<12)|(((ins>>7)&1)<<11)|(((ins>>25)&63)<<5)|(((ins>>8)&15)<<1),13)
            if regs[rs1]<regs[rs2]:nextpc=pc+imm
        elif op==0x73:
            if ins==0x30200073:nextpc=mepc
            elif ins>>20==0x305:mtvec=regs[rs1]-0x40000000
            elif ins>>20==0x304:assert regs[rs1]==0x800
            else:assert ins==0x30046073
        else:assert op==0xf
        if value is not None and rd:regs[rd]=value&0xffffffff
        pc=nextpc
        if op==0x23 and address==0x40000800 and not irq:
            mepc=pc;pc=mtvec;irq=True;total+=1
        if address==0x10000010:break
    assert total==413 and loads==64 and stores==67 and regs[20]==1
    assert [mem[a] for a in (0x40000800,0x40000804,0x40000840,0x40000844)]==[64,2080,1,1]
    return dict(events=total,loads=loads,DDR_stores=stores,IRQ=1,final_words=[64,2080,1,1],PERF_START_STOP='3/4 at 0x108')


def main():
    assert not MANIFEST.exists() and not (HERE/'build'/TAG).exists()
    tb=HERE/'tb_write_buffer_x32.sv';assert not tb.exists();tb.write_text(build_tb(),encoding='utf-8')
    isa=read(ROOT/'sim/cpu_zmmul/tb_cpu_rv32i_sample.sv').replace('module tb_cpu_rv32i_sample;','module tb_write_buffer_isa;')
    isa=isa.replace(".irq_timer(1'b0),", ".irq_timer(1'b0),.memory_order_busy(1'b0),",1)
    (HERE/'tb_write_buffer_isa.sv').write_text(isa,encoding='utf-8')
    sys.path.insert(0,str(ROOT/'difftest/golden'));from rvtool import Assembler
    asm=Assembler();program=asm.assemble(read(HERE/'write_buffer_soc.S'))
    assert len(program)==35 and asm.sym=={'loop':64,'pass_store':124,'done':128,'handler':256}
    program_review=offline_program(program)
    image=PREP/'soc_program.hex'
    image.write_text(''.join(f'{program.get(a,0):08x}\n' for a in range(0,4096,4)),encoding='ascii')
    write(PREP/'program_review.json',dict(status='OFFLINE_ARCHITECTURAL_PROGRAM_CHECK_PASS_HDL_NOT_RUN',**program_review))
    receipt=json.loads(read(HERE/'build/ds_mini_response_turnover_decl_resume_20261013_a/codex_review.json'))
    changed=['myriscv/dual_sram_to_pango_ddr_bridge.v','myriscv/mycpu_sync.v','myriscv/data_bus_interconnect.v','myriscv/soc_top.v']
    differences={n for n,h in receipt['source_sha256'].items() if sha(ROOT/n)!=h};assert differences==set(changed)
    source_hashes={n:sha(ROOT/n) for n in receipt['source_sha256']}
    cpu=json.loads(read(ROOT/'sim/cpu_zmmul/inputs.json'))
    chosen=random.Random(2026101327).sample(cpu['test_plan']['isa_cases'],2)
    jobs=[]
    for s in chosen:
        baseline='sim/cpu_zmmul/build/ds_cpu_zmmul_isa_resume_20261013_a/isa_'+s['name']+'.events.log'
        expected_events=len(events(ROOT/baseline));assert expected_events==({'lhu':320,'or':530}[s['name']])
        jobs.append({**s,'traps':'sim/cpu_zmmul/fixtures/isa_'+s['name']+'_traps.txt',
                     'baseline_events':baseline,'expected_events':expected_events})
    core=json.loads(read(ROOT/'sim/cpu_zmmul/coremark_crc_inputs.json'))
    sources=[n for n in core['compile_sources'] if not n.startswith('sim/')]
    sources += ['ipcore/inst_rom/inst_rom.v','ipcore/inst_rom/rtl/ipm2l_rom_v1_8_inst_rom.v',
                'ipcore/inst_rom/rtl/ipm2l_spram_v1_8_inst_rom.v','ipcore/data_ram/data_ram.v',
                'ipcore/data_ram/rtl/ipm2l_spram_v1_8_data_ram.v','sim/mini_board_migration/tb_write_buffer_x32.sv',
                'sim/mini_board_migration/tb_write_buffer_isa.sv']
    sources=list(dict.fromkeys(sources))
    vendor=['GTP_GRS.v','GTP_DRM36K_E1.v','GTP_APM_E2.v']
    modules=[name for p in [*[VENDOR/n for n in vendor],*[ROOT/n for n in sources]]
             for name in re.findall(r'^\s*module\s+(\w+)',read(p),re.M)]
    assert len(modules)==len(set(modules))
    new=['sim/mini_board_migration/'+n for n in ['generate_write_buffer_tb.py','write_buffer_connections.svh',
        'write_buffer_cases.svh','write_buffer_soc.S','tb_write_buffer_x32.sv','tb_write_buffer_isa.sv',
        'run_write_buffer.py','review_write_buffer.py','prepare_write_buffer.py']]
    new+=['tools/uart_loader/candidates/perf_2b/run_write_buffer_measurement.py',
          'tools/uart_loader/candidates/perf_2b/run_write_buffer_measurements.ps1',image.relative_to(ROOT).as_posix()]
    files=set(source_hashes)|set(receipt['software_sha256'])|set(sources)|set(new)
    files.update('sim/mini_board_migration/'+n for n in ['resume_inst_drm64.py','resume_inst_cache32.py',
        'run_inst_drm64.py','run_inst_cache32.py','tb_response_turnover_x32.sv','response_turnover_cpu_mux.svh'])
    files.update(['difftest/golden/rvtool.py','sim/cpu_zmmul/tb_cpu_rv32i_sample.sv'])
    files.update(p.relative_to(ROOT).as_posix() for p in (PREP/'before').rglob('*') if p.is_file())
    for j in jobs:files.update(n for n in (j['rom'],j['ram'],j['traps'],j['baseline_events']) if n)
    for p in (ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01').rglob('*.json'):
        files.add(p.relative_to(ROOT).as_posix())
    # Dependencies of the unchanged software verifier/transport are frozen too.
    old=json.loads(read(HERE/'response_turnover_decl_resume_inputs.json'))
    files.update(n for n in old['sha256'] if n.startswith(('tools/uart_loader/','tests/cpu_performance_2b/')))
    external={n:sha(n) for n in old['external_sha256']}
    groups=[('posted_ack_instruction_overlap',8),('masked_store_readback',385),('full_entry_miss_ordering',5),
            ('instruction_invalidation',10),('reset_initialization_pause',8),('non_ddr_order_gate',10),('real_soc_fence_irq_stop',413)]
    snapshots=new+changed
    for n in new:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    m=dict(status='WRITE_BUFFER_PREPARED_HDL_NOT_RUN',fixed_tag=TAG,sha256={n:sha(ROOT/n) for n in sorted(files)},
        external_sha256=external,source_sha256=source_hashes,software_sha256=receipt['software_sha256'],
        compile_sources=sources,vendor_compile_sources=vendor,expected_modules=modules,snapshot_files=snapshots,
        cpu_image=image.relative_to(ROOT).as_posix(),groups=[dict(name=n,checks=c) for n,c in groups],
        expected_checks=839,control_checks=8,cpu_changed=True,isa_seed=2026101327,isa_jobs=jobs,
        scope='x32 one-entry posted write, real SoC/FENCE/IRQ/PERF STOP + two ISA samples; no PHY/PDS/board; x16 static only')
    write(MANIFEST,m)
    patches={}
    for n in changed:
        before=read(PREP/'before'/n);after=read(ROOT/n)
        patches[n]=''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),fromfile='before/'+n,tofile=n))
    write(PREP/'rtl_patches.json',patches)
    write(PREP/'static_review.json',dict(status='WRITE_BUFFER_STATIC_PREPARATION_PASS_HDL_NOT_RUN',
        manifest_sha256=sha(MANIFEST),RTL_sha256={n:sha(ROOT/n) for n in changed},registered_changes=changed,
        CPU_program=program_review,inputs=len(files),external_inputs=len(external),snapshot_files=len(snapshots),
        design_modules=len(modules),ISA_seed=2026101327,ISA_samples=[j['name'] for j in jobs],
        HDL_started=False,PDS_started=False,serial_opened=False))
    write(PREP/'board_plan.json',dict(status='WRITE_BUFFER_BOARD_PREPARED_NOT_RUN',iterations=300,port='COM9',
        baseline='sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01',
        baseline_cycles=[283353216,282589565],modes=['performance_300','validation_300'],
        new_log_directory='sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01',
        software_sha256=receipt['software_sha256'],PDS_or_bitstream_review_required=False,serial_opened=False))
    print('FROZEN',len(files),'external',len(external),'snapshots',len(snapshots),'modules',len(modules),
          'ISA',[j['name'] for j in jobs],'SHA',sha(MANIFEST))


if __name__=='__main__':main()
