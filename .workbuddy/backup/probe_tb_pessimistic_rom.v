`timescale 1ns / 1ps
// 对照仿真用:悲观 ROM 模型(内部地址寄存器"不复位",对应 RST_VAL_EN=false)
module probe_tb;
    reg         clk;
    reg         resetn;

    wire [31:0] inst_sram_addr;
    wire [31:0] inst_sram_rdata;
    wire        data_sram_we;
    wire [31:0] data_sram_addr;
    wire [31:0] data_sram_wdata;
    wire [31:0] data_sram_rdata;
    wire [31:0] debug_wb_pc;
    wire [ 3:0] debug_wb_rf_we;
    wire [ 4:0] debug_wb_rf_wnum;
    wire [31:0] debug_wb_rf_wdata;

    initial begin clk = 1'b0; forever #5 clk = ~clk; end
    initial begin resetn = 1'b0; #60; resetn = 1'b1; #400; $finish; end

    reg  [31:0] rom_mem [0:1023];
    reg  [ 9:0] rom_addr_r;
    initial $readmemh("D:/riscv/tbtb/rom_test.dat", rom_mem);
    always @(posedge clk) rom_addr_r <= inst_sram_addr[11:2];
    assign inst_sram_rdata = rom_mem[rom_addr_r];

    topcpu u_topcpu(
        .clk(clk), .resetn(resetn),
        .inst_sram_addr(inst_sram_addr), .inst_sram_rdata(inst_sram_rdata),
        .data_sram_we(data_sram_we), .data_sram_addr(data_sram_addr),
        .data_sram_wdata(data_sram_wdata), .data_sram_rdata(data_sram_rdata),
        .debug_wb_pc(debug_wb_pc), .debug_wb_rf_we(debug_wb_rf_we),
        .debug_wb_rf_wnum(debug_wb_rf_wnum), .debug_wb_rf_wdata(debug_wb_rf_wdata)
    );

    reg [31:0] expect_pc;
    reg [31:0] err_cnt;
    reg [31:0] vld_cnt;
    reg        first_seen;

    always @(posedge clk) begin
        #1;
        if (!resetn) begin
            expect_pc  <= 32'h0;
            err_cnt    <= 32'h0;
            vld_cnt    <= 32'h0;
            first_seen <= 1'b0;
        end
        else if (u_topcpu.u_ifu.if_id_valid) begin
            vld_cnt <= vld_cnt + 1;
            if (!first_seen) begin
                first_seen <= 1'b1;
                $display("FIRST_VALID_AT=%0t  (pc=%08h inst=%08h ; mem[0]=%08h mem[1]=%08h)",
                         $time, u_topcpu.u_ifu.if_id_pc, u_topcpu.u_ifu.if_id_inst,
                         rom_mem[0], rom_mem[1]);
            end
            if (u_topcpu.u_ifu.if_id_pc !== expect_pc) begin
                err_cnt <= err_cnt + 1;
                if (err_cnt < 3)
                  $display("ERR_PC  @%0t: if_id_pc=%08h expect %08h", $time, u_topcpu.u_ifu.if_id_pc, expect_pc);
            end
            if (u_topcpu.u_ifu.if_id_inst !== rom_mem[expect_pc[11:2]]) begin
                err_cnt <= err_cnt + 1;
                if (err_cnt < 3)
                  $display("ERR_INST@%0t: if_id_pc=%08h if_id_inst=%08h expect mem[%0d]=%08h",
                           $time, u_topcpu.u_ifu.if_id_pc, u_topcpu.u_ifu.if_id_inst,
                           expect_pc[11:2], rom_mem[expect_pc[11:2]]);
            end
            expect_pc <= expect_pc + 32'h4;
        end
    end

    initial begin
        #460;
        $display("SUMMARY errors=%0d valid=%0d", err_cnt, vld_cnt);
        $finish;
    end
endmodule
