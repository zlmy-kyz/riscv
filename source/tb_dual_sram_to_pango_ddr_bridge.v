`timescale 1ns / 1ps

module tb_dual_sram_to_pango_ddr_bridge;
    reg clk;
    reg resetn;
    reg ddr_init_done;

    reg         inst_req_valid;
    reg  [31:0] inst_req_addr;
    wire        inst_req_ready;
    wire        inst_rsp_valid;
    wire [31:0] inst_rsp_rdata;
    wire        inst_rsp_error;

    reg         data_req_valid;
    reg         data_req_write;
    reg  [1:0]  data_req_size;
    reg  [31:0] data_req_addr;
    reg  [31:0] data_req_wdata;
    reg  [3:0]  data_req_wstrb;
    wire        data_req_ready;
    wire        data_rsp_valid;
    wire [31:0] data_rsp_rdata;
    wire        data_rsp_error;

    wire [27:0]  axi_awaddr;
    wire         axi_awuser_ap;
    wire [3:0]   axi_awuser_id;
    wire [3:0]   axi_awlen;
    wire         axi_awvalid;
    reg          axi_awready;
    wire [127:0] axi_wdata;
    wire [15:0]  axi_wstrb;
    reg          axi_wready;
    reg  [3:0]   axi_wusero_id;
    reg          axi_wusero_last;

    wire [27:0]  axi_araddr;
    wire         axi_aruser_ap;
    wire [3:0]   axi_aruser_id;
    wire [3:0]   axi_arlen;
    wire         axi_arvalid;
    reg          axi_arready;
    reg  [127:0] axi_rdata;
    reg  [3:0]   axi_rid;
    reg          axi_rlast;
    reg          axi_rvalid;

    reg [127:0] memory [0:15];
    reg          read_pending;
    reg [1:0]    read_delay;
    reg [27:0]   read_addr;
    reg [3:0]    read_id;
    reg          write_pending;
    reg [1:0]    write_delay;
    reg [27:0]   write_addr;
    reg [27:0]   expected_ctrl_addr;
    integer failures;
    integer i;

    dual_sram_to_pango_ddr_bridge dut (
        .clk              (clk),
        .resetn           (resetn),
        .ddr_init_done    (ddr_init_done),
        .inst_req_valid   (inst_req_valid),
        .inst_req_addr    (inst_req_addr),
        .inst_req_ready   (inst_req_ready),
        .inst_rsp_valid   (inst_rsp_valid),
        .inst_rsp_rdata   (inst_rsp_rdata),
        .inst_rsp_error   (inst_rsp_error),
        .data_req_valid   (data_req_valid),
        .data_req_write   (data_req_write),
        .data_req_size    (data_req_size),
        .data_req_addr    (data_req_addr),
        .data_req_wdata   (data_req_wdata),
        .data_req_wstrb   (data_req_wstrb),
        .data_req_ready   (data_req_ready),
        .data_rsp_valid   (data_rsp_valid),
        .data_rsp_rdata   (data_rsp_rdata),
        .data_rsp_error   (data_rsp_error),
        .axi_awaddr       (axi_awaddr),
        .axi_awuser_ap    (axi_awuser_ap),
        .axi_awuser_id    (axi_awuser_id),
        .axi_awlen        (axi_awlen),
        .axi_awready      (axi_awready),
        .axi_awvalid      (axi_awvalid),
        .axi_wdata        (axi_wdata),
        .axi_wstrb        (axi_wstrb),
        .axi_wready       (axi_wready),
        .axi_wusero_id    (axi_wusero_id),
        .axi_wusero_last  (axi_wusero_last),
        .axi_araddr       (axi_araddr),
        .axi_aruser_ap    (axi_aruser_ap),
        .axi_aruser_id    (axi_aruser_id),
        .axi_arlen        (axi_arlen),
        .axi_arready      (axi_arready),
        .axi_arvalid      (axi_arvalid),
        .axi_rdata        (axi_rdata),
        .axi_rid          (axi_rid),
        .axi_rlast        (axi_rlast),
        .axi_rvalid       (axi_rvalid)
    );

    always #5 clk = ~clk;

    // 具有命令和数据延迟的 Pango 用户口行为模型。
    always @(*) begin
        axi_arready = !read_pending;
        axi_awready = !write_pending;
    end

    always @(posedge clk) begin
        axi_rvalid <= 1'b0;
        axi_wready <= 1'b0;

        if (!resetn) begin
            read_pending   <= 1'b0;
            read_delay     <= 2'b0;
            read_addr      <= 28'b0;
            read_id        <= 4'b0;
            write_pending  <= 1'b0;
            write_delay    <= 2'b0;
            write_addr     <= 28'b0;
            axi_rdata      <= 128'b0;
            axi_rid        <= 4'b0;
            axi_rlast      <= 1'b0;
            axi_wusero_id  <= 4'b0;
            axi_wusero_last <= 1'b0;
        end else begin
            if (axi_arvalid && axi_arready) begin
                if ((axi_arlen !== 4'd0) || (axi_araddr[2:0] !== 3'b000)) begin
                    failures = failures + 1;
                    $display("FAIL: read command len/alignment addr=%x len=%x",
                             axi_araddr, axi_arlen);
                end
                expected_ctrl_addr =
                    (((axi_aruser_id == 4'd1) ? data_req_addr : inst_req_addr)
                     >> 1) & 28'hfff_fff8;
                if (axi_araddr !== expected_ctrl_addr) begin
                    failures = failures + 1;
                    $display("FAIL: read address got=%x expected=%x",
                             axi_araddr, expected_ctrl_addr);
                end
                read_pending <= 1'b1;
                read_delay   <= 2'd2;
                read_addr    <= axi_araddr;
                read_id      <= axi_aruser_id;
            end else if (read_pending && (read_delay != 0)) begin
                read_delay <= read_delay - 2'd1;
            end else if (read_pending) begin
                axi_rdata    <= memory[read_addr[6:3]];
                axi_rid      <= read_id;
                axi_rlast    <= 1'b1;
                axi_rvalid   <= 1'b1;
                read_pending <= 1'b0;
            end

            if (axi_awvalid && axi_awready) begin
                if ((axi_awlen !== 4'd0) || (axi_awaddr[2:0] !== 3'b000)) begin
                    failures = failures + 1;
                    $display("FAIL: write command len/alignment addr=%x len=%x",
                             axi_awaddr, axi_awlen);
                end
                expected_ctrl_addr = (data_req_addr >> 1) & 28'hfff_fff8;
                if (axi_awaddr !== expected_ctrl_addr) begin
                    failures = failures + 1;
                    $display("FAIL: write address got=%x expected=%x",
                             axi_awaddr, expected_ctrl_addr);
                end
                write_pending <= 1'b1;
                write_delay   <= 2'd3;
                write_addr    <= axi_awaddr;
            end else if (write_pending && (write_delay != 0)) begin
                write_delay <= write_delay - 2'd1;
            end else if (write_pending) begin
                for (i = 0; i < 16; i = i + 1)
                    if (axi_wstrb[i])
                        memory[write_addr[6:3]][i*8 +: 8] <=
                            axi_wdata[i*8 +: 8];
                axi_wready       <= 1'b1;
                axi_wusero_id    <= axi_awuser_id;
                axi_wusero_last  <= 1'b1;
                write_pending    <= 1'b0;
            end
        end
    end

    task inst_read;
        input [31:0] address;
        input [31:0] expected;
        begin
            @(negedge clk);
            inst_req_addr  = address;
            inst_req_valid = 1'b1;
            while (!inst_req_ready)
                @(negedge clk);
            @(negedge clk);
            inst_req_valid = 1'b0;
            while (!inst_rsp_valid)
                @(negedge clk);
            if ((inst_rsp_rdata !== expected) || inst_rsp_error) begin
                failures = failures + 1;
                $display("FAIL: inst read addr=%x data=%x expected=%x error=%b",
                         address, inst_rsp_rdata, expected, inst_rsp_error);
            end else begin
                $display("PASS: inst read addr=%x data=%x", address, expected);
            end
        end
    endtask

    task data_read;
        input [31:0] address;
        input [31:0] expected;
        begin
            @(negedge clk);
            data_req_addr  = address;
            data_req_write = 1'b0;
            data_req_wstrb = 4'b0;
            data_req_valid = 1'b1;
            while (!data_req_ready)
                @(negedge clk);
            @(negedge clk);
            data_req_valid = 1'b0;
            while (!data_rsp_valid)
                @(negedge clk);
            if ((data_rsp_rdata !== expected) || data_rsp_error) begin
                failures = failures + 1;
                $display("FAIL: data read addr=%x data=%x expected=%x error=%b",
                         address, data_rsp_rdata, expected, data_rsp_error);
            end else begin
                $display("PASS: data read addr=%x data=%x", address, expected);
            end
        end
    endtask

    task data_write;
        input [31:0] address;
        input [31:0] write_data;
        input [3:0]  write_strobe;
        begin
            @(negedge clk);
            data_req_addr  = address;
            data_req_write = 1'b1;
            data_req_wdata = write_data;
            data_req_wstrb = write_strobe;
            data_req_valid = 1'b1;
            while (!data_req_ready)
                @(negedge clk);
            @(negedge clk);
            data_req_valid = 1'b0;
            while (!data_rsp_valid)
                @(negedge clk);
            if (data_rsp_error) begin
                failures = failures + 1;
                $display("FAIL: data write addr=%x error", address);
            end else begin
                $display("PASS: data write addr=%x", address);
            end
        end
    endtask

    initial begin
        clk              = 1'b0;
        resetn           = 1'b0;
        ddr_init_done    = 1'b0;
        inst_req_valid   = 1'b0;
        inst_req_addr    = 32'b0;
        data_req_valid   = 1'b0;
        data_req_write   = 1'b0;
        data_req_size    = 2'd2;
        data_req_addr    = 32'b0;
        data_req_wdata   = 32'b0;
        data_req_wstrb   = 4'b0;
        failures         = 0;

        for (i = 0; i < 16; i = i + 1)
            memory[i] = 128'b0;
        memory[1][1*32 +: 32] = 32'h1122_3344;
        memory[2][3*32 +: 32] = 32'ha5a5_5a5a;
        memory[2][1*32 +: 32] = 32'hdead_beef;
        memory[15][3*32 +: 32] = 32'h89ab_cdef;

        repeat (3) @(posedge clk);
        @(negedge clk);
        resetn = 1'b1;

        // 初始化完成前两个端口都必须保持 back-pressure。
        inst_req_valid = 1'b1;
        inst_req_addr  = 32'h0000_0014;
        repeat (2) begin
            @(negedge clk);
            if (inst_req_ready || data_req_ready) begin
                failures = failures + 1;
                $display("FAIL: request accepted before ddr_init_done");
            end
        end
        inst_req_valid = 1'b0;
        ddr_init_done  = 1'b1;

        // addr 0x14 -> 第 1 个 128-bit 拍的 lane 1。
        inst_read(32'h0000_0014, 32'h1122_3344);

        // addr 0x2c -> 控制器地址 16，第 2 个拍的 lane 3。
        data_read(32'h0000_002c, 32'ha5a5_5a5a);

        // addr 0x25 的 CPU 写数据/strobe 已在 32-bit 字内左移 1 byte；
        // 桥还需把该 32-bit 字移动到拍内 lane 1。
        data_write(32'h0000_0025, 32'h0000_aa00, 4'b0010);
        data_read(32'h0000_0024, 32'hdead_aaef);
        // 覆盖 512 MiB 窗口末端，确保命令地址第 27 位没有被截断。
        data_read(32'h1fff_fffc, 32'h89ab_cdef);

        // 同拍请求时验证数据端优先，指令请求随后仍可被接受。
        @(negedge clk);
        data_req_valid = 1'b1;
        data_req_write = 1'b0;
        data_req_addr  = 32'h0000_002c;
        inst_req_valid = 1'b1;
        inst_req_addr  = 32'h0000_0014;
        #1;
        if (!data_req_ready || inst_req_ready) begin
            failures = failures + 1;
            $display("FAIL: arbitration data_ready=%b inst_ready=%b",
                     data_req_ready, inst_req_ready);
        end
        @(negedge clk);
        data_req_valid = 1'b0;
        while (!data_rsp_valid)
            @(negedge clk);
        while (!inst_req_ready)
            @(negedge clk);
        @(negedge clk);
        inst_req_valid = 1'b0;
        while (!inst_rsp_valid)
            @(negedge clk);
        if (inst_rsp_rdata !== 32'h1122_3344) begin
            failures = failures + 1;
            $display("FAIL: held instruction request after arbitration");
        end else begin
            $display("PASS: data-priority arbitration");
        end

        if (failures == 0)
            $display("RESULT: PASS dual_sram_to_pango_ddr_bridge");
        else
            $display("RESULT: FAIL dual_sram_to_pango_ddr_bridge failures=%0d",
                     failures);
        $finish;
    end

endmodule
