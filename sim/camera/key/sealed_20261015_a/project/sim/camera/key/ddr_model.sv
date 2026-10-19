`include "generated/ddr_header.svh"
    reg mclk=0;
    always #5.333 mclk=~mclk;
    assign core_clk=mclk;
    assign pll_lock=resetn;assign ddr_init_done=resetn;
    assign phy_pll_lock=resetn;assign gpll_lock=resetn;
    assign rst_gpll_lock=resetn;assign ddrphy_cpd_lock=resetn;
    reg [255:0] lowmem[0:4095], frames[0:65535];
    reg [31:0] image[0:4095];
    integer epoch=0,cycle=0,aw_age=0,w_age=0,r_age=0,i,j;
    integer camera_writes[0:2],last_write[0:2];
    reg writing=0,reading=0;
    reg [27:0] wa=0,ra=0;
    reg [3:0] wi=0,ri=0;
    integer logfd,wepoch=0,repoch=0;
    string path;
    initial begin
        if(!$value$plusargs("DAT=%s",path))$fatal(1,"RESULT: FAIL DAT missing");
        $readmemh(path,image);
        for(i=0;i<4096;i=i+1)lowmem[i]={8{32'ha5a55a5a}};
        for(i=0;i<65536;i=i+1)frames[i]={8{32'hdeadbeef}};
        for(i=0;i<4096;i=i+1)lowmem[i/8][(i%8)*32+:32]=image[i];
        for(i=0;i<3;i=i+1)begin camera_writes[i]=0;last_write[i]=0;end
        if(!$value$plusargs("BUS=%s",path))$fatal(1,"RESULT: FAIL BUS missing");
        logfd=$fopen(path,"w");if(!logfd)$fatal(1,"RESULT: FAIL BUS open");
        axi_rvalid=0;axi_rdata=0;axi_rid=0;axi_rlast=0;
    end
    function automatic [255:0] load(input [27:0] address);
        if(address<28'h8000)load=lowmem[address>>3];
        else if(address>=28'h400000 && address<28'h480000)load=frames[(address-28'h400000)>>3];
        else begin $fatal(1,"RESULT: FAIL DDR address outside model %h",address);load=0;end
    endfunction
    task automatic store(input [27:0] address,input[255:0] value,input[31:0] mask);
        integer lane;
        begin
            if(address[2:0]!=0)$fatal(1,"RESULT: FAIL native alignment");
            if(address<28'h8000)begin
                for(lane=0;lane<32;lane=lane+1)if(mask[lane])lowmem[address>>3][lane*8+:8]=value[lane*8+:8];
            end else if(address>=28'h400000 && address<28'h480000)begin
                for(lane=0;lane<32;lane=lane+1)if(mask[lane])frames[(address-28'h400000)>>3][lane*8+:8]=value[lane*8+:8];
            end else $fatal(1,"RESULT: FAIL native write range");
        end
    endtask
    // Independent stalls, including immediate AW/W consumption and a long final-W hold.
    wire last_addr=(writing ? wa : axi_awaddr)==28'h4707f8;
    assign axi_awready=resetn && !writing && aw_age>=2 && cycle%13!=0;
    assign axi_wready=resetn && (writing ? (w_age>=(last_addr?127:4) && cycle%7!=0) :
                     (axi_awvalid && axi_awready && cycle%3==0 && !last_addr));
    assign axi_wusero_id=writing?wi:axi_awuser_id;
    assign axi_wusero_last=axi_wready;
    assign axi_arready=resetn && !reading && r_age>=2 && cycle%11!=0;
    reg held=0,wheld=0;
    reg [324:0] aw_fields;
    reg [287:0] w_fields;
    always @(negedge mclk)cycle=cycle+1;
    always @(posedge mclk)begin
        axi_rvalid<=0;axi_rlast<=0;
        if(!resetn)begin writing<=0;reading<=0;aw_age<=0;w_age<=0;r_age<=0;held=0;wheld=0;end
        else begin
            if(held && (!axi_awvalid || {axi_awaddr,axi_awlen,axi_awuser_id,axi_awuser_ap,axi_wdata,axi_wstrb}!==aw_fields))
                $fatal(1,"RESULT: FAIL native AW stability");
            if(wheld && {axi_wdata,axi_wstrb}!==w_fields)$fatal(1,"RESULT: FAIL native W stability");
            held=axi_awvalid && !axi_awready;
            aw_fields={axi_awaddr,axi_awlen,axi_awuser_id,axi_awuser_ap,axi_wdata,axi_wstrb};
            if(axi_awvalid && !axi_awready)aw_age<=aw_age+1;
            if(axi_awvalid && axi_awready)begin
                if(writing || axi_awlen!=0 || axi_awuser_ap || axi_awaddr[2:0]!=0)
                    $fatal(1,"RESULT: FAIL native AW attributes");
                $fdisplay(logfd,"AW %0d %0d %0d %07h",epoch,cycle,axi_awuser_id,axi_awaddr);
                wa<=axi_awaddr;wi<=axi_awuser_id;wepoch<=epoch;
                // Compute acceptance using old 'writing' before changing model state.
                if(axi_wready)begin
                    store(axi_awaddr,axi_wdata,axi_wstrb);
                    $fdisplay(logfd,"W %0d %0d %0d %07h %064h %08h",epoch,cycle,axi_awuser_id,axi_awaddr,axi_wdata,axi_wstrb);
                    if(axi_awuser_id==2)begin camera_writes[epoch]=camera_writes[epoch]+1;last_write[epoch]=cycle;end
                end else begin writing<=1;w_age<=0;end
                aw_age<=0;
            end else if(writing && axi_wready)begin
                store(wa,axi_wdata,axi_wstrb);
                $fdisplay(logfd,"W %0d %0d %0d %07h %064h %08h",wepoch,cycle,wi,wa,axi_wdata,axi_wstrb);
                if(wi==2)begin camera_writes[wepoch]=camera_writes[wepoch]+1;last_write[wepoch]=cycle;end
                writing<=0;w_age<=0;
            end else if(writing)w_age<=w_age+1;
            wheld=(writing || (axi_awvalid && axi_awready)) && !axi_wready;w_fields={axi_wdata,axi_wstrb};
            if(axi_arvalid && !axi_arready && !reading)r_age<=r_age+1;
            if(axi_arvalid && axi_arready)begin
                if(axi_arlen || axi_aruser_ap || axi_araddr[2:0]!=0)$fatal(1,"RESULT: FAIL native AR attributes");
                ra<=axi_araddr;ri<=axi_aruser_id;repoch<=epoch;reading<=1;r_age<=-5-(cycle%4);
                $fdisplay(logfd,"AR %0d %0d %0d %07h",epoch,cycle,axi_aruser_id,axi_araddr);
            end else if(reading)begin
                if(r_age==0)begin
                    axi_rdata<=load(ra);axi_rid<=ri;axi_rvalid<=1;axi_rlast<=1;reading<=0;
                    $fdisplay(logfd,"R %0d %0d %0d %07h %064h",repoch,cycle,ri,ra,load(ra));
                end else r_age<=r_age+1;
            end
        end
    end
endmodule
