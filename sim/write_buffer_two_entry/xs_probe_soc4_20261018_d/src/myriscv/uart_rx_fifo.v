`timescale 1ns / 1ps

// Small synchronous byte FIFO. read_data is the current head (FWFT), valid
// while !empty; rd_en consumes it on the next rising edge. Empty reads are
// ignored. A simultaneous empty read/write stores the byte, without bypass.
// At full, a simultaneous valid read frees a slot for the write. Otherwise
// a full write drops the NEW byte and pulses overflow for one clk cycle.
// Memory need not be reset: count masks stale entries after reset.
module uart_rx_fifo #(
    parameter integer DEPTH = 16
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire       wr_en,
    input  wire [7:0] write_data,
    input  wire       rd_en,
    output wire [7:0] read_data,
    output wire       empty,
    output wire       full,
    output reg  [((DEPTH < 1) ? 1 : $clog2(DEPTH + 1))-1:0] count,
    output reg        overflow
);
    // DEPTH must be positive; explicit wrapping also permits non-powers of 2.
    localparam integer PTR_WIDTH = (DEPTH <= 1) ? 1 : $clog2(DEPTH);
    localparam integer COUNT_WIDTH = (DEPTH < 1) ? 1 : $clog2(DEPTH + 1);
    localparam [PTR_WIDTH-1:0] LAST_PTR = DEPTH - 1;
    localparam [COUNT_WIDTH-1:0] FULL_COUNT = DEPTH;
    reg [7:0] storage [0:DEPTH-1];
    reg [PTR_WIDTH-1:0] write_ptr;
    reg [PTR_WIDTH-1:0] read_ptr;
    wire read_fire;
    wire write_fire;

    assign empty = (count == 0);
    assign full = (count == FULL_COUNT);
    assign read_data = empty ? 8'd0 : storage[read_ptr];
    assign read_fire = resetn && rd_en && !empty;
    assign write_fire = resetn && wr_en && (!full || read_fire);

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            write_ptr <= {PTR_WIDTH{1'b0}};
            read_ptr  <= {PTR_WIDTH{1'b0}};
            count     <= {COUNT_WIDTH{1'b0}};
            overflow  <= 1'b0;
        end else begin
            overflow <= wr_en && !write_fire;
            if (write_fire) begin
                storage[write_ptr] <= write_data;
                write_ptr <= (write_ptr == LAST_PTR) ? {PTR_WIDTH{1'b0}} : write_ptr + 1'b1;
            end
            if (read_fire)
                read_ptr <= (read_ptr == LAST_PTR) ? {PTR_WIDTH{1'b0}} : read_ptr + 1'b1;
            case ({write_fire, read_fire})
                2'b10: count <= count + 1'b1;
                2'b01: count <= count - 1'b1;
                default: count <= count;
            endcase
        end
    end
endmodule
