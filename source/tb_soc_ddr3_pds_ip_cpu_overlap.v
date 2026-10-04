`timescale 1ns / 10fs

// Use the real on-chip ROM/RAM and DDR3 physical model. The requests remain
// CPU-generated: only the instruction ready handshake is held for a few
// cycles after fetching a DDR load/store instruction.
module tb_soc_ddr3_pds_ip_cpu_overlap;
    tb_soc_ddr3_pds_ip base();
    integer waited;
    reg saw_overlap = 1'b0;

    initial begin
        wait (base.saw_ddr_fetch);
        begin : find_memory_instruction
            forever begin
                @(negedge base.core_clk);
                if (base.dut.u_soc.inst_ddr_rsp_valid &&
                    (base.dut.u_soc.inst_ddr_rsp_rdata[6:0] == 7'h03 ||
                     base.dut.u_soc.inst_ddr_rsp_rdata[6:0] == 7'h23)) begin
                    force base.dut.u_soc.inst_ddr_req_ready = 1'b0;
                    $display("CHECK: held next CPU fetch after DDR memory instruction at pc=%h",
                             base.dut.u_soc.u_cpu.inst_pending_pc);
                    disable find_memory_instruction;
                end
            end
        end
        begin : wait_for_overlap
            for (waited = 0; waited < 12; waited = waited + 1) begin
                @(negedge base.core_clk);
                if (base.dut.u_soc.inst_ddr_req_valid &&
                    base.dut.u_soc.data_ddr_req_valid) begin
                    saw_overlap = 1'b1;
                    if (base.dut.u_soc.inst_req_valid !== 1'b1 ||
                        base.dut.u_soc.data_req_valid !== 1'b1)
                        $fatal(1, "RESULT: FAIL DDR requests were not CPU-originated");
                    release base.dut.u_soc.inst_ddr_req_ready;
                    #1;
                    if (base.dut.u_soc.data_ddr_req_ready !== 1'b1 ||
                        base.dut.u_soc.inst_ddr_req_ready !== 1'b0)
                        $fatal(1, "RESULT: FAIL CPU-originated DDR data priority");
                    $display("CHECK: CPU-origin DDR overlap inst=%h data=%h after %0d held cycles",
                             base.dut.u_soc.inst_ddr_req_addr,
                             base.dut.u_soc.data_ddr_req_addr, waited + 1);
                    disable wait_for_overlap;
                end
            end
            if (!saw_overlap) begin
                release base.dut.u_soc.inst_ddr_req_ready;
                $fatal(1, "RESULT: FAIL no CPU DDR overlap after fetch hold");
            end
        end
    end

    always @(posedge base.core_clk) begin
        if (saw_overlap && base.soc_resetn && base.saw_ddr_fetch &&
            base.dut.u_soc.data_req_valid && base.dut.u_soc.data_req_ready &&
            base.dut.u_soc.data_req_write &&
            base.dut.u_soc.data_req_addr == base.tohost_addr &&
            base.dut.u_soc.data_req_wdata === 32'd1)
            $display("CHECK: CPU-origin DDR contention recovered; tohost=1");
    end
endmodule
