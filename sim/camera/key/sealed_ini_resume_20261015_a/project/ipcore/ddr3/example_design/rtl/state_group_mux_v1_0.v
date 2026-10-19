////////////////////////////////////////////////////////////////
// Copyright (c) 019 PANGO MICROSYSTEMS, INC
// ALL RIGHTS REVERVED.
////////////////////////////////////////////////////////////////
//Description:
//Author:  wxxiao
//History: v1.0
////////////////////////////////////////////////////////////////
`timescale 1ns/1ps
module state_group_mux_v1_0 #(
  parameter MEM_DQS_WIDTH = 4,
  parameter REM_DQS_WIDTH = 9 - MEM_DQS_WIDTH
)(
    input                                  ddrphy_sysclk        ,
    input                                  ddrphy_rst_n         ,

    input       [75*MEM_DQS_WIDTH -1:0]    debug_data           ,
    input       [24*MEM_DQS_WIDTH -1:0]    dbg_slice_state      ,
    input       [64*MEM_DQS_WIDTH -1:0]    dq_idly_bin          ,
    input       [64*MEM_DQS_WIDTH -1:0]    dq_odly_bin          ,
    input       [MEM_DQS_WIDTH*64 -1:0]    err_data_pre         ,
    input       [MEM_DQS_WIDTH*64 -1:0]    err_data_aft         ,
    input       [MEM_DQS_WIDTH*64 -1:0]    err_data_out         ,
    input       [MEM_DQS_WIDTH*64 -1:0]    err_flag_out         ,
    input       [MEM_DQS_WIDTH*64 -1:0]    next_err_data        ,
    input       [31:0]                     ctrl_bus_14          ,
    output reg  [74:0]                     debug_data_group     ,
    output reg  [23:0]                     dbg_slice_state_group,
    output reg  [63:0]                     dq_idly_bin_group    ,
    output reg  [63:0]                     dq_odly_bin_group    ,
    output reg  [63:0]                     err_data_pre_group   ,
    output reg  [63:0]                     err_data_aft_group   ,
    output reg  [63:0]                     err_data_out_group   ,
    output reg  [63:0]                     err_flag_out_group   ,
    output reg  [63:0]                     next_err_data_group   
 );

    wire [75*9-1:0] status_debug_data;
    wire [24*9-1:0] status_dbg_slice_state;
    wire [64*9-1:0] status_dq_idly_bin;
    wire [64*9-1:0] status_dq_odly_bin;
    wire [64*9-1:0] status_err_data_pre;
    wire [64*9-1:0] status_err_data_aft;
    wire [64*9-1:0] status_err_data_out;
    wire [64*9-1:0] status_err_flag_out;
    wire [64*9-1:0] status_next_err_data;

    assign status_debug_data      = {{75*REM_DQS_WIDTH{1'b0}},debug_data};
    assign status_dbg_slice_state = {{24*REM_DQS_WIDTH{1'b0}},dbg_slice_state};
    assign status_dq_idly_bin     = {{64*REM_DQS_WIDTH{1'b0}},dq_idly_bin};
    assign status_dq_odly_bin     = {{64*REM_DQS_WIDTH{1'b0}},dq_odly_bin};
    assign status_err_data_pre    = {{64*REM_DQS_WIDTH{1'b0}},err_data_pre   };
    assign status_err_data_aft    = {{64*REM_DQS_WIDTH{1'b0}},err_data_aft   };
    assign status_err_data_out    = {{64*REM_DQS_WIDTH{1'b0}},err_data_out   };
    assign status_err_flag_out    = {{64*REM_DQS_WIDTH{1'b0}},err_flag_out   };
    assign status_next_err_data   = {{64*REM_DQS_WIDTH{1'b0}},next_err_data  };


 always @(posedge ddrphy_sysclk or negedge ddrphy_rst_n)
     if(!ddrphy_rst_n)  begin
        debug_data_group        <= 75'b0;
        dbg_slice_state_group   <= 24'b0;
        dq_idly_bin_group       <= 64'b0;
        dq_odly_bin_group       <= 64'b0;
        err_data_pre_group      <= 64'b0;
        err_data_aft_group      <= 64'b0;
        err_data_out_group      <= 64'b0;
        err_flag_out_group      <= 64'b0;
        next_err_data_group     <= 64'b0;
     end
     else begin
         case(ctrl_bus_14)
                  32'd0: begin                             
                             debug_data_group        <= status_debug_data[75*0 +: 75];
                             dbg_slice_state_group   <= status_dbg_slice_state[24*0 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*0 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*0 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*0 +: 64];
                             err_data_aft_group      <= status_err_data_aft[64*0 +: 64];  
                             err_data_out_group      <= status_err_data_out[64*0 +: 64];         
                             err_flag_out_group      <= status_err_flag_out[64*0 +: 64]; 
                             next_err_data_group     <= status_next_err_data[64*0 +: 64];
                           end

                  32'd1: begin                             
                             debug_data_group        <= status_debug_data[75*1 +: 75];     
                             dbg_slice_state_group   <= status_dbg_slice_state[24*1 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*1 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*1 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*1 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*1 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*1 +: 64];    
                             err_flag_out_group      <= status_err_flag_out[64*1 +: 64]; 
                             next_err_data_group     <= status_next_err_data[64*1 +: 64];
                           end

                  32'd2: begin                            
                             debug_data_group        <= status_debug_data[75*2 +: 75];     
                             dbg_slice_state_group   <= status_dbg_slice_state[24*2 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*2 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*2 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*2 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*2 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*2 +: 64];    
                             err_flag_out_group      <= status_err_flag_out[64*2 +: 64]; 
                             next_err_data_group     <= status_next_err_data[64*2 +: 64];
                           end

                   32'd3:begin                            
                             debug_data_group        <= status_debug_data[75*3 +: 75];     
                             dbg_slice_state_group   <= status_dbg_slice_state[24*3 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*3 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*3 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*3 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*3 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*3 +: 64];    
                             err_flag_out_group      <= status_err_flag_out[64*3 +: 64]; 
                             next_err_data_group     <= status_next_err_data[64*3 +: 64];
                           end
                           
                   32'd4: begin                            
                             debug_data_group        <= status_debug_data[75*4 +: 75];     
                             dbg_slice_state_group   <= status_dbg_slice_state[24*4 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*4 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*4 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*4 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*4 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*4 +: 64];    
                             err_flag_out_group      <= status_err_flag_out[64*4 +: 64]; 
                             next_err_data_group     <= status_next_err_data[64*4 +: 64];
                           end

                   32'd5: begin                            
                             debug_data_group        <= status_debug_data[75*5 +: 75];     
                             dbg_slice_state_group   <= status_dbg_slice_state[24*5 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*5 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*5 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*5 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*5 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*5 +: 64];    
                             err_flag_out_group      <= status_err_flag_out[64*5 +: 64]; 
                             next_err_data_group     <= status_next_err_data[64*5 +: 64];
                           end

                   32'd6: begin                            
                             debug_data_group        <= status_debug_data[75*6 +: 75];     
                             dbg_slice_state_group   <= status_dbg_slice_state[24*6 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*6 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*6 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*6 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*6 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*6 +: 64];    
                             err_flag_out_group      <= status_err_flag_out[64*6 +: 64]; 
                             next_err_data_group     <= status_next_err_data[64*6 +: 64]; 
                           end

                   32'd7: begin                            
                             debug_data_group        <= status_debug_data[75*7 +: 75];    
                             dbg_slice_state_group   <= status_dbg_slice_state[24*7 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*7 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*7 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*7 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*7 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*7 +: 64];
                             err_flag_out_group      <= status_err_flag_out[64*7 +: 64];
                             next_err_data_group     <= status_next_err_data[64*7 +: 64];
                           end
                   32'd8: begin                            
                             debug_data_group        <= status_debug_data[75*8 +: 75];    
                             dbg_slice_state_group   <= status_dbg_slice_state[24*8 +: 24];
                             dq_idly_bin_group       <= status_dq_idly_bin[64*8 +: 64];
                             dq_odly_bin_group       <= status_dq_odly_bin[64*8 +: 64];
                             err_data_pre_group      <= status_err_data_pre[64*8 +: 64];   
                             err_data_aft_group      <= status_err_data_aft[64*8 +: 64];   
                             err_data_out_group      <= status_err_data_out[64*8 +: 64];
                             err_flag_out_group      <= status_err_flag_out[64*8 +: 64];
                             next_err_data_group     <= status_next_err_data[64*8 +: 64];
                           end
                   default: begin                            
                             debug_data_group        <= 75'b0;
                             dbg_slice_state_group   <= 24'b0;
                             dq_idly_bin_group       <= 64'b0;
                             dq_odly_bin_group       <= 64'b0;
                             err_data_pre_group      <= 64'b0;
                             err_data_aft_group      <= 64'b0;
                             err_data_out_group      <= 64'b0;
                             err_flag_out_group      <= 64'b0;
                             next_err_data_group     <= 64'b0;
                           end
               endcase
   end

endmodule
