`timescale 1ns/1ps
// Task031 functional Pango user-port test: the sole posted write entry may be
// reused on its own W completion edge (WRITE_BUFFER_TURNOVER_ENABLE).
// Physical DDR performance is a separate board run; this TB uses a TB-local
// user-port model and never loads the DDR PHY.
module tb_write_buffer_turnover_completion #(parameter integer POSTED=1, parameter integer TURNOVER=1);
    // CODEX_OBSERVATION_BEGIN
    integer completion_ev_fd=0, completion_bus_fd=0;
    integer completion_ev_index=0, completion_cycle=0;
    bit completion_short_trace=0, completion_prev_reset=1, completion_prev_init=0;
    reg [31:0] completion_owned_addr=0;
    string completion_ev_path, completion_bus_path;
    // CODEX_OBSERVATION_END
    GTP_GRS GRS_INST (.GRS_N(1'b1));
    // Independent capacity oracle; production RTL fixes I64/D64.
    localparam integer I_LINES = 64;
    localparam integer D_LINES = 64;
    localparam integer D_ENABLED = 1;
    localparam integer ENABLE = 1;
    reg clk=0, resetn=0, init_done=0;
    always #5 clk=~clk;
    reg iv=0, dv=0, dw=0;
    reg [31:0] ia=0, da=0, wd=0;
    reg [3:0] ws=0;
    reg [1:0] ds=2;
    wire ir, dr, isv, dsv, ise, dse;
    wire [31:0] idata, ddata;
    wire [27:0] aa, ra;
    wire av, rv, ardy, rrdy, wrdy, apw, apr;
    wire [255:0] wdata, rdata;
    wire [31:0] wstrb;
    wire [3:0] wid, rid, alen, rlen;
    wire rvalid;
    reg backpressure=1, instant_read=0, instant_write=0;
    reg block_aw=0,block_w=0,block_read=0,force_arready=0;
    // w_early models the real user-port case "WREADY high while AW is still not accepted":
    // the beat is NOT accepted then, so it must not complete the entry or update memory.
    reg w_early=0;
    // Model-side record of whether the current entry's AW was already accepted.
    // The DUT's completion is write_buffer_valid && axi_wready && (aw_sent || axi_awready),
    // so the model mirrors exactly that expression.
    reg model_aw_sent=0;
    integer w_latency=4;
    reg bad_id=0, bad_last=0, cross_id=0, stray_read=0;
    reg reading=0, writing=0;
    reg [27:0] saved_ra=0, saved_aa=0;
    reg [3:0] saved_rid=0;
    integer aw_wait=0, ar_wait=0, r_wait=0, w_wait=0;
    integer ar_count=0, aw_count=0, w_count=0;
    integer i_requests=0, d_requests=0, i_responses=0, d_responses=0;
    integer tests=0, k, lane;
    // Existing 128 backing rows cover all local addresses 0x000..0xfff.
    reg [255:0] memory[0:127];
    reg [255:0] expected_wdata=0;
    reg [31:0] expected_wstrb=0;
    reg [27:0] expected_aa=0, expected_ra=0;
    reg [3:0] expected_rid=0;
    reg ar_blocked=0, aw_blocked=0;
    reg [27:0] held_ra=0, held_aa=0;
    reg [255:0] held_wdata=0;
    reg [31:0] held_wstrb=0;
    reg [3:0] held_rid=0;

    // User-port model: identical timing contract to the verified 027/029 model.
    assign rrdy=init_done && !block_read && (force_arready || (rv && !reading && (!backpressure || ar_wait>=3)));
    assign ardy=init_done && !block_aw && av && !writing && (!backpressure || aw_wait>=2);
    assign rvalid=stray_read || (instant_read && rv && rrdy) || (reading && r_wait==0);
    assign rdata=stray_read ? 256'hbad0bad1_bad2bad3_bad4bad5_bad6bad7_bad0bad1_bad2bad3_bad4bad5_bad6bad7 :
                             memory[(instant_read ? ra : saved_ra)>>3];
    assign wrdy=init_done && !block_w && (w_early || (instant_write && av && ardy) || (writing && w_wait==0));
    wire [27:0] write_addr=instant_write ? aa : saved_aa;
    wire [3:0] model_id=instant_read ? rid : saved_rid;
    wire [3:0] returned_id=bad_id ? 4'hf : (cross_id ? (model_id ^ 4'd1) : model_id);

    reg soc_mode=0,soc_irq=0;
    wire man_busy;
    wire mav,mrv,maw_ap,mar_ap;
    wire [27:0] maa,mra;
    wire [255:0] mwd;
    wire [31:0] mws;
    wire [3:0] maw_id,mar_id,maw_len,mar_len;
    wire sav,srv,saw_ap,sar_ap;
    wire [27:0] saa,sra;
    wire [255:0] swd;
    wire [31:0] sws;
    wire [3:0] saw_id,sar_id,saw_len,sar_len;
    wire [31:0] cpc,cinst,cvalue;
    wire [3:0] cwe;
    wire [4:0] crd;
    wire [1:0] selftest;
    wire uart_out;
    wire busy=soc_mode ? soc.ddr_write_buffer_busy : man_busy;
    // A W beat is accepted only after AW acceptance (or on that same edge). This is a
    // literal mirror of the DUT's write_buffer_complete expression, using the bridge's
    // own busy flag plus the user-port handshakes; it decides WHEN the accepted store
    // is committed, never WHAT is committed (always the accepted request fields).
    wire backend_write_accepted=resetn && init_done && busy && wrdy && (model_aw_sent || ardy);
    wire biv=soc_mode ? soc.inst_ddr_req_valid : iv;
    wire bdv=soc_mode ? soc.data_ddr_req_valid : dv;
    wire bdw=soc_mode ? soc.data_ddr_req_write : dw;
    wire [31:0] bia=soc_mode ? soc.inst_ddr_req_addr : ia;
    wire [31:0] bda=soc_mode ? soc.data_ddr_req_addr : da;
    wire [31:0] bwd=soc_mode ? soc.data_ddr_req_wdata : wd;
    wire [3:0] bws=soc_mode ? soc.data_ddr_req_wstrb : ws;
    wire bir=soc_mode ? soc.inst_ddr_req_ready : ir;
    wire bdr=soc_mode ? soc.data_ddr_req_ready : dr;
    wire bisv=soc_mode ? soc.inst_ddr_rsp_valid : isv;
    wire bdsv=soc_mode ? soc.data_ddr_rsp_valid : dsv;
    wire [31:0] bidata=soc_mode ? soc.inst_ddr_rsp_rdata : idata;
    wire [31:0] bddata=soc_mode ? soc.data_ddr_rsp_rdata : ddata;
    wire cache_we=soc_mode ? soc.g_ddr.u_ddr_bridge.g_data_drm.u_data_data_ram.wr_en :
                             dut.g_data_drm.u_data_data_ram.wr_en;
    wire [5:0] cache_wa=soc_mode ? soc.g_ddr.u_ddr_bridge.g_data_drm.u_data_data_ram.wr_addr :
                                 dut.g_data_drm.u_data_data_ram.wr_addr;
    wire [255:0] cache_wd=soc_mode ? soc.g_ddr.u_ddr_bridge.g_data_drm.u_data_data_ram.wr_data :
                                   dut.g_data_drm.u_data_data_ram.wr_data;
    wire [31:0] cache_be=soc_mode ? soc.g_ddr.u_ddr_bridge.g_data_drm.u_data_data_ram.wr_byte_en :
                                  dut.g_data_drm.u_data_data_ram.wr_byte_en;
    assign av=soc_mode ? sav : mav;
    assign rv=soc_mode ? srv : mrv;
    assign aa=soc_mode ? saa : maa;
    assign ra=soc_mode ? sra : mra;
    assign wdata=soc_mode ? swd : mwd;
    assign wstrb=soc_mode ? sws : mws;
    assign wid=soc_mode ? saw_id : maw_id;
    assign rid=soc_mode ? sar_id : mar_id;
    assign alen=soc_mode ? saw_len : maw_len;
    assign rlen=soc_mode ? sar_len : mar_len;
    assign apw=soc_mode ? saw_ap : maw_ap;
    assign apr=soc_mode ? sar_ap : mar_ap;
    dual_sram_to_pango_ddr_bridge #(.MEM_DQ_WIDTH(32),.POSTED_WRITE_ENABLE(POSTED),
                                    .WRITE_BUFFER_TURNOVER_ENABLE(TURNOVER)) dut(
        .clk(clk),.resetn(resetn && !soc_mode),.ddr_init_done(init_done),.write_buffer_busy(man_busy),
        .inst_req_valid(iv),.inst_req_addr(ia),.inst_req_ready(ir),
        .inst_rsp_valid(isv),.inst_rsp_rdata(idata),.inst_rsp_error(ise),
        .data_req_valid(dv),.data_req_write(dw),.data_req_size(ds),.data_req_addr(da),
        .data_req_wdata(wd),.data_req_wstrb(ws),.data_req_ready(dr),
        .data_rsp_valid(dsv),.data_rsp_rdata(ddata),.data_rsp_error(dse),
        .axi_awaddr(maa),.axi_awuser_ap(maw_ap),.axi_awuser_id(maw_id),.axi_awlen(maw_len),
        .axi_awready(ardy),.axi_awvalid(mav),.axi_wdata(mwd),.axi_wstrb(mws),
        .axi_wready(wrdy),.axi_wusero_id(4'd1),.axi_wusero_last(wrdy),
        .axi_araddr(mra),.axi_aruser_ap(mar_ap),.axi_aruser_id(mar_id),.axi_arlen(mar_len),
        .axi_arready(rrdy),.axi_arvalid(mrv),.axi_rdata(rdata),.axi_rid(returned_id),
        .axi_rlast(rvalid && !bad_last),.axi_rvalid(rvalid));
    // Real SoC integration path; the SoC keeps the bridge defaults (turnover on).
    soc_top #(.RESET_PC(32'h40000000),.INST_ROM_BASE(0),.DATA_RAM_BASE(0),
        .ENABLE_DDR(1),.DDR_MEM_DQ_WIDTH(32),.DDR_POSTED_WRITE_ENABLE(POSTED),.PERF_AUTO_ARM(0)) soc(
        .clk(clk),.resetn(resetn && soc_mode),.irq_external(soc_irq),.irq_software(1'b0),.irq_timer(1'b0),
        .debug_wb_pc(cpc),.debug_wb_rf_we(cwe),.debug_wb_rf_wnum(crd),.debug_wb_rf_wdata(cvalue),.debug_inst(cinst),
        .ddr_init_done(init_done),.ddr_axi_awaddr(saa),.ddr_axi_awuser_ap(saw_ap),.ddr_axi_awuser_id(saw_id),
        .ddr_axi_awlen(saw_len),.ddr_axi_awready(ardy),.ddr_axi_awvalid(sav),.ddr_axi_wdata(swd),
        .ddr_axi_wstrb(sws),.ddr_axi_wready(wrdy),.ddr_axi_wusero_id(4'd1),.ddr_axi_wusero_last(wrdy),
        .ddr_axi_araddr(sra),.ddr_axi_aruser_ap(sar_ap),.ddr_axi_aruser_id(sar_id),.ddr_axi_arlen(sar_len),
        .ddr_axi_arready(rrdy),.ddr_axi_arvalid(srv),.ddr_axi_rdata(rdata),.ddr_axi_rid(returned_id),
        .ddr_axi_rlast(rvalid && !bad_last),.ddr_axi_rvalid(rvalid),.selftest_status(selftest),
        .uart_rx(1'b1),.uart_tx(uart_out));

    // Isolated interconnect gate checks; real SoC below tests the actual busy connection.
    reg ov=0,ow=1,order_busy=0;
    reg [31:0] oa=0;
    wire omready,omvalid,omerror;
    wire [31:0] omdata;
    wire orv,omv,ouv,odv;
    reg order_rsp=0;
    integer order_ram=0,order_mmio=0,order_uart=0,order_ddr=0;
    data_bus_interconnect #(.RAM_BASE(0),.ENABLE_DDR(1),.ENABLE_UART(1),.DDR_WRITE_ORDER_ENABLE(POSTED)) order_bus(
        .clk(clk),.resetn(resetn),.ddr_write_buffer_busy(order_busy),
        .m_req_valid(ov),.m_req_write(ow),.m_req_size(2'd2),.m_req_addr(oa),.m_req_wdata(32'h1234),
        .m_req_wstrb(4'hf),.m_req_ready(omready),.m_rsp_valid(omvalid),.m_rsp_rdata(omdata),.m_rsp_error(omerror),
        .ram_req_valid(orv),.ram_req_write(),.ram_req_size(),.ram_req_addr(),.ram_req_wdata(),.ram_req_wstrb(),
        .ram_req_ready(1'b1),.ram_rsp_valid(order_rsp),.ram_rsp_rdata(32'b0),.ram_rsp_error(1'b0),
        .mmio_req_valid(omv),.mmio_req_write(),.mmio_req_size(),.mmio_req_addr(),.mmio_req_wdata(),.mmio_req_wstrb(),
        .mmio_req_ready(1'b1),.mmio_rsp_valid(order_rsp),.mmio_rsp_rdata(32'b0),.mmio_rsp_error(1'b0),
        .uart_req_valid(ouv),.uart_req_write(),.uart_req_size(),.uart_req_addr(),.uart_req_wdata(),.uart_req_wstrb(),
        .uart_req_ready(1'b1),.uart_rsp_valid(order_rsp),.uart_rsp_rdata(32'b0),.uart_rsp_error(1'b0),
        .ddr_req_valid(odv),.ddr_req_write(),.ddr_req_size(),.ddr_req_addr(),.ddr_req_wdata(),.ddr_req_wstrb(),
        .ddr_req_ready(!order_busy),.ddr_rsp_valid(order_rsp),.ddr_rsp_rdata(32'b0),.ddr_rsp_error(1'b0));

    function automatic [31:0] word_at(input [31:0] address);
        word_at=memory[address>>5][address[4:2]*32+:32];
    endfunction

    always @(posedge clk) begin
        if (!resetn) begin
            reading<=0; writing<=0; ar_wait<=0; aw_wait<=0; r_wait<=0; w_wait<=0;
            ar_count<=0; aw_count<=0; w_count<=0;
            i_requests<=0; d_requests<=0; i_responses<=0; d_responses<=0;
            ar_blocked<=0;aw_blocked<=0;model_aw_sent<=0;
        end else begin
            if (ar_blocked && init_done && (!rv || ra!==held_ra || rid!==held_rid))
                $fatal(1,"RESULT: FAIL read address changed under backpressure");
            if (aw_blocked && init_done && (!av || aa!==held_aa || wdata!==held_wdata || wstrb!==held_wstrb))
                $fatal(1,"RESULT: FAIL write command changed under backpressure");
            ar_blocked<=init_done && rv && !rrdy;aw_blocked<=init_done && av && !ardy;
            held_ra<=ra;held_rid<=rid;held_aa<=aa;held_wdata<=wdata;held_wstrb<=wstrb;
            if (biv && bir) begin expected_ra<={bia[29:5],3'b0};expected_rid<=0;end
            if (bdv && bdr) begin
                if (bdw) begin
                    expected_aa<={bda[29:5],3'b0};
                    expected_wdata<={224'b0,bwd} << {bda[4:2],5'b0};
                    expected_wstrb<={28'b0,bws} << {bda[4:2],2'b0};
                end else begin expected_ra<={bda[29:5],3'b0};expected_rid<=1;end
            end
            if (biv && bir) i_requests<=i_requests+1;
            if (bdv && bdr) d_requests<=d_requests+1;
            if (bisv) i_responses<=i_responses+1;
            if (bdsv) d_responses<=d_responses+1;
            if (bisv && bdsv) $fatal(1,"RESULT: FAIL duplicate response owner");
            if (biv && bdv && bir && bdr) $fatal(1,"RESULT: FAIL instruction bypassed data priority");
            if (rv && !rrdy) ar_wait<=ar_wait+1;
            if (av && !ardy) aw_wait<=aw_wait+1;
            if (rv && rrdy) begin
                if (rlen!=0 || ra!==expected_ra || rid!==expected_rid || apr)
                    $fatal(1,"RESULT: FAIL read command");
                ar_count<=ar_count+1; ar_wait<=0;
                saved_ra<=ra; saved_rid<=rid;
                if (!instant_read) begin reading<=1; r_wait<=4; end
            end
            if (init_done && reading && r_wait>0) r_wait<=r_wait-1;
            if (reading && rvalid) reading<=0;
            if (av && ardy) begin
                if (alen!=0 || aa!==expected_aa || wid!=1 || apw)
                    $fatal(1,"RESULT: FAIL write command");
                aw_count<=aw_count+1; aw_wait<=0; saved_aa<=aa;
                if (!instant_write) begin writing<=1; w_wait<=w_latency; end
            end
            if (init_done && writing && w_wait>0) w_wait<=w_wait-1;
            // Mirror the DUT's aw_sent bookkeeping exactly, including precedence:
            // completion first, else the AW handshake, and a same-edge push wins.
            if (backend_write_accepted) model_aw_sent<=0;
            else if (av && ardy) model_aw_sent<=1;
            if (bdv && bdr && bdw) model_aw_sent<=0;
            if (backend_write_accepted) begin
                if (wdata!==expected_wdata || wstrb!==expected_wstrb)
                    $fatal(1,"RESULT: FAIL write lane/strobe expansion");
                for (integer byte_lane=0;byte_lane<32;byte_lane=byte_lane+1)
                    if (wstrb[byte_lane]) memory[write_addr>>3][byte_lane*8+:8]<=wdata[byte_lane*8+:8];
                w_count<=w_count+1; writing<=0;
            end
        end
    end

`include "turnover_completion_cases.svh"
    // CODEX_OBSERVATION_BEGIN
`include "turnover_completion_observe.svh"
    // CODEX_OBSERVATION_END
endmodule
