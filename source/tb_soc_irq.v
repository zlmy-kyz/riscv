`timescale 1ns/1fs
module tb_soc_irq #(parameter integer EXEC_FROM_DDR=0);
    localparam [31:0] PROGRAM_BASE=EXEC_FROM_DDR ? 32'h40001000 : 0;
    integer test_case=0;
    reg [31:0] target_pc=0, resume_pc=0;
    task check;
        input condition;
        input [1023:0] message;
        begin
            if (condition !== 1'b1) begin
                $display("RESULT: FAIL soc_irq case=%0d t=%0t: %0s; ref_pc=%h WB_pc=%h mepc=%h mcause=%h req=%0d rsp=%0d",test_case,$time,message,ref_pc,dut.u_cpu.mem_wb_pc,dut.u_cpu.u_csr_file.mepc,dut.u_cpu.u_csr_file.mcause,accepted,responses);
                $fatal(1,"%0s",message);
            end
        end
    endtask
    `include "soc_fixture.vh"
    `include "irq_checks.vh"
    `include "uart_stimulus.vh"
    reg injected=0, withdrawn=0;
    integer wait_overlap=0, irq_drain_cycles=0, inject_cycle=0, cycles=0;
    initial begin
        if (!$value$plusargs("CASE=%d",test_case)) test_case=0;
        if (!$value$plusargs("TARGET=%h",target_pc)) target_pc=0;
        if (!$value$plusargs("RESUME=%h",resume_pc)) resume_pc=0;
        if ($test$plusargs("WAVE")) begin $dumpfile("wave.vcd"); $dumpvars(0,tb_soc_irq); end
        repeat(8) @(negedge clk); resetn=1;
    end
    // Drive only on falling edges, hold level through retirement/drain.
    always @(negedge clk) if (resetn && test_case<100) begin
        if (test_case==15) begin
            if (irqs>=1) irq_external=0;
            if (irqs>=2) irq_software=0;
            if (irqs>=3) irq_timer=0;
        end else if (injected && irqs >= (test_case==12?2:1)) begin irq_external=0; irq_software=0; irq_timer=0; end
        if (!injected) begin
            case (test_case)
                0,9,12,13,14,15: if (dut.u_cpu.id_ex_valid && dut.u_cpu.id_ex_pc==target_pc) injected=1;
                1,2: if (selftest==1) injected=1;
                3,4,7,11: if (dut.u_cpu.ex_mem_valid && dut.u_cpu.ex_mem_pc==target_pc && !dut.data_rsp_valid) injected=1;
                5,6,8,10: if (dut.u_cpu.ex_mem_valid && dut.u_cpu.ex_mem_pc==target_pc && dut.data_rsp_valid) injected=1;
            endcase
            if (injected) begin
                inject_cycle=cycles;
                case (test_case)
                    13: irq_software=1;
                    14: irq_timer=1;
                    15: begin irq_external=1; irq_software=1; irq_timer=1; end
                    default: irq_external=1;
                endcase
            end
        end
        if (test_case==11 && injected && cycles-inject_cycle>=2) begin irq_external=0; withdrawn=1; end
    end
    always @(posedge clk) if (resetn) begin
        cycles=cycles+1;
        if (dut.u_cpu.flow_state==4) irq_drain_cycles=irq_drain_cycles+1;
        if (injected && !withdrawn && dut.u_cpu.ex_mem_valid && dut.u_cpu.ex_mem_pc==target_pc && !dut.data_rsp_valid) wait_overlap=wait_overlap+1;
        if (test_case<100 && dut.u_cpu.sync_trap_event) begin
            check((test_case==9 && dut.u_cpu.wb_trap_cause==4 && dut.u_cpu.wb_trap_tval==32'h40000001) ||
                  (test_case==10 && dut.u_cpu.wb_trap_cause==7 && dut.u_cpu.wb_trap_tval==32'h10000004),"unexpected exception/cause/tval");
            check(irqs==0 && injected,"synchronous exception did not precede pending IRQ");
        end
    end
    initial begin
        wait(resetn);
        if (test_case<100) begin
            wait(selftest==2);
            repeat(30) @(negedge clk);
            check(injected,"IRQ scenario was never exercised");
            check(irqs==(test_case==11?0:(test_case==12?2:(test_case==15?3:1))),"unexpected missing/extra IRQ");
            check(faults==((test_case==9 || test_case==10)?1:0) && mrets==irqs+faults,"exception/MRET count");
            check(target_retired==((test_case==9 || test_case==10)?0:1) && foreground_resume==1,"target duplicated or missing / resume not executed once");
            check(target_requests==((test_case>=3 && test_case<=8) || test_case==10 || test_case==11 ?1:0),"load/store repeated or missing request");
            if (test_case==3 || test_case==5 || test_case==11) check(ddr_writes==1 && beats[0][31:0]==85,"DDR store side effect count/data");
            if (test_case==4 || test_case==6) check(ddr_reads==1 && ref_rf[10]==32'h12345678,"DDR load count/value");
            if (test_case==7 || test_case==8) check(ref_rf[10]==1,"MMIO load data");
            if (test_case==1 || test_case==2) check(ref_rf[9]==32'h800,"mip must expose masked raw IRQ");
            if (test_case==3 || test_case==4 || test_case==7 || test_case==11) check(wait_overlap>0 && irq_drain_cycles>0,"wait/drain not exercised");
            if (test_case==11) check(withdrawn,"IRQ withdrawal missing");
            if (irqs>0) begin
                check(ref_rf[20]==(32'h80000000|((test_case==13)?3:((test_case==14 || test_case==15)?7:11))),"ISR mcause CSR read value");
                check(ref_rf[21]===saved_mepc && ref_rf[22]==0,"ISR mepc/mtval CSR read values");
            end
            check(dut.u_cpu.u_csr_file.mstatus[3] && !irq_external && !irq_software && !irq_timer,"MRET enable/IRQ withdrawal final state");
            if (EXEC_FROM_DDR) check(ddr_instruction_reads>0,"DDR instruction path not exercised");
            $display("RESULT: PASS CPU IRQ case=%0d IRQ=%0d fault=%0d MRET=%0d req=%0d rsp=%0d target_req=%0d target_retire=%0d DDR_W=%0d DDR_R=%0d wait_overlap=%0d",test_case,irqs,faults,mrets,accepted,responses,target_requests,target_retired,ddr_writes,ddr_reads,wait_overlap);
            $finish;
        end
    end
    initial begin #20_000_000; check(0,"IRQ test timeout"); end
endmodule
