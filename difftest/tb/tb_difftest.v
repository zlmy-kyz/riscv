// ============================================================================
// tb_difftest.v -- 黄金轨迹差分验证测试台
// ----------------------------------------------------------------------------
// 做什么
//   1) DUT（soc_top 内的 mycpu_sync）每提交一条写寄存器的指令，就把
//      {PC, 目标寄存器, 写数据}
//      和黄金轨迹逐条比对；一旦不一致，立刻打印现场并 $finish 停止仿真。
//   2) 同时比对**指令流**：每拍提交级存在有效指令时，比对 {PC, 指令}。
//      这一路比写回轨迹更严 —— 取指错、分支冲刷错、多跑一条错路指令，
//      都会在第一时间露头，而不是等到某条指令写回时才暴露。
//   3) 跑到停机点（jal x0, self）后，把 DUT 的寄存器堆与数据存储器整体导出，
//      交给 rvtool.py 与黄金终值做全量比对。
//
// 采样点（关键，不能随便改）
//   ★ 指令流/停机判定探的 mem_wb_* 必须与 debug_wb_* 同相位 —— 两者都要在【提交级】。
//     提交级随流水深度走：2 级时 if_id_* → 加 ID/EX 后 id_ex_* → 加 EX/MEM 后 ex_mem_*
//     → 加 MEM/WB 后 mem_wb_*。（本工程当前是 5 级 IF|ID|EX|MEM|WB）
//     探错级的症状：指令流能对上（两条路各走各的表），但停机导出会早一拍，
//     最后一条指令的写回还没落进寄存器堆（prog0_alu 的 x11 就栽在这）。
//   Verilog 里 always @(posedge clk) 读到的是"沿前值"，也就是**本沿正要提交**的那条
//   指令 —— 这正是我们要的相位。若改成沿后采样，会整体错开一拍。
//
// 文件约定（都在 vvp 的工作目录下）
//   rom.hex / ram.hex    存储器初值      <- rvtool.py build 生成
//   trace.txt            写回事件        <- 同上
//   itrace.txt           指令流          <- 同上
//   rf_dut.txt           DUT 寄存器堆终值   （本 tb 输出）
//   mem_dut.txt          DUT 数据存储器终值 （本 tb 输出）
// ============================================================================
`timescale 1ns / 1ps

module tb_difftest;

    parameter MAX_CYCLE = 20000;      // 拍数上限：跑飞时给出明确失败而不是挂死
    parameter INST_REQ_STALL_CYCLES = 0;
    parameter INST_RSP_DELAY_CYCLES = 0;
    parameter DATA_REQ_STALL_CYCLES = 0;
    parameter DATA_RSP_DELAY_CYCLES = 0;

    // ---------------- 时钟与复位 ----------------
    reg clk    = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;             // 10ns 周期

    // ---------------- DUT ----------------
    wire [31:0] dbg_pc;
    wire [3:0]  dbg_we;
    wire [4:0]  dbg_wnum;
    wire [31:0] dbg_wdata;

    soc_top #(
        .INST_REQ_STALL_CYCLES(INST_REQ_STALL_CYCLES),
        .INST_RSP_DELAY_CYCLES(INST_RSP_DELAY_CYCLES),
        .DATA_REQ_STALL_CYCLES(DATA_REQ_STALL_CYCLES),
        .DATA_RSP_DELAY_CYCLES(DATA_RSP_DELAY_CYCLES)
    ) dut (
        .clk               (clk),
        .resetn            (resetn),
        .irq_external      (1'b0),
        .irq_software      (1'b0),
        .irq_timer         (1'b0),
        .debug_wb_pc       (dbg_pc),
        .debug_wb_rf_we    (dbg_we),
        .debug_wb_rf_wnum  (dbg_wnum),
        .debug_wb_rf_wdata (dbg_wdata)
    );

    // ---------------- 黄金轨迹 ----------------
    integer f_tr, f_it, f_rf, f_mem;
    integer n_wb, n_it, halt_pc, halt_pc_i;
    integer wb_i, it_i, rs;
    integer e_pc, e_wnum, e_data, e_inst;
    integer n_wb_chk, n_it_chk, cyc;
    integer i;
    reg [31:0] prev_pc;               // 同一条指令在 ID 多占几拍（如 load 停拍）时去重

    // ---------------- 失败/通过：唯一的两个出口 ----------------
    task fail_stop;
        begin
            $display("");
            $display("================================================================");
            $display("  RESULT: FAIL   —— 差分比对不一致，仿真在此立即停止");
            $display("  已通过：指令流 %0d/%0d 条，写回轨迹 %0d/%0d 次",
                     n_it_chk, n_it, n_wb_chk, n_wb);
            $display("================================================================");
            $finish;
        end
    endtask

    task dump_final;
        begin
            f_rf = $fopen("rf_dut.txt", "w");
            $fwrite(f_rf, "%08x\n", 32);
            for (i = 0; i < 32; i = i + 1)
                $fwrite(f_rf, "%02x %08x\n", i, dut.u_cpu.u_regfile.rf[i]);
            $fclose(f_rf);

            f_mem = $fopen("mem_dut.txt", "w");
            $fwrite(f_mem, "%08x\n", 1024);
            for (i = 0; i < 1024; i = i + 1)
                $fwrite(f_mem, "%04x %08x\n", i, dut.u_data_ram.mem[i]);
            $fclose(f_mem);
        end
    endtask

    task pass_stop;
        begin
            $display("");
            $display("================================================================");
            $display("  RESULT: PASS");
            $display("    指令流比对  : %0d / %0d 条   全部一致", n_it_chk, n_it);
            $display("    写回轨迹比对: %0d / %0d 次   全部一致", n_wb_chk, n_wb);
            $display("    总拍数      : %0d", cyc);
            $display("    -> 已导出 rf_dut.txt / mem_dut.txt，请再跑 rvtool.py check 做终值比对");
            $display("================================================================");
            $finish;
        end
    endtask

    // ---------------- 读入黄金轨迹 ----------------
    initial begin
        n_wb_chk = 0; n_it_chk = 0; wb_i = 0; it_i = 0; cyc = 0;
        prev_pc = 32'hFFFFFFFF;

        f_tr = $fopen("trace.txt", "r");
        if (f_tr == 0) begin
            $display("[FATAL] 打不开 trace.txt —— 请先用 rvtool.py build 生成黄金轨迹");
            $finish;
        end
        rs = $fscanf(f_tr, "%h %h\n", halt_pc, n_wb);

        f_it = $fopen("itrace.txt", "r");
        if (f_it == 0) begin
            $display("[FATAL] 打不开 itrace.txt —— 请先用 rvtool.py build 生成黄金轨迹");
            $finish;
        end
        rs = $fscanf(f_it, "%h %h\n", halt_pc_i, n_it);

        $display("================================================================");
        $display("  黄金轨迹差分验证");
        $display("    halt_pc   = %08x", halt_pc);
        $display("    期望写回   = %0d 次", n_wb);
        $display("    期望指令   = %0d 条", n_it);
        $display("================================================================");
    end

    // ---------------- 复位序列（驱动在 negedge，避开采样竞争）----------------
    initial begin
        resetn = 1'b0;
        repeat (8) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;
    end

`ifdef WAVE
    initial begin
        $dumpfile("wave.vcd");
        $dumpvars(0, tb_difftest);
    end
