`timescale 1ns/1ps

// One focused test, four delay parameters. Compare all external outputs with
// the frozen UART and independently check latency, serial bytes and bus data.
module uart_wait_chain_case #(parameter integer DELAY = 0) (output reg done = 0);
    reg clk = 0, resetn = 0, rx = 1;
    reg valid = 0, write = 0;
    reg [1:0] size = 2;
    reg [31:0] addr = 0, wdata = 0;
    reg [3:0] strb = 0;
    wire [1:0] ready, response, error, tx, irq;
    wire [31:0] rdata [0:1];
    integer accepted = 0, responses = 0, transactions = 0, decoded = 0;
    integer bit_no;
    reg [7:0] received;
    always #5 clk = ~clk;

    uart_mmio_baseline #(.CLK_HZ(100_000_000), .BAUD(10_000_000),
                         .RSP_DELAY_CYCLES(DELAY)) baseline (
        .clk(clk), .resetn(resetn), .req_valid(valid), .req_write(write),
        .req_size(size), .req_addr(addr), .req_wdata(wdata), .req_wstrb(strb),
        .req_ready(ready[0]), .rsp_valid(response[0]), .rsp_rdata(rdata[0]),
        .rsp_error(error[0]), .uart_rx(rx), .uart_tx(tx[0]), .uart_irq(irq[0])
    );
    uart_mmio #(.CLK_HZ(100_000_000), .BAUD(10_000_000),
                .RSP_DELAY_CYCLES(DELAY)) optimized (
        .clk(clk), .resetn(resetn), .req_valid(valid), .req_write(write),
        .req_size(size), .req_addr(addr), .req_wdata(wdata), .req_wstrb(strb),
        .req_ready(ready[1]), .rsp_valid(response[1]), .rsp_rdata(rdata[1]),
        .rsp_error(error[1]), .uart_rx(rx), .uart_tx(tx[1]), .uart_irq(irq[1])
    );
    task check(input condition, input [1023:0] message);
        if (condition !== 1'b1) begin
            $display("RESULT: FAIL uart_wait_chain delay=%0d t=%0t %0s", DELAY, $time, message);
            $fatal(1, "%0s", message);
        end
    endtask
    always @(negedge clk) begin
        #1;
        check({ready[0],response[0],error[0],rdata[0],tx[0],irq[0]} ===
              {ready[1],response[1],error[1],rdata[1],tx[1],irq[1]},
              "external outputs differ from frozen baseline");
    end
    always @(posedge clk) if (resetn) begin
        if (valid && ready[1]) accepted = accepted + 1;
        if (response[1]) responses = responses + 1;
    end

    task transact(input wr, input [31:0] address, input [31:0] data,
                  input [3:0] mask, input [1:0] access_size,
                  input [31:0] expected, input expected_error);
        integer before_accept, before_response, tick;
        begin
            @(negedge clk);
            before_accept = accepted; before_response = responses;
            valid = 1; write = wr; addr = address; wdata = data;
            strb = mask; size = access_size;
            @(posedge clk);
            check(ready[1], "request was not accepted at expected edge");
            #1;
            for (tick = 0; tick <= DELAY; tick = tick + 1) begin
                check(!ready[1], "pending request must block another acceptance");
                check(response[1] === (tick == DELAY), "response edge changed");
                if (tick < DELAY) begin
                    // Keep valid held, but change already-accepted payload.
                    @(negedge clk); addr = 32'h100; wdata = 0; strb = 0;
                    @(posedge clk); #1;
                end
            end
            check(rdata[1] === expected && error[1] === expected_error,
                  "latched response data/error incorrect");
            @(negedge clk); valid = 0; addr = 32'h100; wdata = 0;
            @(posedge clk); #1;
            check(ready[1] && !response[1], "response not consumed exactly once");
            check(accepted == before_accept + 1 && responses == before_response + 1,
                  "request/response count not conserved");
            transactions = transactions + 1;
        end
    endtask
    task wave(input [7:0] byte_value, input stop_bit);
        integer k;
        begin
            #3; rx = 0; #100;
            for (k = 0; k < 8; k = k + 1) begin rx = byte_value[k]; #100; end
            rx = stop_bit; #100; rx = 1; #200;
        end
    endtask
    // Independent pin-level decoder; no internal FIFO/TX state is inspected.
    always begin
        @(negedge tx[1]);
        if (resetn) begin
            check(decoded == 0, "unexpected repeated/extra TX frame");
            #50; check(tx[1] === 0, "TX start bit");
            for (bit_no = 0; bit_no < 8; bit_no = bit_no + 1) begin
                #100; received[bit_no] = tx[1];
            end
            #100; check(tx[1] === 1 && received === 8'ha5, "TX byte or stop bit");
            decoded = decoded + 1;
        end
    end

    initial begin
        repeat (5) @(negedge clk); resetn = 1;
        transact(0,8,0,0,2,1,0);
        transact(1,0,32'ha5,1,0,0,0);
        transact(1,0,32'h58,1,0,0,1); // busy must discard X
        transact(1,1,32'h5800,2,0,0,0);
        transact(1,2,32'h12340000,12,1,0,0);
        transact(1,0,32'h58,0,2,0,0);
        repeat (120) @(negedge clk);
        check(decoded == 1, "one accepted TX store must produce one frame");
        transact(0,8,0,0,2,1,0);
        $display("CHECK: uart_wait_chain delay=%0d latency/held-valid/TX/lanes PASS", DELAY);

        transact(1,12,32'h100,1,2,0,0); // wrong lane cannot enable IRQ
        check(!irq[1], "masked IRQ enable");
        transact(1,13,32'h100,2,0,0,0);
        wave(8'h41,1); wave(8'h42,1);
        transact(0,8,0,0,2,32'hc5,0);
        transact(0,5,0,0,0,32'h41,0); // upper RX lane cannot pop
        transact(0,4,0,0,2,32'h41,0);
        check(irq[1], "IRQ must stay high for second byte");
        transact(0,4,0,0,2,32'h42,0);
        check(!irq[1], "last pop must remove IRQ");
        transact(0,8,0,0,2,32'h41,0);
        transact(0,4,0,0,2,0,0);
        transact(1,13,32'h300,2,0,0,0); // disable wins
        transact(0,12,0,0,2,0,0);
        $display("CHECK: uart_wait_chain delay=%0d RX/order/no-repeat/empty/IRQ PASS", DELAY);

        transact(0,16,0,0,2,0,1);
        transact(0,0,0,0,2,0,1);
        transact(1,8,0,15,2,1,1);
        transact(0,5,0,0,2,0,1);
        transact(0,8,0,0,3,0,1);
        wave(8'h96,0);
        transact(0,8,0,0,2,32'h11,0);
        transact(1,12,1,2,2,0,0); // wrong W1C lane
        transact(0,8,0,0,2,32'h11,0);
        transact(1,12,1,1,2,0,0);
        transact(0,8,0,0,2,1,0);
        $display("CHECK: uart_wait_chain delay=%0d access-fault/frame/W1C PASS", DELAY);

        // Cancel a newly accepted request before its response-sampling edge,
        // including delay 0 where response is already visible between edges.
        @(negedge clk); valid = 1; write = 0; addr = 8; size = 2;
        @(posedge clk); check(ready[1], "reset cancellation request acceptance");
        #1;
        @(negedge clk); valid = 0; resetn = 0;
        #1; check(!ready[1] && !response[1] && !irq[1] && tx[1], "reset pending cancellation");
        repeat (3) @(negedge clk); resetn = 1;
        transact(0,8,0,0,2,1,0);
        check(accepted == responses + 1 && responses == transactions,
              "exactly one canceled request expected");
        $display("CHECK: uart_wait_chain delay=%0d reset/canceled=1 PASS", DELAY);
        $display("RESULT: PASS uart_wait_chain delay=%0d transactions=%0d accepted=%0d responses=%0d decoded=%0d canceled=1",
                 DELAY, transactions, accepted, responses, decoded);
        done = 1;
    end
endmodule

module tb_wait_chain;
    wire [3:0] done;
    uart_wait_chain_case #(.DELAY(0)) zero_delay(done[0]);
    uart_wait_chain_case #(.DELAY(1)) one_delay(done[1]);
    uart_wait_chain_case #(.DELAY(2)) power_of_two_delay(done[2]);
    uart_wait_chain_case #(.DELAY(6)) existing_tb_delay(done[3]);
    initial begin
        wait (&done);
        $display("RESULT: PASS uart_wait_chain_all modes=4");
        $finish;
    end
    initial begin
        #100000;
        $fatal(1, "RESULT: FAIL uart_wait_chain timeout");
    end
endmodule
