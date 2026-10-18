`timescale 1ns/1ps
// ===========================================================================
// tb_br_ex_redirect.v
//   针对 "ID 判定 + EX 重定向" 改动的隔离回归台。
//   - 指令/数据各一个 1 拍同步存储器模型，可每拍接受新请求并回一个响应
//   - 不依赖 Pango 原语 / ModelSim，纯 iverilog
//   - 断言只看架构可见结果（DMEM 内容、trap 计数、退休数），不看内部信号
// ===========================================================================
module tb_br_ex_redirect;

    reg clk = 1'b0;
    reg resetn = 1'b0;
    always #5 clk = ~clk;

    reg [31:0] imem [0:511];
    reg [31:0] dmem [0:511];

    wire        inst_req_valid;
    wire [31:0] inst_req_addr;
    reg         inst_req_ready = 1'b1;
    reg         inst_rsp_valid = 1'b0;
    reg  [31:0] inst_rsp_rdata = 32'b0;
    reg         inst_rsp_error = 1'b0;

    wire        data_req_valid;
    wire        data_req_write;
    wire [ 1:0] data_req_size;
    wire [31:0] data_req_addr;
    wire [31:0] data_req_wdata;
    wire [ 3:0] data_req_wstrb;
    reg         data_req_ready = 1'b1;
    reg         data_rsp_valid = 1'b0;
    reg  [31:0] data_rsp_rdata = 32'b0;
    reg         data_rsp_error = 1'b0;

    wire [31:0] debug_wb_pc;
    wire [ 3:0] debug_wb_rf_we;
    wire [ 4:0] debug_wb_rf_wnum;
    wire [31:0] debug_wb_rf_wdata;
    wire [31:0] debug_inst;
    wire [ 7:0] perf_events;
    wire [31:0] perf_branch_target;
    wire [31:0] perf_fetch_pc;

    mycpu_sync #(
        .RESET_PC(32'h0000_0000)
    ) u_dut (
        .clk(clk), .resetn(resetn),
        .irq_external(1'b0), .irq_software(1'b0), .irq_timer(1'b0),
        .memory_order_busy(1'b0),
        .inst_req_valid(inst_req_valid), .inst_req_addr(inst_req_addr),
        .inst_req_ready(inst_req_ready),
        .inst_rsp_valid(inst_rsp_valid), .inst_rsp_rdata(inst_rsp_rdata),
        .inst_rsp_error(inst_rsp_error),
        .data_req_valid(data_req_valid), .data_req_write(data_req_write),
        .data_req_size(data_req_size), .data_req_addr(data_req_addr),
        .data_req_wdata(data_req_wdata), .data_req_wstrb(data_req_wstrb),
        .data_req_ready(data_req_ready),
        .data_rsp_valid(data_rsp_valid), .data_rsp_rdata(data_rsp_rdata),
        .data_rsp_error(data_rsp_error),
        .debug_wb_pc(debug_wb_pc), .debug_wb_rf_we(debug_wb_rf_we),
        .debug_wb_rf_wnum(debug_wb_rf_wnum), .debug_wb_rf_wdata(debug_wb_rf_wdata),
        .debug_inst(debug_inst),
        .perf_events(perf_events),
        .perf_branch_target(perf_branch_target),
        .perf_fetch_pc(perf_fetch_pc)
    );

    // ---------------- 可配置延迟的同步存储器模型 ----------------
    // +DELAY=n 让每个请求等 n 拍才返回，用来复现 DDR 的多拍响应，
    // 覆盖"分支在 EX 等 load 响应"这类真实场景。默认 1 拍。
    integer    delay = 1;
    integer    i_cnt = 0;
    integer    d_cnt = 0;
    reg [31:0] i_addr_q  = 32'b0;
    reg [31:0] d_addr_q  = 32'b0;
    reg        d_write_q = 1'b0;
    reg [31:0] d_wdata_q = 32'b0;
    reg [ 3:0] d_wstrb_q = 4'b0;
    integer    wi;

    always @(posedge clk) begin
        inst_rsp_valid <= (i_cnt == 1);
        if (i_cnt == 1) inst_rsp_rdata <= imem[i_addr_q[10:2]];
        if (inst_req_valid && inst_req_ready) begin
            i_addr_q <= inst_req_addr;
            i_cnt    <= delay;
        end else if (i_cnt > 0) begin
            i_cnt <= i_cnt - 1;
        end
    end

    always @(posedge clk) begin
        data_rsp_valid <= (d_cnt == 1);
        if (d_cnt == 1) begin
            data_rsp_rdata <= dmem[d_addr_q[10:2]];
            if (d_write_q) begin
                for (wi = 0; wi < 4; wi = wi + 1)
                    if (d_wstrb_q[wi])
                        dmem[d_addr_q[10:2]][8*wi +: 8] <= d_wdata_q[8*wi +: 8];
            end
        end
        if (data_req_valid && data_req_ready) begin
            d_addr_q  <= data_req_addr;
            d_write_q <= data_req_write;
            d_wdata_q <= data_req_wdata;
            d_wstrb_q <= data_req_wstrb;
            d_cnt     <= delay;
        end else if (d_cnt > 0) begin
            d_cnt <= d_cnt - 1;
        end
    end

    // ---------------- 观测 ----------------
    integer retire = 0;
    integer traps  = 0;
    integer cycles = 0;
    reg     bench_done = 1'b0;

    always @(posedge clk) begin
        cycles = cycles + 1;
        if (resetn) begin
            if (perf_events[0]) retire = retire + 1;
            if (perf_events[1]) traps  = traps + 1;
            // bench 程序最后一条 store 写 dmem[8] (0x20) 作为完成标记
            if (!bench_done && data_req_valid && data_req_ready && data_req_write &&
                (data_req_addr[10:2] == 10'd8) && (data_req_wstrb != 4'b0)) begin
                bench_done <= 1'b1;
                $display("BENCH_DONE cycles=%0d retire=%0d", cycles, retire);
            end
        end
    end

    integer errors = 0;
    integer i;
    integer mode = 0;
    reg [31:0] exp_dmem [0:31];

    task chk32(input [31:0] addr, input [31:0] exp, input [255:0] tag);
        begin
            if (dmem[addr[10:2]] !== exp) begin
                errors = errors + 1;
                $display("  [FAIL] %0s dmem[%0d] got=%h exp=%h",
                         tag, addr, dmem[addr[10:2]], exp);
            end else begin
                $display("  [ ok ] %0s dmem[%0d]=%h", tag, addr, dmem[addr[10:2]]);
            end
        end
    endtask

    initial begin
        if (!$value$plusargs("MODE=%d", mode)) mode = 0;
        if (!$value$plusargs("DELAY=%d", delay)) delay = 1;
        if (delay < 1) delay = 1;
        for (i = 0; i < 512; i = i + 1) begin
            imem[i] = 32'h0000_0013;   // NOP
            dmem[i] = 32'h0000_0000;
        end
        $readmemh("imem.hex", imem);
        $readmemh("dmem_init.hex", dmem);

        repeat (6) @(posedge clk);
        resetn = 1'b1;
        if (mode == 2) repeat (30000) @(posedge clk);
        else           repeat (3000 * delay) @(posedge clk);

        $display("---- mode=%0d delay=%0d retire=%0d traps=%0d cycles=%0d ----",
                 mode, delay, retire, traps, cycles);

        if (mode == 2) begin
            if (!bench_done) begin
                errors = errors + 1;
                $display("  [FAIL] bench did not finish");
            end
            chk32(32'd32, 32'd1000, "bench_count");
        end else if (mode == 0) begin
            chk32(32'd0,  32'h0000_000C, "basic_branch");
            chk32(32'd4,  32'h0000_002A, "jal_jalr");
            chk32(32'd8,  32'h0000_0001, "load_to_branch");
            chk32(32'd12, 32'h0000_0007, "load_to_jalr");
            chk32(32'd16, 32'h0000_0005, "b2b_loop");
            chk32(32'd20, 32'h0000_0009, "branch_in_stall");

            if (traps != 0) begin
                errors = errors + 1;
                $display("  [FAIL] unexpected traps=%0d", traps);
            end
            if (retire < 40) begin
                errors = errors + 1;
                $display("  [FAIL] too few retired instructions: %0d", retire);
            end
        end else begin
            // mode 1: 目标错位必须走异常而不是重定向。
            chk32(32'd24, 32'h0000_0001, "trap_setup_ran");
            chk32(32'd28, 32'h0000_0000, "no_fallthrough_after_trap");
            if (traps < 1) begin
                errors = errors + 1;
                $display("  [FAIL] misaligned jalr did not trap");
            end
        end

        if (errors == 0) $display("RESULT: PASS br_ex_redirect errors=0");
        else             $display("RESULT: FAIL br_ex_redirect errors=%0d", errors);
        $finish;
    end

    initial begin
        repeat (300000) @(posedge clk);
        $display("RESULT: FAIL br_ex_redirect timeout");
        $finish;
    end

endmodule
