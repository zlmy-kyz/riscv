`timescale 1ns / 1ps

// Standalone 8N1 transmitter, LSB first. No queue or generated clock.
// Accept tx_data only on a clk edge with tx_valid && tx_ready.
// A pulse while busy is ignored; a valid held until ready is accepted later.
// Inputs must be synchronous to clk; resetn asserts asynchronously and its
// release must be synchronized by the caller, as with the SoC reset domain.
module uart_tx #(
    parameter integer CLK_HZ = 93_750_000,
    parameter integer BAUD = 115_200
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire [7:0] tx_data,
    input  wire       tx_valid,
    output reg        tx,
    output wire       tx_busy,
    output wire       tx_ready
);
    // Valid configuration: CLK_HZ > 0, BAUD > 0, rounded divisor >= 1.
    // At the defaults: 814 clocks/bit, 115171.990 baud (-0.024314%).
    localparam integer BIT_CYCLES = (CLK_HZ + BAUD / 2) / BAUD;
    localparam integer COUNT_WIDTH = (BIT_CYCLES <= 1) ? 1 : $clog2(BIT_CYCLES);
    localparam [COUNT_WIDTH-1:0] LAST_COUNT = BIT_CYCLES - 1;
    localparam [1:0] IDLE = 2'd0, START = 2'd1, DATA = 2'd2, STOP = 2'd3;

    reg [1:0] state;
    reg [COUNT_WIDTH-1:0] bit_count;
    reg [2:0] bit_index;
    reg [7:0] data_latched;

    assign tx_busy = (state != IDLE);
    assign tx_ready = resetn && !tx_busy;

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state        <= IDLE;
            bit_count    <= {COUNT_WIDTH{1'b0}};
            bit_index    <= 3'd0;
            data_latched <= 8'd0;
            tx           <= 1'b1;
        end else if (state == IDLE) begin
            tx        <= 1'b1;
            bit_count <= {COUNT_WIDTH{1'b0}};
            bit_index <= 3'd0;
            if (tx_valid && tx_ready) begin
                data_latched <= tx_data;
                tx           <= 1'b0;
                state        <= START;
            end
        end else if (bit_count == LAST_COUNT) begin
            bit_count <= {COUNT_WIDTH{1'b0}};
            case (state)
                START: begin
                    tx    <= data_latched[0];
                    state <= DATA;
                end
                DATA: begin
                    if (bit_index == 3'd7) begin
                        tx    <= 1'b1;
                        state <= STOP;
                    end else begin
                        bit_index <= bit_index + 3'd1;
                        tx        <= data_latched[bit_index + 3'd1];
                    end
                end
                STOP: begin
                    tx    <= 1'b1;
                    state <= IDLE;
                end
                default: begin
                    tx    <= 1'b1;
                    state <= IDLE;
                end
            endcase
        end else begin
            bit_count <= bit_count + 1'b1;
        end
    end
endmodule
