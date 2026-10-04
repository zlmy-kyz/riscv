`timescale 1ns/1ps

// 执行 misaligned_data_step8.S：handler 每次保存 cause/PC/有效地址并跳过故障指令。
module tb_misaligned_data_step8;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));
    wire [31:0] trace_irq_raw = 32'b0;
    `include "difftest/tb/arch_trace.vh"

    reg [31:0] expected_pc [0:10];
    reg [31:0] expected_addr [0:10];
    reg [4:0] expected_cause [0:10];
    integer trap_count = 0;
    integer ex_fault_count = 0;
    integer bad_store_count = 0;
    integer i;

    initial begin
        expected_pc[0] = 32'h34; expected_addr[0] = 32'h301;
        expected_pc[1] = 32'h38; expected_addr[1] = 32'h303;
        expected_pc[2] = 32'h3c; expected_addr[2] = 32'h301;
        expected_pc[3] = 32'h40; expected_addr[3] = 32'h302;
        expected_pc[4] = 32'h44; expected_addr[4] = 32'h303;
        expected_pc[5] = 32'h48; expected_addr[5] = 32'h301;
        expected_pc[6] = 32'h4c; expected_addr[6] = 32'h303;
        expected_pc[7] = 32'h50; expected_addr[7] = 32'h301;
        expected_pc[8] = 32'h54; expected_addr[8] = 32'h302;
        expected_pc[9] = 32'h58; expected_addr[9] = 32'h303;
        expected_pc[10] = 32'h68; expected_addr[10] = 32'h1301;
        for (i = 0; i < 11; i = i + 1)
            expected_cause[i] = (i < 5 || i == 10) ? 5'd4 : 5'd6;
    end

    initial begin
        #40000;
        $fatal(1, "data-misaligned timeout trap=%0d ex=%0d", trap_count, ex_fault_count);
    end

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (trap_count == 11 && dut.u_regfile.rf[14] == 32'h7b);
        repeat (12) @(posedge clk);
        #1;
        if (trap_count != 11 || ex_fault_count != 11 || bad_store_count != 0)
            $fatal(1, "unexpected trap/EX/store count %0d/%0d/%0d",
                   trap_count, ex_fault_count, bad_store_count);
        for (i = 0; i < 11; i = i + 1) begin
            if (dut.the_instance_name.mem[128 + 3*i] !== {27'b0, expected_cause[i]} ||
                dut.the_instance_name.mem[129 + 3*i] !== expected_pc[i] ||
                dut.the_instance_name.mem[130 + 3*i] !== expected_addr[i])
                $fatal(1, "handler log[%0d] wrong cause=%h pc=%h addr=%h",
                       i, dut.the_instance_name.mem[128 + 3*i],
                       dut.the_instance_name.mem[129 + 3*i],
                       dut.the_instance_name.mem[130 + 3*i]);
        end
        if (dut.the_instance_name.mem[192] !== 32'h007b_007b ||
            dut.the_instance_name.mem[193] !== 32'h7b00_007b ||
            dut.the_instance_name.mem[194] !== 32'h0000_007b ||
            dut.u_regfile.rf[2] !== 32'h3f0 ||
            dut.u_regfile.rf[3] !== 32'h33 ||
            dut.u_regfile.rf[4] !== 32'h44 ||
            dut.u_regfile.rf[5] !== 32'h55 ||
            dut.u_regfile.rf[6] !== 32'h56 ||
            dut.u_regfile.rf[7] !== 32'h57 ||
            dut.u_regfile.rf[8] !== 32'h7b ||
            dut.u_regfile.rf[9] !== 32'h7b ||
            dut.u_regfile.rf[10] !== 32'h7b ||
            dut.u_regfile.rf[11] !== 32'h7b ||
            dut.u_regfile.rf[12] !== 32'h7b ||
            dut.u_regfile.rf[13] !== 32'h7b ||
            dut.u_regfile.rf[14] !== 32'h7b ||
            dut.u_regfile.rf[15] !== 32'h5f ||
            dut.u_regfile.rf[17] !== 32'h1300 ||
            dut.u_regfile.rf[20] !== 32'h284 ||
            dut.u_csr_file.mepc !== 32'h6c ||
            dut.u_csr_file.mcause !== 32'd4 ||
            dut.u_csr_file.mtval !== 32'h1301)
            $fatal(1, "valid access or fault suppression final state wrong");
        $display("RESULT: PASS misaligned LH/LHU/LW/SH/SW, precise RAM/GPR suppression, aligned and byte access");
        $finish;
    end

    always @(posedge clk) if (resetn) begin
        if (dut.id_ex_valid && dut.ex_data_misaligned) begin
            ex_fault_count = ex_fault_count + 1;
            if (!dut.ex_exc_valid ||
                dut.ex_exc_cause !== (dut.id_ex_wmem ? 5'd6 : 5'd4) ||
                dut.ex_exc_tval !== dut.data_sram_addr)
                $fatal(1, "EX misalignment payload wrong pc=%h", dut.id_ex_pc);
            if (dut.id_ex_wmem &&
                (dut.ex_store_commit || dut.the_instance_name.wr_en ||
                 dut.data_sram_we !== 4'b0000))
                $fatal(1, "faulty store wrote RAM in EX pc=%h", dut.id_ex_pc);
        end
        if (dut.ex_mem_valid && dut.ex_mem_exc_valid && dut.ex_mem_i_l &&
            (dut.fwd_mem_en || dut.mem_fwd_data !== 32'b0))
            $fatal(1, "faulty load supplied MEM forwarding/writeback data");
        if (dut.the_instance_name.wr_en &&
            (dut.data_sram_addr == 32'h301 ||
             dut.data_sram_addr == 32'h303 ||
             (dut.data_sram_addr == 32'h302 && dut.id_ex_sw)))
            bad_store_count = bad_store_count + 1;
        if (dut.sync_trap_event) begin
            if (trap_count >= 11) $fatal(1, "unexpected additional data trap");
            if (!dut.mem_wb_exc_valid ||
                dut.mem_wb_pc !== expected_pc[trap_count] ||
                dut.wb_trap_cause !== expected_cause[trap_count] ||
                dut.wb_trap_tval !== expected_addr[trap_count] ||
                dut.rf_we || dut.csr_commit || dut.normal_retire || dut.fwd_wb_en ||
                dut.the_instance_name.mem[192] !== 32'h7b ||
                dut.the_instance_name.mem[193] !== 32'h7b)
                $fatal(1, "WB trap[%0d] state or target/neighbor sentinel wrong", trap_count);
            trap_count = trap_count + 1;
            #1;
            if (dut.pc !== 32'h180 ||
                dut.u_csr_file.mepc !== expected_pc[trap_count-1] ||
                dut.u_csr_file.mcause !== {27'b0, expected_cause[trap_count-1]} ||
                dut.u_csr_file.mtval !== expected_addr[trap_count-1])
                $fatal(1, "trap[%0d] CSR or redirect wrong", trap_count-1);
        end
    end
endmodule
