`timescale 1ns / 10fs

// Physical-DDR arbitration check. The generated on-chip IP/DDR3 model are
// instantiated by base; this TB injects requests at the SoC's decoded DDR
// inputs so both bridge ports can be active in the same cycle.
module tb_soc_ddr3_pds_ip_contention;
    tb_soc_ddr3_pds_ip base();

    initial begin
        #200000;
        $fatal(1, "RESULT: FAIL physical DDR contention timeout");
    end

    initial begin
        @(posedge base.soc_resetn);
        @(negedge base.core_clk);

        // Seed one physical DDR word through the data port.
        force base.dut.u_soc.inst_ddr_req_valid = 1'b0;
        force base.dut.u_soc.data_ddr_req_valid = 1'b1;
        force base.dut.u_soc.data_ddr_req_write = 1'b1;
        force base.dut.u_soc.data_ddr_req_size = 2'd2;
        force base.dut.u_soc.data_ddr_req_addr = 32'h0000_0100;
        force base.dut.u_soc.data_ddr_req_wdata = 32'haabb_ccdd;
        force base.dut.u_soc.data_ddr_req_wstrb = 4'hf;
        #1;
        if (base.dut.u_soc.data_ddr_req_ready !== 1'b1)
            $fatal(1, "RESULT: FAIL initial DDR write not accepted");
        @(posedge base.core_clk);
        @(negedge base.core_clk);
        force base.dut.u_soc.data_ddr_req_valid = 1'b0;
        @(posedge base.dut.u_soc.data_ddr_rsp_valid);
        if (base.dut.u_soc.data_ddr_rsp_error !== 1'b0)
            $fatal(1, "RESULT: FAIL initial DDR write response");
        $display("CHECK: seeded DDR word through data bridge port");

        wait (base.dut.u_soc.g_ddr.u_ddr_bridge.state == 3'd0);
        @(negedge base.core_clk);
        // Both reads stay valid until their respective ready handshake.
        force base.dut.u_soc.data_ddr_req_write = 1'b0;
        force base.dut.u_soc.data_ddr_req_valid = 1'b1;
        force base.dut.u_soc.inst_ddr_req_addr = 32'h0000_0100;
        force base.dut.u_soc.inst_ddr_req_valid = 1'b1;
        #1;
        if (base.dut.u_soc.data_ddr_req_ready !== 1'b1 ||
            base.dut.u_soc.inst_ddr_req_ready !== 1'b0)
            $fatal(1, "RESULT: FAIL physical DDR data priority");
        $display("CHECK: simultaneous DDR reads accepted data first");
        @(posedge base.core_clk);
        @(negedge base.core_clk);
        force base.dut.u_soc.data_ddr_req_valid = 1'b0;
        @(posedge base.dut.u_soc.data_ddr_rsp_valid);
        if (base.dut.u_soc.data_ddr_rsp_error !== 1'b0 ||
            base.dut.u_soc.data_ddr_rsp_rdata !== 32'haabb_ccdd ||
            base.dut.u_soc.inst_ddr_rsp_valid !== 1'b0)
            $fatal(1, "RESULT: FAIL data DDR read result before instruction");
        $display("CHECK: physical DDR data read returned aabbccdd");

        wait (base.dut.u_soc.inst_ddr_req_ready == 1'b1);
        @(posedge base.core_clk);
        @(negedge base.core_clk);
        force base.dut.u_soc.inst_ddr_req_valid = 1'b0;
        @(posedge base.dut.u_soc.inst_ddr_rsp_valid);
        if (base.dut.u_soc.inst_ddr_rsp_error !== 1'b0 ||
            base.dut.u_soc.inst_ddr_rsp_rdata !== 32'haabb_ccdd ||
            base.dut.u_soc.data_ddr_rsp_valid !== 1'b0)
            $fatal(1, "RESULT: FAIL held instruction DDR read result");
        $display("RESULT: PASS physical DDR data-priority contention and both reads");
        $finish;
    end
endmodule
