//======================================================================
// br_alu — B 型分支条件比较(译码阶段组合判定,不进 ALU)
//   六个比较并行计算,由 inst_6b 按当前分支指令选通(独热,恰好一位为 1)
//   inst_6b 位序 = {bgeu, bltu, bge, blt, bne, beq} → [5]..[0]
//   功能与 singlecycle/b_alu.v 相同,改名以避免两核混编时模块重名
//======================================================================
module br_alu(
    input  wire [5:0]  inst_6b,
    input  wire [31:0] xrs1,
    input  wire [31:0] xrs2,
    output wire        br_taken
);
    wire beq_taken  = (xrs1 == xrs2);
    wire bne_taken  = (xrs1 != xrs2);
    wire blt_taken  = ($signed(xrs1) <  $signed(xrs2));
    wire bge_taken  = ($signed(xrs1) >= $signed(xrs2));
    wire bltu_taken = (xrs1 <  xrs2);
    wire bgeu_taken = (xrs1 >= xrs2);

    assign br_taken =  inst_6b[5] & bgeu_taken
                    |  inst_6b[4] & bltu_taken
                    |  inst_6b[3] & bge_taken
                    |  inst_6b[2] & blt_taken
                    |  inst_6b[1] & bne_taken
                    |  inst_6b[0] & beq_taken;
endmodule
