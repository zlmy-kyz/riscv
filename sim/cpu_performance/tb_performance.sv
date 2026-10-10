`timescale 1ns/10fs
`ifdef PERF_PHYSICAL
`define SOC dut.u_soc
`define CPU dut.u_soc.u_cpu
`else
`define SOC dut
`define CPU dut.u_cpu
`endif
module tb_performance;
    wire clk, resetn, txd;
`ifdef PERF_PHYSICAL
    reg ref_clk=0, board_resetn=1, grs_n=0;
    wire init_done;
    wire csn,rstn,ck,ckn,cke,rasn,casn,wen,odt;
    wire [14:0] addr;
    wire [2:0] ba;
    wire [1:0] dqs,dqsn,dm;
    wire [15:0] dq;
    GTP_GRS GRS_INST(.GRS_N(grs_n));
    always #4 ref_clk=~ref_clk;
    initial begin #5 grs_n=1; end
    initial begin #10 board_resetn=0; #50 board_resetn=1; end
`ifdef PERF_DIRECT
    perf_ddr3_setup #(.CORE_CLK_HZ(93750000)) dut(
`else
    soc_ddr3_top #(.CORE_CLK_HZ(93750000)) dut(
`endif
        .ddr_ref_clk(ref_clk),.resetn(board_resetn),.uart_rx(1'b1),.uart_tx(txd),
        .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .core_clk(clk),.ddr_init_done(init_done),.soc_resetn(resetn),
        .debug_wb_pc(),.debug_wb_rf_we(),.debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(),
        .mem_cs_n(csn),.mem_rst_n(rstn),.mem_ck(ck),.mem_ck_n(ckn),.mem_cke(cke),
        .mem_ras_n(rasn),.mem_cas_n(casn),.mem_we_n(wen),.mem_odt(odt),
        .mem_a(addr),.mem_ba(ba),.mem_dqs(dqs),.mem_dqs_n(dqsn),.mem_dm(dm),.mem_dq(dq),
        .led_clk_alive(),.led_ddr_ready(),.led_selftest());
    wire csd,rstd,ckd,cknd,cked,rasd,casd,wed,odtd;
    wire [14:0] addrd; wire [2:0] bad;
    assign #0.15 csd=csn; assign #0.15 rstd=rstn;
    assign #0.15 ckd=ck; assign #0.15 cknd=ckn; assign #0.15 cked=cke;
    assign #0.15 rasd=rasn; assign #0.15 casd=casn; assign #0.15 wed=wen;
    assign #0.15 odtd=odt; assign #0.15 addrd=addr; assign #0.15 bad=ba;
    ddr3_mem #(.DEBUG(0)) mem_core(.rst_n(rstd),.ck(ckd),.ck_n(cknd),.cs_n(csd),
        .ras_n(rasd),.cas_n(casd),.we_n(wed),.addr(addrd),.ba(bad),.odt(odtd),.cke(cked),
        .dq(dq),.dqs(dqs),.dqs_n(dqsn),.dm_tdqs(dm),.tdqs_n());
