`include "generated/ddr_header.svh"
// Native Pango user-port model for the preprocess key group. No PHY claim.
// Source contents come only from the closed-form pattern definition; the
// independent Python reference is the authority the checker compares against.
// The synthetic camera write stream must write exactly the reference bytes for
// its addresses, so stored DDR content is never corrupted by test stimulus.
    reg mclk=0;
    always #5.333 mclk=~mclk;
    assign core_clk=mclk;
    assign pll_lock=resetn;assign ddr_init_done=resetn;
    assign phy_pll_lock=resetn;assign gpll_lock=resetn;
    assign rst_gpll_lock=resetn;assign ddrphy_cpd_lock=resetn;
    reg [255:0] lowmem[0:8191];
    reg [255:0] outmem[0:2047];
    // Dedicated 4KiB window just outside the 4MiB frame aperture: the synthetic
    // camera write host writes fixed bytes here, so contention is real without
    // ever changing the formula-defined source content.
    reg [255:0] camw[0:127];
    reg [31:0] image[0:4095];
    integer epoch=0,cycle=0,aw_age=0,w_age=0,r_age=0,i,j,k;
    reg writing=0,reading=0,extra=0;
    reg [27:0] wa=0,ra=0;
    reg [3:0] wi=0,ri=0,wepoch=0;
    reg [4:0] remaining=0;
    // Held empty for every preprocess job: any non-reference source write is a
    // failure. Only the real-camera hold sub-case (after all PP jobs) may store
    // DVP bytes, into this override map, and nothing reads those lines again.
    reg [255:0] srcover[longint];
    integer allow_src_write=0;
    integer logfd,inject=0,inject_pending=0;
    // Stall knobs used by the abort sub-cases (model stimulus, never a design force).
    integer hold_ar=0,hold_aw=0,hold_w=0,hold_r=0;
    integer pp_reads=0,pp_writes=0,cam_writes_n=0,cpu_writes_n=0,cpu_reads_n=0;
    integer same_cycle_ar_r=0,immediate_r=0;
    string path;
    // 0=constant colour (param is the RGB565 word), 1=asymmetric coordinate pattern.
    integer src_kind[0:1];integer src_param[0:1];
    function automatic [15:0] src_pixel(input integer bidx,x,y,kind,param);
        integer r5,g6,b5;
        begin
            if(kind==0) src_pixel=param[15:0];
            else begin
                r5=(3*x+5*y+7*param)&31;
                g6=(11*x+7*y+13*param)&63;
                b5=(x^(3*y)^(17*param))&31;
                src_pixel=(r5<<11)|(g6<<5)|b5;
            end
        end
    endfunction
    // One 256-bit beat = 16 consecutive pixels inside one row (rows are 80 beats).
    function automatic [255:0] src_word(input [27:0] address);
        integer bidx,off,y,x0,x;
        reg [31:0] laddr;
        begin
            laddr=address<<2;bidx=(laddr>=32'h00200000)?1:0;
            off=laddr-(bidx?32'h00200000:0);
            y=off/2560;x0=(off%2560)/2;
            for(x=0;x<16;x=x+1) src_word[x*16+:16]=src_pixel(bidx,x0+x,y,src_kind[bidx],src_param[bidx]);
        end
    endfunction
    function automatic [255:0] reference_word(input [27:0] address);
        integer bidx,off,y,x0,x;
        reg [31:0] laddr;
        begin
            laddr=address<<2;bidx=(laddr>=32'h00200000)?1:0;
            off=laddr-(bidx?32'h00200000:0);
            y=off/2560;x0=(off%2560)/2;
            for(x=0;x<16;x=x+1) reference_word[x*16+:16]=src_pixel(bidx,x0+x,y,src_kind[bidx],src_param[bidx]);
        end
    endfunction
    function automatic [255:0] load(input [27:0] address);
        if(address<28'h10000)load=lowmem[address>>3];
        else if(address>=28'h400000 && address<28'h500000)
            load=(allow_src_write && srcover.exists(longint'(address))) ? srcover[longint'(address)] : src_word(address);
        else if(address>=28'h800000 && address<28'h804000)load=outmem[(address-28'h800000)>>3];
        else if(address>=28'h500000 && address<28'h501000)load=camw[(address-28'h500000)>>3];
        else begin $fatal(1,"RESULT: FAIL DDR read outside model %h",address);load=0;end
    endfunction
    task automatic store(input [27:0] address,input[255:0] value,input[31:0] mask,input[3:0] id);
        integer lane;
        begin
            if(address[2:0]!=0)$fatal(1,"RESULT: FAIL native alignment");
            if(address<28'h10000)begin
                for(lane=0;lane<32;lane=lane+1)if(mask[lane])lowmem[address>>3][lane*8+:8]=value[lane*8+:8];
                cpu_writes_n=cpu_writes_n+1;
            end else if(address>=28'h400000 && address<28'h500000)begin
                // The synthetic camera host must never change source content.
                if(allow_src_write)begin
                    srcover[longint'(address)]=value;cam_writes_n=cam_writes_n+1;
                end else begin
                    if(mask!==32'hffffffff || value!==reference_word(address))
                        $fatal(1,"RESULT: FAIL synthetic camera write is not reference source %h",address);
                    cam_writes_n=cam_writes_n+1;
                end
            end else if(address>=28'h800000 && address<28'h804000)begin
                for(lane=0;lane<32;lane=lane+1)if(mask[lane])outmem[(address-28'h800000)>>3][lane*8+:8]=value[lane*8+:8];
            end else if(address>=28'h500000 && address<28'h501000)begin
                for(lane=0;lane<32;lane=lane+1)if(mask[lane])camw[(address-28'h500000)>>3][lane*8+:8]=value[lane*8+:8];
                cam_writes_n=cam_writes_n+1;
            end else $fatal(1,"RESULT: FAIL native write range %h id %0d",address,id);
        end
    endtask
    wire ar_fire=axi_arvalid && axi_arready;
    wire immediate=ar_fire && !reading && axi_arlen==0 && (cycle%4)==0 && inject==0;
    wire reg_beat=resetn && reading && r_age==0 && !hold_r;
    wire injected_wrong_id=reg_beat && inject==1;
    wire injected_no_last=reg_beat && inject==2;
    wire wrong_rid=injected_wrong_id;
    assign axi_arready=resetn && !reading && !hold_ar && r_age>=2 && cycle%11!=0;
    assign axi_awready=resetn && !writing && !hold_aw && aw_age>=2 && cycle%13!=0;
    assign axi_wready=resetn && !hold_w && (writing ? (w_age>=4 && cycle%7!=0) :
                     (axi_awvalid && axi_awready && cycle%3==0));
    assign axi_wusero_id=writing?wi:axi_awuser_id;
    assign axi_wusero_last=axi_wready;
    // Combinational response path so AR/R in the same cycle is a real edge case.
    always @(*) begin
        axi_rvalid = resetn && (reg_beat || immediate || extra);
        axi_rdata  = immediate ? load(axi_araddr) : load(ra);
        axi_rid    = immediate ? axi_aruser_id : (wrong_rid ? (ri==4'd3 ? 4'd2 : ri+4'd1) : ri);
        axi_rlast  = immediate ? 1'b1 : (injected_no_last ? 1'b0 : (remaining==5'd1));
    end
    reg held=0,wheld=0;
    reg [324:0] aw_fields;
    reg [287:0] w_fields;
    always @(negedge mclk)cycle=cycle+1;
    always @(posedge mclk)begin
        if(!resetn)begin
            writing<=0;reading<=0;aw_age<=0;w_age<=0;r_age<=0;held=0;wheld=0;
            extra<=0;inject<=0;inject_pending<=0;remaining<=0;
        end else begin
            extra<=0;
            if(held && (!axi_awvalid || {axi_awaddr,axi_awlen,axi_awuser_id,axi_awuser_ap,axi_wdata,axi_wstrb}!==aw_fields))
                $fatal(1,"RESULT: FAIL native AW stability id=%0d addr=%h cyc=%0d awv=%0d awr=%0d old=%h new=%h",
                    axi_awuser_id,axi_awaddr,cycle,axi_awvalid,axi_awready,aw_fields[255:0],axi_wdata);
            if(wheld && {axi_wdata,axi_wstrb}!==w_fields)
                $fatal(1,"RESULT: FAIL native W stability id=%0d addr=%h cyc=%0d",wi,wa,cycle);
            held=axi_awvalid && !axi_awready;
            aw_fields={axi_awaddr,axi_awlen,axi_awuser_id,axi_awuser_ap,axi_wdata,axi_wstrb};
            if(axi_awvalid && !axi_awready)aw_age<=aw_age+1;
            if(axi_awvalid && axi_awready)begin
                if(writing || axi_awuser_ap || axi_awaddr[2:0]!=0)
                    $fatal(1,"RESULT: FAIL native AW attributes");
                $fdisplay(logfd,"AW %0d %0d %0d %07h %0d %0d",axi_awuser_id,cycle,epoch,axi_awaddr,axi_awlen,axi_awuser_ap);
                wa<=axi_awaddr;wi<=axi_awuser_id;wepoch<=epoch;
                if(axi_awuser_id==4'd3)pp_writes=pp_writes+1; else if(axi_awuser_id!=4'd2)cpu_writes_n=cpu_writes_n+1;
                if(axi_wready)begin
                    store(axi_awaddr,axi_wdata,axi_wstrb,axi_awuser_id);
                    $fdisplay(logfd,"W %0d %0d %0d %07h %064h %08h",axi_awuser_id,cycle,epoch,axi_awaddr,axi_wdata,axi_wstrb);
                end else begin writing<=1;w_age<=0;end
                aw_age<=0;
            end else if(writing && axi_wready)begin
                store(wa,axi_wdata,axi_wstrb,wi);
                $fdisplay(logfd,"W %0d %0d %0d %07h %064h %08h",wi,cycle,wepoch,wa,axi_wdata,axi_wstrb);
                writing<=0;w_age<=0;
            end else if(writing)w_age<=w_age+1;
            wheld=(writing || (axi_awvalid && axi_awready)) && !axi_wready;w_fields={axi_wdata,axi_wstrb};
            if(axi_arvalid && !axi_arready && !reading)r_age<=r_age+1;
            if(axi_arvalid && axi_arready)begin
                if(axi_aruser_ap || axi_araddr[2:0]!=0)$fatal(1,"RESULT: FAIL native AR attributes");
                $fdisplay(logfd,"AR %0d %0d %0d %07h %0d %0d",axi_aruser_id,cycle,epoch,axi_araddr,axi_arlen,axi_aruser_ap);
                if(axi_aruser_id==4'd3)pp_reads=pp_reads+1; else cpu_reads_n=cpu_reads_n+1;
                if(immediate)begin
                    immediate_r=immediate_r+1;same_cycle_ar_r=same_cycle_ar_r+1;
                    $fdisplay(logfd,"R %0d %0d %0d %07h %064h",axi_aruser_id,cycle,epoch,axi_araddr,load(axi_araddr));
                end else begin
                    ra<=axi_araddr;ri<=axi_aruser_id;remaining<={1'b0,axi_arlen}+5'd1;reading<=1;
                    r_age<=-(axi_araddr>=28'h400000 ? 5:3)-(cycle%4);
                end
                inject<=inject_pending;inject_pending<=0;
            end else if(reg_beat)begin
                $fdisplay(logfd,"R %0d %0d %0d %07h %064h",axi_rid,cycle,epoch,ra,load(ra));
                if(wrong_rid || injected_no_last)begin
                    reading<=0;inject<=0;
                end else if(remaining==5'd1)begin
                    reading<=0;
                    if(inject==3)begin extra<=1;inject<=0;end else inject<=0;
                end else begin
                    remaining<=remaining-5'd1;ra<=ra+8;r_age<=-1-(cycle%3);
                end
            end else if(reading && r_age<0)r_age<=r_age+1;
        end
    end
    initial begin
        if(!$value$plusargs("DAT=%s",path))$fatal(1,"RESULT: FAIL DAT missing");
        $readmemh(path,image);
        for(i=0;i<8192;i=i+1)lowmem[i]={8{32'ha5a55a5a}};
        for(i=0;i<2048;i=i+1)outmem[i]={8{32'hdeadbeef}};
        for(i=0;i<128;i=i+1)camw[i]={8{32'h0f1e2d3c}};
        for(i=0;i<8192;i=i+1)lowmem[i/8][(i%8)*32+:32]=image[i];
        lowmem[3072]=0;
        for(k=0;k<2;k=k+1)begin src_kind[k]=0;src_param[k]=0;end
        if(!$value$plusargs("BUS=%s",path))$fatal(1,"RESULT: FAIL BUS missing");
        logfd=$fopen(path,"w");if(!logfd)$fatal(1,"RESULT: FAIL BUS open");
    end
endmodule
