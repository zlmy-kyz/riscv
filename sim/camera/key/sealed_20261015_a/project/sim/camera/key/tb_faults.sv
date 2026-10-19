`timescale 1ns/1ps
module tb_camera_faults;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    wire arb_done,aperture_done;
    camera_aperture_unit aperture_test(.done(aperture_done));
    camera_arbiter_unit arb_test(.done(arb_done));
    reg clk=0,resetn=0;
    always #5.333 clk=~clk;
    wire pclk,vs,href;
    wire [7:0] din;
    camera_dvp dvp(.pclk(pclk),.vsync(vs),.href(href),.din(din));
    tri1 scl,sda;
    wire sl,dl,sn,busy,ready,rv,re,av;
    wire [31:0] rd;
    wire [27:0] aa;
    wire [255:0] wd;
    reg req=0,write=0;
    reg [31:0] addr=0,data=0;
    reg [3:0] strobe=15;
    integer inj=0,writes,reads,which=0,cycle=0,aw_wait=0,wait_w=0,beats=0;
    integer same=0,late=0,hold_last=0;
    reg pending=0;
    reg [27:0] saved_addr;
    wire awready=av && which!=3 && which!=6 && which!=7 && aw_wait>=3;
    wire wready=(pending || (av && awready)) && which!=2 && which!=4 && which!=5 &&
                 (which==0 ? (beats==1023 ? hold_last>=80 : cycle%5!=0) : wait_w>=5);
    camera_mmio #(.WIDTH(128),.HEIGHT(128),.DROP_FRAMES(0)) cam(
        .clk(clk),.resetn(resetn),.busy(busy),.req_valid(req),.req_write(write),.req_size(2'd2),
        .req_addr(addr),.req_wdata(data),.req_wstrb(strobe),.req_ready(ready),.rsp_valid(rv),
        .rsp_error(re),.rsp_rdata(rd),.pclk(pclk),.vsync(vs),.href(href),.din(din),
        .scl_in(scl),.sda_in(sda),.scl_low(sl),.sda_low(dl),.sensor_resetn(sn),
        .dma_awvalid(av),.dma_awaddr(aa),.dma_wdata(wd),.dma_awready(awready),.dma_wready(wready));
    defparam cam.u_config.CLK_HZ=1600000;
    assign scl=sl?1'b0:1'bz;assign sda=dl?1'b0:1'bz;
    camera_sensor sensor(.resetn(resetn),.scl(scl),.sda(sda),.injection(inj),.writes(writes),.reads(reads));
    task automatic access(input integer wr,off,value,expect_error,output reg[31:0] result);
        begin
            @(negedge clk);req=1;write=wr;addr=off;data=value;
            do @(posedge clk);while(!ready);
            @(negedge clk);req=0;
            wait(rv);#0.001;
            if(re!==expect_error[0]) $fatal(1,"RESULT: FAIL MMIO error off=%h",off);
            result=rd;
            $display("UNIT_MMIO %0t %0d %0d %02h %08h %0d %08h",$time,which,wr,off,value,re,rd);
            @(negedge clk);
        end
    endtask
    reg [31:0] value;
    task automatic reset_config;
        begin
            @(negedge clk);resetn=0;
            repeat(8) @(negedge clk);
            resetn=1;
            wait(cam.config_done || cam.config_error);
            if(cam.config_error) $fatal(1,"RESULT: FAIL fault test configuration");
        end
    endtask
    task automatic arm;
        begin
            beats=0;pending=0;aw_wait=0;wait_w=0;hold_last=0;
            $display("ARMU %0d",which);
            access(1,4,1,0,value);
            wait(cam.run);repeat(8) @(negedge pclk);
        end
    endtask
    task automatic invalid_result(input integer code);
        begin
            repeat(100) @(negedge clk);
            if(cam.frame_done || cam.frame_bytes || cam.pixel_count || cam.frame_crc32 ||
               !cam.error_latched || cam.error_code!=code || cam.frame_seq!=1)
                $fatal(1,"RESULT: FAIL invalid-frame metadata case=%0d",which);
            $display("CASE FAULT %0d %0d %0d %0d",which,beats,cam.error_code,busy);
        end
    endtask
    initial begin
        wait(arb_done && aperture_done);reset_config;
        which=0;arm;
        access(1,4,1,1,value); // repeated ARM while busy must be rejected
        dvp.frame(1,128,128,3);wait(!busy);
        if(!cam.frame_done || cam.frame_seq!=1 || cam.frame_bytes!=32768 || cam.pixel_count!=16384 || beats!=1024)
            $fatal(1,"RESULT: FAIL normal reduced capture");
        $display("CASE FAULT 0 %0d 0 0",beats);
        access(1,4,4,0,value);
        which=1;arm;dvp.frame(1,128,128,1);wait(!busy);invalid_result(3);
        which=2;arm;dvp.frame(1,128,128,0);wait(cam.overflow_sync[1]);
        if(!cam.overflow_latched) repeat(10) @(negedge clk);
        repeat(100) @(negedge clk);
        if(!busy || !pending || !cam.error_latched || cam.error_code!=2 ||
           cam.frame_done || cam.frame_bytes || cam.pixel_count || cam.frame_crc32)
            $fatal(1,"RESULT: FAIL overflow lost pending write or reported completion");
        $display("OVERFLOW_PENDING %0d %0d",beats,cam.error_code);
        // Release the already accepted W after overflow, then wait for safe idle.
        which=8;wait(!busy);which=2;invalid_result(2);
        which=3;arm;
        fork
            dvp.frame(1,128,128,0);
            begin wait(av);repeat(8) @(negedge clk);access(1,4,2,0,value);
                repeat(20) @(negedge clk);
                if(!busy || !av) $fatal(1,"RESULT: FAIL ABORT withdrew public AW");
                which=8;wait(!busy);which=3;invalid_result(5);
            end
        join
        which=4;arm;
        fork
            dvp.frame(1,128,128,0);
            begin wait(pending);access(1,4,2,0,value);
                repeat(20) @(negedge clk);
                if(!busy || !pending) $fatal(1,"RESULT: FAIL ABORT before W drain");
                which=8;wait(!busy);which=4;invalid_result(5);
            end
        join
        // Reset cancels in-flight work, with PCLK continuing; no stale DONE afterwards.
        which=5;arm;
        fork
            dvp.frame(1,128,128,0);
            begin wait(pending);@(negedge clk);resetn=0;repeat(8) @(negedge clk);resetn=1;end
        join
        repeat(100) @(negedge clk);
        if(busy || cam.frame_done || cam.frame_seq || cam.frame_bytes || cam.frame_crc32)
            $fatal(1,"RESULT: FAIL reset W stale result");
        $display("CASE FAULT 5 %0d 0 0",beats);
        wait(cam.config_done);
        which=6;arm;
        fork
            dvp.frame(1,128,128,0);
            begin wait(av);@(negedge clk);resetn=0;repeat(8) @(negedge clk);resetn=1;end
        join
        repeat(100) @(negedge clk);
        if(busy || cam.frame_done || cam.frame_seq || cam.frame_bytes || cam.frame_crc32)
            $fatal(1,"RESULT: FAIL reset AW stale result");
        $display("CASE FAULT 6 %0d 0 0",beats);
        wait(cam.config_done);
        which=7;arm;
        fork
            dvp.frame(1,128,128,0);
            begin wait(av);access(1,4,2,0,value);repeat(300) @(negedge clk);
                if(!busy || !av || cam.frame_done || !cam.error_latched || cam.error_code!=5 ||
                   cam.frame_bytes || cam.pixel_count || cam.frame_crc32)
                    $fatal(1,"RESULT: FAIL stuck abort false completion");end
        join
        $display("CASE FAULT 7 %0d 5 1",beats);
        @(negedge clk);resetn=0;
        if(same==0 || late==0) $fatal(1,"RESULT: FAIL write timing coverage");
        $display("FAULT_TIMING %0d %0d",same,late);
        $display("RESULT: PASS camera_faults");$finish;
    end
    always @(negedge clk) cycle=cycle+1;
    reg held=0;
    reg [283:0] fields;
    always @(posedge clk) begin
        if(!resetn) begin pending<=0;held=0;end
        else begin
            
            if(held && {aa,wd}!==fields) $fatal(1,"RESULT: FAIL camera AW/W changed while stalled");
            held=(av && !awready) || (pending && !wready);fields={aa,wd};
            if(av && !awready) aw_wait<=aw_wait+1;
            if(av && awready) begin
                if(pending || aa!=28'h400000+beats*8) $fatal(1,"RESULT: FAIL DMA address/order");
                saved_addr=aa;pending<=1;aw_wait<=0;
                if(wready) same=same+1;else late=late+1;
            end
            if(pending && !wready) wait_w<=wait_w+1;
            if(pending && beats==1023 && !wready) begin
                hold_last<=hold_last+1;
                if(cam.frame_done) $fatal(1,"RESULT: FAIL DONE before held last W");
            end
            if(wready) begin
                if(!(pending || (av && awready))) $fatal(1,"RESULT: FAIL orphan W");
                $display("CAMW %0d %0d %07h %064h",which,beats,saved_addr,wd);
                beats<=beats+1;pending<=0;wait_w<=0;
            end
            if(cam.frame_done && (cam.written_beats!=1024 || pending || av))
                $fatal(1,"RESULT: FAIL premature DONE");
        end
    end
    initial begin #300000000; $fatal(1,"RESULT: FAIL faults timeout"); end
endmodule
