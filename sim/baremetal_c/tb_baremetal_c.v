`timescale 1ns / 1ps
// Real CPU + SoC buses + existing DDR bridge and LED RTL; test-only DDR user port.
module tb_baremetal_c #(
    parameter integer LED_TIMEOUT = 30000,
    parameter integer MAX_CYCLES = 40000
);
    reg clk = 0, resetn = 0;
    always #(1.0e9 / 93750000.0 / 2.0) clk = ~clk;
    initial begin repeat (5) @(negedge clk); resetn = 1; end
    wire [27:0] awaddr, araddr;
    wire awvalid, arvalid;
    wire [127:0] wdata;
    wire [15:0] wstrb;
    reg [127:0] rdata = 0;
    reg rvalid = 0, writing = 0, reading = 0;
    reg [27:0] wa, ra;
    integer aw_wait = 0, ar_wait = 0, w_wait = 0, r_wait = 0;
    wire awready = awvalid && !writing && aw_wait >= 2;
    wire arready = arvalid && !reading && ar_wait >= 3;
    wire wready = writing && w_wait == 0;
    wire [1:0] status;
    wire alive, ready, result_led;
    wire uart_tx;
    integer tx_accepted = 0, tx_decoded = 0;
    reg [7:0] expected_tx [0:3];
    reg [127:0] beats [0:4095]; // full 64 KiB, including stack at DDR+0xfff0
    reg [31:0] image [0:4095];
    integer mode, payload_words, bss_start, bss_end, main_pc, done_pc, results_addr;
    integer cycles = 0, copied = 0, reads = 0, writes = 0, done_retired = 0;
    integer bss_clears = 0, run_edges = 0, result_edges = 0, last_run_edge = 0;
    integer last_result_edge = 0, hold_cycles = 0, heartbeat_edges = 0;
    integer loader_phase = 1, saw_main = 0, saw_run = 0;
    integer saw_initial_sp = 0;
    reg old_result = 0, old_alive = 0;
    reg [1:0] old_status = 0;
    reg test_pass = 0;
    string image_path;

    task check;
        input condition;
        input [511:0] message;
        begin if (condition !== 1'b1) $fatal(1, "RESULT: FAIL baremetal_c mode=%0d cycle=%0d: %0s", mode, cycles, message); end
    endtask
    function [31:0] word_at;
        input [31:0] address;
        reg [31:0] offset;
        begin
            offset = address - 32'h40000000;
            word_at = beats[offset[15:4]][offset[3:2]*32 +: 32];
        end
    endfunction

    soc_top #(.ENABLE_DDR(1), .RESET_PC(0), .INST_ROM_BASE(0), .DATA_RAM_BASE(0)) dut (
        .clk(clk), .resetn(resetn), .uart_rx(1'b1), .uart_tx(uart_tx),
        .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0),
        .selftest_status(status), .debug_wb_pc(), .debug_wb_rf_we(),
        .debug_wb_rf_wnum(), .debug_wb_rf_wdata(), .debug_inst(),
        .ddr_init_done(1'b1), .ddr_axi_awaddr(awaddr), .ddr_axi_awuser_ap(),
        .ddr_axi_awuser_id(), .ddr_axi_awlen(), .ddr_axi_awready(awready),
        .ddr_axi_awvalid(awvalid), .ddr_axi_wdata(wdata), .ddr_axi_wstrb(wstrb),
        .ddr_axi_wready(wready), .ddr_axi_wusero_id(4'd0), .ddr_axi_wusero_last(wready),
        .ddr_axi_araddr(araddr), .ddr_axi_aruser_ap(), .ddr_axi_aruser_id(),
        .ddr_axi_arlen(), .ddr_axi_arready(arready), .ddr_axi_arvalid(arvalid),
        .ddr_axi_rdata(rdata), .ddr_axi_rid(4'd0), .ddr_axi_rlast(rvalid), .ddr_axi_rvalid(rvalid)
    );
    // Speed up display time only. Production board_top still supplies 93.75 MHz.
    soc_ddr3_leds #(.CORE_CLK_HZ(32), .SELFTEST_TIMEOUT_CYCLES(LED_TIMEOUT)) leds (
        .clk(clk), .resetn(resetn), .soc_resetn(resetn), .selftest_status(status),
        .led_clk_alive(alive), .led_ddr_ready(ready), .led_selftest(result_led)
    );

    integer i, lane;
    initial begin
        check($value$plusargs("MODE=%d", mode), "missing MODE");
        check($value$plusargs("IMAGE=%s", image_path), "missing IMAGE");
        check($value$plusargs("WORDS=%d", payload_words), "missing WORDS");
        check($value$plusargs("MAIN=%h", main_pc), "missing MAIN");
        check($value$plusargs("DONE=%h", done_pc), "missing DONE");
        check($value$plusargs("BSS_START=%h", bss_start), "missing BSS_START");
        check($value$plusargs("BSS_END=%h", bss_end), "missing BSS_END");
        check($value$plusargs("RESULTS=%h", results_addr), "missing RESULTS");
        check(mode >= 0 && mode <= 4 && payload_words > 0 && payload_words <= 4092, "invalid case configuration");
        expected_tx[0] = 8'h33; expected_tx[1] = 8'h30;
        expected_tx[2] = 8'h0d; expected_tx[3] = 8'h0a;
        $readmemh(image_path, image);
        check(image[4092] == payload_words && image[4093] == 0 && image[4094] == 0 && image[4095] == 0, "bad RAM manifest");
        // No C code preloaded into DDR; poison BSS and stack before CPU loading.
        for (i = 0; i < 4096; i = i + 1) beats[i] = {4{32'ha5a5a5a5}};
        if ($test$plusargs("WAVE")) begin $dumpfile("baremetal_c.vcd"); $dumpvars(0, tb_baremetal_c); end
    end

    // Pango-specific AW/W split handshake. Commit masked writes once at WREADY.
    always @(posedge clk) begin
        rvalid <= 0;
        if (resetn) begin
            if (awvalid && !awready) aw_wait <= aw_wait + 1;
            if (arvalid && !arready) ar_wait <= ar_wait + 1;
            if (awvalid && awready) begin
                check(awaddr[27:15] == 0, "DDR write outside 64 KiB; address alias");
                wa <= awaddr; writing <= 1; w_wait <= 4; aw_wait <= 0;
            end
            if (writing && w_wait > 0) w_wait <= w_wait - 1;
            if (wready) begin
                for (lane = 0; lane < 16; lane = lane + 1)
                    if (wstrb[lane]) beats[wa[14:3]][lane*8 +: 8] <= wdata[lane*8 +: 8];
                writing <= 0; writes = writes + 1;
            end
            if (arvalid && arready) begin
                check(araddr[27:15] == 0, "DDR read outside 64 KiB; address alias");
                ra <= araddr; reading <= 1; r_wait <= 5; ar_wait <= 0;
            end
            if (reading && r_wait > 0) r_wait <= r_wait - 1;
            if (reading && r_wait == 0) begin
                rdata <= beats[ra[14:3]]; rvalid <= 1; reading <= 0; reads = reads + 1;
            end
        end
    end

    integer j;
    always @(posedge clk) if (resetn) begin
        cycles = cycles + 1;
        check(!dut.u_cpu.sync_trap_event, "unexpected CPU synchronous exception");
        check(!(dut.inst_rsp_valid && dut.inst_rsp_error) && !(dut.data_rsp_valid && dut.data_rsp_error), "bus access error");
        if (dut.data_req_valid && dut.data_req_ready && dut.data_req_write) begin
            if (loader_phase && dut.data_req_addr >= 32'h40000000) begin
                check(dut.data_req_addr == 32'h40000000 + copied*4 && copied < payload_words, "loader address/order/count");
                check(dut.data_req_wdata === image[copied] && dut.data_req_wstrb == 15, "loader data/strobe");
                copied = copied + 1;
            end
            if (dut.data_req_addr >= bss_start && dut.data_req_addr < bss_end && !saw_main) begin
                check(dut.data_req_addr == bss_start + bss_clears*4 && dut.data_req_wdata == 0 && dut.data_req_wstrb == 15, "BSS clear sequence");
                bss_clears = bss_clears + 1;
            end
        end
        if (loader_phase && dut.inst_req_valid && dut.inst_req_ready && dut.inst_req_addr == 32'h40000000) begin
            check(copied == payload_words && !writing, "jump before loader completes");
            for (j = 0; j < payload_words; j = j + 1)
                check(word_at(32'h40000000 + j*4) === image[j], "DDR payload differs from BIN/DAT");
            for (j = bss_start; j < bss_end; j = j + 4)
                check(word_at(j) === 32'ha5a5a5a5, "BSS unexpectedly pre-cleared by model/loader");
            loader_phase = 0;
            $display("CHECK: CPU loader copied %0d words, exact DDR image, poisoned BSS retained", copied);
        end
        if (dut.u_cpu.normal_retire) begin
            if (dut.u_cpu.mem_wb_pc == 32'h4000000c) begin
                check(dut.debug_wb_rf_we == 15 && dut.debug_wb_rf_wnum == 2 &&
                      dut.debug_wb_rf_wdata === 32'h40010000, "startup SP writeback");
                saw_initial_sp = 1;
            end
            if (dut.u_cpu.mem_wb_pc == main_pc && !saw_main) begin
                check(!loader_phase && bss_clears*4 == bss_end-bss_start, "main before complete BSS initialization");
                for (j = bss_start; j < bss_end; j = j + 4) check(word_at(j) === 0, "BSS nonzero at main entry");
                saw_main = 1;
                $display("CHECK: main retired at %h, BSS cleared=%0d words", main_pc, bss_clears);
            end
            if (dut.u_cpu.mem_wb_pc == done_pc) done_retired = done_retired + 1;
        end
        if (mode == 4 && dut.u_uart_mmio.tx_send) begin
            check(tx_accepted < 4 && dut.u_uart_mmio.tx_ready, "extra/busy UART send");
            check(dut.u_uart_mmio.req_wdata[7:0] === expected_tx[tx_accepted] &&
                  dut.u_uart_mmio.req_wstrb == 1, "UART TX byte/strobe mismatch");
            tx_accepted = tx_accepted + 1;
        end
        check(cycles < MAX_CYCLES, "simulation timeout");
    end

    // Independent PC receiver: decode actual TX pin at nominal 115200 baud.
    reg [7:0] decoded_byte;
    integer bit_index;
    always begin
        @(negedge uart_tx);
        if (resetn && mode == 4) begin
            #(1.0e9 / 115200.0 / 2.0);
            check(uart_tx === 0, "UART start bit");
            for (bit_index = 0; bit_index < 8; bit_index = bit_index + 1) begin
                #(1.0e9 / 115200.0);
                decoded_byte[bit_index] = uart_tx;
            end
            #(1.0e9 / 115200.0);
            check(uart_tx === 1 && tx_decoded < 4, "UART stop bit/extra frame");
            check(decoded_byte === expected_tx[tx_decoded], "PC decoded UART byte mismatch");
            $display("DECODE: UART printf index=%0d byte=%02h", tx_decoded, decoded_byte);
            tx_decoded = tx_decoded + 1;
        end
    end

    always @(negedge clk) begin
        if (resetn) begin
            check(ready, "DDR-ready LED missing");
            if (alive != old_alive) heartbeat_edges = heartbeat_edges + 1;
            if (status == 1) begin
                saw_run = 1;
                if (old_status == 1 && result_led != old_result) begin
                    if (run_edges > 0) check(cycles-last_run_edge == 16, "RUN slow blink interval");
                    run_edges = run_edges + 1; last_run_edge = cycles;
                end
            end
            if (status == 2 || status == 3 || leds.timed_out) begin
                if (mode == 1 || mode == 4) check(status == 2 && !leds.timed_out && result_led, "PASS must hold LED on");
                if (mode == 4) check(tx_decoded == 4 && tx_accepted == 4 &&
                    dut.u_uart_mmio.tx_ready && !dut.u_uart_mmio.tx_busy && uart_tx === 1,
                    "PASS reported before UART frame completion");
                if (mode == 2) check(status == 3 && !leds.timed_out, "injected failure must report FAIL");
                if (mode == 3) check(status == 0 && leds.timed_out, "baseline hang must remain IDLE and time out");
                if ((mode == 2 && old_status == 3) || (mode == 3 && hold_cycles > 1)) begin
                    if (result_led != old_result) begin
                        if (result_edges > 0) check(cycles-last_result_edge == 4, "FAIL/timeout fast blink interval");
                        result_edges = result_edges + 1; last_result_edge = cycles;
                    end
                end
                hold_cycles = hold_cycles + 1;
            end
            if (done_retired >= 8 && ((mode == 0) || (hold_cycles >= 80))) begin
                check(saw_main && saw_initial_sp && heartbeat_edges > 0, "main/SP/heartbeat coverage missing");
                if (mode == 4) check(dut.u_cpu.u_regfile.rf[2] >= 32'h4000f000 &&
                    dut.u_cpu.u_regfile.rf[2] < 32'h40010000 && dut.u_cpu.u_regfile.rf[2][3:0] == 0, "UART C stack bounds/alignment");
                else check(dut.u_cpu.u_regfile.rf[2] === 32'h4000fff0, "final C stack pointer");
                if (mode == 0 || mode == 3) begin
                    check(word_at(32'h4000fff4) === 10 && word_at(32'h4000fff8) === 20 && word_at(32'h4000fffc) === 30, "baseline stack a/b/c mismatch");
                    check(status == 0 && !saw_run, "original C unexpectedly reported status");
                    if (mode == 0) check(!leds.timed_out && !result_led, "baseline LED must remain IDLE");
                end else if (mode == 4) begin
                    check(word_at(results_addr) === 30 && saw_run && run_edges >= 2 && bss_clears > 0,
                          "UART C result/RUN/BSS coverage");
                    $display("CHECK: printf real CPU decoded 30 CR LF, TX accepted=%0d decoded=%0d, LED PASS", tx_accepted, tx_decoded);
                end else begin
                    check(word_at(results_addr) === 10 && word_at(results_addr+4) === 20 && word_at(results_addr+8) === 30, "C results mismatch");
                    check(saw_run && run_edges >= 2 && bss_clears > 0, "RUN blink/BSS coverage missing");
                    if (mode == 2) check(result_edges >= 8, "FAIL blink coverage missing");
                end
                if (mode == 3) check(result_edges >= 8, "timeout blink coverage missing");
                test_pass = 1;
                $display("RESULT: PASS baremetal_c mode=%0d copied=%0d main=%h done=%h retired=%0d BSS=%0d status=%0d timeout=%0d RUN_edges=%0d FAST_edges=%0d DDR_W=%0d DDR_R=%0d cycles=%0d", mode, copied, main_pc, done_pc, done_retired, bss_clears, status, leds.timed_out, run_edges, result_edges, writes, reads, cycles);
                $finish;
            end
            old_result = result_led; old_alive = alive; old_status = status;
        end else check(!ready && !result_led, "reset LED gating");
    end
endmodule
