`timescale 1ns / 1ps

module tb_data_bus_interconnect;
    reg clk;
    reg resetn;

    reg         m_req_valid;
    reg         m_req_write;
    reg  [ 1:0] m_req_size;
    reg  [31:0] m_req_addr;
    reg  [31:0] m_req_wdata;
    reg  [ 3:0] m_req_wstrb;
    wire        m_req_ready;
    wire        m_rsp_valid;
    wire [31:0] m_rsp_rdata;
    wire        m_rsp_error;

    wire        ram_req_valid;
    wire        ram_req_write;
    wire [ 1:0] ram_req_size;
    wire [31:0] ram_req_addr;
    wire [31:0] ram_req_wdata;
    wire [ 3:0] ram_req_wstrb;
    wire        ram_req_ready;
    reg         ram_rsp_valid;
    reg  [31:0] ram_rsp_rdata;
    wire        ram_rsp_error;

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

    integer failures;
    integer ram_request_count;
    reg [31:0] observed_data;
    reg        observed_error;

    assign ram_req_ready = 1'b1;
    assign ram_rsp_error = 1'b0;

    data_bus_interconnect #(
        .RAM_BASE      (32'h8000_0000),
        .RAM_ADDR_MASK (32'hffff_c000),
        .MMIO_BASE     (32'h1000_0000),
        .MMIO_ADDR_MASK(32'hffff_f000)
    ) dut (
        .clk            (clk),
        .resetn         (resetn),
        .m_req_valid    (m_req_valid),
        .m_req_write    (m_req_write),
        .m_req_size     (m_req_size),
        .m_req_addr     (m_req_addr),
        .m_req_wdata    (m_req_wdata),
        .m_req_wstrb    (m_req_wstrb),
        .m_req_ready    (m_req_ready),
        .m_rsp_valid    (m_rsp_valid),
        .m_rsp_rdata    (m_rsp_rdata),
        .m_rsp_error    (m_rsp_error),
        .ram_req_valid  (ram_req_valid),
        .ram_req_write  (ram_req_write),
        .ram_req_size   (ram_req_size),
        .ram_req_addr   (ram_req_addr),
        .ram_req_wdata  (ram_req_wdata),
        .ram_req_wstrb  (ram_req_wstrb),
        .ram_req_ready  (ram_req_ready),
        .ram_rsp_valid  (ram_rsp_valid),
        .ram_rsp_rdata  (ram_rsp_rdata),
        .ram_rsp_error  (ram_rsp_error),
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
        .ddr_req_ready  (1'b0),
        .uart_req_valid(), .uart_req_write(), .uart_req_size(),
        .uart_req_addr(), .uart_req_wdata(), .uart_req_wstrb(),
        .uart_req_ready(1'b0), .uart_rsp_valid(1'b0),
        .uart_rsp_rdata(32'd0), .uart_rsp_error(1'b0),
        .ddr_rsp_valid  (1'b0),
        .ddr_rsp_rdata  (32'b0),
        .ddr_rsp_error  (1'b0)
    );

    simple_mmio u_mmio (
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
        .rsp_error (mmio_rsp_error)
    );

    // 一拍响应的 RAM 模型；返回值包含局部地址，便于检查地址平移。
    always @(posedge clk) begin
        if (!resetn) begin
            ram_rsp_valid     <= 1'b0;
            ram_rsp_rdata     <= 32'b0;
            ram_request_count <= 0;
        end else begin
            ram_rsp_valid <= ram_req_valid && ram_req_ready;
            if (ram_req_valid && ram_req_ready) begin
                ram_rsp_rdata <= 32'ha500_0000 | ram_req_addr;
                ram_request_count <= ram_request_count + 1;
            end
        end
    end

    always begin
        #5 clk = ~clk;
    end

    task transact;
        input        write_enable;
        input [31:0] address;
        input [31:0] write_data;
        input [ 3:0] write_strobe;
        begin
            @(negedge clk);
            m_req_valid = 1'b1;
            m_req_write = write_enable;
            m_req_addr  = address;
            m_req_wdata = write_data;
            m_req_wstrb = write_strobe;
            while (!m_req_ready)
                @(negedge clk);

            @(negedge clk);
            m_req_valid = 1'b0;
            while (!m_rsp_valid)
                @(negedge clk);
            observed_data  = m_rsp_rdata;
            observed_error = m_rsp_error;
        end
    endtask

    task expect_response;
        input [31:0] expected_data;
        input        expected_error;
        input [8*48-1:0] test_name;
        begin
            if ((observed_data !== expected_data) ||
                (observed_error !== expected_error)) begin
                failures = failures + 1;
                $display("FAIL: %0s data=%08x expected=%08x error=%b expected=%b",
                         test_name, observed_data, expected_data,
                         observed_error, expected_error);
            end else begin
                $display("PASS: %0s", test_name);
            end
        end
    endtask

    initial begin
        clk               = 1'b0;
        resetn            = 1'b0;
        m_req_valid       = 1'b0;
        m_req_write       = 1'b0;
        m_req_size        = 2'd2;
        m_req_addr        = 32'b0;
        m_req_wdata       = 32'b0;
        m_req_wstrb       = 4'b0;
        failures          = 0;
        observed_data     = 32'b0;
        observed_error    = 1'b0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;

        transact(1'b0, 32'h8000_0020, 32'b0, 4'b0000);
        expect_response(32'ha500_0020, 1'b0, "RAM base address translation");

        transact(1'b0, 32'h8000_3ffc, 32'b0, 4'b0000);
        expect_response(32'ha500_3ffc, 1'b0, "RAM upper boundary");

        transact(1'b1, 32'h1000_0000, 32'hdead_beef, 4'b1111);
        expect_response(32'h0000_0000, 1'b0, "MMIO scratch write");

        transact(1'b0, 32'h1000_0000, 32'b0, 4'b0000);
        expect_response(32'hdead_beef, 1'b0, "MMIO scratch read");

        transact(1'b1, 32'h1000_0001, 32'h0000_aa00, 4'b0010);
        expect_response(32'hdead_beef, 1'b0, "MMIO byte write");

        transact(1'b0, 32'h1000_0000, 32'b0, 4'b0000);
        expect_response(32'hdead_aaef, 1'b0, "MMIO byte write result");

        transact(1'b0, 32'h1000_0004, 32'b0, 4'b0000);
        expect_response(32'h4d4d_494f, 1'b0, "MMIO ID register");

        transact(1'b1, 32'h1000_0004, 32'h1234_5678, 4'b1111);
        expect_response(32'h4d4d_494f, 1'b1, "MMIO read-only write error");

        transact(1'b0, 32'h8000_4000, 32'b0, 4'b0000);
        expect_response(32'h0000_0000, 1'b1, "Address immediately above RAM");

        transact(1'b0, 32'h2000_0000, 32'b0, 4'b0000);
        expect_response(32'h0000_0000, 1'b1, "Unmapped address error");

        if (ram_request_count !== 2) begin
            failures = failures + 1;
            $display("FAIL: RAM selected %0d times, expected 2",
                     ram_request_count);
        end

        if (failures == 0)
            $display("RESULT: PASS data_bus_interconnect");
        else
            $display("RESULT: FAIL data_bus_interconnect failures=%0d",
                     failures);
        $finish;
    end

endmodule
