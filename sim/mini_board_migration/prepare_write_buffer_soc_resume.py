"""Static repair and continuation preparation; no simulator, PDS or serial operation."""
import ast,inspect,json,re,sys
from pathlib import Path
import run_write_buffer as original
from run_write_buffer_soc_resume import ROOT,HERE,TAG,MANIFEST,sha,read,write
from generate_write_buffer_soc_resume_tb import build_resume_tb
from prepare_write_buffer import offline_program
PREP=HERE/'build/write_buffer_soc_resume_preparation_20261013_a'

def corrected_program_check(program):
    # Retain the original arithmetic oracle and explicitly add the MMIO RUN contract.
    text=inspect.getsource(offline_program)
    text=text.replace('loads=0;perf=0','loads=0;perf=0;test_status=0',1)
    text=text.replace('else:assert address==0x10000010 and regs[rs2]==2 and perf==2',
        '''else:
                assert address==0x10000010
                if regs[rs2]==1:assert test_status==0 and perf==1;test_status=1
                else:assert regs[rs2]==2 and test_status==1 and perf==2;test_status=2''',1)
    text=text.replace('if address==0x10000010:break','if address==0x10000010 and test_status==2:break',1)
    text=text.replace('total==413','total==414 and test_status==2',1)
    namespace={};exec(compile(text,'<static_corrected_program_oracle>','exec'),namespace)
    return namespace['offline_program'](program)

def main():
    old=original.require_inputs();assert not MANIFEST.exists() and not (HERE/'build'/TAG).exists()
    failure_path=PREP/'failure_review.json';failure=json.loads(read(failure_path))
    for n,h in failure['old_artifact_sha256'].items():assert sha(ROOT/n)==h,n
    assert failure['source_sha256']==old['source_sha256'] and failure['software_sha256']==old['software_sha256']
    src=read(HERE/'write_buffer_soc.S');anchor='    lui x10, 0x10000\n    addi x11, x0, 4\n'
    assert src.count(anchor)==1
    fixed=src.replace(anchor,'    lui x10, 0x10000\n    sw x6, 16(x10) # TEST_STATUS RUN before PASS\n    addi x11, x0, 4\n',1)
    fixed_source=HERE/'write_buffer_soc_resume.S';assert not fixed_source.exists();fixed_source.write_text(fixed,encoding='utf-8')
    sys.path.insert(0,str(ROOT/'difftest/golden'));from rvtool import Assembler
    asm=Assembler();program=asm.assemble(fixed);review=corrected_program_check(program)
    assert len(program)==36 and asm.sym=={'loop':64,'pass_store':128,'done':132,'handler':256}
    # The faulting original program writes TEST_STATUS=2 while IDLE; the main RTL rejects it.
    mmio=read(ROOT/'myriscv/simple_mmio.v')
    assert "else if (test_status == 2'd0)" in mmio and "response_error <= 1'b1;" in mmio
    cpu=read(ROOT/'myriscv/mycpu_sync.v')
    assert 'RV_EXC_STORE_ACCESS_FAULT' in cpu
    image=PREP/'soc_program.hex';assert not image.exists()
    image.write_text(''.join(f'{program.get(a,0):08x}\n' for a in range(0,4096,4)),encoding='ascii')
    tb=HERE/'tb_write_buffer_soc_resume.sv';assert not tb.exists();tb.write_text(build_resume_tb(),encoding='utf-8')
    assert 'init_done=1;soc_mode=1' in read(tb)
    sources=[n.replace('tb_write_buffer_x32.sv','tb_write_buffer_soc_resume.sv') for n in old['compile_sources']]
    modules=[name for p in [*[original.VENDOR/n for n in old['vendor_compile_sources']],*[ROOT/n for n in sources]]
        for name in re.findall(r'^\s*module\s+(\w+)',read(p),re.M)]
    assert len(modules)==37 and len(set(modules))==37
    new=['sim/mini_board_migration/'+n for n in ['generate_write_buffer_soc_resume_tb.py',
        'prepare_write_buffer_soc_resume.py','run_write_buffer_soc_resume.py','review_write_buffer_soc_resume.py',
        'write_buffer_soc_resume.S','tb_write_buffer_soc_resume.sv']]
    new += ['tools/uart_loader/candidates/perf_2b/run_write_buffer_soc_resume_measurement.py',
        'tools/uart_loader/candidates/perf_2b/run_write_buffer_soc_resume_measurements.ps1',image.relative_to(ROOT).as_posix()]
    files=set(old['sha256'])|set(failure['old_artifact_sha256'])|set(new)|{
        failure_path.relative_to(ROOT).as_posix(),'sim/mini_board_migration/write_buffer_inputs.json',
        'sim/mini_board_migration/review_write_buffer_failure.py'}
    for n in new:
        if n.endswith('.py'):ast.parse(read(ROOT/n))
    snapshots=new+[n for n in old['snapshot_files'] if n.startswith('myriscv/')]
    m=dict(status='WRITE_BUFFER_SOC_REPAIR_PREPARED_HDL_NOT_RUN',fixed_tag=TAG,
        sha256={n:sha(ROOT/n) for n in sorted(files)},external_sha256=old['external_sha256'],
        source_sha256=old['source_sha256'],software_sha256=old['software_sha256'],
        original_manifest_sha256=sha(original.MANIFEST),failure_review=failure_path.relative_to(ROOT).as_posix(),
        compile_sources=sources,vendor_compile_sources=old['vendor_compile_sources'],expected_modules=modules,
        snapshot_files=snapshots,cpu_image=image.relative_to(ROOT).as_posix(),old_cpu_image=old['cpu_image'],
        isa_jobs=old['isa_jobs'],isa_seed=old['isa_seed'],expected_checks=414,
        reused_control_checks=8,reused_front_key_checks=426,aggregate_key_checks=840,
        scope='x32 one-entry buffer; repaired TEST_STATUS RUN/PASS SoC414, precise old-program cause7 reproduction, two pending ISA; no x16 HDL/PHY/PDS/board')
    write(MANIFEST,m)
    write(PREP/'static_review.json',dict(status='WRITE_BUFFER_SOC_PROGRAM_REPAIR_STATIC_PASS_HDL_NOT_RUN',
        manifest_sha256=sha(MANIFEST),inputs=len(files),external_inputs=len(m['external_sha256']),
        snapshot_files=len(snapshots),design_modules=37,CPU_program=review,
        source_software_unchanged_since_failed_task=True,program_change='Exactly one sw x6,16(x10) for TEST_STATUS RUN',
        original_cause='Static predicted store access fault; original log cause not recorded; precise reproduction pending',
        reuse='control8/front426; only unfinished SoC plus pending ISA',old_raw_files=len(failure['old_artifact_sha256']),
        HDL_started=False,PDS_started=False,serial_opened=False))
    print('STATIC PREPARED',len(files),'+',len(m['external_sha256']),'snapshots',len(snapshots),'SHA',sha(MANIFEST))
if __name__=='__main__':main()
