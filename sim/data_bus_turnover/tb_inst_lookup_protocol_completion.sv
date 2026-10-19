`timescale 1ns/1ps
// Task032 protocol-completion B-only top level (successor of the resume E top).
//
// One real x32 bridge (real icache/dcache vendor IP inside), one GRS instance.
// No cache/tag/valid/way_hit_q/state/ready/DRM output is ever deposited or forced:
// the caches start empty after reset and are filled only by legal DDR transactions.
//
// Race-free structure required by the plan:
//   * exactly one driver process, negedge only; it changes inputs and never touches
//     them at a posedge;
//   * exactly one monitor process, posedge only; it records the complete pre-edge
//     interface snapshot (the DUT's non-blocking updates land after this read), so
//     every field is the value that edge actually consumes;
//   * the driver consumes the monitor's flags on the following negedge.
//
// A token is presented until the monitor reports a real valid&&ready acceptance and
// is dropped at the next negedge. Nothing is re-presented implicitly, including
// across reset: every post-reset request is a new, explicitly declared token.
//
// Coverage completions over the resume E top (no edge number is ever faked):
//
//   1. TRUE SAME-EDGE AR/R. The driver runs one clock phase before the DUT consumes
//      the command, so the combinational `bus_arvalid` visible at a negedge is the
//      exact value the coming posedge samples (the DUT updates its registers only on
//      that posedge, in the NBA region, i.e. after the monitor's pre-NBA read). When
//      that combinational ARVALID will meet ARREADY at the coming posedge, the model
//      pre-drives RVALID/RDATA/RID/RLAST at the same negedge, so ARVALID&&ARREADY,
//      RVALID and the data are all present on one and the same posedge. `line_of()`
//      reads the byte memory after the previous edge's write commit and before the
//      coming edge's, i.e. memory as of that posedge. The delayed-return mode stays
//      and is still used everywhere except the windows that require the same edge.
//
//   2. MEMORY COMMITS ONLY ON A REAL W COMPLETION. AW acceptance merely latches the
//      owner address/data/strobe. The bytes change on f_w = WREADY && (AW accepted on
//      this edge || this owner's AW was accepted earlier), which mirrors the bridge's
//      write_buffer_complete (the user port has no WVALID). Between AW and W the byte
//      memory keeps the old bytes, and the address, data and strobe must all stay
//      stable until the W beat (checked below).
//
//   3. TRUE SIMULTANEOUS I/D REQUESTS. `present_i` and `present_d` may both be set, so
//      one edge can carry inst_req_valid and data_req_valid together; with DREADY high
//      the bridge raises IREADY low and takes only D, and the unaccepted I keeps its
//      fields until a later edge accepts it. Two declared scenarios do this.
//
//   4. BUILD-TIME SCENARIO IDENTITY. Each scenario number is fixed while the program
//      is built and written into the token table (plan.log) before execution starts;
//      the trace's cur_scen is only the run-time mirror of that same number. plan.log
//      also carries planned_cancel per token.
//
// +EDGE_LOG=<path>  per-posedge "E ..." snapshots, SCEN/TOK/BUS markers, SUM summary
// +PLAN_LOG=<path>  the stimulus token plan actually driven
module tb_inst_lookup_protocol_completion;
    GTP_GRS GRS_INST (.GRS_N(1'b1));

    logic clk = 1'b0;
    always #5 clk = ~clk;

    // ---------------------------------------------------------------- plan table
    localparam integer MAX_TOK = 128;
    localparam integer MAX_STEP = 1024;
    localparam integer T_I = 0, T_D = 1;
    localparam integer S_PRES = 0, S_WAIT_ACC = 1, S_WAIT_RSP = 2, S_IDLE = 3, S_DRAIN = 4,
                       S_CFG = 5, S_RST_AFTER_ACC = 6, S_RST_NOW = 7, S_SCEN = 8, S_END = 9;
    localparam integer C_AR_BLOCK = 0, C_R_SAME = 1, C_R_DLY = 2, C_AW_RDY = 3, C_W_RDY = 4;

    integer p_tgt [0:MAX_TOK-1];
    integer p_wr [0:MAX_TOK-1];
    integer p_size [0:MAX_TOK-1];
    integer p_scen [0:MAX_TOK-1];
    integer p_cancel [0:MAX_TOK-1];
    reg [31:0] p_addr [0:MAX_TOK-1];
    reg [31:0] p_wdata [0:MAX_TOK-1];
    reg [3:0] p_wstrb [0:MAX_TOK-1];

    integer s_kind [0:MAX_STEP-1];
    integer s_a [0:MAX_STEP-1];
    integer s_b [0:MAX_STEP-1];

    integer tok_n = 0, step_n = 0, scen_n = 0, build_scen = 0;
    integer cfg_ar_block = 0, cfg_r_same = 0, cfg_r_dly = 0, cfg_aw_rdy = 1, cfg_w_rdy = 1;
    reg next_cancel = 1'b0;

    // ------------------------------------------------------------ DDR user model
    reg m_ar_ready = 1'b0, m_aw_ready = 1'b0, m_w_ready = 1'b0;
    reg m_rvalid = 1'b0, m_rlast = 1'b0;
    reg [255:0] m_rdata = 256'b0;
    reg [3:0] m_rid = 4'b0;
    integer ar_block_left = 0, r_delay_left = 0;
    reg r_owed = 1'b0;
    reg same_pending = 1'b0;
    reg aw_owned = 1'b0;
    reg [27:0] ar_addr_lat = 28'b0;
    reg [3:0] ar_id_lat = 4'b0;
    reg [27:0] aw_addr_lat = 28'b0;
    reg [255:0] aw_wdata_lat = 256'b0;
    reg [31:0] aw_wstrb_lat = 32'b0;

    reg [7:0] dm [0:4095];

    function automatic [255:0] line_of(input [27:0] a);
        integer j, k;
        reg [31:0] w;
        begin
            line_of = 256'b0;
            for (j = 0; j < 8; j = j + 1) begin
                w = 32'b0;
                for (k = 0; k < 4; k = k + 1)
                    w[8*k +: 8] = dm[(a*4 + j*4 + k) & 4095];
                line_of[j*32 +: 32] = w;
            end
        end
    endfunction

    // --------------------------------------------------------------- DUT signals
    reg resetn = 1'b0, init_done = 1'b0;
    reg inst_req_valid = 1'b0;
    reg [31:0] inst_req_addr = 32'b0;
    reg data_req_valid = 1'b0, data_req_write = 1'b0;
    reg [1:0] data_req_size = 2'd2;
    reg [31:0] data_req_addr = 32'b0, data_req_wdata = 32'b0;
    reg [3:0] data_req_wstrb = 4'b0;
    wire inst_req_ready, inst_rsp_valid, inst_rsp_error, data_req_ready, data_rsp_valid, data_rsp_error;
    wire write_buffer_busy;
    wire [31:0] inst_rsp_rdata, data_rsp_rdata;
    wire [27:0] bus_awaddr, bus_araddr;
    wire bus_awuser_ap, bus_awvalid, bus_aruser_ap, bus_arvalid;
    wire [3:0] bus_awuser_id, bus_awlen, bus_aruser_id, bus_arlen;
    wire [255:0] bus_wdata;
    wire [31:0] bus_wstrb;

    dual_sram_to_pango_ddr_bridge #(
        .MEM_DQ_WIDTH(32), .INST_LINE_BUFFER_ENABLE(1),
        .DATA_LINE_BUFFER_ENABLE(1), .POSTED_WRITE_ENABLE(1)) dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(init_done), .write_buffer_busy(write_buffer_busy),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr),
        .inst_req_ready(inst_req_ready), .inst_rsp_valid(inst_rsp_valid),
        .inst_rsp_rdata(inst_rsp_rdata), .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(data_req_write),
        .data_req_size(data_req_size), .data_req_addr(data_req_addr),
        .data_req_wdata(data_req_wdata), .data_req_wstrb(data_req_wstrb),
        .data_req_ready(data_req_ready), .data_rsp_valid(data_rsp_valid),
        .data_rsp_rdata(data_rsp_rdata), .data_rsp_error(data_rsp_error),
        .axi_awaddr(bus_awaddr), .axi_awuser_ap(bus_awuser_ap), .axi_awuser_id(bus_awuser_id),
        .axi_awlen(bus_awlen), .axi_awready(m_aw_ready), .axi_awvalid(bus_awvalid),
        .axi_wdata(bus_wdata), .axi_wstrb(bus_wstrb), .axi_wready(m_w_ready),
        .axi_wusero_id(4'd1), .axi_wusero_last(m_w_ready),
        .axi_araddr(bus_araddr), .axi_aruser_ap(bus_aruser_ap), .axi_aruser_id(bus_aruser_id),
        .axi_arlen(bus_arlen), .axi_arready(m_ar_ready), .axi_arvalid(bus_arvalid),
        .axi_rdata(m_rdata), .axi_rid(m_rid), .axi_rlast(m_rlast), .axi_rvalid(m_rvalid));

    // ------------------------------------------------------------- monitor state
    integer edge_id = 0, cyc = 0;
    always @(posedge clk) cyc = cyc + 1;
    integer cur_scen = 0;
    reg f_i_acc = 0, f_d_acc = 0, f_rsp_i = 0, f_rsp_d = 0;
    reg f_ar = 0, f_aw = 0, f_w = 0, f_r = 0, f_dual = 0, f_reset = 0;
    reg [27:0] s_araddr = 0, s_awaddr = 0;
    reg [3:0] s_arid = 0;
    reg [255:0] s_wdata = 0;
    reg [31:0] s_wstrb = 0;
    integer m_edge = 0;
    integer edge_logged = 0, first_logged = 0;
    integer t_same = 0, t_dual = 0;

    // --------------------------------------------------------- driver bookkeeping
    integer tok_state [0:MAX_TOK-1];
    integer tok_acc_edge [0:MAX_TOK-1];
    integer present_i = -1, present_d = -1;
    integer pc_i = -1, pc_d = -1;
    integer t_acc = 0, t_rsp = 0, t_can = 0, t_reset = 0, t_ar = 0, t_r = 0, t_aw = 0, t_w = 0;
    integer t_mism = 0;
    reg was_reset = 1'b0;
    integer sp = 0, last_sp = -1, step_cnt = 0, wait_n = 0;
    reg program_ready = 1'b0;
    integer fd_edge, fd_plan;
    string edge_path, plan_path;

    // ------------------------------------------------------------------- utilities
    task automatic emit_plan(input integer t);
        begin
            $fdisplay(fd_plan, "PLAN %0d %0d %0d %0d %08x %0d %08x %01x %0d",
                      t, p_scen[t], p_tgt[t], p_wr[t], p_addr[t], p_size[t], p_wdata[t],
                      p_wstrb[t], p_cancel[t]);
        end
    endtask

    task automatic add_step(input integer kind, input integer a, input integer b);
        begin
            s_kind[step_n] = kind; s_a[step_n] = a; s_b[step_n] = b; step_n = step_n + 1;
        end
    endtask

    // The scenario number is fixed while the program is built, so PLAN carries the
    // real scenario identity instead of the not-yet-started run-time cur_scen.
    task automatic add_tok(input integer tgt, input integer wr, input [31:0] addr,
                           input integer size, input [31:0] wdata, input [3:0] wstrb);
        begin
            p_tgt[tok_n] = tgt; p_wr[tok_n] = wr; p_addr[tok_n] = addr; p_size[tok_n] = size;
            p_wdata[tok_n] = wdata; p_wstrb[tok_n] = wstrb; p_scen[tok_n] = build_scen;
            p_cancel[tok_n] = next_cancel; next_cancel = 1'b0;
            emit_plan(tok_n);
            tok_n = tok_n + 1;
        end
    endtask

    // Declare that the token added next is the one the upcoming reset cancels.
    task automatic CANC;
        begin next_cancel = 1'b1; end
    endtask

    task automatic TOK(input integer tgt, input integer wr, input [31:0] addr,
                       input integer size, input [31:0] wdata, input [3:0] wstrb);
        begin
            add_tok(tgt, wr, addr, size, wdata, wstrb);
            add_step(S_PRES, tgt, tok_n - 1);
            add_step(S_WAIT_ACC, tok_n - 1, 0);
            add_step(S_WAIT_RSP, tok_n - 1, 0);
        end
    endtask

    task automatic PRES(input integer tgt, input integer tok);
        begin add_step(S_PRES, tgt, tok); end
    endtask

    // Present a token and wait only for its acceptance; the response is awaited
    // later so configuration steps can run in between.
    task automatic TOKC(input integer tgt, input integer wr, input [31:0] addr,
                        input integer size, input [31:0] wdata, input [3:0] wstrb);
        begin
            add_tok(tgt, wr, addr, size, wdata, wstrb);
            add_step(S_PRES, tgt, tok_n - 1);
            add_step(S_WAIT_ACC, tok_n - 1, 0);
        end
    endtask

    task automatic WACC(input integer tok);
        begin add_step(S_WAIT_ACC, tok, 0); end
    endtask

    task automatic WRSP(input integer tok);
        begin add_step(S_WAIT_RSP, tok, 0); end
    endtask

    task automatic IDLE(input integer n);
        begin add_step(S_IDLE, n, 0); end
    endtask

    task automatic DRAIN;
        begin add_step(S_DRAIN, 0, 0); end
    endtask

    task automatic CFG(input integer key, input integer value);
        begin add_step(S_CFG, key, value); end
    endtask

    task automatic SCEN(input string name);
        begin
            build_scen = build_scen + 1;
            scen_n = build_scen;
            add_step(S_SCEN, build_scen, 0);
            $fdisplay(fd_edge, "SCEN %0d %0s", build_scen, name);
        end
    endtask

    // ------------------------------------------------------------- scenario program
    // The token table is the sealed completion plan: 44 tokens, 17 scenarios,
    // per-target order preserved. Tokens 2 and 31 are the two declared AR/R
    // same-posedge cases; scenarios 7 and 9 carry the true I/D dual-valid requests.
    task automatic build_program;
        integer i, t_i1, t_i2, t_d1;
        begin
            // 1: cold miss with delayed R, then the same line hits without AR
            SCEN("cold miss delayed R then same line hit");
            CFG(C_AR_BLOCK, 0); CFG(C_R_SAME, 0); CFG(C_R_DLY, 3);
            TOK(T_I, 0, 32'h4000_0000, 2, 0, 0);
            CFG(C_R_DLY, 0);
            TOK(T_I, 0, 32'h4000_0000, 2, 0, 0);
            DRAIN;

            // 2: AR/R on the same edge, then every lane of the filled line
            SCEN("AR R same edge then all eight lanes");
            CFG(C_R_SAME, 1);
            TOK(T_I, 0, 32'h4000_0040, 2, 0, 0);
            CFG(C_R_SAME, 0);
            for (i = 0; i < 8; i = i + 1)
                TOK(T_I, 0, 32'h4000_0040 + i*4, 2, 0, 0);
            DRAIN;

            // 3: at least three cycles of AR back pressure
            SCEN("AR back pressure and live decoy");
            CFG(C_AR_BLOCK, 3);
            TOK(T_I, 0, 32'h4000_0100, 2, 0, 0);
            CFG(C_AR_BLOCK, 0);
            DRAIN;

            // 4: hit to hit on a different index and lane
            SCEN("hit to hit different index and lane");
            TOK(T_I, 0, 32'h4000_0140, 2, 0, 0);
            TOK(T_I, 0, 32'h4000_0150, 2, 0, 0);
            TOK(T_I, 0, 32'h4000_0144, 2, 0, 0);
            DRAIN;

            // 5: hit to miss
            SCEN("hit to miss");
            TOK(T_I, 0, 32'h4000_0180, 2, 0, 0);
            TOK(T_I, 0, 32'h4000_0200, 2, 0, 0);
            DRAIN;

            // 6: miss response then hit
            SCEN("miss response then hit");
            TOK(T_I, 0, 32'h4000_0240, 2, 0, 0);
            TOK(T_I, 0, 32'h4000_0244, 2, 0, 0);
            DRAIN;

            // 7: one edge carries I_VALID and D_VALID together; D_READY wins, only D is
            //    accepted once and the untouched I keeps its fields until it is taken.
            SCEN("I response edge with D request data priority");
            CFG(C_R_SAME, 0); CFG(C_R_DLY, 0); CFG(C_AR_BLOCK, 0);
            t_i1 = tok_n;
            add_tok(T_I, 0, 32'h4000_0280, 2, 0, 0);
            t_d1 = tok_n;
            add_tok(T_D, 0, 32'h4000_0280, 2, 0, 0);
            PRES(T_I, t_i1);
            PRES(T_D, t_d1);          // both valid on the very next edge
            WACC(t_d1);               // D_READY=1 => I_READY=0: only D is taken here
            WACC(t_i1);               // the held I is accepted on a later edge
            WRSP(t_i1);
            WRSP(t_d1);
            DRAIN;

            // 8: D response edge also presents an I request
            SCEN("D response edge with I request");
            t_d1 = tok_n;
            add_tok(T_D, 0, 32'h4000_02c0, 2, 0, 0);
            t_i1 = tok_n;
            add_tok(T_I, 0, 32'h4000_02c0, 2, 0, 0);
            PRES(T_D, t_d1);
            WACC(t_d1);
            PRES(T_I, t_i1);
            WRSP(t_d1);
            WRSP(t_i1);
            DRAIN;

            // 9: posted store with AW not accepted plus a true dual present; the I hit
            //    is served while the store still owns the write buffer.
            SCEN("posted write AW not accepted");
            CFG(C_AW_RDY, 0); CFG(C_W_RDY, 1); CFG(C_R_SAME, 0);
            t_d1 = tok_n;
            add_tok(T_D, 1, 32'h4000_0300, 2, 32'h1122_3344, 4'hf);
            t_i1 = tok_n;
            add_tok(T_I, 0, 32'h4000_0000, 2, 0, 0);
            PRES(T_D, t_d1);
            PRES(T_I, t_i1);          // dual present again: D wins, I is held
            WACC(t_d1);
            WACC(t_i1);
            WRSP(t_d1);
            WRSP(t_i1);
            t_i2 = tok_n;
            TOKC(T_I, 0, 32'h4000_0340, 2, 0, 0);
            IDLE(2);
            CFG(C_AW_RDY, 1);
            WRSP(t_i2);
            DRAIN;

            // 10: AW accepted, W waiting
            SCEN("AW accepted W waiting");
            CFG(C_AW_RDY, 1); CFG(C_W_RDY, 0);
            TOK(T_D, 1, 32'h4000_0380, 2, 32'h5566_7788, 4'hf);
            TOK(T_I, 0, 32'h4000_0000, 2, 0, 0);
            TOKC(T_I, 0, 32'h4000_03c0, 2, 0, 0);
            IDLE(2);
            CFG(C_W_RDY, 1);
            WRSP(tok_n - 1);
            DRAIN;

            // 11: lookup miss presented on the edge where the posted write drains; its
            //     AR/R is a true same-posedge pair and the fill must contain the
            //     finished store bytes.
            SCEN("lookup miss with write drain boundary");
            CFG(C_AW_RDY, 1); CFG(C_W_RDY, 0);
            TOK(T_D, 1, 32'h4000_0400, 2, 32'h99aa_bbcc, 4'hf);
            TOK(T_I, 0, 32'h4000_0000, 2, 0, 0);
            IDLE(1);
            CFG(C_W_RDY, 1);
            CFG(C_R_SAME, 1);
            t_i1 = tok_n;
            TOKC(T_I, 0, 32'h4000_0408, 2, 0, 0);
            IDLE(1);
            WRSP(t_i1);
            CFG(C_R_SAME, 0);
            DRAIN;

            // 12: old I hit response on the same edge as an invalidating store
            SCEN("old I hit with same edge invalidating store");
            t_i1 = tok_n;
            TOK(T_I, 0, 32'h4000_0040, 2, 0, 0);
            t_i2 = tok_n;
            add_tok(T_I, 0, 32'h4000_0040, 2, 0, 0);
            t_d1 = tok_n;
            add_tok(T_D, 1, 32'h4000_0040, 2, 32'hdead_beef, 4'hf);
            PRES(T_I, t_i2);
            WACC(t_i2);
            PRES(T_D, t_d1);          // valid on the edge that consumes token t_i2's response
            WRSP(t_i2);
            WRSP(t_d1);
            DRAIN;

            // 13: same line written (full word then non-zero-lane partial strobe) and
            //     refetched through DDR; the untouched bytes must survive.
            SCEN("same line write then refetch");
            CFG(C_AW_RDY, 1); CFG(C_W_RDY, 1);
            TOK(T_D, 1, 32'h4000_0440, 2, 32'h0bad_f00d, 4'hf);
            TOK(T_D, 1, 32'h4000_0444, 2, 32'h0102_0304, 4'ha);
            TOK(T_I, 0, 32'h4000_0440, 2, 0, 0);
            DRAIN;

            // 14: idle with valid zero stays silent
            SCEN("idle valid zero silence");
            IDLE(4);
            DRAIN;

            // 15: reset between a hit acceptance and its response consumption
            SCEN("reset before consuming a registered hit");
            CANC;
            add_tok(T_I, 0, 32'h4000_0000, 2, 0, 0);
            PRES(T_I, tok_n - 1);
            WACC(tok_n - 1);
            add_step(S_RST_AFTER_ACC, tok_n - 1, 0);
            IDLE(2);
            TOK(T_I, 0, 32'h4000_0000, 2, 0, 0);
            DRAIN;

            // 16: reset while a miss can only wait for AR back pressure
            SCEN("reset at miss AR back pressure");
            CFG(C_AR_BLOCK, 6);
            CANC;
            add_tok(T_I, 0, 32'h4000_0480, 2, 0, 0);
            PRES(T_I, tok_n - 1);
            WACC(tok_n - 1);
            IDLE(2);
            add_step(S_RST_NOW, 0, 0);
            CFG(C_AR_BLOCK, 0);
            IDLE(2);
            TOK(T_I, 0, 32'h4000_0480, 2, 0, 0);
            DRAIN;

            // 17: reset while an accepted AR waits for R data
            SCEN("reset at RDATA wait");
            CFG(C_R_DLY, 8);
            CANC;
            add_tok(T_I, 0, 32'h4000_04c0, 2, 0, 0);
            PRES(T_I, tok_n - 1);
            WACC(tok_n - 1);
            IDLE(3);
            add_step(S_RST_NOW, 0, 0);
            CFG(C_R_DLY, 0);
            IDLE(2);
            TOK(T_I, 0, 32'h4000_04c0, 2, 0, 0);
            DRAIN;

            add_step(S_END, 0, 0);
        end
    endtask

    // ---------------------------------------------------------------------- monitor
    // Active region of every posedge, before the DUT's non-blocking updates: each
    // field below is exactly the value this edge consumes. Events are only credited
    // while reset is released; a reset edge performs no accept/response/DDR action.
    always @(posedge clk) begin
        edge_id = edge_id + 1;
        if (edge_id > 1) begin
            f_i_acc = inst_req_valid && inst_req_ready && resetn;
            f_d_acc = data_req_valid && data_req_ready && resetn;
            f_rsp_i = inst_rsp_valid && resetn;
            f_rsp_d = data_rsp_valid && resetn;
            f_ar    = bus_arvalid && m_ar_ready && resetn;
            f_aw    = bus_awvalid && m_aw_ready && resetn;
            f_w     = m_w_ready && (aw_owned || (bus_awvalid && m_aw_ready)) && resetn;
            f_r     = m_rvalid && resetn;
            f_dual  = inst_req_valid && data_req_valid && resetn;
            f_reset = !resetn;
            if (f_ar && f_r) t_same = t_same + 1;   // genuine AR/R on one posedge
            if (f_dual) t_dual = t_dual + 1;
            if (f_ar) begin s_araddr = bus_araddr; s_arid = bus_aruser_id; end
            if (f_aw) begin s_awaddr = bus_awaddr; s_wdata = bus_wdata; s_wstrb = bus_wstrb; end
            if (edge_logged == 0) first_logged = edge_id;
            edge_logged = edge_logged + 1;
            $fdisplay(fd_edge,
                "E %0d %0d %0d %0d %0b %0b %08x %0b %0b %0b %0d %08x %08x %01x %0b %08x %0b %08x %0b %0b %08x %0d %0b %0b %08x %064x %08x %0b %0b %064x %0d %0b %0b",
                edge_id, cur_scen, resetn, init_done,
                inst_req_valid, inst_req_ready, inst_req_addr,
                data_req_valid, data_req_ready, data_req_write, data_req_size, data_req_addr,
                data_req_wdata, data_req_wstrb,
                inst_rsp_valid, inst_rsp_rdata, data_rsp_valid, data_rsp_rdata,
                bus_arvalid, m_ar_ready, bus_araddr, bus_aruser_id,
                bus_awvalid, m_aw_ready, bus_awaddr, bus_wdata, bus_wstrb,
                m_w_ready, m_rvalid, m_rdata, m_rid, m_rlast, write_buffer_busy);
        end
    end

    // ----------------------------------------------------------------------- driver
    task automatic note_accept(input integer tok, input integer edge_id);
        begin
            if (tok < 0) begin
                t_mism = t_mism + 1;
                $fatal(1, "RESULT: FAIL protocol_completion accept with no presented token");
            end
            if (tok_state[tok] != 0) begin
                t_mism = t_mism + 1;
                $fatal(1, "RESULT: FAIL protocol_completion token %0d accepted twice", tok);
            end
            tok_state[tok] = 1;
            tok_acc_edge[tok] = edge_id;
            t_acc = t_acc + 1;
            if (p_tgt[tok] == T_I) pc_i = tok; else pc_d = tok;
            $fdisplay(fd_edge, "TOK %0d %0d ACC %0d", edge_id, tok, p_tgt[tok]);
        end
    endtask

    task automatic note_response(input integer tgt, input integer edge_id);
        integer tok;
        begin
            tok = (tgt == T_I) ? pc_i : pc_d;
            if (tok < 0) begin
                t_mism = t_mism + 1;
                $fatal(1, "RESULT: FAIL protocol_completion response without owner");
            end
            tok_state[tok] = 2;
            t_rsp = t_rsp + 1;
            if (tgt == T_I) pc_i = -1; else pc_d = -1;
            $fdisplay(fd_edge, "TOK %0d %0d RSP", edge_id, tok);
        end
    endtask

    task automatic note_cancel(input integer edge_id);
        integer i;
        begin
            for (i = 0; i < tok_n; i = i + 1) begin
                if (tok_state[i] == 1) begin
                    tok_state[i] = 3;
                    t_can = t_can + 1;
                    $fdisplay(fd_edge, "TOK %0d %0d CAN %0d", edge_id, i, tok_acc_edge[i]);
                end
            end
            pc_i = -1; pc_d = -1; present_i = -1; present_d = -1;
        end
    endtask

    task automatic drive_inputs;
        begin
            if (present_i >= 0) begin
                inst_req_valid = 1'b1;
                inst_req_addr = p_addr[present_i];
            end else begin
                inst_req_valid = 1'b0;
                inst_req_addr = 32'b0;
            end
            if (present_d >= 0) begin
                data_req_valid = 1'b1;
                data_req_write = (p_wr[present_d] != 0);
                data_req_size  = p_size[present_d][1:0];
                data_req_addr  = p_addr[present_d];
                data_req_wdata = p_wdata[present_d];
                data_req_wstrb = p_wstrb[present_d];
            end else begin
                data_req_valid = 1'b0;
                data_req_write = 1'b0;
                data_req_addr  = 32'b0;
            end
        end
    endtask

    task automatic do_reset;
        begin
            present_i = -1; present_d = -1;
            inst_req_valid = 1'b0; data_req_valid = 1'b0;
            resetn = 1'b0;
            drive_inputs();
            @(negedge clk);                       // first negedge whose posedge sampled reset low
            if (!was_reset) begin
                was_reset = 1'b1;
                t_reset = t_reset + 1;
                note_cancel(edge_id);
            end
            m_ar_ready = 1'b0; m_aw_ready = 1'b0; m_w_ready = 1'b0;
            m_rvalid = 1'b0; m_rlast = 1'b0;
            r_owed = 1'b0; same_pending = 1'b0; r_delay_left = 0; ar_block_left = 0;
            aw_owned = 1'b0;
            repeat (2) @(negedge clk);
            resetn = 1'b1;
            init_done = 1'b1;
            repeat (2) @(negedge clk);
            was_reset = 1'b0;
        end
    endtask

    // A write beat commits the byte memory only here, and only from the fields the
    // very edge sampled. AW acceptance alone never touches the memory.
    task automatic commit_write;
        integer lane, j;
        reg [27:0] a;
        begin
            if (aw_owned) begin
                if (bus_awaddr !== aw_addr_lat) begin
                    t_mism = t_mism + 1;
                    $fatal(1, "RESULT: FAIL protocol_completion AW address not stable for W");
                end
                if (bus_wdata !== aw_wdata_lat) begin
                    t_mism = t_mism + 1;
                    $fatal(1, "RESULT: FAIL protocol_completion AW data not stable for W");
                end
                if (bus_wstrb !== aw_wstrb_lat) begin
                    t_mism = t_mism + 1;
                    $fatal(1, "RESULT: FAIL protocol_completion AW strobe not stable for W");
                end
                a = aw_addr_lat;
            end else begin
                a = bus_awaddr;      // this edge accepts AW and completes W together
            end
            for (lane = 0; lane < 8; lane = lane + 1)
                for (j = 0; j < 4; j = j + 1)
                    if (bus_wstrb[lane*4 + j])
                        dm[(a*4 + lane*4 + j) & 4095] = bus_wdata[lane*32 + j*8 +: 8];
        end
    endtask

    // DDR model: reacts only on negedge, using the monitor's latched flags/fields and
    // the combinational bus_arvalid that the coming posedge will sample. Memory is as
    // of just before that posedge: the previous edge's W bytes were committed above,
    // the coming edge's W bytes are not committed until the following negedge.
    task automatic ddr_model;
        integer will_ar_ready;
        begin
            if (f_r) begin m_rvalid = 1'b0; m_rlast = 1'b0; end
            will_ar_ready = (ar_block_left > 0) ? 0 : 1;
            if (r_owed) begin
                if (r_delay_left > 0) begin
                    r_delay_left = r_delay_left - 1;
                end else begin
                    m_rdata = line_of(ar_addr_lat);
                    m_rid = ar_id_lat; m_rvalid = 1'b1; m_rlast = 1'b1;
                    r_owed = 1'b0;
                end
            end else if (cfg_r_same && !same_pending && will_ar_ready && resetn && init_done &&
                         bus_arvalid) begin
                // True same-edge return: ARVALID here is the combinational value the
                // coming posedge consumes and ARREADY is driven below, so that posedge
                // sees ar_v && ar_r && r_v together in one pre-NBA snapshot.
                m_rdata = line_of(bus_araddr);
                m_rid   = bus_aruser_id;
                m_rvalid = 1'b1; m_rlast = 1'b1;
                same_pending = 1'b1;
            end else if (f_ar && !same_pending) begin
                ar_addr_lat = s_araddr; ar_id_lat = s_arid;
                r_owed = 1'b1; r_delay_left = cfg_r_dly;
            end
            if (same_pending && f_ar) same_pending = 1'b0;
            m_ar_ready = will_ar_ready ? 1'b1 : 1'b0;
            if (ar_block_left > 0) ar_block_left = ar_block_left - 1;
            m_aw_ready = (cfg_aw_rdy != 0);
            m_w_ready  = (cfg_w_rdy != 0);
        end
    endtask

    function automatic integer step_ready(input integer idx);
        begin
            step_ready = 1'b1;
            case (s_kind[idx])
                S_WAIT_ACC: step_ready = (tok_state[s_a[idx]] != 0);
                S_WAIT_RSP: step_ready = (tok_state[s_a[idx]] >= 2);
                S_IDLE:     step_ready = (step_cnt >= s_a[idx]);
                S_DRAIN:    step_ready = (pc_i < 0 && pc_d < 0 && present_i < 0 && present_d < 0 &&
                                          !bus_arvalid && !bus_awvalid && !r_owed && !same_pending);
                S_RST_AFTER_ACC: step_ready = (tok_state[s_a[idx]] != 0);
                default:    step_ready = 1'b1;
            endcase
        end
    endfunction

    always @(negedge clk) begin
        if (program_ready) begin
            // ---- 1. consume the last edge (resets are handled inside do_reset)
            begin
                if (f_rsp_i) note_response(T_I, edge_id);
                if (f_rsp_d) note_response(T_D, edge_id);
                if (f_i_acc && f_d_acc) begin
                    t_mism = t_mism + 1;
                    $fatal(1, "RESULT: FAIL protocol_completion I and D accepted on the same edge");
                end
                if (f_i_acc) begin note_accept(present_i, edge_id); present_i = -1; end
                if (f_d_acc) begin note_accept(present_d, edge_id); present_d = -1; end
                if (f_aw) begin
                    aw_owned = 1'b1;
                    aw_addr_lat = bus_awaddr;
                    aw_wdata_lat = bus_wdata;
                    aw_wstrb_lat = bus_wstrb;
                    t_aw = t_aw + 1;
                    $fdisplay(fd_edge, "BUS %0d AW", edge_id);
                end
                if (f_w) begin
                    commit_write();
                    t_w = t_w + 1;
                    $fdisplay(fd_edge, "BUS %0d W", edge_id);
                    aw_owned = 1'b0;
                end
                if (f_ar) begin t_ar = t_ar + 1; $fdisplay(fd_edge, "BUS %0d AR", edge_id); end
                if (f_r)  begin t_r  = t_r  + 1; $fdisplay(fd_edge, "BUS %0d R", edge_id); end
                ddr_model();
            end

            // ---- 2. advance the step program
            if (sp != last_sp) begin last_sp = sp; step_cnt = 0; end
            else step_cnt = step_cnt + 1;
            while (sp < step_n && step_ready(sp)) begin
                case (s_kind[sp])
                    S_PRES: begin
                        if (s_a[sp] == T_I) present_i = s_b[sp]; else present_d = s_b[sp];
                        sp = sp + 1;
                    end
                    S_CFG: begin
                        case (s_a[sp])
                            C_AR_BLOCK: ar_block_left = s_b[sp];
                            C_R_SAME:   cfg_r_same = s_b[sp];
                            C_R_DLY:    cfg_r_dly = s_b[sp];
                            C_AW_RDY:   cfg_aw_rdy = s_b[sp];
                            C_W_RDY:    cfg_w_rdy = s_b[sp];
                        endcase
                        sp = sp + 1;
                    end
                    S_SCEN: begin cur_scen = s_a[sp]; sp = sp + 1; end
                    S_RST_AFTER_ACC: begin do_reset(); sp = sp + 1; end
                    S_RST_NOW: begin do_reset(); sp = sp + 1; end
                    default: sp = sp + 1;
                endcase
                last_sp = -1;
            end
            drive_inputs();
        end else begin
            drive_inputs();
        end
    end

    // --------------------------------------------------------------------- control
    integer i;
    initial begin
        if (!$value$plusargs("EDGE_LOG=%s", edge_path)) $fatal(1, "RESULT: FAIL missing +EDGE_LOG");
        if (!$value$plusargs("PLAN_LOG=%s", plan_path)) $fatal(1, "RESULT: FAIL missing +PLAN_LOG");
        fd_edge = $fopen(edge_path, "w");
        fd_plan = $fopen(plan_path, "w");
        if (!fd_edge || !fd_plan) $fatal(1, "RESULT: FAIL cannot open trace files");
        for (i = 0; i < 4096; i = i + 1) dm[i] = (i[7:0] * 8'h2B) + 8'h5A;
        for (i = 0; i < MAX_TOK; i = i + 1) tok_state[i] = 0;
        build_program();
        program_ready = 1'b1;
        repeat (4) @(negedge clk);
        resetn = 1'b1;
        init_done = 1'b1;
        wait (sp >= step_n);
        repeat (3) @(negedge clk);
        $fdisplay(fd_edge, "SUM scenarios=%0d tokens=%0d accepts=%0d responses=%0d cancels=%0d resets=%0d ar=%0d r=%0d aw=%0d w=%0d edges=%0d mismatches=%0d",
                  scen_n, tok_n, t_acc, t_rsp, t_can, t_reset, t_ar, t_r, t_aw, t_w, edge_id, t_mism);
        if (t_mism != 0 || t_acc != t_rsp + t_can) begin
            $fdisplay(fd_edge, "RESULT: FAIL protocol_completion conservation");
            $fatal(1, "RESULT: FAIL protocol_completion conservation");
        end
        // The edge counter and the number of logged snapshots differ by the first
        // posedge (edge_id 1) which is never logged; both are reported separately.
        $display("EDGES counter=%0d logged=%0d first_logged=%0d",
                 edge_id, edge_logged, first_logged);
        $display("RESULT: PASS inst_lookup_protocol_completion scenarios=%0d tokens=%0d accepts=%0d responses=%0d cancels=%0d resets=%0d ar=%0d r=%0d aw=%0d w=%0d ar_r_same=%0d dual_present=%0d edges=%0d mismatches=0",
                 scen_n, tok_n, t_acc, t_rsp, t_can, t_reset, t_ar, t_r, t_aw, t_w,
                 t_same, t_dual, edge_id);
        $fclose(fd_edge);
        $fclose(fd_plan);
        $finish;
    end

    initial begin
        #4000000;
        $fatal(1, "RESULT: FAIL protocol_completion watchdog");
    end
endmodule