`endif

    // ---------------- 比对主体 ----------------
    always @(posedge clk) begin
        if (resetn) begin
            cyc = cyc + 1;

            if (cyc > MAX_CYCLE) begin
                $display("[FAIL] 超过 %0d 拍仍未到停机点（程序跑飞 / PC 卡死）", MAX_CYCLE);
                $display("       当前提交级: pc=%08x inst=%08x valid=%b",
                         dut.u_cpu.mem_wb_pc, dut.u_cpu.mem_wb_inst,
                         dut.u_cpu.mem_wb_valid);
                fail_stop;
            end

            // =========================================================
            // 1) 写回轨迹比对 —— 用户方案的核心
            // =========================================================
            if (|dbg_we && dbg_wnum != 5'd0) begin
                if (wb_i >= n_wb) begin
                    $display("[FAIL] 多出的写回（黄金轨迹已经走完）");
                    $display("       DUT : pc=%08x  x%0d <= %08x", dbg_pc, dbg_wnum, dbg_wdata);
                    fail_stop;
                end
                rs = $fscanf(f_tr, "%h %h %h\n", e_pc, e_wnum, e_data);
                if (dbg_pc !== e_pc) begin
                    $display("[FAIL] 写回 PC 不一致 —— 第 %0d 次写回", wb_i);
                    $display("       DUT : pc=%08x  x%0d <= %08x", dbg_pc, dbg_wnum, dbg_wdata);
                    $display("       黄金: pc=%08x  x%0d <= %08x", e_pc, e_wnum, e_data);
                    fail_stop;
                end
                if (dbg_wnum !== e_wnum || dbg_wdata !== e_data) begin
                    $display("[FAIL] 写回内容不一致 @pc=%08x —— 第 %0d 次写回", dbg_pc, wb_i);
                    $display("       DUT : x%0d <= %08x", dbg_wnum, dbg_wdata);
                    $display("       黄金: x%0d <= %08x", e_wnum, e_data);
                    fail_stop;
                end
                wb_i    = wb_i + 1;
                n_wb_chk = n_wb_chk + 1;
            end

            // =========================================================
            // 2) 指令流比对 —— 比写回更严，取指/冲刷错误在这里就暴露
            //    ★ 探测点 = 提交级 mem_wb_*(WB 级)，必须与第 1 路(调试口)同相位。
            //      提交级随流水深度走，探错级的症状：指令流能对上（两条路各走各的表），
            //      但停机导出会早一拍，最后一条指令的写回还没落进寄存器堆
            //      （prog0_alu 的 x11 就栽在这，详见文件头的"采样点"说明）。
            //    去重规则：一条指令如果在提交级停留多拍（load 停拍），
            //    那几拍的 PC 相同且中间没有气泡 —— 只比第一次。
            //    中间出现气泡（valid=0）则清掉去重状态，允许同一 PC 再次出现
            //    （分支跳回原处是合法的）。
            // =========================================================
            if (!dut.u_cpu.mem_wb_valid) begin
                prev_pc = 32'hFFFFFFFF;
            end
            else if (dut.u_cpu.mem_wb_pc !== prev_pc) begin
                if (it_i >= n_it) begin
                    $display("[FAIL] 多执行的指令（黄金指令流已走完）");
                    $display("       DUT : pc=%08x inst=%08x",
                             dut.u_cpu.mem_wb_pc, dut.u_cpu.mem_wb_inst);
                    fail_stop;
                end
                rs = $fscanf(f_it, "%h %h\n", e_pc, e_inst);
                if (dut.u_cpu.mem_wb_pc !== e_pc || dut.u_cpu.mem_wb_inst !== e_inst) begin
                    $display("[FAIL] 指令流不一致 —— 第 %0d 条有效指令", it_i);
                    $display("       DUT : pc=%08x inst=%08x",
                             dut.u_cpu.mem_wb_pc, dut.u_cpu.mem_wb_inst);
                    $display("       黄金: pc=%08x inst=%08x", e_pc, e_inst);
                    fail_stop;
                end
                prev_pc  = dut.u_cpu.mem_wb_pc;
                it_i     = it_i + 1;
                n_it_chk = n_it_chk + 1;

                // =========================================================
                // 3) 停机判定
                //    ★ 同样在提交级判定：停机指令【提交】的那一拍才导出终值，
                //      此时它前面那条的写回已经落进寄存器堆。
                // =========================================================
                if (dut.u_cpu.mem_wb_pc == halt_pc) begin
                    dump_final;
                    if (wb_i != n_wb || it_i != n_it) begin
                        $display("[FAIL] 已到停机点，但轨迹没走完：指令流 %0d/%0d，写回 %0d/%0d",
                                 it_i, n_it, wb_i, n_wb);
                        fail_stop;
                    end
                    pass_stop;
                end
            end
        end
    end

endmodule
