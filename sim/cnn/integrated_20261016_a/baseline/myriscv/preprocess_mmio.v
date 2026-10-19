`timescale 1ns/1ps
// Fixed 1280x720 RGB565 -> centered 720-square -> 96x96 RGB888/HWC.
// CPU claims a camera buffer first; busy holds that claim until every native
// read/write drains. Output is a separate 64KiB uncached, non-executable aperture.
module preprocess_mmio #(parameter integer CLK_HZ=93750000) (
    input wire clk, resetn,
    input wire req_valid, req_write,
    input wire [1:0] req_size,
    input wire [31:0] req_addr, req_wdata,
    input wire [3:0] req_wstrb,
    output wire req_ready,
    output reg rsp_valid, rsp_error,
    output reg [31:0] rsp_rdata,
    input wire camera_dual_mode, source_geometry_ok,
    input wire [1:0] cpu_owned,
    input wire [31:0] source_seq0, source_seq1,
    output reg busy, done,
    output wire [1:0] source_hold,
    output wire [27:0] araddr, awaddr,
    output wire arvalid, awvalid,
    output wire [255:0] wdata,
    input wire arready, rvalid, rlast, awready, wready, read_protocol_error,
    input wire [3:0] rid,
    input wire [255:0] rdata
);
    localparam IDLE=0, RADDR=1, RDATA=2, PACK=3, WADDR=4, WDATA=5, FINISH=6, HANG=7;
    reg [2:0] state, resume_state;
    reg selected_buf, active_buf;
    reg [31:0] expected_seq, job_seq, published_seq;
    reg error_latched, aborting;
    reg [7:0] error_code;
    reg [31:0] timer, elapsed, produced_bytes, pixels, writes, reads;
    reg [31:0] row_addr, source_addr;
    reg [6:0] x, y;
    reg [1:0] channel;
    reg [4:0] pack_count;
    reg [23:0] rgb;
    reg [255:0] pack_data;
    reg [31:0] crc, published_crc;
    wire [15:0] pixel=rdata[source_addr[4:1]*16 +: 16];
    wire [7:0] emit_byte=channel==0 ? rgb[23:16] : channel==1 ? rgb[15:8] : rgb[7:0];
    wire last_pixel=(x==95 && y==95);
    wire [2:0] next_pixel_state=channel!=2 ? PACK : last_pixel ? FINISH : RADDR;
    // Center-coordinate NN: floor((2*x+1)*15/4) = 3,11,18,26,...,716.
    wire [31:0] next_row=row_addr+(y[0] ? 32'd17920 : 32'd20480);
    wire [31:0] selected_seq=selected_buf ? source_seq1 : source_seq0;
    assign source_hold=busy ? (active_buf ? 2'b10 : 2'b01) : 2'b00;
    assign req_ready=resetn && !rsp_valid;
    wire accept=req_valid && req_ready;
    wire command=accept && req_write && req_addr==4 && req_size==2 && req_wstrb==15;
    wire start_cmd=command && req_wdata==1 && !busy && camera_dual_mode &&
                   source_geometry_ok && cpu_owned[selected_buf] && expected_seq==selected_seq &&
                   !read_protocol_error;
    wire abort_cmd=command && req_wdata==2;
    wire clear_cmd=command && req_wdata==4 && !busy && !read_protocol_error;
    wire select_cmd=accept && req_write && req_addr==12 && req_size==2 && req_wstrb==15 &&
                    !busy && req_wdata<=1;
    wire token_cmd=accept && req_write && req_addr==16 && req_size==2 && req_wstrb==15 && !busy;
    wire expired=busy && timer>=CLK_HZ*3;
    wire cancel=aborting || abort_cmd || expired || read_protocol_error;
    wire read_fire=rvalid && ((state==RDATA) || (state==RADDR && arready));
    wire write_fire=wready && ((state==WDATA) || (state==WADDR && awready));
    assign arvalid=resetn && state==RADDR;
    assign araddr={source_addr[29:5],3'b000};
    assign awvalid=resetn && state==WADDR;
    // Local byte 0x02000000 / 4, full 32-byte writes, 864 beats total.
    assign awaddr=28'h0800000 + (writes<<3);
    assign wdata=pack_data;
    function [31:0] crc_byte;
        input [31:0] previous;
        input [7:0] b;
        reg [31:0] c;
        integer n;
        begin
            c=previous ^ {24'b0,b};
            for(n=0;n<8;n=n+1) c=c[0] ? (c>>1)^32'hedb88320 : c>>1;
            crc_byte=c;
        end
    endfunction
    always @(posedge clk or negedge resetn) begin
        if (!resetn) begin
            state<=IDLE; resume_state<=IDLE; selected_buf<=0; active_buf<=0;
            expected_seq<=0; job_seq<=0; published_seq<=0;
            busy<=0; done<=0; error_latched<=0; aborting<=0; error_code<=0;
            timer<=0; elapsed<=0; produced_bytes<=0; pixels<=0; writes<=0; reads<=0;
            row_addr<=0; source_addr<=0; x<=0; y<=0; channel<=0; pack_count<=0;
            rgb<=0; pack_data<=0; crc<=32'hffffffff; published_crc<=0;
            rsp_valid<=0; rsp_error<=0; rsp_rdata<=0;
        end else begin
            rsp_valid<=0;
            if (accept) begin
                rsp_valid<=1; rsp_error<=0; rsp_rdata<=0;
                if(req_size!=2 || req_addr[1:0]!=0 || req_addr>60) rsp_error<=1;
                else if(req_write) begin
                    if(!(start_cmd || abort_cmd || clear_cmd || select_cmd || token_cmd)) rsp_error<=1;
                end else case(req_addr[5:2])
                    0: rsp_rdata<=32'h50525001;
                    1: rsp_rdata<=0;
                    2: rsp_rdata<={29'b0,(error_latched|read_protocol_error),done,busy};
                    3: rsp_rdata<={31'b0,selected_buf};
                    4: rsp_rdata<=expected_seq;
                    5: rsp_rdata<=done ? published_seq : 0;
                    6: rsp_rdata<=32'h42000000;
                    7: rsp_rdata<=done ? 32'd27648 : 0;
                    8: rsp_rdata<=done ? published_crc : 0;
                    9: rsp_rdata<=read_protocol_error ? 32'd3 : {24'b0,error_code};
                    10: rsp_rdata<=reads;
                    11: rsp_rdata<=writes;
                    12: rsp_rdata<=produced_bytes;
                    13: rsp_rdata<=busy ? timer : elapsed;
                    14: rsp_rdata<=32'h00600060; // height:width = 96:96
                    15: rsp_rdata<={31'b0,active_buf};
                endcase
            end
            if(select_cmd) selected_buf<=req_wdata[0];
            if(token_cmd) expected_seq<=req_wdata;
            if(clear_cmd) begin done<=0; error_latched<=0; error_code<=0; published_crc<=0; end
            if(start_cmd) begin
                active_buf<=selected_buf; job_seq<=selected_seq;
                busy<=1; done<=0; error_latched<=0; aborting<=0; error_code<=0;
                timer<=0; elapsed<=0; produced_bytes<=0; pixels<=0; writes<=0; reads<=0;
                row_addr<=selected_buf ? 32'h01202036 : 32'h01002036;
                source_addr<=selected_buf ? 32'h01202036 : 32'h01002036;
                x<=0; y<=0; channel<=0; pack_count<=0; pack_data<=0; crc<=32'hffffffff;
                published_seq<=0; published_crc<=0; state<=RADDR;
            end else if(busy) begin
                if(!expired) timer<=timer+1'b1;
                if(cancel) begin
                    done<=0; error_latched<=1; aborting<=1;
                    if(!aborting) error_code<=abort_cmd ? 8'd1 : 8'd2;
                end
                case(state)
                    RADDR,RDATA: begin
                        if(read_fire) begin
                            reads<=reads+1'b1;
                            if(rid!=3 || !rlast) begin
                                state<=HANG; error_latched<=1; error_code<=3;
                            end else if(cancel) begin busy<=0; elapsed<=timer; state<=IDLE; end
                            else begin
                                rgb<={{pixel[15:11],pixel[15:13]},
                                      {pixel[10:5],pixel[10:9]},
                                      {pixel[4:0],pixel[4:2]}};
                                state<=PACK;
                            end
                        end else if(state==RADDR && arready) state<=RDATA;
                    end
                    PACK: if(cancel) begin busy<=0; elapsed<=timer; state<=IDLE; end
                          else begin
                              pack_data[pack_count*8 +: 8]<=emit_byte;
                              crc<=crc_byte(crc,emit_byte);
                              produced_bytes<=produced_bytes+1'b1;
                              channel<=channel==2 ? 0 : channel+1'b1;
                              if(channel==2) begin
                                  pixels<=pixels+1'b1;
                                  if(x==95) begin x<=0; y<=y+1'b1; row_addr<=next_row; source_addr<=next_row; end
                                  else begin x<=x+1'b1; source_addr<=source_addr+(x[0] ? 32'd14 : 32'd16); end
                              end
                              if(pack_count==31) begin
                                  pack_count<=0; resume_state<=next_pixel_state; state<=WADDR;
                              end else begin pack_count<=pack_count+1'b1; state<=next_pixel_state; end
                          end
                    WADDR,WDATA: if(write_fire) begin
                        writes<=writes+1'b1;
                        if(cancel) begin busy<=0; elapsed<=timer; state<=IDLE; end
                        else state<=resume_state;
                    end else if(state==WADDR && awready) state<=WDATA;
                    FINISH: begin
                        busy<=0; elapsed<=timer; state<=IDLE;
                        if(!cancel && produced_bytes==27648 && pixels==9216 && writes==864 && reads==9216) begin
                            done<=1; published_seq<=job_seq; published_crc<=~crc;
                        end else if(!cancel) begin error_latched<=1; error_code<=4; end
                    end
                    default: begin end // HANG retains source lock until global reset.
                endcase
                if(read_protocol_error) begin
                    // A read-port fault must not withdraw an already exposed AW.
                    if((state!=WADDR && state!=WDATA) || write_fire) state<=HANG;
                    busy<=1; done<=0; error_latched<=1; aborting<=1; error_code<=3;
                end
            end else if(abort_cmd) begin
                done<=0; error_latched<=1; error_code<=1; published_crc<=0;
            end
        end
    end
endmodule
