`timescale 1ns/1ps
// One RGB888/HWC byte per accepted input, R first. NOT a native DDR port.
// A future DMA serializer must buffer unbackpressurable DDR returns.
// Partial output is invalid if error=1. Reset cancels the whole job.
module cnn_rgb96_gray32 (
    input wire clk, resetn,
    input wire start_valid,
    output wire start_ready,
    input wire in_valid,
    output wire in_ready,
    input wire [7:0] in_data,
    input wire in_last,
    output reg out_valid,
    input wire out_ready,
    output reg signed [7:0] out_data,
    output reg [9:0] out_index,
    output reg busy, done, error,
    output reg [14:0] input_bytes,
    output reg [10:0] output_bytes
);
    localparam FEED=0, GRAY=1, FINISH=2;
    reg [1:0] state, channel, xphase, yphase;
    reg [6:0] x, y;
    reg [15:0] red_term, green_term, blue_term;
    reg [10:0] produced;
    wire selected = (xphase==1 && yphase==1);
    wire [15:0] gray_sum = red_term + green_term + blue_term + 16'd128;
    assign start_ready = !busy && !out_valid;
    assign in_ready = busy && state==FEED && !out_valid;
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=FEED; channel<=0; xphase<=0; yphase<=0;
            x<=0; y<=0; red_term<=0; green_term<=0; blue_term<=0;
            produced<=0; out_valid<=0; out_data<=0; out_index<=0;
            busy<=0; done<=0; error<=0; input_bytes<=0; output_bytes<=0;
        end else begin
            if (out_valid && out_ready) begin
                out_valid<=0;
                output_bytes<=output_bytes+1'b1;
            end
            if (start_valid && start_ready) begin
                state<=FEED; channel<=0; xphase<=0; yphase<=0;
                x<=0; y<=0; produced<=0;
                busy<=1; done<=0; error<=0; input_bytes<=0; output_bytes<=0;
            end else if (busy) begin
                case (state)
                    FEED: if (in_valid && in_ready) begin
                        input_bytes<=input_bytes+1'b1;
                        // Exactly one LAST on byte 27647. No silent short frame.
                        if (in_last != (input_bytes==15'd27647)) begin
                            busy<=0; error<=1; done<=0; out_valid<=0;
                        end else begin
                            if (selected) begin
                                case (channel)
                                    0: red_term <= {8'b0,in_data} * 16'd77;
                                    1: green_term <= {8'b0,in_data} * 16'd150;
                                    2: begin
                                        blue_term <= {8'b0,in_data} * 16'd29;
                                        state<=GRAY;
                                    end
                                endcase
                            end
                            if (channel==2) begin
                                channel<=0;
                                if (x==95) begin
                                    x<=0; xphase<=0; y<=y+1'b1;
                                    yphase <= yphase==2 ? 0 : yphase+1'b1;
                                end else begin
                                    x<=x+1'b1;
                                    xphase <= xphase==2 ? 0 : xphase+1'b1;
                                end
                            end else channel<=channel+1'b1;
                            if (in_last) state<=FINISH;
                        end
                    end
                    GRAY: begin
                        out_data <= gray_sum[15:8] ^ 8'h80;
                        out_index <= produced[9:0];
                        produced <= produced+1'b1;
                        out_valid<=1;
                        state<=FEED;
                    end
                    FINISH: if (!out_valid) begin
                        busy<=0;
                        if (produced==1024 && output_bytes==1024) done<=1;
                        else error<=1;
                    end
                    default: begin busy<=0; error<=1; done<=0; end
                endcase
            end
        end
    end
endmodule
