// 只为"单独编译 mycpu_sync.v"提供的空壳,验证文件自身的语法/端口/隐式线网问题
module alu(input wire [11:0] alu_op, input wire [31:0] alu_src1, alu_src2, output wire [31:0] alu_result);
    assign alu_result = alu_src1 + alu_src2;
endmodule

module l_alu(input wire [1:0] sel_addr, input wire [4:0] inst_5l, input wire [31:0] data_sram_rdata, output wire [31:0] mem_result);
    assign mem_result = data_sram_rdata;
endmodule

module inst_rom(input wire [9:0] addr, input wire clk, input wire rst, output wire [31:0] rd_data);
    assign rd_data = 32'h00000013;
endmodule
