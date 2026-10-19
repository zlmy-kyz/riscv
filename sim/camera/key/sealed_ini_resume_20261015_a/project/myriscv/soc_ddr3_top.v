`timescale 1ns / 1ps

// MINI-(200H) x32 / 8Gb DDR3 集成顶层。ddr_ref_clk 是已缓冲的单端参考时钟。
// 当前生成 DDR3 IP 使用 125 MHz 参考时钟、750 Mbps；core_clk 为 93.75 MHz。
// CORE_CLK_HZ 默认值保留仿真接口兼容，board_top 按实际 core_clk 覆写。
module soc_ddr3_top #(
    parameter integer ENABLE_CAMERA = 0,
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

    wire cam_req_valid, cam_req_write, cam_req_ready, cam_rsp_valid, cam_rsp_error;
    wire [1:0] cam_req_size;
    wire [31:0] cam_req_addr, cam_req_wdata, cam_rsp_rdata;
    wire [3:0] cam_req_wstrb;
    wire camera_busy;
    wire [27:0] cpu_awaddr, cam_awaddr;
    wire [3:0] cpu_awlen, cpu_awid;
    wire cpu_awap, cpu_awvalid, cpu_awready, cpu_wready, cam_awvalid, cam_awready, cam_wready;
    wire [255:0] cpu_wdata, cam_wdata;
    wire [31:0] cpu_wstrb;
    wire cam_scl_low, cam_sda_low;
    assign camera_scl=cam_scl_low ? 1'b0 : 1'bz;
    assign camera_sda=cam_sda_low ? 1'b0 : 1'bz;
    generate if (ENABLE_CAMERA!=0) begin : g_camera
        camera_mmio #(.CLK_HZ(CORE_CLK_HZ)) u_camera (
            .clk(core_clk), .resetn(soc_resetn), .busy(camera_busy),
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
            .awaddr(axi_awaddr), .awlen(axi_awlen), .awid(axi_awuser_id), .awap(axi_awuser_ap),
            .awvalid(axi_awvalid), .awready(axi_awready), .wdata(axi_wdata), .wstrb(axi_wstrb),
            .wready(axi_wready), .busy()
        );
    end else begin : g_no_camera
        assign camera_busy=0;
        assign cam_req_ready=0; assign cam_rsp_valid=0; assign cam_rsp_error=0; assign cam_rsp_rdata=0;
        assign cam_scl_low=0; assign cam_sda_low=0; assign camera_resetn=0;
        assign cam_awvalid=0; assign cam_awaddr=0; assign cam_wdata=0;
        assign cam_awready=0; assign cam_wready=0;
        assign axi_awaddr=cpu_awaddr; assign axi_awlen=cpu_awlen; assign axi_awuser_id=cpu_awid;
        assign axi_awuser_ap=cpu_awap; assign axi_awvalid=cpu_awvalid;
        assign axi_wdata=cpu_wdata; assign axi_wstrb=cpu_wstrb;
        assign cpu_awready=axi_awready; assign cpu_wready=axi_wready;
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
        .ENABLE_CAMERA(ENABLE_CAMERA),
        .RESET_PC(RESET_PC),
        .ENABLE_DDR(1),
        .DDR_BASE(DDR_BASE),
        .DDR_ADDR_MASK(32'hc000_0000),
        .DDR_MEM_DQ_WIDTH(32),
        .UART_CLK_HZ(CORE_CLK_HZ)
    ) u_soc (
        .cam_req_valid(cam_req_valid), .cam_req_write(cam_req_write),
        .cam_req_size(cam_req_size), .cam_req_addr(cam_req_addr),
        .cam_req_wdata(cam_req_wdata), .cam_req_wstrb(cam_req_wstrb),
        .cam_req_ready(cam_req_ready), .cam_rsp_valid(cam_rsp_valid),
        .cam_rsp_error(cam_rsp_error), .cam_rsp_rdata(cam_rsp_rdata),
        .camera_busy(camera_busy),
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
        .ddr_axi_araddr(axi_araddr),
        .ddr_axi_aruser_ap(axi_aruser_ap),
        .ddr_axi_aruser_id(axi_aruser_id),
        .ddr_axi_arlen(axi_arlen),
        .ddr_axi_arready(axi_arready),
        .ddr_axi_arvalid(axi_arvalid),
        .ddr_axi_rdata(axi_rdata),
        .ddr_axi_rid(axi_rid),
        .ddr_axi_rlast(axi_rlast),
        .ddr_axi_rvalid(axi_rvalid)
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
