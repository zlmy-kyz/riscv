`timescale 1ns/1ps
module tb_coremark #(parameter integer MAX_CYCLES=20000000);
    localparam real TBIT=1.0e9/115200.0;
    reg clk=0, resetn=0;
    always #(1.0e9/93750000.0/2.0) clk=~clk;
    wire txd;
    wire [27:0] awaddr,araddr;
    wire awvalid,arvalid,awready,arready,wready,rvalid;
    wire [127:0] wdata,rdata;
    wire [15:0] wstrb;
    soc_top #(.ENABLE_DDR(1),.RESET_PC(0),.INST_ROM_BASE(0),.DATA_RAM_BASE(0),
              .UART_RSP_DELAY_CYCLES(7)) dut(
        .clk(clk),.resetn(resetn),.uart_rx(1'b1),.uart_tx(txd),
        .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .selftest_status(),.debug_wb_pc(),.debug_wb_rf_we(),
        .debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(),
        .ddr_init_done(1'b1),.ddr_axi_awaddr(awaddr),.ddr_axi_awuser_ap(),
        .ddr_axi_awuser_id(),.ddr_axi_awlen(),.ddr_axi_awready(awready),
        .ddr_axi_awvalid(awvalid),.ddr_axi_wdata(wdata),.ddr_axi_wstrb(wstrb),
        .ddr_axi_wready(wready),.ddr_axi_wusero_id(4'd0),.ddr_axi_wusero_last(wready),
        .ddr_axi_araddr(araddr),.ddr_axi_aruser_ap(),.ddr_axi_aruser_id(),
        .ddr_axi_arlen(),.ddr_axi_arready(arready),.ddr_axi_arvalid(arvalid),
        .ddr_axi_rdata(rdata),.ddr_axi_rid(4'd0),.ddr_axi_rlast(rvalid),.ddr_axi_rvalid(rvalid));
    coremark_ddr_model memory(
        .clk(clk),.resetn(resetn),.awaddr(awaddr),.awvalid(awvalid),.awready(awready),
        .wdata(wdata),.wstrb(wstrb),.wready(wready),.araddr(araddr),.arvalid(arvalid),
        .arready(arready),.rdata(rdata),.rvalid(rvalid));
    reg [31:0] image[0:4095];
    reg [7:0] sent_bytes[0:8191];
    string path;
    integer words,main_pc,done_pc,bss_start,bss_end;
    integer cycles=0,copied=0,clears=0,retired=0,written=0,decoded=0,i,b,uart_file;
    integer timer_reads=0;
    reg [31:0] timer_start,timer_stop;
    reg [31:0] min_sp=32'h40010000;
    reg loader_phase=1,saw_main=0,saw_sp=0,done=0,test_pass=0;
    reg [7:0] byte_value;
    task check;
        input condition;
        input [511:0] message;
        begin if(condition !== 1'b1)
            $fatal(1,"RESULT: FAIL coremark cycle=%0d pc=%h: %0s",cycles,dut.debug_wb_pc,message);
        end
    endtask
    initial begin
        check($value$plusargs("DAT=%s",path),"missing DAT");
        $readmemh(path,image); words=image[4092];
        check(words>0 && words<=4092 && image[4093]==0 && image[4094]==0 && image[4095]==0,"manifest");
        check($value$plusargs("MAIN=%h",main_pc),"missing MAIN");
        check($value$plusargs("DONE=%h",done_pc),"missing DONE");
        check($value$plusargs("BSS_START=%h",bss_start),"missing BSS_START");
        check($value$plusargs("BSS_END=%h",bss_end),"missing BSS_END");
        uart_file=$fopen("uart.txt","wb"); check(uart_file!=0,"UART capture open");
        repeat(10) @(negedge clk); resetn=1;
    end
    always @(posedge clk) if(resetn) begin
        cycles=cycles+1;
        if(cycles%1000000==0) $display("PROGRESS cycles=%0d pc=%h decoded=%0d",cycles,dut.debug_wb_pc,decoded);
        check(cycles<MAX_CYCLES,"cycle timeout");
        check(!dut.u_cpu.sync_trap_event && !dut.u_cpu.irq_take,"CPU trap/interrupt");
        check(!(dut.inst_rsp_valid && dut.inst_rsp_error) && !(dut.data_rsp_valid && dut.data_rsp_error),"bus fault");
        if(dut.data_req_valid && dut.data_req_ready && dut.data_req_write) begin
            if(loader_phase && dut.data_req_addr>=32'h40000000) begin
                check(copied<words && dut.data_req_addr==32'h40000000+copied*4,"loader address/count");
                check(dut.data_req_wdata===image[copied] && dut.data_req_wstrb==15,"loader word/strobe");
                copied=copied+1;
            end else if(!saw_main && dut.data_req_addr>=bss_start && dut.data_req_addr<bss_end) begin
                check(dut.data_req_addr==bss_start+clears*4 && dut.data_req_wdata==0 && dut.data_req_wstrb==15,"BSS clear order");
                clears=clears+1;
            end else if(dut.data_req_addr>=32'h40000000) begin
                check(saw_main,"unexpected DDR write before main");
                check((dut.data_req_addr>=bss_start && dut.data_req_addr<bss_end) ||
                      (dut.data_req_addr>=32'h4000f040 && dut.data_req_addr<32'h40010000),"write outside BSS/stack or stack guard touched");
            end
        end
        if(loader_phase && dut.inst_req_valid && dut.inst_req_ready && dut.inst_req_addr==32'h40000000) begin
            check(copied==words && !memory.writing,"loader completion");
            for(i=0;i<words;i=i+1) check(memory.word_at(32'h40000000+i*4)===image[i],"DDR payload mismatch");
            for(i=bss_start;i<bss_end;i=i+4) check(memory.word_at(i)===32'ha5a5a5a5,"BSS pre-cleared");
            loader_phase=0;
            $display("CHECK: ROM loader copied final DAT words=%0d",copied);
        end
        if(dut.u_cpu.normal_retire) begin
            retired=retired+1;
            // LA SP is AUIPC+ADDI: the first write is an intermediate PC value.
            if(dut.debug_wb_rf_we==15 && dut.debug_wb_rf_wnum==2 && dut.u_cpu.mem_wb_pc!=32'h40000008) begin
                check(dut.debug_wb_rf_wdata>=32'h4000f040 && dut.debug_wb_rf_wdata<=32'h40010000,"SP outside stack");
                if(dut.debug_wb_rf_wdata<min_sp) min_sp=dut.debug_wb_rf_wdata;
                saw_sp=1;
                if(dut.u_cpu.mem_wb_pc==32'h4000000c) check(dut.debug_wb_rf_wdata==32'h40010000,"initial SP");
            end
            if(dut.u_cpu.mem_wb_pc==main_pc && !saw_main) begin
                check(!loader_phase && saw_sp && clears*4==bss_end-bss_start,"main before initialization");
                for(i=bss_start;i<bss_end;i=i+4) check(memory.word_at(i)===0,"BSS nonzero at main");
                saw_main=1;
                $display("CHECK: startup initialized SP/BSS bytes=%0d",clears*4);
            end
            if(dut.u_cpu.mem_wb_pc==done_pc) done=1;
        end
        if(dut.data_req_valid && dut.data_req_ready && !dut.data_req_write && dut.data_req_addr==32'h10000008) begin
            check(timer_reads<2,"unexpected timer read");
            if(timer_reads==0) timer_start=cycles; else timer_stop=cycles;
            timer_reads=timer_reads+1;
        end
        if(dut.u_uart_mmio.tx_send) begin
            check(saw_main && written<8192,"TX before main or capture overflow");
            check(dut.u_uart_mmio.req_wstrb==1 && dut.u_uart_mmio.req_size==0,"TX must be SB lane0");
            sent_bytes[written]=dut.u_uart_mmio.req_wdata[7:0]; written=written+1;
        end
    end
    initial forever begin
        @(negedge txd); if(resetn) begin
            #(TBIT/2); check(txd===0,"UART start");
            for(b=0;b<8;b=b+1) begin #(TBIT); byte_value[b]=txd; end
            #(TBIT); check(txd===1,"UART stop");
            check(decoded<written && byte_value===sent_bytes[decoded],"TX pin differs from accepted byte");
            $fwrite(uart_file,"%c",byte_value); $fflush(uart_file); decoded=decoded+1;
        end
    end
    initial begin
        wait(done); wait(!dut.u_uart_mmio.tx_busy); #(TBIT*12);
        check(decoded==written && decoded>0 && timer_reads==2,"missing UART/timer evidence");
        for(i=32'h4000f000;i<32'h4000f040;i=i+4) check(memory.word_at(i)===32'ha5a5a5a5,"stack guard corrupted");
        $fclose(uart_file);
        test_pass=1;
        $display("RESULT: PASS coremark_full_boot words=%0d bss_bytes=%0d uart_bytes=%0d min_sp=%h stack_used=%0d timer_ticks=%0d retired=%0d cycles=%0d",words,clears*4,decoded,min_sp,32'h40010000-min_sp,timer_stop-timer_start,retired,cycles);
        $finish;
    end
endmodule
