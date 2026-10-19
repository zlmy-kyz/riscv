`timescale 1ns/1ps
// Functional Pango user-port test only; physical DDR performance is a separate run.
module tb_data_read_buffer;
    // Oracle only: frozen baseline has no D buffer; current candidate enables it.
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

    task automatic simultaneous(input bit write_request,input [31:0] address);
        integer old_ar,old_aw;
        begin
            @(negedge clk);old_ar=ar_count;old_aw=aw_count;
            iv=1;ia=address;dv=1;dw=write_request;da=address;wd=32'h87654321;ws=15;
            #1;if (!dr || ir) $fatal(1,"RESULT: FAIL data priority");
            @(posedge clk);@(negedge clk);dv=0;
            while (!dsv) begin
                if (ir) $fatal(1,"RESULT: FAIL fetch accepted during data transaction");
                @(negedge clk);
            end
            if (dse || ddata!==(write_request ? 32'b0 : word_at(address)))
                $fatal(1,"RESULT: FAIL concurrent data response");
            while (!ir) @(negedge clk);
            @(posedge clk);@(negedge clk);iv=0;
            while (!isv) @(negedge clk);
            if (ise || idata!==word_at(address)) $fatal(1,"RESULT: FAIL concurrent fetch");
            if (ar_count-old_ar!=(write_request ? 1 : (D_ENABLED ? 0 : 1)) ||
                aw_count-old_aw!=integer'(write_request))
                $fatal(1,"RESULT: FAIL concurrent commands");
            @(negedge clk);tests=tests+1;
        end
    endtask

    // Read miss uses its accepted tag/lane even when the live address changes;
    // queued writes cannot be accepted until its response has completed.
    task automatic queued_write(input bit unrelated);
        begin
            @(negedge clk);dv=1;dw=0;da='h180;ws=0;
            @(posedge clk);@(negedge clk);dv=0;da='h2d0;
            wait(rv);@(negedge clk);
            dv=1;dw=1;da=unrelated ? 'h280 : 'h180;wd=32'h90807060;ws=15;
            while (!dsv) begin
                if (dr) $fatal(1,"RESULT: FAIL queued write accepted during read");
                @(negedge clk);
            end
            if (ddata!==word_at('h180)) $fatal(1,"RESULT: FAIL accepted read address");
            while (!dr) @(negedge clk);
            @(posedge clk);@(negedge clk);dv=0;
            while (!dsv) @(negedge clk);
            @(negedge clk);
            load_word('h180,unrelated ? 0 : 1);load_word('h184,0);
            tests=tests+1;
        end
    endtask

    task automatic read_with_stray_return;
        integer old_ar;
        begin
            @(negedge clk);old_ar=ar_count;dv=1;dw=0;da='h380;
            @(posedge clk);@(negedge clk);dv=0;stray_read=1;
            // AR is still backpressured; this unsolicited RVALID cannot complete it.
            repeat(2) begin
                @(negedge clk);
                if (dsv || dr) $fatal(1,"RESULT: FAIL unsolicited response completed read");
            end
            stray_read=0;
            while (!dsv) @(negedge clk);
            if (dse || ddata!==word_at('h380) || ar_count-old_ar!=1)
                $fatal(1,"RESULT: FAIL read after unsolicited response");
            @(negedge clk);tests=tests+1;
            load_word('h384,0);
        end
    endtask

    initial begin
        for (k=0;k<64;k=k+1)
            for (lane=0;lane<4;lane=lane+1) memory[k][lane*32+:32]=32'h12340000+k*16+lane*4;
        repeat(3) @(negedge clk);resetn=1;
        repeat(2) @(negedge clk);
        if (ir || dr) $fatal(1,"RESULT: FAIL before DDR ready");
        init_done=1;
        // A cold row supplies all four words; subsequent IF requests cannot evict D.
        load_word('h20,1);
        fetch('h80,1);fetch('h90,1);fetch('ha0,1);fetch('hb0,1);
        for (k=0;k<4;k=k+1) begin load_word('h20+k*4,0);fetch('h80+k*16,0);end
        load_word('h60,1);load_word('h64,0);load_word('h20,1);load_word('h24,0);
        // D reads must not replace any of the four I banks.
        for (k=0;k<4;k=k+1) fetch('h80+k*16,0);
        store_word('h120,32'h11223344,15);load_word('h24,0);
        // Prime both caches on one row; a single accepted write invalidates both.
        fetch('h20,1);load_word('h20,0);
        for (k=0;k<4;k=k+1) begin
            ds=2;store_word('h20+k*4,32'hdead8000+k,15);
            fetch('h20+k*4,1);load_word('h20+k*4,1);
            fetch('h20+k*4,0);load_word('h20+k*4,0);
        end
        // Every byte/halfword position, not only the low lane.
        for (k=0;k<16;k=k+1) begin
            ds=0;store_word('h20+k,32'h80 << ((k%4)*8),4'b0001 << (k%4));
            ds=2;load_word('h20+(k/4)*4,1);fetch('h20+(k/4)*4,1);
            ds=0;load_word('h20+k,0);
        end
        for (k=0;k<8;k=k+1) begin
            ds=1;store_word('h20+k*2,32'h9876 << ((k%2)*16),4'b0011 << ((k%2)*2));
            load_word('h20+k*2,1);fetch('h20+k*2,1);load_word('h20+k*2,0);
        end
        ds=2;store_word('h2c,0,0);load_word('h2c,1);fetch('h2c,1);
        // D miss data stays independent of the current instruction row.
        load_word('h140,1);fetch('h20,0);load_word('h144,0);
        // Write hits I only, then D only, then neither.
        store_word('h20,32'haabbccdd,15);load_word('h140,0);fetch('h20,1);
        store_word('h140,32'h11224488,15);fetch('h20,0);load_word('h140,1);
        store_word('h240,32'h12345678,15);fetch('h20,0);load_word('h140,0);
        queued_write(0);load_word('h1c0,1);queued_write(1);
        // Both cached responses still obey data-first arbitration.
        fetch('h180,1);load_word('h180,0);simultaneous(0,'h180);
        simultaneous(1,'h180);load_word('h180,1);load_word('h184,0);
        // Same-cycle AR/R and AW/W responses use the same allocation/invalidation.
        instant_read=1;instant_write=1;backpressure=0;
        load_word('h200,1);load_word('h20c,0);
        fetch('h200,1);store_word('h204,32'habcd1234,15);
        load_word('h204,1);fetch('h204,1);load_word('h208,0);
        // Identity errors cannot evict an existing valid D row.
        bad_id=1;load_word('h240,1);load_word('h244,1);bad_id=0;
        load_word('h208,0);
        bad_last=1;load_word('h280,1);load_word('h284,1);bad_last=0;
        load_word('h20c,0);load_word('h280,1);load_word('h284,0);
        cross_id=1;load_word('h240,1);cross_id=0;load_word('h284,0);
        cross_id=1;fetch('h340,1);cross_id=0;load_word('h284,0);fetch('h340,1);
        fetch('h300,1);load_word('h284,0);fetch('h304,0);
        @(negedge clk);init_done=0;
        repeat(3) @(negedge clk);
        if (ir || dr) $fatal(1,"RESULT: FAIL accepted without DDR readiness");
        init_done=1;load_word('h280,1);load_word('h284,0);fetch('h300,1);
        conservation();
        // Reset cancels a pending D miss; both caches must become cold.
        instant_read=0;instant_write=0;backpressure=1;
        read_with_stray_return();
        @(negedge clk);dv=1;dw=0;da='h340;
        @(posedge clk);@(negedge clk);dv=0;
        wait(rv);@(negedge clk);resetn=0;init_done=0;
        repeat(3) @(negedge clk);resetn=1;init_done=1;
        load_word('h280,1);load_word('h284,0);fetch('h300,1);fetch('h304,0);
        conservation();
        $display("RESULT: PASS data_read_buffer enabled=%0d tests=%0d",D_ENABLED,tests);
        $finish;
    end
    initial begin #1000000;$fatal(1,"RESULT: FAIL watchdog");end
endmodule
