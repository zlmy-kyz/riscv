`timescale 1ns/1ps
// Task033 minimal real-CPU integration.
// Real CPU / interconnects / icache / dcache / on-chip ROM+RAM / UART+MMIO and
// the bridge under test; the DDR3 user port is the functional x32 model. Camera,
// PP and CNN stay enabled but their ports are idle. The program image is loaded
// straight into the model, so this is explicitly NOT a Full Boot.
module tb_inst_hit_overlap_soc;
    GTP_GRS GRS_INST (.GRS_N(1'b1));

    reg clk = 0;
    always #5 clk = ~clk;

    reg resetn = 0, init_done = 0;
    integer ep = 0;

    wire [27:0] saa, sra;
    wire sav, srv, saw_ap, sar_ap, m_awready, m_wready, m_arready, m_rvalid;
    wire [255:0] swd, srd;
    wire [31:0] sws;
    wire [3:0] saw_id, sar_id, saw_len, sar_len, srid;
    wire srlast;
    wire [31:0] cpc, cinst, cvalue, cnpc;
    wire [3:0] cwe;
    wire [4:0] crd;
    wire [1:0] selftest;
    wire uart_out;

    overlap_ddr_model ddr (
        .clk(clk), .resetn(resetn), .init_done(init_done),
        .awaddr(saa), .awvalid(sav), .awready(m_awready), .wdata(swd), .wstrb(sws),
        .wready(m_wready), .araddr(sra), .aruser_id(sar_id), .arvalid(srv),
        .arready(m_arready), .rdata(srd), .rvalid(m_rvalid), .rid(srid), .rlast(srlast)
    );

    soc_top #(
        .RESET_PC(32'h4000_0000), .INST_ROM_BASE(32'h0), .DATA_RAM_BASE(32'h0),
        .ENABLE_CNN(1), .ENABLE_PREPROCESS(1), .ENABLE_CAMERA(1),
        .ENABLE_DDR(1), .DDR_MEM_DQ_WIDTH(32), .DDR_POSTED_WRITE_ENABLE(1),
        .PERF_ENABLE(1), .PERF_AUTO_ARM(0)
    ) soc (
        .cnn_req_valid(), .cnn_req_write(), .cnn_req_size(), .cnn_req_addr(),
        .cnn_req_wdata(), .cnn_req_wstrb(), .cnn_req_ready(1'b0),
        .cnn_rsp_valid(1'b0), .cnn_rsp_error(1'b0), .cnn_rsp_rdata(32'b0),
        .pp_req_valid(), .pp_req_write(), .pp_req_size(), .pp_req_addr(),
        .pp_req_wdata(), .pp_req_wstrb(), .pp_req_ready(1'b0),
        .pp_rsp_valid(1'b0), .pp_rsp_error(1'b0), .pp_rsp_rdata(32'b0),
        .preprocess_busy(1'b0), .preprocess_done(1'b0),
        .cam_req_valid(), .cam_req_write(), .cam_req_size(), .cam_req_addr(),
        .cam_req_wdata(), .cam_req_wstrb(), .cam_req_ready(1'b0),
        .cam_rsp_valid(1'b0), .cam_rsp_error(1'b0), .cam_rsp_rdata(32'b0),
        .camera_busy(1'b0), .camera_dual_mode(1'b0), .camera_cpu_owned(2'b00),
        .clk(clk), .resetn(resetn), .irq_external(1'b0), .irq_software(1'b0),
        .irq_timer(1'b0),
        .debug_wb_pc(cpc), .debug_wb_rf_we(cwe), .debug_wb_rf_wnum(crd),
        .debug_wb_rf_wdata(cvalue), .debug_inst(cinst),
        .ddr_init_done(init_done),
        .ddr_axi_awaddr(saa), .ddr_axi_awuser_ap(saw_ap), .ddr_axi_awuser_id(saw_id),
        .ddr_axi_awlen(saw_len), .ddr_axi_awready(m_awready), .ddr_axi_awvalid(sav),
        .ddr_axi_wdata(swd), .ddr_axi_wstrb(sws), .ddr_axi_wready(m_wready),
        .ddr_axi_wusero_id(4'd1), .ddr_axi_wusero_last(m_wready),
        .ddr_axi_araddr(sra), .ddr_axi_aruser_ap(sar_ap), .ddr_axi_aruser_id(sar_id),
        .ddr_axi_arlen(sar_len), .ddr_axi_arready(m_arready), .ddr_axi_arvalid(srv),
        .ddr_axi_rdata(srd), .ddr_axi_rid(srid), .ddr_axi_rlast(srlast),
        .ddr_axi_rvalid(m_rvalid), .selftest_status(selftest),
        .uart_rx(1'b1), .uart_tx(uart_out)
    );

    integer fd, n = 0;
    string edge_path, mem_path, prog_path, fault_cam, fault_pp;
    integer traps = 0;

    task automatic log_edge(input string ph);
        begin
            // Same field set as the bridge job, but sampled on the bridge's own
            // ports inside the SoC (DDR-local byte addresses), so the same
            // independent reference can replay it.
            $fdisplay(fd, "E n=%0d ph=%s rst=%0b init=%0b iv=%0b ir=%0b ia=%08x dv=%0b dr=%0b dw=%0b sz=%0d da=%08x dwd=%08x ds=%01x ip=%0b ie=%0b id=%08x dp=%0b de=%0b dd=%08x busy=%0b arv=%0b arr=%0b ara=%07x ari=%01x arl=%01x awv=%0b awr=%0b awa=%07x awi=%01x awl=%01x wrdy=%0b wdv=%064x wsv=%08x rv=%0b rdv=%064x rid=%01x rl=%0b ep=%0d",
                n, ph, resetn, init_done,
                soc.inst_ddr_req_valid, soc.inst_ddr_req_ready, soc.inst_ddr_req_addr,
                soc.data_ddr_req_valid, soc.data_ddr_req_ready, soc.data_ddr_req_write,
                soc.data_ddr_req_size, soc.data_ddr_req_addr, soc.data_ddr_req_wdata,
                soc.data_ddr_req_wstrb,
                soc.inst_ddr_rsp_valid, soc.inst_ddr_rsp_error, soc.inst_ddr_rsp_rdata,
                soc.g_ddr.bridge_data_rsp_valid, soc.g_ddr.bridge_data_rsp_error,
                soc.g_ddr.bridge_data_rsp_rdata, soc.ddr_write_buffer_busy,
                srv, m_arready, sra, sar_id, sar_len, sav, m_awready, saa, saw_id, saw_len,
                m_wready, swd, sws, m_rvalid, srd, srid, srlast, ep);
            $fdisplay(fd, "F n=%0d ph=%s hold=%0b bufv=%0b bufp=%08x pop=%0b pend=%0b pendpc=%08x drop=%0b stall=%0b flow=%0d ep=%0d",
                n, ph, soc.u_cpu.frontend_hold, soc.u_cpu.inst_buffer_valid,
                soc.u_cpu.inst_buffer_pc, soc.u_cpu.inst_buffer_pop,
                soc.u_cpu.inst_pending, soc.u_cpu.inst_pending_pc,
                soc.u_cpu.inst_pending_drop, soc.u_cpu.data_pipeline_stall,
                soc.u_cpu.flow_state, ep);
            if (ph == "PRE" && (soc.u_cpu.normal_retire || soc.u_cpu.sync_trap_event ||
                soc.u_cpu.mret_commit))
                $fdisplay(fd, "R n=%0d pc=%08x inst=%08x we=%01x rd=%02x wd=%08x npc=%08x trap=%0b cause=%02x tval=%08x irq=%0b ep=%0d",
                    n, cpc, cinst, cwe[0], crd, cvalue, soc.u_cpu.mem_wb_next_pc,
                    soc.u_cpu.sync_trap_event, soc.u_cpu.wb_trap_cause,
                    soc.u_cpu.wb_trap_tval, soc.u_cpu.irq_take, ep);
        end
    endtask

    always @(posedge clk) begin
        n = n + 1;
        log_edge("PRE");
        #1;
        log_edge("POST");
        if (n > 100000) $fatal(1, "RESULT: FAIL cycle watchdog");
    end

    integer guard;
    initial begin : run
        if (!$value$plusargs("EDGE_LOG=%s", edge_path)) $fatal(1, "RESULT: FAIL missing EDGE_LOG");
        if (!$value$plusargs("MEM_DUMP=%s", mem_path)) $fatal(1, "RESULT: FAIL missing MEM_DUMP");
        if (!$value$plusargs("PROG=%s", prog_path)) $fatal(1, "RESULT: FAIL missing PROG");
        if (!$value$plusargs("FAULT_CAM=%s", fault_cam)) $fatal(1, "RESULT: FAIL missing FAULT_CAM");
        if (!$value$plusargs("FAULT_PP=%s", fault_pp)) $fatal(1, "RESULT: FAIL missing FAULT_PP");
        fd = $fopen(edge_path, "w");
        if (!fd) $fatal(1, "RESULT: FAIL cannot open edge log");

        // Realistic latency: the slot is not free on the very next edge.
        ddr.ar_block = 2;
        ddr.r_lat = 10;
        ddr.aw_block = 1;
        ddr.w_lat = 3;

        // ---------------- epoch 1: main program ----------------
        ep = 1;
        ddr.preload_hex(prog_path, 116);
        resetn = 0;
        repeat (4) @(negedge clk);
        resetn = 1; init_done = 1;
        guard = 0;
        while (selftest != 2'd2 && guard < 20000) begin
            @(negedge clk); guard = guard + 1;
        end
        if (selftest != 2'd2) $fatal(1, "RESULT: FAIL no TEST_STATUS PASS");
        repeat (60) @(negedge clk);
        $display("EPOCH1 pass edge=%0d", n);

        // ---------------- epoch 2: Camera window illegal fetch ----------------
        ep = 2;
        resetn = 0;
        repeat (4) @(negedge clk);
        ddr.preload_hex(fault_cam, 2);
        resetn = 1; init_done = 1;
        guard = 0;
        while (soc.u_cpu.sync_trap_event !== 1'b1 && guard < 400) begin
            @(negedge clk); guard = guard + 1;
        end
        if (soc.u_cpu.sync_trap_event !== 1'b1) $fatal(1, "RESULT: FAIL no camera trap");
        traps = traps + 1;
        repeat (6) @(negedge clk);
        $display("EPOCH2 camera trap cause=%0d tval=%08x",
                 soc.u_cpu.u_csr_file.mcause, soc.u_cpu.u_csr_file.mtval);

        // ---------------- epoch 3: PP window illegal fetch ----------------
        ep = 3;
        resetn = 0;
        repeat (4) @(negedge clk);
        ddr.preload_hex(fault_pp, 2);
        resetn = 1; init_done = 1;
        guard = 0;
        while (soc.u_cpu.sync_trap_event !== 1'b1 && guard < 400) begin
            @(negedge clk); guard = guard + 1;
        end
        if (soc.u_cpu.sync_trap_event !== 1'b1) $fatal(1, "RESULT: FAIL no PP trap");
        traps = traps + 1;
        repeat (6) @(negedge clk);
        $display("EPOCH3 pp trap cause=%0d tval=%08x",
                 soc.u_cpu.u_csr_file.mcause, soc.u_cpu.u_csr_file.mtval);

        ddr.dump(mem_path);
        $fclose(fd);
        $display("RESULT: PASS inst_hit_overlap_soc trap_count=%0d edges=%0d", traps, n);
        $finish;
    end

    initial begin
        #4000000;
        $fatal(1, "RESULT: FAIL wall watchdog");
    end
endmodule
