//////////////////////////////////////////////////////////////////////////////
//
// Copyright (c) 00 PANGO MICROSYSTEMS, INC
// ALL RIGHTS REVERVED.
//
// THE SOURCE CODE CONTAINED HEREIN IS PROPRIETARY TO PANGO MICROSYSTEMS, INC.
// IT SHALL NOT BE REPRODUCED OR DISCLOSED IN WHOLE OR IN PART OR USED BY
// PARTIES WITHOUT WRITTEN AUTHORIZATION FROM THE OWNER.
//
//////////////////////////////////////////////////////////////////////////////
`timescale 1ns/1ns
module apb_master (
    input               clk       ,
    input               rst_n     ,
    input               temp_rd_en  ,
    input               volt_rd_en  ,
    output  reg         psel     ,
    output  reg [5:0]   paddr    ,
    output  reg         penable  ,
    output  reg         pwrite   ,
    output  reg [7:0]   pwdata   ,
    input               pready     ,
    input       [7:0]   prdata ,
    output reg [11:0]   read_data   
);

localparam [4:0] IDLE           = 5'd0;
localparam [4:0] WRITE1_SETUP   = 5'd1;
localparam [4:0] WRITE1_ACCESS  = 5'd2;
localparam [4:0] DELAY0         = 5'd3;
localparam [4:0] WRITE2_SETUP   = 5'd4;
localparam [4:0] WRITE2_ACCESS  = 5'd5;
localparam [4:0] DELAY1         = 5'd6;
localparam [4:0] WRITE3_SETUP   = 5'd7;
localparam [4:0] WRITE3_ACCESS  = 5'd8;
localparam [4:0] DELAY2         = 5'd9;
localparam [4:0] WRITE4_SETUP   = 5'd10;
localparam [4:0] WRITE4_ACCESS  = 5'd11;
localparam [4:0] DELAY3         = 5'd12;
localparam [4:0] WRITE5_SETUP   = 5'd13;
localparam [4:0] WRITE5_ACCESS  = 5'd14;
localparam [4:0] DELAY4         = 5'd15;
localparam [4:0] WRITE6_SETUP   = 5'd16;
localparam [4:0] WRITE6_ACCESS  = 5'd17;
localparam [4:0] DELAY5         = 5'd18;
localparam [4:0] WRITE7_SETUP   = 5'd19;
localparam [4:0] WRITE7_ACCESS  = 5'd20;
localparam [4:0] DELAY6         = 5'd21;
localparam [4:0] WRITE8_SETUP   = 5'd22;
localparam [4:0] WRITE8_ACCESS  = 5'd23;
localparam [4:0] DELAY7         = 5'd24;
localparam [4:0] READ1_SETUP    = 5'd25;
localparam [4:0] READ1_ACCESS   = 5'd26;
localparam [4:0] DELAY8         = 5'd27;
localparam [4:0] READ2_SETUP    = 5'd28;
localparam [4:0] READ2_ACCESS   = 5'd29;
localparam [4:0] DONE           = 5'd30;

reg [4:0] cur_state;
reg [4:0] nxt_state;
reg [7:0]  read1_data;  
reg [7:0]  read2_data;   
reg [19:0] cnt;
reg vt_flag;

localparam [19:0] DLY_20US = 20'd999;
`ifdef RTL_SIM
localparam [14:0] DLY_20MS = 20'd1999;
`else 
localparam [19:0] DLY_20MS = 20'd999999;
`endif

always @(posedge clk or negedge rst_n)
begin
    if(!rst_n)
        vt_flag <= 1'b0 ;
    else if(temp_rd_en)
        vt_flag <= 1'b1 ;
    else if(volt_rd_en)
        vt_flag <= 1'b0 ;
end

always @(posedge clk or negedge rst_n)
begin
    if(!rst_n)
        cur_state <= IDLE;
    else 
	    cur_state <= nxt_state ;
end

