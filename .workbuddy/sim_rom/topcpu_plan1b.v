`timescale 1ns / 1ps
// 方案一-B: addr = pc_r,指令不寄存,组合直通 ID
// 真 IP 下:不需要门控、也不需要多保持一拍
module topcpu_plan1b(
    input  wire        clk,
    input  wire        resetn,
    output wire [31:0] debug_pc,
    output wire [31:0] debug_inst
);
    reg  [31:0] pc_r;
    reg  [31:0] if_id_pc;
    reg         if_id_valid;
    wire [31:0] inst;

    inst_rom u_inst_rom(
        .addr(pc_r[11:2]),          // ★ 以 PC 作读地址
        .clk(clk),
        .rst(!resetn),
        .rd_data(inst)
    );

    always @(posedge clk) begin
        if (!resetn) pc_r <= 32'h0000_0000;
        else         pc_r <= pc_r + 32'd4;
    end

    always @(posedge clk) begin
        if (!resetn) begin
            if_id_pc    <= 32'h0000_0000;
            if_id_valid <= 1'b0;
        end else begin
            if_id_pc    <= pc_r;    // 只寄存 PC
            if_id_valid <= 1'b1;
        end
    end

    assign debug_pc   = if_id_pc;
    assign debug_inst = inst;       // ★ 指令不寄存

endmodule
