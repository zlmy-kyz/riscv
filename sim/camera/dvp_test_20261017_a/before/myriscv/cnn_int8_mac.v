`timescale 1ns/1ps
// One dot product per command: bias + exactly term_count signed products.
// Separate registered multiply and add; at most one term every two clocks.
// error accompanies the held result; overflow/weight -128 invalidates the job.
module cnn_int8_mac (
    input wire clk, resetn,
    input wire cmd_valid,
    output wire cmd_ready,
    input wire signed [31:0] bias,
    input wire [15:0] term_count,
    input wire in_valid,
    output wire in_ready,
    input wire signed [7:0] activation, weight,
    output wire out_valid,
    input wire out_ready,
    output wire signed [31:0] out_data,
    output reg out_error
);
    localparam IDLE=0, INPUT_TERM=1, ADD_TERM=2, RESULT=3;
    reg [1:0] state;
    reg [15:0] remaining;
    reg signed [15:0] product;
    reg signed [31:0] accumulator;
    wire signed [32:0] wide_sum =
        {accumulator[31],accumulator} + {{17{product[15]}},product};
    assign cmd_ready = state==IDLE;
    assign in_ready = state==INPUT_TERM;
    assign out_valid = state==RESULT;
    assign out_data = accumulator;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=IDLE; remaining<=0; product<=0; accumulator<=0; out_error<=0;
        end else begin
            case (state)
                IDLE: if (cmd_valid) begin
                    accumulator<=bias; remaining<=term_count; out_error<=0;
                    state <= term_count==0 ? RESULT : INPUT_TERM;
                end
                INPUT_TERM: if (in_valid) begin
                    product <= activation * weight;
                    if (weight==8'sh80) out_error<=1;
                    state<=ADD_TERM;
                end
                ADD_TERM: begin
                    accumulator<=wide_sum[31:0];
                    if (wide_sum[32]!=wide_sum[31]) out_error<=1;
                    remaining<=remaining-1'b1;
                    state <= remaining==1 ? RESULT : INPUT_TERM;
                end
                RESULT: if (out_ready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end
endmodule
