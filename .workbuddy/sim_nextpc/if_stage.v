`timescale 1ns / 1ps
//==========================================================================
// if_stage.v —— 取指级:以 nextPC 作同步 ROM 的读地址
//
// 背景约束:ROM 只有 1 拍读延迟 —— 地址在时钟沿被内部寄存器锁存,
//           数据在下一个沿之后组合输出。若"老老实实"再放一级 IF/ID 去
//           等这个数据,前端就凭空多出一级(整机 6 级)。
//
// 本方案的做法:把 ROM 自带的那个地址寄存器,直接当成 PC 寄存器的"影子"。
//   地址端口接 nextPC(而不是 PC),于是每个时钟沿上:
//       PC 寄存器      <= nextPC
//       ROM 内部寄存器 <= nextPC      <-- 同一个值,同一个沿
//   两者永远锁步,于是恒有
//       rom_rdata(t) ≡ ROM[pc(t)]
//   取指级当拍就能拿到自己这条指令 —— 读请求在"更新 PC 的那一拍"发起,
//   输出正好在"取指阶段"完成,IF 级不额外多花一个寄存器。
//
// 复位处理(本方案唯一的坑):
//   ROM 内部寄存器的 D 端接的是 nextPC = pc+4,它不会自己回到复位向量。
//   解法:复位期间把 nextPC 强制成 RESET_VECTOR,让复位向量从它的 D 端
//   灌进去(走正常写入路径),而不是去指望 IP 的复位值功能(RST_VAL_EN)。
//   这样复位一释放,PC 与 ROM 输出就已经配对,且 0 气泡。
//==========================================================================
module if_stage #(
    parameter [31:0] RESET_VECTOR = 32'h0000_0000
)(
    input  wire        clk,
    input  wire        rst_i,         // 高有效、同步复位(保持与 IP 核一致)
    input  wire        stall_i,       // 1 = 冻结 PC(译码阻塞 / 访存结构冒险)
    input  wire        flush_i,       // 1 = 冲刷 IF/ID(分支、跳转、异常)
    input  wire        br_taken_i,    // 1 = 本拍提交分支/跳转
    input  wire [31:0] br_target_i,

    output wire [31:0] pc_o,          // 当前取指 PC
    output wire [31:0] rom_addr_o,    // ROM 地址端口(字节地址,外部取 [11:2])
    input  wire [31:0] rom_rdata_i,

    output reg  [31:0] if_id_pc_o,    // IF/ID:指令的 PC
    output reg  [31:0] if_id_inst_o,  // IF/ID:指令
    output reg         if_id_valid_o  // 0 = 气泡
);
    reg [31:0] pc_q;

    //------------------------------------------------------------------
    // 1) nextPC —— 它同时是"PC 寄存器的 D 端"和"ROM 的读地址"
    //    复位期间 = RESET_VECTOR(不是 pc+4),这是本方案能 0 气泡的关键
    //------------------------------------------------------------------
    wire [31:0] pc_plus4 = pc_q + 32'd4;
    wire [31:0] next_pc  = rst_i      ? RESET_VECTOR   :
                           stall_i    ? pc_q           :   // 冻结:PC 不动,
                                                           // ROM 地址也不动
                           br_taken_i ? br_target_i    :
                                        pc_plus4;

    always @(posedge clk) begin
        if (rst_i) pc_q <= RESET_VECTOR;
        else       pc_q <= next_pc;
    end

    assign pc_o       = pc_q;
    assign rom_addr_o = next_pc;      // ★ 组合直连:中间绝不能夹寄存器

    //------------------------------------------------------------------
    // 2) IF/ID —— 每个沿把 {当拍 PC, 当拍 ROM 输出} 整对锁存
    //    因为 rom_rdata ≡ ROM[pc_q],这一对天然是"同一条指令",无需再对齐
    //------------------------------------------------------------------
    always @(posedge clk) begin
        if (rst_i || flush_i) begin
            if_id_pc_o    <= 32'h0;
            if_id_inst_o  <= 32'h0;
            if_id_valid_o <= 1'b0;
        end else if (!stall_i) begin
            if_id_pc_o    <= pc_q;
            if_id_inst_o  <= rom_rdata_i;
            if_id_valid_o <= 1'b1;          // 复位释放后第一拍就是有效指令
        end
        // stall:整体保持,pc 与 rom 地址同步冻结 ⇒ 配对依然成立
    end

endmodule
