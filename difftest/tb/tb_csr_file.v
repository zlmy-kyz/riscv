`timescale 1ns/1ps
`include "csr_defs.vh"

module tb_csr_file;
    reg clk = 0;
    always #5 clk = ~clk;

    reg resetn = 0;
    reg [11:0] csr_addr = 0;
    reg csr_read_en = 0;
    reg csr_write_intent = 0;
    reg [31:0] csr_wdata = 0;
    reg csr_commit = 0;
    wire [31:0] csr_rdata;
    wire csr_exists, csr_readonly_addr, csr_access_illegal;
    reg trap_enter = 0;
    reg [31:0] trap_pc = 0;
    reg trap_is_interrupt = 0;
    reg [4:0] trap_cause = 0;
    reg [31:0] trap_tval = 0;
    reg mret_commit = 0;
    reg irq_external = 0, irq_software = 0, irq_timer = 0;
    wire [31:0] trap_target, mret_target, irq_pending, irq_enable;
    wire irq_global_enable;

    csr_file dut (
        .clk(clk), .resetn(resetn), .csr_addr(csr_addr),
        .csr_read_en(csr_read_en), .csr_write_intent(csr_write_intent),
        .csr_wdata(csr_wdata), .csr_commit(csr_commit),
        .csr_rdata(csr_rdata), .csr_exists(csr_exists),
        .csr_readonly_addr(csr_readonly_addr),
        .csr_access_illegal(csr_access_illegal),
        .trap_enter(trap_enter), .trap_pc(trap_pc),
        .trap_is_interrupt(trap_is_interrupt), .trap_cause(trap_cause),
        .trap_tval(trap_tval), .mret_commit(mret_commit),
        .irq_external(irq_external), .irq_software(irq_software),
        .irq_timer(irq_timer), .trap_target(trap_target),
        .mret_target(mret_target), .irq_pending(irq_pending),
        .irq_enable(irq_enable), .irq_global_enable(irq_global_enable)
    );

    task check32;
        input [31:0] actual, expected;
        input [255:0] label;
        begin
            if (actual !== expected) begin
                $display("FAIL %0s: got %08x expected %08x", label, actual, expected);
                $fatal(1);
            end
        end
    endtask

    task read_check;
        input [11:0] addr;
        input [31:0] expected;
        input [255:0] label;
        begin
            csr_addr = addr;
            csr_read_en = 1;
            csr_write_intent = 0;
            #1;
            check32(csr_rdata, expected, label);
            check32({31'b0, csr_exists}, 32'd1, "address exists");
            check32({31'b0, csr_access_illegal}, 32'd0, "read is legal");
        end
    endtask

    task write_csr;
        input [11:0] addr;
        input [31:0] value;
        begin
            @(negedge clk);
            csr_addr = addr;
            csr_read_en = 0;
            csr_write_intent = 1;
            csr_wdata = value;
            csr_commit = 1;
            #1;
            check32({31'b0, csr_access_illegal}, 32'd0, "write is legal");
            @(posedge clk);
            #1;
            csr_commit = 0;
            csr_write_intent = 0;
        end
    endtask

    initial begin
        @(posedge clk);
        #1;
        resetn = 1;
        read_check(`RV_CSR_MSTATUS, 32'h0000_1800, "mstatus reset");
        read_check(`RV_CSR_MISA, `RV_MISA_RV32I, "misa reset");
        read_check(`RV_CSR_MIE, 0, "mie reset");
        read_check(`RV_CSR_MTVEC, 32'h0000_0100, "mtvec reset");
        read_check(`RV_CSR_MSTATUSH, 0, "mstatush reset");
        read_check(`RV_CSR_MSCRATCH, 0, "mscratch reset");
        read_check(`RV_CSR_MEPC, 0, "mepc reset");
        read_check(`RV_CSR_MCAUSE, 0, "mcause reset");
        read_check(`RV_CSR_MTVAL, 0, "mtval reset");
        read_check(`RV_CSR_MIP, 0, "mip reset");
        read_check(`RV_CSR_MVENDORID, 0, "mvendorid reset");
        read_check(`RV_CSR_MARCHID, 0, "marchid reset");
        read_check(`RV_CSR_MIMPID, 0, "mimpid reset");
        read_check(`RV_CSR_MHARTID, 0, "mhartid reset");
        read_check(`RV_CSR_MCONFIGPTR, 0, "mconfigptr reads zero");

        write_csr(`RV_CSR_MSTATUS, 32'hffff_ffff);
        read_check(`RV_CSR_MSTATUS, 32'h0000_1888, "mstatus mask and fixed MPP");
        check32({31'b0, irq_global_enable}, 1, "MIE view");
        write_csr(`RV_CSR_MIE, 32'hffff_ffff);
        read_check(`RV_CSR_MIE, 32'h0000_0888, "mie mask");
        check32(irq_enable, 32'h0000_0888, "mie view");
        write_csr(`RV_CSR_MTVEC, 32'h0000_0203);
        read_check(`RV_CSR_MTVEC, 32'h0000_0200, "mtvec direct alignment");
        check32(trap_target, 32'h0000_0200, "trap target");
        write_csr(`RV_CSR_MSCRATCH, 32'hdead_beef);
        read_check(`RV_CSR_MSCRATCH, 32'hdead_beef, "mscratch RW");
        write_csr(`RV_CSR_MEPC, 32'h0000_0123);
        read_check(`RV_CSR_MEPC, 32'h0000_0120, "mepc alignment");
        check32(mret_target, 32'h0000_0120, "MRET target");
        write_csr(`RV_CSR_MCAUSE, 32'hffff_ffff);
        read_check(`RV_CSR_MCAUSE, 32'h8000_001f, "mcause supported bits");
        write_csr(`RV_CSR_MTVAL, 32'h1234_5678);
        read_check(`RV_CSR_MTVAL, 32'h1234_5678, "mtval RW");

        write_csr(`RV_CSR_MISA, 0);
        read_check(`RV_CSR_MISA, `RV_MISA_RV32I, "misa legal ignored write");
        write_csr(`RV_CSR_MSTATUSH, 32'hffff_ffff);
        read_check(`RV_CSR_MSTATUSH, 0, "mstatush legal ignored write");
        irq_external = 1; irq_timer = 1; irq_software = 1;
        #1;
        read_check(`RV_CSR_MIP, 32'h0000_0888, "mip reflects all IRQ inputs");
        write_csr(`RV_CSR_MIP, 0);
        read_check(`RV_CSR_MIP, 32'h0000_0888, "mip ignored write");
        irq_external = 0; irq_timer = 0; irq_software = 0;
        #1;
        read_check(`RV_CSR_MIP, 0, "mip follows cleared input");

        csr_addr = `RV_CSR_MCONFIGPTR;
        csr_read_en = 1; csr_write_intent = 1; csr_commit = 1;
        #1;
        check32({31'b0, csr_exists}, 1, "mconfigptr exists");
        check32({31'b0, csr_readonly_addr}, 1, "mconfigptr read-only address");
        check32({31'b0, csr_access_illegal}, 1, "mconfigptr write illegal");
        @(posedge clk); #1;
        csr_commit = 0; csr_write_intent = 0;
        read_check(`RV_CSR_MCONFIGPTR, 0, "mconfigptr still zero after rejected write");

        csr_addr = `RV_CSR_MHARTID;
        csr_read_en = 1; csr_write_intent = 1; csr_commit = 1;
        #1;
        check32({31'b0, csr_readonly_addr}, 1, "ID read-only address");
        check32({31'b0, csr_access_illegal}, 1, "ID write illegal");
        csr_addr = 12'h306;
        #1;
        check32({31'b0, csr_exists}, 0, "unimplemented address absent");
        check32({31'b0, csr_access_illegal}, 1, "unimplemented access illegal");
        csr_commit = 0; csr_write_intent = 0;

        write_csr(`RV_CSR_MSTATUS, 32'h0000_1808);
        @(negedge clk);
        trap_enter = 1;
        trap_pc = 32'h0000_0083;
        trap_is_interrupt = 1;
        trap_cause = `RV_IRQ_CAUSE_EXTERNAL;
        trap_tval = 32'habcd_1234;
        @(posedge clk); #1;
        trap_enter = 0;
        read_check(`RV_CSR_MSTATUS, 32'h0000_1880, "trap saves MIE into MPIE");
        check32({31'b0, irq_global_enable}, 0, "trap clears MIE");
        read_check(`RV_CSR_MEPC, 32'h0000_0080, "trap mepc alignment");
        read_check(`RV_CSR_MCAUSE, 32'h8000_000b, "trap interrupt cause");
        read_check(`RV_CSR_MTVAL, 32'habcd_1234, "trap tval");
        @(negedge clk); mret_commit = 1;
        @(posedge clk); #1; mret_commit = 0;
        read_check(`RV_CSR_MSTATUS, 32'h0000_1888, "MRET restores MIE and sets MPIE");

        write_csr(`RV_CSR_MSTATUS, 32'h0000_1800);
        @(negedge clk);
        trap_enter = 1; trap_is_interrupt = 0;
        trap_cause = `RV_EXC_ECALL_M; trap_pc = 32'h0000_0040; trap_tval = 0;
        @(posedge clk); #1; trap_enter = 0;
        read_check(`RV_CSR_MSTATUS, 32'h0000_1800, "trap saves disabled MIE");
        read_check(`RV_CSR_MCAUSE, 32'h0000_000b, "trap synchronous cause");
        @(negedge clk); mret_commit = 1;
        @(posedge clk); #1; mret_commit = 0;
        read_check(`RV_CSR_MSTATUS, 32'h0000_1880, "MRET with saved MIE zero");

        $display("RESULT: PASS csr_file reset, WARL, legality, IRQ view, trap and MRET");
        $finish;
    end
endmodule
