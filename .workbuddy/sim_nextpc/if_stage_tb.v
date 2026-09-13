`timescale 1ns / 1ps
//==========================================================================
// if_stage_tb.v —— if_stage(以 nextPC 作 ROM 读地址)自检 tb
//
// 检查点:
//   A) 复位释放后 0 气泡:第一个时钟沿就产出有效指令,且 pc = 0
//   B) PC 与指令恒配对:if_id_inst == ROM[if_id_pc>>2](全程逐拍检查)
//   C) stall 冻结 PC;flush + 跳转只花 1 个气泡
//
// ROM 模型:故意**不给内部地址寄存器复位**(悲观模型,初值 X),
//   用来证明本方案不依赖 IP 的复位值功能。
//   ROM[i] = 32'h1000_0000 + i*4,于是"配对正确"等价于
//       if_id_inst == 32'h1000_0000 + if_id_pc
//==========================================================================
module if_stage_tb;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg         rst_i       = 1'b1;
    reg         stall_i     = 1'b0;
    reg         flush_i     = 1'b0;
    reg         br_taken_i  = 1'b0;
    reg  [31:0] br_target_i = 32'h0;

    wire [31:0] pc_o, rom_addr_o, rom_rdata_i;
    wire [31:0] if_id_pc_o, if_id_inst_o;
    wire        if_id_valid_o;

    //---------------- 悲观 ROM 模型(内部地址寄存器不复位) ----------------
    reg  [31:0] rom [0:1023];
    reg  [ 9:0] rom_addr_q;
    integer i;
    initial for (i = 0; i < 1024; i = i + 1) rom[i] = 32'h1000_0000 + i * 4;

    always @(posedge clk) rom_addr_q <= rom_addr_o[11:2];
    assign rom_rdata_i = rom[rom_addr_q];

    if_stage dut (
        .clk(clk), .rst_i(rst_i), .stall_i(stall_i), .flush_i(flush_i),
        .br_taken_i(br_taken_i), .br_target_i(br_target_i),
        .pc_o(pc_o), .rom_addr_o(rom_addr_o), .rom_rdata_i(rom_rdata_i),
        .if_id_pc_o(if_id_pc_o), .if_id_inst_o(if_id_inst_o),
        .if_id_valid_o(if_id_valid_o)
    );

    //---------------- 逐拍配对检查 ----------------
    integer err_cnt = 0;
    integer vld_cnt = 0;
    always @(posedge clk) begin
        #1;
        if (if_id_valid_o) begin
            vld_cnt = vld_cnt + 1;
            if (if_id_inst_o !== (32'h1000_0000 + if_id_pc_o)) begin
                err_cnt = err_cnt + 1;
                $display("[%0t] ERROR 配对失败: pc=%08h inst=%08h",
                         $time, if_id_pc_o, if_id_inst_o);
            end
        end
    end

    reg [31:0] hold_pc, hold_ifpc;

    initial begin
        $timeformat(-9, 0, " ns", 10);

        //=================== 复位(6 个沿)===================
        repeat (6) @(posedge clk);
        @(negedge clk); rst_i = 1'b0;

        //=================== A) 0 气泡 ===================
        @(posedge clk); #1;
        if (!if_id_valid_o) begin
            err_cnt = err_cnt + 1;
            $display("[%0t] ERROR A) 复位后第一拍没有有效指令(多出气泡)", $time);
        end else if (if_id_pc_o !== 32'h0) begin
            err_cnt = err_cnt + 1;
            $display("[%0t] ERROR A) 第一条指令 pc=%08h,应为 0", $time, if_id_pc_o);
        end else begin
            $display("[%0t] OK  A) 复位后第一拍即取到 PC=0 的有效指令(0 气泡)", $time);
        end

        repeat (6) @(posedge clk);

        //=================== B) stall 冻结 ===================
        #1;                                   // 避开沿上竞争,读沿后的稳定值
        hold_pc   = pc_o;
        hold_ifpc = if_id_pc_o;
        @(negedge clk); stall_i = 1'b1;
        repeat (3) @(posedge clk);
        if (pc_o !== hold_pc || if_id_pc_o !== hold_ifpc) begin
            err_cnt = err_cnt + 1;
            $display("[%0t] ERROR B) stall 期间 PC/IF-ID 未冻结", $time);
        end else begin
            $display("[%0t] OK  B) stall 期间 pc=%08h 与 IF/ID 均冻结", $time, pc_o);
        end
        @(negedge clk); stall_i = 1'b0;
        @(posedge clk);

        //=================== C) flush + 跳转 0x40 ===================
        @(negedge clk); flush_i = 1'b1; br_taken_i = 1'b1; br_target_i = 32'h40;
        @(posedge clk); #1;                       // 冲刷沿:IF/ID 应被打成气泡
        if (if_id_valid_o) begin
            err_cnt = err_cnt + 1;
            $display("[%0t] ERROR C) 冲刷沿未插入气泡", $time);
        end else begin
            $display("[%0t] OK  C) 冲刷插入 1 个气泡", $time);
        end
        @(negedge clk); flush_i = 1'b0; br_taken_i = 1'b0;
        @(posedge clk); #1;                       // 下一沿:目标指令应就位
        if (!if_id_valid_o || if_id_pc_o !== 32'h40) begin
            err_cnt = err_cnt + 1;
            $display("[%0t] ERROR C) 跳转目标未恢复:valid=%b pc=%08h",
                     $time, if_id_valid_o, if_id_pc_o);
        end else begin
            $display("[%0t] OK  C) 跳转目标 0x40 恢复取指", $time);
        end

        repeat (6) @(posedge clk);

        $display("=========================================================");
        if (err_cnt == 0)
            $display("---- PASS:共 %0d 条有效指令,PC/指令配对全部正确 ----", vld_cnt);
        else
            $display("---- FAIL:共 %0d 处错误 ----", err_cnt);
        $finish;
    end
endmodule
