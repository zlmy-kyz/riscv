`ifndef MYRISCV_CSR_DEFS_VH
`define MYRISCV_CSR_DEFS_VH

// 首版异常与中断机制实现的 M 模式 CSR 地址。
`define RV_CSR_MSTATUS    12'h300
`define RV_CSR_MISA       12'h301
`define RV_CSR_MIE        12'h304
`define RV_CSR_MTVEC      12'h305
`define RV_CSR_MSTATUSH   12'h310
`define RV_CSR_MSCRATCH   12'h340
`define RV_CSR_MEPC       12'h341
`define RV_CSR_MCAUSE     12'h342
`define RV_CSR_MTVAL      12'h343
`define RV_CSR_MIP        12'h344
`define RV_CSR_MVENDORID  12'hf11
`define RV_CSR_MARCHID    12'hf12
`define RV_CSR_MIMPID     12'hf13
`define RV_CSR_MHARTID    12'hf14
`define RV_CSR_MCONFIGPTR 12'hf15

// 首版实现的 mstatus、mie 和 mip 位位置及掩码。
`define RV_MSTATUS_MIE_BIT    3
`define RV_MSTATUS_MPIE_BIT   7
`define RV_MSTATUS_MPP_MSB   12
`define RV_MSTATUS_MPP_LSB   11
`define RV_IRQ_SOFTWARE_BIT   3
`define RV_IRQ_TIMER_BIT      7
`define RV_IRQ_EXTERNAL_BIT  11
`define RV_MSTATUS_RW_MASK   32'h0000_0088
`define RV_MIE_RW_MASK       32'h0000_0888
`define RV_MIP_INPUT_MASK    32'h0000_0888

// 复位值与支持的架构模式；mtvec 仅采用 Direct 模式。
`define RV_MSTATUS_RESET     32'h0000_1800
`define RV_MISA_RV32I        32'h4000_0100
`define RV_MTVEC_RESET       32'h0000_0100
`define RV_MTVEC_DIRECT_MODE 2'b00
`define RV_MCAUSE_INTERRUPT  32'h8000_0000

// 同步异常原因编号；访问失败 1/5/7 留待后续总线错误响应阶段接入。
`define RV_EXC_INST_ADDR_MISALIGNED 5'd0
`define RV_EXC_INST_ACCESS_FAULT    5'd1
`define RV_EXC_ILLEGAL_INST         5'd2
`define RV_EXC_BREAKPOINT           5'd3
`define RV_EXC_LOAD_ADDR_MISALIGNED 5'd4
`define RV_EXC_LOAD_ACCESS_FAULT    5'd5
`define RV_EXC_STORE_ADDR_MISALIGNED 5'd6
`define RV_EXC_STORE_ACCESS_FAULT   5'd7
`define RV_EXC_ECALL_M              5'd11

// 机器中断原因编号；写入 mcause 时还需将最高位置 1。
`define RV_IRQ_CAUSE_SOFTWARE 5'd3
`define RV_IRQ_CAUSE_TIMER    5'd7
`define RV_IRQ_CAUSE_EXTERNAL 5'd11

`endif
