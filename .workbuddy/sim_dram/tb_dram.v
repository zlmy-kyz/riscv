`timescale 1ns / 1ps
// Minimum testbench: only the data_ram part, replicating tb_topcpu_instrom's stimulus
module tb_dram();
    reg clk;
    reg resetn;
    reg [31:0] wr_data;
    reg [9:0]  addr;
    reg wr_en;
    wire [31:0] rd_data;

    data_ram u_data_ram (
        .wr_data(wr_data),
        .addr(addr),
        .wr_en(wr_en),
        .wr_byte_en(4'b1111),
        .clk(clk),
        .rst(~resetn),
        .rd_data(rd_data)
    );

    GTP_GRS GRS_INST(.GRS_N(1'b1));

    // ---- probes: what the IP actually receives ----
    wire [9:0]  probe_ipm_addr   = u_data_ram.U_ipml_spram_data_ram.addr;
    wire        probe_cs_bit0    = u_data_ram.U_ipml_spram_data_ram.cs_bit0;
    wire        probe_cs_bit1    = u_data_ram.U_ipml_spram_data_ram.cs_bit1_bus[0];
    wire        probe_cs_bit2    = u_data_ram.U_ipml_spram_data_ram.cs_bit2_bus[0];
    wire        probe_wr_en_ipm  = u_data_ram.U_ipml_spram_data_ram.wr_en;
    wire        probe_wr_en_b    = u_data_ram.U_ipml_spram_data_ram.wr_en_b;
    wire        probe_clk_en     = u_data_ram.U_ipml_spram_data_ram.clk_en;
    wire        probe_ceb        = u_data_ram.U_ipml_spram_data_ram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.CEB;
    wire        probe_addrb_hold = u_data_ram.U_ipml_spram_data_ram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.ADDRB_HOLD;
    wire        probe_csb_reg    = u_data_ram.U_ipml_spram_data_ram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.csb_reg;
    wire        probe_web_reg    = u_data_ram.U_ipml_spram_data_ram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.web_reg;
    wire        probe_write_en_a = u_data_ram.U_ipml_spram_data_ram.ADDR_LOOP[0].DATA_LOOP[0].U_GTP_DRM36K_E1.write_en_a;

    initial begin
        $display("t(ns) | addr | cs0 cs1 cs2 | ipm.wr_en web | clk_en ceb | csb_reg web_reg | write_en_a | rd_data");
        forever begin
            @(posedge clk); #1;
            if ($time >= 85 && $time <= 165)
                $display("%5d | %4d |  %b   %b   %b  |    %b      %b  |   %b      %b  |    %b        %b    |   %b     | %h",
                    $time, probe_ipm_addr, probe_cs_bit0, probe_cs_bit1, probe_cs_bit2,
                    probe_wr_en_ipm, probe_wr_en_b, probe_clk_en, probe_ceb,
                    probe_csb_reg, probe_web_reg, probe_write_en_a,
                    ~resetn, rd_data);
        end
    end

    initial begin
        clk = 1'b1;
        forever #5 clk = ~clk;
    end

    initial begin
        resetn = 1'b0;
        wr_data = 32'h0; addr = 10'h0; wr_en = 1'b0;
        #95;
        resetn = 1'b1;
        #5;
        addr = 10'h0; wr_data = 32'hbbbbbbbb; wr_en = 1'b0;
        #10;
        addr = 10'h1;
        #10;
        wr_data = 32'haaaaaaaa; wr_en = 1'b1;
        #10;
        wr_en = 1'b0;
        #40;
        // read back both addresses
        addr = 10'h0; #20;
        $display("t=%0t  READ addr=0 -> rd_data=%h", $time, rd_data);
        addr = 10'h1; #20;
        $display("t=%0t  READ addr=1 -> rd_data=%h", $time, rd_data);
        #100;
        $finish;
    end

    // trace each posedge around the write window
    initial begin
        $display("t=%0t  start", $time);
        forever begin
            @(posedge clk);
            #1;
            if ($time > 90 && $time < 145)
                $display("t=%0t  addr=%0d wr_en=%b wr_data=%h rst=%b | rd_data=%h",
                         $time, addr, wr_en, wr_data, ~resetn, rd_data);
        end
    end

    // Dump the whole hierarchy so we can inspect the DRM array offline
    initial begin
        $dumpfile("dram.vcd");
        $dumpvars(0, tb_dram);
    end

    // also report the decoded 32-bit memory contents via the read port
    initial begin
        #170;
        $display("--- read-back through the port ---");
        #0 addr = 10'h0; #20;
        $display("addr=0 -> %h", rd_data);
        #0 addr = 10'h1; #20;
        $display("addr=1 -> %h", rd_data);
        #0 addr = 10'h2; #20;
        $display("addr=2 -> %h", rd_data);
        #0 addr = 10'h3; #20;
        $display("addr=3 -> %h", rd_data);
        #20;
        $finish;
    end
endmodule
