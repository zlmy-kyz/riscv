`timescale 1ns/1ps
module tb_uart_loader #(parameter integer STAGE=0, PING_COUNT=100, CASES=114, TIME_SCALE=64);
    localparam real TBIT=1.0e9/115200.0;
    reg clk=0, resetn=0, rxd=1;
    always #(1.0e9/93750000.0/2.0) clk=~clk;
    wire txd;
    wire [27:0] awaddr, araddr;
    wire awvalid, arvalid;
    wire awready,arready,wready,rvalid;
    wire [127:0] wdata,rdata;
    wire [15:0] wstrb;
    wire [3:0] awlen,arlen,awid,arid;
    reg inject_fault=0,ddr_allowed=0;
    wire [31:0] wb_pc, wb_value, wb_inst;
    wire [3:0] wb_we;
    wire [4:0] wb_rd;
    soc_top #(.ENABLE_DDR(1),.RESET_PC(0),.UART_RSP_DELAY_CYCLES(7)) dut(
        .clk(clk),.resetn(resetn),.uart_rx(rxd),.uart_tx(txd),
        .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .debug_wb_pc(wb_pc),.debug_wb_rf_we(wb_we),.debug_wb_rf_wnum(wb_rd),
        .debug_wb_rf_wdata(wb_value),.debug_inst(wb_inst),.selftest_status(),
        .ddr_init_done(1'b1),.ddr_axi_awaddr(awaddr),.ddr_axi_awuser_ap(),
        .ddr_axi_awuser_id(awid),.ddr_axi_awlen(awlen),.ddr_axi_awready(awready),
        .ddr_axi_awvalid(awvalid),.ddr_axi_wdata(wdata),.ddr_axi_wstrb(wstrb),
        .ddr_axi_wready(wready),.ddr_axi_wusero_id(4'b0),.ddr_axi_wusero_last(wready),
        .ddr_axi_araddr(araddr),.ddr_axi_aruser_ap(),.ddr_axi_aruser_id(arid),
        .ddr_axi_arlen(arlen),.ddr_axi_arready(arready),.ddr_axi_arvalid(arvalid),
        .ddr_axi_rdata(rdata),.ddr_axi_rid(arid),.ddr_axi_rlast(rvalid),.ddr_axi_rvalid(rvalid));
    loader_ddr_model memory(.clk(clk),.resetn(resetn),.enabled(STAGE>=3),.inject_fault(inject_fault),
        .awaddr(awaddr),.araddr(araddr),.awvalid(awvalid),.arvalid(arvalid),.wdata(wdata),.wstrb(wstrb),
        .awready(awready),.wready(wready),.arready(arready),.rvalid(rvalid),.rdata(rdata));
    // DDR is available only in fixed write/read and read-only CRC stages.
    reg [7:0] stimulus[0:16383], expected[0:32767];
    reg [31:0] frame_lengths[0:511], case_state[0:3071], ddr_state[0:2047], crc_state[0:3583];
    reg [7:0] rx_latched, decoded_byte;
    reg test_pass=0, saw_main=0, saw_sp=0, rx_pending=0;
    integer bss_start,bss_end,rodata_end,main_pc,ready_addr,ping_addr,nack_addr,stack_set_pc;
    integer last_seq_addr,boot_error_addr,recover_addr,probe_addr,rx_pc,rx_rd,recover_rx_pc,recover_rx_rd;
    integer sent=0,received=0,popped=0,read_back=0,cpu_lbu=0;
    integer tx_written=0,decoded=0,cycles=0,retired=0,peak=0;
    integer bss_clears=0,constant_reads=0,boot_checks=0,min_sp=16368;
    integer epoch,k,n,b,fd,rx_fd,frames,half,offset,expected_pings;
    integer request_bytes,response_bytes;
    integer test_count_addr,test_bytes_addr,test_crc_addr,data_crc,byte_offset,case_index,j;
    integer ddr_count_addr,ddr_bytes_addr,ddr_status_addr,ddr_write_pc,ddr_read_pc,ddr_read_rd;
    integer cpu_writes=0,cpu_reads=0,store_retired=0,load_retired=0,user_aw=0,user_w=0,user_ar=0;
    integer before_writes,before_reads,before_store,before_load,frame_end,trace_fd,expected_word,slot;
    integer crc_count_addr,crc_reads_addr,crc_actual_addr,crc_expected_addr,crc_status_addr,crc_read_pc,crc_read_rd;
    reg crc_attempt=0;
    reg write_pass=0;
    string ddr_state_path,trace_path;
    string crc_state_path;
    string lengths_path,state_path,fault_path;
    reg [31:0] faults[0:511];
    reg [31:0] virtual_cycle=0;
    integer injected_frame=0,injected_overflow=0,error_clears=0,dropped=0;
    integer pop_index=0,lbu_index=0,accepted_count=0;
    reg [7:0] accepted_stimulus[0:16383];
    integer uart_flags_addr;
    realtime case_start;
    integer timing_fd;
    string timing_path;
    // Only the MMIO cycle time source is scaled. CPU, UART, DDR remain at 93.75 MHz.
    // TIME_SCALE=1 is the independent native 100ms timeout confirmation suite.
    generate if(TIME_SCALE!=1) begin
        always @(negedge clk) begin
            if(!resetn) virtual_cycle=0;
            else virtual_cycle=virtual_cycle+TIME_SCALE;
        end
        initial force dut.u_simple_mmio.cycle_counter=virtual_cycle;
    end endgenerate
    string rx_path,tx_path,capture_path,rx_capture_path;

    function [31:0] ram_word;
        input integer address;
        begin ram_word=dut.u_data_ram.mem[address>>2]; end
    endfunction
    function [31:0] memory_crc;
        reg [31:0] crc;
        integer index,bit_no;
        begin
            crc=32'hffffffff;
            for(index=0;index<64;index=index+1) begin
                crc=crc ^ ((memory.word_at(32'h40000000+index) >> (8*(index%4))) & 255);
                for(bit_no=0;bit_no<8;bit_no=bit_no+1)
                    crc=(crc>>1) ^ (crc[0] ? 32'hedb88320 : 0);
            end
            memory_crc=~crc;
        end
    endfunction
    task check;
        input condition;
        input [1023:0] message;
        begin
            if(condition !== 1'b1)
                $fatal(1,"RESULT: FAIL uart_loader stage=%0d cycles=%0d: %0s",STAGE,cycles,message);
        end
    endtask
    task send_byte;
        input [7:0] value;
        integer bit_no;
        begin
            rxd=0; #(TBIT);
            for(bit_no=0;bit_no<8;bit_no=bit_no+1) begin rxd=value[bit_no]; #(TBIT); end
            rxd=1; #(TBIT);
        end
    endtask
    task guards;
        integer address;
        begin
            for(address=0;address<32;address=address+4)
                check(ram_word(address)===32'ha5a5a5a5,"low RAM guard modified");
            for(address=48;address<256;address=address+4)
                check(ram_word(address)===32'ha5a5a5a5,"diagnostic boundary modified");
            for(address=12288;address<12352;address=address+4)
                check(ram_word(address)===32'ha5a5a5a5,"stack bottom guard modified");
            for(address=16368;address<16384;address=address+4)
                check(ram_word(address)===32'ha5a5a5a5,"old manifest reservation modified");
        end
    endtask
    task boot_epoch;
        integer address,boot_cycles;
        begin
            @(negedge clk); resetn=0; rxd=1;
            repeat(12) @(negedge clk);
            // Poison volatile state every boot. Do not reload the RAM DAT.
            for(address=bss_start;address<bss_end;address=address+4)
                dut.u_data_ram.mem[address>>2]=32'hdededede;
            for(address=0;address<256;address=address+4)
                dut.u_data_ram.mem[address>>2]=32'ha5a5a5a5;
            for(address=12288;address<16384;address=address+4)
                dut.u_data_ram.mem[address>>2]=32'ha5a5a5a5;
            for(address=8192;address<8448;address=address+4)
                dut.u_data_ram.mem[address>>2]=32'hcccccccc;
            saw_main=0; saw_sp=0; bss_clears=0; constant_reads=0;
            @(negedge clk); resetn=1;
            boot_cycles=0;
            while(ram_word(ready_addr)!==32'h52454144 && boot_cycles<40000) begin
                @(negedge clk); boot_cycles=boot_cycles+1;
            end
            if(ram_word(ready_addr)!==32'h52454144)
                $fatal(1,"RESULT: FAIL boot timeout pc=%h error=%h diag=%h/%h/%h/%h",dut.u_cpu.pc,ram_word(boot_error_addr),ram_word(32),ram_word(36),ram_word(40),ram_word(44));
            @(negedge clk);
            check(saw_main && saw_sp,"ready before startup/main");
            check(ram_word(boot_error_addr)===0,"software ROM/RAM self-check failed");
            check(ram_word(32)===32'h929a5e56,"RAM constant XOR");
            check(ram_word(36)===32'hcbf43926 && ram_word(40)===0,"CRC vectors");
            check(ram_word(44)===0,"boot diagnostics nonzero");
            check(ram_word(ping_addr)===0 && ram_word(nack_addr)===0,"counters retained across reset");
            if(STAGE>=2) check(ram_word(test_count_addr)===0 && ram_word(test_bytes_addr)===0 &&
                              ram_word(test_crc_addr)===0,"RX test state retained across reset");
            if(STAGE>=3) check(ram_word(ddr_count_addr)===0 && ram_word(ddr_bytes_addr)===0 &&
                              ram_word(ddr_status_addr)===0,"DDR diagnostics retained across reset");
            if(STAGE==4) check(ram_word(crc_count_addr)===0 && ram_word(crc_reads_addr)===0 &&
                              ram_word(crc_actual_addr)===0 && ram_word(crc_expected_addr)===0 &&
                              ram_word(crc_status_addr)===0,"DDR CRC diagnostics retained across reset");
            check(constant_reads>=4,"no data-bus RAM constant reads");
            check(dut.u_uart_mmio.rx_irq_enable===0,"UART RX IRQ enabled");
            check(dut.u_cpu.u_csr_file.irq_global_enable===0,"CPU MIE enabled");
            for(address=0;address<8;address=address+1)
                check(ram_word(probe_addr+address*4)==32'hb5500000+address,"post-clear BSS probe");
            guards(); boot_checks=boot_checks+1;
            $display("CHECK: ROM boot epoch=%0d BSS_clears=%0d constants=%0d sp=00003ff0 CRC=cbf43926",epoch,bss_clears,constant_reads);
        end
    endtask
    task fixed_transact;
        input integer frame_index;
        integer byte_no,address,verify_index;
        begin
            if(STAGE>=3) begin
                crc_attempt=STAGE==4 && crc_state[frame_index*7+5]!=0;
                ddr_allowed=ddr_state[frame_index*4+1]!=0 || crc_attempt;
                inject_fault=ddr_state[frame_index*4+2]!=0;
                before_writes=cpu_writes;before_reads=cpu_reads;
                before_store=store_retired;before_load=load_retired;write_pass=crc_attempt;
                frame_end=byte_offset+frame_lengths[frame_index];
            end
            case_start=$realtime;
            verify_index=frame_index+(faults[frame_index]==3 ? 1 : 0);
            if(faults[frame_index]==1) begin
                // Physical BREAK: only RX pin is driven; original clocks/CPU stay active.
                rxd=0; #20000000.0; rxd=1; #(TBIT*2.0);
                check(injected_frame==1,"BREAK did not generate exactly one frame error");
            end
            for(byte_no=0;byte_no<frame_lengths[frame_index];byte_no=byte_no+1) begin
                send_byte(stimulus[byte_offset+byte_no]); sent=sent+1;
            end
            wait(decoded >= (verify_index+1)*60);
            wait(!dut.u_uart_mmio.tx_busy);
            repeat(50) @(negedge clk);
            if(case_state[verify_index*6+4])
                while(ram_word(recover_addr)!==0) @(negedge clk);
            check(ram_word(ping_addr)==case_state[verify_index*6],"fixed suite PING count");
            check(ram_word(test_count_addr)==case_state[verify_index*6+1],"fixed receive count/duplicate");
            check(ram_word(test_bytes_addr)==64*case_state[verify_index*6+1],"fixed byte count");
            check(ram_word(test_crc_addr)==(case_state[verify_index*6+1] ? data_crc : 0),"CPU RAM diagnostic CRC");
            check(ram_word(nack_addr)==case_state[verify_index*6+2],"fixed suite NACK count");
            check(ram_word(last_seq_addr)==case_state[verify_index*6+3],"fixed suite sequence state");
            if(STAGE>=3) begin
                check(ram_word(ddr_count_addr)==ddr_state[verify_index*4],"DDR success/duplicate count");
                check(ram_word(ddr_bytes_addr)==64*ddr_state[verify_index*4],"DDR verified byte count");
                check(ram_word(ddr_status_addr)==ddr_state[verify_index*4+3],"DDR compare diagnostic status");
                check(cpu_writes-before_writes==16*ddr_state[verify_index*4+1] &&
                      cpu_reads-before_reads==16*(ddr_state[verify_index*4+1]+crc_attempt) &&
                      store_retired-before_store==16*ddr_state[verify_index*4+1] &&
                      load_retired-before_load==16*(ddr_state[verify_index*4+1]+crc_attempt),"DDR write/read/retirement counts");
                if(ddr_allowed) begin
                    check(write_pass,"read/compare before DDR write PASS");
                    for(byte_no=0;byte_no<64;byte_no=byte_no+1) begin
                        address=8320+byte_no;
                        check(((ram_word(address)>>(8*(address%4)))&255)==
                              ((memory.word_at(32'h40000000+byte_no)>>(8*(byte_no%4)))&255),"RAM readback not actual DDR");
                    end
                end
                for(address=4;address<4096;address=address+1)
                    check(memory.beats[address]=={4{32'ha5a5a5a5}},"DDR outside fixed64 modified");
                if(STAGE==4) begin
                    check(ram_word(crc_count_addr)==crc_state[verify_index*7] &&
                          ram_word(crc_reads_addr)==crc_state[verify_index*7+1],"CRC count/duplicate read count");
                    check(ram_word(crc_actual_addr)==crc_state[verify_index*7+2] &&
                          ram_word(crc_expected_addr)==crc_state[verify_index*7+3] &&
                          ram_word(crc_status_addr)==crc_state[verify_index*7+4],"CPU DDR CRC actual/expected/status");
                    check(memory_crc()==crc_state[verify_index*7+6],"physical DDR CRC differs from Python oracle");
                    $display("CHECK: CRC case=%0d reads=%0d success=%0d actual=%08h expected=%08h status=%08h",frame_index,
                             ram_word(crc_reads_addr),ram_word(crc_count_addr),ram_word(crc_actual_addr),
                             ram_word(crc_expected_addr),ram_word(crc_status_addr));
                end
                ddr_allowed=0;inject_fault=0;crc_attempt=0;
            end
            if(case_state[verify_index*6+5]) begin
                for(byte_no=0;byte_no<64;byte_no=byte_no+1) begin
                    address=8192+32+byte_no;
                    check(((ram_word(address) >> (8*(address%4))) & 255)==stimulus[byte_offset+32+byte_no],"RX payload in RAM differs");
                end
            end
            for(address=8292;address<8448;address=address+4)
                if(STAGE<3 || address<8320 || address>=8384)
                    check(ram_word(address)===32'hcccccccc,"RX buffer upper guard modified");
            check(dut.u_uart_mmio.fifo_empty,"FIFO not empty after fixed transaction");
            check(!dut.u_uart_mmio.frame_error_status && !dut.u_uart_mmio.overflow_status,"sticky errors not cleared after recovery");
            $fdisplay(timing_fd,"%0d,%0f",frame_index,($realtime-case_start)/1.0e9);
            $display("CHECK: timing case=%0d seconds=%0f TIME_SCALE=%0d",frame_index,($realtime-case_start)/1.0e9,TIME_SCALE);
            if(faults[frame_index]==1) check(ram_word(uart_flags_addr)==16,"frame snapshot not raw STATUS[4]");
            if(faults[frame_index]==3) begin
                check(injected_overflow>0 && peak==16,"wire flood did not fill and overflow real FIFO");
                check(injected_frame==1 && ram_word(uart_flags_addr)==32,"overflow mistaken for frame error");
            end
            byte_offset=byte_offset+frame_lengths[frame_index];
            $display("CHECK: RX case=%0d pings=%0d tests=%0d nacks=%0d last_seq=%0d",frame_index,
                     ram_word(ping_addr),ram_word(test_count_addr),ram_word(nack_addr),ram_word(last_seq_addr));
        end
    endtask
    task transact;
        input integer frame_index;
        integer j;
        begin
            // No inter-byte gap: service the real 16-byte FIFO by CPU polling.
            for(j=0;j<36;j=j+1) begin
                send_byte(stimulus[frame_index*36+j]); sent=sent+1;
            end
            wait(decoded >= (frame_index+1)*60);
            wait(!dut.u_uart_mmio.tx_busy);
            repeat(50) @(negedge clk);
        end
    endtask

    initial begin
        check($value$plusargs("UART_FLAGS=%h",uart_flags_addr),"missing UART_FLAGS");
        check($value$plusargs("BSS_START=%h",bss_start),"missing BSS_START");
        check($value$plusargs("BSS_END=%h",bss_end),"missing BSS_END");
        check($value$plusargs("RODATA_END=%h",rodata_end),"missing RODATA_END");
        check($value$plusargs("MAIN=%h",main_pc),"missing MAIN");
        check($value$plusargs("STACK_SET=%h",stack_set_pc),"missing STACK_SET");
        check($value$plusargs("READY=%h",ready_addr),"missing READY");
        check($value$plusargs("PING_ADDR=%h",ping_addr),"missing PING_ADDR");
        check($value$plusargs("NACK_ADDR=%h",nack_addr),"missing NACK_ADDR");
        check($value$plusargs("LAST_SEQ=%h",last_seq_addr),"missing LAST_SEQ");
        check($value$plusargs("BOOT_ERROR=%h",boot_error_addr),"missing BOOT_ERROR");
        check($value$plusargs("RECOVER=%h",recover_addr),"missing RECOVER");
        check($value$plusargs("PROBE=%h",probe_addr),"missing PROBE");
        check($value$plusargs("RX_PC=%h",rx_pc),"missing RX_PC");
        check($value$plusargs("RX_RD=%d",rx_rd),"missing RX_RD");
        check($value$plusargs("RECOVER_RX_PC=%h",recover_rx_pc),"missing RECOVER_RX_PC");
        check($value$plusargs("RECOVER_RX_RD=%d",recover_rx_rd),"missing RECOVER_RX_RD");
        check($value$plusargs("CAPTURE=%s",capture_path),"missing capture path");
        check($value$plusargs("RX_CAPTURE=%s",rx_capture_path),"missing RX capture");
        fd=$fopen(capture_path,"wb"); rx_fd=$fopen(rx_capture_path,"wb");
        check(fd!=0 && rx_fd!=0,"cannot open capture");
        if(STAGE>=2) begin
            check($value$plusargs("TEST_COUNT=%h",test_count_addr),"missing TEST_COUNT");
            check($value$plusargs("TEST_BYTES=%h",test_bytes_addr),"missing TEST_BYTES");
            check($value$plusargs("TEST_CRC=%h",test_crc_addr),"missing TEST_CRC");
            check($value$plusargs("DATA_CRC=%h",data_crc),"missing DATA_CRC");
            check($value$plusargs("LENGTHS=%s",lengths_path),"missing LENGTHS");
            check($value$plusargs("CASE_STATE=%s",state_path),"missing CASE_STATE");
            $readmemh(lengths_path,frame_lengths,0,STAGE==4 ? CASES-1 : STAGE==3 ? 16 : 13);
            $readmemh(state_path,case_state,0,STAGE==4 ? CASES*6-1 : STAGE==3 ? 101 : 83);
        end
        if(STAGE>=3) begin
            check($value$plusargs("DDR_COUNT=%h",ddr_count_addr),"missing DDR_COUNT");
            check($value$plusargs("DDR_BYTES=%h",ddr_bytes_addr),"missing DDR_BYTES");
            check($value$plusargs("DDR_STATUS=%h",ddr_status_addr),"missing DDR_STATUS");
            check($value$plusargs("DDR_WRITE_PC=%h",ddr_write_pc),"missing DDR_WRITE_PC");
            check($value$plusargs("DDR_READ_PC=%h",ddr_read_pc),"missing DDR_READ_PC");
            check($value$plusargs("DDR_READ_RD=%d",ddr_read_rd),"missing DDR_READ_RD");
            check($value$plusargs("DDR_STATE=%s",ddr_state_path),"missing DDR_STATE");
            check($value$plusargs("TRACE=%s",trace_path),"missing TRACE");
            $readmemh(ddr_state_path,ddr_state,0,STAGE==4 ? CASES*4-1 : 67);trace_fd=$fopen(trace_path,"w");
            check(trace_fd!=0,"DDR trace open");
        end
        if(STAGE==4) begin
            check($value$plusargs("CRC_COUNT=%h",crc_count_addr),"missing CRC_COUNT");
            check($value$plusargs("CRC_READS=%h",crc_reads_addr),"missing CRC_READS");
            check($value$plusargs("CRC_ACTUAL=%h",crc_actual_addr),"missing CRC_ACTUAL");
            check($value$plusargs("CRC_EXPECTED=%h",crc_expected_addr),"missing CRC_EXPECTED");
            check($value$plusargs("CRC_STATUS=%h",crc_status_addr),"missing CRC_STATUS");
            check($value$plusargs("CRC_READ_PC=%h",crc_read_pc),"missing CRC_READ_PC");
            check($value$plusargs("CRC_READ_RD=%d",crc_read_rd),"missing CRC_READ_RD");
            check($value$plusargs("CRC_STATE=%s",crc_state_path),"missing CRC_STATE");
            $readmemh(crc_state_path,crc_state,0,CASES*7-1);
            check($value$plusargs("FAULTS=%s",fault_path),"missing FAULTS");
            $readmemh(fault_path,faults,0,CASES-1);
            check($value$plusargs("TIMING=%s",timing_path),"missing TIMING");
            timing_fd=$fopen(timing_path,"w"); check(timing_fd!=0,"timing file");
        end
        if(STAGE!=0) begin
            check($value$plusargs("STIMULUS=%s",rx_path),"missing stimulus");
            check($value$plusargs("EXPECTED=%s",tx_path),"missing expected");
            frames=STAGE==4 ? CASES : STAGE==3 ? 17 : STAGE==2 ? 14 : PING_COUNT+4;
            request_bytes=STAGE>=2 ? 0 : frames*36; response_bytes=frames*60;
            if(STAGE>=2) for(j=0;j<frames;j=j+1) request_bytes=request_bytes+frame_lengths[j];
            $readmemh(rx_path,stimulus,0,request_bytes-1);
            $readmemh(tx_path,expected,0,response_bytes-1);
        end else begin request_bytes=0; response_bytes=0; end
        #200;
        if(STAGE==0) begin
            for(epoch=0;epoch<3;epoch=epoch+1) begin
                boot_epoch(); repeat(200) @(negedge clk); guards();
                check(ram_word(ready_addr)!==0,"reset dirty state was not retained for next boot");
            end
            check(sent==0 && decoded==0 && tx_written==0,"residency stage emitted UART bytes");
        end else if(STAGE>=2) begin
            byte_offset=0;
            for(epoch=0;epoch<(STAGE==4 ? 1 : 2);epoch=epoch+1) begin
                boot_epoch();
                for(case_index=(epoch==0 ? 0 : STAGE==4 ? CASES : STAGE==3 ? 12 : 10);case_index<(epoch==0 ? (STAGE==4 ? CASES : STAGE==3 ? 12 : 10) : frames);case_index=case_index+1)
                    if(faults[case_index]!=4) fixed_transact(case_index);
                guards();
            end
            #(TBIT*20.0);
            check(sent==request_bytes && received==sent && popped==sent-dropped && read_back==sent-dropped && cpu_lbu==sent-dropped,"fixed RX/pop/MMIO/CPU LBU counts differ");
            check(tx_written==response_bytes && decoded==response_bytes,"fixed TX byte count");
        end else begin
            check(PING_COUNT>=2 && PING_COUNT<=200,"bad PING_COUNT");
            half=PING_COUNT/2; offset=0;
            for(epoch=0;epoch<2;epoch=epoch+1) begin
                boot_epoch();
                expected_pings=epoch==0 ? half : PING_COUNT-half;
                for(n=0;n<expected_pings;n=n+1) begin
                    transact(offset); offset=offset+1;
                    check(ram_word(ping_addr)==n+1,"PING counted incorrectly");
                    check(ram_word(last_seq_addr)==n+1,"PING sequence not updated");
                end
                if(epoch==0) begin
                    // Same PING sequence is ACKed without incrementing count.
                    transact(offset); offset=offset+1;
                    check(ram_word(ping_addr)==half,"duplicate PING executed twice");
                    // LOAD, VERIFY and RUN must all remain rejected at stage 1.
                    for(n=0;n<3;n=n+1) begin
                        transact(offset); offset=offset+1;
                        while(ram_word(recover_addr)!==0) @(negedge clk);
                        check(ram_word(nack_addr)==n+1,"unsupported command not NACKed");
                        check(ram_word(ping_addr)==half,"unsupported command changed PING state");
                    end
                end
                guards(); check(dut.u_uart_mmio.fifo_empty,"FIFO not empty after epoch");
            end
            #(TBIT*20.0);
            check(sent==request_bytes && received==sent && popped==sent && read_back==sent && cpu_lbu==sent,"RX pin/pop/MMIO/retired LBU counts differ");
            check(tx_written==response_bytes && decoded==response_bytes,"TX count or extra response");
        end
        guards(); test_pass=1;
        if(injected_frame+injected_overflow>0) check(error_clears>=2 && accepted_count==popped,"CPU did not clear/drain each real UART error");
        $fclose(fd); $fclose(rx_fd);
        if(STAGE>=3) begin
            check(cpu_writes==(STAGE==4 ? 16 : 80) && cpu_reads==(STAGE==4 ? 16*(1+crc_state[(CASES-1)*7+1]) : 80) &&
                  user_aw==cpu_writes && user_w==cpu_writes && user_ar==cpu_reads &&
                  store_retired==cpu_writes && load_retired==cpu_reads,"DDR total transaction counts");
            $fclose(trace_fd); if(STAGE==4) $fclose(timing_fd);
            $display("CHECK: DDR total SW=%0d LW=%0d user_AW/W=%0d AR=%0d",cpu_writes,cpu_reads,user_w,user_ar);
        end
        $display("CHECK: WIRE_ERRORS frame=%0d overflow=%0d dropped=%0d clears=%0d accepted=%0d",injected_frame,injected_overflow,dropped,error_clears,accepted_count);
        $display("RESULT: PASS uart_loader stage=%0d boots=%0d pings=%0d fixed_unique=%0d RX=%0d pop=%0d MMIO=%0d LBU=%0d TX=%0d decoded=%0d fifo_peak=%0d min_sp=%08h retired=%0d cycles=%0d DDR_SW=%0d DDR_LW=%0d",STAGE,boot_checks,STAGE==1 ? PING_COUNT : STAGE==4 ? 3 : STAGE>=2 ? 4 : 0,STAGE==2 ? 4 : STAGE==3 ? 2 : STAGE==4 ? 1 : 0,received,popped,read_back,cpu_lbu,tx_written,decoded,peak,min_sp,retired,cycles,cpu_writes,cpu_reads);
        $finish;
    end

    always @(posedge clk) if(resetn) begin
        cycles=cycles+1;
        check(!dut.u_cpu.sync_trap_event && !dut.u_cpu.irq_take,"unexpected CPU trap/IRQ");
        check(!(dut.inst_rsp_valid && dut.inst_rsp_error) && !(dut.data_rsp_valid && dut.data_rsp_error),"bus error");
        check(!dut.inst_ddr_req_valid,"unexpected DDR instruction fetch");
        if(STAGE<3 || !ddr_allowed)
            check(!dut.data_ddr_req_valid && !awvalid && !arvalid,"unexpected DDR request");
        if(STAGE!=4 || faults[case_index]==0) begin
            check(!dut.u_uart_mmio.frame_error_status && !dut.u_uart_mmio.overflow_status,"unexpected UART sticky error");
            check(!dut.u_uart_mmio.frame_error && !dut.u_uart_mmio.overflow,"unexpected UART event error");
        end
        if(dut.u_uart_mmio.frame_error) injected_frame=injected_frame+1;
        if(dut.u_uart_mmio.overflow) begin injected_overflow=injected_overflow+1; dropped=dropped+1; end
        if(dut.u_uart_mmio.req_valid && dut.u_uart_mmio.req_ready && dut.u_uart_mmio.req_write &&
           dut.u_uart_mmio.req_addr[3:0]==12 && dut.u_uart_mmio.req_wdata[1:0]==3 && injected_frame+injected_overflow>0)
            error_clears=error_clears+1;
        if(dut.u_uart_mmio.fifo_count>peak) peak=dut.u_uart_mmio.fifo_count;
        if(dut.inst_req_valid) check(dut.inst_req_addr<32'h4000 && dut.inst_req_addr[1:0]==0,"not executing aligned ROM instructions");
        if(dut.data_req_valid && dut.data_req_ready) begin
            if(!dut.data_req_write && dut.data_req_addr>=256 && dut.data_req_addr<rodata_end)
                constant_reads=constant_reads+1;
            if(dut.data_req_write && dut.data_req_addr<32'h4000) begin
                check((dut.data_req_addr>=bss_start && dut.data_req_addr<bss_end) ||
                      (dut.data_req_addr>=32 && dut.data_req_addr<48) ||
                      (dut.data_req_addr>=8192 && dut.data_req_addr<8448) ||
                      (dut.data_req_addr>=12352 && dut.data_req_addr<16368),"RAM write outside mutable partitions/stack guard");
                if(!saw_main && dut.data_req_addr>=bss_start && dut.data_req_addr<bss_end) begin
                    check(dut.data_req_addr==bss_start+4*bss_clears && dut.data_req_wdata===0 && dut.data_req_wstrb==15,"BSS startup clear wrong address/value/strobe");
                    bss_clears=bss_clears+1;
                end
            end
        end
        if(dut.u_cpu.normal_retire) begin
            if(STAGE>=3 && wb_pc==ddr_write_pc) begin
                check(ddr_allowed && !crc_attempt && store_retired-before_store<16,"unexpected DDR SW retirement");
                store_retired=store_retired+1;
                if(store_retired-before_store==16) begin
                    check(user_w==cpu_writes,"SW retired before Pango write complete");
                    for(j=0;j<16;j=j+1)
                        check(memory.word_at(32'h40000000+4*j)=={stimulus[byte_offset+35+4*j],stimulus[byte_offset+34+4*j],stimulus[byte_offset+33+4*j],stimulus[byte_offset+32+4*j]},"DDR content after writes");
                    write_pass=1;
                    $display("CHECK: CPU DDR write PASS case=%0d SW=16 four128bitbeats",case_index);
                end
            end
            if(STAGE>=3 && (wb_pc==ddr_read_pc || (STAGE==4 && wb_pc==crc_read_pc))) begin
                check((wb_pc==crc_read_pc)==crc_attempt || STAGE!=4,"wrong DDR LW routine");
                check(ddr_allowed && write_pass && load_retired-before_load<16,"DDR LW before write gate");
                check(wb_we==15 && wb_rd==(crc_attempt ? crc_read_rd : ddr_read_rd) && wb_value===memory.word_at(32'h40000000+4*(load_retired-before_load)),"DDR LW retired value/source");
                $fdisplay(trace_fd,"%0s,%08h,%08h",crc_attempt ? "CRC_LW_RETIRE" : "LW_RETIRE",32'h40000000+4*(load_retired-before_load),wb_value);
                load_retired=load_retired+1;
            end
            retired=retired+1;
            if(wb_we==15 && wb_rd==2) begin
                if(!saw_sp && wb_pc!=stack_set_pc) begin
                    check(wb_pc==stack_set_pc-4 && wb_inst[6:0]==7'h17,"unexpected SP initialization instruction");
                end else begin
                    check(wb_value>=12352 && wb_value<=16368 && wb_value[3:0]==0,"SP outside aligned Loader stack");
                    if(!saw_sp) begin check(wb_value==16368,"initial SP"); saw_sp=1; end
                    if(wb_value<min_sp) min_sp=wb_value;
                end
            end
            if(wb_pc==main_pc && !saw_main) begin
                check(saw_sp && bss_clears*4==bss_end-bss_start,"main before full BSS initialization");
                for(k=bss_start;k<bss_end;k=k+4) check(ram_word(k)===0,"BSS nonzero at main");
                saw_main=1;
            end
            if(wb_pc==rx_pc || wb_pc==recover_rx_pc) begin
                
                check(wb_we==15 && wb_rd==(wb_pc==rx_pc ? rx_rd : recover_rx_rd) && cpu_lbu<read_back && wb_value=={24'b0,accepted_stimulus[lbu_index]},"retired CPU LBU differs from UART input");
                cpu_lbu=cpu_lbu+1;lbu_index=lbu_index+1;
            end
        end
        if(dut.u_uart_mmio.rx_valid) begin
            check(received<request_bytes && dut.u_uart_mmio.rx_data===stimulus[received],"RX pin decoder differs from stimulus");
            $fwrite(rx_fd,"%c",dut.u_uart_mmio.rx_data); received=received+1;
            if(!dut.u_uart_mmio.fifo_full || dut.u_uart_mmio.fifo_pop) begin
                accepted_stimulus[accepted_count]=dut.u_uart_mmio.rx_data; accepted_count=accepted_count+1;
            end
        end
        if(dut.u_uart_mmio.fifo_pop) begin
            
            check(popped<received && dut.u_uart_mmio.fifo_data===accepted_stimulus[pop_index],"FIFO pop value/order");
            check(!rx_pending,"duplicate RX request");
            rx_latched=dut.u_uart_mmio.fifo_data; rx_pending=1; popped=popped+1;pop_index=pop_index+1;
        end
        if(dut.u_uart_mmio.rsp_valid && rx_pending) begin
            check(!dut.u_uart_mmio.rsp_error && dut.u_uart_mmio.rsp_rdata=={24'b0,rx_latched},"MMIO RX response differs from accepted pop");
            rx_pending=0; read_back=read_back+1;
        end
        if(dut.u_uart_mmio.tx_send) begin
            check(tx_written<response_bytes && dut.u_uart_mmio.req_wstrb==1 && dut.u_uart_mmio.req_wdata[7:0]===expected[tx_written],"MMIO TX differs from Python response/CRC");
            tx_written=tx_written+1;
        end
    end
    always @(posedge clk) if(resetn && STAGE>=3) begin
        if(dut.data_ddr_req_valid && dut.data_ddr_req_ready) begin
            check(ddr_allowed && cpu_lbu+dropped>=frame_end,"DDR before complete validated UART packet");
            check(dut.data_ddr_req_size==2 && dut.data_ddr_req_addr[1:0]==0,"DDR CPU width/alignment");
            if(dut.data_ddr_req_write) begin
                slot=cpu_writes-before_writes;
                check(!crc_attempt && slot<16 && dut.data_ddr_req_addr==4*slot && dut.data_ddr_req_wstrb==15,"DDR CPU SW address/strobe");
                expected_word={stimulus[byte_offset+35+4*slot],stimulus[byte_offset+34+4*slot],stimulus[byte_offset+33+4*slot],stimulus[byte_offset+32+4*slot]};
                check(dut.data_ddr_req_wdata===expected_word,"DDR CPU SW data");
                $fdisplay(trace_fd,"SW_REQ,%08h,%08h",32'h40000000+4*slot,expected_word);
                cpu_writes=cpu_writes+1;
            end else begin
                check(write_pass,"DDR CPU read before write PASS");slot=cpu_reads-before_reads;
                check(slot<16 && dut.data_ddr_req_addr==4*slot,"DDR CPU LW address");cpu_reads=cpu_reads+1;
            end
        end
        if(awvalid && awready) begin
            slot=user_aw-before_writes;
            check(ddr_allowed && !crc_attempt && slot<16 && awaddr==(slot/4)*8 && awlen==0 && awid==1,"Pango AW address/length/id");
            check(wstrb==(16'hf<<((slot%4)*4)),"Pango write lane/strobe");
            expected_word={stimulus[byte_offset+35+4*slot],stimulus[byte_offset+34+4*slot],stimulus[byte_offset+33+4*slot],stimulus[byte_offset+32+4*slot]};
            check(wdata===({96'b0,expected_word}<<((slot%4)*32)),"Pango 128-bit write placement");
            $fdisplay(trace_fd,"AW,%08h,%04h,%032h",awaddr,wstrb,wdata);user_aw=user_aw+1;
        end
        if(wready) begin check(ddr_allowed && user_w<user_aw,"unexpected Pango W acceptance");user_w=user_w+1;end
        if(arvalid && arready) begin
            slot=user_ar-before_reads;
            check(ddr_allowed && write_pass && slot<16 && araddr==(slot/4)*8 && arlen==0,"Pango AR address/length");
            $fdisplay(trace_fd,"AR,%08h",araddr);user_ar=user_ar+1;
        end
    end
    initial forever begin
        @(negedge txd);
        if(resetn) begin
            #(TBIT/2.0); check(txd===0,"TX start bit"); decoded_byte=0;
            for(b=0;b<8;b=b+1) begin #(TBIT); decoded_byte[b]=txd; end
            #(TBIT); check(txd===1,"TX stop bit");
            check(decoded<response_bytes && decoded_byte===expected[decoded],"TXD independent decoder differs from response bytes");
            $fwrite(fd,"%c",decoded_byte); decoded=decoded+1;
        end
    end
    initial begin
        #20000000000.0;
        $fatal(1,"RESULT: FAIL uart_loader timeout stage=%0d rx=%0d tx=%0d decoded=%0d ready=%h pc=%h",STAGE,received,tx_written,decoded,ram_word(ready_addr),dut.u_cpu.pc);
    end
endmodule
