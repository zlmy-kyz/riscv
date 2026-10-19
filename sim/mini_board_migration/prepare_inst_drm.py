"""One-time static Task019 preparation. Does not execute HDL/PDS/serial."""
from pathlib import Path
import difflib
import hashlib
import json
import re
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE))
from resume_inst_cache32 import project_configuration
from run_inst_drm import planned_counts, VENDOR

sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
PREP = HERE / 'build/inst_drm_preparation_20261012_a'
PREP.mkdir(exist_ok=False)
BASE = HERE / 'build/inst_cache32_preparation_20261012_a'
old_bridge = HERE / 'build/ds_mini_i32_resume_20261012_170046/dual_sram_to_pango_ddr_bridge.v'
assert sha(old_bridge) == '78c624e8eb8a7ea1ad0fd8186873c5ba17f4e98d7623bce83006e5336bdccb34'
baseline = json.loads((BASE / 'pds_review.json').read_text(encoding='utf-8'))
for name, digest in baseline['registered_input_sha256'].items():
    if name != 'myriscv/dual_sram_to_pango_ddr_bridge.v':
        assert sha(ROOT / name) == digest, name

old_tb = (HERE / 'tb_inst_cache32_x32.sv').read_text(encoding='utf-8')
new_tb = old_tb.replace('module tb_inst_cache32_x32;',
    'module tb_inst_drm_x32;\n    GTP_GRS GRS_INST (.GRS_N(1\'b1));', 1)
extra = r'''    // DRM-specific checks: real primitive synchronous address capture, not a RAM stub.
    integer fill_writes=0;
    always @(posedge clk) begin
        if (!resetn) fill_writes<=0;
        else if (dut.g_inst_drm.u_inst_data_ram.wr_en) fill_writes<=fill_writes+1;
        if (dut.g_inst_drm.u_inst_data_ram.wr_en !== (resetn && init_done && dut.inst_line_fill))
            $fatal(1,"RESULT: FAIL DRM fill write qualification");
        if (dut.g_inst_drm.u_inst_data_ram.wr_addr !== {1'b0,dut.request_line_tag[4:0]} ||
            dut.g_inst_drm.u_inst_data_ram.rd_addr !== {1'b0,ia[9:2]})
            $fatal(1,"RESULT: FAIL DRM address mapping/unused upper half");
    end

    task automatic sync_hit_address_change(input [31:0] address, input [31:0] poison);
        integer old_ar;
        reg [31:0] expected;
        begin
            expected=word_at(address);
            @(negedge clk);old_ar=ar_count;iv=1;ia=address;
            #1;if (!ir) $fatal(1,"RESULT: FAIL ready for DRM hit");
            @(posedge clk);#1;
            if (!isv || ise || idata!==expected || ar_count!=old_ar)
                $fatal(1,"RESULT: FAIL DRM hit edge/address=%h",address);
            ia=poison;#1;
            if (!isv || idata!==expected)
                $fatal(1,"RESULT: FAIL live address changed accepted DRM response");
            @(negedge clk);iv=0;#1;
            if (!isv || idata!==expected)
                $fatal(1,"RESULT: FAIL DRM response not held to capture edge");
            @(posedge clk);
            if (!isv || idata!==expected)
                $fatal(1,"RESULT: FAIL DRM response wrong at CPU capture edge");
            @(negedge clk);
            if (isv || dsv || ar_count!=old_ar)
                $fatal(1,"RESULT: FAIL repeated DRM response or spurious AR");
            tests=tests+1;
        end
    endtask

    task automatic reset_during_hit;
        begin
            conservation();
            @(negedge clk);iv=1;ia='hbfc;
            @(posedge clk);#1;
            if (!isv || idata!==word_at('hbfc))
                $fatal(1,"RESULT: FAIL reset test did not start with DRM hit");
            @(negedge clk);iv=0;resetn=0;
            repeat(2) @(negedge clk);
            if (isv || dsv || rv || av)
                $fatal(1,"RESULT: FAIL reset retained DRM response");
            resetn=1;
            // Stale RAM contents must not bypass the cleared valid bit.
            fetch('hbfc,1);fetch('hbe4,0);
            tests=tests+1;
        end
    endtask

'''
new_tb = new_tb.replace('    initial begin : run_tests', extra+'    initial begin : run_tests', 1)
insert = r'''        // New synchronous RAM checks use the warm 0x800..0xbff I32 from above.
        conservation();
        for (k=0;k<I_LINES;k=k+1) begin
            for (lane=0;lane<8;lane=lane+1) begin
                sync_hit_address_change('h800+k*32+lane*4, (31-k)*32+((lane+3)%8)*4);
            end
        end
        reset_during_hit();
        if (fill_writes<=0) $fatal(1,"RESULT: FAIL no qualified DRM fills");
        $display("CHECK: synchronous_read_accepted_address_all_rows_words_hit_reset PASS");
'''
new_tb = new_tb.replace('        conservation();\n        if (tests!=834)',
                        insert+'        conservation();\n        if (tests!=1093)', 1)
new_tb = new_tb.replace('expected=834', 'expected=1093').replace('PASS inst_cache32_x32', 'PASS inst_drm_x32')
(HERE / 'tb_inst_drm_x32.sv').write_text(new_tb, encoding='utf-8')

