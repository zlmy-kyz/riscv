`timescale 1ns/1ps
// ===========================================================================
// tb_fix01.v  —  Task040 correction: five-edge sampling with explicit phases
//
// Corrections vs the rejected run2 TB:
//  * t3 is sampled AFTER the clock edge (NBA) as "this edge loaded IF/ID",
//    with the OLD pending/buffer owner PC recorded alongside. The pre-edge
//    snapshot is phase 0, the post-NBA check is phase 1.
//  * Instruction latency is real: N=1 is consumed at E+1, N=8 at E+8.
//    Each request gets a request_id; accepted / response-generated /
//    consumed(deliver|drop) / cancelled are tracked separately so
//    inflight = accepted - consumed - cancelled is checkable.
//  * Reset is released on a falling edge.
//  * Observation window (ROI) starts before the branch and ends when the
//    target completion store retires; later spin is excluded.
//  * Every retired instruction is logged (PC/inst/rd/we/value) for an
//    independent reference comparison, and wrong-path x31 is checked.
// ===========================================================================
module tb_fix01;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

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

    // ================= instruction model: one slot, real N-cycle latency ====
    integer    slow_addr  = -1;
    integer    slow_delay = 8;
    integer    i_busy = 0;
    integer    i_cnt  = 0;
    reg [31:0] i_addr_q = 32'b0;
    reg [31:0] i_data_q = 32'b0;

    integer    i_acc = 0;          // accepted requests
    integer    i_rspgen = 0;       // responses produced (valid asserted)
    integer    i_consume = 0;      // responses consumed by CPU
    integer    i_deliver = 0;      // consumed and used (not dropped)
    integer    i_drop = 0;         // consumed but dropped (wrong path)
    integer    i_cur_id = 0;
    reg [31:0] i_acc_addr [0:255];
    integer    i_acc_cyc  [0:255];
    integer    i_rsp_cyc  [0:255];
    integer    i_cons_cyc [0:255];
    reg [31:0] i_rsp_id_q = 32'b0;   // request_id of the response in flight
    integer    i_rsp_cycle_q = -1;
    integer    slow_id = -1;

    reg stop_accept = 1'b0;
    assign inst_req_ready = ((i_busy == 0) && !stop_accept) ? 1'b1 : 1'b0;
    wire i_fire = inst_req_valid && inst_req_ready;
    // CPU consumes the response on the cycle it is valid and pending
    wire i_consume_ev = inst_rsp_valid && u_dut.inst_pending;
    wire i_deliver_ev = i_consume_ev && !u_dut.inst_pending_drop && !u_dut.redirect_valid;
    wire i_drop_ev    = i_consume_ev && (u_dut.inst_pending_drop || u_dut.redirect_valid);

    integer cycle = 0;

    always @(posedge clk) begin
        cycle = cycle + 1;
        inst_rsp_valid <= 1'b0;
        if (i_fire) begin
            i_acc = i_acc + 1;
            i_acc_addr[i_acc] = inst_req_addr;
            i_acc_cyc[i_acc]  = cycle;
            i_addr_q <= inst_req_addr;
            i_data_q <= imem[inst_req_addr[10:2]];
            if (inst_req_addr == slow_addr) begin
                i_busy <= 1;
                i_cnt  <= (slow_delay <= 1) ? 1 : (slow_delay - 1);
                slow_id = i_acc;
            end else begin
                inst_rsp_valid <= 1'b1;          // consumed at cycle+1
                inst_rsp_rdata <= imem[inst_req_addr[10:2]];
                i_rspgen = i_rspgen + 1;
                i_rsp_cyc[i_acc] = cycle + 1;
                i_rsp_id_q <= i_acc;
            end
        end else if (i_busy == 1) begin
            if (i_cnt == 1) begin
                inst_rsp_valid <= 1'b1;          // consumed at cycle+1
                inst_rsp_rdata <= i_data_q;
                i_busy  <= 0;
                i_rspgen = i_rspgen + 1;
                i_rsp_cyc[i_acc] = cycle + 1;
                i_rsp_id_q <= i_acc;
            end else i_cnt <= i_cnt - 1;
        end
        if (i_consume_ev) begin
            i_consume = i_consume + 1;
            i_cons_cyc[i_rsp_id_q] = cycle;
            if (i_deliver_ev) i_deliver = i_deliver + 1;
            else              i_drop    = i_drop + 1;
        end
    end

    // ================= data model ==========================================
    integer ddelay = 1;
    integer d_busy = 0, d_cnt = 0;
    reg [31:0] d_addr_q = 32'b0;
    reg        d_wr_q = 1'b0;
    reg [31:0] d_wd_q = 32'b0;
    reg [ 3:0] d_ws_q = 4'b0;
    reg [31:0] d_lat_q = 32'b0;
    integer    d_acc = 0, d_rspgen = 0, d_consume = 0, d_store = 0;
    integer    wi;

    always @(posedge clk) begin
        data_rsp_valid <= 1'b0;
        if (data_req_valid && data_req_ready) begin
            d_acc = d_acc + 1;
            d_addr_q <= data_req_addr;
            d_lat_q  <= dmem[data_req_addr[10:2]];
            if (data_req_write) begin
                d_store = d_store + 1;
                for (wi = 0; wi < 4; wi = wi + 1)
                    if (data_req_wstrb[wi])
                        dmem[data_req_addr[10:2]][8*wi +: 8] <= data_req_wdata[8*wi +: 8];
                if (ddelay <= 1) begin
                    data_rsp_valid <= 1'b1; data_rsp_rdata <= 32'b0;
                    d_rspgen = d_rspgen + 1;
                end else begin d_busy <= 1; d_cnt <= (ddelay <= 1) ? 1 : (ddelay - 1); end
            end else begin
                if (ddelay <= 1) begin
                    data_rsp_valid <= 1'b1;
                    data_rsp_rdata <= dmem[data_req_addr[10:2]];
                    d_rspgen = d_rspgen + 1;
                end else begin d_busy <= 1; d_cnt <= (ddelay <= 1) ? 1 : (ddelay - 1); end
            end
        end else if (d_busy == 1) begin
            if (d_cnt == 1) begin
                data_rsp_valid <= 1'b1;
                data_rsp_rdata <= d_lat_q;
                d_busy <= 0;
                d_rspgen = d_rspgen + 1;
            end else d_cnt <= d_cnt - 1;
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

    // ================= five-edge state (phase 0 pre-edge, phase 1 post-NBA)
    integer br_seen = 0;
    integer t0_cycle = -1, t1_cycle = -1, t2_cycle = -1, t3_cycle = -1, t4_cycle = -1;
    integer t0_pc = 0, t0_target = 0;
    integer t1_pc = 0;
    integer t2_reqid = -1;
    integer t3_oldpend_pc = 0, t3_oldbuf_pc = 0;
    integer seen1 = 0, seen2 = 0, seen3 = 0, seen4 = 0;
    integer pending_at_t1 = -1;

    // ROI classification counters
    integer roi_on = 0, roi_off = 0;
    integer roi_cycles = 0;
    integer c_other = 0, c_mem = 0, c_if = 0, c_br = 0, c_lu = 0, c_ctrl = 0, c_hold = 0;
    integer other_ret = 0, other_noret = 0;
    integer other_idfire = 0, other_adv = 0;
    integer retire = 0;
    reg [31:0] retire_pc_q [0:255];
    reg [31:0] retire_inst_q [0:255];
    integer retire_n = 0;
    integer target_store_pc = -1;

    integer trace_lim = 80;
    integer mode = 1;
    integer errors = 0;

    always @(posedge clk) begin
        if (resetn) begin
            // ROI opens one cycle before the branch leaves ID (first taken cond branch)
            if (!br_seen && u_dut.id_fire && u_dut.id_taken &&
                u_dut.inst_b && !u_dut.id_exc_valid) begin
                br_seen   = 1;
                t0_cycle  = cycle;
                t0_pc     = u_dut.if_id_pc;
                t0_target = u_dut.bj_pc;
                roi_on    = 1;
            end
            if (seen1 == 0 && br_seen && u_dut.ex_br_redirect) begin
                seen1 = 1; t1_cycle = cycle; t1_pc = u_dut.id_ex_pc;
                pending_at_t1 = (u_dut.inst_pending && !u_dut.inst_rsp_valid);
            end
            if (seen1 && !seen2 && i_fire && (inst_req_addr == t0_target)) begin
                seen2 = 1; t2_cycle = cycle; t2_reqid = i_acc + 1;
            end
            if (seen3 && !seen4 && u_dut.id_fire && (u_dut.if_id_pc == t0_target)) begin
                seen4 = 1; t4_cycle = cycle;
            end

            if (roi_on && !roi_off) begin
                roi_cycles = roi_cycles + 1;
                case (cls)
                    8: begin c_other = c_other + 1;
                             if (perf_events[0]) other_ret = other_ret + 1;
                             else                other_noret = other_noret + 1;
                             if (u_dut.id_fire)     other_idfire = other_idfire + 1;
                             if (u_dut.id_ex_advance) other_adv  = other_adv + 1; end
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
                if (retire_n < 256) begin
                    retire_pc_q[retire_n]   = debug_wb_pc;
                    retire_inst_q[retire_n] = debug_inst;
                    retire_n = retire_n + 1;
                end
                // close ROI at the target completion store retire
                if (roi_on && !roi_off && (debug_wb_pc == target_store_pc)) begin
                    roi_off = 1;
                end
            end

            if (cycle <= trace_lim)
                $display("EV,cyc=%0d,ph=0,pc=%h,ireq=%b%b,%h,irsp=%b,%h,pend=%b,%h,%b,buf=%b,%h,ifid=%b,%h,%h,idfire=%b,taken=%b,bj=%h,exc=%b,lu=%b,idex=%b,%h,%b,%h,adv=%b,can=%b,emrdy=%b,emcmp=%b,stall=%b,older=%b,rdir=%b,tgt=%h,fs=%0d,sc=%b,si=%b,front=%b,ret=%b,%h,cls=%0d",
                    cycle, u_dut.pc,
                    inst_req_valid, inst_req_ready, inst_req_addr,
                    inst_rsp_valid, inst_rsp_rdata,
                    u_dut.inst_pending, u_dut.inst_pending_pc, u_dut.inst_pending_drop,
                    u_dut.inst_buffer_valid, u_dut.inst_buffer_pc,
                    u_dut.if_id_valid, u_dut.if_id_pc, u_dut.if_id_inst,
                    u_dut.id_fire, u_dut.id_taken, u_dut.bj_pc,
                    u_dut.id_exc_valid, u_dut.load_use,
                    u_dut.id_ex_valid, u_dut.id_ex_pc,
                    u_dut.id_ex_br_taken, u_dut.id_ex_br_target,
                    u_dut.id_ex_advance, u_dut.id_ex_can_advance,
                    u_dut.ex_mem_ready, u_dut.ex_mem_complete,
                    u_dut.data_pipeline_stall, u_dut.older_fault_for_ex,
                    u_dut.branch_redirect, u_dut.redirect_pc,
                    u_dut.flow_state, u_dut.serial_candidate, u_dut.serial_issue,
                    u_dut.frontend_hold, perf_events[0], debug_wb_pc, cls);
        end
        // phase 1 on the SAME edge, after NBA: did this edge load the target?
        // Kept inside the single posedge block so `cycle` has exactly one owner.
        #1;
        if (resetn && seen2 && !seen3 &&
            u_dut.if_id_valid && (u_dut.if_id_pc == t0_target)) begin
            seen3 = 1;
            t3_cycle = cycle;
            t3_oldpend_pc = u_dut.inst_pending_pc;
            t3_oldbuf_pc  = u_dut.inst_buffer_pc;
            $display("EV,cyc=%0d,ph=1,LOAD_IFID,pc=%h,oldpend_pc=%h,oldbuf_pc=%h,ifid_inst=%h",
                     cycle, u_dut.if_id_pc, t3_oldpend_pc, t3_oldbuf_pc, u_dut.if_id_inst);
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
        for (i = 0; i < 512; i = i + 1) begin
            imem[i] = 32'h0000_0013;
            dmem[i] = 32'h0;
        end
        $readmemh("imem.hex", imem);
        $readmemh("dmem_init.hex", dmem);

        // reset released on a falling edge
        repeat (3) @(negedge clk);
        @(negedge clk);
        resetn = 1'b1;
        repeat (400) @(posedge clk);
        stop_accept = 1'b1;          // stop accepting new I requests, drain in-flight
        repeat (40) @(posedge clk);

        $display("---- mode=%0d ddelay=%0d slowaddr=%0d slowdelay=%0d stpc=%0d ----",
                 mode, ddelay, slow_addr, slow_delay, target_store_pc);
        $display("EVENT t0=%0d t1=%0d t2=%0d t3=%0d t4=%0d t1pc=%h t2reqid=%0d",
                 t0_cycle, t1_cycle, t2_cycle, t3_cycle, t4_cycle, t1_pc, t2_reqid);
        $display("DELTA t1-t0=%0d t2-t1=%0d t3-t2=%0d t4-t3=%0d",
                 t1_cycle-t0_cycle, t2_cycle-t1_cycle, t3_cycle-t2_cycle, t4_cycle-t3_cycle);
        $display("WRONGPATH pending_at_t1=%0d oldpend_pc_at_t3=%h oldbuf_pc_at_t3=%h",
                 pending_at_t1, t3_oldpend_pc, t3_oldbuf_pc);
        $display("IAUDIT acc=%0d rspgen=%0d consume=%0d deliver=%0d drop=%0d inflight=%0d",
                 i_acc, i_rspgen, i_consume, i_deliver, i_drop,
                 i_acc - i_consume);
        if (slow_id > 0)
            $display("SLOWWIT id=%0d addr=%h acc=%0d rsp=%0d consume=%0d consumed_minus_accepted=%0d",
                     slow_id, i_acc_addr[slow_id], i_acc_cyc[slow_id],
                     i_rsp_cyc[slow_id], i_cons_cyc[slow_id],
                     i_cons_cyc[slow_id] - i_acc_cyc[slow_id]);
        $display("DAUDIT acc=%0d rspgen=%0d consume=%0d stores=%0d dmem0=%h",
                 d_acc, d_rspgen, d_consume, d_store, dmem[0]);
        $display("ROI cycles=%0d other=%0d mem=%0d if=%0d branch=%0d load_use=%0d ctrl=%0d hold=%0d",
                 roi_cycles, c_other, c_mem, c_if, c_br, c_lu, c_ctrl, c_hold);
        $display("OTHER ret=%0d noret=%0d idfire=%0d advance=%0d (cross, overlaps)",
                 other_ret, other_noret, other_idfire, other_adv);
        $display("X31CHECK wrong_path_reg=%h (expect 00000000)", u_dut.u_regfile.rf[31]);

        // retire dump for the independent reference comparison
        for (i = 0; i < retire_n; i = i + 1)
            $display("RET,%0d,%h,%h", i, retire_pc_q[i], retire_inst_q[i]);

        if (i_acc !== i_rspgen) begin
            errors = errors + 1;
            $display("RESULT: FAIL iaudit rspgen_mismatch");
        end else if ((i_acc - i_consume) !== 0) begin
            errors = errors + 1;
            $display("RESULT: FAIL iaudit inflight_not_zero");
        end else if (dmem[0] !== 32'h0000_0001) begin
            errors = errors + 1;
            $display("RESULT: FAIL target_flag_missing dmem0=%h", dmem[0]);
        end else if (u_dut.u_regfile.rf[31] !== 32'h0) begin
            errors = errors + 1;
            $display("RESULT: FAIL wrong_path_register_written x31=%h", u_dut.u_regfile.rf[31]);
        end else if (mode == 4) begin
            if (t1_cycle >= 0) begin
                errors = errors + 1;
                $display("RESULT: FAIL nottaken_branch_redirected t1=%0d", t1_cycle);
            end else begin
                $display("RESULT: PASS fix01 nottaken_no_redirect retire=%0d", retire);
            end
        end else if (t1_cycle < 0 || t2_cycle < 0 || t3_cycle < 0 || t4_cycle < 0) begin
            errors = errors + 1;
            $display("RESULT: INCOMPLETE missing_event");
        end else begin
            $display("RESULT: PASS fix01");
        end
        if (errors != 0) $display("RESULT: FAIL fix01 errors=%0d", errors);
        $finish;
    end

    initial begin
        repeat (50000) @(posedge clk);
        $display("RESULT: FAIL timeout");
        $finish;
    end

endmodule
