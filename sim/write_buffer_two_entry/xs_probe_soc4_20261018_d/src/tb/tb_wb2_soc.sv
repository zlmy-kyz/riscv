`timescale 1ns/1ps
// Task043 / 补正02 item 2: minimum real-CPU + real-interconnect fragment.
//
// Real soc_top (real CPU, both interconnects, ROM/RAM/MMIO/UART, I- and
// D-cache, camera/PP apertures) against the functional x32 user-port model.
// The DDR image is preloaded into the model, so this is explicitly NOT a full
// boot. Two epochs, each from a clean reset:
//
//   ep1  ordering: two posted DDR stores -> UART TX store -> on-chip RAM store
//        -> FENCE -> camera x2 -> PP x2 -> DDR done marker.
//        Non-DDR side effects must not be accepted while the posted queue is
//        not empty; FENCE must retire after the whole queue has drained.
//   ep2  interrupt: MEIE + MIE + mtvec, two posted DDR stores, then the
//        harness raises irq_external while the queue is provably busy. The
//        trap must be taken only after the whole queue has drained.
module tb_wb2_soc;
    GTP_GRS GRS_INST (.GRS_N(1'b1));

    reg clk = 0;
    always #5 clk = ~clk;

    reg resetn = 0, init_done = 0, irq_ext = 0;
    integer n = 0, ep = 0;

    wire [27:0] saa, sra;
    wire [255:0] swd, srd;
    wire [31:0] sws;
    wire sav, srv, saw_ap, sar_ap, m_awready, m_wready, m_arready, m_rvalid;
    wire [3:0] saw_id, sar_id, saw_len, sar_len, srid;
    wire srlast;
    wire ddr_writing;
    wire [31:0] cpc, cinst, cvalue;
    wire [3:0] cwe;
    wire [4:0] crd;
    wire [1:0] selftest;
    wire uart_out;

    wb2_ddr_model ddr (
        .clk(clk), .resetn(resetn), .init_done(init_done),
        .awaddr(saa), .awvalid(sav), .awready(m_awready),
        .wdata(swd), .wstrb(sws), .wready(m_wready),
        .araddr(sra), .aruser_id(sar_id), .arvalid(srv), .arready(m_arready),
        .rdata(srd), .rvalid(m_rvalid), .rid(srid), .rlast(srlast),
        .writing(ddr_writing)
    );

    soc_top #(
        .RESET_PC(32'h4000_0000),
        // The defaults of these two follow RESET_PC; they must be pinned here or
        // the 16 KiB ROM/RAM move to 0x4000_0000 and swallow the DDR fetch.
        .INST_ROM_BASE(32'h0), .DATA_RAM_BASE(32'h0),
        .MMIO_BASE(32'h1000_0000), .UART_BASE(32'h1000_1000),
        .ENABLE_CNN(0), .ENABLE_PREPROCESS(1), .ENABLE_CAMERA(1),
        .ENABLE_DDR(1), .DDR_MEM_DQ_WIDTH(32), .DDR_POSTED_WRITE_ENABLE(1),
        .PERF_ENABLE(1), .PERF_AUTO_ARM(0)
    ) soc (
        .cnn_req_valid(), .cnn_req_write(), .cnn_req_size(), .cnn_req_addr(),
        .cnn_req_wdata(), .cnn_req_wstrb(), .cnn_req_ready(1'b0),
        .cnn_rsp_valid(1'b0), .cnn_rsp_error(1'b0), .cnn_rsp_rdata(32'b0),
        .pp_req_valid(), .pp_req_write(), .pp_req_size(), .pp_req_addr(),
        .pp_req_wdata(), .pp_req_wstrb(), .pp_req_ready(1'b0),
        .pp_rsp_valid(1'b0), .pp_rsp_error(1'b0), .pp_rsp_rdata(32'b0),
        // PP aperture 0x4200_0000 lives in the DDR frame window: keep the
        // preprocess slot "done" so the interconnect lets it through to DDR.
        .preprocess_busy(1'b0), .preprocess_done(1'b1),
        .cam_req_valid(), .cam_req_write(), .cam_req_size(), .cam_req_addr(),
        .cam_req_wdata(), .cam_req_wstrb(), .cam_req_ready(1'b0),
        .cam_rsp_valid(1'b0), .cam_rsp_error(1'b0), .cam_rsp_rdata(32'b0),
        .camera_busy(1'b0), .camera_dual_mode(1'b0), .camera_cpu_owned(2'b00),
        .clk(clk), .resetn(resetn), .irq_external(irq_ext),
        .irq_software(1'b0), .irq_timer(1'b0),
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

    // ---- observation points (all pre-edge values) --------------------------
    wire        o_busy   = soc.ddr_write_buffer_busy;
    wire        o_dv     = soc.data_req_valid;
    wire        o_dr     = soc.data_req_ready;
    wire        o_dw     = soc.data_req_write;
    wire [31:0] o_da     = soc.data_req_addr;
    wire        o_ddrsel = soc.u_data_bus_interconnect.ddr_select;
    wire        o_uarsel = soc.u_data_bus_interconnect.uart_select;
    wire        o_rmsel  = soc.u_data_bus_interconnect.ram_select;
    wire        o_mmsel  = soc.u_data_bus_interconnect.mmio_select;
    wire        o_ddrv   = soc.data_ddr_req_valid;
    wire        o_ddrr   = soc.data_ddr_req_ready;
    wire [31:0] o_ddra   = soc.data_ddr_req_addr;
    wire        o_uarv   = soc.uart_req_valid;
    wire        o_uarr   = soc.uart_req_ready;
    wire        o_rmv    = soc.ram_bus_req_valid;
    wire        o_rmr    = soc.ram_bus_req_ready;
    wire        o_mmv    = soc.mmio_req_valid;
    wire        o_mmr    = soc.mmio_req_ready;
    wire        o_wf     = m_wready && ddr_writing;
    wire        o_ret    = soc.u_cpu.normal_retire;
    wire        o_fret   = o_ret && (cpc == 32'h4000_003c);
    wire        o_itk    = soc.u_cpu.irq_take;
    wire [2:0]  o_fl     = soc.u_cpu.flow_state;
    wire [31:0] o_mcs    = soc.u_cpu.u_csr_file.mcause;
    wire [31:0] o_mepc   = soc.u_cpu.u_csr_file.mepc;
    wire [31:0] o_mie    = soc.u_cpu.u_csr_file.mie;
    wire [31:0] o_mst    = soc.u_cpu.u_csr_file.mstatus;

    integer fd;
    task automatic log_edge;
        begin
            $fdisplay(fd,
                "E n=%0d ep=%0d rst=%0b init=%0b busy=%0b dv=%0b dr=%0b dw=%0b da=%08x ds=%01x ddrv=%0b ddrr=%0b ddra=%08x uarv=%0b uarr=%0b rmv=%0b rmr=%0b mmv=%0b mmr=%0b awv=%0b awr=%0b awa=%07x wr=%0b wf=%0b wdv=%064x wsv=%08x arv=%0b arr=%0b ara=%07x ari=%01x rv=%0b rdv=%064x rid=%01x fret=%0b itk=%0b fst=%0d mcs=%08x",
                n, ep, resetn, init_done, o_busy,
                o_dv, o_dr, o_dw, o_da,
                {o_ddrsel, o_uarsel, o_rmsel, o_mmsel},
                o_ddrv, o_ddrr, o_ddra, o_uarv, o_uarr, o_rmv, o_rmr,
                o_mmv, o_mmr,
                sav, m_awready, saa, m_wready, o_wf, swd, sws,
                srv, m_arready, sra, sar_id, m_rvalid, srd, srid,
                o_fret, o_itk, o_fl, o_mcs);
        end
    endtask

    always @(posedge clk) begin
        n = n + 1;
        log_edge;
        if (ep == 1 && soc.u_cpu.sync_trap_event === 1'b1)
            $fatal(1, "RESULT: FAIL unexpected trap in epoch1 cause=%08x pc=%08x",
                   soc.u_cpu.wb_trap_cause, cpc);
        if (o_ret)
            $fdisplay(fd, "T n=%0d ep=%0d pc=%08x inst=%08x we=%01x rd=%02x wd=%08x",
                      n, ep, cpc, cinst, cwe[0], crd, cvalue);
        if (o_itk)
            $fdisplay(fd, "I n=%0d ep=%0d cause=%08x epc=%08x mie=%08x mst=%08x busy=%0b",
                      n, ep, o_mcs, o_mepc, o_mie, o_mst, o_busy);
        if (n > 200000) $fatal(1, "RESULT: FAIL cycle watchdog");
    end

    string edge_path, mem_path, prog_a, prog_b;
    integer guard;
    integer traps = 0;

    // Poll the model's backing store directly: a value argument would be copied
    // once and never see the update.
    task automatic wait_ddr(input integer beat, input [31:0] want, input integer lim);
        begin
            guard = 0;
            while (ddr.beats[beat][31:0] !== want && guard < lim) begin
                @(negedge clk); guard = guard + 1;
            end
        end
    endtask

    initial begin : run
        // Fixed relative paths: the runner always executes with its own frozen
        // run directory as cwd, and xsim's batch launcher splits '=' inside an
        // argv token, so --testplusarg cannot carry "NAME=value" on this host.
        edge_path = "soc.edges.log";
        mem_path  = "soc.mem.log";
        prog_a    = "src/tb/soc_wb2_a.hex";
        prog_b    = "src/tb/soc_wb2_b.hex";
        fd = $fopen(edge_path, "w");
        if (!fd) $fatal(1, "RESULT: FAIL cannot open edge log");

        // ---------------- epoch 1: ordering ----------------
        ep = 1;
        ddr.preload_hex(prog_a);
        resetn = 0; init_done = 0; irq_ext = 0;
        repeat (6) @(negedge clk);
        resetn = 1; init_done = 1;
        wait_ddr(32'h82, 32'h0000_0001, 40000);
        if (ddr.beats[32'h82][31:0] !== 32'h0000_0001)
            $fatal(1, "RESULT: FAIL epoch1 no DDR done marker");
        repeat (60) @(negedge clk);
        $display("EPOCH1 done edge=%0d", n);

        // ---------------- epoch 2: external interrupt ----------------
        ep = 2;
        resetn = 0; init_done = 0; irq_ext = 0;
        repeat (6) @(negedge clk);
        ddr.preload_hex(prog_b);
        resetn = 1; init_done = 1;
        // Raise the interrupt only once the posted queue is provably occupied:
        // the first AW has been accepted and at least one beat is still queued.
        guard = 0;
        while (!(sav === 1'b1 && m_awready === 1'b1) && guard < 4000) begin
            @(negedge clk); guard = guard + 1;
        end
        if (guard >= 4000) $fatal(1, "RESULT: FAIL epoch2 no AW before the interrupt");
        @(negedge clk);
        if (o_busy !== 1'b1) $fatal(1, "RESULT: FAIL epoch2 queue not busy at irq raise");
        irq_ext = 1;
        $display("IRQ raised edge=%0d busy=%0b", n, o_busy);
        wait_ddr(32'h102, 32'h0000_0007, 20000);
        if (ddr.beats[32'h102][31:0] !== 32'h0000_0007)
            $fatal(1, "RESULT: FAIL epoch2 handler marker missing");
        repeat (60) @(negedge clk);
        $display("EPOCH2 irq cause=%08x epc=%08x", o_mcs, o_mepc);

        ddr.dump(mem_path);
        $fclose(fd);
        $display("RESULT: PASS wb2_soc edges=%0d", n);
        $finish;
    end

    initial begin
        #20000000;
        $fatal(1, "RESULT: FAIL wall watchdog");
    end
endmodule
