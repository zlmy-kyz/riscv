`timescale 1ns/1ps

// 三源优先级、撤销、同步故障优先、重复 pending、store 排空的定向验证。
module tb_irq_step11;
    reg clk = 0;
    reg resetn = 0;
    reg irq_external = 1, irq_software = 1, irq_timer = 1;
    always #5 clk = ~clk;
    mycpu_sync dut (
        .clk(clk), .resetn(resetn),
        .irq_external(irq_external), .irq_software(irq_software),
        .irq_timer(irq_timer)
    );
    wire [31:0] trace_irq_raw = (irq_external ? 32'h800 : 32'b0) |
                                (irq_software ? 32'h008 : 32'b0) |
                                (irq_timer ? 32'h080 : 32'b0);
    `include "difftest/tb/arch_trace.vh"

    integer irq_count = 0;
    integer sync_count = 0;
    integer store_req_28 = 0;
    integer store_retire_28 = 0;
    integer store_req_34 = 0;
    integer store_retire_34 = 0;
    integer drain_seen = 0;
    integer cancel_seen = 0;
    integer load_use_irq_seen = 0;
    integer addi30_retire_count = 0;
    integer addi30_before_irq = 0;
    integer next_issue_tag = 1;
    integer idex_tag = 0;
    reg store_seen [0:10000];
    integer tag_i;
    reg fault_irq_injected = 0;
    reg store_irq_injected = 0;
    reg cancel_injected = 0;
    reg cancel_active = 0;
    reg mem_store_irq_injected = 0;
    reg wb_store_irq_injected = 0;
    reg load_use_irq_injected = 0;
    reg [31:0] expected_arch_pc = 0;
    reg [31:0] expected_mepc [0:8];
    reg [4:0] expected_cause [0:8];

    initial for (tag_i = 0; tag_i <= 10000; tag_i = tag_i + 1)
        store_seen[tag_i] = 0;

    initial begin
        expected_cause[0] = 11; expected_mepc[0] = 32'h20;
        expected_cause[1] = 3;  expected_mepc[1] = 32'h20;
        expected_cause[2] = 7;  expected_mepc[2] = 32'h20;
        expected_cause[3] = 3;  expected_mepc[3] = 32'h28;
        expected_cause[4] = 11; expected_mepc[4] = 32'h2c;
        expected_cause[5] = 11; expected_mepc[5] = 32'h2c;
        expected_cause[6] = 11; expected_mepc[6] = 32'h3c;
        expected_cause[7] = 7;  expected_mepc[7] = 32'h30;
        expected_cause[8] = 3;  expected_mepc[8] = 32'h30;
    end

    initial begin
        #50000;
        $fatal(1, "IRQ step11 timeout irq=%0d sync=%0d cancel=%0d mem=%0d wb=%0d x8=%0d state=%0d",
               irq_count, sync_count, cancel_seen, mem_store_irq_injected,
               wb_store_irq_injected, dut.u_regfile.rf[8], dut.flow_state);
    end

    initial begin
        repeat (8) @(posedge clk);
        @(negedge clk) resetn = 1;
        wait (irq_count == 9 && cancel_seen && dut.u_regfile.rf[8] >= 4);
        repeat (30) @(posedge clk);
        #1;
        if (irq_count != 9 || sync_count != 1 || !fault_irq_injected ||
            !store_irq_injected || !cancel_injected ||
            !mem_store_irq_injected || !wb_store_irq_injected ||
            !load_use_irq_injected || !load_use_irq_seen || !drain_seen ||
            dut.u_regfile.rf[9] !== 32'h888 ||
            dut.u_regfile.rf[10] !== 0 ||
            dut.u_regfile.rf[23] !== 10 ||
            dut.the_instance_name.mem[192] !== 32'h55 ||
            dut.the_instance_name.mem[193] !== 32'h56 ||
            dut.the_instance_name.mem[194] !== 0 ||
            dut.u_csr_file.mie !== 32'h888 ||
            !dut.u_csr_file.mstatus[3])
            $fatal(1, "IRQ final state wrong irq=%0d sync=%0d req=%0d retire=%0d mipread=%h count=%h x10=%h mem0=%h mem1=%h mie=%h mstatus=%h req34=%0d ret34=%0d",
                   irq_count, sync_count, store_req_28, store_retire_28,
                   dut.u_regfile.rf[9], dut.u_regfile.rf[23],
                   dut.u_regfile.rf[10], dut.the_instance_name.mem[192],
                   dut.the_instance_name.mem[193], dut.u_csr_file.mie,
                   dut.u_csr_file.mstatus, store_req_34, store_retire_34);
        $display("RESULT: PASS MEI>MSI>MTI, sync fault priority, reentry, cancellation and precise store");
        $finish;
    end

    // 只在下降沿改变同步电平，让上升沿采样与检查没有竞争。
    always @(negedge clk) if (resetn) begin
        if (irq_count == 1) irq_external = 0;
        if (irq_count == 2) irq_software = 0;
        if (irq_count == 3) irq_timer = 0;
        if (irq_count == 4) irq_software = 0;
        if (irq_count == 6 && !mem_store_irq_injected) irq_external = 0;
        if (irq_count == 7) irq_external = 0;
        if (irq_count == 8) irq_timer = 0;
        if (irq_count == 9) irq_software = 0;

        if (irq_count == 3 && !fault_irq_injected &&
            dut.id_ex_valid && dut.id_ex_pc == 32'h24) begin
            irq_software = 1;
            fault_irq_injected = 1;
        end
        if (irq_count == 4 && !store_irq_injected &&
            dut.id_ex_valid && dut.id_ex_pc == 32'h28) begin
            irq_external = 1;
            store_irq_injected = 1;
        end
        if (irq_count == 6 && !cancel_injected &&
            dut.id_ex_valid && dut.id_ex_pc == 32'h34) begin
            irq_timer = 1;
            cancel_injected = 1;
            cancel_active = 1;
        end else if (cancel_active) begin
            irq_timer = 0;
            cancel_active = 0;
        end
        if (irq_count == 6 && cancel_seen && !mem_store_irq_injected &&
            dut.ex_mem_valid && dut.ex_mem_pc == 32'h34) begin
            irq_external = 1;
            mem_store_irq_injected = 1;
        end
        if (irq_count == 7 && !wb_store_irq_injected &&
            dut.mem_wb_valid && dut.mem_wb_pc == 32'h28) begin
            irq_timer = 1;
            wb_store_irq_injected = 1;
        end
        if (irq_count == 8 && !load_use_irq_injected &&
            dut.load_use && dut.id_ex_valid && dut.id_ex_pc == 32'h2c &&
            dut.if_id_valid && dut.if_id_pc == 32'h30) begin
            irq_software = 1;
            load_use_irq_injected = 1;
            addi30_before_irq = addi30_retire_count;
            if (dut.id_fire) $fatal(1, "load-use consumer issued on IRQ arrival");
            load_use_irq_seen = load_use_irq_seen + 1;
        end
    end

    always @(posedge clk) if (resetn) begin
        if (load_use_irq_injected && irq_count == 8 &&
            dut.if_id_valid && dut.if_id_pc == 32'h30 && dut.id_fire)
            $fatal(1, "load-use consumer issued before pending IRQ was accepted");
        if (dut.mem_wb_valid && (dut.mem_wb_exc_valid || dut.wb_csr_illegal) &&
            (dut.rf_we || dut.normal_retire))
            $fatal(1, "faulting instruction retired or wrote GPR");
        if (dut.mem_store_request && dut.id_ex_pc == 32'h40)
            $fatal(1, "wrong-path store issued a memory request");
        if (dut.mem_store_request) begin
            if (idex_tag < 1 || idex_tag > 10000 || store_seen[idex_tag])
                $fatal(1, "store committed twice or without an issue token");
            store_seen[idex_tag] = 1;
        end
        if (dut.normal_retire && dut.mem_wb_pc == 32'h30)
            addi30_retire_count = addi30_retire_count + 1;
        if (dut.kill_id_ex)
            idex_tag <= 0;
        else if (dut.id_fire) begin
            if (next_issue_tag > 10000) $fatal(1, "issue token overflow");
            idex_tag <= next_issue_tag;
            next_issue_tag = next_issue_tag + 1;
        end else
            idex_tag <= 0;
        if (dut.mem_store_request && dut.id_ex_pc == 32'h28)
            store_req_28 = store_req_28 + 1;
        if (dut.mem_store_request && dut.id_ex_pc == 32'h34)
            store_req_34 = store_req_34 + 1;
        if (dut.normal_retire && dut.mem_wb_pc == 32'h28)
            store_retire_28 = store_retire_28 + 1;
        if (dut.normal_retire && dut.mem_wb_pc == 32'h34)
            store_retire_34 = store_retire_34 + 1;
        if (dut.normal_retire)
            expected_arch_pc = (dut.mem_wb_pc == 32'h3c) ?
                               32'h28 : dut.mem_wb_pc + 32'd4;
        if (dut.mret_commit)
            expected_arch_pc = dut.csr_mret_target;
        if (dut.flow_state == dut.FLOW_IRQ_DRAIN) drain_seen = drain_seen + 1;
        if (cancel_injected && !cancel_active &&
            dut.flow_state == dut.FLOW_RUN && !irq_timer)
            cancel_seen = cancel_seen + 1;
        if (dut.irq_take) begin
            if (irq_count >= 9 || !dut.pipeline_empty ||
                dut.mem_load_request || dut.mem_store_request ||
                dut.id_fire || dut.normal_retire || dut.sync_trap_event ||
                dut.arch_next_pc !== expected_mepc[irq_count] ||
                dut.arch_next_pc !== expected_arch_pc ||
                dut.irq_cause !== expected_cause[irq_count])
                $fatal(1, "IRQ take[%0d] invalid cause=%0d pc=%h", irq_count,
                       dut.irq_cause, dut.arch_next_pc);
            if (irq_count == 4 &&
                (store_req_28 != 1 || store_retire_28 != 1 ||
                 dut.the_instance_name.mem[192] !== 32'h55))
                $fatal(1, "EX store did not finish exactly once before IRQ");
            if (irq_count >= 4 &&
                (store_req_28 != store_retire_28 ||
                 store_req_34 != store_retire_34))
                $fatal(1, "store request/retirement count differs at IRQ boundary");
            if (irq_count == 8 && addi30_retire_count != addi30_before_irq)
                $fatal(1, "load-use consumer retired before IRQ boundary");
            irq_count = irq_count + 1;
            expected_arch_pc = 32'h100;
            #1;
            if (dut.u_csr_file.mcause !==
                    (32'h8000_0000 | {27'b0, expected_cause[irq_count-1]}) ||
                dut.u_csr_file.mepc !== expected_mepc[irq_count-1] ||
                dut.u_csr_file.mtval !== 0 || dut.pc !== 32'h100 ||
                dut.arch_next_pc !== 32'h100 ||
                dut.u_csr_file.mstatus[3] !== 0)
                $fatal(1, "IRQ trap CSR/PC wrong at take[%0d]", irq_count-1);
        end else if (dut.sync_trap_event) begin
            sync_count = sync_count + 1;
            expected_arch_pc = 32'h100;
            if (sync_count != 1 || !fault_irq_injected ||
                dut.mem_wb_pc !== 32'h24 || dut.wb_trap_cause !== 5'd4 ||
                dut.wb_trap_tval !== 32'h301 || dut.irq_take)
                $fatal(1, "old synchronous load fault lost priority");
            #1;
            if (dut.u_csr_file.mcause !== 32'd4 ||
                dut.u_csr_file.mepc !== 32'h24 ||
                dut.u_csr_file.mtval !== 32'h301)
                $fatal(1, "synchronous fault CSR wrong");
        end
    end
endmodule
