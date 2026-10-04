`timescale 1ns / 1ps

// 单主机、ROM/DDR 指令总线互连/地址译码器。
// ROM/DDR 窗口内的完整 CPU 地址先减去对应 BASE，再交给从机；未映射请求
// 在下一拍返回 rsp_error，供 CPU 产生 Instruction Access Fault。
// 支持“旧响应完成 + 新请求接受”同拍发生，保持现有取指接口的周转能力。
module inst_bus_interconnect #(
    parameter [31:0] ROM_BASE      = 32'h8000_0000,
    parameter [31:0] ROM_ADDR_MASK = 32'hffff_c000, // 16 KiB
    parameter integer ENABLE_DDR   = 0,
    parameter [31:0] DDR_BASE      = 32'h4000_0000,
    parameter [31:0] DDR_ADDR_MASK = 32'he000_0000  // 512 MiB
) (
    input  wire        clk,
    input  wire        resetn,

    input  wire        m_req_valid,
    input  wire [31:0] m_req_addr,
    output wire        m_req_ready,
    output wire        m_rsp_valid,
    output wire [31:0] m_rsp_rdata,
    output wire        m_rsp_error,

    output wire        rom_req_valid,
    output wire [31:0] rom_req_addr,
    input  wire        rom_req_ready,
    input  wire        rom_rsp_valid,
    input  wire [31:0] rom_rsp_rdata,
    input  wire        rom_rsp_error,

    output wire        ddr_req_valid,
    output wire [31:0] ddr_req_addr,
    input  wire        ddr_req_ready,
    input  wire        ddr_rsp_valid,
    input  wire [31:0] ddr_rsp_rdata,
    input  wire        ddr_rsp_error
);

    localparam [1:0] TARGET_ROM   = 2'd0;
    localparam [1:0] TARGET_DDR   = 2'd1;
    localparam [1:0] TARGET_ERROR = 2'd2;

    wire rom_select;
    wire ddr_select;
    wire response_done;
    wire can_accept;
    wire req_fire;
    reg  pending;
    reg [1:0] response_target;

    assign rom_select = ((m_req_addr & ROM_ADDR_MASK) ==
                         (ROM_BASE & ROM_ADDR_MASK));
    assign ddr_select = (ENABLE_DDR != 0) && !rom_select &&
                        ((m_req_addr & DDR_ADDR_MASK) ==
                         (DDR_BASE & DDR_ADDR_MASK));

    assign m_rsp_valid = pending &&
                         ((response_target == TARGET_ROM) ? rom_rsp_valid :
                          (response_target == TARGET_DDR) ? ddr_rsp_valid :
                                                            1'b1);
    assign m_rsp_rdata = (response_target == TARGET_ROM) ? rom_rsp_rdata :
                         (response_target == TARGET_DDR) ? ddr_rsp_rdata :
                                                           32'b0;
    assign m_rsp_error = m_rsp_valid &&
                         ((response_target == TARGET_ROM) ? rom_rsp_error :
                          (response_target == TARGET_DDR) ? ddr_rsp_error :
                                                            1'b1);

    assign response_done = m_rsp_valid;
    assign can_accept = !pending || response_done;
    assign m_req_ready = can_accept &&
                         (rom_select ? rom_req_ready :
                          ddr_select ? ddr_req_ready : 1'b1);
    assign req_fire = m_req_valid && m_req_ready;

    assign rom_req_valid = can_accept && m_req_valid && rom_select;
    assign rom_req_addr  = m_req_addr - ROM_BASE;
    assign ddr_req_valid = can_accept && m_req_valid && ddr_select;
    assign ddr_req_addr  = m_req_addr - DDR_BASE;

    always @(posedge clk) begin
        if (!resetn) begin
            pending         <= 1'b0;
            response_target <= TARGET_ERROR;
        end else begin
            if (response_done)
                pending <= 1'b0;

            if (req_fire) begin
                pending <= 1'b1;
                response_target <= rom_select ? TARGET_ROM :
                                   ddr_select ? TARGET_DDR : TARGET_ERROR;
            end
        end
    end

endmodule
