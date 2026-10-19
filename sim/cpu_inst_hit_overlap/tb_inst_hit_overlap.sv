`timescale 1ns/1ps
// Task033 bridge job: one TB, one frozen plan, only the new parameter differs.
// Stimulus changes on the falling edge. The edge log records the values sampled
// just before every rising edge (PRE) and the values after NBA/DRM settle (POST).
// The checker recomputes every expectation from the plan, the model's frozen
// initial memory and this log.
module tb_inst_hit_overlap #(parameter integer OVERLAP = 1);
    GTP_GRS GRS_INST (.GRS_N(1'b1));

    localparam integer MAXT = 700;
    localparam integer KIND_I  = 0;
    localparam integer KIND_D  = 1;
    localparam integer KIND_W  = 2;
    localparam integer KIND_PI = 3;
    localparam integer KIND_PD = 4;
    localparam integer KIND_X  = 5;
    localparam integer KIND_K  = 6;
    localparam integer KIND_M  = 7;
    localparam integer KIND_R  = 8;
    localparam integer KIND_E  = 9;
    localparam integer KIND_WAIT = 10;

    reg clk = 0;
    always #5 clk = ~clk;

    reg resetn = 0, init_done = 0;
    reg iv = 0, dv = 0, dw = 0;
    reg [31:0] ia = 0, da = 0, dwdata = 0;
    reg [3:0] dstrb = 0;
    reg [1:0] dsize = 2'd2;
    wire ir, dr, ip, dp, ie, de, busy;
    wire [31:0] idata, ddata;
    wire [27:0] ara, awa;
    wire arv, awv, arr, awr, wrdy, rv;
    wire [3:0] ari, awid, arlen, awlen;
    wire [255:0] wd, rd;
    wire [31:0] ws;
    wire [3:0] rid;
    wire rlast;
    wire ar_ap, aw_ap;

    dual_sram_to_pango_ddr_bridge #(
        .MEM_DQ_WIDTH(32),
        .INST_LINE_BUFFER_ENABLE(1),
        .DATA_LINE_BUFFER_ENABLE(1),
        .CAMERA_UNCACHED_ENABLE(1),
        .PREPROCESS_UNCACHED_ENABLE(1),
        .POSTED_WRITE_ENABLE(1),
        .DATA_READ_UNDER_WRITE_ENABLE(1),
        .DATA_STORE_FORWARD_ENABLE(1),
        .WRITE_BUFFER_TURNOVER_ENABLE(1),
        .INST_HIT_UNDER_DATA_MISS_ENABLE(OVERLAP)
    ) dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(init_done),
        .write_buffer_busy(busy),
        .inst_req_valid(iv), .inst_req_addr(ia), .inst_req_ready(ir),
        .inst_rsp_valid(ip), .inst_rsp_rdata(idata), .inst_rsp_error(ie),
        .data_req_valid(dv), .data_req_write(dw), .data_req_size(dsize),
        .data_req_addr(da), .data_req_wdata(dwdata), .data_req_wstrb(dstrb),
        .data_req_ready(dr), .data_rsp_valid(dp), .data_rsp_rdata(ddata),
        .data_rsp_error(de),
        .axi_awaddr(awa), .axi_awuser_ap(aw_ap), .axi_awuser_id(awid),
        .axi_awlen(awlen), .axi_awready(awr), .axi_awvalid(awv),
        .axi_wdata(wd), .axi_wstrb(ws), .axi_wready(wrdy),
        .axi_wusero_id(4'd1), .axi_wusero_last(wrdy),
        .axi_araddr(ara), .axi_aruser_ap(ar_ap), .axi_aruser_id(ari),
        .axi_arlen(arlen), .axi_arready(arr), .axi_arvalid(arv),
        .axi_rdata(rd), .axi_rid(rid), .axi_rlast(rlast), .axi_rvalid(rv)
    );

    overlap_ddr_model ddr (
        .clk(clk), .resetn(resetn), .init_done(init_done),
        .awaddr(awa), .awvalid(awv), .awready(awr),
        .wdata(wd), .wstrb(ws), .wready(wrdy),
        .araddr(ara), .aruser_id(ari), .arvalid(arv), .arready(arr),
        .rdata(rd), .rvalid(rv), .rid(rid), .rlast(rlast)
    );

    // ---------- frozen plan ----------
    integer t_count = 0;
    integer t_kind [0:MAXT-1];
    reg [31:0] t_addr [0:MAXT-1];
    reg [31:0] t_data [0:MAXT-1];
    reg [3:0]  t_strb [0:MAXT-1];
    integer t_size [0:MAXT-1];
    integer t_wmode [0:MAXT-1];
    integer t_warg [0:MAXT-1];
    integer t_grp [0:MAXT-1];
    string  t_scen [0:MAXT-1];

    integer fd, tfd;
    string edge_path, plan_path, mem_path, tok_path;
    // Observation-only debug trace, disabled unless +DBGLOG=<path> is given.
    integer dfd = 0;
    string dbg_path;
    initial begin
        if ($value$plusargs("DBGLOG=%s", dbg_path)) dfd = $fopen(dbg_path, "w");
    end

    integer n = 0;
    integer ar_stall = 0;
    integer rsp_cyc = 0;
    integer irsp_cyc = 0;
    integer ar_fire = 0;
    integer aw_open = 0;
    integer epoch = 0;
    integer d_inflight_cycles = 0;
    reg     d_wait_active = 0;
    integer i_acc = 0, i_rsp = 0, d_acc = 0, d_rsp = 0;

    reg acc [0:MAXT-1];
    reg fin [0:MAXT-1];
    reg rel [0:MAXT-1];
    integer holds [0:MAXT-1];
    integer tok_accept [0:MAXT-1];

    task automatic log_line(input string ph);
        begin
            $fdisplay(fd, "E n=%0d ph=%s rst=%0b init=%0b iv=%0b ir=%0b ia=%08x dv=%0b dr=%0b dw=%0b sz=%0d da=%08x dwd=%08x ds=%01x ip=%0b ie=%0b id=%08x dp=%0b de=%0b dd=%08x busy=%0b arv=%0b arr=%0b ara=%07x ari=%01x arl=%01x awv=%0b awr=%0b awa=%07x awi=%01x awl=%01x wrdy=%0b wdv=%064x wsv=%08x rv=%0b rdv=%064x rid=%01x rl=%0b ep=%0d",
                n, ph, resetn, init_done, iv, ir, ia, dv, dr, dw, dsize, da, dwdata, dstrb,
                ip, ie, idata, dp, de, ddata, busy,
                arv, arr, ara, ari, arlen, awv, awr, awa, awid, awlen, wrdy, wd, ws,
                rv, rd, rid, rlast, epoch);
        end
    endtask

    always @(posedge clk) begin
        n = n + 1;
        log_line("PRE");
        if (arv && !arr) ar_stall = ar_stall + 1;
        else ar_stall = 0;
        if (arv && arr) ar_fire = ar_fire + 1;
        if (awv && awr) aw_open = 1;
        if (wrdy) aw_open = 0;
        if (d_wait_active && !dp) d_inflight_cycles = d_inflight_cycles + 1;
        if (dp) d_wait_active = 0;
        if (ip) i_rsp = i_rsp + 1;
        if (dp) d_rsp = d_rsp + 1;
        if (iv && ir) i_acc = i_acc + 1;
        if (dv && dr) d_acc = d_acc + 1;
        if (dfd) $fdisplay(dfd, "D %0d state=%0d arv=%b arr=%b busy=%b ilh=%b pend=%b ip=%b dp=%b iv=%b ir=%b",
                            n, dut.state, arv, arr, busy, dut.inst_line_hit,
                            dut.inst_overlap_pending, ip, dp, iv, ir);
        #1;
        rsp_cyc = dp;
        irsp_cyc = ip;
        log_line("POST");
        if (n > 100000) $fatal(1, "RESULT: FAIL cycle watchdog");
    end

    function automatic integer kind_of(input string k);
        begin
            case (k)
                "I":  kind_of = KIND_I;
                "D":  kind_of = KIND_D;
                "W":  kind_of = KIND_W;
                "PI": kind_of = KIND_PI;
                "PD": kind_of = KIND_PD;
                "X":  kind_of = KIND_X;
                "K":  kind_of = KIND_K;
                "M":  kind_of = KIND_M;
                "R":  kind_of = KIND_R;
                "E":  kind_of = KIND_E;
                "WAIT": kind_of = KIND_WAIT;
                default: kind_of = -1;
            endcase
        end
    endfunction

    task automatic release_wait(input integer idx);
        integer cond, arg, base;
        begin
            cond = t_wmode[idx];
            arg  = t_warg[idx];
            case (cond)
                0: ;
                1: repeat (arg) @(negedge clk);
                2: while (ar_stall < arg) @(negedge clk);
                3: while (d_inflight_cycles < arg) @(negedge clk);
                4: while (!busy) @(negedge clk);
                5: while (!aw_open) @(negedge clk);
                6: while (!(rsp_cyc || (d_acc == d_rsp))) @(negedge clk);
                7: while (!rsp_cyc) @(negedge clk);
                8: while (!(irsp_cyc || (i_acc == i_rsp))) @(negedge clk);
                9: begin
                       base = ar_fire;
                       while (ar_fire == base) @(negedge clk);
                       @(negedge clk);
                   end
                10: while (busy) @(negedge clk);
                default: ;
            endcase
        end
    endtask

    task automatic drive_token(input integer idx);
        begin
            case (t_kind[idx])
                KIND_I: begin
                    ia = t_addr[idx]; iv = 1'b1;
                end
                KIND_D: begin
                    da = t_addr[idx]; dv = 1'b1; dw = 1'b0;
                    dsize = t_size[idx]; dwdata = 32'b0; dstrb = 4'b0;
                end
                KIND_W: begin
                    da = t_addr[idx]; dv = 1'b1; dw = 1'b1;
                    dsize = t_size[idx]; dwdata = t_data[idx]; dstrb = t_strb[idx];
                end
                KIND_PI: begin
                    ia = t_addr[idx]; iv = 1'b1;
                end
                KIND_PD: begin
                    da = t_addr[idx]; dv = 1'b1; dw = 1'b0;
                    dsize = t_size[idx]; dstrb = 4'b0;
                end
                default: ;
            endcase
        end
    endtask

    task automatic undo_token(input integer idx);
        begin
            case (t_kind[idx])
                KIND_I, KIND_PI: iv = 1'b0;
                KIND_D, KIND_W, KIND_PD: dv = 1'b0;
                default: ;
            endcase
        end
    endtask

    task automatic run_group(input integer gi, input integer gj);
        integer kk, done_cnt, last_progress;
        begin
            for (kk = gi; kk < gj; kk = kk + 1) begin
                acc[kk] = 1'b0; fin[kk] = 1'b0; rel[kk] = 1'b0; holds[kk] = 0;
                tok_accept[kk] = 32'hffff_ffff;
                drive_token(kk);
                $fdisplay(tfd, "P %0d %s kind=%0d addr=%08x edge=%0d",
                          kk, t_scen[kk], t_kind[kk], t_addr[kk], n);
            end
            done_cnt = gj - gi;
            last_progress = n;
            while (done_cnt > 0) begin
                @(posedge clk);
                for (kk = gi; kk < gj; kk = kk + 1) begin
                    if (!fin[kk]) begin
                        if (t_kind[kk] == KIND_PI) begin
                            if (ir) $fatal(1, "RESULT: FAIL probe I accepted %0d %s edge=%0d",
                                           kk, t_scen[kk], n);
                            holds[kk] = holds[kk] + 1;
                            if (holds[kk] >= t_warg[kk]) begin
                                fin[kk] = 1'b1; rel[kk] = 1'b1; done_cnt = done_cnt - 1;
                                $fdisplay(tfd, "N %0d %s held=%0d edge=%0d", kk, t_scen[kk], holds[kk], n);
                            end
                        end else if (t_kind[kk] == KIND_PD) begin
                            if (dr) $fatal(1, "RESULT: FAIL probe D accepted %0d %s edge=%0d",
                                           kk, t_scen[kk], n);
                            holds[kk] = holds[kk] + 1;
                            if (holds[kk] >= t_warg[kk]) begin
                                fin[kk] = 1'b1; rel[kk] = 1'b1; done_cnt = done_cnt - 1;
                                $fdisplay(tfd, "N %0d %s held=%0d edge=%0d", kk, t_scen[kk], holds[kk], n);
                            end
                        end else if (t_kind[kk] == KIND_I) begin
                            if (iv && ir) begin
                                fin[kk] = 1'b1; rel[kk] = 1'b1; acc[kk] = 1'b1;
                                tok_accept[kk] = n; done_cnt = done_cnt - 1;
                                $fdisplay(tfd, "A %0d %s edge=%0d", kk, t_scen[kk], n);
                            end
                        end else if ((t_kind[kk] == KIND_D) || (t_kind[kk] == KIND_W)) begin
                            if (dv && dr) begin
                                fin[kk] = 1'b1; rel[kk] = 1'b1; acc[kk] = 1'b1;
                                tok_accept[kk] = n; done_cnt = done_cnt - 1;
                                $fdisplay(tfd, "A %0d %s edge=%0d", kk, t_scen[kk], n);
                                if (t_kind[kk] == KIND_D) begin
                                    d_wait_active = 1'b1; d_inflight_cycles = 0;
                                end
                            end
                        end
                    end
                end
                if (done_cnt > 0 && (n - last_progress) > 400)
                    $fatal(1, "RESULT: FAIL group %0d accept watchdog", gi);
                @(negedge clk);
                for (kk = gi; kk < gj; kk = kk + 1)
                    if (rel[kk]) begin undo_token(kk); rel[kk] = 1'b0; end
            end
        end
    endtask

    integer gi, gj, kk, j, idx, plan_rc;
    string tag, kstr, scen;
    reg [31:0] pa, pd;
    reg [3:0] ps;
    integer psz, pwm, pwa, pg;

    initial begin : run
        if (!$value$plusargs("PLAN=%s", plan_path)) $fatal(1, "RESULT: FAIL missing PLAN");
        if (!$value$plusargs("EDGE_LOG=%s", edge_path)) $fatal(1, "RESULT: FAIL missing EDGE_LOG");
        if (!$value$plusargs("TOK_LOG=%s", tok_path)) $fatal(1, "RESULT: FAIL missing TOK_LOG");
        if (!$value$plusargs("MEM_DUMP=%s", mem_path)) $fatal(1, "RESULT: FAIL missing MEM_DUMP");
        fd  = $fopen(edge_path, "w");
        tfd = $fopen(tok_path, "w");
        if (!fd || !tfd) $fatal(1, "RESULT: FAIL cannot open logs");

        begin : parse
            integer pf;
            pf = $fopen(plan_path, "r");
            if (!pf) $fatal(1, "RESULT: FAIL cannot open plan");
            while (!$feof(pf)) begin
                plan_rc = $fscanf(pf, "%s %d %s %h %h %h %d %d %d %d %s\n",
                                  tag, idx, kstr, pa, pd, ps, psz, pwm, pwa, pg, scen);
                if (plan_rc == 11) begin
                    if (idx != t_count) $fatal(1, "RESULT: FAIL plan index %0d expected %0d", idx, t_count);
                    t_kind[t_count] = kind_of(kstr);
                    if (t_kind[t_count] < 0) $fatal(1, "RESULT: FAIL plan kind %s", kstr);
                    t_addr[t_count] = pa;
                    t_data[t_count] = pd;
                    t_strb[t_count] = ps;
                    t_size[t_count] = psz;
                    t_wmode[t_count] = pwm;
                    t_warg[t_count] = pwa;
                    t_grp[t_count] = pg;
                    t_scen[t_count] = scen;
                    t_count = t_count + 1;
                    if (t_count >= MAXT) $fatal(1, "RESULT: FAIL plan too long");
                end
            end
            $fclose(pf);
            if (t_count == 0) $fatal(1, "RESULT: FAIL empty plan");
            $display("PLAN tokens=%0d overlap=%0d", t_count, OVERLAP);
        end

        resetn = 0; init_done = 0;
        repeat (3) @(negedge clk);
        resetn = 1; init_done = 1;
        @(negedge clk);

        gi = 0;
        while (gi < t_count) begin
            gj = gi + 1;
            while (gj < t_count && t_grp[gj] == t_grp[gi]) gj = gj + 1;
            case (t_kind[gi])
                KIND_K: begin
                    case (t_addr[gi])
                        1: ddr.ar_block  = t_data[gi];
                        2: ddr.r_lat     = t_data[gi];
                        3: ddr.aw_block  = t_data[gi];
                        4: ddr.w_lat     = t_data[gi];
                        5: ddr.r_hold    = t_data[gi];
                        6: ddr.instant_r = t_data[gi];
                        7: ddr.instant_w = t_data[gi];
                        default: $fatal(1, "RESULT: FAIL unknown knob %0d", t_addr[gi]);
                    endcase
                    $fdisplay(tfd, "K %0d knob=%0d val=%0d edge=%0d", gi, t_addr[gi], t_data[gi], n);
                    gi = gj;
                end
                KIND_M: begin
                    ddr.poke(t_addr[gi], t_data[gi], t_strb[gi]);
                    $fdisplay(tfd, "M %0d addr=%08x data=%08x strb=%01x edge=%0d",
                              gi, t_addr[gi], t_data[gi], t_strb[gi], n);
                    gi = gj;
                end
                KIND_R: begin
                    if (t_data[gi] == 0) begin
                        resetn = 0; init_done = 0; iv = 0; dv = 0;
                        repeat (2) @(negedge clk);
                        // Outstanding tokens are cancelled by the reset epoch.
                        i_acc = i_rsp;
                        d_acc = d_rsp;
                    end else if (t_data[gi] == 1) begin
                        resetn = 1; init_done = 1;
                        @(negedge clk);
                    end else begin
                        resetn = 1; init_done = 0;
                        @(negedge clk);
                    end
                    $fdisplay(tfd, "R %0d mode=%0d edge=%0d", gi, t_data[gi], n);
                    gi = gj;
                end
                KIND_E: begin
                    epoch = t_data[gi];
                    $fdisplay(tfd, "E %0d epoch=%0d edge=%0d", gi, epoch, n);
                    gi = gj;
                end
                KIND_WAIT: begin
                    release_wait(gi);
                    $fdisplay(tfd, "W %0d %s wmode=%0d warg=%0d edge=%0d",
                              gi, t_scen[gi], t_wmode[gi], t_warg[gi], n);
                    gi = gj;
                end
                KIND_X: begin
                    ia = t_addr[gi];
                    $fdisplay(tfd, "X %0d live_i=%08x edge=%0d", gi, t_addr[gi], n);
                    gi = gj;
                end
                default: begin
                    release_wait(gi);
                    run_group(gi, gj);
                    gi = gj;
                end
            endcase
        end

        repeat (4) @(negedge clk);
        ddr.dump(mem_path);
        $fdisplay(tfd, "END edge=%0d epoch=%0d", n, epoch);
        $fclose(tfd);
        $fclose(fd);
        $display("RESULT: PASS inst_hit_overlap overlap=%0d tokens=%0d edges=%0d",
                 OVERLAP, t_count, n);
        $finish;
    end

    initial begin
        #4000000;
        $fatal(1, "RESULT: FAIL wall watchdog");
    end
endmodule
