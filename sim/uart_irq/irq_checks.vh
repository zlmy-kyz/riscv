// Independent retirement PC model; decode branches/JAL/JALR from instructions.
// Never use arch_next_pc or mem_wb_next_pc to calculate the expected resume PC.
reg [31:0] ref_pc=PROGRAM_BASE, ref_rf [0:31];
reg [31:0] trap_resume=0;
integer irqs=0, faults=0, mrets=0, accepted=0, responses=0;
integer target_requests=0, target_retired=0, foreground_resume=0;
integer ref_i;
reg [31:0] retired_inst, next_ref, branch_imm, jump_imm, old_status;
reg [31:0] saved_mepc, saved_cause;
initial for (ref_i=0;ref_i<32;ref_i=ref_i+1) ref_rf[ref_i]=0;
always @(posedge clk) if (resetn) begin
    if (dut.u_cpu.data_req_fire) begin
        accepted=accepted+1;
        if (dut.u_cpu.id_ex_pc==target_pc) target_requests=target_requests+1;
    end
    if (dut.data_rsp_valid) responses=responses+1;
    check(responses<=accepted,"response without accepted request");
    if (dut.u_cpu.normal_retire) begin
        check(dut.u_cpu.mem_wb_pc===ref_pc,"retired PC differs from independent program flow");
        retired_inst=dut.u_cpu.mem_wb_inst;
        next_ref=ref_pc+4;
        branch_imm={{19{retired_inst[31]}},retired_inst[31],retired_inst[7],retired_inst[30:25],retired_inst[11:8],1'b0};
        jump_imm={{11{retired_inst[31]}},retired_inst[31],retired_inst[19:12],retired_inst[20],retired_inst[30:21],1'b0};
        case (retired_inst[6:0])
            7'h6f: next_ref=ref_pc+jump_imm;
            7'h67: next_ref=(ref_rf[retired_inst[19:15]]+{{20{retired_inst[31]}},retired_inst[31:20]}) & 32'hfffffffe;
            7'h63: case (retired_inst[14:12])
                0: if (ref_rf[retired_inst[19:15]]==ref_rf[retired_inst[24:20]]) next_ref=ref_pc+branch_imm;
                1: if (ref_rf[retired_inst[19:15]]!=ref_rf[retired_inst[24:20]]) next_ref=ref_pc+branch_imm;
                4: if ($signed(ref_rf[retired_inst[19:15]])<$signed(ref_rf[retired_inst[24:20]])) next_ref=ref_pc+branch_imm;
                5: if ($signed(ref_rf[retired_inst[19:15]])>=$signed(ref_rf[retired_inst[24:20]])) next_ref=ref_pc+branch_imm;
                6: if (ref_rf[retired_inst[19:15]]<ref_rf[retired_inst[24:20]]) next_ref=ref_pc+branch_imm;
                7: if (ref_rf[retired_inst[19:15]]>=ref_rf[retired_inst[24:20]]) next_ref=ref_pc+branch_imm;
            endcase
        endcase
        if (dut.u_cpu.rf_we && dut.u_cpu.rf_waddr!=0) ref_rf[dut.u_cpu.rf_waddr]=dut.u_cpu.rf_wdata;
        if (ref_pc==target_pc) begin
            target_retired=target_retired+1;
            $display("CHECK: target retired pc=%08h count=%0d",ref_pc,target_retired);
        end
        if (ref_pc==resume_pc) begin
            foreground_resume=foreground_resume+1;
            $display("CHECK: following CSR retired pc=%08h count=%0d",ref_pc,foreground_resume);
        end
        ref_pc=next_ref;
    end
    if (dut.u_cpu.irq_take || dut.u_cpu.sync_trap_event) begin
        check(!(dut.u_cpu.irq_take && dut.u_cpu.sync_trap_event),"IRQ and synchronous exception committed together");
        old_status=dut.u_cpu.u_csr_file.mstatus;
        saved_mepc=ref_pc;
        if (dut.u_cpu.irq_take) begin
            check(dut.u_cpu.pipeline_empty && accepted==responses && !write_pending && !(read_pending && !read_address[11]),
                  "IRQ before pipeline/accepted bus transaction drained");
            check(!dut.u_cpu.data_req_fire && !dut.u_cpu.normal_retire && !dut.u_cpu.id_fire,
                  "new work at IRQ boundary");
            check(old_status[3] && ((dut.u_cpu.csr_irq_pending & dut.u_cpu.csr_irq_enable)!=0),"masked IRQ taken");
            saved_cause=32'h80000000|dut.u_cpu.irq_cause;
            if (dut.u_cpu.csr_irq_pending[11] && dut.u_cpu.csr_irq_enable[11]) check(dut.u_cpu.irq_cause==11,"external priority/cause");
            else if (dut.u_cpu.csr_irq_pending[3] && dut.u_cpu.csr_irq_enable[3]) check(dut.u_cpu.irq_cause==3,"software priority/cause");
            else check(dut.u_cpu.irq_cause==7,"timer cause");
            irqs=irqs+1;
        end else begin
            check(dut.u_cpu.mem_wb_pc===ref_pc && !dut.u_cpu.rf_we,"fault PC or fault wrote register");
            saved_cause=dut.u_cpu.wb_trap_cause;
            faults=faults+1;
        end
        ref_pc=32'h400;
        #0.1;
        check(dut.u_cpu.u_csr_file.mepc===saved_mepc,"mepc differs from independent continuation/fault PC");
        check(dut.u_cpu.u_csr_file.mcause===saved_cause,"mcause mismatch");
        check(dut.u_cpu.u_csr_file.mstatus[3]==0 && dut.u_cpu.u_csr_file.mstatus[7]===old_status[3],"trap MIE/MPIE");
        check(dut.u_cpu.pc===32'h400,"mtvec direct redirect");
        if (saved_cause[31]) check(dut.u_cpu.u_csr_file.mtval==0,"interrupt mtval");
        $display("CHECK: trap mepc=%08h mcause=%08h mtval=%08h MIE=0 MPIE=%0d PASS",saved_mepc,saved_cause,dut.u_cpu.u_csr_file.mtval,old_status[3]);
    end else if (dut.u_cpu.mret_commit) begin
        check(dut.u_cpu.mem_wb_pc===ref_pc,"MRET retired at wrong PC");
        old_status=dut.u_cpu.u_csr_file.mstatus;
        trap_resume=dut.u_cpu.u_csr_file.mepc;
        // mepc is checked at trap entry; only exception handler adds four.
        check(trap_resume==saved_mepc+(saved_cause[31]?0:4),"handler/MRET return address");
        ref_pc=trap_resume;
        mrets=mrets+1;
        #0.1;
        check(dut.u_cpu.pc===trap_resume && dut.u_cpu.u_csr_file.mstatus[3]===old_status[7] && dut.u_cpu.u_csr_file.mstatus[7],"MRET PC/MIE/MPIE restore");
        $display("CHECK: MRET pc=%08h MIE=%0d MPIE=1 PASS",trap_resume,old_status[7]);
    end
end
