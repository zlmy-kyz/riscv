module mycpu_top(
    input  wire        clk,
    input  wire        resetn,
    // inst sram interface
    output wire [31:0] inst_sram_addr,
    input  wire [31:0] inst_sram_rdata,
    // data sram interface
    output wire [3:0]  data_sram_we,
    output wire [31:0] data_sram_addr,
    output wire [31:0] data_sram_wdata,
    input  wire [31:0] data_sram_rdata,
    // trace debug interface
    output wire [31:0] debug_wb_pc,
    output wire [ 3:0] debug_wb_rf_we,
    output wire [ 4:0] debug_wb_rf_wnum,
    output wire [31:0] debug_wb_rf_wdata
);


reg         valid;
always @(posedge clk) begin
    if (!resetn) begin
        valid <= 1'b0;
    end
    else begin
        valid <= 1'b1;
    end
end

wire [31:0] seq_pc;
wire [31:0] nextpc;
wire        br_taken;
wire [31:0] br_target;
wire [31:0] inst;
reg  [31:0] pc;

wire [11:0] alu_op;
wire        load_op;
wire        src1_is_pc;
wire        src2_is_imm;
wire        res_from_mem;
wire        dst_is_r1;
wire        gr_we;
wire        mem_we;
wire        src_reg_is_rd;
wire [4: 0] dest;
wire [31:0] rj_value;
wire [31:0] rkd_value;
wire [31:0] imm;
wire [31:0] br_offs;
wire [31:0] jirl_offs;

// ===== RV32I 字段(译码区自行声明,不再需要 6-64 等译码器)=====

wire        need_ui5;
wire        need_si12;
wire        need_si16;
wire        need_si20;
wire        need_si26;
wire        src2_is_4;

wire [ 4:0] rf_raddr1;
wire [31:0] rf_rdata1;
wire [ 4:0] rf_raddr2;
wire [31:0] rf_rdata2;
wire        rf_we   ;
wire [ 4:0] rf_waddr;
wire [31:0] rf_wdata;

wire [31:0] alu_src1   ;
wire [31:0] alu_src2   ;
wire [31:0] alu_result ;

wire [31:0] mem_result;
wire [31:0] final_result;

assign seq_pc       = pc + 32'h4;
assign nextpc       = br_taken ? br_target : seq_pc;

always @(posedge clk) begin
    // valid=0(复位期 + 释放后第一拍):pc 停在复位向量 0x0
    // valid=1 后:pc 才走 nextpc —— 0x0 处第一条指令在 valid=1
    // 的周期里被执行并提交,不会被跳过
    if (!valid) begin
        pc <= 32'h00000000;     // 复位向量 = ROM 入口
    end
    else begin
        pc <= nextpc;
    end
end

assign inst_sram_addr  = pc;
assign inst            = inst_sram_rdata;

// ===================== RV32I 字段拆解 =====================
wire [6:0] opcode = inst[ 6: 0];
wire [2:0] funct3 = inst[14:12];
wire [6:0] funct7 = inst[31:25];

wire [4:0] rd    = inst[11: 7];
wire [4:0] rs1   = inst[19:15];
wire [4:0] rs2   = inst[24:20];
wire [4:0] shamt = inst[24:20];

// ===================== RV32I 指令识别(全集)=====================
// ---- R 型(0110011)----
wire inst_add  = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0000000);
wire inst_sub  = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0100000);
wire inst_sll  = (opcode == 7'b0110011) && (funct3 == 3'b001);
wire inst_slt  = (opcode == 7'b0110011) && (funct3 == 3'b010);
wire inst_sltu = (opcode == 7'b0110011) && (funct3 == 3'b011);
wire inst_xor  = (opcode == 7'b0110011) && (funct3 == 3'b100);
wire inst_srl  = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
wire inst_sra  = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
wire inst_or   = (opcode == 7'b0110011) && (funct3 == 3'b110);
wire inst_and  = (opcode == 7'b0110011) && (funct3 == 3'b111);

