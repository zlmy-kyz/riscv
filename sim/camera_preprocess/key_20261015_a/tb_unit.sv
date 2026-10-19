`timescale 1ns/1ps
// Preprocess key group, direct unit level: real preprocess_mmio, both real write
// arbiter levels, the real read arbiter, the real decode/permission logic, a
// native DDR model, and a real small-geometry camera_mmio for the external-hold
// contract. No force/deposit into the design.
module tb_pp_unit;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    reg refclk=0,resetn=0;always #4 refclk=~refclk;
    wire clk;
    // ---------------- native DDR port ----------------
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
    pp_aperture u_perm();
    // ---------------- preprocess DUT ----------------
    reg pp_req_valid=0,pp_req_write=0;
    reg [1:0] pp_req_size=2;
    reg [31:0] pp_req_addr=0,pp_req_wdata=0;
    reg [3:0] pp_req_wstrb=15;
    wire pp_req_ready,pp_rsp_valid,pp_rsp_error;
    wire [31:0] pp_rsp_rdata;
    wire pp_busy,pp_done,pp_read_error;
    wire [1:0] pp_source_hold;
    reg cam_dual=0,cam_geom=1;
    reg [1:0] cam_owned=0;
    reg [31:0] cam_seq0=0,cam_seq1=0;
    wire [27:0] pp_araddr,pp_awaddr;
    wire pp_arvalid,pp_awvalid,pp_arready,pp_awready,pp_wready,pp_rvalid;
    wire [255:0] pp_wdata;
    preprocess_mmio u_pp(.clk(clk),.resetn(resetn),
        .req_valid(pp_req_valid),.req_write(pp_req_write),.req_size(pp_req_size),.req_addr(pp_req_addr),
        .req_wdata(pp_req_wdata),.req_wstrb(pp_req_wstrb),.req_ready(pp_req_ready),
        .rsp_valid(pp_rsp_valid),.rsp_error(pp_rsp_error),.rsp_rdata(pp_rsp_rdata),
        .camera_dual_mode(cam_dual),.source_geometry_ok(cam_geom),.cpu_owned(cam_owned),
        .source_seq0(cam_seq0),.source_seq1(cam_seq1),
        .busy(pp_busy),.done(pp_done),.source_hold(pp_source_hold),
        .araddr(pp_araddr),.arvalid(pp_arvalid),.arready(pp_arready),
        .rvalid(pp_rvalid),.rlast(n_rlast),.rid(n_rid),.rdata(n_rdata),
        .awaddr(pp_awaddr),.awvalid(pp_awvalid),.awready(pp_awready),.wdata(pp_wdata),.wready(pp_wready),
        .read_protocol_error(pp_read_error));
    // ---------------- real small-geometry camera (external hold contract) ----------------
    wire hpclk,hvs,hhref;wire [7:0] hdin;tri1 hscl,hsda;
    wire hscl_low,hsda_low,hsensor_resetn;
    camera_dvp hdvp(.pclk(hpclk),.vsync(hvs),.href(hhref),.din(hdin));
    integer hsw,hsr;
    camera_sensor hsensor(.resetn(resetn),.scl(hscl),.sda(hsda),.injection(32'b0),.writes(hsw),.reads(hsr));
    assign hscl=hscl_low?1'b0:1'bz;
    assign hsda=hsda_low?1'b0:1'bz;
    reg [1:0] hold_ext=0;
    wire h_req_ready,h_rsp_valid,h_rsp_error,h_busy,h_dual,h_geom;
    wire [1:0] h_req_size,h_owned;
    wire [31:0] h_req_addr,h_req_wdata,h_rsp_rdata,h_seq0,h_seq1;
    wire [3:0] h_req_wstrb;
    wire h_dma_awvalid,h_dma_awready,h_dma_wready;
    wire [27:0] h_dma_awaddr;wire [255:0] h_dma_wdata;
    reg h_req_valid=0,h_req_write=0;
    reg [31:0] h_req_addr_r=0,h_req_wdata_r=0;
    reg [1:0] h_req_size_r=2;
    reg [3:0] h_req_wstrb_r=15;
    camera_mmio #(.CLK_HZ(100000),.WIDTH(64),.HEIGHT(128),.DROP_FRAMES(10),.EXTERNAL_HOLD_ENABLE(1)) u_hold(
        .clk(clk),.resetn(resetn),
        .req_valid(h_req_valid),.req_write(h_req_write),.req_size(h_req_size_r),.req_addr(h_req_addr_r),
        .req_wdata(h_req_wdata_r),.req_wstrb(h_req_wstrb_r),.req_ready(h_req_ready),
        .rsp_valid(h_rsp_valid),.rsp_error(h_rsp_error),.rsp_rdata(h_rsp_rdata),
        .busy(h_busy),.dual_mode(h_dual),.cpu_owned(h_owned),.external_hold(hold_ext),
        .source_seq0(h_seq0),.source_seq1(h_seq1),.source_geometry_ok(h_geom),
        .pclk(hpclk),.vsync(hvs),.href(hhref),.din(hdin),
        .scl_in(hscl),.sda_in(hsda),.scl_low(hscl_low),.sda_low(hsda_low),.sensor_resetn(hsensor_resetn),
        .dma_awvalid(h_dma_awvalid),.dma_awaddr(h_dma_awaddr),.dma_wdata(h_dma_wdata),
        .dma_awready(h_dma_awready),.dma_wready(h_dma_wready));
    defparam u_hold.u_config.CLK_HZ=1600000;
    // ---------------- read arbiter + CPU read host ----------------
    reg cpu_rd_valid=0,cpu_rd_ap=0,cpu_rd_en=1;
    reg [27:0] cpu_rd_addr=0;
    reg [3:0] cpu_rd_len=0,cpu_rd_id=1;
    wire cpu_rd_ready,cpu_rd_rvalid;
    preprocess_ddr_read_arbiter u_rd(.clk(clk),.resetn(resetn),
        .cpu_addr(cpu_rd_addr),.cpu_len(cpu_rd_len),.cpu_id(cpu_rd_id),.cpu_ap(cpu_rd_ap),.cpu_valid(cpu_rd_valid),
        .cpu_ready(cpu_rd_ready),.cpu_rvalid(cpu_rd_rvalid),
        .pp_addr(pp_araddr),.pp_valid(pp_arvalid),.pp_ready(pp_arready),.pp_rvalid(pp_rvalid),
        .araddr(n_araddr),.arlen(n_arlen),.arid(n_arid),.arap(n_arap),.arvalid(n_arvalid),
        .arready(n_arready),.rvalid(n_rvalid),.rlast(n_rlast),.rid(n_rid),.protocol_error(pp_read_error));
    // ---------------- two-level write arbitration ----------------
    wire [27:0] i_awaddr;wire [3:0] i_awid,i_awlen;wire i_awap,i_awvalid,i_awready,i_wready;
    wire [255:0] i_wdata;wire [31:0] i_wstrb;
    reg cpu_awvalid=0,cpu_wr_en=1;
    reg [27:0] cpu_awaddr=28'h7000;
    reg [255:0] cpu_wdata={8{32'hc0de0000}};
    wire cpu_awready,cpu_wready;
    reg hold_mode=0;
    reg syn_awvalid=0;
    reg [27:0] syn_awaddr=28'h500000;
    reg [255:0] syn_wdata={8{32'h5a5a5a5a}};
    integer cam_wst=0;
    wire cam_awvalid_d=hold_mode?h_dma_awvalid:syn_awvalid;
    wire [27:0] cam_awaddr_d=hold_mode?h_dma_awaddr:syn_awaddr;
    wire [255:0] cam_wdata_d=hold_mode?h_dma_wdata:syn_wdata;
    wire cam_awready,cam_wready;
    assign h_dma_awready=cam_awready;
    assign h_dma_wready=cam_wready;
    camera_ddr_write_arbiter #(.CAM_AW_ID(4'd2)) u_win(.clk(clk),.resetn(resetn),
        .cpu_awaddr(cpu_awaddr),.cpu_awlen(4'd0),.cpu_awid(4'd1),.cpu_awap(1'b0),.cpu_awvalid(cpu_awvalid),
        .cpu_wdata(cpu_wdata),.cpu_wstrb(32'hffffffff),.cpu_awready(cpu_awready),.cpu_wready(cpu_wready),
        .cam_awaddr(cam_awaddr_d),.cam_awvalid(cam_awvalid_d),.cam_wdata(cam_wdata_d),
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
    // ---------------- logging ----------------
    integer fd,cycle=0;
    string path;
    integer same_aw_w=0,sep_aw_w=0,aw_contend=0,ar_mix=0,last_ar_owner=-1;
    integer cpu_ar_n=0,pp_ar_n=0,cpu_beats=0,cpu_wr_n=0,cam_wr_n=0,pp_wr_n=0;
    reg [31:0] m_rdata;reg m_err;
    task automatic mmio(input integer wr,input [31:0] addr,input [31:0] data,input [1:0] size,input [3:0] strb);
        begin
            @(negedge clk);pp_req_valid=1;pp_req_write=wr;pp_req_addr=addr;pp_req_wdata=data;pp_req_size=size;pp_req_wstrb=strb;
            while(!pp_req_ready)@(negedge clk);
            @(posedge clk);
            @(negedge clk);pp_req_valid=0;
            m_err=pp_rsp_error;m_rdata=pp_rsp_rdata;
            $fdisplay(fd,"MMIO %0d %08h %08h %0d %0h %0d %08h",cycle,addr,data,size,strb,m_err,m_rdata);
            repeat(2)@(negedge clk);
        end
    endtask
    reg [31:0] hm_rdata;reg hm_err;
    task automatic mmio_hold(input integer wr,input [31:0] addr,input [31:0] data,input [1:0] size,input [3:0] strb);
        begin
            @(negedge clk);h_req_valid=1;h_req_write=wr;h_req_addr_r=addr;h_req_wdata_r=data;h_req_size_r=size;h_req_wstrb_r=strb;
            while(!h_req_ready)@(negedge clk);
            @(posedge clk);
            @(negedge clk);h_req_valid=0;
            hm_err=h_rsp_error;hm_rdata=h_rsp_rdata;
            $fdisplay(fd,"HOLD_MMIO %0d %08h %08h %0d %0d %08h",cycle,addr,data,hm_err,hm_rdata[3:0],hm_rdata);
            repeat(2)@(negedge clk);
        end
    endtask
    // ---- CPU read host: deterministic len0/1/7/15 with legal ids/ap ----
    integer cr_state=0,cr_beats=0,cr_len=0,cr_id=1,cr_seq=0;
    always @(posedge clk) if(resetn) begin
        case(cr_state)
            0: if(cpu_rd_en && !pp_read_error) begin
                   cr_seq=cr_seq+1;
                   case(cr_seq%4)
                       0:begin cr_len=0;cr_id=1;end
                       1:begin cr_len=1;cr_id=1;end
                       2:begin cr_len=7;cr_id=0;end
                       default:begin cr_len=15;cr_id=1;end
                   endcase
                   cpu_rd_addr<=28'h1000+((cr_seq[7:0])<<3);cpu_rd_len<=cr_len[3:0];cpu_rd_id<=cr_id[3:0];
                   cpu_rd_valid<=1;cr_state<=1;
               end
            1: if(cpu_rd_ready) begin
                   cpu_rd_valid<=0;cr_beats=0;cpu_ar_n=cpu_ar_n+1;
                   $fdisplay(fd,"CPU_AR %0d %07h %0d %0d",cycle,cpu_rd_addr,cpu_rd_len,cpu_rd_id);
                   cr_state<=2;
               end
            2: if(cpu_rd_rvalid) begin
                   if(n_rid!==cpu_rd_id)$fatal(1,"RESULT: FAIL CPU got foreign R id %0d",n_rid);
                   cr_beats=cr_beats+1;cpu_beats=cpu_beats+1;
                   if(cr_beats==cr_len+1)begin $fdisplay(fd,"CPU_R %0d %0d",cycle,cr_beats);cr_state<=0;end
               end
            default: cr_state<=0;
        endcase
    end
    // ---- CPU / synthetic camera write hosts ----
    reg [1:0] cpu_wst=0;
    always @(posedge clk) if(resetn) begin
        if(cpu_wr_en) case(cpu_wst)
            0:begin cpu_awvalid<=1;cpu_awaddr<=28'h7000;cpu_wdata<={224'b0,32'hc0de0000+cpu_wr_n[31:0]};cpu_wst<=1;end
            1:if(cpu_awready)begin cpu_awvalid<=0;cpu_wst<=cpu_wready?1'b0:1'b1+1'b1;end
            2:if(cpu_wready)cpu_wst<=0;
            default:cpu_wst<=0;
        endcase
        if(!hold_mode) case(cam_wst)
            0:begin syn_awvalid<=1;syn_awaddr<=28'h500000+(cam_wr_n[6:0]<<3);syn_wdata<={8{32'h5a5a5a5a}};cam_wst<=1;end
            1:if(cam_awready)begin syn_awvalid<=0;cam_wst<=cam_wready?1'b0:1'b1+1'b1;end
            2:if(cam_wready)cam_wst<=0;
            default:cam_wst<=0;
        endcase
        if(n_arvalid&&n_arready)begin
            if(n_arid==4'd3)pp_ar_n=pp_ar_n+1;
            if(last_ar_owner>=0 && ((n_arid==4'd3)!==(last_ar_owner==1)))ar_mix=ar_mix+1;
            last_ar_owner=(n_arid==4'd3)?1:0;
        end
        if(n_awvalid&&n_awready)begin
            if(n_wready)same_aw_w=same_aw_w+1;else sep_aw_w=sep_aw_w+1;
            if(n_awid==4'd3)pp_wr_n=pp_wr_n+1;else if(n_awid==4'd2)cam_wr_n=cam_wr_n+1;else cpu_wr_n=cpu_wr_n+1;
        end
        if(u_win.cpu_awvalid&&u_win.cam_awvalid)aw_contend=aw_contend+1;
        if(u_wout.cpu_awvalid&&u_wout.cam_awvalid)aw_contend=aw_contend+1;
    end
    // ---------------- job control ----------------
    integer job,seq=0,jobs_done=0,aborts_done=0,proto_done=0,mmio_neg=0;
    task automatic set_pattern(input integer bidx,input integer kind,input integer param);
        begin u_ddr3.src_kind[bidx]=kind;u_ddr3.src_param[bidx]=param;end
    endtask
    task automatic pp_start(input integer bidx,input integer useq);
        begin
            cam_dual=1;cam_geom=1;cam_owned=2'b01<<bidx;cam_seq0=0;cam_seq1=0;
            if(bidx==0)cam_seq0=useq;else cam_seq1=useq;
            mmio(1,12,bidx,2,15);mmio(1,16,useq,2,15);mmio(1,4,1,2,15);
        end
    endtask
    task automatic wait_busy(input integer limit);
        integer g;begin g=0;
            while(!pp_busy && g<limit)begin @(negedge clk);g=g+1;end
            if(g>=limit)$fatal(1,"RESULT: FAIL preprocess never became busy");end
    endtask
    task automatic wait_done(input integer limit);
        integer g;begin g=0;
            while(!pp_done && !pp_read_error && g<limit)begin @(negedge clk);g=g+1;end
            if(g>=limit)$fatal(1,"RESULT: FAIL preprocess job timeout");end
    endtask
    task automatic reset_now;
        begin
            resetn=0;cam_dual=0;cam_owned=0;cpu_rd_valid=0;cpu_awvalid=0;syn_awvalid=0;pp_req_valid=0;
            u_ddr3.hold_ar=0;u_ddr3.hold_aw=0;u_ddr3.hold_w=0;u_ddr3.hold_r=0;
            repeat(10)@(negedge refclk);resetn=1;repeat(40)@(negedge clk);
        end
    endtask
    task automatic warm_hold;
        begin
            wait(u_hold.run);
            repeat(10)begin hdvp.idle(12);@(negedge hpclk);hdvp.vsync=0;repeat(12)@(negedge hpclk);hdvp.idle(12);end
        end
    endtask
    task automatic wait_hold_ready(input integer b,input integer limit);
        integer g;begin g=0;
            while(u_hold.buffer_state[b]!=2 && g<limit)begin @(negedge clk);g=g+1;end
            if(g>=limit)$fatal(1,"RESULT: FAIL hold buffer %0d not READY state=%0d err=%0d busy=%0d rsp=%0d beats=%0d dma=%0d timer=%0d wr=%0d pclk=%0d",
                b,u_hold.buffer_state[b],u_hold.error_code,u_hold.busy,u_hold.u_config.config_error,
                u_hold.written_beats,u_hold.dma_state,u_hold.timer,u_ddr3.cam_writes_n,hdvp.pclk);
        end
    endtask
    integer j;
    initial begin
        if(!$value$plusargs("UNIT=%s",path))$fatal(1,"RESULT: FAIL UNIT path");
        fd=$fopen(path,"w");if(!fd)$fatal(1,"RESULT: FAIL UNIT open");
        for(j=0;j<2;j=j+1)begin set_pattern(j,0,16'hf800);end
        repeat(12)@(negedge refclk);resetn=1;repeat(80)@(negedge clk);
        // ---------------- five complete jobs ----------------
        for(job=0;job<5;job=job+1)begin
            case(job)
                0:begin set_pattern(0,0,16'hf800);end
                1:begin set_pattern(1,0,16'h07e0);end
                2:begin set_pattern(0,0,16'h001f);end
                3:begin set_pattern(0,1,1);end
                default:begin set_pattern(1,1,2);end
            endcase
            seq=seq+1;
            $fdisplay(fd,"JOB %0d %0d %0d",job+1,(job==1||job==4),seq);
            pp_start((job==1||job==4),seq);
            if(m_err)$fatal(1,"RESULT: FAIL job start rejected");
            wait_busy(2000);wait_done(4000000);
            if(pp_read_error||u_pp.error_latched)$fatal(1,"RESULT: FAIL job error state");
            if(u_pp.reads!=9216||u_pp.pixels!=9216||u_pp.produced_bytes!=27648||u_pp.writes!=864)
                $fatal(1,"RESULT: FAIL job counters %0d %0d %0d %0d",u_pp.reads,u_pp.pixels,u_pp.produced_bytes,u_pp.writes);
            if(!pp_done||pp_busy)$fatal(1,"RESULT: FAIL job completion state");
            mmio(0,20,0,2,0);
            $fdisplay(fd,"JOB_DONE %0d %08h",job+1,m_rdata);
            mmio(1,4,4,2,15);
            jobs_done=jobs_done+1;
        end
        // ---------------- MMIO negative set ----------------
        cam_dual=1;cam_owned=2'b01;cam_seq0=seq;cam_seq1=0;cam_geom=1;
        mmio(1,12,2,2,15); if(!m_err)$fatal(1,"RESULT: FAIL SELECT range accepted");
        mmio(1,4,3,2,15);  if(!m_err)$fatal(1,"RESULT: FAIL compound CTRL accepted");
        mmio(1,0,0,2,15);  if(!m_err)$fatal(1,"RESULT: FAIL RO write accepted");
        mmio(1,4,1,1,15);  if(!m_err)$fatal(1,"RESULT: FAIL size accepted");
        mmio(1,4,1,2,3);   if(!m_err)$fatal(1,"RESULT: FAIL strobe accepted");
        mmio(1,5,1,2,15);  if(!m_err)$fatal(1,"RESULT: FAIL misaligned accepted");
        mmio(1,64,0,2,15); if(!m_err)$fatal(1,"RESULT: FAIL reserved offset accepted");
        cam_owned=0;mmio(1,12,0,2,15);mmio(1,16,seq,2,15);mmio(1,4,1,2,15);
        if(!m_err||u_pp.busy)$fatal(1,"RESULT: FAIL unclaimed START accepted");
        cam_owned=2'b01;cam_seq0=seq;mmio(1,12,0,2,15);mmio(1,16,seq+5,2,15);mmio(1,4,1,2,15);
        if(!m_err||u_pp.busy)$fatal(1,"RESULT: FAIL wrong-seq START accepted");
        cam_dual=0;cam_seq0=seq;mmio(1,12,0,2,15);mmio(1,16,seq,2,15);mmio(1,4,1,2,15);
        if(!m_err||u_pp.busy)$fatal(1,"RESULT: FAIL non-dual START accepted");
        mmio_neg=12;$fdisplay(fd,"CASE MMIO_NEG %0d",mmio_neg);
        // ---------------- ABORT positions ----------------
        reset_now;cam_dual=1;cam_geom=1;
        for(j=0;j<5;j=j+1)begin
            set_pattern(0,0,16'hf800);seq=seq+1;
            case(j)
                0:u_ddr3.hold_ar=1;
                1:u_ddr3.hold_r=1;
                2:;
                3:u_ddr3.hold_aw=1;
                default:u_ddr3.hold_w=1;
            endcase
            pp_start(0,seq);
            if(m_err)$fatal(1,"RESULT: FAIL abort-case start rejected");
            if(j==2)wait(u_pp.state==3);
            else if(j==0)wait(u_pp.arvalid);
            else if(j==1)wait(u_pp.state==2);
            else if(j==3)wait(u_pp.awvalid);
            else wait(u_pp.state==5);
            mmio(1,4,2,2,15);
            u_ddr3.hold_ar=0;u_ddr3.hold_aw=0;u_ddr3.hold_w=0;u_ddr3.hold_r=0;
            begin:wd integer g;g=0;
                while(pp_busy && g<400000)begin @(negedge clk);g=g+1;end
                if(g>=400000)$fatal(1,"RESULT: FAIL abort did not drain case %0d",j);
            end
            if(pp_done||!u_pp.error_latched||u_pp.error_code!=1)$fatal(1,"RESULT: FAIL abort state %0d",j);
            $fdisplay(fd,"CASE ABORT %0d %0d",j,u_pp.error_code);
            aborts_done=aborts_done+1;
            mmio(1,4,4,2,15);
        end
        // ---------------- read protocol errors ----------------
        for(j=1;j<=3;j=j+1)begin
            reset_now;cpu_rd_en=0;cpu_wr_en=0;cam_dual=1;cam_geom=1;
            set_pattern(0,0,16'hf800);seq=seq+1;
            u_ddr3.inject_pending=j;
            pp_start(0,seq);
            if(m_err)$fatal(1,"RESULT: FAIL protocol-case start rejected");
            begin:pd integer g;g=0;
                while(!pp_read_error && g<200000)begin @(negedge clk);g=g+1;end
                if(g>=200000)$fatal(1,"RESULT: FAIL protocol error not detected case %0d",j);
            end
            repeat(30)@(negedge clk);
            if(pp_done||!u_pp.error_latched||u_pp.error_code!=3)$fatal(1,"RESULT: FAIL protocol state %0d",j);
            if(pp_source_hold==0)$fatal(1,"RESULT: FAIL protocol released source hold");
            if(u_pp.arvalid)$fatal(1,"RESULT: FAIL new AR after protocol error");
            $fdisplay(fd,"CASE PROTO %0d %0d %0d",j,u_pp.error_code,pp_source_hold);
            proto_done=proto_done+1;
            u_ddr3.inject=0;u_ddr3.inject_pending=0;
        end
        // ---------------- real camera_mmio external hold ----------------
        reset_now;cpu_rd_en=1;cpu_wr_en=1;hold_mode=1;u_ddr3.allow_src_write=1;
        begin:hc
            begin:cfg integer g;g=0;
                while(!u_hold.config_done && !u_hold.config_error && g<3000000)begin @(negedge clk);g=g+1;end
                if(g>=3000000 || u_hold.config_error)$fatal(1,"RESULT: FAIL hold camera config");
            end
            mmio_hold(1,4,8,2,15);                       // STREAM_START
            if(hm_err)$fatal(1,"RESULT: FAIL hold stream start");
            warm_hold;
            $fdisplay(fd,"HOLD_WARM %0d %0d",u_hold.busy,u_hold.run);
            hdvp.frame(1,64,128,0);
            wait_hold_ready(0,3000000);
            wait(u_hold.run);
            hdvp.frame(2,64,128,0);
            wait_hold_ready(1,3000000);
            $fdisplay(fd,"HOLD_READY %0d %0d %0d %0d",u_hold.buffer_seq[0],u_hold.buffer_seq[1],hsw,hsr);
            mmio_hold(1,44,0,2,15);mmio_hold(1,56,u_hold.buffer_seq[0],2,15);mmio_hold(1,4,32,2,15);
            if(hm_err||u_hold.buffer_state[0]!=3)$fatal(1,"RESULT: FAIL hold claim A");
            hold_ext=2'b01;
            mmio_hold(1,44,0,2,15);mmio_hold(1,56,u_hold.buffer_seq[0],2,15);mmio_hold(1,4,64,2,15);
            if(!hm_err||u_hold.buffer_state[0]!=3)$fatal(1,"RESULT: FAIL held source release accepted");
            if(u_ddr3.cam_writes_n==0)$fatal(1,"RESULT: FAIL hold camera never wrote");
            $fdisplay(fd,"CASE HOLD_BLOCK %0d %0d",u_hold.buffer_state[0],u_hold.buffer_state[1]);
            mmio_hold(1,44,1,2,15);mmio_hold(1,56,u_hold.buffer_seq[1],2,15);mmio_hold(1,4,32,2,15);
            if(hm_err||u_hold.buffer_state[1]!=3)$fatal(1,"RESULT: FAIL other block claim blocked");
            mmio_hold(1,44,1,2,15);mmio_hold(1,56,u_hold.buffer_seq[1],2,15);mmio_hold(1,4,64,2,15);
            if(hm_err||u_hold.buffer_state[1]==3)$fatal(1,"RESULT: FAIL other block release blocked");
            hold_ext=2'b00;
            mmio_hold(1,44,0,2,15);mmio_hold(1,56,u_hold.buffer_seq[0],2,15);mmio_hold(1,4,64,2,15);
            if(hm_err||u_hold.buffer_state[0]==3)$fatal(1,"RESULT: FAIL release after hold removed");
            $fdisplay(fd,"CASE HOLD_PASS %0d",u_hold.buffer_state[0]);
        end
        $fdisplay(fd,"COVER %0d %0d %0d %0d %0d %0d %0d %0d",jobs_done,aborts_done,proto_done,mmio_neg,same_aw_w,sep_aw_w,aw_contend,ar_mix);
        $fdisplay(fd,"CPU_HOSTS %0d %0d %0d %0d %0d %0d",cpu_ar_n,pp_ar_n,cpu_beats,cpu_wr_n,cam_wr_n,pp_wr_n);
        $fdisplay(fd,"DDR_COVER %0d %0d %0d %0d",u_ddr3.same_cycle_ar_r,u_ddr3.immediate_r,u_ddr3.pp_reads,u_ddr3.pp_writes);
        $display("RESULT: PASS PP_UNIT");
        $fclose(fd);$finish;
    end
    always @(posedge clk)cycle=cycle+1;
    initial begin #60000000;$fatal(1,"RESULT: FAIL unit deadline");end
endmodule
