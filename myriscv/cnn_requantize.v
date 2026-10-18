`timescale 1ns/1ps
// RHA: nearest, exact halves away from zero. shift=0..31.
// relu_int8=1: result 0..127, zero-extended; otherwise signed INT32 (FC).
module cnn_requantize (
    input wire clk, resetn,
    input wire in_valid,
    output wire in_ready,
    input wire signed [31:0] in_data,
    input wire [4:0] shift,
    input wire relu_int8,
    output wire out_valid,
    input wire out_ready,
    output reg signed [31:0] out_data,
    output reg out_clipped
);
    localparam IDLE=0, ROUND=1, SCALE=2, RESULT=3;
    reg [1:0] state;
    reg negative, clip_mode;
    reg [4:0] shift_reg;
    reg [32:0] magnitude, rounded;
    wire signed [32:0] extended = {in_data[31],in_data};
    wire [32:0] scaled = rounded >> shift_reg;
    wire [32:0] signed_scaled = negative ? (~scaled + 33'd1) : scaled;
    assign in_ready = state==IDLE;
    assign out_valid = state==RESULT;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=IDLE; negative<=0; clip_mode<=0; shift_reg<=0;
            magnitude<=0; rounded<=0; out_data<=0; out_clipped<=0;
        end else begin
            case (state)
                IDLE: if (in_valid) begin
                    negative<=in_data[31]; clip_mode<=relu_int8; shift_reg<=shift;
                    magnitude <= in_data[31] ? -extended : extended;
                    out_clipped<=0;
                    state<=ROUND;
                end
                ROUND: begin
                    if (shift_reg==0) rounded<=magnitude;
                    else rounded<=magnitude+(33'd1 << (shift_reg-1'b1));
                    state<=SCALE;
                end
                SCALE: begin
                    if (clip_mode && negative) begin
                        out_data<=0;
                        out_clipped <= scaled!=0;
                    end else if (clip_mode && scaled>33'd127) begin
                        out_data<=32'd127; out_clipped<=1;
                    end else out_data<=signed_scaled[31:0];
                    state<=RESULT;
                end
                RESULT: if (out_ready) state<=IDLE;
                default: state<=IDLE;
            endcase
        end
    end
endmodule
