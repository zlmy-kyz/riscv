`timescale 1ns/1ps
// ===========================================================================
// 五级流水验证:tb_pipe5.v
//   用 `define TEST_x 选择程序,一次只跑一组,便于把失败点隔离出来。
//   所有寄存器堆 / 内存检查都放在 tb 里(通过层次化引用直接读 rf)。
// ===========================================================================

`ifndef TEST_A
`ifndef TEST_B
`ifndef TEST_C
`ifndef TEST_D
`ifndef TEST_E
`ifndef TEST_F
`ifndef TEST_G
`ifndef TEST_H
  `define TEST_A       // 默认跑 A
`endif
`endif
`endif
`endif
`endif
`endif
`endif
`endif

module tb_pipe5;
    reg clk    = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    integer errors = 0;
    integer k;

`ifdef SIM_ASSERT
    // 断言版实例化
`endif
    mycpu_sync u_dut (.clk(clk), .resetn(resetn));

    // ---------- trace:每个沿打印一条"提交"记录(可选,只在前若干拍)----------
    integer trace_on = 1;
    integer ncommit  = 0;
    always @(posedge clk) if (resetn && trace_on) begin
        #1;
        if (u_dut.mem_wb_valid)
            $display("  [wb] t=%0t pc=%h we=%b rd=x%0d data=%h%s",
                     $time, u_dut.mem_wb_pc, u_dut.mem_wb_rf_we, u_dut.mem_wb_rd,
                     u_dut.rf_wdata,
                     (u_dut.mem_wb_pc === 32'hFFFF_FFFF) ? "  <-- 哨兵!valid 逻辑错" : "");
        ncommit = ncommit + 1;
        if (ncommit > 40) trace_on = 0;
    end

    task chk(input [31:0] got, input [31:0] exp, input [255:0] tag);
        begin
            if (got !== exp) begin
                errors = errors + 1;
                $display("  [FAIL] %0s got=%h exp=%h", tag, got, exp);
            end else $display("  [ ok ] %0s = %h", tag, got);
        end
    endtask

    initial begin
`ifdef TEST_A
        $display("=== TEST A: 基本正确性(无冒险顺序路径)===");
`endif
`ifdef TEST_B
        $display("=== TEST B: 判决位 rd==0 / 同时写不同 rd ===");
`endif
`ifdef TEST_C
        $display("=== TEST C: ALU 转发 EX/MEM->EX + 连续 RAW 链 ===");
`endif
`ifdef TEST_D
        $display("=== TEST D: load-use 冒险 ===");
`endif
`ifdef TEST_E
        $display("=== TEST E: 分支 + 转发 ===");
`endif
`ifdef TEST_F
        $display("=== TEST F: 分支 + load-use ===");
`endif
`ifdef TEST_G
        $display("=== TEST G: jal / jalr 跳转 + 链接值 ===");
`endif
`ifdef TEST_H
        $display("=== TEST H: 分支不命中 + 访存 ===");
