`timescale 1ns/1ps
// Pango single-beat user port: no WVALID/B/RREADY. Memory is poisoned once,
// never preloaded with the expected pattern and retained across SoC reset.
module loader_ddr_model(
    input clk,resetn,enabled,inject_fault,
    input [27:0] awaddr,araddr,input awvalid,arvalid,
    input [127:0] wdata,input [15:0] wstrb,
    output awready,wready,arready,rvalid,output [127:0] rdata);
    reg [127:0] beats[0:4095];
    reg writing=0,reading=0,fault_used=0;
    reg [27:0] wa,ra;
    reg [127:0] held_data;
    reg [15:0] held_strobe;
    integer aw_wait=0,ar_wait=0,w_wait=0,r_wait=0;
    integer writes=0,reads=0,i,lane;
    wire immediate_write=awvalid && awready && writes%2==0;
    wire immediate_read=arvalid && arready && reads%2==0 && !(inject_fault && !fault_used);
    assign awready=enabled && awvalid && !writing && aw_wait>=1+writes%3;
    assign arready=enabled && arvalid && !reading && ar_wait>=2+reads%3;
    assign wready=enabled && ((writing && w_wait==0) || immediate_write);
    assign rvalid=enabled && (immediate_read || (reading && r_wait==0));
    assign rdata=reading ? beats[ra[14:3]] : beats[araddr[14:3]];
    function [31:0] word_at;
        input [31:0] address;
        reg [31:0] offset;
        begin offset=address-32'h40000000; word_at=beats[offset[15:4]][offset[3:2]*32+:32]; end
    endfunction
    initial for(i=0;i<4096;i=i+1) beats[i]={4{32'ha5a5a5a5}};
    always @(posedge clk) begin
        if(!resetn) begin
            writing<=0;reading<=0;fault_used<=0;
            aw_wait<=0;ar_wait<=0;w_wait<=0;r_wait<=0;
        end else if(enabled) begin
            if(!inject_fault) fault_used<=0;
            if(awvalid && !awready) aw_wait<=aw_wait+1;
            if(arvalid && !arready) ar_wait<=ar_wait+1;
            if(awvalid && awready) begin
                if(awaddr[27:15]!=0 || awaddr[2:0]!=0)
                    $fatal(1,"RESULT: FAIL DDR model AW alias/alignment");
                wa<=awaddr;held_data<=wdata;held_strobe<=wstrb;aw_wait<=0;
                if(immediate_write) begin
                    for(lane=0;lane<16;lane=lane+1)
                        if(wstrb[lane]) beats[awaddr[14:3]][lane*8+:8]<=wdata[lane*8+:8];
                    writes<=writes+1;
                end else begin writing<=1;w_wait<=2+writes%4;end
            end
            if(writing) begin
                if(wdata!==held_data || wstrb!==held_strobe)
                    $fatal(1,"RESULT: FAIL DDR model W not held stable");
                if(w_wait>0) w_wait<=w_wait-1;
                if(wready) begin
                    for(lane=0;lane<16;lane=lane+1)
                        if(wstrb[lane]) beats[wa[14:3]][lane*8+:8]<=wdata[lane*8+:8];
                    writing<=0;writes<=writes+1;
                end
            end
            if(arvalid && arready) begin
                if(araddr[27:15]!=0 || araddr[2:0]!=0)
                    $fatal(1,"RESULT: FAIL DDR model AR alias/alignment");
                ra<=araddr;ar_wait<=0;reads<=reads+1;
                if(inject_fault && !fault_used) begin
                    // Physical DDR byte 26 is changed after writes, before readback.
                    beats[1][80+:8]<=beats[1][80+:8]^8'h01;fault_used<=1;
                end
                if(!immediate_read) begin reading<=1;r_wait<=3+reads%4;end
            end
            if(reading) begin
                if(r_wait>0) r_wait<=r_wait-1;
                else reading<=0;
            end
        end
    end
endmodule
