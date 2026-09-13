`timescale 1ns / 1ps
//==========================================================================
// topcpu_gate : 在用户版基础上只改"复位释放的时序关系"
//   核心: 让 CPU 侧的复位比 ROM 侧的复位晚一拍释放
//   -> ROM 在整个复位期间地址端口都是 word0(复位向量)
//   -> ROM 的同步复位释放后有一整个周期把 mem[0] 打出来
//   -> 下一沿 if_id 锁到 (pc=0, mem[0])
//==========================================================================
module topcpu_gate(
    input  wire        clk,
    input  wire        resetn,
    output wire [31:0] debug_pc,
    output wire [31:0] debug_inst
);

    //---- 复位同步/延迟一级: CPU 控制逻辑用的复位比 resetn 晚一拍释放 ----
    reg resetn_1;
    always @(posedge clk) resetn_1 <= resetn;
    wire pc_hold = !resetn;      // 复位中 + 复位释放后一拍,都保持

    wire [31:0] inst_sram_addr;
    wire [31:0] inst;
    inst_rom u_inst_rom(
        .addr(inst_sram_addr[11:2]),
        .clk(clk),
        .rst(!resetn),             // ROM 用原始 resetn(早一拍释放)
        .rd_data(inst)
    );

    reg  [31:0] pc;
    wire [31:0] next_pc     = pc + 32'd4;
    wire [31:0] pc_next     = pc_hold ? pc : next_pc;   // ★ 复位期间 next_pc = pc
    assign      inst_sram_addr = pc_next;

    always @(posedge clk) begin
        if (!resetn)      pc <= 32'h0000_0000;
        else if (!pc_hold) pc <= next_pc;
    end

    reg [31:0] if_id_inst;
    reg [31:0] if_id_pc;
    reg        if_id_valid;
    always @(posedge clk) begin
        if (!resetn) begin
            if_id_inst  <= 32'h0000_0000;
            if_id_pc    <= 32'h0000_0000;
            if_id_valid <= 1'b0;
        end else begin
            if_id_inst  <= inst;
            if_id_pc    <= pc;
            if_id_valid <= 1'b1;
        end
    end

    assign debug_pc   = if_id_pc;
    assign debug_inst = if_id_inst;

endmodule