`else
    reg fast_clk=0,fast_resetn=0;
    assign clk=fast_clk; assign resetn=fast_resetn;
    always #(1.0e9/93750000.0/2.0) fast_clk=~fast_clk;
    initial begin repeat(10) @(negedge clk); fast_resetn=1; end
    wire [27:0] awaddr,araddr; wire awvalid,arvalid,awready,arready,wready,rvalid;
    wire [127:0] wdata,rdata; wire [15:0] wstrb;
    soc_top #(.ENABLE_DDR(1)) dut(.clk(clk),.resetn(resetn),.uart_rx(1'b1),.uart_tx(txd),
        .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .selftest_status(),.debug_wb_pc(),.debug_wb_rf_we(),.debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(),
        .ddr_init_done(1'b1),.ddr_axi_awaddr(awaddr),.ddr_axi_awuser_ap(),.ddr_axi_awuser_id(),
        .ddr_axi_awlen(),.ddr_axi_awready(awready),.ddr_axi_awvalid(awvalid),
        .ddr_axi_wdata(wdata),.ddr_axi_wstrb(wstrb),.ddr_axi_wready(wready),
        .ddr_axi_wusero_id(4'd1),.ddr_axi_wusero_last(wready),
        .ddr_axi_araddr(araddr),.ddr_axi_aruser_ap(),.ddr_axi_aruser_id(),.ddr_axi_arlen(),
        .ddr_axi_arready(arready),.ddr_axi_arvalid(arvalid),.ddr_axi_rdata(rdata),
        .ddr_axi_rid(4'd0),.ddr_axi_rlast(rvalid),.ddr_axi_rvalid(rvalid));
    coremark_ddr_model memory(.clk(clk),.resetn(resetn),.awaddr(awaddr),.awvalid(awvalid),
        .awready(awready),.wdata(wdata),.wstrb(wstrb),.wready(wready),
        .araddr(araddr),.arvalid(arvalid),.arready(arready),.rdata(rdata),.rvalid(rvalid));
`endif
    integer is_micro, n_windows, max_cycles, done_pc, timer_start_pc, timer_stop_pc;
    integer cycles=0, copied=0, words, finished_windows=0, phase=0, trace_file, timer_file, uart_file;
    integer sent=0,decoded=0,b,i;
    reg [31:0] markers[0:47], image[0:4095];
    reg [7:0] sent_bytes[0:8191], byte_value;
    reg [31:0] marker_id, start_tick=0;
    reg start_event,stop_event;
    reg saw_ddr=0,done=0,passed=0,timer_seeded=0;
    string out_dir,path;
    localparam real TBIT=1.0e9/115200.0;
    wire timer_read=`SOC.data_req_valid && `SOC.data_req_ready && !`SOC.data_req_write &&
                    `SOC.data_req_addr==32'h10000008;
    // Functional oracle only: exercise the existing 32-bit timer across wrap.
    always @(negedge clk) if(resetn && is_micro && $test$plusargs("TIMER_WRAP") &&
                            start_event && !timer_seeded) begin
        `SOC.u_simple_mmio.cycle_counter=32'hfffffffc;
        timer_seeded=1;
    end
    initial begin
        if(!$value$plusargs("OUT=%s",out_dir) || !$value$plusargs("DAT=%s",path) ||
           !$value$plusargs("MICRO=%d",is_micro) || !$value$plusargs("DONE=%h",done_pc))
            $fatal(1,"RESULT: FAIL missing required plusargs");
        $readmemh(path,image); words=image[4092];
        if(!$value$plusargs("MAX_CYCLES=%d",max_cycles)) max_cycles=60000000;
        for(i=0;i<48;i=i+1) markers[i]=0;
        if(is_micro) begin
            if(!$value$plusargs("MARKERS=%s",path) || !$value$plusargs("WINDOWS=%d",n_windows))
                $fatal(1,"missing micro markers");
            $readmemh(path,markers);
        end else begin
            n_windows=1;
            if(!$value$plusargs("START_FN=%h",timer_start_pc) || !$value$plusargs("STOP_FN=%h",timer_stop_pc))
                $fatal(1,"missing CoreMark timer symbols");
        end
        trace_file=$fopen({out_dir,"/retire_trace.csv"},"w");
        timer_file=$fopen({out_dir,"/timer.csv"},"w");
        uart_file=$fopen({out_dir,"/uart.txt"},"wb");
        $fdisplay(trace_file,"cycle,window,pc,write,rd,value");
        $fdisplay(timer_file,"window,start,stop,ticks");
    end
    always @* begin
        start_event=0; stop_event=0; marker_id=1;
        if(timer_read) begin
            if(is_micro) begin
                for(integer m=0;m<16;m=m+1) begin
                    if(m<n_windows && `CPU.id_ex_pc==markers[m*3+1]) begin
                        start_event=1; marker_id=markers[m*3];
                    end
                    if(m<n_windows && `CPU.id_ex_pc==markers[m*3+2]) begin
                        stop_event=1; marker_id=markers[m*3];
                    end
                end
            end else begin start_event=(phase==1); stop_event=(phase==2); end
        end
    end
    wire target_delivered=`CPU.inst_if_id_accept &&
        ((`CPU.inst_buffer_valid && `CPU.inst_buffer_pc==monitor.recovery_target) ||
         (!`CPU.inst_buffer_valid && `CPU.inst_response_good && `CPU.inst_pending_pc==monitor.recovery_target));
    perf_monitor monitor(.clk(clk),.resetn(resetn),.start_window(start_event),.stop_window(stop_event),
        .window_id(marker_id),.retire_pc(`CPU.mem_wb_pc),.branch_target(`CPU.redirect_pc),
        .normal_retire(`CPU.normal_retire),.mret_commit(`CPU.mret_commit),
        .control_redirect(`CPU.trap_redirect_req || `CPU.mret_redirect_req),
        .control_hold(`CPU.flow_state!=0 || `CPU.serial_candidate || `CPU.fault_inflight || `CPU.irq_candidate),
        .mem_stall(`CPU.data_pipeline_stall),.load_use(`CPU.if_id_valid && `CPU.load_use),
        .branch_redirect(`CPU.branch_redirect),.target_delivered(target_delivered),
        .fetch_starved(`CPU.fetch_valid && `CPU.inst_if_id_accept && !`CPU.inst_buffer_valid && !`CPU.inst_response_good),
        .i_req(`SOC.inst_req_valid),.i_ready(`SOC.inst_req_ready),.i_rsp(`SOC.inst_rsp_valid),
        .i_drop(`CPU.inst_pending_drop || `CPU.redirect_valid),
        .d_req(`SOC.data_req_valid),.d_ready(`SOC.data_req_ready),.d_rsp(`SOC.data_rsp_valid),
        .bridge_i_fire(`SOC.inst_ddr_req_valid && `SOC.inst_ddr_req_ready),
        .bridge_d_fire(`SOC.data_ddr_req_valid && `SOC.data_ddr_req_ready),
        .bridge_contention(`SOC.inst_ddr_req_valid && `SOC.data_ddr_req_valid),
        .ar_fire(`SOC.ddr_axi_arvalid && `SOC.ddr_axi_arready),
        .aw_fire(`SOC.ddr_axi_awvalid && `SOC.ddr_axi_awready),
        .r_beat(`SOC.ddr_axi_rvalid),.w_beat(`SOC.ddr_axi_wready),
        .bridge_state(`SOC.g_ddr.u_ddr_bridge.state));
    always @(posedge clk) if(resetn) begin
        cycles=cycles+1;
        if(cycles%1000000==0) $display("PROGRESS cycles=%0d pc=%h decoded=%0d",cycles,`CPU.mem_wb_pc,decoded);
        if(cycles>=max_cycles) $fatal(1,"RESULT: FAIL timeout pc=%h",`CPU.mem_wb_pc);
        if((`SOC.inst_rsp_valid && `SOC.inst_rsp_error) || (`SOC.data_rsp_valid && `SOC.data_rsp_error))
            $fatal(1,"RESULT: FAIL bus access fault");
        if(`CPU.irq_take || (`CPU.sync_trap_event && (is_micro || `CPU.wb_trap_cause!=11)))
            $fatal(1,"RESULT: FAIL unexpected trap cause=%d",`CPU.wb_trap_cause);
        if(!saw_ddr && `SOC.data_write && `SOC.data_req_addr>=32'h40000000) begin
            if(copied>=words || `SOC.data_req_addr!=32'h40000000+copied*4 ||
               `SOC.data_req_wdata!==image[copied] || `SOC.data_req_wstrb!=15)
                $fatal(1,"RESULT: FAIL CPU copy-loader payload/order");
            copied=copied+1;
            if(copied%512==0) $display("COPY progress words=%0d/%0d time=%t",copied,words,$time);
        end
        if(!saw_ddr && `SOC.inst_req_valid && `SOC.inst_req_ready && `SOC.inst_req_addr==32'h40000000) begin
`ifdef PERF_DIRECT
            if(!dut.setup_done) $fatal(1,"RESULT: FAIL CPU started before full DDR readback");
            copied=words;
`else
            if(copied!=words) $fatal(1,"RESULT: FAIL incomplete CPU copy");
`endif
            saw_ddr=1;
`ifdef PERF_DIRECT
            $display("CHECK: CPU entered DDR after physical payload readback (%0d words)",words);
`else
            $display("CHECK: CPU copied exact BIN (%0d words) through DDR bridge",copied);
`endif
        end
        if(start_event) start_tick=`SOC.u_simple_mmio.cycle_counter;
        if(stop_event) begin
            $fdisplay(timer_file,"%0d,%0d,%0d,%0d",marker_id,start_tick,`SOC.u_simple_mmio.cycle_counter,
                      32'(`SOC.u_simple_mmio.cycle_counter-start_tick));
            $fflush(timer_file); finished_windows=finished_windows+1;
        end
        if(`CPU.normal_retire || `CPU.mret_commit) begin
            if(!is_micro && `CPU.mem_wb_pc==timer_start_pc) phase<=1;
            if(!is_micro && `CPU.mem_wb_pc==timer_stop_pc) phase<=2;
            if(is_micro && saw_ddr)
                $fdisplay(trace_file,"%0d,%0d,%08h,%0d,%0d,%08h",cycles,
                    (start_event || (monitor.running && !stop_event)) ? (start_event?marker_id:monitor.active_id):0,
                    `CPU.mem_wb_pc,`SOC.debug_wb_rf_we==15,`SOC.debug_wb_rf_wnum,`SOC.debug_wb_rf_wdata);
            if(`CPU.mem_wb_pc==done_pc) done=1;
        end
        if(!is_micro && timer_read && phase!=0) phase<=0;
        if(`SOC.data_write && `SOC.data_req_addr==32'h10000010) begin
            if(`SOC.data_req_wdata==3) $fatal(1,"RESULT: FAIL micro checksum");
            if(`SOC.data_req_wdata==2) passed=1;
        end
        if(`SOC.u_uart_mmio.tx_send) begin
            if(sent>=8192) $fatal(1,"UART capture overflow");
            sent_bytes[sent]=`SOC.u_uart_mmio.req_wdata[7:0]; sent=sent+1;
        end
        if(done && (is_micro || (sent==decoded && !`SOC.u_uart_mmio.tx_busy))) begin
            if(finished_windows!=n_windows || (is_micro && !passed)) $fatal(1,"RESULT: FAIL missing windows/PASS");
            $fflush(trace_file); $fflush(uart_file);
            $display("RESULT: PASS cpu_performance windows=%0d cycles=%0d",finished_windows,cycles); $finish;
        end
    end
    initial forever begin
        @(negedge txd); if(resetn) begin
            #(TBIT/2); if(txd!==0) $fatal(1,"UART start");
            for(b=0;b<8;b=b+1) begin #(TBIT); byte_value[b]=txd; end
            #(TBIT); if(txd!==1 || decoded>=sent || byte_value!==sent_bytes[decoded]) $fatal(1,"UART pin byte mismatch");
            $fwrite(uart_file,"%c",byte_value); $fflush(uart_file); decoded=decoded+1;
        end
    end
    initial begin #1000000000; $fatal(1,"RESULT: FAIL simulation time watchdog"); end
endmodule
`undef SOC
`undef CPU
