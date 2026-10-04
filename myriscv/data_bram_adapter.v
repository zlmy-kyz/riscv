`timescale 1ns / 1ps

// 将 CPU 的类 SRAM 请求/响应接口转换为本工程单端口同步 BRAM 接口。
//
// 总线约定：
//   * req_valid && req_ready：地址、写数据和控制信息被接受。
//   * rsp_valid：上一笔请求完成；读请求的 rsp_rdata 在同一拍有效。
//   * 首版只允许一笔未完成事务，响应无需反压，CPU 必须在 rsp_valid 当拍接收。
//   * 请求未被接受时，CPU 负责保持请求字段稳定。
module data_bram_adapter #(
    parameter integer RAM_ADDR_WIDTH = 12,
    // 默认均为 0：空闲时立即接受请求，BRAM 固有一拍后返回响应。
    // 非零值用于仿真/低速从设备建模，可验证 CPU 的任意等待周期处理。
    parameter integer REQ_STALL_CYCLES = 0,
    parameter integer RSP_DELAY_CYCLES = 0
) (
    input  wire                      clk,
    input  wire                      resetn,

    input  wire                      req_valid,
    input  wire                      req_write,
    input  wire [1:0]                req_size,
    input  wire [31:0]               req_addr,
    input  wire [31:0]               req_wdata,
    input  wire [3:0]                req_wstrb,
    output wire                      req_ready,

    output wire                      rsp_valid,
    output wire [31:0]               rsp_rdata,
    output wire                      rsp_error,

    output wire [RAM_ADDR_WIDTH-1:0] ram_addr,
    output wire [31:0]               ram_wdata,
    output wire [3:0]                ram_wstrb,
    output wire                      ram_we,
    input  wire [31:0]               ram_rdata
);

    reg pending;
    reg [31:0] req_wait_count;
    reg [31:0] rsp_wait_count;
    reg [RAM_ADDR_WIDTH-1:0] accepted_ram_addr;
    wire req_fire;

    assign req_ready = !pending &&
                       ((REQ_STALL_CYCLES == 0) ||
                        (req_wait_count >= REQ_STALL_CYCLES));
    assign req_fire  = req_valid && req_ready;

    // BRAM 在请求接受沿锁存地址，沿后给出读数据；pending 因而正好成为
    // 下一拍的 data_ok/rsp_valid。写请求也返回一次完成响应，以维持顺序。
    assign rsp_valid = pending && (rsp_wait_count == 0);
    assign rsp_rdata = ram_rdata;
    assign rsp_error = 1'b0;

    // 请求接受后必须固定 BRAM 地址直到响应。否则在额外响应延迟期间，
    // 空闲 EX 级的组合地址会让同步 RAM 输出漂到另一位置。
    assign ram_addr  = pending ? accepted_ram_addr :
                                 req_addr[RAM_ADDR_WIDTH+1:2];
    assign ram_wdata = req_wdata;
    assign ram_wstrb = req_wstrb;
    assign ram_we    = req_fire && req_write;

    always @(posedge clk) begin
        if (!resetn) begin
            pending <= 1'b0;
            req_wait_count <= 32'b0;
            rsp_wait_count <= 32'b0;
            accepted_ram_addr <= {RAM_ADDR_WIDTH{1'b0}};
        end else begin
            if (!pending && req_valid && !req_ready)
                req_wait_count <= req_wait_count + 32'd1;
            else if (req_fire || !req_valid)
                req_wait_count <= 32'b0;

            if (pending && (rsp_wait_count != 0))
                rsp_wait_count <= rsp_wait_count - 32'd1;

            if (rsp_valid) begin
                pending <= 1'b0;
                rsp_wait_count <= 32'b0;
            end
            if (req_fire) begin
                pending <= 1'b1;
                rsp_wait_count <= RSP_DELAY_CYCLES;
                accepted_ram_addr <= req_addr[RAM_ADDR_WIDTH+1:2];
            end
        end
    end

    // BRAM 已由字节写使能表达访问宽度；保留 size 是为了让同一 CPU 接口
    // 后续能直接连接地址译码器、外设桥或 DDR3 桥。
    wire [1:0] _unused_req_size = req_size;

endmodule
