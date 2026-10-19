"""One-time static I64 preparation; preserve I32/D32 success, do not run HDL/PDS."""
from pathlib import Path
import difflib
import hashlib
import json
from run_inst_drm64 import HERE, ROOT, MANIFEST, project_identity, planned_counts, require_inputs

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
prep=HERE/'build/inst_drm64_preparation_20261013_a';prep.mkdir(exist_ok=False)
BASE=HERE/'build/data_drm32_preparation_20261012_a'
pds=json.loads((BASE/'pds_review.json').read_text(encoding='utf-8'))
board=json.loads((BASE/'board_review.json').read_text(encoding='utf-8'))
assert pds['status']=='MINI_DATA_DRM32_PDS_EVIDENCE_REVIEW_PASS'
assert board['status']=='MINI_DATA_DRM32_ACTUAL_DDR_FIXED120_REVIEW_PASS'
old=HERE/'build/ds_mini_ddrm32_20261012_185339/dual_sram_to_pango_ddr_bridge.v'
assert sha(old)=='918efab77d6e00d609529599d13be6b6b004c34199692c2ca8556c2e04525851'
for path,h in pds['registered_input_sha256'].items():
    if path!='myriscv/dual_sram_to_pango_ddr_bridge.v':assert sha(ROOT/path)==h,path
for path,item in pds['evidence'].items():assert sha(BASE/'pds_evidence'/path)==item['sha256']
assert all(sha(ROOT/p)==h for p,h in board['raw_log_sha256'].items())

tb=(HERE/'tb_data_drm32_x32.sv').read_text(encoding='utf-8')
tb=tb.replace('module tb_data_drm32_x32;','module tb_inst_drm64_x32;',1)
tb=tb.replace('production RTL fixes I32/D32','production RTL fixes I64/D32')
tb=tb.replace('localparam integer I_LINES = 32;','localparam integer I_LINES = 64;')
tb=tb.replace('// Same per-line oracle as the successful tests; extra backing rows cover\n'
              '    // I32 reset/independence addresses 0x800..0xbff. No timing-model change.',
              '// Existing 128 backing rows cover all I64 addresses 0x000..0xfff.\n'
              '    // Keep the successful DDR timing model and transfer oracle.')
# Upper I63 accepted miss: incoming IA changes, queued matching or alias-tag store.
a=tb.index('    task automatic queued_inst_fill(');b=tb.index('    endtask',a)+len('    endtask')
body=tb[a:b]
body=body.replace("'h3ec","'h7ec").replace("same_row_write ? 'h3e4 : 'h7e4","same_row_write ? 'h7e4 : 'hfe4")
body=body.replace("fetch('h3e4","fetch('h7e4").replace("fetch('h3ec","fetch('h7ec")
tb=tb[:a]+body+tb[b:]
tb=tb.replace("wr_addr !== {1'b0,dut.request_line_tag[4:0]}","wr_addr !== dut.request_line_tag[5:0]",1)
tb=tb.replace("rd_addr !== {1'b0,ia[9:2]}","rd_addr !== ia[10:2]")
tb=tb.replace('DRM address mapping/unused upper half','I64 DRM full-capacity address mapping')
a=tb.index('    task automatic reset_during_hit;');b=tb.index('    endtask',a)+len('    endtask')
body=tb[a:b].replace("'hbfc","'hffc").replace("'hbe4","'hfe4")
tb=tb[:a]+body+tb[b:]
start=tb.index('    initial begin : run_tests')
main=tb[start:]
main=main.replace('// All 32 I rows and eight words; I16 would evict the lower half.',
                  '// All 64 I rows and eight words; I32 would alias the upper half.')
main=main.replace("fetch('h400,1);fetch('h200,0);fetch(0,1);fetch('h400,1);fetch('h200,0);",
                  "fetch('h800,1);fetch('h400,0);fetch(0,1);fetch('h800,1);fetch('h400,0);")
main=main.replace('thirtytwo_rows_slots_512_split_1024_conflict','sixtyfour_rows_slots_1024_split_2048_conflict')
a=main.index('        cold();\n        for (k=0;k<I_LINES;',main.index('sixtyfour_rows_slots'))
b=main.index('$display("CHECK: upper_I31',a)
section=main[a:b]
for before,after in [("'h7e4","'hfe4"),("'h3e0","'h7e0"),("'h3e4","'h7e4"),("'h3fc","'h7fc"),
                     ("'h3e5","'h7e5"),("'h3fa","'h7fa")]:section=section.replace(before,after)
