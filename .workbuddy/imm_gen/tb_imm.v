`timescale 1ns/1ps
// 验证"立即数统一生成"是否与原来的优先级链等价:
//   覆盖 U型(lui/auipc) / I型(addi 负数) / shamt(slli/srli) / S型(sw) / load-I(lw)
module tb_imm;
    reg clk    = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    integer errors = 0;
    integer k;

    localparam [31:0] SW_INST = 32'h00E02423;   // sw   x14, 8(x0)
    localparam [31:0] LW_INST = 32'h00402803;   // lw   x16, 4(x0)

    reg [31:0] sw_addr = 32'hDEAD_BEEF;
    reg [31:0] lw_addr = 32'hDEAD_BEEF;
    integer    nvalid  = 0;
    reg [31:0] exp_path [0:15];

    mycpu_single_async u_dut (.clk(clk), .resetn(resetn));

    initial begin
        // 本程序无分支 → pc 纯顺序递增,ID 级路径就是 0,4,8,...
        for (k = 0; k < 16; k = k + 1) exp_path[k] = k * 4;
    end

    task chk(input [31:0] got, input [31:0] exp, input [255:0] tag);
        begin
            if (got !== exp) begin
                errors = errors + 1;
                $display("  [FAIL] %0s got=%h exp=%h", tag, got, exp);
            end else $display("  [ ok ] %0s = %h", tag, got);
        end
    endtask

    // 逐拍观察 ID 级;顺带抓 sw / lw 在 ID 级时的访存地址
    always @(posedge clk) if (resetn) begin
        #1;
        if (u_dut.valid && u_dut.if_id_valid) begin
            if (nvalid < 16 && u_dut.if_id_pc !== exp_path[nvalid]) begin
                errors = errors + 1;
                $display("  [FAIL] path[%0d] got=%h exp=%h", nvalid, u_dut.if_id_pc, exp_path[nvalid]);
            end
            if (u_dut.if_id_inst === SW_INST) sw_addr = u_dut.data_sram_addr;
            if (u_dut.if_id_inst === LW_INST) lw_addr = u_dut.data_sram_addr;
            nvalid = nvalid + 1;
        end
    end

    initial begin
        $display("=== immediate generation (unified imm) ===");
        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (14) @(posedge clk);
        #1;

        $display("-- U 型:src1=pc,src2=imm_u --");
        chk(u_dut.u_regfile.rf[10], 32'h12345000, "x10 lui   imm_u 上位");
        chk(u_dut.u_regfile.rf[11], 32'h00001004, "x11 auipc 0x04+0x1000");
        $display("-- I 型:符号扩展 --");
        chk(u_dut.u_regfile.rf[12], 32'hFFFFFFFF, "x12 addi x0,-1 符号扩展");
        chk(u_dut.u_regfile.rf[13], 32'h00000000, "x13 addi x12,1");
        $display("-- shamt --");
        chk(u_dut.u_regfile.rf[14], 32'hFFFFFFF0, "x14 slli 4");
        chk(u_dut.u_regfile.rf[15], 32'h0000000F, "x15 srli 28");
        $display("-- S 型 / load-I 型:走 alu_src2=imm --");
        chk(sw_addr, 32'h00000008, "sw 访存地址 = 0+8");
        chk(lw_addr, 32'h00000004, "lw 访存地址 = 0+4");

        if (errors == 0) $display("=== PASS ===");
        else             $display("=== FAIL: %0d mismatch ===", errors);
        $finish;
    end
endmodule

// ROM 空壳:同步读,1 拍延迟
module inst_rom(input wire [9:0] addr, input wire clk, input wire rst, output reg [31:0] rd_data);
    reg [31:0] mem [0:1023];
    integer i;
    initial begin
        for (i = 0; i < 1024; i = i + 1) mem[i] = 32'h00000013; // nop
        mem[0] = 32'h12345537;  // 0x00 lui   x10, 0x12345
        mem[1] = 32'h00001597;  // 0x04 auipc x11, 0x1     -> 0x04+0x1000
        mem[2] = 32'hFFF00613;  // 0x08 addi  x12, x0, -1
        mem[3] = 32'h00160693;  // 0x0c addi  x13, x12, 1
        mem[4] = 32'h00461713;  // 0x10 slli  x14, x12, 4
        mem[5] = 32'h01C65793;  // 0x14 srli  x15, x12, 28
        mem[6] = 32'h00E02423;  // 0x18 sw    x14, 8(x0)
        mem[7] = 32'h00402803;  // 0x1c lw    x16, 4(x0)
    end
    always @(posedge clk) begin
        if (rst) rd_data <= mem[10'h0];
        else     rd_data <= mem[addr];
    end
endmodule
