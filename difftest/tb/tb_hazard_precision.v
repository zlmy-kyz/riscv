`timescale 1ns/1ps

module tb_hazard_precision;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;

    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));

    integer false_lui = 0;
    integer false_addi = 0;
    integer true_addi = 0;
    integer cycles = 0;

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
    end

    always @(posedge clk) if (resetn) begin
        cycles = cycles + 1;
        if (dut.id_ex_valid && dut.id_ex_i_l && dut.if_id_valid) begin
            case (dut.if_id_pc)
                32'h0000000c: begin
                    false_lui = false_lui + 1;
                    if (dut.load_use) $fatal(1, "LUI false dependency stalled");
                end
                32'h00000014: begin
                    false_addi = false_addi + 1;
                    if (dut.load_use) $fatal(1, "ADDI immediate false dependency stalled");
                end
                32'h0000001c: begin
                    true_addi = true_addi + 1;
                    if (!dut.load_use) $fatal(1, "Real load-use dependency did not stall");
                end
            endcase
        end
        if (cycles == 50) begin
            if (false_lui != 1 || false_addi != 1 || true_addi != 1)
                $fatal(1, "Missing hazard cases: LUI=%0d ADDI=%0d real=%0d",
                       false_lui, false_addi, true_addi);
            if (dut.u_regfile.rf[5] !== 32'h55 ||
                dut.u_regfile.rf[6] !== 32'h28000 ||
                dut.u_regfile.rf[7] !== 32'h5 ||
                dut.u_regfile.rf[8] !== 32'h56)
                $fatal(1, "Final register values are incorrect");
            $display("RESULT: PASS hazard precision: two false stalls removed; real stall retained");
            $finish;
        end
    end
endmodule
