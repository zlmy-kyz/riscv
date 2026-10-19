`timescale 1ns / 1ps

// 将 CPU 的两个类 SRAM 请求/响应端口转换为紫光同创 DDR3 IP 的用户接口。
//
// 这个 DDR3 用户接口只是“AXI-like”，并不是标准 AXI4：
//   * 写通道没有 WVALID/B 通道，AW 命令接受后以 WREADY 表示数据拍被接受；
//   * 读通道没有 RREADY，RVALID 出现时本模块必须立即接收；
//   * x16/x32 DDR3 IP 的每个数据拍分别为 128/256 bit，CPU 为 32 bit。
//
// 本模块的事务策略：
//   * 最多保留一笔 DDR 事务；可选 x32 单条顺序写缓冲独立于前端响应槽；
//   * 只产生单拍访问（AWLEN/ARLEN = 0）；
//   * 输入地址是地址译码器减去 DDR_BASE 后的“DDR 局部字节地址”；
//   * 控制器地址按 MEM_DQ_WIDTH bit 字计数，每拍 8 字对齐；
//   * 字节地址的拍内位选择 32 bit 槽，缓存行大小等于一个用户数据拍。
//   * 指令缓存和数据读缓冲均为 64 行直接映射。
//   * x32 I/D 数据分别用 icache/dcache DRM 同步读，tag/valid 仍在逻辑中。
//     x16 保留数组实现；x32 I64/D64 各为 2 KiB。
//   * 读命中不发 DDR 命令；写仍直达 DDR，I 命中行在写接受时失效。
//   * x32 D 写命中在 DDR 写完成时按字节更新；写 miss 不分配。
//   * posted 模式 store 入缓冲即响应；下一写可在旧写完成边沿接续，读 miss 等排空。
//     D 命中读经一拍资格寄存后与旧写重叠；同行同字读按 mask 转发。
//     同行读不在缓存写完成边沿接受，避免依赖 DRM 的读写碰撞语义。
//     I 命中可继续，I miss 可先锁存但 AR 等排空；SoC 接 FENCE/IRQ 与非 DDR 排空。
//     x16 保留原数组和写命中失效策略。
//   * 旧响应周期可同时接受下一请求；同步 DRM 输出在接受边沿后才更新，
//     CPU 在该边沿仍消费旧响应。没有下一请求时回到 IDLE。
//   * x32 可在 D 读 miss 等待期间独立接受一笔 I 查询：命中直接响应，
//     miss 暂存至主槽空闲后再发 DDR 读；不增加物理 DDR 在途读数量。
//
// CPU 和本模块都应工作在 DDR3 IP 输出的 core_clk 域中。只有
// ddr_init_done=1 后才接受新请求。
module dual_sram_to_pango_ddr_bridge #(
    parameter integer CTRL_ADDR_WIDTH = 28,
    parameter integer MEM_DQ_WIDTH = 16,
    parameter integer INST_LINE_BUFFER_ENABLE = 1,
    parameter integer DATA_LINE_BUFFER_ENABLE = 1,
    parameter integer CAMERA_UNCACHED_ENABLE = 0,
    parameter integer PREPROCESS_UNCACHED_ENABLE = 0,
    // Default off for legacy direct instances; board x32 enables it in soc_top.
    parameter integer POSTED_WRITE_ENABLE = 0,
    parameter integer DATA_READ_UNDER_WRITE_ENABLE = 1,
    parameter integer DATA_STORE_FORWARD_ENABLE = 1,
    // Reuse the sole posted entry on its W completion edge; no extra queue slot.
    parameter integer WRITE_BUFFER_TURNOVER_ENABLE = 1,
    // Independent I lookup while a D read miss owns the shared DDR read slot.
    parameter integer INST_HIT_UNDER_DATA_MISS_ENABLE = 1
) (
    input  wire                          clk,
    input  wire                          resetn,
    input  wire                          ddr_init_done,
    output wire                          write_buffer_busy,

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
    output wire [8*MEM_DQ_WIDTH-1:0]     axi_wdata,
    output wire [MEM_DQ_WIDTH-1:0]       axi_wstrb,
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
    input  wire [8*MEM_DQ_WIDTH-1:0]     axi_rdata,
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
    // x32 I lookup: registered row hits resolve alongside synchronous DRM data.
    // Hit responds now; miss issues AR now, just as the former RSP/RADDR split.
    localparam [2:0] STATE_INST_LOOKUP = 3'd6;

    localparam TARGET_INST = 1'b0;
    localparam TARGET_DATA = 1'b1;
    // 本工程仅实例化 x16 或 x32；常量表达式兼容 PDS 的 Verilog-2001 前端。
    localparam integer BEAT_ADDR_BITS = (MEM_DQ_WIDTH == 32) ? 5 : 4;
    localparam integer BYTE_ADDR_SHIFT = (MEM_DQ_WIDTH == 32) ? 2 : 1;
    localparam integer LANE_BITS = BEAT_ADDR_BITS - 2;
    localparam integer TAG_BITS = 32 - BEAT_ADDR_BITS;
    localparam integer POSTED_WRITE_ACTIVE = (POSTED_WRITE_ENABLE != 0) && (MEM_DQ_WIDTH == 32);
    localparam integer INST_LOOKUP_ACTIVE = (MEM_DQ_WIDTH == 32) && (INST_LINE_BUFFER_ENABLE != 0);
    localparam integer INST_OVERLAP_ACTIVE = INST_LOOKUP_ACTIVE &&
                                             (INST_HIT_UNDER_DATA_MISS_ENABLE != 0);

    // One ordered store entry. No combining; hit loads may forward written bytes.
    reg write_buffer_valid;
    reg write_buffer_aw_sent;
    reg [CTRL_ADDR_WIDTH-1:0] write_buffer_ctrl_addr;
    reg [LANE_BITS-1:0] write_buffer_lane;
    reg [31:0] write_buffer_wdata;
    reg [3:0] write_buffer_wstrb;
    reg [TAG_BITS-1:0] write_buffer_line_tag;
    reg write_buffer_hit;
    wire write_buffer_push;
    wire write_buffer_complete;
    wire write_buffer_turnover_ready;
    wire [5:0] data_ram_write_index;
    reg data_read_overlap_permit;
    reg data_read_overlap_same_line;
    reg [31:0] response_forward_mask;
    reg [31:0] response_forward_data;
    wire [31:0] data_drm_with_forward;

    reg [2:0] state;
    reg       response_target;
    reg [CTRL_ADDR_WIDTH-1:0] request_ctrl_addr;
    reg [LANE_BITS-1:0] request_lane;
    reg [31:0] request_wdata;
    reg [3:0] request_wstrb;
    reg [31:0] response_rdata;
    reg        response_from_inst_drm;
    reg        response_from_data_drm;

    // 64 行直接映射指令缓存，完整局部行地址比较。
    // 主槽只保留一个 DDR 读；额外 I 查询 miss 先等待，不并发发 AR。
    reg [63:0]  inst_line_valid;
    reg [TAG_BITS-1:0] inst_line_tag [0:63];
    wire [31:0] inst_drm_rdata;
    wire [31:0] inst_legacy_rdata;
    reg [TAG_BITS-1:0] request_line_tag;
    wire [5:0]  inst_line_index;
    wire [5:0]  data_line_index;
    wire [5:0]  fill_line_index;
    integer     reset_line;
    wire        inst_line_hit;
    wire        inst_line_fill;
    wire        inst_line_write_hit;

    // 64 行数据读缓冲，完整局部行地址比较，无 dirty 状态。
    // CPU 所有 DDR 写仍经过原 AW/W 路径；x32 命中行按 strobe 更新。
    reg [63:0]  data_line_valid;
    reg [TAG_BITS-1:0] data_line_tag [0:63];
    wire [31:0] data_drm_rdata;
    wire [31:0] data_legacy_rdata;
    wire [5:0]  data_read_line_index;
    wire [5:0]  data_fill_line_index;
    integer     reset_data_line;
    wire        data_line_hit;
    wire        data_line_fill;
    wire        data_line_write_hit;
    reg         request_data_write_hit;
    wire        data_line_store;

    wire idle_ready;
    wire front_slot_available;
    wire inst_lookup_response;
    wire read_address_phase;
    wire take_data;
    wire take_inst;
    wire take_inst_front;
    wire take_inst_overlap;
    wire data_read_miss_busy;
    wire inst_overlap_response;
    wire inst_overlap_slot_ready;
    wire promote_inst_overlap;
    wire inst_tag_sample;
    reg inst_overlap_pending;
    reg [31:0] inst_overlap_addr;
    wire [31:0] selected_addr;
    wire [CTRL_ADDR_WIDTH-1:0] selected_ctrl_addr;

    // RSP 或 LOOKUP 命中表示旧事务已完成，可在旧响应消费边沿接续。
    // 主 DDR 事务槽仍数据优先；D miss 时的额外 I 查询不修改该槽。
    assign inst_lookup_response = INST_LOOKUP_ACTIVE &&
                                  (state == STATE_INST_LOOKUP) && inst_line_hit;
    assign front_slot_available = (state == STATE_IDLE) || (state == STATE_RSP) ||
                                  inst_lookup_response;
    assign idle_ready = front_slot_available && ddr_init_done;
    assign read_address_phase = (state == STATE_RADDR) ||
                                (INST_LOOKUP_ACTIVE && (state == STATE_INST_LOOKUP) &&
                                 !inst_line_hit);

    // 两端同时请求时先完成流水线中的 load/store，避免数据相关停顿继续扩大。
    // Hit eligibility/line relation are registered, keeping tag comparison off ready.
    // The requester holds valid/address/type until accepted; permit is consumed once.
    // Only stores reuse a completing entry. Loads keep the existing DRM collision guard.
    // Completion depends on the OLD AW/W fields, never on the incoming store.
    assign write_buffer_turnover_ready = (WRITE_BUFFER_TURNOVER_ENABLE != 0) &&
                                        data_req_write && write_buffer_complete;
    assign data_req_ready = idle_ready && (!write_buffer_busy ||
                             write_buffer_turnover_ready ||
                             (!data_req_write && data_read_overlap_permit &&
                              !(data_read_overlap_same_line && write_buffer_complete)));
    // The extra slot accepts a lookup, NOT a second DDR read. A hit returns
    // next cycle; a miss holds its address/verdict until the shared slot is free.
    // No live I-address/tag comparison enters ready. Do not extend this to
    // simultaneous store acceptance: I invalidation must precede a new lookup.
    assign data_read_miss_busy = INST_OVERLAP_ACTIVE && ddr_init_done &&
                                 (response_target == TARGET_DATA) &&
                                 ((state == STATE_RADDR) || (state == STATE_RDATA));
    assign inst_overlap_response = INST_OVERLAP_ACTIVE &&
                                    inst_overlap_pending && inst_line_hit;
    assign inst_overlap_slot_ready = !inst_overlap_pending || inst_overlap_response;
    assign inst_req_ready = ((idle_ready && !take_data) || data_read_miss_busy) &&
                             inst_overlap_slot_ready;
    assign take_data = data_req_valid && data_req_ready;
    assign take_inst = inst_req_valid && inst_req_ready;
    assign take_inst_front = take_inst && idle_ready;
    assign take_inst_overlap = take_inst && data_read_miss_busy;
    // A parked I miss cannot be bypassed by another I request. Data retains
    // the existing shared-slot priority; promotion uses the saved address only.
    assign promote_inst_overlap = idle_ready && !take_data &&
                                   inst_overlap_pending && !inst_line_hit;
    // Hold a parked miss verdict even if a new D request takes the main slot.
    // The I DRM is sampled on acceptance; its output is consumed one edge later.
    assign inst_tag_sample = (idle_ready || data_read_miss_busy) && inst_overlap_slot_ready;

    always @(posedge clk) begin
        if (!resetn) begin
            inst_overlap_pending <= 1'b0;
            inst_overlap_addr <= 32'b0;
        end else begin
            if (inst_overlap_response || promote_inst_overlap)
                inst_overlap_pending <= 1'b0;
            // New acceptance wins over consumption of the previous hit.
            if (take_inst_overlap) begin
                inst_overlap_pending <= 1'b1;
                inst_overlap_addr <= inst_req_addr;
            end
        end
    end

    assign inst_line_index = inst_req_addr[BEAT_ADDR_BITS+5:BEAT_ADDR_BITS];
    assign data_line_index = data_req_addr[BEAT_ADDR_BITS+5:BEAT_ADDR_BITS];
    assign fill_line_index = request_line_tag[5:0];
    generate
        if ((MEM_DQ_WIDTH == 32) && (INST_LINE_BUFFER_ENABLE != 0)) begin : g_inst_tag_parallel
            // Compare fixed rows in parallel, then register BEFORE the global
            // reduction. The late CPU load/branch address no longer traverses
            // both tag comparison and 64-row reduction into the state register.
            // A valid row's low six tag bits equal its fixed row index because
            // fills write request_line_tag at request_line_tag[5:0]. Compare
            // only the upper tag here and decode the index separately.
            // Preserve small compare/reduction boundaries so ADS cannot rebuild
            // wide carry comparisons or a monolithic 64-input reduction.
            wire [63:0] way_hit;
            reg [63:0] way_hit_q;
            (* syn_keep = 1 *) wire [15:0] hit_group;
            (* syn_keep = 1 *) wire [3:0] hit_quarter;
            genvar inst_tag_way;
            for (inst_tag_way = 0; inst_tag_way < 64; inst_tag_way = inst_tag_way + 1) begin : g_way
                localparam [5:0] ROW_INDEX = inst_tag_way;
                // Three tag bits plus three request bits fit a six-input LUT.
                (* syn_keep = 1 *) wire [6:0] tag_match_part;
                (* syn_keep = 1 *) wire tag_match_lo;
                (* syn_keep = 1 *) wire tag_match_hi;
                wire tag_match;
                genvar inst_tag_part;
                for (inst_tag_part = 0; inst_tag_part < 7; inst_tag_part = inst_tag_part + 1) begin : g_part
                    assign tag_match_part[inst_tag_part] =
                        (inst_line_tag[inst_tag_way][6 + inst_tag_part*3 +: 3] ==
                         inst_req_addr[BEAT_ADDR_BITS + 6 + inst_tag_part*3 +: 3]);
                end
                assign tag_match_lo = &tag_match_part[3:0];
                assign tag_match_hi = &tag_match_part[6:4];
                assign tag_match = tag_match_lo && tag_match_hi;
                assign way_hit[inst_tag_way] = inst_line_valid[inst_tag_way] &&
                                               (inst_line_index == ROW_INDEX) && tag_match;
            end
            // Sample with the synchronous DRM read. No request-valid/branch
            // qualifier on these register enables. Accepted I requests enter
            // either main LOOKUP or the independent overlap slot. Unaccepted
            // snapshots are ignored. A parked overlap miss holds its verdict
            // until promotion, regardless of live-address changes or D traffic.
            always @(posedge clk) begin
                if (!resetn)
                    way_hit_q <= 64'b0;
                else if (inst_tag_sample)
                    way_hit_q <= way_hit;
            end
            genvar inst_hit_group;
            for (inst_hit_group = 0; inst_hit_group < 16; inst_hit_group = inst_hit_group + 1) begin : g_hit_group
                assign hit_group[inst_hit_group] = |way_hit_q[inst_hit_group*4 +: 4];
            end
            genvar inst_hit_quarter;
            for (inst_hit_quarter = 0; inst_hit_quarter < 4; inst_hit_quarter = inst_hit_quarter + 1) begin : g_hit_quarter
                assign hit_quarter[inst_hit_quarter] = |hit_group[inst_hit_quarter*4 +: 4];
            end
            assign inst_line_hit = |hit_quarter;
        end else begin : g_inst_tag_legacy
            assign inst_line_hit = (INST_LINE_BUFFER_ENABLE != 0) &&
                                   inst_line_valid[inst_line_index] &&
                                   (inst_line_tag[inst_line_index] == inst_req_addr[31:BEAT_ADDR_BITS]);
        end
    endgenerate
    // 比较完整 DDR 局部行地址；同一行的 SB/SH/SW（包括零 strobe）均失效。
    // 不同数据行的写不修改缓存拍，减少无关 store 后的重复取指读取。
    assign inst_line_write_hit = take_data && data_req_write &&
                                 inst_line_valid[data_line_index] &&
                                 (inst_line_tag[data_line_index] == data_req_addr[31:BEAT_ADDR_BITS]);
    // RREADY 不存在，沿用原 FSM 接收时机，包括 AR 接受同拍返回。
    // 旁带不改变原 CPU error 语义；不完整/身份异常的拍不留作后续命中。
    assign inst_line_fill = (INST_LINE_BUFFER_ENABLE != 0) &&
                            (response_target == TARGET_INST) &&
                            axi_rvalid && (axi_rid == 4'd0) && axi_rlast &&
                            ((state == STATE_RDATA) ||
                             (read_address_phase && axi_arvalid && axi_arready));

    generate
        if ((MEM_DQ_WIDTH == 32) && (INST_LINE_BUFFER_ENABLE != 0)) begin : g_inst_drm
            // IP 配置：64x256 写 / 512x32 同步读，无额外输出寄存器。
            // 使用全部 64 行：写地址 index[5:0]，读地址 index[5:0]:word[2:0]。
            // 接受边沿同时采样读地址和逐行命中，LOOKUP 命中周期直接使用 IP 输出。
            // 读地址即使随后变化，也不会在下一个时钟边沿前改变此响应。
            icache u_inst_data_ram (
                .wr_data(axi_rdata),
                .wr_addr(fill_line_index),
                .wr_en(resetn && ddr_init_done && inst_line_fill),
                .wr_clk(clk),
                .wr_rst(!resetn),
                .rd_addr(inst_req_addr[10:2]),
                .rd_data(inst_drm_rdata),
                .rd_clk(clk),
                .rd_rst(!resetn)
            );
            assign inst_legacy_rdata = 32'b0;
        end else begin : g_inst_legacy
            // 历史 x16 仿真/配置沿用原数组与响应寄存器路径。
            reg [8*MEM_DQ_WIDTH-1:0] inst_line_data [0:63];
            integer reset_inst_data;
            always @(posedge clk) begin
                if (!resetn) begin
                    for (reset_inst_data = 0; reset_inst_data < 64; reset_inst_data = reset_inst_data + 1)
                        inst_line_data[reset_inst_data] <= {(8*MEM_DQ_WIDTH){1'b0}};
                end else if (ddr_init_done && inst_line_fill) begin
                    inst_line_data[fill_line_index] <= axi_rdata;
                end
            end
            assign inst_legacy_rdata =
                inst_line_data[inst_line_index][inst_req_addr[BEAT_ADDR_BITS-1:2] * 32 +: 32];
            assign inst_drm_rdata = 32'b0;
        end
    endgenerate

    assign data_read_line_index = data_req_addr[BEAT_ADDR_BITS+5:BEAT_ADDR_BITS];
    assign data_fill_line_index = request_line_tag[5:0];
    wire preprocess_data_addr=(PREPROCESS_UNCACHED_ENABLE!=0) && data_req_addr[31:16]==16'h0200;
    wire preprocess_fill_addr=(PREPROCESS_UNCACHED_ENABLE!=0) &&
                              (request_line_tag >> (16-BEAT_ADDR_BITS))==16'h0200;
    wire camera_data_addr=(CAMERA_UNCACHED_ENABLE!=0) &&
                          (data_req_addr[31:22]==(32'h01000000 >> 22));
    wire camera_fill_addr=(CAMERA_UNCACHED_ENABLE!=0) &&
                          ((request_line_tag >> (22-BEAT_ADDR_BITS))==(32'h01000000 >> 22));
    assign data_line_hit = (DATA_LINE_BUFFER_ENABLE != 0) && !camera_data_addr && !preprocess_data_addr &&
                           !data_req_write && data_line_valid[data_read_line_index] &&
                           (data_line_tag[data_read_line_index] == data_req_addr[31:BEAT_ADDR_BITS]);
    always @(posedge clk) begin
        if (!resetn || !ddr_init_done || !write_buffer_busy || take_data ||
            !data_req_valid || data_req_write) begin
            data_read_overlap_permit <= 1'b0;
            data_read_overlap_same_line <= 1'b0;
        end else begin
            data_read_overlap_permit <= POSTED_WRITE_ACTIVE &&
                (DATA_READ_UNDER_WRITE_ENABLE != 0) && data_line_hit &&
                ((DATA_STORE_FORWARD_ENABLE != 0) ||
                 (data_req_addr[31:BEAT_ADDR_BITS] != write_buffer_line_tag));
            data_read_overlap_same_line <=
                (data_req_addr[31:BEAT_ADDR_BITS] == write_buffer_line_tag);
        end
    end
    assign data_line_write_hit = take_data && data_req_write && !camera_data_addr && !preprocess_data_addr &&
                                 data_line_valid[data_read_line_index] &&
                                 (data_line_tag[data_read_line_index] == data_req_addr[31:BEAT_ADDR_BITS]);
    assign data_line_fill = (DATA_LINE_BUFFER_ENABLE != 0) && !camera_fill_addr && !preprocess_fill_addr &&
                            (response_target == TARGET_DATA) &&
                            axi_rvalid && (axi_rid == 4'd1) && axi_rlast &&
                            ((state == STATE_RDATA) ||
                             ((state == STATE_RADDR) && axi_arvalid && axi_arready));

    // D RAM 仍只在实际单拍写完成边沿更新。
    // Posted 模式使用独立写缓冲字段，取指不能覆盖写地址/行/槽/数据。
    assign data_line_store = resetn && ddr_init_done &&
                             (MEM_DQ_WIDTH == 32) &&
                             (DATA_LINE_BUFFER_ENABLE != 0) &&
                             (POSTED_WRITE_ACTIVE ?
                              (write_buffer_complete && write_buffer_hit &&
                               data_line_valid[write_buffer_line_tag[5:0]] &&
                               data_line_tag[write_buffer_line_tag[5:0]] == write_buffer_line_tag) :
                              (request_data_write_hit &&
                               (((state == STATE_WADDR) && axi_awready && axi_wready) ||
                                ((state == STATE_WDATA) && axi_wready))));
    assign data_ram_write_index = (POSTED_WRITE_ACTIVE && data_line_store) ?
                                   write_buffer_line_tag[5:0] : data_fill_line_index;

    generate
        if ((MEM_DQ_WIDTH == 32) && (DATA_LINE_BUFFER_ENABLE != 0)) begin : g_data_drm
            // D64 使用全部 64 行及 512 个 word，写端新增 32 个字节使能。
            // 命中接受边沿采样读地址；RSP 周期选同步 RAM 输出，不再二次寄存。
            // 填充写全拍；store 命中只更新指定字节，无 read-modify-write。
            dcache u_data_data_ram (
                .wr_data(data_line_fill ? axi_rdata : axi_wdata),
                .wr_addr(data_ram_write_index),
                .wr_en(resetn && ddr_init_done && (data_line_fill || data_line_store)),
                .wr_clk(clk),
                .wr_rst(!resetn),
                .wr_byte_en(data_line_fill ? 32'hffff_ffff : axi_wstrb),
                .rd_addr(data_req_addr[10:2]),
                .rd_data(data_drm_rdata),
                .rd_clk(clk),
                .rd_rst(!resetn)
            );
            assign data_legacy_rdata = 32'b0;
        end else begin : g_data_legacy
            reg [8*MEM_DQ_WIDTH-1:0] data_line_data [0:63];
            integer reset_data_array;
            always @(posedge clk) begin
                if (!resetn) begin
                    for (reset_data_array = 0; reset_data_array < 64; reset_data_array = reset_data_array + 1)
                        data_line_data[reset_data_array] <= {(8*MEM_DQ_WIDTH){1'b0}};
                end else if (ddr_init_done && data_line_fill) begin
                    data_line_data[data_fill_line_index] <= axi_rdata;
                end
            end
            assign data_legacy_rdata =
                data_line_data[data_read_line_index][data_req_addr[BEAT_ADDR_BITS-1:2] * 32 +: 32];
            assign data_drm_rdata = 32'b0;
        end
    endgenerate

    // x32 D 写命中保留 valid/tag；同行读接受边沿避开缓存写完成边沿。
    // 命中读不填充，不能改变写条的命中元数据。
    // I-Cache 仍独立失效；x16 D 保留原失效行为。
    always @(posedge clk) begin
        if (!resetn) begin
            data_line_valid <= 64'b0;
            for (reset_data_line = 0; reset_data_line < 64; reset_data_line = reset_data_line + 1) begin
                data_line_tag[reset_data_line]  <= {TAG_BITS{1'b0}};
            end
        end else if (!ddr_init_done) begin
            data_line_valid <= 64'b0;
        end else if ((MEM_DQ_WIDTH != 32) && data_line_write_hit) begin
            // 同行部分/零 strobe 写均保守失效；旁路 DMA 须另接一致性协议。
            data_line_valid[data_read_line_index] <= 1'b0;
        end else if (data_line_fill) begin
            data_line_valid[data_fill_line_index] <= 1'b1;
            data_line_tag[data_fill_line_index]   <= request_line_tag;
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            inst_line_valid <= 64'b0;
            for (reset_line = 0; reset_line < 64; reset_line = reset_line + 1) begin
                inst_line_tag[reset_line]  <= {TAG_BITS{1'b0}};
            end
        end else if (!ddr_init_done) begin
            inst_line_valid <= 64'b0;
        end else if (inst_line_write_hit) begin
            // 当前没有 DMA；未来其他 DDR 写主机必须另接失效/一致性协议。
            // 单事务串行化保证写接受与读填充不会同时发生，失效仍优先。
            inst_line_valid[data_line_index] <= 1'b0;
        end else if (inst_line_fill) begin
            inst_line_valid[fill_line_index] <= 1'b1;
            inst_line_tag[fill_line_index]   <= request_line_tag;
        end
    end

    assign selected_addr = take_data ? data_req_addr : inst_req_addr;

    // DDR 地址单位随物理 DQ 宽度变化。每拍含 8 个地址单位，低 3 bit 清零。
    assign selected_ctrl_addr =
        {selected_addr[CTRL_ADDR_WIDTH+BYTE_ADDR_SHIFT-1:BEAT_ADDR_BITS], 3'b000};

    assign axi_awaddr    = POSTED_WRITE_ACTIVE ? write_buffer_ctrl_addr : request_ctrl_addr;
    assign axi_awuser_ap = 1'b0;
    assign axi_awuser_id = 4'd1;
    assign axi_awlen     = 4'd0;
    assign axi_awvalid   = POSTED_WRITE_ACTIVE ?
                           (write_buffer_valid && !write_buffer_aw_sent && ddr_init_done) :
                           (state == STATE_WADDR);

    // CPU 已经依据 addr[1:0] 将字节/半字数据和 strobe 放到正确的 32 bit
    // 字节位置；这里再把整个 32 bit 字移动到对应的用户拍内槽。
    assign axi_wdata = POSTED_WRITE_ACTIVE ?
                       ({{(8*MEM_DQ_WIDTH-32){1'b0}}, write_buffer_wdata} << (write_buffer_lane * 32)) :
                       ({{(8*MEM_DQ_WIDTH-32){1'b0}}, request_wdata} << (request_lane * 32));
    assign axi_wstrb = POSTED_WRITE_ACTIVE ?
                       ({{(MEM_DQ_WIDTH-4){1'b0}}, write_buffer_wstrb} << (write_buffer_lane * 4)) :
                       ({{(MEM_DQ_WIDTH-4){1'b0}}, request_wstrb} << (request_lane * 4));

    assign axi_araddr    = request_ctrl_addr;
    assign axi_aruser_ap = 1'b0;
    assign axi_aruser_id = (response_target == TARGET_DATA) ? 4'd1 : 4'd0;
    assign axi_arlen     = 4'd0;
    assign axi_arvalid   = read_address_phase && !write_buffer_busy;

    // An overlap hit may return together with the main D response. The main
    // slot cannot own an I response while an overlap request remains pending.
    assign inst_rsp_valid = inst_overlap_response ||
                            (((state == STATE_RSP) || inst_lookup_response) &&
                             (response_target == TARGET_INST));
    // Preselect DRM for the whole overlap slot, including invalid miss cycles;
    // keep the registered 64-row hit reduction out of the data mux select.
    assign inst_rsp_rdata = (inst_overlap_pending || response_from_inst_drm) ?
                            inst_drm_rdata : response_rdata;
    assign inst_rsp_error = 1'b0;

    assign data_rsp_valid = (state == STATE_RSP) &&
                            (response_target == TARGET_DATA);
    // Forward fields belong to this response, not to the live/draining write entry.
    assign data_drm_with_forward = (data_drm_rdata & ~response_forward_mask) |
                                  (response_forward_data & response_forward_mask);
    assign data_rsp_rdata = response_from_data_drm ? data_drm_with_forward : response_rdata;
    assign data_rsp_error = 1'b0;

    assign write_buffer_busy = POSTED_WRITE_ACTIVE && write_buffer_valid;
    assign write_buffer_push = POSTED_WRITE_ACTIVE && take_data && data_req_write;
    // WREADY is meaningful only after AW acceptance or on its acceptance edge.
    assign write_buffer_complete = POSTED_WRITE_ACTIVE && resetn && ddr_init_done &&
                                    write_buffer_valid && axi_wready &&
                                    (write_buffer_aw_sent || axi_awready);
    always @(posedge clk) begin
        if (!resetn) begin
            write_buffer_valid <= 1'b0;
            write_buffer_aw_sent <= 1'b0;
            write_buffer_ctrl_addr <= {CTRL_ADDR_WIDTH{1'b0}};
            write_buffer_lane <= {LANE_BITS{1'b0}};
            write_buffer_wdata <= 32'b0;
            write_buffer_wstrb <= 4'b0;
            write_buffer_line_tag <= {TAG_BITS{1'b0}};
            write_buffer_hit <= 1'b0;
        end else if (POSTED_WRITE_ACTIVE) begin
            // init loss pauses the entry; SoC reset cancels it. Never reissue accepted AW.
            if (write_buffer_complete) begin
                write_buffer_valid <= 1'b0;
                write_buffer_aw_sent <= 1'b0;
            end else if (axi_awvalid && axi_awready) begin
                write_buffer_aw_sent <= 1'b1;
            end
            // Push wins over completion: old data updates D RAM at this edge,
            // then the new entry owns AW/W and must obtain its own AW acceptance.
            if (write_buffer_push) begin
                write_buffer_valid <= 1'b1;
                write_buffer_aw_sent <= 1'b0;
                write_buffer_ctrl_addr <= selected_ctrl_addr;
                write_buffer_lane <= data_req_addr[BEAT_ADDR_BITS-1:2];
                write_buffer_wdata <= data_req_wdata;
                write_buffer_wstrb <= data_req_wstrb;
                write_buffer_line_tag <= data_req_addr[31:BEAT_ADDR_BITS];
                write_buffer_hit <= data_line_write_hit;
            end
        end
    end

    always @(posedge clk) begin
        if (!resetn) begin
            state             <= STATE_IDLE;
            response_target   <= TARGET_INST;
            request_ctrl_addr <= {CTRL_ADDR_WIDTH{1'b0}};
            request_lane      <= {LANE_BITS{1'b0}};
            request_wdata     <= 32'b0;
            request_wstrb     <= 4'b0;
            response_rdata    <= 32'b0;
            response_from_inst_drm <= 1'b0;
            response_from_data_drm <= 1'b0;
            response_forward_mask <= 32'b0;
            response_forward_data <= 32'b0;
            request_line_tag <= {TAG_BITS{1'b0}};
            request_data_write_hit <= 1'b0;
        end else begin
            if (front_slot_available) begin
                // x32 cache hits respond directly from the synchronous DRM.
                // Clear the unused fallback here, without request/tag gating:
                // D-DRM -> ID branch -> I-tag must not drive this register's CE.
                // A miss captures DDR data later in RADDR/RDATA as before.
                if (MEM_DQ_WIDTH == 32)
                    response_rdata <= 32'b0;
                // 默认清旧响应来源；若接受新命中，下方重新置位。
                response_from_inst_drm <= 1'b0;
                response_from_data_drm <= 1'b0;
                response_forward_mask <= 32'b0;
                response_forward_data <= 32'b0;
                state <= STATE_IDLE;
                if (take_data) begin
                    response_from_inst_drm <= 1'b0;
                    response_from_data_drm <= (MEM_DQ_WIDTH == 32) && data_line_hit;
                    if ((DATA_STORE_FORWARD_ENABLE != 0) && write_buffer_busy &&
                        data_line_hit &&
                        (data_req_addr[31:BEAT_ADDR_BITS] == write_buffer_line_tag) &&
                        (data_req_addr[BEAT_ADDR_BITS-1:2] == write_buffer_lane)) begin
                        response_forward_mask <= {{8{write_buffer_wstrb[3]}},
                            {8{write_buffer_wstrb[2]}}, {8{write_buffer_wstrb[1]}},
                            {8{write_buffer_wstrb[0]}}};
                        response_forward_data <= write_buffer_wdata;
                    end
                    response_target   <= TARGET_DATA;
                    request_ctrl_addr <= selected_ctrl_addr;
                    request_lane      <= selected_addr[BEAT_ADDR_BITS-1:2];
                    request_wdata     <= data_req_wdata;
                    request_wstrb     <= data_req_wstrb;
                    if (MEM_DQ_WIDTH != 32)
                        response_rdata <= 32'b0;
                    request_line_tag  <= data_req_addr[31:BEAT_ADDR_BITS];
                    request_data_write_hit <= data_line_write_hit;
                    if (data_req_write) begin
                        // Response confirms ordered entry ownership, not DDR completion.
                        state <= POSTED_WRITE_ACTIVE ? STATE_RSP : STATE_WADDR;
                    end else if (data_line_hit) begin
                        if (MEM_DQ_WIDTH != 32)
                            response_rdata <= data_legacy_rdata;
                        state <= STATE_RSP;
                    end else begin
                        state <= STATE_RADDR;
                    end
                end else if (promote_inst_overlap) begin
                    // The independent lookup already proved miss. Promote only
                    // AFTER the old D response; never clobber an outstanding R.
                    // AR still obeys the original posted-write drain gate.
                    response_from_inst_drm <= 1'b0;
                    response_from_data_drm <= 1'b0;
                    response_target <= TARGET_INST;
                    request_ctrl_addr <=
                        {inst_overlap_addr[CTRL_ADDR_WIDTH+BYTE_ADDR_SHIFT-1:BEAT_ADDR_BITS], 3'b000};
                    request_lane <= inst_overlap_addr[BEAT_ADDR_BITS-1:2];
                    request_line_tag <= inst_overlap_addr[31:BEAT_ADDR_BITS];
                    request_wdata <= 32'b0;
                    request_wstrb <= 4'b0;
                    request_data_write_hit <= 1'b0;
                    state <= STATE_RADDR;
                end else if (take_inst_front) begin
                    // Preselect x32 DRM without putting the I-tag compare
                    // on this response selector's D input. A miss has no
                    // valid response here and clears it in the miss address phase.
                    response_from_inst_drm <= (MEM_DQ_WIDTH == 32);
                    response_from_data_drm <= 1'b0;
                    response_target   <= TARGET_INST;
                    request_ctrl_addr <= selected_ctrl_addr;
                    request_lane      <= selected_addr[BEAT_ADDR_BITS-1:2];
                    request_wdata     <= 32'b0;
                    request_wstrb     <= 4'b0;
                    request_line_tag  <= inst_req_addr[31:BEAT_ADDR_BITS];
                    request_data_write_hit <= 1'b0;
                    if (INST_LOOKUP_ACTIVE) begin
                        // Do not decide hit/miss from the live request here.
                        // Next cycle's registered verdict selects response
                        // or AR, preserving both original external timings.
                        state <= STATE_INST_LOOKUP;
                    end else if (inst_line_hit) begin
                        if (MEM_DQ_WIDTH != 32)
                            response_rdata <= inst_legacy_rdata;
                        state <= STATE_RSP;
                    end else begin
                        state <= STATE_RADDR;
                    end
                end
            end else begin
                case (state)
                    STATE_INST_LOOKUP, STATE_RADDR: begin
                        // Misses return the captured DDR beat, including an R beat
                        // arriving on the AR acceptance edge. Clear before RSP;
                        // LOOKUP hits use the front-slot branch above. LOOKUP misses
                        // can accept AR and R here without an extra lookup bubble.
                        response_from_inst_drm <= 1'b0;
                        state <= STATE_RADDR;
                        if (axi_arvalid && axi_arready) begin
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

                    default: begin
                        state <= STATE_IDLE;
                    end
                endcase
            end
        end
    end

    // 首版不根据这些返回旁带信号产生 CPU fault：Pango 用户口没有标准
    // AXI BRESP/RRESP。保留端口，后续加入多笔 outstanding 时用 ID/last 校验。
    wire [11:0] _unused_sideband = {data_req_size, axi_wusero_id,
                                    axi_wusero_last, axi_rid, axi_rlast};

endmodule
