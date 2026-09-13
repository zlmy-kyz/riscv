`timescale 1ns / 1ps
//=============================================================================
// mem_write_stage.v
//   演示"EX 级发出写请求 → 下一个 clk 上升沿内存值实际写入"的完整过程。
//
//   时序约定（与你的设计一致）：
//     - 读/写请求在指令位于 EX  阶段时发出（组合，直连 data_ram）
//     - 写数据在下一个 clk 上升沿真正落入 RAM
//     - 读数据在指令位于 MEM 阶段时返回
//
//   四个信号全部由 EX 级组合产生、同拍到达 RAM：
//     data_ram.wr_en   = ex_valid & ex_mem_wen
//     data_ram.addr    = ex_addr  (= x[rs1] + imm)
//     data_ram.wr_data = ex_rd_data2
//     data_ram.rd_en   = ex_valid & ex_mem_ren
//=============================================================================
module mem_write_stage (
    input  wire        clk,
    input  wire        resetn,

    // ---- 来自 ID 级（已由 ID/EX 寄存器锁存）----
    input  wire        id_ex_valid,
    input  wire        id_ex_mem_wen,      // 内存写使能
    input  wire        id_ex_mem_ren,      // 内存读使能
    input  wire [31:0] id_ex_rd_data1,     // x[rs1] 的值（读寄存器1）
    input  wire [31:0] id_ex_rd_data2,     // 要写入内存的数据
    input  wire [31:0] id_ex_imm,          // 立即数

    // ---- 来自 ID 级但需要 EX 计算的地址 ----
    output wire [31:0] ex_addr,            // = rd_data1 + imm
    output wire        ex_mem_wen,
    output wire        ex_mem_ren,

    // ---- 直连 data_ram ----
    output wire [31:0] dram_addr,
    output wire        dram_wr_en,
    output wire [31:0] dram_wr_data,
    output wire [3:0]  dram_wr_byte_en,
    input  wire [31:0] dram_rd_data,

    // ---- 调试输出：MEM 级看到的读数据 ----
    output reg  [31:0] mem_rd_data,
    output reg         mem_rd_valid
);

    //--------------------------------------------------------------------------
    // 1) EX 级：地址计算（组合，最慢路径）
    //--------------------------------------------------------------------------
    assign ex_addr = id_ex_rd_data1 + id_ex_imm;

    //--------------------------------------------------------------------------
    // 2) EX 级：读/写使能（组合，与地址同拍生成）
    //--------------------------------------------------------------------------
    assign ex_mem_wen = id_ex_valid & id_ex_mem_wen;
    assign ex_mem_ren = id_ex_valid & id_ex_mem_ren;

    //--------------------------------------------------------------------------
    // 3) 四个信号一起直连到 data_ram —— 同源同拍，天然对齐
    //--------------------------------------------------------------------------
    assign dram_addr       = ex_addr;
    assign dram_wr_data    = id_ex_rd_data2;     // 直连，不寄存
    assign dram_wr_en      = ex_mem_wen;         // 直连，不寄存
    assign dram_wr_byte_en = 4'b1111;            // 字写，全字节使能

    //--------------------------------------------------------------------------
    // 4) MEM 级：在下一个 clk 上升沿，RAM 的读数据返回
    //    （RAM 在 EX/MEM 沿采地址，下一拍输出 —— 这里直接对 rd_data 打一拍）
    //--------------------------------------------------------------------------
    always @(posedge clk) begin
        if (!resetn) begin
            mem_rd_data  <= 32'h0;
            mem_rd_valid <= 1'b0;
        end else begin
            mem_rd_data  <= dram_rd_data;
            mem_rd_valid <= ex_mem_ren;
        end
    end

endmodule
