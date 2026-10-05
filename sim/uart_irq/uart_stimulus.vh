localparam real BIT_NS=1.0e9/115_200.0;
reg [31:0] queue_pc=0, mmio_pc=0;
wire [31:0] phase=dut.u_data_ram.mem[192];
integer fifo_peak=0, rx_pops=0, rx_frames=0, buffer_byte;
integer store_irq_wait=0, mmio_irq_wait=0;
integer queue_requests=0, mmio_requests=0, queue_retires=0, mmio_retires=0;
reg [7:0] expected_rx [0:9];
reg previous_pop_last=0;
task send_byte;
    input [7:0] value;
    integer bit_number;
    begin
        rx=0; #(BIT_NS);
        for(bit_number=0;bit_number<8;bit_number=bit_number+1) begin rx=value[bit_number]; #(BIT_NS); end
        rx=1; #(BIT_NS);
    end
endtask
initial begin
    if (!$value$plusargs("QUEUE_LOAD=%h",queue_pc)) queue_pc=0;
    if (!$value$plusargs("WAIT_MMIO=%h",mmio_pc)) mmio_pc=0;
    expected_rx[0]="D"; expected_rx[1]="H"; expected_rx[2]="H";
    expected_rx[3]="e"; expected_rx[4]="l"; expected_rx[5]="l";
    expected_rx[6]="o"; expected_rx[7]=8'ha5; expected_rx[8]=8'hb6; expected_rx[9]="Z";
    wait(resetn);
    if (test_case==100) begin
        write_delay=14000; read_delay=70000;
        wait(phase==1); #113.317; send_byte("D");
        wait(phase==3); #271.153; send_byte("H");
        wait(phase==4 && read_pending && !read_address[11]);
        #317.417;
        send_byte("H"); send_byte("e"); send_byte("l"); send_byte("l"); send_byte("o");
        wait(phase==5 && write_pending); #193.113; send_byte(8'ha5);
        wait(phase==6 && dut.u_uart_mmio.pending && dut.u_cpu.ex_mem_pc==mmio_pc);
        #157.317; send_byte(8'hb6);
        wait(phase==7); #293.417; send_byte("Z");
    end
end
always @(negedge clk) if (resetn && test_case==100) begin
    check(dut.uart_irq===(dut.u_uart_mmio.rx_irq_enable && !dut.u_uart_mmio.fifo_empty),"UART IRQ must be enable AND FIFO nonempty");
    check(tx===1,"RX-only test must leave TX idle high");
    if (previous_pop_last) check(!dut.uart_irq,"last FIFO pop must remove IRQ before MMIO response");
    if (phase==1 || phase==2) check(irqs==0,"disabled RX or enabled empty FIFO caused interrupt");
    if (phase==7) check(irqs==4 && !dut.uart_irq && !dut.u_uart_mmio.rx_irq_enable,"disable command/polling caused IRQ");
end
always @(posedge clk) if (resetn && test_case==100) begin
    previous_pop_last=0;
    if (dut.u_uart_mmio.fifo_count>fifo_peak) fifo_peak=dut.u_uart_mmio.fifo_count;
    if (dut.u_uart_mmio.rx_valid) rx_frames=rx_frames+1;
    if (dut.u_uart_mmio.fifo_pop) begin
        check(rx_pops<10 && dut.u_uart_mmio.fifo_data===expected_rx[rx_pops],"FIFO byte lost/repeated/out of order");
        if (rx_pops==0 || rx_pops==9) check(!dut.uart_irq,"polling with IRQ disabled");
        else check(dut.uart_irq && !dut.u_cpu.u_csr_file.mstatus[3],"ISR pop must occur under held level IRQ, MIE cleared");
        previous_pop_last=dut.u_uart_mmio.fifo_count==1;
        rx_pops=rx_pops+1;
    end
    if (dut.u_cpu.data_req_fire) begin
        if (dut.u_cpu.id_ex_pc==queue_pc) queue_requests=queue_requests+1;
        if (dut.u_cpu.id_ex_pc==mmio_pc) mmio_requests=mmio_requests+1;
    end
    if (dut.u_cpu.normal_retire) begin
        if (dut.u_cpu.mem_wb_pc==queue_pc) queue_retires=queue_retires+1;
        if (dut.u_cpu.mem_wb_pc==mmio_pc) mmio_retires=mmio_retires+1;
    end
    if (dut.uart_irq && dut.u_cpu.ex_mem_valid && !dut.data_rsp_valid) begin
        if (dut.u_cpu.ex_mem_pc==target_pc) store_irq_wait=store_irq_wait+1;
        if (dut.u_cpu.ex_mem_pc==mmio_pc) mmio_irq_wait=mmio_irq_wait+1;
    end
    if (dut.u_cpu.irq_take) begin
        check(dut.uart_irq && dut.u_cpu.irq_cause==11 && !irq_external,"real UART external IRQ source/cause");
        if (phase==4) check(fifo_peak>=5 && ddr_reads==1 && queue_retires==1,"multi-byte queue / DDR read before IRQ");
        if (phase==5) check(store_irq_wait>0 && ddr_writes==1 && target_retired==1 && target_requests==1,"UART IRQ duplicated/preempted waiting DDR store");
        if (phase==6) check(mmio_irq_wait>0 && mmio_retires==1 && mmio_requests==1,"UART IRQ duplicated/preempted MMIO load");
    end
    check(!dut.u_uart_mmio.frame_error_status && !dut.u_uart_mmio.overflow_status,"unexpected RX framing/overflow");
end
initial begin
    wait(resetn);
    if (test_case==100) begin
        wait(selftest==2);
        repeat(100) @(negedge clk);
        check(irqs==4 && mrets==4 && faults==0 && ref_rf[23]==4 && ref_rf[27]==8,"ISR/MRET/byte counts");
        check(ref_rf[20]==32'h8000000b && ref_rf[21]===saved_mepc && ref_rf[22]==0,"software CSR readback in UART ISR");
        check(rx_frames==10 && rx_pops==10 && dut.u_uart_mmio.fifo_empty && !dut.uart_irq,"RX/FIFO drain counts or residue");
        check(target_requests==1 && target_retired==1 && foreground_resume==1 && ddr_writes==1 && ddr_reads==1,"waiting DDR transaction/resume count");
        check(queue_requests==1 && queue_retires==1 && mmio_requests==1 && mmio_retires==1,"waiting loads repeated or missing");
        check(beats[0][63:32]==85 && ref_rf[10]==32'h12345678 && ref_rf[12]==32'h41,"DDR/MMIO load-store data");
        for(buffer_byte=0;buffer_byte<10;buffer_byte=buffer_byte+1)
            check(dut.u_data_ram.mem[512+buffer_byte/4][(buffer_byte%4)*8+:8]===expected_rx[buffer_byte],"software receive buffer mismatch");
        check(dut.u_cpu.u_csr_file.mstatus[3] && accepted==responses,"MRET restored execution with no pending bus transaction");
        if (EXEC_FROM_DDR) check(ddr_instruction_reads>0,"DDR instruction fetch path not exercised");
        $display("RESULT: PASS UART RX IRQ: pin_bytes=%0d pops=%0d ISR=%0d MRET=%0d FIFO_peak=%0d DDR_store_IRQ_wait=%0d MMIO_load_IRQ_wait=%0d DDR_W=%0d DDR_R=%0d req=%0d rsp=%0d",rx_frames,rx_pops,irqs,mrets,fifo_peak,store_irq_wait,mmio_irq_wait,ddr_writes,ddr_reads,accepted,responses);
        $finish;
    end
end
