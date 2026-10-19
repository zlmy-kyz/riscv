`timescale 1ns/1ps
module tb_data_bus_turnover #(parameter TURNOVER=1);
    GTP_GRS GRS_INST (.GRS_N(1'b1));
    reg clk=0;
    always #5.333 clk=~clk;
    wire unit_done;
    data_turnover_unit #(.TURNOVER(TURNOVER)) unit_test(.clk(clk),.done(unit_done));
    reg resetn=0,done=0;
    wire [27:0] aa,ra;
    wire av,arv,ardy,rrdy,wrdy,rvalid;
    wire [255:0] wd,rd;
    wire [31:0] ws;
    wire [3:0] awid,arid,awlen,arlen;
    wire awap,arap;
    reg [3:0] rid=0;
    wire [31:0] pc,ins,value;
    wire [3:0] we;
    wire [4:0] regno;
    wire [1:0] status;
    wire uart;
    soc_top #(.RESET_PC(32'h40000000),.INST_ROM_BASE(0),.DATA_RAM_BASE(0),
        .ENABLE_DDR(1),.DDR_MEM_DQ_WIDTH(32),.PERF_AUTO_ARM(0)) soc(
        .clk(clk),.resetn(resetn),.irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .debug_wb_pc(pc),.debug_wb_rf_we(we),.debug_wb_rf_wnum(regno),.debug_wb_rf_wdata(value),.debug_inst(ins),
        .ddr_init_done(resetn),.ddr_axi_awaddr(aa),.ddr_axi_awuser_ap(awap),.ddr_axi_awuser_id(awid),.ddr_axi_awlen(awlen),
        .ddr_axi_awready(ardy),.ddr_axi_awvalid(av),.ddr_axi_wdata(wd),.ddr_axi_wstrb(ws),
        .ddr_axi_wready(wrdy),.ddr_axi_wusero_id(4'd1),.ddr_axi_wusero_last(wrdy),
        .ddr_axi_araddr(ra),.ddr_axi_aruser_ap(arap),.ddr_axi_aruser_id(arid),.ddr_axi_arlen(arlen),
        .ddr_axi_arready(rrdy),.ddr_axi_arvalid(arv),.ddr_axi_rdata(rd),.ddr_axi_rid(rid),
        .ddr_axi_rlast(rvalid),.ddr_axi_rvalid(rvalid),.selftest_status(status),.uart_rx(1'b1),.uart_tx(uart));
    // Select the existing interconnect parameter; no SoC/CPU/bridge source edits.
    defparam soc.u_data_bus_interconnect.RESPONSE_TURNOVER_ENABLE=TURNOVER;
    mini_ddr_model_x32 memory_model(.clk(clk),.resetn(resetn),.awaddr(aa),.araddr(ra),
        .awvalid(av),.arvalid(arv),.awready(ardy),.arready(rrdy),.wready(wrdy),
        .wdata(wd),.wstrb(ws),.rdata(rd),.rvalid(rvalid));
    always @(posedge clk) if(resetn && arv && rrdy) rid<=arid;
    integer ev_fd,bus_fd,cycles=0,events=0,turns=0,mem_wait=0,faults=0,error_responses=0;
    integer mmio_count=0,uart_count=0,ram_count=0,fence_count=0,fence_wait=0,aw_count=0,w_count=0;
    reg [27:0] write_address=0;
    string ev_path,bus_path;
    initial begin
        if(!$value$plusargs("EV_LOG=%s",ev_path) || !$value$plusargs("BUS_LOG=%s",bus_path))
            $fatal(1,"RESULT: FAIL missing SoC trace paths");
        ev_fd=$fopen(ev_path,"w");bus_fd=$fopen(bus_path,"w");
        if(!ev_fd || !bus_fd) $fatal(1,"RESULT: FAIL SoC trace open");
        wait(unit_done);
        @(negedge clk);resetn=1;
        wait(done);
        @(negedge clk);
        if(status!=2 || faults!=1 || error_responses!=1 || aw_count!=5 || w_count!=5 || fence_wait==0 ||
           mmio_count!=5 || uart_count!=1 || ram_count!=1 || fence_count!=1 ||
           (TURNOVER ? turns==0 : turns!=0))
            $fatal(1,"RESULT: FAIL SoC coverage/status turns=%0d mmio=%0d uart=%0d ram=%0d fence=%0d AW=%0d W=%0d faults=%0d",
                turns,mmio_count,uart_count,ram_count,fence_count,aw_count,w_count,faults);
        $display("SOC: cycles=%0d events=%0d turns=%0d mem_wait=%0d fault=%0d error_rsp=%0d mmio=%0d uart=%0d ram=%0d fence=%0d fence_wait=%0d aw=%0d w=%0d",
            cycles,events,turns,mem_wait,faults,error_responses,mmio_count,uart_count,ram_count,fence_count,fence_wait,aw_count,w_count);
        $display("RESULT: PASS data_bus_turnover key_group TURNOVER=%0d",TURNOVER);
        $fflush(ev_fd);$fflush(bus_fd);$finish;
    end
    initial begin repeat(100000) @(posedge clk);$fatal(1,"RESULT: FAIL test cycle timeout");end
    always @(posedge clk) if(resetn && !done) begin
        cycles=cycles+1;
        if(soc.u_cpu.perf_events[3]) mem_wait=mem_wait+1;
        if(soc.u_cpu.if_id_valid && soc.u_cpu.inst_fence && soc.ddr_write_buffer_busy) fence_wait=fence_wait+1;
        if(soc.data_rsp_valid) begin
            $fdisplay(bus_fd,"CPU_RSP %0d %08h %0d",cycles,soc.data_rsp_rdata,soc.data_rsp_error);
            if(soc.data_rsp_error) begin
                error_responses=error_responses+1;
                if(soc.data_req_valid || soc.data_req_ready)
                    $fatal(1,"RESULT: FAIL younger CPU request on old error edge");
            end
        end
        if(rvalid) $fdisplay(bus_fd,"R %0d %0d %064h",cycles,rid,rd);
        if(av && ardy) begin
            if(awid!=1 || awlen!=0 || awap) $fatal(1,"RESULT: FAIL AW attributes");
            write_address=aa;aw_count=aw_count+1;
            $fdisplay(bus_fd,"AW %0d %07h %064h %08h",cycles,aa,wd,ws);
        end
        if(wrdy) begin
            w_count=w_count+1;
            $fdisplay(bus_fd,"W %0d %07h %064h %08h",cycles,write_address,wd,ws);
        end
        if(arv && rrdy) begin
            if(arlen!=0 || arap || arid>1) $fatal(1,"RESULT: FAIL AR attributes");
            $fdisplay(bus_fd,"AR %0d %07h %0d",cycles,ra,arid);
        end
        if(soc.data_req_valid && soc.data_req_ready) begin
            $fdisplay(bus_fd,"CPU_REQ %0d %0d %0d %08h %08h %01h",cycles,
                soc.data_req_write,soc.data_req_size,soc.data_req_addr,soc.data_req_wdata,soc.data_req_wstrb);
            if(soc.data_rsp_valid) begin
                turns=turns+1;
                $fdisplay(bus_fd,"TURN %0d",cycles);
            end
            if(soc.data_req_write && soc.data_req_addr==32'h40000808)
                $fatal(1,"RESULT: FAIL younger store escaped precise access fault");
        end
        if(soc.mmio_req_valid && soc.mmio_req_ready) begin
            if(soc.ddr_write_buffer_busy) $fatal(1,"RESULT: FAIL MMIO before write drain");
            if(soc.mmio_req_write) mmio_count=mmio_count+1;
            $fdisplay(bus_fd,"SIDE %0d MMIO %0d",cycles,soc.ddr_write_buffer_busy);
        end
        if(soc.uart_req_valid && soc.uart_req_ready) begin
            uart_count=uart_count+1;
            if(soc.ddr_write_buffer_busy) $fatal(1,"RESULT: FAIL UART before write drain");
            $fdisplay(bus_fd,"SIDE %0d UART %0d",cycles,soc.ddr_write_buffer_busy);
        end
        if(soc.ram_bus_req_valid && soc.ram_bus_req_ready) begin
            if(soc.ram_bus_req_write) ram_count=ram_count+1;
            if(soc.ddr_write_buffer_busy) $fatal(1,"RESULT: FAIL RAM before write drain");
            $fdisplay(bus_fd,"SIDE %0d RAM %0d",cycles,soc.ddr_write_buffer_busy);
        end
        if(soc.u_cpu.serial_issue && soc.u_cpu.inst_fence) begin
            fence_count=fence_count+1;
            if(soc.ddr_write_buffer_busy) $fatal(1,"RESULT: FAIL FENCE before write drain");
            $fdisplay(bus_fd,"FENCE %0d %0d",cycles,soc.ddr_write_buffer_busy);
        end
        if(soc.u_cpu.irq_take || soc.u_cpu.mret_commit) $fatal(1,"RESULT: FAIL unexpected IRQ/MRET");
        if(soc.u_cpu.sync_trap_event) begin
            faults=faults+1;
            $fdisplay(ev_fd,"EV %0d T %08h %08h %01h %0d %08h %08h %08h %08h",events,
                pc,ins,we,we ? regno : 5'b0,we ? value : 32'b0,
                {27'b0,soc.u_cpu.wb_trap_cause},soc.u_cpu.wb_trap_tval,soc.u_cpu.csr_trap_target);
            events=events+1;
        end else if(soc.u_cpu.normal_retire) begin
            $fdisplay(ev_fd,"EV %0d N %08h %08h %01h %0d %08h %08h %08h %08h",events,
                pc,ins,we,we ? regno : 5'b0,we ? value : 32'b0,32'b0,32'b0,soc.u_cpu.mem_wb_next_pc);
            events=events+1;
            if(pc==32'h40000304) done=1;
        end
        $fflush(ev_fd);$fflush(bus_fd);
    end
endmodule
`include "unit_cases.svh"
