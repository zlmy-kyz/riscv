`timescale 1ns / 1ps

// Observe CPU-originated requests without changing the existing RV32I TB.
module tb_cpu_ddr_overlap_fast;
    tb_soc_ddr3_rv32i_fast base();
    integer cpu_both = 0;
    integer ddr_both = 0;
    integer ddr_inst = 0;
    integer ddr_data = 0;
    integer inst_wait = 0;
    integer data_wait = 0;
    integer inst_pending_with_data = 0;
    integer idle_both = 0;
    integer inst_grants = 0;
    reg [31:0] first_inst_addr = 32'b0;
    reg [31:0] first_data_addr = 32'b0;

    always @(posedge base.clk) begin
        if (base.resetn) begin
            if (base.dut.inst_req_valid && base.dut.data_req_valid)
                cpu_both = cpu_both + 1;
            if (base.dut.inst_ddr_req_valid)
                ddr_inst = ddr_inst + 1;
            if (base.dut.data_ddr_req_valid)
                ddr_data = ddr_data + 1;
            if (base.dut.inst_ddr_req_valid && base.dut.data_ddr_req_valid) begin
                ddr_both = ddr_both + 1;
                if (ddr_both == 1) begin
                    first_inst_addr = base.dut.inst_ddr_req_addr;
                    first_data_addr = base.dut.data_ddr_req_addr;
                end
                if (base.dut.g_ddr.u_ddr_bridge.state == 3'd0) begin
                    idle_both = idle_both + 1;
                    if (base.dut.data_ddr_req_ready !== 1'b1 ||
                        base.dut.inst_ddr_req_ready !== 1'b0)
                        $fatal(1, "RESULT: FAIL CPU-originated DDR data priority");
                end
            end
            if (base.dut.inst_ddr_req_valid && base.dut.inst_ddr_req_ready)
                inst_grants = inst_grants + 1;
            if (base.dut.inst_ddr_req_valid && !base.dut.inst_ddr_req_ready)
                inst_wait = inst_wait + 1;
            if (base.dut.data_ddr_req_valid && !base.dut.data_ddr_req_ready)
                data_wait = data_wait + 1;
            if (base.dut.u_cpu.inst_pending && base.dut.data_ddr_req_valid)
                inst_pending_with_data = inst_pending_with_data + 1;
        end
    end

    final begin
        $display("OBS: CPU origin both=%0d DDR both=%0d idle_priority=%0d inst_grants=%0d inst=%0d data=%0d inst_wait=%0d data_wait=%0d pending_inst_with_data=%0d first_inst=%h first_data=%h",
                 cpu_both, ddr_both, idle_both, inst_grants,
                 ddr_inst, ddr_data, inst_wait,
                 data_wait, inst_pending_with_data,
                 first_inst_addr, first_data_addr);
    end
endmodule
