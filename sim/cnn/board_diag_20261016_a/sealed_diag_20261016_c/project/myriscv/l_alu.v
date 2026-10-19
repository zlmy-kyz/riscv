module l_alu(
    input [1:0] sel_addr,
    input wire [4:0] inst_5l,
    input wire [31:0] data_sram_rdata,
    output wire [31:0] mem_result
);

    wire [31:0] mem_result_lb;
    wire [31:0] mem_result_lh;
    wire [31:0] mem_result_lbu;
    wire [31:0] mem_result_lhu;
    wire [31:0] mem_result_lw;  
    wire [7:0] byte_data1, byte_data2, byte_data3, byte_data4;
    wire [15:0] halfword_data1, halfword_data2;

    assign {byte_data4, byte_data3, byte_data2, byte_data1} = data_sram_rdata;
    assign {halfword_data2, halfword_data1} = data_sram_rdata;

    assign mem_result_lb = (sel_addr == 2'b00) ? {{24{byte_data1[7]}}, byte_data1} :
                           (sel_addr == 2'b01) ? {{24{byte_data2[7]}}, byte_data2} :
                           (sel_addr == 2'b10) ? {{24{byte_data3[7]}}, byte_data3} :
                                                 {{24{byte_data4[7]}}, byte_data4};

    assign mem_result_lbu = (sel_addr == 2'b00) ? {24'b0, byte_data1} :
                            (sel_addr == 2'b01) ? {24'b0, byte_data2} :
                            (sel_addr == 2'b10) ? {24'b0, byte_data3} :
                                                  {24'b0, byte_data4};
                    
    assign mem_result_lh = (sel_addr == 2'b00) ? {{16{halfword_data1[15]}}, halfword_data1} :
                           (sel_addr == 2'b10) ? {{16{halfword_data2[15]}}, halfword_data2} :
                                                 {{16{halfword_data2[15]}}, halfword_data2};


    assign mem_result_lhu = (sel_addr == 2'b00) ? {16'b0, halfword_data1} :
                            (sel_addr == 2'b10) ? {16'b0, halfword_data2} :
                                                  {16'b0, halfword_data2};

    assign mem_result_lw = data_sram_rdata;

    assign mem_result = (inst_5l[4]) ? mem_result_lw :
                        (inst_5l[3]) ? mem_result_lh :
                        (inst_5l[2]) ? mem_result_lhu :
                        (inst_5l[1]) ? mem_result_lb :
                        (inst_5l[0]) ? mem_result_lbu :
                                      32'b0;



endmodule