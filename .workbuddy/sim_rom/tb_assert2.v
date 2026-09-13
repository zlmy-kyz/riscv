`timescale 1ns / 1ps
// 对照:同一个激励,同时跑"当前版"和"改一处版",并用断言检查假有效气泡
module tb_assert2();
    reg clk, resetn;

    wire [31:0] pc_a, inst_a, pc_b, inst_b;

    topcpu_instrom u_cur(
        .clk(clk), .resetn(resetn),
        .debug_pc(pc_a), .debug_inst(inst_a)
    );

    topcpu_instrom_fix u_fix(
        .clk(clk), .resetn(resetn),
        .debug_pc(pc_b), .debug_inst(inst_b)
    );

    GTP_GRS GRS_INST(.GRS_N(1'b1));

    initial begin clk = 1'b1; forever #5 clk = ~clk; end
    initial begin resetn = 1'b0; #95; resetn = 1'b1; end

    integer err_cur, err_fix;
    initial begin err_cur = 0; err_fix = 0; end

    always @(posedge clk) begin
        #1;
        if (u_cur.if_id_valid && (u_cur.if_id_inst == 32'h0000_0000)) begin
            err_cur = err_cur + 1;
            $display("  [当前版] ASSERT-FAIL @%0t: valid=1 但指令全零(非法) pc=%h <- 假有效气泡",
                     $time, u_cur.if_id_pc);
        end
        if (u_fix.if_id_valid && (u_fix.if_id_inst == 32'h0000_0000)) begin
            err_fix = err_fix + 1;
            $display("  [改一处] ASSERT-FAIL @%0t: valid=1 但指令全零(非法) pc=%h",
                     $time, u_fix.if_id_pc);
        end
    end

    integer i;
    initial begin
        $display("  time | 当前版: v pc        inst     | 改一处: v pc        inst");
        $display("-------+-------------------------------+------------------------------");
        for (i = 0; i < 12; i = i + 1) begin
            @(posedge clk); #1;
            $display("%6.0f | %b %h %h | %b %h %h",
                     $time,
                     u_cur.if_id_valid, pc_a, inst_a,
                     u_fix.if_id_valid, pc_b, inst_b);
        end
        $display("---- 断言报错次数:当前版=%0d  改一处=%0d ----", err_cur, err_fix);
        $finish;
    end
endmodule
