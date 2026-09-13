module inst_rom(input wire [9:0] addr, input wire clk, input wire rst, output wire [31:0] rd_data);
    assign rd_data = 32'h00000013;
endmodule
