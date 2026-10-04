`timescale 1ns/1ps

// 第 5 步仅测试异常运输和副作用门控。真实异常检测、CSR trap 更新在后续步骤接入。
module tb_exception_path;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));

    integer old_store_count = 0;
    integer young_store_count = 0;
    integer handler_store_count = 0;
    integer trap_count = 0;

    initial begin
        #5000;
        $fatal(1, "exception-path timeout");
    end

    initial begin
        #1;
        // 老 addi/store 可以完成；PC=8 的 addi 注入故障；其后 store 不得执行。
        dut.u_inst_rom.mem[0]  = 32'h0050_0093; // addi x1,x0,5
        dut.u_inst_rom.mem[1]  = 32'h0010_2023; // sw x1,0(x0)
        dut.u_inst_rom.mem[2]  = 32'h0060_0113; // addi x2,x0,6，注入故障
        dut.u_inst_rom.mem[3]  = 32'h0010_2223; // 年轻 sw x1,4(x0)
        dut.u_inst_rom.mem[4]  = 32'h0070_0193; // 年轻 addi x3,x0,7
        dut.u_inst_rom.mem[5]  = 32'h0000_006f;
        dut.u_inst_rom.mem[64] = 32'h0090_0213; // 0x100: addi x4,x0,9
        dut.u_inst_rom.mem[65] = 32'h0040_2423; // sw x4,8(x0)
        dut.u_inst_rom.mem[66] = 32'h0000_006f;

        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (dut.if_id_valid && dut.if_id_pc == 32'd8);
        @(negedge clk);
        force dut.id_exc_valid = 1'b1;
        force dut.id_exc_cause = 5'd11;
        force dut.id_exc_tval = 32'hdead_beef;
        @(posedge clk); #1;
        if (!dut.id_ex_valid || !dut.id_ex_exc_valid || dut.id_ex_pc !== 32'd8 ||
            dut.id_ex_inst !== 32'h0060_0113 ||
            dut.id_ex_exc_cause !== 5'd11 || dut.id_ex_exc_tval !== 32'hdead_beef)
            $fatal(1, "ID/EX fault payload or PC/inst mismatch");
        release dut.id_exc_valid;
        release dut.id_exc_cause;
        release dut.id_exc_tval;
        wait (dut.mem_wb_valid && dut.mem_wb_exc_valid);
        #1;
        if (dut.mem_wb_pc !== 32'd8 || dut.mem_wb_inst !== 32'h0060_0113 ||
            dut.mem_wb_exc_cause !== 5'd11 || dut.mem_wb_exc_tval !== 32'hdead_beef ||
            !dut.sync_trap_event || dut.normal_retire || dut.rf_we || dut.id_fire)
            $fatal(1, "WB fault event/payload/side effect mismatch");
        @(posedge clk); #1;
        if (dut.pc !== 32'h100 || dut.if_id_valid || dut.mem_wb_exc_valid)
            $fatal(1, "fault redirect did not kill younger state");
        repeat (18) @(posedge clk);
        #1;
        if (old_store_count != 1 || young_store_count != 0 ||
            handler_store_count != 1 || trap_count != 1 ||
            dut.u_regfile.rf[1] !== 32'd5 ||
            dut.u_regfile.rf[2] !== 32'd0 || dut.u_regfile.rf[3] !== 32'd0 ||
            dut.the_instance_name.mem[0] !== 32'd5 ||
            dut.the_instance_name.mem[1] !== 32'd0 ||
            dut.the_instance_name.mem[2] !== 32'd9)
            $fatal(1, "fault sequence state/count mismatch old=%0d young=%0d handler=%0d trap=%0d",
                   old_store_count, young_store_count, handler_store_count, trap_count);

        // 第二轮：故障项本身是 store，必须在 EX 当拍抑制 RAM 写。
        @(negedge clk) resetn = 0;
        dut.u_inst_rom.mem[0]  = 32'h00b0_0093; // addi x1,x0,11
        dut.u_inst_rom.mem[1]  = 32'h0010_2023; // 老 sw x1,0(x0)
        dut.u_inst_rom.mem[2]  = 32'h0010_2223; // 故障 sw x1,4(x0)
        dut.u_inst_rom.mem[3]  = 32'h0010_2423; // 年轻 sw x1,8(x0)
        dut.u_inst_rom.mem[4]  = 32'h0000_006f;
        dut.u_inst_rom.mem[64] = 32'h0000_006f;
        repeat (4) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (dut.if_id_valid && dut.if_id_pc == 32'd8);
        @(negedge clk);
        force dut.id_exc_valid = 1'b1;
        force dut.id_exc_cause = 5'd6;
        force dut.id_exc_tval = 32'd4;
        @(posedge clk); #1;
        release dut.id_exc_valid;
        release dut.id_exc_cause;
        release dut.id_exc_tval;
        if (!dut.id_ex_valid || !dut.id_ex_exc_valid || dut.ex_store_commit)
            $fatal(1, "faulty store was not suppressed in EX");
        wait (dut.sync_trap_event);
        @(posedge clk); #1;
        if (dut.the_instance_name.mem[0] !== 32'd11 ||
            dut.the_instance_name.mem[1] !== 32'd0 ||
            dut.the_instance_name.mem[2] !== 32'd9)
            $fatal(1, "faulty or younger store changed memory");

        // 第三轮：模拟老指令在 MEM 才被判故障，同时年轻 store 已处于 EX。
        @(negedge clk) resetn = 0;
        dut.u_inst_rom.mem[0]  = 32'h00d0_0093; // addi x1,x0,13
        dut.u_inst_rom.mem[1]  = 32'h0010_0113; // 老 addi x2,x0,1，MEM 故障
        dut.u_inst_rom.mem[2]  = 32'h0010_2623; // 年轻 sw x1,12(x0)
        dut.u_inst_rom.mem[3]  = 32'h0000_006f;
        dut.u_inst_rom.mem[64] = 32'h0000_006f;
        repeat (4) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (dut.id_ex_valid && dut.id_ex_pc == 32'd8 &&
              dut.ex_mem_valid && dut.ex_mem_pc == 32'd4);
        @(negedge clk);
        force dut.ex_mem_exc_valid = 1'b1;
        force dut.ex_mem_exc_cause = 5'd2;
        force dut.ex_mem_exc_tval = 32'hbad0_0001;
        #1;
        if (dut.ex_store_commit || dut.data_sram_we !== 4'b0000)
            $fatal(1, "younger EX store passed older MEM fault");
        @(posedge clk); #1;
        if (!dut.mem_wb_exc_valid || dut.mem_wb_pc !== 32'd4 ||
            dut.mem_wb_exc_cause !== 5'd2 || dut.mem_wb_exc_tval !== 32'hbad0_0001)
            $fatal(1, "MEM fault record did not reach WB");
        release dut.ex_mem_exc_valid;
        release dut.ex_mem_exc_cause;
        release dut.ex_mem_exc_tval;
        @(posedge clk); #1;
        if (dut.the_instance_name.mem[3] !== 32'd0 || dut.u_regfile.rf[2] !== 32'd0)
            $fatal(1, "younger store or faulty GPR write committed");

        $display("RESULT: PASS exception payload, precise stores, WB event and redirect");
        $finish;
    end

    always @(posedge clk) if (resetn) begin
        if (dut.the_instance_name.wr_en) begin
            case (dut.data_sram_addr)
                32'd0: old_store_count = old_store_count + 1;
                32'd4: young_store_count = young_store_count + 1;
                32'd8: handler_store_count = handler_store_count + 1;
                default: ;
            endcase
        end
        if (dut.sync_trap_event) trap_count = trap_count + 1;
    end
endmodule
