`timescale 1ns / 1ps

// Observe the reusable DDR diagnostic record while the existing fast SoC TB
// performs its normal loader-count, DDR-fetch, tohost and timeout checks.
module tb_ddr_selftest_fast;
    tb_soc_ddr3_rv32i_fast base();
    wire led_clk_alive, led_ddr_ready, led_selftest;
    reg [1:0] previous_status = 0;
    reg saw_run = 0;
    soc_ddr3_leds #(.CORE_CLK_HZ(16), .SELFTEST_TIMEOUT_CYCLES(200000)) leds (
        .clk(base.clk), .resetn(base.resetn), .soc_resetn(base.resetn),
        .selftest_status(base.dut.selftest_status),
        .led_clk_alive(led_clk_alive), .led_ddr_ready(led_ddr_ready),
        .led_selftest(led_selftest)
    );

    always @(negedge base.clk) begin
        if (!base.resetn) begin
            previous_status = 0;
            saw_run = 0;
        end else if (base.dut.selftest_status != previous_status) begin
            case (base.dut.selftest_status)
                2'd1: begin
                    saw_run = 1;
                    $display("CHECK: MMIO selftest RUN");
                end
                2'd2: begin
                    if (!saw_run || !led_ddr_ready || !led_selftest || leds.timed_out)
                        $fatal(1, "RESULT: FAIL MMIO PASS/LED sequence");
                    $display("CHECK: MMIO selftest PASS LED=1");
                end
                2'd3: begin
                    if (!saw_run || leds.timed_out)
                        $fatal(1, "RESULT: FAIL MMIO FAIL sequence");
                    $display("CHECK: MMIO selftest FAIL");
                end
                default: $fatal(1, "RESULT: FAIL unexpected MMIO status");
            endcase
            previous_status = base.dut.selftest_status;
        end
    end

    always @(posedge base.clk) begin
        if (base.resetn && base.dut.data_req_valid &&
            base.dut.data_req_ready && base.dut.data_req_write) begin
            case (base.dut.data_req_addr)
                32'h4000_1004: $display("DIAG: address=%08x", base.dut.data_req_wdata);
                32'h4000_1008: $display("DIAG: expected=%08x", base.dut.data_req_wdata);
                32'h4000_100c: $display("DIAG: observed=%08x", base.dut.data_req_wdata);
                32'h4000_1010: $display("DIAG: phase=%0d", base.dut.data_req_wdata);
                32'h4000_1014: $display("DIAG: checks=%0d", base.dut.data_req_wdata);
                default: ;
            endcase
        end
    end
endmodule
