`timescale 1ns/1ps

// 第 6 步：运行 trap_mret_step6.S 生成的 ROM，检查两次真实 trap 和 MRET。
module tb_trap_mret;
    reg clk = 0;
    reg resetn = 0;
    always #5 clk = ~clk;
    mycpu_sync dut (.clk(clk), .resetn(resetn),
                    .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0));

    integer trap_count = 0;
    integer mret_count = 0;
    integer handler_entry_count = 0;
    integer sentinel_write_count = 0;

    initial begin
        #10000;
        $fatal(1, "trap/MRET timeout trap=%0d mret=%0d handler=%0d",
               trap_count, mret_count, handler_entry_count);
    end

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (trap_count == 2 && mret_count == 2 &&
              dut.u_regfile.rf[9] == 32'd1 &&
              dut.u_regfile.rf[10] == 32'h1888);
        repeat (12) @(posedge clk);
        #1;
        if (trap_count != 2 || mret_count != 2 || handler_entry_count != 2 ||
            sentinel_write_count != 1)
            $fatal(1, "trap/MRET/handler counts wrong %0d/%0d/%0d/%0d",
                   trap_count, mret_count, handler_entry_count, sentinel_write_count);
        if (dut.the_instance_name.mem[128] !== 32'd11 ||
            dut.the_instance_name.mem[129] !== 32'd36 ||
            dut.the_instance_name.mem[130] !== 32'h1880 ||
            dut.the_instance_name.mem[131] !== 32'd3 ||
            dut.the_instance_name.mem[132] !== 32'd44 ||
            dut.the_instance_name.mem[133] !== 32'h1880)
            $fatal(1, "handler cause/mepc/mstatus log wrong");
        if (dut.the_instance_name.mem[188] !== 32'd85 ||
            dut.the_instance_name.mem[250] !== 32'd33 ||
            dut.the_instance_name.mem[251] !== 32'd44)
            $fatal(1, "sentinel or saved register memory wrong");
        if (dut.u_regfile.rf[2] !== 32'h3f0 ||
            dut.u_regfile.rf[5] !== 32'd33 ||
            dut.u_regfile.rf[6] !== 32'd44 ||
            dut.u_regfile.rf[20] !== 32'h218 ||
            dut.u_regfile.rf[9] !== 32'd1 ||
            dut.u_regfile.rf[10] !== 32'h1888)
            $fatal(1, "handler did not restore registers or MRET state");
        if (dut.u_csr_file.mstatus !== 32'h1888 ||
            dut.u_csr_file.mtvec !== 32'h180 ||
            dut.u_csr_file.mepc !== 32'd48 ||
            dut.u_csr_file.mcause !== 32'd3 ||
            dut.u_csr_file.mtval !== 32'd0)
            $fatal(1, "final trap CSR state wrong");
        $display("RESULT: PASS ECALL, EBREAK, trap CSR, handler, MRET and younger-store ordering");
        $finish;
    end

    always @(posedge clk) if (resetn) begin
        if (dut.sync_trap_event) begin
            trap_count = trap_count + 1;
            if (trap_count == 1) begin
                if (dut.mem_wb_pc !== 32'd36 || dut.mem_wb_inst !== 32'h0000_0073 ||
                    dut.mem_wb_exc_cause !== 5'd11 ||
                    dut.the_instance_name.mem[188] !== 32'd0 ||
                    dut.rf_we || dut.normal_retire)
                    $fatal(1, "ECALL trap event or younger-store ordering wrong");
            end else if (trap_count == 2) begin
                if (dut.mem_wb_pc !== 32'd44 || dut.mem_wb_inst !== 32'h0010_0073 ||
                    dut.mem_wb_exc_cause !== 5'd3)
                    $fatal(1, "EBREAK trap event wrong");
            end else $fatal(1, "unexpected third trap");
            #1;
            if (dut.pc !== 32'h180 || dut.u_csr_file.mepc !==
                (trap_count == 1 ? 32'd36 : 32'd44) ||
                dut.u_csr_file.mcause !== (trap_count == 1 ? 32'd11 : 32'd3) ||
                dut.u_csr_file.mtval !== 32'd0 ||
                dut.u_csr_file.mstatus !== 32'h1880)
                $fatal(1, "trap CSR update or redirect wrong");
        end
        if (dut.mret_commit) begin
            mret_count = mret_count + 1;
            if (dut.csr_mret_target !== (mret_count == 1 ? 32'd40 : 32'd48) ||
                dut.u_csr_file.mstatus !== 32'h1880)
                $fatal(1, "MRET did not use latest mepc/mstatus");
            #1;
            if (dut.pc !== (mret_count == 1 ? 32'd40 : 32'd48) ||
                dut.u_csr_file.mstatus !== 32'h1888)
                $fatal(1, "MRET redirect/status restore wrong");
        end
        if (dut.id_fire && dut.if_id_pc == 32'h180)
            handler_entry_count = handler_entry_count + 1;
        if (dut.the_instance_name.wr_en && dut.data_sram_addr == 32'h2f0) begin
            sentinel_write_count = sentinel_write_count + 1;
            if (mret_count == 0) $fatal(1, "younger store escaped before MRET");
        end
    end
endmodule
