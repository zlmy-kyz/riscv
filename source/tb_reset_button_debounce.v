`timescale 1ns / 1ps

// Functional contract: no release before a full stable-high interval,
// immediate assertion even without clock edges, and one release per press.
module debounce_scenario #(parameter integer CYCLES = 8) (output reg done = 0);
    reg clk = 0, clock_running = 1, keyn = 1;
    wire resetn;
    integer checks = 0, releases = 0;
    reset_button_debounce #(.STABLE_CYCLES(CYCLES)) dut (
        .clk(clk), .keyn(keyn), .resetn_out(resetn)
    );
    always #4 if (clock_running) clk = ~clk;
    always @(posedge resetn) releases = releases + 1;

    task check;
        input condition;
        input [511:0] message;
        begin
            checks = checks + 1;
            if (condition !== 1'b1) $fatal(1, "cycles=%0d %s", CYCLES, message);
        end
    endtask

    task release_and_check;
        integer i;
        begin
            @(negedge clk); #1 keyn = 1;
            for (i = 1; i <= CYCLES + 2; i = i + 1) begin
                @(posedge clk); #1;
                check(resetn === (i == CYCLES + 2), "release interval boundary");
            end
            repeat (CYCLES + 4) begin
                @(posedge clk); #1; check(resetn === 1'b1, "released state must not wrap");
            end
        end
    endtask

    initial begin
        #1 check(resetn === 1'b0, "power-up reset while key is already up");
        #1 keyn = 0;
        #1 check(resetn === 1'b0, "held key resets");
        repeat (3) begin
            @(negedge clk); #1 keyn = 1;
            repeat (2) begin
                @(posedge clk); #1; check(resetn === 1'b0, "short release bounce rejected");
            end
            @(negedge clk); #1 keyn = 0;
            #1 check(resetn === 1'b0, "bounce restarts stable interval");
        end
        release_and_check;
        check(releases == 1, "release bounce must produce only one release");

        // A pulse shorter than one reference-clock period must not be missed.
        @(negedge clk); #1 keyn = 0;
        #0.1 check(resetn === 1'b0, "subcycle press asserts immediately");
        #0.1 keyn = 1;
        repeat (2) begin
            @(posedge clk); #1; check(resetn === 1'b0, "subcycle press holds reset afterward");
        end
        @(negedge clk); #1 keyn = 0;
        release_and_check;
        check(releases == 2, "second qualified release");

        // Reset assertion must work when PLL-derived clocks are stopped.
        @(negedge clk); clock_running = 0;
        #1 keyn = 0;
        #0.1 check(resetn === 1'b0, "press with stopped clock");
        #1 keyn = 1;
        #40 check(resetn === 1'b0, "no release without clock edges");
        keyn = 0; clock_running = 1;
        release_and_check;
        check(releases == 3, "release after clock restarts");
        $display("CHECK: debounce threshold=%0d checks=%0d PASS", CYCLES, checks);
        done = 1;
    end
endmodule

module tb_reset_button_debounce;
    wire d1, d2, d8, d9;
    debounce_scenario #(.CYCLES(1)) c1(d1);
    debounce_scenario #(.CYCLES(2)) c2(d2);
    debounce_scenario #(.CYCLES(8)) c8(d8);
    debounce_scenario #(.CYCLES(9)) c9(d9);

    reg clk = 0, keyn = 1;
    wire resetn_default;
    realtime release_time;
    reset_button_debounce default_filter (
        .clk(clk), .keyn(keyn), .resetn_out(resetn_default)
    );
    always #4 clk = ~clk;
    initial begin
        #1;
        if (resetn_default !== 1'b0) $fatal(1, "default startup reset");
        #19_999_999;
        if (resetn_default !== 1'b0) $fatal(1, "default released before 20 ms");
        @(posedge resetn_default); release_time = $realtime;
        if (release_time < 20_000_000 || release_time > 20_000_024)
            $fatal(1, "incorrect 125 MHz / 20 ms interval: %f ns", release_time);
        if (!(d1 && d2 && d8 && d9)) $fatal(1, "scenario incomplete");
        #1 keyn = 0;
        #0.1;
        if (resetn_default !== 1'b0) $fatal(1, "default immediate assertion");
        $display("RESULT: PASS reset debounce, 1/2/8/9 cycles, real default release=%f ns", release_time);
        $finish;
    end
    initial begin #21_000_000; $fatal(1, "debounce test timeout"); end
endmodule

// These stand-ins belong only to this board-boundary regression. They are
// never included in the PDS design or the full DDR physical-model regression.
`ifdef KEY_RESET_BOARD_STUB
module GTP_INBUFDS(output wire O, input wire I, input wire IB);
    assign O = I;
