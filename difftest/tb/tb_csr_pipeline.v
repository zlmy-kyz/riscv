`timescale 1ns/1ps

// CSR 指令流水集成测试；期望值直接按指令语义列出，不使用 DUT 的计算结果推导。
module tb_csr_pipeline;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));

    function [31:0] csr_inst;
        input [11:0] addr;
        input [4:0] rs1_or_zimm;
        input [2:0] funct3;
        input [4:0] rd;
        begin
            csr_inst = {addr, rs1_or_zimm, funct3, rd, 7'h73};
        end
    endfunction

    integer cycles = 0;
    integer csr_fire_count = 0;
    integer csr_wb_count = 0;
    integer illegal_count = 0;
    integer csr_write_count = 0;
    integer store_count = 0;

    initial begin
        #1;
        dut.u_inst_rom.mem[0]  = 32'h0550_0093; // addi x1,x0,0x55
        dut.u_inst_rom.mem[1]  = csr_inst(12'h340, 5'd1, 3'b001, 5'd2);  // CSRRW
        dut.u_inst_rom.mem[2]  = csr_inst(12'h340, 5'd0, 3'b010, 5'd3);  // CSRRS 只读
        dut.u_inst_rom.mem[3]  = csr_inst(12'h340, 5'd1, 3'b011, 5'd4);  // CSRRC
        dut.u_inst_rom.mem[4]  = csr_inst(12'h340, 5'd7, 3'b101, 5'd5);  // CSRRWI
        dut.u_inst_rom.mem[5]  = csr_inst(12'h340, 5'd8, 3'b110, 5'd6);  // CSRRSI
        dut.u_inst_rom.mem[6]  = csr_inst(12'h340, 5'd3, 3'b111, 5'd7);  // CSRRCI
        dut.u_inst_rom.mem[7]  = 32'h0003_9463; // bne x7,x0,+8
        dut.u_inst_rom.mem[8]  = 32'h0630_0413; // 错误路径：addi x8,x0,99
        dut.u_inst_rom.mem[9]  = 32'h0013_8413; // addi x8,x7,1
        dut.u_inst_rom.mem[10] = 32'h0080_2023; // sw x8,0(x0)
        dut.u_inst_rom.mem[11] = csr_inst(12'h340, 5'd1, 3'b001, 5'd0);  // CSRRW rd=x0
        dut.u_inst_rom.mem[12] = csr_inst(12'hf15, 5'd0, 3'b010, 5'd10); // 合法只读
        dut.u_inst_rom.mem[13] = csr_inst(12'hf15, 5'd0, 3'b010, 5'd11); // 连续合法只读
        dut.u_inst_rom.mem[14] = csr_inst(12'h300, 5'd0, 3'b010, 5'd12); // 读 mstatus
        dut.u_inst_rom.mem[15] = csr_inst(12'h300, 5'd8, 3'b110, 5'd13); // mstatus.MIE 置位
        dut.u_inst_rom.mem[16] = csr_inst(12'h300, 5'd8, 3'b111, 5'd14); // mstatus.MIE 清位
        dut.u_inst_rom.mem[17] = csr_inst(12'h301, 5'd0, 3'b010, 5'd15); // 读 misa
        dut.u_inst_rom.mem[18] = csr_inst(12'h301, 5'd0, 3'b101, 5'd16); // 写 misa 忽略
        dut.u_inst_rom.mem[19] = csr_inst(12'h341, 5'd1, 3'b001, 5'd17); // 写 mepc=0x55 -> 0x54
        dut.u_inst_rom.mem[20] = csr_inst(12'h341, 5'd0, 3'b010, 5'd18); // 读 mepc
        dut.u_inst_rom.mem[21] = csr_inst(12'h344, 5'd0, 3'b010, 5'd19); // 读 mip
        dut.u_inst_rom.mem[22] = 32'h0000_006f; // 自循环

        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        repeat (260) @(posedge clk);
        #1;
        if (csr_fire_count != 17 || csr_wb_count != 17 ||
            illegal_count != 0 || csr_write_count != 10 || store_count != 1)
            $fatal(1, "counts issue=%0d wb=%0d illegal=%0d write=%0d store=%0d",
                   csr_fire_count, csr_wb_count, illegal_count,
                   csr_write_count, store_count);
        if (dut.u_regfile.rf[2]  !== 32'd0  ||
            dut.u_regfile.rf[3]  !== 32'h55 ||
            dut.u_regfile.rf[4]  !== 32'h55 ||
            dut.u_regfile.rf[5]  !== 32'd0  ||
            dut.u_regfile.rf[6]  !== 32'd7  ||
            dut.u_regfile.rf[7]  !== 32'd15 ||
            dut.u_regfile.rf[8]  !== 32'd16 ||
            dut.u_regfile.rf[10] !== 32'd0  ||
            dut.u_regfile.rf[11] !== 32'd0  ||
            dut.u_regfile.rf[12] !== 32'h1800 ||
            dut.u_regfile.rf[13] !== 32'h1800 ||
            dut.u_regfile.rf[14] !== 32'h1808 ||
            dut.u_regfile.rf[15] !== 32'h4000_0100 ||
            dut.u_regfile.rf[16] !== 32'h4000_0100 ||
            dut.u_regfile.rf[17] !== 32'd0  ||
            dut.u_regfile.rf[18] !== 32'h54 ||
            dut.u_regfile.rf[19] !== 32'd0)
            $fatal(1, "CSR/GPR results incorrect");
        if (dut.the_instance_name.mem[0] !== 32'd16 ||
            dut.u_csr_file.mscratch !== 32'h55 ||
            dut.u_csr_file.mstatus !== 32'h1800 ||
            dut.u_csr_file.mepc !== 32'h54)
            $fatal(1, "memory or final CSR state incorrect");
        $display("RESULT: PASS six CSR instructions, hazards, x0, legality and WB data");
        $finish;
    end

    always @(posedge clk) if (resetn) begin
        cycles = cycles + 1;
        if (cycles > 300) $fatal(1, "CSR integration timeout");
        if (dut.id_fire && dut.csr_inst) begin
            csr_fire_count = csr_fire_count + 1;
            if (dut.id_ex_valid || dut.ex_mem_valid || dut.mem_wb_valid)
                $fatal(1, "CSR issued before older pipeline drained");
            if ((dut.inst_csrrw || dut.inst_csrrs || dut.inst_csrrc) && !dut.uses_rs1)
                $fatal(1, "register CSR does not mark rs1 used");
            if ((dut.inst_csrrwi || dut.inst_csrrsi || dut.inst_csrrci) && dut.uses_rs1)
                $fatal(1, "immediate CSR incorrectly reads rs1");
            if (dut.uses_rs2) $fatal(1, "CSR incorrectly reads rs2");
        end
        if (dut.mem_wb_valid && dut.mem_wb_csr) begin
            csr_wb_count = csr_wb_count + 1;
            if (dut.wb_csr_illegal) begin
                illegal_count = illegal_count + 1;
                if (dut.rf_we || dut.csr_commit)
                    $fatal(1, "illegal CSR changed architectural state");
            end else if (dut.wb_csr_write_intent) begin
                csr_write_count = csr_write_count + 1;
            end
            if (dut.rf_we && dut.debug_wb_rf_wdata !== dut.rf_wdata)
                $fatal(1, "debug CSR result differs from GPR write port");
        end
        if (dut.the_instance_name.wr_en) store_count = store_count + 1;
        if (dut.id_fire && dut.if_id_pc == 32'h20)
            $fatal(1, "wrong branch path issued");
    end
endmodule
