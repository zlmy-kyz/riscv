`timescale 1ns/1ps

module tb_pipeline_control;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;

    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));

    integer serial_fire_count = 0;
    integer serial_wb_count = 0;
    integer serial_hold_cycles = 0;
    integer next_fire_count = 0;
    integer branch_count = 0;
    integer store0_count = 0;
    integer store1_count = 0;
    integer wrong_store_count = 0;
    integer cycles = 0;

    initial begin
        // 覆盖行为 ROM 的测试程序：旧 store -> 串行 CSR 占位项 -> 年轻 ALU/分支/store。
        // 第 3 步只检验串行控制，CSR 的实际读改写在第 4 步接入。
        #1;
        dut.u_inst_rom.mem[0]  = 32'h0000_0093; // addi x1,x0,0
        dut.u_inst_rom.mem[1]  = 32'h0070_0113; // addi x2,x0,7
        dut.u_inst_rom.mem[2]  = 32'h0020_a023; // sw x2,0(x1)
        dut.u_inst_rom.mem[3]  = 32'h3400_21f3; // csrrs x3,mscratch,x0
        dut.u_inst_rom.mem[4]  = 32'h0010_0213; // addi x4,x0,1
        dut.u_inst_rom.mem[5]  = 32'h0080_006f; // jal x0,+8
        dut.u_inst_rom.mem[6]  = 32'h0020_a423; // 错误路径: sw x2,8(x1)
        dut.u_inst_rom.mem[7]  = 32'h0040_a223; // sw x4,4(x1)
        dut.u_inst_rom.mem[8]  = 32'h0000_006f; // 停机自循环
        dut.u_inst_rom.mem[16] = 32'h0630_0313; // 0x40: addi x6,x0,99
        dut.u_inst_rom.mem[17] = 32'h0060_a623; // sw x6,12(x1)
        dut.u_inst_rom.mem[18] = 32'h0000_006f; // 停机自循环
        dut.u_inst_rom.mem[20] = 32'h02a0_0393; // 0x50: addi x7,x0,42
        dut.u_inst_rom.mem[21] = 32'h0070_a823; // sw x7,16(x1)
        dut.u_inst_rom.mem[22] = 32'h0000_006f;
        dut.u_inst_rom.mem[24] = 32'h0000_a403; // 0x60: lw x8,0(x1)
        dut.u_inst_rom.mem[25] = 32'h0014_0493; // addi x9,x8,1，触发 load-use
        dut.u_inst_rom.mem[26] = 32'h0020_aa23; // 被取消: sw x2,20(x1)
        dut.u_inst_rom.mem[27] = 32'h0000_006f;
        dut.u_inst_rom.mem[28] = 32'h0370_0513; // 0x70: addi x10,x0,55
        dut.u_inst_rom.mem[29] = 32'h00a0_ac23; // sw x10,24(x1)
        dut.u_inst_rom.mem[30] = 32'h0000_006f;

        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        repeat (70) @(posedge clk);
        #1;
        if (serial_fire_count != 1 || serial_wb_count != 1 ||
            serial_hold_cycles < 3 || next_fire_count != 1 || branch_count != 1)
            $fatal(1, "serial counts fire=%0d wb=%0d hold=%0d next=%0d branch=%0d",
                   serial_fire_count, serial_wb_count, serial_hold_cycles,
                   next_fire_count, branch_count);
        if (store0_count != 1 || store1_count != 1 || wrong_store_count != 0)
            $fatal(1, "store counts old=%0d young=%0d wrong=%0d",
                   store0_count, store1_count, wrong_store_count);
        if (dut.the_instance_name.mem[0] !== 32'd7 ||
            dut.the_instance_name.mem[1] !== 32'd1 ||
            dut.the_instance_name.mem[2] !== 32'd0 ||
            dut.u_regfile.rf[4] !== 32'd1)
            $fatal(1, "serial/barrier final state incorrect");

        // 模拟未来 WB trap 重定向：必须覆盖当前保持/预取状态，丢弃旧返回。
        @(negedge clk);
        force dut.trap_redirect_req = 1'b1;
        force dut.trap_redirect_target = 32'h0000_0040;
        @(posedge clk); #1;
        if (dut.pc !== 32'h40 || dut.inst_if !== 32'h0630_0313 || dut.if_id_valid !== 0)
            $fatal(1, "trap redirect did not align PC/ROM or kill old IF/ID");
        release dut.trap_redirect_req;
        release dut.trap_redirect_target;
        repeat (14) @(posedge clk);
        #1;
        if (dut.the_instance_name.mem[3] !== 32'd99 || dut.u_regfile.rf[6] !== 32'd99)
            $fatal(1, "first trap-target instruction was lost");

        // 模拟未来 MRET 重定向：经 IRQ_CHECK 保持一拍后仍须执行返回目标首条。
        @(negedge clk);
        force dut.mret_redirect_req = 1'b1;
        force dut.mret_redirect_target = 32'h0000_0050;
        @(posedge clk); #1;
        if (dut.pc !== 32'h50 || dut.inst_if !== 32'h02a0_0393 || dut.if_id_valid !== 0)
            $fatal(1, "MRET redirect did not align PC/ROM or kill old IF/ID");
        release dut.mret_redirect_req;
        release dut.mret_redirect_target;
        repeat (16) @(posedge clk);
        #1;
        if (dut.the_instance_name.mem[4] !== 32'd42 || dut.u_regfile.rf[7] !== 32'd42)
            $fatal(1, "first MRET-target instruction was lost");

        // 把流水带到真实 load-use 停顿，再在同一拍要求 trap 重定向。
        @(negedge clk);
        force dut.trap_redirect_req = 1'b1;
        force dut.trap_redirect_target = 32'h0000_0060;
        @(posedge clk); #1;
        release dut.trap_redirect_req;
        release dut.trap_redirect_target;
        wait (dut.load_use === 1'b1);
        @(negedge clk);
        if (dut.load_use !== 1'b1) $fatal(1, "expected load-use hold disappeared");
        force dut.trap_redirect_req = 1'b1;
        force dut.trap_redirect_target = 32'h0000_0070;
        @(posedge clk); #1;
        if (dut.pc !== 32'h70 || dut.inst_if !== 32'h0370_0513 || dut.if_id_valid !== 0)
            $fatal(1, "trap redirect lost to simultaneous load-use hold");
        release dut.trap_redirect_req;
        release dut.trap_redirect_target;
        repeat (14) @(posedge clk);
        #1;
        if (dut.the_instance_name.mem[5] !== 32'd0 ||
            dut.the_instance_name.mem[6] !== 32'd55 ||
            dut.u_regfile.rf[9] !== 32'd0 || dut.u_regfile.rf[10] !== 32'd55)
            $fatal(1, "load-use redirect failed to kill old path or lost target");

        $display("RESULT: PASS pipeline serial drain, one-shot issue, redirect refill and stores");
        $finish;
    end

    always @(posedge clk) begin
        if (!resetn) begin
            if (dut.the_instance_name.wr_en !== 1'b0 || dut.rf_we !== 1'b0)
                $fatal(1, "reset allowed RAM or GPR write");
        end else begin
            cycles = cycles + 1;
            if (cycles > 180) $fatal(1, "pipeline control timeout");
            if (dut.flow_state == 2'd1 && dut.frontend_hold)
                serial_hold_cycles = serial_hold_cycles + 1;
            if (dut.id_fire && dut.if_id_pc == 32'hc) begin
                serial_fire_count = serial_fire_count + 1;
                if (dut.id_ex_valid || dut.ex_mem_valid || dut.mem_wb_valid)
                    $fatal(1, "serial instruction issued before older pipeline drained");
            end
            if (dut.mem_wb_valid && dut.mem_wb_pc == 32'hc)
                serial_wb_count = serial_wb_count + 1;
            if (dut.id_fire && dut.if_id_pc == 32'h10)
                next_fire_count = next_fire_count + 1;
            if (dut.branch_redirect && dut.if_id_pc == 32'h14)
                branch_count = branch_count + 1;
            if (dut.id_fire && dut.if_id_pc == 32'h18)
                $fatal(1, "wrong-path store issued");
            if (dut.the_instance_name.wr_en) begin
                case (dut.data_sram_addr)
                    32'h0: store0_count = store0_count + 1;
                    32'h4: store1_count = store1_count + 1;
                    32'h8: wrong_store_count = wrong_store_count + 1;
                endcase
            end
        end
    end
endmodule
