`timescale 1ns / 1ps

module ifu(
    input  wire        clk,
    input  wire        resetn,       // 低有效复位(与 IP 核一致:同步复位)
    input  wire [31:0] next_pc,      // 下一拍 PC;分支逻辑接入前,顶层接 pc+4

    output wire [31:0] pc,           // 当前取指 PC(供顶层算 next_pc / 调试)

    // IF/ID 输出(给 idu 用):指令与 PC 同一沿锁存,永远配对
    output reg  [31:0] if_id_pc,     // 这条指令的 PC
    output reg  [31:0] if_id_inst,   // 指令
    output reg         if_id_valid,  // 1=有效指令,0=气泡

    // 指令 ROM 接口(1 拍读:地址在沿上被锁存,数据下一拍才有效)
    output wire [31:0] inst_sram_addr,
    input  wire [31:0] inst_sram_rdata
);
    parameter RESET_VECTOR = 32'h0000_0000;   // ROM 入口 = 第一条指令的地址

    //==================================================================
    // IF:PC 寄存器
    //   pc 复位到入口本身,不需要"入口-4"之类的 trick:
    //   复位后第一条指令就是 ROM 入口处那条,会被正常取到。
    //==================================================================
    reg [31:0] pc_r;
    always @(posedge clk) begin
        if (!resetn)      pc_r <= RESET_VECTOR;
        else              pc_r <= next_pc;   // 分支接入后,next_pc 由控制级给出
    end

    //==================================================================
    // pc 打一拍:与 ROM 读数据对齐(关键!)
    //   ROM 读时序:地址在沿上被锁存,inst_sram_rdata 下一拍才有效,
    //   即 rdata 永远对应"上一个周期的 pc"。
    //   所以与指令配对的 pc = pc_r 打一拍后的 pc_d1。
    //   pc_d1 与 rdata 每拍同步,同一沿锁存 → 配对永不落空。
    //==================================================================
    reg [31:0] pc_d1;
    always @(posedge clk) begin
        if (!resetn) pc_d1 <= 32'h0;
        else         pc_d1 <= pc_r;
    end

    //==================================================================
    // 复位"放行"信号:run_d1 = resetn 延迟一拍(寄存版)
    //   resetn=0(复位)期间:run_d1=0
    //   resetn=1(释放)后  :run_d1 从下一个沿起才变 1
    // 用途:
    //   if_id 寄存器每个沿都会装载。复位释放后的"第一个沿"上,
    //   装进去的 inst_sram_rdata 是复位期间 ROM 的输出(旧值/被复位
    //   清掉的值),不可信 → 用 run_d1(此刻还是 0)把这笔写成气泡;
    //   从"第二个沿"起,ROM 已用复位后的地址正常读过一次,数据才可信,
    //   run_d1=1 → if_id_valid=1,第一条真指令放行。
    //   代价:复位后多一个气泡(1 拍),换取对 ROM 复位行为不确定性的免疫。
    //   若你确认 ROM 复位后读输出可靠(如地址寄存器复位为 0 且输出未被清),
    //   可把下方 if_id_valid <= run_d1 改为 if_id_valid <= 1'b1,省掉这拍。
    //==================================================================
    reg run_d1;
    always @(posedge clk) begin
        if (!resetn) run_d1 <= 1'b0;
        else         run_d1 <= 1'b1;
    end

    //==================================================================
    // IF/ID 寄存器(取指级出口,方案 A)
    //   每个时钟沿把 {pc_d1, inst_sram_rdata} 整对锁存 → 指令与 PC 配对
    //==================================================================
    always @(posedge clk) begin
        if (!resetn) begin
            if_id_pc    <= 32'h0;
            if_id_inst  <= 32'h0;
            if_id_valid <= 1'b0;
        end
        else begin
            if_id_pc    <= pc_d1;           // 与数据同源的 PC
            if_id_inst  <= inst_sram_rdata; // 上一拍地址对应的指令
            if_id_valid <= run_d1;          // 复位释放沿的那次写入作废(气泡)
            // 分支/冲刷接入时,这里要能被外部打 0:
            //   if_id_valid <= flush_req ? 1'b0 : run_d1;
        end
    end

    assign pc            = pc_r;
    assign inst_sram_addr = pc_r;   // 字节地址;若 ROM 按字寻址,外部接 pc_r[11:2]

endmodule
