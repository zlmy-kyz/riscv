`timescale 1ns/1ps
// Functional Pango user-port test only; physical DDR performance is a separate run.
module tb_inst_line_invalidation;
    // SELECTIVE=0 checks the preserved all-write-invalidate bridge.
    parameter integer SELECTIVE = 1;
    parameter integer ENABLE = 1;
    reg clk=0, resetn=0, init_done=0;
    always #5 clk=~clk;
    reg iv=0, dv=0, dw=0;
    reg [31:0] ia=0, da=0, wd=0;
    reg [3:0] ws=0;
    wire ir, dr, isv, dsv, ise, dse;
    wire [31:0] idata, ddata;
    wire [27:0] aa, ra;
    wire av, rv, ardy, rrdy, wrdy, apw, apr;
    wire [127:0] wdata, rdata;
    wire [15:0] wstrb;
    wire [3:0] wid, rid, alen, rlen;
    wire rvalid;
    reg backpressure=1, instant_read=0, instant_write=0;
    reg bad_id=0, bad_last=0;
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
    assign rvalid=(instant_read && rv && rrdy) || (reading && r_wait==0);
    assign rdata=memory[(instant_read ? ra : saved_ra)>>3];
    assign wrdy=(instant_write && av && ardy) || (writing && w_wait==0);
    wire [27:0] write_addr=instant_write ? aa : saved_aa;
    wire [3:0] returned_id=bad_id ? 4'hf : (instant_read ? rid : saved_rid);

    dual_sram_to_pango_ddr_bridge #(.INST_LINE_BUFFER_ENABLE(ENABLE)) dut(
        .clk(clk),.resetn(resetn),.ddr_init_done(init_done),
        .inst_req_valid(iv),.inst_req_addr(ia),.inst_req_ready(ir),
        .inst_rsp_valid(isv),.inst_rsp_rdata(idata),.inst_rsp_error(ise),
        .data_req_valid(dv),.data_req_write(dw),.data_req_size(2'd2),
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
            expected_ar=write_request ? 0 : (data_port || !ENABLE ? 1 : cached_ar);
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
            if (!data_port && ENABLE && cached_ar==0 && waited!=0)
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

    task automatic write_queued_during_fill(input bit unrelated);
        begin
            @(negedge clk);iv=1;ia='h50;
            @(posedge clk);@(negedge clk);iv=0;
            dv=1;dw=1;da=unrelated ? 'h150 : 'h50;wd=32'h76543210;ws=4'b1111;
            while (!isv) begin
                if (dr) $fatal(1,"RESULT: FAIL accepted write during pending fill");
                @(negedge clk);
            end
            if (idata!==word_at('h50)) $fatal(1,"RESULT: FAIL original pending read");
            while (!dr) @(negedge clk);
            @(posedge clk);@(negedge clk);dv=0;
            while (!dsv) @(negedge clk);
            @(negedge clk);
            fetch('h50,(unrelated && SELECTIVE) ? 0 : 1);fetch('h54,0);
            tests=tests+1;
        end
    endtask

    task automatic fetch(input [31:0] address,input integer cached_ar);
        transfer(0,0,address,0,0,word_at(address),cached_ar);
    endtask

    task automatic simultaneous_read(input [31:0] address);
        integer old_ar;
        begin
            @(negedge clk);old_ar=ar_count;iv=1;ia=address;dv=1;dw=0;da=address;ws=0;
            #1;if (!dr || ir) $fatal(1,"RESULT: FAIL initial data priority");
            @(posedge clk);@(negedge clk);dv=0;
            while (!dsv) @(negedge clk);
            if (ddata!==word_at(address) || dse) $fatal(1,"RESULT: FAIL data response during contention");
            while (!ir) @(negedge clk);
            @(posedge clk);@(negedge clk);iv=0;
            while (!isv) @(negedge clk);
            if (idata!==word_at(address) || ise) $fatal(1,"RESULT: FAIL instruction response during contention");
            if (ar_count-old_ar!=(ENABLE ? 1 : 2)) $fatal(1,"RESULT: FAIL contention command count");
            @(negedge clk);tests=tests+1;
        end
    endtask

    task automatic simultaneous_write(input [31:0] write_address,
                                       input [31:0] fetch_address);
        integer old_ar, old_aw, expected_ar;
        begin
            @(negedge clk);old_ar=ar_count;old_aw=aw_count;
            iv=1;ia=fetch_address;dv=1;dw=1;da=write_address;
            wd=32'h2468ace0;ws=4'b1111;
            expected_ar=SELECTIVE && write_address[31:4]!=fetch_address[31:4] ? 0 : 1;
            #1;if (!dr || ir) $fatal(1,"RESULT: FAIL write lost initial data priority");
            @(posedge clk);@(negedge clk);dv=0;
            while (!dsv) begin
                if (ir) $fatal(1,"RESULT: FAIL fetch accepted before write response");
                @(negedge clk);
            end
            if (ddata!==0 || dse) $fatal(1,"RESULT: FAIL simultaneous write response");
            while (!ir) @(negedge clk);
            @(posedge clk);@(negedge clk);iv=0;
            while (!isv) @(negedge clk);
            if (idata!==word_at(fetch_address) || ise)
                $fatal(1,"RESULT: FAIL fetch returned stale data after concurrent write");
            if (ar_count-old_ar!=expected_ar || aw_count-old_aw!=1)
                $fatal(1,"RESULT: FAIL simultaneous write command conservation");
            @(negedge clk);tests=tests+1;
        end
    endtask

    initial begin
        for (k=0;k<64;k=k+1)
            for (lane=0;lane<4;lane=lane+1) memory[k][lane*32+:32]=32'h12340000+k*16+lane*4;
        repeat(3) @(negedge clk);resetn=1;
        repeat(2) @(negedge clk);
        if (ir || dr) $fatal(1,"RESULT: FAIL accepted before DDR init");
        init_done=1;
        fetch('h60,1);fetch('h64,0);
        // Four lanes, a neighbouring line, and a same-low-address/different-tag line.
        for (k=0;k<4;k=k+1) begin
            transfer(1,1,'h160+k*4,32'hf0e0d0c0+k,4'b1111,0,0);
            fetch('h60+k*4,SELECTIVE ? 0 : 1);
        end
        transfer(1,1,'h70,32'habcdef12,4'b1111,0,0);
        fetch('h60,SELECTIVE ? 0 : 1);
        transfer(1,1,'h160,0,4'b0000,0,0);
        fetch('h60,SELECTIVE ? 0 : 1);
        // All word lanes in the cached line must still invalidate and reread.
        for (k=0;k<4;k=k+1) begin
            transfer(1,1,'h60+k*4,32'h87654320+k,4'b1111,0,0);
            fetch('h60+k*4,1);fetch('h60+k*4,0);
        end
        transfer(1,1,'h65,32'h00005a00,4'b0010,0,0);fetch('h64,1);
        transfer(1,1,'h6a,32'habcd0000,4'b1100,0,0);fetch('h68,1);
        transfer(1,1,'h68,0,4'b0000,0,0);fetch('h68,1);
        // Data reads don't allocate; simultaneous reads retain data priority.
        transfer(1,0,'h160,0,0,word_at('h160),1);fetch('h68,0);
        simultaneous_read('h68);
        simultaneous_write('h168,'h68);
        simultaneous_write('h68,'h68);
        // A queued write cannot be accepted until the pending fill has completed.
        write_queued_during_fill(0);
        fetch('h60,1);
        write_queued_during_fill(1);
        instant_read=1;instant_write=1;backpressure=0;
        fetch('h80,1);fetch('h84,0);
        transfer(1,1,'h180,32'h13579bdf,4'b1111,0,0);
        fetch('h84,SELECTIVE ? 0 : 1);
        transfer(1,1,'h84,32'h13579bdf,4'b1111,0,0);fetch('h84,1);
        // DDR readiness loss and reset always invalidate, independent of tag.
        @(negedge clk);init_done=0;
        repeat(3) @(negedge clk);
        if (ir || dr) $fatal(1,"RESULT: FAIL request while DDR not ready");
        init_done=1;fetch('h84,1);fetch('h88,0);
        repeat(2) @(negedge clk);
        if (i_requests!=i_responses || d_requests!=d_responses || aw_count!=w_count)
            $fatal(1,"RESULT: FAIL pre-reset conservation");
        @(negedge clk);resetn=0;init_done=0;
        repeat(3) @(negedge clk);resetn=1;init_done=1;
        fetch('h88,1);fetch('h8c,0);
        repeat(3) @(negedge clk);
        if (i_requests!=i_responses || d_requests!=d_responses || aw_count!=w_count)
            $fatal(1,"RESULT: FAIL final conservation");
        $display("RESULT: PASS inst_line_invalidation selective=%0d tests=%0d",SELECTIVE,tests);
        $finish;
    end
    initial begin #1000000;$fatal(1,"RESULT: FAIL watchdog");end
endmodule
