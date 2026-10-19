`timescale 1ns / 1ps

// 单主机、RAM/MMIO/UART/DDR 数据总线互连。
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
    parameter [31:0] DDR_ADDR_MASK  = 32'he000_0000, // 512 MiB
    parameter integer ENABLE_CNN = 0,
    parameter integer ENABLE_PREPROCESS = 0,
    parameter integer ENABLE_CAMERA = 0,
    parameter integer ENABLE_UART  = 0,
    parameter [31:0] UART_BASE      = 32'h1000_1000, // 16-byte aligned, 16 bytes
    parameter integer DDR_WRITE_ORDER_ENABLE = 0,
    parameter integer RESPONSE_TURNOVER_ENABLE = 1
) (
    output wire cnn_req_valid, cnn_req_write,
    output wire [1:0] cnn_req_size,
    output wire [31:0] cnn_req_addr, cnn_req_wdata,
    output wire [3:0] cnn_req_wstrb,
    input wire cnn_req_ready, cnn_rsp_valid, cnn_rsp_error,
    input wire [31:0] cnn_rsp_rdata,
    output wire pp_req_valid, pp_req_write,
    output wire [1:0] pp_req_size,
    output wire [31:0] pp_req_addr, pp_req_wdata,
    output wire [3:0] pp_req_wstrb,
    input wire pp_req_ready, pp_rsp_valid, pp_rsp_error,
    input wire [31:0] pp_rsp_rdata,
    input wire preprocess_busy, preprocess_done,
    output wire cam_req_valid, cam_req_write,
    output wire [1:0] cam_req_size,
    output wire [31:0] cam_req_addr, cam_req_wdata,
    output wire [3:0] cam_req_wstrb,
    input wire cam_req_ready, cam_rsp_valid, cam_rsp_error,
    input wire [31:0] cam_rsp_rdata,
    input wire camera_busy,
    input wire camera_dual_mode,
    input wire [1:0] camera_cpu_owned,
    input  wire        clk,
    input  wire        resetn,
    input  wire        ddr_write_buffer_busy,

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
    input  wire        ddr_rsp_error,
    output wire        uart_req_valid,
    output wire        uart_req_write,
    output wire [ 1:0] uart_req_size,
    output wire [31:0] uart_req_addr,
    output wire [31:0] uart_req_wdata,
    output wire [ 3:0] uart_req_wstrb,
    input  wire        uart_req_ready,
    input  wire        uart_rsp_valid,
    input  wire [31:0] uart_rsp_rdata,
    input  wire        uart_rsp_error
);

    localparam [2:0] TARGET_RAM   = 3'd0;
    localparam [2:0] TARGET_MMIO  = 3'd1;
    localparam [2:0] TARGET_DDR   = 3'd2;
    localparam [2:0] TARGET_ERROR = 3'd3;
    localparam [2:0] TARGET_CNN = 3'd7;
    localparam [2:0] TARGET_PREPROCESS = 3'd6;
    localparam [2:0] TARGET_CAMERA = 3'd5;
    localparam [2:0] TARGET_UART  = 3'd4;

    wire ram_select;
    wire mmio_select;
    wire ddr_select;
    wire uart_select;
    wire cam_select=(ENABLE_CAMERA!=0) && !ram_select && !mmio_select && !uart_select &&
                    (m_req_addr[31:6]==(32'h10002000 >> 6));
    // Two 2MiB slots. In stream mode CPU may only READ a claimed slot;
    // READY is not enough, and a RELEASE closes access before future DMA reuse.
    wire pp_select=(ENABLE_PREPROCESS!=0) && !ram_select && !mmio_select && !uart_select && !cam_select &&
                   (m_req_addr[31:6]==(32'h10003000 >> 6));
    wire cnn_select=(ENABLE_CNN!=0) && !ram_select && !mmio_select && !uart_select && !cam_select && !pp_select &&
                    (m_req_addr[31:8]==24'h100040);
    wire pp_blocked=(ENABLE_PREPROCESS!=0) && (m_req_addr[31:16]==16'h4200) &&
                    (m_req_write || preprocess_busy || !preprocess_done || m_req_addr[15:0]>=16'h6c00);
    wire frame_window=(m_req_addr[31:22]==(32'h41000000 >> 22));
    wire frame_blocked=(ENABLE_CAMERA!=0) && frame_window &&
                       (camera_dual_mode ? (m_req_write || !camera_cpu_owned[m_req_addr[21]]) : camera_busy);
    wire req_fire;
    wire issue_allowed;
    wire response_turnover;
    reg  pending;
    reg [2:0] response_target;

    assign ram_select  = ((m_req_addr & RAM_ADDR_MASK) ==
                          (RAM_BASE & RAM_ADDR_MASK));
    // RAM 优先，避免参数配置错误导致两个窗口重叠时同时选中从机。
    assign mmio_select = !ram_select &&
                         ((m_req_addr & MMIO_ADDR_MASK) ==
                          (MMIO_BASE & MMIO_ADDR_MASK));
    assign uart_select = (ENABLE_UART != 0) && !ram_select && !mmio_select &&
                         (m_req_addr[31:4] == UART_BASE[31:4]);
    assign ddr_select = (ENABLE_DDR != 0) && !ram_select && !mmio_select && !uart_select && !cam_select && !pp_select && !cnn_select && !frame_blocked && !pp_blocked &&
                        ((m_req_addr & DDR_ADDR_MASK) ==
                         (DDR_BASE & DDR_ADDR_MASK));

    // DDR requests are backpressured by the bridge; all other accesses drain first.
    // In particular, PERF STOP and UART side effects cannot overtake buffered stores.
    // The current response keeps its latched owner until the accepting edge.
    // A successful response frees the sole slot for a new request on that edge.
    // Error responses still close the slot first; no younger side effect crosses
    // an older access fault. Slave ready and buffered-write ordering still apply.
    assign response_turnover = (RESPONSE_TURNOVER_ENABLE != 0) &&
                               m_rsp_valid && !m_rsp_error;
    assign issue_allowed = (!pending || response_turnover) &&
                                        ((DDR_WRITE_ORDER_ENABLE == 0) ||
                                         !ddr_write_buffer_busy || ddr_select);
    assign m_req_ready = issue_allowed &&
                         (ram_select  ? ram_req_ready  :
                          mmio_select ? mmio_req_ready :
                          cnn_select  ? cnn_req_ready  :
                          pp_select   ? pp_req_ready   :
                          cam_select  ? cam_req_ready  :
                          uart_select ? uart_req_ready :
                          ddr_select  ? ddr_req_ready  : 1'b1);
    assign req_fire = m_req_valid && m_req_ready;

    assign ram_req_valid = issue_allowed && m_req_valid && ram_select;
    assign ram_req_write = m_req_write;
    assign ram_req_size  = m_req_size;
    assign ram_req_addr  = m_req_addr - RAM_BASE;
    assign ram_req_wdata = m_req_wdata;
    assign ram_req_wstrb = m_req_wstrb;

    assign mmio_req_valid = issue_allowed && m_req_valid && mmio_select;
    assign mmio_req_write = m_req_write;
    assign mmio_req_size  = m_req_size;
    assign mmio_req_addr  = m_req_addr - MMIO_BASE;
    assign mmio_req_wdata = m_req_wdata;
    assign mmio_req_wstrb = m_req_wstrb;

    assign ddr_req_valid = issue_allowed && m_req_valid && ddr_select;
    assign ddr_req_write = m_req_write;
    assign ddr_req_size  = m_req_size;
    assign ddr_req_addr  = m_req_addr - DDR_BASE;
    assign ddr_req_wdata = m_req_wdata;
    assign ddr_req_wstrb = m_req_wstrb;

    assign uart_req_valid = issue_allowed && m_req_valid && uart_select;
    assign uart_req_write = m_req_write;
    assign uart_req_size  = m_req_size;
    assign uart_req_addr  = m_req_addr - UART_BASE;
    assign uart_req_wdata = m_req_wdata;
    assign uart_req_wstrb = m_req_wstrb;

    assign cnn_req_valid=issue_allowed && m_req_valid && cnn_select;
    assign cnn_req_write=m_req_write;
    assign cnn_req_size=m_req_size;
    assign cnn_req_addr=m_req_addr-32'h10004000;
    assign cnn_req_wdata=m_req_wdata;
    assign cnn_req_wstrb=m_req_wstrb;
    assign pp_req_valid=issue_allowed && m_req_valid && pp_select;
    assign pp_req_write=m_req_write;
    assign pp_req_size=m_req_size;
    assign pp_req_addr=m_req_addr-32'h10003000;
    assign pp_req_wdata=m_req_wdata;
    assign pp_req_wstrb=m_req_wstrb;
    assign cam_req_valid=issue_allowed && m_req_valid && cam_select;
    assign cam_req_write=m_req_write;
    assign cam_req_size=m_req_size;
    assign cam_req_addr=m_req_addr-32'h10002000;
    assign cam_req_wdata=m_req_wdata;
    assign cam_req_wstrb=m_req_wstrb;

    // 未映射地址也先完成请求握手，再在下一拍返回 error，避免 CPU 死等。
    assign m_rsp_valid = pending &&
                         ((response_target == TARGET_RAM)  ? ram_rsp_valid  :
                          (response_target == TARGET_MMIO) ? mmio_rsp_valid :
                          (response_target == TARGET_DDR)  ? ddr_rsp_valid  :
                          (response_target == TARGET_CNN) ? cnn_rsp_valid :
                          (response_target == TARGET_PREPROCESS) ? pp_rsp_valid :
                          (response_target == TARGET_CAMERA) ? cam_rsp_valid :
                          (response_target == TARGET_UART) ? uart_rsp_valid :
                                                              1'b1);
    assign m_rsp_rdata = (response_target == TARGET_RAM)  ? ram_rsp_rdata  :
                         (response_target == TARGET_MMIO) ? mmio_rsp_rdata :
                         (response_target == TARGET_DDR)  ? ddr_rsp_rdata  :
                         (response_target == TARGET_CNN) ? cnn_rsp_rdata :
                         (response_target == TARGET_PREPROCESS) ? pp_rsp_rdata :
                         (response_target == TARGET_CAMERA) ? cam_rsp_rdata :
                         (response_target == TARGET_UART) ? uart_rsp_rdata :
                                                           32'b0;
    assign m_rsp_error = m_rsp_valid &&
                         ((response_target == TARGET_RAM)  ? ram_rsp_error  :
                          (response_target == TARGET_MMIO) ? mmio_rsp_error :
                          (response_target == TARGET_DDR)  ? ddr_rsp_error  :
                          (response_target == TARGET_CNN) ? cnn_rsp_error :
                          (response_target == TARGET_PREPROCESS) ? pp_rsp_error :
                          (response_target == TARGET_CAMERA) ? cam_rsp_error :
                          (response_target == TARGET_UART) ? uart_rsp_error :
                                                            1'b1);

    always @(posedge clk) begin
        if (!resetn) begin
            pending         <= 1'b0;
            response_target <= TARGET_ERROR;
        end else begin
            if (m_rsp_valid)
                pending <= 1'b0;

            if (req_fire) begin
                // Later assignment wins: old response completes, new owner lives.
                pending <= 1'b1;
                if (ram_select)
                    response_target <= TARGET_RAM;
                else if (mmio_select)
                    response_target <= TARGET_MMIO;
                else if (cnn_select)
                    response_target <= TARGET_CNN;
                else if (pp_select)
                    response_target <= TARGET_PREPROCESS;
                else if (cam_select)
                    response_target <= TARGET_CAMERA;
                else if (ddr_select)
                    response_target <= TARGET_DDR;
                else if (uart_select)
                    response_target <= TARGET_UART;
                else
                    response_target <= TARGET_ERROR;
            end
        end
    end

endmodule
