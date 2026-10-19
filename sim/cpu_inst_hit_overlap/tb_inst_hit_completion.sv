`timescale 1ns/1ps
// Task033 completion job: one bridge top-level, one vsim run, three scenarios.
//
//   epoch 1  independent I hit accepted while a D cold miss waits for R, then a
//            reset on the falling edge that would have consumed that hit
//   epoch 2  parked I miss promoted to its own AR (saved address, poisoned live
//            address), reset while the I read is still in flight
//   epoch 3  uncached Camera/PP D reads running in parallel with two real I
//            hits, one of them accepted on the delayed D R edge
//
// Stimulus only changes on the falling edge; a request holds valid/address
// until it is accepted. The edge log records the values sampled just before
// every rising edge (PRE), the values after NBA/DRM settle (POST) and the epoch.
module tb_inst_hit_completion;
    GTP_GRS GRS_INST (.GRS_N(1'b1));

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
        .INST_HIT_UNDER_DATA_MISS_ENABLE(1)
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

    completion_ddr_model ddr (
        .clk(clk), .resetn(resetn), .init_done(init_done),
        .awaddr(awa), .awvalid(awv), .awready(awr),
        .wdata(wd), .wstrb(ws), .wready(wrdy),
        .araddr(ara), .aruser_id(ari), .arvalid(arv), .arready(arr),
        .rdata(rd), .rvalid(rv), .rid(rid), .rlast(rlast)
    );

    // ---------------------------------------------------------- frozen numbers
    reg [31:0] c_s1_fill, c_s1_hit, c_s1_d;
    reg [31:0] c_s2_pre, c_s2_miss, c_s2_d;
    reg [31:0] c_cam_a, c_cam_i1, c_cam_i2, c_cam_new;
    reg [31:0] c_pp_a,  c_pp_i1,  c_pp_i2,  c_pp_new;

    integer fd, tfd;
    string edge_path, tok_path, plan_path, mem_path;
    integer n = 0;
    integer epoch = 0;

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
        #1;
        log_line("POST");
        if (n > 100000) $fatal(1, "RESULT: FAIL cycle watchdog");
    end

    // --------------------------------------------------------------- utilities
    task automatic wait_ar(input [3:0] who);
        begin
            @(posedge clk);
            while (!(arv && arr && (ari == who))) @(posedge clk);
        end
    endtask

    task automatic wait_i_rsp();
        begin
            @(posedge clk);
            while (!ip) @(posedge clk);
        end
    endtask

    task automatic wait_d_rsp();
        begin
            @(posedge clk);
            while (!dp) @(posedge clk);
        end
    endtask

    task automatic wait_dual_rsp();
        begin
            @(posedge clk);
            while (!(ip && dp)) @(posedge clk);
        end
    endtask

    // Hold the request until accepted, then release on the falling edge that
    // follows the acceptance edge. Address/valid never change while waiting.
    task automatic i_req(input [31:0] a);
        begin
            @(negedge clk); ia = a; iv = 1'b1;
            while (!ir) @(negedge clk);
            @(posedge clk);
            @(negedge clk); iv = 1'b0;
        end
    endtask

    task automatic d_req(input [31:0] a);
        begin
            @(negedge clk); da = a; dv = 1'b1; dw = 1'b0; dsize = 2'd2;
            dstrb = 4'b0; dwdata = 32'b0;
            while (!dr) @(negedge clk);
            @(posedge clk);
            @(negedge clk); dv = 1'b0;
        end
    endtask

    // Call with the falling edge already reached: the reset takes effect on the
    // next rising edge and stays for three more.
    task automatic reset_now();
        begin
            resetn = 1'b0; init_done = 1'b0; iv = 1'b0; dv = 1'b0; dw = 1'b0;
            repeat (3) @(negedge clk);
        end
    endtask

    task automatic leave_reset(input integer ep);
        begin
            @(negedge clk);
            resetn = 1'b1; init_done = 1'b1;
            epoch = ep;
            @(negedge clk);
        end
    endtask

    // ---------------------------------------------------------------- sequence
    initial begin : run
        if (!$value$plusargs("PLAN=%s", plan_path)) $fatal(1, "RESULT: FAIL missing PLAN");
        if (!$value$plusargs("EDGE_LOG=%s", edge_path)) $fatal(1, "RESULT: FAIL missing EDGE_LOG");
        if (!$value$plusargs("TOK_LOG=%s", tok_path)) $fatal(1, "RESULT: FAIL missing TOK_LOG");
        if (!$value$plusargs("MEM_DUMP=%s", mem_path)) $fatal(1, "RESULT: FAIL missing MEM_DUMP");
        fd  = $fopen(edge_path, "w");
        tfd = $fopen(tok_path, "w");
        if (!fd || !tfd) $fatal(1, "RESULT: FAIL cannot open logs");

        begin : parse
            integer pf, rc;
            string tag, nm;
            reg [31:0] val;
            pf = $fopen(plan_path, "r");
            if (!pf) $fatal(1, "RESULT: FAIL cannot open plan");
            while (!$feof(pf)) begin
                rc = $fscanf(pf, "%s %s %h\n", tag, nm, val);
                if (rc == 3 && tag == "C") begin
                    if (nm == "s1_i_fill")      c_s1_fill = val;
                    else if (nm == "s1_i_hit")  c_s1_hit  = val;
                    else if (nm == "s1_d")      c_s1_d    = val;
                    else if (nm == "s2_i_pre")  c_s2_pre  = val;
                    else if (nm == "s2_i_miss") c_s2_miss = val;
                    else if (nm == "s2_d")      c_s2_d    = val;
                    else if (nm == "cam_a")     c_cam_a   = val;
                    else if (nm == "cam_i1")    c_cam_i1  = val;
                    else if (nm == "cam_i2")    c_cam_i2  = val;
                    else if (nm == "cam_new")   c_cam_new = val;
                    else if (nm == "pp_a")      c_pp_a    = val;
                    else if (nm == "pp_i1")     c_pp_i1   = val;
                    else if (nm == "pp_i2")     c_pp_i2   = val;
                    else if (nm == "pp_new")    c_pp_new  = val;
                    else $fatal(1, "RESULT: FAIL unknown plan constant %s", nm);
                end
            end
            $fclose(pf);
            $display("PLAN constants loaded");
        end

        epoch = 1;
        resetn = 0; init_done = 0;
        repeat (4) @(negedge clk);
        resetn = 1; init_done = 1;
        @(negedge clk);

        // =========================================== epoch 1: independent I hit
        $fdisplay(tfd, "S s1_fill edge=%0d", n);
        i_req(c_s1_fill);                 // real DDR fill of the I line
        wait_i_rsp();

        @(negedge clk);
        ddr.ar_block = 2; ddr.r_lat = 10;
        $fdisplay(tfd, "S s1_dmiss edge=%0d", n);
        d_req(c_s1_d);                    // D cold miss, AR backpressure, long R
        wait_ar(4'd1);
        $fdisplay(tfd, "S s1_ihit edge=%0d", n);
        i_req(c_s1_hit);                  // accepted only by the independent slot
        reset_now();                      // falling edge right after that accept

        // =========================================== epoch 2: promoted miss + reset
        leave_reset(2);
        $fdisplay(tfd, "S s1_cold edge=%0d", n);
        i_req(c_s1_hit);                  // the reset must have dropped the line
        wait_i_rsp();
        $fdisplay(tfd, "S s1_cold_done edge=%0d", n);

        $fdisplay(tfd, "S s2_pre edge=%0d", n);
        i_req(c_s2_pre);                  // second real DDR fill: poison target
        wait_i_rsp();

        @(negedge clk);
        ddr.ar_block = 0; ddr.r_lat = 10;
        $fdisplay(tfd, "S s2_dmiss edge=%0d", n);
        d_req(c_s2_d);
        wait_ar(4'd1);
        $fdisplay(tfd, "S s2_imiss edge=%0d", n);
        i_req(c_s2_miss);                 // parked miss while the D miss is open
        ia = c_s2_pre;                    // poisoned live address (a cached line)
        $fdisplay(tfd, "S s2_poison live=%08x edge=%0d", ia, n);
        wait_d_rsp();                     // D R arrives and is really consumed
        $fdisplay(tfd, "S s2_drsp edge=%0d", n);
        wait_ar(4'd0);                    // the saved miss gets its own AR
        $fdisplay(tfd, "S s2_iar edge=%0d", n);
        repeat (3) @(posedge clk);        // >= two full edges with no I R
        @(negedge clk);
        reset_now();                      // cancel the in-flight I read only

        // =========================================== epoch 3: uncached D + I hits
        leave_reset(3);
        $fdisplay(tfd, "S s2_cold edge=%0d", n);
        i_req(c_s2_miss);                 // cold read of the cancelled line
        wait_i_rsp();

        @(negedge clk);
        ddr.ar_block = 2; ddr.r_lat = 8;
        // -------- Camera window
        $fdisplay(tfd, "S cam_pre edge=%0d", n);
        i_req(c_cam_a);
        wait_i_rsp();
        $fdisplay(tfd, "S cam_dread edge=%0d", n);
        d_req(c_cam_a);
        wait_ar(4'd1);                    // uncached D AR, held by backpressure
        $fdisplay(tfd, "S cam_hit1 edge=%0d", n);
        i_req(c_cam_i1);                  // cached hit while the D read waits
        wait_i_rsp();
        // second hit must be accepted on the delayed D R edge
        @(posedge clk);
        while (!(ddr.reading && (ddr.r_wait == 0))) @(posedge clk);
        @(negedge clk); ia = c_cam_i2; iv = 1'b1;
        while (!ir) @(negedge clk);
        @(posedge clk);
        @(negedge clk); iv = 1'b0;
        $fdisplay(tfd, "S cam_hit2 edge=%0d", n);
        wait_dual_rsp();
        $fdisplay(tfd, "S cam_dual edge=%0d", n);
        @(negedge clk);
        ddr.poke(c_cam_a, c_cam_new, 4'hf);
        $fdisplay(tfd, "M cam addr=%08x data=%08x strb=f edge=%0d", c_cam_a, c_cam_new, n);
        $fdisplay(tfd, "S cam_reread edge=%0d", n);
        d_req(c_cam_a);                   // uncached line was never filled
        wait_ar(4'd1);
        wait_d_rsp();
        $fdisplay(tfd, "S cam_done edge=%0d", n);

        // -------- Preprocess window
        $fdisplay(tfd, "S pp_pre edge=%0d", n);
        i_req(c_pp_a);
        wait_i_rsp();
        $fdisplay(tfd, "S pp_dread edge=%0d", n);
        d_req(c_pp_a);
        wait_ar(4'd1);
        $fdisplay(tfd, "S pp_hit1 edge=%0d", n);
        i_req(c_pp_i1);
        wait_i_rsp();
        @(posedge clk);
        while (!(ddr.reading && (ddr.r_wait == 0))) @(posedge clk);
        @(negedge clk); ia = c_pp_i2; iv = 1'b1;
        while (!ir) @(negedge clk);
        @(posedge clk);
        @(negedge clk); iv = 1'b0;
        $fdisplay(tfd, "S pp_hit2 edge=%0d", n);
        wait_dual_rsp();
        $fdisplay(tfd, "S pp_dual edge=%0d", n);
        @(negedge clk);
        ddr.poke(c_pp_a, c_pp_new, 4'hf);
        $fdisplay(tfd, "M pp addr=%08x data=%08x strb=f edge=%0d", c_pp_a, c_pp_new, n);
        $fdisplay(tfd, "S pp_reread edge=%0d", n);
        d_req(c_pp_a);
        wait_ar(4'd1);
        wait_d_rsp();
        $fdisplay(tfd, "S pp_done edge=%0d", n);

        repeat (4) @(negedge clk);
        ddr.dump(mem_path);
        $fdisplay(tfd, "END edge=%0d epoch=%0d", n, epoch);
        $fclose(tfd);
        $fclose(fd);
        $display("RESULT: PASS inst_hit_completion edges=%0d", n);
        $finish;
    end

    initial begin
        #300000;
        $fatal(1, "RESULT: FAIL wall watchdog");
    end
endmodule
