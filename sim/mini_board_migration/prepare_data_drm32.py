"""One-time Task020 static preparation; no HDL/PDS/board execution."""
from pathlib import Path
import difflib
import hashlib
import json
from run_data_drm32 import HERE, ROOT, MANIFEST, planned_counts, require_inputs
from resume_inst_cache32 import project_configuration

sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
prep=HERE/'build/data_drm32_preparation_20261012_a';prep.mkdir(exist_ok=False)
baseline=HERE/'build/ds_mini_idrm_20261012_181906'
assert json.loads((baseline/'codex_review.json').read_text(encoding='utf-8'))['status']=='MINI_INST_DRM_RAW_EVIDENCE_REVIEW_PASS'
old=baseline/'dual_sram_to_pango_ddr_bridge.v'
assert sha(old)=='b1ec2497bcd6974f1de0fec56c2d9f14ae517853a09b279458f49ea88f04572d'
prior=json.loads((HERE/'inst_drm_inputs.json').read_text(encoding='utf-8'))
for name,digest in prior['sha256'].items():
    if name!='myriscv/dual_sram_to_pango_ddr_bridge.v': assert sha(ROOT/name)==digest,name

tb=(HERE/'tb_inst_drm_x32.sv').read_text(encoding='utf-8')
tb=tb.replace('module tb_inst_drm_x32;','module tb_data_drm32_x32;',1)
tb=tb.replace('production RTL fixes I32/D16','production RTL fixes I32/D32')
tb=tb.replace('localparam integer D_LINES = 16;','localparam integer D_LINES = 32;')
tb=tb.replace('independent_D16_locked_upper_I31_fill_data_priority','independent_D32_locked_upper_I31_fill_data_priority')
tb=tb.replace('readiness_reset_clear_I32_D16_cancel_pending_IF','readiness_reset_clear_I32_D32_cancel_pending_IF')
# Target the new upper D31 and alter live DA while its accepted miss is in flight.
a=tb.index('    task automatic queued_data_fill;');b=tb.index('    endtask',a)+len('    endtask')
body=tb[a:b].replace("'h1fc","'h3fc").replace("'h1e4","'h3e4")
tb=tb[:a]+body+tb[b:]
extra=r'''    // D32 DRM accepted address and independent response-source checks.
    integer data_fill_writes=0;
    always @(posedge clk) begin
        if (!resetn) data_fill_writes<=0;
        else if (dut.g_data_drm.u_data_data_ram.wr_en) data_fill_writes<=data_fill_writes+1;
        if (dut.g_data_drm.u_data_data_ram.wr_en !== (resetn && init_done && dut.data_line_fill))
            $fatal(1,"RESULT: FAIL D DRM write qualification");
        if (dut.g_data_drm.u_data_data_ram.wr_addr !== {1'b0,dut.request_line_tag[4:0]} ||
            dut.g_data_drm.u_data_data_ram.rd_addr !== {1'b0,da[9:2]})
            $fatal(1,"RESULT: FAIL D32 DRM address mapping");
    end

    task automatic sync_data_address_change(input [31:0] address, input [31:0] poison);
        integer old_ar;
        reg [31:0] expected;
        begin
            expected=word_at(address);
            @(negedge clk);old_ar=ar_count;dv=1;dw=0;da=address;
            #1;if (!dr) $fatal(1,"RESULT: FAIL ready for D DRM hit");
            @(posedge clk);#1;
            if (!dsv || isv || dse || ddata!==expected || ar_count!=old_ar)
                $fatal(1,"RESULT: FAIL D DRM hit address=%h",address);
            da=poison;ia='h800+poison;#1;
            if (!dsv || ddata!==expected)
                $fatal(1,"RESULT: FAIL live DA changed accepted D response");
            @(negedge clk);dv=0;#1;
            if (!dsv || ddata!==expected)
                $fatal(1,"RESULT: FAIL D DRM response hold");
            @(posedge clk);
            if (!dsv || ddata!==expected)
                $fatal(1,"RESULT: FAIL D DRM CPU capture edge");
            @(negedge clk);
            if (isv || dsv || ar_count!=old_ar)
                $fatal(1,"RESULT: FAIL D DRM repeated response/extra AR");
            tests=tests+1;
        end
    endtask

    task automatic reset_during_data_hit;
        begin
            conservation();
            @(negedge clk);dv=1;dw=0;da='h3fc;
            @(posedge clk);#1;
            if (!dsv || ddata!==word_at('h3fc))
                $fatal(1,"RESULT: FAIL reset did not start with D31 hit");
            @(negedge clk);dv=0;resetn=0;
            repeat(2) @(negedge clk);
            if (isv || dsv || rv || av) $fatal(1,"RESULT: FAIL D hit reset cancellation");
            resetn=1;
            load_word('h3fc,1);load_word('h3e4,0);
            tests=tests+1;
        end
    endtask

'''
tb=tb.replace('    initial begin : run_tests',extra+'    initial begin : run_tests',1)
new_checks=r'''        // D32: all rows/words, 512 split retained and 1024 alias invalidates.
        for (k=0;k<D_LINES;k=k+1) begin load_word(k*32,1); end
        for (k=0;k<D_LINES;k=k+1) begin
            for (lane=0;lane<8;lane=lane+1) begin
                sync_data_address_change(k*32+lane*4,(31-k)*32+((lane+3)%8)*4);
            end
        end
        load_word('h400,1);load_word(0,1);load_word('h3fc,0);
        reset_during_data_hit();
        if (data_fill_writes<=0) $fatal(1,"RESULT: FAIL no D32 qualified fill");
        $display("CHECK: D32_all_words_synchronous_accepted_address_1024_conflict_hit_reset PASS");

        cold();load_word('h3fc,1);
        bad_id=1;load_word('h7fc,1);bad_id=0;load_word('h3fc,0);
        bad_last=1;load_word('h7f8,1);bad_last=0;load_word('h3fc,0);
        cross_id=1;load_word('h7fc,1);cross_id=0;load_word('h3fc,0);
        instant_read=1;load_word('h7fc,1);load_word('h7f8,0);instant_read=0;
        instant_write=1;store_word('h7f8,32'h12345678,15);instant_write=0;
        load_word('h7fc,1);load_word('h7f8,0);
        cold();load_word('h3fc,1);
        conservation();
        @(negedge clk);dv=1;dw=0;da='h7fc;
        @(posedge clk);@(negedge clk);dv=0;da='h5c;
        if (!rv || rrdy) $fatal(1,"RESULT: FAIL D reset did not cancel blocked AR");
        resetn=0;repeat(2) @(negedge clk);
        if (isv || dsv || rv || av) $fatal(1,"RESULT: FAIL D miss reset cancellation");
        resetn=1;
        load_word('h3fc,1);load_word('h3e4,0);tests=tests+1;
        // Switch among D hit / I miss / I hit / store / I refill / D hit.
        fetch('hbfc,1);load_word('h3fc,0);fetch('hbe4,0);
        store_word('hbec,32'habcd0123,15);fetch('hbec,1);load_word('h3e4,0);
        $display("CHECK: D31_bad_ID_last_same_cycle_fill_cancel_and_I_D_source_switch PASS");
'''
tb=tb.replace('        conservation();\n        if (tests!=1093)',
              new_checks+'        conservation();\n        if (tests!=1521)',1)
