`timescale 1ns / 1ps

// 单主机、RAM/MMIO/DDR 数据总线互连。
//
// 地址空间：
//   RAM   : (地址 & RAM_ADDR_MASK)  == RAM_BASE
//   MMIO  : (地址 & MMIO_ADDR_MASK) == MMIO_BASE
//   DDR   : ENABLE_DDR && (地址 & DDR_ADDR_MASK) == DDR_BASE
//
// CPU 使用完整的 32 位字节地址；送给从机的地址已经减去对应 BASE，
// 因而从机只看到从 0 开始的局部地址。互连最多保留一笔未完成事务，
// 并锁存请求目标，保证响应返回时不会再用已经变化的 CPU 地址做选择。
module data_bus_interconnect #(
    parameter [31:0] RAM_BASE       = 32'h8000_0000,
    parameter [31:0] RAM_ADDR_MASK  = 32'hffff_c000, // 16 KiB
    parameter [31:0] MMIO_BASE      = 32'h1000_0000,
    parameter [31:0] MMIO_ADDR_MASK = 32'hffff_f000, // 4 KiB
    parameter integer ENABLE_DDR    = 0,
    parameter [31:0] DDR_BASE       = 32'h4000_0000,
    parameter [31:0] DDR_ADDR_MASK  = 32'he000_0000  // 512 MiB
) (
    input  wire        clk,
    input  wire        resetn,

    input  wire        m_req_valid,
    input  wire        m_req_write,
    input  wire [ 1:0] m_req_size,
    input  wire [31:0] m_req_addr,
    input  wire [31:0] m_req_wdata,
    input  wire [ 3:0] m_req_wstrb,
    output wire        m_req_ready,
    output wire        m_rsp_valid,
    output wire [31:0] m_rsp_rdata,
    output wire        m_rsp_error,

    output wire        ram_req_valid,
    output wire        ram_req_write,
    output wire [ 1:0] ram_req_size,
    output wire [31:0] ram_req_addr,
    output wire [31:0] ram_req_wdata,
    output wire [ 3:0] ram_req_wstrb,
    input  wire        ram_req_ready,
    input  wire        ram_rsp_valid,
    input  wire [31:0] ram_rsp_rdata,
    input  wire        ram_rsp_error,

    output wire        mmio_req_valid,
    output wire        mmio_req_write,
    output wire [ 1:0] mmio_req_size,
    output wire [31:0] mmio_req_addr,
    output wire [31:0] mmio_req_wdata,
    output wire [ 3:0] mmio_req_wstrb,
    input  wire        mmio_req_ready,
    input  wire        mmio_rsp_valid,
    input  wire [31:0] mmio_rsp_rdata,
    input  wire        mmio_rsp_error,

    output wire        ddr_req_valid,
    output wire        ddr_req_write,
    output wire [ 1:0] ddr_req_size,
    output wire [31:0] ddr_req_addr,
    output wire [31:0] ddr_req_wdata,
    output wire [ 3:0] ddr_req_wstrb,
    input  wire        ddr_req_ready,
    input  wire        ddr_rsp_valid,
    input  wire [31:0] ddr_rsp_rdata,
    input  wire        ddr_rsp_error
);

    localparam [1:0] TARGET_RAM   = 2'd0;
    localparam [1:0] TARGET_MMIO  = 2'd1;
    localparam [1:0] TARGET_DDR   = 2'd2;
    localparam [1:0] TARGET_ERROR = 2'd3;

    wire ram_select;
    wire mmio_select;
    wire ddr_select;
    wire req_fire;
    reg  pending;
    reg [1:0] response_target;

    assign ram_select  = ((m_req_addr & RAM_ADDR_MASK) ==
                          (RAM_BASE & RAM_ADDR_MASK));
    // RAM 优先，避免参数配置错误导致两个窗口重叠时同时选中从机。
    assign mmio_select = !ram_select &&
                         ((m_req_addr & MMIO_ADDR_MASK) ==
                          (MMIO_BASE & MMIO_ADDR_MASK));
    assign ddr_select = (ENABLE_DDR != 0) && !ram_select && !mmio_select &&
                        ((m_req_addr & DDR_ADDR_MASK) ==
                         (DDR_BASE & DDR_ADDR_MASK));

    assign m_req_ready = !pending &&
                         (ram_select  ? ram_req_ready  :
                          mmio_select ? mmio_req_ready :
                          ddr_select  ? ddr_req_ready  : 1'b1);
    assign req_fire = m_req_valid && m_req_ready;

    assign ram_req_valid = !pending && m_req_valid && ram_select;
    assign ram_req_write = m_req_write;
    assign ram_req_size  = m_req_size;
    assign ram_req_addr  = m_req_addr - RAM_BASE;
    assign ram_req_wdata = m_req_wdata;
    assign ram_req_wstrb = m_req_wstrb;

    assign mmio_req_valid = !pending && m_req_valid && mmio_select;
    assign mmio_req_write = m_req_write;
    assign mmio_req_size  = m_req_size;
    assign mmio_req_addr  = m_req_addr - MMIO_BASE;
    assign mmio_req_wdata = m_req_wdata;
    assign mmio_req_wstrb = m_req_wstrb;

    assign ddr_req_valid = !pending && m_req_valid && ddr_select;
    assign ddr_req_write = m_req_write;
    assign ddr_req_size  = m_req_size;
    assign ddr_req_addr  = m_req_addr - DDR_BASE;
    assign ddr_req_wdata = m_req_wdata;
    assign ddr_req_wstrb = m_req_wstrb;

    // 未映射地址也先完成请求握手，再在下一拍返回 error，避免 CPU 死等。
    assign m_rsp_valid = pending &&
                         ((response_target == TARGET_RAM)  ? ram_rsp_valid  :
                          (response_target == TARGET_MMIO) ? mmio_rsp_valid :
                          (response_target == TARGET_DDR)  ? ddr_rsp_valid  :
                                                              1'b1);
    assign m_rsp_rdata = (response_target == TARGET_RAM)  ? ram_rsp_rdata  :
                         (response_target == TARGET_MMIO) ? mmio_rsp_rdata :
                         (response_target == TARGET_DDR)  ? ddr_rsp_rdata  :
                                                           32'b0;
    assign m_rsp_error = m_rsp_valid &&
                         ((response_target == TARGET_RAM)  ? ram_rsp_error  :
                          (response_target == TARGET_MMIO) ? mmio_rsp_error :
                          (response_target == TARGET_DDR)  ? ddr_rsp_error  :
                                                            1'b1);

    always @(posedge clk) begin
        if (!resetn) begin
            pending         <= 1'b0;
            response_target <= TARGET_ERROR;
        end else begin
            if (m_rsp_valid)
                pending <= 1'b0;

            if (req_fire) begin
                pending <= 1'b1;
                if (ram_select)
                    response_target <= TARGET_RAM;
                else if (mmio_select)
                    response_target <= TARGET_MMIO;
                else if (ddr_select)
                    response_target <= TARGET_DDR;
                else
                    response_target <= TARGET_ERROR;
            end
        end
    end

endmodule
