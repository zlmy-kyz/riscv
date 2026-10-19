`timescale 1ns/1ps
// Task032 second timing repair: minimal combinational I-tag lookup group.
//
// Only the real bridge is instantiated (x32, INST_LINE_BUFFER_ENABLE=1). There is
// no CPU, no program, no DDR traffic and no FSM activity: both request ports stay
// idle and the DDR user port never handshakes, so the bridge remains in IDLE and
// the I tag/valid registers are never written by the bridge after reset.
//
// Test preparation deposits inst_line_tag / inst_line_valid (no force, no writes to
// hit/state/ready or any other DUT output). Every valid row keeps the real fill
// invariant tag = (upper_tag << 6) | row_index, which is what the RTL relies on.
// Expected hits come from this testbench's own prepared arrays; the DUT hit output
// is only ever compared against them.
module tb_inst_tag_lookup;
    GTP_GRS GRS_INST (.GRS_N(1'b1));
    localparam integer TAG_BITS  = 27;
    localparam integer HIGH_BITS = 21;
    localparam [20:0] PATTERN_A  = 21'h000000;   // all zero
    localparam [20:0] PATTERN_B  = 21'h1FFFFF;   // all ones
    localparam [20:0] PATTERN_C  = 21'h055555;   // alternating

    reg clk = 0;
    always #5 clk = ~clk;
    reg resetn = 0;
    reg init_done = 0;

    reg  [31:0] inst_req_addr = 32'h4000_0000;
    reg         inst_req_valid = 1'b0;
    reg  [31:0] data_req_addr = 32'h0;
    reg         data_req_valid = 1'b0;
    reg         data_req_write = 1'b0;
    reg  [1:0]  data_req_size = 2'd2;
    reg  [31:0] data_req_wdata = 32'h0;
    reg  [3:0]  data_req_wstrb = 4'h0;
    wire        inst_req_ready, inst_rsp_valid, inst_rsp_error;
    wire [31:0] inst_rsp_rdata, data_rsp_rdata;
    wire        data_req_ready, data_rsp_valid, data_rsp_error, write_buffer_busy;
    wire [27:0] awaddr, araddr;
    wire        awuser_ap, awvalid, aruser_ap, arvalid;
    wire [3:0]  awuser_id, awlen, aruser_id, arlen;
    wire [255:0] wdata;
    wire [31:0] wstrb;

    dual_sram_to_pango_ddr_bridge #(.MEM_DQ_WIDTH(32), .INST_LINE_BUFFER_ENABLE(1)) dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(init_done), .write_buffer_busy(write_buffer_busy),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr), .inst_req_ready(inst_req_ready),
        .inst_rsp_valid(inst_rsp_valid), .inst_rsp_rdata(inst_rsp_rdata), .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(data_req_write), .data_req_size(data_req_size),
        .data_req_addr(data_req_addr), .data_req_wdata(data_req_wdata), .data_req_wstrb(data_req_wstrb),
        .data_req_ready(data_req_ready), .data_rsp_valid(data_rsp_valid), .data_rsp_rdata(data_rsp_rdata),
        .data_rsp_error(data_rsp_error),
        .axi_awaddr(awaddr), .axi_awuser_ap(awuser_ap), .axi_awuser_id(awuser_id), .axi_awlen(awlen),
        .axi_awready(1'b0), .axi_awvalid(awvalid), .axi_wdata(wdata), .axi_wstrb(wstrb),
        .axi_wready(1'b0), .axi_wusero_id(4'd1), .axi_wusero_last(1'b0),
        .axi_araddr(araddr), .axi_aruser_ap(aruser_ap), .axi_aruser_id(aruser_id), .axi_arlen(arlen),
        .axi_arready(1'b0), .axi_arvalid(arvalid), .axi_rdata(256'b0), .axi_rid(4'd0),
        .axi_rlast(1'b0), .axi_rvalid(1'b0));

    reg [20:0] tab_upper [0:63];
    reg        tab_valid [0:63];
    reg [63:0] tab_vbits;
    integer    fd, i, r, b, k, idx;
    integer    scenario = 0;
    integer    det_obs = 0, rnd_obs = 0, mismatches = 0, hits = 0, misses = 0;
    reg [31:0] x, seed;
    reg [20:0] base, req_upper;
    string     lookup_path;

    function automatic [31:0] lcg(input [31:0] value);
        lcg = value * 32'd1103515245 + 32'd12345;
    endfunction

    function automatic [20:0] pattern_of(input integer row);
        pattern_of = (row % 3 == 0) ? PATTERN_A : (row % 3 == 1) ? PATTERN_B : PATTERN_C;
    endfunction

    // Test preparation only: deposit the design fill invariant for one row.
    task automatic deposit_row(input integer row);
        begin
            dut.inst_line_tag[row] = {tab_upper[row], row[5:0]};
            dut.inst_line_valid[row] = tab_valid[row];
        end
    endtask

    task automatic deposit_all;
        begin
            for (i = 0; i < 64; i = i + 1) deposit_row(i);
        end
    endtask

    // kind: 0 det_hit, 1 det_valid0, 2 det_flip, 3 random
    task automatic observe(input integer kind, input integer param, input integer index,
                           input [20:0] request_upper);
        reg expected, observed;
        begin
            inst_req_addr = {request_upper, index[5:0], 5'b0};
            #1;
            expected = tab_valid[index] && (tab_upper[index] == request_upper);
            observed = dut.inst_line_hit;
            if (dut.state !== 3'd0)
                $fatal(1, "RESULT: FAIL tag_lookup bridge left IDLE");
            if (awvalid || arvalid || write_buffer_busy)
                $fatal(1, "RESULT: FAIL tag_lookup DDR activity");
            if (dut.inst_line_index !== index[5:0])
                $fatal(1, "RESULT: FAIL tag_lookup request index decode");
            if (observed !== expected) begin
                mismatches = mismatches + 1;
                $fatal(1, "RESULT: FAIL tag_lookup scenario=%0d kind=%0d index=%0d req=%05x sel=%06x valid=%0b exp=%0b obs=%0b",
                       scenario, kind, index, request_upper,
                       {tab_upper[index], index[5:0]}, tab_valid[index], expected, observed);
            end
            if (expected) hits = hits + 1;
            else          misses = misses + 1;
            $fdisplay(fd, "OBS %0d %0d %0d %0d %05x %06x %0b %0b %0b", scenario, kind, param, index,
                      request_upper, {tab_upper[index], index[5:0]}, tab_valid[index], expected, observed);
            scenario = scenario + 1;
            if (kind == 3) rnd_obs = rnd_obs + 1;
            else           det_obs = det_obs + 1;
        end
    endtask

    task automatic dump_table(input [31:0] seed_value);
        begin
            tab_vbits = 64'b0;
            for (i = 0; i < 64; i = i + 1) begin
                tab_vbits[i] = tab_valid[i];
            end
            $fwrite(fd, "TBL %0d", seed_value);
            for (i = 0; i < 64; i = i + 1) $fwrite(fd, " %06x", tab_upper[i]);
            $fwrite(fd, " %016x\n", tab_vbits);
        end
    endtask

    initial begin
        if (!$value$plusargs("LOOKUP_LOG=%s", lookup_path))
            $fatal(1, "RESULT: FAIL missing +LOOKUP_LOG");
        fd = $fopen(lookup_path, "w");
        if (!fd) $fatal(1, "RESULT: FAIL cannot open lookup log");
        repeat (4) @(negedge clk);
        resetn = 1'b1;
        init_done = 1'b1;
        repeat (2) @(negedge clk);
        #1;
        if (dut.state !== 3'd0) $fatal(1, "RESULT: FAIL tag_lookup bridge not IDLE after reset");

        // ---- deterministic: 64 rows x (hit + selected-valid0 + 21 high-bit flips)
        for (r = 0; r < 64; r = r + 1) begin
            base = pattern_of(r);
            for (i = 0; i < 64; i = i + 1) begin
                tab_upper[i] = base;      // all rows share this upper tag
                tab_valid[i] = 1'b1;      // and are valid: index select must isolate the request
            end
            deposit_all();
            observe(0, 0, r, base);                       // matching row -> hit
            tab_valid[r] = 1'b0; deposit_row(r);
            observe(1, 0, r, base);                       // selected row invalid -> miss
            tab_valid[r] = 1'b1; deposit_row(r);
            for (b = 0; b < HIGH_BITS; b = b + 1) begin
                tab_upper[r] = base ^ (21'd1 << b); deposit_row(r);
                observe(2, b, r, base);                   // one high tag bit wrong -> miss
            end
            tab_upper[r] = base; deposit_row(r);
        end

        // ---- fixed seed 20261014: 8 random well-formed tables per row
        for (r = 0; r < 64; r = r + 1) begin
            for (k = 0; k < 8; k = k + 1) begin
                seed = 20261014 + r * 8 + k;
                x = seed;
                for (i = 0; i < 64; i = i + 1) begin
                    x = lcg(x); tab_upper[i] = x[31:11];
                end
                for (i = 0; i < 64; i = i + 1) begin
                    x = lcg(x); tab_valid[i] = x[0];
                end
                x = lcg(x); idx = x[5:0];
                x = lcg(x); req_upper = x[31:11];
                if (k % 2 == 0) req_upper = tab_upper[idx];
                else            req_upper = tab_upper[idx] ^ 21'd1;
                deposit_all();
                dump_table(seed);
                observe(3, seed, idx, req_upper);
            end
        end

        if (mismatches != 0) $fatal(1, "RESULT: FAIL tag_lookup mismatches");
        if (det_obs < 64 * 23) $fatal(1, "RESULT: FAIL tag_lookup deterministic coverage");
        if (rnd_obs < 512) $fatal(1, "RESULT: FAIL tag_lookup random coverage");
        $fdisplay(fd, "LOOKUP-SUMMARY det=%0d rnd=%0d mismatches=%0d hits=%0d misses=%0d rows=64 high_bits=%0d seed=20261014",
                  det_obs, rnd_obs, mismatches, hits, misses, HIGH_BITS);
        $display("RESULT: PASS tag_lookup det=%0d rnd=%0d mismatches=%0d hits=%0d misses=%0d",
                 det_obs, rnd_obs, mismatches, hits, misses);
        $fclose(fd);
        $finish;
    end

    initial begin #2000000; $fatal(1, "RESULT: FAIL tag_lookup watchdog"); end
endmodule
