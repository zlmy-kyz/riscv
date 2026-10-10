`timescale 1ns/1ps
module tb_counter;
    reg clk=0; always #5 clk=~clk;
    reg resetn=0,req_valid=0,req_write=0;
    reg [1:0] req_size=2;
    reg [31:0] req_addr=0,req_wdata=0;
    reg [3:0] req_wstrb=15;
    wire req_ready,rsp_valid,rsp_error; wire [31:0] rsp_rdata; wire [1:0] status;
    reg [7:0] events=0; reg [31:0] retire_pc=32'h40000000,branch_target=32'h40000200,fetch_pc=0;
    reg ar=0,aw=0;
    simple_mmio #(.PERF_ENABLE(1),.PERF_AUTO_ARM(0)) dut(
        .clk(clk),.resetn(resetn),.req_valid(req_valid),.req_write(req_write),.req_size(req_size),
        .req_addr(req_addr),.req_wdata(req_wdata),.req_wstrb(req_wstrb),.req_ready(req_ready),
        .rsp_valid(rsp_valid),.rsp_rdata(rsp_rdata),.rsp_error(rsp_error),.test_status(status),
        .perf_events(events),.perf_retire_pc(retire_pc),.perf_branch_target(branch_target),
        .perf_fetch_pc(fetch_pc),.perf_ar_fire(ar),.perf_aw_fire(aw));
    wire delivered=events[7] && fetch_pc==monitor.recovery_target;
    perf_monitor monitor(.clk(clk),.resetn(resetn),.start_window(dut.g_perf.u_perf.start_event),
        .stop_window(dut.g_perf.u_perf.stop_event),.window_id(32'd1),.retire_pc(retire_pc),.branch_target(branch_target),
        .normal_retire(events[0]),.mret_commit(1'b0),.control_redirect(events[1]),.control_hold(events[2]),
        .mem_stall(events[3]),.load_use(events[4]),.branch_redirect(events[5]),.fetch_starved(events[6]),
        .target_delivered(delivered),.i_req(1'b0),.i_ready(1'b0),.i_rsp(1'b0),.i_drop(1'b0),
        .d_req(1'b0),.d_ready(1'b0),.d_rsp(1'b0),.bridge_i_fire(1'b0),.bridge_d_fire(1'b0),
        .bridge_contention(1'b0),.ar_fire(ar),.aw_fire(aw),.r_beat(1'b0),.w_beat(1'b0),.bridge_state(3'd0));
    integer index,transactions=0,windows=0;
    reg [31:0] value;
    task check_counts;
        begin
            for(index=0;index<13;index=index+1)
                if(dut.g_perf.u_perf.count[index]!==monitor.count[index<11?index:index+4])
                    $fatal(1,"counter mismatch index=%d hardware=%d observer=%d",index,
                        dut.g_perf.u_perf.count[index],monitor.count[index<11?index:index+4]);
        end
    endtask
    task bus(input bit wr,input [31:0] address,input [31:0] data,input bit bad);
        begin
            @(negedge clk); req_valid=1;req_write=wr;req_addr=address;req_wdata=data;
            @(posedge clk); if(!req_ready) $fatal(1,"test master busy");
            #1; if(!rsp_valid || rsp_error!==bad) $fatal(1,"MMIO access error addr=%h wanted=%b got=%b",address,bad,rsp_error);
            value=rsp_rdata;transactions=transactions+1;
            @(negedge clk);req_valid=0;
            @(posedge clk);#1;if(rsp_valid) $fatal(1,"response not drained");
        end
    endtask
    task step(input [7:0] e,input bit a,input bit w,input [31:0] pc);
        begin @(negedge clk);events=e;ar=a;aw=w;fetch_pc=pc; @(posedge clk);#1;end
    endtask
    always @(posedge clk) if(resetn && dut.g_perf.u_perf.stop_event) windows=windows+1;
    initial begin
        repeat(3) @(negedge clk);resetn=1;
        bus(0,32'h100,0,0);if(value!=32'h50524601) $fatal(1,"ID");
        bus(0,32'h140,0,1); // No live/torn counter reads.
        bus(1,32'h108,4,1); // Stop without start.
        bus(1,32'h108,2,0);
        bus(1,32'h10c,0,0);bus(1,32'h110,0,0);bus(1,32'h108,1,0);
        bus(1,32'h10c,0,1);bus(1,32'h108,3,1); // Armed configuration is immutable.
        bus(0,8,0,0); // S included.
        step(8'b01111111,1,1,0); // Intersection chooses control redirect; DDR adds TWO.
        step(8'b01111101,0,0,0); // MEM wins.
        step(8'b01110101,1,0,0); // control hold wins.
        step(8'b01110001,0,1,0); // load-use wins.
        step(8'b01100001,0,0,0); // branch redirect begins recovery.
        step(8'b11000001,0,0,32'h40000204); // wrong PC is not delivery.
        step(8'b11000001,0,0,32'h40000200); // target delivered, classify IF.
        step(8'b00000001,0,0,0); // other.
        bus(1,32'h108,1,1); // No rearm while running.
        bus(0,32'h140,0,1);
        step(0,0,0,0);
        bus(0,8,0,0);check_counts(); // T excluded.
        if(dut.g_perf.u_perf.count[9]!=4 || dut.g_perf.u_perf.count[11]!=2 || dut.g_perf.u_perf.count[12]!=2)
            $fatal(1,"DDR command width");
        if(dut.g_perf.u_perf.count[5]!=1 || dut.g_perf.u_perf.count[3]!=1 ||
           dut.g_perf.u_perf.count[6]!=1 || dut.g_perf.u_perf.count[7]!=1 || dut.g_perf.u_perf.count[4]!=2)
            $fatal(1,"exclusive priority oracle");
        bus(0,32'h140,0,0);
        if(value!=dut.g_perf.u_perf.stop_tick-dut.g_perf.u_perf.start_tick) $fatal(1,"CYCLE window delta");
        for(index=0;index<26;index=index+1) begin
            bus(0,32'h140+index*4,0,0);
            if(value !== (index[0]?dut.g_perf.u_perf.count[index>>1][63:32]:dut.g_perf.u_perf.count[index>>1][31:0]))
                $fatal(1,"64-bit software read map");
        end
        bus(1,32'h140,0,1);bus(0,32'h1a8,0,1);bus(1,32'h100,0,1);
        req_wstrb=1;bus(1,32'h108,2,1);req_wstrb=15;
        req_size=0;bus(0,32'h100,0,1);req_size=2;
        bus(1,32'h108,3,0); // New manual window clears old bank and includes S.
        @(negedge clk);
        dut.g_perf.u_perf.count[0]=64'hffffffff;
        dut.g_perf.u_perf.count[8]=64'hffffffff;
        // Observer is one sample ahead of the registered hardware bank.
        monitor.count[0]=64'h100000000;monitor.count[8]=64'h100000000;
        @(posedge clk);#1;
        if(dut.g_perf.u_perf.count[0]!=64'h100000000) $fatal(1,"64-bit carry");
        // Seeded carry also adjusts the independent observer; compare at T,
        // after the one-cycle observation pipeline has applied its final sample.
        bus(1,32'h108,4,0);check_counts();bus(0,32'h144,0,0);if(value!=1) $fatal(1,"high word");
        // PC-qualified mode ignores unrelated timers and unretired marker PCs.
        bus(1,32'h108,2,0);bus(1,32'h10c,32'h400007d0,0);bus(1,32'h110,32'h400007f4,0);bus(1,32'h108,1,0);
        retire_pc=32'h400007d0;bus(0,8,0,0);if(dut.g_perf.u_perf.state!=1) $fatal(1,"unretired marker");
        @(negedge clk);events=1;@(posedge clk);#1;@(negedge clk);events=0;
        bus(0,8,0,0);if(dut.g_perf.u_perf.state!=2) $fatal(1,"qualified start");
        bus(0,8,0,0);if(dut.g_perf.u_perf.state!=2) $fatal(1,"unqualified stop");
        retire_pc=32'h400007f4;@(negedge clk);events=1;@(posedge clk);#1;@(negedge clk);events=0;
        bus(0,8,0,0);check_counts();if(dut.g_perf.u_perf.state!=3) $fatal(1,"qualified stop");
        // Cancel is an abort, not a successful snapshot.
        bus(1,32'h108,3,0);bus(1,32'h108,2,0);
        if(dut.g_perf.u_perf.state!=0 || dut.g_perf.u_perf.count[0]!=0) $fatal(1,"cancel");
        bus(0,32'h140,0,1);
        bus(1,0,32'h12345678,0);bus(0,0,0,0);if(value!=32'h12345678) $fatal(1,"legacy scratch");
        bus(1,16,1,0);bus(1,16,2,0);bus(0,16,0,0);if(value!=2) $fatal(1,"legacy status");
        if(windows!=3) $fatal(1,"missing windows");
        $display("RESULT: PASS PERF2B counter/MMIO oracle transactions=%d windows=%d",transactions,windows);$finish;
    end
    initial begin #100000; $fatal(1,"counter test timeout");end
endmodule
