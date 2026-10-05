`timescale 1ns / 1fs

module tb_uart_rx;
    localparam real CLK_NS = 1.0e9 / 93_750_000.0;
    localparam real BIT_NS = 1.0e9 / 115_200.0;
    localparam real SAMPLE_STOP_NS = (407.0 + 9.0 * 814.0) * CLK_NS;
    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg stimulus_rx = 1'b1;
    reg loopback = 1'b0;
    reg [7:0] tx_data = 8'd0;
    reg tx_valid = 1'b0;
    wire tx, tx_busy, tx_ready;
    wire rx = loopback ? tx : stimulus_rx;
    wire [7:0] rx_data, fifo_data;
    wire rx_valid, frame_error, rx_busy;
    reg fifo_read = 1'b0;
    wire fifo_empty, fifo_full, overflow;
    wire [4:0] fifo_count;
    wire fifo_unit_done;
    reg test_pass = 1'b0;

    uart_tx u_tx (
        .clk(clk), .resetn(resetn), .tx_data(tx_data), .tx_valid(tx_valid),
        .tx(tx), .tx_busy(tx_busy), .tx_ready(tx_ready)
    );
    uart_rx u_rx (
        .clk(clk), .resetn(resetn), .rx(rx), .rx_data(rx_data),
        .rx_valid(rx_valid), .frame_error(frame_error), .rx_busy(rx_busy)
    );
    uart_rx_fifo u_fifo (
        .clk(clk), .resetn(resetn), .wr_en(rx_valid), .write_data(rx_data),
        .rd_en(fifo_read), .read_data(fifo_data), .empty(fifo_empty),
        .full(fifo_full), .count(fifo_count), .overflow(overflow)
    );
    uart_fifo_unit_test u_fifo_test (.clk(clk), .done(fifo_unit_done));
    always #(CLK_NS / 2.0) clk = ~clk;

    task check;
        input condition;
        input [1023:0] message;
        begin
            if (condition !== 1'b1) begin
                $display("RESULT: FAIL uart_rx t=%0t: %0s", $time, message);
                $fatal(1, "%0s", message);
            end
        end
    endtask

    // Expected UART events are entered by an independent waveform driver or
    // by the TX handshake, before the frame completes. No DUT internals read.
    reg [7:0] event_data [0:255];
    reg event_error [0:255];
    realtime event_min [0:255], event_max [0:255];
    integer expected_events = 0, observed_events = 0;
    integer good_events = 0, error_events = 0, overflow_events = 0;
    integer fifo_writes = 0, fifo_reads = 0, simultaneous_full = 0;
    reg previous_valid = 1'b0, previous_error = 1'b0;
    reg [7:0] previous_data = 8'd0;

    task expect_event;
        input [7:0] value;
        input bad_stop;
        input realtime start_time;
        begin
            check(expected_events < 256, "test expectation table exhausted");
            event_data[expected_events] = value;
            event_error[expected_events] = bad_stop;
            // Input edge to FSM detection is 2..3 clocks. Allow 0.1 ns for
            // simulation rounding, much less than one 10.667 ns clock.
            event_min[expected_events] = start_time + SAMPLE_STOP_NS + 2.0 * CLK_NS - 0.1;
            event_max[expected_events] = start_time + SAMPLE_STOP_NS + 3.0 * CLK_NS + 0.1;
            expected_events = expected_events + 1;
        end
    endtask

    always @(posedge clk) begin
        #0.001;
        if (!resetn) begin
            check(!rx_valid && !frame_error && !rx_busy && rx_data == 0,
                  "RX reset outputs must be idle/clear");
            previous_data = 8'd0;
        end else begin
            check(!(rx_valid && frame_error), "valid and frame_error are mutually exclusive");
            check(!(rx_valid && previous_valid), "rx_valid must be one clock pulse");
            check(!(frame_error && previous_error), "frame_error must be one clock pulse");
            if (rx_valid || frame_error) begin
                check(observed_events < expected_events, "unexpected character/error (false start, duplicate, or reset residue)");
                if (rx_valid !== !event_error[observed_events] ||
                    frame_error !== event_error[observed_events]) begin
                    $display("EVENT ERROR: index=%0d expected_error=%b valid=%b error=%b",
                             observed_events, event_error[observed_events], rx_valid, frame_error);
                    check(1'b0, "wrong normal/error frame classification");
                end
                if ($realtime < event_min[observed_events] || $realtime > event_max[observed_events]) begin
                    $display("TIMING ERROR: index=%0d time=%f expected=[%f,%f] ns",
                             observed_events, $realtime, event_min[observed_events], event_max[observed_events]);
                    check(1'b0, "RX completion must occur at scheduled stop center, including CDC delay");
                end
                if (rx_valid) begin
                    if (rx_data !== event_data[observed_events]) begin
                        $display("DATA ERROR: index=%0d expected=%02h got=%02h",
                                 observed_events, event_data[observed_events], rx_data);
                        check(1'b0, "RX data/LSB first/byte order mismatch");
                    end
                    previous_data = rx_data;
                    good_events = good_events + 1;
                end else begin
                    error_events = error_events + 1;
                end
                observed_events = observed_events + 1;
            end
            check(rx_data === previous_data, "rx_data must retain last good byte on idle/error cycles");
        end
        previous_valid = rx_valid;
        previous_error = frame_error;
    end

    // FIFO reference is a shifted byte queue, independently of ring pointers.
    // Check every clock, including delayed RX writes, empty/full simultaneous
    // operations, overflow pulses, head data, and all occupancy transitions.
    reg [7:0] queue [0:15];
    integer queue_count = 0;
    integer q;
    reg pop_now, push_now, expected_overflow;
    always @(posedge clk) begin
        if (!resetn) begin
            queue_count = 0;
            expected_overflow = 1'b0;
        end else begin
            pop_now = fifo_read && queue_count != 0;
            push_now = rx_valid && (queue_count < 16 || pop_now);
            expected_overflow = rx_valid && !push_now;
            if (pop_now && push_now && queue_count == 16)
                simultaneous_full = simultaneous_full + 1;
            if (pop_now) begin
                check(fifo_data === queue[0], "FIFO read order mismatch");
                for (q = 0; q < 15; q = q + 1) queue[q] = queue[q + 1];
                queue_count = queue_count - 1;
                fifo_reads = fifo_reads + 1;
            end
            if (push_now) begin
                queue[queue_count] = rx_data;
                queue_count = queue_count + 1;
                fifo_writes = fifo_writes + 1;
            end
            if (expected_overflow) overflow_events = overflow_events + 1;
        end
        #0.001;
        check(fifo_count === queue_count[4:0], "FIFO count mismatch");
        check(fifo_empty === (queue_count == 0), "FIFO empty mismatch");
        check(fifo_full === (queue_count == 16), "FIFO full mismatch");
        check(overflow === expected_overflow, "FIFO overflow pulse/drop-new mismatch");
        check(fifo_data === ((queue_count == 0) ? 8'd0 : queue[0]), "FIFO head changed/old data overwritten");
    end

    task settle;
        begin repeat (6) @(negedge clk); end
    endtask

    // Standard 8N1 waveform, real-valued nominal baud. Calls can be adjacent
    // (no artificial gap beyond one stop bit) and start at asynchronous phase.
    task send_wave;
        input [7:0] value;
        input realtime period_ns;
        input good_stop;
        integer bit_number;
        begin
            check(!loopback && stimulus_rx, "independent stimulus must start from idle high");
            expect_event(value, !good_stop, $realtime);
            stimulus_rx = 1'b0;
            #(period_ns);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                stimulus_rx = value[bit_number];
                #(period_ns);
            end
            stimulus_rx = good_stop;
            #(period_ns);
        end
    endtask

    task read_byte;
        input [7:0] value;
        begin
            @(negedge clk);
            check(!fifo_empty && fifo_data === value, "FIFO expected read byte mismatch");
            fifo_read = 1'b1;
            @(posedge clk); #0.002;
            @(negedge clk); fifo_read = 1'b0;
        end
    endtask

    task reset_and_quiet;
        begin
            @(negedge clk); #0.2;
            resetn = 1'b0; stimulus_rx = 1'b1; loopback = 1'b0;
            fifo_read = 1'b0; tx_valid = 1'b0;
            #0.001;
            check(!rx_busy && !rx_valid && !frame_error && !overflow && fifo_empty && fifo_count == 0,
                  "asynchronous reset must clear RX/FIFO/errors");
            repeat (4) @(negedge clk);
            resetn = 1'b1;
            #(11.0 * BIT_NS);
            settle;
            check(!rx_busy && fifo_empty && !overflow && !frame_error, "reset residue/idle recovery");
        end
    endtask

    // Leave each data bit correct only in its central 40%; inverse elsewhere.
    // This stress frame distinguishes center sampling from boundary sampling.
    task center_window_wave;
        input [7:0] value;
        integer bit_number;
        begin
            expect_event(value, 1'b0, $realtime);
            stimulus_rx = 1'b0; #(BIT_NS);
            for (bit_number = 0; bit_number < 8; bit_number = bit_number + 1) begin
                stimulus_rx = !value[bit_number]; #(0.3 * BIT_NS);
                stimulus_rx = value[bit_number]; #(0.4 * BIT_NS);
                stimulus_rx = !value[bit_number]; #(0.3 * BIT_NS);
            end
            stimulus_rx = 1'b1; #(BIT_NS);
        end
    endtask

    reg [7:0] patterns [0:10];
    integer i, rate, valid_before, error_before, overflow_before, write_before;
    realtime period;
    initial begin
        patterns[0] = "H"; patterns[1] = "e"; patterns[2] = "l";
        patterns[3] = "l"; patterns[4] = "o";
        patterns[5] = 8'h00; patterns[6] = 8'hff; patterns[7] = 8'h55;
        patterns[8] = 8'haa; patterns[9] = 8'h01; patterns[10] = 8'h80;
        #0.002;
        check(fifo_empty && !rx_valid && !frame_error && !overflow, "initial reset");
        repeat (4) @(negedge clk); resetn = 1'b1;
        settle;

        // Truly independent asynchronous, nominal 115200 stream.
        #1.731;
        for (i = 0; i < 11; i = i + 1) send_wave(patterns[i], BIT_NS, 1'b1);
        settle;
        check(good_events == 11 && fifo_count == 11 && !fifo_full, "nominal stream count");
        for (i = 0; i < 11; i = i + 1) read_byte(patterns[i]);
        check(fifo_empty, "nominal stream completely drained");
        $display("CHECK: independent nominal UART Hello + 00/ff/55/aa/01/80, ordered FIFO PASS");

        valid_before = good_events; error_before = error_events;
        #2.317; stimulus_rx = 1'b0; #(BIT_NS / 8.0); stimulus_rx = 1'b1;
        #(11.0 * BIT_NS); settle;
        check(good_events == valid_before && error_events == error_before && fifo_empty && !rx_busy,
              "false start must not emit a character/error/write");
        send_wave(8'h35, BIT_NS, 1'b1); settle; read_byte(8'h35);
        $display("CHECK: false start rejected, next valid frame received PASS");

        write_before = fifo_writes; error_before = error_events;
        send_wave(8'h96, BIT_NS, 1'b0);
        #(12.0 * BIT_NS); // sustained low must not create repeated errors
        check(error_events == error_before + 1 && fifo_writes == write_before && fifo_empty && rx_busy,
              "bad stop must emit one error, no FIFO byte, and wait for high");
        stimulus_rx = 1'b1; #(BIT_NS); settle;
        send_wave(8'hc3, BIT_NS, 1'b1); settle; read_byte(8'hc3);
        $display("CHECK: bad stop frame_error pulse, error frame discarded, break recovery PASS");

        // FIFO fill/drop-new through real UART, then simultaneous full read/write.
        overflow_before = overflow_events;
        for (i = 0; i < 20; i = i + 1) send_wave(8'h40 + i, BIT_NS, 1'b1);
        settle;
        check(fifo_full && fifo_count == 16 && overflow_events == overflow_before + 4,
              "20 serial bytes must fill 16 slots and overflow exactly 4 times");
        fork
            send_wave(8'ha5, BIT_NS, 1'b1);
            begin
                @(negedge clk);
                while (!rx_valid) @(negedge clk);
                check(fifo_full && fifo_data == 8'h40, "full simultaneous read must consume oldest byte");
                fifo_read = 1'b1;
                @(negedge clk); fifo_read = 1'b0;
            end
        join
        settle;
        check(fifo_full && fifo_count == 16 && simultaneous_full == 1 &&
              overflow_events == overflow_before + 4, "full simultaneous read/write must accept new byte without overflow");
        for (i = 1; i < 16; i = i + 1) read_byte(8'h40 + i);
        read_byte(8'ha5);
        check(fifo_empty, "full overflow drain must preserve all old unread bytes");
        $display("CHECK: FIFO full/drop-new/4 overflow pulses/old data/full simultaneous read-write PASS");

        // Real-valued bit periods test faster/slower external transmitters,
        // with all patterns and different phase, without modifying local TX.
        for (rate = 0; rate < 2; rate = rate + 1) begin
            period = (rate == 0) ? BIT_NS / 1.02 : BIT_NS / 0.98;
            #(2.139 + rate * 3.713);
            for (i = 0; i < 11; i = i + 1) send_wave(patterns[i], period, 1'b1);
            settle;
            check(fifo_count == 11, "baud mismatch stream count");
            for (i = 0; i < 11; i = i + 1) read_byte(patterns[i]);
            $display("CHECK: independent UART baud %0d%%, all 11 patterns PASS", (rate == 0) ? 102 : 98);
        end
        for (i = 0; i < 8; i = i + 1) begin
            @(negedge clk); #(CLK_NS * (i + 0.25) / 8.0);
            send_wave(8'h81 ^ (i * 17), BIT_NS, 1'b1);
            settle; read_byte(8'h81 ^ (i * 17));
        end
        center_window_wave(8'h5a); settle; read_byte(8'h5a);
        $display("CHECK: eight asynchronous phases and center-only data windows PASS");

        // Reset in idle, START, DATA, and with unread data. Assert between edges.
        reset_and_quiet;
        send_wave(8'h11, BIT_NS, 1'b1); settle; read_byte(8'h11);
        stimulus_rx = 1'b0; #(BIT_NS / 4.0);
        check(rx_busy, "receiver must be in START before reset");
        reset_and_quiet;
        send_wave(8'h22, BIT_NS, 1'b1); settle; read_byte(8'h22);
        stimulus_rx = 1'b0; #(3.2 * BIT_NS);
        check(rx_busy, "receiver must be active in DATA before reset");
        reset_and_quiet;
        send_wave(8'h33, BIT_NS, 1'b1); settle; read_byte(8'h33);
        send_wave(8'h44, BIT_NS, 1'b1); settle;
        check(fifo_count == 1, "nonempty FIFO reset precondition");
        reset_and_quiet;
        send_wave(8'h55, BIT_NS, 1'b1); settle; read_byte(8'h55);
        $display("CHECK: reset in idle/START/DATA/nonempty FIFO and subsequent reception PASS");

        // Existing TX remains unchanged. Continuous valid/ready Hello stream.
        @(negedge clk); loopback = 1'b1; tx_valid = 1'b1; tx_data = patterns[0];
        for (i = 0; i < 5; i = i + 1) begin
            @(posedge clk);
            while (!tx_ready) @(posedge clk);
            expect_event(patterns[i], 1'b0, $realtime);
            #0.002;
            @(negedge clk);
            if (i == 4) tx_valid = 1'b0;
            else tx_data = patterns[i + 1];
        end
        while (!tx_ready) @(negedge clk);
        settle;
        check(fifo_count == 5, "loopback Hello count");
        for (i = 0; i < 5; i = i + 1) read_byte(patterns[i]);
        #(12.0 * BIT_NS); settle;
        check(fifo_empty && !rx_busy && observed_events == expected_events, "loopback missing/extra byte or unfinished frame");
        check(fifo_unit_done, "direct FIFO boundary regression incomplete");
        $display("CHECK: unchanged uart_tx -> uart_rx -> FIFO, continuous Hello PASS");
        $display("RESULT: PASS uart_rx + fifo + loopback; good=%0d frame_errors=%0d overflow=%0d writes=%0d reads=%0d",
                 good_events, error_events, overflow_events, fifo_writes, fifo_reads);
        test_pass = 1'b1;
        $finish;
    end

    initial begin
        #20_000_000;
        check(1'b0, "timeout: missing RX event or stuck receiver/FIFO");
    end
endmodule

// Direct cycle-level FIFO test covers boundary operations that serial input
// cannot produce at consecutive clk edges. Uses a shifted software queue.
module uart_fifo_unit_test(input wire clk, output reg done = 1'b0);
    reg resetn = 1'b0, wr_en = 1'b0, rd_en = 1'b0;
    reg [7:0] write_data = 8'd0;
    wire [7:0] read_data;
    wire empty, full, overflow;
    wire [4:0] count;
    reg [7:0] reference_queue [0:15];
    integer reference_count = 0, cycles = 0, i, round, n;
    reg pop_now, push_now, expected_overflow;
    uart_rx_fifo dut (
        .clk(clk), .resetn(resetn), .wr_en(wr_en), .write_data(write_data),
        .rd_en(rd_en), .read_data(read_data), .empty(empty), .full(full),
        .count(count), .overflow(overflow)
    );

    task check;
        input condition;
        input [1023:0] message;
        begin
            if (condition !== 1'b1) begin
                $display("RESULT: FAIL FIFO cycle=%0d: %0s", cycles, message);
                $fatal(1, "%0s", message);
            end
        end
    endtask

    task cycle;
        input write_request, read_request;
        input [7:0] value;
        begin
            @(negedge clk); wr_en = write_request; rd_en = read_request; write_data = value;
            pop_now = read_request && reference_count != 0;
            push_now = write_request && (reference_count < 16 || pop_now);
            expected_overflow = write_request && !push_now;
            if (pop_now) begin
                check(read_data === reference_queue[0], "pre-edge head/read order");
                for (n = 0; n < 15; n = n + 1) reference_queue[n] = reference_queue[n + 1];
                reference_count = reference_count - 1;
            end
            if (push_now) begin
                reference_queue[reference_count] = value;
                reference_count = reference_count + 1;
            end
            @(posedge clk); #0.002; cycles = cycles + 1;
            check(count === reference_count[4:0] && empty === (reference_count == 0) && full === (reference_count == 16),
                  "post-edge count/empty/full");
            check(read_data === ((reference_count == 0) ? 8'd0 : reference_queue[0]), "post-edge head/overwrite");
            check(overflow === expected_overflow, "overflow/drop-new/full read-write semantics");
        end
    endtask

    initial begin
        #0.002; check(empty && count == 0 && !overflow, "initial reset");
        @(negedge clk); resetn = 1'b1;
        cycle(0, 1, 0); // empty read ignored
        cycle(1, 1, 8'h55); // empty simultaneous: store, no bypass
        check(count == 1 && read_data == 8'h55, "empty read-write stores one byte");
        cycle(0, 1, 0);
        for (i = 0; i < 16; i = i + 1) cycle(1, 0, i);
        cycle(1, 0, 8'hee); cycle(1, 0, 8'hef);
        cycle(0, 0, 0); check(!overflow, "overflow clears without rejected write");
        cycle(1, 1, 8'ha5); // full simultaneous: free then replace
        for (i = 0; i < 16; i = i + 1) cycle(0, 1, 0);
        cycle(0, 1, 0);
        for (round = 0; round < 3; round = round + 1) begin
            for (i = 0; i < 16; i = i + 1) cycle(1, 0, i + 32 * round);
            for (i = 0; i < 16; i = i + 1) cycle(0, 1, 0);
        end
        for (i = 0; i < 7; i = i + 1) cycle(1, 0, i);
        for (i = 0; i < 40; i = i + 1) cycle(1, 1, 8'h80 + i);
        for (i = 0; i < 7; i = i + 1) cycle(0, 1, 0);
        for (i = 0; i < 16; i = i + 1) cycle(1, 0, i);
        cycle(1, 0, 8'hff); check(overflow, "reset overflow precondition");
        @(negedge clk); #0.2; resetn = 1'b0;
        #0.001; check(empty && !full && count == 0 && !overflow && read_data == 0, "async reset clears full FIFO/overflow");
        wr_en = 0; rd_en = 0; reference_count = 0;
        repeat (3) @(negedge clk); resetn = 1'b1;
        cycle(1, 0, 8'hc7); cycle(0, 1, 0);
        @(negedge clk); wr_en = 0; rd_en = 0;
        $display("CHECK: direct FIFO empty/full/consecutive read-write/simultaneous/wrap/reset, %0d cycles PASS", cycles);
        done = 1'b1;
    end
endmodule
