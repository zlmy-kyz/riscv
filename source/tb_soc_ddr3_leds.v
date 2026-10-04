`timescale 1ns / 1ps

// Check observable behavior with short divisors; no DDR/IP model required.
module tb_soc_ddr3_leds;
    reg clk = 0;
    always #5 clk = !clk;
    reg resetn = 0, soc_resetn = 0;
    reg req_valid = 0, req_write = 0;
    reg [31:0] req_addr = 0, req_wdata = 0;
    reg [3:0] req_wstrb = 0;
    wire req_ready, rsp_valid, rsp_error;
    wire [31:0] rsp_rdata;
    wire [1:0] status;
    wire alive, ready, result_led;
    integer checks = 0, i, transitions;
    reg last_led;
    simple_mmio mmio (
        .clk(clk), .resetn(soc_resetn), .req_valid(req_valid),
        .req_write(req_write), .req_size(2'd2), .req_addr(req_addr),
        .req_wdata(req_wdata), .req_wstrb(req_wstrb), .req_ready(req_ready),
        .rsp_valid(rsp_valid), .rsp_rdata(rsp_rdata), .rsp_error(rsp_error),
        .test_status(status)
    );
    soc_ddr3_leds #(.CORE_CLK_HZ(16), .SELFTEST_TIMEOUT_CYCLES(400)) leds (
        .clk(clk), .resetn(resetn), .soc_resetn(soc_resetn),
        .selftest_status(status), .led_clk_alive(alive),
        .led_ddr_ready(ready), .led_selftest(result_led)
    );

    task check_expect;
        input condition;
        input [511:0] description;
        begin
            if (condition !== 1'b1)
                $fatal(1, "RESULT: FAIL LED/MMIO %0s", description);
            checks = checks + 1;
        end
    endtask

    task access;
        input write_access;
        input [31:0] address, data;
        input [3:0] strobe;
        input error_expected;
        input [31:0] read_expected;
        begin
            @(negedge clk);
            req_valid = 1; req_write = write_access;
            req_addr = address; req_wdata = data; req_wstrb = strobe;
            check_expect(req_ready, "request ready");
            @(posedge clk); #1;
            check_expect(rsp_valid && rsp_error == error_expected, "response/error");
            if (!write_access) check_expect(rsp_rdata == read_expected, "read data");
            @(negedge clk); req_valid = 0;
            @(posedge clk); #1;
            check_expect(!rsp_valid, "response completes once");
        end
    endtask

    task reset_soc;
        begin
            @(negedge clk); soc_resetn = 0;
            repeat (2) begin @(posedge clk); #1; end
            check_expect(status == 0 && !ready && !result_led && !leds.timed_out,
                   "SoC reset clears status and timeout");
            @(negedge clk); soc_resetn = 1;
            @(posedge clk); #1;
            check_expect(ready && !result_led, "ready precedes selftest start");
        end
    endtask

    task check_blink;
        input integer samples, expected_edges;
        begin
            // Sample a whole number of blink periods after a mode transition.
            repeat (2) begin @(posedge clk); #1; end
            transitions = 0; last_led = result_led;
            for (i = 0; i < samples; i = i + 1) begin
                @(posedge clk); #1;
                if (result_led != last_led) transitions = transitions + 1;
                last_led = result_led;
            end
            check_expect(transitions == expected_edges, "blink period");
        end
    endtask

    initial begin
        repeat (2) begin @(posedge clk); #1; end
        check_expect(!alive && !ready && !result_led && status == 0, "power/reset LEDs off");
        @(negedge clk); resetn = 1;
        repeat (7) begin @(posedge clk); #1; end
        check_expect(!alive && !ready && !result_led, "heartbeat before half period");
        @(posedge clk); #1;
        check_expect(alive && !ready && !result_led, "heartbeat while DDR still training");
        repeat (8) begin @(posedge clk); #1; end
        check_expect(!alive && !leds.timed_out, "training does not start timeout");
        reset_soc;
        access(0, 32'h10000010, 0, 0, 0, 0);
        access(1, 32'h10000010, 2, 15, 1, 0);
        check_expect(status == 0, "PASS before RUN rejected");
        access(1, 32'h10000010, 3, 15, 1, 0);
        access(1, 32'h10000010, 4, 15, 1, 0);
        access(1, 32'h10000010, 1, 14, 0, 0);
        check_expect(status == 0, "high-byte strobe cannot start");
        access(1, 32'h10000010, 1, 1, 0, 0);
        check_expect(status == 1, "low-byte RUN accepted");
        check_blink(32, 4);
        access(0, 32'h10000010, 0, 0, 0, 1);
        access(1, 32'h10000010, 2, 15, 0, 0);
        check_expect(status == 2 && result_led, "PASS lights result LED");
        access(1, 32'h10000010, 3, 15, 0, 0);
        access(1, 32'h10000010, 1, 15, 0, 0);
        check_expect(status == 2 && result_led, "PASS sticky against FAIL/RUN");
        repeat (410) begin @(posedge clk); #1; end
        check_expect(result_led && !leds.timed_out, "PASS never times out");
        access(1, 32'h10000000, 32'h11223344, 15, 0, 0);
        access(1, 32'h10000000, 32'haabbccdd, 5, 0, 0);
        access(0, 32'h10000000, 0, 0, 0, 32'h11bb33dd);
        access(0, 32'h10000004, 0, 0, 0, 32'h4d4d494f);
        access(0, 32'h1000000c, 0, 0, 0, 1);
        access(1, 32'h1000000c, 1, 15, 1, 0);
        access(0, 32'h10000014, 0, 0, 1, 0);
        reset_soc;
        access(1, 32'h10000010, 1, 15, 0, 0);
        access(1, 32'h10000010, 3, 15, 0, 0);
        check_expect(status == 3, "FAIL reported");
        check_blink(16, 8);
        access(1, 32'h10000010, 2, 15, 0, 0);
        check_expect(status == 3, "FAIL sticky against PASS");
        repeat (410) begin @(posedge clk); #1; end
        check_expect(!leds.timed_out, "reported FAIL stops watchdog");
        reset_soc;
        // First released edge already counted by reset_soc.
        repeat (398) begin @(posedge clk); #1; end
        check_expect(!leds.timed_out && !result_led, "idle timeout exact boundary before");
        @(posedge clk); #1;
        check_expect(leds.timed_out && status == 0, "idle timeout on 400th edge");
        check_blink(16, 8);
        access(1, 32'h10000010, 1, 15, 0, 0);
        access(1, 32'h10000010, 2, 15, 0, 0);
        check_expect(status == 2 && leds.timed_out, "late PASS cannot hide timeout");
        check_blink(16, 8);
        reset_soc;
        access(1, 32'h10000010, 1, 15, 0, 0);
        repeat (400) begin @(posedge clk); #1; end
        check_expect(status == 1 && leds.timed_out, "RUN hang times out");
        @(negedge clk); resetn = 0; soc_resetn = 0;
        #1; check_expect(!alive && !ready && !result_led, "external reset immediately extinguishes LEDs");
        @(posedge clk); #1;
        check_expect(status == 0 && !leds.timed_out, "external reset clears latched state");
        $display("RESULT: PASS LED/MMIO heartbeat, states, strobes, latch, timeout, reset checks=%0d", checks);
        $finish;
    end
    initial begin #30000; $fatal(1, "RESULT: FAIL LED/MMIO TB timeout"); end
endmodule
