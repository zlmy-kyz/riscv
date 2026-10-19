"""Freeze Task028 static preparation. HDL is executed only by DeepSeek."""
import ast,difflib,inspect,json,re,sys
from pathlib import Path
from run_data_read_overlap import ROOT,HERE,MANIFEST,TAG,VENDOR,sha,read,write
from generate_data_read_overlap_tb import build_tb
from prepare_write_buffer import offline_program
from prepare_write_buffer_soc_resume import corrected_program_check
PREP=HERE/'build/read_hit_under_write_preparation_20261013_a'
def main():
    assert not MANIFEST.exists() and not (HERE/'build'/TAG).exists()
    receipt_path=HERE/'build/ds_mini_write_buffer_soc_resume_20261013_a/codex_review.json'
    r=json.loads(read(receipt_path));bridge='myriscv/dual_sram_to_pango_ddr_bridge.v'
    assert {n for n,h in r['source_sha256'].items() if sha(ROOT/n)!=h}=={bridge}
    assert sha(PREP/'before'/bridge)==r['source_sha256'][bridge]
    for n,h in r['software_sha256'].items():assert sha(ROOT/n)==h
    old=json.loads(read(HERE/'write_buffer_soc_resume_inputs.json'))
    program_source=read(HERE/'write_buffer_soc_resume.S')
    program_source=program_source.replace('    lui x10, 0x10000\n    addi x11, x0, 3\n',
        '    addi x7, x1, 32\n    lw x8, 0(x7) # Preload an independent D-cache line\n    lui x10, 0x10000\n    addi x11, x0, 3\n',1)
    program_source=program_source.replace('    sw x5, 0(x1)\n',
        '    sw x5, 0(x1)\n    lw x8, 0(x7) # Hit this other line while the store drains\n',1)
    source=HERE/'data_read_overlap_soc.S';assert not source.exists();source.write_text(program_source,encoding='utf-8')
    sys.path.insert(0,str(ROOT/'difftest/golden'));from rvtool import Assembler
    asm=Assembler();program=asm.assemble(program_source)
    assert len(program)==39 and asm.sym=={'loop':72,'pass_store':140,'done':144,'handler':256}
    # Same independent architectural arithmetic/MMIO oracle, with explicit added loads.
    checker=inspect.getsource(corrected_program_check).replace("'total==414 and test_status==2'","'total==480 and test_status==2'")
    checker=checker.replace('namespace={};exec(',"text=text.replace('loads==64','loads==129',1)\n    namespace={};exec(",1)
    namespace=dict(inspect=inspect,offline_program=offline_program)
    exec(compile(checker,'<static_Task028_program_oracle>','exec'),namespace)
    program_review=namespace['corrected_program_check'](program)
    image=PREP/'soc_program.hex';assert not image.exists()
    image.write_text(''.join(f'{program.get(a,0):08x}\n' for a in range(0,4096,4)),encoding='ascii')
    tb=HERE/'tb_data_read_overlap_x32.sv';assert not tb.exists();tb.write_text(build_tb(),encoding='utf-8')
    sources=[n for n in old['compile_sources'] if not n.endswith('tb_write_buffer_isa.sv')]
    sources=[n.replace('tb_write_buffer_soc_resume.sv','tb_data_read_overlap_x32.sv') for n in sources]
    modules=[name for p in [*[VENDOR/n for n in old['vendor_compile_sources']],*[ROOT/n for n in sources]]
        for name in re.findall(r'^\s*module\s+(\w+)',read(p),re.M)]
    assert len(modules)==36 and len(set(modules))==36
    new=['sim/mini_board_migration/'+n for n in ['generate_data_read_overlap_tb.py','data_read_overlap_cases.svh',
        'data_read_overlap_soc.S','tb_data_read_overlap_x32.sv','run_data_read_overlap.py','review_data_read_overlap.py',
        'prepare_data_read_overlap.py']]
    new+=['tools/uart_loader/candidates/perf_2b/run_data_read_overlap_measurement.py',
        'tools/uart_loader/candidates/perf_2b/run_data_read_overlap_measurements.ps1',image.relative_to(ROOT).as_posix()]
    files=set(old['sha256'])|set(new)|{receipt_path.relative_to(ROOT).as_posix(),
        'sim/mini_board_migration/write_buffer_soc_resume_inputs.json',
        (PREP/'before'/bridge).relative_to(ROOT).as_posix()}
    for p in (HERE/'board/coremark_i64_d64_zmmul_wbuf_300_01').rglob('*.json'):files.add(p.relative_to(ROOT).as_posix())
    for n in new:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    groups=[('qualification_priority_turnover',8),('all_rows_words_mask_overlap',704),
        ('same_line_all_byte_masks_order',385),('alias_miss_and_full_store_order',11),
        ('reset_and_init_qualification_clear',9),('real_soc_read_overlap_fence_irq_stop',480)]
    assert sum(v for _,v in groups)==1597
    source_hashes={n:sha(ROOT/n) for n in r['source_sha256']}
    m=dict(status='DATA_READ_OVERLAP_PREPARED_HDL_NOT_RUN',fixed_tag=TAG,
        sha256={n:sha(ROOT/n) for n in sorted(files)},external_sha256=old['external_sha256'],
        source_sha256=source_hashes,software_sha256=r['software_sha256'],compile_sources=sources,
        vendor_compile_sources=old['vendor_compile_sources'],expected_modules=modules,snapshot_files=new+[bridge],
        cpu_image=image.relative_to(ROOT).as_posix(),groups=[dict(name=n,checks=v) for n,v in groups],
        expected_checks=1597,control_checks=8,CPU_changed=False,ISA_samples=[],
        scope='x32 registered other-line D-hit overlap; 64 rows/8 words/masks/order/qualification reset + real SoC480; x16 static only; no PHY/PDS/board')
    write(MANIFEST,m)
    before=read(PREP/'before'/bridge);after=read(ROOT/bridge)
    (PREP/'bridge.patch').write_text(''.join(difflib.unified_diff(before.splitlines(True),after.splitlines(True),
        fromfile='before/'+bridge,tofile=bridge)),encoding='utf-8')
    write(PREP/'static_review.json',dict(status='DATA_READ_OVERLAP_STATIC_PREPARATION_PASS_HDL_NOT_RUN',
        manifest_sha256=sha(MANIFEST),bridge_sha256=sha(ROOT/bridge),previous_bridge_sha256=sha(PREP/'before'/bridge),
        inputs=len(files),external_inputs=len(m['external_sha256']),snapshot_files=len(m['snapshot_files']),design_modules=36,
        changed_registered_sources=[bridge],unchanged_registered_sources=136,CPU_changed=False,ISA_samples=[],
        CPU_program=program_review,key_checks=1597,control_checks=8,manual_early_D_hits=514,
        HDL_started=False,PDS_started=False,serial_opened=False))
    write(PREP/'board_plan.json',dict(status='DATA_READ_OVERLAP_BOARD_PREPARED_NOT_RUN',iterations=300,port='COM9',
        baseline='sim/mini_board_migration/board/coremark_i64_d64_zmmul_wbuf_300_01',baseline_cycles=[250107028,249687374],
        modes=['performance_300','validation_300'],new_log_directory='sim/mini_board_migration/board/coremark_i64_d64_zmmul_dread_300_01',
        software_sha256=r['software_sha256'],PDS_or_bitstream_review_required=False,serial_opened=False))
    print('STATIC FROZEN',len(files),'+',len(m['external_sha256']),'snapshots',len(m['snapshot_files']),
        'modules36 key1597 CPU480 SHA',sha(MANIFEST),'BRIDGE',sha(ROOT/bridge))
if __name__=='__main__':main()
