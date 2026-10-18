// Behavioral stand-in for the Pango Simple-Multiplier IP.
// Only used by the iverilog branch/redirect regression, which contains no
// multiply instruction; it exists so mycpu_sync elaborates without the
// vendor netlist. Latency mirrors the IP's 4 CE-enabled stages.
`timescale 1ns/1ps
module mul (
    input  wire        ce,
    input  wire        rst,
    input  wire        clk,
    input  wire [32:0] a,
    input  wire [32:0] b,
    output reg  [65:0] p
);
    reg [65:0] s1, s2, s3;
    always @(posedge clk) begin
        if (rst) begin
            s1 <= 66'b0;
            s2 <= 66'b0;
            s3 <= 66'b0;
            p  <= 66'b0;
        end else if (ce) begin
            s1 <= a * b;
            s2 <= s1;
            s3 <= s2;
            p  <= s3;
        end
    end
endmodule
