`timescale 1ns / 1ps

// Pango AXI-like single-beat interface: AW/W have no WVALID or B channel;
// AR/R have no RREADY. This TB deliberately does not model AXI4.
module tb_ddr_bridge_wait_reset_scoreboard;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg resetn = 1'b0, ddr_init_done = 1'b0;
    reg inst_req_valid = 1'b0;
    reg [31:0] inst_req_addr = 0;
    wire inst_req_ready, inst_rsp_valid, inst_rsp_error;
    wire [31:0] inst_rsp_rdata;
    reg data_req_valid = 1'b0, data_req_write = 1'b0;
    reg [1:0] data_req_size = 2'd2;
    reg [31:0] data_req_addr = 0, data_req_wdata = 0;
    reg [3:0] data_req_wstrb = 0;
    wire data_req_ready, data_rsp_valid, data_rsp_error;
    wire [31:0] data_rsp_rdata;
    wire [27:0] axi_awaddr, axi_araddr;
    wire axi_awuser_ap, axi_aruser_ap;
    wire [3:0] axi_awuser_id, axi_awlen, axi_aruser_id, axi_arlen;
    wire axi_awvalid, axi_arvalid;
    wire [127:0] axi_wdata;
    wire [15:0] axi_wstrb;
    reg axi_awready = 0, axi_wready = 0, axi_arready = 0;
    reg [3:0] axi_wusero_id = 0, axi_rid = 0;
    reg axi_wusero_last = 0, axi_rlast = 0;
    reg [127:0] axi_rdata = 0;
    reg axi_rvalid = 0;

    dual_sram_to_pango_ddr_bridge dut (
        .clk(clk), .resetn(resetn), .ddr_init_done(ddr_init_done),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr),
        .inst_req_ready(inst_req_ready), .inst_rsp_valid(inst_rsp_valid),
        .inst_rsp_rdata(inst_rsp_rdata), .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(data_req_write),
        .data_req_size(data_req_size), .data_req_addr(data_req_addr),
        .data_req_wdata(data_req_wdata), .data_req_wstrb(data_req_wstrb),
        .data_req_ready(data_req_ready), .data_rsp_valid(data_rsp_valid),
        .data_rsp_rdata(data_rsp_rdata), .data_rsp_error(data_rsp_error),
        .axi_awaddr(axi_awaddr), .axi_awuser_ap(axi_awuser_ap),
        .axi_awuser_id(axi_awuser_id), .axi_awlen(axi_awlen),
        .axi_awvalid(axi_awvalid), .axi_awready(axi_awready),
        .axi_wdata(axi_wdata), .axi_wstrb(axi_wstrb),
        .axi_wready(axi_wready), .axi_wusero_id(axi_wusero_id),
        .axi_wusero_last(axi_wusero_last),
        .axi_araddr(axi_araddr), .axi_aruser_ap(axi_aruser_ap),
        .axi_aruser_id(axi_aruser_id), .axi_arlen(axi_arlen),
        .axi_arvalid(axi_arvalid), .axi_arready(axi_arready),
        .axi_rdata(axi_rdata), .axi_rid(axi_rid),
        .axi_rlast(axi_rlast), .axi_rvalid(axi_rvalid)
    );

    // Separate reference and device-side memories, 64 128-bit beats.
    reg [7:0] reference [0:1023];
    reg [7:0] device_mem [0:1023];
    reg [31:0] random_state;
    integer transactions = 0, writes = 0, reads = 0, resets = 0;
    integer i, j, seed, d;
    reg [31:0] a, v;
    reg [3:0] mask;

    function [27:0] ctrl_addr(input [31:0] byte_addr);
        ctrl_addr = (byte_addr >> 1) & 28'hfff_fff8;
    endfunction

    function [127:0] model_beat(input [31:0] byte_addr);
        integer k, base;
        begin
            base = byte_addr & 32'hffff_fff0;
            model_beat = 0;
            for (k = 0; k < 16; k = k + 1)
                model_beat[k*8 +: 8] = device_mem[base+k];
        end
    endfunction

    function [31:0] expected_word(input [31:0] byte_addr);
        integer k, base;
        begin
            base = byte_addr & 32'hffff_fffc;
            expected_word = 0;
            for (k = 0; k < 4; k = k + 1)
                expected_word[k*8 +: 8] = reference[base+k];
        end
    endfunction

    task check_mem;
        integer k;
        begin
            for (k = 0; k < 1024; k = k + 1)
                if (device_mem[k] !== reference[k])
                    $fatal(1, "RESULT: FAIL memory byte %0d device=%02x expected=%02x",
                           k, device_mem[k], reference[k]);
        end
    endtask

    task check_quiet;
        begin
            if (axi_awvalid !== 0 || axi_arvalid !== 0 ||
                inst_rsp_valid !== 0 || data_rsp_valid !== 0)
                $fatal(1, "RESULT: FAIL stale command or duplicate response");
        end
    endtask

    task take_write(input [31:0] addr, input [31:0] word,
                    input [3:0] strb);
        begin
            @(negedge clk);
            data_req_addr = addr; data_req_wdata = word;
            data_req_wstrb = strb; data_req_write = 1; data_req_valid = 1;
            #1;
            if (data_req_ready !== 1 || inst_req_ready !== 0)
                $fatal(1, "RESULT: FAIL write request acceptance");
            @(posedge clk); #1;
            @(negedge clk); data_req_valid = 0;
        end
    endtask

    task take_read(input bit instruction, input [31:0] addr);
        begin
            @(negedge clk);
            if (instruction) begin
                inst_req_addr = addr; inst_req_valid = 1;
            end else begin
                data_req_addr = addr; data_req_write = 0;
                data_req_wstrb = 0; data_req_valid = 1;
            end
            #1;
            if ((instruction ? inst_req_ready : data_req_ready) !== 1)
                $fatal(1, "RESULT: FAIL read request acceptance");
            @(posedge clk); #1;
            @(negedge clk);
            inst_req_valid = 0; data_req_valid = 0;
        end
    endtask

    task check_aw(input [31:0] addr, input [31:0] word,
                  input [3:0] strb);
        reg [127:0] want_data;
        reg [15:0] want_strb;
        begin
            want_data = {96'b0, word} << (addr[3:2] * 32);
            want_strb = {12'b0, strb} << (addr[3:2] * 4);
            if (axi_awvalid !== 1 || axi_awaddr !== ctrl_addr(addr) ||
                axi_awlen !== 0 || axi_awuser_id !== 1 ||
                axi_awuser_ap !== 0 || axi_wdata !== want_data ||
                axi_wstrb !== want_strb)
                $fatal(1, "RESULT: FAIL AW/W addr=%08x actual=%07x data=%032x strb=%04x",
                       addr, axi_awaddr, axi_wdata, axi_wstrb);
        end
    endtask

    task check_ar(input bit instruction, input [31:0] addr);
        begin
            if (axi_arvalid !== 1 || axi_araddr !== ctrl_addr(addr) ||
                axi_arlen !== 0 || axi_aruser_ap !== 0 ||
                axi_aruser_id !== (instruction ? 4'd0 : 4'd1))
                $fatal(1, "RESULT: FAIL AR addr=%08x actual=%07x id=%d",
                       addr, axi_araddr, axi_aruser_id);
        end
    endtask

    task commit_write(input [31:0] addr, input [31:0] word,
                      input [3:0] strb);
        integer k, base;
        begin
            base = addr & 32'hffff_fff0;
            for (k = 0; k < 16; k = k + 1)
                if (axi_wstrb[k]) device_mem[base+k] = axi_wdata[k*8 +: 8];
            base = addr & 32'hffff_fffc;
            for (k = 0; k < 4; k = k + 1)
                if (strb[k]) reference[base+k] = word[k*8 +: 8];
            check_mem();
        end
    endtask

    task check_response(input bit instruction, input bit write_access,
                        input [31:0] addr);
        reg [31:0] got;
        begin
            #1;
            if (instruction) begin
                if (inst_rsp_valid !== 1 || data_rsp_valid !== 0 ||
                    inst_rsp_error !== 0)
                    $fatal(1, "RESULT: FAIL instruction response routing");
                got = inst_rsp_rdata;
            end else begin
                if (data_rsp_valid !== 1 || inst_rsp_valid !== 0 ||
                    data_rsp_error !== 0)
                    $fatal(1, "RESULT: FAIL data response routing");
                got = data_rsp_rdata;
            end
            if (!write_access && got !== expected_word(addr))
                $fatal(1, "RESULT: FAIL response addr=%08x got=%08x expected=%08x",
                       addr, got, expected_word(addr));
            @(posedge clk); #1;
            check_quiet();
        end
    endtask

    task do_write(input [31:0] addr, input [31:0] word,
                  input [3:0] strb, input integer aw_wait,
                  input integer w_wait);
        integer k;
        begin
            take_write(addr, word, strb);
            for (k = 0; k < aw_wait; k = k + 1) begin
                #1; check_aw(addr, word, strb);
                if (data_req_ready !== 0 || inst_req_ready !== 0 ||
                    data_rsp_valid !== 0 || inst_rsp_valid !== 0)
                    $fatal(1, "RESULT: FAIL early write acceptance/response");
                @(posedge clk); #1; @(negedge clk);
            end
            check_aw(addr, word, strb);
            axi_awready = 1;
            axi_wready = (w_wait == 0);
            #1; check_aw(addr, word, strb);
            @(posedge clk); #1;
            @(negedge clk); axi_awready = 0; axi_wready = 0;
            if (w_wait != 0) begin
                for (k = 0; k < w_wait; k = k + 1) begin
                    #1;
                    if (axi_wdata !== ({96'b0, word} << (addr[3:2]*32)) ||
                        axi_wstrb !== ({12'b0, strb} << (addr[3:2]*4)) ||
                        data_req_ready !== 0 || inst_req_ready !== 0 ||
                        data_rsp_valid !== 0 || inst_rsp_valid !== 0)
                        $fatal(1, "RESULT: FAIL W changed during stall");
                    @(posedge clk); #1; @(negedge clk);
                end
                axi_wready = 1;
                @(posedge clk); #1;
                @(negedge clk); axi_wready = 0;
            end
            commit_write(addr, word, strb);
            check_response(0, 1, addr);
            transactions = transactions + 1; writes = writes + 1;
        end
    endtask

    // r_wait=-1 returns RVALID in the same cycle as the AR handshake.
    task do_read(input bit instruction, input [31:0] addr,
                 input integer ar_wait, input integer r_wait);
        integer k;
        begin
            take_read(instruction, addr);
            for (k = 0; k < ar_wait; k = k + 1) begin
                #1; check_ar(instruction, addr);
                if (inst_req_ready !== 0 || data_req_ready !== 0 ||
                    inst_rsp_valid !== 0 || data_rsp_valid !== 0)
                    $fatal(1, "RESULT: FAIL early read acceptance/response");
                @(posedge clk); #1; @(negedge clk);
            end
            check_ar(instruction, addr);
            axi_arready = 1;
            if (r_wait == -1) begin
                axi_rdata = model_beat(addr); axi_rvalid = 1;
                axi_rid = instruction ? 0 : 1; axi_rlast = 1;
            end
            #1; check_ar(instruction, addr);
            @(posedge clk); #1;
            @(negedge clk); axi_arready = 0; axi_rvalid = 0;
            if (r_wait >= 0) begin
                for (k = 0; k < r_wait; k = k + 1) begin
                    #1;
                    if (axi_arvalid !== 0 || inst_req_ready !== 0 ||
                        data_req_ready !== 0 || inst_rsp_valid !== 0 ||
                        data_rsp_valid !== 0)
                        $fatal(1, "RESULT: FAIL R wait state");
                    @(posedge clk); #1; @(negedge clk);
                end
                axi_rdata = model_beat(addr); axi_rvalid = 1;
                axi_rid = instruction ? 0 : 1; axi_rlast = 1;
                @(posedge clk); #1;
                @(negedge clk); axi_rvalid = 0;
            end
            check_response(instruction, 0, addr);
            transactions = transactions + 1; reads = reads + 1;
        end
    endtask

    task reset_and_recover(input integer phase);
        begin
            @(negedge clk);
            resetn = 0; ddr_init_done = 0;
            inst_req_valid = 0; data_req_valid = 0;
            axi_arready = 0; axi_awready = 0;
            axi_rvalid = 0; axi_wready = 0;
            @(posedge clk); #1;
            check_quiet(); check_mem();
            @(negedge clk); resetn = 1;
            inst_req_valid = 1; data_req_valid = 1;
            #1;
            if (inst_req_ready !== 0 || data_req_ready !== 0)
                $fatal(1, "RESULT: FAIL accepted before DDR reinit phase=%0d", phase);
            @(posedge clk); #1;
            @(negedge clk);
            inst_req_valid = 0; data_req_valid = 0;
            ddr_init_done = 1;
            #1; check_quiet();
            resets = resets + 1;
            $display("CHECK: reset phase=%0d canceled outstanding bridge work", phase);
            // The transaction after each reset must use the same memory.
            do_read(0, 32'h0000_0034, 2, 3);
        end
    endtask

    task reset_cases;
        begin
            // 1: accepted read, AR held.
            take_read(1, 32'h34);
            #1; check_ar(1, 32'h34);
            reset_and_recover(1);
            // 2: AR accepted, RVALID still absent.
            take_read(0, 32'h38);
            axi_arready = 1;
            #1; check_ar(0, 32'h38);
            @(posedge clk); #1;
            @(negedge clk); axi_arready = 0;
            reset_and_recover(2);
            // 3: RVALID sampled, response must be canceled before CPU sees it.
            take_read(1, 32'h3c);
            axi_arready = 1;
            @(posedge clk); #1;
            @(negedge clk); axi_arready = 0;
            axi_rdata = model_beat(32'h3c); axi_rvalid = 1;
            @(posedge clk); #1;
            if (inst_rsp_valid !== 1) $fatal(1, "RESULT: FAIL read RSP setup");
            reset_and_recover(3);
            // 4: accepted write, AW held.
            take_write(32'h40, 32'h12345678, 4'hf);
            #1; check_aw(32'h40, 32'h12345678, 4'hf);
            reset_and_recover(4);
            // 5: AW accepted, WREADY still absent.
            take_write(32'h44, 32'h87654321, 4'hf);
            axi_awready = 1;
            @(posedge clk); #1;
            @(negedge clk); axi_awready = 0;
            reset_and_recover(5);
            // 6: WREADY accepted; memory commits but CPU response is canceled.
            take_write(32'h48, 32'hcafef00d, 4'hf);
            axi_awready = 1; axi_wready = 1;
            #1; check_aw(32'h48, 32'hcafef00d, 4'hf);
            @(posedge clk); #1;
            if (data_rsp_valid !== 1) $fatal(1, "RESULT: FAIL write RSP setup");
            commit_write(32'h48, 32'hcafef00d, 4'hf);
            reset_and_recover(6);
            do_read(0, 32'h48, 1, 1);
        end
    endtask

    initial begin
        #200000;
        $fatal(1, "RESULT: FAIL scoreboard timeout");
    end

    initial begin
        seed = 1;
        if ($value$plusargs("SEED=%d", seed)) begin end
        if (seed == 0) seed = 1;
        random_state = seed;
        for (i = 0; i < 1024; i = i + 1) begin
            reference[i] = (i * 13 + 8'h5a) & 8'hff;
            device_mem[i] = reference[i];
        end
        repeat (3) @(posedge clk);
        @(negedge clk); resetn = 1; ddr_init_done = 1;

        // Each delay 0..7 is exercised on all four Pango phases.
        for (d = 0; d < 8; d = d + 1) begin
            a = (d * 16) + ((d % 4) * 4);
            v = 32'h1020_3040 ^ (32'h0101_0101 * d);
            do_write(a, v, 4'hf, d, 7-d);
            do_read(d[0], a, 7-d, d);
        end
        // Partial writes at every 32-bit slot, with byte mask expansion.
        for (d = 0; d < 4; d = d + 1) begin
            a = 32'h100 + d*4;
            do_write(a+1, 32'h0000_a500, 4'b0010, d, d+1);
            do_read(0, a, d, 2);
            do_read(1, a, 1, -1);
        end
        // Explicit same-cycle AR/R and AW/W handshakes.
        do_write(32'h1fc, 32'h55aa_6699, 4'hf, 0, 0);
        do_read(1, 32'h1fc, 0, -1);

        // Fixed-seed constrained traffic, including zero and partial masks.
        for (j = 0; j < 128; j = j + 1) begin
            random_state = random_state * 32'd1664525 + 32'd1013904223;
            a = ((random_state >> 4) & 32'h3f) * 16 +
                ((random_state >> 10) & 3) * 4;
            v = random_state ^ (random_state << 13);
            mask = (random_state >> 16) & 4'hf;
            if (j % 3 == 0)
                do_write(a, v, mask, (random_state >> 20) & 7,
                         (random_state >> 24) & 7);
            else
                do_read(j[0], a, (random_state >> 20) & 7,
                        (random_state >> 24) & 7);
        end
        reset_cases();
        check_mem();
        $display("RESULT: PASS bridge wait/reset scoreboard seed=%0d transactions=%0d writes=%0d reads=%0d resets=%0d",
                 seed, transactions, writes, reads, resets);
        $finish;
    end
endmodule
