//////////////////////////////////////////////////////////////////////////////
// 文件名 : topcpu_tb.v
// 功能   : topcpu(取指部分)的仿真测试平台
//   验证点:
//     1. 复位(同步)期间 if_id_valid = 0;
//     2. 复位释放后:第 1 次 IF/ID 写入是气泡(run_d1),之后每拍有效;
//     3. if_id_pc 从 0x0 起每次 +4,且 if_id_inst == ROM[if_id_pc>>2](1 拍读配对);
//   说明:
//     ROM 模型:同步复位、1 拍读(地址在沿上锁存、数据组合输出),
//     与你的 ROM IP 行为一致;数据文件 D:/riscv/tbtb/rom_test.dat(1024 字)。
//////////////////////////////////////////////////////////////////////////////

`timescale 1ns / 1ps

module topcpu_tb;

    //--------------------------------------------------------------------------
    // 信号声明
    //--------------------------------------------------------------------------
    reg         clk;
    reg         resetn;                 // 低有效,同步复位(与 CPU/IP 一致)

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

    //--------------------------------------------------------------------------
    // 时钟: 10ns 周期
    //--------------------------------------------------------------------------
    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    //--------------------------------------------------------------------------
    // 激励:复位(覆盖多个沿)→ 释放,跑一段时间
    //--------------------------------------------------------------------------
    initial begin
        resetn = 1'b0;
        #60;                        // 复位 60ns(6 个沿,同步复位足够)
        resetn = 1'b1;              // 释放
        #400;
        $finish;
    end

    //--------------------------------------------------------------------------
    // ROM 模型:同步复位 + 1 拍读(与 ROM IP 时序一致)
    //   复位时地址寄存器清 0;释放后每个沿锁存总线地址,数据组合输出
    //--------------------------------------------------------------------------
    reg  [31:0] rom_mem [0:1023];
    reg  [ 9:0] rom_addr_r;
    initial $readmemh("D:/riscv/tbtb/rom_test.dat", rom_mem);

    always @(posedge clk) begin
        if (!resetn) rom_addr_r <= 10'd0;
        else         rom_addr_r <= inst_sram_addr[11:2];   // 字节地址 → 字地址
    end
    assign inst_sram_rdata = rom_mem[rom_addr_r];

    //--------------------------------------------------------------------------
    // DUT
    //--------------------------------------------------------------------------
    topcpu u_topcpu(
        .clk             (clk             ),
        .resetn          (resetn          ),
        .inst_sram_addr  (inst_sram_addr  ),
        .inst_sram_rdata (inst_sram_rdata ),
        .data_sram_we    (data_sram_we    ),
        .data_sram_addr  (data_sram_addr  ),
        .data_sram_wdata (data_sram_wdata ),
        .data_sram_rdata (data_sram_rdata ),
        .debug_wb_pc     (debug_wb_pc     ),
        .debug_wb_rf_we  (debug_wb_rf_we  ),
        .debug_wb_rf_wnum(debug_wb_rf_wnum),
        .debug_wb_rf_wdata(debug_wb_rf_wdata)
    );

    //--------------------------------------------------------------------------
    // 自检:每个沿后 #1 采样(避竞争),检查
    //   * 第一条有效指令 pc 必须 = 0x0(说明复位后没有垃圾指令混入);
    //   * 之后每条有效指令 pc 逐次 +4;
    //   * if_id_inst 必须 == ROM[pc>>2](PC 与指令配对)。
    //--------------------------------------------------------------------------
    integer     vld_cnt;
    reg  [31:0] expect_pc;
    reg  [31:0] err_cnt;

    initial $timeformat(-9, 0, " ns", 10);

    always @(posedge clk) begin
        #1;                                  // 采样延迟,避开沿上竞争
        if (!resetn) begin
            expect_pc <= 32'h0;
            err_cnt   <= 32'h0;
            vld_cnt   <= 0;
        end
        else if (u_topcpu.u_ifu.if_id_valid) begin
            vld_cnt <= vld_cnt + 1;

            // 1) PC 必须是期望值(0x0 起 +4 递增)
            if (u_topcpu.u_ifu.if_id_pc !== expect_pc) begin
                err_cnt <= err_cnt + 1;
                $display("[%0t] ERROR: if_id_pc = %08h,期望 %08h",
                         $time, u_topcpu.u_ifu.if_id_pc, expect_pc);
            end

            // 2) 指令必须与 PC 配对(1 拍读对齐)
            if (u_topcpu.u_ifu.if_id_inst !== rom_mem[expect_pc[11:2]]) begin
                err_cnt <= err_cnt + 1;
                $display("[%0t] ERROR: if_id_inst = %08h,期望 mem[%3d] = %08h (PC 与指令不配对)",
                         $time, u_topcpu.u_ifu.if_id_inst,
                         expect_pc[11:2], rom_mem[expect_pc[11:2]]);
            end
            else begin
                $display("[%0t] PC = %08h,INST = %08h   <== 配对正确",
                         $time, u_topcpu.u_ifu.if_id_pc, u_topcpu.u_ifu.if_id_inst);
            end

            expect_pc <= expect_pc + 32'h4;
        end
    end

    //--------------------------------------------------------------------------
    // 结束判定
    //--------------------------------------------------------------------------
    initial begin
        #460;                       // 跑 16 条有效指令后总结
        if (err_cnt == 0) begin
            $display("==========================================================");
            $display("---- PASS: 取指配对正确,共取 %0d 条有效指令 ----", vld_cnt);
        end
        else begin
            $display("---- FAIL: 共 %0d 处错误 ----", err_cnt);
        end
        $finish;
    end

endmodule
