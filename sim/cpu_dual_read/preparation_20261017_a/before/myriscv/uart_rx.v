`timescale 1ns / 1ps

// Standalone 8N1 receiver, LSB first, center sampling at the rounded baud rate.
// rx is asynchronous: only the second synchronizer stage reaches the FSM.
// rx_valid: one clk pulse with a new rx_data, only for a high stop sample.
// frame_error: one clk pulse for a low stop sample; rx_valid stays low and
// rx_data retains the last good byte. Wait for high after an invalid stop.
// resetn asserts asynchronously; the caller must synchronize its release.
module uart_rx #(
    parameter integer CLK_HZ = 93_750_000,
    parameter integer BAUD = 115_200
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire       rx,
    output reg  [7:0] rx_data,
    output reg        rx_valid,
    output reg        frame_error,
    output wire       rx_busy
);
    // Valid configuration: positive parameters, rounded BIT_CYCLES >= 2.
    localparam integer BIT_CYCLES = (CLK_HZ + BAUD / 2) / BAUD;
    localparam integer HALF_CYCLES = BIT_CYCLES / 2;
    localparam integer COUNT_WIDTH = (BIT_CYCLES <= 1) ? 1 : $clog2(BIT_CYCLES);
    localparam [COUNT_WIDTH-1:0] LAST_BIT = BIT_CYCLES - 1;
    localparam [COUNT_WIDTH-1:0] LAST_HALF = HALF_CYCLES - 1;
    localparam [2:0] IDLE = 3'd0, START = 3'd1, DATA = 3'd2,
                     STOP = 3'd3, WAIT_HIGH = 3'd4;

    reg rx_meta;
    reg rx_sync;
    reg rx_previous;
    reg [2:0] state;
    reg [COUNT_WIDTH-1:0] sample_count;
    reg [2:0] bit_index;
    reg [7:0] data_shift;

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            rx_meta     <= 1'b1;
            rx_sync     <= 1'b1;
            rx_previous <= 1'b1;
        end else begin
            rx_meta     <= rx;
            rx_sync     <= rx_meta;
            rx_previous <= rx_sync;
        end
    end

    assign rx_busy = (state != IDLE);

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state        <= IDLE;
            sample_count <= {COUNT_WIDTH{1'b0}};
            bit_index    <= 3'd0;
            data_shift   <= 8'd0;
            rx_data      <= 8'd0;
            rx_valid     <= 1'b0;
            frame_error  <= 1'b0;
        end else begin
            rx_valid    <= 1'b0;
            frame_error <= 1'b0;
            case (state)
                IDLE: begin
                    sample_count <= {COUNT_WIDTH{1'b0}};
                    bit_index    <= 3'd0;
                    if (rx_previous && !rx_sync)
                        state <= START;
                end
                START: begin
                    if (sample_count == LAST_HALF) begin
                        sample_count <= {COUNT_WIDTH{1'b0}};
                        if (!rx_sync)
                            state <= DATA;
                        else
                            state <= IDLE; // reject false start at its center
                    end else begin
                        sample_count <= sample_count + 1'b1;
                    end
                end
                DATA: begin
                    if (sample_count == LAST_BIT) begin
                        sample_count <= {COUNT_WIDTH{1'b0}};
                        data_shift[bit_index] <= rx_sync;
                        if (bit_index == 3'd7)
                            state <= STOP;
                        else
                            bit_index <= bit_index + 3'd1;
                    end else begin
                        sample_count <= sample_count + 1'b1;
                    end
                end
                STOP: begin
                    if (sample_count == LAST_BIT) begin
                        sample_count <= {COUNT_WIDTH{1'b0}};
                        if (rx_sync) begin
                            rx_data  <= data_shift;
                            rx_valid <= 1'b1;
                            state    <= IDLE;
                        end else begin
                            frame_error <= 1'b1;
                            state       <= WAIT_HIGH;
                        end
                    end else begin
                        sample_count <= sample_count + 1'b1;
                    end
                end
                WAIT_HIGH: begin
                    if (rx_sync)
                        state <= IDLE;
                end
                default: state <= IDLE;
            endcase
        end
    end
endmodule
