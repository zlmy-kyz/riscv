`timescale 1ns / 1ps

module tb_inst_access_fault_test;
    parameter MAX_CYCLE = 8000;

    reg clk;
    reg resetn;
    integer cycles;
    integer unmapped_fetch_count;
    integer error_response_count;
    integer trap_count;
    integer ram_request_count;
    integer route_errors;

    soc_top #(
        .RESET_PC(32'h8000_0000),
        .INST_ROM_BASE(32'h8000_0000),
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
        unmapped_fetch_count = 0;
        error_response_count = 0;
        trap_count = 0;
        ram_request_count = 0;
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
            if (dut.inst_rsp_valid && dut.inst_rsp_error)
                error_response_count = error_response_count + 1;
            if (dut.u_cpu.sync_trap_event)
                trap_count = trap_count + 1;

            if (dut.inst_req_valid && dut.inst_req_ready &&
                ((dut.inst_req_addr & 32'hffff_c000) != 32'h8000_0000)) begin
                unmapped_fetch_count = unmapped_fetch_count + 1;
                if (dut.rom_bus_req_valid) begin
                    route_errors = route_errors + 1;
                    $display("ROUTE ERROR: unmapped instruction selected ROM, addr=%08x",
                             dut.inst_req_addr);
                end
            end

            if (dut.data_write && dut.data_addr == 32'h8000_1000) begin
                if ((dut.data_wdata == 32'd1) &&
                    (unmapped_fetch_count >= 1) &&
                    (error_response_count >= 1) &&
                    (trap_count == 1) &&
                    (ram_request_count == 1) &&
                    (route_errors == 0) &&
                    (dut.u_cpu.u_regfile.rf[3] == 32'd1) &&
                    (dut.u_cpu.u_csr_file.mcause == 32'd1) &&
                    (dut.u_cpu.u_csr_file.mtval == 32'h8000_4000)) begin
                    $display("RESULT: PASS inst_access_fault_e2e cycles=%0d unmapped_fetch=%0d errors=%0d traps=%0d",
                             cycles, unmapped_fetch_count,
                             error_response_count, trap_count);
                end else begin
                    $display("RESULT: FAIL inst_access_fault_e2e tohost=%08x unmapped_fetch=%0d errors=%0d traps=%0d ram=%0d route_errors=%0d gp=%08x mcause=%08x mtval=%08x mepc=%08x",
                             dut.data_wdata, unmapped_fetch_count,
                             error_response_count, trap_count,
                             ram_request_count, route_errors,
                             dut.u_cpu.u_regfile.rf[3],
                             dut.u_cpu.u_csr_file.mcause,
                             dut.u_cpu.u_csr_file.mtval,
                             dut.u_cpu.u_csr_file.mepc);
                end
                $finish;
            end

            if (cycles >= MAX_CYCLE) begin
                $display("RESULT: TIMEOUT inst_access_fault_e2e pc=%08x gp=%08x mcause=%08x mtval=%08x",
                         dut.u_cpu.pc, dut.u_cpu.u_regfile.rf[3],
                         dut.u_cpu.u_csr_file.mcause,
                         dut.u_cpu.u_csr_file.mtval);
                $finish;
            end
        end
    end

endmodule
