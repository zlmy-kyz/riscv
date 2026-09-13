`timescale 1ns / 1ps
// 方案一-B 在真 IP 下的对照仿真
module tb_probe_plan1b();
    reg clk, resetn;
    wire [31:0] debug_pc, debug_inst;

    topcpu_plan1b u_dut(
        .clk(clk), .resetn(resetn),
        .debug_pc(debug_pc), .debug_inst(debug_inst)
    );

    GTP_GRS GRS_INST(.GRS_N(1'b1));

    initial begin clk = 1'b1; forever #5 clk = ~clk; end
    initial begin resetn = 1'b0; #95; resetn = 1'b1; end

    integer i;
    initial begin
        $display("  time | pc_r    | if_id_pc | valid | debug_inst");
        $display("-------+---------+----------+-------+-----------");
        for (i = 0; i < 20; i = i + 1) begin
            @(posedge clk); #1;
            $display("%6.0f | %h | %h |   %b   | %h",
                     $time, u_dut.pc_r, u_dut.if_id_pc, u_dut.if_id_valid, u_dut.debug_inst);
        end
        $display("---- done ----");
        $finish;
    end
endmodule
