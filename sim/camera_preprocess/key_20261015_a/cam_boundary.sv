`timescale 1ns/1ps
// Explicitly marked Camera MMIO/ownership BOUNDARY MODEL for the preprocess key
// group. It reproduces only the already-accepted Camera ABI2 ownership subset the
// real CPU program uses (SELECT/TOKEN/CLAIM/RELEASE + read-only metadata). It is
// not the real camera_mmio, not DVP/PCLK capture and not board_top/PHY.
module cam_boundary(
    input wire clk,resetn,
    input wire req_valid,req_write,
    input wire [1:0] req_size,
    input wire [31:0] req_addr,req_wdata,
    input wire [3:0] req_wstrb,
    output wire req_ready,
    output reg rsp_valid,rsp_error,
    output reg [31:0] rsp_rdata,
    output wire dual_mode,
    output wire [1:0] cpu_owned,
    input wire [1:0] external_hold,
    output wire [31:0] source_seq0,source_seq1,
    output wire source_geometry_ok
);
    localparam [1:0] BUF_FREE=0,BUF_WRITING=1,BUF_READY=2,BUF_CPU=3;
    reg [1:0] state[0:1];
    reg [31:0] seq[0:1];
    reg [31:0] expected_seq,global_seq;
    reg [1:0] selected;
    assign dual_mode=1'b1;
    assign source_geometry_ok=1'b1;
    assign source_seq0=seq[0];
    assign source_seq1=seq[1];
    assign cpu_owned={state[1]==BUF_CPU,state[0]==BUF_CPU};
    assign req_ready=resetn && !rsp_valid;
    wire accept=req_valid && req_ready;
    wire ctrl=accept && req_write && req_addr==4 && req_size==2 && req_wstrb==15;
    wire select_cmd=accept && req_write && req_addr==44 && req_size==2 && req_wstrb==15 && req_wdata<=1;
    wire token_cmd=accept && req_write && req_addr==56 && req_size==2 && req_wstrb==15;
    wire ready_any=(state[0]==BUF_READY)||(state[1]==BUF_READY);
    task automatic publish(input [1:0] b,input [31:0] s);
        begin state[b]<=BUF_READY;seq[b]<=s;global_seq<=global_seq+1;end
    endtask
    always @(posedge clk or negedge resetn) begin
        if(!resetn) begin
            rsp_valid<=0;rsp_error<=0;rsp_rdata<=0;
            state[0]<=BUF_FREE;state[1]<=BUF_FREE;seq[0]<=0;seq[1]<=0;
            expected_seq<=0;global_seq<=0;selected<=0;
        end else begin
            rsp_valid<=0;
            if(accept) begin
                rsp_valid<=1;rsp_error<=0;rsp_rdata<=0;
                if(req_size!=2 || req_addr[1:0]!=0 || req_addr>60) rsp_error<=1;
                else if(req_write) begin
                    if(ctrl) begin
                        if(req_wdata==32'd32) begin
                            if(state[selected]!=BUF_READY || expected_seq!=seq[selected]) rsp_error<=1;
                            else state[selected]<=BUF_CPU;
                        end else if(req_wdata==32'd64) begin
                            if(state[selected]!=BUF_CPU || expected_seq!=seq[selected] ||
                               external_hold[selected]) rsp_error<=1;
                            else state[selected]<=BUF_FREE;
                        end else rsp_error<=1;
                    end else if(select_cmd) selected<=req_wdata[0];
                    else if(token_cmd) expected_seq<=req_wdata;
                    else rsp_error<=1;
                end else case(req_addr[5:2])
                    0: rsp_rdata<=32'h43414d02;
                    2: rsp_rdata<={24'b0,1'b0,1'b1,1'b1,1'b0,1'b0,ready_any,1'b0,1'b1};
                    3: rsp_rdata<=32'h41000000+(selected?32'h00200000:32'd0);
                    4: rsp_rdata<=32'd1843200;
                    5: rsp_rdata<=seq[selected];
                    6: rsp_rdata<=32'd921600;
                    7: rsp_rdata<=32'd0;
                    8: rsp_rdata<=32'h5640;
                    9: rsp_rdata<=32'd57600;
                    10: rsp_rdata<=32'h5a5a5a5a;
                    11: rsp_rdata<={31'b0,selected};
                    12: rsp_rdata<={22'b0,1'b0,1'b1,1'b0,1'b0,selected,state[1],state[0]};
                    13: rsp_rdata<=global_seq;
                    14: rsp_rdata<=expected_seq;
                    15: rsp_rdata<=32'd0;
                    default: rsp_error<=1;
                endcase
            end
        end
    end
endmodule
