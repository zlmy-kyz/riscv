`timescale 1ns / 1ps
module tb_dram();
    reg clk, resetn, wr_en;
    reg [31:0] wr_data;
    reg [9:0]  addr;
    wire [31:0] rd_data;

    data_ram u_data_ram (
        .wr_data(wr_data), .addr(addr), .wr_en(wr_en),
        .wr_byte_en(4'b1111), .clk(clk), .rst(~resetn), .rd_data(rd_data)
    );
    GTP_GRS GRS_INST(.GRS_N(1'b1));

    initial begin clk = 1'b1; forever #5 clk = ~clk; end

    initial begin
        resetn = 1'b0; wr_data = 32'h0; addr = 10'h0; wr_en = 1'b0;
        #95; resetn = 1'b1;
        #20;                          // 等内部 rsta_int 真正撤销
        addr = 10'h1; wr_data = 32'haaaaaaaa;   // 数据提前 1 拍建立
        #10;
        wr_en = 1'b1;                 // 此沿写入
        #10;
        wr_en = 1'b0;
        #60;
        addr = 10'h1; #20;
        $display("FIXED  read addr=1 -> %h  (expect aaaaaaaa)", rd_data);
        #20; $finish;
    end
endmodule