`endif

        repeat (4) @(posedge clk);      // 复位保持
        resetn = 1'b1;
        repeat (40) @(posedge clk);     // 跑完程序 + 排空流水
        #1;

`ifdef TEST_A
        chk(u_dut.u_regfile.rf[10], 32'h12345000, "x10 lui");
        chk(u_dut.u_regfile.rf[11], 32'h00001004, "x11 auipc 0x04+0x1000");
        chk(u_dut.u_regfile.rf[12], 32'hFFFFFFFF, "x12 addi x0,-1");
        chk(u_dut.u_regfile.rf[14], 32'hFFFFFFF0, "x14 slli x12,4");
        chk(u_dut.u_regfile.rf[15], 32'h0000000F, "x15 srli x12,28");
        $display("-- sw x14,8(x0) 的访存地址应为 8 --");
        chk(u_dut.u_regfile.rf[13], 32'h0, "x13 未写(程序里没有)");
`endif

`ifdef TEST_B
        chk(u_dut.u_regfile.rf[0],  32'h00000000, "★ x0 恒 0(有指令想写它)");
        chk(u_dut.u_regfile.rf[1],  32'h000007FF, "x1 addi 0x7FF");
        chk(u_dut.u_regfile.rf[2],  32'h00005000, "x2 lui 0x5");
        chk(u_dut.u_regfile.rf[3],  32'h00005000, "x3 lui 0x5(与 x2 同时写)");
        chk(u_dut.u_regfile.rf[4],  32'h00000055, "x4 addi 0x55");
`endif

`ifdef TEST_C
        chk(u_dut.u_regfile.rf[1], 32'h00000011, "x1 addi 0x11");
        chk(u_dut.u_regfile.rf[2], 32'h00000012, "x2 = x1+1        (EX/MEM 转发)");
        chk(u_dut.u_regfile.rf[3], 32'h00000013, "x3 = x2+1        (EX/MEM 转发)");
        chk(u_dut.u_regfile.rf[4], 32'h00000014, "x4 = x3+1        (EX/MEM 转发)");
        chk(u_dut.u_regfile.rf[5], 32'h00000015, "x5 = x4+1        (EX/MEM 转发)");
        chk(u_dut.u_regfile.rf[6], 32'h00000054, "x6 = x5<<2       (EX/MEM 转发)");
        chk(u_dut.u_regfile.rf[7], 32'h0000002A, "x7 = x6>>1       (EX/MEM 转发)");
`endif

`ifdef TEST_D
        chk(u_dut.u_regfile.rf[1], 32'h0000001F, "x1 addi 0x1F");
        chk(u_dut.u_regfile.rf[2], 32'h0000001F, "★ x2 lw   -> 0x1F(load-use)");
        chk(u_dut.u_regfile.rf[3], 32'h0000002F, "★ x3 = x2+0x10  -> 0x2F(load-use 转发)");
        chk(u_dut.u_regfile.rf[4], 32'h0000001F, "x4 lw");
        chk(u_dut.u_regfile.rf[5], 32'h0000001F, "x5 lw");
        chk(u_dut.u_regfile.rf[6], 32'h00000021, "★ x6 = x5+2 -> 0x21(load-use 转发)");
`endif

`ifdef TEST_E
        chk(u_dut.u_regfile.rf[1],  32'h0000000A, "x1 = 10");
        chk(u_dut.u_regfile.rf[2],  32'h0000000A, "x2 = 10");
        chk(u_dut.u_regfile.rf[20], 32'h00000000, "★ x20 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[21], 32'h00000000, "★ x21 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[3],  32'h0000000B, "x3 = x1+1 -> 0xB(分支延迟槽,MEM/WB 转发)");
        chk(u_dut.u_regfile.rf[4],  32'h00099000, "x4 lui 0x99");
`endif

`ifdef TEST_F
        chk(u_dut.u_regfile.rf[1],  32'h00000033, "x1 = 0x33");
        chk(u_dut.u_regfile.rf[2],  32'h00000033, "x2 = lw -> 0x33");
        chk(u_dut.u_regfile.rf[20], 32'h00000000, "★ x20 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[21], 32'h00000000, "★ x21 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[3],  32'h00000034, "x3 = x2+1 -> 0x34");
`endif

`ifdef TEST_G
        chk(u_dut.u_regfile.rf[1],  32'h00000005, "x1 = 5");
        chk(u_dut.u_regfile.rf[2],  32'h00000008, "★ x2 = jal 链接值 0x08(pc 0x04+4)");
        chk(u_dut.u_regfile.rf[20], 32'h00000000, "★ x20 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[21], 32'h00000000, "★ x21 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[3],  32'h00000007, "x3 = 7(jal 目标 0x10 处)");
        chk(u_dut.u_regfile.rf[4],  32'h00000018, "★ x4 = jalr 链接值 0x18(pc 0x14+4)");
        chk(u_dut.u_regfile.rf[22], 32'h00000000, "★ x22 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[23], 32'h00000000, "★ x23 错路哨兵未被写");
        chk(u_dut.u_regfile.rf[5],  32'h00000000, "★ x5 = 0(0x20 被 jalr 跳过,不应执行)");
        chk(u_dut.u_regfile.rf[6],  32'h0000000B, "x6 = 0xB(jalr 目标 0x24 处执行)");
`endif

`ifdef TEST_H
        chk(u_dut.u_regfile.rf[1],  32'h0000000A, "x1 = 0x0A");
        chk(u_dut.u_regfile.rf[2],  32'h00000014, "x2 = 0x14");
        chk(u_dut.u_regfile.rf[3],  32'h00000033, "x3 = 0x33(beq 未命中,顺延执行)");
        chk(u_dut.u_regfile.rf[20], 32'h00000000, "★ x20 错路哨兵未被写(beq 未命中)");
        chk(u_dut.u_regfile.rf[4],  32'h00000033, "★ x4 = lw 读到 x3 存进去的 0x33");
`endif

        if (errors == 0) $display("=== PASS ===");
        else             $display("=== FAIL: %0d mismatch ===", errors);
        $finish;
    end
endmodule

// ===========================================================================
// ROM 模型:同步读,1 拍延迟(对应 OUTPUT_REG=0 的真实 IP)
//   悲观模型:内部地址寄存器**不带复位**(对应 RST_VAL_EN=false)
// ===========================================================================
module inst_rom(input wire [9:0] addr, input wire clk, input wire rst,
                output reg [31:0] rd_data);
    reg [31:0] mem [0:1023];
    reg [9:0]  addr_r;
    integer i;
    initial begin
        for (i = 0; i < 1024; i = i + 1) mem[i] = 32'h00000013; // NOP
`ifdef TEST_A
        mem[ 0] = 32'h12345537;  // 0x00  lui   x10, 0x12345
        mem[ 1] = 32'h00001597;  // 0x04  auipc x11, 0x1
        mem[ 2] = 32'hFFF00613;  // 0x08  addi  x12, x0, -1
        mem[ 3] = 32'h00461713;  // 0x0C  slli  x14, x12, 4
        mem[ 4] = 32'h01C65793;  // 0x10  srli  x15, x12, 28
        mem[ 5] = 32'h00E02423;  // 0x14  sw    x14, 8(x0)
`endif
`ifdef TEST_B
        mem[ 0] = 32'h7FF00093;  // 0x00  addi  x1, x0, 0x7FF
        mem[ 1] = 32'h12300013;  // 0x04  addi  x0, x0, 0x123
        mem[ 2] = 32'h00005137;  // 0x08  lui   x2, 0x5
        mem[ 3] = 32'h000051B7;  // 0x0C  lui   x3, 0x5
        mem[ 4] = 32'h05500213;  // 0x10  addi  x4, x0, 0x55
`endif
`ifdef TEST_C
        mem[ 0] = 32'h01100093;  // 0x00  addi  x1, x0, 0x11
        mem[ 1] = 32'h00108113;  // 0x04  addi  x2, x1, 0x01
        mem[ 2] = 32'h00110193;  // 0x08  addi  x3, x2, 0x01
        mem[ 3] = 32'h00118213;  // 0x0C  addi  x4, x3, 0x01
        mem[ 4] = 32'h00120293;  // 0x10  addi  x5, x4, 0x01
        mem[ 5] = 32'h00229313;  // 0x14  slli  x6, x5, 2
        mem[ 6] = 32'h00135393;  // 0x18  srli  x7, x6, 1
`endif
`ifdef TEST_D
        mem[ 0] = 32'h01F00093;  // 0x00  addi  x1, x0, 0x1F
        mem[ 1] = 32'h00102223;  // 0x04  sw    x1, 4(x0)
        mem[ 2] = 32'h00402103;  // 0x08  lw    x2, 4(x0)
        mem[ 3] = 32'h01010193;  // 0x0C  addi  x3, x2, 0x10
        mem[ 4] = 32'h00402203;  // 0x10  lw    x4, 4(x0)
        mem[ 5] = 32'h00402283;  // 0x14  lw    x5, 4(x0)
        mem[ 6] = 32'h00228313;  // 0x18  addi  x6, x5, 0x02
`endif
`ifdef TEST_E
        mem[ 0] = 32'h00A00093;  // 0x00  addi  x1, x0, 0x0A
        mem[ 1] = 32'h00A00113;  // 0x04  addi  x2, x0, 0x0A
        mem[ 2] = 32'h00208663;  // 0x08  beq   x1, x2, +12  -> 0x14
        mem[ 3] = 32'h77700A13;  // 0x0C  错路:addi x20,x0,0x777
        mem[ 4] = 32'h88800A93;  // 0x10  错路:addi x21,x0,0x888
        mem[ 5] = 32'h00108193;  // 0x14  addi  x3, x1, 0x01
        mem[ 6] = 32'h00099237;  // 0x18  lui   x4, 0x99
`endif
`ifdef TEST_F
        mem[ 0] = 32'h03300093;  // 0x00  addi  x1, x0, 0x33
        mem[ 1] = 32'h00102223;  // 0x04  sw    x1, 4(x0)
        mem[ 2] = 32'h00402103;  // 0x08  lw    x2, 4(x0)
        mem[ 3] = 32'h00110663;  // 0x0C  beq   x2, x1, +12  -> 0x18
        mem[ 4] = 32'h11100A13;  // 0x10  错路:addi x20,x0,0x111
        mem[ 5] = 32'h22200A93;  // 0x14  错路:addi x21,x0,0x222
        mem[ 6] = 32'h00110193;  // 0x18  addi  x3, x2, 0x01
`endif
`ifdef TEST_G
        mem[ 0] = 32'h00500093;  // 0x00  addi  x1, x0, 0x05
        mem[ 1] = 32'h00C0016F;  // 0x04  jal   x2, +12   -> 0x10, link 0x08
        mem[ 2] = 32'h11100A13;  // 0x08  错路哨兵 x20
        mem[ 3] = 32'h22200A93;  // 0x0C  错路哨兵 x21
        mem[ 4] = 32'h00700193;  // 0x10  addi  x3, x0, 0x07
        mem[ 5] = 32'h02008267;  // 0x14  jalr  x4, x1, 0x20 -> 5+0x20=0x25 -> 0x24
        mem[ 6] = 32'h33300B13;  // 0x18  错路哨兵 x22
        mem[ 7] = 32'h44400B93;  // 0x1C  错路哨兵 x23
        mem[ 8] = 32'h00900293;  // 0x20  addi  x5, x0, 0x09
        mem[ 9] = 32'h00B00313;  // 0x24  addi  x6, x0, 0x0B
`endif
`ifdef TEST_H
        mem[ 0] = 32'h00A00093;  // 0x00  addi  x1, x0, 0x0A
        mem[ 1] = 32'h01400113;  // 0x04  addi  x2, x0, 0x14
        mem[ 2] = 32'h00208663;  // 0x08  beq   x1, x2, +12  -> NOT taken
        mem[ 3] = 32'h03300193;  // 0x0C  addi  x3, x0, 0x33   ★ 应执行
        mem[ 4] = 32'h00209463;  // 0x10  bne   x1, x2, +8    -> taken to 0x18
        mem[ 5] = 32'h55500A13;  // 0x14  错路哨兵 x20
        mem[ 6] = 32'h00302423;  // 0x18  sw    x3, 8(x0)
        mem[ 7] = 32'h00802203;  // 0x1C  lw    x4, 8(x0)
`endif
        addr_r = 10'd1;      // ★ 悲观:内部地址寄存器初值非 0(对应 RST_VAL_EN=false)
    end
    // ★ 悲观:地址寄存器不复位,复位期间照常跟随 addr
    always @(posedge clk) addr_r <= addr;
    always @(posedge clk) begin
        if (rst) rd_data <= 32'h0;
        else     rd_data <= mem[addr_r];
    end
endmodule

// ===========================================================================
// data_ram 行为模型:同步读(1 拍) + 字节写使能 + NORMAL_WRITE
//   与 ipm2l_spram 语义一致:写周期不透明(读出的还是旧数据)
// ===========================================================================
module data_ram(
    input  wire [ 9:0] addr,
    input  wire [31:0] wr_data,
    output reg  [31:0] rd_data,
    input  wire        wr_en,
    input  wire [ 3:0] wr_byte_en,
    input  wire        clk,
    input  wire        rst
);
    reg [31:0] mem [0:1023];
    integer i;
    initial for (i = 0; i < 1024; i = i + 1) mem[i] = 32'h0;

    always @(posedge clk) begin
        if (rst) begin
            rd_data <= 32'h0;
        end else begin
            if (wr_en) begin
                if (wr_byte_en[0]) mem[addr][ 7: 0] <= wr_data[ 7: 0];
                if (wr_byte_en[1]) mem[addr][15: 8] <= wr_data[15: 8];
                if (wr_byte_en[2]) mem[addr][23:16] <= wr_data[23:16];
                if (wr_byte_en[3]) mem[addr][31:24] <= wr_data[31:24];
            end
            rd_data <= mem[addr];     // NORMAL_WRITE:写周期读出的仍是旧值
        end
    end
endmodule
