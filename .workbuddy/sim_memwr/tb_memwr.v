`timescale 1ns / 1ps
//=============================================================================
// tb_memwr.v
//   Demo: EX stage issues a write request -> the memory value is actually
//   written on the NEXT rising edge of clk.
//
//   Uses the real Pango data_ram IP (official simulation model), so the write
//   really happens and can be read back for verification.
//
//   ASCII-only output so it survives any console encoding.
//=============================================================================
module tb_memwr ();

    reg clk;
    reg resetn;

    // ---- stand-ins for the ID/EX pipeline register outputs ----
    reg        id_ex_valid;
    reg        id_ex_mem_wen;
    reg        id_ex_mem_ren;
    reg [31:0] id_ex_rd_data1;   // x[rs1]
    reg [31:0] id_ex_rd_data2;   // data to store
    reg [31:0] id_ex_imm;

    wire [31:0] ex_addr;
    wire        ex_mem_wen;
    wire        ex_mem_ren;
    wire [31:0] dram_addr;
    wire        dram_wr_en;
    wire [31:0] dram_wr_data;
    wire [3:0]  dram_wr_byte_en;
    wire [31:0] dram_rd_data;
    wire [31:0] mem_rd_data;
    wire        mem_rd_valid;

    wire [9:0] ram_addr = dram_addr[11:2];

    mem_write_stage u_dut (
        .clk             (clk),
        .resetn          (resetn),
        .id_ex_valid     (id_ex_valid),
        .id_ex_mem_wen   (id_ex_mem_wen),
        .id_ex_mem_ren   (id_ex_mem_ren),
        .id_ex_rd_data1  (id_ex_rd_data1),
        .id_ex_rd_data2  (id_ex_rd_data2),
        .id_ex_imm       (id_ex_imm),
        .ex_addr         (ex_addr),
        .ex_mem_wen      (ex_mem_wen),
        .ex_mem_ren      (ex_mem_ren),
        .dram_addr       (dram_addr),
        .dram_wr_en      (dram_wr_en),
        .dram_wr_data    (dram_wr_data),
        .dram_wr_byte_en (dram_wr_byte_en),
        .dram_rd_data    (dram_rd_data),
        .mem_rd_data     (mem_rd_data),
        .mem_rd_valid    (mem_rd_valid)
    );

    data_ram u_data_ram (
        .wr_data    (dram_wr_data),
        .addr       (ram_addr),
        .wr_en      (dram_wr_en),
        .wr_byte_en (dram_wr_byte_en),
        .clk        (clk),
        .rst        (~resetn),
        .rd_data    (dram_rd_data)
    );

    GTP_GRS GRS_INST (.GRS_N(1'b1));

    initial begin
        clk = 1'b1;
        forever #5 clk = ~clk;
    end

    //------------------------------------------------------------------------
    // Per-cycle trace.  Samples #1 after each rising edge, so every row shows
    // the state the RAM just latched on that edge.
    //------------------------------------------------------------------------
    initial begin
        $display("");
        $display("   t(ns) | phase | valid wen ren |  addr    | RAM.wr_en wr_data | RAM rd_data");
        $display("   ------+-------+--------------+----------+-------------------+------------");
        forever begin
            @(posedge clk);
            #1;
            if ($time >= 95 && $time <= 250)
                $display("   %5d |       |   %b     %b   %b  | %h |     %b     %h | %h",
                         $time, id_ex_valid, id_ex_mem_wen, id_ex_mem_ren,
                         ex_addr, dram_wr_en, dram_wr_data, dram_rd_data);
        end
    end

    //------------------------------------------------------------------------
    // Stimulus
    //------------------------------------------------------------------------
    initial begin
        resetn          = 1'b0;
        id_ex_valid     = 1'b0;
        id_ex_mem_wen   = 1'b0;
        id_ex_mem_ren   = 1'b0;
        id_ex_rd_data1  = 32'h0;
        id_ex_rd_data2  = 32'h0;
        id_ex_imm       = 32'h0;

        #95;
        resetn = 1'b1;
        #10;   // wait one more cycle: IP internal rsta_int drops one cycle later

        //====================================================================
        // Cycle 1: SW enters EX.  x[rs1]=0x04, imm=0 -> addr=0x04 -> ram[1]
        //          store data = DEADBEEF
        //   The four RAM inputs are driven combinationally here, and are
        //   sampled by the RAM on the NEXT rising edge.
        //====================================================================
        @(negedge clk);
        id_ex_valid    = 1'b1;
        id_ex_mem_wen  = 1'b1;
        id_ex_mem_ren  = 1'b0;
        id_ex_rd_data1 = 32'h0000_0004;
        id_ex_rd_data2 = 32'hDEAD_BEEF;
        id_ex_imm      = 32'h0000_0000;
        $display("");
        $display("   [%0t ns] EX issues WRITE request : addr=%h  data=%h  wr_en=%b",
                 $time, ex_addr, dram_wr_data, dram_wr_en);

        //====================================================================
        // Next rising edge: RAM latches addr/wr_en/wr_data -> value written
        //====================================================================
        @(posedge clk);
        #1;
        $display("   [%0t ns] ==> RAM writes on this edge : ram[1] = %h", $time, dram_wr_data);

        //====================================================================
        // Cycle 2: instruction leaves EX, request withdrawn
        //====================================================================
        @(negedge clk);
        id_ex_valid    = 1'b0;
        id_ex_mem_wen  = 1'b0;
        id_ex_rd_data2 = 32'h0;
        id_ex_rd_data1 = 32'h0;

        //====================================================================
        // Cycle 3: LW reads back the same address
        //====================================================================
        @(negedge clk);
        id_ex_valid    = 1'b1;
        id_ex_mem_wen  = 1'b0;
        id_ex_mem_ren  = 1'b1;
        id_ex_rd_data1 = 32'h0000_0004;
        id_ex_imm      = 32'h0000_0000;
        $display("   [%0t ns] EX issues READ  request : addr=%h  rd_en=%b", $time, ex_addr, ex_mem_ren);

        @(posedge clk); #1;
        @(posedge clk); #1;

        $display("");
        $display("   ================= RESULT =================");
        $display("     RAM read-back    = %h", dram_rd_data);
        $display("     MEM stage value  = %h", mem_rd_data);
        if (dram_rd_data === 32'hDEAD_BEEF)
            $display("     PASS: written value read back correctly");
        else
            $display("     FAIL: expected DEADBEEF, got %h", dram_rd_data);
        $display("   ==========================================");
        $display("");

        #50;
        $finish;
    end

endmodule
