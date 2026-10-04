`timescale 1ns/1ps

// 用第 9 步 ROM 覆盖正常退休、跳转、气泡、同步 trap、MRET 与 EX 访存事件。
module tb_retire_step10;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));

    reg [31:0] expected_arch_pc = 0;
    integer trap_count = 0;
    integer mret_count = 0;
    integer retire_count = 0;
    integer bubble_count = 0;
    integer load_count = 0;
    integer store_count = 0;
    integer branch_count = 0;
    integer jalr_count = 0;

    function [31:0] successor;
        input [31:0] instruction_pc;
        begin
            case (instruction_pc)
                32'h50: successor = 32'h58; // JALR 清 bit 0 后的目标
                32'h60: successor = 32'h68; // 采用的 BEQ
                32'h6c: successor = 32'h6c; // 自循环 JAL
                default: successor = instruction_pc + 32'd4;
            endcase
        end
    endfunction

    initial begin
        #30000;
        $fatal(1, "retire step10 timeout");
    end

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (trap_count == 6 && dut.u_regfile.rf[13] == 32'd1);
        repeat (12) @(posedge clk);
        #2;
        if (trap_count != 6 || mret_count != 6 || retire_count < 100 ||
            bubble_count < 1 || load_count < 1 || store_count < 1 ||
            branch_count != 1 || jalr_count != 1)
            $fatal(1, "event counts trap=%0d mret=%0d retire=%0d bubble=%0d load=%0d store=%0d branch=%0d jalr=%0d",
                   trap_count, mret_count, retire_count, bubble_count,
                   load_count, store_count, branch_count, jalr_count);
        $display("RESULT: PASS architectural next PC and separate retirement/memory events");
        $finish;
    end

    always @(posedge clk) begin
        if (!resetn) begin
            expected_arch_pc = 0;
        end else begin
            if ((dut.normal_retire + dut.sync_trap_event + dut.mret_commit) > 1)
                $fatal(1, "retire/trap/mret event overlap");
            if (dut.mem_store_request !== dut.ex_store_commit ||
                dut.mem_store_request !== (|dut.data_sram_we))
                $fatal(1, "store event differs from actual RAM write enable");
            if (dut.mem_load_request &&
                (!dut.id_ex_valid || !dut.id_ex_i_l || dut.ex_exc_valid ||
                 dut.older_fault_for_ex))
                $fatal(1, "load event on invalid or faulty instruction");
            if (dut.id_ex_valid && dut.id_ex_pc == 32'h58 &&
                (dut.mem_load_request || dut.mem_store_request))
                $fatal(1, "faulting load generated a memory event");

            if (dut.mem_load_request) load_count = load_count + 1;
            if (dut.mem_store_request) store_count = store_count + 1;
            if (dut.normal_retire) begin
                retire_count = retire_count + 1;
                if (dut.mem_wb_next_pc !== successor(dut.mem_wb_pc))
                    $fatal(1, "successor mismatch pc=%h got=%h want=%h",
                           dut.mem_wb_pc, dut.mem_wb_next_pc,
                           successor(dut.mem_wb_pc));
                if (dut.mem_wb_pc == 32'h60) branch_count = branch_count + 1;
                if (dut.mem_wb_pc == 32'h50) jalr_count = jalr_count + 1;
                expected_arch_pc = successor(dut.mem_wb_pc);
            end else if (dut.sync_trap_event) begin
                trap_count = trap_count + 1;
                if (dut.normal_retire || dut.mem_wb_mret)
                    $fatal(1, "fault counted as normal retirement");
                expected_arch_pc = 32'h180;
            end else if (dut.mret_commit) begin
                mret_count = mret_count + 1;
                expected_arch_pc = dut.csr_mret_target;
            end else begin
                bubble_count = bubble_count + 1;
            end
        end
        #1;
        if (dut.arch_next_pc !== expected_arch_pc)
            $fatal(1, "arch_next_pc=%h expected=%h", dut.arch_next_pc, expected_arch_pc);
    end
endmodule
