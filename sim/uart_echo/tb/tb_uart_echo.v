`timescale 1ns/1ps
// Testbench-only stimulus/scoreboards. Production CPU and UART RTL are unchanged.
module tb_uart_echo #(parameter integer LAYER=0);
    localparam real TBIT=1.0e9/115200.0;
    localparam integer COUNT=97;
    reg clk=0, resetn=0, rxd=1;
    always #(1.0e9/93750000.0/2.0) clk=~clk;
    wire txd, rx_event, frame_error, overflow, pop, tx_start, tx_ready;
    wire [7:0] rx_byte, head_byte, tx_byte;
    wire [4:0] fifo_count;
    wire req_fire, req_write, rsp_valid, rsp_error;
    wire [31:0] req_addr, rsp_data;
    reg [7:0] expected [0:COUNT-1];
    integer sent=0, received=0, popped=0, read_back=0, written=0, decoded=0;
    integer cycles=0, peak=0, retired=0, cpu_loaded=0;
    reg [31:0] software_count=0, software_error=0;
    reg pending_rx=0, test_pass=0, program_ready=0, stimulus_done=0;
    reg [7:0] decoded_byte;
    integer bit_index, k, n;

    task check;
        input condition;
        input [511:0] message;
        begin
            if (condition !== 1'b1)
                $fatal(1,"RESULT: FAIL uart_echo layer=%0d cycle=%0d: %0s",LAYER,cycles,message);
        end
    endtask
    task send_byte;
        input [7:0] value;
        integer b;
        begin
            sent=sent+1;
            rxd=0; #(TBIT);
            for(b=0;b<8;b=b+1) begin rxd=value[b]; #(TBIT); end
            rxd=1; #(TBIT);
        end
    endtask

    generate if(LAYER==0) begin: g_module
        wire empty, full;
        wire send=resetn && tx_ready && !empty;
        uart_rx rx(.clk(clk),.resetn(resetn),.rx(rxd),.rx_data(rx_byte),
                   .rx_valid(rx_event),.frame_error(frame_error),.rx_busy());
        uart_rx_fifo fifo(.clk(clk),.resetn(resetn),.wr_en(rx_event),.write_data(rx_byte),
                          .rd_en(send),.read_data(head_byte),.empty(empty),.full(full),
                          .count(fifo_count),.overflow(overflow));
        // Module-level test driver transfers decoded FIFO bytes; no pin bypass.
        uart_tx tx(.clk(clk),.resetn(resetn),.tx_data(head_byte),.tx_valid(send),
                   .tx(txd),.tx_busy(),.tx_ready(tx_ready));
        assign pop=send; assign tx_start=send; assign tx_byte=head_byte;
        assign req_fire=0; assign req_write=0; assign req_addr=0;
        assign rsp_valid=0; assign rsp_error=0; assign rsp_data=0;
        initial begin wait(resetn); program_ready=1; end
    end else if(LAYER==1) begin: g_mmio
        reg valid=0, write=0;
        reg [1:0] size=2;
        reg [31:0] addr=0, data=0;
        reg [3:0] strobe=0;
        wire ready;
        uart_mmio #(.RSP_DELAY_CYCLES(7)) dut(
            .clk(clk),.resetn(resetn),.req_valid(valid),.req_write(write),.req_size(size),
            .req_addr(addr),.req_wdata(data),.req_wstrb(strobe),.req_ready(ready),
            .rsp_valid(rsp_valid),.rsp_rdata(rsp_data),.rsp_error(rsp_error),
            .uart_rx(rxd),.uart_tx(txd),.uart_irq());
        assign rx_event=dut.rx_valid; assign rx_byte=dut.rx_data;
        assign frame_error=dut.frame_error || dut.frame_error_status;
        assign overflow=dut.overflow || dut.overflow_status;
        assign head_byte=dut.fifo_data; assign fifo_count=dut.fifo_count;
        assign pop=dut.fifo_pop; assign tx_start=dut.tx_send;
        assign tx_byte=dut.req_wdata[7:0]; assign tx_ready=dut.tx_ready;
        assign req_fire=valid && ready; assign req_write=write; assign req_addr=addr;
        task access;
            input wr;
            input [31:0] address, value;
            input [1:0] sz;
            input [3:0] lanes;
            output [31:0] result;
            begin
                @(negedge clk);
                valid=1; write=wr; addr=address; data=value; size=sz; strobe=lanes;
                @(posedge clk); while(!ready) @(posedge clk);
                @(negedge clk); valid=0;
                @(posedge clk); while(!rsp_valid) @(posedge clk);
                check(!rsp_error,"MMIO error"); result=rsp_data;
                @(negedge clk);
            end
        endtask
        reg [31:0] status, byte_value, unused;
        initial begin
            wait(resetn); program_ready=1;
            forever begin
                access(0,8,0,2,0,status);
                if(status[2]) begin
                    access(0,4,0,0,0,byte_value);
                    access(0,8,0,2,0,status);
                    while(!status[0]) access(0,8,0,2,0,status);
                    access(1,0,byte_value,0,1,unused);
                end
            end
        end
    end else begin: g_cpu
        wire [27:0] awaddr,araddr;
        wire awvalid,arvalid,awready,arready,wready,rvalid;
        wire [127:0] wdata,rdata;
        wire [15:0] wstrb;
        wire [1:0] status;
        integer copied=0, words, i, bss_start, bss_end, clears=0, main_pc;
        integer rx_load_pc, count_addr, error_addr;
        reg loader_phase=(LAYER==3), saw_sp=0, saw_main=0;
        reg [31:0] image[0:4095];
        string dat_path;
        soc_top #(.ENABLE_DDR(1),.RESET_PC(LAYER==3 ? 0 : 32'h40000000),
                  .INST_ROM_BASE(0),.DATA_RAM_BASE(0),.UART_RSP_DELAY_CYCLES(7)) dut(
            .clk(clk),.resetn(resetn),.uart_rx(rxd),.uart_tx(txd),
            .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
            .selftest_status(status),.debug_wb_pc(),.debug_wb_rf_we(),
            .debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(),
            .ddr_init_done(1'b1),.ddr_axi_awaddr(awaddr),.ddr_axi_awuser_ap(),
            .ddr_axi_awuser_id(),.ddr_axi_awlen(),.ddr_axi_awready(awready),
            .ddr_axi_awvalid(awvalid),.ddr_axi_wdata(wdata),.ddr_axi_wstrb(wstrb),
            .ddr_axi_wready(wready),.ddr_axi_wusero_id(4'd0),.ddr_axi_wusero_last(wready),
            .ddr_axi_araddr(araddr),.ddr_axi_aruser_ap(),.ddr_axi_aruser_id(),
            .ddr_axi_arlen(),.ddr_axi_arready(arready),.ddr_axi_arvalid(arvalid),
            .ddr_axi_rdata(rdata),.ddr_axi_rid(4'd0),.ddr_axi_rlast(rvalid),.ddr_axi_rvalid(rvalid));
        echo_ddr_model #(.PRELOAD(LAYER==2)) memory(
            .clk(clk),.resetn(resetn),.awaddr(awaddr),.awvalid(awvalid),.awready(awready),
            .wdata(wdata),.wstrb(wstrb),.wready(wready),.araddr(araddr),.arvalid(arvalid),
            .arready(arready),.rdata(rdata),.rvalid(rvalid));
        assign rx_event=dut.u_uart_mmio.rx_valid; assign rx_byte=dut.u_uart_mmio.rx_data;
        assign frame_error=dut.u_uart_mmio.frame_error || dut.u_uart_mmio.frame_error_status;
        assign overflow=dut.u_uart_mmio.overflow || dut.u_uart_mmio.overflow_status;
        assign head_byte=dut.u_uart_mmio.fifo_data; assign fifo_count=dut.u_uart_mmio.fifo_count;
        assign pop=dut.u_uart_mmio.fifo_pop; assign tx_start=dut.u_uart_mmio.tx_send;
        assign tx_byte=dut.u_uart_mmio.req_wdata[7:0]; assign tx_ready=dut.u_uart_mmio.tx_ready;
        assign req_fire=dut.u_uart_mmio.req_fire; assign req_write=dut.u_uart_mmio.req_write;
        assign req_addr=dut.u_uart_mmio.req_addr; assign rsp_valid=dut.u_uart_mmio.rsp_valid;
        assign rsp_error=dut.u_uart_mmio.rsp_error; assign rsp_data=dut.u_uart_mmio.rsp_rdata;
        initial begin
            check($value$plusargs("DAT=%s",dat_path),"missing DAT");
            check($value$plusargs("MAIN=%h",main_pc),"missing main PC");
            check($value$plusargs("BSS_START=%h",bss_start),"missing BSS start");
            check($value$plusargs("BSS_END=%h",bss_end),"missing BSS end");
            check($value$plusargs("RX_LOAD_PC=%h",rx_load_pc),"missing RX load PC");
            check($value$plusargs("COUNT_ADDR=%h",count_addr),"missing echo_count address");
            check($value$plusargs("ERROR_ADDR=%h",error_addr),"missing echo_error address");
            $readmemh(dat_path,image);
            words=image[4092];
            check(words>0 && words<=4092 && image[4093]==0 && image[4094]==0 && image[4095]==0,"RAM manifest");
        end
        always @(posedge clk) if(resetn) begin
            check(!dut.u_cpu.sync_trap_event,"CPU synchronous exception");
            check(!dut.u_cpu.irq_take,"unexpected CPU interrupt");
            check(!(dut.inst_rsp_valid && dut.inst_rsp_error) &&
                  !(dut.data_rsp_valid && dut.data_rsp_error),"CPU bus fault");
            if(dut.data_req_valid && dut.data_req_ready && dut.data_req_write) begin
                if(loader_phase && dut.data_req_addr>=32'h40000000) begin
                    check(copied<words && dut.data_req_addr==32'h40000000+copied*4,"loader address/order/count");
                    check(dut.data_req_wdata===image[copied] && dut.data_req_wstrb==15,"loader contents/strobe");
                    copied=copied+1;
                end
                if(!saw_main && dut.data_req_addr>=bss_start && dut.data_req_addr<bss_end) begin
                    check(dut.data_req_addr==bss_start+clears*4 && dut.data_req_wdata==0 && dut.data_req_wstrb==15,"BSS clear order");
                    clears=clears+1;
                end
            end
            if(loader_phase && dut.inst_req_valid && dut.inst_req_ready && dut.inst_req_addr==32'h40000000) begin
                check(copied==words && !memory.writing,"loader must finish before DDR entry");
                for(i=0;i<words;i=i+1) check(memory.word_at(32'h40000000+i*4)===image[i],"loaded DDR payload differs from final DAT");
                for(i=bss_start;i<bss_end;i=i+4) check(memory.word_at(i)===32'ha5a5a5a5,"BSS was pre-cleared");
                loader_phase=0;
                $display("CHECK: final DAT copied by ROM loader, words=%0d",copied);
            end
            if(dut.u_cpu.normal_retire) begin
                retired=retired+1;
                if(dut.u_cpu.mem_wb_pc==rx_load_pc) begin
                    check(cpu_loaded<read_back && dut.debug_wb_rf_we==15 &&
                          dut.debug_wb_rf_wnum==10 && dut.debug_wb_rf_wdata=={24'd0,expected[cpu_loaded]},
                          "CPU retired LBU value differs from MMIO/input");
                    cpu_loaded=cpu_loaded+1;
                end
                if(dut.u_cpu.mem_wb_pc==32'h4000000c) begin
                    check(dut.debug_wb_rf_we==15 && dut.debug_wb_rf_wnum==2 && dut.debug_wb_rf_wdata==32'h40010000,"startup stack pointer");
                    saw_sp=1;
                end
                if(dut.u_cpu.mem_wb_pc==main_pc && !saw_main) begin
                    check(!loader_phase && saw_sp && clears*4==bss_end-bss_start,"main reached before initialization");
                    for(i=bss_start;i<bss_end;i=i+4) check(memory.word_at(i)===0,"BSS nonzero at main");
                    saw_main=1;
                end
            end
            // Wait for software's CONTROL write, beyond main/startup retirement.
            if(req_fire && req_write && req_addr==12) begin
                check(saw_main && dut.u_uart_mmio.req_wdata==32'h203,"software UART initialization");
                program_ready=1;
            end
            if(tx_start) check(dut.u_uart_mmio.req_wstrb==1 && dut.u_uart_mmio.req_size==0,"CPU TX must be SB lane0");
            if(pop) check(dut.u_uart_mmio.req_size==0,"CPU RX must be LBU lane0");
        end
        always @(negedge clk) if(stimulus_done && decoded==COUNT && tx_ready) begin
            software_count=memory.word_at(count_addr);
            software_error=memory.word_at(error_addr);
        end
    end endgenerate

    // Every stage compares every byte; MMIO stages also compare delayed read responses.
    always @(posedge clk) if(resetn) begin
        cycles=cycles+1;
        check(cycles<1500000,"simulation timeout");
        check(!frame_error && !overflow,"framing error or FIFO overflow");
        check(!rsp_error,"UART access fault");
        if(fifo_count>peak) peak=fifo_count;
        if(rx_event) begin
            check(received<sent && received<COUNT && rx_byte===expected[received],"UART RX result mismatch/order/extra");
            received=received+1;
        end
        if(pop) begin
            check(popped<received && head_byte===expected[popped],"FIFO/MMIO pop mismatch or repeated read");
            popped=popped+1;
        end
        if(rsp_valid && pending_rx) begin
            check(read_back<popped && rsp_data[7:0]===expected[read_back] && rsp_data[31:8]==0,"MMIO read response mismatch");
            read_back=read_back+1;
        end
        if(rsp_valid) pending_rx=0;
        if(req_fire && !req_write && req_addr==4) begin
            check(pop && !pending_rx,"RX_DATA read without available byte"); pending_rx=1;
        end
        if(tx_start) begin
            check(tx_ready && written<popped && written<COUNT && tx_byte===expected[written],"TX write byte mismatch/busy/duplicate/order");
            written=written+1;
        end
    end
    // Independent PC UART monitor: start -> center samples -> LSB first -> stop.
    always begin
        @(negedge txd);
        if(resetn) begin
            #(TBIT/2); check(txd===0,"TX start bit");
            for(bit_index=0;bit_index<8;bit_index=bit_index+1) begin
                #(TBIT); check(txd===0 || txd===1,"TX unknown bit"); decoded_byte[bit_index]=txd;
            end
            #(TBIT); check(txd===1,"TX stop/framing error");
            check(decoded<written && decoded<COUNT && decoded_byte===expected[decoded],"TXD decoded byte mismatch/order/duplicate");
            $display("DECODE: layer=%0d index=%0d byte=%02h",LAYER,decoded,decoded_byte);
            decoded=decoded+1;
        end
    end
    initial begin
        // A, hello123, nine more uninterrupted groups, then binary patterns.
        expected[0]="A";
        for(n=0;n<10;n=n+1) begin
            expected[1+n*8+0]="h"; expected[1+n*8+1]="e";
            expected[1+n*8+2]="l"; expected[1+n*8+3]="l";
            expected[1+n*8+4]="o"; expected[1+n*8+5]="1";
            expected[1+n*8+6]="2"; expected[1+n*8+7]="3";
        end
        for(n=0;n<16;n=n+1) expected[81+n]=n*17;
        repeat(8) @(negedge clk); resetn=1;
        wait(program_ready); #(TBIT*2+123.0);
        send_byte(expected[0]);
        wait(decoded==1); #(TBIT*2);
        for(k=1;k<9;k=k+1) send_byte(expected[k]);
        wait(decoded==9); #(TBIT*2);
        for(k=9;k<COUNT;k=k+1) send_byte(expected[k]);
        stimulus_done=1;
        wait(decoded==COUNT && tx_ready);
        #(TBIT*20); // Detect trailing duplicates after software/FIFO drain.
        @(negedge clk);
        check(sent==COUNT && received==COUNT && popped==COUNT && written==COUNT && decoded==COUNT,"lost/repeated byte count");
        if(LAYER>0) check(read_back==COUNT && !pending_rx,"lost/repeated MMIO response");
        check(fifo_count==0 && txd===1 && tx_ready,"final FIFO/TX not idle");
        if(LAYER>1) check(retired>100 && cpu_loaded==COUNT && software_count==COUNT && software_error==0,
                         "CPU load/count/error diagnostic mismatch");
        test_pass=1;
        $display("RESULT: PASS uart_echo layer=%0d sent=%0d rx=%0d pop=%0d mmio_read=%0d cpu_lbu=%0d tx_write=%0d decoded=%0d fifo_peak=%0d retired=%0d cycles=%0d",LAYER,sent,received,popped,read_back,cpu_loaded,written,decoded,peak,retired,cycles);
        $finish;
    end
endmodule

// Pango-specific single-beat user-port model with independent AW/AR/W/R delays.
// No PHY/DDR training. Full boot starts poisoned; only ROM CPU stores load code.
module echo_ddr_model #(parameter integer PRELOAD=0)(
    input clk,resetn,input [27:0] awaddr,araddr,input awvalid,arvalid,
    output awready,arready,wready,input [127:0] wdata,input [15:0] wstrb,
    output reg [127:0] rdata=0,output reg rvalid=0);
    reg [127:0] beats[0:4095];
    reg [31:0] image[0:4095];
    reg writing=0,reading=0;
    reg [27:0] wa,ra;
    integer aw_wait=0,ar_wait=0,w_wait=0,r_wait=0,i,lane;
    string dat_path;
    assign awready=awvalid && !writing && aw_wait>=2;
    assign arready=arvalid && !reading && ar_wait>=3;
    assign wready=writing && w_wait==0;
    function [31:0] word_at;
        input [31:0] address;
        reg [31:0] offset;
        begin offset=address-32'h40000000; word_at=beats[offset[15:4]][offset[3:2]*32+:32]; end
    endfunction
    initial begin
        if(!$value$plusargs("DAT=%s",dat_path)) $fatal(1,"RESULT: FAIL missing DAT");
        $readmemh(dat_path,image);
        for(i=0;i<4096;i=i+1) beats[i]={4{32'ha5a5a5a5}};
        if(PRELOAD) for(i=0;i<image[4092];i=i+1) beats[i/4][(i%4)*32+:32]=image[i];
    end
    always @(posedge clk) begin
        rvalid<=0;
        if(resetn) begin
            if(awvalid && !awready) aw_wait<=aw_wait+1;
            if(arvalid && !arready) ar_wait<=ar_wait+1;
            if(awvalid && awready) begin
                if(awaddr[27:15]!=0) $fatal(1,"RESULT: FAIL DDR write alias");
                wa<=awaddr; writing<=1; w_wait<=4; aw_wait<=0;
            end
            if(writing && w_wait>0) w_wait<=w_wait-1;
            if(wready) begin
                for(lane=0;lane<16;lane=lane+1)
                    if(wstrb[lane]) beats[wa[14:3]][lane*8+:8]<=wdata[lane*8+:8];
                writing<=0;
            end
            if(arvalid && arready) begin
                if(araddr[27:15]!=0) $fatal(1,"RESULT: FAIL DDR read alias");
                ra<=araddr; reading<=1; r_wait<=5; ar_wait<=0;
            end
            if(reading && r_wait>0) r_wait<=r_wait-1;
            if(reading && r_wait==0) begin rdata<=beats[ra[14:3]];rvalid<=1;reading<=0;end
        end
    end
endmodule
