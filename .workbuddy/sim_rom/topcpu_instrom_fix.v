`timescale 1ns / 1ps
// 与 topcpu_instrom.v 完全一致,只改一处:
//   if_id 块的复位条件由 !resetn 改成 !vaild(比 resetn 晚一拍)
//   -> 复位释放后那一拍不再往 IF/ID 里写,if_id_valid 保持 0
module topcpu_instrom_fix(
    input  wire        clk,
    input  wire        resetn,
    output wire [31:0] debug_pc,
    output wire [31:0] debug_inst
);
    reg vaild;
    always@(posedge clk)begin
        vaild <= resetn;
    end
    wire [31:0] inst_sram_addr;
    wire [31:0] inst;
    inst_rom u_inst_rom(
        .addr(inst_sram_addr[11:2]),
        .clk(clk),
        .rst(!resetn),
        .rd_data(inst)
    );
    reg[31:0] pc;
    wire[31:0] next_pc;
    assign next_pc = pc + 4;
    assign inst_sram_addr = vaild ? next_pc : pc;
    always@(posedge clk)begin
        if(!resetn)begin
            pc <= 32'h00000000;
        end
        else if(vaild) begin
            pc <= next_pc;
        end
    end
    reg [31:0] if_id_inst;
    reg [31:0] if_id_pc;
    reg if_id_valid;
    always@(posedge clk)begin
        if(!vaild)begin                 // ★★ 唯一改动:!resetn -> !vaild
            if_id_inst <= 32'h00000000;
            if_id_pc <= 32'h00000000;
            if_id_valid <= 1'b0;
        end
        else begin
            if_id_inst <= inst;
            if_id_pc <= pc;
            if_id_valid <= 1'b1;
        end
    end
    assign debug_pc = if_id_pc;
    assign debug_inst = if_id_inst;
endmodule
