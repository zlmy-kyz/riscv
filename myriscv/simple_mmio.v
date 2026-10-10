`timescale 1ns / 1ps

// 用于验证地址译码和外设访问的最小 MMIO 从机。
// 局部地址布局：
//   0x000 SCRATCH  可读写，支持字节写使能
//   0x004 ID       只读，固定为 "MMIO"
//   0x008 CYCLE    只读，自复位释放后递增
//   0x00c STATUS   只读，bit0 恒为 1
//   0x010 TEST_STATUS  0=IDLE，1=RUN，2=PASS，3=FAIL；结果锁存至复位
// 其他偏移以及对只读寄存器的写入返回总线错误。
module simple_mmio #(
    parameter integer PERF_ENABLE = 0,
    parameter integer PERF_AUTO_ARM = 0,
    parameter [31:0] PERF_START_PC = 32'h400007d0,
    parameter [31:0] PERF_STOP_PC = 32'h400007f4
) (
    input  wire        clk,
    input  wire        resetn,

    input  wire        req_valid,
    input  wire        req_write,
    input  wire [ 1:0] req_size,
    input  wire [31:0] req_addr,
    input  wire [31:0] req_wdata,
    input  wire [ 3:0] req_wstrb,
    output wire        req_ready,

    output wire        rsp_valid,
    output wire [31:0] rsp_rdata,
    output wire        rsp_error,
    output reg  [ 1:0] test_status,
    input wire [7:0] perf_events,
    input wire [31:0] perf_retire_pc, perf_branch_target, perf_fetch_pc,
    input wire perf_ar_fire, perf_aw_fire
);

    reg        pending;
    reg [31:0] response_data;
    reg        response_error;
    reg [31:0] scratch;
    reg [31:0] cycle_counter;
    wire       req_fire;

    wire [31:0] perf_rdata;
    wire perf_error;
    generate if (PERF_ENABLE != 0) begin : g_perf
        cpu_perf_counters #(.AUTO_ARM(PERF_AUTO_ARM), .DEFAULT_START_PC(PERF_START_PC),
            .DEFAULT_STOP_PC(PERF_STOP_PC)) u_perf (
            .clk(clk), .resetn(resetn), .events(perf_events), .retire_pc(perf_retire_pc),
            .branch_target(perf_branch_target), .fetch_pc(perf_fetch_pc),
            .ar_fire(perf_ar_fire), .aw_fire(perf_aw_fire), .timer_value(cycle_counter),
            .timer_read(req_fire && !req_write && req_addr[11:2]==10'd2),
            .access(req_fire), .write(req_write), .size(req_size), .addr(req_addr[11:0]),
            .wdata(req_wdata), .wstrb(req_wstrb), .rdata(perf_rdata), .error(perf_error));
    end else begin : g_no_perf
        assign perf_rdata=0;
        assign perf_error=1;
    end endgenerate

    function [31:0] merge_wstrb;
        input [31:0] old_value;
        input [31:0] new_value;
        input [ 3:0] write_strobe;
        integer i;
        begin
            merge_wstrb = old_value;
            for (i = 0; i < 4; i = i + 1)
                if (write_strobe[i])
                    merge_wstrb[i*8 +: 8] = new_value[i*8 +: 8];
        end
    endfunction

    assign req_ready = !pending;
    assign req_fire  = req_valid && req_ready;
    assign rsp_valid = pending;
    assign rsp_rdata = response_data;
    assign rsp_error = pending && response_error;

    always @(posedge clk) begin
        if (!resetn) begin
            pending        <= 1'b0;
            response_data  <= 32'b0;
            response_error <= 1'b0;
            scratch        <= 32'b0;
            cycle_counter  <= 32'b0;
            test_status    <= 2'd0;
        end else begin
            cycle_counter <= cycle_counter + 32'd1;

            if (rsp_valid)
                pending <= 1'b0;

            if (req_fire) begin
                pending        <= 1'b1;
                response_data  <= 32'b0;
                response_error <= 1'b0;

                case (req_addr[11:2])
                    10'd0: begin
                        response_data <= scratch;
                        if (req_write)
                            scratch <= merge_wstrb(scratch, req_wdata,
                                                   req_wstrb);
                    end
                    10'd1: begin
                        response_data <= 32'h4d4d_494f;
                        if (req_write)
                            response_error <= 1'b1;
                    end
                    10'd2: begin
                        response_data <= cycle_counter;
                        if (req_write)
                            response_error <= 1'b1;
                    end
                    10'd3: begin
                        response_data <= 32'h0000_0001;
                        if (req_write)
                            response_error <= 1'b1;
                    end
                    10'd4: begin
                        response_data <= {30'b0, test_status};
                        // 仅最低字节有效；PASS/FAIL 必须在 RUN 之后上报。
                        if (req_write && req_wstrb[0]) begin
                            case (req_wdata[7:0])
                                8'd1: begin
                                    if (test_status == 2'd0)
                                        test_status <= 2'd1;
                                end
                                8'd2, 8'd3: begin
                                    if (test_status == 2'd1)
                                        test_status <= req_wdata[1:0];
                                    else if (test_status == 2'd0)
                                        response_error <= 1'b1;
                                end
                                default: response_error <= 1'b1;
                            endcase
                        end
                    end
                    default: begin
                        response_data <= perf_rdata;
                        response_error <= perf_error;
                    end
                endcase
            end
        end
    end

    wire [1:0] _unused_req_size = req_size;

endmodule

// Synthesizable 64-bit counters. Included in candidate simple_mmio.v to keep
// the existing PDS source inventory and standalone MMIO compilations usable.
module cpu_perf_counters #(
    parameter integer AUTO_ARM=0,
    parameter [31:0] DEFAULT_START_PC=32'h400007d0,
    parameter [31:0] DEFAULT_STOP_PC=32'h400007f4
) (
    input wire clk, resetn,
    input wire [7:0] events,
    input wire [31:0] retire_pc, branch_target, fetch_pc, timer_value,
    input wire ar_fire, aw_fire, timer_read, access, write,
    input wire [1:0] size,
    input wire [11:0] addr,
    input wire [31:0] wdata,
    input wire [3:0] wstrb,
    output reg [31:0] rdata,
    output reg error
);
    localparam IDLE=2'd0, ARMED=2'd1, RUNNING=2'd2, DONE=2'd3;
    reg [1:0] state;
    reg [31:0] start_pc, stop_pc, start_tick, stop_tick;
    reg start_seen, stop_seen, recovering;
    reg [31:0] recovery_target;
    reg [63:0] count [0:12];
    integer k;
    reg [3:0] classification;
    wire delivered=events[7] && fetch_pc==recovery_target;
    wire command=access && write && addr==12'h108 && !error;
    wire arm=command && wdata==1;
    wire cancel=command && wdata==2;
    wire manual_start=command && wdata==3;
    wire manual_stop=command && wdata==4;
    wire start_event=manual_start || (state==ARMED && timer_read && (start_pc==0 || start_seen));
    wire stop_event=manual_stop || (state==RUNNING && timer_read && (stop_pc==0 || stop_seen));
    wire sample=(state==RUNNING || start_event) && !stop_event && !cancel;
    wire [1:0] ddr_increment={1'b0,ar_fire}+{1'b0,aw_fire};
    // One observation pipeline stage breaks CPU/MMIO -> 64-bit CE paths.
    // Counts consume edge E on E+1, so the last [S,T) sample is applied AT T.
    // DONE is visible after T, when the entire frozen bank is already complete.
    reg sample_q, start_q, clear_q, retire_q, branch_q, ar_q, aw_q;
    reg [1:0] ddr_q;
    reg [3:0] classification_q;
    always @* begin
        if(events[1]) classification=5;
        else if(events[3]) classification=3;
        else if(events[2]) classification=6;
        else if(events[4]) classification=7;
        else if(events[5] || (recovering && !delivered)) classification=4;
        else if(events[6]) classification=2;
        else classification=8;
        rdata=0; error=1;
        if(size==2 && addr[1:0]==0) begin
            case(addr)
                12'h100: begin rdata=32'h50524601; error=write; end
                12'h104: begin rdata={28'd0,stop_seen,start_seen,state}; error=write; end
                12'h108: begin
                    error=write && (wstrb!=4'hf ||
                        !((wdata==1 && state!=RUNNING) || wdata==2 ||
                          (wdata==3 && (state==IDLE || state==DONE)) ||
                          (wdata==4 && state==RUNNING)));
                end
                12'h10c,12'h110: begin
                    rdata=(addr==12'h10c)?start_pc:stop_pc;
                    error=write && (wstrb!=4'hf || wdata[1:0]!=0 ||
                                   (state!=IDLE && state!=DONE));
                end
                12'h114: begin rdata=start_tick; error=write; end
                12'h118: begin rdata=stop_tick; error=write; end
                default: if(addr>=12'h140 && addr<=12'h1a4) begin
                    // A frozen bank is its own snapshot. Never expose torn live reads.
                    error=write || state!=DONE;
                    rdata=addr[2] ? count[(addr-12'h140)>>3][63:32] : count[(addr-12'h140)>>3][31:0];
                end
            endcase
        end
    end
    always @(posedge clk) begin
        if(!resetn) begin
            state<=AUTO_ARM?ARMED:IDLE;
            start_pc<=DEFAULT_START_PC; stop_pc<=DEFAULT_STOP_PC;
            start_tick<=0; stop_tick<=0; start_seen<=0; stop_seen<=0;
            recovering<=0; recovery_target<=0;
            sample_q<=0;start_q<=0;clear_q<=0;retire_q<=0;branch_q<=0;
            ar_q<=0;aw_q<=0;ddr_q<=0;classification_q<=8;
            for(k=0;k<13;k=k+1) count[k]<=0;
        end else begin
            sample_q<=sample;start_q<=start_event;clear_q<=arm || cancel;
            retire_q<=events[0];branch_q<=events[5];ar_q<=ar_fire;aw_q<=aw_fire;
            ddr_q<=ddr_increment;classification_q<=classification;
            // Track branch recovery even outside ROI, matching the 2A observer.
            if(events[1]) recovering<=0;
            else if(events[5]) begin recovering<=1; recovery_target<=branch_target; end
            else if(recovering && delivered) recovering<=0;
            if(state==ARMED && events[0] && retire_pc==start_pc) start_seen<=1;
            if(state==RUNNING && events[0] && retire_pc==stop_pc) stop_seen<=1;
            if(access && write && !error) begin
                if(addr==12'h10c) start_pc<=wdata;
                if(addr==12'h110) stop_pc<=wdata;
            end
            if(arm || cancel) begin
                state<=arm?ARMED:IDLE; start_seen<=0; stop_seen<=0;
                start_tick<=0; stop_tick<=0;
            end else if(stop_event) begin
                state<=DONE; stop_tick<=timer_value;
            end else if(start_event) begin
                state<=RUNNING; start_tick<=timer_value; stop_tick<=0; stop_seen<=0;
            end
            if(clear_q) begin
                for(k=0;k<13;k=k+1) count[k]<=0;
            end else if(sample_q) begin
                if(start_q) for(k=0;k<13;k=k+1) count[k]<=0;
                count[0]<=start_q?64'd1:count[0]+64'd1;
                count[1]<=(start_q?64'd0:count[1])+{63'd0,retire_q};
                count[classification_q]<=(start_q?64'd0:count[classification_q])+64'd1;
                count[9]<=(start_q?64'd0:count[9])+{62'd0,ddr_q};
                count[10]<=(start_q?64'd0:count[10])+{63'd0,branch_q};
                count[11]<=(start_q?64'd0:count[11])+{63'd0,ar_q};
                count[12]<=(start_q?64'd0:count[12])+{63'd0,aw_q};
            end
        end
    end
endmodule