always @(*)begin
	nxt_state = IDLE;
	case(cur_state)
	    IDLE              : nxt_state = (temp_rd_en | volt_rd_en) ? WRITE1_SETUP : IDLE;
	    WRITE1_SETUP      : nxt_state = WRITE1_ACCESS;
	    WRITE1_ACCESS     : nxt_state = pready ? DELAY0 : WRITE1_ACCESS;
        DELAY0            : nxt_state = (cnt >= 20'd19) ? WRITE2_SETUP : DELAY0;
	    WRITE2_SETUP      : nxt_state = WRITE2_ACCESS;
	    WRITE2_ACCESS     : nxt_state = pready ? DELAY1 : WRITE2_ACCESS;
        DELAY1            : nxt_state = (cnt >= DLY_20US) ? WRITE3_SETUP : DELAY1;
	    WRITE3_SETUP      : nxt_state = WRITE3_ACCESS;
	    WRITE3_ACCESS     : nxt_state = pready ? DELAY2 : WRITE3_ACCESS;
        DELAY2            : nxt_state = (cnt >= 20'd19) ? WRITE4_SETUP : DELAY2;
	    WRITE4_SETUP      : nxt_state = WRITE4_ACCESS;
	    WRITE4_ACCESS     : nxt_state = pready ? DELAY3 : WRITE4_ACCESS;
        DELAY3            : nxt_state = (cnt >= 20'd19) ? WRITE5_SETUP : DELAY3;
	    WRITE5_SETUP      : nxt_state = WRITE5_ACCESS;
	    WRITE5_ACCESS     : nxt_state = pready ? DELAY4 : WRITE5_ACCESS;
	    DELAY4            : nxt_state = (cnt == DLY_20US) ? WRITE6_SETUP : DELAY4;
	    WRITE6_SETUP      : nxt_state = WRITE6_ACCESS;
	    WRITE6_ACCESS     : nxt_state = pready ? DELAY5 : WRITE6_ACCESS;
	    DELAY5            : nxt_state = (cnt == DLY_20MS) ? WRITE7_SETUP : DELAY5;
	    WRITE7_SETUP      : nxt_state = WRITE7_ACCESS;
	    WRITE7_ACCESS     : nxt_state = pready ? DELAY6: WRITE7_ACCESS;
        DELAY6            : nxt_state = (cnt >= 20'd19) ? WRITE8_SETUP : DELAY6;
	    WRITE8_SETUP      : nxt_state = WRITE8_ACCESS;
	    WRITE8_ACCESS     : nxt_state = pready ? DELAY7: WRITE8_ACCESS;
        DELAY7            : nxt_state = (cnt >= 20'd19) ? READ1_SETUP : DELAY7;
	    READ1_SETUP       : nxt_state = READ1_ACCESS;
	    READ1_ACCESS      : nxt_state = pready ? DELAY8: READ1_ACCESS;
        DELAY8            : nxt_state = (cnt >= 20'd19) ? READ2_SETUP : DELAY8;
	    READ2_SETUP       : nxt_state = READ2_ACCESS;
	    READ2_ACCESS      : nxt_state = pready ? DONE : READ2_ACCESS;
	    DONE              : nxt_state = IDLE;
        default           : nxt_state = IDLE;
    endcase
end

always @(posedge clk or negedge rst_n)begin
    if(!rst_n)
	    cnt <= 20'd0;
    else if((cur_state == WRITE1_ACCESS) |(cur_state == WRITE2_ACCESS) |(cur_state == WRITE3_ACCESS) |(cur_state == WRITE4_ACCESS) |(cur_state == WRITE5_ACCESS) |
            (cur_state == WRITE6_ACCESS) |(cur_state == WRITE7_ACCESS) |(cur_state == WRITE8_ACCESS) | (cur_state == READ1_ACCESS) | (cur_state == READ2_ACCESS))
	    cnt <= 20'd0;
    else
        cnt <= cnt + 1'd1;
end

always @(posedge clk or negedge rst_n)begin
    if(!rst_n)begin
        psel       <= 1'b0;
	penable    <= 1'b0;
	paddr      <= 6'h00;
	pwrite     <= 1'b0;
	pwdata     <= 8'h00;
	read1_data  <= 8'h00;
	read2_data  <= 8'h00;
     end
     else begin
	 case(cur_state)
             WRITE1_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h0e;
	             pwrite     <= 1'b1;
	             pwdata     <= 8'h00;
             end
             WRITE1_ACCESS :begin
		         penable    <= 1'b1;
             end
             WRITE2_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h0e;
	             pwdata     <= 8'h04;
             end
             WRITE2_ACCESS :begin
		         penable    <= 1'b1;
             end
             WRITE3_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h0b;
	             pwdata     <= vt_flag ? 8'h00 : 8'h10;
             end
             WRITE3_ACCESS :begin
		         penable    <= 1'b1;
             end
             WRITE4_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h04;
	             pwdata     <= vt_flag ? 8'h07 : 8'h0d;
             end
             WRITE4_ACCESS :begin
		         penable    <= 1'b1;
             end
             WRITE5_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h0e;
	             pwdata     <= 8'h02;
             end
             WRITE5_ACCESS :begin
		         penable    <= 1'b1;
             end
             WRITE6_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h0e;
	             pwdata     <= 8'h06;
             end
             WRITE6_ACCESS :begin
		         penable    <= 1'b1;
             end
             WRITE7_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h0e;
	             pwdata     <= 8'h01;
             end
             WRITE7_ACCESS :begin
		         penable    <= 1'b1;
             end
             WRITE8_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= 6'h0e;
	             pwdata     <= 8'h00;
             end
             WRITE8_ACCESS :begin
		         penable    <= 1'b1;
             end
             READ1_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= vt_flag ? 6'h01 : 8'h02; 
	             pwrite     <= 1'b0;
             end
             READ1_ACCESS :begin
		         penable    <= 1'b1;
                 if(pready)
                     read1_data <= prdata;
             end
             READ2_SETUP :begin
                 psel       <= 1'b1;
	             penable    <= 1'b0;
	             paddr      <= vt_flag ? 6'h02 : 8'h03;
             end
             READ2_ACCESS :begin
		         penable    <= 1'b1;
                 if(pready)
                     read2_data <= prdata;
             end
             default      :begin
                 psel       <= 1'b0;
	         penable    <= 1'b0;
	     end
	 endcase
    end
end

always @(posedge clk or negedge rst_n)
begin
    if(!rst_n)
	    read_data <= 12'b0;
    else if(vt_flag == 1'b1)
	    read_data <= {2'b00,read2_data[1:0],read1_data[7:0]};
    else
	    read_data <= {read2_data[5:0],read1_data[7:2]};
end
endmodule
