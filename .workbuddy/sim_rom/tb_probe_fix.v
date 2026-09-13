`timescale 1ns / 1ps
// 修复版对照仿真:同一个激励,同一个 ROM(官方 RTL 模型)
module tb_probe_fix();
    reg clk, resetn;
    wire [31:0] debug_pc, debug_inst;

    topcpu_fix u_topcpu_fix(
        .clk(clk), .resetn(resetn),
        .debug_pc(debug_pc), .debug_inst(debug_inst)
    );

    GTP_GRS GRS_INST(.GRS_N(1'b1));

    initial begin clk = 1'b1; forever #5 clk = ~clk; end
    initial begin resetn = 1'b0; #95; resetn = 1'b1; end

    integer i;
    initial begin
        $display("  time | pc      | rom_inst  | if_id_pc | if_id_inst");
        $display("-------+---------+-----------+----------+-----------");
        for (i = 0; i < 22; i = i + 1) begin
            @(posedge clk); #1;
            $display("%6.0f | %h | %h | %h | %h",
                     $time, u_topcpu_fix.pc, u_topcpu_fix.inst,
                     u_topcpu_fix.if_id_pc, u_topcpu_fix.if_id_inst);
        end
        $display("---- done ----");
        $finish;
    end
endmodule
