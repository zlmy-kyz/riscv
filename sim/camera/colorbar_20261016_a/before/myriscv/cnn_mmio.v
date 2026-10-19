`timescale 1ns/1ps
// digits10 ABI1. Native reads are one 256bit beat, ID4, local word addresses.
module cnn_mmio #(parameter integer CLK_HZ=93750000) (
    input wire clk, resetn,
    input wire req_valid, req_write,
    input wire [1:0] req_size,
    input wire [31:0] req_addr, req_wdata,
    input wire [3:0] req_wstrb,
    output wire req_ready,
    output reg rsp_valid, rsp_error,
    output reg [31:0] rsp_rdata,
    input wire pp_done, pp_busy, pp_result_buf,
    input wire [31:0] pp_result_seq,
    output wire pp_hold,
    output wire [27:0] araddr,
    output wire arvalid,
    input wire arready, rvalid, rlast, protocol_error,
    input wire [3:0] rid,
    input wire [255:0] rdata
);
    localparam IDLE=0, GSTART=1, ADDR=2, RESPONSE=3, SERIAL=4,
        GWAIT=5, ESTART=6, EWAIT=7, HANG=8;
    reg [3:0] state;
    wire busy=state!=IDLE;
    reg done, error, aborting;
    reg [7:0] error_code;
    reg [31:0] expected_seq, result_seq, timer;
    reg expected_buf, result_buf;
    reg [9:0] reads;
    reg [4:0] byte_index;
    reg [255:0] beat;
    reg [31:0] model_id, model_crc;
    reg [12:0] load_count;
    reg loading, load_error, model_valid;
    wire accept=req_valid && req_ready;
    wire legal= req_size==2 && req_addr[1:0]==0 && req_addr<=32'h64;
    wire write=accept && req_write && legal && req_wstrb==15;
    wire start_cmd=write && req_addr==4 && req_wdata==1 && !busy && model_valid &&
        pp_done && !pp_busy && pp_result_seq==expected_seq && pp_result_buf==expected_buf && !protocol_error;
    wire abort_cmd=write && req_addr==4 && req_wdata==2;
    wire clear_cmd=write && req_addr==4 && req_wdata==4 && !busy && !protocol_error;
    wire begin_cmd=write && req_addr==4 && req_wdata==8 && !busy;
    wire id_cmd=write && req_addr==12 && !busy && loading && load_count==0;
    wire seq_cmd=write && req_addr==28 && !busy;
    wire buf_cmd=write && req_addr==32 && !busy && req_wdata<=1;
    // Conservative bound covers the largest dot (144 terms) including -128 input.
    wire bias_ok=($signed(req_wdata)>=-32'sd2145142783 && $signed(req_wdata)<=32'sd2145142783);
    wire param_ok=load_count<6152 ? (req_wdata<=255 && req_wdata!=128) :
                  load_count<6218 ? bias_ok : load_count<6222 && req_wdata<=31;
    wire data_cmd=write && req_addr==16 && !busy && loading && !load_error && param_ok;
    wire commit_cmd=write && req_addr==20 && !busy && loading && !load_error &&
        load_count==6222 && model_id!=0 && req_wdata==~model_crc;
    wire expired=busy && timer>=CLK_HZ*3;
    wire cancel_job=aborting || abort_cmd || expired;
    wire read_fire=rvalid && (state==RESPONSE || (state==ADDR && arready));
    wire gr_start_ready, gr_ready, gr_valid, gr_done, gr_error;
    wire [7:0] gr_data;
    wire [9:0] gr_index;
    wire [10:0] gr_count;
    wire engine_ready, engine_done, engine_error;
    wire [31:0] engine_score;
    wire [3:0] engine_class;
    wire [3:0] score_sel=(req_addr[7:0]-8'h40)>>2;
    assign req_ready=resetn && !rsp_valid;
    assign pp_hold=busy;
    assign arvalid=resetn && state==ADDR;
    assign araddr=28'h0800000+({18'b0,reads}<<3);
    function [31:0] crc_word;
        input [31:0] previous, value;
        reg [31:0] c;
        integer i;
        begin
            c=previous ^ value;
            for(i=0;i<32;i=i+1) c=c[0] ? (c>>1)^32'hedb88320 : c>>1;
            crc_word=c;
        end
    endfunction
    cnn_rgb96_gray32 u_gray (.clk(clk),.resetn(resetn && state!=IDLE && state!=HANG),
        .start_valid(state==GSTART),.start_ready(gr_start_ready),
        .in_valid(state==SERIAL && !cancel_job),.in_ready(gr_ready),
        .in_data(beat[byte_index*8 +: 8]),.in_last(reads==864 && byte_index==31),
        .out_valid(gr_valid),.out_ready(1'b1),.out_data(gr_data),.out_index(gr_index),
        .busy(),.done(gr_done),.error(gr_error),.input_bytes(),.output_bytes(gr_count));
    cnn_digits_engine u_engine (.clk(clk),.resetn(resetn),.cancel(state==IDLE || state==HANG),
        .param_we(data_cmd),.param_index(load_count),.param_data(req_wdata),
        .gray_we(gr_valid && !cancel_job && !protocol_error),.gray_addr(gr_index),.gray_data(gr_data),
        .start(state==ESTART && !cancel_job),.ready(engine_ready),.done(engine_done),.error(engine_error),
        .score_index(score_sel),.score_data(engine_score),.prediction(engine_class));
    always @(posedge clk or negedge resetn) begin
        if(!resetn) begin
            state<=IDLE; done<=0; error<=0; aborting<=0; error_code<=0;
            expected_seq<=0; expected_buf<=0; result_seq<=0; result_buf<=0;
            timer<=0; reads<=0; byte_index<=0; beat<=0;
            model_id<=0; model_crc<=32'hffffffff; load_count<=0;
            loading<=0; load_error<=0; model_valid<=0;
            rsp_valid<=0; rsp_error<=0; rsp_rdata<=0;
        end else begin
            rsp_valid<=0;
            if(accept) begin
                rsp_valid<=1; rsp_error<=0; rsp_rdata<=0;
                if(!legal) rsp_error<=1;
                else if(req_write) begin
                    if(!(start_cmd || abort_cmd || clear_cmd || begin_cmd || id_cmd ||
                         seq_cmd || buf_cmd || data_cmd || commit_cmd)) rsp_error<=1;
                end else case(req_addr[7:2])
                    0: rsp_rdata<=32'h434e4e01;
                    1: rsp_rdata<=0;
                    2: rsp_rdata<={26'b0,load_error,loading,model_valid,(error|protocol_error),done,busy};
                    3: rsp_rdata<=model_id;
                    4: rsp_rdata<=0;
                    5: rsp_rdata<=~model_crc;
                    6: rsp_rdata<={19'b0,load_count};
                    7: rsp_rdata<=expected_seq;
                    8: rsp_rdata<={31'b0,expected_buf};
                    9: rsp_rdata<=done ? result_seq : 0;
                    10: rsp_rdata<=done ? {31'b0,result_buf} : 0;
                    11: rsp_rdata<=timer;
                    12: rsp_rdata<={22'b0,reads};
                    13: rsp_rdata<=done ? 32'd1024 : {21'b0,gr_count};
                    14: rsp_rdata<=done ? {28'b0,engine_class} : 0;
                    15: rsp_rdata<=protocol_error ? 32'd3 : {24'b0,error_code};
                    default: rsp_rdata<=done ? engine_score : 0;
                endcase
            end
            if(begin_cmd) begin
                loading<=1; load_error<=0; model_valid<=0; model_id<=0;
                load_count<=0; model_crc<=32'hffffffff; done<=0;
            end
            if(id_cmd) model_id<=req_wdata;
            if(seq_cmd) expected_seq<=req_wdata;
            if(buf_cmd) expected_buf<=req_wdata[0];
            if(data_cmd) begin
                load_count<=load_count+1'b1; model_crc<=crc_word(model_crc,req_wdata);
            end
            if(write && req_addr==16 && !busy && loading && !data_cmd) load_error<=1;
            if(commit_cmd) begin loading<=0; model_valid<=1; end
            if(clear_cmd) begin done<=0; error<=0; error_code<=0; end
            if(start_cmd) begin
                state<=GSTART; done<=0; error<=0; aborting<=0; error_code<=0;
                result_seq<=pp_result_seq; result_buf<=pp_result_buf;
                timer<=0; reads<=0; byte_index<=0;
            end else if(busy) begin
                if(!expired) timer<=timer+1'b1;
                if(cancel_job) begin
                    done<=0; error<=1; aborting<=1;
                    if(!aborting) error_code<=abort_cmd ? 1 : 2;
                end
                case(state)
                    GSTART: if(gr_start_ready) state<=ADDR;
                    ADDR,RESPONSE: begin
                        if(read_fire) begin
                            if(rid!=4 || !rlast) begin state<=HANG; error<=1; error_code<=3; end
                            else if(cancel_job) state<=IDLE;
                            else begin beat<=rdata; reads<=reads+1'b1; byte_index<=0; state<=SERIAL; end
                        end else if(state==ADDR && arready) state<=RESPONSE;
                    end
                    SERIAL: if(gr_ready) begin
                        if(byte_index==31) state<= reads==864 ? GWAIT : ADDR;
                        else byte_index<=byte_index+1'b1;
                    end
                    GWAIT: begin
                        if(gr_error) begin state<=IDLE; error<=1; error_code<=4; end
                        else if(gr_done) begin
                            if(gr_count==1024 && reads==864) state<=ESTART;
                            else begin state<=IDLE; error<=1; error_code<=4; end
                        end
                    end
                    ESTART: if(engine_ready) state<=EWAIT;
                    EWAIT: begin
                        if(engine_error) begin state<=IDLE; error<=1; error_code<=5; end
                        else if(engine_done) begin state<=IDLE; done<=1; end
                    end
                    default: begin end
                endcase
                // Never withdraw an exposed AR or release while waiting for R.
                if(cancel_job && state!=ADDR && state!=RESPONSE && state!=HANG) state<=IDLE;
                // DONE must not win a same-cycle abort/timeout.
                if(cancel_job) done<=0;
            end
            if(protocol_error) begin
                done<=0; error<=1; error_code<=3;
                if(busy) state<=HANG;
            end
        end
    end
endmodule
