`timescale 1ns/1ps

module tb_coremark_zmmul;
    localparam real TBIT=1.0e9/115200.0;
    reg clk=0, resetn=0;
    always #(1.0e9/93750000.0/2.0) clk=~clk;
    wire txd;
    wire [27:0] awaddr, araddr;
    wire awvalid, arvalid, awready, arready, wready, rvalid;
    wire [255:0] wdata, rdata;
    wire [31:0] wstrb;
    GTP_GRS GRS_INST (.GRS_N(1'b1));
    soc_top #(.ENABLE_DDR(1), .DDR_MEM_DQ_WIDTH(32),
              .DDR_ADDR_MASK(32'hc0000000), .RESET_PC(32'h40000000),
              .INST_ROM_BASE(0), .DATA_RAM_BASE(0)) dut (
        .clk(clk), .resetn(resetn), .uart_rx(1'b1), .uart_tx(txd),
        .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0),
        .selftest_status(), .debug_wb_pc(), .debug_wb_rf_we(),
        .debug_wb_rf_wnum(), .debug_wb_rf_wdata(), .debug_inst(),
        .ddr_init_done(1'b1),
        .ddr_axi_awaddr(awaddr), .ddr_axi_awuser_ap(), .ddr_axi_awuser_id(),
        .ddr_axi_awlen(), .ddr_axi_awready(awready), .ddr_axi_awvalid(awvalid),
        .ddr_axi_wdata(wdata), .ddr_axi_wstrb(wstrb), .ddr_axi_wready(wready),
        .ddr_axi_wusero_id(4'd0), .ddr_axi_wusero_last(wready),
        .ddr_axi_araddr(araddr), .ddr_axi_aruser_ap(), .ddr_axi_aruser_id(),
        .ddr_axi_arlen(), .ddr_axi_arready(arready), .ddr_axi_arvalid(arvalid),
        .ddr_axi_rdata(rdata), .ddr_axi_rid(4'd0), .ddr_axi_rlast(rvalid),
        .ddr_axi_rvalid(rvalid)
    );
    mini_ddr_model_x32 memory(
        .clk(clk), .resetn(resetn), .awaddr(awaddr), .araddr(araddr),
        .awvalid(awvalid), .arvalid(arvalid), .awready(awready),
        .arready(arready), .wdata(wdata), .wstrb(wstrb), .wready(wready),
        .rdata(rdata), .rvalid(rvalid)
    );

    integer cycles=0, max_cycles=20000000, done_pc, retired=0;
    integer ar_count=0, aw_count=0, sent=0, decoded=0, uart_file, b;
    reg done=0, test_pass=0;
    integer mul_retired=0, matrix_mul_retired=0, k;
    reg [31:0] hot_pcs[0:4];
    string hot_file;
    reg [7:0] sent_bytes[0:8191], byte_value;
    string out_dir;
    initial begin
        if (!$value$plusargs("DONE=%h",done_pc) || !$value$plusargs("OUT=%s",out_dir))
            $fatal(1,"RESULT: FAIL missing DONE/OUT");
        void'($value$plusargs("MAX_CYCLES=%d",max_cycles));
        if (!$value$plusargs("HOT_PC_FILE=%s",hot_file)) $fatal(1,"RESULT: FAIL missing matrix MUL PCs");
        $readmemh(hot_file,hot_pcs);
        uart_file=$fopen({out_dir,"/uart.txt"},"wb");
        if (uart_file==0) $fatal(1,"RESULT: FAIL UART capture open");
        repeat (10) @(negedge clk); resetn=1;
    end
    always @(posedge clk) if (resetn) begin
        cycles=cycles+1;
        if (cycles>=max_cycles) $fatal(1,"RESULT: FAIL timeout pc=%h",dut.u_cpu.mem_wb_pc);
        // BSP timer probes use the supported M-mode ECALL (cause 11).
        if (dut.u_cpu.irq_take ||
            (dut.u_cpu.sync_trap_event && dut.u_cpu.wb_trap_cause!=11))
            $fatal(1,"RESULT: FAIL unexpected CPU trap/interrupt pc=%h cause=%0d",
                   dut.u_cpu.mem_wb_pc,dut.u_cpu.wb_trap_cause);
        if ((dut.inst_rsp_valid && dut.inst_rsp_error) ||
            (dut.data_rsp_valid && dut.data_rsp_error))
            $fatal(1,"RESULT: FAIL bus error");
        if (awvalid && awready) aw_count=aw_count+1;
        if (arvalid && arready) ar_count=ar_count+1;
        if (dut.u_cpu.normal_retire) begin
            retired=retired+1;
            if (dut.u_cpu.mem_wb_inst[6:0]==7'h33 && dut.u_cpu.mem_wb_inst[31:25]==7'h01 && !dut.u_cpu.mem_wb_inst[14]) begin
                mul_retired=mul_retired+1;
                for(k=0;k<5;k=k+1) if(dut.u_cpu.mem_wb_pc==hot_pcs[k]) matrix_mul_retired=matrix_mul_retired+1;
            end
            if (dut.u_cpu.mem_wb_pc==done_pc) done=1;
        end
        if (dut.u_uart_mmio.tx_send) begin
            if (sent>=8192) $fatal(1,"RESULT: FAIL UART capture overflow");
            sent_bytes[sent]=dut.u_uart_mmio.req_wdata[7:0]; sent=sent+1;
        end
    end
    initial forever begin
        @(negedge txd);
        if (resetn) begin
            #(TBIT/2);
            if (txd!==0) $fatal(1,"RESULT: FAIL UART start");
            for (b=0;b<8;b=b+1) begin #(TBIT); byte_value[b]=txd; end
            #(TBIT);
            if (txd!==1 || decoded>=sent || byte_value!==sent_bytes[decoded])
                $fatal(1,"RESULT: FAIL UART pin decode");
            $fwrite(uart_file,"%c",byte_value); $fflush(uart_file); decoded=decoded+1;
        end
    end
    initial begin
        wait(done);
        wait(!dut.u_uart_mmio.tx_busy);
        #(TBIT*12);
        if (decoded!=sent || decoded==0 || ar_count==0 || aw_count==0)
            $fatal(1,"RESULT: FAIL missing UART/DDR traffic");
        $fclose(uart_file);
        if (mul_retired==0 || matrix_mul_retired==0) $fatal(1,"RESULT: FAIL no actual hardware matrix MUL retired");
        test_pass=1;
        $display("RESULT: PASS coremark_zmmul_direct cycles=%0d retired=%0d AR=%0d AW=%0d UART=%0d MUL=%0d MATRIX_MUL=%0d",
                 cycles,retired,ar_count,aw_count,decoded,mul_retired,matrix_mul_retired);
        $finish;
    end
endmodule
