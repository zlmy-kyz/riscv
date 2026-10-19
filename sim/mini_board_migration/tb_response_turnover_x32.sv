`timescale 1ns/1ps
// Functional Pango user-port test only; physical DDR performance is a separate run.
module tb_response_turnover_x32;
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

    assign rrdy=rv && !reading && (!backpressure || ar_wait>=3);
    assign ardy=av && !writing && (!backpressure || aw_wait>=2);
    assign rvalid=stray_read || (instant_read && rv && rrdy) || (reading && r_wait==0);
    assign rdata=stray_read ? 256'hbad0bad1_bad2bad3_bad4bad5_bad6bad7_bad0bad1_bad2bad3_bad4bad5_bad6bad7 :
                             memory[(instant_read ? ra : saved_ra)>>3];
    assign wrdy=(instant_write && av && ardy) || (writing && w_wait==0);
    wire [27:0] write_addr=instant_write ? aa : saved_aa;
    wire [3:0] model_id=instant_read ? rid : saved_rid;
    wire [3:0] returned_id=bad_id ? 4'hf : (cross_id ? (model_id ^ 4'd1) : model_id);

    reg cpu_mode=0,cpu_allow=0;
    wire civ,cdv,cdw;
    wire [31:0] cia,cda,cwd;
    wire [3:0] cws;
    wire [1:0] cds;
    wire [31:0] cpc,cinst,cvalue;
    wire [3:0] cwe;
    wire [4:0] crd;
    wire biv=cpu_mode ? (cpu_allow && civ) : iv;
    wire bdv=cpu_mode ? (cpu_allow && cdv) : dv;
    wire bdw=cpu_mode ? cdw : dw;
    wire [31:0] bia=cpu_mode ? cia-32'h40000000 : ia;
    wire [31:0] bda=cpu_mode ? cda-32'h40000000 : da;
    wire [31:0] bwd=cpu_mode ? cwd : wd;
    wire [3:0] bws=cpu_mode ? cws : ws;
    wire [1:0] bds=cpu_mode ? cds : ds;
    mycpu_sync #(.RESET_PC(32'h40000000)) cpu(
        .clk(clk),.resetn(resetn && cpu_mode),
        .irq_external(1'b0),.irq_software(1'b0),.irq_timer(1'b0),
        .inst_req_valid(civ),.inst_req_addr(cia),.inst_req_ready(cpu_allow && ir),
        .inst_rsp_valid(isv),.inst_rsp_rdata(idata),.inst_rsp_error(ise),
        .data_req_valid(cdv),.data_req_write(cdw),.data_req_size(cds),
        .data_req_addr(cda),.data_req_wdata(cwd),.data_req_wstrb(cws),
        .data_req_ready(cpu_allow && dr),.data_rsp_valid(dsv),
        .data_rsp_rdata(ddata),.data_rsp_error(dse),
        .debug_wb_pc(cpc),.debug_wb_rf_we(cwe),.debug_wb_rf_wnum(crd),
        .debug_wb_rf_wdata(cvalue),.debug_inst(cinst),
        .perf_events(),.perf_branch_target(),.perf_fetch_pc());

    dual_sram_to_pango_ddr_bridge #(.MEM_DQ_WIDTH(32), .INST_LINE_BUFFER_ENABLE(ENABLE)) dut(
        .clk(clk),.resetn(resetn),.ddr_init_done(init_done),
        .inst_req_valid(biv),.inst_req_addr(bia),.inst_req_ready(ir),
        .inst_rsp_valid(isv),.inst_rsp_rdata(idata),.inst_rsp_error(ise),
        .data_req_valid(bdv),.data_req_write(bdw),.data_req_size(bds),
        .data_req_addr(bda),.data_req_wdata(bwd),.data_req_wstrb(bws),
        .data_req_ready(dr),.data_rsp_valid(dsv),.data_rsp_rdata(ddata),.data_rsp_error(dse),
        .axi_awaddr(aa),.axi_awuser_ap(apw),.axi_awuser_id(wid),.axi_awlen(alen),
        .axi_awready(ardy),.axi_awvalid(av),.axi_wdata(wdata),.axi_wstrb(wstrb),
        .axi_wready(wrdy),.axi_wusero_id(4'd1),.axi_wusero_last(wrdy),
        .axi_araddr(ra),.axi_aruser_ap(apr),.axi_aruser_id(rid),.axi_arlen(rlen),
        .axi_arready(rrdy),.axi_arvalid(rv),.axi_rdata(rdata),
        .axi_rid(returned_id),.axi_rlast(rvalid && !bad_last),.axi_rvalid(rvalid));

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
            if (ar_blocked && (!rv || ra!==held_ra || rid!==held_rid))
                $fatal(1,"RESULT: FAIL read address changed under backpressure");
            if (aw_blocked && (!av || aa!==held_aa || wdata!==held_wdata || wstrb!==held_wstrb))
                $fatal(1,"RESULT: FAIL write command changed under backpressure");
            ar_blocked<=rv && !rrdy;aw_blocked<=av && !ardy;
            held_ra<=ra;held_rid<=rid;held_aa<=aa;held_wdata<=wdata;held_wstrb<=wstrb;
            if (biv && ir) begin expected_ra<={bia[29:5],3'b0};expected_rid<=0;end
            if (bdv && dr) begin
                if (bdw) begin
                    expected_aa<={bda[29:5],3'b0};
                    expected_wdata<={224'b0,bwd} << {bda[4:2],5'b0};
                    expected_wstrb<={28'b0,bws} << {bda[4:2],2'b0};
                end else begin expected_ra<={bda[29:5],3'b0};expected_rid<=1;end
            end
            if (biv && ir) i_requests<=i_requests+1;
            if (bdv && dr) d_requests<=d_requests+1;
            if (isv) i_responses<=i_responses+1;
            if (dsv) d_responses<=d_responses+1;
            if (isv && dsv) $fatal(1,"RESULT: FAIL duplicate response owner");
            if (biv && bdv && ir) $fatal(1,"RESULT: FAIL instruction bypassed data priority");
            if (rv && !rrdy) ar_wait<=ar_wait+1;
            if (av && !ardy) aw_wait<=aw_wait+1;
            if (rv && rrdy) begin
                if (rlen!=0 || ra!==expected_ra || rid!==expected_rid || apr)
                    $fatal(1,"RESULT: FAIL read command");
                ar_count<=ar_count+1; ar_wait<=0;
                saved_ra<=ra; saved_rid<=rid;
                if (!instant_read) begin reading<=1; r_wait<=4; end
            end
            if (reading && r_wait>0) r_wait<=r_wait-1;
            if (reading && rvalid) reading<=0;
            if (av && ardy) begin
                if (alen!=0 || aa!==expected_aa || wid!=1 || apw)
                    $fatal(1,"RESULT: FAIL write command");
                aw_count<=aw_count+1; aw_wait<=0; saved_aa<=aa;
                if (!instant_write) begin writing<=1; w_wait<=4; end
            end
            if (writing && w_wait>0) w_wait<=w_wait-1;
            if (wrdy) begin
                if (wdata!==expected_wdata || wstrb!==expected_wstrb)
                    $fatal(1,"RESULT: FAIL write lane/strobe expansion");
                for (integer byte_lane=0;byte_lane<32;byte_lane=byte_lane+1)
                    if (wstrb[byte_lane]) memory[write_addr>>3][byte_lane*8+:8]<=wdata[byte_lane*8+:8];
                w_count<=w_count+1; writing<=0;
            end
        end
    end

    task automatic transfer(input bit data_port, input bit write_request,
                            input [31:0] address, input [31:0] value, input [3:0] strobe,
                            input [31:0] expected, input integer cached_ar);
        integer old_ar, old_aw, waited, expected_ar;
        begin
            @(negedge clk);
            old_ar=ar_count; old_aw=aw_count;
            expected_ar=write_request ? 0 : ((data_port ? !D_ENABLED : !ENABLE) ? 1 : cached_ar);
            if (data_port) begin dv=1;dw=write_request;da=address;wd=value;ws=strobe;end
            else begin iv=1;ia=address;end
            @(posedge clk);
            while (!(data_port ? dr : ir)) @(posedge clk);
            @(negedge clk);
            if (data_port) begin dv=0;da='hfe4;wd=32'hdeadbeef;ws=0;dw=0;end
            else begin iv=0;ia='hfd0;end
            waited=0;
            while (!(data_port ? dsv : isv)) begin
                @(negedge clk); waited=waited+1;
                if (waited>100) $fatal(1,"RESULT: FAIL response timeout");
            end
            if (!write_request && (data_port ? D_ENABLED : ENABLE) && cached_ar==0 && waited!=0)
                $fatal(1,"RESULT: FAIL hit did not respond on next cycle");
            if ((data_port ? ddata : idata)!==expected || (data_port ? dse : ise))
                $fatal(1,"RESULT: FAIL wrong response data address=%h",address);
            if (ar_count-old_ar!=expected_ar || aw_count-old_aw!=integer'(write_request))
                $fatal(1,"RESULT: FAIL command count address=%h AR=%0d expected=%0d",
                       address,ar_count-old_ar,expected_ar);
            @(negedge clk);
            if (isv || dsv) $fatal(1,"RESULT: FAIL response repeated");
            tests=tests+1;
        end
    endtask


    task automatic fetch(input [31:0] address,input integer cached_ar);
        transfer(0,0,address,0,0,word_at(address),cached_ar);
    endtask
    task automatic load_word(input [31:0] address,input integer cached_ar);
        transfer(1,0,address,0,0,word_at(address),cached_ar);
    endtask
    task automatic store_word(input [31:0] address,input [31:0] value,input [3:0] strobe);
        transfer(1,1,address,value,strobe,0,0);
    endtask
    task automatic conservation;
        repeat(2) @(negedge clk);
        if (i_requests!=i_responses || d_requests!=d_responses || aw_count!=w_count)
            $fatal(1,"RESULT: FAIL request/response/beat conservation");
    endtask


    task automatic cold;
        begin
            conservation();
            @(negedge clk);init_done=0;
            repeat(2) @(negedge clk);
            if (ir || dr) $fatal(1,"RESULT: FAIL ready without DDR initialization");
            init_done=1;
        end
    endtask


`include "response_turnover_cases.svh"
endmodule
