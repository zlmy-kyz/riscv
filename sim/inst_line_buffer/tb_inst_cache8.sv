`timescale 1ns/1ps
// Functional Pango user-port test only; physical DDR performance is a separate run.
module tb_inst_cache8;
    // Oracle capacity only; both frozen/current RTL retain the single-line D buffer.
    parameter integer LINES = 8;
    parameter integer D_ENABLED = 1;
    parameter integer ENABLE = 1;
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
    wire [127:0] wdata, rdata;
    wire [15:0] wstrb;
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
    reg [127:0] memory[0:63];
    reg [127:0] expected_wdata=0;
    reg [15:0] expected_wstrb=0;
    reg [27:0] expected_aa=0, expected_ra=0;
    reg [3:0] expected_rid=0;
    reg ar_blocked=0, aw_blocked=0;
    reg [27:0] held_ra=0, held_aa=0;
    reg [127:0] held_wdata=0;
    reg [15:0] held_wstrb=0;
    reg [3:0] held_rid=0;

    assign rrdy=rv && !reading && (!backpressure || ar_wait>=3);
    assign ardy=av && !writing && (!backpressure || aw_wait>=2);
    assign rvalid=stray_read || (instant_read && rv && rrdy) || (reading && r_wait==0);
    assign rdata=memory[(instant_read ? ra : saved_ra)>>3];
    assign wrdy=(instant_write && av && ardy) || (writing && w_wait==0);
    wire [27:0] write_addr=instant_write ? aa : saved_aa;
    wire [3:0] model_id=instant_read ? rid : saved_rid;
    wire [3:0] returned_id=bad_id ? 4'hf : (cross_id ? (model_id ^ 4'd1) : model_id);

    dual_sram_to_pango_ddr_bridge #(.INST_LINE_BUFFER_ENABLE(ENABLE)) dut(
        .clk(clk),.resetn(resetn),.ddr_init_done(init_done),
        .inst_req_valid(iv),.inst_req_addr(ia),.inst_req_ready(ir),
        .inst_rsp_valid(isv),.inst_rsp_rdata(idata),.inst_rsp_error(ise),
        .data_req_valid(dv),.data_req_write(dw),.data_req_size(ds),
        .data_req_addr(da),.data_req_wdata(wd),.data_req_wstrb(ws),
        .data_req_ready(dr),.data_rsp_valid(dsv),.data_rsp_rdata(ddata),.data_rsp_error(dse),
        .axi_awaddr(aa),.axi_awuser_ap(apw),.axi_awuser_id(wid),.axi_awlen(alen),
        .axi_awready(ardy),.axi_awvalid(av),.axi_wdata(wdata),.axi_wstrb(wstrb),
        .axi_wready(wrdy),.axi_wusero_id(4'd1),.axi_wusero_last(wrdy),
        .axi_araddr(ra),.axi_aruser_ap(apr),.axi_aruser_id(rid),.axi_arlen(rlen),
        .axi_arready(rrdy),.axi_arvalid(rv),.axi_rdata(rdata),
        .axi_rid(returned_id),.axi_rlast(rvalid && !bad_last),.axi_rvalid(rvalid));

    function automatic [31:0] word_at(input [31:0] address);
        word_at=memory[address>>4][address[3:2]*32+:32];
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
            if (iv && ir) begin expected_ra<={ia[28:4],3'b0};expected_rid<=0;end
            if (dv && dr) begin
                if (dw) begin
                    expected_aa<={da[28:4],3'b0};
                    expected_wdata<={96'b0,wd} << {da[3:2],5'b0};
                    expected_wstrb<={12'b0,ws} << {da[3:2],2'b0};
                end else begin expected_ra<={da[28:4],3'b0};expected_rid<=1;end
            end
            if (iv && ir) i_requests<=i_requests+1;
            if (dv && dr) d_requests<=d_requests+1;
            if (isv) i_responses<=i_responses+1;
            if (dsv) d_responses<=d_responses+1;
            if (isv && dsv) $fatal(1,"RESULT: FAIL duplicate response owner");
            if (iv && dv && ir) $fatal(1,"RESULT: FAIL instruction bypassed data priority");
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
                for (integer byte_lane=0;byte_lane<16;byte_lane=byte_lane+1)
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
            if (data_port) dv=0; else iv=0;
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

    task automatic queued_inst_fill(input bit same_row_write);
        begin
            @(negedge clk);iv=1;ia='h6c;
            @(posedge clk);@(negedge clk);iv=0;ia='h14;
            dv=1;dw=1;da=same_row_write ? 'h64 : 'he4;wd=32'h76543210;ws=15;
            while (!isv) begin
                if (dr) $fatal(1,"RESULT: FAIL accepted queued write during IF fill");
                @(negedge clk);
            end
            if (ise || idata!==word_at('h6c)) $fatal(1,"RESULT: FAIL accepted IF tag/lane");
            while (!dr) @(negedge clk);
            @(posedge clk);@(negedge clk);dv=0;
            while (!dsv) @(negedge clk);
            if (dse || ddata!==0) $fatal(1,"RESULT: FAIL queued write response");
            @(negedge clk);
            fetch('h64,same_row_write ? 1 : 0);fetch('h6c,0);
            tests=tests+1;
        end
    endtask

    task automatic cached_contention(input bit store_request);
        integer old_ar,old_aw;
        begin
            @(negedge clk);old_ar=ar_count;old_aw=aw_count;
            iv=1;ia='h74;dv=1;dw=store_request;da='h74;wd=32'h2468ace0;ws=15;
            #1;if (!dr || ir) $fatal(1,"RESULT: FAIL cached data-first arbitration");
            @(posedge clk);@(negedge clk);dv=0;
            while (!dsv) begin
                if (ir) $fatal(1,"RESULT: FAIL accepted IF during data response wait");
                @(negedge clk);
            end
            if (dse || ddata!==(store_request ? 32'b0 : word_at('h74)))
                $fatal(1,"RESULT: FAIL cached contention data response");
            while (!ir) @(negedge clk);
            @(posedge clk);@(negedge clk);iv=0;
            while (!isv) @(negedge clk);
            if (ise || idata!==word_at('h74)) $fatal(1,"RESULT: FAIL cached contention IF response");
            if (ar_count-old_ar!=integer'(store_request) || aw_count-old_aw!=integer'(store_request))
                $fatal(1,"RESULT: FAIL cached contention AR/AW");
            @(negedge clk);tests=tests+1;
        end
    endtask

    initial begin
        if ((LINES!=4 && LINES!=8) || !ENABLE || !D_ENABLED)
            $fatal(1,"RESULT: FAIL unsupported oracle configuration");
        for (k=0;k<64;k=k+1)
            for (lane=0;lane<4;lane=lane+1) memory[k][lane*32+:32]=32'h12340000+k*16+lane*4;
        repeat(3) @(negedge clk);resetn=1;
        repeat(2) @(negedge clk);
        if (ir || dr) $fatal(1,"RESULT: FAIL ready before DDR initialization");
        init_done=1;
        for (k=0;k<LINES;k=k+1) fetch(k*16,1);
        for (k=0;k<LINES;k=k+1)
            for (lane=0;lane<4;lane=lane+1) fetch(k*16+lane*4,0);
        fetch('h00,0);fetch('h40,LINES==8 ? 0 : 1);fetch('h00,LINES==8 ? 0 : 1);
        // 128-byte aliases collide in both versions, while bank4 survives in the new one.
        fetch('h80,1);fetch('h40,LINES==8 ? 0 : 1);fetch('h80,LINES==8 ? 0 : 1);
        fetch('h84,0);fetch('h10,0);
        $display("CHECK: all_indices_slots_and_64_128_byte_conflicts PASS");

        cold();
        for (k=0;k<LINES;k=k+1) fetch(k*16,1);
        fetch('h50,LINES==8 ? 0 : 1);load_word('h50,1);fetch('h20,0);
        store_word('h54,32'haabbccdd,15);fetch('h54,1);load_word('h54,1);
        fetch('h20,0);fetch('h10,LINES==8 ? 0 : 1);fetch('h50,LINES==8 ? 0 : 1);
        // Same index, different full tag must preserve both the I and D rows.
        store_word('hd0,32'h11223344,15);fetch('h58,0);load_word('h58,0);
        ds=0;store_word('h55,32'h00005a00,2);fetch('h54,1);load_word('h55,1);
        ds=1;store_word('h5a,32'habcd0000,12);fetch('h58,1);load_word('h5a,1);
        ds=2;store_word('h5c,0,0);fetch('h5c,1);load_word('h5c,1);
        fetch('h5c,0);load_word('h5c,0);fetch('h20,0);
        $display("CHECK: upper_index_full_tag_partial_zero_write_invalidation PASS");

        cold();
        for (k=0;k<LINES;k=k+1) fetch(k*16,1);
        load_word('h180,1);
        for (k=0;k<LINES;k=k+1) fetch(k*16,0);
        load_word('h184,0);fetch('h1e0,1);load_word('h188,0);
        load_word('h280,1);fetch('h1e4,0);
        cold();queued_inst_fill(0);
        cold();queued_inst_fill(1);
        // Hold both cached requests together; then prove one write invalidates both.
        fetch('h70,1);load_word('h70,1);cached_contention(0);cached_contention(1);
        load_word('h74,1);fetch('h78,0);load_word('h78,0);
        $display("CHECK: independent_D_buffer_locked_IF_fill_and_data_priority PASS");

        cold();instant_read=1;instant_write=1;backpressure=0;
        fetch('h70,1);fetch('h7c,0);load_word('h70,1);
        store_word('h74,32'habcd1234,15);fetch('h74,1);load_word('h74,1);
        bad_id=1;fetch('hf0,1);fetch('hf4,1);bad_id=0;
        fetch('h78,0);load_word('h78,0);
        bad_last=1;fetch('h170,1);fetch('h174,1);bad_last=0;fetch('h7c,0);
        cross_id=1;fetch('hf0,1);cross_id=0;fetch('h70,0);load_word('h7c,0);
        $display("CHECK: same_cycle_returns_and_bad_sidebands_preserve_victim PASS");

        cold();
        for (k=0;k<LINES;k=k+1) fetch('h100+k*16,1);
        load_word('h340,1);cold();
        for (k=0;k<LINES;k=k+1) begin fetch('h100+k*16,1);fetch('h104+k*16,0);end
        load_word('h344,1);load_word('h348,0);
        $display("CHECK: DDR_readiness_clears_all_indices_and_D PASS");
        conservation();
        instant_read=0;instant_write=0;backpressure=1;
        @(negedge clk);iv=1;ia='h2fc;
        @(posedge clk);@(negedge clk);iv=0;
        wait(rv);@(negedge clk);resetn=0;init_done=0;
        repeat(3) @(negedge clk);
        if (isv || dsv || rv || av) $fatal(1,"RESULT: FAIL reset did not cancel request");
        resetn=1;init_done=1;
        for (k=0;k<LINES;k=k+1) begin fetch('h100+k*16,1);fetch('h104+k*16,0);end
        load_word('h340,1);load_word('h344,0);
        conservation();
        $display("CHECK: reset_cancels_fill_and_clears_all_indices PASS");
        $display("RESULT: PASS inst_cache8 lines=%0d tests=%0d",LINES,tests);
        $finish;
    end
    initial begin #1000000;$fatal(1,"RESULT: FAIL watchdog");end
endmodule
