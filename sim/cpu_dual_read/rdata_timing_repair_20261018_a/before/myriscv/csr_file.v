`timescale 1ns/1ps
`include "csr_defs.vh"

// 仅支持 M 模式的 CSR 寄存器组。
// CPU 完成指令合法性检查和串行化后，才发送持续一拍的提交脉冲。
// 本模块不负责流水线停顿、冲刷和异常仲裁；csr_wdata 是 CPU 算好的最终写入候选值。
module csr_file #(
    // trap 入口复位地址；实际保存时强制清除低两位，首版只支持 Direct 模式。
    parameter [31:0] MTVEC_RESET_ADDR = `RV_MTVEC_RESET
) (
    input  wire        clk,
    input  wire        resetn,             // 同步低有效复位
    // CSR 指令接口：读使能与写意图由指令语义决定，不能仅依据源数据是否为零。
    input  wire [11:0] csr_addr,
    input  wire        csr_read_en,
    input  wire        csr_write_intent,
    input  wire [31:0] csr_wdata,
    input  wire        csr_commit,         // 合法 CSR 指令在 WB 的一次性提交脉冲
    output reg  [31:0] csr_rdata,
    output reg         csr_exists,
    output wire        csr_readonly_addr,
    output wire        csr_access_illegal,
    // trap/MRET 提交接口：由上层保证一次事件只提交一拍。
    input  wire        trap_enter,
    input  wire [31:0] trap_pc,
    input  wire        trap_is_interrupt,
    input  wire [4:0]  trap_cause,
    input  wire [31:0] trap_tval,
    input  wire        mret_commit,
    // 三路中断输入在进入本模块前应已同步到 clk，均按电平处理。
    input  wire        irq_external,
    input  wire        irq_software,
    input  wire        irq_timer,
    // 入口/返回目标和原始 pending、局部使能、全局使能，供 CPU 中断控制器使用。
    output wire [31:0] trap_target,
    output wire [31:0] mret_target,
    output wire [31:0] irq_pending,
    output wire [31:0] irq_enable,
    output wire        irq_global_enable
);

    // 只给需要保存的 CSR 分配触发器；misa、mstatush、机器信息 CSR 为固定值，
    // mip 由外部中断电平实时构成，因此它们都没有独立存储寄存器。
    reg [31:0] mstatus;
    reg [31:0] mie;
    reg [31:0] mtvec;
    reg [31:0] mscratch;
    reg [31:0] mepc;
    reg [31:0] mcause;
    reg [31:0] mtval;

    // mip 的 MEIP[11]、MTIP[7]、MSIP[3] 显示原始中断电平。
    // mie 和 mstatus.MIE 只影响“是否响应”，不屏蔽软件读取到的 pending。
    // 板级异步输入的双触发器同步或脉冲保持由后续 SoC 层完成。
    assign irq_pending = (irq_external ? 32'h0000_0800 : 32'b0) |
                         (irq_timer    ? 32'h0000_0080 : 32'b0) |
                         (irq_software ? 32'h0000_0008 : 32'b0);
    assign irq_enable = mie;
    assign irq_global_enable = mstatus[`RV_MSTATUS_MIE_BIT];
    // 当前 mtvec 强制 Direct 模式，所以 trap 入口始终是 mtvec 基址。
    // 本模块只提供地址，不在这里修改 CPU 的 PC。
    assign trap_target = mtvec;
    assign mret_target = mepc;

    // 只读“地址”与 CSR 内部的只读“字段”不同：
    // 写机器信息 CSR 属于非法访问；写 misa/mstatush 的固定值字段或
    // mip 的硬件输入字段，访问合法但不会改变其值。
    assign csr_readonly_addr = (csr_addr == `RV_CSR_MVENDORID) ||
                               (csr_addr == `RV_CSR_MARCHID) ||
                               (csr_addr == `RV_CSR_MIMPID) ||
                               (csr_addr == `RV_CSR_MHARTID) ||
                               (csr_addr == `RV_CSR_MCONFIGPTR);
    assign csr_access_illegal = (csr_read_en || csr_write_intent) &&
                               (!csr_exists ||
                                 (csr_write_intent && csr_readonly_addr));

    // 已实现地址白名单。地址不存在时由上层把 csr_access_illegal 转为非法指令异常。
    always @* begin
        csr_exists = 1'b1;
        case (csr_addr)
            `RV_CSR_MSTATUS, `RV_CSR_MISA, `RV_CSR_MIE,
            `RV_CSR_MTVEC, `RV_CSR_MSTATUSH, `RV_CSR_MSCRATCH,
            `RV_CSR_MEPC, `RV_CSR_MCAUSE, `RV_CSR_MTVAL,
            `RV_CSR_MIP, `RV_CSR_MVENDORID, `RV_CSR_MARCHID,
            `RV_CSR_MIMPID, `RV_CSR_MHARTID,
            `RV_CSR_MCONFIGPTR: ;
            default: csr_exists = 1'b0;
        endcase
    end

    // 组合读：CSR 指令在 WB 上升沿前即可得到旧值，用于写回 rd 和计算新值。
    // 不请求读取或地址不存在时返回零；零数据本身不表示访问合法。
    always @* begin
        csr_rdata = 32'b0;
        if (csr_read_en && csr_exists) begin
            case (csr_addr)
                `RV_CSR_MSTATUS:   csr_rdata = mstatus;
                `RV_CSR_MISA:      csr_rdata = `RV_MISA_RV32I;
                `RV_CSR_MIE:       csr_rdata = mie;
                `RV_CSR_MTVEC:     csr_rdata = mtvec;
                `RV_CSR_MSTATUSH:  csr_rdata = 32'b0;
                `RV_CSR_MSCRATCH:  csr_rdata = mscratch;
                `RV_CSR_MEPC:      csr_rdata = mepc;
                `RV_CSR_MCAUSE:    csr_rdata = mcause;
                `RV_CSR_MTVAL:     csr_rdata = mtval;
                `RV_CSR_MIP:       csr_rdata = irq_pending;
                `RV_CSR_MVENDORID,
                `RV_CSR_MARCHID,
                `RV_CSR_MIMPID,
                `RV_CSR_MHARTID,
                `RV_CSR_MCONFIGPTR: csr_rdata = 32'b0;
                default:           csr_rdata = 32'b0;
            endcase
        end
    end

    // 所有可变 CSR 由同一个时序块驱动，避免多个 always 块同时写同一寄存器。
    // 上层应保证提交事件互斥；若误同时出现，优先级为复位 > trap > MRET > CSR 写。
    always @(posedge clk) begin
        if (!resetn) begin
            // 同步复位：MIE/MPIE 为零，MPP 固定为 M(2'b11)；其他可变 CSR 清零。
            mstatus  <= `RV_MSTATUS_RESET;
            mie      <= 32'b0;
            mtvec    <= {MTVEC_RESET_ADDR[31:2], `RV_MTVEC_DIRECT_MODE};
            mscratch <= 32'b0;
            mepc     <= 32'b0;
            mcause   <= 32'b0;
            mtval    <= 32'b0;
        end else if (trap_enter) begin
            // 故障指令 PC 或排空后的中断续执行 PC 写入 mepc；无 C 扩展，低两位固定零。
            // mcause[31]=1 表示中断，低五位保存原因；mtval 保存上层提供的故障信息。
            mepc    <= {trap_pc[31:2], 2'b00};
            mcause  <= {trap_is_interrupt, 26'b0, trap_cause};
            mtval   <= trap_tval;
            // 进入 trap：旧 MIE -> MPIE，然后清 MIE；MPP 始终为 M。
            mstatus <= `RV_MSTATUS_RESET |
                       (mstatus[`RV_MSTATUS_MIE_BIT] ? 32'h0000_0080 : 32'b0);
        end else if (mret_commit) begin
            // MRET：MPIE -> MIE，MPIE 置 1，MPP 保持 M；PC 重定向由上层完成。
            mstatus <= `RV_MSTATUS_RESET |
                       (mstatus[`RV_MSTATUS_MPIE_BIT] ? 32'h0000_0008 : 32'b0) |
                       32'h0000_0080;
        end else if (csr_commit && csr_write_intent && !csr_access_illegal) begin
            // 普通 CSR 写：先由 CPU 算出候选值，再在这里施加各寄存器的写掩码/WARL 约束。
            case (csr_addr)
                `RV_CSR_MSTATUS:  mstatus  <= `RV_MSTATUS_RESET |
                                               (csr_wdata & `RV_MSTATUS_RW_MASK);
                `RV_CSR_MIE:      mie      <= csr_wdata & `RV_MIE_RW_MASK;
                `RV_CSR_MTVEC:    mtvec    <= {csr_wdata[31:2], `RV_MTVEC_DIRECT_MODE};
                `RV_CSR_MSCRATCH: mscratch <= csr_wdata;
                `RV_CSR_MEPC:     mepc     <= {csr_wdata[31:2], 2'b00};
                `RV_CSR_MCAUSE:   mcause   <= {csr_wdata[31], 26'b0, csr_wdata[4:0]};
                `RV_CSR_MTVAL:    mtval    <= csr_wdata;
                // misa、mstatush、mip：地址可访问，但首版已实现字段写入无效果。
                default: ;
            endcase
        end
    end
endmodule
