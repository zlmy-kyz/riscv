
//////////////////////////////////////////////////////////////////////////////
//
// Copyright (c) 2019 PANGO MICROSYSTEMS, INC
// ALL RIGHTS REVERVED.
//
// THE SOURCE CODE CONTAINED HEREIN IS PROPRIETARY TO PANGO MICROSYSTEMS, INC.
// IT SHALL NOT BE REPRODUCED OR DISCLOSED IN WHOLE OR IN PART OR USED BY
// PARTIES WITHOUT WRITTEN AUTHORIZATION FROM THE OWNER.
//
//////////////////////////////////////////////////////////////////////////////
// Library:
// Filename:data_ram.v
//////////////////////////////////////////////////////////////////////////////

module data_ram (
    addr        ,
    wr_data     ,
    rd_data     ,
    wr_en       ,
    clk         ,
    
    wr_byte_en  ,
    
    rst
);


localparam CAS_MODE = "36K" ; // @IPC enum 18K,36K,64K

localparam POWER_OPT = 0 ; // @IPC bool

localparam WRITE_MODE = "NORMAL_WRITE"; // @IPC enum NORMAL_WRITE,TRANSPARENT_WRITE,READ_BEFORE_WRITE

localparam WR_BYTE_EN = 1 ; // @IPC bool

localparam BYTE_SIZE = 8 ; // @IPC enum 8,9

localparam ADDR_WIDTH = 10 ; // @IPC int 9,20

localparam DATA_WIDTH = 32 ; // @IPC int 1,1152

localparam BE_WIDTH = 4 ; // @IPC int 1,128

localparam CLK_EN  = 0 ; // @IPC bool

localparam ADDR_STROBE_EN  = 0 ; // @IPC bool

localparam RD_OCE_EN = 0 ; // @IPC bool

localparam OUTPUT_REG = 0 ; // @IPC bool

localparam CLK_OR_POL_INV = 0 ; // @IPC bool

localparam FAB_REG = 0 ; // @IPC bool

localparam RESET_TYPE = "SYNC" ; // @IPC enum SYNC,ASYNC

localparam INIT_EN = 1 ; // @IPC bool

localparam INIT_FILE = "D:/riscv/tbtb/ram_test.dat" ; // @IPC string

localparam INIT_FORMAT = "HEX" ; // @IPC enum BIN,HEX

localparam RST_VAL_EN = 0 ; // @IPC bool


input  [ADDR_WIDTH-1 : 0]   addr        ;
input  [DATA_WIDTH-1 : 0]   wr_data     ;
output [DATA_WIDTH-1 : 0]   rd_data     ;
input                       wr_en       ;
input                       clk         ;

input  [BE_WIDTH-1 : 0]     wr_byte_en  ;

input                       rst         ;

wire [ADDR_WIDTH-1 : 0]     addr        ;
wire [DATA_WIDTH-1 : 0]     wr_data     ;
wire [DATA_WIDTH-1 : 0]     rd_data     ;
wire                        wr_en       ;
wire                        clk         ;
wire                        clk_en      ;
wire                        addr_strobe ;
wire                        rst         ;
wire [BE_WIDTH-1 : 0]       wr_byte_en  ;
wire                        rd_oce      ;

wire [BE_WIDTH-1 : 0]       wr_byte_en_mux  ;
wire                        rd_oce_mux2d    ;
wire                        rd_oce_mux2f    ;
wire                        clk_en_mux      ;
wire                        addr_strobe_mux ;

wire [DATA_WIDTH-1 : 0]     rd_data_d;
reg  [DATA_WIDTH-1 : 0]     fab_reg_invt;
reg  [DATA_WIDTH-1 : 0]     fab_reg;


assign wr_byte_en_mux   = (WR_BYTE_EN     == 1) ? wr_byte_en  : -1  ;
assign rd_oce_mux2d     = ((FAB_REG       == 1) && (OUTPUT_REG == 1)) ? 1 :
                           (OUTPUT_REG    == 1) ? ((RD_OCE_EN  == 1)  ? rd_oce : 1'b1) : 1'b0 ;
assign rd_oce_mux2f     =  (FAB_REG       == 1) ? ((RD_OCE_EN  == 1)  ? rd_oce : 1'b1) : 1'b0 ;
assign clk_en_mux       = (CLK_EN         == 1) ? clk_en      : 1'b1 ;
assign addr_strobe_mux  = (ADDR_STROBE_EN == 1) ? addr_strobe : 1'b0 ;

//ipm2l_sdpram IP instance
ipm2l_spram_v1_8_data_ram #(
    .c_CAS_MODE         (CAS_MODE               ),
    .c_ADDR_WIDTH       (ADDR_WIDTH             ),
    .c_DATA_WIDTH       (DATA_WIDTH             ),
    .c_OUTPUT_REG       (OUTPUT_REG             ),
    .c_RD_OCE_EN        (RD_OCE_EN              ),
    .c_FAB_REG          (FAB_REG                ),
    .c_CLK_EN           (CLK_EN                 ),
    .c_ADDR_STROBE_EN   (ADDR_STROBE_EN         ),
    .c_RESET_TYPE       (RESET_TYPE             ),
    .c_POWER_OPT        (POWER_OPT              ),
    .c_CLK_OR_POL_INV   (CLK_OR_POL_INV         ),
    .c_INIT_FILE        ("NONE"                 ),
    .c_INIT_FORMAT      (INIT_FORMAT            ),
    .c_WR_BYTE_EN       (WR_BYTE_EN             ),
    .c_BE_WIDTH         (BE_WIDTH               ),
    .c_WRITE_MODE       (WRITE_MODE             )
) U_ipml_spram_data_ram (
    .addr               ( addr                  ),
    .wr_data            ( wr_data               ),
    
    .rd_data            ( rd_data               ),
    
    .wr_en              ( wr_en                 ),
    .clk                ( clk                   ),
    .clk_en             ( clk_en_mux            ),
    .addr_strobe        ( addr_strobe_mux       ),
    .rst                ( rst                   ),
    .wr_byte_en         ( wr_byte_en_mux        ),
    .rd_oce             ( rd_oce_mux2d          )
);


generate
    if (FAB_REG == 1) begin

        assign rd_data = (FAB_REG == 1) ? ((CLK_OR_POL_INV == 1) ? fab_reg_invt : fab_reg) : rd_data_d ;
        if (CLK_OR_POL_INV == 1) begin
            always @(negedge clk or posedge rst) begin
                if (rst)
                    fab_reg_invt      <= {DATA_WIDTH{1'b0}};
                else if (rd_oce_mux2f)
                    fab_reg_invt      <= rd_data_d;
            end
        end
        else begin
            always @(posedge clk or posedge rst) begin
                if (rst)
                    fab_reg           <= {DATA_WIDTH{1'b0}};
                else if (rd_oce_mux2f)
                    fab_reg           <= rd_data_d;
            end
        end
    end
endgenerate

endmodule
