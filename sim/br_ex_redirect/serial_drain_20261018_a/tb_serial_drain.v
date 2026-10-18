`timescale 1ns/1ps
// ===========================================================================
// tb_serial_drain.v  —  Task038 minimal localisation
//
// Purpose: prove or disprove that an EX-stage branch redirect can strand the
// flow FSM in FLOW_SERIAL_DRAIN because the younger ID CSR that started the
// drain was flushed, while serial_issue still requires a live serial_candidate.
//
// Instruction side intentionally uses the real one-cycle hit contract:
//   E   : address accepted (req_valid && req_ready)
//   E+1 : rsp_valid=1 with data for that address, and E+1 may accept the next
//   (combinational read sampled at E, registered for E+1; no zero-cycle response)
// The earlier two-cycle model is rejected by the task because it cannot show
// an EX branch overlapping a younger ID serial instruction.
//
// Modes: +MODE=1 (A: branch straight into CSR)
//        +MODE=2 (B: drain entered while an older load still holds MEM)
//        +MODE=3 (control: branch straight into a plain ALU instruction)
//        +MODE=4 (control: serial CSR executed on the correct path)
// +DDELAY=n  data-side response latency (>=1). I side is always 1 cycle.
// ===========================================================================
module tb_serial_drain;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] imem [0:255];
    reg [31:0] dmem [0:255];

    wire        inst_req_valid;
    wire [31:0] inst_req_addr;
    reg         inst_req_ready = 1'b1;
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

    // ---------------- instruction side: one-cycle hit ----------------
    wire i_fire = inst_req_valid && inst_req_ready;
    always @(posedge clk) begin
        inst_rsp_valid <= i_fire;
        if (i_fire) inst_rsp_rdata <= imem[inst_req_addr[9:2]];
    end

    // ---------------- data side: configurable latency ----------------
    integer delay = 1;
    integer d_cnt = 0;
    reg [31:0] d_addr_q = 32'b0;
    reg        d_wr_q = 1'b0;
    reg [31:0] d_wd_q = 32'b0;
    reg [ 3:0] d_ws_q = 4'b0;
    integer    wi;

    wire d_fire = data_req_valid && data_req_ready;

    always @(posedge clk) begin
        if (delay <= 1) begin
            data_rsp_valid <= d_fire;
            if (d_fire) begin
                data_rsp_rdata <= dmem[data_req_addr[9:2]];
                if (data_req_write)
                    for (wi = 0; wi < 4; wi = wi + 1)
                        if (data_req_wstrb[wi])
                            dmem[data_req_addr[9:2]][8*wi +: 8] <= data_req_wdata[8*wi +: 8];
            end
        end else begin
            data_rsp_valid <= (d_cnt == 1);
            if (d_cnt == 1) begin
                data_rsp_rdata <= dmem[d_addr_q[9:2]];
                if (d_wr_q)
                    for (wi = 0; wi < 4; wi = wi + 1)
                        if (d_ws_q[wi])
                            dmem[d_addr_q[9:2]][8*wi +: 8] <= d_wd_q[8*wi +: 8];
            end
            if (d_fire) begin
                d_addr_q <= data_req_addr;
                d_wr_q   <= data_req_write;
                d_wd_q   <= data_req_wdata;
                d_ws_q   <= data_req_wstrb;
                d_cnt    <= delay;
            end else if (d_cnt > 0) begin
                d_cnt <= d_cnt - 1;
            end
        end
    end

    // ---------------- observation ----------------
    integer mode = 1;
    integer cycle = 0;
    integer stuck_cycle = -1;
    integer stuck_run = 0;
    reg     stuck = 1'b0;
    reg     saw_drain = 1'b0;
    integer drain_cycle = -1;
    integer first_redirect_cycle = -1;
    integer retire = 0;

    always @(posedge clk) begin
        cycle = cycle + 1;
        if (resetn) begin
            if (perf_events[0]) retire = retire + 1;
            if (u_dut.flow_state == 3'd1 && !saw_drain) begin
                saw_drain    = 1'b1;
                drain_cycle  = cycle;
            end
            if (u_dut.branch_redirect && first_redirect_cycle < 0)
                first_redirect_cycle = cycle;
            // 死锁判据：连续 8 拍处于"DRAIN 且无串行候选"才算永久停滞。
            // 单拍满足只是撤销转移的那一拍，下一拍就应恢复，不算死锁。
            if (u_dut.flow_state == 3'd1 && !u_dut.serial_candidate)
                stuck_run = stuck_run + 1;
            else
                stuck_run = 0;
            if (!stuck && stuck_run >= 8) begin
                stuck       = 1'b1;
                stuck_cycle = cycle - 7;
            end
            if (cycle < 40)
                $display("TR cyc=%0d pc=%h ifid=%b/%h/%h idex=%b/%h/%b/%h fire=%b adv=%b rdir=%b tgt=%h fs=%0d sc=%b si=%b pe=%b hold=%b ireq=%b/%b/%h pend=%b/%b",
                    cycle, u_dut.pc,
                    u_dut.if_id_valid, u_dut.if_id_pc, u_dut.if_id_inst,
                    u_dut.id_ex_valid, u_dut.id_ex_pc,
                    u_dut.id_taken, u_dut.bj_pc,
                    u_dut.id_fire, u_dut.id_ex_advance,
                    u_dut.branch_redirect, u_dut.redirect_pc,
                    u_dut.flow_state, u_dut.serial_candidate, u_dut.serial_issue,
                    u_dut.pipeline_empty, u_dut.frontend_hold,
                    u_dut.inst_req_valid, u_dut.inst_req_ready, u_dut.inst_req_addr,
                    u_dut.inst_pending, u_dut.inst_pending_drop);
        end
    end

    integer errors = 0;
    integer done_ok = 0;

    initial begin
        if (!$value$plusargs("MODE=%d", mode)) mode = 1;
        if (!$value$plusargs("DDELAY=%d", delay)) delay = 1;
        if (delay < 1) delay = 1;
        for (wi = 0; wi < 256; wi = wi + 1) begin
            imem[wi] = 32'h0000_0013;
            dmem[wi] = 32'h0;
        end
        $readmemh("imem.hex", imem);
        $readmemh("dmem_init.hex", dmem);

        repeat (6) @(posedge clk);
        resetn = 1'b1;
        repeat (2000) @(posedge clk);

        done_ok = (dmem[0] == 32'h1);
        $display("---- mode=%0d ddelay=%0d retire=%0d drain_cycle=%0d redirect_cycle=%0d stuck_cycle=%0d flow_state=%0d dmem0=%h ----",
                 mode, delay, retire, drain_cycle, first_redirect_cycle, stuck_cycle,
                 u_dut.flow_state, dmem[0]);

        if (mode == 1 || mode == 2) begin
            if (stuck) begin
                $display("RESULT: EXPECTED_BUG_REPRODUCED stuck_at_cycle=%0d drain_cycle=%0d redirect_cycle=%0d dmem0=%h",
                         stuck_cycle, drain_cycle, first_redirect_cycle, dmem[0]);
            end else if (done_ok) begin
                $display("RESULT: NO_REPRODUCTION target_completed dmem0=%h", dmem[0]);
            end else begin
                $display("RESULT: INCOMPLETE no_drain_no_completion drain_cycle=%0d dmem0=%h",
                         drain_cycle, dmem[0]);
            end
        end else begin
            if (done_ok && !stuck) $display("RESULT: PASS control_completed dmem0=%h", dmem[0]);
            else begin
                errors = errors + 1;
                $display("RESULT: FAIL control_did_not_complete dmem0=%h stuck=%0d", dmem[0], stuck);
            end
        end
        $finish;
    end

endmodule
