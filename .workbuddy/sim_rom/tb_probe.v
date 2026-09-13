`timescale 1ns / 1ps
//==========================================================================
// tb_probe : 复现 source/tb_topcpu.v 的激励,加上逐拍打印
//   - 用 Pango 官方 RTL 行为模型(GTP_DRM36K_E1 / GTP_GRS),不是简化模型
//==========================================================================
module tb_probe();

    reg clk;
    reg resetn;

    wire [31:0] debug_pc;
    wire [31:0] debug_inst;

    topcpu u_topcpu(
        .clk(clk),
        .resetn(resetn),
        .debug_pc(debug_pc),
        .debug_inst(debug_inst)
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
        #95;
        resetn = 1'b1;
    end

    //---- 被观察的内部信号 ----
    wire [31:0] w_pc          = u_topcpu.pc;
    wire [31:0] w_next_pc     = u_topcpu.next_pc;
    wire [31:0] w_inst_addr   = u_topcpu.inst_sram_addr;
    wire [31:0] w_inst        = u_topcpu.inst;
    wire [31:0] w_ifid_pc     = u_topcpu.if_id_pc;
    wire [31:0] w_ifid_inst   = u_topcpu.if_id_inst;

    // ROM 内部:drm_addr(送给 DRM 的地址) 与 ada_reg(DRM 内部地址寄存器)
    wire [15:0] w_drm_addr = u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.drm_addr;
    wire [15:0] w_ada_reg  = u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.ada_reg;

    integer i;
    initial begin
        #1;
        $display("DBG DRM.INIT_FILE = %s", u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.INIT_FILE);
        $display("DBG DRM.INIT_00   = %h", u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.INIT_00);
        $display("DBG spram INIT_00 = %h", u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.INIT_00);
        $display("DBG mem[3..0]     = %h %h %h %h",
            u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[3],
            u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[2],
            u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[1],
            u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[0]);
        $display("DBG word0         = %h",
            {u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[3][7:0],
             u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[2][7:0],
             u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[1][7:0],
             u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.mem[0][7:0]});
        $display("DBG spram c_INIT_FILE = %s", u_topcpu.u_inst_rom.U_ipm2l_rom_inst_rom.U_ipm2l_spram.c_INIT_FILE);
    end

    initial begin
        $dumpfile("rom_probe.vcd");
        $dumpvars(0, tb_probe);
        $display("  time | resetn |   pc    | next_pc | rom_addr(word) | ada_reg |  rom_inst  | if_id_pc | if_id_inst");
        $display("-------+--------+---------+---------+----------------+---------+------------+----------+-----------");
        for (i = 0; i < 26; i = i + 1) begin
            @(posedge clk);
            #1;   // 让非阻塞赋值全部完成后再看
            $display("%6.0f |   %b    | %h | %h  |      %2d        |   %2d    | %h | %h | %h",
                     $time, resetn, w_pc, w_next_pc,
                     w_inst_addr[11:2], w_ada_reg[14:5],
                     w_inst, w_ifid_pc, w_ifid_inst);
        end
        $display("---- done ----");
        $finish;
    end

endmodule
