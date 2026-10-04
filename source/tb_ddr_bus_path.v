`timescale 1ns / 1ps

// 指令/数据地址译码器 + 共享 DDR 桥的端到端测试。
// DDR 用户口由简单模型代替，不依赖 Pango 的加密仿真库。
module tb_ddr_bus_path;
    reg clk = 1'b0;
    reg resetn = 1'b0;
    reg ddr_init_done = 1'b0;
    always #5 clk = ~clk;

    reg i_valid = 1'b0;
    reg [31:0] i_addr = 32'b0;
    wire i_ready, i_rsp_valid, i_rsp_error;
    wire [31:0] i_rsp_data;
    reg d_valid = 1'b0;
    reg d_write = 1'b0;
    reg [31:0] d_addr = 32'b0;
    reg [31:0] d_wdata = 32'b0;
    reg [3:0] d_wstrb = 4'b0;
    wire d_ready, d_rsp_valid, d_rsp_error;
    wire [31:0] d_rsp_data;

    wire rom_valid;
    wire [31:0] rom_addr;
    reg rom_rsp_valid = 1'b0;
    reg [31:0] rom_rsp_data = 32'b0;
    wire ram_valid;
    wire [31:0] ram_addr;
    reg ram_rsp_valid = 1'b0;
    reg [31:0] ram_rsp_data = 32'b0;
    wire mmio_valid;
    wire [31:0] mmio_addr;
    reg mmio_rsp_valid = 1'b0;
    reg [31:0] mmio_rsp_data = 32'b0;

    wire bi_valid, bi_ready, bi_rsp_valid, bi_rsp_error;
    wire [31:0] bi_addr, bi_rsp_data;
    wire bd_valid, bd_write, bd_ready, bd_rsp_valid, bd_rsp_error;
    wire [1:0] bd_size;
    wire [31:0] bd_addr, bd_wdata, bd_rsp_data;
    wire [3:0] bd_wstrb;

    wire [27:0] awaddr, araddr;
    wire [3:0] awid, arid, awlen, arlen;
    wire awap, arap, awvalid, arvalid;
    wire [127:0] wdata;
    wire [15:0] wstrb;
    reg wready = 1'b0;
    reg [3:0] wid = 4'b0;
    reg wlast = 1'b0;
    reg [127:0] rdata = 128'b0;
    reg [3:0] rid = 4'b0;
    reg rlast = 1'b0;
    reg rvalid = 1'b0;
    reg read_pending = 1'b0;
    reg write_pending = 1'b0;
    reg [27:0] saved_read_addr = 28'b0;
    reg [27:0] saved_write_addr = 28'b0;
    reg [3:0] saved_read_id = 4'b0;
    reg [127:0] memory [0:3];
    integer failures = 0;
    integer byte_index;

    inst_bus_interconnect #(
        .ROM_BASE(32'h0000_0000),
        .ENABLE_DDR(1),
        .DDR_BASE(32'h4000_0000)
    ) u_inst_bus (
        .clk(clk), .resetn(resetn),
        .m_req_valid(i_valid), .m_req_addr(i_addr), .m_req_ready(i_ready),
        .m_rsp_valid(i_rsp_valid), .m_rsp_rdata(i_rsp_data),
        .m_rsp_error(i_rsp_error),
        .rom_req_valid(rom_valid), .rom_req_addr(rom_addr),
        .rom_req_ready(1'b1), .rom_rsp_valid(rom_rsp_valid),
        .rom_rsp_rdata(rom_rsp_data), .rom_rsp_error(1'b0),
        .ddr_req_valid(bi_valid), .ddr_req_addr(bi_addr),
        .ddr_req_ready(bi_ready), .ddr_rsp_valid(bi_rsp_valid),
        .ddr_rsp_rdata(bi_rsp_data), .ddr_rsp_error(bi_rsp_error)
    );

    data_bus_interconnect #(
        .RAM_BASE(32'h0000_0000),
        .MMIO_BASE(32'h1000_0000),
        .ENABLE_DDR(1),
        .DDR_BASE(32'h4000_0000)
    ) u_data_bus (
        .clk(clk), .resetn(resetn),
        .m_req_valid(d_valid), .m_req_write(d_write), .m_req_size(2'd2),
        .m_req_addr(d_addr), .m_req_wdata(d_wdata), .m_req_wstrb(d_wstrb),
        .m_req_ready(d_ready), .m_rsp_valid(d_rsp_valid),
        .m_rsp_rdata(d_rsp_data), .m_rsp_error(d_rsp_error),
        .ram_req_valid(ram_valid), .ram_req_write(), .ram_req_size(),
        .ram_req_addr(ram_addr), .ram_req_wdata(), .ram_req_wstrb(),
        .ram_req_ready(1'b1), .ram_rsp_valid(ram_rsp_valid),
        .ram_rsp_rdata(ram_rsp_data), .ram_rsp_error(1'b0),
        .mmio_req_valid(mmio_valid), .mmio_req_write(), .mmio_req_size(),
        .mmio_req_addr(mmio_addr), .mmio_req_wdata(), .mmio_req_wstrb(),
        .mmio_req_ready(1'b1), .mmio_rsp_valid(mmio_rsp_valid),
        .mmio_rsp_rdata(mmio_rsp_data), .mmio_rsp_error(1'b0),
        .ddr_req_valid(bd_valid), .ddr_req_write(bd_write),
        .ddr_req_size(bd_size), .ddr_req_addr(bd_addr),
        .ddr_req_wdata(bd_wdata), .ddr_req_wstrb(bd_wstrb),
        .ddr_req_ready(bd_ready), .ddr_rsp_valid(bd_rsp_valid),
        .ddr_rsp_rdata(bd_rsp_data), .ddr_rsp_error(bd_rsp_error)
    );

    dual_sram_to_pango_ddr_bridge u_bridge (
        .clk(clk), .resetn(resetn), .ddr_init_done(ddr_init_done),
        .inst_req_valid(bi_valid), .inst_req_addr(bi_addr),
        .inst_req_ready(bi_ready), .inst_rsp_valid(bi_rsp_valid),
        .inst_rsp_rdata(bi_rsp_data), .inst_rsp_error(bi_rsp_error),
        .data_req_valid(bd_valid), .data_req_write(bd_write),
        .data_req_size(bd_size), .data_req_addr(bd_addr),
        .data_req_wdata(bd_wdata), .data_req_wstrb(bd_wstrb),
        .data_req_ready(bd_ready), .data_rsp_valid(bd_rsp_valid),
        .data_rsp_rdata(bd_rsp_data), .data_rsp_error(bd_rsp_error),
        .axi_awaddr(awaddr), .axi_awuser_ap(awap), .axi_awuser_id(awid),
        .axi_awlen(awlen), .axi_awready(!write_pending),
        .axi_awvalid(awvalid), .axi_wdata(wdata), .axi_wstrb(wstrb),
        .axi_wready(wready), .axi_wusero_id(wid), .axi_wusero_last(wlast),
        .axi_araddr(araddr), .axi_aruser_ap(arap), .axi_aruser_id(arid),
        .axi_arlen(arlen), .axi_arready(!read_pending),
        .axi_arvalid(arvalid), .axi_rdata(rdata), .axi_rid(rid),
        .axi_rlast(rlast), .axi_rvalid(rvalid)
    );

    always @(posedge clk) begin
        rom_rsp_valid <= resetn && rom_valid;
        ram_rsp_valid <= resetn && ram_valid;
        mmio_rsp_valid <= resetn && mmio_valid;
        if (rom_valid) rom_rsp_data <= 32'hcafe_0000 | rom_addr;
        if (ram_valid) ram_rsp_data <= 32'hbeef_0000 | ram_addr;
        if (mmio_valid) mmio_rsp_data <= 32'h5a5a_0000 | mmio_addr;

        rvalid <= 1'b0;
        wready <= 1'b0;
        if (!resetn) begin
            read_pending <= 1'b0;
            write_pending <= 1'b0;
        end else begin
            if (arvalid && !read_pending) begin
                if (arlen !== 4'd0 || araddr[2:0] !== 3'b0) begin
                    failures = failures + 1;
                    $display("FAIL: DDR read command addr=%x len=%x", araddr, arlen);
                end
                read_pending <= 1'b1;
                saved_read_addr <= araddr;
                saved_read_id <= arid;
            end else if (read_pending) begin
                rdata <= memory[saved_read_addr[4:3]];
                rid <= saved_read_id;
                rlast <= 1'b1;
                rvalid <= 1'b1;
                read_pending <= 1'b0;
            end

            if (awvalid && !write_pending) begin
                if (awlen !== 4'd0 || awaddr[2:0] !== 3'b0) begin
                    failures = failures + 1;
                    $display("FAIL: DDR write command addr=%x len=%x", awaddr, awlen);
                end
                write_pending <= 1'b1;
                saved_write_addr <= awaddr;
            end else if (write_pending) begin
                for (byte_index = 0; byte_index < 16; byte_index = byte_index + 1)
                    if (wstrb[byte_index])
                        memory[saved_write_addr[4:3]][byte_index*8 +: 8] <=
                            wdata[byte_index*8 +: 8];
                wid <= awid;
                wlast <= 1'b1;
                wready <= 1'b1;
                write_pending <= 1'b0;
            end
        end
    end

    task inst_read;
        input [31:0] addr;
        input [31:0] expected;
        input expected_error;
        begin
            @(negedge clk);
            i_addr = addr;
            i_valid = 1'b1;
            while (!i_ready) @(negedge clk);
            @(negedge clk);
            i_valid = 1'b0;
            while (!i_rsp_valid) @(negedge clk);
            if (i_rsp_data !== expected || i_rsp_error !== expected_error) begin
                failures = failures + 1;
                $display("FAIL: I addr=%x data=%x error=%b", addr,
                         i_rsp_data, i_rsp_error);
            end else $display("PASS: I addr=%x", addr);
        end
    endtask

    task data_access;
        input do_write;
        input [31:0] addr;
        input [31:0] store_data;
        input [3:0] strobe;
        input [31:0] expected;
        input expected_error;
        begin
            @(negedge clk);
            d_write = do_write;
            d_addr = addr;
            d_wdata = store_data;
            d_wstrb = strobe;
            d_valid = 1'b1;
            while (!d_ready) @(negedge clk);
            @(negedge clk);
            d_valid = 1'b0;
            while (!d_rsp_valid) @(negedge clk);
            if ((!do_write && d_rsp_data !== expected) ||
                d_rsp_error !== expected_error) begin
                failures = failures + 1;
                $display("FAIL: D addr=%x data=%x error=%b", addr,
                         d_rsp_data, d_rsp_error);
            end else $display("PASS: D addr=%x write=%b", addr, do_write);
        end
    endtask

    initial begin
        memory[0] = 128'b0;
        memory[1] = 128'b0;
        memory[2] = 128'b0;
        memory[3] = 128'b0;
        memory[1][1*32 +: 32] = 32'h1122_3344;
        memory[2][3*32 +: 32] = 32'ha5a5_5a5a;
        memory[2][1*32 +: 32] = 32'hdead_beef;
        repeat (3) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
        i_valid = 1'b1;
        i_addr = 32'h4000_0014;
        #1;
        if (i_ready) begin
            failures = failures + 1;
            $display("FAIL: DDR request accepted before init");
        end
        i_valid = 1'b0;
        ddr_init_done = 1'b1;

        inst_read(32'h0000_0020, 32'hcafe_0020, 1'b0);
        data_access(1'b0, 32'h0000_0020, 32'b0, 4'b0,
                    32'hbeef_0020, 1'b0);
        data_access(1'b0, 32'h1000_0004, 32'b0, 4'b0,
                    32'h5a5a_0004, 1'b0);
        inst_read(32'h4000_0014, 32'h1122_3344, 1'b0);
        data_access(1'b0, 32'h4000_002c, 32'b0, 4'b0,
                    32'ha5a5_5a5a, 1'b0);
        data_access(1'b1, 32'h4000_0025, 32'h0000_aa00, 4'b0010,
                    32'b0, 1'b0);
        data_access(1'b0, 32'h4000_0024, 32'b0, 4'b0,
                    32'hdead_aaef, 1'b0);
        inst_read(32'h6000_0000, 32'b0, 1'b1);
        data_access(1'b0, 32'h6000_0000, 32'b0, 4'b0,
                    32'b0, 1'b1);

        if (failures == 0)
            $display("RESULT: PASS ddr_bus_path");
        else
            $display("RESULT: FAIL ddr_bus_path failures=%0d", failures);
        $finish;
    end

    initial begin
        #10000;
        $display("RESULT: TIMEOUT ddr_bus_path");
        $finish;
    end
endmodule
