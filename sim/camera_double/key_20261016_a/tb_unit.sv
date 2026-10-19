`timescale 1ns/1ps
module tb_double_unit;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    reg clk=0,rst=0;always #5.333 clk=~clk;
    wire pclk,vs,href;wire[7:0]din;double_dvp dvp(.pclk(pclk),.vsync(vs),.href(href),.din(din));
    tri1 scl,sda;wire scllow,sdalow;assign scl=scllow?1'b0:1'bz;assign sda=sdalow?1'b0:1'bz;
    integer sw,sr;camera_sensor sensor(.resetn(rst),.scl(scl),.sda(sda),.injection(32'b0),.writes(sw),.reads(sr));
    reg v=0,wr=0;reg[31:0]addr=0,data=0;reg[1:0]size=2;reg[3:0]strb=15;
    wire ready,rv,re;wire[31:0]rr;wire av;wire[27:0]aa;wire[255:0]wd;
    reg awgate=1,wgate=1,finalgate=1;reg pending=0;reg[27:0]wa=0;integer age=0,cycle=0,epoch=0,fd;
    wire ar=awgate && !pending && cycle%7!=0;
    wire last=(pending?wa:aa)==28'h400ff8 || (pending?wa:aa)==28'h480ff8;
    wire ww=wgate && (!last || finalgate) && (pending ? age>=3 && cycle%5!=0 : av && ar && cycle%3==0);
    camera_mmio #(.CLK_HZ(100000),.WIDTH(64),.HEIGHT(128),.DROP_FRAMES(10)) cam(
        .clk(clk),.resetn(rst),.req_valid(v),.req_write(wr),.req_size(size),.req_addr(addr),.req_wdata(data),.req_wstrb(strb),
        .req_ready(ready),.rsp_valid(rv),.rsp_error(re),.rsp_rdata(rr),.pclk(pclk),.vsync(vs),.href(href),.din(din),
        .scl_in(scl),.sda_in(sda),.scl_low(scllow),.sda_low(sdalow),.dma_awvalid(av),.dma_awaddr(aa),.dma_wdata(wd),.dma_awready(ar),.dma_wready(ww));
    defparam cam.u_config.CLK_HZ=1600000;
    wire aperture_done;double_aperture aperture(aperture_done);
    integer wc[0:1],lastw[0:1],oldstate[0:1],pubs=0,release_publish=0,stop_race=0,awstall=0,wstall=0,same=0,separate=0,b,i;
    reg[31:0]got,save0,save1,seq0,seq1;reg[27:0]held_addr;reg[255:0]held_data,held_w;reg held=0,wheld=0;
    string path;
    task bus(input bit write_,input[31:0]a,d,input[1:0]sz,input[3:0]st,input bit error_);
        begin
            @(negedge clk);v=1;wr=write_;addr=a;data=d;size=sz;strb=st;
            do @(posedge clk);while(!ready);
            @(negedge clk);v=0;
            if(!rv)wait(rv);
            got=rr;if(re!==error_)$fatal(1,"RESULT: FAIL MMIO %h %h got error=%b wanted=%b",a,d,re,error_);
            $fdisplay(fd,"MMIO %0d %0d %08h %08h %0d %0d %0d %08h",cycle,write_,a,d,sz,st,re,rr);
            @(negedge clk);
        end
    endtask
    task cmd(input[31:0]c,input bit e);bus(1,4,c,2,15,e);endtask
    task select_token(input integer b,input[31:0]s);begin bus(1,44,b,2,15,0);bus(1,56,s,2,15,0);end endtask
    task warm;begin wait(cam.run);repeat(10)begin dvp.idle(12);@(negedge pclk);dvp.vsync=0;repeat(12)@(negedge pclk);dvp.idle(12);end end endtask
    task frame(input integer p,k);begin epoch=p;dvp.frame(p,64,128,k);end endtask
    task until_idle;begin wait(!cam.busy);repeat(3)@(negedge clk);end endtask
    task preserved(input integer b,input[31:0]s,c);
        if(cam.buffer_state[b]!=3 || cam.buffer_seq[b]!=s || cam.buffer_crc[b]!=c)$fatal(1,"RESULT: FAIL held CPU buffer changed");
    endtask
    initial begin
        if(!$value$plusargs("UNIT=%s",path))$fatal(1,"RESULT: FAIL UNIT path");fd=$fopen(path,"w");
        for(i=0;i<2;i=i+1)begin wc[i]=0;lastw[i]=-1;oldstate[i]=0;end
        repeat(10)@(negedge clk);rst=1;wait(cam.config_done);
        bus(0,0,0,2,15,0);if(got!=32'h43414d02)$fatal(1,"RESULT: FAIL ABI ID");
        cmd(8,0);warm();frame(1,0);wait(cam.buffer_state[0]==2);
        select_token(0,0);cmd(32,1);select_token(0,1);cmd(64,1);cmd(32,0);cmd(32,1);
        save0=cam.buffer_crc[0];seq0=cam.buffer_seq[0];
        wait(cam.run);select_token(1,2);cmd(32,1);
        bus(0,12,0,2,15,0);if(got!=32'h41200000)$fatal(1,"RESULT: FAIL selected B base");
        bus(0,16,0,2,15,0);if(got!=0)$fatal(1,"RESULT: FAIL WRITING bytes valid");
        bus(0,20,0,2,15,0);if(got!=0)$fatal(1,"RESULT: FAIL WRITING sequence valid");
        bus(0,40,0,2,15,0);if(got!=0)$fatal(1,"RESULT: FAIL WRITING CRC valid");
        frame(2,0);wait(cam.buffer_state[1]==2);
        select_token(1,0);cmd(32,1);select_token(1,2);cmd(64,1);cmd(32,0);cmd(32,1);
        save1=cam.buffer_crc[1];seq1=cam.buffer_seq[1];
        select_token(0,0);cmd(64,1);select_token(0,1);
        // Illegal width, strobe, SELECT, offset, read-only and combined commands: no ownership side effects.
        bus(1,44,2,2,15,1);bus(1,44,1,0,1,1);bus(1,56,1234,2,1,1);bus(1,0,0,2,15,1);
        bus(0,1,0,2,15,1);bus(0,64,0,2,15,1);cmd(96,1);cmd(4,1);cmd(8,1);cmd(1,1);
        bus(1,4,64,2,1,1);
        bus(0,44,0,2,15,0);if(got!=0)$fatal(1,"RESULT: FAIL invalid SELECT side effect");
        bus(0,56,0,2,15,0);if(got!=1)$fatal(1,"RESULT: FAIL invalid TOKEN side effect");
        epoch=9;repeat(3)frame(9,0);preserved(0,seq0,save0);preserved(1,seq1,save1);
        if(!cam.wait_free || cam.wait_cycles==0)$fatal(1,"RESULT: FAIL WAIT_FREE");
        $fdisplay(fd,"CASE FULL_WAIT_STABLE %0d %0d",cycle,cam.wait_cycles);
        fork
            frame(9,0);
            begin @(negedge vs);repeat(30)@(negedge pclk);cmd(64,0);if(vs)$fatal(1,"RESULT: FAIL unit release mid-frame coverage");end
        join
        wait(cam.run);select_token(1,2);
        fork
            frame(3,0);
            begin wait(cam.run && cam.done_sync[1] && cam.written_beats==512 && cam.dma_state==0);cmd(64,0);end
        join
        wait(cam.buffer_state[0]==2);select_token(0,3);cmd(32,0);save0=cam.buffer_crc[0];seq0=3;
        wait(cam.run && cam.active_buf==1);finalgate=0;
        fork
            frame(4,0);
            begin wait(cam.written_beats==511 && (pending || av));cmd(16,0);repeat(24)@(negedge clk);
                if(!cam.busy || cam.buffer_state[1]!=1 || cam.frame_seq!=3)$fatal(1,"RESULT: FAIL STOP published withheld final W");finalgate=1;
            end
        join
        until_idle();if(cam.frame_seq!=4 || cam.buffer_state[1]!=2 || cam.stream_enabled)$fatal(1,"RESULT: FAIL STOP drain");preserved(0,3,save0);
        $fdisplay(fd,"CASE STOP_DRAIN %0d",cycle);
        select_token(1,4);cmd(32,0);cmd(64,0);select_token(0,3);cmd(64,0);
        // STOP at an otherwise eligible auto-allocation edge must win.
        cmd(8,0);wait(cam.idle_count==15 && !cam.busy);cmd(16,0);repeat(20)@(negedge clk);
        if(cam.busy || cam.buffer_state[0]!=0 || cam.buffer_state[1]!=0)$fatal(1,"RESULT: FAIL STOP race");
        $fdisplay(fd,"CASE STOP_ALLOCATION_RACE %0d",cycle);
        cmd(4,0);cmd(8,0);warm();frame(5,0);wait(cam.buffer_state[0]==2);
        select_token(0,5);cmd(32,0);save0=cam.buffer_crc[0];
        wait(cam.run && cam.active_buf==1);awgate=0;wgate=0;
        fork
            frame(6,0);
            begin wait(av);cmd(2,0);repeat(20)@(negedge clk);
                if(!cam.busy || cam.buffer_state[1]!=1 || cam.frame_seq!=5)$fatal(1,"RESULT: FAIL ABORT discarded public AW");
                awgate=1;wait(pending);repeat(20)@(negedge clk);if(!cam.busy)$fatal(1,"RESULT: FAIL ABORT before W");wgate=1;
            end
        join
        until_idle();preserved(0,5,save0);if(cam.buffer_state[1]!=0 || cam.frame_seq!=5 || cam.error_code!=5)$fatal(1,"RESULT: FAIL ABORT preservation");
        $fdisplay(fd,"CASE ABORT_DRAIN_PRESERVE %0d",cycle);
        select_token(0,5);cmd(64,0);cmd(4,0);cmd(8,0);warm();frame(7,0);wait(cam.buffer_state[0]==2);
        select_token(0,6);cmd(32,0);save0=cam.buffer_crc[0];wait(cam.run);frame(8,1);until_idle();
        preserved(0,6,save0);if(cam.error_code!=3 || cam.frame_seq!=6 || cam.buffer_state[1]!=0)$fatal(1,"RESULT: FAIL short-frame stream");
        $fdisplay(fd,"CASE SHORT_FRAME_PRESERVE %0d",cycle);
        select_token(0,6);cmd(64,0);cmd(4,0);cmd(8,0);warm();frame(10,0);wait(cam.buffer_state[0]==2);
        select_token(0,7);cmd(32,0);save0=cam.buffer_crc[0];wait(cam.run);awgate=0;wgate=0;frame(11,0);
        wait(cam.overflow_latched);preserved(0,7,save0);if(!cam.busy || cam.buffer_state[1]!=1)$fatal(1,"RESULT: FAIL overflow drained without public AW");
        awgate=1;wgate=1;until_idle();if(cam.frame_seq!=7 || cam.error_code!=2)$fatal(1,"RESULT: FAIL overflow publish");
        $fdisplay(fd,"CASE OVERFLOW_PRESERVE %0d",cycle);
        select_token(0,7);cmd(64,0);cmd(4,0);cmd(8,0);wait(cam.run);dvp.clock_enable=0;
        wait(cam.error_latched);until_idle();if(cam.frame_seq!=7 || cam.error_code!=4)$fatal(1,"RESULT: FAIL missing PCLK timeout");
        $fdisplay(fd,"CASE MISSING_PCLK_TIMEOUT %0d",cycle);
        dvp.clock_enable=1;cmd(4,0);cmd(8,0);warm();frame(12,0);wait(cam.buffer_state[0]==2);
        select_token(0,8);cmd(32,0);wait(cam.run && cam.active_buf==1);
        if(cam.cpu_owned!=1 || cam.buffer_state[1]!=1)$fatal(1,"RESULT: FAIL reset coverage not CPU plus writer");
        rst=0;repeat(6)@(negedge clk);dvp.clock_enable=1;
        if(cam.dual_mode || cam.cpu_owned || cam.frame_seq || cam.buffer_state[0] || cam.buffer_state[1])$fatal(1,"RESULT: FAIL reset ownership");
        $fdisplay(fd,"CASE RESET_CLEAR %0d",cycle);
        wait(aperture_done);
        if(pubs!=8 || release_publish==0 || stop_race==0 || awstall==0 || wstall==0 || same==0 || separate==0)$fatal(1,"RESULT: FAIL unit coverage %0d/%0d/%0d",pubs,release_publish,stop_race);
        $fdisplay(fd,"COVER %0d %0d %0d %0d %0d %0d %0d",pubs,release_publish,stop_race,awstall,wstall,same,separate);$fflush(fd);
        $display("RESULT: PASS ABI2_OWNERSHIP_FAULTS_PERMISSIONS");$finish;
    end
    always @(negedge vs)if(rst && cam.run)$fdisplay(fd,"EDGE %0d",cycle);
    always @(negedge clk)if(rst && cycle%128==0)$fflush(fd);
    always @(posedge clk)begin
        cycle=cycle+1;
        if(!rst)begin pending<=0;held=0;wheld=0;end
        else begin
            if(av && !ar)awstall=awstall+1;if(pending && !ww)wstall=wstall+1;
            if(held && (!av || aa!==held_addr || wd!==held_data))$fatal(1,"RESULT: FAIL unit public AW unstable");
            held=av&&!ar;held_addr=aa;held_data=wd;
            if(wheld && wd!==held_w)$fatal(1,"RESULT: FAIL unit W data unstable");
            wheld=(pending || (av&&ar))&&!ww;held_w=wd;
            if(cam.release_cmd && cam.run && cam.done_sync[1] && cam.written_beats==512 && cam.dma_state==0)release_publish=release_publish+1;
            if(cam.stream_stop_cmd && cam.idle_count==15 && !cam.busy && cam.free_available && cam.stream_enabled)stop_race=stop_race+1;
            if(av && ar)begin wa<=aa;$fdisplay(fd,"AW %0d %0d %07h",epoch,cycle,aa);if(!ww)begin pending<=1;age<=0;separate=separate+1;end else same=same+1;end
            if((pending || (av&&ar)) && ww)begin
                b=cam.active_buf;wc[b]=wc[b]+1;lastw[b]=cycle;pending<=0;
                $fdisplay(fd,"W %0d %0d %07h %064h",epoch,cycle,pending?wa:aa,wd);
                if(cam.buffer_state[b]!=1)$fatal(1,"RESULT: FAIL DMA without WRITING");
            end else if(pending)age<=age+1;
            #0.001;
            for(b=0;b<2;b=b+1)begin
                if(cam.buffer_state[b]==1 && oldstate[b]!=1)begin wc[b]=0;$fdisplay(fd,"START %0d %0d %0d",cycle,b,cam.stream_warmed);end
                if(cam.buffer_state[b]==2 && oldstate[b]==1)begin
                    pubs=pubs+1;if(wc[b]!=512 || cycle<=lastw[b])$fatal(1,"RESULT: FAIL unit publication timing/count");
                    $fdisplay(fd,"PUB %0d %0d %0d %0d %08h %0d %0d",epoch,cycle,b,cam.buffer_seq[b],cam.buffer_crc[b],lastw[b],cam.u_capture.dropped);
                end
                if(cam.buffer_state[b]!=oldstate[b])$fdisplay(fd,"STATE %0d %0d %0d %0d",cycle,b,oldstate[b],cam.buffer_state[b]);
                oldstate[b]=cam.buffer_state[b];
            end
        end
    end
    initial begin #300000000;$fatal(1,"RESULT: FAIL unit deadline");end
endmodule
