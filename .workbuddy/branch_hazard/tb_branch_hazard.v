`timescale 1ns/1ps
// 分支冒险验证:ID 级判定 + 冲刷 + 重定向。工程外的验证材料,不进工程。
module tb_branch_hazard;
    reg clk    = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    integer errors  = 0;
    integer nvalid  = 0;      // ID 级有效指令计数
    integer nBubble = 0;      // 气泡总数
    integer nFlush  = 0;      // 其中"分支冲刷"气泡(if_id_pc = FFFF_FFFF 哨兵)
    integer k;

    reg [31:0] exp_path [0:15];   // 期望真正进入 ID 的 PC 序列
    reg [31:0] got_path [0:15];   // 实测
    integer    exp_n;

    // 4 条"错路"填充指令:只要它们带着 valid=1 进过 ID,就是冲刷失效
    function is_wrongpath(input [31:0] v);
        is_wrongpath = (v === 32'h22200A13) || (v === 32'h33300A93) ||
                       (v === 32'h55500B13) || (v === 32'h77700B93);
    endfunction

    mycpu_single_async u_dut (.clk(clk), .resetn(resetn));

    initial begin
        exp_path[0] = 32'h00000000;   // addi x1,x0,5
        exp_path[1] = 32'h00000004;   // beq  x1,x1,12   (taken)
        exp_path[2] = 32'h00000010;   // jal  x5,8       (taken)
        exp_path[3] = 32'h00000018;   // jalr x7,x0,0x20 (taken)
        exp_path[4] = 32'h00000020;   // addi x9,x0,1
        exp_path[5] = 32'h00000024;   // bne  x1,x1,16   (NOT taken)
        exp_path[6] = 32'h00000028;   // addi x24,x0,0x999
        exp_path[7] = 32'h0000002c;   // beq  x1,x2,20   (NOT taken)
        exp_path[8] = 32'h00000030;   // addi x25,x0,0xaaa
        exp_n = 9;
    end

    // 每个时钟沿之后采样 ID 级(IF/ID 寄存器)的内容
    always @(posedge clk) if (resetn) begin
        #1;
        if (u_dut.valid) begin
            if (u_dut.if_id_valid) begin
                if (is_wrongpath(u_dut.if_id_inst)) begin
                    errors = errors + 1;
                    $display("  [FAIL] wrong-path inst entered ID: pc=%h inst=%h",
                             u_dut.if_id_pc, u_dut.if_id_inst);
                end
                if (nvalid < 16) got_path[nvalid] = u_dut.if_id_pc;
                nvalid = nvalid + 1;
            end
            else begin
                nBubble = nBubble + 1;
                if (u_dut.if_id_pc === 32'hFFFF_FFFF) nFlush = nFlush + 1;
                $display("  [bubble] cycle=%0d  pc(IF)=%h  if_id_pc=%h  %0s",
                         nvalid + nBubble, u_dut.pc, u_dut.if_id_pc,
                         (u_dut.if_id_pc === 32'hFFFF_FFFF) ? "<- flush" : "<- reset");
            end
        end
    end

    initial begin
        $display("=== branch hazard: ID-stage resolve + flush + redirect ===");
        repeat (4) @(posedge clk);
        resetn = 1'b1;
        repeat (16) @(posedge clk);
        #1;

        $display("-- ID 级实际执行路径 --");
        for (k = 0; k < exp_n; k = k + 1) begin
            if (got_path[k] !== exp_path[k]) begin
                errors = errors + 1;
                $display("  [FAIL] path[%0d] got=%h exp=%h", k, got_path[k], exp_path[k]);
            end else begin
                $display("  [ ok ] path[%0d] = %h", k, got_path[k]);
            end
        end
        $display("  共执行 %0d 条有效指令;气泡 %0d 个 = 分支冲刷 %0d + 复位 %0d",
                 nvalid, nBubble, nFlush, nBubble - nFlush);
        if (nFlush !== 3) begin
            errors = errors + 1;
            $display("  [FAIL] 分支冲刷气泡应为 3(beq/jal/jalr 各 1),实测 %0d", nFlush);
        end else $display("  [ ok ] 分支代价:3 条命中分支/jump 各付 1 个气泡");

        $display("-- 寄存器堆 --");
        if (u_dut.u_regfile.rf[1]  !== 32'h00000005) begin errors=errors+1; $display("  [FAIL] x1"); end
        else $display("  [ ok ] x1 =5      (addi 执行)");
        if (u_dut.u_regfile.rf[9]  !== 32'h00000001) begin errors=errors+1; $display("  [FAIL] x9"); end
        else $display("  [ ok ] x9 =1      (addi 执行)");
        if (u_dut.u_regfile.rf[5]  !== 32'h00000014) begin errors=errors+1; $display("  [FAIL] x5"); end
        else $display("  [ ok ] x5 =14     (jal  链接值 = if_id_pc+4 = 0x10+4)");
        if (u_dut.u_regfile.rf[7]  !== 32'h0000001c) begin errors=errors+1; $display("  [FAIL] x7"); end
        else $display("  [ ok ] x7 =1c     (jalr 链接值 = if_id_pc+4 = 0x18+4)");
        if (u_dut.u_regfile.rf[24] !== 32'hfffff999) begin errors=errors+1; $display("  [FAIL] x24"); end
        else $display("  [ ok ] x24=fffff999 (bne 未命中,顺延执行)");
        if (u_dut.u_regfile.rf[25] !== 32'hfffffaaa) begin errors=errors+1; $display("  [FAIL] x25"); end
        else $display("  [ ok ] x25=fffffaaa (beq 未命中,顺延执行)");
        if (u_dut.u_regfile.rf[20] !== 32'h0 ||
            u_dut.u_regfile.rf[21] !== 32'h0 ||
            u_dut.u_regfile.rf[22] !== 32'h0 ||
            u_dut.u_regfile.rf[23] !== 32'h0) begin
            errors=errors+1;
            $display("  [FAIL] 错路哨兵被执行了: x20=%h x21=%h x22=%h x23=%h",
                     u_dut.u_regfile.rf[20], u_dut.u_regfile.rf[21],
                     u_dut.u_regfile.rf[22], u_dut.u_regfile.rf[23]);
        end else $display("  [ ok ] x20~x23 全 0 (错路指令一条都没落地)");

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
        // ---- 真正要执行的路径 ----
        mem[0]  = 32'h00500093;  // 0x00 addi x1,x0,5
        mem[1]  = 32'h00108663;  // 0x04 beq  x1,x1,12   -> 0x10
        mem[4]  = 32'h008002EF;  // 0x10 jal  x5,8       -> 0x18, link 0x14
        mem[6]  = 32'h020003E7;  // 0x18 jalr x7,x0,0x20 -> 0x20, link 0x1c
        mem[8]  = 32'h00100493;  // 0x20 addi x9,x0,1
        mem[9]  = 32'h00109863;  // 0x24 bne  x1,x1,16   -> NOT taken
        mem[10] = 32'h99900C13;  // 0x28 addi x24,x0,0x999
        mem[11] = 32'h00208A63;  // 0x2c beq  x1,x2,20   -> NOT taken
        mem[12] = 32'hAAA00C93;  // 0x30 addi x25,x0,0xaaa
        // ---- 错路哨兵:被冲掉的地址上放它们,一旦执行就能发现 ----
        mem[2]  = 32'h22200A13;  // 0x08 (beq 后面那条) addi x20,x0,0x222
        mem[3]  = 32'h33300A93;  // 0x0c addi x21,x0,0x333
        mem[5]  = 32'h55500B13;  // 0x14 (jal 后面那条) addi x22,x0,0x555
        mem[7]  = 32'h77700B93;  // 0x1c (jalr 后面那条) addi x23,x0,0x777
    end
    always @(posedge clk) begin
        if (rst) rd_data <= mem[10'h0];
        else     rd_data <= mem[addr];
    end
endmodule
