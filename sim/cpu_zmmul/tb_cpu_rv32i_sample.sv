`timescale 1ns/1ps
module tb_cpu_rv32i_sample;
    localparam [31:0] BASE=32'h80000000, DATA=32'h80003000;
    reg clk=0,resetn=0,irq=0;
    wire iv,dv,dw;
    wire [31:0] ia,da,wd;
    wire [3:0] ws;
    wire [1:0] ds;
    reg ir=0,dr=0,de=0;
    reg [31:0] idata=0,ddata=0;
    reg ipending=0,dpending=0;
    reg [31:0] saved_i,saved_d,saved_w;
    reg [3:0] saved_s;
    reg saved_write,saved_error;
    integer itimer=0,dtimer=0,cycle=0;
    wire fast_if,iready,dready;
    reg [31:0] rom[0:4095],ram[0:4095];
    integer kind[0:14999],wren[0:14999],rd[0:14999];
    reg [31:0] gpc[0:14999],ginst[0:14999],value[0:14999],cause[0:14999],tval[0:14999];
    integer index=0,nevents=0,muls=0,starts=0,expected_muls=0;
    integer pure_wait=0,held_done=0,cancelled=0,traps=0,irqs=0;
    integer case_id=6,isa=1,fd,i,j,n,reads=0;
    reg reset_done=0,irq_sent=0,fault_sent=0,status_seen=0,finish_pending=0;
    reg checking=1,holding=0;
    reg [31:0] status_addr=32'h80003ffc,irq_pc=0,last_result=0;
    reg [32:0] stable_a,stable_b;
    string rom_path,ram_path,trace_path,name;
    string trap_path,event_path;
    integer event_fd=0,trap_index=0;
    reg [31:0] trap_pc[0:4],trap_inst[0:4],trap_cause[0:4],trap_tval[0:4],trap_target[0:4];
    reg csr_check=0,await_target=0,status_committed=0;
    reg [31:0] check_pc,check_cause,check_tval,next_target,status_store_pc;
    assign fast_if=!isa;
    assign iready=resetn&&(fast_if || (!ipending&&!ir));
    assign dready=resetn&&!dpending&&!dr&&(cycle%5!=1);
    always #5 clk=~clk;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    mycpu_sync #(.RESET_PC(BASE)) dut(
        .clk(clk),.resetn(resetn),.irq_external(irq),.irq_software(1'b0),.irq_timer(1'b0),
        .memory_order_busy(1'b0),
        .inst_req_valid(iv),.inst_req_addr(ia),.inst_req_ready(iready),
        .inst_rsp_valid(ir),.inst_rsp_rdata(idata),.inst_rsp_error(1'b0),
        .data_req_valid(dv),.data_req_write(dw),.data_req_size(ds),.data_req_addr(da),
        .data_req_wdata(wd),.data_req_wstrb(ws),.data_req_ready(dready),
        .data_rsp_valid(dr),.data_rsp_rdata(ddata),.data_rsp_error(de),
        .debug_wb_pc(),.debug_wb_rf_we(),.debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(),
        .perf_events(),.perf_branch_target(),.perf_fetch_pc());

    task automatic fail(input string reason);
        $display("RESULT: FAIL rv32i_sample case=%s %s event=%0d pc=%h inst=%h cause=%0d tval=%h rf_we=%b irq_take=%b target=%h t=%0t",
                 name,reason,index,dut.mem_wb_pc,dut.mem_wb_inst,dut.wb_trap_cause,
                 dut.wb_trap_tval,dut.rf_we,dut.irq_take,dut.csr_trap_target,$time);
        if(event_fd) begin $fflush(event_fd);$fclose(event_fd);event_fd=0;end
        $fatal(1);
    endtask
    task automatic pass;
        if(trap_index!=5 || traps!=5 || muls!=0 || irqs!=0 || await_target || !status_committed)
            fail("trap/redirect/retirement totals");
        $display("CHECK: %s PASS tohost=00000001 traps=5 probes=4 muls=0 events=%0d",name,index);
        $display("RESULT: PASS rv32i_sample case=%s tohost=1 traps=5 probes=4 muls=0",name);
        $fflush(event_fd);$fclose(event_fd);event_fd=0;$finish;
    endtask
    // Independent single-outstanding instruction/data models, with accepted requests latched.
    always @(posedge clk) begin
        if(!resetn) begin
            ir<=0;dr<=0;de<=0;ipending<=0;dpending<=0;itimer<=0;dtimer<=0;cycle<=0;
            fault_sent<=0;reads<=0;status_seen<=0;
        end else begin
            cycle<=cycle+1; ir<=0;dr<=0;de<=0;
            if(iv&&iready) begin
                if(ia<BASE || ia>=BASE+32'h4000 || ia[1:0]!=0) fail("instruction address");
                if(fast_if) begin idata<=rom[ia[13:2]];ir<=1;end
                else begin saved_i<=ia;ipending<=1;itimer<=cycle%3;end
            end
            if(ipending) begin
                if(itimer==0) begin idata<=rom[saved_i[13:2]];ir<=1;ipending<=0;end
                else itimer<=itimer-1;
            end
            if(dv&&dready) begin
                if(da<BASE || da>=BASE+32'h4000) fail("data address");
                saved_d<=da;saved_write<=dw;saved_w<=wd;saved_s<=ws;
                saved_error<=(case_id==3 && da==DATA && !dw && !fault_sent);
                if(case_id==3 && da==DATA && !dw && !fault_sent) fault_sent<=1;
                dpending<=1;
                dtimer<=(!dw && (case_id==1 || case_id==3))?35:cycle%6;
                if(!dw) reads<=reads+1;
                if(dw) begin
                    for(j=0;j<4;j=j+1) if(ws[j]) ram[da[13:2]][8*j+:8]<=wd[8*j+:8];
                    if(da==status_addr) begin
                        if(ws!=4'b1111 || wd!=1) fail($sformatf("tohost=%h",wd));
                        status_seen<=1;status_store_pc<=dut.id_ex_pc;
                    end
                end
            end
            if(dpending) begin
                if(dtimer==0) begin
                    dr<=1;de<=saved_error;ddata<=ram[saved_d[13:2]];dpending<=0;
                end else dtimer<=dtimer-1;
            end
        end
    end


    // Only five exact, ordered traps are allowed: four bootstrap probes and passing ECALL.
    // Read-only architectural trace never feeds CPU control or creates expected values.
    always @(posedge clk) begin : observe_isa
        integer event_kind;
        if(!resetn) begin
            index=0;trap_index=0;traps=0;irqs=0;muls=0;
            csr_check=0;await_target=0;status_committed=0;finish_pending=0;
        end else begin
            if(dut.normal_retire || dut.mret_commit || dut.sync_trap_event || dut.irq_take) begin
                event_kind=dut.irq_take?2:(dut.sync_trap_event?1:(dut.mret_commit?3:0));
                $fdisplay(event_fd,"EV %0d %08h %08h %b %0d %08h %0d %08h %08h %0t",
                          event_kind,dut.mem_wb_pc,dut.mem_wb_inst,dut.rf_we,dut.mem_wb_rd,
                          dut.rf_wdata,dut.wb_trap_cause,dut.wb_trap_tval,dut.csr_trap_target,$time);
                $fflush(event_fd);
                index=index+1;
                if(dut.irq_take) begin irqs=irqs+1;fail("unexpected IRQ");end
                if(await_target) begin
                    if(!(dut.normal_retire || dut.mret_commit) || dut.mem_wb_pc!==next_target)
                        fail("first committed instruction after trap is not expected target");
                    await_target=0;
                end
                if(dut.sync_trap_event) begin
                    if(trap_index>=5) fail("extra trap");
                    if(dut.mem_wb_pc!==trap_pc[trap_index] || dut.mem_wb_inst!==trap_inst[trap_index] ||
                       {27'b0,dut.wb_trap_cause}!==trap_cause[trap_index] ||
                       dut.wb_trap_tval!==trap_tval[trap_index] || dut.rf_we!==1'b0 ||
                       dut.csr_trap_target!==trap_target[trap_index])
                        fail($sformatf("trap #%0d mismatch expected_pc=%h expected_inst=%h expected_cause=%0d expected_tval=%h expected_target=%h",
                             trap_index,trap_pc[trap_index],trap_inst[trap_index],trap_cause[trap_index],trap_tval[trap_index],trap_target[trap_index]));
                    $display("ISA_TRAP: %s index=%0d pc=%h inst=%h cause=%0d tval=%h target=%h rf_we=%b",
                             name,trap_index,dut.mem_wb_pc,dut.mem_wb_inst,dut.wb_trap_cause,dut.wb_trap_tval,dut.csr_trap_target,dut.rf_we);
                    check_pc=trap_pc[trap_index];check_cause=trap_cause[trap_index];check_tval=trap_tval[trap_index];
                    next_target=trap_target[trap_index];csr_check=1;await_target=1;
                    trap_index=trap_index+1;traps=traps+1;
                end
                if(dut.normal_retire && dut.mem_wb_inst[6:0]==7'h33 && dut.mem_wb_inst[31:25]==7'h01) begin
                    muls=muls+1;fail("M instruction in frozen RV32I sample");
                end
                if(dut.normal_retire && status_seen && dut.mem_wb_pc==status_store_pc && dut.mem_wb_inst[6:0]==7'h23)
                    status_committed=1;
            end
            if(status_seen && status_committed && !dpending && !dr) finish_pending=1;
        end
    end
    always @(negedge clk) begin
        if(resetn) begin
            if(csr_check) begin
                if(dut.u_csr_file.mepc!==check_pc || dut.u_csr_file.mcause!==check_cause || dut.u_csr_file.mtval!==check_tval)
                    fail("trap CSR state after commit");
                csr_check=0;
            end
            if(finish_pending) pass();
        end
    end
    initial begin
        if(!$value$plusargs("NAME=%s",name)) fail("no name");
        if(!$value$plusargs("ROM=%s",rom_path)) fail("no ROM");
        if(!$value$plusargs("STATUS=%h",status_addr)) fail("no status address");
        if(!$value$plusargs("TRAPS=%s",trap_path)) fail("no trap oracle");
        if(!$value$plusargs("EVENT_LOG=%s",event_path)) fail("no trace destination");
        event_fd=$fopen(event_path,"w");if(!event_fd) fail("trace open");
        fd=$fopen(trap_path,"r");if(!fd) fail("trap oracle open");
        for(i=0;i<5;i=i+1)
            if($fscanf(fd,"%h %h %h %h %h\n",trap_pc[i],trap_inst[i],trap_cause[i],trap_tval[i],trap_target[i])!=5)
                fail("trap oracle format/count");
        $fclose(fd);
        for(i=0;i<4096;i=i+1) begin rom[i]=32'h13;ram[i]=0;end
        $readmemh(rom_path,rom);
        if($value$plusargs("RAM=%s",ram_path)) $readmemh(ram_path,ram);
        repeat(5) @(negedge clk);resetn=1;
    end
    initial begin #20000000;fail("watchdog");end
endmodule
