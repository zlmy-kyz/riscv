// ============================================================================
// inst_rom.v -- 指令存储器的**时序忠实行为模型**（差分验证用）
// ----------------------------------------------------------------------------
// 替换 ipcore/inst_rom/inst_rom.v 参与仿真，接口一字不差：
//     inst_rom u_inst_rom(.addr(a[11:0]), .clk, .rst, .rd_data);
//
// 为什么不在差分验证里直接用厂商 IP？
//   1) iverilog 里拿不到原语 GTP_DRM36K_E1 的源文件（Pango 只提供编译好的
//      ModelSim 库 D:\modelsim\...\pango_sim_libraries\*，没有 .v）；
//   2) 差分验证需要"换程序不用重新生成 IP"，所以必须走 $readmemh。
//   最终验收仍应在 vsim + 真 IP 上复跑同一套黄金轨迹，见 difftest/README.md。
//
// 时序按 doc/ROM与RAM时序处理方案总结.md 与 doc/取指ROM复位后丢第一条指令_原因与修复.md
// 的实测结论建模：
//   * 同步单端口、读延迟 1 拍：地址在上升沿被锁存，数据在沿后有效
//   * OUTPUT_REG=0 / FAB_REG=0  -> 读通路里只有那一个**地址寄存器**，
//     所以数据是"地址寄存器 + 组合阵列"出来的，不是再打一拍
//   * 内部地址寄存器**不带复位**（RST_VAL_EN=false）
//   * rst 撤销后输出仍被强制为 0 **一个时钟**（IP 内部把 rst 打了一拍）
//
// 最后这条是"丢第一条指令"那个坑的根源。本模型保留它，所以它比"乐观模型"
// 更悲观 —— 能在这个模型下过，才是真的过。
// ============================================================================
`timescale 1ns / 1ps

module inst_rom (
    input  wire [11:0] addr,
    input  wire        clk,
    input  wire        rst,        // 高有效、同步
    output wire [31:0] rd_data
);

    reg [31:0] mem [0:4095];

    reg [11:0] addr_r;     // IP 内部地址寄存器：不复位
    reg       rst_d1;      // rst 打一拍 -> 输出强制 0 的窗口

    integer i;
    initial begin
        for (i = 0; i < 4096; i = i + 1) mem[i] = 32'h0;
        rst_d1 = 1'b1;
        addr_r = 12'h0;
        $readmemh("rom.hex", mem, 0, 4095);
    end

    always @(posedge clk) begin
        rst_d1 <= rst;
        addr_r <= addr;                        // 复位期间照常锁存
    end

    assign rd_data = rst_d1 ? 32'h0 : mem[addr_r];

endmodule
