`timescale 1ns / 1ps

// Fast RV32I sweep through the same CPU, address decoders and DDR bridge.
// This Pango user-port memory model is for broad functional coverage only;
// tb_soc_ddr3_top.v remains the DDR3 IP + physical-model validation path.
module tb_soc_ddr3_rv32i_fast;
    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;
    initial begin #35 resetn = 1'b1; end

    wire [27:0] awaddr, araddr;
    wire awvalid, arvalid;
    wire [127:0] wdata;
    wire [15:0] wstrb;
    wire [31:0] debug_wb_pc;
    wire [3:0] debug_wb_rf_we;
    wire [4:0] debug_wb_rf_wnum;
    wire [31:0] debug_wb_rf_wdata;
    wire [31:0] debug_inst;
    reg [127:0] rdata;
    reg rvalid = 1'b0;

    soc_top #(.RESET_PC(32'h0000_0000), .ENABLE_DDR(1),
              .DDR_BASE(32'h8000_0000)) dut (
        .clk(clk), .resetn(resetn),
        .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0),
        .debug_wb_pc(debug_wb_pc), .debug_wb_rf_we(debug_wb_rf_we),
        .debug_wb_rf_wnum(debug_wb_rf_wnum),
        .debug_wb_rf_wdata(debug_wb_rf_wdata), .debug_inst(debug_inst),
        .ddr_init_done(1'b1),
        .ddr_axi_awaddr(awaddr), .ddr_axi_awvalid(awvalid),
        .ddr_axi_awready(1'b1), .ddr_axi_wdata(wdata),
        .ddr_axi_wstrb(wstrb), .ddr_axi_wready(1'b1),
        .ddr_axi_wusero_id(4'd1), .ddr_axi_wusero_last(1'b1),
        .ddr_axi_araddr(araddr), .ddr_axi_arvalid(arvalid),
        .ddr_axi_arready(1'b1), .ddr_axi_rdata(rdata),
        .ddr_axi_rid(4'd0), .ddr_axi_rlast(1'b1),
        .ddr_axi_rvalid(rvalid)
    );

    // A 128-bit beat corresponds to eight 16-bit DDR user-address units.
    reg [127:0] beats [0:4095];
    integer byte_index;
    always @(posedge clk) begin
        rvalid <= arvalid;
        if (arvalid)
            rdata <= beats[araddr[14:3]];
        if (awvalid)
            for (byte_index = 0; byte_index < 16; byte_index = byte_index + 1)
                if (wstrb[byte_index])
                    beats[awaddr[14:3]][byte_index * 8 +: 8] <=
                        wdata[byte_index * 8 +: 8];
    end

    string test_name;
    reg [31:0] tohost_addr;
    integer cycles = 0;
    integer loader_writes = 0;
    reg saw_ddr_fetch = 1'b0;
    initial begin
        if (!$value$plusargs("TEST=%s", test_name))
            $fatal(1, "missing +TEST=<name>");
        if (!$value$plusargs("TOHOST=%h", tohost_addr))
            $fatal(1, "missing +TOHOST=<hex address>");
    end

    always @(posedge clk) begin
        if (!resetn) begin
            cycles <= 0;
            loader_writes <= 0;
            saw_ddr_fetch <= 1'b0;
        end else begin
            cycles <= cycles + 1;
            if ((dut.inst_rsp_valid && dut.inst_rsp_error) ||
                (dut.data_rsp_valid && dut.data_rsp_error)) begin
                $display("RESULT: FAIL %s bus access fault pc=%h", test_name,
                         dut.u_cpu.pc);
                $finish;
            end
            if (dut.data_req_valid && dut.data_req_ready &&
                dut.data_req_write && dut.data_req_addr >= 32'h8000_0000 &&
                !saw_ddr_fetch)
                loader_writes <= loader_writes + 1;

            if (dut.inst_req_valid && dut.inst_req_ready &&
                dut.inst_req_addr == 32'h8000_0000 && !saw_ddr_fetch) begin
                if (loader_writes != dut.u_data_ram.words[4092] +
                                     dut.u_data_ram.words[4094]) begin
                    $display("RESULT: FAIL %s loader count got=%0d expected=%0d",
                             test_name, loader_writes,
                             dut.u_data_ram.words[4092] +
                             dut.u_data_ram.words[4094]);
                    $finish;
                end
                saw_ddr_fetch <= 1'b1;
                $display("CHECK: %s CPU loaded %0d words into DDR",
                         test_name, loader_writes);
            end
            if (saw_ddr_fetch &&
                dut.data_req_valid && dut.data_req_ready &&
                dut.data_req_write && dut.data_req_addr == tohost_addr) begin
                if (dut.data_req_wdata === 32'd1)
                    $display("RESULT: PASS %s DDR RV32I tohost=1 cycles=%0d",
                             test_name, cycles);
                else
                    $display("RESULT: FAIL %s DDR RV32I tohost=%h failed_test=%0d cycles=%0d",
                             test_name, dut.data_req_wdata,
                             dut.data_req_wdata >> 1, cycles);
                $finish;
            end
            if (cycles >= 200000) begin
                $display("RESULT: FAIL %s timeout fetch=%b copied=%0d pc=%h",
                         test_name, saw_ddr_fetch, loader_writes, dut.u_cpu.pc);
                $finish;
            end
        end
    end
endmodule
