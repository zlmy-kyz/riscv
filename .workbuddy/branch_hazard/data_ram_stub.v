// 临时空壳:仅用于单独编译 mycpu_sync.v(它例化了 data_ram)
module data_ram (
    input  wire [31:0] wr_data,
    input  wire [ 9:0] addr,
    input  wire        wr_en,
    input  wire [ 3:0] wr_byte_en,
    input  wire        clk,
    input  wire        rst,
    output wire [31:0] rd_data
);
    assign rd_data = 32'h0;
endmodule
