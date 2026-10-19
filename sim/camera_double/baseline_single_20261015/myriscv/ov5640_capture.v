`timescale 1ns/1ps
// All DVP signals are synchronous to PCLK. First byte is RGB565[15:8].
// A frame is accepted only from a VSYNC falling edge to the next rising edge.
module ov5640_capture #(
    parameter integer WIDTH=1280, HEIGHT=720, DROP_FRAMES=10
) (
    input wire pclk, resetn, run,
    input wire vsync, href,
    input wire [7:0] din,
    input wire fifo_full,
    output wire fifo_write,
    output wire [15:0] fifo_data,
    output reg done, overflow, format_error,
    output wire [31:0] frame_crc32
);
    (* async_reg="true" *) reg [1:0] run_sync;
    // Register the complete source-synchronous bus together. This removes the
    // half-cycle external DVP -> 16-bit CRC path without changing pixel order.
    (* syn_preserve=1 *) reg [7:0] din_q;
    (* syn_preserve=1 *) reg vsync_q, href_q;
    always @(posedge pclk or negedge resetn) begin
        if (!resetn) begin din_q<=0; vsync_q<=1; href_q<=0; end
        else begin din_q<=din; vsync_q<=vsync; href_q<=href; end
    end
    reg old_vs, old_href, active, started;
    reg [7:0] dropped;
    reg [12:0] line_bytes;
    reg [10:0] lines;
    reg [7:0] high_byte;
    reg [31:0] crc;
    // Reflected IEEE CRC32, initial FFFFFFFF, final complement. Memory stores
    // each RGB565 pixel low byte first, although DVP transmits its high byte first.
    function [31:0] crc_pixel;
        input [31:0] previous;
        input [15:0] pixel;
        reg [31:0] c;
        integer bitn;
        begin
            c=previous ^ {16'b0,pixel};
            for (bitn=0;bitn<16;bitn=bitn+1)
                c=c[0] ? (c>>1)^32'hedb88320 : c>>1;
            crc_pixel=c;
        end
    endfunction
    assign frame_crc32=~crc;
    wire frame_start=old_vs && !vsync_q;
    wire frame_end=!old_vs && vsync_q;
    wire line_end=old_href && !href_q;
    assign fifo_write=active && run_sync[1] && !done && !overflow && !format_error &&
                      !vsync_q && href_q && line_bytes[0] && line_bytes<WIDTH*2 &&
                      lines<HEIGHT && !fifo_full;
    assign fifo_data={high_byte,din_q};
    always @(posedge pclk or negedge resetn) begin
        if (!resetn) begin
            run_sync<=0; old_vs<=1; old_href<=0; active<=0; started<=0;
            dropped<=0; line_bytes<=0; lines<=0; high_byte<=0;
            done<=0; overflow<=0; format_error<=0; crc<=32'hffffffff;
        end else begin
            run_sync<={run_sync[0],run}; old_vs<=vsync_q; old_href<=href_q;
            if (fifo_write) crc<=crc_pixel(crc,fifo_data);
            if (!run_sync[1]) active<=0;
            else if (!started) begin
                if (frame_start) begin
                    if (dropped<DROP_FRAMES) dropped<=dropped+1'b1;
                    else begin
                        started<=1; active<=1; line_bytes<=0; lines<=0;
                        if (href_q) begin active<=0; format_error<=1; end
                    end
                end
            end else if (active) begin
                if (href_q && !vsync_q) begin
                    if (line_bytes>=WIDTH*2 || lines>=HEIGHT) begin
                        format_error<=1; active<=0;
                    end else begin
                        line_bytes<=line_bytes+1'b1;
                        if (!line_bytes[0]) high_byte<=din_q;
                        else if (fifo_full) begin overflow<=1; active<=0; end
                    end
                end
                if (line_end) begin
                    if (line_bytes!=WIDTH*2 || lines>=HEIGHT) begin format_error<=1; active<=0; end
                    else begin lines<=lines+1'b1; line_bytes<=0; end
                end
                if (frame_end) begin
                    active<=0;
                    // Last HREF falling and VSYNC rising may share an edge.
                    if (!href_q && ((line_end && line_bytes==WIDTH*2 && lines==HEIGHT-1) ||
                                  (!line_end && line_bytes==0 && lines==HEIGHT))) done<=1;
                    else format_error<=1;
                end
            end
        end
    end
endmodule
