`timescale 1ns/1ps
// FAST=1 models byte transport at real MMIO/FIFO boundaries, not 115200 wire timing.
// FAST=0 drives/decodes the original 115200 UART pins without any UART force.
module tb_load #(parameter FAST=1, CASES=1, RX_BYTES=1, TIME_SCALE=512);
    localparam real TBIT=1.0e9/115200.0;
    reg clk=0,resetn=0,rxd=1;
    always #(1.0e9/93750000.0/2.0) clk=~clk;
    wire txd;wire [27:0] awaddr,araddr;wire [127:0] wdata,rdata;wire [15:0] wstrb;
    wire awvalid,arvalid,awready,arready,wready,rvalid;wire [3:0] awlen,arlen,awid,arid;
    wire [31:0] wb_pc,wb_value,wb_inst;wire [3:0] wb_we;wire [4:0] wb_rd;
    soc_top #(.ENABLE_DDR(1),.UART_RSP_DELAY_CYCLES(7)) dut(
        .clk(clk),.resetn(resetn),.uart_rx(rxd),.uart_tx(txd),
        .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .debug_wb_pc(wb_pc),.debug_wb_rf_we(wb_we),.debug_wb_rf_wnum(wb_rd),.debug_wb_rf_wdata(wb_value),.debug_inst(wb_inst),.selftest_status(),
        .ddr_init_done(1'b1),.ddr_axi_awaddr(awaddr),.ddr_axi_awuser_ap(),.ddr_axi_awuser_id(awid),.ddr_axi_awlen(awlen),.ddr_axi_awready(awready),.ddr_axi_awvalid(awvalid),
        .ddr_axi_wdata(wdata),.ddr_axi_wstrb(wstrb),.ddr_axi_wready(wready),.ddr_axi_wusero_id(4'b0),.ddr_axi_wusero_last(wready),
        .ddr_axi_araddr(araddr),.ddr_axi_aruser_ap(),.ddr_axi_aruser_id(arid),.ddr_axi_arlen(arlen),.ddr_axi_arready(arready),.ddr_axi_arvalid(arvalid),
        .ddr_axi_rdata(rdata),.ddr_axi_rid(arid),.ddr_axi_rlast(rvalid),.ddr_axi_rvalid(rvalid));
    loader_ddr_model memory(.clk(clk),.resetn(resetn),.enabled(1'b1),.inject_fault(1'b0),
        .awaddr(awaddr),.araddr(araddr),.awvalid(awvalid),.arvalid(arvalid),.wdata(wdata),.wstrb(wstrb),
        .awready(awready),.wready(wready),.arready(arready),.rvalid(rvalid),.rdata(rdata));
    reg [7:0] stimulus[0:RX_BYTES-1],expected[0:CASES*60-1],shadow[0:65535];
    reg [31:0] metadata[0:CASES*16-1];
    reg test_pass=0;
    reg [7:0] injected_data=0;reg injected_valid=0;
    reg [31:0] virtual_cycle=0;
    generate if(FAST) begin
        initial begin
            force dut.u_uart_mmio.rx_valid=injected_valid;
            force dut.u_uart_mmio.rx_data=injected_data;
            force dut.u_uart_mmio.tx_ready=1'b1;
            force dut.u_uart_mmio.tx_busy=1'b0;
        end
    end endgenerate
    generate if(TIME_SCALE!=1) begin
        always @(negedge clk) if(!resetn) virtual_cycle=0;else virtual_cycle=virtual_cycle+TIME_SCALE;
        initial force dut.u_simple_mmio.cycle_counter=virtual_cycle;
    end endgenerate
    integer active_addr,complete_addr,total_addr,received_addr,image_crc_addr;
    integer bss_start,bss_end,buffer_end,main_pc,ready_addr,boot_error,rx_pc,rx_rd,recover_pc,recover_rd;
    integer case_index=-1,offset=0,frame_end=0,n,j,k,lane,address,boot_count=0,clears=0;
    integer sent=0,received=0,popped=0,rx_retired=0,tx_written=0,decoded=0;
    integer cycles=0,retired=0,min_sp=16368,fifo_peak=0,write_bytes=0,read_bytes=0;
    integer current_write=0,current_read=0,write_cursor=0,read_cursor=0;
    integer req_count=0,retire_count=0,rsp_count=0,user_aw=0,user_ar=0,user_w=0,aw_index=0,ar_index=0;
    integer trace_fd,tx_fd,rx_fd,byte_no,bit_no,inject_offset;
    integer rx_pending=0;reg [7:0] rx_latched;
    reg saw_main=0;reg [7:0] decoded_byte;
    reg [31:0] req_pc[0:262143],req_addr[0:262143],req_word[0:262143],req_data[0:262143];
    reg [1:0] req_size[0:262143];reg req_write[0:262143];reg [3:0] req_strobe[0:262143];
    string path,tx_path,rx_path,meta_path,trace_path;
    realtime started;
    function [31:0] ram_word(input integer a);ram_word=dut.u_data_ram.mem[a>>2];endfunction
    function [31:0] shadow_word(input integer a);
        integer aligned;begin aligned=a&65532;shadow_word={shadow[aligned+3],shadow[aligned+2],shadow[aligned+1],shadow[aligned]};end
    endfunction
    task check(input condition,input string message);
        if(condition!==1'b1)$fatal(1,"RESULT: FAIL load_stage10 FAST=%0d case=%0d cycles=%0d pc=%h: %s",FAST,case_index,cycles,dut.u_cpu.pc,message);
    endtask
    task guards;
        begin
            for(j=0;j<32;j=j+4)check(ram_word(j)===32'ha5a5a5a5,"low RAM sentinel");
            for(j=48;j<256;j=j+4)check(ram_word(j)===32'ha5a5a5a5,"diagnostic RAM sentinel");
            for(j=12288;j<12352;j=j+4)check(ram_word(j)===32'ha5a5a5a5,"stack bottom sentinel");
            for(j=16368;j<16384;j=j+4)check(ram_word(j)===32'ha5a5a5a5,"old RAM manifest sentinel");
            for(j=61440;j<65536;j=j+4)check(memory.word_at(32'h40000000+j)===32'ha5a5a5a5,"DDR application stack sentinel");
        end
    endtask
    task boot;
        integer a,waited;
        begin
            @(negedge clk);resetn=0;rxd=1;injected_valid=0;repeat(12)@(negedge clk);
            for(a=bss_start;a<bss_end;a=a+4)dut.u_data_ram.mem[a>>2]=32'hdededede;
            for(a=0;a<256;a=a+4)dut.u_data_ram.mem[a>>2]=32'ha5a5a5a5;
            for(a=12288;a<16384;a=a+4)dut.u_data_ram.mem[a>>2]=32'ha5a5a5a5;
            for(a=8192;a<buffer_end;a=a+4)dut.u_data_ram.mem[a>>2]=32'hcccccccc;
            saw_main=0;clears=0;
            @(negedge clk);resetn=1;waited=0;
            while(ram_word(ready_addr)!==32'h52454144 && waited<60000)begin @(negedge clk);waited=waited+1;end
            check(ram_word(ready_addr)===32'h52454144 && saw_main,"ROM/RAM boot not ready");
            check(ram_word(boot_error)===0 && clears==(bss_end-bss_start)/4,"BSS/constant/CRC startup");
            check(ram_word(32)===32'h929a5e56 && ram_word(36)===32'hcbf43926 && ram_word(40)===0 && ram_word(44)===0,"boot vectors");
            check(!dut.u_uart_mmio.rx_irq_enable && !dut.u_cpu.u_csr_file.irq_global_enable,"IRQ enabled");
            guards();boot_count=boot_count+1;
            $display("CHECK: stage10 boot=%0d dirty_BSS_words=%0d constants/CRC PASS",boot_count,clears);
        end
    endtask
    task send_byte(input [7:0] value);
        integer bit_index,before_pop;
        begin
            if(FAST)begin
                before_pop=popped;
                @(negedge clk);check(dut.u_uart_mmio.fifo_empty,"fast transport outstanding byte");injected_data=value;injected_valid=1;
                @(negedge clk);injected_valid=0;
                while(popped==before_pop)@(negedge clk);
            end else begin
                rxd=0;#(TBIT);
                for(bit_index=0;bit_index<8;bit_index=bit_index+1)begin rxd=value[bit_index];#(TBIT);end
                rxd=1;#(TBIT);
            end
            sent=sent+1;
        end
    endtask
    initial begin
        check($value$plusargs("ACTIVE=%h",active_addr),"ACTIVE");
        check($value$plusargs("COMPLETE=%h",complete_addr),"COMPLETE");
        check($value$plusargs("TOTAL=%h",total_addr),"TOTAL");
        check($value$plusargs("ACCEPTED=%h",received_addr),"ACCEPTED");
        check($value$plusargs("IMAGE_CRC=%h",image_crc_addr),"IMAGE_CRC");
        check($value$plusargs("BSS_START=%h",bss_start),"BSS_START");check($value$plusargs("BSS_END=%h",bss_end),"BSS_END");
        check($value$plusargs("BUFFER_END=%h",buffer_end),"BUFFER_END");check($value$plusargs("MAIN=%h",main_pc),"MAIN");
        check($value$plusargs("READY=%h",ready_addr),"READY");check($value$plusargs("BOOT_ERROR=%h",boot_error),"BOOT_ERROR");
        check($value$plusargs("RX_PC=%h",rx_pc),"RX_PC");check($value$plusargs("RX_RD=%d",rx_rd),"RX_RD");
        check($value$plusargs("RECOVER_PC=%h",recover_pc),"RECOVER_PC");check($value$plusargs("RECOVER_RD=%d",recover_rd),"RECOVER_RD");
        check($value$plusargs("REQUESTS=%s",path),"REQUESTS");$readmemh(path,stimulus);
        check($value$plusargs("RESPONSES=%s",path),"RESPONSES");$readmemh(path,expected);
        check($value$plusargs("META=%s",meta_path),"META");$readmemh(meta_path,metadata);
        check($value$plusargs("CAPTURE=%s",tx_path),"CAPTURE");tx_fd=$fopen(tx_path,"wb");
        check($value$plusargs("RX_CAPTURE=%s",rx_path),"RX_CAPTURE");rx_fd=$fopen(rx_path,"wb");
        check($value$plusargs("TRACE=%s",trace_path),"TRACE");trace_fd=$fopen(trace_path,"w");
        check(tx_fd && rx_fd && trace_fd,"capture open");
        for(n=0;n<65536;n=n+1)shadow[n]=8'ha5;
        #200;for(n=0;n<3;n=n+1)boot();
        for(case_index=0;case_index<CASES;case_index=case_index+1)begin
            if(case_index>0 && metadata[case_index*16+1])boot();
            inject_offset=metadata[case_index*16+2];
            if(inject_offset)begin
                @(negedge clk);inject_offset=inject_offset-1;
                memory.beats[inject_offset/16][(inject_offset%16)*8+:8]=memory.beats[inject_offset/16][(inject_offset%16)*8+:8]^8'h01;
                shadow[inject_offset]=shadow[inject_offset]^8'h01;
            end
            current_write=0;current_read=0;write_cursor=0;read_cursor=0;
            frame_end=offset+metadata[case_index*16];started=$realtime;
            repeat(metadata[case_index*16+9])@(negedge clk);
            for(byte_no=offset;byte_no<frame_end;byte_no=byte_no+1)send_byte(stimulus[byte_no]);
            while(decoded<(case_index+1)*60)@(negedge clk);
            while(dut.u_uart_mmio.tx_busy)@(negedge clk);
            repeat(50)@(negedge clk);
            check(current_write==metadata[case_index*16+3] && current_read==metadata[case_index*16+4],"per-case DDR byte count/negative side effects");
            check(req_count==retire_count && req_count==rsp_count,"each DDR transaction retired/responded once");
            check(dut.u_uart_mmio.fifo_empty,"extra RX after response");
            guards();
            check(ram_word(complete_addr)===metadata[case_index*16+10],"complete state");
            check(ram_word(active_addr)===metadata[case_index*16+11],"active state");
            check(ram_word(total_addr)===metadata[case_index*16+12],"total state");
            check(ram_word(received_addr)===metadata[case_index*16+13],"accepted state");
            check(ram_word(image_crc_addr)===metadata[case_index*16+14],"image CRC identity state");
            if(metadata[case_index*16+7])begin
                for(j=0;j<65536;j=j+4)check(memory.word_at(32'h40000000+j)===shadow_word(j),"full physical DDR vs byte oracle");
                $display("CHECK: IMAGE case=%0d bytes=%0d physical DDR/CRC/tail/stack PASS",case_index,metadata[case_index*16+6]);
            end
            offset=frame_end;
        end
        repeat(100)@(negedge clk);
        check(sent==RX_BYTES && received==sent && popped==sent && rx_retired==sent,"raw RX/pop/CPU LBU counts");
        check(tx_written==CASES*60 && decoded==tx_written,"TX raw/decoded count");
        check(user_aw==user_w && user_aw+user_ar==req_count,"Pango transaction conservation");
        guards();test_pass=1;$fclose(tx_fd);$fclose(rx_fd);$fclose(trace_fd);
        $display("RESULT: PASS load_stage10 FAST=%0d frames=%0d boots=%0d RX=%0d pop=%0d LBU=%0d TX=%0d decoded=%0d write_bytes=%0d read_bytes=%0d DDR_req=%0d retired_DDR=%0d AW/W=%0d AR=%0d fifo_peak=%0d min_sp=%08h cycles=%0d retired=%0d",FAST,CASES,boot_count,received,popped,rx_retired,tx_written,decoded,write_bytes,read_bytes,req_count,retire_count,user_w,user_ar,fifo_peak,min_sp,cycles,retired);$finish;
    end
    always @(posedge clk)if(resetn)begin
        cycles=cycles+1;
        check(!dut.u_cpu.sync_trap_event && !dut.u_cpu.irq_take,"CPU trap/IRQ");
        check(!(dut.inst_rsp_valid && dut.inst_rsp_error) && !(dut.data_rsp_valid && dut.data_rsp_error),"bus error");
        check(!dut.inst_ddr_req_valid && (!dut.inst_req_valid || dut.inst_req_addr<16384),"left ROM or executed random DDR bytes");
        check(!dut.u_uart_mmio.frame_error_status && !dut.u_uart_mmio.overflow_status && !dut.u_uart_mmio.overflow,"unexpected UART error");
        if(dut.u_uart_mmio.fifo_count>fifo_peak)fifo_peak=dut.u_uart_mmio.fifo_count;
        if(dut.data_req_valid && dut.data_req_ready && dut.data_req_write && dut.data_req_addr<16384)begin
            address=dut.data_req_addr;
            check((address>=bss_start && address<bss_end) || (address>=32 && address<48) || (address>=8192 && address<buffer_end) || (address>=12352 && address<16368),"RAM write outside mutable partitions");
            if(!saw_main && address>=bss_start && address<bss_end)begin
                check(address==bss_start+4*clears && dut.data_req_wdata===0 && dut.data_req_wstrb==15,"ordered BSS zero clear");clears=clears+1;
            end
        end
        if(dut.u_cpu.normal_retire)begin
            retired=retired+1;
            if(wb_pc==main_pc)saw_main=1;
            if(wb_we==15 && wb_rd==2 && wb_pc>=32)begin
                check(wb_value>=12352 && wb_value<=16368 && wb_value[3:0]==0,"Loader stack limit/alignment");if(wb_value<min_sp)min_sp=wb_value;
            end
            if((wb_pc==rx_pc || wb_pc==recover_pc) && wb_we==15)begin
                check(rx_retired<received && wb_value=={24'b0,stimulus[rx_retired]},"retired UART LBU byte/order");rx_retired=rx_retired+1;
            end
            if(retire_count<req_count && wb_pc==req_pc[retire_count])begin
                check(wb_inst[6:0]==(req_write[retire_count]?7'h23:7'h03),"DDR retirement instruction");
                if(!req_write[retire_count])check(wb_we==15 && wb_value==req_word[retire_count],"physical DDR load retired value");
                $fdisplay(trace_fd,"RETIRE,%08h,%08h,%08h",wb_pc,req_addr[retire_count],wb_value);retire_count=retire_count+1;
            end
        end
        if(dut.u_uart_mmio.rx_valid)begin
            check(received<RX_BYTES && dut.u_uart_mmio.rx_data===stimulus[received],"UART input byte");$fwrite(rx_fd,"%c",dut.u_uart_mmio.rx_data);received=received+1;
        end
        if(dut.u_uart_mmio.fifo_pop)begin
            check(!rx_pending && dut.u_uart_mmio.fifo_data===stimulus[popped],"FIFO pop exactly once/order");
            rx_latched=dut.u_uart_mmio.fifo_data;rx_pending=1;popped=popped+1;
        end
        if(rx_pending && dut.u_uart_mmio.rsp_valid)begin
            check(dut.u_uart_mmio.rsp_rdata=={24'b0,rx_latched} && !dut.u_uart_mmio.rsp_error,"RX MMIO response");rx_pending=0;
        end
        if(dut.u_uart_mmio.tx_send)begin
            check(tx_written<CASES*60 && dut.u_uart_mmio.req_wdata[7:0]===expected[tx_written],"CPU response vs zlib/byte oracle");
            if(FAST)begin $fwrite(tx_fd,"%c",dut.u_uart_mmio.req_wdata[7:0]);decoded=decoded+1;end
            tx_written=tx_written+1;
        end
        if(dut.data_ddr_req_valid && dut.data_ddr_req_ready)begin
            check(case_index>=0 && rx_retired>=frame_end,"DDR before full UART packet consumed");
            address=dut.data_ddr_req_addr;check(address<61440 && (dut.data_ddr_req_size==0 || (dut.data_ddr_req_size==2 && address%4==0)),"DDR size/window/alignment");
            check(req_count<262144,"transaction queue capacity");
            req_pc[req_count]=dut.u_cpu.id_ex_pc;req_addr[req_count]=address;req_size[req_count]=dut.data_ddr_req_size;
            req_write[req_count]=dut.data_ddr_req_write;req_data[req_count]=dut.data_ddr_req_wdata;req_strobe[req_count]=dut.data_ddr_req_wstrb;
            if(dut.data_ddr_req_write)begin
                check(address==metadata[case_index*16+5]-32'h40000000+write_cursor,"exact write address sequence");
                check(dut.data_ddr_req_wstrb==(dut.data_ddr_req_size==2 ? 4'hf : 4'b1<<(address%4)),"DDR SB/SW write strobe");
                for(lane=0;lane<4;lane=lane+1)if(dut.data_ddr_req_wstrb[lane])begin
                    check(current_write<metadata[case_index*16+3],"unexpected write/duplicate/negative side effect");
                    check(dut.data_ddr_req_wdata[lane*8+:8]===stimulus[offset+metadata[case_index*16+8]+write_cursor],"DDR store payload byte");
                    shadow[(address&65532)+lane]=dut.data_ddr_req_wdata[lane*8+:8];write_cursor=write_cursor+1;current_write=current_write+1;write_bytes=write_bytes+1;
                end
            end else begin
                check(address==metadata[case_index*16+5]-32'h40000000+read_cursor,"exact read range/address sequence");
                req_word[req_count]=dut.data_ddr_req_size==2 ? shadow_word(address) : {24'b0,shadow[address]};
                k=dut.data_ddr_req_size==2 ? 4 : 1;current_read=current_read+k;read_cursor=read_cursor+k;read_bytes=read_bytes+k;
                check(current_read<=metadata[case_index*16+4],"unexpected DDR read/negative side effect");
            end
            $fdisplay(trace_fd,"REQ,%08h,%08h,%0d,%0d,%01h,%08h",dut.u_cpu.id_ex_pc,address,dut.data_ddr_req_write,dut.data_ddr_req_size,dut.data_ddr_req_wstrb,dut.data_ddr_req_wdata);
            req_count=req_count+1;
        end
        if(dut.data_ddr_rsp_valid)begin
            check(rsp_count<req_count && !dut.data_ddr_rsp_error,"DDR response exactly once");
            if(!req_write[rsp_count])check(dut.data_ddr_rsp_rdata===shadow_word(req_addr[rsp_count]),"bridge read response vs physical byte oracle");rsp_count=rsp_count+1;
        end
        if(awvalid && awready)begin
            while(aw_index<req_count && !req_write[aw_index])aw_index=aw_index+1;
            check(aw_index<req_count && awaddr==(req_addr[aw_index]/16)*8 && awlen==0 && awid==1,"Pango AW beat address/id");
            check(wstrb==({12'b0,req_strobe[aw_index]}<<((req_addr[aw_index]%16)/4*4)) && wdata==({96'b0,req_data[aw_index]}<<((req_addr[aw_index]%16)/4*32)),"Pango 128-bit byte placement");
            aw_index=aw_index+1;user_aw=user_aw+1;
        end
        if(wready)begin check(user_w<user_aw,"Pango W without AW");user_w=user_w+1;end
        if(arvalid && arready)begin
            while(ar_index<req_count && req_write[ar_index])ar_index=ar_index+1;
            check(ar_index<req_count && araddr==(req_addr[ar_index]/16)*8 && arlen==0,"Pango AR beat address");ar_index=ar_index+1;user_ar=user_ar+1;
        end
    end
    initial if(!FAST)forever begin
        @(negedge txd);if(resetn)begin
            #(TBIT/2);check(txd===0,"wire TX start");decoded_byte=0;
            for(bit_no=0;bit_no<8;bit_no=bit_no+1)begin #(TBIT);decoded_byte[bit_no]=txd;end
            #(TBIT);check(txd===1,"wire TX stop");check(decoded<CASES*60 && decoded_byte===expected[decoded],"independent wire decode");
            $fwrite(tx_fd,"%c",decoded_byte);decoded=decoded+1;
        end
    end
    initial begin #10000000000.0;$fatal(1,"RESULT: FAIL stage10 watchdog case=%0d rx=%0d tx=%0d pc=%h",case_index,received,decoded,dut.u_cpu.pc);end
endmodule
