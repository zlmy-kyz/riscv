`timescale 1ns / 10fs

// PDS full path: RV32 CPU -> generated on-chip ROM/RAM IP -> two buses ->
// DDR bridge -> Pango DDR3 IP -> vendor x16 DDR3 physical model.
// The ROM and RAM modules are compiled from their generated IP files.
module tb_board_top_selftest;
    // Matches the generated x16/4Gb example model's ADDR_BITS value.
    localparam ADDR_BITS = 16;

    reg ddr_ref_clk = 1'b0;
    reg resetn = 1'b1;
    reg grs_n = 1'b0;
    wire core_clk;
    wire ddr_init_done;
    wire soc_resetn;
    wire led_clk_alive, led_ddr_ready, led_selftest;
    wire [31:0] debug_wb_pc;
    wire [3:0] debug_wb_rf_we;
    wire [4:0] debug_wb_rf_wnum;
    wire [31:0] debug_wb_rf_wdata;
    wire [31:0] debug_inst;

    wire mem_cs_n, mem_rst_n, mem_ck, mem_ck_n, mem_cke;
    wire mem_ras_n, mem_cas_n, mem_we_n, mem_odt;
    wire [14:0] mem_a;
    wire [2:0] mem_ba;
    wire [1:0] mem_dqs, mem_dqs_n, mem_dm;
    wire [15:0] mem_dq;

    // Pango primitive models refer to this exact top-level instance name.
    GTP_GRS GRS_INST (.GRS_N(grs_n));

`ifdef DDR_RV32I
    board_top #(.KEY_DEBOUNCE_CYCLES(8), .RESET_PC(32'h0000_0000),
                   .DDR_BASE(32'h8000_0000)) dut (
`else
    board_top #(.KEY_DEBOUNCE_CYCLES(8), .RESET_PC(32'h8000_0000)) dut (
`endif
        .ddr_ref_clk_p(ddr_ref_clk), .ddr_ref_clk_n(~ddr_ref_clk),
        .resetn(resetn),
        .uart_rx(1'b1), .uart_tx(),
        .led_clk_alive(led_clk_alive),
        .led_ddr_ready(led_ddr_ready),
        .led_selftest(led_selftest),
        .mem_cs_n(mem_cs_n),
        .mem_rst_n(mem_rst_n),
        .mem_ck(mem_ck),
        .mem_ck_n(mem_ck_n),
        .mem_cke(mem_cke),
        .mem_ras_n(mem_ras_n),
        .mem_cas_n(mem_cas_n),
        .mem_we_n(mem_we_n),
        .mem_odt(mem_odt),
        .mem_a(mem_a),
        .mem_ba(mem_ba),
        .mem_dqs(mem_dqs),
        .mem_dqs_n(mem_dqs_n),
        .mem_dq(mem_dq),
        .mem_dm(mem_dm)
    );

    assign core_clk = dut.core_clk;
    assign ddr_init_done = dut.ddr_init_done;
    assign soc_resetn = dut.soc_resetn;
    assign debug_wb_pc = dut.debug_wb_pc;
    assign debug_inst = dut.debug_inst;
    assign debug_wb_rf_we = dut.debug_wb_rf_we;
    assign debug_wb_rf_wnum = dut.debug_wb_rf_wnum;
    assign debug_wb_rf_wdata = dut.debug_wb_rf_wdata;

    integer key_release_count = 0;
    realtime key_last_release = 0;
    always @(posedge resetn) key_last_release = $realtime;
    always @(posedge dut.key_resetn) begin
        key_release_count = key_release_count + 1;
        if ($realtime - key_last_release < 64.0)
            $fatal(1, "board reset escaped release bounce");
    end
    initial begin : board_clock_checks
        realtime t0, t1;
        repeat (4) begin
            @(posedge ddr_ref_clk); #0.01;
            if (dut.ddr_ref_clk !== ddr_ref_clk) $fatal(1, "board P buffer");
            @(negedge ddr_ref_clk); #0.01;
            if (dut.ddr_ref_clk !== ddr_ref_clk) $fatal(1, "board N buffer");
        end
        if ({dut.u_soc.irq_external, dut.u_soc.irq_software,
             dut.u_soc.irq_timer} !== 3'b000) $fatal(1, "board IRQ tie-off");
        wait (soc_resetn);
        @(posedge core_clk); t0 = $realtime;
        @(posedge core_clk); t1 = $realtime;
        if (t1-t0 < 10.65 || t1-t0 > 10.68) $fatal(1, "board core period %f", t1-t0);
        @(posedge mem_ck); t0 = $realtime;
        @(posedge mem_ck); t1 = $realtime;
        if (t1-t0 < 2.65 || t1-t0 > 2.68) $fatal(1, "board DDR CK period %f", t1-t0);
        $display("CHECK: board_top differential buffer, IRQ=0, core=93.75MHz, DDR=750Mbps");
    end

    // Same command/address flight delay and DDR3 model as the generated
    // example_design/bench/ddr3_tb/ddr3_test_top_tb.v (one x16 device).
    wire [ADDR_BITS-1:0] mem_addr =
        {{(ADDR_BITS-15){1'b0}}, mem_a};
    wire [1:0] mem_rst_n_dly, mem_ck_dly, mem_ck_n_dly, mem_cs_n_dly;
    wire [1:0] mem_ras_n_dly, mem_cas_n_dly, mem_we_n_dly;
    wire [1:0] mem_cke_dly, mem_odt_dly;
    wire [2*ADDR_BITS-1:0] mem_addr_dly;
    wire [5:0] mem_ba_dly;

    assign #0.15 mem_rst_n_dly = {mem_rst_n, mem_rst_n};
    assign #0.15 mem_ck_dly    = {mem_ck, mem_ck};
    assign #0.15 mem_ck_n_dly  = {mem_ck_n, mem_ck_n};
    assign #0.15 mem_cs_n_dly  = {mem_cs_n, mem_cs_n};
    assign #0.15 mem_ras_n_dly = {mem_ras_n, mem_ras_n};
    assign #0.15 mem_cas_n_dly = {mem_cas_n, mem_cas_n};
    assign #0.15 mem_we_n_dly  = {mem_we_n, mem_we_n};
    assign #0.15 mem_cke_dly   = {mem_cke, mem_cke};
    assign #0.15 mem_odt_dly   = {mem_odt, mem_odt};
    assign #0.15 mem_addr_dly  = {mem_addr, mem_addr};
    assign #0.15 mem_ba_dly    = {mem_ba, mem_ba};

`ifdef DDR_RV32I
    // Keep the physical checks, but omit per-transfer INFO traces for the
    // long RV32I suite. Timing warnings and errors remain enabled.
    ddr3_mem #(.DEBUG(0)) mem_core (
`else
    ddr3_mem mem_core (
`endif
        .rst_n(mem_rst_n_dly[0]),
        .ck(mem_ck_dly[0]),
        .ck_n(mem_ck_n_dly[0]),
        .cs_n(mem_cs_n_dly[0]),
        .ras_n(mem_ras_n_dly[0]),
        .cas_n(mem_cas_n_dly[0]),
        .we_n(mem_we_n_dly[0]),
        .addr(mem_addr_dly[14:0]),
        .ba(mem_ba_dly[2:0]),
        .odt(mem_odt_dly[0]),
        .cke(mem_cke_dly[0]),
        .dq(mem_dq),
        .dqs(mem_dqs),
        .dqs_n(mem_dqs_n),
        .dm_tdqs(mem_dm),
        .tdqs_n()
    );

    always #4 ddr_ref_clk = ~ddr_ref_clk; // Current generated IP: 125 MHz

    initial begin
        #5 grs_n = 1'b1;
    end

    initial begin
        #10 resetn = 1'b0;
        #50 resetn = 1'b1;
        #20 resetn = 1'b0;
        #5 resetn = 1'b1;
        #25 resetn = 1'b0;
        #3 resetn = 1'b1;
    end

`ifdef DDR_RV32I
    string test_name;
    reg [31:0] tohost_addr;
    integer expected_writes;
    integer test_cycle = 0;
    integer loader_writes = 0;
    reg saw_ddr_fetch = 1'b0;
    reg check_selftest_led;
    reg saw_selftest_run = 1'b0;
    reg [1:0] previous_selftest_status = 2'd0;
    initial begin
        check_selftest_led = $test$plusargs("CHECK_SELFTEST_LED");
        if (!$value$plusargs("TEST=%s", test_name))
            $fatal(1, "missing +TEST=<name>");
        if (!$value$plusargs("TOHOST=%h", tohost_addr))
            $fatal(1, "missing +TOHOST=<hex address>");
        if (!$value$plusargs("EXPECTED_WRITES=%d", expected_writes))
            $fatal(1, "missing +EXPECTED_WRITES=<decimal count>");
    end

    always @(negedge core_clk) begin
        if (!soc_resetn) begin
            saw_selftest_run = 1'b0;
            previous_selftest_status = 2'd0;
        end else if (check_selftest_led && dut.u_soc.selftest_status != previous_selftest_status) begin
            case (dut.u_soc.selftest_status)
                2'd1: begin
                    saw_selftest_run = 1'b1;
                    $display("CHECK: MMIO selftest RUN");
                end
                2'd2: begin
                    if (!saw_selftest_run || !led_ddr_ready || !led_selftest || dut.u_soc.u_leds.timed_out)
                        $fatal(1, "RESULT: FAIL selftest PASS/LED sequence");
                    $display("CHECK: MMIO selftest PASS LED=1");
                end
                2'd3: begin
                    if (!saw_selftest_run)
                        $fatal(1, "RESULT: FAIL selftest FAIL without RUN");
                    $display("CHECK: MMIO selftest FAIL");
                end
                default: $fatal(1, "RESULT: FAIL unexpected selftest status");
            endcase
            previous_selftest_status = dut.u_soc.selftest_status;
        end
    end

    always @(posedge core_clk) begin
        if (!soc_resetn) begin
            test_cycle <= 0;
            loader_writes <= 0;
            saw_ddr_fetch <= 1'b0;
        end else begin
            test_cycle <= test_cycle + 1;
            if (!ddr_init_done) begin
                $display("RESULT: FAIL %s CPU released before DDR init", test_name);
                $finish;
            end
            if ((dut.u_soc.u_soc.inst_rsp_valid && dut.u_soc.u_soc.inst_rsp_error) ||
                (dut.u_soc.u_soc.data_rsp_valid && dut.u_soc.u_soc.data_rsp_error)) begin
                $display("RESULT: FAIL %s bus access fault pc=%h", test_name,
                         dut.u_soc.u_soc.u_cpu.pc);
                $finish;
            end
            if (dut.u_soc.u_soc.data_req_valid && dut.u_soc.u_soc.data_req_ready &&
                dut.u_soc.u_soc.data_req_write &&
                dut.u_soc.u_soc.data_req_addr >= 32'h8000_0000 &&
                !saw_ddr_fetch)
                loader_writes <= loader_writes + 1;

            if (dut.u_soc.u_soc.inst_req_valid && dut.u_soc.u_soc.inst_req_ready &&
                dut.u_soc.u_soc.inst_req_addr == 32'h8000_0000 && !saw_ddr_fetch) begin
                if (loader_writes != expected_writes) begin
                    $display("RESULT: FAIL %s loader copied %0d words, expected %0d",
                             test_name, loader_writes, expected_writes);
                    $finish;
                end
                saw_ddr_fetch <= 1'b1;
                $display("CHECK: %s CPU copied %0d words then fetched from DDR",
                         test_name, loader_writes);
            end

            if (saw_ddr_fetch &&
                dut.u_soc.u_soc.data_req_valid && dut.u_soc.u_soc.data_req_ready &&
                dut.u_soc.u_soc.data_req_write &&
                dut.u_soc.u_soc.data_req_addr == tohost_addr) begin
                if (check_selftest_led && (!saw_selftest_run ||
                    (dut.u_soc.u_soc.data_req_wdata == 32'd1 &&
                     (dut.u_soc.selftest_status != 2'd2 || !led_selftest)) ||
                    (dut.u_soc.u_soc.data_req_wdata == 32'd2 && dut.u_soc.selftest_status != 2'd3)))
                    $fatal(1, "RESULT: FAIL tohost/MMIO selftest mismatch");
                if (dut.u_soc.u_soc.data_req_wdata === 32'd1) begin
                    $display("RESULT: PASS %s DDR RV32I tohost=1 cycles=%0d",
                             test_name, test_cycle);
                end else begin
                    $display("RESULT: FAIL %s DDR RV32I tohost=%h failed_test=%0d cycles=%0d",
                             test_name, dut.u_soc.u_soc.data_req_wdata,
                             dut.u_soc.u_soc.data_req_wdata >> 1, test_cycle);
                end
                $finish;
            end
        end
    end

    initial begin
        #5000000;
        $display("RESULT: FAIL %s DDR RV32I timeout init=%b fetch=%b copied=%0d pc=%h",
                 test_name, ddr_init_done, saw_ddr_fetch, loader_writes,
                 dut.u_soc.u_soc.u_cpu.pc);
        $finish;
    end
`elsif DDR_REGRESSION
    // Each read is checked at CPU retirement, not at a bridge-internal signal.
    // The checks cover all four 32-bit lanes of a 128-bit beat and the next beat.
    reg [4:0]  saw_word_stores = 5'b0;
    reg [2:0]  saw_masked_stores = 3'b0;
    reg [3:0]  saw_code_stores = 4'b0;
    reg [13:0] saw_load_checks = 14'b0;
    reg [1:0]  saw_ddr_fetch_checks = 2'b0;
    reg [13:0] load_check_bit;
    reg [31:0] load_expected;

    always @* begin
        load_check_bit = 14'b0;
        load_expected = 32'b0;
        case (debug_wb_pc)
            32'h8000_002c: begin load_check_bit[ 0] = 1'b1; load_expected = 32'h0000_0011; end
            32'h8000_0030: begin load_check_bit[ 1] = 1'b1; load_expected = 32'h0000_0022; end
            32'h8000_0034: begin load_check_bit[ 2] = 1'b1; load_expected = 32'h0000_0033; end
            32'h8000_0038: begin load_check_bit[ 3] = 1'b1; load_expected = 32'h0000_0044; end
            32'h8000_003c: begin load_check_bit[ 4] = 1'b1; load_expected = 32'h0000_0055; end
            32'h8000_0054: begin load_check_bit[ 5] = 1'b1; load_expected = 32'h8001_8022; end
            32'h8000_0058: begin load_check_bit[ 6] = 1'b1; load_expected = 32'hffff_ff80; end
            32'h8000_005c: begin load_check_bit[ 7] = 1'b1; load_expected = 32'h0000_0080; end
            32'h8000_0060: begin load_check_bit[ 8] = 1'b1; load_expected = 32'hffff_8001; end
            32'h8000_0064: begin load_check_bit[ 9] = 1'b1; load_expected = 32'h0000_8001; end
            32'h8000_0068: begin load_check_bit[10] = 1'b1; load_expected = 32'h0000_0011; end
            32'h8000_006c: begin load_check_bit[11] = 1'b1; load_expected = 32'h0000_0033; end
            32'h8000_0078: begin load_check_bit[12] = 1'b1; load_expected = 32'hfe00_0044; end
            32'h8000_007c: begin load_check_bit[13] = 1'b1; load_expected = 32'h0000_0055; end
            default: ;
        endcase
    end

    always @(posedge core_clk) begin
        if (soc_resetn && !ddr_init_done) begin
            $display("RESULT: FAIL DDR regression CPU released before DDR init");
            $finish;
        end
        if (soc_resetn) begin
            if ((dut.u_soc.u_soc.inst_rsp_valid && dut.u_soc.u_soc.inst_rsp_error) ||
                (dut.u_soc.u_soc.data_rsp_valid && dut.u_soc.u_soc.data_rsp_error)) begin
                $display("RESULT: FAIL DDR regression bus access fault at %t", $time);
                $finish;
            end

            if (dut.u_soc.u_soc.data_req_valid && dut.u_soc.u_soc.data_req_ready &&
                dut.u_soc.u_soc.data_req_write) begin
                case (dut.u_soc.u_soc.data_req_addr)
                    32'h4000_0000: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'hf) begin
                            $display("RESULT: FAIL DDR regression SW strobe at +0"); $finish;
                        end
                        saw_word_stores[0] <= 1'b1;
                    end
                    32'h4000_0004: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'hf) begin
                            $display("RESULT: FAIL DDR regression SW strobe at +4"); $finish;
                        end
                        saw_word_stores[1] <= 1'b1;
                    end
                    32'h4000_0008: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'hf) begin
                            $display("RESULT: FAIL DDR regression SW strobe at +8"); $finish;
                        end
                        saw_word_stores[2] <= 1'b1;
                    end
                    32'h4000_000c: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'hf) begin
                            $display("RESULT: FAIL DDR regression SW strobe at +12"); $finish;
                        end
                        saw_word_stores[3] <= 1'b1;
                    end
                    32'h4000_0010: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'hf) begin
                            $display("RESULT: FAIL DDR regression SW strobe at +16"); $finish;
                        end
                        saw_word_stores[4] <= 1'b1;
                    end
                    32'h4000_0005: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'b0010) begin
                            $display("RESULT: FAIL DDR regression SB strobe at +5"); $finish;
                        end
                        saw_masked_stores[0] <= 1'b1;
                    end
                    32'h4000_0006: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'b1100) begin
                            $display("RESULT: FAIL DDR regression SH strobe at +6"); $finish;
                        end
                        saw_masked_stores[1] <= 1'b1;
                    end
                    32'h4000_000f: begin
                        if (dut.u_soc.u_soc.data_req_wstrb !== 4'b1000) begin
                            $display("RESULT: FAIL DDR regression SB strobe at +15"); $finish;
                        end
                        saw_masked_stores[2] <= 1'b1;
                    end
                    32'h4000_0040: saw_code_stores[0] <= 1'b1;
                    32'h4000_0044: saw_code_stores[1] <= 1'b1;
                    32'h4000_0048: saw_code_stores[2] <= 1'b1;
                    32'h4000_004c: saw_code_stores[3] <= 1'b1;
                    default: ;
                endcase
            end

            if (debug_wb_rf_we != 4'b0 && load_check_bit != 14'b0) begin
                if (debug_wb_rf_wnum !== 5'd10 ||
                    debug_wb_rf_wdata !== load_expected) begin
                    $display("RESULT: FAIL DDR regression PC=%h rd=%d got=%h expected=%h",
                             debug_wb_pc, debug_wb_rf_wnum, debug_wb_rf_wdata,
                             load_expected);
                    $finish;
                end
                saw_load_checks <= saw_load_checks | load_check_bit;
                $display("CHECK: DDR data PC=%h value=%h at %t",
                         debug_wb_pc, debug_wb_rf_wdata, $time);
            end

            if (debug_wb_rf_we != 4'b0 && debug_wb_pc == 32'h4000_0040) begin
                if (debug_wb_rf_wnum !== 5'd11 ||
                    debug_wb_rf_wdata !== 32'hfe00_0044) begin
                    $display("RESULT: FAIL DDR regression DDR-code LW x11 got=%h",
                             debug_wb_rf_wdata);
                    $finish;
                end
                saw_ddr_fetch_checks[0] <= 1'b1;
            end
            if (debug_wb_rf_we != 4'b0 && debug_wb_pc == 32'h4000_0044) begin
                if (debug_wb_rf_wnum !== 5'd12 ||
                    debug_wb_rf_wdata !== 32'h0000_0055) begin
                    $display("RESULT: FAIL DDR regression DDR-code LW x12 got=%h",
                             debug_wb_rf_wdata);
                    $finish;
                end
                saw_ddr_fetch_checks[1] <= 1'b1;
            end
            if (debug_wb_rf_we != 4'b0 && debug_wb_pc == 32'h4000_0048) begin
                if (debug_wb_rf_wnum !== 5'd13 ||
                    debug_wb_rf_wdata !== 32'hfe00_0099) begin
                    $display("RESULT: FAIL DDR regression DDR-code ADD got=%h",
                             debug_wb_rf_wdata);
                    $finish;
                end
                if (!(&saw_word_stores) || !(&saw_masked_stores) ||
                    !(&saw_code_stores) || !(&saw_load_checks) ||
                    !(&saw_ddr_fetch_checks)) begin
                    $display("RESULT: FAIL DDR regression missing checks sw=%b mask=%b code=%b load=%h fetch=%b",
                             saw_word_stores, saw_masked_stores, saw_code_stores,
                             saw_load_checks, saw_ddr_fetch_checks);
                    $finish;
                end
                $display("RESULT: PASS DDR regression lanes/masks/boundary/DDR-code at %t", $time);
                $finish;
            end
        end
    end

    initial begin
        #300000;
        $display("RESULT: FAIL DDR regression timeout init=%b sw=%b mask=%b code=%b load=%h fetch=%b",
                 ddr_init_done, saw_word_stores, saw_masked_stores,
                 saw_code_stores, saw_load_checks, saw_ddr_fetch_checks);
        $finish;
    end
`else
    reg saw_ddr_store = 1'b0;
    reg saw_ddr_load = 1'b0;
    reg saw_ddr_fetch = 1'b0;

    always @(posedge core_clk) begin
        if (soc_resetn && !ddr_init_done) begin
            $display("RESULT: FAIL soc_ddr3_top CPU released before DDR init");
            $finish;
        end
        if (soc_resetn) begin
            if (dut.u_soc.u_soc.data_req_valid && dut.u_soc.u_soc.data_req_ready &&
                dut.u_soc.u_soc.data_req_write &&
                dut.u_soc.u_soc.data_req_addr == 32'h4000_0000)
                saw_ddr_store <= 1'b1;

            if (debug_wb_rf_we != 4'b0 &&
                debug_wb_pc == 32'h8000_000c &&
                debug_wb_rf_wnum == 5'd3) begin
                if (debug_wb_rf_wdata !== 32'd42) begin
                    $display("RESULT: FAIL soc_ddr3_top DDR load got=%h expected=0000002a",
                             debug_wb_rf_wdata);
                    $finish;
                end
                saw_ddr_load <= 1'b1;
                $display("CHECK: CPU DDR store/load returned 42 at %t", $time);
            end

            if (debug_wb_rf_we != 4'b0 &&
                debug_wb_pc == 32'h4000_0020 &&
                debug_wb_rf_wnum == 5'd5) begin
                if (debug_wb_rf_wdata !== 32'h0000_005a) begin
                    $display("RESULT: FAIL soc_ddr3_top DDR instruction got=%h",
                             debug_wb_rf_wdata);
                    $finish;
                end
                saw_ddr_fetch <= 1'b1;
                if (saw_ddr_store && saw_ddr_load) begin
                    $display("RESULT: PASS soc_ddr3_top DDR store/load/fetch at %t", $time);
                    $finish;
                end else begin
                    $display("RESULT: FAIL soc_ddr3_top DDR fetch before store/load checks");
                    $finish;
                end
            end

            if ((dut.u_soc.u_soc.inst_rsp_valid && dut.u_soc.u_soc.inst_rsp_error) ||
                (dut.u_soc.u_soc.data_rsp_valid && dut.u_soc.u_soc.data_rsp_error)) begin
                $display("RESULT: FAIL soc_ddr3_top bus access fault at %t", $time);
                $finish;
            end
        end
    end

    initial begin
        #300000;
        $display("RESULT: FAIL soc_ddr3_top timeout init=%b store=%b load=%b fetch=%b",
                 ddr_init_done, saw_ddr_store, saw_ddr_load, saw_ddr_fetch);
        $finish;
    end
`endif

    initial begin : board_boot_smoke
        wait (saw_ddr_fetch && saw_selftest_run);
        #1;
        if (!ddr_init_done || !soc_resetn || !led_ddr_ready || key_release_count != 1)
            $fatal(1, "board key/DDR boot sequence");
        $display("RESULT: PASS board key bounce, DDR init, 245-word loader/fetch and MMIO RUN");
        $finish;
    end
endmodule
