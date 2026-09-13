module mycpu_single_async (
    input  wire        clk,
    input  wire        resetn
);

    reg vaild;
    always@(posedge clk)begin
        if(!resetn)begin
            vaild <= 1'b0;
        end
        else begin
            vaild <= 1'b1;
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
    assign next_pc = pc + 4;
    assign inst_sram_addr = vaild ? next_pc : pc;
    always@(posedge clk)begin
        if(!resetn)begin
            pc <= 32'h00000000;
        end
        else if(vaild) begin
            pc <= next_pc;
        end
    end
    reg [31:0] if_id_inst;
    reg [31:0] if_id_pc;
    reg if_id_valid;
    always@(posedge clk)begin
        if(!vaild)begin
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

    wire [31:0] pc4    = pc + 32'h4;              // 顺序后继 = jal/jalr 链接值(差异2)
    wire [31:0] b_pc   = pc + imm_b;              // 分支目标(if_id_pc→pc,差异1)

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

    // ---- 寄存器堆(共享 singlecycle/regfile.v:异步读,沿上写)----
    wire [31:0] rdata1, rdata2;
    wire        rf_we;                 // 写回控制(声明提前:regfile 例化处即引用)
    wire [4:0]  rf_waddr;
    wire [31:0] rf_wdata;
    regfile u_regfile (
        .clk   (clk),
        .raddr1(rs1), .raddr2(rs2),
        .waddr (rf_waddr), .we(rf_we),
        .wdata (rf_wdata),
        .rdata1(rdata1), .rdata2(rdata2)
    );

    // ---- B 型分支:译码阶段独立比较单元判定,不复用 ALU(见 br_alu.v)----
    wire [5:0] inst_6b = {inst_bgeu, inst_bltu, inst_bge, inst_blt, inst_bne, inst_beq};
    wire br_taken;
    br_alu u_br_alu (
        .inst_6b (inst_6b),
        .xrs1    (rdata1),
        .xrs2    (rdata2),
        .br_taken(br_taken)
    );

    // ---- ALU 控制(不含分支/跳转:分支由 br_alu 判,跳转目标/链接值独立算)----
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

    // src1:auipc 用 pc;其余 rs1(默认)
    // src2:跳转/分支不再经 ALU(目标与链接值均独立算),故无 i_j 分支
    wire [31:0] alu_src1 = inst_auipc ? pc : rdata1;
    wire [31:0] alu_src2 = i_u ? imm_u
                         : (i_I | i_l) ? imm_i
                         : inst_s ? imm_s
                         : i_shamt ? shamt
                         : rdata2;
    wire [31:0] alu_result;
    alu u_alu (.alu_op(alu_op), .alu_src1(alu_src1), .alu_src2(alu_src2), .alu_result(alu_result));

    // br_taken 由 br_alu 在译码阶段产生(见上方例化),不再经 ALU 派生

    // ---- 访存(控制逻辑与 topcpu.v 相同;读当拍出数,故删 wb_mem_sel 延迟)----
    wire [1:0] st_off = alu_result[1:0];
    wire [3:0] st_we  = inst_sw ? 4'b1111
                      : inst_sh ? (st_off[1] ? 4'b1100 : 4'b0011)
                      : inst_sb ? (4'b0001 << st_off)
                      : 4'b0000;
    assign data_sram_we   = st_we & {4{vaild}};
    assign data_sram_addr = alu_result;
    assign data_sram_wdata = rdata2 << {2'b00, alu_result[1:0], 3'b000};

    wire [31:0] mem_result;
    l_alu u_l_alu (
        .sel_addr(alu_result[1:0]),     // 当前拍即本 load 的偏移,无需延迟
        .inst_5l(inst_5l),
        .data_sram_rdata(data_sram_rdata),
        .mem_result(mem_result)
    );

    // ---- 写回(组合直选;与 pc 更新同沿 = 经典单周期)----
    wire wmem = inst_sw | inst_sh | inst_sb;
    wire gf_we = ~wmem & ~inst_b;                 // store/分支不写;jal/jalr 写链接
    assign rf_we    = gf_we & vaild;
    assign rf_waddr = rd;
    assign rf_wdata = i_l ? mem_result             // load:存储器数据(当拍)
                    : i_j ? pc4                    // jal/jalr:链接值(差异2)
                    : alu_result;

    // ---- 观测口(仅 tb,非数据通路)。tb 在沿后采样(约定:显示"该沿提交的
    //      指令");复位在沿间释放 → 首条指令的执行窗横跨两个采样点,组合
    //      信号抓不到,必须拍存沿前值。数据通路无此寄存器。----


    assign debug_wb_pc     = pc;
    assign debug_wb_rf_we  = {4{rf_we}};
    assign debug_wb_rf_wnum = rf_waddr;
    assign debug_wb_rf_wdata = rf_wdata;

endmodule
