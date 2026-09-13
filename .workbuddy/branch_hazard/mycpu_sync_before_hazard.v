module mycpu_single_async (
    input  wire        clk,
    input  wire        resetn
);

    reg valid;
    always@(posedge clk)begin
        if(!resetn)begin
            valid <= 1'b0;
        end
        else begin
            valid <= 1'b1;
        end
    end
    wire [31:0] inst_sram_addr;
    wire [31:0] inst;

    inst_rom u_inst_rom(
        .addr(inst_sram_addr[11:2]),
        .clk(clk),
        .rst(!resetn),
        .rd_data(inst)
    );
    reg[31:0] pc;
    wire[31:0] next_pc;
    // next_pc 的赋值下移到"跳转地址 / next_pc 逻辑"处(依赖译码出的分支/跳转信号)
    assign inst_sram_addr = valid ? next_pc : pc;
    always@(posedge clk)begin
        if(!resetn)begin
            pc <= 32'h00000000;
        end
        else if(valid) begin
            pc <= next_pc;
        end
    end
    reg [31:0] if_id_inst;
    reg [31:0] if_id_pc;
    reg if_id_valid;
    always@(posedge clk)begin
        if(!valid)begin
            if_id_inst <= 32'h00000000;
            if_id_pc <= 32'h00000000;
            if_id_valid <= 1'b0;
        end
        else begin
            if_id_inst <= inst;
            if_id_pc <= pc;
            if_id_valid <= 1'b1;
        end
    end

    // ================= 跳转地址 / next_pc 逻辑 =================
    // 顺序后继:既是默认 next_pc,也是 jal/jalr 的链接值(写回 rd)
    wire [31:0] pc4    = pc + 32'h4;

    // 三种跳转目标(全部当拍组合算出,满足 ROM 地址口 setup)
    wire [31:0] b_pc    = pc + imm_b;                  // B 型:分支目标 = pc + imm_b
    wire [31:0] jal_pc  = pc + imm_j;                  // J 型:jal 目标 = pc + imm_j
    wire [31:0] jalr_pc = (rdata1 + imm_i) & ~32'h1;   // I 型:jalr 目标 = (rs1+imm_i) 清最低位

    // 分支目标与跳转目标合并(按指令选通)
    wire [31:0] bj_pc   = inst_jalr ? jalr_pc
                        : inst_jal  ? jal_pc
                        :             b_pc;            // 默认 = 分支目标

    // 跳转使能:分支条件成立(br_alu 组合输出)| jal | jalr
    // 注:非分支指令 inst_6b 全 0,br_taken 必为 0,故可安全相或
    wire        pc_sel  = br_taken | inst_jal | inst_jalr;

    assign next_pc = pc_sel ? bj_pc : pc4;             // 跳转取目标,否则顺序 +4
    // =========================================================

    // ---- 译码(与 topcpu.v 完全相同)----
    wire [6:0] opcode = inst[6:0];
    wire [2:0] funct3 = inst[14:12];
    wire [6:0] funct7 = inst[31:25];
    wire [4:0] rd     = inst[11:7];
    wire [4:0] rs1    = inst[19:15];
    wire [4:0] rs2    = inst[24:20];
    wire [11:0] csr_addr = inst[31:20];
    wire [31:0] shamt = {27'b0, inst[24:20]};

    wire inst_add   = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0000000);
    wire inst_addi  = (opcode == 7'b0010011) && (funct3 == 3'b000);
    wire inst_sub   = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0100000);
    wire inst_lui   = (opcode == 7'b0110111);
    wire inst_auipc = (opcode == 7'b0010111);
    wire inst_and   = (opcode == 7'b0110011) && (funct3 == 3'b111) && (funct7 == 7'b0000000);
    wire inst_andi  = (opcode == 7'b0010011) && (funct3 == 3'b111);
    wire inst_or    = (opcode == 7'b0110011) && (funct3 == 3'b110) && (funct7 == 7'b0000000);
    wire inst_ori   = (opcode == 7'b0010011) && (funct3 == 3'b110);
    wire inst_xor   = (opcode == 7'b0110011) && (funct3 == 3'b100) && (funct7 == 7'b0000000);
    wire inst_xori  = (opcode == 7'b0010011) && (funct3 == 3'b100);
    wire inst_sll   = (opcode == 7'b0110011) && (funct3 == 3'b001) && (funct7 == 7'b0000000);
    wire inst_slli  = (opcode == 7'b0010011) && (funct3 == 3'b001) && (funct7 == 7'b0000000);
    wire inst_slti  = (opcode == 7'b0010011) && (funct3 == 3'b010);
    wire inst_slt   = (opcode == 7'b0110011) && (funct3 == 3'b010) && (funct7 == 7'b0000000);
    wire inst_srli  = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
    wire inst_srl   = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
    wire inst_sra   = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
    wire inst_srai  = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
    wire inst_sltu  = (opcode == 7'b0110011) && (funct3 == 3'b011) && (funct7 == 7'b0000000);
    wire inst_sltiu = (opcode == 7'b0010011) && (funct3 == 3'b011);
    wire inst_jalr  = (opcode == 7'b1100111) && (funct3 == 3'b000);
    wire inst_jal   = (opcode == 7'b1101111);
    wire inst_bne   = (opcode == 7'b1100011) && (funct3 == 3'b001);
    wire inst_beq   = (opcode == 7'b1100011) && (funct3 == 3'b000);
    wire inst_blt   = (opcode == 7'b1100011) && (funct3 == 3'b100);
    wire inst_bge   = (opcode == 7'b1100011) && (funct3 == 3'b101);
    wire inst_bltu  = (opcode == 7'b1100011) && (funct3 == 3'b110);
    wire inst_bgeu  = (opcode == 7'b1100011) && (funct3 == 3'b111);
    wire inst_lw    = (opcode == 7'b0000011) && (funct3 == 3'b010);
    wire inst_lh    = (opcode == 7'b0000011) && (funct3 == 3'b001);
    wire inst_lb    = (opcode == 7'b0000011) && (funct3 == 3'b000);
    wire inst_lhu   = (opcode == 7'b0000011) && (funct3 == 3'b101);
    wire inst_lbu   = (opcode == 7'b0000011) && (funct3 == 3'b100);
    wire inst_sw    = (opcode == 7'b0100011) && (funct3 == 3'b010);
    wire inst_sh    = (opcode == 7'b0100011) && (funct3 == 3'b001);
    wire inst_sb    = (opcode == 7'b0100011) && (funct3 == 3'b000);
    wire inst_csrrw = (opcode == 7'b1110011) && (funct3 == 3'b001);
    wire inst_csrrs = (opcode == 7'b1110011) && (funct3 == 3'b010);
    wire inst_csrrc = (opcode == 7'b1110011) && (funct3 == 3'b011);
    wire inst_csrrwi = (opcode == 7'b1110011) && (funct3 == 3'b101);
    wire inst_csrrsi = (opcode == 7'b1110011) && (funct3 == 3'b110);
    wire inst_csrrci = (opcode == 7'b1110011) && (funct3 == 3'b111);
    wire i_j    = inst_jalr | inst_jal;
    wire i_l    = inst_lw | inst_lh | inst_lb | inst_lhu | inst_lbu;
    wire [4:0] inst_5l = {inst_lw, inst_lh, inst_lhu, inst_lb, inst_lbu};
    wire i_u    = inst_lui | inst_auipc;
    wire i_shamt= inst_slli | inst_srli | inst_srai;
    wire i_I    = inst_slti | inst_sltiu | inst_addi | inst_andi | inst_ori | inst_xori;
    wire inst_s = inst_sw | inst_sh | inst_sb;
    wire inst_b = inst_beq | inst_bne | inst_blt | inst_bge | inst_bltu | inst_bgeu;

    wire [31:0] imm_u = {inst[31:12], 12'b0};
    wire [31:0] imm_i = {{20{inst[31]}}, inst[31:20]};
    wire [31:0] imm_s = {{20{inst[31]}}, inst[31:25], inst[11:7]};
    wire [31:0] imm_b = {{19{inst[31]}}, inst[31], inst[7], inst[30:25], inst[11:8], 1'b0};
    wire [31:0] imm_j = {{11{inst[31]}}, inst[31], inst[19:12], inst[20], inst[30:21], 1'b0};
    wire [4:0] zimm = inst[19:15];
    
    wire wmem;
    wire gf_we;

    assign wmem = inst_sw | inst_sh | inst_sb;
    assign gf_we = ~wmem & ~inst_b;

    wire [31:0] rdata1, rdata2;
    wire        rf_we;              
    wire [4:0]  rf_waddr;
    wire [31:0] rf_wdata;
    regfile u_regfile (
        .clk   (clk),
        .raddr1(rs1), .raddr2(rs2),
        .waddr (rf_waddr), .we(rf_we), .rst(~resetn),
        .wdata (rf_wdata),
        .rdata1(rdata1), .rdata2(rdata2)
    );

  
    wire [5:0] inst_6b = {inst_bgeu, inst_bltu, inst_bge, inst_blt, inst_bne, inst_beq};
    wire br_taken;
    br_alu u_br_alu (
        .inst_6b (inst_6b),
        .xrs1    (rdata1),
        .xrs2    (rdata2),
        .br_taken(br_taken)
    );

    wire [10:0] alu_op;
    assign alu_op[0]  = inst_add | inst_auipc | inst_addi |
                        inst_lw | inst_lh | inst_lb | inst_lhu | inst_lbu |
                        inst_sw | inst_sh | inst_sb;
    assign alu_op[1]  = inst_sub;
    assign alu_op[2]  = inst_lui;
    assign alu_op[3]  = inst_and | inst_andi;
    assign alu_op[4]  = inst_or | inst_ori;
    assign alu_op[5]  = inst_xor | inst_xori;
    assign alu_op[6]  = inst_sll | inst_slli;
    assign alu_op[7]  = inst_slt | inst_slti;
    assign alu_op[8]  = inst_srl | inst_srli;
    assign alu_op[9]  = inst_sra | inst_srai;
    assign alu_op[10] = inst_sltu | inst_sltiu;


    wire [31:0] alu_src1 = inst_auipc ? pc : rdata1;
    wire [31:0] alu_src2 = i_u ? imm_u
                         : (i_I | i_l) ? imm_i
                         : inst_s ? imm_s
                         : i_shamt ? shamt
                         : rdata2;
    wire [31:0] alu_result;
    alu u_alu (.alu_op(alu_op), .alu_src1(alu_src1), .alu_src2(alu_src2), .alu_result(alu_result));

    wire [31:0] data_sram_addr;
    wire [31:0] data_sram_wdata;
    wire [3:0]  data_sram_we;
    wire [31:0] data_sram_rdata;

    wire [1:0] st_off = alu_result[1:0];
    wire [3:0] st_we  = inst_sw ? 4'b1111
                      : inst_sh ? (st_off[1] ? 4'b1100 : 4'b0011)
                      : inst_sb ? (4'b0001 << st_off)
                      : 4'b0000;
    assign data_sram_we   = st_we & {4{valid}};
    assign data_sram_addr = alu_result;
    assign data_sram_wdata = rdata2 << {2'b00, alu_result[1:0], 3'b000};
    

    
    data_ram the_instance_name (
        .wr_data(data_sram_wdata),          // input [31:0]
        .addr(data_sram_addr[11:2]),                // input [9:0]
        .wr_en(wmem),              // input
        .wr_byte_en(data_sram_we),    // input [3:0]
        .clk(clk),                  // input
        .rst(~resetn),                  // input
        .rd_data(data_sram_rdata)           // output [31:0]
    );

    wire [31:0] mem_result;
    l_alu u_l_alu (
        .sel_addr(alu_result[1:0]),     
        .inst_5l(inst_5l),
        .data_sram_rdata(data_sram_rdata),
        .mem_result(mem_result)
    );

    
                     
    assign rf_we    = gf_we & valid;
    assign rf_waddr = rd;
    assign rf_wdata = i_l ? mem_result            
                    : i_j ? pc4                    
                    : alu_result;

 

    assign debug_wb_pc     = pc;
    assign debug_wb_rf_we  = {4{rf_we}};
    assign debug_wb_rf_wnum = rf_waddr;
    assign debug_wb_rf_wdata = rf_wdata;

endmodule
