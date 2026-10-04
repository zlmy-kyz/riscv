`timescale 1ns/1ps
// 诊断4:jal / jalr 逐拍追踪
//   程序与 TEST_G 相同。
//   关注:jal(PC 0x04) 与 jalr(PC 0x14) 各自在 ID 级算出的 bj_pc、
//         进到 EX/MEM 后的值、mem_taken / flush / next_pc 的节拍。
module tb_diag4;
    reg clk = 0, resetn = 0;
    always #5 clk = ~clk;
    integer k = 0;
    mycpu_sync u_dut (.clk(clk), .resetn(resetn));

    initial begin
        $display("=== jal/jalr 逐拍追踪 ===");
        $display(" time | pc    | if_id: pc inst      v | id_ex: pc   bj_pc    is_j is_b rs1 r1v imm  v | ex_mem: pc   bj_pc    is_j is_b v | flush next_pc");
        repeat (46) @(posedge clk) begin
            #1;
            $display("%5t | %h | %h %h %b | %h %h %b %b x%0d %h %h %b | %h %h %b %b %b | %b %h",
              $time, u_dut.pc,
              u_dut.if_id_pc, u_dut.if_id_inst, u_dut.if_id_valid,
              u_dut.id_ex_pc, u_dut.id_ex_bj_pc, u_dut.id_ex_is_j, u_dut.id_ex_is_b,
              u_dut.id_ex_rs1, u_dut.id_ex_rs1_val, u_dut.id_ex_imm, u_dut.id_ex_valid,
              u_dut.ex_mem_pc, u_dut.ex_mem_bj_pc, u_dut.ex_mem_is_j, u_dut.ex_mem_is_b,
              u_dut.ex_mem_valid,
              u_dut.flush, u_dut.next_pc);
            if (resetn === 1'b0 && k == 3) resetn = 1'b1;
            k = k + 1;
        end
        $display("--- 寄存器最终值 ---");
        $display("x1=%h x2=%h x3=%h x4=%h x5=%h x6=%h x20=%h x21=%h x22=%h x23=%h",
            u_dut.u_regfile.rf[1], u_dut.u_regfile.rf[2], u_dut.u_regfile.rf[3],
            u_dut.u_regfile.rf[4], u_dut.u_regfile.rf[5], u_dut.u_regfile.rf[6],
            u_dut.u_regfile.rf[20], u_dut.u_regfile.rf[21],
            u_dut.u_regfile.rf[22], u_dut.u_regfile.rf[23]);
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
        mem[ 0] = 32'h00500093;  // 0x00  addi  x1, x0, 0x05
        mem[ 1] = 32'h00C0016F;  // 0x04  jal   x2, +12   -> 0x10, link 0x08
        mem[ 2] = 32'h11100A13;  // 0x08  错路哨兵 x20
        mem[ 3] = 32'h22200A93;  // 0x0C  错路哨兵 x21
        mem[ 4] = 32'h00700193;  // 0x10  addi  x3, x0, 0x07
        mem[ 5] = 32'h02008267;  // 0x14  jalr  x4, x1, 0x20 -> 5+0x20=0x25 -> 0x24
        mem[ 6] = 32'h33300B13;  // 0x18  错路哨兵 x22
        mem[ 7] = 32'h44400B93;  // 0x1C  错路哨兵 x23
        mem[ 8] = 32'h00900293;  // 0x20  addi  x5, x0, 0x09
        mem[ 9] = 32'h00B00313;  // 0x24  addi  x6, x0, 0x0B
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
