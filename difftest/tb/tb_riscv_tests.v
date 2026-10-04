`timescale 1ns / 1ps

`ifndef RISCV_TEST_TOHOST_ADDR
`define RISCV_TEST_TOHOST_ADDR 32'h8000_1000
`endif
`ifndef RISCV_TEST_INST_REQ_STALL_CYCLES
`define RISCV_TEST_INST_REQ_STALL_CYCLES 0
`endif
`ifndef RISCV_TEST_INST_RSP_DELAY_CYCLES
`define RISCV_TEST_INST_RSP_DELAY_CYCLES 0
`endif
`ifndef RISCV_TEST_DATA_REQ_STALL_CYCLES
`define RISCV_TEST_DATA_REQ_STALL_CYCLES 0
`endif
`ifndef RISCV_TEST_DATA_RSP_DELAY_CYCLES
`define RISCV_TEST_DATA_RSP_DELAY_CYCLES 0
`endif

// 通用 riscv-tests 测试台。rom.hex/ram.hex 由运行目录提供；
// 通过 CPU 数据总线真正接受的 store 观察 tohost。
module tb_riscv_tests;
    parameter MAX_CYCLE = 200000;
    // 大型测试的 .text/.data 布局可能把 tohost 放到 0x8000_2000；
    // 批量脚本可用 -DRISCV_TEST_TOHOST_ADDR=<address> 覆写默认值。
    parameter [31:0] TOHOST_ADDR = `RISCV_TEST_TOHOST_ADDR;
    parameter INST_REQ_STALL_CYCLES = `RISCV_TEST_INST_REQ_STALL_CYCLES;
    parameter INST_RSP_DELAY_CYCLES = `RISCV_TEST_INST_RSP_DELAY_CYCLES;
    parameter DATA_REQ_STALL_CYCLES = `RISCV_TEST_DATA_REQ_STALL_CYCLES;
    parameter DATA_RSP_DELAY_CYCLES = `RISCV_TEST_DATA_RSP_DELAY_CYCLES;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    integer cycles = 0;

    always #5 clk = ~clk;

    soc_top #(
        .RESET_PC(32'h8000_0000),
        .INST_REQ_STALL_CYCLES(INST_REQ_STALL_CYCLES),
        .INST_RSP_DELAY_CYCLES(INST_RSP_DELAY_CYCLES),
        .DATA_REQ_STALL_CYCLES(DATA_REQ_STALL_CYCLES),
        .DATA_RSP_DELAY_CYCLES(DATA_RSP_DELAY_CYCLES)
    ) dut (
        .clk               (clk),
        .resetn            (resetn),
        .irq_external      (1'b0),
        .irq_software      (1'b0),
        .irq_timer         (1'b0),
        .debug_wb_pc       (),
        .debug_wb_rf_we    (),
        .debug_wb_rf_wnum  (),
        .debug_wb_rf_wdata (),
        .debug_inst        ()
    );

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
    end

    always @(posedge clk) begin
        if (resetn) begin
            cycles = cycles + 1;
            if (dut.data_write && (dut.data_addr == TOHOST_ADDR)) begin
                if (dut.data_wdata == 32'd1)
                    $display("RESULT: PASS cycles=%0d", cycles);
                else
                    $display("RESULT: FAIL tohost=%08x failed_test=%0d cycles=%0d",
                             dut.data_wdata, dut.data_wdata >> 1, cycles);
                $finish;
            end
            if (cycles >= MAX_CYCLE) begin
                $display("RESULT: TIMEOUT pc=%08x gp=%08x mcause=%08x",
                         dut.u_cpu.pc, dut.u_cpu.u_regfile.rf[3],
                         dut.u_cpu.u_csr_file.mcause);
                $finish;
            end
        end
    end
endmodule
