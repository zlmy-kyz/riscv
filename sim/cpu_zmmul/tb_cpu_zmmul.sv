`timescale 1ns/1ps
module tb_cpu_zmmul;
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
    integer case_id=0,isa=0,fd,i,j,n,reads=0;
    reg reset_done=0,irq_sent=0,fault_sent=0,status_seen=0,finish_pending=0;
    reg checking=1,holding=0;
    reg [31:0] status_addr=32'h80003ffc,irq_pc=0,last_result=0;
    reg [32:0] stable_a,stable_b;
    string rom_path,ram_path,trace_path,name;
    assign fast_if=!isa;
    assign iready=resetn&&(fast_if || (!ipending&&!ir));
    assign dready=resetn&&!dpending&&!dr&&(cycle%5!=1);
    always #5 clk=~clk;
    GTP_GRS GRS_INST(.GRS_N(1'b1));
    mycpu_sync #(.RESET_PC(BASE)) dut(
        .clk(clk),.resetn(resetn),.irq_external(irq),.irq_software(1'b0),.irq_timer(1'b0),
        .inst_req_valid(iv),.inst_req_addr(ia),.inst_req_ready(iready),
        .inst_rsp_valid(ir),.inst_rsp_rdata(idata),.inst_rsp_error(1'b0),
        .data_req_valid(dv),.data_req_write(dw),.data_req_size(ds),.data_req_addr(da),
        .data_req_wdata(wd),.data_req_wstrb(ws),.data_req_ready(dready),
        .data_rsp_valid(dr),.data_rsp_rdata(ddata),.data_rsp_error(de),
        .debug_wb_pc(),.debug_wb_rf_we(),.debug_wb_rf_wnum(),.debug_wb_rf_wdata(),.debug_inst(),
        .perf_events(),.perf_branch_target(),.perf_fetch_pc());

    task automatic fail(input string reason);
        $display("RESULT: FAIL cpu_zmmul case=%s %s event=%0d pc=%h t=%0t",name,reason,index,dut.mem_wb_pc,$time);
        $fatal(1);
    endtask
    task automatic pass;
        if(!isa) begin
            if(index!=nevents || muls!=expected_muls) fail("retirement totals");
            // In case 1 all multiply wait intentionally overlaps the older load wait.
            if(case_id!=1 && pure_wait==0) fail("no pure multiply wait observed");
            if(case_id==1 && held_done<2) fail("no completed result held behind MEM");
            if(case_id==2 && !reset_done) fail("mid-multiply reset not exercised");
            if(case_id==3 && (traps!=1 || starts!=muls+1 || cancelled<1)) fail("older fault cancellation not exercised");
            if(case_id==4 && (irqs!=1 || !irq_sent)) fail("IRQ drain not exercised");
            if(case_id==5 && traps!=5) fail("illegal instruction traps");
        end else if(muls!=0 || starts!=0 || traps!=1) fail("ISA old path/ECALL totals");
        $display("CHECK: %s PASS events=%0d muls=%0d launches=%0d pure_wait=%0d held_done=%0d cancelled=%0d traps=%0d irqs=%0d",name,index,muls,starts,pure_wait,held_done,cancelled,traps,irqs);
        $display("RESULT: PASS cpu_zmmul case=%s events=%0d muls=%0d",name,index,muls); $finish;
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
                        status_seen<=1;
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

    // Compare every committed instruction, synchronous exception, MRET and IRQ against Python.
    always @(posedge clk) begin : observe
        integer actual_kind;
        reg is_m;
        if(!resetn) begin
            index=0;muls=0;starts=0;pure_wait=0;held_done=0;cancelled=0;traps=0;irqs=0;finish_pending=0;holding=0;
        end else if(checking) begin
            if(dut.mul_start) begin starts=starts+1;stable_a=dut.mul_operand_a;stable_b=dut.mul_operand_b;end
            if(dut.mul_busy && !dut.kill_id_ex && !dut.older_fault_for_ex) begin
                if(dut.mul_operand_a!==stable_a || dut.mul_operand_b!==stable_b) fail("unstable operands while busy");
            end
            if((dut.mul_busy || dut.mul_done) && dut.older_fault_for_ex) cancelled=cancelled+1;
            if(dut.id_ex_valid && dut.id_ex_mul && !dut.mul_done && !dut.perf_memory_stall) begin
                pure_wait=pure_wait+1;
                if(dut.perf_events[3]!==0) fail("multiply incorrectly counted as MEM wait");
                if(dut.fwd_ex_en!==0 || dut.id_ex_advance!==0) fail("premature multiply forward/advance");
            end
            if(dut.mul_done && !dut.ex_mem_ready) begin
                if(holding && dut.mul_result!==last_result) fail("completed result changed under MEM hold");
                if(dut.mul_ce!==0) fail("CE still enabled after completion");
                last_result=dut.mul_result;held_done=held_done+1;holding=1;
            end else holding=0;
            if(dut.normal_retire || dut.mret_commit || dut.sync_trap_event || dut.irq_take) begin
                actual_kind=dut.irq_take?2:(dut.sync_trap_event?1:(dut.mret_commit?3:0));
                is_m=(dut.mem_wb_inst[6:0]==7'h33 && dut.mem_wb_inst[31:25]==7'h01 && !dut.mem_wb_inst[14]);
                if(actual_kind==0 && is_m) muls=muls+1;
                if(actual_kind==1) traps=traps+1;
                if(actual_kind==2) begin irqs=irqs+1;irq<=0;end
                if(!isa) begin
                    if(index>=nevents) fail("extra retirement event");
                    if(actual_kind!=kind[index]) fail("event kind/order");
                    if(actual_kind==2) begin
                        if(dut.arch_next_pc!==gpc[index] || {1'b1,26'b0,dut.irq_cause}!==cause[index] || !dut.pipeline_empty) fail("IRQ not precise");
                    end else begin
                        if(dut.mem_wb_pc!==gpc[index] || dut.mem_wb_inst!==ginst[index]) fail("instruction PC/order");
                        if(actual_kind==1) begin
                            if({27'b0,dut.wb_trap_cause}!==cause[index] || dut.wb_trap_tval!==tval[index] || dut.rf_we) fail("trap cause/tval/write");
                        end else begin
                            if(dut.rf_we!==wren[index][0]) fail("register write enable");
                            if(wren[index] && (dut.mem_wb_rd!==rd[index][4:0] || dut.rf_wdata!==value[index]))
                                fail($sformatf("register result got=%h expected=%h rd=%0d",dut.rf_wdata,value[index],rd[index]));
                        end
                    end
                    index=index+1;
                    if(index==nevents) finish_pending=1;
                end else begin
                    index=index+1;
                    if(actual_kind==2 || (actual_kind==1 &&
                       (dut.wb_trap_cause!=5'd11 || dut.mem_wb_inst!=32'h00000073 || dut.rf_we)))
                        fail("unexpected ISA trap/IRQ");
                end
            end
            if(isa && status_seen && !dpending && !dr) finish_pending=1;
        end
    end
    always @(negedge clk) begin
        if(resetn && checking) begin
            if(case_id==4 && !irq_sent && dut.mul_busy && dut.mul_count==2 && dut.id_ex_pc==irq_pc) begin
                irq=1;irq_sent=1;
            end
            if(finish_pending) pass();
        end
    end

    initial begin
        if(!$value$plusargs("CASE=%d",case_id)) fail("no case");
        if(!$value$plusargs("NAME=%s",name)) fail("no name");
        if(!$value$plusargs("ROM=%s",rom_path)) fail("no ROM");
        n=$value$plusargs("ISA=%d",isa);
        n=$value$plusargs("STATUS=%h",status_addr);
        n=$value$plusargs("IRQ_PC=%h",irq_pc);
        n=$value$plusargs("MULS=%d",expected_muls);
        for(i=0;i<4096;i=i+1) begin rom[i]=32'h13;ram[i]=0;end
        $readmemh(rom_path,rom);
        if($value$plusargs("RAM=%s",ram_path)) $readmemh(ram_path,ram);
        if(!isa) begin
            if(!$value$plusargs("TRACE=%s",trace_path)) fail("no trace");
            if(!$value$plusargs("EVENTS=%d",nevents)) fail("no event count");
            fd=$fopen(trace_path,"r");if(!fd) fail("trace open");
            for(i=0;i<nevents;i=i+1)
                if($fscanf(fd,"%h %h %h %h %h %h %h %h\n",kind[i],gpc[i],ginst[i],wren[i],rd[i],value[i],cause[i],tval[i])!=8) fail("trace format/count");
            $fclose(fd);
        end
        repeat(5) @(negedge clk);
        if(case_id==2) begin
            // First invocation uses different operands; reset during multiplication.
            checking=0;rom[1]=32'h04500093;resetn=1;
            wait(dut.mul_busy && dut.mul_count==2);@(negedge clk);resetn=0;
            repeat(3) @(negedge clk);
            $readmemh(rom_path,rom);reset_done=1;checking=1;
        end
        resetn=1;
    end
    initial begin #20000000;fail("watchdog");end
endmodule
