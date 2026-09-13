`timescale 1ns / 1ps

module topcpu_instrom(
    input  wire        clk,
    input  wire        resetn,
    input  wire [31:0] wr_data,
    input  wire [9:0]  addr,
    input  wire        wr_en,
    output wire [31:0] debug_pc,
    output wire [31:0] debug_inst,
    output wire [31:0] debug_rd_data
);
    /*reg vaild;
    always@(posedge clk)begin

        if(!resetn)begin
            vaild <= 1'b0;
        end
        else begin
            vaild <= 1'b1;
        end
    end*/
    reg vaild;
    always@(posedge clk)begin
        if(!resetn)begin
            vaild <= 1'b0;
        end
        else begin
            vaild <= 1'b1;
        end
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
        if(!vaild)begin
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
    reg [31:0] id_ex_inst;
    reg [31:0] id_ex_pc;
    reg id_ex_valid;
    always@(posedge clk)begin
        if(!vaild)begin
            id_ex_inst <= 32'h00000000;
            id_ex_pc <= 32'h00000000;
            id_ex_valid <= 1'b0;
        end
        else begin
            id_ex_inst <= if_id_inst;
            id_ex_pc <= if_id_pc;
            id_ex_valid <= if_id_valid;
        end
    end
    wire [31:0] rd_data;
    data_ram u_data_ram (
        .wr_data(wr_data),          // input [31:0]
        .addr(addr),                // input [9:0]
        .wr_en(wr_en),              // input
        .wr_byte_en(4'b1111),    // input [3:0]
        .clk(clk),                  // input
        .rst(~resetn),              // input
        .rd_data(rd_data)           // output [31:0]
    );
    reg [31:0] ex_mem_inst;
    reg [31:0] ex_mem_pc;
    reg ex_mem_valid;
    always@(posedge clk)begin
        if(!vaild)begin
            ex_mem_inst <= 32'h00000000;
            ex_mem_pc <= 32'h00000000;
            ex_mem_valid <= 1'b0;
        end
        else begin
            ex_mem_inst <= id_ex_inst;
            ex_mem_pc <= id_ex_pc;
            ex_mem_valid <= id_ex_valid;
        end
    end

    reg [31:0] mem_wb_inst;
    reg [31:0] mem_wb_pc;
    reg mem_wb_valid;
    reg [31:0] mem_wb_rd_data;
    always@(posedge clk)begin
        if(!vaild)begin
            mem_wb_inst <= 32'h00000000;
            mem_wb_pc <= 32'h00000000;
            mem_wb_valid <= 1'b0;
            mem_wb_rd_data <= 32'h00000000;
        end
        else begin  
            mem_wb_inst <= ex_mem_inst;
            mem_wb_pc <= ex_mem_pc;
            mem_wb_valid <= ex_mem_valid;
            mem_wb_rd_data <= rd_data;
        end
    end
    assign debug_pc = mem_wb_pc;
    assign debug_inst = mem_wb_inst;
    assign debug_rd_data = mem_wb_rd_data;
endmodule
