// Pango-specific single-beat user-port model with independent AW/AR/W/R delays.
// No PHY/DDR training. Full boot starts poisoned; only ROM CPU stores load code.
module coremark_ddr_model #(parameter integer PRELOAD=0)(
    input clk,resetn,input [27:0] awaddr,araddr,input awvalid,arvalid,
    output awready,arready,wready,input [127:0] wdata,input [15:0] wstrb,
    output reg [127:0] rdata=0,output reg rvalid=0);
    reg [127:0] beats[0:4095];
    reg [31:0] image[0:4095];
    reg writing=0,reading=0;
    reg [27:0] wa,ra;
    integer aw_wait=0,ar_wait=0,w_wait=0,r_wait=0,i,lane;
    string dat_path;
    assign awready=awvalid && !writing && aw_wait>=2;
    assign arready=arvalid && !reading && ar_wait>=3;
    assign wready=writing && w_wait==0;
    function [31:0] word_at;
        input [31:0] address;
        reg [31:0] offset;
        begin offset=address-32'h40000000; word_at=beats[offset[15:4]][offset[3:2]*32+:32]; end
    endfunction
    initial begin
        if(!$value$plusargs("DAT=%s",dat_path)) $fatal(1,"RESULT: FAIL missing DAT");
        $readmemh(dat_path,image);
        for(i=0;i<4096;i=i+1) beats[i]={4{32'ha5a5a5a5}};
        if(PRELOAD) for(i=0;i<image[4092];i=i+1) beats[i/4][(i%4)*32+:32]=image[i];
    end
    always @(posedge clk) begin
        rvalid<=0;
        if(resetn) begin
            if(awvalid && !awready) aw_wait<=aw_wait+1;
            if(arvalid && !arready) ar_wait<=ar_wait+1;
            if(awvalid && awready) begin
                if(awaddr[27:15]!=0) $fatal(1,"RESULT: FAIL DDR write alias");
                wa<=awaddr; writing<=1; w_wait<=4; aw_wait<=0;
            end
            if(writing && w_wait>0) w_wait<=w_wait-1;
            if(wready) begin
                for(lane=0;lane<16;lane=lane+1)
                    if(wstrb[lane]) beats[wa[14:3]][lane*8+:8]<=wdata[lane*8+:8];
                writing<=0;
            end
            if(arvalid && arready) begin
                if(araddr[27:15]!=0) $fatal(1,"RESULT: FAIL DDR read alias");
                ra<=araddr; reading<=1; r_wait<=5; ar_wait<=0;
            end
            if(reading && r_wait>0) r_wait<=r_wait-1;
            if(reading && r_wait==0) begin rdata<=beats[ra[14:3]];rvalid<=1;reading<=0;end
        end
    end
endmodule
