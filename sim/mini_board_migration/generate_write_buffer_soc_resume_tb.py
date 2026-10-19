"""Resume only the unfinished SoC group; retain all original memory/CPU predicates."""
from pathlib import Path
from generate_write_buffer_tb import build_tb
HERE=Path(__file__).resolve().parent
def build_resume_tb():
    text=build_tb().replace('module tb_write_buffer_x32 #(parameter integer POSTED=1);',
        'module tb_write_buffer_soc_resume #(parameter integer POSTED=1, REPRO_OLD_PROGRAM=0);',1)
    cases=(HERE/'write_buffer_cases.svh').read_text(encoding='utf-8')
    a=cases.index('        for(k=0;k<128;k=k+1) for(lane=0;lane<8;lane=lane+1) memory[k]')
    b=cases.index('        @(negedge clk);resetn=0;soc_mode=1;iv=0;dv=0;w_latency=40;',a)
    # The former six manual groups are already PASS. SoC has its own complete reset/image.
    cases=cases[:a]+cases[b:]
    cases=cases.replace('resetn=0;soc_mode=1;', 'resetn=0;init_done=1;soc_mode=1;',1)
    cases=cases.replace('pass_writes=0;', 'pass_writes=0,run_writes=0;',1)
    cases=cases.replace("if(soc.mmio_req_write && soc.mmio_req_addr=='h10) pass_writes=pass_writes+1;", """if(soc.mmio_req_write && soc.mmio_req_addr=='h10) begin
                    if(soc.mmio_req_wdata==1 && selftest==0) run_writes=run_writes+1;
                    else if(soc.mmio_req_wdata==2 && (selftest==1 || REPRO_OLD_PROGRAM)) pass_writes=pass_writes+1;
                    else $fatal(1,"RESULT: FAIL TEST_STATUS RUN/PASS contract");
                end""",1)
    cases=cases.replace('if(soc.u_cpu.sync_trap_event) $fatal(1,"RESULT: FAIL unexpected synchronous CPU trap");', """if(soc.u_cpu.sync_trap_event) begin
                $display("DIAG_TRAP pc=%h inst=%h cause=%0d tval=%h cpu_events=%0d AW=%0d W=%0d selftest=%0d busy=%0d flow=%0d",
                    soc.u_cpu.mem_wb_pc,soc.u_cpu.mem_wb_inst,soc.u_cpu.wb_trap_cause,soc.u_cpu.wb_trap_tval,
                    cpu_events,aw_count,w_count,selftest,busy,soc.u_cpu.flow_state);
                if(REPRO_OLD_PROGRAM && soc.u_cpu.mem_wb_pc===32'h4000007c &&
                   soc.u_cpu.mem_wb_inst===32'h00b52823 && soc.u_cpu.wb_trap_cause===5'd7 &&
                   soc.u_cpu.wb_trap_tval===32'h10000010 && cpu_events==412 &&
                   run_writes==0 && pass_writes==1 && selftest==0 && irq_count==1 &&
                   !busy && aw_count==67 && w_count==67 && soc.u_simple_mmio.g_perf.u_perf.state==3 &&
                   soc.u_simple_mmio.g_perf.u_perf.count[12]==67) begin
                    $display("CHECK: original_missing_RUN_store_fault PASS pc=4000007c cause=7 tval=10000010");
                    $display("RESULT: PASS write_buffer_old_program_diagnosis events=412 original_functional_status=FAIL");
                    $finish;
                end
                $fatal(1,"RESULT: FAIL unexpected synchronous CPU trap");
            end""",1)
    cases=cases.replace('cpu_events!=413','cpu_events!=414',1)
    cases=cases.replace('pass_writes!=1 ||','pass_writes!=1 || run_writes!=1 ||',1)
    cases=cases.replace('tests-group_start!=413','tests-group_start!=414',1)
    cases=cases.replace("if(opcode=='h23 && address=='h10000010) cpu_done=1;",
                        "if(opcode=='h23 && address=='h10000010 && golden_regs[r2]==2) cpu_done=1;",1)
    cases=cases.replace('real_soc_fence_irq_stop PASS checks=413','real_soc_fence_irq_stop PASS checks=414',1)
    cases=cases.replace('tests!=839 ||','REPRO_OLD_PROGRAM || tests!=414 ||',1)
    cases=cases.replace('pushes!=204 || completions!=202 || cancelled!=2 ||',
                        'pushes!=67 || completions!=67 || cancelled!=0 ||',1)
    cases=cases.replace('fills!=8 || updates!=198','fills!=1 || updates!=65',1)
    cases=cases.replace('RESULT: PASS write_buffer_x32 tests=', 'RESULT: PASS write_buffer_soc_resume tests=',1)
    text=text.replace('`include "write_buffer_cases.svh"',cases,1)
    # Trace is observation only. Flush each event to preserve evidence on a fatal.
    probe="""
    integer trace_fd;
    string trace_path;
    initial begin
        if(!$value$plusargs("EVENT_LOG=%s",trace_path)) $fatal(1,"RESULT: FAIL missing event log");
        trace_fd=$fopen(trace_path,"w");
        if(!trace_fd) $fatal(1,"RESULT: FAIL cannot open event log");
    end
    always @(negedge clk) if(resetn && soc_mode) begin
        if(soc.u_cpu.normal_retire || soc.u_cpu.mret_commit || soc.u_cpu.irq_take || soc.u_cpu.sync_trap_event) begin
            $fdisplay(trace_fd,"EV t=%0t pc=%h inst=%h we=%h rd=%0d data=%h trap=%0d cause=%0d tval=%h irq=%0d next=%h busy=%0d flow=%0d AW=%0d W=%0d",
                $time,cpc,cinst,cwe,crd,cvalue,soc.u_cpu.sync_trap_event,soc.u_cpu.wb_trap_cause,
                soc.u_cpu.wb_trap_tval,soc.u_cpu.irq_take,soc.u_cpu.arch_next_pc,busy,soc.u_cpu.flow_state,aw_count,w_count);
            $fflush(trace_fd);
        end
        if((biv && bir)||(bdv && bdr)||bisv||bdsv||(av && ardy)||wrdy||(rv && rrdy)) begin
            $fdisplay(trace_fd,"BUS t=%0t I=%0d ia=%h D=%0d da=%h write=%0d wd=%h strb=%h Irsp=%0d idata=%h Drsp=%0d ddata=%h AR=%0d ra=%h AW=%0d aa=%h W=%0d busy=%0d",
                $time,biv&&bir,bia,bdv&&bdr,bda,bdw,bwd,bws,bisv,bidata,bdsv,bddata,rv&&rrdy,ra,av&&ardy,aa,wrdy,busy);
            $fflush(trace_fd);
        end
    end
"""
    return text.replace('\nendmodule\n',probe+'\nendmodule\n',1)
if __name__=='__main__':
    p=HERE/'tb_write_buffer_soc_resume.sv';assert not p.exists()
    p.write_text(build_resume_tb(),encoding='utf-8')
