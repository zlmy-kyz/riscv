`timescale 1ns/1ps
// Functional Pango x32 user-port model for the Task043 SoC integration fragment.
// Byte backing store, 32-byte beats, controller address unit = 4 bytes.
// The camera/PP apertures live far outside the small backing store, so their
// lines are aliased into a reserved area; that is a property of this model, not
// of the DUT.
module wb2_ddr_model(
    input  wire        clk,
    input  wire        resetn,
    input  wire        init_done,
    input  wire [27:0] awaddr,
    input  wire        awvalid,
    output wire        awready,
    input  wire [255:0] wdata,
    input  wire [31:0] wstrb,
    output wire        wready,
    input  wire [27:0] araddr,
    input  wire [3:0]  aruser_id,
    input  wire        arvalid,
    output wire        arready,
    output wire [255:0] rdata,
    output wire        rvalid,
    output wire [3:0]  rid,
    output wire        rlast,
    output reg         writing
);
    // 0x3000 beats so the reserved camera/PP alias area (0x2000/0x2040) is in
    // range; the real backing store only needs the first 2 KiB.
    localparam integer NBEAT = 12'h3000;
    reg [255:0] beats [0:NBEAT-1];
    // Static staging image: xsim 2019.2 aborts at time 0 when $readmemh targets
    // an array declared inside an automatic task, so the buffer lives here.
    reg [31:0] img [0:2047];

    integer aw_block = 2, w_lat = 6, ar_block = 1, r_lat = 3;
    integer aw_wait = 0, ar_wait = 0, w_wait = 0, r_wait = 0;
    reg     reading = 0;
    reg [27:0] ra = 0, wa = 0;
    reg [255:0] rdata_q = 0;
    reg        rv_q = 0;
    reg [3:0]  rid_q = 0;
    reg [255:0] held_wdata = 0;
    reg [31:0] held_wstrb = 0;
    integer i, k, cam_reads = 0, pp_reads = 0;

    // Local byte address of a controller address (one unit = 4 bytes).
    function automatic [31:0] byte_of(input [27:0] ctrl);
        byte_of = {4'b0, ctrl} * 4;
    endfunction

    function automatic integer beat_of(input [27:0] ctrl);
        reg [31:0] b;
        begin
            b = byte_of(ctrl);
            if (b[31:22] == 10'h004)          // camera local 0x0100_0000
                beat_of = 32'h2000 + ((b[10:5]) & 32'h1f);
            else if (b[31:22] == 10'h008)     // PP local 0x0200_0000
                beat_of = 32'h2040 + ((b[10:5]) & 32'h1f);
            else
                beat_of = b >> 5;
        end
    endfunction

    assign awready = resetn && init_done && awvalid && !writing && (aw_wait >= aw_block);
    assign wready  = resetn && init_done && (writing && w_wait == 0);
    assign arready = resetn && init_done && arvalid && !reading && (ar_wait >= ar_block);
    assign rvalid  = rv_q;
    assign rlast   = rv_q;
    assign rid     = rid_q;
    assign rdata   = rdata_q;

    task automatic dump(input string path);
        integer fd, n;
        begin
            fd = $fopen(path, "w");
            if (!fd) $fatal(1, "RESULT: FAIL cannot open memory dump");
            for (n = 0; n < 256; n = n + 1)
                $fdisplay(fd, "P %0d %064h", n, beats[n]);
            $fclose(fd);
        end
    endtask

    task automatic preload_hex(input string path);
        integer w, b, fd;
        begin
            fd = $fopen(path, "r");
            if (!fd) $fatal(1, "RESULT: FAIL cannot open program image %s", path);
            $fclose(fd);
            for (w = 0; w < 2048; w = w + 1) img[w] = 32'h0;
            $readmemh(path, img);
            for (w = 0; w < 512; w = w + 1) begin
                b = w * 4;
                beats[b >> 5][(b & 31) * 8 +: 32] = img[w];
            end
        end
    endtask

    initial begin
        for (i = 0; i < NBEAT; i = i + 1)
            for (k = 0; k < 32; k = k + 1)
                beats[i][k*8 +: 8] = (i * 29 + k * 7 + 3) & 8'hff;
        // Known camera/PP pattern: one word per line, rest from the formula.
        beats[32'h2000][31:0] = 32'hC0DE_0001;
        beats[32'h2040][31:0] = 32'hB0B0_0001;
        rv_q = 0;
    end

    always @(posedge clk) begin
        rv_q <= 1'b0;
        if (!resetn) begin
            writing <= 0; reading <= 0;
            aw_wait <= 0; ar_wait <= 0; w_wait <= 0; r_wait <= 0;
            rdata_q <= 0; rid_q <= 0;
            cam_reads = 0; pp_reads = 0;
        end else if (init_done) begin
            if (awvalid && !awready) aw_wait <= aw_wait + 1;
            if (awvalid && awready) begin
                if (awaddr[2:0] != 3'b0)
                    $fatal(1, "RESULT: FAIL native AW alignment %h", awaddr);
                wa <= awaddr;
                held_wdata <= wdata;
                held_wstrb <= wstrb;
                aw_wait <= 0;
                writing <= 1;
                w_wait <= w_lat;
            end
            if (writing) begin
                if (w_wait > 0) w_wait <= w_wait - 1;
                else if (wready) begin
                    for (k = 0; k < 32; k = k + 1)
                        if (held_wstrb[k])
                            beats[beat_of(wa)][k*8 +: 8] <= held_wdata[k*8 +: 8];
                    writing <= 0;
                end
            end
            if (arvalid && !arready) ar_wait <= ar_wait + 1;
            if (arvalid && arready) begin
                if (araddr[2:0] != 3'b0)
                    $fatal(1, "RESULT: FAIL native AR alignment %h", araddr);
                ra <= araddr;
                rid_q <= aruser_id;
                ar_wait <= 0;
                reading <= 1;
                r_wait <= r_lat;
            end else if (reading) begin
                if (r_wait > 0) r_wait <= r_wait - 1;
                else begin
                    reading <= 0;
                    rdata_q <= beats[beat_of(ra)];
                    rv_q <= 1'b1;
                    // The camera/PP model changes content after the first read so a
                    // cached copy would be visibly stale on the second read.
                    if (beat_of(ra) == 32'h2000) begin
                        cam_reads = cam_reads + 1;
                        beats[32'h2000][31:0] <= 32'hC0DE_0002;
                    end
                    if (beat_of(ra) == 32'h2040) begin
                        pp_reads = pp_reads + 1;
                        beats[32'h2040][31:0] <= 32'hB0B0_0002;
                    end
                end
            end
        end
    end
endmodule
