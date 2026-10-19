"""Task029 forwarding oracle, completion-edge checks and typed-load SoC integration."""
from pathlib import Path
from generate_data_read_overlap_tb import build_tb as prior_tb
HERE=Path(__file__).resolve().parent
def build_tb():
    s=prior_tb().replace('module tb_data_read_overlap_x32 #(parameter integer READ_OVERLAP=1);',
        'module tb_store_forward_x32 #(parameter integer FORWARD_ENABLE=1);\n    localparam integer READ_OVERLAP=1;',1)
    s=s.replace('.DATA_READ_UNDER_WRITE_ENABLE(READ_OVERLAP)) dut(',
        '.DATA_READ_UNDER_WRITE_ENABLE(READ_OVERLAP),.DATA_STORE_FORWARD_ENABLE(FORWARD_ENABLE)) dut(',1)
    s=s.replace('integer fills=0,updates=0,cancelled=0,d_overlap=0;',
        'integer fills=0,updates=0,cancelled=0,d_overlap=0,same_reads=0,word_forwards=0,collision_blocks=0,response_w_overlap=0;\n    reg [2:0] pending_lane=0;\n    reg d_same_line=0;',1)
    s=s.replace('|| pending_tag==bda[31:5]', '|| (pending_tag==bda[31:5] && !FORWARD_ENABLE)',1)
    s=s.replace('if(!backend_write) d_overlap=d_overlap+1;', '''if(!backend_write) begin
                        d_overlap=d_overlap+1;
                        if(pending_tag==bda[31:5]) begin
                            same_reads=same_reads+1;
                            if(pending_lane==bda[4:2]) word_forwards=word_forwards+1;
                        end
                    end
                    if(backend_write && pending_tag==bda[31:5]) $fatal(1,"RESULT: FAIL same-line acceptance collided with cache write");''',1)
    s=s.replace('dexpect=bdw ? 0 : word_at(bda);','dexpect=bdw ? 0 : architectural_word(bda);\n                d_same_line=pending_store && !bdw && pending_tag==bda[31:5];',1)
    s=s.replace('pending_row<=bda[10:5];pending_tag<=bda[31:5];',
        'pending_row<=bda[10:5];pending_tag<=bda[31:5];pending_lane<=bda[4:2];',1)
    s=s.replace('if (bdsv) begin', 'if (bdsv) begin\n                if(d_same_line && backend_write) response_w_overlap=response_w_overlap+1;',1)
    s=s.replace('if (pending_store && rv)', '''if(pending_store && backend_write && bdv && !bdw && pending_tag==bda[31:5] &&
               oracle_valid[bda[10:5]] && oracle_tag[bda[10:5]]==bda[31:5] && !bdr) collision_blocks=collision_blocks+1;
            if (pending_store && rv)''',1)
    # Keep only the related existing helpers; replace the prior manual groups.
    old=(HERE/'data_read_overlap_cases.svh').read_text(encoding='utf-8')
    helpers=old[old.index('    task automatic blocked_read'):old.index('    task automatic manual_groups')]
    new=(HERE/'store_forward_cases.svh').read_text(encoding='utf-8')
    s=s.replace(old,helpers+'\n'+new,1)
    s=s.replace("'h03:begin address=golden_regs[r1]+sext(instruction>>20,12);expected_value=golden_mem[(address-'h40000000)/4];expected_we=rdn!=0;end", """'h03:begin
                        address=golden_regs[r1]+sext(instruction>>20,12);
                        expected_value=golden_mem[(address-'h40000000)/4] >> (address[1:0]*8);
                        case(funct3)
                            0:expected_value=sext(expected_value,8);
                            1:expected_value=sext(expected_value,16);
                            2: ;
                            4:expected_value=expected_value & 'hff;
                            5:expected_value=expected_value & 'hffff;
                            default:$fatal(1,"RESULT: FAIL unsupported golden load size");
                        endcase
                        expected_we=rdn!=0;
                    end""",1)
    s=s.replace("if(address[31:12]=='h40000) golden_mem[(address-'h40000000)/4]=golden_regs[r2];", """if(address[31:12]=='h40000) begin
                            case(funct3)
                                0:golden_mem[(address-'h40000000)/4][address[1:0]*8+:8]=golden_regs[r2][7:0];
                                1:golden_mem[(address-'h40000000)/4][address[1:0]*8+:16]=golden_regs[r2][15:0];
                                2:golden_mem[(address-'h40000000)/4]=golden_regs[r2];
                                default:$fatal(1,"RESULT: FAIL unsupported golden store size");
                            endcase
                        end""",1)
    s=s.replace('w_count==67','w_count==71',1)
    s=s.replace('cpu_events!=480','cpu_events!=489',1)
    s=s.replace('aw_count!=67 || w_count!=67','aw_count!=71 || w_count!=71',1)
    s=s.replace('count[12]!=67','count[12]!=71',1)
    s=s.replace('tests-group_start!=480','tests-group_start!=489',1)
    s=s.replace('real_soc_read_overlap_fence_irq_stop PASS checks=480','real_soc_store_forward_typed_loads PASS checks=489',1)
    s=s.replace('tests!=1597','tests!=2238',1)
    s=s.replace('pushes-base_pushes!=67 || completions-base_completions!=67','pushes-base_pushes!=71 || completions-base_completions!=71',1)
    s=s.replace('updates-base_updates!=65 || d_overlap-base_d_overlap<=0',
        'updates-base_updates!=69 || d_overlap-base_d_overlap<=0 || same_reads-base_same<=0 || word_forwards-base_word<=0',1)
    s=s.replace('RESULT: PASS data_read_overlap_x32 tests=', 'RESULT: PASS store_forward_x32 tests=',1)
    s=s.replace('SOC_D_OVERLAP=%0d",',
        'SOC_D_OVERLAP=%0d SAME_LINE=%0d WORD_FORWARD=%0d SOC_SAME_LINE=%0d SOC_WORD_FORWARD=%0d COLLISION_BLOCKS=%0d RSP_W_OVERLAP=%0d",',1)
    s=s.replace('d_overlap,d_overlap-base_d_overlap);',
        'd_overlap,d_overlap-base_d_overlap,same_reads,word_forwards,same_reads-base_same,word_forwards-base_word,collision_blocks,response_w_overlap);',1)
    return s
if __name__=='__main__':
    p=HERE/'tb_store_forward_x32.sv';assert not p.exists();p.write_text(build_tb(),encoding='utf-8')
