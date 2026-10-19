`timescale 1ns/1ps

// 256-bit, single-beat Pango user-port model. Address units are 32-bit words.
// Application bytes are preloaded only for this direct DDR execution test.
module mini_ddr_model_x32(
    input clk, resetn,
    input [27:0] awaddr, araddr,
    input awvalid, arvalid,
    output awready, arready, wready,
    input [255:0] wdata,
    input [31:0] wstrb,
    output reg [255:0] rdata=0,
    output reg rvalid=0
);
    reg [255:0] beats[0:2047];
    reg [31:0] image[0:4095];
    reg writing=0, reading=0;
    reg [27:0] wa, ra;
    integer aw_wait=0, ar_wait=0, w_wait=0, r_wait=0;
    integer i, lane;
    string path;
    assign awready=awvalid && !writing && aw_wait>=2;
    assign arready=arvalid && !reading && ar_wait>=3;
    assign wready=writing && w_wait==0;

    initial begin
        if (!$value$plusargs("DAT=%s",path)) $fatal(1,"RESULT: FAIL missing DAT");
        $readmemh(path,image);
        for (i=0;i<2048;i=i+1) beats[i]={8{32'ha5a5a5a5}};
        for (i=0;i<image[4092];i=i+1)
            beats[i/8][(i%8)*32+:32]=image[i];
    end

    always @(posedge clk) begin
        rvalid<=0;
        if (!resetn) begin
            writing<=0; reading<=0;
            aw_wait<=0; ar_wait<=0; w_wait<=0; r_wait<=0;
        end else begin
            if (awvalid && !awready) aw_wait<=aw_wait+1;
            if (arvalid && !arready) ar_wait<=ar_wait+1;
            if (awvalid && awready) begin
                if (awaddr[27:14]!=0 || awaddr[2:0]!=0)
                    $fatal(1,"RESULT: FAIL x32 DDR write alias/alignment %h",awaddr);
                wa<=awaddr; writing<=1; w_wait<=4; aw_wait<=0;
            end
            if (writing && w_wait>0) w_wait<=w_wait-1;
            if (wready) begin
                for (lane=0;lane<32;lane=lane+1)
                    if (wstrb[lane]) beats[wa[13:3]][lane*8+:8]<=wdata[lane*8+:8];
                writing<=0;
            end
            if (arvalid && arready) begin
                if (araddr[27:14]!=0 || araddr[2:0]!=0)
                    $fatal(1,"RESULT: FAIL x32 DDR read alias/alignment %h",araddr);
                ra<=araddr; reading<=1; r_wait<=5; ar_wait<=0;
            end
            if (reading && r_wait>0) r_wait<=r_wait-1;
            if (reading && r_wait==0) begin
                rdata<=beats[ra[13:3]]; rvalid<=1; reading<=0;
            end
        end
    end
endmodule
