`timescale 1ns / 10fs

// Reuse the real on-chip IP/DDR3 physical-model test unchanged. Insert one
// external reset while the CPU loader writes to DDR, then require the loader
// and RV32I test to run again after DDR retraining.
module tb_soc_ddr3_pds_ip_reset;
    tb_soc_ddr3_pds_ip base();

    integer overlap_cycles = 0;
    integer priority_cycles = 0;
    reg reset_done = 1'b0;

    always @(posedge base.core_clk) begin
        if (base.soc_resetn) begin
            if (!base.ddr_init_done)
                $fatal(1, "RESULT: FAIL CPU released before DDR reinitialization");
            if (base.dut.u_soc.inst_ddr_req_valid &&
                base.dut.u_soc.data_ddr_req_valid) begin
                overlap_cycles = overlap_cycles + 1;
                if (base.dut.u_soc.g_ddr.u_ddr_bridge.state == 3'd0) begin
                    priority_cycles = priority_cycles + 1;
                    if (base.dut.u_soc.data_ddr_req_ready !== 1'b1 ||
                        base.dut.u_soc.inst_ddr_req_ready !== 1'b0)
                        $fatal(1, "RESULT: FAIL DDR data priority during overlap");
                end
            end
        end
    end

    initial begin
        wait (base.loader_writes >= 10);
        @(negedge base.ddr_ref_clk);
        $display("CHECK: loader wrote %0d DDR words; assert external reset at %t",
                 base.loader_writes, $time);
        base.resetn = 1'b0;
        #1000;
        if (base.soc_resetn !== 1'b0)
            $fatal(1, "RESULT: FAIL SoC reset was not asserted");
        base.resetn = 1'b1;
        @(posedge base.soc_resetn);
        if (base.ddr_init_done !== 1'b1)
            $fatal(1, "RESULT: FAIL SoC released before DDR retraining");
        if (base.loader_writes !== 0 || base.saw_ddr_fetch !== 1'b0 ||
            base.dut.u_soc.g_ddr.u_ddr_bridge.state !== 3'd0)
            $fatal(1, "RESULT: FAIL loader/bridge state was not cleared by reset");
        reset_done = 1'b1;
        $display("CHECK: DDR retrained and CPU released after reset at %t", $time);
        @(posedge base.saw_ddr_fetch);
        $display("CHECK: loader recopied %0d words and refetched DDR after reset", base.loader_writes);
        if (base.loader_writes !== base.expected_writes)
            $fatal(1, "RESULT: FAIL loader count after reset");
        $display("CHECK: DDR overlap cycles=%0d idle data-priority cycles=%0d",
                 overlap_cycles, priority_cycles);
    end

    always @(posedge base.core_clk) begin
        if (reset_done && base.soc_resetn && base.saw_ddr_fetch &&
            base.dut.u_soc.data_req_valid && base.dut.u_soc.data_req_ready &&
            base.dut.u_soc.data_req_write &&
            base.dut.u_soc.data_req_addr == base.tohost_addr) begin
            if (base.dut.u_soc.data_req_wdata !== 32'd1)
                $fatal(1, "RESULT: FAIL RV32I tohost after reset");
            $display("CHECK: warm reset completed; tohost=1 overlap=%0d priority=%0d",
                     overlap_cycles, priority_cycles);
        end
    end
endmodule
