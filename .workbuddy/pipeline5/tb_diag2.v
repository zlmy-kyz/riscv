`timescale 1ns/1ps
// 诊断2:store 是否真的写进 RAM;load 是否读到;分支是否重定向
module tb_diag2;
    reg clk = 0, resetn = 0;
    always #5 clk = ~clk;
    integer k = 0;
    mycpu_sync u_dut (.clk(clk), .resetn(resetn));

    initial begin
        $display("=== store/load/branch 诊断 ===");
        $display(" time | pc    | ex_mem: pc  is_b is_j bj_pc    valid | br_taken_ex mem_taken | flush | next_pc | mem_wb: pc rd we");
        repeat (30) @(posedge clk) begin
            #1;
            $display("%5t | %h | %h %b %b %h %b | %b %b | %b | %h | %h x%0d %b",
              $time, u_dut.pc,
              u_dut.ex_mem_pc, u_dut.ex_mem_is_b, u_dut.ex_mem_is_j,
              u_dut.ex_mem_bj_pc, u_dut.ex_mem_valid,
              u_dut.br_taken_ex, u_dut.mem_taken,
              u_dut.flush, u_dut.next_pc,
              u_dut.mem_wb_pc, u_dut.mem_wb_rd, u_dut.mem_wb_rf_we);
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
        mem[0] = 32'h00A00093;  // 0x00  addi x1,x0,0x0A
        mem[1] = 32'h00A00113;  // 0x04  addi x2,x0,0x0A
        mem[2] = 32'h00208663;  // 0x08  beq  x1,x2,+12 -> 0x14  ★应跳
        mem[3] = 32'h77700A13;  // 0x0C  错路
        mem[4] = 32'h88800A93;  // 0x10  错路
        mem[5] = 32'h00108193;  // 0x14  目标
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
