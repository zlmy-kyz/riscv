`timescale 1ns / 1ps

// CPU真正执行mmio_test.S，验证CPU、数据互连、MMIO和RAM整条路径。
module tb_mmio_test;
    parameter MAX_CYCLE = 5000;

    reg clk;
    reg resetn;
    integer cycles;
    integer mmio_request_count;
    integer ram_request_count;
    integer route_errors;

    wire [31:0] debug_wb_pc;
    wire [ 3:0] debug_wb_rf_we;
    wire [ 4:0] debug_wb_rf_wnum;
    wire [31:0] debug_wb_rf_wdata;
    wire [31:0] debug_inst;

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
        .debug_wb_pc       (debug_wb_pc),
        .debug_wb_rf_we    (debug_wb_rf_we),
        .debug_wb_rf_wnum  (debug_wb_rf_wnum),
        .debug_wb_rf_wdata (debug_wb_rf_wdata),
        .debug_inst        (debug_inst)
    );

    initial begin
        clk = 1'b0;
        forever #5 clk = ~clk;
    end

    initial begin
        resetn = 1'b0;
        cycles = 0;
        mmio_request_count = 0;
        ram_request_count = 0;
        route_errors = 0;
        repeat (8) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
    end

    always @(posedge clk) begin
        if (resetn) begin
            cycles = cycles + 1;

            if (dut.mmio_req_valid && dut.mmio_req_ready)
                mmio_request_count = mmio_request_count + 1;
            if (dut.ram_bus_req_valid && dut.ram_bus_req_ready)
                ram_request_count = ram_request_count + 1;

            // 一笔请求只能到达一个从机。
            if (dut.mmio_req_valid && dut.ram_bus_req_valid) begin
                route_errors = route_errors + 1;
                $display("ROUTE ERROR: RAM and MMIO selected together, addr=%08x",
                         dut.data_req_addr);
            end

            // 根据CPU完整地址检查片选方向。
            if (dut.data_req_valid && dut.data_req_ready) begin
                if ((dut.data_req_addr & 32'hffff_f000) == 32'h1000_0000) begin
                    if (!dut.mmio_req_valid || dut.ram_bus_req_valid) begin
                        route_errors = route_errors + 1;
                        $display("ROUTE ERROR: MMIO address routed incorrectly");
                    end
                end else if ((dut.data_req_addr & 32'hffff_c000) ==
                             32'h8000_0000) begin
                    if (!dut.ram_bus_req_valid || dut.mmio_req_valid) begin
                        route_errors = route_errors + 1;
                        $display("ROUTE ERROR: RAM address routed incorrectly");
                    end
                end
            end

            if (dut.data_write && dut.data_addr == 32'h8000_1000) begin
                if ((dut.data_wdata == 32'd1) &&
                    (dut.u_simple_mmio.scratch == 32'h1234_aa78) &&
                    (mmio_request_count == 5) &&
                    (ram_request_count == 1) &&
                    (route_errors == 0)) begin
                    $display("RESULT: PASS mmio_e2e cycles=%0d mmio_req=%0d ram_req=%0d scratch=%08x",
                             cycles, mmio_request_count, ram_request_count,
                             dut.u_simple_mmio.scratch);
                end else begin
                    $display("RESULT: FAIL mmio_e2e tohost=%08x mmio_req=%0d ram_req=%0d route_errors=%0d scratch=%08x",
                             dut.data_wdata, mmio_request_count,
                             ram_request_count, route_errors,
                             dut.u_simple_mmio.scratch);
                end
                $finish;
            end

            if (cycles >= MAX_CYCLE) begin
                $display("RESULT: TIMEOUT mmio_e2e pc=%08x gp=%08x mcause=%08x",
                         dut.u_cpu.pc, dut.u_cpu.u_regfile.rf[3],
                         dut.u_cpu.u_csr_file.mcause);
                $finish;
            end
        end
    end

endmodule
