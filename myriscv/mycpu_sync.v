`include "csr_defs.vh"

module mycpu_sync #(
    // 兼容现有地址 0 测试；运行链接在 0x8000_0000 的 riscv-tests 时覆写此参数。
    parameter [31:0] RESET_PC = 32'h0000_0000
) (
    input  wire        clk,
    input  wire        resetn,
    // 均为 clk 域同步电平；异步外设须在 SoC 边界同步，窄脉冲须保持。
    input  wire        irq_external,
    input  wire        irq_software,
    input  wire        irq_timer,
    // 只读指令请求/响应总线；请求与响应可相隔任意拍。
    output wire        inst_req_valid,
    output wire [31:0] inst_req_addr,
    input  wire        inst_req_ready,
    input  wire        inst_rsp_valid,
    input  wire [31:0] inst_rsp_rdata,
    input  wire        inst_rsp_error,
    // 数据类 SRAM 总线：请求接受与响应完成相互独立，首版最多一笔未完成事务。
    output wire        data_req_valid,
    output wire        data_req_write,
    output wire [ 1:0] data_req_size,
    output wire [31:0] data_req_addr,
    output wire [31:0] data_req_wdata,
    output wire [ 3:0] data_req_wstrb,
    input  wire        data_req_ready,
    input  wire        data_rsp_valid,
    input  wire [31:0] data_rsp_rdata,
    input  wire        data_rsp_error,
    output [31:0]      debug_wb_pc,
    output [3:0]       debug_wb_rf_we,
    output [4:0]       debug_wb_rf_wnum,
    output [31:0]      debug_wb_rf_wdata,
    output [31:0]      debug_inst
);

    // ================================================================================
    // 流水结构: IF | ID | EX | MEM | WB
    //   IF  : 指令请求/响应、顺序预取、响应缓冲与错路响应丢弃
    //   ID  : 译码 / 立即数 / 寄存器堆读 / 转发选择 / 分支判定 / PC 重定向 / load-use 阻塞
    //   EX  : ALU → 访存地址；通过 valid/ready 提交 load/store 请求
    //   MEM : 保持事务直到 rsp_valid；load 经 l_alu 后锁进 MEM/WB
    //   WB  : 写寄存器堆 + 调试口
    // 指令侧和数据侧都采用类 SRAM 请求/响应总线；每侧首版各自单 outstanding。
    // BRAM adapter 将它们转换为当前同步存储器；以后可替换为互连、Cache 或 DDR3 桥。
    // 转发: 方案一 —— 起点在各级结果输出处, 终点统一在 ID 级寄存器堆读出生成逻辑处。
    //   4 级下有 EX、MEM 两条路径, 带优先级 EX > MEM > 寄存器堆。
    // 排版: 所有内部信号统一在模块前部声明；后面的逻辑仍按 IF→ID→EX→MEM→WB 排列。
    //   组合信号先声明、后用 assign 赋值，各级流水寄存器的时序块保留在所属流水级。
    // ================================================================================

    // ==================== 集中信号声明 ====================
    // 全部 wire/reg 在任何实例、always、assign 之前声明，兼容严格 Verilog 编译器。
    localparam [2:0] FLOW_RUN = 3'd0,
                     FLOW_SERIAL_DRAIN = 3'd1,
                     FLOW_SERIAL_RUN = 3'd2,
                     FLOW_IRQ_CHECK = 3'd3,
                     FLOW_IRQ_DRAIN = 3'd4;

    // IF、全局流水控制与中断仲裁
    reg fetch_valid;
    reg [31:0] pc;              // 下一笔取指请求的字节地址
    reg        inst_pending;
    reg [31:0] inst_pending_pc;
    reg        inst_pending_drop;
    reg        inst_buffer_valid;
    reg [31:0] inst_buffer_pc;
    reg [31:0] inst_buffer_data;
    reg        inst_buffer_error;
    wire       inst_req_fire;
    wire       inst_response_good;
    wire       inst_if_id_accept;
    wire       inst_buffer_pop;
    wire       inst_turnover_safe;
    wire load_use;
    wire frontend_hold, bubble_id_ex, id_fire;
    wire data_pipeline_stall;
    wire kill_if_id, kill_id_ex, kill_ex_mem, kill_mem_wb;
    wire branch_redirect, trap_redirect_req, mret_redirect_req;
    wire redirect_valid;
    wire [31:0] redirect_pc;
    wire serial_issue, serial_candidate, serial_done;
    wire fault_inflight;
    wire sync_trap_event;
    wire normal_retire;
    wire id_taken;
    wire pipeline_empty;
    wire wb_csr_illegal;
    reg  ex_mem_valid;
    reg  ex_mem_exc_valid;
    reg  mem_wb_valid;
    reg  mem_wb_exc_valid;
    reg [31:0] arch_next_pc;
    wire mem_load_request, mem_store_request;
    wire irq_candidate, irq_take;
    wire [4:0] irq_cause;
    wire [31:0] irq_eligible;
    reg [2:0] flow_state;

    // IF/ID 流水寄存器与 ID 级译码
    reg [31:0] if_id_inst;
    reg [31:0] if_id_pc;
    reg if_id_valid;
    reg if_id_access_fault;
    wire [31:0] inst;
    wire [6:0] opcode;
    wire [2:0] funct3;
    wire [6:0] funct7;
    wire [4:0] rd;
    wire [4:0] rs1;
    wire [4:0] rs2;
    wire [11:0] csr_addr;
    wire [31:0] shamt;
    wire inst_add;
    wire inst_addi;
    wire inst_sub;
    wire inst_lui;
    wire inst_auipc;
    wire inst_and;
    wire inst_andi;
    wire inst_or;
    wire inst_ori;
    wire inst_xor;
    wire inst_xori;
    wire inst_sll;
    wire inst_slli;
    wire inst_slti;
    wire inst_slt;
    wire inst_srli;
    wire inst_srl;
    wire inst_sra;
    wire inst_srai;
    wire inst_sltu;
    wire inst_sltiu;
    wire inst_jalr;
    wire inst_jal;
    wire inst_bne;
    wire inst_beq;
    wire inst_blt;
    wire inst_bge;
    wire inst_bltu;
    wire inst_bgeu;
    wire inst_lw;
    wire inst_lh;
    wire inst_lb;
    wire inst_lhu;
    wire inst_lbu;
    wire inst_sw;
    wire inst_sh;
    wire inst_sb;
    wire inst_csrrw;
    wire inst_csrrs;
    wire inst_csrrc;
    wire inst_csrrwi;
    wire inst_csrrsi;
    wire inst_csrrci;
    wire inst_fence;
    wire inst_wfi;
    wire csr_inst;
    wire csr_imm_form;
    wire csr_read_req;
    wire csr_write_req;
    wire [31:0] csr_src;
    wire i_j;
    wire i_l;
    wire [4:0] inst_5l;
    wire i_u;
    wire i_shamt;
    wire i_I;
    wire i_R;
    wire inst_s;
    wire inst_b;
    wire [31:0] imm_u;
    wire [31:0] imm_i;
    wire [31:0] imm_s;
    wire [31:0] imm_b;
    wire [31:0] imm_j;
    wire [4:0] zimm;
    wire imm_i_sel;
    wire [31:0] imm;
    wire use_imm;
    wire wmem;
    wire gf_we;
    wire [31:0] rdata1, rdata2;
    wire        rf_we;
    wire [4:0]  rf_waddr;
    wire [31:0] rf_wdata;
    wire [10:0] alu_op;
    wire [31:0] id_rs1;
    wire [31:0] id_rs2;

    // ID/EX 流水寄存器与异常信息
    reg [31:0] id_ex_pc;          // 提交给 debug_wb_pc(经 EX/MEM 传下去)
    reg [31:0] id_ex_next_pc;     // 本条指令正常完成后的实际后继 PC
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
    reg        id_ex_gf_we;       // 已实现的普通指令和 CSR 指令写 GPR 许可
    reg        id_ex_valid;       // 气泡唯一标志
    reg        id_ex_serial;      // 串行项标记，随指令走到 WB 后释放前端
    reg        id_ex_csr;
    reg [11:0] id_ex_csr_addr;
    reg [1:0]  id_ex_csr_op;       // funct3[1:0]：01 写、10 置位、11 清位
    reg [31:0] id_ex_csr_src;
    reg        id_ex_csr_read_en;
    reg        id_ex_csr_write_intent;
    reg        id_ex_mret;
    reg        id_ex_exc_valid;
    reg [4:0]  id_ex_exc_cause;
    reg [31:0] id_ex_exc_tval;
    wire        inst_ecall;
    wire        inst_ebreak;
    wire        inst_mret;
    wire        id_inst_supported;
    wire        id_illegal_inst;
    wire        id_target_misaligned;
    wire [31:0] bj_pc;
    wire        id_exc_valid;
    wire [4:0]  id_exc_cause;
    wire [31:0] id_exc_tval;
    wire uses_rs1;
    wire uses_rs2;

    // EX 级、数据存储器接口与 EX/MEM 流水寄存器
    wire [31:0] alu_result;
    wire ex_access_half;
    wire ex_access_word;
    wire ex_data_misaligned;
    wire        ex_exc_valid;
    wire [4:0]  ex_exc_cause;
    wire [31:0] ex_exc_tval;
    wire older_fault_for_ex;
    wire ex_store_commit;
    wire id_ex_needs_bus;
    wire data_req_fire;
    wire ex_mem_bus_error;
    wire ex_mem_complete;
    wire ex_mem_ready;
    wire id_ex_can_advance;
    wire id_ex_advance;
    wire [1:0] st_off;
    wire [3:0] st_we;
    wire [31:0] ex_wb_data;
    reg [31:0] ex_mem_alu_result;  // 非 load 的写回值; load 时它低 2 位当 l_alu 的 sel_addr
    reg [31:0] ex_mem_pc;          // debug_wb_pc
    reg [31:0] ex_mem_next_pc;
    reg [31:0] ex_mem_inst;        // debug_inst
    reg [ 4:0] ex_mem_rd;          // RF 写口 + 转发比较的源
    reg [ 4:0] ex_mem_inst_5l;     // l_alu 类型选择
    reg        ex_mem_i_l;         // 选 MEM 的写回源(mem_result / alu_result)
    reg        ex_mem_gf_we;       // 写回使能
    reg        ex_mem_mem_pending; // load/store 请求已接受，MEM 正等待完成响应
    reg        ex_mem_mem_write;   // 1=store，0=load；用于总线错误异常原因
    reg        ex_mem_serial;
    reg        ex_mem_csr;
    reg [11:0] ex_mem_csr_addr;
    reg [1:0]  ex_mem_csr_op;
    reg [31:0] ex_mem_csr_src;
    reg        ex_mem_csr_read_en;
    reg        ex_mem_csr_write_intent;
    reg        ex_mem_mret;
    reg [4:0]  ex_mem_exc_cause;
    reg [31:0] ex_mem_exc_tval;

    // MEM 级与 MEM/WB 流水寄存器
    wire [31:0] mem_result;
    wire [31:0] mem_fwd_data;
    reg [31:0] mem_wb_wdata;       // 最终写回值(load 走 l_alu, 其余走 ALU 结果)
    reg [31:0] mem_wb_pc;          // debug_wb_pc
    reg [31:0] mem_wb_next_pc;
    reg [31:0] mem_wb_inst;        // debug_inst
    reg [ 4:0] mem_wb_rd;          // RF 写口 + 前递比较的源
    reg        mem_wb_gf_we;       // 写回使能
    reg        mem_wb_serial;
    reg        mem_wb_csr;
    reg [11:0] mem_wb_csr_addr;
    reg [1:0]  mem_wb_csr_op;
    reg [31:0] mem_wb_csr_src;
    reg        mem_wb_csr_read_en;
    reg        mem_wb_csr_write_intent;
    reg        mem_wb_mret;
    reg [4:0]  mem_wb_exc_cause;
    reg [31:0] mem_wb_exc_tval;

    // WB、CSR、异常入口与中断状态
    wire wb_csr_valid;
    wire wb_csr_read_en;
    wire wb_csr_write_intent;
    wire [31:0] csr_rdata;
    wire [31:0] csr_wdata;
    wire csr_exists, csr_readonly_addr, csr_access_illegal;
    wire [4:0] wb_trap_cause;
    wire [31:0] wb_trap_tval;
    wire csr_commit;
    wire mret_commit;
    wire [31:0] csr_trap_target, csr_mret_target;
    wire [31:0] csr_irq_pending, csr_irq_enable;
    wire csr_irq_global_enable;

    // 前递、分支与末端控制逻辑
    wire fwd_ex_en;
    wire id_fwd_ex1;
    wire id_fwd_ex2;
    wire fwd_mem_en;
    wire id_fwd_mem1;
    wire id_fwd_mem2;
    wire fwd_wb_en;
    wire id_fwd_wb1;
    wire id_fwd_wb2;
    wire [5:0] inst_6b;
    wire br_taken;
    wire [31:0] jalr_pc;
    wire serial_csr;
    wire serial_system;
    wire serial_fence;
    wire [31:0] trap_redirect_target;
    wire [31:0] mret_redirect_target;

    // ==================== ① IF 段 ====================
    // pc 始终指向下一笔尚未接受的请求。已接受请求的 PC 单独锁在 pending_pc，
    // 因而响应延迟、前端暂停或分支重定向都不会破坏 (PC, instruction) 配对。
    always @(posedge clk) begin
        if (!resetn) fetch_valid <= 1'b0;
        else         fetch_valid <= 1'b1;
    end

    // IF/ID 能在本拍装入新指令：当前 ID 未被保持，且没有冲刷事件。
    assign inst_if_id_accept = !frontend_hold && !kill_if_id;
    assign inst_buffer_pop = inst_buffer_valid && inst_if_id_accept;
    assign inst_response_good = inst_pending && inst_rsp_valid &&
                                !inst_pending_drop && !redirect_valid;

    // 一拍 ROM 响应时允许“旧响应完成 + 新请求接受”同沿发生；如果旧响应
    // 需要进入缓冲而不是 IF/ID，则不能同时再发请求，以免下一响应溢出。
    assign inst_turnover_safe = !inst_pending ||
                                (inst_rsp_valid &&
                                 (inst_pending_drop || inst_if_id_accept));
    assign inst_req_valid = resetn && fetch_valid && !redirect_valid &&
                            inst_turnover_safe &&
                            (!inst_buffer_valid || inst_buffer_pop);
    assign inst_req_addr = pc;
    assign inst_req_fire = inst_req_valid && inst_req_ready;

    always @(posedge clk) begin
        if (!resetn)
            pc <= RESET_PC;
        else if (redirect_valid)
            pc <= redirect_pc;
        else if (inst_req_fire)
            pc <= pc + 32'd4;
    end

    // 单 outstanding 请求跟踪。重定向不能撤销已接受请求，所以把它标记为
    // drop，等响应回来后静默丢弃；同拍可继续接受重定向目标的新请求。
    always @(posedge clk) begin
        if (!resetn) begin
            inst_pending      <= 1'b0;
            inst_pending_pc   <= 32'b0;
            inst_pending_drop <= 1'b0;
        end else begin
            if (inst_pending && inst_rsp_valid) begin
                inst_pending      <= 1'b0;
                inst_pending_drop <= 1'b0;
            end
            if (redirect_valid && inst_pending && !inst_rsp_valid)
                inst_pending_drop <= 1'b1;
            if (inst_req_fire) begin
                inst_pending      <= 1'b1;
                inst_pending_pc   <= inst_req_addr;
                inst_pending_drop <= 1'b0;
            end
        end
    end

    // IF/ID 被数据冒险、串行指令或总线等待按住时，返回的指令先进入缓冲。
    always @(posedge clk) begin
        if (!resetn || redirect_valid) begin
            inst_buffer_valid <= 1'b0;
            inst_buffer_pc    <= 32'b0;
            inst_buffer_data  <= 32'b0;
            inst_buffer_error <= 1'b0;
        end else begin
            if (inst_buffer_pop)
                inst_buffer_valid <= 1'b0;
            if (inst_response_good && !inst_if_id_accept) begin
                inst_buffer_valid <= 1'b1;
                inst_buffer_pc    <= inst_pending_pc;
                inst_buffer_data  <= inst_rsp_rdata;
                inst_buffer_error <= inst_rsp_error;
            end
        end
    end

    // ==================== ② IF/ID 流水寄存器 = ID 级的输入 ====================
    // ★ 位置: 正好卡在 IF / ID 的交界处 —— 上面是①IF 段, 下面是③ID 段。ID/EX 同理见⑥, EX/MEM 见⑧。
    // 气泡来源: 复位/ROM 未就绪、明确取消；load-use 和串行等待则保持原 ID 项。
    // 约定:气泡的唯一标志是 if_id_valid=0;指令/PC 字段只填"安全兜底值",不参与判断

    // ---------- IF/ID 时序块 ----------
    always @(posedge clk) begin
        if (!resetn || !fetch_valid) begin
            if_id_inst <= 32'h00000000;
            if_id_pc <= 32'h00000000;
            if_id_valid <= 1'b0;
            if_id_access_fault <= 1'b0;
        end
        else if (kill_if_id) begin
            // 分支/trap 重定向或串行发射清除已经消费/失效的 ID 项。
            if_id_inst <= 32'h0000_0013;                       // NOP(addi x0,x0,0)兜底
            if_id_pc <= 32'hFFFF_FFFF;                         // 哨兵:波形上一眼认出气泡
            if_id_valid <= 1'b0;
            if_id_access_fault <= 1'b0;
        end
        else if (frontend_hold) begin
            if_id_inst <= if_id_inst;
            if_id_pc <= if_id_pc;
            if_id_valid <= if_id_valid;
            if_id_access_fault <= if_id_access_fault;
        end
        else if (inst_buffer_valid) begin
            if_id_inst <= inst_buffer_data;
            if_id_pc <= inst_buffer_pc;
            if_id_valid <= 1'b1;
            if_id_access_fault <= inst_buffer_error;
        end
        else if (inst_response_good) begin
            if_id_inst <= inst_rsp_rdata;
            if_id_pc <= inst_pending_pc;
            if_id_valid <= 1'b1;
            if_id_access_fault <= inst_rsp_error;
        end
        else begin
            if_id_inst <= 32'h0000_0013;
            if_id_pc <= 32'hFFFF_FFFF;
            if_id_valid <= 1'b0;
            if_id_access_fault <= 1'b0;
        end
    end

    // ID 级及其后各级看到的指令 = IF/ID 寄存器输出。
    // 沿用旧名 inst → 下方整套译码/立即数代码一行都不用改。
    assign inst = if_id_inst;

    // ==================== ③ 译码 / 立即数(ID 级) ====================
    // ---- 译码(与 topcpu.v 完全相同)----
    assign opcode = inst[6:0];
    assign funct3 = inst[14:12];
    assign funct7 = inst[31:25];
    assign rd     = inst[11:7];
    assign rs1    = inst[19:15];
    assign rs2    = inst[24:20];
    assign csr_addr = inst[31:20];
    assign shamt = {27'b0, inst[24:20]};

    assign inst_add   = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0000000);
    assign inst_addi  = (opcode == 7'b0010011) && (funct3 == 3'b000);
    assign inst_sub   = (opcode == 7'b0110011) && (funct3 == 3'b000) && (funct7 == 7'b0100000);
    assign inst_lui   = (opcode == 7'b0110111);
    assign inst_auipc = (opcode == 7'b0010111);
    assign inst_and   = (opcode == 7'b0110011) && (funct3 == 3'b111) && (funct7 == 7'b0000000);
    assign inst_andi  = (opcode == 7'b0010011) && (funct3 == 3'b111);
    assign inst_or    = (opcode == 7'b0110011) && (funct3 == 3'b110) && (funct7 == 7'b0000000);
    assign inst_ori   = (opcode == 7'b0010011) && (funct3 == 3'b110);
    assign inst_xor   = (opcode == 7'b0110011) && (funct3 == 3'b100) && (funct7 == 7'b0000000);
    assign inst_xori  = (opcode == 7'b0010011) && (funct3 == 3'b100);
    assign inst_sll   = (opcode == 7'b0110011) && (funct3 == 3'b001) && (funct7 == 7'b0000000);
    assign inst_slli  = (opcode == 7'b0010011) && (funct3 == 3'b001) && (funct7 == 7'b0000000);
    assign inst_slti  = (opcode == 7'b0010011) && (funct3 == 3'b010);
    assign inst_slt   = (opcode == 7'b0110011) && (funct3 == 3'b010) && (funct7 == 7'b0000000);
    assign inst_srli  = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
    assign inst_srl   = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0000000);
    assign inst_sra   = (opcode == 7'b0110011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
    assign inst_srai  = (opcode == 7'b0010011) && (funct3 == 3'b101) && (funct7 == 7'b0100000);
    assign inst_sltu  = (opcode == 7'b0110011) && (funct3 == 3'b011) && (funct7 == 7'b0000000);
    assign inst_sltiu = (opcode == 7'b0010011) && (funct3 == 3'b011);
    assign inst_jalr  = (opcode == 7'b1100111) && (funct3 == 3'b000);
    assign inst_jal   = (opcode == 7'b1101111);
    assign inst_bne   = (opcode == 7'b1100011) && (funct3 == 3'b001);
    assign inst_beq   = (opcode == 7'b1100011) && (funct3 == 3'b000);
    assign inst_blt   = (opcode == 7'b1100011) && (funct3 == 3'b100);
    assign inst_bge   = (opcode == 7'b1100011) && (funct3 == 3'b101);
    assign inst_bltu  = (opcode == 7'b1100011) && (funct3 == 3'b110);
    assign inst_bgeu  = (opcode == 7'b1100011) && (funct3 == 3'b111);
    assign inst_lw    = (opcode == 7'b0000011) && (funct3 == 3'b010);
    assign inst_lh    = (opcode == 7'b0000011) && (funct3 == 3'b001);
    assign inst_lb    = (opcode == 7'b0000011) && (funct3 == 3'b000);
    assign inst_lhu   = (opcode == 7'b0000011) && (funct3 == 3'b101);
    assign inst_lbu   = (opcode == 7'b0000011) && (funct3 == 3'b100);
    assign inst_sw    = (opcode == 7'b0100011) && (funct3 == 3'b010);
    assign inst_sh    = (opcode == 7'b0100011) && (funct3 == 3'b001);
    assign inst_sb    = (opcode == 7'b0100011) && (funct3 == 3'b000);
    assign inst_csrrw = (opcode == 7'b1110011) && (funct3 == 3'b001);
    assign inst_csrrs = (opcode == 7'b1110011) && (funct3 == 3'b010);
    assign inst_csrrc = (opcode == 7'b1110011) && (funct3 == 3'b011);
    assign inst_csrrwi = (opcode == 7'b1110011) && (funct3 == 3'b101);
    assign inst_csrrsi = (opcode == 7'b1110011) && (funct3 == 3'b110);
    assign inst_csrrci = (opcode == 7'b1110011) && (funct3 == 3'b111);
    // FENCE 作为串行内存屏障；保留的 rd/rs1 字段不读写 GPR。
    // FENCE.I 未实现，funct3=001 会落入非法指令。WFI 首版作串行 NOP。
    assign inst_fence = (opcode == 7'b0001111) && (funct3 == 3'b000);
    assign inst_wfi = (inst == 32'h1050_0073);
    assign csr_inst = inst_csrrw | inst_csrrs | inst_csrrc |
                      inst_csrrwi | inst_csrrsi | inst_csrrci;
    assign csr_imm_form = inst_csrrwi | inst_csrrsi | inst_csrrci;
    // CSRRW/CSRRWI 的 rd=x0 抑制读取；其余四条总要读取旧值。
    assign csr_read_req = csr_inst &&
                          (!(inst_csrrw || inst_csrrwi) || (rd != 5'd0));
    // CSRRS/CSRRC 的写意图取决于 rs1 编号，立即数形式取决于 zimm。
    // rs1 非 x0 但寄存器内容为零时，仍有写意图。
    assign csr_write_req = (inst_csrrw || inst_csrrwi) ||
                           (csr_inst && (rs1 != 5'd0));
    assign i_j    = inst_jalr | inst_jal;
    assign i_l    = inst_lw | inst_lh | inst_lb | inst_lhu | inst_lbu;
    assign inst_5l = {inst_lw, inst_lh, inst_lhu, inst_lb, inst_lbu};
    assign i_u    = inst_lui | inst_auipc;
    assign i_shamt= inst_slli | inst_srli | inst_srai;
    assign i_I    = inst_slti | inst_sltiu | inst_addi | inst_andi | inst_ori | inst_xori;
    assign i_R    = inst_add | inst_sub | inst_and | inst_or | inst_xor |
                    inst_sll | inst_slt | inst_sltu | inst_srl | inst_sra;
    assign inst_s = inst_sw | inst_sh | inst_sb;
    assign inst_b = inst_beq | inst_bne | inst_blt | inst_bge | inst_bltu | inst_bgeu;

    assign imm_u = {inst[31:12], 12'b0};
    assign imm_i = {{20{inst[31]}}, inst[31:20]};
    assign imm_s = {{20{inst[31]}}, inst[31:25], inst[11:7]};
    assign imm_b = {{19{inst[31]}}, inst[31], inst[7], inst[30:25], inst[11:8], 1'b0};
    assign imm_j = {{11{inst[31]}}, inst[31], inst[19:12], inst[20], inst[30:21], 1'b0};
    assign zimm = inst[19:15];

    // ---- 立即数统一生成:六类编码两两互斥 → 按位或合并 ----
    // 为什么可以直接"或":各编码的 opcode 互不相同 ——
    //   U(0110111/0010111) I(0010011/0000011) S(0100011) B(1100011) J(1101111) jalr(1100111);
    //   唯一共用 0010011 的 i_I 与 i_shamt 由 funct3 区分(000/010/011/100/110/111 vs 001/101)。
    // 与优先级链相比:少了 3 级级联 mux,而且生成了唯一一个 imm,分支目标也能复用它。
    assign imm_i_sel = i_I | i_l | inst_jalr;      // jalr 的目标同样吃 I 型立即数
    assign imm = ({32{i_u}}       & imm_u)
                 | ({32{imm_i_sel}} & imm_i)
                 | ({32{inst_s}}    & imm_s)
                 | ({32{i_shamt}}   & shamt)
                 | ({32{inst_b}}    & imm_b)
                 | ({32{inst_jal}}  & imm_j);
    assign use_imm = i_u | i_I | i_l | inst_s | i_shamt;

    assign wmem = inst_sw | inst_sh | inst_sb;
    // 仅已实现、确实有 GPR 目标的指令可写回；未实现编码不能再误写 GPR。
    assign gf_we = (i_R | i_I | i_shamt | i_u | i_l | i_j | csr_inst) &&
                   (rd != 5'd0);

    // ==================== ④ 寄存器堆(ID 级读, WB 级写) ====================
    // rf_we / rf_waddr / rf_wdata 已在模块前部声明，赋值在⑪ WB 段。
    regfile u_regfile (
        .clk   (clk),
        .raddr1(rs1), .raddr2(rs2),
        .waddr (rf_waddr), .we(rf_we), .rst(~resetn),
        .wdata (rf_wdata),
        .rdata1(rdata1), .rdata2(rdata2)
    );

    // ==================== ⑤ ALU 操作码(译码产物, ID 级算完锁进 ID/EX) ====================
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
    assign csr_src = csr_imm_form ? {27'b0, zimm} : id_rs1;

    // 气泡约定沿用 IF/ID:唯一标志 id_ex_valid=0,且控制字全部清 0(不依赖 NOP 兜底值)。

    // ECALL/EBREAK/MRET/WFI 只接受完整的 32 位编码。
    assign inst_ecall = (inst == 32'h0000_0073);
    assign inst_ebreak = (inst == 32'h0010_0073);
    assign inst_mret = (inst == 32'h3020_0073);
    // 白名单同时覆盖 opcode、funct3、funct7 和指令长度；IF/ID 气泡即使
    // 含 0，也只有 id_fire 时才会锁进异常记录，不会误报。
    assign id_inst_supported = i_R || i_I || i_shamt || i_u || i_l ||
                                    inst_s || inst_b || i_j || csr_inst ||
                                    inst_ecall || inst_ebreak || inst_mret ||
                                    inst_fence || inst_wfi;
    assign id_illegal_inst = !id_inst_supported;
    assign id_exc_valid = if_id_access_fault || inst_ecall || inst_ebreak ||
                               id_illegal_inst || id_target_misaligned;
    assign id_exc_cause = if_id_access_fault ? `RV_EXC_INST_ACCESS_FAULT :
                                 inst_ecall ? `RV_EXC_ECALL_M :
                                 inst_ebreak ? `RV_EXC_BREAKPOINT :
                                 id_illegal_inst ? `RV_EXC_ILLEGAL_INST :
                                 id_target_misaligned ?
                                     `RV_EXC_INST_ADDR_MISALIGNED : 5'b0;
    assign id_exc_tval = if_id_access_fault ? if_id_pc :
                               id_illegal_inst ? inst :
                                id_target_misaligned ? bj_pc : 32'b0;

    // ---------- load-use 阻塞判据 ----------
    // EX 里是 load、而 ID 这条要用它的结果 —— 此时 load 的数据还在 RAM 里没出来(下一拍才到 MEM),
    //   所以 EX 无法前递, 只能把 ID 这条按在译码级等一拍(下一拍从 MEM 前递)。
    // 这就是书本说的"引入前递之后, 译码级唯一的阻塞条件"。
    // 只比较当前指令实际读取的源寄存器。U/J 型的相同位段是立即数,
    // I 型的 rs2 位段也是立即数, 不能因为位模式碰巧等于 load.rd 而停顿。
    assign uses_rs1 = i_R | i_I | i_shamt | i_l | inst_s | inst_b |
                      inst_jalr | inst_csrrw | inst_csrrs | inst_csrrc;
    assign uses_rs2 = i_R | inst_s | inst_b;
    assign load_use = id_ex_valid & id_ex_i_l & id_ex_gf_we & (id_ex_rd != 5'd0) &
                      ((uses_rs1 & (id_ex_rd == rs1)) |
                       (uses_rs2 & (id_ex_rd == rs2)));

    // ---------- ID/EX 时序块 ----------
    // 普通 ID 分支只取消更年轻的 IF/ID，不取消本拍发射的分支自身。
    // trap/MRET 的取消范围更大，由单独的 kill_id_ex 控制。
    always@(posedge clk)begin
        if(!resetn || kill_id_ex)begin
            id_ex_valid    <= 1'b0;
            id_ex_serial   <= 1'b0;
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
        else if(data_pipeline_stall)begin
            // 总线尚未接受 EX 请求，或 MEM 尚未收到响应：整组字段保持，
            // 保证 valid 拉高期间请求地址/数据/控制稳定，也避免重复发射 store。
            id_ex_valid    <= id_ex_valid;
            id_ex_serial   <= id_ex_serial;
            id_ex_pc       <= id_ex_pc;
            id_ex_inst     <= id_ex_inst;
            id_ex_src1     <= id_ex_src1;
            id_ex_src2     <= id_ex_src2;
            id_ex_rs2_data <= id_ex_rs2_data;
            id_ex_alu_op   <= id_ex_alu_op;
            id_ex_rd       <= id_ex_rd;
            id_ex_inst_5l  <= id_ex_inst_5l;
            id_ex_i_l      <= id_ex_i_l;
            id_ex_wmem     <= id_ex_wmem;
            id_ex_sw       <= id_ex_sw;
            id_ex_sh       <= id_ex_sh;
            id_ex_sb       <= id_ex_sb;
            id_ex_gf_we    <= id_ex_gf_we;
        end
        else if(bubble_id_ex)begin
            // 停顿、串行排空或 ID 无有效项：老 EX 继续推进，ID/EX 插气泡。
            id_ex_valid    <= 1'b0;
            id_ex_serial   <= 1'b0;
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
        else if(id_fire)begin
            id_ex_valid    <= 1'b1;
            id_ex_serial   <= serial_candidate;
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
            // CSR 指令由 WB 的旧值写回 rd；ECALL/EBREAK/MRET/FENCE 不写 GPR。
            id_ex_gf_we    <= gf_we;
        end
        else begin
            // 气泡: 控制字全部清 0 —— EX 级任何 enable 都不会误触发。
            // (不依赖 if_id_inst=0x0000_0013 那个 NOP 兜底: NOP 的 gf_we 其实是 1,
            //  只是靠 rd=0 才没闯祸; 清 0 之后天然安全, 不再靠这一条。)
            id_ex_valid    <= 1'b0;
            id_ex_serial   <= 1'b0;
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

    always @(posedge clk) begin
        if (!resetn || kill_id_ex)
            id_ex_next_pc <= 32'b0;
        else if (data_pipeline_stall)
            id_ex_next_pc <= id_ex_next_pc;
        else if (bubble_id_ex)
            id_ex_next_pc <= 32'b0;
        else if (id_fire)
            id_ex_next_pc <= id_taken ? bj_pc : if_id_pc + 32'd4;
    end

    // CSR 元数据随有效指令前进；停顿/取消时清零，不能把气泡当作 CSR。
    always @(posedge clk) begin
        if (!resetn || kill_id_ex) begin
            id_ex_csr              <= 1'b0;
            id_ex_csr_addr         <= 12'b0;
            id_ex_csr_op           <= 2'b0;
            id_ex_csr_src          <= 32'b0;
            id_ex_csr_read_en      <= 1'b0;
            id_ex_csr_write_intent <= 1'b0;
            id_ex_mret             <= 1'b0;
        end else if (data_pipeline_stall) begin
            id_ex_csr              <= id_ex_csr;
            id_ex_csr_addr         <= id_ex_csr_addr;
            id_ex_csr_op           <= id_ex_csr_op;
            id_ex_csr_src          <= id_ex_csr_src;
            id_ex_csr_read_en      <= id_ex_csr_read_en;
            id_ex_csr_write_intent <= id_ex_csr_write_intent;
            id_ex_mret             <= id_ex_mret;
        end else if (bubble_id_ex) begin
            id_ex_csr              <= 1'b0;
            id_ex_csr_addr         <= 12'b0;
            id_ex_csr_op           <= 2'b0;
            id_ex_csr_src          <= 32'b0;
            id_ex_csr_read_en      <= 1'b0;
            id_ex_csr_write_intent <= 1'b0;
            id_ex_mret             <= 1'b0;
        end else if (id_fire) begin
            id_ex_csr              <= csr_inst;
            id_ex_csr_addr         <= csr_addr;
            id_ex_csr_op           <= funct3[1:0];
            id_ex_csr_src          <= csr_src;
            id_ex_csr_read_en      <= csr_read_req;
            id_ex_csr_write_intent <= csr_write_req;
            id_ex_mret             <= inst_mret;
        end
    end

    always @(posedge clk) begin
        if (!resetn || kill_id_ex) begin
            id_ex_exc_valid <= 1'b0;
            id_ex_exc_cause <= 5'b0;
            id_ex_exc_tval  <= 32'b0;
        end else if (data_pipeline_stall) begin
            id_ex_exc_valid <= id_ex_exc_valid;
            id_ex_exc_cause <= id_ex_exc_cause;
            id_ex_exc_tval  <= id_ex_exc_tval;
        end else if (bubble_id_ex) begin
            id_ex_exc_valid <= 1'b0;
            id_ex_exc_cause <= 5'b0;
            id_ex_exc_tval  <= 32'b0;
        end else if (id_fire) begin
            id_ex_exc_valid <= id_exc_valid;
            id_ex_exc_cause <= id_exc_cause;
            id_ex_exc_tval  <= id_exc_tval;
        end
    end

    // ==================== ⑦ EX 段:ALU + 访存地址发射 ====================
    alu u_alu (.alu_op(id_ex_alu_op), .alu_src1(id_ex_src1),
               .alu_src2(id_ex_src2), .alu_result(alu_result));

    // 地址在 EX 才由 ALU 算出：半字看 bit0，字看 bit[1:0]；字节天然对齐。
    // 已有 ID 故障优先，不允许 EX 的默认检测覆盖原 cause/tval。
    assign ex_access_half = id_ex_inst_5l[3] || id_ex_inst_5l[2] || id_ex_sh;
    assign ex_access_word = id_ex_inst_5l[4] || id_ex_sw;
    assign ex_data_misaligned = id_ex_valid && !id_ex_exc_valid &&
                              ((ex_access_half && alu_result[0]) ||
                               (ex_access_word && (|alu_result[1:0])));
    assign ex_exc_valid = id_ex_exc_valid || ex_data_misaligned;
    assign ex_exc_cause = id_ex_exc_valid ? id_ex_exc_cause :
                               ex_data_misaligned ?
                                   (id_ex_wmem ? `RV_EXC_STORE_ADDR_MISALIGNED :
                                                  `RV_EXC_LOAD_ADDR_MISALIGNED) : 5'b0;
    assign ex_exc_tval = id_ex_exc_valid ? id_ex_exc_tval :
                              ex_data_misaligned ? alu_result : 32'b0;
    // 老异常位于 MEM/WB 时，当前 EX store 是年轻指令，不得提前写 RAM。
    // 总线错误在响应当拍即视为老故障，不能等到下一拍进入 WB 才抑制年轻请求。
    assign ex_mem_bus_error = ex_mem_valid && ex_mem_mem_pending &&
                              data_rsp_valid && data_rsp_error;
    assign older_fault_for_ex = (ex_mem_valid && ex_mem_exc_valid) ||
                                ex_mem_bus_error ||
                                (mem_wb_valid && mem_wb_exc_valid) ||
                                wb_csr_illegal;


    // 存数路径: 字节偏移只有算完地址才知道, 所以掩码只能在 EX 级合成
    //   (ID 级只能带"是 sw 还是 sh 还是 sb"这个类型过来)
    assign st_off = alu_result[1:0];
    assign st_we  = id_ex_sw ? 4'b1111
                    : id_ex_sh ? (st_off[1] ? 4'b1100 : 4'b0011)
                    : id_ex_sb ? (4'b0001 << st_off)
                    : 4'b0000;
    // 类 SRAM 数据总线。请求从 EX 发出，只有 valid/ready 同时为 1 才进入 MEM；
    // 未接受期间 ID/EX 保持，因此以下全部请求字段也保持不变。
    assign id_ex_needs_bus = resetn && id_ex_valid && (id_ex_i_l || id_ex_wmem) &&
                             !kill_ex_mem && !ex_exc_valid && !older_fault_for_ex;
    assign data_req_valid = id_ex_needs_bus && ex_mem_ready;
    assign data_req_write = id_ex_wmem;
    assign data_req_size  = (id_ex_sw || id_ex_inst_5l[4]) ? 2'b10 :
                            (id_ex_sh || id_ex_inst_5l[3] || id_ex_inst_5l[2]) ? 2'b01 :
                            2'b00;
    assign data_req_addr  = alu_result;
    assign data_req_wdata = id_ex_rs2_data << {2'b00, alu_result[1:0], 3'b000};
    assign data_req_wstrb = st_we;
    assign data_req_fire  = data_req_valid && data_req_ready;

    assign mem_load_request  = data_req_fire && !data_req_write;
    assign mem_store_request = data_req_fire &&  data_req_write;
    assign ex_store_commit   = mem_store_request;

    // MEM 必须等响应完成；EX/MEM 腾空（或本拍完成）之后，EX 才能前进。
    assign ex_mem_complete  = ex_mem_valid &&
                              (!ex_mem_mem_pending || data_rsp_valid);
    assign ex_mem_ready     = !ex_mem_valid || ex_mem_complete;
    assign id_ex_can_advance = ex_mem_ready &&
                               (!id_ex_needs_bus || data_req_ready);
    assign id_ex_advance    = id_ex_valid && id_ex_can_advance;
    assign data_pipeline_stall = (ex_mem_valid && !ex_mem_complete) ||
                                 (id_ex_valid && !id_ex_can_advance);

    // EX 这一拍能前递/写回的值: 只有 alu_result。
    //   ★ load 在 EX 这一拍【没有】可用数据 —— 它的数据要下一拍才从 RAM 出来。
    //     所以 EX→ID 前递必须用 id_ex_i_l 屏蔽掉, 这就是 load-use 阻塞存在的原因。
    assign ex_wb_data = alu_result;

    // ==================== ⑧ EX/MEM 流水寄存器 = MEM 级的输入 ====================
    // ★ 位置: 正好卡在 EX / MEM 的交界处。
    // load/store 只有请求握手成功才进入这里；进入后保持到 rsp_valid。
    // 非访存指令仍按普通一拍 MEM 级前进。
    // 气泡约定: ex_mem_valid=0；trap/MRET 取消信号可明确清除这一流水级。
    // ex_mem_valid 已在文件顶部前置声明；气泡唯一标志。
    // ex_mem_exc_valid 已在文件顶部前置声明。

    // ---------- EX/MEM 时序块 ----------
    always@(posedge clk)begin
        if(!resetn || kill_ex_mem)begin
            ex_mem_valid      <= 1'b0;
            ex_mem_serial     <= 1'b0;
            ex_mem_alu_result <= 32'h00000000;
            ex_mem_pc         <= 32'hFFFF_FFFF;                // 哨兵
            ex_mem_inst       <= 32'h00000000;
            ex_mem_rd         <= 5'd0;
            ex_mem_inst_5l    <= 5'b0;
            ex_mem_i_l        <= 1'b0;
            ex_mem_gf_we      <= 1'b0;
            ex_mem_mem_pending<= 1'b0;
            ex_mem_mem_write  <= 1'b0;
        end
        else if(id_ex_advance)begin
            ex_mem_valid      <= 1'b1;
            ex_mem_serial     <= id_ex_serial;
            ex_mem_alu_result <= alu_result;
            ex_mem_pc         <= id_ex_pc;
            ex_mem_inst       <= id_ex_inst;
            ex_mem_rd         <= id_ex_rd;
            ex_mem_inst_5l    <= id_ex_inst_5l;
            ex_mem_i_l        <= id_ex_i_l;
            ex_mem_gf_we      <= id_ex_gf_we;
            ex_mem_mem_pending<= id_ex_needs_bus;
            ex_mem_mem_write  <= id_ex_wmem;
        end
        else if(ex_mem_complete)begin
            ex_mem_valid      <= 1'b0;
            ex_mem_serial     <= 1'b0;
            ex_mem_alu_result <= 32'h00000000;
            ex_mem_pc         <= 32'hFFFF_FFFF;
            ex_mem_inst       <= 32'h00000000;
            ex_mem_rd         <= 5'd0;
            ex_mem_inst_5l    <= 5'b0;
            ex_mem_i_l        <= 1'b0;
            ex_mem_gf_we      <= 1'b0;
            ex_mem_mem_pending<= 1'b0;
            ex_mem_mem_write  <= 1'b0;
        end
    end

    always @(posedge clk) begin
        if (!resetn || kill_ex_mem)
            ex_mem_next_pc <= 32'b0;
        else if (id_ex_advance)
            ex_mem_next_pc <= id_ex_next_pc;
        else if (ex_mem_complete)
            ex_mem_next_pc <= 32'b0;
    end

    always @(posedge clk) begin
        if (!resetn || kill_ex_mem) begin
            ex_mem_csr              <= 1'b0;
            ex_mem_csr_addr         <= 12'b0;
            ex_mem_csr_op           <= 2'b0;
            ex_mem_csr_src          <= 32'b0;
            ex_mem_csr_read_en      <= 1'b0;
            ex_mem_csr_write_intent <= 1'b0;
            ex_mem_mret             <= 1'b0;
        end else if (id_ex_advance) begin
            ex_mem_csr              <= id_ex_csr;
            ex_mem_csr_addr         <= id_ex_csr_addr;
            ex_mem_csr_op           <= id_ex_csr_op;
            ex_mem_csr_src          <= id_ex_csr_src;
            ex_mem_csr_read_en      <= id_ex_csr_read_en;
            ex_mem_csr_write_intent <= id_ex_csr_write_intent;
            ex_mem_mret             <= id_ex_mret;
        end else if (ex_mem_complete) begin
            ex_mem_csr              <= 1'b0;
            ex_mem_csr_addr         <= 12'b0;
            ex_mem_csr_op           <= 2'b0;
            ex_mem_csr_src          <= 32'b0;
            ex_mem_csr_read_en      <= 1'b0;
            ex_mem_csr_write_intent <= 1'b0;
            ex_mem_mret             <= 1'b0;
        end
    end

    always @(posedge clk) begin
        if (!resetn || kill_ex_mem) begin
            ex_mem_exc_valid <= 1'b0;
            ex_mem_exc_cause <= 5'b0;
            ex_mem_exc_tval  <= 32'b0;
        end else if (id_ex_advance) begin
            ex_mem_exc_valid <= ex_exc_valid;
            ex_mem_exc_cause <= ex_exc_cause;
            ex_mem_exc_tval  <= ex_exc_tval;
        end else if (ex_mem_complete) begin
            ex_mem_exc_valid <= 1'b0;
            ex_mem_exc_cause <= 5'b0;
            ex_mem_exc_tval  <= 32'b0;
        end
    end

    // ==================== ⑨ MEM 段:消费总线响应 ====================
    // rsp_valid 当拍，rsp_rdata 与当前 EX/MEM load 一一对应。l_alu 在这里完成
    // 字节/半字抽取和符号扩展，结果随完成事件锁入 MEM/WB。
    l_alu u_l_alu (
        .sel_addr(ex_mem_alu_result[1:0]),
        .inst_5l(ex_mem_inst_5l),
        .data_sram_rdata(data_rsp_rdata),
        .mem_result(mem_result)
    );

    // MEM 这一级"将要写回的结果"—— 也是 MEM→ID 前递的起点
    // 故障 load 仍可经过普通 BRAM 的读端口，但结果不得成为写回/前递数据。
    assign mem_fwd_data = (ex_mem_exc_valid || ex_mem_bus_error) ? 32'b0 :
                          (ex_mem_i_l ? mem_result : ex_mem_alu_result);

    // ==================== ⑩ MEM/WB 流水寄存器 = WB 级的输入 ====================
    // ★ 位置: 正好卡在 MEM / WB 的交界处。
    // 只有 ex_mem_complete 才允许进入 WB。对 load/store，它等价于 rsp_valid；
    // 因而任意总线延迟都不会重复退休，也不会把尚未有效的读数据锁进来。
    // 气泡约定: mem_wb_valid=0；trap/MRET 取消信号可明确清除这一流水级。
    // mem_wb_valid 已在文件顶部前置声明；气泡唯一标志。
    // mem_wb_exc_valid 已在文件顶部前置声明。

    // ---------- MEM/WB 时序块 ----------
    always@(posedge clk)begin
        if(!resetn || kill_mem_wb)begin
            mem_wb_valid   <= 1'b0;
            mem_wb_serial  <= 1'b0;
            mem_wb_wdata   <= 32'h00000000;
            mem_wb_pc      <= 32'hFFFF_FFFF;                   // 哨兵
            mem_wb_inst    <= 32'h00000000;
            mem_wb_rd      <= 5'd0;
            mem_wb_gf_we   <= 1'b0;
        end
        else if(ex_mem_complete)begin
            mem_wb_valid   <= 1'b1;
            mem_wb_serial  <= ex_mem_serial;
            mem_wb_wdata   <= mem_fwd_data;
            mem_wb_pc      <= ex_mem_pc;
            mem_wb_inst    <= ex_mem_inst;
            mem_wb_rd      <= ex_mem_rd;
            mem_wb_gf_we   <= ex_mem_gf_we;
        end
        else begin
            mem_wb_valid   <= 1'b0;
            mem_wb_serial  <= 1'b0;
            mem_wb_wdata   <= 32'h00000000;
            mem_wb_pc      <= 32'hFFFF_FFFF;
            mem_wb_inst    <= 32'h00000000;
            mem_wb_rd      <= 5'd0;
            mem_wb_gf_we   <= 1'b0;
        end
    end

    always @(posedge clk) begin
        if (!resetn || kill_mem_wb || !ex_mem_complete)
            mem_wb_next_pc <= 32'b0;
        else
            mem_wb_next_pc <= ex_mem_next_pc;
    end

    always @(posedge clk) begin
        if (!resetn || kill_mem_wb || !ex_mem_complete) begin
            mem_wb_csr              <= 1'b0;
            mem_wb_csr_addr         <= 12'b0;
            mem_wb_csr_op           <= 2'b0;
            mem_wb_csr_src          <= 32'b0;
            mem_wb_csr_read_en      <= 1'b0;
            mem_wb_csr_write_intent <= 1'b0;
            mem_wb_mret             <= 1'b0;
        end else begin
            mem_wb_csr              <= ex_mem_csr;
            mem_wb_csr_addr         <= ex_mem_csr_addr;
            mem_wb_csr_op           <= ex_mem_csr_op;
            mem_wb_csr_src          <= ex_mem_csr_src;
            mem_wb_csr_read_en      <= ex_mem_csr_read_en;
            mem_wb_csr_write_intent <= ex_mem_csr_write_intent;
            mem_wb_mret             <= ex_mem_mret;
        end
    end

    always @(posedge clk) begin
        if (!resetn || kill_mem_wb || !ex_mem_complete) begin
            mem_wb_exc_valid <= 1'b0;
            mem_wb_exc_cause <= 5'b0;
            mem_wb_exc_tval  <= 32'b0;
        end else begin
            mem_wb_exc_valid <= ex_mem_exc_valid || ex_mem_bus_error;
            mem_wb_exc_cause <= ex_mem_bus_error ?
                                (ex_mem_mem_write ? `RV_EXC_STORE_ACCESS_FAULT :
                                                    `RV_EXC_LOAD_ACCESS_FAULT) :
                                ex_mem_exc_cause;
            mem_wb_exc_tval  <= ex_mem_bus_error ? ex_mem_alu_result :
                                                   ex_mem_exc_tval;
        end
    end

    // ==================== ⑪ WB 段:写寄存器堆 + 调试口 ====================
    // CSR 指令在 WB 组合读旧值、生成新值；合法写与 GPR 旧值写回同沿提交。
    // wb_csr_illegal 已在文件顶部前置声明。

    assign wb_csr_valid = resetn && mem_wb_valid && mem_wb_csr;
    assign wb_csr_read_en = wb_csr_valid && mem_wb_csr_read_en;
    assign wb_csr_write_intent = wb_csr_valid && mem_wb_csr_write_intent;
    assign wb_csr_illegal = wb_csr_valid && csr_access_illegal;
    // CSR 地址合法性到 WB 才知道：非法访问也走同一个同步 trap 提交点。
    assign wb_trap_cause = mem_wb_exc_valid ? mem_wb_exc_cause :
                           `RV_EXC_ILLEGAL_INST;
    assign wb_trap_tval = mem_wb_exc_valid ? mem_wb_exc_tval : mem_wb_inst;
    assign csr_wdata = (mem_wb_csr_op == 2'b01) ? mem_wb_csr_src :
                       (mem_wb_csr_op == 2'b10) ? (csr_rdata | mem_wb_csr_src) :
                       (mem_wb_csr_op == 2'b11) ? (csr_rdata & ~mem_wb_csr_src) :
                       32'b0;
    assign csr_commit = wb_csr_valid && !mem_wb_exc_valid &&
                        !wb_csr_illegal && !trap_redirect_req;
    assign mret_commit = resetn && mem_wb_valid && mem_wb_mret &&
                         !mem_wb_exc_valid && !sync_trap_event;

    csr_file u_csr_file (
        .clk(clk), .resetn(resetn),
        .csr_addr(mem_wb_csr_addr),
        .csr_read_en(wb_csr_read_en),
        .csr_write_intent(wb_csr_write_intent),
        .csr_wdata(csr_wdata), .csr_commit(csr_commit),
        .csr_rdata(csr_rdata), .csr_exists(csr_exists),
        .csr_readonly_addr(csr_readonly_addr),
        .csr_access_illegal(csr_access_illegal),
        .trap_enter(trap_redirect_req),
        .trap_pc(irq_take ? arch_next_pc : mem_wb_pc),
        .trap_is_interrupt(irq_take),
        .trap_cause(irq_take ? irq_cause : wb_trap_cause),
        .trap_tval(irq_take ? 32'b0 : wb_trap_tval),
        .mret_commit(mret_commit),
        .irq_external(irq_external), .irq_software(irq_software),
        .irq_timer(irq_timer),
        .trap_target(csr_trap_target), .mret_target(csr_mret_target),
        .irq_pending(csr_irq_pending), .irq_enable(csr_irq_enable),
        .irq_global_enable(csr_irq_global_enable)
    );

    // ID 非法指令和 WB 非法 CSR 都抑制 GPR 写入；CSR 写入另由 csr_commit 门控。
    assign rf_we    = resetn & mem_wb_valid & mem_wb_gf_we &
                      ~mem_wb_exc_valid & ~trap_redirect_req & ~wb_csr_illegal;
    assign rf_waddr = mem_wb_rd;
    assign rf_wdata = wb_csr_valid ? csr_rdata : mem_wb_wdata;

    assign debug_wb_pc       = mem_wb_pc;
    assign debug_wb_rf_we    = {4{rf_we}};
    assign debug_wb_rf_wnum  = mem_wb_rd;
    assign debug_wb_rf_wdata = rf_wdata;
    assign debug_inst        = mem_wb_inst;

    // ==================== ⑫ EX→ID / MEM→ID / WB→ID 转发(方案一) ====================
    // 起点: 各级"将要写回的结果输出处"—— EX 是 alu_result, MEM 是 mem_fwd_data,
    //       WB 是 rf_wdata（普通结果或 CSR 旧值）。
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
    assign fwd_ex_en  = id_ex_valid & id_ex_gf_we & ~id_ex_i_l & ~ex_exc_valid;
    assign id_fwd_ex1 = fwd_ex_en & (id_ex_rd != 5'd0) & (id_ex_rd == rs1);
    assign id_fwd_ex2 = fwd_ex_en & (id_ex_rd != 5'd0) & (id_ex_rd == rs2);

    // load 只有收到无错误响应后才能从 MEM 前递；普通 ALU 指令仍可直接前递。
    assign fwd_mem_en  = ex_mem_valid & ex_mem_gf_we & ~ex_mem_exc_valid &
                         ~ex_mem_bus_error &
                         (~ex_mem_i_l | (ex_mem_mem_pending & data_rsp_valid));
    assign id_fwd_mem1 = fwd_mem_en & (ex_mem_rd != 5'd0) & (ex_mem_rd == rs1);
    assign id_fwd_mem2 = fwd_mem_en & (ex_mem_rd != 5'd0) & (ex_mem_rd == rs2);

    assign fwd_wb_en  = mem_wb_valid & mem_wb_gf_we & ~mem_wb_exc_valid & ~wb_csr_illegal;
    assign id_fwd_wb1 = fwd_wb_en & (mem_wb_rd != 5'd0) & (mem_wb_rd == rs1);
    assign id_fwd_wb2 = fwd_wb_en & (mem_wb_rd != 5'd0) & (mem_wb_rd == rs2);

    assign id_rs1 = id_fwd_ex1  ? ex_wb_data   :
                    id_fwd_mem1 ? mem_fwd_data :
                     id_fwd_wb1  ? rf_wdata     : rdata1;
    assign id_rs2 = id_fwd_ex2  ? ex_wb_data   :
                    id_fwd_mem2 ? mem_fwd_data :
                     id_fwd_wb2  ? rf_wdata     : rdata2;

    // ==================== ⑬ ID 级分支 / 跳转 ====================
    // 分支判定留在 ID: 下沉到 EX 会让分支惩罚从 1 拍涨到 2 拍。
    // 位置约束:本段排在④⑩之后 —— br_alu 要吃转发后的 id_rs1/id_rs2。
    // 注意: jal/jalr 的链接值(PC+4)不在这里算 —— 已交给 EX 的 ALU。
    // 目标复用同一个 imm(B→imm_b、J→imm_j):分支与 jal 共用一个加法器。
    assign inst_6b = {inst_bgeu, inst_bltu, inst_bge, inst_blt, inst_bne, inst_beq};
    br_alu u_br_alu (
        .inst_6b (inst_6b),
        .xrs1    (id_rs1),          // ★ 必须用转发后的值
        .xrs2    (id_rs2),          // ★
        .br_taken(br_taken)
    );

    assign jalr_pc = (id_rs1 + imm) & ~32'h1;         // I 型:jalr rs1+imm_i,清 bit0  ★ 转发后的 rs1
    assign bj_pc   = inst_jalr ? jalr_pc
                     : (if_id_pc + imm);    // B/J 型:if_id_pc + 对应立即数

    // ID 级命中:分支条件成立(br_alu 组合输出)| jal | jalr
    // 注:非分支指令 inst_6b 全 0 → br_taken 必 0,可安全相或
    // id_taken 已在文件顶部前置声明。
    assign id_taken = br_taken | inst_jal | inst_jalr;
    // 只检查真正采用的目标。JALR 已先清 bit0；load-use 未解除时
    // rs1/rs2 可能还是旧值，必须等到本条能够发射时再判目标。
    assign id_target_misaligned = if_id_valid && !load_use &&
                                   (inst_b || i_j) && id_taken &&
                                   (|bj_pc[1:0]);
    // ==================== ⑭ 发射、排空、取消和重定向控制 ====================
    // CSR、MRET、ECALL、EBREAK、FENCE 和 WFI 共用串行排空控制。
    assign serial_csr = csr_inst;
    assign serial_system = inst_mret || inst_ecall || inst_ebreak;
    assign serial_fence = inst_fence || inst_wfi;
    assign serial_candidate = if_id_valid &&
                              (serial_csr || serial_system || serial_fence);

    // pending 保留原始电平；只有 pending、mie 与 mstatus.MIE 同时满足才成为候选。
    // 选择次序遵照本项目方案：MEI > MSI > MTI；接受前再组合重判一次。
    assign irq_eligible = csr_irq_pending & csr_irq_enable;
    assign irq_candidate = csr_irq_global_enable && (|irq_eligible);
    assign irq_cause = irq_eligible[`RV_IRQ_EXTERNAL_BIT] ? `RV_IRQ_CAUSE_EXTERNAL :
                       irq_eligible[`RV_IRQ_SOFTWARE_BIT] ? `RV_IRQ_CAUSE_SOFTWARE :
                       `RV_IRQ_CAUSE_TIMER;
    // EX/MEM 在响应回来之前始终保持 valid，因此已发射事务自然包含在排空条件中。
    assign irq_take = resetn && (flow_state == FLOW_IRQ_DRAIN) &&
                      pipeline_empty && irq_candidate && !sync_trap_event;
    // WB 同步故障优先于中断；irq_take 只会在排空后产生，二者不会同时成立。
    assign trap_redirect_req = sync_trap_event || irq_take;
    assign mret_redirect_req = mret_commit;
    assign trap_redirect_target = csr_trap_target;
    assign mret_redirect_target = csr_mret_target;

    // pipeline_empty 已在文件顶部前置声明。
    assign pipeline_empty = !id_ex_valid && !ex_mem_valid && !mem_wb_valid;
    // 已发现的故障令前端保持，老指令仍逐级完成；WB 事件负责取消年轻项。
    assign fault_inflight = (id_ex_valid && ex_exc_valid) ||
                            (ex_mem_valid && ex_mem_exc_valid) ||
                            ex_mem_bus_error ||
                            (mem_wb_valid && mem_wb_exc_valid);
    // 故障项本身保持 valid=1，但不计为正常退休。
    assign sync_trap_event = resetn && mem_wb_valid &&
                             (mem_wb_exc_valid || wb_csr_illegal);
    // 四类事件分开：正常退休不包含异常和 MRET；RAM 请求发生在 EX 沿。
    assign normal_retire = resetn && mem_wb_valid && !mem_wb_mret &&
                           !mem_wb_exc_valid && !wb_csr_illegal;
    always @(posedge clk) begin
        if (!resetn)
            arch_next_pc <= RESET_PC;
        else if (trap_redirect_req)
            arch_next_pc <= csr_trap_target;
        else if (mret_commit)
            arch_next_pc <= csr_mret_target;
        else if (normal_retire)
            arch_next_pc <= mem_wb_next_pc;
    end
    assign serial_issue = (flow_state == FLOW_SERIAL_DRAIN) &&
                          pipeline_empty && serial_candidate;
    assign id_fire = resetn && fetch_valid && if_id_valid &&
                      (((flow_state == FLOW_RUN) && !irq_candidate &&
                        !load_use && !serial_candidate && !data_pipeline_stall) ||
                       serial_issue) && !fault_inflight &&
                      !trap_redirect_req && !mret_redirect_req;
    assign bubble_id_ex = !id_fire && !data_pipeline_stall;
    assign frontend_hold = (flow_state != FLOW_RUN) || load_use ||
                            data_pipeline_stall || serial_candidate ||
                            fault_inflight || irq_candidate;

    // 普通 ID 分支在本拍真正发射后才能重定向；失效项或 load-use 停顿不允许跳转。
    assign branch_redirect = id_fire && !id_exc_valid &&
                             (flow_state == FLOW_RUN) && id_taken;
    assign redirect_valid = trap_redirect_req || mret_redirect_req || branch_redirect;
    assign redirect_pc = trap_redirect_req ? trap_redirect_target :
                         mret_redirect_req ? mret_redirect_target : bj_pc;
    assign kill_if_id = redirect_valid || serial_issue;
    assign kill_id_ex = trap_redirect_req || mret_redirect_req;
    assign kill_ex_mem = trap_redirect_req || mret_redirect_req;
    assign kill_mem_wb = trap_redirect_req || mret_redirect_req;

    // 只有当前串行指令到达 WB 才能结束等待，避免保持在 ID 的项重复发射。
    assign serial_done = (flow_state == FLOW_SERIAL_RUN) &&
                         mem_wb_valid && mem_wb_serial;
    always @(posedge clk) begin
        if (!resetn) begin
            flow_state <= FLOW_RUN;
        end else if (trap_redirect_req) begin
            flow_state <= FLOW_RUN;
        end else if (mret_redirect_req) begin
            flow_state <= FLOW_IRQ_CHECK;
        end else begin
            case (flow_state)
                FLOW_RUN: if (irq_candidate)
                              flow_state <= FLOW_IRQ_DRAIN;
                          else if (fetch_valid && serial_candidate)
                              flow_state <= FLOW_SERIAL_DRAIN;
                FLOW_SERIAL_DRAIN: if (serial_issue)
                                       flow_state <= FLOW_SERIAL_RUN;
                FLOW_SERIAL_RUN: if (serial_done)
                                     flow_state <= FLOW_IRQ_CHECK;
                FLOW_IRQ_CHECK: flow_state <= irq_candidate ? FLOW_IRQ_DRAIN : FLOW_RUN;
                FLOW_IRQ_DRAIN: if (pipeline_empty && !irq_candidate)
                                    flow_state <= FLOW_RUN;
                default: flow_state <= FLOW_RUN;
            endcase
        end
    end

endmodule
