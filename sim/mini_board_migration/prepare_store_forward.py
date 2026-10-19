"""Task029 static preparation and independent byte-addressed program oracle; no HDL."""
import ast,difflib,json,re,sys
from run_store_forward import ROOT,HERE,MANIFEST,TAG,VENDOR,sha,read,write
from generate_store_forward_tb import build_tb
PREP=HERE/'build/store_forward_preparation_20261013_a'
def program_check(p):
    regs=[0]*32;mem={};pc=0;events=0;loads=0;stores=0;irq=False;mepc=0;mtvec=0;perf=0;test=0;typed=[]
    def sext(v,b):
        v&=(1<<b)-1
        return v-(1<<b) if v&(1<<(b-1)) else v
    for _ in range(1000):
        ins=p[pc];op=ins&127;rd=(ins>>7)&31;r1=(ins>>15)&31;r2=(ins>>20)&31;f3=(ins>>12)&7
        nextpc=pc+4;value=None;addr=None;events+=1
        if op==0x37:value=ins&0xfffff000
        elif op==0x13:value=regs[r1]+sext(ins>>20,12)
        elif op==0x33:value=regs[r1]+regs[r2]
        elif op==3:
            addr=regs[r1]+sext(ins>>20,12);size={0:1,1:2,2:4,4:1,5:2}[f3]
            value=sum(mem.get(addr+i,0)<<(8*i) for i in range(size));loads+=1
            if f3 in (0,1):value=sext(value,size*8)
            if f3!=2:typed.append(value)
        elif op==0x23:
            addr=regs[r1]+sext(((ins>>25)<<5)|((ins>>7)&31),12)
            if addr>>12==0x40000:
                for i in range({0:1,1:2,2:4}[f3]):mem[addr+i]=(regs[r2]>>(8*i))&255
                stores+=1
            elif addr==0x10000108:
                if regs[r2]==3:assert perf==0;perf=1
                else:assert regs[r2]==4 and perf==1 and stores==71;perf=2
            else:
                assert addr==0x10000010
                if regs[r2]==1:assert test==0 and perf==1;test=1
                else:assert regs[r2]==2 and test==1 and perf==2;test=2
        elif op==0x63:
            imm=sext(((ins>>31)<<12)|(((ins>>7)&1)<<11)|(((ins>>25)&63)<<5)|(((ins>>8)&15)<<1),13)
            if sext(regs[r1],32)<sext(regs[r2],32):nextpc=pc+imm
        elif op==0x73:
            if ins==0x30200073:nextpc=mepc
            elif ins>>20==0x305:mtvec=regs[r1]-0x40000000
            elif ins>>20==0x304:assert regs[r1]==0x800
            else:assert ins==0x30046073
        else:assert op==15
        if value is not None and rd:regs[rd]=value&0xffffffff
        pc=nextpc
        if op==0x23 and addr==0x40000800 and not irq:
            mepc=pc;pc=mtvec;irq=True;events+=1
        if test==2:break
    assert events==489 and loads==133 and stores==71 and regs[20]==1
    assert typed==[-128,128,-128,65408]
    words=[sum(mem[a+i]<<(8*i) for i in range(4)) for a in (0x40000800,0x40000804,0x40000840,0x40000844)]
    assert words==[64,2080,1,1]
    return dict(events=events,loads=loads,DDR_stores=stores,IRQ=1,final_words=words,typed_load_values=typed,
                PERF_START_STOP='3/4 at 0x108',TEST_STATUS='RUN1 then PASS2')
