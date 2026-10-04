`timescale 1ns/1ps

// 由 illegal_step7.S 生成 ROM，handler 每次记录 mcause/mepc/mtval 并跳过故障指令。
module tb_illegal_step7;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));
    wire [31:0] trace_irq_raw = 32'b0;
    `include "difftest/tb/arch_trace.vh"

    reg [31:0] expected_pc [0:7];
    reg [31:0] expected_inst [0:7];
    integer trap_count = 0;
    integer i;

    initial begin
        expected_pc[0] = 32'h2c; expected_inst[0] = 32'h0000_0000;
        expected_pc[1] = 32'h30; expected_inst[1] = 32'h0000_0001;
        expected_pc[2] = 32'h34; expected_inst[2] = 32'h0200_01b3;
        expected_pc[3] = 32'h38; expected_inst[3] = 32'h0210_1213;
        expected_pc[4] = 32'h3c; expected_inst[4] = 32'h0000_100f;
        expected_pc[5] = 32'h40; expected_inst[5] = 32'h0000_200f;
        expected_pc[6] = 32'h44; expected_inst[6] = 32'hf154_a573;
        expected_pc[7] = 32'h48; expected_inst[7] = 32'h3060_25f3;
    end

    initial begin
        #30000;
        $fatal(1, "illegal instruction timeout traps=%0d", trap_count);
    end

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (trap_count == 8 && dut.u_regfile.rf[14] == 32'd1);
        repeat (12) @(posedge clk);
        #1;
        if (trap_count != 8) $fatal(1, "bubble or valid hint generated extra trap");
        for (i = 0; i < 8; i = i + 1) begin
            if (dut.the_instance_name.mem[128 + 3*i] !== 32'd2 ||
                dut.the_instance_name.mem[129 + 3*i] !== expected_pc[i] ||
                dut.the_instance_name.mem[130 + 3*i] !== expected_inst[i])
                $fatal(1, "handler log[%0d] wrong cause=%h pc=%h tval=%h",
                       i, dut.the_instance_name.mem[128 + 3*i],
                       dut.the_instance_name.mem[129 + 3*i],
                       dut.the_instance_name.mem[130 + 3*i]);
        end
        if (dut.u_regfile.rf[3] !== 32'h44 ||
            dut.u_regfile.rf[4] !== 32'h77 ||
            dut.u_regfile.rf[8] !== 32'h180 ||
            dut.u_regfile.rf[10] !== 32'h123 ||
            dut.u_regfile.rf[11] !== 32'h234 ||
            dut.u_regfile.rf[12] !== 32'd0 ||
            dut.u_regfile.rf[13] !== 32'h55 ||
            dut.u_regfile.rf[14] !== 32'd1 ||
            dut.u_regfile.rf[20] !== 32'h260 ||
            dut.u_csr_file.mscratch !== 32'h55 ||
            dut.u_csr_file.mstatus !== 32'h1880 ||
            dut.u_csr_file.mepc !== 32'h4c ||
            dut.u_csr_file.mcause !== 32'd2 ||
            dut.u_csr_file.mtval !== expected_inst[7])
            $fatal(1, "illegal/valid instruction final state wrong");
        $display("RESULT: PASS illegal instruction/CSR trap, mtval, FENCE and WFI");
        $finish;
    end

    always @(posedge clk) if (resetn) begin
        if (dut.id_fire && dut.if_id_pc == 32'h50) begin
            if (!dut.inst_fence || !dut.serial_candidate ||
                dut.gf_we || dut.uses_rs1 || dut.uses_rs2)
                $fatal(1, "FENCE used reserved rd/rs1 as GPR operands");
        end
        if (dut.id_fire && dut.if_id_pc == 32'h54) begin
            if (!dut.inst_wfi || !dut.serial_candidate || dut.id_exc_valid)
                $fatal(1, "WFI not legal serial NOP");
        end
        if (dut.sync_trap_event) begin
            if (trap_count >= 8) $fatal(1, "unexpected additional trap");
            if (dut.mem_wb_pc !== expected_pc[trap_count] ||
                dut.mem_wb_inst !== expected_inst[trap_count] ||
                dut.wb_trap_cause !== 5'd2 ||
                dut.wb_trap_tval !== expected_inst[trap_count] ||
                dut.rf_we || dut.csr_commit || dut.normal_retire)
                $fatal(1, "trap[%0d] payload or illegal side effect wrong", trap_count);
            if (trap_count < 6) begin
                if (!dut.mem_wb_exc_valid || dut.wb_csr_illegal)
                    $fatal(1, "ID illegal instruction was not carried as fault item");
            end else begin
                if (dut.mem_wb_exc_valid || !dut.wb_csr_illegal)
                    $fatal(1, "WB illegal CSR did not generate cause 2");
            end
            trap_count = trap_count + 1;
            #1;
            if (dut.pc !== 32'h180 ||
                dut.u_csr_file.mcause !== 32'd2 ||
                dut.u_csr_file.mepc !== expected_pc[trap_count-1] ||
                dut.u_csr_file.mtval !== expected_inst[trap_count-1])
                $fatal(1, "trap[%0d] CSR update/redirect wrong", trap_count-1);
        end
    end
endmodule