// ---- I 型算术/移位(0010011)----
wire inst_addi = (opcode == 7'b0010011) && (funct3 == 3'b000);
wire inst_slli = (opcode == 7'b0010011) && (funct3 == 3'b001) && (funct7 == 7'b0000000);
wire inst_slti = (opcode == 7'b0010011) && (funct3 == 3'b010);
wire inst_sltiu= (opcode == 7'b0010011) && (funct3 == 3'b011);
wire inst_xori = (opcode == 7'b0010011) && (funct3 == 3'b100);
wire inst_srli = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
wire inst_srai = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
wire inst_ori  = (opcode == 7'b0010011) && (funct3 == 3'b110);
wire inst_andi = (opcode == 7'b0010011) && (funct3 == 3'b111);

// ---- 访存:load(0000011)----
wire inst_lb  = (opcode == 7'b0000011) && (funct3 == 3'b000);
wire inst_lh  = (opcode == 7'b0000011) && (funct3 == 3'b001);
wire inst_lw  = (opcode == 7'b0000011) && (funct3 == 3'b010);
wire inst_lbu = (opcode == 7'b0000011) && (funct3 == 3'b100);
wire inst_lhu = (opcode == 7'b0000011) && (funct3 == 3'b101);

// ---- 访存:store(0100011)----
wire inst_sb  = (opcode == 7'b0100011) && (funct3 == 3'b000);
wire inst_sh  = (opcode == 7'b0100011) && (funct3 == 3'b001);
wire inst_sw  = (opcode == 7'b0100011) && (funct3 == 3'b010);

// ---- 分支(1100011)----
wire inst_beq  = (opcode == 7'b1100011) && (funct3 == 3'b000);
wire inst_bne  = (opcode == 7'b1100011) && (funct3 == 3'b001);
wire inst_blt  = (opcode == 7'b1100011) && (funct3 == 3'b100);
wire inst_bge  = (opcode == 7'b1100011) && (funct3 == 3'b101);
wire inst_bltu = (opcode == 7'b1100011) && (funct3 == 3'b110);
wire inst_bgeu = (opcode == 7'b1100011) && (funct3 == 3'b111);

// ---- 跳转 ----
wire inst_jal  = (opcode == 7'b1101111);                                // jal
wire inst_jalr = (opcode == 7'b1100111) && (funct3 == 3'b000);           // jalr

// ---- 上立即数 ----
wire inst_lui   = (opcode == 7'b0110111);                               // lui
wire inst_auipc = (opcode == 7'b0010111);                               // auipc

// ---- 杂项(先当 NOP 处理)----
wire inst_fence   = (opcode == 7'b0001111) && (funct3 == 3'b000);       // fence(暂 NOP)
wire inst_fence_i = (opcode == 7'b0001111) && (funct3 == 3'b001);       // fence.i(暂 NOP)
wire inst_ecall   = (inst == 32'h0000_0073);                            // ecall(暂 NOP)
wire inst_ebreak  = (inst == 32'h0010_0073);                            // ebreak(暂 NOP)

// ---- CSR(Zicsr,1110011;funct3=000 为 ecall/ebreak)----
wire inst_csrrw  = (opcode == 7'b1110011) && (funct3 == 3'b001);
wire inst_csrrs  = (opcode == 7'b1110011) && (funct3 == 3'b010);
wire inst_csrrc  = (opcode == 7'b1110011) && (funct3 == 3'b011);
wire inst_csrrwi = (opcode == 7'b1110011) && (funct3 == 3'b101);
wire inst_csrrsi = (opcode == 7'b1110011) && (funct3 == 3'b110);
wire inst_csrrci = (opcode == 7'b1110011) && (funct3 == 3'b111);

// ===================== RV32I 立即数(RV32I 五种编码)=====================
wire [31:0] imm_i = {{20{inst[31]}}, inst[31:20]};                       // I 型(有符号)
wire [31:0] imm_s = {{20{inst[31]}}, inst[31:25], inst[11: 7]};          // S 型(有符号)
wire [31:0] imm_b = {{19{inst[31]}}, inst[31], inst[ 7], inst[30:25],
                      inst[11:8], 1'b0};                                 // B 型(有符号)
wire [31:0] imm_u = {inst[31:12], 12'b0};                                // U 型(无符号)
wire [31:0] imm_j = {{12{inst[31]}}, inst[19:12], inst[20],
                      inst[30:21], 1'b0};                                // J 型(有符号)
wire [31:0] shamt_imm = {27'b0, inst[24:20]};                            // 移位量(零扩展)

wire is_load   = inst_lb | inst_lh | inst_lw | inst_lbu | inst_lhu;
wire is_store  = inst_sb | inst_sh | inst_sw;
wire is_branch = inst_beq | inst_bne | inst_blt | inst_bge |
                 inst_bltu | inst_bgeu;

// ===================== RV32I 控制信号 =====================
// ALU 操作(alu.v 位编码:0加 1减 2slt 3sltu 4与 5或非 6或 7异或 8sll 9srl 10sra 11lui直通)
assign alu_op[ 0] = inst_add  | inst_addi | inst_auipc | is_load | is_store
                    | inst_jal | inst_jalr;                      // jal/jalr 的加=算 pc+4 链接值
assign alu_op[ 1] = inst_sub;
assign alu_op[ 2] = inst_slt | inst_slti | inst_blt | inst_bge;  // bge 用 ~slt
assign alu_op[ 3] = inst_sltu | inst_sltiu | inst_bltu | inst_bgeu;
assign alu_op[ 4] = inst_and | inst_andi;
assign alu_op[ 5] = 1'b0;                                        // RV32I 无 NOR
assign alu_op[ 6] = inst_or | inst_ori;
assign alu_op[ 7] = inst_xor | inst_xori;
assign alu_op[ 8] = inst_sll | inst_slli;
assign alu_op[ 9] = inst_srl | inst_srli;
assign alu_op[10] = inst_sra | inst_srai;
assign alu_op[11] = inst_lui;                                    // lui:直通 src2(=imm_u)

// ALU 第一输入:00/01 选 pc(rj_value=rs1 为默认)
assign src1_is_pc = inst_auipc | inst_jal | inst_jalr;  // auipc:pc+uimm;jal/jalr:pc+4
assign src2_is_4  = inst_jal | inst_jalr;               // 链接值要加的 4

wire i_alu = inst_addi | inst_slli | inst_slti | inst_sltiu | inst_xori |
             inst_srli | inst_srai | inst_ori  | inst_andi;

// ALU 第二输入用的立即数(与跳转偏移 br_offs 分开)
assign imm = src2_is_4        ? 32'h4     :              // jal/jalr:pc+4
             (inst_lui | inst_auipc) ? imm_u :           // lui 直通 / auipc 相加
             (inst_slli | inst_srli | inst_srai) ? shamt_imm :   // 移位量
             is_store    ? imm_s :
             imm_i;                                      // addi/slti 等 I 型与 load

assign src2_is_imm = i_alu | is_load | is_store |
                     inst_lui | inst_auipc | inst_jal | inst_jalr;

// 跳转偏移与目标(独立加法,不占 ALU)
assign br_offs = inst_jal ? imm_j : imm_b;   // jal / 分支偏移

wire eq_rs = (rj_value == rkd_value);        // beq/bne 用
assign br_taken = ( (inst_beq  &&  eq_rs)
                 || (inst_bne  && ~eq_rs)
                 || (inst_blt  &&  alu_result[0])   // alu 已按 blt 设 slt
                 || (inst_bge  && ~alu_result[0])
                 || (inst_bltu &&  alu_result[0])   // alu 已按 bltu 设 sltu
                 || (inst_bgeu && ~alu_result[0])
                 || inst_jal
                 || inst_jalr
                ) && valid;
assign br_target = (is_branch || inst_jal) ? (pc + br_offs)
                                            : (rj_value + imm_i);   // inst_jalr:rs1+imm

// ---- 寄存器堆(同步写,异步读;x0 由 regfile 内部保护)----
assign rf_raddr1 = rs1;
assign rf_raddr2 = rs2;
regfile u_regfile(
    .clk    (clk      ),
    .raddr1 (rf_raddr1),
    .rdata1 (rf_rdata1),
    .raddr2 (rf_raddr2),
    .rdata2 (rf_rdata2),
    .we     (rf_we    ),
    .waddr  (rf_waddr ),
    .wdata  (rf_wdata )
    );

assign rj_value  = rf_rdata1;   // rs1 读值(沿用旧名)
assign rkd_value = rf_rdata2;   // rs2 读值

// ---- 访存与写回 ----
assign gr_we = inst_add | inst_sub | inst_sll | inst_slt | inst_sltu |
               inst_xor | inst_srl | inst_sra | inst_or  | inst_and |
               inst_addi| inst_slli| inst_slti| inst_sltiu| inst_xori|
               inst_srli| inst_srai| inst_ori| inst_andi|
               inst_lui | inst_auipc | is_load | inst_jal | inst_jalr;
assign mem_we = is_store;
assign dest   = rd;                            

assign data_sram_we    = {4{mem_we && valid}};   // 先支持 sw 整字;sb/sh 需按地址出字节使能
assign data_sram_addr  = alu_result;             // load/store 地址 = rs1 + imm
assign data_sram_wdata = rkd_value;              // 写 rs2

assign res_from_mem  = is_load;
assign final_result  = res_from_mem ? data_sram_rdata : alu_result;  // lb/lh 符号扩展后续加

assign rf_we    = gr_we && valid;
assign rf_waddr = dest;
assign rf_wdata = final_result;

// debug info generate
assign debug_wb_pc       = pc;
//assign debug_wb_rf_wen   = {4{rf_we}};   //to change wen to we
assign debug_wb_rf_we   = {4{rf_we}};   //to change wen to we
assign debug_wb_rf_wnum  = dest;
assign debug_wb_rf_wdata = final_result;

endmodule
