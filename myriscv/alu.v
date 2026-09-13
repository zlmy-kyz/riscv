module alu(
  input  wire [10:0] alu_op,
  input  wire [31:0] alu_src1,
  input  wire [31:0] alu_src2,
  output wire [31:0] alu_result
);
    wire op_add_auipc;   //add operation
    wire op_sub;   //sub operation
    wire op_lui;   //Load Upper Immediatecd
    wire op_and;   //and operation
    wire op_or;    //or operation
    wire op_xor;   //xor operation
    wire op_sll;   //logic left shift
    wire op_slt;   //signed compared and set less than
    wire op_srl;   //logic right shi
    wire op_sra;   //arithmetic right shift
    wire op_sltu;  //unsigned compared and set less than

    // control code decomposition
    assign op_add_auipc  = alu_op[ 0];
    assign op_sub  = alu_op[ 1];
    assign op_lui  = alu_op[ 2]; 
    assign op_and  = alu_op[ 3];
    assign op_or   = alu_op[ 4];
    assign op_xor  = alu_op[ 5];
    assign op_sll  = alu_op[ 6];
    assign op_slt  = alu_op[ 7];
    assign op_srl  = alu_op[ 8];
    assign op_sra  = alu_op[ 9];
    assign op_sltu = alu_op[10];


    wire [31:0] add_sub_result;
    wire [31:0] lui_result;
    wire [31:0] and_result;
    wire [31:0] or_result;
    wire [31:0] xor_result;
    wire [31:0] sll_result;
    wire [31:0] slt_result;
    wire [31:0] srl_result;
    wire [31:0] sra_result;
    wire [31:0] sltu_result;

    wire [31:0] adder_a;
    wire [31:0] adder_b;
    wire        adder_cin;
    wire [31:0] adder_result;
    wire        adder_cout;

    assign adder_a   = alu_src1;
    assign adder_b   = (op_sub | op_slt) ? ~alu_src2 : alu_src2;  //src1 - src2 rj-rk
    assign adder_cin = (op_sub | op_slt) ? 1'b1      : 1'b0;
    assign {adder_cout, adder_result} = adder_a + adder_b + adder_cin;

    assign add_sub_result = adder_result;
    assign lui_result = alu_src2;
    assign and_result = alu_src1 & alu_src2;
    assign or_result  = alu_src1 | alu_src2;
    assign xor_result = alu_src1 ^ alu_src2;
    assign sll_result = alu_src1 << alu_src2[4:0];
    assign slt_result[31:1] = 31'b0;   //rj < rk 1
    assign slt_result[0]    = (alu_src1[31] & ~alu_src2[31])
                            | ((alu_src1[31] ~^ alu_src2[31]) & adder_result[31]);
    assign srl_result = alu_src1 >> alu_src2[4:0];
    assign sra_result = ($signed(alu_src1)) >>> alu_src2[4:0];
    assign sltu_result = (alu_src1 < alu_src2);  // 直接比较
    assign alu_result = ({32{op_add_auipc|op_sub}} & add_sub_result)
                      | ({32{op_lui}} & lui_result)
                      | ({32{op_and}} & and_result)
                      | ({32{op_or}} & or_result)
                      | ({32{op_xor}} & xor_result)
                      | ({32{op_sll}} & sll_result)
                      | ({32{op_slt}} & slt_result)
                      | ({32{op_srl}} & srl_result)
                      | ({32{op_sra}} & sra_result)
                      | ({32{op_sltu}} & sltu_result);

endmodule
