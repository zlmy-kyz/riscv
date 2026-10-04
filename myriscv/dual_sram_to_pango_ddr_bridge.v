`timescale 1ns / 1ps

// 将 CPU 的两个类 SRAM 请求/响应端口转换为紫光同创 DDR3 IP 的用户接口。
//
// 这个 DDR3 用户接口只是“AXI-like”，并不是标准 AXI4：
//   * 写通道没有 WVALID/B 通道，AW 命令接受后以 WREADY 表示数据拍被接受；
//   * 读通道没有 RREADY，RVALID 出现时本模块必须立即接收；
//   * 当前 x16 DDR3 IP 的每个数据拍是 128 bit，而 CPU 是 32 bit。
//
// 本模块的首版策略：
//   * 最多保留一笔 DDR 事务，数据端口优先于指令端口；
//   * 只产生单拍访问（AWLEN/ARLEN = 0）；
//   * 输入地址是地址译码器减去 DDR_BASE 后的“DDR 局部字节地址”；
//   * DDR 控制器地址按 16 bit 字计数，且 128 bit 数据拍按 8 字对齐；
//   * addr[3:2] 选择 128 bit 返回数据中的一个 32 bit 槽。
//
// CPU 和本模块都应工作在 DDR3 IP 输出的 core_clk 域中。只有
// ddr_init_done=1 后才接受新请求。
module dual_sram_to_pango_ddr_bridge #(
    parameter integer CTRL_ADDR_WIDTH = 28
) (
    input  wire                          clk,
    input  wire                          resetn,
    input  wire                          ddr_init_done,

    // 指令类 SRAM 端口，只读。
    input  wire                          inst_req_valid,
    input  wire [31:0]                   inst_req_addr,
    output wire                          inst_req_ready,
    output wire                          inst_rsp_valid,
    output wire [31:0]                   inst_rsp_rdata,
    output wire                          inst_rsp_error,

    // 数据类 SRAM 端口。
    input  wire                          data_req_valid,
    input  wire                          data_req_write,
    input  wire [1:0]                    data_req_size,
    input  wire [31:0]                   data_req_addr,
    input  wire [31:0]                   data_req_wdata,
    input  wire [3:0]                    data_req_wstrb,
    output wire                          data_req_ready,
    output wire                          data_rsp_valid,
    output wire [31:0]                   data_rsp_rdata,
    output wire                          data_rsp_error,

    // Pango DDR3 写地址/写数据用户接口。
    output wire [CTRL_ADDR_WIDTH-1:0]    axi_awaddr,
    output wire                          axi_awuser_ap,
    output wire [3:0]                    axi_awuser_id,
    output wire [3:0]                    axi_awlen,
    input  wire                          axi_awready,
    output wire                          axi_awvalid,
    output wire [127:0]                  axi_wdata,
    output wire [15:0]                   axi_wstrb,
    input  wire                          axi_wready,
    input  wire [3:0]                    axi_wusero_id,
    input  wire                          axi_wusero_last,

    // Pango DDR3 读地址/读数据用户接口。
    output wire [CTRL_ADDR_WIDTH-1:0]    axi_araddr,
    output wire                          axi_aruser_ap,
    output wire [3:0]                    axi_aruser_id,
    output wire [3:0]                    axi_arlen,
    input  wire                          axi_arready,
    output wire                          axi_arvalid,
    input  wire [127:0]                  axi_rdata,
    input  wire [3:0]                    axi_rid,
    input  wire                          axi_rlast,
    input  wire                          axi_rvalid
);

    localparam [2:0] STATE_IDLE   = 3'd0;
    localparam [2:0] STATE_RADDR  = 3'd1;
    localparam [2:0] STATE_RDATA  = 3'd2;
    localparam [2:0] STATE_WADDR  = 3'd3;
    localparam [2:0] STATE_WDATA  = 3'd4;
    localparam [2:0] STATE_RSP    = 3'd5;

    localparam TARGET_INST = 1'b0;
    localparam TARGET_DATA = 1'b1;

    reg [2:0] state;
    reg       response_target;
    reg [CTRL_ADDR_WIDTH-1:0] request_ctrl_addr;
    reg [1:0] request_lane;
    reg [31:0] request_wdata;
    reg [3:0] request_wstrb;
    reg [31:0] response_rdata;

    wire idle_ready;
    wire take_data;
    wire take_inst;
    wire [31:0] selected_addr;
    wire [CTRL_ADDR_WIDTH-1:0] selected_ctrl_addr;

    assign idle_ready = (state == STATE_IDLE) && ddr_init_done;

    // 两端同时请求时先完成流水线中的 load/store，避免数据相关停顿继续扩大。
    assign data_req_ready = idle_ready;
    assign inst_req_ready = idle_ready && !data_req_valid;
    assign take_data = data_req_valid && data_req_ready;
    assign take_inst = inst_req_valid && inst_req_ready;

    assign selected_addr = take_data ? data_req_addr : inst_req_addr;

    // DDR 地址单位是 16 bit 字。一个用户数据拍含 8 个半字，所以命令地址
    // 的低 3 bit 清零；CPU 字节地址 [3:2] 留作拍内 32 bit 槽选择。
    assign selected_ctrl_addr =
        {selected_addr[CTRL_ADDR_WIDTH:4], 3'b000};

    assign axi_awaddr    = request_ctrl_addr;
    assign axi_awuser_ap = 1'b0;
    assign axi_awuser_id = 4'd1;
    assign axi_awlen     = 4'd0;
    assign axi_awvalid   = (state == STATE_WADDR);

    // CPU 已经依据 addr[1:0] 将字节/半字数据和 strobe 放到正确的 32 bit
    // 字节位置；这里再把整个 32 bit 字移动到 128 bit 拍内对应的槽。
    assign axi_wdata = {96'b0, request_wdata} <<
                       {request_lane, 5'b00000};
    assign axi_wstrb = {12'b0, request_wstrb} <<
                       {request_lane, 2'b00};

    assign axi_araddr    = request_ctrl_addr;
    assign axi_aruser_ap = 1'b0;
    assign axi_aruser_id = (response_target == TARGET_DATA) ? 4'd1 : 4'd0;
    assign axi_arlen     = 4'd0;
    assign axi_arvalid   = (state == STATE_RADDR);

    assign inst_rsp_valid = (state == STATE_RSP) &&
                            (response_target == TARGET_INST);
    assign inst_rsp_rdata = response_rdata;
    assign inst_rsp_error = 1'b0;

    assign data_rsp_valid = (state == STATE_RSP) &&
                            (response_target == TARGET_DATA);
    assign data_rsp_rdata = response_rdata;
    assign data_rsp_error = 1'b0;

    always @(posedge clk) begin
        if (!resetn) begin
            state             <= STATE_IDLE;
            response_target   <= TARGET_INST;
            request_ctrl_addr <= {CTRL_ADDR_WIDTH{1'b0}};
            request_lane      <= 2'b0;
            request_wdata     <= 32'b0;
            request_wstrb     <= 4'b0;
            response_rdata    <= 32'b0;
        end else begin
            case (state)
                STATE_IDLE: begin
                    if (take_data) begin
                        response_target   <= TARGET_DATA;
                        request_ctrl_addr <= selected_ctrl_addr;
                        request_lane      <= selected_addr[3:2];
                        request_wdata     <= data_req_wdata;
                        request_wstrb     <= data_req_wstrb;
                        response_rdata    <= 32'b0;
                        state <= data_req_write ? STATE_WADDR : STATE_RADDR;
                    end else if (take_inst) begin
                        response_target   <= TARGET_INST;
                        request_ctrl_addr <= selected_ctrl_addr;
                        request_lane      <= selected_addr[3:2];
                        request_wdata     <= 32'b0;
                        request_wstrb     <= 4'b0;
                        state             <= STATE_RADDR;
                    end
                end

                STATE_RADDR: begin
                    if (axi_arready) begin
                        // 接口没有 RREADY；兼容命令握手同拍就返回数据的实现。
                        if (axi_rvalid) begin
                            response_rdata <=
                                axi_rdata[request_lane * 32 +: 32];
                            state <= STATE_RSP;
                        end else begin
                            state <= STATE_RDATA;
                        end
                    end
                end

                STATE_RDATA: begin
                    if (axi_rvalid) begin
                        response_rdata <=
                            axi_rdata[request_lane * 32 +: 32];
                        state <= STATE_RSP;
                    end
                end

                STATE_WADDR: begin
                    if (axi_awready) begin
                        // 没有 WVALID：数据和 strobe 从发 AW 前一直保持稳定。
                        // 对单拍写，第一次 WREADY 就表示数据拍已经被控制器接受。
                        if (axi_wready)
                            state <= STATE_RSP;
                        else
                            state <= STATE_WDATA;
                    end
                end

                STATE_WDATA: begin
                    if (axi_wready)
                        state <= STATE_RSP;
                end

                STATE_RSP: begin
                    state <= STATE_IDLE;
                end

                default: begin
                    state <= STATE_IDLE;
                end
            endcase
        end
    end

    // 首版不根据这些返回旁带信号产生 CPU fault：Pango 用户口没有标准
    // AXI BRESP/RRESP。保留端口，后续加入多笔 outstanding 时用 ID/last 校验。
    wire [11:0] _unused_sideband = {data_req_size, axi_wusero_id,
                                    axi_wusero_last, axi_rid, axi_rlast};

endmodule
