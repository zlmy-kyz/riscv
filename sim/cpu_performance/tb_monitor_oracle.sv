`timescale 1ns/1ps
module tb_monitor_oracle;
    reg clk=0,resetn=0;
    reg [63:0] e=0, events[0:63];
    integer n,i,carry;
    string path;
    always #5 clk=~clk;
    perf_monitor monitor(.clk(clk),.resetn(resetn),.start_window(e[0]),.stop_window(e[1]),
        .window_id(e[32]?32'd2:32'd1),.retire_pc(32'h40000000),.branch_target(32'h40000080),
        .normal_retire(e[2]),.mret_commit(e[3]),.control_redirect(e[4]),.control_hold(e[5]),
        .mem_stall(e[6]),.load_use(e[7]),.branch_redirect(e[8]),.fetch_starved(e[9]),
        .target_delivered(e[10]),.i_req(e[11]),.i_ready(e[12]),.i_rsp(e[13]),.i_drop(e[14]),
        .d_req(e[15]),.d_ready(e[16]),.d_rsp(e[17]),.bridge_i_fire(e[18]),.bridge_d_fire(e[19]),
        .bridge_contention(e[20]),.ar_fire(e[21]),.aw_fire(e[22]),.r_beat(e[23]),.w_beat(e[24]),
        .bridge_state(e[27:25]));
    initial begin
        if(!$value$plusargs("EVENTS=%s",path) || !$value$plusargs("EVENT_COUNT=%d",n)) $fatal(1,"missing oracle events");
        $readmemh(path,events);
        repeat(2) @(negedge clk); resetn=1;
        for(i=0;i<n;i=i+1) begin
            e=events[i];
            @(posedge clk); #1;
            // Seed only the simulation monitor to exercise 32-bit carry.
            if(e[0] && e[32]) begin
                monitor.count[0]=64'hffffffff;
                monitor.count[8]=64'hffffffff;
                monitor.count[28]=64'hffffffff;
            end
            @(negedge clk);
        end
        $display("RESULT: PASS monitor_oracle stimulus complete"); $finish;
    end
endmodule
