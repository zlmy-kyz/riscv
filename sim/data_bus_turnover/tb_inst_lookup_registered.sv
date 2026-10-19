`timescale 1ns/1ps
// ============================================================================
// Task032 registered per-row I hit: minimal directed top level.
//
// Target RTL: myriscv/dual_sram_to_pango_ddr_bridge.v
//   SHA256 f14b16cb97fa24fd17050995a1b254933aea5bca3b4a071a33712c7a17c52ba0
//
// Only one real x32 bridge is instantiated (MEM_DQ_WIDTH=32,
// INST_LINE_BUFFER_ENABLE=1, DATA_LINE_BUFFER_ENABLE=1, POSTED_WRITE_ENABLE=1,
// remaining parameters default). icache/dcache vendor IP lives inside the
// bridge, so no behavioural RAM replaces it and no extra module is declared.
//
// TIMING CONVENTION (one driver process, no same-edge race)
//   * "cycle c" = the clock cycle between posedge c and posedge c+1.
//   * Everything is driven and sampled at the NEGEDGE in the middle of a cycle,
//     half a period before the sampling posedge. Values driven at the negedge of
//     cycle c are stable at the posedge that ends cycle c. Values sampled there
//     were already stable before that edch, i.e. they are cycle-c values.
//   * A handshake is logged in the cycle in which both sides were high, which is
//     also the cycle whose ending posedge completes it.
//
// GROUP A - registered tag snapshot. Only tag/valid are deposited (test
// preparation, performed while the bridge sits in its free front slot); state,
// ready, way_hit_q, the hit net and every DUT output are never forced or
// written. Every observation contains exactly one real accepted I request, and
// the live address is switched to a cached hit address immediately after
// acceptance, so the outcome of the following cycle can only come from the
// snapshot registered at the acceptance edge.
//
// GROUP B - real handshake/DRM/fill integration. The bridge is reset between the
// groups and the tables start empty; group B deposits nothing. A legal Pango
// user port model (no WVALID/BREADY/RREADY) drives AW/W and AR/R with full
// ownership and an independent byte memory.
//
// plusargs:
//   +LOOKUP_LOG=<path>   group A trace
//   +BUS_LOG=<path>      group B trace
// ============================================================================
module tb_inst_lookup_registered;
    GTP_GRS GRS_INST (.GRS_N(1'b1));

    localparam integer TAG_BITS  = 27;
    localparam integer HIGH_BITS = 21;
    localparam [20:0] PAT_ZERO = 21'h000000;
    localparam [20:0] PAT_ONES = 21'h1FFFFF;
    localparam [20:0] PAT_ALT  = 21'h055555;

    reg clk = 0;
    always #5 clk = ~clk;
    reg resetn = 0;
    reg init_done = 0;

    // ------------------------------------------------------------------ ports
    reg  [31:0] inst_req_addr  = 32'h4000_0000;
    reg         inst_req_valid = 1'b0;
    reg  [31:0] data_req_addr  = 32'h4000_0000;
    reg         data_req_valid = 1'b0;
    reg         data_req_write = 1'b0;
    reg  [1:0]  data_req_size  = 2'd2;
    reg  [31:0] data_req_wdata = 32'h0;
    reg  [3:0]  data_req_wstrb = 4'h0;
    wire        inst_req_ready, inst_rsp_valid, inst_rsp_error;
    wire [31:0] inst_rsp_rdata;
    wire        data_req_ready, data_rsp_valid, data_rsp_error;
    wire [31:0] data_rsp_rdata;
    wire        write_buffer_busy;
    wire [27:0] bus_awaddr, bus_araddr;
    wire        bus_awuser_ap, bus_awvalid, bus_aruser_ap, bus_arvalid;
    wire [3:0]  bus_awuser_id, bus_awlen, bus_aruser_id, bus_arlen;
    wire [255:0] bus_wdata;
    wire [31:0] bus_wstrb;

    // user port model drives (legal user port: no WVALID, no BREADY, no RREADY)
    reg         m_aw_ready = 1'b0;
    reg         m_w_ready  = 1'b0;
    reg         m_ar_ready = 1'b1;
    reg         m_rvalid   = 1'b0;
    reg  [255:0] m_rdata   = 256'b0;
    reg  [3:0]  m_rid      = 4'd0;
    reg         m_rlast    = 1'b0;

    dual_sram_to_pango_ddr_bridge #(
        .MEM_DQ_WIDTH(32),
        .INST_LINE_BUFFER_ENABLE(1),
        .DATA_LINE_BUFFER_ENABLE(1),
        .POSTED_WRITE_ENABLE(1)) dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(init_done),
        .write_buffer_busy(write_buffer_busy),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr),
        .inst_req_ready(inst_req_ready), .inst_rsp_valid(inst_rsp_valid),
        .inst_rsp_rdata(inst_rsp_rdata), .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(data_req_write),
        .data_req_size(data_req_size), .data_req_addr(data_req_addr),
        .data_req_wdata(data_req_wdata), .data_req_wstrb(data_req_wstrb),
        .data_req_ready(data_req_ready), .data_rsp_valid(data_rsp_valid),
        .data_rsp_rdata(data_rsp_rdata), .data_rsp_error(data_rsp_error),
        .axi_awaddr(bus_awaddr), .axi_awuser_ap(bus_awuser_ap),
        .axi_awuser_id(bus_awuser_id), .axi_awlen(bus_awlen),
        .axi_awready(m_aw_ready), .axi_awvalid(bus_awvalid),
        .axi_wdata(bus_wdata), .axi_wstrb(bus_wstrb), .axi_wready(m_w_ready),
        .axi_wusero_id(4'd1), .axi_wusero_last(m_w_ready),
        .axi_araddr(bus_araddr), .axi_aruser_ap(bus_aruser_ap),
        .axi_aruser_id(bus_aruser_id), .axi_arlen(bus_arlen),
        .axi_arready(m_ar_ready), .axi_arvalid(bus_arvalid),
        .axi_rdata(m_rdata), .axi_rid(m_rid), .axi_rlast(m_rlast),
        .axi_rvalid(m_rvalid));

    // ---------------------------------------------------------- cycle counter
    integer cyc = 0;
    always @(posedge clk) cyc = cyc + 1;

    // ======================================================================
    // memories and helper functions (declared before first use)
    // ======================================================================
    // One shared byte memory image: byte(addr*4 + i). addr counts 16-bit user
    // words, so the 32 bytes of one x32 beat are addr*4 + 0 .. addr*4 + 31.
    reg [7:0] a_dm [0:4095];
    reg [7:0] b_dm [0:4095];

    function automatic [255:0] a_line_data(input [27:0] addr);
        integer j, k;
        reg [31:0] word;
        begin
            a_line_data = 256'b0;
            for (j = 0; j < 8; j = j + 1) begin
                word = 32'b0;
                for (k = 0; k < 4; k = k + 1)
                    word[8*k +: 8] = a_dm[(addr*4 + j*4 + k) & 4095];
                a_line_data[j*32 +: 32] = word;
            end
        end
    endfunction

    function automatic [255:0] b_line_data(input [27:0] addr);
        integer j, k;
        reg [31:0] word;
        begin
            b_line_data = 256'b0;
            for (j = 0; j < 8; j = j + 1) begin
                word = 32'b0;
                for (k = 0; k < 4; k = k + 1)
                    word[8*k +: 8] = b_dm[(addr*4 + j*4 + k) & 4095];
                b_line_data[j*32 +: 32] = word;
            end
        end
    endfunction

    function automatic [31:0] lcg(input [31:0] value);
        lcg = value * 32'd1103515245 + 32'd12345;
    endfunction

    // ======================================================================
    // GROUP A
    // ======================================================================
    reg [26:0] a_tag   [0:63];
    reg        a_valid [0:63];
    reg [63:0] a_vbits;
    reg [63:0] a_row_mask;
    integer    a_fd, a_scen = 0, a_det = 0, a_rnd = 0, a_hits = 0, a_misses = 0;
    integer    a_mism = 0, a_cont = 0, a_rows_seen = 0;
    string     a_path;

    function automatic [20:0] a_pat(input integer row);
        a_pat = (row % 3 == 0) ? PAT_ZERO : (row % 3 == 1) ? PAT_ONES : PAT_ALT;
    endfunction

    // test preparation only: deposit the real fill invariant for all 64 rows
    task automatic a_deposit_all;
        integer i;
        begin
            for (i = 0; i < 64; i = i + 1) begin
                dut.inst_line_tag[i]   = a_tag[i];
                dut.inst_line_valid[i] = a_valid[i];
            end
        end
    endtask

    task automatic a_reset_arrays;
        integer i;
        begin
            for (i = 0; i < 64; i = i + 1) begin
                a_tag[i]   = 27'b0;
                a_valid[i] = 1'b0;
            end
        end
    endtask

    // wait until the front slot is free and nothing is in flight
    task automatic a_wait_idle;
        begin
            @(negedge clk);
            while (!(inst_req_ready && !inst_rsp_valid && !bus_arvalid && !m_rvalid))
                @(negedge clk);
        end
    endtask

    // kind 0 = det hit, 1 = det selected-valid0 miss, 2 = det flipped high bit, 3 = random
    task automatic a_observe(input integer kind, input integer param, input integer row,
                             input [20:0] req_upper);
        integer accept_edge, decoy_row, cont_taken;
        reg [26:0] req_tag;
        reg expected, obs_resp, obs_ar, ready_now;
        begin
            req_tag    = {req_upper, row[5:0]};
            expected   = a_valid[row] && (a_tag[row] == req_tag);
            decoy_row  = (row + 1) & 63;
            cont_taken = 0;
            a_wait_idle();
            a_deposit_all();
            inst_req_addr  = {req_upper, row[5:0], 5'b0};
            inst_req_valid = 1'b1;
            if (!inst_req_ready)
                $fatal(1, "RESULT: FAIL inst_lookup A front slot not free before accept");
            accept_edge = cyc + 1;                 // acceptance at the posedge ending this cycle
            @(negedge clk);                        // now inside the outcome cycle (cyc == accept_edge)
            // switch the live address to a cached hit address: the outcome of this
            // cycle can only come from the snapshot registered at the accept edge
            inst_req_addr = {a_tag[decoy_row][26:6], decoy_row[5:0], 5'b0};
            obs_resp  = inst_rsp_valid;
            obs_ar    = bus_arvalid;
            ready_now = inst_req_ready;
            if (obs_resp && obs_ar)
                $fatal(1, "RESULT: FAIL inst_lookup A response and AR in the same outcome cycle");
            if (!obs_resp && !obs_ar)
                $fatal(1, "RESULT: FAIL inst_lookup A no response and no AR after acceptance");
            if (obs_resp !== expected) begin
                a_mism = a_mism + 1;
                $fatal(1, "RESULT: FAIL inst_lookup A row=%0d kind=%0d observed=%0b expected=%0b",
                       row, kind, obs_resp, expected);
            end
            if (obs_resp) a_hits = a_hits + 1; else a_misses = a_misses + 1;
            if (kind == 3) a_rnd = a_rnd + 1; else a_det = a_det + 1;
            if (!a_row_mask[row]) begin
                a_row_mask[row] = 1'b1;
                a_rows_seen = a_rows_seen + 1;
            end
            $fdisplay(a_fd, "A %0d %0d %0d %0d %07x %07x %0b %0b %0b %0s %0d %0d",
                      a_scen, kind, param, row, req_tag, a_tag[row], a_valid[row], expected,
                      (obs_resp ? 1'b1 : 1'b0), (obs_resp ? "RESP" : "AR"), accept_edge, cyc);
            a_scen = a_scen + 1;
            if (!obs_resp) begin
                // miss: earliest legal AR/R same-cycle return, captured in this cycle
                m_rvalid = 1'b1;
                m_rdata  = a_line_data(bus_araddr);
                m_rid    = bus_aruser_id;
                m_rlast  = 1'b1;
            end else begin
                cont_taken = ready_now;            // a new I request is accepted at this edge
            end
            @(negedge clk);
            m_rvalid = 1'b0;
            m_rlast  = 1'b0;
            inst_req_valid = 1'b0;
            if (!obs_resp) begin
                if (inst_rsp_valid !== 1'b1)
                    $fatal(1, "RESULT: FAIL inst_lookup A miss response missing");
            end else if (cont_taken) begin
                a_cont = a_cont + 1;
                if (inst_rsp_valid !== 1'b1)
                    $fatal(1, "RESULT: FAIL inst_lookup A continuation decoy did not hit");
                $fdisplay(a_fd, "ACONT %0d %0d %0d", a_scen, accept_edge + 1, cyc);
            end
            @(negedge clk);
        end
    endtask

    task automatic a_emit_table(input integer seed, input integer row, input [20:0] req_upper,
                                input integer decoy_row);
        integer i;
        begin
            a_vbits = 64'b0;
            for (i = 0; i < 64; i = i + 1) a_vbits[i] = a_valid[i];
            $fwrite(a_fd, "ATBL %0d %0d", seed, row);
            for (i = 0; i < 64; i = i + 1) $fwrite(a_fd, " %07x", a_tag[i]);
            $fwrite(a_fd, " %016x %05x %0d %05x\n", a_vbits, req_upper, decoy_row,
                    a_tag[decoy_row][26:6]);
        end
    endtask

    task automatic a_run;
        integer r, b, k, i, idx, decoy_row;
        reg [31:0] x, seed;
        reg [20:0] base, ru;
        begin
            // deterministic: 64 rows x (hit + selected valid0 + 21 flipped high bits)
            for (r = 0; r < 64; r = r + 1) begin
                base = a_pat(r);
                for (i = 0; i < 64; i = i + 1) begin
                    a_tag[i]   = {base, i[5:0]};
                    a_valid[i] = 1'b1;
                end
                a_observe(0, 0, r, base);
                a_valid[r] = 1'b0;
                a_observe(1, 0, r, base);
                a_valid[r] = 1'b1;
                for (b = 0; b < HIGH_BITS; b = b + 1) begin
                    a_tag[r] = {(base ^ (21'd1 << b)), r[5:0]};
                    a_observe(2, b, r, base);
                end
                a_tag[r] = {base, r[5:0]};
            end
            // random: seed 20261014, 8 per row, deliberately 4 hits and 4 misses
            for (r = 0; r < 64; r = r + 1) begin
                for (k = 0; k < 8; k = k + 1) begin
                    seed = 20261014 + r * 8 + k;
                    x = seed;
                    for (i = 0; i < 64; i = i + 1) begin
                        x = lcg(x);
                        a_tag[i]   = {x[31:11], i[5:0]};
                        a_valid[i] = 1'b0;
                    end
                    for (i = 0; i < 64; i = i + 1) begin
                        x = lcg(x);
                        a_valid[i] = x[0];
                    end
                    x = lcg(x);
                    idx = x[5:0];
                    if (k < 4) begin
                        a_valid[idx] = 1'b1;               // forced matching hit
                        ru = a_tag[idx][26:6];
                    end else if (k == 4 || k == 6) begin
                        a_valid[idx] = 1'b0;               // forced miss: selected row invalid
                        ru = a_tag[idx][26:6];
                    end else begin
                        a_valid[idx] = 1'b1;               // forced miss: upper tag mismatch
                        ru = a_tag[idx][26:6] ^ 21'd1;
                    end
                    decoy_row = (idx + 1) & 63;
                    a_valid[decoy_row] = 1'b1;             // decoy must be a real cached hit
                    a_observe(3, seed, idx, ru);
                    a_emit_table(seed, idx, ru, decoy_row);
                end
            end
        end
    endtask

    // ======================================================================
    // GROUP B
    // ======================================================================
    reg        b_aw_acc;
    integer    b_r_pending;
    reg        b_r_same;
    integer    b_r_delay;
    reg [27:0] b_ar_addr_lat;
    reg [3:0]  b_ar_rid_lat;
    integer    b_fd, b_scen = 0, b_events = 0, b_acc = 0, b_rsp = 0, b_can = 0, b_out = 0;
    string     b_path;

    task automatic b_init_mem;
        integer i;
        begin
            for (i = 0; i < 4096; i = i + 1) begin
                b_dm[i] = (i[7:0] * 8'h2B) + 8'h5A;
                a_dm[i] = (i[7:0] * 8'h2B) + 8'h5A;
            end
        end
    endtask

    task automatic b_step;
        integer k;
        reg ar_hs, aw_hs, w_hs;
        begin
            // ---------------- sample the current cycle ----------------
            if (inst_req_valid && inst_req_ready) begin
                $fdisplay(b_fd, "BEV %0d %0d I_ACC %08x", b_scen, cyc, inst_req_addr);
                b_events = b_events + 1; b_acc = b_acc + 1; b_out = b_out + 1;
            end
            if (data_req_valid && data_req_ready) begin
                $fdisplay(b_fd, "BEV %0d %0d D_ACC %0d %08x %0d %08x %01x", b_scen, cyc,
                          data_req_write, data_req_addr, data_req_size, data_req_wdata,
                          data_req_wstrb);
                b_events = b_events + 1; b_acc = b_acc + 1; b_out = b_out + 1;
            end
            if (inst_rsp_valid) begin
                $fdisplay(b_fd, "BEV %0d %0d I_RSP %08x", b_scen, cyc, inst_rsp_rdata);
                b_events = b_events + 1; b_rsp = b_rsp + 1; b_out = b_out - 1;
            end
            if (data_rsp_valid) begin
                $fdisplay(b_fd, "BEV %0d %0d D_RSP %08x", b_scen, cyc, data_rsp_rdata);
                b_events = b_events + 1; b_rsp = b_rsp + 1; b_out = b_out - 1;
            end
            ar_hs = bus_arvalid && m_ar_ready;
            aw_hs = bus_awvalid && m_aw_ready;
            w_hs  = m_w_ready && (b_aw_acc || aw_hs);
            if (ar_hs) begin
                $fdisplay(b_fd, "BEV %0d %0d AR %08x %0d", b_scen, cyc, bus_araddr, bus_aruser_id);
                b_events = b_events + 1;
            end
            if (aw_hs) begin
                $fdisplay(b_fd, "BEV %0d %0d AW %08x %064x %08x", b_scen, cyc, bus_awaddr,
                          bus_wdata, bus_wstrb);
                b_events = b_events + 1;
            end
            if (w_hs) begin
                $fdisplay(b_fd, "BEV %0d %0d W %08x %064x %08x", b_scen, cyc, bus_awaddr,
                          bus_wdata, bus_wstrb);
                b_events = b_events + 1;
                for (k = 0; k < 32; k = k + 1)
                    if (bus_wstrb[k]) b_dm[(bus_awaddr*4 + k) & 4095] = bus_wdata[k*8 +: 8];
            end
            if (m_rvalid) begin
                $fdisplay(b_fd, "BEV %0d %0d R %064x %0d %0b", b_scen, cyc, m_rdata, m_rid, m_rlast);
                b_events = b_events + 1;
            end

            // ---------------- drive the edge ending this cycle ----------------
            m_rvalid = 1'b0;
            m_rlast  = 1'b0;
            if (ar_hs) begin
                b_ar_addr_lat = bus_araddr;
                b_ar_rid_lat  = bus_aruser_id;
                if (b_r_same) begin
                    m_rvalid = 1'b1; m_rdata = b_line_data(bus_araddr);
                    m_rid = bus_aruser_id; m_rlast = 1'b1;
                end else begin
                    b_r_pending = b_r_delay;
                end
            end else if (b_r_pending > 0) begin
                b_r_pending = b_r_pending - 1;
                if (b_r_pending == 0) begin
                    m_rvalid = 1'b1; m_rdata = b_line_data(b_ar_addr_lat);
                    m_rid = b_ar_rid_lat; m_rlast = 1'b1;
                end
            end
            if (aw_hs && !m_w_ready) b_aw_acc = 1'b1;
            else if (!aw_hs && b_aw_acc && m_w_ready) b_aw_acc = 1'b0;
        end
    endtask

    task automatic b_run(input integer cycles);
        integer n;
        begin
            for (n = 0; n < cycles; n = n + 1) begin
                b_step();
                @(negedge clk);
            end
        end
    endtask

    task automatic b_scenario_start(input integer id);
        begin
            b_scen = id;
            $fdisplay(b_fd, "BSCEN %0d", id);
        end
    endtask

    task automatic b_stim_i(input [31:0] addr);
        begin
            inst_req_addr  = addr;
            inst_req_valid = 1'b1;
            $fdisplay(b_fd, "BSTIM %0d %0d I 1 %08x", b_scen, cyc, addr);
        end
    endtask

    task automatic b_stim_i_off;
        begin
            inst_req_valid = 1'b0;
            $fdisplay(b_fd, "BSTIM %0d %0d I 0 %08x", b_scen, cyc, inst_req_addr);
        end
    endtask

    task automatic b_stim_d(input is_write, input [31:0] addr, input [1:0] size,
                            input [31:0] wdata, input [3:0] wstrb);
        begin
            data_req_addr  = addr;
            data_req_write = is_write;
            data_req_size  = size;
            data_req_wdata = wdata;
            data_req_wstrb = wstrb;
            data_req_valid = 1'b1;
            $fdisplay(b_fd, "BSTIM %0d %0d D 1 %08x %0d %08x %01x", b_scen, cyc, addr, size,
                      wdata, wstrb);
        end
    endtask

    task automatic b_stim_d_off;
        begin
            data_req_valid = 1'b0;
            data_req_wstrb = 4'h0;
            $fdisplay(b_fd, "BSTIM %0d %0d D 0 %08x", b_scen, cyc, data_req_addr);
        end
    endtask

    task automatic b_soft_reset(input integer phase);
        begin
            $fdisplay(b_fd, "BEV %0d %0d RESET %0d", b_scen, cyc, phase);
            b_events = b_events + 1;
            b_can = b_can + b_out;
            b_out = 0;
            resetn = 1'b0;
            m_rvalid = 1'b0; m_rlast = 1'b0;
            m_ar_ready = 1'b1; m_aw_ready = 1'b1; m_w_ready = 1'b1;
            b_aw_acc = 1'b0; b_r_pending = 0;
            b_run(3);
            resetn = 1'b1;
            init_done = 1'b1;
            b_run(2);
        end
    endtask

    task automatic b_group;
        begin
            // ---- reset between groups: tables start empty, inputs idle ----
            resetn = 1'b0; init_done = 1'b0;
            a_reset_arrays();
            m_ar_ready = 1'b1; m_aw_ready = 1'b1; m_w_ready = 1'b1;
            m_rvalid = 1'b0; m_rlast = 1'b0; b_aw_acc = 1'b0; b_r_pending = 0;
            b_r_same = 1'b0; b_r_delay = 2;
            inst_req_valid = 1'b0; data_req_valid = 1'b0;
            b_run(4);
            resetn = 1'b1; init_done = 1'b1;
            b_run(2);

            // 1. cold miss, ARREADY=1, R late, then re-hit the filled line
            b_scenario_start(1);
            b_stim_i(32'h4000_0000);
            b_run(3);
            b_stim_i_off();
            b_run(12);
            b_stim_i(32'h4000_0000);
            b_run(3);
            b_stim_i_off();
            b_run(6);

            // 2. cold miss with AR/R same-cycle return
            b_scenario_start(2);
            b_r_same = 1'b1;
            b_stim_i(32'h4000_0040);
            b_run(3);
            b_stim_i_off();
            b_run(8);
            b_r_same = 1'b0; b_r_delay = 2;

            // 3. AR backpressure >= 3 cycles with a live address change
            b_scenario_start(3);
            m_ar_ready = 1'b0;
            b_stim_i(32'h4000_0080);
            b_run(4);
            b_stim_i(32'h4000_0000);          // live address becomes a cached hit line
            b_run(4);
            m_ar_ready = 1'b1;
            b_run(8);
            b_stim_i_off();
            b_run(4);

            // 4. hit then hit on a different index and lane
            b_scenario_start(4);
            b_stim_i(32'h4000_0004);
            b_run(3);
            b_stim_i(32'h4000_0000);
            b_run(3);
            b_stim_i_off();
            b_run(4);

            // 5. hit then miss
            b_scenario_start(5);
            b_stim_i(32'h4000_0000);
            b_run(3);
            b_stim_i(32'h4000_0100);
            b_run(3);
            b_stim_i_off();
            b_run(10);

            // 6. miss then immediate hit of the filled line
            b_scenario_start(6);
            b_stim_i(32'h4000_0140);
            b_run(3);
            b_stim_i_off();
            b_run(10);
            b_stim_i(32'h4000_0140);
            b_run(3);
            b_stim_i_off();
            b_run(4);

            // 7. I hit response edge together with a D read request (data priority)
            b_scenario_start(7);
            b_stim_i(32'h4000_0000);
            b_run(2);
            b_stim_d(1'b0, 32'h4000_0000, 2'd2, 32'h0, 4'h0);
            b_run(4);
            b_stim_d_off();
            b_stim_i_off();
            b_run(6);

            // 8. D response edge together with an I request
            b_scenario_start(8);
            b_stim_d(1'b0, 32'h4000_0200, 2'd2, 32'h0, 4'h0);
            b_run(2);
            b_stim_i(32'h4000_0000);
            b_run(4);
            b_stim_i_off();
            b_stim_d_off();
            b_run(10);

            // 9. posted store with AW not accepted: I hit continues, I miss waits
            b_scenario_start(9);
            m_aw_ready = 1'b0;
            b_stim_d(1'b1, 32'h4000_0300, 2'd2, 32'hdead_beef, 4'hf);
            b_run(3);
            b_stim_d_off();
            b_stim_i(32'h4000_0000);
            b_run(3);
            b_stim_i_off();
            b_run(2);
            b_stim_i(32'h4000_0240);
            b_run(4);
            b_stim_i_off();
            m_aw_ready = 1'b1;
            b_run(10);

            // 10. posted store with AW accepted and W waiting
            b_scenario_start(10);
            m_w_ready = 1'b0;
            b_stim_d(1'b1, 32'h4000_0340, 2'd2, 32'h1234_5678, 4'h3);
            b_run(3);
            b_stim_d_off();
            b_stim_i(32'h4000_0280);
            b_run(4);
            b_stim_i_off();
            m_w_ready = 1'b1;
            b_run(10);

            // 11. miss in LOOKUP while the posted W completes; store invalidates a hit line
            b_scenario_start(11);
            b_stim_d(1'b1, 32'h4000_0180, 2'd2, 32'hcafe_0001, 4'hf);
            b_run(2);
            b_stim_d_off();
            b_stim_i(32'h4000_02c0);
            b_run(4);
            b_stim_d(1'b1, 32'h4000_0000, 2'd2, 32'h55aa_55aa, 4'hf);
            b_run(4);
            b_stim_d_off();
            b_stim_i_off();
            b_run(10);
            b_stim_i(32'h4000_0000);          // must re-read after the invalidation
            b_run(3);
            b_stim_i_off();
            b_run(10);

            // 12. idle with valid deasserted and a changing address
            b_scenario_start(12);
            inst_req_addr = 32'h4000_0400; inst_req_valid = 1'b0;
            b_run(2);
            inst_req_addr = 32'h4000_0000;
            b_run(2);
            inst_req_addr = 32'h4000_0440;
            b_run(4);

            // 13/14/15. reset on the three boundaries
            b_scenario_start(13);
            b_stim_i(32'h4000_0000);
            b_run(2);                          // accepted, LOOKUP hit pending consumption
            b_soft_reset(1);
            b_run(4);
            b_scenario_start(14);
            m_ar_ready = 1'b0;
            b_stim_i(32'h4000_0480);
            b_run(2);                          // accepted, LOOKUP miss, AR held off
            b_soft_reset(2);
            m_ar_ready = 1'b1;
            b_run(4);
            b_scenario_start(15);
            b_r_delay = 12;
            b_stim_i(32'h4000_04c0);
            b_run(4);                          // accepted, waiting for R
            b_soft_reset(3);
            b_r_delay = 2;
            b_run(4);
            b_stim_i_off();
            b_run(4);

            // 16. same-line store invalidates, next fetch misses with new data
            b_scenario_start(16);
            b_stim_i(32'h4000_0500);
            b_run(3);
            b_stim_i_off();
            b_run(10);
            b_stim_d(1'b1, 32'h4000_0500, 2'd2, 32'h0102_0304, 4'hf);
            b_run(3);
            b_stim_d_off();
            b_run(8);
            b_stim_i(32'h4000_0500);
            b_run(3);
            b_stim_i_off();
            b_run(10);
        end
    endtask

    // ======================================================================
    // main
    // ======================================================================
    initial begin
        if (!$value$plusargs("LOOKUP_LOG=%s", a_path))
            $fatal(1, "RESULT: FAIL inst_lookup missing +LOOKUP_LOG");
        if (!$value$plusargs("BUS_LOG=%s", b_path))
            $fatal(1, "RESULT: FAIL inst_lookup missing +BUS_LOG");
        a_fd = $fopen(a_path, "w");
        b_fd = $fopen(b_path, "w");
        if (!a_fd || !b_fd) $fatal(1, "RESULT: FAIL inst_lookup cannot open trace files");
        $fdisplay(a_fd, "ALOOKUP registered lookup group A; invariant tag[5:0]==row; seed base 20261014");
        $fdisplay(b_fd, "BLOOKUP registered lookup group B; b_dm[i]=(i[7:0]*0x2B+0x5A)&0xFF; byte base = addr*4");
        b_init_mem();
        a_row_mask = 64'b0;

        resetn = 1'b0;
        repeat (4) @(negedge clk);
        resetn = 1'b1;
        init_done = 1'b1;
        m_aw_ready = 1'b0;                  // group A performs no writes
        m_w_ready  = 1'b0;
        m_ar_ready = 1'b1;
        repeat (2) @(negedge clk);

        a_run();
        b_group();

        if (a_mism != 0 || a_det < 64*23 || a_rnd < 512 || a_rows_seen != 64)
            $fatal(1, "RESULT: FAIL inst_lookup group A coverage or mismatch");
        $fdisplay(a_fd, "ASUM det=%0d rnd=%0d hits=%0d misses=%0d rows=%0d cont=%0d mismatches=%0d",
                  a_det, a_rnd, a_hits, a_misses, a_rows_seen, a_cont, a_mism);
        $fdisplay(b_fd, "BSUM accepts=%0d responses=%0d cancels=%0d events=%0d outstanding=%0d",
                  b_acc, b_rsp, b_can, b_events, b_out);
        if (b_out != 0 || b_acc != b_rsp + b_can)
            $fatal(1, "RESULT: FAIL inst_lookup group B conservation");
        $display("RESULT: PASS inst_lookup_registered A_det=%0d A_rnd=%0d hits=%0d misses=%0d rows=%0d high_bits=21 B_scenarios=%0d B_events=%0d mismatches=0",
                 a_det, a_rnd, a_hits, a_misses, a_rows_seen, b_scen, b_events);
        $fclose(a_fd);
        $fclose(b_fd);
        $finish;
    end

    initial begin
        #5000000;
        $fatal(1, "RESULT: FAIL inst_lookup watchdog");
    end
endmodule
