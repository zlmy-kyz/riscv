`timescale 1ns/1ps
// Sixteen consecutive samples of ONE channel, not interleaved HWC.
// Scheduler must provide the channel order. Reset cancels a partial group.
module cnn_gap16 (
    input wire clk, resetn,
    input wire in_valid,
    output wire in_ready,
    input wire [7:0] in_data,
    output reg out_valid,
    input wire out_ready,
    output reg [7:0] out_data,
    output reg out_error
);
    reg [3:0] count;
    reg [11:0] sum;
    reg group_error;
    wire [12:0] next_sum = {1'b0,sum}+{5'b0,in_data};
    wire [12:0] rounded_sum = next_sum+13'd8;
    assign in_ready = !out_valid;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            count<=0; sum<=0; group_error<=0;
            out_valid<=0; out_data<=0; out_error<=0;
        end else begin
            if (out_valid && out_ready) out_valid<=0;
            if (in_valid && in_ready) begin
                if (count==15) begin
                    out_data<=rounded_sum[11:4];
                    out_error<=group_error || in_data[7];
                    out_valid<=1;
                    count<=0; sum<=0; group_error<=0;
                end else begin
                    count<=count+1'b1;
                    sum<=next_sum[11:0];
                    if (in_data[7]) group_error<=1;
                end
            end
        end
    end
endmodule
