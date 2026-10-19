//////////////////////////////////////////////////////////////////////////////
//
// Copyright (c) 2014 PANGO MICROSYSTEMS, INC
// ALL RIGHTS RESERVED.
//
// THE SOURCE CODE CONTAINED HEREIN IS PROPRIETARY TO PANGO MICROSYSTEMS, INC.
// IT SHALL NOT BE REPRODUCED OR DISCLOSED IN WHOLE OR IN PART OR USED BY
// PARTIES WITHOUT WRITTEN AUTHORIZATION FROM THE OWNER.
//
//////////////////////////////////////////////////////////////////////////////
//
// Library: General technology primitive
// Filename: GTP_DRM36K_E1.v
//
// Functional description:
// Fake module
//
// Parameter  description:
//
// Port description:
//
// Revision history:
//
//////////////////////////////////////////////////////////////////////////////

`timescale 1 ns / 1 ps

module GTP_DRM36K_E1
#(
    parameter GRS_EN = "TRUE",
    parameter [2:0] CSA_MASK = 3'b000,
    parameter [2:0] CSB_MASK = 3'b000,
    parameter integer DATA_WIDTH_A = 18,
    parameter integer DATA_WIDTH_B = 18,
    parameter WRITE_MODE_A = "NORMAL_WRITE",
    parameter WRITE_MODE_B = "NORMAL_WRITE",
    parameter integer DOA_REG = 0,
    parameter integer DOB_REG = 0,
    parameter integer DOA_REG_CLKINV = 0,
    parameter integer DOB_REG_CLKINV = 0,
    parameter [35:0] RSTA_VAL = 36'b0,
    parameter [35:0] RSTB_VAL = 36'b0,
    parameter RST_TYPE = "SYNC",
    parameter RAM_MODE = "TRUE_DUAL_PORT",
    parameter RAM_CASCADE = "NONE",
    parameter ECC_WRITE_EN = "FALSE",
    parameter ECC_READ_EN = "FALSE",
    parameter [287:0] INIT_00 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_01 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_02 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_03 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_04 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_05 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_06 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_07 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_08 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_09 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_0A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_0B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_0C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_0D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_0E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_0F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_10 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_11 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_12 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_13 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_14 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_15 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_16 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_17 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_18 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_19 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_1A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_1B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_1C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_1D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_1E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_1F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_20 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_21 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_22 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_23 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_24 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_25 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_26 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_27 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_28 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_29 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_2A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_2B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_2C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_2D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_2E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_2F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_30 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_31 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_32 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_33 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_34 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_35 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_36 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_37 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_38 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_39 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_3A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_3B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_3C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_3D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_3E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_3F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_40 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_41 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_42 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_43 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_44 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_45 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_46 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_47 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_48 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_49 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_4A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_4B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_4C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_4D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_4E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_4F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_50 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_51 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_52 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_53 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_54 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_55 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_56 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_57 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_58 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_59 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_5A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_5B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_5C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_5D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_5E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_5F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_60 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_61 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_62 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_63 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_64 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_65 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_66 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_67 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_68 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_69 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_6A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_6B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_6C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_6D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_6E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_6F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_70 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_71 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_72 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_73 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_74 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_75 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_76 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_77 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_78 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_79 = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_7A = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_7B = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_7C = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_7D = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_7E = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter [287:0] INIT_7F = 288'h000000000000000000000000000000000000000000000000000000000000000000000000,
    parameter INIT_FILE = "NONE",
    parameter integer BLOCK_X = 0,
    parameter integer BLOCK_Y = 0,
    parameter integer RAM_DATA_WIDTH = 18,
    parameter integer RAM_ADDR_WIDTH = 11,
    parameter INIT_FORMAT = "BIN"
) (
    output [35:0] DOA,
    output [35:0] DOB,
    input  [35:0] DIA,
    input  [35:0] DIB,
    input  [15:0] ADDRA,
    input  [15:0] ADDRB,
    input  ADDRA_HOLD,
    input  ADDRB_HOLD,
    input  [2:0] CSA,
    input  [2:0] CSB,
    input  [7:0] BWEA,
    input  [3:0] BWEB,
    input  CLKA,
    input  CLKB,
    input  CEA,
    input  CEB,
    input  WEA,
    input  WEB,
    input  ORCEA,
    input  ORCEB,
    input  RSTA,
    input  RSTB,
    input  CINA,
    input  CINB,
    input  INJECT_SBITERR,
    input  INJECT_DBITERR,
    output ECC_SBITERR,
    output ECC_DBITERR,
    output [8:0] ECC_RDADDR,
    output [7:0] ECC_PARITY,
    output COUTA,
    output COUTB
);
// synthesis translate_off


    localparam  BLOCK_DEPTH = 2**(DATA_WIDTH_A == 1 ? 15 :      // block type 32k*1
                                  DATA_WIDTH_A == 2 ? 14 :      // block type 16k*2
                                  DATA_WIDTH_A == 4 ? 13 :      // block type 8k*4
                                  DATA_WIDTH_A <= 9 ? 12 :      // block type 4k*8 or 4k*9
                                  DATA_WIDTH_A <= 18 ? 11 :     // block type 1k*36 or 1k*32
                                  DATA_WIDTH_A <= 36 ? 10 : 9); // block type 512*72 or 512*64     block memory address width

    localparam  BLOCK_WIDTH =   DATA_WIDTH_A;             //block memory data width

    localparam MEM_SIZE = 36864;
    localparam width_a = (DATA_WIDTH_A == 72) ? 36 : (DATA_WIDTH_A == 64) ? 32 : DATA_WIDTH_A;
    localparam width_b = (DATA_WIDTH_B == 72) ? 36 : (DATA_WIDTH_B == 64) ? 32 : DATA_WIDTH_B;

    integer  cnt;
    reg [9-1:0] mem [MEM_SIZE/9-1:0];

    reg csa_reg = 1'b0, csb_reg = 1'b0;
    reg [15:0] ada_reg = 16'b0, adb_reg = 16'b0;
    reg [35:0] da_reg = 36'b0, db_reg = 36'b0;
    reg wea_reg = 1'b0, web_reg = 1'b0;
    reg [7:0] bea_reg;
    reg [3:0] beb_reg;
    wire write_en_a, write_en_b, read_en_a, read_en_b;
    reg [35:0] DIA_int,DIB_int;
    reg ecc_wren,ecc_rden;
    wire ecc_sbiterr_int,ecc_dbiterr_int;
    reg ecc_sbiterr,ecc_dbiterr,ecc_sbiterr_reg,ecc_dbiterr_reg;
    reg [8:0] ecc_rdaddr,ecc_rdaddr_reg;
    reg [35:0] a_out_ecc,b_out_ecc;

    wire [7:0] ecc_p_enc,ecc_p_dec,ecc_p_out;
    wire [63:0] ecc_d_dec;
    wire [63:0] ecc_d_in;
    wire [63:0] ecc_d_out;
    wire [71:0] d_out_ecc;
    reg  [71:0] ecc_corrected;
    reg  [7:0] ecc_p_reg;

    reg [35:0] a_out;
    reg [35:0] a_out_reg;
    reg [35:0] b_out;
    reg [35:0] b_out_reg;

    wire grs, rsta_grs, rstb_grs;
    wire rsta_grs_sync;
    wire rstb_grs_sync;
    wire rsta_grs_async;
    wire rstb_grs_async;
    
    reg [35:0] doa, doa_mux, doa_reg_s, doa_reg_as;
    reg [35:0] dob, dob_mux, dob_reg_s, dob_reg_as;

    wire [35:0] doa_reg;
    wire [35:0] dob_reg;

    reg [1:0] cas_en;
    wire cas_inta, cas_intb;
    reg  cas_sela=1'b1, cas_selb=1'b1;
    wire [35:0] a_out_mux;
    wire [35:0] b_out_mux;
    wire CLKA_for_or, CLKB_for_or;
    wire rsta_int, rstb_int;

    wire [35:0] rsta_val_int;
    wire [35:0] rstb_val_int;

// synthesis translate_off

    assign rsta_val_int = ((DATA_WIDTH_A == 16 | DATA_WIDTH_A == 32) & DATA_WIDTH_B !=64) ? {4'h0,RSTA_VAL[34:27],RSTA_VAL[25:18],RSTA_VAL[16:9],RSTA_VAL[7:0]}:RSTA_VAL;
    assign rstb_val_int =  (DATA_WIDTH_B == 16 | DATA_WIDTH_B == 32) ? {4'h0,RSTB_VAL[34:27],RSTB_VAL[25:18],RSTB_VAL[16:9],RSTB_VAL[7:0]}:RSTB_VAL;

    initial begin
    doa_reg_s  = RSTA_VAL;
    doa_reg_as = RSTA_VAL;
    dob_reg_s  = RSTB_VAL;
    dob_reg_as = RSTB_VAL;
    end

    initial begin
        #1;
        a_out = rsta_val_int;
        a_out_reg = rsta_val_int;
        b_out = rstb_val_int;
        b_out_reg = rstb_val_int;
        doa = RSTA_VAL;
        dob = RSTB_VAL;
        doa_mux = RSTA_VAL;
        dob_mux = RSTB_VAL;
    end

   reg [RAM_DATA_WIDTH-1:0] ini_mem [2**RAM_ADDR_WIDTH-1:0];
   integer p;
   initial
   begin
      if(INIT_FILE != "NONE")
      begin
          if(INIT_FORMAT == "BIN")
              $readmemb(INIT_FILE,ini_mem);
          else
              $readmemh(INIT_FILE,ini_mem);
          for(p=0;p<20;p=p+1)
              $display("ini_mem[%d] = %b",p,ini_mem[p]);
      end
   end
///////////////////
// parameter check
///////////////////
    initial begin
        case (DATA_WIDTH_A)
            1, 2, 4, 8, 16, 32, 64: begin
                case (DATA_WIDTH_B)
                    1, 2, 4, 8, 16, 32, 64:  ; //null
                    default: begin
                        $display("ERROR: GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_B:%d is illegal. The legal values are 1,2,4,8,16,32 or 64.",DATA_WIDTH_B);
                        $finish;
                    end
                endcase
            end
            9, 18, 36, 72: begin
                case (DATA_WIDTH_B)
                    9, 18, 36, 72:    ; //null
                    default: begin
                        $display("ERROR: GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_B:%d is illegal. The legal values are 9,18,32 or 72.",DATA_WIDTH_B);
                        $finish;
                    end
                endcase
            end
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_A:%d is illegal. The legal values are 1,2,4,8,9,16,18,32,36,64 or 72.",DATA_WIDTH_A);
                $finish;
            end
        endcase

        case (WRITE_MODE_A)
            "NORMAL_WRITE",
            "TRANSPARENT_WRITE",
            "READ_BEFORE_WRITE":    ; //null 
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter WRITE_MODE_A: %s is illegal. The legal values are NORMAL_WRITE,TRANSPARENT_WRITE or READ_BEFORE_WRITE.", WRITE_MODE_A);
                $finish;
            end
        endcase

        case (WRITE_MODE_B)
            "NORMAL_WRITE",
            "TRANSPARENT_WRITE",
            "READ_BEFORE_WRITE":    ; //null  
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter WRITE_MODE_B: %s is illegal. The legal values are NORMAL_WRITE,TRANSPARENT_WRITE or READ_BEFORE_WRITE.", WRITE_MODE_B);
                $finish;
            end
        endcase

        case (DOA_REG)
            0,1:     ;//null
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter DOA_REG: %s is illegal. The legal values are 0 or 1.", DOA_REG);
                $finish;
            end
        endcase

        case (DOB_REG)
            0,1:     ;//null
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter DOB_REG: %s is illegal. The legal values are 0 or 1.", DOB_REG);
                $finish;
            end
        endcase

        case (DOA_REG_CLKINV)
            0,1:     ;//null
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter DOA_REG_CLKINV: %s is illegal. The legal values are 0 or 1.", DOA_REG_CLKINV);
                $finish;
            end
        endcase

        case (DOB_REG_CLKINV)
            0,1:     ;//null
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter DOB_REG_CLKINV: %s is illegal. The legal values are 0 or 1.", DOB_REG_CLKINV);
                $finish;
            end
        endcase

        case (RST_TYPE)
            "ASYNC",
            "SYNC":     ;//null
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter RST_TYPE: %s is illegal. The legal values are ASYNC or SYNC.", RST_TYPE);
                $finish;
            end
        endcase

        case (RAM_MODE)
            "ROM":	; //null
            "SINGLE_PORT": 
///////
		if ((DATA_WIDTH_A > 18 || DATA_WIDTH_B > 18) && (WRITE_MODE_A != "NORMAL_WRITE" || WRITE_MODE_B != "NORMAL_WRITE")) begin
                    $display("ERROR: GTP_DRM36K_E1 instance %m must to use NORMAL_WRITE if DATA_WIDTH_A and RAM_MODE: %d,%s.",DATA_WIDTH_A,RAM_MODE);
		    $finish;
                end 
//////    
            "SIMPLE_DUAL_PORT": begin
//////
                if ((DATA_WIDTH_A > 18 || DATA_WIDTH_B > 18) && (WRITE_MODE_A != "NORMAL_WRITE" || WRITE_MODE_B != "NORMAL_WRITE")) begin
                    $display("ERROR: GTP_DRM36K_E1 instance %m must to use NORMAL_WRITE if DATA_WIDTH_A and RAM_MODE: %d,%s.",DATA_WIDTH_A,RAM_MODE);
		    $finish;
                end
//////
                else if (DATA_WIDTH_A < 32 && WRITE_MODE_A != "NORMAL_WRITE") begin
                    $display("Warrning: GTP_DRM36K_E1 instance %m suggest to use TRUE_DUAL_PORT RAM_MODE if DATA_WIDTH_A and WRITE_MODE_A: %d,%s.",DATA_WIDTH_A,WRITE_MODE_A);
                end
            end
            "TRUE_DUAL_PORT": begin
                if (DATA_WIDTH_A > 36 || DATA_WIDTH_B > 36) begin
                    $display("ERROR: GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_A and DATA_WIDTH_B in TRUE_DUAL_PORT MODE:%d,%d is illegal. The legal values are 1,2,4,8,9,16 or 18.",DATA_WIDTH_A,DATA_WIDTH_B);
                    $finish;
                end
            end
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter RAM_MODE value: %s is illegal. The legal values are ROM or SINGLE_PORT, SIMPLE_DUAL_PORT or TRUE_DUAL_PORT.", RAM_MODE);
                $finish;
            end
        endcase
        
        case (RAM_CASCADE)
            "NONE": begin
                cas_en = 2'b00;
            end
            "LOWER": begin
                if (DATA_WIDTH_A != 1 || DATA_WIDTH_B != 1) begin
                    $display("ERROR: GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_A and DATA_WIDTH_B:%s,%s in CASCADING MODE:%s are illegal, then DATA_WIDTH_A and DATA_WIDTH_B have to be set to 1.",DATA_WIDTH_A,DATA_WIDTH_B,RAM_CASCADE);
                    $finish;
                end
                cas_en = 2'b01;
            end
            "UPPER": begin
                if (DATA_WIDTH_A != 1 || DATA_WIDTH_B != 1) begin
                    $display("ERROR: GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_A and DATA_WIDTH_B:%s,%s in CASCADING MODE:%s are illegal, then DATA_WIDTH_A and DATA_WIDTH_B have to be set to 1.",DATA_WIDTH_A,DATA_WIDTH_B,RAM_CASCADE);
                    $finish;
                end
                cas_en = 2'b11;
            end
            default: begin
                $display("ERROR: GTP_DRM36K_E1 instance %m parameter RAM_CASCADE: %s is illegal, the legal values are NONE,LOWER or UPPER", RAM_CASCADE);
                $finish;
            end
        endcase

        case (ECC_WRITE_EN)
            "FALSE": ecc_wren = 1'b0;
            "TRUE" : begin
                ecc_wren = 1'b1;
                if (DATA_WIDTH_A != 72 || DATA_WIDTH_B != 72) begin
                    $display("ERROR: ECCWR_ERROR GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_A and DATA_WIDTH_B:%s,%s in ECC MODE:%s are illegal, then DATA_WIDTH_A and DATA_WIDTH_B have to be set to 72.",DATA_WIDTH_A,DATA_WIDTH_B,ECC_WRITE_EN);
                    $finish;
                end
            end
            default: begin
                    $display("ERROR: ECCWR_ERROR GTP_DRM36K_E1 instance %m parameter ECC_WRITE_EN:%s is illegal, the lecal values are TRUE or FALSE.",ECC_WRITE_EN);
                    $finish;
            end
        endcase

        case (ECC_READ_EN)
            "FALSE": ecc_rden = 1'b0;
            "TRUE" : begin
                ecc_rden = 1'b1;
                if (DATA_WIDTH_A != 72 || DATA_WIDTH_B != 72) begin
                    $display("ERROR: ECCRD_ERROR GTP_DRM36K_E1 instance %m parameter DATA_WIDTH_A and DATA_WIDTH_B:%s,%s in ECC MODE:%s are illegal, then DATA_WIDTH_A and DATA_WIDTH_B have to be set to 72.",DATA_WIDTH_A,DATA_WIDTH_B,ECC_READ_EN);
                    $finish;
                end
            end
            default: begin
                    $display("ERROR: ECCRD_ERROR GTP_DRM36K_E1 instance %m parameter ECC_READ_EN:%s is illegal, the lecal values are TRUE or FALSE.",ECC_READ_EN);
                    $finish;
            end
        endcase
    end

/////////////////
// initialization
/////////////////

    initial begin
        if (INIT_FILE == "NONE") begin
            for (cnt = 0; cnt < 32; cnt = cnt + 1) begin
                mem[32*0 + cnt] = INIT_00[cnt*9 +: 9];
                mem[32*1 + cnt] = INIT_01[cnt*9 +: 9];
                mem[32*2 + cnt] = INIT_02[cnt*9 +: 9];
                mem[32*3 + cnt] = INIT_03[cnt*9 +: 9];
                mem[32*4 + cnt] = INIT_04[cnt*9 +: 9];
                mem[32*5 + cnt] = INIT_05[cnt*9 +: 9];
                mem[32*6 + cnt] = INIT_06[cnt*9 +: 9];
                mem[32*7 + cnt] = INIT_07[cnt*9 +: 9];
                mem[32*8 + cnt] = INIT_08[cnt*9 +: 9];
                mem[32*9 + cnt] = INIT_09[cnt*9 +: 9];
                mem[32*10 + cnt] = INIT_0A[cnt*9 +: 9];
                mem[32*11 + cnt] = INIT_0B[cnt*9 +: 9];
                mem[32*12 + cnt] = INIT_0C[cnt*9 +: 9];
                mem[32*13 + cnt] = INIT_0D[cnt*9 +: 9];
                mem[32*14 + cnt] = INIT_0E[cnt*9 +: 9];
                mem[32*15 + cnt] = INIT_0F[cnt*9 +: 9];
                mem[32*16 + cnt] = INIT_10[cnt*9 +: 9];
                mem[32*17 + cnt] = INIT_11[cnt*9 +: 9];
                mem[32*18 + cnt] = INIT_12[cnt*9 +: 9];
                mem[32*19 + cnt] = INIT_13[cnt*9 +: 9];
                mem[32*20 + cnt] = INIT_14[cnt*9 +: 9];
                mem[32*21 + cnt] = INIT_15[cnt*9 +: 9];
                mem[32*22 + cnt] = INIT_16[cnt*9 +: 9];
                mem[32*23 + cnt] = INIT_17[cnt*9 +: 9];
                mem[32*24 + cnt] = INIT_18[cnt*9 +: 9];
                mem[32*25 + cnt] = INIT_19[cnt*9 +: 9];
                mem[32*26 + cnt] = INIT_1A[cnt*9 +: 9];
                mem[32*27 + cnt] = INIT_1B[cnt*9 +: 9];
                mem[32*28 + cnt] = INIT_1C[cnt*9 +: 9];
                mem[32*29 + cnt] = INIT_1D[cnt*9 +: 9];
                mem[32*30 + cnt] = INIT_1E[cnt*9 +: 9];
                mem[32*31 + cnt] = INIT_1F[cnt*9 +: 9];
                mem[32*32 + cnt] = INIT_20[cnt*9 +: 9];
                mem[32*33 + cnt] = INIT_21[cnt*9 +: 9];
                mem[32*34 + cnt] = INIT_22[cnt*9 +: 9];
                mem[32*35 + cnt] = INIT_23[cnt*9 +: 9];
                mem[32*36 + cnt] = INIT_24[cnt*9 +: 9];
                mem[32*37 + cnt] = INIT_25[cnt*9 +: 9];
                mem[32*38 + cnt] = INIT_26[cnt*9 +: 9];
                mem[32*39 + cnt] = INIT_27[cnt*9 +: 9];
                mem[32*40 + cnt] = INIT_28[cnt*9 +: 9];
                mem[32*41 + cnt] = INIT_29[cnt*9 +: 9];
                mem[32*42 + cnt] = INIT_2A[cnt*9 +: 9];
                mem[32*43 + cnt] = INIT_2B[cnt*9 +: 9];
                mem[32*44 + cnt] = INIT_2C[cnt*9 +: 9];
                mem[32*45 + cnt] = INIT_2D[cnt*9 +: 9];
                mem[32*46 + cnt] = INIT_2E[cnt*9 +: 9];
                mem[32*47 + cnt] = INIT_2F[cnt*9 +: 9];
                mem[32*48 + cnt] = INIT_30[cnt*9 +: 9];
                mem[32*49 + cnt] = INIT_31[cnt*9 +: 9];
                mem[32*50 + cnt] = INIT_32[cnt*9 +: 9];
                mem[32*51 + cnt] = INIT_33[cnt*9 +: 9];
                mem[32*52 + cnt] = INIT_34[cnt*9 +: 9];
                mem[32*53 + cnt] = INIT_35[cnt*9 +: 9];
                mem[32*54 + cnt] = INIT_36[cnt*9 +: 9];
                mem[32*55 + cnt] = INIT_37[cnt*9 +: 9];
                mem[32*56 + cnt] = INIT_38[cnt*9 +: 9];
                mem[32*57 + cnt] = INIT_39[cnt*9 +: 9];
                mem[32*58 + cnt] = INIT_3A[cnt*9 +: 9];
                mem[32*59 + cnt] = INIT_3B[cnt*9 +: 9];
                mem[32*60 + cnt] = INIT_3C[cnt*9 +: 9];
                mem[32*61 + cnt] = INIT_3D[cnt*9 +: 9];
                mem[32*62 + cnt] = INIT_3E[cnt*9 +: 9];
                mem[32*63 + cnt] = INIT_3F[cnt*9 +: 9];
                mem[32*64 + cnt] = INIT_40[cnt*9 +: 9];
                mem[32*65 + cnt] = INIT_41[cnt*9 +: 9];
                mem[32*66 + cnt] = INIT_42[cnt*9 +: 9];
                mem[32*67 + cnt] = INIT_43[cnt*9 +: 9];
                mem[32*68 + cnt] = INIT_44[cnt*9 +: 9];
                mem[32*69 + cnt] = INIT_45[cnt*9 +: 9];
                mem[32*70 + cnt] = INIT_46[cnt*9 +: 9];
                mem[32*71 + cnt] = INIT_47[cnt*9 +: 9];
                mem[32*72 + cnt] = INIT_48[cnt*9 +: 9];
                mem[32*73 + cnt] = INIT_49[cnt*9 +: 9];
                mem[32*74 + cnt] = INIT_4A[cnt*9 +: 9];
                mem[32*75 + cnt] = INIT_4B[cnt*9 +: 9];
                mem[32*76 + cnt] = INIT_4C[cnt*9 +: 9];
                mem[32*77 + cnt] = INIT_4D[cnt*9 +: 9];
                mem[32*78 + cnt] = INIT_4E[cnt*9 +: 9];
                mem[32*79 + cnt] = INIT_4F[cnt*9 +: 9];
                mem[32*80 + cnt] = INIT_50[cnt*9 +: 9];
                mem[32*81 + cnt] = INIT_51[cnt*9 +: 9];
                mem[32*82 + cnt] = INIT_52[cnt*9 +: 9];
                mem[32*83 + cnt] = INIT_53[cnt*9 +: 9];
                mem[32*84 + cnt] = INIT_54[cnt*9 +: 9];
                mem[32*85 + cnt] = INIT_55[cnt*9 +: 9];
                mem[32*86 + cnt] = INIT_56[cnt*9 +: 9];
                mem[32*87 + cnt] = INIT_57[cnt*9 +: 9];
                mem[32*88 + cnt] = INIT_58[cnt*9 +: 9];
                mem[32*89 + cnt] = INIT_59[cnt*9 +: 9];
                mem[32*90 + cnt] = INIT_5A[cnt*9 +: 9];
                mem[32*91 + cnt] = INIT_5B[cnt*9 +: 9];
                mem[32*92 + cnt] = INIT_5C[cnt*9 +: 9];
                mem[32*93 + cnt] = INIT_5D[cnt*9 +: 9];
                mem[32*94 + cnt] = INIT_5E[cnt*9 +: 9];
                mem[32*95 + cnt] = INIT_5F[cnt*9 +: 9];
                mem[32*96 + cnt] = INIT_60[cnt*9 +: 9];
                mem[32*97 + cnt] = INIT_61[cnt*9 +: 9];
                mem[32*98 + cnt] = INIT_62[cnt*9 +: 9];
                mem[32*99 + cnt] = INIT_63[cnt*9 +: 9];
                mem[32*100 + cnt] = INIT_64[cnt*9 +: 9];
                mem[32*101 + cnt] = INIT_65[cnt*9 +: 9];
                mem[32*102 + cnt] = INIT_66[cnt*9 +: 9];
                mem[32*103 + cnt] = INIT_67[cnt*9 +: 9];
                mem[32*104 + cnt] = INIT_68[cnt*9 +: 9];
                mem[32*105 + cnt] = INIT_69[cnt*9 +: 9];
                mem[32*106 + cnt] = INIT_6A[cnt*9 +: 9];
                mem[32*107 + cnt] = INIT_6B[cnt*9 +: 9];
                mem[32*108 + cnt] = INIT_6C[cnt*9 +: 9];
                mem[32*109 + cnt] = INIT_6D[cnt*9 +: 9];
                mem[32*110 + cnt] = INIT_6E[cnt*9 +: 9];
                mem[32*111 + cnt] = INIT_6F[cnt*9 +: 9];
                mem[32*112 + cnt] = INIT_70[cnt*9 +: 9];
                mem[32*113 + cnt] = INIT_71[cnt*9 +: 9];
                mem[32*114 + cnt] = INIT_72[cnt*9 +: 9];
                mem[32*115 + cnt] = INIT_73[cnt*9 +: 9];
                mem[32*116 + cnt] = INIT_74[cnt*9 +: 9];
                mem[32*117 + cnt] = INIT_75[cnt*9 +: 9];
                mem[32*118 + cnt] = INIT_76[cnt*9 +: 9];
                mem[32*119 + cnt] = INIT_77[cnt*9 +: 9];
                mem[32*120 + cnt] = INIT_78[cnt*9 +: 9];
                mem[32*121 + cnt] = INIT_79[cnt*9 +: 9];
                mem[32*122 + cnt] = INIT_7A[cnt*9 +: 9];
                mem[32*123 + cnt] = INIT_7B[cnt*9 +: 9];
                mem[32*124 + cnt] = INIT_7C[cnt*9 +: 9];
                mem[32*125 + cnt] = INIT_7D[cnt*9 +: 9];
                mem[32*126 + cnt] = INIT_7E[cnt*9 +: 9];
                mem[32*127 + cnt] = INIT_7F[cnt*9 +: 9];
            end
        end
        else  begin      // INIT_FILE 
            case(DATA_WIDTH_A)
                1: begin  //DRM TYPE 32K*1
                   for(cnt=0; cnt<4*1024;cnt = cnt+1)
                       mem[cnt][7:0] = {ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8+7][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8+6][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8+5][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8+4][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8+3][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8+2][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8+1][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*8][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH]};
                end
                2: begin //DRM TYPE 16K*2
                   for(cnt=0; cnt<4*1024;cnt = cnt+1)
                       mem[cnt][7:0] = {ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*4+3][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*4+2][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*4+1][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                        ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*4][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH]};
                end
                4: begin //DRM TYPE 8K*4
                   for(cnt=0; cnt<4*1024;cnt = cnt+1)
                       {mem[cnt][7:0]} = {ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*2+1][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH],
                                          ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt*2][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH]};
                end
                8: begin //DRM TYPE 4K*8
                   for(cnt=0; cnt<4*1024;cnt = cnt+1)
                       mem[cnt][7:0] = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
                9: begin //DRM TYPE 4K*9
                   for(cnt=0; cnt<4*1024;cnt = cnt+1)
                       mem[cnt] = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
                16:begin //DRM TYPE 2k*16
                   for(cnt=0; cnt<2*1024;cnt = cnt+1)
                       {mem[cnt*2+1][7:0], mem[cnt*2][7:0]} = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
                18:begin //DRM TYPE 2k*18
                   for(cnt=0; cnt<2*1024;cnt = cnt+1)
                       {mem[cnt*2+1], mem[cnt*2]} = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
                32:begin //DRM TYPE 1k*32
                   for(cnt=0; cnt<1024;cnt = cnt+1)
                       {mem[cnt*4+3][7:0],mem[cnt*4+2][7:0],mem[cnt*4+1][7:0],mem[cnt*4][7:0]} = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
                36:begin //DRM TYPE 1k*36
                   for(cnt=0; cnt<1024;cnt = cnt+1)
                       {mem[cnt*4+3],mem[cnt*4+2],mem[cnt*4+1],mem[cnt*4]} = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
                64:begin //DRM TYPE 512*64
                   for(cnt=0; cnt<512;cnt = cnt+1)
                       {mem[cnt*8+7][7:0],mem[cnt*8+6][7:0],mem[cnt*8+5][7:0],mem[cnt*8+4][7:0],
                        mem[cnt*8+3][7:0],mem[cnt*8+2][7:0],mem[cnt*8+1][7:0],mem[cnt*8][7:0]} = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
                72:begin //DRM TYPE 512*72
                   for(cnt=0; cnt<512;cnt = cnt+1)
                       {mem[cnt*8+7],mem[cnt*8+6],mem[cnt*8+5],mem[cnt*8+4],
                        mem[cnt*8+3],mem[cnt*8+2],mem[cnt*8+1],mem[cnt*8]} = ini_mem[BLOCK_Y*BLOCK_DEPTH + cnt][BLOCK_X*BLOCK_WIDTH +:BLOCK_WIDTH];
                end
            endcase
        end
    end

    always @(*) begin
        DIB_int = ecc_wren ? {ecc_p_enc[7],DIB[34:27],ecc_p_enc[6],DIB[25:18],ecc_p_enc[5],DIB[16:9],ecc_p_enc[4],DIB[7:0]} : DIB;
        DIA_int = ecc_wren ? {ecc_p_enc[3],DIA[34:27],ecc_p_enc[2],DIA[25:18],ecc_p_enc[1],DIA[16:9],ecc_p_enc[0],DIA[7:0]} : DIA;
        if(ecc_wren && (INJECT_SBITERR || INJECT_DBITERR)) begin
            DIA_int[33] = ~ DIA_int[33];
        end
        if(ecc_wren && INJECT_DBITERR) begin
            DIB_int[33] = ~ DIB_int[33];
        end
    end

    always @(posedge CLKA) begin
        if (CEA) begin
            // high to hold the address
            if (ADDRA_HOLD == 1'b0) begin
                if(CSA == CSA_MASK) begin
                    ada_reg <= ADDRA;
                end
                csa_reg <= (CSA == CSA_MASK);
            end
            da_reg <= DIA_int;
            wea_reg <= WEA;
            bea_reg <= BWEA;
            ecc_p_reg <= ecc_p_enc;
        end
    end

    always @(posedge CLKB) begin
        if (CEB) begin
            // high to hold the address
            if (ADDRB_HOLD == 1'b0) begin
                if(CSB == CSB_MASK) begin
                   adb_reg <= ADDRB;
                end
                csb_reg <= (CSB == CSB_MASK);
            end
          //db_reg <= DIB_int;
            web_reg <= WEB;
            beb_reg <= BWEB;
        end
    end

    ///////////////////
    // task & function
    ///////////////////

    function [DATA_WIDTH_A-1:0] mem_read_a;
        input [14:0]  addr;
    begin
        case (DATA_WIDTH_A)
            1: mem_read_a = mem[addr[14:3]][addr[2:0]];
            2: mem_read_a = mem[addr[14:3]][addr[2:1]*2 +: 2];
            4: mem_read_a = mem[addr[14:3]][addr[2]*4 +: 4];
            8: mem_read_a = mem[addr[14:3]][7:0];
            9: mem_read_a = mem[addr[14:3]];
            16: mem_read_a = {mem[addr[14:4]*2+1][7:0], mem[addr[14:4]*2][7:0]};
            18: mem_read_a = {mem[addr[14:4]*2+1]     , mem[addr[14:4]*2]};
            32: mem_read_a = {mem[addr[14:5]*4+3][7:0], mem[addr[14:5]*4+2][7:0], mem[addr[14:5]*4+1][7:0], mem[addr[14:5]*4][7:0]};
            36: mem_read_a = {mem[addr[14:5]*4+3]     , mem[addr[14:5]*4+2]     , mem[addr[14:5]*4+1]     , mem[addr[14:5]*4]};
            default:      ;//null 
        endcase
    end
    endfunction

    function [DATA_WIDTH_B-1:0] mem_read_b;
        input [14:0]  addr;
    begin
        case (DATA_WIDTH_B)
            1: mem_read_b = mem[addr[14:3]][addr[2:0]];
            2: mem_read_b = mem[addr[14:3]][addr[2:1]*2 +: 2];
            4: mem_read_b = mem[addr[14:3]][addr[2]*4 +: 4];
            8: mem_read_b = mem[addr[14:3]][7:0];
            9: mem_read_b = mem[addr[14:3]];
            16: mem_read_b = {mem[addr[14:4]*2+1][7:0], mem[addr[14:4]*2][7:0]};
            18: mem_read_b = {mem[addr[14:4]*2+1]     , mem[addr[14:4]*2]};
            32: mem_read_b = {mem[addr[14:5]*4+3][7:0], mem[addr[14:5]*4+2][7:0], mem[addr[14:5]*4+1][7:0], mem[addr[14:5]*4][7:0]};
            36: mem_read_b = {mem[addr[14:5]*4+3]     , mem[addr[14:5]*4+2]     , mem[addr[14:5]*4+1]     , mem[addr[14:5]*4]};
            64: mem_read_b = {mem[addr[14:6]*8+7][7:0], mem[addr[14:6]*8+6][7:0], mem[addr[14:6]*8+5][7:0], mem[addr[14:6]*8+4][7:0],
                              mem[addr[14:6]*8+3][7:0], mem[addr[14:6]*8+2][7:0], mem[addr[14:6]*8+1][7:0], mem[addr[14:6]*8][7:0]};
            72: mem_read_b = {mem[addr[14:6]*8+7], mem[addr[14:6]*8+6], mem[addr[14:6]*8+5], mem[addr[14:6]*8+4],
                              mem[addr[14:6]*8+3], mem[addr[14:6]*8+2], mem[addr[14:6]*8+1], mem[addr[14:6]*8]};
            default:      ;//null 
        endcase
    end
    endfunction

    task mem_write_a;
        input [14:0] addr;
        input [71:0] data;
        input [7:0]  byte_en;
    begin
        case (DATA_WIDTH_A)
            1: mem[addr[14:3]][addr[2:0]] = data[0];
            2: mem[addr[14:3]][addr[2:1]*2 +: 2] = data[1:0];
            4: mem[addr[14:3]][addr[2]*4 +: 4] = data[3:0];
            8: mem[addr[14:3]][7:0] = data[7:0];
            9: mem[addr[14:3]] = data[8:0];
            16: begin
                if (byte_en[1])
                    mem[addr[14:4]*2+1][7:0] = data[16:9];
                if (byte_en[0])
                    mem[addr[14:4]*2][7:0]   = data[7:0];
            end
            18: begin
                if (byte_en[1])
                    mem[addr[14:4]*2+1] = data[17:9];
                if (byte_en[0])
                    mem[addr[14:4]*2]   = data[8:0];
            end
            32: begin
                if (byte_en[3])
                    mem[addr[14:5]*4+3][7:0] = data[34:27];
                if (byte_en[2])
                    mem[addr[14:5]*4+2][7:0] = data[25:18];
                if (byte_en[1])
                    mem[addr[14:5]*4+1][7:0] = data[16:9];
                if (byte_en[0])
                    mem[addr[14:5]*4][7:0]   = data[7:0];
            end
            36: begin
                if (byte_en[3])
                    mem[addr[14:5]*4+3] = data[35:27];
                if (byte_en[2])
                    mem[addr[14:5]*4+2] = data[26:18];
                if (byte_en[1])
                    mem[addr[14:5]*4+1] = data[17:9];
                if (byte_en[0])
                    mem[addr[14:5]*4]   = data[8:0];
            end
            64: begin
                if (byte_en[7])
                    mem[addr[14:6]*8+7][7:0] = data[70:63];
                if (byte_en[6])
                    mem[addr[14:6]*8+6][7:0] = data[61:54];
                if (byte_en[5])
                    mem[addr[14:6]*8+5][7:0] = data[52:45];
                if (byte_en[4])
                    mem[addr[14:6]*8+4][7:0] = data[43:36];
                if (byte_en[3])
                    mem[addr[14:6]*8+3][7:0] = data[34:27];
                if (byte_en[2])
                    mem[addr[14:6]*8+2][7:0] = data[25:18];
                if (byte_en[1])
                    mem[addr[14:6]*8+1][7:0] = data[16:9];
                if (byte_en[0])
                    mem[addr[14:6]*8][7:0]   = data[7:0];
            end
            72: begin
                if (byte_en[7])
                    mem[addr[14:6]*8+7] = data[71:63];
                if (byte_en[6])
                    mem[addr[14:6]*8+6] = data[62:54];
                if (byte_en[5])
                    mem[addr[14:6]*8+5] = data[53:45];
                if (byte_en[4])
                    mem[addr[14:6]*8+4] = data[44:36];
                if (byte_en[3])
                    mem[addr[14:6]*8+3] = data[35:27];
                if (byte_en[2])
                    mem[addr[14:6]*8+2] = data[26:18];
                if (byte_en[1])
                    mem[addr[14:6]*8+1] = data[17:9];
                if (byte_en[0])
                    mem[addr[14:6]*8]   = data[8:0];
            end
            default:     ;//null
        endcase
    end
    endtask

    task mem_write_b;
        input [14:0] addr;
        input [35:0] data;
        input [3:0]  byte_en;
    begin
        case (DATA_WIDTH_B)
            1: mem[addr[14:3]][addr[2:0]] = data[0];
            2: mem[addr[14:3]][addr[2:1]*2 +: 2] = data[1:0];
            4: mem[addr[14:3]][addr[2]*4 +: 4] = data[3:0];
            8: mem[addr[14:3]][7:0] = data[7:0];
            9: mem[addr[14:3]] = data[8:0];
            16: begin
                if (byte_en[1])
                    mem[addr[14:4]*2+1][7:0] = data[16:9];
                if (byte_en[0])
                    mem[addr[14:4]*2][7:0]   = data[7:0];
            end
            18: begin
                if (byte_en[1])
                    mem[addr[14:4]*2+1] = data[17:9];
                if (byte_en[0])
                    mem[addr[14:4]*2]   = data[8:0];
            end
            32: begin
                if (byte_en[3])
                    mem[addr[14:5]*4+3][7:0] = data[34:27];
                if (byte_en[2])
                    mem[addr[14:5]*4+2][7:0] = data[25:18];
                if (byte_en[1])
                    mem[addr[14:5]*4+1][7:0] = data[16:9];
                if (byte_en[0])
                    mem[addr[14:5]*4][7:0]   = data[7:0];
            end
            36: begin
                if (byte_en[3])
                    mem[addr[14:5]*4+3] = data[35:27];
                if (byte_en[2])
                    mem[addr[14:5]*4+2] = data[26:18];
                if (byte_en[1])
                    mem[addr[14:5]*4+1] = data[17:9];
                if (byte_en[0])
                    mem[addr[14:5]*4]   = data[8:0];
            end
            default:     ;//null
        endcase
    end
    endtask

    function [7:0] func_ecc;
        input [63:0] ecc_din;
    begin
        func_ecc[0] = ecc_din[0]^ecc_din[1]^ecc_din[3]^ecc_din[4]^ecc_din[6]^ecc_din[8]
                         ^ecc_din[10]^ecc_din[11]^ecc_din[13]^ecc_din[15]^ecc_din[17]^ecc_din[19]
                         ^ecc_din[21]^ecc_din[23]^ecc_din[25]^ecc_din[26]^ecc_din[28]^ecc_din[30]
                         ^ecc_din[32]^ecc_din[34]^ecc_din[36]^ecc_din[38]^ecc_din[40]^ecc_din[42]
                         ^ecc_din[44]^ecc_din[46]^ecc_din[48]^ecc_din[50]^ecc_din[52]^ecc_din[54]
                         ^ecc_din[56]^ecc_din[57]^ecc_din[59]^ecc_din[61]^ecc_din[63];
        func_ecc[1] = ecc_din[0]^ecc_din[2]^ecc_din[3]^ecc_din[5]^ecc_din[6]^ecc_din[9]
                         ^ecc_din[10]^ecc_din[12]^ecc_din[13]^ecc_din[16]^ecc_din[17]^ecc_din[20]
                         ^ecc_din[21]^ecc_din[24]^ecc_din[25]^ecc_din[27]^ecc_din[28]^ecc_din[31]
                         ^ecc_din[32]^ecc_din[35]^ecc_din[36]^ecc_din[39]^ecc_din[40]^ecc_din[43]
                         ^ecc_din[44]^ecc_din[47]^ecc_din[48]^ecc_din[51]^ecc_din[52]^ecc_din[55]
                         ^ecc_din[56]^ecc_din[58]^ecc_din[59]^ecc_din[62]^ecc_din[63];
        func_ecc[2] = ecc_din[1]^ecc_din[2]^ecc_din[3]^ecc_din[7]^ecc_din[8]^ecc_din[9]
                         ^ecc_din[10]^ecc_din[14]^ecc_din[15]^ecc_din[16]^ecc_din[17]^ecc_din[22]
                         ^ecc_din[23]^ecc_din[24]^ecc_din[25]^ecc_din[29]^ecc_din[30]^ecc_din[31]
                         ^ecc_din[32]^ecc_din[37]^ecc_din[38]^ecc_din[39]^ecc_din[40]^ecc_din[45]
                         ^ecc_din[46]^ecc_din[47]^ecc_din[48]^ecc_din[53]^ecc_din[54]^ecc_din[55]
                         ^ecc_din[56]^ecc_din[60]^ecc_din[61]^ecc_din[62]^ecc_din[63];
        func_ecc[3] = ecc_din[4]^ecc_din[5]^ecc_din[6]^ecc_din[7]^ecc_din[8]^ecc_din[9]
                         ^ecc_din[10]^ecc_din[18]^ecc_din[19]^ecc_din[20]^ecc_din[21]^ecc_din[22]
                         ^ecc_din[23]^ecc_din[24]^ecc_din[25]^ecc_din[33]^ecc_din[34]^ecc_din[35]
                         ^ecc_din[36]^ecc_din[37]^ecc_din[38]^ecc_din[39]^ecc_din[40]^ecc_din[49]
                         ^ecc_din[50]^ecc_din[51]^ecc_din[52]^ecc_din[53]^ecc_din[54]^ecc_din[55]^ecc_din[56];
        func_ecc[4] = ecc_din[11]^ecc_din[12]^ecc_din[13]^ecc_din[14]^ecc_din[15]^ecc_din[16]
                         ^ecc_din[17]^ecc_din[18]^ecc_din[19]^ecc_din[20]^ecc_din[21]^ecc_din[22]
                         ^ecc_din[23]^ecc_din[24]^ecc_din[25]^ecc_din[41]^ecc_din[42]^ecc_din[43]
                         ^ecc_din[44]^ecc_din[45]^ecc_din[46]^ecc_din[47]^ecc_din[48]^ecc_din[49]
                         ^ecc_din[50]^ecc_din[51]^ecc_din[52]^ecc_din[53]^ecc_din[54]^ecc_din[55]^ecc_din[56];
        func_ecc[5] = ecc_din[26]^ecc_din[27]^ecc_din[28]^ecc_din[29]^ecc_din[30]^ecc_din[31]
                         ^ecc_din[32]^ecc_din[33]^ecc_din[34]^ecc_din[35]^ecc_din[36]^ecc_din[37]
                         ^ecc_din[38]^ecc_din[39]^ecc_din[40]^ecc_din[41]^ecc_din[42]^ecc_din[43]
                         ^ecc_din[44]^ecc_din[45]^ecc_din[46]^ecc_din[47]^ecc_din[48]^ecc_din[49]
                         ^ecc_din[50]^ecc_din[51]^ecc_din[52]^ecc_din[53]^ecc_din[54]^ecc_din[55]^ecc_din[56];
        func_ecc[6] = ecc_din[57]^ecc_din[58]^ecc_din[59]^ecc_din[60]^ecc_din[61]^ecc_din[62]^ecc_din[63];
        
        func_ecc[7] = ecc_din[0]^ecc_din[1]^ecc_din[2]^ecc_din[4]^ecc_din[5]^ecc_din[7]
                         ^ecc_din[10]^ecc_din[11]^ecc_din[12]^ecc_din[14]^ecc_din[17]^ecc_din[18]
                         ^ecc_din[21]^ecc_din[23]^ecc_din[24]^ecc_din[26]^ecc_din[27]^ecc_din[29]
                         ^ecc_din[32]^ecc_din[33]^ecc_din[36]^ecc_din[38]^ecc_din[39]^ecc_din[41]
                         ^ecc_din[44]^ecc_din[46]^ecc_din[47]^ecc_din[50]^ecc_din[51]^ecc_din[53]
                         ^ecc_din[56]^ecc_din[57]^ecc_din[58]^ecc_din[60]^ecc_din[63];
    end
    endfunction

    ///////////////
    // memory core
    ///////////////
reg CLKA_active;
reg CLKB_active;
initial begin
  CLKA_active = 1'b0;
  CLKB_active = 1'b0;
end
always @(posedge CLKA) begin
   if (CEA) begin
      CLKA_active <= 1'b1;
      #0.2 CLKA_active = 1'b0;
   end
   else
      CLKA_active <= 1'b0;
end
always @(posedge CLKB) begin
   if (CEB) begin
      CLKB_active <= 1'b1;
      #0.2 CLKB_active = 1'b0;
   end
   else
      CLKB_active <= 1'b0;
end

////////////////////////////////////////////////////////////////////////////////////////////
assign cas_inta = cas_en[1] ? ~ada_reg[15] : ada_reg[15];
assign cas_intb = cas_en[1] ? ~adb_reg[15] : adb_reg[15];

always @(*) begin
    if(WRITE_MODE_A == "NORMAL_WRITE" && wea_reg == 1'b1 || ~csa_reg) begin
        cas_sela = cas_sela;
    end else begin
        cas_sela = cas_inta;
    end
end
always @(*) begin
    if(WRITE_MODE_B == "NORMAL_WRITE" && web_reg == 1'b1 || ~csb_reg) begin
        cas_selb = cas_selb;
    end else begin
        cas_selb = cas_intb;
    end
end

assign a_out_mux[0] = ((cas_sela == 1'b0) && cas_en == 2'b11) ? CINA : a_out[0];
assign a_out_mux[35:1] = a_out[35:1];
assign b_out_mux[0] = ((cas_selb == 1'b0) && cas_en == 2'b11) ? CINB : b_out[0];
assign b_out_mux[35:1] = b_out[35:1];

assign COUTA = a_out[0];
assign COUTB = b_out[0];

generate
////////////////////////////////////////////////////////////////////////////////////////////
// ROM or SINGLE_PORT 
////////////////////////////////////////////////////////////////////////////////////////////
if(RAM_MODE == "ROM" || RAM_MODE == "SINGLE_PORT") begin:ROMorSP_MODE

    always @(posedge CLKA) begin
        if (CEA)
            db_reg <= DIB_int;
    end

    if (DATA_WIDTH_A > 36 || DATA_WIDTH_B > 36) begin

        assign write_en_a = csa_reg && cas_inta && (wea_reg == 1'b1);
        assign read_en_b  = csb_reg && cas_intb && (web_reg == 1'b0);
        // Port A (wirte) operations
        always @(negedge CLKA_active)
        begin
            if (write_en_a) begin  // write
              mem_write_a(ada_reg[14:0], {db_reg[35:0], da_reg[35:0]}, bea_reg);
            end
        end
        // Port B (read) operations
        always @(negedge CLKB_active or posedge rstb_int)
        begin
            if (rstb_int)
               {b_out, a_out} = {rstb_val_int, rsta_val_int};
            else if(read_en_b)begin
              if(DATA_WIDTH_B == 64)begin
                  {b_out[34:27],b_out[25:18],b_out[16:9],b_out[7:0],a_out[34:27],a_out[25:18],a_out[16:9],a_out[7:0]} = mem_read_b(adb_reg[14:0]);
              end
              else begin
                  {b_out[35:0],a_out[35:0]} = mem_read_b(adb_reg[14:0]);
              end
            end
        end

    end
    else  begin   //x1 x2 x4 x8 x9 x16 x18 x32 x36

        assign write_en_a = csa_reg && cas_inta && (wea_reg == 1'b1);
        assign read_en_a  = csa_reg && cas_inta && (wea_reg == 1'b0);
        // Port A operations
        always @(negedge CLKA_active)
        begin
            if (write_en_a)  begin  // write
               // read during write
               if (WRITE_MODE_A == "TRANSPARENT_WRITE") begin
                   a_out[width_a-1:0] = mem_read_a(ada_reg);

                   if(DATA_WIDTH_A == 16) begin
                       if(bea_reg[0])
                           a_out[7:0] = da_reg[7:0];
                       else
                           a_out[7:0] = a_out[7:0];

                       if(bea_reg[1])
                           a_out[15:8] = da_reg[16:9];
                       else
                           a_out[15:8] = a_out[15:8];
                   end
                   else if(DATA_WIDTH_A == 18) begin
                        if(bea_reg[0])
                            a_out[8:0] = da_reg[8:0];
                        else
                            a_out[8:0] = a_out[8:0];

                        if(bea_reg[1])
                            a_out[17:9] = da_reg[17:9];
                        else
                            a_out[17:9] = a_out[17:9];
                   end
                   else if(DATA_WIDTH_A == 32) begin
                       if(bea_reg[0])
                           a_out[7:0] = da_reg[7:0];
                       else
                           a_out[7:0] = a_out[7:0];

                       if(bea_reg[1])
                           a_out[15:8] = da_reg[16:9];
                       else
                           a_out[15:8] = a_out[15:8];

                       if(bea_reg[2])
                           a_out[23:16] = da_reg[25:18];
                       else
                           a_out[23:16] = a_out[23:16];

                       if(bea_reg[3])
                           a_out[31:24] = da_reg[34:27];
                       else
                           a_out[31:24] = a_out[31:24];
                   end
                   else if(DATA_WIDTH_A == 36) begin
                        if(bea_reg[0])
                            a_out[8:0] = da_reg[8:0];
                        else
                            a_out[8:0] = a_out[8:0];

                        if(bea_reg[1])
                            a_out[17:9] = da_reg[17:9];
                        else
                            a_out[17:9] = a_out[17:9];

                        if(bea_reg[2])
                            a_out[26:18] = da_reg[26:18];
                        else
                            a_out[26:18] = a_out[26:18];

                        if(bea_reg[3])
                            a_out[35:27] = da_reg[35:27];
                        else
                            a_out[35:27] = a_out[35:27];
                   end
                   else begin
                        a_out[width_a-1:0] = da_reg[width_a-1:0];
                   end
               end
               else if (WRITE_MODE_A == "READ_BEFORE_WRITE")
                   a_out[width_a-1:0] = mem_read_a(ada_reg[14:0]);

               mem_write_a(ada_reg[14:0], {36'b0, da_reg}, bea_reg);
            end
        end

        always @(negedge CLKA_active or posedge rsta_int)
        begin
            if (rsta_int)
               a_out = rsta_val_int;
            else if (read_en_a)          // read 
               a_out[width_a-1:0] = mem_read_a(ada_reg[14:0]);
        end
    end
end
////////////////////////////////////////////////////////////////////////////////////////////
//SIMPLE_DUAL_PORT
////////////////////////////////////////////////////////////////////////////////////////////
else if(RAM_MODE == "SIMPLE_DUAL_PORT")begin:SDP_MODE
    //port_A operation: only write in SDP MODE
    if (DATA_WIDTH_A > 36) begin:PORTA

        assign write_en_a = csa_reg && cas_inta && (wea_reg == 1'b1);

        always @(posedge CLKA) begin
           if (CEA)
              db_reg  <= DIB_int;
        end
        always @(negedge CLKA_active) begin
           if (write_en_a)    // write 
              mem_write_a(ada_reg[14:0], {db_reg[35:0], da_reg[35:0]}, bea_reg);
        end
    end
    else  begin:PORTA    //  x1 x2 x4 x8 x9 x16 x18 x32 x36

        assign write_en_a = csa_reg && cas_inta && (wea_reg == 1'b1);
        assign read_en_a  = csa_reg && cas_inta && (wea_reg == 1'b0) ;

        always @(negedge CLKA_active) begin
           if (write_en_a)     // write
           begin
              mem_write_a(ada_reg[14:0], {36'b0, da_reg}, bea_reg);
           end
        end
        if(DATA_WIDTH_B <= 36) begin
           always @(negedge CLKA_active or posedge rsta_int)
           begin
               if (rsta_int)
                  a_out = rsta_val_int;
               else if (read_en_a)
                  a_out[width_a-1 : 0] = mem_read_a(ada_reg[14:0]);
           end
        end
    end
    //port_B operation:only read in SDP MODE
    if (DATA_WIDTH_B > 36) begin:PORTB
    // SIMPLE_DUAL_PORT 

        assign read_en_b  = csb_reg && cas_intb && (web_reg == 1'b0);

        always @(negedge CLKB_active or posedge rstb_int)
        begin
           if (rstb_int)
              {b_out, a_out} = {rstb_val_int, rsta_val_int};
           else if (read_en_b)       // read 
                if(DATA_WIDTH_B == 64)begin
                  {b_out[34:27],b_out[25:18],b_out[16:9],b_out[7:0],a_out[34:27],a_out[25:18],a_out[16:9],a_out[7:0]} = mem_read_b(adb_reg[14:0]);
              end
              else begin
                  {b_out[35:0],a_out[35:0]} = mem_read_b(adb_reg[14:0]);
              end
        end
    end
    else  begin:PORTB  //  x1 x2 x4 x8 x9  x16 x18 x32 x36

        assign read_en_b  = csb_reg && cas_intb && (web_reg == 1'b0);

        always @(negedge CLKB_active or posedge rstb_int)
        begin
           if (rstb_int)
              b_out = rstb_val_int;
           else if (read_en_b)   //  read 
              b_out[width_b-1 : 0] = mem_read_b(adb_reg[14:0]);
        end
    end
end
////////////////////////////////////////////////////////////////////////////////////////////
//DP_MODE
////////////////////////////////////////////////////////////////////////////////////////////
else   begin:DP_MODE   //  --x1 x2 x4 x8 x9 x16 x18 x32 x36
    assign write_en_a = csa_reg && cas_inta && (wea_reg == 1'b1) ;
    assign read_en_a  = csa_reg && cas_inta && (wea_reg == 1'b0) ;
    assign write_en_b = csb_reg && cas_intb && (web_reg == 1'b1) ;
    assign read_en_b  = csb_reg && cas_intb && (web_reg == 1'b0) ;
    // Port A operations
    always @(negedge CLKA_active)
    begin
        if (write_en_a)  begin  // write
            // read during write
            if (WRITE_MODE_A == "TRANSPARENT_WRITE")
            begin
               a_out[width_a-1:0] = mem_read_a(ada_reg);

               if(DATA_WIDTH_A == 16) begin
                   if(bea_reg[0])
                       a_out[7:0] = da_reg[7:0];
                   else
                       a_out[7:0] = a_out[7:0];

                   if(bea_reg[1])
                       a_out[15:8] = da_reg[16:9];
                   else
                       a_out[15:8] = a_out[15:8];
               end
               else if(DATA_WIDTH_A == 18) begin
                    if(bea_reg[0])
                        a_out[8:0] = da_reg[8:0];
                    else
                        a_out[8:0] = a_out[8:0];

                    if(bea_reg[1])
                        a_out[17:9] = da_reg[17:9];
                    else
                        a_out[17:9] = a_out[17:9];
               end
               else if(DATA_WIDTH_A == 32) begin
                   if(bea_reg[0])
                       a_out[7:0] = da_reg[7:0];
                   else
                       a_out[7:0] = a_out[7:0];

                   if(bea_reg[1])
                       a_out[15:8] = da_reg[16:9];
                   else
                       a_out[15:8] = a_out[15:8];

                   if(bea_reg[2])
                       a_out[23:16] = da_reg[25:18];
                   else
                       a_out[23:16] = a_out[23:16];

                   if(bea_reg[3])
                       a_out[31:24] = da_reg[34:27];
                   else
                       a_out[31:24] = a_out[31:24];
               end
               else if(DATA_WIDTH_A == 36) begin
                    if(bea_reg[0])
                        a_out[8:0] = da_reg[8:0];
                    else
                        a_out[8:0] = a_out[8:0];

                    if(bea_reg[1])
                        a_out[17:9] = da_reg[17:9];
                    else
                        a_out[17:9] = a_out[17:9];

                    if(bea_reg[2])
                        a_out[26:18] = da_reg[26:18];
                    else
                        a_out[26:18] = a_out[26:18];

                    if(bea_reg[3])
                        a_out[35:27] = da_reg[35:27];
                    else
                        a_out[35:27] = a_out[35:27];
               end
               else begin
                    a_out[width_a-1:0] = da_reg[width_a-1:0];
               end
            end
            else if (WRITE_MODE_A == "READ_BEFORE_WRITE")
               a_out[width_a-1:0] = mem_read_a(ada_reg[14:0]);

            mem_write_a(ada_reg[14:0], {36'b0, da_reg}, bea_reg);
        end
    end

    always @(negedge CLKA_active or posedge rsta_int)
    begin
        if (rsta_int)
           a_out = rsta_val_int;
        else if (read_en_a)
           a_out[width_a-1 : 0] = mem_read_a(ada_reg[14:0]);
    end
    // Port B operations
    always @(posedge CLKB) begin
         if (CEB)
            db_reg <= DIB_int;
    end

    always @(negedge CLKB_active)
    begin
        if (write_en_b)  begin  // write
            // read during write
            if (WRITE_MODE_B == "TRANSPARENT_WRITE")
            begin
                b_out[width_b-1:0] = mem_read_b(adb_reg);

                if(DATA_WIDTH_B == 16) begin
                    if(beb_reg[0])
                        b_out[7:0] = db_reg[7:0];
                    else
                        b_out[7:0] = b_out[7:0];

                    if(beb_reg[1])
                        b_out[15:8] = db_reg[16:9];
                    else
                        b_out[15:8] = b_out[15:8];
                end
                else if(DATA_WIDTH_B == 18) begin
                    if(beb_reg[0])
                        b_out[8:0] = db_reg[8:0];
                    else
                        b_out[8:0] = b_out[8:0];

                    if(beb_reg[1])
                        b_out[17:9] = db_reg[17:9];
                    else
                        b_out[17:9] = b_out[17:9];
                end
                else if(DATA_WIDTH_B == 32) begin
                    if(beb_reg[0])
                        b_out[7:0] = db_reg[7:0];
                    else
                        b_out[7:0] = b_out[7:0];

                    if(beb_reg[1])
                        b_out[15:8] = db_reg[16:9];
                    else
                        b_out[15:8] = b_out[15:8];

                    if(beb_reg[2])
                        b_out[23:16] = db_reg[25:18];
                    else
                        b_out[23:16] = b_out[23:16];

                    if(beb_reg[3])
                        b_out[31:24] = db_reg[34:27];
                    else
                        b_out[31:24] = b_out[31:24];
                end
                else if(DATA_WIDTH_B == 36) begin
                     if(beb_reg[0])
                         b_out[8:0] = db_reg[8:0];
                     else
                         b_out[8:0] = b_out[8:0];

                     if(beb_reg[1])
                         b_out[17:9] = db_reg[17:9];
                     else
                         b_out[17:9] = b_out[17:9];

                     if(beb_reg[2])
                         b_out[26:18] = db_reg[26:18];
                     else
                         b_out[26:18] = b_out[26:18];

                     if(beb_reg[3])
                         b_out[35:27] = db_reg[35:27];
                     else
                         b_out[35:27] = b_out[35:27];
                end
                else begin
                    b_out[width_b-1:0] = db_reg[width_b-1:0];
                end
            end
            else if (WRITE_MODE_B == "READ_BEFORE_WRITE")
                b_out[width_b-1:0] = mem_read_b(adb_reg[14:0]);

            mem_write_b(adb_reg[14:0], db_reg, beb_reg);
        end
    end

    always @(negedge CLKB_active or posedge rstb_int)
    begin
        if (rstb_int)
           b_out = rstb_val_int;
        else if (read_en_b)
           b_out[width_b-1 : 0] = mem_read_b(adb_reg[14:0]);
    end
end
////////////////////////////////////////////////////////////////////////////////////////////
endgenerate


//////////////
// core latch
//////////////
assign grsn =  (GRS_EN == "TRUE") ? GRS_INST.GRSNET : 1'b1;
assign grs =  ~grsn;
or (rsta_grs, grs, RSTA);
or (rstb_grs, grs, RSTB);

reg rsta_grsn_d;

    always @(posedge CLKA_for_or) begin
        if (RSTA) begin
            rsta_grsn_d   <= 1'b1;
        end
        else begin
            rsta_grsn_d   <= 1'b0;
        end
    end

reg rstb_grsn_d;
    
    always @(posedge CLKB_for_or) begin
        if (RSTB) begin
            rstb_grsn_d   <= 1'b1;
        end
        else begin
            rstb_grsn_d   <= 1'b0;
        end
    end

initial begin
    rsta_grsn_d = 1'b1;
    rstb_grsn_d = 1'b1;
end

assign rsta_grs_sync  = (RST_TYPE == "SYNC") ? rsta_grsn_d : 1'b0;
assign rstb_grs_sync  = (RST_TYPE == "SYNC") ? rstb_grsn_d : 1'b0;
assign rsta_grs_async = (RST_TYPE == "ASYNC") ? rsta_grs : grs;
assign rstb_grs_async = (RST_TYPE == "ASYNC") ? rstb_grs : grs;

assign rsta_int = rsta_grs_sync | rsta_grs_async;
assign rstb_int = rstb_grs_sync | rstb_grs_async;
/////////////////////////////////////////////////////////////////////
//port out
assign CLKA_for_or = (DOA_REG_CLKINV == 1) ? ~CLKA : CLKA;
assign CLKB_for_or = (DOB_REG_CLKINV == 1) ? ~CLKB : CLKB;


generate
////////////////////////////////////////////////////////////////////////////////////////////
assign ecc_d_in  = {DIB[34:27],DIB[25:18],DIB[16:9],DIB[7:0],DIA[34:27],DIA[25:18],DIA[16:9],DIA[7:0]};
assign ecc_p_enc = func_ecc (ecc_d_in);
assign ecc_d_dec = {b_out_mux[34:27],b_out_mux[25:18],b_out_mux[16:9],b_out_mux[7:0],a_out_mux[34:27],a_out_mux[25:18],a_out_mux[16:9],a_out_mux[7:0]};
assign ecc_p_out = {b_out_mux[35],b_out_mux[26],b_out_mux[17],b_out_mux[8],a_out_mux[35],a_out_mux[26],a_out_mux[17],a_out_mux[8]};
assign ecc_d_out = {b_out_mux[34:27],b_out_mux[25:18],b_out_mux[16:9],b_out_mux[7:0],a_out_mux[34:27],a_out_mux[25:18],a_out_mux[16:9],a_out_mux[7:0]};
assign ecc_p_dec = func_ecc (ecc_d_out) ^ ecc_p_out;

assign ecc_sbiterr_int = ^ecc_p_dec;
assign ecc_dbiterr_int = (|ecc_p_dec[6:0]) & ~ecc_sbiterr_int;
always @(*) begin
    ecc_corrected = {ecc_d_dec[63:57], ecc_p_out[6], ecc_d_dec[56:26], ecc_p_out[5], ecc_d_dec[25:11], ecc_p_out[4], ecc_d_dec[10:4], ecc_p_out[3], ecc_d_dec[3:1], ecc_p_out[2], ecc_d_dec[0], ecc_p_out[1:0], ecc_p_out[7]};
    ecc_corrected[ecc_p_dec[6:0]] = ecc_sbiterr_int ^ecc_corrected[ecc_p_dec[6:0]];
end
assign d_out_ecc = {ecc_corrected[0],ecc_corrected[71:65],ecc_corrected[63],ecc_corrected[64],ecc_corrected[62:55],ecc_corrected[32],ecc_corrected[54:47],ecc_corrected[16],ecc_corrected[46:39],ecc_corrected[8],ecc_corrected[38:33],ecc_corrected[31:30],ecc_corrected[4],ecc_corrected[29:22],ecc_corrected[2],ecc_corrected[21:17],ecc_corrected[15:13],ecc_corrected[1],ecc_corrected[12:9],ecc_corrected[7:5],ecc_corrected[3]};
////////////////////////////////////////////////////////////////////////////////////////////
if (DATA_WIDTH_B > 36)
begin:FAKE_DP_OUT
    //port_A output
    always @(posedge CLKB_for_or or posedge rstb_int)
    begin
        if (rstb_int) begin
            a_out_reg <= RSTA_VAL;
        end else if (ORCEB) begin
            a_out_reg <= ecc_rden ? d_out_ecc[35:0] : a_out;
        end
    end

    //doa combination logic
    always @(*)
    begin
        if (DOB_REG == 0)
        begin
            case(DATA_WIDTH_B)
                64: doa_mux = a_out_mux;
                72: doa_mux = ecc_rden ? d_out_ecc[35:0] : a_out_mux;
            endcase
        end
        else
        begin
            case(DATA_WIDTH_B)
                64: doa_mux = a_out_reg;
                72: doa_mux = a_out_reg;
            endcase
        end
    end

    always @(posedge CLKB_for_or or posedge rstb_int)
    begin
        if (rstb_int) begin
            b_out_reg <= RSTB_VAL;
            ecc_sbiterr_reg <= 1'b0;
            ecc_dbiterr_reg <= 1'b0;
            ecc_rdaddr_reg <= 9'h0;
        end else if (ORCEB) begin
            b_out_reg <= ecc_rden ? d_out_ecc[71:36] : b_out;
            ecc_sbiterr_reg <= ecc_sbiterr_int;
            ecc_dbiterr_reg <= ecc_dbiterr_int;
            ecc_rdaddr_reg <= adb_reg[14:6];
        end
    end

    //dob combination logic
    always @(*)
    begin
        if (DOB_REG == 0)
        begin
            case(DATA_WIDTH_B)
                64: dob_mux = b_out_mux;
                72: dob_mux = ecc_rden ? d_out_ecc[71:36] : b_out_mux;
            endcase
            ecc_sbiterr = ecc_sbiterr_int;
            ecc_dbiterr = ecc_dbiterr_int;
            ecc_rdaddr = adb_reg[14:6];
        end
        else
        begin
            case(DATA_WIDTH_B)
                64: dob_mux = b_out_reg;
                72: dob_mux = b_out_reg;
            endcase
            ecc_sbiterr = ecc_sbiterr_reg;
            ecc_dbiterr = ecc_dbiterr_reg;
            ecc_rdaddr = ecc_rdaddr_reg;
        end
    end
end
////////////////////////////////////////////////////////////////////////////////////////////
else
begin:TRUE_DP_OUT
    //port_A output

    always @(posedge CLKA_for_or or posedge RSTA)
    begin
        if (RSTA)
            doa_reg_as <= RSTA_VAL;
        else if (ORCEA)
            doa_reg_as <= doa;
    end

    always @(posedge CLKA_for_or)
    begin
        if (RSTA)
            doa_reg_s <= RSTA_VAL;
        else if (ORCEA)
            doa_reg_s <= doa;
    end

assign doa_reg = (RST_TYPE == "SYNC") ? doa_reg_s:doa_reg_as;

    //doa combination logic
    always @(a_out_mux)
    begin
       case(DATA_WIDTH_A)
          1: {doa[16:9],doa[7:0]} = {16{a_out_mux[width_a-1:0]}};
          2: {doa[16:9],doa[7:0]} = { 8{a_out_mux[width_a-1:0]}};
          4: {doa[16:9],doa[7:0]} = { 4{a_out_mux[width_a-1:0]}};
          8: {doa[16:9],doa[7:0]} = { 2{a_out_mux[width_a-1:0]}};
          9: {doa[17:9],doa[8:0]} = { 2{a_out_mux[width_a-1:0]}};
          16:{doa[16:9],doa[7:0]} =     a_out_mux[width_a-1:0]  ;
          18: doa[17:0]           =     a_out_mux[width_a-1:0]  ;
          32:{doa[34:27],doa[25:18],doa[16:9],doa[7:0]} = a_out_mux[width_a-1:0]  ;
          36: doa = a_out_mux;
       endcase
    end

    always @(doa or doa_reg)
    begin
        if (DOA_REG == 0)
            doa_mux = doa;
        else
            doa_mux = doa_reg;
    end

    //port_B output

    always @(posedge CLKB_for_or or posedge RSTB)
    begin
        if (RSTB)
            dob_reg_as <= RSTB_VAL;
        else if (ORCEB)
            dob_reg_as <= dob;
    end

    always @(posedge CLKB_for_or)
    begin
        if (RSTB)
            dob_reg_s <= RSTB_VAL;
        else if (ORCEB)
            dob_reg_s <= dob;
    end
assign dob_reg = (RST_TYPE == "SYNC") ? dob_reg_s:dob_reg_as;

    //dob combination logic
    always @(b_out_mux)
    begin
        case(DATA_WIDTH_B)  
           1: {dob[16:9],dob[7:0]} = {16{b_out_mux[width_b-1:0]}};
           2: {dob[16:9],dob[7:0]} = { 8{b_out_mux[width_b-1:0]}};
           4: {dob[16:9],dob[7:0]} = { 4{b_out_mux[width_b-1:0]}};
           8: {dob[16:9],dob[7:0]} = { 2{b_out_mux[width_b-1:0]}};
           9: {dob[17:9],dob[8:0]} = { 2{b_out_mux[width_b-1:0]}};
           16:{dob[16:9],dob[7:0]} =     b_out_mux[width_b-1:0]  ;
           18: dob[17:0]           =     b_out_mux[width_b-1:0]  ;
           32:{dob[34:27],dob[25:18],dob[16:9],dob[7:0]} = b_out_mux[width_b-1:0]  ;
           36: dob = b_out_mux;
        endcase
    end

    always @(dob or dob_reg)
    begin
        if (DOB_REG == 0)
            dob_mux = dob;
        else
            dob_mux = dob_reg;
    end

end
////////////////////////////////////////////////////////////////////////////////////////////
endgenerate

assign DOA = doa_mux;
assign DOB = dob_mux;
assign ECC_PARITY = ecc_p_reg;
assign ECC_RDADDR = ecc_rdaddr;
assign ECC_SBITERR = ecc_sbiterr;
assign ECC_DBITERR = ecc_dbiterr;
// synthesis translate_on
endmodule

