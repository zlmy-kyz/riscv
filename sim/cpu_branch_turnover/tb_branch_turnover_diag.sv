`timescale 1ns/1ps
module tb_branch_turnover_diag #(parameter integer ENABLE=1);
    localparam [31:0] BASE=32'h80000000,DATA=32'h80003000,STATUS=32'h80003ffc;
    reg clk=0,resetn=0,irq=0,checking=0;
    wire iv,iready,ir,ie,dv,dw,dready,rv,rom_ready,rom_valid;
    wire [31:0] ia,idata,da,wd,rom_addr;
    wire [3:0] ws;wire [1:0] ds;
    reg rom_rsp=0,rom_error=0,dr=0,de=0,ipending=0,dpending=0;
    reg [31:0] rom_data=0,ddata=0,saved_i=0,saved_d=0;
    reg saved_error=0;
    integer itimer=0,dtimer=0,cycle=0,profile=0;
    reg [31:0] rom[0:4095],ram[0:4095];
    integer kind[0:9999],wren[0:9999],rd[0:9999];
    reg [31:0] gpc[0:9999],ginst[0:9999],gvalue[0:9999],gcause[0:9999],gtval[0:9999];
    integer index=0,events=0,total_events=0,case_count=0,fd=0,trace_fd=0,spec_fd=0,i,j,n,c;
    integer fast=0,empty_fast=0,response_fast=0,late_wait=0,ready_wait=0,buffer_flush=0;
    integer discarded_errors=0,load_stalls=0,traps=0,irqs=0,resets=0;
    integer reset_case=0,expected_cases=0;
    reg fault_sent=0,irq_sent=0,status_seen=0,finish_pending=0,csr_check=0,check_if=0;
    reg [31:0] if_fault=0,data_fault=0,irq_load=0,memory_target=0;
    reg [31:0] csr_pc=0,csr_cause=0,csr_tval=0,expect_pc=0,expect_pending_pc=0;
    reg expect_new_pending=0;
    string name,rom_path,oracle_path,spec_path,event_path;
    always #5 clk=~clk;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    mycpu_sync #(.RESET_PC(BASE),.BRANCH_FETCH_TURNOVER_ENABLE(ENABLE)) dut(
        .clk(clk),.resetn(resetn),.irq_external(irq),.irq_software(1'b0),.irq_timer(1'b0),.memory_order_busy(1'b0),
        .inst_req_valid(iv),.inst_req_addr(ia),.inst_req_ready(iready),.inst_rsp_valid(ir),.inst_rsp_rdata(idata),.inst_rsp_error(ie),
        .data_req_valid(dv),.data_req_write(dw),.data_req_size(ds),.data_req_addr(da),.data_req_wdata(wd),.data_req_wstrb(ws),
        .data_req_ready(dready),.data_rsp_valid(dr),.data_rsp_rdata(ddata),.data_rsp_error(de),
        .debug_wb_pc(),.debug_wb_rf_we(),.debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(),
        .perf_events(),.perf_branch_target(),.perf_fetch_pc());
    inst_bus_interconnect #(.ROM_BASE(BASE)) bus(
        .clk(clk),.resetn(resetn),.m_req_valid(iv),.m_req_addr(ia),.m_req_ready(iready),
        .m_rsp_valid(ir),.m_rsp_rdata(idata),.m_rsp_error(ie),
        .rom_req_valid(rom_valid),.rom_req_addr(rom_addr),.rom_req_ready(rom_ready),
        .rom_rsp_valid(rom_rsp),.rom_rsp_rdata(rom_data),.rom_rsp_error(rom_error),
        .ddr_req_valid(),.ddr_req_addr(),.ddr_req_ready(1'b0),.ddr_rsp_valid(1'b0),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0));
    // Profile 2 deliberately denies the target on the redirect edge; next edge is free.
    // This is stimulus only. Architectural expected values come solely from fixtures.
    assign rom_ready=resetn && (!ipending || rom_rsp) && !(profile==2 && dut.branch_redirect);
    assign dready=resetn && !dpending && !dr && cycle%5!=1;
    task automatic fail(input string reason);
        if(reason=="coverage totals")
            $display("COVERAGE_DIAG enable=%0d cases=%0d events=%0d FAST=%0d EMPTY=%0d RSP=%0d LATE=%0d READY=%0d BUFFER=%0d DROP_ERR=%0d LOAD=%0d TRAP=%0d IRQ=%0d RESET=%0d",
                ENABLE,case_count,total_events,fast,empty_fast,response_fast,late_wait,ready_wait,buffer_flush,discarded_errors,load_stalls,traps,irqs,resets);
        $display("RESULT: FAIL branch_turnover case=%s event=%0d pc=%h inst=%h cause=%0d tval=%h %s",
            name,index,dut.mem_wb_pc,dut.mem_wb_inst,dut.wb_trap_cause,dut.wb_trap_tval,reason);
        if(trace_fd) $fflush(trace_fd);$fatal(1);
    endtask
    function automatic fault_i(input [31:0] addr);
        // Illegal/error payload on skipped wrong-path stores must never retire or trap.
        fault_i=(BASE+addr==if_fault) || (rom[addr[13:2]]==32'h000f2023);
    endfunction
    always @(posedge clk) begin
        if(!resetn) begin
            rom_rsp<=0;rom_error<=0;dr<=0;de<=0;ipending<=0;dpending<=0;itimer<=0;dtimer<=0;cycle<=0;
            fault_sent<=0;irq_sent<=0;irq<=0;status_seen<=0;
        end else begin
            cycle<=cycle+1;rom_rsp<=0;rom_error<=0;dr<=0;de<=0;
            if(ipending) begin
                if(itimer==0) begin
                    rom_data<=rom[saved_i[13:2]];rom_error<=fault_i(saved_i);rom_rsp<=1;ipending<=0;
                end else itimer<=itimer-1;
            end
            if(rom_valid && rom_ready) begin
                if(rom_addr[1:0]!=0 || rom_addr>=32'h4000) fail("unaligned/out of range fetch");
                if(profile==0 || profile==2) begin rom_data<=rom[rom_addr[13:2]];rom_error<=fault_i(rom_addr);rom_rsp<=1;end
                else begin
                    saved_i<=rom_addr;ipending<=1;
                    // Skipped stores are intentionally slow; old pending must drain.
                    itimer<=(rom[rom_addr[13:2]]==32'h000f2023)?12:((rom_addr>>2)%3);
                end
            end
            if(dv&&dready) begin
                if(da<BASE || da>=BASE+32'h4000) fail("unexpected data side effect/address");
                saved_d<=da;dpending<=1;
                saved_error<=!dw && da==data_fault && !fault_sent;
                if(!dw && da==data_fault) fault_sent<=1;
                dtimer<=dw?cycle%4:20;
                if(dw) begin
                    for(j=0;j<4;j=j+1) if(ws[j]) ram[da[13:2]][8*j+:8]<=wd[8*j+:8];
                    if(da==STATUS) begin if(ws!=15 || wd!=1) fail("wrong-path/failing status store");status_seen<=1;end
                end
                if(!dw && da==irq_load && !irq_sent) begin irq<=1;irq_sent<=1;end
            end
            if(dpending) begin
                if(dtimer==0) begin dr<=1;de<=saved_error;ddata<=ram[saved_d[13:2]];dpending<=0;end
                else dtimer<=dtimer-1;
            end
            if(dut.irq_take) irq<=0;
        end
    end
    // Check launch slot, target, PC advance, and suppression independently of returned values.
    always @(posedge clk) begin : observe
        integer k;
        if(!resetn) begin index=0;finish_pending=0;csr_check=0;check_if=0;end
        else if(checking) begin
            if(dut.load_use) load_stalls=load_stalls+1;
            if(ir && ie && (dut.inst_pending_drop || dut.branch_redirect)) discarded_errors=discarded_errors+1;
            if(dut.trap_redirect_req || dut.mret_redirect_req) begin
                if(iv) fail("trap/MRET issued redirect-edge fetch");
            end
            if(dut.branch_redirect) begin
                check_if=1;expect_pc=dut.redirect_pc;expect_new_pending=0;
                if(dut.inst_buffer_valid) buffer_flush=buffer_flush+1;
                if(!ENABLE) begin if(iv) fail("disabled control launched on branch");end
                else if(dut.inst_pending && !ir) begin
                    late_wait=late_wait+1;if(iv) fail("reused outstanding slot before response");
                end else begin
                    if(!iv || ia!==dut.redirect_pc) fail("eligible branch did not present target");
                    if(iready) begin
                        fast=fast+1;if(dut.inst_pending) response_fast=response_fast+1;else empty_fast=empty_fast+1;
                        expect_pc=dut.redirect_pc+4;expect_pending_pc=ia;expect_new_pending=1;
                    end else ready_wait=ready_wait+1;
                end
            end
            if(dut.normal_retire || dut.mret_commit || dut.sync_trap_event || dut.irq_take) begin
                k=dut.irq_take?2:(dut.sync_trap_event?1:(dut.mret_commit?3:0));
                if(index>=events || k!=kind[index]) fail("event kind/order");
                if(k==2) begin
                    if(dut.arch_next_pc!==gpc[index] || {1'b1,26'b0,dut.irq_cause}!==gcause[index] || !dut.pipeline_empty)
                        fail("imprecise IRQ");
                    irqs=irqs+1;csr_pc=gpc[index];csr_cause=gcause[index];csr_tval=gtval[index];csr_check=1;
                end else begin
                    if(dut.mem_wb_pc!==gpc[index] || dut.mem_wb_inst!==ginst[index]) fail("retirement PC/instruction");
                    if(k==1) begin
                        if({27'b0,dut.wb_trap_cause}!==gcause[index] || dut.wb_trap_tval!==gtval[index] || dut.rf_we)
                            fail("trap cause/tval/write");
                        traps=traps+1;csr_pc=gpc[index];csr_cause=gcause[index];csr_tval=gtval[index];csr_check=1;
                    end else if(dut.rf_we!==wren[index][0] ||
                        (wren[index] && (dut.mem_wb_rd!==rd[index][4:0] || dut.rf_wdata!==gvalue[index])))
                        fail("register write/result");
                end
                $fdisplay(trace_fd,"EV %s %0d %08h %08h %0d %0d %08h %08h %08h",name,k,
                    (k==2)?dut.arch_next_pc:dut.mem_wb_pc,(k==2)?32'b0:dut.mem_wb_inst,dut.rf_we,
                    dut.mem_wb_rd,dut.rf_wdata,(k==1)?dut.wb_trap_cause:((k==2)?{1'b1,26'b0,dut.irq_cause}:0),(k==1)?dut.wb_trap_tval:0);
                $fflush(trace_fd);index=index+1;if(index==events) finish_pending=1;
            end
        end
    end
    always @(negedge clk) if(resetn && checking) begin
        if(check_if) begin
            if(dut.pc!==expect_pc || dut.inst_buffer_valid) fail("redirect PC increment/buffer clear");
            if(expect_new_pending && (!dut.inst_pending || dut.inst_pending_drop || dut.inst_pending_pc!==expect_pending_pc))
                fail("target request owner PC/drop");
            check_if=0;
        end
        if(csr_check) begin
            if(dut.u_csr_file.mepc!==csr_pc || dut.u_csr_file.mcause!==csr_cause || dut.u_csr_file.mtval!==csr_tval)
                fail("precise trap/IRQ CSR state");
            csr_check=0;
        end
    end
    initial begin : suite
        if(!$value$plusargs("SPECS=%s",spec_path) || !$value$plusargs("CASES=%d",expected_cases) ||
           !$value$plusargs("EVENT_LOG=%s",event_path)) fail("missing input");
        trace_fd=$fopen(event_path,"w");spec_fd=$fopen(spec_path,"r");if(!trace_fd || !spec_fd) fail("input/output open");
        for(c=0;c<expected_cases;c=c+1) begin
            @(negedge clk);resetn=0;checking=0;
            n=$fscanf(spec_fd,"%s %d %d %d %h %h %h %h %s %s\n",name,profile,events,reset_case,if_fault,data_fault,irq_load,memory_target,rom_path,oracle_path);
            if(n!=10) fail("case spec format");
            for(i=0;i<4096;i=i+1) begin rom[i]=32'h13;ram[i]=0;end
            ram[DATA[13:2]]=9;ram[(DATA+4)>>2 & 4095]=17;ram[(DATA+8)>>2 & 4095]=memory_target;
            $readmemh(rom_path,rom);fd=$fopen(oracle_path,"r");if(!fd) fail("oracle open");
            for(i=0;i<events;i=i+1)
                if($fscanf(fd,"%h %h %h %h %h %h %h %h\n",kind[i],gpc[i],ginst[i],wren[i],rd[i],gvalue[i],gcause[i],gtval[i])!=8)
                    fail("oracle format/count");
            $fclose(fd);repeat(4) @(negedge clk);
            if(reset_case) begin
                resetn=1;wait(dut.inst_pending_drop);@(negedge clk);resetn=0;
                repeat(3) @(negedge clk);resets=resets+1;
            end
            checking=1;resetn=1;wait(finish_pending);@(negedge clk);
            if(!status_seen || dpending || dr) fail("final status/transaction");
            total_events=total_events+index;case_count=case_count+1;
            $display("CHECK: %s PASS events=%0d cycles=%0d",name,index,cycle);
            resetn=0;checking=0;
        end
        if(ENABLE && (case_count!=9 || total_events!=455 || fast<=0 || response_fast<=0 || empty_fast<=0 || late_wait<=0 ||
            ready_wait<=0 || buffer_flush<=0 || discarded_errors<=0 || load_stalls<=0 || traps!=3 || irqs!=1 || resets!=1)) fail("coverage totals");
        if(!ENABLE && (case_count!=1 || fast!=0)) fail("disabled control totals");
        $display("RESULT: PASS branch_turnover enable=%0d cases=%0d events=%0d FAST=%0d EMPTY=%0d RSP=%0d LATE=%0d READY=%0d BUFFER=%0d DROP_ERR=%0d LOAD=%0d TRAP=%0d IRQ=%0d RESET=%0d",
            ENABLE,case_count,total_events,fast,empty_fast,response_fast,late_wait,ready_wait,buffer_flush,discarded_errors,load_stalls,traps,irqs,resets);
        $fclose(spec_fd);$fclose(trace_fd);$finish;
    end
    initial begin #20000000;fail("watchdog");end
endmodule
