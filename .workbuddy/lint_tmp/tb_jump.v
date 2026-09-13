`timescale 1ns/1ps
// 仅用于验证 mycpu_sync.v 的 next_pc / 跳转逻辑;不进入工程
module tb_jump;
    reg clk    = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    integer errors = 0;
    integer k;

    reg [31:0] exp_pc [0:9];

    mycpu_single_async u_dut (.clk(clk), .resetn(resetn));

    initial begin
        exp_pc[0] = 32'h00000000; // addi x1,x0,5
        exp_pc[1] = 32'h00000004; // beq  x1,x1,12   -> TAKEN   => 0x10
        exp_pc[2] = 32'h00000010; // jal  x5,8       -> TAKEN   => 0x18
        exp_pc[3] = 32'h00000018; // jalr x7,x0,0x20 -> TAKEN   => 0x20
        exp_pc[4] = 32'h00000020; // addi x9,x0,1
        exp_pc[5] = 32'h00000024; // bne  x1,x1,16   -> NOT taken => +4
        exp_pc[6] = 32'h00000028; // addi x24,x0,0x999
        exp_pc[7] = 32'h0000002c; // beq  x1,x2,20   -> NOT taken => +4
        exp_pc[8] = 32'h00000030; // addi x25,x0,0xaaa
        exp_pc[9] = 32'h00000034; // nop
    end

    task chk(input [31:0] got, input [31:0] exp, input [255:0] tag);
        begin
            if (got !== exp) begin
                errors = errors + 1;
                $display("  [FAIL] %0s got=%h exp=%h", tag, got, exp);
            end else begin
                $display("  [ ok ] %0s = %h", tag, got);
            end
        end
    endtask

    initial begin
        $display("=== jump / next_pc functional check ===");
        repeat (4) @(posedge clk);
        resetn = 1'b1;

        for (k = 0; k < 10; k = k + 1) begin
            @(posedge clk); #1;
            chk(u_dut.pc, exp_pc[k], "pc");
        end

        $display("-- taken 路径 --");
        chk(u_dut.u_regfile.rf[1],  32'h00000005, "x1  addi ran");
        chk(u_dut.u_regfile.rf[5],  32'h00000014, "x5  jal  link = pc4");
        chk(u_dut.u_regfile.rf[7],  32'h0000001c, "x7  jalr link = pc4");
        chk(u_dut.u_regfile.rf[9],  32'h00000001, "x9  addi ran");
        $display("-- 被跳过的 filler 必须保持 0 --");
        chk(u_dut.u_regfile.rf[20], 32'h00000000, "x20 0x08 skipped");
        chk(u_dut.u_regfile.rf[21], 32'h00000000, "x21 0x0c skipped");
        chk(u_dut.u_regfile.rf[22], 32'h00000000, "x22 0x14 skipped");
        chk(u_dut.u_regfile.rf[23], 32'h00000000, "x23 0x1c skipped");
        $display("-- not-taken 路径 --");
        // 注:imm_i 是符号扩展,0x999/0xaaa 最高位为 1 -> 实际为负
        chk(u_dut.u_regfile.rf[24], 32'hfffff999, "x24 bne NOT taken, fell through");
        chk(u_dut.u_regfile.rf[25], 32'hfffffaaa, "x25 beq NOT taken, fell through");

        if (errors == 0) $display("=== PASS ===");
        else             $display("=== FAIL: %0d mismatch ===", errors);
        $finish;
    end
endmodule

// ROM 空壳:同步读,1 拍延迟(对应 OUTPUT_REG=0 的真实 IP)
module inst_rom(input wire [9:0] addr, input wire clk, input wire rst, output reg [31:0] rd_data);
    reg [31:0] mem [0:1023];
    integer i;
    initial begin
        for (i = 0; i < 1024; i = i + 1) mem[i] = 32'h00000013; // nop
        // --- 真正执行的指令 ---
        mem[0]  = 32'h00500093;  // 0x00 addi x1,x0,5
        mem[1]  = 32'h108663;    // 0x04 beq  x1,x1,12   -> 0x10
        mem[4]  = 32'h8002EF;    // 0x10 jal  x5,8       -> 0x18, link 0x14
        mem[6]  = 32'h020003E7;  // 0x18 jalr x7,x0,0x20 -> 0x20, link 0x1c
        mem[8]  = 32'h00100493;  // 0x20 addi x9,x0,1
        mem[9]  = 32'h109863;    // 0x24 bne  x1,x1,16   -> NOT taken
        mem[10] = 32'h99900C13;  // 0x28 addi x24,x0,0x999
        mem[11] = 32'h208A63;    // 0x2c beq  x1,x2,20   -> NOT taken
        mem[12] = 32'hAAA00C93;  // 0x30 addi x25,x0,0xaaa
        // --- 哨兵:一旦被执行就会写入非零,便于定位错误 ---
        mem[2]  = 32'h22200A13;  // 0x08 addi x20,x0,0x222 (must skip)
        mem[3]  = 32'h33300A93;  // 0x0c addi x21,x0,0x333 (must skip)
        mem[5]  = 32'h55500B13;  // 0x14 addi x22,x0,0x555 (must skip)
        mem[7]  = 32'h77700B93;  // 0x1c addi x23,x0,0x777 (must skip)
    end
    always @(posedge clk) begin
        if (rst) rd_data <= mem[10'h0];
        else     rd_data <= mem[addr];
    end
endmodule
