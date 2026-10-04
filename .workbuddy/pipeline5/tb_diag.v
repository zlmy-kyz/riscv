`timescale 1ns/1ps
// 诊断:逐拍列出 IF/ID/EX/MEM/WB 五级的 pc / inst / valid,定位 pc 配对关系
module tb_diag;
    reg clk    = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;
    integer k = 0;

    mycpu_sync u_dut (.clk(clk), .resetn(resetn));

    initial begin
        $display("=== 五级 pc 逐拍(只列 pc 与 valid,inst 用 if_id/id_ex 里的) ===");
        $display(" time | valid |   pc   next_pc addr  inst_if | if_id_pc if_id_inst v | id_ex_pc id_ex_inst v | ex_mem_pc v | mem_wb_pc v");
        repeat (40) @(posedge clk) begin
            #1;
            $display("%5t |   %b   | %h %h %h %h | %h %h %b | %h %h %b | %h %b | %h %b",
                $time, u_dut.valid,
                u_dut.pc, u_dut.next_pc, u_dut.inst_sram_addr, u_dut.inst_if,
                u_dut.if_id_pc, u_dut.if_id_inst, u_dut.if_id_valid,
                u_dut.id_ex_pc, u_dut.id_ex_imm, u_dut.id_ex_valid,
                u_dut.ex_mem_pc, u_dut.ex_mem_valid,
                u_dut.mem_wb_pc, u_dut.mem_wb_valid);
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
        mem[0] = 32'h12345537;  // lui  x10, 0x12345
        mem[1] = 32'h00001597;  // auipc x11, 0x1
        mem[2] = 32'hFFF00613;  // addi x12, x0, -1
        mem[3] = 32'h00461713;  // slli x14, x12, 4
        addr_r = 10'd1;
    end
    always @(posedge clk) addr_r <= addr;
    always @(posedge clk) begin
        if (rst) rd_data <= 32'h0;
        else     rd_data <= mem[addr_r];
    end
endmodule

module data_ram(
    input  wire [ 9:0] addr,
    input  wire [31:0] wr_data,
    output reg  [31:0] rd_data,
    input  wire        wr_en,
    input  wire [ 3:0] wr_byte_en,
    input  wire        clk,
    input  wire        rst
);
    always @(posedge clk) rd_data <= rst ? 32'h0 : wr_data;
endmodule
