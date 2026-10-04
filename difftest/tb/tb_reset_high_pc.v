`timescale 1ns/1ps

// 核对 riscv-tests 的 0x8000_0000 入口与低 12 位 ROM 索引的配对。
module tb_reset_high_pc;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync #(.RESET_PC(32'h8000_0000)) dut (
        .clk(clk), .resetn(resetn),
        .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0)
    );

    initial begin
        // 行为 ROM 的 $readmemh 在时间 0 完成后覆盖三个测试位置。
        #1;
        dut.u_inst_rom.mem[0] = 32'h0540_006f;  // jal x0, 0x80000054
        dut.u_inst_rom.mem[21] = 32'h0010_0193; // addi x3,x0,1
        dut.u_inst_rom.mem[22] = 32'h0000_006f; // 自循环
        repeat (8) @(posedge clk);
        #1;
        if (dut.pc !== 32'h8000_0000 ||
            dut.arch_next_pc !== 32'h8000_0000)
            $fatal(1, "high reset PC lost");
        @(negedge clk) resetn = 1;
        wait (dut.u_regfile.rf[3] == 32'd1);
        repeat (4) @(posedge clk);
        #1;
        if (dut.arch_next_pc !== 32'h8000_0058 ||
            dut.pc[31:12] !== 20'h80000)
            $fatal(1, "high PC jump/retire mismatch pc=%h arch=%h",
                   dut.pc, dut.arch_next_pc);
        $display("RESULT: PASS high reset PC and ROM alias mapping");
        $finish;
    end

    initial begin
        #3000;
        $fatal(1, "high reset PC test timeout");
    end
endmodule
