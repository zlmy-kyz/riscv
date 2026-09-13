`timescale 1ns / 1ps
module tb_topcpu_instrom();
    reg clk;
    reg resetn;
    reg [31:0] wr_data;
    reg [9:0] addr;
    reg wr_en;
    wire [31:0] debug_pc;
    wire [31:0] debug_inst;
    wire [31:0] debug_rd_data;

    wire [31:0] next_pc_dbg;
    wire [31:0] pc_dbg;
    wire [31:0] inst_dbg;
    wire [31:0] inst_sram_addr_dbg;
    wire [31:0] rd_data_dbg;
    wire [31:0] id_ex_dbg;
    wire [31:0] id_ex_inst_dbg;
    wire id_ex_vaild_dbg;
    wire vaild_dbg;
    wire if_id_valid_dbg;
    wire [31:0] if_id_pc_dbg;
    wire [31:0] if_id_inst_dbg;
    assign next_pc_dbg = u_topcpu_insrom.next_pc;
    assign pc_dbg = u_topcpu_insrom.pc;
    assign inst_dbg = u_topcpu_insrom.inst;
    assign inst_sram_addr_dbg = u_topcpu_insrom.inst_sram_addr;
    assign rd_data_dbg = u_topcpu_insrom.rd_data;
    assign vaild_dbg = u_topcpu_insrom.vaild;
    assign if_id_valid_dbg = u_topcpu_insrom.if_id_valid;
    assign if_id_pc_dbg = u_topcpu_insrom.if_id_pc;
    assign if_id_inst_dbg = u_topcpu_insrom.if_id_inst;
    assign id_ex_dbg = u_topcpu_insrom.id_ex_pc;
    assign id_ex_inst_dbg = u_topcpu_insrom.id_ex_inst;
    assign id_ex_vaild_dbg = u_topcpu_insrom.id_ex_valid;

    topcpu_instrom u_topcpu_insrom(
        .clk(clk),
        .resetn(resetn),
        .wr_data(wr_data),
        .addr(addr),
        .wr_en(wr_en),
        .debug_pc(debug_pc),
        .debug_inst(debug_inst),
        .debug_rd_data(debug_rd_data)
    );

    GTP_GRS GRS_INST(
        .GRS_N(1'b1)
    );

    initial begin
        clk = 1'b1;

        forever #5 clk = ~clk;
    end

    initial begin
        resetn = 1'b0;
        wr_en = 1'b0;
        wr_data = 32'haaaaaaaa;
        #95;
        resetn = 1'b1;
        #36;
        addr = 10'h1;
        #10;
        addr = 10'h0;wr_data = 32'hbbbbbbbb;wr_en = 1'b1;
        #10;
        wr_en = 1'b0;
        addr = 10'h1;
        #10;
        addr = 10'h0;
        #1000;
        $finish;
    end



endmodule