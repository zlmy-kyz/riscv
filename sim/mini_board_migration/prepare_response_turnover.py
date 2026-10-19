"""One-time static preparation of Task026; never invokes simulator/PDS/serial."""
from pathlib import Path
import ast
import json
import sys
from generate_response_turnover_tb import build_tb
from run_response_turnover import ROOT,HERE,MANIFEST,TAG,sha,write


def main():
    assert not MANIFEST.exists()
    tb=HERE/'tb_response_turnover_x32.sv'
    if tb.exists():assert tb.read_text(encoding='utf-8')==build_tb()
    else:tb.write_text(build_tb(),encoding='utf-8')
    sys.path.insert(0,str(ROOT/'difftest/golden'))
    from rvtool import Assembler,disasm
    asm=Assembler();program=asm.assemble((HERE/'response_turnover_cpu.S').read_text(encoding='utf-8'))
    assert sorted(program)==list(range(0,60,4)) and asm.sym['loop']==20 and asm.sym['done']==56
    prep=HERE/'build/response_turnover_preparation_20261013_a'
    image=prep/'cpu_program.hex'
    image_text=''.join(f'{program[n]:08x}\n' for n in range(0,60,4))
    if image.exists():assert image.read_text(encoding='ascii')==image_text
    else:image.write_text(image_text,encoding='ascii')
    listing=prep/'cpu_program.lst'
    listing_text='\n'.join(f'{n:08x} {program[n]:08x} {disasm(program[n],n,{})}' for n in program)+'\n'
    if listing.exists():assert listing.read_text(encoding='utf-8')==listing_text
    else:listing.write_text(listing_text,encoding='utf-8')
    baseline=(ROOT/'sim/mini_board_migration/build/data_write_hit_preparation_20261013_a/pds_handoff.json')
    previous=json.loads(baseline.read_text(encoding='utf-8'))
    changed='myriscv/dual_sram_to_pango_ddr_bridge.v'
    for n,h in previous['source_sha256'].items():
        if n!=changed:assert sha(ROOT/n)==h,n
    source_sha256={n:sha(ROOT/n) for n in previous['source_sha256']}
    sw=ROOT/'tests/cpu_performance_2b/build/measure_zmmul300_20261013_a'
    software_sha256={p.relative_to(ROOT).as_posix():sha(p) for p in sw.rglob('*')
                     if p.is_file() and p.name in ('program.bin','program.elf','manifest.json','reference.txt')}
    assert len(software_sha256)==8
    prefix='sim/mini_board_migration/'
    new_files=[prefix+n for n in ('run_response_turnover.py','review_response_turnover.py',
        'prepare_response_turnover.py','generate_response_turnover_tb.py','tb_response_turnover_x32.sv',
        'response_turnover_cpu_mux.svh','response_turnover_cases.svh','response_turnover_cpu.S')]
    new_files += [image.relative_to(ROOT).as_posix(),listing.relative_to(ROOT).as_posix(),
        'tools/uart_loader/candidates/perf_2b/run_response_turnover_measurement.py',
        'tools/uart_loader/candidates/perf_2b/run_response_turnover_measurements.ps1']
    old_files=[prefix+n for n in ('resume_inst_drm64.py','resume_inst_cache32.py','run_inst_drm64.py',
        'run_inst_cache32.py','tb_data_write_hit_x32.sv','review_data_write_hit_board.py')]
    old_files += ['tools/uart_loader/candidates/perf_2b/run_zmmul300_measurement.py',
        'tools/uart_loader/candidates/perf_2b/run_measurement.py','tests/cpu_performance_2b/zmmul300_software.py',
        'tests/cpu_performance_2b/zmmul_software.py','tests/cpu_performance_2b/measurement_software.py',
        'tools/uart_loader/candidates/bsp_workflow/upload.py','tools/uart_loader/candidates/bsp_workflow/application.py',
        'tools/uart_loader/candidates/bsp_workflow/plan.py','tests/uart_loader/candidates/verify_run_hello/image_to_dat.py',
        'difftest/golden/rvtool.py']
    old_inputs=json.loads((HERE/'data_write_hit_inputs.json').read_text(encoding='utf-8'))
    external={n:sha(n) for n in old_inputs['external_sha256']}
    from run_response_turnover import VENDOR
    external[str(VENDOR/'GTP_APM_E2.v')]=sha(VENDOR/'GTP_APM_E2.v')
    baseline_bridge=(prep/'dual_sram_to_pango_ddr_bridge_before.v').relative_to(ROOT).as_posix()
    files=set(source_sha256)|set(software_sha256)|set(new_files)|set(old_files)|{baseline_bridge}
    board=ROOT/'sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01'
    for p in board.rglob('*.json'):files.add(p.relative_to(ROOT).as_posix())
    cpu_inputs=json.loads((ROOT/'sim/cpu_zmmul/inputs.json').read_text(encoding='utf-8'))
    cpu_sources=[n for n in cpu_inputs['compile_sources'] if n.endswith('.v')]
    sources=['ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v','ipcore/dcache/rtl/ipm2l_sdpram_v1_10_dcache.v',
             'ipcore/icache/icache.v','ipcore/dcache/dcache.v',*cpu_sources,changed,prefix+'tb_response_turnover_x32.sv']
    assert len(sources)==17
    snapshots=new_files+[changed,'myriscv/mycpu_sync.v','ipcore/icache/icache.v','ipcore/dcache/dcache.v',baseline_bridge]
    groups=[('instruction_hit_stream',576),('data_hit_stream',576),('alternating_response_owner',128),
            ('write_hit_turnover_ordering',128),('read_miss_turnover',24),('reset_and_initialization',8),('real_cpu_ddr_loop',392)]
    m=dict(status='RESPONSE_TURNOVER_PREPARED_HDL_NOT_RUN',fixed_tag=TAG,
        sha256={n:sha(ROOT/n) for n in sorted(files)},external_sha256=external,
        source_sha256=source_sha256,software_sha256=software_sha256,compile_sources=sources,
        vendor_compile_sources=['GTP_GRS.v','GTP_DRM36K_E1.v','GTP_APM_E2.v'],snapshot_files=snapshots,
        baseline_bridge=baseline_bridge,cpu_image=image.relative_to(ROOT).as_posix(),
        groups=[dict(name=n,checks=c) for n,c in groups],expected_checks=1832,cpu_changed=False,
        timeouts={'vlib':60,'compile':60,'simulation':180},
        scope='x32 real I/D DRM manual turnover + real CPU/bridge DDR user-port loop; no SoC MMIO/Loader/PHY/PDS/board, x16 static only')
    for n in new_files+old_files:
        if n.endswith('.py'):ast.parse((ROOT/n).read_text(encoding='utf-8'))
    write(MANIFEST,m)
    write(prep/'static_review.json',dict(status='RESPONSE_TURNOVER_STATIC_PREPARATION_PASS_HDL_NOT_RUN',
        manifest_sha256=sha(MANIFEST),bridge_sha256=sha(ROOT/changed),CPU_sha256=sha(ROOT/'myriscv/mycpu_sync.v'),
        protected_inputs=len(files),external_inputs=len(external),snapshot_files=len(snapshots),expected_checks=1832,
        HDL_started=False,PDS_started=False,serial_opened=False,
        board_baseline='sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01',
        cpu_program={'words':15,'expected_retirements':392,'loads':64,'stores':66,'data_AR':1,'final_words':[64,2080,1]},
        scope=m['scope']))
    write(prep/'board_plan.json',dict(status='RESPONSE_TURNOVER_BOARD_PREPARED_NOT_RUN',
        modes=['performance_300','validation_300'],iterations=300,port='COM9',baud=115200,
        new_log_directory='sim/mini_board_migration/board/coremark_i64_d64_zmmul_turnover_300_01',
        baseline={'performance_cycles':395967938,'validation_cycles':395398048,
                  'directory':'sim/mini_board_migration/board/coremark_i64_d64_zmmul_dwh_300_01'},
        software_sha256=software_sha256,responses_per_mode=123,RUN_per_mode=1,
        functional_review_required=True,PDS_or_bitstream_review_required=False,serial_opened=False,
        user_operations=['Generate and download new design','Close other serial software',
                         'KEY0 release, wait DDR, then Enter per mode','P300 and V300 once each']))
    print('FROZEN inputs',len(files),'external',len(external),'snapshots',len(snapshots),'SHA',sha(MANIFEST))


if __name__=='__main__':main()
