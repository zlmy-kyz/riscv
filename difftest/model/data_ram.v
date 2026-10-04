// ============================================================================
// data_ram.v -- 数据存储器的**时序忠实行为模型**（差分验证用）
// ----------------------------------------------------------------------------
// 替换 ipcore/data_ram/data_ram.v 参与仿真，接口一字不差：
//     data_ram u_data_ram(.wr_data, .addr[11:0], .wr_en, .wr_byte_en[3:0],
//                                .clk, .rst, .rd_data);
//
// 时序与真 IP 对齐（依据 doc/ROM与RAM时序处理方案总结.md 第 2 节、以及
// doc/data_ram写入数据错拍_bbbbbbbb问题.md 的复现结论）：
//   * **同步读、读延迟 1 拍**：地址在沿上被锁存，rd_data 反映的是**上一个沿
//     锁存的那个地址**的内容 —— 这正是 CPU 侧 load 必须多占一拍的依据。
//   * **写与时钟沿同步**，支持字节使能（sb/sh 靠 wr_byte_en 选字节道）。
//   * 读/写共用一套地址端口（单端口），NORMAL_WRITE 下写周期不透明。
//   * rst 高有效、同步；复位期间读输出为 0。
//
// ⚠️ 注意：这个"读延迟 1 拍"不是模型简化，是真 IP 的行为。
//     如果 myCPU 的 load 写回没有把这一步算进去，差分比对会在第一条 lw 处
//     精确报错 —— 那不是模型的问题，是 RTL 的问题。
// ============================================================================
`timescale 1ns / 1ps

module data_ram (
    input  wire [31:0] wr_data,
    input  wire [11:0] addr,
    input  wire        wr_en,
    input  wire [ 3:0] wr_byte_en,
    input  wire        clk,
    input  wire        rst,        // 高有效、同步
    output wire [31:0] rd_data
);

    reg [31:0] mem [0:4095];

    reg [11:0] addr_r;
    reg        rst_d1;
    reg [31:0] mask;

    integer i;
    initial begin
        for (i = 0; i < 4096; i = i + 1) mem[i] = 32'h0;
        addr_r = 12'h0;
        rst_d1 = 1'b1;
        $readmemh("ram.hex", mem, 0, 4095);
    end

    always @(posedge clk) begin
        rst_d1 <= rst;
        addr_r <= addr;
        if (wr_en && !rst) begin
            mask = { {8{wr_byte_en[3]}}, {8{wr_byte_en[2]}},
                     {8{wr_byte_en[1]}}, {8{wr_byte_en[0]}} };
            mem[addr] <= (mem[addr] & ~mask) | (wr_data & mask);
        end
    end

    assign rd_data = rst_d1 ? 32'h0 : mem[addr_r];

endmodule
