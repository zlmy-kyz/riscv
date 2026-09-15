module mycpu_sync (
    input  wire        clk,
    input  wire        resetn,
    output [31:0]      debug_wb_pc,
    output [3:0]       debug_wb_rf_we,
    output [4:0]       debug_wb_rf_wnum,
    output [31:0]      debug_wb_rf_wdata,
    output [31:0]      debug_inst
);

    // ================================================================================
    // 流水结构: IF | ID | EX | MEM | WB
    //   IF  : pc / inst_rom(同步读, 1 拍延迟)
    //   ID  : 译码 / 立即数 / 寄存器堆读 / 转发选择 / 分支判定 / flush / PC 重定向 / load-use 阻塞
    //   EX  : ALU → 访存地址, 组合直连 RAM 地址口; 存数数据/字节使能也在这一拍提交
    //   MEM : 消费 RAM 读数据(l_alu) → 锁进 MEM/WB
    //   WB  : 写寄存器堆 + 调试口
    // 访存时序用 doc/ROM与RAM时序处理方案总结.md 的「访存方案一」:
    //   ★ RAM 内部那个地址寄存器就是 EX/MEM 边界 —— 地址路径全程组合, 中间一个寄存器都不能有。
    //     一旦在它前面再插寄存器, 就变成方案二: 读数据掉到 WB 级、load-use 必停。
    // 转发: 方案一 —— 起点在各级结果输出处, 终点统一在 ID 级寄存器堆读出生成逻辑处。
    //   4 级下有 EX、MEM 两条路径, 带优先级 EX > MEM > 寄存器堆。
    // 排版: 按流水线顺序自上而下, 每级逻辑后面紧跟它那一级的流水寄存器(声明 + 时序块)。
    //   有 4 个信号是"先声明、后面赋值"(next_pc / flush / load_use / id_rs1,id_rs2):
    //   它们是组合反馈, 产生源在文件更下方, 前置声明才能让时序块贴着自己的寄存器放。
    // ================================================================================

    // ==================== ① IF 段 ====================
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
    // 这三个是组合反馈, 产生源在文件更下方(flush/load_use 在⑥⑪, next_pc 在⑪), 先声明后赋值
    wire flush;
    wire load_use;

    // next_pc 的赋值下移到"跳转地址 / next_pc 逻辑"处(依赖译码出的分支/跳转信号)
    // ★ load-use 冻结时地址口也必须一起冻在 pc 上。否则: pc 冻住 → pc(N+1)=pc(N),
    //   而地址口还在跟 next_pc = pc+4 跑 → ROM 锁进去的和 pc 差一条 → (pc, inst) 配对断裂。
    //   (doc/ROM与RAM时序处理方案总结.md 6.4 节第 2 条硬约束)
    assign inst_sram_addr = load_use ? pc : (valid ? next_pc : pc);
    always@(posedge clk)begin
        if(!resetn)begin
            pc <= 32'h00000000;
        end
        else if(valid) begin
            // ★ load-use 阻塞时冻结 pc: pc 与 IF/ID 必须一起冻, 只冻一个会让 (pc, inst) 配对断裂
            pc <= load_use ? pc : next_pc;
        end
    end

    // ==================== ② IF/ID 流水寄存器 = ID 级的输入 ====================
    // ★ 位置: 正好卡在 IF / ID 的交界处 —— 上面是①IF 段, 下面是③ID 段。ID/EX 同理见⑥, EX/MEM 见⑧。
    // 气泡三个来源:① 复位(!valid) ② 分支/跳转冲刷(flush) ③ load-use 阻塞(load_use,冻结而非清零)
    // 约定:气泡的唯一标志是 if_id_valid=0;指令/PC 字段只填"安全兜底值",不参与判断
    // flush / load_use 的声明在①(IF 段要用 load_use 冻结地址口), 赋值分别在⑪和⑥。
    reg [31:0] if_id_inst;
    reg [31:0] if_id_pc;
    reg if_id_valid;

    // ---------- IF/ID 时序块 ----------
    always@(posedge clk)begin
        if(!valid)begin
            if_id_inst <= 32'h00000000;
            if_id_pc <= 32'h00000000;
            if_id_valid <= 1'b0;
        end
        else if(load_use)begin             // ★ load-use: 冻结(不是清零)—— 消费者留在 ID 再等一拍
            if_id_inst <= if_id_inst;
            if_id_pc <= if_id_pc;
            if_id_valid <= if_id_valid;
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

    // ==================== ③ 译码 / 立即数(ID 级) ====================
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

    // ==================== ④ 寄存器堆(ID 级读, MEM 级写) ====================
    // rf_we / rf_waddr / rf_wdata 在这里只声明, 赋值在⑨(MEM 段) —— 沿用 wmem/gf_we 的写法。
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

    // ==================== ⑤ ALU 操作码(译码产物, ID 级算完锁进 ID/EX) ====================
    wire [10:0] alu_op;
    assign alu_op[0]  = inst_add | inst_auipc | inst_addi |
                        inst_lw | inst_lh | inst_lb | inst_lhu | inst_lbu |
                        inst_sw | inst_sh | inst_sb |
                        inst_jal | inst_jalr;         // 跳转的链接值 = PC+4, 复用这个加法器
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

    // ==================== ⑥ ID/EX 流水寄存器 = EX 级的输入 ====================
    // ★ 位置: 正好卡在 ID / EX 的交界处 —— 上面是 ID 级逻辑(译码 / 立即数 / 寄存器堆 / alu_op),
    //   下面是 EX 级逻辑。IF/ID 同理(见②), EX/MEM 同理(见⑧)。
    // 原则: EX 里不该再出现任何 inst_* / imm / if_id_* —— 译码和操作数选择全部在 ID 做完,
    //   只把"结果"锁进来。所以 src1/src2 存的是已经选好的最终操作数, 不是 raw rdata/imm。
    // src1/src2 要吃转发值, 而转发源在⑦EX 和⑨MEM —— id_rs1/id_rs2 先声明、到⑩转发段再赋值。
    wire [31:0] id_rs1;
    wire [31:0] id_rs2;

    // 气泡约定沿用 IF/ID:唯一标志 id_ex_valid=0,且控制字全部清 0(不依赖 NOP 兜底值)。
    reg [31:0] id_ex_pc;          // 提交给 debug_wb_pc(经 EX/MEM 传下去)
    reg [31:0] id_ex_inst;        // 提交给 debug_inst
    reg [31:0] id_ex_src1;        // 已在 ID 选好: auipc/jal/jalr 取 if_id_pc, 其余取转发后 rs1
    reg [31:0] id_ex_src2;        // 已在 ID 选好: jal/jalr 取 4, 吃立即数类取 imm, 其余取转发后 rs2
    reg [31:0] id_ex_rs2_data;    // ★ 存数数据: 转发后的原始 rs2(不是 src2 —— 存数时 src2 是地址偏移)
    reg [10:0] id_ex_alu_op;      // ALU 唯一需要的译码信息(含 jal/jalr 的 PC+4)
    reg [ 4:0] id_ex_rd;          // RF 写口 + 转发比较的源
    reg [ 4:0] id_ex_inst_5l;     // l_alu 类型选择, 位序 {lw,lh,lhu,lb,lbu}
    reg        id_ex_i_l;         // load 标志: 选 MEM 的写回源 + 屏蔽 EX→ID 前递
    reg        id_ex_wmem;        // data_ram.wr_en
    reg        id_ex_sw;          // 存数类型: 与 alu_result[1:0] 合成字节掩码
    reg        id_ex_sh;
    reg        id_ex_sb;
    reg        id_ex_gf_we;       // = ~wmem & ~inst_b
    reg        id_ex_valid;       // 气泡唯一标志

    // ---------- load-use 阻塞判据 ----------
    // EX 里是 load、而 ID 这条要用它的结果 —— 此时 load 的数据还在 RAM 里没出来(下一拍才到 MEM),
    //   所以 EX 无法前递, 只能把 ID 这条按在译码级等一拍(下一拍从 MEM 前递)。
    // 这就是书本说的"引入前递之后, 译码级唯一的阻塞条件"。
    // 注意这里是按 rs1/rs2 字段直接比, 不看该指令是否真的读这两个字段 —— 假命中只会多停一拍,
    //   不会算错(比如 lui 的 rs1 字段其实装的是立即数)。
    assign load_use = id_ex_valid & id_ex_i_l & id_ex_gf_we & (id_ex_rd != 5'd0) &
                      ((id_ex_rd == rs1) | (id_ex_rd == rs2));

    // ---------- ID/EX 时序块 ----------
    // 优先级: !valid > load_use(插气泡) > if_id_valid(正常) > 气泡
    // ★ 这里绝不能出现 flush: 分支命中时 EX 里那条比分支更老、是合法取来的, 必须让它做完。
    //   被冲刷的指令压根进不了 ID(if_id_valid=0), 自然也就进不了 ID/EX ——
    //   气泡是"顺着 valid 流下来"的, 不是"被 flush 擦掉"的。
    always@(posedge clk)begin
        if(!valid)begin
            id_ex_valid    <= 1'b0;
            id_ex_pc       <= 32'hFFFF_FFFF;                   // 哨兵
            id_ex_inst     <= 32'h00000000;
            id_ex_src1     <= 32'h00000000;
            id_ex_src2     <= 32'h00000000;
            id_ex_rs2_data <= 32'h00000000;
            id_ex_alu_op   <= 11'b0;
            id_ex_rd       <= 5'd0;
            id_ex_inst_5l  <= 5'b0;
            id_ex_i_l      <= 1'b0;
            id_ex_wmem     <= 1'b0;
            id_ex_sw       <= 1'b0;
            id_ex_sh       <= 1'b0;
            id_ex_sb       <= 1'b0;
            id_ex_gf_we    <= 1'b0;
        end
        else if(load_use)begin
            // ★ 消费者留在 ID 再等一拍, EX 这一拍空出来插气泡(它的操作数此刻还不正确)
            id_ex_valid    <= 1'b0;
            id_ex_pc       <= 32'hFFFF_FFFF;
            id_ex_inst     <= 32'h00000000;
            id_ex_src1     <= 32'h00000000;
            id_ex_src2     <= 32'h00000000;
            id_ex_rs2_data <= 32'h00000000;
            id_ex_alu_op   <= 11'b0;
            id_ex_rd       <= 5'd0;
            id_ex_inst_5l  <= 5'b0;
            id_ex_i_l      <= 1'b0;
            id_ex_wmem     <= 1'b0;
            id_ex_sw       <= 1'b0;
            id_ex_sh       <= 1'b0;
            id_ex_sb       <= 1'b0;
            id_ex_gf_we    <= 1'b0;
        end
        else if(if_id_valid)begin
            id_ex_valid    <= 1'b1;
            id_ex_pc       <= if_id_pc;
            id_ex_inst     <= if_id_inst;
            id_ex_src1     <= (inst_auipc | i_j) ? if_id_pc : id_rs1;         // ★ 转发值
            id_ex_src2     <= i_j ? 32'd4 : (use_imm ? imm : id_rs2);         // ★ 转发值
            id_ex_rs2_data <= id_rs2;                                         // ★ 原始 rs2
            id_ex_alu_op   <= alu_op;
            id_ex_rd       <= rd;
            id_ex_inst_5l  <= inst_5l;
            id_ex_i_l      <= i_l;
            id_ex_wmem     <= wmem;
            id_ex_sw       <= inst_sw;
            id_ex_sh       <= inst_sh;
            id_ex_sb       <= inst_sb;
            id_ex_gf_we    <= gf_we;
        end
        else begin
            // 气泡: 控制字全部清 0 —— EX 级任何 enable 都不会误触发。
            // (不依赖 if_id_inst=0x0000_0013 那个 NOP 兜底: NOP 的 gf_we 其实是 1,
            //  只是靠 rd=0 才没闯祸; 清 0 之后天然安全, 不再靠这一条。)
            id_ex_valid    <= 1'b0;
            id_ex_pc       <= 32'hFFFF_FFFF;
            id_ex_inst     <= 32'h00000000;
            id_ex_src1     <= 32'h00000000;
            id_ex_src2     <= 32'h00000000;
            id_ex_rs2_data <= 32'h00000000;
            id_ex_alu_op   <= 11'b0;
            id_ex_rd       <= 5'd0;
            id_ex_inst_5l  <= 5'b0;
            id_ex_i_l      <= 1'b0;
            id_ex_wmem     <= 1'b0;
            id_ex_sw       <= 1'b0;
            id_ex_sh       <= 1'b0;
            id_ex_sb       <= 1'b0;
            id_ex_gf_we    <= 1'b0;
        end
    end

    // ==================== ⑦ EX 段:ALU + 访存地址发射 ====================
    wire [31:0] alu_result;
    alu u_alu (.alu_op(id_ex_alu_op), .alu_src1(id_ex_src1),
               .alu_src2(id_ex_src2), .alu_result(alu_result));

    wire [31:0] data_sram_addr;
    wire [31:0] data_sram_wdata;
    wire [3:0]  data_sram_we;
    wire [31:0] data_sram_rdata;

    // 存数路径: 字节偏移只有算完地址才知道, 所以掩码只能在 EX 级合成
    //   (ID 级只能带"是 sw 还是 sh 还是 sb"这个类型过来)
    wire [1:0] st_off;
    assign st_off = alu_result[1:0];
    wire [3:0] st_we;
    assign st_we  = id_ex_sw ? 4'b1111
                    : id_ex_sh ? (st_off[1] ? 4'b1100 : 4'b0011)
                    : id_ex_sb ? (4'b0001 << st_off)
                    : 4'b0000;
    // ★★★ 访存方案一的三条硬约束, 一条都不能破 ★★★
    //   ① 地址路径全程组合: alu_result → RAM addr 口, 中间不夹任何寄存器。
    //      RAM 内部那个地址寄存器就充当 EX/MEM 边界, 读数据下一拍(MEM)整拍有效。
    //   ② wr_en / wr_data / 字节使能必须与地址【同拍】到 RAM 口 —— store 在 EX/MEM 沿就提交完了。
    //      它们绝不能跟着进 EX/MEM 寄存器, 否则会晚一拍、把数据写到下一个地址上。
    //   ③ wr_en 必须与当级 valid 相与 —— 被冲刷/气泡的指令绝不能发出写请求。
    assign data_sram_we    = st_we & {4{id_ex_valid}};
    assign data_sram_addr  = alu_result;
    assign data_sram_wdata = id_ex_rs2_data << {2'b00, alu_result[1:0], 3'b000};   // ★ 原始 rs2

    data_ram the_instance_name (
        .wr_data(data_sram_wdata),          // input [31:0]
        .addr(data_sram_addr[11:2]),        // input [9:0]: 丢低 2 位, 只有 10 位, 越界会静默回绕
        .wr_en(id_ex_wmem & id_ex_valid),   // input: 气泡绝不发写请求
        .wr_byte_en(data_sram_we),          // input [3:0]
        .clk(clk),                          // input
        .rst(~resetn),                      // input
        .rd_data(data_sram_rdata)           // output [31:0]
    );

    // EX 这一拍能前递/写回的值: 只有 alu_result。
    //   ★ load 在 EX 这一拍【没有】可用数据 —— 它的数据要下一拍才从 RAM 出来。
    //     所以 EX→ID 前递必须用 id_ex_i_l 屏蔽掉, 这就是 load-use 阻塞存在的原因。
    wire [31:0] ex_wb_data;
    assign ex_wb_data = alu_result;

    // ==================== ⑧ EX/MEM 流水寄存器 = MEM 级的输入 ====================
    // ★ 位置: 正好卡在 EX / MEM 的交界处。
    // 说明: 地址/写数据/写使能【不在】这里 —— 它们已经组合送到 RAM 口了(见⑦)。
    //   本寄存器装的是"下一拍写回要用什么"以及 debug 相位对齐。
    // 气泡约定: ex_mem_valid=0。这里没有 flush(气泡顺 valid 流下来)。
    reg [31:0] ex_mem_alu_result;  // 非 load 的写回值; load 时它低 2 位当 l_alu 的 sel_addr
    reg [31:0] ex_mem_pc;          // debug_wb_pc
    reg [31:0] ex_mem_inst;        // debug_inst
    reg [ 4:0] ex_mem_rd;          // RF 写口 + 转发比较的源
    reg [ 4:0] ex_mem_inst_5l;     // l_alu 类型选择
    reg        ex_mem_i_l;         // 选 MEM 的写回源(mem_result / alu_result)
    reg        ex_mem_gf_we;       // 写回使能
    reg        ex_mem_valid;       // 气泡唯一标志

    // ---------- EX/MEM 时序块 ----------
    always@(posedge clk)begin
        if(!valid)begin
            ex_mem_valid      <= 1'b0;
            ex_mem_alu_result <= 32'h00000000;
            ex_mem_pc         <= 32'hFFFF_FFFF;                // 哨兵
            ex_mem_inst       <= 32'h00000000;
            ex_mem_rd         <= 5'd0;
            ex_mem_inst_5l    <= 5'b0;
            ex_mem_i_l        <= 1'b0;
            ex_mem_gf_we      <= 1'b0;
        end
        else if(id_ex_valid)begin
            ex_mem_valid      <= 1'b1;
            ex_mem_alu_result <= alu_result;
            ex_mem_pc         <= id_ex_pc;
            ex_mem_inst       <= id_ex_inst;
            ex_mem_rd         <= id_ex_rd;
            ex_mem_inst_5l    <= id_ex_inst_5l;
            ex_mem_i_l        <= id_ex_i_l;
            ex_mem_gf_we      <= id_ex_gf_we;
        end
        else begin
            ex_mem_valid      <= 1'b0;
            ex_mem_alu_result <= 32'h00000000;
            ex_mem_pc         <= 32'hFFFF_FFFF;
            ex_mem_inst       <= 32'h00000000;
            ex_mem_rd         <= 5'd0;
            ex_mem_inst_5l    <= 5'b0;
            ex_mem_i_l        <= 1'b0;
            ex_mem_gf_we      <= 1'b0;
        end
    end

    // ==================== ⑨ MEM 段:消费 RAM 读数据 ====================
    // 这一拍 data_sram_rdata = mem[EX 那拍 addr 口上的地址] —— 正是本条指令要的数据。
    //   (写周期 NORMAL_WRITE 下 rd_data 保持上个地址的值, 但那种情况 ex_mem_i_l=0,
    //    不会被选进写回, 所以不需要额外的 mem_rvalid 屏蔽。)
    // ★ l_alu 必须留在 MEM:载入数据的字节/半字抽取要吃 data_sram_rdata, 而它只在 MEM
    //   这一拍有效。抽完把结果锁进 MEM/WB —— 到了 WB 再选就晚了, 那时总线上已经是
    //   下一条指令地址对应的数据了。
    wire [31:0] mem_result;
    l_alu u_l_alu (
        .sel_addr(ex_mem_alu_result[1:0]),
        .inst_5l(ex_mem_inst_5l),
        .data_sram_rdata(data_sram_rdata),
        .mem_result(mem_result)
    );

    // MEM 这一级"将要写回的结果"—— 也是 MEM→ID 前递的起点
    wire [31:0] mem_fwd_data;
    assign mem_fwd_data = ex_mem_i_l ? mem_result : ex_mem_alu_result;

    // ==================== ⑩ MEM/WB 流水寄存器 = WB 级的输入 ====================
    // ★ 位置: 正好卡在 MEM / WB 的交界处。
    // ★ 内存值【可以】直接锁进来 —— 因为用的是访存方案一: 地址在 EX 那拍组合打到 RAM 口,
    //   RAM 内部寄存器在 EX/MEM 沿锁存它, 于是读数据在整个 MEM 拍都稳, MEM/WB 沿采它是安全的。
    //   (doc 里"内存值必须绕过 MEM/WB"那条警告是给方案二写的 —— 那种接法数据要到 WB 才有效,
    //    在 MEM/WB 沿锁进去的是上一个地址的旧值。本设计不是那种接法。)
    // 反过来, 到了 WB 级 data_sram_rdata 已经变成下一条指令地址对应的数据, 所以写回值
    //   必须来自这里, 不能再回头去组合选择 RAM 输出。
    // 气泡约定: mem_wb_valid=0。这里没有 flush(气泡顺 valid 流下来)。
    reg [31:0] mem_wb_wdata;       // 最终写回值(load 走 l_alu, 其余走 ALU 结果)
    reg [31:0] mem_wb_pc;          // debug_wb_pc
    reg [31:0] mem_wb_inst;        // debug_inst
    reg [ 4:0] mem_wb_rd;          // RF 写口 + 前递比较的源
    reg        mem_wb_gf_we;       // 写回使能
    reg        mem_wb_valid;       // 气泡唯一标志

    // ---------- MEM/WB 时序块 ----------
    always@(posedge clk)begin
        if(!valid)begin
            mem_wb_valid   <= 1'b0;
            mem_wb_wdata   <= 32'h00000000;
            mem_wb_pc      <= 32'hFFFF_FFFF;                   // 哨兵
            mem_wb_inst    <= 32'h00000000;
            mem_wb_rd      <= 5'd0;
            mem_wb_gf_we   <= 1'b0;
        end
        else if(ex_mem_valid)begin
            mem_wb_valid   <= 1'b1;
            mem_wb_wdata   <= mem_fwd_data;
            mem_wb_pc      <= ex_mem_pc;
            mem_wb_inst    <= ex_mem_inst;
            mem_wb_rd      <= ex_mem_rd;
            mem_wb_gf_we   <= ex_mem_gf_we;
        end
        else begin
            mem_wb_valid   <= 1'b0;
            mem_wb_wdata   <= 32'h00000000;
            mem_wb_pc      <= 32'hFFFF_FFFF;
            mem_wb_inst    <= 32'h00000000;
            mem_wb_rd      <= 5'd0;
            mem_wb_gf_we   <= 1'b0;
        end
    end

    // ==================== ⑪ WB 段:写寄存器堆 + 调试口 ====================
    // 位置约束: rf_we/rf_waddr/rf_wdata 在④只声明, 到这里才赋值 —— 沿用 wmem/gf_we 的写法。
    assign rf_we    = mem_wb_valid & mem_wb_gf_we;   // 气泡 / 分支 / 存数 都不写回
    assign rf_waddr = mem_wb_rd;
    assign rf_wdata = mem_wb_wdata;

    assign debug_wb_pc       = mem_wb_pc;
    assign debug_wb_rf_we    = {4{rf_we}};
    assign debug_wb_rf_wnum  = mem_wb_rd;
    assign debug_wb_rf_wdata = mem_wb_wdata;
    assign debug_inst        = mem_wb_inst;

    // ==================== ⑫ EX→ID / MEM→ID / WB→ID 转发(方案一) ====================
    // 起点: 各级"将要写回的结果输出处"—— EX 是 alu_result, MEM 是 mem_fwd_data,
    //       WB 是 mem_wb_wdata(已经锁进 MEM/WB 的那个值)。
    // 终点: 统一在 ID 级寄存器堆读出生成逻辑处(下面这两个 mux), 所有消费者都在这一处取数。
    //   —— 这正是书里说的"方案一: 所有前递路径终点一致, 由前递结果生成正确源操作数的
    //      逻辑可以在一处集中处理"。分支/jalr 留在 ID 级也正靠这一点: 它们的源操作数
    //      同样从这个 mux 出来, 不必阻塞等待写回。
    // 优先级: EX > MEM > WB > 寄存器堆 —— 越靠前越年轻, 它才是最后写进寄存器的值。
    //   书里的判优例子: add r4,r1,r1 / add r4,r2,r2 / add r4,r3,r3 三条都在飞时,
    //   最下面那条 sub r6,r5,r4 必须选 EX 前递过来的结果。
    //   本设计里真实发生过的同拍双命中: sw x2,0(x1) 同时要 x1(来自 MEM 里的 addi)
    //   和 x2(来自 EX 里的 addi) —— 优先级写反就会取错。
    // ★★ 门控三件套 + 一条屏蔽:
    //   valid  —— 气泡不能前递
    //   gf_we  —— 分支/存数不写寄存器, 前递它们等于前递垃圾
    //   rd != 0 —— 否则 add x0,x1,x2 这类也会命中, 消费者拿到的不是 0 而是 ALU 结果
    //   ~i_l   —— EX 里是 load 时数据还没出来, 绝对不能前递(这就是 load-use 阻塞的由来)
    wire fwd_ex_en;
    assign fwd_ex_en  = id_ex_valid & id_ex_gf_we & ~id_ex_i_l;
    wire id_fwd_ex1;
    assign id_fwd_ex1 = fwd_ex_en & (id_ex_rd != 5'd0) & (id_ex_rd == rs1);
    wire id_fwd_ex2;
    assign id_fwd_ex2 = fwd_ex_en & (id_ex_rd != 5'd0) & (id_ex_rd == rs2);

    // MEM 这一条不需要 ~i_l 屏蔽 —— 到了 MEM 级, load 的数据已经在 mem_fwd_data 里了
    wire fwd_mem_en;
    assign fwd_mem_en  = ex_mem_valid & ex_mem_gf_we;
    wire id_fwd_mem1;
    assign id_fwd_mem1 = fwd_mem_en & (ex_mem_rd != 5'd0) & (ex_mem_rd == rs1);
    wire id_fwd_mem2;
    assign id_fwd_mem2 = fwd_mem_en & (ex_mem_rd != 5'd0) & (ex_mem_rd == rs2);

    wire fwd_wb_en;
    assign fwd_wb_en  = mem_wb_valid & mem_wb_gf_we;
    wire id_fwd_wb1;
    assign id_fwd_wb1 = fwd_wb_en & (mem_wb_rd != 5'd0) & (mem_wb_rd == rs1);
    wire id_fwd_wb2;
    assign id_fwd_wb2 = fwd_wb_en & (mem_wb_rd != 5'd0) & (mem_wb_rd == rs2);

    assign id_rs1 = id_fwd_ex1  ? ex_wb_data   :
                    id_fwd_mem1 ? mem_fwd_data :
                    id_fwd_wb1  ? mem_wb_wdata : rdata1;
    assign id_rs2 = id_fwd_ex2  ? ex_wb_data   :
                    id_fwd_mem2 ? mem_fwd_data :
                    id_fwd_wb2  ? mem_wb_wdata : rdata2;

    // ==================== ⑬ ID 级分支 / 跳转 ====================
    // 分支判定留在 ID: 下沉到 EX 会让分支惩罚从 1 拍涨到 2 拍。
    // 位置约束:本段排在④⑩之后 —— br_alu 要吃转发后的 id_rs1/id_rs2。
    // 注意: jal/jalr 的链接值(PC+4)不在这里算 —— 已交给 EX 的 ALU。
    // 目标复用同一个 imm(B→imm_b、J→imm_j):分支与 jal 共用一个加法器。
    wire [5:0] inst_6b;
    assign inst_6b = {inst_bgeu, inst_bltu, inst_bge, inst_blt, inst_bne, inst_beq};
    wire br_taken;
    br_alu u_br_alu (
        .inst_6b (inst_6b),
        .xrs1    (id_rs1),          // ★ 必须用转发后的值
        .xrs2    (id_rs2),          // ★
        .br_taken(br_taken)
    );

    wire [31:0] jalr_pc;
    assign jalr_pc = (id_rs1 + imm) & ~32'h1;         // I 型:jalr rs1+imm_i,清 bit0  ★ 转发后的 rs1
    wire [31:0] bj_pc;
    assign bj_pc   = inst_jalr ? jalr_pc
                     : (if_id_pc + imm);    // B/J 型:if_id_pc + 对应立即数

    // ID 级命中:分支条件成立(br_alu 组合输出)| jal | jalr
    // 注:非分支指令 inst_6b 全 0 → br_taken 必 0,可安全相或
    wire id_taken;
    assign id_taken = br_taken | inst_jal | inst_jalr;
    // 只有"ID 级真的在跑一条有效指令"时才冲刷(气泡绝不能触发重定向)
    // ★ 还要排除 load-use 那一拍: 那时 ID 的操作数还是旧的, br_taken 不可信。
    //   被门控掉的分支会在下一拍(已拿到前递值)重新判定, 不会丢。
    assign flush    = id_taken & if_id_valid & ~load_use;

    assign next_pc = flush ? bj_pc : pc + 32'h4;           // 命中→重定向;否则顺序 +4

endmodule
