`timescale 1ns / 1fs

// Real data interconnect + old MMIO + UART. Master follows CPU valid/ready
// protocol; response delay exercises a held request without a second handshake.
module tb_uart_mmio;
    localparam real CLK_NS = 1.0e9 / 93_750_000.0;
    localparam real BIT_NS = 1.0e9 / 115_200.0;
    localparam [31:0] BASE = 32'h1000_1000;
    reg clk = 0, resetn = 0, rx = 1;
    reg valid = 0, write = 0;
    reg [1:0] size = 2;
    reg [31:0] addr = 0, wdata = 0;
    reg [3:0] strb = 0;
    wire ready, rsp_valid, rsp_error, tx, uart_irq;
    wire [31:0] rdata;
    wire uv, uw, ur, usv, uart_rsp_err;
    wire [1:0] usize;
    wire [31:0] ua, ud, usd;
    wire [3:0] ust;
    wire mv, mw, mr, msv, mse;
    wire [1:0] msize;
    wire [31:0] ma, md, msd;
    wire [3:0] mst;
    wire ramv, ddrv;
    reg ramrsp = 0, ddrrsp = 0;
    reg test_pass = 0;
    integer accepted = 0, responses = 0, pops = 0, starts = 0;
    integer frames = 0, overflows = 0;
    integer decoded = 0, i;
    reg [7:0] expected_tx [0:8];
    reg [7:0] hello [0:4];
    reg [31:0] result;
    reg result_error;

    always #(CLK_NS / 2.0) clk = ~clk;
    data_bus_interconnect #(.RAM_BASE(0), .ENABLE_DDR(1), .ENABLE_UART(1)) bus (
        .clk(clk), .resetn(resetn), .m_req_valid(valid), .m_req_write(write),
        .m_req_size(size), .m_req_addr(addr), .m_req_wdata(wdata), .m_req_wstrb(strb),
        .m_req_ready(ready), .m_rsp_valid(rsp_valid), .m_rsp_rdata(rdata), .m_rsp_error(rsp_error),
        .ram_req_valid(ramv), .ram_req_write(), .ram_req_size(), .ram_req_addr(),
        .ram_req_wdata(), .ram_req_wstrb(), .ram_req_ready(1'b1),
        .ram_rsp_valid(ramrsp), .ram_rsp_rdata(32'h1234abcd), .ram_rsp_error(1'b0),
        .mmio_req_valid(mv), .mmio_req_write(mw), .mmio_req_size(msize), .mmio_req_addr(ma),
        .mmio_req_wdata(md), .mmio_req_wstrb(mst), .mmio_req_ready(mr),
        .mmio_rsp_valid(msv), .mmio_rsp_rdata(msd), .mmio_rsp_error(mse),
        .ddr_req_valid(ddrv), .ddr_req_write(), .ddr_req_size(), .ddr_req_addr(),
        .ddr_req_wdata(), .ddr_req_wstrb(), .ddr_req_ready(1'b1),
        .ddr_rsp_valid(ddrrsp), .ddr_rsp_rdata(32'hdd330055), .ddr_rsp_error(1'b0),
        .uart_req_valid(uv), .uart_req_write(uw), .uart_req_size(usize), .uart_req_addr(ua),
        .uart_req_wdata(ud), .uart_req_wstrb(ust), .uart_req_ready(ur),
        .uart_rsp_valid(usv), .uart_rsp_rdata(usd), .uart_rsp_error(uart_rsp_err)
    );
    uart_mmio #(.RSP_DELAY_CYCLES(6)) uart (
        .clk(clk), .resetn(resetn), .req_valid(uv), .req_write(uw), .req_size(usize),
        .req_addr(ua), .req_wdata(ud), .req_wstrb(ust), .req_ready(ur),
        .rsp_valid(usv), .rsp_rdata(usd), .rsp_error(uart_rsp_err), .uart_rx(rx), .uart_tx(tx), .uart_irq(uart_irq)
    );
    simple_mmio old_mmio (
        .clk(clk), .resetn(resetn), .req_valid(mv), .req_write(mw), .req_size(msize),
        .req_addr(ma), .req_wdata(md), .req_wstrb(mst), .req_ready(mr),
        .rsp_valid(msv), .rsp_rdata(msd), .rsp_error(mse), .test_status()
    );

    task check;
        input condition;
        input [1023:0] message;
        begin
            if (condition !== 1'b1) begin
                $display("RESULT: FAIL uart_mmio t=%0t: %0s", $time, message);
                $fatal(1, "%0s", message);
            end
        end
    endtask
    always @(posedge clk) begin
        ramrsp <= resetn && ramv;
        ddrrsp <= resetn && ddrv;
        if (resetn) begin
            check(({3'd0,ramv} + {3'd0,mv} + {3'd0,uv} + {3'd0,ddrv}) <= 1,
                  "multiple address targets selected");
            if (valid && ready) accepted = accepted + 1;
            if (rsp_valid) responses = responses + 1;
            if (uart.fifo_pop) pops = pops + 1;
            if (uart.tx_send) starts = starts + 1;
            if (uart.frame_error) frames = frames + 1;
            if (uart.overflow) overflows = overflows + 1;
        end
    end

    task transact;
        input wr;
        input [31:0] address, data;
        input [3:0] mask;
        input [1:0] access_size;
        input integer held_cycles;
        integer before_accept, before_response;
        begin
            @(negedge clk);
            before_accept = accepted; before_response = responses;
            valid = 1; write = wr; addr = address; wdata = data; strb = mask; size = access_size;
            @(posedge clk);
            while (!ready) @(posedge clk);
            #0.002;
            if (held_cycles > 0) repeat (held_cycles) begin
                @(negedge clk);
                check(!ready, "held request must remain blocked after its single acceptance");
            end
            else @(negedge clk);
            valid = 0;
            // Change the master address while waiting: response target/data
            // must be latched and must not follow this unrelated RAM address.
            addr = 32'h0000_0020;
            while (!rsp_valid) @(negedge clk);
            result = rdata; result_error = rsp_error;
            @(negedge clk);
            check(accepted == before_accept + 1 && responses == before_response + 1,
                  "one request must have exactly one handshake and one response");
        end
    endtask
    task read_status;
        begin
            transact(0, BASE+8, 0, 0, 2, 0);
            check(!result_error && result[31:8] == 0, "STATUS read/reserved bits");
        end
    endtask
    task put_byte;
        input [7:0] value;
        input [1:0] access_size;
        input [3:0] mask;
        begin
            read_status;
            while (!result[0]) read_status;
            transact(1, BASE, {24'd0,value}, mask, access_size, 5);
            check(!result_error, "polled TX store must succeed");
        end
    endtask
    task wave;
        input [7:0] value;
        input stop;
        integer bit_no;
        begin
            #1.731; rx = 0; #(BIT_NS);
            for (bit_no=0; bit_no<8; bit_no=bit_no+1) begin
                rx = value[bit_no]; #(BIT_NS);
            end
            rx = stop; #(BIT_NS); rx = 1; #(BIT_NS/2.0);
        end
    endtask
    task get_byte;
        input [7:0] value;
        input integer hold;
        integer before_pop;
        begin
            before_pop = pops;
            transact(0, BASE+4, 0, 0, 2, hold);
            check(!result_error && result === {24'd0,value}, "RX_DATA return value");
            check(pops == before_pop + 1, "one RX read must pop exactly once");
        end
    endtask
    task control;
        input [31:0] value;
        begin
            transact(1, BASE+12, value, 4'b1111, 2, 0);
            check(!result_error, "CONTROL W1C store");
        end
    endtask

    reg [7:0] received;
    integer rx_bit;
    always begin
        @(negedge tx);
        if (resetn) begin
            check(decoded < 9, "extra TX frame from repeated request or masked/busy store");
            #(BIT_NS/2.0); check(tx === 0, "TX start bit");
            for (rx_bit=0; rx_bit<8; rx_bit=rx_bit+1) begin
                #(BIT_NS); received[rx_bit] = tx;
            end
            #(BIT_NS); check(tx === 1, "TX stop bit");
            check(received === expected_tx[decoded], "independent TX serial byte/LSB order");
            decoded = decoded + 1;
        end
    end

    integer before_pop, before_start;
    initial begin
        hello[0]="H"; hello[1]="e"; hello[2]="l"; hello[3]="l"; hello[4]="o";
        expected_tx[0]="H";
        for (i=0; i<5; i=i+1) expected_tx[i+1]=hello[i];
        expected_tx[6]=8'h55; expected_tx[7]=8'haa; expected_tx[8]=8'h80;
        repeat (5) @(negedge clk); resetn=1;
        read_status; check(result == 1, "reset STATUS must be TX_READY only");
        put_byte("H", 2, 15);
        read_status; check(result[1:0] == 2, "TX busy STATUS");
        transact(1, BASE, "X", 15, 2, 5);
        check(result_error, "busy TX write must error without sending X");
        for (i=0; i<5; i=i+1) put_byte(hello[i], 2, 15);
        put_byte(8'h55, 0, 1); put_byte(8'haa, 1, 3); put_byte(8'h80, 2, 15);
        read_status; while (!result[0]) read_status;
        before_start=starts;
        transact(1, BASE+1, 32'h00005800, 2, 0, 0);
        check(!result_error && starts==before_start, "SB upper lane must not start TX");
        transact(1, BASE+2, 32'h12340000, 12, 1, 0);
        check(!result_error && starts==before_start, "SH upper lanes must not start TX");
        transact(1, BASE, 32'h58, 0, 2, 0);
        check(!result_error && starts==before_start, "zero write mask must not start TX");
        $display("CHECK: STATUS reset/TX busy/Hello serial/SB SH SW/masked stores PASS");

        for (i=0; i<5; i=i+1) wave(hello[i],1);
        read_status; check(result[2], "RX_NOT_EMPTY after pin stimulus");
        before_pop=pops;
        repeat (8) read_status;
        check(pops==before_pop && uart.fifo_count==5, "STATUS reads have no side effects");
        for (i=0; i<5; i=i+1) get_byte(hello[i],5);
        wave("A",1); wave("B",1); wave("C",1);
        before_pop=pops;
        transact(0, BASE+5,0,0,0,5);
        check(!result_error && result[31:8]==0 && pops==before_pop, "upper byte RX read must not pop");
        get_byte("A",5); check(uart.fifo_count==2, "held read consumed only A");
        get_byte("B",5); get_byte("C",5);
        before_pop=pops;
        repeat (3) begin
            transact(0, BASE+4,0,0,2,5);
            check(!result_error && result===0 && pops==before_pop, "empty read zero/no pop");
        end
        read_status; check(!result[2], "RX empty status after reads");
        $display("CHECK: pin RX Hello/FIFO order/held A B C read/empty/status side effects PASS");

        wave(8'h96,0);
        #(2*BIT_NS);
        read_status; check(result[4] && !result[2] && frames==1, "frame error sticky and no error byte");
        control(0); read_status; check(result[4], "W1C zero must not clear");
        control(1); read_status; check(!result[4], "W1C frame only");
        // Clear arrives exactly on the edge that consumes a fresh error pulse.
        fork
            wave(8'h96,0);
            begin @(posedge uart.frame_error); control(1); end
        join
        read_status; check(result[4], "new frame event wins over same-edge W1C");
        control(1);

        for (i=0; i<16; i=i+1) wave(8'h40+i,1);
        fork
            wave(8'hee,1);
            begin @(posedge uart.overflow); control(2); end
        join
        #(2*BIT_NS);
        read_status; check(result[5:2]==4'b1011 && overflows==1, "full/overflow sticky and event wins over clear");
        wave(8'h96,0);
        read_status; check(result[5:4]==3, "both sticky flags set");
        control(0); read_status; check(result[5:4]==3, "W1C zero preserves both flags");
        transact(1,BASE+13,32'h00000300,2,0,0);
        read_status; check(result[5:4]==3, "masked CONTROL must not clear flags");
        control(1); read_status; check(result[5:4]==2, "W1C 1 clears frame only");
        wave(8'h96,0);
        control(2); read_status; check(result[5:4]==1, "W1C 2 clears overflow only");
        wave(8'hef,1);
        control(3); read_status; check(result[5:4]==0, "W1C 3 clears both");
        for (i=0; i<16; i=i+1) get_byte(8'h40+i,5);
        read_status; check(result==1, "overflow did not overwrite old bytes or change TX");
        $display("CHECK: frame/overflow sticky/W1C 0 1 2 3/set priority/full old-data preservation PASS");

        transact(0,BASE+16,0,0,2,0); check(result_error && result==0, "UART +10 unmapped fault");
        transact(1,BASE+20,0,15,2,0); check(result_error, "UART +14 unmapped fault");
        transact(1,BASE+8,0,15,2,0); check(result_error, "STATUS is read only");
        transact(1,BASE+4,0,15,2,0); check(result_error, "RX_DATA is read only");
        transact(0,BASE,0,0,2,0); check(result_error, "TX_DATA is write only");
        transact(0,BASE+5,0,0,2,0); check(result_error, "misaligned word request error");
        transact(0,0,0,0,2,0); check(!result_error && result==32'h1234abcd, "RAM routing unchanged");
        transact(0,32'h40000000,0,0,2,0); check(!result_error && result==32'hdd330055, "DDR routing unchanged");
        transact(1,32'h10000000,32'habcd,15,2,0); check(!result_error, "old MMIO write");
        transact(0,32'h10000000,0,0,2,0); check(!result_error && result==32'habcd, "old MMIO read");
        transact(0,32'h20000000,0,0,2,0); check(result_error, "unmapped response unchanged");
        $display("CHECK: 16-byte decode/unmapped/access permissions/old RAM MMIO DDR PASS");

        // RX IRQ commands use byte lane 1, leaving the old low W1C independent.
        transact(0,BASE+12,0,0,2,0); check(result==0, "CONTROL still reads zero");
        transact(1,BASE+12,32'h100,1,2,0);
        check(!uart_irq && !uart.rx_irq_enable, "masked IRQ set command ignored");
        transact(1,BASE+12,32'h100,4,2,0);
        check(!uart.rx_irq_enable, "upper lanes cannot change IRQ enable");
        transact(1,BASE+13,32'h100,2,2,0);
        check(result_error && !uart.rx_irq_enable, "invalid aligned access cannot enable IRQ");
        transact(1,BASE+13,32'h100,2,0,5);
        read_status; check(result==32'h41 && !uart_irq, "SB enable with empty FIFO");
        wave("Q",1);
        read_status; check(result==32'hc5 && uart_irq, "RX data holds enabled level IRQ");
        control(0); control(3);
        check(uart_irq && uart.rx_irq_enable, "old low W1C and zero preserve enable");
        control(32'h200);
        read_status; check(result==5 && !uart_irq, "disable preserves FIFO for polling");
        get_byte("Q",5);
        wave("R",1);
        check(!uart_irq, "disabled plus data must not assert IRQ");
        transact(1,BASE+12,32'h100,3,1,5);
        check(uart_irq, "SH enable acts on already queued data");
        get_byte("R",5);
        check(!uart_irq && uart.rx_irq_enable, "last pop drops IRQ while enable stays set");
        control(32'h300);
        check(!uart.rx_irq_enable, "disable wins over simultaneous set/clear");
        control(32'h100); wave("S",1);
        check(uart_irq, "nonempty IRQ before reset");
        @(negedge clk) resetn=0;
        repeat(5) @(negedge clk);
        check(!uart_irq && uart.fifo_empty && tx==1 && !uart.rx_irq_enable, "reset clears IRQ enable and FIFO");
        resetn=1;
        read_status; check(result==1, "polling reset STATUS unchanged");
        $display("CHECK: RX IRQ reset/SB SH SW/lane mask/invalid access/W1C compatibility/held level/last pop/disable priority PASS");
        #(12*BIT_NS);
        check(decoded==9 && starts==9 && responses==accepted, "no lost/duplicate TX or bus response");
        $display("RESULT: PASS uart_mmio; TX=%0d requests=%0d responses=%0d pops=%0d",decoded,accepted,responses,pops);
        test_pass=1; $finish;
    end
    initial begin #10_000_000; check(0,"UART MMIO timeout"); end
endmodule
