`timescale 1ns / 1ps

module tb_inst_bus_interconnect;
    reg clk;
    reg resetn;
    reg         m_req_valid;
    reg  [31:0] m_req_addr;
    wire        m_req_ready;
    wire        m_rsp_valid;
    wire [31:0] m_rsp_rdata;
    wire        m_rsp_error;

    wire        rom_req_valid;
    wire [31:0] rom_req_addr;
    wire        rom_req_ready;
    reg         rom_rsp_valid;
    reg  [31:0] rom_rsp_rdata;
    wire        rom_rsp_error;

    integer failures;
    integer rom_request_count;
    reg [31:0] observed_data;
    reg        observed_error;

    assign rom_req_ready = 1'b1;
    assign rom_rsp_error = 1'b0;

    inst_bus_interconnect #(
        .ROM_BASE     (32'h8000_0000),
        .ROM_ADDR_MASK(32'hffff_c000)
    ) dut (
        .clk           (clk),
        .resetn        (resetn),
        .m_req_valid   (m_req_valid),
        .m_req_addr    (m_req_addr),
        .m_req_ready   (m_req_ready),
        .m_rsp_valid   (m_rsp_valid),
        .m_rsp_rdata   (m_rsp_rdata),
        .m_rsp_error   (m_rsp_error),
        .rom_req_valid (rom_req_valid),
        .rom_req_addr  (rom_req_addr),
        .rom_req_ready (rom_req_ready),
        .rom_rsp_valid (rom_rsp_valid),
        .rom_rsp_rdata (rom_rsp_rdata),
        .rom_rsp_error (rom_rsp_error),
        .ddr_req_ready (1'b0),
        .ddr_rsp_valid (1'b0),
        .ddr_rsp_rdata (32'b0),
        .ddr_rsp_error (1'b0)
    );

    always begin
        #5 clk = ~clk;
    end

    // 一拍ROM响应模型，返回值携带局部地址。
    always @(posedge clk) begin
        if (!resetn) begin
            rom_rsp_valid     <= 1'b0;
            rom_rsp_rdata     <= 32'b0;
            rom_request_count <= 0;
        end else begin
            rom_rsp_valid <= rom_req_valid && rom_req_ready;
            if (rom_req_valid && rom_req_ready) begin
                rom_rsp_rdata <= 32'hcafe_0000 | rom_req_addr;
                rom_request_count <= rom_request_count + 1;
            end
        end
    end

    task fetch;
        input [31:0] address;
        begin
            @(negedge clk);
            m_req_valid = 1'b1;
            m_req_addr  = address;
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
        clk = 1'b0;
        resetn = 1'b0;
        m_req_valid = 1'b0;
        m_req_addr = 32'b0;
        failures = 0;
        observed_data = 32'b0;
        observed_error = 1'b0;

        repeat (3) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;

        fetch(32'h8000_0020);
        expect_response(32'hcafe_0020, 1'b0, "ROM base address translation");

        fetch(32'h8000_3ffc);
        expect_response(32'hcafe_3ffc, 1'b0, "ROM upper boundary");

        fetch(32'h0000_0020);
        expect_response(32'h0000_0000, 1'b1, "Old low-address alias rejected");

        fetch(32'h8000_4000);
        expect_response(32'h0000_0000, 1'b1, "Address immediately above ROM");

        if (rom_request_count !== 2) begin
            failures = failures + 1;
            $display("FAIL: ROM selected %0d times, expected 2",
                     rom_request_count);
        end

        if (failures == 0)
            $display("RESULT: PASS inst_bus_interconnect");
        else
            $display("RESULT: FAIL inst_bus_interconnect failures=%0d",
                     failures);
        $finish;
    end

endmodule
