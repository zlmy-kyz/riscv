`timescale 1ns / 1ps

// Simulation-only replacements for the two on-chip memory IPs.  The DDR3
// controller and external DDR3 model remain the real Pango simulation models.
// The default ROM keeps the step-1 store/load/fetch test reproducible.
// DDR_REGRESSION selects the step-2 lane/mask/boundary/DDR-code program.
module inst_rom (
    input  wire [11:0] addr,
    input  wire        clk,
    input  wire        rst,
    output reg  [31:0] rd_data
);
    always @(posedge clk) begin
`ifdef DDR_REGRESSION
        case (addr)
            12'h000: rd_data <= 32'h4000_00b7; // lui  x1,0x40000
            12'h001: rd_data <= 32'h0110_0113; // addi x2,x0,0x11
            12'h002: rd_data <= 32'h0020_a023; // sw   x2,0(x1)
            12'h003: rd_data <= 32'h0220_0113; // addi x2,x0,0x22
            12'h004: rd_data <= 32'h0020_a223; // sw   x2,4(x1)
            12'h005: rd_data <= 32'h0330_0113; // addi x2,x0,0x33
            12'h006: rd_data <= 32'h0020_a423; // sw   x2,8(x1)
            12'h007: rd_data <= 32'h0440_0113; // addi x2,x0,0x44
            12'h008: rd_data <= 32'h0020_a623; // sw   x2,12(x1)
            12'h009: rd_data <= 32'h0550_0113; // addi x2,x0,0x55
            12'h00a: rd_data <= 32'h0020_a823; // sw   x2,16(x1)
            12'h00b: rd_data <= 32'h0000_a503; // lw   x10,0(x1)
            12'h00c: rd_data <= 32'h0040_a503; // lw   x10,4(x1)
            12'h00d: rd_data <= 32'h0080_a503; // lw   x10,8(x1)
            12'h00e: rd_data <= 32'h00c0_a503; // lw   x10,12(x1)
            12'h00f: rd_data <= 32'h0100_a503; // lw   x10,16(x1)
            12'h010: rd_data <= 32'hf800_0113; // addi x2,x0,-128
            12'h011: rd_data <= 32'h0020_82a3; // sb   x2,5(x1)
            12'h012: rd_data <= 32'h0000_8137; // lui  x2,0x8
            12'h013: rd_data <= 32'h0011_0113; // addi x2,x2,1 = 0x8001
            12'h014: rd_data <= 32'h0020_9323; // sh   x2,6(x1)
            12'h015: rd_data <= 32'h0040_a503; // lw   x10,4(x1)
            12'h016: rd_data <= 32'h0050_8503; // lb   x10,5(x1)
            12'h017: rd_data <= 32'h0050_c503; // lbu  x10,5(x1)
            12'h018: rd_data <= 32'h0060_9503; // lh   x10,6(x1)
            12'h019: rd_data <= 32'h0060_d503; // lhu  x10,6(x1)
            12'h01a: rd_data <= 32'h0000_a503; // lw   x10,0(x1)
            12'h01b: rd_data <= 32'h0080_a503; // lw   x10,8(x1)
            12'h01c: rd_data <= 32'hffe0_0113; // addi x2,x0,-2
            12'h01d: rd_data <= 32'h0020_87a3; // sb   x2,15(x1)
            12'h01e: rd_data <= 32'h00c0_a503; // lw   x10,12(x1)
            12'h01f: rd_data <= 32'h0100_a503; // lw   x10,16(x1)
            // Write four instructions into the DDR beat at +0x40.
            12'h020: rd_data <= 32'h00c0_a337; // lui  x6,0x00c0a
            12'h021: rd_data <= 32'h5833_0313; // addi x6,x6,0x583 -> lw x11,12(x1)
            12'h022: rd_data <= 32'h0460_a023; // sw   x6,64(x1)
            12'h023: rd_data <= 32'h0100_a337; // lui  x6,0x0100a
            12'h024: rd_data <= 32'h6033_0313; // addi x6,x6,0x603 -> lw x12,16(x1)
            12'h025: rd_data <= 32'h0460_a223; // sw   x6,68(x1)
            12'h026: rd_data <= 32'h00c5_8337; // lui  x6,0x00c58
            12'h027: rd_data <= 32'h6b33_0313; // addi x6,x6,0x6b3 -> add x13,x11,x12
            12'h028: rd_data <= 32'h0460_a423; // sw   x6,72(x1)
            12'h029: rd_data <= 32'h06f0_0313; // addi x6,x0,0x6f -> jal x0,0
            12'h02a: rd_data <= 32'h0460_a623; // sw   x6,76(x1)
            12'h02b: rd_data <= 32'h0400_8067; // jalr x0,64(x1)
            default: rd_data <= 32'h0000_006f; // jal  x0,0
        endcase
`else
        case (addr)
            12'h000: rd_data <= 32'h4000_00b7; // lui  x1,0x40000
            12'h001: rd_data <= 32'h02a0_0113; // addi x2,x0,42
            12'h002: rd_data <= 32'h0020_a023; // sw   x2,0(x1)
            12'h003: rd_data <= 32'h0000_a183; // lw   x3,0(x1)
            12'h004: rd_data <= 32'h05a0_0337; // lui  x6,0x05a00
            12'h005: rd_data <= 32'h2933_0313; // addi x6,x6,0x293
            12'h006: rd_data <= 32'h0260_a023; // sw   x6,0x20(x1)
            12'h007: rd_data <= 32'h06f0_0393; // addi x7,x0,0x6f
            12'h008: rd_data <= 32'h0270_a223; // sw   x7,0x24(x1)
            12'h009: rd_data <= 32'h0200_8067; // jalr x0,0x20(x1)
            default: rd_data <= 32'h0000_006f; // jal  x0,0
        endcase
`endif
    end
endmodule

module data_ram (
    input  wire [11:0] addr,
    input  wire [31:0] wr_data,
    output reg  [31:0] rd_data,
    input  wire        wr_en,
    input  wire [3:0]  wr_byte_en,
    input  wire        clk,
    input  wire        rst
);
    reg [31:0] words [0:4095];
    integer byte_index;
    always @(posedge clk) begin
        rd_data <= words[addr];
        if (wr_en)
            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
                if (wr_byte_en[byte_index])
                    words[addr][byte_index * 8 +: 8] <=
                        wr_data[byte_index * 8 +: 8];
    end
endmodule
