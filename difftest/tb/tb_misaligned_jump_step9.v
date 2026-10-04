`timescale 1ns/1ps

// 执行 misaligned_jump_step9.S：对比采用/未采用目标、前递、load-use 和老故障优先级。
module tb_misaligned_jump_step9;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));
    wire [31:0] trace_irq_raw = 32'b0;
    `include "difftest/tb/arch_trace.vh"

    reg [31:0] expected_pc [0:5];
    reg [31:0] expected_tval [0:5];
    reg [31:0] target_pc [0:4];
    reg [31:0] target_tval [0:4];
    integer trap_count = 0;
    integer target_fault_count = 0;
    integer load_branch_stalls = 0;
    integer load_jalr_stalls = 0;
    integer old_fault_priority_seen = 0;
    integer legal_jalr_seen = 0;
    integer not_taken_seen = 0;
    integer i;

    initial begin
        expected_pc[0] = 32'h2c; expected_tval[0] = 32'h2e;
        expected_pc[1] = 32'h30; expected_tval[1] = 32'h32;
        expected_pc[2] = 32'h40; expected_tval[2] = 32'h42;
        expected_pc[3] = 32'h48; expected_tval[3] = 32'h202;
        expected_pc[4] = 32'h58; expected_tval[4] = 32'h301;
        expected_pc[5] = 32'h5c; expected_tval[5] = 32'h5e;
        target_pc[0] = 32'h2c; target_tval[0] = 32'h2e;
        target_pc[1] = 32'h30; target_tval[1] = 32'h32;
        target_pc[2] = 32'h40; target_tval[2] = 32'h42;
        target_pc[3] = 32'h48; target_tval[3] = 32'h202;
        target_pc[4] = 32'h5c; target_tval[4] = 32'h5e;
    end

    initial begin
        #30000;
        $fatal(1, "jump misalignment timeout traps=%0d", trap_count);
    end

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (trap_count == 6 && dut.u_regfile.rf[13] == 32'd1);
        repeat (12) @(posedge clk);
        #1;
        if (trap_count != 6 || target_fault_count != 5 ||
            load_branch_stalls < 1 || load_jalr_stalls < 1 ||
            old_fault_priority_seen < 1 || legal_jalr_seen != 1 ||
            not_taken_seen != 1)
            $fatal(1, "jump event counts wrong trap=%0d target=%0d lb=%0d lj=%0d old=%0d legal=%0d nt=%0d",
                   trap_count, target_fault_count, load_branch_stalls,
                   load_jalr_stalls, old_fault_priority_seen,
                   legal_jalr_seen, not_taken_seen);
        for (i = 0; i < 6; i = i + 1) begin
            if (dut.the_instance_name.mem[128 + 3*i] !== (i == 4 ? 32'd4 : 32'd0) ||
                dut.the_instance_name.mem[129 + 3*i] !== expected_pc[i] ||
                dut.the_instance_name.mem[130 + 3*i] !== expected_tval[i])
                $fatal(1, "handler log[%0d] wrong cause=%h pc=%h tval=%h",
                       i, dut.the_instance_name.mem[128 + 3*i],
                       dut.the_instance_name.mem[129 + 3*i],
                       dut.the_instance_name.mem[130 + 3*i]);
        end
        if (dut.u_regfile.rf[2] !== 32'h3f0 ||
            dut.u_regfile.rf[5] !== 32'h55 ||
            dut.u_regfile.rf[7] !== 32'd0 ||
            dut.u_regfile.rf[8] !== 32'h202 ||
            dut.u_regfile.rf[9] !== 32'h77 ||
            dut.u_regfile.rf[10] !== 32'h59 ||
            dut.u_regfile.rf[11] !== 32'h54 ||
            dut.u_regfile.rf[12] !== 32'h12 ||
            dut.u_regfile.rf[13] !== 32'd1 ||
            dut.u_regfile.rf[20] !== 32'h248 ||
            dut.u_csr_file.mepc !== 32'h60 ||
            dut.u_csr_file.mcause !== 32'd0 ||
            dut.u_csr_file.mtval !== 32'h5e)
            $fatal(1, "jump/link/return final state wrong");
        $display("RESULT: PASS taken target alignment, JALR bit0, load-use and old-fault priority");
        $finish;
    end

    always @(posedge clk) if (resetn) begin
        if (dut.id_fire &&
            (dut.if_id_pc == 32'h54 ||
             dut.if_id_pc == 32'h64))
            $fatal(1, "wrong-path zero instruction issued");
        if (dut.id_fire && dut.if_id_pc == 32'h28) begin
            not_taken_seen = not_taken_seen + 1;
            if (dut.id_taken || dut.id_target_misaligned || dut.branch_redirect)
                $fatal(1, "not-taken branch with misaligned encoded target trapped");
        end
        if (dut.if_id_valid && dut.if_id_pc == 32'h40 && dut.load_use) begin
            load_branch_stalls = load_branch_stalls + 1;
            if (dut.id_fire || dut.id_target_misaligned || dut.branch_redirect)
                $fatal(1, "load->branch judged target before data ready");
        end
        if (dut.if_id_valid && dut.if_id_pc == 32'h48 && dut.load_use) begin
            load_jalr_stalls = load_jalr_stalls + 1;
            if (dut.id_fire || dut.id_target_misaligned || dut.branch_redirect)
                $fatal(1, "load->JALR judged target before data ready");
        end
        if (dut.id_fire && dut.id_target_misaligned) begin
            if (target_fault_count >= 5 ||
                dut.if_id_pc !== target_pc[target_fault_count] ||
                dut.bj_pc !== target_tval[target_fault_count] ||
                dut.branch_redirect || !dut.id_exc_valid ||
                dut.id_exc_cause !== 5'd0 ||
                dut.id_exc_tval !== dut.bj_pc)
                $fatal(1, "ID target fault[%0d] wrong", target_fault_count);
            if (dut.if_id_pc == 32'h40 && dut.id_rs1 !== 32'd0)
                $fatal(1, "load->branch used stale operand");
            if (dut.if_id_pc == 32'h48 && dut.id_rs1 !== 32'h202)
                $fatal(1, "load->JALR used stale operand");
            target_fault_count = target_fault_count + 1;
        end
        if (dut.id_fire && dut.if_id_pc == 32'h50) begin
            legal_jalr_seen = legal_jalr_seen + 1;
            if (dut.id_rs1 !== 32'h59 || dut.jalr_pc !== 32'h58 ||
                !dut.branch_redirect || dut.id_target_misaligned)
                $fatal(1, "JALR did not clear bit0 before alignment check");
        end
        if (dut.id_ex_valid && dut.id_ex_pc == 32'h58 &&
            dut.ex_data_misaligned && dut.if_id_valid && dut.if_id_pc == 32'h5c) begin
            old_fault_priority_seen = old_fault_priority_seen + 1;
            if (dut.id_fire || dut.branch_redirect || !dut.fault_inflight ||
                !dut.id_target_misaligned || dut.id_exc_cause !== 5'd0)
                $fatal(1, "younger ID branch overtook older EX fault");
        end
        if (dut.sync_trap_event) begin
            if (trap_count >= 6 ||
                dut.mem_wb_pc !== expected_pc[trap_count] ||
                dut.wb_trap_cause !== (trap_count == 4 ? 5'd4 : 5'd0) ||
                dut.wb_trap_tval !== expected_tval[trap_count] ||
                dut.rf_we || dut.normal_retire || dut.fwd_wb_en)
                $fatal(1, "WB trap[%0d] wrong or faulty link wrote back", trap_count);
            trap_count = trap_count + 1;
            #1;
            if (dut.pc !== 32'h180 ||
                dut.u_csr_file.mepc !== expected_pc[trap_count-1] ||
                dut.u_csr_file.mcause !== (trap_count == 5 ? 32'd4 : 32'd0) ||
                dut.u_csr_file.mtval !== expected_tval[trap_count-1])
                $fatal(1, "trap[%0d] CSR or redirect wrong", trap_count-1);
        end
    end
endmodule
