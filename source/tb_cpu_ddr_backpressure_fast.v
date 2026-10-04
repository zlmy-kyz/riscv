`timescale 1ns / 1ps

// Delay an actual CPU fetch request briefly after a DDR load/store fetch,
// allowing that instruction's data request to meet the held next fetch.
module tb_cpu_ddr_backpressure_fast;
    tb_soc_ddr3_rv32i_fast base();
    integer waited;
    reg saw_overlap = 1'b0;

    initial begin
        wait (base.saw_ddr_fetch);
        begin : find_memory_instruction
            forever begin
                @(negedge base.clk);
                if (base.dut.inst_ddr_rsp_valid &&
                    (base.dut.inst_ddr_rsp_rdata[6:0] == 7'h03 ||
                     base.dut.inst_ddr_rsp_rdata[6:0] == 7'h23)) begin
                    force base.dut.inst_ddr_req_ready = 1'b0;
                    $display("CHECK: held next CPU fetch after DDR memory instruction at pc=%h",
                             base.dut.u_cpu.inst_pending_pc);
                    disable find_memory_instruction;
                end
            end
        end
        begin : wait_for_overlap
            for (waited = 0; waited < 12; waited = waited + 1) begin
                @(negedge base.clk);
                if (base.dut.inst_ddr_req_valid && base.dut.data_ddr_req_valid) begin
                    saw_overlap = 1'b1;
                    if (base.dut.inst_req_valid !== 1'b1 ||
                        base.dut.data_req_valid !== 1'b1)
                        $fatal(1, "RESULT: FAIL DDR requests were not simultaneously presented by CPU");
                    release base.dut.inst_ddr_req_ready;
                    #1;
                    if (base.dut.data_ddr_req_ready !== 1'b1 ||
                        base.dut.inst_ddr_req_ready !== 1'b0)
                        $fatal(1, "RESULT: FAIL CPU DDR overlap priority");
                    $display("CHECK: CPU-origin DDR overlap inst=%h data=%h after %0d held cycles",
                             base.dut.inst_ddr_req_addr,
                             base.dut.data_ddr_req_addr, waited + 1);
                    disable wait_for_overlap;
                end
            end
            if (!saw_overlap) begin
                release base.dut.inst_ddr_req_ready;
                $fatal(1, "RESULT: FAIL no CPU DDR overlap after fetch hold");
            end
        end
    end
endmodule
