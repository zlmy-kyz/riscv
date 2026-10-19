`timescale 1ns/1ps
// Task043 bridge-level key verification for the two-entry ordered posted write buffer.
//
// This TB drives the CPU-side SRAM ports and models the Pango DDR user port itself
// (no WVALID/B, no RREADY; WREADY only means "this beat is accepted"). All expected
// data comes from this file's own beat memory and its own cache/queue copies; no DUT
// forward mask, queue register or internal state is used as an expectation.
// Every edge is traced so an independent Python checker can re-derive the ledger.
module tb_wb2_bridge #(
    parameter integer DQ       = 32,
    parameter integer POSTED   = 1,
    parameter integer DEPTH    = 2,
    parameter integer TURNOVER = 1,
    parameter integer FORWARD  = 1,
    parameter integer RUW      = 1,
    parameter integer ICACHE   = 1,
    parameter integer DCACHE   = 1,
    parameter integer CAMERA   = 0,
    parameter integer PREPROC  = 0,
    parameter integer PLANE    = 0
);
    // DQ is the user-port beat width in BYTES (32 -> 256-bit beat, 16 -> 128-bit).
    localparam integer BYTES = DQ;
    localparam integer BEATB = (DQ == 32) ? 5 : 4;
    localparam integer TAGB  = 32 - BEATB;
    localparam integer LINES = 64;

    GTP_GRS GRS_INST (.GRS_N(1'b1));

    reg clk = 0;
    always #5 clk = ~clk;

    reg resetn = 0;
    reg init_done = 0;

    reg  iv = 0, dv = 0, dw = 0;
    reg  [31:0] ia = 0, da = 0, wd = 0;
    reg  [3:0]  ws = 0;
    reg  [1:0]  ds = 2'b10;
    wire ir, dr, isv, dsv;
    wire [31:0] idata, ddata;

    wire [27:0] awaddr, araddr;
    wire awvalid, arvalid, rvalid;
    wire [3:0] awid, arid_out, awlen, arlen;
    wire awap, arap;
    wire [8*DQ-1:0] wdata_dut, rdata_dut;
    wire [DQ-1:0]   wstrb_dut;
    wire busy;

    reg block_aw = 0, block_w = 0, block_r = 0;
    reg instant_w = 0, instant_r = 0, w_early = 0;
    integer aw_hold = 0, w_hold = 0, r_hold = 0;
    integer aw_wait = 0, w_wait = 0, r_wait = 0, ar_wait = 0;
    reg writing = 0, reading = 0;

    reg [8*DQ-1:0]  mem [0:255];
    reg [8*DQ-1:0]  dca [0:LINES-1];
    reg [LINES-1:0] dca_v;
    reg [TAGB-1:0]  dca_tag [0:LINES-1];
    reg [8*DQ-1:0]  ica [0:LINES-1];
    reg [LINES-1:0] ica_v;
    reg [TAGB-1:0]  ica_tag [0:LINES-1];

    integer pend_n = 0;
    reg [31:0] p_addr [0:1];
    reg [31:0] p_data [0:1];
    reg [3:0]  p_strb [0:1];
    reg        p_hit  [0:1];

    reg aw_sent = 0;
    reg prev_aw_hold = 0, prev_ar_hold = 0;
    reg [27:0] saved_aw = 0, saved_ar = 0, driven_ar = 0;
    reg [8*DQ-1:0] saved_wd = 0;
    reg [DQ-1:0]   saved_ws = 0;
    reg [3:0]      saved_rid = 0;

    integer aw_cnt = 0, w_cnt = 0, ar_cnt = 0, r_cnt = 0;
    integer d_acc = 0, d_rsp = 0, i_acc = 0, i_rsp = 0;
    integer wb_cancel = 0, wb_drain_edge = 0, ar_blocked_by_queue = 0;
    integer same_edge_cnt = 0;

    // Response ledgers: a store is answered by exactly one posted ACK, a load by
    // its data. Acceptance may coincide with the previous response edge, so both
    // ports keep a small FIFO and the response is matched before the new push.
    integer rq_head = 0, rq_tail = 0, iq_head = 0, iq_tail = 0;
    reg [1:0]  rq_kind [0:3];   // 0 = store ACK, 1 = load hit, 2 = load miss
    reg [31:0] rq_exp  [0:3];
    reg [31:0] rq_addr [0:3];
    reg [1:0]  iq_kind [0:3];
    reg [31:0] iq_exp  [0:3];
    reg [31:0] iq_addr [0:3];
    integer store_acc = 0, store_ack = 0, load_rsp = 0, inst_rsp = 0;
    integer front_cancel_st = 0, front_cancel_ld = 0;

    wire w_commit;
    assign rlast = rvalid;

    // ---- independent reference helpers (declared before use) ----
    function automatic integer idx_of(input [31:0] a);
        idx_of = a[BEATB+5:BEATB];
    endfunction

    function automatic integer uncached(input [31:0] a);
        uncached = ((CAMERA != 0) && (a[31:22] == 10'h004)) ||
                   ((PREPROC != 0) && (a[31:16] == 16'h0200));
    endfunction

    function automatic [31:0] word_of(input [8*DQ-1:0] line, input [4:0] lane);
        word_of = line[lane*32 +: 32];
    endfunction

    // The user port always drives the full 32-bit word in its lane; only WSTRB
    // decides which bytes are physically committed.
    function automatic [8*DQ-1:0] pwsel(input [31:0] a, input [31:0] d, input [3:0] s);
        integer q;
        begin
            pwsel = {8*DQ{1'b0}};
            pwsel[a[BEATB-1:2]*32 +: 32] = d;
        end
    endfunction

    function automatic [DQ-1:0] pwstrb(input [31:0] a, input [3:0] s);
        integer q;
        begin
            pwstrb = {DQ{1'b0}};
            for (q = 0; q < 4; q = q + 1)
                pwstrb[a[BEATB-1:2]*4 + q] = s[q];
        end
    endfunction

    // The CPU-side store data is already byte-positioned inside its addressed
    // word; forwarding merges whole bytes of that word, not the beat lane.
    function automatic [31:0] merge_word(input [31:0] base, input [31:0] data, input [3:0] strb);
        integer q;
        begin
            merge_word = base;
            for (q = 0; q < 4; q = q + 1)
                if (strb[q]) merge_word[q*8 +: 8] = data[q*8 +: 8];
        end
    endfunction

    function automatic [31:0] expect_load(input [31:0] a);
        integer f;
        reg [31:0] v;
        reg [31:0] lane;
        begin
            lane = a[BEATB-1:2];
            if (DCACHE != 0 && dca_v[idx_of(a)] && dca_tag[idx_of(a)] == a[31:BEATB]) begin
                v = word_of(dca[idx_of(a)], a[BEATB-1:2]);
                for (f = 0; f < 2; f = f + 1)
                    if (f < pend_n && FORWARD != 0 &&
                        p_addr[f][31:BEATB] == a[31:BEATB] &&
                        p_addr[f][BEATB-1:2] == lane)
                        v = merge_word(v, p_data[f], p_strb[f]);
                expect_load = v;
            end else begin
                expect_load = word_of(mem[a / BYTES], a[BEATB-1:2]);
            end
        end
    endfunction

    // ---- DDR user-port model ----
    assign awready = init_done && !block_aw && awvalid && !writing && (aw_wait >= aw_hold);
    assign wready  = init_done && !block_w &&
                     (w_early || (instant_w && awvalid && awready) ||
                      (writing && w_wait == 0));
    assign arready = init_done && !block_r && arvalid && !reading && (r_wait >= r_hold);
    assign rvalid  = (instant_r && arvalid && arready) || (reading && r_wait == 0);
    // Controller addresses count 8 address units per beat, so beat index = addr>>3
    // and the byte address of that beat is ctrl << (BEATB-3).
    function automatic [31:0] baddr(input [27:0] ctrl);
        baddr = {4'b0, ctrl} << (BEATB - 3);
    endfunction

    // An immediate R belongs to the AR accepted on THIS edge, so it must use the
    // live address/ID; only a delayed R may use the latched copy. Using saved_*
    // for the immediate case returns the previous beat's data.
    wire ar_hs = arvalid && arready;
    wire [27:0] r_cur_addr = (instant_r && ar_hs) ? araddr   : saved_ar;
    wire [3:0]  r_cur_id   = (instant_r && ar_hs) ? arid_out : saved_rid;

    assign rdata_dut = mem[r_cur_addr >> 3];
    wire [3:0] rid_dut = r_cur_id;

    assign w_commit = resetn && init_done && busy && wready && (aw_sent || awready);

    dual_sram_to_pango_ddr_bridge #(
        .MEM_DQ_WIDTH(DQ),
        .INST_LINE_BUFFER_ENABLE(ICACHE),
        .DATA_LINE_BUFFER_ENABLE(DCACHE),
        .CAMERA_UNCACHED_ENABLE(CAMERA),
        .PREPROCESS_UNCACHED_ENABLE(PREPROC),
        .POSTED_WRITE_ENABLE(POSTED),
        .DATA_READ_UNDER_WRITE_ENABLE(RUW),
        .DATA_STORE_FORWARD_ENABLE(FORWARD),
        .WRITE_BUFFER_TURNOVER_ENABLE(TURNOVER),
`ifdef LEGACY_BRIDGE
        .CACHE_PERF_ENABLE(0),
        .DIAG_PERF_ENABLE(0)
