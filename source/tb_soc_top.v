`timescale 1ns / 1ps
module tb_soc_top();
    reg clk;
    reg resetn;
    wire [31:0] debug_wb_pc;
    wire [3:0] debug_wb_rf_we;
    wire [4:0] debug_wb_rf_wnum;
    wire [31:0] debug_wb_rf_wdata;
    wire [31:0] debug_inst;
    wire [31:0] debug_x4;
    wire [31:0] debug_x15;
    wire [31:0] debug_x17;
    integer test_cycle;
    // riscv-tests 的链接入口为 0x8000_0000；其他测试台不覆写参数时仍从 0 启动。
    soc_top #(.RESET_PC(32'h8000_0000),
              .INST_REQ_STALL_CYCLES(2),    
              .INST_RSP_DELAY_CYCLES(5),
              .DATA_REQ_STALL_CYCLES(3),
              .DATA_RSP_DELAY_CYCLES(7)) u_soc(
        .clk(clk),
        .resetn(resetn),
        .irq_external(1'b0),
        .irq_software(1'b0),
        .irq_timer(1'b0),
        .ddr_init_done(1'b0),
        .ddr_axi_awready(1'b0),
        .ddr_axi_wready(1'b0),
        .ddr_axi_wusero_id(4'b0),
        .ddr_axi_wusero_last(1'b0),
        .ddr_axi_arready(1'b0),
        .ddr_axi_rdata(128'b0),
        .ddr_axi_rid(4'b0),
        .ddr_axi_rlast(1'b0),
        .ddr_axi_rvalid(1'b0),
        .debug_wb_pc(debug_wb_pc),
        .debug_wb_rf_we(debug_wb_rf_we),
        .debug_wb_rf_wnum(debug_wb_rf_wnum),
        .debug_wb_rf_wdata(debug_wb_rf_wdata),
        .debug_inst(debug_inst)
    );  
    assign debug_x4 = u_soc.u_cpu.u_regfile.rf[4];
    assign debug_x15 = u_soc.u_cpu.u_regfile.rf[15];
    assign debug_x17 = u_soc.u_cpu.u_regfile.rf[17];
    GTP_GRS GRS_INST (
        .GRS_N(1'b1)
    );

    initial begin
        clk = 1'b1;
        forever #5 clk = ~clk;
    end


    initial begin
        resetn = 1'b0;
        #35;
        resetn = 1'b1;
    end

    // riscv-tests 用 tohost 报告结果：1 表示通过，其他奇数为
    // (失败用例编号 << 1) | 1。必须看完整地址，不能看 RAM 的截断索引。
    always @(posedge clk) begin
        if (!resetn) begin
            test_cycle <= 0;
        end else begin
            test_cycle <= test_cycle + 1;
            if (u_soc.data_write &&
                u_soc.data_addr == 32'h8000_1000) begin
                if (u_soc.data_wdata == 32'd1)
                    $display("RESULT: PASS rv32ui-p-add, tohost=1, cycles=%0d", test_cycle);
                else
                    $display("RESULT: FAIL rv32ui-p-add, tohost=%08x, failed_test=%0d, cycles=%0d",
                             u_soc.data_wdata,
                             u_soc.data_wdata >> 1, test_cycle);
                $finish;
            end
            if (test_cycle >= 100000) begin
                $display("RESULT: TIMEOUT rv32ui-p-add, pc=%08x, gp=%08x, mcause=%08x",
                         u_soc.u_cpu.pc, u_soc.u_cpu.u_regfile.rf[3],
                         u_soc.u_cpu.u_csr_file.mcause);
                $finish;
            end
        end
    end
endmodule