endmodule

module GTP_CLKBUFG(output wire CLKOUT, input wire CLKIN);
    assign CLKOUT = CLKIN;
endmodule

module soc_ddr3_top #(
    parameter [31:0] RESET_PC = 0, DDR_BASE = 0,
    parameter integer CORE_CLK_HZ = 1, SELFTEST_TIMEOUT_CYCLES = 1
) (
    input wire ddr_ref_clk, resetn, irq_external, irq_software, irq_timer,
    output wire core_clk, ddr_init_done, soc_resetn,
    output wire [31:0] debug_wb_pc, debug_inst, debug_wb_rf_wdata,
    output wire [3:0] debug_wb_rf_we,
    output wire [4:0] debug_wb_rf_wnum,
    output wire led_clk_alive, led_ddr_ready, led_selftest,
    output wire mem_cs_n, mem_rst_n, mem_ck, mem_ck_n, mem_cke,
    output wire mem_ras_n, mem_cas_n, mem_we_n, mem_odt,
    output wire [14:0] mem_a,
    output wire [2:0] mem_ba,
    output wire [1:0] mem_dm,
    inout wire [15:0] mem_dq,
    inout wire [1:0] mem_dqs, mem_dqs_n,
    output wire uart_tx,
    input wire uart_rx
);
    // Model the important dependency: no core clock until reset is released.
    assign core_clk = resetn ? ddr_ref_clk : 1'b0;
    assign soc_resetn = resetn;
endmodule

module tb_board_key_reset;
    reg ref_clk = 0, keyn = 0;
    wire soc_resetn;
    integer releases = 0, i;
    board_top #(.KEY_DEBOUNCE_CYCLES(8)) dut (
        .ddr_ref_clk_p(ref_clk), .ddr_ref_clk_n(~ref_clk), .resetn(keyn),
        .uart_rx(1'b1), .uart_tx()
    );
    always #4 ref_clk = ~ref_clk;
    always @(posedge dut.u_soc.resetn) releases = releases + 1;
    initial begin
        #10;
        if (dut.core_clk !== 1'b0 || dut.u_soc.resetn !== 1'b0)
            $fatal(1, "board must stay reset with core clock stopped");
        repeat (3) begin
            @(negedge ref_clk); #1 keyn = 1;
            repeat (7) @(posedge ref_clk);
            #1;
            if (dut.u_soc.resetn !== 1'b0) $fatal(1, "board release bounce leaked");
            @(negedge ref_clk); #1 keyn = 0;
        end
        @(negedge ref_clk); #1 keyn = 1;
        for (i = 1; i <= 10; i = i + 1) begin
            @(posedge ref_clk); #1;
            if (dut.u_soc.resetn !== (i == 10)) $fatal(1, "board debounce boundary i=%0d", i);
        end
        if (releases != 1 || dut.core_clk !== 1'b1) $fatal(1, "board startup deadlock or repeated release");
        @(negedge ref_clk); #1 keyn = 0;
        #0.1;
        if (dut.u_soc.resetn !== 1'b0 || dut.core_clk !== 1'b0) $fatal(1, "board asynchronous press");
        $display("RESULT: PASS board KEY0 filtering, reference clock prevents reset deadlock");
        $finish;
    end
    initial begin #10_000; $fatal(1, "board debounce timeout"); end
endmodule
`endif
