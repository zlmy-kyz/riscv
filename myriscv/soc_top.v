`timescale 1ns / 1ps

// SoC 顶层：CPU + 独立指令/数据总线 + ROM/RAM/MMIO，可选共享 DDR3。
module soc_top #(
    parameter [31:0] RESET_PC = 32'h0000_0000,
    parameter [31:0] INST_ROM_BASE = RESET_PC,
    // 默认让 RAM 跟随测试程序的链接基址；正式上板时可独立覆写。
    parameter [31:0] DATA_RAM_BASE = RESET_PC,
    parameter [31:0] MMIO_BASE = 32'h1000_0000,
    parameter integer ENABLE_DDR = 0,
    parameter [31:0] DDR_BASE = 32'h4000_0000,
    parameter [31:0] DDR_ADDR_MASK = 32'he000_0000,
    parameter integer INST_REQ_STALL_CYCLES = 0,
    parameter integer INST_RSP_DELAY_CYCLES = 0,
    parameter integer DATA_REQ_STALL_CYCLES = 0,
    parameter integer DATA_RSP_DELAY_CYCLES = 0,
    parameter [31:0] UART_BASE = 32'h1000_1000,
    parameter integer UART_CLK_HZ = 93_750_000,
    parameter integer UART_RSP_DELAY_CYCLES = 0
) (
    input  wire        clk,
    input  wire        resetn,
    input  wire        irq_external,
    input  wire        irq_software,
    input  wire        irq_timer,
    output wire [31:0] debug_wb_pc,
    output wire [ 3:0] debug_wb_rf_we,
    output wire [ 4:0] debug_wb_rf_wnum,
    output wire [31:0] debug_wb_rf_wdata,
    output wire [31:0] debug_inst,

    // Pango DDR3 IP 的 core_clk 域用户口；ENABLE_DDR=0 时输出为 0。
    input  wire        ddr_init_done,
    output wire [27:0] ddr_axi_awaddr,
    output wire        ddr_axi_awuser_ap,
    output wire [ 3:0] ddr_axi_awuser_id,
    output wire [ 3:0] ddr_axi_awlen,
    input  wire        ddr_axi_awready,
    output wire        ddr_axi_awvalid,
    output wire [127:0] ddr_axi_wdata,
    output wire [15:0] ddr_axi_wstrb,
    input  wire        ddr_axi_wready,
    input  wire [ 3:0] ddr_axi_wusero_id,
    input  wire        ddr_axi_wusero_last,
    output wire [27:0] ddr_axi_araddr,
    output wire        ddr_axi_aruser_ap,
    output wire [ 3:0] ddr_axi_aruser_id,
    output wire [ 3:0] ddr_axi_arlen,
    input  wire        ddr_axi_arready,
    output wire        ddr_axi_arvalid,
    input  wire [127:0] ddr_axi_rdata,
    input  wire [ 3:0] ddr_axi_rid,
    input  wire        ddr_axi_rlast,
    input  wire        ddr_axi_rvalid,
    output wire [ 1:0] selftest_status,
    input  wire        uart_rx,
    output wire        uart_tx
);

    // CPU 使用字节地址；ROM/RAM IP 使用 32 位字地址。
    wire        inst_req_valid;
    wire [31:0] inst_req_addr;
    wire        inst_req_ready;
    wire        inst_rsp_valid;
    wire [31:0] inst_rsp_rdata;
    wire        inst_rsp_error;
    wire        rom_bus_req_valid;
    wire [31:0] rom_bus_req_addr;
    wire        rom_bus_req_ready;
    wire        rom_bus_rsp_valid;
    wire [31:0] rom_bus_rsp_rdata;
    wire        rom_bus_rsp_error;
    wire        inst_ddr_req_valid;
    wire [31:0] inst_ddr_req_addr;
    wire        inst_ddr_req_ready;
    wire        inst_ddr_rsp_valid;
    wire [31:0] inst_ddr_rsp_rdata;
    wire        inst_ddr_rsp_error;
    wire [11:0] inst_rom_addr;
    wire [31:0] inst_rom_rdata;
    wire        data_req_valid;
    wire        data_req_write;
    wire [ 1:0] data_req_size;
    wire [31:0] data_req_addr;
    wire [31:0] data_req_wdata;
    wire [ 3:0] data_req_wstrb;
    wire        data_req_ready;
    wire        data_rsp_valid;
    wire [31:0] data_rsp_rdata;
    wire        data_rsp_error;
    wire        uart_irq;
    // Preserve the existing generic external source; board_top ties it low.
    // UART is synchronous to this same core_clk domain and holds a level.
    wire        cpu_irq_external = irq_external | uart_irq;

    wire        ram_bus_req_valid;
    wire        ram_bus_req_write;
    wire [ 1:0] ram_bus_req_size;
    wire [31:0] ram_bus_req_addr;
    wire [31:0] ram_bus_req_wdata;
    wire [ 3:0] ram_bus_req_wstrb;
    wire        ram_bus_req_ready;
    wire        ram_bus_rsp_valid;
    wire [31:0] ram_bus_rsp_rdata;
    wire        ram_bus_rsp_error;

    wire        data_ddr_req_valid;
    wire        data_ddr_req_write;
    wire [ 1:0] data_ddr_req_size;
    wire [31:0] data_ddr_req_addr;
    wire [31:0] data_ddr_req_wdata;
    wire [ 3:0] data_ddr_req_wstrb;
    wire        data_ddr_req_ready;
    wire        data_ddr_rsp_valid;
    wire [31:0] data_ddr_rsp_rdata;
    wire        data_ddr_rsp_error;

    wire        mmio_req_valid;
    wire        mmio_req_write;
    wire [ 1:0] mmio_req_size;
    wire [31:0] mmio_req_addr;
    wire [31:0] mmio_req_wdata;
    wire [ 3:0] mmio_req_wstrb;
    wire        mmio_req_ready;
    wire        mmio_rsp_valid;
    wire [31:0] mmio_rsp_rdata;
    wire        mmio_rsp_error;

    wire uart_req_valid, uart_req_write, uart_req_ready;
    wire [1:0] uart_req_size;
    wire [31:0] uart_req_addr, uart_req_wdata, uart_rsp_rdata;
    wire [3:0] uart_req_wstrb;
    wire uart_rsp_valid, uart_rsp_error;

    wire [11:0] data_ram_addr;
    wire [31:0] data_ram_wdata;
    wire [31:0] data_ram_rdata;
    wire [ 3:0] data_ram_wstrb;
    wire        data_ram_we;

    // 兼容现有测试台的观察点：data_write 表示一次真正被接受的 store，
    // 因此即使总线反压也只产生一个周期的提交脉冲。
    wire [31:0] data_addr;
    wire [31:0] data_wdata;
    wire        data_read;
    wire        data_write;
    wire [31:0] inst_addr;
    assign inst_addr  = inst_req_addr;
    assign data_addr  = data_req_addr;
    assign data_wdata = data_req_wdata;
    assign data_read  = data_req_valid && data_req_ready && !data_req_write;
    assign data_write = data_req_valid && data_req_ready &&  data_req_write;

    mycpu_sync #(
        .RESET_PC(RESET_PC)
    ) u_cpu (
        .clk               (clk),
        .resetn            (resetn),
        .irq_external      (cpu_irq_external),
        .irq_software      (irq_software),
        .irq_timer         (irq_timer),
        .inst_req_valid    (inst_req_valid),
        .inst_req_addr     (inst_req_addr),
        .inst_req_ready    (inst_req_ready),
        .inst_rsp_valid    (inst_rsp_valid),
        .inst_rsp_rdata    (inst_rsp_rdata),
        .inst_rsp_error    (inst_rsp_error),
        .data_req_valid    (data_req_valid),
        .data_req_write    (data_req_write),
        .data_req_size     (data_req_size),
        .data_req_addr     (data_req_addr),
        .data_req_wdata    (data_req_wdata),
        .data_req_wstrb    (data_req_wstrb),
        .data_req_ready    (data_req_ready),
        .data_rsp_valid    (data_rsp_valid),
        .data_rsp_rdata    (data_rsp_rdata),
        .data_rsp_error    (data_rsp_error),
        .debug_wb_pc       (debug_wb_pc),
        .debug_wb_rf_we    (debug_wb_rf_we),
        .debug_wb_rf_wnum  (debug_wb_rf_wnum),
        .debug_wb_rf_wdata (debug_wb_rf_wdata),
        .debug_inst        (debug_inst)
    );

    inst_bus_interconnect #(
        .ROM_BASE      (INST_ROM_BASE),
        .ROM_ADDR_MASK (32'hffff_c000),
        .ENABLE_DDR     (ENABLE_DDR),
        .DDR_BASE       (DDR_BASE),
        .DDR_ADDR_MASK  (DDR_ADDR_MASK)
    ) u_inst_bus_interconnect (
        .clk           (clk),
        .resetn        (resetn),
        .m_req_valid   (inst_req_valid),
        .m_req_addr    (inst_req_addr),
        .m_req_ready   (inst_req_ready),
        .m_rsp_valid   (inst_rsp_valid),
        .m_rsp_rdata   (inst_rsp_rdata),
        .m_rsp_error   (inst_rsp_error),
        .rom_req_valid (rom_bus_req_valid),
        .rom_req_addr  (rom_bus_req_addr),
        .rom_req_ready (rom_bus_req_ready),
        .rom_rsp_valid (rom_bus_rsp_valid),
        .rom_rsp_rdata (rom_bus_rsp_rdata),
        .rom_rsp_error (rom_bus_rsp_error),
        .ddr_req_valid (inst_ddr_req_valid),
        .ddr_req_addr  (inst_ddr_req_addr),
        .ddr_req_ready (inst_ddr_req_ready),
        .ddr_rsp_valid (inst_ddr_rsp_valid),
        .ddr_rsp_rdata (inst_ddr_rsp_rdata),
        .ddr_rsp_error (inst_ddr_rsp_error)
    );

    inst_bram_adapter #(
        .ROM_ADDR_WIDTH(12),
        .REQ_STALL_CYCLES(INST_REQ_STALL_CYCLES),
        .RSP_DELAY_CYCLES(INST_RSP_DELAY_CYCLES)
    ) u_inst_bram_adapter (
        .clk        (clk),
        .resetn     (resetn),
        .req_valid  (rom_bus_req_valid),
        .req_addr   (rom_bus_req_addr),
        .req_ready  (rom_bus_req_ready),
        .rsp_valid  (rom_bus_rsp_valid),
        .rsp_rdata  (rom_bus_rsp_rdata),
        .rsp_error  (rom_bus_rsp_error),
        .rom_addr   (inst_rom_addr),
        .rom_rdata  (inst_rom_rdata)
    );

    // 4096 x 32 bit = 16 KiB。适配器收到的已经是相对INST_ROM_BASE
    // 的局部字节地址，不再把窗口外高地址按低位镜像到ROM。
    inst_rom u_inst_rom (
        .addr    (inst_rom_addr),
        .clk     (clk),
        .rst     (!resetn),
        .rd_data (inst_rom_rdata)
    );

    data_bus_interconnect #(
        .RAM_BASE      (DATA_RAM_BASE),
        .RAM_ADDR_MASK (32'hffff_c000),
        .MMIO_BASE     (MMIO_BASE),
        .MMIO_ADDR_MASK(32'hffff_f000),
        .ENABLE_DDR    (ENABLE_DDR),
        .DDR_BASE      (DDR_BASE),
        .DDR_ADDR_MASK (DDR_ADDR_MASK),
        .ENABLE_UART   (1),
        .UART_BASE     (UART_BASE)
    ) u_data_bus_interconnect (
        .clk            (clk),
        .resetn         (resetn),
        .m_req_valid    (data_req_valid),
        .m_req_write    (data_req_write),
        .m_req_size     (data_req_size),
        .m_req_addr     (data_req_addr),
        .m_req_wdata    (data_req_wdata),
        .m_req_wstrb    (data_req_wstrb),
        .m_req_ready    (data_req_ready),
        .m_rsp_valid    (data_rsp_valid),
        .m_rsp_rdata    (data_rsp_rdata),
        .m_rsp_error    (data_rsp_error),
        .ram_req_valid  (ram_bus_req_valid),
        .ram_req_write  (ram_bus_req_write),
        .ram_req_size   (ram_bus_req_size),
        .ram_req_addr   (ram_bus_req_addr),
        .ram_req_wdata  (ram_bus_req_wdata),
        .ram_req_wstrb  (ram_bus_req_wstrb),
        .ram_req_ready  (ram_bus_req_ready),
        .ram_rsp_valid  (ram_bus_rsp_valid),
        .ram_rsp_rdata  (ram_bus_rsp_rdata),
        .ram_rsp_error  (ram_bus_rsp_error),
        .mmio_req_valid (mmio_req_valid),
        .mmio_req_write (mmio_req_write),
        .mmio_req_size  (mmio_req_size),
        .mmio_req_addr  (mmio_req_addr),
        .mmio_req_wdata (mmio_req_wdata),
        .mmio_req_wstrb (mmio_req_wstrb),
        .mmio_req_ready (mmio_req_ready),
        .mmio_rsp_valid (mmio_rsp_valid),
        .mmio_rsp_rdata (mmio_rsp_rdata),
        .mmio_rsp_error (mmio_rsp_error),
        .ddr_req_valid  (data_ddr_req_valid),
        .ddr_req_write  (data_ddr_req_write),
        .ddr_req_size   (data_ddr_req_size),
        .ddr_req_addr   (data_ddr_req_addr),
        .ddr_req_wdata  (data_ddr_req_wdata),
        .ddr_req_wstrb  (data_ddr_req_wstrb),
        .ddr_req_ready  (data_ddr_req_ready),
        .ddr_rsp_valid  (data_ddr_rsp_valid),
        .ddr_rsp_rdata  (data_ddr_rsp_rdata),
        .ddr_rsp_error  (data_ddr_rsp_error),
        .uart_req_valid(uart_req_valid), .uart_req_write(uart_req_write),
        .uart_req_size(uart_req_size), .uart_req_addr(uart_req_addr),
        .uart_req_wdata(uart_req_wdata), .uart_req_wstrb(uart_req_wstrb),
        .uart_req_ready(uart_req_ready), .uart_rsp_valid(uart_rsp_valid),
        .uart_rsp_rdata(uart_rsp_rdata), .uart_rsp_error(uart_rsp_error)
    );

    data_bram_adapter #(
        .RAM_ADDR_WIDTH(12),
        .REQ_STALL_CYCLES(DATA_REQ_STALL_CYCLES),
        .RSP_DELAY_CYCLES(DATA_RSP_DELAY_CYCLES)
    ) u_data_bram_adapter (
        .clk        (clk),
        .resetn     (resetn),
        .req_valid  (ram_bus_req_valid),
        .req_write  (ram_bus_req_write),
        .req_size   (ram_bus_req_size),
        .req_addr   (ram_bus_req_addr),
        .req_wdata  (ram_bus_req_wdata),
        .req_wstrb  (ram_bus_req_wstrb),
        .req_ready  (ram_bus_req_ready),
        .rsp_valid  (ram_bus_rsp_valid),
        .rsp_rdata  (ram_bus_rsp_rdata),
        .rsp_error  (ram_bus_rsp_error),
        .ram_addr   (data_ram_addr),
        .ram_wdata  (data_ram_wdata),
        .ram_wstrb  (data_ram_wstrb),
        .ram_we     (data_ram_we),
        .ram_rdata  (data_ram_rdata)
    );

    data_ram u_data_ram (
        .wr_data    (data_ram_wdata),
        .addr       (data_ram_addr),
        .wr_en      (data_ram_we),
        .wr_byte_en (data_ram_wstrb),
        .clk        (clk),
        .rst        (!resetn),
        .rd_data    (data_ram_rdata)
    );

    simple_mmio u_simple_mmio (
        .clk       (clk),
        .resetn    (resetn),
        .req_valid (mmio_req_valid),
        .req_write (mmio_req_write),
        .req_size  (mmio_req_size),
        .req_addr  (mmio_req_addr),
        .req_wdata (mmio_req_wdata),
        .req_wstrb (mmio_req_wstrb),
        .req_ready (mmio_req_ready),
        .rsp_valid (mmio_rsp_valid),
        .rsp_rdata (mmio_rsp_rdata),
        .rsp_error (mmio_rsp_error),
        .test_status(selftest_status)
    );

    uart_mmio #(.CLK_HZ(UART_CLK_HZ), .RSP_DELAY_CYCLES(UART_RSP_DELAY_CYCLES)) u_uart_mmio (
        .clk(clk), .resetn(resetn), .req_valid(uart_req_valid),
        .req_write(uart_req_write), .req_size(uart_req_size),
        .req_addr(uart_req_addr), .req_wdata(uart_req_wdata), .req_wstrb(uart_req_wstrb),
        .req_ready(uart_req_ready), .rsp_valid(uart_rsp_valid),
        .rsp_rdata(uart_rsp_rdata), .rsp_error(uart_rsp_error),
        .uart_rx(uart_rx), .uart_tx(uart_tx), .uart_irq(uart_irq)
    );

    generate
        if (ENABLE_DDR != 0) begin : g_ddr
            dual_sram_to_pango_ddr_bridge u_ddr_bridge (
                .clk              (clk),
                .resetn           (resetn),
                .ddr_init_done    (ddr_init_done),
                .inst_req_valid   (inst_ddr_req_valid),
                .inst_req_addr    (inst_ddr_req_addr),
                .inst_req_ready   (inst_ddr_req_ready),
                .inst_rsp_valid   (inst_ddr_rsp_valid),
                .inst_rsp_rdata   (inst_ddr_rsp_rdata),
                .inst_rsp_error   (inst_ddr_rsp_error),
                .data_req_valid   (data_ddr_req_valid),
                .data_req_write   (data_ddr_req_write),
                .data_req_size    (data_ddr_req_size),
                .data_req_addr    (data_ddr_req_addr),
                .data_req_wdata   (data_ddr_req_wdata),
                .data_req_wstrb   (data_ddr_req_wstrb),
                .data_req_ready   (data_ddr_req_ready),
                .data_rsp_valid   (data_ddr_rsp_valid),
                .data_rsp_rdata   (data_ddr_rsp_rdata),
                .data_rsp_error   (data_ddr_rsp_error),
                .axi_awaddr       (ddr_axi_awaddr),
                .axi_awuser_ap    (ddr_axi_awuser_ap),
                .axi_awuser_id    (ddr_axi_awuser_id),
                .axi_awlen        (ddr_axi_awlen),
                .axi_awready      (ddr_axi_awready),
                .axi_awvalid      (ddr_axi_awvalid),
                .axi_wdata        (ddr_axi_wdata),
                .axi_wstrb        (ddr_axi_wstrb),
                .axi_wready       (ddr_axi_wready),
                .axi_wusero_id    (ddr_axi_wusero_id),
                .axi_wusero_last  (ddr_axi_wusero_last),
                .axi_araddr       (ddr_axi_araddr),
                .axi_aruser_ap    (ddr_axi_aruser_ap),
                .axi_aruser_id    (ddr_axi_aruser_id),
                .axi_arlen        (ddr_axi_arlen),
                .axi_arready      (ddr_axi_arready),
                .axi_arvalid      (ddr_axi_arvalid),
                .axi_rdata        (ddr_axi_rdata),
                .axi_rid          (ddr_axi_rid),
                .axi_rlast        (ddr_axi_rlast),
                .axi_rvalid       (ddr_axi_rvalid)
            );
        end else begin : g_no_ddr
            assign inst_ddr_req_ready = 1'b0;
            assign inst_ddr_rsp_valid = 1'b0;
            assign inst_ddr_rsp_rdata = 32'b0;
            assign inst_ddr_rsp_error = 1'b0;
            assign data_ddr_req_ready = 1'b0;
            assign data_ddr_rsp_valid = 1'b0;
            assign data_ddr_rsp_rdata = 32'b0;
            assign data_ddr_rsp_error = 1'b0;
            assign ddr_axi_awaddr     = 28'b0;
            assign ddr_axi_awuser_ap  = 1'b0;
            assign ddr_axi_awuser_id  = 4'b0;
            assign ddr_axi_awlen      = 4'b0;
            assign ddr_axi_awvalid    = 1'b0;
            assign ddr_axi_wdata      = 128'b0;
            assign ddr_axi_wstrb      = 16'b0;
            assign ddr_axi_araddr     = 28'b0;
            assign ddr_axi_aruser_ap  = 1'b0;
            assign ddr_axi_aruser_id  = 4'b0;
            assign ddr_axi_arlen      = 4'b0;
            assign ddr_axi_arvalid    = 1'b0;
        end
    endgenerate

endmodule
