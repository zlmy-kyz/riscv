`timescale 1ns / 1ps
//==========================================================================
// 方案一-B:以 PC(pc_r)作 ROM 读地址,只把 PC 寄存进 if_id,
//          「指令不寄存」—— rd_data 组合直通 ID 阶段。
//   不变式:rd_data(t) == mem[if_id_pc(t)]
//     if_id_pc(t)  = pc_r(t-1)
//     rd_data(t)   = mem[ROMreg(t)] = mem[pc_r(t-1)]
//   → PC 与指令天然配对,且 5 级、不依赖 IP 复位行为。
//==========================================================================
module ifu(
    input  wire        clk,
    input  wire        resetn,
    input  wire [31:0] next_pc,

    output wire [31:0] pc,

    output wire [31:0] if_id_pc,
    output wire [31:0] if_id_inst,
    output reg         if_id_valid,

    output wire [31:0] inst_sram_addr,
    input  wire [31:0] inst_sram_rdata
);
    parameter RESET_VECTOR = 32'h0000_0000;

    reg [31:0] pc_r;
    always @(posedge clk) begin
        if (!resetn) pc_r <= RESET_VECTOR;
        else         pc_r <= next_pc;
    end

    reg [31:0] if_id_pc_r;
    always @(posedge clk) begin
        if (!resetn) if_id_pc_r <= 32'h0;
        else         if_id_pc_r <= pc_r;
    end

    always @(posedge clk) begin
        if (!resetn) if_id_valid <= 1'b0;
        else         if_id_valid <= 1'b1;
    end

    assign pc             = pc_r;
    assign inst_sram_addr = pc_r;          // ★ 以 PC 作读地址
    assign if_id_pc       = if_id_pc_r;
    assign if_id_inst     = inst_sram_rdata;   // ★ 指令不寄存,组合直通
endmodule
