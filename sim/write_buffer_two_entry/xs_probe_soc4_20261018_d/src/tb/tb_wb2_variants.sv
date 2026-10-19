// Parameterised wrappers around tb_wb2_bridge.
//
// Why: Vivado xsim (2019.2) has no equivalent of vsim's -g<NAME>=<value> for
// Verilog parameters; -generic_top only drives VHDL generics. Each runnable
// configuration therefore gets a thin wrapper module that overrides the
// parameters of the single testbench. The testbench itself is NOT modified, so
// every configuration below still runs the identical stimulus code.
//
// LEGACY_BRIDGE is a compile-time switch inside tb_wb2_bridge (the pre-043
// bridge has no WRITE_BUFFER_DEPTH port), so the two "old" wrappers only make
// sense in a library compiled with +define+LEGACY_BRIDGE.

// ---- full key group, two-entry posted write buffer ----
module tb_wb2_key;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(0)
    ) u ();
endmodule

// ---- short reference sequence, new bridge, depth 2 ----
module tb_wb2_short_new_d2;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(1)
    ) u ();
endmodule

// ---- short reference sequence, new bridge, depth 1 (ordered-single baseline) ----
module tb_wb2_short_new_d1;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(1), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(1)
    ) u ();
endmodule

// ---- short reference sequence, pre-043 bridge (no depth parameter) ----
module tb_wb2_short_old;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(1), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(1)
    ) u ();
endmodule

// ---- compatibility points that must not depend on the second entry ----
module tb_wb2_compat_noposted;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(0), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(1)
    ) u ();
endmodule

module tb_wb2_compat_noturnover;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(0), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(1)
    ) u ();
endmodule

module tb_wb2_compat_no_forward;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(0), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(1)
    ) u ();
endmodule

module tb_wb2_compat_linebuf_off;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(0), .DCACHE(0), .CAMERA(0), .PREPROC(0), .PLANE(1)
    ) u ();
endmodule

// ---- fair short comparison: identical TB/bytes/backend calendar, depth only ----
module tb_wb2_fair_d1;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(1), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(2)
    ) u ();
endmodule

module tb_wb2_fair_d2;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(2)
    ) u ();
endmodule

// ---- remaining bridge edges, one independent fragment each ----
module tb_wb2_edge;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(3)
    ) u ();
endmodule

// ---- x16 minimal read/write (128-bit beats, four lanes, native units) ----
// The line buffers are built on the x32 path only, so this configuration runs
// with both disabled rather than pretending to check a cache that does not exist.
module tb_wb2_x16;
    tb_wb2_bridge #(
        .DQ(16), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(0), .DCACHE(0), .CAMERA(0), .PREPROC(0), .PLANE(4)
    ) u ();
endmodule

// ---- non-posted x32 minimal ----
module tb_wb2_noposted;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(0), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(1),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(5)
    ) u ();
endmodule

// ---- RUW=0: loads must wait for the whole queue, then read correctly ----
module tb_wb2_ruw0;
    tb_wb2_bridge #(
        .DQ(32), .POSTED(1), .DEPTH(2), .TURNOVER(1), .FORWARD(1), .RUW(0),
        .ICACHE(1), .DCACHE(1), .CAMERA(0), .PREPROC(0), .PLANE(6)
    ) u ();
endmodule