main=main[:a]+section+main[b:]
main=main.replace('upper_I31_full_tag_partial_zero_write_I_D_invalidation','upper_I63_full_tag_partial_zero_write_I_D_invalidation')
main=main.replace('independent_D32_locked_upper_I31_fill_data_priority','independent_D32_locked_upper_I63_fill_data_priority')
a=main.index('        cold();\n        for (k=0;k<I_LINES;',main.index('independent_D32_locked'))
b=main.index('$display("CHECK: same_cycle',a)
section=main[a:b].replace("'h7fc","'hffc").replace("'h7f8","'hff8").replace("'h3fc","'h7fc").replace('k<31;','k<63;')
main=main[:a]+section+main[b:]
main=main.replace('same_cycle_bad_ID_last_idle_preserve_upper_I31_victim','same_cycle_bad_ID_last_idle_preserve_upper_I63_victim')
main=main.replace('// Warm I31 is 0xbe0; 0x7e0 is a different full tag at the same index.',
                  '// Warm I63 is 0xfe0; 0x7e0 is a different full tag at the same index.')
main=main.replace('readiness_reset_clear_I32_D32_cancel_pending_IF','readiness_reset_clear_I64_D32_cancel_pending_IF')
main=main.replace('// New synchronous RAM checks use the warm 0x800..0xbff I32 from above.',
                  '// Synchronous RAM checks use all warm 0x800..0xfff I64 rows.')
main=main.replace('(31-k)*32+((lane+3)%8)*4);\n            end\n        end\n        reset_during_hit();',
                  '(63-k)*32+((lane+3)%8)*4);\n            end\n        end\n        reset_during_hit();')
main=main.replace('if (tests!=1521)','if (tests!=2449)').replace('expected=1521','expected=2449').replace('PASS data_drm32_x32','PASS inst_drm64_x32')
tb=tb[:start]+main
(HERE/'tb_inst_drm64_x32.sv').write_text(tb,encoding='utf-8')
assert 'memory[0:127]' in tb and "fetch('hffc" in tb

previous=json.loads((HERE/'data_drm32_inputs.json').read_text(encoding='utf-8'))
paths=set(pds['registered_input_sha256'])|set(pds['fixed_software_sha256'])
paths.update([
    str(old.relative_to(ROOT)).replace('\\','/'),
    'sim/mini_board_migration/run_inst_drm64.py','sim/mini_board_migration/prepare_inst_drm64.py',
    'sim/mini_board_migration/tb_inst_drm64_x32.sv','sim/mini_board_migration/tb_data_drm32_x32.sv',
    'sim/mini_board_migration/resume_inst_cache32.py','sim/mini_board_migration/run_data_drm32.py',
    'sim/mini_board_migration/data_drm32_inputs.json',
    'sim/mini_board_migration/build/ds_mini_ddrm32_20261012_185339/codex_review.json',
    'sim/mini_board_migration/build/data_drm32_preparation_20261012_a/pds_review.json',
    'sim/mini_board_migration/build/data_drm32_preparation_20261012_a/board_review.json'])
paths.update(board['raw_log_sha256'])
paths.update(str((BASE/'pds_evidence'/p).relative_to(ROOT)).replace('\\','/') for p in pds['evidence'])
# IP generated init/reset helpers are retained even though init is disabled.
paths.update(str(p.relative_to(ROOT)).replace('\\','/') for name in ['icache','dcache']
             for p in (ROOT/f'ipcore/{name}/rtl').glob('*.v'))
m=dict(status='MINI_INST_DRM64_PREPARED_HDL_NOT_RUN',baseline_bridge=str(old.relative_to(ROOT)).replace('\\','/'),
    baseline_board_directory='sim/mini_board_migration/board/coremark_idrm_d32_01',
    baseline_bitstream_sha256=pds['bitstream_sha256'],candidate_bridge_sha256=sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'),
    expected_checks=2449,unit_plan=planned_counts(),isa_cases=[],vendor_sha256=previous['vendor_sha256'],
    ip_configuration=previous['ip_configuration'],project_configuration_sha256=project_identity((ROOT/'RISCV.pds').read_text()),
    sha256={p:sha(ROOT/p) for p in sorted(paths)})
MANIFEST.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
require_inputs()
(prep/'rtl_change.patch').write_text(''.join(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),
    (ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8').splitlines(True),
    fromfile='successful_I32_D32_DRM',tofile='myriscv/dual_sram_to_pango_ddr_bridge.v')),encoding='utf-8')
r=dict(status='MINI_INST_DRM64_STATIC_PREPARATION_PASS_HDL_NOT_RUN',input_manifest_sha256=sha(MANIFEST),
    protected_inputs=len(paths),vendor_models=2,candidate_bridge_sha256=m['candidate_bridge_sha256'],
    expected_checks=2449,unit_plan=m['unit_plan'],scope='I32 to I64 only; D32/FSM/response/CPU/IP/PDS/clock/software unchanged',
    I_capacity_bytes=2048,D_capacity_bytes=1024,IP_regenerated=False,PDS_modified=False,
    HDL='NOT_RUN',PDS='NOT_RUN',board='NOT_TESTED')
(prep/'preparation.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(r,indent=2,ensure_ascii=False))