pds = ROOT / 'RISCV.pds'
before = pds.read_bytes()
(PREP / 'RISCV_before.pds').write_bytes(before)
text = before.decode('utf-8')
assert 'ipcore/icache/icache.idf' not in text
ip_node = '''                (_ip "ipcore/icache/icache.idf"
                    (_ip_source_item "ipcore/icache/rtl/ipm2l_sdpram_v1_10_icache.v")
                    (_ip_source_item "ipcore/icache/icache.v")
                )
'''
anchor = '                (_ip "ipcore/inst_rom/inst_rom.idf"'
assert text.count(anchor) == 1
# Preserve the rest of the user's project byte for byte, including CRLF.
newline = '\r\n' if '\r\n' in text else '\n'
text = text.replace(anchor, ip_node.replace('\n', newline)+anchor, 1)
pds.write_bytes(text.encode('utf-8'))
assert text.replace(ip_node.replace('\n', newline), '', 1).encode('utf-8') == before

paths = set(baseline['registered_input_sha256'])
paths.update(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT / 'ipcore/icache').rglob('*') if p.is_file())
paths.update(str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT / 'ipcore/dcache').rglob('*') if p.is_file())
paths.update([
    str(old_bridge.relative_to(ROOT)).replace('\\','/'),
    'sim/mini_board_migration/run_inst_drm.py', 'sim/mini_board_migration/prepare_inst_drm.py',
    'sim/mini_board_migration/run_inst_cache32.py', 'sim/mini_board_migration/resume_inst_cache32.py',
    'sim/mini_board_migration/tb_inst_cache32_x32.sv', 'sim/mini_board_migration/tb_inst_drm_x32.sv',
    'sim/mini_board_migration/build/inst_drm_preparation_20261012_a/RISCV_before.pds',
    'sim/mini_board_migration/build/inst_cache32_preparation_20261012_a/pds_review.json',
    'sim/mini_board_migration/build/inst_cache32_preparation_20261012_a/board_review.json',
    'sim/mini_board_migration/build/ds_mini_i32_resume_20261012_170046/codex_review.json',
])
paths.update(baseline['fixed_software_sha256'])
for mode in ['performance_120', 'validation_120']:
    paths.add(f'sim/mini_board_migration/board/coremark_i32_01/{mode}.json')
vendor = [VENDOR / 'GTP_GRS.v', VENDOR / 'GTP_DRM36K_E1.v']
config = project_configuration(text)
manifest = dict(status='MINI_INST_DRM_PREPARED_HDL_NOT_RUN',
    baseline_bridge=str(old_bridge.relative_to(ROOT)).replace('\\','/'),
    baseline_board_directory='sim/mini_board_migration/board/coremark_i32_01',
    baseline_bitstream_sha256=baseline['bitstream_sha256'],
    candidate_bridge_sha256=sha(ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v'),
    expected_checks=1093, unit_plan=planned_counts(), isa_cases=[],
    project_configuration_sha256=hashlib.sha256(config.encode()).hexdigest(),
    ip_configuration={'WR_DATA_WIDTH':'256','WR_ADDR_WIDTH':'6','RD_DATA_WIDTH':'32','RD_ADDR_WIDTH':'9',
        'OUTPUT_REG':'false','FAB_REG':'false','RESET_TYPE':'SYNC','INIT_EN':'false','INIT_FILE':'NONE',
        'WR_BYTE_EN':'false','WR_CLK_EN':'false','RD_CLK_EN':'false','CAS_MODE':'36K'},
    sha256={p:sha(ROOT / p) for p in sorted(paths)},
    vendor_sha256={str(p).replace('\\','/'):sha(p) for p in vendor})
(HERE / 'inst_drm_inputs.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
old = old_bridge.read_text(encoding='utf-8').splitlines(keepends=True)
new = (ROOT / 'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8').splitlines(keepends=True)
(PREP / 'rtl_change.patch').write_text(''.join(difflib.unified_diff(old,new,fromfile='successful_I32_D16',
    tofile='myriscv/dual_sram_to_pango_ddr_bridge.v')),encoding='utf-8')
from run_inst_drm import require_inputs
require_inputs()
receipt = dict(status='MINI_INST_DRM_STATIC_PREPARATION_PASS_HDL_NOT_RUN',
    input_manifest_sha256=sha(HERE / 'inst_drm_inputs.json'), protected_inputs=len(paths),
    candidate_bridge_sha256=manifest['candidate_bridge_sha256'],
    expected_checks=1093, unit_plan=manifest['unit_plan'], vendor_models=manifest['vendor_sha256'],
    baseline_registered_sources_unchanged_except_bridge=True, only_I_data_implementation_changed=True,
    pds_delta='Only add icache IDF and its two generated sources; other bytes preserved',
    ip_spec_warning='04030130 nonfatal AW6 vs legacy minimum9 check; GUI permits6, preserve generator/source',
    simulation='NOT_RUN', pds='NOT_RUN', board='NOT_RUN')
(PREP / 'preparation.json').write_text(json.dumps(receipt,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(receipt,ensure_ascii=False,indent=2))
