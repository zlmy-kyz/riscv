"""Freeze Task025 inputs and future same-BIN board plan; software/static only."""
from pathlib import Path
import ast
import json
from run_data_write_hit import ROOT,HERE,MANIFEST,TAG,sha,write


def main():
    assert not MANIFEST.exists()
    old=json.loads((HERE/'data_drm64_inputs.json').read_text(encoding='utf-8'))
    receipt=json.loads((ROOT/'sim/cpu_zmmul/build/preparation_20261013_a/pds_review_20261013/receipt.json').read_text(encoding='utf-8'))
    files=set(receipt['registered_input_sha256']);files.add('RISCV.pds')
    extra=['sim/mini_board_migration/'+n for n in ['run_data_write_hit.py','review_data_write_hit.py','prepare_data_write_hit.py',
           'tb_data_write_hit_x32.sv','tb_data_drm64_x32.sv','resume_inst_drm64.py','resume_inst_cache32.py','run_inst_drm64.py']]
    baseline='sim/mini_board_migration/build/data_write_hit_preparation_20261013_a/dual_sram_to_pango_ddr_bridge_before.v'
    extra += [baseline,'tools/uart_loader/candidates/perf_2b/run_data_write_hit_measurement.py',
              'tools/uart_loader/candidates/perf_2b/run_data_write_hit_measurements.ps1',
              'tools/uart_loader/candidates/perf_2b/run_zmmul300_measurement.py',
              'tools/uart_loader/candidates/perf_2b/run_measurement.py','tests/cpu_performance_2b/zmmul300_software.py',
              'tests/cpu_performance_2b/zmmul_software.py','tests/cpu_performance_2b/measurement_software.py',
              'tools/uart_loader/candidates/bsp_workflow/upload.py','tools/uart_loader/candidates/bsp_workflow/application.py',
              'tools/uart_loader/candidates/bsp_workflow/plan.py','tests/uart_loader/candidates/verify_run_hello/image_to_dat.py']
    files.update(extra)
    for folder in ['tests/cpu_performance_2b/build/measure_zmmul300_20261013_a','sim/cpu_zmmul/board/coremark_i64_d64_zmmul_300_01']:
        files.update(p.relative_to(ROOT).as_posix() for p in (ROOT/folder).rglob('*') if p.is_file())
    for p in (ROOT/'ipcore/dcache/rtl').rglob('*.v'):files.add(p.relative_to(ROOT).as_posix())
    external=set(old['external_tool_sha256'])|set(old['external_reference_sha256'])|set(old['vendor_sha256'])
    groups=[('full_fill_byte_enable',512),('masked_hit_all_lanes',384),('no_allocate_tag_conflict',8),
            ('write_completion_and_backpressure',16),('instruction_invalidation_and_zero_mask',12),
            ('reset_before_aw_during_w_after_write',9),('initialization_loss',4)]
    compile_sources=['ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v','ipcore/dcache/rtl/ipm2l_sdpram_v1_10_dcache.v',
                     'ipcore/icache/icache.v','ipcore/dcache/dcache.v','myriscv/dual_sram_to_pango_ddr_bridge.v',
                     'sim/mini_board_migration/tb_data_write_hit_x32.sv']
    snapshots=[n for n in extra if n.endswith(('run_data_write_hit.py','review_data_write_hit.py','prepare_data_write_hit.py',
               'tb_data_write_hit_x32.sv','run_data_write_hit_measurement.py','run_data_write_hit_measurements.ps1'))]+[
               'myriscv/dual_sram_to_pango_ddr_bridge.v','ipcore/dcache/dcache.v','ipcore/dcache/dcache.idf',
               'ipcore/dcache/rtl/ipm2l_sdpram_v1_10_dcache.v']
    m=dict(status='DATA_WRITE_HIT_PREPARED_HDL_NOT_RUN',sha256={n:sha(ROOT/n) for n in sorted(files)},
           external_sha256={n:sha(n) for n in sorted(external)},compile_sources=compile_sources,snapshot_files=snapshots,
           groups=[dict(name=n,checks=c) for n,c in groups],expected_checks=945,cpu_changed=False,baseline_bridge=baseline,
           dcache_parameters={'WR_BYTE_EN':'true','BE_WIDTH':'32','BYTE_SIZE':'8','WR_DATA_WIDTH':'256','WR_ADDR_WIDTH':'6',
           'RD_DATA_WIDTH':'32','RD_ADDR_WIDTH':'9','OUTPUT_REG':'false','FAB_REG':'false','RESET_TYPE':'SYNC',
           'WR_ADDR_STROBE_EN':'false','RD_ADDR_STROBE_EN':'false','INIT_FILE':'NONE','POWER_OPT':'false'},
           fixed_tag=TAG,timeouts={'vlib':60,'compile':60,'simulation':180},
           scope='x32 real I/D DRM write-hit group, unchanged DDR controller/model; x16 static only; no CPU ISA/SoC execution/PHY/board')
    for n in extra:
        if n.endswith('.py'):ast.parse((ROOT/n).read_text(encoding='utf-8'))
    write(MANIFEST,m)
    print('FROZEN',len(files),len(external),'snapshots',len(snapshots),'SHA',sha(MANIFEST),
          'BRIDGE',sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'))


if __name__=='__main__':main()