def main():
    assert not MANIFEST.exists() and not (HERE/'build'/TAG).exists()
    rpath=HERE/'build/ds_mini_data_read_overlap_20261013_a/codex_review.json';r=json.loads(read(rpath))
    bridge='myriscv/dual_sram_to_pango_ddr_bridge.v'
    assert {n for n,h in r['source_sha256'].items() if sha(ROOT/n)!=h}=={bridge}
    assert sha(PREP/'before'/bridge)==r['source_sha256'][bridge]
    for n,h in r['software_sha256'].items():assert sha(ROOT/n)==h
    src=read(HERE/'data_read_overlap_soc.S')
    src=src.replace('    lw x8, 0(x7) # Hit this other line while the store drains',
        '    lw x9, 0(x1) # Forward the immediately preceding store to the same word',1)
    anchor='    sw x4, 4(x1)\n';assert src.count(anchor)==1
    extra='''    addi x6, x0, -128
    sb x6, 1(x1)
    lb x9, 1(x1)
    lbu x10, 1(x1)
    sw x2, 0(x1)
    sh x6, 2(x1)
    lh x11, 2(x1)
    lhu x8, 2(x1)
    sw x2, 0(x1)
'''
    src=src.replace(anchor,extra+anchor,1)
    source=HERE/'store_forward_soc.S';assert not source.exists();source.write_text(src,encoding='utf-8')
    sys.path.insert(0,str(ROOT/'difftest/golden'));from rvtool import Assembler
    asm=Assembler();p=asm.assemble(src);review=program_check(p)
    assert len(p)==48 and asm.sym=={'loop':72,'pass_store':176,'done':180,'handler':256}
    image=PREP/'soc_program.hex';assert not image.exists()
    image.write_text(''.join(f'{p.get(a,0):08x}\n' for a in range(0,4096,4)),encoding='ascii')
    tb=HERE/'tb_store_forward_x32.sv';assert not tb.exists();tb.write_text(build_tb(),encoding='utf-8')
    old=json.loads(read(HERE/'data_read_overlap_inputs.json'))
    sources=[n.replace('tb_data_read_overlap_x32.sv','tb_store_forward_x32.sv') for n in old['compile_sources']]
    modules=[n for pth in [*[VENDOR/n for n in old['vendor_compile_sources']],*[ROOT/n for n in sources]]
        for n in re.findall(r'^\s*module\s+(\w+)',read(pth),re.M)]
    assert len(modules)==36 and len(set(modules))==36
    new=['sim/mini_board_migration/'+n for n in ['generate_store_forward_tb.py','store_forward_cases.svh',
        'store_forward_soc.S','tb_store_forward_x32.sv','run_store_forward.py','review_store_forward.py','prepare_store_forward.py']]
    new+=['tools/uart_loader/candidates/perf_2b/run_store_forward_measurement.py',
        'tools/uart_loader/candidates/perf_2b/run_store_forward_measurements.ps1',image.relative_to(ROOT).as_posix()]
    files=set(old['sha256'])|set(new)|{rpath.relative_to(ROOT).as_posix(),
        'sim/mini_board_migration/data_read_overlap_inputs.json',(PREP/'before'/bridge).relative_to(ROOT).as_posix()}
    for pth in (HERE/'board/coremark_i64_d64_zmmul_dread_300_01').rglob('*.json'):files.add(pth.relative_to(ROOT).as_posix())
    for n in new:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    groups=[('forward_response_owner_clear',8),('all_write_read_words_byte_masks',1280),('all_line_indices_forward',320),
        ('unaligned_byte_half_packets',24),('miss_alias_and_store_order',12),('W_accept_and_response_boundaries',96),
        ('reset_init_forward_metadata_clear',9),('real_soc_store_forward_typed_loads',489)]
    assert sum(v for _,v in groups)==2238
    m=dict(status='STORE_FORWARD_PREPARED_HDL_NOT_RUN',fixed_tag=TAG,sha256={n:sha(ROOT/n) for n in sorted(files)},
        external_sha256=old['external_sha256'],source_sha256={n:sha(ROOT/n) for n in r['source_sha256']},
        software_sha256=r['software_sha256'],compile_sources=sources,vendor_compile_sources=old['vendor_compile_sources'],
        expected_modules=modules,snapshot_files=new+[bridge],cpu_image=image.relative_to(ROOT).as_posix(),
        groups=[dict(name=n,checks=v) for n,v in groups],expected_checks=2238,control_checks=8,CPU_changed=False,ISA_samples=[],
        scope='x32 byte forwarding for cache-hit loads; collision guard and pinned response mask; typed SB/SH/LB/LBU/LH/LHU SoC489; x16 static; no PHY/PDS/board')
    write(MANIFEST,m)
    (PREP/'bridge.patch').write_text(''.join(difflib.unified_diff(read(PREP/'before'/bridge).splitlines(True),read(ROOT/bridge).splitlines(True),
        fromfile='before/'+bridge,tofile=bridge)),encoding='utf-8')
    write(PREP/'static_review.json',dict(status='STORE_FORWARD_STATIC_PREPARATION_PASS_HDL_NOT_RUN',manifest_sha256=sha(MANIFEST),
        bridge_sha256=sha(ROOT/bridge),previous_bridge_sha256=sha(PREP/'before'/bridge),inputs=len(files),external_inputs=10,
        snapshots=11,design_modules=36,changed_registered_sources=[bridge],unchanged_registered_sources=136,
        CPU_program=review,CPU_changed=False,ISA_samples=[],key_checks=2238,control_checks=8,
        manual_same_line_reads=1184,manual_word_forwards=217,manual_collision_blocks=16,manual_response_W_overlaps=16,
        HDL_started=False,PDS_started=False,serial_opened=False))
    write(PREP/'board_plan.json',dict(status='STORE_FORWARD_BOARD_PREPARED_NOT_RUN',port='COM9',iterations=300,
        baseline='sim/mini_board_migration/board/coremark_i64_d64_zmmul_dread_300_01',baseline_cycles=[231832909,231467889],
        baseline_seconds=[2.4728843626666666,2.468990816],new_log_directory='sim/mini_board_migration/board/coremark_i64_d64_zmmul_sfwd_300_01',
        software_sha256=r['software_sha256'],PDS_or_bitstream_review_required=False,serial_opened=False))
    print('FROZEN',len(files),'+10 /11 snapshots /36 modules; SHA',sha(MANIFEST),'BRIDGE',sha(ROOT/bridge))
if __name__=='__main__':main()
