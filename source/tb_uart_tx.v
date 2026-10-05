`timescale 1ns / 1fs

// Only external DUT ports are observed. The serial decoder uses the nominal
// 115200 baud period, independently of the DUT's integer divider.
module tb_uart_tx;
    localparam real CLK_PERIOD_NS = 1.0e9 / 93_750_000.0;
    localparam real RX_BIT_NS = 1.0e9 / 115_200.0;
    localparam integer EXPECTED_CYCLES = 814;
    localparam integer FRAME_CYCLES = 10 * EXPECTED_CYCLES;
    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg [7:0] tx_data = 8'd0;
    reg tx_valid = 1'b0;
    wire tx, tx_busy, tx_ready;
    reg test_pass = 1'b0;
    reg decode_enabled = 1'b1;
    reg [7:0] expected [0:11];
    integer decoded = 0, accepted = 0, completed = 0;
    integer bit_checks = 0, busy_pulses = 0;
    integer i;

    uart_tx dut (
        .clk(clk), .resetn(resetn), .tx_data(tx_data), .tx_valid(tx_valid),
        .tx(tx), .tx_busy(tx_busy), .tx_ready(tx_ready)
    );
    always #(CLK_PERIOD_NS / 2.0) clk = ~clk;

    task check;
        input condition;
        input [1023:0] message;
        begin
            if (condition !== 1'b1) begin
                $display("RESULT: FAIL uart_tx t=%0t: %0s", $time, message);
                $fatal(1, "%0s", message);
            end
        end
    endtask

    // Cycle-by-cycle line scoreboard checks all ten full bit intervals,
    // including identical adjacent bits (which have no visible TX edge).
    // This also checks exact busy/ready timing and protects latched data
    // against changing inputs or new valid pulses during an active frame.
    reg model_active = 1'b0;
    reg [9:0] model_frame;
    integer frame_age = 0;
    realtime last_clk_edge = 0.0;
    realtime last_accept = 0.0;
    always @(posedge clk) begin
        last_clk_edge = $realtime;
        if (!resetn) begin
            model_active = 1'b0;
            frame_age = 0;
        end else if (!model_active) begin
            if (tx_valid && tx_ready) begin
                if (accepted > 0 && accepted < 5)
                    // Allow accumulated 1 fs clock-delay rounding (< 0.01 ns/frame).
                    check(($realtime - last_accept > (FRAME_CYCLES + 1) * CLK_PERIOD_NS - 0.01) &&
                          ($realtime - last_accept < (FRAME_CYCLES + 1) * CLK_PERIOD_NS + 0.01),
                          "Hello must use earliest ready edge (one idle clock between frames)");
                last_accept = $realtime;
                model_frame = {1'b1, tx_data, 1'b0};
                model_active = 1'b1;
                frame_age = 0;
                accepted = accepted + 1;
            end
        end else if (frame_age == FRAME_CYCLES - 1) begin
            model_active = 1'b0;
            frame_age = 0;
            completed = completed + 1;
        end else begin
            frame_age = frame_age + 1;
        end
        #0.001; // observe registered outputs after NBA
        check(tx === (model_active ? model_frame[frame_age / EXPECTED_CYCLES] : 1'b1),
              "TX bit value/duration mismatch (start, data LSB first, stop, or idle)");
        check(tx_busy === model_active, "busy must cover exactly the complete 10-bit frame");
        check(tx_ready === (resetn && !model_active), "ready/reset/handshake timing mismatch");
        if (model_active) bit_checks = bit_checks + 1;
    end

    // Reject any glitch away from a rising clock edge during normal operation.
    always @(tx) begin
        if (resetn && $realtime > CLK_PERIOD_NS)
            check($realtime - last_clk_edge < 0.001, "TX changed between clock edges");
    end

    // Independent UART receiver: falling start edge, center-of-start check,
    // eight nominal-rate center samples, and center-of-stop check.
    reg [7:0] received;
    integer rx_bit;
    realtime start_time, previous_start = 0.0;
    always begin
        @(negedge tx);
        if (resetn && decode_enabled) begin
            start_time = $realtime;
            check(decoded < 12, "extra/duplicate serial character");
            if (decoded > 0 && decoded < 5)
                check(start_time - previous_start < 10.01 * RX_BIT_NS,
                      "unexpected gap in continuous Hello serial stream");
            previous_start = start_time;
            #(RX_BIT_NS / 2.0);
            check(tx === 1'b0, "invalid UART start bit at center");
            for (rx_bit = 0; rx_bit < 8; rx_bit = rx_bit + 1) begin
                #(RX_BIT_NS);
                check(tx === 1'b0 || tx === 1'b1, "unknown UART data level");
                received[rx_bit] = tx;
            end
            #(RX_BIT_NS);
            check(tx === 1'b1, "invalid UART stop bit at center");
            if (received !== expected[decoded]) begin
                $display("DECODE ERROR: index=%0d expected=0x%02h got=0x%02h",
                         decoded, expected[decoded], received);
                check(1'b0, "UART decoded character mismatch or LSB ordering error");
            end
            $display("DECODE: index=%0d byte=0x%02h PASS", decoded, received);
            decoded = decoded + 1;
        end
    end

    task send_byte;
        input [7:0] value;
        begin
            @(negedge clk);
            while (!tx_ready) @(negedge clk);
            tx_data = value;
            tx_valid = 1'b1;
            @(posedge clk); #0.002;
            check(tx_busy && !tx_ready && !tx, "accepted byte must immediately start frame");
            @(negedge clk); tx_valid = 1'b0;
        end
    endtask

    task wait_idle;
        begin
            @(negedge clk);
            while (!tx_ready) @(negedge clk);
            check(tx && !tx_busy, "completed stop bit returns to idle high");
        end
    endtask

    task quiet_check;
        input integer clocks;
        integer n;
        begin
            for (n = 0; n < clocks; n = n + 1) begin
                @(negedge clk);
                check(tx && !tx_busy && tx_ready, "unexpected queued/repeated frame in idle");
            end
        end
    endtask

    initial begin
        expected[0] = "H"; expected[1] = "e"; expected[2] = "l";
        expected[3] = "l"; expected[4] = "o";
        expected[5] = 8'h00; expected[6] = 8'hff;
        expected[7] = 8'h55; expected[8] = 8'haa;
        expected[9] = 8'h01; expected[10] = 8'h80;
        expected[11] = "R";
        #0.002;
        check(tx && !tx_busy && !tx_ready, "reset must force idle high and block requests");
        tx_valid = 1'b1; tx_data = 8'hcc;
        repeat (4) @(negedge clk);
        tx_valid = 1'b0; resetn = 1'b1;
        quiet_check(4);

        // Keep valid asserted; update the next character only after handshake.
        // Ready returns after the full stop interval, then the next edge
        // accepts the following byte. No characters may be lost or repeated.
        @(negedge clk); tx_valid = 1'b1; tx_data = expected[0];
        for (i = 0; i < 5; i = i + 1) begin
            @(posedge clk);
            while (!tx_ready) @(posedge clk);
            #0.002;
            @(negedge clk);
            if (i == 4) tx_valid = 1'b0;
            else tx_data = expected[i + 1];
        end
        wait_idle;
        check(decoded == 5 && accepted == 5 && completed == 5, "Hello count mismatch");
        quiet_check(FRAME_CYCLES + 2);
        $display("CHECK: continuous nominal-rate decoded Hello PASS");

        // Attack an active 0x00 frame with pulses in start/data/stop intervals.
        // Data changes even when valid is low must also have no effect.
        send_byte(expected[5]);
        for (i = 0; i < FRAME_CYCLES - 2; i = i + 1) begin
            tx_data = i;
            tx_valid = (i % EXPECTED_CYCLES == 10);
            if (tx_valid) busy_pulses = busy_pulses + 1;
            check(tx_busy && !tx_ready, "busy pulse unexpectedly accepted");
            @(negedge clk);
        end
        tx_valid = 1'b0;
        wait_idle;
        quiet_check(FRAME_CYCLES + 2);
        check(decoded == 6 && accepted == 6 && completed == 6 && busy_pulses == 10,
              "busy requests must not corrupt, queue, lose, or duplicate data");
        for (i = 6; i < 11; i = i + 1) begin
            send_byte(expected[i]);
            wait_idle;
        end
        check(decoded == 11 && completed == 11, "data-pattern count mismatch");
        quiet_check(FRAME_CYCLES + 2);

        // Abort a frame with reset between clock edges; it must never resume.
        decode_enabled = 1'b0;
        send_byte(8'h00);
        repeat (2 * EXPECTED_CYCLES) @(negedge clk);
        #0.2; resetn = 1'b0; tx_valid = 1'b1; tx_data = 8'hff;
        #0.001;
        check(tx && !tx_busy && !tx_ready, "asynchronous mid-frame reset must force idle high");
        repeat (4) @(negedge clk);
        tx_valid = 1'b0; resetn = 1'b1;
        quiet_check(FRAME_CYCLES + 2);
        decode_enabled = 1'b1;
        send_byte(expected[11]); wait_idle;
        quiet_check(2 * FRAME_CYCLES);
        check(decoded == 12 && accepted == 13 && completed == 12,
              "final counts: one reset-aborted frame, no missing or repeated completed bytes");
        $display("CHECK: 814 clocks/bit, all line levels, busy pulses=%0d, reset recovery PASS", busy_pulses);
        $display("RESULT: PASS uart_tx Hello + 00/ff/55/aa/01/80 + reset recovery; decoded=%0d bit_cycle_checks=%0d",
                 decoded, bit_checks);
        test_pass = 1'b1;
        $finish;
    end

    initial begin
        #3_000_000;
        check(1'b0, "timeout: missing UART character or stuck busy/ready");
    end
endmodule
