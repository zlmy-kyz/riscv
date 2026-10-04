`timescale 1ns/1ps
// 诊断3:store->load 同地址,不同间距,看几拍才拿到新值
module tb_diag3;
    reg clk = 0, resetn = 0;
    always #5 clk = ~clk;
    integer k = 0;
    mycpu_sync u_dut (.clk(clk), .resetn(resetn));

    initial begin
        $display("=== store->load 同地址,间距实验 ===");
        $display(" time | ex_mem: pc    st_we addr  valid | RAM.addr RAM.rd_data | mem_wb: pc rd we wdata");
        repeat (40) @(posedge clk) begin
            #1;
            $display("%5t | %h %b %h %b | %h %h | %h x%0d %b %h",
              $time,
              u_dut.ex_mem_pc, u_dut.ex_mem_st_we, u_dut.ex_mem_addr, u_dut.ex_mem_valid,
              u_dut.ex_mem_addr[11:2], u_dut.data_sram_rdata,
              u_dut.mem_wb_pc, u_dut.mem_wb_rd, u_dut.mem_wb_rf_we, u_dut.rf_wdata);
            if (resetn === 1'b0 && k == 3) resetn = 1'b1;
            k = k + 1;
        end
        $finish;
    end
endmodule

module inst_rom(input wire [9:0] addr, input wire clk, input wire rst,
                output reg [31:0] rd_data);
    reg [31:0] mem [0:1023];
    reg [9:0]  addr_r;
    integer i;
    initial begin
        for (i = 0; i < 1024; i = i + 1) mem[i] = 32'h00000013;
        mem[0] = 32'h01F00093;  // 0x00  addi x1,x0,0x1F
        mem[1] = 32'h00102223;  // 0x04  sw   x1, 4(x0)
        mem[2] = 32'h00000013;  // 0x08  nop        <-- 拉开间距
        mem[3] = 32'h00000013;  // 0x0C  nop
        mem[4] = 32'h00402103;  // 0x10  lw   x2, 4(x0)
        mem[5] = 32'h01010193;  // 0x14  addi x3,x2,0x10
        addr_r = 10'd1;
    end
    always @(posedge clk) addr_r <= addr;
    always @(posedge clk) rd_data <= rst ? 32'h0 : mem[addr_r];
endmodule

module data_ram(
    input  wire [ 9:0] addr, input  wire [31:0] wr_data,
    output reg  [31:0] rd_data, input  wire wr_en,
    input  wire [ 3:0] wr_byte_en, input wire clk, input wire rst
);
    reg [31:0] mem [0:1023];
    integer i;
    initial for (i=0;i<1024;i=i+1) mem[i]=32'h0;
    always @(posedge clk) begin
        if (rst) rd_data <= 32'h0;
        else begin
            if (wr_en) begin
                if (wr_byte_en[0]) mem[addr][ 7: 0] <= wr_data[ 7: 0];
                if (wr_byte_en[1]) mem[addr][15: 8] <= wr_data[15: 8];
                if (wr_byte_en[2]) mem[addr][23:16] <= wr_data[23:16];
                if (wr_byte_en[3]) mem[addr][31:24] <= wr_data[31:24];
            end
            rd_data <= mem[addr];
        end
    end
endmodule
