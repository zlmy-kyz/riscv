module mycpu_sync (
    input  wire        clk,
    input  wire        resetn,
    output [31:0]      debug_wb_pc,
    output [3:0]       debug_wb_rf_we,
    output [4:0]       debug_wb_rf_wnum,
    output [31:0]      debug_wb_rf_wdata,
    output [31:0]      debug_inst
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
    wire [31:0] inst_if;        // IF 级:ROM 取回的原始指令(同步读,1 拍延迟)

    inst_rom u_inst_rom(
        .addr(inst_sram_addr[11:2]),
        .clk(clk),
        .rst(!resetn),
        .rd_data(inst_if)
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
    // ---------- IF/ID 流水寄存器 = ID 级的输入 ----------
    // 气泡三个来源:① 复位(!valid) ② 分支/跳转冲刷(flush) ③ 下游阻塞(stall,暂未做)
    // 约定:气泡的唯一标志是 if_id_valid=0;指令/PC 字段只填"安全兜底值",不参与判断
    // 寄存器本体在这里声明, 但它的时序块挪到了下面"分支冒险"段之后 ——
    // 该块要读 flush, 而 flush 依赖 ID 级译码 / 寄存器堆 / br_alu, 那些信号声明在后面。
    // 全模块按"先声明后使用"的顺序排, 不留任何前置声明。
    reg [31:0] if_id_inst;
    reg [31:0] if_id_pc;
    reg if_id_valid;
        // ===================================================================

    // ---------- IF/ID 流水寄存器时序块 ----------
    // 排在分支冒险段之后: 上面的 flush 已经声明并赋值, 这里才读它。
    // 气泡三个来源:① 复位(!valid) ② 分支/跳转冲刷(flush) ③ 下游阻塞(stall,暂未做)
    // 约定:气泡的唯一标志是 if_id_valid=0;指令/PC 字段只填"安全兜底值",不参与判断
    always@(posedge clk)begin
        if(!valid)begin
            if_id_inst <= 32'h00000000;
            if_id_pc <= 32'h00000000;
            if_id_valid <= 1'b0;
        end
        else if(flush)begin                                    // ★ 分支冒险:冲掉错取的指令
            if_id_inst <= 32'h0000_0013;                       // NOP(addi x0,x0,0)兜底
            if_id_pc <= 32'hFFFF_FFFF;                         // 哨兵:波形上一眼认出气泡
            if_id_valid <= 1'b0;
        end
        else begin
            if_id_inst <= inst_if;
            if_id_pc <= pc;
            if_id_valid <= 1'b1;
        end
    end
    // ID 级及其后各级看到的指令 = IF/ID 寄存器输出。
    // 沿用旧名 inst → 下方整套译码/立即数代码一行都不用改。
    wire [31:0] inst;
    assign inst = if_id_inst;

    // ---- 译码(与 topcpu.v 完全相同)----
    wire [6:0] opcode;
    assign opcode = inst[6:0];
    wire [2:0] funct3;
    assign funct3 = inst[14:12];
    wire [6:0] funct7;
    assign funct7 = inst[31:25];
    wire [4:0] rd;
    assign rd     = inst[11:7];
    wire [4:0] rs1;
    assign rs1    = inst[19:15];
    wire [4:0] rs2;
    assign rs2    = inst[24:20];
    wire [11:0] csr_addr;
    assign csr_addr = inst[31:20];
    wire [31:0] shamt;
    assign shamt = {27'b0, inst[24:20]};

    wire inst_add;
    assign inst_add   = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0000000);
    wire inst_addi;
    assign inst_addi  = (opcode == 7'b0010011) && (funct3 == 3'b000);
    wire inst_sub;
    assign inst_sub   = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0100000);
    wire inst_lui;
    assign inst_lui   = (opcode == 7'b0110111);
    wire inst_auipc;
    assign inst_auipc = (opcode == 7'b0010111);
    wire inst_and;
    assign inst_and   = (opcode == 7'b0110011) && (funct3 == 3'b111) && (funct7 == 7'b0000000);
    wire inst_andi;
    assign inst_andi  = (opcode == 7'b0010011) && (funct3 == 3'b111);
    wire inst_or;
    assign inst_or    = (opcode == 7'b0110011) && (funct3 == 3'b110) && (funct7 == 7'b0000000);
    wire inst_ori;
    assign inst_ori   = (opcode == 7'b0010011) && (funct3 == 3'b110);
    wire inst_xor;
    assign inst_xor   = (opcode == 7'b0110011) && (funct3 == 3'b100) && (funct7 == 7'b0000000);
    wire inst_xori;
    assign inst_xori  = (opcode == 7'b0010011) && (funct3 == 3'b100);
    wire inst_sll;
    assign inst_sll   = (opcode == 7'b0110011) && (funct3 == 3'b001) && (funct7 == 7'b0000000);
    wire inst_slli;
    assign inst_slli  = (opcode == 7'b0010011) && (funct3 == 3'b001) && (funct7 == 7'b0000000);
    wire inst_slti;
    assign inst_slti  = (opcode == 7'b0010011) && (funct3 == 3'b010);
    wire inst_slt;
    assign inst_slt   = (opcode == 7'b0110011) && (funct3 == 3'b010) && (funct7 == 7'b0000000);
    wire inst_srli;
    assign inst_srli  = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
    wire inst_srl;
    assign inst_srl   = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
    wire inst_sra;
    assign inst_sra   = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
    wire inst_srai;
    assign inst_srai  = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
    wire inst_sltu;
    assign inst_sltu  = (opcode == 7'b0110011) && (funct3 == 3'b011) && (funct7 == 7'b0000000);
    wire inst_sltiu;
    assign inst_sltiu = (opcode == 7'b0010011) && (funct3 == 3'b011);
    wire inst_jalr;
    assign inst_jalr  = (opcode == 7'b1100111) && (funct3 == 3'b000);
    wire inst_jal;
    assign inst_jal   = (opcode == 7'b1101111);
    wire inst_bne;
    assign inst_bne   = (opcode == 7'b1100011) && (funct3 == 3'b001);
    wire inst_beq;
    assign inst_beq   = (opcode == 7'b1100011) && (funct3 == 3'b000);
    wire inst_blt;
    assign inst_blt   = (opcode == 7'b1100011) && (funct3 == 3'b100);
    wire inst_bge;
    assign inst_bge   = (opcode == 7'b1100011) && (funct3 == 3'b101);
    wire inst_bltu;
    assign inst_bltu  = (opcode == 7'b1100011) && (funct3 == 3'b110);
    wire inst_bgeu;
    assign inst_bgeu  = (opcode == 7'b1100011) && (funct3 == 3'b111);
    wire inst_lw;
    assign inst_lw    = (opcode == 7'b0000011) && (funct3 == 3'b010);
    wire inst_lh;
    assign inst_lh    = (opcode == 7'b0000011) && (funct3 == 3'b001);
    wire inst_lb;
    assign inst_lb    = (opcode == 7'b0000011) && (funct3 == 3'b000);
    wire inst_lhu;
    assign inst_lhu   = (opcode == 7'b0000011) && (funct3 == 3'b101);
    wire inst_lbu;
    assign inst_lbu   = (opcode == 7'b0000011) && (funct3 == 3'b100);
    wire inst_sw;
    assign inst_sw    = (opcode == 7'b0100011) && (funct3 == 3'b010);
    wire inst_sh;
    assign inst_sh    = (opcode == 7'b0100011) && (funct3 == 3'b001);
    wire inst_sb;
    assign inst_sb    = (opcode == 7'b0100011) && (funct3 == 3'b000);
    wire inst_csrrw;
    assign inst_csrrw = (opcode == 7'b1110011) && (funct3 == 3'b001);
    wire inst_csrrs;
    assign inst_csrrs = (opcode == 7'b1110011) && (funct3 == 3'b010);
    wire inst_csrrc;
    assign inst_csrrc = (opcode == 7'b1110011) && (funct3 == 3'b011);
    wire inst_csrrwi;
    assign inst_csrrwi = (opcode == 7'b1110011) && (funct3 == 3'b101);
    wire inst_csrrsi;
    assign inst_csrrsi = (opcode == 7'b1110011) && (funct3 == 3'b110);
    wire inst_csrrci;
    assign inst_csrrci = (opcode == 7'b1110011) && (funct3 == 3'b111);
    wire i_j;
    assign i_j    = inst_jalr | inst_jal;
    wire i_l;
    assign i_l    = inst_lw | inst_lh | inst_lb | inst_lhu | inst_lbu;
    wire [4:0] inst_5l;
    assign inst_5l = {inst_lw, inst_lh, inst_lhu, inst_lb, inst_lbu};
    wire i_u;
    assign i_u    = inst_lui | inst_auipc;
    wire i_shamt;
    assign i_shamt= inst_slli | inst_srli | inst_srai;
    wire i_I;
    assign i_I    = inst_slti | inst_sltiu | inst_addi | inst_andi | inst_ori | inst_xori;
    wire inst_s;
    assign inst_s = inst_sw | inst_sh | inst_sb;
    wire inst_b;
    assign inst_b = inst_beq | inst_bne | inst_blt | inst_bge | inst_bltu | inst_bgeu;

    wire [31:0] imm_u;
    assign imm_u = {inst[31:12], 12'b0};
    wire [31:0] imm_i;
    assign imm_i = {{20{inst[31]}}, inst[31:20]};
    wire [31:0] imm_s;
    assign imm_s = {{20{inst[31]}}, inst[31:25], inst[11:7]};
    wire [31:0] imm_b;
    assign imm_b = {{19{inst[31]}}, inst[31], inst[7], inst[30:25], inst[11:8], 1'b0};
    wire [31:0] imm_j;
    assign imm_j = {{11{inst[31]}}, inst[31], inst[19:12], inst[20], inst[30:21], 1'b0};
    wire [4:0] zimm;
    assign zimm = inst[19:15];

    // ---- 立即数统一生成:六类编码两两互斥 → 按位或合并 ----
    // 为什么可以直接"或":各编码的 opcode 互不相同 ——
    //   U(0110111/0010111) I(0010011/0000011) S(0100011) B(1100011) J(1101111) jalr(1100111);
    //   唯一共用 0010011 的 i_I 与 i_shamt 由 funct3 区分(000/010/011/100/110/111 vs 001/101)。
    // 与优先级链相比:少了 3 级级联 mux,而且生成了唯一一个 imm,分支目标也能复用它。
    wire imm_i_sel;
    assign imm_i_sel = i_I | i_l | inst_jalr;      // jalr 的目标同样吃 I 型立即数
    wire [31:0] imm;
    assign imm = ({32{i_u}}       & imm_u)
                 | ({32{imm_i_sel}} & imm_i)
                 | ({32{inst_s}}    & imm_s)
                 | ({32{i_shamt}}   & shamt)
                 | ({32{inst_b}}    & imm_b)
                 | ({32{inst_jal}}  & imm_j);
    wire use_imm;
    assign use_imm = i_u | i_I | i_l | inst_s | i_shamt;
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

  
    wire [5:0] inst_6b;
    assign inst_6b = {inst_bgeu, inst_bltu, inst_bge, inst_blt, inst_bne, inst_beq};
    wire br_taken;
    br_alu u_br_alu (
        .inst_6b (inst_6b),
        .xrs1    (rdata1),
        .xrs2    (rdata2),
        .br_taken(br_taken)
    );

    // ============ 分支冒险:ID 级组合判定 → 冲刷 + PC 重定向 ============
    // 为什么有冒险:ID 级执行的是 if_id_inst(IF/ID 寄存器输出),而此刻 IF 已经把
    //   顺延的那条指令取回来了。分支一旦命中,那条"错取"的指令必须冲掉,同时把 pc
    //   重定向到目标 —— 本段就是干这个。
    // 为什么目标/链接值用 if_id_pc:分支自己停在 ID 级,它的 PC = if_id_pc;
    //   而 IF 级的 pc 已经领先一条(即原注释里的"差异1 / 差异2")。
    // 位置约束:本段必须排在译码 / 寄存器堆 / br_alu 之后 —— 用到的 inst_* / rdata* /
    //   br_taken 都在前面声明,Verilog 要求先声明后使用。
    //   IF/ID 的时序块排在更后面, 所以这里算出的 flush 同样满足"先声明后使用"。
    wire [31:0] pc4;
    assign pc4     = if_id_pc + 32'h4;                // 顺序后继 = jal/jalr 链接值
    // 目标复用同一个 imm(B→imm_b、J→imm_j):分支与 jal 共用一个加法器,省掉 b_pc/jal_pc 那层 mux
    wire [31:0] jalr_pc;
    assign jalr_pc = (rdata1 + imm) & ~32'h1;         // I 型:jalr rs1+imm_i,清 bit0
    wire [31:0] bj_pc;
    assign bj_pc   = inst_jalr ? jalr_pc
                     : (if_id_pc + imm);    // B/J 型:if_id_pc + 对应立即数

    // ID 级命中:分支条件成立(br_alu 组合输出)| jal | jalr
    // 注:非分支指令 inst_6b 全 0 → br_taken 必 0,可安全相或
    wire id_taken;
    assign id_taken = br_taken | inst_jal | inst_jalr;
    // 只有"ID 级真的在跑一条有效指令"时才冲刷(气泡绝不能触发重定向)
    wire flush;
    assign flush    = id_taken & if_id_valid;         // 就近声明即赋值

    assign next_pc = flush ? bj_pc : pc + 32'h4;           // 命中→重定向;否则顺序 +4

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


    wire [31:0] alu_src1;
    assign alu_src1 = inst_auipc ? if_id_pc : rdata1;   // auipc 用 ID 级指令自己的 PC
    // ALU 第二操作数:吃立即数的那五类统一选 imm,其余(R 型 / jal / jalr)用 rdata2
    wire [31:0] alu_src2;
    assign alu_src2 = use_imm ? imm : rdata2;
    wire [31:0] alu_result;
    alu u_alu (.alu_op(alu_op), .alu_src1(alu_src1), .alu_src2(alu_src2), .alu_result(alu_result));

    wire [31:0] data_sram_addr;
    wire [31:0] data_sram_wdata;
    wire [3:0]  data_sram_we;
    wire [31:0] data_sram_rdata;

    wire [1:0] st_off;
    assign st_off = alu_result[1:0];
    wire [3:0] st_we;
    assign st_we  = inst_sw ? 4'b1111
                    : inst_sh ? (st_off[1] ? 4'b1100 : 4'b0011)
                    : inst_sb ? (4'b0001 << st_off)
                    : 4'b0000;
    assign data_sram_we   = st_we & {4{if_id_valid}};   // 气泡绝不发写请求(闸门=当级 valid)
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

    
                     
    assign rf_we    = gf_we & if_id_valid;         // 气泡/被冲刷的指令不写回
    assign rf_waddr = rd;
    assign rf_wdata = i_l ? mem_result            
                    : i_j ? pc4                    
                    : alu_result;

 

    assign debug_wb_pc     = if_id_pc;   // 该沿提交的是 ID 级这条指令
    assign debug_wb_rf_we  = {4{rf_we}};
    assign debug_wb_rf_wnum = rf_waddr;
    assign debug_wb_rf_wdata = rf_wdata;
    assign debug_inst = if_id_inst;  // 该沿提交的是 ID 级这条指令

endmodule
