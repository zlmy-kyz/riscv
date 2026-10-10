`timescale 1ns/1ps
// Isolated synchronous BRAM models; reset does NOT reload RAM contents.
module inst_rom(input [11:0] addr, input clk,rst, output [31:0] rd_data);
    reg [31:0] mem[0:4095];
    reg [11:0] addr_r=0;
    reg rst_d1=1;
    string path;
    initial begin
        if (!$value$plusargs("ROM=%s",path)) $fatal(1,"RESULT: FAIL missing ROM");
        $readmemh(path,mem);
    end
    always @(posedge clk) begin rst_d1<=rst; addr_r<=addr; end
    assign rd_data = rst_d1 ? 0 : mem[addr_r];
endmodule
module data_ram(input [31:0] wr_data,input [11:0] addr,input wr_en,
                input [3:0] wr_byte_en,input clk,rst,output [31:0] rd_data);
    reg [31:0] mem[0:4095];
    reg [11:0] addr_r=0;
    reg rst_d1=1;
    integer lane;
    string path;
    initial begin
        if (!$value$plusargs("RAM=%s",path)) $fatal(1,"RESULT: FAIL missing RAM");
        $readmemh(path,mem);
    end
    always @(posedge clk) begin
        rst_d1<=rst; addr_r<=addr;
        if (wr_en && !rst) for (lane=0;lane<4;lane=lane+1)
            if (wr_byte_en[lane]) mem[addr][lane*8+:8]<=wr_data[lane*8+:8];
    end
    assign rd_data = rst_d1 ? 0 : mem[addr_r];
endmodule
