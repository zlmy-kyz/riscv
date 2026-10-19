`timescale 1ns/1ps
// One missing boundary only: old cached I response + younger I + invalidating D store.
// DDR-local byte addresses. All stimulus changes at negedge; snapshots precede NBA.
module tb_inst_lookup_triple;
    GTP_GRS GRS_INST (.GRS_N(1'b1));
    reg clk=0;
    always #5 clk=~clk;
    reg resetn=0, init_done=0;
    reg iv=0, dv=0, dw=0;
    reg [31:0] ia=0, da=0, dd=0;
    reg [3:0] ds=0;
    wire ir, dr, ip, dp, ie, de, busy;
    wire [31:0] idata, ddata;
    wire arv, awv;
    wire [27:0] ara, awa;
    wire [3:0] ari;
    wire [255:0] wd;
    wire [31:0] ws;
    reg rv=0;
    reg [255:0] rd=0;
    reg [3:0] ri=0;
    dual_sram_to_pango_ddr_bridge #(.MEM_DQ_WIDTH(32),
        .INST_LINE_BUFFER_ENABLE(1), .DATA_LINE_BUFFER_ENABLE(1), .POSTED_WRITE_ENABLE(1)) dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(init_done), .write_buffer_busy(busy),
        .inst_req_valid(iv), .inst_req_addr(ia), .inst_req_ready(ir),
        .inst_rsp_valid(ip), .inst_rsp_rdata(idata), .inst_rsp_error(ie),
        .data_req_valid(dv), .data_req_write(dw), .data_req_size(2'd2),
        .data_req_addr(da), .data_req_wdata(dd), .data_req_wstrb(ds), .data_req_ready(dr),
        .data_rsp_valid(dp), .data_rsp_rdata(ddata), .data_rsp_error(de),
        .axi_awaddr(awa), .axi_awuser_ap(), .axi_awuser_id(), .axi_awlen(),
        .axi_awready(1'b1), .axi_awvalid(awv), .axi_wdata(wd), .axi_wstrb(ws),
        .axi_wready(1'b1), .axi_wusero_id(4'd1), .axi_wusero_last(1'b1),
        .axi_araddr(ara), .axi_aruser_ap(), .axi_aruser_id(ari), .axi_arlen(),
        .axi_arready(1'b1), .axi_arvalid(arv), .axi_rdata(rd), .axi_rid(ri),
        .axi_rlast(1'b1), .axi_rvalid(rv));
    reg [7:0] memory [0:4095];
    integer fd, fp, n=0, accepts=0, responses=0, aw_count=0, w_count=0;
    integer itok=-1, dtok=-1, owner=-1;
    integer state [0:3];
    integer j;
    string log_path, plan_path;
    reg fi, fdi, fr, faw;
    reg [27:0] sampled_aw;
    reg [255:0] sampled_w;
    reg [31:0] sampled_s;

    function automatic [255:0] beat(input [27:0] a);
        integer k;
        begin
            beat=0;
            for(k=0;k<32;k=k+1) beat[k*8+:8]=memory[(a*4+k)&4095];
        end
    endfunction

    // The caller enters/exits on a negedge. Generate R before the upcoming AR edge.
    task automatic tick;
        integer k;
        begin
            #1;
            rv=resetn && init_done && arv;
            rd=rv ? beat(ara) : 256'b0;
            ri=ari;
            @(posedge clk);
            n=n+1;
            $fdisplay(fd,"E %0d 1 %0b %0b %0b %0b %08x %0b %0b %0b 2 %08x %08x %01x %0b %08x %0b %08x %0b 1 %08x %0d %0b 1 %08x %064x %08x 1 %0b %064x %0d 1 %0b",
                n,resetn,init_done,iv,ir,ia,dv,dr,dw,da,dd,ds,ip,idata,dp,ddata,
                arv,ara,ari,awv,awa,wd,ws,rv,rd,ri,busy);
            if(resetn && ((ip && ie !== 1'b0) || (dp && de !== 1'b0)))
                $fatal(1,"RESULT: FAIL response error edge=%0d",n);
            fi=resetn && iv && ir;
            fdi=resetn && dv && dr;
            fr=resetn && (ip || dp);
            faw=resetn && awv;  // AWREADY=WREADY=1 => same edge physical W
            sampled_aw=awa; sampled_w=wd; sampled_s=ws;
            if(fi && fdi) $fatal(1,"RESULT: FAIL both requests accepted edge=%0d",n);
            if(fr) begin
                if(owner<0 || (ip && dp)) $fatal(1,"RESULT: FAIL response owner edge=%0d",n);
                state[owner]=2; owner=-1; responses=responses+1;
            end
            if(fi) begin
                if(owner>=0 || itok<0 || state[itok]!=0) $fatal(1,"RESULT: FAIL I owner");
                owner=itok; state[itok]=1; accepts=accepts+1;
            end
            if(fdi) begin
                if(owner>=0 || dtok<0 || state[dtok]!=0) $fatal(1,"RESULT: FAIL D owner");
                owner=dtok; state[dtok]=1; accepts=accepts+1;
            end
            @(negedge clk);
            // Only consumed W fields change memory, after this edge's read was sampled.
            if(faw) begin
                aw_count=aw_count+1; w_count=w_count+1;
                for(k=0;k<32;k=k+1)
                    if(sampled_s[k]) memory[(sampled_aw*4+k)&4095]=sampled_w[k*8+:8];
            end
            if(fi) begin iv=0; itok=-1; end
            if(fdi) begin dv=0; dtok=-1; end
            if(n>80) $fatal(1,"RESULT: FAIL edge watchdog");
        end
    endtask
    task automatic present_i(input integer t, input [31:0] addr);
        begin itok=t; ia=addr; iv=1; end
    endtask
    task automatic wait_acc(input integer t);
        begin while(state[t]==0) tick(); end
    endtask
    task automatic wait_rsp(input integer t);
        begin while(state[t]!=2) tick(); end
    endtask

    initial begin
        if(!$value$plusargs("EDGE_LOG=%s",log_path) || !$value$plusargs("PLAN_LOG=%s",plan_path))
            $fatal(1,"RESULT: FAIL missing paths");
        fd=$fopen(log_path,"w"); fp=$fopen(plan_path,"w");
        if(!fd || !fp) $fatal(1,"RESULT: FAIL trace open");
        for(j=0;j<4096;j=j+1) memory[j]=(j*43+90)&255;
        for(j=0;j<4;j=j+1) state[j]=0;
        $fdisplay(fp,"PLAN 0 1 0 0 00000040 2 00000000 0 0");
        $fdisplay(fp,"PLAN 1 1 0 0 00000044 2 00000000 0 0");
        $fdisplay(fp,"PLAN 2 1 0 0 00000044 2 00000000 0 0");
        $fdisplay(fp,"PLAN 3 1 1 1 00000044 2 01020304 a 0");
        $fclose(fp);
        @(negedge clk);
        repeat(3) tick();
        resetn=1; init_done=1;
        present_i(0,32'h40); wait_rsp(0);  // legal DDR fill
        present_i(1,32'h44); wait_acc(1);  // old hit, next edge consumes its response
        present_i(2,32'h44);               // younger I must lose and remain valid
        dtok=3; dv=1; dw=1; da=32'h44; dd=32'h01020304; ds=4'ha;
        wait_acc(3);
        wait_acc(2);                       // old D ACK + held I acceptance
        wait_rsp(2);
        repeat(2) tick();
        if(accepts!=4 || responses!=4 || aw_count!=1 || w_count!=1 || owner!=-1)
            $fatal(1,"RESULT: FAIL final conservation");
        $fdisplay(fd,"SUM accepts=%0d responses=%0d aw=%0d w=%0d edges=%0d",accepts,responses,aw_count,w_count,n);
        $fclose(fd);
        $display("RESULT: PASS inst_lookup_triple accepts=4 responses=4 aw=1 w=1");
        $finish;
    end
    initial begin #4000000; $fatal(1,"RESULT: FAIL watchdog"); end
endmodule
