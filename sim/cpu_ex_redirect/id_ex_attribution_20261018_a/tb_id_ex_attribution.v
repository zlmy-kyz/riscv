`timescale 1ns/1ps
// ===========================================================================
// tb_id_ex_attribution.v  —  Task040 dynamic attribution for CPU 039
//
// Instruction side is a TRUE one-cycle single-slot model:
//   E   : request accepted (req_ready = !busy)
//   E+1 : rsp_valid=1 with the data of that address, ready already back to 1
//         so an accept can happen on the same edge as the old response is used.
// A declared slow address (+SLOWADDR / +SLOWDELAY) models an in-flight
// wrong-path fetch; the delay is selected by the ACCEPTED ADDRESS only and
// never reads DUT taken/redirect signals.
// Data side latency: +DDELAY (1 = one-cycle hit).
//
// Five events per taken branch instance: t0 id_fire, t1 ex_br_redirect,
// t2 target accepted, t3 target into IF/ID, t4 target id_fire.
// OTHER classification is taken from the real cpu_perf_counters expression.
// ===========================================================================
module tb_id_ex_attribution;

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

    // ---------------- instruction side: one slot, one-cycle hit ----------------
    integer    slow_addr  = -1;
    integer    slow_delay = 8;
    integer    i_busy = 0;
    integer    i_cnt  = 0;
    reg [31:0] i_addr_q = 32'b0;
    reg [31:0] i_data_q = 32'b0;
    integer    i_acc  = 0;      // accepted count
    integer    i_rsp  = 0;

    assign inst_req_ready = (i_busy == 0) ? 1'b1 : 1'b0;
    wire i_fire = inst_req_valid && inst_req_ready;

    always @(posedge clk) begin
        inst_rsp_valid <= 1'b0;
        if (i_fire) begin
            i_addr_q <= inst_req_addr;
            i_data_q <= imem[inst_req_addr[10:2]];
            i_acc    = i_acc + 1;
            if (inst_req_addr == slow_addr) begin
                i_busy <= 1;
                i_cnt  <= slow_delay;
            end else begin
                // one-cycle hit: response is valid during the next cycle
                inst_rsp_valid <= 1'b1;
                inst_rsp_rdata <= imem[inst_req_addr[10:2]];
                i_rsp = i_rsp + 1;
            end
        end else if (i_busy == 1) begin
            if (i_cnt == 1) begin
                inst_rsp_valid <= 1'b1;
                inst_rsp_rdata <= i_data_q;
                i_busy <= 0;
                i_rsp  = i_rsp + 1;
            end else begin
                i_cnt <= i_cnt - 1;
            end
        end
    end

    // ---------------- data side ----------------
    integer ddelay = 1;
    integer d_busy = 0;
    integer d_cnt  = 0;
    reg [31:0] d_addr_q = 32'b0;
    reg        d_wr_q = 1'b0;
    reg [31:0] d_wd_q = 32'b0;
    reg [ 3:0] d_ws_q = 4'b0;
    integer    wi;
    reg [31:0] d_lat_q = 32'b0;

    always @(posedge clk) begin
        data_rsp_valid <= 1'b0;
        if (data_req_valid && data_req_ready) begin
            d_addr_q <= data_req_addr;
            d_lat_q  <= dmem[data_req_addr[10:2]];
            if (data_req_write) begin
                for (wi = 0; wi < 4; wi = wi + 1)
                    if (data_req_wstrb[wi])
                        dmem[data_req_addr[10:2]][8*wi +: 8] <= data_req_wdata[8*wi +: 8];
                if (ddelay <= 1) begin
                    data_rsp_valid <= 1'b1;
                    data_rsp_rdata <= 32'b0;
                end else begin
                    d_busy <= 1; d_cnt <= ddelay;
                end
            end else begin
                if (ddelay <= 1) begin
                    data_rsp_valid <= 1'b1;
                    data_rsp_rdata <= dmem[data_req_addr[10:2]];
                end else begin
                    d_busy <= 1; d_cnt <= ddelay;
                end
            end
        end else if (d_busy == 1) begin
            if (d_cnt == 1) begin
                data_rsp_valid <= 1'b1;
                data_rsp_rdata <= d_lat_q;
                d_busy <= 0;
            end else d_cnt <= d_cnt - 1;
        end
    end

    // ---------------- real classification from cpu_perf_counters ----------------
    wire [3:0] cls;
    wire [31:0] perf_rdata;
    wire        perf_error;
    cpu_perf_counters u_perf (
        .clk(clk), .resetn(resetn),
        .events(perf_events), .retire_pc(debug_wb_pc),
        .branch_target(perf_branch_target), .fetch_pc(perf_fetch_pc),
        .timer_value(32'b0), .ar_fire(1'b0), .aw_fire(1'b0),
        .timer_read(1'b0), .access(1'b0), .write(1'b0), .size(2'b00),
        .addr(12'b0), .wdata(32'b0), .wstrb(4'b0),
        .rdata(perf_rdata), .error(perf_error)
    );
    assign cls = u_perf.classification;   // 8 = OTHER, same expression as RTL

    // ---------------- five-event tracking for the first taken branch ----------------
    integer cycle = 0;
    integer br_seen = 0;
    integer t0_cycle = -1, t1_cycle = -1, t2_cycle = -1, t3_cycle = -1, t4_cycle = -1;
    integer t0_pc = 0, t0_target = 0;
    integer seen1 = 0, seen2 = 0, seen3 = 0, seen4 = 0;
    integer wrong_path_pending_at_t1 = -1;
    integer other_cycles = 0, mem_cycles = 0, if_cycles = 0, branch_cycles = 0;
    integer load_use_cycles = 0, ctrl_cycles = 0, ctrl_hold_cycles = 0;
    integer other_retire = 0, other_noretire = 0;
    integer retire = 0;
    integer n_accept = 0, n_rsp = 0;
    integer i;
    integer trace_lim = 60;

    always @(posedge clk) begin
        cycle = cycle + 1;
        if (resetn) begin
            if (perf_events[0]) retire = retire + 1;
            case (cls)
                8: begin other_cycles = other_cycles + 1;
                         if (perf_events[0]) other_retire = other_retire + 1;
                         else other_noretire = other_noretire + 1; end
                3: mem_cycles      = mem_cycles + 1;
                2: if_cycles       = if_cycles + 1;
                4: branch_cycles   = branch_cycles + 1;
                7: load_use_cycles = load_use_cycles + 1;
                5: ctrl_cycles     = ctrl_cycles + 1;
                6: ctrl_hold_cycles= ctrl_hold_cycles + 1;
                default: ;
            endcase

            // t0: first taken CONDITIONAL branch leaving ID. JAL/JALR are
            // excluded so a trailing spin `j` cannot stand in for the branch
            // under test (m4's not-taken case must produce no t0 at all).
            if (!br_seen && u_dut.id_fire && u_dut.id_taken &&
                u_dut.inst_b && !u_dut.id_exc_valid) begin
                br_seen   = 1;
                t0_cycle  = cycle;
                t0_pc     = u_dut.if_id_pc;
                t0_target = u_dut.bj_pc;
            end
            // t1: same instance raises EX redirect
            if (br_seen && !seen1 && u_dut.ex_br_redirect) begin
                seen1 = 1; t1_cycle = cycle;
                wrong_path_pending_at_t1 = (u_dut.inst_pending && !u_dut.inst_rsp_valid);
            end
            // t2: target address accepted (only after t1)
            if (seen1 && !seen2 && i_fire && (inst_req_addr == t0_target)) begin
                seen2 = 1; t2_cycle = cycle;
            end
            // t3: target actually loaded into IF/ID
            if (seen2 && !seen3 && u_dut.if_id_valid &&
                (u_dut.if_id_pc == t0_target) && !u_dut.kill_if_id) begin
                seen3 = 1; t3_cycle = cycle;
            end
            // t4: target instruction issues from ID
            if (seen3 && !seen4 && u_dut.id_fire &&
                (u_dut.if_id_pc == t0_target)) begin
                seen4 = 1; t4_cycle = cycle;
            end

            if (cycle <= trace_lim)
                $display("EV,cyc=%0d,pc=%h,ireq=%b%b,%h,irsp=%b,%b,%h,pend=%b,%h,%b,buf=%b,%h,ifid=%b,%h,%h,id_fire=%b,id_taken=%b,bj=%h,idex=%b,%h,%b,%h,adv=%b,emrdy=%b,emcmp=%b,stall=%b,older=%b,rdir=%b,tgt=%h,fs=%0d,front=%b,cls=%0d,ret=%b",
                    cycle, u_dut.pc,
                    inst_req_valid, inst_req_ready, inst_req_addr,
                    inst_rsp_valid, inst_rsp_error, inst_rsp_rdata,
                    u_dut.inst_pending, u_dut.inst_pending_pc, u_dut.inst_pending_drop,
                    u_dut.inst_buffer_valid, u_dut.inst_buffer_pc,
                    u_dut.if_id_valid, u_dut.if_id_pc, u_dut.if_id_inst,
                    u_dut.id_fire, u_dut.id_taken, u_dut.bj_pc,
                    u_dut.id_ex_valid, u_dut.id_ex_pc,
                    u_dut.id_ex_br_taken, u_dut.id_ex_br_target,
                    u_dut.id_ex_advance, u_dut.ex_mem_ready, u_dut.ex_mem_complete,
                    u_dut.data_pipeline_stall, u_dut.older_fault_for_ex,
                    u_dut.branch_redirect, u_dut.redirect_pc,
                    u_dut.flow_state, u_dut.frontend_hold, cls, perf_events[0]);
        end
    end

    integer mode = 1;
    integer errors = 0;
    reg     void_ignore;

    initial begin
        if (!$value$plusargs("MODE=%d", mode)) mode = 1;
        if (!$value$plusargs("DDELAY=%d", ddelay)) ddelay = 1;
        if (!$value$plusargs("SLOWDELAY=%d", slow_delay)) slow_delay = 8;
        void_ignore = $value$plusargs("SLOWADDR=%d", slow_addr);
        for (i = 0; i < 512; i = i + 1) begin
            imem[i] = 32'h0000_0013;
            dmem[i] = 32'h0;
        end
        $readmemh("imem.hex", imem);
        $readmemh("dmem_init.hex", dmem);

        repeat (6) @(posedge clk);
        resetn = 1'b1;
        repeat (400) @(posedge clk);

        $display("---- mode=%0d ddelay=%0d slowaddr=%0h slowdelay=%0d ----",
                 mode, ddelay, slow_addr, slow_delay);
        $display("EVENT t0=%0d t1=%0d t2=%0d t3=%0d t4=%0d", t0_cycle, t1_cycle, t2_cycle, t3_cycle, t4_cycle);
        $display("DELTA t1-t0=%0d t2-t1=%0d t3-t2=%0d t4-t3=%0d", t1_cycle-t0_cycle,
                 t2_cycle-t1_cycle, t3_cycle-t2_cycle, t4_cycle-t3_cycle);
        $display("WRONGPATH pending_at_t1=%0d", wrong_path_pending_at_t1);
        $display("CLASS other=%0d mem=%0d if=%0d branch=%0d load_use=%0d ctrl=%0d ctrl_hold=%0d",
                 other_cycles, mem_cycles, if_cycles, branch_cycles,
                 load_use_cycles, ctrl_cycles, ctrl_hold_cycles);
        $display("OTHER retire=%0d noretire=%0d (cross-stat, may overlap)", other_retire, other_noretire);
        $display("IOPS accept=%0d rsp=%0d inflight=%0d dmem0=%h", i_acc, i_rsp, i_busy, dmem[0]);

        if (mode == 4) begin
            // not-taken control: no redirect at all, correct path commits
            if (dmem[0] !== 32'h0000_0001) begin
                errors = errors + 1;
                $display("RESULT: FAIL nottaken_flag_missing dmem0=%h", dmem[0]);
            end else if (t1_cycle >= 0) begin
                errors = errors + 1;
                $display("RESULT: FAIL nottaken_branch_redirected t1=%0d", t1_cycle);
            end else begin
                $display("RESULT: PASS nottaken_control no_redirect retire=%0d", retire);
            end
        end else if (!seen1 || !seen2 || !seen3 || !seen4) begin
            errors = errors + 1;
            $display("RESULT: INCOMPLETE missing_event seen=%0d%0d%0d%0d", seen1, seen2, seen3, seen4);
        end else if (dmem[0] !== 32'h0000_0001) begin
            errors = errors + 1;
            $display("RESULT: FAIL target_flag_missing dmem0=%h", dmem[0]);
        end else begin
            $display("RESULT: PASS id_ex_attribution errors=0");
        end
        $finish;
    end

    initial begin
        repeat (20000) @(posedge clk);
        $display("RESULT: FAIL timeout");
        $finish;
    end
endmodule
