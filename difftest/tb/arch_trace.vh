// 在提交沿输出架构事件；trap/MRET 沿后输出完整状态快照供独立 ISS 重放。
// 引用者需提供 dut、clk、resetn 和由测试台输入组成的 trace_irq_raw。
integer arch_trace_fd;
integer arch_trace_i;
initial begin
    arch_trace_fd = $fopen("arch_events.txt", "w");
    if (arch_trace_fd == 0) $fatal(1, "cannot open arch_events.txt");
end
always @(posedge clk) if (resetn) begin
    if (dut.normal_retire)
        $fwrite(arch_trace_fd, "R %08x %08x %08x %01x %02x %08x\n",
                dut.mem_wb_pc, dut.mem_wb_inst, trace_irq_raw,
                dut.rf_we, dut.rf_we ? dut.rf_waddr : 5'b0,
                dut.rf_we ? dut.rf_wdata : 32'b0);
    else if (dut.sync_trap_event)
        $fwrite(arch_trace_fd, "T %08x %08x %08x %02x %08x\n",
                dut.mem_wb_pc, dut.mem_wb_inst, trace_irq_raw,
                dut.wb_trap_cause, dut.wb_trap_tval);
    else if (dut.mret_commit)
        $fwrite(arch_trace_fd, "M %08x %08x %08x\n",
                dut.mem_wb_pc, dut.mem_wb_inst, trace_irq_raw);
    else if (dut.irq_take)
        $fwrite(arch_trace_fd, "I %08x %02x\n",
                trace_irq_raw, dut.irq_cause);

    if (dut.sync_trap_event || dut.irq_take || dut.mret_commit) begin
        #1;
        $fwrite(arch_trace_fd, "S %08x %08x %08x %08x %08x %08x %08x %08x",
                dut.arch_next_pc, dut.u_csr_file.mstatus,
                dut.u_csr_file.mie, dut.u_csr_file.mtvec,
                dut.u_csr_file.mscratch, dut.u_csr_file.mepc,
                dut.u_csr_file.mcause, dut.u_csr_file.mtval);
        for (arch_trace_i = 0; arch_trace_i < 32; arch_trace_i = arch_trace_i + 1)
            $fwrite(arch_trace_fd, " %08x", dut.u_regfile.rf[arch_trace_i]);
        for (arch_trace_i = 0; arch_trace_i < 1024; arch_trace_i = arch_trace_i + 1)
            $fwrite(arch_trace_fd, " %08x", dut.the_instance_name.mem[arch_trace_i]);
        $fwrite(arch_trace_fd, "\n");
    end
end
