`timescale 1ns / 1ps

// Simulation-only on-chip memories for the CPU-driven DDR image loader.
// The DDR controller and external DDR3 memory remain vendor models.
module inst_rom (
    input  wire [11:0] addr,
    input  wire        clk,
    input  wire        rst,
    output reg  [31:0] rd_data
);
    reg [31:0] words [0:4095];
    string boot_path;
    initial begin
        if (!$value$plusargs("BOOT=%s", boot_path))
            $fatal(1, "missing +BOOT=<boot_rom.dat>");
        $readmemh(boot_path, words);
    end
    always @(posedge clk)
        rd_data <= words[addr];
endmodule

module data_ram (
    input  wire [11:0] addr,
    input  wire [31:0] wr_data,
    output reg  [31:0] rd_data,
    input  wire        wr_en,
    input  wire [3:0]  wr_byte_en,
    input  wire        clk,
    input  wire        rst
);
    reg [31:0] words [0:4095];
    string image_path;
    integer byte_index;
    initial begin
        if (!$value$plusargs("IMAGE=%s", image_path))
            $fatal(1, "missing +IMAGE=<test.dat>");
        $readmemh(image_path, words);
    end
    always @(posedge clk) begin
        rd_data <= words[addr];
        if (wr_en)
            for (byte_index = 0; byte_index < 4; byte_index = byte_index + 1)
                if (wr_byte_en[byte_index])
                    words[addr][byte_index * 8 +: 8] <=
                        wr_data[byte_index * 8 +: 8];
    end
endmodule
