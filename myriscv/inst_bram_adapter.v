`timescale 1ns / 1ps

// 只读指令总线到同步 ROM 的适配器。
// 允许在 rsp_valid 当拍接受下一请求，因此 ROM 一拍响应时可连续取指；
// 任意额外等待周期由两个参数提供，主要用于验证前端停顿与重定向处理。
module inst_bram_adapter #(
    parameter integer ROM_ADDR_WIDTH = 12,
    parameter integer REQ_STALL_CYCLES = 0,
    parameter integer RSP_DELAY_CYCLES = 0
) (
    input  wire                      clk,
    input  wire                      resetn,

    input  wire                      req_valid,
    input  wire [31:0]               req_addr,
    output wire                      req_ready,

    output wire                      rsp_valid,
    output wire [31:0]               rsp_rdata,
    output wire                      rsp_error,

    output wire [ROM_ADDR_WIDTH-1:0] rom_addr,
    input  wire [31:0]               rom_rdata
);

    reg pending;
    reg [31:0] req_wait_count;
    reg [31:0] rsp_wait_count;
    reg [ROM_ADDR_WIDTH-1:0] accepted_rom_addr;
    wire req_fire;

    assign rsp_valid = pending && (rsp_wait_count == 0);

    // rsp_valid 没有反压：响应会在本拍被 CPU 接收，因此可以在同一个时钟沿
    // 把下一地址交给 ROM，保持一拍 ROM 的连续吞吐率。
    assign req_ready = (!pending || rsp_valid) &&
                       ((REQ_STALL_CYCLES == 0) ||
                        (req_wait_count >= REQ_STALL_CYCLES));
    assign req_fire = req_valid && req_ready;

    assign rsp_rdata = rom_rdata;
    assign rsp_error = 1'b0;
    assign rom_addr = req_fire ? req_addr[ROM_ADDR_WIDTH+1:2] :
                      pending  ? accepted_rom_addr :
                                 req_addr[ROM_ADDR_WIDTH+1:2];

    always @(posedge clk) begin
        if (!resetn) begin
            pending <= 1'b0;
            req_wait_count <= 32'b0;
            rsp_wait_count <= 32'b0;
            accepted_rom_addr <= {ROM_ADDR_WIDTH{1'b0}};
        end else begin
            if ((!pending || rsp_valid) && req_valid && !req_ready)
                req_wait_count <= req_wait_count + 32'd1;
            else if (req_fire || !req_valid)
                req_wait_count <= 32'b0;

            if (pending && !rsp_valid && (rsp_wait_count != 0))
                rsp_wait_count <= rsp_wait_count - 32'd1;

            if (rsp_valid) begin
                pending <= 1'b0;
                rsp_wait_count <= 32'b0;
            end

            if (req_fire) begin
                pending <= 1'b1;
                rsp_wait_count <= RSP_DELAY_CYCLES;
                accepted_rom_addr <= req_addr[ROM_ADDR_WIDTH+1:2];
            end
        end
    end

endmodule
