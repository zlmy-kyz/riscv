`timescale 1ns/1ps
// Task033 completion job. Functional Pango x32 user-port model, frozen copy of
// the original model with a distinct module name so both harnesses stay
// independent. Byte backing store; 32-byte beats; CTRL address unit is 4 bytes.
// Camera-local 0x01xxxxxx and PP-local 0x02xxxxxx windows are carried in a small
// alias area because this task only touches a few lines there.
module completion_ddr_model(
    input  wire clk,
    input  wire resetn,
    input  wire init_done,
    output wire awready,
    input  wire [27:0] awaddr,
    input  wire awvalid,
    input  wire [255:0] wdata,
    input  wire [31:0] wstrb,
    output wire wready,
    output wire arready,
    input  wire [27:0] araddr,
    input  wire [3:0] aruser_id,
    input  wire arvalid,
    output wire [255:0] rdata,
    output wire rvalid,
    output wire [3:0] rid,
    output wire rlast
);
    localparam integer NBEAT = 8256;
    reg [255:0] beats [0:NBEAT-1];

    reg        reading = 0;
    reg        writing = 0;
    reg [27:0] ra = 0, wa = 0;
    reg [255:0] rdata_q = 0;
    reg        rv_q = 0;
    reg [3:0]  rid_q = 0;
    reg [255:0] held_wdata = 0;
    reg [31:0] held_wstrb = 0;
    reg [3:0]  held_rid = 0;
    integer    ar_wait = 0, aw_wait = 0, r_wait = 0, w_wait = 0;
    integer    i, k;
    integer    ar_count = 0, r_count = 0, aw_count = 0, w_count = 0;
    reg [31:0] seed = 32'd1;

    // Knobs driven by the testbench sequence.
    integer ar_block = 0;
    integer r_lat = 2;
    integer aw_block = 0;
    integer w_lat = 1;
    integer r_hold = 0;
    integer instant_r = 0;
    integer instant_w = 0;

    function automatic integer beat_index(input [27:0] a);
        reg [31:0] b;
        begin
            b = {4'b0, a} * 4;
            if (b[31:22] == 10'h004)
                beat_index = 32'h2000 + ((b[10:5]) & 32'h1f);
            else if (b[31:22] == 10'h008)
                beat_index = 32'h2020 + ((b[10:5]) & 32'h1f);
            else
                beat_index = b >> 5;
        end
    endfunction

    assign arready = init_done && arvalid && !reading &&
                     (instant_r != 0 || (ar_wait >= ar_block));
    assign awready = init_done && awvalid && !writing && (aw_wait >= aw_block);
    assign wready  = init_done && ((writing && w_wait == 0) ||
                                  (instant_w && awvalid && awready));

    wire comb_r = (instant_r == 2) && arvalid && arready;
    assign rvalid = rv_q || comb_r;
    assign rlast  = rvalid;
    assign rid    = comb_r ? aruser_id : rid_q;
    assign rdata  = comb_r ? beats[beat_index(araddr)] : rdata_q;

    initial begin
        // Deterministic LCG image; the Python reference replays the same recurrence.
        for (i = 0; i < NBEAT; i = i + 1)
            for (k = 0; k < 32; k = k + 1) begin
                seed = seed * 32'd1103515245 + 32'd12345;
                beats[i][k*8 +: 8] = seed[23:16];
            end
    end

    // Legal model-side external update (used only by the uncached-region case).
    task automatic poke(input [31:0] baddr, input [31:0] val, input [3:0] strb);
        integer b;
        begin
            b = beat_index(baddr[29:2]);
            for (k = 0; k < 4; k = k + 1)
                if (strb[k])
                    beats[b][baddr[4:0]*8 + k*8 +: 8] = val[k*8 +: 8];
        end
    endtask

    task automatic dump(input string path);
        integer fd, n, p;
        begin
            fd = $fopen(path, "w");
            if (!fd) $fatal(1, "RESULT: FAIL cannot open memory dump");
            for (n = 0; n < NBEAT; n = n + 1)
                $fdisplay(fd, "%0d %h", n, beats[n]);
            $fclose(fd);
        end
    endtask

    always @(posedge clk) begin
        rv_q <= 1'b0;
        if (!resetn) begin
            reading <= 1'b0; writing <= 1'b0;
            ar_wait <= 0; aw_wait <= 0; r_wait <= 0; w_wait <= 0;
            rdata_q <= 0; rid_q <= 0;
        end else if (init_done) begin
            if (arvalid && !arready) ar_wait <= ar_wait + 1;
            if (awvalid && !awready) aw_wait <= aw_wait + 1;
            if (arvalid && arready) begin
                if (araddr[2:0] != 3'b0)
                    $fatal(1, "RESULT: FAIL x32 AR misaligned %h", araddr);
                ra <= araddr;
                held_rid <= aruser_id;
                ar_wait <= 0;
                ar_count = ar_count + 1;
                if (instant_r == 2) begin
                    r_count = r_count + 1;
                end else if (instant_r == 1) begin
                    rdata_q <= beats[beat_index(araddr)];
                    rid_q <= aruser_id;
                    rv_q <= 1'b1;
                    r_count = r_count + 1;
                end else begin
                    reading <= 1'b1;
                    r_wait <= r_lat;
                end
            end
            if (reading) begin
                if (r_wait > 0) r_wait <= r_wait - 1;
                else if (!r_hold) begin
                    reading <= 1'b0;
                    rdata_q <= beats[beat_index(ra)];
                    rid_q <= held_rid;
                    rv_q <= 1'b1;
                    r_count = r_count + 1;
                end
            end
            if (awvalid && awready) begin
                if (awaddr[2:0] != 3'b0)
                    $fatal(1, "RESULT: FAIL x32 AW misaligned %h", awaddr);
                wa <= awaddr;
                held_wdata <= wdata;
                held_wstrb <= wstrb;
                aw_wait <= 0;
                aw_count = aw_count + 1;
                if (instant_w) begin
                    for (k = 0; k < 32; k = k + 1)
                        if (wstrb[k]) beats[beat_index(awaddr)][k*8 +: 8] <= wdata[k*8 +: 8];
                    w_count = w_count + 1;
                end else begin
                    writing <= 1'b1;
                    w_wait <= w_lat;
                end
            end
            if (writing) begin
                if (w_wait > 0) w_wait <= w_wait - 1;
                else if (wready) begin
                    for (k = 0; k < 32; k = k + 1)
                        if (held_wstrb[k]) beats[beat_index(wa)][k*8 +: 8] <= held_wdata[k*8 +: 8];
                    writing <= 1'b0;
                    w_count = w_count + 1;
                end
            end
        end
    end

    final begin
        if (ar_count != r_count + (reading ? 1 : 0))
            $display("MODEL_NOTE ar=%0d r=%0d reading=%0d", ar_count, r_count, reading);
    end
endmodule
