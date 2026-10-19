`timescale 1ns/1ps

module tb_ddr_bridge_x32;
    reg clk = 0;
    always #5 clk = ~clk;
    reg resetn = 0;
    reg ddr_init_done = 0;
    reg inst_req_valid = 0;
    reg [31:0] inst_req_addr = 0;
    wire inst_req_ready, inst_rsp_valid, inst_rsp_error;
    wire [31:0] inst_rsp_rdata;
    reg data_req_valid = 0, data_req_write = 0;
    reg [31:0] data_req_addr = 0, data_req_wdata = 0;
    reg [3:0] data_req_wstrb = 0;
    wire data_req_ready, data_rsp_valid, data_rsp_error;
    wire [31:0] data_rsp_rdata;
    wire [27:0] axi_awaddr, axi_araddr;
    wire axi_awuser_ap, axi_awvalid, axi_aruser_ap, axi_arvalid;
    wire [3:0] axi_awuser_id, axi_awlen, axi_aruser_id, axi_arlen;
    wire [255:0] axi_wdata;
    wire [31:0] axi_wstrb;
    reg axi_awready = 1, axi_wready = 1, axi_arready = 1;
    reg [255:0] axi_rdata = 0;
    reg [3:0] axi_rid = 0;
    reg axi_rlast = 0, axi_rvalid = 0;

    dual_sram_to_pango_ddr_bridge #(.MEM_DQ_WIDTH(32)) dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(ddr_init_done),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr),
        .inst_req_ready(inst_req_ready), .inst_rsp_valid(inst_rsp_valid),
        .inst_rsp_rdata(inst_rsp_rdata), .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(data_req_write),
        .data_req_size(2'b10), .data_req_addr(data_req_addr),
        .data_req_wdata(data_req_wdata), .data_req_wstrb(data_req_wstrb),
        .data_req_ready(data_req_ready), .data_rsp_valid(data_rsp_valid),
        .data_rsp_rdata(data_rsp_rdata), .data_rsp_error(data_rsp_error),
        .axi_awaddr(axi_awaddr), .axi_awuser_ap(axi_awuser_ap),
        .axi_awuser_id(axi_awuser_id), .axi_awlen(axi_awlen),
        .axi_awready(axi_awready), .axi_awvalid(axi_awvalid),
        .axi_wdata(axi_wdata), .axi_wstrb(axi_wstrb),
        .axi_wready(axi_wready), .axi_wusero_id(4'b0),
        .axi_wusero_last(1'b1), .axi_araddr(axi_araddr),
        .axi_aruser_ap(axi_aruser_ap), .axi_aruser_id(axi_aruser_id),
        .axi_arlen(axi_arlen), .axi_arready(axi_arready),
        .axi_arvalid(axi_arvalid), .axi_rdata(axi_rdata),
        .axi_rid(axi_rid), .axi_rlast(axi_rlast), .axi_rvalid(axi_rvalid)
    );

    task fail(input [255:0] message);
        begin $display("RESULT: FAIL %0s", message); $finish; end
    endtask

    task read_inst(input [31:0] addr, input [27:0] ctrl_addr,
                   input [31:0] expected, input miss);
        begin
            @(negedge clk);
            inst_req_addr = addr;
            inst_req_valid = 1;
            if (!inst_req_ready) fail("inst request not ready");
            @(posedge clk); #1;
            inst_req_valid = 0;
            if (miss) begin
                if (!axi_arvalid || axi_araddr !== ctrl_addr || axi_aruser_id !== 0)
                    fail("inst AR address/ID mismatch");
                @(posedge clk); #1;
                axi_rdata = 0;
                axi_rdata[addr[4:2]*32 +: 32] = expected;
                axi_rid = 0; axi_rlast = 1; axi_rvalid = 1;
                @(posedge clk); #1; axi_rvalid = 0;
            end else if (axi_arvalid) fail("inst cache miss unexpectedly");
            if (!inst_rsp_valid || inst_rsp_rdata !== expected || inst_rsp_error)
                fail("inst read response mismatch");
            @(posedge clk); #1;
        end
    endtask

    task read_data(input [31:0] addr, input [27:0] ctrl_addr,
                   input [31:0] expected, input miss);
        begin
            @(negedge clk);
            data_req_addr = addr; data_req_write = 0; data_req_valid = 1;
            if (!data_req_ready) fail("data request not ready");
            @(posedge clk); #1; data_req_valid = 0;
            if (miss) begin
                if (!axi_arvalid || axi_araddr !== ctrl_addr || axi_aruser_id !== 1)
                    fail("data AR address/ID mismatch");
                @(posedge clk); #1;
                axi_rdata = 0;
                axi_rdata[addr[4:2]*32 +: 32] = expected;
                axi_rid = 1; axi_rlast = 1; axi_rvalid = 1;
                @(posedge clk); #1; axi_rvalid = 0;
            end else if (axi_arvalid) fail("data cache miss unexpectedly");
            if (!data_rsp_valid || data_rsp_rdata !== expected || data_rsp_error)
                fail("data read response mismatch");
            @(posedge clk); #1;
        end
    endtask

    task write_data(input [31:0] addr, input [27:0] ctrl_addr,
                    input [31:0] word, input [3:0] strobe);
        begin
            @(negedge clk);
            data_req_addr = addr; data_req_write = 1; data_req_valid = 1;
            data_req_wdata = word; data_req_wstrb = strobe;
            if (!data_req_ready) fail("write request not ready");
            @(posedge clk); #1; data_req_valid = 0;
            if (!axi_awvalid || axi_awaddr !== ctrl_addr ||
                axi_wdata[addr[4:2]*32 +: 32] !== word ||
                axi_wstrb !== (32'(strobe) << (addr[4:2]*4)))
                fail("write address/data/strobe mismatch");
            @(posedge clk); #1;
            if (!data_rsp_valid || data_rsp_error) fail("write response mismatch");
            @(posedge clk); #1;
        end
    endtask

    initial begin
        repeat (2) @(posedge clk); #1;
        resetn = 1; ddr_init_done = 1;
        read_inst(32'h0000_001c, 28'h0000000, 32'h11223344, 1);
        read_inst(32'h0000_001c, 28'h0000000, 32'h11223344, 0);
        read_inst(32'h2000_001c, 28'h8000000, 32'h55667788, 1);
        read_inst(32'h3fff_fffc, 28'hffffff8, 32'h13579bdf, 1);
        read_data(32'h0000_0018, 28'h0000000, 32'h99aabbcc, 1);
        read_data(32'h0000_0018, 28'h0000000, 32'h99aabbcc, 0);
        write_data(32'h0000_001c, 28'h0000000, 32'hdeadbeef, 4'b0101);
        read_data(32'h0000_0018, 28'h0000000, 32'h99aabbcc, 1);
        read_inst(32'h0000_001c, 28'h0000000, 32'h11223344, 1);
        $display("RESULT: PASS x32 DDR bridge lanes, high address, caches, write mask");
        $finish;
    end

    initial begin #10000; fail("timeout"); end
endmodule
