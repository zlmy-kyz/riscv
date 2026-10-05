`timescale 1ns / 1fs

// Real CPU + soc_top, simulation-only ROM/RAM. Runs uart_poll.S; pin stimulus
// and TX decoder are independent of DUT UART logic, no forced bus transactions.
module tb_soc_uart_cpu;
    localparam real CLK_NS = 1.0e9 / 93_750_000.0;
    localparam real BIT_NS = 1.0e9 / 115_200.0;
    reg clk=0, resetn=0, rx=1;
    wire tx;
    wire [1:0] selftest;
    reg test_pass=0;
    reg [7:0] hello [0:4];
    integer decoded=0, i;
    integer tx_stores=0, rx_loads=0, status_loads=0;
    soc_top #(.INST_REQ_STALL_CYCLES(2), .INST_RSP_DELAY_CYCLES(3),
              .DATA_REQ_STALL_CYCLES(2), .DATA_RSP_DELAY_CYCLES(3)) dut (
        .clk(clk), .resetn(resetn), .uart_rx(rx), .uart_tx(tx),
        .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0),
        .selftest_status(selftest),
        .debug_wb_pc(), .debug_wb_rf_we(), .debug_wb_rf_wnum(),
        .debug_wb_rf_wdata(), .debug_inst(),
        .ddr_init_done(1'b0), .ddr_axi_awaddr(), .ddr_axi_awuser_ap(),
        .ddr_axi_awuser_id(), .ddr_axi_awlen(), .ddr_axi_awready(1'b0),
        .ddr_axi_awvalid(), .ddr_axi_wdata(), .ddr_axi_wstrb(),
        .ddr_axi_wready(1'b0), .ddr_axi_wusero_id(4'd0), .ddr_axi_wusero_last(1'b0),
        .ddr_axi_araddr(), .ddr_axi_aruser_ap(), .ddr_axi_aruser_id(),
        .ddr_axi_arlen(), .ddr_axi_arready(1'b0), .ddr_axi_arvalid(),
        .ddr_axi_rdata(128'd0), .ddr_axi_rid(4'd0), .ddr_axi_rlast(1'b0), .ddr_axi_rvalid(1'b0)
    );
    always #(CLK_NS/2.0) clk=~clk;
    task check;
        input condition;
        input [1023:0] message;
        begin
            if (condition !== 1'b1) begin
                $display("RESULT: FAIL soc_uart_cpu: %0s",message);
                $fatal(1,"%0s",message);
            end
        end
    endtask
    always @(posedge clk) if (resetn) begin
        if (dut.data_rsp_valid) check(!dut.data_rsp_error,"CPU received unexpected bus fault");
        if (dut.uart_req_valid && dut.uart_req_ready) begin
            if (dut.uart_req_addr == 0 && dut.uart_req_write) tx_stores=tx_stores+1;
            if (dut.uart_req_addr == 4 && !dut.uart_req_write) rx_loads=rx_loads+1;
            if (dut.uart_req_addr == 8 && !dut.uart_req_write) status_loads=status_loads+1;
        end
        check(selftest != 3,"CPU software reported RX compare failure");
    end
    reg [7:0] received;
    integer bit_no;
    always begin
        @(negedge tx);
        if (resetn) begin
            check(decoded < 5,"CPU produced extra serial byte");
            #(BIT_NS/2.0); check(tx === 0,"CPU TX start bit");
            for (bit_no=0;bit_no<8;bit_no=bit_no+1) begin
                #(BIT_NS); received[bit_no]=tx;
            end
            #(BIT_NS); check(tx === 1,"CPU TX stop bit");
            check(received === hello[decoded],"CPU TX Hello byte/LSB mismatch");
            decoded=decoded+1;
        end
    end
    initial begin
        hello[0]="H";hello[1]="e";hello[2]="l";hello[3]="l";hello[4]="o";
        repeat (6) @(negedge clk); resetn=1;
        #1000.317;
        for (i=0;i<5;i=i+1) begin
            rx=0; #(BIT_NS);
            for (integer n=0;n<8;n=n+1) begin rx=hello[i][n]; #(BIT_NS); end
            rx=1; #(BIT_NS);
        end
    end
    initial begin
        wait(selftest == 2 && decoded == 5);
        #(12*BIT_NS);
        check(decoded==5 && tx_stores==5 && rx_loads==5 && status_loads>5 && dut.u_uart_mmio.fifo_empty,
              "CPU polling counts/duplicate pop/TX or FIFO residue");
        $display("RESULT: PASS soc_uart_cpu; real CPU SB/SH/SW TX Hello, LBU/LB/LHU/LH/LW RX Hello; polls=%0d",status_loads);
        test_pass=1; $finish;
    end
    initial begin #3_000_000; check(0,"CPU UART timeout"); end
endmodule
