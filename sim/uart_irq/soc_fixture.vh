// Test-only Pango user-port model: AW/W backpressure and delayed read response.
// Writes occur once at WREADY; this is the project's AXI-like port, no WVALID.
localparam real CLK_NS = 1.0e9 / 93_750_000.0;
reg clk=0, resetn=0, rx=1;
reg irq_external=0, irq_software=0, irq_timer=0;
wire tx;
wire [1:0] selftest;
wire [27:0] awaddr, araddr;
wire awvalid, arvalid;
wire [127:0] wdata;
wire [15:0] wstrb;
reg [127:0] rdata=0;
reg rvalid=0, write_pending=0, read_pending=0;
integer aw_wait=0, ar_wait=0, write_wait=0, read_wait=0;
integer write_delay=30, read_delay=40;
integer ddr_writes=0, ddr_reads=0, ddr_instruction_reads=0;
reg [27:0] write_address, read_address;
reg [127:0] saved_wdata;
reg [15:0] saved_wstrb;
reg [127:0] beats [0:511];
reg [31:0] code_words [0:4095];
wire awready = awvalid && !write_pending && aw_wait >= 5;
wire arready = arvalid && !read_pending && ar_wait >= 7;
wire wready = write_pending && write_wait == 0;
soc_top #(.ENABLE_DDR(1), .RESET_PC(PROGRAM_BASE), .INST_ROM_BASE(0), .DATA_RAM_BASE(0),
          .INST_REQ_STALL_CYCLES(1),
          .INST_RSP_DELAY_CYCLES(2), .DATA_REQ_STALL_CYCLES(2),
          .DATA_RSP_DELAY_CYCLES(3), .UART_RSP_DELAY_CYCLES(10000)) dut (
    .clk(clk), .resetn(resetn), .uart_rx(rx), .uart_tx(tx),
    .irq_external(irq_external), .irq_software(irq_software), .irq_timer(irq_timer),
    .selftest_status(selftest),
    .debug_wb_pc(), .debug_wb_rf_we(), .debug_wb_rf_wnum(), .debug_wb_rf_wdata(), .debug_inst(),
    .ddr_init_done(1'b1), .ddr_axi_awaddr(awaddr), .ddr_axi_awuser_ap(),
    .ddr_axi_awuser_id(), .ddr_axi_awlen(), .ddr_axi_awready(awready),
    .ddr_axi_awvalid(awvalid), .ddr_axi_wdata(wdata), .ddr_axi_wstrb(wstrb),
    .ddr_axi_wready(wready), .ddr_axi_wusero_id(4'd0), .ddr_axi_wusero_last(wready),
    .ddr_axi_araddr(araddr), .ddr_axi_aruser_ap(), .ddr_axi_aruser_id(),
    .ddr_axi_arlen(), .ddr_axi_arready(arready), .ddr_axi_arvalid(arvalid),
    .ddr_axi_rdata(rdata), .ddr_axi_rid(4'd0), .ddr_axi_rlast(rvalid), .ddr_axi_rvalid(rvalid)
);
always #(CLK_NS/2.0) clk=~clk;
integer fixture_i, lane;
initial begin
    for (fixture_i=0;fixture_i<512;fixture_i=fixture_i+1) beats[fixture_i]={4{32'h12345678}};
    if (EXEC_FROM_DDR) begin
        $readmemh("rom.hex",code_words);
        // Same linked relative branches at DDR+0x1000; mtvec remains ROM 0x400.
        for (fixture_i=0;fixture_i<256;fixture_i=fixture_i+1)
            beats[256+fixture_i/4][(fixture_i%4)*32+:32]=code_words[fixture_i];
    end
end
always @(posedge clk) begin
    rvalid <= 0;
    if (!resetn) begin
        aw_wait<=0; ar_wait<=0; write_pending<=0; read_pending<=0;
    end else begin
        if (awvalid && !awready) aw_wait<=aw_wait+1;
        if (awvalid && awready) begin
            write_pending<=1; write_wait<=write_delay; aw_wait<=0;
            write_address<=awaddr; saved_wdata<=wdata; saved_wstrb<=wstrb;
        end
        if (write_pending && write_wait>0) write_wait<=write_wait-1;
        if (wready) begin
            check(write_address[27:12]==0,"DDR write outside test memory");
            for (lane=0;lane<16;lane=lane+1)
                if (saved_wstrb[lane]) beats[write_address[11:3]][lane*8+:8]<=saved_wdata[lane*8+:8];
            ddr_writes=ddr_writes+1; write_pending<=0;
        end
        if (arvalid && !arready) ar_wait<=ar_wait+1;
        if (arvalid && arready) begin
            read_pending<=1; read_wait<=araddr[11] ? 3 : read_delay; ar_wait<=0; read_address<=araddr;
            if (araddr[11]) ddr_instruction_reads=ddr_instruction_reads+1;
            else ddr_reads=ddr_reads+1;
        end
        if (read_pending && read_wait>0) read_wait<=read_wait-1;
        if (read_pending && read_wait==0) begin
            check(read_address[27:12]==0,"DDR read outside test memory");
            rdata<=beats[read_address[11:3]]; rvalid<=1; read_pending<=0;
        end
    end
end
