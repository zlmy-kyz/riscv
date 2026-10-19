`timescale 1ns / 1ps

// Active-low reset button: assert immediately, release only after a stable
// high interval. Use an always-running reference clock, never a clock whose
// PLL is held in reset by resetn_out. Default: 20 ms at 125 MHz.
module reset_button_debounce #(
    parameter integer STABLE_CYCLES = 2_500_000
) (
    input  wire clk,
    input  wire keyn,
    output reg  resetn_out = 1'b0
);
    localparam integer FILTER_CYCLES = (STABLE_CYCLES < 1) ? 1 : STABLE_CYCLES;
    localparam integer COUNT_WIDTH = (FILTER_CYCLES <= 1) ? 1 : $clog2(FILTER_CYCLES);
    localparam [COUNT_WIDTH-1:0] LAST_COUNT = FILTER_CYCLES - 1;

    // FPGA power-up values keep reset asserted even if KEY0 is already up.
    // Both stages assert asynchronously and release on reference-clock edges.
    reg [1:0] key_release_sync = 2'b00;
    reg [COUNT_WIDTH-1:0] stable_count = {COUNT_WIDTH{1'b0}};

    always @(posedge clk or negedge keyn) begin
        if (!keyn)
            key_release_sync <= 2'b00;
        else
            key_release_sync <= {key_release_sync[0], 1'b1};
    end

    always @(posedge clk or negedge keyn) begin
        if (!keyn) begin
            stable_count <= {COUNT_WIDTH{1'b0}};
            resetn_out <= 1'b0;
        end else if (!key_release_sync[1]) begin
            stable_count <= {COUNT_WIDTH{1'b0}};
            resetn_out <= 1'b0;
        end else if (!resetn_out) begin
            if (stable_count == LAST_COUNT)
                resetn_out <= 1'b1;
            else
                stable_count <= stable_count + 1'b1;
        end
    end
endmodule
