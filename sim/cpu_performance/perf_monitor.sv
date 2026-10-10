`timescale 1ns/1ps
// Simulation-only observer. Sample pre-NBA signals at the CPU clock edge.
module perf_monitor (
    input wire clk, resetn, start_window, stop_window,
    input wire [31:0] window_id, retire_pc, branch_target,
    input wire normal_retire, mret_commit, control_redirect, control_hold,
    input wire mem_stall, load_use, branch_redirect, fetch_starved,
    input wire target_delivered,
    input wire i_req, i_ready, i_rsp, i_drop, d_req, d_ready, d_rsp,
    input wire bridge_i_fire, bridge_d_fire, bridge_contention,
    input wire ar_fire, aw_fire, r_beat, w_beat,
    input wire [2:0] bridge_state
);
    reg running = 0;
    reg [31:0] active_id = 0, recovery_target = 0;
    reg recovering = 0;
    reg [63:0] tick = 0, count [0:33], pc_count [0:16383];
    reg [63:0] latency [0:1][0:4096];
    reg [63:0] accepted_at [0:1];
    reg pending [0:1];
    integer pending_start [0:1];
    integer stats_file, hist_file, pc_file, k, c, slot;
    integer classification, delay_cycles;
    string out_dir;
    wire i_fire = i_req && i_ready;
    wire d_fire = d_req && d_ready;
    wire sample = (running || start_window) && !stop_window;
    initial begin
        if (!$value$plusargs("OUT=%s", out_dir)) out_dir = ".";
        stats_file = $fopen({out_dir, "/metrics.csv"}, "w");
        hist_file = $fopen({out_dir, "/latency.csv"}, "w");
        pc_file = $fopen({out_dir, "/retire_pc.csv"}, "w");
        if (!stats_file || !hist_file || !pc_file) $fatal(1, "monitor output open failed");
        $fdisplay(stats_file, "window,metric,value");
        $fdisplay(hist_file, "window,channel,latency_cycles,count");
        $fdisplay(pc_file, "window,pc,count");
        for (c=0; c<2; c=c+1) begin pending[c]=0; accepted_at[c]=0; end
    end
    function automatic string metric_name(input integer index);
        case(index)
            0: metric_name="cycles"; 1: metric_name="instret";
            2: metric_name="if_stall_cycles"; 3: metric_name="mem_stall_cycles";
            4: metric_name="branch_flush_cycles"; 5: metric_name="control_redirect_cycles";
            6: metric_name="control_hold_cycles"; 7: metric_name="load_use_cycles";
            8: metric_name="other_cycles"; 9: metric_name="ddr_transactions";
            10: metric_name="branch_redirects"; 11: metric_name="if_requests";
            12: metric_name="if_responses"; 13: metric_name="data_requests";
            14: metric_name="data_responses"; 15: metric_name="ddr_ar_commands";
            16: metric_name="ddr_aw_commands"; 17: metric_name="ddr_r_beats";
            18: metric_name="ddr_w_beats"; 19: metric_name="if_req_backpressure_cycles";
            20: metric_name="if_pending_cycles"; 21: metric_name="data_req_backpressure_cycles";
            22: metric_name="data_pending_cycles"; 23: metric_name="bridge_if_requests";
            24: metric_name="bridge_data_requests"; 25: metric_name="bridge_rsp_cycles";
            26: metric_name="bridge_contention_cycles"; 27: metric_name="if_dropped_responses";
            28: metric_name="bridge_idle_cycles"; 29: metric_name="bridge_raddr_cycles";
            30: metric_name="bridge_rdata_cycles"; 31: metric_name="bridge_waddr_cycles";
            32: metric_name="bridge_wdata_cycles"; 33: metric_name="bridge_rsp_state_cycles";
            default: metric_name="invalid";
        endcase
    endfunction
    always @(posedge clk) begin
        if (!resetn) begin
            tick=0; running=0; recovering=0;
            pending[0]=0; pending[1]=0;
        end else begin
            if (start_window) begin
                if (running || stop_window) $fatal(1,"overlapping monitor windows");
                active_id=window_id;
                for(k=0;k<34;k=k+1) count[k]=0;
                for(k=0;k<16384;k=k+1) pc_count[k]=0;
                for(c=0;c<2;c=c+1) begin
                    pending_start[c]=pending[c];
                    for(k=0;k<4097;k=k+1) latency[c][k]=0;
                end
                running=1;
            end
            if (stop_window) begin
                if (!running) $fatal(1,"stop without monitor window");
                if (count[0] != count[2]+count[3]+count[4]+count[5]+count[6]+count[7]+count[8])
                    $fatal(1,"exclusive stall partition does not sum to cycles");
                if ($signed(count[11]-count[12]) != $signed(integer'(pending[0])-pending_start[0]) ||
                    $signed(count[13]-count[14]) != $signed(integer'(pending[1])-pending_start[1]))
                    $fatal(1,"request/response window conservation failed");
                for(k=0;k<34;k=k+1) $fdisplay(stats_file,"%0d,%s,%0d",active_id,metric_name(k),count[k]);
                for(c=0;c<2;c=c+1) begin
                    $fdisplay(stats_file,"%0d,pending_%0d_start,%0d",active_id,c,pending_start[c]);
                    $fdisplay(stats_file,"%0d,pending_%0d_end,%0d",active_id,c,pending[c]);
                    for(k=0;k<4097;k=k+1) if(latency[c][k])
                        $fdisplay(hist_file,"%0d,%0d,%0d,%0d",active_id,c,k,latency[c][k]);
                end
                for(k=0;k<16384;k=k+1) if(pc_count[k])
                    $fdisplay(pc_file,"%0d,%08h,%0d",active_id,32'h40000000+k*4,pc_count[k]);
                $fflush(stats_file); $fflush(hist_file); $fflush(pc_file);
                $display("PERF window=%0d cycles=%0d instret=%0d IF=%0d MEM=%0d branch=%0d DDR=%0d",
                    active_id,count[0],count[1],count[2],count[3],count[4],count[9]);
                running=0;
            end
            if (sample) begin
                count[0]=count[0]+1;
                count[1]=count[1]+(normal_retire || mret_commit);
                if (normal_retire || mret_commit) begin
                    if(retire_pc>=32'h40000000 && retire_pc<32'h40010000)
                        pc_count[(retire_pc-32'h40000000)>>2]=pc_count[(retire_pc-32'h40000000)>>2]+1;
                end
                // Priority is part of the metric contract. Raw waits may overlap.
                if(control_redirect) classification=5;
                else if(mem_stall) classification=3;
                else if(control_hold) classification=6;
                else if(load_use) classification=7;
                else if(branch_redirect || (recovering && !target_delivered)) classification=4;
                else if(fetch_starved) classification=2;
                else classification=8;
                count[classification]=count[classification]+1;
                count[9]=count[9]+ar_fire+aw_fire;
                count[10]=count[10]+branch_redirect;
                count[11]=count[11]+i_fire; count[12]=count[12]+i_rsp;
                count[13]=count[13]+d_fire; count[14]=count[14]+d_rsp;
                count[15]=count[15]+ar_fire; count[16]=count[16]+aw_fire;
                count[17]=count[17]+r_beat; count[18]=count[18]+w_beat;
                count[19]=count[19]+(i_req && !i_ready); count[20]=count[20]+pending[0];
                count[21]=count[21]+(d_req && !d_ready); count[22]=count[22]+pending[1];
                count[23]=count[23]+bridge_i_fire; count[24]=count[24]+bridge_d_fire;
                count[25]=count[25]+(bridge_state==5); count[26]=count[26]+bridge_contention;
                count[27]=count[27]+(i_rsp && i_drop);
                if(bridge_state>5) $fatal(1,"invalid bridge state");
                count[28+bridge_state]=count[28+bridge_state]+1;
            end
            // Finish old response before accepting a replacement at the same edge.
            for(c=0;c<2;c=c+1) begin
                if((c==0 && i_rsp) || (c==1 && d_rsp)) begin
                    if(!pending[c]) $fatal(1,"response without pending request channel=%0d",c);
                    delay_cycles=tick-accepted_at[c];
                    slot=(delay_cycles>4095)?4096:delay_cycles;
                    if(sample) latency[c][slot]=latency[c][slot]+1;
                    pending[c]=0;
                end
                if((c==0 && i_fire) || (c==1 && d_fire)) begin
                    if(pending[c]) $fatal(1,"two outstanding requests channel=%0d",c);
                    pending[c]=1; accepted_at[c]=tick;
                end
            end
            if(control_redirect) recovering=0;
            else if(branch_redirect) begin recovering=1; recovery_target=branch_target; end
            else if(recovering && target_delivered) recovering=0;
            tick=tick+1;
        end
    end
endmodule
