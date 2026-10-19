"""Task028 key suite, proven physical model and actual SoC retirement oracle."""
from pathlib import Path
from generate_write_buffer_soc_resume_tb import build_resume_tb
HERE=Path(__file__).resolve().parent
def build_tb():
    text=build_resume_tb()
    text=text.replace('module tb_write_buffer_soc_resume #(parameter integer POSTED=1, REPRO_OLD_PROGRAM=0);',
        'module tb_data_read_overlap_x32 #(parameter integer READ_OVERLAP=1);\n    localparam integer POSTED=1, REPRO_OLD_PROGRAM=0;',1)
    text=text.replace('.MEM_DQ_WIDTH(32),.POSTED_WRITE_ENABLE(POSTED)) dut(',
        '.MEM_DQ_WIDTH(32),.POSTED_WRITE_ENABLE(POSTED),.DATA_READ_UNDER_WRITE_ENABLE(READ_OVERLAP)) dut(',1)
    text=text.replace('integer fills=0,updates=0,cancelled=0;', 'integer fills=0,updates=0,cancelled=0,d_overlap=0;',1)
    text=text.replace('if (POSTED && pending_store) $fatal(1,"RESULT: FAIL D accepted while entry full");', '''if (pending_store) begin
                    if(bdw || !READ_OVERLAP || !oracle_valid[bda[10:5]] ||
                       oracle_tag[bda[10:5]]!=bda[31:5] || pending_tag==bda[31:5])
                        $fatal(1,"RESULT: FAIL unqualified D access overtook write");
                    if(!backend_write) d_overlap=d_overlap+1;
                end''',1)
    cases=(HERE/'data_read_overlap_cases.svh').read_text(encoding='utf-8')
    text=text.replace('    initial begin : suite',cases+'\n    initial begin : suite\n        manual_groups();',1)
    text=text.replace('cpu_events!=414','cpu_events!=480',1)
    text=text.replace('tests-group_start!=414','tests-group_start!=480',1)
    text=text.replace('real_soc_fence_irq_stop PASS checks=414','real_soc_read_overlap_fence_irq_stop PASS checks=480',1)
    text=text.replace('REPRO_OLD_PROGRAM || tests!=414 ||','REPRO_OLD_PROGRAM || tests!=1597 ||',1)
    text=text.replace('pushes!=67 || completions!=67 || cancelled!=0 ||',
        'pushes-base_pushes!=67 || completions-base_completions!=67 || cancelled-base_cancelled!=0 ||',1)
    text=text.replace('fills!=1 || updates!=65',
        'fills-base_fills!=2 || updates-base_updates!=65 || d_overlap-base_d_overlap<=0',1)
    text=text.replace('RESULT: PASS write_buffer_soc_resume tests=', 'RESULT: PASS data_read_overlap_x32 tests=',1)
    text=text.replace('STOP_WAIT=%0d fills=%0d updates=%0d",',
        'STOP_WAIT=%0d fills=%0d updates=%0d D_OVERLAP=%0d SOC_D_OVERLAP=%0d",',1)
    text=text.replace('stop_wait,fills,updates);',
        'stop_wait,fills-base_fills,updates-base_updates,d_overlap,d_overlap-base_d_overlap);',1)
    return text
if __name__=='__main__':
    p=HERE/'tb_data_read_overlap_x32.sv';assert not p.exists();p.write_text(build_tb(),encoding='utf-8')
