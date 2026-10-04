`timescale 1ns / 1ps

// 验证互连错误响应被CPU转换为精确的load/store access fault。
module tb_access_fault_test;
    parameter MAX_CYCLE = 8000;

    reg clk;
    reg resetn;
    integer cycles;
    integer unmapped_request_count;
    integer error_response_count;
    integer trap_count;
    integer ram_request_count;
    integer mmio_request_count;
    integer route_errors;

    soc_top #(
        .RESET_PC(32'h8000_0000),
        .DATA_RAM_BASE(32'h8000_0000),
        .MMIO_BASE(32'h1000_0000),
        .INST_REQ_STALL_CYCLES(2),
        .INST_RSP_DELAY_CYCLES(5),
        .DATA_REQ_STALL_CYCLES(3),
        .DATA_RSP_DELAY_CYCLES(7)
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
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        resetn = 1'b0;
        cycles = 0;
        unmapped_request_count = 0;
        error_response_count = 0;
        trap_count = 0;
        ram_request_count = 0;
        mmio_request_count = 0;
        route_errors = 0;
        repeat (8) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
    end

    always @(posedge clk) begin
        if (resetn) begin
            cycles = cycles + 1;

            if (dut.ram_bus_req_valid && dut.ram_bus_req_ready)
                ram_request_count = ram_request_count + 1;
            if (dut.mmio_req_valid && dut.mmio_req_ready)
                mmio_request_count = mmio_request_count + 1;
            if (dut.data_rsp_valid && dut.data_rsp_error)
                error_response_count = error_response_count + 1;
            if (dut.u_cpu.sync_trap_event)
                trap_count = trap_count + 1;

            if (dut.data_req_valid && dut.data_req_ready &&
                ((dut.data_req_addr == 32'h2000_0000) ||
                 (dut.data_req_addr == 32'h2000_0004))) begin
                unmapped_request_count = unmapped_request_count + 1;
                if (dut.ram_bus_req_valid || dut.mmio_req_valid) begin
                    route_errors = route_errors + 1;
                    $display("ROUTE ERROR: unmapped address selected a slave, addr=%08x",
                             dut.data_req_addr);
                end
            end

            if (dut.data_write && dut.data_addr == 32'h8000_1000) begin
                if ((dut.data_wdata == 32'd1) &&
                    (unmapped_request_count == 2) &&
                    (error_response_count == 2) &&
                    (trap_count == 2) &&
                    (ram_request_count == 1) &&
                    (mmio_request_count == 0) &&
                    (route_errors == 0) &&
                    (dut.u_cpu.u_regfile.rf[7] == 32'h0000_0055) &&
                    (dut.u_cpu.u_regfile.rf[8] == 32'd2) &&
                    (dut.u_cpu.u_csr_file.mcause == 32'd7) &&
                    (dut.u_cpu.u_csr_file.mtval == 32'h2000_0004)) begin
                    $display("RESULT: PASS access_fault_e2e cycles=%0d unmapped=%0d errors=%0d traps=%0d",
                             cycles, unmapped_request_count,
                             error_response_count, trap_count);
                end else begin
                    $display("RESULT: FAIL access_fault_e2e tohost=%08x unmapped=%0d errors=%0d traps=%0d ram=%0d mmio=%0d route_errors=%0d x7=%08x x8=%08x mcause=%08x mtval=%08x",
                             dut.data_wdata, unmapped_request_count,
                             error_response_count, trap_count,
                             ram_request_count, mmio_request_count,
                             route_errors, dut.u_cpu.u_regfile.rf[7],
                             dut.u_cpu.u_regfile.rf[8],
                             dut.u_cpu.u_csr_file.mcause,
                             dut.u_cpu.u_csr_file.mtval);
                end
                $finish;
            end

            if (cycles >= MAX_CYCLE) begin
                $display("RESULT: TIMEOUT access_fault_e2e pc=%08x gp=%08x mcause=%08x mtval=%08x",
                         dut.u_cpu.pc, dut.u_cpu.u_regfile.rf[3],
                         dut.u_cpu.u_csr_file.mcause,
                         dut.u_cpu.u_csr_file.mtval);
                $finish;
            end
        end
    end

endmodule
