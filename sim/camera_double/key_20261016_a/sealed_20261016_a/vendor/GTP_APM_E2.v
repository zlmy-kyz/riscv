//////////////////////////////////////////////////////////////////////////////
//
// Copyright (c) 2016 PANGO MICROSYSTEMS, INC
// ALL RIGHTS RESERVED.
//
// THE SOURCE CODE CONTAINED HEREIN IS PROPRIETARY TO PANGO MICROSYSTEMS, INC.
// IT SHALL NOT BE REPRODUCED OR DISCLOSED IN WHOLE OR IN PART OR USED BY
// PARTIES WITHOUT WRITTEN AUTHORIZATION FROM THE OWNER.
//
//////////////////////////////////////////////////////////////////////////////
//
// Date(08/02/2019) Author:dfpu
//
// GTP model of APML device
//
// History:
//      initial version 
//
//////////////////////////////////////////////////////////////////////////////
`timescale 1ns/1ps

`define assert(condition, message) \
        if (!(condition)) begin \
            $display($realtime, "ERROR: ASSERTION FAILED in %s, line %d: %s", `__FILE__, `__LINE__, message); \
            $finish; \
        end
// module declaration
module GTP_APM_E2 #(

    parameter GRS_EN = "TRUE",  //"TRUE","FALSE",enable global reset
    parameter USE_POSTADD = 0, //enable postadder 0/1
    parameter USE_PREADD = 0,  //enable preadder 0/1
    parameter PREADD_REG = 0,  //preadder reg 0/1

    parameter X_REG = 0,  //X input reg 0/1/2/3
    parameter CXO_REG = 0, //X cascade out reg latency, 0/1/2/3
    parameter XB_REG = 0,  //XB input reg 0/1
    parameter Y_REG = 0,  //Y input reg 0/1/2/3
    parameter Z_REG = 0,  //Z input reg 0/1
    parameter MULT_REG = 0,  //multiplier reg 0/1
    parameter P_REG = 0,  //post adder reg 0/1
    parameter MODEY_REG = 0,  //MODEY reg
    parameter MODEZ_REG = 0,  //MODEZ reg
    parameter MODEIN_REG = 0,  //MODEZ reg
    parameter USE_MULT = 1,  //enable mult 1/0

    parameter X_SEL = 0,  // mult X input select X/CXI
    parameter XB_SEL = 0, //X back propagate mux select. 0/1/2/3
    parameter ASYNC_RST = 0,  // RST is sync/async
    parameter USE_SIMD = 0,   // single addsub25_mult25_add48 / dual addsub12_mult12_add24
    parameter [47:0] P_INIT0 = {48{1'b0}},  //P constant input0 (RTI parameter in APM of PG family)
    parameter [47:0] P_INIT1 = {48{1'b0}},  //P constant input1 (RTI parameter in APM of PG family)
    parameter ROUNDMODE_SEL = 0,  //round mode selection

    parameter CPO_REG = 0, // CPO,COUT use register output
    parameter USE_ACCLOW = 0, // accumulator use lower 18-bit feedback only
    parameter CIN_SEL = 0 // select CIN for postadder carry in

)(
    output [47:0] P,
    output [47:0] CPO, //p cascade output
    output COUT,
    output [29:0] CXO, //x cascade output
    output [24:0] CXBO, //x backward cascade output

    input [29:0] X,
    input [29:0] CXI, //x cascade input
    input [24:0] CXBI, //x backward cascade input
    input [24:0] XB, //x backward cascade input
    input [17:0] Y,
    input [47:0] Z,
    input [47:0] CPI, //p cascade input
    input CIN,
    input [2:0] MODEY,
    input [3:0] MODEZ,
    input [4:0] MODEIN,

    input CLK,

    input  CEX1,  //X1 enable signals 
    input  CEX2,  //X2 enable signals 
    input  CEX3,  //X3 enable signals 
    input  CEXB,  //XB enable signals 
    input  CEY1,  //Y1 enable signals 
    input  CEY2,  //Y2 enable signals 
    input  CEZ,  //Z enable signals 
    input  CEPRE,  //PRE enable signals 
    input  CEM,  //M enable signals 
    input  CEP,  //P enable signals 
    input  CEMODEY,  //MODEY enable signals 
    input  CEMODEZ,  //MODEZ enable signals 
    input  CEMODEIN,  //MODEIN enable signals 

    input  RSTX, //X reset signals 
    input  RSTXB, //XB reset signals 
    input  RSTY, //Y reset signals 
    input  RSTZ, //Z reset signals 
    input  RSTPRE, //PRE reset signals 
    input  RSTM, //M reset signals 
    input  RSTP, //P reset signals 
    input  RSTMODEY, //MODEY reset signals 
    input  RSTMODEZ, //MODEZ reset signals 
    input  RSTMODEIN //MODEIN reset signals 

);

    wire grs;
    assign grs = (GRS_EN == "TRUE") ? !GRS_INST.GRSNET : 1'b0;

//rst selection

    assign arst_x = (ASYNC_RST == 1'b1) ? (RSTX | grs) : grs;
    assign arst_xb = (ASYNC_RST == 1'b1) ? (RSTXB | grs) : grs;
    assign arst_y = (ASYNC_RST == 1'b1) ? (RSTY | grs) : grs;
    assign arst_z = (ASYNC_RST == 1'b1) ? (RSTZ | grs) : grs;
    assign arst_pre = (ASYNC_RST == 1'b1) ? (RSTPRE | grs) : grs;
    assign arst_m = (ASYNC_RST == 1'b1) ? (RSTM | grs) : grs;
    assign arst_p = (ASYNC_RST == 1'b1) ? (RSTP | grs) : grs;
    assign arst_modey = (ASYNC_RST == 1'b1) ? (RSTMODEY | grs) : grs;
    assign arst_modez = (ASYNC_RST == 1'b1) ? (RSTMODEZ | grs) : grs;
    assign arst_modein = (ASYNC_RST == 1'b1) ? (RSTMODEIN | grs) : grs;

    assign srst_x = (ASYNC_RST == 1'b1) ? 1'b0 : RSTX;
    assign srst_xb = (ASYNC_RST == 1'b1) ? 1'b0 : RSTXB;
    assign srst_y = (ASYNC_RST == 1'b1) ? 1'b0 : RSTY;
    assign srst_z = (ASYNC_RST == 1'b1) ? 1'b0 : RSTZ;
    assign srst_pre = (ASYNC_RST == 1'b1) ? 1'b0 : RSTPRE;
    assign srst_m = (ASYNC_RST == 1'b1) ? 1'b0 : RSTM;
    assign srst_p = (ASYNC_RST == 1'b1) ? 1'b0 : RSTP;
    assign srst_modey = (ASYNC_RST == 1'b1) ? 1'b0 : RSTMODEY;
    assign srst_modez = (ASYNC_RST == 1'b1) ? 1'b0 : RSTMODEZ;
    assign srst_modein = (ASYNC_RST == 1'b1) ? 1'b0 : RSTMODEIN;
    // input registers

    wire [29:0] xsel_out;
    reg [29:0] x1,x2,x3; // x register latency 
    reg [29:0] sh_xo;
    //x cascade output bus
    assign xsel_out = X_SEL ? CXI[29:0] : X[29:0];
    always @(posedge CLK or posedge arst_x) 
    begin
        if (arst_x) begin
            x1 <= 30'b0;
        end else if (srst_x) begin
            x1 <= 30'b0;
        end else if (CEX1) begin
            x1 <= xsel_out;
            end
    end

    always @(posedge CLK or posedge arst_x) 
    begin
        if (arst_x ) begin
            x2 <= 30'b0;
        end else if (srst_x) begin
            x2 <= 30'b0;
        end else if (CEX2) begin
            x2 <= x1;
            end
    end

    always @(posedge CLK or posedge arst_x) 
    begin
        if (arst_x ) begin
            x3 <= 30'b0;
        end else if (srst_x) begin
            x3 <= 30'b0;
        end else if (CEX3) begin
            x3 <= x2;
            end
    end

    always @ (*) begin
        case(CXO_REG[1:0])
            2'b00 : sh_xo = xsel_out;
            2'b01 : sh_xo = x1;
            2'b10 : sh_xo = x2;
            2'b11 : sh_xo = x3;
        endcase
    end

    assign CXO = sh_xo;

    wire [29:0] xir_out0,xir_out1; //registered (optional) x internal bus
    wire [29:0] x_post;
    wire [24:0] xir_out2,xir_out3;
    wire [4:0] modeini; //registered (optional) INMODE internal
    assign xir_out0 = X_REG[0] ? x1 : xsel_out; 
    assign xir_out1 = X_REG[1] ? x2 : xir_out0; 
    assign x_post = xir_out1;
    assign xir_out2 = modeini[0] ? x1[24:0] : xir_out1[24:0];
    assign xir_out3 = modeini[1] ? xir_out2 : 25'b0; 

    wire [24:0] xbi; //registered (optional) xb internal
    reg [24:0] xbr;
    wire [24:0] xb_in;
    assign xb_in = XB_SEL[0] ? CXBI[24:0] : XB[24:0];
    always @(posedge CLK or posedge arst_xb)
    begin
        if (arst_xb) begin
            xbr[24:0] <= 25'b0;
        end else if (srst_xb) begin
            xbr[24:0] <= 25'b0;
        end else if (CEXB) begin
            xbr[24:0] <= xb_in;
            end
    end

    assign xbi[24:0] = (XB_REG == 1) ? xbr : xb_in;


    reg [17:0] yi; //registered (optional) y internal
    reg [17:0] yr1,yr2;
    always @(posedge CLK or posedge arst_y)
    begin
        if (arst_y) begin
            yr1[17:0] <= 18'b0;
        end else if (srst_y) begin
            yr1[17:0] <= 18'b0;
        end else if (CEY1) begin
            yr1[17:0] <= Y;
            end
    end

    always @(posedge CLK or posedge arst_y)
    begin
        if (arst_y) begin
            yr2[17:0] <= 18'b0;
        end else if (srst_y) begin
            yr2[17:0] <= 18'b0;
        end else if (CEY2) begin
            yr2[17:0] <= yr1;
            end
    end

    always @ (*) begin
        case(Y_REG[1:0])
            2'b00 : yi = Y;
            2'b01 : yi = yr1;
            2'b10 : yi = yr1;
            2'b11 : yi = yr2;
        endcase
    end

    wire [17:0] y_post;
    assign y_post = yi;
    wire [17:0] yi_out;
    assign yi_out = modeini[4] ? yr1 : yi; 

    wire [47:0] zi; //registered (optional) z internal
    reg [47:0] zr;
    always @(posedge CLK or posedge arst_z)
    begin
        if (arst_z) begin
            zr[47:0] <= 48'b0;
        end else if (srst_z) begin
            zr[47:0] <= 48'b0;
        end else if (CEZ) begin
            zr[47:0] <= Z;
            end
    end
    
    assign zi = (Z_REG == 1'b1) ? zr : Z;

    wire [2:0] modeyi; //registered (optional) MODEY internal
    wire [3:0] modezi; //registered (optional) MODEZ internal
    reg [2:0] modeyr; //registered (optional) MODEY internal
    reg [3:0] modezr; //registered (optional) MODEZ internal
    
    always @(posedge CLK or posedge arst_modey)
    begin
        if (arst_modey) begin
            modeyr[2:0] <= 3'b0;
        end else if (srst_modey) begin
            modeyr[2:0] <= 3'b0;
        end else if (CEMODEY) begin
            modeyr[2:0] <= MODEY;
            end
    end
    
    assign modeyi = (MODEY_REG == 1'b1) ? modeyr : MODEY;

    always @(posedge CLK or posedge arst_modez)
    begin
        if (arst_modez) begin
            modezr[3:0] <= 4'b0;
        end else if (srst_modez) begin
            modezr[3:0] <= 4'b0;
        end else if (CEMODEZ) begin
            modezr[3:0] <= MODEZ;
            end
    end
    
    assign modezi = (MODEZ_REG == 1'b1) ? modezr : MODEZ;

    reg [4:0] modeinr;
    always @(posedge CLK or posedge arst_modein)
    begin
        if (arst_modein) begin
            modeinr[4:0] <= 5'b0;
        end else if (srst_modein) begin
            modeinr[4:0] <= 5'b0;
        end else if (CEMODEIN) begin
            modeinr[4:0] <= MODEIN;
            end
    end

    assign modeini = (MODEIN_REG == 1'b1) ? modeinr : MODEIN;

    //preadder

    reg [24:0] xbv;
    always @ (*) begin
        case(XB_SEL[1])
            1'b0 : xbv = xbi;
            1'b1 : xbv = sh_xo[24:0];
        endcase
    end

    assign CXBO = xbv;

    wire [24:0] prec; //cominational preadder output
    wire [24:0] pre_a,pre_b;
    wire preadd_sub;
    wire [24:0] preadd_s;
    wire [11:0] preadd_s_h,preadd_s_l;

    assign pre_a = xir_out3;
    assign pre_b = modeini[2] ? xbv: 25'b0;
    assign preadd_sub = modeini[3];
    assign preadd_s = preadd_sub ? pre_a - pre_b : pre_a + pre_b;
    assign preadd_s_l = preadd_sub ? pre_a[11:0] - pre_b[11:0] : pre_a[11:0] + pre_b[11:0];
    assign preadd_s_h = preadd_sub ? pre_a[23:12] - pre_b[23:12] : pre_a[23:12] + pre_b[23:12];
    assign prec = (USE_SIMD == 1'b1) ? {preadd_s_h[11],preadd_s_h,preadd_s_l} : preadd_s;
    
    reg [24:0] prer;
    always @(posedge CLK or posedge arst_pre)
    begin
        if (arst_pre) begin
            prer[24:0] <= 25'b0;
        end else if (srst_pre) begin
            prer[24:0] <= 25'b0;
        end else if (CEPRE) begin
            prer[24:0] <= prec;
            end
    end

    wire [24:0] prei; //registered (optional) preadder output
    assign prei = (PREADD_REG == 1'b1) ? prer : prec;

    // multiplier
    wire [47:0] mc; //mult combinational output
    wire [24:0] mult_ina;
    wire [17:0] mult_inb;
    wire [47:0] mult_out_s;
    wire [23:0] mult_out_h, mult_out_l;
    assign mult_ina[24:0] = USE_MULT ? (USE_PREADD ? prei[24:0] : xir_out3[24:0] ) : 25'b0;
    assign mult_inb[17:0] = USE_MULT ? yi_out[17:0] : 18'b0;

    assign mult_out_s = {{23{mult_ina[24]}},mult_ina} * {{30{mult_inb[17]}},mult_inb};
    assign mult_out_l = {{12{mult_ina[11]}},mult_ina[11:0]} * {{15{mult_inb[8]}},mult_inb[8:0]};
    assign mult_out_h = {{12{mult_ina[23]}},mult_ina[23:12]} * {{15{mult_inb[17]}},mult_inb[17:9]};

    assign mc = (USE_SIMD == 1'b1) ? {mult_out_h,mult_out_l}: mult_out_s;

    wire [47:0] mi; //registered (optional) mult internal output
    reg [47:0] mr;
    always @(posedge CLK or posedge arst_m)
    begin
        if (arst_m) begin
            mr[47:0] <= 48'b0;
        end else if (srst_m) begin
            mr[47:0] <= 48'b0;
        end else if (CEM) begin
            mr[47:0] <= mc;
            end
    end

    assign mi = (MULT_REG == 1'b1) ? mr : mc;

    //post adder
    reg  [47:0] pyi; // post adder input a before inverter
    wire [47:0] py = modeyi[2] ? ~pyi : pyi; // post adder input a after inverter
    reg  [47:0] pzi; // post adder input b before inverter
    wire [47:0] pz = modezi[3] ? ~pzi : pzi; // post adder input b after inverter

    reg [48:0] pr; // post adder regstered feedback
    wire [47:0] pri =  USE_ACCLOW ? { {31{1'b0}}, pr[16:0] } : pr[47:0];//post adder lower portion feedback

    always @ (*) begin
        case(modeyi[1:0])
            2'b00 : pyi = 48'b0;
            2'b01 : pyi = mi;
            2'b10 : pyi = pri;
            2'b11 : pyi = {x_post[29:0],y_post[17:0]};
        endcase
    end

    always @(*) begin
        case(modezi[2:0])
            3'b000 : pzi = 48'b0;
            3'b001 : pzi = pri;
            3'b010 : pzi = zi;
            3'b011 : pzi = $signed(CPI); //both branch need $signed
            3'b100 : pzi = $signed(CPI) >>> 17; //both branch need $signed
            3'b101 : pzi = $signed(CPI) >>> 24; //both branch need $signed
            3'b110 : pzi = $signed(CPI) >>> 16; //both branch need $signed
            3'b111 : pzi = $signed(CPI) >>> 8; //both branch need $signed
        endcase
    end

    wire cinv;
    assign cinv = CIN_SEL ? CIN : modeyi[2] | modezi[3];

    wire [48:0] pc;
    wire [47:0] alu_out;
    wire cout_inter0;
    wire cout_inter1;
    wire cin_inter;
    wire [47:0] c_inter;
    wire post_select;

    assign post_select = ((modeyi[1:0] == 2'b00) && (modezi[2:0] == 3'b000));
    assign {cout_inter0,alu_out[23:0]} = py[23:0] + pz[23:0] + cinv;
    assign cin_inter = USE_SIMD ? cinv : cout_inter0;
    assign {cout_inter1,alu_out[47:24]} = py[47:24] + pz[47:24] + cin_inter;
    assign c_inter = (ROUNDMODE_SEL ? alu_out[47] : (post_select ? 1'b1 : 1'b0)) ? P_INIT1 : P_INIT0;
    assign pc = {cout_inter1,alu_out[47:0]} + c_inter[47:0] ;



    wire [47:0] pi;
    always @(posedge CLK or posedge arst_p)
    begin
        if (arst_p) begin
            pr[48:0] <= 49'b0;
        end else if (srst_p) begin
            pr[48:0] <= 49'b0;
        end else if (CEP) begin
            pr[48:0] <= pc[48:0];
            end
    end

    assign pi = (P_REG == 1'b1) ? pr[47:0] : pc[47:0];

    assign P = USE_POSTADD ? pi : mi;
    assign CPO = USE_POSTADD ? (CPO_REG ? pr[47:0] : pc[47:0]) : mi;

    assign COUT = CPO_REG ? pr[48] : pc[48];
// DRC check
// pragma translate_off
    initial begin
        `assert(X_REG <= 3, "X_REG <= 3")
        `assert(CXO_REG <= 3, "CXO_REG <= 3")
        `assert(XB_REG <= 1, "XB_REG <= 1")
        `assert(Y_REG <= 3, "Y_REG <= 3")
        `assert(Z_REG <= 1, "Z_REG <= 1")
        `assert(MULT_REG <= 1, "MULT_REG <= 1")
        `assert(P_REG <= 1, "P_REG <= 1")
        `assert(PREADD_REG <= 1, "PREADD_REG <= 1")
        `assert(MODEY_REG <= 1, "MODEY_REG <= 1")
        `assert(MODEZ_REG <= 1, "MODEZ_REG <= 1")
        `assert(MODEIN_REG <= 1, "MODEIN_REG <= 1")
    end
// pragma translate_on
    

endmodule

