`timescale 1ns / 1ps

// Directed bridge test: reset during an unaccepted DDR read command, then
// simultaneous data/instruction reads with data priority and both responses.
module tb_ddr_bridge_reset_contention;
    reg clk = 1'b0;
    always #5 clk = ~clk;

    reg resetn = 1'b0;
    reg ddr_init_done = 1'b0;
    reg inst_req_valid = 1'b0;
    reg [31:0] inst_req_addr = 32'h14;
    wire inst_req_ready, inst_rsp_valid, inst_rsp_error;
    wire [31:0] inst_rsp_rdata;
    reg data_req_valid = 1'b0;
    reg [31:0] data_req_addr = 32'h20;
    wire data_req_ready, data_rsp_valid, data_rsp_error;
    wire [31:0] data_rsp_rdata;
    wire [27:0] axi_araddr;
    wire [3:0] axi_aruser_id;
    wire axi_arvalid;
    reg axi_arready = 1'b0;
    reg [127:0] axi_rdata = 128'b0;
    reg axi_rvalid = 1'b0;

    dual_sram_to_pango_ddr_bridge dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(ddr_init_done),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr),
        .inst_req_ready(inst_req_ready), .inst_rsp_valid(inst_rsp_valid),
        .inst_rsp_rdata(inst_rsp_rdata), .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(1'b0),
        .data_req_size(2'd2), .data_req_addr(data_req_addr),
        .data_req_wdata(32'b0), .data_req_wstrb(4'b0),
        .data_req_ready(data_req_ready), .data_rsp_valid(data_rsp_valid),
        .data_rsp_rdata(data_rsp_rdata), .data_rsp_error(data_rsp_error),
        .axi_awready(1'b0), .axi_wready(1'b0),
        .axi_wusero_id(4'b0), .axi_wusero_last(1'b0),
        .axi_araddr(axi_araddr), .axi_aruser_id(axi_aruser_id),
        .axi_arvalid(axi_arvalid), .axi_arready(axi_arready),
        .axi_rdata(axi_rdata), .axi_rid(4'b0), .axi_rlast(1'b1),
        .axi_rvalid(axi_rvalid)
    );

    initial begin
        #1000;
        $fatal(1, "RESULT: FAIL bridge reset/contention timeout");
    end

    initial begin
        repeat (3) @(negedge clk);
        resetn = 1'b1;
        inst_req_valid = 1'b1;
        data_req_valid = 1'b1;
        #1;
        if (inst_req_ready !== 1'b0 || data_req_ready !== 1'b0)
            $fatal(1, "RESULT: FAIL accepted request before DDR init");
        $display("CHECK: both requests blocked before DDR init");

        ddr_init_done = 1'b1;
        #1;
        if (data_req_ready !== 1'b1 || inst_req_ready !== 1'b0)
            $fatal(1, "RESULT: FAIL data priority before reset");
        @(posedge clk); // The data read is accepted; its AR command is held.
        @(negedge clk);
        data_req_valid = 1'b0;
        #1;
        if (axi_arvalid !== 1'b1 || axi_araddr !== 28'h10 ||
            axi_aruser_id !== 4'd1)
            $fatal(1, "RESULT: FAIL missing pending data AR before reset");

        resetn = 1'b0;
        ddr_init_done = 1'b0;
        inst_req_valid = 1'b0;
        @(posedge clk);
        #1;
        if (axi_arvalid !== 1'b0 || data_rsp_valid !== 1'b0 ||
            inst_rsp_valid !== 1'b0)
            $fatal(1, "RESULT: FAIL stale bridge command/response after reset");
        $display("CHECK: in-flight read canceled by reset");

        @(negedge clk);
        resetn = 1'b1;
        inst_req_valid = 1'b1;
        data_req_valid = 1'b1;
        #1;
        if (inst_req_ready !== 1'b0 || data_req_ready !== 1'b0)
            $fatal(1, "RESULT: FAIL accepted request before reinitialization");
        ddr_init_done = 1'b1;
        #1;
        if (data_req_ready !== 1'b1 || inst_req_ready !== 1'b0)
            $fatal(1, "RESULT: FAIL data priority after reset");
        @(posedge clk); // The data read wins again.
        @(negedge clk);
        data_req_valid = 1'b0;
        axi_arready = 1'b1;
        #1;
        if (axi_araddr !== 28'h10 || axi_aruser_id !== 4'd1)
            $fatal(1, "RESULT: FAIL data AR after reset");
        @(posedge clk); // AR accepted.
        @(negedge clk);
        axi_rdata = {96'b0, 32'haabb_ccdd};
        axi_rvalid = 1'b1;
        @(posedge clk); // Data response captured.
        @(negedge clk);
        axi_rvalid = 1'b0;
        if (data_rsp_valid !== 1'b1 || data_rsp_error !== 1'b0 ||
            data_rsp_rdata !== 32'haabb_ccdd || inst_rsp_valid !== 1'b0)
            $fatal(1, "RESULT: FAIL data response after reset");
        $display("CHECK: data request completed before held instruction");

        @(posedge clk); // Response retires; bridge returns to IDLE.
        @(negedge clk);
        #1;
        if (inst_req_ready !== 1'b1)
            $fatal(1, "RESULT: FAIL held instruction was not accepted");
        @(posedge clk); // Instruction request accepted.
        @(negedge clk);
        inst_req_valid = 1'b0;
        #1;
        if (axi_arvalid !== 1'b1 || axi_araddr !== 28'h08 ||
            axi_aruser_id !== 4'd0)
            $fatal(1, "RESULT: FAIL instruction AR after data response");
        @(posedge clk); // AR accepted.
        @(negedge clk);
        axi_rdata = {64'b0, 32'h1122_3344, 32'b0}; // lane 1
        axi_rvalid = 1'b1;
        @(posedge clk);
        @(negedge clk);
        axi_rvalid = 1'b0;
        if (inst_rsp_valid !== 1'b1 || inst_rsp_error !== 1'b0 ||
            inst_rsp_rdata !== 32'h1122_3344 || data_rsp_valid !== 1'b0)
            $fatal(1, "RESULT: FAIL held instruction response");
        $display("RESULT: PASS bridge reset cancellation and data-priority contention");
        $finish;
    end
endmodule
