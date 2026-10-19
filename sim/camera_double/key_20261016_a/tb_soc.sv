`timescale 1ns/1ps
`define C dut.g_camera.u_camera
`define S dut.u_soc
module tb_double_soc;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    reg refclk=0,resetn=0,uart_rx=1;always #4 refclk=~refclk;
    wire clk,rst,pclk,vs,href;wire[7:0]din;tri1 scl,sda;
    double_dvp dvp(.pclk(pclk),.vsync(vs),.href(href),.din(din));
    integer sw,sr;camera_sensor sensor(.resetn(rst),.scl(scl),.sda(sda),.injection(32'b0),.writes(sw),.reads(sr));
    soc_ddr3_top #(.ENABLE_CAMERA(1),.RESET_PC(32'h40000000),.CORE_CLK_HZ(93750000)) dut(
        .ddr_ref_clk(refclk),.resetn(resetn),.core_clk(clk),.soc_resetn(rst),
        .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),.uart_rx(uart_rx),
        .camera_pclk(pclk),.camera_vsync(vs),.camera_href(href),.camera_data(din),.camera_scl(scl),.camera_sda(sda));
    defparam dut.u_soc.INST_ROM_BASE=0,dut.u_soc.DATA_RAM_BASE=0;
    defparam dut.g_camera.u_camera.WIDTH=64,dut.g_camera.u_camera.HEIGHT=8;
    defparam dut.g_camera.u_camera.u_config.CLK_HZ=1600000;
    integer fd,i,cycle=0,pubs=0,phase=0,loads=0,overlap=0,overlap_w=0,release_mid=0;
    integer oldstate[0:1],lastw[0:1],wcount[0:1],loadcount[0:5];
    integer full_cycle,full_w,full_wait,aw_contention=0,boot_retired=0;reg[31:0]full_crc0,full_crc1;
    reg pending=0;reg[31:0]pa,pseq;integer pb;
    string path;
    task send_byte(input[7:0]value);
        integer j;
        begin
            @(negedge clk);uart_rx=0;repeat(814)@(negedge clk);
            for(j=0;j<8;j=j+1)begin uart_rx=value[j];repeat(814)@(negedge clk);end
            uart_rx=1;repeat(814)@(negedge clk);
            $fdisplay(fd,"UART_STIMULUS %0d %0d",cycle,value);
        end
    endtask
    initial begin
        if(!$value$plusargs("CPU=%s",path))$fatal(1,"RESULT: FAIL CPU path");fd=$fopen(path,"w");
        for(i=0;i<2;i=i+1)begin oldstate[i]=0;lastw[i]=-1;wcount[i]=0;end
        for(i=0;i<6;i=i+1)loadcount[i]=0;
        repeat(12)@(negedge refclk);resetn=1;
        wait(`C.run);repeat(10)@(negedge pclk);
        for(i=0;i<10;i=i+1)begin dvp.idle(12);@(negedge pclk);dvp.vsync=0;repeat(12)@(negedge pclk);dvp.idle(12);end
        dut.u_ddr3.epoch=1;dvp.frame(1,64,8,0);
        wait(phase==1);wait(`C.run && `C.active_buf==1);
        // A is CPU-owned. Synchronize through the real UART, never a cached DDR mailbox.
        fork
            begin dut.u_ddr3.epoch=2;dvp.frame(2,64,8,0);end
            begin @(negedge vs);wait(href);send_byte(1);end
        join
        wait(phase==2);wait(`C.cpu_owned==3);repeat(3)@(negedge clk);
        full_cycle=cycle;full_w=dut.u_ddr3.camera_writes[1]+dut.u_ddr3.camera_writes[2];full_wait=`C.wait_cycles;
        full_crc0=`C.buffer_crc[0];full_crc1=`C.buffer_crc[1];
        $fdisplay(fd,"FULL_BEGIN %0d %08h %08h",cycle,full_crc0,full_crc1);
        dut.u_ddr3.epoch=9;repeat(3)dvp.frame(9,64,8,0);
        if(`C.busy || !`C.wait_free || `C.wait_cycles<=full_wait || `C.buffer_crc[0]!=full_crc0 || `C.buffer_crc[1]!=full_crc1 ||
           `C.buffer_seq[0]!=1 || `C.buffer_seq[1]!=2 || dut.u_ddr3.camera_writes[9]!=0)$fatal(1,"RESULT: FAIL full buffers changed");
        fork
            dvp.frame(9,64,8,0);
            begin @(negedge vs);repeat(16)@(negedge pclk);send_byte(2);
                wait(`C.buffer_state[0]!=3);if(vs)$fatal(1,"RESULT: FAIL release was not mid-frame");release_mid=1;
                $fdisplay(fd,"FULL_END %0d",cycle);
            end
        join
        wait(`C.run);dut.u_ddr3.epoch=3;dvp.frame(3,64,8,0);
        wait(`C.run && `C.active_buf==1);dut.u_ddr3.epoch=4;dvp.frame(4,64,8,3);
        wait(!`C.stream_enabled);
        if(`C.busy)begin wait(`C.run);dut.u_ddr3.epoch=5;dvp.frame(5,64,8,0);end
        wait(`S.selftest_status==2 || `S.selftest_status==3);repeat(8)@(negedge clk);
        if(`S.selftest_status!=2 || pubs<4 || loads<1024 || overlap==0 || overlap_w==0 || aw_contention==0 || !release_mid || `C.cpu_owned || `C.busy || `C.stream_enabled)
            $fatal(1,"RESULT: FAIL CPU coverage pubs=%0d loads=%0d overlap=%0d/%0d",pubs,loads,overlap,overlap_w);
        for(i=1;i<=pubs;i=i+1)if(loadcount[i]!=256)$fatal(1,"RESULT: FAIL incomplete real CPU full read %0d %0d",i,loadcount[i]);
        $fdisplay(fd,"COVER %0d %0d %0d %0d %0d %0d",pubs,loads,overlap,overlap_w,release_mid,aw_contention);
        $fflush(fd);$fflush(dut.u_ddr3.logfd);$display("RESULT: PASS ABI2_SMALL_REAL_CPU");$finish;
    end
    integer b,off;reg[31:0]old_crc[0:1],old_seq[0:1];
    always @(negedge clk)if(rst && cycle%128==0)begin $fflush(fd);$fflush(dut.u_ddr3.logfd);end
    always @(negedge vs)if(rst && `C.run)$fdisplay(fd,"EDGE %0d",cycle);
    always @(posedge clk)if(rst)begin
        cycle=dut.u_ddr3.cycle;
        if(`S.selftest_status==3)begin $fflush(fd);$fflush(dut.u_ddr3.logfd);$fatal(1,"RESULT: FAIL CPU software diagnostic");end
        if(dut.cpu_awvalid && dut.cam_awvalid)begin aw_contention=aw_contention+1;$fdisplay(fd,"CONTEND %0d",cycle);end
        if(`S.u_cpu.normal_retire && boot_retired<16)begin
            if(boot_retired==0 && (`S.debug_wb_pc!=32'h40000000 || `S.debug_inst!=32'h30047073))$fatal(1,"RESULT: FAIL sealed CPU entry");
            $fdisplay(fd,"RETIRE %0d %08h %08h",cycle,`S.debug_wb_pc,`S.debug_inst);boot_retired=boot_retired+1;
        end
        if(`S.u_cpu.sync_trap_event)begin
            $fdisplay(fd,"TRAP %0d %08h %08h %0d %08h",cycle,`S.debug_wb_pc,`S.debug_inst,`S.u_cpu.wb_trap_cause,`S.u_cpu.wb_trap_tval);
            $fflush(fd);$fatal(1,"RESULT: FAIL real CPU trap");
        end
        if(`S.data_req_valid && `S.data_req_ready && `S.data_req_write && `S.data_req_addr==32'h10000000)begin
            $fdisplay(fd,"REPORT %0d %08h",cycle,`S.data_req_wdata);
            if(`S.data_req_wdata[31:28]==12)phase=`S.data_req_wdata[3:0];
        end
        if(`C.dma_awvalid && `C.dma_awready)$fdisplay(fd,"CAM_AW %0d %07h",cycle,`C.dma_awaddr);
        if(`C.dma_complete)begin
            b=`C.active_buf;lastw[b]=cycle;wcount[b]=wcount[b]+1;
            if(`C.cpu_owned[!b] && pending)overlap_w=overlap_w+1;
        end
        if(`S.data_rsp_valid && pending)begin
            if(`S.data_rsp_error)$fatal(1,"RESULT: FAIL owned frame read error");
            $fdisplay(fd,"LOAD %0d %0d %0d %08h %08h",cycle,pb,pseq,pa,`S.data_rsp_rdata);
            loads=loads+1;loadcount[pseq]=loadcount[pseq]+1;pending=0;
        end
        if(`S.data_req_valid && `S.data_req_ready && !`S.data_req_write && `S.data_req_addr>=32'h41000000 && `S.data_req_addr<32'h41400000)begin
            if(pending)$fatal(1,"RESULT: FAIL duplicate pending CPU load");
            pa=`S.data_req_addr;pb=pa[21];pseq=`C.buffer_seq[pb];pending=1;
            if(!`C.cpu_owned[pb])$fatal(1,"RESULT: FAIL read without CPU ownership");
            if(`C.busy && `C.active_buf!=pb)overlap=overlap+1;
        end
        #0.001;
        for(b=0;b<2;b=b+1)begin
            if(`C.buffer_state[b]==2 && oldstate[b]==1)begin
                if(wcount[b]!=32 || cycle<=lastw[b])$fatal(1,"RESULT: FAIL publish before actual final W");
                pubs=pubs+1;
                $fdisplay(fd,"PUB %0d %0d %0d %08h %0d %0d",cycle,b,`C.buffer_seq[b],`C.buffer_crc[b],lastw[b],`C.u_capture.dropped);
            end
            if(`C.buffer_state[b]==1 && oldstate[b]!=1)begin wcount[b]=0;$fdisplay(fd,"START %0d %0d %0d",cycle,b,`C.stream_warmed);end
            if((oldstate[b]==2 || oldstate[b]==3) && (`C.buffer_state[b]==2 || `C.buffer_state[b]==3) &&
               (`C.buffer_crc[b]!=old_crc[b] || `C.buffer_seq[b]!=old_seq[b]))$fatal(1,"RESULT: FAIL owned metadata changed");
            if(`C.buffer_state[b]!=oldstate[b])$fdisplay(fd,"STATE %0d %0d %0d %0d",cycle,b,oldstate[b],`C.buffer_state[b]);
            oldstate[b]=`C.buffer_state[b];old_crc[b]=`C.buffer_crc[b];old_seq[b]=`C.buffer_seq[b];
        end
    end
    initial begin #300000000;$fatal(1,"RESULT: FAIL small CPU simulation deadline");end
endmodule
