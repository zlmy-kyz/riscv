`timescale 1ns/1ps
// ===========================================================================
// tb_fix02.v  —  Task040 correction 02: one physical edge identity
//
// The previous TB let one always block increment `cycle` while another read
// it, so phase-0 and phase-1 could see different numbers. Here every event is
// stamped with $time (the clock has a 10 ns period, posedges at 5,15,25...),
// and the memory model schedules its response by absolute time as well. No
// process reads a mutable cycle counter to decide an accept/consume instant.
//
// Per edge the pre-edge OLD snapshot (pending / pending_pc / buffer / response
// request_id) is frozen, then after NBA the actual IF/ID load is checked.
// t3 < t4 is asserted strictly; t3 is the edge whose NBA made IF/ID hold the
// target for the first time.
// ===========================================================================
module tb_fix02;

    localparam time CLK_HALF   = 5;
    localparam time CLK_PERIOD = 10;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #CLK_HALF clk = ~clk;

    reg [31:0] imem [0:511];
    reg [31:0] dmem [0:511];

    wire        inst_req_valid;
    wire [31:0] inst_req_addr;
    wire        inst_req_ready;
    reg         inst_rsp_valid = 1'b0;
    reg  [31:0] inst_rsp_rdata = 32'b0;
    reg         inst_rsp_error = 1'b0;

    wire        data_req_valid;
    wire        data_req_write;
    wire [ 1:0] data_req_size;
    wire [31:0] data_req_addr;
    wire [31:0] data_req_wdata;
    wire [ 3:0] data_req_wstrb;
    reg         data_req_ready = 1'b1;
    reg         data_rsp_valid = 1'b0;
    reg  [31:0] data_rsp_rdata = 32'b0;
    reg         data_rsp_error = 1'b0;

    wire [31:0] debug_wb_pc;
    wire [ 3:0] debug_wb_rf_we;
    wire [ 4:0] debug_wb_rf_wnum;
    wire [31:0] debug_wb_rf_wdata;
    wire [31:0] debug_inst;
    wire [ 7:0] perf_events;
    wire [31:0] perf_branch_target;
    wire [31:0] perf_fetch_pc;

    mycpu_sync #(.RESET_PC(32'h0000_0000)) u_dut (
        .clk(clk), .resetn(resetn),
        .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0),
        .memory_order_busy(1'b0),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr),
        .inst_req_ready(inst_req_ready),
        .inst_rsp_valid(inst_rsp_valid), .inst_rsp_rdata(inst_rsp_rdata),
        .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(data_req_write),
        .data_req_size(data_req_size), .data_req_addr(data_req_addr),
        .data_req_wdata(data_req_wdata), .data_req_wstrb(data_req_wstrb),
        .data_req_ready(data_req_ready),
        .data_rsp_valid(data_rsp_valid), .data_rsp_rdata(data_rsp_rdata),
        .data_rsp_error(data_rsp_error),
        .debug_wb_pc(debug_wb_pc), .debug_wb_rf_we(debug_wb_rf_we),
        .debug_wb_rf_wnum(debug_wb_rf_wnum), .debug_wb_rf_wdata(debug_wb_rf_wdata),
        .debug_inst(debug_inst),
        .perf_events(perf_events),
        .perf_branch_target(perf_branch_target),
        .perf_fetch_pc(perf_fetch_pc)
    );

    // ================= instruction model: absolute-time scheduling ==========
    integer    slow_addr  = -1;
    integer    slow_delay = 8;
    reg        stop_accept = 1'b0;
    reg        i_busy = 1'b0;
    time       i_set_time = 0;
    reg [31:0] i_data_q = 32'b0;

    integer    i_acc = 0, i_rspgen = 0, i_consume = 0, i_deliver = 0, i_drop = 0;
    reg [31:0] i_acc_addr [0:511];
    time       i_acc_t    [0:511];
    time       i_rsp_t    [0:511];
    time       i_cons_t   [0:511];
    integer    i_rsp_id_q = 0;
    integer    i_cur_id = 0;
    integer    slow_id = -1;

    assign inst_req_ready = ((!i_busy) && (!stop_accept)) ? 1'b1 : 1'b0;
    wire i_fire = inst_req_valid && inst_req_ready;
    wire i_consume_ev = inst_rsp_valid && u_dut.inst_pending;
    wire i_deliver_ev = i_consume_ev && !u_dut.inst_pending_drop && !u_dut.redirect_valid;

    // single owner of the model state
    always @(posedge clk) begin
        inst_rsp_valid <= 1'b0;
        if (i_fire) begin
            i_acc = i_acc + 1;
            i_acc_addr[i_acc] = inst_req_addr;
            i_acc_t[i_acc]    = $time;
            i_cur_id          = i_acc;
            if (inst_req_addr == slow_addr) begin
                i_data_q   <= imem[inst_req_addr[10:2]];
                i_busy      = 1'b1;
                i_set_time  = $time + (slow_delay - 1) * CLK_PERIOD;
                slow_id     = i_acc;
            end else begin
                // fast path: combinational read registered on this edge, so the
                // response is valid during E+1 and the CPU consumes it at E+1
                inst_rsp_valid <= 1'b1;
                inst_rsp_rdata <= imem[inst_req_addr[10:2]];
                i_rspgen = i_rspgen + 1;
                i_rsp_t[i_acc] = $time + CLK_PERIOD;
                i_rsp_id_q = i_cur_id;
            end
        end
        if (i_busy && ($time == i_set_time)) begin
            inst_rsp_valid <= 1'b1;
            inst_rsp_rdata <= i_data_q;
            i_busy   = 1'b0;
            i_rspgen = i_rspgen + 1;
            i_rsp_t[i_acc] = $time + CLK_PERIOD;     // consumed on the next edge
            i_rsp_id_q = i_acc;
        end
        if (i_consume_ev) begin
            i_consume = i_consume + 1;
            i_cons_t[i_rsp_id_q] = $time;
            if (i_deliver_ev) i_deliver = i_deliver + 1;
            else              i_drop    = i_drop + 1;
        end
    end

    // ================= data model ==========================================
    integer ddelay = 1;
    reg     d_busy = 1'b0;
    time    d_set_time = 0;
    reg [31:0] d_lat_q = 32'b0;
    reg        d_wr_q2 = 1'b0;
    reg [31:0] d_addr_q2 = 32'b0;
    reg [31:0] d_wd_q2 = 32'b0;
    reg [ 3:0] d_ws_q2 = 4'b0;

    integer d_acc = 0, d_rspgen = 0, d_consume = 0, d_store = 0;
    integer wi;

    always @(posedge clk) begin
        data_rsp_valid <= 1'b0;
        if (data_req_valid && data_req_ready) begin
            d_acc = d_acc + 1;
            d_wr_q2   <= data_req_write;
            d_wd_q2   <= data_req_wdata;
            d_ws_q2   <= data_req_wstrb;
            d_addr_q2 <= data_req_addr;
            if (ddelay <= 1) begin
                data_rsp_valid <= 1'b1;
                data_rsp_rdata <= dmem[data_req_addr[10:2]];
                d_rspgen = d_rspgen + 1;
                if (data_req_write) d_store = d_store + 1;
                if (data_req_write)
                    for (wi = 0; wi < 4; wi = wi + 1)
                        if (data_req_wstrb[wi])
                            dmem[data_req_addr[10:2]][8*wi +: 8] <= data_req_wdata[8*wi +: 8];
            end else begin
                d_lat_q    <= dmem[data_req_addr[10:2]];
                d_busy      = 1'b1;
                d_set_time  = $time + (ddelay - 1) * CLK_PERIOD;
                if (data_req_write) d_store = d_store + 1;
            end
        end
        if (d_busy && ($time == d_set_time)) begin
            data_rsp_valid <= 1'b1;
            data_rsp_rdata <= d_lat_q;
            d_busy <= 1'b0;
            d_rspgen = d_rspgen + 1;
            if (d_wr_q2)
                for (wi = 0; wi < 4; wi = wi + 1)
                    if (d_ws_q2[wi])
                        dmem[d_addr_q2[10:2]][8*wi +: 8] <= d_wd_q2[8*wi +: 8];
        end
        if (data_rsp_valid) d_consume = d_consume + 1;
    end

    // ================= real classification =================================
    wire [3:0]  cls;
    wire [31:0] perf_rdata;
    wire        perf_error;
    cpu_perf_counters u_perf (
        .clk(clk), .resetn(resetn), .events(perf_events),
        .retire_pc(debug_wb_pc), .branch_target(perf_branch_target),
        .fetch_pc(perf_fetch_pc), .timer_value(32'b0),
        .ar_fire(1'b0), .aw_fire(1'b0), .timer_read(1'b0),
        .access(1'b0), .write(1'b0), .size(2'b00),
        .addr(12'b0), .wdata(32'b0), .wstrb(4'b0),
        .rdata(perf_rdata), .error(perf_error)
    );
    assign cls = u_perf.classification;

    // ================= five events, stamped by $time =======================
    integer mode = 1;
    integer target_store_pc = -1;
    integer br_seen = 0;
    time    t0_t = 0, t1_t = 0, t2_t = 0, t3_t = 0, t4_t = 0;
    integer t0_pc = 0, t0_target = 0;
    integer seen1 = 0, seen2 = 0, seen3 = 0, seen4 = 0;
    integer pending_at_t1 = -1;
    integer t2_reqid = -1;
    // pre-edge OLD snapshot captured on the edge that loads IF/ID
    integer t3_oldpend_pc = 0, t3_oldbuf_pc = 0, t3_oldpend = -1, t3_oldbuf = -1;
    integer t3_rsp_id = -1;
    integer errors = 0;

    integer roi_on = 0, roi_off = 0, roi_edges = 0;
    integer c_other = 0, c_mem = 0, c_if = 0, c_br = 0, c_lu = 0, c_ctrl = 0, c_hold = 0;
    integer other_ret = 0, other_noret = 0, other_fire = 0;
    integer retire = 0;
    reg [31:0] ret_pc_q [0:255], ret_inst_q [0:255];
    integer ret_rd_q [0:255], ret_we_q [0:255];
    reg [31:0] ret_val_q [0:255], ret_npc_q [0:255];
    integer ret_n = 0;
    integer trace_all = 0;

    always @(posedge clk) begin
        if (resetn) begin
            // ---- phase 0: pre-edge snapshot, all stamps use $time ----
            if (!br_seen && u_dut.id_fire && u_dut.id_taken &&
                u_dut.inst_b && !u_dut.id_exc_valid) begin
                br_seen = 1;
                t0_t = $time; t0_pc = u_dut.if_id_pc; t0_target = u_dut.bj_pc;
                roi_on = 1;
            end
            if (!seen1 && br_seen && u_dut.ex_br_redirect &&
                (mode != 4 || (u_dut.id_ex_pc == t0_pc))) begin
                seen1 = 1; t1_t = $time;
                pending_at_t1 = (u_dut.inst_pending && !u_dut.inst_rsp_valid);
            end
            if (seen1 && !seen2 && i_fire && (inst_req_addr == t0_target)) begin
                seen2 = 1; t2_t = $time; t2_reqid = i_acc + 1;
            end
            if (seen3 && !seen4 && u_dut.id_fire && (u_dut.if_id_pc == t0_target)) begin
                seen4 = 1; t4_t = $time;
            end
            // non-taken control: open the ROI at the conditional branch itself
            if (mode == 4 && !br_seen && u_dut.id_fire && u_dut.inst_b &&
                !u_dut.id_exc_valid) begin
                br_seen = 1; t0_t = $time; t0_pc = u_dut.if_id_pc;
                roi_on = 1;
            end

            if (roi_on && !roi_off) begin
                roi_edges = roi_edges + 1;
                case (cls)
                    8: begin c_other = c_other + 1;
                             if (perf_events[0]) other_ret = other_ret + 1;
                             else                other_noret = other_noret + 1;
                             if (u_dut.id_fire)  other_fire = other_fire + 1; end
                    3: c_mem = c_mem + 1;
                    2: c_if = c_if + 1;
                    4: c_br = c_br + 1;
                    7: c_lu = c_lu + 1;
                    5: c_ctrl = c_ctrl + 1;
                    6: c_hold = c_hold + 1;
                    default: ;
                endcase
            end

            if (perf_events[0]) begin
                retire = retire + 1;
                if (ret_n < 256) begin
                    ret_pc_q[ret_n]   = debug_wb_pc;
                    ret_inst_q[ret_n] = debug_inst;
                    ret_rd_q[ret_n]   = debug_wb_rf_wnum;
                    ret_we_q[ret_n]   = debug_wb_rf_we[0];
                    ret_val_q[ret_n]  = debug_wb_rf_wdata;
                    ret_npc_q[ret_n]  = u_dut.mem_wb_next_pc;
                    ret_n = ret_n + 1;
                end
                if (roi_on && !roi_off && (debug_wb_pc == target_store_pc)) roi_off = 1;
            end

            if (trace_all)
                $display("EV,t=%0d,ph=0,pc=%h,ireq=%b%b,%h,irsp=%b,%h,pend=%b,%h,%b,buf=%b,%h,ifid=%b,%h,%h,idfire=%b,taken=%b,bj=%h,exc=%b,lu=%b,idex=%b,%h,%b,%h,adv=%b,emrdy=%b,emcmp=%b,stall=%b,older=%b,rdir=%b,tgt=%h,fs=%0d,sc=%b,si=%b,front=%b,ret=%b,%h,cls=%0d",
                    $time, u_dut.pc,
                    inst_req_valid, inst_req_ready, inst_req_addr,
                    inst_rsp_valid, inst_rsp_rdata,
                    u_dut.inst_pending, u_dut.inst_pending_pc, u_dut.inst_pending_drop,
                    u_dut.inst_buffer_valid, u_dut.inst_buffer_pc,
                    u_dut.if_id_valid, u_dut.if_id_pc, u_dut.if_id_inst,
                    u_dut.id_fire, u_dut.id_taken, u_dut.bj_pc,
                    u_dut.id_exc_valid, u_dut.load_use,
                    u_dut.id_ex_valid, u_dut.id_ex_pc,
                    u_dut.id_ex_br_taken, u_dut.id_ex_br_target,
                    u_dut.id_ex_advance, u_dut.ex_mem_ready, u_dut.ex_mem_complete,
                    u_dut.data_pipeline_stall, u_dut.older_fault_for_ex,
                    u_dut.branch_redirect, u_dut.redirect_pc,
                    u_dut.flow_state, u_dut.serial_candidate, u_dut.serial_issue,
                    u_dut.frontend_hold, perf_events[0], debug_wb_pc, cls);
        end
    end

    // phase 1: same physical edge, after NBA. Freeze the OLD owners first.
    always @(posedge clk) begin
        #1;
        if (resetn && seen2 && !seen3 &&
            u_dut.if_id_valid && (u_dut.if_id_pc == t0_target)) begin
            seen3 = 1;
            t3_t = $time - 1;                    // this edge started at $time-1
            t3_oldpend = u_dut.inst_pending;
            t3_oldpend_pc = u_dut.inst_pending_pc;
            t3_oldbuf = u_dut.inst_buffer_valid;
            t3_oldbuf_pc = u_dut.inst_buffer_pc;
            t3_rsp_id = i_rsp_id_q;
            $display("EV,t=%0d,ph=1,LOAD_IFID,pc=%h,oldpend=%b/%h,oldbuf=%b/%h,rspid=%0d,inst=%h",
                     t3_t, u_dut.if_id_pc, t3_oldpend, t3_oldpend_pc,
                     t3_oldbuf, t3_oldbuf_pc, t3_rsp_id, u_dut.if_id_inst);
        end
    end

    integer i;
    reg void_ignore;

    initial begin
        if (!$value$plusargs("MODE=%d", mode)) mode = 1;
        if (!$value$plusargs("DDELAY=%d", ddelay)) ddelay = 1;
        if (!$value$plusargs("SLOWDELAY=%d", slow_delay)) slow_delay = 8;
        void_ignore = $value$plusargs("SLOWADDR=%d", slow_addr);
        void_ignore = $value$plusargs("STPC=%d", target_store_pc);
        void_ignore = $value$plusargs("TRACE=%d", trace_all);
        for (i = 0; i < 512; i = i + 1) begin
            imem[i] = 32'h0000_0013;
            dmem[i] = 32'h0;
            i_acc_t[i] = 0; i_rsp_t[i] = 0; i_cons_t[i] = 0;
        end
        $readmemh("imem.hex", imem);
        $readmemh("dmem_init.hex", dmem);

        repeat (3) @(negedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (400) @(posedge clk);
        stop_accept = 1'b1;
        repeat (40) @(posedge clk);

        $display("---- mode=%0d ddelay=%0d slowaddr=%0d slowdelay=%0d stpc=%0d ----",
                 mode, ddelay, slow_addr, slow_delay, target_store_pc);
        $display("EVENT t0=%0d t1=%0d t2=%0d t3=%0d t4=%0d", t0_t, t1_t, t2_t, t3_t, t4_t);
        $display("DELTA_EDGES t1-t0=%0d t2-t1=%0d t3-t2=%0d t4-t3=%0d",
                 (t1_t-t0_t)/CLK_PERIOD, (t2_t-t1_t)/CLK_PERIOD,
                 (t3_t-t2_t)/CLK_PERIOD, (t4_t-t3_t)/CLK_PERIOD);
        $display("WRONGPATH pending_at_t1=%0d oldpend_at_t3=%b/%h oldbuf_at_t3=%b/%h rspid=%0d",
                 pending_at_t1, t3_oldpend, t3_oldpend_pc, t3_oldbuf, t3_oldbuf_pc, t3_rsp_id);
        $display("IAUDIT acc=%0d rspgen=%0d consume=%0d deliver=%0d drop=%0d inflight=%0d",
                 i_acc, i_rspgen, i_consume, i_deliver, i_drop, i_acc - i_consume);
        if (slow_id > 0)
            $display("SLOWWIT id=%0d addr=%h acc=%0d rsp=%0d consume=%0d edges_acc_to_consume=%0d",
                     slow_id, i_acc_addr[slow_id], i_acc_t[slow_id], i_rsp_t[slow_id],
                     i_cons_t[slow_id], (i_cons_t[slow_id]-i_acc_t[slow_id])/CLK_PERIOD);
        $display("DAUDIT acc=%0d rspgen=%0d consume=%0d stores=%0d dmem0=%h",
                 d_acc, d_rspgen, d_consume, d_store, dmem[0]);
        $display("ROI edges=%0d other=%0d mem=%0d if=%0d branch=%0d load_use=%0d ctrl=%0d hold=%0d",
                 roi_edges, c_other, c_mem, c_if, c_br, c_lu, c_ctrl, c_hold);
        $display("OTHER ret=%0d noret=%0d idfire=%0d", other_ret, other_noret, other_fire);
        $display("X31CHECK x31=%h mscratch=%h (expect 0/0)",
                 u_dut.u_regfile.rf[31], u_dut.u_csr_file.mscratch);

        for (i = 0; i < ret_n; i = i + 1)
            $display("RET,%0d,%h,%h,%0d,%0d,%h,%h", i, ret_pc_q[i], ret_inst_q[i],
                     ret_rd_q[i], ret_we_q[i], ret_val_q[i], ret_npc_q[i]);

        if (i_acc !== i_rspgen) begin
            errors = errors + 1; $display("RESULT: FAIL iaudit_rspgen");
        end else if ((i_acc - i_consume) !== 0) begin
            errors = errors + 1; $display("RESULT: FAIL iaudit_inflight");
        end else if (d_acc !== d_rspgen) begin
            errors = errors + 1; $display("RESULT: FAIL daudit_rspgen");
        end else if (dmem[0] !== 32'h0000_0001) begin
            errors = errors + 1; $display("RESULT: FAIL target_flag dmem0=%h", dmem[0]);
        end else if (u_dut.u_regfile.rf[31] !== 32'h0) begin
            errors = errors + 1; $display("RESULT: FAIL wrong_path_x31");
        end else if (mode != 4 && u_dut.u_csr_file.mscratch !== 32'h0) begin
            errors = errors + 1; $display("RESULT: FAIL wrong_path_mscratch=%h", u_dut.u_csr_file.mscratch);
        end else if (mode == 4) begin
            if (seen1) begin errors = errors + 1; $display("RESULT: FAIL nottaken_redirected"); end
            else $display("RESULT: PASS fix02 nottaken_no_redirect roi=%0d", roi_edges);
        end else if (!seen1 || !seen2 || !seen3 || !seen4) begin
            errors = errors + 1; $display("RESULT: INCOMPLETE missing_event");
        end else if (t3_t >= t4_t) begin
            errors = errors + 1; $display("RESULT: FAIL t3_not_before_t4");
        end else begin
            $display("RESULT: PASS fix02");
        end
        if (errors != 0) $display("RESULT: FAIL fix02 errors=%0d", errors);
        $finish;
    end

    initial begin
        repeat (50000) @(posedge clk);
        $display("RESULT: FAIL timeout");
        $finish;
    end

endmodule
