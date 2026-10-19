`timescale 1ns/1ps
module camera_arbiter_unit(output reg done=0);
    reg clk=0,resetn=0;
    always #5.333 clk=~clk;
    reg cv=0,mv=0;
    reg [27:0] ca=28'h100,ma=28'h400000;
    reg [255:0] cd=0,md=0;
    wire cr,cw,mr,mw,av;
    wire [27:0] aa;
    wire [3:0] len,id;
    wire ap;
    wire [255:0] data;
    wire [31:0] strb;
    integer cycle=0,remaining=0,cpu_tx=0,cam_tx=0,cpu_beats=0,cam_beats=0,owner=-1;
    integer stalls=0,gaps=0,same=0,contention=0,last=-1;
    wire ar=(cycle%11>=3);
    wire wr=(cycle%7>=2); // intentionally high before AW: must not be routed
    camera_ddr_write_arbiter arb(.clk(clk),.resetn(resetn),.cpu_awaddr(ca),.cpu_awlen(4'd3),
        .cpu_awid(4'd1),.cpu_awap(1'b0),.cpu_awvalid(cv),.cpu_wdata(cd),.cpu_wstrb(32'h5555aaaa),
        .cpu_awready(cr),.cpu_wready(cw),.cam_awaddr(ma),.cam_awvalid(mv),.cam_wdata(md),
        .cam_awready(mr),.cam_wready(mw),.awaddr(aa),.awlen(len),.awid(id),.awap(ap),
        .awvalid(av),.awready(ar),.wdata(data),.wstrb(strb),.wready(wr),.busy());
    reg held=0;
    reg [324:0] held_fields;
    reg [255:0] held_data;
    reg data_held=0;
    initial begin
        repeat(8) @(negedge clk);resetn=1;cv=1;mv=1;cd={8{32'hc0000000}};md={8{32'hd0000000}};
        wait(cpu_tx==6 && cam_tx==6 && remaining==0);
        @(negedge clk);
        if(cpu_beats!=24 || cam_beats!=6 || stalls==0 || gaps==0 || same==0 || contention==0)
            $fatal(1,"RESULT: FAIL arbiter vacuous coverage");
        $display("ARB %0d %0d %0d %0d %0d %0d %0d %0d",cpu_tx,cam_tx,cpu_beats,cam_beats,stalls,gaps,same,contention);
        done=1;
    end
    // Producers change only after their own accepted address/data, on falling edges.
    integer cp=0,mp=0;
    always @(negedge clk) if(resetn && !done) begin
        cycle=cycle+1;
        ca=28'h100+cpu_tx*32;ma=28'h400000+cam_tx*8;
        cv=(cpu_tx<6 && cp==0);mv=(cam_tx<6 && mp==0);
        cd={8{32'hc0000000+cpu_beats}};md={8{32'hd0000000+cam_beats}};
    end
    always @(posedge clk) if(resetn && !done) begin
        if(cv && mv) contention=contention+1;
        if(held && {aa,len,id,ap,data,strb}!==held_fields) $fatal(1,"RESULT: FAIL AW changed under stall");
        held=av && !ar;held_fields={aa,len,id,ap,data,strb};
        if(data_held && data!==held_data) $fatal(1,"RESULT: FAIL W changed under stall");
        if(av && !ar) stalls=stalls+1;
        if(av && ar) begin
            $display("ARBAW %0d %0d %0d %07h %0d %0d",cycle,id,len,aa,cv,mv);
            if(remaining!=0) $fatal(1,"RESULT: FAIL interleaved burst");
            owner=(id==2);remaining=len+1;
            if((id!=1 && id!=2) || ap || len!=(owner ? 0 : 3)) $fatal(1,"RESULT: FAIL arb attributes");
            if(cv && mv && last!=-1 && owner==last) $fatal(1,"RESULT: FAIL arbitration fairness");
            if(owner) begin mp=1;cam_tx=cam_tx+1; end
            else begin cp=1;cpu_tx=cpu_tx+1; end
            if(wr) same=same+1;
        end
        if(wr && remaining!=0) begin
            $display("ARBW %0d %0d %064h %08h",cycle,owner,data,strb);
            if(cw===mw || (owner ? !mw : !cw)) $fatal(1,"RESULT: FAIL W routing");
            if(data!=={8{(owner ? 32'hd0000000+cam_beats : 32'hc0000000+cpu_beats)}} ||
               strb!==(owner ? 32'hffffffff : 32'h5555aaaa)) $fatal(1,"RESULT: FAIL owner/data/strobe");
            if(owner) cam_beats=cam_beats+1; else cpu_beats=cpu_beats+1;
            remaining=remaining-1;
            if(remaining==0) begin last=owner;if(owner)mp=0;else cp=0;end
        end else if(cw || mw) $fatal(1,"RESULT: FAIL premature/foreign W completion");
        if(remaining!=0 && !wr) gaps=gaps+1;
        data_held=remaining!=0 && !wr;held_data=data;
        if(cycle>3000) $fatal(1,"RESULT: FAIL arbiter timeout");
    end
endmodule
