`timescale 1ns/1ps
// Preprocess key group, real CPU + real soc_top/CPU/caches/interconnect/bridge.
// The Camera side is an explicitly marked ABI2 ownership boundary model
// (cam_boundary.sv); DVP capture, PHY and board_top are NOT exercised here.
module tb_pp_soc;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    reg refclk=0,resetn=0,uart_rx=1;always #4 refclk=~refclk;
    wire clk;
    // ---------------- native DDR ----------------
    wire [27:0] n_awaddr,n_araddr;
    wire [3:0] n_awid,n_awlen,n_arid,n_arlen,n_rid,n_wid;
    wire n_awap,n_awvalid,n_awready,n_wready,n_wlast,n_arap,n_arvalid,n_arready,n_rlast,n_rvalid;
    wire [255:0] n_wdata,n_rdata;
    wire [31:0] n_wstrb;
    ddr3 u_ddr3(.ref_clk(refclk),.resetn(resetn),.core_clk(clk),.pll_lock(),.phy_pll_lock(),.gpll_lock(),
        .rst_gpll_lock(),.ddrphy_cpd_lock(),.ddr_init_done(),
        .axi_awaddr(n_awaddr),.axi_awuser_ap(n_awap),.axi_awuser_id(n_awid),.axi_awlen(n_awlen),
        .axi_awready(n_awready),.axi_awvalid(n_awvalid),
        .axi_wdata(n_wdata),.axi_wstrb(n_wstrb),.axi_wready(n_wready),.axi_wusero_id(n_wid),.axi_wusero_last(n_wlast),
        .axi_araddr(n_araddr),.axi_aruser_ap(n_arap),.axi_aruser_id(n_arid),.axi_arlen(n_arlen),
        .axi_arready(n_arready),.axi_arvalid(n_arvalid),
        .axi_rdata(n_rdata),.axi_rid(n_rid),.axi_rlast(n_rlast),.axi_rvalid(n_rvalid),
        .apb_clk(1'b0),.apb_rst_n(1'b0),.apb_sel(1'b0),.apb_enable(1'b0),.apb_addr(8'b0),.apb_write(1'b0),.apb_wdata(16'b0));
    // ---------------- soc_top ----------------
    wire pp_req_valid,pp_req_write,pp_req_ready,pp_rsp_valid,pp_rsp_error;
    wire [1:0] pp_req_size;
    wire [31:0] pp_req_addr,pp_req_wdata,pp_rsp_rdata;
    wire [3:0] pp_req_wstrb;
    wire pp_busy,pp_done,pp_read_error;
    wire [1:0] pp_source_hold;
    wire em_req_valid,em_req_write,em_req_ready,em_rsp_valid,em_rsp_error;
    wire [1:0] em_req_size,em_cpu_owned;
    wire [31:0] em_req_addr,em_req_wdata,em_rsp_rdata,em_seq0,em_seq1;
    wire [3:0] em_req_wstrb;
    wire em_dual,em_geom;
    wire [27:0] cpu_awaddr,cpu_araddr;
    wire [3:0] cpu_awid,cpu_awlen,cpu_arid,cpu_arlen,cpu_rid;
    wire cpu_awap,cpu_awvalid,cpu_awready,cpu_wready,cpu_arap,cpu_arvalid,cpu_arready,cpu_rvalid,cpu_rlast;
    wire [255:0] cpu_wdata,cpu_rdata;
    wire [31:0] cpu_wstrb;
    wire [1:0] selftest;
    wire [31:0] dbg_pc,dbg_inst;
    soc_top #(.ENABLE_CAMERA(1),.ENABLE_PREPROCESS(1),.RESET_PC(32'h40000000),.ENABLE_DDR(1),
              .DDR_BASE(32'h40000000),.DDR_ADDR_MASK(32'hc0000000),.DDR_MEM_DQ_WIDTH(32),
              .UART_CLK_HZ(93750000)) u_soc(
        .pp_req_valid(pp_req_valid),.pp_req_write(pp_req_write),.pp_req_size(pp_req_size),
        .pp_req_addr(pp_req_addr),.pp_req_wdata(pp_req_wdata),.pp_req_wstrb(pp_req_wstrb),
        .pp_req_ready(pp_req_ready),.pp_rsp_valid(pp_rsp_valid),.pp_rsp_error(pp_rsp_error),.pp_rsp_rdata(pp_rsp_rdata),
        .preprocess_busy(pp_busy),.preprocess_done(pp_done),
        .cam_req_valid(em_req_valid),.cam_req_write(em_req_write),.cam_req_size(em_req_size),
        .cam_req_addr(em_req_addr),.cam_req_wdata(em_req_wdata),.cam_req_wstrb(em_req_wstrb),
        .cam_req_ready(em_req_ready),.cam_rsp_valid(em_rsp_valid),.cam_rsp_error(em_rsp_error),.cam_rsp_rdata(em_rsp_rdata),
        .camera_busy(1'b0),.camera_dual_mode(em_dual),.camera_cpu_owned(em_cpu_owned),
        .clk(clk),.resetn(resetn),.irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .debug_wb_pc(dbg_pc),.debug_wb_rf_we(),.debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(dbg_inst),
        .ddr_init_done(resetn),
        .ddr_axi_awaddr(cpu_awaddr),.ddr_axi_awuser_ap(cpu_awap),.ddr_axi_awuser_id(cpu_awid),.ddr_axi_awlen(cpu_awlen),
        .ddr_axi_awready(cpu_awready),.ddr_axi_awvalid(cpu_awvalid),
        .ddr_axi_wdata(cpu_wdata),.ddr_axi_wstrb(cpu_wstrb),.ddr_axi_wready(cpu_wready),
        .ddr_axi_wusero_id(n_wid),.ddr_axi_wusero_last(n_wlast),
        .ddr_axi_araddr(cpu_araddr),.ddr_axi_aruser_ap(cpu_arap),.ddr_axi_aruser_id(cpu_arid),.ddr_axi_arlen(cpu_arlen),
        .ddr_axi_arready(cpu_arready),.ddr_axi_arvalid(cpu_arvalid),
        .ddr_axi_rdata(cpu_rdata),.ddr_axi_rid(cpu_rid),.ddr_axi_rlast(cpu_rlast),.ddr_axi_rvalid(cpu_rvalid),
        .selftest_status(selftest),.uart_rx(uart_rx),.uart_tx());
    defparam u_soc.INST_ROM_BASE=0,u_soc.DATA_RAM_BASE=0;
    // ---------------- camera boundary + preprocess ----------------
    cam_boundary u_cam(.clk(clk),.resetn(resetn),
        .req_valid(em_req_valid),.req_write(em_req_write),.req_size(em_req_size),.req_addr(em_req_addr),
        .req_wdata(em_req_wdata),.req_wstrb(em_req_wstrb),.req_ready(em_req_ready),
        .rsp_valid(em_rsp_valid),.rsp_error(em_rsp_error),.rsp_rdata(em_rsp_rdata),
        .dual_mode(em_dual),.cpu_owned(em_cpu_owned),.external_hold(pp_source_hold),
        .source_seq0(em_seq0),.source_seq1(em_seq1),.source_geometry_ok(em_geom));
    wire [27:0] pp_araddr,pp_awaddr;
    wire pp_arvalid,pp_awvalid,pp_arready,pp_awready,pp_wready,pp_rvalid;
    wire [255:0] pp_wdata;
    preprocess_mmio u_pp(.clk(clk),.resetn(resetn),
        .req_valid(pp_req_valid),.req_write(pp_req_write),.req_size(pp_req_size),.req_addr(pp_req_addr),
        .req_wdata(pp_req_wdata),.req_wstrb(pp_req_wstrb),.req_ready(pp_req_ready),
        .rsp_valid(pp_rsp_valid),.rsp_error(pp_rsp_error),.rsp_rdata(pp_rsp_rdata),
        .camera_dual_mode(em_dual),.source_geometry_ok(em_geom),.cpu_owned(em_cpu_owned),
        .source_seq0(em_seq0),.source_seq1(em_seq1),
        .busy(pp_busy),.done(pp_done),.source_hold(pp_source_hold),
        .araddr(pp_araddr),.arvalid(pp_arvalid),.arready(pp_arready),
        .rvalid(pp_rvalid),.rlast(n_rlast),.rid(n_rid),.rdata(n_rdata),
        .awaddr(pp_awaddr),.awvalid(pp_awvalid),.awready(pp_awready),.wdata(pp_wdata),.wready(pp_wready),
        .read_protocol_error(pp_read_error));
    // ---------------- arbiters ----------------
    wire [27:0] i_awaddr;wire [3:0] i_awid,i_awlen;wire i_awap,i_awvalid,i_awready,i_wready;
    wire [255:0] i_wdata;wire [31:0] i_wstrb;
    reg cam_awvalid=0;
    reg [27:0] cam_awaddr=28'h480000;
    reg [255:0] cam_wdata=0;
    wire cam_awready,cam_wready;
    camera_ddr_write_arbiter #(.CAM_AW_ID(4'd2)) u_win(.clk(clk),.resetn(resetn),
        .cpu_awaddr(cpu_awaddr),.cpu_awlen(cpu_awlen),.cpu_awid(cpu_awid),.cpu_awap(cpu_awap),.cpu_awvalid(cpu_awvalid),
        .cpu_wdata(cpu_wdata),.cpu_wstrb(cpu_wstrb),.cpu_awready(cpu_awready),.cpu_wready(cpu_wready),
        .cam_awaddr(cam_awaddr),.cam_awvalid(cam_awvalid),.cam_wdata(cam_wdata),
        .cam_awready(cam_awready),.cam_wready(cam_wready),
        .awaddr(i_awaddr),.awlen(i_awlen),.awid(i_awid),.awap(i_awap),.awvalid(i_awvalid),.awready(i_awready),
        .wdata(i_wdata),.wstrb(i_wstrb),.wready(i_wready),.busy());
    camera_ddr_write_arbiter #(.CAM_AW_ID(4'd3)) u_wout(.clk(clk),.resetn(resetn),
        .cpu_awaddr(i_awaddr),.cpu_awlen(i_awlen),.cpu_awid(i_awid),.cpu_awap(i_awap),.cpu_awvalid(i_awvalid),
        .cpu_wdata(i_wdata),.cpu_wstrb(i_wstrb),.cpu_awready(i_awready),.cpu_wready(i_wready),
        .cam_awaddr(pp_awaddr),.cam_awvalid(pp_awvalid),.cam_wdata(pp_wdata),
        .cam_awready(pp_awready),.cam_wready(pp_wready),
        .awaddr(n_awaddr),.awlen(n_awlen),.awid(n_awid),.awap(n_awap),.awvalid(n_awvalid),.awready(n_awready),
        .wdata(n_wdata),.wstrb(n_wstrb),.wready(n_wready),.busy());
    preprocess_ddr_read_arbiter u_rd(.clk(clk),.resetn(resetn),
        .cpu_addr(cpu_araddr),.cpu_len(cpu_arlen),.cpu_id(cpu_arid),.cpu_ap(cpu_arap),.cpu_valid(cpu_arvalid),
        .cpu_ready(cpu_arready),.cpu_rvalid(cpu_rvalid),
        .pp_addr(pp_araddr),.pp_valid(pp_arvalid),.pp_ready(pp_arready),.pp_rvalid(pp_rvalid),
        .araddr(n_araddr),.arlen(n_arlen),.arid(n_arid),.arap(n_arap),.arvalid(n_arvalid),
        .arready(n_arready),.rvalid(n_rvalid),.rlast(n_rlast),.rid(n_rid),.protocol_error(pp_read_error));
    // ---------------- logging/observation ----------------
    integer fd,cycle=0,retired=0,loads=0,jobs=0,stores=0,traps=0;
    integer pp_ar_n=0,pp_aw_n=0,cam_w_n=0,cam_stim=0;
    integer same_aw_w=0,sep_aw_w=0,aw_contend=0,ar_mix=0,last_ar=-1,interleaved=0;
    integer load_by_job[1:4],phase_job=-1,credits=0;
    integer pp_ar_cycle=-1,pp_r_cycle=-1,cam_between=0,last_crc_report=0;
    reg [31:0] pend_addr=0;reg pend_rd=0,pend=0;
    string path;
    task automatic cam_beat;
        reg aw_done,w_done;
        begin
            aw_done=0;w_done=0;
            @(negedge clk);
            cam_awaddr=28'h480000+((cam_stim%512)<<3);
            cam_wdata=u_ddr3.reference_word(cam_awaddr);
            cam_awvalid=1;
            while(!aw_done) begin
                @(negedge clk);
                if(cam_awready) begin aw_done=1;if(cam_wready)w_done=1;end
            end
            @(negedge clk);      // let the accepting edge pass before releasing AW
            cam_awvalid=0;
            while(!w_done) begin
                @(negedge clk);
                if(cam_wready)w_done=1;
            end
            @(negedge clk);      // let the consuming edge pass before changing W data
            cam_stim=cam_stim+1;
        end
    endtask
    initial begin
        if(!$value$plusargs("CPU=%s",path))$fatal(1,"RESULT: FAIL CPU log path");
        fd=$fopen(path,"w");if(!fd)$fatal(1,"RESULT: FAIL CPU log open");
        for(integer q=1;q<=3;q=q+1)load_by_job[q]=0;
        u_ddr3.src_kind[0]=1;u_ddr3.src_param[0]=1;
        u_ddr3.src_kind[1]=1;u_ddr3.src_param[1]=2;
        repeat(12)@(negedge refclk);resetn=1;
        fork
            begin
                repeat(600)@(negedge clk);
                for(integer n=0;n<260;n=n+1)cam_beat;
            end
        join_none
        wait(selftest==2 || selftest==3);
        repeat(20)@(negedge clk);
        if(selftest!=2)$fatal(1,"RESULT: FAIL CPU software diagnostic status=%0d",selftest);
        if(traps!=0)$fatal(1,"RESULT: FAIL real CPU trap count %0d",traps);
        if(jobs!=3)$fatal(1,"RESULT: FAIL publication count %0d",jobs);
        if(loads<3*6912)$fatal(1,"RESULT: FAIL output words read %0d",loads);
        if(interleaved==0)$fatal(1,"RESULT: FAIL no camera W between PP AR and R");
        if(aw_contend==0)$fatal(1,"RESULT: FAIL no AW contention");
        if(same_aw_w==0||sep_aw_w==0)$fatal(1,"RESULT: FAIL AW/W same/separate coverage");
        if(ar_mix==0)$fatal(1,"RESULT: FAIL no CPU/PP AR interleave");
        if(cam_w_n==0)$fatal(1,"RESULT: FAIL synthetic camera host never served");
        $fdisplay(fd,"COVER %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d %0d",
            jobs,loads,stores,interleaved,aw_contend,same_aw_w,sep_aw_w,ar_mix,cam_w_n,pp_ar_n,pp_aw_n);
        $fdisplay(fd,"LOADSJOB %0d %0d %0d",load_by_job[1],load_by_job[2],load_by_job[3]);
        $fdisplay(fd,"DDR %0d %0d %0d %0d",u_ddr3.same_cycle_ar_r,u_ddr3.immediate_r,u_ddr3.pp_reads,u_ddr3.pp_writes);
        $display("RESULT: PASS PP_SMALL_REAL_CPU");
        $fflush(fd);$fclose(fd);$finish;
    end
    always @(posedge clk) if(resetn) begin
        cycle=cycle+1;
        if(cycle%2048==0)$fflush(fd);
        if(u_soc.u_cpu.normal_retire && retired<16) begin
            $fdisplay(fd,"RETIRE %0d %08h %08h",cycle,dbg_pc,dbg_inst);
            if(retired==0 && (dbg_pc!=32'h40000000 || dbg_inst!=32'h30047073))
                $fatal(1,"RESULT: FAIL sealed CPU entry");
            retired=retired+1;
        end
        if(u_soc.u_cpu.sync_trap_event) begin
            traps=traps+1;
            $fdisplay(fd,"TRAP %0d %08h %08h %0d %08h",cycle,dbg_pc,dbg_inst,
                u_soc.u_cpu.wb_trap_cause,u_soc.u_cpu.wb_trap_tval);
            $fflush(fd);$fatal(1,"RESULT: FAIL real CPU trap");
        end
        if(u_soc.data_req_valid && u_soc.data_req_ready) begin
            if(u_soc.data_req_write && u_soc.data_req_addr==32'h10000000) begin
                if(u_soc.data_req_wdata[31:28]==4'hc) begin
                    phase_job=(u_soc.data_req_wdata>>4)&15;
                    $fdisplay(fd,"PHASE %0d %0d %0d",cycle,phase_job,u_soc.data_req_wdata[3:0]);
                    if(phase_job==0) begin
                        u_ddr3.src_kind[0]=1;u_ddr3.src_param[0]=1;
                        u_cam.publish(0,1);u_cam.publish(1,2);
                    end else if(phase_job==2) begin
                        u_ddr3.src_kind[0]=1;u_ddr3.src_param[0]=3;
                        u_cam.publish(0,3);
                    end
                end else if(u_soc.data_req_wdata[31:28]==4'hd) begin
                    jobs=jobs+1;
                    $fdisplay(fd,"PUB %0d %0d %0d %08h",cycle,(u_soc.data_req_wdata>>16)&1,
                        u_soc.data_req_wdata[15:0],last_crc_report);
                end else if(u_soc.data_req_wdata[31:28]==4'hb) begin
                    stores=u_soc.data_req_wdata&32'hffffff;
                    $fdisplay(fd,"STORES %0d %0d",cycle,stores);
                end else begin
                    last_crc_report=u_soc.data_req_wdata;
                    $fdisplay(fd,"REPORT %0d %08h",cycle,u_soc.data_req_wdata);
                end
            end else if(u_soc.data_req_write && u_soc.data_req_addr==32'h4001c000) begin
                stores=stores+1;
            end
            if(!u_soc.data_req_write) begin pend_addr<=u_soc.data_req_addr;pend_rd<=1;end
            else pend_rd<=0;
        end
        if(u_soc.data_rsp_valid && pend_rd && pend_addr>=32'h42000000 && pend_addr<32'h42008000) begin
            if(u_soc.data_rsp_error)$fatal(1,"RESULT: FAIL output read error %08h",pend_addr);
            $fdisplay(fd,"LOAD %0d %08h %08h",cycle,pend_addr,u_soc.data_rsp_rdata);
            loads=loads+1;
            if(phase_job>=0 && phase_job<=2)load_by_job[phase_job+1]=load_by_job[phase_job+1]+1;
        end
        if(n_arvalid&&n_arready)begin
            if(n_arid==4'd3)pp_ar_n=pp_ar_n+1;
            if(last_ar>=0 && ((n_arid==4'd3)!==(last_ar==1)))ar_mix=ar_mix+1;
            last_ar=(n_arid==4'd3)?1:0;
        end
        if(pp_arvalid&&pp_arready)pp_ar_cycle=cycle;
        if(pp_rvalid)begin
            pp_r_cycle=cycle;
            if(cam_between>0)interleaved=interleaved+1;
            cam_between=0;
        end
        if(n_awvalid&&n_awready)begin
            if(n_wready)same_aw_w=same_aw_w+1;else sep_aw_w=sep_aw_w+1;
            if(n_awid==4'd2)begin cam_w_n=cam_w_n+1;cam_between=cam_between+1;end
        end
        if(pp_awvalid&&pp_awready)pp_aw_n=pp_aw_n+1;
        if(u_win.cpu_awvalid&&u_win.cam_awvalid)aw_contend=aw_contend+1;
        if(u_wout.cpu_awvalid&&u_wout.cam_awvalid)aw_contend=aw_contend+1;
    end
    initial begin #40000000;$fatal(1,"RESULT: FAIL soc deadline");end
endmodule
