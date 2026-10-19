`timescale 1ns/1ps
// Functional Pango user-port test only; physical DDR performance is a separate run.
module tb_store_forward_x32 #(parameter integer FORWARD_ENABLE=1);
    localparam integer READ_OVERLAP=1;
    localparam integer POSTED=1, REPRO_OLD_PROGRAM=0;
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
    integer w_latency=4;
    reg bad_id=0, bad_last=0, cross_id=0, stray_read=0;
    reg reading=0, writing=0;
    reg [27:0] saved_ra=0, saved_aa=0;
    reg [3:0] saved_rid=0;
    integer aw_wait=0, ar_wait=0, r_wait=0, w_wait=0;
    integer ar_count=0, aw_count=0, w_count=0;
    integer i_requests=0, d_requests=0, i_responses=0, d_responses=0;
    integer tests=0, k, lane;
    // Existing 128 backing rows cover all I64 addresses 0x000..0xfff.
    // Keep the successful DDR timing model and transfer oracle.
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

    assign rrdy=init_done && !block_read && (force_arready || (rv && !reading && (!backpressure || ar_wait>=3)));
    assign ardy=init_done && !block_aw && av && !writing && (!backpressure || aw_wait>=2);
    assign rvalid=stray_read || (instant_read && rv && rrdy) || (reading && r_wait==0);
    assign rdata=stray_read ? 256'hbad0bad1_bad2bad3_bad4bad5_bad6bad7_bad0bad1_bad2bad3_bad4bad5_bad6bad7 :
                             memory[(instant_read ? ra : saved_ra)>>3];
    assign wrdy=init_done && !block_w && ((instant_write && av && ardy) || (writing && w_wait==0));
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
    dual_sram_to_pango_ddr_bridge #(.MEM_DQ_WIDTH(32),.POSTED_WRITE_ENABLE(POSTED),.DATA_READ_UNDER_WRITE_ENABLE(READ_OVERLAP),.DATA_STORE_FORWARD_ENABLE(FORWARD_ENABLE)) dut(
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
            ar_blocked<=0;aw_blocked<=0;
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
            if (wrdy) begin
                if (wdata!==expected_wdata || wstrb!==expected_wstrb)
                    $fatal(1,"RESULT: FAIL write lane/strobe expansion");
                for (integer byte_lane=0;byte_lane<32;byte_lane=byte_lane+1)
                    if (wstrb[byte_lane]) memory[write_addr>>3][byte_lane*8+:8]<=wdata[byte_lane*8+:8];
                w_count<=w_count+1; writing<=0;
            end
        end
    end


    integer iq=0,dq=0,group_start=0,pushes=0,completions=0,i_overlap=0,early_acks=0;
    integer fills=0,updates=0,cancelled=0,d_overlap=0,same_reads=0,word_forwards=0,collision_blocks=0,response_w_overlap=0;
    reg [2:0] pending_lane=0;
    reg d_same_line=0;
    reg [31:0] iexpect,dexpect;
    reg d_is_store=0;
    reg pending_store=0,pending_hit=0;
    reg [5:0] pending_row=0;
    reg [26:0] pending_tag=0;
    reg [63:0] oracle_valid=0;
    reg [26:0] oracle_tag[0:63];
    wire backend_write=wrdy;
    wire backend_fill=rvalid && returned_id==1 && !bad_last &&
                      ((instant_read && rv && rrdy) || reading);
    wire [27:0] fill_address=instant_read ? ra : saved_ra;
    wire expected_cache_write=resetn && init_done && (backend_fill ||
        (backend_write && pending_store && pending_hit && oracle_valid[pending_row] && oracle_tag[pending_row]==pending_tag));

    // A queued I miss observes prior accepted stores after W drains. This is a
    // reference-memory overlay, not a DUT forwarding path or DUT-derived value.
    function automatic [31:0] architectural_word(input [31:0] address);
        integer byte_lane;
        architectural_word=word_at(address);
        if(pending_store && {2'b0,expected_aa[27:3]}==address[31:5])
            for(byte_lane=0;byte_lane<4;byte_lane=byte_lane+1)
                if(expected_wstrb[address[4:2]*4+byte_lane])
                    architectural_word[byte_lane*8+:8]=expected_wdata[address[4:2]*32+byte_lane*8+:8];
    endfunction

    always @(posedge clk) begin
        if (cache_we!==expected_cache_write) $fatal(1,"RESULT: FAIL cache write completion timing");
        if (expected_cache_write) begin
            if (backend_fill) begin
                if (cache_wa!==fill_address[8:3] || cache_wd!==rdata || cache_be!==32'hffffffff)
                    $fatal(1,"RESULT: FAIL fill cache data/mask/row");
                fills=fills+1;
            end else begin
                if (cache_wa!==pending_row || cache_wd!==expected_wdata || cache_be!==expected_wstrb)
                    $fatal(1,"RESULT: FAIL buffered store cache data/mask/row");
                updates=updates+1;
            end
        end
        if (!resetn) begin
            if(pending_store) cancelled=cancelled+1;
            iq=0;dq=0;pending_store<=0;oracle_valid<=0;
        end
        else begin
            if (POSTED && busy!==pending_store) $fatal(1,"RESULT: FAIL busy differs from accepted/drained entry");
            if(pending_store && backend_write && bdv && !bdw && pending_tag==bda[31:5] &&
               oracle_valid[bda[10:5]] && oracle_tag[bda[10:5]]==bda[31:5] && !bdr) collision_blocks=collision_blocks+1;
            if (pending_store && rv) $fatal(1,"RESULT: FAIL DDR read overtook write");
            if (bisv) begin
                if (iq!=1 || bidata!==iexpect) $fatal(1,"RESULT: FAIL I response/owner");
                iq=0;
            end
            if (bdsv) begin
                if(d_same_line && backend_write) response_w_overlap=response_w_overlap+1;
                if (dq!=1 || bddata!==dexpect) $fatal(1,"RESULT: FAIL D response/owner");
                if (POSTED && d_is_store && pending_store && !backend_write) early_acks=early_acks+1;
                dq=0;
            end
            if (backend_write) begin
                if (!pending_store) $fatal(1,"RESULT: FAIL duplicate/unowned W beat");
                pending_store<=0;completions=completions+1;
            end
            if (!init_done) oracle_valid<=0;
            else if (backend_fill) begin
                oracle_valid[fill_address[8:3]]<=1;oracle_tag[fill_address[8:3]]<=fill_address>>3;
            end
            if (biv && bir) begin
                iq=iq+1;iexpect=architectural_word(bia);
                if (pending_store) i_overlap=i_overlap+1;
            end
            if (bdv && bdr) begin
                if (pending_store) begin
                    if(bdw || !READ_OVERLAP || !oracle_valid[bda[10:5]] ||
                       oracle_tag[bda[10:5]]!=bda[31:5] || (pending_tag==bda[31:5] && !FORWARD_ENABLE))
                        $fatal(1,"RESULT: FAIL unqualified D access overtook write");
                    if(!backend_write) begin
                        d_overlap=d_overlap+1;
                        if(pending_tag==bda[31:5]) begin
                            same_reads=same_reads+1;
                            if(pending_lane==bda[4:2]) word_forwards=word_forwards+1;
                        end
                    end
                    if(backend_write && pending_tag==bda[31:5]) $fatal(1,"RESULT: FAIL same-line acceptance collided with cache write");
                end
                dq=dq+1;d_is_store=bdw;dexpect=bdw ? 0 : architectural_word(bda);
                d_same_line=pending_store && !bdw && pending_tag==bda[31:5];
                if (bdw) begin
                    if (pending_store) $fatal(1,"RESULT: FAIL write entry overwritten");
                    pending_store<=1;pushes=pushes+1;
                    pending_hit<=oracle_valid[bda[10:5]] && oracle_tag[bda[10:5]]==bda[31:5];
                    pending_row<=bda[10:5];pending_tag<=bda[31:5];pending_lane<=bda[4:2];
                end
            end
            if (iq>1 || dq>1 || iq+dq>1) $fatal(1,"RESULT: FAIL front response slot overwritten");
        end
    end

    task automatic drain;
        integer waited;
        begin
            waited=0;
            while (busy || writing) begin
                @(negedge clk);waited=waited+1;
                if(waited>300) $fatal(1,"RESULT: FAIL drain timeout");
            end
        end
    endtask
    task automatic transaction(input bit port_d,input bit is_write,input [31:0] addr,
                               input [31:0] value,input [3:0] mask,input integer expected_ar);
        integer waited,old_ar;
        reg [31:0] expected;
        begin
            @(negedge clk);
            if(port_d) begin dv=1;dw=is_write;da=addr;wd=value;ws=mask;end
            else begin iv=1;ia=addr;end
            #1;waited=0;
            while(!(port_d ? dr : ir)) begin
                @(negedge clk);#1;waited=waited+1;
                if(waited>300) $fatal(1,"RESULT: FAIL request timeout");
            end
            old_ar=ar_count;expected=is_write ? 0 : architectural_word(addr);
            @(posedge clk);
            @(negedge clk);
            if(port_d) begin dv=0;dw=0;da='hfe4;wd='hdeadbeef;ws=0;end
            else begin iv=0;ia='hfd0;end
            if(POSTED && is_write && !dsv) $fatal(1,"RESULT: FAIL store not acknowledged next cycle");
            waited=0;
            while(!(port_d ? dsv : isv)) begin
                @(negedge clk);waited=waited+1;
                if(waited>300) $fatal(1,"RESULT: FAIL response timeout");
            end
            if((port_d ? ddata : idata)!==expected || (port_d ? dse : ise) || ar_count-old_ar!=expected_ar)
                $fatal(1,"RESULT: FAIL transaction value/AR addr=%h",addr);
            tests=tests+1;
            @(negedge clk);
            if(isv || dsv) $fatal(1,"RESULT: FAIL response repeated");
        end
    endtask
    task automatic fetch(input [31:0] a,input integer ar);
        transaction(0,0,a,0,0,ar);
    endtask
    task automatic load_word(input [31:0] a,input integer ar);
        transaction(1,0,a,0,0,ar);
    endtask
    task automatic store_word(input [31:0] a,input [31:0] v,input [3:0] mask);
        transaction(1,1,a,v,mask,0);
    endtask
    task automatic checkpoint(input string name,input integer count);
        drain();repeat(2) @(negedge clk);
        if(tests-group_start!=count || iq || dq || i_requests!=i_responses || d_requests!=d_responses || aw_count!=w_count)
            $fatal(1,"RESULT: FAIL checkpoint count/conservation %s tests=%0d",name,tests-group_start);
        $display("CHECK: %s PASS checks=%0d",name,count);group_start=tests;
    endtask
    task automatic soft_reset;
        @(negedge clk);resetn=0;iv=0;dv=0;
        repeat(4) @(negedge clk);
        block_aw=0;block_w=0;init_done=1;resetn=1;
        repeat(2) @(negedge clk);
        if(busy || av || rv || isv || dsv || aw_count || w_count) $fatal(1,"RESULT: FAIL ghost after reset");
    endtask

    always @(posedge clk) begin
        if(!resetn) begin order_rsp<=0;order_ram<=0;order_mmio<=0;order_uart<=0;order_ddr<=0;end
        else begin
            order_rsp<=orv || omv || ouv || odv && !order_busy;
            if(orv) order_ram<=order_ram+1;
            if(omv) order_mmio<=order_mmio+1;
            if(ouv) order_uart<=order_uart+1;
            if(odv && !order_busy) order_ddr<=order_ddr+1;
        end
    end
    task automatic order_case(input [31:0] address,input integer target);
        integer old_total;
        @(negedge clk);oa=address;ov=1;order_busy=1;
        repeat(3) begin
            #1;if(omready || orv || omv || ouv || (target!=3 && odv))
                $fatal(1,"RESULT: FAIL non-DDR side effect before drain");
            if(target==3 && !odv) $fatal(1,"RESULT: FAIL DDR valid incorrectly suppressed");
            @(negedge clk);
        end
        tests=tests+1;
        old_total=order_ram+order_mmio+order_uart+order_ddr;
        order_busy=0;#1;
        if(!omready) $fatal(1,"RESULT: FAIL interconnect drain recovery");
        @(posedge clk);
        @(negedge clk);ov=0;
        if(!omvalid || omerror!==(target==4)) $fatal(1,"RESULT: FAIL interconnect response");
        if(order_ram+order_mmio+order_uart+order_ddr-old_total!=(target==4 ? 0 : 1))
            $fatal(1,"RESULT: FAIL interconnect side effect count");
        tests=tests+1;
        @(negedge clk);
        if(omvalid) $fatal(1,"RESULT: FAIL interconnect response repeated");
    endtask

    // Small independent retirement interpreter for the explicit SoC integration program.
    reg [31:0] golden_regs[0:31],golden_mem[0:1023];
    reg [31:0] golden_pc=32'h40000000,golden_mepc=0,golden_mtvec=0;
    reg cpu_done=0,irq_schedule=0,irq_sent=0,irq_seen=0;
    integer cpu_events=0,irq_count=0,fence_wait=0,irq_wait=0,stop_wait=0,start_writes=0,stop_writes=0,pass_writes=0,run_writes=0;
    string cpu_image;
    function automatic [31:0] sext(input [31:0] v,input integer bits);
        sext=$signed(v << (32-bits)) >>> (32-bits);
    endfunction
    always @(negedge clk) begin
        if(soc_mode && irq_schedule && !irq_sent) begin soc_irq=1;irq_sent=1;end
        if(irq_seen) soc_irq=0;
    end
    always @(posedge clk) begin : real_soc_observe
        reg [31:0] instruction,next_pc,expected_value,address,imm;
        integer opcode,rdn,r1,r2,funct3;
        bit expected_we;
        if(resetn && soc_mode && !cpu_done) begin
            if(bdv && bdr && bdw && bda=='h800 && !irq_sent) irq_schedule=1;
            if(soc.u_cpu.irq_candidate && pending_store) irq_wait=irq_wait+1;
            if(soc.u_cpu.inst_fence && soc.u_cpu.if_id_valid && pending_store) fence_wait=fence_wait+1;
            if(soc.data_req_valid && soc.data_req_addr=='h10000108 && pending_store) begin
                stop_wait=stop_wait+1;
                if(soc.data_req_ready || soc.mmio_req_valid) $fatal(1,"RESULT: FAIL pending PERF STOP accepted before drain");
            end
            if(soc.u_cpu.serial_issue && pending_store) $fatal(1,"RESULT: FAIL serial instruction bypassed entry drain");
            if(soc.mmio_req_valid && soc.mmio_req_ready) begin
                if(pending_store) $fatal(1,"RESULT: FAIL SoC MMIO/perf stop bypassed entry drain");
                if(soc.mmio_req_write && soc.mmio_req_addr=='h108) begin
                    if(soc.mmio_req_wdata==3 && w_count==0) start_writes=start_writes+1;
                    else if(soc.mmio_req_wdata==4 && w_count==71) stop_writes=stop_writes+1;
                    else $fatal(1,"RESULT: FAIL PERF CTRL semantics/STOP ordering");
                end
                if(soc.mmio_req_write && soc.mmio_req_addr=='h10) begin
                    if(soc.mmio_req_wdata==1 && selftest==0) run_writes=run_writes+1;
                    else if(soc.mmio_req_wdata==2 && (selftest==1 || REPRO_OLD_PROGRAM)) pass_writes=pass_writes+1;
                    else $fatal(1,"RESULT: FAIL TEST_STATUS RUN/PASS contract");
                end
            end
            if(soc.u_cpu.sync_trap_event) begin
                $display("DIAG_TRAP pc=%h inst=%h cause=%0d tval=%h cpu_events=%0d AW=%0d W=%0d selftest=%0d busy=%0d flow=%0d",
                    soc.u_cpu.mem_wb_pc,soc.u_cpu.mem_wb_inst,soc.u_cpu.wb_trap_cause,soc.u_cpu.wb_trap_tval,
                    cpu_events,aw_count,w_count,selftest,busy,soc.u_cpu.flow_state);
                if(REPRO_OLD_PROGRAM && soc.u_cpu.mem_wb_pc===32'h4000007c &&
                   soc.u_cpu.mem_wb_inst===32'h00b52823 && soc.u_cpu.wb_trap_cause===5'd7 &&
                   soc.u_cpu.wb_trap_tval===32'h10000010 && cpu_events==412 &&
                   run_writes==0 && pass_writes==1 && selftest==0 && irq_count==1 &&
                   !busy && aw_count==67 && w_count==67 && soc.u_simple_mmio.g_perf.u_perf.state==3 &&
                   soc.u_simple_mmio.g_perf.u_perf.count[12]==67) begin
                    $display("CHECK: original_missing_RUN_store_fault PASS pc=4000007c cause=7 tval=10000010");
                    $display("RESULT: PASS write_buffer_old_program_diagnosis events=412 original_functional_status=FAIL");
                    $finish;
                end
                $fatal(1,"RESULT: FAIL unexpected synchronous CPU trap");
            end
            if(soc.u_cpu.irq_take) begin
                if(pending_store || !irq_sent || irq_count || soc.u_cpu.irq_cause!=11 ||
                   soc.u_cpu.arch_next_pc!==golden_pc || soc.u_cpu.csr_trap_target!==golden_mtvec)
                    $fatal(1,"RESULT: FAIL IRQ drain/cause/precise PC");
                golden_mepc=golden_pc;golden_pc=golden_mtvec;irq_count=irq_count+1;irq_seen=1;
                cpu_events=cpu_events+1;
            end else if(soc.u_cpu.normal_retire || soc.u_cpu.mret_commit) begin
                instruction=golden_mem[(golden_pc-32'h40000000)/4];
                if(cpc!==golden_pc || cinst!==instruction) $fatal(1,"RESULT: FAIL CPU PC/instruction pc=%h expected=%h",cpc,golden_pc);
                opcode=instruction[6:0];rdn=instruction[11:7];r1=instruction[19:15];r2=instruction[24:20];funct3=instruction[14:12];
                next_pc=golden_pc+4;expected_value=0;expected_we=0;
                case(opcode)
                    'h37:begin expected_value={instruction[31:12],12'b0};expected_we=rdn!=0;end
                    'h13:begin expected_value=golden_regs[r1]+sext(instruction>>20,12);expected_we=rdn!=0;end
                    'h33:begin expected_value=golden_regs[r1]+golden_regs[r2];expected_we=rdn!=0;end
                    'h03:begin
                        address=golden_regs[r1]+sext(instruction>>20,12);
                        expected_value=golden_mem[(address-'h40000000)/4] >> (address[1:0]*8);
                        case(funct3)
                            0:expected_value=sext(expected_value,8);
                            1:expected_value=sext(expected_value,16);
                            2: ;
                            4:expected_value=expected_value & 'hff;
                            5:expected_value=expected_value & 'hffff;
                            default:$fatal(1,"RESULT: FAIL unsupported golden load size");
                        endcase
                        expected_we=rdn!=0;
                    end
                    'h23:begin
                        imm=sext({20'b0,instruction[31:25],instruction[11:7]},12);address=golden_regs[r1]+imm;
                        if(address[31:12]=='h40000) begin
                            case(funct3)
                                0:golden_mem[(address-'h40000000)/4][address[1:0]*8+:8]=golden_regs[r2][7:0];
                                1:golden_mem[(address-'h40000000)/4][address[1:0]*8+:16]=golden_regs[r2][15:0];
                                2:golden_mem[(address-'h40000000)/4]=golden_regs[r2];
                                default:$fatal(1,"RESULT: FAIL unsupported golden store size");
                            endcase
                        end
                        else if(address!='h10000108 && address!='h10000010) $fatal(1,"RESULT: FAIL unsupported golden store");
                    end
                    'h63:begin
                        imm=sext({19'b0,instruction[31],instruction[7],instruction[30:25],instruction[11:8],1'b0},13);
                        if($signed(golden_regs[r1])<$signed(golden_regs[r2])) next_pc=golden_pc+imm;
                    end
                    'h0f:if(instruction[14:12]!=0) $fatal(1,"RESULT: FAIL unsupported FENCE.I");
                    'h73:begin
                        if(instruction=='h30200073) next_pc=golden_mepc;
                        else if(instruction[31:20]=='h305) golden_mtvec=golden_regs[r1];
                        else if(instruction[31:20]!='h304 && instruction[31:20]!='h300)
                            $fatal(1,"RESULT: FAIL unexpected golden CSR");
                    end
                    default:$fatal(1,"RESULT: FAIL unsupported golden opcode");
                endcase
                if((expected_we && (cwe!=15 || crd!=rdn || cvalue!==expected_value)) || (!expected_we && cwe!=0))
                    $fatal(1,"RESULT: FAIL CPU register writeback pc=%h",cpc);
                if(expected_we) golden_regs[rdn]=expected_value;
                golden_pc=next_pc;cpu_events=cpu_events+1;
                if(opcode=='h23 && address=='h10000010 && golden_regs[r2]==2) cpu_done=1;
            end
        end
    end

    task automatic blocked_read(input [31:0] address,input integer expected_ar);
        integer before_ar,waited;
        reg [31:0] expected;
        @(negedge clk);dv=1;dw=0;da=address;before_ar=ar_count;force_arready=1;
        repeat(3) begin
            #1;if(dr || dsv || rv || !busy) $fatal(1,"RESULT: FAIL ordered read escaped pending write");
            @(negedge clk);
        end
        block_aw=0;block_w=0;waited=0;#1;
        while(!dr) begin @(negedge clk);#1;waited=waited+1;if(waited>300) $fatal(1,"RESULT: FAIL ordered read timeout");end
        if(busy) $fatal(1,"RESULT: FAIL ordered read accepted before drain");
        expected=word_at(address);
        @(posedge clk);@(negedge clk);dv=0;da='hfe4;waited=0;
        while(!dsv) begin @(negedge clk);waited=waited+1;if(waited>300) $fatal(1,"RESULT: FAIL ordered response timeout");end
        if(ddata!==expected || dse || ar_count-before_ar!=expected_ar) $fatal(1,"RESULT: FAIL ordered read value/AR");
        tests=tests+1;@(negedge clk);force_arready=0;
        if(dsv) $fatal(1,"RESULT: FAIL ordered response duplicated");
    endtask
    task automatic blocked_store(input [31:0] address,input [31:0] value);
        integer waited;
        @(negedge clk);dv=1;dw=1;da=address;wd=value;ws=15;
        repeat(3) begin #1;if(dr || !busy) $fatal(1,"RESULT: FAIL full write entry overwritten");@(negedge clk);end
        block_aw=0;block_w=0;waited=0;#1;
        while(!dr) begin @(negedge clk);#1;waited=waited+1;if(waited>300) $fatal(1,"RESULT: FAIL second store timeout");end
        @(posedge clk);@(negedge clk);dv=0;dw=0;da='hfe4;wd='hdeadbeef;ws=0;
        if(!dsv || ddata!==0 || dse) $fatal(1,"RESULT: FAIL second posted store ACK");
        tests=tests+1;@(negedge clk);if(dsv) $fatal(1,"RESULT: FAIL second store ACK repeated");
    endtask
    task automatic overlapping_read(input [31:0] address);
        integer before_w;
        before_w=w_count;load_word(address,0);
        if(!busy || w_count!=before_w) $fatal(1,"RESULT: FAIL read did not overlap blocked W");
    endtask

    integer base_pushes,base_completions,base_cancelled,base_fills,base_updates,base_d_overlap;
    integer base_same,base_word,base_collision,base_rsp_w;
    task automatic forward_read(input [31:0] address);
        integer old_w;
        old_w=w_count;load_word(address,0);
        if(!busy || w_count!=old_w) $fatal(1,"RESULT: FAIL forwarded read did not finish before W");
    endtask
    task automatic completion_case(input integer phase,input [3:0] mask);
        integer waited,old_w;
        reg [31:0] expected;
        block_w=1;store_word('h200,'h87654321+mask,mask);
        while(!writing || w_wait!=0) @(negedge clk);
        dv=1;dw=0;da='h200;old_w=w_count;expected=architectural_word('h200);waited=0;#1;
        while(!dr) begin @(negedge clk);#1;waited=waited+1;if(waited>300) $fatal(1,"RESULT: FAIL boundary qualification timeout");end
        if(phase==0) begin
            block_w=0;#1;
            if(dr || !wrdy || !busy) $fatal(1,"RESULT: FAIL same-line read accepted on W completion edge");
            tests=tests+1;
            @(posedge clk);@(negedge clk);#1;
            if(busy || !dr || w_count!=old_w+1) $fatal(1,"RESULT: FAIL collision guard did not recover");
            @(posedge clk);@(negedge clk);dv=0;da='hfe4;
            if(!dsv || ddata!==expected || dse) $fatal(1,"RESULT: FAIL read after collision guard");
            tests=tests+1;@(negedge clk);
        end else begin
            @(posedge clk);@(negedge clk);dv=0;da='h200;block_w=0;#1;
            if(!dsv || ddata!==expected || dse || !wrdy) $fatal(1,"RESULT: FAIL latched forward response at W completion");
            tests=tests+1;@(posedge clk);@(negedge clk);
            if(busy || dsv || w_count!=old_w+1) $fatal(1,"RESULT: FAIL forward response/W double completion");
            load_word('h200,0);
        end
    endtask
    task automatic manual_groups;
        integer row,slot,mask,q;
        reg [31:0] target,value;
        reg [3:0] byte_mask;
        for(k=0;k<128;k=k+1) for(lane=0;lane<8;lane=lane+1) memory[k][lane*32+:32]='h81000000+k*32+lane;
        repeat(6) @(negedge clk);resetn=1;init_done=1;
        fetch('he00,1);load_word('h200,1);load_word('h220,1);
        if(!FORWARD_ENABLE) begin
            block_aw=1;store_word('h200,'h12345678,15);forward_read('h220);
            blocked_read('h200,0);load_word('h200,0);fetch('he00,0);
            checkpoint("disabled_store_forward_control",8);
            if(same_reads || word_forwards) $fatal(1,"RESULT: FAIL disabled same-line forwarding");
            $display("RESULT: PASS store_forward_control tests=8");$finish;
        end
        block_aw=1;store_word('h200,'h12345678,15);
        @(negedge clk);dv=1;dw=0;da='h200;#1;
        while(!dr) begin @(negedge clk);#1;end
        @(posedge clk);@(negedge clk);dv=0;da='hfe4;iv=1;ia='he00;#1;
        if(!dsv || ddata!=='h12345678 || !ir) $fatal(1,"RESULT: FAIL forward response/I turnover");
        tests=tests+1;@(posedge clk);@(negedge clk);iv=0;
        if(!isv || idata!==word_at('he00)) $fatal(1,"RESULT: FAIL I response after forwarding");
        tests=tests+1;@(negedge clk);forward_read('h220);
        block_aw=0;drain();load_word('h200,0);
        checkpoint("forward_response_owner_clear",8);

        for(slot=0;slot<8;slot=slot+1) for(mask=0;mask<16;mask=mask+1) begin
            block_aw=(mask%2)==0;block_w=!block_aw;
            store_word('h200+slot*4,'h76543210+slot*16+mask,mask[3:0]);
            for(q=0;q<8;q=q+1) forward_read('h200+q*4);
            block_aw=0;block_w=0;drain();load_word('h200+slot*4,0);
        end
        checkpoint("all_write_read_words_byte_masks",1280);

        for(row=0;row<64;row=row+1) begin
            load_word(row*32,(row==16 || row==17) ? 0 : 1);
            target=row*32+(row%8)*4;block_aw=1;
            store_word(target,'h89abcdef+row,(row%16));
            forward_read(target);forward_read(row*32+((row+1)%8)*4);
            block_aw=0;drain();load_word(target,0);
        end
        checkpoint("all_line_indices_forward",320);

        for(q=0;q<6;q=q+1) begin
            target='h200+q*4;block_w=1;
            if(q<4) begin ds=0;byte_mask=1<<q;value='h80<<(q*8);target=target+q;end
            else begin ds=1;byte_mask=q==4 ? 3 : 12;value=q==4 ? 'h0000ff80 : 'hff800000;target=target+(q==4 ? 0 : 2);end
            store_word(target,value,byte_mask);ds=2;
            forward_read(target);forward_read('h200+((q+1)%8)*4);
            block_w=0;drain();load_word(target,0);
        end
        checkpoint("unaligned_byte_half_packets",24);

        block_aw=1;store_word('h800,'h11111111,15);forward_read(0);blocked_read('h800,1);
        // The preceding loop already warmed row zero: no separate preload here.
        block_aw=1;store_word('h800,'h22222222,15);forward_read('h800);forward_read('h804);forward_read('h200);blocked_read(0,1);
        block_aw=1;store_word('h200,'h33333333,15);blocked_store('h220,'h44444444);
        load_word('h200,0);drain();load_word('h220,0);
        checkpoint("miss_alias_and_store_order",12);

        for(q=0;q<2;q=q+1) for(mask=0;mask<16;mask=mask+1) completion_case(q,mask[3:0]);
        checkpoint("W_accept_and_response_boundaries",96);

        block_aw=1;store_word('h200,'hdead0001,15);
        @(negedge clk);dv=1;dw=0;da='h200;#1;while(!dr) begin @(negedge clk);#1;end
        @(posedge clk);@(negedge clk);dv=0;
        if(!dsv || ddata!=='hdead0001) $fatal(1,"RESULT: FAIL reset forward response setup");
        tests=tests+1;resetn=0;soft_reset();load_word('h200,1);load_word('h220,1);
        block_w=1;store_word('h200,'hdead0002,5);
        while(!writing) @(negedge clk);
        dv=1;dw=0;da='h200;#1;while(!dr) begin @(negedge clk);#1;end
        tests=tests+1;init_done=0;
        repeat(3) begin #1;if(dr || ir || av || wrdy) $fatal(1,"RESULT: FAIL init loss accepted forward read");@(negedge clk);end
        init_done=1;#1;if(dr || !busy) $fatal(1,"RESULT: FAIL stale forward qualification after init loss");tests=tests+1;
        block_w=0;
        begin integer before_ar;reg [31:0] expected;before_ar=ar_count;
            while(!dr) begin @(negedge clk);#1;end
            if(busy) $fatal(1,"RESULT: FAIL invalidated same-line read bypassed W");
            expected=word_at('h200);@(posedge clk);@(negedge clk);dv=0;da='hfe4;
            while(!dsv) @(negedge clk);
            if(ddata!==expected || dse || ar_count-before_ar!=1) $fatal(1,"RESULT: FAIL init forward clear/readback");
            tests=tests+1;@(negedge clk);
        end
        load_word('h220,1);
        checkpoint("reset_init_forward_metadata_clear",9);
        if(same_reads!=1184 || word_forwards!=217 || collision_blocks!=16 || response_w_overlap!=16 ||
           pushes!=completions+cancelled || cancelled!=1) $fatal(1,"RESULT: FAIL manual forward coverage/conservation");
        base_pushes=pushes;base_completions=completions;base_cancelled=cancelled;base_fills=fills;base_updates=updates;base_d_overlap=d_overlap;
        base_same=same_reads;base_word=word_forwards;base_collision=collision_blocks;base_rsp_w=response_w_overlap;
    endtask

    initial begin : suite
        manual_groups();
        @(negedge clk);resetn=0;init_done=1;soc_mode=1;iv=0;dv=0;w_latency=40;
        if(!$value$plusargs("CPU_IMAGE=%s",cpu_image)) $fatal(1,"RESULT: FAIL missing CPU image");
        for(k=0;k<1024;k=k+1) golden_mem[k]=0;
        for(k=0;k<32;k=k+1) golden_regs[k]=0;
        $readmemh(cpu_image,golden_mem);
        for(k=0;k<128;k=k+1) for(lane=0;lane<8;lane=lane+1) memory[k][lane*32+:32]=golden_mem[k*8+lane];
        repeat(6) @(negedge clk);resetn=1;
        while(!cpu_done) @(negedge clk);
        repeat(12) @(negedge clk);
        if(cpu_events!=489 || irq_count!=1 || !irq_wait || !fence_wait || !stop_wait || start_writes!=1 || stop_writes!=1 || pass_writes!=1 || run_writes!=1 ||
           busy || aw_count!=71 || w_count!=71 || golden_regs[20]!=1 || selftest!=2 ||
           memory[64][31:0]!=64 || memory[64][63:32]!=2080 || memory[66][31:0]!=1 || memory[66][63:32]!=1)
            $fatal(1,"RESULT: FAIL real SoC/FENCE/IRQ/MMIO totals events=%0d irq=%0d irq_wait=%0d fence_wait=%0d AW=%0d W=%0d",cpu_events,irq_count,irq_wait,fence_wait,aw_count,w_count);
        if(soc.u_simple_mmio.g_perf.u_perf.state!=3 || soc.u_simple_mmio.g_perf.u_perf.count[12]!=71)
            $fatal(1,"RESULT: FAIL PERF frozen bank missed buffered AW commands");
        tests=tests+cpu_events;
        if(tests-group_start!=489) $fatal(1,"RESULT: FAIL SoC group count");
        $display("CHECK: real_soc_store_forward_typed_loads PASS checks=489");
        if(REPRO_OLD_PROGRAM || tests!=2238 || early_acks==0 || i_overlap==0 || pushes-base_pushes!=71 || completions-base_completions!=71 || cancelled-base_cancelled!=0 ||
           fills-base_fills!=2 || updates-base_updates!=69 || d_overlap-base_d_overlap<=0 || same_reads-base_same<=0 || word_forwards-base_word<=0) $fatal(1,"RESULT: FAIL write-buffer coverage/conservation");
        $display("RESULT: PASS store_forward_x32 tests=%0d cpu_events=%0d IRQ=%0d early_acks=%0d I_OVERLAP=%0d FENCE_WAIT=%0d IRQ_WAIT=%0d STOP_WAIT=%0d fills=%0d updates=%0d D_OVERLAP=%0d SOC_D_OVERLAP=%0d SAME_LINE=%0d WORD_FORWARD=%0d SOC_SAME_LINE=%0d SOC_WORD_FORWARD=%0d COLLISION_BLOCKS=%0d RSP_W_OVERLAP=%0d",
                 tests,cpu_events,irq_count,early_acks,i_overlap,fence_wait,irq_wait,stop_wait,fills-base_fills,updates-base_updates,d_overlap,d_overlap-base_d_overlap,same_reads,word_forwards,same_reads-base_same,word_forwards-base_word,collision_blocks,response_w_overlap);
        $finish;
    end
    initial begin #5000000;$fatal(1,"RESULT: FAIL write buffer watchdog");end

    integer trace_fd;
    string trace_path;
    initial begin
        if(!$value$plusargs("EVENT_LOG=%s",trace_path)) $fatal(1,"RESULT: FAIL missing event log");
        trace_fd=$fopen(trace_path,"w");
        if(!trace_fd) $fatal(1,"RESULT: FAIL cannot open event log");
    end
    always @(negedge clk) if(resetn && soc_mode) begin
        if(soc.u_cpu.normal_retire || soc.u_cpu.mret_commit || soc.u_cpu.irq_take || soc.u_cpu.sync_trap_event) begin
            $fdisplay(trace_fd,"EV t=%0t pc=%h inst=%h we=%h rd=%0d data=%h trap=%0d cause=%0d tval=%h irq=%0d next=%h busy=%0d flow=%0d AW=%0d W=%0d",
                $time,cpc,cinst,cwe,crd,cvalue,soc.u_cpu.sync_trap_event,soc.u_cpu.wb_trap_cause,
                soc.u_cpu.wb_trap_tval,soc.u_cpu.irq_take,soc.u_cpu.arch_next_pc,busy,soc.u_cpu.flow_state,aw_count,w_count);
            $fflush(trace_fd);
        end
        if((biv && bir)||(bdv && bdr)||bisv||bdsv||(av && ardy)||wrdy||(rv && rrdy)) begin
            $fdisplay(trace_fd,"BUS t=%0t I=%0d ia=%h D=%0d da=%h write=%0d wd=%h strb=%h Irsp=%0d idata=%h Drsp=%0d ddata=%h AR=%0d ra=%h AW=%0d aa=%h W=%0d busy=%0d",
                $time,biv&&bir,bia,bdv&&bdr,bda,bdw,bwd,bws,bisv,bidata,bdsv,bddata,rv&&rrdy,ra,av&&ardy,aa,wrdy,busy);
            $fflush(trace_fd);
        end
    end

endmodule
