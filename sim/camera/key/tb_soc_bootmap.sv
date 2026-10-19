`timescale 1ns/1ps
`define SOC dut.u_soc
`define CAM dut.g_camera.u_camera
`define BR dut.u_soc.g_ddr.u_ddr_bridge
module tb_camera_soc_bootmap;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    reg refclk=0,resetn=0;
    always #4 refclk=~refclk;
    wire clk,soc_resetn;
    wire pclk,vs,href;
    wire[7:0]din;
    camera_dvp dvp(.pclk(pclk),.vsync(vs),.href(href),.din(din));
    tri1 scl,sda;
    integer inj=0,writes,reads;
    camera_sensor sensor(.resetn(soc_resetn),.scl(scl),.sda(sda),.injection(inj),.writes(writes),.reads(reads));
    soc_ddr3_top #(.ENABLE_CAMERA(1),.RESET_PC(32'h40000000),.CORE_CLK_HZ(93750000)) dut(
        .ddr_ref_clk(refclk),.resetn(resetn),.irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .camera_pclk(pclk),.camera_vsync(vs),.camera_href(href),.camera_data(din),
        .camera_scl(scl),.camera_sda(sda),.camera_resetn(),.core_clk(clk),.soc_resetn(soc_resetn),
        .uart_rx(1'b1),.uart_tx());
    // Only SCCB/config delay is accelerated; geometry, FIFO, DMA, clocks, CPU/caches unchanged.
    defparam dut.g_camera.u_camera.u_config.CLK_HZ=1600000;
    // Keep the on-chip memories at zero while this simulation boots from DDR.
    defparam dut.u_soc.INST_ROM_BASE=32'h00000000;
    defparam dut.u_soc.DATA_RAM_BASE=32'h00000000;
    initial begin
        #0.001;
        if (`SOC.RESET_PC!=32'h40000000 || `SOC.INST_ROM_BASE!=0 || `SOC.DATA_RAM_BASE!=0)
            $fatal(1,"RESULT: FAIL test boot map parameters");
        $display("BOOTMAP reset=%08h rom=%08h ram=%08h",`SOC.RESET_PC,`SOC.INST_ROM_BASE,`SOC.DATA_RAM_BASE);
    end
    integer boot_printed=0;
    integer arms=0,done_count=0,cycle=0,fd,p,d;
    integer cpu_frame_reads[0:2],frame_ars[0:2];
    integer contention=0,aw_stalls=0,w_stalls=0,same=0,separate=0,crc_reports=0;
    reg done_old=0,cpu_pending=0;
    reg [31:0] pending_addr;
    reg [31:0] mmio_crc;
    reg [7:0] exp1[0:1843199],exp2[0:1843199];
    string path;
    initial begin
        if(!$value$plusargs("CPU=%s",path))$fatal(1,"RESULT: FAIL CPU log path");
        fd=$fopen(path,"w");if(!fd)$fatal(1,"RESULT: FAIL CPU log open");
        if(!$value$plusargs("FRAME1=%s",path))$fatal(1,"RESULT: FAIL FRAME1");$readmemh(path,exp1);
        if(!$value$plusargs("FRAME2=%s",path))$fatal(1,"RESULT: FAIL FRAME2");$readmemh(path,exp2);
        for(p=0;p<3;p=p+1)begin cpu_frame_reads[p]=0;frame_ars[p]=0;end
        repeat(12)@(negedge refclk);resetn=1;
        for(p=1;p<=2;p=p+1)begin
            wait(arms==p);wait(`CAM.run);
            repeat(10)@(negedge pclk);
            // Exercise default ten-frame discard without spending pixels on discarded frames.
            for(d=0;d<10;d=d+1)begin
                dvp.idle(12);@(negedge pclk);dvp.vsync=0;
                repeat(12)@(negedge pclk);dvp.idle(12);
            end
            dvp.frame(p,1280,720,p==2 ? 3 : 0);
            wait(!`CAM.busy);
            if(!`CAM.frame_done)$fatal(1,"RESULT: FAIL full capture error=%0d",`CAM.error_code);
        end
        wait(`SOC.selftest_status==2 || `SOC.selftest_status==3);
        repeat(10)@(negedge clk);
        if(`SOC.selftest_status!=2 || arms!=2 || done_count!=2 || crc_reports!=2 ||
           cpu_frame_reads[0]!=3 || cpu_frame_reads[1]!=460803 || cpu_frame_reads[2]!=460800 ||
           frame_ars[0]!=3 || frame_ars[1]!=460803 || frame_ars[2]!=460800 ||
           contention==0 || aw_stalls==0 || w_stalls==0 || same==0 || separate==0)
            $fatal(1,"RESULT: FAIL SoC coverage/status arms=%0d done=%0d crc=%0d reads=%0d/%0d/%0d ar=%0d/%0d/%0d",
                arms,done_count,crc_reports,cpu_frame_reads[0],cpu_frame_reads[1],cpu_frame_reads[2],frame_ars[0],frame_ars[1],frame_ars[2]);
        $fdisplay(fd,"COVER %0d %0d %0d %0d %0d %0d",contention,aw_stalls,w_stalls,same,separate,crc_reports);
        $fflush(fd);$fflush(dut.u_ddr3.logfd);
        $display("RESULT: PASS camera_soc_two_full_frames");$finish;
    end
    reg expected_valid=0;
    reg[31:0] expected_data;
    reg expected_error;
    integer off,b;
    reg[31:0] want;
    always @(posedge clk)begin
        if(!soc_resetn)begin
            expected_valid=0;cpu_pending=0;done_old=0;
        end else begin
            cycle=dut.u_ddr3.cycle;
            // Check the added response register as a transaction, not just valid latency.
            if(`SOC.data_ddr_rsp_valid!==expected_valid)$fatal(1,"RESULT: FAIL response register valid");
            if(expected_valid && {`SOC.data_ddr_rsp_error,`SOC.data_ddr_rsp_rdata}!=={expected_error,expected_data})
                $fatal(1,"RESULT: FAIL response register data/error");
            expected_valid=`SOC.g_ddr.bridge_data_rsp_valid;
            expected_data=`SOC.g_ddr.bridge_data_rsp_rdata;expected_error=`SOC.g_ddr.bridge_data_rsp_error;
            if (`SOC.inst_req_valid && `SOC.inst_req_ready && `SOC.inst_req_addr==32'h40000000) begin
                if (`SOC.rom_bus_req_valid || !`SOC.inst_ddr_req_valid)
                    $fatal(1,"RESULT: FAIL entry instruction did not route to DDR");
            end
            if (`SOC.data_req_valid && `SOC.data_req_ready && `SOC.data_req_write &&
                `SOC.data_req_addr>=32'h00001000 && `SOC.data_req_addr<32'h00001400) begin
                if (!`SOC.ram_bus_req_valid || `SOC.data_ddr_req_valid)
                    $fatal(1,"RESULT: FAIL CRC table write did not route to on-chip RAM");
            end
            if (`SOC.u_cpu.normal_retire && boot_printed<16) begin
                $display("BOOT_RETIRE cycle=%0d pc=%08h inst=%08h",cycle,`SOC.debug_wb_pc,`SOC.debug_inst);
                if (boot_printed==0 && (`SOC.debug_wb_pc!=32'h40000000 || `SOC.debug_inst!=32'h10002437))
                    $fatal(1,"RESULT: FAIL first retired instruction differs from sealed DDR CPU image");
                boot_printed=boot_printed+1;
            end
            if (`SOC.u_cpu.sync_trap_event) begin
                $display("TRAP cycle=%0d pc=%08h inst=%08h cause=%0d tval=%08h target=%08h current_bus_addr=%08h",
                    cycle,`SOC.debug_wb_pc,`SOC.debug_inst,`SOC.u_cpu.wb_trap_cause,
                    `SOC.u_cpu.wb_trap_tval,`SOC.u_cpu.csr_trap_target,`SOC.data_req_addr);
                $fflush(fd);$fflush(dut.u_ddr3.logfd);
                $fatal(1,"RESULT: FAIL CPU trap");
            end
            if(`SOC.data_rsp_valid && cpu_pending)begin
                if(`SOC.data_rsp_error)$fatal(1,"RESULT: FAIL CPU frame read error");
                off=pending_addr-32'h41000000;want=0;
                for(b=0;b<4;b=b+1)begin
                    if(arms==0)want[b*8+:8]=32'hdeadbeef >> ((off+b)%4)*8;
                    else want[b*8+:8]=(arms==1?exp1[off+b]:exp2[off+b]);
                end
                if(`SOC.data_rsp_rdata!==want)$fatal(1,"RESULT: FAIL CPU frame data addr=%h got=%h want=%h",pending_addr,`SOC.data_rsp_rdata,want);
                cpu_frame_reads[arms]=cpu_frame_reads[arms]+1;
                $fdisplay(fd,"LOAD %0d %0d %08h %08h",arms,cycle,pending_addr,`SOC.data_rsp_rdata);
                cpu_pending=0;
            end
            if(`SOC.data_req_valid && `SOC.data_req_ready && !`SOC.data_req_write &&
               `SOC.data_req_addr>=32'h41000000 && `SOC.data_req_addr<32'h411c2000)begin
                if(cpu_pending || `CAM.busy)$fatal(1,"RESULT: FAIL CPU frame request ownership");
                cpu_pending=1;pending_addr=`SOC.data_req_addr;
            end
            if(dut.axi_arvalid && dut.axi_arready && dut.axi_araddr>=28'h400000 && dut.axi_araddr<28'h470800)
                frame_ars[arms]=frame_ars[arms]+1;
            if((`BR.camera_data_addr && `BR.data_line_hit) || (`BR.camera_fill_addr && `BR.data_line_fill))
                $fatal(1,"RESULT: FAIL frame cache hit/fill");
            if(dut.cpu_awvalid && dut.cam_awvalid)contention=contention+1;
            if(dut.axi_awvalid && !dut.axi_awready)aw_stalls=aw_stalls+1;
            if(dut.u_ddr3.writing && !dut.axi_wready)w_stalls=w_stalls+1;
            if(dut.axi_awvalid && dut.axi_awready)begin if(dut.axi_wready)same=same+1;else separate=separate+1;end
            if(dut.cam_req_valid && dut.cam_req_ready && dut.cam_req_write && dut.cam_req_addr==4 && dut.cam_req_wdata==1)begin
                arms=arms+1;dut.u_ddr3.epoch=arms;
                $fdisplay(fd,"ARM %0d %0d",arms,cycle);
            end
            if(`CAM.frame_done && !done_old)begin
                if(arms<1 || arms>2 || dut.u_ddr3.camera_writes[arms]!=57600 || dut.u_ddr3.writing ||
                   `CAM.frame_seq!=arms || `CAM.frame_bytes!=1843200 || `CAM.pixel_count!=921600)
                    $fatal(1,"RESULT: FAIL DONE before actual final W or metadata");
                done_count=done_count+1;
                $fdisplay(fd,"DONE %0d %0d %0d %08h %0d %0d %0d",arms,cycle,dut.u_ddr3.last_write[arms],
                    `CAM.frame_crc32,`CAM.frame_bytes,`CAM.pixel_count,`CAM.frame_seq);
            end
            done_old=`CAM.frame_done;
            if(`SOC.mmio_req_valid && `SOC.mmio_req_ready && `SOC.mmio_req_write)begin
                $fdisplay(fd,"MMIO %0d %0d %03h %08h",arms,cycle,`SOC.mmio_req_addr,`SOC.mmio_req_wdata);
                if(`SOC.mmio_req_addr==0 && `SOC.mmio_req_wdata>2)begin
                    mmio_crc=`SOC.mmio_req_wdata;crc_reports=crc_reports+1;
                    $display("CPU_CRC %0d %08h",arms,mmio_crc);
                end
            end
            if(cycle%10000000==0)$display("PROGRESS cycle=%0d arms=%0d frame_reads=%0d",cycle,arms,cpu_frame_reads[arms]);
            if(cycle>250000000)$fatal(1,"RESULT: FAIL SoC cycle timeout");
        end
    end
endmodule
