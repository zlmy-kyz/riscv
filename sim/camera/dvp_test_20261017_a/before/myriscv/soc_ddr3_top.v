`timescale 1ns / 1ps

// MINI-(200H) x32 / 8Gb DDR3 集成顶层。ddr_ref_clk 是已缓冲的单端参考时钟。
// 当前生成 DDR3 IP 使用 125 MHz 参考时钟、750 Mbps；core_clk 为 93.75 MHz。
// CORE_CLK_HZ 默认值保留仿真接口兼容，board_top 按实际 core_clk 覆写。
module soc_ddr3_top #(
    parameter integer ENABLE_CNN = 0,
    parameter integer ENABLE_PREPROCESS = 0,
    parameter integer ENABLE_CAMERA = 0,
    parameter integer CAMERA_COLORBAR_ENABLE = 0,
    parameter [31:0] RESET_PC = 32'h0000_0000,
    parameter [31:0] DDR_BASE = 32'h4000_0000,
    parameter integer CORE_CLK_HZ = 100_000_000,
    parameter integer SELFTEST_TIMEOUT_CYCLES = CORE_CLK_HZ * 5
) (
    input wire camera_pclk, camera_vsync, camera_href,
    input wire [7:0] camera_data,
    inout wire camera_scl, camera_sda,
    output wire camera_resetn,
    input  wire        ddr_ref_clk,
    input  wire        resetn,
    input  wire        irq_external,
    input  wire        irq_software,
    input  wire        irq_timer,
    output wire        core_clk,
    output wire        ddr_init_done,
    output wire        soc_resetn,
    output wire [31:0] debug_wb_pc,
    output wire [ 3:0] debug_wb_rf_we,
    output wire [ 4:0] debug_wb_rf_wnum,
    output wire [31:0] debug_wb_rf_wdata,
    output wire [31:0] debug_inst,
    output wire        mem_cs_n,
    output wire        mem_rst_n,
    output wire        mem_ck,
    output wire        mem_ck_n,
    output wire        mem_cke,
    output wire        mem_ras_n,
    output wire        mem_cas_n,
    output wire        mem_we_n,
    output wire        mem_odt,
    output wire [14:0] mem_a,
    output wire [ 2:0] mem_ba,
    inout  wire [ 3:0] mem_dqs,
    inout  wire [ 3:0] mem_dqs_n,
    inout  wire [31:0] mem_dq,
    output wire [ 3:0] mem_dm,
    output wire        led_clk_alive,
    output wire        led_ddr_ready,
    output wire        led_selftest,
    output wire        uart_tx,
    input  wire        uart_rx
);
    wire pll_lock;
    wire [1:0] selftest_status;
    wire [27:0] axi_awaddr;
    wire        axi_awuser_ap;
    wire [ 3:0] axi_awuser_id;
    wire [ 3:0] axi_awlen;
    wire        axi_awready;
    wire        axi_awvalid;
    wire [255:0] axi_wdata;
    wire [ 31:0] axi_wstrb;
    wire        axi_wready;
    wire [ 3:0] axi_wusero_id;
    wire        axi_wusero_last;
    wire [27:0] axi_araddr;
    wire        axi_aruser_ap;
    wire [ 3:0] axi_aruser_id;
    wire [ 3:0] axi_arlen;
    wire        axi_arready;
    wire        axi_arvalid;
    wire [255:0] axi_rdata;
    wire [ 3:0] axi_rid;
    wire        axi_rlast;
    wire        axi_rvalid;

    localparam PREPROCESS_ACTIVE=(ENABLE_PREPROCESS!=0 && ENABLE_CAMERA!=0);
    localparam CNN_ACTIVE=(ENABLE_CNN!=0 && PREPROCESS_ACTIVE);
    wire cnn_req_valid, cnn_req_write, cnn_req_ready, cnn_rsp_valid, cnn_rsp_error;
    wire [1:0] cnn_req_size;
    wire [31:0] cnn_req_addr, cnn_req_wdata, cnn_rsp_rdata;
    wire [3:0] cnn_req_wstrb;
    wire cnn_hold, cnn_arvalid, cnn_arready, cnn_rvalid, inner_read_error, outer_read_error;
    wire [27:0] cnn_araddr, group_araddr;
    wire [3:0] group_arlen, group_arid;
    wire group_arap, group_arvalid, group_arready, group_rvalid;
    wire [31:0] pp_result_seq;
    wire pp_result_buf;
    wire pp_req_valid, pp_req_write, pp_req_ready, pp_rsp_valid, pp_rsp_error;
    wire [1:0] pp_req_size;
    wire [3:0] pp_req_wstrb;
    wire [31:0] pp_req_addr, pp_req_wdata, pp_rsp_rdata;
    wire preprocess_busy, preprocess_done, pp_read_error;
    wire [1:0] pp_source_hold;
    wire [31:0] cam_source_seq0, cam_source_seq1;
    wire cam_source_geometry_ok;
    wire [27:0] shared_awaddr, pp_awaddr, pp_araddr, cpu_araddr;
    wire [3:0] shared_awlen, shared_awuser_id, cpu_arlen, cpu_arid;
    wire shared_awuser_ap, shared_awvalid, shared_awready, shared_wready;
    wire pp_awvalid, pp_awready, pp_wready, pp_arvalid, pp_arready, pp_rvalid;
    wire cpu_arvalid, cpu_arready, cpu_rvalid, cpu_arap;
    wire [255:0] shared_wdata, pp_wdata;
    wire [31:0] shared_wstrb;
    wire cam_req_valid, cam_req_write, cam_req_ready, cam_rsp_valid, cam_rsp_error;
    wire [1:0] cam_req_size;
    wire [31:0] cam_req_addr, cam_req_wdata, cam_rsp_rdata;
    wire [3:0] cam_req_wstrb;
    wire camera_busy;
    wire camera_dual_mode;
    wire [1:0] camera_cpu_owned;
    wire [27:0] cpu_awaddr, cam_awaddr;
    wire [3:0] cpu_awlen, cpu_awid;
    wire cpu_awap, cpu_awvalid, cpu_awready, cpu_wready, cam_awvalid, cam_awready, cam_wready;
    wire [255:0] cpu_wdata, cam_wdata;
    wire [31:0] cpu_wstrb;
    wire cam_scl_low, cam_sda_low;
    assign camera_scl=cam_scl_low ? 1'b0 : 1'bz;
    assign camera_sda=cam_sda_low ? 1'b0 : 1'bz;
    generate if (ENABLE_CAMERA!=0) begin : g_camera
        camera_mmio #(.CLK_HZ(CORE_CLK_HZ), .EXTERNAL_HOLD_ENABLE(PREPROCESS_ACTIVE),
            .COLORBAR_ENABLE(CAMERA_COLORBAR_ENABLE)) u_camera (
            .clk(core_clk), .resetn(soc_resetn), .busy(camera_busy),
            .dual_mode(camera_dual_mode), .cpu_owned(camera_cpu_owned),
            .external_hold(pp_source_hold), .source_seq0(cam_source_seq0), .source_seq1(cam_source_seq1),
            .source_geometry_ok(cam_source_geometry_ok),
            .req_valid(cam_req_valid), .req_write(cam_req_write), .req_size(cam_req_size),
            .req_addr(cam_req_addr), .req_wdata(cam_req_wdata), .req_wstrb(cam_req_wstrb),
            .req_ready(cam_req_ready), .rsp_valid(cam_rsp_valid), .rsp_error(cam_rsp_error),
            .rsp_rdata(cam_rsp_rdata), .pclk(camera_pclk), .vsync(camera_vsync),
            .href(camera_href), .din(camera_data), .scl_in(camera_scl), .sda_in(camera_sda),
            .scl_low(cam_scl_low), .sda_low(cam_sda_low), .sensor_resetn(camera_resetn),
            .dma_awvalid(cam_awvalid), .dma_awaddr(cam_awaddr), .dma_wdata(cam_wdata),
            .dma_awready(cam_awready), .dma_wready(cam_wready)
        );
        camera_ddr_write_arbiter u_write_arbiter (
            .clk(core_clk), .resetn(soc_resetn),
            .cpu_awaddr(cpu_awaddr), .cpu_awlen(cpu_awlen), .cpu_awid(cpu_awid),
            .cpu_awap(cpu_awap), .cpu_awvalid(cpu_awvalid), .cpu_wdata(cpu_wdata), .cpu_wstrb(cpu_wstrb),
            .cpu_awready(cpu_awready), .cpu_wready(cpu_wready),
            .cam_awaddr(cam_awaddr), .cam_awvalid(cam_awvalid), .cam_wdata(cam_wdata),
            .cam_awready(cam_awready), .cam_wready(cam_wready),
            .awaddr(shared_awaddr), .awlen(shared_awlen), .awid(shared_awuser_id), .awap(shared_awuser_ap),
            .awvalid(shared_awvalid), .awready(shared_awready), .wdata(shared_wdata), .wstrb(shared_wstrb),
            .wready(shared_wready), .busy()
        );
    end else begin : g_no_camera
        assign camera_busy=0;
        assign cam_source_seq0=0; assign cam_source_seq1=0; assign cam_source_geometry_ok=0;
        assign camera_dual_mode=0; assign camera_cpu_owned=0;
        assign cam_req_ready=0; assign cam_rsp_valid=0; assign cam_rsp_error=0; assign cam_rsp_rdata=0;
        assign cam_scl_low=0; assign cam_sda_low=0; assign camera_resetn=0;
        assign cam_awvalid=0; assign cam_awaddr=0; assign cam_wdata=0;
        assign cam_awready=0; assign cam_wready=0;
        assign shared_awaddr=cpu_awaddr; assign shared_awlen=cpu_awlen; assign shared_awuser_id=cpu_awid;
        assign shared_awuser_ap=cpu_awap; assign shared_awvalid=cpu_awvalid;
        assign shared_wdata=cpu_wdata; assign shared_wstrb=cpu_wstrb;
        assign cpu_awready=shared_awready; assign cpu_wready=shared_wready;
    end endgenerate


    generate if (PREPROCESS_ACTIVE) begin : g_preprocess
        preprocess_mmio #(.CLK_HZ(CORE_CLK_HZ), .OUTPUT_HOLD_ENABLE(CNN_ACTIVE)) u_preprocess (
            .output_hold(cnn_hold), .result_seq(pp_result_seq), .result_buf(pp_result_buf),
            .clk(core_clk), .resetn(soc_resetn),
            .req_valid(pp_req_valid), .req_write(pp_req_write), .req_size(pp_req_size),
            .req_addr(pp_req_addr), .req_wdata(pp_req_wdata), .req_wstrb(pp_req_wstrb),
            .req_ready(pp_req_ready), .rsp_valid(pp_rsp_valid), .rsp_error(pp_rsp_error), .rsp_rdata(pp_rsp_rdata),
            .camera_dual_mode(camera_dual_mode), .cpu_owned(camera_cpu_owned),
            .source_geometry_ok(cam_source_geometry_ok), .source_seq0(cam_source_seq0), .source_seq1(cam_source_seq1),
            .busy(preprocess_busy), .done(preprocess_done), .source_hold(pp_source_hold),
            .araddr(pp_araddr), .arvalid(pp_arvalid), .arready(pp_arready),
            .rvalid(pp_rvalid), .rdata(axi_rdata), .rid(axi_rid), .rlast(axi_rlast),
            .awaddr(pp_awaddr), .awvalid(pp_awvalid), .awready(pp_awready), .wdata(pp_wdata), .wready(pp_wready),
            .read_protocol_error(pp_read_error)
        );
        camera_ddr_write_arbiter #(.CAM_AW_ID(4'd3)) u_output_arbiter (
            .clk(core_clk), .resetn(soc_resetn),
            .cpu_awaddr(shared_awaddr), .cpu_awlen(shared_awlen), .cpu_awid(shared_awuser_id),
            .cpu_awap(shared_awuser_ap), .cpu_awvalid(shared_awvalid),
            .cpu_wdata(shared_wdata), .cpu_wstrb(shared_wstrb), .cpu_awready(shared_awready), .cpu_wready(shared_wready),
            .cam_awaddr(pp_awaddr), .cam_awvalid(pp_awvalid), .cam_wdata(pp_wdata),
            .cam_awready(pp_awready), .cam_wready(pp_wready),
            .awaddr(axi_awaddr), .awlen(axi_awlen), .awid(axi_awuser_id), .awap(axi_awuser_ap),
            .awvalid(axi_awvalid), .awready(axi_awready), .wdata(axi_wdata), .wstrb(axi_wstrb), .wready(axi_wready), .busy()
        );
        preprocess_ddr_read_arbiter u_read_arbiter (
            .clk(core_clk), .resetn(soc_resetn),
            .cpu_addr(cpu_araddr), .cpu_len(cpu_arlen), .cpu_id(cpu_arid), .cpu_ap(cpu_arap), .cpu_valid(cpu_arvalid),
            .cpu_ready(cpu_arready), .cpu_rvalid(cpu_rvalid),
            .pp_addr(pp_araddr), .pp_valid(pp_arvalid), .pp_ready(pp_arready), .pp_rvalid(pp_rvalid),
            .araddr(group_araddr), .arlen(group_arlen), .arid(group_arid), .arap(group_arap),
            .arvalid(group_arvalid), .arready(group_arready), .rvalid(group_rvalid), .rlast(axi_rlast), .rid(axi_rid),
            .protocol_error(inner_read_error)
        );
    end else begin : g_no_preprocess
        assign pp_req_ready=0; assign pp_rsp_valid=0; assign pp_rsp_error=0; assign pp_rsp_rdata=0;
        assign preprocess_busy=0; assign preprocess_done=0; assign pp_source_hold=0; assign inner_read_error=0;
        assign pp_result_seq=0; assign pp_result_buf=0;
        assign pp_awaddr=0; assign pp_awvalid=0; assign pp_wdata=0; assign pp_awready=0; assign pp_wready=0;
        assign pp_araddr=0; assign pp_arvalid=0; assign pp_arready=0; assign pp_rvalid=0;
        assign axi_awaddr=shared_awaddr; assign axi_awlen=shared_awlen; assign axi_awuser_id=shared_awuser_id;
        assign axi_awuser_ap=shared_awuser_ap; assign axi_awvalid=shared_awvalid;
        assign axi_wdata=shared_wdata; assign axi_wstrb=shared_wstrb;
        assign shared_awready=axi_awready; assign shared_wready=axi_wready;
        assign group_araddr=cpu_araddr; assign group_arlen=cpu_arlen; assign group_arid=cpu_arid;
        assign group_arap=cpu_arap; assign group_arvalid=cpu_arvalid;
        assign cpu_arready=group_arready; assign cpu_rvalid=group_rvalid;
    end endgenerate

    assign pp_read_error=inner_read_error | outer_read_error;
    generate if(CNN_ACTIVE) begin : g_cnn
        cnn_mmio #(.CLK_HZ(CORE_CLK_HZ)) u_cnn (
            .clk(core_clk), .resetn(soc_resetn),
            .req_valid(cnn_req_valid), .req_write(cnn_req_write), .req_size(cnn_req_size),
            .req_addr(cnn_req_addr), .req_wdata(cnn_req_wdata), .req_wstrb(cnn_req_wstrb),
            .req_ready(cnn_req_ready), .rsp_valid(cnn_rsp_valid), .rsp_error(cnn_rsp_error), .rsp_rdata(cnn_rsp_rdata),
            .pp_done(preprocess_done), .pp_busy(preprocess_busy), .pp_result_buf(pp_result_buf),
            .pp_result_seq(pp_result_seq), .pp_hold(cnn_hold),
            .araddr(cnn_araddr), .arvalid(cnn_arvalid), .arready(cnn_arready), .rvalid(cnn_rvalid),
            .rdata(axi_rdata), .rid(axi_rid), .rlast(axi_rlast), .protocol_error(pp_read_error)
        );
        preprocess_ddr_read_arbiter #(.PP_ID(4'd4)) u_cnn_read_arbiter (
            .clk(core_clk), .resetn(soc_resetn),
            .cpu_addr(group_araddr), .cpu_len(group_arlen), .cpu_id(group_arid), .cpu_ap(group_arap),
            .cpu_valid(group_arvalid), .cpu_ready(group_arready), .cpu_rvalid(group_rvalid),
            .pp_addr(cnn_araddr), .pp_valid(cnn_arvalid), .pp_ready(cnn_arready), .pp_rvalid(cnn_rvalid),
            .araddr(axi_araddr), .arlen(axi_arlen), .arid(axi_aruser_id), .arap(axi_aruser_ap),
            .arvalid(axi_arvalid), .arready(axi_arready), .rvalid(axi_rvalid), .rlast(axi_rlast), .rid(axi_rid),
            .protocol_error(outer_read_error)
        );
    end else begin : g_no_cnn
        assign cnn_req_ready=0; assign cnn_rsp_valid=0; assign cnn_rsp_error=0; assign cnn_rsp_rdata=0;
        assign cnn_hold=0; assign cnn_araddr=0; assign cnn_arvalid=0; assign cnn_arready=0; assign cnn_rvalid=0;
        assign outer_read_error=0;
        assign axi_araddr=group_araddr; assign axi_arlen=group_arlen; assign axi_aruser_id=group_arid;
        assign axi_aruser_ap=group_arap; assign axi_arvalid=group_arvalid;
        assign group_arready=axi_arready; assign group_rvalid=axi_rvalid;
    end endgenerate

    // CPU 与桥均运行于 DDR IP 的 core_clk；DDR 校准完成后再同步释放复位。
    reg [1:0] soc_reset_pipe;
    always @(posedge core_clk or negedge resetn) begin
        if (!resetn)
            soc_reset_pipe <= 2'b00;
        else
            soc_reset_pipe <= {soc_reset_pipe[0], ddr_init_done && pll_lock};
    end
    assign soc_resetn = soc_reset_pipe[1];

    soc_ddr3_leds #(
        .CORE_CLK_HZ(CORE_CLK_HZ),
        .SELFTEST_TIMEOUT_CYCLES(SELFTEST_TIMEOUT_CYCLES)
    ) u_leds (
        .clk(core_clk), .resetn(resetn), .soc_resetn(soc_resetn),
        .selftest_status(selftest_status),
        .led_clk_alive(led_clk_alive), .led_ddr_ready(led_ddr_ready),
        .led_selftest(led_selftest)
    );

    soc_top #(
        .ENABLE_CNN(CNN_ACTIVE),
        .ENABLE_PREPROCESS(PREPROCESS_ACTIVE),
        .ENABLE_CAMERA(ENABLE_CAMERA),
        .RESET_PC(RESET_PC),
        .ENABLE_DDR(1),
        .DDR_BASE(DDR_BASE),
        .DDR_ADDR_MASK(32'hc000_0000),
        .DDR_MEM_DQ_WIDTH(32),
        .UART_CLK_HZ(CORE_CLK_HZ)
    ) u_soc (
        .cnn_req_valid(cnn_req_valid), .cnn_req_write(cnn_req_write),
        .cnn_req_size(cnn_req_size), .cnn_req_addr(cnn_req_addr),
        .cnn_req_wdata(cnn_req_wdata), .cnn_req_wstrb(cnn_req_wstrb),
        .cnn_req_ready(cnn_req_ready), .cnn_rsp_valid(cnn_rsp_valid),
        .cnn_rsp_error(cnn_rsp_error), .cnn_rsp_rdata(cnn_rsp_rdata),
        .pp_req_valid(pp_req_valid), .pp_req_write(pp_req_write),
        .pp_req_size(pp_req_size), .pp_req_addr(pp_req_addr),
        .pp_req_wdata(pp_req_wdata), .pp_req_wstrb(pp_req_wstrb),
        .pp_req_ready(pp_req_ready), .pp_rsp_valid(pp_rsp_valid),
        .pp_rsp_error(pp_rsp_error), .pp_rsp_rdata(pp_rsp_rdata),
        .preprocess_busy(preprocess_busy), .preprocess_done(preprocess_done),
        .cam_req_valid(cam_req_valid), .cam_req_write(cam_req_write),
        .cam_req_size(cam_req_size), .cam_req_addr(cam_req_addr),
        .cam_req_wdata(cam_req_wdata), .cam_req_wstrb(cam_req_wstrb),
        .cam_req_ready(cam_req_ready), .cam_rsp_valid(cam_rsp_valid),
        .cam_rsp_error(cam_rsp_error), .cam_rsp_rdata(cam_rsp_rdata),
        .camera_busy(camera_busy),
        .camera_dual_mode(camera_dual_mode), .camera_cpu_owned(camera_cpu_owned),
        .clk(core_clk),
        .resetn(soc_resetn),
        .uart_rx(uart_rx), .uart_tx(uart_tx),
        .irq_external(irq_external),
        .irq_software(irq_software),
        .irq_timer(irq_timer),
        .debug_wb_pc(debug_wb_pc),
        .debug_wb_rf_we(debug_wb_rf_we),
        .debug_wb_rf_wnum(debug_wb_rf_wnum),
        .debug_wb_rf_wdata(debug_wb_rf_wdata),
        .debug_inst(debug_inst),
        .selftest_status(selftest_status),
        .ddr_init_done(ddr_init_done),
        .ddr_axi_awaddr(cpu_awaddr),
        .ddr_axi_awuser_ap(cpu_awap),
        .ddr_axi_awuser_id(cpu_awid),
        .ddr_axi_awlen(cpu_awlen),
        .ddr_axi_awready(cpu_awready),
        .ddr_axi_awvalid(cpu_awvalid),
        .ddr_axi_wdata(cpu_wdata),
        .ddr_axi_wstrb(cpu_wstrb),
        .ddr_axi_wready(cpu_wready),
        .ddr_axi_wusero_id(cpu_wready ? axi_wusero_id : 4'b0),
        .ddr_axi_wusero_last(cpu_wready && axi_wusero_last),
        .ddr_axi_araddr(cpu_araddr),
        .ddr_axi_aruser_ap(cpu_arap),
        .ddr_axi_aruser_id(cpu_arid),
        .ddr_axi_arlen(cpu_arlen),
        .ddr_axi_arready(cpu_arready),
        .ddr_axi_arvalid(cpu_arvalid),
        .ddr_axi_rdata(axi_rdata),
        .ddr_axi_rid(axi_rid),
        .ddr_axi_rlast(axi_rlast),
        .ddr_axi_rvalid(cpu_rvalid)
    );

    ddr3 u_ddr3 (
        .ref_clk(ddr_ref_clk),
        .resetn(resetn),
        .core_clk(core_clk),
        .pll_lock(pll_lock),
        .phy_pll_lock(),
        .gpll_lock(),
        .rst_gpll_lock(),
        .ddrphy_cpd_lock(),
        .ddr_init_done(ddr_init_done),
        .axi_awaddr(axi_awaddr),
        .axi_awuser_ap(axi_awuser_ap),
        .axi_awuser_id(axi_awuser_id),
        .axi_awlen(axi_awlen),
        .axi_awready(axi_awready),
        .axi_awvalid(axi_awvalid),
        .axi_wdata(axi_wdata),
        .axi_wstrb(axi_wstrb),
        .axi_wready(axi_wready),
        .axi_wusero_id(axi_wusero_id),
        .axi_wusero_last(axi_wusero_last),
        .axi_araddr(axi_araddr),
        .axi_aruser_ap(axi_aruser_ap),
        .axi_aruser_id(axi_aruser_id),
        .axi_arlen(axi_arlen),
        .axi_arready(axi_arready),
        .axi_arvalid(axi_arvalid),
        .axi_rdata(axi_rdata),
        .axi_rid(axi_rid),
        .axi_rlast(axi_rlast),
        .axi_rvalid(axi_rvalid),
        // 与生成的 example_design 相同：不使用 APB 配置口。
        .apb_clk(1'b0),
        .apb_rst_n(1'b0),
        .apb_sel(1'b0),
        .apb_enable(1'b0),
        .apb_addr(8'b0),
        .apb_write(1'b0),
        .apb_ready(),
        .apb_wdata(16'b0),
        .apb_rdata(),
        .mem_cs_n(mem_cs_n),
        .mem_rst_n(mem_rst_n),
        .mem_ck(mem_ck),
        .mem_ck_n(mem_ck_n),
        .mem_cke(mem_cke),
        .mem_ras_n(mem_ras_n),
        .mem_cas_n(mem_cas_n),
        .mem_we_n(mem_we_n),
        .mem_odt(mem_odt),
        .mem_a(mem_a),
        .mem_ba(mem_ba),
        .mem_dqs(mem_dqs),
        .mem_dqs_n(mem_dqs_n),
        .mem_dq(mem_dq),
        .mem_dm(mem_dm),
        // 按 example_design 的缺省控制总线值固定调试输入。
        .dbg_gate_start(1'b0),
        .dbg_cpd_start(1'b0),
        .dbg_ddrphy_rst_n(1'b1),
        .dbg_gpll_scan_rst(1'b0),
        .samp_position_dyn_adj(1'b0),
        .init_samp_position_even(32'b0),
        .wrcal_position_dyn_adj(1'b0),
        .init_wrcal_position(32'b0),
        .force_read_clk_ctrl(1'b0),
        .init_slip_step(16'b0),
        .init_read_clk_ctrl(12'b0),
        .debug_calib_ctrl(),
        .dbg_slice_status(),
        .dbg_slice_state(),
        .debug_data(),
        .dbg_dll_upd_state(),
        .debug_gpll_dps_phase(),
        .dbg_rst_dps_state(),
        .dbg_tran_err_rst_cnt(),
        .dbg_ddrphy_init_fail(),
        .debug_cpd_offset_adj(1'b0),
        .debug_cpd_offset_dir(1'b0),
        .debug_cpd_offset(10'b0),
        .debug_dps_cnt_dir0(),
        .debug_dps_cnt_dir1(),
        .ck_dly_en(1'b1),
        .init_ck_dly_step(8'b0),
        .ck_dly_set_bin(),
        .align_error(),
        .debug_rst_state(),
        .debug_cpd_state()
    );
endmodule

// 高电平点亮。放在同一源文件，现有 PDS/ModelSim 编译列表无需增加 RTL 文件。
module soc_ddr3_leds #(
    parameter integer CORE_CLK_HZ = 100_000_000,
    parameter integer SELFTEST_TIMEOUT_CYCLES = CORE_CLK_HZ * 5
) (
    input  wire       clk,
    input  wire       resetn,
    input  wire       soc_resetn,
    input  wire [1:0] selftest_status,
    output reg        led_clk_alive,
    output wire       led_ddr_ready,
    output wire       led_selftest
);
    localparam integer SLOW_HALF_CYCLES = (CORE_CLK_HZ / 2 > 0) ? CORE_CLK_HZ / 2 : 1;
    localparam integer FAST_HALF_CYCLES = (CORE_CLK_HZ / 8 > 0) ? CORE_CLK_HZ / 8 : 1;
    localparam integer TIMEOUT_CYCLES = (SELFTEST_TIMEOUT_CYCLES > 0) ? SELFTEST_TIMEOUT_CYCLES : 1;
    reg [31:0] heartbeat_count;
    reg [31:0] blink_count;
    reg [31:0] timeout_count;
    reg        blink_on;
    reg        timed_out;
    reg [1:0]  previous_mode;
    wire [1:0] mode = timed_out ? 2'd3 : selftest_status;
    wire [31:0] blink_half_cycles = (mode == 2'd3) ? FAST_HALF_CYCLES : SLOW_HALF_CYCLES;

    // 不依赖 DDR 校准完成：训练期间只要 core_clk 存在就能看到心跳。
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            heartbeat_count <= 32'd0;
            led_clk_alive <= 1'b0;
        end else if (heartbeat_count == SLOW_HALF_CYCLES - 1) begin
            heartbeat_count <= 32'd0;
            led_clk_alive <= !led_clk_alive;
        end else begin
            heartbeat_count <= heartbeat_count + 32'd1;
        end
    end

    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            timeout_count <= 32'd0;
            timed_out <= 1'b0;
            blink_count <= 32'd0;
            blink_on <= 1'b0;
            previous_mode <= 2'd0;
        end else if (!soc_resetn) begin
            timeout_count <= 32'd0;
            timed_out <= 1'b0;
            blink_count <= 32'd0;
            blink_on <= 1'b0;
            previous_mode <= 2'd0;
        end else begin
            // 启动装载也计入超时；DDR 训练期间不计时。迟来的 PASS 不能清除超时。
            if (!timed_out && selftest_status != 2'd2 && selftest_status != 2'd3) begin
                if (timeout_count == TIMEOUT_CYCLES - 1)
                    timed_out <= 1'b1;
                else
                    timeout_count <= timeout_count + 32'd1;
            end
            previous_mode <= mode;
            if (mode != previous_mode) begin
                blink_count <= 32'd0;
                blink_on <= 1'b1;
            end else if (mode == 2'd1 || mode == 2'd3) begin
                if (blink_count == blink_half_cycles - 1) begin
                    blink_count <= 32'd0;
                    blink_on <= !blink_on;
                end else begin
                    blink_count <= blink_count + 32'd1;
                end
            end
        end
    end

    assign led_ddr_ready = resetn && soc_resetn;
    assign led_selftest = resetn && soc_resetn &&
                          ((mode == 2'd2) || ((mode == 2'd1 || mode == 2'd3) && blink_on));
endmodule