`else
        .WRITE_BUFFER_DEPTH(DEPTH),
        .CACHE_PERF_ENABLE(0),
        .DIAG_PERF_ENABLE(0)
`endif
    ) dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(init_done),
        .write_buffer_busy(busy),
        .inst_req_valid(iv), .inst_req_addr(ia), .inst_req_ready(ir),
        .inst_rsp_valid(isv), .inst_rsp_rdata(idata), .inst_rsp_error(),
        .data_req_valid(dv), .data_req_write(dw), .data_req_size(ds),
        .data_req_addr(da), .data_req_wdata(wd), .data_req_wstrb(ws),
        .data_req_ready(dr), .data_rsp_valid(dsv), .data_rsp_rdata(ddata),
        .data_rsp_error(),
        .axi_awaddr(awaddr), .axi_awuser_ap(awap), .axi_awuser_id(awid),
        .axi_awlen(awlen), .axi_awready(awready), .axi_awvalid(awvalid),
        .axi_wdata(wdata_dut), .axi_wstrb(wstrb_dut), .axi_wready(wready),
        .axi_wusero_id(4'd1), .axi_wusero_last(wready),
        .axi_araddr(araddr), .axi_aruser_ap(arap), .axi_aruser_id(arid_out),
        .axi_arlen(arlen), .axi_arready(arready), .axi_arvalid(arvalid),
        .axi_rdata(rdata_dut), .axi_rid(rid_dut), .axi_rlast(rlast),
        .axi_rvalid(rvalid), .perf_cache_events(), .perf_cache_enabled(),
        .perf_wait_events()
    );

    // ---- trace ----
    integer fd = 0;
    integer cyc = 0;
    reg [8*19:0] mark_name = 0;
    reg mark_pending = 0;
    string edge_path, mem_path;

    task automatic mark(input [8*19:0] n);
        begin
            @(negedge clk);
            mark_name = n;
            mark_pending = 1;
        end
    endtask

    always @(posedge clk) begin
        if (fd != 0) begin
            $fwrite(fd, "E %0d %0d %0d %0d %0d %0d %h %h %0d %0d %0d %0d %h %h %h %0d %h ",
                    cyc, resetn, init_done, iv, ir, isv, ia, idata,
                    dv, dw, ds, dr, da, wd, ws, dsv, ddata);
            $fwrite(fd, "%0d %0d %h %064h %016h %0d %0d %0d %h %0d %0d %0d %064h %0d\n",
                    awvalid, awready, awaddr,
                    {{(256-8*DQ){1'b0}}, wdata_dut},
                    {{(64-DQ){1'b0}}, wstrb_dut},
                    wready, arvalid, arready, araddr,
                    rvalid, rid_dut, rlast,
                    {{(256-8*DQ){1'b0}}, rdata_dut}, busy);
            if (mark_pending) begin
                $fwrite(fd, "M %0d %0s\n", cyc, mark_name);
                mark_pending = 0;
            end
        end
        cyc = cyc + 1;
    end

    // ---- model update and independent checks ----
    integer k, b, e, rk, qn, cst, cld;
    reg [31:0] ab;
    reg [8*DQ-1:0] mem32_prev;
    reg [8*DQ-1:0] w_word;
    reg [31:0] exp_word;

    always @(posedge clk) begin
        if (!resetn) begin
            writing <= 0; reading <= 0;
            aw_wait <= 0; w_wait <= 0; r_wait <= 0; ar_wait <= 0;
            aw_sent <= 0;
            prev_aw_hold <= 0; prev_ar_hold <= 0;
            // The bridge clears both line buffers on reset (valid + tag), so the
            // reference must clear them as well, otherwise a later hit is invented.
            dca_v <= 0; ica_v <= 0;
            for (k = 0; k < LINES; k = k + 1) begin
                dca_tag[k] <= 0; ica_tag[k] <= 0;
            end
            // Outstanding front-end requests are cancelled by the reset edge. The
            // counts are accumulated in locals first: several non-blocking "+1"
            // writes to the same register in one block would keep only the last.
            cst = 0; cld = 0;
            for (rk = rq_head; rk != rq_tail; rk = rk + 1) begin
                if (rq_kind[rk % 4] == 2'd0) cst = cst + 1;
                else cld = cld + 1;
            end
            for (rk = iq_head; rk != iq_tail; rk = rk + 1) cld = cld + 1;
            front_cancel_st <= front_cancel_st + cst;
            front_cancel_ld <= front_cancel_ld + cld;
            rq_head <= rq_tail;
            iq_head <= iq_tail;
            // Entries still inside the write buffer are a different kind of cancel:
            // the posted ACK was already returned, no W beat will ever be issued.
            wb_cancel <= wb_cancel + pend_n;
            pend_n <= 0;
        end else begin
            // ddr_init_done low clears both line buffers inside the bridge, but the
            // response/accept ledger must keep running: a posted ACK can still be
            // returned on those edges, and swallowing it shifts every later match.
            if (!init_done) begin
                dca_v <= 0; ica_v <= 0;
                for (k = 0; k < LINES; k = k + 1) begin
                    dca_tag[k] <= 0; ica_tag[k] <= 0;
                end
            end
            qn = pend_n;
            if ($test$plusargs("WB2_DEBUG"))
                $display("DBG cyc=%0d hd=%0d tl=%0d kind=%0d addr=%h dsv=%0d isv=%0d dv=%0d dw=%0d dr=%0d bus=%0d",
                         cyc, rq_head, rq_tail, rq_kind[rq_head % 4], rq_addr[rq_head % 4],
                         dsv, isv, dv, dw, dr, busy);
            // ---- 1. protocol checks ----
            if (prev_aw_hold && (awaddr !== saved_aw || wdata_dut !== saved_wd ||
                                 wstrb_dut !== saved_ws))
                $fatal(1, "RESULT: FAIL AW fields changed under backpressure");
            if (prev_ar_hold && araddr !== driven_ar)
                $fatal(1, "RESULT: FAIL AR address changed under backpressure");
            prev_aw_hold <= awvalid && !awready;
            prev_ar_hold <= arvalid && !arready;
            if (awvalid) begin
                saved_aw <= awaddr; saved_wd <= wdata_dut; saved_ws <= wstrb_dut;
            end
            if (arvalid) begin
                saved_ar <= araddr; driven_ar <= araddr;
            end
            if (arvalid && arlen != 0)   $fatal(1, "RESULT: FAIL ARLEN");
            if (awvalid && awlen != 0)   $fatal(1, "RESULT: FAIL AWLEN");
            if (awvalid && awid != 4'd1) $fatal(1, "RESULT: FAIL AWUSER_ID is not the data id");
            if (arvalid && busy)
                $fatal(1, "RESULT: FAIL AR issued while the write queue is not empty");
            if (awvalid && !busy)
                $fatal(1, "RESULT: FAIL AW issued with an empty write queue");

            if (arvalid && !arready) ar_wait <= ar_wait + 1; else ar_wait <= 0;
            if (arvalid && arready) begin
                ar_cnt <= ar_cnt + 1;
                saved_rid <= arid_out;
                if (!instant_r) begin reading <= 1; r_wait <= r_hold; end
            end
            if (reading && r_wait > 0) r_wait <= r_wait - 1;
            if (rvalid) begin reading <= 0; r_cnt <= r_cnt + 1; end

            if (awvalid && !awready) aw_wait <= aw_wait + 1; else aw_wait <= 0;
            if (awvalid && awready) begin
                aw_cnt <= aw_cnt + 1;
                if (!instant_w) begin writing <= 1; w_wait <= w_hold; end
            end
            if (writing && w_wait > 0) w_wait <= w_wait - 1;
            if (w_commit) writing <= 0;
            if (w_commit) aw_sent <= 0;
            else if (awvalid && awready) aw_sent <= 1;

            // ---- 2. responses: the older request is answered first ----
            if (dsv) begin
                d_rsp <= d_rsp + 1;
                if (rq_head == rq_tail) $fatal(1, "RESULT: FAIL data response with no request");
                if (rq_kind[rq_head % 4] == 2'd0) begin
                    store_ack <= store_ack + 1;
                end else begin
                    load_rsp <= load_rsp + 1;
                    exp_word = (rq_kind[rq_head % 4] == 2'd2) ?
                               word_of(mem[rq_addr[rq_head % 4] / BYTES],
                                       rq_addr[rq_head % 4][BEATB-1:2]) :
                               rq_exp[rq_head % 4];
                    if (ddata !== exp_word)
                    $fatal(1, "RESULT: FAIL load data edge %0d addr %h kind %0d got %h exp %h hd %0d tl %0d memline %h w0 %h",
                           cyc, rq_addr[rq_head % 4], rq_kind[rq_head % 4], ddata, exp_word,
                           rq_head, rq_tail,
                           mem[rq_addr[rq_head % 4] / BYTES],
                           word_of(mem[rq_addr[rq_head % 4] / BYTES], 5'd0));
                end
                rq_head <= rq_head + 1;
            end
            if (isv) begin
                i_rsp <= i_rsp + 1;
                if (iq_head == iq_tail) $fatal(1, "RESULT: FAIL instruction response with no request");
                inst_rsp <= inst_rsp + 1;
                exp_word = (iq_kind[iq_head % 4] == 2'd2) ?
                           word_of(mem[iq_addr[iq_head % 4] / BYTES],
                                   iq_addr[iq_head % 4][BEATB-1:2]) :
                           iq_exp[iq_head % 4];
                if (idata !== exp_word)
                    $fatal(1, "RESULT: FAIL instruction data edge %0d addr %h got %h exp %h",
                           cyc, iq_addr[iq_head % 4], idata, exp_word);
                iq_head <= iq_head + 1;
            end

            // ---- 3. DDR read fill ----
            if (rvalid) begin
                ab = baddr(r_cur_addr);
                if (r_cur_id == 4'd0) begin
                    if (ICACHE != 0 && !uncached(ab)) begin
                        ica[idx_of(ab)] <= mem[r_cur_addr >> 3];
                        ica_v[idx_of(ab)] <= 1'b1;
                        ica_tag[idx_of(ab)] <= ab[31:BEATB];
                    end
                end else begin
                    if (DCACHE != 0 && !uncached(ab)) begin
                        dca[idx_of(ab)] <= mem[r_cur_addr >> 3];
                        dca_v[idx_of(ab)] <= 1'b1;
                        dca_tag[idx_of(ab)] <= ab[31:BEATB];
                    end
                end
            end

            // ---- 4. physical write: only the head can be committed ----
            if (w_commit) begin
                w_cnt <= w_cnt + 1;
                if (pend_n == 0) $fatal(1, "RESULT: FAIL W beat with an empty queue");
                // Snapshot the expected lane word first: a part-select of a function
                // call result is not legal Verilog, so it must go through a variable.
                w_word = pwsel(p_addr[0], p_data[0], p_strb[0]);
                if (wdata_dut !== w_word)
                    $fatal(1, "RESULT: FAIL W lane shift or data edge %0d addr %h got %h exp %h strb %h wstrb %h",
                           cyc, p_addr[0], wdata_dut, w_word,
                           p_strb[0], wstrb_dut);
                if (wstrb_dut !== pwstrb(p_addr[0], p_strb[0]))
                    $fatal(1, "RESULT: FAIL W strobe shift edge %0d addr %h", cyc, p_addr[0]);
                if (awaddr !== {p_addr[0][29:BEATB], 3'b000})
                    $fatal(1, "RESULT: FAIL AW address is not the head line");
                for (b = 0; b < BYTES; b = b + 1)
                    if (wstrb_dut[b])
                        mem[p_addr[0] / BYTES][b*8 +: 8] <= w_word[b*8 +: 8];
                if (p_hit[0] && dca_v[idx_of(p_addr[0])] &&
                    dca_tag[idx_of(p_addr[0])] == p_addr[0][31:BEATB])
                    for (b = 0; b < BYTES; b = b + 1)
                        if (wstrb_dut[b])
                            dca[idx_of(p_addr[0])][b*8 +: 8] <= w_word[b*8 +: 8];
                if (pend_n == 2) begin
                    p_addr[0] <= p_addr[1]; p_data[0] <= p_data[1];
                    p_strb[0] <= p_strb[1]; p_hit[0] <= p_hit[1];
                end
                qn = qn - 1;
            end
            pend_n <= qn;

            // ---- 5. accepted CPU requests: oldest response already consumed ----
            if (dv && dr) begin
                d_acc <= d_acc + 1;
                if (dw) begin
                    if (qn >= 2) $fatal(1, "RESULT: FAIL a third store entered a full queue");
                    p_addr[qn] <= da;
                    p_data[qn] <= wd;
                    p_strb[qn] <= ws;
                    p_hit[qn] <= (DCACHE != 0) && !uncached(da) &&
                                 dca_v[idx_of(da)] && (dca_tag[idx_of(da)] == da[31:BEATB]);
                    pend_n <= qn + 1;
                    store_acc <= store_acc + 1;
                    if (ICACHE != 0 && ica_v[idx_of(da)] && ica_tag[idx_of(da)] == da[31:BEATB])
                        ica_v[idx_of(da)] <= 1'b0;
                    rq_kind[rq_tail % 4] <= 2'd0;
                    rq_addr[rq_tail % 4] <= da;
                    rq_tail <= rq_tail + 1;
                end else begin
                    rq_kind[rq_tail % 4] <= ((DCACHE == 0) || uncached(da) ||
                                             !dca_v[idx_of(da)] ||
                                             (dca_tag[idx_of(da)] != da[31:BEATB])) ? 2'd2 : 2'd1;
                    rq_exp[rq_tail % 4]  <= expect_load(da);
                    rq_addr[rq_tail % 4] <= da;
                    rq_tail <= rq_tail + 1;
                end
            end

            if (iv && ir) begin
                i_acc <= i_acc + 1;
                iq_kind[iq_tail % 4] <= ((ICACHE != 0) && !uncached(ia) && ica_v[idx_of(ia)] &&
                                         ica_tag[idx_of(ia)] == ia[31:BEATB]) ? 2'd1 : 2'd2;
                iq_exp[iq_tail % 4]  <= ((ICACHE != 0) && !uncached(ia) && ica_v[idx_of(ia)] &&
                                          ica_tag[idx_of(ia)] == ia[31:BEATB]) ?
                                         word_of(ica[idx_of(ia)], ia[BEATB-1:2]) :
                                         word_of(mem[ia / BYTES], ia[BEATB-1:2]);
                iq_addr[iq_tail % 4] <= ia;
                iq_tail <= iq_tail + 1;
            end
        end
    end

    // ---- stimulus tasks ----
    task automatic st(input [31:0] a, input [31:0] d, input [3:0] s);
        begin
            @(negedge clk);
            dv <= 1; dw <= 1; da <= a; wd <= d; ws <= s; ds <= 2'b10;
            @(posedge clk);
            while (!dr) @(posedge clk);
            dv <= 0; dw <= 0;
        end
    endtask

    task automatic st_blocked(input [31:0] a, input [31:0] d, input [3:0] s,
                              input integer n, output integer accepted);
        integer t;
        begin
            accepted = 0;
            @(negedge clk);
            dv <= 1; dw <= 1; da <= a; wd <= d; ws <= s; ds <= 2'b10;
            for (t = 0; t < n; t = t + 1) begin
                @(posedge clk);
                if (dr) begin accepted = 1; t = n; end
            end
            dv <= 0; dw <= 0;
        end
    endtask

    task automatic ld(input [31:0] a, output [31:0] got);
        begin
            @(negedge clk);
            dv <= 1; dw <= 0; da <= a; wd <= 0; ws <= 4'h0; ds <= 2'b10;
            @(posedge clk);
            while (!dr) @(posedge clk);
            dv <= 0;
            @(posedge clk);
            while (!dsv) @(posedge clk);
            got = ddata;
        end
    endtask

    task automatic ird(input [31:0] a, output [31:0] got);
        begin
            @(negedge clk);
            iv <= 1; ia <= a;
            @(posedge clk);
            while (!ir) @(posedge clk);
            iv <= 0;
            @(posedge clk);
            while (!isv) @(posedge clk);
            got = idata;
        end
    endtask

    task automatic drain(input integer limit);
        integer t;
        begin
            block_aw = 0; block_w = 0;
            for (t = 0; t < limit; t = t + 1) begin
                @(posedge clk);
                // A scenario boundary needs BOTH sides quiet: the write queue and
                // every front-end response. A posted ACK that was suppressed while
                // ddr_init_done was low can arrive after a younger load's data, so
                // starting a new scenario earlier breaks the response order.
                if (!busy && pend_n == 0 && rq_head == rq_tail && iq_head == iq_tail)
                    t = limit;
            end
        end
    endtask

    initial begin : stim
        integer accepted;
        reg [31:0] g, keep;
        reg w_seen, blk_seen, got;
        if (!$value$plusargs("EDGE_LOG=%s", edge_path)) edge_path = "wb2.edges.log";
        if (!$value$plusargs("MEM_DUMP=%s", mem_path)) mem_path = "wb2.mem.log";
        fd = $fopen(edge_path, "w");
        for (k = 0; k < 256; k = k + 1) begin
            for (b = 0; b < BYTES; b = b + 1)
                mem[k][b*8 +: 8] = (k * 37 + b * 11 + 5) & 8'hff;
        end
        // Publish the pre-loaded DDR image as evidence so the independent checker
        // seeds its byte memory from the trace instead of duplicating this formula.
        for (k = 0; k < 256; k = k + 1)
            $fwrite(fd, "N %0d %0h\n", k, mem[k]);
        for (k = 0; k < LINES; k = k + 1) begin
            dca_v[k] = 0; ica_v[k] = 0;
            dca[k] = {8*DQ{1'b0}}; ica[k] = {8*DQ{1'b0}};
            dca_tag[k] = 0; ica_tag[k] = 0;
        end
        resetn = 0; init_done = 0;
        repeat (4) @(negedge clk);
        resetn = 1;
        repeat (2) @(negedge clk);
        init_done = 1;
        repeat (2) @(negedge clk);

        if (PLANE == 0) begin
            // ===== G1 capacity, order, same-edge promotion =====
            mark("G1");
            block_aw = 1; block_w = 1;
            st(32'h000, 32'hA1A1_A1A1, 4'hF);
            st(32'h0A0, 32'hB2B2_B2B2, 4'hF);
            mark("G1_full");
            // C stays valid while the queue is full; it must be accepted exactly on
            // the head completion edge, after B becomes the new head.
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h140; wd <= 32'hC3C3_C3C3; ws <= 4'hF;
            for (k = 0; k < 6; k = k + 1) begin
                @(posedge clk);
                if (dr) $fatal(1, "RESULT: FAIL third store accepted while full");
            end
            mark("G1_release");
            block_aw = 0; block_w = 0; w_hold = 3;
            accepted = 0;
            for (k = 0; k < 40; k = k + 1) begin
                @(posedge clk);
                if (dr && !accepted) begin accepted = 1; k = 40; end
            end
            if (accepted == 0) $fatal(1, "RESULT: FAIL third store never accepted after the drain started");
            dv <= 0; dw <= 0;
            drain(80);
            mark("G1_done");
            if (mem[32'h000 / BYTES][0 +: 32] !== 32'hA1A1_A1A1) $fatal(1, "RESULT: FAIL G1 A");
            if (mem[32'h0A0 / BYTES][0 +: 32] !== 32'hB2B2_B2B2) $fatal(1, "RESULT: FAIL G1 B");
            if (mem[32'h140 / BYTES][0 +: 32] !== 32'hC3C3_C3C3) $fatal(1, "RESULT: FAIL G1 C");

            // ===== G2 AW/W backpressure, stability, init pause =====
            mark("G2_early_w");
            // WREADY high while AW is still not accepted must not commit anything.
            w_early = 1; block_aw = 1;
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h200; wd <= 32'hD4D4_D4D4; ws <= 4'hF;
            @(posedge clk);
            if (!dr) $fatal(1, "RESULT: FAIL the store was not accepted with a free queue");
            dv <= 0;
            repeat (3) @(posedge clk);
            if (w_commit) $fatal(1, "RESULT: FAIL W accepted before AW");
            block_aw = 0; w_early = 0;
            @(negedge clk);
            drain(40);
            mark("G2_same_edge");
            // The instant-W mode must stay on until the AW that really carries this
            // store is accepted. Dropping it right after the posted ACK left AW and
            // W on different edges, so the same-edge count was 0.
            instant_w = 1; block_aw = 0; block_w = 0; w_hold = 0;
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h240; wd <= 32'hE5E5_E5E5; ws <= 4'hF;
            @(posedge clk);
            if (!dr) $fatal(1, "RESULT: FAIL the store was not accepted with a free queue");
            dv <= 0; dw <= 0;
            same_edge_cnt = 0;
            for (k = 0; k < 40; k = k + 1) begin
                @(posedge clk);
                if (awvalid && awready && w_commit) same_edge_cnt = same_edge_cnt + 1;
                if (same_edge_cnt > 0) k = 40;
            end
            instant_w = 0;
            if (same_edge_cnt == 0)
                $fatal(1, "RESULT: FAIL G2_same_edge never completed AW and W on one edge");
            drain(40);
            if (mem[32'h240 / BYTES][0 +: 32] !== 32'hE5E5_E5E5)
                $fatal(1, "RESULT: FAIL same-edge AW/W commit");
            mark("G2_zero_strobe");
            keep = mem[32'h280 / BYTES][0 +: 32];
            st(32'h280, 32'hFFFF_FFFF, 4'h0);
            drain(40);
            if (mem[32'h280 / BYTES][0 +: 32] !== keep)
                $fatal(1, "RESULT: FAIL zero-strobe store changed DDR");
            mark("G2_init_pause");
            block_aw = 1; block_w = 1;
            st(32'h2C0, 32'h1111_2222, 4'hF);
            st(32'h300, 32'h3333_4444, 4'hF);
            init_done = 0;
            repeat (3) @(posedge clk);
            if (awvalid) $fatal(1, "RESULT: FAIL AW while init is not done");
            init_done = 1;
            block_aw = 0; block_w = 0;
            drain(60);
            if (mem[32'h2C0 / BYTES][0 +: 32] !== 32'h1111_2222) $fatal(1, "RESULT: FAIL pause store 1");
            if (mem[32'h300 / BYTES][0 +: 32] !== 32'h3333_4444) $fatal(1, "RESULT: FAIL pause store 2");

            // ===== G3 byte-accurate forwarding =====
            mark("G3_head_tail");
            block_aw = 1; block_w = 1;
            ld(32'h400, g);
            st(32'h400, 32'h1111_1111, 4'hF);
            st(32'h404, 32'h2222_2222, 4'hF);
            ld(32'h400, g);
            if (g !== 32'h1111_1111) $fatal(1, "RESULT: FAIL head-only forward %h", g);
            ld(32'h404, g);
            if (g !== 32'h2222_2222) $fatal(1, "RESULT: FAIL tail-only forward %h", g);
            drain(40);
            mark("G3_overlap");
            block_aw = 1; block_w = 1;
            ld(32'h440, g);
            st(32'h440, 32'hAAAA_AAAA, 4'hF);
            st(32'h440, 32'hBBBB_BBBB, 4'h3);
            ld(32'h440, g);
            if (g !== 32'hAAAA_BBBB) $fatal(1, "RESULT: FAIL younger-over-older merge %h", g);
            drain(40);
            mark("G3_zero_mask");
            block_aw = 1; block_w = 1;
            ld(32'h480, g);
            keep = g;
            st(32'h480, 32'h0BAD_0BAD, 4'h0);
            ld(32'h480, g);
            if (g !== keep) $fatal(1, "RESULT: FAIL zero-mask forward %h", g);
            drain(40);
            mark("G3_lanes");
            for (k = 0; k < 8; k = k + 1) begin
                block_aw = 1; block_w = 1;
                ld(32'h500 + k*4, g);
                st(32'h500 + k*4, 32'hA500_0000 + k, 4'hF);
                ld(32'h500 + k*4, g);
                if (g !== 32'hA500_0000 + k) $fatal(1, "RESULT: FAIL lane %0d forward %h", k, g);
                drain(20);
            end
            mark("G3_sb");
            block_aw = 1; block_w = 1;
            ld(32'h580, g);
            keep = g;
            st(32'h582, 32'h00AB_0000, 4'h4);
            ld(32'h580, g);
            if (g[23:16] !== 8'hAB) $fatal(1, "RESULT: FAIL SB byte forward %h keep %h", g, keep);
            if (g[15:0] !== keep[15:0] || g[31:24] !== keep[31:24])
                $fatal(1, "RESULT: FAIL SB touched other bytes");
            drain(20);
            mark("G3_other_line");
            ld(32'h600, g);                        // pre-fill the neighbour line
            block_aw = 1; block_w = 1;
            ld(32'h5C0, g);
            keep = g;
            st(32'h5C0, 32'hC0C0_C0C0, 4'hF);
            ld(32'h600, g);
            if (g === 32'hC0C0_C0C0) $fatal(1, "RESULT: FAIL forward crossed lines");
            drain(20);
            mark("G3_same_index");
            // 0x1640 and 0x640 share the D-cache index; only 0x1640 is cached, so
            // the hit must compare the full tag and must not forward the store.
            ld(32'h1640, g);
            keep = g;
            block_aw = 1; block_w = 1;
            st(32'h640, 32'hD0D0_D0D0, 4'hF);
            ld(32'h1640, g);
            if (g !== keep) $fatal(1, "RESULT: FAIL a same-index other-tag store changed a cached line");
            drain(20);
            mark("G3_promotion");
            block_aw = 1; block_w = 1;
            ld(32'h680, g);
            st(32'h680, 32'hE1E1_E1E1, 4'hF);
            st(32'h684, 32'hE2E2_E2E2, 4'hF);
            block_aw = 0; block_w = 0; w_hold = 6;
            @(posedge clk);
            while (pend_n == 2) @(posedge clk);
            ld(32'h684, g);
            if (g !== 32'hE2E2_E2E2) $fatal(1, "RESULT: FAIL promoted tail lost its forward %h", g);
            drain(30);

            // ===== G4 eligibility, registration, collision =====
            mark("G4_same_line_forward");
            block_aw = 1; block_w = 1;
            ld(32'h700, g);
            st(32'h700, 32'hF0F0_F0F0, 4'hF);
            ld(32'h704, g);                       // same line, other word: cache
            st(32'h704, 32'hF1F1_F1F1, 4'hF);
            ld(32'h704, g);
            if (g !== 32'hF1F1_F1F1) $fatal(1, "RESULT: FAIL tail forward on the same line");
            drain(40);
            mark("G4_completion_edge");
            // Real completion edge: the D line is cached, one store to that line is
            // queued with its AW already accepted, W is held back, and a same-line
            // load is presented so the DUT latches its overlap qualification on the
            // edge right before the completion. The old version dropped the load
            // after 10 edges while the W only landed later, so it proved nothing.
            block_aw = 0; block_w = 0; w_hold = 0; aw_hold = 0;
            ld(32'h740, g);                              // fill and cache the line
            @(negedge clk);
            block_w = 1;                                 // AW may go, W must not
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h740; wd <= 32'h1234_5678; ws <= 4'hF;
            @(posedge clk);
            if (!dr) $fatal(1, "RESULT: FAIL G4 setup store not accepted");
            dv <= 0; dw <= 0;
            for (k = 0; k < 20; k = k + 1) begin
                @(posedge clk);
                if (aw_sent) k = 20;
            end
            if (!aw_sent) $fatal(1, "RESULT: FAIL G4 setup AW was never accepted");
            @(negedge clk);
            dv <= 1; dw <= 0; da <= 32'h740;              // held same-line load
            @(posedge clk);                               // latches permit/same_line
            if (dr) $fatal(1, "RESULT: FAIL the same-line load was accepted before the completion edge");
            @(negedge clk);
            block_w = 0;                                  // next edge is the completion
            w_seen = 0; blk_seen = 0;
            for (k = 0; k < 20; k = k + 1) begin
                @(posedge clk);
                if (w_commit) begin
                    w_seen = 1;
                    if (!dr) blk_seen = 1;
                    if (dr) $fatal(1, "RESULT: FAIL same-line load accepted on the W completion edge");
                end
                if (dr) k = 20;
            end
            dv <= 0;
            if (!w_seen) $fatal(1, "RESULT: FAIL G4_completion_edge never saw the head W");
            if (!blk_seen) $fatal(1, "RESULT: FAIL the same-line load was not held across the completion edge");
            if (!dr) $fatal(1, "RESULT: FAIL the same-line load was never accepted after the completion");
            drain(40);

            mark("G4_head_other_line");
            // A load to a different cached line must still be accepted on the same
            // completion edge: only the matching line is held back.
            block_aw = 0; block_w = 0; w_hold = 0;
            ld(32'h780, g);                              // cache the other line
            @(negedge clk);
            block_w = 1;
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h740; wd <= 32'h5555_AAAA; ws <= 4'hF;
            @(posedge clk);
            if (!dr) $fatal(1, "RESULT: FAIL G4 other-line setup store not accepted");
            dv <= 0; dw <= 0;
            for (k = 0; k < 20; k = k + 1) begin
                @(posedge clk);
                if (aw_sent) k = 20;
            end
            if (!aw_sent) $fatal(1, "RESULT: FAIL G4 other-line AW was never accepted");
            @(negedge clk);
            dv <= 1; dw <= 0; da <= 32'h780;
            @(posedge clk);
            @(negedge clk);
            block_w = 0;
            got = 0;
            for (k = 0; k < 20; k = k + 1) begin
                @(posedge clk);
                if (w_commit && dr) got = 1;
                if (got) k = 20;
            end
            dv <= 0;
            if (!got)
                $fatal(1, "RESULT: FAIL a different-line load was stalled on the completion edge");
            drain(40);

            mark("G4_tail_same_line");
            // Same-line match covers BOTH entries: the tail blocks the load on the
            // head completion edge, and after the promotion the load still gets the
            // committed head value merged with the forwarded tail.
            block_aw = 0; block_w = 0; w_hold = 0;
            ld(32'h7C0, g);                              // cache the line
            @(negedge clk);
            block_w = 1;
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h7C0; wd <= 32'h0A0A_0A0A; ws <= 4'hF;
            @(posedge clk);
            if (!dr) $fatal(1, "RESULT: FAIL the head store was not accepted");
            dv <= 0; dw <= 0;
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h7C4; wd <= 32'h0B0B_0B0B; ws <= 4'hF;
            @(posedge clk);
            if (!dr) $fatal(1, "RESULT: FAIL the tail store was not accepted while the head is pending");
            dv <= 0; dw <= 0;
            for (k = 0; k < 20; k = k + 1) begin
                @(posedge clk);
                if (aw_sent) k = 20;
            end
            @(negedge clk);
            dv <= 1; dw <= 0; da <= 32'h7C0;
            @(posedge clk);
            @(negedge clk);
            block_w = 0;
            w_seen = 0; blk_seen = 0;
            for (k = 0; k < 20; k = k + 1) begin
                @(posedge clk);
                if (w_commit) begin
                    w_seen = 1;
                    if (!dr) blk_seen = 1;
                end
                if (dr) k = 20;
            end
            dv <= 0;
            if (!w_seen) $fatal(1, "RESULT: FAIL G4_tail_same_line never saw a head W");
            if (!blk_seen) $fatal(1, "RESULT: FAIL a matching tail did not hold the load across the completion edge");
            if (!dr) $fatal(1, "RESULT: FAIL the load after the promotion was never accepted");
            drain(40);
            mark("G4_two_stores_same_tag");
            block_aw = 1; block_w = 1;
            ld(32'h7C0, g);
            st(32'h7C4, 32'h0101_0101, 4'hF);
            st(32'h7C8, 32'h0202_0202, 4'hF);
            ld(32'h7CC, g);
            if (g !== word_of(mem[32'h7C0 / BYTES], 3))
                $fatal(1, "RESULT: FAIL untouched lane came from a forward");
            drain(30);

            // ===== G5 read miss, I query, conflicts =====
            mark("G5_no_ar");
            block_aw = 1; block_w = 1;
            st(32'h800, 32'h5151_5151, 4'hF);
            st(32'h840, 32'h5252_5252, 4'hF);
            @(negedge clk);
            dv <= 1; dw <= 0; da <= 32'h900;
            // The request stays valid until it is really accepted; dropping it after
            // a fixed number of edges would leave the trace with a silently
            // withdrawn load.
            for (k = 0; k < 6; k = k + 1) begin
                @(posedge clk);
                if (dr) $fatal(1, "RESULT: FAIL an uncached load was accepted while the queue is full");
                if (arvalid) $fatal(1, "RESULT: FAIL AR while writes are pending");
            end
            mark("G5_head_only");
            @(negedge clk);
            block_aw = 0; block_w = 0; w_hold = 4; aw_hold = 3;   // slow backend
            got = 0; blk_seen = 0;
            for (k = 0; k < 160; k = k + 1) begin
                @(posedge clk);
                if (pend_n == 1) blk_seen = 1;                 // only the tail left
                if (dr && pend_n != 0)
                    $fatal(1, "RESULT: FAIL the load was accepted before the queue drained");
                if (dr) got = 1;
                if (got) k = 160;
            end
            dv <= 0;
            if (!blk_seen) $fatal(1, "RESULT: FAIL the queue never reached a tail-only state");
            if (!got) $fatal(1, "RESULT: FAIL the uncached load was never accepted after the drain");
            drain(60);
            aw_hold = 0;
            mark("G5_i_park");
            block_aw = 1; block_w = 1;
            st(32'h880, 32'h5A5A_5A5A, 4'hF);
            @(negedge clk); iv <= 1; ia <= 32'hA00;
            @(posedge clk);
            while (!ir) @(posedge clk);
            iv <= 0;
            repeat (3) @(posedge clk);
            if (arvalid) $fatal(1, "RESULT: FAIL parked I miss issued AR before the drain");
            block_aw = 0; block_w = 0; w_hold = 0;
            @(posedge clk);
            while (!isv) @(posedge clk);
            drain(20);
            mark("G5_same_edge_store");
            block_aw = 0; block_w = 0; w_hold = 0;
            @(negedge clk);
            iv <= 1; ia <= 32'hB00; dv <= 1; dw <= 1; da <= 32'hB00;
            wd <= 32'hB0B0_B0B0; ws <= 4'hF;
            @(posedge clk);
            while (!ir || !dr) @(posedge clk);
            iv <= 0; dv <= 0;
            @(posedge clk);
            while (!isv) @(posedge clk);
            drain(20);
            mark("G5_later_load");
            ld(32'hC00, g);
            st(32'hC00, 32'hC0DE_0001, 4'hF);
            drain(30);
            ld(32'hC00, g);
            if (g !== 32'hC0DE_0001) $fatal(1, "RESULT: FAIL committed store invisible to a later load");

            // ===== G7 reset semantics =====
            mark("G7_head_only");
            block_aw = 1; block_w = 1;
            st(32'hD00, 32'hDEAD_0001, 4'hF);
            @(negedge clk); resetn = 0;
            repeat (3) @(negedge clk);
            resetn = 1;
            repeat (3) @(negedge clk);
            if (busy) $fatal(1, "RESULT: FAIL busy survived reset");
            block_aw = 0; block_w = 0;
            drain(20);
            if (mem[32'hD00 / BYTES][0 +: 32] === 32'hDEAD_0001)
                $fatal(1, "RESULT: FAIL cancelled store reached DDR");
            mark("G7_after_aw");
            block_aw = 0; block_w = 1;
            st(32'hD40, 32'hDEAD_0002, 4'hF);
            @(posedge clk);
            while (!awvalid) @(posedge clk);
            @(negedge clk); resetn = 0;
            repeat (3) @(negedge clk);
            resetn = 1;
            repeat (3) @(negedge clk);
            block_w = 0;
            drain(20);
            if (mem[32'hD40 / BYTES][0 +: 32] === 32'hDEAD_0002)
                $fatal(1, "RESULT: FAIL W issued after reset");
            mark("G7_full_reset");
            block_aw = 1; block_w = 1;
            st(32'hD80, 32'hDEAD_0003, 4'hF);
            st(32'hDC0, 32'hDEAD_0004, 4'hF);
            @(negedge clk); resetn = 0;
            repeat (3) @(negedge clk);
            resetn = 1;
            repeat (3) @(negedge clk);
            block_aw = 0; block_w = 0;
            drain(20);
            if (mem[32'hD80 / BYTES][0 +: 32] === 32'hDEAD_0003 ||
                mem[32'hDC0 / BYTES][0 +: 32] === 32'hDEAD_0004)
                $fatal(1, "RESULT: FAIL full-queue reset let a write through");
            mark("G7_new_epoch");
            st(32'hE00, 32'h600D_0001, 4'hF);
            drain(30);
            if (mem[32'hE00 / BYTES][0 +: 32] !== 32'h600D_0001)
                $fatal(1, "RESULT: FAIL new epoch could not store");
        end else begin
            // ===== short reference sequence, identical for old/new depth1 =====
            // Nothing here may assume a two-entry capacity: at depth 1 the second
            // store is only accepted after the head drains, so the request is held
            // valid while the backend is released in parallel.
            mark("S");
            block_aw = 1; block_w = 1; w_hold = 0; aw_hold = 0;
            st(32'h000, 32'hA1A1_A1A1, 4'hF);
            // Hold the second store valid from the first edge on. A depth-2 queue
            // has room and accepts it immediately; a depth-1 queue cannot, and the
            // backend is only released after the request has been offered while
            // blocked. Either way the request must stop being driven on the edge
            // that accepted it: leaving it high would let a depth-2 queue take the
            // same store twice (that was a real bug in this sequence).
            @(negedge clk);
            dv <= 1; dw <= 1; da <= 32'h0A0; wd <= 32'hB2B2_B2B2; ws <= 4'hF;
            got = 0;
            for (k = 0; k < 40; k = k + 1) begin
                @(posedge clk);
                if (dr) got = 1;
                if (k == 3 && !got) begin
                    block_aw = 0; block_w = 0; w_hold = 2;
                end
                if (got) k = 40;
            end
            dv <= 0; dw <= 0;
            if (!got) $fatal(1, "RESULT: FAIL short sequence: second store never accepted");
            drain(60);
            st(32'h1C0, 32'hD4D4_D4D4, 4'hF);
            drain(60);
            ld(32'h200, g);
            st(32'h200, 32'hE5E5_E5E5, 4'hF);
            ld(32'h200, g);
            if (g !== 32'hE5E5_E5E5) $fatal(1, "RESULT: FAIL short sequence forward");
            drain(40);
            mark("S_done");
        end

        repeat (4) @(negedge clk);
        // Nothing may be left outstanding: an unclosed request would make every
        // count above unverifiable.
        if (rq_head != rq_tail)
            $fatal(1, "RESULT: FAIL %0d data request(s) left unsettled", rq_tail - rq_head);
        if (iq_head != iq_tail)
            $fatal(1, "RESULT: FAIL %0d instruction request(s) left unsettled", iq_tail - iq_head);
        if (pend_n != 0 || busy)
            $fatal(1, "RESULT: FAIL write buffer not empty at the end (pend %0d busy %0d)", pend_n, busy);
        for (k = 0; k < 256; k = k + 1)
            $fwrite(fd, "P %0d %064h\n", k, {{(256-8*DQ){1'b0}}, mem[k]});
        $fwrite(fd, "S %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
                cyc, aw_cnt, w_cnt, ar_cnt, r_cnt, d_acc, d_rsp, i_acc, i_rsp, pend_n);
        $fwrite(fd, " %0d %0d %0d %0d %0d %0d %0d\n",
                store_acc, store_ack, load_rsp, inst_rsp, wb_cancel,
                front_cancel_st, front_cancel_ld);
        $fclose(fd);
        $display("RESULT: PASS wb2 edges=%0d aw=%0d w=%0d ar=%0d r=%0d dacc=%0d drsp=%0d iacc=%0d irsp=%0d",
                 cyc, aw_cnt, w_cnt, ar_cnt, r_cnt, d_acc, d_rsp, i_acc, i_rsp);
        $finish;
    end

    initial begin
        #2000000;
        $fatal(1, "RESULT: FAIL wall-clock watchdog");
    end
endmodule