tb=tb.replace('expected=1093','expected=1521').replace('PASS inst_drm_x32','PASS data_drm32_x32')
(HERE/'tb_data_drm32_x32.sv').write_text(tb,encoding='utf-8')

pds=ROOT/'RISCV.pds';before=pds.read_bytes();(prep/'RISCV_before.pds').write_bytes(before)
text=before.decode('utf-8');assert 'ipcore/dcache/dcache.idf' not in text
node='''                (_ip "ipcore/dcache/dcache.idf"
                    (_ip_source_item "ipcore/dcache/rtl/ipm2l_sdpram_v1_10_dcache.v")
                    (_ip_source_item "ipcore/dcache/dcache.v")
                )
'''
newline='\r\n' if '\r\n' in text else '\n';node=node.replace('\n',newline)
anchor='                (_ip "ipcore/icache/icache.idf"';assert text.count(anchor)==1
text=text.replace(anchor,node+anchor,1);pds.write_bytes(text.encode('utf-8'))
assert text.replace(node,'',1).encode('utf-8')==before
paths=set(prior['sha256'])
paths.update([
    str(old.relative_to(ROOT)).replace('\\','/'),
    'sim/mini_board_migration/build/ds_mini_idrm_20261012_181906/codex_review.json',
    'DeepSeek/任务019_结果_ds_mini_idrm_20261012_181906.md',
    'sim/mini_board_migration/review_inst_drm.py','sim/mini_board_migration/inst_drm_inputs.json',
    'sim/mini_board_migration/run_data_drm32.py','sim/mini_board_migration/prepare_data_drm32.py',
    'sim/mini_board_migration/tb_data_drm32_x32.sv',
    'sim/mini_board_migration/build/data_drm32_preparation_20261012_a/RISCV_before.pds'])
m=dict(status='MINI_DATA_DRM32_PREPARED_HDL_NOT_RUN',baseline_bridge=str(old.relative_to(ROOT)).replace('\\','/'),
       baseline_functional='Task019 I32 DRM/D16 FF raw audit PASS',
       baseline_board_directory='sim/mini_board_migration/board/coremark_i32_01',
       baseline_bitstream_sha256=prior['baseline_bitstream_sha256'],
       candidate_bridge_sha256=sha(ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v'),expected_checks=1521,
       unit_plan=planned_counts(),isa_cases=[],ip_configuration=prior['ip_configuration'],
       vendor_sha256=prior['vendor_sha256'],
       project_configuration_sha256=hashlib.sha256(project_configuration(text).encode()).hexdigest(),
       sha256={p:sha(ROOT/p) for p in sorted(paths)})
MANIFEST.write_text(json.dumps(m,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
require_inputs()
(prep/'rtl_change.patch').write_text(''.join(difflib.unified_diff(old.read_text(encoding='utf-8').splitlines(True),
    (ROOT/'myriscv/dual_sram_to_pango_ddr_bridge.v').read_text(encoding='utf-8').splitlines(True),
    fromfile='Task019_I32_DRM_D16_FF',tofile='myriscv/dual_sram_to_pango_ddr_bridge.v')),encoding='utf-8')
r=dict(status='MINI_DATA_DRM32_STATIC_PREPARATION_PASS_HDL_NOT_RUN',input_manifest_sha256=sha(MANIFEST),
       candidate_bridge_sha256=m['candidate_bridge_sha256'],protected_inputs=len(paths),vendor_models=2,
       expected_checks=1521,unit_plan=m['unit_plan'],I_path_and_DDR_FSM_unchanged=True,
       capacity='I32/D32, 1KiB each on x32',PDS='NOT_RUN',board='UNAVAILABLE_NOT_TESTED',
       baseline_I_only_PDS_board='NOT_RUN; user authorized combined D migration before board returns')
(prep/'preparation.json').write_text(json.dumps(r,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
print(json.dumps(r,indent=2,ensure_ascii=False))
